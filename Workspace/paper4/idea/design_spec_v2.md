# 설계 명세 v2 — AoI 인지 V2I 업링크 스케줄링 (2026-08-28)

이 문서는 `idea/scenario.md`(사용자 원안)와 `Conversation.md`(승인된 확정 사항)를 기준으로
State / Action / Reward / 전이(transition)를 **코드와 1:1로 대응 가능한 수준까지** 명세한다.
`review/claude_audit_20260828.md`가 밝힌 결함 6건이 전부 "설계가 코드에 절반만 도달했다"는
같은 뿌리에서 나왔으므로, 구현 착수 전에 명세를 확정한다.

**이 문서는 아직 확정본이 아니다.** 8절의 미확정 항목에 사용자 결정이 필요하다.

---

## 0. 설계 원칙 (이번 재설계에서 새로 세우는 것)

**P1. 단일 정본(single source of truth).** 상태 벡터와 보상은 **한 곳에서만** 생성된다.
현재는 환경과 스케줄러가 각자 만들어 두 세계가 갈라졌고, 학습에 쓰인 쪽이 빈약한 쪽이었다.
어느 쪽을 정본으로 삼을지는 8절 D1.

**P2. 논문 수식 ↔ 코드 함수 1:1.** 논문에 쓰는 수식마다 대응하는 함수가 정확히 하나 있어야 한다.
"로그용 보상"과 "학습용 보상"이 따로 존재하는 상태는 허용하지 않는다.

**P3. 검증은 모델이 실제로 받는 입력에서 한다.** 관측 liveness 검사는 환경 반환값이 아니라
**모델 추론 함수의 인자**에서 측정한다. 이 원칙이 없어 15/18 상수를 놓쳤다.

**P4. 죽은 항은 설계에서 뺀다.** 보상 기여가 1% 미만이거나 상수인 항은
"있는데 안 쓰는" 상태로 두지 않고, 살리거나 명시적으로 제거한다.

---

## 1. 문제 정의 (SMDP)

RSU 한 대가 통신 범위 내 차량 각각에 대해 **다음 갱신 시점·서브채널·전송전력**을 결정한다.
결정은 균일 시간 간격이 아니라 차량마다 다른 간격 Δ로 발생하므로 MDP가 아니라 **SMDP**다.

- **에이전트**: RSU (중앙 집중). 차량은 지시를 따를 뿐 정책을 갖지 않는다.
- **결정 시점** $t_k^{(i)}$: 차량 $i$의 $k$번째 갱신이 처리된 순간. 이때 다음 액션을 정한다.
- **결정 간격** $\Delta_k^{(i)}$: 액션이 직접 정하는 값. 다음 결정까지의 시간.
- **에피소드 종료**: 차량이 RSU 통신 범위를 이탈할 때(차량 단위), 또는 에피소드 스텝 소진.
- **할인**: $\gamma^{\Delta}$ 가변 할인. `RetrospectiveReplayBuffer`에 이미 구현되어 있다
  (`rl_interface.py:566-567`). 현재는 Δ가 상수 0.1이라 무의미하지만, Δ가 살아나면 동작한다.

시뮬레이션 시간 해상도는 SUMO `step-length = 0.1 s`이므로 Δ는 0.1 s 격자에 스냅된다.

---

## 2. State

`scenario.md`의 선정 기준: **(a) 의미 있는 데이터인가, (b) 그 값을 얻는 cost(delay·power)가
얻는 이득보다 크지 않은가.** 아래는 그 기준으로 18차원을 재검토한 결과다.
"수집처" 열이 중요하다 — RSU가 **추가 통신 없이** 얻을 수 있어야 (b)를 만족한다.

| # | 피처 | 정규화 | 수집처 | (b) 통신비용 | 존치 판단 |
|---|---|---|---|---|---|
| 0 | age (마지막 갱신 후 경과) | /10 s, clip[0,1] | RSU 자체 장부 | 없음 | **필수.** AoI 그 자체 |
| 1,2 | 속도 X, Y | /v_max | 마지막 갱신 페이로드 | 없음(이미 받은 값) | 존치. dead reckoning 입력 |
| 3 | speed | /v_max | 동상 | 없음 | 존치 |
| 4 | accel | /a_max | 동상 | 없음 | 존치. 출발 시점 추론 |
| 5,6 | RSU 기준 상대좌표 dx, dy | /RSU_range | 마지막 갱신 + 외삽 | 없음 | 존치 |
| 7 | dist_to_rsu | /RSU_range | 동상 | 없음 | **필수.** 전력 결정의 유일한 물리 근거 |
| 8,9,10 | 신호등 R / Y / G | one-hot | RSU 인프라 직결 | 없음 | **필수.** 정지 추론의 1차 근거 |
| 11 | 신호 전환까지 잔여시간 | /60 s | 동상 | 없음 | **필수.** 출발 시점 추론 |
| 12 | 정지선까지 거리 | /RSU_range | 위치+맵 | 없음 | 존치 |
| 13 | n_active (범위 내 차량 수) | /100 | RSU 장부 | 없음 | 존치. 혼잡 예측 |
| 14 | CBR (채널 점유율) | 이미 [0,1] | RSU 자체 측정 | 없음 | 존치. 혼잡 실측 |
| 15 | stop/start imminent | [0,1] | 11·12에서 파생 | 없음 | **8절 D4** 중복 소지 |
| 16 | n_queue (앞 대기 차량 수) | /queue_max | **RSU 장부 추론** | 없음 | **8절 D3** 현재 상수 0 |
| 17 | heading (접근 +/이탈 −) | [-1,1] | 속도·상대좌표 파생 | 없음 | 존치 |

전부 (b)를 만족한다 — 어느 것도 차량에 추가 질의를 요구하지 않는다.
0·13·14는 RSU가 자기 장부/측정에서 얻고, 1~7·12·16·17은 **이미 받은 마지막 페이로드**에서
파생되며, 8~11은 RSU가 신호기와 유선 연결된 노변 장비라는 전제에서 공짜다.

`scenario.md`의 `info_others`(주변 차량 맥락 재활용)는 13·16이 그 축약형이다. 8절 D3 참조.

### 정지 추론의 논리 사슬 (논문이 주장할 인과)

`신호등 R(8) + 잔여시간(11) + 정지선거리(12) + 앞 차량 수(16) + 현재 속도(3)·가속도(4)`
→ 이 차량은 앞으로 몇 초간 물리적으로 정지해 있을 것이다
→ 그 구간의 이동성 정보는 갱신해도 값이 변하지 않는다
→ **Δ를 그 시간만큼 길게 준다**
→ 전력·혼잡을 아끼면서 AoI 손실은 0.

이 사슬의 어느 한 고리라도 모델 입력에서 빠지면 논문의 핵심 주장이 학습될 수 없다.
현재 구현은 8·11·12·16·4가 **전부 상수**여서 사슬이 끊겨 있다.

---

## 3. Action (승인 완료, 변경 없음)

`Conversation.md` 2절에서 확정. `rl_interface.py::ActionDecoder`가 정본이며 리터럴 중복 금지.

| 성분 | 범위 | 매핑 | 근거 |
|---|---|---|---|
| Δ 갱신 간격 | [0.1, 45.0] s | **기하** $\Delta = 0.1\cdot(450)^{u},\ u=\sigma(\text{logit})$ | 하한 ETSI EN 302 637-2 T_GenCamMin / 상한 실제 net.xml 적색 45 s |
| ch 서브채널 | {0,1,2,3} | Categorical | 802.11p 10 MHz × 4 = 40 MHz |
| p 전송전력 | [10, 23] dBm | 선형 (dBm이 이미 로그) | 상한 3GPP power-class-3 UE 최대 |

Δ 상한 45 s는 임의값이 아니라 **정지 차량이 물리적으로 멈춰 있을 수 있는 최대 시간**이며,
논문의 핵심 주장과 직접 대응한다는 점이 이 설계의 강점이다. 유지한다.

---

## 4. Reward

`Conversation.md` 3절 승인본:

$$R = -\big(w_1 \mathrm{Norm}(e^2) + w_2 \mathrm{Norm}(P_{tx}) + w_3 \mathrm{Norm}(C_{freq}) + w_4 \mathbb{I}_{redundant}\big)$$

$w_1{\sim}w_4$는 고정하지 않고 **Optuna 탐색 공간**에 넣는다(`hpo.py:109-115`에 구현되어 있음).

SMDP로 가면 각 항의 **시간 집계 방식**을 새로 정해야 한다. 이것이 이번 재설계의 핵심이며
8절 D2에서 결정한다. 항별 성격은 다음과 같다.

| 항 | 성격 | 구간 $[t_k, t_{k+1})$ 에서 |
|---|---|---|
| $e^2$ 추정오차 | **구간 내내 누적**되는 비용 | Δ가 길수록 커진다. Δ를 억제하는 힘 |
| $P_{tx}$ 전력 | 갱신 **1회당** 발생 | 구간당 1회. Δ가 길수록 단위시간 비용 감소 |
| $C_{freq}$ 혼잡 | 갱신 1회당 채널 점유 | 동상 |
| $\mathbb{I}_{redundant}$ | 갱신 1회당 이진 | 동상 |

즉 **Δ↑ → 오차↑·전력↓·혼잡↓**, **Δ↓ → 오차↓·전력↑·혼잡↑** 의 트레이드오프가
성립해야 하고, 이것이 논문의 학습 대상이다. 현재 구현은 오차항이 클램프 아티팩트이고
전력항만 살아 있어 트레이드오프가 아예 없다.

### 정규화 기준 (전부 [0,1])

| 항 | 정규화 | 비고 |
|---|---|---|
| $e^2$ | $\min(1, e^2/e_{max}^2)$ | 현재 $e_{max}=10$ m. **8절 D5** — 근거 필요 |
| $P_{tx}$ | $(p - 10)/(23 - 10)$ | 디코더 범위에서 유도. 하드코딩 금지 |
| $C_{freq}$ | 해당 서브채널 CBR (구성상 이미 [0,1]) | 에어타임 실측 |
| $\mathbb{I}_{red}$ | {0, 1} | 8절 D6 |

---

## 5. 전이(Transition) 정의

버퍼에 들어가는 튜플은 차량 $i$의 결정 $k$에 대해:

$$\big(s_k^{(i)},\ a_k^{(i)},\ R_k^{(i)},\ s_{k+1}^{(i)},\ done,\ \Delta_k^{(i)}\big)$$

- $s_k$: 결정 시점 $t_k$의 18차원 관측. **모델 추론에 넘긴 바로 그 벡터**여야 한다(P1, P3).
- $a_k$: 모델의 **원시 출력**(디코딩 전). 디코딩된 (Δ, ch, p)가 아니다 — 정책 갱신에 원시값이 필요.
- $R_k$: 구간 $[t_k, t_{k+1})$의 보상. 4절 + 8절 D2.
- $\Delta_k = t_{k+1} - t_k$: **실제 경과 시간**. 액션이 요청한 Δ와 다를 수 있다
  (전송 실패로 갱신이 밀리거나, 차량이 이탈하는 경우). 요청값이 아니라 실측값을 넣는다.
- $done$: 차량이 통신 범위를 이탈했을 때 True. 이때 종단 전이를 한 번 push한다.

전송이 **실패**한 경우의 처리는 8절 D7.

---

## 6. 모델 운용 (Act / Rest 핫스왑) — 변경 없음

`scenario.md` 원안대로 구현되어 있고 검증도 통과했다. 이번 재설계의 대상이 아니다.

- Act 모델이 서빙하며 배치를 채우고, 가득 차면 Rest 모델이 백그라운드 학습, 완료 시 역할 교대.
- HW feasibility 실측 완료(`results/hw_feasibility.json`): 단일 GPU에서 Act/Rest 공유 시
  추론 지연 평균 **1.232 ms**, p99 2.54 ms. GPU 2장 분리 대비 차이 +1.8%로 무시 가능.
- 논문에는 **단일 GPU 구성**을 주장으로 삼는다. 실제 RSU에 GPU 4장이 달릴 리 없으므로 그쪽이 설득력 있다.

---

## 7. 지표 (논문 결과표)

| 지표 | 정의 | 현재 문제 |
|---|---|---|
| Mean AoI | 관측 시점별 $t - t_{last\_update}$ 의 시간평균 | `max(1.0, ·)` 클램프로 상수 포화 → **클램프 제거** |
| Peak AoI | 갱신 직전 age의 평균(또는 최대) | 동상. 8절 D8에서 평균/최대 확정 |
| Outage (packet loss) | tx_fails / tx_attempts | 정상 |
| Mean/Max estimation error | dead reckoning 오차 | age 클램프에 오염 → 클램프 제거로 동반 해소 |
| Avg Tx power, Total energy | 실측 | 정상 |
| Jain's fairness (AoI, error) | 차량별 평균의 공정성 | 정상 |
| Mean CBR | 에어타임 실측 점유율 | 정상 |

`low_speed_error` / `high_speed_error`는 버킷이 비면 `mean_error`로 폴백하므로
세 값이 같게 찍힐 수 있다. 논문 표에 넣으려면 **표본 수를 함께 보고**하거나 폴백을 없앤다.

---

## 8. 결정 현황 (2026-08-29, `User_Response.md` 반영)

상세 근거와 반론은 **`idea/Claude_Response.md`**에 있다.

| # | 항목 | 결정 | 상태 |
|---|---|---|---|
| D1 | 정본 클래스 | `hot_swap_trainer.AoiV2IEnv`에 Δ 이식, `src/aoi_env.py` 폐기 | **확정** |
| D2 | SMDP 구간 보상 | 오차항만 **스텝별 정규화 후 구간 누적**, 나머지 3항은 갱신 1회 임펄스, $\gamma^\Delta$ 할인 | **확정** |
| D3 | n_queue | RSU 장부 기반 + **신선도 가드**(신선하거나, 정지 상태이고 그 신호가 아직 적색일 때만 사용) | 확정, $\tau_{fresh}$ 초안 1.0 s 승인 대기 |
| D4 | stop_imminent(15) | [15] 제거, [7]·[11]·[12] 유지로 해석 | **해석 확인 필요** |
| D5 | 오차 정규화 | $e_{max}=800$ m는 Optuna로 보정 불가(전력항의 1/130) → 대안 3안 제시 | **재결정 필요** |
| D6 | I_redundant | "예측이 맞았으면 중복" $\mathbb{I}=\mathbb{1}[e \le \epsilon]$, 판정을 simulationStep 이후로 | 확정, $\epsilon$ 초안 3.2 m 승인 대기 |
| D7 | 전송 실패 | 즉시 재시도(같은 결정의 연장, 모델 재호출 없음), 실측 Δ 기록 | 확정, 연속실패 상한 초안 10회 승인 대기 |
| D8 | Peak AoI | 전 차량·전 시간에 대한 **최대값**, 클램프 제거 | **확정** |
| 구조 | 학습 루프 | gym Env 아님. **직접 이벤트 구동 루프** (차량별 Δ 만료 시에만 결정) | **확정** |

### D2 확정 수식

$$R_k = -\Big( w_1 \sum_{t \in [t_k, t_{k+1})} \mathrm{Norm}(e^2(t))\cdot\frac{\delta t}{1\,\mathrm{s}} \;+\; w_2 \mathrm{Norm}(P_{tx}) + w_3 \mathrm{Norm}(C_{freq}) + w_4 \mathbb{I}_{red} \Big)$$

오차항만 누적되므로 **이동 중인데 갱신하지 않으면 매 스텝 벌점**이 쌓이고,
정지 차량은 $e \approx 0$ 이라 아무리 오래 방치해도 0이다. Δ 트레이드오프는 이 비대칭에서 나온다.
사용자가 D2에서 요구한 "이동 상태 미갱신 패널티"가 이 항으로 실현되므로 별도 항을 추가하지 않는다.

### 구조 확정: 직접 이벤트 구동 루프

차량마다 결정 시점이 다른 SMDP이므로 `model.learn(env)` 형태로 표현할 수 없다.
정본 클래스는 시나리오 진행과 물리(SUMO·PHY)만 담당하고, 결정 판단과 전이 조립은 바깥 루프가 한다.
9종 baseline은 전부 `update(batch)` 인터페이스라 구조 변경으로 다시 짤 필요가 없음을 확인했다.
Δ 매핑도 9종 전부 기하(`delta_from_unit`)로 일관됨을 확인했다.

---

## 9. 구현 현황 (2026-08-30, Claude Code)

`User_Response_v2.md`의 D3·D4·D6·D7 승인과 D5 재답변을 반영하여 **구현 완료**. 테스트 119/119 통과.

### 확정된 수치

| 기호 | 값 | 유도 근거 |
|---|---|---|
| `V_LIMIT` | 13.32 m/s (48.0 km/h) | `generated.net.xml`의 최대 차선 제한속도에서 **자동 추출** |
| `E_REF` | 13.32 m | `V_LIMIT` × 1 s. 위치오차를 "몇 초분의 무지"로 환산 |
| `REDUNDANT_ERR_EPS_M` (ε) | 3.2 m | SUMO 기본 차선폭. lane-level accuracy |
| `LEDGER_FRESH_S` (τ_fresh) | 1.0 s | 그 사이 최대 이동 13.3 m < 차간거리 |
| `MAX_TX_RETRIES` | 10 (= 1.0 s) | 연속 실패 상한 |
| `STATE_DIM` | 17 | 18에서 stop_imminent 제거 |
| `warmup_steps` 기본 | **350** (35 s) | 아래 참조 |

> [!NOTE]
> **D5 사용자 답변에 대한 보정.** "법적 최대 60 km/h"로 말씀하셨으나 이 시나리오의 실제 제한속도는
> **40 km/h**다(`make_sumo_set.py:27` `AV_SPEED = 40.0`, net.xml 실측 8.89~13.32 m/s = 32~48 km/h).
> 리터럴 16.667을 박는 대신 Δ 상한 45 s를 net.xml의 실제 적색 시간에서 유도한 것과 **같은 방식**으로
> `get_sumo_max_edge_speed()`가 net.xml에서 읽는다. `AV_SPEED`를 60으로 올리면 `E_REF`도 자동으로 따라간다.
> 정규화 형태는 포화 없는 `e²/(e² + E_REF²)`를 썼다(D5 제안 (다)).

### 구현 내역

| 항목 | 파일 | 내용 |
|---|---|---|
| Δ 게이팅 | `hot_swap_trainer.py::step` | `next_update_t` 도달 전까지 차량은 침묵. grant는 발급 스텝이 아니라 만료 시점에 발화 |
| 구간 보상 | `_finalize_interval` | 오차항만 스텝별 누적, 나머지 3항은 갱신 1회 임펄스 |
| I_redundant | `_is_redundant_update` | "예측이 맞았으면 중복"으로 재정의. 판정을 `simulationStep()` **이후**로 이동 |
| n_queue | `_ledger_queue_count` | RSU 장부 기반 + 신선도 가드. SUMO 직접 조회 폐기 |
| 재시도 | `step` 6절 | 실패 시 다음 스텝 재시도, 모델 재호출 없음. 상한 도달 시 구간 종료 |
| Peak AoI | `get_metrics` | 전 차량·전 시간 최대값. `mean_peak_aoi` 병기 |
| 이중 보상 제거 | `HotSwapRLScheduler` | 스케줄러의 자체 3항 보상 삭제. 순수 추론 + `push_transition`만 |
| 이중 상태 제거 | 동상 | `decide_grant`가 환경이 만든 벡터를 받고, 폭이 다르면 assert |
| 이벤트 구동 루프 | `run_hot_swap_training`, `evaluate.py`, `hpo.py` | 세 곳 전부 Δ 만료 차량만 결정 |

### 검증 결과

**Δ 반영 (동일 시드, Δ만 변경)** — 수정 전에는 두 열이 완전히 같았다.

| | Δ = 0.1 s | Δ = 45.0 s |
|---|---|---|
| tx_attempts | 6197 | **2** |
| mean_aoi | 0.191 s | **16.271 s** |
| mean_error | 0.892 m | **17.631 m** |
| 보상 내 오차항 비중 | 0.34% | **98.51%** |
| I_redundant 발화 | 99.48% | **0.00%** |

트레이드오프가 성립한다: 자주 갱신하면 중복 페널티(50%)와 전력(39%)이, 드물게 갱신하면 오차(98%)가 지배한다.

**모델 입력 liveness (원칙 P3)** — `etc/scripts/verify_model_input_liveness.py`, **17/17 전부 live**.
이전 검사(`verify_observation_liveness.py`)는 `env.step()` 반환값을 봤기 때문에 15/18이 죽은 것을 놓쳤다.
새 스크립트는 `decide_grant`를 가로채 **모델이 실제로 받는 텐서**를 잰다.

### 구현 중 추가로 발견한 결함

**1. 피처 [0] age는 SMDP에서 구조적으로 상수 0이다.** 결정 시점이 항상 갱신 직후이므로 정의상 age = 0.
원칙 P4("죽은 항은 설계에서 뺀다")를 적용해 **마지막 예측 오차** `norm_sq_error(e_last)`로 교체했다.
RSU가 그 순간 공짜로 아는 값이면서, "이 차량이 얼마나 예측 가능한가"를 직접 알려주므로 Δ 결정에 정확히 필요한 정보다.

**2. `warmup_steps=35`는 원래부터 빈 실행이었다.** 3.5초로는 차량이 RSU 반경 300 m에 도달하지 못한다.

| warmup | 3.5 s | 15 s | 35 s | 70 s |
|---|---|---|---|---|
| 범위 내 차량 | **0** | 1 | 22 | 70 |

이전에는 `mean_aoi`가 관측 없을 때 **1.0으로 폴백**해서 빈 실행이 "정상"으로 통과했다.
폴백을 0.0으로 정직하게 바꾸고, `n_observations` / `n_vehicles_seen`을 지표에 추가해
빈 실행이 숫자로 드러나게 했다. 기본 warmup은 350(35 s)으로 올렸다.

**3. 테스트가 `18`을 리터럴로 박고 있었다.** 15개 파일에서 `STATE_DIM`을 읽도록 교체했다.
상태 차원이 바뀔 때마다 테스트를 손으로 고쳐야 하는 구조는 그 자체가 결함이다.

**4. `DummyPolicy`가 디바이스를 맞추지 않았다.** 실 baseline 9종은 `BaseAgent._to_tensor`로
모델 디바이스를 따르는데 테스트 스텁만 CPU 고정이라, Act 모델이 GPU에 올라가면 forward가 죽었다.

---

## 10. 검증 실측 결과 (2026-08-30)

### 학습된 정책의 Δ 분포 — 정상

PPO 1,500스텝(구간 4,676건). **양극단 붕괴 없음.**

| p10 | p25 | p50 | p75 | p90 | 평균 | 최대 |
|---|---|---|---|---|---|---|
| 0.200 s | 0.200 s | 0.200 s | 0.500 s | 3.500 s | 2.267 s | 45.200 s |

하한(<0.2 s) 32.8%, 상한(>40 s) 2.0%. 버퍼 `delta_t` 고유값 **234개**로 $\gamma^\Delta$ 할인이 실제로 동작한다
(수정 전에는 고유값 1개, 즉 상수 0.1이라 SMDP 할인이 무의미했다).
D2에서 우려했던 "Δ를 무조건 늘리는 퇴화"는 관측되지 않았으므로 시간 정규화 안은 보류한다.

### 보상 4항 기여도 — CBR만 1% 언저리

| 항 | 정규화 평균 | 가중 기여 | 비중 |
|---|---|---|---|
| r_err | 0.84727 | 0.42364 | 74.98% |
| i_redundant | 0.91916 | 0.09192 | 16.27% |
| r_power | 0.22662 | 0.04532 | 8.02% |
| **cbr** | 0.02064 | 0.00413 | **0.73%** |

### CBR이 작은 것은 결함이 아니라 물리다 — 다만 논문 서사에 영향이 있다

밀도를 벤치마크 전 구간에서 스윕한 결과, CBR은 밀도에 대해 **단조 증가**하지만 55 veh/km에서도 2%에 머문다.

| density | 차량/스텝 | mean_cbr | max_cbr | tx | packet loss |
|---|---|---|---|---|---|
| 15 | 30.6 | 0.01081 | 0.02688 | 3862 | 0.085 |
| 25 | 44.1 | 0.01569 | 0.04256 | 5602 | 0.097 |
| 35 | 53.0 | 0.01901 | 0.05040 | 6788 | 0.106 |
| 45 | 58.7 | 0.02099 | 0.05376 | 7498 | 0.102 |
| **55** | 59.4 | **0.02129** | 0.05712 | 7602 | 0.108 |

수치는 물리와 정확히 일치한다. 300 B 프레임의 에어타임은 448 µs이므로 100 ms 스텝의 **0.448%**를 점유한다.
밀도 55에서 19.0 tx/step이 4개 서브채널에 분산되어 채널당 4.75회 → 4.75 × 0.448% = **0.0213**. 실측과 동일하다.

**함의**: 이 구성에서 채널은 실질적으로 한산하다. ETSI ITS-G5의 DCC 개입 임계인 CBR ≈ 0.62에 도달하려면
채널당 138회/스텝, 즉 지금의 **약 29배** 부하가 필요하다. 취약구간 겹침 확률도 0.896%에 불과하므로
현재 관측되는 패킷 손실 ~10%는 **충돌이 아니라 거리·전력에 따른 잡음 제한**이다(수정 전 89%가 가짜 충돌이었던 것과 대조).

즉 `scenario.md`가 적은 "너무 잦은 갱신은 전력만 낭비되며 congestion 및 충돌 증가" 중
**전력 낭비와 중복 갱신은 보상에서 실제로 작동하지만(8.0% + 16.3%), 혼잡은 이 시나리오에서 거의 작동하지 않는다.**

### D9 결정: (가) 한계로 명시하고 현행 유지 — **확정 (2026-08-30, 사용자)**

시나리오·보상·액션 공간은 그대로 둔다. 대신 논문에 혼잡 항의 작동 범위를 실측 근거와 함께 명시한다.
검토했으나 채택하지 않은 대안: 서브채널 4→1(`ch` 액션이 사라져 하이브리드 액션 전제가 깨짐),
배경 트래픽 모델링(근거 문헌 필요 + 재훈련), 페이로드 CAM→CPM 확대(CBR 3.7배이나 시나리오 변경).

논문에 쓸 문장은 아래 12절에 준비해 두었다.

---

## 11. 남은 작업

1. ~~D4·D5 확정~~ / ~~구현~~ / ~~모델 입력 liveness 17/17~~ / ~~Δ 반영 검증~~ / ~~Δ 분포 확인~~ / ~~보상 기여도 실측~~ — **완료**
2. ~~9종 baseline 계약 재검증~~ — 완료 (STATE_DIM 17에서 9/9 PASS)
3. ~~D9 결정~~ — **(가) 한계 명시로 확정.** 논문용 문안은 12절
4. `simulation_plan.md` 5-4절 사전 점검 재측정 (STATE_DIM 17·warmup 350 반영)
5. 그 다음에 20만 스텝 착수 (사용자 승인 대기)
6. **본훈련·HPO 후**: 12-1절의 보상 비중 잠정치를 최종치로 교체, ETSI DCC 임계 문헌 확보

---

## 12. 논문에 명시할 한계 (D9 확정 사항)

### 12-1. Limitations 절에 넣을 문안 (초안)

> **Channel load regime.** The congestion penalty $C_{freq}$ is measured as the true 802.11p airtime
> occupancy of the RSU's subchannels: a 300-byte ETSI CAM at the 6 Mbps base rate occupies the channel
> for 448 µs, i.e. 0.448 % of a 100 ms scheduling step. Across the evaluated density range
> (15--55 veh/km) the measured Channel Busy Ratio grows monotonically from 0.0108 to 0.0213, so the
> RSU cell studied here operates in a lightly loaded regime, well below the CBR $\approx$ 0.62 at which
> ETSI ITS-G5 decentralized congestion control would intervene. Two consequences follow, and we state
> them explicitly rather than tuning the scenario to avoid them. First, the packet losses we report
> (8.5--10.8 %) are noise-limited -- set by distance and transmit power -- not collision-limited: the
> vulnerable-period overlap probability between two co-channel frames is $2T_{air}/T_{step} = 0.90$ %.
> Second, of the four reward terms, the congestion penalty is the smallest contributor
> (0.73 % of the mean reward, against 74.98 % for estimation error, 16.27 % for redundant updates and
> 8.02 % for transmit power). The update-interval trade-off this paper optimizes is therefore driven
> by estimation error against power and redundancy, with congestion a secondary term that nonetheless
> scales correctly with density. Regimes where congestion dominates -- denser cells, larger
> cooperative-perception payloads (ETSI TS 103 324 CPMs exceed 1 kB), or a shared band carrying
> background ITS traffic -- are left to future work.

영문 문안은 초안이다. `writer/main.tex` 작성 시 문체를 맞춰 다듬을 것.

> [!WARNING]
> **투고 전 반드시 처리할 것 2건.**
>
> 1. **보상 비중 수치(0.73 / 74.98 / 16.27 / 8.02 %)는 잠정치다.** PPO를 1,500스텝만 돌린
>    사실상 미훈련 정책에서 측정한 값이다. 학습이 진행되면 정책의 Δ 선택이 바뀌고 네 항의 균형도
>    함께 바뀐다. 특히 Optuna가 $w_1{\sim}w_4$를 탐색하므로 최종 가중치 자체가 달라진다.
>    **본훈련·HPO 완료 후 재측정한 값으로 교체할 것.** 재측정 스크립트는 `_finalize_interval`을
>    가로채 항별 평균을 집계하는 방식이며, 이번 세션의 검증에 쓴 것과 동일하다.
>
> 2. **"CBR ≈ 0.62에서 ETSI DCC가 개입한다"는 문헌 검증이 아직 안 됐다.** ETSI TS 102 687의
>    DCC 상태 전이 임계로 통용되는 값이지만, 이 프로젝트는 날조 방지를 위해 인용을 전수 대조해 왔다
>    (`Conversation.md` 4절, `etc/scripts/verify_bibliography.py`). **원 규격을 확인해 정확한 조항과
>    수치를 확보하거나, 확보되지 않으면 이 문장을 빼고 "well below the levels at which congestion
>    control mechanisms engage" 같은 정성적 표현으로 바꿀 것.** 다른 수치는 전부 자체 실측이라
>    이 한 건만 외부 근거가 필요하다.

### 12-2. 이 주장을 뒷받침하는 수치 (전부 실측)

| 값 | 수치 | 출처 |
|---|---|---|
| 프레임 에어타임 (300 B @ 6 Mbps) | 448 µs | `Communications.frame_airtime_s`, 40 µs + 8 µs × 51 심볼 |
| 스텝당 1회 점유율 | 0.448 % | 448 µs / 100 ms |
| 취약구간 겹침 확률 | 0.896 % | $2T_{air}/T_{step}$ |
| CBR (15 → 55 veh/km) | 0.0108 → 0.0213 | 10절 스윕 표 |
| ETSI DCC 개입 임계까지의 배수 | 약 29배 | 138 tx/채널·스텝 필요 vs 실측 4.75 |
| 패킷 손실 | 0.085 → 0.108 | 동 스윕 표 |
| 보상 내 혼잡 항 비중 | 0.73 % | PPO 1,500스텝, 구간 4,676건 |

> [!IMPORTANT]
> 이 표는 **심사 대응의 핵심 자산**이다. "왜 혼잡을 고려한다면서 CBR이 2 %냐"는 질문은 반드시 나온다.
> 답은 "고려했고, 측정했고, 이 구성에서는 작다는 것까지 정량적으로 안다"이다.
> 혼잡 항을 뺐다면 할 수 없는 답변이므로, 항 자체는 유지한다.

### 12-3. 결과 표에 함께 실을 것

밀도 스윕 표(10절)를 논문 결과 절에 **그대로 싣는다.** CBR이 밀도에 단조 증가한다는 사실이
"혼잡 모델이 살아 있다"는 증거이고, 절대값이 작다는 사실이 위 한계 진술의 근거다. 둘은 같은 표에서 나온다.
