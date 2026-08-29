# 시뮬레이션 실행 계획 (rev.3, 2026-08-28 22시 Claude Code 검증)

> [!CAUTION]
> **훈련 착수 금지 (2026-08-28 22:20 기준).** rev.2가 "훈련 시작 가능"이라 판정했으나, 독립 검증에서
> 논문의 핵심 결정변수 **Δ(갱신 타이밍)가 환경에 전혀 반영되지 않음**을 실측으로 확인했다.
> 동일 시드에서 Δ=0.1s와 Δ=45.0s가 tx_attempts·tx_fails·CBR·오차까지 **완전히 동일**하다.
> 추가로 AoI가 `max(1.0, ·)` 클램프로 상수 포화(실제 age 평균 0.0437s, 98.8%가 잘림)되어
> 보상의 70.6%가 아티팩트이며, I_redundant는 호출 순서 문제로 사실상 발화하지 않는다.
> 더 나아가 **리플레이 버퍼에 들어가는 보상은 승인된 4항 보상이 아니라** 스케줄러 내부의 3항 보상이며,
> 그중 오차항과 dt가 상수로 죽어 실질 학습 신호가 `−(0.01 + 0.01·전력)` 뿐이다.
> 또한 **모델이 보는 상태 18차원 중 15개가 상수**다(신호등·거리·CBR·heading 전부 미전달).
> 상세·증거·수정 순서: **`review/claude_audit_20260828.md`**
>
> 사용자 지시(2026-08-28): 비교 방안(베이스라인) 학습은 **보류**. 데이터 확보는 결함 수정 이후.
> 사용자 결정(2026-08-28 22시): 코드 수정 전에 **설계부터 재논의**. Δ 게이팅은 **순수 SMDP** 방식으로 확정.
> 재설계 명세: **`idea/design_spec_v2.md`** (8절에 D1~D8 결정 현황).
> 2026-08-29: 사용자 답변(`idea/User_Response.md`) 반영 — D1·D2·D6·D7·D8 및 루프 구조 확정,
> D4(해석 확인)·D5(오차 정규화 재결정) 2건 미결. 응답·반론: **`idea/Claude_Response.md`**.

> rev.1(agy 작성)의 결함 4건을 수정한 판이다. 변경 이력은 문서 하단 참조.
> 원본은 `backup/simulation_plan.md.agy.*`에 보존.

## 1. 실행 전 필수 조치 (완료)

| # | 조치 | 상태 |
|---|---|---|
| 1 | 스모크 테스트 체크포인트 격리 (31개 + `test_challenger/`) | 완료 → `backup/checkpoints_presmoke_20260828_155837/` |
| 2 | 스모크 훈련 로그 CSV 격리 (12개) | 완료 → `backup/training_logs_presmoke_20260828_155837/` |
| 3 | SUMO 파일 생성에 프로세스 간 배타 락 추가 | 완료 → `make_sumo_set.py::_generation_lock` |
| 4 | 테스트의 전역 오염 수정 (`RSU_RANGE=800` 미복구) | 완료 → `tests/test_dynamics_predictor.py` try/finally |

`checkpoints/`와 `logs/training/`은 현재 비어 있다. 이 상태에서 시작해야 seed 42 기준 재현이 성립한다.

## 2. 워크스테이션

| 리소스 | 사양 |
|---|---|
| CPU | Intel i9-10900X, 20 threads @ 3.70GHz |
| RAM | 125 GiB (100 GiB 여유) |
| GPU | RTX 3090 × 4 (각 24GB) |
| Disk | 163 GB 여유 |

libsumo 인스턴스 하나가 CPU 코어 1개를 점유하므로, GPU 4장 기준 4개 프로세스 동시 실행이 상한이다.

## 3. 실측 처리량과 소요 시간

2에피소드 × 300스텝 실측에서 도출. **200,000 스텝 기준 예상:**

| 모델 | 처리량 | 예상 소요 |
|---|---|---|
| I-HAMAPPO | 42.2 steps/s | 79.0 min |
| SAC | 44.7 | 74.6 |
| RES-MAPDDPG | 51.2 | 65.1 |
| PPO | 56.0 | 59.5 |
| TD3 | 59.8 | 55.7 |
| CARLTON | 60.2 | 55.4 |
| MA2HDQN | 61.7 | 54.0 |
| MADDPG-MT | 70.3 | 47.4 |
| SPAM-D3QN | 76.4 | 43.6 |
| **합계** | | **534 min (8.9 h)** |

> [!NOTE]
> 이 처리량은 에피소드당 300스텝 측정치라 SUMO 재기동·웜업 오버헤드가 상대적으로 크게 반영되어 있다. 실제 2000스텝/에피소드에서는 고정 오버헤드가 6.7배 넓게 분산되므로 **실제 처리량은 이보다 높고 소요는 짧을 가능성이 크다.** 아래 예상 시간은 보수적 상한으로 읽을 것.

## 4. 그룹 배정 (부하 균형 재계산)

rev.1은 Basic 3종을 한 GPU에 몰아 그룹 A가 190분 병목이 되고 나머지 3장이 합계 225분 유휴했다. 느린 모델(I-HAMAPPO, SAC)을 분산하여 재배정한다.

| 그룹 | 담당 | GPU | CPU 핀 | 모델 | 예상 |
|---|---|---|---|---|---|
| A | **Antigravity** | 0 | 0-4 | I-HAMAPPO, PPO | 138.5 min |
| B | **Antigravity** | 1 | 5-9 | SAC, CARLTON | 129.9 min |
| C | **Claude** | 2 | 10-14 | RES-MAPDDPG, TD3 | 120.8 min |
| D | **Claude** | 3 | 15-19 | SPAM-D3QN, MADDPG-MT, MA2HDQN | 145.1 min |

**완료 예상 2.42 h** (rev.1 대비 3.16 h → 2.42 h, 유휴 225분 → 46분).

느린 두 모델(I-HAMAPPO 79분, SAC 75분)을 서로 다른 GPU로 분리하고, 빠른 세 모델을 그룹 D에 모아 균형을 맞췄다. 담당 구분은 rev.1과 같이 A·B가 Antigravity, C·D가 Claude다.

### GPU 하드웨어 격리에 대한 주의

`hot_swap_trainer`는 GPU가 2장 이상 보이면 Act 모델을 `cuda:0`, Rest 모델을 `cuda:1`에 올려 **학습이 추론 지연에 영향을 주지 않도록 하드웨어를 분리**한다(`_select_devices`, `hot_swap_trainer.py:92-107`). 그런데 위 계획처럼 그룹마다 `CUDA_VISIBLE_DEVICES`로 GPU를 1장만 노출하면 가시 장치가 1개이므로 Act와 Rest가 **같은 GPU를 공유**한다. 실측으로 확인했다:

```
CUDA_VISIBLE_DEVICES=3 -> visible GPUs: 1, act_device: cuda:0, rest_device: cuda:0
```

크래시하지는 않으므로 훈련 수렴에는 문제가 없다. 다만 `idea/scenario.md`가 명시한 "학습 리소스가 추론 리소스에 영향이 가지 않도록" 이라는 설계 요구는 이 구성에서 **검증되지 않는다.** 따라서:

**측정 결과 (2026-08-28, TD3 600스텝, `etc/scripts/measure_hw_feasibility.py`)**: 공유해도 사실상 손해가 없다.

| 지표 | GPU 2장 분리 | GPU 1장 공유 | 차이 |
|---|---|---|---|
| 평균 지연 | 1.2097 ms | 1.2320 ms | +0.022 ms (+1.8%) |
| p50 | 1.0789 ms | 1.1209 ms | +0.042 ms |
| p95 | 1.7016 ms | 1.7280 ms | +0.026 ms |
| p99 | 2.9801 ms | 2.5447 ms | **-0.435 ms** |
| 처리량 | 21.18 steps/s | 21.10 steps/s | -0.4% |

메모리도 비쟁점이다. 최대 모델 TD3가 2.96 MB이므로 Act+Rest 2벌이 5.91 MB, RTX 3090 24GB의 **0.024%**에 불과하다. 모델이 작아 GPU가 포화되지 않으며, 핫스왑 시 장치 간 파라미터 복사 비용이 오히려 연산 경합보다 커서 p99는 공유 쪽이 낫게 나왔다.

**결론**: 4그룹 × GPU 1장 구성을 그대로 쓴다. 나아가 **논문에서도 단일 GPU 구성을 주장으로 삼는 것이 유리하다** — 실제 RSU에 GPU 4장이 달릴 리 없으므로, 단일 가속기에서 Act/Rest를 함께 운용하며 추론 지연 1.2 ms를 유지한다는 편이 훨씬 설득력 있는 HW feasibility 근거다. 측정 원본은 `results/hw_feasibility.json`.

## 5. 실행 절차

### 5-1. SUMO 파일 사전 생성 (필수, 단독 실행)

4개 그룹이 동시에 기동하면 전부 캐시 미스로 생성을 시도한다. 락이 있어 손상되지는 않으나 3개가 대기하므로, 먼저 한 번 생성해 캐시를 채운다.

```bash
cd /home/imnyj/Workspace/paper4/coder
/home/imnyj/venv/bin/python -c "
import sys; sys.path.insert(0,'.')
import src.sumo.make_sumo_set as ss
ss.DENSITY = 25.0
ss.NUM_BLOCKS = 5
ss.MAX_STEPS = 2000 + 35 + 100
ss.make_sumo_files()
print('SUMO cache warmed:', ss.generation_signature_matches())
"
```

### 5-2. 4그룹 병렬 기동

`--no-resume`가 **모든 명령에 필수**다. 빠뜨리면 체크포인트에서 재개를 시도한다.

```bash
cd /home/imnyj/Workspace/paper4/coder
mkdir -p logs

# 그룹 A (GPU 0, CPU 0-4)
setsid nohup taskset -c 0-4 env CUDA_VISIBLE_DEVICES=0 \
  /home/imnyj/venv/bin/python run_all.py \
  --models I-HAMAPPO PPO --seed 42 --no-resume \
  > logs/training_groupA.log 2>&1 < /dev/null &

# 그룹 B (GPU 1, CPU 5-9)
setsid nohup taskset -c 5-9 env CUDA_VISIBLE_DEVICES=1 \
  /home/imnyj/venv/bin/python run_all.py \
  --models SAC CARLTON --seed 42 --no-resume \
  > logs/training_groupB.log 2>&1 < /dev/null &

# 그룹 C (GPU 2, CPU 10-14)
setsid nohup taskset -c 10-14 env CUDA_VISIBLE_DEVICES=2 \
  /home/imnyj/venv/bin/python run_all.py \
  --models RES-MAPDDPG TD3 --seed 42 --no-resume \
  > logs/training_groupC.log 2>&1 < /dev/null &

# 그룹 D (GPU 3, CPU 15-19)
setsid nohup taskset -c 15-19 env CUDA_VISIBLE_DEVICES=3 \
  /home/imnyj/venv/bin/python run_all.py \
  --models SPAM-D3QN MADDPG-MT MA2HDQN --seed 42 --no-resume \
  > logs/training_groupD.log 2>&1 < /dev/null &
```

### 5-3. 기동 직후 5분 내 확인 (중요)

로그가 초록불이어도 실제로는 빈 실행일 수 있다. 실제 검증한 사례가 있으므로 반드시 아래를 확인한다.

```bash
cd /home/imnyj/Workspace/paper4/coder
for g in A B C D; do echo "--- group $g ---"; tail -3 logs/training_group$g.log; done
# 에피소드 1개가 끝나면 CSV에 행이 생긴다. tx_attempts 와 mean_reward 를 볼 것.
head -2 logs/training/*_progress.csv | cut -d, -f1,2,3,17,18
```

**정상 판정 기준**: `mean_reward`가 음수(보상 수식상 R≤0), `tx_attempts` > 0, `training_steps` > 0.
`mean_reward=0.0` / `tx_attempts=0`이면 빈 실행이므로 즉시 중단하고 원인을 찾는다.

### 5-4. 사전 점검 결과 (2026-08-28 16:14 실측)

위 명령 형태 그대로 그룹 A·B를 1에피소드 × 200스텝으로 **동시 기동**하여 검증했다.

| 모델 | 보상 | tx_attempts | tx_fails |
|---|---|---|---|
| I-HAMAPPO | -0.4314 | 305 | 151 |
| PPO | -0.4355 | 305 | 162 |
| SAC | -0.4291 | 305 | 167 |
| CARLTON | -0.4119 | 305 | 171 |

`setsid` + `taskset` + `CUDA_VISIBLE_DEVICES` + `--no-resume` 조합이 정상 동작하고, 두 프로세스가 동시에 SUMO를 사용해도 7개 생성 파일이 전부 온전했다(락 동작 확인). 사전 점검 산출물은 `backup/preflight_*`로 격리했으므로 현재 `checkpoints/`와 `logs/training/`은 비어 있다.

## 6. 모니터링

```bash
tail -f logs/training_groupA.log                       # 그룹별 진행
tensorboard --logdir logs/tensorboard/ --port 6006     # 학습 곡선 (5만 step 부근 수렴 확인용)
nvidia-smi -l 10                                       # GPU 4장 부하 균형
ls -la checkpoints/ | tail                             # 에피소드 10마다 체크포인트
```

중단 시 재개는 `--no-resume`를 빼고 같은 명령을 다시 실행하면 된다. `run_hot_swap_training`이 최신 `{model}_ep*.pt`를 찾아 그 다음 에피소드부터 이어간다.

## 7. 훈련 후 다음 단계

1. **Optuna HPO** — `src/hpo.py`. 탐색 공간에 보상 가중치 w1~w4가 포함되어 있다.
2. **벤치마크 평가** — `src/evaluate.py`. 5개 밀도(15~55 veh/km) × 5개 시드.
   > [!WARNING]
   > 밀도 스윕은 에피소드마다 SUMO를 다른 밀도로 재생성한다. 훈련과 **동시에 돌리면 안 된다.** 락이 손상은 막지만 서로의 네트워크를 계속 재생성해 양쪽이 느려진다.
3. **논문 결과 반영** — `writer/main.tex`의 결과 섹션은 현재 비어 있고, 참고문헌은 폐기된 옛 목록이라 `librarian/baselines_v2.md`로 교체해야 한다.

## 8. 미해결 결정 사항

**데이터레이트 6 Mbps가 현재 모델에 반영되어 있지 않다.** `Communications.py:56`의 `min_rate = 6.0`은 레거시 802.11ac 채널 매니저의 바닥값이고, AoI 경로(`hot_swap_trainer.py`)는 `judge_uplink`의 SINR 성공확률만 사용하며 **채널 점유 시간 개념이 없다**. 두 갈래 중 선택이 필요하다.

- **(a) 에어타임 모델 추가** — 패킷 크기 ÷ 6 Mbps로 전송 시간을 계산해 서브채널을 점유시킨다. Δ와 혼잡이 실제로 결합되어 논문의 혼잡 서사가 단단해진다. 구현 후 재훈련 필요.
- **(b) 현 모델 유지** — 논문에 "확률적 충돌 모델이며 에어타임은 모델링하지 않는다"고 한계를 명시한다. 즉시 훈련 시작 가능.

**사용자 결정: (a) 에어타임 모델 구현.** 2026-08-28 착수. 거리·전력·열잡음이 모두 반영된 정교한 PHY로 재구성한다.

확정 파라미터 (전부 IEEE 802.11p 5.9 GHz 규격에서 유도):

| 항목 | 값 | 근거 |
|---|---|---|
| 서브채널 대역폭 | 10 MHz × 4 = 40 MHz | 802.11p 표준 채널폭, 미국 5.9 GHz ITS 할당 내 |
| 잡음바닥 | −95.0 dBm | −174 + 10log₁₀(10⁷) + NF 9 dB |
| 데이터레이트 | 6 Mbps (QPSK 1/2) | 802.11p 기본 레이트, 가장 견고 |
| 필요 SINR | 10 dB | 규격 수신감도 −85 dBm 대비 잡음바닥 −95 dBm |
| 안테나 이득 | 차량 3 dBi, RSU 9 dBi | **현재 모델에 누락된 항목** |
| 프레임 에어타임 | 40 µs + 8 µs × N_sym | 심볼 8 µs, 6 Mbps(QPSK 1/2)에서 **48 bits/symbol**. 300바이트 → **448 µs** |
| 섀도잉 | 로그정규 σ = 4 dB | 도심 가로 환경, 시드 고정 |

안테나 이득 누락이 가장 큰 물리적 결함이었다. 반영 전후 300 m 성공확률:

| 300 m | 10 dBm | 15 dBm | 20 dBm | 23 dBm |
|---|---|---|---|---|
| 이득 미반영(기존) | 0.000 | 0.048 | 0.382 | 0.617 |
| **이득 반영(수정)** | **0.545** | 0.825 | 0.941 | **0.970** |

기존 모델은 10 dBm이 0에 붙어 액션 하한이 죽어 있었다. 이득을 넣어야 전력 축에 학습 가능한 기울기가 생긴다.

에어타임이 들어가면 서브채널 점유 시간에서 **실제 CBR**이 산출되어, Δ(갱신 주기)와 혼잡이 비로소 실제로 결합된다. 지금까지는 확률적 충돌만 있고 채널 점유 개념이 없었다.

### 구현 완료 (2026-08-28) 및 그 과정에서 발견·수정한 결함

**사양 정정**: 최초 사양의 "6 Mbps에서 24 bits/symbol, 300바이트 → 848 µs"는 **오류였다.** 802.11p는 802.11a를 10 MHz로 절반 스케일한 규격이라 심볼이 8 µs다. 24 bits/symbol은 24/8µs = **3 Mbps**(BPSK 1/2)이고, 6 Mbps(QPSK 1/2)는 48 bits/symbol → 300바이트 **448 µs**가 맞다. 802.11a의 N_DBPS를 802.11p에 잘못 대입한 것으로, 구현 에이전트가 지적하여 정정했다. `MCS_TABLE`이 모든 행에 `rate = bits_per_symbol / 8µs`를 강제하므로 재발하지 않는다.

**충돌 모델 전면 교체 (가장 중요)**: 에어타임을 넣자 기존 접근법의 오류가 드러났다. 환경은 한 스텝의 같은 서브채널 grant를 **전부 동시 전송으로 취급**해 상호 간섭을 물렸는데, 프레임은 448 µs이고 스텝은 100 ms다. 두 프레임이 실제로 겹칠 확률은 취약구간 기준 `2T/S = 0.90%`에 불과한데 100%로 계산한 셈이다. 그 결과 **CBR이 0.7%인데 패킷손실이 89.3%**라는 자기모순이 나왔다.

수정: 태그된 프레임 기준으로 다른 grant가 `2·T_air/T_step` 확률로만 간섭원이 되도록 하고, 뽑힌 부분집합만 `judge_uplink`에 넘긴다. Rayleigh SINR 물리는 손대지 않고 시간 겹침만 올바르게 모델링한 것이다(`hot_swap_trainer.py`, `comm.draw_overlap`).

| | 수정 전 | 수정 후 |
|---|---|---|
| 패킷손실 | 0.893 | **0.195** |
| 손실 성격 | 대부분 가짜 충돌 | 거리·전력에 따른 잡음 제한 |

남은 19.5%는 평균 송신전력 16.7 dBm에서 예상되는 값과 일치한다. 이제 전력을 올리면 손실이 줄고 전력 패널티를 무는 **실제 트레이드오프**가 성립한다. 실측 확인: MA2HDQN이 17.75 dBm으로 실패 774건, PPO가 15.20 dBm으로 903건.

**관측 벡터 전수 점검**: 죽은 피처가 세 번 반복(속도 X/Y·heading, CBR, n_active)되어 18개 차원을 한 번에 훑는 검사를 만들었다(`etc/scripts/verify_observation_liveness.py`). 그 결과 **네 번째**를 발견했다 — `accel`이 `"accel": 0.0`으로 하드코딩되어 있었다. `libsumo.vehicle.getAcceleration()`으로 교체했다. 현재 **18개 차원 전부 변화를 보인다.**

| 발견 시점 | 죽은 피처 | 원인 |
|---|---|---|
| 1차 | 속도 X, 속도 Y, heading | 위치 차분이 한 스텝 3회 호출로 2·3번째가 0 |
| 2차 | CBR | state dict에 키가 없어 기본값 폴백 |
| 3차 | n_active | 동일 (기본값 1 → 0.01 고정) |
| 4차 | accel | 리터럴 `0.0` 하드코딩 |

네 건 모두 **테스트 118개를 전부 통과한 상태에서** 살아 있었다. 정적 검사로는 잡히지 않으므로, 상태 벡터를 확장할 때마다 위 liveness 검사를 돌릴 것.

**결정성**: 환경 자체는 시드 고정 시 완전 재현된다(동일 시드 2회 → `tx=117, fail=22, cbr=0.000874` 동일). 다만 end-to-end 훈련은 비동기 Rest 학습 스레드의 타이밍 때문에 미세한 편차가 있다(보상 0.2% 수준). 이는 Act/Rest 핫스왑 구조에 내재된 것으로 이번 수정과 무관하다.

> [!CAUTION]
> ~~PHY 정교화가 완료되었으므로 위 4-그룹 병렬 훈련을 시작할 수 있다.~~
> **철회 (2026-08-28 22시).** PHY 자체는 재검증 결과 정확했으나(448 µs, −95 dBm, 이득 반영 전부 확인),
> 그 위층의 Δ 스케줄링이 아예 없어 훈련이 무의미하다. `review/claude_audit_20260828.md` 참조.

---

## 변경 이력 (rev.1 → rev.2)

| # | rev.1의 문제 | 조치 |
|---|---|---|
| 1 | 모든 명령에 `--no-resume` 누락. `run_all.py`는 `resume=True`가 기본값이고 스모크 체크포인트 31개가 남아 있어, 본훈련이 2에피소드짜리 seed 7 가중치에서 재개될 상태였다 | 체크포인트·로그 격리, 전 명령에 `--no-resume` 추가 |
| 2 | 4개 프로세스가 `src/sumo/`를 공유하는데 프로세스 간 락이 없었다. 파일 단위 원자적 쓰기는 있으나 7개 파일 집합의 상호 일관성은 보장되지 않았다 | `make_sumo_files()`를 배타 flock으로 감싸고, 기동 전 사전 생성 절차 추가 |
| 3 | 그룹 A에 Basic 3종을 몰아 190분 병목. 예상 2.7h는 과소평가(실제 3.16h)이고 GPU 3장이 225분 유휴 | 실측 처리량 기반 재배정, 2.42h / 유휴 46분 |
| 4 | 다이어그램은 CPU 코어 할당을 표시하나 명령어에 `taskset`이 없어 미적용 | 전 명령에 `taskset -c` 추가 |
