"""Versioned, conservative safety assessment for finished perfume products.

This module does not certify IFRA compliance. It evaluates supplied finished-
product mass fractions against a supplied, versioned restriction snapshot.
Incomplete evidence prevents ``pass``; an already demonstrated limit exceedance
remains ``fail`` because unresolved constituents cannot reverse that violation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Mapping

from engine.quantities import Concentration, ConcentrationBasis
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class SafetyAssessmentStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNVERIFIED = "unverified"


@dataclass(frozen=True, slots=True)
class RestrictionEntry:
    """One maximum use level for a material in a finished-product category."""

    material: str
    category: str
    maximum: Concentration

    def __post_init__(self) -> None:
        material = self.material.strip()
        category = self.category.strip()
        if not material or not category:
            raise ValueError("restriction material and category must not be empty")
        if self.maximum.basis is not ConcentrationBasis.MASS_FRACTION:
            raise ValueError("restriction maximum must use a mass-fraction basis")
        if self.maximum.medium != "finished_product":
            raise ValueError("restriction maximum medium must be finished_product")
        object.__setattr__(self, "material", material)
        object.__setattr__(self, "category", category)


@dataclass(frozen=True, slots=True)
class RestrictionDataset:
    """A caller-supplied snapshot of restrictions and explicit coverage."""

    source_name: str
    amendment: str
    source_url: str
    entries: tuple[RestrictionEntry, ...] = ()
    covered_materials: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ConstituentComposition:
    """Regulatory constituent contributions declared for an opaque mixture.

    ``complete`` means all constituents relevant to the supplied restriction
    dataset have been disclosed; the listed fractions need not sum to one.
    """

    fractions: Mapping[str, float]
    complete: bool
    source: str

    def __post_init__(self) -> None:
        normalized: dict[str, float] = {}
        for raw_name, raw_fraction in self.fractions.items():
            name = str(raw_name).strip()
            fraction = float(raw_fraction)
            if not name:
                raise ValueError("constituent names must not be empty")
            if not isfinite(fraction) or not 0 <= fraction <= 1:
                raise ValueError("constituent fractions must be finite values from zero to one")
            normalized[name] = fraction
        if sum(normalized.values()) > 1.0 + 1e-12:
            raise ValueError("constituent fractions must not sum above one")
        object.__setattr__(self, "fractions", normalized)
        object.__setattr__(self, "source", self.source.strip())


@dataclass(frozen=True, slots=True)
class SafetyAssessmentRequest:
    """Inputs needed to make a bounded restriction assessment."""

    category: str
    concentrations: Mapping[str, Concentration]
    dataset: RestrictionDataset | None
    opaque_mixtures: frozenset[str] = frozenset()
    constituent_compositions: Mapping[str, ConstituentComposition] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class SafetyFinding:
    material: str
    concentration_ppm_w_w: float
    maximum_ppm_w_w: float
    ratio_to_limit: float
    within_limit: bool


@dataclass(frozen=True, slots=True)
class SafetyAssessmentResult:
    status: SafetyAssessmentStatus
    loads_ppm_w_w: Mapping[str, float]
    findings: tuple[SafetyFinding, ...]
    unresolved_inputs: tuple[str, ...]
    evidence: EvidenceDescriptor


def assess_safety(request: SafetyAssessmentRequest) -> SafetyAssessmentResult:
    """Assess restrictions without converting missing evidence into a pass."""

    category = request.category.strip()
    unresolved: list[str] = []
    if not category:
        unresolved.append("product category")

    dataset = request.dataset
    if dataset is None:
        unresolved.append("versioned restriction dataset")
    else:
        if not dataset.source_name.strip():
            unresolved.append("restriction dataset source name")
        if not dataset.amendment.strip():
            unresolved.append("restriction dataset amendment")
        if not dataset.source_url.strip():
            unresolved.append("restriction dataset source URL")

    opaque = {_key(name): str(name).strip() for name in request.opaque_mixtures}
    compositions = {
        _key(name): composition
        for name, composition in request.constituent_compositions.items()
    }
    loads: dict[str, float] = {}
    display_names: dict[str, str] = {}

    for raw_material, concentration in request.concentrations.items():
        material = str(raw_material).strip()
        key = _key(material)
        if concentration.basis is not ConcentrationBasis.MASS_FRACTION:
            unresolved.append(f"finished-product mass fraction required: {material}")
            continue
        if concentration.medium != "finished_product":
            unresolved.append(f"finished_product medium required: {material}")
            continue

        if key not in opaque:
            _add_load(loads, display_names, material, concentration.ppm)
            continue

        composition = compositions.get(key)
        if composition is None:
            unresolved.append(f"missing constituent composition: {material}")
            continue
        if not composition.complete:
            unresolved.append(f"incomplete constituent composition: {material}")
        if not composition.source:
            unresolved.append(f"missing constituent source: {material}")
        for constituent, fraction in composition.fractions.items():
            _add_load(
                loads,
                display_names,
                constituent,
                concentration.ppm * fraction,
            )

    findings: list[SafetyFinding] = []
    if dataset is not None:
        covered = {_key(name) for name in dataset.covered_materials}
        for key in loads:
            if key not in covered:
                unresolved.append(
                    f"restriction coverage missing: {display_names[key]}"
                )

        restrictions = {
            _key(entry.material): entry
            for entry in dataset.entries
            if entry.category == category
        }
        for key, load_ppm in loads.items():
            entry = restrictions.get(key)
            if entry is None:
                continue
            maximum_ppm = entry.maximum.ppm
            ratio = load_ppm / maximum_ppm if maximum_ppm > 0 else float("inf")
            findings.append(
                SafetyFinding(
                    material=entry.material,
                    concentration_ppm_w_w=round(load_ppm, 12),
                    maximum_ppm_w_w=round(maximum_ppm, 12),
                    ratio_to_limit=round(ratio, 12),
                    within_limit=load_ppm <= maximum_ppm,
                )
            )

    has_violation = any(not finding.within_limit for finding in findings)
    if has_violation:
        status = SafetyAssessmentStatus.FAIL
    elif unresolved:
        status = SafetyAssessmentStatus.UNVERIFIED
    else:
        status = SafetyAssessmentStatus.PASS

    evidence = _evidence(status, category, dataset)
    return SafetyAssessmentResult(
        status=status,
        loads_ppm_w_w={
            display_names[key]: round(value, 12) for key, value in loads.items()
        },
        findings=tuple(sorted(findings, key=lambda item: item.material.casefold())),
        unresolved_inputs=tuple(dict.fromkeys(unresolved)),
        evidence=evidence,
    )


def _evidence(
    status: SafetyAssessmentStatus,
    category: str,
    dataset: RestrictionDataset | None,
) -> EvidenceDescriptor:
    if status is SafetyAssessmentStatus.UNVERIFIED:
        return EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis="Restriction assessment withheld because required regulatory evidence is incomplete.",
            sources=("engine.safety_assessment",),
            limitations=("This output is not an IFRA certificate or legal opinion.",),
        )
    assert dataset is not None
    return EvidenceDescriptor(
        classification=ScientificClass.LITERATURE_DERIVED,
        basis=(
            f"Finished-product mass fractions evaluated for category {category} "
            f"against {dataset.source_name}, {dataset.amendment}."
        ),
        sources=(dataset.source_url, "engine.safety_assessment"),
        assumptions=("The supplied dataset snapshot and constituent disclosures are applicable.",),
        limitations=("This output is not an IFRA certificate or legal opinion.",),
    )


def _key(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _add_load(
    loads: dict[str, float],
    display_names: dict[str, str],
    material: str,
    ppm: float,
) -> None:
    key = _key(material)
    display_names.setdefault(key, str(material).strip())
    loads[key] = loads.get(key, 0.0) + float(ppm)


__all__ = [
    "ConstituentComposition",
    "RestrictionDataset",
    "RestrictionEntry",
    "SafetyAssessmentRequest",
    "SafetyAssessmentResult",
    "SafetyAssessmentStatus",
    "SafetyFinding",
    "assess_safety",
]
