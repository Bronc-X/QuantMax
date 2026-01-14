from __future__ import annotations
from pathlib import Path
import pandas as pd
import backtrader as bt


class ParquetMinuteData(bt.feeds.PandasData):
    params = (
        ("datetime", None),  # index is datetime
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "volume"),
        # custom lines (optional)
        ("amount", "amount"),
        ("openinterest", None),
    )

    lines = ("amount",)


def load_symbol_parquet(fp: Path) -> pd.DataFrame:
    df = pd.read_parquet(fp).copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").drop_duplicates(subset=["datetime"])
    df = df.set_index("datetime").sort_index()

    # ensure columns
    for c in ["open", "high", "low", "close", "volume"]:
        if c not in df.columns:
            raise ValueError(f"Missing {c} in {fp}")
    if "amount" not in df.columns:
        df["amount"] = 0.0

    return df[["open", "high", "low", "close", "volume", "amount"]]
