# Quality & Adversarial Review Report — Milestone 2

**검토 대상**: Milestone 2 (가짜 데이터 삭제 및 Optuna 하이퍼파라미터 재최적화)  
**리뷰어**: reviewer_m2_1 (reviewer, critic)  
**검토 일시**: 2026-08-24T11:46:00+09:00  

---

## 1. Review Summary

**최종 판정**: **APPROVE (승인)**

Milestone 2에서 수행된 가짜/오염 가중치 및 수렴 로그의 퍼지(Purge) 및 백업 격리, `ACTION_DIM=24` 표준화, 4-GPU 분산 병렬 Optuna 재최적화, 그리고 17개 전체 모델(14개 RL + 3개 non-RL)에 대한 실측 민감도 평가가 엄격한 품질 및 무결성 기준을 100% 충족함을 확인하였습니다.

---

## 2. Verified Claims (주요 검증 내역)

| 검증 항목 | 주장 내용 | 검증 방법 및 관찰 결과 | 판정 |
|---|---|---|---|
| **1. 모델 가중치 퍼지 및 백업** | `data/models/` 내 구 가중치 15종 및 과거 합성 수렴 로그 17종 삭제 및 `backup/` 격리 | `find` 명령어로 `backup/` 외부의 `.pth`/`.pkl` 검색 결과 0개 파일 확인 (`exit code 1`). `data/models/` 디렉토리 완전 공백 확인. `backup/legacy_models_20260824/`에 36개 파일 안전 백업 확인. | **PASS** |
| **2. ACTION_DIM=24 일관성** | ETSI CAM 표준 규격인 4개 생성 주기 x 6개 송신 전력 = 24 액션이 14개 RL 모델에 일관되게 적용됨 | `grep_search` 및 코드 검사 결과, `etsi_cam_layer.py`, `run_optuna_all_baselines.py`, `run_optuna_parallel.py`, `regenerate_optunas.py`, 14개 개별 `optuna_*.py` 스크립트 및 14개 에이전트 클래스 전반에 `action_dim=ACTION_DIM` (24) 통일 확인. | **PASS** |
| **3. REMO-DQN 정식 편입** | 제안 모델 `REMO-DQN`(`ResNetMoEAgent`)이 Optuna 탐색 공간 및 Hook 파이프라인에 편입됨 | `run_optuna_parallel.py`, `MODEL_CONFIGS`, `ai_dcc_hook.py`에 `num_experts`(2~4) 등 탐색 파라미터와 함께 완벽 연동 확인. | **PASS** |
| **4. Optuna 최적 파라미터 JSON** | 14개 RL 모델의 최적 하이퍼파라미터가 `data/optuna_best_params.json`에 저장됨 | Python JSON 검증 결과 14개 모델 키 모두 존재, 각 하이퍼파라미터 수치가 TPE Sampler 실측 값으로 온전하게 기록됨 확인. | **PASS** |
| **5. 민감도 테이블 CSV 무결성** | 17개 전체 모델의 실측 성능 지표(PDR, AoI, CBR, 수렴 보상)가 `data/optuna_sensitivity_table.csv`에 기록됨 | 17개 행(REMO-DQN 1위 배치) 검증 완료. 14개 RL 모델의 Hook 인스턴스화 및 예측 스모크 테스트 전원 통과 (`exit code 0`). | **PASS** |

---

## 3. Adversarial Analysis & Stress-Testing (적대적 분석 및 스트레스 테스트)

### 3.1 비RL 3종 모델(ReactDCC, AdaptDCC, Fixed 10Hz)의 지표 동일성 심층 검증
- **도전 과제 (Hypothesis)**: `data/optuna_sensitivity_table.csv`에서 비RL 3개 모델의 PDR(96.99%), AoI(122.78ms), CBR(0.023) 수치가 완전히 일치하여 하드코딩/더미 복사 의혹 제기.
- **코드 및 물리적 시뮬레이션 분석 (Attack & Verification)**:
  - `sim_engine.py` 및 `etsi_cam_layer.py` 코드 추적 결과:
    - 저밀도(n_vehicles=15, 20) 주행 환경에서는 전체 채널 혼잡도 `CBR ~ 0.023`으로 측정됨.
    - `ReactDCC`: `CBR < 0.40` 구간에서 Relaxed 상태로 진입하여 기본 주기 `T_GenCam = 0.1s` (10 Hz), `p_tx = 20 dBm` 유지.
    - `AdaptDCC`: `CBR < 0.60` (Target) 구간에서 `error < 0`이 되어 `T_GenCam`이 `T_min = 0.1s` (10 Hz), `p_tx = 20 dBm` 유지.
    - `Fixed 10Hz`: 고정 `T_GenCam = 0.1s` (10 Hz), `p_tx = 20 dBm` 유지.
  - **결론**: 동일 시드 및 차량 수 환경에서 세 방식 모두 ETSI 규격에 따라 10 Hz / 20 dBm으로 동일하게 송신하므로, 물리적 시뮬레이션 결과가 정확히 일치하는 것이 지극히 정상적인 현상임(정직한 실측의 증거).

### 3.2 14개 RL 에이전트 인터페이스 스트레스 테스트
- 14개 RL 에이전트를 `data/optuna_best_params.json` 파라미터로 직접 인스턴스화하고 `ai_dcc_hook.py`를 통해 5D State 벡터를 주입하여 예측(Predict)을 수행함.
- 14개 모델 모두 `t_act` ∈ `[0.1, 0.2, 0.5, 1.0]`, `p_act` ∈ `[-5, 0, 5, 10, 15, 20]` 범위 내의 정상 액션을 반환함을 100% 검증 완료.

---

## 4. Findings & Minor Recommendations

### [Minor] 단발성 디버깅 스크립트 잔여물 정리 권장
- **위치**: `code/test_sac_hook.py:10`
- **내용**: 과거 단발성 테스트 파일에 `action_dim=16`이 잔여해 있음. 메인 최적화/실행 파이프라인에는 영향을 주지 않으나 혼선을 방지하기 위해 추후 `etc/` 디렉토리로 이동 또는 삭제 권장.

---

## 5. 최종 결론

- **결론**: 무결성 위반(Integrity Violation) 없음. 가짜 데이터 전면 삭제 및 4-GPU 기반 14개 RL 모델 Optuna 재최적화와 17개 모델 실측 민감도 평가가 완벽하게 수행되었음.
- **후속 단계 권고**: Milestone 3(17개 모델 100 에피소드 풀 재학습 및 신규 가중치 생성)으로 즉시 진행 승인.
