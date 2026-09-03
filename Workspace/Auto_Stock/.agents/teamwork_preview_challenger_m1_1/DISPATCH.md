## 2026-09-02T02:05:03Z

<USER_REQUEST>
당신은 Auto_Stock 프로젝트 Milestone 1의 적대적 챌린저 1 (`teamwork_preview_challenger_m1_1`)입니다.

### 작업 환경
- Your Working Directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_m1_1/
- Project Directory: /home/imnyj/Workspace/Auto_Stock
- Original Request File: /home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md

### 챌린지 대상
- `modules/engine/hybrid_trading_env.py`

### 지시사항
1. 반드시 `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`를 읽으세요.
2. 스트레스 테스트 하네스를 작성하여 실행하세요:
   - 10,000회 이상의 극단적 랜덤 액션 스트림 (경계값 0.0, 1.0, 음수, 과대 비중, 비정상 포맷) 주입
   - 대규모 연속 매수/매도 시 회계 불변식(`verify_accounting_invariant`) 0원 오차 유지 검증
   - 자산 소진 및 파산 임계값에서의 환경 안정성 스트레스 테스트
3. 스트레스 테스트 결과를 바탕으로 최종 보고서를 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_m1_1/handoff.md`에 작성하고 판정(`APPROVE` 또는 `FAIL`)을 보고하세요.
</USER_REQUEST>
