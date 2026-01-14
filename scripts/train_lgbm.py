import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from tqdm import tqdm
from loguru import logger
import pickle

from quantopen.common.config import load_data_config
from quantopen.datafeed.cache import read_symbol
from quantopen.ml.features import compute_technical_features
from quantopen.ml.labels import compute_future_return_rank, align_market_data

def train_lgbm_ranker():
    # 1. Config & Data
    cfg = load_data_config(Path("configs/data.yaml"))
    bars_dir = Path(cfg.bars_dir)
    logger.info(f"Loading data from {bars_dir} for {len(cfg.symbols)} symbols...")
    
    # 2. Load & Feature Engineering
    features_list = []
    prices_list = {} # for label gen
    
    for sym in tqdm(cfg.symbols, desc="Features"):
        try:
            df = read_symbol(bars_dir, sym)
            
            # Ensure DateTime Index
            if "date" in df.columns:
                df["time"] = pd.to_datetime(df["date"])
                df = df.set_index("time").sort_index()
            
            # Store Close for Labeling
            prices_list[sym] = df["close"]
            
            # Features
            feats = compute_technical_features(df)
            feats["symbol"] = sym # Add Key
            features_list.append(feats)
            
        except Exception as e:
            logger.warning(f"Error processing {sym}: {e}")
            
    if not features_list:
        logger.error("No data found!")
        return

    # Stack Features (Long Format)
    full_feats = pd.concat(features_list)
    logger.info(f"Features shape: {full_feats.shape}")
    
    # 3. Label Engineering (Cross-Sectional Rank)
    # Align prices
    logger.info("Computing Labels (Future Return Rank)...")
    price_matrix = pd.concat(prices_list, axis=1)
    price_matrix = price_matrix.sort_index().ffill()
    
    # Target: 10-min future return rank
    ranks = compute_future_return_rank(price_matrix, horizon=10)
    
    # Melt Ranks to Long Format meant for merge
    # index=time, cols=symbols -> melt to time, symbol, label
    ranks_reset = ranks.reset_index().rename(columns={"index": "time"})
    labels_long = ranks_reset.melt(id_vars=["time"], var_name="symbol", value_name="target")
    # index of melt result is just integers
    # Set multi-index for merge? Or just merge on [time, symbol]
    
    # 4. Merge
    logger.info("Merging Features and Labels...")
    # full_feats index is time. Reset to column
    full_feats_reset = full_feats.reset_index().rename(columns={"index": "time"})
    
    # Ensure dtypes match
    labels_long["time"] = pd.to_datetime(labels_long["time"])
    full_feats_reset["time"] = pd.to_datetime(full_feats_reset["time"])
    
    # Merge
    # inner join: we need both feature and label
    data = pd.merge(full_feats_reset, labels_long, on=["time", "symbol"], how="inner")
    data = data.dropna(subset=["target"]) # Drop Rows where label is NaN
    
    # Remove NaNs in features
    data = data.fillna(0.0) 
    
    data = data.sort_values("time")
    logger.info(f"Final Dataset: {data.shape}")
    
    # 5. Split (Time-based)
    # e.g. First 80% Train, last 20% Valid
    dates = data["time"].unique()
    split_idx = int(len(dates) * 0.8)
    split_date = dates[split_idx]
    
    logger.info(f"Splitting at {split_date}")
    train = data[data["time"] < split_date]
    valid = data[data["time"] >= split_date]
    
    # 6. Prepare LGBM Dataset
    # Sort by time for LambdaRank (queries must be contiguous blocks)
    # Already sorted above
    
    def to_lgb_dataset(df):
        # Features
        ignore_cols = ["time", "symbol", "target"]
        feature_cols = [c for c in df.columns if c not in ignore_cols]
        X = df[feature_cols]
        y = df["target"]
        
        # Group info: how many items in each query (timestamp)
        # Assuming df is strictly sorted by time!
        group = df.groupby("time", sort=False).size().to_numpy()
        
        ds = lgb.Dataset(X, y, group=group)
        return ds, feature_cols
    
    logger.info("Creating LGBM Datasets...")
    train_ds, feat_names = to_lgb_dataset(train)
    valid_ds, _ = to_lgb_dataset(valid)
    
    # 7. Train
    # objective="lambdarank"
    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "n_estimators": 100,
        "ndcg_eval_at": [1, 3, 5],
        "verbose": -1
    }
    
    logger.info("Training LightGBM Ranker...")
    model = lgb.train(
        params,
        train_ds,
        valid_sets=[valid_ds],
        callbacks=[
            lgb.early_stopping(stopping_rounds=10),
            lgb.log_evaluation(10)
        ]
    )
    
    # 8. Save
    model_path = Path("models/lgbm_ranker.txt")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))
    logger.success(f"Model saved to {model_path}")
    
    # Feature Importance
    importance = pd.DataFrame({
        "feature": feat_names,
        "importance": model.feature_importance()
    }).sort_values("importance", ascending=False)
    print(importance.head(10))

if __name__ == "__main__":
    train_lgbm_ranker()
