# Paper4 Workflow — AoI-aware V2I 업링크 갱신 스케줄링

> CLI(Antigravity)에서 작업을 이어가기 위한 진행 요약. **무슨 논문을·왜·어떻게** 하는지와 **어디까지 됐는지**를 정리한다. 전체 설계 명세는 같은 폴더의 `aoi_scheduling_design.md` 참조.

---

## 1. 한눈에

| 항목 | 내용 |
|---|---|
| **시나리오** | 단일 RSU 셀에서 차량들이 자기 상태를 업링크로 갱신. RSU가 각 차량에게 **다음 갱신시점·서브채널·전력(grant)** 을 스케줄 |
| **방안** | RL 스케줄러 (표준 Double-DQN부터 시작, REMO-DQN 채택은 미정) |
| **목적** | **유효 AoI**(추정 오차 기반 — 정지 차량은 갱신 불필요) + **망 혼잡**을 동시 최소화 |
| **채널** | Wi-Fi(802.11ac/ax) 기반 **확률적 SINR** 업링크 (경로손실+열잡음+Rayleigh 간섭) |
| **차별화** | ① 순수 AoI가 아닌 **유효 AoI/AoII**(동역학에 따른 갱신 가치) ② **신호 기반 동역학 예측**으로 "바뀌는 순간" 갱신 ③ 예측 없이 현재 관측만 쓰는 견고성 |
| **타깃 학술지** | IEEE TWC |
| **실행 환경** | 원격 워크스테이션(SUMO 필요). 프레임워크는 기존 SumoNetSim(headless NetSim + Wi-Fi Communications + SUMO 환경) 재사용 |

---

## 2. 왜 이 방향인가 (동기)

- 차량 상태정보는 가볍지만 다수·고빈도라, 모두가 자주 보내면 **채널 포화 → 충돌 → 정보가 늦게/못 도달**. 유한 자원 하에 "누구를 언제 갱신시킬지"가 문제이고 목적함수가 AoI. (콘텐츠 프리캐싱/CCN 방향은 폐기됨.)
- 순수 AoI(나이)는 낭비를 부른다. 정지·정체 차량은 RSU가 마지막 상태를 외삽해도 안 어긋나므로 **나이가 많아도 갱신 불필요**. 반대로 가·감속·회전 차량은 몇 초만 지나도 추정이 틀림. → **추정 오차(유효 AoI)** 를 최소화하는 게 순수 AoI 대비 이 논문의 delta.
- 여기에 **신호등 정보**(RSU가 아는 상태·잔여시간)로 곧 일어날 동역학 변화를 예측해, 바뀌는 순간을 놓치지 않고 갱신 → S2에서 발견한 "정지 차량이 낡은 이동속도로 날아가는 함정"을 정면 해결.

---

## 3. 시스템 설계 요약 (자세히는 aoi_scheduling_design.md)

- **환경**: 단일 RSU 셀(가장 붐비는 RSU 자동 선택), 가변 N대, C개 서브채널, SINR 확률 성공.
- **시점(event-driven)**: E1 진입(등록) → E2 예정 갱신(SINR 판정, 성공 시 `(x̂,τ)` 갱신 + 소급 오차 확정) → E3 이탈(종료). 폴링 없음.
- **추정 오차**: 등속 외삽 `x̂(t)=pos+vel·(t−τ)`, `e=‖실제−x̂‖`. 다음 갱신 시 소급 확정.
- **State**: 차량별 [나이·동역학·**신호맥락**·로컬혼잡·채널·전역 망상태] (RSU 관측치만; 실제 오차는 보상에만).
- **Action**: grant `(Δ, ch, p)` 이산 조합.
- **Reward**: `−∫e_i − λ1·CBR − λ2 − β(1−P_succ)` (t_now에 소급 확정).
- **신호 기반 동역학 예측 (A+B 확정)**: (A) 신호 상태·잔여시간·"곧 정지/출발" 예측을 **State 피처**로 제공해 RL이 학습, (B) 동일 예측으로 **신호-인지 휴리스틱 강제 갱신 트리거**를 만들어 **베이스라인**으로 사용.
- **운용**: actor(serving)/learner(training) 분리 + hot-swap + 자원 격리(서비스 무중단).

---

## 4. 로드맵과 진행 상태

| 단계 | 내용 | 상태 |
|---|---|---|
| **S1** | 환경 계층: E1/E2/E3 이벤트 + RSU `(x̂,τ)` 유지 + 등속 외삽 + 사후 소급 오차 | ✅ **완료·검증** |
| **S2** | 확률적 SINR 업링크: grant `(Δ,ch,p)` + 동일 서브채널 SINR 성공판정, 성공분만 갱신 | ✅ **완료·검증** |
| **S2.5** | 신호 기반 동역학 예측 (A: State 피처 계측 / B: 휴리스틱 트리거) | 🔄 **착수** — `getNextTLS`(상태 r/y/g/G + 정지선 거리 + 잔여시간) 동작 100% 확인. 피처·트리거 **미구현** |
| **S3** | 에이전트 인터페이스: State 벡터화·정규화, grant 디코딩, transition/reward 조립 | ⬜ 대기 |
| **S4** | 학습 루프 + 이중 모델(actor/learner) + hot-swap + 자원 격리 | ⬜ 대기 |
| **S5** | 평가 하네스: 제안 vs 베이스라인(순수 AoI / 고정주기 / **신호-인지 휴리스틱** / 랜덤) → 지표 CSV | ⬜ 대기 |

---

## 5. 지금까지 검증된 결과 (실제 SUMO 1.27.1)

**S1 — 유효 AoI 로직**
- 단위테스트: 정지/등속 = 오차 0, 등가속 = `0.5·a·t²`, 회전 = 성장.
- SUMO 런(단일 셀): 저속(<2m/s) 평균오차 **0.18** vs 고속 **0.75** → 정지 차량은 외삽이 잘 맞아 갱신 불필요(유효 AoI 전제 실측 확인).

**S2 — SINR 업링크 (메커니즘 반응성)**
- 단독 전송: 셀 전역 가능(100m 0.999 → 800m 0.865).
- 경합↑ → 성공↓ (동일 서브채널 1/2/4/6대 → 0.99/0.50/0.12/0.03).
- 밀도↑ → 성공↓ (15/30/50 → 0.066/0.036/0.022), 서브채널↑ → 성공↑ (2/4/8 → 0.012/0.039/0.10), Δ↑ → 성공↑ (1/3/6s → 0.065/0.325/0.459).
- `tx_attempts = tx_success + tx_fail` 정합. 성공분만 RSU 갱신.

**핵심 인사이트 (S3 보상 설계에 반영 필요)**
1. **AoI vs 혼잡 트레이드오프**가 실측으로 드러남 — 자주 갱신=신선하나 충돌 / 드물게=성공하나 낡음.
2. **"정지=갱신 불필요"의 함정** — 갱신이 희박하면 RSU가 정지를 *모른 채* 낡은 이동속도로 외삽 → 정지 차량이 오히려 큰 오차. 따라서 **동역학이 바뀌는 순간엔 반드시 한 번 갱신**하고 그 뒤 백오프해야 함 → S2.5(신호 예측)가 이를 해결하는 장치.

---

## 6. 파일 구성 (이 번들)

| 파일 | 위치(워크스테이션) | 설명 |
|---|---|---|
| `NetSim.py` | `code/src/NetSim.py` | headless SumoNetSim 코어 (GUI/영상 제거) |
| `Communications.py` | `code/src/Communications.py` | Wi-Fi rate 모델 + **SINR 업링크 모델**(S2) |
| `aoi_env.py` | `code/src/aoi_env.py` | **S1+S2 환경 계층** (이벤트·오차·SINR grant) |
| `aoi_scheduling_design.md` | (문서) | 전체 설계 명세 |
| `README_S1.md`, `README_S2.md` | (문서) | 각 단계 구현·검증 상세 |
| `workflow.md` | (문서) | 본 파일 |

**실행법 (요지)**: `code/`를 CWD로, `SUMO_HOME` 설정 후
```python
import random
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
ss.RSU_RANGE=800.0; ss.AV_SPEED=45.0; ss.DENSITY=25.0; ss.MAX_STEPS=160.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
random.seed(5); env.WARMUP_S=25.0; env.reset_env()
sim=net.SumoNetSim(VehicleClass=env.VehicleNode, RSUClass=env.RSUNode,
                   start_message_fn=env.start_message)
sim.run(); print(env.METRICS.summary())
```

**주의 (gotcha)**: `make_sumo_set.py`의 `step/GRID_SIZE/EDGE_LENGTH`는 import 시점에 기본값으로 한 번만 계산됨 → import 후 `ss.OUTAGE_ZONE` 등을 바꿔도 격자 geometry는 안 바뀜(간격 2400 고정). 타깃 셀은 중앙이 아니라 **웜업 트래픽 최다 RSU**로 자동 선택됨.

---

## 7. CLI에서 이어갈 다음 작업 (S2.5 → S3)

**S2.5 (지금 착수 지점)** — `aoi_env.py`에 신호 기반 동역학 예측 추가:
1. RSU가 각 추적 차량에 대해 `sumo.vehicle.getNextTLS(vid)`로 (신호상태 r/y/g/G, 정지선 거리, `getNextSwitch` 잔여시간)을 계측.
2. **(A)** 이를 State 재료로 저장: `tls_state`(cyclical), `tls_time_left`, `dist_to_stopline`, `predicted_dynamics_change`(접근+빨간불+곧 정지선 → 감속임박 / 정지+초록임박+큐순번 → 출발임박), `queue_pos`.
3. **(B)** 동일 예측으로 **신호-인지 휴리스틱 스케줄러**(강제 갱신 트리거)를 별도 정책으로 구현 → S5 베이스라인.
4. **검증**: "곧 정지/출발" 예측이 실제 외삽 오차 급증을 **선행**하는지(예측 유효성) 확인.

**S3** — `decide_grant`를 RL 에이전트 인터페이스로 교체: State 벡터화(S2.5 피처 포함)·정규화, grant 디코딩, transition/reward 조립. `pending_tx` 해소 지점에 각 전송의 `P_succ`·소급 오차가 이미 있으므로 보상 훅이 자연스럽게 붙음.
