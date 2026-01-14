from __future__ import annotations
import importlib
from typing import Any

from quantopen.strategy.api import CoreStrategy


def load_core_strategy(dotted: str) -> CoreStrategy:
    """
    dotted example:
      "quant_core.core_strategy:MyCoreStrategy"
    """
    mod_name, cls_name = dotted.split(":")
    mod = importlib.import_module(mod_name)
    cls: Any = getattr(mod, cls_name)
    obj = cls()
    if not isinstance(obj, CoreStrategy):
        raise TypeError(f"{dotted} is not a CoreStrategy")
    return obj
