# Scope: Phase 5 Dynamic Stock Screener

## Architecture
Auto_Stock Phase 5는 대규모 종목 풀(수천 개 종목) 중에서 트레이딩 대상 종목을 발굴하여 강화학습(RL) 에이전트에게 공급하는 다이내믹 종목 스크리너 엔진을 구축합니다.
- **Data Layer (`modules/data/screener.py`)**:
  - `ScreeningCriteria`: 시가총액, PER, PBR, 외국인/기관 수급, 거래량/가격 급등 임계치 등을 정의하는 데이터클래스
  - `StockScreener`: 장 시작 전 정적 필터링(`update_daily_static_pool`) 및 장중 실시간 모멘텀 돌파 트리거(`check_intraday_trigger`), 키움 REST API Rate Limit(초당 5회) 회피를 위한 Sharded Polling Scheduler 및 WebSocket 스트리밍 구독 제어
- **Engine Layer (`modules/engine/live_learning_simulator.py`)**:
  - 스크리너에서 포착(Trigger)된 종목을 실시간으로 수신하여 RL 유니버스에 등록(`inject_triggered_symbol`)
  - 14차원 정규화 관측 상태 생성(`build_rl_observation`) 및 다중 종목 포지션 비중 매매(`step_symbol`) 지원
- **Test Layer (`tests/test_phase5_screener.py`)**:
  - 5-Tier 15개 이상의 완전 격리 가상 테스트 스위트 (Mock DataFrame & Mock TickData Stream 기반)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | R1. Static Daily Filter | 시가총액 1,000억 원 이상, PER 1~15, PBR 0.1~2.0, 외인/기관 수급 양호 조건 기반 감시 풀(Candidate Pool) 추출 (`update_daily_static_pool`) | M1 | ORIGINAL_REQUEST § R1 |
| 2 | R2. Intra-day Dynamic Trigger | 실시간 틱 데이터 주입 시 거래량 전일 대비 300% 폭증 & 시가 대비 3% 급등 모멘텀 돌파 포착 (`check_intraday_trigger`), 쿨다운 디바운스 | M1 | ORIGINAL_REQUEST § R2 |
| 3 | R3. Rate Limit / Streaming Optimization | 초당 5회 제한 회피를 위한 WebSocket 이벤트 수신 및 상위 100~200개 종목에 대한 초당 3개 청크 분할 폴링 스케줄링 | M1 | ORIGINAL_REQUEST § R3 |
| 4 | R4. RL Engine Integration | 트리거 종목의 RL 시뮬레이터 즉각 주입(`inject_triggered_symbol`), 14차원 관측 생성(`build_rl_observation`), 다중 종목 에쿼티 정합성 보장 | M2 | ORIGINAL_REQUEST § R4 |
| 5 | R5. Acceptance Test Suite | `tests/test_phase5_screener.py` 작성, 가상 정적 펀더멘털 DF 검증, 가상 실시간 틱 스트림 검증, 100% Pass | M3 | ORIGINAL_REQUEST § Acceptance Criteria |
| 6 | R6. Full Regression Pass | 기존 475개 전체 테스트 스위트 회귀 검증 (`/home/imnyj/venv/bin/pytest tests/ -v` 100% Pass) | M3 | ORIGINAL_REQUEST § Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Dynamic Stock Screener Core | `modules/data/screener.py`, `modules/data/__init__.py` | Survey | IN_PROGRESS |
| M2 | RL Engine Integration | `modules/engine/live_learning_simulator.py` | M1 | PLANNED |
| M3 | Comprehensive E2E Testing & QA | `tests/test_phase5_screener.py`, Full pytest regression | M1, M2 | PLANNED |

## Interface Contracts
### `modules/data/screener.py` (M1)
```python
@dataclass
class ScreeningCriteria:
    min_market_cap: int = 100_000_000_000  # 1,000억 원
    min_per: Optional[float] = 1.0
    max_per: Optional[float] = 15.0
    min_pbr: Optional[float] = 0.1
    max_pbr: Optional[float] = 2.0
    min_foreign_net_buy: Optional[int] = 0
    min_inst_net_buy: Optional[int] = 0
    volume_surge_threshold: float = 3.0    # 전일 동시간 대비 300% (4배)
    price_surge_threshold: float = 0.03    # 시가 대비 3% 급등
    cooldown_seconds: float = 60.0
    max_candidates: int = 200

class StockScreener:
    def __init__(self, criteria: Optional[ScreeningCriteria] = None, streamer: Optional[Any] = None)
    def update_daily_static_pool(self, data: Optional[Union[pd.DataFrame, List[str]]] = None, criteria: Optional[ScreeningCriteria] = None) -> List[str]
    def check_intraday_trigger(self, tick_data: Union[TickData, dict]) -> Optional[str]
    def schedule_polling_chunks(self, chunk_size: int = 3, interval_seconds: float = 1.0) -> List[List[str]]
    def on_tick(self, tick: Any) -> Optional[str]
```

### `modules/engine/live_learning_simulator.py` (M2)
```python
class LiveLearningSimulator:
    def inject_triggered_symbol(self, symbol: str, trigger_info: Optional[dict] = None) -> bool
    def build_rl_observation(self, symbol: str) -> np.ndarray  # (14,) float32
    def step_symbol(self, symbol: str, action: Union[int, ActionType], quantity: Optional[int] = None, position_weight: float = 1.0) -> Tuple[np.ndarray, float, bool, bool, dict]
    def process_triggered_queue(self, screener_events: List[dict]) -> List[dict]
```

## Code Layout & File Boundaries
- **M1 Worker Ownership**: `modules/data/screener.py`, `modules/data/__init__.py`
- **M2 Worker Ownership**: `modules/engine/live_learning_simulator.py`
- **M3 Worker / Test Writer Ownership**: `tests/test_phase5_screener.py`
- Concurrent workers MUST NEVER edit each other's target files.
- Concurrency & Audit: 모든 파일 수정은 `lock_manager.py` 락 획득 및 `audit_logger.py` 로깅을 수반해야 함 (`GEMINI.md` 준수).
