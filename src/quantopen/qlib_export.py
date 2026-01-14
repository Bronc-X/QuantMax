"""Qlib data export utilities.

Export minute-line data from parquet cache to Qlib bin format.
This is a placeholder/interface for future Qlib integration.
You can train LGBModel, GRU, and other ML models with Qlib.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd
from loguru import logger


def export_to_qlib_csv(
    bars_dir: str | Path,
    output_dir: str | Path,
    symbols: list[str] | None = None,
) -> Path:
    """
    Export parquet data to Qlib-compatible CSV format.
    
    Qlib expects CSV with columns:
    - date (or datetime)
    - symbol
    - open, high, low, close, volume
    
    Args:
        bars_dir: Directory containing parquet files
        output_dir: Output directory for CSVs
        symbols: Optional list of symbols to export (None = all)
    
    Returns:
        Path to exported CSV file
    """
    bars_path = Path(bars_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Collect all parquet files
    if symbols:
        files = [bars_path / f"{s}.parquet" for s in symbols if (bars_path / f"{s}.parquet").exists()]
    else:
        files = list(bars_path.glob("*.parquet"))
    
    if not files:
        raise ValueError(f"No parquet files found in {bars_path}")
    
    # Concatenate all data
    dfs = []
    for fp in files:
        symbol = fp.stem
        df = pd.read_parquet(fp)
        df["symbol"] = symbol
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    
    # Normalize for Qlib
    combined["datetime"] = pd.to_datetime(combined["datetime"])
    combined["date"] = combined["datetime"].dt.date
    
    # Qlib standard columns
    qlib_cols = ["datetime", "symbol", "open", "high", "low", "close", "volume"]
    if "amount" in combined.columns:
        qlib_cols.append("amount")
    
    combined = combined[qlib_cols].sort_values(["symbol", "datetime"])
    
    # Export
    output_file = output_path / f"qlib_data_{datetime.now().strftime('%Y%m%d')}.csv"
    combined.to_csv(output_file, index=False)
    
    logger.info(f"Exported {len(combined)} rows, {len(files)} symbols to {output_file}")
    return output_file


def create_qlib_instruments(
    symbols: list[str],
    output_dir: str | Path,
    market: str = "csi300",
) -> Path:
    """
    Create Qlib instruments file.
    
    Args:
        symbols: List of stock symbols
        output_dir: Output directory
        market: Market name (default: csi300)
    
    Returns:
        Path to instruments file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create instruments file
    instruments_file = output_path / f"{market}.txt"
    
    with open(instruments_file, "w") as f:
        for sym in sorted(symbols):
            # Qlib expects format like "SH600000" or "SZ000001"
            if sym.startswith(("6", "5", "9")):
                qlib_sym = f"SH{sym}"
            else:
                qlib_sym = f"SZ{sym}"
            
            # Format: symbol\tstart_date\tend_date
            f.write(f"{qlib_sym}\t2020-01-01\t2030-01-01\n")
    
    logger.info(f"Created instruments file: {instruments_file}")
    return instruments_file


# ============================================================
# Qlib Integration Notes (for future implementation)
# ============================================================
#
# To fully integrate with Qlib:
#
# 1. Install Qlib:
#    pip install pyqlib
#
# 2. Initialize Qlib with your data:
#    import qlib
#    qlib.init(provider_uri="~/.qlib/qlib_data/cn_data")
#
# 3. Use the exported data:
#    from qlib.data import D
#    df = D.features(
#        instruments="csi300",
#        fields=["$open", "$high", "$low", "$close", "$volume"],
#        start_time="2024-01-01",
#        end_time="2024-12-31",
#    )
#
# 4. Train models:
#    from qlib.contrib.model.gbdt import LGBModel
#    from qlib.data.dataset import DatasetH
#
#    dataset = DatasetH(...)
#    model = LGBModel()
#    model.fit(dataset)
#
# ============================================================
