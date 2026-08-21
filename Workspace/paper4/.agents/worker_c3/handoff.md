# Handoff Report — Task C-3: 보상 함수 재설계 및 CBR_TARGET 자동 측정

## 1. Observation (관측 내용)
- **기존 보상 함수의 구조적 결함**:
  - `code/ai_dcc_hook.py` (구 L159, L209, L256, L319)에서 보상이 `reward = -1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam`로 계산되고 있었음.
  - `code/sim_engine.py` L50 `TX_DURATION_S = (280 * 8) / 3e6 ≈ 0.0007467s` 하에서 `Fixed10Hz` 기준 차량 밀도별 실제 CBR을 측정한 결과 (`data/cbr_target_measurement.csv`):
    - 밀도 10대: Mean CBR = 0.015~0.016, P95 = 0.024~0.026, Max = 0.028
    - 밀도 30대 (SA2 기본): Mean CBR = 0.038, P95 = 0.063, Max = 0.071
    - 밀도 50대: Mean CBR = 0.049, P95 = 0.079, Max = 0.091
    - 밀도 100대: Mean CBR = 0.051~0.053, P95 = 0.082~0.084, Max = 0.094
  - 물리적으로 CBR이 0.10을 넘기 어려움에도 비현실적인 고정 목표 0.60을 `abs()`로 페널티를 주어, 채널을 비현실적으로 채우도록(10Hz 최대 전송) 강제하는 심각한 왜곡이 발생함.
- **수정 후 상태**:
  - `code/measure_cbr_target.py`를 통해 실측된 피크 CBR(0.0941)의 포화 임계치인 `CBR_TARGET = 0.075`를 산출 및 설정.
  - `code/ai_dcc_hook.py`의 모든 DRL hook 클래스에 목표 초과 벌점(`over`), 요동 억제(`osc`), 정보 노후화(`stale`), 빈도 비용(`cost`)의 4항 보상식 적용 완료.
  - `code/` 내 구버전 `abs(cbr_smoothed - 0.6)` 패턴 검색 결과: **0건**.
  - `python3 code/test_c3_reward.py` 7개 단위테스트 실행: `Ran 7 tests in 0.001s, OK (Exit Code 0)`.

## 2. Logic Chain (논리 전개)
1. **문제점 파악**: `abs(cbr - 0.6)`는 $cbr < 0.6$인 정상 저밀도 상태에서도 큰 음수 벌점을 부과하여, 에이전트가 CBR을 높이기 위해 무조건 최소 주기($T_{GenCam}=0.1$s)로 패킷을 폭주 전송하게 만듦.
2. **해결책 설계**:
   - 혼잡 페널티를 양방향 오차(`abs`)에서 단방향 목표 초과(`over = max(0.0, cbr_smoothed - CBR_TARGET)`)로 변경하여, 목표치 이하에서는 채널을 억지로 채우는 신호를 완전 차단함.
   - 채널 안정성 확보를 위해 이전 스텝과의 CBR 변동량 페널티(`osc = abs(cbr_smoothed - prev_cbr)`) 도입.
   - 정보 신선도(AoI) 보호를 위해 $0.5$초 이상 지연 시에만 노후화 벌점(`stale = max(0.0, dt - 0.5)`) 부과.
   - 불필요한 무선 자원 낭비 방지를 위해 전송 빈도 비용(`cost = 0.1 / T_GenCam`)을 부여.
3. **트레이드오프 검증**:
   - 저밀도($cbr \le 0.075$)에서 $T_{GenCam}=0.1$s (Reward = $-0.050$), $T_{GenCam}=0.5$s (Reward = $-0.010$), $T_{GenCam}=1.0$s (Reward = $-0.155$).
   - 저밀도 최적 행동이 10Hz 최대 전송이 아닌 노후화 임계치(0.5s)에 부합하는 적정 주기로 자연스럽게 수렴함을 입증.

## 3. Caveats (주의 및 특이사항)
- `CBR_TARGET = 0.075`는 현재 `sim_engine.py`에 구현된 802.11p 간이 채널 모델(페이로드 airtime 기반) 하에서 실측된 값입니다. 추후 M-8(국소 CBR 공간 개선) 또는 채널 오버헤드 보정이 적용될 경우 `measure_cbr_target.py`를 재실행하여 목표치를 미세 조정할 수 있습니다.
- 다음 단계(C-1, C-2)에서 평가 러너(`sensitivity_runner.py`)에 DRL 모델을 등록하고 가중치를 로드하는 작업이 이어져야 전체 평가 파이프라인에서 신규 보상으로 학습된 모델이 작동합니다.

## 4. Conclusion (최종 결론)
- C-3 작업 목표(보상 함수 4항 재설계, `prev_cbr`/`prev_t_gencam` 상태 관리, CBR_TARGET 자동 측정 스크립트 작성 및 실행, 마스터 작업 목록 초기화)가 100% 완료되었습니다.
- 독립 검증 스크립트(`code/test_c3_reward.py`)를 통해 모든 요구조건이 결함 없이 충족되었음을 입증하였습니다.

## 5. Verification Method (독립 검증 방법)
아래 명령어를 프로젝트 루트(`/home/imnyj/Workspace/paper4`)에서 실행하여 독립 검증을 재현할 수 있습니다:

```bash
# 1. C-3 독립 검증 단위테스트 실행 (7개 테스트 통과 및 Exit Code 0 확인)
python3 code/test_c3_reward.py

# 2. CBR 실측 스크립트 실행 및 결과 확인
python3 code/measure_cbr_target.py

# 3. 구버전 abs(cbr - 0.6) 보상 패턴 완전 제거 검증 (0건 출력 확인)
grep -rn "abs(cbr_smoothed - 0.6)" code/

# 4. 베이스라인 회귀 검증
python3 -c "from sim_engine import SimulationRunner; m = SimulationRunner('urban_grid', 20, 42, method='Fixed10Hz', duration_steps=100).run(); print('Simulation run OK, CBR:', m['CBR_mean'])"
```
