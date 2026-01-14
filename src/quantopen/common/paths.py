from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def bars_1m_dir(self) -> Path:
        return self.root / "data" / "bars_1m"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

def get_paths() -> ProjectPaths:
    # assumes running from repo root
    return ProjectPaths(root=Path.cwd())
