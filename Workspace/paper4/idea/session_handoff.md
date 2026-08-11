# Antigravity Multi-Agent Session Handoff State

## 1. 현재 진행 상황 (Current Progress)
- **과제**: `prompt.md`의 비교 방안 및 제안 방안(REMO-DQN) 논문 데이터 수집 시작 (6번, 7번 항목 진행 중)
- **완료된 선행 작업**:
  - `sim_engine.py`, `etsi_cam_layer.py`, `aoi_tracker.py` 4대 치명적 버그 수정 및 통신 모듈 100% 무결성 검증 (5연속 실증 테스트 완료).
  - 전체 14개 모델에 대한 Optuna 하이퍼파라미터 최적화 완료 및 `/data/optuna/`에 CSV 저장 완료.
  - 13종 비교 방안의 State/Action 텐서 및 코드 구현체 무결성 검증 완료.
- **현재 가동 중인 작업**:
  - `run_parallel_evaluation.py`를 통해 4개의 GPU 자원을 모두 사용하는 멀티프로세싱 대규모 데이터 수집 파이프라인이 구동 중이었습니다.
  - 1차 모델 그룹(`QLearning`, `SARSA`, `ActorCritic`, `VanillaDQN`)의 20만 스텝(100 에피소드) 수렴 훈련이 **약 52 에피소드**까지 진행된 상태였습니다.

## 2. 세션 종료 시 주의사항 (Critical Warning)
> **[WARNING]** 
> 에이전트 세션이 완전히 종료되면, 백그라운드에서 돌고 있던 `run_parallel_evaluation.py` 프로세스도 함께 강제 종료(Kill)됩니다. 
> 스크립트 특성상 재시작 시 기존 모델 수렴을 처음부터(Episode 0) 다시 시작하게 되므로, 새 세션에서는 스크립트를 수정(이어서 학습 기능 추가)하거나 터미널을 통해 `nohup`으로 띄우는 것이 안전합니다.

## 3. 남은 목표 (Next Steps for New Session)
1. 중단된 `run_parallel_evaluation.py`를 이어받아 14개 모델 전체의 훈련(Reward Convergence) 완료.
2. 훈련된 모델들의 `.pth`, `.pkl` 가중치를 바탕으로 차량 밀도(Density) 및 속도(Speed) 변화에 따른 성능(PDR, CBR, AoI, Energy 등) 평가 수행 (`eval_density_results.csv`, `eval_speed_results.csv` 추출).
3. `prompt.md`의 데이터 수집이 끝나면 `visualizer` 에이전트를 소환해 IEEE 스타일의 논문용 그래프 생성 진행.
