"""CSV loading and dataset validation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from modules.utils import parse_bool, parse_list_field


REQUIRED_COLUMNS = [
    "vuln_id",
    "cve_id",
    "patch_id",
    "patch_name",
    "asset_id",
    "asset_name",
    "system_group",
    "service_name",
    "cvss",
    "exploit_probability",
    "exploit_available",
    "active_exploitation",
    "asset_criticality",
    "data_sensitivity",
    "exposure_level",
    "internet_facing",
    "patch_time",
    "patch_cost",
    "manpower_required",
    "remediation_effectiveness",
    "patch_failure_risk",
    "disruption_impact",
    "rollback_complexity",
    "age_days",
    "severity_label",
    "sla_deadline_days",
    "days_open",
    "dependencies",
    "conflicts",
]


def load_dataset(source: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        dataframe = source.copy()
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {source}")
        dataframe = pd.read_csv(path)

    dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]

    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    numeric_columns = [
        "cvss",
        "exploit_probability",
        "exploit_available",
        "active_exploitation",
        "asset_criticality",
        "data_sensitivity",
        "exposure_level",
        "internet_facing",
        "patch_time",
        "patch_cost",
        "manpower_required",
        "remediation_effectiveness",
        "patch_failure_risk",
        "disruption_impact",
        "rollback_complexity",
        "age_days",
        "sla_deadline_days",
        "days_open",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce").fillna(0.0)

    for column in ["exploit_available", "active_exploitation", "internet_facing"]:
        dataframe[column] = dataframe[column].apply(parse_bool)

    for column in ["dependencies", "conflicts"]:
        dataframe[column] = dataframe[column].apply(parse_list_field)

    dataframe["severity_label"] = dataframe["severity_label"].fillna("Unknown").astype(str)
    dataframe["patch_name"] = dataframe["patch_name"].fillna(dataframe["patch_id"]).astype(str)
    dataframe["patch_id"] = dataframe["patch_id"].astype(str)
    dataframe["asset_id"] = dataframe["asset_id"].astype(str)
    dataframe["asset_name"] = dataframe["asset_name"].astype(str)
    dataframe["system_group"] = dataframe["system_group"].astype(str)
    dataframe["service_name"] = dataframe["service_name"].astype(str)
    dataframe["cve_id"] = dataframe["cve_id"].astype(str)
    dataframe["vuln_id"] = dataframe["vuln_id"].astype(str)

    dataframe["patch_time"] = dataframe["patch_time"].clip(lower=0.05)
    dataframe["patch_cost"] = dataframe["patch_cost"].clip(lower=0.0)
    dataframe["manpower_required"] = dataframe["manpower_required"].clip(lower=0.1)
    dataframe["remediation_effectiveness"] = dataframe["remediation_effectiveness"].clip(lower=0.0, upper=1.0)
    dataframe["patch_failure_risk"] = dataframe["patch_failure_risk"].clip(lower=0.0, upper=1.0)
    dataframe["disruption_impact"] = dataframe["disruption_impact"].clip(lower=0.0, upper=1.0)
    dataframe["rollback_complexity"] = dataframe["rollback_complexity"].clip(lower=0.0, upper=1.0)
    dataframe["age_days"] = dataframe["age_days"].clip(lower=0.0)
    dataframe["sla_deadline_days"] = dataframe["sla_deadline_days"].clip(lower=1.0)
    dataframe["days_open"] = dataframe["days_open"].clip(lower=0.0)

    return dataframe.reset_index(drop=True)


def dataset_preview(dataframe: pd.DataFrame, rows: int = 5) -> list[dict[str, Any]]:
    return dataframe.head(rows).to_dict(orient="records")
