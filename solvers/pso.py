"""Particle Swarm Optimization solver for patch selection using swarm intelligence."""

from __future__ import annotations

from time import perf_counter
import random
from typing import Dict, List
import math

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def particle_swarm_optimization(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    num_particles: int = 30,
    iterations: int = 100,
    w: float = 0.7,  # inertia weight
    c1: float = 1.5,  # cognitive coefficient
    c2: float = 1.5,  # social coefficient
) -> OptimizationResult:
    """Particle Swarm Optimization: Swarm intelligence approach mimicking bird flocking.
    
    Particles move through solution space influenced by their best and swarm's best positions.
    """
    start = perf_counter()
    patch_ids = scored["patch_id"].astype(str).tolist()
    lookup_value = scored.set_index("patch_id")["adjusted_patch_value"].to_dict()
    lookup_time = scored.set_index("patch_id")["patch_time"].to_dict()
    lookup_cost = scored.set_index("patch_id")["patch_cost"].to_dict()
    lookup_manpower = scored.set_index("patch_id")["manpower_required"].to_dict()
    
    def calculate_fitness(solution: list[str]) -> float:
        """Calculate fitness as total patch value."""
        return sum(lookup_value.get(p, 0) for p in solution)
    
    def is_feasible(solution: list[str]) -> bool:
        """Check if solution respects constraints."""
        total_time = sum(lookup_time.get(p, 0) for p in solution)
        total_cost = sum(lookup_cost.get(p, 0) for p in solution)
        total_manpower = sum(lookup_manpower.get(p, 0) for p in solution)
        return within_capacity(total_time, total_cost, total_manpower, capacities)
    
    # Initialize particles
    particles: List[list[str]] = []
    velocities: List[set] = []  # Represent velocity as set of patches to add/remove
    best_positions: List[list[str]] = []
    best_fitness: List[float] = []
    
    for _ in range(num_particles):
        # Random initialization
        solution = []
        shuffled = patch_ids.copy()
        random.shuffle(shuffled)
        
        time_used, cost_used, manpower_used = 0.0, 0.0, 0.0
        for p in shuffled:
            if eligible(p, solution, dependency_graph):
                t = time_used + lookup_time.get(p, 0)
                c = cost_used + lookup_cost.get(p, 0)
                m = manpower_used + lookup_manpower.get(p, 0)
                if within_capacity(t, c, m, capacities):
                    solution.append(p)
                    time_used, cost_used, manpower_used = t, c, m
        
        particles.append(solution)
        velocities.append(set())
        best_positions.append(solution.copy())
        best_fitness.append(calculate_fitness(solution))
    
    # Global best
    global_best_idx = max(range(num_particles), key=lambda i: best_fitness[i])
    global_best = best_positions[global_best_idx].copy()
    global_best_fitness = best_fitness[global_best_idx]
    
    # PSO iterations
    for iteration in range(iterations):
        for i in range(num_particles):
            current_fitness = calculate_fitness(particles[i])
            
            # Update personal best
            if current_fitness > best_fitness[i]:
                best_fitness[i] = current_fitness
                best_positions[i] = particles[i].copy()
            
            # Update global best
            if best_fitness[i] > global_best_fitness:
                global_best_fitness = best_fitness[i]
                global_best = best_positions[i].copy()
            
            # Update velocity and position (using discrete PSO)
            # Cognitive component: move towards personal best
            if random.random() < (c1 / (c1 + c2)):
                for p in best_positions[i]:
                    if p not in particles[i] and random.random() < 0.3:
                        if eligible(p, particles[i], dependency_graph):
                            t = sum(lookup_time.get(x, 0) for x in particles[i]) + lookup_time[p]
                            c = sum(lookup_cost.get(x, 0) for x in particles[i]) + lookup_cost[p]
                            m = sum(lookup_manpower.get(x, 0) for x in particles[i]) + lookup_manpower[p]
                            if within_capacity(t, c, m, capacities):
                                particles[i].append(p)
            
            # Social component: move towards global best
            if random.random() < (c2 / (c1 + c2)):
                for p in global_best:
                    if p not in particles[i] and random.random() < 0.2:
                        if eligible(p, particles[i], dependency_graph):
                            t = sum(lookup_time.get(x, 0) for x in particles[i]) + lookup_time[p]
                            c = sum(lookup_cost.get(x, 0) for x in particles[i]) + lookup_cost[p]
                            m = sum(lookup_manpower.get(x, 0) for x in particles[i]) + lookup_manpower[p]
                            if within_capacity(t, c, m, capacities):
                                particles[i].append(p)
            
            # Inertia: occasionally remove patches (exploration)
            if random.random() < (1 - w) and len(particles[i]) > 0:
                particles[i].pop(random.randint(0, len(particles[i]) - 1))
    
    best_solution = global_best
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by PSO." for patch_id in rejected}
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
        algorithm="pso",
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
        score_breakdown={"particles": num_particles, "iterations": iterations, "w": w, "c1": c1, "c2": c2},
        schedule=schedule,
        comparison_note=f"Particle Swarm Optimization (swarm={num_particles}, iter={iterations}).",
    )
