import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_squared_error
import joblib
from pathlib import Path
from tqdm import tqdm
from loguru import logger

from quantopen.common.config import load_data_config
from quantopen.datafeed.cache import read_symbol
from quantopen.ml.features import compute_technical_features, get_feature_names
from quantopen.ml.labels import compute_future_return_rank

def train_ranker_model():
    # 1. Config & Data
    cfg = load_data_config(Path("configs/data.yaml"))
    bars_dir = Path(cfg.bars_dir)
    logger.info(f"Loading data from {bars_dir} for {len(cfg.symbols)} symbols...")
    
    # 2. Load & Feature Engineering
    features_list = []
    prices_list = {} 
    
    # We need to know feature names
    feature_names = None
    
    for sym in tqdm(cfg.symbols, desc="Features"):
        try:
            df = read_symbol(bars_dir, sym)
            
            # Ensure DateTime Index
            if "date" in df.columns:
                df["time"] = pd.to_datetime(df["date"])
                df = df.set_index("time").sort_index()
            
            prices_list[sym] = df["close"]
            
            # Features
            feats = compute_technical_features(df)
            if feature_names is None:
                feature_names = feats.columns.tolist()
                
            feats["symbol"] = sym 
            features_list.append(feats)
            
        except Exception as e:
            logger.warning(f"Error processing {sym}: {e}")
            
    if not features_list:
        logger.error("No data found!")
        return

    # Stack Features
    full_feats = pd.concat(features_list)
    
    # 3. Label Engineering (Future Return Rank)
    logger.info("Computing Labels (Future Return Rank)...")
    price_matrix = pd.concat(prices_list, axis=1)
    price_matrix = price_matrix.sort_index().ffill()
    
    # Target: 10-min future return rank
    ranks = compute_future_return_rank(price_matrix, horizon=10)
    
    # Melt Ranks
    ranks_reset = ranks.reset_index().rename(columns={"index": "time"})
    labels_long = ranks_reset.melt(id_vars=["time"], var_name="symbol", value_name="target")
    
    # 4. Merge
    logger.info("Merging Features and Labels...")
    full_feats_reset = full_feats.reset_index().rename(columns={"index": "time"})
    
    labels_long["time"] = pd.to_datetime(labels_long["time"])
    full_feats_reset["time"] = pd.to_datetime(full_feats_reset["time"])
    
    data = pd.merge(full_feats_reset, labels_long, on=["time", "symbol"], how="inner")
    data = data.dropna(subset=["target"])
    data = data.fillna(0.0) 
    
    data = data.sort_values("time")
    logger.info(f"Final Dataset: {data.shape}")
    
    # 5. Split (Time-based Walk Forward setup, roughly)
    dates = data["time"].unique()
    split_idx = int(len(dates) * 0.8)
    split_date = dates[split_idx]
    
    logger.info(f"Splitting at {split_date}")
    train = data[data["time"] < split_date]
    valid = data[data["time"] >= split_date]
    
    X_train = train[feature_names]
    y_train = train["target"]
    X_valid = valid[feature_names]
    y_valid = valid["target"]
    
    # 6. Train HistGradientBoostingRegressor (Pointwise Ranking)
    # Minimizing MSE on Rank Labels (0..1) aligns with Ranking logic
    logger.info("Training HistGradientBoostingRegressor...")
    model = HistGradientBoostingRegressor(
        max_iter=100, 
        learning_rate=0.1, 
        max_leaf_nodes=31,
        early_stopping=True,
        validation_fraction=0.1,
        verbose=0,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # 7. Evaluate
    train_score = model.score(X_train, y_train)
    valid_score = model.score(X_valid, y_valid)
    logger.info(f"R2 Score: Train={train_score:.4f}, Valid={valid_score:.4f}")
    
    # 8. Save
    model_path = Path("models/ranker_model.pkl")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.success(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_ranker_model()
