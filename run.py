"""Entry point for the web dashboard and CLI demo runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from app import APP_STATE, create_app, _solve_from_request
from modules.data_loader import load_dataset
from modules.dataset_generator import write_dataset
from experiments.phase2_benchmark import run_phase2_benchmark


def run_cli(dataset: str, algorithm: str) -> None:
    path = Path(dataset)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset}")
    form = {
        "algorithm": algorithm,
        "sample_dataset": "sample_small",
        "capacity_maintenance_window_hours": "18",
        "capacity_budget": "45000",
        "capacity_manpower": "30",
        "dependency_mode": "on",
        "dynamic_risk_mode": "on",
        "sla_mode": "on",
        "adversarial_mode": "on",
    }
    _solve_from_request(form, {"dataset_file": type("Upload", (), {"filename": path.name, "read": lambda self=None: path.read_bytes()})()})
    result = APP_STATE["latest_result"]
    print(f"Algorithm: {result.algorithm}")
    print(f"Selected patches: {', '.join(result.selected_ids)}")
    print(f"Risk reduced: {result.total_value:.3f}")
    print(f"Runtime: {result.runtime_seconds:.4f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cybersecurity optimal patch deployment demo")
    parser.add_argument("--cli", action="store_true", help="Run the command-line demo instead of the web app")
    parser.add_argument("--dataset", default="data/sample_small.csv", help="Dataset to use for CLI mode")
    parser.add_argument("--algorithm", default="branch_bound", choices=["greedy_ratio", "greedy_weighted", "multi_resource_greedy", "dp_single", "branch_bound", "fptas", "ilp"], help="Solver to run in CLI mode")
    parser.add_argument("--generate-samples", action="store_true", help="Generate sample_medium.csv and sample_large.csv")
    parser.add_argument("--benchmark-phase2", action="store_true", help="Run the Phase 2 comparison benchmark")
    args = parser.parse_args()

    if args.generate_samples:
        write_dataset("data/sample_medium.csv", size=60, seed=84)
        write_dataset("data/sample_large.csv", size=180, seed=126)
        print("Generated sample_medium.csv and sample_large.csv")
        return

    if args.benchmark_phase2:
        payload = run_phase2_benchmark(args.dataset)
        print(payload)
        return

    if args.cli:
        run_cli(args.dataset, args.algorithm)
        return

    create_app().run(debug=True)


if __name__ == "__main__":
    main()
