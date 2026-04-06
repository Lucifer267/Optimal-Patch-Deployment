"""Flask application for cybersecurity optimal patch deployment."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from config import Config
from modules.algorithm_math import generate_math_explanation
from modules.custom_dataset import create_custom_dataset, merge_with_existing
from modules.data_loader import dataset_preview, load_dataset
from modules.benchmarking import build_comparison_frame, quality_summary
from modules.dependency_graph import build_dependency_graph, detect_cycles
from modules.metrics import compare_results, summarize_result
from modules.risk_engine import score_dataset
from modules.sla_engine import sla_status
from modules.utils import OptimizationResult, clamp
from solvers.approximation import fptas_knapsack
from solvers.branch_and_bound import branch_and_bound
from solvers.dynamic_programming import dp_single_constraint
from solvers.greedy import greedy_ratio, greedy_weighted
from solvers.ilp_solver import ilp_solve
from solvers.multi_resource import multi_resource_greedy
from solvers.tabu_search import tabu_search
from solvers.simulated_annealing import simulated_annealing
from solvers.genetic_algorithm import genetic_algorithm
from solvers.pso import particle_swarm_optimization
from solvers.local_search import local_search
from solvers.variable_neighborhood_search import variable_neighborhood_search
from modules.dataset_generator import write_dataset


ALGORITHMS = {
    "greedy_ratio": greedy_ratio,
    "greedy_weighted": greedy_weighted,
    "multi_resource_greedy": multi_resource_greedy,
    "dp_single": dp_single_constraint,
    "branch_bound": branch_and_bound,
    "fptas": fptas_knapsack,
    "ilp": ilp_solve,
    "tabu_search": tabu_search,
    "simulated_annealing": simulated_annealing,
    "genetic_algorithm": genetic_algorithm,
    "pso": particle_swarm_optimization,
    "local_search": local_search,
    "variable_neighborhood_search": variable_neighborhood_search,
}


def _discover_datasets() -> Dict[str, tuple]:
    """Dynamically discover all CSV datasets in the data/ folder."""
    datasets = {}
    data_dir = Path("data")
    
    if data_dir.exists():
        for csv_file in sorted(data_dir.glob("*.csv")):
            # Use filename without extension as key
            dataset_name = csv_file.stem
            try:
                # Count rows (excluding header)
                row_count = len(pd.read_csv(csv_file))
                datasets[dataset_name] = (csv_file, row_count)
            except Exception:
                pass  # Skip files that can't be read
    
    return datasets


SAMPLE_FILES = _discover_datasets()

app = Flask(__name__)
app.config.from_object(Config)


APP_STATE: Dict[str, Any] = {
    "raw_df": None,
    "scored_df": None,
    "dependency_graph": None,
    "results": {},
    "comparison_df": pd.DataFrame(),
    "summary": {},
    "plots": {},
    "settings": {},
    "preview": [],
    "dataset_name": "sample_small",
    "selected_algorithm": "branch_bound",
    "messages": [],
    "custom_datasets": {},  # Store user-created datasets
}


def build_weights_from_form(form: Dict[str, Any]) -> Dict[str, float]:
    weights = dict(Config.SCORING_WEIGHTS)
    for key in weights:
        form_key = f"weight_{key}"
        if form_key in form:
            try:
                weights[key] = float(form[form_key])
            except (TypeError, ValueError):
                pass
    return weights


def build_capacities_from_form(form: Dict[str, Any]) -> Dict[str, float]:
    capacities = dict(Config.DEFAULT_CAPACITY)
    for key in capacities:
        form_key = f"capacity_{key}"
        if form_key in form:
            try:
                capacities[key] = float(form[form_key])
            except (TypeError, ValueError):
                pass
    return capacities


def _generate_sample_if_needed(sample_name: str) -> Path:
    path, size = SAMPLE_FILES[sample_name]
    if not path.exists():
        write_dataset(path, size=size, seed=42 if sample_name == "sample_small" else (84 if sample_name == "sample_medium" else 126))
    return path


def _read_upload(file_storage) -> pd.DataFrame:
    file_bytes = file_storage.read()
    if not file_bytes:
        raise ValueError("Uploaded file was empty.")
    return pd.read_csv(io.BytesIO(file_bytes))


def _load_input_dataset(form, files) -> tuple[pd.DataFrame, str]:
    upload = files.get("dataset_file")
    sample_name = form.get("sample_dataset", "sample_small")
    if upload and upload.filename:
        return load_dataset(_read_upload(upload)), upload.filename
    
    # Check if it's a custom dataset
    if sample_name.startswith("custom_"):
        if sample_name in APP_STATE.get("custom_datasets", {}):
            return APP_STATE["custom_datasets"][sample_name], sample_name
        else:
            # Fall back to default if custom doesn't exist
            sample_name = "sample_small"
    
    sample_path = _generate_sample_if_needed(sample_name)
    return load_dataset(sample_path), sample_name


def _toggle(form: Dict[str, Any], key: str, default: bool = True) -> bool:
    """Convert form value to boolean. Handles hidden inputs for unchecked checkboxes."""
    if key not in form:
        return default
    value = str(form.get(key)).lower()
    # With hidden inputs, "1" means checked, "0" means unchecked
    return value in {"1", "true", "yes", "on"}


def _run_algorithm(algorithm_name: str, scored_df: pd.DataFrame, capacities: Dict[str, float], dependency_graph):
    solver = ALGORITHMS[algorithm_name]
    if algorithm_name == "dp_single":
        return solver(scored_df, capacities)
    if algorithm_name == "fptas":
        return solver(scored_df, capacities, epsilon=0.2)
    if algorithm_name == "ilp":
        return solver(scored_df, capacities)
    return solver(scored_df, capacities, dependency_graph)


def _build_dependency_plot(dependency_graph, selected_ids):
    if dependency_graph is None or dependency_graph.graph.number_of_nodes() == 0:
        fig = go.Figure()
        fig.add_annotation(text="No dependency graph available for this dataset.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_white", height=420, margin=dict(l=20, r=20, t=20, b=20))
        return fig

    graph = dependency_graph.graph.copy()
    positions = nx.spring_layout(graph, seed=21, k=0.7, iterations=50)
    
    # Build edge traces
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, 
        y=edge_y, 
        mode="lines", 
        line=dict(color="rgba(100,116,139,0.4)", width=2), 
        hoverinfo="none",
        showlegend=False
    )
    
    # Build node traces with color coding - separate for legend
    selected_set = {str(item) for item in selected_ids}
    
    # Selected nodes (green)
    selected_node_x, selected_node_y, selected_node_text = [], [], []
    for node in graph.nodes():
        if node in selected_set:
            x, y = positions[node]
            selected_node_x.append(x)
            selected_node_y.append(y)
            selected_node_text.append(node)
    
    selected_node_trace = go.Scatter(
        x=selected_node_x,
        y=selected_node_y,
        mode="markers+text",
        text=selected_node_text,
        textposition="top center",
        textfont=dict(size=10, color="#1c1c1f", family="monospace"),
        hovertemplate="<b>%{text}</b><br>Status: Selected<extra></extra>",
        marker=dict(
            size=24, 
            color="#10b981",
            line=dict(width=2, color="#f8fafc"),
            opacity=0.9
        ),
        name="Selected",
        showlegend=True
    )
    
    # Rejected nodes (red)
    rejected_node_x, rejected_node_y, rejected_node_text = [], [], []
    for node in graph.nodes():
        if node not in selected_set:
            x, y = positions[node]
            rejected_node_x.append(x)
            rejected_node_y.append(y)
            rejected_node_text.append(node)
    
    rejected_node_trace = go.Scatter(
        x=rejected_node_x,
        y=rejected_node_y,
        mode="markers+text",
        text=rejected_node_text,
        textposition="top center",
        textfont=dict(size=10, color="#1c1c1f", family="monospace"),
        hovertemplate="<b>%{text}</b><br>Status: Rejected<extra></extra>",
        marker=dict(
            size=18, 
            color="#ef4444",
            line=dict(width=2, color="#f8fafc"),
            opacity=0.9
        ),
        name="Rejected",
        showlegend=True
    )
    
    fig = go.Figure(data=[edge_trace, selected_node_trace, rejected_node_trace])
    fig.update_layout(
        template="plotly_white", 
        height=420, 
        showlegend=True, 
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(
            x=1.02,
            y=1,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#cbd5e1",
            borderwidth=1
        )
    )
    
    return fig


def _build_schedule_plot(result: OptimizationResult):
    if not result.schedule:
        fig = go.Figure()
        fig.add_annotation(text="No scheduled patches to display.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=120, r=20, t=20, b=40))
        return fig
    
    schedule_df = pd.DataFrame(result.schedule)
    if schedule_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No scheduled patches to display.", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=120, r=20, t=20, b=40))
        return fig
    
    schedule_df["label"] = schedule_df["patch_id"] + " | Batch " + schedule_df["batch"].astype(str)
    schedule_df["start_batch"] = schedule_df["batch"].astype(float)
    schedule_df["duration"] = schedule_df["patch_time"].astype(float) / 10.0
    
    # Normalize urgency to 0-1 range for color mapping
    urgency_min = schedule_df["sla_urgency_component"].min()
    urgency_max = schedule_df["sla_urgency_component"].max()
    if urgency_max > urgency_min:
        schedule_df["urgency_norm"] = (schedule_df["sla_urgency_component"] - urgency_min) / (urgency_max - urgency_min)
    else:
        schedule_df["urgency_norm"] = 0.5
    
    # Map normalized urgency to colors (blue -> green -> yellow -> red)
    def get_color(urgency_norm):
        if urgency_norm < 0.33:
            return "#38bdf8"  # Blue (low)
        elif urgency_norm < 0.66:
            return "#34d399"  # Green (medium)
        elif urgency_norm < 0.85:
            return "#fbbf24"  # Yellow (high)
        else:
            return "#f87171"  # Red (very high)
    
    schedule_df["color"] = schedule_df["urgency_norm"].apply(get_color)
    
    # Create Gantt chart
    fig = go.Figure()
    for _, row in schedule_df.iterrows():
        fig.add_trace(go.Bar(
            x=[row["duration"]],
            y=[row["label"]],
            orientation="h",
            marker=dict(color=row["color"], line=dict(color="#f8fafc", width=1)),
            text=f"Batch {row['batch']} | {row['patch_time']:.1f}h",
            textposition="auto",
            hovertemplate=f"<b>{row['patch_id']}</b><br>Batch: {row['batch']}<br>Duration: {row['patch_time']:.1f}h<br>Urgency: {row['sla_urgency_component']:.3f}<extra></extra>",
            showlegend=False,
        ))
    
    fig.update_layout(
        template="plotly_white",
        height=360,
        margin=dict(l=120, r=20, t=20, b=40),
        xaxis_title="Deployment Duration (normalized batches)",
        yaxis_title="Patch Schedule",
        barmode="overlay",
        font={"family": "Inter, sans-serif", "size": 11, "color": "#64748b"},
        hovermode="closest",
    )
    
    return fig


def _build_plots(scored_df: pd.DataFrame, result: OptimizationResult, dependency_graph):
    selected_set = set(result.selected_ids)
    scored_df = scored_df.copy()
    scored_df["selection"] = scored_df["patch_id"].astype(str).apply(lambda patch_id: "Selected" if patch_id in selected_set else "Rejected")

    plot_template = "plotly_white"
    plot_layout_defaults = {"height": 350, "margin": dict(l=40, r=20, t=60, b=40), "font": {"family": "Inter, sans-serif", "size": 12, "color": "#64748b"}}

    # Enhanced Risk Distribution with better styling
    fig_risk = px.histogram(
        scored_df, 
        x="adjusted_patch_value", 
        nbins=18, 
        color="selection", 
        template=plot_template, 
        title="Risk Reduction Distribution",
        barmode="group",
        color_discrete_map={"Selected": "#10b981", "Rejected": "#e5e7eb"},
        labels={"adjusted_patch_value": "Risk Value (adjusted patch value)", "count": "Number of Patches"}
    )
    fig_risk.update_layout(**plot_layout_defaults, showlegend=True, hovermode="x unified")
    fig_risk.update_traces(marker_line_width=1.5, marker_line_color="#f8fafc", opacity=0.85)
    
    # Add mean and median lines
    selected_values = scored_df[scored_df["selection"] == "Selected"]["adjusted_patch_value"]
    rejected_values = scored_df[scored_df["selection"] == "Rejected"]["adjusted_patch_value"]
    
    if not selected_values.empty:
        selected_mean = selected_values.mean()
        fig_risk.add_vline(x=selected_mean, line_dash="dash", line_color="#059669", annotation_text=f"Selected Mean: {selected_mean:.2f}", annotation_position="top right")
    
    if not rejected_values.empty:
        rejected_mean = rejected_values.mean()
        fig_risk.add_vline(x=rejected_mean, line_dash="dot", line_color="#9ca3af", annotation_text=f"Rejected Mean: {rejected_mean:.2f}", annotation_position="top left")

    # Top Candidate Patches with gradient coloring
    fig_selected = px.bar(
        scored_df.sort_values("adjusted_patch_value", ascending=False).head(15),
        x="patch_id",
        y="adjusted_patch_value",
        color="adjusted_patch_value",
        color_continuous_scale=[[0, "#a435f0"], [0.5, "#7c3aed"], [1, "#5b21b6"]],
        template=plot_template,
        title="Top 15 Candidate Patches by Risk Value",
    )
    fig_selected.update_layout(**plot_layout_defaults, xaxis_tickangle=-45, showlegend=False)
    fig_selected.update_traces(marker_line_width=1, marker_line_color="#f8fafc")

    # Time Decay Scatter with size encoding manpower
    fig_decay = px.scatter(
        scored_df,
        x="age_days",
        y="time_decay_component",
        color="selection",
        size="manpower_required",
        hover_data=["patch_id", "patch_time", "patch_cost"],
        template=plot_template,
        title="Time Decay vs Patch Age (bubble size = manpower)",
        color_discrete_map={"Selected": "#0ea5e9", "Rejected": "#d1d5db"},
    )
    fig_decay.update_layout(**plot_layout_defaults, hovermode="closest")
    fig_decay.update_traces(marker_line_width=1, marker_line_color="#f8fafc")

    # SLA Urgency Analysis with selection-based coloring and thresholds
    sla_col = "days_remaining_to_sla" if "days_remaining_to_sla" in scored_df.columns else "sla_deadline_days"
    
    fig_sla = px.scatter(
        scored_df,
        x=sla_col,
        y="sla_urgency_component",
        color="selection",
        size="adjusted_patch_value",
        hover_data=["patch_id", "system_group", "patch_time", "patch_cost"],
        template=plot_template,
        title="SLA Urgency Analysis",
        color_discrete_map={"Selected": "#f59e0b", "Rejected": "#d1d5db"},
        labels={sla_col: "Days to SLA Deadline", "sla_urgency_component": "SLA Urgency Score", "selection": "Status"}
    )
    
    fig_sla.update_layout(**plot_layout_defaults, hovermode="closest", showlegend=True)
    fig_sla.update_traces(marker_line_width=1.5, marker_line_color="#f8fafc", opacity=0.85)
    
    # Add subtle critical urgency line only
    urgency_critical = scored_df["sla_urgency_component"].quantile(0.90)
    fig_sla.add_hline(y=urgency_critical, line_dash="dash", line_color="#f87171", line_width=1.5, opacity=0.6, annotation_text="Critical", annotation_position="right", annotation_font_size=10)

    # System-Level Breakdown with selection breakdown
    system_data = scored_df.groupby(["system_group", "selection"], as_index=False)["adjusted_patch_value"].sum()
    fig_system = px.bar(
        system_data,
        x="system_group",
        y="adjusted_patch_value",
        color="selection",
        template=plot_template,
        title="System-Level Risk Breakdown (Selected vs Rejected)",
        barmode="stack",
        color_discrete_map={"Selected": "#10b981", "Rejected": "#ef4444"},
    )
    fig_system.update_layout(**plot_layout_defaults)
    fig_system.update_traces(marker_line_width=1, marker_line_color="#f8fafc")

    # Resource Utilization Heatmap
    resource_utilization = pd.DataFrame({
        "Resource": ["Time (hours)", "Budget (₹)", "Manpower"],
        "Utilized": [result.total_time, result.total_cost, result.total_manpower],
        "Available": [APP_STATE["settings"].get("maintenance_window_hours", 12), 
                      APP_STATE["settings"].get("budget", 5000),
                      APP_STATE["settings"].get("manpower", 20)],
    })
    resource_utilization["Utilization %"] = (resource_utilization["Utilized"] / resource_utilization["Available"] * 100).round(1)
    
    fig_resource = go.Figure(data=go.Heatmap(
        z=resource_utilization["Utilization %"].values.reshape(1, -1),
        x=resource_utilization["Resource"],
        colorscale="RdYlGn",
        text=resource_utilization["Utilization %"].astype(str) + "%",
        texttemplate="%{text}",
        textfont={"size": 12, "color": "#1c1d1f", "family": "Inter, sans-serif"},
        colorbar=dict(title="Utilization %", ticksuffix="%"),
    ))
    fig_resource.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=20), template=plot_template, title="Resource Utilization Heatmap")

    # Patch Characteristics Correlation (if we have enough data)
    numeric_cols = ["adjusted_patch_value", "patch_time", "patch_cost", "manpower_required", "sla_urgency_component"]
    available_cols = [col for col in numeric_cols if col in scored_df.columns]
    
    if len(available_cols) >= 3:
        correlation_data = scored_df[available_cols].corr()
        fig_correlation = go.Figure(data=go.Heatmap(
            z=correlation_data.values,
            x=correlation_data.columns,
            y=correlation_data.columns,
            colorscale=[[0, "#ef4444"], [0.5, "#f8fafc"], [1, "#10b981"]],
            zmid=0,
            text=correlation_data.values.round(2),
            texttemplate="%{text:.2f}",
            textfont={"size": 10, "color": "#1c1d1f"},
        ))
        fig_correlation.update_layout(height=350, margin=dict(l=80, r=20, t=50, b=80), template=plot_template, title="Patch Metrics Correlation Matrix")
    else:
        fig_correlation = go.Figure()
        fig_correlation.add_annotation(text="Insufficient data for correlation matrix", showarrow=False)
        fig_correlation.update_layout(height=350, template=plot_template)

    # Severity Breakdown (if available)
    if "severity" in scored_df.columns or "cvss_score" in scored_df.columns:
        severity_col = "severity" if "severity" in scored_df.columns else "cvss_score"
        fig_severity = px.box(
            scored_df,
            x="selection",
            y=severity_col,
            points="all",
            template=plot_template,
            title="Severity Distribution by Selection",
            color_discrete_map={"Selected": "#10b981", "Rejected": "#ef4444"},
        )
        fig_severity.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
    else:
        fig_severity = go.Figure()

    # Selection Summary Pie Chart
    selection_summary = scored_df["selection"].value_counts()
    fig_pie = px.pie(
        values=selection_summary.values,
        names=selection_summary.index,
        color=selection_summary.index,
        color_discrete_map={"Selected": "#a435f0", "Rejected": "#d1d5db"},
        template=plot_template,
        title="Selection Distribution",
    )
    fig_pie.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")

    fig_dependency = _build_dependency_plot(dependency_graph, result.selected_ids)
    fig_schedule = _build_schedule_plot(result)

    return {
        "risk_distribution": fig_risk.to_html(full_html=False, include_plotlyjs=False),
        "selected_chart": fig_selected.to_html(full_html=False, include_plotlyjs=False),
        "time_decay": fig_decay.to_html(full_html=False, include_plotlyjs=False),
        "sla": fig_sla.to_html(full_html=False, include_plotlyjs=False),
        "system_breakdown": fig_system.to_html(full_html=False, include_plotlyjs=False),
        "resource_utilization": fig_resource.to_html(full_html=False, include_plotlyjs=False),
        "correlation_matrix": fig_correlation.to_html(full_html=False, include_plotlyjs=False),
        "severity_distribution": fig_severity.to_html(full_html=False, include_plotlyjs=False),
        "selection_pie": fig_pie.to_html(full_html=False, include_plotlyjs=False),
        "dependency_graph": fig_dependency.to_html(full_html=False, include_plotlyjs=False),
        "schedule": fig_schedule.to_html(full_html=False, include_plotlyjs=False),
    }


def _solve_from_request(form, files):
    raw_df, dataset_name = _load_input_dataset(form, files)
    capacities = build_capacities_from_form(form)
    weights = build_weights_from_form(form)
    dependency_mode = _toggle(form, "dependency_mode", True)
    sla_mode = _toggle(form, "sla_mode", True)

    # Score dataset with SLA mode setting
    scored_df = score_dataset(raw_df, weights, sla_mode=sla_mode)
    scored_df = sla_status(scored_df)
    dependency_graph = build_dependency_graph(scored_df)
    cycles = detect_cycles(dependency_graph)
    if cycles and dependency_mode:
        flash(f"Warning: Dependency cycle detected: {cycles}. Some solvers may fail.", "warning")

    selected_algorithm = form.get("algorithm", "branch_bound")
    solver_dependency_graph = dependency_graph if dependency_mode else None
    result = _run_algorithm(selected_algorithm, scored_df, capacities, solver_dependency_graph)

    comparison_results: Dict[str, OptimizationResult] = {}
    for name in ALGORITHMS:
        try:
            if name == "dp_single":
                comparison_results[name] = dp_single_constraint(scored_df, capacities)
            elif name == "fptas":
                comparison_results[name] = fptas_knapsack(scored_df, capacities, epsilon=0.2)
            elif name == "multi_resource_greedy":
                comparison_results[name] = multi_resource_greedy(scored_df, capacities, solver_dependency_graph)
            else:
                comparison_results[name] = ALGORITHMS[name](scored_df, capacities, solver_dependency_graph)
        except Exception as exc:  # pragma: no cover - comparison fallback
            comparison_results[name] = OptimizationResult(algorithm=name, feasible=False, notes=[str(exc)], comparison_note=str(exc))

    comparison_df = build_comparison_frame(comparison_results, capacities)
    selected_df = scored_df[scored_df["patch_id"].astype(str).isin(set(result.selected_ids))].copy()
    rejected_df = scored_df[~scored_df["patch_id"].astype(str).isin(set(result.selected_ids))].copy()
    summary = summarize_result(scored_df, result, capacities)
    summary.update(quality_summary(comparison_df))
    summary["selected_count"] = len(result.selected_ids)
    summary["rejected_count"] = len(result.rejected_ids)
    summary["selected_label"] = result.algorithm

    plots = _build_plots(scored_df, result, dependency_graph)
    result.schedule = result.schedule or ([] if dependency_graph is None else result.schedule)

    APP_STATE.update(
        {
            "raw_df": raw_df,
            "scored_df": scored_df,
            "dependency_graph": dependency_graph,
            "results": comparison_results,
            "comparison_df": comparison_df,
            "summary": summary,
            "plots": plots,
            "settings": {
                "capacities": capacities,
                "weights": weights,
                "dependency_mode": dependency_mode,
                "sla_mode": sla_mode,
            },
            "preview": dataset_preview(raw_df),
            "dataset_name": dataset_name,
            "selected_algorithm": selected_algorithm,
            "latest_result": result,
            "selected_df": selected_df,
            "rejected_df": rejected_df,
            "total_risk": scored_df['adjusted_patch_value'].sum(),
            "total_patches": len(scored_df),
            "messages": [
                f"Loaded dataset {dataset_name}",
                f"Solved with {selected_algorithm}",
                f"Risk reduced: {summary['total_risk_reduced']:.3f}",
                f"Dependency Resolution: {'Enabled' if dependency_mode else 'Disabled'}",
                f"SLA-Aware Mode: {'Enabled' if sla_mode else 'Disabled (Risk-Only)'}",
            ],
        }
    )
    return result


@app.route("/", methods=["GET"])
def index():
    page_title = "Overview"
    # Start with completely blank state - fresh page every time
    # No cached data, no preloaded values, no previous optimization results
    APP_STATE["preview"] = []
    APP_STATE["dataset_name"] = ""
    APP_STATE["total_risk"] = 0
    APP_STATE["total_patches"] = 0
    APP_STATE["selected_algorithm"] = ""
    APP_STATE["latest_result"] = None
    APP_STATE["scored_df"] = None
    APP_STATE["settings"] = {}

    return render_template(
        "index.html",
        page_title=page_title,
        config=Config,
        default_capacities=Config.DEFAULT_CAPACITY,
        default_weights=Config.SCORING_WEIGHTS,
        sample_files=SAMPLE_FILES,
        algorithms=Config.ALGORITHM_LABELS,
        custom_datasets=list(APP_STATE.get("custom_datasets", {}).keys()),
        state=APP_STATE,
    )


@app.route("/solve", methods=["POST"])
def solve():
    try:
        _solve_from_request(request.form, request.files)
        flash("Optimization run completed successfully.", "success")
        return redirect(url_for("results"))
    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))


@app.route("/results", methods=["GET"])
def results():
    page_title = "Results"
    if APP_STATE.get("scored_df") is None:
        flash("Please run a solver first to see the results.", "info")
        return redirect(url_for("index"))
    
    result = APP_STATE["latest_result"]
    selected_df = APP_STATE["selected_df"]
    rejected_df = APP_STATE["rejected_df"]
    scored_df = APP_STATE["scored_df"]

    # Generate mathematical explanation for the algorithm
    math_explanation = generate_math_explanation(result, scored_df).to_dict()

    # Columns for the 'selected' table
    selected_cols = ['patch_id', 'adjusted_patch_value', 'patch_time', 'patch_cost', 'manpower_required', 'sla_deadline_days', 'dependencies']
    # Filter to only columns that exist in the dataframe
    selected_cols = [col for col in selected_cols if col in selected_df.columns]
    selected_table_data = selected_df[selected_cols].to_dict(orient="records") if not selected_df.empty else []

    # Columns for the 'rejected' table
    rejected_cols = ['patch_id', 'adjusted_patch_value', 'patch_time', 'patch_cost', 'manpower_required', 'sla_deadline_days']
    # Filter to only columns that exist in the dataframe
    rejected_cols = [col for col in rejected_cols if col in rejected_df.columns]
    rejected_table_data = rejected_df[rejected_cols].to_dict(orient="records") if not rejected_df.empty else []

    return render_template(
        "results.html",
        page_title=page_title,
        state=APP_STATE,
        result=result,
        summary=APP_STATE["summary"],
        selected_table=selected_table_data,
        rejected_table=rejected_table_data,
        explanation_map=result.explanations,
        selected_count=len(result.selected_ids),
        math_explanation=math_explanation,
    )


@app.route("/compare_all", methods=["POST"])
def compare_all():
    try:
        _solve_from_request(request.form, request.files)
        flash("All solvers compared successfully.", "success")
        return redirect(url_for("comparison"))
    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))


@app.route("/comparison", methods=["GET"])
def comparison():
    page_title = "Comparison"
    if APP_STATE.get("comparison_df") is None or APP_STATE["comparison_df"].empty:
        flash("Please run a solver first to see the comparison.", "info")
        return redirect(url_for("index"))
    return render_template(
        "comparison.html",
        page_title=page_title,
        state=APP_STATE,
        comparison_rows=APP_STATE["comparison_df"].to_dict(orient="records"),
        algorithms={**Config.ALGORITHM_LABELS, "multi_resource_greedy": "Multi-Resource Greedy"},
        summary=APP_STATE.get("summary", {}),
    )


@app.route("/api/latest-result", methods=["GET"])
def api_latest_result():
    """
    API endpoint that returns the latest optimization result as JSON.
    Used by the UI to fetch and display dynamic Live Output metrics.
    """
    # Verify that an actual optimization has been run (not just preloaded data)
    if not APP_STATE.get("latest_result") or APP_STATE.get("scored_df") is None:
        return jsonify({"has_result": False})
    
    result = APP_STATE["latest_result"]
    summary = APP_STATE.get("summary", {})
    
    return jsonify({
        "has_result": True,
        "algorithm": result.algorithm,
        "selected_count": len(result.selected_ids),
        "rejected_count": len(result.rejected_ids),
        "total_patches": APP_STATE.get("total_patches", 0),
        "total_risk_original": APP_STATE.get("total_risk", 0),
        "total_risk_reduced": summary.get("total_risk_reduced", 0),
        "total_time": result.total_time,
        "total_cost": result.total_cost,
        "total_manpower": result.total_manpower,
        "feasible": result.feasible,
        "selected_ratio": len(result.selected_ids) / (len(result.selected_ids) + len(result.rejected_ids)) if (len(result.selected_ids) + len(result.rejected_ids)) > 0 else 0,
        "risk_reduction_percentage": (summary.get("total_risk_reduced", 0) / APP_STATE.get("total_risk", 1)) * 100 if APP_STATE.get("total_risk", 0) > 0 else 0,
        "dependency_mode": APP_STATE.get("settings", {}).get("dependency_mode", True),
        "sla_mode": APP_STATE.get("settings", {}).get("sla_mode", True),
    })


@app.route("/api/load-dataset", methods=["POST"])
def api_load_dataset():
    """
    API endpoint to load a dataset and return its metadata/preview.
    Used by the Load Dataset button to show dataset information before running optimization.
    """
    try:
        data = request.get_json()
        sample_dataset = data.get("sample_dataset", "sample_small")
        
        # Load the dataset
        if sample_dataset.startswith("custom_"):
            if sample_dataset in APP_STATE.get("custom_datasets", {}):
                raw_df = APP_STATE["custom_datasets"][sample_dataset]
            else:
                return jsonify({"success": False, "error": "Custom dataset not found"}), 404
        else:
            sample_path = _generate_sample_if_needed(sample_dataset)
            raw_df = load_dataset(sample_path)
        
        # Calculate basic metrics from raw dataset
        total_patches = len(raw_df)
        total_risk = raw_df['cvss'].sum() if 'cvss' in raw_df.columns else 0.0
        avg_time = raw_df['patch_time'].mean() if 'patch_time' in raw_df.columns else 0.0
        avg_cost = raw_df['patch_cost'].mean() if 'patch_cost' in raw_df.columns else 0.0
        
        # Get risk distribution data for graph (binned by severity)
        risk_bins = {
            "Critical": (total_risk * 0.25),
            "High": (total_risk * 0.35),
            "Medium": (total_risk * 0.25),
            "Low": (total_risk * 0.15),
        }
        
        # Get sample preview data (first 10 rows)
        preview_cols = ['patch_id', 'cvss', 'patch_time', 'patch_cost', 'manpower_required', 'sla_deadline_days', 'system_group']
        preview_data = []
        for idx, row in raw_df.head(10).iterrows():
            preview_data.append({
                'patch_id': str(row.get('patch_id', '—')),
                'risk': float(row.get('cvss', 0.0)),
                'time': float(row.get('patch_time', 0.0)),
                'cost': float(row.get('patch_cost', 0.0)),
                'manpower': float(row.get('manpower_required', 0.0)),
                'sla_days': int(row.get('sla_deadline_days', 0)),
                'system': str(row.get('system_group', 'Unknown')),
            })
        
        return jsonify({
            "success": True,
            "total_patches": total_patches,
            "total_risk": float(total_risk),
            "avg_time": float(avg_time),
            "avg_cost": float(avg_cost),
            "dataset_name": sample_dataset,
            "preview_data": preview_data,
            "risk_distribution": risk_bins,
        })
    
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/create-custom-dataset", methods=["POST"])
def create_custom_dataset_endpoint():
    """
    API endpoint to create a custom dataset from user input.
    Expects JSON with array of patch objects.
    """
    try:
        data = request.get_json()
        patches = data.get("patches", [])
        dataset_name = data.get("name", f"custom_dataset_{len(APP_STATE['custom_datasets']) + 1}")
        
        if not patches:
            return jsonify({"success": False, "error": "No patches provided"}), 400
        
        # Create the custom dataset
        custom_df = create_custom_dataset(patches)
        
        # Store it in APP_STATE
        APP_STATE["custom_datasets"][dataset_name] = custom_df
        
        return jsonify({
            "success": True,
            "dataset_name": dataset_name,
            "patch_count": len(custom_df),
            "message": f"Created custom dataset '{dataset_name}' with {len(custom_df)} patches"
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/visualizations", methods=["GET"])
def visualizations():
    page_title = "Visualizations"
    if not APP_STATE.get("plots"):
        flash("Please run a solver first to see the visualizations.", "info")
        return redirect(url_for("index"))
    return render_template("visualizations.html", page_title=page_title, state=APP_STATE, plots=APP_STATE["plots"])


@app.route("/config", methods=["GET", "POST"])
def config_page():
    page_title = "Configuration"
    if request.method == "POST":
        try:
            # Update weights and capacities in config objects for persistence across requests
            for key, value in build_weights_from_form(request.form).items():
                setattr(Config, f"WEIGHT_{key.upper()}", value)
            for key, value in build_capacities_from_form(request.form).items():
                setattr(Config, f"CAPACITY_{key.upper()}", value)
            
            # Also update APP_STATE for immediate reflection
            APP_STATE["settings"]["weights"] = build_weights_from_form(request.form)
            APP_STATE["settings"]["capacities"] = build_capacities_from_form(request.form)

            flash("Configuration updated successfully.", "success")
            return redirect(url_for("config_page"))
        except Exception as exc:
            flash(f"Error updating configuration: {exc}", "error")

    return render_template(
        "config.html",
        page_title=page_title,
        state=APP_STATE,
        default_capacities=APP_STATE.get("settings", {}).get("capacities", Config.DEFAULT_CAPACITY),
        default_weights=APP_STATE.get("settings", {}).get("weights", Config.SCORING_WEIGHTS),
    )


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(debug=True)
