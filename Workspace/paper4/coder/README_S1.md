# S1 — AoI 스케줄링 환경 계층 (aoi_env.py)

설계 명세(`aoi_scheduling_design.md`)의 **S1(환경 계층)** 구현·검증본입니다.

## 배치

`code/src/aoi_env.py` 로 두고, `code/`를 CWD로 실행합니다. (`NetSim.py`, `Communications.py`, `src/sumo/` 재사용. SUMO·`SUMO_HOME` 필요.)

## 무엇을 구현했나

- **이벤트 (E1/E2/E3)**: 차량이 타깃 RSU 셀에 진입(E1)하면 등록, 예정 시점마다 상태 갱신(E2), 셀 이탈/소멸 시 종료(E3). `update_dwell`(매 스텝 훅) 위에 얹음.
- **RSU의 `(x̂, τ)` 유지 + 등속 외삽**: RSU는 각 차량의 마지막 수신 상태(pos·vel·time)를 보유하고 `x̂(t)=pos+vel·(t−τ)`로 외삽.
- **사후 소급 오차**: 매 스텝 실제 위치(SUMO)와 외삽치의 오차 `e_i`를 적분하고, 다음 갱신(E2)이 오면 그 구간 오차를 소급 확정.
- **단일 셀**: 설계대로 RSU 하나만 활성. 타깃은 **웜업 동안 트래픽이 가장 많은 RSU**로 선택(자원경합에 붐비는 셀이 필요).
- **placeholder 스케줄러** `decide_grant()`: 지금은 고정 간격(S1). S3/S4에서 RL 에이전트의 grant `(Δ, ch, p)`로 교체.
- **순수 함수 분리**: `extrapolate()`, `estimation_error()` 는 SUMO 없이 단위테스트 가능.

## 검증 결과 (실제 SUMO 1.27.1)

- **오차 수학 단위테스트**: 정지/등속=오차 0, 등가속=`0.5·a·t²`, 회전=오차 성장. → "유효 AoI" 핵심 로직 확인.
- **SUMO 런(단일 셀 N7, density 25)**: E1=150, E2=9077, E3=7 정상. **저속(<2m/s) 평균오차 0.18 vs 고속 0.75** → 정지/저속 차량은 갱신 안 해도 오차 작음(유효 AoI 전제 실측 확인).

## 실행법

```python
import random
import src.NetSim as net, src.sumo.make_sumo_set as ss, src.aoi_env as env
ss.RSU_RANGE=800.0; ss.AV_SPEED=45.0; ss.DENSITY=25.0; ss.MAX_STEPS=160.0
ss.SPEED=ss.AV_SPEED/3.6; ss.P_GEN=(ss.DENSITY*ss.SPEED)/3600.0
net.MAX_EPISODE=1; net.b_step_log=False; net.b_reroute=False
random.seed(5); env.WARMUP_S=25.0; env.reset_env()
sim=net.SumoNetSim(VehicleClass=env.VehicleNode, RSUClass=env.RSUNode,
                   start_message_fn=env.start_message)
sim.run()
print(env.METRICS.summary())
```

`env.reset_env()`를 매 에피소드 전에 호출하세요(타깃·트랙·지표 초기화).

## 주의 (make_sumo_set 관련 gotcha)

`make_sumo_set.py`의 `step`·`GRID_SIZE`·`EDGE_LENGTH`는 **import 시점에 기본값으로 한 번만 계산**됩니다. import 후 `ss.OUTAGE_ZONE`·`ss.RSU_RANGE`·`ss.NUM_BLOCKS`를 바꿔도 **격자 geometry는 안 바뀝니다**(간격 2400 고정). geometry를 실제로 바꾸려면 해당 파생값을 재계산해야 합니다. S1은 기본 geometry(RSU 25개, 간격 2400)를 그대로 사용합니다.

## 다음 단계 (S2)

`Communications.py`에 `C`개 서브채널을 두고, grant `(Δ, ch, p)`의 동일 서브채널·중첩 전송에 대해 **SINR 확률 성공판정**을 붙입니다. E2의 "상태 전송"이 지금은 직접 호출인데, S2에서 이 SINR 판정을 거치도록 교체합니다.
