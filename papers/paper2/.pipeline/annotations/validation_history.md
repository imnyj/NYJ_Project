# Validation History

## [2026-04-15] 검증 #1 (PASS)
- 검증 대상: 22개 CSV 파일
- 발견된 이슈: MINOR 1건 (S3 TSR 비단조 노이즈)
- 수정 제안: 수정 불필요 (측정 불확실성 범위 내)
- 데이터 무결성: NaN/범위/일관성 모두 PASS
## 검증 이력

---

### [2026-05-06] VALIDATION-MAFAC-001 — MAFAC 시뮬레이션 코드 성능/정확성 검증

**검증자:** Reviewer  
**결과:** ❌ FAIL — 코드 수정 필요  
**대상 파일:**
- `simulation/training/trainer.py`
- `simulation/agents/mafac_agent.py`
- `simulation/agents/federated.py`
- `simulation/env/sumo_env.py`
- `simulation/run_full_simulation.py`

**배경:** Phase 2 (50 vehicles, 500 ep, 3000 step/ep) 학습 시 110/500 ep에서 총 학습시간 3개월 추산. 코드 정확성 및 성능 검증 요청.

---

#### 발견된 이슈 요약 (FAIL 판정 근거)

| ID | 파일 | 심각도 | 판정 | 요약 |
|----|------|--------|------|------|
| BUG_001 | mafac_agent.py | CRITICAL | ✅ 확정 | 256× serial actor forward → 43-51x 속도 저하 |
| BUG_002 | mafac_agent.py | MAJOR | ✅ 확정 | _onehot_actions 이중 루프 (1024 Python iters/call) |
| BUG_003 | trainer.py | CRITICAL | ✅ 확정 | per-step per-vehicle update → 75M gradient updates |
| BUG_004 | trainer.py | MAJOR | ✅ 확정 | 50 독립 agent, warm-start 없음, replay buffer 단편화 |
| BUG_005 | trainer.py | CRITICAL | ✅ 확정 | checkpoint 첫 5개만 저장, buffer/optimizer state 미저장 |
| BUG_006 | run_full_simulation.py | CRITICAL | ✅ 확정 | Phase 2 항상 ep=1 시작, resume 불가 |
| BUG_007 | mafac_agent.py | MINOR | ✅ 추가발견 | log_prob(nlp) 계산 후 미사용 (낭비+entropy 누락 의심) |
| BUG_008 | mafac_agent.py | MAJOR | ✅ 추가발견 | actor advantage hybrid action bias |
| BUG_009 | trainer.py | CRITICAL | ✅ 추가발견 | respawn 시 agent 삭제→학습 소실 |
| BUG_010 | mafac_agent.py | MAJOR | ✅ 추가발견 | actor loop에서 baseline Q 4회 중복 계산 |
| BUG_011 | trainer.py | MINOR | ✅ 추가발견 | checkpoint 저장 실패 silent suppression |
| BUG_012 | federated.py | MINOR | ⚠️ 부분 | RSU 간 uniform avg → participant 불균형 무시 |
| BUG_013 | federated.py | MINOR | ⚠️ 부분 | federation 후 target_critic hard reset |

#### 수학적 정확성

| 항목 | 판정 |
|------|------|
| Lagrangian dual ascent | ✅ 정확 |
| Bellman backup (target_q) | ✅ 정확 (Lagrangian 형태) |
| Entropy regularization | ⚠️ 누락 (nlp 미사용) |
| Federated inverse-AoI weighting | ⚠️ within-RSU 정확, between-RSU uniform avg |
| cv 정의 (binary CBR > 0.65) | ✅ 양쪽 파일 일관 |
| Actor factored PG | ⚠️ hybrid action bias |

#### 3개월 추산 타당성
**타당함 (CONFIRMED).** 
- 50 agents × ~100-180ms/update × 3000 steps ≈ 4.2-7.5 hours/episode
- 500 ep × 4.2h = 2,083h ≈ 2.9개월

#### 수정 후 예상 속도 향상
- BUG_001 단독: **10-20× 가속** → 3개월 → 4-9일
- BUG_001 + BUG_003: **100-200× 가속** → 3개월 → 0.5-1.5일
- 전체 수정: **20-50× 보수적 추정** → 1.8-4.5일

#### 즉각 수정 우선순위
1. **BUG_001** (batch forward 1줄 수정) — 최대 ROI
2. **BUG_005 + BUG_006** (checkpoint/resume 시스템) — 현재 상황 직접 원인
3. **BUG_003** (update frequency) — 독립적 10× 추가 가속
4. **BUG_008** (actor advantage bias) — 수렴 안정성
5. **BUG_002 + BUG_010** (vectorization) — 추가 최적화

**상세 리포트:** `/home/imnyj/papers/paper2/paper/validation/validation_report.json`

---
