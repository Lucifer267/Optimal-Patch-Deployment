# Cybersecurity Optimal Patch Deployment using Multi-Dimensional Knapsack, Risk-Aware Scheduling, and Intelligent Visual Analytics

## Abstract
This project is a decision-support platform for cybersecurity operations teams. It prioritizes vulnerability patches using contextual risk scoring, multi-resource optimization, dependency-aware selection, SLA urgency, and sequential deployment scheduling. The result is an explainable patch plan that maximizes contextual risk reduction under downtime, budget, and manpower constraints.

## Motivation
Security teams rarely patch in a purely severity-driven way. Real-world remediation must account for exploitability, exposed assets, patch failure risk, service disruption, maintenance windows, and dependency chains. This project models those realities with an optimization and visualization stack suitable for a final-year or research-grade demo.

## Problem Statement
Given a set of patches, decide which ones to deploy and in what order so that the total contextual risk reduction is maximized while respecting:
- downtime / maintenance window limits
- budget limits
- manpower limits
- dependency constraints
- conflict constraints
- SLA urgency
- sequential deployment feasibility

## Architecture
The system is organized into a scoring layer, graph layer, optimization layer, scheduling layer, explainability layer, and Flask UI.

- `modules/risk_engine.py` computes contextual risk and adjusted patch value.
- `modules/dependency_graph.py` enforces DAG dependencies and conflicts.
- `solvers/` contains greedy, dynamic programming, branch and bound, FPTAS, ILP, and multi-system solvers.
- `modules/scheduler.py` creates a dependency-safe deployment order.
- `app.py` exposes the Flask dashboard.

## Folder Structure
```text
project/
├── app.py
├── run.py
├── config.py
├── requirements.txt
├── README.md
├── data/
├── modules/
├── solvers/
├── experiments/
├── templates/
├── static/
│   ├── css/
│   ├── js/
│   ├── icons/
│   └── plots/
└── notebooks/
```

## Mathematical Model
Let $x_i \in \{0,1\}$ indicate whether patch $i$ is selected.

Maximize:
$$
\sum_i x_i \cdot V_i
$$
where $V_i$ is the contextual risk reduction of patch $i$.

Subject to:
$$
\sum_i x_i t_i \le T,
\quad
\sum_i x_i c_i \le B,
\quad
\sum_i x_i m_i \le M
$$

and dependency, conflict, SLA, and scheduling feasibility constraints.

## Risk Model
The project uses a contextual scoring model rather than raw CVSS.

$$
\text{base\_risk} =
w_1 \cdot \text{CVSS} +
w_2 \cdot \text{Exploit Probability} +
w_3 \cdot \text{Exploit Availability} +
w_4 \cdot \text{Active Exploitation} +
w_5 \cdot \text{Asset Criticality} +
w_6 \cdot \text{Data Sensitivity} +
w_7 \cdot \text{Exposure} +
w_8 \cdot \text{Time Decay} +
w_9 \cdot \text{SLA Urgency}
$$

Adjusted value:
$$
\text{adjusted\_patch\_value} =
(\text{base\_risk} \cdot \text{remediation\_effectiveness}) - \text{failure\_penalty}
$$

The model explicitly includes:
- Time decay risk
- Exploit availability
- Asset criticality modeling
- Patch failure risk
- SLA constraints
- Adversarial pressure

## Algorithms
- Greedy ratio heuristic
- Greedy weighted multi-resource heuristic
- Phase 2 multi-resource greedy benchmark
- Dynamic programming baseline for classic single-constraint knapsack
- Branch and bound with upper-bound pruning
- FPTAS approximation for the classic case
- ILP benchmark using PuLP
- Multi-system grouped optimization extension

## Phase 2 Focus
Phase 2 adds a stronger multi-dimensional comparison layer on top of the baseline:
- normalized multi-resource footprint scoring
- approximation gap reporting against ILP when available
- quality-vs-runtime benchmark summaries
- experiment runner for repeatable solver comparisons

Run the benchmark:
```bash
python run.py --benchmark-phase2 --dataset data/sample_medium.csv
```

## Dependency Handling
Patch dependencies and conflicts are modeled as a directed graph. The app validates acyclicity, performs topological scheduling, and prevents infeasible selections.

## SLA and Time Decay
Patches become more urgent as they age and approach SLA breach. The urgency signal increases the contextual value of remediation and influences ordering.

## Patch Failure Model
The system penalizes risky patches using patch failure probability, disruption impact, and rollback complexity to avoid unsafe remediation plans.

## Scheduling Model
After selection, patches are ordered using dependency-aware priority scheduling and partitioned into maintenance batches.

## Adversarial Extension
An attacker-pressure layer boosts priority for patches that are internet-facing, exploitable, or already under active exploitation.

## UI Overview
The Flask dashboard includes:
- home/input page
- results page
- comparison page
- visualizations page
- config/weights page

The interface uses a premium dark-first cyber-operations aesthetic with glass-style panels, KPI cards, timeline views, and responsive tables.

## Run Instructions
Install dependencies:
```bash
pip install -r requirements.txt
```

Run the web app:
```bash
python run.py
```

Run the CLI demo:
```bash
python run.py --cli --dataset data/sample_small.csv --algorithm branch_bound
```

Generate larger sample datasets:
```bash
python run.py --generate-samples
```

## Dataset Fields
The project expects:
- vuln_id
- cve_id
- patch_id
- patch_name
- asset_id
- asset_name
- system_group
- service_name
- cvss
- exploit_probability
- exploit_available
- active_exploitation
- asset_criticality
- data_sensitivity
- exposure_level
- internet_facing
- patch_time
- patch_cost
- manpower_required
- remediation_effectiveness
- patch_failure_risk
- disruption_impact
- rollback_complexity
- age_days
- severity_label
- sla_deadline_days
- days_open
- dependencies
- conflicts

## Limitations
- Dynamic programming is kept as a classic single-constraint baseline.
- ILP requires PuLP and a working CBC solver.
- Large dependency-rich instances may be expensive for exact search.

## Future Scope
- richer multi-system allocation models
- stochastic patch failure simulation
- attacker/defender game-theory calibration
- more advanced ILP constraints
- report generation and export automation
