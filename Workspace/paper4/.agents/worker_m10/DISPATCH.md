## 2026-08-20T10:18:22Z
[수행할 단일 작업: M-10 학습 에피소드(500) 및 epsilon_decay(0.995) 스케줄 재설정]
순차 실행 원칙에 따라, M-9 완료에 이어 **M-10** 항목만 수정하고 독립 검증한 뒤 기록합니다.

1. **모든 학습 스크립트의 하이퍼파라미터 표준화 (`code/train_*.py`)**:
   - 기존의 `num_episodes=5` 극소 에피소드 및 비정상 감쇄 스케줄을 전면 정합합니다:
     * `train_resnet.py`, `train_dqn.py`, `train_ddqn.py`, `train_dueling_dqn.py`, `train_moe.py`, `train_qlearning.py`, `train_sarsa.py`, `train_actor_critic.py`, `train_other_models.py` 등 모든 활성 학습 스크립트 대상.
     * 기본 `num_episodes = 500` (CLI 인자 `--episodes` 지원하되 기본값 500 유지).
     * 기본 `epsilon_decay = 0.995` (500 에피소드 동안 $\epsilon=1.0 \to 0.082$로 서서히 수렴하여 충분한 탐험과 안정적 활용 보장).
     * `min_epsilon = 0.01` 또는 `0.05` 설정.
   - 각 스크립트가 에피소드별 보상, 손실, 입실론, 스텝 수를 CSV 로그(`*_train_log.csv`)에 정상 기록하도록 정합합니다.

2. **독립 검증 스크립트 작성 및 실행 (`code/test_m10_training_params.py`)**:
   - `code/test_m10_training_params.py`를 작성하여:
     * 모든 `train_*.py` 스크립트를 정적/동적 검사하여 default `num_episodes == 500` 및 `epsilon_decay == 0.995` 설정 일치 검증.
     * 입실론 감쇄 궤적의 수학적 정합성 검증 (Ep 0: 1.0 -> Ep 100: ~0.60 -> Ep 250: ~0.28 -> Ep 500: ~0.08).
     * CLI 인자 `--episodes`를 통한 스모크 테스트 구동 가능 여부 검증.
     * 2에피소드 스모크 학습 실행으로 에러 없이 가중치 저장 및 CSV 로그 생성 확인.
   - `python3 code/test_m10_training_params.py`를 실행하여 100% 통과(Exit Code 0)함을 입증합니다.

3. **마스터 작업 목록 갱신 (`idea/paper4_code_fix_tasklist.md`)**:
   - M-10 항목의 상태를 [x] 완료로 변경하고 수정 파일 목록, 스케줄 수식, 독립 검증 결과를 상세히 기록합니다.

4. **핸드오프 보고서 작성 및 완료 알림**:
   - `/home/imnyj/Workspace/paper4/.agents/worker_m10/handoff.md`에 결과를 기록하고 오케스트레이터에게 `send_message`로 완료를 보고하세요.
