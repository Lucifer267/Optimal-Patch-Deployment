"""Optional ILP benchmark solver using PuLP."""

from __future__ import annotations

from time import perf_counter
from typing import Dict

import pandas as pd

from modules.explainability import build_explanation_map
from modules.utils import OptimizationResult


def ilp_solve(scored: pd.DataFrame, capacities: Dict[str, float]) -> OptimizationResult:
    start = perf_counter()
    try:
        import pulp
    except Exception as exc:  # pragma: no cover - dependency fallback
        return OptimizationResult(
            algorithm="ilp",
            comparison_note=f"PuLP unavailable: {exc}",
            notes=["ILP benchmark could not run because the PuLP package is unavailable."],
            feasible=False,
        )

    items = scored.reset_index(drop=True).copy()
    model = pulp.LpProblem("PatchDeployment", pulp.LpMaximize)
    variables = [pulp.LpVariable(f"x_{index}", lowBound=0, upBound=1, cat="Binary") for index in range(len(items))]

    model += pulp.lpSum(float(items.iloc[index]["adjusted_patch_value"]) * variables[index] for index in range(len(items)))
    model += pulp.lpSum(float(items.iloc[index]["patch_time"]) * variables[index] for index in range(len(items))) <= capacities.get("maintenance_window_hours", 0.0)
    model += pulp.lpSum(float(items.iloc[index]["patch_cost"]) * variables[index] for index in range(len(items))) <= capacities.get("budget", 0.0)
    model += pulp.lpSum(float(items.iloc[index]["manpower_required"]) * variables[index] for index in range(len(items))) <= capacities.get("manpower", 0.0)

    model.solve(pulp.PULP_CBC_CMD(msg=False))
    selected_ids = [str(items.iloc[index]["patch_id"]) for index, variable in enumerate(variables) if variable.value() and variable.value() > 0.5]
    selected_df = items[items["patch_id"].astype(str).isin(set(selected_ids))].copy()
    rejected_ids = [str(item) for item in items["patch_id"].tolist() if str(item) not in set(selected_ids)]
    return OptimizationResult(
        algorithm="ilp",
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        total_value=float(selected_df["adjusted_patch_value"].sum()),
        total_time=float(selected_df["patch_time"].sum()),
        total_cost=float(selected_df["patch_cost"].sum()),
        total_manpower=float(selected_df["manpower_required"].sum()),
        runtime_seconds=perf_counter() - start,
        feasible=True,
        notes=["ILP benchmark solved using CBC through PuLP."],
        explanations=build_explanation_map(items, selected_ids),
        score_breakdown={"ilp": 1.0},
        comparison_note="Integer programming benchmark for exact multi-constraint optimization.",
    )
