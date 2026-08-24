# Milestone 2 적대적 스트레스 테스트 보고서 (Adversarial Challenge Report)

**작성자**: challenger_m2_1 (Milestone 2 Adversarial Validation Specialist)  
**일시**: 2026-08-24T11:47:35+09:00  
**대상 파일**: 
- `data/optuna_best_params.json`
- `data/optuna_sensitivity.csv`
- `data/optuna_sensitivity_table.csv`
- 14개 강화학습(RL) 모델 구현체 (`code/*_agent.py`) 및 DCC Hook 연동 계층 (`code/ai_dcc_hook.py`)

---

## 1. Challenge Summary

- **종합 위험 평가 (Overall Risk Assessment)**: **LOW** (안정성 및 정합성 검증 완료)
- **최종 판정**: **APPROVE** (모든 14개 RL 모델 하이퍼파라미터 정상, [0, 23] 액션 공간 완벽 준수, Hook 연동 및 학습 스텝 수치 안정성 확보)

---

## 2. Adversarial Challenges & Hypotheses

### [Low] Challenge 1: 하이퍼파라미터 수치 오염 및 비정상 경계값 존재 가능성
- **도전한 가정**: Optuna 최적화 과정에서 NaN, Inf, 음수 학습률, 1.0 초과 할인율($\gamma$), 비정상 버퍼 크기 등의 수치 오염이 발생했을 가능성.
- **공격 시나리오**: `data/optuna_best_params.json`의 14개 모델 전체 파라미터에 대한 전수 범위 스캔 실행 (NaN/Inf, $0 < \text{lr} < 1$, $0 < \gamma \le 1.0$, $0 < \tau < 1$, 양의 정수 버퍼/배치 등).
- **영향 범위(Blast Radius)**: 학습 발산, NaN loss 전파, 역전파 충돌.
- **검증 결과**: 14개 모델 전수 검증 통과 (0건의 결함). 모든 학습률($10^{-5} \sim 10^{-2}$), 감마($0.90 \sim 0.985$), 배치 크기($32, 64, 128$), 버퍼 크기($10,000 \sim 100,000$) 정상 범위 내 존재.

### [Low] Challenge 2: 입력 상태 섭동 및 극한값 입력 시 액션 인덱스 이탈 가능성
- **도전한 가정**: 영벡터(Zero), 상한 경계(1.0), Out-of-Distribution(OOD 극한값), 미세 노이즈, 음수 섭동 및 임의 50개 난수 상태 입력 시 액션 인덱스가 [0, 23] 범위를 벗어나거나 NaN/Float 타입을 반환할 가능성.
- **공격 시나리오**: 62개 극단적 상태(Nominal, Zero, Boundary, Extreme OOD, Small Epsilon, Negative Perturbation, 50 Uniform Randoms)를 주입하고, 결정론적(eval) 및 확률적(expl) 추론 수행.
- **영향 범위(Blast Radius)**: SUMO 통신 시뮬레이터에서 인덱스 에러(`IndexError`) 발생 및 시뮬레이션 중단.
- **검증 결과**: 14개 모델 전체 62개 상태(총 868회 추론)에 대해 100% 정수 액션 반환, 반환값 범위 `[0, 23]` 완벽 준수.

### [Low] Challenge 3: AIDCCHook과의 상호작용 및 물리 파라미터 매핑 불일치
- **도전한 가정**: 모델이 선택한 액션(0~23)이 `T_GRID_S`([0.1, 0.2, 0.5, 1.0]) 및 `PTX_GRID_DBM`([-5, 0, 5, 10, 15, 20])의 물리 값으로 디코딩되지 못하거나 Hook 라이프사이클(차량 진입-스텝-퇴장)에서 에러가 발생할 가능성.
- **공격 시나리오**: `get_hook(model_name)`으로 인스턴스화 후 `predict()` 및 `terminate_vehicle()` 2단계 호출을 통해 보상 계산, 메모리 저장, 종료 전이(`done=True`) 실행.
- **영향 범위(Blast Radius)**: 물리 계층 패킷 전송 주기 및 전력 매핑 실패, 메트릭 수집 누락.
- **검증 결과**: 14개 모델 모두 Hook 연동 완료, (T, Ptx) 유효 값 정상 반환 확인.

### [Low] Challenge 4: 1-스텝 학습 전이 및 손실 함수 수치 불안정성
- **도전한 가정**: 경험 재생 버퍼에 전이 데이터를 저장하고 `train_step()`을 호출했을 때 그래디언트 폭발/소실로 인해 Loss가 NaN 또는 Inf를 반환할 가능성.
- **공격 시나리오**: 가상 전이(State, Action, Reward, Next State, Done)를 배치 크기 이상 주입하고 `agent.train_step()` 직접 실행.
- **영향 범위(Blast Radius)**: Milestone 3 전체 재학습(Full Retraining) 시 훈련 중단 및 가중치 손상.
- **검증 결과**: 14개 모델 전체 손실 함수 유한 실수(Finite Float) 반환 확인, 수치 안정성 검증 완료.

---

## 3. Stress Test Results Summary

| 테스트 항목 | 테스트 시나리오 | 기대 결과 | 실제 측정 결과 | 판정 |
|---|---|---|---|---|
| **Test 1: Hyperparameter Sanity** | 14개 모델 전체 파라미터 전수 검사 | NaN/Inf 없음, $0<\text{lr}<1$, $0<\gamma\le1.0$ | 14개 모델 100% 정상 수치 범위 확인 | **PASS** |
| **Test 2: Instantiation & Inference** | 62개 극한/난수 상태 주입 | 14개 모델 모두 int 반환, $0 \le \text{action} \le 23$ | 868회 추론 100% 액션 범위 [0, 23] 준수 | **PASS** |
| **Test 3: Hook Integration** | AIDCCHook 연결 후 2스텝 추론 & 차량 종료 | 유효한 (T, Ptx) 매핑 및 터미널 전이 저장 | 14개 Hook 매핑 및 차량 종료 전이 정상 동작 | **PASS** |
| **Test 4: Single-Step Training** | 더미 배치 주입 후 `train_step()` 실행 | Loss 계산 완료, NaN/Inf 없음 | 14개 모델 전체 유한한 손실값 반환 | **PASS** |
| **Test 5: Sensitivity Consistency** | CSV와 JSON 간 17개 모델 명세 교차 검증 | 14개 RL + 3개 비RL 모델 수치 일치 | 17개 모델 행 및 파라미터 100% 정합 | **PASS** |

---

## 4. 모델별 세부 검증 결과 요약

| # | Model Name | Type | Tuned Params Summary | Tested States | Observed Action Range | Loss Sample | Hook (T, Ptx) Sample |
|---|---|---|---|---|---|---|---|
| 1 | **REMO-DQN** | Neural (Proposed) | num_exp=3, lr=0.002267, $\gamma$=0.9198, bs=64, buf=10k, upd=2 | 62 | [0, 23] | 0.0684 | 0.100s, +00dBm |
| 2 | **MoEDQN** | Neural | num_exp=2, lr=0.000929, $\gamma$=0.9576, bs=64, buf=100k, upd=1 | 62 | [0, 23] | 0.0570 | 0.200s, -05dBm |
| 3 | **DuelingDQN** | Neural | lr=0.000910, $\gamma$=0.9177, bs=64, buf=50k, upd=1 | 62 | [0, 23] | 0.0628 | 1.000s, +20dBm |
| 4 | **DoubleDQN** | Neural | lr=0.000226, $\gamma$=0.9238, bs=32, buf=100k, upd=2 | 62 | [0, 23] | 0.0704 | 1.000s, +15dBm |
| 5 | **VanillaDQN** | Neural | lr=0.005829, $\gamma$=0.9088, bs=128, buf=100k, upd=5 | 62 | [0, 23] | 0.2429 | 1.000s, +00dBm |
| 6 | **PPO** | Neural | lr=0.008153, $\gamma$=0.9006, eps_clip=0.2135, k_ep=8, bs=64, buf=100k | 62 | [0, 22] | (-0.0304, 0.0926) | 1.000s, +00dBm |
| 7 | **MAPPO** | Neural | lr=0.000665, $\gamma$=0.9169, eps_clip=0.1130, k_ep=10, bs=32, buf=50k | 62 | [0, 23] | (-0.0192, 0.0513) | 0.100s, +20dBm |
| 8 | **SAC** | Neural | lr=0.003986, $\gamma$=0.9451, $\tau$=0.009937, $\alpha$=0.2712, bs=64, buf=100k | 62 | [0, 23] | (-0.8425, 0.8748) | 0.100s, +20dBm |
| 9 | **DDPG** | Neural | lr_a=0.000665, lr_c=3.2e-5, $\gamma$=0.9064, $\tau$=0.00954, bs=32, buf=50k | 62 | [0, 23] | (-0.0582, 0.1013) | 1.000s, +10dBm |
| 10 | **TD3** | Neural | lr=2.2e-5, $\gamma$=0.9327, $\tau$=0.005474, p_del=1, t_noise=0.2004, bs=32 | 62 | [0, 23] | (0.2218, -0.0527) | 1.000s, +00dBm |
| 11 | **ActorCritic** | Neural | lr=0.001999, $\gamma$=0.9636, bs=64, buf=10k | 62 | [1, 22] | (-0.4328, 0.0632) | 0.500s, +10dBm |
| 12 | **DecisionTransformer** | Neural | lr=0.001568, $\gamma$=0.9298, bs=32, buf=100k | 62 | [0, 23] | 3.3240 | 0.500s, +10dBm |
| 13 | **QLearning** | Tabular | $\alpha$=0.01729, $\gamma$=0.9803, eps_decay=0.9472 | 62 | [0, 23] | 0.0 (Tabular TD) | 0.100s, +10dBm |
| 14 | **SARSA** | Tabular | $\alpha$=0.03846, $\gamma$=0.9858, eps_decay=0.9595 | 62 | [0, 23] | 0.0 (Tabular TD) | 1.000s, +05dBm |

---

## 5. Unchallenged Areas

- **장기 수렴 에피소드 스위프 (Multi-Episode Long-term Retraining & Density Sweep)**: Milestone 3 및 Milestone 4 범위로서, 본 적대적 테스트에서는 1스텝 전이 및 수치 안정성까지 검증하였으며 실제 100에피소드 훈련 및 대규모 평가 스위프는 차기 마일스톤 검증에서 전수 수행 예정.

---

## 6. 결론 (Conclusion)

Milestone 2의 산출물인 `data/optuna_best_params.json`, `data/optuna_sensitivity.csv`, `data/optuna_sensitivity_table.csv` 및 14개 RL 모델의 독립 적대적 검증이 모두 성공적으로 완료되었으며, 수치적 오염이나 인터페이스 결함 없이 Milestone 3(17개 모델 전체 재학습)로 안전하게 진입할 수 있음을 확인하여 **APPROVE** 판정을 내립니다.
