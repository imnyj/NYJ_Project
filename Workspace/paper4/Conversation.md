## 사용자와의 소통 창구 (설계안)

이전에 에이전트가 저지른 가짜 환경(Mocking) 꼼수를 전면 폐기하고, `/grill-me` 인터뷰를 통해 도출된 진짜 연구 파이프라인 설계안을 정리합니다. 이 내용은 향후 Claude 등 다른 에이전트와의 교차 검증 시 신뢰할 수 있는 기준(Ground Truth)이 됩니다.

### [x] 1. 설계된 State 변수들 나열 및 설명
- $v_{pos}$ (위치) 및 $d_{rsu}$ (RSU와의 거리): 차량 좌표로부터 RSU와의 직선거리를 즉시 계산. RSSI 등 통신 성공률에 직접적인 영향을 미치는 핵심 지표.
- $v_{heading}$ (방향): 차량이 교차로(RSU)를 향해 접근 중인지, 통과 후 멀어지는지 여부 (차량 자체 정보로 수집 비용 낮음).
- $v_{vel}$ (속도): 차량의 현재 속도 벡터.
- $tls_{state}$ (신호등 상태) & $tls_{dist}$ (정지선 거리): 해당 차선의 신호등 상태(R/Y/G) 및 정지선까지의 거리.
- $n_{queue}$ (동일 차선 큐 길이): 전방 대기 차량 수 (직접적인 지연 요인).
- $n_{active}$ (통신 범위 내 차량 수): RSU Table 내 활성 차량 수 집계. 전체 망 혼잡도 및 서브채널 경쟁(Slot contention) 수준을 나타내는 지표.
- $info_{others}$ (타 차량 맥락 정보): RSU Table에 갱신되어 있는 주변 차량 과거 데이터 (V2I 통신 낭비 없이 재활용).

### [x] 2. 설계된 Action 구조 (승인)
- **하이브리드 액션 공간 (Hybrid Action Space)**
  - $\Delta$ (갱신 타이밍): 연속 변수, **[0.1s, 45.0s]** 범위. 선형이 아닌 **기하(로그) 매핑** $\Delta = \Delta_{min}(\Delta_{max}/\Delta_{min})^{u},\ u \in [0,1]$ 을 사용한다.
  - $p$ (전송 전력): 연속 변수, [10dBm, 23dBm] 범위로 스케일링 제한.
  - $ch$ (서브 채널): 이산(Discrete) 변수, Categorical 선택.

**※ 범위 확정 근거 (2026-08-27 갱신, 기존 상한 5.0s에서 변경)**
- $\Delta$ 하한 0.1s: ETSI EN 302 637-2의 CAM 최소 생성 주기.
- $\Delta$ 상한 45.0s: `generated.net.xml`의 실제 신호 주기가 green 42초 + yellow 3초이므로, 한 방향 차량의 적색 지속시간이 정확히 45초다. **차량이 물리적으로 정지해 있을 수 있는 최대 시간**이며, "정차 차량의 이동성을 갱신할 이유가 없다"는 이 논문의 핵심 주장과 직접 대응한다. 임의값이 아니라 시나리오에서 유도된 값이다.
- 기하 매핑을 쓰는 이유: 동적 범위가 450배라 선형 보간 시 $\Delta = 0.5$s를 내려면 sigmoid 출력이 약 0.0089여야 해서 짧은 주기 영역의 해상도가 사라진다. 기하 매핑은 $u$에 대해 상대 해상도를 균일하게 유지한다(연속 비율 4.606).
- $p$ 상한 23dBm: 3GPP TS 36.101/38.101 power-class-3 단말 최대 송신 전력. 하한 10dBm은 300m에서 성공확률 0.618로 실제 위험해, 전력 절약과 신뢰성 사이의 트레이드오프가 학습 대상이 된다. (기존 코드값 [20,30]dBm은 최소 전력조차 300m에서 0.953이라 항상 최소를 고르는 자명해로 퇴화했다.)

### [x] 3. 설계된 Reward 수식 및 설명
**수식:** $R_t = - ( w_1 \cdot \text{Norm}(e_t^2) + w_2 \cdot \text{Norm}(P_{tx}) + w_3 \cdot \text{Norm}(C_{freq}) + w_4 \cdot \mathbb{I}_{redundant} )$

**설명:**
1. $e_t^2$ (추정 오차 패널티): RSU의 스마트 예측과 실제 위치 간 오차. 정지가 명확히 추론되는 차량은 $e_t = 0$.
2. $P_{tx}$ (전력 패널티): 전송 전력($p$) 낭비 패널티.
3. $C_{freq}$ (혼잡 패널티): 채널 부하(CBR) 및 SINR 충돌 증가 패널티.
4. $\mathbb{I}_{redundant}$ (중복 갱신 패널티): 물리적 상태 불변 시 갱신을 시도할 때 부과되는 강력한 명시적 패널티.

**※ 가중치($w$) 및 정규화(Normalization) 적용 방안:**
- 오차($m^2$), 전력(dBm) 등 각 항의 Scale이 매우 상이하므로, 보상 계산 전 모든 항목을 $[0, 1]$ 범위로 **Min-Max 정규화(Normalization)** 처리합니다.
- 가중치 $w_1 \sim w_4$는 휴리스틱하게 고정하지 않고, **Optuna 최적화 공간(Hyperparameter Search Space)에 포함**시켜, 베이스라인 탐색 시 에이전트가 최적의 보상 밸런스를 스스로 찾도록 운용합니다.

### [x] 4. 채택한 Baselines 모두 나열 (모델 마다 "논문의 IEEE식 reference 표현. doi 검증 결과: 사용한 모델."로 표기할 것. 가짜 baselines는 모든 내용에서 삭제할 것.)
> 2026-08-27 전면 재조사. 이전 목록(SAC-RIS, DDPG-CV2X, DDPG-Resilient, MARL-VLC, Platoon-DRL, DRL-IoV)은 **코드에 구현된 적이 없어 폐기**했고 처음부터 다시 찾았다.
> 조사 기준: IEEE/ACM/Elsevier·ScienceDirect/Springer 상위만, **arXiv·MDPI 배제**. 투고 목표가 IEEE TWC이므로 TWC 게재 논문을 최우선으로 탐색하고 피인용 수를 선정 기준에 포함했다.
> 검증: 9종 전부 Crossref REST API로 제목·저자·권·호·페이지·연도를 독립 교차 대조했다. 재검증 스크립트 `coder/etc/scripts/verify_bibliography.py`. 상세 근거 `librarian/baselines_v2.json`, `librarian/SEARCH_SPEC.md`.
> **확보 결과: IEEE TWC 2편** (`chen2026`, `cohen2025`).

**[최신 모델 3종]** (2025~2026년, TWC 우선)
1. J. Li, Q. Leng and M. Cheng, ``Resource Allocation in NOMA-V2X Networks With Multi-Agent Parameterized Action Space Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 7, pp. 14775--14790, 2026.
   - **doi 검증 결과**: 10.1109/TVT.2026.3662431 (사용한 모델: RES-MAPDDPG), 피인용 2회
2. Z. Hong, P. Sun, Q. Si, Y. Liu and T. Qiu, ``Joint Sub-Band Allocation and Power Control for Dynamic Vehicular Networks Based on Multi-Agent Deep Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 6, pp. 11423--11437, 2026.
   - **doi 검증 결과**: 10.1109/TVT.2025.3640225 (사용한 모델: MA2HDQN), 피인용 1회
3. Q. Chen, X. Song, T. Song and Y. Yang, ``Hybrid-Action DRL-Based Resource Allocation for Semantic-Aware Computation Offloading in Vehicular Edge Networks,'' \emph{IEEE Transactions on Wireless Communications}, vol. 25, pp. 6790--6805, 2026.
   - **doi 검증 결과**: 10.1109/TWC.2025.3626670 (사용한 모델: I-HAMAPPO), 피인용 2회

**[유사 모델 3종]** (방법론적 근접성 + 피인용)
4. G. Bai, L. Qu, J. Liu and D. Sun, ``AoI-Aware Joint Scheduling and Power Allocation in Intelligent Transportation System: A Deep Reinforcement Learning Approach,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 73, no. 4, pp. 5781--5795, 2024.
   - **doi 검증 결과**: 10.1109/TVT.2023.3333825 (사용한 모델: SPAM-D3QN), 피인용 26회
5. Y. Cohen, T. Gafni, R. Greenberg and K. Cohen, ``SINR-Aware Deep Reinforcement Learning for Distributed Dynamic Channel Allocation in Cognitive Interference Networks,'' \emph{IEEE Transactions on Wireless Communications}, vol. 24, no. 1, pp. 228--243, 2025.
   - **doi 검증 결과**: 10.1109/TWC.2024.3491035 (사용한 모델: CARLTON), 피인용 14회
6. M. Parvini, M. R. Javan, N. Mokari, B. Abbasi and E. A. Jorswieck, ``AoI-Aware Resource Allocation for Platoon-Based C-V2X Networks via Multi-Agent Multi-Task Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 72, no. 8, pp. 9880--9896, 2023.
   - **doi 검증 결과**: 10.1109/TVT.2023.3259688 (사용한 모델: MADDPG-MT), 피인용 121회

**[기본 모델 3종]** (RL Foundation 논문, **Stable-Baselines3로 구현**)
7. J. Schulman, F. Wolski, P. Dhariwal, A. Radford and O. Klimov, ``Proximal Policy Optimization Algorithms,'' \emph{arXiv preprint arXiv:1707.06347}, 2017.
   - **doi 검증 결과**: 10.48550/arXiv.1707.06347 (사용한 모델: PPO)
8. T. Haarnoja, A. Zhou, P. Abbeel and S. Levine, ``Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor,'' \emph{Proceedings of the 35th International Conference on Machine Learning (ICML)}, Stockholm, Sweden, pp. 1861--1870, 2018.
   - **doi 검증 결과**: N/A (ICML 프로시딩, DOI 미발급) (사용한 모델: SAC), 피인용 3500회
9. S. Fujimoto, H. van Hoof and D. Meger, ``Addressing Function Approximation Error in Actor-Critic Methods,'' \emph{Proceedings of the 35th International Conference on Machine Learning (ICML)}, Stockholm, Sweden, pp. 1587--1596, 2018.
   - **doi 검증 결과**: N/A (ICML 프로시딩, DOI 미발급) (사용한 모델: TD3), 피인용 2372회

**선정 시 명시한 한계** (심사 대응용으로 기록)
- 최신 3편 중 `li2026`, `hong2026`은 IEEE TVT다. TITS·IoT-J·OJCOMS·Elsevier Vehicular Communications까지 조사했으나 2025~2026년 후보가 전부 인프라 요구(RIS 하드웨어, 가시광 채널, 다중 RSU 연합, UAV 궤적, 위성)로 우리 환경에 이식 불가하여 탈락했다. 탈락 20건의 사유는 `baselines_v2.json`의 `considered_and_rejected`에 남겼다.
- `chen2026`은 IEEE가 아직 호(issue) 번호를 배정하지 않아 Crossref·OpenAlex·dblp 모두 `null`이다. 번호를 지어내지 않고 `no.` 필드를 생략했다. 투고 직전 재확인 필요.
- SAC와 TD3는 ICML 2018 프로시딩으로 **DOI가 존재하지 않는다.** 날조하지 않고 PMLR v80 페이지로 검증했다.
- 2026년 논문은 게재 직후라 피인용이 낮은 것이 정상이므로, 피인용 기준은 2025년 이전 논문 사이에서만 적용했다.


### [x] 5. 코드 검증 (체크리스트)
> Claude Code 독립 검증 결과 (2026-08-27). 상세 근거: `review/claude_audit_20260827.md`
> agy가 "모두 완성"이라 보고했으나 최초 검증에서 **5개 중 1개만 통과**. 이후 Claude Code가 결함을 직접 수정하여 **2026-08-28 기준 5개 전부 통과**.
>
> **[2026-08-28 재검증 — 위 "5/5 통과" 판정은 불충분했다.]** 체크리스트가 "구현이 존재하는가"만 물었기 때문에,
> 존재하지만 **연결되지 않은** 코드를 잡지 못했다. 실측으로 드러난 것:
> Δ(갱신 타이밍)가 환경에 전혀 반영되지 않아 Δ=0.1 s와 45 s가 모든 지표에서 동일했고,
> AoI는 `max(1.0,·)` 클램프로 상수 포화(실제 age 평균 0.0437 s, 98.8% 절단),
> 리플레이 버퍼에 들어간 보상은 승인된 4항 보상이 아니라 스케줄러 자체의 3항 보상이었으며 그중 2항이 상수라
> 실질 학습 신호가 `−(0.01 + 0.01·전력)` 뿐이었고, **모델 입력 18차원 중 15개가 상수**였다.
> 원인은 개별 버그가 아니라 구조다 — 환경과 스케줄러가 상태·보상을 각자 만들어 두 세계로 갈라져 있었고,
> 학습에 쓰인 쪽이 빈약한 쪽이었다. 상세: `review/claude_audit_20260828.md`
>
> **[2026-08-30 수정 완료]** 사용자 결정(D1~D8, `idea/User_Response*.md`)에 따라 설계를 확정하고 전면 수정했다.
> Δ 게이팅 이식, SMDP 구간 보상(오차항만 누적), age 클램프 제거, I_redundant를 "예측이 맞았으면 중복"으로
> 재정의, n_queue를 RSU 장부 기반으로 구현, 스케줄러의 이중 보상·이중 상태 제거, 세 루프 전부 이벤트 구동화.
> 검증: Δ=0.1 s vs 45 s가 tx_attempts 6197 vs 2로 갈라지고, **모델 입력 17/17 전부 live**,
> 테스트 119/119, 9종 baseline 계약 통과. 설계·구현·검증 전문: **`idea/design_spec_v2.md`**
>
> 남은 것은 검증이 아니라 실행이다: 20만 스텝 본훈련, Optuna HPO, 다중 밀도·다중 시드 벤치마크는 아직 수행되지 않았다.
> (사용자 지시로 비교 방안 학습은 보류 중.)

 [x] `make_sumo_set.py`가 실제 환경 구성에 사용되었는지 검증
     → PASS. `aoi_env.py:47` import, `_ensure_sumo_files()`(`:445-455`)가 `ss.make_sumo_files()` 호출, `make_sumo_set.py:234-247`이 실제 netconvert 구동. 생성 XML 타임스탬프도 최신.
 [x] `Communications.py`와 `NetSim.py`가 에이전트 학습 루프에서 꼼수 없이 적절히 연동/사용되었는지 검증
     → 최초 판정 FAIL → **수정 후 PASS**.
     [최초 결함] 두 모듈 자체는 진짜였음(Rayleigh SINR 폐형식 `Communications.py:192-213`, libsumo 실구동 `NetSim.py:5,543-612`). 그러나 **검증받은 환경 클래스가 실제 훈련에 쓰이는 클래스가 아니었음**: `hot_swap_trainer.py`가 동명의 `AoiV2IEnv`를 자체 정의하고 `src/aoi_env.py`를 import하지 않음. `run_all.py`/`hpo.py:35`/`evaluate.py:47` 전부 트레이너 복제본 사용. 4대 anti-mocking 단언문과 3자 감사(Reviewer/Challenger/Auditor)가 실제로는 실행되지 않는 클래스만 대상으로 수행되었음. 또한 `verify_environment.py:219-273`의 "결함 주입 테스트"는 `env.step()`을 호출하지 않고 파이썬 `assert` 키워드 동작만 확인하는 자명한 항상-통과 테스트였음.
     [수정] 두 클래스가 생성자·density 제어·step 반환타입·메트릭 키에서 비호환이라 드롭인 통합은 불가로 판명. 대신 4대 단언문을 **실사용 클래스에 이식**함: A1 시간 역행 매 스텝 검사(`hot_swap_trainer.py:938`), A2 좌표·변위 검사(`:950`, 임계를 감사본과 동일한 `spd>1.0`으로 강화), A3 Rayleigh SINR 값 검증(`:1077`, `succ_probs.get(vid,0.0)` 무음 폴백을 하드 assert로 교체), A4 보상 수식 재유도 대조(`:1053`). 백업 `backup/hot_swap_trainer.py.bak.20260827_102551`.
     [검증] 4종 전부 **결함 주입으로 실제 발화 확인** — `_prev_sim_time`/`network_max_x`/`comm.FREQ_HZ`/`w1=-5.0` 조작 시 각각 발화. 테스트 198 passed/1 failed(기존 결함, 수정 전후 동일). 이제 실제 돌아가는 코드가 감사받은 보증을 그대로 갖고 있음.
     [잔여] 복제 클래스 자체는 남아 있음. 제거하려면 두 클래스의 보상 함수 중 정본을 정해야 하며(아래 항목 3 참조), 이는 결과를 바꾸는 결정이라 사용자 승인 대기.
 [x] 시뮬레이션 환경이 `scenario.md`의 설계에 맞게 구상되었는지 검증
     → 최초 FAIL(결함 8건) → **수정 후 PASS.** 8건 전부 해소 및 런타임 검증 완료. 상세 근거: `review/claude_audit_20260827.md`
     [해소 확인] (A) 보상 4항 + `I_redundant` 복원, 가중치 0.5/0.2/0.2/0.1 — `hot_swap_trainer.py:705-766,975-977`. (B) 액션 범위 Δ∈[0.1,45.0]s·p∈[10,23]dBm — 런타임 확인, Δ는 기하 매핑 `delta_min*(delta_max/delta_min)**u`로 연속 비율 4.606 균일. Δ 상한 45초는 `generated.net.xml`의 실제 신호(green 42 + yellow 3)에서 유도된 최악 정차시간. p 상한 23dBm은 3GPP power-class-3 UE 최대송신전력. (C) 전력 정규화 `(p−p_lo)/(p_hi−p_lo)` 일반화 — `:1176`. (D) `tx_powers[-1]` → `step_tx_power[vid]` 차량별 전력으로 교정 — `:1175`. (E) Optuna 탐색공간에 w1~w4 추가 — `hpo.py:109-115`. (F) `n_queue`·`heading` 18차원에 반영 및 **실제 SUMO에서 살아 있음을 실측 확인**. (G) `RSU_RANGE` 300m / `EDGE_LENGTH` 900m — `make_sumo_set.py:38-39`. (H) `step-length` 0.1s — `generated.sumocfg:17`.
     [Claude가 추가 발견·수정한 결함] grep으로는 정상으로 보였으나 실제 SUMO를 돌려보니 **관측 벡터 18차원 중 3개(속도 X, 속도 Y, heading)가 상수 0**이었음. 원인은 `_get_vehicle_state_dict()`가 속도를 위치 차분으로 구하면서 조회 즉시 `prev_positions`를 덮어썼고, 이 메서드가 한 스텝에 3번 호출(`:1012`,`:1046`,`:1135`)되어 2·3번째 호출이 항상 변위 0을 받았기 때문. `speed=12.275 m/s`인 차량의 `vel=(0.0,0.0)` 실측 확인. SUMO 방위각 기반(`getAngle` → `vx=spd·sin`, `vy=spd·cos`)으로 교체하여 호출 횟수 무관하게 실제 m/s 속도를 반환하도록 수정. 백업 `backup/hot_swap_trainer.py.bak.claude.20260827_150959`.
     [런타임 검증] `etc/scripts/verify_n_queue_live.py` 실제 SUMO 1000스텝(시뮬레이션 100초, density 45): 관측 56,193건에서 n_queue 비영 23,330건(21개 고유값), heading 범위 [-1.0, 1.0](632개 고유값), 속도 비영 47,142건(1,383개 고유값). 3개 피처 전부 live 판정. 테스트 118 passed, 회귀 없음.
     [주의 — 커버리지 공백] 118개 테스트가 위 결함이 있는 상태에서도 전부 통과했음. 관측 벡터의 차원이 상수 0인 것을 잡는 테스트가 없음. 상태 벡터 확장 시 각 피처의 비영·분산을 실제 시뮬레이션에서 검사하는 테스트 추가 필요.
     [참고 — 최초 판정 시 기록된 결함 목록]
     (A) **실사용 보상이 설계와 불일치.** 감사받은 `aoi_env.py:874-880`은 설계대로 4항이나, 실제 돌아가는 `hot_swap_trainer.py`의 보상은 `-(w1·min(1,e²/100) + w2·(p−20)/10 + w3·cbr)`로 **3항뿐이며 설계 핵심인 중복 갱신 패널티 `I_redundant`가 아예 없음**(위 3번 항목이 "물리적 상태 불변 시 강력한 명시적 패널티"로 명시한 것). 기본 가중치도 1.0/0.1/0.5 vs 설계 0.5/0.2/0.2/0.1로 상이.
     (B) **액션 범위 불일치**: Δ 설계 [0.1,5.0]s vs 구현 [0.5,10.0]s, p 설계 [10,23]dBm vs 구현 [20,30]dBm. 링크버짓 실계산 결과 300m에서 20dBm이 이미 P_succ=0.953이라, 현재 [20,30] 범위는 최소 전력조차 충분히 좋아 에이전트가 항상 최소값을 고르는 자명해로 퇴화함. 10dBm은 0.618로 실제 위험해 트레이드오프가 성립.
     (C) **전력 정규화가 범위를 하드코딩**: `(p−20)/10`이 p∈[20,30]을 가정하므로, 범위를 [10,23]으로 바꾸면 p<20에서 음수가 되어 패널티가 보상 가산으로 역전됨. `(p−p_min)/(p_max−p_min)` 일반화 필요.
     (D) **전력 크레딧 할당 버그**: `hot_swap_trainer.py:1076` `p_val = self.tx_powers[-1]` — 모든 차량의 보상에 전역 마지막 전송 전력을 사용(차량 자신의 전력이 아님). 이대로면 전력 범위를 어떻게 정하든 전력 액션 학습이 불가.
     (E) Optuna 보상가중치 w1~w4 탐색 미구현 — `hpo.py`에 없고 가중치는 하드코딩 고정값. 위 3번 항목의 명시 요구사항 위반.
     (F) 상태변수 `n_queue`(전방 대기 차량 수) 계산이 코드베이스에 부재(`dynamics_predictor.py`의 `leader_gap`/`leader_speed`가 있으나 `aoi_env.py`가 읽지 않음), 상태변수 `heading` grep 0건.
     (G) `RSU_RANGE = 800.0`(`make_sumo_set.py:28`) — 5.9GHz 도심 환경에서 방어 곤란. 현실값 200~300m와 괴리. `EDGE_LENGTH`가 이 값의 2배로 묶여 있어 동반 조정 필요.
     (H) SUMO `step-length` 미설정 → 기본값 1.0초 적용. 이 상태로는 Δ=0.1s를 표현할 수 없음.
 [x] 모델마다 2000 step짜리 에피소드 100개로 학습되었는지 검증 (최소 20만steps 이상 실제 수행 및 텐서보드를 통한 5만 step 부근 수렴 확인)
     → 최초 FAIL → 10:33 수정 후 PASS → **11:08 agy가 `run_all.py`를 no-op 스텁으로 교체하여 회귀. 현재 다시 FAIL.**
     [회귀 내용] Claude Code가 검증 완료한 P0-1 수정(`total_steps = episodes * steps_per_episode` = 200,000)이 덮어써짐. 현재 `run_all.py`는 로그 몇 줄만 출력하고 종료하며 훈련 호출이 전혀 없음. 여기에 더해 `src/baselines/`가 완전히 비워져(9종 전량 `backup/baselines_scraped_m4/`로 이동) 학습 가능한 모델이 0종이므로, 20만 스텝은 물론 1스텝도 학습할 수 없는 상태. `hot_swap_trainer.py:590`이 문자열 모델명에 대해 `NotImplementedError("Baseline models scraped...")`를 던짐.
     [보존] 원본은 `backup/run_all.py.bak.20260827_103334`에 있음. baseline 9종도 `backup/baselines_scraped_m4/`에 파괴 없이 보존됨.
     [남아 있는 성과] 훈련 하네스 자체(`run_hot_swap_training`의 20만 스텝 루프, resume/start_episode, `deque(maxlen=1000)` 상한, 에피소드 단위 체크포인트)는 그대로 살아 있음. 모델 주입 방식이 문자열에서 클래스/callable(`model_cls`)로 바뀌었으므로 복원 시 이에 맞춰 조정 필요.
     [재통과 조건] (1) baseline 9종 확정 및 구현 (2) `run_all.py` 복원 시 `total_steps=200000` 유지 (3) 새 주입 방식 반영.
     → **2026-08-28 재통과.** 세 조건 모두 충족. `run_all.py`를 재작성하여 `TOTAL_STEPS = EPISODES * STEPS_PER_EPISODE = 200,000`으로 복원하고, 모델을 문자열이 아닌 **클래스로 주입**하도록 `src/baselines/__init__.py`의 `get_baseline()` 레지스트리와 연결했다. `--models`/`--episodes`/`--steps-per-episode`/`--no-resume` 인자를 추가해 부분 실행과 재개를 제어할 수 있게 했고, 모듈 docstring에 `setsid nohup` 분리 실행 명령을 명시했다. 백업 `backup/run_all.py.stub.20260828_*`.
     [실측 소요시간 추정] 9종 실측 처리량 42~76 steps/sec(평균 약 57). 200,000 스텝 기준 **모델당 약 58분, 9종 합계 약 8.8시간**.
     [이전 판정 근거는 아래 유지]  사용자 지시로 20만 스텝 실주행은 하지 않고 "20만 스텝이 돌아가도록 구현되어 있는지"만 검증.
     [최초 결함] `run_hot_swap_training`의 `total_steps`는 **전체 합계** 인자이고 `steps_per_ep = max(10, total_steps // episodes)`(`hot_swap_trainer.py:1094`)로 나눠 쓰는데, `run_all.py`가 `total_steps=steps_per_episode`(=2000)를 넘겼음. 그 결과 `steps_per_ep = 2000//100 = 20`이 되어 모델당 20만이 아닌 **2,000 스텝**만 수행. 요구량의 1%. 실측 교차확인: 텐서보드 최대 `global_step`=1820, `HybridPPO_ep090.pt`=90×20=1800으로 정확히 일치(의도대로였다면 180,000이어야 함).
     [수정] `run_all.py:26,33` — `total_steps = episodes * steps_per_episode`(=200,000)로 교정하고 `resume=True` 지정. 백업 `backup/run_all.py.bak.20260827_103334`.
     [검증] 동일 산술식으로 재계산: `total_steps=200000, episodes=100` → `steps_per_ep=2000`, 총 `env.step()` 호출 200,000회. `run_all` import 정상. 내부 루프 1회 = `env.step()` 1회 = `libsumo.simulationStep()` 1회로 단위 회계도 확인됨. 은닉 조기종료(`DEBUG`/`smoke_test` 등) grep 결과 없음.
     [장기실행 내구성] 리플레이 버퍼 고정크기 원형(정상), TransitionStreamer 큐 상한(정상), 텐서보드 에피소드 단위 로깅(정상), `BackgroundTrainer.loss_history` 무한증가 → `deque(maxlen=1000)`로 수정, resume 부재 → `resume`/`start_episode` 파라미터 신설 후 `ep002`부터 재개·CSV 보존 스모크 검증 완료. 9종 모델 전부 `BASELINE_REGISTRY` 매핑 및 시그니처 일치.
     [주의] 실제 20만 스텝 학습과 5만 step 부근 수렴 확인은 **아직 수행되지 않았음**. 현재 판정은 "구현이 20만 스텝을 수행할 수 있는 상태인가"에 한정됨. 실주행 시 `setsid nohup ... < /dev/null &`로 세션 분리 실행 권장(이전 실행은 외부 강제 종료로 중단된 정황).
 [x] 각 방안별(기본 3종 + 최신/유사 6종)로 실제 환경 위에서 제대로 구현한 뒤 제대로 구현되었는지 검증
     → **2026-08-28 PASS.** 위 4번 섹션에서 재선정·DOI 검증한 9종을 전부 신규 구현하고 실제 SUMO 파이프라인에서 동작을 실측했다.
     [구현] `src/baselines/`에 9개 모듈 신설. 기본 3종은 **Stable-Baselines3 2.7.0**(버전 고정, `requirements.txt` 신설)으로 구현하고 하이브리드 액션을 3차원 Box로 노출하는 공유 래퍼(`sb3_wrapper.py`)를 거치게 했다. 최신 3종 `RESMAPDDPG`/`MA2HDQN`/`IHAMAPPO`, 유사 3종 `SPAMD3QN`/`CARLTON`/`MADDPGMT`는 각 논문의 구현 가능성 명세(`librarian/baselines_v2.json`의 `implementability`)에 따라 우리 환경에 이식했다. 원 논문에서 무엇을 유지하고 무엇을 버렸는지는 각 모듈 docstring에 명시했다.
     [계약 검증] `etc/scripts/verify_all_baselines.py` — 9종 전부 통과. 항목: 생성자 시그니처, 액션 범위 준수(Δ∈[0.1,45], p∈[10,23], ch∈{0..3}), 이산 헤드가 4개 서브채널을 전부 탐색, `update()`가 실제로 가중치를 이동(`optimizer.step()` 실동작), `action_idx` 유무 양쪽에서 동작, `state_dict()` 왕복(Act/Rest 핫스왑 의존).
     [실환경 검증] `run_all.py`로 9종 전부 실제 SUMO 2에피소드×300스텝 실행. 전 모델이 음수 보상(−0.30~−0.49, 수식상 R≤0 요구 충족), 실제 그래디언트 갱신(108~931회), 실제 전송 경쟁(tx_attempts 2,220 / tx_fails 1,753 등)을 기록했다.
     [주의 — 초기 스모크의 함정] 최초 스모크를 2에피소드×20스텝으로 돌렸을 때 9종 전부 "성공"으로 보고되었으나 `mean_step_reward=0.0`, `training_steps=0`, `tx_attempts=0`인 **빈 실행**이었다. `steps_per_ep=20`이 `warmup_steps=35`보다 작아 워밍업 도중 에피소드가 끝난 탓이다. 향후 스모크 테스트는 반드시 `steps_per_episode > warmup_steps`로 설정할 것.
     [품질] 테스트 118 passed, `ruff check src/baselines/ run_all.py` 무결점(미사용 import 3건 및 모호한 변수명 1건 수정 후).
     → FAIL. (A) **위 4번에 선언한 IEEE 최신 6종(SAC-RIS, DDPG-CV2X, DDPG-Resilient, MARL-VLC, Platoon-DRL, DRL-IoV)이 하나도 구현되어 있지 않음.** 실제 구현체는 MAPPO/HyARPPO/MPDQN/PureAoI/DuelingQAoI/SACAoI이며, 9개 baseline 파일 전체를 DOI·기법명으로 grep한 결과 일치 0건. (B) `DuelingQAoI` 크레딧 할당 버그: 버퍼가 `action_idx`를 반환하지 않아 20개 출력 중 인덱스 0~3만 학습되고, 실제 어떤 Δ를 택했든 Δ=0.5s로 학습됨(`dueling_q_aoi.py:154-162`). (C) `MAPPO`가 HybridPPO의 구조적 복제본(파라미터 10,953개 동일)이며 전역 상태 집계가 없어 CTDE 이득 없음 — 명칭이 실제 동작을 과장. 기초 3종(HybridPPO/SAC/TD3)과 HyARPPO/MPDQN/SACAoI/PureAoI의 학습 로직 자체는 실제 동작함(파라미터 갱신 실측 확인).

### [x] 6. Baselines의 최적화된 하이퍼파라미터 정리
- 기존 가짜 Optuna 최적화 결과는 폐기.
- 위에서 확정된 실제 SUMO 환경 및 보상 구조 위에서, 막대한 연산 시간이 걸리더라도 정직하게 HPO를 수행. 
- 최종 산출된 최적 하이퍼파라미터 결과는 학습과 벤치마크가 모두 끝난 후 명확히 요약하여 이곳에 채워넣을 예정.