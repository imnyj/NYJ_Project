# Paper4 LaTeX 원고 검토 보고서 — IEEE TWC 제출 수준 지향

> **대상 에이전트**: Antigravity Writer Subagent
> **검토 파일**: `Workspace/paper4/writer/final/main.tex` (1,238줄, v1.1, 2026-05-13). 참고: `draft/main.tex`(804줄)는 구버전.
> **작업 규칙(.rules/writer.md 준수)**: 학술 문체 유지 / AI적 표현 금지(과장어·과도 부사·과도한 `---`·`:`·`;`·불필요 괄호 / 문단 최소 5문장 / itemize·enumerate 미지시 시 산문) / **CSV 실측 로드, 수치 임의 추정 금지** / critic 검토 / 모호하면 사용자에게 질의.
> **핵심 결론**: 이 원고는 **REMO-DQN이 아니라 TinyMLP-AI-DCC(behavior cloning + MCU 배포) 논문**이며, 메타데이터상 대상 학술지가 **IEEE IoT-J**다. 게다가 **Proposed 결과가 전부 비어 있는 미완성본**이라 현재 상태로는 어떤 학술지에도 제출 불가다. "문장 교정"이 아니라 **방향 재정렬 → 결과 산출 → 정합성 수리** 순의 재작업이 필요하다.

---

## ⛔ 사전 결정 사항 (Writer가 착수 전 사용자 확인 필수 — .rules/writer.md 마지막 규칙)

이 원고는 두 갈래 중 하나로 확정되어야 하며, 방향에 따라 재작성 범위가 완전히 달라진다.

- **(A) TinyMLP 유지 → IoT-J/TVT 계열 제출**: 현재 원고의 서사와 일치. 단, TWC 지향은 포기. 결과만 채우면 되므로 재작업 최소.
- **(B) REMO-DQN으로 전환 → TWC 지향**: 사용자가 앞서 확정한 방향. 서론·기여도·관련연구·제안기법·수식·기여표를 **전면 재작성**해야 함. 현재 TinyMLP 원고는 §II 관련연구, §III 시스템모델, 평가 프레임(지표·베이스라인·시나리오)만 재활용 가능.

**중요**: 현재 원고는 본문에서 DRL을 명시적으로 **회피 대상**으로 기술한다(초록·서론·결론의 "circumventing/avoiding the convergence instability of deep reinforcement learning"). REMO-DQN(하이브리드 DRL)으로 가면 **이 문장들이 자기모순**이 되므로 반드시 삭제·역전해야 한다. 아래 코멘트는 (B) 전환을 기본 전제로 작성하되, (A)에도 공통 적용되는 항목은 `[공통]`으로 표기한다.

---

## 🔴 BLOCKER — 제출 자체를 막는 무결성/구조 문제

### B-1. 방법론 불일치: 원고 전체가 TinyMLP-AI-DCC, 확정 방향은 REMO-DQN
- **위치**: 전 문서. 제목(L64), 초록, 서론 기여도 C1–C3(L~250), §IV 제안기법(TinyMLP 아키텍처·behavior cloning·오라클), §VI 결론.
- **문제**: 제안 모델·학습 패러다임·기여도가 모두 TinyMLP/BC/오라클 기반이다. REMO-DQN(ResNet+MoE+Dueling+Double DQN) 서사와 양립 불가.
- **지침((B))**: 제목·초록·기여도·§IV를 REMO-DQN 기준으로 재작성. 학습 패러다임을 "오라클 대상 behavior cloning"에서 "온라인/오프라인 심층강화학습"으로 교체. "MCU 4KB 배포"를 핵심 기여로 두던 프레임을 제거하거나 부차 기여로 강등.

### B-2. 대상 학술지 메타데이터가 IoT-J로 고정 `[공통]`
- **위치**: 파일 상단 주석 L2("IEEE IoT-J submission"), `\markboth{IEEE Internet of Things Journal,...}`(L74–75).
- **문제**: 사용자 목표는 IEEE TWC. `\documentclass[journal]{IEEEtran}`은 공용이라 유지 가능하나 `\markboth`·주석·페이지헤더 문구가 IoT-J.
- **지침**: `\markboth`를 `IEEE Transactions on Wireless Communications`로 교체. 상단 주석의 학술지·버전 기록 갱신.

### B-3. Proposed 결과가 전부 비어 있음(“Pending”) — 미완성 원고 `[공통]`
- **위치**: §V Table II `tab:baseline_main`, Proposed 행 전부 `---/Pending`(L~1000). §V-D "Pending Evaluation Items"(L~1070). 상단 주석 "§V baseline-only, Proposed row = Pending".
- **문제**: 논문에 **제안기법 결과가 하나도 없다.** Ablation·민감도·시나리오도 전부 미실시. 이 상태로는 리뷰 불가(desk-reject).
- **지침**: 코드 검토 보고서(별첨 `paper4_code_review_report.md`)의 C-1·C-2·C-3 수리 후 REMO-DQN을 실제 평가하여 표를 채운다. 결과 CSV(`writer/data/`)를 **직접 로드**해 기입(.rules/writer.md: 임의 추정 금지).

### B-4. 초록이 원고에 없는 결과를 정량 주장(과대광고) `[공통]`
- **위치**: 초록("reduces average AoI by up to 35\% and CBR by up to 20\% ... under 4KB"), 결론 Limitations가 스스로 "이 수치는 empirical이 아니라 oracle 기반 projection"이라 자백(L~1180).
- **문제**: 초록은 확정 결과처럼 단정하는데 실제 표는 비어 있음 → 심각한 무결성 위반. 리뷰어가 초록 대비 빈 표를 즉시 포착.
- **추가 내적모순**: BL-A(Reactive) AoI=393.81ms. 35% 감소 시 ≈256ms인데, 이는 최대 전송(BL-D, Fixed10Hz)의 신선도 하한 321.96ms보다도 낮다. **전송률을 낮추면서 최대율 AoI 하한을 깨는 것은 물리적으로 불가**. 주장 자체가 성립 불가.
- **지침**: 실측 결과 확보 전까지 초록의 모든 정량 주장 삭제. 확보 후 실측치로만 기술하고, AoI 개선폭이 BL-D 하한을 넘지 않도록 물리적 정합성 확인.

### B-5. 시뮬레이터·표준 인용의 허위 기술 `[공통]`
- **B-5a. 표준을 2차 문헌으로 오인용(반복)**: `ETSI EN 302 637-2`/`EN 302 571`을 설명하며 `\cite{Bhattacharyya2024}`를 붙임(서론 L~205, §III "Under ETSI EN 302 637-2~\cite{Bhattacharyya2024}", §III-B ReactDCC 등 다수). Bhattacharyya2024는 IEEE TVT 논문이지 ETSI 표준이 아니다. **실제 ETSI 표준 문서(EN 302 637-2 v1.4.1, EN 302 571, TS 103 175 등)를 직접 bibitem으로 추가**하고 표준 서술의 인용을 전부 교체.
- **B-5b. 사용하지 않은 시뮬레이터를 사용한 것처럼 기술**: §III·§V-A가 "SumoNetSim 1.1.5로 IEEE 802.11p MAC/PHY 시뮬레이션"이라 명시. 그러나 실제 `code/sim_engine.py`는 자체 단순 모델(`reception_probability`, `compute_cbr`)을 구현하며 SumoNetSim을 쓰지 않는다. **재현성·무결성 문제**. 실제 채널 모델(거리기반 pathloss + Nakagami-m 근사, TX airtime 기반 CBR)을 있는 그대로 기술하고, SumoNetSim 언급 삭제. `.rules/writer.md`의 "연산 주체·변수 도출·전달" 규칙에 맞춰 실제 파이프라인을 서술.
- **B-5c. 에셋 파일명 불일치**: `generated.sumocfg`/`generated.rou.xml`을 "pre-generated fixed asset"이라 기술하나, 코드는 시드별로 `netgenerate`+랜덤트립을 **런타임 생성**한다(sim_engine `generate_routes`). "동일 mobility realization으로 공정비교"라는 주장과 배치. 실제 생성 방식으로 정정하거나, 정말 고정 에셋을 쓰도록 코드를 바꾼 뒤 그에 맞춰 기술.

### B-6. 모든 기법 PDR=100%가 논문의 문제의식을 스스로 반증 `[공통]`
- **위치**: §V Table II — BL-A~BL-D 전부 `PDR=100.00%`, Fixed10Hz(채널 포화)조차 100%.
- **문제**: 논문의 전제는 "고밀도에서 전송 폭주 → MAC 충돌 → PDR 하락". 그런데 모든 기법이 완벽한 100%면 **혼잡 문제가 존재하지 않는다**는 뜻이 되어 동기 자체가 붕괴. 이는 코드 검토에서 지적한 충돌 모델 취약성(collision_factor 미미, PDR 관대 산정)의 결과. 리뷰어 즉시 반박.
- **지침**: 채널/충돌 모델을 밀도에 따라 PDR이 실제로 하락하도록 보정(코드 보고서 M-8 국소 CBR, 충돌 모델 강화와 연계). 보정 후 PDR이 기법·밀도별로 구분되는 값이 나와야 표가 설득력을 가진다.

---

## 🟠 TWC 적합성 격차 — 통신·이론적 깊이 부족

IEEE TWC는 무선통신 이론 비중이 높은 저널이다. "더 큰 신경망을 적용했다"는 응용 서사만으로는 부적합 판정 위험이 크다. 다음을 보강해야 리뷰 라운드에 진입할 수 있다.

- **T-7. 통신-이론적 기여 부재**: 현재 기여는 (i)프로토콜 오버레이 (ii)학습 프레임 (iii)MCU 배포로, 모두 시스템/응용 성격이다. TWC 지향이면 **AoI–CBR 트레이드오프의 해석적 특성화**, **간섭·충돌 하 PDR/AoI의 근사 해석 모델**, 또는 **제어정책의 안정성/최적성 경계** 중 최소 하나의 분석적 결과가 필요. 순수 실험 + 자명한 Proposition 1로는 부족.
- **T-8. Proposition 1이 공허**: "그리드를 전수 탐색하므로 전역최적"은 정의상 자명한 tautology다. 정식 명제로 세울 가치가 없다. 삭제하거나, 실질적 명제(예: myopic 정책과 장기 최적 사이의 후회(regret) 상한, 혹은 특정 채널 가정 하 AoI 기대값 형태)로 대체.
- **T-9. 시스템 모델의 통신 서술 부족(.rules/writer.md 본문 요령 위반)**: §III가 "누가 어떤 변수로 연산하고 결과가 누구에게 어떻게 전달되는지"의 프로토콜 관점 서술이 얕다. CAM 페이로드 구성, 상태벡터 각 원소의 측정·전달 주기(예: `N_est`가 최근 1s 수신 CAM에서 어떻게 추정되는지, CBR 센싱 윈도우 100ms가 누구 기준인지), 추론 결과 (T,p)가 어느 계층으로 어떻게 반영되는지를 패킷/주기 수준으로 기술.
- **T-10. 통계적 엄밀성**: 시드 3개, CV<1.1%만 보고. TWC 수준이면 신뢰구간 또는 유의성 검정, 밀도 스윕에 대한 분산 보고가 필요. 학습 기반이면 학습곡선·수렴성·시드 간 정책 분산도 요구됨.
- **T-11. 복잡도·수렴 분석**: 제안기법과 베이스라인의 추론/학습 복잡도 비교, 수렴 성질(REMO-DQN이면 Double-DQN 타깃·MoE 게이팅의 안정화 효과)을 정량·정성 논증.

---

## 🟡 정확성·일관성 (수치·용어) `[대부분 공통]`

- **A-12. steps vs seconds 혼동**: §V-A "duration\_steps = 3600 seconds". `duration_steps`는 스텝 수(×0.1s)이므로 3600스텝=360s, 3000스텝=300s다. 단위를 실제 설정과 일치시킬 것(코드 기본 3000 → 300s).
- **A-13. 도로 총연장 14.4km 근거 불명**: 코드는 3×3 그리드, `grid.length=250`. 총 drivable 길이가 14.4km가 되는지 실제 net에서 계산해 검증하거나 실측치로 교체. `~88 concurrent`, `3.06 veh/(km·lane)`도 실제 로그에서 산출.
- **A-14. 에너지효율 단위 불일치**: 초록·§III는 `mJ/km`, §V 지표 M4는 "dimensionless proxy". 하나로 통일(코드 `get_energy_efficiency`는 mJ/km 반환).
- **A-15. n_vehicles 값 불일치**: §V-A "n_vehicles=50", 그러나 코드 baseline runner 기본은 30(SA2), density sweep은 10~100. 논문에 쓸 최종 설정을 확정하고 표·본문 전체를 그 값으로 정렬.
- **A-16. 기여표(Table I) 과대표기**: Proposed 행 "MCU Deployment: Yes(<4KB)", "AoI-Aware: Yes"를 굵게 단정. MCU는 미측정(추정), 평가는 pending. 실증 전까지 단정 금지, 또는 "estimated"로 명시.
- **A-17. 저자 블록 TBD**: `\author{TBD...}` 실제 정보로 교체(제출 전 필수).

---

## 🔵 문체·서술 (.rules/writer.md 준수) `[공통]`

- **S-18. 리스트 남용**: §III 개요(Context Extractor/Inference/Compliance/…)가 `\textbf{...}` 블록 나열로 산문성이 약하다. writer 규칙상 itemize 미지시 구간은 산문으로 전개(문단 최소 5문장).
- **S-19. 과도 기호·부사**: 본문의 `---` em-dash 다수, "elegant in its simplicity", "precisely when it matters most" 등 수사적 표현은 규칙상 금지 대상. 정보 위주로 담백하게.
- **S-20. 초록 길이·주장 톤**: 결과 확보 후 재작성하되, 규칙에 맞춰 과장어 제거하고 정량 주장은 실측 범위로 한정.
- **S-21. 그림 부재**: 본문 `\includegraphics` 0개. `writer/data/plots/`에 PNG가 있으나 미삽입. TWC 원고면 최소 (i)시스템/프로토콜 오버레이 다이어그램 (ii)AoI–CBR 트레이드오프 산점/파레토 (iii)밀도별 PDR/AoI (iv)학습 수렴곡선 (v)CBR 시계열/CDF가 필요. 단, 삽입 그림의 수치는 반드시 확정된 실험 결과에서 생성된 것이어야 함.
- **S-22. 관련연구 초점 이탈**: bibitem 다수가 연합학습·침입탐지·스테가노그래피 등 주제와 무관(31개 미사용). 핵심(DCC/LIMERIC/PULSAR, V2X 전력제어, 브로드캐스트 AoI, 802.11bd 혼잡)로 재편하고 무관 항목 정리. (미사용 bibitem은 출력엔 안 나오나, 관련연구 서술이 FL/보안에 치우쳐 있어 재배치 필요.)

---

## 작업 체크리스트 (task.md 포맷)

```
- [ ] ⛔  방향 확정: (A) TinyMLP→IoT-J 유지 vs (B) REMO-DQN→TWC 전환 — 사용자 확인
- [ ] B-1 (B전환 시) 제목·초록·기여도 C1–C3·§IV를 REMO-DQN 기준 재작성, DRL 회피 문구 전면 삭제
- [ ] B-2 \markboth 및 상단 메타데이터를 IEEE TWC로 교체
- [ ] B-3 코드 보고서 C-1~C-3 수리 후 REMO-DQN 실측 → Table II 채움 (CSV 직접 로드)
- [ ] B-4 초록의 미검증 정량 주장 삭제 → 실측치로만 재기술 (BL-D AoI 하한 정합성 확인)
- [ ] B-5 표준 인용을 실제 ETSI 문서로 교체 / SumoNetSim 서술 삭제·실제 채널모델로 기술 / 에셋 생성 방식 정정
- [ ] B-6 충돌·채널 모델 보정으로 밀도별 PDR 차등 확보 후 표 갱신
- [ ] T-7 통신-이론적 기여 1개 이상 추가(AoI–CBR 해석 or PDR/AoI 근사모델 or 정책 경계)
- [ ] T-8 Proposition 1 삭제 또는 실질 명제로 대체
- [ ] T-9 §III 시스템모델을 프로토콜 관점(변수 도출·주기·전달)으로 보강
- [ ] T-10 통계 엄밀성(CI/유의성/분산) + 학습곡선 추가
- [ ] T-11 복잡도·수렴 분석 추가
- [ ] A-12~A-17 수치·단위·설정·표기 일관화 (steps/sec, 14.4km, 에너지단위, n_vehicles, 기여표, 저자)
- [ ] S-18~S-22 문체 규칙 정합(산문화·기호·그림삽입·관련연구 재편)
- [ ] critic 검토 요청
```

---

## 검증 (.rules/writer.md 준수 — 반드시 수행)

1. **수치 무결성**: 본문·표의 모든 정량치를 `writer/data/*.csv`에서 **직접 로드**해 대조. 임의 추정·기억 기반 기입 금지. 특히 Table II는 REMO-DQN 실측 CSV 생성 후에만 채움.
2. **인용 정합성**: 표준 서술이 실제 ETSI 문서 bibitem을 가리키는지, `Bhattacharyya2024`가 표준 인용으로 남아있지 않은지 grep 검증.
3. **방법 서술 정합성**: 본문이 기술하는 시뮬레이터·채널모델·에셋 생성 방식이 `code/`의 실제 구현과 1:1 대응하는지 대조(허위 기술 제거).
4. **물리적 정합성**: 보고된 AoI 개선폭이 최대율(BL-D) 신선도 하한을 위반하지 않는지, PDR이 밀도에 따라 단조 하락하는지 확인.
5. **LaTeX 무결성**: `\begin/\end` 균형, `\cite`↔bibitem, `\ref`↔label 미싱 0, 삽입 그림 경로 유효성 확인 후 critic 검토.
