"""
페이퍼 AI 본체에서 HTTP로 잡일을 보내기 위한 FastAPI 서버.

사용:
    python scripts/serve.py
    
    # 본체에서:
    POST http://localhost:8765/task
    {"kind": "extract_citations", "input": {"pdf_path": "..."}}
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import yaml

from qwen_loop.agent import Agent, TaskRequest


class TaskIn(BaseModel):
    kind: str
    input: dict
    use_react: bool = True
    use_verifier: bool = True


def make_app(agent: Agent) -> FastAPI:
    app = FastAPI(title="qwen-loop")

    @app.post("/task")
    def run_task(t: TaskIn):
        req = TaskRequest(
            kind=t.kind, input=t.input, use_react=t.use_react, use_verifier=t.use_verifier
        )
        r = agent.run(req)
        return {
            "task_id": r.task_id,
            "converged": r.converged,
            "score": r.score,
            "output": r.output,
            "reflection_note": r.reflection_note,
        }

    @app.post("/maintenance/ab")
    def maintenance_ab():
        return {"promoted": agent.run_ab_promotions()}

    @app.post("/maintenance/skills")
    def maintenance_skills():
        return {"proposals": agent.scan_skill_proposals()}

    @app.get("/health")
    def health():
        return {"ok": True, "model": agent.cfg["llm"]["model"]}

    return app


def main():
    cfg = yaml.safe_load(open("config.yaml"))
    agent = Agent("config.yaml")
    app = make_app(agent)
    uvicorn.run(app, host=cfg["server"]["host"], port=cfg["server"]["port"])


if __name__ == "__main__":
    main()
