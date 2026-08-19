# Handoff Report: Reviewer 2 (초안 스타일 및 수식 정합성 정밀 심사)

- **심사 대상**: `/home/imnyj/Workspace/paper4/paper/paper4_draft_korean.md`
- **심사자**: Reviewer 2 (`reviewer_m6_2`)
- **최종 판정**: **`REQUEST_CHANGES` (수정 후 재심사 요망)**
- **심사 일시**: 2026-08-18

---

## 1. 관측 (Observation)

직접 분석 도구(`/home/imnyj/Workspace/paper4/etc/scripts/verify_paper4_reviewer2.py` 및 파싱 스크립트)와 본문 888개 라인 전수 조사를 통해 직접 관측된 사실은 다음과 같습니다.

### (1) LaTeX 수식 문법 오류 및 기호 표기 비일관성 관측
- **수식 문법 파손 (Line 15, 국문 초록)**:
  - 원문: `Eclipse SUMO 및 Nakagami-$ 페이딩 무선 채널 기반의 통합 시뮬레이션 환경에서...`
  - 관측: `Nakagami-$` 뒤에 `$m$` 또는 닫는 달러 기호가 누락되어 LaTeX 파서 렌더링 에러를 유발함.
- **수식 기호(Notation) 비일관성**:
  - 상태 벡터 표기: 제3.2절/3.3절에서는 볼드체 $\mathbf{s}_t \in \mathbb{R}^5$로 표기되나, 제2.2절 및 일부 본문에서는 비볼드체 $s_t$로 혼용됨.
  - 채널 점유율 표기: $\text{CBR}$ (로만체, 43회), $CBR$ (이탤릭체, 114회), $\text{CBR}_{\text{smoothed}}$, $CBR_{\text{smooth}}$, $\text{CBR}_t$, $CBR_t$ 등 다수 혼용.
  - 정보 연령 및 패킷 전달률 표기: $\text{AoI}$와 $AoI$, $\text{PDR}$과 $PDR$이 절별로 혼용됨.
  - 패킷 생성 주기 및 송신 전력: $T_{\text{GenCam}}$ (Line 404, 452) vs $T_{\text{GenCAM}}$ (Line 455) vs $T_{\text{gen}}$ (Line 95, 101); $P_{\text{tx}}$ vs $P_{tx}$.

### (2) 마크다운 테이블 렌더링 결함 관측
- **Table III-1 (Lines 454, 455, 462)**:
  - Line 454: `| **MDP 정식화** | $|\mathcal{S}|$ | $5$ | 상태 공간 차원 $[\text{CBR}, N_{\text{est}}, v, \Delta t, \text{CBR}_{\text{smoothed}}]$ |`
  - Line 455: `| | $|\mathcal{A}|$ | $16$ ($4 \times 4$) | $T_{\text{GenCAM}} \in \{0.1, 0.2, 0.5, 1.0\}\text{s} \times P_{\text{tx}} \in \{0, 10, 20, 30\}\text{dBm}$ |`
  - Line 462: `| **학습 하이퍼파라미터** | $|\mathcal{B}|$ | $64$ | 미니배치 샘플 크기 |`
  - 관측: 마크다운 테이블 내부 수식에서 집합 크기 표기에 이스케이프되지 않은 파이프 기호(`$|\mathcal{S}|$, $|\mathcal{A}|, |\mathcal{B}|$`)를 사용하여, 마크다운 엔진이 4열 테이블을 6열로 분할 인식함. 이로 인해 테이블 레이아웃이 완전히 깨지는 렌더링 결함 발생.

### (3) 섹션 간 수치 및 내용 모순(Cross-section Inconsistency) 관측
- **고밀도 PDR 수치 모순**:
  - 제1장 Line 65: `120 veh/km의 극단적 고밀도 환경에서도 76.4% 이상의 패킷 전달률(PDR)을 유지함과 동시에...`
  - 제2.4절 Line 203: `고밀도 환경에서도 76.4% 이상의 패킷 전달률을 유지하며...`
  - 반면 제5.4절 Table 5.5 (Line 643), Table 5.10 (Line 788), 국문 초록 (Line 15): 100 veh/km 고밀도 PDR은 **73.41%**이며, 76.54%는 10 veh/km 저밀도 PDR임.
- **파라미터 수 및 연산 지연시간 모순**:
  - 제2.4절 Line 199: `최소한의 파라미터(10만 개 미만)와 마이크로초 단위의 초저지연 추론 성능을 달성하였다.`
  - 반면 제1장 Line 65, 제5.7절 Line 762, Table 5.9 (Line 768): 모델 파라미터 수는 **350K(35만 개)**이며, 추론 지연시간은 **1.2 ms(밀리초)**임.

### (4) 학술적 글쓰기 스타일 및 안티패턴 관측 (`academic-writing-style/SKILL.md`)
- **과장된 수식어 및 단정적 AI 클리셰 다수 발견**:
  - `완벽히` (9회: Line 15, 201, 844, 855 등), `완벽하게` (4회: Line 639, 762, 821), `원천 차단` (4회: Line 185, 200, 707), `독보적인` (2회: Line 15, 703) 등 비객관적/과장된 주관적 부사 사용.
- **소괄호 남용**:
  - 전체 858개 라인 중 357개 라인(41.6%)에 소괄호가 사용되었으며, 용어의 첫 등장 이후에도 `(Vehicle-to-Everything, V2X)`, `(Age of Information, AoI)` 등의 중복 약어 정의가 반복됨.
- **단락 길이 규정 (최소 5문장 이상) 미달 단락 존재**:
  - 제1장(Introduction)과 제2장(Related Works)은 각 문단이 5문장 이상으로 충실히 작성되었으나, 제5장(Performance Evaluation)의 세부 절(5.5.2, 5.6, 5.7, 5.8 등)에서 1~4문장으로 구성된 짧은 단락들이 발견됨.

### (5) 참고문헌 인용 전단사 매핑 관측
- 참고문헌 [1]부터 [27]까지 총 27편이 정의되어 있으며, 본문 내에서 [1]~[27]이 모두 누락 없이 인용됨 (전단사 매핑 100% 일치).
- 2025년 MoE 무선 서베이 논문([22] Xu et al., IEEE COMST 2025)이 제2.4절 및 표 1에 정확히 인용되어 요구사항 R2를 완벽히 충족함.

---

## 2. 논리 체계 (Logic Chain)

1. **테이블 렌더링 무결성**:
   - 마크다운 파서는 라인 내 `|` 기호를 기준으로 열(Column)을 분할한다.
   - Table III-1의 Lines 454, 455, 462에 포함된 `$|\mathcal{S}|$`, `$|\mathcal{A}|$`, `$|\mathcal{B}|$`는 수학적으로는 절대값/원소수 기호이나, 마크다운 문법상 2개의 열 구분자로 처리되어 6개의 컬럼으로 인식된다.
   - 따라서 해당 행의 셀 수가 헤더(4개)와 불일치하여 테이블 렌더링이 깨지므로 수정이 필수적이다. (수정안: `$\vert\mathcal{S}\vert$` 또는 `$\|\mathcal{S}\|$` 사용).

2. **수식 문법 및 기호 일관성**:
   - Line 15의 `Nakagami-$`는 수식 종결 기호가 누락되어 LaTeX 컴파일 시 `Missing $ inserted` 에러를 발생시킨다.
   - 논문의 전문성을 확보하기 위해 논문 전체에 걸쳐 상태 벡터는 볼드체($\mathbf{s}_t$), 행동은 $a_t$, 스칼라 지표는 로만체($\text{CBR}, \text{AoI}, \text{PDR}$), 파라미터는 $T_{\text{GenCam}}, P_{\text{tx}}$로 통일되어야 독자의 혼선을 방지할 수 있다.

3. **데이터 및 수치 일관성**:
   - 초록 및 제5장의 실험 결과 데이터(`73.41% PDR at 100 veh/km`, `350K params`, `1.2 ms`)와 제1장/제2장의 서술(`76.4% at high density`, `10만 개 미만`, `마이크로초 추론`) 간의 불일치는 논문의 신뢰성을 훼손하는 중대한 결함이다.
   - 본문 전체의 모든 정량적 수치를 제5장 시뮬레이션 실측 데이터 테이블 기준으로 일치시켜야 한다.

4. **학술적 문체 준수**:
   - IEEE TWC 저널 기준에 부합하기 위해 `완벽히`, `원천 차단`, `독보적인`과 같은 감정적/과장된 AI 클리셰를 배제하고, 객관적이고 건조한 학술적 문체(`안정성을 확보하였다`, `오류를 방지하였다`, `우수한 성능을 달성하였다`)로 교정해야 한다.

---

## 3. 한계 및 고려사항 (Caveats)

- 본 심사는 한국어 마스터 초안(`paper4_draft_korean.md`)을 대상으로 진행되었으며, 추후 영문 번역(Paper 4 IEEE TWC Final Manuscript) 작업 시 동일한 수식 정합성 및 스타일 규칙이 계승되어야 합니다.
- 14개 강화학습 알고리즘 시뮬레이션 원본 데이터(`aoi_vs_density.csv`, `pdr_vs_density.csv`, `cbr_stability.csv`, `hardware_feasibility.csv` 등)의 물리적 값 자체는 제5장 본문 테이블과 정확히 일치함을 확인하였습니다.

---

## 4. 최종 결론 및 권고 사항 (Conclusion)

### **판정: `REQUEST_CHANGES` (수정 요청)**

제안된 논문 초안은 전반적으로 IEEE TWC에 걸맞은 방대한 분량(888 라인)과 14개 알고리즘 비교, 엄밀한 시스템 모델 및 27개 참고문헌의 완벽한 매핑을 갖추고 있습니다. 그러나 다음의 4가지 주요 수정 사항이 반영되어야 최종 승인이 가능합니다:

1. **[Critical] Table III-1 마크다운 렌더링 수정**:
   - Lines 454, 455, 462의 `$|\mathcal{S}|$, $|\mathcal{A}|, |\mathcal{B}|$`를 `$\vert\mathcal{S}\vert$, $\vert\mathcal{A}\vert$, $\vert\mathcal{B}\vert$`로 수정하여 열 정렬 복원.
2. **[Critical] 초록 수식 오류 수정**:
   - Line 15의 `Nakagami-$`를 `Nakagami-$m$`으로 수정.
3. **[Major] 서론/관련연구 수치 정합성 일치화**:
   - Line 65, 203: 고밀도 PDR 수치를 `76.4%` $\to$ `73.41%`로 수정 (또는 "저밀도 76.54%에서 고밀도 73.41% 유지").
   - Line 199: `10만 개 미만` $\to$ `350K`, `마이크로초` $\to$ `1.2 ms`로 수정.
4. **[Major] 학술적 문체 다듬기**:
   - `완벽히`, `완벽하게`, `원천 차단`, `독보적인` 등 과장된 부사/표현 19건을 건조하고 명확한 학술 용어로 대체.
   - 제5장 세부 분석 단락 중 1~3문장으로 분절된 단락들을 5문장 이상의 완성도 높은 학술 문단으로 병합/보강.

---

## 5. 독립적 검증 방법 (Verification Method)

다음 터미널 명령어를 실행하여 수식 문법, 마크다운 테이블 파싱, 인용 전단사 매핑을 독립적으로 재검증할 수 있습니다:

```bash
# 1. 자동 검증 스크립트 실행
python3 /home/imnyj/Workspace/paper4/etc/scripts/verify_paper4_reviewer2.py

# 2. 테이블 렌더링 무결성 확인
python3 /home/imnyj/Workspace/paper4/etc/scripts/check_tables.py

# 3. 수치 일관성 확인
python3 /home/imnyj/Workspace/paper4/etc/scripts/check_consistency.py
```
