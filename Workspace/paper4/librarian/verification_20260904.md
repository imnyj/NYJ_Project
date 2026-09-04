# paper4 문헌 실존성 전수 검증 (2026-09-04)

검증자: librarian 에이전트
검증 기준일: 2026년 9월 4일
검증 방법: Crossref REST API(`https://api.crossref.org/works/{DOI}`)에 DOI를 직접 조회하여 제목, 저자 전원, 저널명, 권, 호, 페이지, 발행 연도를 항목별로 대조했습니다. 제목만 있고 DOI가 의심스러운 항목은 `query.bibliographic` 서지 검색으로 동일 제목의 논문이 존재하는지 별도로 확인했습니다. 인용 적합성 판정이 필요한 항목은 Semantic Scholar Graph API로 초록 전문을 받아 본문 주장과 대조했습니다.
기존 `coder/etc/scripts/verify_bibliography.py`의 판정은 참조하지 않았고, 모든 조회를 이 문서에서 새로 수행했습니다.

조회 방법의 신뢰성을 먼저 확인하기 위해 실존이 확실한 DOI(`10.1109/INFCOM.2012.6195689`)를 먼저 조회하여 정상적으로 서지 레코드가 반환되는 것을 확인한 뒤, 나머지 항목을 조회했습니다. 따라서 아래에 기록된 404 응답은 도구의 오작동이 아니라 해당 DOI가 Crossref에 등록되어 있지 않다는 뜻입니다.

## 판정 등급 요약

아래 건수는 논문 단위가 아니라 파일에 적힌 레코드 단위입니다. `related_works.json` 42건, `baselines_v2.json` 베이스라인 9건과 배제 목록 20건, `main.tex` bibitem 10건, `writer/references.json` 9건을 합한 90건이 모집단입니다. 같은 논문이 여러 파일에 중복 등재된 경우는 각각 따로 셌습니다.

| 등급 | 정의 | 건수 |
|---|---|---|
| A. 확인 완료 | 제목, 저자, 저널명, 권/호/페이지, 연도가 모두 Crossref 레코드와 일치 | 74 |
| B. 수정 필요 | 논문은 실존하나 기재된 서지 정보에 오류가 있음 | 7 |
| C. 미확인 | DOI가 존재하지 않고 동일 제목의 논문도 찾지 못함 | 8 |
| D. 검증 제외 | 금지 출처라 정책상 조회하지 않음 | 1 |

## 1. 가장 심각한 결함 세 가지

### 1-1. `writer/references.json`과 `User_Request.md` References의 8건이 실존하지 않습니다

9건 중 8건의 DOI가 Crossref에 존재하지 않았고, 해당 제목의 논문도 검색되지 않았습니다. 팀 리드가 지목한 대로 `10.1109/TITS.2025.3512345`, `10.1109/TVT.2024.3456789`처럼 끝자리가 규칙적인 DOI는 전부 생성된 값입니다. 실존이 확인된 항목은 [7] 한 건뿐이며, 그 한 건조차 저자 목록이 틀렸습니다.

### 1-2. `writer/main.tex`가 정의되지 않은 인용 키 6개를 본문에서 사용합니다

`main.tex`의 본문은 `al-khasawneh2026uav`, `zhang2025small`, `li2025next`, `sun2025overcoming`, `park2025adaptive`, `duan2026energy`를 인용하지만, `thebibliography` 블록에는 이 여섯 키의 `\bibitem`이 하나도 없습니다. 즉 현재 원고는 컴파일하면 미정의 인용 경고를 내고 본문에 `[?]`가 찍힙니다. 그리고 이 여섯 키는 모두 위 1-1에서 실존하지 않는 것으로 판정된 문헌입니다. 서론 1문단과 2문단 전체가 존재하지 않는 문헌에만 근거하고 있습니다.

### 1-3. `chen2026` 키가 서로 다른 두 논문을 가리킵니다

| 파일 | 제목 | DOI |
|---|---|---|
| `librarian/related_works.json` | Mobile-Edge Computing in SAGINs: A Hybrid Action Space P-DDQN Algorithm for Joint Offloading and Resource Allocation | 10.1109/TWC.2026.3706356 |
| `librarian/baselines_v2.json` | Hybrid-Action DRL-Based Resource Allocation for Semantic-Aware Computation Offloading in Vehicular Edge Networks | 10.1109/TWC.2025.3626670 |

두 논문 모두 실존하고 서지 정보도 정확합니다. 문제는 동일한 bibitem 키를 공유한다는 점입니다. 두 JSON을 하나의 참고문헌 목록으로 병합하면 한쪽 인용이 조용히 다른 논문을 가리키게 됩니다. 이것은 팀 리드가 지적한 "DOI는 살아 있는데 다른 논문을 가리키는" 유형의 오류가 키 수준에서 발생한 사례입니다. 둘 중 하나를 `chen2026a`/`chen2026b`처럼 구분하거나 저자 이름을 반영해 `chenh2026`(Haosheng Chen)과 `chenq2026`(Quan Chen)으로 분리해야 합니다.

## 2. `writer/references.json` 및 `User_Request.md` References [1]~[9]

| 번호 | 기재된 서지 정보 | Crossref 조회 결과 | 등급 | 필요한 수정 |
|---|---|---|---|---|
| [1] | M. Al-Khasawneh 외 3인, "UAV-Mounted Reconfigurable Intelligent Surfaces for Dynamic IoV Coverage," IEEE TITS, 2026, DOI 10.1109/TITS.2025.3512345 | DOI 404. 동일 제목 논문 없음. 유사 제목 3건은 모두 다른 논문 | C | 삭제. 3-1의 대체안 참조 |
| [2] | H. Zhang 외 3인, "Small Language Models for Real-Time Edge Decision Making in 6G Vehicular Networks," IEEE Wireless Communications, 2025, DOI 10.1109/MWC.2024.3412321 | DOI 404. 동일 제목 논문 없음 | C | 삭제. 3-1의 대체안 참조 |
| [3] | X. Li 외 3인, "Next-Generation Intelligent Transportation Systems Using Multimodal Generative AI," IEEE Trans. Intell. Veh., 2025, DOI 10.1109/TIV.2024.3389012 | DOI 404. 유사 제목의 SSRN 프리프린트(10.2139/ssrn.5547519, Haowen Xu)가 있으나 저자와 게재처가 전혀 다르고 프리프린트라 정책상 사용 불가 | C | 삭제. 3-1의 대체안 참조 |
| [4] | J. Park 외 3인, "Adaptive Congestion Control for Periodic Safety Messages in Dense V2X Networks," IEEE TVT, 2025, DOI 10.1109/TVT.2024.3394567 | DOI 404. 동일 제목 논문 없음 | C | 삭제. 3-2의 대체안으로 교체 |
| [5] | Y. Sun 외 3인, "Overcoming Cellular Bottlenecks in V2N Communications via Edge-Assisted V2I Offloading," IEEE IoT-J, 2025, DOI 10.1109/JIOT.2024.3401234 | DOI 404. 동일 제목 논문 없음 | C | 삭제. 대체 문헌을 찾지 못했습니다. 아래 `## 질의` 1번 항목 참조 |
| [6] | L. Duan, L. Gao, J. Huang, "Energy-Efficient Resource Allocation for Periodic Status Updates in V2I Networks," IEEE TMC, 2026, DOI 10.1109/TMC.2025.3423456 | DOI 404. 동일 제목 논문 없음 | C | 삭제. 3-3의 대체안으로 교체 |
| [7] | A. H. Arani, H. Yanikomeroglu, N. Zorba, "A Resilient AoI-Aware Optimization Framework...," IEEE OJ-COMS, 2026, DOI 10.1109/OJCOMS.2026.3707734 | **실존**. 단 저자가 Atefeh Hajijamali Arani, Hamid Saeedi, Sajedeh Norouzi, Ali Nouruzi, Nizar Zorba, Halim Yanikomeroglu 6인. vol. 7, pp. 7420-7437, 2026 | B | 저자 6인 전원으로 교체. 첫 저자 이름이 "Amir Hossein Arani"로 기재되어 있으나 실제는 "Atefeh Hajijamali Arani". 권 7과 페이지 7420-7437 추가 |
| [8] | Z. Ning 외 3인, "Age and Power Minimization via Meta-Deep Reinforcement Learning in Vehicular Edge Computing," IEEE TVT, 2025, DOI 10.1109/TVT.2024.3456789 | DOI 404. 다만 제목이 매우 유사한 실존 논문 발견: "Age and Power Minimization via Meta-Deep Reinforcement Learning in **AAV** Networks," S. Sarathchandra 외 5인, IEEE TVT vol. 74, no. 11, pp. 16839-16849, 2025, DOI 10.1109/TVT.2025.3579626 | C | 기재된 형태로는 삭제. 실존 논문은 무인 항공기(AAV) 대상이라 차량 엣지 컴퓨팅 주장의 근거로는 부적합하므로 3-3의 대체안 사용 권장 |
| [9] | Q. Cui 외 3인, "Scheduling for Maximizing Information Freshness in V2I Systems via Branch-Network DRL," IEEE TITS, 2025, DOI 10.1109/TITS.2024.3478901 | DOI 404. 다만 초록에 실제로 branch network와 action masking이 등장하는 실존 논문 발견: "Scheduling for Maximizing the Information Freshness in Vehicular Edge Computing-Assisted IoT Systems," Xin Xie, Tao Zhong, Heng Wang, IEEE TITS vol. 26, no. 3, pp. 4140-4151, 2025, DOI 10.1109/TITS.2024.3514099 | C | 3-4의 실존 논문으로 교체. 원래 요약에 적힌 기술적 내용은 이 실존 논문의 것이 변형되어 옮겨진 것으로 보입니다 |

[8]과 [9]는 실존 논문의 기술적 내용은 보존한 채 제목의 응용 분야, 저자, DOI만 바뀐 형태입니다. 완전한 창작이 아니라 실존 문헌이 변형된 결과이므로, 대체 문헌을 찾을 때 이 단서가 유용했습니다.

## 3. 미확인 항목의 대체 문헌 제안

모든 대체안은 Crossref에서 DOI를 직접 조회해 서지 정보를 확인했고, 인용 적합성을 판단할 수 있도록 초록을 읽었습니다. 전부 IEEE 발행물입니다.

### 3-1. [1][2][3] 대체: 서론 도입부의 CAV/C-ITS 및 실시간 이동성 데이터 필요성

**대체안 A**
K. Cai, T. Qu, B. Gao, and H. Chen, "Consensus-Based Distributed Cooperative Perception for Connected and Automated Vehicles," *IEEE Transactions on Intelligent Transportation Systems*, vol. 24, no. 8, pp. 8188-8208, 2023. DOI 10.1109/TITS.2023.3264608

초록 확인 결과 "V2X 정보를 활용한 협력 인지는 자율주행차의 인지 능력을 향상시키지만, 제한된 통신 부담 안에서 연결 정보의 이득을 최대화해야 하는 새로운 과제를 제기한다"고 명시하고 있습니다. 서론이 세우려는 대립 구도, 즉 정보 교환의 필요성과 통신 자원의 제약이 충돌한다는 구도를 그대로 뒷받침합니다.

**대체안 B**
Z. Huang, S. Chen, Y. Pian, Z. Sheng, S. Ahn, and D. A. Noyce, "Toward C-V2X Enabled Connected Transportation System: RSU-Based Cooperative Localization Framework for Autonomous Vehicles," *IEEE Transactions on Intelligent Transportation Systems*, vol. 25, no. 10, pp. 13417-13431, 2024. DOI 10.1109/TITS.2024.3410185

RSU가 C-V2X를 통해 차량의 정확한 위치를 유지하는 프레임워크를 다루므로, 인프라가 주변 차량의 실시간 이동성 정보를 보유해야 한다는 주장의 근거로 적합합니다.

기존에 이미 검증된 문헌 중에서 고른다면 `ding2023`(차량 궤적 예측 서베이)과 `sun2022`(신호 교차로 V2I 에코 드라이빙)도 같은 자리를 메울 수 있습니다. 이미 `related_works.json`에 검증된 상태로 들어 있으므로 새 항목을 추가하지 않아도 됩니다.

### 3-2. [4] 대체: 고정 주기 CAM 브로드캐스트로 인한 채널 혼잡과 패킷 충돌

S. Jung, J.-H. Kim, and J. Kim, "Intelligent Extra Resource Allocation for Cooperative Awareness Message Broadcasting in Cellular-V2X Networks," *IEEE Transactions on Network and Service Management*, vol. 22, no. 2, pp. 1677-1689, 2025. DOI 10.1109/TNSM.2024.3496394

초록에서 C-V2X Mode 4의 SPS 방식이 CAM 전송 시 자원 스케줄링 충돌을 겪으며 이것이 성능을 저하시킨다고 직접 서술하고, 교통 밀도 변동에 실시간으로 대응해 충돌을 줄이는 방법을 제안합니다. 밀집 상황에서 CAM 브로드캐스트가 충돌을 일으킨다는 원고의 주장을 정확히 뒷받침합니다.

이미 검증된 문헌 중에서는 `maksimovski2026`(V2X 메시지 생성 규칙을 적응적으로 바꾸어 채널 부하를 줄이는 연구)이 이 자리에 더 잘 맞습니다. 중복 전송 억제라는 본 논문의 메커니즘과 직결되므로 우선 사용을 권합니다.

### 3-3. [6][8] 대체: 주기적 전송으로 인한 전력 낭비

J. Gong, J. Zhu, X. Chen, and X. Ma, "Sleep, Sense or Transmit: Energy-Age Tradeoff for Status Update With Two-Threshold Optimal Policy," *IEEE Transactions on Wireless Communications*, vol. 21, no. 3, pp. 1751-1765, 2022. DOI 10.1109/TWC.2021.3106395

이미 `related_works.json`에 검증된 상태로 들어 있는 항목입니다. 상태 갱신에서 에너지와 나이의 상충 관계를 다루고 최적 정책이 명시적인 대기 동작을 포함한다는 것을 증명하므로, 무분별한 주기 전송이 전력을 낭비한다는 주장의 근거로 [6]보다 훨씬 강합니다. 함께 검증된 `tang2020`(전력 제약 하 AoI 최소화)도 같은 자리에 쓸 수 있습니다.

### 3-4. [9] 대체: AoI 지향 스케줄링에서의 브랜치 네트워크와 중복 억제

X. Xie, T. Zhong, and H. Wang, "Scheduling for Maximizing the Information Freshness in Vehicular Edge Computing-Assisted IoT Systems," *IEEE Transactions on Intelligent Transportation Systems*, vol. 26, no. 3, pp. 4140-4151, 2025. DOI 10.1109/TITS.2024.3514099

초록에서 "브랜치 네트워크 방식으로 신경망 구조를 개선하여 출력층의 행동 수를 줄였고, 수렴을 가속하는 action masking 기법을 도입했다"고 명시합니다. 존재하지 않는 [9]에 적혀 있던 기술적 서술과 일치하므로, [9]는 이 논문이 변형된 결과로 판단됩니다. 실존 논문으로 그대로 교체하면 됩니다.

## 4. `writer/main.tex` 참고문헌 목록

| 키 | 기재된 서지 정보 | Crossref 조회 결과 | 등급 | 필요한 수정 |
|---|---|---|---|---|
| `kaul2012real` | Proc. IEEE INFOCOM, 2012, pp. 2187-2195 | 제목/저자 3인/INFOCOM 2012 일치. **페이지는 2731-2735** | B | 페이지를 2731--2735로 수정 |
| `ppo` | arXiv:1707.06347, 2017 | arXiv 프리프린트. Crossref DOI 10.48550/arXiv.1707.06347 | A(예외) | 프로젝트의 arXiv 금지 정책의 명시적 예외 항목입니다. 그대로 두되 예외임을 각주로 밝히기를 권합니다 |
| `sac` | ICML 2018, pp. 1856-1865 | PMLR v80 기준 정본 페이지는 1861-1870. 1856-1865는 dblp의 인쇄본 페이지 | B | `baselines_v2.json`은 1861--1870을 쓰고 있어 두 파일이 불일치합니다. 하나로 통일해야 하며 PMLR 표기(1861--1870) 권장 |
| `td3` | ICML 2018, 페이지 없음 | PMLR v80 1587-1596 | B | 페이지 1587--1596 추가 |
| `qi2025deep` | IEEE TVT, vol. 74, no. 1, 2025 | 제목/저자 7인/권/호/연도 일치. 페이지 1365-1378 | B | 페이지 1365--1378 추가 |
| `mlika2022deep` | IEEE TITS, vol. 23, no. 12, pp. 23597-23612, 2022 | 전 항목 일치 | A | 없음 |
| `arani2026resilient` | IEEE OJ-COMS, 2026 | 제목/저자 6인/연도 일치. vol. 7, pp. 7420-7437 | B | 권 7과 페이지 7420--7437 추가 |
| `azizi2024efficient` | IEEE TVT, vol. 73, no. 9, pp. 14009-14014, 2024 | 전 항목 일치 | A | 없음 |
| `lin2025optimization` | IEEE TVT, vol. 75, no. 6, pp. 11512-11527, **2025** | 전 항목 일치하나 **발행 연도는 2026년 6월호** | B | 연도를 2026으로 수정. `baselines_v2.json`도 같은 지적을 이미 기록해 두었습니다 |
| `zhang2025drl` | IEEE TGCN, vol. 9, no. 4, pp. 2144-2159, 2025 | 전 항목 일치 | A | 없음. Semantic Scholar가 2024로 표시하는 것은 early access 날짜이며 최종 호는 2025년입니다 |

이 외에 본문에서 인용하지만 `\bibitem`이 없는 키 6개가 있습니다(1-2 참조). 해당 키들은 전부 실존하지 않는 문헌이므로, `\bibitem`을 추가할 것이 아니라 3절의 대체 문헌으로 교체해야 합니다.

## 5. `librarian/related_works.json` (42건)

42건 전부 Crossref 조회로 제목, 저자 전원, 저널명, 권, 호, 페이지, 연도가 일치함을 확인했습니다. 등급은 모두 A입니다. 다만 아래 다섯 건은 기록해 둘 만한 부가 사항이 있습니다.

| 키 | 부가 사항 |
|---|---|
| `lopez2018` | Crossref는 저자 순서를 Lopez, Wiessner, Behrisch, ... 로 저장하고 있고 JSON은 Wiessner를 마지막에 둡니다. 출판본과 통상적인 인용 관례는 JSON 쪽이 맞으므로 수정하지 않아도 됩니다. JSON에 이미 같은 취지가 기록되어 있습니다 |
| `masson2016` | Crossref에는 페이지 대신 논문 번호 10226만 있습니다. JSON의 1934-1940은 dblp 출처이며 AAAI 인용 관례상 타당합니다 |
| `xu2023` | Crossref는 Neurocomputing 537권의 호를 "C"로 표기합니다. 실제 호 번호가 아니므로 JSON이 호를 비워 둔 것이 맞습니다 |
| `kahraman2024` | Crossref 표기는 İbrahim Kahraman, Alper Köse입니다. LaTeX에서 발음 구별 부호를 살릴지 여부만 결정하면 됩니다 |
| `chen2026` | 1-3에서 지적한 키 충돌 대상입니다. 서지 정보 자체는 정확합니다 |

2025년과 2026년으로 기재된 항목(`saad2025`, `li2026`, `chen2026`, `tadele2026`, `maksimovski2026`)은 모두 Crossref가 해당 연도로 확인해 주었습니다. `hong2026`처럼 DOI 토큰의 연도(2025)와 최종 호 연도(2026)가 다른 경우도 JSON이 최종 호 연도를 쓰고 있어 올바릅니다.

## 6. `librarian/baselines_v2.json`

### 6-1. 선정된 베이스라인 9건

| 키 | Crossref 조회 결과 | 등급 |
|---|---|---|
| `li2026` | IEEE TVT 75(7) 14775-14790, 2026. 저자 3인 일치 | A |
| `hong2026` | IEEE TVT 75(6) 11423-11437, 2026. 저자 5인 일치 | A |
| `chen2026` | IEEE TWC 25, 6790-6805, 2026. 저자 4인 일치. Crossref에 호 번호 없음(JSON이 비워 둔 것이 맞음) | A |
| `bai2024` | IEEE TVT 73(4) 5781-5795, 2024. 저자 4인 일치 | A |
| `cohen2025` | IEEE TWC 24(1) 228-243, 2025. 저자 4인 일치 | A |
| `parvini2023` | IEEE TVT 72(8) 9880-9896, 2023. 저자 5인 일치. Crossref도 4번째 저자를 "Bijan Abbasi"로 표기 | A |
| `schulman2017` | arXiv 프리프린트. 정책 예외 항목 | A(예외) |
| `haarnoja2018` | DOI 없음. PMLR v80 1861-1870 | A |
| `fujimoto2018` | DOI 없음. PMLR v80 1587-1596 | A |

### 6-2. `considered_and_rejected` 20건

19건의 DOI를 조회하여 전부 실존을 확인했고 서지 정보도 일치했습니다. 나머지 1건은 아래와 같습니다.

| 항목 | 등급 | 사유 |
|---|---|---|
| "Joint Optimization of Age of Information and Energy Consumption in NR-V2X System...", Sensors, DOI 10.3390/s24134338 | D | MDPI 발행물이라 프로젝트 정책상 조회 대상에서 제외했습니다. JSON도 이미 정책 위반을 이유로 배제해 두었으므로 실제 사용에는 영향이 없습니다 |

`10.1109/JIOT.2026.3702157`(Lai 외, Space Computing Power Networks)은 실존하지만 Crossref에 권/호/페이지가 없고 페이지가 "1-1"인 early access 상태입니다. JSON이 이 사유로 배제한 것이 타당합니다.

## 7. 인용 적합성 검토

초록을 직접 읽고 본문 주장과 대조한 결과입니다.

| 위치 | 원고의 주장 | 판정 |
|---|---|---|
| `main.tex` 74행 | 기존 AoI 인지 스케줄링 연구(`mlika2022deep`, `qi2025deep`, `zhang2025drl`)는 갱신 결정을 단순 이진 선택으로 다루거나 한 가지 차원만 고립적으로 최적화한다 | **부적합**. 세 논문의 초록이 모두 이 서술과 어긋납니다. `mlika2022deep`은 초록에서 "이산 RB 스케줄링 결정과 연속 전력 및 커버리지 최적화 결정을 포함하는 크고 혼합된 행동 공간"을 명시적으로 다룬다고 밝히고, 그 혼합 문제를 매칭과 DDPG로 분해해 푸는 것이 논문의 핵심 기여입니다. `qi2025deep`은 자원 할당과 RIS 위상 천이 제어를 동시에 수행합니다. `zhang2025drl`은 AoI와 에너지 소비를 함께 최적화합니다. 세 논문 모두 다차원 공동 최적화이므로 현재 문장은 인용된 문헌이 뒷받침하지 않습니다 |
| `main.tex` 112행 | 선행 연구는 대체로 완전 연속 또는 완전 이산 행동 공간을 채택한다 | **부적합**. 같은 원고가 인용하는 `mlika2022deep`이 혼합 행동 공간을 정면으로 다루고, `librarian` 인덱스에 검증되어 있는 `li2026`, `chen2026`, `hong2026`, `masson2016`, `fan2019`, `xu2023`도 전부 혼합 행동 공간 연구입니다. 혼합 행동 공간이 드물다는 서술은 유지할 수 없습니다. 기여를 혼합 행동 공간 자체가 아니라 갱신 간격 Δ를 그 공간에 추가한 것으로 다시 서술해야 합니다 |
| `main.tex` 103행 | Qi 외는 RIS 지원 IoV 네트워크를 위한 SAC 기반 자원 할당 기법을 제안했다 | **적합**. 초록이 SAC 알고리즘 사용을 명시합니다 |
| `main.tex` 104행 | Arani 외는 DRL을 이용한 복원력 있는 AoI 인지 최적화 프레임워크를 개발했다 | **적합**. 초록이 DDPG 기반 RAO 프레임워크임을 명시합니다. 다만 이 논문 기여의 절반은 차량 경로 계획이며, `baselines_v2.json`이 같은 이유로 이 논문을 베이스라인에서 배제했습니다. 관련 연구로 언급하는 것은 문제가 없으나 베이스라인으로 쓰는 것은 별개 문제입니다 |
| `main.tex` 100행 | AoI 개념은 상태 갱신 시스템을 위해 처음 도입되었다(`kaul2012real`) | **적합** |
| `main.tex` 105행 | Zhang 외는 C-V2X 기반 IoV에서 AoI와 에너지 소비를 공동 최적화했다 | **적합**. 초록과 일치합니다 |
| `main.tex` 108, 109행 | Azizi 외의 VLC-V2X 다중 에이전트 RL, Lin 외의 플래툰 스펙트럼 할당 | **적합**. 제목 및 서지 정보와 일치합니다 |
| `writer/references.json` [7] 요약 | "확률적 교통 상황에서 정보 신선도를 유지하기 위해 통신 자원을 동적으로 조정한다" | **부분 적합**. 자원 조정 부분은 맞으나, 이 논문의 핵심인 경로 계획과의 결합 및 복원력 페널티가 요약에서 빠져 있습니다 |

`main.tex` 282행의 베이스라인 목록과 `librarian/baselines_v2.json`의 베이스라인 목록이 완전히 다릅니다. 아래 `## 질의` 2번 항목에서 다룹니다.

## 8. 금지 출처에서만 발견된 문헌

없습니다. Scopus, MDPI, arXiv에서만 확인 가능하여 폐기한 문헌은 이번 검증에서 발생하지 않았습니다. 다만 아래 두 건은 기록해 둡니다.

- `schulman2017`(PPO)은 arXiv 프리프린트이며 `baselines_v2.json`이 기초 RL 논문 3편에 한정된 정책 예외로 명시해 둔 항목입니다.
- MDPI Sensors 논문(10.3390/s24134338)은 `baselines_v2.json`이 이미 정책 위반을 이유로 배제해 두었습니다.
- `User_Request.md` [3]의 유사 제목 논문은 SSRN 프리프린트뿐이라 대체안으로 채택하지 않았습니다.

## 9. 검증에 사용한 도구와 한계

- Crossref REST API로 DOI 직접 조회: 총 73회.
- Crossref `query.bibliographic` 서지 검색: 존재하지 않는 DOI 8건의 제목 실존 여부 확인 및 대체 문헌 탐색에 사용.
- Semantic Scholar Graph API: 인용 적합성 판정을 위한 초록 전문 확보에 사용(7건).
- 이 에이전트에는 Bash 도구가 없어 `lock_manager.py`와 `audit_logger.py`를 실행하지 못했습니다. 다만 이 문서는 신규 파일이며 기존 파일을 하나도 수정하지 않았으므로 락 경합은 발생하지 않았습니다. 감사 로그 기록은 Bash를 사용할 수 있는 에이전트가 대신 남겨 주어야 합니다.
- 에이전트 지침이 언급하는 `/home/imnyj/Workspace/paper4/references.json`은 존재하지 않습니다. 실제 경로는 `writer/references.json` 하나뿐입니다.
