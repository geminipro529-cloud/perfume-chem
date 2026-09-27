"""Truthful advisory validation shared by every formula-bearing endpoint.

This layer screens inputs and reports the exact state of its legacy reference
snapshots. It never grants safety, release, regulatory, or compounding
authority. Structural invalidity blocks execution; missing or incomplete
reference evidence produces an explicit WITHHOLD state while diagnostic engine
work may continue.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from fastapi import HTTPException

from app.core.tracing import get_tracer
from app.services.chemistry_validator import (
    ChemistryValidator,
    ReferenceDatasetStatus,
    ValidationIssue,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)

VALIDATION_SCHEMA_VERSION = "backend-advisory-validation-v2"
VALIDATION_CLASSIFICATION = "ADVISORY_ONLY"
VALIDATION_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "regulatory_authority": False,
    "compounding_authority": False,
}

# Singleton: its hashes and load states are included in every emitted envelope.
_validator: Optional[ChemistryValidator] = None


def _get_validator() -> ChemistryValidator:
    global _validator
    if _validator is None:
        _validator = ChemistryValidator()
    return _validator


@dataclass(slots=True)
class PipelineReport:
    """Always-serializable advisory validation envelope."""

    state: str = "ADVISORY_COMPLETE"
    reference_bundle_sha256: str | None = None
    reference_datasets: dict[str, dict[str, Any]] = field(default_factory=dict)
    coverage: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    info: list[dict[str, Any]] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)
    processing_allowed: bool = True
    engine_job_contract: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "state": self.state,
            "classification": VALIDATION_CLASSIFICATION,
            "reference_bundle_sha256": self.reference_bundle_sha256,
            "reference_datasets": self.reference_datasets,
            "coverage": self.coverage,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "missing_requirements": self.missing_requirements,
            "processing_allowed": self.processing_allowed,
            "authority": dict(VALIDATION_AUTHORITY),
        }
        if self.engine_job_contract is not None:
            payload["engine_job_contract"] = dict(self.engine_job_contract)
        return payload


MAX_INGREDIENTS = 50
MAX_NAME_LENGTH = 200


def _invalid_input(message: str) -> None:
    report = PipelineReport(
        state="INVALID_INPUT",
        processing_allowed=False,
        errors=[
            {
                "severity": "error",
                "chemical": "REQUEST",
                "message": message,
                "suggested_fix": None,
                "current_value": None,
                "recommended_value": None,
            }
        ],
    )
    raise HTTPException(
        status_code=400,
        detail={
            "code": "INVALID_INPUT",
            "message": message,
            "validation": report.to_dict(),
        },
    )


def validate_formula(ingredients: dict[str, float]) -> PipelineReport:
    """Validate structure and emit a truthful advisory evidence envelope."""

    if not isinstance(ingredients, dict) or not ingredients:
        _invalid_input("Formula must contain at least one ingredient.")
    tracer = get_tracer("validation_pipeline")
    with tracer.start_as_current_span("validation.formula") as span:
        span.set_attribute("formula.ingredient_count", len(ingredients))
        return _validate_formula_impl(ingredients, span)


def _validate_formula_impl(
    ingredients: dict[str, float], span: Any
) -> PipelineReport:
    if not isinstance(ingredients, dict) or not ingredients:
        _invalid_input("Formula must contain at least one ingredient.")
    if len(ingredients) > MAX_INGREDIENTS:
        _invalid_input(
            f"Formula exceeds maximum of {MAX_INGREDIENTS} ingredients "
            f"({len(ingredients)} given)."
        )

    normalized: dict[str, float] = {}
    for name, value in ingredients.items():
        if not isinstance(name, str) or not name.strip():
            _invalid_input("Ingredient names must be non-empty strings.")
        if len(name) > MAX_NAME_LENGTH:
            _invalid_input(
                f"Ingredient name exceeds {MAX_NAME_LENGTH} characters: "
                f"'{name[:40]}…'."
            )
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) < 0
        ):
            _invalid_input(
                f"Percentage for '{name}' must be a finite non-negative "
                f"number (got {value!r})."
            )
        normalized[name] = float(value)

    validator = _get_validator()
    ingredient_list = [
        {"name": name, "percentage": value}
        for name, value in normalized.items()
    ]
    issues: list[ValidationIssue] = validator.validate_formula(ingredient_list)
    report = PipelineReport(
        reference_bundle_sha256=validator.reference_bundle_sha256(),
        reference_datasets=validator.reference_snapshot(),
        coverage=validator.coverage_report(ingredient_list),
    )

    for issue in issues:
        serialized = issue.to_dict()
        if issue.severity == ValidationSeverity.ERROR:
            report.errors.append(serialized)
        elif issue.severity == ValidationSeverity.WARNING:
            report.warnings.append(serialized)
        else:
            report.info.append(serialized)

    missing: list[str] = []
    for dataset_id, state in validator.reference_states.items():
        if state.status != ReferenceDatasetStatus.AVAILABLE:
            missing.append(
                f"REFERENCE_DATASET:{dataset_id}:{state.status.value}:"
                f"{state.reason or 'UNAVAILABLE'}"
            )
    for coverage_id, details in report.coverage.items():
        missing_materials = details.get("missing_materials", [])
        if missing_materials:
            missing.append(
                f"POSITIVE_DOSE_COVERAGE:{coverage_id}:"
                + ",".join(str(item) for item in missing_materials)
            )
    report.missing_requirements = sorted(set(missing))

    if report.missing_requirements:
        report.state = "WITHHOLD_UNKNOWN"
    elif report.errors or report.warnings or report.info:
        report.state = "ADVISORY_FINDINGS"
    else:
        report.state = "ADVISORY_COMPLETE"

    span.set_attribute("formula.validation_state", report.state)
    span.set_attribute("formula.errors", len(report.errors))
    span.set_attribute("formula.warnings", len(report.warnings))
    span.set_attribute("formula.info_count", len(report.info))
    logger.debug(
        "Validation state %s (%d errors, %d warnings, %d info)",
        report.state,
        len(report.errors),
        len(report.warnings),
        len(report.info),
    )
    return report


def _non_formula_report() -> PipelineReport:
    validator = _get_validator()
    return PipelineReport(
        reference_bundle_sha256=validator.reference_bundle_sha256(),
        reference_datasets=validator.reference_snapshot(),
    )


def validate_pair(material_a: str, material_b: str) -> PipelineReport:
    """Lightweight structural gate for pair-analysis endpoints."""

    for label, name in (("material_a", material_a), ("material_b", material_b)):
        if not isinstance(name, str) or not name.strip():
            _invalid_input(f"'{label}' must be a non-empty string.")
        if len(name) > MAX_NAME_LENGTH:
            _invalid_input(f"'{label}' exceeds {MAX_NAME_LENGTH} characters.")
    return _non_formula_report()


def validate_search_query(query: str) -> PipelineReport:
    """Structural gate for knowledge-search endpoints."""

    if not isinstance(query, str) or not query.strip():
        _invalid_input("Search query must not be empty.")
    if len(query) > 1000:
        _invalid_input("Search query exceeds 1000 characters.")
    return _non_formula_report()


def attach_validation(
    response: dict[str, Any], report: PipelineReport
) -> dict[str, Any]:
    """Attach the v2 envelope and a one-release compatibility mirror."""

    envelope = report.to_dict()
    response["validation"] = envelope
    response["_validation"] = envelope
    return response


__all__ = [
    "PipelineReport",
    "attach_validation",
    "validate_formula",
    "validate_pair",
    "validate_search_query",
]
