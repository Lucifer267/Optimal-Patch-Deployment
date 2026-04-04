"""Phase 2 benchmark runner for multi-dimensional comparison experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from config import Config
from modules.benchmarking import build_comparison_frame, quality_summary
from modules.data_loader import load_dataset
from modules.dependency_graph import build_dependency_graph
from modules.risk_engine import score_dataset
from modules.sla_engine import sla_status
from solvers.approximation import fptas_knapsack
from solvers.branch_and_bound import branch_and_bound
from solvers.dynamic_programming import dp_single_constraint
from solvers.greedy import greedy_ratio, greedy_weighted
from solvers.ilp_solver import ilp_solve
from solvers.multi_resource import multi_resource_greedy


def run_phase2_benchmark(dataset_path: str | Path = "data/sample_medium.csv") -> dict:
    dataframe = load_dataset(dataset_path)
    scored = score_dataset(dataframe, Config.SCORING_WEIGHTS, adversarial_mode=True)
    scored = sla_status(scored)
    dependency_graph = build_dependency_graph(scored)
    capacities = dict(Config.DEFAULT_CAPACITY)

    results = {
        "greedy_ratio": greedy_ratio(scored, capacities, dependency_graph),
        "greedy_weighted": greedy_weighted(scored, capacities, dependency_graph),
        "multi_resource_greedy": multi_resource_greedy(scored, capacities, dependency_graph),
        "dp_single": dp_single_constraint(scored, capacities),
        "branch_bound": branch_and_bound(scored, capacities, dependency_graph),
        "fptas": fptas_knapsack(scored, capacities),
        "ilp": ilp_solve(scored, capacities),
    }

    comparison_frame = build_comparison_frame(results, capacities)
    summary = quality_summary(comparison_frame)
    return {
        "dataset": str(dataset_path),
        "summary": summary,
        "comparison": comparison_frame.to_dict(orient="records"),
    }


if __name__ == "__main__":
    payload = run_phase2_benchmark()
    print(json.dumps(payload, indent=2))
