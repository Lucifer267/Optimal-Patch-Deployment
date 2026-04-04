"""Phase 2 multi-resource helpers and solver utilities."""

from __future__ import annotations

from time import perf_counter
from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def resource_signature(row: pd.Series, capacities: Dict[str, float]) -> float:
    normalized_time = float(row["patch_time"]) / max(1e-6, capacities.get("maintenance_window_hours", 1.0))
    normalized_cost = float(row["patch_cost"]) / max(1e-6, capacities.get("budget", 1.0))
    normalized_manpower = float(row["manpower_required"]) / max(1e-6, capacities.get("manpower", 1.0))
    return normalized_time + normalized_cost + normalized_manpower


def multi_resource_ratio(row: pd.Series, capacities: Dict[str, float]) -> float:
    footprint = max(1e-6, resource_signature(row, capacities))
    return float(row["adjusted_patch_value"]) / footprint


def multi_resource_greedy(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
) -> OptimizationResult:
    start = perf_counter()
    working = scored.copy()
    working["multi_resource_ratio"] = working.apply(lambda row: multi_resource_ratio(row, capacities), axis=1)
    working = working.sort_values(by=["multi_resource_ratio", "priority_score"], ascending=[False, False])

    selected: list[str] = []
    selected_time = 0.0
    selected_cost = 0.0
    selected_manpower = 0.0
    rejection_notes: dict[str, str] = {}

    for _, row in working.iterrows():
        patch_id = str(row["patch_id"])
        if not eligible(patch_id, selected, dependency_graph):
            rejection_notes.setdefault(patch_id, "dependency or conflict constraint blocked the patch")
            continue

        next_time = selected_time + float(row["patch_time"])
        next_cost = selected_cost + float(row["patch_cost"])
        next_manpower = selected_manpower + float(row["manpower_required"])
        if within_capacity(next_time, next_cost, next_manpower, capacities):
            selected.append(patch_id)
            selected_time = next_time
            selected_cost = next_cost
            selected_manpower = next_manpower
        else:
            rejection_notes.setdefault(patch_id, "multi-dimensional resource footprint exceeded the available capacity")

    feasible, notes = selection_is_feasible(selected, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(set(selected))].copy()
    rejected = [str(item) for item in scored["patch_id"].tolist() if str(item) not in set(selected)]
    schedule = []
    if dependency_graph is not None and not selected_df.empty:
        schedule = build_schedule(selected_df, dependency_graph, capacities.get("maintenance_window_hours", 1.0))

    return OptimizationResult(
        algorithm="multi_resource_greedy",
        selected_ids=selected,
        rejected_ids=rejected,
        total_value=float(selected_df["adjusted_patch_value"].sum()),
        total_time=selected_time,
        total_cost=selected_cost,
        total_manpower=selected_manpower,
        runtime_seconds=perf_counter() - start,
        feasible=feasible,
        notes=notes,
        explanations=build_explanation_map(scored, selected, rejection_notes),
        score_breakdown={"multi_resource_ratio": 1.0},
        schedule=schedule,
        comparison_note="Phase 2 greedy solver using a normalized multi-resource footprint.",
    )


def bounded_search_score(row: pd.Series, capacities: Dict[str, float]) -> float:
    footprint = resource_signature(row, capacities)
    risk_gain = float(row["adjusted_patch_value"])
    urgency_boost = 0.15 * float(row.get("sla_urgency_component", 0.0))
    return (risk_gain + urgency_boost) / max(1e-6, footprint)
