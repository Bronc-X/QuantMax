from __future__ import annotations
import backtrader as bt

class ChinaAStockCommission(bt.CommInfoBase):
    params = dict(
        commission=0.0003,      # 3 bps
        stamp_duty=0.001,       # sell only
        min_commission=5.0,
    )

    def _getcommission(self, size, price, pseudoexec):
        value = abs(size) * price
        comm = max(value * self.p.commission, self.p.min_commission)
        # stamp duty on sells
        if size < 0:
            comm += value * self.p.stamp_duty
        return comm
