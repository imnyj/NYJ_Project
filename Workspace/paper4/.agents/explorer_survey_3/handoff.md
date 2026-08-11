# Handoff Report — Survey Explorer 3

**작성자**: Survey Explorer 3  
**작성일시**: 2026-08-11T15:36:00Z  
**작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3`  
**Handoff 유형**: Hard (Task Complete)

---

## 1. Observation (직접 관찰 내용)

- **프로젝트 및 요구사항 파일**:
  - `/home/imnyj/Workspace/paper4/.agents/ORIGINAL_REQUEST.md`: R3 요구사항으로 추출된 데이터와 학습 수렴 로그 기반 IEEE 스타일 비교 그래프(Convergence, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF 등) 자동 생성 스크립트 작성 및 실행 명시.
  - `/home/imnyj/Workspace/paper4/walkthrough.md`: 5개 핵심 섹션(1. Model Convergence, 2. Scalability: AoI/CBR vs Density, 3. Reliability: PDR over Distance, 4. Congestion Management: CBR CDF, 5. Model Complexity) 분석 설명 및 렌더링 그래프 캡션 확인.

- **기존 시각화 스크립트 및 설정 파일**:
  - `/home/imnyj/Workspace/paper4/visualizer/config.md`: 총 16개 모델(Fixed 10Hz ~ REMO-DQN)의 범례 순서, 모델 카테고리, 공식 이름, Hex Color Code (`#000000` ~ `#FF0000`), Line Style, Marker 사전 정의 확인 (Line 8~25).
  - `/home/imnyj/Workspace/paper4/visualizer/plot_utils.py`: `STYLE_MAP` 딕셔너리 (Line 4~21) 및 `DATA_TO_CONFIG` 딕셔너리 (Line 23~32), `get_style()`, `apply_legend()` 유틸리티 함수 확인.
  - `/home/imnyj/Workspace/paper4/visualizer/plot_all.py`: `config.md` 파싱 후 `coder/data/`의 CSV 데이터들을 읽어서 `1_reward_convergence.png`부터 `10_pdr_vs_distance.png`까지 시각화하는 일괄 처리 로직 확인 (Line 59~241).
  - `/home/imnyj/Workspace/paper4/code/plot_all_convergence.py`: `qlearning_train_log.csv` ~ `resnet_train_log.csv` 등 12개 모델 개별 로그 파일 처리 로직 확인 (Line 5~18).
  - `/home/imnyj/Workspace/paper4/code/plot_sweep.py`: `sweep_density_results_v2.csv` 파일 처리 및 IEEE `rcParams` 기본 세팅 확인 (Line 6~16).

- **입력 데이터 파일 및 위치**:
  - `coder/data/reward_convergence.csv` (7 lines, 1206 bytes): Episode vs 12개 모델 Cumulative Reward.
  - `coder/data/raw_metrics_density.csv` (122 lines, 8767 bytes): `method`, `scenario`, `n_vehicles`, `seed`, `runtime_sec`, `n_cam_events`, `CBR_mean`, `AoI_mean`, `PDR_mean`, `energy_efficiency`, `ETSI_compliance` 필드 확인.
  - `coder/data/cbr_trace.csv`, `coder/data/pdr_vs_distance.csv`, `coder/data/hardware_feasibility.csv`, `coder/data/moe_routing.csv` 등 데이터셋 확인.
  - `data/evaluation/`: 현재 빈 디렉토리이며, R2 평가 완료 시 `eval_density_results.csv` 및 `eval_speed_results.csv`가 저장될 예정임.

---

## 2. Logic Chain (논리적 연결 고리)

1. **관찰 1 (요구사항)**: R3 지침에 따라 수렴 곡선, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF 등을 포함한 IEEE 규격 그래프 작성이 요구됨.
2. **관찰 2 (설정 및 모듈 상태)**: `visualizer/config.md`와 `visualizer/plot_utils.py`에 이미 16개 비교군 모델에 대한 표준 Hex Color, Line Style, Marker 및 제안 모델(`REMO-DQN`)의 강조(두께 3.0, z-order 99) 규칙이 정의되어 있음.
3. **관찰 3 (입력 데이터 소스)**: `coder/data/`에 기존 시뮬레이션 샘플 CSV 파일들이 존재하며, R2 실행 결과 생기는 `eval_density_results.csv` 및 `eval_speed_results.csv`가 메인 입력 데이터로 연결되는 구조임.
4. **추론 및 결론**: 
   - 논문 작성을 위한 10종의 필수 그래프(Convergence, CBR Trace, PDR vs Density, AoI vs Density, CBR CDF, PDR vs Distance, Speed Sweep, Ablation, MoE Routing, Hardware Complexity) 세트 및 데이터 매핑을 완벽히 정립함.
   - IEEE 규격(폰트 Times New Roman, 3.5인치/7인치 규격, 외부 범례, 흑백 가독성 마커/선스타일 혼용, 300+ DPI PDF/PNG 출력)을 적용한 파이프라인(`generate_ieee_plots.py`) 설계 완료.

---

## 3. Caveats (주의사항 및 한계)

- 현재 R1(대규모 멀티프로세싱 모델 훈련) 및 R2(차량 밀도/속도 변동 성능 평가)가 완료 진행 중인 단계이므로, `data/evaluation/eval_density_results.csv` 및 `eval_speed_results.csv` 실제 파일은 R2 완료 후 최종 채워질 예정임.
- 그래프 렌더링 시 LaTeX 엔진(`text.usetex = True`) 미설치 환경을 대비해 `DejaVu Serif` / `serif` 폰트로 자동 폴백(Fallback)되도록 파이프라인에서 예외 처리가 고려되어야 함.

---

## 4. Conclusion (최종 결론)

- V2X 하이브리드 DRL 제안 모델(`REMO-DQN`) 및 13종 이상 비교군의 논문 투고용 10대 필수 그래프 세트 정의 및 IEEE 스타일 규격 요구사항 분석 완료.
- 입력 데이터 파일 구조(학습 로그, 밀도/속도 평가 CSV, CBR/PDR 버킷 어레이 JSON)와 그래프 출력 간의 매핑 명세 수립 완료.
- 상세 분석 결과는 `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3/analysis.md`에 작성 완료됨.

---

## 5. Verification Method (독자적 검증 방법)

1. **분석 문서 확인**:
   - `view_file` 도구로 `/home/imnyj/Workspace/paper4/.agents/explorer_survey_3/analysis.md`를 조회하여 10대 그래프 정의, IEEE 규격 분석, 데이터 매핑 테이블, 구현 파이프라인 구성을 검증.
2. **설정 모듈 확인**:
   - `view_file` 도구로 `/home/imnyj/Workspace/paper4/visualizer/config.md` 및 `plot_utils.py`를 조회하여 16개 모델 스타일 맵핑 일치 여부 확인.
3. **무효화 조건 (Invalidation Conditions)**:
   - 필수 그래프 10종 중 핵심 지표(PDR, CBR Trace, AoI, CBR CDF 등) 누락 시 분석 무효.
   - IEEE 규격(폰트, linewidth, 외부 범례, DPI 등) 기준 불만족 시 무효.
