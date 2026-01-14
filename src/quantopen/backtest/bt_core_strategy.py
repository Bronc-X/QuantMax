from __future__ import annotations

import backtrader as bt
import pandas as pd
from loguru import logger

from quantopen.strategy.api import StrategyConfig, MarketState, AccountState, CoreStrategy


class CoreStrategyBT(bt.Strategy):
    params = dict(
        cfg=StrategyConfig(),
        core=None,  # CoreStrategy instance
        hotlist_csv=None,   # data/raw/hotlist.csv  (date,symbol,rank)
        themes_csv=None,    # configs/themes.csv or data/raw/themes.csv (symbol,theme_boost)
    )

    def __init__(self):
        if self.p.core is None:
            raise ValueError("CoreStrategyBT requires a core strategy instance")

        self.core: CoreStrategy = self.p.core
        self.cfg: StrategyConfig = self.p.cfg

        self._last_rebalance_dt: pd.Timestamp | None = None
        self._peak_equity: float = float(self.broker.getvalue())
        
        # Track entry time for hold_minutes timeout
        self._entry_times: dict[str, pd.Timestamp] = {}

        self.hot_df = self._load_hot(self.p.hotlist_csv) if self.p.hotlist_csv else None
        self.theme_df = self._load_themes(self.p.themes_csv) if self.p.themes_csv else None

    def _load_hot(self, path: str):
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["symbol"] = df["symbol"].astype(str).str.zfill(6)
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
        df = df.dropna(subset=["rank"])
        # index by (date, symbol)
        return df.set_index(["date", "symbol"]).sort_index()

    def _load_themes(self, path: str):
        df = pd.read_csv(path)
        df["symbol"] = df["symbol"].astype(str).str.zfill(6)
        if "theme_boost" not in df.columns:
            df["theme_boost"] = 0.0
        df["theme_boost"] = pd.to_numeric(df["theme_boost"], errors="coerce").fillna(0.0)
        return df.set_index("symbol").sort_index()

    def _now_dt(self) -> pd.Timestamp:
        # Use first data as clock
        dt = self.datas[0].datetime.datetime(0)
        return pd.Timestamp(dt)

    def _should_rebalance(self, now: pd.Timestamp) -> bool:
        if self._last_rebalance_dt is None:
            return True
        delta_min = (now - self._last_rebalance_dt).total_seconds() / 60.0
        return delta_min >= self.cfg.rebalance_every_n_minutes

    def _check_hold_timeout(self, now: pd.Timestamp) -> list[str]:
        """
        Check which positions have exceeded hold_minutes and should be closed.
        Returns list of symbols to force-close.
        """
        timeout_syms = []
        for sym, entry_dt in list(self._entry_times.items()):
            held_minutes = (now - entry_dt).total_seconds() / 60.0
            if held_minutes >= self.cfg.hold_minutes:
                timeout_syms.append(sym)
        return timeout_syms

    def _build_features_snapshot(self, now: pd.Timestamp) -> pd.DataFrame:
        """
        Build a per-symbol snapshot from Backtrader data lines.
        Minimal set: close, prev_close, amount, ret_1
        You can expand this later (rolling windows etc.) or replace with precomputed features.
        """
        rows = []
        for d in self.datas:
            sym = d._name
            if len(d) < 2:
                continue
            close = float(d.close[0])
            prev_close = float(d.close[-1])
            amount = float(getattr(d, "amount")[0]) if hasattr(d, "amount") else 0.0
            ret_1 = close / prev_close - 1.0 if prev_close != 0 else 0.0
            rows.append((sym, close, prev_close, amount, ret_1))
        if not rows:
            return pd.DataFrame(index=pd.Index([], name="symbol"))
        df = pd.DataFrame(rows, columns=["symbol", "close", "prev_close", "amount", "ret_1"]).set_index("symbol")
        return df

    def _get_hot_for_day(self, now: pd.Timestamp) -> pd.DataFrame | None:
        if self.hot_df is None:
            return None
        day = now.date()
        # extract that day rows: index (date,symbol)
        try:
            sub = self.hot_df.loc[day]
        except KeyError:
            return None
        # sub index is symbol
        sub = sub.copy()
        if isinstance(sub, pd.Series):
            sub = sub.to_frame().T
        sub.index = sub.index.astype(str).str.zfill(6)
        return sub[["rank"]]

    def _get_theme(self) -> pd.DataFrame | None:
        return self.theme_df

    def next(self):
        now = self._now_dt()

        # update peak equity/drawdown
        eq = float(self.broker.getvalue())
        self._peak_equity = max(self._peak_equity, eq)
        dd = 0.0 if self._peak_equity <= 0 else (self._peak_equity - eq) / self._peak_equity

        # 1) Check hold_minutes timeout - force close expired positions
        timeout_syms = self._check_hold_timeout(now)
        for d in self.datas:
            sym = d._name
            if sym in timeout_syms:
                pos = self.getposition(d).size
                if pos != 0:
                    self.order_target_percent(data=d, target=0.0)
                    logger.debug(f"[{now}] TIMEOUT: {sym} held > {self.cfg.hold_minutes}min, closing")
                if sym in self._entry_times:
                    del self._entry_times[sym]

        if not self._should_rebalance(now):
            return

        self._last_rebalance_dt = now
        features = self._build_features_snapshot(now)
        if features.empty:
            return

        hot = self._get_hot_for_day(now)
        themes = self._get_theme()
        market = MarketState(dt=now)
        account = AccountState(equity=eq, peak_equity=self._peak_equity, drawdown=dd)

        # 2) alpha score
        scores = self.core.alpha_score(now, features, hot, themes, market)

        # 3) filter + select (pass cfg for parameterized thresholds)
        selected = self.core.filter_and_select(now, scores, features, hot, themes, market)

        # 4) target weights with risk control
        targets = self.core.build_target_weights(now, selected, account, self.cfg)

        # Apply to broker
        # First, close positions not in targets
        target_syms = set(targets.keys())
        for d in self.datas:
            sym = d._name
            pos = self.getposition(d).size
            if pos != 0 and sym not in target_syms:
                self.order_target_percent(data=d, target=0.0)
                if sym in self._entry_times:
                    del self._entry_times[sym]

        # Then, set target weights and track entry times
        for d in self.datas:
            sym = d._name
            if sym in targets:
                current_pos = self.getposition(d).size
                self.order_target_percent(data=d, target=float(targets[sym]))
                # Track new entries
                if current_pos == 0 and targets[sym] > 0:
                    self._entry_times[sym] = now

        logger.info(
            f"[{now}] eq={eq:.2f} dd={dd:.2%} selected={len(targets)} "
            f"top={list(targets.items())[:3]}"
        )
