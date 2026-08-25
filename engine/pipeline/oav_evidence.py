"""Evidence-state OAV gate without aggregate perceptual authority."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.pipeline.formula_state import FormulaState

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class OAVEvidenceState(str, Enum):
    STRICT_MEASURED = "STRICT_MEASURED"
    MODELED_SCREEN = "MODELED_SCREEN"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    INVALID = "INVALID"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _sha256(value: object, field_name: str) -> str:
    digest = _text(value, field_name).lower()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _same_text(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


@dataclass(frozen=True, slots=True)
class OAVMaterialEvidenceInput:
    material_name: str
    canonical_name: str
    exact_stock_ref: str | None
    supplied_strength_fraction: float | None
    carrier: str | None
    active_mass_g: float | None
    formula_matrix: str
    headspace: QuantitativeEvidence
    threshold: QuantitativeEvidence
    natural_or_preblend: bool = False
    constituent_evidence: tuple[QuantitativeEvidence, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "material_name", _text(self.material_name, "material_name")
        )
        object.__setattr__(
            self, "canonical_name", _text(self.canonical_name, "canonical_name")
        )
        object.__setattr__(
            self,
            "exact_stock_ref",
            _optional_text(self.exact_stock_ref, "exact_stock_ref"),
        )
        object.__setattr__(self, "carrier", _optional_text(self.carrier, "carrier"))
        object.__setattr__(
            self, "formula_matrix", _text(self.formula_matrix, "formula_matrix")
        )
        if self.supplied_strength_fraction is not None:
            value = self.supplied_strength_fraction
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("supplied_strength_fraction must be numeric")
            strength = float(value)
            if not isfinite(strength) or strength <= 0 or strength > 1:
                raise ValueError(
                    "supplied_strength_fraction must be finite and in (0, 1]"
                )
            object.__setattr__(self, "supplied_strength_fraction", strength)
        if self.active_mass_g is not None:
            value = self.active_mass_g
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("active_mass_g must be numeric")
            mass = float(value)
            if not isfinite(mass) or mass < 0:
                raise ValueError("active_mass_g must be finite and nonnegative")
            object.__setattr__(self, "active_mass_g", mass)
        if not isinstance(self.headspace, QuantitativeEvidence):
            raise TypeError("headspace must be QuantitativeEvidence")
        if not isinstance(self.threshold, QuantitativeEvidence):
            raise TypeError("threshold must be QuantitativeEvidence")
        if not isinstance(self.natural_or_preblend, bool):
            raise TypeError("natural_or_preblend must be boolean")
        constituents = tuple(self.constituent_evidence)
        if any(not isinstance(item, QuantitativeEvidence) for item in constituents):
            raise TypeError("constituent_evidence must contain QuantitativeEvidence")
        object.__setattr__(self, "constituent_evidence", constituents)


@dataclass(frozen=True, slots=True)
class OAVEvidenceRequest:
    formula_sha256: str
    dose_receipt_sha256: str
    measurement_context: str
    rows: tuple[OAVMaterialEvidenceInput, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "formula_sha256", _sha256(self.formula_sha256, "formula_sha256")
        )
        object.__setattr__(
            self,
            "dose_receipt_sha256",
            _sha256(self.dose_receipt_sha256, "dose_receipt_sha256"),
        )
        object.__setattr__(
            self,
            "measurement_context",
            _text(self.measurement_context, "measurement_context"),
        )
        rows = tuple(self.rows)
        if any(not isinstance(row, OAVMaterialEvidenceInput) for row in rows):
            raise TypeError("rows must contain OAVMaterialEvidenceInput")
        object.__setattr__(self, "rows", rows)


@dataclass(frozen=True, slots=True)
class OAVMaterialEvidenceResult:
    material_name: str
    canonical_name: str
    state: OAVEvidenceState
    headspace_basis: EvidenceBasis
    threshold_basis: EvidenceBasis
    oav: float | None
    threshold_screening: str
    recognizable_in_mixture: None
    constituent_evidence_count: int
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "material_name": self.material_name,
            "canonical_name": self.canonical_name,
            "state": self.state.value,
            "headspace_basis": self.headspace_basis.value,
            "threshold_basis": self.threshold_basis.value,
            "oav": self.oav,
            "threshold_screening": self.threshold_screening,
            "recognizable_in_mixture": None,
            "constituent_evidence_count": self.constituent_evidence_count,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class OAVEvidenceResult:
    state: OAVEvidenceState
    formula_sha256: str
    dose_receipt_sha256: str
    measurement_context: str
    rows: tuple[OAVMaterialEvidenceResult, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "oav_evidence_v2",
            "state": self.state.value,
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "measurement_context": self.measurement_context,
            "rows": [row.as_dict() for row in self.rows],
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "authority": {
                "sensory": self.sensory_authority,
                "hedonic": self.hedonic_authority,
                "release": self.release_authority,
            },
        }


def _invalid_row(
    row: OAVMaterialEvidenceInput,
    blockers: list[str],
    limitations: list[str],
) -> OAVMaterialEvidenceResult:
    return OAVMaterialEvidenceResult(
        material_name=row.material_name,
        canonical_name=row.canonical_name,
        state=OAVEvidenceState.INVALID,
        headspace_basis=row.headspace.basis,
        threshold_basis=row.threshold.basis,
        oav=None,
        threshold_screening="NOT_COMPUTABLE",
        recognizable_in_mixture=None,
        constituent_evidence_count=len(row.constituent_evidence),
        blockers=tuple(blockers),
        limitations=tuple(limitations),
    )


def _evaluate_row(
    row: OAVMaterialEvidenceInput,
    measurement_context: str,
) -> OAVMaterialEvidenceResult:
    blockers: list[str] = []
    limitations = [
        "OAV is a threshold-screening ratio only and does not establish mixture recognition."
    ]
    if row.constituent_evidence and not row.natural_or_preblend:
        blockers.append("constituent evidence is attached to a monomolecular row")
    for label, evidence in (("headspace", row.headspace), ("threshold", row.threshold)):
        if evidence.basis is not EvidenceBasis.UNKNOWN:
            if not _same_text(evidence.context, measurement_context):
                blockers.append(f"{label} context does not match request context")
    if (
        row.headspace.basis is not EvidenceBasis.UNKNOWN
        and row.threshold.basis is not EvidenceBasis.UNKNOWN
        and not _same_text(row.headspace.unit, row.threshold.unit)
    ):
        blockers.append("headspace and threshold units are incompatible")
    if row.threshold.value is not None and row.threshold.value <= 0:
        blockers.append("threshold must be greater than zero")
    if blockers:
        return _invalid_row(row, blockers, limitations)

    if (
        row.headspace.basis is EvidenceBasis.UNKNOWN
        or row.threshold.basis is EvidenceBasis.UNKNOWN
    ):
        limitations.append("An unknown quantitative field prevents OAV calculation.")
        return OAVMaterialEvidenceResult(
            material_name=row.material_name,
            canonical_name=row.canonical_name,
            state=OAVEvidenceState.ABSTAINED,
            headspace_basis=row.headspace.basis,
            threshold_basis=row.threshold.basis,
            oav=None,
            threshold_screening="NOT_COMPUTABLE",
            recognizable_in_mixture=None,
            constituent_evidence_count=len(row.constituent_evidence),
            blockers=(),
            limitations=tuple(limitations),
        )

    oav_value = float(row.headspace.value or 0.0) / float(row.threshold.value or 1.0)
    threshold_screening = (
        "ABOVE_OR_AT_THRESHOLD" if oav_value >= 1 else "BELOW_THRESHOLD"
    )
    incomplete_lineage = (
        row.exact_stock_ref is None
        or row.supplied_strength_fraction is None
        or row.active_mass_g is None
        or (
            row.supplied_strength_fraction is not None
            and row.supplied_strength_fraction < 1
            and row.carrier is None
        )
    )
    transferred = EvidenceBasis.TRANSFERRED in {
        row.headspace.basis,
        row.threshold.basis,
    }
    natural_uncertainty = row.natural_or_preblend
    if incomplete_lineage:
        limitations.append("Exact stock or active-dose lineage is incomplete.")
    if transferred:
        limitations.append("At least one quantitative value is transferred evidence.")
    if natural_uncertainty:
        limitations.append(
            "The natural or preblend remains one formula row with constituent uncertainty."
        )
    if incomplete_lineage or transferred or natural_uncertainty:
        state = OAVEvidenceState.PARTIAL
    elif EvidenceBasis.MODELED in {row.headspace.basis, row.threshold.basis}:
        state = OAVEvidenceState.MODELED_SCREEN
        limitations.insert(
            0,
            "Modeled headspace or threshold is a prediction screen, not observed behavior.",
        )
    else:
        state = OAVEvidenceState.STRICT_MEASURED
    return OAVMaterialEvidenceResult(
        material_name=row.material_name,
        canonical_name=row.canonical_name,
        state=state,
        headspace_basis=row.headspace.basis,
        threshold_basis=row.threshold.basis,
        oav=oav_value,
        threshold_screening=threshold_screening,
        recognizable_in_mixture=None,
        constituent_evidence_count=len(row.constituent_evidence),
        blockers=(),
        limitations=tuple(limitations),
    )


def evaluate_oav_evidence(request: OAVEvidenceRequest) -> OAVEvidenceResult:
    """Evaluate row-level OAV evidence without aggregate sensory authority."""

    if not isinstance(request, OAVEvidenceRequest):
        raise TypeError("request must be an OAVEvidenceRequest")
    blockers: list[str] = []
    names = [row.material_name.casefold() for row in request.rows]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        blockers.append("duplicate material row: " + ", ".join(duplicates))
    rows = tuple(
        _evaluate_row(row, request.measurement_context) for row in request.rows
    )
    blockers.extend(
        f"{row.material_name}: {blocker}"
        for row in rows
        for blocker in row.blockers
    )
    row_states = {row.state for row in rows}
    if blockers or OAVEvidenceState.INVALID in row_states:
        state = OAVEvidenceState.INVALID
    elif not rows or row_states == {OAVEvidenceState.ABSTAINED}:
        state = OAVEvidenceState.ABSTAINED
    elif OAVEvidenceState.ABSTAINED in row_states or OAVEvidenceState.PARTIAL in row_states:
        state = OAVEvidenceState.PARTIAL
    elif row_states == {OAVEvidenceState.STRICT_MEASURED}:
        state = OAVEvidenceState.STRICT_MEASURED
    else:
        state = OAVEvidenceState.MODELED_SCREEN
    limitations = (
        "OAV rows cannot establish odor contribution, balance, diffusion, liking, beauty, synergy, similarity, or release readiness.",
        "Perceptible-material count cannot increase evidence authority.",
    )
    return OAVEvidenceResult(
        state=state,
        formula_sha256=request.formula_sha256,
        dose_receipt_sha256=request.dose_receipt_sha256,
        measurement_context=request.measurement_context,
        rows=rows,
        blockers=tuple(blockers),
        limitations=limitations,
    )


def _lookup(mapping: Mapping[str, Any], name: str, canonical_name: str) -> Any:
    if name in mapping:
        return mapping[name]
    return mapping.get(canonical_name)


def oav_evidence_request_from_formula_state(
    state: FormulaState,
    *,
    formula_sha256: str,
    dose_receipt_sha256: str,
    exact_stock_refs: Mapping[str, str],
    model_source: EvidenceSourceRef,
    threshold_sources: Mapping[str, EvidenceSourceRef],
) -> OAVEvidenceRequest:
    """Adapt modeled FormulaState values without upgrading their evidence basis."""

    if not isinstance(state, FormulaState):
        raise TypeError("state must be a FormulaState")
    if not isinstance(model_source, EvidenceSourceRef):
        raise TypeError("model_source must be an EvidenceSourceRef")
    rows: list[OAVMaterialEvidenceInput] = []
    for material in state.materials:
        threshold_source = _lookup(
            threshold_sources, material.name, material.canonical_name
        )
        if material.odt_air_ppm is None or threshold_source is None:
            threshold = QuantitativeEvidence(
                value=None,
                unit="",
                context="",
                method="",
                basis=EvidenceBasis.UNKNOWN,
                source=None,
            )
        else:
            threshold = QuantitativeEvidence(
                value=float(material.odt_air_ppm),
                unit="ppm",
                context=state.context,
                method=str(material.sources.get("odt", "formula-state ODT lookup")),
                basis=EvidenceBasis.TRANSFERRED,
                source=threshold_source,
            )
        rows.append(
            OAVMaterialEvidenceInput(
                material_name=material.name,
                canonical_name=material.canonical_name,
                exact_stock_ref=_lookup(
                    exact_stock_refs, material.name, material.canonical_name
                ),
                supplied_strength_fraction=(
                    float(material.dilution) if material.stock_declared else None
                ),
                carrier=material.stock_carrier or None,
                active_mass_g=material.authoritative_active_g,
                formula_matrix=state.headspace_basis,
                headspace=QuantitativeEvidence(
                    value=float(material.vapor_ppm),
                    unit="ppm",
                    context=state.context,
                    method=state.headspace_basis,
                    basis=EvidenceBasis.MODELED,
                    source=model_source,
                ),
                threshold=threshold,
                natural_or_preblend=(
                    material.is_opaque_preblend
                    or "natural_composite" in material.sources
                ),
                constituent_evidence=(),
            )
        )
    return OAVEvidenceRequest(
        formula_sha256=formula_sha256,
        dose_receipt_sha256=dose_receipt_sha256,
        measurement_context=state.context,
        rows=tuple(rows),
    )


__all__ = [
    "OAVEvidenceRequest",
    "OAVEvidenceResult",
    "OAVEvidenceState",
    "OAVMaterialEvidenceInput",
    "OAVMaterialEvidenceResult",
    "evaluate_oav_evidence",
    "oav_evidence_request_from_formula_state",
]
