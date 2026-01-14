import pandas as pd
import numpy as np
from loguru import logger

def compute_future_return_rank(prices: pd.DataFrame, horizon: int = 10) -> pd.DataFrame:
    """
    Compute cross-sectional rank of future N-minute returns.
    
    Args:
        prices (pd.DataFrame): Wide dataframe of close prices. 
                               Index=Datetime, Columns=Symbols.
        horizon (int): N minutes into the future.
        
    Returns:
        pd.DataFrame: DataFrame of ranks (0.0 to 1.0) for each timestamp/symbol.
                      Target Label for "Learning to Rank".
    """
    # 1. Calculate Future Return
    # Ret = (P_{t+h} / P_t) - 1.0
    # shift(-h) moves future data to current row
    future_prices = prices.shift(-horizon)
    returns = (future_prices / prices) - 1.0
    
    # 2. Cross-Sectional Ranking (Row-wise)
    # rank(axis=1) ranks columns for each row
    # pct=True normalizes to [0, 1]
    ranks = returns.rank(axis=1, pct=True)
    
    # Handle NaNs (e.g. end of data, or halt)
    # If a stock is halted (NaN price), return is NaN -> Rank is NaN.
    # LightGBM handles NaN targets by ignoring? Or we fill?
    # Usually we drop rows/samples where target is NaN.
    
    return ranks

def align_market_data(bars_loader) -> pd.DataFrame:
    """
    Helper to load multi-symbol price matrix.
    bars_loader: functions that yields (symbol, df)
    """
    dfs = {}
    for symbol, df in bars_loader:
        if "close" in df.columns:
            dfs[symbol] = df["close"]
    
    if not dfs:
        return pd.DataFrame()
        
    # Concat strategies: outer join to align times
    price_matrix = pd.concat(dfs, axis=1)
    # Forward fill to handle small missing bars (suspension handling is separate)
    price_matrix = price_matrix.sort_index().ffill()
    
    return price_matrix
