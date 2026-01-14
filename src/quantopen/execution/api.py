from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Position:
    symbol: str
    volume: int
    available: int
    price: float  # Avg cost or current price
    market_value: float

@dataclass
class Balance:
    total_assets: float
    available_cash: float
    market_value: float

class TradeExecutor(ABC):
    @abstractmethod
    def connect(self, **kwargs):
        """Connect to broker"""
        pass

    @abstractmethod
    def get_balance(self) -> Balance:
        """Get account balance"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        pass

    @abstractmethod
    def buy(self, symbol: str, price: float, amount: int) -> Optional[str]:
        """
        Buy symbol.
        amount: number of shares (e.g. 100)
        Returns: order_id or None
        """
        pass

    @abstractmethod
    def sell(self, symbol: str, price: float, amount: int) -> Optional[str]:
        """
        Sell symbol.
        amount: number of shares
        Returns: order_id or None
        """
        pass
    
    @abstractmethod
    def cancel_all(self):
        """Cancel all open orders"""
        pass
