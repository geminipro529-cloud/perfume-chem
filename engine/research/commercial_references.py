"""Governed commercial-reference identities, panels, samples, and evaluation.

Commercial success is useful for selecting relevant comparison products.  It
is not a sensory observation, a liking label, or evidence of a proprietary
formula.  This module makes those authority boundaries executable and keeps
runtime comparison offline against a reviewed local registry.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPOSITORY_ROOT / "data" / "governance" / "commercial_reference_registry_v1.json"
)

EVIDENCE_CLASSES = {
    "AUDITED_OR_ISSUER_MARKET_PANEL",
    "MULTIBRAND_RETAIL_BESTSELLER",
    "OFFICIAL_PRODUCT_ARCHITECTURE",
    "DECLARED_INGREDIENT_LIST",
    "EXACT_SAMPLE_ANALYTICAL_PROFILE",
    "BLINDED_SENSORY_PROFILE",
    "PERSONAL_LIKING",
    "TARGET_POPULATION_LIKING",
}
MARKET_SCOPES = {"EXACT_PRODUCT", "PRODUCT_LINE", "FRAGRANCE_FRANCHISE"}
COMPARISON_EVIDENCE_MODES = {
    "DOCUMENT_ONLY",
    "QUICK_BLIND",
    "CONTROLLED_PERSONAL",
    "TARGET_POPULATION",
}


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} must be non-empty text")
    return text


def _sha(value: str, field: str) -> str:
    normalized = value.strip().casefold()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ValueError(f"{field} must be lowercase SHA-256")
    return normalized


def _date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be ISO date text") from exc


def _url(value: str, field: str) -> str:
    text = _text(value, field)
    if not text.startswith("https://"):
        raise ValueError(f"{field} must use https")
    return text


@dataclass(frozen=True, slots=True)
class CommercialProductIdentityV1:
    product_id: str
    franchise_id: str
    brand: str
    product_name: str
    concentration: str
    edition: str
    launch_version_scope: str
    region: str
    official_product_url: str
    official_page_snapshot_sha256: str
    official_page_snapshot_basis: str
    marketed_family: str
    marketed_facets: tuple[str, ...]
    marketed_note_architecture: Mapping[str, Sequence[str]]
    formula_composition_known: bool
    market_position_authority: bool
    official_architecture_authority: bool
    analytical_composition_authority: bool
    sensory_profile_authority: bool
    liking_authority: bool

    def __post_init__(self) -> None:
        for field in (
            "product_id",
            "franchise_id",
            "brand",
            "product_name",
            "concentration",
            "edition",
            "launch_version_scope",
            "region",
            "marketed_family",
            "official_page_snapshot_basis",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "official_product_url", _url(self.official_product_url, "official_product_url"))
        object.__setattr__(
            self,
            "official_page_snapshot_sha256",
            _sha(self.official_page_snapshot_sha256, "official_page_snapshot_sha256"),
        )
        facets = tuple(_text(value, "marketed facet") for value in self.marketed_facets)
        if not facets:
            raise ValueError("marketed_facets must not be empty")
        object.__setattr__(self, "marketed_facets", facets)
        architecture = {
            _text(stage, "architecture stage"): tuple(
                _text(note, "marketed note") for note in notes
            )
            for stage, notes in self.marketed_note_architecture.items()
        }
        if not architecture or any(not notes for notes in architecture.values()):
            raise ValueError("marketed_note_architecture must contain non-empty stages")
        object.__setattr__(self, "marketed_note_architecture", architecture)
        for field in (
            "formula_composition_known",
            "market_position_authority",
            "official_architecture_authority",
            "analytical_composition_authority",
            "sensory_profile_authority",
            "liking_authority",
        ):
            if not isinstance(getattr(self, field), bool):
                raise TypeError(f"{field} must be boolean")
        if self.formula_composition_known and not self.analytical_composition_authority:
            raise ValueError("known formula composition requires analytical composition authority")

    @property
    def display_name(self) -> str:
        return f"{self.brand} {self.product_name} {self.concentration}"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CommercialReferenceEvidenceV1:
    evidence_id: str
    evidence_class: str
    title: str
    url: str
    source_snapshot_sha256: str
    source_snapshot_basis: str
    reviewed_on: str
    expires_on: str | None
    product_ids: tuple[str, ...]
    market_scope: str | None
    claim_scope: str
    usable_for_panel_selection: bool
    supplies_liking_label: bool
    retraction_state: str

    def __post_init__(self) -> None:
        for field in (
            "evidence_id",
            "title",
            "claim_scope",
            "retraction_state",
            "source_snapshot_basis",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(f"unsupported commercial evidence class: {self.evidence_class}")
        object.__setattr__(self, "url", _url(self.url, "url"))
        object.__setattr__(self, "source_snapshot_sha256", _sha(self.source_snapshot_sha256, "source_snapshot_sha256"))
        _date(self.reviewed_on, "reviewed_on")
        if self.expires_on is not None:
            _date(self.expires_on, "expires_on")
        product_ids = tuple(_text(value, "product_id") for value in self.product_ids)
        object.__setattr__(self, "product_ids", product_ids)
        if self.market_scope is not None and self.market_scope not in MARKET_SCOPES:
            raise ValueError(f"unsupported market_scope: {self.market_scope}")
        if self.supplies_liking_label and self.evidence_class not in {
            "PERSONAL_LIKING",
            "TARGET_POPULATION_LIKING",
        }:
            raise ValueError("market, retail, official-note, and analytical evidence cannot supply liking labels")
        if self.retraction_state == "RETRACTED" and self.usable_for_panel_selection:
            raise ValueError("retracted evidence cannot be selectable")

    def is_current(self, as_of: date) -> bool:
        return self.expires_on is None or _date(self.expires_on, "expires_on") >= as_of

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CommercialReferencePanelV1:
    panel_id: str
    concept_tags: tuple[str, ...]
    as_of_date: str
    expires_on: str
    active_members: tuple[Mapping[str, Any], ...]
    reserve_members: tuple[Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "panel_id", _text(self.panel_id, "panel_id"))
        tags = tuple(_text(value, "concept tag").casefold() for value in self.concept_tags)
        if not tags:
            raise ValueError("commercial panel needs concept tags")
        object.__setattr__(self, "concept_tags", tags)
        _date(self.as_of_date, "as_of_date")
        _date(self.expires_on, "expires_on")
        active = tuple(dict(row) for row in self.active_members)
        reserve = tuple(dict(row) for row in self.reserve_members)
        if not 1 <= len(active) <= 4:
            raise ValueError("commercial panel must contain one to four active references")
        ids = [str(row.get("product_id", "")).strip() for row in (*active, *reserve)]
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("commercial panel product identities must be non-empty and unique")
        if sum(bool(row.get("market_anchor")) for row in active) < 2:
            raise ValueError("commercial panel needs at least two current market anchors")
        if sum(bool(row.get("structural_neighbour")) for row in active) < 2:
            raise ValueError("commercial panel needs at least two structural neighbours")
        for row in (*active, *reserve):
            _text(row.get("role"), "panel member role")
            _text(row.get("reason"), "panel member reason")
        object.__setattr__(self, "active_members", active)
        object.__setattr__(self, "reserve_members", reserve)
        object.__setattr__(self, "evidence_ids", tuple(_text(value, "evidence_id") for value in self.evidence_ids))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def sha256(self) -> str:
        return stable_payload_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class CommercialReferenceSampleV1:
    sample_identifier: str
    product_id: str
    concentration: str
    edition: str
    commercial_registry_sha256: str
    purchase_source: str | None = None
    batch_code: str | None = None
    acquisition_date: str | None = None
    authenticity_documentation_state: str = "NOT_PROVIDED_PERSONAL_MODE"

    def __post_init__(self) -> None:
        for field in ("sample_identifier", "product_id", "concentration", "edition", "authenticity_documentation_state"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "commercial_registry_sha256", _sha(self.commercial_registry_sha256, "commercial_registry_sha256"))
        for field in ("purchase_source", "batch_code"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _text(value, field))
        if self.acquisition_date is not None:
            _date(self.acquisition_date, "acquisition_date")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": "commercial-reference-sample-v1",
            **asdict(self),
            "photograph_required": False,
            "personal_comparison_allowed": True,
            **FALSE_ACTION_AUTHORITY,
        }
        return {**payload, "sample_sha256": stable_payload_hash(payload)}


@dataclass(frozen=True, slots=True)
class CommercialReferenceRegistryV1:
    products: Mapping[str, CommercialProductIdentityV1]
    evidence: Mapping[str, CommercialReferenceEvidenceV1]
    panels: Mapping[str, CommercialReferencePanelV1]
    prohibited_sources: tuple[Mapping[str, Any], ...]
    historical_provisional_paths: tuple[str, ...]
    source_path: str
    registry_sha256: str


def load_commercial_reference_registry(
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> CommercialReferenceRegistryV1:
    source = Path(path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "commercial-reference-registry-v1":
        raise ValueError("unsupported commercial-reference registry schema")
    products = {
        row["product_id"]: CommercialProductIdentityV1(**row)
        for row in raw.get("products", [])
    }
    evidence = {
        row["evidence_id"]: CommercialReferenceEvidenceV1(**row)
        for row in raw.get("evidence", [])
    }
    panels = {
        row["panel_id"]: CommercialReferencePanelV1(**row)
        for row in raw.get("panels", [])
    }
    if len(products) != len(raw.get("products", [])):
        raise ValueError("duplicate commercial product identity")
    if len(evidence) != len(raw.get("evidence", [])):
        raise ValueError("duplicate commercial evidence identity")
    if len(panels) != len(raw.get("panels", [])):
        raise ValueError("duplicate commercial panel identity")
    for panel in panels.values():
        member_ids = [row["product_id"] for row in (*panel.active_members, *panel.reserve_members)]
        if any(product_id not in products for product_id in member_ids):
            raise ValueError(f"panel {panel.panel_id} references an unknown product")
        franchises = [products[product_id].franchise_id for product_id in member_ids]
        if len(franchises) != len(set(franchises)):
            raise ValueError(f"panel {panel.panel_id} contains duplicate franchise members")
        if any(evidence_id not in evidence for evidence_id in panel.evidence_ids):
            raise ValueError(f"panel {panel.panel_id} references unknown evidence")
    prohibited = tuple(dict(row) for row in raw.get("prohibited_sources", []))
    if not any(
        row.get("title") == "Social success of perfumes" and row.get("status") == "RETRACTED_REJECTED"
        for row in prohibited
    ):
        raise ValueError("retracted Social success of perfumes source must be explicitly rejected")
    registry_sha256 = stable_payload_hash(raw)
    return CommercialReferenceRegistryV1(
        products=products,
        evidence=evidence,
        panels=panels,
        prohibited_sources=prohibited,
        historical_provisional_paths=tuple(raw.get("historical_provisional_paths", [])),
        source_path=source.as_posix(),
        registry_sha256=registry_sha256,
    )


def build_commercial_reference_panel(
    concept_tags: Sequence[str],
    *,
    as_of_date: str,
    registry: CommercialReferenceRegistryV1 | None = None,
    panel_id: str | None = None,
) -> dict[str, Any]:
    """Select and validate one predeclared, concept-matched current panel."""

    registry = registry or load_commercial_reference_registry()
    as_of = _date(as_of_date, "as_of_date")
    tags = {str(value).strip().casefold() for value in concept_tags if str(value).strip()}
    if not tags:
        raise ValueError("at least one concept tag is required")
    if panel_id is not None:
        candidates = [registry.panels.get(panel_id)]
        if candidates[0] is None:
            raise KeyError(f"unknown commercial panel: {panel_id}")
    else:
        candidates = sorted(
            registry.panels.values(),
            key=lambda panel: (-len(tags & set(panel.concept_tags)), panel.panel_id),
        )
    panel = candidates[0]
    assert panel is not None
    if not (tags & set(panel.concept_tags)):
        raise ValueError("no commercial panel matches the requested concept")
    if _date(panel.expires_on, "expires_on") < as_of:
        raise ValueError("COMMERCIAL_REFERENCE_PANEL_EXPIRED")
    referenced_evidence = [registry.evidence[value] for value in panel.evidence_ids]
    if any(not row.is_current(as_of) for row in referenced_evidence):
        raise ValueError("COMMERCIAL_REFERENCE_EVIDENCE_EXPIRED")
    if any(not row.usable_for_panel_selection for row in referenced_evidence):
        raise ValueError("COMMERCIAL_REFERENCE_EVIDENCE_NOT_SELECTABLE")
    products = {
        product_id: registry.products[product_id].as_dict()
        for product_id in [row["product_id"] for row in (*panel.active_members, *panel.reserve_members)]
    }
    result = {
        "schema_version": "commercial-reference-panel-result-v1",
        "status": "MARKET_SELECTED_REFERENCE_PANEL",
        "panel": panel.as_dict(),
        "panel_sha256": panel.sha256,
        "registry_sha256": registry.registry_sha256,
        "products": products,
        "evidence": [row.as_dict() for row in referenced_evidence],
        "selection_scope": "MARKET_POSITION_AND_OFFICIAL_ARCHITECTURE_ONLY",
        "proprietary_composition_state": "PROPRIETARY_COMPOSITION_UNKNOWN",
        "population_liking_state": "POPULATION_LIKING_NOT_ESTABLISHED",
        "most_liked_claim": False,
        "best_composition_claim": False,
        "proven_hedonic_target_claim": False,
        **FALSE_ACTION_AUTHORITY,
    }
    return {**result, "result_sha256": stable_payload_hash(result)}


def evaluate_reference_panel(
    *,
    target_snapshot_id: str,
    target_snapshot_sha256: str,
    request_interpretation_sha256: str,
    reference_panel_id: str,
    reference_panel_sha256: str,
    comparison_evidence: str,
    observation_record_ids: Sequence[str],
    seed: int,
    as_of_date: str,
    registry: CommercialReferenceRegistryV1 | None = None,
) -> dict[str, Any]:
    """Evaluate only the evidence channel authorized by the supplied mode."""

    if comparison_evidence not in COMPARISON_EVIDENCE_MODES:
        raise ValueError(f"unsupported comparison evidence mode: {comparison_evidence}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    _text(target_snapshot_id, "target_snapshot_id")
    _sha(target_snapshot_sha256, "target_snapshot_sha256")
    _sha(request_interpretation_sha256, "request_interpretation_sha256")
    _sha(reference_panel_sha256, "reference_panel_sha256")
    registry = registry or load_commercial_reference_registry()
    selected_panel = registry.panels.get(reference_panel_id)
    if selected_panel is None:
        raise KeyError(f"unknown commercial panel: {reference_panel_id}")
    panel_result = build_commercial_reference_panel(
        selected_panel.concept_tags,
        as_of_date=as_of_date,
        registry=registry,
        panel_id=reference_panel_id,
    )
    if panel_result["panel_sha256"] != reference_panel_sha256:
        raise ValueError("REFERENCE_PANEL_HASH_MISMATCH")
    products = panel_result["products"]
    active = panel_result["panel"]["active_members"]
    architecture = [
        {
            "product_id": member["product_id"],
            "role": member["role"],
            "reason": member["reason"],
            "marketed_family": products[member["product_id"]]["marketed_family"],
            "marketed_facets": products[member["product_id"]]["marketed_facets"],
            "marketed_note_architecture": products[member["product_id"]]["marketed_note_architecture"],
            "comparison_authority": "MARKETED_ARCHITECTURE_ONLY",
        }
        for member in active
    ]
    observation_ids = tuple(_text(value, "observation_record_id") for value in observation_record_ids)
    findings: list[str] = []
    validation_state = "ADVISORY_COMPLETE"
    applicability_state = "PARTIAL"
    documentary_state = "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
    if comparison_evidence != "DOCUMENT_ONLY":
        if not observation_ids:
            findings.append("OBSERVATION_RECORDS_REQUIRED_FOR_SELECTED_COMPARISON_MODE")
        else:
            # IDs are provenance, not the observations themselves.  A
            # server-owned observation resolver/admission review must supply
            # endpoint values before this isolated engine job can compare them.
            findings.append("OBSERVATION_RECORDS_BOUND_NOT_ADJUDICATED")
        validation_state = "WITHHOLD_UNKNOWN"
        applicability_state = "UNAVAILABLE"

    report = {
        "schema_version": "reference-panel-evaluation-v1",
        "target_snapshot_id": target_snapshot_id,
        "target_snapshot_sha256": target_snapshot_sha256,
        "request_interpretation_sha256": request_interpretation_sha256,
        "reference_panel_id": reference_panel_id,
        "reference_panel_sha256": reference_panel_sha256,
        "comparison_evidence": comparison_evidence,
        "seed": seed,
        "market_positioning": {
            "state": "MARKET_SELECTED_REFERENCE_PANEL",
            "claim_scope": "REFERENCE_SELECTION_NOT_LIKING",
            "evidence": panel_result["evidence"],
        },
        "official_architecture_comparison": {
            "state": documentary_state,
            "references": architecture,
            "target_sensory_distance_established": False,
        },
        "analytical_comparison": {"state": "UNAVAILABLE_EXACT_SAMPLE_ANALYSIS_NOT_SUPPLIED"},
        "sensory_character_comparison": {"state": "NOT_ESTABLISHED"},
        "intensity_comparison": {"state": "NOT_ESTABLISHED"},
        "personal_liking": {"state": "NOT_ESTABLISHED"},
        "target_population_liking": {"state": "POPULATION_LIKING_NOT_ESTABLISHED"},
        "request_fulfilment": {"state": "NOT_PHYSICALLY_TESTED"},
        "observation_record_ids": list(observation_ids),
        "findings": findings,
        "applicability": {
            "state": applicability_state,
            "documentary_architecture": "APPLICABLE",
            "sensory_and_liking": "UNAVAILABLE",
        },
        "selection": {
            "status": (
                "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
                if comparison_evidence == "DOCUMENT_ONLY"
                else "UNORDERED_HYPOTHESES"
            ),
            "ranked_candidates": [],
            "unordered_candidates": [],
            "formula_action": "NO_CHANGE",
            "reason_codes": findings or ["DOCUMENT_ONLY_CANNOT_SELECT_SENSORY_WINNER"],
        },
        "validation_state": validation_state,
        "proprietary_composition_state": "PROPRIETARY_COMPOSITION_UNKNOWN",
        "formula_modified": False,
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "evaluation_sha256": stable_payload_hash(report)}


__all__ = [
    "COMPARISON_EVIDENCE_MODES",
    "CommercialProductIdentityV1",
    "CommercialReferenceEvidenceV1",
    "CommercialReferencePanelV1",
    "CommercialReferenceRegistryV1",
    "CommercialReferenceSampleV1",
    "build_commercial_reference_panel",
    "evaluate_reference_panel",
    "load_commercial_reference_registry",
]
