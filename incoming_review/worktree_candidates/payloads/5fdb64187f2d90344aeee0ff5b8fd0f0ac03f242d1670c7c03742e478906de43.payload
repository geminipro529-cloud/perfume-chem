"""Formula-artifact binding and exact-decimal export repair helpers.

Canonical formula parts are immutable inputs. Only derived dose fields are
recomputed, and any successor export receives a new hash and parent reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
from typing import Iterable, Mapping

from .canonical import canonical_decimal, parse_decimal, sha256_payload


class FormulaArtifactError(ValueError):
    pass


class DriftClass(str, Enum):
    MATCH = "MATCH"
    UNINTENDED_SOURCE_MUTATION = "UNINTENDED_SOURCE_MUTATION"
    INTENTIONAL_SOURCE_MUTATION_NOT_REBOUND = "INTENTIONAL_SOURCE_MUTATION_NOT_REBOUND"
    STALE_GENERATED_ANALYSIS = "STALE_GENERATED_ANALYSIS"
    RENDERER_VERSION_DRIFT = "RENDERER_VERSION_DRIFT"
    MISSING_DEPENDENCY_OR_SOURCE_BYTES = "MISSING_DEPENDENCY_OR_SOURCE_BYTES"
    MALFORMED_BINDING_METADATA = "MALFORMED_BINDING_METADATA"
    AMBIGUOUS_REVIEW_REQUIRED = "AMBIGUOUS_REVIEW_REQUIRED"


@dataclass(frozen=True)
class FormulaPartLine:
    line_id: str
    parts_per_1000: Decimal

    @classmethod
    def create(cls, *, line_id: str, parts_per_1000: Decimal | str | int) -> "FormulaPartLine":
        parts = parse_decimal(parts_per_1000)
        if not line_id.strip():
            raise FormulaArtifactError("line_id is required")
        if parts < 0:
            raise FormulaArtifactError("parts_per_1000 cannot be negative")
        return cls(line_id=line_id, parts_per_1000=parts)


@dataclass(frozen=True)
class DoseExportLine:
    line_id: str
    parts_per_1000: Decimal
    exact_dose_ul: Decimal
    exported_dose_ul: Decimal
    rounding_adjustment_ul: Decimal


@dataclass(frozen=True)
class DoseExport:
    formula_id: str
    parent_formula_hash: str
    concentrate_ul: Decimal
    display_places: int | None
    balance_line_id: str | None
    lines: tuple[DoseExportLine, ...]
    exact_total_ul: Decimal
    exported_total_ul: Decimal
    canonical_parts_unchanged: bool
    successor_hash: str


@dataclass(frozen=True)
class ArtifactBinding:
    canonical_record_id: str
    canonical_content_hash: str
    renderer_version: str
    analysis_input_hash: str
    generated_analysis_hash: str
    source_file_hash: str
    parent_artifact_hash: str | None = None


@dataclass(frozen=True)
class BindingValidation:
    state: str
    mismatches: Mapping[str, tuple[str, str]]
    drift_class: DriftClass
    rebind_allowed: bool
    explanation: str


def recompute_dose_export(
    *,
    formula_id: str,
    parent_formula_hash: str,
    lines: Iterable[FormulaPartLine],
    concentrate_ul: Decimal | str | int,
    display_places: int | None = None,
    balance_line_id: str | None = None,
) -> DoseExport:
    """Recompute derived dose fields from canonical Decimal parts.

    When display precision is requested, all rows except the deterministic
    balance row are rounded independently. The balance row receives the exact
    display residual so the exported total closes without changing formula
    parts. The adjustment is explicit metadata, never hidden in the formula.
    """

    line_list = list(lines)
    if not formula_id.strip():
        raise FormulaArtifactError("formula_id is required")
    if len(parent_formula_hash) != 64:
        raise FormulaArtifactError("parent_formula_hash must be a SHA-256")
    if not line_list:
        raise FormulaArtifactError("at least one formula line is required")
    if len({line.line_id for line in line_list}) != len(line_list):
        raise FormulaArtifactError("duplicate formula line IDs are prohibited")

    total_parts = sum((line.parts_per_1000 for line in line_list), Decimal("0"))
    if total_parts != Decimal("1000"):
        raise FormulaArtifactError(
            f"canonical formula parts must total exactly 1000, observed {canonical_decimal(total_parts)}"
        )
    concentrate = parse_decimal(concentrate_ul)
    if concentrate <= 0:
        raise FormulaArtifactError("concentrate_ul must be positive")

    exact: dict[str, Decimal] = {
        line.line_id: line.parts_per_1000 * concentrate / Decimal("1000")
        for line in line_list
    }

    if display_places is None:
        exported = dict(exact)
        chosen_balance = None
    else:
        if display_places < 0 or display_places > 12:
            raise FormulaArtifactError("display_places must be between 0 and 12")
        quantum = Decimal(1).scaleb(-display_places)
        chosen_balance = balance_line_id
        if chosen_balance is None:
            chosen_balance = sorted(
                line_list,
                key=lambda line: (-line.parts_per_1000, line.line_id),
            )[0].line_id
        if chosen_balance not in exact:
            raise FormulaArtifactError("balance_line_id is not present in formula")
        exported = {}
        for line in line_list:
            if line.line_id == chosen_balance:
                continue
            exported[line.line_id] = exact[line.line_id].quantize(
                quantum, rounding=ROUND_HALF_EVEN
            )
        exported[chosen_balance] = concentrate - sum(exported.values(), Decimal("0"))
        if exported[chosen_balance] < 0:
            raise FormulaArtifactError("rounding balance would make the balance line negative")
        if exported[chosen_balance].quantize(quantum) != exported[chosen_balance]:
            raise FormulaArtifactError("rounding balance cannot be represented at requested precision")

    export_lines = tuple(
        DoseExportLine(
            line_id=line.line_id,
            parts_per_1000=line.parts_per_1000,
            exact_dose_ul=exact[line.line_id],
            exported_dose_ul=exported[line.line_id],
            rounding_adjustment_ul=exported[line.line_id] - exact[line.line_id],
        )
        for line in line_list
    )
    exported_total = sum((line.exported_dose_ul for line in export_lines), Decimal("0"))
    payload = {
        "formula_id": formula_id,
        "parent_formula_hash": parent_formula_hash,
        "concentrate_ul": canonical_decimal(concentrate),
        "display_places": display_places,
        "balance_line_id": chosen_balance,
        "canonical_parts_unchanged": True,
        "lines": [
            {
                "line_id": line.line_id,
                "parts_per_1000": canonical_decimal(line.parts_per_1000),
                "exact_dose_ul": canonical_decimal(line.exact_dose_ul),
                "exported_dose_ul": canonical_decimal(line.exported_dose_ul),
                "rounding_adjustment_ul": canonical_decimal(line.rounding_adjustment_ul),
            }
            for line in export_lines
        ],
    }
    return DoseExport(
        formula_id=formula_id,
        parent_formula_hash=parent_formula_hash,
        concentrate_ul=concentrate,
        display_places=display_places,
        balance_line_id=chosen_balance,
        lines=export_lines,
        exact_total_ul=concentrate,
        exported_total_ul=exported_total,
        canonical_parts_unchanged=True,
        successor_hash=sha256_payload(payload, domain="PERFUME_CHEM_DERIVED_DOSE_EXPORT_V20"),
    )


def validate_binding(expected: ArtifactBinding, actual: ArtifactBinding) -> BindingValidation:
    fields = (
        "canonical_record_id",
        "canonical_content_hash",
        "renderer_version",
        "analysis_input_hash",
        "generated_analysis_hash",
        "source_file_hash",
        "parent_artifact_hash",
    )
    mismatches = {
        field: (str(getattr(expected, field)), str(getattr(actual, field)))
        for field in fields
        if getattr(expected, field) != getattr(actual, field)
    }
    if not mismatches:
        return BindingValidation(
            state="PASS",
            mismatches={},
            drift_class=DriftClass.MATCH,
            rebind_allowed=False,
            explanation="Artifact binding matches exactly; no rebind is needed.",
        )

    keys = set(mismatches)
    if not expected.canonical_record_id or not expected.renderer_version:
        drift = DriftClass.MALFORMED_BINDING_METADATA
    elif "source_file_hash" in keys and "canonical_content_hash" in keys:
        drift = DriftClass.UNINTENDED_SOURCE_MUTATION
    elif keys <= {"generated_analysis_hash", "analysis_input_hash"}:
        drift = DriftClass.STALE_GENERATED_ANALYSIS
    elif keys == {"renderer_version", "generated_analysis_hash"} or keys == {"renderer_version"}:
        drift = DriftClass.RENDERER_VERSION_DRIFT
    elif "parent_artifact_hash" in keys and actual.parent_artifact_hash is None:
        drift = DriftClass.MISSING_DEPENDENCY_OR_SOURCE_BYTES
    else:
        drift = DriftClass.AMBIGUOUS_REVIEW_REQUIRED

    return BindingValidation(
        state="HOLD",
        mismatches=mismatches,
        drift_class=drift,
        rebind_allowed=False,
        explanation=(
            "Semantic review is required. A hash mismatch must not be repaired by blind commit, "
            "stash, reset, regeneration, or hand-edited expected hashes."
        ),
    )


def classify_reviewed_change(
    *,
    source_semantic_change: bool,
    change_intentional: bool,
    generated_only_change: bool,
    renderer_changed: bool,
    dependency_missing: bool,
    metadata_malformed: bool,
) -> DriftClass:
    if metadata_malformed:
        return DriftClass.MALFORMED_BINDING_METADATA
    if dependency_missing:
        return DriftClass.MISSING_DEPENDENCY_OR_SOURCE_BYTES
    if source_semantic_change and change_intentional:
        return DriftClass.INTENTIONAL_SOURCE_MUTATION_NOT_REBOUND
    if source_semantic_change and not change_intentional:
        return DriftClass.UNINTENDED_SOURCE_MUTATION
    if generated_only_change and renderer_changed:
        return DriftClass.RENDERER_VERSION_DRIFT
    if generated_only_change:
        return DriftClass.STALE_GENERATED_ANALYSIS
    return DriftClass.AMBIGUOUS_REVIEW_REQUIRED


def rebind_preflight(
    *,
    clean_or_intentionally_staged: bool,
    semantic_diff_reviewed: bool,
    change_unambiguous: bool,
    parent_source_bytes_available: bool,
    drift_class: DriftClass,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not clean_or_intentionally_staged:
        reasons.append("working tree is neither clean nor intentionally staged")
    if not semantic_diff_reviewed:
        reasons.append("semantic diff has not been reviewed")
    if not change_unambiguous:
        reasons.append("change classification is ambiguous")
    if not parent_source_bytes_available:
        reasons.append("exact parent source bytes are unavailable")
    if drift_class not in {
        DriftClass.INTENTIONAL_SOURCE_MUTATION_NOT_REBOUND,
        DriftClass.STALE_GENERATED_ANALYSIS,
        DriftClass.RENDERER_VERSION_DRIFT,
    }:
        reasons.append(f"drift class {drift_class.value} is not rebind-eligible")
    return not reasons, tuple(reasons)
