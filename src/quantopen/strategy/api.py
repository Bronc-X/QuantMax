from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional
import pandas as pd


@dataclass(frozen=True)
class MarketState:
    """可扩展：指数涨跌、波动、风格、资金流等。"""
    dt: pd.Timestamp


@dataclass(frozen=True)
class AccountState:
    equity: float
    peak_equity: float
    drawdown: float  # 0~1


@dataclass(frozen=True)
class StrategyConfig:
    # universe / selection
    topk: int = 5
    max_positions: int = 5
    max_weight_per_symbol: float = 0.10

    # filters
    hot_topn: int = 50
    min_amount_1m: float = 2_000_000.0  # 1分钟成交额阈值（可调整）
    limit_up_threshold: float = 0.095   # 近似涨停阈值（9.5%）

    # execution
    rebalance_every_n_minutes: int = 5
    hold_minutes: int = 60

    # risk control
    max_account_drawdown: float = 0.08  # 超过就降仓/清仓（示例）
    risk_off_weight: float = 0.0        # 风控触发时目标仓位


class CoreStrategy(ABC):
    """
    闭源核心策略只需要实现这个接口。
    开源框架负责：数据、回测撮合、成本、报告等。
    """

    @abstractmethod
    def alpha_score(
        self,
        dt: pd.Timestamp,
        features: pd.DataFrame,
        hot: Optional[pd.DataFrame],
        themes: Optional[pd.DataFrame],
        market: MarketState,
    ) -> pd.Series:
        """
        返回每个 symbol 的分数（越大越强）。
        features: index=symbol, columns=特征（含 close/amount/ret等）
        hot: index=symbol, columns=[rank] 可为空
        themes: index=symbol, columns=[theme_boost] 可为空
        """

    @abstractmethod
    def filter_and_select(
        self,
        dt: pd.Timestamp,
        scores: pd.Series,
        features: pd.DataFrame,
        hot: Optional[pd.DataFrame],
        themes: Optional[pd.DataFrame],
        market: MarketState,
    ) -> pd.Series:
        """
        返回被选中的 symbol 分数（已过滤），index=symbol
        """

    @abstractmethod
    def build_target_weights(
        self,
        dt: pd.Timestamp,
        selected_scores: pd.Series,
        account: AccountState,
        cfg: StrategyConfig,
    ) -> Dict[str, float]:
        """
        输出目标权重 {symbol: weight}，权重可为 0~1。
        """
