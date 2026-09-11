# 채택 Baselines (v2) — 재조사 결과

> **2026-09-05 갱신(두 차례).** 이 문서는 한동안 `baselines_v2.json`보다 뒤처진 구버전 목록을 싣고 있었습니다. 1차 갱신에서 HOORL(`xu2026`)과 DDPG-AoI(`mlika2022`) 대신 I-HAMAPPO(`chen2026`)와 CARLTON(`cohen2025`)을 싣도록 JSON에 맞추었습니다. 이어서 사용자 결정으로 **유사 2번 자리의 CARLTON을 HOORL로 교체**했습니다. CARLTON은 목적함수에 AoI가 없어 유사 범주에 맞지 않고 구현 쪽 문제도 겹쳤으며, HOORL은 AoI를 목적함수에 담고 갱신 주기 자체를 학습하는 유일한 문헌입니다. 결과적으로 `xu2026`은 최신 범주에서 내려왔다가 유사 범주로 복귀했습니다. 이전 버전은 git 이력에서 확인할 수 있습니다. 앞으로도 JSON이 정본이고 이 문서는 그 표현입니다.

> 이전 에이전트가 제시한 baseline 목록(SAC-RIS, DDPG-CV2X, DDPG-Resilient, MARL-VLC, Platoon-DRL, DRL-IoV)은 **전량 폐기**하고, 어떤 항목도 재활용하지 않은 상태에서 처음부터 다시 검색했습니다.
> 검색 대상 venue는 IEEE / ACM / Elsevier(ScienceDirect) / Springer 상위 저널 / Nature 계열로 한정했으며, **arXiv 프리프린트와 MDPI는 전면 배제**했습니다. 유일한 예외는 RL 기초 3종(PPO/SAC/TD3)입니다.
> 선정의 최우선 기준은 화려함이 아니라 **우리 환경(18차원 RSU 관측, 하이브리드 액션 Δ·p·ch, 단일 RSU, SUMO + Rayleigh SINR)에서 실제로 재구현 가능한가**입니다.

**DOI 검증 절차 (전 항목 공통).** 모든 DOI를 (1) `https://doi.org/`로 실제 resolve시켜 IEEE Xplore 문서 페이지에 도달하는지 확인하고, (2) 제목·전체 저자·저널명·권·호·페이지·연도를 **Crossref REST API, OpenAlex API, dblp** 세 곳에서 각각 독립적으로 대조했습니다. 아래 9종은 세 출처가 모든 필드에서 일치했습니다. 초록은 Semantic Scholar Graph API로 확보하여 요약과 구현가능성 평가에 사용했습니다.

**연도 표기 주의.** IEEE는 early access 시점에 DOI를 부여하므로 DOI 문자열의 연도가 실제 게재 호(issue)보다 앞설 수 있습니다(예: `10.1109/TVT.2025.3640225` → 2026년 6월호, vol. 75 no. 6). 아래 인용은 모두 **최종 issue 연도** 기준이며, 이는 Crossref·dblp가 보고하는 값이자 IEEE가 논문에 인쇄하는 값입니다.

---

## [최신 모델 3종] — 2026년 게재 확정

2026년 V2X/IoV 분야의 AoI-aware DRL 자원할당 문헌을 훑은 결과, **하이브리드(이산+연속) 액션을 실제로 학습하는 연구**는 IEEE Transactions on Vehicular Technology와 목표 저널인 IEEE Transactions on Wireless Communications에 모여 있었습니다. 세 편 중 두 편이 TVT이고 한 편이 TWC이며, TITS·IoT-J·OJCOMS의 2026년 대안들도 모두 검토한 뒤 **구현가능성 때문에** 탈락시켰습니다(아래 "검토 후 제외" 참조). 2025년 논문으로 대체한 항목은 **없습니다** — 3종 전부 2026년입니다.

**1. RES-MAPDDPG** — 파라미터화 액션 공간(이산 채널 + 그에 딸린 연속 파라미터)을 한 정책으로 학습.

```latex
\bibitem{li2026} J. Li, Q. Leng and M. Cheng, ``Resource Allocation in NOMA-V2X Networks With Multi-Agent Parameterized Action Space Reinforcement Learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 7, pp. 14775--14790, 2026.
```

- **DOI 검증 결과**: 10.1109/TVT.2026.3662431 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/11373895. Crossref·OpenAlex·dblp 3중 대조 일치 (TVT vol. 75 no. 7, pp. 14775–14790, 2026). (사용할 모델명: RES-MAPDDPG)
- **구현가능성**: 구현 가능. res-MAPDDPG 학습기만 이식하여, 이산 헤드가 4개 서브채널 중 하나를 고르고 연속 헤드가 그 채널의 파라미터로 (Δ, p) 2차원을 출력하도록 확장(원 논문은 전력 1차원). NOMA 그룹핑·볼록최적화 V2I 단계는 **제거**(우리 상향링크는 직교 서브채널이며 SIC 수신기가 없음) — 이 경우 파라미터화 액션 DDPG 베이스라인으로 축약되며, 그것이 정확히 우리가 원하는 비교 대상임을 논문에 명시할 것.

**2. I-HAMAPPO** — 중요도 기반 하이브리드 액션 멀티에이전트 PPO. 연속 변수와 이산 변수를 하나의 정책에서 함께 최적화하며, 목표 저널인 IEEE TWC 게재분입니다.

```latex
\bibitem{chen2026} Q. Chen, X. Song, T. Song and Y. Yang, ``Hybrid-Action DRL-Based Resource Allocation for Semantic-Aware Computation Offloading in Vehicular Edge Networks,'' \emph{IEEE Transactions on Wireless Communications}, vol. 25, pp. 6790--6805, 2026.
```

- **DOI 검증 결과**: 10.1109/TWC.2025.3626670 — 검증 완료. doi.org resolve → ieeexplore.ieee.org/document/11226898. Crossref·OpenAlex·dblp 3중 대조 일치 (TWC vol. 25, pp. 6790–6805). **호 번호는 의도적으로 비워 두었습니다** — 세 색인 모두 아직 호를 배정하지 않아(Crossref `issue=null`, OpenAlex `issue=None`, dblp `number=None`) 번호를 지어내지 않고 `no.` 필드를 생략했습니다. 연도 주의: dblp와 Crossref는 2026, OpenAlex는 early access 날짜를 따라 2025로 보고합니다. (사용할 모델명: I-HAMAPPO)
- **키 주의**: `related_works.json`에도 `chen2026`이 있었으나 그것은 Haosheng Chen 외의 SAGIN P-DDQN 논문으로 다른 문헌입니다. 2026-09-05에 그 항목을 `chen20262`로 바꾸었고, 결과 표와 그림 범례에서 반복 인용되는 이 베이스라인이 접미사 없는 `chen2026`을 유지합니다.
- **구현가능성**: 구현 가능하며 시맨틱 관련 절반은 제거합니다. 원 관측은 태스크 큐·채널·엣지 서버 상태의 차량별 관점이고, 원 액션은 이산 오프로딩 및 자원 선택에 연속 시맨틱 압축률과 통신 자원 배분이 결합된 혼합 형태입니다. 우리 쪽 이식은 I-HAMAPPO 학습기를 그대로 두고 이산 분기가 4개 서브채널 중 하나를 고르며 연속 분기가 (Δ, p)를 내보내도록 연결한 뒤 18차원 RSU 관측을 넣는 것입니다. 멀티에이전트 PPO는 통신 범위 내 차량마다 파라미터를 공유하는 액터를 두고 전부 RSU에서 실행하므로 단일 RSU 중앙집중 스케줄러와 구조가 맞습니다. **중요도 평가 모듈과 시맨틱 압축률 액션은 제거**합니다. 우리는 시맨틱 특징이 아니라 이동성 상태를 전송하므로 유사도 항도 압축 대상도 없습니다. **논문에 정직하게 밝힐 점**: 원 논문 기여의 약 절반(시맨틱 및 중요도 평가 부분)은 재현하지 않으며 제목에 있는 하이브리드 액션 MAPPO 학습기만 비교한다는 사실입니다. 인프라 공백은 없습니다.

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

**2. HOORL** — 엣지 서버가 "누가 전송할지"와 "각 기기의 센싱 주기"를 동시에 결정하며, 목적함수가 요구 AoI와 에너지 소비의 가중합입니다. 갱신 주기 자체를 학습 대상으로 삼는 유일한 문헌이라 우리 Δ의 직접 대응물입니다.

```latex
\bibitem{xu2026} J. Xu, X. Zhou, M. Song, W. Wang, D. Niyato and C. Yuen, ``AoI and Energy-Aware Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning Framework,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 8, pp. 18102--18115, 2026.
```

- **DOI 검증 결과**: 10.1109/TVT.2026.3675626 — 검증 완료. Crossref 직접 조회(2026-09-05)로 제목, 저자 6인 전원, TVT vol. 75 no. 8, pp. 18102–18115, 2026이 모두 일치했습니다. doi.org resolve → ieeexplore.ieee.org/document/11442965이며 Crossref·OpenAlex·dblp 3중 대조도 일치합니다. **피인용**: Crossref 0, Semantic Scholar 1 (2026-09-05 조회). 2026년 게재 직후라 정상이며 품질 신호가 아닙니다. (사용할 모델명: HOORL)
- **AoI 목적함수**: 있습니다. 초록이 "The objective is to minimize the average weighted sum of required AoI and the energy consumption of the mobile devices"라고 명시합니다. AoI가 보조 지표가 아니라 최적화 대상이며, 이 점이 CARLTON을 대체한 첫 번째 이유입니다.
- **구현가능성**: 구현 가능하며 오프라인 로그 수집 단계가 하나 추가됩니다(사용자 결정으로 이 단계를 포함합니다). 원 결정 주체인 엣지 서버가 우리 RSU에, 전송 스케줄링이 서브채널 배정에, 센싱 주기가 우리 Δ에, 기기 에너지가 전력 항에 대응합니다. 부분관측 전제도 RSU가 차량 내부 상태를 보지 못하는 상황과 맞으므로 17차원 관측 벡터를 그대로 씁니다. **센싱 주기 대 Δ 대응**: 원 논문은 주기를 이산 후보에서 고르지만 우리 Δ는 [0.1, 45] s 연속이므로 기존 기하 매핑을 재사용해 정책이 이 구간의 Δ를 내도록 하고 그것을 다음 결정 시점까지의 침묵 구간으로 해석합니다. 서브채널은 이산 헤드가 4개 중 하나를, 전력은 [10, 23] dBm의 연속 출력을 냅니다. **오프라인 단계의 행동 정책**: 문서화된 고정 주기 휴리스틱으로 정합니다. Δ를 고정값으로 두고 서브채널과 전력을 각 범위에서 균등 무작위로 뽑으며, 이 명세를 기록해야 오프라인 강화학습의 전제인 행동 정책 기지성이 성립합니다. 다른 베이스라인의 학습 로그를 재활용하지 않는 이유가 여기 있습니다. 학습 도중 계속 변하는 정책이 만든 데이터는 분포 이동이 통제되지 않습니다. 수집은 동일한 SUMO 시나리오에서 CPU만 써서 수행하므로 다른 여덟 종의 탐색과 병행할 수 있습니다. **온라인 미세조정**: 오프라인에서 얻은 정책과 가치 함수를 초기값으로 삼아 우리 환경에서 이어 학습합니다. 이 인계 지점이 제목의 Hybrid가 가리키는 부분이므로 생략하지 않습니다. 인프라 공백은 없습니다.
- **원고에 쓸 도메인 방어 논거**: 심사자가 "왜 V2X가 아닌 논문을 비교군으로 삼았는가"를 물을 것이므로 미리 준비합니다. 첫째, 결정 구조가 1:1로 대응합니다. 하나의 인프라 노드가 다수 이기종 단말의 전송을 스케줄링하면서 갱신 주기를 함께 정한다는 세 조건이 모두 일치합니다. 둘째, 관측 조건이 맞습니다. 원 논문이 부분관측으로 정식화한 이유가 서버가 기기 배터리를 볼 수 없기 때문인데, 우리 RSU도 차량 내부 상태를 보지 못하고 마지막 수신 갱신과 추정에 의존합니다. 셋째, 목적함수가 같은 종류의 상충을 다룹니다. 넷째, 이 비교가 답하려는 질문이 "갱신 주기를 학습하는 기존 방식이 우리 침묵 구간 환산보다 나은가"이므로 갱신 주기를 학습하는 방법이 반드시 필요한데, 조사 범위에서 그 성질을 가진 문헌은 이 한 편뿐이었습니다.
- **정직하게 밝힐 약점 셋**: 응용 도메인이 V2X가 아니라 모바일 크라우드센싱입니다(위 논거를 함께 서술). 피인용이 0에서 1로 낮으며 선정 근거는 영향력이 아니라 방법론적 근접성입니다. 오프라인 데이터셋 생성이 선행되어야 해 준비 시간이 더 들며, 다만 그 부담은 CPU 시간에 한정됩니다.

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

사용자가 뒤집을 수 있도록 탈락 사유를 모두 남깁니다. 아래 DOI는 전부 실재하며 Crossref로 확인했습니다. 이 표는 `baselines_v2.json`의 `considered_and_rejected` 20건 중 주요 항목을 추린 것이며, 표에 없는 항목의 사유는 JSON에서 확인할 수 있습니다.

맨 위 두 건은 이전 버전에서 **채택 항목이었다가 강등된 문헌**입니다. 코드 레지스트리에 구현되어 있지 않으므로 원고에서 베이스라인으로 인용하면 실행되지 않은 비교군이 논문에 들어갑니다.

| 논문 | Venue / 연도 | DOI | 제외 사유 |
|---|---|---|---|
| SINR-Aware DRL for Distributed Dynamic Channel Allocation in Cognitive Interference Networks (Cohen, Gafni, Greenberg, Cohen) | IEEE TWC, 24(1), 228–243, 2025 | 10.1109/TWC.2024.3491035 | **강등(구 CARLTON, 유사 2번 자리). 2026-09-05 사용자 결정.** 사유는 둘입니다. 첫째, **목적함수에 AoI가 없습니다.** 전역 SINR 척도를 최대화하는 분산 채널 할당이며 정보 신선도 항을 담지 않는데, 유사 범주는 본 논문과 가장 가까운 연구를 담는 자리이고 본 논문의 주제가 AoI 인지 스케줄링이므로 어긋납니다. 채택 당시의 구현가능성 서술도 "AoI 목적은 우리 보상에서 오며 그 대체 사실을 밝혀야 한다"고 이미 적고 있었는데, 그 단서가 곧 이 자리에 맞지 않는다는 신호였습니다. 둘째, **구현 쪽 문제가 겹쳤습니다.** 전수 조사에서 mean 팔이 200,000스텝 내내 균등 무작위 정책에 고정된 것이 확인되었고 원논문의 저차원 QoS형 관측 표현도 재현되지 않았습니다. 근본 원인은 탐색 온도가 backup 연산자에 묶여 Q 값 척도에 대해 불변이 아니라는 점이며, 관측 정규화가 100에서 168로 바뀌면서 더 불확실해졌습니다. **되살릴 조건**: 유사 범주가 아니라 순수한 채널 할당 대조군을 따로 두기로 하고, 동시에 탐색 온도를 Q 값 척도에 불변이 되도록 고쳐 원논문 거동을 재현할 수 있게 된다면 재고할 수 있습니다. 문헌 자체에는 결함이 없으며 서지도 검증되어 있습니다 |
| Deep Deterministic Policy Gradient to Minimize the Age of Information in Cellular V2X Communications (Mlika, Cherkaoui) | IEEE TITS, 23(12), 23597–23612, 2022 | 10.1109/TITS.2022.3190799 | **강등(구 DDPG-AoI, 유사 2번 자리).** `cohen2025`에 밀렸습니다. 첫째로 `cohen2025`가 목표 저널 게재분입니다. 둘째로 2022년이라 선호 구간을 벗어나며 이전 버전에서도 연도 플래그가 붙어 있었습니다. 셋째로 `cohen2025`가 다루는 문제, 즉 반송파 간 간섭 아래 재사용되는 K개 주파수 분리 서브채널을 SINR 목적함수로 최적화하는 설정이 우리 경쟁 모델을 더 문자 그대로 기술합니다. 이 논문의 NOMA 자원블록 스케줄링은 우리에게 없는 SIC를 요구합니다. **2026-09-05 정정: 되살릴 수 없습니다.** 두 가지 이유입니다. 첫째, 이 DOI는 `SEARCH_SPEC.md:6`의 폐기 6종 중 DDPG-CV2X와 같은 논문이며 재조사에서 재선정되지 않았으므로 베이스라인은 물론 서론과 관련 연구에서도 인용할 수 없습니다. 둘째, 이 항목을 밀어낸 `cohen2025`도 같은 날 강등되어 그 자리를 `xu2026`이 차지했으므로 위 비교 논거 자체가 현재 상태를 설명하지 않습니다. 이전 판에 있던 "피인용 32회이므로 되살릴 수 있다"는 서술은 폐기 목록을 대조하지 않은 판단이었으므로 철회합니다 |
| Age-of-Information Aware Mobility-Based Vehicular-Fog Formation Using DRL (Tadele, Kar, Wakgra, Liyanage) | IEEE TITS, 27(7), 8238–8251, 2026 | 10.1109/TITS.2026.3667859 | **없는 인프라.** 학습 액션이 **다중 RSU** 환경의 RSU 연결(association)과 vehicular-fog 멤버십이며 전력·서브채널·갱신간격이 없음. 이동성도 Gauss-Markov(SUMO 아님). 단일 RSU 환경에서 액션 공간 자체를 표현 불가. RSU 2개로 환경을 확장할 의향이 있다면 재고 가능 |
| Multiagent DRL for Optimal Resource Allocation in AoI-Aware Energy-Efficient Platoon-Based C-V2X Networks (Zheng, Nguyen, Duong) | IEEE IoT-J, 13(6), 10814–10828, 2026 | 10.1109/JIOT.2025.3650400 | **플래툰 구조 부재.** 플래툰 리더·리더-팔로워 V2V·플래툰 내 CAM 전파 위에 세워진 정식화인데 우리 SUMO는 신호교차로 비정형 도심 교통. 플래툰을 걷어내면 parvini2023가 더 충실히 커버하는 일반 MADRL이 됨. (부가: 초록을 어떤 공개 출처에서도 확보하지 못해, 제목의 명시적 플래툰 프레이밍에 근거한 판단임을 밝힘) |
| A Resilient AoI-Aware Optimization Framework for ITS Using DRL (Arani, Saeedi, Norouzi, Nouruzi, Zorba, Yanikomeroglu) | IEEE OJ-COMS, 7, 7420–7437, 2026 | 10.1109/OJCOMS.2026.3707734 | **방법의 절반이 우리가 제어하지 않는 액션.** 기여의 핵심이 차량 **경로계획(routing)**과 AoI 자원할당의 결합인데, 우리 RSU는 (Δ,p,ch)만 결정하고 경로를 바꾸지 않음. routing을 빼면 보상만 재설계한 DDPG가 되어 논문 재현이 안 됨. **2026-09-05 추가: 이 항목은 뒤집을 수 없습니다.** 이 DOI는 `SEARCH_SPEC.md:6`의 폐기 6종 중 DDPG-Resilient와 같은 논문이며, 사용자가 명시적으로 폐기했고 재조사에서 재선정되지도 않았습니다. 따라서 베이스라인은 물론 서론과 관련 연구에서도 인용할 수 없습니다. 이전 판의 "뒤집을 만합니다"라는 서술은 폐기 목록을 대조하지 않은 판단이었으므로 철회합니다 |
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
| 2 | 최신 | I-HAMAPPO | `chen2026` | IEEE TWC 25 (호 미배정) | 2026 | 10.1109/TWC.2025.3626670 |
| 3 | 최신 | MA2HDQN | `hong2026` | IEEE TVT 75(6) | 2026 | 10.1109/TVT.2025.3640225 |
| 4 | 유사 | SPAM-D3QN | `bai2024` | IEEE TVT 73(4) | 2024 | 10.1109/TVT.2023.3333825 |
| 5 | 유사 | HOORL | `xu2026` | IEEE TVT 75(8) | 2026 | 10.1109/TVT.2026.3675626 |
| 6 | 유사 | MADDPG-MT | `parvini2023` | IEEE TVT 72(8) | 2023 | 10.1109/TVT.2023.3259688 |
| 7 | 기본 | PPO | `schulman2017` | arXiv (예외 허용) | 2017 | 10.48550/arXiv.1707.06347 |
| 8 | 기본 | SAC | `haarnoja2018` | ICML 2018 (PMLR 80) | 2018 | N/A |
| 9 | 기본 | TD3 | `fujimoto2018` | ICML 2018 (PMLR 80) | 2018 | N/A |
