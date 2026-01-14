from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass
class DataConfig:
    provider: str
    bars_dir: str
    start_date: str
    end_date: str
    symbols: list[str]

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_data_config(path: Path) -> DataConfig:
    d = load_yaml(path)
    return DataConfig(
        provider=d["provider"],
        bars_dir=d["bars_dir"],
        start_date=d["start_date"],
        end_date=d["end_date"],
        symbols=list(d["symbols"]),
    )
