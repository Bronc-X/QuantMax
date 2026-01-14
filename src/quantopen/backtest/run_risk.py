"""Backtest runner with risk-controlled strategy."""
from __future__ import annotations
from pathlib import Path
import backtrader as bt

from quantopen.backtest.bt_engine import ParquetMinuteData, load_symbol_parquet
from quantopen.backtest.bt_strategy_risk import HoldNMinutesWithRisk
from quantopen.backtest.costs import ChinaAStockCommission


def run_backtest_with_risk(
    bars_dir: str,
    symbols: list[str],
    cash: float = 1_000_000,
    max_dd_pct: float = 0.10,
    limit_up_threshold: float = 0.095,
    min_avg_volume: float = 10000,
):
    """
    Run backtest with risk-controlled strategy.
    
    Args:
        bars_dir: Directory containing parquet files
        symbols: List of stock symbols
        cash: Initial capital
        max_dd_pct: Maximum drawdown before stopping (0.10 = 10%)
        limit_up_threshold: Threshold for limit-up filter (0.095 = 9.5%)
        min_avg_volume: Minimum average volume for liquidity filter
    
    Returns:
        Dict with backtest results
    """
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(cash)
    cerebro.broker.addcommissioninfo(ChinaAStockCommission())

    bars_path = Path(bars_dir)
    loaded = 0
    for sym in symbols:
        fp = bars_path / f"{sym}.parquet"
        if not fp.exists():
            continue
        df = load_symbol_parquet(fp)
        data = ParquetMinuteData(dataname=df, name=sym)
        cerebro.adddata(data)
        loaded += 1

    cerebro.addstrategy(
        HoldNMinutesWithRisk,
        hold_minutes=60,
        target_percent=0.1,
        max_positions=5,
        limit_up_threshold=limit_up_threshold,
        min_avg_volume=min_avg_volume,
        max_drawdown_pct=max_dd_pct,
        reduce_at_drawdown=max_dd_pct * 0.5,  # start reducing at 50% of max
    )

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="ret")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    results = cerebro.run()
    strat = results[0]
    
    return {
        "final_value": cerebro.broker.getvalue(),
        "sharpe": strat.analyzers.sharpe.get_analysis(),
        "drawdown": strat.analyzers.dd.get_analysis(),
        "returns": strat.analyzers.ret.get_analysis(),
        "trades": strat.analyzers.trades.get_analysis(),
        "loaded_symbols": loaded,
    }
