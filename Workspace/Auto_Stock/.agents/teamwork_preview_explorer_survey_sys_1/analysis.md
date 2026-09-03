# Auto_Stock 시스템 아키텍처 / 동시성 / 메모리 / 논리 결함 전수 조사 분석 보고서 (Survey Agent 1)

**작성자**: Explorer (Survey Agent 1 - System & Concurrency Specialist)  
**작성 일시**: 2026-09-02T17:09:00+09:00  
**프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`  
**보고서 위치**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_survey_sys_1/analysis.md`  

---

## 1. 개요 및 조사 목적

본 보고서는 Auto_Stock 프로젝트의 **Area 1: 치명적 결함(System/Architecture, Concurrency/Multiprocessing, Memory/Resource, Logical Bugs & Edge Cases)** 영역에 대한 전수 검토 및 심층 분석 결과를 기술합니다.

전체 코드베이스와 18개 테스트 파일(총 426개 테스트 항목) 및 보조 스크립트를 정밀 스캔하여, 잠재적 크래시, 메모리/소켓 누수, 스레드 레이스 컨디션, 데이터 오염, 아키텍처 불일치 및 기존 테스트 실패 원인을 명확한 코드 증거(라인 번호, 스니펫, 근본 원인, 구체적 수정 방안)와 함께 제시합니다.

---

## 2. 프로젝트 구조 및 기존 테스트 현황 분석

### 2.1 전체 모듈 아키텍처

```
Auto_Stock/
├── core/                           # 핵심 기반 모듈
│   ├── config.py                   # 계층적 설정 관리 및 SecretStr 시크릿 캡슐화
│   └── kiwoom_api.py               # 키움 REST API (2024) 통신 클라이언트 및 토큰 매니저
├── modules/
│   ├── data/                       # 데이터 수집, 검증, PIT 통합 모듈
│   │   ├── collector_price.py      # OHLCV 시계열 수집, 결측치 정제 및 리샘플링
│   │   ├── collector_fundamental.py # DART / Naver 펀더멘털 수집 및 교차 검증
│   │   ├── consolidator.py         # Point-in-Time merge_asof 및 Parquet I/O
│   │   ├── pipeline.py             # 데이터 수집-검증-저장 통합 파이프라인
│   │   └── streamer.py             # 실시간 틱 수신, CircularBuffer 및 캔들 집계
│   ├── engine/                     # 거래 체결 및 Gymnasium 환경
│   │   ├── mock_environment.py     # VirtualAccount (1원 정밀 회계), MockExecutionEngine
│   │   ├── hybrid_trading_env.py   # Gymnasium 1.2.0 호환 HybridTradingEnv
│   │   ├── live_learning_simulator.py # 키움 REST API 연동 실시간 모의 학습 시뮬레이터
│   │   └── manual_trader.py        # CLI 기반 수동 매매 제어기 (Rich 포맷팅 지원)
│   ├── models/                     # 지도학습(SL) 및 강화학습(RL) 신경망
│   │   ├── feature_extractor.py    # 1D-CNN + MLP DualStream 및 SLPretrainer
│   │   └── hybrid_policy.py        # HybridActorCritic, HybridPPO, SB3 어댑터
│   └── hpo/                        # 하이퍼파라미터 최적화
│       ├── metrics.py              # 샤프지수(0-분산 방어), MDD, 승률 지표 계산
│       ├── optuna_pipeline.py      # Optuna TPESampler/MedianPruner 파이프라인
│       └── exporter.py             # 20개 컬럼 스키마 원자적 CSV 내보내기 (fcntl.flock)
├── scripts/
│   └── run_hpo.py                  # HPO CLI 실행 엔트리포인트
├── tests/                          # 18개 정규 및 적대적 테스트 스위트 (426 items)
├── etc/                            # 보조 스크립트, HPO 결과 및 로그 저장소
└── backup/                         # 과거 버전 백업 디렉토리
```

### 2.2 테스트 스위트 실행 결과 및 현황

- **전체 수집 항목**: 426개 테스트 케이스 (18개 테스트 파일)
- **실행 결과**: **407 PASSED / 19 FAILED / 22 WARNINGS**
- **실패 항목 분포**:
  1. `tests/test_adversarial_m2_rl_challenger.py` (5건 실패): GAE 오라클 인덱싱 불일치
  2. `tests/test_phase3_api.py` (14건 실패): `core/kiwoom_api.py`와 테스트 목(Mock) 스키마 간 API 계약 불일치 및 32자 정규식 오탐
  3. `etc/scripts/test_extreme_4_1.py` (1건 수집 크래시): 모듈 임포트 시 탑레벨 실행으로 인한 전체 `pytest` 컬렉션 중단

---

## 3. 치명적 결함 심층 조사 (Area 1 Findings)

---

### 카테고리 1: 논리적 버그 및 예외 처리 결함 (Logical Bugs & Edge Cases)

#### [BUG-L01] `KiwoomClient.get_account_balance`: API null 반환 시 `Decimal("None")` 크래시
- **위치**: `core/kiwoom_api.py:343-346`
- **코드 스니펫**:
  ```python
  deposit_received = Decimal(str(res.get("prsm_dpst_aset_amt", 0)))
  total_eval_amount = Decimal(str(res.get("tot_evlt_amt", 0)))
  total_eval_pnl = Decimal(str(res.get("tot_evlt_pl", 0)))
  ```
- **문제 원인**:
  증권사 REST API 응답 JSON에 특정 필드가 명시적 `null`로 올 경우(예: `{"prsm_dpst_aset_amt": null}`), Python `dict.get("key", 0)`은 기본값 `0` 대신 `None`을 반환합니다. `str(None)`은 `"None"`이 되며, 이를 `Decimal("None")`으로 변환 시 `decimal.InvalidOperation` 예외가 발생하여 잔고 조회가 크래시됩니다.
- **권장 수정 방안**:
  ```python
  deposit_received = Decimal(str(res.get("prsm_dpst_aset_amt") or 0))
  total_eval_amount = Decimal(str(res.get("tot_evlt_amt") or 0))
  total_eval_pnl = Decimal(str(res.get("tot_evlt_pl") or 0))
  ```

---

#### [BUG-L02] `PriceDataCollector.validate_and_clean_ohlcv`: `fillna(0.0)`로 인한 `low` 가격 0원 오염
- **위치**: `modules/data/collector_price.py:715-732`
- **코드 스니펫**:
  ```python
  df_clean['open'] = pd.to_numeric(df_clean['open'], errors='coerce').fillna(0.0).astype(float)
  df_clean['high'] = pd.to_numeric(df_clean['high'], errors='coerce').fillna(0.0).astype(float)
  df_clean['low'] = pd.to_numeric(df_clean['low'], errors='coerce').fillna(0.0).astype(float)
  df_clean['close'] = pd.to_numeric(df_clean['close'], errors='coerce').fillna(0.0).astype(float)
  ...
  computed_low = df_clean[['open', 'high', 'low', 'close']].min(axis=1)
  df_clean['low'] = computed_low
  ```
- **문제 원인**:
  입력 데이터프레임에서 `open`이나 `high`에 일시적 결측치(NaN)가 있어 `fillna(0.0)`이 적용되면, 뒤이어 실행되는 `computed_low = min(open, high, low, close)`가 `0.0`을 선택하게 됩니다. 이로 인해 정상적인 양수였던 `low` 가격까지 영구적으로 `0.0`으로 덮어씌워져 주가 데이터가 심각하게 왜곡됩니다.
- **권장 수정 방안**:
  가격 컬럼 결측치는 0.0으로 채우지 않고 이전 유효 가격으로 forward-fill하거나, 유효한 양수값들에 대해서만 `min`을 산출하도록 방어 로직 적용:
  ```python
  for col in ['open', 'high', 'low', 'close']:
      df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').ffill().bfill().fillna(100.0)
  ```

---

#### [BUG-L03] `DataConsolidator.consolidate_point_in_time`: `merge_asof` 다중 종목 펀더멘털 교차 오염
- **위치**: `modules/data/consolidator.py:147-154`
- **코드 스니펫**:
  ```python
  merged = pd.merge_asof(
      p_df,
      f_df,
      left_on='date',
      right_on='announcement_date',
      direction='backward',
      suffixes=('', '_fund')
  )
  ```
- **문제 원인**:
  `f_df`에 여러 종목의 재무제표가 포함되어 있을 경우, `by='symbol'` 인자가 누락되어 주가 시점 이전의 가장 최신 공시를 무조건 병합합니다. 즉, 삼성전자 주가 데이터에 직전 공시된 SK하이닉스의 재무제표가 결합되는 치명적인 데이터 교차 오염(Cross-Contamination)이 발생합니다.
- **권장 수정 방안**:
  `by='symbol'` 인자를 추가하고, 병합 전 `f_df`를 `symbol`별로 분리하거나 단일 종목으로 필터링:
  ```python
  if symbol and 'symbol' in f_df.columns:
      f_df = f_df[f_df['symbol'] == symbol].copy()
  merged = pd.merge_asof(
      p_df,
      f_df,
      left_on='date',
      right_on='announcement_date',
      by='symbol' if ('symbol' in p_df.columns and 'symbol' in f_df.columns) else None,
      direction='backward',
      suffixes=('', '_fund')
  )
  ```

---

#### [BUG-L04] `HybridTradingEnv`: 관망(HOLD) 스텝에서 이전 `trade_record` 상태 누출 (Stale State Leak)
- **위치**: `modules/engine/hybrid_trading_env.py:587`
- **코드 스니펫**:
  ```python
  "trade_record": trade_record or self._last_trade_record,
  ```
- **문제 원인**:
  에이전트가 현재 스텝에서 `HOLD`(0) 액션을 취하거나 체결되지 않은 경우 `trade_record`는 `None`입니다. 하지만 `trade_record or self._last_trade_record`로 인해 이전 스텝의 매매 기록이 반환되어, 하류 모듈(성과 분석기, 백테스터)이 현재 스텝에서도 매매가 일어난 것으로 잘못 집계합니다.
- **권장 수정 방안**:
  현재 스텝에서 발생한 체결 내역만 정확히 반환:
  ```python
  "trade_record": trade_record,
  ```

---

#### [BUG-L05] `test_adversarial_m2_rl_challenger.py`: GAE 오라클 인덱싱 오류 (Off-by-One)
- **위치**: `tests/test_adversarial_m2_rl_challenger.py:207, 312`
- **코드 스니펫**:
  ```python
  next_non_terminal = 1.0 - float(dones[t + 1])
  ```
- **문제 원인**:
  테스트의 `_ground_truth_gae` 함수에서 `dones[t + 1]`을 참조하여, $t$ 시점의 전이 종료 여부를 $t+1$ 시점의 완료 플래그로 잘못 검증함. 이로 인해 모델의 올바른 `RolloutBuffer` 구현(`1.0 - dones[t]`)과 불일치가 발생하여 5개 테스트가 실패함.
- **권장 수정 방안**:
  `_ground_truth_gae` 내부의 `dones[t + 1]`을 `dones[t]`로 수정.

---

#### [BUG-L06] `collector_fundamental.py`: 0원 이익 / 0% 마진 불리언 Falsy 오작동
- **위치**: `modules/data/collector_fundamental.py:461-470, 654-658`
- **코드 스니펫**:
  ```python
  if stmt.revenue and stmt.operating_profit:
      stmt.op_margin = round((stmt.operating_profit / stmt.revenue) * 100, 2)
  ```
- **문제 원인**:
  영업이익이 0원(손익분기점)일 때 `stmt.operating_profit == 0`이 `False`로 평가되어 `op_margin` 계산을 건너뛰고 `None`으로 남는 결함.
- **권장 수정 방안**:
  ```python
  if stmt.revenue is not None and stmt.operating_profit is not None and stmt.revenue != 0:
      stmt.op_margin = round((stmt.operating_profit / stmt.revenue) * 100, 2)
  ```

---

### 카테고리 2: 메모리 누수 및 리소스 관리 결함 (Memory Leaks & Resource Management)

#### [BUG-M01] HTTP `requests.Session()` 미해제 소켓 및 파일 디스크립터 누수
- **위치**:
  - `modules/data/collector_price.py:112` (`NaverPriceFetcher`)
  - `modules/data/collector_fundamental.py:326` (`OpenDartCollector`)
  - `modules/data/collector_fundamental.py:546` (`NaverFinanceCollector`)
  - `modules/data/streamer.py:636` (`NaverPollingStreamer`)
- **문제 원인**:
  내부에서 `requests.Session()`을 인스턴스화하지만 `close()` 메서드나 `__enter__/__exit__` 컨텍스트 매니저 인터페이스를 제공하지 않음. 배치 수집 파이프라인에서 수집기 객체가 반복 생성/폐기될 때 열려 있는 TCP 연결 풀과 OS 소켓 파일 디스크립터가 GC 시점까지 누수됨.
- **권장 수정 방안**:
  모든 수집기 및 스트리머 클래스에 `close()` 및 Context Manager 지원 추가:
  ```python
  def close(self) -> None:
      if hasattr(self, "session") and self.session:
          self.session.close()

  def __enter__(self):
      return self

  def __exit__(self, exc_type, exc_val, exc_tb):
      self.close()
  ```

---

#### [BUG-M02] `NaverPollingStreamer.stop()` 타임아웃 불일치로 인한 좀비 스레드 누수
- **위치**: `modules/data/streamer.py:730-749`
- **코드 스니펫**:
  ```python
  def stop(self) -> None:
      self._stop_event.set()
      if self._thread and self._thread.is_alive():
          self._thread.join(timeout=2.0)
      self._is_running = False
  ```
- **문제 원인**:
  `_poll_symbol`의 HTTP 타임아웃은 `self.timeout = 5`초인데, `stop()`의 `join` 대기시간은 2.0초로 짧습니다. 네트워크 응답이 지연되는 동안 `stop()`이 호출되면 2초 후 `_is_running = False`로 풀리고 스레드는 5초간 백그라운드에 남아있게 됩니다. 이 상태에서 `start()`가 재호출되면 미종료 스레드가 방치되어 좀비 스레드가 누적됩니다.
- **권장 수정 방안**:
  `join` 타임아웃을 `self.timeout + 1.0` 이상으로 설정하고, 세션을 종료하여 블로킹 I/O를 즉각 인터럽트:
  ```python
  def stop(self) -> None:
      if not self._is_running:
          return
      self._stop_event.set()
      if self.session:
          self.session.close()
      if self._thread and self._thread.is_alive():
          self._thread.join(timeout=self.timeout + 1.0)
      self._is_running = False
  ```

---

#### [BUG-M03] `CircularBuffer` 다중 종목 스트리밍 시 딕셔너리 무한 증식 (Unbounded Growth)
- **위치**: `modules/data/streamer.py:154-165`
- **문제 원인**:
  `_buffers: Dict[str, deque]`에서 각 종목 큐는 `maxlen=50000`으로 제한되나, 수집 대상 종목 수가 늘어날 경우 키 딕셔너리 자체는 절대 제거되지 않고 메모리를 점유함.
- **권장 수정 방안**:
  `max_symbols` 한도를 두고 오래된 종목을 정리하거나 `clear(symbol)` API를 강화.

---

### 카테고리 3: 멀티프로세싱 및 동시성 결함 (Multiprocessing & Concurrency)

#### [BUG-C01] `TokenManager`: 스레드 락 부재로 인한 토큰 갱신 Race Condition
- **위치**: `core/kiwoom_api.py:156-209`
- **문제 원인**:
  `TokenManager`에 동기화 락(`threading.Lock`)이 없어, 토큰이 만료된 순간 여러 워커 스레드가 동시에 `get_access_token()`을 호출하면 모든 스레드가 `refresh_token()`으로 진입하여 수십 건의 중복 HTTP POST 요청을 전송함 (API Rate Limit 소진 및 불필요한 트래픽 유발).
- **권장 수정 방안**:
  `TokenManager`에 `self._lock = threading.Lock()`을 선언하고 Double-Checked Locking 적용:
  ```python
  def get_access_token(self, force_refresh: bool = False) -> str:
      if force_refresh or self.is_expired():
          with self._lock:
              if force_refresh or self.is_expired():
                  self.refresh_token()
      return self._access_token or ""
  ```

---

#### [BUG-C02] `core/config.py`: `_GLOBAL_CONFIG` 전역 싱글톤 동시성 레이스 컨디션
- **위치**: `core/config.py:330-342`
- **문제 원인**:
  `get_config(reload=True)` 또는 다중 스레드 동시 기동 시 `_GLOBAL_CONFIG` 전역 변수에 대한 원자적 락이 없어 부분적으로 초기화된 인스턴스를 참조할 위험이 존재함.
- **권장 수정 방안**:
  `_CONFIG_LOCK = threading.Lock()`으로 싱글톤 로딩 보호.

---

#### [BUG-C03] `LiveLearningSimulator`: `_GLOBAL_SIMULATOR` 전역 인스턴스 락 부재
- **위치**: `modules/engine/live_learning_simulator.py:161-168`
- **문제 원인**:
  `get_live_simulator()` 호출 시 락 없이 인스턴스를 생성하여 다중 스레드에서 중복 시뮬레이터 인스턴스가 생성되는 레이스 컨디션.
- **권장 수정 방안**:
  `threading.Lock()`을 적용하여 싱글톤 원자성 보장.

---

### 카테고리 4: 시스템 아키텍처, 설정 관리 및 테스트 정합성 결함 (Architecture, Config & Test Integrity)

#### [BUG-A01] 프로젝트 루트 디렉토리 내 임시 스크립트 방치 (Workspace Cleanliness 위반)
- **위치**: `/home/imnyj/Workspace/Auto_Stock/fix_config.py`, `fix_kiwoom_api.py`, `fix_tests.py`, `fix_tests2.py`, `test_kw.py`
- **문제 원인**:
  과거 수동 수정용 임시 스크립트들이 루트에 방치되어 있어 `GEMINI.md` Rule 5 및 Rule 10 위반.
- **권장 수정 방안**:
  `etc/scripts/` 또는 `backup/`으로 이동 및 격리.

---

#### [BUG-A02] `test_extreme_4_1.py`: 탑레벨 실행 코드로 인한 `pytest` 전체 컬렉션 크래시
- **위치**: `etc/scripts/test_extreme_4_1.py:24`
- **문제 원인**:
  `if __name__ == '__main__':` 가드 없이 모듈 임포트 시점에 `study.optimize(_obj, n_trials=1)`을 즉시 실행하여 `pytest` 전체 스위트 수집(Collection)을 실패시킴 (`ValueError: '4' not in (32, 64, 128, 256)`).
- **권장 수정 방안**:
  스크립트 코드를 `if __name__ == "__main__":` 블록 내부로 감싸거나 `pytest` 수집 대상에서 제외.

---

#### [BUG-A03] `tests/test_phase3_api.py`와 `core/kiwoom_api.py` 간 API 계약 불일치
- **위치**: `tests/test_phase3_api.py:180-400` vs `core/kiwoom_api.py`
- **문제 원인**:
  1. `test_phase3_api.py`의 목(Mock) 페이로드는 KIS 구형 포맷(`stck_prpr`, `output1` 등), `core/kiwoom_api.py`는 2024 키움 REST 포맷(`cur_prc`, `ord_no` 등)을 파싱하여 14개 테스트 실패.
  2. `client.get_account_positions()` 편의 메서드 미구현.
  3. `TokenManager.revoke_token()` 미구현.
  4. `OrderResult.order_type` 반환값 포맷 차이 (`"3"` vs `"MARKET"`).
  5. `test_forensic_static_audit_zero_hardcoded_secrets` 정규식이 `modules/hpo/__init__.py`의 `calculate_annualized_sharpe_ratio`(33자)를 비밀키로 오탐.
- **권장 수정 방안**:
  키움 2024 REST API 규격에 맞추어 `core/kiwoom_api.py`와 `test_phase3_api.py`의 계약을 완전 일치시키고, 32자 정규식에 허용 목록(Whitelist) 추가.

---

## 4. 결함 요약 및 심각도 매트릭스

| ID | 카테고리 | 대상 파일 및 라인 | 심각도 | 핵심 결함 내용 |
|---|---|---|:---:|---|
| **BUG-L01** | 논리/예외 | `core/kiwoom_api.py:343` | **High** | API null 응답 시 `Decimal("None")` 크래시 |
| **BUG-L02** | 논리/데이터 | `modules/data/collector_price.py:715` | **High** | NaN 채우기 후 `min` 산출로 주가 0원 오염 |
| **BUG-L03** | 논리/데이터 | `modules/data/consolidator.py:147` | **High** | `merge_asof` 종목 필터 부재로 타사 재무제표 오염 |
| **BUG-L04** | 논리/상태 | `modules/engine/hybrid_trading_env.py:587` | **Medium** | 관망(HOLD) 스텝에서 이전 매매기록 누출 |
| **BUG-L05** | 논리/테스트 | `tests/test_adversarial_m2_rl_challenger.py:207` | **Medium** | GAE 오라클 인덱싱 오류로 테스트 5건 실패 |
| **BUG-L06** | 논리/수식 | `modules/data/collector_fundamental.py:461` | **Low** | 0원 영업이익/0% ROE에 대한 마진 미계산 |
| **BUG-M01** | 메모리/자원 | `collector_price.py`, `collector_fundamental.py` | **High** | `requests.Session()` 미해제 소켓/FD 누수 |
| **BUG-M02** | 메모리/자원 | `modules/data/streamer.py:730` | **Medium** | `stop()` 타임아웃 불일치로 인한 좀비 스레드 누수 |
| **BUG-M03** | 메모리/자원 | `modules/data/streamer.py:154` | **Low** | `CircularBuffer` 종목 딕셔너리 무한 증식 |
| **BUG-C01** | 동시성 | `core/kiwoom_api.py:156` | **High** | `TokenManager` 락 부재로 토큰 갱신 Race Condition |
| **BUG-C02** | 동시성 | `core/config.py:330` | **Medium** | `_GLOBAL_CONFIG` 전역 싱글톤 동시성 레이스 |
| **BUG-C03** | 동시성 | `modules/engine/live_learning_simulator.py:161` | **Low** | 전역 시뮬레이터 인스턴스 락 부재 |
| **BUG-A01** | 아키텍처 | 루트 디렉토리 (`fix_*.py`, `test_kw.py`) | **Medium** | 임시 파일 방치 (Workspace Cleanliness 위반) |
| **BUG-A02** | 아키텍처 | `etc/scripts/test_extreme_4_1.py:24` | **High** | 탑레벨 실행으로 `pytest` 전체 컬렉션 실패 |
| **BUG-A03** | 아키텍처 | `tests/test_phase3_api.py` vs `core/kiwoom_api.py` | **High** | API 인터페이스 계약 불일치로 14건 실패 |

---

## 5. 결론 및 후속 조치 제언

1. **리팩토링 및 버그 수정 우선순위**:
   - **Phase 1 (치명적 오류 차단)**: BUG-A02 (pytest 크래시 방지), BUG-L01 (Decimal None 크래시 방어), BUG-C01 (TokenManager 스레드 락 적용)
   - **Phase 2 (데이터 및 자원 무결성)**: BUG-L02 (주가 0원 오염 방어), BUG-L03 (merge_asof 종목별 격리), BUG-M01 (requests.Session close 추가), BUG-M02 (좀비 스레드 방지)
   - **Phase 3 (테스트 정합성 및 정리)**: BUG-A03 (`test_phase3_api.py` 키움 REST 스키마 정합화), BUG-L05 (GAE 테스트 인덱스 수정), BUG-A01 (루트 임시파일 `backup/` 격리)
2. **테스트 통과 목표**: 상기 결함 수정 시 현재 19개 FAILED 및 1개 Collection Error가 모두 해소되어 **426 / 426 (100%) PASS** 달성 가능.
