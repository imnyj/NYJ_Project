## 2026-09-03T10:26:24+09:00

당신은 Auto_Stock Phase 5의 Regression & Integration Reviewer (teamwork_preview_reviewer)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_p5_2/` 입니다.

### 필수 참조 자료 (Mandatory)
작업 시작 전 반드시 다음 파일들을 읽으십시오:
- `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/GEMINI.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/SCOPE.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5/handoff.md`

### 검토 대상 파일
- `modules/data/screener.py`
- `modules/data/__init__.py`
- `modules/engine/live_learning_simulator.py`
- `tests/test_phase5_screener.py`

### 검토 목표 및 업무
1. `modules/engine/live_learning_simulator.py`의 기존 `step(symbol, action, quantity)` 및 `get_state()`에 대한 100% 하위 호환성을 검증하십시오.
2. `tests/test_live_learning_simulator.py` 및 `tests/test_hybrid_trading_env.py` 등 기존 엔진/RL 테스트가 회귀 없이 100% 통과하는지 직접 테스트하십시오:
   `/home/imnyj/venv/bin/pytest tests/test_live_learning_simulator.py tests/test_hybrid_trading_env.py -v`
   `/home/imnyj/venv/bin/pytest tests/test_phase5_screener.py -v`
3. Worker가 보고한 `test_phase3_api.py`의 만료시각 사전결함 격리가 타당한지 검토하고, Phase 5 변경이 타 모듈에 부수효과(side-effect)를 미치지 않았는지 확인하십시오.
4. 최종 판정(`APPROVE` 또는 `REQUEST_CHANGES`)을 내리고, 상세 분석 근거와 함께 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_reviewer_p5_2/handoff.md`를 작성한 뒤 caller에게 send_message로 보고하십시오.
5. 모든 문서와 커뮤니케이션은 한국어로 작성하십시오. 코드를 직접 수정하지 마십시오.
