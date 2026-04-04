"""Multi-system extension for grouped patch deployment."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from modules.dependency_graph import DependencyGraph
from solvers.branch_and_bound import branch_and_bound


def solve_by_system(
    scored: pd.DataFrame,
    capacities: Dict[str, float],
    dependency_graph: DependencyGraph | None = None,
    group_column: str = "system_group",
) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for group_name, group_frame in scored.groupby(group_column):
        group_result = branch_and_bound(group_frame.copy(), capacities, dependency_graph)
        results[str(group_name)] = group_result.to_dict()
    return results
