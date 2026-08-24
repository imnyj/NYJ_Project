# Paper4 시뮬레이션 환경 및 네트워크/통신 계층 정밀 분석 보고서 (survey_sim.md)

- **작성일자**: 2026-08-24
- **작성 에이전트**: Survey 탐색 에이전트 (`explorer_survey_1`)
- **작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_explorer_survey_1`
- **대상 프로젝트**: `/home/imnyj/Workspace/paper4`

---

## 1. 개요 및 분석 목적
본 보고서는 Paper4 프로젝트의 V2X(Vehicle-to-Everything) 분산 혼잡 제어(DCC: Decentralized Congestion Control) 강화학습 프레임워크인 **REMO-DQN** 및 16개 비교 모델의 시뮬레이션 환경, 네트워크 통신 계층, SUMO 모빌리티 연동, 수학적 채널 모델, AoI(Age of Information) 추적기, 그리고 MoE/t-SNE 로깅 연동 구조를 정밀 분석하여 R1 사전 감사(Audit) 및 후속 파이프라인 구현을 위한 기술적 기초를 제공합니다.

---

## 2. 파일 구조 및 시뮬레이션 구성 요소 분석

### 2.1 주요 파일 구성 및 역할

| 파일 경로 | 핵심 클래스 / 함수 | 주요 역할 및 기능 |
|---|---|---|
| `code/sim_engine.py` | `SimulationRunner`, `simulate_receptions`, `compute_local_cbr`, `compute_local_n_est`, `reception_probability_vec` | `libsumo` 기반 시뮬레이션 라이프사이클 관리, SUMO 네트워크 동적 생성, 802.11p 채널 감쇄 모델, CAM 수신 판정, 에피소드 메트릭 집계 |
| `code/etsi_cam_layer.py` | `ETSICAMLayer`, `VehicleCAMState` | ETSI EN 302 637-2 표준 기반 CAM 생성 조건 판정(방향, 위치, 속도, 주기 트리거), DCC 제어기 상태 머신(ReactDCC, AdaptDCC, Heuristic, Fixed10Hz, AI DCC) |
| `code/aoi_tracker.py` | `AoITracker` | 차량 간 송수신 타임스탬프 기록, $300\text{m}$ 통신 반경 내 차량 쌍별 순간/평균 AoI 추적, PDR(Packet Delivery Ratio) 계산 |
| `code/ai_dcc_hook.py` | `AIDCCHookBase`, `ResNetMoEDQNHook`, `get_hook` | 5차원 상태 벡터 구성, 24개 이산 액션 매핑, C-3 다중 목표 보상 계산, 에피소드 전환(transition) 버퍼 저장 |
| `code/resnet_moe_agent.py` | `ResNetMoEDQN`, `ResNetMoEAgent`, `ResNetFeatureExtractor`, `DuelingExpert` | 제안 모델 REMO-DQN 구조 (5D State $\to$ 2블록 ResNet Feature $\to$ Softmax Gating Network + 3개 Dueling Expert) |
| `code/moe_agent.py` | `MoEDQN`, `MoEAgent` | MoE 비교 모델 구조 (3개 FCN Expert + Softmax Gating) |
| `SumoNetSim1.1.5/src/sumo/make_sumo_set.py` | `make_sumo_files`, `generate_nodes_edges`, `CalcP_GEN` | $6\times 6$ 맨해튼 격자망(Urban Grid) 생성, TAZ(Traffic Assignment Zone) 기반 확률적 차량 유입 flow 생성 |
| `config.md` | 설정 테이블 (`AV_SPEED`, `DENSITY`, `NUM_BLOCKS` 등) | 시뮬레이션 환경의 최상위 제어 파라미터 정의 |
| `visualizer/prepare_data.py` | `build_reward_convergence`, `build_distance_metrics` 등 | 평가 결과 및 메트릭 가공, 11개 타깃 데이터셋 생성 (현재 가상/하드코딩 수식 존재) |

---

## 3. SUMO Mobility 반영 및 통신 계층 전달 메커니즘

### 3.1 동적 네트워크 생성 및 초기화
1. **설정 파싱**: `sim_engine.py:487-497`에서 `config.md`를 로드하고, 스윕 변수(`DENSITY`, `AV_SPEED`)를 오버라이드합니다.
2. **SUMO 네트워크 빌드**: `sim_engine.py:499`에서 `generate_sumonetsim_files`를 호출하여 `make_sumo_set.py`를 실행합니다.
   - `netconvert`를 통해 `generated.nod.xml` + `generated.edg.xml` $\to$ `generated.net.xml` 생성.
   - TAZ 기반으로 차량 진출입 경로 `generated.rou.xml` 및 부가파일 `generated.add.xml` 생성.
   - $P_{\text{GEN}} = \frac{\text{Density} \times L_{\text{tot}} \times v}{L_{\text{path\_avg}} \times n^2 \times 3600}$ 확률로 각 TAZ 간 차량 flow가 주입됩니다.
3. **SUMO 구성 파일**: `generate_sumocfg`를 통해 스텝 길이 $0.1\text{s}$ (100ms) 기준 `.sumocfg` 파일 생성.

### 3.2 스텝별 차량 위치 및 궤적 추출 흐름
`sim_engine.py:553-587`의 메인 시뮬레이션 루프에서 매 스텝(100ms)마다 다음 절차가 실행됩니다:
```
libsumo.simulationStep()
  │
  ├─> vehicle_ids = libsumo.vehicle.getIDList()
  ├─> departed_vids 감지 -> cam_layer.remove_vehicle(vid), aoi_tracker.remove_vehicle(vid)
  │
  └─> For each vid in vehicle_ids:
        x, y = libsumo.vehicle.getPosition(vid)
        speed = libsumo.vehicle.getSpeed(vid)
        heading = libsumo.vehicle.getAngle(vid)
        accel = libsumo.vehicle.getAcceleration(vid)
        -> vehicle_positions[vid] = (x, y)
        -> vehicles_data.append({"vid": vid, "x": x, "y": y, "speed": speed, "heading": heading, "accel": accel})
```

### 3.3 통신 계층으로의 데이터 전달 및 CAM 생성 판정
1. **로컬 밀도($n_{\text{est}}$) 계산**: `compute_local_n_est`를 통해 차량 $i$의 통신 반경($300\text{m}$) 내 이웃 차량 수를 유클리드 거리 행렬로 고속 계산하여 `vdata["n_est"]`에 저장.
2. **이전 CBR 매핑**: 직전 스텝에서 계산된 로컬 채널 점유율 `cbr_dict_prev[vid]`를 `vdata["cbr"]`에 저장.
3. **CAM 생성 트리거 판정 (`ETSICAMLayer.step`)**:
   - 누적 이동거리(Odometer): $dx = x - x_{\text{prev}}, dy = y - y_{\text{prev}} \to \text{odometer} += \sqrt{dx^2 + dy^2}$
   - DCC 제어기 업데이트: AI/규칙 기반으로 목표 $T_{\text{GenCam}}$ 및 $P_{\text{tx}}$ 결정.
   - ETSI EN 302 637-2 표준 트리거 조건 검사:
     - 최대 주기 만료: $\Delta t = t_{\text{sim}} - t_{\text{last\_cam}} \ge 1.0\text{ s}$
     - 방향 변화: $|\Delta \text{heading}| \ge 4.0^\circ$
     - 위치 변화: $\Delta \text{pos} = \sqrt{\Delta x^2 + \Delta y^2} \ge 4.0\text{ m}$
     - 속도 변화: $|\Delta \text{speed}| \ge 0.5\text{ m/s}$
   - DCC 최소 전송 주기 가드: $\Delta t < T_{\text{GenCam}}$ 이면 전송 차단 (Suppress).
   - 트리거 충족 시 `cam_events` 생성: `{"vid", "t_gen", "x", "y", "speed", "heading", "T_GenCam", "p_tx"}`.

---

## 4. 통신 성능(PDR)의 거리 및 밀도 수학적 감쇄(Decay) 모델

### 4.1 거리 감쇄 모델 (Path Loss + Nakagami-$m$ Fading)
`sim_engine.py:54-96` 및 `reception_probability_vec`에 정의된 802.11p 무선 채널 물리 계층 수식:

1. **로그-거리 경로 손실 (Log-distance Path Loss)**:
   $$PL(d) = PL_0 + 10 \cdot \alpha \cdot \log_{10}\left(\frac{\max(d, 1.0)}{d_0}\right) \quad [\text{dB}]$$
   - 기준 거리: $d_0 = 1.0\text{ m}$
   - 기준 경로 손실: $PL_0 = 20 \log_{10}\left(\frac{4 \pi \cdot 1.0 \cdot 5.9 \times 10^9}{3 \times 10^8}\right) \approx 47.85\text{ dB}$ ($f = 5.9\text{ GHz}$)
   - 경로 손실 지수: $\alpha = 2.0$ (Free-space-like Urban)
2. **수신 전력 및 SNR 계산**:
   $$P_{\text{rx}}(d) = P_{\text{tx}} - PL(d) \quad [\text{dBm}]$$
   - 열잡음 전력 ($BW = 10\text{ MHz}$, $NF = 10\text{ dB}$):
     $$N = -174 + 10 \log_{10}(10^7) + 10 = -94.0\text{ dBm}$$
   - 수신 SNR:
     $$SNR_{\text{dB}} = P_{\text{rx}}(d) - N \implies SNR_{\text{lin}} = 10^{SNR_{\text{dB}} / 10}$$
   - 변조 임계값: $SNR_{\text{thresh}} = 5.0\text{ dB} \implies SNR_{\text{thresh, lin}} \approx 3.162$ (BPSK 1/2 기준)
3. **Nakagami-$m$ ($m=3$) 페이딩 수신 확률**:
   - 평균 SNR 대비 임계 SNR 비율: $\text{ratio} = \frac{SNR_{\text{lin}}}{SNR_{\text{thresh, lin}}}$
   - $m=3$의 상보 누적 분포 함수 (CCDF):
     $$x = \frac{m}{\text{ratio}} = \frac{3.0}{\text{ratio}}$$
     $$P_{\text{rx\_prob}}(d) = \begin{cases} 1.0, & \text{if } \text{ratio} > 50.0 \\ \exp(-x) \left(1.0 + x + 0.5 x^2\right), & \text{otherwise} \end{cases}$$

### 4.2 밀도 및 채널 부하(CBR) 감쇄 모델 (Collision Factor)
`sim_engine.py:259-261`에서 차량 밀도 증가에 따른 채널 혼잡 및 패킷 충돌 효과 반영:
1. **로컬 CBR 측정**:
   $$CBR(vid) = \min\left(1.0, \frac{\sum_{j \in S(vid)} N_{\text{tx}}(j) \times \text{tx\_duration\_s}}{\text{window\_duration\_s}}\right)$$
   - $\text{tx\_duration\_s} = \frac{280 \times 8}{3 \times 10^6} \approx 0.747\text{ ms}$, $\text{window\_duration\_s} = 0.1\text{ s}$
2. **충돌 감쇄 계수 및 최종 수신 성공 확률**:
   $$\text{col\_factor}(vid) = \max\left(0.1, 1.0 - CBR(vid) \times 0.8\right)$$
   $$P_{\text{success}}(d, CBR) = P_{\text{rx\_prob}}(d) \times \text{col\_factor}(vid)$$
   - 채널이 포화($CBR \to 1.0$)되면 수신 성공률이 최대 80% 감쇄(최소 0.1 보장)되어 혼잡에 의한 패킷 유실을 수학적으로 정확하게 재현합니다.

---

## 5. AoI(Age of Information) 추적 및 데이터 기록 결함 분석

### 5.1 AoI 추적 로직 (`aoi_tracker.py`)
- **타임스탬프 관리**:
  - `last_cam_sent[vid] = (t_gen, x, y)`: 송신 차량별 최근 송신 정보.
  - `last_received_gen_time[(sid, rid)] = t_gen`: 수신 차량 쌍 $(sid, rid)$별 최근 성공 수신 CAM의 생성 시간.
  - `first_tx_time[sid]`: 차량 $sid$의 최초 전송 시간 (수신 이력이 없는 경우의 fallback 기준).
- **순간 AoI 및 평균 AoI 계산 (`step`)**:
  - 통신 반경($300\text{m}$) 내 활성 차량 쌍에 대해:
    $$AoI_{ij}(t) = \min\left(2000.0, \max\left(0.0, (t_{\text{sim}} - T_{ij}) \times 1000.0\right)\right) \quad [\text{ms}]$$
  - 유효 차량 쌍 전체의 평균 $\text{mean\_AoI}$를 매 스텝 `aoi_history`에 기록.

### 5.2 식별된 결함 및 미구현 사항

#### [결함 1] `distance_aoi` 구간별 AoI 집계 기능 완전 부재
- **현상**:
  - `sim_engine.py`에는 `dist_tx_counts[6]`와 `dist_rx_counts[6]`를 이용한 `distance_pdr` (50m 단위 6개 구간: 0~50m, 50~100m, 100~150m, 150~200m, 200~250m, 250~300m) 추출 로직은 있으나, **거리 구간별 AoI(`distance_aoi`) 집계 로직이 `aoi_tracker.py`와 `sim_engine.py`에 전혀 구현되어 있지 않습니다.**
  - 이로 인해 `visualizer/prepare_data.py:427`에서 `aoi_val = aoi_base / max(0.01, prx / 100.0)`라는 가상의 수식으로 `aoi_vs_distance.csv`를 하드코딩 생성하는 치명적 왜곡이 발생하고 있었습니다.
- **수정 요구사항**:
  - `sim_engine.py` 또는 `aoi_tracker.py`의 `step()` 시점에 거리 구간 bin별 순간 AoI 합과 카운트를 누적하고, 에피소드 종료 시 6개 거리 구간별 평균 AoI 배열 `distance_aoi`를 반환하도록 수정해야 합니다.

#### [결함 2] `cbr_history` 및 타임시리즈 트레이스 저장 파이프라인 단절
- **현상**:
  - `sim_engine.py:670`에서 `cbr_history` 배열을 반환하지만, 상위 스윕 스크립트(`run_density_sweep_all.py` / `run_parallel_evaluation.py`)에서 이를 `cbr_trace.json`으로 온전히 덤프하지 못했습니다.
  - 그 결과 `visualizer/prepare_data.py:330`에서 에피소드 100개의 `CBR_mean`을 시간축 삼아 가상의 trace를 생성하고 있었습니다.
- **수정 요구사항**:
  - 평가 스윕 시 지정된 에피소드(예: density=30, seed=42)의 스텝별 실제 `cbr_history`를 `cbr_trace.json`으로 저장하여 시각화 모듈에 직접 전달해야 합니다.

---

## 6. `resnet_moe_agent.py` t-SNE 및 MoE 게이팅 로깅 연동 분석

### 6.1 현재 신경망 아키텍처 및 한계
- `ResNetMoEDQN` 아키텍처:
  - **입력 State**: $s = [CBR_{\text{global}}, n_{\text{neighbors}}, v_{\text{norm}}, \Delta t_{\text{last\_cam}}, CBR_{\text{smoothed}}] \in \mathbb{R}^5$
  - **ResNet Feature Extractor**: $s \to z \in \mathbb{R}^{128}$ (Linear 128 + 2 Residual Blocks)
  - **Gating Network**: $z.\text{detach}() \to \text{Linear}(64) \to \text{ReLU} \to \text{Linear}(3) \to \text{Softmax} \to g = [g_1, g_2, g_3]$
  - **3 Dueling Experts**: 각 Expert $k$에 대해 Value Stream $V_k(z) \in \mathbb{R}^1$ 및 Advantage Stream $A_k(z) \in \mathbb{R}^{24}$ $\implies Q_k(z) \in \mathbb{R}^{24}$
  - **MoE 결합**: $Q(s) = \sum_{k=1}^3 g_k \cdot Q_k(z)$
- **한계점**:
  - `ResNetMoEAgent`의 `act(state)`는 오직 최적 액션 인덱스(`int`)만 반환하며, 128차원 feature activation $z$와 3차원 게이팅 가중치 $g$를 외부로 반환하는 API가 없습니다.
  - 이로 인해 `visualizer/prepare_data.py:258, 287`에서 `oracle_dataset.csv`나 가상 상태 배열, 하드코딩된 routing 비율(`[88, 76, 58, ...]`)을 사용하는 문제가 발생했습니다.

### 6.2 시뮬레이션 엔진 및 평가 파이프라인 연동 방안
1. **에이전트 인터페이스 확장**:
   - `ResNetMoEAgent`에 `inspect_state(state)` 또는 `get_latent_and_gate(state)` 메서드를 추가하여:
     ```python
     def get_latent_and_gate(self, state):
         s_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
         self.q_network.eval()
         with torch.no_grad():
             feat = self.q_network.feature_extractor(s_t)
             gate = self.q_network.gating_network(feat)
         return feat.squeeze(0).cpu().numpy(), gate.squeeze(0).cpu().numpy()
     ```
2. **평가 스윕 연동 (`run_density_sweep_parallel.py`)**:
   - 평가 주행 중 관측된 실제 상태 $s_t$들을 수집하여:
     - `tsne_data.json`: 수집된 128차원 latent feature 벡터들 및 혼잡도 클러스터 레이블(Low: $n<30$, Medium: $30\le n\le 70$, High: $n>70$)을 저장하고 t-SNE 2D 투영 좌표를 저장.
     - `moe_routing.json`: 밀도 $D \in [5, 10, \dots, 50]$별 실제 에피소드에서 관측된 평균 게이트 분배율 $[g_1, g_2, g_3]$을 측정하여 저장.
   - `visualizer/prepare_data.py`는 이 JSON 파일들을 직접 로드하여 100% 실제 신경망 추론 데이터를 플롯으로 변환.

---

## 7. 결론 및 R1 감사 요약

1. **SUMO Mobility & 통신 계층**: SUMO $6\times 6$ 격자망 생성, `libsumo` 기반 100ms 스텝 모빌리티 추출, ETSI EN 302 637-2 표준 기반 CAM 트리거, 802.11p Nakagami-m 페이딩 및 CBR 충돌 감쇄 메커니즘이 코드상에 정밀하게 구현되어 있음을 확인하였습니다.
2. **필수 수정 사항 (Action Items for Coder/Implementer)**:
   - **`sim_engine.py` / `aoi_tracker.py`**: 6개 거리 구간(0~300m, 50m 간격)별 `distance_aoi` 누적 및 반환 기능 추가.
   - **`resnet_moe_agent.py`**: 128차원 feature activation 및 게이팅 가중치 추출 API(`get_latent_and_gate`) 구현.
   - **Evaluation Pipeline**: `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`을 100% 실제 시뮬레이션/신경망 추론 결과로부터 생성하도록 연동.
   - **`visualizer/prepare_data.py`**: 가상 수식 및 하드코딩 배열을 완전 삭제하고 실제 생성된 JSON/CSV 파일만 로드하도록 정리.
