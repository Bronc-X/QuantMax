from __future__ import annotations
from pathlib import Path
from typing import Optional
from loguru import logger
from tqdm import tqdm
import typer

from quantopen.common.config import load_data_config
from quantopen.datafeed.akshare_1m import fetch_1m_eastmoney
from quantopen.datafeed.cache import read_symbol, write_symbol, merge_dedup_sort

app = typer.Typer(no_args_is_help=True)


@app.command()
def trade(
    broker: str = typer.Option("xq", help="Broker client: xq, ht, ths, yb"),
    config: str = typer.Option("easytrader.json", help="Config file for broker login (optional)"),
):
    """
    [Experimental] Connect to broker and show balance/positions.
    Currently supports EasyTrader backends (e.g. XueQiu).
    """
    from quantopen.execution.easytrader_adapter import EasyTraderExecutor
    import json
    
    # Load login kwargs
    kwargs = {}
    cfg_path = Path(config)
    if cfg_path.exists():
        with cfg_path.open() as f:
            kwargs = json.load(f)
            
    exe = EasyTraderExecutor()
    try:
        exe.connect(client=broker, **kwargs)
        
        bal = exe.get_balance()
        logger.info(f"Balance: Assets={bal.total_assets}, Cash={bal.available_cash}")
        
        positions = exe.get_positions()
        logger.info(f"Positions: {len(positions)}")
        for p in positions:
            logger.info(f"  {p.symbol}: {p.volume} (Avail: {p.available}) Val: {p.market_value}")
            
    except ImportError:
        logger.error("EasyTrader not installed. Run: pip install easytrader")
    except Exception as e:
        logger.error(f"Trade Error: {e}")



@app.command()
def download_hotlist(
    output: str = typer.Option("data/raw/hotlist.csv", help="Path to append hotlist"),
    source: str = typer.Option("em", help="Source: 'em' (Eastmoney) or 'xq' (XueQiu)"),
):
    """
    Fetch current hotlist and append to CSV.
    Sources:
      - em: 东方财富人气榜
      - xq: 雪球热股榜 (替代无法直接获取的同花顺)
    """
    from quantopen.datafeed.hotlist import fetch_and_append_hotlist
    fetch_and_append_hotlist(output, source=source)



@app.command()
def download_1m(config: str = typer.Option("configs/data.yaml", help="Path to data config yaml")):
    """
    Download 1-minute bars for configured symbols and cache to parquet per symbol.
    """
    cfg_path = Path(config)
    cfg = load_data_config(cfg_path)

    bars_dir = Path(cfg.bars_dir)
    bars_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Provider={cfg.provider}, bars_dir={bars_dir}, {cfg.start_date} -> {cfg.end_date}")
    logger.info(f"Symbols={len(cfg.symbols)}")

    for sym in tqdm(cfg.symbols, desc="Downloading 1m"):
        try:
            old = read_symbol(bars_dir, sym)
            new = fetch_1m_eastmoney(sym, cfg.start_date, cfg.end_date)
            merged = merge_dedup_sort(old, new)
            fp = write_symbol(bars_dir, sym, merged)
            logger.info(f"{sym}: rows={len(merged)} -> {fp}")
        except Exception as e:
            logger.exception(f"{sym} failed: {e}")


@app.command()
def backtest(config: str = typer.Option("configs/data.yaml", help="Path to data config yaml")):
    """
    Run backtest with basic HoldNMinutes strategy.
    """
    from quantopen.backtest.run import run_backtest as _run_backtest

    cfg = load_data_config(Path(config))
    report = _run_backtest(cfg.bars_dir, cfg.symbols, cash=1_000_000)
    logger.info(f"Backtest Report:")
    logger.info(f"  Final Value: {report['final_value']:,.2f}")
    logger.info(f"  Sharpe: {report['sharpe']}")
    logger.info(f"  Drawdown: {report['drawdown']}")
    logger.info(f"  Returns: {report['returns']}")


@app.command()
def backtest_risk(
    config: str = typer.Option("configs/data.yaml", help="Path to data config yaml"),
    max_dd: float = typer.Option(0.10, help="Max drawdown percentage (0.10 = 10%)"),
    limit_up: float = typer.Option(0.095, help="Limit-up threshold"),
    min_volume: float = typer.Option(10000, help="Min avg volume for liquidity"),
):
    """
    Run backtest with risk-controlled strategy (涨停+流动性+回撤风控).
    """
    from quantopen.backtest.run_risk import run_backtest_with_risk

    cfg = load_data_config(Path(config))
    report = run_backtest_with_risk(
        bars_dir=cfg.bars_dir,
        symbols=cfg.symbols,
        cash=1_000_000,
        max_dd_pct=max_dd,
        limit_up_threshold=limit_up,
        min_avg_volume=min_volume,
    )
    logger.info(f"Risk-Controlled Backtest Report:")
    logger.info(f"  Final Value: {report['final_value']:,.2f}")
    logger.info(f"  Sharpe: {report['sharpe']}")
    logger.info(f"  Max Drawdown: {report['drawdown'].get('max', {}).get('drawdown', 'N/A'):.2f}%")
    logger.info(f"  Total Return: {report['returns'].get('rtot', 0) * 100:.2f}%")


@app.command()
def export_qlib(
    config: str = typer.Option("configs/qlib.yaml", help="Qlib export config yaml"),
):
    """
    Export cached 1-min parquet bars into a minimal Qlib-compatible local dataset directory.
    Creates: calendars/, instruments/, features/ structure.
    """
    import yaml
    from quantopen.models.qlib_export import QlibExportConfig, export_qlib_minute_dataset

    cfg_path = Path(config)
    with cfg_path.open("r", encoding="utf-8") as f:
        d = yaml.safe_load(f)

    qcfg = QlibExportConfig(
        qlib_dir=Path(d["qlib_dir"]),
        bars_dir=Path(d["bars_dir"]),
        market=d.get("market", "cn"),
        freq=d.get("freq", "1min"),
    )

    export_qlib_minute_dataset(qcfg, symbols=None)


@app.command()
def backtest_core(
    data_config: str = typer.Option("configs/data.yaml", help="Data config yaml"),
    core: str = typer.Option("quant_core.core_strategy:MyCoreStrategy", help="Core strategy dotted path"),
    hotlist_csv: str = typer.Option("", help="Path to hotlist csv (date,symbol,rank)"),
    themes_csv: str = typer.Option("", help="Path to themes csv (symbol,theme_boost)"),
    topk: int = typer.Option(5, help="Top K stocks to hold"),
    max_dd: float = typer.Option(0.08, help="Max account drawdown (0.08 = 8%)"),
    rebalance_min: int = typer.Option(5, help="Rebalance every N minutes"),
):
    """
    Run backtest with closed-source core strategy (动量+量价+热榜+主题).
    """
    from quantopen.strategy.api import StrategyConfig
    from quantopen.backtest.run_core import run_core_backtest

    cfg = load_data_config(Path(data_config))

    scfg = StrategyConfig(
        topk=topk,
        max_positions=topk,
        max_weight_per_symbol=min(0.20, 1.0 / topk),
        rebalance_every_n_minutes=rebalance_min,
        hold_minutes=60,
        max_account_drawdown=max_dd,
        risk_off_weight=0.0,
    )

    report = run_core_backtest(
        bars_dir=cfg.bars_dir,
        symbols=cfg.symbols,
        core_dotted=core,
        cfg=scfg,
        cash=1_000_000.0,
        hotlist_csv=hotlist_csv if hotlist_csv else None,
        themes_csv=themes_csv if themes_csv else None,
    )
    
    logger.info(f"Core Strategy Backtest Report:")
    logger.info(f"  Final Value: {report['final_value']:,.2f}")
    logger.info(f"  Sharpe: {report['sharpe']}")
    logger.info(f"  Max Drawdown: {report['drawdown'].get('max', {}).get('drawdown', 'N/A'):.2f}%")
    logger.info(f"  Total Return: {report['returns'].get('rtot', 0) * 100:.2f}%")
    logger.info(f"  Loaded Symbols: {report['loaded_symbols']}")


@app.command()
def subscribe(
    api_key: str = typer.Option(..., prompt=True, hide_input=True, help="Your QuantMax API Key"),
    host: str = typer.Option("http://127.0.0.1:8000/v1", help="API Host (Mock or Real)"),
    date: str = typer.Option(None, help="Date to fetch signals (YYYY-MM-DD)")
):
    """
    [Pro] Fetch Premium Alpha Signals from QuantMax Cloud.
    Requires an active subscription API Key.
    """
    from quantopen.sdk.client import QuantMaxClient
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    client = QuantMaxClient(api_key=api_key, base_url=host)
    
    logger.info(f"Connecting to {host}...")
    if not client.check_connection():
        logger.error("Connection failed. Check API Key or Host.")
        if "127.0.0.1" in host:
            logger.warning("Tip: Run 'python -m quantopen.sdk.mock_server' in another terminal to start mock server.")
        return

    logger.success("Authenticated successfully!")
    logger.info(f"Fetching signals for {date}...")
    
    signals = client.get_alpha_signals(date)
    
    if signals:
        logger.info(f"Received {len(signals)} Alpha Signals:")
        sorted_sigs = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        for sym, score in sorted_sigs:
            logger.info(f"  {sym}: {score:.4f}")
    else:
        logger.warning("No signals found for this date.")


if __name__ == "__main__":
    app()
