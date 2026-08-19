# R1 환경 및 모델 물리적 구현 전수 조사 보고서 (Handoff Report)

## 1. Observation (직접 관찰 사실)

### 1.1 SUMO 네트워크 환경 설정 파일 위치 및 구조
- **원본 SUMO 환경 생성기 및 템플릿**:
  - 파일 경로: `/home/imnyj/SumoNetSim1.1.5/src/sumo/make_sumo_set.py`
  - 관련 XML 파일들:
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.sumocfg`: SUMO 메인 실행 설정 (Net, Route, Additional, RSU POI 참조).
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.nod.xml`, `generated.edg.xml`: 노드 및 엣지 정의.
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.net.xml`: `netconvert`로 빌드된 Urban Grid 도로망.
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.rou.xml`: TAZ 기반 출발/도착 플로우 및 확률 기반 차량 발생 (`<flow id="F{i}_{j}" ...>`).
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/generated.add.xml`: TAZ (Traffic Assignment Zones) 소스/싱크 정의.
    - `/home/imnyj/SumoNetSim1.1.5/src/sumo/rsu.poi.xml`: 노변 기지국(RSU) 위치 정보.
  - **핵심 환경 제어 파라미터 (Control Variables)**:
    - `OUTAGE_ZONE = 800` (음영 구역 크기, m)
    - `AV_SPEED = 40` (평균 차량 속도, km/h; `0` 설정 시 10~120 km/h 범위 내 균등 무작위 할당)
    - `DENSITY = 20` (차량 밀도, veh/1km-lane; `0` 설정 시 1~20 사이 임의 무작위 할당)
    - `P_GEN = 0.005` (차량 발생 확률 계수)
    - `NUM_BLOCKS = 6` (도심 격자망 블록 수)
    - `MAX_STEPS = 3600.0` (시뮬레이션 최대 시간/스텝)
    - `RSU_RANGE = 800.0` (RSU 통신 반경, m)
    - `EDGE_LENGTH = 2400.0` (`RSU_RANGE * 2 + OUTAGE_ZONE`)
    - `NUM_LANES = 2` (차선 수)

- **시뮬레이션 엔진 연동 구조 (`/home/imnyj/Workspace/paper4/code/sim_engine.py`)**:
  - `load_config(config_path)` (lines 186-202): 마크다운 표 형태의 `config.md` 파싱.
  - `generate_sumonetsim_files(work_dir, config, seed)` (lines 204-238): `SumoNetSim1.1.5/src/sumo/make_sumo_set.py`를 읽어 `config.md` 설정값과 난수 시드(`random.seed(seed)`)를 주입한 후 실행하여 실시간으로 네트워크/라우트 XML을 빌드.
  - `SimulationRunner.run()` (lines 295-365): `libsumo.start()`를 통해 SUMO 프로세스를 인프로세스로 고속 제어하며 에피소드 단위 시뮬레이션 수행.

---

### 1.2 사용자 환경변수 제어 `config.md` 현황 및 설정 항목
- **현재 파일 위치**: `/home/imnyj/Workspace/paper4/code/config.md`
- **현재 설정 내용**:
  ```markdown
  # SUMO Environment Configuration

  This file configures the SUMO network environment. If you set `AV_SPEED` or `DENSITY` to 0, they will be randomly selected per simulation run.

  | Variable | Value | Description |
  |---|---|---|
  | AV_SPEED | 60 | Average vehicle speed (km/h). 0 for random. |
  | DENSITY | 0 | Vehicle density (/1km-lane). 0 for random. |
  | NUM_BLOCKS | 6 | Number of grid blocks. |
  | MAX_STEPS | 3600.0 | Maximum simulation steps. |
  | OUTAGE_ZONE | 800 | Outage zone size. |
  | RSU_RANGE | 800.0 | Communication range of RSU. |
  ```
- **권장 보완 사항**:
  1. 프로젝트 최상위 루트 경로(`/home/imnyj/Workspace/paper4/config.md`)에 배치하거나 `code/config.md`와 동기화하여 사용자가 루트에서도 즉시 변경 가능하도록 지원.
  2. 추가 설정 항목: `SEED` (난수 시드), `COMM_RANGE_M` (기본 300.0m), `DATA_RATE_BPS` (기본 3,000,000 bps).

---

### 1.3 통신 모듈(Communication Module) 물리적 구현 현황
- **무선 채널 및 물리 계층 모델링 (`code/sim_engine.py`)**:
  - `reception_probability(dist_m, p_tx_dbm)` (lines 53-95):
    - 주파수 5.9 GHz V2X 채널, 자유공간+도심 경로손실 지수 $\alpha = 2.0$, $PL_0 \approx 47\text{ dB at } 1\text{m}$.
    - 열잡음: $-174\text{ dBm/Hz} + 10\log_{10}(10\text{MHz}) + NF(10\text{dB}) = -94\text{ dBm}$.
    - Nakagami-$m$ 페이딩 ($m=3$) 기반 수신 확률 CCDF 정밀 계산: $P(\text{SNR} \ge \gamma_{\text{th}}) = e^{-x} (1 + x + 0.5 x^2)$, where $x = 3 / (\text{SNR} / \gamma_{\text{th}})$.
  - `simulate_receptions()` (lines 120-180): CSMA/CA MAC 계층 경합 및 충돌 인자($\text{collision\_factor} = \max(0.1, 1.0 - \text{CBR}_{\text{local}} \times 0.8)$) 적용.
  - `compute_local_cbr()` (lines 97-118): 차량 반경 500m 감지 영역 내 전송 패킷 기반 Channel Busy Ratio(CBR) 실시간 계산.
- **ETSI 표준 CAM 계층 및 DCC 제어기 (`code/etsi_cam_layer.py`)**:
  - ETSI EN 302 637-2 표준 기반 CAM 생성 트리거 ($\Delta\text{heading} \ge 4^\circ$, $\Delta\text{pos} \ge 4\text{m}$, $\Delta\text{speed} \ge 0.5\text{m/s}$, 타이머 $T_{\text{GenCam}} \in [0.1\text{s}, 1.0\text{s}]$ 만료).
  - DCC 상태 머신 및 레이트 제어기 완비:
    - `ReactDCC`: 3단계 상태 전이 (Relaxed: 10Hz, Active: 3.3Hz, Restricted: 1Hz, CBR 임계값 0.40/0.60).
    - `AdaptDCC`: 목표 CBR(0.60) 추종 비례 제어기.
    - `Heuristic`: Bhattacharyya (2024) 기반 (CBR zone, Neighbor zone) 2D Lookup Table.
    - `Fixed10Hz`: 고정 10Hz ($T=0.1\text{s}, p_{\text{tx}}=+20\text{dBm}$).
- **정보 연령(AoI) 추적기 (`code/aoi_tracker.py`)**:
  - 이웃 차량 간 CAM 패킷 생성 시간($t_{\text{gen}}$)과 수신 시간($t_{\text{rx}}$) 기반 실시간 AoI 계산 및 Fake AoI 억제 메커니즘 포함.
- **AI-DCC Hook 인터페이스 (`code/ai_dcc_hook.py`)**:
  - DRL 에이전트(상태: $[cbr_{\text{global}}, n_{\text{neighbors}}, v_{\text{norm}}, \Delta t_{\text{cam}}, cbr_{\text{smoothed}}]$)의 행동($T_{\text{GenCam}} \times p_{\text{tx}}$ 16차원 이산 행동 공간)을 CAM 레이어와 완벽 연동.
- **통신 모듈 검증 테스트 (`code/test_comm_module.py`)**:
  - 5회 연속 시뮬레이션 실행을 통해 메모리 누수, 예외, 지표 범위(PDR, CBR, AoI, Energy) 수학적 유효성 검증 완료.

---

### 1.4 14개 비교 베이스라인 및 제안 모델(REMO-DQN) 물리적 구현 전수 조사

| 번호 | 모델명 | 유형 | 물리적 구현 코드 위치 | 사전 학습 체크포인트 | 수렴 CSV 데이터 |
|:---:|:---|:---:|:---|:---|:---|
| 1 | **Fixed 10Hz** | 규칙 기반 | `code/etsi_cam_layer.py` | N/A (Rule-based) | `data/cbr_trace.csv`, `data/pdr_vs_density.csv` 등 |
| 2 | **ReactDCC** | 표준 DCC | `code/etsi_cam_layer.py` | N/A (ETSI Standard) | `data/cbr_trace.csv`, `data/pdr_vs_density.csv` 등 |
| 3 | **AdaptDCC** | 표준 DCC | `code/etsi_cam_layer.py` | N/A (ETSI Standard) | `data/cbr_trace.csv`, `data/pdr_vs_density.csv` 등 |
| 4 | **Q-Learning** | 표 기반 RL | `code/qlearning_agent.py`<br>`code/train_qlearning.py` | `data/models/QLearning.pkl`<br>`code/qlearning_model.pkl` | `data/models/QLearning_convergence.csv` |
| 5 | **SARSA** | On-Policy RL | `code/sarsa_agent.py`<br>`code/train_sarsa.py` | `data/models/SARSA.pkl`<br>`code/sarsa_model.pkl` | `data/models/SARSA_convergence.csv` |
| 6 | **Actor-Critic** | 정책 기반 RL | `code/actor_critic_agent.py`<br>`code/train_actor_critic.py` | `data/models/ActorCritic.pth`<br>`code/actor_critic.pth` | `data/models/ActorCritic_convergence.csv` |
| 7 | **Vanilla DQN** | 딥 Q-러닝 | `code/dqn_agent.py`<br>`code/train_dqn.py` | `data/models/VanillaDQN.pth`<br>`code/vanilla_dqn.pth` | `data/models/VanillaDQN_convergence.csv` |
| 8 | **Double DQN** | 오버에스티메이션 방지 | `code/ddqn_agent.py`<br>`code/optuna_ddqn.py` | `data/models/DoubleDQN.pth`<br>`code/ddqn.pth` | `data/models/DoubleDQN_convergence.csv` |
| 9 | **DDPG** | 연속 제어 DRL | `code/ddpg_agent.py`<br>`code/optuna_ddpg.py` | `data/models/DDPG.pth`<br>`code/ddpg_model.pth` | `data/models/DDPG_convergence.csv` |
| 10 | **PPO** | 온폴리시 클리핑 | `code/ppo_agent.py`<br>`code/optuna_ppo.py` | `data/models/PPO.pth`<br>`code/ppo.pth` | `data/models/PPO_convergence.csv` |
| 11 | **SAC** | 최대 엔트로피 RL | `code/sac_agent.py`<br>`code/optuna_sac.py` | `data/models/SAC.pth`<br>`code/sac.pth` | `data/models/SAC_convergence.csv` |
| 12 | **TD3** | 트윈 딜레이 DDPG | `code/td3_agent.py`<br>`code/optuna_td3.py` | `data/models/TD3.pth`<br>`code/td3.pth` | `data/models/TD3_convergence.csv` |
| 13 | **Decision Transformer** | 오프라인 트랜스포머 | `code/dt_agent.py`<br>`code/optuna_dt.py` | `data/models/DecisionTransformer.pth`<br>`code/dt_model.pth` | `data/models/DecisionTransformer_convergence.csv` |
| 14 | **MAPPO** | 다중 에이전트 PPO | `code/mappo_agent.py`<br>`code/optuna_mappo.py` | `data/models/MAPPO.pth`<br>`code/mappo.pth` | `data/models/MAPPO_convergence.csv` |
| 15 | **Dueling DQN** *(추가)* | 듀얼링 가치 분리 | `code/dueling_dqn_agent.py` | `data/models/DuelingDQN.pth`<br>`code/dueling_dqn.pth` | `data/models/DuelingDQN_convergence.csv` |
| 16 | **MoEDQN** *(추가)* | 전문가 혼합 DQN | `code/moe_agent.py`<br>`code/train_moe.py` | `data/models/MoEDQN.pth`<br>`code/moe_dqn.pth` | `data/models/MoEDQN_convergence.csv` |
| 17 | **REMO-DQN (제안)** | **ResNet+MoE+Dueling** | `code/resnet_moe_agent.py`<br>`code/train_resnet.py` | `data/models/REMO-DQN.pth`<br>`code/resnet_moe_dqn.pth` | `data/models/REMO-DQN_convergence.csv` |

- **Ablation 스터디 구현 현황 (`code/ablation_agents.py`)**:
  - `Variant1_REMODQN`: 제안 전체 모델 (ResNet + MoE + Dueling DQN).
  - `Variant2_NoResNet`: ResNet 제거 (MLP Feature Extractor + MoE + Dueling).
  - `Variant3_NoMoE`: MoE 제거 (ResNet + 단일 Dueling Expert).
  - `Variant4_NoDueling`: Dueling 구조 제거 (ResNet + MoE + Standard Q Output).
  - 실행 스크립트: `code/run_ablation_structure.py`, `code/run_ablation_reward.py`, `code/run_ablation_state.py`.
  - 구조 Ablation 데이터(`data/ablation_structure/`) 완비 (모든 변형의 `.pth`, `train_log.csv`, `eval_metrics.csv` 존재).

---

## 2. Logic Chain (추론 단계)

1. **[SUMO 네트워크 파이프라인 검증]**:
   - `sim_engine.py`는 `SumoNetSim1.1.5/src/sumo/make_sumo_set.py` 스크립트를 동적으로 로드하고 `config.md` 파라미터(`AV_SPEED`, `DENSITY` 등)를 치환 실행하여 XML 망 파일들을 생성함.
   - `DENSITY=0`, `AV_SPEED=0` 지정 시 `make_sumo_set.py` 내부의 무작위 분기(`CalcP_GEN(random.randint(1,20))`, `random.uniform(10.0/3.6, 120.0/3.6)`)가 정상 작동하여 요구사항에 명시된 무작위 시뮬레이션 환경이 물리적으로 보장됨.

2. **[통신 모듈의 수학적/물리적 무결성]**:
   - `sim_engine.py`의 채널 모델은 무선 통신의 표준인 5.9 GHz Nakagami-$m$ 페이딩($m=3$) 및 감쇄 모델을 수학적으로 엄밀히 따르고 있으며, `etsi_cam_layer.py`는 ETSI EN 302 637-2 표준 트리거를 완전히 준수함.
   - `test_comm_module.py`를 통해 5회 반복 검증 결과 예외 없이 안정적 작동이 입증됨.

3. **[14개 베이스라인 + 제안 모델 아키텍처 및 데이터 완결성]**:
   - 14개 베이스라인(규칙 기반 3종 + 고전 RL 2종 + 심층 RL/트랜스포머 9종)과 제안 모델(REMO-DQN), 추가 베이스라인 2종(DuelingDQN, MoEDQN)까지 총 17개 모델의 독립적인 에이전트 클래스, 훈련 스크립트, 가중치 체크포인트(`.pth`/`.pkl`), Optuna 튜닝 결과(`data/optuna/`), 수렴 로그 CSV가 모두 실존함.
   - 제안 모델 REMO-DQN은 `ResNetFeatureExtractor`(2 잔차 블록) + `gating_network`(3 전문가 소프트맥스 라우팅) + `DuelingExpert`(Value/Advantage 스트림)의 물리적 아키텍처를 정확히 충족함.

---

## 3. Caveats (주의사항 및 한계)

1. **`config.md` 파일 경로 다중화**:
   - 현재 `code/config.md`가 실제 시뮬레이션에서 파싱되어 사용 중이나, 사용자의 편의성 및 원본 요구사항(`R1`) 준수를 위해 프로젝트 루트 경로 `/home/imnyj/Workspace/paper4/config.md`에도 최신 설정 파일이 제공되어야 함.
2. **보상(Reward) 및 상태(State) Ablation Raw 데이터**:
   - 구조 Ablation(`data/ablation_structure/`)은 4종 변형이 모두 완비되어 있으나, 보상 및 상태 Ablation(`data/ablation_reward/`, `data/ablation_state/`)은 Base 로그만 존재하므로, 논문 작성을 위한 전체 변형(`wo_R1`, `wo_R2`, `wo_R3`, `wo_Density`, `wo_CBR`, `wo_Kinematics`) 데이터 추출 스크립트의 추가 실행이 요구됨.

---

## 4. Conclusion (최종 결론)

- **SUMO 환경 및 `config.md`**: `SumoNetSim1.1.5/src/sumo` 기반의 네트워크 생성 스크립트 및 `config.md` 파싱 제어 파이프라인이 정상 구축되어 있으며, `DENSITY=0`, `AV_SPEED=0` 무작위 파라미터 제어가 완벽히 지원됨.
- **통신 모듈**: 802.11p WAVE 채널 모델, ETSI EN 302 637-2 CAM 계층, DCC 제어기, AoI 추적기 등이 누락 없이 완성도 높게 구현되어 있음.
- **모델 전수 조사**: 14개 비교 베이스라인 모델 및 제안 모델(REMO-DQN, ResNet+MoE+Dueling DQN)의 물리적 소스코드, 모델 가중치 파일(`.pth`/`.pkl`), 수렴 CSV 데이터, Optuna 파라미터가 모두 실존하며 즉시 벤치마크 및 시각화 파이프라인에 투입 가능한 상태임을 확인하였음.

---

## 5. Verification Method (독립 검증 방법)

1. **통신 모듈 5회 검증 스크립트 실행**:
   ```bash
   python3 /home/imnyj/Workspace/paper4/code/test_comm_module.py
   ```
   - 예상 결과: 5/5 Iterations Passed 종료 코드 0.
2. **모델 체크포인트 및 파일 존재 확인**:
   ```bash
   ls -la /home/imnyj/Workspace/paper4/data/models/
   ls -la /home/imnyj/Workspace/paper4/data/optuna/
   ```
   - 14개 베이스라인 및 REMO-DQN `.pth`/`.pkl` 및 `_convergence.csv` 존재 확인.
3. **제안 모델 및 Ablation 구조 로드 테스트**:
   ```bash
   python3 -c "import sys; sys.path.insert(0, '/home/imnyj/Workspace/paper4/code'); from resnet_moe_agent import ResNetMoEDQN; m = ResNetMoEDQN(5, 16); print('REMO-DQN Loaded successfully:', m)"
   ```
