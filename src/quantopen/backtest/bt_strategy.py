from __future__ import annotations
import backtrader as bt

class HoldNMinutes(bt.Strategy):
    params = dict(
        hold_minutes=60,
        target_percent=0.1,  # per symbol target
        max_positions=5,
    )

    def __init__(self):
        self.entry_bar = {}  # data -> bar index at entry

    def next(self):
        # basic: if positions < max, buy first symbols that have data and no position
        # sell after hold_minutes bars
        for d in self.datas:
            pos = self.getposition(d).size
            if pos != 0:
                # check holding time
                if d in self.entry_bar:
                    held = len(d) - self.entry_bar[d]
                    if held >= self.p.hold_minutes:
                        self.close(data=d)
                continue

        # open new positions if room
        current_positions = sum(1 for d in self.datas if self.getposition(d).size != 0)
        room = self.p.max_positions - current_positions
        if room <= 0:
            return

        # naive pick: just take earliest datas without position
        for d in self.datas:
            if room <= 0:
                break
            if self.getposition(d).size == 0:
                self.order_target_percent(data=d, target=self.p.target_percent)
                self.entry_bar[d] = len(d)
                room -= 1
