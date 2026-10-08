"""Governed commercial-reference identities, panels, samples, and evaluation.

Commercial success is useful for selecting relevant comparison products.  It
is not a sensory observation, a liking label, or evidence of a proprietary
formula.  This module makes those authority boundaries executable and keeps
runtime comparison offline against a reviewed local registry.
"""

from __future__ import annotations

import calendar
import json
import re
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from .request_interpretation import positive_reference_text

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = (
    REPOSITORY_ROOT / "data" / "governance" / "commercial_reference_registry_v3.json"
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
MARKET_EVIDENCE_CLASSES = {"AUDITED_OR_ISSUER_MARKET_PANEL", "MULTIBRAND_RETAIL_BESTSELLER"}


def _market_deadline(period_end: date) -> date:
    year = period_end.year + 1
    return period_end.replace(year=year, day=min(period_end.day, calendar.monthrange(year, period_end.month)[1]))


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
    source_period_start: str | None = None
    source_period_end: str | None = None
    published_on: str | None = None
    market_region: str | None = None
    market_channel: str | None = None
    metric: str | None = None

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
        for field in ("usable_for_panel_selection", "supplies_liking_label"):
            if type(getattr(self, field)) is not bool:
                raise TypeError(f"{field} must be boolean")
        if (self.source_period_start is None) != (self.source_period_end is None):
            raise ValueError("market period requires both start and end")
        if self.source_period_end is not None:
            assert self.source_period_start is not None
            if _date(self.source_period_start, "source_period_start") > _date(self.source_period_end, "source_period_end"):
                raise ValueError("market period is reversed")
        if self.published_on is not None:
            published = _date(self.published_on, "published_on")
            if published > _date(self.reviewed_on, "reviewed_on"):
                raise ValueError("publication is later than recorded review")
            if self.source_period_end and published < _date(self.source_period_end, "source_period_end"):
                raise ValueError("publication precedes observed period end")
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
        if self.retraction_state in {"RETRACTED", "EXPRESSION_OF_CONCERN"}:
            return False
        if _date(self.reviewed_on, "reviewed_on") > as_of:
            return False
        if self.published_on and _date(self.published_on, "published_on") > as_of:
            return False
        if self.expires_on and _date(self.expires_on, "expires_on") < as_of:
            return False
        if self.evidence_class in MARKET_EVIDENCE_CLASSES:
            # A later review of an old report does not create new observations.
            if not self.source_period_end or not self.source_period_start:
                return False
            period_end = _date(self.source_period_end, "source_period_end")
            return period_end <= as_of <= _market_deadline(period_end)
        return True

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
            for field in ("market_anchor", "structural_neighbour"):
                if type(row.get(field)) is not bool:
                    raise TypeError(f"panel {field} must be boolean")
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
    selection_rules: Mapping[str, Mapping[str, Any]] = dataclass_field(default_factory=dict)


def load_commercial_reference_registry(
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> CommercialReferenceRegistryV1:
    source = Path(path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid commercial-reference registry shape")
    if raw.get("schema_version") not in {"commercial-reference-registry-v1", "commercial-reference-registry-v2", "commercial-reference-registry-v3"}:
        raise ValueError("unsupported commercial-reference registry schema")
    if raw["schema_version"] in {"commercial-reference-registry-v2", "commercial-reference-registry-v3"}:
        authority = raw.get("authority")
        if not isinstance(authority, dict) or any(authority.get(key) is not False for key in FALSE_ACTION_AUTHORITY):
            raise ValueError("commercial evidence cannot grant action authority")
        _sha(raw.get("predecessor_sha256", ""), "predecessor_sha256")
        if raw.get("market_expiry_policy") != "TWELVE_CALENDAR_MONTHS_AFTER_SOURCE_PERIOD_END_REVIEW_CANNOT_RENEW":
            raise ValueError("unsupported market expiry policy")
        for row in raw.get("evidence", []):
            if row.get("evidence_class") in MARKET_EVIDENCE_CLASSES:
                for field in ("source_period_start", "source_period_end", "market_region", "market_channel", "metric"):
                    if not isinstance(row.get(field), str) or not row[field].strip():
                        raise ValueError(f"market evidence requires {field}")
    rules = raw.get("selection_rules", {})
    if raw["schema_version"] == "commercial-reference-registry-v3":
        predecessor = REPOSITORY_ROOT / "data/governance/commercial_reference_registry_v2.json"
        if raw.get("predecessor_path") != "data/governance/commercial_reference_registry_v2.json" or sha256(predecessor.read_bytes()).hexdigest() != raw["predecessor_sha256"]:
            raise ValueError("COMMERCIAL_REGISTRY_PREDECESSOR_DRIFT")
        if not isinstance(rules, dict) or set(rules) != {row["panel_id"] for row in raw.get("panels", [])}:
            raise ValueError("every v3 panel requires a selection rule")
        for rule in rules.values():
            if not isinstance(rule, dict) or set(rule) != {"required_any_tag_groups"}:
                raise ValueError("invalid panel selection rule")
            groups = rule["required_any_tag_groups"]
            if not isinstance(groups, list) or not groups or any(not isinstance(group, list) or not group or any(not isinstance(tag, str) or not tag.strip() for tag in group) for group in groups):
                raise ValueError("invalid panel signature groups")
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
        selection_rules=rules,
    )




def resolve_documentary_references(text: str, *, as_of_date: str, registry: CommercialReferenceRegistryV1 | None = None) -> dict[str, Any]:
    """Named products are documentary hints, never authenticated sample bindings."""
    registry = registry or load_commercial_reference_registry()
    as_of = _date(as_of_date, "as_of_date")
    positive = positive_reference_text(text).casefold()
    products: list[CommercialProductIdentityV1] = []
    unresolved = []
    for product in registry.products.values():
        match = re.search(rf"(?<!\w){re.escape(product.product_name.casefold())}(?!\w)", positive)
        if match is None:
            continue
        suffix = re.split(r"[,;.]|\band\b|\bwith\b|\bwithout\b", positive[match.end():], maxsplit=1)[0].strip()
        concentration = re.match(r"(eau de parfum|eau de toilette|edp|edt|cologne|parfum)\b", suffix)
        expected = {"eau de parfum": "edp", "eau de toilette": "edt", "cologne": "cologne"}.get(product.concentration.casefold(), product.concentration.casefold())
        supplied = concentration.group(1) if concentration else None
        if supplied is not None:
            supplied = {"eau de parfum": "edp", "eau de toilette": "edt"}.get(supplied, supplied)
        reason = None
        if supplied is not None and supplied != expected:
            reason = "NAMED_REFERENCE_CONCENTRATION_MISMATCH"
        edition_suffix = suffix[concentration.end():].strip() if concentration else suffix
        if re.match(r"(?:intense|elixir|exclusif|la ros[eé]e|virtual flower|sweet chemistry|le parfum|radical essence|hair|body|diffuser|candle)\b", edition_suffix):
            reason = "NAMED_REFERENCE_EDITION_NOT_BOUND"
        if not any(product.product_id in row.product_ids and row.evidence_class == "OFFICIAL_PRODUCT_ARCHITECTURE" and row.usable_for_panel_selection and row.is_current(as_of) for row in registry.evidence.values()):
            reason = "NAMED_REFERENCE_ARCHITECTURE_UNAVAILABLE"
        if reason:
            unresolved.append({"product_id": product.product_id, "reason": reason})
        else:
            products.append(product)
    return {"products": products, "unresolved": unresolved, "sample_identity_bound": False}


def _panel_matches(panel: CommercialReferencePanelV1, tags: set[str], registry: CommercialReferenceRegistryV1) -> bool:
    rule = registry.selection_rules.get(panel.panel_id)
    if rule is not None:
        return all(tags & {tag.casefold() for tag in group} for group in rule["required_any_tag_groups"])
    return bool(tags & set(panel.concept_tags))


def _panel_evidence_error(panel: CommercialReferencePanelV1, as_of: date, registry: CommercialReferenceRegistryV1) -> str | None:
    if _date(panel.as_of_date, "as_of_date") > as_of:
        return "COMMERCIAL_REFERENCE_PANEL_NOT_YET_REVIEWED"
    if _date(panel.expires_on, "expires_on") < as_of:
        return "COMMERCIAL_REFERENCE_PANEL_EXPIRED"
    rows = [registry.evidence[key] for key in panel.evidence_ids]
    if any(not row.usable_for_panel_selection for row in rows):
        return "COMMERCIAL_REFERENCE_EVIDENCE_NOT_SELECTABLE"
    if any(not row.is_current(as_of) for row in rows if row.evidence_class not in MARKET_EVIDENCE_CLASSES):
        return "COMMERCIAL_REFERENCE_EVIDENCE_EXPIRED"
    for member in panel.active_members:
        if member["market_anchor"] and not any(member["product_id"] in row.product_ids and row.evidence_class in MARKET_EVIDENCE_CLASSES and row.market_scope is not None and row.is_current(as_of) for row in rows):
            return "CURRENT_MARKET_ANCHOR_EVIDENCE_UNAVAILABLE"
        if member["structural_neighbour"] and not any(member["product_id"] in row.product_ids and row.evidence_class == "OFFICIAL_PRODUCT_ARCHITECTURE" and row.is_current(as_of) for row in rows):
            return "STRUCTURAL_NEIGHBOUR_ARCHITECTURE_UNAVAILABLE"
    return None


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
    candidates: list[CommercialReferencePanelV1]
    if panel_id is not None:
        explicit_panel = registry.panels.get(panel_id)
        if explicit_panel is None:
            raise KeyError(f"unknown commercial panel: {panel_id}")
        candidates = [explicit_panel]
    else:
        candidates = sorted(
            (panel for panel in registry.panels.values() if _panel_matches(panel, tags, registry)),
            key=lambda panel: (-len(tags & set(panel.concept_tags)), panel.panel_id),
        )
    if not candidates:
        raise ValueError("no commercial panel matches the requested concept")
    if panel_id is None:
        eligible = [panel for panel in candidates if _panel_evidence_error(panel, as_of, registry) is None]
        if not eligible:
            raise ValueError(_panel_evidence_error(candidates[0], as_of, registry))
        if len(eligible) > 1 and len(tags & set(eligible[0].concept_tags)) == len(tags & set(eligible[1].concept_tags)):
            raise ValueError("COMMERCIAL_REFERENCE_PANEL_RELEVANCE_AMBIGUOUS")
        candidates = eligible
    panel = candidates[0]
    if not _panel_matches(panel, tags, registry):
        raise ValueError("no commercial panel matches the requested concept")
    error = _panel_evidence_error(panel, as_of, registry)
    if error:
        raise ValueError(error)
    referenced_evidence = [registry.evidence[value] for value in panel.evidence_ids]
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
        "selection_rule_sha256": stable_payload_hash(registry.selection_rules.get(panel.panel_id, {})),
        "products": products,
        "evidence": [{**row.as_dict(), "current_for_selection": row.is_current(as_of),
                      "selection_role": "CURRENT_SELECTION_EVIDENCE" if row.is_current(as_of)
                      else "HISTORICAL_CONTEXT_ONLY"} for row in referenced_evidence],
        "historical_market_evidence_ids": [row.evidence_id for row in referenced_evidence
                                           if row.evidence_class in MARKET_EVIDENCE_CLASSES and not row.is_current(as_of)],
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
