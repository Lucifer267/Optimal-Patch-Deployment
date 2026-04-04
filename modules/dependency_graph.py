"""Dependency and conflict graph utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Set

import networkx as nx
import pandas as pd

from modules.utils import parse_list_field


@dataclass
class DependencyGraph:
    graph: nx.DiGraph
    conflicts: Dict[str, Set[str]]


def build_dependency_graph(dataframe: pd.DataFrame) -> DependencyGraph:
    graph = nx.DiGraph()
    conflicts: Dict[str, Set[str]] = {}

    for _, row in dataframe.iterrows():
        patch_id = str(row["patch_id"])
        graph.add_node(patch_id)
        conflicts.setdefault(patch_id, set())
        for dependency in parse_list_field(row.get("dependencies", [])):
            dependency_id = str(dependency)
            graph.add_edge(dependency_id, patch_id)
        for conflict in parse_list_field(row.get("conflicts", [])):
            conflict_id = str(conflict)
            conflicts[patch_id].add(conflict_id)
            conflicts.setdefault(conflict_id, set()).add(patch_id)

    return DependencyGraph(graph=graph, conflicts=conflicts)


def detect_cycles(dependency_graph: DependencyGraph) -> List[List[str]]:
    return list(nx.simple_cycles(dependency_graph.graph)) if dependency_graph.graph.number_of_edges() else []


def topological_order(dependency_graph: DependencyGraph, selected_ids: Sequence[str] | None = None) -> List[str]:
    graph = dependency_graph.graph.copy()
    if selected_ids is not None:
        selected = {str(item) for item in selected_ids}
        graph = graph.subgraph([node for node in graph.nodes if node in selected]).copy()
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError(f"Dependency cycle detected: {list(nx.simple_cycles(graph))}")
    return list(nx.topological_sort(graph))


def dependency_closure(dependency_graph: DependencyGraph, patch_id: str) -> Set[str]:
    ancestors = nx.ancestors(dependency_graph.graph, patch_id)
    return {str(node) for node in ancestors} | {str(patch_id)}


def selection_feasible(selected_ids: Sequence[str], dependency_graph: DependencyGraph) -> tuple[bool, list[str]]:
    selected_set = {str(item) for item in selected_ids}
    issues: list[str] = []
    for patch_id in selected_set:
        predecessors = set(dependency_graph.graph.predecessors(patch_id))
        missing = predecessors - selected_set
        if missing:
            issues.append(f"{patch_id}: missing prerequisites {sorted(missing)}")
    for patch_id in selected_set:
        for conflict in dependency_graph.conflicts.get(patch_id, set()):
            if conflict in selected_set and patch_id < conflict:
                issues.append(f"{patch_id} conflicts with {conflict}")
    return (len(issues) == 0, issues)
