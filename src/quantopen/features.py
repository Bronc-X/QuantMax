"""Feature engineering module with placeholder interface for proprietary features."""

from typing import Any, Optional
import pandas as pd
import numpy as np
from loguru import logger


class FeatureRegistry:
    """
    Registry for feature computation functions.
    
    Use this to register both open-source and proprietary features.
    Proprietary features can be added via plugins without modifying core code.
    """
    
    _features: dict[str, callable] = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a feature function."""
        def decorator(func):
            cls._features[name] = func
            logger.debug(f"Registered feature: {name}")
            return func
        return decorator
    
    @classmethod
    def compute(cls, name: str, df: pd.DataFrame, **kwargs) -> pd.Series:
        """Compute a registered feature."""
        if name not in cls._features:
            raise KeyError(f"Feature '{name}' not registered")
        
        return cls._features[name](df, **kwargs)
    
    @classmethod
    def compute_all(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Compute all registered features."""
        result = df.copy()
        
        for name, func in cls._features.items():
            try:
                result[name] = func(df, **kwargs)
            except Exception as e:
                logger.warning(f"Failed to compute feature {name}: {e}")
        
        return result
    
    @classmethod
    def list_features(cls) -> list[str]:
        """List all registered features."""
        return list(cls._features.keys())


# ============================================================
# Built-in Open-Source Features
# ============================================================

@FeatureRegistry.register("sma_5")
def sma_5(df: pd.DataFrame, **kwargs) -> pd.Series:
    """5-period Simple Moving Average."""
    return df["close"].rolling(window=5).mean()


@FeatureRegistry.register("sma_10")
def sma_10(df: pd.DataFrame, **kwargs) -> pd.Series:
    """10-period Simple Moving Average."""
    return df["close"].rolling(window=10).mean()


@FeatureRegistry.register("sma_20")
def sma_20(df: pd.DataFrame, **kwargs) -> pd.Series:
    """20-period Simple Moving Average."""
    return df["close"].rolling(window=20).mean()


@FeatureRegistry.register("ema_12")
def ema_12(df: pd.DataFrame, **kwargs) -> pd.Series:
    """12-period Exponential Moving Average."""
    return df["close"].ewm(span=12, adjust=False).mean()


@FeatureRegistry.register("ema_26")
def ema_26(df: pd.DataFrame, **kwargs) -> pd.Series:
    """26-period Exponential Moving Average."""
    return df["close"].ewm(span=26, adjust=False).mean()


@FeatureRegistry.register("macd")
def macd(df: pd.DataFrame, **kwargs) -> pd.Series:
    """MACD Line (12-day EMA - 26-day EMA)."""
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    return ema12 - ema26


@FeatureRegistry.register("macd_signal")
def macd_signal(df: pd.DataFrame, **kwargs) -> pd.Series:
    """MACD Signal Line (9-day EMA of MACD)."""
    macd_line = macd(df)
    return macd_line.ewm(span=9, adjust=False).mean()


@FeatureRegistry.register("rsi_14")
def rsi_14(df: pd.DataFrame, **kwargs) -> pd.Series:
    """14-period Relative Strength Index."""
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))


@FeatureRegistry.register("bollinger_upper")
def bollinger_upper(df: pd.DataFrame, window: int = 20, num_std: float = 2.0, **kwargs) -> pd.Series:
    """Bollinger Band Upper."""
    sma = df["close"].rolling(window=window).mean()
    std = df["close"].rolling(window=window).std()
    return sma + (std * num_std)


@FeatureRegistry.register("bollinger_lower")
def bollinger_lower(df: pd.DataFrame, window: int = 20, num_std: float = 2.0, **kwargs) -> pd.Series:
    """Bollinger Band Lower."""
    sma = df["close"].rolling(window=window).mean()
    std = df["close"].rolling(window=window).std()
    return sma - (std * num_std)


@FeatureRegistry.register("atr_14")
def atr_14(df: pd.DataFrame, **kwargs) -> pd.Series:
    """14-period Average True Range."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=14).mean()


@FeatureRegistry.register("volume_sma_20")
def volume_sma_20(df: pd.DataFrame, **kwargs) -> pd.Series:
    """20-period Volume Moving Average."""
    return df["volume"].rolling(window=20).mean()


@FeatureRegistry.register("volume_ratio")
def volume_ratio(df: pd.DataFrame, **kwargs) -> pd.Series:
    """Volume ratio vs 20-period average."""
    vol_sma = df["volume"].rolling(window=20).mean()
    return df["volume"] / vol_sma


@FeatureRegistry.register("return_1")
def return_1(df: pd.DataFrame, **kwargs) -> pd.Series:
    """1-period log return."""
    return np.log(df["close"] / df["close"].shift(1))


@FeatureRegistry.register("return_5")
def return_5(df: pd.DataFrame, **kwargs) -> pd.Series:
    """5-period log return."""
    return np.log(df["close"] / df["close"].shift(5))


# ============================================================
# Placeholder for Proprietary Features
# ============================================================

class ProprietaryFeaturePlugin:
    """
    Base class for proprietary feature plugins.
    
    Inherit from this class to create your own feature plugin:
    
    ```python
    class MyStrategy(ProprietaryFeaturePlugin):
        def register_features(self):
            @FeatureRegistry.register("my_secret_alpha")
            def my_alpha(df, **kwargs):
                # Your proprietary logic here
                return computed_series
    ```
    """
    
    def __init__(self):
        self.register_features()
    
    def register_features(self):
        """Override this method to register your proprietary features."""
        pass


def compute_features(
    df: pd.DataFrame,
    feature_names: Optional[list[str]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Compute features for a dataframe.
    
    Args:
        df: Input OHLCV dataframe
        feature_names: List of feature names to compute (None = all)
        **kwargs: Additional parameters for feature functions
    
    Returns:
        DataFrame with added feature columns
    """
    result = df.copy()
    
    names = feature_names or FeatureRegistry.list_features()
    
    for name in names:
        try:
            result[name] = FeatureRegistry.compute(name, df, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to compute feature {name}: {e}")
    
    return result
