"""Application configuration for the cybersecurity patch optimization project."""

from __future__ import annotations


class Config:
    SECRET_KEY = "cyber-optimal-patch-deployment"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = "data/uploads"
    DEFAULT_DATASET = "data/sample_small.csv"

    DEFAULT_CAPACITY = {
        "maintenance_window_hours": 18.0,
        "budget": 45000.0,
        "manpower": 30.0,
    }

    SCORING_WEIGHTS = {
        "cvss": 0.18,
        "exploit_probability": 0.12,
        "exploit_available": 0.08,
        "active_exploitation": 0.10,
        "asset_criticality": 0.16,
        "data_sensitivity": 0.10,
        "exposure_level": 0.09,
        "time_decay": 0.10,
        "sla_urgency": 0.07,
        "failure_penalty": 0.14,
        "adversarial": 0.05,
    }

    ALGORITHM_LABELS = {
        "greedy_ratio": "Greedy Ratio",
        "greedy_weighted": "Greedy Weighted",
        "multi_resource_greedy": "Multi-Resource Greedy",
        "dp_single": "Dynamic Programming",
        "branch_bound": "Branch and Bound",
        "fptas": "Approximation (FPTAS)",
        "ilp": "ILP Benchmark",
        "tabu_search": "Tabu Search",
        "simulated_annealing": "Simulated Annealing",
        "genetic_algorithm": "Genetic Algorithm",
        "pso": "Particle Swarm Optimization",
        "local_search": "Local Search/Hill Climbing",
        "variable_neighborhood_search": "Variable Neighborhood Search",
    }

    THEME = {
        "name": "nocturne-cyber",
        "accent": "#7c3aed",
        "accent_2": "#06b6d4",
        "bg": "#070b14",
        "panel": "#0d1424",
        "panel_elevated": "#111a2e",
        "border": "rgba(148, 163, 184, 0.16)",
        "text": "#e5eefb",
        "muted": "#94a3b8",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
    }


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
