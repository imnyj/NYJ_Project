"""
Episodic memory: 모든 task 실행 기록 (input, plan, actions, output, score, reflection).
이 데이터가 self-upgrade 학습 소스.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
    kind = Column(String(64), index=True)              # task 종류 (예: extract_citations)
    prompt_version = Column(String(64), index=True)    # 사용된 프롬프트 버전
    input_payload = Column(JSON)                        # 입력
    plan = Column(JSON)                                 # ReAct plan trace
    actions = Column(JSON)                              # tool calls list
    output = Column(JSON)                               # 최종 출력
    success = Column(Integer)                           # 1=성공, 0=실패, NULL=미평가
    score = Column(Float)                               # 0.0~1.0 품질 점수
    reflection = Column(Text)                           # reflector가 남긴 메모
    error = Column(Text)                                # 에러 메시지 (실패 시)


class EpisodicMemory:
    def __init__(self, db_path: str = "data/episodic.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def log(self, **kwargs) -> int:
        with self.Session() as s:
            rec = TaskRecord(**kwargs)
            s.add(rec)
            s.commit()
            return rec.id

    def update(self, task_id: int, **kwargs) -> None:
        with self.Session() as s:
            rec = s.get(TaskRecord, task_id)
            if rec is None:
                raise ValueError(f"Task {task_id} not found")
            for k, v in kwargs.items():
                setattr(rec, k, v)
            s.commit()

    def recent(self, kind: str | None = None, limit: int = 50) -> list[TaskRecord]:
        with self.Session() as s:
            q = s.query(TaskRecord)
            if kind:
                q = q.filter(TaskRecord.kind == kind)
            return q.order_by(desc(TaskRecord.created_at)).limit(limit).all()

    def failures(self, kind: str | None = None, limit: int = 50) -> list[TaskRecord]:
        with self.Session() as s:
            q = s.query(TaskRecord).filter(TaskRecord.success == 0)
            if kind:
                q = q.filter(TaskRecord.kind == kind)
            return q.order_by(desc(TaskRecord.created_at)).limit(limit).all()

    def winrate(self, kind: str, prompt_version: str) -> tuple[int, float]:
        """(시도 수, 성공률) 반환."""
        with self.Session() as s:
            recs = (
                s.query(TaskRecord)
                .filter(TaskRecord.kind == kind, TaskRecord.prompt_version == prompt_version)
                .all()
            )
            n = len(recs)
            if n == 0:
                return 0, 0.0
            wins = sum(1 for r in recs if r.success == 1)
            return n, wins / n
