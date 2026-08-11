# 시각화 및 논문용 그래프 생성 조사 및 파이프라인 분석 보고서 (Survey Explorer 3)

**작성자**: Survey Explorer 3  
**작성일시**: 2026-08-11T15:35:00Z  
**작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3`  
**프로젝트**: Paper4 (V2X 하이브리드 DRL 기반 혼잡 제어 모델 - ResNet-MoE-Dueling DQL)

---

## 1. 개요 및 조사 목적

본 보고서는 V2X(Vehicle-to-Everything) 환경에서의 하이브리드 DRL 기반 혼잡 제어(DCC) 모델(제안 모델: **REMO-DQN** / ResNet-MoE-Dueling DQL)과 13종 비교군(총 14~16종 모델)의 성능 평가 결과를 IEEE 논문 투고 표준 규격에 맞추어 그래프로 자동 생성하기 위한 기존 스크립트 분석, 필수 그래프 종류 파악, IEEE 스타일 요구사항 정의, 데이터 입력 소스 매핑 및 시각화 구현 파이프라인 설계를 다룹니다.

---

## 2. 기존 시각화 스크립트 및 모듈 분석

프로젝트 전반에 걸쳐 분산되어 있는 시각화 관련 스크립트와 설정 모듈을 조사한 결과는 다음과 같습니다.

### 2.1 `visualizer/` 디렉토리 모듈
- **`visualizer/config.md`**: 
  - 총 16개 모델(Fixed 10Hz, ReactDCC, AdaptDCC, TinyMLP, Q-Learning, SARSA, Actor-Critic, Vanilla DQN, PPO, DDPG, Double DQN, TD3, Decision Transformer, SAC, MAPPO, REMO-DQN)에 대한 범례 순서(Order 1~16), 카테고리, 공식 이름, Hex Color Code, Line Style, Marker 지정 테이블.
  - **주요 렌더링 지침**:
    1) 색상 난립 방지: Hex Code 명시적 지정.
    2) REMO-DQN 강조: 두께(linewidth) 3.0(타 라인 1.5 대비 2배), z-order 99(최상단 배치).
    3) 범례 배치: 그래프 가림 방지를 위해 `bbox_to_anchor`를 이용한 외부 배치.
- **`visualizer/plot_utils.py`**:
  - `config.md` 명세를 파이썬 코드로 모듈화. `STYLE_MAP`, `DATA_TO_CONFIG` 딕셔너리, `get_style(data_name)`, `apply_legend(ax)` 함수 제공.
- **`visualizer/plot_all.py`**:
  - `config.md`를 파싱하고 `coder/data/` 내의 CSV 데이터들을 통합하여 1~10번 그래프(Reward Convergence, Ablation Study, MoE Routing, t-SNE, Hardware Feasibility, CBR Trace, PDR vs Density, AoI vs Density, PDR vs Distance 등)를 일괄 생성하는 종합 시각화 스크립트.
- **`visualizer/plot_cbr_cdf.py`, `plot_convergence.py`, `plot_line_density.py`, `plot_pdr_distance.py`**:
  - 특정 평가 지표 렌더링을 위한 독립 실행 파일들.

### 2.2 `code/` 디렉토리 모듈
- **`code/plot_all_convergence.py`**: 개별 모델 학습 로그 CSV 파일들(`qlearning_train_log.csv`, `resnet_train_log.csv` 등)을 개별 읽기하여 수렴 곡선을 시각화.
- **`code/plot_sweep.py`**: `sweep_density_results_v2.csv` 기반 차량 밀도 변화에 따른 Energy Efficiency, AoI, CBR 그래프 생성. IEEE rcParams 폰트 기본 설정 포함.
- **`code/plot_complexity.py`**: FLOPs 및 Parameter 수 비교 그래프 및 표 생성.

---

## 3. 생성해야 할 필수 그래프 종류 분석 (10대 그래프 세트)

IEEE 논문의 결과 및 분석(Results & Discussion) 섹션에 반드시 포함되어야 할 10종 필수 시각화 그래프 항목입니다.

| 번호 | 그래프 명칭 | 축 정의 (X축 / Y축) | 주요 목적 및 전달 메시지 |
|---|---|---|---|
| 1 | **Reward Convergence** | Episode / Cumulative Reward | 14~16개 전체 모델의 에피소드별 수렴 속도 및 학습 안정성 비교 |
| 2 | **CBR Trace** | Time (s) [0~100] / CBR [0~1.0] | 시간 흐름에 따른 CBR 변동 및 ETSI 한계선(0.6) 준수 여부 증명 |
| 3 | **PDR vs Vehicle Density** | Density (veh/km) [20~200] / PDR (%) | 밀도 증가 시 통신 신뢰성(Packet Delivery Ratio) 우수성 입증 |
| 4 | **AoI vs Vehicle Density** | Density (veh/km) [20~200] / Mean AoI (ms) | 밀도 증가 시 정보 신선도(Age of Information) 유지 능력 증명 |
| 5 | **CBR CDF** | CBR [0~1.0] / Cumulative Probability | 고밀도(100 vehicles)에서 CBR이 0.6을 초과하는 혼잡 위험율 비교 |
| 6 | **PDR vs Transmission Distance** | Distance (m) [25~275] / PDR (%) | 송수신 거리 증가에 따른 신호 감쇄 환경에서의 PDR 유지력 비교 |
| 7 | **Performance vs Vehicle Speed** | Speed (km/h) [30~120] / PDR, AoI, CBR | 차량 속도 변화에 따른 알골즘의 강건성(Robustness) 검증 |
| 8 | **Ablation Study Convergence** | Episode / Cumulative Reward | REMO-DQN 구성 요소(ResNet, MoE, Dueling) 단계별 기여도 검증 |
| 9 | **MoE Routing Weight Distribution** | Vehicle Density / Routing Weight (%) | 차량 밀도에 따른 3개 Expert(Low/Mid/High) 라우팅 비율 Stackplot |
| 10 | **Hardware Complexity & Feasibility** | Models / Params (K), FLOPs (MFLOPs) | 엣지 장치(OBU) 배포 가능성을 증명하는 복잡도 바 차트/테이블 |

---

## 4. IEEE 스타일 규격 요구사항 분석

IEEE Transactions 및 Magazine 규격을 충족하기 위한 폰트, 레이아웃, 색상, 가독성, DPI 등의 세부 스타일 명세입니다.

### 4.1 폰트 및 텍스트 규격
- **Font Family**: `Times New Roman` (또는 `DejaVu Serif`, `serif` 계열). LaTeX font rendering (`text.usetex = True` 사용 가능 환경 지원).
- **Font Sizes**:
  - Axis Title (Label): **10 pt ~ 12 pt**
  - Axis Ticks (Numbers): **8 pt ~ 10 pt**
  - Legend: **8 pt ~ 9 pt**
  - Figure Title (필요 시): **11 pt ~ 12 pt Bold**

### 4.2 차트 크기 및 비율 (Dimensions & Margins)
- **Single-Column Figure**: 폭 3.5 inches (약 8.89 cm), 높이 2.62 inches (4:3 비율).
- **Double-Column Figure**: 폭 7.0 inches (약 17.78 cm), 높이 3.5 ~ 4.5 inches.
- **Bounding Box & Margins**: `bbox_inches='tight'`, `pad_inches=0.04`를 적용하여 잘림 현상 방지.

### 4.3 색상 및 선 스타일 명세 (Grayscale Printing Compatibility)
- **색상 지정**: `visualizer/config.md`의 Hex Color 사전 적용.
  - Proposed (`REMO-DQN`): `#FF0000` (Red), `linewidth=3.0`, `zorder=99`, Marker `*`.
  - Baselines: `#000000`, `#8B4513`, `#FF69B4`, `#D3D3D3`, `#87CEEB`, `#0000FF`, `#000080` 등. `linewidth=1.5`.
- **흑백 가독성(Black & White Print)**: 라인 전용 그래프는 명확한 Line Style (`-`, `--`, `-.`, `:`) 및 distinct Marker (`x`, `v`, `^`, `<`, `.`, `s`, `p`, `h`, `+`, `d`, `*`, `D`, `o`)를 필수 혼용하여 흑백 인쇄 시에도 완벽히 구별 가능해야 함.

### 4.4 범례 및 그리드 규격
- **Legend Location**: 모델 수가 14~16개로 매우 많으므로 그래프 본문을 가리지 않도록 그래프 외부 우측(`bbox_to_anchor=(1.05, 1)`, `loc='upper left'`) 또는 상단 다단 배치(`loc='upper center'`, `bbox_to_anchor=(0.5, 1.15)`, `ncol=4`).
- **Grid**: `plt.grid(True, linestyle='--', alpha=0.5, color='#d3d3d3')`.

### 4.5 출력 해상도 및 파일 포맷
- **Resolution**: 최소 300 DPI (권장 600 DPI).
- **File Formats**:
  - 논문 인쇄/컴파일용 Vector 포맷: `.pdf` / `.eps`
  - 빠른 이미지 미리보기 및 에이전트 검증(Critic)용 Raster 포맷: `.png`

---

## 5. 시각화 데이터 입력 소스 및 매핑 파악

각 그래프 작성을 위해 필요한 데이터 입력 파일과 데이터 컬럼 구조는 다음과 같이 매핑됩니다.

```
[입력 소스 파일] ───> [데이터 추출 및 전처리] ───> [IEEE Visualizer] ───> [결과 그래프 (.pdf/.png)]
```

| 그래프 종류 | 입력 소스 파일 경로 | 주요 필드 / 컬럼 | 전처리 및 매핑 로직 |
|---|---|---|---|
| **1. Reward Convergence** | `coder/data/reward_convergence.csv` 또는 `data/models/*_convergence.csv` | `Episode`, `[Model_Names...]` | Episode별 Cumulative Reward 추출 및 Smooth (window=5) 적용 옵션 |
| **2. CBR Trace** | `coder/data/cbr_trace.csv` 또는 `SA1_arrays.json` | `Time`, `[Model_Names...]` | 시간(0~100초) 흐름별 CBR 값 plotting + y=0.6 점선 가이드라인 추가 |
| **3. PDR vs Density** | `eval_density_results.csv` (또는 `coder/data/raw_metrics_density.csv`) | `method`, `n_vehicles`, `PDR_mean`, `seed` | `method`별 `n_vehicles` (20~200) 그룹화 후 `PDR_mean` 평균 및 errorbar 계산 |
| **4. AoI vs Density** | `eval_density_results.csv` | `method`, `n_vehicles`, `AoI_mean`, `seed` | `method`별 `n_vehicles` 그룹화 후 `AoI_mean` 평균 및 errorbar 계산 |
| **5. CBR CDF** | `SA1_arrays.json` | `param_value=100`, `cbr_history` | n_vehicles=100 조건에서 CBR 리스트 추출 -> `np.sort` 및 CDF ($y = i / (N-1)$) 계산 |
| **6. PDR vs Distance** | `coder/data/pdr_vs_distance.csv` 또는 `SA1_arrays.json` | `Distance`, `distance_pdr` | Distance buckets [25, 75, 125, 175, 225, 275m]별 PDR 평균 계산 |
| **7. Performance vs Speed**| `eval_speed_results.csv` | `method`, `speed_kmh`, `PDR_mean`, `AoI_mean` | `speed_kmh` (30~120 km/h) 축에 따른 PDR 및 AoI 변화 라인 플롯 |
| **8. Ablation Convergence** | `coder/data/ablation_study.csv` 또는 `data/ablation_structure/*` | `Episode`, `Vanilla DQN`, `DQN+MoE`, `REMO-DQN` | 3가지 소거 모델의 에피소드별 수렴 곡선 대비 |
| **9. MoE Routing** | `coder/data/moe_routing.csv` | `Density`, `Expert1`, `Expert2`, `Expert3` | 차량 밀도에 따른 3개 Expert 가중치 누적 영역 플롯 (`plt.stackplot`) |
| **10. Model Complexity** | `coder/data/hardware_feasibility.csv` 또는 `calc_flops_all.py` | `Model`, `Parameters (K)`, `FLOPs (MFLOPs)` | 막대 그래프(Bar plot) 및 비교 테이블 생성 |

---

## 6. 시각화 구현 파이프라인 설계 (Architecture & Implementation Plan)

구현 단계에서 시각화를 효율적이고 일관되게 자동 처리하기 위한 4단계 파이프라인 구조입니다.

```
+-------------------------------------------------------------------------+
| Module 1: IEEE Style Manager (ieee_style.py)                            |
|  - Load config.md color/marker/z-order maps                             |
|  - Configure Matplotlib rcParams (Serif fonts, 300/600 DPI, tight_layout)|
+-------------------------------------------------------------------------+
                                   │
                                   ▼
+-------------------------------------------------------------------------+
| Module 2: Data Preprocessor & Loader (data_aggregator.py)              |
|  - Parse eval_density_results.csv, eval_speed_results.csv, train logs   |
|  - Standardize model names via DATA_TO_CONFIG mapping                   |
|  - Calculate mean, std over seeds, handle missing metrics               |
+-------------------------------------------------------------------------+
                                   │
                                   ▼
+-------------------------------------------------------------------------+
| Module 3: Specialized Graph Renderers (renderers/*.py)                  |
|  - render_convergence(): Fig 1, Fig 8                                   |
|  - render_density_sweep(): Fig 3, Fig 4                                 |
|  - render_speed_sweep(): Fig 7                                          |
|  - render_cbr_cdf_trace(): Fig 2, Fig 5                                 |
|  - render_pdr_distance(): Fig 6                                         |
|  - render_moe_routing_complexity(): Fig 9, Fig 10                       |
+-------------------------------------------------------------------------+
                                   │
                                   ▼
+-------------------------------------------------------------------------+
| Module 4: Master Pipeline Automation (generate_ieee_plots.py)           |
|  - One-click execution to export all figures                            |
|  - Output directories: paper/data/plots/ (.pdf, .eps, .png)             |
+-------------------------------------------------------------------------+
```

### 6.1 세부 모듈 설계
1. **`ieee_style.py`**:
   - IEEE 공인 스타일(폰트, 라인 두께, 마커, 색상)을 일관되게 주입하는 데코레이터 및 유틸리티 클래스.
   - `REMO-DQN` 자동 강조 로직 포함 (`linewidth=3.0`, `zorder=99`).
2. **`data_aggregator.py`**:
   - `eval_density_results.csv` 및 `eval_speed_results.csv`가 준비되지 않은 초기 단계에서도 안전하게 예외 처리를 수행하고, 데이터 완비 시 자동으로 그룹화 연산을 수행.
3. **`generate_ieee_plots.py`**:
   - 메인 파이프라인 실행 스크립트로, 10종 시각화 그래프를 한번에 생성하며, 고해상도 PNG(300 DPI 이상)와 벡터 PDF를 동시에 생성하여 논문 작성 디렉토리(`/home/imnyj/Workspace/paper4/paper/data/plots/`) 및 시각화 디렉토리에 저장.

---

## 7. 결론 및 결언

- 시각화 관련 스크립트 조사 결과 `visualizer/config.md` 및 `visualizer/plot_utils.py`에 총 16개 모델의 일관된 범례, 색상, 마커 규칙이 이미 잘 정비되어 있음을 확인하였습니다.
- 논문 작성을 위한 10종의 필수 그래프(Convergence, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF, PDR vs Distance, Speed Sweep, Ablation, MoE Routing, Hardware Complexity)의 축, 목적 및 소스 데이터 매핑을 완료하였습니다.
- 본 조사를 바탕으로 모듈화된 IEEE 시각화 자동화 파이프라인(`generate_ieee_plots.py`)을 구축하면, R1(훈련 completion) 및 R2(평가 completion) 데이터 산출 즉시 논문 투고 수준의 그래프를 자동으로 차질 없이 생성할 수 있습니다.
