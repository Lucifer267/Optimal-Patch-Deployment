"""Contextual cybersecurity risk scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

from modules.sla_engine import sla_urgency
from modules.utils import clamp


@dataclass
class RiskWeights:
    cvss: float = 0.18
    exploit_probability: float = 0.12
    exploit_available: float = 0.08
    active_exploitation: float = 0.10
    asset_criticality: float = 0.16
    data_sensitivity: float = 0.10
    exposure_level: float = 0.09
    time_decay: float = 0.10
    sla_urgency: float = 0.07
    failure_penalty: float = 0.14
    adversarial: float = 0.05


def _scale_0_to_1(value: float, scale: float = 10.0) -> float:
    return clamp(float(value) / scale, 0.0, 1.0)


def time_decay_component(age_days: float, half_life: float = 60.0) -> float:
    age = max(0.0, float(age_days))
    return clamp(float(1.0 - np.exp(-age / max(1.0, half_life))), 0.0, 1.0)


def attacker_pressure(row: pd.Series) -> float:
    exposure = clamp(float(row.get("exposure_level", 0.0)) / 5.0, 0.0, 1.0)
    internet = clamp(float(row.get("internet_facing", 0.0)), 0.0, 1.0)
    exploit_available_component = clamp(float(row.get("exploit_available", 0.0)), 0.0, 1.0)
    active = clamp(float(row.get("active_exploitation", 0.0)), 0.0, 1.0)
    return clamp(0.32 * exposure + 0.24 * internet + 0.25 * exploit_available_component + 0.19 * active, 0.0, 1.0)


def failure_penalty(row: pd.Series) -> float:
    failure_risk = clamp(float(row.get("patch_failure_risk", 0.0)), 0.0, 1.0)
    disruption = clamp(float(row.get("disruption_impact", 0.0)), 0.0, 1.0)
    rollback = clamp(float(row.get("rollback_complexity", 0.0)), 0.0, 1.0)
    return clamp(0.5 * failure_risk + 0.3 * disruption + 0.2 * rollback, 0.0, 1.0)


def risk_breakdown(row: pd.Series, weights: Dict[str, float], adversarial_mode: bool = False) -> Dict[str, float]:
    cvss_component = _scale_0_to_1(row.get("cvss", 0.0), 10.0)
    exploit_probability_component = clamp(float(row.get("exploit_probability", 0.0)), 0.0, 1.0)
    exploit_available_component = clamp(float(row.get("exploit_available", 0.0)), 0.0, 1.0)
    active_exploitation_component = clamp(float(row.get("active_exploitation", 0.0)), 0.0, 1.0)
    asset_criticality_component = clamp(float(row.get("asset_criticality", 0.0)) / 5.0, 0.0, 1.0)
    data_sensitivity_component = clamp(float(row.get("data_sensitivity", 0.0)) / 5.0, 0.0, 1.0)
    exposure_component = clamp(float(row.get("exposure_level", 0.0)) / 5.0, 0.0, 1.0)
    time_decay = time_decay_component(row.get("age_days", 0.0))
    sla_component = sla_urgency(row.get("days_open", 0.0), row.get("sla_deadline_days", 1.0))
    failure_component = failure_penalty(row)
    pressure = attacker_pressure(row) if adversarial_mode else 0.0

    base_risk = (
        weights.get("cvss", 0.18) * cvss_component
        + weights.get("exploit_probability", 0.12) * exploit_probability_component
        + weights.get("exploit_available", 0.08) * exploit_available_component
        + weights.get("active_exploitation", 0.10) * active_exploitation_component
        + weights.get("asset_criticality", 0.16) * asset_criticality_component
        + weights.get("data_sensitivity", 0.10) * data_sensitivity_component
        + weights.get("exposure_level", 0.09) * exposure_component
        + weights.get("time_decay", 0.10) * time_decay
        + weights.get("sla_urgency", 0.07) * min(sla_component, 1.0)
    )

    if adversarial_mode:
        base_risk += weights.get("adversarial", 0.05) * pressure

    failure_penalty_component = weights.get("failure_penalty", 0.14) * failure_component
    remediation_effectiveness = clamp(float(row.get("remediation_effectiveness", 0.0)), 0.0, 1.0)
    adjusted_value = max(base_risk * remediation_effectiveness - failure_penalty_component, 0.0)

    return {
        "normalized_cvss": cvss_component,
        "exploit_probability_component": exploit_probability_component,
        "exploit_available_component": exploit_available_component,
        "active_exploitation_component": active_exploitation_component,
        "asset_criticality_component": asset_criticality_component,
        "data_sensitivity_component": data_sensitivity_component,
        "exposure_component": exposure_component,
        "time_decay_component": time_decay,
        "sla_urgency_component": float(min(sla_component, 1.5)),
        "failure_penalty_component": failure_penalty_component,
        "attacker_pressure_component": pressure,
        "base_risk": float(base_risk),
        "adjusted_patch_value": float(adjusted_value),
    }


def score_dataset(dataframe: pd.DataFrame, weights: Dict[str, float], adversarial_mode: bool = False, sla_mode: bool = True) -> pd.DataFrame:
    scored = dataframe.copy()
    breakdown_rows = scored.apply(lambda row: risk_breakdown(row, weights, adversarial_mode), axis=1)
    breakdown_df = pd.DataFrame(list(breakdown_rows))
    scored = pd.concat([scored.reset_index(drop=True), breakdown_df], axis=1)
    scored["value_per_time"] = scored["adjusted_patch_value"] / scored["patch_time"].replace(0, 0.0001)
    scored["value_per_resource"] = scored["adjusted_patch_value"] / (
        scored["patch_time"] + scored["patch_cost"] / 10000.0 + scored["manpower_required"]
    ).replace(0, 0.0001)
    
    # Adjust priority scoring based on SLA mode
    if sla_mode:
        # SLA-Aware: Boost SLA urgency component weight to prioritize deadline-critical patches
        scored["priority_score"] = (
            scored["adjusted_patch_value"]
            + 0.30 * scored["sla_urgency_component"]  # Doubled from 0.15
            + 0.10 * scored["time_decay_component"]
            + 0.05 * scored["attacker_pressure_component"]
        )
    else:
        # Risk-Only: Focus purely on risk/impact without SLA consideration
        scored["priority_score"] = (
            scored["adjusted_patch_value"]
            + 0.05 * scored["sla_urgency_component"]  # Reduced from 0.15
            + 0.10 * scored["time_decay_component"]
            + 0.05 * scored["attacker_pressure_component"]
        )
    
    return scored
