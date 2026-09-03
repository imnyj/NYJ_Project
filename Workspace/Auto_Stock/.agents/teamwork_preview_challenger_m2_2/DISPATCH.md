## 2026-09-02T02:18:41Z
<USER_REQUEST>
당신은 Auto_Stock 프로젝트 Milestone 2의 적대적 챌린저 2 (`teamwork_preview_challenger_m2_2`)입니다.

### 작업 환경
- Your Working Directory: /home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_m2_2/
- Project Directory: /home/imnyj/Workspace/Auto_Stock
- Original Request File: /home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md

### 챌린지 대상
- `modules/models/feature_extractor.py`
- `modules/models/hybrid_policy.py`

### 지시사항
1. 반드시 `/home/imnyj/Workspace/Auto_Stock/.agents/ORIGINAL_REQUEST.md`를 읽으세요.
2. RL 정책 및 SB3 연동에 대한 적대적 챌린지를 수행하세요:
   - `HybridPPO` 및 `SB3HybridPolicyAdapter`와 `HybridTradingEnv` 간 1,000 스텝 롤아웃 학습 및 정책 수렴성 스트레스 검증
   - GAE 어드밴티지 및 엔트로피 보너스 계산의 수치적 무결성
   - 난수 시드 기반 학습 재현성 및 모델 저장/로드 후 체크포인트 가중치 일치 검증
3. 최종 보고서를 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_challenger_m2_2/handoff.md`에 작성하고 판정(`APPROVE` 또는 `FAIL`)을 보고하세요.
</USER_REQUEST>
