from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "source_registry.yaml"


def load_source_registry(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    registry_path = Path(path) if path is not None else SOURCE_REGISTRY_PATH
    with registry_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return data

