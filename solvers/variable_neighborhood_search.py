"""Variable Neighborhood Search solver for patch selection with neighborhood switching."""

from __future__ import annotations

from time import perf_counter
import random
from typing import Dict, Callable, List

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def variable_neighborhood_search(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    k_max: int = 5,
    iterations: int = 200,
) -> OptimizationResult:
    """Variable Neighborhood Search: Systematically explores different neighborhood structures.
    
    Switches between different neighborhood definitions to escape local optima more effectively.
    """
    start = perf_counter()
    patch_ids = scored["patch_id"].astype(str).tolist()
    lookup_value = scored.set_index("patch_id")["adjusted_patch_value"].to_dict()
    lookup_time = scored.set_index("patch_id")["patch_time"].to_dict()
    lookup_cost = scored.set_index("patch_id")["patch_cost"].to_dict()
    lookup_manpower = scored.set_index("patch_id")["manpower_required"].to_dict()
    
    def get_constraint_cost(solution: list[str]) -> tuple[float, float, float]:
        """Calculate current resource usage."""
        return (
            sum(lookup_time.get(p, 0) for p in solution),
            sum(lookup_cost.get(p, 0) for p in solution),
            sum(lookup_manpower.get(p, 0) for p in solution),
        )
    
    def calculate_fitness(solution: list[str]) -> float:
        """Calculate fitness as total patch value."""
        return sum(lookup_value.get(p, 0) for p in solution)
    
    # Initialize with greedy solution
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
    
    best_solution = current_solution.copy()
    best_fitness = calculate_fitness(best_solution)
    
    # Define neighborhood structures
    def neighborhood_1(solution: list[str]) -> list[str]:
        """N1: Add a single patch."""
        candidates = [p for p in patch_ids if p not in solution]
        if not candidates:
            return solution.copy()
        patch = random.choice(candidates)
        if eligible(patch, solution, dependency_graph):
            t, c, m = get_constraint_cost(solution)
            if within_capacity(t + lookup_time[patch], c + lookup_cost[patch], m + lookup_manpower[patch], capacities):
                return solution + [patch]
        return solution.copy()
    
    def neighborhood_2(solution: list[str]) -> list[str]:
        """N2: Remove a single patch."""
        if not solution:
            return solution.copy()
        patch = random.choice(solution)
        return [p for p in solution if p != patch]
    
    def neighborhood_3(solution: list[str]) -> list[str]:
        """N3: Swap two patches (remove one, add another)."""
        if not solution:
            return solution.copy()
        to_remove = random.choice(solution)
        candidates = [p for p in patch_ids if p not in solution and p != to_remove]
        if not candidates:
            return solution.copy()
        to_add = random.choice(candidates)
        if eligible(to_add, [p for p in solution if p != to_remove], dependency_graph):
            t, c, m = get_constraint_cost([p for p in solution if p != to_remove])
            if within_capacity(t + lookup_time[to_add], c + lookup_cost[to_add], m + lookup_manpower[to_add], capacities):
                return [p for p in solution if p != to_remove] + [to_add]
        return solution.copy()
    
    def neighborhood_4(solution: list[str]) -> list[str]:
        """N4: Add two patches."""
        candidates = [p for p in patch_ids if p not in solution]
        if len(candidates) < 2:
            return solution.copy()
        patches = random.sample(candidates, 2)
        test = solution + patches
        t, c, m = get_constraint_cost(test)
        if within_capacity(t, c, m, capacities) and all(eligible(p, test, dependency_graph) for p in patches):
            return test
        return solution.copy()
    
    def neighborhood_5(solution: list[str]) -> list[str]:
        """N5: Remove two patches."""
        if len(solution) < 2:
            return solution.copy()
        patches = random.sample(solution, 2)
        return [p for p in solution if p not in patches]
    
    neighborhoods: List[Callable] = [neighborhood_1, neighborhood_2, neighborhood_3, neighborhood_4, neighborhood_5]
    
    # VNS algorithm
    for iteration in range(iterations):
        k = 1
        while k <= k_max:
            # Explore neighborhood k
            neighbor = neighborhoods[k - 1](current_solution)
            neighbor_fitness = calculate_fitness(neighbor)
            
            if neighbor_fitness > calculate_fitness(current_solution):
                # Found improvement in neighborhood k
                current_solution = neighbor
                if neighbor_fitness > best_fitness:
                    best_fitness = neighbor_fitness
                    best_solution = current_solution.copy()
                k = 1  # Reset to first neighborhood
            else:
                k += 1  # Move to next neighborhood
    
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by VNS." for patch_id in rejected}
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
        algorithm="variable_neighborhood_search",
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
        score_breakdown={"k_max": k_max, "iterations": iterations, "neighborhoods": len(neighborhoods)},
        schedule=schedule,
        comparison_note=f"Variable Neighborhood Search with {len(neighborhoods)} neighborhood structures.",
    )
