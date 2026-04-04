"""Greedy heuristics for patch selection."""

from __future__ import annotations

from time import perf_counter
from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def _greedy_run(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None,
    score_column: str,
    algorithm_name: str,
) -> OptimizationResult:
    start = perf_counter()
    working = scored.sort_values(by=[score_column, "adjusted_patch_value"], ascending=[False, False]).copy()
    selected: list[str] = []
    selected_cost = 0.0
    selected_time = 0.0
    selected_manpower = 0.0

    rejected_notes: dict[str, str] = {}
    improved = True
    while improved:
        improved = False
        for _, row in working.iterrows():
            patch_id = str(row["patch_id"])
            if patch_id in selected:
                continue
            if not eligible(patch_id, selected, dependency_graph):
                rejected_notes.setdefault(patch_id, "a prerequisite patch was missing or it conflicted with an already selected patch")
                continue
            next_time = selected_time + float(row["patch_time"])
            next_cost = selected_cost + float(row["patch_cost"])
            next_manpower = selected_manpower + float(row["manpower_required"])
            if within_capacity(next_time, next_cost, next_manpower, capacities):
                selected.append(patch_id)
                selected_time = next_time
                selected_cost = next_cost
                selected_manpower = next_manpower
                improved = True

    feasible, notes = selection_is_feasible(selected, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(selected)].copy()
    explanations = build_explanation_map(scored, selected, rejected_notes)
    schedule = []
    if dependency_graph is not None:
        schedule = build_schedule(selected_df, dependency_graph, capacities.get("maintenance_window_hours", 1.0))

    total_value = float(selected_df["adjusted_patch_value"].sum())
    runtime = perf_counter() - start
    rejected = [str(item) for item in scored["patch_id"].tolist() if str(item) not in set(selected)]

    return OptimizationResult(
        algorithm=algorithm_name,
        selected_ids=selected,
        rejected_ids=rejected,
        total_value=total_value,
        total_time=selected_time,
        total_cost=selected_cost,
        total_manpower=selected_manpower,
        runtime_seconds=runtime,
        feasible=feasible,
        notes=notes,
        explanations=explanations,
        score_breakdown={"greedy_score_column": 1.0},
        schedule=schedule,
        comparison_note="Dependency-aware greedy heuristic with resource feasibility checks.",
    )


def greedy_ratio(scored: pd.DataFrame, capacities: Dict[str, float], dependency_graph: DependencyGraph | None = None) -> OptimizationResult:
    return _greedy_run(scored, capacities, dependency_graph, "value_per_time", "greedy_ratio")


def greedy_weighted(scored: pd.DataFrame, capacities: Dict[str, float], dependency_graph: DependencyGraph | None = None) -> OptimizationResult:
    return _greedy_run(scored, capacities, dependency_graph, "value_per_resource", "greedy_weighted")
