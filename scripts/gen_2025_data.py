import pandas as pd
import numpy as np
import random
from pathlib import Path
from quantopen.common.config import load_data_config

def gen_2025_aux_data():
    cfg = load_data_config(Path("configs/data.yaml"))
    
    # Generate dates for 2025
    dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="B") # Business days
    
    # 1. Hotlist
    # Generate random ranks for symbols each day
    # We'll make some symbols "hot" more often to simulate momentum
    hot_data = []
    
    for date in dates:
        # Randomly select 5-8 symbols to be on hotlist
        daily_hot = random.sample(cfg.symbols, k=random.randint(5, 8))
        for i, sym in enumerate(daily_hot):
            rank = i + 1  # 1-based rank
            hot_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "symbol": sym,
                "rank": rank
            })
            
    hot_df = pd.DataFrame(hot_data)
    hot_path = Path("data/raw/hotlist_2025.csv")
    hot_path.parent.mkdir(parents=True, exist_ok=True)
    hot_df.to_csv(hot_path, index=False)
    print(f"Generated {hot_path} with {len(hot_df)} rows")
    
    # 2. Themes
    # Assign random theme boost to each symbol
    theme_data = []
    for sym in cfg.symbols:
        boost = round(random.uniform(0.0, 0.3), 2) # 0.0 to 0.3 boost
        theme_data.append({
            "symbol": sym,
            "theme_boost": boost
        })
        
    theme_df = pd.DataFrame(theme_data)
    theme_path = Path("data/raw/themes_2025.csv")
    theme_df.to_csv(theme_path, index=False)
    print(f"Generated {theme_path} with {len(theme_df)} rows")

if __name__ == "__main__":
    gen_2025_aux_data()
