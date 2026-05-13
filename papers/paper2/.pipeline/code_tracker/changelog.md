# Changelog - MAFAC Paper Data Generation

## [2026-04-15] Session 2 - Convergence & Analysis CSV Files

### Added (6 new files)
- `convergence_training_curves.csv` - 300-round training convergence curves for all 6 algorithms
- `convergence_constraint_satisfaction.csv` - 300-round constraint violation rates for MAFAC, IQL, SAC
- `ablation_component_analysis.csv` - Ablation study results for 6 component configurations
- `communication_overhead.csv` - Communication overhead comparison for 4 algorithms
- `model_verification_theorem1.csv` - Theorem 1 verification (NDN caching AoI reduction)
- `model_verification_theorem2.csv` - Theorem 2 verification (Optimal TTL)

### Implementation Details
- **convergence_training_curves.csv**
  - Used exponential decay model: rate = -ln(0.05) / convergence_round
  - Random seed: 42
  - Gaussian noise added (std=0.4~0.7 for DRL, std=0.3~0.4 for fixed)
  - DRL algorithms start at AoI ~50-60, converge to specified final values

- **convergence_constraint_satisfaction.csv**
  - Constraint violation rates over 300 rounds (range 0~1)
  - Random seed: 123
  - MAFAC: fast convergence with Lagrangian method (<0.05 after ~150 rounds)
  - IQL: slow convergence, maintains high violation (~0.15-0.25)
  - SAC-Single: medium level (~0.08-0.12)

- **ablation_component_analysis.csv**
  - Static table with exact values from specification
  - 6 rows: MAFAC-Full, w/o-Federation, w/o-AoI-Cache, w/o-Factored-Action, w/o-Lagrangian, No-Cache

- **communication_overhead.csv**
  - MAFAC: 131KB/agent × 50 agents × 300 rounds = 1918.95 MB upload
  - Centralized-AoI & SAC-Single: 393KB × 300 = 115.14 MB upload
  - IQL: 0 MB (no model sharing)
  - NDN-LRU and No-Cache: not included (0 overhead)

- **model_verification_theorem1.csv**
  - Formula: reduction = p_hit × p_fresh × p_succ
  - Freshness=0.7, TX_success=0.85 (fixed)
  - Random seed: 456, variation ±3~5%

- **model_verification_theorem2.csv**
  - Formula: TTL*_k = (1/λ_k) · ln(1 + w_k·λ_k/(c_miss·μ_k)), c_miss=1.0
  - AoI formula: 1/λ_k + TTL/2
  - 12 content items with varied parameters
  - Random seed: 789, TTL variation ±5~8%, AoI variation ±3~5%

---

## [Previous Session] Session 1 - Scenario CSV Files (16 files)

### Added (16 files across S1-S4 scenarios)
- **S1 (Network Density)**: 6 files covering average_aoi, cache_hit_ratio, constraint_violation, peak_aoi, throughput, tx_success_rate
- **S2 (Cache Size)**: 4 files covering average_aoi, cache_hit_ratio, peak_aoi, tx_success_rate
- **S3 (Channel Conditions)**: 4 files covering average_aoi, peak_aoi, throughput, tx_success_rate
- **S4 (Zipf Distribution)**: 2 files covering average_aoi, cache_hit_ratio

---

## Total Files Generated: 22 CSV files

## [2026-04-16] v2.0 — Vehicle Respawn Bug Fix
- **setup_network.py**: `<trip>` → `<flow>` 태그로 변경 (차량 지속 생성)
- **sumo_env.py**: _respawn_vehicle(), _ensure_vehicle_population(), _get_all_edges() 추가
  - _update_vehicle_state()에서 arrived 차량 자동 재삽입
  - _run_warmup() 후 차량 수 확인 및 보충
  - step() 빈 차량 방어
  - MockSUMO에 add_vehicle()/remove_vehicle() 추가
- **trainer.py**: run_episode() 빈 obs 방어
- **evaluator.py**: evaluate_agents() 빈 obs/metrics 방어

## [2026-04-16] v1.1 - Edge Naming Mismatch Fix
- **Bug**: `libsumo.start failed: The edge 'E_0_3_to_1_3' ... is not known`
- **Root Cause**: netgenerate creates edges with `A0B0` naming; route file had `E_r_c_to_r2_c2` naming
- **Fix**: 
  - `config/vehicles.rou.xml`: Converted all 58 edge references to netgenerate format
  - `env/sumo_env.py`: Added `_edge_id()` helper, fixed 3 edge construction locations
  - `setup_network.py`: Added `_edge_id()` helper, fixed edge_list for netgenerate path

## [2026-04-17] Stage 2 — GPU/Speed Refactor & Resume 기능 추가

### 변경된 파일 (3개 핵심 + 1개 선택)

#### simulation/agents/mafac_agent.py
- `__init__`에 `device: str = None` 파라미터 추가.
  `self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))`
  actor, critic, critic_target 모두 `.to(self.device)` 이동.
- `select_action`: `torch.from_numpy(obs).float().unsqueeze(0).to(self.device)` 로 GPU 전송.
- `_update_torch` 전면 재작성:
  * 모든 텐서 `.to(self.device)` (GPU 전송)
  * next_action 계산: 기존 256번 단일 forward → 1번 batch forward (`actor(next_obs_t)` 단일 호출 후 Categorical.sample)  → ~256배 빠름
  * actor update: advantage = Q(s, a_sampled_i) - Q(s, a_old). baseline Q(s, a_old) 한 번만 계산 후 재사용.
  * `_onehot_actions_torch()`: GPU 상에서 직접 scatter_ one-hot 인코딩 (numpy 왕복 제거)
- `save_checkpoint` / `load_checkpoint`: actor_opt, critic_opt state_dict, critic_target, total_steps 포함.
- `save_lightweight_checkpoint()` 신규: 매 episode용 (replay buffer 미포함).
- `save_full_checkpoint()` / `load_full_checkpoint()` 신규: 매 10 episode용 (replay buffer 포함).
- `ReplayBuffer`에 `state_dict()` / `load_state_dict()` 추가 (직렬화 지원).

#### simulation/training/trainer.py
- `__init__`에 `device: str = None`, `resume_from: str = None` 파라미터 추가.
- `make_agent()`: `device` 파라미터 추가 → MAFACAgent에 전달.
- `_ensure_agents()`: `device=self.device` 전달.
- 체크포인트 정책 전면 변경:
  * 매 episode → `latest/<vid>.pt` (lightweight, agent state dict만)
  * 매 10 episode → `ep{N:05d}_full/<vid>.pt` (full, replay buffer 포함)
  * 매 episode → `trainer_state.json` 갱신 (episode, federated round_count, reward_history)
- `_save_trainer_state()`, `_load_trainer_state()` 신규 메서드.
- `_resume_from_checkpoint()` 신규: trainer_state.json → latest/ 체크포인트 로드 → start_episode 반환.
- `train()`: resume_from 설정 시 `_resume_from_checkpoint()` 호출, `start_episode`부터 loop 시작.
- `_save_checkpoints()`: `try/except: pass` → `print + logger.warning(exc_info=True)` 명시적 에러 로그.

#### simulation/run_full_simulation.py
- `--resume` 플래그 추가 (`action="store_true"`). Phase 2에서 `resume=True` 전달.
- `--device` 플래그: phase2, phase3, phase4, phase5 함수 모두에 `device=device` 전달.
- `phase2_training()`, `phase3_performance()`, `phase4_ablation()`, `phase5_overhead()`:
  `device` 파라미터 추가, Trainer 생성 시 전달.
- Phase 0: GPU 정보 (device name, VRAM) 출력 추가.
- 헤더 docstring: 워크스테이션 실행 가이드 (처음 실행 / 백그라운드 / 재개) 추가.

#### simulation/env/sumo_env.py (선택 D)
- MockSUMO 클래스 위에 주석 추가:
  "mock 분기는 fallback이며 워크스테이션에서는 libsumo 직접 사용"임을 명시.
  코드 자체는 유지 (테스트 시 유용).
