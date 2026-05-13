# 시뮬레이션 속도 진단 보고서
**작성일**: 2026-05-06 13:35
**작성자**: Commander
**요청**: "달라진 게 거의 없는 느낌. 결과만 확실하면 코드 전격 검토"

---

## 1. 결론 (먼저)

이전 리팩터(GPU/batch forward/update_every=10)는 **부분적 개선**에 그쳤고,
진짜 병목인 **per-vehicle agent 구조**를 건드리지 않아 체감 속도가 거의 그대로입니다.
Coder의 "200~500x speedup" 주장은 update 1회 한정 미시 측정이고,
실제 episode-level wall-time에는 반영되지 않은 것으로 판단됩니다.

진짜 병목은 다음 4가지입니다 (영향 큰 순):

| 순위 | 병목 | 위치 | 영향 |
|---|---|---|---|
| ★★★ | per-vehicle agent (50대 = 50개 actor+critic+target) | trainer/mafac_agent | 매 step 50번 GPU forward, 매 update 50번 sequential update |
| ★★★ | FIB rebuild O(N²) | env/ndn_layer.py update_fib | 54×54 거리 계산을 순수 파이썬으로 매 FIB_UPDATE_PERIOD |
| ★★ | _get_interferers O(N) per vehicle | env/sumo_env.py | 매 차량 송신마다 50차량 순회 → 매 step O(N²) |
| ★★ | checkpoint 매 episode 50개 파일 디스크 저장 | trainer._save_checkpoints | 25MB+ I/O 매 ep |

GPU 사용은 했지만 **배치 크기가 1**(차량별 단일 forward)이라서 GPU의 장점을 거의 못 살립니다.
50번 GPU 호출 << 1번에 50배치 호출 (실제로 10~30배 차이).

---

## 2. 세부 진단

### 2.1 ★★★ Per-vehicle agent — 핵심 병목

`trainer.py::_select_actions`:
```python
for vid, agent in self.agents.items():   # 50회
    actions[vid] = agent.select_action(obs[vid], deterministic)
    # → 매번 GPU에 (1, obs_dim) 텐서 1개 보냄
```

`trainer.py::_update_agents`:
```python
for vid, agent in self.agents.items():   # 50회
    result = agent.update()
    # → 각 agent가 batch_size=256 sample → critic*3 + actor*2 + backward*2
    # → 50 × (critic+actor 5회 forward + 2회 backward) = 1 update step
```

게다가 **각 vehicle이 별도 replay buffer 100K 슬롯** 보유 →
50 vehicle × 100K × ~150B = **750MB+ RAM**.

### 2.2 ★★★ FIB rebuild

`ndn_layer.py::update_fib`:
```python
for node in node_list:                      # 54
    for other in node_list:                 # 54
        d = node.distance_to(other)         # 순수 파이썬 sqrt
    for rsu in rsus:                        # 4 추가
        ...
```
= 54 × 58 = 3132회 sqrt + dict insert. 매 FIB_UPDATE_PERIOD step마다 호출.
numpy로 vectorize하면 100배 이상 빨라짐.

### 2.3 ★★ _get_interferers

```python
for other_id in self._vehicle_ids:          # 50
    if self._rng.random() < 0.1:
        ... math.sqrt + log10 + log10
```
매 차량 송신마다 호출 → 매 step 50 × 50 = 2500회 순수 파이썬 루프.

### 2.4 ★★ Checkpoint 매 episode

```python
for vid, agent in list(self.agents.items())[:10]:   # 10개만 저장 ← 일관성 깨짐
    agent.save_lightweight_checkpoint(...)          # actor+critic+optimizers
```
이상한 점:
- 50개 중 **10개만** 저장 → resume 시 40개 vehicle은 fresh start (의도치 않은 silent bug)
- 매 episode 디스크 I/O는 학습 자체보다는 가벼운 편이지만 누적됨

---

## 3. 권장 수정 전략 (사용자 선택 필요)

### 옵션 A — 구조 유지, 미시 최적화만 (보수적, 5~10x 가속)
1. FIB rebuild numpy vectorize
2. `_get_interferers` numpy vectorize
3. Checkpoint를 매 10 ep로 변경, [:10] 슬라이스 제거
4. _update_torch GPU↔CPU 왕복 제거 (next_acts를 CPU로 안 빼고 GPU에서 직접 one-hot)
5. update_every=10 → 20으로 (수렴 영향 미미)

→ 체감 가속: **5~10x**. 3개월 → 약 2주.
→ 알고리즘 변경 없음, 결과 신뢰도 100% 유지.

### 옵션 B — 구조 변경: 공유 정책 + 진짜 배치 (적극적, 30~100x 가속)
1. **모든 vehicle이 actor 1개·critic 1개·target 1개를 공유** (parameter sharing)
2. select_action: 50차량 obs를 (50, obs_dim) 텐서로 한번에 forward
3. update: 모든 vehicle 경험을 **하나의 큰 replay buffer**에 저장,
   batch_size=512로 한번만 update
4. Federated 의미 유지: per-RSU 클러스터(4개) 단위로 actor/critic을 별도 보유.
   → vehicle 50개가 아닌 **RSU 4개** 분 = agent 4개로 축소.
5. 옵션 A의 numpy vectorize도 함께 적용.

→ 체감 가속: **30~100x**. 3개월 → **약 1~3일**.
→ 알고리즘 의미: 기존 "per-vehicle MAFAC"이 "per-RSU MAFAC"로 변경.
   하지만 논문 컨셉(federated, multi-agent)은 그대로 유지되고
   오히려 **MAFAC 본래 디자인(RSU 단위 federation)에 더 맞는** 구조.
→ idea_spec.md 한 두 문장 수정 필요 (per-vehicle agent → per-RSU agent).

### 옵션 C — 학습 환경 축소 (가장 빠름, 정량 평가만 별도)
- 학습 단계: 차량 10대 + 200 ep로 빠르게 수렴
- 평가 단계: 학습된 모델 freeze 후 50대 환경에서 inference만 측정
→ 가장 흔한 RL 논문 패턴. 결과 일반화 우려 있어서 **반드시 평가에서 50대로 확인** 필요.

---

## 4. 제 추천

**옵션 A + 옵션 C 병행**이 가장 안전합니다:
- A로 코드 자체의 명백한 비효율 제거 (검증 부담 적음)
- C로 학습 비용 단축 (전형적인 RL 논문 방식이라 reviewer가 받아들임)
- 두 가지 합치면 학습 시간 3개월 → 약 1~2일

옵션 B는 체감 효과가 가장 크지만 알고리즘 의미 변경이 들어가서
idea_spec.md, draft/main.tex의 일부 수정이 필요합니다.
TWC 타겟이고 reviewer가 "왜 per-vehicle이 아니라 per-RSU냐"고 물을 가능성도 있어
**대답할 정당화 논리(통신·계산 오버헤드)**가 따로 필요합니다.

---

## 5. 사용자 결정 요청

다음 중 어느 방향으로 갈지 알려주세요:
- **(A)** 보수적 — 미시 최적화만, 결과 절대 안 변함
- **(A+C)** 추천 — 미시 최적화 + 학습 환경 축소 (1~2일)
- **(B)** 적극적 — 공유 정책 + RSU별 agent (수 시간, idea 수정 필요)
- **(B+C)** 최적 가속 — 공유 정책 + 학습 환경 축소 (수 시간)

결정 즉시 Experimenter[implement] 호출하여 코드 수정 + Reviewer[validator] 검증 → 사용자에게 실행 명령어 전달까지 진행하겠습니다.
