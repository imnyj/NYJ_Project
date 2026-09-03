# Auto_Stock Phase 5: API & Test Architecture 심층 탐색 보고서

**작성 일시**: 2026-09-03T10:15:00+09:00  
**작성자**: API & Test Explorer (`teamwork_preview_explorer_survey_p5_3`)  
**대상 모듈**: Phase 5 Dynamic Stock Screener (`modules/data/screener.py`), 키움증권 REST/WebSocket API (`core/kiwoom_api.py`, `modules/data/streamer.py`), RL 시뮬레이터 (`modules/engine/live_learning_simulator.py`), 테스트 스위트 (`tests/test_phase5_screener.py`)

---

## 1. 개요 및 조사 목적
본 조사는 주식 자동 매매 시스템 'Auto_Stock'의 **Phase 5: 다이내믹 종목 스크리너(Dynamic Stock Screener)** 모듈 개발에 앞서 다음 4가지 핵심 영역을 심층 분석하고 실현 가능한 아키텍처를 수립하는 것을 목적으로 합니다:
1. **R3 요구사항 분석**: 키움증권 REST API의 초당 호출 제한(초당 5회 등)을 회피하기 위한 WebSocket 이벤트 구독 및 N초 주기 분할 폴링(Sharded Polling) 스케줄링 구조 설계
2. **기존 테스트 스위트 전수 분석**: `tests/` 내 25개 테스트 파일, pytest 실행 환경, 격리 Mock 방식, Fixture 패턴 심층 분석
3. **R5 및 Acceptance Criteria 테스트 아키텍처 설계**: `tests/test_phase5_screener.py`의 5-Tier 테스트 스위트 설계 (정적 펀더멘털 필터링 검증, 실시간 틱 모멘텀 돌파 검증, 회귀 방지)
4. **pytest 실행 및 전체 회귀 상태 검증**: 475개 전체 테스트 스위트 100% Pass 확인 및 빌드/테스트 제약사항 정리

---

## 2. R3: 키움 REST API Rate Limit 회피 및 스트리밍 최적화 설계

### 2.1 키움증권 REST API의 물리적 한계 및 문제점
- **호출 한도 (Rate Limit)**: 키움증권 REST API는 서버 부하 방지를 위해 **초당 최대 5회**, 분당 수백 회 수준의 엄격한 Throttling을 적용함 (`core/kiwoom_api.py` 내 HTTP 429 처리 로직 존재).
- **스크리너 유니버스 규모**: 장 시작 전 정적 필터를 통과한 후보 종목 풀(Candidate Pool)은 통상 **100 ~ 200개 종목**에 달함.
- **치명적 위험**: 만약 100~200개 종목을 1초마다 동기적 REST API(`get_current_price`)로 전수 조회하려 시도할 경우:
  1. 초당 100~200회 요청으로 즉각적인 `HTTP 429 Too Many Requests` (`KiwoomRateLimitError`) 발생.
  2. 증권사 서버로부터 계정 세션 차단 또는 IP 차단 위험.
  3. 네트워크 지연(RTT) 누적으로 인해 장중 실시간 모멘텀(거래량 폭증 및 가격 급등) 포착 타이밍 상실.

### 2.2 해결 아키텍처 설계: 듀얼 모드 (WebSocket 이벤트 스트리밍 + Sharded Polling)

#### (1) 기본 모드: WebSocket 이벤트 기반 실시간 스트리밍 (Event-Driven Streaming)
- **개념**: 후보 풀(100~200개 종목)을 키움 실시간 WebSocket(또는 시스템 내 `BaseStreamer`/`MockStreamer`/`NaverPollingStreamer`)에 일괄 구독(`streamer.subscribe(symbol)`).
- **구동 메커니즘**:
  - 증권사 WebSocket 서버가 체결 틱을 푸시할 때마다 스트리머의 이벤트 디스패처(`_dispatch_tick`)가 구동됨.
  - `StockScreener`가 스트리머의 리스너(`on_tick(tick: TickData)`)로 등록되어 인메모리에서 즉각적으로 `check_intraday_trigger(tick)`을 수행.
- **장점**: REST API 호출 횟수 = **0회 (Rate Limit 완전 회피)**. 지연 시간 수 밀리초(ms) 이내 즉각 포착.

#### (2) 백업/오프라인 모드: N초 주기 분할 폴링 스케줄러 (Sharded Polling Scheduler)
- **개념**: WebSocket 사용이 불가능한 환경(모의 서버, 네트워크 방화벽 등)에서 REST API 또는 폴링 엔드포인트를 사용할 때, 시간축을 분할하여 호출을 분산.
- **수학적 스케줄링 모델**:
  - 후보 종목 수 $M = 150$, 총 순환 주기 $T = 30\text{초}$.
  - 초당 안전 허용 호출 수 $B = 3\text{회/초}$ (초당 5회 제한 대비 마진 확보).
  - 전체 종목을 $K = \lceil M / (T \times B) \rceil$ 개씩 초당 배치로 분할.
  - 예: 150개 종목 / 30초 = 초당 5개 종목 조회 필요. 안전 마진을 위해 $T=50$초로 설정 시 초당 3개씩 분할 폴링.
- **토큰 버킷(Token Bucket) RateLimiter 결합**:
  - `RateLimiter(max_rate=3.0, time_period=1.0)`을 두어 REST API 호출 전 `acquire()`를 강제하여 물리적으로 초당 3회를 초과하지 않도록 보장.
- **우선순위 계층형 폴링 (Tiered Polling)**:
  - Tier 1 (전일 거래대금 최상위 20개): 10초 주기
  - Tier 2 (중위 50개): 30초 주기
  - Tier 3 (나머지 80개): 60초 주기

### 2.3 `modules/data/screener.py` 반영 구조
```python
@dataclass
class ScreenerConfig:
    streaming_mode: str = "websocket"  # "websocket" | "polling" | "mock"
    max_requests_per_sec: float = 3.0  # REST 폴링 시 초당 최대 호출 수
    polling_cycle_seconds: float = 30.0
    batch_size: int = 3
    candidate_pool_size: int = 200
    min_market_cap: int = 100_000_000_000  # 1,000억 원
    per_min: float = 1.0
    per_max: float = 15.0
    volume_surge_ratio: float = 3.0  # 300% 급증
    price_surge_ratio: float = 0.03   # 3% 급등
    cooldown_seconds: float = 300.0   # 동일 종목 재트리거 방지 쿨다운

class ShardedPollingScheduler:
    """100~200개 종목을 초당 호출 제한 내에서 분할 순환 스케줄링하는 엔진"""
    def __init__(self, symbols: List[str], max_per_sec: float = 3.0):
        self.symbols = symbols
        self.max_per_sec = max_per_sec
        self.rate_limiter = TokenBucketLimiter(rate=max_per_sec)

    def get_batches(self) -> List[List[str]]:
        chunk_size = max(1, int(self.max_per_sec))
        return [self.symbols[i:i + chunk_size] for i in range(0, len(self.symbols), chunk_size)]
```

---

## 3. 기존 테스트 스위트 (`tests/`) 전수 분석

### 3.1 테스트 파일 목록 및 역할 분류 (총 25개 파일)
| 파일명 | 대상 영역 | 주요 검증 내용 |
|---|---|---|
| `test_phase1.py` | Data Pipeline (M1) | OpenDART/Naver/Mock 수집기, CrossValidator, PIT Consolidator |
| `test_phase2.py` | Mock Engine (M2) | VirtualAccount, MockExecutionEngine, 1원 오차 불변식 |
| `test_phase3_api.py` | Kiwoom REST (M3) | OAuth2 토큰, SecretStr 은닉, 주문/잔고/시세 TR, HTTP 429 복구 |
| `test_price_streamer.py` | Streaming (M2) | RingBuffer 동시성, WindowBarAggregator, MockStreamer, NaverPolling |
| `test_fundamental.py` | Fundamental Data | 재무제표 표준화, RealtimeValuation, 재무비율 교차검증 |
| `test_consolidator.py` | Data Consolidation | Point-in-Time 병합, 룩어헤드 방지, Parquet I/O |
| `test_live_learning_simulator.py` | RL Live Sim | 가상 계좌 연동 체결, Gymnasium 1.2.0 5-tuple, 싱글톤 안전성 |
| `test_hybrid_trading_env.py` | Gym Environment | 이산+연속 복합 액션 공간, 수수료 차감, 파산 종료 |
| `test_hybrid_env_gym_seeding_sb3.py`| Gym Seeding | 난수 시드 재현성, Stable-Baselines3 환경 래핑 호환성 |
| `test_hybrid_env_stress.py` | Env Stress | 초고빈도 체결, 극단적 시장 급락 변동성 방어 |
| `test_models.py` | Feature/Policy | 1D-CNN, MLP Feature Extractor, Hybrid Actor-Critic Policy |
| `test_hpo.py` | Optuna HPO | TPESampler, MedianPruner, Sharpe Ratio 목적함수 |
| `test_hpo_pipeline.py` | HPO E2E | 5-Tier HPO 통합 파이프라인, baseline_hpo.csv 스키마 |
| `test_adversarial_*.py` (8개) | Adversarial & Edge | 적대적 입력, 데이터 왜곡, 경쟁 조건, 메모리 누수 방어 |
| `test_m2_*.py` / `test_m3_*.py` (4개)| Subsystem Hardening| M2/M3 모듈별 결함 교정 및 안전성 한계 테스트 |

### 3.2 pytest 실행 환경 및 특이사항
- **가상환경 경로**: `/home/imnyj/venv/bin/pytest`
- **실행 권장 명령**: `/home/imnyj/venv/bin/pytest tests/ -v` (또는 `make test-all`)
- **수집 충돌 발견 (Critical)**:
  - 인자 없이 `pytest`만 루트에서 실행 시, `etc/scripts/m2_challenger2_stress_test.py` 파일(모듈 레벨 `sys.exit(0)`)이 테스트 모듈로 오인 수집되어 `INTERNALERROR> SystemExit: 0`으로 수집 단계에서 즉시 중단됨.
  - **대응책**: 항상 테스트 대상을 `tests/` 또는 `tests/test_xxx.py`로 명시해야 함.

### 3.3 Mock 방식 및 Fixture 패턴
- **외부 I/O 100% 격리**:
  - `unittest.mock.patch("core.kiwoom_api.KiwoomClient.get_current_price")`
  - `unittest.mock.patch.object(requests.Session, "post")` / `patch.object(requests.Session, "get")`
- **합성 데이터 생성기 활용**:
  - `MockStreamer.generate_ticks(...)`: 기하 브라운 운동(GBM) 기반 틱 데이터 시퀀스 생성
  - `MockPriceFetcher`: 가상 OHLCV 데이터프레임 생성
  - `CircularBuffer` / `RealtimeRingBuffer`: 실제 인메모리 링버퍼 주입
- **테스트 격리 및 상태 초기화**:
  - `reset_global_simulator()` 호출로 싱글톤 상태 오염 원천 방지

---

## 4. R5 / Acceptance Criteria: `tests/test_phase5_screener.py` 아키텍처 설계

프로젝트의 표준인 **5-Tier Test Architecture**를 적용하여 견고하고 누락 없는 테스트 스위트를 설계합니다.

### 4.1 Acceptance Criteria 매핑 테이블
| 인수 기준 요구사항 | 담당 Tier | 테스트 케이스 ID | 검증 내용 |
|---|:---:|---|---|
| 가상 정적 펀더멘털 DataFrame 주입 검증 | Tier 1, 2 | TC-P5-01, 05, 06 | 시총 1000억 이상, PER 1~15 등 조건 부합 종목만 감시 풀 진입 검증 |
| 가상 실시간 틱 데이터 스트림 주입 검증 | Tier 1, 2 | TC-P5-02, 03, 07 | 거래량 300% 폭증 & 가격 3% 급등 시 정확한 트리거 및 비충족 시 무시 |
| API Rate Limit / 스케줄링 구조 검증 | Tier 3 | TC-P5-09, 10, 11 | Sharded Polling 30초 주기 분할 및 TokenBucket 초당 한도 강제 |
| RL 시뮬레이터 연동 (R4) | Tier 4 | TC-P5-12, 13 | 포착된 종목이 LiveLearningSimulator의 obs/action 루프로 직결 |
| 전체 테스트 호환성 및 회귀 방지 | Tier 5 | TC-P5-14, 15 | 동시성 틱 유입 멀티스레드 안전성, 쿨다운 중복 방지, 100% Pass |

### 4.2 5-Tier 세부 테스트 케이스 명세

#### [Tier 1: Feature Coverage (핵심 기능 정상 검증)]
1. `test_update_daily_static_pool_happy_path`:
   - 시가총액 1,000억 이상, PER 1~15, PBR 0.2~2.0 조건을 갖춘 가상 DataFrame(10종목) 주입.
   - 조건 만족 종목(A: 5,000억/PER 8, B: 1,200억/PER 12)만 감시 풀 리스트로 반환되는지 assert.
2. `test_check_intraday_trigger_volume_and_price_surge`:
   - 감시 풀 등록 종목에 대해 전일 평균 거래량 1,000주 대비 현재 틱 누적 4,000주 (400% 폭증) & 시가 50,000원 대비 현재가 52,000원 (+4.0% 급등) 틱 주입.
   - 반환값이 정확히 해당 종목 코드(`symbol`)인지 assert.
3. `test_check_intraday_trigger_negative_conditions`:
   - 케이스 1: 거래량 500% 급증, 가격 상승률 0.5% (가격 미충족) -> None 반환.
   - 케이스 2: 가격 5.0% 급등, 거래량 120% (거래량 미충족) -> None 반환.
   - 케이스 3: 감시 풀에 포함되지 않은 미등록 종목의 폭증 틱 -> None 반환.
4. `test_screener_config_defaults_and_custom`:
   - `ScreenerConfig`의 기본값 로드 및 사용자 임계치 변경 유효성 검증.

#### [Tier 2: Boundary & Corner Cases (경계값 및 결측 방어)]
5. `test_boundary_market_cap_exact_threshold`:
   - 정확히 1,000억 원(100,000,000,000)인 종목 -> 포함.
   - 999억 9,999만 9,999원인 종목 -> 제외.
6. `test_boundary_per_zero_negative_nan_inf`:
   - 적자 기업 음수 PER(-3.5), 자본잠식 음수 PBR(-0.8), 결측치(NaN, None), 무한대(Inf)가 포함된 DataFrame 주입 시 예외 발생 없이 정상 필터링(제외)되는지 검증.
7. `test_boundary_surge_threshold_exact_match`:
   - 거래량 정확히 300.0% & 가격 정확히 +3.0% 경계 테스트.
   - 299.99% 미충족, 300.00% 충족.
8. `test_zero_open_price_and_zero_base_volume_defense`:
   - 시가(`open_price = 0`) 또는 기준 거래량(`base_volume = 0`) 데이터 유입 시 `ZeroDivisionError` 방어 및 안전 처리.

#### [Tier 3: API Rate Limit & Scheduling Optimization (호출 최적화)]
9. `test_sharded_polling_scheduler_partitioning`:
   - 150개 후보 종목 리스트를 `ShardedPollingScheduler(max_per_sec=3.0)`에 전달했을 때, 1개 배치당 3개 종목씩 총 50개 배치로 정확히 분할되는지 검증.
10. `test_token_bucket_rate_limiter_throttling`:
    - 초당 3회 제한 TokenBucket에 6회 연속 토큰 획득 시도 시, 정확히 1초 이상의 지연(Throttling)이 발생하는지 시간 측정 검증.
11. `test_websocket_streamer_event_driven_integration`:
    - `MockStreamer`에 `screener.on_tick`을 리스너로 등록하고 `MockStreamer.emit_tick()` 실행 시, REST API 호출 0건 상태에서 이벤트 기반으로 즉시 트리거 감지 확인.

#### [Tier 4: Real-World E2E Pipeline & Simulator Integration (R4)]
12. `test_e2e_screener_pipeline_simulation`:
    - 50개 종목 가상 유니버스 생성 -> 정적 필터링으로 10개 감시 풀 선정 -> MockStreamer 틱 스트림 주입 -> 특정 종목 모멘텀 폭증 포착까지 원스톱 검증.
13. `test_screener_to_live_learning_simulator_handoff`:
    - 스크리너에서 포착된 종목 코드가 `LiveLearningSimulator`로 전달되어 즉시 `sim.get_state(symbol)` 및 `sim.step(symbol, ActionType.BUY)`로 이어지는 파이프라인 연동 검증.

#### [Tier 5: Adversarial & Concurrency Hardening (동시성/안전성)]
14. `test_concurrent_tick_injection_thread_safety`:
    - 8개 작업자 스레드에서 수천 개의 틱을 동시에 주입할 때 Race Condition이나 데드락 없이 안정적으로 트리거 판정 수행.
15. `test_screener_trigger_cooldown_defense`:
    - 한 번 트리거된 종목이 300초 쿨다운 기간 내에 반복적으로 재트리거되지 않도록 방어하는 로직 검증.

---

## 5. 현재 pytest 실행 결과 및 빌드 무결성 확인

### 5.1 실행 명령 및 결과 요약
- **실행 명령**:
  ```bash
  /home/imnyj/venv/bin/pytest tests/ -v
  ```
- **실행 결과**:
  ```text
  ================= 475 passed, 22 warnings in 110.88s (0:01:50) =================
  ```
- **상태**: **100% Pass (0 Failed, 0 Error)**
- **결론**: 기존 시스템의 모든 회계 엔진, 강화학습 환경, HPO 파이프라인, 데이터 수집기, API 모듈이 완벽히 정상 동작 중이며, 신규 Phase 5 모듈 추가 시 이 기존 테스트 스위트에 단 하나의 회귀도 발생하지 않아야 함.

---

## 6. 구현자(Worker)를 위한 제언 및 인터페이스 규격 합의안

1. **모듈 생성 위치**: `/home/imnyj/Workspace/Auto_Stock/modules/data/screener.py`
2. **테스트 파일 생성 위치**: `/home/imnyj/Workspace/Auto_Stock/tests/test_phase5_screener.py`
3. **핵심 인터페이스 시그니처 제안**:
   ```python
   class DynamicStockScreener:
       def __init__(self, config: Optional[ScreenerConfig] = None):
           ...
       def update_daily_static_pool(self, df_fundamental: pd.DataFrame) -> List[str]:
           """정적 펀더멘털 필터를 통해 감시 풀 갱신 및 반환"""
           ...
       def check_intraday_trigger(self, tick: TickData) -> Optional[str]:
           """실시간 틱 수신 시 모멘텀 돌파 여부 판정 후 종목코드 반환 (미충족 시 None)"""
           ...
       def attach_streamer(self, streamer: BaseStreamer) -> None:
           """실시간 스트리머 이벤트 리스너 등록"""
           ...
       def get_candidate_pool(self) -> List[str]:
           """현재 감시 풀 반환"""
           ...
   ```
4. **시뮬레이터 파이프라인 연계**:
   - `modules/engine/live_learning_simulator.py`에 스크리너 트리거 이벤트를 수신하여 감시 종목을 능동적으로 관측/거래할 수 있는 메서드(예: `register_screener_trigger(symbol)`) 추가 권장.
