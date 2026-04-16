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
    
    # Find best feasible solution for approximation gap baseline
    feasible_results = {k: v for k, v in results.items() if v.feasible}
    baseline_value = (
        max((r.total_value for r in feasible_results.values()), default=None)
        if feasible_results else results.get(baseline_algorithm).total_value if baseline_algorithm in results else None
    )
    
    for algorithm, result in results.items():
        approximation_gap = None
        if baseline_value not in (None, 0) and baseline_value > 0:
            # Gap is negative if worse than baseline, positive if better
            approximation_gap = (result.total_value - baseline_value) / baseline_value
        
        if capacities:
            time_utilization = result.total_time / max(1e-6, capacities.get("maintenance_window_hours", 1.0))
            cost_utilization = result.total_cost / max(1e-6, capacities.get("budget", 1.0))
            manpower_utilization = result.total_manpower / max(1e-6, capacities.get("manpower", 1.0))
        else:
            time_utilization = result.total_time
            cost_utilization = result.total_cost
            manpower_utilization = result.total_manpower
        
        # Calculate constraint violations for infeasible solutions
        violations = []
        if not result.feasible and capacities:
            if result.total_time > capacities.get("maintenance_window_hours", 0):
                violations.append("Time")
            if result.total_cost > capacities.get("budget", 0):
                violations.append("Budget")
            if result.total_manpower > capacities.get("manpower", 0):
                violations.append("Manpower")
        
        records.append(
            {
                "algorithm": algorithm,
                "selected": len(result.selected_ids),
                "risk_reduced": result.total_value,
                "runtime_seconds": result.runtime_seconds,
                "time_utilization": min(time_utilization, 1.0) if result.feasible else time_utilization,
                "cost_utilization": min(cost_utilization, 1.0) if result.feasible else cost_utilization,
                "manpower_utilization": min(manpower_utilization, 1.0) if result.feasible else manpower_utilization,
                "feasible": result.feasible,
                "comparison_note": result.comparison_note,
                "approximation_gap": approximation_gap,
                "constraint_violations": ", ".join(violations) if violations else "",
                "coverage_ratio": len(result.selected_ids) / max(1, len(result.selected_ids) + len(result.rejected_ids)),
            }
        )
    
    frame = pd.DataFrame.from_records(records)
    if not frame.empty:
        # Improved quality_score: higher runtime weight for stability, clamp for numerical safety
        safe_runtime = frame["runtime_seconds"].replace(0, 0.001)
        frame["quality_score"] = frame["risk_reduced"] / (safe_runtime ** 0.8)  # Softer penalty on runtime
        frame["quality_score"] = frame["quality_score"].fillna(0).replace([float('inf'), float('-inf')], 0)
    return frame

def quality_summary(comparison_frame: pd.DataFrame) -> dict:
    """
    Generate summary of best algorithms across different metrics.
    Filters to feasible solutions for primary rankings but provides infeasible fallback.
    """
    if comparison_frame.empty:
        return {
            "best_algorithm": None,
            "best_risk": 0.0,
            "fastest_algorithm": None,
            "fastest_runtime": 0.0,
            "best_feasible_algorithm": None,
            "efficiency_leader": None,
            "most_conservative": None,
            "best_coverage": None,
            "feasibility_rate": 0.0,
        }

    # Filter to feasible solutions only for primary rankings
    feasible_frame = comparison_frame[comparison_frame["feasible"] == True]
    feasibility_rate = len(feasible_frame) / len(comparison_frame) if len(comparison_frame) > 0 else 0.0
    
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
        # Use nlargest to handle ties gracefully
        best_efficiency = feasible_frame.nlargest(1, "quality_score")
        if not best_efficiency.empty:
            efficiency_leader = str(best_efficiency.iloc[0]["algorithm"])
    else:
        best_efficiency = comparison_frame.nlargest(1, "quality_score")
        if not best_efficiency.empty:
            efficiency_leader = str(best_efficiency.iloc[0]["algorithm"])
    
    # Most conservative: lowest resource utilization among feasible solutions
    most_conservative = None
    if not feasible_frame.empty:
        feasible_frame_copy = feasible_frame.copy()
        feasible_frame_copy["avg_utilization"] = (
            feasible_frame_copy["time_utilization"] 
            + feasible_frame_copy["cost_utilization"] 
            + feasible_frame_copy["manpower_utilization"]
        ) / 3
        conservative = feasible_frame_copy.nsmallest(1, "avg_utilization")
        if not conservative.empty:
            most_conservative = str(conservative.iloc[0]["algorithm"])
    
    # Best coverage: highest number of patches selected among feasible solutions
    best_coverage = None
    if not feasible_frame.empty:
        coverage = feasible_frame.nlargest(1, "selected")
        if not coverage.empty:
            best_coverage = str(coverage.iloc[0]["algorithm"])
    
    return {
        "best_algorithm": best_algorithm,
        "best_risk": best_risk,
        "fastest_algorithm": fastest_algorithm,
        "fastest_runtime": fastest_runtime,
        "best_feasible_algorithm": best_feasible_algorithm,
        "efficiency_leader": efficiency_leader,
        "most_conservative": most_conservative,
        "best_coverage": best_coverage,
        "feasibility_rate": feasibility_rate,
    }
