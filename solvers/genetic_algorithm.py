"""Genetic Algorithm solver for patch selection using population-based evolution."""

from __future__ import annotations

from time import perf_counter
import random
from typing import Dict, Tuple
import math

import pandas as pd

from modules.dependency_graph import DependencyGraph
from modules.explainability import build_explanation_map
from modules.scheduler import build_schedule
from modules.utils import OptimizationResult
from solvers.common import eligible, selection_is_feasible, within_capacity


def genetic_algorithm(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    population_size: int = 50,
    generations: int = 100,
    mutation_rate: float = 0.15,
    crossover_rate: float = 0.8,
) -> OptimizationResult:
    """Genetic Algorithm: Evolution-based approach using population of solutions.
    
    Uses crossover and mutation operators to explore the solution space.
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
    
    def is_valid(solution: list[str]) -> bool:
        """Check if solution respects constraints."""
        total_time = sum(lookup_time.get(p, 0) for p in solution)
        total_cost = sum(lookup_cost.get(p, 0) for p in solution)
        total_manpower = sum(lookup_manpower.get(p, 0) for p in solution)
        if not within_capacity(total_time, total_cost, total_manpower, capacities):
            return False
        return all(eligible(p, solution, dependency_graph) for p in solution)
    
    def initialize_population() -> list[list[str]]:
        """Create initial population with random valid solutions."""
        population = []
        while len(population) < population_size:
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
            
            if len(solution) > 0 or random.random() < 0.3:
                population.append(solution)
        
        return population[:population_size]
    
    def crossover(parent1: list[str], parent2: list[str]) -> Tuple[list[str], list[str]]:
        """Single-point crossover."""
        if len(parent1) == 0 or len(parent2) == 0:
            return parent1.copy(), parent2.copy()
        
        point = random.randint(1, max(len(parent1), len(parent2)) - 1)
        child1 = (parent1[:point] + parent2[point:])[:max(len(parent1), len(parent2))]
        child2 = (parent2[:point] + parent1[point:])[:max(len(parent1), len(parent2))]
        
        # Remove duplicates
        child1 = list(dict.fromkeys(child1))
        child2 = list(dict.fromkeys(child2))
        
        return child1, child2
    
    def mutate(solution: list[str]) -> list[str]:
        """Mutation: add/remove random patches."""
        result = solution.copy()
        
        if random.random() < mutation_rate / 2 and len(result) > 0:
            # Remove random patch
            result.pop(random.randint(0, len(result) - 1))
        
        if random.random() < mutation_rate / 2:
            # Add random patch
            available = [p for p in patch_ids if p not in result]
            if available:
                candidate = random.choice(available)
                if eligible(candidate, result, dependency_graph):
                    t = sum(lookup_time.get(p, 0) for p in result) + lookup_time[candidate]
                    c = sum(lookup_cost.get(p, 0) for p in result) + lookup_cost[candidate]
                    m = sum(lookup_manpower.get(p, 0) for p in result) + lookup_manpower[candidate]
                    if within_capacity(t, c, m, capacities):
                        result.append(candidate)
        
        return result
    
    # Initialize population
    population = initialize_population()
    best_solution = max(population, key=calculate_fitness) if population else []
    best_fitness = calculate_fitness(best_solution)
    
    # Evolution
    for generation in range(generations):
        # Fitness evaluation
        fitness_scores = [(calculate_fitness(sol), sol) for sol in population]
        fitness_scores.sort(reverse=True)
        
        # Update best
        if fitness_scores[0][0] > best_fitness:
            best_fitness = fitness_scores[0][0]
            best_solution = fitness_scores[0][1].copy()
        
        # Selection and reproduction
        new_population = [fitness_scores[0][1]]  # Elitism
        
        while len(new_population) < population_size:
            # Tournament selection
            tournament = random.sample(population, min(3, len(population)))
            parent1 = max(tournament, key=calculate_fitness)
            
            tournament = random.sample(population, min(3, len(population)))
            parent2 = max(tournament, key=calculate_fitness)
            
            if random.random() < crossover_rate:
                child1, child2 = crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            
            child1 = mutate(child1)
            if random.random() < 0.5 and len(new_population) < population_size:
                new_population.append(child1)
            
            child2 = mutate(child2)
            if len(new_population) < population_size:
                new_population.append(child2)
        
        population = new_population[:population_size]
    
    feasible, notes = selection_is_feasible(best_solution, dependency_graph)
    selected_df = scored[scored["patch_id"].astype(str).isin(best_solution)].copy()
    rejected = [str(item) for item in patch_ids if str(item) not in set(best_solution)]
    rejected_notes = {patch_id: "Not selected by genetic algorithm." for patch_id in rejected}
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
        algorithm="genetic_algorithm",
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
        score_breakdown={"population_size": population_size, "generations": generations, "mutation_rate": mutation_rate},
        schedule=schedule,
        comparison_note=f"Genetic Algorithm with evolution (pop={population_size}, gen={generations}).",
    )
