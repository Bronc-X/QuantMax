from __future__ import annotations
from typing import Dict
import pandas as pd

from quantopen.strategy.api import AccountState, StrategyConfig


def topk_equal_weight(selected_scores: pd.Series, cfg: StrategyConfig) -> Dict[str, float]:
    if selected_scores is None or selected_scores.empty:
        return {}

    pick = selected_scores.sort_values(ascending=False).head(cfg.topk)
    n = len(pick)
    if n == 0:
        return {}

    w = min(cfg.max_weight_per_symbol, 1.0 / n)
    return {sym: float(w) for sym in pick.index}


def apply_account_risk_control(
    weights: Dict[str, float],
    account: AccountState,
    cfg: StrategyConfig,
) -> Dict[str, float]:
    # 简化：回撤超过阈值直接 risk-off
    if account.drawdown >= cfg.max_account_drawdown:
        return {sym: float(cfg.risk_off_weight) for sym in weights.keys()}
    return weights
