"""SLA urgency and breach estimation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.utils import clamp


def sla_urgency(days_open: float, sla_deadline_days: float) -> float:
    deadline = max(1.0, float(sla_deadline_days))
    age = max(0.0, float(days_open))
    days_remaining = deadline - age
    if days_remaining <= 0:
        breach_depth = min(1.0, abs(days_remaining) / deadline)
        return clamp(1.0 + breach_depth * 0.5, 0.0, 1.5)
    urgency = 1.0 - np.exp(-age / max(1.0, deadline / 3.0))
    return clamp(float(urgency), 0.0, 1.0)


def sla_status(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    result["sla_urgency_component"] = result.apply(
        lambda row: sla_urgency(row["days_open"], row["sla_deadline_days"]), axis=1
    )
    result["days_remaining_to_sla"] = result["sla_deadline_days"] - result["days_open"]
    result["sla_breached"] = result["days_remaining_to_sla"] <= 0
    result["sla_state"] = result["days_remaining_to_sla"].apply(
        lambda remaining: "Breached" if remaining <= 0 else ("Critical" if remaining <= 3 else "Safe")
    )
    return result
