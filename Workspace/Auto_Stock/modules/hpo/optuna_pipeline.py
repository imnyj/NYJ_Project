"""
modules/hpo/optuna_pipeline.py
==============================
Auto Stock ML/RL Trader — Milestone 3: Optuna 기반 하이퍼파라미터 최적화(HPO) 파이프라인.

주요 컴포넌트:
1. create_hpo_study:
   - TPESampler(seed=42) 및 MedianPruner 기반 Optuna Study 인스턴스 생성.
2. objective:
   - SL-RL 하이퍼파라미터(학습률, 배치 크기, 은닉층 차원, 감가율, 클리핑 범위, 엔트로피 계수 등) 제안.
   - HybridTradingEnv 상에서 모델 훈련 및 트레이딩 시뮬레이션 수행.
   - Total Equity, Sharpe Ratio, MDD, Win Rate 등 6대 핵심 지표 산출.
   - Trial 종료 시 원자적으로 etc/hpo_results/baseline_hpo.csv에 20개 컬럼 기록.
   - 가지치기(Pruning) 및 예외 복원력(Exception Resilience) 지원.
3. run_hpo_optimization:
   - n_trials 횟수만큼 최적화 루프 완주 및 best_trial, study 결과 반환.
"""

import datetime
import logging
import math
import os
import random
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import optuna
import torch

from modules.engine.hybrid_trading_env import HybridTradingEnv
from modules.hpo.exporter import export_trial_to_csv
from modules.hpo.metrics import (
    calculate_annualized_sharpe_ratio,
    calculate_max_drawdown_pct,
    calculate_total_equity,
    calculate_total_return_pct,
    calculate_win_rate,
    evaluate_trading_history,
)
from modules.models.feature_extractor import (
    DualStreamSLFeatureExtractor,
    TabularMLPFeatureExtractor,
)
from modules.models.hybrid_policy import (
    HybridActorCritic,
    HybridPPO,
)

logger = logging.getLogger("AutoStock.HPO")


def create_hpo_study(
    study_name: str = "auto_stock_hpo",
    storage: Optional[str] = None,
    seed: int = 42,
    direction: str = "maximize",
    pruner: Optional[optuna.pruners.BasePruner] = None,
) -> optuna.Study:
    """
    Optuna HPO Study를 생성합니다.

    - Sampler: TPESampler (재현성을 위해 seed 고정)
    - Pruner: MedianPruner (중간 성능 하위 Trial 조기 가지치기)

    Args:
        study_name: Study 식별 이름
        storage: RDB / SQLite 스토리지 URL (기본값: None, 인메모리)
        seed: 난수 시드 (기본값: 42)
        direction: 최적화 방향 ('maximize' 또는 'minimize')
        pruner: 커스텀 Pruner 객체 (기본값: MedianPruner)

    Returns:
        study: optuna.Study 인스턴스
    """
    sampler = optuna.samplers.TPESampler(seed=seed)
    selected_pruner = pruner or optuna.pruners.MedianPruner(
        n_startup_trials=2,
        n_warmup_steps=5,
        interval_steps=1,
    )

    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=sampler,
        pruner=selected_pruner,
        direction=direction,
        load_if_exists=True,
    )
    return study


def objective(
    trial: optuna.Trial,
    symbol: str = "005930",
    data_path: Optional[str] = None,
    output_csv: str = "etc/hpo_results/baseline_hpo.csv",
    n_timesteps: int = 200,
    fast_mode: bool = True,
    seed: int = 42,
    env_kwargs: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> float:
    """
    Optuna 단일 Trial 목적 함수 (Objective Function).

    1. SL & RL 하이퍼파라미터 제안:
       - sl_lr: float (1e-5 ~ 1e-2, log=True)
       - sl_hidden_dim: categorical [32, 64, 128, 256]
       - sl_batch_size: categorical [16, 32, 64, 128]
       - rl_lr: float (1e-5 ~ 1e-3, log=True)
       - rl_gamma: float (0.90 ~ 0.999)
       - rl_clip_range: float (0.1 ~ 0.3)
       - rl_ent_coef: float (1e-4 ~ 1e-1, log=True)
       - rl_hidden_dim: categorical [64, 128, 256]
    2. 환경 구성 및 고속 학습:
       - HybridTradingEnv 인스턴스화
       - TabularMLPFeatureExtractor + HybridActorCritic + HybridPPO 구성
       - ppo.learn(n_timesteps)
    3. 종합 평가 및 지표 산출:
       - Total Equity, Total Return %, Sharpe Ratio (0-분산 방어), MDD %, Total Trades, Win Rate %
    4. CSV 원자적 저장 및 목적 함수 값 반환.

    Args:
        trial: Optuna Trial 객체
        symbol: 종목 코드
        data_path: 데이터 파일 경로
        output_csv: 결과 저장 대상 CSV 경로
        n_timesteps: Trial당 RL 학습 스텝 수
        fast_mode: 고속 최적화 모드 여부
        seed: 난수 시드
        env_kwargs: 환경 추가 인자
        verbose: 로깅 상세 여부

    Returns:
        objective_value: float (최적화 대상 값, 기본적으로 Sharpe Ratio)
    """
    t_start = time.time()
    dt_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    trial_seed = seed + trial.number

    # Trial-level deterministic RNG seeding
    torch.manual_seed(trial_seed)
    np.random.seed(trial_seed)
    random.seed(trial_seed)

    # 1. 하이퍼파라미터 탐색 공간 정의
    sl_lr = trial.suggest_float("sl_lr", 1e-5, 1e-2, log=True)
    sl_hidden_dim = trial.suggest_categorical("sl_hidden_dim", [32, 64, 128, 256])
    sl_batch_size = trial.suggest_categorical("sl_batch_size", [16, 32, 64, 128])

    rl_lr = trial.suggest_float("rl_lr", 1e-5, 1e-3, log=True)
    rl_gamma = trial.suggest_float("rl_gamma", 0.90, 0.999)
    rl_clip_range = trial.suggest_float("rl_clip_range", 0.1, 0.3)
    rl_ent_coef = trial.suggest_float("rl_ent_coef", 1e-4, 1e-1, log=True)
    rl_hidden_dim = trial.suggest_categorical("rl_hidden_dim", [64, 128, 256])

    trial_state = "COMPLETE"
    metrics: Dict[str, Any] = {
        "total_equity": 10_000_000.0,
        "total_return_pct": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "total_trades": 0,
        "win_rate": 0.0,
    }
    objective_value = 0.0

    try:
        # 2. 환경 빌드
        merged_env_kwargs = {
            "symbol": symbol,
            "data_path": data_path,
            "mode": "offline",
            "initial_cash": 10_000_000,
        }
        if env_kwargs:
            merged_env_kwargs.update(env_kwargs)

        env = HybridTradingEnv(**merged_env_kwargs)
        obs_dim = env.observation_space.shape[0]

        # 3. 모델 네트워크 및 PPO 에이전트 빌드
        feature_extractor = TabularMLPFeatureExtractor(
            input_dim=obs_dim,
            hidden_dims=[sl_hidden_dim, sl_hidden_dim // 2] if sl_hidden_dim >= 64 else [sl_hidden_dim],
            output_dim=sl_hidden_dim,
            dropout=0.0,
        )

        policy = HybridActorCritic(
            obs_dim=obs_dim,
            feature_extractor=feature_extractor,
            feature_dim=sl_hidden_dim,
            hidden_dims=[rl_hidden_dim, rl_hidden_dim],
            distribution_type="beta",
        )

        n_steps = min(64 if fast_mode else 128, max(16, n_timesteps // 2))
        batch_size = min(int(sl_batch_size), n_steps)
        n_epochs = 2 if fast_mode else 4

        ppo = HybridPPO(
            env=env,
            policy=policy,
            learning_rate=rl_lr,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=rl_gamma,
            clip_range=rl_clip_range,
            ent_coef=rl_ent_coef,
            seed=trial_seed,
            device="cpu",
        )

        # 4. 고속 학습 수행
        ppo.learn(total_timesteps=n_timesteps)

        # 5. 최종 평가 롤아웃 수행
        obs, info = env.reset(seed=trial_seed)
        equity_history = [float(info.get("total_equity", 10_000_000.0))]
        returns_history: List[float] = []
        trades_history: List[Any] = []
        done = False
        prev_eq = equity_history[0]

        while not done:
            action, _ = ppo.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            curr_eq = float(info.get("total_equity", 10_000_000.0))
            equity_history.append(curr_eq)

            if prev_eq > 0:
                ret = (curr_eq - prev_eq) / prev_eq
            else:
                ret = 0.0
            returns_history.append(ret)
            prev_eq = curr_eq

            if info.get("trade_record") is not None:
                trades_history.append(info["trade_record"])

        # 6. 성과 지표 계산
        metrics = evaluate_trading_history(
            equity_history=equity_history,
            returns_history=returns_history,
            trades_history=trades_history,
            initial_cash=10_000_000.0,
        )

        # 파산 여부 확인
        if terminated and equity_history[-1] < 500_000.0:
            objective_value = -100.0
        else:
            # 샤프 지수를 기본 목적 함수로 설정하되 유효한 부동소수점 보장
            sr = float(metrics["sharpe_ratio"])
            sr_safe = sr if not (math.isnan(sr) or math.isinf(sr)) else 0.0
            tot_ret = float(metrics.get("total_return_pct", 0.0))
            tot_ret_safe = tot_ret if not (math.isnan(tot_ret) or math.isinf(tot_ret)) else 0.0
            total_trades = int(metrics.get("total_trades", 0))

            # BUG-RL05: 무거래(100% 현금 보유, total_trades=0) 편향 방어 및 복합 가중치 적용
            if total_trades == 0:
                objective_value = -1.0
            else:
                objective_value = sr_safe + 0.01 * tot_ret_safe

        # Pruning 리포트 및 검사
        trial.report(objective_value, step=n_timesteps)
        if trial.should_prune():
            trial_state = "PRUNED"

    except optuna.TrialPruned:
        trial_state = "PRUNED"
        objective_value = float(metrics.get("sharpe_ratio", -50.0))
        raise

    except Exception as e:
        logger.warning(f"[Trial {trial.number}] 실행 도중 예외 발생: {e}")
        trial_state = "FAIL"
        objective_value = -100.0

    finally:
        t_end = time.time()
        duration_sec = max(0.001, t_end - t_start)
        dt_complete = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Trial 사용자 속성 기록
        trial.set_user_attr("total_equity", float(metrics["total_equity"]))
        trial.set_user_attr("total_return_pct", float(metrics["total_return_pct"]))
        trial.set_user_attr("sharpe_ratio", float(metrics["sharpe_ratio"]))
        trial.set_user_attr("max_drawdown_pct", float(metrics["max_drawdown_pct"]))
        trial.set_user_attr("total_trades", int(metrics["total_trades"]))
        trial.set_user_attr("win_rate", float(metrics["win_rate"]))
        trial.set_user_attr("state", trial_state)
        trial.set_user_attr("duration_seconds", round(duration_sec, 4))

        # 7. CSV 원자적 저장 (20개 컬럼 스키마)
        trial_record = {
            "trial_id": trial.number,
            "state": trial_state,
            "objective_value": round(float(objective_value), 6),
            "total_equity": round(float(metrics["total_equity"]), 2),
            "total_return_pct": round(float(metrics["total_return_pct"]), 4),
            "sharpe_ratio": round(float(metrics["sharpe_ratio"]), 4),
            "max_drawdown_pct": round(float(metrics["max_drawdown_pct"]), 4),
            "total_trades": int(metrics["total_trades"]),
            "win_rate": round(float(metrics["win_rate"]), 2),
            "param_sl_lr": sl_lr,
            "param_sl_hidden_dim": int(sl_hidden_dim),
            "param_sl_batch_size": int(sl_batch_size),
            "param_rl_lr": rl_lr,
            "param_rl_gamma": rl_gamma,
            "param_rl_clip_range": rl_clip_range,
            "param_rl_ent_coef": rl_ent_coef,
            "param_rl_hidden_dim": int(rl_hidden_dim),
            "duration_seconds": round(duration_sec, 4),
            "datetime_start": dt_start,
            "datetime_complete": dt_complete,
        }

        if output_csv:
            export_trial_to_csv(trial_record, csv_path=output_csv)

    if trial_state == "PRUNED":
        raise optuna.TrialPruned()

    return float(objective_value)


def run_hpo_optimization(
    n_trials: int = 3,
    symbol: str = "005930",
    data_path: Optional[str] = None,
    output_csv: str = "etc/hpo_results/baseline_hpo.csv",
    seed: int = 42,
    n_timesteps: int = 200,
    fast_mode: bool = True,
    study_name: str = "auto_stock_hpo",
    storage: Optional[str] = None,
    timeout: Optional[float] = None,
    verbose: bool = True,
) -> Tuple[optuna.Study, optuna.trial.FrozenTrial]:
    """
    Optuna HPO 최적화 파이프라인을 실행하고 최적 Trial 결과를 반환합니다.

    Args:
        n_trials: 실행할 Trial 총 횟수 (기본값: 3)
        symbol: 주식 종목 코드 (기본값: '005930')
        data_path: 시계열 데이터 경로
        output_csv: 결과 CSV 저장 경로 (기본값: 'etc/hpo_results/baseline_hpo.csv')
        seed: 기본 난수 시드 (기본값: 42)
        n_timesteps: Trial당 학습 스텝 수 (기본값: 200)
        fast_mode: 고속 실행 모드
        study_name: Study 식별 이름
        storage: Optuna 스토리지
        timeout: 전체 최적화 타임아웃(초)
        verbose: 진행 상황 출력 여부

    Returns:
        (study, best_trial): 완료된 Optuna Study 및 최적 FrozenTrial 객체
    """
    if verbose:
        print(f"=== [AutoStock HPO] Starting Optimization (n_trials={n_trials}, symbol={symbol}) ===")

    study = create_hpo_study(
        study_name=study_name,
        storage=storage,
        seed=seed,
        direction="maximize",
    )

    optuna.logging.set_verbosity(
        optuna.logging.INFO if verbose else optuna.logging.WARNING
    )

    def _obj_wrapper(t: optuna.Trial) -> float:
        return objective(
            trial=t,
            symbol=symbol,
            data_path=data_path,
            output_csv=output_csv,
            n_timesteps=n_timesteps,
            fast_mode=fast_mode,
            seed=seed,
            verbose=verbose,
        )

    study.optimize(
        _obj_wrapper,
        n_trials=n_trials,
        timeout=timeout,
        catch=(Exception,),
    )

    best_trial = study.best_trial

    if verbose:
        print(f"=== [AutoStock HPO] Optimization Complete ===")
        print(f"Best Trial #{best_trial.number}: Objective Value = {best_trial.value:.6f}")
        print("Best Hyperparameters:")
        for k, v in best_trial.params.items():
            print(f"  - {k}: {v}")
        print(f"Results exported to: {os.path.abspath(output_csv)}")

    return study, best_trial
