"""Custom dataset generation with intelligent field completion."""

from __future__ import annotations

import random
from typing import Any, Dict, List

import pandas as pd


def generate_placeholder_fields(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate missing fields intelligently based on user input.
    
    User only needs to provide:
    - patch_id, patch_name
    - patch_cost
    - exposure_level (0-1)
    - internet_facing (bool)
    - asset_criticality (0-1)
    - Other critical fields
    
    This function auto-generates:
    - vuln_id, cve_id (derived)
    - Exploit probability/availability (derived from exposure)
    - Time estimates (derived from complexity)
    - Risk propagation fields
    """
    result = user_input.copy()
    
    # Extract key parameters
    patch_cost = float(result.get('patch_cost', 500))
    exposure = float(result.get('exposure_level', 0.5))
    internet_facing = bool(result.get('internet_facing', 0))
    asset_crit = float(result.get('asset_criticality', 0.5))
    
    # Generate IDs if not provided
    if 'vuln_id' not in result or not result['vuln_id']:
        patch_id = result.get('patch_id', 'PKG_001')
        result['vuln_id'] = f"VUL_{hash(patch_id) % 10000:04d}"
    
    if 'cve_id' not in result or not result['cve_id']:
        result['cve_id'] = f"CVE-2026-{random.randint(1000, 9999)}"
    
    # Asset info if not provided
    if 'asset_id' not in result or not result['asset_id']:
        result['asset_id'] = f"ASSET_{random.randint(1000, 9999):04d}"
    
    if 'asset_name' not in result or not result['asset_name']:
        result['asset_name'] = result.get('system_group', 'Server') + f"_{random.randint(1, 50):02d}"
    
    # System and service info
    if 'system_group' not in result or not result['system_group']:
        systems = ['Web Server', 'Database', 'Mail Server', 'DNS', 'Load Balancer', 'FTP Server']
        result['system_group'] = random.choice(systems)
    
    if 'service_name' not in result or not result['service_name']:
        result['service_name'] = result.get('system_group', 'Unknown').lower().replace(' ', '_')
    
    # CVSS score (0-10) - derived from exposure and criticality
    if 'cvss' not in result or not result['cvss']:
        cvss_score = (exposure * 0.4 + asset_crit * 0.4 + random.random() * 0.2) * 10
        result['cvss'] = round(min(9.9, max(3.0, cvss_score)), 1)
    
    # Exploit probability (higher if exposed)
    if 'exploit_probability' not in result or not result['exploit_probability']:
        base = 0.3 if internet_facing else 0.1
        result['exploit_probability'] = round(base + exposure * 0.5 + random.random() * 0.2, 2)
    
    # Exploit available (higher with exposure)
    if 'exploit_available' not in result or not result['exploit_available']:
        result['exploit_available'] = 1 if exposure > 0.6 and internet_facing else (1 if random.random() > 0.7 else 0)
    
    # Active exploitation (rare but possible)
    if 'active_exploitation' not in result or not result['active_exploitation']:
        result['active_exploitation'] = 1 if random.random() > 0.95 else 0
    
    # Data sensitivity (user should provide, default to asset criticality)
    if 'data_sensitivity' not in result or not result['data_sensitivity']:
        result['data_sensitivity'] = round(asset_crit * random.uniform(0.7, 1.0), 2)
    
    # Patch time in hours (derived from complexity and cost)
    if 'patch_time' not in result or not result['patch_time']:
        # More expensive patches typically take longer
        cost_factor = min(patch_cost / 5000, 1.0)
        base_time = 0.5 + cost_factor * 1.5
        result['patch_time'] = round(base_time + random.uniform(-0.2, 0.4), 1)
    
    # Manpower required (derived from time and cost)
    if 'manpower_required' not in result or not result['manpower_required']:
        time_hours = float(result.get('patch_time', 1.0))
        result['manpower_required'] = round(0.5 + time_hours * 0.5, 1)
    
    # Remediation effectiveness (how much it reduces risk)
    if 'remediation_effectiveness' not in result or not result['remediation_effectiveness']:
        cvss = float(result.get('cvss', 5.0))
        result['remediation_effectiveness'] = round(0.6 + cvss / 20, 2)
    
    # Patch failure risk (inverse to cost and time - more investment = safer)
    if 'patch_failure_risk' not in result or not result['patch_failure_risk']:
        cost_factor = min(patch_cost / 5000, 1.0)
        result['patch_failure_risk'] = round(0.1 + (1 - cost_factor) * 0.15, 2)
    
    # Disruption impact (high if internet-facing or critical)
    if 'disruption_impact' not in result or not result['disruption_impact']:
        impact = asset_crit * 0.5 + (0.5 if internet_facing else 0.2)
        result['disruption_impact'] = round(min(1.0, impact), 2)
    
    # Rollback complexity (medium default)
    if 'rollback_complexity' not in result or not result['rollback_complexity']:
        result['rollback_complexity'] = round(0.4 + random.uniform(-0.1, 0.2), 2)
    
    # Age in days (randomize patch age)
    if 'age_days' not in result or not result['age_days']:
        result['age_days'] = random.randint(1, 180)
    
    # Severity label (derived from CVSS)
    if 'severity_label' not in result or not result['severity_label']:
        cvss = float(result.get('cvss', 5.0))
        if cvss >= 9:
            result['severity_label'] = 'Critical'
        elif cvss >= 7:
            result['severity_label'] = 'High'
        elif cvss >= 4:
            result['severity_label'] = 'Medium'
        else:
            result['severity_label'] = 'Low'
    
    # SLA deadline (days remaining)
    if 'sla_deadline_days' not in result or not result['sla_deadline_days']:
        severity = result.get('severity_label', 'Medium')
        sla_map = {'Critical': 3, 'High': 7, 'Medium': 14, 'Low': 30}
        result['sla_deadline_days'] = sla_map.get(severity, 14)
    
    # Days open (time since vuln was discovered)
    if 'days_open' not in result or not result['days_open']:
        result['days_open'] = random.randint(1, 60)
    
    # Dependencies (patches that must be applied first)
    if 'dependencies' not in result or not result['dependencies']:
        result['dependencies'] = ''  # Empty list - user can specify
    
    # Conflicts (patches that cannot be applied together)
    if 'conflicts' not in result or not result['conflicts']:
        result['conflicts'] = ''  # Empty list - user can specify
    
    return result


def create_custom_dataset(patches_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create a DataFrame from user-provided patch data with auto-generated fields.
    
    Parameters:
    - patches_data: List of dictionaries with user input
    
    Returns:
    - DataFrame with all required columns
    """
    # Fill in missing fields for each patch
    completed_patches = []
    for patch_input in patches_data:
        completed = generate_placeholder_fields(patch_input)
        completed_patches.append(completed)
    
    # Create DataFrame
    df = pd.DataFrame(completed_patches)
    
    # Define column order matching required columns
    required_columns = [
        'vuln_id', 'cve_id', 'patch_id', 'patch_name',
        'asset_id', 'asset_name', 'system_group', 'service_name',
        'cvss', 'exploit_probability', 'exploit_available',
        'active_exploitation', 'asset_criticality', 'data_sensitivity',
        'exposure_level', 'internet_facing', 'patch_time', 'patch_cost',
        'manpower_required', 'remediation_effectiveness', 'patch_failure_risk',
        'disruption_impact', 'rollback_complexity', 'age_days', 'severity_label',
        'sla_deadline_days', 'days_open', 'dependencies', 'conflicts'
    ]
    
    # Add missing columns with defaults
    for col in required_columns:
        if col not in df.columns:
            if col in ['dependencies', 'conflicts']:
                df[col] = ''
            else:
                df[col] = 0
    
    # Reorder columns
    df = df[required_columns]
    
    # Ensure correct data types
    numeric_cols = [
        'cvss', 'exploit_probability', 'asset_criticality', 'data_sensitivity',
        'exposure_level', 'internet_facing', 'patch_time', 'patch_cost',
        'manpower_required', 'remediation_effectiveness', 'patch_failure_risk',
        'disruption_impact', 'rollback_complexity', 'age_days', 'sla_deadline_days',
        'days_open', 'active_exploitation', 'exploit_available'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df


def merge_with_existing(custom_df: pd.DataFrame, existing_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Merge custom dataset with existing data or return custom data if no existing.
    """
    if existing_df is None or existing_df.empty:
        return custom_df
    
    # Concatenate and reset index
    merged = pd.concat([existing_df, custom_df], ignore_index=True)
    
    # Remove duplicates by patch_id if any
    merged = merged.drop_duplicates(subset=['patch_id'], keep='last')
    
    return merged
