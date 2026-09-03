# Handoff Report — Survey Explorer 3 (HPO & Test Infrastructure)

## 1. Observation (관찰 사실)

### 1.1 환경 및 라이브러리 설치 현황
`/home/imnyj/venv/bin/python` 환경 조사를 통해 아래 핵심 의존성 패키지들이 이미 설치되어 정상 임포트 및 실행 가능함을 직접 확인하였습니다.
- **Optuna**: `4.8.0` (정상 작동 확인, `optuna.create_study` 및 `TPESampler` 지원)
- **PyTorch**: `2.11.0+cu130` (정상 작동 확인)
- **Stable-Baselines3**: `2.7.0` (정상 작동 확인)
- **Gymnasium**: `1.2.0` (`spaces.Tuple`, `spaces.Dict`, `spaces.Discrete`, `spaces.Box` 지원)
- **Pandas**: `2.3.3` / **NumPy**: `2.4.4` / **Pytest**: `9.0.3`

### 1.2 기존 엔진 및 데이터 현황
- **가상 체결 엔진**: `modules/engine/mock_environment.py`에 한국 시장 표준 비용(수수료 0.015%, 거래세 0.18%, 고정 슬리피지 0.1%)과 1원 단위 정밀 회계(`VirtualAccount`, `MockExecutionEngine`)가 구현되어 있음.
- **실거래 시뮬레이터**: `modules/engine/live_learning_simulator.py`에 `LiveLearningSimulator`가 구현되어 있으며, `get_state()`, `step()`, `reset()` 인터페이스를 제공함.
- **기존 테스트 현황**: `tests/test_phase1.py`, `tests/test_phase2.py`, `tests/test_live_learning_simulator.py`를 실행한 결과 **93개 테스트가 100% 통과(3.65s)**됨.
- **학습 데이터**: `data/raw/` 디렉토리에 삼성전자(`005930_consolidated.parquet`), SK하이닉스(`000660_consolidated.parquet`), 현대차(`005380_consolidated.parquet`) 등 40개 컬럼의 일봉 및 재무 지표 데이터가 적재되어 있음.

---

## 2. Logic Chain (논리적 추론 및 아키텍처 분석)

### 2.1 Optuna 기반 하이퍼파라미터 최적화(HPO) 구현 방안

#### A. 모델 파이프라인 구조
Hybrid SL-RL 모델은 크게 2단계(지도학습 특징 추출기 + 강화학습 정책망)로 구성되며, Optuna는 두 단계의 하이퍼파라미터를 체계적으로 최적화합니다.
1. **SL Feature Extractor (특징 추출기)**:
   - 입력: 기술적 지표(수익률, 변동성, 이평선 등) + 재무 지표(PER, PBR, ROE 등)
   - 구조: MLP 또는 1D-CNN (Temporal Convolution)
   - 최적화 파라미터:
     - `sl_lr`: `trial.suggest_float("sl_lr", 1e-5, 1e-2, log=True)`
     - `sl_hidden_dim`: `trial.suggest_categorical("sl_hidden_dim", [32, 64, 128, 256])`
     - `sl_batch_size`: `trial.suggest_categorical("sl_batch_size", [16, 32, 64, 128])`
     - `sl_dropout`: `trial.suggest_float("sl_dropout", 0.0, 0.5, step=0.1)`
     - `sl_num_layers`: `trial.suggest_int("sl_num_layers", 1, 3)`
2. **RL Agent (하이브리드 액션 정책망)**:
   - 입력: SL Feature Embedding ($z_{SL}$) + 시장 시세 상태 + 계좌 잔고 및 보유 포지션 정보
   - 정책망 헤드:
     - 이산 액션 헤드 (3-way Categorical: 0=HOLD, 1=BUY, 2=SELL)
     - 연속 비중 헤드 (1-dim Box: [0.0, 1.0] 포지션 매매 비중)
   - 최적화 파라미터:
     - `rl_lr`: `trial.suggest_float("rl_lr", 1e-5, 1e-3, log=True)`
     - `rl_gamma`: `trial.suggest_float("rl_gamma", 0.90, 0.999)`
     - `rl_clip_range`: `trial.suggest_float("rl_clip_range", 0.1, 0.3)`
     - `rl_ent_coef`: `trial.suggest_float("rl_ent_coef", 1e-4, 1e-1, log=True)`
     - `rl_hidden_dim`: `trial.suggest_categorical("rl_hidden_dim", [64, 128, 256])`
     - `rl_n_steps`: `trial.suggest_categorical("rl_n_steps", [64, 128, 256, 512])`

#### B. Sampler 및 Pruner 전략
- **Sampler**: `optuna.samplers.TPESampler(seed=42)`를 사용하여 탐색 효율 극대화.
- **Pruner**: `optuna.pruners.MedianPruner(n_startup_trials=2, n_warmup_steps=5)` 또는 `HyperbandPruner`를 활용하여 에포크/스텝 중간 평가치가 하위 50%에 미달하는 비유망 Trial을 조기 가지치기(Pruning)하여 탐색 시간 단축.
- **예외 안전성**: Trial 도중 손실 발산(NaN) 또는 파산 발생 시 `trial.report(metric, step)` 후 `optuna.TrialPruned()`를 발생시키거나 안전한 페널티 점수를 반환하여 전체 Study가 중단되지 않도록 보호.

---

### 2.2 목적 함수(Objective Function) 평가 지표 산출 로직

#### A. 총 수익금 (Total Equity, $E_T$)
- 가상 계좌의 에피소드 종료 시점 총 자산 평가액:
  $$E_T = \text{Cash}_T + \sum_{i} (\text{Holding}_{i, T} \times P_{i, T})$$
- 총 수익률 (Total Return %):
  $$\text{Total Return (\%)} = \frac{E_T - E_0}{E_0} \times 100$$

#### B. 샤프 지수 (Sharpe Ratio, $SR$)
- 스텝/일별 자산 수익률 시계열 ($r_t$):
  $$r_t = \frac{E_t - E_{t-1}}{E_{t-1}}, \quad t \in \{1, 2, \dots, T\}$$
- 평균 수익률 ($\mu_r$) 및 표본 표준편차 ($\sigma_r$):
  $$\mu_r = \frac{1}{T}\sum_{t=1}^T r_t, \quad \sigma_r = \sqrt{\frac{1}{T-1}\sum_{t=1}^T (r_t - \mu_r)^2}$$
- 연율화 샤프 지수 ($SR_{annualized}$):
  $$SR_{annualized} = \frac{\mu_r - r_f}{\sigma_r + \epsilon} \times \sqrt{252}$$
  - $r_f$: 무위험 이자율 (기본값: $0.0$ 또는 $0.035 / 252$)
  - $\epsilon$: 분모 0 방지 상수 ($10^{-8}$)

#### C. 목적 함수 합성 및 엣지 케이스 방어
- **단일 목적 최적화 (Sharpe Ratio 우선 + Equity 패널티)**:
  $$V_{\text{objective}}(\theta) = \begin{cases} 
  -100.0, & \text{if 파산 발생 } (E_T < 0.05 E_0) \\
  0.0, & \text{if 거래 없음 및 } \sigma_r \le \epsilon \\
  SR_{annualized}, & \text{if 정상 운용 완료 및 } \sigma_r > \epsilon 
  \end{cases}$$
- **복합 점수 최적화 (Composite Objective)**:
  $$\text{Score} = w_1 \cdot \text{clip}\left(\frac{E_T - E_0}{E_0}, -1.0, 3.0\right) + w_2 \cdot \text{clip}(SR_{annualized}, -5.0, 5.0)$$
- **다중 목적 최적화 (Multi-Objective)**:
  `optuna.create_study(directions=["maximize", "maximize"])`를 통해 $(E_T, SR)$ 파레토 프론티어 탐색 지원.

---

### 2.3 결과 저장 경로 및 CSV 명세 (`etc/hpo_results/baseline_hpo.csv`)

#### A. 디렉토리 구조 및 저장 규칙
- 저장 경로: `/home/imnyj/Workspace/Auto_Stock/etc/hpo_results/baseline_hpo.csv`
- 디렉토리 자동 생성: HPO 실행 전 `os.makedirs("etc/hpo_results", exist_ok=True)` 보장.
- 원자적 파일 쓰기(Atomic Write): Trial 완료 시마다 임시 파일에 기록 후 rename하거나 flush하여 프로세스 비정상 종료 시에도 CSV 손상을 방지.

#### B. CSV 컬럼 명세 (총 20개 컬럼)
| # | Column Name | Data Type | Description | 예시 값 |
|---|---|---|---|---|
| 1 | `trial_id` | int | Trial 번호 (0-based) | `0` |
| 2 | `state` | str | Trial 상태 (`COMPLETE`, `PRUNED`, `FAIL`) | `COMPLETE` |
| 3 | `objective_value` | float | 목적 함수 최종 반환값 | `1.8421` |
| 4 | `total_equity` | float | 최종 총 평가금 (원) | `10450000.0` |
| 5 | `total_return_pct`| float | 총 수익률 (%) | `4.50` |
| 6 | `sharpe_ratio` | float | 연율화 샤프 지수 | `1.8421` |
| 7 | `max_drawdown_pct`| float | 최대 낙폭 (%) | `-2.15` |
| 8 | `total_trades` | int | 총 체결 주문 수 | `12` |
| 9 | `win_rate` | float | 승률 (%) | `58.33` |
| 10 | `param_sl_lr` | float | SL 학습률 | `0.001` |
| 11 | `param_sl_hidden_dim`| int | SL 은닉층 차원 | `64` |
| 12 | `param_sl_batch_size`| int | SL 배치 크기 | `32` |
| 13 | `param_rl_lr` | float | RL 학습률 | `0.0003` |
| 14 | `param_rl_gamma` | float | RL 감가율 | `0.99` |
| 15 | `param_rl_clip_range`| float | PPO 클리핑 범위 | `0.2` |
| 16 | `param_rl_ent_coef` | float | 엔트로피 가중치 | `0.01` |
| 17 | `param_rl_hidden_dim`| int | RL 정책망 차원 | `128` |
| 18 | `duration_seconds` | float | Trial 소요 시간 (초) | `1.45` |
| 19 | `datetime_start` | str | 시작 시각 (ISO 8601) | `2026-09-02T11:00:00` |
| 20 | `datetime_complete`| str | 완료 시각 (ISO 8601) | `2026-09-02T11:00:01` |

---

### 2.4 승인 기준(Acceptance Criteria) 검증을 위한 테스트 구조

`tests/test_hpo_pipeline.py`에 다음 5대 핵심 검증 항목을 배치합니다:

```
[tests/test_hpo_pipeline.py]
 ├── 1. TestHybridActionSpace
 │     ├── test_hybrid_tuple_structure (spaces.Tuple: Discrete(3) + Box(0, 1, (1,)))
 │     ├── test_hybrid_dict_structure (spaces.Dict: 'discrete' + 'continuous')
 │     └── test_action_unification_and_step_execution (액션 샘플링 및 env.step 정상 처리)
 ├── 2. TestObjectiveMetrics
 │     ├── test_total_equity_calculation (현금 + 종목별 시장가 평가액 일치)
 │     ├── test_sharpe_ratio_standard (일반 수익률 곡선 연율화 계산 정확성)
 │     ├── test_sharpe_ratio_zero_variance (수익률 변동 0인 경우 0.0 반환 및 분모 0 방어)
 │     └── test_max_drawdown_calculation (고점 대비 하락폭 산출 검증)
 ├── 3. TestHPOExecutionAndStudy
 │     ├── test_hpo_pipeline_n_trials_3 (n_trials=3 완주 및 study.trials 길이 3 검증)
 │     ├── test_best_trial_retrieval (최적 파라미터 및 objective value 획득 검증)
 │     └── test_pruning_and_exception_resilience (Trial 실패 시 Study 전체 중단 방지)
 ├── 4. TestResultsExportAndSchema
 │     ├── test_baseline_hpo_csv_generation (etc/hpo_results/baseline_hpo.csv 파일 존재)
 │     ├── test_baseline_hpo_csv_row_count (최소 3개 이상의 Trial 행 기록)
 │     └── test_baseline_hpo_csv_column_schema (20개 컬럼 명세 일치 및 데이터 타입 검증)
 └── 5. TestFastExecutionMock
       └── test_fast_execution_within_time_budget (전체 테스트 5초 이내 완료)
```

---

## 3. Caveats (주의 사항 및 제약 조건)

1. **테스트 실행 속도 보장**:
   - `tests/test_hpo_pipeline.py` 실행 시 실제 수만 스텝의 RL 훈련을 진행하면 테스트 시간이 초과되므로, 테스트 픽스처에서는 `n_steps=20`, `sl_epochs=1`, `n_trials=3` 등 초경량 파라미터를 사용하여 전체 테스트가 5초 이내에 완료되도록 구성해야 합니다.
2. **무거래 및 0 분산 방어**:
   - 에이전트가 에피소드 내내 관망(HOLD)만 하여 수익률 분산이 0인 경우, 샤프 지수 계산 시 분모 0 에러가 발생하지 않도록 $\epsilon = 10^{-8}$ 처리 및 `return 0.0` 방어 로직이 반드시 포함되어야 합니다.
3. **파산 시 조기 종료 및 음수 페널티**:
   - 자산이 초기 자본의 5% 미만으로 떨어지는 파산 상태 발생 시 에피소드를 즉시 종료하고 `-100.0` 수준의 명확한 음수 보상/페널티를 부여해야 Optuna가 비정상적인 전략을 탐색하지 않습니다.
4. **결과 파일 디렉토리 자동 생성**:
   - `etc/hpo_results/` 디렉토리가 없는 환경에서도 에러 없이 생성되도록 디렉토리 존재 확인 및 생성 로직이 보장되어야 합니다.

---

## 4. Conclusion (최종 결론 및 제안 명세)

1. **모듈 분할 제안**:
   - `modules/hpo/__init__.py`: HPO 모듈 엔트리포인트
   - `modules/hpo/metrics.py`: Total Equity, Sharpe Ratio, MDD, Win Rate 등 평가 지표 산출 모듈
   - `modules/hpo/optuna_pipeline.py`: Optuna Study 생성, 파라미터 제안, 목적 함수 실행 및 Pruning 관리
   - `modules/hpo/exporter.py`: Trial 결과 집계 및 `etc/hpo_results/baseline_hpo.csv` 원자적 파일 출력기
2. **테스트 스위트 제안**:
   - `tests/test_hpo_pipeline.py`: 하이브리드 액션 공간 assertion, 지표 계산 유닛 테스트, `n_trials=3` E2E 검증, `baseline_hpo.csv` 스키마 및 행 수(>=3) 단언을 포함하는 100% 자동화 테스트 스위트.
3. **승인 기준 충족 방안**:
   - `pytest tests/test_hpo_pipeline.py` 단일 명령어로 AC1(`n_trials=3` 완주), AC2(`baseline_hpo.csv` 3건 이상 기록 및 스키마 검증), AC3(하이브리드 액션 공간 assertion)이 원스톱으로 검증됩니다.

---

## 5. Verification Method (독립적 검증 방법)

### 5.1 테스트 실행 커맨드
```bash
# 전체 HPO 파이프라인 및 테스트 스위트 실행
PYTHONPATH=. /home/imnyj/venv/bin/pytest tests/test_hpo_pipeline.py -v

# 기존 Phase 1, Phase 2, Live Simulator 회귀 테스트 동시 검증
PYTHONPATH=. /home/imnyj/venv/bin/pytest tests/test_phase1.py tests/test_phase2.py tests/test_live_learning_simulator.py tests/test_hpo_pipeline.py -v
```

### 5.2 산출물 CSV 파일 검증 커맨드
```bash
# CSV 파일 존재 및 헤더/행 수 확인
ls -la etc/hpo_results/baseline_hpo.csv
head -n 5 etc/hpo_results/baseline_hpo.csv

# Python 스크립트를 통한 데이터 무결성 검증
/home/imnyj/venv/bin/python -c "
import pandas as pd
df = pd.read_csv('etc/hpo_results/baseline_hpo.csv')
print('Trial Count:', len(df))
print('Columns:', df.columns.tolist())
assert len(df) >= 3, 'Trial count must be at least 3'
assert 'total_equity' in df.columns and 'sharpe_ratio' in df.columns
print('CSV Validation SUCCESS!')
"
```
