# Critic 리뷰 — 물리 계층 · 관측/행동 인터페이스 · SUMO 시나리오

검토자: critic-physics (읽기 전용, 소스 수정 없음)
검토일: 2026-08-31
검토 대상: `coder/src/Communications.py`, `coder/src/rl_interface.py`, `coder/src/dynamics_predictor.py`,
`coder/src/sumo/make_sumo_set.py` 및 생성 XML, 그리고 이들 모듈의 계약이 소비되는 지점에 한해
`coder/src/hot_swap_trainer.py` · `coder/src/hpo.py` · `coder/src/evaluate.py`
기준 설계: `Conversation.md`, `aoi_scheduling_design.md`
이전 리포트: 같은 경로의 이전 판(git에 보존됨), 아래 "이전 지적 사항의 처리 상태"에서 8건 전부 대조함

모든 수치는 `cat -n`으로 직접 읽은 코드와, `/home/imnyj/venv/bin/python`으로 실제 SUMO(libsumo)를
구동해 얻은 실측치에 근거한다. 실측 스크립트는 스크래치패드에만 두었고 저장소에는 아무것도 쓰지 않았다.
다만 진단을 위해 환경을 실제로 reset·step 했으므로 `src/sumo/generated.*.xml`과
`.sumo_gen_signature.json`이 재생성되었다. 이 파일들은 어차피 다음 실행에서 서명 불일치로
재생성되는 대상이라 무해하다고 판단했으나, 고정 파일셋을 유지해야 한다면 알려주기 바란다(질문 Q6).

---

## 판정

**CONDITIONAL — 현 상태로 20만 스텝 본훈련에 착수하는 것에 반대한다.** 세 가지가 걸린다.
첫째, RSU 장부의 위치와 시각이 한 SUMO 스텝(0.1 s)만큼 어긋나 있어 논문의 대표 지표인 추정 오차에
차량 속도에 비례하는 제거 불가능한 바닥값이 깔린다. 실측으로 Δ=0.1 s 전송 시 평균 오차 0.8153 m가
나오는데 이는 같은 구간 평균 속도 8.099 m/s에 0.1 s를 곱한 0.810 m와 비 1.007로 일치한다. 즉 측정된
오차의 거의 전부가 물리가 아니라 부기(bookkeeping) 오차다. 둘째, 보상의 셋째 항인 혼잡 페널티가
수치적으로 무력하다. 실측 CBR은 랜덤 정책에서 평균 0.00087, 최대 0.0056이고, 모든 차량이 0.1초마다
같은 서브채널로 쏘는 병리적 구성에서도 망 평균 0.0594에 그친다. 설계가 명시한 "각 항 [0,1]
Min-Max 정규화"가 이 항에는 적용되지 않았고, 그 결과 논문이 내세우는 두 목적 중 하나인 망 혼잡
최소화가 보상·HPO 목적함수·평가표 어디에도 실질적으로 존재하지 않는다. 셋째, 최종 leaderboard를
만드는 `evaluate.py`가 폐기된 [20,30] dBm 전력 정규화를 그대로 쓰고 있어, 이미 한 번 고쳤다고
선언된 결함이 평가 경로에서 재발해 있다. 첫째와 둘째는 보상을 바꾸므로 나중에 고치면 9종 × 20만
스텝을 통째로 다시 돌려야 한다. 착수 전에 처리하기 바란다.

물리 계층 자체는 건강하다. 경로손실·잡음바닥·MCS 임계·에어타임·안테나이득·Rayleigh 폐형식을
전부 재계산해 코드값과 일치함을 확인했고, 이전 리포트가 지적한 `noise_floor_mw`의 대역폭 역산은
수정되었다. 관측 벡터의 데이터 누수도 심각한 것은 없었다 — 17차원 중 미래 정보나 보상 자체를
흘리는 차원은 없으며, 결정 시점이 갱신 도착 시점과 일치하므로 live SUMO 값을 읽는 것도 방어
가능하다. 문제는 누수가 아니라 위 세 가지 정합성·척도 문제다.

---

## 결함 목록

### L1 [CRITICAL] RSU 장부의 위치와 타임스탬프가 한 스텝 어긋난다 — 추정 오차에 v·0.1 m 바닥값이 깔린다

`hot_swap_trainer.py:1419-1437`이 이번 스텝에 발사할 grant들을 모으면서 `st = self._get_vehicle_state_dict(vid)`로
차량 위치를 읽는다. 이 시점은 `libsumo.simulationStep()`(`:1442`) **이전**이므로 `item["pos"]`는 시각
t의 위치다. 그런데 전송이 성공했을 때 장부를 갱신하는 `:1651-1655`는 `"pos": item["pos"]`(시각 t의
위치)를 `"t_update": self.sim_time`(시각 t+0.1)과 짝지어 저장한다. 그 결과 RSU의 등속 외삽
`p_hat = pos + vel·(now − t_update)`가 항상 실제보다 한 스텝만큼 뒤처진 점에서 출발한다.
같은 파일의 `_register_vehicle`(`:1267`)은 `"t_update": self.sim_time if is_initial else self.sim_time - self.step_length`로
**올바른 관례를 이미 쓰고 있다.** 두 곳이 서로 다른 관례를 쓰고 있다는 사실 자체가 이것이 의도가
아니라 누락임을 보여준다.

실측으로 확인했다. 모든 차량에 Δ=0.1 s(=매 스텝 전송), 23 dBm, 단일 서브채널을 준 600스텝 구간에서
`mean_error = 0.8153 m`가 나왔다. 장부가 정렬되어 있다면 Δ=0.1 s에서 남는 오차는 가속도 2차항
`0.5·a·t² ≈ 0.5·2.6·0.01 = 0.013 m` 수준이어야 한다. 같은 구간의 관측 speed 피처 평균 0.6080에
`V_LIMIT = 13.32`를 곱하면 평균 속도 8.099 m/s이고, 여기에 스텝 길이 0.1 s를 곱하면 0.810 m다.
측정/예측 비는 1.007이다. 측정된 오차의 99 %가 물리가 아니라 한 스텝 지연이다.

파급은 세 갈래다. (가) 논문 표의 `mean_error`·`max_error`·`high_speed_error`가 전부 부풀려진다.
정지 차량은 v=0이라 영향이 없으므로 "정지 차량은 갱신이 불필요하다"는 핵심 주장 자체는 살아남지만,
저속/고속 오차 대비의 절대 격차가 왜곡된다. (나) `err_now`(`:1564-1565`)는 스텝 **이후**의 실제
위치와 대조해 계산되는데, 실제로 패킷에 실린 위치는 스텝 **이전**의 것이다. 이 값이 관측 피처 [0]
`last_pred_err`(`:1655` → `rl_interface.py:471`)로 들어가고 `I_redundant` 판정(`:1259`,
임계 3.2 m)에도 쓰인다. 즉 RSU가 원리적으로 계산할 수 없는 양이 관측과 보상에 섞여 있다.
크기는 v·0.1 ≤ 1.33 m로 작지만 "State에 실제 오차를 넣지 말 것"(설계 §7)의 경계선을 애매하게 만든다.
(다) `interval_start_t`가 스텝 이전 시각으로, `delta_actual`(`:1343-1344`)이 스텝 이후 시각으로
계산되어 SMDP 할인 지수 `delta_t`가 항상 Δ + 0.1 s가 된다. Δ=0.1일 때 두 배다.

**코더 지시**: 전송 성공 시 장부에 넣는 `(pos, vel, t_update)` 삼중항을 같은 시각으로 맞출 것.
가장 작은 수정은 `:1654`를 `"t_update": self.sim_time - self.step_length`로 바꾸는 것이며,
이는 `_register_vehicle:1267`의 관례와 일치한다. 동시에 `err_now`를 계산할 때 대조 대상을
"패킷에 실린 위치가 유효한 시각"의 실제 위치로 맞추거나, 아니면 `pending_transmissions`를
`simulationStep()` **이후에** 수집하도록 순서를 바꿔 전송 시각과 관측 시각을 한 점으로 모을 것.
어느 쪽이든 `interval_start_t`/`delta_actual`도 같은 관례로 통일해야 한다. 수정 후에는 Δ=0.1 s
전량 전송 구성에서 `mean_error`가 1 m대에서 0.01 m대로 떨어지는지를 회귀 기준으로 삼을 것.

### L2 [HIGH] 혼잡 페널티 `w3·Norm(C_freq)`가 수치적으로 무력하다 — 논문의 두 목적 중 하나가 학습되지 않는다

CBR은 `hot_swap_trainer.py:1501-1507`에서 `CBR[ch] = (해당 채널 grant 수) × frame_airtime / step_length`로
정의된다. 300 B를 6 Mbps로 보내는 802.11p 프레임의 에어타임은 448 µs이고 스텝은 100 ms이므로
grant 하나당 채널 점유는 0.448 %다. 실측했다. 랜덤 정책(Δ는 기하 매핑 균등, 채널 균등, 전력 균등)
600스텝에서 관측 피처 [14]는 31,202개 샘플 중 **고유값이 6개**뿐이고 평균 0.00087, 최대 0.0056이었다.
`_finalize_interval`(`:1329`)이 실제로 보상에 쓰는 `subchannel_cbr[ch]`도 최대 0.0179에 그친다.
모든 차량이 매 스텝 같은 채널로 전송하는 병리적 구성을 억지로 만들어도 망 평균 CBR은 0.0594,
가장 붐비는 서브채널이 0.2374였다.

즉 `r_cong ∈ [0, 0.018]`(현실) 또는 `[0, 0.24]`(병리)인데, 같은 보상식의 `r_power`는
`(p − 10)/13`로 정확히 [0,1]을 채우고 `r_red`는 {0,1}이다. `hpo.py:99-116`이 w1~w4를 합 1로
정규화하므로 w3를 아무리 키워도 혼잡 항의 기여는 0.006을 넘지 못한다. 전력 항 대비 두 자릿수
작다. `Conversation.md` §3의 가중치 주석은 "각 항의 Scale이 매우 상이하므로 보상 계산 전 모든
항목을 [0,1] 범위로 Min-Max 정규화 처리합니다"라고 명시하는데, 이 항만 정규화되지 않았다.

같은 공백이 아래 두 단계에도 있다. `hpo.py:274-297`의 `compute_composite_objective`는
오차·AoI·아웃티지·전력 네 항만 쓰고 혼잡을 아예 포함하지 않는다. `evaluate.py:320-333`의
`agg_cols`에도 `mean_cbr`/`max_cbr`이 없어(두 값 모두 `hot_swap_trainer.py:1837-1838`에서
계산은 된다) 논문 표에 실릴 CSV에 혼잡 지표가 남지 않는다. 설계 §12가 "CBR/충돌률"을 핵심
지표로 못박았는데도 그렇다.

주의할 점 하나. 혼잡 자체가 시뮬레이션에서 아무 일도 안 하는 것은 아니다. 병리적 구성에서
패킷 손실률이 20.3 %까지 올라갔고(거리·전력만으로는 2~3 %여야 한다) 이는 동일 채널 간섭이
실제로 작동한다는 증거다. 다만 그 압력이 보상에는 **간접 경로**(전송 실패 → 미갱신 → 오차 누적)로만
전달되고, 설계가 명시한 **명시적 혼잡 항**은 죽어 있다.

**코더 지시**: 임의로 고치지 말고 아래 질문 Q1을 상위 에이전트/사용자에게 올린 뒤 결정에 따를 것.
선택지는 (i) 서브채널 수 축소(설계문 v2가 4→1을 대안으로 남겨둔 바 있음), (ii) 페이로드 확대 또는
운용 레이트 하향으로 에어타임 증가, (iii) 차량 밀도 상향, (iv) `Norm(C_freq)`를 실현 가능 최대치로
Min-Max 정규화해 [0,1]을 실제로 채우게 하는 것이다. 어느 쪽이든 결과를 바꾸는 결정이다.
결정 후에는 `hpo.compute_composite_objective`와 `evaluate.agg_cols`에 혼잡 지표를 추가해
세 단계(보상·HPO·평가)가 같은 목적을 말하게 할 것.

### L3 [HIGH] `evaluate.py`의 전력 정규화가 폐기된 [20,30] dBm 창을 쓴다 — 이미 고쳤다고 선언된 결함의 재발

`evaluate.py:345`:

```python
p_norm = (df_leaderboard_agg["avg_tx_power_dbm"] - 20.0).clip(lower=0.0) / 10.0
```

현행 행동 범위는 `rl_interface.py:41-42`의 `P_MIN=10.0`, `P_MAX=23.0`이다. 이 식은 평균 전력이
20 dBm 이하인 모든 모델을 0으로 뭉개고, 상한 23 dBm에서도 0.3까지만 간다. 전력을 아끼도록 학습한
모델과 10 dBm 고정 정책을 구분하지 못한다는 뜻이다. 이 식이 들어가는 `composite_score`(`:346-353`)가
`eval_leaderboard.csv`의 정렬 기준, 즉 논문 표의 순위다. `Conversation.md` §5 항목 (C)가
"전력 정규화가 범위를 하드코딩... `(p−p_min)/(p_max−p_min)` 일반화 필요"라고 지적하고 해소되었다고
기록했는데, 학습 경로(`hot_swap_trainer.py:1325-1327`)와 HPO 경로(`hpo.py:398-399`, 주석에까지
"not a hardcoded [20, 30] window"라고 써 있다)는 고쳐졌고 평가 경로만 남았다.

곁가지로, 같은 파일이 만든 `results/eval/*.csv`(8월 27일자)는 모든 행의 `avg_tx_power_dbm`이
24.9 dBm으로 현행 상한 23 dBm을 넘는다. 폐기된 전력 범위에서 나온 산출물이므로 논문에 인용하거나
회귀 기준으로 삼으면 안 된다.

**코더 지시**: `evaluate.py:345`를 `rl_interface`의 `P_MIN`/`P_MAX`를 import해
`np.clip((p − P_MIN)/(P_MAX − P_MIN), 0, 1)`로 바꿀 것. `hpo.py:398-399`가 이미 정확한 형태이니
그대로 옮기면 된다. 리터럴을 다시 쓰지 말고 상수를 import할 것. 그리고 `results/eval/` 아래
8월 27일자 CSV 3종은 폐기 표시하거나 backup으로 옮길 것.

### L4 [MEDIUM] 같은 seed가 같은 결과를 주지 않는다 — 전역 `random` 스트림 위치가 SUMO 파일 캐시 상태에 좌우된다

`hot_swap_trainer.py:931-933`이 `random.seed(self.seed)` 직후 `ss.make_sumo_files()`를 부른다.
`make_sumo_set.py:331-336`의 도로망 생성은 엣지마다 `random.uniform`을 두 번 호출하는데,
서명이 일치해 생성이 건너뛰어지면(`make_sumo_set.py:495-500`) 이 호출이 하나도 일어나지 않는다.
직접 세어 확인했다: 재생성 시 정확히 **200회**의 `random.uniform`이 소비되고, 캐시 적중 시 0회다.
같은 seed로 시작해도 재생성 후 첫 `random.random()`은 0.9690, 캐시 적중 후 첫 값은 0.6394로 다르다.

`hot_swap_trainer.py:1632`의 `is_succ = random.random() < prob`가 바로 이 전역 스트림을 쓴다.
따라서 업링크 성공/실패의 전체 실현이 "디스크에 캐시가 있었는가"에 달라진다. 구체적으로,
에피소드 1은 서명 불일치로 재생성하고 에피소드 2부터는 캐시를 쓰므로 **같은 seed의 에피소드 1과 2가
서로 다른 채널 실현**을 갖는다. 밀도 스윕에서 밀도가 바뀔 때마다 재생성되므로 스윕 순서에 따라서도
달라진다. 설계 §15가 요구하는 "평가는 고정 정책·별도 run·시드 고정으로 재현"이 현재로선 성립하지 않는다.

섀도잉과 겹침 판정은 이 문제에서 자유롭다. `Communications.py:190-219`가 전용 `_shadow_rng`를 쓰고
`reset()`이 `comm.seed_channel(self.seed)`(`:1016`)로 매 에피소드 재시드하기 때문이다. 설계가 잘 된 부분이다.

**코더 지시**: Bernoulli 성공 판정을 전역 `random`에서 떼어내 환경 소유의 `random.Random(seed)`
인스턴스로 옮기고 `reset()`에서 재시드할 것. 이미 `Communications._shadow_rng`가 같은 이유로
같은 패턴을 쓰고 있으니 그대로 따르면 된다. 전역 `random.seed`는 SUMO 파일 생성 재현성 용도로만 남길 것.

### L5 [MEDIUM] 오차항만 구간 길이에 비례해 누적되어 네 항의 척도가 최대 45:1로 벌어진다

`hot_swap_trainer.py:1578`이 `interval_accum[vid] += norm_sq_error(err) * (step_length / 1.0)`로
구간 내내 오차를 적분하고, `_finalize_interval:1320`이 그 누적값을 `r_err`로 쓴다. 다른 세 항은
구간당 한 번, [0,1]에서 부과된다. Δ가 상한 45 s까지 갈 수 있으므로 `r_err`의 상한은 45,
나머지는 1이다. 최대 45배 차이다. 설계문 §D2가 "오차항만 누적"을 명시적 선택으로 기록했고
그것이 Δ 트레이드오프의 본체라는 논리도 이해되지만, `Conversation.md` §3의 정규화 주석
("모든 항목을 [0,1] 범위로 Min-Max 정규화")과는 정면으로 어긋난다. 그리고 `hpo.py`가 w1~w4를
합 1로 정규화하는 이상, w를 어떻게 뽑아도 이 45:1 척도차를 상쇄할 수 없다.

L2와 합치면 실질 보상은 `R ≈ −(w1·r_err + w2·Norm(P_tx))`이고, 네 항 설계 중 두 항만 살아 있다.

**코더 지시**: 이것은 결과를 바꾸는 설계 결정이므로 임의 수정 금지. 질문 Q2로 올린 뒤 지시를 따를 것.
현 상태를 유지한다면 최소한 논문 본문에 "오차항은 구간 적분이고 나머지 세 항은 구간당 1회"임을
명시하고, `hot_swap_trainer.py:748-759`의 docstring이 이미 그렇게 쓰여 있으니 표기만 일관되게 유지할 것.

### L6 [MEDIUM] `judge_uplink` 호출 방식이 모듈이 문서화한 계약을 깬다 — 섀도잉이 링크당 1회가 아니다

`Communications.py:296-299`의 docstring은 "One shadowing sample is drawn per link and reused for
that link's role as both the desired signal and as interference at the RSU, because it is a property
of the propagation path, not of the receiver's viewpoint"라고 보증한다. 이 보증은 **한 번의
`judge_uplink` 호출 안에서만** 성립한다(`:302-305`가 그룹 전체의 `powers`를 한 번에 만든다).

그런데 `hot_swap_trainer.py:1601-1612`는 그룹 안의 tagged 차량마다 `judge_uplink`를 **다시 호출한다**:

```python
for tagged in comm_group:
    interferers = [other for other in comm_group
                   if other[0] != tagged[0] and comm.draw_overlap(p_overlap)]
    probs = comm.judge_uplink([tagged] + interferers, num_subchannels=self.num_channels)
    succ_probs[tagged[0]] = probs[tagged[0]]
```

결과적으로 같은 차량의 같은 링크가 A의 판정에서와 B의 판정에서 서로 다른 섀도잉 샘플을 갖는다.
docstring이 명시적으로 배제한 "수신기 관점에 따라 달라지는 전파 경로"가 정확히 발생한다.
같은 루프에서 `draw_overlap`도 (tagged, other) 쌍마다 독립적으로 추출되므로 겹침 사건이 비대칭이다.
A의 프레임은 B에 맞았는데 B의 프레임은 A에 안 맞는 물리적으로 불가능한 실현이 생긴다.
주변 확률은 옳게 유지되므로 결과를 크게 왜곡하지는 않지만, 심사에서 통신 모델의 일관성을
물으면 방어하기 어렵다.

부수적으로, 섀도잉이 전송마다 독립 재추출된다. 로그노멀 섀도잉은 통상 10~25 m의 감쇠 거리를
갖는 공간 상관 과정이므로, Δ가 짧을 때(차량이 1 m 남짓 움직였을 때)도 완전히 새 샘플을 뽑는 것은
섀도잉 변동성을 과대평가한다. 이것은 근사의 문제이지 버그는 아니므로 논문에 한 줄 명시하면 족하다.

**코더 지시**: 한 스텝 · 한 서브채널의 그룹에 대해 `judge_uplink`를 **한 번만** 호출하도록 바꿀 것.
겹침 판정이 필요하다면 대칭 상삼각 쌍에 대해서만 `draw_overlap`을 뽑아 겹침 그래프를 먼저 만든 뒤,
그 그래프를 `judge_uplink`에 넘길 수 있도록 시그니처를 확장하는 편이 낫다(단, `Communications.py`
수정은 계약 변경이므로 코더가 설계 담당과 합의한 뒤 진행). 최소한 섀도잉 샘플은 그룹 단위로 한 번만
뽑아 재사용해야 docstring의 보증이 실제로 성립한다.

### L7 [MEDIUM] 속도 피처가 관측의 8.6 %에서 포화한다 — `v_max`가 실제 최고 속도가 아니다

`rl_interface.py:113-155`의 `get_sumo_max_edge_speed()`는 net.xml의 차선 제한속도 최댓값을 읽어
`V_LIMIT = 13.32 m/s`를 얻고, `StateVectorizer`가 이를 피처 [1][2][3]의 정규화 분모로 쓴다
(`:472-474`). 그러나 `make_sumo_set.py`는 `generated.rou.xml`에 `<vType>`을 전혀 쓰지 않으므로
SUMO의 `DEFAULT_VEHTYPE`이 적용되고, 그 `speedFactor`는 평균 1 · 표준편차 0.1의 절단 정규분포라
차량이 차선 제한속도를 최대 20 % 초과해 달릴 수 있다.

실측했다. 300스텝 구간에서 관측된 실제 속도의 최댓값은 **14.768 m/s**로 `V_LIMIT`을 11 % 초과했고,
전체 관측의 **8.62 %가 `V_LIMIT`을 넘었으며**, 피처 [3]이 정확히 1.0으로 클리핑된 비율도
**8.63 %**로 일치했다. 즉 가장 빠르게 달리는 — 다시 말해 등속 외삽이 가장 빨리 무너지는, 이 논문이
정확히 구분하고 싶어 하는 — 차량들이 관측에서는 서로 구분되지 않는다.

**코더 지시**: `get_sumo_max_edge_speed()`가 반환한 값에 SUMO 기본 `speedFactor`의 상한 계수를
곱하도록 하거나(절단 정규분포의 상한은 2이므로 실효 여유로 1.2 정도가 현실적),
`generated.rou.xml`에 `speedFactor`를 명시한 `<vType>`을 정의해 실제 상한을 결정론적으로 만들 것.
후자가 시나리오 재현성 면에서 낫다. 어느 쪽이든 `E_REF = V_LIMIT · 1.0`(`rl_interface.py:204`)이
함께 움직이므로 보상 척도가 바뀐다는 점을 인지하고 진행할 것.

### L8 [MEDIUM] `StateVectorizer.vectorize()`는 호출자가 없는 중복 구현이며, 쓰이면 특권 정보를 먼저 집는다

`rl_interface.py:370-449`의 `vectorize()`(노드 객체 경로)를 `grep -rn "\.vectorize("`로 찾은 결과
테스트 밖에서는 호출자가 0건이다. 실제 관측은 전부 `vectorize_from_dict()`(`:451-504`)가 만든다
(`hot_swap_trainer.py:1291`). 두 메서드는 같은 17차원을 서로 다른 코드로 두 번 구현하고 있고,
현재 미세하게 다르게 동작한다.

`vectorize()`의 `:441`은 `self._extract_queue_count(tls, getattr(vehicle_node, "__dict__", None))`로
**TLS 피처 딕셔너리를 먼저** 본다. 그 딕셔너리는 `dynamics_predictor.extract_tls_features`가
`extract_queue_features`(`dynamics_predictor.py:139-217`)로 만든 것이고, 그 `n_queue`는
`lane.getLastStepVehicleIDs` + `vehicle.getSpeed`로 **SUMO 실측**한 값이다. 실제 RSU가 가질 수 없는
정보다. 반면 `vectorize_from_dict`의 `:498`은 `state_dict`를 먼저 보고, `hot_swap_trainer.py:1178-1181`이
거기에 장부 기반 `_ledger_queue_count`를 넣어 두었기 때문에 올바른 값이 이긴다.
즉 **현재 실행 경로는 안전하지만, 죽은 쪽 코드는 누수 경로다.** 누가 `vectorize()`를 되살리는 순간
관측에 특권 정보가 섞인다.

**코더 지시**: `vectorize()`를 삭제하고 관련 테스트를 `vectorize_from_dict`로 옮기거나,
남긴다면 `_extract_queue_count`의 소스 우선순위를 `vectorize_from_dict`와 동일하게 맞출 것.
두 개의 관측 생성 경로를 유지하는 것 자체가 설계문 원칙 P1("관측 벡터는 한 곳에서만 만든다")에 어긋난다.

### L9 [MEDIUM] `with_queue` 최적화가 절반만 되어 있다 — SUMO 차선 순회는 여전히 스텝·차량당 3회 돈다

`hot_swap_trainer.py:1172-1177`의 주석은 `_get_vehicle_state_dict`가 스텝당 차량마다 3회 호출되므로
큐 계산을 관측 경로에서만 하도록 `with_queue` 플래그를 두었다고, 그것이 "step cost grow with the
square of the vehicle population"을 고친 것이라고 설명한다. 그러나 `with_queue`가 막는 것은
`_ledger_queue_count`(`:1178-1181`)뿐이다. 그 위 `:1145`의 `extract_tls_features(libsumo, vid, ...)`는
**무조건** 호출되고, `dynamics_predictor.py:316`이 그 안에서 `extract_queue_features(driver, vid)`를
**무조건** 호출하며, 그 함수는 `:191-213`에서 차선 전체 차량 목록을 받아 각각에 대해
`getLanePosition`과 `getSpeed`를 부른다. 즉 주석이 제거했다고 주장한 차선 순회가 그대로 3회 남아 있다.

덧붙여 `extract_tls_features`는 `predict_stop_imminent`/`predict_start_imminent`(`:345-364`)도
매번 계산하는데, 설계 결정 D4로 `stop/start_imminent` 피처가 관측에서 제거되었으므로 학습 경로에서는
계산 결과가 버려진다(`heuristic_scheduler`만 쓴다).

20만 스텝 × 9종을 앞둔 시점에서 처리량은 실행 가능성 자체를 좌우한다. `Conversation.md` §5의
실측 처리량 42~76 steps/sec, 모델당 약 58분이라는 추정도 이 비용을 포함한 값인지 확인이 필요하다.

**코더 지시**: `extract_tls_features`에 `with_queue`(또는 `need_queue`) 인자를 추가해
`extract_queue_features` 호출을 관측 경로에서만 수행하도록 할 것. `lane_id`/`lane_position`은
장부 갱신에 필요하므로 큐 순회 없이 두 값만 얻는 경량 경로를 따로 둘 것. 그리고 `:1172-1177`의
주석은 현재 사실과 다르므로 함께 고칠 것.

### L10 [MEDIUM] PHY 수치에 회귀 테스트가 없다

`tests/`에 `test_communications.py`가 없다. `grep`으로 확인한 결과 `Communications`를 언급하는
테스트는 `test_tier2_boundaries.py`(`:63,87,92`, `judge_uplink`의 단조성만 확인),
`test_dummy_verification.py`, `test_dynamics_predictor.py` 세 곳뿐이고, `path_loss_db`,
`noise_floor_dbm`, `frame_airtime_s`, `sensitivity_dbm`, `rayleigh_success_prob`의 **수치를
폐형식과 대조해 고정하는 테스트가 하나도 없다.** 이 상수들이 논문에서 "튜닝이 아니라 표준에서
유도했다"고 방어할 근거 전체인데, 누가 `PL_EXP`나 `OPERATING_RATE_MBPS`를 건드리면 아무도 모른다.
`Conversation.md` §5가 이미 "커버리지 공백 — 관측 벡터의 차원이 상수 0인 것을 잡는 테스트가 없음"을
같은 종류의 문제로 기록한 바 있다.

내가 이번에 직접 재계산해 확인한 값은 다음과 같다. 1 m 기준 자유공간손실 47.8588 dB,
10 MHz 잡음바닥 −95.0 dBm, 6 Mbps 감도 −85.0 dBm, 300 B 프레임 에어타임 448.0 µs,
취약구간 겹침확률 0.896 %, `SINR_TH_DB` = 10.0 dB(하드코딩이 아니라 MCS 표에서 유도됨). 전부 코드와 일치했다.
링크버짓도 확인했다: 300 m에서 P_succ가 10 dBm 0.545 / 23 dBm 0.970으로, 설계가 의도한
"하한 전력은 실제로 위험하다"는 트레이드오프가 성립한다.

**코더 지시**: `tests/test_communications.py`를 신설해 위 여섯 수치를 상대오차 1e-6으로 고정하고,
`rayleigh_success_prob`을 간섭 0/1/2개 케이스에서 폐형식과 대조하는 테스트를 추가할 것.

### L11 [LOW] 스케일 상수가 매직 넘버로 남아 있다

`rl_interface.py`의 정규화 상수 중 셋이 시나리오에서 유도되지 않은 리터럴이다.
`:430` 위상 잔여시간을 60.0으로 나누는데 실제 최대 녹색 지속은 42 s이므로(`generated.net.xml`의
tlLogic: 42/3/42/3) 이 피처는 1.0에 닿지 않으며, 1.0은 오직 "다음 신호가 없어 `inf`가 클리핑된 경우"에만
나온다. 두 상황이 같은 값으로 뭉개진다. `:436` 활성 차량 수를 100.0으로 나누는데 실측 범위는
밀도 25에서 [0.22, 0.75]였다. `:305` `queue_max=20.0`은 실측에서 1.0까지 포화했다. `:304` `a_max=5.0`은
SUMO 기본 차량형의 가속 2.6 / 감속 4.5에 대해 피처 범위가 [−0.9, +0.52]에 그친다.
어느 것도 결과를 왜곡하지 않지만, 같은 파일이 `DELTA_MAX`·`V_LIMIT`·`RSU_RANGE`는 시나리오에서
유도하도록 공들여 만들어 놓은 것과 대비된다.

`heuristic_scheduler.py:35-41`도 `delta_min=0.1`, `delta_max=45.0`, `p_high=23.0`, `p_low=10.0`을
리터럴로 들고 있다. `rl_interface`가 "SINGLE SOURCE OF TRUTH"를 자처하는데(`:13-16`) 이 파일만
import하지 않는다.

`hot_swap_trainer.py:854`의 `self.target_rsu_pos = (1200.0, 10800.0)`은 RSU_RANGE가 800 m이던
시절의 좌표다. 현재 격자는 최대 4500 m까지만 뻗으므로 이 좌표는 망 밖이다. `reset()`이
`:1052-1059`에서 실측 최다 접촉 신호등으로 덮어쓰므로 정상 경로에서는 쓰이지 않지만
(실측 확인: N39 = (4050, 4050)), `:1023`의 XML 파싱이 예외를 던져 `rsu_nodes`가 비면
이 유령 좌표가 그대로 살아남아 모든 차량이 범위 밖으로 판정되고 빈 에피소드가 된다.

**코더 지시**: `heuristic_scheduler`가 `rl_interface`의 `DELTA_MIN`/`DELTA_MAX`/`P_MIN`/`P_MAX`를
import하도록 바꿀 것. `target_rsu_pos` 초기값은 `None`으로 두고 reset이 채우지 못하면 명시적으로
실패하게 할 것. 나머지 정규화 상수는 시나리오 유도로 바꾸거나, 그럴 근거가 없다면 왜 그 값인지
한 줄 주석을 달 것.

### L12 [LOW] `Communications.py`에 참조자가 사라진 상수가 남아 있다

`TX_POWER_LEVELS_DBM`(`:99`, docstring이 "backwards compatibility with src/aoi_env.py"라고 밝히는데
`src/aoi_env.py`는 이미 삭제됨), `MAX_FRAME_SIZE`(`:36`), `FRAG_LIMIT`(`:37`),
`STREAM_THRESHOLD`(`:38`)(셋 다 docstring이 "NetSim fragmentation... is preserved"라고 하는데
`src/NetSim.py`도 삭제됨), `REFRACTIVE_INDEX_FIBER`(`:29`), `FIBER_PROPAGATION_SPEED`(`:30`).
`src/` 전체와 `run_all.py`에서 외부 참조 0건을 확인했다. 실행에 영향은 없다.
특히 `TX_POWER_LEVELS_DBM = [20, 25, 30]`은 폐기된 전력 범위를 담고 있어, 누가 이것을 보고
행동 범위를 잘못 이해할 여지가 있다.

**코더 지시**: 여섯 상수를 삭제할 것. `C_LIGHT`는 `_PL_REF_DB` 계산에 쓰이므로 남길 것.

### L13 [LOW] `dynamics_predictor`의 무로그 예외 처리 — 이전 리포트 5번, 미해결

`dynamics_predictor.py:187-188`, `:203-204`, `:210-211`, `:312-313`, `:333-334`가 전부
로그 없이 안전한 기본값으로 폴백한다. 개별 차량의 일시적 조회 실패에는 적절한 방어이나,
TraCI 연결 자체가 열화되면 `n_queue`·`leader_*`·`time_to_switch`가 조용히 0/`inf`로 굳는다.
`extract_tls_features`의 최외곽 `except Exception: return default_res`(`:384-385`)는 특히
넓어서 어떤 내부 결함도 "신호 없음, 정지 아님, 큐 0"인 그럴듯한 딕셔너리로 바꿔 버린다.
`Conversation.md` §5가 이미 폴백이 결함을 정상으로 통과시킨 사례(mean_aoi 1.0 폴백, warmup 부족)를
두 건 기록했다.

**코더 지시**: 각 `except`에 `logging.debug`(개별 차량) 또는 `logging.warning`(최외곽) 한 줄씩
추가하고, 에피소드 단위로 폴백 횟수를 세어 `get_metrics()`에 넣을 것. 폴백률이 임계를 넘으면
에피소드를 실패로 표시할 수 있어야 한다.

### L14 [LOW] `ss.MAX_STEPS`에 스텝 수를 넣는데 rou.xml의 `end=`는 초 단위다

`hot_swap_trainer.py:930`이 `ss.MAX_STEPS = self.max_steps + self.warmup_steps + 100`으로
**스텝 수**를 넣고, `make_sumo_set.py:444`가 이 값을 `<flow ... end="{MAX_STEPS}"/>`의 **초**로 쓴다.
스텝 길이가 0.1 s이므로 10배 길게 잡히는 셈이라 현재는 무해하다(흐름이 에피소드보다 오래 지속된다).
다만 단위 혼동이며, 스텝 길이를 바꾸는 실험을 하면 방향이 뒤집혀 에피소드 중간에 차량 생성이
끊길 수 있다. 곁가지로 `generated.sumocfg`의 `<end value="360000"/>`는 초 단위 하드코딩이라
`MAX_STEPS`와 무관하게 항상 100시간이다.

**코더 지시**: `:930`을 `ss.MAX_STEPS = (self.max_steps + self.warmup_steps + 100) * self.step_length`로
바꾸고 `make_sumo_set.py`의 해당 변수명을 `FLOW_END_S` 등 단위가 드러나는 이름으로 바꿀 것.

---

## 이전 리포트 지적 사항의 처리 상태 (8건 전수 대조)

이전 판의 1번(`rsu_range` 하드코딩 300.0)은 **해소되었다.** `rl_interface.py:163-167`이
`make_sumo_set.RSU_RANGE`에서 파생시키고, `evaluate.py:44`와 `hot_swap_trainer.py:60`이 그것을
import한다. 2번(`MAX_SPEED` 사용처 없음)은 **해소되었다.** 상수가 제거되고
`make_sumo_set.py:46-50`에 왜 없앴는지가 기록되었다. 3번(`heuristic_scheduler` 주석과 실제값 불일치)은
**해소되었다.** `:146`과 `:159`가 "upper bound"/"lower bound"로 바뀌었다(다만 리터럴 자체는
L11에서 다시 지적한다). 4번(`noise_floor_mw`의 대역폭 역산)은 **해소되었다.**
`Communications.py:233-245`가 `SUBCHANNEL_BW_HZ`를 직접 쓰고 `num_subchannels`를 의도적으로
버린다고 명시한다. 6번(`src/model.py` 죽은 파일)과 7번(`src/NetSim.py` 고아 모듈)은
**해소되었다.** 두 파일 모두 `src/`에서 삭제되었고 `backup/`에 보존되어 있다.
5번(무로그 예외)은 **미해결**로 L13에 다시 올린다. 8번(`CalcP_GEN` 유도 근거)은 **미해결**이다.
`make_sumo_set.py:209-218`에 여전히 유도 과정이 없어 독립 재현 검증이 불가능하다.
결과를 왜곡한 증거는 없고 밀도 스윕에서 정성적으로 단조 증가하는 것은 확인되었으므로,
논문에 이 식을 실을 계획이라면 유도 한 문단을 주석으로 남기라는 지시만 반복한다.

---

## 확인했으나 결함이 아닌 것

관측 벡터의 데이터 누수는 심각한 것이 없다. 17차원 중 미래 위치, 보상 자체, 다른 차량의
사적 상태를 흘리는 차원은 없다. 피처 [1]~[4]와 [8]~[12]가 결정 시점에 SUMO에서 live로 읽히지만,
`hot_swap_trainer.py:1758-1760`이 결정을 요청하는 대상을 "standing grant가 없는 차량"으로
한정하고 그런 차량은 방금 갱신을 보냈거나 방금 진입한 차량이므로, RSU가 실제로 그 순간 보유한
정보와 일치한다. 예외는 `MAX_TX_RETRIES` 소진으로 갱신이 끝내 도달하지 못한 채 구간이 닫히는
경우인데, 이때 RSU는 받은 적 없는 운동학을 관측하게 된다. 실측 두 구성 모두에서
`tx_abandoned = 0`이었으므로 현재 발현되지 않으며, 질문 Q4로 처리 방침만 확인받고자 한다.
피처 [15] `n_queue`는 SUMO 실측이 아니라 RSU 장부 재구성(`_ledger_queue_count:1184-1224`)으로
계산되며, 신선도 가드와 "정지 차량은 적색이 유지되는 동안만 정지로 믿는다"는 순환 방지 조건까지
갖춰 잘 설계되어 있다.

17차원 전부 live임을 실제 SUMO 600스텝(31,202 관측)으로 재확인했다. 랜덤 정책 기준 고유값 수는
[0] 367, [1] 12309, [2] 12949, [3] 24605, [4] 26214, [5] 13039, [6] 13929, [7] 26600,
[8]~[10] 각 2, [11] 421, [12] 18588, [13] 52, [14] 6, [15] 17, [16] 7579이다. 죽은 차원은 없다.
다만 [14](CBR)는 고유값 6개에 표준편차 0.0010으로 "변하긴 하지만 신호가 없는" 상태이며(L2),
[13]은 100.0 분모 때문에 [0.22, 0.75]만 쓴다(L11).

행동 디코딩은 단일 정본이 지켜지고 있다. `ActionDecoder`가 Δ와 전력 범위를 소유하고
(`rl_interface.py:507-645`), `hot_swap_trainer.py:1325-1326`과 `hpo.py:398-399`가 리터럴 대신
`decoder.p_min`/`p_max`를 읽으며, `:1397-1404`에 범위 위반을 잡는 하드 assert가 있다.
Δ의 기하 매핑(`delta_from_unit:560-570`)과 그 역함수(`unit_from_delta:572-577`)가 서로
정확한 역이며, `decode_action`의 폴백도 기하 매핑으로 통일되어 있다. 실측 decoder 값은
Δ∈[0.1, 45.0], p∈[10.0, 23.0], 4채널로 설계와 일치한다. `DELTA_MAX=45.0`이 net.xml의
tlLogic(green 42 + yellow 3)에서 실제로 유도됨을 `get_sumo_max_red_phase_duration`의 동작과
XML 원문 양쪽으로 확인했다. 다만 `decode_action:627`의 `ch = int(round(raw_ch)) % num_channels`는
연속 출력을 넘기면 채널 분포가 균등하지 않게 되는데, 실사용 경로는 전부 이산 헤드가 인덱스를
직접 넘기므로 현재 발현되지 않는다.

`estimation_error`(`rl_interface.py:223-234`)와 `norm_sq_error`(`:237-251`)는 설계 D5와 일치한다.
`e²/(e²+e_ref²)` 형태는 클리핑 형태와 달리 어디서도 포화하지 않고 `e = E_REF`에서 정확히 0.5이며,
`E_REF`를 RSU 반경이 아니라 "1초 주행거리"로 잡은 이유가 주석에 정확히 기록되어 있다.
`refresh_scenario_constants()`(`:169-188`)가 `_init_sumo`에서 호출되고 그 직후 decoder와
vectorizer를 재생성하는 순서(`hot_swap_trainer.py:938-942`)도 옳다.

SUMO 시나리오의 좌표계도 정합한다. 격자는 0~4500 m, RSU_RANGE 300 m, EDGE_LENGTH 900 m
(= 300×2 + 300)로 커버 2/3 · 아웃티지 1/3 비율이 유지된다. 선택된 RSU는 실측에서 N39 = (4050, 4050)이었고
`network_max_x/y`는 4500으로 올바르게 파싱되었다. warmup 350스텝(35 s) 후 관측된 활성 차량 수는
밀도 25에서 22~64대로, 빈 에피소드는 아니다. `_SIGNATURE_EXACT_KEYS`에 `DENSITY`가 포함되어
밀도 스윕이 실제로 재생성을 유발하는 것도 확인했다.

---

## 질문

**Q1.** 혼잡 항을 어떻게 살릴 것인가. 현재 CBR의 실현 가능 최대치가 랜덤 정책에서 0.006,
극단 구성에서도 0.24라 `w3` 항이 사실상 죽어 있다(L2). 서브채널 4→1 축소, 페이로드/레이트 조정,
차량 밀도 상향, 아니면 `Norm(C_freq)`를 실현 최대치로 Min-Max 정규화 — 어느 쪽인가.
어느 선택이든 결과를 바꾸므로 임의로 정하지 않았다. 아울러 CBR을 `hpo.compute_composite_objective`와
`evaluate.agg_cols`에도 넣을 것인지 함께 결정해 주기 바란다.

**Q2.** 오차항만 구간 길이에 비례해 [0, 45]로 누적되고 나머지 세 항은 [0,1]에 갇히는 현재 구조가
의도인가(L5). 설계문 D2는 "오차항만 누적"을 명시하지만 `Conversation.md` §3은 "모든 항목을 [0,1]로
Min-Max 정규화"를 명시해 두 문서가 충돌한다. 오차항을 구간 길이로 나눠 평균 오차로 만들 것인지,
아니면 현 구조를 유지하고 논문에 SMDP 적분임을 명시할 것인지 확정이 필요하다.

**Q3.** Δ 상한 45 s의 근거를 유지할 것인가. `Conversation.md` §2는 이를 "차량이 물리적으로 정지해
있을 수 있는 최대 시간"이라 했으나, 실제 신호 주기는 90 s(42+3+42+3)이고 큐 뒤쪽 차량은 한 주기를
놓쳐 90 s 이상 정지할 수 있다. 실측에서도 `peak_aoi`가 45.1 s로 상한에 붙었다. 45 s를 유지할지,
아니면 한 주기(90 s)로 올릴지 결정이 필요하다.

**Q4.** `MAX_TX_RETRIES` 소진으로 갱신이 도달하지 못한 채 구간이 닫힌 차량에 대해, 다음 결정 시점의
관측을 무엇으로 채울 것인가. 현재는 live SUMO 값을 읽으므로 RSU가 받은 적 없는 정보를 보게 된다.
마지막 수신값으로 대체할 것인지 확인 바란다. 현재 발현 빈도는 0이다.

**Q5.** seed가 무엇을 랜덤화하는지 논문에 어떻게 쓸 것인가. 현재 도로망 생성 서명에 seed가 없어
같은 밀도면 모든 seed가 **같은 도로망**을 쓰고 seed는 SUMO 교통 난수만 바꾼다. 이것이 의도인지,
아니면 seed마다 도로망까지 다시 뽑을 것인지 확정이 필요하다(L4의 수정 방향과 연동된다).

**Q6.** 진단 과정에서 `src/sumo/generated.*.xml`과 `.sumo_gen_signature.json`이 재생성되었다.
서명이 어차피 불일치(MAX_STEPS 490 < 본훈련이 요구하는 2450)라 다음 실행에서 자동 재생성되므로
무해하다고 판단했다. 특정 파일셋을 고정 보존해야 하는 사정이 있으면 알려주기 바란다.
