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
        return {
            "best_algorithm": None,
            "best_risk": 0.0,
            "fastest_algorithm": None,
            "fastest_runtime": 0.0,
            "best_feasible_algorithm": None,
            "efficiency_leader": None,
        }

    # Filter to feasible solutions only for primary rankings
    feasible_frame = comparison_frame[comparison_frame["feasible"] == True]
    
    # Best quality: highest risk_reduced among feasible solutions
    if not feasible_frame.empty:
        best_row = feasible_frame.sort_values("risk_reduced", ascending=False).iloc[0]
        best_algorithm = str(best_row["algorithm"])
        best_risk = float(best_row["risk_reduced"])
        best_feasible_algorithm = best_algorithm
    else:
        # Fallback to any solution if no feasible ones
        best_row = comparison_frame.sort_values("risk_reduced", ascending=False).iloc[0]
        best_algorithm = str(best_row["algorithm"])
        best_risk = float(best_row["risk_reduced"])
        best_feasible_algorithm = None
    
    # Fastest solver: lowest runtime among feasible solutions
    if not feasible_frame.empty:
        fastest_row = feasible_frame.sort_values("runtime_seconds", ascending=True).iloc[0]
        fastest_algorithm = str(fastest_row["algorithm"])
        fastest_runtime = float(fastest_row["runtime_seconds"])
    else:
        fastest_row = comparison_frame.sort_values("runtime_seconds", ascending=True).iloc[0]
        fastest_algorithm = str(fastest_row["algorithm"])
        fastest_runtime = float(fastest_row["runtime_seconds"])
    
    # Efficiency leader: best quality_score (risk reduction per second) among feasible
    efficiency_leader = None
    if not feasible_frame.empty:
        efficiency_row = feasible_frame.sort_values("quality_score", ascending=False).iloc[0]
        efficiency_leader = str(efficiency_row["algorithm"])
    
    return {
        "best_algorithm": best_algorithm,
        "best_risk": best_risk,
        "fastest_algorithm": fastest_algorithm,
        "fastest_runtime": fastest_runtime,
        "best_feasible_algorithm": best_feasible_algorithm,
        "efficiency_leader": efficiency_leader,
    }
