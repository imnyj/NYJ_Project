# Milestone 1 Code Modifications Report (`changes.md`)

- **작업자**: Milestone 1 구현 엔지니어 (`worker_m1`)
- **수행 일시**: 2026-08-24
- **작업 디렉토리**: `/home/imnyj/Workspace/paper4/.agents/teamwork_preview_worker_m1`
- **대상 프로젝트**: `/home/imnyj/Workspace/paper4`

---

## 1. 개요
Milestone 1(시뮬레이션 환경 및 메트릭 추출 코드 수정)의 목표는 사후 가상 수식이나 모의(Mock) 데이터에 의존하지 않고, 100% 실제 통신 시뮬레이션 및 신경망 추론 과정에서 **거리별 AoI (`distance_aoi`)**, **스텝별 CBR 시계열 (`cbr_history`)**, **128차원 ResNet 잠재 특징 벡터 및 3차원 Softmax Gating 가중치 (`get_latent_and_gate`)**를 완전히 추출할 수 있도록 핵심 코드를 보완하고 검증하는 것입니다.

---

## 2. 세부 변경 내역

### 2.1 `code/aoi_tracker.py`
1. **거리 구간별 순간 AoI 누적기 추가 (`__init__`, `reset`)**:
   - 6개 통신 거리 구간(0~50m, 50~100m, 100~150m, 150~200m, 200~250m, 250~300m, 중심거리 25, 75, 125, 175, 225, 275m)에 대한 누적 통계 변수 추가:
     - `self.dist_aoi_sum: List[float] = [0.0] * 6`
     - `self.dist_aoi_count: List[int] = [0] * 6`
     - `self.dist_aoi_samples: List[List[float]] = [[] for _ in range(6)]`
   - `reset()` 호출 시 위 누적기들이 안전하게 초기화되도록 구현.
2. **스텝 단위 거리별 AoI 집계 (`step`)**:
   - 웜업 기간 이후(`not self._in_warmup`), 통신 반경(300m) 내 유효 차량 쌍의 유클리드 거리 $d = \sqrt{\Delta x^2 + \Delta y^2}$를 벡터화 계산.
   - 각 쌍의 순간 $\text{AoI} = \min(2000.0, \max(0.0, (t_{\text{sim}} - T_{ij}) \times 1000.0))$ [ms]를 산출하여 해당하는 거리 버킷 $b = \min(\lfloor d / 50 \rfloor, 5)$에 누적.
3. **구간별 평균/표준편차 반환 메서드 구현 (`get_distance_aoi`, `get_distance_aoi_dict`)**:
   - `get_distance_aoi(as_dict=False)`: 6개 거리 구간별 평균 AoI 리스트 `List[float]` (기본값) 또는 딕셔너리 반환.
   - `get_distance_aoi_dict()`: `{"distances": [25, 75, 125, 175, 225, 275], "aoi_mean": [...], "aoi_std": [...]}` 형태의 표준 스키마 딕셔너리 반환.

### 2.2 `code/sim_engine.py`
1. **시뮬레이션 결과 딕셔너리 연동 (`SimulationRunner.run`)**:
   - `distance_aoi = aoi_tracker.get_distance_aoi()`를 호출하여 에피소드 실행 결과 딕셔너리에 `"distance_aoi": distance_aoi` 필드 추가.
   - 하위 호환성을 위해 `"M1_mean_AoI"` 키를 함께 제공.
2. **`cbr_history` 시계열 기록 확인 및 보완**:
   - 매 스텝(0.1초) 계산된 글로벌 채널 점유율 `cbr_mean`이 웜업 이후 `cbr_history` 리스트에 순차적으로 기록되어 결과 딕셔너리에 온전히 포함됨을 확인.

### 2.3 `code/resnet_moe_agent.py`
1. **`get_latent_and_gate(state)` 메서드 구현**:
   - 5차원 입력 상태 $s \in \mathbb{R}^5$ (단일 벡터 `(5,)` 또는 배치 `(B, 5)`)를 입력받아:
     - 2블록 ResNet Feature Extractor로부터 128차원 잠재 특징 벡터 $z \in \mathbb{R}^{128}$ (또는 `(B, 128)`) 추출.
     - Softmax Gating Network로부터 3차원 전문가 가중치 $g \in \mathbb{R}^3$ (또는 `(B, 3)`) 추출.
   - `eval()` 모드에서 `torch.no_grad()`로 안전하게 추론하고, 기존 훈련/평가 모드 상태를 보존.
   - NumPy `ndarray` 튜플 `(latent_features, gating_weights)` 형태로 반환.

### 2.4 `code/moe_agent.py`
1. **베이스라인 `MoEAgent` 인터페이스 통일**:
   - `MoEAgent` 클래스에도 동일한 인터페이스의 `get_latent_and_gate(state)`를 구현하여 모든 MoE 계열 에이전트의 일관된 잠재 벡터 및 게이팅 가중치 추출 지원.

### 2.5 `code/test_m1_audit.py` (신규 검증 스위트)
1. **`TestAoITrackerDistance`**: 6개 거리 구간(25m~275m)에 위치한 차량 쌍의 AoI가 각 버킷에 정확히 누적되고 평균/표준편차가 수학적으로 일치하는지 단위 테스트.
2. **`TestMoEActivationExtraction`**: `ResNetMoEAgent` 및 `MoEAgent`의 `get_latent_and_gate` 단일/배치 입력 처리, 차원 정합성(`128`, `3`), Softmax 합산(=1.0) 검증.
3. **`TestSimEngineMetrics`**: 실제 SUMO 시뮬레이션을 구동하여 반환 딕셔너리 내 `AoI_mean`, `CBR_mean`, `PDR_mean`, `cbr_history`, `distance_pdr` (6 bins), `distance_aoi` (6 bins)의 유효성 및 범위 검증.

---

## 3. 파일 락 및 감사 로깅 준수 현황
- `code/aoi_tracker.py`: LockManager 획득/해제, AuditLogger 기록 완료
- `code/sim_engine.py`: LockManager 획득/해제, AuditLogger 기록 완료
- `code/resnet_moe_agent.py`: LockManager 획득/해제, AuditLogger 기록 완료
- `code/moe_agent.py`: LockManager 획득/해제, AuditLogger 기록 완료
- `code/test_m1_audit.py`: LockManager 획득/해제, AuditLogger 기록 완료
- `logs/execution_notes.md`: LockManager 획득/해제, AuditLogger 기록 완료 (Rule 13 반영)

---

## 4. 검증 결과 요약

### 4.1 신규 Milestone 1 감사 테스트 (`code/test_m1_audit.py`)
```
============================= test session starts ==============================
rootdir: /home/imnyj/Workspace/paper4
collected 6 items

code/test_m1_audit.py::TestAoITrackerDistance::test_distance_bins_accumulation PASSED [ 16%]
code/test_m1_audit.py::TestAoITrackerDistance::test_empty_bins_and_reset PASSED [ 33%]
code/test_m1_audit.py::TestMoEActivationExtraction::test_resnet_moe_single_state PASSED [ 50%]
code/test_m1_audit.py::TestMoEActivationExtraction::test_resnet_moe_batch_state PASSED [ 66%]
code/test_m1_audit.py::TestMoEActivationExtraction::test_moe_agent_latent_and_gate PASSED [ 83%]
code/test_m1_audit.py::TestSimEngineMetrics::test_simulation_metrics_export PASSED [100%]

============================== 6 passed in 5.36s ===============================
```

### 4.2 전체 연계 회귀 테스트 (`code/test_*.py`)
- `test_m1_audit.py`: 6 passed
- `test_c1_c2_wiring.py`: 4 passed
- `test_c3_reward.py`: 7 passed
- `test_m7_nest.py`: 7 passed
- `test_m8_local_cbr.py`: 7 passed
- **총 31개 테스트 100% PASS** (0 Failure, 0 Error, 0 Regression)
