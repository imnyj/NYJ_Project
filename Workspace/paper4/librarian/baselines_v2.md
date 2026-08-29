# 채택 Baselines (v2) — 재조사 결과

> 이전 에이전트가 제시한 baseline 목록(SAC-RIS, DDPG-CV2X, DDPG-Resilient, MARL-VLC, Platoon-DRL, DRL-IoV)은 **전량 폐기**하고, 어떤 항목도 재활용하지 않은 상태에서 처음부터 다시 검색했습니다.
> 검색 대상 venue는 IEEE / ACM / Elsevier(ScienceDirect) / Springer 상위 저널 / Nature 계열로 한정했으며, **arXiv 프리프린트와 MDPI는 전면 배제**했습니다. 유일한 예외는 RL 기초 3종(PPO/SAC/TD3)입니다.
> 선정의 최우선 기준은 화려함이 아니라 **우리 환경(18차원 RSU 관측, 하이브리드 액션 Δ·p·ch, 단일 RSU, SUMO + Rayleigh SINR)에서 실제로 재구현 가능한가**입니다.

**DOI 검증 절차 (전 항목 공통).** 모든 DOI를 (1) `https://doi.org/`로 실제 resolve시켜 IEEE Xplore 문서 페이지에 도달하는지 확인하고, (2) 제목·전체 저자·저널명·권·호·페이지·연도를 **Crossref REST API, OpenAlex API, dblp** 세 곳에서 각각 독립적으로 대조했습니다. 아래 9종은 세 출처가 모든 필드에서 일치했습니다. 초록은 Semantic Scholar Graph API로 확보하여 요약과 구현가능성 평가에 사용했습니다.

**연도 표기 주의.** IEEE는 early access 시점에 DOI를 부여하므로 DOI 문자열의 연도가 실제 게재 호(issue)보다 앞설 수 있습니다(예: `10.1109/TVT.2025.3640225` → 2026년 6월호, vol. 75 no. 6). 아래 인용은 모두 **최종 issue 연도** 기준이며, 이는 Crossref·dblp가 보고하는 값이자 IEEE가 논문에 인쇄하는 값입니다.

---

## [최신 모델 3종] — 2026년 게재 확정

2026년 V2X/IoV 분야의 AoI-aware DRL 자원할당 문헌을 훑은 결과, **하이브리드(이산+연속) 액션을 실제로 학습하는 연구가 IEEE Transactions on Vehicular Technology에 집중**되어 있었습니다. 세 편 모두 같은 저널인 것은 단일 질의의 편향이 아니라 해당 분야의 실제 분포이며, TITS·IoT-J·OJCOMS의 2026년 대안들도 모두 검토한 뒤 **구현가능성 때문에** 탈락시켰습니다(아래 "검토 후 제외" 참조). 2025년 논문으로 대체한 항목은 **없습니다** — 3종 전부 2026년입니다.

**1. RES-MAPDDPG** — 파라미터화 액션 공간(이산 채널 + 그에 딸린 연속 파라미터)을 한 정책으로 학습.

```latex
\bibitem{li2026} J. Li, Q. Leng and M. Cheng, ``Resource Allocation in NOMA-V2X Networks With Multi-Agent Parameterized Action Space Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 7, pp. 14775--14790, 2026.
```

- **DOI 검증 결과**: 10.1109/TVT.2026.3662431 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/11373895. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 75 no. 7, pp. 14775–14790, 2026). (사용할 모델명: RES-MAPDDPG)
- **구현가능성**: 구현 가능. res-MAPDDPG 학습기만 이식하여, 이산 헤드가 4개 서브채널 중 하나를 고르고 연속 헤드가 그 채널의 파라미터로 (Δ, p) 2차원을 출력하도록 확장(원 논문은 전력 1차원). NOMA 그룹핑·볼록최적화 V2I 단계는 **제거**(우리 상향링크는 직교 서브채널이며 SIC 수신기가 없음) — 이 경우 파라미터화 액션 DDPG 베이스라인으로 축약되며, 그것이 정확히 우리가 원하는 비교 대상임을 논문에 명시할 것.

**2. HOORL** — 엣지 서버가 "누가 전송할지"와 "각 노드의 센싱 주기(=갱신 간격)"를 동시에 결정. Δ를 학습 대상으로 삼는 유일한 2026년 문헌.

```latex
\bibitem{xu2026} J. Xu, X. Zhou, M. Song, W. Wang, D. Niyato and C. Yuen, ``AoI and Energy-Aware Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning Framework,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 8, pp. 18102--18115, 2026.
```

- **DOI 검증 결과**: 10.1109/TVT.2026.3675626 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/11442965. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 75 no. 8, pp. 18102–18115, 2026). (사용할 모델명: HOORL)
- **구현가능성**: 구현 가능하나 파이프라인 1단계 추가 필요. 센싱 주기 ↔ 우리 Δ가 1:1 대응, 전송 스케줄링 ↔ 서브채널 배정, 디바이스 에너지 ↔ 전력 패널티 $P_{tx}$로 대응되며 부분관측(POMDP) 전제도 우리 RSU 상황과 정확히 일치. 다만 offline 사전학습용 로그 데이터셋을 먼저 생성해야 함(고정 Δ 주기 휴리스틱 + 랜덤 채널/전력으로 동일 SUMO 환경에서 약 5만 transition 수집 후 online fine-tuning). 추가 하드웨어·인프라는 전혀 불필요. **주의로 표기할 점**: 응용 도메인이 V2X가 아닌 mobile crowdsensing(게재는 IEEE TVT)이며, 도메인 동일성이 아니라 방법론적 근접성(AoI+에너지+학습되는 샘플링 주기+부분관측)으로 선정했습니다.

**3. MA2HDQN** — 하이브리드 액션을 분기 구조로 명시 분할: 이산 서브밴드는 MA-D3QN, 연속 전력은 i-DDPG.

```latex
\bibitem{hong2026} Z. Hong, P. Sun, Q. Si, Y. Liu and T. Qiu, ``Joint Sub-Band Allocation and Power Control for Dynamic Vehicular Networks Based on Multi-Agent Deep Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 6, pp. 11423--11437, 2026.
```

- **DOI 검증 결과**: 10.1109/TVT.2025.3640225 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/11278196. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 75 no. 6, pp. 11423–11437). DOI 문자열은 2025지만 early access(2025-12-04) 때문이며, **최종 게재는 2026년 6월호**로 Crossref·dblp 모두 2026으로 보고. (사용할 모델명: MA2HDQN)
- **구현가능성**: 9종 중 가장 drop-in에 가까움. D3QN 분기를 우리 4개 서브채널에, i-DDPG 분기 출력을 1차원(p) → 2차원(Δ, p)으로 확장하기만 하면 됨(Δ는 기존 기하 매핑 재사용). 관측은 18차원 벡터 그대로. RIS·VLC·NOMA·다중 RSU·플래툰 등 부족한 인프라가 **하나도 없음**.

---

## [유사 모델 3종] — 방법론적으로 가장 가까운 연구

리뷰어가 "왜 이것과 비교하지 않았나"라고 물을 만한 순서대로 배치했습니다.

**1. SPAM-D3QN** — 인프라(RSU) 측 **단일 에이전트 MDP**로 스케줄링과 전력을 동시 결정하여 AoI 최소화. 행위 주체·결정 대상·목적함수·V2I 격자 토폴로지가 모두 우리와 동일한, 가장 가까운 선행 연구.

```latex
\bibitem{bai2024} G. Bai, L. Qu, J. Liu and D. Sun, ``AoI-Aware Joint Scheduling and Power Allocation in Intelligent Transportation System: A Deep Reinforcement Learning Approach,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 73, no. 4, pp. 5781--5795, 2024.
```

- **DOI 검증 결과**: 10.1109/TVT.2023.3333825 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/10321738. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 73 no. 4, pp. 5781–5795, 2024). (사용할 모델명: SPAM-D3QN)
- **구현가능성**: 구현 가능. 에이전트가 이미 우리와 같은 위치(RSU)에 있으므로 관측은 18차원 그대로. 연속 축을 D3QN 헤드용으로 이산화(p는 [10,23] dBm을 L단계, Δ는 연속 매핑과 **동일한 기하 격자**에서 K단계)하고 서브채널을 세 번째 이산 인자로 둠. PER은 그대로 이식. 리스크: 결합 액션 공간이 K×L×4로 폭증하므로 factored/branching Q-head 또는 거친 격자(예 K=8, L=4)를 쓰고 격자를 논문에 명시할 것. 이 베이스라인은 "완전 이산화 기준점" 역할을 하여 **연속 Δ·p가 실제로 무엇을 벌어주는지**를 정량화해 줍니다.

**2. DDPG-AoI** — 혼합 이산/연속 문제를 **분해**로 푸는 정석: 이산 RB 스케줄링은 stable-roommate 매칭, 연속 전력은 DDPG. 우리의 "하이브리드를 통째로 학습" 설계와 정반대 축의 대조군.

```latex
\bibitem{mlika2022} Z. Mlika and S. Cherkaoui, ``Deep Deterministic Policy Gradient to Minimize the Age of Information in Cellular V2X Communications,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol. 23, no. 12, pp. 23597--23612, 2022.
```

- **DOI 검증 결과**: 10.1109/TITS.2022.3190799 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/9839316. Crossref·OpenAlex·dblp 3중 대조 일치 (TITS vol. 23 no. 12, pp. 23597–23612, 2022). (사용할 모델명: DDPG-AoI)
- **구현가능성**: 분해형 베이스라인으로 구현 가능. 1단계는 기존 Rayleigh SINR 모듈이 이미 산출하는 SINR/경쟁 추정치로 매칭하여 서브채널 배정, 2단계는 배정된 채널을 조건으로 DDPG가 (Δ, p)를 출력. NOMA 전력영역 다중화·브로드캐스트 커버리지 변수·half-duplex 송수신기 선택은 **제거**(우리 상향링크 V2I 모델에 존재하지 않음).
- **⚠ 연도 예외 플래그**: 2022년으로, Category B의 선호 구간(2023–2026)을 벗어납니다. 2023년 이후 문헌 중 "매칭 + DDPG 분해"라는 동일한 대조 구도를 제공하는 AoI-V2X 논문을 찾지 못해 유지했습니다. 엄격한 최신성을 원하시면 이 항목만 교체 가능하나, 대체재는 방법론적 근접성이 더 낮아집니다(2023·2024는 parvini2023·bai2024가 이미 커버).
- **참고**: 이 DOI는 폐기된 목록에도 있었으나, 신규 Crossref 검색으로 **독립적으로 재도출**하여 자체 기준으로 재선정한 것이며 이전 목록에서 가져온 것이 아닙니다.

**3. MADDPG-MT** — 전역 critic + 에이전트별 지역 critic 이중 구조, 그리고 **보상을 sub-reward로 분해하여 task별 가치함수를 따로 학습**하는 변형. 우리 보상이 이질적인 4개 항의 가중합이므로, 이 아이디어가 원 논문보다 우리 문제에 더 잘 맞습니다.

```latex
\bibitem{parvini2023} M. Parvini, M. R. Javan, N. Mokari, B. Abbasi and E. A. Jorswieck, ``AoI-Aware Resource Allocation for Platoon-Based C-V2X Networks via Multi-Agent Multi-Task Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 72, no. 8, pp. 9880--9896, 2023.
```

- **DOI 검증 결과**: 10.1109/TVT.2023.3259688 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/10077432. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 72 no. 8, pp. 9880–9896, 2023). 저자명 주의: 4번째 저자를 Crossref·dblp는 "Bijan Abbasi", OpenAlex는 "Bijan Abbasi Arand"로 표기 — 2/3 다수형인 `B. Abbasi`를 채택했습니다. (사용할 모델명: MADDPG-MT)
- **구현가능성**: 구현 가능. 에이전트를 플래툰 리더가 아닌 **통신범위 내 개별 차량**으로 두고 actor·critic 전부를 RSU에서 실행 — 우리 스케줄러가 단일 RSU 중앙집중이므로 CTDE의 "중앙 critic"은 추가 가정이 아니라 실제 배치 구조 그 자체. 전역 critic의 입력은 이미 환경이 유지 중인 RSU Table($info_{others}$). task 분해 보상은 우리 4개 항($e^2$, $P_{tx}$, $C_{freq}$, $\mathbb{I}_{redundant}$)에 1:1로 대응. 플래툰/CAM 구조는 **제거**. 리스크: 차량이 300 m 범위를 드나들며 에이전트 수가 변하므로 전역 critic에 고정크기 패딩 + validity mask(또는 permutation-invariant pooling)를 **직접 구현해야 함** — 원 논문에 없는 부분입니다.

---

## [기본 모델 3종] — RL Foundation

세 편 모두 **Stable-Baselines3(SB3)** 구현을 사용하되, 우리 하이브리드 액션 공간에 맞춰 래핑합니다. 래퍼는 `[-1,1]` 범위의 3차원 Box를 노출하여 0·1번 차원을 Δ(기하 매핑, [0.1,45] s)와 p(선형, [10,23] dBm)에, 2번 차원을 4개 서브채널로 binning합니다. **세 모델 모두 동일한 래퍼를 써야 상호 비교가 성립**하며, 래퍼 방식은 논문에 명시해야 합니다.

```latex
\bibitem{schulman2017} J. Schulman, F. Wolski, P. Dhariwal, A. Radford and O. Klimov, ``Proximal Policy Optimization Algorithms,'' \emph{arXiv preprint arXiv:1707.06347}, 2017.
```

- **DOI 검증 결과**: 10.48550/arXiv.1707.06347 — 검증 완료. doi.org resolve → arxiv.org/abs/1707.06347. 제목·저자 5인 dblp(CoRR abs/1707.06347, 2017) 대조 일치. venue 규칙의 유일한 예외(기초 RL 3종)에 해당. (사용할 모델: PPO, SB3 `PPO`)
- **구현가능성**: SB3 `PPO` + 공통 하이브리드 래퍼. binning 손실이 문제가 되면 (Δ,p)는 DiagGaussian, ch는 Categorical로 결합한 커스텀 분포로 대체 가능.

```latex
\bibitem{haarnoja2018} T. Haarnoja, A. Zhou, P. Abbeel and S. Levine, ``Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor,'' \emph{Proceedings of the 35th International Conference on Machine Learning (ICML)}, Stockholm, Sweden, pp. 1861--1870, 2018.
```

- **DOI 검증 결과**: **DOI 없음 (N/A)** — ICML 2018 proceedings(PMLR v80)에는 DOI가 부여되지 않습니다. 대신 proceedings.mlr.press/v80/haarnoja18b.html 원문에서 "Proceedings of the 35th International Conference on Machine Learning, PMLR 80:1861-1870, 2018"과 저자 4인을 직접 확인했고, dblp의 ICML 2018 레코드로 교차 확인했습니다. 참고: dblp는 페이지를 1856–1865로 표기하는데 이는 인쇄본 페이지네이션이며, 관례적·권위적 인용은 PMLR 기준 1861–1870이므로 후자를 사용했습니다. (사용할 모델: SAC, SB3 `SAC`)
- **구현가능성**: SB3 `SAC` + 공통 래퍼. SB3의 SAC은 Box 전용이라 binning 래퍼가 선택이 아닌 **필수**. 액션이 3차원이 되므로 `target_entropy`를 재조정해야 하며, 보상 가중치 $w_1\sim w_4$와 함께 Optuna 탐색공간에 포함시킬 것.

```latex
\bibitem{fujimoto2018} S. Fujimoto, H. van Hoof and D. Meger, ``Addressing Function Approximation Error in Actor-Critic Methods,'' \emph{Proceedings of the 35th International Conference on Machine Learning (ICML)}, Stockholm, Sweden, pp. 1587--1596, 2018.
```

- **DOI 검증 결과**: **DOI 없음 (N/A)** — ICML 2018 proceedings(PMLR v80). proceedings.mlr.press/v80/fujimoto18a.html에서 "PMLR 80:1587-1596, 2018"과 저자 3인 직접 확인, dblp ICML 2018 레코드로 교차 확인. dblp 표기(1582–1591)는 인쇄본 페이지네이션. (사용할 모델: TD3, SB3 `TD3`)
- **구현가능성**: SB3 `TD3` + 공통 래퍼. TD3는 결정론적이라 binning된 3번째 차원에 자체 탐색이 없으므로 action noise 크기가 bin 경계를 실제로 넘길 만큼 커야 함. 이 점은 **연속 전용 기법이 이산 서브채널 결정에서 하이브리드 액션 베이스라인보다 불리한 정직한 이유**로 논문에 명시할 것.

---

## 검토 후 제외 (considered_and_rejected)

사용자가 뒤집을 수 있도록 탈락 사유를 모두 남깁니다. 아래 DOI는 전부 실재하며 Crossref로 확인했습니다.

| 논문 | Venue / 연도 | DOI | 제외 사유 |
|---|---|---|---|
| Age-of-Information Aware Mobility-Based Vehicular-Fog Formation Using DRL (Tadele, Kar, Wakgra, Liyanage) | IEEE TITS, 27(7), 8238–8251, 2026 | 10.1109/TITS.2026.3667859 | **없는 인프라.** 학습 액션이 **다중 RSU** 환경의 RSU 연결(association)과 vehicular-fog 멤버십이며 전력·서브채널·갱신간격이 없음. 이동성도 Gauss-Markov(SUMO 아님). 단일 RSU 환경에서 액션 공간 자체를 표현 불가. RSU 2개로 환경을 확장할 의향이 있다면 재고 가능 |
| Multiagent DRL for Optimal Resource Allocation in AoI-Aware Energy-Efficient Platoon-Based C-V2X Networks (Zheng, Nguyen, Duong) | IEEE IoT-J, 13(6), 10814–10828, 2026 | 10.1109/JIOT.2025.3650400 | **플래툰 구조 부재.** 플래툰 리더·리더-팔로워 V2V·플래툰 내 CAM 전파 위에 세워진 정식화인데 우리 SUMO는 신호교차로 비정형 도심 교통. 플래툰을 걷어내면 parvini2023가 더 충실히 커버하는 일반 MADRL이 됨. (부가: 초록을 어떤 공개 출처에서도 확보하지 못해, 제목의 명시적 플래툰 프레이밍에 근거한 판단임을 밝힘) |
| A Resilient AoI-Aware Optimization Framework for ITS Using DRL (Arani, Saeedi, Norouzi, Nouruzi, Zorba, Yanikomeroglu) | IEEE OJ-COMS, 7, 7420–7437, 2026 | 10.1109/OJCOMS.2026.3707734 | **방법의 절반이 우리가 제어하지 않는 액션.** 기여의 핵심이 차량 **경로계획(routing)**과 AoI 자원할당의 결합인데, 우리 RSU는 (Δ,p,ch)만 결정하고 경로를 바꾸지 않음. routing을 빼면 보상만 재설계한 DDPG가 되어 논문 재현이 안 됨. **탈락 목록 중 가장 아슬아슬한 건**: AoI 위반의 심각도·지속시간을 벌하는 resiliency 패널티 자체는 우리 보상으로 이식 가능하므로, TVT가 아닌 2026년 항목을 원하시면 이것으로 뒤집을 만합니다 |
| DRL-Based AoI-Aware Resource Allocation for RIS-Aided IoV Networks (Qi 외 6인) | IEEE TVT, 74(1), 1365–1378, 2025 | 10.1109/TVT.2024.3452790 | **RIS 하드웨어 없음.** 액션 벡터 상당 부분이 RIS 위상천이 설정이고 성능 이득도 거기서 나옴. 우리 Rayleigh 페이딩 모델에 RIS 소자가 없으며, 넣으면 에이전트가 아니라 물리계층이 바뀜. (폐기 목록은 이 논문을 "2024"로 적었으나 실제 게재는 2025년 1월호) |
| Efficient AoI-Aware Resource Management in VLC-V2X Networks via Multi-Agent RL (Azizi, Zeinali, Mili, Shokrollahi) | IEEE TVT, 73(9), 14009–14014, 2024 | 10.1109/TVT.2024.3392738 | **시뮬레이션하지 않는 가시광 채널.** LED 헤드램프 기하와 Lambertian 광 경로손실 위의 자원할당. 우리는 5.9 GHz RF + Rayleigh이므로 배분할 VLC 링크 자체가 없음 |
| DRL-Based Optimization for AoI and Energy Consumption in C-V2X Enabled IoV (Zhang, Wu, Fan, Cheng, Chen, Letaief) | IEEE TGCN, 9(4), 2144–2159, 2025 | 10.1109/TGCN.2025.3531902 | **채널 모델 불일치.** 논문의 요체가 C-V2X mode-4 SPS 위에 NOMA+SIC를 얹은 **분산 V2V** 자원선택. 우리는 직교 서브채널 V2I 상향링크 + RSU 중앙 스케줄러 + SIC 없음으로, 다중접속 방식과 결정 주체가 모두 다름. 이식하려면 SINR 모델을 다시 써야 함 |
| Optimization of Spectrum Resource Allocation for Vehicle Platoon in V2X Networks Based on DRL (Lin, Pan, Wang) | IEEE TVT, 75(6), 11512–11527, 2026 | 10.1109/TVT.2025.3643923 | **플래툰 구조 부재**(위 Zheng 건과 동일). 추가로 AoI 목적함수와 갱신간격 결정이 아예 없어, 같은 호·같은 액션공간의 hong2026보다 방법론적 근접성이 낮음. (폐기 목록은 "2025"로 적었으나 실제 게재는 2026년 6월호) |
| Hybrid-Action MARL for Task Offloading and Resource Allocation in Space Computing Power Networks (Lai 외 5인) | IEEE IoT-J, early access, 2026 | 10.1109/JIOT.2026.3702157 | **도메인 불일치 + 서지정보 미완.** 위성 컴퓨팅 네트워크 태스크 오프로딩으로 AoI 목적도 차량 이동성도 없음. 하이브리드 액션 MARL 아이디어는 li2026·hong2026이 도메인 내에서 이미 대표. 게다가 early access라 vol/no/pp가 없어(`1-1`) 요구된 저널 인용 형식을 채울 수 없음 |
| A Two-Layered RL Framework for AoI-Aware Trajectory Planning and Scheduling in Multi-UAV Networks (Fu, Zhao, Wang) | IEEE IoT-J, 13(3), 4668–4682, 2026 | 10.1109/JIOT.2025.3636204 | **없는 UAV 이동성 액션.** 2계층 중 상위 계층이 UAV 궤적을 계획 = 에이전트가 이동성을 제어. 우리 RSU는 교차로에 고정이고 차량 운동은 SUMO의 차량추종·신호 로직이 결정. 하위 스케줄링 계층만 남으면 bai2024의 열화판 |
| Joint Optimization of AoI and Energy Consumption in NR-V2X System Based on DRL | Sensors (MDPI), 24(13), 4338, 2024 | 10.3390/s24134338 | **Venue 규정에 의한 배제(MDPI).** 주제적으로는 상당히 가까운 AoI+에너지 NR-V2X DRL 논문이 검색되었으나 규정상 사용하지 않았음을 기록으로 남김 |

---

## 요약 표 (결과 테이블용 모델명)

| # | 구분 | 모델명 | 논문 ID | Venue | 연도 | DOI |
|---|---|---|---|---|---|---|
| 1 | 최신 | RES-MAPDDPG | `li2026` | IEEE TVT 75(7) | 2026 | 10.1109/TVT.2026.3662431 |
| 2 | 최신 | HOORL | `xu2026` | IEEE TVT 75(8) | 2026 | 10.1109/TVT.2026.3675626 |
| 3 | 최신 | MA2HDQN | `hong2026` | IEEE TVT 75(6) | 2026 | 10.1109/TVT.2025.3640225 |
| 4 | 유사 | SPAM-D3QN | `bai2024` | IEEE TVT 73(4) | 2024 | 10.1109/TVT.2023.3333825 |
| 5 | 유사 | DDPG-AoI | `mlika2022` | IEEE TITS 23(12) | 2022 | 10.1109/TITS.2022.3190799 |
| 6 | 유사 | MADDPG-MT | `parvini2023` | IEEE TVT 72(8) | 2023 | 10.1109/TVT.2023.3259688 |
| 7 | 기본 | PPO | `schulman2017` | arXiv (예외 허용) | 2017 | 10.48550/arXiv.1707.06347 |
| 8 | 기본 | SAC | `haarnoja2018` | ICML 2018 (PMLR 80) | 2018 | N/A |
| 9 | 기본 | TD3 | `fujimoto2018` | ICML 2018 (PMLR 80) | 2018 | N/A |
