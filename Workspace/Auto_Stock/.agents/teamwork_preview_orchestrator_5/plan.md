# Execution Plan — Phase 5: Dynamic Stock Screener

## 1. Survey Phase
- Goal: Deeply investigate existing data pipelines (`modules/data/`), trading engine (`modules/engine/`), data structures, Kiwoom API wrapper/simulation models, and existing test suite.
- Subagents: 3 parallel Explorers
  - Explorer 1: Data module & market data representation (`modules/data/`, tick data formats, daily OHLCV / fundamental data structures).
  - Explorer 2: Trading engine & RL simulator (`modules/engine/live_learning_simulator.py`, RL agent observation/action loop, state representation).
  - Explorer 3: Test harness & API rate limits / streaming structure (`tests/`, rate limit conventions, mock interfaces, websocket vs polling design).

## 2. Architecture & Contract Phase
- Synthesize explorer findings into `SCOPE.md`.
- Define exact method signatures for `screener.py`:
  - `update_daily_static_pool(...)`
  - `check_intraday_trigger(...)`
  - Polling / Streaming rate limit handling
- Define integration contract with `live_learning_simulator.py`.
- Define test specifications for `tests/test_phase5_screener.py`.

## 3. Milestone 1: Stock Screener Implementation
- Target: `modules/data/screener.py`
- Features: Static daily filter (market cap >= 1000억, PER/PBR, institutional/foreign supply) + Intraday dynamic trigger (volume 300%+ breakout, price 3%+ surge).
- Worker implements, Reviewers (2) + Challengers (2) + Forensic Auditor (1) verify.

## 4. Milestone 2: RL Engine Integration & Streaming Optimization
- Target: `modules/engine/live_learning_simulator.py` and `screener.py` rate limiting.
- Features: Integrating triggered stocks into RL observation/action loop, streaming subscription/polling queue.
- Worker implements, Reviewers (2) + Challengers (2) + Forensic Auditor (1) verify.

## 5. Milestone 3: Comprehensive Testing & Verification
- Target: `tests/test_phase5_screener.py` and regression testing.
- Features: 100% test pass on mock fundamental DataFrame & real-time tick stream, zero regressions on existing tests.
- Worker/Test Writer, Reviewers (2) + Challengers (2) + Forensic Auditor (1) verify.

## 6. Final Reporting
- Prepare final report and notify Sentinel via send_message.
