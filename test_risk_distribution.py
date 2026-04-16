#!/usr/bin/env python3
"""Test that different algorithm selections produce different risk distributions."""

import pandas as pd
import numpy as np

# Simulate two different algorithm selections
selected_patches_algo1 = [1, 5, 9, 12, 15, 18]  # 6 patches
selected_patches_algo2 = [2, 4, 7, 11, 14, 17, 20]  # 7 patches (different selection)

# Create sample patch data
data = {
    'patch_id': range(1, 21),
    'adjusted_patch_value': np.random.uniform(1, 10, 20),  # Risk values 1-10
}
df = pd.DataFrame(data)

print("=" * 60)
print("Testing Risk Distribution Calculation")
print("=" * 60)

def calculate_risk_distribution(df, selected_ids):
    """Calculate risk distribution for selected patches."""
    selected_df = df[df['patch_id'].isin(selected_ids)].copy()
    
    if len(selected_df) == 0:
        return {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    
    risks = selected_df["adjusted_patch_value"].values
    total_risk = risks.sum()
    
    if total_risk == 0:
        return {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    
    # Define severity thresholds (percentiles)
    p75 = float(pd.Series(risks).quantile(0.75))
    p50 = float(pd.Series(risks).quantile(0.50))
    p25 = float(pd.Series(risks).quantile(0.25))
    
    # Categorize selected patches by risk
    critical = selected_df[selected_df["adjusted_patch_value"] >= p75]["adjusted_patch_value"].sum()
    high = selected_df[(selected_df["adjusted_patch_value"] >= p50) & (selected_df["adjusted_patch_value"] < p75)]["adjusted_patch_value"].sum()
    medium = selected_df[(selected_df["adjusted_patch_value"] >= p25) & (selected_df["adjusted_patch_value"] < p50)]["adjusted_patch_value"].sum()
    low = selected_df[selected_df["adjusted_patch_value"] < p25]["adjusted_patch_value"].sum()
    
    return {
        "Critical": float(critical),
        "High": float(high),
        "Medium": float(medium),
        "Low": float(low),
    }

# Calculate distributions
dist1 = calculate_risk_distribution(df, selected_patches_algo1)
dist2 = calculate_risk_distribution(df, selected_patches_algo2)

print("\nAlgorithm 1 - Selected patches:", selected_patches_algo1)
print("  Risk values:", df[df['patch_id'].isin(selected_patches_algo1)]['adjusted_patch_value'].values)
print("  Distribution:", dist1)
print(f"  Total: {sum(dist1.values()):.2f}")

print("\nAlgorithm 2 - Selected patches:", selected_patches_algo2)
print("  Risk values:", df[df['patch_id'].isin(selected_patches_algo2)]['adjusted_patch_value'].values)
print("  Distribution:", dist2)
print(f"  Total: {sum(dist2.values()):.2f}")

print("\n" + "=" * 60)
if dist1 != dist2:
    print("✓ SUCCESS: Different selections produce DIFFERENT distributions!")
else:
    print("⚠ ISSUE: Same distribution despite different selections")
print("=" * 60)
