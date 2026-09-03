# Handoff Report — Data Pipeline Explorer (Phase 5 Dynamic Stock Screener)

- **작성 에이전트**: Data Pipeline Explorer (`teamwork_preview_explorer_survey_p5_1`)
- **수신 에이전트**: Project Orchestrator (`4361a64e-415a-4de5-81f3-8b8d281253cd`)
- **작업 유형**: Hard Handoff (조사 및 아키텍처 설계 완료)
- **작성 일자**: 2026-09-03
- **보고서 파일**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_1/survey_data.md`

---

## 1. Observation (직접 관찰 사실)

1. **`modules/data/` 내부 파일 및 `screener.py` 부재**:
   - `/home/imnyj/Workspace/Auto_Stock/modules/data/` 디렉토리에 `__init__.py`, `collector_fundamental.py`, `collector_price.py`, `consolidator.py`, `pipeline.py`, `streamer.py` 6개 파일만 존재하며, `screener.py`는 존재하지 않음.
   - grep 검색 결과 코드베이스 내 `screener.py` 구현체는 없으며, `ORIGINAL_REQUEST.md` (라인 50: `modules/data/screener.py` 내부에 구현) 및 에이전트 기획 문서에서만 언급됨.

2. **시가총액 및 펀더멘털 데이터 포맷**:
   - `/home/imnyj/Workspace/Auto_Stock/modules/data/collector_fundamental.py`의 `RealtimeValuation` (라인 158~174):
     ```python
     @dataclass
     class RealtimeValuation:
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
     ```
   - 라인 265~280의 `parse_korean_money`: '1,520조 324억', '5,000억' 등을 원(KRW) 단위 int로 변환함. 시가총액은 원(KRW) 단위 정수(`1,000억 원 = 100_000_000_000`)로 관리됨.
   - `/home/imnyj/Workspace/Auto_Stock/modules/data/consolidator.py` (라인 186~211):
     `dynamic_per = close / eps`, `dynamic_pbr = close / bps`, `dynamic_market_cap = close * shares_outstanding`으로 산출되며, EPS/BPS가 0 이하일 경우 `np.nan` 처리됨.

3. **외국인/기관 수급 데이터 현황**:
   - `RealtimeValuation`에는 `foreign_rate` (외국인 지분율/보유율, float %)만 존재하며, 순매수 금액/수량 컬럼(`foreign_net_buy`, `inst_net_buy`)은 `modules/data/`에 아직 정의되어 있지 않음.
   - `ORIGINAL_REQUEST.md` (라인 50)에서는 "기관/외국인 수급 양호 조건을 만족하는 관심 종목(Candidate Pool) 리스트를 추출"하도록 요구함.

4. **실시간 틱 데이터 구조체 (`streamer.py`)**:
   - `/home/imnyj/Workspace/Auto_Stock/modules/data/streamer.py`의 `TickData` (라인 37~50):
     `timestamp`, `symbol`, `price`, `volume`, `accum_volume`, `side`, `bid_price`, `ask_price`, `open_price`, `high_price`, `low_price` 필드를 가짐.
   - `open_price`가 제공되므로 장중 시가 대비 3% 급등(`(price - open_price) / open_price >= 0.03`) 계산을 즉시 수행 가능함.

5. **테스트 환경 및 회귀 검증**:
   - 가상환경 경로 `/home/imnyj/venv/bin/pytest`를 통해 실행:
     - `tests/test_fundamental.py`: 30 passed in 1.34s
     - `tests/test_consolidator.py`: 19 passed in 2.29s
     - `tests/test_price_streamer.py`: 35 passed in 2.48s
   - 전체 기존 테스트 스위트가 100% 정상 통과함을 확인.

---

## 2. Logic Chain (논리적 추론 체계)

1. **[Observation 1 참조]**
   - `modules/data/screener.py`가 아직 존재하지 않으므로, 신규 모듈을 `modules/data/screener.py`에 생성하고 `modules/data/__init__.py`의 `__all__`에 공개 인터페이스(`StockScreener`, `ScreeningCriteria`)를 추가해야 한다.

2. **[Observation 2, 3 참조]**
   - `ORIGINAL_REQUEST.md`의 승인 기준(Line 65) "가상의 정적 펀더멘털 데이터(DataFrame)를 주입했을 때 조건에 맞는 종목만 감시 풀에 들어가는지 검증"을 만족하기 위해서는, `update_daily_static_pool`이 `pd.DataFrame`을 직접 파라미터로 주입받을 수 있어야 한다.
   - 동시에 실서비스/온라인 환경에서는 종목코드 리스트(`List[str]`)가 주입되었을 때 `FundamentalDataCollector`를 호출하여 실시간 가치지표를 조회하고 DataFrame을 구성하는 다형성(Polymorphism)을 지원해야 한다.
   - 시가총액은 원(KRW) 단위 정수(`>= 100_000_000_000`)를 기본으로 하되, 컬럼명 별칭(`market_cap`, `dynamic_market_cap`, `시가총액`) 및 PER/PBR 별칭을 정규화하는 `_normalize_columns` 헬퍼가 필요하다.
   - 수급 데이터(`foreign_net_buy`, `inst_net_buy`)는 현재 데이터 수집기에 명시적 컬럼이 없으므로, DataFrame에 해당 컬럼이 있을 때는 양수 순매수(`foreign_net_buy + inst_net_buy > 0`)를 검사하고, 없을 때는 경고 로깅 후 바이패스하여 모듈이 크래시되지 않도록 Fault-Tolerant하게 설계해야 한다.

3. **[Observation 4 참조]**
   - R2 실시간 모멘텀 트리거(`check_intraday_trigger`)는 `streamer.py`의 `TickData` 객체 및 `dict`를 모두 수용하도록 Duck Typing 처리하며, `open_price` 기반 시가 대비 3% 급등(`price_surge_threshold=0.03`) 및 거래량 300% 폭증(`volume_surge_threshold=3.0`) 조건을 감시 풀(`self.candidate_pool`) 내 종목에 대해 평가해야 한다.

4. **[Observation 5 참조]**
   - 단위 테스트 실행 시 시스템 전역 `pytest`가 아닌 `/home/imnyj/venv/bin/pytest`를 사용해야 하므로, 향후 `tests/test_phase5_screener.py` 구현 및 검증 명령어도 해당 가상환경을 기준으로 가이드해야 한다.

---

## 3. Caveats (주의사항 및 한계)

1. **수급 데이터 실시간 수집 연동**:
   - 네이버 모바일 API 및 DART에서는 당일 장중 외국인/기관 순매수 수치를 실시간으로 제공하지 않으며, 네이버 일별 시세 웹페이지 스크래핑 또는 키움 REST API의 `opt10045` 조회가 필요함. 백테스트 및 단위 테스트는 DataFrame 모의 주입으로 100% 검증 가능함.
2. **키움 REST API Rate Limit**:
   - 초당 5회 제한이 있으므로 전 종목(2,000개 이상)을 장 시작 직전 실시간 API로 긁는 것은 불가능함. 따라서 `update_daily_static_pool`은 상위 200개(`max_candidates=200`)로 종목 수를 압축하거나, 사전 수집된 Parquet 캐시 데이터를 기반으로 필터링해야 함.

---

## 4. Conclusion (최종 결론 및 권장사항)

1. **모듈 아키텍처 확정**:
   - `modules/data/screener.py` 단일 파일 내에 `ScreeningCriteria` (데이터클래스)와 `StockScreener` (엔진 클래스)를 구현.
2. **`update_daily_static_pool` 명세 확정**:
   - 시그니처: `update_daily_static_pool(self, data: Optional[Union[pd.DataFrame, List[str]]] = None, criteria: Optional[ScreeningCriteria] = None) -> List[str]`
   - 시가총액 >= 1,000억 원 (`100_000_000_000`), PER 1~15 (`1.0 <= per <= 15.0`), PBR 0.1~2.0, 외인/기관 순매수 양수 필터링 수행.
   - 반환값: 6자리 정규화된 종목코드 문자열 리스트 (`List[str]`).
3. **상세 설계서 작성 완료**:
   - 구체적인 구현 코드 스켈레톤과 컬럼 정규화 테이블을 `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_1/survey_data.md`에 완비함.

---

## 5. Verification Method (독립 검증 방법)

1. **보고서 파일 검증**:
   - 경로: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_1/survey_data.md`
   - 검증 내용: R1 `update_daily_static_pool` 입출력/필터링/에러핸들링 명세, `ScreeningCriteria` 필드 명세, 컬럼 정규화 매핑 테이블, `modules/data/screener.py` 스켈레톤 코드 포함 여부 확인.

2. **기존 테스트 스위트 회귀 검증 명령**:
   ```bash
   /home/imnyj/venv/bin/pytest tests/test_fundamental.py tests/test_consolidator.py tests/test_price_streamer.py -q
   ```
   - 정상 기준: 84개 테스트 100% 통과 (0 failed).
