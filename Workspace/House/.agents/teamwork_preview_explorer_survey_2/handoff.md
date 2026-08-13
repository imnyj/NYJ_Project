# 📋 Handoff Report — UI Survey & Technical Specifications for index4.html

**Agent**: teamwork_preview_explorer_survey_2  
**Working Directory**: `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_2`  
**Date**: 2026-08-12  

---

## 1. Observation (관측 사실)

1. **프로젝트 주요 요구사항 파일 확인**:
   - `/home/imnyj/Workspace/House/ORIGINAL_REQUEST.md`: R1(매입 일회성 비용 전수조사), R2(대출 시나리오 비교), R3(월별 재무 시뮬레이션), R4(행정 절차 체크리스트), R5(`index4.html` 실시간 웹 시뮬레이터) 명세 확인.
   - `/home/imnyj/Workspace/House/UI 요구서.md`: 대출 종류 가시화 탭, 보금자리론→신생아대출 계산기 탭, 역산 계산기 탭, 별채 거주/독립 준비 탭 요구사항 명세 확인.
   - `/home/imnyj/Workspace/House/Budget/8. 학기 중 예상 지출 보고서.md`: 월 소득 3,300,000원, 기존 13대 카테고리 생활비 2,390,708원, 기존 월세 311,000원(매입 후 제거 대상), 교연비 10,000,000원(2월/8월 각 500만), 특강비 2,000,000원(1월/7월 각 100만) 데이터 확인.

2. **기존 UI 구현 파일 검토**:
   - `/home/imnyj/Workspace/House/ui/index.html`: 4개 탭(대출 정리, 대출 계산기, 역산 계산기, 별채 거주), CSS 변수 기반 글래스모피즘 테마 및 `updateChartTheme()` 구현 확인 (lines 9-28, 300-311).
   - `/home/imnyj/Workspace/House/ui/index2.html`: 뉴브루탈리즘(고대비 흑백 wireframe) 스타일 변형 버전 (lines 9-19).
   - `/home/imnyj/Workspace/House/ui/index3.html`: 이중축 Chart.js 구현 (`yLeft`: 월 발생 이자/납입액/보너스, `yRight`: 대출 잔액, lines 467-611), 글래스모피즘 배경 블롭 (`.blob1`, `.blob2`, `.blob3`, lines 38-43), 월별 시뮬레이션 및 미납 이자 누적/보너스 청산 로직 (lines 307-440).
   - `/home/imnyj/Workspace/House/ui/update_ui.py`: `LockManager` 및 `AuditLogger`를 사용하여 `index.html` 파일을 안전하게 업데이트하는 스크립트 구조 확인.

---

## 2. Logic Chain (논리적 추론 과정)

1. **디자인 톤 통합성**: `index.html`과 `index3.html`에서 검증된 `:root` 및 `[data-theme="dark"]` CSS 토큰, 반투명 카드 (`backdrop-filter: blur(12px)`), 앰비언트 오로라 블롭(`blob1`, `blob2`, `blob3`) 디자인 시스템을 `index4.html`에 일관되게 채택해야 함.
2. **시각화 충실도**: `index3.html`에 적용된 Chart.js 이중축(Dual-Axis) 구현 방식(`yLeft`: 지출/보너스 막대 및 라인, `yRight`: 대출 잔액 영역 라인, `grid: { drawOnChartArea: false }`)이 R5 요구사항인 월 지출과 대출 잔액의 독립 스케일링 시각화를 완벽하게 지원함을 확인.
3. **재무 시뮬레이션 정합성**:
   - 기존 생활비 2,390,708원에서 월세 311,000원을 제외한 기본 순수 생활비 2,079,708원에 방서동 자이 아파트 관리비(약 20만~25만 원) 및 고정비를 가산하여 월 총지출을 구함.
   - 월 소득 3,300,000원에서 월 총지출을 차감하여 실시간 월 잔여 자금을 산출함.
   - 보너스 수입(1/7월 특강비 각 100만 원, 2/8월 교연비 각 500만 원)은 미납이자 발생 시 우선 청산 후 잔여액을 대출 원금 즉시 상환에 투입함.
4. **종합 명세 도출**: 위 관측과 논리를 바탕으로 `survey_ui.md`에 `index4.html` 생성을 위한 4대 실시간 지처(초기 필요 자금, 월 총지출, 월 잔여자금, 완납 시점) 산출 공식과 컨트롤 패널 및 차트 명세를 완전하게 체계화함.

---

## 3. Caveats (제약 및 고려사항)

- 본 탐색은 읽기 전용(Read-only) 조사 작업이며, 프로젝트 코드나 소스 파일을 직접 수정하지 않았습니다.
- 실제 `index4.html` 구현 시 브라우저 호환성을 위해 외부 모듈 번들러 없이 CDN 기반 Chart.js(v4 이상) 단일 script 태그 로딩 방식을 유지해야 합니다.
- 방서동 자이 아파트 30평 미만의 실제 관리비 수준(약 20만~25만 원)은 사용자가 필요 시 조정할 수 있도록 기본값 입력 필드로 제공하는 것이 권장됩니다.

---

## 4. Conclusion (결론 및 제언)

- 기존 UI 구현물(`index3.html` 중심)의 글래스모피즘 CSS 테마, 다크모드 토글, Chart.js 이중축 시각화 및 월별 상환 로직은 `index4.html` 구축을 위한 뛰어난 기술적 기반을 제공합니다.
- 작성된 `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_2/survey_ui.md` 보고서는 요구사항 R1~R5와 UI 요구서를 모두 만족하는 `index4.html` 구현의 완벽한 기술 설계 명세서 역할을 수행합니다.

---

## 5. Verification Method (검증 방법)

1. **보고서 파일 존재 확인 및 내용 검증**:
   - `view_file` 또는 terminal 명령으로 `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_survey_2/survey_ui.md` 내용 검토.
2. **기술 명세 충수성 검증**:
   - `survey_ui.md` 내에 (1) 글래스모피즘 CSS 변수/다크모드, (2) 이중축 Chart.js 명세, (3) 슬라이더/입력 필드 매핑 및 계산 알고리즘, (4) `index4.html` 4대 실시간 산출 지처 공식 및 레이아웃 구조가 모두 포함되어 있는지 직접 확인.
