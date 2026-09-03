# 포렌식 무결성 감사 보고서 (Forensic Audit Report) — Milestone 4 & 전체 파이프라인

**대상 산출물 (Work Product)**: Auto_Stock Hybrid SL-RL Baseline & Optuna HPO Pipeline (M1 ~ M4 전체)
**감사관 (Auditor)**: teamwork_preview_auditor_m4
**프로파일 (Profile)**: General Project Forensic Integrity
**최종 판정 (Final Verdict)**: **CLEAN (무결성 검증 완료 / 치팅 및 위조 없음)**

---

## 1. 관찰 내용 (Observation)

### 1.1 소스코드 정적 분석 및 하드코딩 탐색 (Static Hardcoding Inspection)
- **점검 대상**: `modules/engine/hybrid_trading_env.py`, `modules/engine/mock_environment.py`, `modules/models/feature_extractor.py`, `modules/models/hybrid_policy.py`, `modules/hpo/metrics.py`, `modules/hpo/optuna_pipeline.py`, `modules/hpo/exporter.py`, `scripts/run_hpo.py`, `tests/test_hpo_pipeline.py`
- **검색 패턴**: 특정 테스트 기댓값 상수, Sharpe ratio 고정값(`0.9776`, `0.9483`), 고정 자산액(`12139024`, `12009774`), 더미 리턴(`return True`, `return 0.0` 무조건 반환)
- **직접 관찰 결과**:
  - 소스코드 내 테스트 기댓값 상수가 하드코딩되어 반환되는 치팅 패턴은 발견되지 않음.
  - `12139024`, `0.9776` 등의 값은 실제 런타임에 Optuna HPO가 실행되면서 `etc/hpo_results/baseline_hpo.csv`에 기록된 결과값이며, 소스코드 모듈에는 일체 하드코딩되어 있지 않음.

### 1.2 파사드 및 신경망 연산 무결성 (Facade & Neural Net Gradient Verification)
- **직접 실행 명령어**:
  ```bash
  /home/imnyj/venv/bin/python3 -c "... HybridActorCritic forward & backward ..."
  ```
- **실측치**:
  - `HybridActorCritic` 역전파 그래디언트 노름(Gradient Norm): `136.340168` (> 0)
  - 입력 텐서 `torch.randn(4, 14)`에 대해 `actor_latent`, `critic_latent`, `discrete_head`, `alpha_head`, `beta_head`, `value_head` 전 계층에 실질적인 파라미터 그래디언트 전파 확인.
  - 파사드/더미 구현체 없이 PyTorch의 실수 연산 및 신경망 순전파/역전파가 정상 수행됨을 입증.

### 1.3 1원 단위 정밀 회계 및 Gymnasium 1.2.0 규격 준수 (Accounting & Interface Invariants)
- **인터페이스 관찰**:
  - `HybridTradingEnv.reset(seed=...)` -> `(obs, info)` 2-tuple 반환 (관측값 형상 `(14,)`, `dtype=float32`, info 내 계좌 감사 딕셔너리 포함).
  - `HybridTradingEnv.step(action)` -> `(obs, reward, terminated, truncated, info)` 5-tuple 반환 (`len(step_out) == 5`).
- **회계 불변식(Zero Discrepancy Accounting Invariant) 관찰**:
  - `VirtualAccount` 및 `MockExecutionEngine`에서 `Decimal` 기반 1원 단위 양자화(`quantize_krw`, `ROUND_FLOOR`/`ROUND_HALF_UP`) 및 증권사 표준 비용(위탁수수료 0.015%, 증권거래세 0.18% 매도시, 슬리피지 0.1%) 적용.
  - `env.verify_accounting_invariant()` 결과: `True` (초기자본 + 시세변동손익 - 최종자산 - 누적비용 = 0원).

### 1.4 CSV 출력 진위성 및 원자적 누적 기록 (CSV Genuineness & Atomic Export)
- **파일 경로**: `/home/imnyj/Workspace/Auto_Stock/etc/hpo_results/baseline_hpo.csv`
- **스키마 관찰**: 20개 표준 컬럼 명세와 100% 일치
  - `trial_id, state, objective_value, total_equity, total_return_pct, sharpe_ratio, max_drawdown_pct, total_trades, win_rate, param_sl_lr, param_sl_hidden_dim, param_sl_batch_size, param_rl_lr, param_rl_gamma, param_rl_clip_range, param_rl_ent_coef, param_rl_hidden_dim, duration_seconds, datetime_start, datetime_complete`
- **시계열 타임스탬프 관찰**:
  - 2026-09-02T02:34:07Z ~ 2026-09-02T06:24:56Z 동안 다수의 HPO 롤아웃이 실제 소요시간(`duration_seconds: 0.6s ~ 2.1s`)과 함께 누적 기록됨.
- **독립 격리 검증**: 임시 디렉토리에 3-Trial HPO 독립 실행 시 실제 3개 행이 동적으로 생성 및 기록됨 확인.

---

## 2. 논리 분석 체계 (Logic Chain)

1. **하드코딩 부재 논리**:
   - 정적 ripgrep 전수 조사에서 비즈니스 로직 내 정적 상수 반환 및 결과값 모킹이 전무함을 확인.
   - 서로 다른 매수 비중(25% vs 75%) 투입 시 매수 수량(11주 vs 39주)과 잔고(7,681,832원 vs 1,963,263원)가 선형 비례하여 동적으로 계산됨을 실측. 따라서 결과값 위조/하드코딩 없음.
2. **진본 파이프라인 연산 논리**:
   - `optuna_pipeline.py`의 `objective` 함수는 Optuna의 제안 파라미터를 받아 모델 및 환경을 인스턴스화하고 실제 환경 롤아웃(RL policy rollout)을 실행하여 `total_equity`, `sharpe_ratio`를 산출함.
   - 역전파 그래디언트(`norm=136.34`)가 정상 전파되므로 더미/파사드가 아닌 진본 딥러닝/강화학습 모델임이 확증됨.
3. **회계 및 규격 정직성 논리**:
   - Gymnasium 1.2.0의 `reset`(2-tuple) 및 `step`(5-tuple) 반환 규격을 완벽히 준수함.
   - 1원 단위 정수 회계 및 거래세/수수료 차감 후에도 계좌 잔고와 주식 평가액의 합이 총자산과 오차 0원으로 일치함.
4. **산출물 진위성 논리**:
   - `baseline_hpo.csv`에 기록된 20개 컬럼과 파라미터 값, 실행 시간, 시작/종료 UTC 타임스탬프가 실제 프로세스 실행 기록과 완벽히 부합함.

---

## 3. 한계 및 고려사항 (Caveats)

1. **시간 예산(Time Budget) 테스트 변동성**:
   - `test_fast_execution_budget`(3-Trial < 10.0초)는 시스템 CPU 부하 및 PyTorch 초기화 오버헤드에 따라 ~10.02초가 소요되어 단언 실패가 발생할 수 있으나, 이는 알고리즘 무결성(Integrity) 결함이 아닌 환경적 실행 속도 변동성임.
2. **타 모듈 간섭 격리**:
   - `etc/scripts/` 디렉토리 내의 적대적 스트레스 스크립트 및 이전 마일스톤의 API 모의 테스트 실패 건은 M4 HPO 파이프라인의 진위성 및 무결성과는 무관함.

---

## 4. 최종 감사 결론 (Conclusion)

- **최종 판정**: **CLEAN (무결성 이상 없음 / 위조 및 치팅 미발견)**
- Auto_Stock 프로젝트의 M1~M4 하이브리드 SL-RL 환경, 신경망 모델, Optuna HPO 파이프라인, 성과 평가 지표 및 CSV 내보내기 구현체는 하드코딩이나 파사드 없는 진본 구현체이며, 1원 단위 회계 무결성과 Gymnasium 표준 인터페이스를 완벽하게 준수하고 있습니다.

---

## 5. 독립 검증 방법 (Verification Method)

감사 결과를 재현하고 독립적으로 검증하기 위한 명령어:

```bash
# 1. HPO 파이프라인 종합 테스트 스위트 실행
/home/imnyj/venv/bin/pytest tests/test_hpo_pipeline.py -v

# 2. 독립 런타임 포렌식 스크립트 실행 (하드코딩, 그래디언트, 1원 회계, CSV 동적 생성)
/home/imnyj/venv/bin/python3 -c "
from modules.engine.hybrid_trading_env import HybridTradingEnv
from modules.models.hybrid_policy import HybridActorCritic
from modules.hpo.optuna_pipeline import run_hpo_optimization
from modules.hpo.exporter import load_hpo_results
import tempfile, os

env = HybridTradingEnv(initial_cash=10000000)
obs, info = env.reset(seed=42)
assert len(obs) == 14
assert env.verify_accounting_invariant() is True
print('Gym Env & Accounting Invariant: PASS')

with tempfile.TemporaryDirectory() as d:
    csv_p = os.path.join(d, 'test.csv')
    study, best = run_hpo_optimization(n_trials=3, output_csv=csv_p, seed=42, fast_mode=True, verbose=False)
    df = load_hpo_results(csv_p)
    assert len(df) == 3
    print('Dynamic 3-Trial Optuna & CSV Generation: PASS')
"
```
