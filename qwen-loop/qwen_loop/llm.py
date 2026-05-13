"""
Qwen2.5:72B 클라이언트 래퍼.

핵심 기능:
- Ollama 백엔드 호출 (chat / generate)
- JSON 강제 모드 (format="json")
- Pydantic 스키마 기반 구조화 출력 (parse 실패 시 재시도)
- 환각 억제용 시스템 프롬프트 기본 주입
- Self-consistency (N개 샘플링 후 다수결 또는 평균)
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Type, TypeVar

import ollama
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

T = TypeVar("T", bound=BaseModel)

# Qwen2.5의 closed-book 환각 패턴을 인지하고, "모르면 모른다"를 강제하는 기본 시스템 프롬프트
DEFAULT_SYSTEM = """당신은 학술 논문 처리를 돕는 보조 AI입니다.

규칙:
1. 주어진 문서/도구 결과에 명시되지 않은 사실은 절대 단언하지 마세요.
2. 인용·저자·연도 등 메타데이터는 출처가 없으면 null 또는 "unknown"으로 표시하세요.
3. 추측이 필요하면 "추측:" 접두어를 붙이고 근거를 명시하세요.
4. 한국어 입력에는 한국어로, 영어 입력에는 영어로 응답하세요.
5. 형식 지시(JSON 스키마 등)가 주어지면 반드시 그 형식만 출력하세요. 다른 텍스트 금지."""


class QwenClient:
    def __init__(
        self,
        model: str = "qwen2.5:72b",
        host: str = "http://localhost:11434",
        temperature: float = 0.2,
        top_p: float = 0.9,
        num_ctx: int = 32768,
        timeout: int = 600,
    ):
        self.client = ollama.Client(host=host, timeout=timeout)
        self.model = model
        self.opts = {"temperature": temperature, "top_p": top_p, "num_ctx": num_ctx}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def chat(
        self,
        prompt: str,
        system: str | None = None,
        history: list[dict] | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
    ) -> str:
        """단일 응답."""
        messages = [{"role": "system", "content": system or DEFAULT_SYSTEM}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        opts = dict(self.opts)
        if temperature is not None:
            opts["temperature"] = temperature

        resp = self.client.chat(
            model=self.model,
            messages=messages,
            options=opts,
            format="json" if json_mode else "",
        )
        return resp["message"]["content"]

    def parse(
        self,
        prompt: str,
        schema: Type[T],
        system: str | None = None,
        history: list[dict] | None = None,
        max_repair: int = 2,
    ) -> T:
        """
        Pydantic 스키마로 강제 구조화 출력.
        파싱 실패 시 모델에 에러 메시지를 보여주고 자가 수정 요청 (max_repair회).
        """
        sys_prompt = (system or DEFAULT_SYSTEM) + (
            f"\n\n출력은 반드시 다음 JSON 스키마를 따라야 합니다:\n"
            f"```json\n{json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)}\n```\n"
            f"오직 JSON만 출력하세요."
        )
        last_err = None
        cur_prompt = prompt
        for attempt in range(max_repair + 1):
            raw = self.chat(cur_prompt, system=sys_prompt, history=history, json_mode=True)
            try:
                return schema.model_validate_json(raw)
            except ValidationError as e:
                last_err = e
                cur_prompt = (
                    f"이전 응답이 스키마 검증에 실패했습니다.\n"
                    f"실패한 응답:\n{raw}\n\n"
                    f"검증 오류:\n{e}\n\n"
                    f"원래 요청:\n{prompt}\n\n"
                    f"오류를 수정해 다시 출력하세요. JSON만."
                )
        raise RuntimeError(f"Schema validation failed after {max_repair} repairs: {last_err}")

    def self_consistent(
        self,
        prompt: str,
        n: int = 3,
        temperature: float = 0.7,
        system: str | None = None,
    ) -> tuple[str, float]:
        """
        N개 샘플 후 다수결. (정답 텍스트, 동의율) 반환.
        핵심 추론 단계에서만 호출 — 비싸다.
        """
        samples = [
            self.chat(prompt, system=system, temperature=temperature) for _ in range(n)
        ]
        # 단순 다수결 — 도메인에 맞게 normalize 함수를 주입할 수도 있음
        normalized = [s.strip() for s in samples]
        counter = Counter(normalized)
        winner, count = counter.most_common(1)[0]
        return winner, count / n

    def embed(self, text: str) -> list[float]:
        """임베딩은 별도 모델 권장 — 여기서는 Ollama embedding endpoint 사용."""
        return self.client.embeddings(model=self.model, prompt=text)["embedding"]
