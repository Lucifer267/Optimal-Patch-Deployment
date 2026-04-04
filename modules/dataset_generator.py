"""Synthetic cybersecurity patch dataset generation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_dataset(size: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    patch_ids = [f"P{index:03d}" for index in range(1, size + 1)]
    for index, patch_id in enumerate(patch_ids, start=1):
        if index == 1:
            dependencies = []
        else:
            dependencies = [patch_ids[rng.integers(0, index - 1)]] if rng.random() < 0.42 else []
        conflicts = []
        if index > 2 and rng.random() < 0.12:
            conflicts = [patch_ids[rng.integers(0, index - 1)]]
        asset_slot = int(rng.integers(1, max(4, size // 3) + 1))
        records.append(
            {
                "vuln_id": f"V{index:04d}",
                "cve_id": f"CVE-2025-{1000 + index:04d}",
                "patch_id": patch_id,
                "patch_name": f"Security Patch {index}",
                "asset_id": f"A{asset_slot:03d}",
                "asset_name": f"Asset {asset_slot}",
                "system_group": rng.choice(["ERP", "CRM", "OT", "Cloud", "Endpoints", "DataLake"]),
                "service_name": rng.choice(["Auth", "Payment", "Web", "Database", "API", "Gateway"]),
                "cvss": round(float(rng.uniform(4.0, 9.9)), 1),
                "exploit_probability": round(float(rng.uniform(0.15, 0.98)), 2),
                "exploit_available": int(rng.random() < 0.58),
                "active_exploitation": int(rng.random() < 0.28),
                "asset_criticality": int(rng.integers(1, 6)),
                "data_sensitivity": int(rng.integers(1, 6)),
                "exposure_level": int(rng.integers(1, 6)),
                "internet_facing": int(rng.random() < 0.52),
                "patch_time": round(float(rng.uniform(0.5, 7.5)), 1),
                "patch_cost": round(float(rng.uniform(250.0, 5500.0)), 2),
                "manpower_required": round(float(rng.uniform(0.5, 6.0)), 1),
                "remediation_effectiveness": round(float(rng.uniform(0.58, 0.99)), 2),
                "patch_failure_risk": round(float(rng.uniform(0.02, 0.42)), 2),
                "disruption_impact": round(float(rng.uniform(0.05, 0.65)), 2),
                "rollback_complexity": round(float(rng.uniform(0.05, 0.75)), 2),
                "age_days": int(rng.integers(1, 420)),
                "severity_label": rng.choice(["Low", "Medium", "High", "Critical"]),
                "sla_deadline_days": int(rng.integers(5, 45)),
                "days_open": int(rng.integers(0, 60)),
                "dependencies": "|".join(dependencies),
                "conflicts": "|".join(conflicts),
            }
        )
    return pd.DataFrame.from_records(records)


def write_dataset(path: str | Path, size: int, seed: int = 42) -> pd.DataFrame:
    dataframe = generate_dataset(size=size, seed=seed)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output, index=False)
    return dataframe
