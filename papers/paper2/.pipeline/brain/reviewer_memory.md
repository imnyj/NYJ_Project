# Reviewer Memory — MAFAC 코드 구조 기록

업데이트: 2026-05-06 | 검증 ID: VALIDATION-MAFAC-001

---

## 코드 아키텍처 요약

### 파일 구조
```
simulation/
├── training/
│   └── trainer.py          # 학습 루프, checkpoint, federated 호출
├── agents/
│   ├── mafac_agent.py      # MAFACAgent (actor+critic+buffer+lagrange)
│   ├── federated.py        # FederatedAggregator (AoI-weighted FedAvg)
│   ├── centralized_agent.py
│   ├── sac_agent.py
│   ├── iql_agent.py
│   ├── ndn_lru_agent.py
│   └── no_cache_agent.py
├── env/
│   ├── sumo_env.py         # libsumo 환경 (MockSUMO fallback)
│   ├── ndn_layer.py        # NDN 캐싱 레이어
│   ├── channel_model.py    # Rician/Nakagami 채널
│   └── aoi_tracker.py      # AoI 추적기
├── utils/
│   ├── metrics.py          # EpisodeMetrics, compute_theorem1_bound 등
│   └── logger.py           # ExperimentLogger (CSV 저장)
└── run_full_simulation.py  # Phase 0~5 실행 스크립트
```

---

## 핵심 클래스/메서드 메모

### MAFACAgent (mafac_agent.py)
- `__init__`: obs_dim=14, action_dims=(3,2,5,50), batch_size=256, buffer=100K
- `FactoredActor`: encoder(14→128→128) + 4 heads → (3,2,5,50) logits
- `CentralizedCritic`: [obs(14) + action_oh(60)] → 256 → 256 → 1
- `_update_torch()`: 핵심 학습 루프
  - **병목 #1**: `for i in range(256): actor.get_action(next_obs[i:i+1])` — 반드시 배치로 교체
  - **병목 #2**: `_onehot_actions` 이중 루프 (4×256 Python iters)
  - **병목 #3**: actor loop에서 critic forward 8회 (4 sub-action × 2), 기준 Q 4회 중복
  - **수학 이슈**: nlp 미사용 (entropy 누락), hybrid action bias (acts_copy)
- `save_checkpoint()`: actor/critic/lambda/total_steps만 저장 (buffer/optimizer 미저장)
- `load_checkpoint()`: Trainer에서 호출되지 않음 (dead code for resume)

### Trainer (trainer.py)
- `_ensure_agents()`: 매 step obs를 보고 agent 생성/삭제. **버그**: respawn 차량 agent 삭제
- `_update_agents()`: 매 step 모든 50 agent update 호출 — **75M total updates**
- `_save_checkpoints()`: 50 ep마다, **첫 5개 agent만** 저장, silent error suppression
- `train()`: `for ep in range(1, total+1)` — resume 불가

### FederatedAggregator (federated.py)
- `aggregate_at_rsu()`: inverse-AoI weight → 정규화 → 가중 평균 ✅
- `aggregate_rsu_models()`: RSU 간 **uniform 1/N 평균** (participant 수 무시) ⚠️
- `run_federation_round()`: 10 episode마다 호출, critic만 집계, actor는 local
- `set_critic_params()` (in mafac_agent.py): critic + target_critic 동시 hard reset ⚠️

### SUMOEnv (sumo_env.py)
- obs_dim = 14 (9 base + 5 neighbor AoI)
- action_dims = (3, 2, 5, 50) = sum 60 → one-hot 60차원
- `_respawn_vehicle()`: 동일 vid로 재삽입 → trainer._ensure_agents()와 충돌 가능
- `get_observations()`: O(N²) neighbor search (50×50=2500 distance calc/step)
- CBR_THRESH = 0.65, cv = binary (cbr > 0.65)
- WARMUP_STEPS = 1000 (100s), episode_duration_s = 300s → max_steps = 3000

---

## 알고리즘 수학적 정확성 메모

| 구성요소 | 구현 | 표준 | 판정 |
|----------|------|------|------|
| Lagrangian λ update | max(0, λ + α(cv - 0.65)) | max(0, λ + α∇_λL) | ✅ |
| Bellman target_q | r - λ*c + γ(1-d)*V_target | r - λ*c + γ(1-d)*V_target | ✅ |
| Entropy term | 미포함 (nlp 버려짐) | Q(s',a') - α*log_π(a'\|s') | ⚠️ |
| Factored PG | hybrid action (j≠i은 buffer) | all dims from current π | ⚠️ BIASED |
| AoI federated weight | 1/(AoI+1e-6), normalized | 동일 | ✅ within-RSU |
| RSU 간 집계 | uniform 1/N | participant-weighted | ⚠️ |
| cv 정의 | binary (cbr > 0.65) | idea_spec 동일 | ✅ |

---

## Phase 2 성능 추산

- 구성: 50 agents, 500 ep, 3000 step/ep, batch=256
- 총 gradient updates: **75,000,000회**
- 추산 update당 시간(CPU): ~100-180ms (BUG_001이 주요 원인)
- 추산 학습 시간: **2.9-6.4개월** (3개월 추산 타당)
- BUG_001+003 수정 후: **1.8-4.5일** (20-50× 가속)

---

## 수정 우선순위 (알고리즘 동등성 유지)

1. **BUG_001** (mafac_agent.py, 256-loop → batch forward) — 3줄 수정, 43× 가속
2. **BUG_005+006** (checkpoint 전체 저장 + resume 로직) — 즉시 작업 재개 가능
3. **BUG_003** (update frequency: every 10 step) — 10× 추가 가속  
4. **BUG_009** (respawn agent 삭제 금지) — 학습 연속성 보장
5. **BUG_010** (baseline Q cache) — 4 critic forward → 1 (2.5×)
6. **BUG_002** (_onehot vectorize) — 추가 1.1-1.5×
7. **BUG_008** (actor hybrid action bias) — gradient 정확도 개선

---

## 파일 경로 참조

- 검증 리포트: `/home/imnyj/papers/paper2/paper/validation/validation_report.json`
- 검증 이력: `/home/imnyj/papers/paper2/.pipeline/annotations/validation_history.md`
- 코드 베이스: `/home/imnyj/papers/paper2/simulation/`
