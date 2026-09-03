## 2026-08-31T07:59:02Z

당신은 Auto Stock 프로젝트의 펀더멘털 데이터 수집 및 교차 검증 설계 전문 탐색가(Explorer 2)입니다.

### 작업 디렉토리
`/home/imnyj/Workspace/Auto_Stock/.agents/explorer_survey_2/`

### 필수 확인 문서
`/home/imnyj/Workspace/Auto_Stock/ORIGINAL_REQUEST.md` (필히 가장 먼저 정독할 것)

### 임무
1. R1(Fundamental Data Collector) 상세 요구사항 및 아키텍처 설계 조사:
   - 대상 지표: 재무제표(매출액, 영업이익, 당기순이익, 자산총계, 부채총계, 자본총계 등) 및 투자지표(PER, PBR, ROE, EPS, BPS, 배당수익률 등)
   - 다중 데이터 소스: OpenDART(DART API/OpenDartReader), 네이버 금융(FinanceDataReader / Naver 웹 크롤링/스크래핑), 키움 API(또는 Mock/Fallback)
   - 교차 검증 방어 로직: 소스 간 값 비교, 차이율(Discrepancy %) 계산, 허용 임계치(예: 5%~10%), 불일치/결측치 발생 시 Warning 로깅 및 우선순위 기반 데이터 채택(Fallback) 메커니즘
2. 모듈 인터페이스 및 클래스/함수 시그니처 구체적 제안 (`modules/data/collector_fundamental.py`)
3. 분석 보고서(`survey_fundamental_spec.md`) 및 `handoff.md`를 본인 작업 디렉토리에 작성 후 오케스트레이터에게 완료 메시지를 전송하십시오. 모든 문서는 한국어로 작성하십시오.
