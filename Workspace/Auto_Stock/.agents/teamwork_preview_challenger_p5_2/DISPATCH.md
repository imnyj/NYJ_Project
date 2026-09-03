## 2026-09-03T01:26:24Z

당신은 Auto_Stock Phase 5의 RL Engine & Rate Limit Challenger (teamwork_preview_challenger)입니다.
당신의 작업 디렉토리는 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_p5_2/` 입니다.

### 필수 참조 자료 (Mandatory)
작업 시작 전 반드시 다음 파일들을 읽으십시오:
- `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`
- `/home/imnyj/GEMINI.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_orchestrator_5/SCOPE.md`
- `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_worker_p5/handoff.md`

### 챌린지 대상
- `modules/engine/live_learning_simulator.py`
- `modules/data/screener.py` (`ShardedPollingScheduler`, `TokenBucketLimiter`, WebSocket 연동)

### 적대적 챌린지 과제
`live_learning_simulator.py` 및 Rate Limiting 구조를 가혹한 극한 환경으로 실측 검증(Empirical Verification)하십시오:
1. 임시 테스트 스크립트(반드시 `etc/scripts/` 또는 에이전트 작업 디렉토리 내에 작성)를 작성하여 실행하십시오.
2. 검증 항목:
   - 100개 이상의 종목이 연속/동시 트리거 주입(`inject_triggered_symbol`)될 때 큐 오버플로우나 메모리 누수 없이 안정적으로 처리되는지 여부
   - `build_rl_observation`으로 생성된 벡터가 정확히 14차원 float32이고, NaN/Inf 없이 유효한 수치 범위를 유지하는지 여부
   - `step_symbol`에서 다중 종목 포지션 보유 중 가격 급변동 시 전체 포트폴리오 에쿼티가 정확히 보존되고 왜곡이 없는지 검증
   - `ShardedPollingScheduler` 및 `TokenBucketLimiter`가 초당 5회 제한을 100% 엄격 준수하여 429 에러 발생 가능성을 원천 차단하는지 검증
3. 실측 검증 결과를 수치와 함께 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_p5_2/handoff.md`에 상세히 기록하고 최종 판정(`APPROVE` 또는 `REJECT`)을 caller에게 send_message로 보고하십시오.
4. 소스 코드를 직접 수정하지 마십시오. 모든 문서와 커뮤니케이션은 한국어로 작성하십시오.
