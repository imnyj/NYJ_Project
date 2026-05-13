"""Working memory: 최근 대화 turn deque. 매 LLM 호출 컨텍스트에 포함."""

from collections import deque
from typing import Iterator


class WorkingMemory:
    def __init__(self, max_turns: int = 12):
        self._buf: deque[dict] = deque(maxlen=max_turns)

    def add(self, role: str, content: str) -> None:
        self._buf.append({"role": role, "content": content})

    def history(self) -> list[dict]:
        return list(self._buf)

    def clear(self) -> None:
        self._buf.clear()

    def __iter__(self) -> Iterator[dict]:
        return iter(self._buf)

    def __len__(self) -> int:
        return len(self._buf)
