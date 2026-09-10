"""Recursive-dynamic projection layer.

Wraps the validated comparative-static core in a time loop, driven by an
externally-sourced, versioned baseline trajectory. Baseline drift and policy
increment are reported separately, so a reader can always see how much of a
projected figure is "the world changing anyway" versus the policy.

The trajectory is an INPUT, not a forecast the model makes: it is adopted from a
recognised external authority (EU Agricultural Outlook / OECD-FAO Aglink-Cosimo,
the same sources CAPRI uses as its trend supports) and carries its own provenance.
"""
from .trajectory import BaselineTrajectory, TrajectoryError
from .reconcile import reconcile_projected_data, ReconciliationReport
from .projection_module import ProjectionModule, ProjectionResult
from .captrd_import import extract_trajectory, write_trajectory

__all__ = [
    "BaselineTrajectory", "TrajectoryError",
    "reconcile_projected_data", "ReconciliationReport",
    "ProjectionModule", "ProjectionResult",
    "extract_trajectory", "write_trajectory",
]
