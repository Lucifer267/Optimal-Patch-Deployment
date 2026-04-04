"""Phase 2 algorithm benchmarking utilities."""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from modules.utils import OptimizationResult


def build_comparison_frame(
    results: Dict[str, OptimizationResult],
    capacities: Optional[Dict[str, float]] = None,
    baseline_algorithm: str = "ilp",
) -> pd.DataFrame:
    records = []
    baseline_value = results.get(baseline_algorithm).total_value if baseline_algorithm in results else None
    for algorithm, result in results.items():
        approximation_gap = None
        if baseline_value not in (None, 0):
            approximation_gap = max(0.0, (baseline_value - result.total_value) / baseline_value)
        if capacities:
            time_utilization = result.total_time / max(1e-6, capacities.get("maintenance_window_hours", 1.0))
            cost_utilization = result.total_cost / max(1e-6, capacities.get("budget", 1.0))
            manpower_utilization = result.total_manpower / max(1e-6, capacities.get("manpower", 1.0))
        else:
            time_utilization = result.total_time
            cost_utilization = result.total_cost
            manpower_utilization = result.total_manpower
        records.append(
            {
                "algorithm": algorithm,
                "selected": len(result.selected_ids),
                "risk_reduced": result.total_value,
                "runtime_seconds": result.runtime_seconds,
                "time_utilization": time_utilization,
                "cost_utilization": cost_utilization,
                "manpower_utilization": manpower_utilization,
                "feasible": result.feasible,
                "comparison_note": result.comparison_note,
                "approximation_gap": approximation_gap,
            }
        )
    frame = pd.DataFrame.from_records(records)
    if not frame.empty:
        frame["quality_score"] = frame["risk_reduced"] / frame["runtime_seconds"].replace(0, 1e-6)
    return frame


def quality_summary(comparison_frame: pd.DataFrame) -> dict:
    if comparison_frame.empty:
        return {"best_algorithm": None, "best_risk": 0.0, "fastest_algorithm": None}

    best_row = comparison_frame.sort_values(["risk_reduced", "selected"], ascending=[False, False]).iloc[0]
    fastest_row = comparison_frame.sort_values("runtime_seconds", ascending=True).iloc[0]
    return {
        "best_algorithm": str(best_row["algorithm"]),
        "best_risk": float(best_row["risk_reduced"]),
        "fastest_algorithm": str(fastest_row["algorithm"]),
        "fastest_runtime": float(fastest_row["runtime_seconds"]),
    }
