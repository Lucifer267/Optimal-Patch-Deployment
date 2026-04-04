"""Exact single-constraint dynamic programming baseline."""

from __future__ import annotations

from time import perf_counter
from typing import Dict

import pandas as pd

from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult


def dp_single_constraint(scored: pd.DataFrame, capacities: Dict[str, float]) -> OptimizationResult:
    start = perf_counter()
    items = scored.reset_index(drop=True).copy()
    capacity = int(round(capacities.get("maintenance_window_hours", 0.0) * 10))
    weights = [int(round(float(value) * 10)) for value in items["patch_time"].tolist()]
    values = [float(value) for value in items["adjusted_patch_value"].tolist()]

    dp = [0.0] * (capacity + 1)
    keep = [[False] * (capacity + 1) for _ in range(len(items))]

    for item_index, weight in enumerate(weights):
        value = values[item_index]
        for current_capacity in range(capacity, weight - 1, -1):
            candidate_value = dp[current_capacity - weight] + value
            if candidate_value > dp[current_capacity]:
                dp[current_capacity] = candidate_value
                keep[item_index][current_capacity] = True

    selected_indices: list[int] = []
    current_capacity = max(range(capacity + 1), key=lambda cap: dp[cap])
    for item_index in range(len(items) - 1, -1, -1):
        if current_capacity >= 0 and keep[item_index][current_capacity]:
            selected_indices.append(item_index)
            current_capacity -= weights[item_index]
    selected_indices.reverse()

    selected_df = items.iloc[selected_indices].copy() if selected_indices else items.iloc[0:0].copy()
    selected_ids = selected_df["patch_id"].astype(str).tolist()
    rejected_ids = [str(item) for item in items["patch_id"].tolist() if str(item) not in set(selected_ids)]
    explanations = build_explanation_map(items, selected_ids)
    total_time = float(selected_df["patch_time"].sum())
    total_cost = float(selected_df["patch_cost"].sum())
    total_manpower = float(selected_df["manpower_required"].sum())
    schedule = []
    if not selected_df.empty:
        try:
            from modules.dependency_graph import DependencyGraph
            import networkx as nx

            dummy_graph = DependencyGraph(graph=nx.DiGraph(), conflicts={})
            schedule = build_schedule(selected_df, dummy_graph, capacities.get("maintenance_window_hours", 1.0))
        except Exception:
            schedule = []

    return OptimizationResult(
        algorithm="dp_single",
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        total_value=float(selected_df["adjusted_patch_value"].sum()),
        total_time=total_time,
        total_cost=total_cost,
        total_manpower=total_manpower,
        runtime_seconds=perf_counter() - start,
        feasible=True,
        notes=["Exact baseline for single time-capacity knapsack; dependency handling is intentionally limited."],
        explanations=explanations,
        score_breakdown={"dynamic_programming": 1.0},
        schedule=schedule,
        comparison_note="Classic 0/1 knapsack baseline on patch time only.",
    )
