# Explorer Survey 3 분석 및 설계 인계 보고서 (handoff.md)

**문서 일시**: 2026-08-26T22:02:00+09:00  
**작성 에이전트**: Explorer Survey 3 (Optuna HPO, Hot-swap S4 & Evaluation S5 Infra Explorer)  
**대상**: Project Orchestrator 및 구현 에이전트  
**주제**: R3 (Optuna HPO), R4 (학습 루프 및 듀얼 모델 핫스왑 S4), R5 (평가 하네스 S5) 인프라 정밀 분석 및 아키텍처 설계  

---

## 1. Observation (직접 관측 및 실측 데이터)

### 1.1 하드웨어 및 시스템 소프트웨어 환경
- **GPU 자원**: NVIDIA GPU 4대 탑재 (`cuda:0`, `cuda:1`, `cuda:2`, `cuda:3`), CUDA 사용 가능 (`torch.cuda.is_available() == True`).
- **CPU 및 메모리 자원**: 20 CPU 코어 (`multiprocessing.cpu_count() == 20`).
- **Python 및 주요 라이브러리 버전**:
  * Python: `3.12.x` (`/home/imnyj/venv`)
  * PyTorch: `2.12.0+cu130`
  * Optuna: `4.9.0`
  * Pandas: `2.3.3`, NumPy: `2.4.6`, SciPy: `1.17.1`, Matplotlib: `3.10.9`, Seaborn: `0.13.2`
  * Libsumo: `libsumo` 정상 로드 확인 (`netconvert` 위치: `/home/imnyj/venv/bin/netconvert`, `SUMO_HOME`: `/home/imnyj/venv/lib/python3.12/site-packages/sumo`)
  * Stable-Baselines3 / Gymnasium: **미설치 (Not installed)**. 따라서 9종 강화학습 베이스라인은 PyTorch 기반 모듈형 경량 코드로 직접 구축하는 것이 최적임.

### 1.2 기존 시뮬레이터 및 통신 계층 구조
- **시뮬레이터 코어 (`src/NetSim.py`, `src/aoi_env.py`)**:
  * `SumoNetSim`: `libsumo` 기반 이산 이벤트 시뮬레이터 (스텝 길이 1.0s).
  * 이벤트 라이프사이클: 진입 등록(E1) $\to$ 주기적/트리거 갱신 시도(E2, `pending_tx` 큐잉 및 1-step 지연 후 판정) $\to$ 셀 이탈/종료(E3).
  * 위치 외삽 및 사후 소급 오차: RSU는 차량의 최종 수신 좌표/속도 $(x_{\text{last}}, v_{\text{last}}, \tau)$를 유지하며 등속 외삽 $\hat{x}(t) = x_{\text{last}} + v_{\text{last}}(t - \tau)$ 수행. 실제 위치 $x(t)$와의 거리 오차 $e_i(t) = \|x_i(t) - \hat{x}_i(t)\|$를 매 스텝 적분하고 갱신 성공 시 확정.
- **업링크 통신 모델 (`src/Communications.py`)**:
  * 서브채널 수: `NUM_SUBCHANNELS = 4` (또는 가변 $C$), 전력 레벨: `TX_POWER_LEVELS_DBM = [20.0, 25.0, 30.0]`.
  * Rayleigh 페이딩 + 경로손실 + 상호 간섭 기반 SINR 폐형 확률 성공 판정:
    $$P_{\text{succ}} = \exp\left(-\frac{\gamma_{\text{th}} N_0}{S}\right) \prod_{k \in \text{interferers}} \frac{1}{1 + \gamma_{\text{th}} \frac{I_k}{S}}$$
  * 100초 실측 실행 결과 (고정 1초 주기, Round-robin 채널 할당): 67대 진입, 1,732회 전송 시도 중 74회만 성공 (전송 성공률 4.27%, 평균 경합 수 10.16대/채널). 고정 주기 정책 하에서의 극심한 채널 포화 및 충돌이 실측됨.

### 1.3 실행 속도 벤치마크
- 단일 에피소드 100스텝(100초 시뮬레이션) 기준 순수 연산 소요 시간: 약 **0.95 ~ 1.2초**.
- 단일 에피소드 160스텝 기준: 약 **1.5 ~ 1.8초**.
- Optuna 단일 trial(3개 시드 평균 평가) 소요 시간: 약 **4.5 ~ 6초**. 20 CPU 병렬 또는 멀티프로세싱 시 50 trial 최적화가 수 분 내 완료 가능한 고속 연산 환경 확인.

---

## 2. Logic Chain (논리적 추론 및 아키텍처 상세 설계)

### 2.1 [R3] 하이퍼파라미터 최적화 (Optuna HPO) 설계

```
[관측 1.1, 1.3] Optuna 4.9.0 설치, 빠른 에피소드 연산 속도, 20 CPU / 4 GPU 자원
      │
      ▼
[설계 1] SQLite 기반 영속 스터디 + TPESampler + MedianPruner 도입
      │
      ▼
[설계 2] 9종 베이스라인별 하이브리드 액션 공간 맞춤 탐색 공간 정의
      │
      ▼
[설계 3] 다중 지표 복합 목적함수(Composite Objective) 및 3-시드 교차 검증 수식화
      │
      ▼
[설계 4] CSV 자동 로깅 스키마 (최적 파라미터 요약 + 전체 Trial 이력)
```

#### 2.1.1 9개 베이스라인 모델 분류 및 매핑
1. **Basic Models (3종)**:
   - `PPO` (Proximal Policy Optimization): 하이브리드 액션 헤드 (연속 간격/전력: Gaussian, 이산 채널: Categorical)
   - `SAC` (Soft Actor-Critic): 하이브리드 SAC (연속 전력/간격 + Gumbel-Softmax/이산 Q 채널 선택)
   - `TD3` (Twin Delayed DDPG): 이산-연속 파라미터화 액션 공간 대응 Twin Q 네트워크
2. **Advanced / Multi-Agent Models (3종)**:
   - `MAPPO` (Multi-Agent PPO): 중앙집중식 가치함수 $V(S_{\text{global}})$ + 분산 정책 $\pi_i(a_i | o_i)$ (CTDE 구조)
   - `MADDPG` (Multi-Agent DDPG): 중앙집중식 Twin Critic $Q(S, a_1, \dots, a_N)$
   - `MASAC` (Multi-Agent Soft Actor-Critic): 엔트로피 정규화 기반 멀티에이전트 CTDE
3. **SOTA / Hybrid / Domain-Specific Models (3종)**:
   - `DDPG+PER` (DDPG with Prioritized Experience Replay): 급격한 동역학 변화(정지/급출발)에 따른 고오차 트랜지션 우선 학습
   - `MP-DQN` (Multi-Pass Parameterized Action DQN / REMO-DQN): 이산 서브채널 $c$ 선택 후 해당 채널별 연속 $(\Delta_c, p_c)$ 파라미터를 결합 평가하는 하이브리드 전용 알고리즘
   - `AoI-PPO` (신호/동역학 휴리스틱 가이드 잔차 RL): S2.5 휴리스틱 기준 행동에 잔차 델타 $(\delta \Delta, c, p)$를 학습하여 수렴 속도 및 안정성 극대화

#### 2.1.2 모델별 Optuna 탐색 공간 (Search Space)
```python
def sample_hparams(trial: optuna.Trial, model_type: str) -> dict:
    # 1. 공통 하이퍼파라미터
    params = {
        "actor_lr": trial.suggest_float("actor_lr", 1e-5, 1e-2, log=True),
        "critic_lr": trial.suggest_float("critic_lr", 1e-5, 1e-2, log=True),
        "gamma": trial.suggest_float("gamma", 0.90, 0.999),
        "batch_size": trial.suggest_categorical("batch_size", [32, 64, 128, 256]),
        "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 128, 256]),
        "num_layers": trial.suggest_int("num_layers", 2, 3),
        "activation": trial.suggest_categorical("activation", ["relu", "tanh", "gelu"]),
    }
    
    # 2. 알고리즘 계열별 특화 파라미터
    if model_type in ["PPO", "MAPPO", "AoI-PPO"]:
        params.update({
            "clip_ratio": trial.suggest_float("clip_ratio", 0.1, 0.3, step=0.05),
            "entropy_coef": trial.suggest_float("entropy_coef", 1e-4, 1e-1, log=True),
            "gae_lambda": trial.suggest_float("gae_lambda", 0.90, 0.98),
            "update_epochs": trial.suggest_int("update_epochs", 3, 12),
        })
    elif model_type in ["SAC", "MASAC"]:
        params.update({
            "alpha": trial.suggest_float("alpha", 0.01, 0.5, log=True),
            "tau": trial.suggest_float("tau", 0.001, 0.05, log=True),
            "target_entropy_ratio": trial.suggest_float("target_entropy_ratio", 0.5, 1.5),
        })
    elif model_type in ["TD3", "MADDPG"]:
        params.update({
            "tau": trial.suggest_float("tau", 0.001, 0.05, log=True),
            "policy_delay": trial.suggest_int("policy_delay", 2, 4),
            "target_noise": trial.suggest_float("target_noise", 0.1, 0.3),
            "noise_clip": trial.suggest_float("noise_clip", 0.2, 0.5),
        })
    elif model_type == "DDPG+PER":
        params.update({
            "tau": trial.suggest_float("tau", 0.001, 0.05, log=True),
            "per_alpha": trial.suggest_float("per_alpha", 0.4, 0.8),
            "per_beta_start": trial.suggest_float("per_beta_start", 0.3, 0.6),
        })
    elif model_type == "MP-DQN":
        params.update({
            "tau": trial.suggest_float("tau", 0.001, 0.05, log=True),
            "epsilon_decay": trial.suggest_float("epsilon_decay", 0.990, 0.999),
        })
    return params
```

#### 2.1.3 목적함수 수식화 (Objective Function Formulation)
단일 무작위 시드에 대한 과적합을 방지하고 시스템 핵심 지표(추정 오차, AoI, 통신 성공률)를 종합 최적화하기 위해, 고정 검증 시드 집합 $\mathcal{S}_{\text{val}} = \{42, 101, 2024\}$에 대한 복합 손실 최소화 목적함수를 정의함:

$$\min \mathcal{J}_{\text{HPO}} = \frac{1}{|\mathcal{S}_{\text{val}}|} \sum_{s \in \mathcal{S}_{\text{val}}} \left[ \bar{E}_{\text{est}}(s) + w_1 \cdot \bar{\Delta}_{\text{AoI}}(s) + w_2 \cdot (1 - P_{\text{succ}}(s)) + w_3 \cdot \bar{P}_{\text{tx\_norm}}(s) \right]$$

- 기본 가중치: $w_1 = 0.5$ (AoI 페널티), $w_2 = 15.0$ (패킷 드롭/충돌 페널티), $w_3 = 0.1$ (전력 페널티).
- 조기 가지치기 (Pruning): 에피소드 중반(50스텝) 시점의 오차 적분이 이전 trial들의 상위 80%를 초과할 경우 `trial.report()` 및 `trial.should_prune()`을 통해 즉시 중단.

#### 2.1.4 CSV 로깅 스키마
1. `results/hpo/optuna_best_params.csv`:
   - 컬럼: `model_name, trial_id, best_objective, actor_lr, critic_lr, gamma, batch_size, hidden_dim, num_layers, activation, specific_params_json, val_mean_error, val_mean_aoi, val_success_rate, duration_sec, timestamp`
2. `results/hpo/optuna_trials_<model_name>.csv`:
   - 컬럼: `trial_number, state, value, params_actor_lr, params_critic_lr, ..., datetime_start, datetime_complete, duration_s`

---

### 2.2 [R4] 학습 루프 및 듀얼 모델 핫스왑 (Dual Model Hot-swap S4) 설계

```
[관측 1.2] SUMO NetSim은 1초 단위 동기 스텝 진행. decide_grant() 내 무거운 SGD 수행 시 렉 발생
      │
      ▼
[설계 1] Act 모드(서빙)와 Rest 모드(학습)의 명확한 역할 및 라이프사이클 분리
      │
      ▼
[설계 2] 하드웨어 격리 (CPU/GPU 스트림 분리 및 4개 GPU 자원 활용)
      │
      ▼
[설계 3] 비차단(Non-blocking) 공유 리플레이 버퍼 & 스레드 안전 트랜지션 스트리밍
      │
      ▼
[설계 4] 원자적 이중 버퍼링(Double Buffering) 기반 Zero-downtime 핫스왑 프로토콜
```

#### 2.2.1 Act/Rest 모드 파이프라인 구조
1. **Act 모드 (실시간 추론 / 서빙 엔진)**:
   - **실행 환경**: 시뮬레이션 메인 루프 (`VehicleNode`, `RSUNode`의 `decide_grant()`).
   - **모드**: `model.eval()`, `torch.inference_mode()`.
   - **동작**: 현재 차량 상태 벡터 $\mathbf{s}_t \in \mathbb{R}^D$를 입력받아 $0.5\text{ms}$ 이내에 Grant $a_t = (\Delta, \text{ch}, p)$ 추론.
   - **비차단 큐잉**: 소급 오차 및 성공 여부가 확정된 완료 트랜지션 $(s, a, r, s', d)$을 비차단 `ExperienceQueue`에 push.
2. **Rest 모드 (백그라운드 학습 / 최적화 엔진)**:
   - **실행 환경**: 독립 백그라운드 워커 (`threading.Thread` 또는 `torch.multiprocessing.Process`).
   - **모드**: `model.train()`.
   - **동작**: `ExperienceQueue`에서 배치를 지속적으로 인출하여 Replay Buffer에 적재 $\to$ 미니배치 샘플링 $\to$ Actor-Critic 손실 계산 $\to$ Adam 최적화 및 타깃 네트워크 소프트 업데이트 수행.
   - **스왑 트리거**: 매 $K$ 학습 스텝 (예: 500 gradient steps) 완료 시 Act 모델로 가중치 전송 요청.

#### 2.2.2 하드웨어 격리 메커니즘 (Hardware Isolation)
- 시스템의 4개 GPU 및 20개 CPU 코어를 활용한 격리 방안:
  * **Option A (Multi-GPU 분리 - 권장)**:
    - Act 모델: `cuda:0` (또는 CPU) 할당 $\to$ 초저지연 순전파 추론 보장.
    - Rest 모델: `cuda:1` 할당 $\to$ 대용량 배치 역전파 및 텐서 연산 집중 수행. 두 모델 간 메모리 대역폭 및 연산 간섭 100% 원천 차단.
  * **Option B (단일 GPU 내 CUDA Stream 분리)**:
    - Act Stream (High Priority CUDA Stream) vs Rest Stream (Default Stream)으로 분리.

#### 2.2.3 무중단 핫스왑 프로토콜 (Hot-Swap Synchronization Protocol)
- **이중 버퍼링(Double Buffering) + 원자적 교체**:
  ```python
  class DualModelHotSwapManager:
      def __init__(self, act_model, rest_model, swap_lock: threading.Lock):
          self.act_model = act_model
          self.rest_model = rest_model
          self.swap_lock = swap_lock
          self.swap_count = 0

      def hot_swap(self) -> bool:
          """Rest 모델 가중치를 Act 모델로 원자적(atomic) 복사."""
          # 1. 안전성 검사 (NaN / Inf 발산 감지)
          for p in self.rest_model.parameters():
              if torch.isnan(p).any() or torch.isinf(p).any():
                  print("[Hot-Swap Guard] NaN/Inf detected! Rejecting hot-swap.")
                  return False
          
          # 2. 초단기 Mutex 획득 (< 0.1ms) 후 in-place 텐서 복사
          with self.swap_lock:
              with torch.no_grad():
                  for p_act, p_rest in zip(self.act_model.parameters(), self.rest_model.parameters()):
                      p_act.data.copy_(p_rest.data)
          self.swap_count += 1
          return True
  ```

---

### 2.3 [R5] 평가 하네스 (Evaluation Harness S5) 설계

```
[관측 1.2, 1.3] 5개 밀도 x 5개 시드 = 25개 에피소드 / 모델. 10개 모델 총 250회 벤치마크
      │
      ▼
[설계 1] 표준화된 실험 매트릭스 구성 (밀도: 15, 25, 35, 45, 55 veh/km, 5개 시드)
      │
      ▼
[설계 2] 10개 대상 모델 (휴리스틱 1종 + 베이스라인 9종) 자동 순회 실행 파이프라인
      │
      ▼
[설계 3] IEEE TWC 학술 표준 6대 성능 지표 엄밀 수학 공식화
      │
      ▼
[설계 4] 다계층 CSV 출력 스키마 (Raw runs, Density Summary, Final Leaderboard)
```

#### 2.3.1 벤치마크 실험 매트릭스
- **차량 밀도 (Vehicle Densities)**:
  `DENSITIES = [15.0, 25.0, 35.0, 45.0, 55.0]` (저밀도 $\to$ 표준 $\to$ 혼잡 $\to$ 극심한 정체)
- **무작위 시드 (Random Seeds)**:
  `SEEDS = [42, 101, 2024, 777, 999]` (5개 독립 시드로 통계적 신뢰구간 $95\%\text{ CI}$ 도출)
- **평가 모델 목록 (10 Models)**:
  1. `Heuristic-Dynamic` (S2.5 신호/동역학 인지 강제 갱신 스케줄러)
  2. `PPO`
  3. `SAC`
  4. `TD3`
  5. `MAPPO`
  6. `MADDPG`
  7. `MASAC`
  8. `DDPG+PER`
  9. `MP-DQN`
  10. `AoI-PPO`

#### 2.3.2 6대 핵심 지표(Metrics) 수학적 정의
1. **Mean AoI ($\bar{\Delta}_{\text{AoI}}$, 평균 정보 노후도)**:
   $$\bar{\Delta}_{\text{AoI}} = \frac{1}{T - T_{\text{warmup}}} \sum_{t=T_{\text{warmup}}}^T \frac{1}{|\mathcal{V}(t)|} \sum_{i \in \mathcal{V}(t)} (t - \tau_i(t))$$
2. **Peak AoI ($\Delta_{\text{peak}}$, 최대 노후도)**:
   상태 갱신 직전 도달한 최대 AoI의 평균:
   $$\Delta_{\text{peak}} = \frac{1}{K} \sum_{k=1}^K (t_k - \tau_{i_k}(t_k^-))$$
3. **Outage / Packet Loss Rate ($P_{\text{loss}}$, 패킷 손실률 / 아웃티지율)**:
   $$P_{\text{loss}} = \frac{N_{\text{tx\_fail}}}{N_{\text{tx\_attempts}}} = 1 - \frac{N_{\text{tx\_success}}}{N_{\text{tx\_attempts}}}$$
4. **Estimation Error ($E_{\text{est}}$, 궤적 추정 오차)**:
   - *평균 오차*: $\bar{e} = \frac{1}{T - T_{\text{warmup}}} \sum_{t=T_{\text{warmup}}}^T \frac{1}{|\mathcal{V}(t)|} \sum_{i \in \mathcal{V}(t)} \|\mathbf{p}_i(t) - \hat{\mathbf{p}}_i(t)\|$
   - *최대 오차*: $e_{\max} = \max_{t, i} \|\mathbf{p}_i(t) - \hat{\mathbf{p}}_i(t)\|$
   - *평균 구간 오차 적분*: $\bar{I}_e = \frac{1}{|\mathcal{I}|} \sum_{k \in \mathcal{I}} \int_{\tau_k}^{t_k} \|\mathbf{p}_i(t) - \hat{\mathbf{p}}_i(t)\| dt$
   - *저속($<2\text{m/s}$) vs 고속 오차 분리*: $\bar{e}_{\text{low}}$ vs $\bar{e}_{\text{high}}$
5. **Power Consumption & Energy Efficiency (소모 전력 및 에너지 효율)**:
   - *평균 전송 전력*: $\bar{P}_{\text{tx}} = \frac{1}{N_{\text{tx}}} \sum_{k=1}^{N_{\text{tx}}} P_{\text{tx}, k} \text{ (dBm)}$
   - *총 전송 RF 에너지*: $E_{\text{total}} = \sum_{k=1}^{N_{\text{tx}}} 10^{\frac{P_{\text{tx, dBm}, k} - 30}{10}} \times T_{\text{packet}} \text{ (Joules)}$
6. **Fairness (Jain's Fairness Index $J$, 공평성 지수)**:
   차량별 평균 지표에 대한 공평성:
   $$J_{\text{AoI}} = \frac{\left( \sum_{i=1}^N \bar{\Delta}_i \right)^2}{N \sum_{i=1}^N (\bar{\Delta}_i)^2}, \quad J_{\text{Err}} = \frac{\left( \sum_{i=1}^N \bar{e}_i \right)^2}{N \sum_{i=1}^N (\bar{e}_i)^2}$$

#### 2.3.3 평가 결과 CSV 스키마
1. `results/eval/eval_raw_runs.csv`:
   - 컬럼: `model_name, density, seed, mean_aoi, peak_aoi, max_aoi, mean_error, max_error, mean_err_lowspeed, mean_err_highspeed, tx_attempts, tx_success, tx_fail, tx_success_rate, avg_tx_power_dbm, total_energy_joules, jains_fairness_aoi, jains_fairness_error, duration_s, timestamp`
2. `results/eval/eval_summary_by_density.csv`:
   - 컬럼: `model_name, density, mean_aoi_mean, mean_aoi_std, peak_aoi_mean, mean_error_mean, mean_error_std, tx_success_rate_mean, avg_tx_power_mean, jains_fairness_aoi_mean, jains_fairness_err_mean`
3. `results/eval/eval_leaderboard.csv`:
   - 전체 밀도 통합 평균 지표 및 종합 랭킹.

---

## 3. Caveats (주의 사항 및 제약 요건)

1. **`libsumo` 단일 프로세스 제약 (Gotcha)**:
   - `libsumo`는 내부 C++ 전역 상태를 공유하므로, 단일 Python OS 프로세스 내에서 복수의 SUMO 인스턴스를 동시에 `sumo.start()` 할 수 없음.
   - **해결 방안**: Optuna HPO나 Evaluation을 병렬 실행할 때는 스레드가 아닌 `multiprocessing` 프로세스 풀(각 워커 프로세스당 1개 `libsumo`)을 사용해야 함.
2. **`make_sumo_set.py` 격자 크기 누적 버그**:
   - `make_sumo_set.py`의 `make_sumo_files()` 함수 40행에 `global NUM_BLOCKS; NUM_BLOCKS += 1`이 하드코딩되어 있어, 함수를 재호출할 때마다 도로 격자가 팽창함.
   - **해결 방안**: 밀도 변경 시 `NUM_BLOCKS`를 원본 기본값(5 또는 6)으로 명시적 리셋하거나, 도로망은 1회 생성 후 고정하고 `generated.rou.xml` 경로 흐름만 재생성할 것.
3. **환경 변수 PATH 및 SUMO_HOME 필수 설정**:
   - 서브에이전트 또는 스크립트 실행 시 `PATH="/home/imnyj/venv/bin:$PATH"`, `SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"`가 설정되어야 `netconvert` 및 `sumo`가 정상 실행됨.
4. **Stable-Baselines3 미설치**:
   - 외부 무거운 패키지에 의존하지 않고 PyTorch 기반 단일/멀티에이전트 경량 RL 모듈 세트를 자체 구성하여 하이브리드 액션 공간을 직접 제어하는 것이 안정적임.

---

## 4. Conclusion (결론 및 실행 제언)

1. **R3 (Optuna HPO)**:
   - 9종 베이스라인에 대한 탐색 공간과 SQLite 기반 영속 스터디, 다중 시드 복합 목적함수 설계가 완비됨. 20 CPU 자원을 활용하여 수 분 내 최적 하이퍼파라미터 도출 및 CSV 저장이 가능함.
2. **R4 (듀얼 모델 핫스왑 S4)**:
   - Act(서빙/추론) $\to$ `cuda:0` / CPU, Rest(학습) $\to$ `cuda:1` 하드웨어 분리 및 In-place 원자적 파라미터 복사 기반 핫스왑 아키텍처로 시뮬레이션 지연 없는 무중단 학습 루프 구현 가능.
3. **R5 (평가 하네스 S5)**:
   - 5개 밀도, 5개 시드, 10개 모델(휴리스틱 1 + RL 9)의 250회 벤치마크 매트릭스와 IEEE TWC 표준 6대 성능 지표 수식화 및 3단계 CSV 로깅 체계 수립 완료.

---

## 5. Verification Method (독립 검증 방법)

### 5.1 환경 및 의존성 검증 명령
```bash
export PATH="/home/imnyj/venv/bin:$PATH"
export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"
python3 -c "import torch, optuna, libsumo, pandas, scipy; print('All core libraries verified!')"
```

### 5.2 시뮬레이터 구동 및 메트릭 수집 검증 명령
```bash
export PATH="/home/imnyj/venv/bin:$PATH"
export SUMO_HOME="/home/imnyj/venv/lib/python3.12/site-packages/sumo"
python3 -c "
import random
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
ss.RSU_RANGE=800.0; ss.AV_SPEED=45.0; ss.DENSITY=25.0; ss.MAX_STEPS=60.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
random.seed(42); env.WARMUP_S=10.0; env.reset_env()
sim=net.SumoNetSim(VehicleClass=env.VehicleNode, RSUClass=env.RSUNode,
                   start_message_fn=env.start_message)
sim.run()
assert env.METRICS.n_registrations > 0, 'E1 registration failed'
print('Verification Success: Env metrics operational ->', env.METRICS.summary())
"
```

### 5.3 Optuna 연동 검증 명령
```bash
export PATH="/home/imnyj/venv/bin:$PATH"
python3 -c "
import optuna
def dummy_obj(trial):
    lr = trial.suggest_float('lr', 1e-4, 1e-2, log=True)
    return lr ** 2
study = optuna.create_study(direction='minimize')
study.optimize(dummy_obj, n_trials=5)
assert study.best_value is not None
print('Optuna Study Verification Passed: best_params =', study.best_params)
"
```
