# HOORL 원논문의 오프라인 사전학습 자료 출처 조사

조사일: 2026-09-06
담당: librarian
대상 문헌: Xu et al., "AoI and Energy-Aware Resource Scheduling for Crowdsensing: A Hybrid Reinforcement Learning Framework," IEEE Transactions on Vehicular Technology, vol. 75, no. 8, pp. 18102-18115, 2026. DOI 10.1109/TVT.2026.3675626 (프로젝트 내 식별자 `xu2026`)

---

## 1. 결론

**오프라인 데이터셋의 출처를 확인하지 못했습니다.** 제시된 다섯 가지 선택지 가운데 어느 것인지 판정할 근거를 찾지 못했습니다.

다만 판정 불가의 성격을 정확히 구분해서 적어야 합니다. 선택지 5번은 "본문에 명시되지 않음"인데, 이번 조사에서 원논문 본문에는 접근하지 못했으므로 본문에 명시되어 있는지 여부 자체를 확인할 수 없었습니다. 따라서 이번 조사가 확정할 수 있는 명제는 다음 한 문장으로 한정됩니다.

> 초록 전문, 색인 서지 정보, 이 논문을 인용한 문헌의 서술이라는 세 범위 안에서는 오프라인 데이터셋의 출처를 특정하는 서술이 존재하지 않습니다.

본문에 기재되어 있으나 초록에 올라오지 않았을 가능성은 배제되지 않았습니다. 실제로 오프라인 강화학습 논문이 데이터 수집 절차를 시뮬레이션 설정 절에만 적고 초록에는 생략하는 사례가 흔하므로, 이 가능성이 오히려 높다고 보는 편이 타당합니다.

---

## 2. 직접 확인한 사실

### 2.1 서지 정보의 재검증

Crossref REST API를 직접 조회하여 다음을 확인했습니다. 제목, 저자 6인 전원, 게재지 IEEE Transactions on Vehicular Technology, 75권 8호, 18102쪽부터 18115쪽까지, 2026년입니다. 모든 항목이 `librarian/baselines_v2.json`의 기존 기록과 일치했으므로 서지 정보를 수정할 사유는 발생하지 않았습니다. Crossref 레코드에는 초록 필드가 존재하지 않습니다.

### 2.2 초록 전문

두 개의 독립적인 색인에서 초록을 받아 서로 대조했으며 문면이 일치했습니다. 아래는 원문 그대로입니다.

> "Information freshness plays a pivotal role in time-sensitive applications within Mobile Crowdsensing (MCS) networks and is quantitatively characterized by the Age of Information (AoI). This paper considers an MCS network where end users submit requests to an edge server (ES) for status updates monitored by a group of energy-acquiring mobile devices operating with periodic sensing. In such a system, the ES must schedule transmissions among heterogeneous mobile devices while optimizing their sensing cycles to better align with user demands. A critical challenge arises from the mobile devices' limited battery capacity, which is not directly observable by the ES. The objective is to minimize the average weighted sum of required AoI and the energy consumption of the mobile devices. To address this issue, we model the problem as a Partially Observable Markov Decision Process (POMDP) and leverage reinforcement learning (RL) methods to find a solution. Key challenges include sparse rewards and a mismatch between user demands and mobile device sensing frequencies. To address these issues, we propose an innovative Hybrid Offline-Online Reinforcement Learning (HOORL) algorithm, which combines the strengths of offline and online RL techniques. Finally, simulation results show that the proposed HOORL algorithm achieves superior performance compared to relevant scheduling schemes, effectively reducing system costs while maintaining stable battery levels in mobile devices."

이 초록에는 데이터셋, 궤적, 행동 정책, 전문가 시연, 로그, 벤치마크에 해당하는 어휘가 하나도 등장하지 않습니다. 오프라인 단계에 관한 서술은 마지막에서 두 번째 문장의 "combines the strengths of offline and online RL techniques" 한 구절이 전부입니다.

### 2.3 약어의 정식 확장형

초록이 HOORL을 "Hybrid Offline-Online Reinforcement Learning"으로 명시합니다. 이것은 원문에서 직접 확인한 사항이므로 원고에서 약어를 처음 쓸 때 이 확장형을 그대로 사용할 수 있습니다.

### 2.4 오프라인 단계를 도입한 이유

초록이 "Key challenges include sparse rewards and a mismatch between user demands and mobile device sensing frequencies"라고 적고, 바로 이어서 "To address these issues, we propose ... HOORL"이라고 서술합니다. 즉 오프라인과 온라인을 결합한 동기가 희소 보상과 요구 대비 센싱 빈도의 불일치라는 두 가지 난점에 있다는 사실은 직접 확인되었습니다. 데이터를 어디서 모았는지는 여전히 나오지 않습니다.

### 2.5 색인 키워드

OpenAlex가 부여한 개념 목록은 스케줄링, 강화학습, 자원 관리, 프로세서 스케줄링처럼 일반적인 항목뿐이며 데이터 출처를 시사하는 항목은 없습니다. IEEE가 논문에 인쇄하는 저자 키워드와 IEEE 용어 목록은 확보하지 못했습니다.

---

## 3. 확인하지 못한 것과 시도한 경로

### 3.1 오프라인 데이터셋의 출처

선택지 1번부터 5번까지 어느 것도 지지하거나 배제할 근거를 얻지 못했습니다.

### 3.2 오프라인 단계와 온라인 단계의 연결 방식

부수 질문에 대해서도 근거를 얻지 못했습니다. 확보한 서술은 "combines the strengths of offline and online RL techniques"뿐이며, 이 표현은 사전학습한 가중치를 온라인 초기값으로 넘기는 방식과 오프라인 데이터를 온라인 재생 버퍼에 섞어 함께 학습하는 방식을 모두 포괄합니다. 두 방식은 하이브리드 강화학습 문헌에서 모두 통용되므로 이 문장 하나로는 구별되지 않습니다. 따라서 우리 이식이 채택한 가중치 인계 방식이 원논문과 같은지 다른지는 판정할 수 없습니다.

### 3.3 이번 조사에서 시도한 경로와 결과

| 경로 | 결과 |
|---|---|
| IEEE Xplore 문서 페이지 `ieeexplore.ieee.org/document/11442965` | 본문이 비어 있는 응답이 돌아왔습니다. 자바스크립트로 그려지는 페이지라 추출되지 않습니다. |
| IEEE Xplore 초록 페이지 `/abstract/document/11442965` | HTTP 418로 차단되었습니다. |
| IEEE Xplore 메타데이터 REST 종단점 `/rest/document/11442965/metadata` | HTTP 418로 차단되었습니다. |
| Crossref REST API 직접 조회 | 서지 정보는 전부 확인되었으나 초록 필드가 없습니다. |
| 색인 A의 초록 조회 | 초록 전문을 확보했습니다. 데이터 출처 서술은 없습니다. |
| 색인 B의 초록 조회 | 초록 전문을 확보했고 색인 A와 문면이 일치했습니다. 데이터 출처 서술은 없습니다. |
| 원논문의 참고문헌 목록 조회 | 출판사가 참고문헌 필드를 제거해 두어 조회되지 않았습니다. 색인 B에서도 참조 목록이 비어 있습니다. |
| 이 논문을 인용한 문헌 조회 | 인용 문헌이 단 한 편이며, 이종 클라우드 데이터센터의 가상 머신 마이그레이션을 다루는 학회 논문입니다. HOORL을 설명하는 서술이 없어 간접 근거로 쓸 수 없습니다. |
| 저자별 선행 연구 조사 (제1저자) | 크라우드센싱과 AoI를 다룬 논문이 두 편 더 있으나 각각 프라이버시 보호 유인 설계와 가격 결정 및 매칭 기반 과제 할당이며 강화학습을 쓰지 않습니다. HOORL의 학회 선행판은 존재하지 않습니다. |
| 저자별 선행 연구 조사 (교신 저자로 추정되는 계정) | 논문 23편을 확인했으나 오프라인 강화학습을 쓴 선행 연구가 없습니다. HOORL의 학회 선행판도 없습니다. |
| IEEE Xplore, ACM DL, ScienceDirect, Elsevier로 범위를 제한한 주제어 검색 3회 | 원논문이나 HOORL을 서술한 문헌이 검색되지 않았습니다. |
| 공개 접근본 존재 여부 확인 | 접근 상태가 CLOSED로 표시됩니다. 합법적으로 열람 가능한 무료 전문이 존재하지 않습니다. |

세 가지 사실이 조사 실패의 구조적 원인입니다. 첫째, 2026년 8월호 게재분이라 인용이 사실상 없습니다. 둘째, 출판사가 참고문헌 목록을 색인에서 제거해 두었습니다. 셋째, 공개 접근본이 없습니다. 이 세 가지가 겹치면 초록 바깥의 어떤 정보도 유료 열람 없이는 얻을 수 없습니다.

### 3.4 금지 출처에서만 발견된 문헌

이번 조사에서 금지 출처에만 존재하여 버린 문헌은 없습니다. 다만 하이브리드 오프라인-온라인 강화학습을 주제어로 검색했을 때 arXiv 게재본 다수가 결과에 섞여 나왔습니다. 이들은 HOORL 원논문과 무관한 일반 방법론 문헌이고 금지 출처이므로 근거로 채택하지 않았고 이 보고서 어디에도 반영하지 않았습니다.

---

## 4. 추정 (직접 확인이 아님)

아래는 확인된 사실이 아니라 정황에 근거한 추정입니다. 4장 전체를 판단 근거로 삼을 때는 3장의 확인 사실과 반드시 구별해 주십시오.

### 4.1 추정의 내용

원논문의 오프라인 데이터가 상태와 무관한 균등 무작위 정책만으로 수집되었을 가능성은 상대적으로 낮고, 어느 정도 성능이 있는 행동 정책이 개입했을 가능성이 있습니다.

### 4.2 추정의 근거

근거는 초록이 밝힌 동기 한 가지입니다. 초록은 오프라인 단계를 도입한 이유를 희소 보상이라고 적었습니다. 강화학습에서 희소 보상을 오프라인 데이터로 완화하는 통상적인 논리는, 무작위 탐색으로는 보상이 발생하는 상태에 거의 도달하지 못하므로 보상에 도달하는 궤적을 미리 확보해 둔다는 것입니다. 이 논리가 성립하려면 데이터셋에 보상 신호가 실제로 담겨 있어야 하고, 그러려면 수집에 쓰인 정책이 무작위보다는 나아야 합니다. 따라서 선택지 2번인 학습된 정책이나 전문가 궤적, 혹은 3번인 휴리스틱 스케줄러 로그일 가능성이 1번보다 높다고 볼 여지가 있습니다.

### 4.3 추정의 신뢰도

**낮음입니다.** 이 추정을 원고의 서술 근거로 쓰는 것은 권장하지 않습니다. 신뢰도를 낮게 잡는 이유가 셋 있습니다.

첫째, 이 논문의 문제 설정에서 보상은 요구 AoI와 에너지 소비의 가중합이므로 매 결정마다 값이 발생하는 조밀한 보상입니다. 그런데도 초록이 희소 보상을 난점으로 든 것을 보면, 이 논문이 말하는 희소성이 통상적인 희소 보상 문제와 다른 것을 가리킬 가능성이 있습니다. 예를 들어 배터리가 고갈되거나 사용자 요구가 충족되는 사건이 드물게 발생하는 상황을 그렇게 표현했을 수 있습니다. 그렇다면 4.2의 논리 연쇄가 성립하지 않습니다.

둘째, 무작위 정책으로 수집한 데이터로 희소 보상을 다루는 접근도 문헌에 존재합니다. 데이터의 품질이 아니라 분량과 상태 공간 피복률로 문제를 완화하는 방향입니다.

셋째, 이 추정은 오직 초록의 한 문장에서 도출되었으며 이를 뒷받침하는 독립적인 문헌 근거가 하나도 없습니다. 인용 문헌도 저자의 선행 연구도 근거를 보태 주지 못했습니다.

### 4.4 추정하지 않은 것

선택지 4번인 공개 벤치마크 데이터셋에 대해서는 지지 근거도 반박 근거도 없습니다. 다만 이 논문의 환경이 저자들이 직접 정의한 모바일 크라우드센싱 모형이고 에너지 수확 기기의 배터리 동역학을 포함하므로, 이 환경에 맞는 공개 벤치마크가 존재할 가능성은 낮습니다. 이것 역시 추정이며 확인된 사실이 아닙니다.

---

## 5. 우리 이식과의 대조에서 남는 위험

팀 리드가 제기한 문제, 즉 HOORL이 낮은 성적을 낸 원인이 방법의 한계인지 이식 조건의 차이인지 구별되지 않는다는 우려는 이번 조사로 해소되지 않았습니다. 원논문의 수집 조건을 모르므로 우리 조건이 그보다 불리한지 대등한지 판정할 수 없습니다.

참고로 코드 쪽 기록을 확인한 결과, `coder/src/hoorl_offline.py`가 데이터셋 메타데이터에 기록하는 행동 정책의 종류는 `fixed_period_uniform_channel_power`이며, 소스 주석은 서브채널을 균등 이산 분포에서, 전력을 해당 구간의 균등 분포에서 뽑고 Delta는 고정 주기로 두되 지터 설정에 따라 로그 균등 대역에서 뽑는다고 설명합니다. 이것은 `baselines_v2.json`의 `implementability` 항목이 규정한 "문서화된 고정 주기 휴리스틱"과 부합하는 형태이며, 팀 리드가 전한 "상태와 무관한 균등 무작위 정책"이라는 표현과도 어긋나지 않습니다. 다만 구현이 실제로 그 규격대로 동작하는지는 문헌 담당이 판정할 사항이 아니므로 구현 담당의 확인이 필요합니다.

원고에 반영할 사항을 정직하게 정리하면 다음과 같습니다. 우리는 원논문의 오프라인 데이터 수집 절차를 확인하지 못했고, 그래서 문서화된 고정 주기 휴리스틱을 행동 정책으로 삼아 자체적으로 데이터를 수집했습니다. 이 선택은 오프라인 강화학습이 전제하는 행동 정책 기지성을 만족시키기 위한 것이며 그 자체로는 방법론적으로 타당합니다. 그러나 원논문이 더 좋은 데이터를 썼을 경우 우리 재현이 원논문보다 불리한 조건에서 돌았을 가능성이 남습니다. 결과 서술에서 HOORL의 성적을 해석할 때 이 불확실성을 명시하는 편이 안전합니다.

---

## 6. 남은 유일한 경로

초록 바깥의 정보를 얻으려면 원논문 본문을 유료로 열람하는 방법밖에 없습니다. 소속 기관이 IEEE Xplore 구독 권한을 보유하고 있다면 사용자가 직접 로그인하여 PDF를 내려받은 뒤 그 파일 경로를 알려 주는 방식이 가장 확실합니다. 확인해야 할 지점은 시뮬레이션 설정 절에서 오프라인 데이터셋의 크기와 수집에 쓴 정책을 서술한 문단, 그리고 알고리즘 절에서 오프라인 학습 결과를 온라인 단계로 넘기는 절차를 서술한 문단, 이렇게 두 곳입니다.

---

## 7. JSON 갱신 사항

이번 작업에서 `librarian/baselines_v2.json`을 포함한 어떤 문헌 메타데이터 파일도 수정하지 않았습니다. 서지 정보를 재검증한 결과 기존 기록과 완전히 일치하여 수정 사유가 없었고, 초록 전문과 약어 확장형을 추가하는 것은 팀 리드의 요청 범위를 벗어나므로 임의로 반영하지 않았습니다. 반영이 필요하면 지시해 주십시오.

## 8. 프로토콜 준수 상황

이 보고서 파일은 신규 생성이며 기존 파일을 덮어쓰지 않았으므로 백업 격리 대상이 발생하지 않았습니다. `lock_manager.py`의 락 획득과 `audit_logger.py`의 기록은 수행하지 못했습니다. 문헌 담당 에이전트에게는 셸 실행 도구가 부여되어 있지 않아 두 스크립트를 실행할 수단이 없기 때문입니다. 기록이 필요하면 셸을 쓸 수 있는 에이전트가 대신 남겨 주어야 합니다.
