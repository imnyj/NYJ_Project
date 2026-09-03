# Auto_Stock Phase 6: HPO 파이프라인 및 테스트 스위트 상세 조사 및 아키텍처 설계 보고서

- **작성자**: teamwork_preview_explorer_p6_3 (Phase 6 HPO 파이프라인 및 테스트 스위트 전문 Explorer)
- **작성 일시**: 2026-09-03T11:02:30+09:00
- **작업 디렉토리**: `/home/imnyj/Workspace/Auto_Stock/.agents/teamwork_preview_explorer_p6_3`
- **프로젝트 루트**: `/home/imnyj/Workspace/Auto_Stock`
- **조사 모드**: Read-Only Investigation (소스 코드 직접 수정 0건)

---

## 1. 조사 배경 및 핵심 목표

Auto_Stock 프로젝트는 Phase 1~5를 거쳐 실시간 키움 API 연동, 데이터 수집/정합, Gymnasium 1.2.0 규격 하이브리드 트레이딩 환경, 다이내믹 종목 스크리너 엔진을 구축 완료하였습니다.
Phase 6의 핵심 목표는 **다중 시계열 데이터를 처리하는 3가지 이상의 다양한 지도학습(SL) 아키텍처(ResNet, Transformer, CVAE)를 설계하고, 이를 PPO 강화학습과 결합하여 대규모 파라미터 탐색(Large-scale HPO)을 수행하는 본 모델(Main Model) 파이프라인을 완성**하는 것입니다.

본 조사는 Phase 6의 요구사항 **R3(Large-scale HPO Pipeline)** 및 **승인 기준(Acceptance Criteria)**을 완벽히 달성하기 위해, 기존 `modules/hpo/` 코드베이스와 전체 테스트 스위트를 심층 분석하고, 구현 단계에서 발생할 수 있는 회귀(Regression) 및 충돌을 원천 차단하는 최적의 아키텍처 설계안을 도출하는 것을 목적으로 합니다.

### Phase 6 R3 및 검증 승인 기준 요약
1. **R3. Large-scale HPO Pipeline**:
   - 1D-CNN ResNet, 시계열 Attention Transformer, 잠재 공간 이상치 탐지 CVAE 각 아키텍처별 Optuna 최적화 파이프라인 구축.
2. **Acceptance Criteria 1 (`tests/test_phase6_models.py`)**:
   - 3가지 SL 아키텍처 모델들이 각각 정의된 형태의 동일한 텐서(Tensor) 입력을 받아 정상적인 형태(Shape)의 특징 벡터 출력을 반환하는지 검증.
3. **Acceptance Criteria 2 (`tests/test_phase6_hpo.py`)**:
   - 각 아키텍처별 Optuna 최적화가 최소 2회(`n_trials=2`) 이상 크래시 없이 정상 실행되고, 그 결과가 `etc/hpo_results/main_models_hpo.csv` 형태로 저장됨을 입증.
4. **Acceptance Criteria 3 (회귀 방지 및 100% Pass)**:
   - 신규 테스트를 포함한 전체 테스트 스위트(기존 18개 스위트, 497개 테스트)가 무결하게 100% Pass.

---

## 2. 기존 HPO 파이프라인 심층 분석 (`modules/hpo/`)

### 2.1 기존 파일 구성 및 역할
`modules/hpo/` 패키지는 다음 4개 핵심 파일로 구성되어 있습니다:
- `__init__.py`: 주요 함수 및 상수 인터페이스 노출.
- `optuna_pipeline.py`: Optuna Study 생성, 단일 Trial 목적함수(`objective`), 최적화 루프 실행(`run_hpo_optimization`).
- `exporter.py`: 20개 표준 컬럼 스키마 정의, `fcntl.flock` 기반 원자적 CSV 내보내기 및 스레드/프로세스 락 보호.
- `metrics.py`: Total Equity, Return %, 연율화 Sharpe Ratio(0-분산 방어), MDD %, Win Rate % 등 금융 성과 지표 계산.

### 2.2 `optuna_pipeline.py` 구조 분석 및 제약사항
1. **Study 생성 (`create_hpo_study`)**:
   - `sampler = optuna.samplers.TPESampler(seed=seed)`: TPE 베이지안 최적화 샘플러 채택. 시드 고정으로 재현성 보장.
   - `pruner = optuna.pruners.MedianPruner(n_startup_trials=2, n_warmup_steps=5, interval_steps=1)`: 초기 2개 trial 이후 하위 50% 성능 조기 가지치기.
   - `direction="maximize"`: 샤프 지수 기반 목적함수 최대화.
2. **목적함수 (`objective`)의 단일 모델 결합 제약**:
   - 라인 185~190에서 `TabularMLPFeatureExtractor`만 하드코딩되어 호출됨.
   - 탐색 공간이 MLP 파라미터(`sl_lr`, `sl_hidden_dim`, `sl_batch_size`)와 PPO 파라미터(`rl_lr`, `rl_gamma`, `rl_clip_range`, `rl_ent_coef`, `rl_hidden_dim`)로 한정되어 있음.
   - ResNet, Transformer, CVAE 등의 상이한 모델 아키텍처를 선택하거나 주입할 수 있는 인터페이스 부재.
3. **목적함수 값 계산 로직**:
   - 무거래(100% 현금 보유, `total_trades=0`) 시 `objective_value = -1.0` 패널티 (Milestone 3에서 발견된 BUG-RL05 방어).
   - 파산(잔고 50만 원 미만) 시 `objective_value = -100.0`.
   - 정상 시: `objective_value = sharpe_ratio + 0.01 * total_return_pct`.

### 2.3 `exporter.py` 스키마 제약 및 엄격성
1. **20개 고정 컬럼 스키마 (`CSV_COLUMNS`)**:
   ```python
   CSV_COLUMNS = [
       "trial_id", "state", "objective_value", "total_equity", "total_return_pct",
       "sharpe_ratio", "max_drawdown_pct", "total_trades", "win_rate",
       "param_sl_lr", "param_sl_hidden_dim", "param_sl_batch_size", "param_rl_lr",
       "param_rl_gamma", "param_rl_clip_range", "param_rl_ent_coef", "param_rl_hidden_dim",
       "duration_seconds", "datetime_start", "datetime_complete"
   ]
   ```
2. **치명적 회귀 위험 지점**:
   - `tests/test_hpo.py` (라인 219~229) 및 `tests/test_adversarial_challenger2_hpo.py` (라인 78~79):
     ```python
     assert len(CSV_COLUMNS) == 20
     assert len(df.columns) == 20
     assert list(df.columns) == CSV_COLUMNS
     ```
   - 기존 `CSV_COLUMNS`의 길이나 필드명을 직접 수정하면 기존 테스트가 즉각 실패함!
   - 따라서 `main_models_hpo.csv`용 확장 스키마는 기존 `CSV_COLUMNS`를 건드리지 않는 독립적/확장 가능한 구조로 설계되어야 함.

---

## 3. Phase 6 R3: 3개 메인 모델 Optuna HPO 파이프라인 구축 설계

### 3.1 모델 아키텍처별 특성 및 하이퍼파라미터 탐색 공간(Search Space)

| 모델 아키텍처 | 주요 레이어 및 메커니즘 | 모델 고유 HPO 파라미터 (Search Space) |
|---|---|---|
| **ResNet (1D-CNN)** | Residual Blocks, Conv1d, BatchNorm/GroupNorm, LeakyReLU/ReLU | - `resnet_num_blocks`: categorical `[2, 3, 4]`<br>- `resnet_filters`: categorical `[32, 64, 128]`<br>- `resnet_kernel_size`: categorical `[3, 5]`<br>- `resnet_dropout`: float `[0.0, 0.3]`<br>- `sl_lr`: float `[1e-4, 1e-2]` (log scale) |
| **Transformer (TimeSeries)** | Multi-Head Self-Attention, Positional Encoding, FeedForward, LayerNorm | - `tf_d_model`: categorical `[32, 64, 128]`<br>- `tf_nhead`: categorical `[2, 4, 8]`<br>  *(제약: `tf_d_model % tf_nhead == 0` 필수)*<br>- `tf_num_layers`: categorical `[1, 2, 3]`<br>- `tf_dim_feedforward`: categorical `[64, 128, 256]`<br>- `tf_dropout`: float `[0.0, 0.3]`<br>- `sl_lr`: float `[1e-4, 1e-2]` (log scale) |
| **CVAE (Latent Anomaly)** | Encoder($\mu, \sigma$), Reparameterization $z$, Decoder(Reconstruction), Condition Concatenation | - `cvae_latent_dim`: categorical `[8, 16, 32]`<br>- `cvae_hidden_dim`: categorical `[32, 64, 128]`<br>- `cvae_kl_weight` ($\beta$): float `[1e-4, 1e-1]` (log scale)<br>- `cvae_dropout`: float `[0.0, 0.3]`<br>- `sl_lr`: float `[1e-4, 1e-2]` (log scale) |

#### 공통 PPO 탐색 공간
- `rl_lr`: float `[1e-5, 1e-3]` (log=True)
- `rl_gamma`: float `[0.90, 0.999]`
- `rl_clip_range`: float `[0.1, 0.3]`
- `rl_ent_coef`: float `[1e-4, 1e-1]` (log=True)
- `rl_hidden_dim`: categorical `[64, 128, 256]`
- `batch_size`: categorical `[16, 32, 64]`

### 3.2 Transformer `d_model % nhead == 0` 제약조건 해결 방안
PyTorch `nn.MultiheadAttention`은 `d_model`이 `nhead`로 나누어떨어지지 않을 시 `ValueError: embed_dim must be divisible by num_heads` 예외를 던집니다.
Optuna 탐색 시 불일치로 인한 크래시를 방지하기 위해 다음 2가지 안전 방식을 적용합니다:
1. **조건부 샘플링 (Conditional Suggestion)**:
   ```python
   tf_nhead = trial.suggest_categorical("tf_nhead", [2, 4])
   # nhead의 배수로만 d_model 선택
   d_model_candidates = [32, 64, 128] if tf_nhead == 2 else [32, 64, 128]  # 모두 2, 4의 배수
   tf_d_model = trial.suggest_categorical("tf_d_model", d_model_candidates)
   ```
2. **동적 보정 가드 (Dynamic Auto-Correction Guard)**:
   ```python
   if tf_d_model % tf_nhead != 0:
       tf_d_model = (tf_d_model // tf_nhead) * tf_nhead
       if tf_d_model == 0:
           tf_d_model = tf_nhead
   ```

### 3.3 아키텍처별 목적함수 및 모델 팩토리 설계
`modules/hpo/optuna_pipeline.py` 내에 다형성을 지원하는 목적함수 인터페이스를 구성합니다.

```python
def objective_main_model(
    trial: optuna.Trial,
    model_type: str = "resnet",  # "resnet", "transformer", "cvae"
    symbol: str = "005930",
    data_path: Optional[str] = None,
    output_csv: str = "etc/hpo_results/main_models_hpo.csv",
    n_timesteps: int = 100,
    fast_mode: bool = True,
    seed: int = 42,
    env_kwargs: Optional[Dict[str, Any]] = None,
) -> float:
    """
    ResNet, Transformer, CVAE 3대 모델별 동적 탐색 공간 및 하이브리드 PPO 최적화 목적함수.
    """
    # 1. 모델 유형별 하이퍼파라미터 제안 (Search Space Branching)
    # 2. 모델 인스턴스화 (Model Factory)
    # 3. HybridActorCritic(feature_extractor=model) 및 HybridPPO 인스턴스화
    # 4. ppo.learn(total_timesteps=n_timesteps) 고속 학습
    # 5. HybridTradingEnv 시뮬레이션 롤아웃 및 6대 성과 지표 산출
    # 6. 원자적 CSV 저장: export_main_model_trial_to_csv()
    # 7. Sharpe Ratio + 0.01 * Return % 반환
```

### 3.4 n_trials 실행 흐름 및 러너 설계
각 아키텍처별로 독립적인 Study를 생성하거나 공통 스토리지에 아키텍처별 study_name을 부여하여 실행합니다.

```python
def run_model_hpo(
    model_type: str,  # "resnet" | "transformer" | "cvae"
    n_trials: int = 2,
    symbol: str = "005930",
    output_csv: str = "etc/hpo_results/main_models_hpo.csv",
    seed: int = 42,
    n_timesteps: int = 100,
    fast_mode: bool = True,
    study_name: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Tuple[optuna.Study, optuna.trial.FrozenTrial]:
    ...
```
- 개별 실행 편의 함수:
  - `run_resnet_hpo(...)`
  - `run_transformer_hpo(...)`
  - `run_cvae_hpo(...)`
- 통합 일괄 실행 함수:
  - `run_all_main_models_hpo(model_types=["resnet", "transformer", "cvae"], n_trials=2, ...)`

---

## 4. HPO 결과 저장 메커니즘 설계 (`etc/hpo_results/main_models_hpo.csv`)

### 4.1 스키마 설계: `MAIN_MODELS_CSV_COLUMNS`
3가지 상이한 아키텍처가 동일한 CSV 파일(`etc/hpo_results/main_models_hpo.csv`)에 Trial을 순차/병렬로 기록해야 하므로, **통합 슈퍼셋 스키마(Unified Superset Schema)**를 채택합니다.

```python
MAIN_MODELS_CSV_COLUMNS = [
    "trial_id",
    "model_type",          # "resnet", "transformer", "cvae"
    "state",               # "COMPLETE", "PRUNED", "FAIL"
    "objective_value",
    "total_equity",
    "total_return_pct",
    "sharpe_ratio",
    "max_drawdown_pct",
    "total_trades",
    "win_rate",
    # 공통 학습 파라미터
    "param_sl_lr",
    "param_rl_lr",
    "param_rl_gamma",
    "param_rl_clip_range",
    "param_rl_ent_coef",
    "param_rl_hidden_dim",
    "param_batch_size",
    # ResNet 전용 파라미터
    "param_resnet_num_blocks",
    "param_resnet_filters",
    "param_resnet_kernel_size",
    "param_resnet_dropout",
    # Transformer 전용 파라미터
    "param_tf_d_model",
    "param_tf_nhead",
    "param_tf_num_layers",
    "param_tf_dim_feedforward",
    "param_tf_dropout",
    # CVAE 전용 파라미터
    "param_cvae_latent_dim",
    "param_cvae_hidden_dim",
    "param_cvae_kl_weight",
    "param_cvae_dropout",
    # 메타 정보 및 파라미터 전체 JSON 백업
    "params_json",
    "duration_seconds",
    "datetime_start",
    "datetime_complete",
]
```

### 4.2 파일 락 기반 원자적 Append 및 동시성 안전 보장
- `modules/hpo/exporter.py`의 `_process_file_lock(abs_path, shared=False)` 컨텍스트 매니저를 직접 활용.
- 동작 원리:
  1. 쓰기 직전 `fcntl.flock(fd, fcntl.LOCK_EX)` 획득.
  2. 파일 미존재 시 `MAIN_MODELS_CSV_COLUMNS` 헤더를 먼저 기록.
  3. `csv.DictWriter(..., fieldnames=MAIN_MODELS_CSV_COLUMNS)`로 레코드 추가.
  4. `f.flush()` 및 `os.fsync(fd)`로 디스크 물리 기록 보장.
  5. 파일 락 해제 (`fcntl.LOCK_UN`).
- 이를 통해 3개 모델이 순차적이든 멀티프로세스 병렬이든 동일한 CSV에 크래시나 데이터 유실 없이 안전하게 누적 기록됨.

### 4.3 데이터 로더 및 유효성 검증 함수
```python
def load_main_models_hpo_results(
    csv_path: str = "etc/hpo_results/main_models_hpo.csv",
) -> pd.DataFrame:
    """
    main_models_hpo.csv 파일을 Shared Lock(LOCK_SH)으로 안전하게 읽고
    필수 컬럼 및 데이터 무결성을 검증합니다.
    """
```

---

## 5. Phase 6 테스트 스위트 구성 요건 명세

### 5.1 `tests/test_phase6_models.py` 구성 요건

이 테스트 파일은 Phase 6 R1 요구사항 및 승인 기준 1번을 검증하는 전용 스위트입니다.

```
tests/test_phase6_models.py
├── TestPhase6ModelShapes (입출력 텐서 형상 검증)
│   ├── test_resnet1d_tensor_shapes
│   ├── test_transformer_tensor_shapes
│   ├── test_cvae_tensor_shapes
│   └── test_unbatched_and_numpy_inputs
├── TestPhase6ModelMechanisms (모델별 고유 메커니즘 검증)
│   ├── test_resnet_residual_connection_and_gradients
│   ├── test_transformer_attention_and_head_divisibility
│   ├── test_cvae_reparameterization_and_losses
│   └── test_nan_and_inf_resilience
└── TestPhase6ModelRLIntegration (하이브리드 Actor-Critic 결합 검증)
    ├── test_actor_critic_with_resnet_backbone
    ├── test_actor_critic_with_transformer_backbone
    └── test_actor_critic_with_cvae_backbone
```

#### 핵심 테스트 케이스 상세:
1. **공통 입력 텐서 규격**:
   - `seq_len = 20`, `in_channels = 10`, `batch_size = 4`
   - Batched Tensor: `torch.randn(4, 20, 10)`
   - Unbatched Tensor: `torch.randn(20, 10)`
   - 출력 형상: Batched는 `(4, feature_dim)`, Unbatched는 `(feature_dim,)`
2. **Transformer Attention 검증**:
   - `d_model % nhead == 0` 유효 조합 정상 작동 단언.
   - `d_model % nhead != 0` 부적합 입력 시 명확한 ValueError 또는 자동 가드 동작 확인.
3. **CVAE 이상치 탐지 및 잠재 표현 검증**:
   - `encode(x, condition) -> mu, logvar`
   - `reparameterize(mu, logvar) -> z`
   - `decode(z, condition) -> recon_x`
   - 손실함수 `recon_loss + kl_weight * kl_loss` 역전파 시 정상 그래디언트 생성 단언.

### 5.2 `tests/test_phase6_hpo.py` 구성 요건

이 테스트 파일은 Phase 6 R3 요구사항 및 승인 기준 2번을 검증하는 전용 스위트입니다.

```
tests/test_phase6_hpo.py
├── TestPhase6ArchitectureHPO (아키텍처별 n_trials=2 최적화 완주 검증)
│   ├── test_resnet_hpo_2_trials
│   ├── test_transformer_hpo_2_trials
│   └── test_cvae_hpo_2_trials
├── TestPhase6HPOCSVExport (etc/hpo_results/main_models_hpo.csv 검증)
│   ├── test_main_models_hpo_csv_creation_and_accumulation
│   ├── test_main_models_hpo_schema_integrity
│   └── test_main_models_hpo_metrics_validity
└── TestPhase6HPOConcurrencyAndResilience (동시성 및 내결함성 검증)
    ├── test_concurrent_csv_writes_thread_safety
    └── test_trial_pruning_and_exception_resilience
```

#### 핵심 테스트 케이스 상세:
1. **각 아키텍처별 최소 2회(n_trials=2) 최적화 완주**:
   - `run_model_hpo(model_type="resnet", n_trials=2, output_csv=tmp_csv, fast_mode=True)`
   - `run_model_hpo(model_type="transformer", n_trials=2, output_csv=tmp_csv, fast_mode=True)`
   - `run_model_hpo(model_type="cvae", n_trials=2, output_csv=tmp_csv, fast_mode=True)`
2. **`main_models_hpo.csv` 누적 저장 검증**:
   - `assert len(df) >= 6` (3개 모델 × 2회)
   - `assert set(df["model_type"].unique()) == {"resnet", "transformer", "cvae"}`
   - `assert (df["state"] == "COMPLETE").all()` (또는 `{"COMPLETE", "PRUNED"}`)
   - `assert not df["objective_value"].isna().any()`
   - `assert (df["total_equity"] > 0).all()`
3. **타임 버짓 최적화 (Fast Mode)**:
   - 각 trial의 `n_timesteps=32~64`, `n_epochs=1~2`를 적용하여 3개 모델 × 2회 = 6개 trial이 총 15초 이내에 신속 완주되도록 설계.

---

## 6. 기존 18개 테스트 스위트와의 충돌 분석 및 회귀 방지 전략

### 6.1 `CSV_COLUMNS` 변경 금지 원칙 (최우선 과제)
- **현상**: `tests/test_hpo.py` 및 `tests/test_adversarial_challenger2_hpo.py`에서 `CSV_COLUMNS`의 길이가 정확히 20인지 엄격히 단언(`assert len(CSV_COLUMNS) == 20`).
- **해결책**:
  - 기존 `modules/hpo/exporter.py`의 `CSV_COLUMNS`, `export_trial_to_csv()`, `load_hpo_results()`는 **100% 원형 보존**.
  - Phase 6용으로 `MAIN_MODELS_CSV_COLUMNS`, `export_main_model_trial_to_csv()`, `load_main_models_hpo_results()`를 별도로 추가.
  - 또는 `export_trial_to_csv`에 `columns: Optional[List[str]] = None` 기본값을 주어 기존 호출에는 20개 컬럼을 유지하고, 명시된 경우에만 확장 컬럼을 사용하도록 안전하게 확장.

### 6.2 pytest 실행 경로 충돌 방지 (`etc/scripts/` top-level exit 문제)
- **현상**: `pytest`를 아무 인자 없이 실행할 경우, `etc/scripts/m2_challenger2_stress_test.py`의 최상위 `sys.exit(0)`이 실행되어 pytest 수집 단계에서 `SystemExit: 0` 인터널 에러 발생.
- **해결책**:
  - `Makefile`에 정의된 바와 같이 테스트 실행 명령어는 항상 디렉토리를 명시: `/home/imnyj/venv/bin/pytest tests/ -v`.
  - 루트의 `pytest.ini` 설정(또는 생성) 시 `testpaths = ["tests"]`를 명시하여 `etc/` 디렉토리가 테스트 수집 대상에서 제외되도록 선제 조치 권고.

### 6.3 텐서 디바이스 일치성 (BUG-RL03 재발 방지)
- Milestone 3에서 `isinstance(..., np.ndarray)` 검사 누락으로 PyTorch 텐서의 CPU/CUDA 디바이스 불일치 버그가 발생한 이력이 있음.
- ResNet, Transformer, CVAE 내부의 모든 입력 처리부에서 `torch.as_tensor(x, dtype=torch.float32, device=device)` 패턴을 철저히 적용.

---

## 7. 구현 로드맵 및 파일별 제안 사항

### 7.1 대상 파일 및 역할 매핑

| 파일 경로 | 작업 내용 | 비고 |
|---|---|---|
| `modules/models/resnet_extractor.py` (또는 `feature_extractor.py`) | 1D-CNN 기반 `ResNet1DFeatureExtractor` 구현 | R1 |
| `modules/models/transformer_extractor.py` (또는 `feature_extractor.py`) | TimeSeries `TransformerFeatureExtractor` 구현 | R1 |
| `modules/models/cvae_extractor.py` (또는 `feature_extractor.py`) | Anomaly Detection `CVAEFeatureExtractor` 구현 | R1 |
| `modules/models/hybrid_policy.py` | 3가지 SL 아키텍처와 PPO 정책망 End-to-End 결합 인터페이스 보완 | R2 |
| `modules/hpo/exporter.py` | `MAIN_MODELS_CSV_COLUMNS`, `export_main_model_trial_to_csv` 추가 | R3 |
| `modules/hpo/optuna_pipeline.py` | `objective_main_model`, `run_model_hpo`, `run_all_main_models_hpo` 추가 | R3 |
| `tests/test_phase6_models.py` | 3가지 모델 텐서 입출력 형상 및 단위/통합 테스트 신규 작성 | Acceptance Criteria 1 |
| `tests/test_phase6_hpo.py` | 3가지 모델 Optuna HPO(n_trials=2) 및 `main_models_hpo.csv` 검증 테스트 신규 작성 | Acceptance Criteria 2 |

### 7.2 결론 요약
1. Phase 6의 HPO 및 모델 아키텍처 확장은 기존 모듈의 안정성을 100% 계승하면서 깔끔하게 분기 및 확장될 수 있습니다.
2. 특히 기존의 엄격한 20컬럼 검증 테스트 스위트와의 충돌을 피하기 위해 `MAIN_MODELS_CSV_COLUMNS`와 전용 내보내기 함수를 분리 설계하는 것이 가장 안전한 무결성 전략입니다.
3. 본 설계안을 바탕으로 Worker 에이전트들이 구현 및 테스트 작성을 진행할 경우 회귀 없이 완벽하게 승인 기준을 통과할 수 있습니다.
