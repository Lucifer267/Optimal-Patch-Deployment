"""Metrics and comparison helpers."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from modules.utils import OptimizationResult


def summarize_result(scored: pd.DataFrame, result: OptimizationResult, capacities: Dict[str, float]) -> Dict[str, float]:
    selected_df = scored[scored["patch_id"].astype(str).isin(set(result.selected_ids))].copy()
    utilization = {
        "time_utilization": float(selected_df["patch_time"].sum() / max(1e-6, capacities.get("maintenance_window_hours", 1.0))),
        "cost_utilization": float(selected_df["patch_cost"].sum() / max(1e-6, capacities.get("budget", 1.0))),
        "manpower_utilization": float(selected_df["manpower_required"].sum() / max(1e-6, capacities.get("manpower", 1.0))),
    }
    summary = {
        "total_risk_reduced": float(selected_df["adjusted_patch_value"].sum()),
        "selected_patches": float(len(result.selected_ids)),
        "rejected_patches": float(len(result.rejected_ids)),
        "runtime_seconds": float(result.runtime_seconds),
        "total_cost": float(result.total_cost),
        "total_time": float(result.total_time),
        "total_manpower": float(result.total_manpower),
    }
    summary.update(utilization)
    return summary


def compare_results(results: Dict[str, OptimizationResult]) -> pd.DataFrame:
    records = []
    for algorithm, result in results.items():
        records.append(
            {
                "algorithm": algorithm,
                "selected": len(result.selected_ids),
                "risk_reduced": result.total_value,
                "time": result.total_time,
                "cost": result.total_cost,
                "manpower": result.total_manpower,
                "runtime_seconds": result.runtime_seconds,
                "feasible": result.feasible,
            }
        )
    return pd.DataFrame.from_records(records)
