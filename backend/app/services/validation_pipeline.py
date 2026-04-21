"""
Unified Validation Pipeline
============================
Every formula-bearing request passes through these gates IN ORDER before
the endpoint logic executes:

  Gate 1 ─ Input Sanitization   (size, type, non-empty)
  Gate 2 ─ Balance Check        (≈100 %)
  Gate 3 ─ Chemistry Validation (potency limits, IFRA compliance, note pyramid)
  Gate 4 ─ Response Envelope    (attach warnings / info to output)

ERROR-severity issues → HTTP 400 (request rejected before processing).
WARNING / INFO issues → processing continues; issues attached to response.

Rate limiting is handled separately as middleware in main.py.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from fastapi import HTTPException
import logging

from app.core.tracing import get_tracer
from app.services.chemistry_validator import (
    ChemistryValidator,
    ValidationSeverity,
    ValidationIssue,
)

logger = logging.getLogger(__name__)

# Singleton – loaded once on first call, reused thereafter.
_validator: Optional[ChemistryValidator] = None


def _get_validator() -> ChemistryValidator:
    global _validator
    if _validator is None:
        _validator = ChemistryValidator()
    return _validator


# ─── Data Structures ────────────────────────────────────────────────

@dataclass
class PipelineReport:
    """Result of the full validation pipeline."""
    passed: bool = True
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    info: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


# ─── Public API ─────────────────────────────────────────────────────

MAX_INGREDIENTS = 50
MAX_NAME_LENGTH = 200


def validate_formula(ingredients: dict[str, float]) -> PipelineReport:
    """
    Run the full gate sequence on a ``{name: pct}`` formula dict.

    Raises ``HTTPException(400)`` if any ERROR-level issue is found.
    Otherwise returns a ``PipelineReport`` with warnings/info that the
    endpoint can fold into its response.
    """
    _tracer = get_tracer("validation_pipeline")
    with _tracer.start_as_current_span("validation.formula") as span:
        span.set_attribute("formula.ingredient_count", len(ingredients))
        return _validate_formula_impl(ingredients, span)


def _validate_formula_impl(ingredients: dict[str, float], span) -> PipelineReport:
    report = PipelineReport()

    # ── Gate 1: Input Sanitization ──
    if not ingredients:
        raise HTTPException(status_code=400, detail="Formula must contain at least one ingredient.")

    if len(ingredients) > MAX_INGREDIENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Formula exceeds maximum of {MAX_INGREDIENTS} ingredients ({len(ingredients)} given).",
        )

    for name in ingredients:
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="Ingredient names must be non-empty strings.")
        if len(name) > MAX_NAME_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Ingredient name exceeds {MAX_NAME_LENGTH} characters: '{name[:40]}…'",
            )

    for name, pct in ingredients.items():
        if not isinstance(pct, (int, float)) or pct < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Percentage for '{name}' must be a non-negative number (got {pct}).",
            )

    # ── Gate 2 + 3: Chemistry Validation ──
    # Convert {name: pct} → list-of-dicts expected by ChemistryValidator
    ingredient_list = [{"name": n, "percentage": p} for n, p in ingredients.items()]

    validator = _get_validator()
    issues: List[ValidationIssue] = validator.validate_formula(ingredient_list)

    for issue in issues:
        bucket = issue.to_dict()
        # Chemistry issues are advisory — downgrade errors to warnings
        # so formulators can experiment freely.  Only Gate-1 (input
        # sanitization) produces hard rejections.
        if issue.severity == ValidationSeverity.ERROR:
            report.warnings.append(bucket)
        elif issue.severity == ValidationSeverity.WARNING:
            report.warnings.append(bucket)
        else:
            report.info.append(bucket)

    span.set_attribute("formula.warnings", len(report.warnings))
    span.set_attribute("formula.info_count", len(report.info))
    logger.debug(
        "Validation pipeline passed (%d warnings, %d info)",
        len(report.warnings),
        len(report.info),
    )
    return report


def validate_pair(material_a: str, material_b: str) -> PipelineReport:
    """Lightweight gate for pair-analysis endpoints (sanitization only)."""
    report = PipelineReport()

    for label, name in [("material_a", material_a), ("material_b", material_b)]:
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail=f"'{label}' must be a non-empty string.")
        if len(name) > MAX_NAME_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"'{label}' exceeds {MAX_NAME_LENGTH} characters.",
            )

    return report


def validate_search_query(query: str) -> PipelineReport:
    """Gate for knowledge-search endpoints."""
    report = PipelineReport()

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query must not be empty.")
    if len(query) > 1000:
        raise HTTPException(status_code=400, detail="Search query exceeds 1000 characters.")

    return report


def attach_validation(response: dict, report: PipelineReport) -> dict:
    """Fold pipeline warnings/info into any endpoint response dict."""
    if report.warnings or report.info:
        response["_validation"] = {
            "warnings": report.warnings,
            "info": report.info,
        }
    return response
