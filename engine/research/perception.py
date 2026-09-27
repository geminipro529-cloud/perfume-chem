"""Endpoint-separated detection, intensity, and character computations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from engine.dose_response import (
    measured_mixture_intensity_challengers,
    resolve_measured_curve,
)

from .contracts import FALSE_ACTION_AUTHORITY


def _finite_nonnegative(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"{name} must be finite and non-negative")
    return float(value)


def compute_detection_diagnostic(
    *,
    material_id: str,
    delivered_gas_ug_l: float | None,
    threshold_gas_ug_l: float | None,
    concentration_identity_id: str,
    threshold_identity_id: str,
    concentration_phase: str,
    threshold_phase: str,
    concentration_unit: str,
    threshold_unit: str,
    concentration_protocol_id: str,
    threshold_protocol_id: str,
    concentration_temperature_k: float,
    threshold_temperature_k: float,
    temperature_correction_capability_id: str | None = None,
) -> dict[str, Any]:
    """Compute OAV only for a matched delivered-gas detection contract."""

    if not isinstance(material_id, str) or not material_id.strip():
        raise ValueError("material_id must be non-empty text")
    reasons: list[str] = []
    if delivered_gas_ug_l is None:
        reasons.append("DELIVERED_GAS_CONCENTRATION_UNAVAILABLE")
    else:
        delivered = _finite_nonnegative(delivered_gas_ug_l, "delivered_gas_ug_l")
    if threshold_gas_ug_l is None:
        reasons.append("COMPATIBLE_GAS_THRESHOLD_UNAVAILABLE")
    else:
        threshold = _finite_nonnegative(threshold_gas_ug_l, "threshold_gas_ug_l")
        if threshold == 0:
            raise ValueError("threshold_gas_ug_l must be greater than zero")
    if concentration_identity_id != threshold_identity_id:
        reasons.append("IDENTITY_MISMATCH")
    if concentration_phase != "AIR" or threshold_phase != "AIR":
        reasons.append("PHASE_NOT_DELIVERED_AIR")
    if concentration_unit != "ug/L_air" or threshold_unit != "ug/L_air":
        reasons.append("UNIT_MISMATCH")
    if concentration_protocol_id != threshold_protocol_id:
        reasons.append("PROTOCOL_MISMATCH")
    for value, name in (
        (concentration_temperature_k, "concentration_temperature_k"),
        (threshold_temperature_k, "threshold_temperature_k"),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
        ):
            raise ValueError(f"{name} must be finite and positive")
    if not math.isclose(
        float(concentration_temperature_k),
        float(threshold_temperature_k),
        rel_tol=0.0,
        abs_tol=1e-9,
    ) and not temperature_correction_capability_id:
        reasons.append("TEMPERATURE_MISMATCH_UNCORRECTED")

    return {
        "schema_version": "gas-detection-diagnostic-v1",
        "endpoint": "DETECTION_DIAGNOSTIC",
        "material_id": material_id.strip(),
        "oav": None if reasons else delivered / threshold,
        "unit": "dimensionless",
        "applicability_state": "UNAVAILABLE" if reasons else "APPLICABLE",
        "validation_state": "WITHHOLD_UNKNOWN" if reasons else "ADVISORY_COMPLETE",
        "reason_codes": sorted(set(reasons)),
        "optimizer_selection_usable": False,
        "intensity_authorized": False,
        "pleasantness_authorized": False,
        "liking_authorized": False,
        "beauty_authorized": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


def evaluate_individual_intensity(
    capability: Mapping[str, Any],
    *,
    delivered_gas_ug_l: float,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one governed curve without requiring or fabricating an ODT."""

    concentration = _finite_nonnegative(delivered_gas_ug_l, "delivered_gas_ug_l")
    resolved = resolve_measured_curve(
        capability,
        gas_ug_l_air=concentration,
        context=dict(context),
    )
    admission = dict(resolved["admission"])
    return {
        "schema_version": "individual-intensity-estimate-v1",
        "endpoint": "INTENSITY",
        "value": resolved["intensity"],
        "unit": capability.get("curve", {}).get("response_scale"),
        "applicability_state": "APPLICABLE" if admission.get("usable") else "UNAVAILABLE",
        "validation_state": "ADVISORY_COMPLETE" if admission.get("usable") else "WITHHOLD_UNKNOWN",
        "admission": admission,
        "detection_threshold_required": False,
        "oav_used": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


def evaluate_mixture_intensity(
    gas_ug_l_by_identity: Mapping[str, float],
    curves: Mapping[str, Mapping[str, float]],
    *,
    partial_addition_lambda: float | None,
    upper_bound: float,
) -> dict[str, Any]:
    """Return three inspectable challengers; never average or relabel them."""

    result = measured_mixture_intensity_challengers(
        dict(gas_ug_l_by_identity),
        dict(curves),
        partial_addition_lambda=partial_addition_lambda,
        upper_bound=upper_bound,
    )
    return {
        "schema_version": "mixture-intensity-challengers-v1",
        "endpoint": "INTENSITY",
        **result,
        "ensemble_prediction": None,
        "pleasantness": None,
        "beauty": None,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


@dataclass(frozen=True, slots=True)
class CharacterComponentV1:
    component_id: str
    positive_dose: bool
    intensity: float | None
    descriptors: Mapping[str, float] | None

    def __post_init__(self) -> None:
        if not isinstance(self.component_id, str) or not self.component_id.strip():
            raise ValueError("component_id must be non-empty text")
        if not isinstance(self.positive_dose, bool):
            raise TypeError("positive_dose must be boolean")
        if self.intensity is not None:
            object.__setattr__(
                self, "intensity", _finite_nonnegative(self.intensity, "intensity")
            )
        if self.descriptors is not None:
            normalized: dict[str, float] = {}
            for key, value in self.descriptors.items():
                label = str(key).strip()
                if not label:
                    raise ValueError("descriptor labels must be non-empty")
                normalized[label] = _finite_nonnegative(value, f"descriptor {label}")
            object.__setattr__(self, "descriptors", normalized)


def linear_intensity_weighted_character(
    components: Sequence[CharacterComponentV1],
    *,
    incomplete_policy: Literal["WITHHOLD", "PARTIAL"] = "WITHHOLD",
) -> dict[str, Any]:
    """Simple concentration-aware descriptor baseline.

    It returns descriptor character only. It cannot stand in for hedonic value,
    perceptual distance, depth, richness, or final formula quality.
    """

    rows = tuple(components)
    if not rows:
        raise ValueError("at least one character component is required")
    if len({row.component_id for row in rows}) != len(rows):
        raise ValueError("character component identities must be unique")
    positive = [row for row in rows if row.positive_dose]
    missing = [
        row.component_id
        for row in positive
        if row.intensity is None or row.descriptors is None
    ]
    complete = [
        row
        for row in positive
        if row.intensity is not None and row.descriptors is not None
    ]
    coverage = len(complete) / len(positive) if positive else 1.0
    if missing and incomplete_policy == "WITHHOLD":
        return {
            "schema_version": "linear-character-baseline-v1",
            "endpoint": "CHARACTER",
            "descriptor_profile": None,
            "positive_dose_coverage": coverage,
            "missing_component_ids": sorted(missing),
            "applicability_state": "UNAVAILABLE",
            "validation_state": "WITHHOLD_UNKNOWN",
            "reason_codes": ["MISSING_COMPONENT_CHARACTER_CALIBRATION"],
            "pleasantness": None,
            "liking": None,
            "beauty": None,
            "formula_action": "NO_CHANGE",
            **FALSE_ACTION_AUTHORITY,
        }
    total_intensity = math.fsum(row.intensity or 0.0 for row in complete)
    if total_intensity <= 0:
        return {
            "schema_version": "linear-character-baseline-v1",
            "endpoint": "CHARACTER",
            "descriptor_profile": None,
            "positive_dose_coverage": coverage,
            "missing_component_ids": sorted(missing),
            "applicability_state": "UNAVAILABLE",
            "validation_state": "WITHHOLD_UNKNOWN",
            "reason_codes": ["NO_POSITIVE_CALIBRATED_INTENSITY"],
            "pleasantness": None,
            "liking": None,
            "beauty": None,
            "formula_action": "NO_CHANGE",
            **FALSE_ACTION_AUTHORITY,
        }
    labels = sorted(
        {label for row in complete for label in (row.descriptors or {})}
    )
    profile = {
        label: math.fsum(
            (row.intensity or 0.0) * float((row.descriptors or {}).get(label, 0.0))
            for row in complete
        )
        / total_intensity
        for label in labels
    }
    partial = bool(missing)
    return {
        "schema_version": "linear-character-baseline-v1",
        "endpoint": "CHARACTER",
        "descriptor_profile": profile,
        "positive_dose_coverage": coverage,
        "missing_component_ids": sorted(missing),
        "applicability_state": "PARTIAL" if partial else "APPLICABLE",
        "validation_state": "ADVISORY_FINDINGS" if partial else "ADVISORY_COMPLETE",
        "reason_codes": ["PARTIAL_COMPONENT_COVERAGE"] if partial else [],
        "baseline_kind": "INTENSITY_WEIGHTED_LINEAR_COMPONENT_PROFILE",
        "pleasantness": None,
        "liking": None,
        "beauty": None,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


def unavailable_hedonic_endpoints() -> dict[str, Any]:
    """Canonical absence result when no applicable human hedonic labels exist."""

    return {
        "population_pleasantness": None,
        "personal_liking": None,
        "beauty": None,
        "validation_state": "WITHHOLD_UNKNOWN",
        "applicability_state": "UNAVAILABLE",
        "reason_codes": [
            "APPLICABLE_POPULATION_PLEASANTNESS_CAPABILITY_MISSING",
            "PERSONAL_LIKING_OBSERVATIONS_MISSING",
            "BEAUTY_ENDPOINT_PROHIBITED",
        ],
        "neutral_midpoint_imputed": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


__all__ = [
    "CharacterComponentV1",
    "compute_detection_diagnostic",
    "evaluate_individual_intensity",
    "evaluate_mixture_intensity",
    "linear_intensity_weighted_character",
    "unavailable_hedonic_endpoints",
]
