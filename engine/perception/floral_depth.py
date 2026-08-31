"""Target-first floral and flower-linked wood depth experiment contracts.

The module designs closed comparisons. It does not infer beauty, liking,
realism, performance, safety, or release success, and it never authorizes a
formula mutation or physical action.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex


class FloralDesignState(str, Enum):
    READY = "READY"
    NO_CHANGE = "NO_CHANGE"
    HOLD = "HOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FloralScope(str, Enum):
    SOLIFLORE = "SOLIFLORE"
    BOUQUET = "BOUQUET"
    FLORAL_DOMINANT_FAMILY = "FLORAL_DOMINANT_FAMILY"
    FLOWER_LED_HYBRID = "FLOWER_LED_HYBRID"


class FloralSubjectRole(str, Enum):
    LEAD = "LEAD"
    CO_LEAD = "CO_LEAD"
    SUPPORT = "SUPPORT"


class FloralSourceClass(str, Enum):
    ESSENTIAL_OIL = "ESSENTIAL_OIL"
    ABSOLUTE = "ABSOLUTE"
    KNOWN_CHEMICAL = "KNOWN_CHEMICAL"
    OPAQUE_BASE = "OPAQUE_BASE"
    FRAGRANCE_OIL = "FRAGRANCE_OIL"
    FTEC = "FTEC"
    UNKNOWN_BLEND = "UNKNOWN_BLEND"


class FloralDepthStrategy(str, Enum):
    AUTOGENOUS_POLARITY = "AUTOGENOUS_POLARITY"
    ANATOMICAL_CONTINUUM = "ANATOMICAL_CONTINUUM"
    TEMPORAL_METAMORPHOSIS = "TEMPORAL_METAMORPHOSIS"
    ATMOSPHERIC_RELIEF = "ATMOSPHERIC_RELIEF"
    TEXTURAL_COUNTERPOINT = "TEXTURAL_COUNTERPOINT"
    INTERFLOWER_POLYPHONY = "INTERFLOWER_POLYPHONY"
    PRECISE_SIMPLICITY = "PRECISE_SIMPLICITY"


class FloralBackgroundMode(str, Enum):
    """Target-linked implementations of resistance and recession.

    These are mechanism classes, not ingredient recipes.  In particular,
    FLOWER_LINKED_WOOD is optional and carries no material-count quota.
    """

    FLOWER_DERIVED_SLOW_ECHO = "FLOWER_DERIVED_SLOW_ECHO"
    FLOWER_LINKED_WOOD = "FLOWER_LINKED_WOOD"
    FLOWER_LINKED_RESIN_SHADOW = "FLOWER_LINKED_RESIN_SHADOW"
    FLOWER_LINKED_MUSK_SKIN = "FLOWER_LINKED_MUSK_SKIN"
    ATMOSPHERIC_NEGATIVE_SPACE = "ATMOSPHERIC_NEGATIVE_SPACE"
    TARGET_LINKED_HYBRID = "TARGET_LINKED_HYBRID"


class FloralEvaluationEndpoint(str, Enum):
    """Endpoints that must not be collapsed into a beauty or depth score."""

    IDENTITY = "IDENTITY"
    REALISM = "REALISM"
    DEPTH = "DEPTH"
    TRANSITION_LIKING = "TRANSITION_LIKING"
    OVERALL_LIKING = "OVERALL_LIKING"


class FloralFacetClass(str, Enum):
    PETAL = "PETAL"
    FLESH = "FLESH"
    POLLEN = "POLLEN"
    NECTAR = "NECTAR"
    STEM_LEAF = "STEM_LEAF"
    HUMIDITY = "HUMIDITY"
    DIFFUSION = "DIFFUSION"
    SHADOW = "SHADOW"
    ROOT_RHIZOME = "ROOT_RHIZOME"
    WAX = "WAX"
    FRUIT = "FRUIT"
    SPICE = "SPICE"
    TEA = "TEA"
    LEATHER = "LEATHER"
    POWDER = "POWDER"
    TEMPORAL_TRANSITION = "TEMPORAL_TRANSITION"


class InventoryBindingState(str, Enum):
    OWNED = "OWNED"
    IDEAL_ONLY = "IDEAL_ONLY"
    MISSING = "MISSING"
    DEPLETED = "DEPLETED"
    UNKNOWN = "UNKNOWN"


class NaturalOAVState(str, Enum):
    COMPOSITE_COVERED = "COMPOSITE_COVERED"
    HOLD_LOT_OR_MODEL = "HOLD_LOT_OR_MODEL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TrainingDomain(str, Enum):
    FLORAL = "FLORAL"
    BACKGROUND = "BACKGROUND"
    WOOD = "WOOD"
    MUSK = "MUSK"


class FloralMaterialClass(str, Enum):
    """Material-class axis used for target-linked architecture accounting."""

    FLORAL = "FLORAL"
    GREEN_HUMIDITY = "GREEN_HUMIDITY"
    TOP = "TOP"
    WOOD = "WOOD"
    RESIN_SHADOW = "RESIN_SHADOW"
    MUSK = "MUSK"
    BRIDGE = "BRIDGE"


class FloralTemporalBand(str, Enum):
    OPENING = "OPENING"
    HEART = "HEART"
    LATE_HEART = "LATE_HEART"
    DRYDOWN = "DRYDOWN"
    PERSISTENT = "PERSISTENT"


_REQUIRED_WINDOWS = frozenset(
    {"OPENING", "5_MIN", "30_MIN", "2_HOUR", "4_HOUR", "8_HOUR"}
)
_ALLOWED_SOURCE_CLASSES = frozenset(
    {
        FloralSourceClass.ESSENTIAL_OIL,
        FloralSourceClass.ABSOLUTE,
        FloralSourceClass.KNOWN_CHEMICAL,
    }
)
_EXCEPTION_MUSKS = ("tonalide", "macrolide", "musk ketone")
_BASE_MATERIAL_CLASSES = frozenset(
    {
        FloralMaterialClass.WOOD,
        FloralMaterialClass.RESIN_SHADOW,
        FloralMaterialClass.MUSK,
    }
)
_EPSILON = Decimal("0.000001")
_REQUIRED_NONCOMPENSATORY_ENDPOINTS = frozenset(FloralEvaluationEndpoint)
_COMPENSATORY_ACCEPTANCE_MARKERS = (
    "weighted",
    "aggregate score",
    "overall score",
    "composite score",
    "average score",
    "offset a loss",
    "offsets a loss",
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings")
    return " ".join(value.split())


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in tuple(values))
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be decimal-compatible")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be decimal-compatible") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return format(value, "f")
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
class FloralSubjectV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_subject_v1"

    subject_id: str
    name: str
    role: FloralSubjectRole

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _text(self.subject_id, "subject_id"))
        object.__setattr__(self, "name", _text(self.name, "name"))
        object.__setattr__(self, "role", FloralSubjectRole(self.role))


@dataclass(frozen=True, slots=True)
class FloralIdentityContractV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_identity_contract_v1"

    target_identity: str
    emotional_tone: str
    floral_subjects: tuple[FloralSubjectV1, ...]
    floral_scope: FloralScope
    realism_target: str
    ideal_formula_ref: str
    current_inventory_build_ref: str
    allowed_source_classes: tuple[FloralSourceClass, ...]
    forbidden_drift: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_ceiling: str

    def __post_init__(self) -> None:
        for name in (
            "target_identity",
            "emotional_tone",
            "realism_target",
            "ideal_formula_ref",
            "current_inventory_build_ref",
            "claim_ceiling",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        subjects = tuple(self.floral_subjects)
        if not subjects or any(not isinstance(item, FloralSubjectV1) for item in subjects):
            raise ValueError("floral_subjects must contain FloralSubjectV1 records")
        ids = tuple(item.subject_id for item in subjects)
        if len(ids) != len(set(ids)):
            raise ValueError("floral subject IDs must be unique")
        object.__setattr__(self, "floral_subjects", subjects)
        object.__setattr__(self, "floral_scope", FloralScope(self.floral_scope))
        source_classes = tuple(FloralSourceClass(item) for item in self.allowed_source_classes)
        if not source_classes or len(source_classes) != len(set(source_classes)):
            raise ValueError("allowed_source_classes must be nonempty and unique")
        object.__setattr__(self, "allowed_source_classes", source_classes)
        object.__setattr__(
            self,
            "forbidden_drift",
            _text_tuple(tuple(self.forbidden_drift), "forbidden_drift"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _text_tuple(tuple(self.evidence_refs), "evidence_refs"),
        )


@dataclass(frozen=True, slots=True)
class FloralFacetV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_facet_v1"

    facet_id: str
    facet_class: FloralFacetClass
    target_function: str
    subject_owner: str
    omission_loss: str
    failure_mode: str
    required_temporal_windows: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    ideal_materials: tuple[str, ...]
    current_build_bindings: tuple[str, ...]
    controlled_comparison_ref: str

    def __post_init__(self) -> None:
        for name in ("facet_id", "target_function", "subject_owner", "failure_mode"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "omission_loss", _optional_text(self.omission_loss))
        object.__setattr__(
            self,
            "controlled_comparison_ref",
            _optional_text(self.controlled_comparison_ref),
        )
        object.__setattr__(self, "facet_class", FloralFacetClass(self.facet_class))
        for name in (
            "required_temporal_windows",
            "evidence_refs",
            "ideal_materials",
            "current_build_bindings",
        ):
            object.__setattr__(self, name, _text_tuple(tuple(getattr(self, name)), name))


@dataclass(frozen=True, slots=True)
class FloralCouplingContractV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_coupling_contract_v1"

    coupling_id: str
    facet_ids: tuple[str, ...]
    shared_recognizers: tuple[str, ...]
    relationship_edges: tuple[str, ...]
    bridge: str
    collision_risks: tuple[str, ...]
    controlled_arms: tuple[str, str]
    identity_retention_endpoints: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "coupling_id", _text(self.coupling_id, "coupling_id"))
        object.__setattr__(self, "bridge", _optional_text(self.bridge))
        for name in (
            "facet_ids",
            "shared_recognizers",
            "relationship_edges",
            "collision_risks",
            "controlled_arms",
            "identity_retention_endpoints",
        ):
            object.__setattr__(self, name, _text_tuple(tuple(getattr(self, name)), name))


@dataclass(frozen=True, slots=True)
class FloralTemporalWindowV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_temporal_window_v1"

    window_id: str
    required_recognizers: tuple[str, ...]
    state_hypothesis: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_id", _text(self.window_id, "window_id"))
        object.__setattr__(
            self,
            "required_recognizers",
            _text_tuple(tuple(self.required_recognizers), "required_recognizers"),
        )
        object.__setattr__(
            self,
            "state_hypothesis",
            _text(self.state_hypothesis, "state_hypothesis"),
        )


@dataclass(frozen=True, slots=True)
class FloralTemporalContourV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_temporal_contour_v1"

    windows: tuple[FloralTemporalWindowV1, ...]

    def __post_init__(self) -> None:
        values = tuple(self.windows)
        if any(not isinstance(item, FloralTemporalWindowV1) for item in values):
            raise TypeError("windows must contain FloralTemporalWindowV1 records")
        ids = tuple(item.window_id for item in values)
        if len(ids) != len(set(ids)):
            raise ValueError("temporal window IDs must be unique")
        object.__setattr__(self, "windows", values)


@dataclass(frozen=True, slots=True)
class FloralDosePreparationV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_dose_preparation_v1"

    preparation_id: str
    source_material: str
    source_stock_fraction: Decimal
    concentration_basis: str
    carrier: str
    source_ul: Decimal
    carrier_ul: Decimal
    prepared_total_ul: Decimal
    final_stock_fraction: Decimal
    delivered_ul: Decimal
    delivered_active_ul: Decimal
    instruction: str

    def __post_init__(self) -> None:
        for name in (
            "preparation_id",
            "source_material",
            "concentration_basis",
            "carrier",
            "instruction",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "source_stock_fraction",
            "source_ul",
            "carrier_ul",
            "prepared_total_ul",
            "final_stock_fraction",
            "delivered_ul",
            "delivered_active_ul",
        ):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class FloralMaterialDoseV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_material_dose_v1"

    material_id: str
    material: str
    source_class: FloralSourceClass
    subject_owner: str
    target_function: str
    raw_stock_ul: Decimal
    stock_fraction: Decimal
    active_ul: Decimal
    active_ppm: Decimal
    inventory_state: InventoryBindingState
    exact_stock_ref: str | None
    preparation_id: str | None
    natural_oav_state: NaturalOAVState
    is_musk: bool = False

    def __post_init__(self) -> None:
        for name in ("material_id", "material", "subject_owner", "target_function"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "source_class", FloralSourceClass(self.source_class))
        object.__setattr__(
            self,
            "inventory_state",
            InventoryBindingState(self.inventory_state),
        )
        object.__setattr__(
            self,
            "natural_oav_state",
            NaturalOAVState(self.natural_oav_state),
        )
        for name in ("raw_stock_ul", "stock_fraction", "active_ul", "active_ppm"):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))
        if self.exact_stock_ref is not None:
            object.__setattr__(
                self,
                "exact_stock_ref",
                _text(self.exact_stock_ref, "exact_stock_ref"),
            )
        if self.preparation_id is not None:
            object.__setattr__(
                self,
                "preparation_id",
                _text(self.preparation_id, "preparation_id"),
            )
        if not isinstance(self.is_musk, bool):
            raise TypeError("is_musk must be boolean")


@dataclass(frozen=True, slots=True)
class WoodTextureContractV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "wood_texture_contract_v1"

    contract_id: str
    material_ids: tuple[str, ...]
    texture_axis: str
    floral_echo: str
    omission_loss: str
    failure_mode: str
    fixed_constraints: tuple[str, ...]
    controlled_arms: tuple[str, ...]
    prerequisite_trial_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "contract_id",
            "texture_axis",
            "floral_echo",
            "omission_loss",
            "failure_mode",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "material_ids",
            "fixed_constraints",
            "controlled_arms",
            "prerequisite_trial_ids",
        ):
            object.__setattr__(self, name, _text_tuple(tuple(getattr(self, name)), name))


@dataclass(frozen=True, slots=True)
class FloralBackgroundContractV1(_CanonicalRecord):
    """One target-linked resistant field and its preferred recession.

    A background is defined by what it preserves and how it recedes, not by a
    mandatory wood, amber, musk, resin, or sweetness category.  Wood is valid
    only through the dedicated nonredundancy trial field.
    """

    SCHEMA_VERSION: ClassVar[str] = "floral_background_contract_v1"

    background_id: str
    mode: FloralBackgroundMode
    material_ids: tuple[str, ...]
    target_function: str
    flower_identity_link: str
    resistance_mechanism: str
    texture_target: str
    recession_target: str
    temporal_bands: tuple[FloralTemporalBand, ...]
    connective_interface_ids: tuple[str, ...]
    omission_loss: str
    takeover_failure_mode: str
    controlled_trial_id: str
    preferred_recession_trial_id: str
    wood_nonredundancy_trial_id: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "background_id",
            "target_function",
            "flower_identity_link",
            "resistance_mechanism",
            "texture_target",
            "recession_target",
            "omission_loss",
            "takeover_failure_mode",
            "controlled_trial_id",
            "preferred_recession_trial_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "mode", FloralBackgroundMode(self.mode))
        material_ids = _text_tuple(tuple(self.material_ids), "material_ids")
        if not material_ids:
            raise ValueError("material_ids must not be empty")
        object.__setattr__(self, "material_ids", material_ids)
        bands = tuple(FloralTemporalBand(item) for item in self.temporal_bands)
        if not bands or len(bands) != len(set(bands)):
            raise ValueError("temporal_bands must be nonempty and unique")
        object.__setattr__(self, "temporal_bands", bands)
        interface_ids = _text_tuple(
            tuple(self.connective_interface_ids),
            "connective_interface_ids",
        )
        if not interface_ids:
            raise ValueError("connective_interface_ids must not be empty")
        object.__setattr__(self, "connective_interface_ids", interface_ids)
        if self.wood_nonredundancy_trial_id is not None:
            object.__setattr__(
                self,
                "wood_nonredundancy_trial_id",
                _text(
                    self.wood_nonredundancy_trial_id,
                    "wood_nonredundancy_trial_id",
                ),
            )


@dataclass(frozen=True, slots=True)
class FloralEndpointGateV1(_CanonicalRecord):
    """One endpoint-specific gate; another endpoint may not rescue failure."""

    SCHEMA_VERSION: ClassVar[str] = "floral_endpoint_gate_v1"

    endpoint: FloralEvaluationEndpoint
    evaluation_question: str
    accept_condition: str
    reject_condition: str
    time_windows: tuple[str, ...]
    noncompensatory: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "endpoint", FloralEvaluationEndpoint(self.endpoint))
        for name in ("evaluation_question", "accept_condition", "reject_condition"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        windows = _text_tuple(tuple(self.time_windows), "time_windows")
        if not windows:
            raise ValueError("time_windows must not be empty")
        object.__setattr__(self, "time_windows", windows)
        if not isinstance(self.noncompensatory, bool):
            raise TypeError("noncompensatory must be boolean")


@dataclass(frozen=True, slots=True)
class FloralRelationalGrammarV1(_CanonicalRecord):
    """DHP-derived causal grammar without importing DHP's materials or family."""

    SCHEMA_VERSION: ClassVar[str] = "floral_relational_grammar_v1"

    grammar_id: str
    flower_totality: str
    internal_contrast_facet_ids: tuple[str, ...]
    connective_tissue_material_ids: tuple[str, ...]
    connective_interface_ids: tuple[str, ...]
    resistant_background_id: str
    preferred_recession: str
    preferred_recession_trial_id: str
    endpoint_gates: tuple[FloralEndpointGateV1, ...]
    anti_compensation_rule: str
    anti_collapse_trial_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "grammar_id",
            "flower_totality",
            "resistant_background_id",
            "preferred_recession",
            "preferred_recession_trial_id",
            "anti_compensation_rule",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "internal_contrast_facet_ids",
            "connective_tissue_material_ids",
            "connective_interface_ids",
            "anti_collapse_trial_ids",
        ):
            values = _text_tuple(tuple(getattr(self, name)), name)
            if not values:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, values)
        gates = tuple(self.endpoint_gates)
        if not gates or any(not isinstance(item, FloralEndpointGateV1) for item in gates):
            raise ValueError("endpoint_gates must contain FloralEndpointGateV1 records")
        endpoints = tuple(item.endpoint for item in gates)
        if len(endpoints) != len(set(endpoints)):
            raise ValueError("endpoint_gates must contain unique endpoints")
        object.__setattr__(self, "endpoint_gates", gates)


@dataclass(frozen=True, slots=True)
class FloralTrainingTrialV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_training_trial_v1"

    trial_id: str
    domain: TrainingDomain
    stage_order: int
    changed_factor: str
    intervention_material_ids: tuple[str, ...]
    controlled_arms: tuple[str, ...]
    primary_endpoints: tuple[str, ...]
    failure_endpoints: tuple[str, ...]
    constant_constraints: tuple[str, ...]
    prerequisite_trial_ids: tuple[str, ...]
    accept_rule: str
    reject_rule: str
    blinding_rule: str
    order_rule: str
    time_windows: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "trial_id",
            "changed_factor",
            "accept_rule",
            "reject_rule",
            "blinding_rule",
            "order_rule",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "domain", TrainingDomain(self.domain))
        if isinstance(self.stage_order, bool) or self.stage_order < 1:
            raise ValueError("stage_order must be a positive integer")
        for name in (
            "intervention_material_ids",
            "controlled_arms",
            "primary_endpoints",
            "failure_endpoints",
            "constant_constraints",
            "prerequisite_trial_ids",
            "time_windows",
            "evidence_refs",
        ):
            object.__setattr__(self, name, _text_tuple(tuple(getattr(self, name)), name))


@dataclass(frozen=True, slots=True)
class MissingChemicalImpactV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "missing_chemical_impact_v1"

    material: str
    target_function: str
    impact: str
    current_handling: str
    decision: str

    def __post_init__(self) -> None:
        for name in (
            "material",
            "target_function",
            "impact",
            "current_handling",
            "decision",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class FloralSubjectAnatomyV1(_CanonicalRecord):
    """Required, target-specific anatomy for one named floral subject."""

    SCHEMA_VERSION: ClassVar[str] = "floral_subject_anatomy_v1"

    subject_id: str
    required_facet_classes: tuple[FloralFacetClass, ...]
    required_material_ids: tuple[str, ...]
    omission_trial_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _text(self.subject_id, "subject_id"))
        facet_classes = tuple(FloralFacetClass(item) for item in self.required_facet_classes)
        if not facet_classes or len(facet_classes) != len(set(facet_classes)):
            raise ValueError("required_facet_classes must be nonempty and unique")
        object.__setattr__(self, "required_facet_classes", facet_classes)
        for name in ("required_material_ids", "omission_trial_ids"):
            values = _text_tuple(tuple(getattr(self, name)), name)
            if not values:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class FloralMaterialRoleV1(_CanonicalRecord):
    """One independently falsifiable primary role for one current-build row."""

    SCHEMA_VERSION: ClassVar[str] = "floral_material_role_v1"

    material_id: str
    module_id: str
    primary_role_id: str
    material_class: FloralMaterialClass
    temporal_band: FloralTemporalBand
    texture_axis: str
    interface_ids: tuple[str, ...]
    ablation_trial_id: str

    def __post_init__(self) -> None:
        for name in (
            "material_id",
            "module_id",
            "primary_role_id",
            "texture_axis",
            "ablation_trial_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "material_class", FloralMaterialClass(self.material_class))
        object.__setattr__(self, "temporal_band", FloralTemporalBand(self.temporal_band))
        object.__setattr__(
            self,
            "interface_ids",
            _text_tuple(tuple(self.interface_ids), "interface_ids"),
        )


@dataclass(frozen=True, slots=True)
class FloralInterfaceEdgeV1(_CanonicalRecord):
    """A tested bridge between modules rather than a rhetorical layer label."""

    SCHEMA_VERSION: ClassVar[str] = "floral_interface_edge_v1"

    interface_id: str
    source_module_id: str
    target_module_id: str
    bridge_material_ids: tuple[str, ...]
    failure_mode: str
    controlled_trial_id: str

    def __post_init__(self) -> None:
        for name in (
            "interface_id",
            "source_module_id",
            "target_module_id",
            "failure_mode",
            "controlled_trial_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.source_module_id == self.target_module_id:
            raise ValueError("an interface must connect two distinct modules")
        values = _text_tuple(tuple(self.bridge_material_ids), "bridge_material_ids")
        if not values:
            raise ValueError("bridge_material_ids must not be empty")
        object.__setattr__(self, "bridge_material_ids", values)


@dataclass(frozen=True, slots=True)
class FloralArchitectureContractV1(_CanonicalRecord):
    """Target-scoped resolution contract; never an aggregate complexity score.

    Required roles are named in advance. Material count cannot establish depth,
    but a benchmarked design cannot silently compress away declared anatomy,
    interfaces, temporal registers, or causal controls.
    """

    SCHEMA_VERSION: ClassVar[str] = "floral_architecture_contract_v1"

    contract_id: str
    benchmark_reference: str
    benchmark_scope: str
    subject_anatomies: tuple[FloralSubjectAnatomyV1, ...]
    material_roles: tuple[FloralMaterialRoleV1, ...]
    interface_edges: tuple[FloralInterfaceEdgeV1, ...]
    required_module_ids: tuple[str, ...]
    required_wood_role_ids: tuple[str, ...]
    required_floral_temporal_bands: tuple[FloralTemporalBand, ...]
    required_wood_temporal_bands: tuple[FloralTemporalBand, ...]
    required_wood_texture_axes: tuple[str, ...]
    ablation_trial_ids: tuple[str, ...]
    perturbation_trial_ids: tuple[str, ...]
    anti_collapse_trial_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        for name in (
            "contract_id",
            "benchmark_reference",
            "benchmark_scope",
            "rationale",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        typed_fields = (
            ("subject_anatomies", FloralSubjectAnatomyV1),
            ("material_roles", FloralMaterialRoleV1),
            ("interface_edges", FloralInterfaceEdgeV1),
        )
        for name, expected_type in typed_fields:
            values = tuple(getattr(self, name))
            if not values or any(not isinstance(item, expected_type) for item in values):
                raise ValueError(f"{name} must contain {expected_type.__name__} records")
            object.__setattr__(self, name, values)
        for name in (
            "required_module_ids",
            "required_wood_role_ids",
            "required_wood_texture_axes",
            "ablation_trial_ids",
            "perturbation_trial_ids",
            "anti_collapse_trial_ids",
        ):
            values = _text_tuple(tuple(getattr(self, name)), name)
            if not values:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, values)
        for name in (
            "required_floral_temporal_bands",
            "required_wood_temporal_bands",
        ):
            values = tuple(FloralTemporalBand(item) for item in getattr(self, name))
            if not values or len(values) != len(set(values)):
                raise ValueError(f"{name} must be nonempty and unique")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class FloralArchitectureContractV2(_CanonicalRecord):
    """Adaptive-background architecture with no material-category quota.

    V1 remains the exact legacy flower/wood contract used by White Fire.
    V2 names background roles generically so a flower-derived film, negative
    space, resin shadow, musk skin, or one justified wood can close the same
    relational function without being mislabeled as wood.
    """

    SCHEMA_VERSION: ClassVar[str] = "floral_architecture_contract_v2"

    contract_id: str
    benchmark_reference: str
    benchmark_scope: str
    subject_anatomies: tuple[FloralSubjectAnatomyV1, ...]
    material_roles: tuple[FloralMaterialRoleV1, ...]
    interface_edges: tuple[FloralInterfaceEdgeV1, ...]
    required_module_ids: tuple[str, ...]
    required_background_role_ids: tuple[str, ...]
    required_floral_temporal_bands: tuple[FloralTemporalBand, ...]
    required_background_temporal_bands: tuple[FloralTemporalBand, ...]
    required_background_texture_axes: tuple[str, ...]
    ablation_trial_ids: tuple[str, ...]
    perturbation_trial_ids: tuple[str, ...]
    anti_collapse_trial_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        for name in (
            "contract_id",
            "benchmark_reference",
            "benchmark_scope",
            "rationale",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        typed_fields = (
            ("subject_anatomies", FloralSubjectAnatomyV1),
            ("material_roles", FloralMaterialRoleV1),
            ("interface_edges", FloralInterfaceEdgeV1),
        )
        for name, expected_type in typed_fields:
            values = tuple(getattr(self, name))
            if not values or any(not isinstance(item, expected_type) for item in values):
                raise ValueError(f"{name} must contain {expected_type.__name__} records")
            object.__setattr__(self, name, values)
        for name in (
            "required_module_ids",
            "required_background_role_ids",
            "required_background_texture_axes",
            "ablation_trial_ids",
            "perturbation_trial_ids",
            "anti_collapse_trial_ids",
        ):
            values = _text_tuple(tuple(getattr(self, name)), name)
            if not values:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, values)
        for name in (
            "required_floral_temporal_bands",
            "required_background_temporal_bands",
        ):
            values = tuple(FloralTemporalBand(item) for item in getattr(self, name))
            if not values or len(values) != len(set(values)):
                raise ValueError(f"{name} must be nonempty and unique")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class FloralDesignRequestV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_design_request_v1"

    identity: FloralIdentityContractV1
    strategy: FloralDepthStrategy
    facets: tuple[FloralFacetV1, ...]
    coupling: FloralCouplingContractV1 | None
    temporal_contour: FloralTemporalContourV1
    ideal_materials: tuple[FloralMaterialDoseV1, ...]
    current_build_materials: tuple[FloralMaterialDoseV1, ...]
    preparations: tuple[FloralDosePreparationV1, ...]
    missing_chemical_impacts: tuple[MissingChemicalImpactV1, ...]
    wood_texture_contracts: tuple[WoodTextureContractV1, ...]
    training_trials: tuple[FloralTrainingTrialV1, ...]
    passed_trial_ids: tuple[str, ...]
    no_change_reason: str
    architecture_contract: (
        FloralArchitectureContractV1 | FloralArchitectureContractV2 | None
    ) = None
    background_contracts: tuple[FloralBackgroundContractV1, ...] = ()
    relational_grammar: FloralRelationalGrammarV1 | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, FloralIdentityContractV1):
            raise TypeError("identity must be a FloralIdentityContractV1")
        object.__setattr__(self, "strategy", FloralDepthStrategy(self.strategy))
        if self.coupling is not None and not isinstance(
            self.coupling, FloralCouplingContractV1
        ):
            raise TypeError("coupling must be a FloralCouplingContractV1")
        if not isinstance(self.temporal_contour, FloralTemporalContourV1):
            raise TypeError("temporal_contour must be a FloralTemporalContourV1")
        if self.architecture_contract is not None and not isinstance(
            self.architecture_contract,
            (FloralArchitectureContractV1, FloralArchitectureContractV2),
        ):
            raise TypeError(
                "architecture_contract must be FloralArchitectureContractV1, "
                "FloralArchitectureContractV2, or None"
            )
        if self.relational_grammar is not None and not isinstance(
            self.relational_grammar,
            FloralRelationalGrammarV1,
        ):
            raise TypeError("relational_grammar must be FloralRelationalGrammarV1 or None")
        typed_fields = (
            ("facets", FloralFacetV1),
            ("ideal_materials", FloralMaterialDoseV1),
            ("current_build_materials", FloralMaterialDoseV1),
            ("preparations", FloralDosePreparationV1),
            ("missing_chemical_impacts", MissingChemicalImpactV1),
            ("wood_texture_contracts", WoodTextureContractV1),
            ("background_contracts", FloralBackgroundContractV1),
            ("training_trials", FloralTrainingTrialV1),
        )
        for name, expected_type in typed_fields:
            values = tuple(getattr(self, name))
            if any(not isinstance(item, expected_type) for item in values):
                raise TypeError(f"{name} must contain {expected_type.__name__} records")
            object.__setattr__(self, name, values)
        object.__setattr__(
            self,
            "passed_trial_ids",
            _text_tuple(tuple(self.passed_trial_ids), "passed_trial_ids"),
        )
        object.__setattr__(
            self,
            "no_change_reason",
            _text(self.no_change_reason, "no_change_reason"),
        )


@dataclass(frozen=True, slots=True)
class FloralDesignResultV1(_CanonicalRecord):
    SCHEMA_VERSION: ClassVar[str] = "floral_design_result_v1"

    state: FloralDesignState
    reason_codes: tuple[str, ...]
    request_sha256: str
    selected_trial: FloralTrainingTrialV1 | None
    deferred_trial_ids: tuple[str, ...]
    quantitative_oav_holds: tuple[str, ...]
    blockers: tuple[str, ...]
    identity: FloralIdentityContractV1
    strategy: FloralDepthStrategy
    ideal_materials: tuple[FloralMaterialDoseV1, ...]
    current_build_materials: tuple[FloralMaterialDoseV1, ...]
    missing_chemical_impacts: tuple[MissingChemicalImpactV1, ...]
    empirical_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", FloralDesignState(self.state))
        object.__setattr__(self, "strategy", FloralDepthStrategy(self.strategy))
        object.__setattr__(
            self,
            "reason_codes",
            _text_tuple(tuple(self.reason_codes), "reason_codes"),
        )
        object.__setattr__(
            self,
            "deferred_trial_ids",
            _text_tuple(tuple(self.deferred_trial_ids), "deferred_trial_ids"),
        )
        object.__setattr__(
            self,
            "quantitative_oav_holds",
            _text_tuple(tuple(self.quantitative_oav_holds), "quantitative_oav_holds"),
        )
        object.__setattr__(
            self,
            "blockers",
            _text_tuple(tuple(self.blockers), "blockers"),
        )


def _append_issue(
    codes: list[str], blockers: list[str], code: str, detail: str
) -> None:
    if code not in codes:
        codes.append(code)
    if detail not in blockers:
        blockers.append(detail)


def _preparation_is_complete(preparation: FloralDosePreparationV1) -> bool:
    if (
        preparation.source_stock_fraction <= 0
        or preparation.source_stock_fraction > 1
        or preparation.source_ul < 10
        or preparation.carrier_ul < 10
        or preparation.prepared_total_ul < 20
        or preparation.delivered_ul < 10
        or preparation.final_stock_fraction <= 0
        or preparation.delivered_active_ul <= 0
    ):
        return False
    if abs(
        preparation.source_ul
        + preparation.carrier_ul
        - preparation.prepared_total_ul
    ) > _EPSILON:
        return False
    expected_fraction = (
        preparation.source_stock_fraction
        * preparation.source_ul
        / preparation.prepared_total_ul
    )
    expected_active = preparation.final_stock_fraction * preparation.delivered_ul
    return (
        abs(expected_fraction - preparation.final_stock_fraction) <= _EPSILON
        and abs(expected_active - preparation.delivered_active_ul) <= _EPSILON
    )


def _source_hashes(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        value.casefold()
        for value in values
        if len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _validate_architecture_contract(
    request: FloralDesignRequestV1,
    *,
    facets_by_id: dict[str, FloralFacetV1],
    current_by_id: dict[str, FloralMaterialDoseV1],
    trials_by_id: dict[str, FloralTrainingTrialV1],
    codes: list[str],
    blockers: list[str],
) -> None:
    """Validate target-linked resolution without treating row count as depth."""

    if request.strategy is FloralDepthStrategy.PRECISE_SIMPLICITY:
        return
    contract = request.architecture_contract
    if contract is None:
        _append_issue(
            codes,
            blockers,
            "HOLD_ARCHITECTURE_CONTRACT_MISSING",
            "A non-simple floral design requires a target-linked anatomy, role, interface, and causal-test contract.",
        )
        return

    subjects_by_id = {item.subject_id: item for item in request.identity.floral_subjects}
    primary_subject_ids = {
        item.subject_id
        for item in request.identity.floral_subjects
        if item.role in {FloralSubjectRole.LEAD, FloralSubjectRole.CO_LEAD}
    }
    anatomies_by_id = {item.subject_id: item for item in contract.subject_anatomies}
    if len(anatomies_by_id) != len(contract.subject_anatomies):
        _append_issue(
            codes,
            blockers,
            "HOLD_SUBJECT_ANATOMY",
            "Subject anatomy records must be unique.",
        )
    missing_anatomies = primary_subject_ids - set(anatomies_by_id)
    unknown_anatomies = set(anatomies_by_id) - set(subjects_by_id)
    if missing_anatomies or unknown_anatomies:
        _append_issue(
            codes,
            blockers,
            "HOLD_SUBJECT_ANATOMY",
            "Every lead or co-lead requires one known subject-anatomy record.",
        )

    facets_by_owner: dict[str, set[FloralFacetClass]] = {}
    for facet in facets_by_id.values():
        facets_by_owner.setdefault(facet.subject_owner, set()).add(facet.facet_class)
    for subject_id in sorted(primary_subject_ids & set(anatomies_by_id)):
        anatomy = anatomies_by_id[subject_id]
        required = set(anatomy.required_facet_classes)
        minimum_anatomy = {FloralFacetClass.PETAL, FloralFacetClass.FLESH}
        if len(required) < 4 or not minimum_anatomy.issubset(required):
            _append_issue(
                codes,
                blockers,
                "HOLD_SUBJECT_ANATOMY",
                f"{subject_id} must declare PETAL, FLESH, and at least two target-specific anatomy facets.",
            )
        if not required.issubset(facets_by_owner.get(subject_id, set())):
            _append_issue(
                codes,
                blockers,
                "HOLD_SUBJECT_ANATOMY",
                f"{subject_id} lacks one or more declared anatomy facets in the active design.",
            )
        missing_materials = set(anatomy.required_material_ids) - set(current_by_id)
        wrongly_owned = {
            material_id
            for material_id in anatomy.required_material_ids
            if material_id in current_by_id
            and current_by_id[material_id].subject_owner != subject_id
        }
        if missing_materials or wrongly_owned:
            _append_issue(
                codes,
                blockers,
                "HOLD_SUBJECT_ANATOMY",
                f"{subject_id} anatomy is not bound to owned, subject-specific current materials.",
            )
        omission_trials = [
            trials_by_id[trial_id]
            for trial_id in anatomy.omission_trial_ids
            if trial_id in trials_by_id
        ]
        covered = {
            material_id
            for trial in omission_trials
            for material_id in trial.intervention_material_ids
        }
        if len(omission_trials) != len(anatomy.omission_trial_ids) or not set(
            anatomy.required_material_ids
        ).issubset(covered):
            _append_issue(
                codes,
                blockers,
                "HOLD_SUBJECT_ANATOMY",
                f"{subject_id} anatomy lacks a bound constant-total omission comparison.",
            )

    roles_by_material = {item.material_id: item for item in contract.material_roles}
    role_ids = tuple(item.primary_role_id for item in contract.material_roles)
    if (
        len(roles_by_material) != len(contract.material_roles)
        or len(role_ids) != len(set(role_ids))
        or set(roles_by_material) != set(current_by_id)
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_ROLE_COVERAGE",
            "Every current-build material requires exactly one unique, independently falsifiable primary role.",
        )
    roles_by_id = {item.primary_role_id: item for item in contract.material_roles}
    if isinstance(contract, FloralArchitectureContractV1):
        required_support_roles = set(contract.required_wood_role_ids)
        if not required_support_roles.issubset(roles_by_id):
            _append_issue(
                codes,
                blockers,
                "HOLD_ROLE_COVERAGE",
                "One or more target-declared wood/base roles were compressed out of the build.",
            )
        elif any(
            roles_by_id[role_id].material_class not in _BASE_MATERIAL_CLASSES
            for role_id in required_support_roles
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_ROLE_COVERAGE",
                "Declared wood/base role IDs must bind to wood, resin-shadow, or musk materials.",
            )
    else:
        required_support_roles = set(contract.required_background_role_ids)
        if not required_support_roles.issubset(roles_by_id):
            _append_issue(
                codes,
                blockers,
                "HOLD_ROLE_COVERAGE",
                "One or more target-declared adaptive-background roles were compressed out of the build.",
            )
    observed_modules = {item.module_id for item in contract.material_roles}
    if not set(contract.required_module_ids).issubset(observed_modules):
        _append_issue(
            codes,
            blockers,
            "HOLD_ROLE_COVERAGE",
            "One or more target-declared architecture modules have no surviving material role.",
        )
    for role in contract.material_roles:
        trial = trials_by_id.get(role.ablation_trial_id)
        if trial is None or role.material_id not in trial.intervention_material_ids:
            _append_issue(
                codes,
                blockers,
                "HOLD_ROLE_ABLATION",
                f"{role.primary_role_id} lacks a material-bound constant-total ablation trial.",
            )

    interfaces_by_id = {item.interface_id: item for item in contract.interface_edges}
    if len(interfaces_by_id) != len(contract.interface_edges):
        _append_issue(
            codes,
            blockers,
            "HOLD_INTERFACE_CLOSURE",
            "Interface IDs must be unique.",
        )
    for role in contract.material_roles:
        if any(interface_id not in interfaces_by_id for interface_id in role.interface_ids):
            _append_issue(
                codes,
                blockers,
                "HOLD_INTERFACE_CLOSURE",
                f"{role.primary_role_id} references an unknown module interface.",
            )
    touched_modules: set[str] = set()
    for edge in contract.interface_edges:
        touched_modules.update((edge.source_module_id, edge.target_module_id))
        trial = trials_by_id.get(edge.controlled_trial_id)
        if (
            edge.source_module_id not in observed_modules
            or edge.target_module_id not in observed_modules
            or not set(edge.bridge_material_ids).issubset(current_by_id)
            or trial is None
            or not set(edge.bridge_material_ids).issubset(trial.intervention_material_ids)
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_INTERFACE_CLOSURE",
                f"{edge.interface_id} is not closed by owned bridge materials and a controlled trial.",
            )
    if not primary_subject_ids.issubset(touched_modules):
        _append_issue(
            codes,
            blockers,
            "HOLD_INTERFACE_CLOSURE",
            "Every lead or co-lead must participate in an explicit module interface.",
        )

    support_roles = tuple(
        roles_by_id[role_id]
        for role_id in required_support_roles
        if role_id in roles_by_id
    )
    support_material_ids = {role.material_id for role in support_roles}
    floral_roles = tuple(
        role for role in contract.material_roles if role.material_id not in support_material_ids
    )
    required_support_bands = (
        contract.required_wood_temporal_bands
        if isinstance(contract, FloralArchitectureContractV1)
        else contract.required_background_temporal_bands
    )
    required_support_textures = (
        contract.required_wood_texture_axes
        if isinstance(contract, FloralArchitectureContractV1)
        else contract.required_background_texture_axes
    )
    if not set(contract.required_floral_temporal_bands).issubset(
        {item.temporal_band for item in floral_roles}
    ) or not set(required_support_bands).issubset(
        {item.temporal_band for item in support_roles}
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_TEMPORAL_RESOLUTION",
            "Floral and resistant-background roles do not span all target-declared temporal registers.",
        )
    if not {item.casefold() for item in required_support_textures}.issubset(
        {item.texture_axis.casefold() for item in support_roles}
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_TEXTURE_RESOLUTION",
            "Resistant-background roles do not cover all target-declared tactile axes.",
        )

    for trial_id in (
        *contract.ablation_trial_ids,
        *contract.perturbation_trial_ids,
        *contract.anti_collapse_trial_ids,
    ):
        if trial_id not in trials_by_id:
            _append_issue(
                codes,
                blockers,
                "HOLD_EFFECTIVE_COMPLEXITY",
                f"Architecture control {trial_id} is absent.",
            )
    for trial_id in contract.anti_collapse_trial_ids:
        trial = trials_by_id.get(trial_id)
        if trial is not None and not any(
            marker in endpoint.upper()
            for endpoint in trial.failure_endpoints
            for marker in ("COLLAPSE", "GENERIC", "BLUR")
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_EFFECTIVE_COMPLEXITY",
                f"{trial_id} does not observe collapse or genericization.",
            )


def _validate_relational_grammar(
    request: FloralDesignRequestV1,
    *,
    facets_by_id: dict[str, FloralFacetV1],
    current_by_id: dict[str, FloralMaterialDoseV1],
    trials_by_id: dict[str, FloralTrainingTrialV1],
    codes: list[str],
    blockers: list[str],
) -> None:
    """Validate flower totality, resistance, and recession without a wood quota."""

    if request.strategy is FloralDepthStrategy.PRECISE_SIMPLICITY:
        return
    architecture = request.architecture_contract
    if not isinstance(architecture, FloralArchitectureContractV2):
        # V1 is the frozen legacy White Fire flower/wood contract.  New adaptive
        # designs use V2; preserving V1 avoids silently rewriting its evidence.
        return

    grammar = request.relational_grammar
    if grammar is None:
        _append_issue(
            codes,
            blockers,
            "HOLD_RELATIONAL_GRAMMAR",
            "Adaptive-background architecture requires flower totality, internal contrast, connective tissue, resistance, and preferred recession.",
        )
        return

    backgrounds_by_id = {
        item.background_id: item for item in request.background_contracts
    }
    if (
        not request.background_contracts
        or len(backgrounds_by_id) != len(request.background_contracts)
        or grammar.resistant_background_id not in backgrounds_by_id
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_RESISTANT_BACKGROUND",
            "The relational grammar must select one explicit adaptive resistant background.",
        )
        return
    if len(request.background_contracts) != 1:
        _append_issue(
            codes,
            blockers,
            "HOLD_RESISTANT_BACKGROUND",
            "One design request may contain exactly one active resistant background; alternatives belong in controlled arms.",
        )
    background = backgrounds_by_id[grammar.resistant_background_id]

    if request.coupling is None:
        _append_issue(
            codes,
            blockers,
            "HOLD_EXTERNALIZED_DEPTH",
            "A resistant background cannot substitute for the flower's internal coupled depth relation.",
        )
    elif (
        len(grammar.internal_contrast_facet_ids) < 2
        or not set(grammar.internal_contrast_facet_ids).issubset(facets_by_id)
        or not set(grammar.internal_contrast_facet_ids).issubset(
            request.coupling.facet_ids
        )
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_INTERNAL_CONTRAST",
            "Internal contrast must bind at least two declared flower facets inside the active coupling.",
        )

    if not set(grammar.connective_tissue_material_ids).issubset(current_by_id):
        _append_issue(
            codes,
            blockers,
            "HOLD_CONNECTIVE_TISSUE",
            "Every connective-tissue material must be an owned current-build row.",
        )
    interfaces_by_id = {
        item.interface_id: item for item in architecture.interface_edges
    }
    required_interfaces = set(grammar.connective_interface_ids) | set(
        background.connective_interface_ids
    )
    if not required_interfaces.issubset(interfaces_by_id):
        _append_issue(
            codes,
            blockers,
            "HOLD_CONNECTIVE_TISSUE",
            "Connective tissue must bind to explicit architecture interfaces.",
        )

    roles_by_material = {
        item.material_id: item for item in architecture.material_roles
    }
    background_ids = set(background.material_ids)
    required_background_roles = set(architecture.required_background_role_ids)
    bound_background_ids = {
        roles_by_id.material_id
        for roles_by_id in architecture.material_roles
        if roles_by_id.primary_role_id in required_background_roles
    }
    if (
        not background_ids.issubset(current_by_id)
        or not background_ids.issubset(roles_by_material)
        or background_ids != bound_background_ids
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_RESISTANT_BACKGROUND",
            "The selected background must close exactly through owned rows and declared background roles.",
        )
    if not {
        FloralTemporalBand.DRYDOWN,
        FloralTemporalBand.PERSISTENT,
    }.intersection(background.temporal_bands):
        _append_issue(
            codes,
            blockers,
            "HOLD_RESISTANT_BACKGROUND",
            "Resistance requires an explicit drydown or persistent temporal band.",
        )

    background_trial = trials_by_id.get(background.controlled_trial_id)
    wood_ids = {
        material_id
        for material_id in background_ids
        if material_id in roles_by_material
        and roles_by_material[material_id].material_class is FloralMaterialClass.WOOD
    }
    nonwood_background_ids = background_ids - wood_ids
    if (
        background_trial is None
        or not nonwood_background_ids.issubset(
            background_trial.intervention_material_ids
        )
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_RESISTANT_BACKGROUND",
            "The non-wood resistant field must be isolated by its declared constant-total trial.",
        )

    preferred_trial_id = grammar.preferred_recession_trial_id
    preferred_trial = trials_by_id.get(preferred_trial_id)
    late_windows = {"2_HOUR", "4_HOUR", "8_HOUR"}
    if (
        preferred_trial_id != background.preferred_recession_trial_id
        or preferred_trial is None
        or FloralEvaluationEndpoint.TRANSITION_LIKING.value
        not in preferred_trial.primary_endpoints
        or not late_windows.intersection(preferred_trial.time_windows)
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_PREFERRED_RECESSION",
            "Preferred recession requires a late, endpoint-specific transition-liking comparison.",
        )

    endpoint_gates = {item.endpoint: item for item in grammar.endpoint_gates}
    if (
        set(endpoint_gates) != _REQUIRED_NONCOMPENSATORY_ENDPOINTS
        or any(not item.noncompensatory for item in endpoint_gates.values())
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_NONCOMPENSATORY_ENDPOINTS",
            "Identity, realism, depth, transition liking, and overall liking require five separate noncompensatory gates.",
        )
    observed_primary_endpoints = {
        endpoint
        for trial in request.training_trials
        for endpoint in trial.primary_endpoints
    }
    if not {
        item.value for item in _REQUIRED_NONCOMPENSATORY_ENDPOINTS
    }.issubset(observed_primary_endpoints):
        _append_issue(
            codes,
            blockers,
            "HOLD_NONCOMPENSATORY_ENDPOINTS",
            "Every mandatory endpoint must be observed explicitly by the controlled trial sequence.",
        )
    compensation_rule = grammar.anti_compensation_rule.casefold()
    if not (
        "cannot compensate" in compensation_rule
        or "may not compensate" in compensation_rule
        or "no gain can offset" in compensation_rule
        or "must each pass" in compensation_rule
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_COMPENSATORY_ACCEPTANCE",
            "The grammar must state that every endpoint passes independently.",
        )
    for trial in request.training_trials:
        folded = trial.accept_rule.casefold()
        if any(marker in folded for marker in _COMPENSATORY_ACCEPTANCE_MARKERS):
            _append_issue(
                codes,
                blockers,
                "HOLD_COMPENSATORY_ACCEPTANCE",
                f"{trial.trial_id} uses a weighted or aggregate acceptance rule.",
            )
    if any(
        trial_id not in trials_by_id
        for trial_id in grammar.anti_collapse_trial_ids
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_EFFECTIVE_COMPLEXITY",
            "Every relational anti-collapse trial must exist in the closed sequence.",
        )

    all_wood_ids = {
        role.material_id
        for role in architecture.material_roles
        if role.material_class is FloralMaterialClass.WOOD
    }
    if all_wood_ids:
        wood_trial = (
            trials_by_id.get(background.wood_nonredundancy_trial_id)
            if background.wood_nonredundancy_trial_id is not None
            else None
        )
        wood_primary = set(wood_trial.primary_endpoints) if wood_trial else set()
        wood_failures = {
            endpoint.upper()
            for endpoint in wood_trial.failure_endpoints
        } if wood_trial else set()
        if (
            background.mode
            not in {
                FloralBackgroundMode.FLOWER_LINKED_WOOD,
                FloralBackgroundMode.TARGET_LINKED_HYBRID,
            }
            or not all_wood_ids.issubset(background_ids)
            or wood_trial is None
            or not all_wood_ids.issubset(wood_trial.intervention_material_ids)
            or not {
                item.value for item in _REQUIRED_NONCOMPENSATORY_ENDPOINTS
            }.issubset(wood_primary)
            or not any("WOOD_TAKEOVER" in item for item in wood_failures)
            or not any("IDENTITY" in item for item in wood_failures)
            or not any("REALISM" in item for item in wood_failures)
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_WOOD_NONREDUNDANCY",
                "Wood has no quota and is admissible only through an exact target-linked nonredundancy trial with separate identity, realism, depth, transition-liking, and overall-liking gates.",
            )


def _result(
    request: FloralDesignRequestV1,
    *,
    state: FloralDesignState,
    reason_codes: tuple[str, ...],
    selected_trial: FloralTrainingTrialV1 | None,
    deferred_trial_ids: tuple[str, ...],
    quantitative_oav_holds: tuple[str, ...],
    blockers: tuple[str, ...],
) -> FloralDesignResultV1:
    return FloralDesignResultV1(
        state=state,
        reason_codes=reason_codes,
        request_sha256=request.record_sha256,
        selected_trial=selected_trial,
        deferred_trial_ids=deferred_trial_ids,
        quantitative_oav_holds=quantitative_oav_holds,
        blockers=blockers,
        identity=request.identity,
        strategy=request.strategy,
        ideal_materials=request.ideal_materials,
        current_build_materials=request.current_build_materials,
        missing_chemical_impacts=request.missing_chemical_impacts,
    )


def evaluate_floral_design(request: FloralDesignRequestV1) -> FloralDesignResultV1:
    """Return one target-scoped experiment, NO_CHANGE, NOT_APPLICABLE, or HOLD."""

    if not isinstance(request, FloralDesignRequestV1):
        raise TypeError("request must be a FloralDesignRequestV1")

    if not any(
        subject.role in {FloralSubjectRole.LEAD, FloralSubjectRole.CO_LEAD}
        for subject in request.identity.floral_subjects
    ):
        return _result(
            request,
            state=FloralDesignState.NOT_APPLICABLE,
            reason_codes=("FLORAL_NOT_PRIMARY",),
            selected_trial=None,
            deferred_trial_ids=tuple(trial.trial_id for trial in request.training_trials),
            quantitative_oav_holds=(),
            blockers=(),
        )

    codes: list[str] = []
    blockers: list[str] = []
    identity = request.identity
    if identity.ideal_formula_ref == identity.current_inventory_build_ref:
        _append_issue(
            codes,
            blockers,
            "HOLD_TARGET_BUILD_COLLAPSE",
            "TARGET/IDEAL and CURRENT-INVENTORY references must remain distinct.",
        )

    allowed_sources = frozenset(identity.allowed_source_classes)
    if not allowed_sources.issubset(_ALLOWED_SOURCE_CLASSES):
        _append_issue(
            codes,
            blockers,
            "HOLD_SOURCE_CLASS",
            "Identity policy contains an unauthorized source class.",
        )
    all_materials = (*request.ideal_materials, *request.current_build_materials)
    for material in all_materials:
        if material.source_class not in allowed_sources:
            _append_issue(
                codes,
                blockers,
                "HOLD_SOURCE_CLASS",
                f"{material.material} uses source class {material.source_class.value}.",
            )

    current_ids = tuple(item.material_id for item in request.current_build_materials)
    if len(current_ids) != len(set(current_ids)):
        _append_issue(
            codes,
            blockers,
            "HOLD_DUPLICATE_MATERIAL_ID",
            "Current-build material IDs must be unique.",
        )
    for material in request.current_build_materials:
        if material.inventory_state is not InventoryBindingState.OWNED:
            _append_issue(
                codes,
                blockers,
                "HOLD_CURRENT_BUILD_MISSING",
                f"{material.material} is not bound as owned current inventory.",
            )

    facets_by_id = {item.facet_id: item for item in request.facets}
    if len(facets_by_id) != len(request.facets):
        _append_issue(
            codes,
            blockers,
            "HOLD_DUPLICATE_FACET_ID",
            "Facet IDs must be unique.",
        )
    for facet in request.facets:
        if not facet.omission_loss or not facet.controlled_comparison_ref:
            _append_issue(
                codes,
                blockers,
                "HOLD_DECORATIVE_FACET",
                f"{facet.facet_id} lacks omission loss or a discriminating comparison.",
            )

    coupling = request.coupling
    if request.strategy is FloralDepthStrategy.AUTOGENOUS_POLARITY:
        if (
            coupling is None
            or len(coupling.facet_ids) < 2
            or any(facet_id not in facets_by_id for facet_id in coupling.facet_ids)
            or not coupling.shared_recognizers
            or not coupling.relationship_edges
            or not coupling.bridge
            or len(coupling.controlled_arms) != 2
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_STRATEGY_UNSUPPORTED",
                "Autogenous polarity requires two target facets and explicit reciprocal coupling.",
            )
    if (
        (request.wood_texture_contracts or request.background_contracts)
        and coupling is None
        and request.strategy is not FloralDepthStrategy.PRECISE_SIMPLICITY
    ):
        _append_issue(
            codes,
            blockers,
            "HOLD_EXTERNALIZED_DEPTH",
            "Wood texture or a resistant background cannot substitute for an internal flower-depth relation.",
        )

    observed_windows = {item.window_id for item in request.temporal_contour.windows}
    if not _REQUIRED_WINDOWS.issubset(observed_windows):
        _append_issue(
            codes,
            blockers,
            "HOLD_TEMPORAL_CONTOUR",
            "The fixed opening-through-8-hour floral contour is incomplete.",
        )

    preparations = {item.preparation_id: item for item in request.preparations}
    if len(preparations) != len(request.preparations):
        _append_issue(
            codes,
            blockers,
            "HOLD_PREPARATION_ID",
            "Preparation IDs must be unique.",
        )
    for preparation in request.preparations:
        if not _preparation_is_complete(preparation):
            _append_issue(
                codes,
                blockers,
                "HOLD_SUB_10_UL",
                f"{preparation.preparation_id} is not a complete measurable preparation.",
            )

    quantitative_holds: list[str] = []
    for material in all_materials:
        if (
            material.raw_stock_ul < 10
            or material.stock_fraction <= 0
            or material.stock_fraction > 1
            or material.active_ul <= 0
            or material.active_ppm <= 0
            or abs(material.raw_stock_ul * material.stock_fraction - material.active_ul)
            > _EPSILON
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_SUB_10_UL",
                f"{material.material} lacks a measurable, arithmetically closed stock delivery.",
            )
        if material.stock_fraction < 1 and material.exact_stock_ref is None:
            preparation = (
                preparations.get(material.preparation_id)
                if material.preparation_id is not None
                else None
            )
            if (
                preparation is None
                or not _preparation_is_complete(preparation)
                or abs(preparation.delivered_ul - material.raw_stock_ul) > _EPSILON
                or abs(preparation.delivered_active_ul - material.active_ul) > _EPSILON
            ):
                _append_issue(
                    codes,
                    blockers,
                    "HOLD_SUB_10_UL",
                    f"{material.material} dilution is not bound to an exact stock or preparation.",
                )
        if material.source_class in {
            FloralSourceClass.ESSENTIAL_OIL,
            FloralSourceClass.ABSOLUTE,
        }:
            if material.natural_oav_state is NaturalOAVState.NOT_APPLICABLE:
                _append_issue(
                    codes,
                    blockers,
                    "HOLD_NATURAL_OAV_AUTHORITY",
                    f"{material.material} lacks composite-natural OAV disposition.",
                )
            elif (
                material.natural_oav_state is NaturalOAVState.HOLD_LOT_OR_MODEL
                and material.material not in quantitative_holds
            ):
                quantitative_holds.append(material.material)

    current_by_id = {item.material_id: item for item in request.current_build_materials}
    for contract in request.wood_texture_contracts:
        if any(material_id not in current_by_id for material_id in contract.material_ids):
            _append_issue(
                codes,
                blockers,
                "HOLD_WOOD_TEXTURE_BINDING",
                f"{contract.contract_id} references an absent current-build material.",
            )

    musks = tuple(item for item in request.current_build_materials if item.is_musk)
    for musk in musks:
        if any(marker in musk.material.casefold() for marker in _EXCEPTION_MUSKS):
            _append_issue(
                codes,
                blockers,
                "HOLD_MUSK_EXCEPTION",
                f"{musk.material} is exception-only and lacks an exception contract.",
            )
    if len(musks) > 1:
        musk_ids = {item.material_id for item in musks}
        pairwise_trials = tuple(
            trial
            for trial in request.training_trials
            if trial.domain is TrainingDomain.MUSK
            and set(trial.intervention_material_ids) == musk_ids
            and len(trial.controlled_arms) >= 2 ** len(musks)
        )
        if not pairwise_trials:
            _append_issue(
                codes,
                blockers,
                "HOLD_MUSK_REDUNDANCY",
                "Multiple musks require a complete isolated interaction comparison.",
            )

    trials_by_id = {item.trial_id: item for item in request.training_trials}
    if len(trials_by_id) != len(request.training_trials):
        _append_issue(
            codes,
            blockers,
            "HOLD_DUPLICATE_TRIAL_ID",
            "Training trial IDs must be unique.",
        )
    for trial in request.training_trials:
        if any(value not in trials_by_id for value in trial.prerequisite_trial_ids):
            _append_issue(
                codes,
                blockers,
                "HOLD_TRIAL_PREREQUISITE",
                f"{trial.trial_id} references an unknown prerequisite.",
            )
        if len(trial.controlled_arms) < 2 or not any(
            "TOTAL" in constraint.upper() for constraint in trial.constant_constraints
        ):
            _append_issue(
                codes,
                blockers,
                "HOLD_COMPARISON_CLOSURE",
                f"{trial.trial_id} lacks two arms or a constant-total constraint.",
            )
        if not _source_hashes(trial.evidence_refs):
            _append_issue(
                codes,
                blockers,
                "HOLD_SOURCE_BINDING",
                f"{trial.trial_id} lacks an exact SHA-256 evidence binding.",
            )

    _validate_architecture_contract(
        request,
        facets_by_id=facets_by_id,
        current_by_id=current_by_id,
        trials_by_id=trials_by_id,
        codes=codes,
        blockers=blockers,
    )
    _validate_relational_grammar(
        request,
        facets_by_id=facets_by_id,
        current_by_id=current_by_id,
        trials_by_id=trials_by_id,
        codes=codes,
        blockers=blockers,
    )

    if codes:
        return _result(
            request,
            state=FloralDesignState.HOLD,
            reason_codes=tuple(codes),
            selected_trial=None,
            deferred_trial_ids=tuple(trial.trial_id for trial in request.training_trials),
            quantitative_oav_holds=tuple(quantitative_holds),
            blockers=tuple(blockers),
        )

    if request.strategy is FloralDepthStrategy.PRECISE_SIMPLICITY:
        if request.training_trials:
            return _result(
                request,
                state=FloralDesignState.HOLD,
                reason_codes=("HOLD_PRECISE_SIMPLICITY_PADDING",),
                selected_trial=None,
                deferred_trial_ids=tuple(trial.trial_id for trial in request.training_trials),
                quantitative_oav_holds=tuple(quantitative_holds),
                blockers=("Precise simplicity may not carry decorative training trials.",),
            )
        return _result(
            request,
            state=FloralDesignState.NO_CHANGE,
            reason_codes=("NO_TARGET_DEFICIENCY",),
            selected_trial=None,
            deferred_trial_ids=(),
            quantitative_oav_holds=tuple(quantitative_holds),
            blockers=(),
        )

    passed = set(request.passed_trial_ids)
    eligible = tuple(
        trial
        for trial in request.training_trials
        if trial.trial_id not in passed
        and set(trial.prerequisite_trial_ids).issubset(passed)
    )
    if not eligible:
        return _result(
            request,
            state=FloralDesignState.HOLD,
            reason_codes=("HOLD_NO_CLOSED_COMPARISON",),
            selected_trial=None,
            deferred_trial_ids=tuple(
                trial.trial_id
                for trial in request.training_trials
                if trial.trial_id not in passed
            ),
            quantitative_oav_holds=tuple(quantitative_holds),
            blockers=("No prerequisite-satisfied closed comparison is available.",),
        )
    first_stage = min(trial.stage_order for trial in eligible)
    first = tuple(trial for trial in eligible if trial.stage_order == first_stage)
    if len(first) != 1:
        return _result(
            request,
            state=FloralDesignState.HOLD,
            reason_codes=("HOLD_MULTIPLE_ACTIVE_TRIALS",),
            selected_trial=None,
            deferred_trial_ids=tuple(trial.trial_id for trial in request.training_trials),
            quantitative_oav_holds=tuple(quantitative_holds),
            blockers=("Exactly one trial must occupy the next stage.",),
        )
    selected = first[0]
    deferred = tuple(
        trial.trial_id
        for trial in sorted(request.training_trials, key=lambda item: (item.stage_order, item.trial_id))
        if trial.trial_id != selected.trial_id and trial.trial_id not in passed
    )
    return _result(
        request,
        state=FloralDesignState.READY,
        reason_codes=("ONE_CLOSED_COMPARISON",),
        selected_trial=selected,
        deferred_trial_ids=deferred,
        quantitative_oav_holds=tuple(quantitative_holds),
        blockers=(),
    )


__all__ = [
    "FloralArchitectureContractV1",
    "FloralArchitectureContractV2",
    "FloralBackgroundContractV1",
    "FloralBackgroundMode",
    "FloralCouplingContractV1",
    "FloralDepthStrategy",
    "FloralDesignRequestV1",
    "FloralDesignResultV1",
    "FloralDesignState",
    "FloralDosePreparationV1",
    "FloralEndpointGateV1",
    "FloralEvaluationEndpoint",
    "FloralFacetClass",
    "FloralFacetV1",
    "FloralIdentityContractV1",
    "FloralInterfaceEdgeV1",
    "FloralMaterialClass",
    "FloralMaterialDoseV1",
    "FloralMaterialRoleV1",
    "FloralRelationalGrammarV1",
    "FloralScope",
    "FloralSourceClass",
    "FloralSubjectRole",
    "FloralSubjectAnatomyV1",
    "FloralSubjectV1",
    "FloralTemporalBand",
    "FloralTemporalContourV1",
    "FloralTemporalWindowV1",
    "FloralTrainingTrialV1",
    "InventoryBindingState",
    "MissingChemicalImpactV1",
    "NaturalOAVState",
    "TrainingDomain",
    "WoodTextureContractV1",
    "evaluate_floral_design",
]
