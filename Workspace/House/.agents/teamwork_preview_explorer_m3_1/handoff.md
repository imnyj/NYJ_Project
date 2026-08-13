# Handoff Report — `teamwork_preview_explorer_m3_1`

## 1. Observation
- **입력 파일 분석**:
  - `ORIGINAL_REQUEST.md`: R1~R5 요구사항 및 Follow-up 자금 운영 계획(보유 현금 2.3억, 세후 월 소득 330만, 연 보너스 1,000만 원 원금상환, 디딤돌/시중은행 대출 비교) 확인.
  - `PROJECT.md`: 13대 카테고리 생활비 중 월세 31.1만 원 제거(기본 2,079,708원), 아파트 관리비(20만 원), 주차/인터넷(4만 원) 신규 고정비(총 24만 원) 데이터 규격 확인.
  - `survey_ui.md`: `:root` 및 `[data-theme="dark"]` CSS 토큰, 글래스모피즘 (`backdrop-filter`, `border-radius: 20px`, `.blob1~3`), Chart.js 이중축 설정(`drawOnChartArea: false`) 명세 확인.
  - `ui/index3.html`: 기존 대출 상환 시뮬레이터 HTML 구조, 슬라이더 이벤트 바인딩 (`calculate()`), `toggleTheme()` 다크모드 메커니즘 확인.
- **산출물 생성**:
  - `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m3_1/ui_arch_report.md` 생성 완료.

## 2. Logic Chain
1. **관측된 CSS 및 UI 구조 추출**: `index3.html`과 `survey_ui.md`의 디자인 토큰과 다크모드 구조를 결합하여 `[data-theme="dark"]`와 `:root`에 명확한 Glassmorphism CSS 변수를 배정함.
2. **4대 KPI 지표 계산 공식 정립**:
   - 초기 필요 자금 총액($C_{init}$) = 아파트 매매가 + 일회성 부대비용(취득세 + 중개수수료 + 법무사비 + 인지세 + 채권할인 + 이사비 + 수리비 + 대출 부대비용).
   - 필요 대출금($L_{req}$) = $C_{init}$ - 2.3억 원.
   - 월별 총 지출($E_{total}$) = 월 대출 상환액(50만 원) + 기존 생활비(207.97만 원) + 아파트 고정비(24만 원) = 281.97만 원.
   - 월 잔여 자금($R_{monthly}$) = 월 소득(330만 원) - $E_{total}$ = 48.03만 원.
   - 완납 시점($T_{payoff}$) = 연 1,000만 원 보너스 상환을 반영한 상환 알고리즘 적용 시점.
3. **Chart.js 이중축 시각화 옵션 고도화**:
   - `yLeft` (월 이자, 보너스 상환 막대)와 `yRight` (대출 잔액 곡선)을 분리하고, 우측 grid에 `drawOnChartArea: false`를 부여하여 그리드선 중첩 방지.
4. **4대 상세 분석 탭 (R1~R4) 레이아웃 설계**:
   - UI Card 탭 시스템을 도입하여 R1(부대비용 표), R2(대출 상품 비교), R3(월별 현금흐름/상환 표), R4(행정 절차 체크리스트)를 단일 HTML 내에 깔끔하게 포함시킴.

## 3. Caveats
- **코드 파일 직접 작성 금지**: 본 작업은 탐색 에이전트(Explorer)의 읽기 전용(Read-only) 조사 임무이므로, `ui/index4.html` 파일을 직접 생성하거나 수정하지 않았습니다.
- **디딤돌대출 규제완화 시나리오**: 부부합산 소득이 1.3억 원 이상으로 현행 디딤돌 소득기준(8,500만 원 이하)을 초과할 수 있으나, 요구사항에 따라 규제 완화 여부를 슬라이더로 조절하여 비교할 수 있도록 설계했습니다.

## 4. Conclusion
- `ui/index4.html` 개발을 위한 완전하고 정밀한 UI/UX 아키텍처 및 기술 명세서(`ui_arch_report.md`) 작성을 완료했습니다.
- 구현 담당 에이전트(Worker)는 `ui_arch_report.md`에 기재된 HTML 구조, CSS 토큰, JS 상환 알고리즘, Chart.js 이중축 옵션, 4대 탭 명세를 그대로 옮겨 `index4.html`을 즉시 제작할 수 있습니다.

## 5. Verification Method
- **보고서 파일 검증**:
  - `view_file` 도구로 `/home/imnyj/Workspace/House/.agents/teamwork_preview_explorer_m3_1/ui_arch_report.md` 내용 및 목차 정합성 확인.
- **데이터 산출식 검증**:
  - `ui_arch_report.md` 4.1절의 부대비용 및 생활비 산출식이 `PROJECT.md` 규격과 일치하는지 대조.
