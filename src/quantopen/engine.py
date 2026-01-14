"""Backtrader engine wrapper for backtesting."""

from pathlib import Path
from typing import Any, Optional, Type
import yaml
import pandas as pd
from loguru import logger

try:
    import backtrader as bt
except ImportError:
    bt = None
    logger.warning("Backtrader not installed, backtesting will not work")


class BaseStrategy(bt.Strategy if bt else object):
    """
    Base strategy class with feature placeholder interface.
    
    Your private strategy should inherit from this class and implement:
    - __init__: Initialize indicators
    - next: Trading logic executed on each bar
    - compute_features: Custom feature computation (placeholder for your strategy)
    """
    
    params = (
        ("printlog", True),
    )
    
    def __init__(self):
        """Initialize strategy indicators."""
        if bt is None:
            raise ImportError("Backtrader is required for backtesting")
        
        # Data references
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        # Order tracking
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Feature placeholder - override in your strategy
        self.features = {}
    
    def log(self, txt: str, dt=None):
        """Logging function."""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.datetime(0)
            logger.info(f"{dt.isoformat()} {txt}")
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}")
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications."""
        if not trade.isclosed:
            return
        
        self.log(f"OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}")
    
    def compute_features(self) -> dict[str, Any]:
        """
        Placeholder for custom feature computation.
        Override this method in your strategy to compute proprietary features.
        
        Returns:
            Dictionary of feature name -> value
        """
        return {}
    
    def next(self):
        """
        Main trading logic - executed on each bar.
        Override this method in your strategy.
        """
        # Compute features
        self.features = self.compute_features()
        
        # Default: do nothing (placeholder)
        pass


class PandasData(bt.feeds.PandasData if bt else object):
    """Pandas data feed with standard OHLCV columns."""
    
    params = (
        ("datetime", None),
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", -1),
    )


def load_config(config_path: str) -> dict:
    """Load backtest configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_backtest(
    config_path: str = "configs/backtest.yaml",
    strategy_class: Optional[Type] = None,
) -> Optional[list]:
    """
    Run backtest with given configuration.
    
    Args:
        config_path: Path to YAML config file
        strategy_class: Strategy class to use (default: BaseStrategy)
    
    Returns:
        List of strategy results
    """
    if bt is None:
        raise ImportError("Backtrader is required for backtesting")
    
    config = load_config(config_path)
    
    # Create cerebro engine
    cerebro = bt.Cerebro()
    
    # Set initial capital
    initial_cash = config.get("initial_cash", 100000.0)
    cerebro.broker.setcash(initial_cash)
    
    # Set commission
    commission = config.get("commission", 0.001)
    cerebro.broker.setcommission(commission=commission)
    
    # Add strategy
    strategy = strategy_class or BaseStrategy
    cerebro.addstrategy(strategy)
    
    # Load data
    data_config = config.get("data", {})
    symbol = data_config.get("symbol", "000001")
    period = data_config.get("period", "1")
    
    from .data_loader import download_bars
    df = download_bars(symbol, period)
    
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    # Run backtest
    logger.info(f"Starting backtest with {initial_cash:.2f} cash")
    logger.info(f"Data: {symbol} {period}m bars, {len(df)} rows")
    
    results = cerebro.run()
    
    # Print results
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Final Portfolio Value: {final_value:.2f}")
    logger.info(f"Total Return: {((final_value / initial_cash) - 1) * 100:.2f}%")
    
    # Analyzers
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    
    if sharpe.get("sharperatio"):
        logger.info(f"Sharpe Ratio: {sharpe['sharperatio']:.2f}")
    
    if drawdown.get("max", {}).get("drawdown"):
        logger.info(f"Max Drawdown: {drawdown['max']['drawdown']:.2f}%")
    
    return results
