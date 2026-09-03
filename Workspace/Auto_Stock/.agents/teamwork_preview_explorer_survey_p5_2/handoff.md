# Handoff Report — Auto_Stock Phase 5 RL Engine Explorer

- **작성 에이전트**: RL Engine Explorer (`teamwork_preview_explorer_survey_p5_2`)
- **수신 에이전트**: Orchestrator (`teamwork_preview_orchestrator_5`, ID: `4361a64e-415a-4de5-81f3-8b8d281253cd`)
- **작업 범위**: `modules/engine/live_learning_simulator.py`, `modules/engine/hybrid_trading_env.py`, `modules/models/`, `modules/data/streamer.py`, R2 및 R4 연동 인터페이스 설계
- **산출물**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_2/survey_engine.md`

---

## 1. Observation (직접 관찰 결과)

1. **`LiveLearningSimulator` 구조 및 단일 종목 종속성**:
   - 위치: `modules/engine/live_learning_simulator.py:32-170`
   - `reset()` 메서드는 53번째 라인에서 `return self.get_state(symbol="005930")`와 같이 특정 종목코드가 하드코딩되어 있음.
   - `step()` 메서드(67-146 라인)는 `step(symbol: str, action: Union[int, ActionType], quantity: int = 1)` 시그니처를 가지며, 한 번에 한 종목에 대해서만 동기식으로 주문을 체결함.
   - `get_state()`(148-169 라인)는 `symbol`, `current_price`, `cash_balance`, `holding_quantity`, `avg_buy_price`, `total_equity`, `realized_pnl`, `unrealized_pnl`, `cumulative_frictions`의 9개 키를 가진 Python dict를 반환함.

2. **포트폴리오 에쿼티 계산 시 잠재적 왜곡**:
   - `modules/engine/live_learning_simulator.py:127`:
     `curr_equity = self.account.get_total_equity({symbol: current_price})`
   - `VirtualAccount.get_total_equity`(`modules/engine/mock_environment.py:400-426`)는 인자로 전달된 딕셔너리에 특정 종목이 없으면 평단가(`pos.avg_price`)로 평가함. 만약 시뮬레이터가 A종목을 매수한 후 B종목 스텝을 진행할 때 A종목의 최신 시장가가 반영되지 않아 포트폴리오 에쿼티 및 로그 수익률 보상($r_t$)에 왜곡이 발생할 수 있음.

3. **강화학습 환경 및 모델의 관측/행동 규격**:
   - `HybridTradingEnv`(`modules/engine/hybrid_trading_env.py:112-122`):
     관측 공간은 14차원 float32 벡터(10개 시장 피처 + 4개 계좌 상태 피처: `cash_ratio`, `position_ratio`, `unrealized_pnl_ratio`, `step_progress`)로 정의됨.
   - `HybridActorCritic`(`modules/models/hybrid_policy.py:51-120`):
     14차원 관측 벡터를 입력받아 이산 매매 방향(3-class: HOLD, BUY, SELL)과 연속 포지션 비중($w \in [0.0, 1.0]$)을 동시에 출력함.
   - `HybridTradingEnv.step()`(`modules/engine/hybrid_trading_env.py:386-419`):
     포지션 비중 $w$를 가용 현금 및 예상 1주 매수 비용(`est_cost_per_share = current_price * (1 + slip) * (1 + comm)`)으로 나누어 실제 체결 주수(`target_qty`)를 동적으로 계산함.

4. **실시간 틱 및 시세 스트리밍 인프라**:
   - `modules/data/streamer.py:37-51`:
     `TickData` 구조체에 `timestamp`, `symbol`, `price`, `volume`, `accum_volume`, `side`, `bid_price`, `ask_price`, `open_price`, `high_price`, `low_price`, `raw_data` 필드가 완비되어 있음.
   - `CircularBuffer`(`modules/data/streamer.py:147-252`):
     종목별 `deque(maxlen=50000)` 및 스레드 안전 락을 제공하여 O(1) 추가 및 고정 메모리 한도를 보장함.
   - `BaseStreamer`(`modules/data/streamer.py:416-520`):
     `subscribe(symbol)`, `unsubscribe(symbol)`, `add_listener(callback)` 인터페이스를 제공함.

5. **기존 테스트 스위트 통과 상태**:
   - `/home/imnyj/venv/bin/pytest tests/test_live_learning_simulator.py tests/test_hybrid_trading_env.py` 실행 결과: 18 passed (0.55s), 회귀 없음 확인.

---

## 2. Logic Chain (추론 단계)

1. **[관찰 1, 3 연계]**:
   - `LiveLearningSimulator`의 현재 `get_state`는 9개 키의 딕셔너리를 반환하지만, `HybridTradingEnv`와 `HybridActorCritic` 모델은 14차원의 정규화된 NumPy 배열을 요구함.
   - 따라서 스크리너에서 포착된 종목이 RL 에이전트 루프로 주입될 때, 해당 종목의 14차원 관측 벡터를 생성해주는 어댑터/메서드(`build_rl_observation(symbol)`)가 `LiveLearningSimulator`에 반드시 구현되어야 함.

2. **[관찰 1, 4 연계]**:
   - 스크리너가 장중 틱 스트림을 감시하다가 조건 충족 시 종목을 포착하면, `LiveLearningSimulator`가 해당 종목을 동적으로 등록할 수 있는 인터페이스(`inject_triggered_symbol(symbol, trigger_data)`)가 필요함.
   - 동시에 실시간 시세 수신을 위해 시뮬레이터가 연결된 `BaseStreamer`에게 해당 종목의 구독(`subscribe(symbol)`)을 즉시 지시할 수 있어야 함.

3. **[관찰 2 연계]**:
   - 복수 종목을 스크리닝하여 순차/배치 매매할 때, 포트폴리오 에쿼티가 왜곡되는 문제를 방지하려면 `get_total_equity` 호출 시 단일 `{symbol: current_price}`가 아닌 `self.engine._last_market_prices` 전체를 전달해야 함.

4. **[관찰 3, 5 연계]**:
   - 기존 `step(symbol, action, quantity=1)` 시그니처를 수정하면 기존 테스트(`test_live_learning_simulator.py`)가 깨질 수 있으므로, 하위 호환성을 100% 유지하면서 포지션 비중($w$)을 지원하는 확장 메서드 `step_symbol(symbol, action, quantity=None, position_weight=1.0)`을 제공해야 함.

---

## 3. Caveats (제약 사항 및 가정)

1. **전일 동시간대 거래량 데이터 확보**:
   - 틱 데이터 자체에 `prev_same_time_volume`이 포함되어 전달되거나, 스크리너가 일봉/분봉 수집기로부터 사전에 구축한 거래량 프로파일 캐시(`volume_profile`)를 참조할 수 있어야 합니다.
   - 만약 기준 데이터가 없는 경우를 대비해 `min_volume_threshold`(예: 10,000주) 및 결측 안전 Fallback 로직이 설계에 포함되었습니다.
2. **코드 수정 범위**:
   - 본 탐색자는 Read-only Explorer 규칙에 따라 소스 코드를 직접 수정하지 않았으며, 모든 설계 및 인터페이스 시그니처 제안은 `survey_engine.md`에 상세히 기술되었습니다.

---

## 4. Conclusion (최종 결론)

Auto_Stock의 Phase 5 Dynamic Stock Screener 개발을 위한 RL 엔진 탐색 및 연동 인터페이스 설계가 완료되었습니다.
1. **R2 명세**:
   - `TickData` 기반 포맷 확정 (`symbol`, `price`, `open_price`, `volume`, `accum_volume`, `prev_same_time_volume`).
   - `check_intraday_trigger` 트리거 판정 규칙 확정 (감시 풀 소속 검증 + 시가 대비 3% 급등 + 전일 대비 300% 거래량 폭증 + 쿨다운 디바운스).
2. **R4 연동 인터페이스**:
   - `LiveLearningSimulator`에 `inject_triggered_symbol`, `build_rl_observation`(14차원 정규화 obs), `step_symbol`(비중 기반 사이징 및 다중 종목 에쿼티 정합성 보장), `process_triggered_queue` 신규 메서드 설계 완료.
   - 기존 인터페이스와의 100% 하위 호환성 보장 방안 확립.
3. **상세 설계서**:
   - `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_2/survey_engine.md`에 전체 코드 구조, 클래스 다이어그램, 메서드 시그니처 및 구현 가이드 완비.

---

## 5. Verification Method (독립 검증 방법)

1. **상세 설계서 검토**:
   - 대상 파일: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_p5_2/survey_engine.md`
   - 확인 항목: R2 틱 데이터 포맷, `check_intraday_trigger` 시그니처, R4 `inject_triggered_symbol` 및 `build_rl_observation` 메서드 설계.
2. **기존 테스트 스위트 회귀 검증**:
   - 명령어: `/home/imnyj/venv/bin/pytest tests/test_live_learning_simulator.py tests/test_hybrid_trading_env.py`
   - 통과 조건: 18개 테스트 100% Pass.
3. **무효화 조건 (Invalidation Conditions)**:
   - `LiveLearningSimulator`의 기존 `step` 및 `get_state` 반환 형식을 변경하여 기존 테스트가 실패하는 경우.
   - `check_intraday_trigger`에서 쿨다운 메커니즘 부재로 고빈도 틱 시 매 틱마다 중복 트리거가 발생하는 경우.
