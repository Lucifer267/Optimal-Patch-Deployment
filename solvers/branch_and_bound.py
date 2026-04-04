"""Branch and bound solver with resource pruning."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


@dataclass
class _SearchState:
    selected: list[str]
    time: float
    cost: float
    manpower: float
    value: float


def _bound(items: pd.DataFrame, start_index: int, remaining_time: float, remaining_cost: float, remaining_manpower: float) -> float:
    bound_value = 0.0
    for _, row in items.iloc[start_index:].iterrows():
        if remaining_time <= 0 or remaining_cost <= 0 or remaining_manpower <= 0:
            break
        ratio = float(row["adjusted_patch_value"]) / max(0.0001, float(row["patch_time"]) + float(row["patch_cost"]) / 10000.0 + float(row["manpower_required"]))
        bound_value += ratio * min(remaining_time, float(row["patch_time"]))
        remaining_time -= float(row["patch_time"])
        remaining_cost -= float(row["patch_cost"])
        remaining_manpower -= float(row["manpower_required"])
    return bound_value


def branch_and_bound(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
) -> OptimizationResult:
    start = perf_counter()
    items = scored.sort_values(by="value_per_resource", ascending=False).reset_index(drop=True)
    best_state = _SearchState(selected=[], time=0.0, cost=0.0, manpower=0.0, value=0.0)

    def search(index: int, state: _SearchState) -> None:
        nonlocal best_state
        if index >= len(items):
            if state.value > best_state.value:
                best_state = _SearchState(state.selected.copy(), state.time, state.cost, state.manpower, state.value)
            return

        upper = state.value + _bound(
            items,
            index,
            capacities.get("maintenance_window_hours", 0.0) - state.time,
            capacities.get("budget", 0.0) - state.cost,
            capacities.get("manpower", 0.0) - state.manpower,
        )
        if upper <= best_state.value:
            return

        row = items.iloc[index]
        patch_id = str(row["patch_id"])

        if eligible(patch_id, state.selected, dependency_graph):
            next_time = state.time + float(row["patch_time"])
            next_cost = state.cost + float(row["patch_cost"])
            next_manpower = state.manpower + float(row["manpower_required"])
            if within_capacity(next_time, next_cost, next_manpower, capacities):
                state.selected.append(patch_id)
                search(
                    index + 1,
                    _SearchState(
                        selected=state.selected,
                        time=next_time,
                        cost=next_cost,
                        manpower=next_manpower,
                        value=state.value + float(row["adjusted_patch_value"]),
                    ),
                )
                state.selected.pop()

        search(index + 1, state)

    search(0, _SearchState(selected=[], time=0.0, cost=0.0, manpower=0.0, value=0.0))
    selected_df = scored[scored["patch_id"].astype(str).isin(set(best_state.selected))].copy()
    explanations = build_explanation_map(scored, best_state.selected)
    feasible, notes = selection_is_feasible(best_state.selected, dependency_graph)
    schedule = []
    if dependency_graph is not None and not selected_df.empty:
        schedule = build_schedule(selected_df, dependency_graph, capacities.get("maintenance_window_hours", 1.0))
    rejected = [str(item) for item in scored["patch_id"].tolist() if str(item) not in set(best_state.selected)]
    return OptimizationResult(
        algorithm="branch_bound",
        selected_ids=best_state.selected,
        rejected_ids=rejected,
        total_value=best_state.value,
        total_time=float(selected_df["patch_time"].sum()),
        total_cost=float(selected_df["patch_cost"].sum()),
        total_manpower=float(selected_df["manpower_required"].sum()),
        runtime_seconds=perf_counter() - start,
        feasible=feasible,
        notes=notes,
        explanations=explanations,
        score_breakdown={"branch_and_bound": 1.0},
        schedule=schedule,
        comparison_note="Exact search with pruning using a fractional upper bound.",
    )
