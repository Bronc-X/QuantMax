from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from loguru import logger


@dataclass
class QlibExportConfig:
    qlib_dir: Path
    bars_dir: Path
    market: str = "cn"
    freq: str = "1min"


def _ensure_dirs(root: Path) -> dict[str, Path]:
    """
    Create a minimal qlib data layout.

    root/
      calendars/1min.txt
      instruments/all.txt
      features/           (per symbol)
        600000.parquet
        000001.parquet
    """
    calendars = root / "calendars"
    instruments = root / "instruments"
    features = root / "features"

    calendars.mkdir(parents=True, exist_ok=True)
    instruments.mkdir(parents=True, exist_ok=True)
    features.mkdir(parents=True, exist_ok=True)

    return {"calendars": calendars, "instruments": instruments, "features": features}


def _list_symbols_from_bars(bars_dir: Path) -> list[str]:
    syms = []
    for fp in bars_dir.glob("*.parquet"):
        syms.append(fp.stem)
    syms = sorted(set(syms))
    return syms


def _load_symbol_1m(bars_fp: Path) -> pd.DataFrame:
    df = pd.read_parquet(bars_fp)
    # expected columns from our cache:
    # datetime, open, high, low, close, volume, amount
    if "datetime" not in df.columns:
        raise ValueError(f"Missing datetime column in {bars_fp}")
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").drop_duplicates(subset=["datetime"])
    # basic cleaning
    for c in ["open", "high", "low", "close", "volume", "amount"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["datetime", "close"])
    return df


def _build_calendar(all_datetimes: Iterable[pd.Timestamp]) -> pd.Series:
    cal = pd.Series(pd.to_datetime(list(all_datetimes))).dropna().drop_duplicates().sort_values()
    return cal


def export_qlib_minute_dataset(cfg: QlibExportConfig, symbols: list[str] | None = None) -> None:
    paths = _ensure_dirs(cfg.qlib_dir)

    if symbols is None:
        symbols = _list_symbols_from_bars(cfg.bars_dir)

    if not symbols:
        raise RuntimeError(f"No symbols found under {cfg.bars_dir}")

    logger.info(f"Exporting {len(symbols)} symbols from {cfg.bars_dir} -> {cfg.qlib_dir}")

    # 1) export per-symbol features parquet
    all_dt = []
    exported = 0

    for sym in symbols:
        bars_fp = cfg.bars_dir / f"{sym}.parquet"
        if not bars_fp.exists():
            continue

        df = _load_symbol_1m(bars_fp)

        # Qlib convention: index as datetime, columns as features
        out = df.set_index("datetime")[["open", "high", "low", "close", "volume", "amount"]].copy()
        out.index.name = "datetime"

        # store features file
        out_fp = paths["features"] / f"{sym}.parquet"
        out.to_parquet(out_fp)

        all_dt.extend(out.index.to_list())
        exported += 1

    if exported == 0:
        raise RuntimeError("No symbol parquet exported. Check your bars_dir content.")

    # 2) calendar
    cal = _build_calendar(all_dt)
    cal_fp = paths["calendars"] / f"{cfg.freq}.txt"
    # one datetime per line, ISO format
    cal.astype("datetime64[ns]").dt.strftime("%Y-%m-%d %H:%M:%S").to_csv(
        cal_fp, index=False, header=False
    )
    logger.info(f"Calendar written: {cal_fp} (rows={len(cal)})")

    # 3) instruments list
    # Minimal instrument file: one symbol per line
    inst_fp = paths["instruments"] / "all.txt"
    pd.Series(symbols).to_csv(inst_fp, index=False, header=False)
    logger.info(f"Instruments written: {inst_fp} (rows={len(symbols)})")

    logger.success("Qlib minute dataset export completed.")
