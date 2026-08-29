# 문헌 재조사 사양 (2026-08-27)

사용자 지시로 기존 baseline 문헌 목록을 **전량 폐기**하고 처음부터 재조사. 이 문서는 조사 기준과 산출물 위치를 기록하여, 다음 작업자(agy 포함)가 같은 기준으로 이어받을 수 있게 한다.

## 폐기된 목록 (재사용 금지)
`Conversation.md` 4번 섹션, `run_all.py` 스텁, `writer/main.tex`에 남아 있는 아래 6종은 **사용자가 명시적으로 폐기**했다. 코드에 구현된 적도 없고(9개 baseline 파일 전체를 DOI·기법명으로 grep한 결과 일치 0건), 재조사 결과 독립적으로 재선정되지 않는 한 인용해서는 안 된다.
- SAC-RIS (TVT 2024, 10.1109/TVT.2024.3452790)
- DDPG-CV2X (TITS 2022, 10.1109/TITS.2022.3190799)
- DDPG-Resilient (OJCOMS 2026, 10.1109/OJCOMS.2026.3707734)
- MARL-VLC (TVT 2024, 10.1109/TVT.2024.3392738)
- Platoon-DRL (TVT 2025, 10.1109/TVT.2025.3643923)
- DRL-IoV (TGCN 2025, 10.1109/TGCN.2025.3531902)

## 게재처 규칙 (엄격)
- **허용**: IEEE, ACM, Elsevier/ScienceDirect, Springer 상위, Nature 계열.
- **배제**: arXiv 프리프린트, MDPI, Scopus 전용 및 약탈적 저널.
- **예외**: 보편적으로 인용되는 기초 문헌에 한함. PPO는 arXiv에만 존재하고 SAC/TD3는 ICML 프로시딩이며, 원조 AoI 논문은 INFOCOM이다. 예외를 적용한 항목은 반드시 명시할 것.

## 조사 범위

### A. 비교 baseline 9종 → `baselines_v2.json` / `baselines_v2.md`
- **최신 3편**: 2026년 게재. V2X/IoV/차량 네트워크의 AoI 인지 스케줄링 또는 자원 할당 DRL. 2026년 논문으로 3편을 채우지 못할 경우에만 2025년으로 대체하되 대체 사실과 검색 경위를 명시.
- **유사 3편**: 방법론적으로 가장 가까운 연구. AoI 인지 스케줄링, 갱신 주기/샘플링률 제어, 송신 전력 제어, 서브채널 할당. 2023~2026 선호.
- **기본 3편**: PPO, SAC, TD3. **SB3(Stable-Baselines3)로 구현**하며 하이브리드 액션 공간에 맞게 래핑.

### B. Related Works 문헌 15~25편 → `related_works.json` / `related_works.md`
7개 갈래로 분산 조사:
1. AoI 이론 기초 (peak AoI, AoI 최적 샘플링/스케줄링, Whittle index)
2. 차량 네트워크의 AoI
3. RL 기반 V2X 자원 할당 (전력 제어, 자원블록 할당, 모드 선택, RSU 보조 스케줄링)
4. 하이브리드/파라미터화 액션 공간 RL — 우리 액션이 하이브리드이므로 필수
5. Semi-Markov / 이벤트 트리거 / 가변 주기 의사결정 — Δ가 SMDP를 만들므로 정식화 근거
6. 이동성 예측 및 정지 상태 활용 — 중복 갱신 패널티의 정당화 근거
7. SUMO 기반 V2X 평가 방법론

각 항목마다 우리 논문의 어떤 주장을 뒷받침하는지(`supports_claim`) 명시.

## 구현 가능성 기준 (인상적임보다 우선)
최신·유사 6편은 **우리 환경에서 재구현 가능해야** 한다. 우리 환경: 18차원 RSU 관점 관측, 하이브리드 액션(연속 Δ + 연속 p + 이산 ch), 단일 RSU 스케줄링, SUMO + Rayleigh SINR. RIS 하드웨어, 가시광 채널, 다중 RSU 연합학습, 우리가 시뮬레이션하지 않는 데이터 양식을 요구하는 논문은 아무리 좋아도 **탈락**시키고 `considered_and_rejected`에 사유와 함께 기록. 사용자가 뒤집을 수 있도록.

## 인용 형식 (`Prompt.md` 준수)
- 논문 ID = 제1저자 성 + 년도 소문자. 중복 시 숫자 접미사: `nam2026`, `nam20262`, `nam20263`.
- **저자는 et al. 없이 전원 표기.**
- 저널: `\bibitem{ID} Author1, Author2, ... and AuthorN, ``Title,'' \emph{Journal Name}, vol. xx, no. xx, pp. xx--xx, 20xx.`
- 학회: `\bibitem{ID} Author1, Author2, ... and AuthorN, ``Title,'' \emph{Conference Name}, City, Country, pp. xx--xx, 20xx.`
- LaTeX 여는 따옴표는 백틱 2개, 닫는 따옴표는 어포스트로피 2개, 페이지 범위는 `--`.

## 검증 원칙
모든 DOI는 실재해야 하며 주장한 논문으로 실제 연결되어야 한다. 제목·저자·게재처·권·호·페이지·연도를 독립적으로 교차 확인한다. **어떤 필드도 날조 금지.** 확인 불가한 필드는 비워 두고 `doi_verified`에 사유를 남긴다. 짧고 정직한 목록이 길고 날조된 목록보다 낫다 — 이 프로젝트는 이미 한 차례 문헌 날조로 신뢰를 잃은 이력이 있다.

## 산출물 위치
| 파일 | 내용 |
|---|---|
| `librarian/baselines_v2.json` | 비교 baseline 9종 구조화 데이터 + `considered_and_rejected` |
| `librarian/baselines_v2.md` | 위 9종의 `\bibitem` + DOI 검증 결과 + 구현 가능성 (Conversation.md 4번에 붙여넣을 형태) |
| `librarian/related_works.json` | Related Works 문헌, 갈래별 분류 + `supports_claim` |
| `librarian/related_works.md` | 위 문헌의 `\bibitem` + DOI 검증 결과 + 인용 위치 |

JSON의 `summary` 필드는 2~3문장으로, 나중에 다시 찾을 때 한눈에 파악되도록 작성한다.

---

# 조사 완료 및 Claude Code 독립 검증 결과 (2026-08-27 16:0x)

librarian 에이전트 2기의 보고를 그대로 신뢰하지 않고, **38편 전수를 Crossref REST API로 재조회하여 제목·연도·권·호·페이지를 자동 대조**했다. 검증 스크립트: `coder/etc/scripts/verify_bibliography.py`.

```
TOTAL 38: OK=34  DIFF=1  FAIL=1  SKIP=2
```
**날조 0건.** 예외 3건은 전부 정상 사유:
- `sun2022` DIFF — Elsevier 논문번호를 IEEE 표기 관례대로 `Art. no. 103876`으로 적은 것이며 Crossref의 `103876`과 동일. 수정 불필요.
- `schulman2017` FAIL — arXiv DOI(`10.48550/*`)는 Crossref가 아니라 DataCite 소관이라 조회 실패. 오류 아님.
- `haarnoja2018`, `fujimoto2018` SKIP — ICML 2018 프로시딩은 DOI가 존재하지 않음. 에이전트가 날조하지 않고 `doi_verified: false`로 정직하게 표기했으며 PMLR v80 페이지로 검증함.

## 확정된 비교 baseline 9종 (`baselines_v2.json`)

| 분류 | ID | 논문 | 게재처 | 검증 |
|---|---|---|---|---|
| 최신 | `li2026` | Resource Allocation in NOMA-V2X Networks With **Multi-Agent Parameterized Action Space** RL | TVT 75(7) 14775–14790, 2026 | OK |
| 최신 | `xu2026` | **AoI and Energy-Aware Resource Scheduling** for Crowdsensing: Hybrid RL | TVT 75(8) 18102–18115, 2026 | OK |
| 최신 | `hong2026` | Joint **Sub-Band Allocation and Power Control** for Dynamic Vehicular Networks, MADRL | TVT 75(6) 11423–11437, 2026 | OK |
| 유사 | `bai2024` | AoI-Aware Joint Scheduling and Power Allocation in ITS | TVT 73(4) 5781–5795, 2024 | OK |
| 유사 | `mlika2022` | DDPG to Minimize AoI in Cellular V2X | TITS 23(12) 23597–23612, 2022 | OK |
| 유사 | `parvini2023` | AoI-Aware RA for Platoon-Based C-V2X, Multi-Agent Multi-Task RL | TVT 72(8) 9880–9896, 2023 | OK |
| 기본 | `schulman2017` | PPO | arXiv (SB3 구현) | DOI 존재 |
| 기본 | `haarnoja2018` | SAC | ICML 2018, PMLR 80:1861–1870 (SB3) | DOI 없음(정상) |
| 기본 | `fujimoto2018` | TD3 | ICML 2018, PMLR 80:1587–1596 (SB3) | DOI 없음(정상) |

2026년 논문 3편을 실제로 확보했으며 2025년 대체는 없었다. 인용 형식은 9건 전부 `Prompt.md` 규칙(bibitem ID 일치, et al. 미사용, LaTeX 따옴표, `--` 페이지 범위, 저널 vol./no.) 자동 검사 통과.

**주목**: `li2026`은 파라미터화 액션 공간을, `hong2026`은 서브밴드 할당 + 전력 제어를 다루어 우리 하이브리드 액션(연속 Δ·p + 이산 ch)과 구조적으로 정확히 대응한다. 비교군으로서 설득력이 가장 높다.

**한계로 명시된 것**:
- `xu2026`은 V2X가 아니라 모바일 크라우드센싱(TVT 게재). 채택 사유는 2026년 논문 중 **샘플링 주기 자체를 학습하는 유일한 사례**로 우리 Δ와 같은 결정 변수라는 점. 도메인 차이는 리뷰어 지적 가능.
- 최신 3편이 전부 TVT. TITS·IoT-J·OJCOMS·Elsevier Vehicular Communications를 모두 조사했으나 2026년 후보는 전부 인프라 사유로 탈락. 게재처 다양성이 필요하면 **가장 아까운 탈락**인 `10.1109/OJCOMS.2026.3707734`(RAO, OJ-COMS 7:7420–7437, 2026)를 사용자가 뒤집을 수 있음 — resiliency 기반 AoI 패널티는 이식 가능하나 핵심 기여가 **차량 경로 계획**과 결합되어 우리 RSU가 제어하지 않는 액션임.
- `mlika2022`는 2022년으로 선호 구간(2023~2026) 밖. 매칭+DDPG 분해 대비를 제공하는 2023년 이후 대안이 없어 유지.
- 탈락 10건 중 1건은 초록을 구하지 못해 제목의 platoon 표현만으로 판단했다고 스스로 한계를 밝힘.

**폐기 목록 관련 확인**: 옛 목록 6종 중 재조사에서 독립적으로 살아남은 것은 `mlika2022` 하나뿐이다. 나머지는 방법론·인프라 사유로 탈락. 더불어 **옛 목록에 연도 오류 2건**이 있었다 — Qi et al.은 2024가 아니라 2025, Lin et al.은 2025가 아니라 2026.

## Related Works 29편 (`related_works.json`)

7개 갈래 분포: AoI 이론 7 / 차량 AoI 4 / RL 기반 V2X 자원할당 4 / 하이브리드 액션 RL 4 / SMDP·이벤트트리거 3 / 이동성 예측 4 / SUMO 평가 방법론 3. 29편 전부 Crossref 대조 통과, arXiv·MDPI 0건.

**갈래 5(SMDP)가 가장 얇다(3편).** SMDP + AoI + 무선을 동시에 만족하면서 IEEE/ACM/Elsevier에 5년 내 게재된 논문을 찾지 못했다. 최적 후보(*Semi-Markov Decision Process Framework for Age of Incorrect Information Minimization*)가 arXiv 전용이라 배제했고, `perezromero2020`(2020, 5년 경계)을 대체로 넣었다. 3장의 SMDP 주장을 강하게 뒷받침하려면 이 갈래만 추가 조사할 가치가 있다.

**게재처 예외 2건 적용**: `masson2016`(AAAI-16), `fan2019`(IJCAI-19). 둘 다 정식 ML 학회 프로시딩이며 DOI가 해석됨.

**Crossref에서 얻지 못해 다른 출처로 보강한 필드**(전부 파일 내 명시): `masson2016` 페이지(AAAI OJS가 페이지 미표기 → DBLP), 학회 개최 도시(공식 사이트/DBLP), `sommer2011`·`raviglione2024` 이름 전체(Crossref가 이니셜만 보관 — `raviglione2024`는 추정하지 않고 이니셜 유지), `lopez2018` 저자 순서(Crossref와 출판본 불일치, 출판본 순서 채택 후 표시).

## `writer/main.tex`의 확인된 결함 (Claude 직접 검증)

1. **인용 페이지 오류**: `main.tex:333`이 `kaul2012real`을 `pp.~2187--2195`로 인용하나, Crossref 원본(`10.1109/INFCOM.2012.6195689`, "Real-time status: How often should one update?", IEEE INFOCOM 2012, Orlando, FL, USA)의 실제 페이지는 **2731--2735**이다.
2. **참고문헌 전체가 폐기된 옛 목록**: `qi2025deep`, `arani2026resilient`, `azizi2024efficient`, `lin2025optimization`, `zhang2025drl` 등 사용자가 폐기 지시한 항목으로만 구성되어 있어 전면 교체 필요.
3. **논문 ID가 `Prompt.md` 규약 위반**: `kaul2012real`→`kaul2012`, `ppo`→`schulman2017`, `sac`→`haarnoja2018`, `td3`→`fujimoto2018`, `qi2025deep`→`qi2025` 형태여야 한다(제1저자 성+연도).
4. **2장 C절 "Hybrid Action Spaces"에 인용이 0건**. 세 문장이 근거 없이 서술되어 있어 리뷰어의 첫 표적이 될 부분이다. Related Works 갈래 4가 이를 위해 존재하며 `li2026`이 핵심 인용이다.

## 중복 및 재확인 사항
- `li2026`은 baseline이자 Related Works 갈래 4의 핵심 인용이다. **bibitem을 두 번 등록하지 않도록** 주의.
- `tadele2026`은 baseline에서는 탈락(단일 RSU 환경에 부적합)했으나 Related Works의 서사 맥락으로는 유효하다.
- 2026년 항목(`li2026`, `tadele2026`, `xu2026`, `hong2026`, `maksimovski2026`)은 IEEE가 권·호·페이지를 조정할 수 있으므로 **투고 직전 재확인** 필요. `verify_bibliography.py`를 다시 돌리면 된다.

## 통합 절차 (조사 완료 후)
librarian 산출물은 **자동 반영하지 않는다.** Claude Code가 검토한 뒤:
1. `Conversation.md` 4번 섹션을 `baselines_v2.md` 내용으로 교체.
2. `writer/main.tex`의 참고문헌을 교체.
3. 선정된 9종 구현 착수. 기본 3종은 SB3 사용.
4. `run_all.py` 복원 (`backup/run_all.py.bak.20260827_103334` 기준, `total_steps=200000` 유지, 새 `model_cls` 주입 방식 반영).
