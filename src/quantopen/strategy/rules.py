from __future__ import annotations
import pandas as pd


def approx_limit_up_mask(features: pd.DataFrame, threshold: float) -> pd.Series:
    """
    近似涨停过滤：用 close 与 prev_close 估计涨幅。
    需要 features 里有 close 和 prev_close（如果没有就退化不拦）。
    """
    if "close" not in features.columns or "prev_close" not in features.columns:
        return pd.Series(False, index=features.index)
    pct = (features["close"] / features["prev_close"] - 1.0)
    return pct >= threshold


def liquidity_mask(features: pd.DataFrame, min_amount_1m: float) -> pd.Series:
    if "amount" not in features.columns:
        # 没有amount就不筛
        return pd.Series(True, index=features.index)
    return features["amount"].fillna(0.0) >= float(min_amount_1m)


def hot_rank_mask(hot: pd.DataFrame | None, hot_topn: int, universe_index: pd.Index) -> pd.Series:
    """
    hot: index=symbol, column rank(1=最热)
    """
    if hot is None or hot.empty or "rank" not in hot.columns:
        return pd.Series(True, index=universe_index)
    rank = hot["rank"].reindex(universe_index)
    return rank.notna() & (rank <= hot_topn)
