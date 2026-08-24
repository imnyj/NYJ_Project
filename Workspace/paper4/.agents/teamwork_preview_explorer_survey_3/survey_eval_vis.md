# Paper 4 평가 스윕(17,000 에피소드) 및 시각화(22개 플롯/테이블) 파이프라인 정밀 분석 보고서

**작성자**: explorer_survey_3 (Survey 탐색 에이전트)  
**일자**: 2026-08-24  
**대상 프로젝트**: `/home/imnyj/Workspace/paper4`  
**목적**: 평가 스윕(17,000 에피소드) 및 시각화(11개 데이터셋, 22개 산출물) 파이프라인 전수 조사, mock/fake 데이터 주입 지점 식별, 실측 데이터 추출 스키마 및 병렬 처리 아키텍처 수립

---

## 1. 개요 및 요약 (Executive Summary)

본 조사는 `/home/imnyj/Workspace/paper4`의 평가 스윕(17개 모델 x 10개 밀도 x 100개 에피소드 = 17,000 에피소드) 및 논문 제출용 22개 시각화/테이블 산출물 파이프라인을 전수 분석한 결과입니다.

주요 핵심 결과:
1. **하드웨어 역량 확인**: Intel i9-10900X (10코어/20스레드), 125 GiB RAM, 4x NVIDIA RTX 3090 (각 24GB VRAM) 환경으로 16~18개 멀티프로세싱 워커를 통한 고속 병렬 평가가 가능함.
2. **`visualizer/prepare_data.py` Mock/Fake 전수 적발**: 9개 빌드 함수 전반에 걸쳐 하드코딩된 더미 상수(-900,000 등), 수식 기반 가짜 데이터 조작(이론 수식으로 PDR/AoI 생성, 선형 근사로 손실/지연 생성), 하드코딩된 Optuna 민감도 테이블 등이 발견됨.
3. **실측 데이터 6대 타겟 스키마 정립**: `eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`의 표준 스키마 및 추출 경로 정의 완료.
4. **11개 대상 데이터셋 및 22개 시각화/테이블 파일 명세 정립**: 9개 핵심 플롯(각 PNG 350 DPI + Vector PDF = 18개)과 2개 핵심 테이블(각 CSV + LaTeX TeX = 4개)로 구성된 총 22개 산출물 규격화.

---

## 2. 시스템 자원 및 병렬 처리 환경 분석

### 2.1 하드웨어 스펙
- **CPU**: Intel(R) Core(TM) i9-10900X CPU @ 3.70GHz
  - 물리 코어: 10 Cores
  - 논리 스레드: 20 Threads (`os.cpu_count() == 20`, `multiprocessing.cpu_count() == 20`)
- **시스템 메모리 (RAM)**: 총 125 GiB (사용 가능 메모리 ~108 GiB)
- **GPU**: 4x NVIDIA GeForce RTX 3090
  - VRAM: 개당 24,576 MiB (총 96 GB VRAM)
  - Driver Version: 580.173.02, CUDA 13.0 지원

### 2.2 17,000 에피소드 병렬 평가 파이프라인 아키텍처
- **총 평가 에피소드 수**:  
  $$\text{Total Episodes} = 17 \text{ Models} \times 10 \text{ Densities } (5, 10, \dots, 50) \times 100 \text{ Episodes} = 17,000 \text{ Episodes}$$
- **멀티프로세싱 풀 구성**:
  - `multiprocessing.set_start_method('spawn', force=True)` 적용 (PyTorch CUDA 컨텍스트 및 libsumo 메모리 격리 필수).
  - 워커 수: `num_workers = 16` (20개 논리 스레드 중 80% 활용하여 OS/I/O 병목 방지).
  - GPU 분배: 워커 ID를 기준으로 4개 GPU에 균등 라운드로빈 할당 (`gpu_id = worker_idx % 4`).
  - libsumo 격리: 각 워커 프로세스가 `tempfile.mkdtemp()`를 사용하여 독립된 `.net.xml`, `.rou.xml`, `.sumocfg` 디렉토리에서 SUMO 시뮬레이션을 구동하여 파일 락 충돌 방지.
  - 내결함성(Fault-tolerance): 에피소드 단위 또는 `(model, density)` 청크 단위로 결과를 `data/evaluation/eval_density_results.csv`에 atomic flush하여 중단 시 즉시 이어하기(Resume) 지원.

---

## 3. `visualizer/prepare_data.py` Mock / Fake 데이터 전수 조사 결과

`visualizer/prepare_data.py` (총 506행)에 대한 전수 정밀 코드 감사를 수행한 결과, 시뮬레이션 실측 데이터가 아닌 가짜(fake) 데이터 및 하드코딩된 수식이 다음과 같이 다수 발견되었습니다.

| 함수명 | 라인 번호 | 위반 및 하드코딩 유형 | 상세 코드 및 분석 |
|---|---|---|---|
| `build_reward_convergence` | L75-76, L98, L103, L108-115 | 더미 상수 패딩 및 비RL 하드코딩 | - 데이터 부족 시 `-900000.0`으로 패딩 (L98, L103)<br>- Non-RL 모델(Fixed 10Hz, ReactDCC, AdaptDCC)에 `-995000.0`, `-982000.0`, `-978000.0` 정적 상수 부여 (L108-115) |
| `build_ablation_study` | L169-186 | 가짜 수식 및 오프셋 기반 곡선 조작 | - 실측 Ablation 학습 없이 REMO-DQN 보상에 오프셋 적용:<br>  * `w/o ResNet`: `remo_rew - 10000.0`<br>  * `w/o MoE`: `remo_rew - 20000.0`<br>  * `w/o Dueling`: `remo_rew - 30000.0`<br>  * `w/o R1`: `remo_rew - aoi_term`<br>  * `w/o R2`: `remo_rew - cbr_term`<br>  * `w/o R3`: `remo_rew + 5000.0` |
| `build_optuna_sensitivity` | L195-213 | 전체 테이블 100% 하드코딩 | 17개 모델 전체의 최적 하이퍼파라미터, 보상, PDR, AoI, CBR 수치를 코드에 정적 튜플로 직접 박아 넣음. Optuna 최적화 로그 파일과 완전히 단절됨. |
| `build_tsne_clustering` | L259-281 | 오라클 데이터셋 샘플링 및 Sine파 폴백 | - 신경망 잠재 공간(Latent representation) 추출 대신 `oracle_dataset.csv`를 샘플링함.<br>- 파일 부재 시 `math.sin(i * 0.1)` 기반 가짜 2D 좌표 생성 (L278-280). |
| `build_moe_routing` | L298-300, L312-324 | 가짜 상태 벡터 주입 및 하드코딩 배열 폴백 | - 인위적 수식 `cbr_val = min(0.9, 0.05 + d * 0.007)`로 임의의 텐서를 만들어 추론 (L298-300).<br>- 모델 부재 시 `[88, 76, 58, ...]`, `[10, 20, 36, ...]`, `[2, 4, 6, ...]` 가짜 라우팅 가중치 배열 주입 (L314-324). |
| `build_cbr_trace` | L351, L356, L358 | 평탄한 상수값 패딩 | 실측 시계열 누락 시 `0.08`, `0.086` 상수값으로 전체 100단계를 채움. |
| `build_density_metrics` | L380-383 | 임의의 선형 결합 수식 주입 | - 지연시간: `Delay_ms = AoI_mean * 0.085 + (CBR_mean * 12.0)` (L381)<br>- 공정성: `Fairness = np.clip(ETSI_compliance / 100.0 * 0.96 + 0.02, 0.85, 0.99)` (L382) |
| `build_distance_metrics` | L425-428 | 이론 수식으로 가짜 실측치 생성 | 패킷 로그 대신 `reception_probability(d) * max(0.1, 1.0 - cbr * 0.8)` 수식으로 거리별 PDR/AoI 계산. |
| `build_hardware_feasibility` | L443-453 | 하드코딩 테이블 | 정적 튜플로 FLOPs, Latency, Memory를 정의. |

---

## 4. 실측 데이터 추출 요구사항 및 스키마 명세

17,000 에피소드 평가 및 시각화 파이프라인에서 추출해야 하는 100% 실측 데이터 6종의 스키마와 저장 위치는 다음과 같습니다.

### 4.1 `data/evaluation/eval_density_results.csv`
- **목적**: 17개 모델 x 10개 밀도 x 100개 에피소드의 시뮬레이션 실측 통계
- **헤더 스키마**:
  ```csv
  method,density,seed,runtime_sec,n_cam_events,Reward,CBR_mean,AoI_mean,PDR_mean,energy_efficiency,ETSI_compliance
  ```
- **데이터 건수**: 정확히 17,000행 (헤더 제외)
- **포함 모델 (17개)**:
  1. REMO-DQN (Proposed)
  2. Fixed 10Hz
  3. ReactDCC
  4. AdaptDCC
  5. MoEDQN
  6. MAPPO
  7. PPO
  8. SAC
  9. DDPG
  10. TD3
  11. DuelingDQN
  12. DoubleDQN
  13. VanillaDQN
  14. QLearning
  15. SARSA
  16. ActorCritic
  17. DecisionTransformer

### 4.2 `data/evaluation/distance_pdr.json` (또는 `data/distance_pdr.json`)
- **목적**: 통신 거리 구간(0~50m, 50~100m, 100~150m, 150~200m, 200~250m, 250~300m)에 따른 모델별 실측 패킷 수신 성공률(PDR)
- **JSON 스키마**:
  ```json
  {
    "REMO-DQN": {
      "distances": [25, 75, 125, 175, 225, 275],
      "pdr_mean": [99.2, 97.5, 93.1, 85.4, 72.0, 55.3],
      "pdr_std": [0.5, 1.1, 1.8, 2.4, 3.1, 4.0]
    },
    ...
  }
  ```

### 4.3 `data/evaluation/distance_aoi.json` (또는 `data/distance_aoi.json`)
- **목적**: 통신 거리 구간에 따른 모델별 실측 정보 연령(AoI, ms)
- **JSON 스키마**:
  ```json
  {
    "REMO-DQN": {
      "distances": [25, 75, 125, 175, 225, 275],
      "aoi_mean": [105.2, 115.4, 135.8, 175.2, 240.5, 350.1],
      "aoi_std": [5.2, 8.4, 12.1, 18.5, 25.0, 38.2]
    },
    ...
  }
  ```

### 4.4 `data/evaluation/cbr_trace.json` (또는 `data/cbr_trace.json`)
- **목적**: 시뮬레이션 시간 진행(Time Step)에 따른 채널 점유율(CBR) 실측 궤적
- **JSON 스키마**:
  ```json
  {
    "time_seconds": [0.1, 0.2, 0.3, "...", 200.0],
    "traces": {
      "REMO-DQN": [0.58, 0.59, 0.60, 0.59, "..."],
      "Fixed 10Hz": [0.85, 0.88, 0.91, 0.89, "..."],
      "..."
    }
  }
  ```

### 4.5 `data/evaluation/tsne_data.json` (또는 `data/tsne_data.json`)
- **목적**: `ResNetMoEAgent`의 128차원 ResNet Feature Extractor에서 추출된 실제 잠재 특징 벡터와 t-SNE 2D 투영 좌표
- **JSON 스키마**:
  ```json
  {
    "x": [0.124, -0.452, "..."],
    "y": [0.881, 1.235, "..."],
    "cluster": ["Low Traffic", "Medium Traffic", "High Traffic", "..."],
    "expert_id": [1, 2, 3, "..."],
    "raw_state_samples": "..."
  }
  ```

### 4.6 `data/evaluation/moe_routing.json` (또는 `data/moe_routing.json`)
- **목적**: 밀도(5~50 veh/km)에 따른 REMO-DQN Gating Network의 3개 전문가(Expert 1, 2, 3) 활성화 가중치(Softmax Soft Routing) 실측값
- **JSON 스키마**:
  ```json
  {
    "densities": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    "expert1_weights": [85.4, 72.1, 55.0, "..."],
    "expert2_weights": [12.1, 23.5, 36.2, "..."],
    "expert3_weights": [2.5, 4.4, 8.8, "..."]
  }
  ```

---

## 5. 11개 대상 데이터셋 및 22개 시각화/테이블 산출물 명세

`visualizer/generate_visualizations.py`, `plot_figures.py`, `generate_tables.py`, `plot_all.py`를 전수 조사하여 정리한 11개 대상 산출물 명세입니다.

모든 시각화 이미지 파일은 **350 DPI PNG** 및 **Vector PDF** 두 가지 포맷으로 생성되며, 표는 **CSV** 및 **LaTeX (.tex)** 두 가지 포맷으로 생성되어 총 22개 파일이 도출됩니다.

| Target 번호 | 데이터셋 파일명 (`data/`) | 시각화/산출물 파일명 (`visualizer/`) | 형식 및 규격 | 주요 시각화 내용 및 요구사항 |
|---|---|---|---|---|
| **Target 1** | `ablation_study.csv` | `1_ablation_study.png`<br>`1_ablation_study.pdf` | PNG (350 DPI)<br>Vector PDF | (a) 구조적 소거(w/o ResNet, w/o MoE, w/o Dueling), (b) 보상 소거(w/o R1, w/o R2, w/o R3), Phase I/II 배경 음영 |
| **Target 2** | `optuna_sensitivity_table.csv` | `2_optuna_sensitivity_table.csv`<br>`2_optuna_sensitivity_table.tex` | CSV<br>LaTeX TeX | 17개 모델의 Optuna 최적 하이퍼파라미터, 수렴 보상, PDR, AoI, CBR 성능 비교표 |
| **Target 3** | `reward_convergence.csv` | `3_reward_convergence.png`<br>`3_reward_convergence.pdf` | PNG (350 DPI)<br>Vector PDF | 17개 베이스라인의 20만 스텝 학습 수렴 곡선, 이동 평균 스무딩, 제안 기법 신뢰구간 음영 |
| **Target 4** | `tsne_clustering.csv` | `4_tsne_clustering.png`<br>`4_tsne_clustering.pdf` | PNG (350 DPI)<br>Vector PDF | ResNet 잠재 공간의 t-SNE 2D 군집화 (Low, Medium, High traffic) 및 신뢰 타원(Confidence Ellipse) |
| **Target 5** | `moe_routing.csv` | `5_moe_routing.png`<br>`5_moe_routing.pdf` | PNG (350 DPI)<br>Vector PDF | 차량 밀도(5~50 veh/km)에 따른 MoE 3개 전문가 동적 활성화 가중치 누적 영역도 (Stacked Area Plot) |
| **Target 6** | `cbr_trace.csv` | `6_cbr_trace.png`<br>`6_cbr_trace.pdf` | PNG (350 DPI)<br>Vector PDF | 17개 모델의 시간별 CBR 궤적 및 ETSI 표준 목표치($CBR_{\text{target}}=0.60$) 기준선 대조 |
| **Target 7** | `pdr_vs_density.csv` | `7_pdr_vs_density.png`<br>`7_pdr_vs_density.pdf` | PNG (350 DPI)<br>Vector PDF | 차량 밀도(5~50 veh/km) 증가에 따른 17개 모델의 패킷 수신 성공률(PDR, %) 방어 곡선 |
| **Target 8** | `aoi_vs_density.csv` | `8_aoi_vs_density.png`<br>`8_aoi_vs_density.pdf` | PNG (350 DPI)<br>Vector PDF | 차량 밀도(5~50 veh/km)에 따른 17개 모델의 평균 정보 연령(AoI, ms) 대조 곡선 |
| **Target 9** | `pdr_vs_distance.csv` | `9_pdr_vs_distance.png`<br>`9_pdr_vs_distance.pdf` | PNG (350 DPI)<br>Vector PDF | 통신 거리(0~300m)에 따른 17개 모델의 패킷 수신 성공률(PDR, %) 감쇄 곡선 |
| **Target 10** | `aoi_vs_distance.csv` | `10_aoi_vs_distance.png`<br>`10_aoi_vs_distance.pdf` | PNG (350 DPI)<br>Vector PDF | 통신 거리(0~300m)에 따른 17개 모델의 정보 연령(AoI, ms) 증가 곡선 |
| **Target 11** | `hardware_feasibility_table.csv` | `11_hardware_feasibility_table.csv`<br>`11_hardware_feasibility_table.tex` | CSV<br>LaTeX TeX | 모델별 FLOPs/MACs, 파라미터 수, 추론 지연(ms), 메모리 점유(KB), MCU 탑재 실효성 분류표 |

---

## 6. 결론 및 구현/실행 권고사항

1. **`prepare_data.py` 전면 리팩토링 필수**:
   - 기존의 모든 수식 기반 가짜 데이터 생성 로직 및 하드코딩 배열을 제거.
   - `data/evaluation/eval_density_results.csv`, `distance_pdr.json`, `distance_aoi.json`, `cbr_trace.json`, `tsne_data.json`, `moe_routing.json`을 직접 파싱하여 11개 CSV를 생성하는 순수 파이프라인으로 전환.
2. **`run_density_sweep_parallel.py` 신규 작성 및 실행**:
   - `multiprocessing.Pool(processes=16)`을 활용하여 17,000 에피소드 병렬 실행.
   - `SimulationRunner` 및 `AoITracker`에서 거리별 PDR/AoI 및 CBR 시계열, t-SNE 특징을 실시간 추출하도록 연동.
3. **시각화 DPI 및 범례 순서 엄격 준수**:
   - `evaluation_plan.md` 및 `PROJECT.md`에 명시된 17개 베이스라인 표준 범례 순서 및 고정 컬러 팔레트 유지.
   - 모든 PNG 산출물의 DPI를 350으로 렌더링하고 `PIL.Image.open().info['dpi'] == (350, 350)` 검증 통과 확보.
