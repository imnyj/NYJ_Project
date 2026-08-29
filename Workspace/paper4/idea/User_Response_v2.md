## User Response 2

## D3
  n_queue | RSU 장부 기반 + **신선도 가드**(신선하거나, 정지 상태이고 그 신호가 아직 적색일 때만 사용) | 확정, $\tau_{fresh}$ 초안 1.0 s 승인 대기 |
>> OK.


## D4
  stop_imminent(15) | [15] 제거, [7]·[11]·[12] 유지로 해석 | **해석 확인 필요** |
>> OK.

## D5
  오차 정규화 | $e_{max}=800$ m는 Optuna로 보정 불가(전력항의 1/130) → 대안 3안 제시 | **재결정 필요** |
>> 법적 최대 규정 속도 60km/h = 16.667 m/s 라고 하여 1초에 해당 하는 16.667m를 정규화 값으로 사용하는 건 어때?


## D6
  I_redundant | "예측이 맞았으면 중복" $\mathbb{I}=\mathbb{1}[e \le \epsilon]$, 판정을 simulationStep 이후로 | 확정, $\epsilon$ 초안 3.2 m 승인 대기 |
>> OK

## D7 
  전송 실패 | 즉시 재시도(같은 결정의 연장, 모델 재호출 없음), 실측 Δ 기록 | 확정, 연속실패 상한 초안 10회 승인 대기 |
>> OK

## 사용자 의견
Env 이용 방식과 직접 환경 구현 방식이 있는데, 다중 차량의 state 시기에 비해 next state 시기가 너무 불규칙적이어서 Env 방식은 힘들 것 같아. 시간이 걸리더라도 직접 구현 방식으로 가자.

* Env 구현 방식
env = Env(파라미터)
model.learn(env)

Env(파라미터):
    def __init__():

    def __reset__():

    def __step__():

* 직접 구현 방식
model = RL()

for step to max_step:
    시나리오

    if(v_id가 갱신)
        if(rsu 진입이면 첫 갱신)
            batch[v_id] = {state, ...}
            next_update = model[rsu_id].predict(state)

        if(batch == full)
            학습