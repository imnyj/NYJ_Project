# Experimenter Memory

## [2026-04-30] [Stage 1: design] — experiment_spec.json 작성 완료

### 작업 개요
- Stage 1 (design) 수행 완료.
- 출력 파일: `/home/imnyj/papers/paper1/paper/experiment/experiment_spec.json`
- 시뮬레이션/그래프 생성 없음 (design-only).

### 설계 근거

#### 1. 실험 목적
- Primary: dwell_cur / dwell_nxt MAE·RMSE·MAPE 기준 ST-MBAN이 모든 baseline 상회 증명
- Secondary: dwell time 예측 정확도 → V2I Precaching hit-rate 직결 검증
- Tertiary: RSU-Local Snapshot 분산 학습에서도 충분한 일반화 성능 유지

#### 2. 시나리오 (5개)
| ID | 이름 | 설명 |
|----|------|------|
| S1 | urban_grid_peak | 4x4 RSU 격자, peak 시간대, 차량 밀도 HIGH |
| S2 | urban_grid_offpeak | 동일 토폴로지, off-peak, 차량 밀도 LOW~MEDIUM |
| S3 | sensitivity_rsu_radius | RSU 통신반경 민감도 (400~1000m) |
| S4 | sensitivity_vehicle_density | 차량 밀도 배율 민감도 (x0.5~x2.0) |
| S5 | sensitivity_signal_cycle | 신호 주기 민감도 (60/90/120s) |

#### 3. 알고리즘 선정 근거
총 9개 (제안 1개 + baseline 8개):

- **A0 ST-MBAN** (제안): 3-Branch Multi-Head Attention + ResBlock Decoder. model_stmban.py 기구현.
- **A1 Constant-Velocity** (heuristic): d_l_c/v_c_a 단순 물리 계산. ML 없는 하한선. (needs_reference: true)
- **A2 Linear Regression** (classical ML): sklearn LRBaseline. 선형 모델 비선형성 결여 정량화. (needs_reference: true)
- **A3 Popularity-Only** (cat=popularity): refs #1, #4, #57. Zipf 분포 인기도만 사용, 이동성 미반영 한계 시연.
- **A4 LSTM Mobility-Only** (cat=mobility): refs #18, #42, #43. 운동학 변수만 LSTM 입력. Traffic/Social 누락 오차 정량화.
- **A5 Hybrid (AFL+DRL)** (cat=hybrid): refs #21, #46, #63. 인기도+이동성 병합 FL 방식 대비 정밀 dwell 예측 효과 비교.
- **A6 ST-CVAE** (prior model): model.py + train.py 기구현. 생성모델 vs 결정론적 Multi-Branch 비교. (self-citation, needs_reference: true)
- **A7 FT-Transformer** (DL): refs #7, #59, #62. 단일 통합 Transformer 대비 Multi-Branch Attention 이점 입증.
- **A8 Snapshot RSU-Local MLP** (distributed): refs #27, #48, #39. 동일 RSU-Local 조건에서 architecture 효과 분리 검증.

#### 4. 메트릭 선택 근거
- 예측: MAE/RMSE/MAPE x [dwell_cur, dwell_nxt] — dwell time 연구 표준 메트릭
- Calibration: Pinball Loss / Coverage — 확률 모델(ST-CVAE) 비교 시 선택적
- Precaching: cache_hit_ratio, content_delivery_success_rate, latency_reduction_pct — V2I 효과 직결 지표
- Efficiency: inference_time_ms (100ms 이하 목표), model_size_MB, training_time_epoch_s

#### 5. 입력 변수 구성
- Kinematic Branch (K): 13개 — 속도·거리·이동학 변수
- Traffic Control Branch (T): 6개 — 신호등 상태·대기시간·대기열 (cyclical encoding 포함)
- Social Branch (S): 11개 — 주변 차량 밀도·혼잡도·점유율
- Total: 30개 (dataset.py FEATURE_COLS 일치)
- Target: dwell_cur, dwell_nxt (TARGET_COLS 일치)

#### 6. 출력 파일 계획 (10개 CSV)
- data/S1_peak_prediction_metrics.csv
- data/S2_offpeak_prediction_metrics.csv
- data/S1_peak_precaching_metrics.csv
- data/S2_offpeak_precaching_metrics.csv
- data/S1_peak_efficiency_metrics.csv
- data/S3_sensitivity_rsu_radius.csv
- data/S4_sensitivity_vehicle_density.csv
- data/S5_sensitivity_signal_cycle.csv
- data/ablation_branch_contribution.csv
- data/ablation_fusion_mechanism.csv

#### 7. 데이터 의존성
- dataset_pending: true — SUMO 시뮬 데이터 미수집
- 데이터 도착 시 Stage 2에서 dataset.py FEATURE_COLS 컬럼 매핑 확인 후 진행
- inf_clip: 5000.0, 음수 타겟 제거, train/val/test 70/15/15 시계열 순서 분할

#### 8. 금지 사항 준수
- 시뮬레이션 코드 실행 없음 OK
- 그래프 생성 없음 OK
- st_cvae_baseline/ 덮어쓰기 없음 OK
- references.json 미수록 baseline: needs_reference:true 명시 (A1, A2, A6) OK

### 다음 단계
- Stage 2 (implement): 데이터셋 수집 완료 후 실제 학습 코드 실행 및 결과 CSV 생성
- 현재 status: running (implement 단계 남음)