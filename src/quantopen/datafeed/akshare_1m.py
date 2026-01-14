from __future__ import annotations
import pandas as pd
from loguru import logger

def _normalize_symbol(symbol: str) -> str:
    # accept "600000" or "sh600000"/"sz000001" style; normalize to 6-digit
    s = symbol.strip().lower().replace("sh", "").replace("sz", "")
    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"Bad symbol: {symbol}")
    return s

def fetch_1m_eastmoney(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Uses AkShare Eastmoney minute kline.
    Note: AkShare API may change; if it errors, we swap provider quickly.
    Output columns: datetime, open, high, low, close, volume, amount
    """
    import akshare as ak

    sym = _normalize_symbol(symbol)

    # Eastmoney minute API often expects market prefix; AkShare handles some formats
    # We'll try both "sh/sz" heuristics:
    pref = "sh" if sym.startswith(("5", "6", "9")) else "sz"
    em_symbol = f"{pref}{sym}"

    try:
        df = ak.stock_zh_a_hist_min_em(
            symbol=em_symbol,
            start_date=start_date,
            end_date=end_date,
            period="1",
            adjust=""
        )
    except Exception as e:
        logger.warning(f"Fetch failed with {em_symbol}: {e}. Trying raw {sym}...")
        df = ak.stock_zh_a_hist_min_em(
            symbol=sym,
            start_date=start_date,
            end_date=end_date,
            period="1",
            adjust=""
        )

    if df is None or df.empty:
        return pd.DataFrame(columns=["datetime","open","high","low","close","volume","amount"])

    # AkShare columns commonly: ['时间','开盘','收盘','最高','最低','成交量','成交额','振幅','涨跌幅','涨跌额','换手率']
    colmap = {
        "时间": "datetime",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "日期": "datetime",
    }
    df = df.rename(columns=colmap)

    need = ["datetime","open","high","low","close","volume","amount"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns from AkShare response: {missing}. Got: {list(df.columns)}")

    df = df[need].copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    for c in ["open","high","low","close","volume","amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["datetime","close"]).sort_values("datetime").reset_index(drop=True)
    return df
