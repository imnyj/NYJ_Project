# Paper4 (REMO-DQN) 코드 전수 검토 보고서

> **대상 에이전트**: Antigravity Coder Subagent
> **작업 범위 규칙**: `/code/` 내 파일만 수정. 수정 후 **반드시 독립 검증 스크립트**로 팩트 확인 후 `critic` 검토.
> **검토 범위**: `Workspace/paper4/code/*.py` (backup/`.bak` 제외), `idea/*.md`
> **핵심 결론**: 개별 함수 로직은 대체로 정상이나, **학습 → 평가 파이프라인의 "배선"이 끊겨 있어 현재 상태로는 REMO-DQN 결과가 산출되지 않는다.** 현재 모든 결과 수치는 `Proposed = TinyMLP` 경로에서 나온 것이며 REMO-DQN은 학습만 되고 평가되지 않는다.
> **제안 모델 확정**: REMO-DQN(`ResNetMoEDQN`). `idea/simulation_results_report.md`의 "Decision Tree Depth 5를 Proposed로 채택" 서사는 **폐기됨**.

---

## 우선순위 실행 순서 (권장)

1. **C-3** 보상 함수 & 목표 CBR 재설계 (가장 급함 — 안 고치면 학습 방향 자체가 틀림)
2. **C-1, C-2** 평가 러너에 DRL 메서드 등록 + 학습 가중치(.pth) 로드/`set_agent` 배선
3. **H-4** p_tx 액션 그리드 통일 (비교 공정성)
4. **H-5** Vanilla/Dueling 라벨 정리 및 Ablation 재구성
5. **H-6** tabular 상태 정규화 정합
6. **M-*** 방법론적 한계 보정

각 항목은 `수정 후 검증` 절의 스크립트를 반드시 실행하여 통과시킨 뒤 다음 항목으로 넘어갈 것.

---

## 🔴 CRITICAL — 결과 유효성 자체를 무너뜨리는 문제

### C-1. REMO-DQN이 평가 파이프라인에 등록되어 있지 않음

- **위치**: `code/sensitivity_runner.py` L80(`methods_sa1`), L103(SA2 `methods`)
- **현상**: 평가 대상이 `["ReactDCC","AdaptDCC","Heuristic","Fixed10Hz","DecTree","StdMLP","Proposed"]` 뿐이다. `DuelingDQN`, `MoEDQN`, `ResNetMoEDQN`이 목록에 없다. `"Proposed"`는 `ai_dcc_hook.py`에서 **TinyMLPHook**으로 매핑된다.
- **영향**: `train_resnet.py`로 REMO-DQN을 학습시켜도 러너가 실행하지 않으므로, 논문의 모든 그래프가 REMO-DQN이 아닌 TinyMLP/DT 결과다.
- **수정 지침**:
  - SA1/SA2 메서드 리스트에 `"ResNetMoEDQN"`(제안), 그리고 Ablation·비교용으로 `"MoEDQN"`, `"DuelingDQN"`(=Vanilla, H-5 참조)을 추가한다.
  - 논문 표기상 "제안 모델"의 라벨을 `Proposed(TinyMLP)`가 아니라 `ResNetMoEDQN`으로 못박는다. 결과 집계/플롯의 라벨 매핑도 함께 수정한다(`plot_*.py`, `aggregator.py`).

### C-2. 러너가 학습된 가중치(.pth)를 로드하지 않음 → 껍데기 평가

- **위치**: `code/sensitivity_runner.py` (전역: `.pth` 로드 / `set_agent` 호출 없음), `code/ai_dcc_hook.py` L138–141
- **현상**: DRL hook은 `self.agent`가 `None`이면 `action_idx = 0` **고정 폴백**으로 동작한다(L141). 러너는 agent를 만들지도 로드하지도 않는다.
- **영향**: 설령 C-1을 고쳐 `ResNetMoEDQN`을 목록에 넣어도, 학습된 정책이 아니라 "항상 action 0만 내는 껍데기"가 평가된다.
- **수정 지침**: 러너가 DRL 메서드를 실행하기 **전에** 에이전트를 생성·로드·주입하도록 배선한다. 예:

```python
# sensitivity_runner.py — 각 run 실행 직전(evaluate 경로)
from ai_dcc_hook import get_hook
from resnet_moe_agent import ResNetMoEAgent
from moe_agent import MoEAgent
from dqn_agent import DQNAgent

DRL_SETUP = {
    "ResNetMoEDQN": lambda: (ResNetMoEAgent(state_dim=5, action_dim=16, num_experts=3, hidden_dim=128), "resnet_moe_dqn.pth"),
    "MoEDQN":       lambda: (MoEAgent(state_dim=5, action_dim=16, num_experts=2), "moe_dqn.pth"),
    "DuelingDQN":   lambda: (DQNAgent(state_dim=5, action_dim=16), "vanilla_dqn.pth"),  # H-5 반영 후 라벨/파일명 정정
}

def setup_eval_hook(method):
    if method in DRL_SETUP:
        agent, ckpt = DRL_SETUP[method]()
        agent.load(os.path.join(os.path.dirname(__file__), ckpt))
        agent.epsilon = 0.0                 # 평가 시 탐험 off
        hook = get_hook(method)
        hook.set_agent(agent)
        hook.is_training = False            # 평가 중 transition 저장/보상 계산 금지
```

- **주의**: `get_hook`은 전역 싱글턴 캐시(`_hooks`)다. 학습 프로세스와 평가 프로세스가 같은 파이썬 세션이면 `is_training` 값이 오염될 수 있으니, **평가 러너는 별도 프로세스로 실행**하거나 매 실행 전 `is_training=False`를 명시적으로 세팅할 것.

### C-3. 보상 함수가 논문 목표(혼잡 억제·CBR 안정화)와 반대 방향

- **위치**: `code/ai_dcc_hook.py` L149(`DuelingDQNHook.predict`), L185(`SARSAHook.predict`); 채널 모델 `code/sim_engine.py` L47, L91–103
- **현상**:
  - 보상 = `-1.0 * abs(cbr_smoothed - 0.6) - 0.1 * dt_since_last_cam`
  - `compute_cbr`상 CAM 1건의 CBR 기여 = `TX_DURATION_S / step = (280*8/3e6)/0.1 ≈ 0.00747`.
  - 학습 밀도 50대 → 최대 CBR ≈ **0.37**, SA2 기본 30대 → ≈ **0.22**. 즉 **목표 0.6에 물리적으로 도달 불가**.
  - 따라서 `abs(cbr-0.6)`를 줄이려면 **더 많이 전송**해야 하고, `-0.1*dt` 항도 **자주 전송**을 보상한다. 두 항 모두 "10Hz로 최대한 쏴라"로 수렴 → 혼잡 제어라는 핵심 기여도와 정면 모순.
- **원인 두 가지 (둘 다 대응 필요)**:
  1. **보상 형태 결함**: `abs()`는 목표보다 낮을 때도 페널티를 주어 "채널을 채우라"는 신호가 된다.
  2. **채널 모델 CBR 과소추정**: 페이로드 airtime만 계산하고 PHY/MAC 오버헤드(프리앰블·헤더·SIFS)와 국소 측정을 반영하지 않아 CBR이 비현실적으로 낮다.
- **수정 지침**:
  - **(a) 보상 재설계** — 목표 초과분만 벌하고, 요동(oscillation)과 정보 노후화(staleness)를 함께 반영. hook에 `prev_cbr_smoothed[vid]`를 저장할 것.

    ```python
    CBR_TARGET = 0.6          # C-3(b)로 채널 모델을 고치면 유지, 아니면 밀도에 맞게 하향(예: 0.35)
    T_STALE    = 0.5          # 이 이상 지연되면 노후화 페널티(초)
    over  = max(0.0, cbr_smoothed - CBR_TARGET)                 # 혼잡(목표 초과)만 벌점
    osc   = abs(cbr_smoothed - self.prev_cbr.get(vid, cbr_smoothed))  # 요동 억제 → 안정성
    stale = max(0.0, dt_since_last_cam - T_STALE)              # 너무 뜸하면 벌점(AoI 보호)
    cost  = 0.1 / max(T_GenCam, 1e-3)                          # 전송 빈도 비용(에너지/채널)
    reward = -1.0*over - 0.5*osc - 0.3*stale - 0.05*cost
    self.prev_cbr[vid] = cbr_smoothed
    ```
    → 목표 이하에서는 혼잡 벌점이 0이라 "채우라" 신호가 사라지고, 빈도 비용 vs 노후화 벌점 사이에서 균형점을 학습한다. 가중치(1.0/0.5/0.3/0.05)는 튜닝 대상.
  - **(b) 채널 모델 보정(권장)** — `TX_DURATION_S`에 PHY/MAC 오버헤드를 포함(예: 프리앰블+헤더+SIFS 상수 가산)하거나, CBR을 "국소 이웃 기준 채널 점유 시간 비율"로 측정하도록 `compute_cbr`를 개선하여 ETSI 목표(0.6)가 실제 도달 가능하도록 만든다. **모델을 고치지 않을 경우 반드시 (a)의 `CBR_TARGET`을 테스트 밀도에서 실제 도달 가능한 값으로 하향**하고 그 근거를 논문에 명시한다.

---

## 🟠 HIGH — 비교 공정성·재현성을 훼손하는 문제

### H-4. p_tx 액션 그리드가 파일마다 제각각 + 제안 모델만 30 dBm 사용 가능

- **위치**: `ai_dcc_hook.py` L15–16(TinyMLP `[0.0,15.0,30.0]`), L67–68/L115–116(`[0.0,10.0,20.0,30.0]`); `etsi_cam_layer.py` L44(`PTX_GRID_DBM=[-10,0,10,20]`)
- **현상**: hook이 `vs.p_tx`를 직접 덮어쓴다. DRL 모델은 **30 dBm(1W)** 까지 송신 가능한데 모든 베이스라인은 고정 20 dBm. 수신확률이 SNR(전력)에 비례하므로(`sim_engine.reception_probability`) 제안 모델만 PDR에서 부당하게 유리하다.
- **수정 지침**: p_tx 그리드를 **단일 상수 모듈**로 통일하고(예: `etsi_cam_layer.PTX_GRID_DBM = [-10,0,10,20]` 하나만 참조), 모든 hook이 이 그리드를 import해서 쓰도록 리팩터. `action_dim`(=len(t_grid)*len(p_grid))도 이 상수에서 유도. 베이스라인 최대 전력(20 dBm)을 넘는 액션은 제거하거나 모든 기법에 동일 허용.

### H-5. "Vanilla DQN" vs "Dueling DQN" 라벨 혼선 → Ablation 오염

- **위치**: `train_dqn.py`(전체), `dqn_agent.py`(`VanillaDQN`, 단일 타깃), `moe_agent.py`/`resnet_moe_agent.py`(Double DQN + Dueling)
- **현상**:
  - `train_dqn.py`는 `DQNAgent`(=순수 MLP `VanillaDQN`, **dueling 아님**)를 만들어 hook `"DuelingDQN"`으로 쓰고 `dueling_dqn.pth`로 저장 → 파일명과 실제 구조 불일치.
  - `dqn_agent.py`는 **single-DQN 타깃**(`target.max`), `moe/resnet`은 **Double DQN 타깃 + Dueling**. 즉 Ablation `[Vanilla] vs [DQN+MoE] vs [ResNet+MoE+Dueling]`이 (타깃종류·dueling유무·MoE·ResNet)을 한꺼번에 바꾸는 **교란 비교**. 순수 dueling-only 베이스라인도 없음.
- **수정 지침**:
  - 파일명·라벨 정정: Vanilla는 `vanilla_dqn.pth`/`"VanillaDQN"`, Dueling-only는 별도 에이전트로 신설.
  - Ablation을 **한 번에 한 요소만** 바꾸도록 재구성: `Vanilla DQN` → `+Double` → `+Dueling` → `+MoE` → `+ResNet(=제안)`. 각 단계가 직전 단계에서 정확히 한 컴포넌트만 추가되도록 에이전트를 구성하고 동일 하이퍼파라미터로 학습.

### H-6. tabular 에이전트 상태 정규화 불일치

- **위치**: `etsi_cam_layer.py` L379(`n_neighbors = n_est/50.0`) vs `qlearning_agent.py`/`sarsa_agent.py`의 `state_bounds` 이웃 축 `(0.0, 200.0)`
- **현상**: hook에는 정규화된 `n_est/50`(≈0~2)이 들어오는데 tabular은 원시값(0~200)을 가정 → 이산화 시 항상 bin 0. **Q/SARSA가 이웃 밀도를 사실상 무시**.
- **부가**: 두 tabular 에이전트에는 `train_step()`이 없다(`store_transition` 내 온라인 갱신). 다른 train 스크립트 패턴으로 `train_step()`을 호출하면 `AttributeError`.
- **수정 지침**: 정규화 규약을 한쪽으로 통일(권장: 모든 에이전트가 정규화된 상태를 받도록 `state_bounds`를 `(0,1)`로 맞추고, `v_norm`/`n_neighbors` 정규화 상수를 명세). tabular 학습 스크립트가 `train_step()`을 호출하지 않는지 점검.

---

## 🟡 MEDIUM — 방법론적 한계 (리뷰어 지적 예상 지점)

- **M-7. `n_est`가 국소 이웃이 아니라 맵 전체 차량 수** — `sim_engine.py` L397 `"n_est": len(vehicle_ids) - 1`. 모든 차량이 동일 값을 봐 "국소 밀도" 피처 의미 상실. 통신 반경(`COMM_RANGE_M`) 내 이웃 수로 계산하도록 수정.
- **M-8. CBR이 전역 스칼라 1개** — `compute_cbr`가 맵 전체 1값. 3×3 그리드(≈750m) 전체가 하나의 CBR 공유 → 공간 재사용(spatial reuse) 무시, 혼잡 결합 과대평가. 수신자 이웃 기준 국소 CBR로 개선 권장(C-3(b)와 연계).
- **M-9. 하드코딩 절대경로** — `train_final.py`의 `/home/imnyj/papers/paper4/paper/data/oracle_dataset.csv`, `sim_engine.py` L159/L172의 `/home/imnyj/venv/bin/netgenerate`. 상대경로/환경변수/설정파일로 이전(재현성).
- **M-10. 학습량 부족** — `train_resnet.py` `num_episodes=5`, `epsilon_decay=0.995`(5에피소드면 ε≈0.975, 거의 랜덤). reward convergence 곡선을 5점으로 그리는 것은 근거 부족. 에피소드 수 대폭 상향(수백~수천) + ε 스케줄 재설정.
- **M-11. `train_7_models.py`가 완전 난수 데이터** — `np.random.rand`, `randint(0,25)`로 학습 + `"TinyMLP (Proposed)"` 라벨 + 25클래스(액션공간 16과 불일치). 복잡도(latency/params) 측정 용도면 데이터는 무방하나, 라벨을 REMO-DQN 기준으로 정정하고 클래스 수를 실제 액션 수에 맞출 것.
- **M-12. `done` 플래그가 항상 False** — hook이 transition을 `done=False`로만 저장(차량 이탈 시 terminal 미처리). 에피소드/차량 종료 시 terminal 전이를 저장하도록 보완(부트스트랩 편향 완화).

---

## 작업 체크리스트 (task.md 포맷)

```
- [ ] C-3  보상 함수 재설계 (over-target only + osc + stale + cost) & CBR_TARGET/채널모델 정합
      - [ ] hook에 prev_cbr[vid] 저장 로직 추가
      - [ ] (권장) compute_cbr에 PHY/MAC 오버헤드 반영 또는 국소 CBR
      - [ ] 검증: reward가 저밀도에서 '전송 최대화'로 수렴하지 않음을 단위테스트로 확인
- [ ] C-1  sensitivity_runner에 ResNetMoEDQN/MoEDQN/DuelingDQN 등록 + 라벨 매핑 수정
- [ ] C-2  러너에 agent 생성·.pth 로드·set_agent·is_training=False·epsilon=0 배선
      - [ ] 검증: DRL 메서드가 action 0 고정이 아닌 다양한 액션을 내는지 로그로 확인
- [ ] H-4  p_tx 액션 그리드 단일 상수로 통일 (베이스라인 최대전력 초과 액션 정리)
- [ ] H-5  Vanilla/Dueling 라벨·파일명 정정 + Ablation 단계별 1요소 변경 재구성
- [ ] H-6  tabular 상태 정규화 정합 ((0,1)로 통일) + train_step 부재 점검
- [ ] M-7  n_est를 통신반경 내 국소 이웃 수로 계산
- [ ] M-8  국소 CBR 도입
- [ ] M-9  하드코딩 절대경로 제거
- [ ] M-10 학습 에피소드/ε 스케줄 재설정
- [ ] M-11 train_7_models 라벨/클래스 수 정정
- [ ] M-12 terminal(done=True) 전이 저장
- [ ] 전 항목 완료 후 critic 검토 요청
```

---

## 수정 후 검증 (coder 규칙 준수 — 반드시 실행)

각 항목 수정 후, 임의 판단 금지·독립 검증 원칙에 따라 아래 최소 검증을 통과시킬 것.

1. **C-2 배선 검증**: `ResNetMoEDQN`을 짧은 duration(예: `duration_steps=300`)으로 1회 평가 실행하여, hook이 내는 `action_idx` 분포가 **단일값(0)이 아님**을 로그로 확인.
2. **C-3 보상 방향 검증**: 저밀도(예: 10~30대) 합성 상태 시퀀스에 대해 재설계된 보상을 계산했을 때, "T_GenCam=0.1(최대 전송)"이 유일 최적이 **아님**을 단위테스트로 확인(전송 비용·노후화 트레이드오프 존재).
3. **H-4 그리드 검증**: 모든 hook의 p_tx 그리드가 동일 상수를 참조하고, 최대 p_tx가 베이스라인(20 dBm)을 넘지 않음을 assert.
4. **회귀 검증**: 베이스라인(Fixed10Hz/ReactDCC/AdaptDCC) 결과가 수정 전후로 재현되는지(시드 고정) 대조하여, 리팩터가 베이스라인을 오염시키지 않았는지 확인.
5. 결과·로그는 규칙대로 파일(csv/md/npz)로 남기고 최신 버전만 유지, 이전 버전 수정 시 백업 프로토콜 준수.
