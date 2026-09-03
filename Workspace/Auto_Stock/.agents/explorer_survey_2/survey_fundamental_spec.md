# R1. Fundamental Data Collector & Cross-Validation Architecture Specification

## 1. 개요 및 목적 (Executive Summary)

본 문서는 **Auto Stock ML/RL Trader**의 **Phase 1 데이터 수집 파이프라인** 중 **R1: Fundamental Data Collector (재무제표 및 가치투자 지표 수집기 및 교차 검증 시스템)**의 상세 요구사항, 다중 데이터 소스 인터페이스, 계정 표준화 및 교차 검증 방어 로직을 정의하는 기술 명세서입니다.

- **대상 모듈**: `modules/data/collector_fundamental.py`
- **핵심 목표**:
  1. OpenDART, 네이버 금융(웹 스크래핑/모바일 API), 키움 API(또는 Mock/Fallback) 등 복수의 소스로부터 안정적으로 재무 및 가치 지표를 수집.
  2. 출처 간 수치 차이(Discrepancy %)를 정밀 계산하여 허용 오차 이내인지 교차 검증(Cross-Validation).
  3. API 키 미설정, 네트워크 오류, 결측치, 5%~10% 이상의 불일치 발생 시 Warning 로깅 및 우선순위 기반 데이터 Fallback 방어 메커니즘 제공.
  4. ML/RL 피처 엔지니어링 및 시계열 결합(R3)에 적합한 표준화된 데이터 모델 및 Pandas DataFrame 반환 인터페이스 구축.

---

## 2. 대상 지표 정의 및 데이터 표준화 (Target Metrics & Normalization)

### 2.1 수집 대상 지표 체계

| 대분류 | 세부 지표명 | 영문 표준 Key | 단위 (표준화) | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| **재무상태표 (BS)** | 자산총계 | `total_assets` | KRW (원) | 기업의 총 자산 규모 |
| | 부채총계 | `total_liabilities` | KRW (원) | 기업의 총 부채 규모 |
| | 자본총계 | `total_equity` | KRW (원) | 지배/비지배 포함 총 자기자본 |
| | 자본금 | `capital_stock` | KRW (원) | 납입 자본금 |
| **손익계산서 (IS/CIS)**| 매출액 | `revenue` | KRW (원) | 기업의 총 매출/영업수익 |
| | 영업이익 | `operating_profit` | KRW (원) | 본업 활동을 통한 영업이익(손실) |
| | 당기순이익 | `net_income` | KRW (원) | 법인세 차감 후 최종 당기순이익 |
| **현금흐름표 (CF)** | 영업활동현금흐름 | `operating_cash_flow` | KRW (원) | 영업활동으로 인한 실제 현금 유입/유출 |
| | 잉여현금흐름 (FCF) | `free_cash_flow` | KRW (원) | 영업CF - CAPEX (WiseFn/계산치) |
| **수익성/안정성 지표** | ROE (자기자본이익률) | `roe` | % (0~100) | (당기순이익 / 평균자본총계) * 100 |
| | ROA (총자산이익률) | `roa` | % (0~100) | (당기순이익 / 평균자산총계) * 100 |
| | 부채비율 | `debt_ratio` | % (0~100) | (부채총계 / 자본총계) * 100 |
| | 영업이익률 | `op_margin` | % (0~100) | (영업이익 / 매출액) * 100 |
| | 순이익률 | `net_margin` | % (0~100) | (당기순이익 / 매출액) * 100 |
| **시장 가치 지표** | PER (주가수익비율) | `per` | 배 (Ratio) | 주가 / 주당순이익(EPS) |
| | PBR (주가순자산비율) | `pbr` | 배 (Ratio) | 주가 / 주당순자산(BPS) |
| | EPS (주당순이익) | `eps` | KRW (원) | 지배주주순이익 / 가중평균주식수 |
| | BPS (주당순자산) | `bps` | KRW (원) | 지배주주자본 / 기말발행주식수 |
| | 배당수익률 | `dividend_yield` | % (0~100) | (주당배당금 / 현재주가) * 100 |
| | 주당배당금 (DPS) | `dps` | KRW (원) | 보통주 기준 결산 현금배당금 |
| | 시가총액 | `market_cap` | KRW (원) | 현재주가 * 총발행주식수 |
| | 총발행주식수 | `shares_outstanding`| 주 (Count) | 보통주 + 우선주 발행 주식수 |

### 2.2 단위 표준화 규칙 (Unit Standardization Rules)
- **금액 단위 통일**:
  - DART 원천 데이터는 원(KRW) 단위 정수 문자열로 제공됨.
  - 네이버 금융(웹/모바일)은 재무제표 수치를 **억원** 단위(예: 300,870 = 30조 870억)로 제공함.
  - **규칙**: 모든 재무제표 금액(`revenue`, `operating_profit`, `net_income`, `total_assets`, `total_liabilities`, `total_equity`, `operating_cash_flow`)은 **KRW (원, integer/int64)** 단위로 통일하여 변환 후 비교 및 반환한다. (네이버 억원 수치는 `x 100,000,000` 수행).
- **지표 단위 통일**:
  - 비율 지표(`roe`, `debt_ratio`, `dividend_yield` 등)는 백분율 표기(예: 10.5% -> `10.5` 또는 `0.105` 중 명확히 표준화, 본 시스템에서는 직관적 비교를 위해 `% 수치인 10.5`로 통일).
  - 배수 지표(`per`, `pbr` 등)는 소수점 배수(`float`)로 표준화.
- **연결 vs 개별 기준 통일**:
  - 종속회사가 있는 상장사의 경우 IFRS 연결재무제표(`CFS`)를 최우선 기준으로 채택.
  - DART 수집 시 `fs_div='CFS'`를 기본값으로 하며, 종속회사가 없는 경우 개별(`OFS`)로 자동 전환.

---

## 3. 다중 데이터 소스 상세 명세 (Multi-Source Acquisition Specs)

### 3.1 소스 1: OpenDART (공식 전자공시 REST API)
- **제공 기관**: 금융감독원 전자공시시스템 (OpenDART)
- **엔드포인트**:
  1. `https://opendart.fss.or.kr/api/fnlttSinglAcnt.json` (단일회사 주요계정)
  2. `https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json` (단일회사 전체 재무제표)
  3. `https://opendart.fss.or.kr/api/corpCode.xml` (고유번호 고유코드 다운로드)
- **인증 방식**: HTTP GET Query Parameter `crtfc_key` (환경변수 `DART_API_KEY` 또는 `OPENDART_API_KEY`)
- **보고서 코드(`reprt_code`)**:
  - `11011`: 사업보고서 (4분기/연간 확정)
  - `11012`: 반기보고서 (2분기)
  - `11013`: 1분기보고서 (1분기)
  - `11014`: 3분기보고서 (3분기)
- **계정명 매핑 사전 (Synonym Normalizer)**:
  - 매출액: `['매출액', '수익(매출액)', '영업수익', '매출']`
  - 영업이익: `['영업이익', '영업이익(손실)']`
  - 당기순이익: `['당기순이익', '당기순이익(손실)', '연결당기순이익', '연결당기순이익(손실)']`
  - 자산총계: `['자산총계']`
  - 부채총계: `['부채총계']`
  - 자본총계: `['자본총계']`
- **장단점**:
  - 장점: 법적 효력을 갖는 가장 신뢰성 높은 원천 확정 재무데이터.
  - 단점: API Key 필수, 공시 시차(분기 종료 후 45일), 실시간 가치지표(PER/PBR) 미제공(직접 계산 필요).

### 3.2 소스 2: 네이버 금융 (Naver Finance Mobile API & Scraping)
- **엔드포인트 구성**:
  1. **모바일 재무 API**: `https://m.stock.naver.com/api/stock/{code}/finance/annual` 및 `.../quarter`
     - JSON 포맷으로 연간/분기 실적 및 투자지표(매출, 영업익, 순이익, ROE, 부채비율, EPS, PER, BPS, PBR, DPS) 제공.
     - `isConsensus` 플래그를 통해 확정 실적('N')과 증권사 컨센서스('Y') 명확히 분리.
  2. **모바일 통합 정보 API**: `https://m.stock.naver.com/api/stock/{code}/integration`
     - JSON 포맷으로 실시간 시가총액, TTM PER, TTM EPS, PBR, BPS, 배당수익률, 52주 최고/최저가 제공.
  3. **PC 웹 스크래핑**: `https://finance.naver.com/item/main.naver?code={code}`
     - HTML 기반 기업실적분석 테이블 (`cop_analysis`) 및 aside 투자정보 파싱.
  4. **WiseFn / FnGuide iframe**: `https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={code}`
     - 상세 재무비율, FCF, CAPEX, 추정치 컨센서스 제공.
- **장단점**:
  - 장점: 별도 API Key 불필요(무료), 실시간 시장지표(PER/PBR/시총) 즉시 획득 가능, `requests` 및 `bs4` 기반 순수 파이썬 구현 가능.
  - 단점: 비공식 엔드포인트로 HTML/JSON 스키마 변경 위험 존재(방어적 파싱 필수).

### 3.3 소스 3: 키움 API / Mock Provider (Kiwoom OpenAPI+)
- **운용 방식**:
  - 키움증권 OpenAPI+는 32-bit Windows OCX 환경에 의존하므로, Linux/CI 환경에서는 `MockKiwoomCollector` 또는 네트워크 소켓 Bridge 패턴을 제공.
  - `TR: opt10001` (주식기본정보요청): PER, PBR, EPS, BPS, 자본금, 매출액, 영업이익, 당기순이익 등.
- **역할**:
  - 단위 테스트 및 오프라인 시뮬레이션을 위한 완벽한 Fixture/Mock 제공.
  - 실거래 Windows 환경 배포 시 실제 키움 OpenAPI OCX 핸들러로 스위칭 가능한 인터페이스 일치.

---

## 4. 교차 검증 및 방어 아키텍처 (Cross-Validation & Fallback Defense)

### 4.1 불일치도 계산 공식 (Discrepancy Formula)
두 데이터 소스 $S_1, S_2$에서 동일한 지표 값 $V_1, V_2$를 추출했을 때의 상대 오차율(Discrepancy Percentage)을 다음과 같이 정의합니다:

$$\text{Discrepancy}(\%) = \frac{|V_1 - V_2|}{\max(|V_1|, |V_2|) + \epsilon} \times 100 \quad (\epsilon = 10^{-6})$$

- 절대 금액 지표(매출, 영업이익, 자산총계 등)와 배수 지표(PER, PBR 등) 모두 동일한 정규화 공식 적용.

### 4.2 오차 판정 임계치 (Tolerance Thresholds)
1. **Pass (정상 일치, $< 5.0\%$)**:
   - 두 소스 간 수치가 일치하거나 미세한 반올림 오차 범위 내인 경우.
   - `status = "PASSED"`, 우선순위 소스(DART) 데이터를 최종 채택.
2. **Warning (경미한 불일치, $5.0\% \le \text{Diff} < 10.0\%$)**:
   - 연결/개별 회계 차이, 분기 잠정치 vs 확정치 수정 반영 시차 등으로 인한 오차.
   - `status = "WARNING"`, 상세 로깅(Logger.warning) 기록 후 확정 원천(DART) 데이터 우선 채택.
3. **Critical Discrepancy (중대 불일치, $\ge 10.0\%$)**:
   - 데이터 단위 불일치(예: 억원 vs 원 변환 실패), 주식 분할/병합 미반영, 컨센서스와 실제치의 혼용 등 심각한 불일치.
   - `status = "CRITICAL_DISCREPANCY"`, Logger.error 기록, 데이터 품질 플래그 `is_reliable=False` 마킹 후 신뢰도 상위 소스 데이터 채택 및 검증 보고서에 상세 사유 명시.

### 4.3 데이터 소스 우선순위 계층 (Fallback Priority Matrix)

| 지표 유형 | 1순위 (Primary) | 2순위 (Secondary) | 3순위 (Tertiary) | 최후 수단 (Fallback) |
| :--- | :--- | :--- | :--- | :--- |
| **과거 확정 재무제표**<br>(매출, 영업익, 순이익, 자산 등) | **OpenDART**<br>(공식 공시 원천) | **Naver Finance**<br>(모바일/웹 재무) | **WiseFn / FnGuide** | **Mock / Local Cache** |
| **실시간/당일 투자지표**<br>(현재 PER, PBR, BPS, EPS, 시총) | **Naver Finance**<br>(실시간 시세 반영) | **Kiwoom API**<br>(opt10001) | **DART 계산치**<br>(공시치 기반 산출) | **Mock / Local Cache** |
| **컨센서스 및 추정치**<br>(추정 PER, 추정 EPS 등) | **Naver Finance**<br>(증권사 컨센서스) | **WiseFn** | - | `None` (결측 처리) |

### 4.4 결측치 및 장애 방어 메커니즘 (Fault-Tolerance & Missing Value Strategy)
1. **DART API Key 부재 시**:
   - 즉시 2순위인 `NaverFinanceCollector`로 자동 Fallback하여 파이프라인 중단 방지.
   - "DART API Key not found. Falling back to Naver Finance" Warning 1회 로깅.
2. **네트워크 타임아웃 / HTTP 5xx 에러 시**:
   - 지수 백오프(Exponential Backoff: 1s, 2s, 4s) 기반 최대 3회 재시도.
   - 재시도 실패 시 다음 우선순위 소스로 Fallback.
3. **결측치(NaN/None) 발생 시**:
   - 필수 지표(매출, 영업익)가 1순위에서 결측된 경우 2순위 데이터로 필드 단위 병합(Field-level Coalesce).
   - 모든 소스에서 결측된 경우 `None` 또는 `np.nan` 유지하고 `missing_fields` 목록에 기록.

---

## 5. 모듈 인터페이스 및 클래스/함수 시그니처 설계 (`modules/data/collector_fundamental.py`)

### 5.1 데이터 모델 (Data Models)

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import pandas as pd


class PeriodType(str, Enum):
    ANNUAL = "annual"
    QUARTER = "quarter"


class ValidationStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    CRITICAL_DISCREPANCY = "CRITICAL_DISCREPANCY"
    FALLBACK = "FALLBACK"
    SINGLE_SOURCE = "SINGLE_SOURCE"


@dataclass
class FinancialStatement:
    """연간 또는 분기 단위 표준 재무제표 데이터 모델"""
    ticker: str
    year: int
    quarter: Optional[int] = None  # None for annual (4Q), 1/2/3/4 for quarterly
    period_type: PeriodType = PeriodType.ANNUAL
    is_consensus: bool = False
    
    # Financial Statements (Unit: KRW)
    revenue: Optional[int] = None               # 매출액
    operating_profit: Optional[int] = None      # 영업이익
    net_income: Optional[int] = None            # 당기순이익
    total_assets: Optional[int] = None          # 자산총계
    total_liabilities: Optional[int] = None     # 부채총계
    total_equity: Optional[int] = None          # 자본총계
    operating_cash_flow: Optional[int] = None   # 영업활동현금흐름
    free_cash_flow: Optional[int] = None        # 잉여현금흐름 (FCF)
    
    # Financial Ratios (Unit: %)
    roe: Optional[float] = None                 # 자기자본이익률 (%)
    roa: Optional[float] = None                 # 총자산이익률 (%)
    debt_ratio: Optional[float] = None          # 부채비율 (%)
    op_margin: Optional[float] = None           # 영업이익률 (%)
    net_margin: Optional[float] = None          # 순이익률 (%)
    
    # Valuation Metrics
    eps: Optional[float] = None                 # 주당순이익 (원)
    bps: Optional[float] = None                 # 주당순자산 (원)
    per: Optional[float] = None                 # 주가수익비율 (배)
    pbr: Optional[float] = None                 # 주가순자산비율 (배)
    dps: Optional[float] = None                 # 주당배당금 (원)
    dividend_yield: Optional[float] = None      # 배당수익률 (%)
    
    # Metadata
    source: str = "UNKNOWN"
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RealtimeValuation:
    """실시간/당일 기준 가치평가 및 시장 지표 모델"""
    ticker: str
    current_price: int
    market_cap: int
    shares_outstanding: int
    per: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    dividend_yield: Optional[float] = None
    foreign_rate: Optional[float] = None
    high_52w: Optional[int] = None
    low_52w: Optional[int] = None
    source: str = "NAVER"
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DiscrepancyItem:
    """개별 지표별 교차 검증 결과"""
    metric_name: str
    source_a_name: str
    source_a_value: Any
    source_b_name: str
    source_b_value: Any
    discrepancy_pct: float
    is_valid: bool
    message: str


@dataclass
class ValidationReport:
    """교차 검증 종합 보고서"""
    ticker: str
    target_period: str
    status: ValidationStatus
    primary_source: str
    comparison_source: Optional[str]
    items: Dict[str, DiscrepancyItem] = field(default_factory=dict)
    max_discrepancy_pct: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
```

---

### 5.2 소스별 수집기 인터페이스 (Source Collector Classes)

```python
from abc import ABC, abstractmethod


class BaseFundamentalSource(ABC):
    """모든 펀더멘털 데이터 수집기가 상속해야 하는 추상 베이스 클래스"""

    @abstractmethod
    def get_annual_financials(self, ticker: str, start_year: int, end_year: int) -> List[FinancialStatement]:
        """연간 재무제표 리스트 수집"""
        pass

    @abstractmethod
    def get_quarterly_financials(self, ticker: str, count: int = 8) -> List[FinancialStatement]:
        """최근 분기 재무제표 리스트 수집"""
        pass

    @abstractmethod
    def get_realtime_valuation(self, ticker: str) -> Optional[RealtimeValuation]:
        """실시간/당일 시장 가치 지표 수집"""
        pass


class OpenDartCollector(BaseFundamentalSource):
    """OpenDART REST API 전용 수집기"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DART_API_KEY") or os.getenv("OPENDART_API_KEY")
        self.session = requests.Session()
        self._corp_code_cache: Dict[str, str] = {
            "005930": "00126380",  # 삼성전자
            "000660": "00164779",  # SK하이닉스
            "035420": "00266961",  # NAVER
            "035720": "00258801",  # 카카오
            "005380": "00164742",  # 현대차
        }

    def get_corp_code(self, ticker: str) -> Optional[str]: ...
    def fetch_single_account(self, corp_code: str, bsns_year: str, reprt_code: str, fs_div: str = "CFS") -> Dict[str, Any]: ...
    def get_annual_financials(self, ticker: str, start_year: int, end_year: int) -> List[FinancialStatement]: ...
    def get_quarterly_financials(self, ticker: str, count: int = 8) -> List[FinancialStatement]: ...
    def get_realtime_valuation(self, ticker: str) -> Optional[RealtimeValuation]:
        # DART는 실시간 지표를 제공하지 않으므로 None 반환 (설계상 명확한 분리)
        return None


class NaverFinanceCollector(BaseFundamentalSource):
    """네이버 금융 모바일 API 및 웹 스크래핑 수집기"""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_annual_financials(self, ticker: str, start_year: int, end_year: int) -> List[FinancialStatement]: ...
    def get_quarterly_financials(self, ticker: str, count: int = 8) -> List[FinancialStatement]: ...
    def get_realtime_valuation(self, ticker: str) -> Optional[RealtimeValuation]: ...
    def get_cop_analysis_table(self, ticker: str) -> pd.DataFrame: ...


class MockKiwoomCollector(BaseFundamentalSource):
    """Linux/CI 환경 및 오프라인 테스트용 Kiwoom/Mock 수집기"""

    def __init__(self, fixture_dir: Optional[str] = None):
        self.fixture_dir = fixture_dir

    def get_annual_financials(self, ticker: str, start_year: int, end_year: int) -> List[FinancialStatement]: ...
    def get_quarterly_financials(self, ticker: str, count: int = 8) -> List[FinancialStatement]: ...
    def get_realtime_valuation(self, ticker: str) -> Optional[RealtimeValuation]: ...
```

---

### 5.3 교차 검증기 (FundamentalCrossValidator)

```python
class FundamentalCrossValidator:
    """복수 소스 데이터 간 정밀 교차 검증기"""

    def __init__(self, warning_threshold: float = 0.05, critical_threshold: float = 0.10):
        self.warning_threshold = warning_threshold      # 5% 오차
        self.critical_threshold = critical_threshold    # 10% 오차

    @staticmethod
    def calculate_discrepancy(val_a: Union[int, float, None], val_b: Union[int, float, None]) -> float:
        """두 값의 상대 오차 비율 계산 (0.0 ~ 1.0)"""
        if val_a is None or val_b is None:
            return 0.0
        if val_a == 0 and val_b == 0:
            return 0.0
        max_val = max(abs(val_a), abs(val_b))
        if max_val == 0:
            return 0.0
        return abs(val_a - val_b) / max_val

    def validate_statements(
        self,
        stmt_primary: FinancialStatement,
        stmt_secondary: FinancialStatement,
        metrics_to_compare: Optional[List[str]] = None
    ) -> ValidationReport:
        """
        두 재무제표 인스턴스를 비교하여 ValidationReport 생성
        기본 비교 지표: revenue, operating_profit, net_income, roe, eps, per, pbr
        """
        ...
```

---

### 5.4 통합 수집기 파사드 (FundamentalDataCollector)

```python
class FundamentalDataCollector:
    """
    R1 메인 파사드 클래스:
    다중 소스 수집, 교차 검증, 방어적 Fallback 및 DataFrame 병합 기능을 캡슐화하여 제공
    """

    def __init__(
        self,
        dart_api_key: Optional[str] = None,
        enable_cross_validation: bool = True,
        warning_threshold: float = 0.05,
        critical_threshold: float = 0.10,
        mock_mode: bool = False
    ):
        self.enable_cross_validation = enable_cross_validation
        self.validator = FundamentalCrossValidator(warning_threshold, critical_threshold)
        self.mock_mode = mock_mode
        
        # Source Initializations
        self.naver_collector = NaverFinanceCollector()
        self.dart_collector = OpenDartCollector(api_key=dart_api_key)
        self.mock_collector = MockKiwoomCollector()

    def get_financial_statements(
        self,
        ticker: str,
        period_type: PeriodType = PeriodType.ANNUAL,
        start_year: int = 2021,
        end_year: int = 2025,
        quarter_count: int = 8
    ) -> Tuple[List[FinancialStatement], Optional[ValidationReport]]:
        """
        펀더멘털 재무제표 수집 및 교차 검증 수행
        
        반환값:
            (최종 채택된 FinancialStatement 리스트, 교차검증 리포트)
        """
        ...

    def get_realtime_valuation(self, ticker: str) -> RealtimeValuation:
        """
        실시간/당일 기준 가치평가 지표 수집
        """
        ...

    def get_as_dataframe(
        self,
        ticker: str,
        period_type: PeriodType = PeriodType.ANNUAL,
        start_year: int = 2021,
        end_year: int = 2025
    ) -> pd.DataFrame:
        """
        ML/RL 피처 결합용 표준 Pandas DataFrame 변환
        인덱스: DatetimeIndex (예: '2023-12-31', '2024-12-31')
        컬럼: revenue, operating_profit, net_income, roe, per, pbr, eps, bps, dividend_yield 등
        """
        ...
```

---

## 6. 테스트 및 검증 전략 (Testing & Verification Strategy)

### 6.1 테스트 케이스 매트릭스 (`tests/test_collector_fundamental.py`)
1. **단위 테스트 (Unit Tests)**:
   - `test_discrepancy_calculation`: 0%, 3%, 7%, 15% 차이에 대한 오차율 계산 정확성.
   - `test_unit_normalization`: 억원 수치와 원 수치 간 100,000,000배 단위 정규화 변환 검증.
   - `test_synonym_mapping`: DART 계정명 다양성(수익(매출액), 영업수익 등)의 표준 키 매핑.
2. **통합 및 방어 테스트 (Integration & Defense Tests)**:
   - `test_samsung_electronics_live_naver`: 삼성전자('005930') 네이버 모바일 API 실시간 호출 및 유효한 매출/영업익/PER/PBR 수집 검증.
   - `test_dart_fallback_when_key_missing`: DART API Key가 없을 때 예외 발생 없이 네이버 수집기로 매끄럽게 Fallback 동작하는지 검증.
   - `test_cross_validation_report_warning`: 8% 인위적 오차 주입 시 `ValidationStatus.WARNING` 생성 및 로그 기록 검증.
   - `test_cross_validation_report_critical`: 15% 인위적 오차 주입 시 `ValidationStatus.CRITICAL_DISCREPANCY` 생성 검증.
   - `test_dataframe_output_schema`: 최종 DataFrame의 인덱스, 컬럼명, 결측치 처리 및 Parquet 저장 적합성 검증.

---

## 7. 결론 및 다운스트림 연계 (Conclusion & Next Steps)

- **결론**: 본 명세는 외부 의존성(OpenDartReader 등 미설치 패키지)에 종속되지 않고, 표준 라이브러리 및 기설치된 `requests`, `bs4`, `pandas`만을 활용하여 100% 자립적인 고신뢰 다중 소스 수집기 및 교차 검증 시스템을 구축할 수 있도록 설계되었습니다.
- **R3(Consolidator) 연계**: 시계열 주가 수집기(R2)의 일봉/분봉 데이터와 결합할 수 있도록 분기/연간 재무제표의 기준일(공시일/분기말일)을 `date` 컬럼으로 정렬하여 Forward-fill (ffill) 결합이 가능한 표준 포맷을 제공합니다.
