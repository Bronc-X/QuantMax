from __future__ import annotations
from pathlib import Path
import pandas as pd

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def symbol_path(bars_dir: Path, symbol: str) -> Path:
    return bars_dir / f"{symbol}.parquet"

def read_symbol(bars_dir: Path, symbol: str) -> pd.DataFrame | None:
    fp = symbol_path(bars_dir, symbol)
    if not fp.exists():
        return None
    return pd.read_parquet(fp)

def write_symbol(bars_dir: Path, symbol: str, df: pd.DataFrame) -> Path:
    ensure_dir(bars_dir)
    fp = symbol_path(bars_dir, symbol)
    df.to_parquet(fp, index=False)
    return fp

def merge_dedup_sort(old: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    if old is None or old.empty:
        out = new.copy()
    else:
        out = pd.concat([old, new], axis=0, ignore_index=True)
    # normalize datetime column name
    if "datetime" not in out.columns:
        raise ValueError("Expected column 'datetime'")
    out["datetime"] = pd.to_datetime(out["datetime"])
    out = out.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    return out
