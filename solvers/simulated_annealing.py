"""Simulated Annealing solver for patch selection with probabilistic moves."""

from __future__ import annotations

from time import perf_counter
import random
import math
from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def simulated_annealing(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    initial_temp: float = 100.0,
    cooling_rate: float = 0.95,
    iterations_per_temp: int = 50,
) -> OptimizationResult:
    """Simulated Annealing: Probabilistic local search that accepts worse solutions to escape local optima.
    
    Temperature gradually decreases to focus search on promising regions.
    """
    start = perf_counter()
    patch_ids = scored["patch_id"].astype(str).tolist()
    lookup_value = scored.set_index("patch_id")["adjusted_patch_value"].to_dict()
    lookup_time = scored.set_index("patch_id")["patch_time"].to_dict()
    lookup_cost = scored.set_index("patch_id")["patch_cost"].to_dict()
    lookup_manpower = scored.set_index("patch_id")["manpower_required"].to_dict()
    
    # Initialize with greedy solution
    current_solution: list[str] = []
    current_value = 0.0
    best_solution = current_solution.copy()
    best_value = 0.0
    
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
    temperature = initial_temp
    
    # Annealing loop
    total_iterations = 0
    while temperature > 0.01:
        for _ in range(iterations_per_temp):
            # Generate neighbor by adding or removing a patch
            if random.random() < 0.5 and len(current_solution) > 0:
                # Try removing
                patch_to_remove = random.choice(current_solution)
                neighbor_solution = [p for p in current_solution if p != patch_to_remove]
                neighbor_value = current_value - lookup_value[patch_to_remove]
            else:
                # Try adding
                candidates = [p for p in patch_ids if p not in current_solution]
                if not candidates:
                    continue
                patch_to_add = random.choice(candidates)
                
                if not eligible(patch_to_add, current_solution, dependency_graph):
                    continue
                
                total_time = sum(lookup_time.get(p, 0) for p in current_solution) + lookup_time[patch_to_add]
                total_cost = sum(lookup_cost.get(p, 0) for p in current_solution) + lookup_cost[patch_to_add]
                total_manpower = sum(lookup_manpower.get(p, 0) for p in current_solution) + lookup_manpower[patch_to_add]
                
                if not within_capacity(total_time, total_cost, total_manpower, capacities):
                    continue
                
                neighbor_solution = current_solution + [patch_to_add]
                neighbor_value = current_value + lookup_value[patch_to_add]
            
            # Metropolis acceptance criterion
            delta = neighbor_value - current_value
            if delta > 0 or random.random() < math.exp(delta / (temperature + 1e-10)):
                current_solution = neighbor_solution
                current_value = neighbor_value
            
            if current_value > best_value:
                best_value = current_value
                best_solution = current_solution.copy()
            
            total_iterations += 1
        
        temperature *= cooling_rate
    
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by simulated annealing." for patch_id in rejected}
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
        algorithm="simulated_annealing",
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
        score_breakdown={"initial_temp": initial_temp, "cooling_rate": cooling_rate, "iterations": total_iterations},
        schedule=schedule,
        comparison_note=f"Simulated Annealing with probabilistic moves (T={initial_temp}, rate={cooling_rate}).",
    )
