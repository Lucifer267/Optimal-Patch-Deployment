"""Dependency-aware sequential patch scheduler."""

from __future__ import annotations

import heapq
from typing import List

import pandas as pd

from modules.dependency_graph import DependencyGraph


def build_schedule(
    selected_data: pd.DataFrame,
    dependency_graph: DependencyGraph,
    maintenance_window_hours: float,
) -> list[dict]:
    if selected_data.empty:
        return []

    selected_ids = {str(patch_id) for patch_id in selected_data["patch_id"].tolist()}
    graph = dependency_graph.graph.subgraph(selected_ids).copy()

    indegree = {node: 0 for node in graph.nodes}
    for source, target in graph.edges:
        indegree[target] = indegree.get(target, 0) + 1

    score_lookup = selected_data.set_index("patch_id")["priority_score"].to_dict()
    urgency_lookup = selected_data.set_index("patch_id")["sla_urgency_component"].to_dict()
    time_lookup = selected_data.set_index("patch_id")["patch_time"].to_dict()

    heap: list[tuple[float, float, str]] = []
    for node, degree in indegree.items():
        if degree == 0:
            heapq.heappush(heap, (-float(score_lookup.get(node, 0.0)), float(time_lookup.get(node, 0.0)), node))

    ordered: list[str] = []
    while heap:
        _, _, node = heapq.heappop(heap)
        ordered.append(node)
        for successor in graph.successors(node):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(
                    heap,
                    (-float(score_lookup.get(successor, 0.0)), float(time_lookup.get(successor, 0.0)), successor),
                )

    remaining = set(selected_ids) - set(ordered)
    if remaining:
        ordered.extend(sorted(remaining, key=lambda patch_id: (-score_lookup.get(patch_id, 0.0), patch_id)))

    schedule: list[dict] = []
    batch = 1
    batch_time = 0.0
    for position, patch_id in enumerate(ordered, start=1):
        patch_time = float(time_lookup.get(patch_id, 0.0))
        if batch_time + patch_time > maintenance_window_hours and batch_time > 0:
            batch += 1
            batch_time = 0.0
        batch_time += patch_time
        schedule.append(
            {
                "position": position,
                "batch": batch,
                "patch_id": patch_id,
                "priority_score": float(score_lookup.get(patch_id, 0.0)),
                "sla_urgency_component": float(urgency_lookup.get(patch_id, 0.0)),
                "patch_time": patch_time,
            }
        )
    return schedule
