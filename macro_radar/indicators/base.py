from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

ALLOWED_ZONES = {
    "Risk-On",
    "Neutral",
    "Risk-Off",
    "Insufficient Data",
    "Not Implemented",
}


@dataclass
class IndicatorResult:
    key: str
    name: str
    status: str
    latest_date: pd.Timestamp | None
    latest_value: float | None
    zone: str
    explanation: str
    dataframe: pd.DataFrame | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.zone not in ALLOWED_ZONES:
            allowed = ", ".join(sorted(ALLOWED_ZONES))
            raise ValueError(f"Invalid indicator zone {self.zone!r}. Allowed zones: {allowed}")

