"""Shared solver helpers."""

from __future__ import annotations

from typing import Dict, Sequence

import pandas as pd

from modules.dependency_graph import DependencyGraph, selection_feasible


def get_lookup(dataframe: pd.DataFrame, column: str) -> dict:
    return dataframe.set_index("patch_id")[column].to_dict()


def eligible(patch_id: str, selected: Sequence[str], dependency_graph: DependencyGraph | None) -> bool:
    if dependency_graph is None:
        return True
    selected_set = set(str(item) for item in selected)
    predecessors = set(dependency_graph.graph.predecessors(patch_id))
    if not predecessors.issubset(selected_set):
        return False
    for conflict in dependency_graph.conflicts.get(patch_id, set()):
        if conflict in selected_set:
            return False
    return True


def selection_is_feasible(selected: Sequence[str], dependency_graph: DependencyGraph | None) -> tuple[bool, list[str]]:
    if dependency_graph is None:
        return True, []
    return selection_feasible(selected, dependency_graph)


def within_capacity(total_time: float, total_cost: float, total_manpower: float, capacities: Dict[str, float]) -> bool:
    return (
        total_time <= capacities.get("maintenance_window_hours", total_time)
        and total_cost <= capacities.get("budget", total_cost)
        and total_manpower <= capacities.get("manpower", total_manpower)
    )
