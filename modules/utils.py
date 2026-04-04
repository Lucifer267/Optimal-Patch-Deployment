"""Utility helpers and shared data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return float(max(lower, min(upper, value)))


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_bool(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    text = str(value).strip().lower()
    return int(text in {"1", "true", "yes", "y", "on"})


def parse_list_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return []
    if not text:
        return []
    text = text.strip("[]")
    for separator in ["|", ";", ","]:
        if separator in text:
            return [part.strip() for part in text.split(separator) if part.strip()]
    return [text]


def normalize_series(series: pd.Series, lower: float | None = None, upper: float | None = None) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if lower is None:
        lower = float(numeric.min()) if len(numeric) else 0.0
    if upper is None:
        upper = float(numeric.max()) if len(numeric) else 1.0
    if upper <= lower:
        return pd.Series(np.zeros(len(numeric)), index=series.index)
    return (numeric - lower) / (upper - lower)


def weighted_average(values: Dict[str, float], weights: Dict[str, float]) -> float:
    return float(sum(values.get(name, 0.0) * weight for name, weight in weights.items()))


@dataclass
class OptimizationResult:
    algorithm: str
    selected_ids: List[str] = field(default_factory=list)
    rejected_ids: List[str] = field(default_factory=list)
    total_value: float = 0.0
    total_time: float = 0.0
    total_cost: float = 0.0
    total_manpower: float = 0.0
    runtime_seconds: float = 0.0
    feasible: bool = True
    notes: List[str] = field(default_factory=list)
    explanations: Dict[str, str] = field(default_factory=dict)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    schedule: List[Dict[str, Any]] = field(default_factory=list)
    comparison_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "selected_ids": list(self.selected_ids),
            "rejected_ids": list(self.rejected_ids),
            "total_value": self.total_value,
            "total_time": self.total_time,
            "total_cost": self.total_cost,
            "total_manpower": self.total_manpower,
            "runtime_seconds": self.runtime_seconds,
            "feasible": self.feasible,
            "notes": list(self.notes),
            "explanations": dict(self.explanations),
            "score_breakdown": dict(self.score_breakdown),
            "schedule": list(self.schedule),
            "comparison_note": self.comparison_note,
        }
