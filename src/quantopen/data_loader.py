"""Data loader module for downloading and caching market data from AkShare."""

from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger
from tqdm import tqdm

try:
    import akshare as ak
except ImportError:
    ak = None
    logger.warning("AkShare not installed, data download will not work")


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "bars_1m"


def download_bars(
    symbol: str,
    period: str = "1",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    Download minute-level bar data from AkShare (东方财富).
    
    Args:
        symbol: Stock symbol, e.g., "000001" for 平安银行
        period: Period in minutes: "1", "5", "15", "30", "60"
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        adjust: Adjustment type: "qfq" (前复权), "hfq" (后复权), "" (不复权)
    
    Returns:
        DataFrame with OHLCV data
    """
    if ak is None:
        raise ImportError("AkShare is required for data download")
    
    cache_path = DATA_DIR / f"{symbol}_{period}m.parquet"
    
    # Check cache first
    if cache_path.exists():
        logger.info(f"Loading cached data from {cache_path}")
        df = pd.read_parquet(cache_path)
        return df
    
    logger.info(f"Downloading {symbol} {period}m bars from AkShare...")
    
    try:
        # 东方财富分钟线接口
        df = ak.stock_zh_a_hist_min_em(
            symbol=symbol,
            period=period,
            adjust=adjust,
        )
        
        # Standardize column names
        df = df.rename(columns={
            "时间": "datetime",
            "开盘": "open",
            "收盘": "close", 
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        })
        
        # Convert datetime
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")
        
        # Cache to parquet
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, engine="pyarrow")
        logger.info(f"Cached data to {cache_path}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to download data: {e}")
        raise


def load_cached_bars(symbol: str, period: str = "1") -> Optional[pd.DataFrame]:
    """Load cached bar data if available."""
    cache_path = DATA_DIR / f"{symbol}_{period}m.parquet"
    
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    
    return None


def list_cached_symbols() -> list[str]:
    """List all cached symbols."""
    if not DATA_DIR.exists():
        return []
    
    files = DATA_DIR.glob("*.parquet")
    symbols = [f.stem.split("_")[0] for f in files]
    return list(set(symbols))
