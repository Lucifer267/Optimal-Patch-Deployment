"""Local Search (Hill Climbing) solver for patch selection."""

from __future__ import annotations

from time import perf_counter
import random
from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def local_search(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    max_no_improve: int = 100,
    random_restarts: int = 5,
) -> OptimizationResult:
    """Local Search (Hill Climbing): Greedy local search with restarts for exploration.
    
    Repeatedly makes locally optimal moves until reaching a local maximum.
    Random restarts help escape local optima.
    """
    start = perf_counter()
    patch_ids = scored["patch_id"].astype(str).tolist()
    lookup_value = scored.set_index("patch_id")["adjusted_patch_value"].to_dict()
    lookup_time = scored.set_index("patch_id")["patch_time"].to_dict()
    lookup_cost = scored.set_index("patch_id")["patch_cost"].to_dict()
    lookup_manpower = scored.set_index("patch_id")["manpower_required"].to_dict()
    
    best_solution: list[str] = []
    best_value = 0.0
    
    for restart in range(random_restarts):
        # Random starting solution
        if restart == 0:
            # First restart: use greedy initialization
            working = scored.sort_values("adjusted_patch_value", ascending=False).copy()
            current_solution: list[str] = []
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
                    current_time = next_time
                    current_cost = next_cost
                    current_manpower = next_manpower
        else:
            # Other restarts: random solution
            current_solution = []
            shuffled = patch_ids.copy()
            random.shuffle(shuffled)
            current_time, current_cost, current_manpower = 0.0, 0.0, 0.0
            
            for patch_id in shuffled:
                if eligible(patch_id, current_solution, dependency_graph):
                    next_time = current_time + lookup_time.get(patch_id, 0)
                    next_cost = current_cost + lookup_cost.get(patch_id, 0)
                    next_manpower = current_manpower + lookup_manpower.get(patch_id, 0)
                    if within_capacity(next_time, next_cost, next_manpower, capacities) and random.random() < 0.7:
                        current_solution.append(patch_id)
                        current_time = next_time
                        current_cost = next_cost
                        current_manpower = next_manpower
        
        current_value = sum(lookup_value.get(p, 0) for p in current_solution)
        no_improve_count = 0
        
        # Hill climbing loop
        while no_improve_count < max_no_improve:
            improved = False
            
            # Try adding patches
            for patch_id in patch_ids:
                if patch_id in current_solution:
                    continue
                
                if not eligible(patch_id, current_solution, dependency_graph):
                    continue
                
                total_time = sum(lookup_time.get(p, 0) for p in current_solution) + lookup_time[patch_id]
                total_cost = sum(lookup_cost.get(p, 0) for p in current_solution) + lookup_cost[patch_id]
                total_manpower = sum(lookup_manpower.get(p, 0) for p in current_solution) + lookup_manpower[patch_id]
                
                if within_capacity(total_time, total_cost, total_manpower, capacities):
                    new_value = current_value + lookup_value[patch_id]
                    if new_value > current_value:
                        current_solution.append(patch_id)
                        current_value = new_value
                        improved = True
                        no_improve_count = 0
                        break
            
            if improved:
                continue
            
            # Try removing patches
            for patch_id in current_solution:
                new_value = current_value - lookup_value[patch_id]
                if new_value > current_value - 1e-10:  # Slight improvement or lateral move
                    current_solution.remove(patch_id)
                    current_value = new_value
                    improved = True
                    no_improve_count = 0
                    break
            
            if not improved:
                no_improve_count += 1
        
        # Update best solution
        if current_value > best_value:
            best_value = current_value
            best_solution = current_solution.copy()
    
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by local search." for patch_id in rejected}
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
        algorithm="local_search",
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
        score_breakdown={"restarts": random_restarts, "max_no_improve": max_no_improve},
        schedule=schedule,
        comparison_note=f"Local Search/Hill Climbing with {random_restarts} random restarts.",
    )
