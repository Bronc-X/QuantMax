"""Risk control filters for A-stock trading."""
from __future__ import annotations
import backtrader as bt
from loguru import logger


class RiskFilters:
    """
    Collection of risk filters for A-stock minute-level trading.
    
    Usage in strategy:
        self.filters = RiskFilters(self)
        
        def next(self):
            for d in self.datas:
                if self.filters.is_limit_up(d):
                    continue  # skip buying
    """
    
    def __init__(self, strategy: bt.Strategy, limit_up_threshold: float = 0.095):
        self.strategy = strategy
        self.limit_up_threshold = limit_up_threshold
    
    def is_limit_up(self, data) -> bool:
        """
        Check if stock is at or near limit up (涨停).
        Uses previous bar's close to current bar's close.
        
        A-stock limit: +10% for main board, +20% for 创业板/科创板
        We use 9.5% as simplified threshold.
        """
        if len(data) < 2:
            return False
        
        prev_close = data.close[-1]
        curr_close = data.close[0]
        
        if prev_close <= 0:
            return False
        
        change_pct = (curr_close - prev_close) / prev_close
        return change_pct >= self.limit_up_threshold
    
    def is_limit_down(self, data) -> bool:
        """Check if stock is at or near limit down (跌停)."""
        if len(data) < 2:
            return False
        
        prev_close = data.close[-1]
        curr_close = data.close[0]
        
        if prev_close <= 0:
            return False
        
        change_pct = (curr_close - prev_close) / prev_close
        return change_pct <= -self.limit_up_threshold


class LiquidityFilter:
    """
    Filter stocks based on liquidity (trading volume/amount).
    
    Usage:
        self.liquidity = LiquidityFilter(lookback=30, min_avg_volume=10000)
    """
    
    def __init__(self, lookback: int = 30, min_avg_volume: float = 10000):
        self.lookback = lookback
        self.min_avg_volume = min_avg_volume
        self._cache = {}  # data -> rolling avg
    
    def is_liquid(self, data) -> bool:
        """
        Check if stock has sufficient liquidity.
        Uses rolling average of volume over lookback period.
        """
        if len(data) < self.lookback:
            return True  # not enough data, allow trading
        
        # Calculate rolling average volume
        volumes = [data.volume[-i] for i in range(self.lookback)]
        avg_volume = sum(volumes) / len(volumes)
        
        return avg_volume >= self.min_avg_volume
    
    def get_avg_volume(self, data) -> float:
        """Get rolling average volume for a data feed."""
        if len(data) < self.lookback:
            return data.volume[0]
        
        volumes = [data.volume[-i] for i in range(self.lookback)]
        return sum(volumes) / len(volumes)


class DrawdownRiskControl:
    """
    Account-level drawdown risk control.
    
    Tracks peak portfolio value and triggers actions when drawdown exceeds threshold.
    
    Usage:
        self.dd_control = DrawdownRiskControl(broker, max_dd_pct=0.10)
        
        def next(self):
            self.dd_control.update()
            if self.dd_control.should_reduce_position():
                # reduce or close positions
    """
    
    def __init__(
        self,
        broker,
        max_dd_pct: float = 0.10,  # 10% max drawdown
        reduce_at_pct: float = 0.05,  # start reducing at 5%
        initial_cash: float = None,
    ):
        self.broker = broker
        self.max_dd_pct = max_dd_pct
        self.reduce_at_pct = reduce_at_pct
        self.peak_value = initial_cash or broker.getcash()
        self.current_dd_pct = 0.0
    
    def update(self) -> float:
        """Update peak value and return current drawdown percentage."""
        current_value = self.broker.getvalue()
        
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        if self.peak_value > 0:
            self.current_dd_pct = (self.peak_value - current_value) / self.peak_value
        else:
            self.current_dd_pct = 0.0
        
        return self.current_dd_pct
    
    def should_reduce_position(self) -> bool:
        """Check if we should reduce position size."""
        return self.current_dd_pct >= self.reduce_at_pct
    
    def should_stop_trading(self) -> bool:
        """Check if we should stop trading (max drawdown hit)."""
        return self.current_dd_pct >= self.max_dd_pct
    
    def get_position_scale(self) -> float:
        """
        Get position scale factor based on current drawdown.
        Returns 1.0 when no drawdown, scales down linearly as DD increases.
        """
        if self.current_dd_pct <= 0:
            return 1.0
        elif self.current_dd_pct >= self.max_dd_pct:
            return 0.0
        else:
            # Linear scale from 1.0 at 0% DD to 0.0 at max_dd_pct
            return 1.0 - (self.current_dd_pct / self.max_dd_pct)
