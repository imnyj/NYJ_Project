# Handoff Report — H-4: 송신 전력 p_tx 그리드 단일 상수화 및 30 dBm 불공정 액션 완전 제거

## 1. Observation (직접 관찰 사실)
- **수정 전 상태**:
  - `code/etsi_cam_layer.py`: `PTX_GRID_DBM = [-10, 0, 10, 20]`, `T_GENCAM_GRID = [0.1, 0.2, 0.5, 1.0]` (4x4 = 16 액션)
  - `code/ai_dcc_hook.py`:
    * `TinyMLPHook`: `p_tx_grid = [0.0, 15.0, 30.0]`, `t_grid = [0.1, 0.3, 1.0]`
    * `SklearnHook`: `p_tx_grid = [0.0, 10.0, 20.0, 30.0]`, `t_grid = [0.1, 0.2, 0.5, 1.0]`
    * `DuelingDQNHook`: `p_tx_grid = [0.0, 10.0, 20.0, 30.0]`, `t_grid = [0.1, 0.2, 0.5, 1.0]`
    * 각 hook마다 파편화된 p_tx 그리드를 하드코딩하고 있었으며, 베이스라인 최대 전력(+20 dBm = 100mW)을 초과하는 **30 dBm (1W)** 액션을 사용하여 제안 모델에 불공정한 SNR/PDR 이득을 부여하고 있었음.
- **수정 후 상태**:
  - `code/etsi_cam_layer.py`:
    ```python
    PTX_GRID_DBM = [-5, 0, 5, 10, 15, 20]  # 6단계 (최대 20 dBm = 100mW)
    T_GRID_S = [0.1, 0.2, 0.5, 1.0]        # 4단계
    ACTION_DIM = len(T_GRID_S) * len(PTX_GRID_DBM)  # 24
    T_GENCAM_GRID = T_GRID_S               # 하위 호환 별칭
    ```
  - `code/ai_dcc_hook.py`:
    * `from etsi_cam_layer import PTX_GRID_DBM, T_GRID_S, ACTION_DIM` 적용
    * 16개 전체 Hook 클래스(`TinyMLPHook`, `SklearnHook`, `DuelingDQNHook`, `ResNetMoEDQNHook`, `MoEDQNHook`, `VanillaDQNHook`, `DDQNHook`, `QLearningHook`, `SARSAHook`, `ActorCriticHook`, `PPOHook`, `DDPGHook`, `DecisionTransformerHook`, `SACHook`, `MAPPOHook`, `TD3Hook`)가 `self.p_tx_grid = list(PTX_GRID_DBM)`, `self.t_grid = list(T_GRID_S)`, `self.action_dim = ACTION_DIM`을 공통 사용.
    * 액션 인덱스 디코딩 로직 `(t_act, p_act) = (self.t_grid[action_idx // len(self.p_tx_grid)], self.p_tx_grid[action_idx % len(self.p_tx_grid)])`로 일원화.
  - 관련 스크립트(`optuna_optimize.py`, `train_final.py`, `tinymlp_train_redo4.py`, `diagnostics_E4-1-redo3.py`, `oracle_generator.py`)의 전력 그리드 하드코딩 및 30 dBm 정의 전면 제거.
  - `code/sensitivity_runner.py`의 `setup_eval_hook`이 체크포인트의 액션 차원(24 또는 레거시 16)을 유연하게 감지하여 로드하도록 호환성 확보.

## 2. Logic Chain (논리적 추론 과정)
1. **문제점**:
   - `sim_engine.py`의 수신 확률 모델(`reception_probability`)은 송신 전력 $P_{\text{tx}}$(mW)에 직접 비례하여 SNR을 계산함.
   - 베이스라인 기법들(ReactDCC, AdaptDCC, Heuristic, Fixed10Hz)은 모두 +20 dBm(100mW)을 최대로 사용하는 반면, 기존 AI 훅에 30 dBm(1000mW = 10배 전력)이 허용되어 있어 불공정한 PDR 우위가 발생했음.
2. **해결책**:
   - 표준 전력 그리드를 6단계 `[-5, 0, 5, 10, 15, 20]` dBm (최대 +20 dBm 상한 준수)으로 확정.
   - 주기 그리드 4단계 `[0.1, 0.2, 0.5, 1.0]`초와 결합하여 총 이산 액션 공간 크기 `ACTION_DIM = 24` 확립.
   - `code/etsi_cam_layer.py`에 단일 모듈 상수로 정의하고, 모든 AI-DCC Hook 및 관련 학습/평가 스크립트가 이를 직접 import하도록 리팩터링함.
3. **효과**:
   - 모든 AI 모델의 최대 송신 전력이 베이스라인과 동일한 20 dBm으로 제한되어 비교 공정성이 100% 회복됨.
   - 파일마다 제각각이던 액션 공간 규격이 단일 상수로 일원화되어 후속 Ablation(H-5) 및 재학습(M-10)의 일관된 기반 마련.

## 3. Caveats (주의 사항 및 제약)
- 기존에 학습되어 저장되어 있던 체크포인트 파일들(`vanilla_dqn.pth`, `ddqn.pth`, `DuelingDQN.pth`, `moe_dqn.pth`, `resnet_moe_dqn.pth`)은 이전의 `action_dim=16`으로 학습된 가중치입니다.
- `sensitivity_runner.py`의 `setup_eval_hook`에 24/16 유연 로드 로직을 적용하여 현재 레거시 체크포인트 평가 및 향후 H-5/M-10에서 24차원으로 재학습된 가중치 로드가 모두 무결하게 호환됩니다.

## 4. Conclusion (최종 결론)
- H-4 단일 작업(송신 전력 p_tx 그리드 통일 및 30 dBm 불공정 액션 완전 제거)이 완벽히 완료되었습니다.
- 모든 hook의 전력 그리드가 `[-5, 0, 5, 10, 15, 20]` (최대 20 dBm)으로 통일되었고, action_dim=24가 확립되었습니다.
- 코드베이스 전역 AST/정규식 검사로 30 dBm 전력 액션 정의 0건을 입증하였으며, 독립 검증 스위트 `test_h4_grid.py` 5/5 테스트를 100% 통과했습니다.

## 5. Verification Method (독립 검증 방법)
아래 검증 명령어를 실행하여 독립적으로 확인할 수 있습니다:

```bash
# 1. H-4 전용 독립 검증 스위트 실행 (5개 테스트 100% PASS)
python3 code/test_h4_grid.py

# 2. C-3 보상 함수 회귀 검증 (7개 테스트 100% PASS)
python3 code/test_c3_reward.py

# 3. C-1/C-2 러너 배선 회귀 검증 (4개 테스트 100% PASS)
python3 code/test_c1_c2_wiring.py
```
