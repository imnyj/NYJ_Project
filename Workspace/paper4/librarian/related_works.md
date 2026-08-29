# Related Works 문헌 목록 (총 42편)

> 작성: librarian agent, 2026-08-27
> 1차 29편 → **TWC 보강 후 42편**(2026-08-27 갱신)
> 목적: 본 논문(AoI-aware V2I uplink scheduling, hybrid action space, SMDP)의 **Related Works 절을 채우기 위한 지형도**.
> 이 파일은 비교 baseline 선정과 무관합니다. Baseline 9종은 형제 에이전트가 `baselines_v2.json` / `baselines_v2.md`에 별도로 정리합니다.

## 투고 목표 저널(IEEE TWC) 대응 현황

투고 목표가 **IEEE Transactions on Wireless Communications**라는 사실에 맞춰 2차 보강을 수행했습니다.

- **TWC 게재 문헌: 1편 → 12편** (전체 42편의 29%)
- 상위 게재처 합계: TWC 12 + JSAC 4 + IEEE/ACM ToN 4 + TIT 3 + TMC 1 = **24편(57%)**
- 보강은 코디네이터가 지정한 갈래 1·3·5에 집중했습니다. 갈래 1: 7→11, 갈래 3: 4→8, 갈래 5: 3→7, 갈래 4: 4→5(TWC 네이티브 하이브리드 액션 1편 추가).

| 게재처 | 편수 |
|---|---|
| IEEE Trans. Wireless Communications | **12** |
| IEEE/ACM Trans. Networking | 4 |
| IEEE J. Selected Areas in Communications | 4 |
| IEEE Trans. Vehicular Technology | 4 |
| IEEE Trans. Information Theory | 3 |
| IEEE Trans. Intelligent Transportation Systems | 2 |
| IEEE Internet of Things Journal | 2 |
| 그 외(TMC, TAC, T-IV, Access, Neurocomputing, Comput. Commun., TR-C, INFOCOM, ITSC, AAAI, IJCAI) | 각 1 |

## 검증 방식 (읽고 시작할 것)

모든 항목은 다음 2단계로 교차 검증했습니다.

1. **CrossRef REST API**(`api.crossref.org/works/{DOI}` 및 서지·제목 검색)로 제목·전체 저자·저널명·권·호·페이지·연도를 원본 메타데이터에서 직접 대조.
2. **`https://doi.org/{DOI}` 실제 해석(resolve)** — 42건 전부 정상 해석됨(IEEE Xplore는 HTTP 202, Elsevier/AAAI/IJCAI는 HTTP 200).

**추측으로 채운 필드는 하나도 없습니다.** CrossRef가 제공하지 않은 정보(학회 개최 도시, AAAI 페이지 번호, 이니셜만 저장된 저자의 full name)는 별도 출처를 명시했고, 확인하지 못한 것은 확인하지 못했다고 적었습니다.

## 피인용 수 기록 방식

JSON의 모든 항목에 `cited_by_count` 필드를 추가했습니다. **OpenAlex와 CrossRef 두 출처를 모두 기록**했으며(2026-08-27 조회), 파일 맨 끝에 42편 전체 표를 두었습니다.

- 두 수치가 크게 어긋나는 4건(`maatouk2020`, `yates2021`, `han2021`, `rajaraman2021`)은 OpenAlex가 레코드를 분할 저장해 과소 집계한 경우로 판단되며, 해당 항목의 `note`에 **어느 쪽이 신뢰할 만한지 명시**했습니다. 임의로 큰 값을 고르지 않았습니다.
- **2026년 게재 문헌 5편**(`tadele2026`, `li2026`, `maksimovski2026`, `chen2026`, 및 `arani2026`류)은 피인용이 0~2입니다. 게재 직후라 정상이며 품질 신호가 아니라고 각 항목에 적어 두었습니다.
- 저피인용 1건(`jiang2021`, 1~2회)은 주제 적합성만으로 채택했음을 해당 항목에 명시했습니다.

## 게재지 정책 준수

- arXiv 프리프린트 **0건**, MDPI **0건**. 검색 과정에서 다수 노출되었으나 전부 배제했습니다.
- 게재지는 IEEE / ACM / Elsevier(ScienceDirect) 로 한정되었습니다.
- **예외 적용 2건**(둘 다 ML 학회 정식 proceedings이며 arXiv 전용이 아니고 DOI가 해석됨): `masson2016`(AAAI-16), `fan2019`(IJCAI-19). 해당 항목에 명시했습니다.
- 3년 이내(2023~2026) 17편. 나머지는 `foundational: true` 정초 문헌이거나, TWC/JSAC의 정본급 스케줄링 이론 문헌입니다.

## 인용 형식 주의사항 (writer에게)

- 형식은 `Prompt.md` 규격을 그대로 따랐습니다(여는 따옴표 ``` `` ```, 닫는 따옴표 `''`, 페이지 en-dash `--`, **저자 전원 표기, et al. 금지**).
- 호(issue)가 없는 저널(IEEE Access, Neurocomputing, Computer Communications)은 `no.`를 생략했습니다.
- Transportation Research Part C는 논문번호제라 `Art. no. 103876`으로 표기했습니다.
- **`main.tex` 정합성 경고 2건**
  1. 현재 `main.tex:333`의 `kaul2012real` 항목은 **페이지가 틀렸습니다**. `pp.~2187--2195`로 적혀 있으나 CrossRef 원본은 **2731--2735**입니다. 본 파일의 `kaul2012`로 교체하거나 페이지만이라도 정정해야 합니다.
  2. 논문 ID 규칙(`Prompt.md`)은 `성+연도`이므로 `kaul2012real` → `kaul2012`가 맞습니다. 기존 키를 유지하려면 중복 등록이 되지 않도록 둘 중 하나만 남기십시오.

- **형제 에이전트 파일(`baselines_v2.json`)과의 중복 2건** — 최종 참고문헌 목록에서 `\bibitem`이 두 번 등록되지 않도록 주의하십시오.
  1. `li2026` (`10.1109/TVT.2026.3662431`) — 형제 에이전트가 **채택 baseline으로 선정**했습니다. ID와 DOI가 양쪽에서 독립적으로 동일하게 도출되었으므로 충돌이 아니라 동일 논문입니다. 본문에서는 Sec. II-C(하이브리드 액션 근거)와 실험 절(비교 대상) **양쪽에서 같은 키로 인용**하면 됩니다.
  2. `tadele2026` (`10.1109/TITS.2026.3667859`) — 형제 에이전트는 "다중 RSU fog 인프라를 전제해 우리 단일 RSU 환경에서 구현 불가"를 이유로 **baseline에서 기각**했습니다. 기각 사유는 구현 가능성에 관한 것이고 문헌적 관련성은 유효하므로, Related Works의 서술용 인용으로는 그대로 쓰면 됩니다.

---

# 1. AoI 이론 기반 (11편, TWC 2편 · JSAC 3편)

AoI가 무엇이고 왜 "많이 보낼수록 좋다"가 거짓인지를 세우는 층입니다. 본 논문 Introduction과 Sec. II-A의 뼈대가 됩니다.
**2차 보강분 4편**(`tang2020`, `gong2022`, `han2021`, `rajaraman2021`)은 아래 정초 문헌 뒤에 이어집니다 — 전력 제약·서브채널 배정·정보 품질이라는 우리 보상의 세 축을 각각 목표 저널권 문헌으로 받칩니다.

\bibitem{kaul2012} S. Kaul, R. Yates, and M. Gruteser, ``Real-time status: How often should one update?,'' \emph{Proc. IEEE INFOCOM}, Orlando, FL, USA, pp. 2731--2735, 2012.

DOI 검증 결과: `10.1109/INFCOM.2012.6195689` — CrossRef 메타데이터 일치(제목·저자 3인·pp. 2731-2735·INFOCOM 2012), doi.org 해석 정상. 개최지 Orlando, FL, USA(2012.3.25-30)는 INFOCOM 2012 공식 사이트로 확인. **foundational**.
인용 위치: Introduction 첫 문단 + Sec. II-A. **갱신 주기에 내부 최적점이 존재한다**는 본 논문의 대전제 자체. `main.tex`의 잘못된 페이지 번호를 이걸로 교체할 것.

\bibitem{costa2016} M. Costa, M. Codreanu, and A. Ephremides, ``On the age of information in status update systems with packet management,'' \emph{IEEE Transactions on Information Theory}, vol. 62, no. 4, pp. 1897--1910, 2016.

DOI 검증 결과: `10.1109/TIT.2016.2533395` — CrossRef 일치(TIT 62(4) 1897-1910, 2016), doi.org 해석 정상. **foundational**.
인용 위치: Sec. II-A, peak AoI를 도입하는 문장. RSU가 차량별 최신 상태만 유지하고 낡은 갱신을 큐에 쌓지 않는 설계를 정당화.

\bibitem{sun2017} Y. Sun, E. Uysal-Biyikoglu, R. D. Yates, C. E. Koksal, and N. B. Shroff, ``Update or wait: How to keep your data fresh,'' \emph{IEEE Transactions on Information Theory}, vol. 63, no. 11, pp. 7492--7508, 2017.

DOI 검증 결과: `10.1109/TIT.2017.2735804` — CrossRef 일치(저자 5인 전원, TIT 63(11) 7492-7508, 2017), doi.org 해석 정상. **foundational**.
인용 위치: Introduction + Sec. III(SMDP 정식화). **zero-wait가 최적이 아님을 증명**한 논문으로, 연속 변수 Δ와 중복 갱신 패널티에 대한 가장 강한 이론적 근거. 이 편이 없으면 "왜 그냥 항상 보내지 않는가"에 답할 수 없습니다.

\bibitem{kadota2018} I. Kadota, A. Sinha, E. Uysal-Biyikoglu, R. Singh, and E. Modiano, ``Scheduling policies for minimizing age of information in broadcast wireless networks,'' \emph{IEEE/ACM Transactions on Networking}, vol. 26, no. 6, pp. 2637--2650, 2018.

DOI 검증 결과: `10.1109/TNET.2018.2873606` — CrossRef 일치(저자 5인, ToN 26(6) 2637-2650, 2018), doi.org 해석 정상. **foundational**.
인용 위치: Sec. II-A. 다중 사용자 AoI 스케줄링의 정본이며 Whittle-index·Max-Weight 정책을 함께 제시. 우리 RSU를 "다수 경쟁 차량에 대한 중앙 AoI 스케줄러"로 자리매김할 때 사용.

\bibitem{tripathi2024} V. Tripathi and E. Modiano, ``A Whittle index approach to minimizing functions of age of information,'' \emph{IEEE/ACM Transactions on Networking}, vol. 32, no. 6, pp. 5144--5158, 2024.

DOI 검증 결과: `10.1109/TNET.2024.3452006` — CrossRef 일치(ToN 32(6) 5144-5158, 2024), doi.org 해석 정상.
인용 위치: Sec. II-A 마무리. 해석적 AoI 스케줄링의 최신 도달점. **대비 논지**로 쓰십시오 — index 정책은 명시적 age-cost 함수를 요구하지만, 우리 보상은 추정오차·전력·혼잡을 섞은 다목적이라 index화가 자명하지 않습니다.

\bibitem{maatouk2020} A. Maatouk, S. Kriouile, M. Assaad, and A. Ephremides, ``The age of incorrect information: A new performance metric for status updates,'' \emph{IEEE/ACM Transactions on Networking}, vol. 28, no. 5, pp. 2215--2228, 2020.

DOI 검증 결과: `10.1109/TNET.2020.3005549` — CrossRef 일치(저자 4인, ToN 28(5) 2215-2228, 2020), doi.org 해석 정상.
인용 위치: **Introduction에 크게, 그리고 보상식 정의부에 다시.** 본 논문 핵심 주장의 개념적 앵커입니다. AoII는 "수신측 추정이 실제와 어긋난 동안에만" 증가하므로, 적색 신호에 정지한 차량의 정보는 **낡되 틀리지 않습니다**. 우리 보상의 $e_t^2$ 항과 $\mathbb{I}_{redundant}$가 정확히 이 관점의 구현임을 이 인용으로 설명하십시오.

\bibitem{yates2021} R. D. Yates, Y. Sun, D. R. Brown, S. K. Kaul, E. Modiano, and S. Ulukus, ``Age of information: An introduction and survey,'' \emph{IEEE Journal on Selected Areas in Communications}, vol. 39, no. 5, pp. 1183--1210, 2021.

DOI 검증 결과: `10.1109/JSAC.2021.3065072` — CrossRef 일치(저자 6인, JSAC 39(5) 1183-1210, 2021), doi.org 해석 정상. **foundational**.
인용 위치: Sec. II-A 첫 문장. AoI 문헌 전체를 한 줄로 가리킬 때의 표준 서베이.

## ↓ 2차 보강분 (TWC/JSAC)

\bibitem{tang2020} H. Tang, J. Wang, L. Song, and J. Song, ``Minimizing age of information with power constraints: Multi-user opportunistic scheduling in multi-state time-varying channels,'' \emph{IEEE Journal on Selected Areas in Communications}, vol. 38, no. 5, pp. 854--868, 2020.

DOI 검증 결과: `10.1109/JSAC.2020.2980911` — CrossRef 일치(저자 4인, JSAC 38(5) 854-868, 2020), doi.org 해석 정상. **피인용: OpenAlex 166 / CrossRef 155** (본 목록 AoI 이론군 중 최다).
인용 위치: Sec. II-A, `kadota2018` 옆. **평균 전송전력 제약이 붙는 순간 age 최적 스케줄이 채널 기회주의적·임계 구조가 된다**는 것을 제약 MDP로 증명한 논문. 우리 보상의 $w_2 \cdot \text{Norm}(P_{tx})$ 항, 그리고 "전력은 갱신 결정과 함께 최적화되어야지 고정하면 안 된다"는 주장의 해석적 근거입니다.

\bibitem{gong2022} J. Gong, J. Zhu, X. Chen, and X. Ma, ``Sleep, sense or transmit: Energy-age tradeoff for status update with two-threshold optimal policy,'' \emph{IEEE Transactions on Wireless Communications}, vol. 21, no. 3, pp. 1751--1765, 2022.

DOI 검증 결과: `10.1109/TWC.2021.3106395` — CrossRef 일치(저자 4인, **TWC** 21(3) 1751-1765, 2022), doi.org 해석 정상. **피인용: OpenAlex 25 / CrossRef 28**.
인용 위치: Sec. II-A + $\mathbb{I}_{redundant}$ 정의부. **목표 저널(TWC) 논문이 "최적 정책에는 상태에 따라 선택되는 명시적 아무것도-하지-않기(sleep) 액션이 포함된다"를 증명**했습니다. 정지 차량에 대해 우리 중복 갱신 패널티가 유도하려는 바로 그 행동이며, 그것이 편의적 선택이 아니라 **최적**임을 보증합니다. 두 개의 임계값 구조라는 결과 형태도 우리 Δ 정책의 해석에 쓸 수 있습니다.

\bibitem{han2021} B. Han, Y. Zhu, Z. Jiang, M. Sun, and H. D. Schotten, ``Fairness for freshness: Optimal age of information based OFDMA scheduling with minimal knowledge,'' \emph{IEEE Transactions on Wireless Communications}, vol. 20, no. 12, pp. 7903--7919, 2021.

DOI 검증 결과: `10.1109/TWC.2021.3088719` — CrossRef 일치(저자 5인, **TWC** 20(12) 7903-7919, 2021), doi.org 해석 정상. **피인용: OpenAlex 2 / CrossRef 23 — 불일치.** OpenAlex 레코드가 분할된 것으로 보이며 **CrossRef의 23을 신뢰값으로 봅니다.**
인용 위치: Sec. II-A + system model의 4개 서브채널 도입부. 우리 액션의 **서브채널 축**을 목표 저널권 문헌으로 받칩니다. 주파수 자원을 어느 사용자에게 주느냐 자체가 AoI 결정이라는 점을 보이므로, `ch`가 별도 MAC 계층으로 빠지지 않고 Δ·p와 같은 액션 벡터에 들어가야 하는 이유가 됩니다.

\bibitem{rajaraman2021} N. Rajaraman, R. Vaze, and G. Reddy, ``Not just age but age and quality of information,'' \emph{IEEE Journal on Selected Areas in Communications}, vol. 39, no. 5, pp. 1325--1338, 2021.

DOI 검증 결과: `10.1109/JSAC.2021.3065061` — CrossRef 일치(저자 3인, JSAC 39(5) 1325-1338, 2021), doi.org 해석 정상. **피인용: OpenAlex 14 / CrossRef 38 — 불일치.** CrossRef 쪽이 더 완전한 집계로 판단됩니다.
인용 위치: Introduction, `maatouk2020` 옆에 나란히. **갱신마다 정보 가치가 다르면 age만 줄이는 것은 잘못된 목적함수**라는 스케줄링 이론 쪽의 논증. 정지 차량에 대한 갱신처럼 새 정보를 전혀 담지 않는 전송을 벌하는 것에 대한 형식적 근거를 `maatouk2020`과 다른 각도에서 보강합니다.

---

# 2. 차량 네트워크에서의 AoI (4편)

AoI를 V2X 맥락으로 끌어오는 층. 형제 에이전트가 고른 baseline 6종과 **겹치지 않도록** 의도적으로 다른 논문을 골랐습니다.

\bibitem{chen2020} X. Chen, C. Wu, T. Chen, H. Zhang, Z. Liu, Y. Zhang, and M. Bennis, ``Age of information aware radio resource management in vehicular networks: A proactive deep reinforcement learning perspective,'' \emph{IEEE Transactions on Wireless Communications}, vol. 19, no. 4, pp. 2268--2281, 2020.

DOI 검증 결과: `10.1109/TWC.2019.2963667` — CrossRef 일치(저자 7인 전원, TWC 19(4) 2268-2281, 2020), doi.org 해석 정상. (주의: `10.1109/TWC.2019.2963277`은 존재하지 않는 DOI입니다. 혼동 금지.)
인용 위치: Sec. II-A/II-B. **RSU가 다수 차량의 AoI를 DRL로 스케줄링한다는 구조의 가장 가까운 선행 연구**. 대비점을 분명히 쓸 것 — 이 논문은 주파수 대역 할당만 하지만 우리는 갱신 간격·전력·서브채널을 동시에 낸다.

\bibitem{abbas2023} Q. Abbas, S. A. Hassan, H. Jung, and M. S. Hossain, ``On minimizing the age of information in NOMA-based vehicular networks using Markov decision process,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol. 24, no. 12, pp. 15557--15567, 2023.

DOI 검증 결과: `10.1109/TITS.2022.3173351` — CrossRef 일치(저자 4인, T-ITS 24(12) 15557-15567, 2023), doi.org 해석 정상.
인용 위치: Sec. III(SMDP 동기 부여). 차량 AoI를 MDP로 세우고 전력을 결정변수로 둔 선행. **이 논문은 고정 슬롯 MDP이고 우리는 가변 Δ 때문에 semi-Markov가 된다**는 차이가 Sec. III의 논리 전개점입니다.

\bibitem{kahraman2024} I. Kahraman, A. Kose, M. Koca, and E. Anarim, ``Age of information in Internet of Things: A survey,'' \emph{IEEE Internet of Things Journal}, vol. 11, no. 6, pp. 9896--9914, 2024.

DOI 검증 결과: `10.1109/JIOT.2023.3324879` — CrossRef 일치(저자 4인, IoT-J 11(6) 9896-9914, 2024), doi.org 해석 정상. 참고: CrossRef 원본 표기는 `İbrahim Kahraman`, `Alper Köse`로 발음부호가 있습니다. 정확히 쓰려면 LaTeX에서 `K\"ose`로 조판하십시오.
인용 위치: Sec. II-A 도입부. 응용 AoI 문헌(비정보이론 계열)을 3년 이내 서베이 한 편으로 대신 가리킬 때.

\bibitem{tadele2026} S. B. Tadele, B. Kar, F. G. Wakgra, and M. Liyanage, ``Age-of-information aware mobility-based vehicular-fog formation using deep reinforcement learning,'' \emph{IEEE Transactions on Intelligent Transportation Systems}, vol. 27, no. 7, pp. 8238--8251, 2026.

DOI 검증 결과: `10.1109/TITS.2026.3667859` — CrossRef 일치(저자 4인, T-ITS 27(7) 8238-8251, 2026), doi.org 해석 정상. **단, 2026년 게재로 피인용 0건이라 IEEE가 권·호·페이지를 추후 정정할 여지가 있습니다.** 투고 직전 재확인 권장.
인용 위치: Sec. II-A. **이동성 상태를 조건으로 AoI 결정을 내리는 것이 현재(2026) 진행형 흐름**임을 보이는 데 사용. 우리 18차원 관측이 하는 일이 바로 그것입니다.

---

# 3. RL 기반 V2X 자원 할당 (8편, TWC 4편)

서브채널·전력을 RL로 정하는 계보. Sec. II-B의 본체입니다.
**2차 보강분 4편은 전부 TWC**입니다(`tan2021`, `zhang2021`, `guo2022`, `xu20232`). 목표 저널이 이 갈래의 본진이므로 가장 두껍게 보강했습니다.

\bibitem{ye2019} H. Ye, G. Y. Li, and B.-H. F. Juang, ``Deep reinforcement learning based resource allocation for V2V communications,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 68, no. 4, pp. 3163--3173, 2019.

DOI 검증 결과: `10.1109/TVT.2019.2897134` — CrossRef 일치(저자 3인, TVT 68(4) 3163-3173, 2019), doi.org 해석 정상. **foundational**.
인용 위치: Sec. II-B 첫 문단. **서브채널+전력이 V2X의 표준 액션 쌍**임을 세우는 원조. 우리 액션은 여기에 Δ를 더한 것이라고 쓰면 기여가 선명해집니다.

\bibitem{liang2019} L. Liang, H. Ye, and G. Y. Li, ``Spectrum sharing in vehicular networks based on multi-agent reinforcement learning,'' \emph{IEEE Journal on Selected Areas in Communications}, vol. 37, no. 10, pp. 2282--2292, 2019.

DOI 검증 결과: `10.1109/JSAC.2019.2933962` — CrossRef 일치(저자 3인, JSAC 37(10) 2282-2292, 2019), doi.org 해석 정상. **foundational**.
인용 위치: Sec. II-B. 다중 에이전트 정식화의 표준이자, **처리율 대 신뢰성의 가중합 보상**이라는 선례. 우리 4항 보상의 스칼라화도 구조적으로 같은 계열임을 밝힐 때 씁니다.

\bibitem{gui2024} J. Gui, L. Lin, X. Deng, and L. Cai, ``Spectrum-energy-efficient mode selection and resource allocation for heterogeneous V2X networks: A federated multi-agent deep reinforcement learning approach,'' \emph{IEEE/ACM Transactions on Networking}, vol. 32, no. 3, pp. 2689--2704, 2024.

DOI 검증 결과: `10.1109/TNET.2024.3364161` — CrossRef 일치(저자 4인, ToN 32(3) 2689-2704, 2024), doi.org 해석 정상.
인용 위치: Sec. II-B, 그리고 Sec. II-C에서 한 번 더. 최상위 저널의 3년 이내 논문으로 **V2X 결정이 본래 이산-연속 혼합**임을 보여줍니다. 보상의 에너지 항에 대한 직접 선행이기도 합니다.

\bibitem{saad2025} M. M. Saad, M. A. Tariq, M. Ajmal, D. Kim, and G. Srivastava, ``Federated multiagent reinforcement learning for resource allocation in NR-V2X mode 2,'' \emph{IEEE Internet of Things Journal}, vol. 12, no. 13, pp. 23402--23417, 2025.

DOI 검증 결과: `10.1109/JIOT.2025.3555195` — CrossRef 일치(저자 5인, IoT-J 12(13) 23402-23417, 2025), doi.org 해석 정상.
인용 위치: Sec. II-B + system model의 서브채널 정의부. 우리 환경이 모사하는 **C-V2X/NR-V2X 서브채널 경쟁 모형**의 근거이자, 분산 스케줄링 대 우리의 RSU 중앙 스케줄링을 대비시키는 지점.

## ↓ 2차 보강분 (전부 TWC)

\bibitem{tan2021} J. Tan, Y.-C. Liang, L. Zhang, and G. Feng, ``Deep reinforcement learning for joint channel selection and power control in D2D networks,'' \emph{IEEE Transactions on Wireless Communications}, vol. 20, no. 2, pp. 1363--1378, 2021.

DOI 검증 결과: `10.1109/TWC.2020.3032991` — CrossRef 일치(저자 4인, **TWC** 20(2) 1363-1378, 2021), doi.org 해석 정상. **피인용: OpenAlex 136 / CrossRef 130 — 보강분 중 최다.**
인용 위치: **Sec. II-B의 앵커**, 그리고 Sec. II-C에서 재인용. **이산 채널 선택 + 연속 전력**이라는 우리 액션 쌍을 상호 간섭 환경에서 학습한, 목표 저널 내 최고 피인용 선행 연구입니다. 이 논문을 기준선으로 두면 우리 기여를 "확립된 (채널, 전력) 쌍에 시간축 Δ를 추가한 것"으로 아주 깔끔하게 진술할 수 있습니다.

\bibitem{zhang2021} T. Zhang, K. Zhu, and J. Wang, ``Energy-efficient mode selection and resource allocation for D2D-enabled heterogeneous networks: A deep reinforcement learning approach,'' \emph{IEEE Transactions on Wireless Communications}, vol. 20, no. 2, pp. 1175--1187, 2021.

DOI 검증 결과: `10.1109/TWC.2020.3031436` — CrossRef 일치(저자 3인, **TWC** 20(2) 1175-1187, 2021), doi.org 해석 정상. **피인용: OpenAlex 104 / CrossRef 96.**
인용 위치: Sec. II-B. **이산 구조 결정(mode)과 연속 자원 결정을 무선에서 함께 학습하는 것이 관행**임을, 그리고 에너지 효율이 표준적 스칼라화 목적함수임을 목표 저널 문헌으로 보여줍니다. 우리 4항 보상은 이 틀의 확장이라고 서술하면 됩니다.

\bibitem{guo2022} S. Guo, B.-J. Hu, and Q. Wen, ``Joint resource allocation and power control for full-duplex V2I communication in high-density vehicular network,'' \emph{IEEE Transactions on Wireless Communications}, vol. 21, no. 11, pp. 9497--9508, 2022.

DOI 검증 결과: `10.1109/TWC.2022.3177199` — CrossRef 일치(저자 3인, **TWC** 21(11) 9497-9508, 2022), doi.org 해석 정상. **피인용: OpenAlex 35 / CrossRef 30.**
인용 위치: Sec. II-B + Sec. V(밀도 스윕 결과부). **물리적 설정이 우리와 가장 가까운 TWC 논문**입니다 — V2I 업링크, 전력 제어, 그리고 명시적인 고밀도 혼잡. 보상의 $w_3 \cdot \text{Norm}(C_{freq})$ 혼잡 항과, 교통 밀도를 바꿔가며 평가하는 우리 실험 설계 양쪽을 받쳐 줍니다.

\bibitem{xu20232} Y. Xu, K. Zhu, H. Xu, and J. Ji, ``Deep reinforcement learning for multi-objective resource allocation in multi-platoon cooperative vehicular networks,'' \emph{IEEE Transactions on Wireless Communications}, vol. 22, no. 9, pp. 6185--6198, 2023.

DOI 검증 결과: `10.1109/TWC.2023.3240425` — CrossRef 일치(저자 4인, **TWC** 22(9) 6185-6198, 2023), doi.org 해석 정상. **피인용: OpenAlex 48 / CrossRef 52.** **ID 주의**: `xu2023`은 이미 Yahao Xu(Neurocomputing) 항목이 점유하고 있어 `Prompt.md` 중복 규칙에 따라 **`xu20232`**를 부여했습니다.
인용 위치: Sec. II-B + Sec. IV(가중치 최적화 정당화부). **손으로 고정한 스칼라화 가중치는 약점이라는 주장을 우리와 똑같이 펴는 TWC 논문**입니다. 보상 가중치 $w_1 \sim w_4$를 휴리스틱 고정 대신 Optuna 탐색공간에 넣은 우리 결정을 직접 뒷받침합니다.

---

# 4. 하이브리드 / 파라미터화 액션 공간 RL (5편)

**현재 `main.tex`의 Sec. II-C는 인용이 0건인 세 문장짜리 문단입니다.** 리뷰어가 가장 먼저 지적할 곳이므로 이 4편으로 채우십시오.

\bibitem{masson2016} W. Masson, P. Ranchod, and G. Konidaris, ``Reinforcement learning with parameterized actions,'' \emph{Proc. 30th AAAI Conf. Artif. Intell. (AAAI)}, Phoenix, AZ, USA, pp. 1934--1940, 2016.

DOI 검증 결과: `10.1609/aaai.v30i1.10226` — doi.org가 AAAI OJS 레코드로 정상 해석(HTTP 200)되며 제목·저자 3인·AAAI vol. 30 no. 1·2016 확인. CrossRef도 동일. **페이지 1934-1940은 DBLP 출처** — AAAI OJS 자체는 페이지를 표기하지 않기 때문입니다. **foundational**.
**게재지 예외 적용**: ML 학회 정식 proceedings(AAAI). arXiv 전용이 아니고 DOI가 해석되므로 예외 조항으로 채택했습니다.
인용 위치: Sec. II-C + Sec. IV(정책 헤드 정의). **PAMDP(parameterized-action MDP)의 정식 정의** — 이산 액션을 고르고 그 액션의 연속 파라미터를 붙이는 구조가 곧 우리 액션 공간입니다.

\bibitem{fan2019} Z. Fan, R. Su, W. Zhang, and Y. Yu, ``Hybrid actor-critic reinforcement learning in parameterized action space,'' \emph{Proc. 28th Int. Joint Conf. Artif. Intell. (IJCAI)}, Macao, China, pp. 2279--2285, 2019.

DOI 검증 결과: `10.24963/ijcai.2019/316` — CrossRef 일치(저자 4인, IJCAI-19 proceedings, pp. 2279-2285, 2019), doi.org 해석 정상(HTTP 200). 개최지 Macao, China는 IJCAI-19 표준 표기.
**게재지 예외 적용**: ML 학회 정식 proceedings(IJCAI). 위와 동일한 사유.
인용 위치: Sec. II-C + Sec. IV-A. **H-PPO** — 공유 critic 위에 이산 head와 연속 head를 병렬로 두는 구조로, 우리 HybridPPO 아키텍처의 직접적 선행입니다. 이산화의 조합 폭발도, 연속 완화의 근사 오차도 피한다는 논지를 그대로 가져오면 됩니다.

\bibitem{xu2023} Y. Xu, Y. Wei, K. Jiang, L. Chen, D. Wang, and H. Deng, ``Action decoupled SAC reinforcement learning with discrete-continuous hybrid action spaces,'' \emph{Neurocomputing}, vol. 537, pp. 141--151, 2023.

DOI 검증 결과: `10.1016/j.neucom.2023.03.054` — CrossRef 일치(저자 6인, Neurocomputing vol. 537 pp. 141-151, 2023, Elsevier), doi.org 해석 정상(HTTP 200). Neurocomputing은 호 번호가 없어 `no.`를 생략했습니다.
인용 위치: Sec. II-C. 혼합 액션에서 **엔트로피 항을 분기별로 따로 유도하지 않으면 최대엔트로피 목적함수가 무너진다**는 점을 짚습니다. 우리 SAC 계열 하이브리드 baseline의 설계 근거이자, Sec. IV에서 우리가 이 문제를 어떻게 다뤘는지 밝혀야 할 이유.

\bibitem{li2026} J. Li, Q. Leng, and M. Cheng, ``Resource allocation in NOMA-V2X networks with multi-agent parameterized action space reinforcement learning,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 75, no. 7, pp. 14775--14790, 2026.

DOI 검증 결과: `10.1109/TVT.2026.3662431` — CrossRef 일치(저자 3인, TVT 75(7) 14775-14790, 2026), doi.org 해석 정상. 2026년 게재라 권·호·페이지가 추후 조정될 수 있으니 투고 직전 재확인 권장.
인용 위치: **Sec. II-C의 핵심 인용.** 파라미터화 액션 RL이 지금 V2X 자원 할당의 정답으로 통용되고 있음을 보이는 가장 좋은 증거로, 우리 하이브리드 액션 공간이 기이한 선택이 아니라 표준 관행임을 확립합니다.

## ↓ 2차 보강분 (TWC)

\bibitem{chen2026} H. Chen, H. Cui, P. Cao, Y. He, J. Li, I. W.-H. Ho, and V. C. M. Leung, ``Mobile-edge computing in SAGINs: A hybrid action space P-DDQN algorithm for joint offloading and resource allocation,'' \emph{IEEE Transactions on Wireless Communications}, vol. 25, pp. 19115--19130, 2026.

DOI 검증 결과: `10.1109/TWC.2026.3706356` — CrossRef 일치(저자 7인 전원, **TWC** vol. 25 pp. 19115-19130, 2026), doi.org 해석 정상. **CrossRef에 호 번호가 아직 없어** `no.`를 생략했습니다(2026년 게재분). 투고 직전 재확인 권장. **피인용: OpenAlex 0 / CrossRef 0 — 2026년 게재 직후라 정상이며 품질 신호가 아닙니다.**
인용 위치: **Sec. II-C, `li2026` 옆.** 목표 저널 대응 관점에서 **이번 보강에서 가장 값어치 있는 한 편**입니다. TWC가 파라미터화 액션(P-DQN 계열) 기법을 직접 게재한다는 사실을 보여주므로, 우리 하이브리드 액션 공간이 ML 문헌에서 억지로 끌어온 외래 요소가 아니라 **투고 저널의 정상 범위 안**이라는 점을 리뷰어에게 확립할 수 있습니다. 갈래 4는 원래 IEEE 저널 근거가 `li2026`(TVT) 한 편뿐이었는데 이제 목표 저널 자체의 사례가 생겼습니다.

---

# 5. Semi-Markov / 이벤트 트리거 / 가변 간격 의사결정 (7편, TWC 4편)

Δ가 연속 변수라는 사실이 **왜 formulation을 semi-Markov로 만드는지**, 그리고 **왜 주기적 샘플링이 최적이 아닌지**를 받치는 층. Sec. III에서 "SMDP"라고 선언하는 문장에는 반드시 인용이 붙어야 합니다.
**코디네이터 요청에 따라 이 갈래를 집중 보강했습니다(3편 → 7편, 추가분 4편 전부 TWC).** 다만 아래 "정직한 공백 보고"에 적었듯 *SMDP 그 자체*는 보강하지 못했고, 대신 **원격 추정·이벤트 기반 전송**이라는 인접 축을 목표 저널 문헌으로 두껍게 채웠습니다.

\bibitem{sun2020} Y. Sun, Y. Polyanskiy, and E. Uysal, ``Sampling of the Wiener process for remote estimation over a channel with random delay,'' \emph{IEEE Transactions on Information Theory}, vol. 66, no. 2, pp. 1118--1135, 2020.

DOI 검증 결과: `10.1109/TIT.2019.2937336` — CrossRef 일치(저자 3인, TIT 66(2) 1118-1135, 2020), doi.org 해석 정상.
인용 위치: 보상의 오차 항 $e_t^2$ 정의부. **MSE 최적 샘플러는 signal-aware이며 추정오차에 대한 임계 정책 형태이고, age 최적(신호 무관) 샘플러를 엄밀히 능가한다**는 결과. 즉 우리가 raw age가 아니라 추정오차를 벌하는 것, 그리고 Δ를 상태 의존 가변으로 두는 것 양쪽을 동시에 정당화합니다. `sun2017`과 묶어 Sec. III의 이론적 척추로 쓰십시오.

\bibitem{xu2020} L. Xu, Y. Mo, and L. Xie, ``Remote state estimation with stochastic event-triggered sensor schedule and packet drops,'' \emph{IEEE Transactions on Automatic Control}, vol. 65, no. 11, pp. 4981--4988, 2020.

DOI 검증 결과: `10.1109/TAC.2020.3004328` — CrossRef 일치(저자 3인, TAC 65(11) 4981-4988, 2020), doi.org 해석 정상.
인용 위치: Sec. II에 이벤트 트리거 단락을 짧게 신설하고 거기에 + Sec. III. **"보내지 않는 것 자체가 정보이며, 추정 품질을 떨어뜨리지 않고도 전송률을 크게 줄일 수 있다"**는 제어이론 쪽의 정본 진술 — 중복 갱신 패널티가 학습으로 찾아내기를 기대하는 바로 그 메커니즘입니다.

\bibitem{perezromero2020} J. Perez-Romero and O. Sallent, ``Optimization of multitenant radio admission control through a semi-Markov decision process,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 69, no. 1, pp. 862--875, 2020.

DOI 검증 결과: `10.1109/TVT.2019.2951322` — CrossRef 일치(저자 2인, TVT 69(1) 862-875, 2020), doi.org 해석 정상.
인용 위치: **Sec. III에서 SMDP를 정의하는 문장에 직접.** 무선 자원 관리 안에서 SMDP를 실제로 세운 사례로, 결정 시점이 고정 클럭이 아니라 사건으로 촉발되고 **체류시간(sojourn time)이 가치함수에 들어가는** 방식의 템플릿입니다. 우리 Δ가 semi-Markov를 유발한다는 주장의 방법론적 선례.

> **정직한 공백 보고**: 이 thread는 7개 중 가장 얇습니다(3편). "SMDP + AoI + 무선"을 정확히 다루면서 IEEE/ACM/Elsevier에 실린 3년 이내 논문을 CrossRef 서지 검색·제목 검색·웹 검색으로 반복 탐색했으나, 조건을 모두 만족하는 후보는 arXiv 프리프린트(예: *Semi-Markov Decision Process Framework for Age of Incorrect Information Minimization*)로만 존재해 배제했습니다. `perezromero2020`(2020, 5년 경계)이 정식 게재된 SMDP-무선 문헌 중 가장 적합한 대체입니다. 더 최신 근거가 필요하면 이 항목만 추가 조사할 가치가 있습니다.

---

# 6. 이동성 예측과 정지 상태 활용 (4편)

**중복 갱신 패널티의 물리적 정당화층.** "정지가 추론 가능하다"는 우리 주장이 근거 없는 가정이 아님을 이 4편으로 보증합니다.

\bibitem{sun2022} P. Sun, D. Nam, R. Jayakrishnan, and W. Jin, ``An eco-driving algorithm based on vehicle to infrastructure (V2I) communications for signalized intersections,'' \emph{Transportation Research Part C: Emerging Technologies}, vol. 144, Art. no. 103876, 2022.

DOI 검증 결과: `10.1016/j.trc.2022.103876` — CrossRef 일치(저자 4인, TR-C vol. 144 art. 103876, 2022, Elsevier), doi.org 해석 정상(HTTP 200). 이 저널은 페이지 범위 대신 논문번호를 씁니다.
인용 위치: **Sec. II-D + $\mathbb{I}_{redundant}$ 정의부.** 교통공학 쪽에서 **신호 위상·정지선 거리·큐 상태만으로 차량이 정지할지와 언제 다시 움직일지를 사전에 계산**할 수 있음을 미시 시뮬레이션으로 검증한 논문. 우리 관측벡터의 `tls_state`, `tls_dist`, `n_queue`가 왜 그 세 개여야 하는지에 대한 외부 근거가 정확히 이것입니다. `scenario.md`의 "신호등 상태, 남은 시간, 앞 차량 대수, 출발 시점 추론" 항목과 1:1로 대응합니다.

\bibitem{yao2023} H. Yao, X. Li, and X. Yang, ``Physics-aware learning-based vehicle trajectory prediction of congested traffic in a connected vehicle environment,'' \emph{IEEE Transactions on Vehicular Technology}, vol. 72, no. 1, pp. 102--112, 2023.

DOI 검증 결과: `10.1109/TVT.2022.3203906` — CrossRef 일치(저자 3인, TVT 72(1) 102-112, 2023), doi.org 해석 정상.
인용 위치: Sec. II-D + system model의 RSU 추정기 서술부. RSU가 갱신 사이에 차량 상태를 외삽(dead-reckoning)하는 단계를 받쳐줍니다. 특히 **우리 정지 차량이 실제로 존재하는 정체·stop-and-go 구간에서 그 외삽이 정확하다**는 점을 보인 논문이라 논지가 정확히 맞습니다.

\bibitem{ding2023} Z. Ding and H. Zhao, ``Incorporating driving knowledge in deep learning based vehicle trajectory prediction: A survey,'' \emph{IEEE Transactions on Intelligent Vehicles}, vol. 8, no. 8, pp. 3996--4015, 2023.

DOI 검증 결과: `10.1109/TIV.2023.3266446` — CrossRef 일치(저자 2인, T-IV 8(8) 3996-4015, 2023), doi.org 해석 정상.
인용 위치: Sec. II-D 도입 문장. 예측기들을 일일이 나열하지 않고 "차량의 미래 상태는 맥락으로부터 예측 가능하다"를 한 줄로 처리할 때의 서베이 인용.

\bibitem{maksimovski2026} D. Maksimovski, A. Festag, and C. Facchi, ``Adaptive message generation rules for V2X maneuver coordination service,'' \emph{IEEE Access}, vol. 14, pp. 6417--6437, 2026.

DOI 검증 결과: `10.1109/ACCESS.2026.3652364` — CrossRef 일치(저자 3인, IEEE Access vol. 14 pp. 6417-6437, 2026), doi.org 해석 정상. IEEE Access는 호 번호가 없어 `no.`를 생략했습니다.
인용 위치: Sec. II-D + 중복 갱신 패널티 논의. **표준화 진영의 대응물** — 고정 주기 대신 위치·방향·동역학 변화량이 임계를 넘을 때만 메시지를 생성하는 규칙이 V2X에서 중복 억제의 공인된 방식임을 보이고 채널 부하 감소량까지 정량화합니다. 우리의 학습된 Δ가 이겨야 할 **규칙 기반 비교 대상**으로 언급하기에도 좋습니다.

---

# 7. SUMO 기반 V2X 평가 방법론 (3편)

"진짜 시뮬레이션을 썼다"는 주장을 방어하는 층. Sec. V-A에 배치하십시오.

\bibitem{sommer2011} C. Sommer, R. German, and F. Dressler, ``Bidirectionally coupled network and road traffic simulation for improved IVC analysis,'' \emph{IEEE Transactions on Mobile Computing}, vol. 10, no. 1, pp. 3--15, 2011.

DOI 검증 결과: `10.1109/TMC.2010.133` — CrossRef 일치(TMC 10(1) 3-15, 2011), doi.org 해석 정상. **주의**: CrossRef에는 저자가 이니셜(`C Sommer; R German; F Dressler`)로만 저장되어 있습니다. Christoph / Reinhard / Falko라는 full name은 게재 논문 원문 기준이며, bibitem은 IEEE 관례대로 이니셜 표기를 썼습니다. **foundational**.
인용 위치: Sec. V-A 첫 문장. Veins의 원논문이자, 더 중요하게는 **도로 교통과 네트워크 시뮬레이션이 양방향 결합되어야 한다**는 방법론적 논거입니다. 합성 이동성 트레이스가 아니라 실제 SUMO 미시 시뮬레이션 위에 올린 우리 선택을 정당화합니다.

\bibitem{lopez2018} P. A. Lopez, M. Behrisch, L. Bieker-Walz, J. Erdmann, Y.-P. Fl\"otter\"od, R. Hilbrich, L. L\"ucken, J. Rummel, P. Wagner, and E. Wie\ss ner, ``Microscopic traffic simulation using SUMO,'' \emph{Proc. 21st IEEE Int. Conf. Intell. Transp. Syst. (ITSC)}, Maui, HI, USA, pp. 2575--2582, 2018.

DOI 검증 결과: `10.1109/ITSC.2018.8569938` — CrossRef 일치(제목·ITSC 2018·pp. 2575-2582), doi.org 해석 정상. 개최지 Maui, HI, USA(2018.11.4-7)는 DBLP와 ITSC 2018 공식 사이트로 확인. **주의**: CrossRef는 Wiessner를 두 번째로 나열하지만 게재본의 저자 순서는 Lopez 이후 알파벳순이며, 본 bibitem은 이 표준 순서를 따랐습니다. 움라우트는 LaTeX 명령으로 복원해 두었습니다. **foundational**.
인용 위치: Sec. V-A. SUMO가 공식적으로 요구하는 인용이며, netconvert 생성 네트워크·0.1 s step-length·libsumo 구동이라는 우리 설정의 근거입니다.

\bibitem{raviglione2024} F. Raviglione, C. M. Risma Carletti, M. Malinverno, C. Casetti, and C. F. Chiasserini, ``ms-van3t: An integrated multi-stack framework for virtual validation of V2X communication and services,'' \emph{Computer Communications}, vol. 217, pp. 70--86, 2024.

DOI 검증 결과: `10.1016/j.comcom.2024.01.022` — CrossRef 일치(저자 5인, Computer Communications vol. 217 pp. 70-86, 2024, Elsevier), doi.org 해석 정상(HTTP 200). **주의**: CrossRef에 given name이 이니셜로만 저장되어 있어 bibitem도 이니셜로 표기했습니다. full name은 독립 확인하지 못했으므로 단정하지 않았습니다. 이 저널도 호 번호가 없어 `no.`를 생략했습니다.
인용 위치: Sec. V-A에서 `sommer2011`과 나란히. SUMO + ns-3 결합에 ETSI ITS-G5 / C-V2X / LTE 다중 스택과 CAM/DENM/CPM 계층을 얹은 3년 이내 프레임워크로, **SUMO를 물리계층 모델과 결합하는 것이 V2X 스케줄링 연구의 공인된 평가 방식**임을 보증합니다. 우리 5.9 GHz Rayleigh 페이딩 SINR + 서브채널 모델의 정당화에도 함께 쓰십시오.

---

# 부록: writer를 위한 배치 요약

| 절 | 현재 상태 | 투입할 인용 |
|---|---|---|
| Introduction | `kaul2012` 1건뿐 | + `sun2017`, `maatouk2020` (핵심 주장 앵커) |
| II-A AoI in Vehicular Networks | baseline 4건 나열만 | + `yates2021`, `costa2016`, `kadota2018`, `tripathi2024`, `kahraman2024`, `chen2020`, `tadele2026` |
| II-B Resource Allocation in V2X | baseline 2건 나열만 | + `ye2019`, `liang2019`, `gui2024`, `saad2025` |
| II-C Hybrid Action Spaces | **인용 0건, 3문장** | + `masson2016`, `fan2019`, `xu2023`, `li2026` |
| II-D (신설 권장) Mobility Prediction & Redundant Updates | 없음 | `ding2023`, `sun2022`, `yao2023`, `maksimovski2026` |
| II-E (신설 권장) Event-Triggered / SMDP | 없음 | `xu2020`, `sun2020`, `perezromero2020` |
| III Problem Formulation (SMDP) | 인용 없이 SMDP 선언 | `perezromero2020`, `abbas2023`, `sun2017`, `sun2020` |
| V-A Simulation Setup | 없음 | `lopez2018`, `sommer2011`, `raviglione2024` |
