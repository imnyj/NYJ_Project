# Handoff Report — M-10: 학습 에피소드(500) 및 epsilon_decay(0.995) 스케줄 재설정 및 CSV 로깅 표준화

**에이전트**: worker_m10 (Coder Worker)  
**작업 일시**: 2026-08-20T19:27:30+09:00  
**상태**: 완료 (Hard Handoff)  
**프로젝트 루트**: `/home/imnyj/Workspace/paper4`  

---

## 1. Observation (관측 사실)

1. **기존 학습 스크립트의 하이퍼파라미터 결함**:
   - `code/train_resnet.py`, `code/train_dqn.py`, `code/train_ddqn.py`, `code/train_dueling_dqn.py`, `code/train_moe.py` 등에서 `num_episodes = 5`로 극소 설정되어 있었음.
   - DRL 학습 루프 내부의 `for _ in range(num_updates):` 블록 안에서 `agent.update_epsilon()`이 에피소드당 수십 번씩 중복 호출되어, $0.995^{46} \approx 0.793$ 등 불과 몇 에피소드 만에 최저 탐험률로 급격히 축퇴되는 결함이 존재했음.
   - `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`는 기본 실행 시 Optuna 탐색 루틴에 결합되어 있거나 `num_episodes=5`로 제한되어 있었음.
   - CLI 인자(`--episodes`) 지원이 부재하여 배치/스모크 테스트 시 코드 직접 수정이 요구되었음.

2. **수정 및 표준화 적용 파일**:
   - `code/train_resnet.py`: ResNetMoEDQN (제안 모델 REMO-DQN) 학습 스크립트 표준화
   - `code/train_dqn.py`: VanillaDQN 학습 스크립트 표준화
   - `code/train_ddqn.py`: DoubleDQN 학습 스크립트 표준화
   - `code/train_dueling_dqn.py`: DuelingDQN 학습 스크립트 표준화
   - `code/train_moe.py`: MoEDQN 학습 스크립트 표준화
   - `code/train_qlearning.py`: Q-Learning 학습 스크립트 표준화 (`--optuna` 플래그 분리)
   - `code/train_sarsa.py`: SARSA 학습 스크립트 표준화 (`--optuna` 플래그 분리)
   - `code/train_actor_critic.py`: ActorCritic 학습 스크립트 표준화 (`action_dim=ACTION_DIM` (24), `--optuna` 플래그 분리)
   - `code/train_other_models.py`: 지도학습 모델(StdMLP, DecTree) 데이터셋 동적 탐색 및 CLI 지원
   - `code/actor_critic_agent.py`: 기본 `action_dim=ACTION_DIM` (24) 및 `select_action` 별칭 추가
   - `code/test_m10_training_params.py`: M-10 독립 검증 테스트 스위트 (7개 테스트) 신규 작성

3. **독립 검증 및 회귀 테스트 실행 결과**:
   - `python3 code/test_m10_training_params.py`:
     `Ran 7 tests in 5.860s, OK (Exit Code 0)`
   - 전체 누적 9개 테스트 스위트 (총 59개 단위/통합 테스트) 연계 회귀 검증:
     ```bash
     python3 code/test_c3_reward.py && python3 code/test_c1_c2_wiring.py && python3 code/test_h4_grid.py && python3 code/test_h5_ablation.py && python3 code/test_h6_tabular.py && python3 code/test_m7_nest.py && python3 code/test_m8_local_cbr.py && python3 code/test_m9_paths.py && python3 code/test_m10_training_params.py
     ```
     결과: **59개 테스트 100% 통과 (Exit Code 0)**.

---

## 2. Logic Chain (논리적 추론 체계)

1. **에피소드 및 감쇄 스케줄의 수학적 설계**:
   - 강화학습에서 초기 $\epsilon=1.0$ (전면 무작위 탐험)에서 출발하여 학습이 진행됨에 따라 정책 활용(Exploitation) 비율을 점진적으로 높여야 함.
   - 500 에피소드 기준 $\epsilon(t) = \max(0.01, 1.0 \times 0.995^t)$ 적용 시:
     * $t = 0$: $\epsilon = 1.000$ (100% 탐험)
     * $t = 100$: $\epsilon = 1.0 \times 0.995^{100} = 0.60577 \approx 0.606$ (탐험 60.6%, 정책 39.4%)
     * $t = 250$: $\epsilon = 1.0 \times 0.995^{250} = 0.28561 \approx 0.286$ (탐험 28.6%, 정책 71.4%)
     * $t = 500$: $\epsilon = 1.0 \times 0.995^{500} = 0.08157 \approx 0.082$ (탐험 8.2%, 정책 91.8%)
     * $t \ge 918$: $\epsilon = 0.010$ (안정적 하한 유지)
   - 따라서 `update_epsilon()`을 에피소드 루프 끝에서 **에피소드당 1회** 호출하도록 정합하여 500 에피소드 동안 최적의 탐험-활용 균형이 유지됨.

2. **CLI 인터페이스 및 CSV 로깅 표준화**:
   - 모든 학습 스크립트에 `argparse` 파서를 구성하여 기본값 500 에피소드로 동작하면서도 `--episodes 2` 등으로 빠른 스모크 테스트가 가능하도록 구현.
   - 각 에피소드 완료 시 `['Episode', 'Reward', 'Loss', 'Epsilon', 'Steps', 'AoI_mean', 'CBR_mean', 'PDR_mean']` 표준 CSV 포맷으로 로그가 자동 누적되어 학습 수렴 추이 시각화 및 분석이 가능함.

---

## 3. Caveats (제약 및 주의사항)

- **No caveats.**
- 본 작업은 M-10 단일 항목(학습 에피소드 및 감쇄 스케줄, CSV 로깅 표준화)에 한정되었으며, 기존의 액션 그리드(H-4), Ablation(H-5), Tabular bounds(H-6), 국소 n_est/CBR(M-7/M-8), 경로 전환(M-9)과 100% 상호 호환성을 유지함.
- M-11(7개 모델 벤치마크 및 REMO-DQN 라벨 정합), M-12(ai_dcc_hook vehicle termination transition)는 다음 순차 작업에서 진행 예정.

---

## 4. Conclusion (최종 결론)

- Paper4 내 모든 활성 학습 스크립트(`code/train_*.py`)의 기본 `num_episodes = 500`, `epsilon_decay = 0.995`, `min_epsilon = 0.01`, `--episodes` CLI 인자 및 CSV 로깅이 완벽하게 표준화되었습니다.
- `code/test_m10_training_params.py` 및 전체 9개 회귀 테스트 스위트(59개 테스트)가 100% 통과하여 M-10 작업이 성공적으로 완료되었습니다.

---

## 5. Verification Method (독립 검증 절차)

다음 명령어로 직접 검증할 수 있습니다:

```bash
# 1. M-10 전용 독립 검증 스위트 실행
python3 code/test_m10_training_params.py

# 2. 개별 학습 스크립트 CLI 스모크 테스트 (2 에피소드 빠른 실행)
python3 code/train_resnet.py --episodes 2 --duration_steps 50 --output_model /tmp/test_resnet.pth --output_log /tmp/test_resnet.csv

# 3. 전체 9개 테스트 스위트 연계 회귀 검증
python3 code/test_c3_reward.py && \
python3 code/test_c1_c2_wiring.py && \
python3 code/test_h4_grid.py && \
python3 code/test_h5_ablation.py && \
python3 code/test_h6_tabular.py && \
python3 code/test_m7_nest.py && \
python3 code/test_m8_local_cbr.py && \
python3 code/test_m9_paths.py && \
python3 code/test_m10_training_params.py
```
