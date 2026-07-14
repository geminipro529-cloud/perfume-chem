"""Thin wrapper around the canonical engine intervention diagnosis layer."""

from __future__ import annotations

from engine.pipeline.interventions import (
    diagnose_data_quality,
    diagnose_gates,
    diagnose_industry,
    diagnose_oav_table,
    diagnose_release_report as diagnose_all,
    diagnose_vp_pairs,
)

__all__ = [
    "diagnose_industry",
    "diagnose_oav_table",
    "diagnose_gates",
    "diagnose_vp_pairs",
    "diagnose_data_quality",
    "diagnose_all",
]
