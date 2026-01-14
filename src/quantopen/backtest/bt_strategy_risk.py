"""Enhanced strategy with risk controls."""
from __future__ import annotations
import backtrader as bt
from loguru import logger

from quantopen.backtest.risk_filters import (
    RiskFilters,
    LiquidityFilter,
    DrawdownRiskControl,
)


class HoldNMinutesWithRisk(bt.Strategy):
    """
    Enhanced HoldNMinutes strategy with:
    - Limit-up filter (涨停过滤)
    - Liquidity filter (流动性过滤)
    - Drawdown risk control (回撤风控)
    """
    
    params = dict(
        hold_minutes=60,
        target_percent=0.1,
        max_positions=5,
        # Risk control params
        limit_up_threshold=0.095,
        min_avg_volume=10000,
        volume_lookback=30,
        max_drawdown_pct=0.10,
        reduce_at_drawdown=0.05,
    )

    def __init__(self):
        self.entry_bar = {}
        
        # Initialize risk controls
        self.risk_filters = RiskFilters(self, self.p.limit_up_threshold)
        self.liquidity = LiquidityFilter(
            lookback=self.p.volume_lookback,
            min_avg_volume=self.p.min_avg_volume,
        )
        self.dd_control = DrawdownRiskControl(
            self.broker,
            max_dd_pct=self.p.max_drawdown_pct,
            reduce_at_pct=self.p.reduce_at_drawdown,
        )
        
        # Tracking
        self.order_count = 0
        self.filtered_count = 0

    def log(self, txt: str):
        dt = self.datas[0].datetime.datetime(0)
        logger.debug(f"{dt.isoformat()} {txt}")

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY {order.data._name} @ {order.executed.price:.2f}")
            else:
                self.log(f"SELL {order.data._name} @ {order.executed.price:.2f}")

    def next(self):
        # Update drawdown control
        current_dd = self.dd_control.update()
        
        # Check if we should stop trading
        if self.dd_control.should_stop_trading():
            # Close all positions
            for d in self.datas:
                if self.getposition(d).size != 0:
                    self.close(data=d)
                    self.log(f"DD STOP: Closing {d._name}")
            return
        
        # Get position scale based on drawdown
        position_scale = self.dd_control.get_position_scale()
        
        # Check existing positions for exit
        for d in self.datas:
            pos = self.getposition(d).size
            if pos != 0:
                if d in self.entry_bar:
                    held = len(d) - self.entry_bar[d]
                    if held >= self.p.hold_minutes:
                        self.close(data=d)
                        del self.entry_bar[d]
                continue

        # Open new positions if room
        current_positions = sum(1 for d in self.datas if self.getposition(d).size != 0)
        room = self.p.max_positions - current_positions
        if room <= 0:
            return
        
        # Collect and filter candidates
        candidates = []
        for d in self.datas:
            if self.getposition(d).size != 0:
                continue
            
            # Apply filters
            if self.risk_filters.is_limit_up(d):
                self.filtered_count += 1
                continue
            
            if not self.liquidity.is_liquid(d):
                self.filtered_count += 1
                continue
            
            candidates.append(d)
        
        # Open positions with scaled target
        scaled_target = self.p.target_percent * position_scale
        
        for d in candidates[:room]:
            self.order_target_percent(data=d, target=scaled_target)
            self.entry_bar[d] = len(d)
            self.order_count += 1

    def stop(self):
        logger.info(
            f"Strategy finished: {self.order_count} orders, "
            f"{self.filtered_count} filtered, "
            f"final value: {self.broker.getvalue():,.2f}"
        )
