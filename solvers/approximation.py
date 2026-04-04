"""FPTAS for the classic 0/1 knapsack reduction."""

from __future__ import annotations

from math import floor
from time import perf_counter
from typing import Dict

import pandas as pd

from modules.explainability import build_explanation_map
from modules.utils import OptimizationResult


def fptas_knapsack(scored: pd.DataFrame, capacities: Dict[str, float], epsilon: float = 0.2) -> OptimizationResult:
    start = perf_counter()
    items = scored.reset_index(drop=True).copy()
    capacity = int(round(capacities.get("maintenance_window_hours", 0.0) * 10))
    values = items["adjusted_patch_value"].tolist()
    weights = [int(round(float(value) * 10)) for value in items["patch_time"].tolist()]
    if not values:
        return OptimizationResult(algorithm="fptas", comparison_note="Empty input.")
    max_value = max(values)
    scale = epsilon * max_value / max(1, len(values))
    scaled_values = [int(floor(value / max(scale, 1e-9))) for value in values]
    sum_scaled = sum(scaled_values)
    dp = [float("inf")] * (sum_scaled + 1)
    dp[0] = 0
    parent = [[False] * (sum_scaled + 1) for _ in range(len(items))]

    for item_index, (scaled_value, weight) in enumerate(zip(scaled_values, weights)):
        for current_value in range(sum_scaled, scaled_value - 1, -1):
            candidate_weight = dp[current_value - scaled_value] + weight
            if candidate_weight < dp[current_value]:
                dp[current_value] = candidate_weight
                parent[item_index][current_value] = True

    best_scaled_value = max((index for index, total_weight in enumerate(dp) if total_weight <= capacity), default=0)
    selected_indices: list[int] = []
    current_value = best_scaled_value
    for item_index in range(len(items) - 1, -1, -1):
        if current_value >= 0 and parent[item_index][current_value]:
            selected_indices.append(item_index)
            current_value -= scaled_values[item_index]
    selected_indices.reverse()

    selected_df = items.iloc[selected_indices].copy() if selected_indices else items.iloc[0:0].copy()
    selected_ids = selected_df["patch_id"].astype(str).tolist()
    rejected_ids = [str(item) for item in items["patch_id"].tolist() if str(item) not in set(selected_ids)]
    return OptimizationResult(
        algorithm="fptas",
        selected_ids=selected_ids,
        rejected_ids=rejected_ids,
        total_value=float(selected_df["adjusted_patch_value"].sum()),
        total_time=float(selected_df["patch_time"].sum()),
        total_cost=float(selected_df["patch_cost"].sum()),
        total_manpower=float(selected_df["manpower_required"].sum()),
        runtime_seconds=perf_counter() - start,
        feasible=True,
        notes=[f"Approximation with epsilon={epsilon:.2f} for the single-constraint time knapsack."],
        explanations=build_explanation_map(items, selected_ids),
        score_breakdown={"fptas": 1.0},
        comparison_note="Polynomial-time approximation for the classic single-constraint case.",
    )
