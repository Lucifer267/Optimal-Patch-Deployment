"""Text generation for selected and rejected patches."""

from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd


def _top_feature_reasons(row: pd.Series) -> list[str]:
    reasons: list[str] = []
    if row.get("exploit_available_component", 0.0) >= 0.5:
        reasons.append("exploit was available")
    if row.get("active_exploitation_component", 0.0) >= 0.5:
        reasons.append("active exploitation was detected")
    if row.get("asset_criticality_component", 0.0) >= 0.6:
        reasons.append("asset criticality was high")
    if row.get("data_sensitivity_component", 0.0) >= 0.6:
        reasons.append("data sensitivity was elevated")
    if row.get("time_decay_component", 0.0) >= 0.5:
        reasons.append("time decay had increased the risk")
    if row.get("sla_urgency_component", 0.0) >= 0.5:
        reasons.append("SLA deadline was close")
    if row.get("attacker_pressure_component", 0.0) >= 0.5:
        reasons.append("attacker pressure was high")
    return reasons


def explain_patch_decision(row: pd.Series, selected: bool, rejection_reason: str | None = None) -> str:
    reasons = _top_feature_reasons(row)
    base = (
        f"Selected because {', '.join(reasons[:3])}."
        if selected
        else f"Rejected because {'; '.join(reasons[:2]) or 'the score did not justify its resource use'}."
    )
    if not selected and rejection_reason:
        base += f" {rejection_reason}."
    if selected:
        base += f" Adjusted value {row.get('adjusted_patch_value', 0.0):.3f} exceeded its resource cost profile."
    return base


def build_explanation_map(dataframe: pd.DataFrame, selected_ids: Iterable[str], rejection_notes: Dict[str, str] | None = None) -> Dict[str, str]:
    selected_set = {str(item) for item in selected_ids}
    rejection_notes = rejection_notes or {}
    explanations: Dict[str, str] = {}
    for _, row in dataframe.iterrows():
        patch_id = str(row["patch_id"])
        explanations[patch_id] = explain_patch_decision(
            row,
            patch_id in selected_set,
            rejection_reason=rejection_notes.get(patch_id),
        )
    return explanations


def build_result_summary(selected_df: pd.DataFrame, rejected_df: pd.DataFrame) -> str:
    selected_risk = float(selected_df.get("adjusted_patch_value", pd.Series(dtype=float)).sum()) if not selected_df.empty else 0.0
    rejected_risk = float(rejected_df.get("adjusted_patch_value", pd.Series(dtype=float)).sum()) if not rejected_df.empty else 0.0
    return (
        f"Selected {len(selected_df)} patches with {selected_risk:.3f} contextual risk reduction. "
        f"Rejected {len(rejected_df)} patches representing {rejected_risk:.3f} deferred reduction."
    )
