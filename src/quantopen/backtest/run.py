from __future__ import annotations
from pathlib import Path
import backtrader as bt

from quantopen.backtest.bt_engine import ParquetMinuteData, load_symbol_parquet
from quantopen.backtest.bt_strategy import HoldNMinutes
from quantopen.backtest.costs import ChinaAStockCommission

def run_backtest(bars_dir: str, symbols: list[str], cash: float = 1_000_000):
    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(cash)
    cerebro.broker.addcommissioninfo(ChinaAStockCommission())

    bars_path = Path(bars_dir)
    for sym in symbols:
        fp = bars_path / f"{sym}.parquet"
        if not fp.exists():
            continue
        df = load_symbol_parquet(fp)
        data = ParquetMinuteData(dataname=df, name=sym)
        cerebro.adddata(data)

    cerebro.addstrategy(HoldNMinutes, hold_minutes=60, target_percent=0.1, max_positions=5)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="dd")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="ret")

    results = cerebro.run()
    strat = results[0]
    return {
        "final_value": cerebro.broker.getvalue(),
        "sharpe": strat.analyzers.sharpe.get_analysis(),
        "drawdown": strat.analyzers.dd.get_analysis(),
        "returns": strat.analyzers.ret.get_analysis(),
    }
