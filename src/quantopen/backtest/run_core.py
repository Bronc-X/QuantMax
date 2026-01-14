from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import backtrader as bt

from quantopen.backtest.bt_data import ParquetMinuteData, load_symbol_parquet
from quantopen.backtest.bt_core_strategy import CoreStrategyBT
from quantopen.backtest.costs import ChinaAStockCommission
from quantopen.strategy.api import StrategyConfig
from quantopen.strategy.loader import load_core_strategy


def run_core_backtest(
    bars_dir: str,
    symbols: List[str],
    core_dotted: str,
    cfg: StrategyConfig,
    cash: float = 1_000_000.0,
    hotlist_csv: Optional[str] = None,
    themes_csv: Optional[str] = None,
) -> Dict:
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

    core = load_core_strategy(core_dotted)

    cerebro.addstrategy(
        CoreStrategyBT,
        cfg=cfg,
        core=core,
        hotlist_csv=hotlist_csv,
        themes_csv=themes_csv,
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
