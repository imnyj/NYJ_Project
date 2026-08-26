# Forensic Integrity Audit Report (포렌식 무결성 감사 보고서)

**감사관**: `auditor_final_1` (Role: Forensic Integrity Auditor)  
**수신자**: 상위 오케스트레이터 (`parent` / `ba919436-abcb-4a7c-adf4-43263891d24a`)  
**감사 대상**: SUMO V2I AoI 강화학습 스케줄링 파이프라인 전체 (`src/`, `verify_environment.py`, `tests/`, `results/`)  
**감사 일시**: 2026-08-27  
**적용 프로파일**: General Project / Benchmark Mode (무결성 최상위 엄격 모드)  
**최종 판정**: **CLEAN (무결성 완벽 통과 및 200,000 스텝 헤비 훈련 진입 승인 준비 완료)**

---

## 1. Observation (직접 관찰 결과 및 실증 증거)

### 1.1 정적 분석 (Static Analysis & Anti-Mocking Verification)
1. **합성 모의(SyntheticVehicle) 및 가짜 kinematic 루프 완전 제거 확인**:
   - `grep_search`를 통해 `src/` 전체에 대해 `SyntheticVehicle`, `EvalSyntheticVehicle`, `v_pos = {v: ...}` 등의 가짜 모의 코드를 검색한 결과, 활성 소스 코드(`src/hot_swap_trainer.py`, `src/hpo.py`, `src/evaluate.py`, `src/aoi_env.py`) 내에 일체의 가짜 우회 로직이 존재하지 않음을 확인하였습니다.
   - 과거 버전의 가짜 구현체는 GEMINI.md 규칙 5에 따라 `backup/` 디렉토리로 안전하게 격리되어 프로젝트 실행 경로와 완전히 분리되어 있음을 확인하였습니다 (`backup/evaluate.py_old`, `backup/hpo.py_old`).
2. **하드코딩된 더미 반환값 및 조작된 평가 점수 부재**:
   - 9종 베이스라인 모델(`src/baselines/`: `HybridPPO`, `HybridSAC`, `HybridTD3`, `MAPPO`, `HyARPPO`, `MPDQN`, `PureAoI`, `DuelingQAoI`, `SACAoI`) 모두 실질적인 PyTorch 신경망 계층(`nn.Module`), 손실 함수, 역전파 옵티마이저, 탐색 전략을 정상 탑재하고 있습니다.
   - `results/eval/eval_leaderboard.csv` 및 `results/hpo/optuna_best_params.csv`는 실시간 시뮬레이션 및 Optuna Study 결과로부터 계산된 동적 데이터이며, 소스 코드 내 하드코딩된 리더보드/점수 상수는 존재하지 않습니다.

### 1.2 런타임 추적 및 4대 Anti-Mocking 단언문 검증 (Runtime Tracing)
1. **`src/aoi_env.py` 내 4대 하드코딩 런타임 단언문 실증**:
   - **Assertion 1 (시간 전진 검증, L687-697)**: `sumo.simulationStep()` 호출 후 `current_time > self._prev_sim_time` 검사.
   - **Assertion 2 (물리 변위 $\Delta x > 0$ 검증, L698-726)**: 속도 $v > 1.0\text{ m/s}$인 이동 차량의 실제 좌표 변위 $dist\_moved > 0.0$ 검증.
   - **Assertion 3 (5.9GHz Rayleigh 페이딩 채널 연산 검증, L800-814)**: `Communications.judge_uplink()` 호출 및 유효 확률 $0.0 \le P_{\text{succ}} \le 1.0$ 검증.
   - **Assertion 4 (보상 수식 정합성 및 음수성 검증, L894-913)**: $R_t = -(w_1 e^2_{\text{norm}} + w_2 P_{\text{norm}} + w_3 C_{\text{freq}} + w_4 I_{\text{redundant}}) \le 0$ 수식 일치 검증.
2. **독립 검증 스크립트 `verify_environment.py` 실행 결과**:
   - 5개 페이즈(SUMO 파일 생성, 리셋 웜업, 20스텝 물리 롤아웃, 무선 채널 SINR, 의도적 결함 주입 단언문 크래시 테스트) 전수 실행 결과 **종료 코드 0 (Exit Code 0)** 및 100% 정상 통과를 직접 확인하였습니다.

### 1.3 아키텍처 준비도 (Architecture Readiness for 200k Steps)
1. **`src/hot_swap_trainer.py`**:
   - Act/Rest 모델 하드웨어 분리(`cuda:0`/`cuda:1` 또는 CPU), 비차단 큐(`TransitionStreamer`), NaN/Inf 사전 검증 가드를 갖춘 `DualModelHotSwapManager` 구현 완료.
   - 200,000 스텝(2,000 steps $\times$ 100 episodes) 대응 TensorBoard(`SummaryWriter`) 실시간 로깅 및 주기적/최고 성능 체크포인트(`checkpoints/`) 저장 로직 완비.
2. **`src/hpo.py`**:
   - 9종 베이스라인 알고리즘별 맞춤형 하이퍼파라미터 탐색 공간 정의 및 진성 `AoiV2IEnv` 상의 다중 시드 평가 기반 Optuna Study 파이프라인 완비.
3. **`src/evaluate.py`**:
   - 5개 밀도(15~55 veh/km) $\times$ 5개 시드(42, 101, 2024, 777, 999)에 걸친 10종 모델(휴리스틱 + 9종 RL) 250회 평가 및 6대 IEEE TWC 표준 지표(Mean/Peak AoI, Outage, Tracking Error, Power/Energy, Jain's Fairness) 산출 파이프라인 완비.

### 1.4 정지 프로토콜 준수 (Halt Protocol Verification)
- 대규모 200,000 스텝 무거운 연산 루프가 임의로 실행되지 않았으며, 10스텝 단기 더미 검증(`tests/test_dummy_verification.py`, 3.41초 완료)을 통해 수학적·기능적 무결성만을 사전 검증한 후 사용자의 코드 리뷰를 대기하는 정지(Halt) 상태를 엄격히 유지하고 있습니다.

### 1.5 전체 테스트 스위트 독립 실행 결과
- `pytest tests/ -v`: **199 passed / 0 failed (100% Pass Rate, 실행 시간 43.74s)**
- `pytest tests/test_dummy_verification.py -v`: **14 passed in 3.41s**
- `pytest tests/test_aoi_env_genuine.py -v`: **11 passed in 3.03s**

---

## 2. Logic Chain (논리적 추론 체계)

1. **[정적 분석 관찰에 근거]**: `SyntheticVehicle`과 같은 가짜 모의 루프가 활성 소스 코드에서 완전히 제거되고 레거시 파일이 `backup/`으로 격리되었으며, 9종 모델이 실제 신경망 가중치 역전파를 수행하므로 외형만 갖춘 가짜(Facade) 구현체 또는 조작된 출력(Fabricated Output) 위반이 전혀 없습니다.
2. **[런타임 추적 및 단언문 관찰에 근거]**: `aoi_env.py`의 `step()` 내에 내장된 4대 단언문이 실제 SUMO 시간 전진, 이동 차량 물리 변위($\Delta x > 0$), 5.9GHz Rayleigh 페이딩 간섭 계산, 수학적 보상 수식을 매 스텝 강제하고 있으며, `verify_environment.py`의 결함 주입 테스트를 통해 임의의 조작이나 우회 시 즉각적인 `AssertionError` 크래시가 발생함을 증명하였습니다.
3. **[아키텍처 및 정지 프로토콜 관찰에 근거]**: `hot_swap_trainer.py`, `hpo.py`, `evaluate.py`가 모두 진성 `AoiV2IEnv`와 직접 연결되어 200k 스텝 훈련을 수행할 준비가 완벽히 갖추어져 있으며, 단기 10스텝 더미 검증을 통해 파이프라인 무결성을 입증한 후 사용자 리뷰를 위해 안전하게 대기 중이므로 모든 제약조건과 프로토콜을 충족합니다.

---

## 3. Caveats (주의 사항 및 사후 관리 사항)

1. **SUMO 환경 변수 경로**:
   - 시스템 가상환경(`venv`) 내의 `sumo` 바이너리를 안정적으로 호출하기 위해 `aoi_env.py` 및 `verify_environment.py` 상단에서 `PATH`에 `/home/imnyj/venv/bin`을 자동 주입하고 있습니다.
2. **200,000 스텝 헤비 훈련 진입 시 자원 관리**:
   - 200k 스텝 대규모 훈련(2,000 steps $\times$ 100 episodes) 실행 시 메모리 누수를 방지하기 위해 100스텝마다 `gc.collect()` 및 `torch.cuda.empty_cache()`가 가동되도록 설계되어 있습니다.
3. **사용자 승인 후 훈련 착수**:
   - 본 포렌식 감사 완료 후 사용자의 명시적 승인(Green Light)이 있어야 대규모 200,000 스텝 학습을 개시할 수 있습니다.

---

## 4. Conclusion (최종 결론)

- **포렌식 무결성 감사 결과**: **CLEAN (무결성 위반 0건)**
- 모든 가짜 모의 루프(`SyntheticVehicle`, `EvalSyntheticVehicle`) 전면 제거 완료 확인.
- `NetSim.py` 및 `Communications.py`의 진성 물리 시뮬레이션 매 스텝 연동 및 4대 Anti-Mocking 단언문 실동작 확인.
- 9종 하이브리드 액션 공간 베이스라인 RL 모델 및 핫스왑 트레이너의 200k 스텝 확장 구조 준비 완료 확인.
- 전체 199개 단위/통합 테스트 100% 통과 (Pass Rate 100%).
- 대규모 연산 착수 전 정지 프로토콜(Halt Protocol) 완벽 준수 확인.

---

## 5. Verification Method (독립 검증 명령어 증거)

후속 검증관 또는 사용자는 다음 독립 명령어를 통해 본 감사 결과를 즉시 재현할 수 있습니다:

```bash
# 1. 독립 환경 자가 검증 스크립트 실행 (Exit Code 0 확인)
/home/imnyj/venv/bin/python /home/imnyj/Workspace/paper4/coder/verify_environment.py

# 2. 10스텝 엔드투엔드 Short Dummy Run 검증 테스트 (14개 항목, ~3.4초 소요)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_dummy_verification.py -v

# 3. 진성 환경 및 Anti-Mocking 단위 테스트 (11개 항목, ~3.0초 소요)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/test_aoi_env_genuine.py -v

# 4. 전체 프로젝트 199개 통합 회귀 테스트 스위트 실행 (~43초 소요)
/home/imnyj/venv/bin/pytest /home/imnyj/Workspace/paper4/coder/tests/ -v
```
