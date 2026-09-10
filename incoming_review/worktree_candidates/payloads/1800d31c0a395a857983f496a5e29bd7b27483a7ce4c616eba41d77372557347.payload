"""Universal, non-scalar perfume-depth experiment contracts.

The records in this module describe target-linked hypotheses and controlled
comparisons. They never infer sensory depth, liking, realism, performance,
similarity, safety, stability, or release success.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex


class PerfumeFamily(str, Enum):
    FLORAL = "FLORAL"
    WOODY = "WOODY"
    AMBER_RESINOUS = "AMBER_RESINOUS"
    LEATHER_SUEDE = "LEATHER_SUEDE"
    CHYPRE = "CHYPRE"
    FOUGERE = "FOUGERE"
    GOURMAND = "GOURMAND"
    CITRUS_HESPERIDIC = "CITRUS_HESPERIDIC"
    AROMATIC_HERBAL = "AROMATIC_HERBAL"
    GREEN = "GREEN"
    FRUITY = "FRUITY"
    AQUATIC_OZONIC = "AQUATIC_OZONIC"
    MINERAL_EARTH = "MINERAL_EARTH"
    MUSK_SKIN = "MUSK_SKIN"
    INCENSE_SMOKE = "INCENSE_SMOKE"
    TOBACCO_HAY = "TOBACCO_HAY"
    ALDEHYDIC_ABSTRACT = "ALDEHYDIC_ABSTRACT"
    HYBRID_MULTIFAMILY = "HYBRID_MULTIFAMILY"


class DepthDimension(str, Enum):
    CONSTRUCTION_COMPLEXITY = "CONSTRUCTION_COMPLEXITY"
    OBJECT_IDENTITY = "OBJECT_IDENTITY"
    INTERNAL_ANATOMY = "INTERNAL_ANATOMY"
    RELATIONAL_TOPOLOGY = "RELATIONAL_TOPOLOGY"
    CONTRAST_NEGATIVE_SPACE = "CONTRAST_NEGATIVE_SPACE"
    TEXTURE_MATERIALITY = "TEXTURE_MATERIALITY"
    TEMPORAL_ARCHITECTURE = "TEMPORAL_ARCHITECTURE"
    SPATIAL_PERFORMANCE = "SPATIAL_PERFORMANCE"
    HEDONIC_ARCHITECTURE = "HEDONIC_ARCHITECTURE"
    NONLINEAR_INTERACTION = "NONLINEAR_INTERACTION"
    PHYSICAL_CHEMISTRY = "PHYSICAL_CHEMISTRY"
    COGNITIVE_CONTEXT = "COGNITIVE_CONTEXT"
    ROBUSTNESS_ANTI_COLLAPSE = "ROBUSTNESS_ANTI_COLLAPSE"
    EVIDENCE_QUALITY = "EVIDENCE_QUALITY"


class DepthMechanismKind(str, Enum):
    ANCHOR = "ANCHOR"
    FACET = "FACET"
    BRIDGE = "BRIDGE"
    ECHO = "ECHO"
    CONTRAST = "CONTRAST"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    CONFIGURAL_BLEND = "CONFIGURAL_BLEND"
    SUPPRESSION_CONTROL = "SUPPRESSION_CONTROL"
    TEXTURE_MODULATION = "TEXTURE_MODULATION"
    TEMPORAL_HANDOFF = "TEMPORAL_HANDOFF"
    RECURRENCE = "RECURRENCE"
    METAMORPHOSIS = "METAMORPHOSIS"
    DIFFUSION_CARRIER = "DIFFUSION_CARRIER"
    PERSISTENCE_SUPPORT = "PERSISTENCE_SUPPORT"
    HEDONIC_TENSION_RELEASE = "HEDONIC_TENSION_RELEASE"
    FAMILIARITY_CUE = "FAMILIARITY_CUE"
    ANTI_COLLAPSE = "ANTI_COLLAPSE"
    PHYSICAL_CONSTRAINT = "PHYSICAL_CONSTRAINT"


class DepthProbeType(str, Enum):
    ABLATION = "ABLATION"
    RATIO_SWEEP = "RATIO_SWEEP"
    RECOMBINATION = "RECOMBINATION"
    ANTI_COLLAPSE = "ANTI_COLLAPSE"
    TEMPORAL = "TEMPORAL"
    SPATIAL = "SPATIAL"
    HEDONIC_PREFERENCE = "HEDONIC_PREFERENCE"
    TEXTURE = "TEXTURE"
    REFERENCE = "REFERENCE"
    REPEATABILITY = "REPEATABILITY"
    PHYSICAL_DIAGNOSTIC = "PHYSICAL_DIAGNOSTIC"


class DepthEvidenceState(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    OBSERVED_SCOPE = "OBSERVED_SCOPE"
    REPLICATED_SCOPE = "REPLICATED_SCOPE"


class DepthDesignState(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    HOLD = "HOLD"
    NO_CHANGE = "NO_CHANGE"


FORMULA_BOUND_REQUIRED_DIMENSIONS = (
    DepthDimension.OBJECT_IDENTITY,
    DepthDimension.INTERNAL_ANATOMY,
    DepthDimension.RELATIONAL_TOPOLOGY,
    DepthDimension.CONTRAST_NEGATIVE_SPACE,
    DepthDimension.TEXTURE_MATERIALITY,
    DepthDimension.TEMPORAL_ARCHITECTURE,
    DepthDimension.SPATIAL_PERFORMANCE,
    DepthDimension.HEDONIC_ARCHITECTURE,
    DepthDimension.NONLINEAR_INTERACTION,
    DepthDimension.PHYSICAL_CHEMISTRY,
    DepthDimension.COGNITIVE_CONTEXT,
    DepthDimension.ROBUSTNESS_ANTI_COLLAPSE,
    DepthDimension.EVIDENCE_QUALITY,
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in tuple(values))
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must contain at least one value")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _enum(value: object, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be a {enum_type.__name__}")


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return, union-attr]
    return value


class _CanonicalRecord:
    SCHEMA_VERSION: ClassVar[str]

    def as_dict(self) -> dict[str, Any]:
        payload = {item.name: _json_value(getattr(self, item.name)) for item in fields(self)}
        return {"schema_version": self.SCHEMA_VERSION, **payload}

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class DepthProbeV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_probe_v1"

    probe_id: str
    probe_type: DepthProbeType
    changed_factor: str
    arms: tuple[str, ...]
    constant_constraints: tuple[str, ...]
    primary_endpoints: tuple[str, ...]
    failure_endpoints: tuple[str, ...]
    time_windows: tuple[str, ...]
    blinding_rule: str
    order_rule: str
    accept_rule: str
    reject_rule: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "probe_id", _text(self.probe_id, "probe_id"))
        _enum(self.probe_type, DepthProbeType, "probe_type")
        for field_name in (
            "changed_factor",
            "blinding_rule",
            "order_rule",
            "accept_rule",
            "reject_rule",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        arms = _text_tuple(self.arms, "arms", allow_empty=False)
        if len(arms) < 2:
            raise ValueError("a depth probe requires at least two controlled arms")
        object.__setattr__(self, "arms", arms)
        for field_name in (
            "constant_constraints",
            "primary_endpoints",
            "failure_endpoints",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name, allow_empty=False),
            )
        object.__setattr__(self, "time_windows", _text_tuple(self.time_windows, "time_windows"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))

    @property
    def probe_sha256(self) -> str:
        return self.record_sha256


@dataclass(frozen=True, slots=True)
class DepthMechanismV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_mechanism_v1"

    mechanism_id: str
    dimension: DepthDimension
    kind: DepthMechanismKind
    target_link: str
    causal_hypothesis: str
    participant_ids: tuple[str, ...]
    expected_contribution: str
    failure_mode: str
    falsification_probe_id: str
    temporal_windows: tuple[str, ...]
    evidence_state: DepthEvidenceState
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "mechanism_id",
            "target_link",
            "causal_hypothesis",
            "expected_contribution",
            "failure_mode",
            "falsification_probe_id",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        _enum(self.dimension, DepthDimension, "dimension")
        _enum(self.kind, DepthMechanismKind, "kind")
        _enum(self.evidence_state, DepthEvidenceState, "evidence_state")
        object.__setattr__(
            self,
            "participant_ids",
            _text_tuple(self.participant_ids, "participant_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "temporal_windows",
            _text_tuple(self.temporal_windows, "temporal_windows"),
        )
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))

    @property
    def mechanism_sha256(self) -> str:
        return self.record_sha256


@dataclass(frozen=True, slots=True)
class DepthDimensionContractV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_dimension_contract_v1"

    dimension: DepthDimension
    target_definition: str
    required: bool
    mechanism_ids: tuple[str, ...]
    observable_endpoints: tuple[str, ...]
    failure_modes: tuple[str, ...]
    probe_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _enum(self.dimension, DepthDimension, "dimension")
        object.__setattr__(
            self,
            "target_definition",
            _text(self.target_definition, "target_definition"),
        )
        if not isinstance(self.required, bool):
            raise TypeError("required must be boolean")
        for field_name in (
            "mechanism_ids",
            "observable_endpoints",
            "failure_modes",
            "probe_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))

    @property
    def dimension_sha256(self) -> str:
        return self.record_sha256


@dataclass(frozen=True, slots=True)
class DepthFormulaRoleV1(_CanonicalRecord):
    """One exact parser-visible formula row bound to a target-linked role."""

    SCHEMA_VERSION: ClassVar[str] = "depth_formula_role_v1"

    row_number: int
    role_id: str
    material_name: str
    raw_ul: float
    active_ul: float
    active_ppm: float
    target_function: str

    def __post_init__(self) -> None:
        if isinstance(self.row_number, bool) or not isinstance(self.row_number, int):
            raise TypeError("row_number must be an integer")
        if self.row_number < 1:
            raise ValueError("row_number must be positive")
        object.__setattr__(self, "role_id", _text(self.role_id, "role_id"))
        if re.fullmatch(r"R\d{2,}", self.role_id) is None:
            raise ValueError("role_id must use the R01-style role syntax")
        object.__setattr__(self, "material_name", _text(self.material_name, "material_name"))
        object.__setattr__(self, "target_function", _text(self.target_function, "target_function"))
        for field_name in ("raw_ul", "active_ul", "active_ppm"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric")
            normalized = float(value)
            if not math.isfinite(normalized) or normalized < 0:
                raise ValueError(f"{field_name} must be finite and nonnegative")
            object.__setattr__(self, field_name, normalized)


@dataclass(frozen=True, slots=True)
class DepthFormulaEvidenceV1(_CanonicalRecord):
    """Exact formula/pipeline binding; diagnostic authority remains explicit."""

    SCHEMA_VERSION: ClassVar[str] = "depth_formula_evidence_v1"

    formula_path: str
    formula_file_sha256: str
    formula_definition_sha256: str
    analysis_input_sha256: str
    inventory_sha256: str
    scientific_inputs_sha256: str
    pipeline_source_sha256: str
    formula_name: str
    formula_number: int
    roles: tuple[DepthFormulaRoleV1, ...]
    total_raw_ul: float
    total_active_ul: float
    temporal_windows: tuple[str, ...]
    headspace_basis: str
    temporal_authority: str
    pipeline_overall: str
    release_evidence_overall: str
    unknown_oav_materials: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "formula_path",
            "formula_name",
            "headspace_basis",
            "temporal_authority",
            "pipeline_overall",
            "release_evidence_overall",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        for field_name in (
            "formula_file_sha256",
            "formula_definition_sha256",
            "analysis_input_sha256",
            "inventory_sha256",
            "scientific_inputs_sha256",
            "pipeline_source_sha256",
        ):
            value = _text(getattr(self, field_name), field_name).casefold()
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"{field_name} must be a SHA-256 hex digest")
            object.__setattr__(self, field_name, value)
        if isinstance(self.formula_number, bool) or not isinstance(self.formula_number, int):
            raise TypeError("formula_number must be an integer")
        if self.formula_number < 1:
            raise ValueError("formula_number must be positive")
        roles = tuple(self.roles)
        if not roles or any(not isinstance(item, DepthFormulaRoleV1) for item in roles):
            raise ValueError("roles must contain at least one DepthFormulaRoleV1")
        object.__setattr__(self, "roles", roles)
        if tuple(item.row_number for item in roles) != tuple(range(1, len(roles) + 1)):
            raise ValueError("formula row numbers must be consecutive from one")
        role_ids = tuple(item.role_id for item in roles)
        material_names = tuple(item.material_name for item in roles)
        if len(role_ids) != len(set(role_ids)):
            raise ValueError("formula role IDs must be unique")
        if len(tuple(name.casefold() for name in material_names)) != len(
            set(name.casefold() for name in material_names)
        ):
            raise ValueError("formula material names must be unique")
        for field_name in ("total_raw_ul", "total_active_ul"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric")
            normalized = float(value)
            if not math.isfinite(normalized) or normalized < 0:
                raise ValueError(f"{field_name} must be finite and nonnegative")
            object.__setattr__(self, field_name, normalized)
        if not math.isclose(
            self.total_raw_ul,
            sum(item.raw_ul for item in roles),
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("total_raw_ul does not match formula roles")
        if not math.isclose(
            self.total_active_ul,
            sum(item.active_ul for item in roles),
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ValueError("total_active_ul does not match formula roles")
        object.__setattr__(
            self,
            "temporal_windows",
            _text_tuple(self.temporal_windows, "temporal_windows", allow_empty=False),
        )
        unknown = _text_tuple(self.unknown_oav_materials, "unknown_oav_materials")
        material_keys = {name.casefold() for name in material_names}
        if any(name.casefold() not in material_keys for name in unknown):
            raise ValueError("unknown_oav_materials must belong to the bound formula")
        object.__setattr__(self, "unknown_oav_materials", unknown)

    @property
    def formula_row_count(self) -> int:
        return len(self.roles)

    @property
    def role_ids(self) -> tuple[str, ...]:
        return tuple(item.role_id for item in self.roles)

    @property
    def material_names(self) -> tuple[str, ...]:
        return tuple(item.material_name for item in self.roles)


@dataclass(frozen=True, slots=True)
class DepthArchitectureProfileV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_architecture_profile_v1"

    profile_id: str
    target_identity: str
    family: PerfumeFamily
    emotional_tone: str
    realism_or_abstraction_target: str
    forbidden_drift: tuple[str, ...]
    ideal_formula_ref: str
    current_inventory_build_ref: str
    dimension_contracts: tuple[DepthDimensionContractV1, ...]
    mechanisms: tuple[DepthMechanismV1, ...]
    probes: tuple[DepthProbeV1, ...]
    construction_row_count: int | None
    source_refs: tuple[str, ...]
    claim_ceiling: str
    formula_evidence: DepthFormulaEvidenceV1 | None = None
    formula_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "target_identity",
            "emotional_tone",
            "realism_or_abstraction_target",
            "ideal_formula_ref",
            "current_inventory_build_ref",
            "claim_ceiling",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        _enum(self.family, PerfumeFamily, "family")
        object.__setattr__(
            self,
            "forbidden_drift",
            _text_tuple(self.forbidden_drift, "forbidden_drift", allow_empty=False),
        )
        object.__setattr__(self, "source_refs", _text_tuple(self.source_refs, "source_refs"))
        if self.ideal_formula_ref == self.current_inventory_build_ref:
            raise ValueError(
                "TARGET/IDEAL and CURRENT-INVENTORY references must remain distinct ledgers"
            )
        if self.construction_row_count is not None:
            if isinstance(self.construction_row_count, bool) or not isinstance(
                self.construction_row_count, int
            ):
                raise TypeError("construction_row_count must be an integer or None")
            if self.construction_row_count < 0:
                raise ValueError("construction_row_count cannot be negative")
        if self.formula_evidence is not None:
            if not isinstance(self.formula_evidence, DepthFormulaEvidenceV1):
                raise TypeError("formula_evidence must be DepthFormulaEvidenceV1 or None")
            if self.construction_row_count != self.formula_evidence.formula_row_count:
                raise ValueError(
                    "construction_row_count must match bound formula evidence"
                )

        dimension_values = tuple(item.dimension for item in self.dimension_contracts)
        if len(dimension_values) != len(set(dimension_values)):
            raise ValueError("dimension contracts must contain unique dimensions")
        mechanism_ids = tuple(item.mechanism_id for item in self.mechanisms)
        if len(mechanism_ids) != len(set(mechanism_ids)):
            raise ValueError("mechanism IDs must be unique")
        probe_ids = tuple(item.probe_id for item in self.probes)
        if len(probe_ids) != len(set(probe_ids)):
            raise ValueError("probe IDs must be unique")

    @property
    def profile_sha256(self) -> str:
        return self.record_sha256


@dataclass(frozen=True, slots=True)
class DepthEvaluationResultV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "depth_evaluation_result_v1"

    state: DepthDesignState
    profile_sha256: str
    reason_codes: tuple[str, ...]
    blockers: tuple[str, ...]
    uncovered_dimensions: tuple[DepthDimension, ...]
    unbound_mechanism_ids: tuple[str, ...]
    empirical_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _enum(self.state, DepthDesignState, "state")
        object.__setattr__(self, "profile_sha256", _text(self.profile_sha256, "profile_sha256"))
        if len(self.profile_sha256) != 64:
            raise ValueError("profile_sha256 must contain 64 hexadecimal characters")
        try:
            int(self.profile_sha256, 16)
        except ValueError as exc:
            raise ValueError("profile_sha256 must contain 64 hexadecimal characters") from exc
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(self.reason_codes, "reason_codes"),
        )
        object.__setattr__(self, "blockers", _text_tuple(self.blockers, "blockers"))
        if len(self.uncovered_dimensions) != len(set(self.uncovered_dimensions)):
            raise ValueError("uncovered_dimensions must not contain duplicates")
        for value in self.uncovered_dimensions:
            _enum(value, DepthDimension, "uncovered_dimensions")
        object.__setattr__(
            self,
            "unbound_mechanism_ids",
            _text_tuple(self.unbound_mechanism_ids, "unbound_mechanism_ids"),
        )

    @property
    def result_sha256(self) -> str:
        return self.record_sha256


__all__ = [
    "DepthArchitectureProfileV1",
    "DepthDesignState",
    "DepthDimension",
    "DepthDimensionContractV1",
    "DepthEvaluationResultV1",
    "DepthEvidenceState",
    "DepthFormulaEvidenceV1",
    "DepthFormulaRoleV1",
    "DepthMechanismKind",
    "DepthMechanismV1",
    "DepthProbeType",
    "DepthProbeV1",
    "FORMULA_BOUND_REQUIRED_DIMENSIONS",
    "PerfumeFamily",
]
