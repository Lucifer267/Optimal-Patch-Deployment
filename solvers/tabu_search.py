"""Tabu Search solver for patch selection with memory-based local search."""

from __future__ import annotations

from time import perf_counter
from typing import Dict, Set
import random

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def tabu_search(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    max_iterations: int = 500,
    tabu_tenure: int = 50,
) -> OptimizationResult:
    """Tabu Search: Uses memory to avoid revisiting recent solutions.
    
    Maintains a tabu list of recently moved patches to escape local optima.
    Explores neighborhood by adding/removing patches and keeps the best solution found.
    """
    start = perf_counter()
    patch_ids = scored["patch_id"].astype(str).tolist()
    lookup_value = scored.set_index("patch_id")["adjusted_patch_value"].to_dict()
    lookup_time = scored.set_index("patch_id")["patch_time"].to_dict()
    lookup_cost = scored.set_index("patch_id")["patch_cost"].to_dict()
    lookup_manpower = scored.set_index("patch_id")["manpower_required"].to_dict()
    
    # Initialize with empty or greedy solution
    current_solution: list[str] = []
    current_value = 0.0
    best_solution = current_solution.copy()
    best_value = 0.0
    tabu_list: Set[str] = set()
    
    # Try to build a greedy initial solution
    working = scored.sort_values("adjusted_patch_value", ascending=False).copy()
    current_time, current_cost, current_manpower = 0.0, 0.0, 0.0
    
    for _, row in working.iterrows():
        patch_id = str(row["patch_id"])
        if not eligible(patch_id, current_solution, dependency_graph):
            continue
        next_time = current_time + float(row["patch_time"])
        next_cost = current_cost + float(row["patch_cost"])
        next_manpower = current_manpower + float(row["manpower_required"])
        if within_capacity(next_time, next_cost, next_manpower, capacities):
            current_solution.append(patch_id)
            current_value += lookup_value[patch_id]
            current_time = next_time
            current_cost = next_cost
            current_manpower = next_manpower
    
    best_solution = current_solution.copy()
    best_value = current_value
    
    # Tabu search iterations
    for iteration in range(max_iterations):
        candidates = []
        
        # Generate neighborhood: try adding or removing patches
        for patch_id in patch_ids:
            if patch_id not in current_solution:
                if patch_id not in tabu_list or current_value + lookup_value[patch_id] > best_value:
                    # Try adding
                    total_time = sum(lookup_time[p] for p in current_solution) + lookup_time[patch_id]
                    total_cost = sum(lookup_cost[p] for p in current_solution) + lookup_cost[patch_id]
                    total_manpower = sum(lookup_manpower[p] for p in current_solution) + lookup_manpower[patch_id]
                    
                    if within_capacity(total_time, total_cost, total_manpower, capacities):
                        if eligible(patch_id, current_solution, dependency_graph):
                            new_value = current_value + lookup_value[patch_id]
                            candidates.append(("add", patch_id, new_value, total_time, total_cost, total_manpower))
        
        for patch_id in current_solution:
            if patch_id not in tabu_list:
                # Try removing
                new_value = current_value - lookup_value[patch_id]
                total_time = sum(lookup_time[p] for p in current_solution if p != patch_id)
                total_cost = sum(lookup_cost[p] for p in current_solution if p != patch_id)
                total_manpower = sum(lookup_manpower[p] for p in current_solution if p != patch_id)
                candidates.append(("remove", patch_id, new_value, total_time, total_cost, total_manpower))
        
        if not candidates:
            break
        
        # Select best candidate
        candidates.sort(key=lambda x: x[2], reverse=True)
        action, patch_id, new_value, total_time, total_cost, total_manpower = candidates[0]
        
        if action == "add":
            current_solution.append(patch_id)
            current_value = new_value
        else:
            current_solution.remove(patch_id)
            current_value = new_value
        
        # Update tabu list
        tabu_list.add(patch_id)
        if len(tabu_list) > tabu_tenure:
            tabu_list.pop()
        
        # Update best if improved
        if current_value > best_value:
            best_value = current_value
            best_solution = current_solution.copy()
    
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by tabu search." for patch_id in rejected}
    explanations = build_explanation_map(scored, best_solution, rejected_notes)
    schedule = []
    if dependency_graph is not None:
        schedule = build_schedule(selected_df, dependency_graph, capacities.get("maintenance_window_hours", 1.0))
    
    total_value = float(selected_df["adjusted_patch_value"].sum()) if len(selected_df) > 0 else 0.0
    runtime = perf_counter() - start
    
    total_time = sum(lookup_time.get(p, 0) for p in best_solution)
    total_cost = sum(lookup_cost.get(p, 0) for p in best_solution)
    total_manpower = sum(lookup_manpower.get(p, 0) for p in best_solution)
    
    return OptimizationResult(
        algorithm="tabu_search",
        selected_ids=best_solution,
        rejected_ids=rejected,
        total_value=total_value,
        total_time=total_time,
        total_cost=total_cost,
        total_manpower=total_manpower,
        runtime_seconds=runtime,
        feasible=feasible,
        notes=notes,
        explanations=explanations,
        score_breakdown={"tabu_iterations": iteration + 1, "tabu_tenure": tabu_tenure},
        schedule=schedule,
        comparison_note=f"Tabu Search with memory-based local search ({iteration + 1} iterations, tenure={tabu_tenure}).",
    )
