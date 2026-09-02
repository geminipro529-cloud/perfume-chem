"""Central, authority-bounded wood capability registry.

The registry is the single material-to-wood-capability map for the active
formulation-intelligence layer.  It is deliberately structural: ownership can
make a stock selectable, but cannot establish target fit, perceived depth,
liking, safety, stability, or release.  Natural woods remain whole formula
identities and require composite OAV evidence before quantitative use.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass, fields
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from typing import Any, ClassVar, Iterable, Mapping, cast

from .contracts import AuthorityCeiling, CriterionValue, EvidenceClass, ProvenanceRef
from .inventory_projection import (
    AliquotState,
    ExactStockRef,
    StockAvailability,
    current_inventory_stock_corrections,
)
from .physicochemical_plane import MaterialKind


def _text(value: object, field_name: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError(f"{field_name} must be nonblank text")
    return normalized.casefold() if identifier else normalized


def _values(
    values: Iterable[Any],
    enum_type: type[Enum],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[Any, ...]:
    normalized = tuple(enum_type(value) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda item: cast(Enum, item).value))


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = True,
    identifiers: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(
        _text(value, field_name, identifier=identifiers) for value in values
    )
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    folded = tuple(value.casefold() for value in normalized)
    if len(folded) != len(set(folded)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized, key=lambda value: (value.casefold(), value)))


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, _Record):
        return value.as_dict()
    if isinstance(value, (CriterionValue, ProvenanceRef)):
        return value.as_dict()
    if isinstance(value, Mapping):
        return {
            str(key): _primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON forbids non-finite floats")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"{type(value).__name__} is not canonically serializable")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload(payload: Mapping[str, Any], record_type: type[_Record]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    expected = {
        "schema_version",
        *(item.name for item in fields(cast(Any, record_type))),
    }
    received = set(payload)
    if received != expected:
        raise ValueError(
            f"{record_type.SCHEMA_VERSION} payload does not match the closed schema; "
            f"missing={sorted(expected - received)!r}, "
            f"extra={sorted(received - expected)!r}"
        )
    if payload["schema_version"] != record_type.SCHEMA_VERSION:
        raise ValueError(
            f"schema_version must be {record_type.SCHEMA_VERSION!r}, "
            f"received {payload['schema_version']!r}"
        )
    return payload


class _Record:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{
                item.name: _primitive(getattr(self, item.name))
                for item in fields(cast(Any, self))
            },
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_bytes(self.as_dict())).hexdigest()


class WoodGroup(str, Enum):
    """Stable value bridge to the six existing wood-depth group identities.

    The hash-pinned ``engine.perception.wood_depth`` candidate is intentionally
    not imported here: doing so would silently turn an unadmitted specialist
    module into a runtime dependency.  Compatibility is by exact value and is
    covered by tests.
    """

    G16_GRAIN_ROOT = "G16_CEDAR_VETIVER_PATCHOULI_ROOT_WOODS"
    G17_CREAMY_WOODS = "G17_SANDALWOOD_CREAMY_WOODS"
    G18_TRANSPARENT_WOODS = "G18_TRANSPARENT_WOODS"
    G19_AMBERWOODS = "G19_AMBERGRIS_AMBERWOODS"
    RESIN_SMOKE_SHADOW = "RESIN_SMOKE_SHADOW"
    MUSK_ROUNDING = "MUSK_ROUNDING"


class WoodFunctionalRole(str, Enum):
    ROOT_GRAIN_BRIDGE = "root_grain_bridge"
    CREAMY_BODY = "creamy_body"
    TRANSPARENT_PATCHOULI = "transparent_patchouli"
    AMBERWOOD_POWER = "amberwood_power"
    RESIN_SMOKE_SHADOW = "resin_smoke_shadow"
    CONIFER_TRANSITION = "conifer_transition"
    AROMATIC_DRYNESS = "aromatic_dryness"
    FLORAL_WOOD_BRIDGE = "floral_wood_bridge"
    SOFT_WOODY_BODY = "soft_woody_body"
    DARK_OUD_BODY = "dark_oud_body"
    DRYDOWN_CONTINUITY = "drydown_continuity"
    MUSK_ROUNDING = "musk_rounding"


class WoodFacet(str, Enum):
    CREAMY = "creamy"
    SANDALWOOD = "sandalwood"
    PATCHOULI = "patchouli"
    TRANSPARENT = "transparent"
    ROOTY = "rooty"
    GRAINED = "grained"
    SMOKY = "smoky"
    RESINOUS = "resinous"
    OUD = "oud"
    CONIFEROUS = "coniferous"
    AROMATIC = "aromatic"
    DRY = "dry"
    FLORAL = "floral"
    SOFT = "soft"
    SWEET = "sweet"


class WoodTemporalWindow(str, Enum):
    OPENING = "opening"
    HEART = "heart"
    DRYDOWN = "drydown"


class QuantitativeOAVState(str, Enum):
    NOT_AUTHORIZED = "not_authorized"
    NATURAL_COMPOSITE_REQUIRED_UNBOUND = "natural_composite_required_unbound"
    OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND = (
        "opaque_bulk_reference_required_unbound"
    )


class WoodCandidateDisposition(str, Enum):
    FRONTIER = "frontier"
    NO_TARGET_FIT = "no_target_fit"
    FORBIDDEN_FACET = "forbidden_facet"


MANDATORY_AUTHORITY_EXCLUSIONS: tuple[str, ...] = (
    "formula_generation",
    "liking_inference",
    "observed_depth_or_richness",
    "physical_execution_authority",
    "release_authority",
    "safety_inference",
    "smell_or_target_fit_inference",
    "stability_inference",
)


@dataclass(frozen=True, slots=True)
class RationalFraction(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_rational_fraction_v1"

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int):
            raise TypeError("numerator must be an integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int):
            raise TypeError("denominator must be an integer")
        if self.denominator <= 0 or self.numerator <= 0:
            raise ValueError("fractions require positive numerator and denominator")
        fraction = Fraction(self.numerator, self.denominator)
        if fraction > 1:
            raise ValueError("fractions must not exceed one")
        if (fraction.numerator, fraction.denominator) != (
            self.numerator,
            self.denominator,
        ):
            raise ValueError("fractions must use canonical reduced form")

    @property
    def value(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RationalFraction:
        data = _payload(payload, cls)
        return cls(numerator=data["numerator"], denominator=data["denominator"])


@dataclass(frozen=True, slots=True)
class StockComponent(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_stock_component_v1"

    component_id: str
    component_name: str
    fraction: RationalFraction
    fraction_basis: str
    is_active_material: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "component_id", _text(self.component_id, "component_id", identifier=True)
        )
        object.__setattr__(
            self, "component_name", _text(self.component_name, "component_name")
        )
        if not isinstance(self.fraction, RationalFraction):
            raise TypeError("fraction must be a RationalFraction")
        object.__setattr__(
            self, "fraction_basis", _text(self.fraction_basis, "fraction_basis")
        )
        if not isinstance(self.is_active_material, bool):
            raise TypeError("is_active_material must be bool")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> StockComponent:
        data = _payload(payload, cls)
        return cls(
            component_id=data["component_id"],
            component_name=data["component_name"],
            fraction=RationalFraction.from_dict(data["fraction"]),
            fraction_basis=data["fraction_basis"],
            is_active_material=data["is_active_material"],
        )


@dataclass(frozen=True, slots=True)
class WoodMaterialCapability(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_material_capability_v1"

    capability_id: str
    canonical_material_name: str
    aliases: tuple[str, ...]
    material_kind: MaterialKind
    groups: tuple[WoodGroup, ...]
    functional_roles: tuple[WoodFunctionalRole, ...]
    facets: tuple[WoodFacet, ...]
    temporal_windows: tuple[WoodTemporalWindow, ...]
    exact_stock_ref: str
    stock_components: tuple[StockComponent, ...]
    quantitative_oav_state: QuantitativeOAVState
    liking: CriterionValue
    formula_constituent_expansion: bool
    authority_ceiling: AuthorityCeiling
    authority_exclusions: tuple[str, ...]
    provenance_refs: tuple[ProvenanceRef, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "capability_id", _text(self.capability_id, "capability_id", identifier=True)
        )
        object.__setattr__(
            self,
            "canonical_material_name",
            _text(self.canonical_material_name, "canonical_material_name"),
        )
        aliases = _text_tuple(self.aliases, "aliases")
        if self.canonical_material_name.casefold() in {
            value.casefold() for value in aliases
        }:
            raise ValueError("aliases must not repeat the canonical material name")
        object.__setattr__(self, "aliases", aliases)
        kind = MaterialKind(self.material_kind)
        object.__setattr__(self, "material_kind", kind)
        object.__setattr__(
            self,
            "groups",
            _values(self.groups, WoodGroup, "groups", allow_empty=False),
        )
        object.__setattr__(
            self,
            "functional_roles",
            _values(
                self.functional_roles,
                WoodFunctionalRole,
                "functional_roles",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "facets",
            _values(self.facets, WoodFacet, "facets", allow_empty=False),
        )
        object.__setattr__(
            self,
            "temporal_windows",
            _values(
                self.temporal_windows,
                WoodTemporalWindow,
                "temporal_windows",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "exact_stock_ref",
            _text(self.exact_stock_ref, "exact_stock_ref", identifier=True),
        )
        components = tuple(sorted(self.stock_components, key=lambda item: item.component_id))
        if not components or any(not isinstance(item, StockComponent) for item in components):
            raise ValueError("stock_components must contain StockComponent values")
        if len({item.component_id for item in components}) != len(components):
            raise ValueError("stock_components must use unique component_id values")
        if sum((item.fraction.value for item in components), Fraction()) != Fraction(1, 1):
            raise ValueError("stock component fractions must sum exactly to one")
        active = tuple(item for item in components if item.is_active_material)
        if len(active) != 1:
            raise ValueError("exactly one active stock component is required")
        if active[0].component_name.casefold() != self.canonical_material_name.casefold():
            raise ValueError("active stock component must match canonical material name")
        object.__setattr__(self, "stock_components", components)
        oav_state = QuantitativeOAVState(self.quantitative_oav_state)
        object.__setattr__(self, "quantitative_oav_state", oav_state)
        if kind is MaterialKind.NATURAL_MIXTURE and oav_state is not (
            QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
        ):
            raise ValueError("natural mixtures require an explicit composite OAV hold")
        if kind is MaterialKind.OPAQUE_MIXTURE and oav_state is not (
            QuantitativeOAVState.OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND
        ):
            raise ValueError("opaque mixtures require an explicit bulk-reference OAV hold")
        if not isinstance(self.liking, CriterionValue):
            raise TypeError("liking must be a CriterionValue")
        if self.liking.value is not None:
            raise ValueError("wood capability records cannot carry numeric liking")
        if self.formula_constituent_expansion:
            raise ValueError("wood capabilities never expand formula identity into constituents")
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("wood capability authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)
        exclusions = _text_tuple(
            self.authority_exclusions,
            "authority_exclusions",
            allow_empty=False,
            identifiers=True,
        )
        missing = sorted(set(MANDATORY_AUTHORITY_EXCLUSIONS) - set(exclusions))
        if missing:
            raise ValueError(f"mandatory authority exclusions are missing: {missing!r}")
        object.__setattr__(self, "authority_exclusions", exclusions)
        provenance = tuple(sorted(self.provenance_refs, key=lambda item: item.provenance_id))
        if not provenance or any(not isinstance(item, ProvenanceRef) for item in provenance):
            raise ValueError("wood capabilities require provenance")
        if len({item.provenance_id for item in provenance}) != len(provenance):
            raise ValueError("provenance_refs must use unique provenance_id values")
        object.__setattr__(self, "provenance_refs", provenance)

    @property
    def active_fraction(self) -> Fraction:
        return next(
            item.fraction.value
            for item in self.stock_components
            if item.is_active_material
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WoodMaterialCapability:
        data = _payload(payload, cls)
        return cls(
            capability_id=data["capability_id"],
            canonical_material_name=data["canonical_material_name"],
            aliases=tuple(data["aliases"]),
            material_kind=MaterialKind(data["material_kind"]),
            groups=tuple(WoodGroup(value) for value in data["groups"]),
            functional_roles=tuple(
                WoodFunctionalRole(value) for value in data["functional_roles"]
            ),
            facets=tuple(WoodFacet(value) for value in data["facets"]),
            temporal_windows=tuple(
                WoodTemporalWindow(value) for value in data["temporal_windows"]
            ),
            exact_stock_ref=data["exact_stock_ref"],
            stock_components=tuple(
                StockComponent.from_dict(item) for item in data["stock_components"]
            ),
            quantitative_oav_state=QuantitativeOAVState(
                data["quantitative_oav_state"]
            ),
            liking=CriterionValue.from_dict(data["liking"]),
            formula_constituent_expansion=data["formula_constituent_expansion"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            authority_exclusions=tuple(data["authority_exclusions"]),
            provenance_refs=tuple(
                ProvenanceRef.from_dict(item) for item in data["provenance_refs"]
            ),
        )


def _stock_authority_digest(
    materials: Iterable[WoodMaterialCapability],
) -> str:
    bindings: dict[str, str] = {}
    for item in materials:
        for ref in item.provenance_refs:
            if not ref.provenance_id.startswith("wood-stock:"):
                continue
            if ref.source_sha256 is None:
                raise ValueError("wood stock provenance requires source_sha256")
            current = bindings.get(ref.source_ref)
            if current is not None and current != ref.source_sha256:
                raise ValueError(
                    f"wood stock authority {ref.source_ref!r} has conflicting hashes"
                )
            bindings[ref.source_ref] = ref.source_sha256
    if not bindings:
        raise ValueError("wood registry requires stock authority bindings")
    payload = tuple(
        {"exact_stock_ref": ref, "content_sha256": bindings[ref]}
        for ref in sorted(bindings)
    )
    return sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class WoodCapabilityRegistry(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_capability_registry_v1"

    registry_id: str
    semantic_version: str
    materials: tuple[WoodMaterialCapability, ...]
    stock_authority_sha256: str
    authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "registry_id", _text(self.registry_id, "registry_id", identifier=True)
        )
        version = _text(self.semantic_version, "semantic_version")
        if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
            raise ValueError("semantic_version must use MAJOR.MINOR.PATCH")
        object.__setattr__(self, "semantic_version", version)
        materials = tuple(sorted(self.materials, key=lambda item: item.capability_id))
        if not materials or any(
            not isinstance(item, WoodMaterialCapability) for item in materials
        ):
            raise ValueError("materials must contain WoodMaterialCapability values")
        if len({item.capability_id for item in materials}) != len(materials):
            raise ValueError("materials must use unique capability_id values")
        names: dict[str, str] = {}
        for item in materials:
            for name in (item.canonical_material_name, *item.aliases):
                key = name.casefold()
                if key in names:
                    raise ValueError(
                        f"wood identity {name!r} conflicts with {names[key]!r}"
                    )
                names[key] = item.capability_id
        object.__setattr__(self, "materials", materials)
        digest = _text(
            self.stock_authority_sha256,
            "stock_authority_sha256",
            identifier=True,
        )
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("stock_authority_sha256 must be a SHA-256 digest")
        expected_digest = _stock_authority_digest(materials)
        if digest != expected_digest:
            raise ValueError(
                "stock_authority_sha256 does not match bound stock provenance"
            )
        object.__setattr__(self, "stock_authority_sha256", digest)
        ceiling = AuthorityCeiling(self.authority_ceiling)
        if not ceiling.is_no_stronger_than(AuthorityCeiling.STRUCTURAL_ONLY):
            raise ValueError("registry authority cannot exceed STRUCTURAL_ONLY")
        object.__setattr__(self, "authority_ceiling", ceiling)

    def resolve(self, material_name: str) -> WoodMaterialCapability | None:
        key = _text(material_name, "material_name").casefold()
        for item in self.materials:
            if key in {
                item.canonical_material_name.casefold(),
                *(alias.casefold() for alias in item.aliases),
            }:
                return item
        return None

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WoodCapabilityRegistry:
        data = _payload(payload, cls)
        return cls(
            registry_id=data["registry_id"],
            semantic_version=data["semantic_version"],
            materials=tuple(
                WoodMaterialCapability.from_dict(item) for item in data["materials"]
            ),
            stock_authority_sha256=data["stock_authority_sha256"],
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )


@dataclass(frozen=True, slots=True)
class WoodTargetRequest(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_target_request_v1"

    target_id: str
    family_id: str
    required_groups: tuple[WoodGroup, ...] = ()
    required_functional_roles: tuple[WoodFunctionalRole, ...] = ()
    required_facets: tuple[WoodFacet, ...] = ()
    forbidden_facets: tuple[WoodFacet, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "target_id", _text(self.target_id, "target_id", identifier=True)
        )
        object.__setattr__(
            self, "family_id", _text(self.family_id, "family_id", identifier=True)
        )
        object.__setattr__(
            self,
            "required_groups",
            _values(self.required_groups, WoodGroup, "required_groups"),
        )
        object.__setattr__(
            self,
            "required_functional_roles",
            _values(
                self.required_functional_roles,
                WoodFunctionalRole,
                "required_functional_roles",
            ),
        )
        object.__setattr__(
            self,
            "required_facets",
            _values(self.required_facets, WoodFacet, "required_facets"),
        )
        object.__setattr__(
            self,
            "forbidden_facets",
            _values(self.forbidden_facets, WoodFacet, "forbidden_facets"),
        )
        if not (
            self.required_groups
            or self.required_functional_roles
            or self.required_facets
        ):
            raise ValueError(
                "wood target requests require a substantive group, role, or facet"
            )
        overlap = set(self.required_facets) & set(self.forbidden_facets)
        if overlap:
            raise ValueError(f"required and forbidden facets overlap: {overlap!r}")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WoodTargetRequest:
        data = _payload(payload, cls)
        return cls(
            target_id=data["target_id"],
            family_id=data["family_id"],
            required_groups=tuple(WoodGroup(value) for value in data["required_groups"]),
            required_functional_roles=tuple(
                WoodFunctionalRole(value)
                for value in data["required_functional_roles"]
            ),
            required_facets=tuple(WoodFacet(value) for value in data["required_facets"]),
            forbidden_facets=tuple(WoodFacet(value) for value in data["forbidden_facets"]),
        )


@dataclass(frozen=True, slots=True)
class WoodCandidateMatch(_Record):
    SCHEMA_VERSION: ClassVar[str] = "wood_candidate_match_v1"

    capability_id: str
    disposition: WoodCandidateDisposition
    matched_groups: tuple[WoodGroup, ...]
    matched_functional_roles: tuple[WoodFunctionalRole, ...]
    matched_facets: tuple[WoodFacet, ...]
    reason_codes: tuple[str, ...]
    registry_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "capability_id", _text(self.capability_id, "capability_id", identifier=True)
        )
        object.__setattr__(
            self, "disposition", WoodCandidateDisposition(self.disposition)
        )
        object.__setattr__(
            self,
            "matched_groups",
            _values(self.matched_groups, WoodGroup, "matched_groups"),
        )
        object.__setattr__(
            self,
            "matched_functional_roles",
            _values(
                self.matched_functional_roles,
                WoodFunctionalRole,
                "matched_functional_roles",
            ),
        )
        object.__setattr__(
            self,
            "matched_facets",
            _values(self.matched_facets, WoodFacet, "matched_facets"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(
                self.reason_codes,
                "reason_codes",
                allow_empty=False,
                identifiers=True,
            ),
        )
        digest = _text(self.registry_sha256, "registry_sha256", identifier=True)
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("registry_sha256 must be a SHA-256 digest")
        object.__setattr__(self, "registry_sha256", digest)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WoodCandidateMatch:
        data = _payload(payload, cls)
        return cls(
            capability_id=data["capability_id"],
            disposition=WoodCandidateDisposition(data["disposition"]),
            matched_groups=tuple(WoodGroup(value) for value in data["matched_groups"]),
            matched_functional_roles=tuple(
                WoodFunctionalRole(value)
                for value in data["matched_functional_roles"]
            ),
            matched_facets=tuple(WoodFacet(value) for value in data["matched_facets"]),
            reason_codes=tuple(data["reason_codes"]),
            registry_sha256=data["registry_sha256"],
        )


def select_wood_capabilities(
    request: WoodTargetRequest,
    registry: WoodCapabilityRegistry,
    *,
    include_rejected: bool = False,
) -> tuple[WoodCandidateMatch, ...]:
    """Select by declared target requirements; ownership alone never selects."""

    if not isinstance(request, WoodTargetRequest):
        raise TypeError("request must be a WoodTargetRequest")
    if not isinstance(registry, WoodCapabilityRegistry):
        raise TypeError("registry must be a WoodCapabilityRegistry")
    matches: list[WoodCandidateMatch] = []
    for item in registry.materials:
        forbidden = tuple(sorted(set(item.facets) & set(request.forbidden_facets), key=lambda x: x.value))
        groups = tuple(sorted(set(item.groups) & set(request.required_groups), key=lambda x: x.value))
        roles = tuple(
            sorted(
                set(item.functional_roles) & set(request.required_functional_roles),
                key=lambda x: x.value,
            )
        )
        facets = tuple(sorted(set(item.facets) & set(request.required_facets), key=lambda x: x.value))
        if forbidden:
            disposition = WoodCandidateDisposition.FORBIDDEN_FACET
            reasons = ("FORBIDDEN_FACET_PRESENT",)
        elif groups or roles or facets:
            disposition = WoodCandidateDisposition.FRONTIER
            reasons = ("TARGET_LINKED_REQUIREMENT_MATCH",)
        else:
            disposition = WoodCandidateDisposition.NO_TARGET_FIT
            reasons = ("NO_DECLARED_TARGET_REQUIREMENT_MATCH",)
        match = WoodCandidateMatch(
            capability_id=item.capability_id,
            disposition=disposition,
            matched_groups=groups,
            matched_functional_roles=roles,
            matched_facets=facets,
            reason_codes=reasons,
            registry_sha256=registry.content_sha256,
        )
        if include_rejected or disposition is WoodCandidateDisposition.FRONTIER:
            matches.append(match)
    return tuple(sorted(matches, key=lambda item: item.capability_id))


_STRUCTURAL_SOURCE = (
    "Perfume-Chem wood capability registry v1; structural target-linked material "
    "roles only; no formula, smell, depth, richness, liking, performance, safety, "
    "stability, physical execution, or release authority."
)
_STRUCTURAL_SOURCE_SHA256 = sha256(_STRUCTURAL_SOURCE.encode("utf-8")).hexdigest()


def _stock_map(stock_refs: Iterable[ExactStockRef]) -> dict[str, ExactStockRef]:
    records = tuple(stock_refs)
    by_ref: dict[str, ExactStockRef] = {}
    for item in records:
        if not isinstance(item, ExactStockRef):
            raise TypeError("stock_refs must contain ExactStockRef values")
        if item.exact_stock_ref in by_ref:
            raise ValueError(f"duplicate stock ref {item.exact_stock_ref!r}")
        by_ref[item.exact_stock_ref] = item
    return by_ref


def _components(
    parts: tuple[tuple[str, int, int, bool], ...],
) -> tuple[StockComponent, ...]:
    return tuple(
        StockComponent(
            component_id=f"stock-component:{index}:{name.casefold().replace(' ', '-')}",
            component_name=name,
            fraction=RationalFraction(numerator, denominator),
            fraction_basis="w/w",
            is_active_material=is_active,
        )
        for index, (name, numerator, denominator, is_active) in enumerate(parts)
    )


def _capability(
    *,
    stock: ExactStockRef,
    capability_id: str,
    canonical_material_name: str,
    aliases: tuple[str, ...],
    material_kind: MaterialKind,
    groups: tuple[WoodGroup, ...],
    roles: tuple[WoodFunctionalRole, ...],
    facets: tuple[WoodFacet, ...],
    windows: tuple[WoodTemporalWindow, ...],
    components: tuple[StockComponent, ...],
    oav_state: QuantitativeOAVState,
    accepted_fraction_bases: tuple[str, ...],
    expected_carrier: str,
    additional_stock_authorities: tuple[ExactStockRef, ...] = (),
) -> WoodMaterialCapability:
    if stock.availability is not StockAvailability.OWNED:
        raise ValueError(f"{stock.exact_stock_ref!r} is not current owned stock")
    if not stock.exact_identity or not stock.composition_complete:
        raise ValueError(f"{stock.exact_stock_ref!r} lacks exact current stock authority")
    if stock.aliquot_state is not AliquotState.READY:
        raise ValueError(f"{stock.exact_stock_ref!r} is not a ready aliquot")
    if not stock.quantitative_authority:
        raise ValueError(f"{stock.exact_stock_ref!r} lacks stock-fraction authority")
    canonical_name = _text(canonical_material_name, "canonical_material_name")
    if stock.material_name.casefold() != canonical_name.casefold():
        raise ValueError(f"{stock.exact_stock_ref!r} material identity disagrees")
    accepted_bases = {
        _text(value, "accepted_fraction_bases", identifier=True)
        for value in accepted_fraction_bases
    }
    if stock.fraction_basis not in accepted_bases:
        raise ValueError(f"{stock.exact_stock_ref!r} fraction basis disagrees")
    if stock.carrier != _text(expected_carrier, "expected_carrier", identifier=True):
        raise ValueError(f"{stock.exact_stock_ref!r} carrier disagrees")
    active = next(item for item in components if item.is_active_material)
    if stock.fraction is None or not math.isclose(
        stock.fraction,
        float(active.fraction.value),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(f"{stock.exact_stock_ref!r} fraction disagrees with components")
    stock_provenance = ProvenanceRef(
        provenance_id=f"wood-stock:{capability_id}",
        source_ref=stock.exact_stock_ref,
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key=f"current-stock:{capability_id}",
        source_sha256=stock.content_sha256,
    )
    additional_stock_provenance = tuple(
        ProvenanceRef(
            provenance_id=(
                f"wood-stock:{capability_id}:authority-{index}"
            ),
            source_ref=authority.exact_stock_ref,
            evidence_class=EvidenceClass.USER_REPORT,
            independence_key=f"current-stock:{capability_id}:authority-{index}",
            source_sha256=authority.content_sha256,
        )
        for index, authority in enumerate(additional_stock_authorities, start=1)
    )
    structural_provenance = ProvenanceRef(
        provenance_id="wood-registry:structural-design:v1",
        source_ref="inline:wood-capability-registry-v1",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key="wood-registry:structural-design:v1",
        source_sha256=_STRUCTURAL_SOURCE_SHA256,
    )
    return WoodMaterialCapability(
        capability_id=capability_id,
        canonical_material_name=canonical_name,
        aliases=aliases,
        material_kind=material_kind,
        groups=groups,
        functional_roles=roles,
        facets=facets,
        temporal_windows=windows,
        exact_stock_ref=stock.exact_stock_ref,
        stock_components=components,
        quantitative_oav_state=oav_state,
        liking=CriterionValue.unknown(
            "No exact-condition participant liking observation is bound"
        ),
        formula_constituent_expansion=False,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        authority_exclusions=MANDATORY_AUTHORITY_EXCLUSIONS,
        provenance_refs=(
            stock_provenance,
            *additional_stock_provenance,
            structural_provenance,
        ),
    )


def _black_agarwood_neat_tombstone(
    stocks: tuple[ExactStockRef, ...],
) -> ExactStockRef:
    tombstone_ref = "inventory:tombstone:black-agarwood-artificial:neat"
    by_ref = _stock_map(stocks)
    tombstone = by_ref.get(tombstone_ref)
    if tombstone is None:
        raise ValueError("Black Agarwood neat tombstone is required")
    if (
        tombstone.material_name.casefold() != "black agarwood artificial"
        or tombstone.availability is not StockAvailability.TOMBSTONED
        or tombstone.fraction != 1.0
        or tombstone.fraction_basis != "neat_as_supplied"
        or tombstone.carrier != "none"
        or tombstone.aliquot_state is not AliquotState.NOT_PREPARED
        or tombstone.quantitative_authority
    ):
        raise ValueError("Black Agarwood neat tombstone authority disagrees")
    competing_neat = tuple(
        stock.exact_stock_ref
        for stock in stocks
        if stock.exact_stock_ref != tombstone_ref
        and stock.material_name.casefold() == "black agarwood artificial"
        and stock.availability is StockAvailability.OWNED
        and stock.fraction == 1.0
        and stock.fraction_basis == "neat_as_supplied"
        and stock.carrier in {None, "none"}
    )
    if competing_neat:
        raise ValueError(
            "Black Agarwood neat stock conflicts with the current tombstone: "
            + ", ".join(sorted(competing_neat))
        )
    return tombstone


def default_wood_capability_registry(
    stock_refs: Iterable[ExactStockRef] | None = None,
) -> WoodCapabilityRegistry:
    """Return the deterministic current-stock wood capability registry."""

    stocks = tuple(
        current_inventory_stock_corrections() if stock_refs is None else stock_refs
    )
    by_ref = _stock_map(stocks)
    black_agarwood_tombstone = _black_agarwood_neat_tombstone(stocks)

    specs = (
        _capability(
            stock=by_ref["inventory:v8:bacdanol:neat"],
            capability_id="wood.bacdanol",
            canonical_material_name="Bacdanol",
            aliases=("Bacnadol",),
            material_kind=MaterialKind.EXACT_MOLECULE,
            groups=(WoodGroup.G17_CREAMY_WOODS,),
            roles=(
                WoodFunctionalRole.CREAMY_BODY,
                WoodFunctionalRole.FLORAL_WOOD_BRIDGE,
                WoodFunctionalRole.DRYDOWN_CONTINUITY,
            ),
            facets=(WoodFacet.CREAMY, WoodFacet.SANDALWOOD, WoodFacet.SOFT),
            windows=(WoodTemporalWindow.HEART, WoodTemporalWindow.DRYDOWN),
            components=_components((("Bacdanol", 1, 1, True),)),
            oav_state=QuantitativeOAVState.NOT_AUTHORIZED,
            accepted_fraction_bases=("neat_as_supplied",),
            expected_carrier="none",
        ),
        _capability(
            stock=by_ref["inventory:v7:clearwood:neat"],
            capability_id="wood.clearwood",
            canonical_material_name="Clearwood",
            aliases=(),
            material_kind=MaterialKind.OPAQUE_MIXTURE,
            groups=(
                WoodGroup.G16_GRAIN_ROOT,
                WoodGroup.G18_TRANSPARENT_WOODS,
            ),
            roles=(
                WoodFunctionalRole.ROOT_GRAIN_BRIDGE,
                WoodFunctionalRole.TRANSPARENT_PATCHOULI,
                WoodFunctionalRole.DRYDOWN_CONTINUITY,
            ),
            facets=(
                WoodFacet.PATCHOULI,
                WoodFacet.ROOTY,
                WoodFacet.TRANSPARENT,
            ),
            windows=(WoodTemporalWindow.HEART, WoodTemporalWindow.DRYDOWN),
            components=_components((("Clearwood", 1, 1, True),)),
            oav_state=(
                QuantitativeOAVState.OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND
            ),
            accepted_fraction_bases=("neat_as_supplied",),
            expected_carrier="none",
        ),
        _capability(
            stock=by_ref["inventory:v8:guaiacwood-eo:one-third-ww"],
            capability_id="wood.guaiacwood-eo",
            canonical_material_name="Guaiacwood EO",
            aliases=("Guaiac Wood EO",),
            material_kind=MaterialKind.NATURAL_MIXTURE,
            groups=(WoodGroup.G16_GRAIN_ROOT, WoodGroup.RESIN_SMOKE_SHADOW),
            roles=(
                WoodFunctionalRole.FLORAL_WOOD_BRIDGE,
                WoodFunctionalRole.RESIN_SMOKE_SHADOW,
                WoodFunctionalRole.ROOT_GRAIN_BRIDGE,
            ),
            facets=(
                WoodFacet.FLORAL,
                WoodFacet.RESINOUS,
                WoodFacet.ROOTY,
                WoodFacet.SMOKY,
            ),
            windows=(WoodTemporalWindow.HEART, WoodTemporalWindow.DRYDOWN),
            components=_components(
                (
                    ("Guaiacwood EO", 1, 3, True),
                    ("Ethanol", 1, 3, False),
                    ("DEP", 1, 3, False),
                ),
            ),
            oav_state=(
                QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
            ),
            accepted_fraction_bases=("mass_fraction", "w/w"),
            expected_carrier="ethanol + dep",
        ),
        _capability(
            stock=by_ref["inventory:v7:black-agarwood-artificial:10pct-ww-dpg"],
            capability_id="wood.black-agarwood-artificial",
            canonical_material_name="Black Agarwood Artificial",
            aliases=("Black Agarwood Artificial 10%",),
            material_kind=MaterialKind.OPAQUE_MIXTURE,
            groups=(WoodGroup.RESIN_SMOKE_SHADOW,),
            roles=(
                WoodFunctionalRole.DARK_OUD_BODY,
                WoodFunctionalRole.RESIN_SMOKE_SHADOW,
            ),
            facets=(WoodFacet.OUD, WoodFacet.RESINOUS, WoodFacet.SMOKY),
            windows=(WoodTemporalWindow.HEART, WoodTemporalWindow.DRYDOWN),
            components=_components(
                (
                    ("Black Agarwood Artificial", 1, 10, True),
                    ("DPG", 9, 10, False),
                ),
            ),
            oav_state=(
                QuantitativeOAVState.OPAQUE_BULK_REFERENCE_REQUIRED_UNBOUND
            ),
            accepted_fraction_bases=("w/w", "mass_fraction"),
            expected_carrier="dpg",
            additional_stock_authorities=(black_agarwood_tombstone,),
        ),
        _capability(
            stock=by_ref["inventory:v8:cypress-eo:neat-as-supplied"],
            capability_id="wood.cypress-eo",
            canonical_material_name="Cypress EO",
            aliases=("Cypress Essential Oil",),
            material_kind=MaterialKind.NATURAL_MIXTURE,
            groups=(WoodGroup.G16_GRAIN_ROOT,),
            roles=(
                WoodFunctionalRole.AROMATIC_DRYNESS,
                WoodFunctionalRole.CONIFER_TRANSITION,
                WoodFunctionalRole.ROOT_GRAIN_BRIDGE,
            ),
            facets=(
                WoodFacet.AROMATIC,
                WoodFacet.CONIFEROUS,
                WoodFacet.DRY,
            ),
            windows=(
                WoodTemporalWindow.OPENING,
                WoodTemporalWindow.HEART,
                WoodTemporalWindow.DRYDOWN,
            ),
            components=_components((("Cypress EO", 1, 1, True),)),
            oav_state=(
                QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
            ),
            accepted_fraction_bases=("neat_as_supplied",),
            expected_carrier="none",
        ),
        _capability(
            stock=by_ref["inventory:v8:cabreuva-eo:50pct-ww-dpg"],
            capability_id="wood.cabreuva-eo",
            canonical_material_name="Cabreuva EO",
            aliases=("Cabreuva Essential Oil",),
            material_kind=MaterialKind.NATURAL_MIXTURE,
            groups=(WoodGroup.G16_GRAIN_ROOT, WoodGroup.G17_CREAMY_WOODS),
            roles=(
                WoodFunctionalRole.FLORAL_WOOD_BRIDGE,
                WoodFunctionalRole.ROOT_GRAIN_BRIDGE,
                WoodFunctionalRole.SOFT_WOODY_BODY,
            ),
            facets=(
                WoodFacet.DRY,
                WoodFacet.FLORAL,
                WoodFacet.SOFT,
                WoodFacet.SWEET,
            ),
            windows=(WoodTemporalWindow.HEART, WoodTemporalWindow.DRYDOWN),
            components=_components(
                (
                    ("Cabreuva EO", 1, 2, True),
                    ("DPG", 1, 2, False),
                ),
            ),
            oav_state=(
                QuantitativeOAVState.NATURAL_COMPOSITE_REQUIRED_UNBOUND
            ),
            accepted_fraction_bases=("w/w", "mass_fraction"),
            expected_carrier="dpg",
        ),
    )
    stock_authority_sha256 = _stock_authority_digest(specs)
    return WoodCapabilityRegistry(
        registry_id="perfume-chem:wood-capability-registry:v1",
        semantic_version="1.0.0",
        materials=specs,
        stock_authority_sha256=stock_authority_sha256,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
    )


__all__ = [
    "MANDATORY_AUTHORITY_EXCLUSIONS",
    "QuantitativeOAVState",
    "RationalFraction",
    "StockComponent",
    "WoodCandidateDisposition",
    "WoodCandidateMatch",
    "WoodCapabilityRegistry",
    "WoodFacet",
    "WoodFunctionalRole",
    "WoodGroup",
    "WoodMaterialCapability",
    "WoodTargetRequest",
    "WoodTemporalWindow",
    "default_wood_capability_registry",
    "select_wood_capabilities",
]
