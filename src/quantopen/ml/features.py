import pandas as pd
import numpy as np

def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical features for a single symbol.
    Input df must have: open, high, low, close, volume, amount
    """
    out = pd.DataFrame(index=df.index)
    close = df["close"]
    
    # 1. Momentum (Returns)
    out["ret_1"] = close.pct_change(1)
    out["ret_5"] = close.pct_change(5)
    out["ret_30"] = close.pct_change(30)
    
    # 2. Volatility (StdDev of 1-min returns)
    r1 = out["ret_1"]
    out["vol_5"] = r1.rolling(5).std()
    out["vol_30"] = r1.rolling(30).std()
    
    # 3. Bias (Distance from Moving Average)
    ma_5 = close.rolling(5).mean()
    ma_30 = close.rolling(30).mean()
    out["bias_5"] = (close / ma_5) - 1
    out["bias_30"] = (close / ma_30) - 1
    
    # 4. Volume / Liquidity
    if "amount" in df.columns:
        amt = df["amount"]
        amt_ma_30 = amt.rolling(30).mean() + 1.0 # avoid div 0
        out["amt_norm_30"] = amt / amt_ma_30
        
    # 5. Intraday Range (Volatility proxy)
    if "high" in df.columns and "low" in df.columns:
        out["hl_spread"] = (df["high"] - df["low"]) / close
    
    # 6. Time features (Min of day)
    # Useful for model to know "Open" vs "Close" behavior
    # Assuming index is Datetime
    # out["min_of_day"] = df.index.hour * 60 + df.index.minute
    
    return out

def get_feature_names(df: pd.DataFrame) -> list:
    return [c for c in df.columns if c not in ["date", "symbol", "open", "high", "low", "close", "volume", "amount"]]
