from __future__ import annotations
from pathlib import Path
import pandas as pd
import backtrader as bt

class ParquetMinuteData(bt.feeds.PandasData):
    """Minute-level data feed from parquet files with datetime as index."""
    params = (
        ("datetime", None),  # None means use index as datetime
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        ("openinterest", -1),  # -1 means column not present
    )

def load_symbol_parquet(fp: Path) -> pd.DataFrame:
    """Load parquet file and prepare for Backtrader."""
    df = pd.read_parquet(fp)
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    # backtrader expects OHLCV columns
    return df[["open", "high", "low", "close", "volume"]]
