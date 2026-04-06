"""Mathematical explanation generation for optimization algorithms."""

from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd

from modules.utils import OptimizationResult


class MathExplanation:
    """Container for algorithm mathematical explanation with steps."""

    def __init__(self, algorithm_name: str, algorithm_full_name: str, core_formula: str):
        self.algorithm_name = algorithm_name
        self.algorithm_full_name = algorithm_full_name
        self.core_formula = core_formula
        self.steps: List[Dict[str, Any]] = []
        self.key_parameters: Dict[str, str] = {}
        self.final_result = ""

    def add_step(self, step_num: int, description: str, formula: str = "", value: Any = None):
        """Add a calculation step."""
        self.steps.append({
            "step": step_num,
            "description": description,
            "formula": formula,
            "value": value,
        })

    def add_parameter(self, param_name: str, param_value: str):
        """Add a key parameter."""
        self.key_parameters[param_name] = param_value

    def set_final_result(self, result: str):
        """Set the final result summary."""
        self.final_result = result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "algorithm_name": self.algorithm_name,
            "algorithm_full_name": self.algorithm_full_name,
            "core_formula": self.core_formula,
            "key_parameters": self.key_parameters,
            "steps": self.steps,
            "final_result": self.final_result,
        }


def greedy_ratio_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    total_time: float,
) -> MathExplanation:
    """Generate math explanation for greedy ratio algorithm."""
    math = MathExplanation(
        "greedy_ratio",
        "Greedy Value-to-Time Ratio",
        "Sort by ratio = adjusted_patch_value ÷ patch_time, then greedily select patches"
    )

    # Calculate ratios for top 3 selected patches
    selected_df_filtered = scored_df[scored_df["patch_id"].astype(str).isin(selected_ids)].head(3).copy()
    
    math.add_parameter("total_patches", str(len(selected_ids)))
    math.add_parameter("total_time_used", f"{total_time:.1f}h")
    math.add_parameter("total_value_gained", f"{total_value:.3f}")
    
    math.add_step(
        1,
        "Calculate value-to-time ratio for each patch",
        "ratio = adjusted_patch_value ÷ patch_time"
    )
    
    step = 2
    for _, row in selected_df_filtered.iterrows():
        patch_id = str(row["patch_id"])
        value = float(row["adjusted_patch_value"])
        time = float(row["patch_time"])
        ratio = value / time if time > 0 else 0
        math.add_step(
            step,
            f"Patch {patch_id}: {value:.3f} ÷ {time:.1f}h",
            f"ratio = {value:.3f} / {time:.1f}",
            f"= {ratio:.3f}"
        )
        step += 1
    
    math.add_step(
        step,
        "Sort all patches by ratio (highest first)",
        "sorted_patches = sorted(all_patches, by=ratio, descending=True)"
    )
    
    math.set_final_result(
        f"Selected {len(selected_ids)} patches with combined value {total_value:.3f} "
        f"using {total_time:.1f}h maintenance time"
    )
    
    return math


def dp_single_constraint_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    total_time: float,
    capacity_hours: float,
) -> MathExplanation:
    """Generate math explanation for dynamic programming knapsack."""
    math = MathExplanation(
        "dp_single",
        "0/1 Knapsack (Dynamic Programming)",
        "dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight[i]] + value[i])"
    )

    math.add_parameter("capacity", f"{capacity_hours:.1f}h")
    math.add_parameter("total_patches", str(len(scored_df)))
    math.add_parameter("selected_patches", str(len(selected_ids)))
    math.add_parameter("utilization", f"{(total_time/capacity_hours*100):.1f}%")
    
    math.add_step(
        1,
        "Initialize DP table",
        "dp[0...capacity] = [0.0]",
        f"Create table for capacity {capacity_hours:.1f}h"
    )
    
    math.add_step(
        2,
        "For each patch i from 0 to n:",
        "For each capacity w from capacity down to weight[i]:",
        "Reverse iteration prevents using same item twice"
    )
    
    math.add_step(
        3,
        "Recurrence relation",
        "if dp[w-weight[i]] + value[i] > dp[w]:",
        "dp[w] = dp[w-weight[i]] + value[i]"
    )
    
    selected_df_filtered = scored_df[scored_df["patch_id"].astype(str).isin(selected_ids)].head(3).copy()
    
    step = 4
    for _, row in selected_df_filtered.iterrows():
        patch_id = str(row["patch_id"])
        value = float(row["adjusted_patch_value"])
        time = float(row["patch_time"])
        math.add_step(
            step,
            f"Patch {patch_id} included in optimal solution",
            f"Time: {time:.1f}h, Value: {value:.3f}"
        )
        step += 1
    
    math.add_step(
        step,
        "Backtrack from dp[capacity] to reconstruct solution",
        "For i from n-1 down to 0: if keep[i][capacity]: add patch i to solution"
    )
    
    math.set_final_result(
        f"Optimal value: {total_value:.3f}\n"
        f"Selected {len(selected_ids)} patches, using {total_time:.1f}h / {capacity_hours:.1f}h capacity"
    )
    
    return math


def genetic_algorithm_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
    population_size: int = 50,
    generations: int = 100,
    mutation_rate: float = 0.15,
    crossover_rate: float = 0.8,
) -> MathExplanation:
    """Generate math explanation for genetic algorithm."""
    math = MathExplanation(
        "genetic_algorithm",
        "Genetic Algorithm",
        "Evolve population through selection, crossover, and mutation"
    )

    math.add_parameter("population_size", str(population_size))
    math.add_parameter("generations", str(generations))
    math.add_parameter("mutation_rate", f"{mutation_rate*100:.1f}%")
    math.add_parameter("crossover_rate", f"{crossover_rate*100:.1f}%")
    
    math.add_step(
        1,
        "Initialize population with random valid solutions",
        "population = [random_solution() for _ in range(population_size)]",
        f"Generate {population_size} candidate solutions"
    )
    
    math.add_step(
        2,
        "Calculate fitness for each solution",
        "fitness(solution) = sum(adjusted_patch_value for each patch in solution)",
        f"Maximize total patch value"
    )
    
    math.add_step(
        3,
        "Selection: Choose parents based on fitness",
        "parent_probability ∝ fitness(solution)",
        "Higher fitness → higher chance of reproduction"
    )
    
    math.add_step(
        4,
        "Crossover with probability",
        f"if random() < {crossover_rate}: child = combine(parent1, parent2)",
        "Single-point or multi-point crossover"
    )
    
    math.add_step(
        5,
        "Mutation with probability",
        f"if random() < {mutation_rate}: randomly flip/add/remove genes",
        "Diversify population to escape local optima"
    )
    
    math.add_step(
        6,
        f"Repeat for {generations} generations",
        "each_generation: selection → crossover → mutation → evaluate",
        f"Evolve toward better solutions iteratively"
    )
    
    math.set_final_result(
        f"Best fitness found: {total_value:.3f}\n"
        f"Selected {len(selected_ids)} patches\n"
        f"Converged in {runtime_seconds:.2f}s over {generations} generations"
    )
    
    return math


def tabu_search_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
    max_iterations: int = 500,
    tabu_tenure: int = 50,
) -> MathExplanation:
    """Generate math explanation for tabu search."""
    math = MathExplanation(
        "tabu_search",
        "Tabu Search with Memory",
        "Explore neighborhood while maintaining tabu list of forbidden moves"
    )

    math.add_parameter("max_iterations", str(max_iterations))
    math.add_parameter("tabu_tenure", f"{tabu_tenure} iterations")
    math.add_parameter("best_value_found", f"{total_value:.3f}")
    
    math.add_step(
        1,
        "Initialize with greedy solution",
        "current_solution = greedy_build(patches)",
        "Start from feasible solution"
    )
    
    math.add_step(
        2,
        "Initialize tabu list (empty)",
        "tabu_list = {}, best_solution = current_solution",
        "Track recently rejected moves"
    )
    
    math.add_step(
        3,
        "For each iteration k = 1 to max_iterations:",
        "Generate neighbors by adding/removing patches",
        "Neighborhood: {solution ± patch | patch ∈ candidate_set}"
    )
    
    math.add_step(
        4,
        "Evaluate all neighbors",
        "fitness(neighbor) = sum(patch values) if feasible else -∞",
        "Only consider solutions respecting constraints"
    )
    
    math.add_step(
        5,
        "Select best neighbor (unless tabu or no improvement)",
        "if neighbor not in tabu_list OR fitness(neighbor) > best_value:",
        "Aspiration criterion allows breaking tabu for very good solutions"
    )
    
    math.add_step(
        6,
        "Update tabu list",
        f"Add move to tabu_list with tenure = {tabu_tenure}",
        "Forbid reversing best move for next moves"
    )
    
    math.add_step(
        7,
        "Decay tabu list",
        "age_counter += 1; remove moves if age > tenure",
        "Gradually free up forbidden moves"
    )
    
    math.set_final_result(
        f"Best solution found: {total_value:.3f}\n"
        f"Selected {len(selected_ids)} patches\n"
        f"Converged after exploring neighborhood "
        f"(runtime: {runtime_seconds:.2f}s)"
    )
    
    return math


def pso_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
) -> MathExplanation:
    """Generate math explanation for particle swarm optimization."""
    math = MathExplanation(
        "pso",
        "Particle Swarm Optimization",
        "velocity[i] = w·velocity[i] + c1·random()·(pbest[i] - position[i]) + c2·random()·(gbest - position[i])"
    )

    math.add_parameter("particles", "30")
    math.add_parameter("generations", "100")
    math.add_parameter("inertia_weight", "0.7")
    math.add_parameter("cognitive_coeff", "1.5")
    math.add_parameter("social_coeff", "1.5")
    
    math.add_step(
        1,
        "Initialize swarm with random particles (solutions)",
        "position[i] = random_solution() for i in particles",
        "Each particle represents a patch selection"
    )
    
    math.add_step(
        2,
        "Evaluate fitness for each particle",
        "fitness[i] = sum(patch values) if feasible",
        "Track personal best (pbest[i]) and global best (gbest)"
    )
    
    math.add_step(
        3,
        "Update velocity vector",
        "v[i] = w·v[i] + c1·r1()·(pbest[i]-x[i]) + c2·r2()·(gbest-x[i])",
        "Attraction to personal best and global best"
    )
    
    math.add_step(
        4,
        "Update position",
        "x[i] = x[i] + v[i]",
        "Move particle in the solution space"
    )
    
    math.add_step(
        5,
        "Apply constraints and repair",
        "if solution violates capacity: remove lowest-value patches",
        "Ensure new particle position is feasible"
    )
    
    math.add_step(
        6,
        "Update personal and global best",
        "if fitness[i] > pbest_fitness[i]: pbest[i] = x[i]",
        "if fitness[i] > gbest_fitness: gbest = x[i]"
    )
    
    math.add_step(
        7,
        "Repeat for N generations",
        "accumulate_velocity_momentum_toward_best_solutions()",
        "Swarm converges to optimal region"
    )
    
    math.set_final_result(
        f"Global best fitness: {total_value:.3f}\n"
        f"Selected {len(selected_ids)} patches\n"
        f"Swarm converged in {runtime_seconds:.2f}s"
    )
    
    return math


def simulated_annealing_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
) -> MathExplanation:
    """Generate math explanation for simulated annealing."""
    math = MathExplanation(
        "simulated_annealing",
        "Simulated Annealing",
        "p_accept(neighbor) = exp(-(cost(neighbor) - cost(current)) / temperature)"
    )

    math.add_parameter("initial_temp", "100.0")
    math.add_parameter("cooling_rate", "0.95")
    math.add_parameter("min_temp", "1.0")
    
    math.add_step(
        1,
        "Initialize with random solution at high temperature",
        "current_solution = random_solution()",
        "High temperature allows exploration"
    )
    
    math.add_step(
        2,
        "Set initial temperature",
        "T = T_initial = 100.0",
        "Temperature controls acceptance of worse solutions"
    )
    
    math.add_step(
        3,
        "For each temperature level:",
        "while T > T_min: explore neighbors",
        "Inner loop explores many solutions at given T"
    )
    
    math.add_step(
        4,
        "Generate neighbor by adding/removing patch",
        "neighbor = current_solution ± random_patch",
        "Single-move local neighborhood"
    )
    
    math.add_step(
        5,
        "Calculate acceptance probability",
        "if ΔE < 0: accept (neighbor is better)",
        "if ΔE ≥ 0: accept with p = exp(-ΔE / T)"
    )
    
    math.add_step(
        6,
        "Accept or reject neighbor",
        "if random() < p_accept: current = neighbor",
        "Lower temperature → lower acceptance of worse solutions"
    )
    
    math.add_step(
        7,
        "Cool down temperature",
        f"T = T * cooling_rate",
        "Gradually shift from exploration to exploitation"
    )
    
    math.set_final_result(
        f"Best solution found: {total_value:.3f}\n"
        f"Selected {len(selected_ids)} patches\n"
        f"Temperature cooled to convergence ({runtime_seconds:.2f}s)"
    )
    
    return math


def greedy_weighted_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    total_time: float,
) -> MathExplanation:
    """Generate math explanation for greedy weighted algorithm."""
    math = MathExplanation(
        "greedy_weighted",
        "Greedy Weighted Value Score",
        "Sort by adjusted_patch_value weighted by priority, then greedily select"
    )

    math.add_parameter("total_patches", str(len(selected_ids)))
    math.add_parameter("total_time_used", f"{total_time:.1f}h")
    math.add_parameter("total_value_gained", f"{total_value:.3f}")
    
    math.add_step(
        1,
        "Calculate weighted score for each patch",
        "score = adjusted_patch_value × (1 + priority_factor)"
    )
    
    selected_df_filtered = scored_df[scored_df["patch_id"].astype(str).isin(selected_ids)].head(3).copy()
    
    step = 2
    for _, row in selected_df_filtered.iterrows():
        patch_id = str(row["patch_id"])
        value = float(row["adjusted_patch_value"])
        priority = float(row.get("priority_score", 1.0))
        weighted_score = value * (1 + priority)
        math.add_step(
            step,
            f"Patch {patch_id}: {value:.3f} × (1 + {priority:.2f})",
            f"weighted_score = {value:.3f} × {1 + priority:.2f}",
            f"= {weighted_score:.3f}"
        )
        step += 1
    
    math.add_step(
        step,
        "Sort patches by weighted score (highest first)",
        "sorted = sorted(patches, by=weighted_score, descending=True)"
    )
    
    math.set_final_result(
        f"Selected {len(selected_ids)} patches with combined value {total_value:.3f} "
        f"prioritizing high-score items over others"
    )
    return math


def multi_resource_greedy_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    total_time: float,
    total_cost: float,
    total_manpower: float,
) -> MathExplanation:
    """Generate math explanation for multi-resource greedy algorithm."""
    math = MathExplanation(
        "multi_resource_greedy",
        "Multi-Resource Greedy (3D Knapsack)",
        "ratio = value ÷ (norm_time + norm_cost + norm_manpower)"
    )

    math.add_parameter("total_patches", str(len(selected_ids)))
    math.add_parameter("time_used", f"{total_time:.1f}h")
    math.add_parameter("cost_used", f"₹{total_cost:.2f}")
    math.add_parameter("manpower_used", f"{total_manpower:.1f}")
    
    math.add_step(
        1,
        "Normalize each resource to [0,1]",
        "norm_time = patch_time / capacity_hours",
        "norm_cost = patch_cost / budget_limit"
    )
    
    math.add_step(
        2,
        "Calculate resource footprint",
        "footprint = norm_time + norm_cost + norm_manpower",
        "Sum of normalized resource demands"
    )
    
    math.add_step(
        3,
        "Calculate multi-resource ratio",
        "ratio = adjusted_patch_value / footprint",
        "Higher ratio = better efficiency across all resources"
    )
    
    selected_df_filtered = scored_df[scored_df["patch_id"].astype(str).isin(selected_ids)].head(2).copy()
    
    step = 4
    for _, row in selected_df_filtered.iterrows():
        patch_id = str(row["patch_id"])
        value = float(row["adjusted_patch_value"])
        math.add_step(
            step,
            f"Patch {patch_id} included in selection",
            f"Value: {value:.3f}, Resources balanced"
        )
        step += 1
    
    math.add_step(
        step,
        "Select greedily until capacity exhausted",
        "Iterate through sorted patches, add while feasible"
    )
    
    math.set_final_result(
        f"Balanced solution across 3 resources:\n"
        f"Value: {total_value:.3f} | Time: {total_time:.1f}h | "
        f"Cost: ₹{total_cost:.2f} | Manpower: {total_manpower:.1f}"
    )
    return math


def branch_and_bound_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
) -> MathExplanation:
    """Generate math explanation for branch and bound algorithm."""
    math = MathExplanation(
        "branch_bound",
        "Branch and Bound with Upper Bound Pruning",
        "Explore search tree with bounding: if upper_bound ≤ best_found, prune branch"
    )

    math.add_parameter("selected_patches", str(len(selected_ids)))
    math.add_parameter("best_value_found", f"{total_value:.3f}")
    math.add_parameter("solution_type", "Exact (provably optimal)")
    
    math.add_step(
        1,
        "Sort items by value-per-resource ratio",
        "ratio = value / (time + cost/10000 + manpower)",
        "Heuristic ordering for better pruning"
    )
    
    math.add_step(
        2,
        "Initialize: best_solution = empty, best_value = 0",
        "Maintain best feasible solution found so far"
    )
    
    math.add_step(
        3,
        "Recursively branch on each item (include/exclude)",
        "For each item at index i:\n  - Try including it: recurse(i+1, ...) with item added\n  - Try excluding it: recurse(i+1, ...) without item",
        "Binary tree of 2^n possible solutions"
    )
    
    math.add_step(
        4,
        "Calculate upper bound for current branch",
        "upper_bound = current_value + greedy_estimate(remaining_items)",
        "Estimate best possible from this branch"
    )
    
    math.add_step(
        5,
        "Prune if upper_bound ≤ best_value",
        "if upper_bound <= best_value: return (skip this branch)",
        "Eliminates provably suboptimal branches"
    )
    
    math.add_step(
        6,
        "Update best solution when feasible complete solution found",
        "if index >= n_items and value > best_value: best_solution = current"
    )
    
    math.set_final_result(
        f"Optimal solution (proven):\n"
        f"Value: {total_value:.3f}\n"
        f"Patches: {len(selected_ids)}\n"
        f"Runtime: {runtime_seconds:.2f}s"
    )
    return math


def ilp_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
) -> MathExplanation:
    """Generate math explanation for ILP solver."""
    math = MathExplanation(
        "ilp",
        "Integer Linear Programming (ILP)",
        "Maximize: Σ(value_i × x_i) subject to: Σ(time_i × x_i) ≤ capacity, x_i ∈ {0,1}"
    )

    math.add_parameter("solver", "CBC (via PuLP)")
    math.add_parameter("problem_type", "Integer Linear Program")
    math.add_parameter("num_variables", str(len(scored_df)))
    math.add_parameter("num_constraints", "3 (time, cost, manpower)")
    
    math.add_step(
        1,
        "Formulate optimization problem",
        "Decision variables: x_i ∈ {0, 1} for each patch i",
        "Binary: 1=selected, 0=not selected"
    )
    
    math.add_step(
        2,
        "Objective function (maximize)",
        "Max: Σ(adjusted_patch_value_i × x_i)",
        "Maximize total patch value"
    )
    
    math.add_step(
        3,
        "Constraint 1: Maintenance time",
        "Σ(patch_time_i × x_i) ≤ maintenance_window_hours",
        "Respect time capacity"
    )
    
    math.add_step(
        4,
        "Constraint 2: Budget",
        "Σ(patch_cost_i × x_i) ≤ budget_limit",
        "Respect cost capacity"
    )
    
    math.add_step(
        5,
        "Constraint 3: Manpower",
        "Σ(manpower_required_i × x_i) ≤ manpower_limit",
        "Respect manpower capacity"
    )
    
    math.add_step(
        6,
        "Solve using CBC branch-and-cut algorithm",
        "Solver explores integer space with cutting planes",
        "Guarantees optimal solution"
    )
    
    math.set_final_result(
        f"Optimal solution found:\n"
        f"Objective value: {total_value:.3f}\n"
        f"Selected: {len(selected_ids)} patches\n"
        f"Solver time: {runtime_seconds:.2f}s"
    )
    return math


def fptas_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    epsilon: float = 0.2,
) -> MathExplanation:
    """Generate math explanation for FPTAS knapsack approximation."""
    math = MathExplanation(
        "fptas",
        "Fully Polynomial-Time Approximation (FPTAS)",
        "Scale values to reduce DP table size, then solve scaled knapsack exactly"
    )

    math.add_parameter("original_problem", "Unbounded value range")
    math.add_parameter("epsilon", f"{epsilon:.2f}")
    math.add_parameter("approximation_ratio", f"(1 + ε) ≤ {1 + epsilon:.2f}×OPT")
    
    math.add_step(
        1,
        "Find maximum value",
        "max_value = max(adjusted_patch_value for all patches)",
        f"Pivot for scaling: {float(scored_df['adjusted_patch_value'].max()):.3f}"
    )
    
    math.add_step(
        2,
        "Calculate scaling factor",
        f"scale = ε × max_value / n = {epsilon} × max_value / {len(scored_df)}",
        "Trade accuracy for reduced DP table size"
    )
    
    math.add_step(
        3,
        "Scale and round values",
        "scaled_value_i = floor(value_i / scale)",
        "Converts continuous values to discrete integers"
    )
    
    math.add_step(
        4,
        "Create DP table with scaled values",
        "dp[0...sum_scaled] = standard 0/1 knapsack on scaled problem",
        "Much smaller table than original (polynomial in n and 1/ε)"
    )
    
    math.add_step(
        5,
        "Find best achievable scaled value",
        "best_scaled = max(i where dp[i] ≤ capacity)",
        "Backtrack to find which patches to include"
    )
    
    math.add_step(
        6,
        "Return unscaled solution",
        "Reconstructed solution achieves (1+ε) approximation",
        f"Actual value: {total_value:.3f}"
    )
    
    math.set_final_result(
        f"Approximation guarantee: solution ≥ OPT / (1 + {epsilon})\n"
        f"Polynomial time: O(n²/ε)\n"
        f"Selected {len(selected_ids)} patches, value {total_value:.3f}"
    )
    return math


def local_search_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
    random_restarts: int = 5,
    max_no_improve: int = 100,
) -> MathExplanation:
    """Generate math explanation for local search with restarts."""
    math = MathExplanation(
        "local_search",
        "Local Search (Hill Climbing) with Random Restarts",
        "Repeatedly make locally-optimal moves until stuck, then restart from random solution"
    )

    math.add_parameter("random_restarts", str(random_restarts))
    math.add_parameter("no_improve_limit", str(max_no_improve))
    math.add_parameter("best_value_found", f"{total_value:.3f}")
    
    math.add_step(
        1,
        "For each restart k in 1..K:",
        "Different random starting solutions to explore variety"
    )
    
    math.add_step(
        2,
        "Initialize solution",
        "if k=1: use greedy solution; else: random valid solution",
        "First uses heuristic, others explore randomly"
    )
    
    math.add_step(
        3,
        "Generate neighbors",
        "neighbors = {solution ± patch | patch in candidates}",
        "Add/remove single patches for local neighborhood"
    )
    
    math.add_step(
        4,
        "Evaluate all neighbors",
        "scores = [fitness(neighbor) for neighbor in neighbors]",
        "Calculate value of each neighboring solution"
    )
    
    math.add_step(
        5,
        "Select best improving neighbor",
        "best_neighbor = argmax(scores) if improving else STOP",
        "Greedy: only move if better than current"
    )
    
    math.add_step(
        6,
        "Update current solution",
        "current = best_neighbor; no_improve_count = 0",
        "Move to better neighbor, reset counter"
    )
    
    math.add_step(
        7,
        "Check for local optimum",
        "if no improving neighbor for N iterations: stop this restart",
        "Caught in local maximum, start over"
    )
    
    math.set_final_result(
        f"Best solution found:\n"
        f"Value: {total_value:.3f}\n"
        f"Selected: {len(selected_ids)} patches\n"
        f"Runtime: {runtime_seconds:.2f}s"
    )
    return math


def vns_math(
    scored_df: pd.DataFrame,
    selected_ids: List[str],
    total_value: float,
    runtime_seconds: float,
    k_max: int = 5,
    iterations: int = 200,
) -> MathExplanation:
    """Generate math explanation for variable neighborhood search."""
    math = MathExplanation(
        "variable_neighborhood_search",
        "Variable Neighborhood Search (VNS)",
        "Switch between k different neighborhood structures to escape local optima"
    )

    math.add_parameter("k_max", str(k_max))
    math.add_parameter("total_iterations", str(iterations))
    math.add_parameter("best_value_found", f"{total_value:.3f}")
    
    math.add_step(
        1,
        "Initialize with greedy solution",
        "current = greedy_build(patches)",
        "Start from feasible heuristic solution"
    )
    
    math.add_step(
        2,
        "Set neighborhood index k = 1",
        "Define k different neighborhood structures",
        "Example: k1=add, k2=remove, k3=swap, k4=2-exchange, k5=complex"
    )
    
    math.add_step(
        3,
        "For each iteration:",
        "Generate k-th neighborhood",
        "Different k gives different neighboring solutions"
    )
    
    math.add_step(
        4,
        "Apply local search in neighborhood k",
        "local_best = local_search_in_N_k(current)",
        "Hill climb within current neighborhood"
    )
    
    math.add_step(
        5,
        "Check improvement",
        "if fitness(local_best) > fitness(current):",
        "If found better, move there and reset k=1"
    )
    
    math.add_step(
        6,
        "If no improvement, switch neighborhood",
        "else: k = k + 1 (try different neighborhood)",
        "Escape local optimum by changing search strategy"
    )
    
    math.add_step(
        7,
        "Repeat until k > k_max or iterations exhausted",
        "Try all neighborhood structures before restarting",
        "Systematic exploration with multiple perspectives"
    )
    
    math.set_final_result(
        f"Best solution found across neighborhoods:\n"
        f"Value: {total_value:.3f}\n"
        f"Selected: {len(selected_ids)} patches\n"
        f"Runtime: {runtime_seconds:.2f}s"
    )
    return math


def generate_math_explanation(
    result: OptimizationResult,
    scored_df: pd.DataFrame,
) -> MathExplanation:
    """Generate appropriate math explanation based on algorithm used."""
    
    algorithm = result.algorithm
    selected_ids = result.selected_ids
    total_value = result.total_value
    total_time = result.total_time
    total_cost = result.total_cost
    total_manpower = result.total_manpower
    runtime_seconds = result.runtime_seconds

    if algorithm == "greedy_ratio":
        return greedy_ratio_math(scored_df, selected_ids, total_value, total_time)
    elif algorithm == "greedy_weighted":
        return greedy_weighted_math(scored_df, selected_ids, total_value, total_time)
    elif algorithm == "multi_resource_greedy":
        return multi_resource_greedy_math(scored_df, selected_ids, total_value, total_time, total_cost, total_manpower)
    elif algorithm == "dp_single":
        capacity = 40.0
        return dp_single_constraint_math(scored_df, selected_ids, total_value, total_time, capacity)
    elif algorithm == "branch_bound":
        return branch_and_bound_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "fptas":
        return fptas_math(scored_df, selected_ids, total_value, epsilon=0.2)
    elif algorithm == "ilp":
        return ilp_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "genetic_algorithm":
        return genetic_algorithm_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "tabu_search":
        return tabu_search_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "pso":
        return pso_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "simulated_annealing":
        return simulated_annealing_math(scored_df, selected_ids, total_value, runtime_seconds)
    elif algorithm == "local_search":
        return local_search_math(scored_df, selected_ids, total_value, runtime_seconds, random_restarts=5, max_no_improve=100)
    elif algorithm == "variable_neighborhood_search":
        return vns_math(scored_df, selected_ids, total_value, runtime_seconds, k_max=5, iterations=200)
    else:
        # Generic explanation for any other algorithms
        math = MathExplanation(
            algorithm,
            algorithm.replace("_", " ").title(),
            "Custom optimization algorithm"
        )
        math.add_parameter("selected", str(len(selected_ids)))
        math.add_parameter("total_value", f"{total_value:.3f}")
        math.add_step(1, "Execute algorithm", "See solver implementation for mathematical details")
        math.set_final_result(f"Found solution with value {total_value:.3f}")
        return math
