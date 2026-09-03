"""
modules/hpo/metrics.py
======================
Auto Stock ML/RL Trader — Milestone 3: 금융 성과 및 트레이딩 평가 지표 계산 모듈.

주요 함수:
1. calculate_total_equity: 잔고 + 보유 주식 × 시장가 기반 총 평가금 계산.
2. calculate_total_return_pct: 초기 자본금 대비 최종 자산 총 수익률(%) 계산.
3. calculate_annualized_sharpe_ratio: 연율화 샤프 지수 계산 (표준편차 <= 1e-8 시 0.0 반환하는 제로 분산 방어 필수).
4. calculate_max_drawdown_pct: 고점 대비 최대 낙폭 (MDD, %) 계산.
5. calculate_win_rate: 거래 내역 기반 총 체결 수 및 승률(%) 계산.
6. evaluate_trading_history: 트레이딩 시계열 및 체결 이력을 기반으로 종합 성과 지표 딕셔너리 산출.
"""

import math
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


def calculate_total_equity(
    cash: Union[Decimal, float, int],
    holdings: Union[int, float, Dict[str, Union[int, float]]],
    current_price: Union[Decimal, float, int, Dict[str, Union[Decimal, float, int]]] = 0.0,
) -> float:
    """
    현재 현금 잔고와 보유 주식의 시장가치 총합(Total Equity)을 계산합니다.

    Args:
        cash: 현금 잔고 (Decimal, float, int)
        holdings: 보유 주식 수량 (단일 종목 int/float 또는 {symbol: qty} 딕셔너리)
        current_price: 현재 시장가 (단일 종목 float/Decimal 또는 {symbol: price} 딕셔너리)

    Returns:
        total_equity: float 총 평가금 (원)
    """
    total_cash = float(cash)
    holdings_value = 0.0

    if isinstance(holdings, dict) and isinstance(current_price, dict):
        for sym, qty in holdings.items():
            p = float(current_price.get(sym, 0.0))
            holdings_value += float(qty) * p
    elif isinstance(holdings, (int, float, np.integer, np.floating)):
        p = float(current_price) if not isinstance(current_price, dict) else 0.0
        holdings_value = float(holdings) * p
    else:
        # Fallback
        holdings_value = 0.0

    total_eq = total_cash + holdings_value
    if math.isnan(total_eq) or math.isinf(total_eq):
        return total_cash
    return float(total_eq)


def calculate_total_return_pct(
    initial_equity: Union[Decimal, float, int],
    final_equity: Union[Decimal, float, int],
) -> float:
    """
    초기 자본금 대비 총 수익률(Total Return, %)을 계산합니다.

    Args:
        initial_equity: 초기 자산 평가액
        final_equity: 최종 자산 평가액

    Returns:
        total_return_pct: float 총 수익률 (%)
    """
    init_eq = float(initial_equity)
    fin_eq = float(final_equity)

    if init_eq <= 0.0:
        return 0.0

    ret_pct = ((fin_eq - init_eq) / init_eq) * 100.0
    if math.isnan(ret_pct) or math.isinf(ret_pct):
        return 0.0
    return float(ret_pct)


def calculate_annualized_sharpe_ratio(
    returns: Union[Sequence[float], np.ndarray, pd.Series],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    eps: float = 1e-8,
) -> float:
    """
    수익률 시계열의 연율화 샤프 지수(Annualized Sharpe Ratio)를 계산합니다.
    - Zero-Variance Defense: 수익률의 표본 표준편차가 1e-8 이하이거나 NaN인 경우 0.0을 반환합니다.
    - 무거래 또는 일정한 자산 곡선으로 인한 0으로 나누기(ZeroDivisionError)를 완벽히 방어합니다.

    Args:
        returns: 일별 또는 스텝별 수익률 시계열 (예: [0.01, -0.005, 0.002, ...])
        risk_free_rate: 연간 무위험 이자율 (기본값: 0.0)
        periods_per_year: 연간 거래일/스텝 수 (기본값: 252)
        eps: 분모 0 방지 상수 (기본값: 1e-8)

    Returns:
        annualized_sharpe_ratio: float 샤프 지수
    """
    if returns is None or len(returns) < 2:
        return 0.0

    # NumPy 배열로 변환 및 유효값 필터링
    r_arr = np.asarray(returns, dtype=np.float64)
    r_clean = r_arr[np.isfinite(r_arr)]

    if len(r_clean) < 2:
        return 0.0

    # 일별 무위험 이자율
    rf_daily = risk_free_rate / periods_per_year

    # 표본 평균 및 표본 표준편차 (ddof=1)
    mean_r = float(np.mean(r_clean))
    std_r = float(np.std(r_clean, ddof=1))

    # Zero-Variance Defense: 분산이 극도로 작거나 0인 경우 0.0 반환
    if std_r <= 1e-8 or math.isnan(std_r) or math.isinf(std_r):
        return 0.0

    excess_mean = mean_r - rf_daily
    sharpe = (excess_mean / (std_r + eps)) * math.sqrt(periods_per_year)

    if math.isnan(sharpe) or math.isinf(sharpe):
        return 0.0

    return float(sharpe)


def calculate_max_drawdown_pct(
    equity_curve: Union[Sequence[float], np.ndarray, pd.Series],
) -> float:
    """
    자산 평가액 시계열로부터 최대 낙폭 (Maximum Drawdown, MDD %)을 계산합니다.
    - MDD = min((E_t - Peak_t) / Peak_t) * 100.0 (음수 퍼센티지, 예: -5.25%)
    - 낙폭이 전혀 없는 단조 증가의 경우 0.0%를 반환합니다.

    Args:
        equity_curve: 자산 평가액 시계열 [E_0, E_1, ..., E_T]

    Returns:
        max_drawdown_pct: float 최대 낙폭 (%) (<= 0.0)
    """
    if equity_curve is None or len(equity_curve) < 1:
        return 0.0

    eq_arr = np.asarray(equity_curve, dtype=np.float64)
    eq_clean = eq_arr[np.isfinite(eq_arr)]

    if len(eq_clean) < 1:
        return 0.0

    # 누적 고점 계산
    peaks = np.maximum.accumulate(eq_clean)
    peaks = np.where(peaks <= 0.0, 1e-8, peaks)

    drawdowns = (eq_clean - peaks) / peaks * 100.0
    mdd = float(np.min(drawdowns))

    if math.isnan(mdd) or math.isinf(mdd):
        return 0.0

    # 부동소수점 오차로 0.0000001 같은 미세 양수가 되는 것 방지
    if mdd > 0.0:
        mdd = 0.0

    return float(mdd)


def calculate_win_rate(
    trade_pnls_or_records: Union[Sequence[Union[float, Decimal, Any]], np.ndarray],
) -> Tuple[int, float]:
    """
    체결된 거래 내역 또는 실현 손익 목록으로부터 총 체결 수와 승률(Win Rate, %)을 계산합니다.

    Args:
        trade_pnls_or_records: 실현 손익(PnL) 숫자 리스트 또는 TradeRecord 객체 리스트

    Returns:
        (total_trades, win_rate_pct): (int 총 거래 수, float 승률 %)
    """
    if trade_pnls_or_records is None or len(trade_pnls_or_records) == 0:
        return 0, 0.0

    pnls: List[float] = []
    for item in trade_pnls_or_records:
        if isinstance(item, (int, float, np.integer, np.floating)):
            pnls.append(float(item))
        elif isinstance(item, Decimal):
            pnls.append(float(item))
        elif hasattr(item, "realized_pnl"):
            pnl_val = getattr(item, "realized_pnl")
            if pnl_val is not None:
                pnls.append(float(pnl_val))
        elif isinstance(item, dict) and "realized_pnl" in item:
            pnls.append(float(item["realized_pnl"]))
        else:
            # General trade event (count as neutral 0 if unknown)
            pass

    total_trades = len(pnls) if len(pnls) > 0 else len(trade_pnls_or_records)
    if total_trades == 0:
        return 0, 0.0

    if len(pnls) > 0:
        win_count = sum(1 for p in pnls if p > 0.0)
        win_rate = (win_count / len(pnls)) * 100.0
    else:
        win_rate = 0.0

    return int(total_trades), float(win_rate)


def evaluate_trading_history(
    equity_history: Optional[Sequence[float]] = None,
    returns_history: Optional[Sequence[float]] = None,
    trades_history: Optional[Sequence[Any]] = None,
    initial_cash: float = 10_000_000.0,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> Dict[str, Union[float, int]]:
    """
    트레이딩 이력(에쿼티 시계열, 스텝 수익률, 체결 내역)으로부터 종합 평가 지표를 산출합니다.

    Args:
        equity_history: 스텝별 총 평가금 시계열
        returns_history: 스텝별 수익률 시계열
        trades_history: 체결 기록 리스트
        initial_cash: 초기 자본금 (기본: 10,000,000원)
        risk_free_rate: 연간 무위험 이자율
        periods_per_year: 연간 거래일/스텝 수

    Returns:
        metrics_dict: {
            "total_equity": float,
            "total_return_pct": float,
            "sharpe_ratio": float,
            "max_drawdown_pct": float,
            "total_trades": int,
            "win_rate": float,
        }
    """
    # 1. Total Equity & Total Return
    if equity_history is not None and len(equity_history) > 0:
        final_equity = float(equity_history[-1])
        init_eq = float(equity_history[0]) if len(equity_history) > 0 else initial_cash
    else:
        final_equity = float(initial_cash)
        init_eq = float(initial_cash)

    tot_return_pct = calculate_total_return_pct(init_eq, final_equity)

    # 2. Returns series derivation if not provided
    if returns_history is not None and len(returns_history) > 0:
        rets = list(returns_history)
    elif equity_history is not None and len(equity_history) >= 2:
        eqs = np.asarray(equity_history, dtype=np.float64)
        eq_prev = eqs[:-1]
        eq_curr = eqs[1:]
        # Calculate percentage returns: (curr - prev) / max(prev, 1e-8)
        rets = list((eq_curr - eq_prev) / np.maximum(eq_prev, 1e-8))
    else:
        rets = []

    # 3. Sharpe Ratio (with zero-variance defense)
    sharpe = calculate_annualized_sharpe_ratio(
        returns=rets,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )

    # 4. Max Drawdown
    if equity_history is not None and len(equity_history) > 0:
        mdd = calculate_max_drawdown_pct(equity_history)
    else:
        mdd = 0.0

    # 5. Total Trades & Win Rate
    tot_trades, win_rate = calculate_win_rate(trades_history or [])

    return {
        "total_equity": round(final_equity, 2),
        "total_return_pct": round(tot_return_pct, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown_pct": round(mdd, 4),
        "total_trades": int(tot_trades),
        "win_rate": round(win_rate, 2),
    }
