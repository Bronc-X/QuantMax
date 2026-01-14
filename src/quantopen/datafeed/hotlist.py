import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger

def fetch_and_append_hotlist(output_path: str = "data/raw/hotlist.csv", source: str = "em"):
    """
    Fetch current hotlist from source and append to CSV.
    Sources:
      - 'em': Eastmoney (东方财富)
      - 'xq': XueQiu (雪球)
    """
    logger.info(f"Fetching hotlist from {source}...")
    
    try:
        if source == "em":
            # 东方财富
            df = ak.stock_hot_rank_em()
            # Cols: 序号, 代码, 名称, 最新价, ...
            # Extract symbol from "代码"
            
            # Data cleaning for EM
            out_df = pd.DataFrame()
            out_df["symbol"] = df["代码"].astype(str).str.zfill(6)
            out_df["rank"] = range(1, len(df) + 1)
            
        elif source == "xq":
            # 雪球 (热度榜)
            # stock_hot_follow_xq returns: symbol, ...
            # Usually returns detailed columns. Let's check headers if needed, 
            # but usually it has 'symbol' or 'code'.
            # Note: Akshare xq might use SH/SZ prefix or just code.
            df = ak.stock_hot_follow_xq()
            
            # XQ usually has columns like 'symbol' (SH600...), 'name', ...
            out_df = pd.DataFrame()
            # Clean symbol (remove SH/SZ prefix if present)
            # Assuming column is 'symbol' or 'code'
            # Let's try to find the code column
            target_col = None
            for col in ["code", "symbol", "股票代码"]:
                if col in df.columns:
                    target_col = col
                    break
            
            if target_col:
                 # Remove non-digit chars
                 out_df["symbol"] = df[target_col].astype(str).str.extract(r'(\d{6})')[0]
            else:
                 # Fallback: assume first column is code
                 out_df["symbol"] = df.iloc[:, 0].astype(str).str.extract(r'(\d{6})')[0]
                 
            out_df["rank"] = range(1, len(df) + 1)
            
        else:
            logger.error(f"Unknown source: {source}")
            return

    except Exception as e:
        logger.error(f"Failed to fetch hotlist from {source}: {e}")
        return

    # Standardize
    if out_df.empty:
        logger.warning(f"Fetched hotlist from {source} is empty")
        return
        
    out_df = out_df.dropna(subset=["symbol"])
    
    # Date: Use current system date
    today = datetime.now().date()
    out_df["date"] = today
    
    # Add source column? No, we stick to (date,symbol,rank) schema.
    # But wait, if we have multiple sources, ranks might conflict?
    # Strategy expects ONE rank per symbol per day.
    # If we run both, valid strategy is: use the MIN rank (highest popularity) or Average.
    # But current CSV schema is simple. 
    # Let's just output to the file. If user runs EM then XQ, the second one might overwrite or duplicate?
    # My previous logic: `existing = existing[existing["date"] != today]`.
    # This means the LAST run source wins for the day. 
    # This is acceptable for "Switching sources".
    
    # Reorder
    out_df = out_df[["date", "symbol", "rank"]]
    
    # Save/Append
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.exists():
        existing = pd.read_csv(path)
        existing["date"] = pd.to_datetime(existing["date"]).dt.date
        
        # Remove existing data for today to avoid duplicates (overwrite today)
        existing = existing[existing["date"] != today]
        
        final_df = pd.concat([existing, out_df], axis=0).sort_values(["date", "rank"])
    else:
        final_df = out_df
        
    final_df.to_csv(path, index=False)
    logger.success(f"Saved {len(out_df)} rows from {source} for {today} to {path}")
    logger.info(f"Top 3: {out_df.head(3)['symbol'].tolist()}")

if __name__ == "__main__":
    fetch_and_append_hotlist()
