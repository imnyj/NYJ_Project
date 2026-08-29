## User Response

## D1
>> hot_swap_trainer.AoiV2IEnv.py에 Δ 이식 하기.

## D2
>> 정지 상태 시, AoI 갱신 안 한 것에 보상을 주는 것의 문제라면, 이동 상태 시, AoI 갱신을 안 한 것에는 패널티를 주어 Δ를 무조건 늘리느 것을 방지하는 것은 어떤지?

## D3
>> (가) 방식으로 활용. 장부가 낡을 수 있으니, AoI가 너무 큰 정보는 사용하지 않도록 하는 것도 괜찮지 않을까? 아니면, 차량의 상태를 같이 저장하여 정지 상태면 AoI가 커도 쓰고, 차량이 정지 상태가 아니면 안 쓰는 것은 어때?

## D4
>> 정지선 거리는 앞에 차량이 몇대나 있는지와 신호등 신호가 변경될 때까지의 남은 시간과 관계가 없다고 생각한다. 정확히는 정지선 거리보다는 RSU와의 거리를 계산하여 RSSI 등의 통신 특성을 반영해야 한다고 생각한다.

## D5
>> 혹시 RSU의 통신 반경인 800m로 하면 optuna로 인한 조정에서 weight가 커져서 자동으로 수치가 맞춰지지 않을까?

## D6
>> 후자로 결정.

## D7
>> (가)로 운용.

## D8
>> 나는 Peak라는 값을 최대로 해석하고 있어.

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