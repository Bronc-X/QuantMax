from quantopen.strategy.api import CoreStrategy, MarketState, AccountState, StrategyConfig
from quantopen.strategy import rules, portfolio
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

class MLCoreStrategy(CoreStrategy):
    """
    Core Strategy Implementation using 'Learning to Rank'.
    Predictions: Cross-Sectional Rank of future N-min return.
    """
    def __init__(self, model_path="models/ranker_model.pkl"):
        # Load Scikit-Learn model
        p = Path(model_path)
        if not p.exists():
            raise FileNotFoundError(f"Model not found at {p}. Run 'script/train_model.py' first.")
        self.model = joblib.load(p)
        
    def alpha_score(self, dt, features, hot, themes, market) -> pd.Series:
        # features: DataFrame with keys ["open", ..., "vol_5", "ret_30", ...]
        
        if features.empty:
            return pd.Series(dtype=float)

        # Align columns to model's expected features
        # Scikit-learn models store feature names
        if hasattr(self.model, "feature_names_in_"):
            needed_cols = self.model.feature_names_in_
        else:
            # Fallback if attribute missing (older sklearn or wrapper)
            # Assume features match provided df columns excluding metadata
            needed_cols = [c for c in features.columns if c not in ["symbol", "date", "time"]]

        # Using reindex to ensure columns exist (creates NaN if missing)
        X = features.reindex(columns=needed_cols)
        # Handle NaNs (HistGradientBoosting can handle them, but safer to fill 0 if critical)
        X = X.fillna(0.0) 
        
        try:
            scores = self.model.predict(X)
            # scores is array of predicted rank/return
            return pd.Series(scores, index=features.index)
        except Exception as e:
            return pd.Series(0.0, index=features.index)

    def filter_and_select(self, dt, scores, features, hot, themes, market) -> pd.Series:
        # Standard logic: Limit Up filter, Liquidity filter
        idx = features.index
        limit_mask = ~rules.approx_limit_up_mask(features)
        liq_mask = rules.liquidity_mask(features)
        
        mask = limit_mask & liq_mask
        valid_scores = scores[mask].dropna()
        
        # Sort descending (Higher Score = Better Rank/Return)
        return valid_scores.sort_values(ascending=False)

    def build_target_weights(self, dt, selected, account, cfg) -> dict:
        # Standard portfolio: TopK Equal Weight
        return portfolio.topk_equal_weight(selected, cfg)
