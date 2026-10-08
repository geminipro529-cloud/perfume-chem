"""Deep Plane handoff for the DHI 2011 05443/A architecture study.

This adapter turns the target-specific DHI architecture into four recursive
resolution levels, each assessed across all thirteen formulation-intelligence
planes.  The perceptual graph inside those assessments preserves six artistic
perfume layers plus one cross-layer structural field.  The adapter also emits
an exact raw-stock-volume command packet for another Codex model or bench-card
renderer.  The packet is operationally complete at the stated raw-volume
level; it does not convert modeled structure into observed similarity, safety,
stability, or release authority.

The generic Deep Plane runtime remains pure and read-only.  This module is the
target-specific caller: it supplies the DHI identity, layer graph, mixture
rows, uncertainty, and controlled probes that the generic runtime deliberately
does not invent.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from engine.calibration.hashing import stable_json_hash
from engine.formulation_intelligence.contracts import (
    AssessmentScope,
    AuthorityCeiling,
    ClaimKind,
    CriterionDirection,
    CriterionValue,
    EvidenceClass,
    ParetoCriterion,
    PlaneAssessment,
    PlaneConflict,
    PlaneId,
    ProvenanceRef,
    ScopedClaim,
    UnknownFact,
)
from engine.formulation_intelligence.deep_plane_runtime import (
    DeepPlaneLayerRequest,
    DeepPlaneRuntimeReceipt,
    DeepPlaneRuntimeRequest,
    execute_deep_plane_runtime_candidate,
)
from engine.perception.dhi_2011_architecture import (
    DHI2011ArchitectureRequestV1,
    DHI2011ArchitectureResultV1,
    DHI2011EvidenceTier,
    DHI2011ProgramState,
    build_default_dhi_2011_architecture,
)

CONCENTRATE_UL = 6000.0
NOMINAL_FINISHED_UL = 30000.0
ETHANOL_96_ADDITION_UL = 24000.0
PARENT_FORMULA_REF = "formulas/DHI-11_Velours_d_Iris_05443A_30mL_20pct.md"
BASKET_LABELS: dict[int, str] = {
    1: "Always used",
    2: "Vetivers",
    3: "Woods",
    4: "Wood modifiers and ambers",
    5: "Wood-vetivers",
    6: "Musks",
    7: "Muguet and lavender",
    8: "Jasmine, indole, and magnolia",
    9: "Ylang, orange flower, and narcotics",
    10: "Rose",
    11: "Iris and orris",
    12: "Edible smells",
    13: "Edible spices",
    14: "My favorite smells",
    15: "Fruits",
    16: "Aldehydes",
    17: "Green smelling things",
}


class DHI2011ClaimStatus(str, Enum):
    """Orthogonal status labels; evidence tier and claim status never collapse."""

    EXACT_05443A_APPLICABILITY_MODERATE = "EXACT_05443A_APPLICABILITY_MODERATE"
    DHI_LINEAGE_CONTINUITY_ONLY = "DHI_LINEAGE_CONTINUITY_ONLY"
    PACKAGE_PRESENCE_ONLY = "PACKAGE_PRESENCE_ONLY"
    MATERIAL_IDENTITY_UNCONFIRMED = "MATERIAL_IDENTITY_UNCONFIRMED"
    MATERIAL_PROXY_EQUIVALENCE_UNTESTED = "MATERIAL_PROXY_EQUIVALENCE_UNTESTED"
    QUANTITATIVE_FORMULA_UNKNOWN = "QUANTITATIVE_FORMULA_UNKNOWN"
    TEMPORAL_BEHAVIOR_PREDICTED_NOT_OBSERVED = (
        "TEMPORAL_BEHAVIOR_PREDICTED_NOT_OBSERVED"
    )
    SPATIAL_BEHAVIOR_PREDICTED_NOT_OBSERVED = (
        "SPATIAL_BEHAVIOR_PREDICTED_NOT_OBSERVED"
    )
    SENSORY_RELATION_HYPOTHESIS = "SENSORY_RELATION_HYPOTHESIS"
    REFERENCE_SIMILARITY_NOT_TESTED = "REFERENCE_SIMILARITY_NOT_TESTED"
    PHYSICAL_PERFORMANCE_WITHHELD = "PHYSICAL_PERFORMANCE_WITHHELD"
    SAFETY_STABILITY_RELEASE_WITHHELD = "SAFETY_STABILITY_RELEASE_WITHHELD"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(
    values: Iterable[str], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    result = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must contain unique values")
    return result


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return, union-attr]
    return value


class _CanonicalRecord:
    SCHEMA_VERSION: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _json_value(getattr(self, item.name)) for item in fields(self)},
        }

    @property
    def record_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class DHI2011StructuralFieldV1(_CanonicalRecord):
    """A cross-layer field, deliberately not promoted to a seventh note layer."""

    SCHEMA_VERSION = "dhi_2011_structural_field_v1"

    field_id: str
    display_name: str
    function_ids: tuple[str, ...]
    phase_presence: tuple[str, ...]
    spatial_role: str
    target_link: str
    success_observable: str
    failure_observable: str
    proxy_intent_ids: tuple[str, ...]
    evidence_tier: DHI2011EvidenceTier
    claim_status: DHI2011ClaimStatus
    falsification_probe_id: str

    def __post_init__(self) -> None:
        for name in (
            "field_id",
            "display_name",
            "spatial_role",
            "target_link",
            "success_observable",
            "failure_observable",
            "falsification_probe_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("function_ids", "phase_presence", "proxy_intent_ids"):
            object.__setattr__(self, name, _text_tuple(getattr(self, name), name))
        object.__setattr__(self, "evidence_tier", DHI2011EvidenceTier(self.evidence_tier))
        object.__setattr__(self, "claim_status", DHI2011ClaimStatus(self.claim_status))


@dataclass(frozen=True, slots=True)
class DHI2011LayerCommandV1(_CanonicalRecord):
    """The complete artistic command for one DHI layer."""

    SCHEMA_VERSION = "dhi_2011_layer_command_v1"

    layer_id: str
    display_name: str
    source_basis: str
    inference_boundary: str
    owned_function_ids: tuple[str, ...]
    phase_presence: tuple[str, ...]
    spatial_role: str
    texture: str
    required_recognizer: str
    omission_loss: str
    takeover_condition: str
    forbidden_drift_codes: tuple[str, ...]
    evidence_tiers: tuple[DHI2011EvidenceTier, ...]
    claim_statuses: tuple[DHI2011ClaimStatus, ...]
    falsification_probe_ids: tuple[str, ...]
    incoming_transition_ids: tuple[str, ...]
    outgoing_transition_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "layer_id",
            "display_name",
            "source_basis",
            "inference_boundary",
            "spatial_role",
            "texture",
            "required_recognizer",
            "omission_loss",
            "takeover_condition",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "owned_function_ids",
            "phase_presence",
            "forbidden_drift_codes",
            "falsification_probe_ids",
        ):
            object.__setattr__(self, name, _text_tuple(getattr(self, name), name))
        for name in ("incoming_transition_ids", "outgoing_transition_ids"):
            object.__setattr__(
                self,
                name,
                _text_tuple(getattr(self, name), name, allow_empty=True),
            )
        tiers = tuple(DHI2011EvidenceTier(item) for item in self.evidence_tiers)
        statuses = tuple(DHI2011ClaimStatus(item) for item in self.claim_statuses)
        if not tiers or len(tiers) != len(set(tiers)):
            raise ValueError("evidence_tiers must be nonempty and unique")
        if not statuses or len(statuses) != len(set(statuses)):
            raise ValueError("claim_statuses must be nonempty and unique")
        object.__setattr__(self, "evidence_tiers", tiers)
        object.__setattr__(self, "claim_statuses", statuses)


@dataclass(frozen=True, slots=True)
class DHI2011CompoundRowV1(_CanonicalRecord):
    """One exact raw-stock-volume row in basket-first order."""

    SCHEMA_VERSION = "dhi_2011_compound_row_v1"

    step: int
    basket: int
    engine_material: str
    physical_stock_label: str
    dilution_label: str
    raw_ul: float
    nominal_active_ul: float
    active_ppm_in_concentrate: float
    architecture_node_ids: tuple[str, ...]
    function_ids: tuple[str, ...]
    role: str
    analytical_status: str

    def __post_init__(self) -> None:
        for name in ("step", "basket"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in (
            "engine_material",
            "physical_stock_label",
            "dilution_label",
            "role",
            "analytical_status",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        raw = float(self.raw_ul)
        active = float(self.nominal_active_ul)
        ppm = float(self.active_ppm_in_concentrate)
        if raw <= 0 or active < 0 or active > raw or ppm < 0:
            raise ValueError("compound-row quantities are inconsistent")
        expected_ppm = active / CONCENTRATE_UL * 1_000_000.0
        if abs(ppm - expected_ppm) > 1e-6:
            raise ValueError("active_ppm_in_concentrate does not match nominal_active_ul")
        object.__setattr__(self, "raw_ul", raw)
        object.__setattr__(self, "nominal_active_ul", active)
        object.__setattr__(self, "active_ppm_in_concentrate", ppm)
        object.__setattr__(
            self,
            "architecture_node_ids",
            _text_tuple(self.architecture_node_ids, "architecture_node_ids"),
        )
        object.__setattr__(self, "function_ids", _text_tuple(self.function_ids, "function_ids"))


@dataclass(frozen=True, slots=True)
class DHI2011BasketCheckpointV1(_CanonicalRecord):
    """One explicit physical-basket checkpoint, including empty-basket skips."""

    SCHEMA_VERSION = "dhi_2011_basket_checkpoint_v1"

    basket: int
    basket_label: str
    action: str
    row_steps: tuple[int, ...]
    subtotal_ul: float
    running_total_ul: float

    def __post_init__(self) -> None:
        if isinstance(self.basket, bool) or not isinstance(self.basket, int):
            raise TypeError("basket must be an integer")
        if self.basket not in BASKET_LABELS:
            raise ValueError("basket must be one of the seventeen physical baskets")
        object.__setattr__(self, "basket_label", _text(self.basket_label, "basket_label"))
        if self.basket_label != BASKET_LABELS[self.basket]:
            raise ValueError("basket_label does not match the physical basket map")
        steps = tuple(self.row_steps)
        if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in steps):
            raise ValueError("row_steps must contain positive integers")
        if steps != tuple(sorted(set(steps))):
            raise ValueError("row_steps must be unique and ordered")
        object.__setattr__(self, "row_steps", steps)
        subtotal = float(self.subtotal_ul)
        running = float(self.running_total_ul)
        if subtotal < 0.0 or running < subtotal:
            raise ValueError("basket checkpoint quantities are inconsistent")
        expected_action = "COMPOUND" if steps else "SKIP"
        if self.action != expected_action:
            raise ValueError(f"basket checkpoint action must be {expected_action}")
        if bool(steps) != (subtotal > 0.0):
            raise ValueError("occupied basket checkpoints require a positive subtotal")
        object.__setattr__(self, "subtotal_ul", subtotal)
        object.__setattr__(self, "running_total_ul", running)


@dataclass(frozen=True, slots=True)
class DHI2011CompounderCommandV1(_CanonicalRecord):
    """No-invention command packet usable by another Codex model."""

    SCHEMA_VERSION = "dhi_2011_compounder_command_v1"

    command_id: str
    mode: str
    target_id: str
    architecture_request_sha256: str
    deep_plane_request_sha256: str
    formula_binding_ref: str
    formula_rows_sha256: str
    immediate_parent_ref: str | None
    parent_semantics: str
    raw_concentrate_ul: float
    ethanol_96_addition_ul: float
    nominal_finished_ul: float
    finish_convention: str
    rows: tuple[DHI2011CompoundRowV1, ...]
    basket_checkpoints: tuple[DHI2011BasketCheckpointV1, ...]
    layer_commands: tuple[DHI2011LayerCommandV1, ...]
    structural_fields: tuple[DHI2011StructuralFieldV1, ...]
    artistic_layer_order: tuple[str, ...]
    model_instructions: tuple[str, ...]
    unresolved_facts: tuple[str, ...]
    raw_volume_recipe_complete: bool = True
    agent_handoff_ready: bool = True
    basket_compounding_card_ready: bool = True
    component_count_used_as_complexity: bool = False
    physical_execution_authorized: bool = False
    sensory_similarity_authorized: bool = False
    safety_release_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "command_id",
            "mode",
            "target_id",
            "architecture_request_sha256",
            "deep_plane_request_sha256",
            "formula_binding_ref",
            "formula_rows_sha256",
            "parent_semantics",
            "finish_convention",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.mode != "EXPLORATORY_RAW_VOLUME_BUILD":
            raise ValueError("DHI compounder command mode is fixed")
        for name in (
            "architecture_request_sha256",
            "deep_plane_request_sha256",
            "formula_rows_sha256",
        ):
            value = getattr(self, name)
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if self.immediate_parent_ref != PARENT_FORMULA_REF:
            raise ValueError("The smooth successor must bind the rejected 14-row parent")
        rows = tuple(self.rows)
        checkpoints = tuple(self.basket_checkpoints)
        layers = tuple(self.layer_commands)
        structural_fields = tuple(self.structural_fields)
        if not rows or any(not isinstance(item, DHI2011CompoundRowV1) for item in rows):
            raise TypeError("rows must contain DHI2011CompoundRowV1 values")
        if len(checkpoints) != len(BASKET_LABELS) or any(
            not isinstance(item, DHI2011BasketCheckpointV1) for item in checkpoints
        ):
            raise TypeError("basket_checkpoints must contain all seventeen physical baskets")
        if not layers or any(not isinstance(item, DHI2011LayerCommandV1) for item in layers):
            raise TypeError("layer_commands must contain DHI2011LayerCommandV1 values")
        if not structural_fields or any(
            not isinstance(item, DHI2011StructuralFieldV1) for item in structural_fields
        ):
            raise TypeError("structural_fields must contain DHI2011StructuralFieldV1 values")
        if tuple(item.step for item in rows) != tuple(range(1, len(rows) + 1)):
            raise ValueError("compound rows must have contiguous one-based steps")
        if tuple(item.basket for item in rows) != tuple(sorted(item.basket for item in rows)):
            raise ValueError("compound rows must remain in basket-first order")
        for basket in sorted({item.basket for item in rows}):
            amounts = [item.raw_ul for item in rows if item.basket == basket]
            if amounts != sorted(amounts, reverse=True):
                raise ValueError("raw doses must descend inside each occupied basket")
        if len({item.engine_material for item in rows}) != len(rows):
            raise ValueError("compound rows require unique engine materials")
        if abs(sum(item.raw_ul for item in rows) - CONCENTRATE_UL) > 1e-9:
            raise ValueError("compound rows must total exactly 6000 uL")
        if min(item.raw_ul for item in rows) < 10.0:
            raise ValueError("raw doses below 10 uL require a prepared dilution")
        running = 0.0
        for basket, checkpoint in zip(BASKET_LABELS, checkpoints, strict=True):
            basket_rows = tuple(item for item in rows if item.basket == basket)
            subtotal = sum(item.raw_ul for item in basket_rows)
            running += subtotal
            if checkpoint.basket != basket:
                raise ValueError("basket checkpoints must preserve all seventeen baskets in order")
            if checkpoint.row_steps != tuple(item.step for item in basket_rows):
                raise ValueError("basket checkpoint row_steps do not match command rows")
            if abs(checkpoint.subtotal_ul - subtotal) > 1e-9:
                raise ValueError("basket checkpoint subtotal does not match command rows")
            if abs(checkpoint.running_total_ul - running) > 1e-9:
                raise ValueError("basket checkpoint running total does not match command rows")
        if abs(running - CONCENTRATE_UL) > 1e-9:
            raise ValueError("basket checkpoints must close at exactly 6000 uL")
        expected_rows_hash = stable_json_hash([item.as_dict() for item in rows])
        if self.formula_rows_sha256 != expected_rows_hash:
            raise ValueError("formula_rows_sha256 does not bind the command rows")
        if float(self.raw_concentrate_ul) != CONCENTRATE_UL:
            raise ValueError("raw_concentrate_ul must remain 6000")
        if float(self.ethanol_96_addition_ul) != ETHANOL_96_ADDITION_UL:
            raise ValueError("ethanol_96_addition_ul must remain 24000")
        if float(self.nominal_finished_ul) != NOMINAL_FINISHED_UL:
            raise ValueError("nominal_finished_ul must remain 30000")
        order = _text_tuple(self.artistic_layer_order, "artistic_layer_order")
        if order != tuple(item.layer_id for item in layers):
            raise ValueError("artistic_layer_order must match layer_commands")
        allowed_nodes = {
            *(item.layer_id for item in layers),
            *(item.field_id for item in structural_fields),
        }
        used_nodes = {node for row in rows for node in row.architecture_node_ids}
        if used_nodes != allowed_nodes:
            missing = sorted(allowed_nodes.difference(used_nodes))
            unknown = sorted(used_nodes.difference(allowed_nodes))
            raise ValueError(
                "compound rows must cover every architecture node exactly within "
                f"the declared graph; missing={missing}, unknown={unknown}"
            )
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "basket_checkpoints", checkpoints)
        object.__setattr__(self, "layer_commands", layers)
        object.__setattr__(self, "structural_fields", structural_fields)
        object.__setattr__(self, "artistic_layer_order", order)
        object.__setattr__(
            self,
            "model_instructions",
            _text_tuple(self.model_instructions, "model_instructions"),
        )
        object.__setattr__(
            self,
            "unresolved_facts",
            _text_tuple(self.unresolved_facts, "unresolved_facts"),
        )
        for name in (
            "raw_volume_recipe_complete",
            "agent_handoff_ready",
            "basket_compounding_card_ready",
        ):
            if getattr(self, name) is not True:
                raise ValueError(f"{name} must remain true for this exact command")
        for name in (
            "component_count_used_as_complexity",
            "physical_execution_authorized",
            "sensory_similarity_authorized",
            "safety_release_authorized",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"{name} must remain false")


@dataclass(frozen=True, slots=True)
class DHI2011DeepPlaneProgramV1(_CanonicalRecord):
    """Integrated DHI architecture, recursive receipt, and compounder command."""

    SCHEMA_VERSION = "dhi_2011_deep_plane_program_v1"

    architecture_request: DHI2011ArchitectureRequestV1
    architecture_result: DHI2011ArchitectureResultV1
    deep_plane_request: DeepPlaneRuntimeRequest
    deep_plane_receipt: DeepPlaneRuntimeReceipt
    compounder_command: DHI2011CompounderCommandV1
    structural_state: str = "DEEP_PLANE_HANDOFF_READY"
    basket_compounding_card_ready: bool = True
    empirical_authority: bool = False
    formula_generation_authorized: bool = False
    formula_mutation_authorized: bool = False
    physical_execution_authorized: bool = False
    compounding_authorized: bool = False
    sensory_authority: bool = False
    liking_authority: bool = False
    similarity_authority: bool = False
    safety_authority: bool = False
    stability_authority: bool = False
    release_authority: bool = False

    def __post_init__(self) -> None:
        if self.architecture_result.state is not DHI2011ProgramState.THEORY_SELECTED:
            raise ValueError("DHI Deep Plane handoff requires one theory-selected architecture")
        if self.architecture_result.request_sha256 != self.architecture_request.record_sha256:
            raise ValueError("architecture result is not bound to the architecture request")
        if self.deep_plane_receipt.request != self.deep_plane_request:
            raise ValueError("Deep Plane receipt is not bound to its request")
        if self.compounder_command.architecture_request_sha256 != (
            self.architecture_request.record_sha256
        ):
            raise ValueError("compounder command is not bound to the DHI architecture")
        if self.compounder_command.deep_plane_request_sha256 != (
            self.deep_plane_request.content_sha256
        ):
            raise ValueError("compounder command is not bound to the Deep Plane request")
        expected_depths = (
            "deep:target-silhouette",
            "deep:perceptual-layer-graph",
            "deep:material-role-geometry",
            "deep:compounder-and-experiment-control",
        )
        if tuple(item.layer_id for item in self.deep_plane_request.layers) != expected_depths:
            raise ValueError("Deep Plane recursion must preserve the four resolution levels")
        if len(self.compounder_command.layer_commands) != 6:
            raise ValueError("the perceptual layer graph must preserve all six artistic layers")
        if any(len(item.assessments) != len(PlaneId) for item in self.deep_plane_request.layers):
            raise ValueError("every DHI resolution level must contain all thirteen planes")
        if self.structural_state != "DEEP_PLANE_HANDOFF_READY":
            raise ValueError("structural_state is fixed for this program version")
        if self.basket_compounding_card_ready is not True:
            raise ValueError("basket_compounding_card_ready must remain true")
        if self.compounder_command.basket_compounding_card_ready is not True:
            raise ValueError("compounder command must carry a ready basket card")
        for name in (
            "empirical_authority",
            "formula_generation_authorized",
            "formula_mutation_authorized",
            "physical_execution_authorized",
            "compounding_authorized",
            "sensory_authority",
            "liking_authority",
            "similarity_authority",
            "safety_authority",
            "stability_authority",
            "release_authority",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"{name} must remain false")


def _structural_field() -> DHI2011StructuralFieldV1:
    return DHI2011StructuralFieldV1(
        field_id="field:iris-air-seam",
        display_name="Iris Air Seam",
        function_ids=("fn:negative-space",),
        phase_presence=("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"),
        spatial_role="interstitial separation around the dense Orris Body and its rear wood frame",
        target_link="preserve foreground-background legibility without adding a seventh named note layer",
        success_observable="iris remains dimensional, ventilated, and clearly separate from the wood frame",
        failure_observable="the perfume becomes either an opaque powder block or a generic radiant-wood aura",
        proxy_intent_ids=("intent:hedione", "intent:iso-e", "intent:benzyl-benzoate"),
        evidence_tier=DHI2011EvidenceTier.PERFUMER_INFERENCE,
        claim_status=DHI2011ClaimStatus.SPATIAL_BEHAVIOR_PREDICTED_NOT_OBSERVED,
        falsification_probe_id="probe:dhi2011:whole-formula",
    )


def _layer_commands(request: DHI2011ArchitectureRequestV1) -> tuple[DHI2011LayerCommandV1, ...]:
    by_id = {item.layer_id: item for item in request.layers}
    incoming = {
        layer_id: tuple(
            item.transition_id for item in request.transitions if item.target_layer_id == layer_id
        )
        for layer_id in by_id
    }
    outgoing = {
        layer_id: tuple(
            item.transition_id for item in request.transitions if item.source_layer_id == layer_id
        )
        for layer_id in by_id
    }

    def command(
        layer_id: str,
        source_basis: str,
        inference_boundary: str,
        recognizer: str,
        omission_loss: str,
        drift_codes: tuple[str, ...],
        tiers: tuple[DHI2011EvidenceTier, ...],
        statuses: tuple[DHI2011ClaimStatus, ...],
        probes: tuple[str, ...],
    ) -> DHI2011LayerCommandV1:
        layer = by_id[layer_id]
        return DHI2011LayerCommandV1(
            layer_id=layer.layer_id,
            display_name=layer.identity,
            source_basis=source_basis,
            inference_boundary=inference_boundary,
            owned_function_ids=layer.owned_function_ids,
            phase_presence=layer.temporal_position,
            spatial_role=layer.spatial_position,
            texture=layer.texture,
            required_recognizer=recognizer,
            omission_loss=omission_loss,
            takeover_condition=layer.takeover_condition,
            forbidden_drift_codes=drift_codes,
            evidence_tiers=tiers,
            claim_statuses=statuses,
            falsification_probe_ids=probes,
            incoming_transition_ids=incoming[layer_id],
            outgoing_transition_ids=outgoing[layer_id],
        )

    return (
        command(
            "layer:lavender-veil",
            "The contemporaneous 2011 launch report names lavender as the opening.",
            "Tailoring, ester polish, short duration, and the exact fold into powder are unobserved perfumer hypotheses.",
            "Lavender is legible initially and is no longer the subject in the iris heart.",
            "Without it, the fragrance begins as a preformed cosmetic block with no entry perspective.",
            ("FOUGERE_TAKEOVER", "STATIC_NO_HANDOFF"),
            (
                DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
            ),
            (
                DHI2011ClaimStatus.EXACT_05443A_APPLICABILITY_MODERATE,
                DHI2011ClaimStatus.TEMPORAL_BEHAVIOR_PREDICTED_NOT_OBSERVED,
            ),
            ("probe:dhi2011:lavender-frontier", "probe:dhi2011:whole-formula"),
        ),
        command(
            "layer:ambrette-pear-talc-membrane",
            "The 2011 report and Dior house description join ambrette, pear liqueur, powder, musk, and silk talc.",
            "The membrane topology, fermented inner glint, and late skin recurrence are unobserved relational hypotheses.",
            "Pear, musk, and talc read as one texture around iris rather than three independent notes.",
            "Without mediation, pear disappears or becomes literal fruit, talc becomes chalk, and the skin continuity breaks.",
            ("PEAR_CANDY_OBJECT", "WINE_MUSK_OBJECT", "LAUNDRY_SKIN_CLOSURE"),
            (
                DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION,
                DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
            ),
            (
                DHI2011ClaimStatus.DHI_LINEAGE_CONTINUITY_ONLY,
                DHI2011ClaimStatus.MATERIAL_PROXY_EQUIVALENCE_UNTESTED,
                DHI2011ClaimStatus.SENSORY_RELATION_HYPOTHESIS,
            ),
            (
                "probe:dhi2011:pear-continuum",
                "probe:dhi2011:ambrette-omission",
                "probe:dhi2011:talc-cushion",
                "probe:dhi2011:seam-smoothness",
                "probe:dhi2011:whole-formula",
            ),
        ),
        command(
            "layer:orris-body",
            "Iris or Tuscan iris butter and powder are repeated house and 2011 identity anchors.",
            "Powder body, violet mobility, root coolness, and a fatty woody seam are a construction hypothesis; the exact molecules are unknown.",
            "A dominant dimensional iris remains recognizable through the heart and is more specific than generic lipstick.",
            "Without it, no DHI recognizer remains; if collapsed, it becomes a flat ionone slab, chalk, violet candy, or cosmetic wax.",
            ("IRIS_IDENTITY_LOSS", "IONONE_SLAB", "VIOLET_CANDY", "COSMETIC_WAX"),
            (
                DHI2011EvidenceTier.CONFIRMED_MARKETING_ARCHITECTURE,
                DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION,
                DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
            ),
            (
                DHI2011ClaimStatus.DHI_LINEAGE_CONTINUITY_ONLY,
                DHI2011ClaimStatus.PACKAGE_PRESENCE_ONLY,
                DHI2011ClaimStatus.MATERIAL_IDENTITY_UNCONFIRMED,
                DHI2011ClaimStatus.QUANTITATIVE_FORMULA_UNKNOWN,
            ),
            (
                "probe:dhi2011:iris-anatomy",
                "probe:dhi2011:talc-cushion",
                "probe:dhi2011:seam-smoothness",
                "probe:dhi2011:whole-formula",
            ),
        ),
        command(
            "layer:amber-vanillic-shadow",
            "Dior supports amber and vanilla warmth; 05443/A package transcription supports coumarin presence only.",
            "An under-iris coumarinic geometry, roasted darkness, and any cocoa-like emergence are hypotheses; literal cocoa is unconfirmed.",
            "Warmth deepens the iris but is not named before it.",
            "Without it the heart is cold and thin; in excess it becomes dessert, tonka hay, pastry, or sweet fougere.",
            ("DESSERT_AMBER", "FOUGERE_TAKEOVER"),
            (
                DHI2011EvidenceTier.CONFIRMED_MARKETING_ARCHITECTURE,
                DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
            ),
            (
                DHI2011ClaimStatus.DHI_LINEAGE_CONTINUITY_ONLY,
                DHI2011ClaimStatus.PACKAGE_PRESENCE_ONLY,
                DHI2011ClaimStatus.SENSORY_RELATION_HYPOTHESIS,
            ),
            (
                "probe:dhi2011:cocoa-shadow",
                "probe:dhi2011:orivone-frontier",
                "probe:dhi2011:seam-smoothness",
            ),
        ),
        command(
            "layer:cedar-vetiver-counterform",
            "Virginia cedar and vetiver are the reported 2011 base, and Virginia cedar persists in Dior's identity language.",
            "Counterform, shared ionone grain, late reveal, and retention of iris are unobserved temporal and spatial hypotheses.",
            "Dry masculine wood becomes clearer as iris recedes while residual iris remains.",
            "Without it the drydown is cosmetic musk; in excess it becomes pencil cedar, root-smoke vetiver, or generic amberwood.",
            (
                "WOOD_RETURN_ABSENT",
                "PENCIL_CEDAR",
                "ROOT_SMOKE_VETIVER",
                "BLUE_AMBERWOOD_DRIFT",
            ),
            (
                DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT,
                DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
            ),
            (
                DHI2011ClaimStatus.EXACT_05443A_APPLICABILITY_MODERATE,
                DHI2011ClaimStatus.TEMPORAL_BEHAVIOR_PREDICTED_NOT_OBSERVED,
                DHI2011ClaimStatus.SPATIAL_BEHAVIOR_PREDICTED_NOT_OBSERVED,
            ),
            (
                "probe:dhi2011:wood-frontier",
                "probe:dhi2011:seam-smoothness",
                "probe:dhi2011:whole-formula",
            ),
        ),
        command(
            "layer:musky-skin-echo",
            "Ambrette's musky and silk-talc facets are persistent house architecture.",
            "Textile closure, late pear-talc recurrence, persistence, and the Ambrettolide mechanism all require reference-sample testing.",
            "The final trace retains a small iris and talc memory inside dry wood and intimate musk.",
            "Without it the ending is disconnected; in excess it becomes laundry, wine musk, or anonymous persistence.",
            ("LAUNDRY_SKIN_CLOSURE", "WINE_MUSK_OBJECT", "IRIS_ERASURE_BY_BASE"),
            (
                DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION,
                DHI2011EvidenceTier.PERFUMER_INFERENCE,
                DHI2011EvidenceTier.REFERENCE_SAMPLE_TEST_REQUIRED,
            ),
            (
                DHI2011ClaimStatus.DHI_LINEAGE_CONTINUITY_ONLY,
                DHI2011ClaimStatus.MATERIAL_PROXY_EQUIVALENCE_UNTESTED,
                DHI2011ClaimStatus.REFERENCE_SIMILARITY_NOT_TESTED,
            ),
            (
                "probe:dhi2011:ambrette-omission",
                "probe:dhi2011:musk-axes",
                "probe:dhi2011:talc-cushion",
                "probe:dhi2011:whole-formula",
            ),
        ),
    )


def _compound_row(
    step: int,
    basket: int,
    engine_material: str,
    physical_stock_label: str,
    dilution_label: str,
    raw_ul: float,
    nominal_fraction: float,
    node_ids: tuple[str, ...],
    function_ids: tuple[str, ...],
    role: str,
    analytical_status: str,
) -> DHI2011CompoundRowV1:
    active = raw_ul * nominal_fraction
    return DHI2011CompoundRowV1(
        step=step,
        basket=basket,
        engine_material=engine_material,
        physical_stock_label=physical_stock_label,
        dilution_label=dilution_label,
        raw_ul=raw_ul,
        nominal_active_ul=active,
        active_ppm_in_concentrate=active / CONCENTRATE_UL * 1_000_000.0,
        architecture_node_ids=node_ids,
        function_ids=function_ids,
        role=role,
        analytical_status=analytical_status,
    )


def _compound_rows() -> tuple[DHI2011CompoundRowV1, ...]:
    direct = "RAW_VOLUME_DIRECT; MASS_PPM_REQUIRES_DENSITY"
    natural = "RAW_VOLUME_DIRECT; LOT_COMPOSITION_UNMEASURED; COMPOSITE_OAV_SCREEN_ONLY"
    diluted = "RAW_VOLUME_DIRECT; DECLARED_WORKING_STOCK; ACTIVE_UL_IS_NOMINAL_SCREEN_ONLY"
    diluted_w_w = "RAW_VOLUME_DIRECT; W_W_STOCK; STOCK_SOLUTION_DENSITY_UNMEASURED; ACTIVE_UL_IS_NOMINAL_SCREEN_ONLY"
    return (
        _compound_row(1, 1, "Hedione", "Hedione", "neat", 140, 1.0, ("field:iris-air-seam", "layer:orris-body"), ("fn:negative-space",), "floral air spanning lavender decay, fruit ingress, and the iris edge", direct),
        _compound_row(2, 1, "Iso E Super", "Iso E Super", "neat", 140, 1.0, ("field:iris-air-seam", "layer:cedar-vetiver-counterform"), ("fn:negative-space", "fn:wood-return"), "transparent rear wood that receives the iris tail before cedar", direct),
        _compound_row(3, 1, "Benzyl Salicylate", "Benzyl Salicylate", "neat", 60, 1.0, ("layer:ambrette-pear-talc-membrane", "layer:musky-skin-echo"), ("fn:talc-cushion", "fn:skin-closure"), "waxy cosmetic film between ionone powder and musk velvet", direct),
        _compound_row(4, 1, "Benzyl Benzoate", "Benzyl Benzoate", "neat", 40, 1.0, ("field:iris-air-seam", "layer:musky-skin-echo"), ("fn:negative-space", "fn:skin-closure"), "sub-threshold slow mass and constant-total replacement reservoir", direct),
        _compound_row(5, 2, "Vetiver EO (India)", "Indian Vetiver EO (volume grade)", "neat", 140, 1.0, ("layer:cedar-vetiver-counterform",), ("fn:wood-return",), "dry earthy counterline in the late wood reveal", natural),
        _compound_row(6, 3, "Cedarwood oil Virginia", "Cedarwood oil Virginia", "neat", 250, 1.0, ("layer:cedar-vetiver-counterform",), ("fn:wood-return",), "Virginia-cedar identity and dry grain", natural),
        _compound_row(7, 3, "Cashmeran", "Cashmeran (neat)", "neat", 60, 1.0, ("layer:cedar-vetiver-counterform", "layer:musky-skin-echo"), ("fn:wood-softening", "fn:skin-closure"), "warm textile flex between powder, wood, and skin", direct),
        _compound_row(8, 3, "Sandalore", "Sandalore", "neat", 60, 1.0, ("layer:cedar-vetiver-counterform", "layer:musky-skin-echo"), ("fn:wood-softening",), "sub-threshold creamy seam hypothesis that rounds cedar into textile musk", direct),
        _compound_row(9, 5, "Vetival", "Vetival", "neat", 80, 1.0, ("layer:cedar-vetiver-counterform",), ("fn:wood-softening", "fn:wood-return"), "polished suede-vetiver bridge before the natural root counterline", direct),
        _compound_row(10, 6, "Ambrettolide", "Ambrettolide (10% w/w in DPG)", "10% w/w in DPG", 1600, 0.10, ("layer:ambrette-pear-talc-membrane", "layer:musky-skin-echo"), ("fn:ambrette-mediator", "fn:skin-closure"), "fruity-wine ambrette proxy binding pear, talc, iris, and skin", diluted_w_w),
        _compound_row(11, 6, "Ethylene Brassylate", "Ethylene Brassylate", "neat", 870, 1.0, ("layer:ambrette-pear-talc-membrane", "layer:musky-skin-echo"), ("fn:talc-cushion", "fn:musk-velvet"), "creamy low-frequency textile mass below the iris powder", direct),
        _compound_row(12, 6, "Romandolide", "Romandolide", "neat", 210, 1.0, ("layer:musky-skin-echo",), ("fn:musk-diffusion",), "restrained outward woody-musk shell", direct),
        _compound_row(13, 7, "Lavender EO High Altitude", "Lavender EO High Altitude (angustifolia, France)", "neat", 110, 1.0, ("layer:lavender-veil",), ("fn:lavender-entry",), "fine French aromatic veil", natural),
        _compound_row(14, 7, "Linalyl Acetate", "Linalyl Acetate", "neat", 70, 1.0, ("layer:lavender-veil", "layer:ambrette-pear-talc-membrane"), ("fn:lavender-entry", "fn:pear-glint"), "soft ester fold from lavender into pear skin and powder", direct),
        _compound_row(15, 7, "Linalool", "Linalool", "neat", 20, 1.0, ("layer:lavender-veil", "field:iris-air-seam"), ("fn:lavender-entry", "fn:negative-space"), "small floral-air continuation through the first handoff", direct),
        _compound_row(16, 9, "Mimosa Absolute", "Mimosa Absolute (10% in DPG)", "10% in DPG", 80, 0.10, ("layer:ambrette-pear-talc-membrane", "layer:orris-body"), ("fn:talc-cushion", "fn:orris-root"), "honeyed-green natural powder irregularity", diluted),
        _compound_row(17, 9, "Osmanthus Absolute", "Osmanthus Absolute (10% in DPG)", "10% in DPG", 20, 0.10, ("layer:ambrette-pear-talc-membrane", "layer:orris-body"), ("fn:pear-glint", "fn:iris-mobility"), "trace apricot-suede skin linking fruit and woody violet", diluted),
        _compound_row(18, 11, "Alpha Isomethyl Ionone (Methyl Ionone Pure)", "Alpha Isomethyl Ionone (Methyl Ionone Pure)", "neat", 420, 1.0, ("layer:orris-body",), ("fn:iris-object",), "powder and lipstick body", direct),
        _compound_row(19, 11, "Alpha Ionone", "Alpha Ionone", "neat", 180, 1.0, ("layer:ambrette-pear-talc-membrane", "layer:orris-body"), ("fn:iris-mobility", "fn:pear-glint"), "violet-iris motion receiving fruit and turning toward wood", direct),
        _compound_row(20, 11, "Alpha Irone", "Alpha Irone (10% w/w in DEP)", "10% w/w in DEP", 180, 0.10, ("layer:orris-body",), ("fn:orris-root",), "cool buttery rhizome specificity", diluted_w_w),
        _compound_row(21, 11, "Dihydro Beta Ionone", "Dihydro Beta Ionone", "neat", 100, 1.0, ("layer:orris-body", "layer:cedar-vetiver-counterform"), ("fn:iris-tail", "fn:wood-softening"), "sub-threshold structural darkening hypothesis at the iris-to-wood seam", direct),
        _compound_row(22, 11, "Irotyl", "Irotyl", "neat", 80, 1.0, ("layer:orris-body", "layer:musky-skin-echo"), ("fn:iris-tail",), "sub-threshold dry-grain hypothesis in the late iris", direct),
        _compound_row(23, 11, "Ultralia", "Ultralia", "neat", 60, 1.0, ("layer:orris-body", "layer:musky-skin-echo"), ("fn:iris-tail", "fn:skin-closure"), "sub-threshold iris-recurrence hypothesis in the textile drydown", direct),
        _compound_row(24, 11, "Orivone", "Orivone", "neat", 20, 1.0, ("layer:orris-body", "layer:amber-vanillic-shadow"), ("fn:orris-root", "fn:warm-shadow"), "fatty-warm orris seam", direct),
        _compound_row(25, 11, "Carrot Seed EO", "Carrot Seed EO", "neat", 10, 1.0, ("layer:orris-body", "layer:cedar-vetiver-counterform"), ("fn:orris-root", "fn:wood-softening"), "sub-threshold botanical-asymmetry hypothesis linking irone to vetiver", natural),
        _compound_row(26, 12, "Tonkarome", "Tonkarome (20% w/w in TEC)", "20% w/w in TEC", 310, 0.20, ("layer:amber-vanillic-shadow",), ("fn:coumarinic-shadow", "fn:warm-shadow"), "restrained hay-tonka warmth under iris", diluted_w_w),
        _compound_row(27, 12, "Isobutavan", "Isobutavan", "neat", 140, 1.0, ("layer:amber-vanillic-shadow", "layer:musky-skin-echo"), ("fn:vanillic-shadow", "fn:skin-closure"), "narrow buttery-vanillic seam from tonka into musk velvet", direct),
        _compound_row(28, 15, "Verdox", "Verdox", "neat", 340, 1.0, ("layer:ambrette-pear-talc-membrane", "layer:cedar-vetiver-counterform"), ("fn:pear-glint", "fn:wood-softening"), "green pear body with woody continuity", direct),
        _compound_row(29, 15, "Benzyl Acetate", "Benzyl Acetate", "neat", 160, 1.0, ("layer:ambrette-pear-talc-membrane", "layer:orris-body"), ("fn:pear-glint", "fn:iris-mobility"), "soft floral-fruit skin at the pear-to-orris boundary", direct),
        _compound_row(30, 15, "Ethyl 2-Methylbutyrate", "Ethyl 2-Methylbutyrate (0.1%)", "0.1% in DPG", 50, 0.001, ("layer:lavender-veil", "layer:ambrette-pear-talc-membrane"), ("fn:pear-glint",), "volatile juicy pear-liqueur flash", diluted),
    )


def _basket_checkpoints(
    rows: tuple[DHI2011CompoundRowV1, ...],
) -> tuple[DHI2011BasketCheckpointV1, ...]:
    """Render every physical basket, including explicit empty-basket skips."""

    running_total = 0.0
    checkpoints: list[DHI2011BasketCheckpointV1] = []
    for basket, label in BASKET_LABELS.items():
        basket_rows = tuple(row for row in rows if row.basket == basket)
        subtotal = sum(row.raw_ul for row in basket_rows)
        running_total += subtotal
        checkpoints.append(
            DHI2011BasketCheckpointV1(
                basket=basket,
                basket_label=label,
                action="COMPOUND" if basket_rows else "SKIP",
                row_steps=tuple(row.step for row in basket_rows),
                subtotal_ul=subtotal,
                running_total_ul=running_total,
            )
        )
    return tuple(checkpoints)


def _evidence_class(tier: DHI2011EvidenceTier) -> EvidenceClass:
    return {
        DHI2011EvidenceTier.CONFIRMED_MARKETING_ARCHITECTURE: EvidenceClass.OFFICIAL_RECORD,
        DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION: EvidenceClass.OFFICIAL_RECORD,
        DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT: EvidenceClass.HISTORICAL_PRIOR,
        DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION: EvidenceClass.HISTORICAL_PRIOR,
        DHI2011EvidenceTier.COLLECTOR_VERSION_EVIDENCE: EvidenceClass.HISTORICAL_PRIOR,
        DHI2011EvidenceTier.PERFUMER_INFERENCE: EvidenceClass.HEURISTIC,
        DHI2011EvidenceTier.COMMERCIAL_ANALYSIS_CLAIM_UNVERIFIED: EvidenceClass.UNKNOWN,
        DHI2011EvidenceTier.REFERENCE_SAMPLE_TEST_REQUIRED: EvidenceClass.UNKNOWN,
    }[tier]


def _provenance_refs(
    request: DHI2011ArchitectureRequestV1,
    resolution_id: str,
) -> tuple[ProvenanceRef, ...]:
    refs: list[ProvenanceRef] = [
        ProvenanceRef(
            provenance_id=f"dhi2011:architecture:{resolution_id}",
            source_ref=f"python://engine.perception.dhi_2011_architecture/{resolution_id}",
            evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
            independence_key="dhi2011-architecture-request-v1",
            source_sha256=request.record_sha256,
        )
    ]
    for evidence in request.evidence_claims:
        for index, source_ref in enumerate(evidence.source_refs):
            refs.append(
                ProvenanceRef(
                    provenance_id=f"dhi2011:{evidence.claim_id}:{index}",
                    source_ref=source_ref,
                    evidence_class=_evidence_class(evidence.tier),
                    independence_key=evidence.claim_id,
                    source_sha256=None,
                )
            )
    return tuple(refs)


def _resolution_specs() -> tuple[tuple[str, str], ...]:
    """Deep Plane layers are resolution levels, not note/perceptual layers."""

    return (
        (
            "deep:target-silhouette",
            "whole-target identity, version lock, invariants, and forbidden drift",
        ),
        (
            "deep:perceptual-layer-graph",
            "six artistic layers, one interstitial field, and convergent transitions",
        ),
        (
            "deep:material-role-geometry",
            "exact current-stock roles, dose hierarchy, ppm proxies, and takeover controls",
        ),
        (
            "deep:compounder-and-experiment-control",
            "basket-first raw-volume execution, no-invention rules, and controlled falsification",
        ),
    )


def _resolution_plane_claim_text(
    plane_id: PlaneId,
    resolution_id: str,
    focus: str,
    request: DHI2011ArchitectureRequestV1,
    rows: tuple[DHI2011CompoundRowV1, ...],
    commands: tuple[DHI2011LayerCommandV1, ...],
    field: DHI2011StructuralFieldV1,
) -> str:
    prefix = f"resolution={resolution_id}; focus={focus}; "
    values = {
        PlaneId.IDENTITY: (
            f"target={request.target.target_identity}; version={request.target.formula_code_scope}; "
            f"recognizers={' | '.join(item.required_recognizer for item in commands)}; "
            f"forbidden={' | '.join(request.target.forbidden_drift)}"
        ),
        PlaneId.MORPHOLOGY: (
            "artistic layers="
            + "; ".join(
                f"{item.layer_id} ({item.display_name}) "
                f"[{','.join(item.phase_presence)}] {item.texture}"
                for item in commands
            )
            + f"; structural field={field.field_id} ({field.spatial_role})"
        ),
        PlaneId.FUNCTION: (
            "owned functions="
            + "; ".join(
                f"{item.layer_id}:{','.join(item.owned_function_ids)}; omission={item.omission_loss}"
                for item in commands
            )
        ),
        PlaneId.RELATION: (
            "transitions="
            + "; ".join(
                f"{item.transition_id}:{item.source_layer_id}->{item.target_layer_id}:{item.intended_effect}"
                for item in request.transitions
            )
            + f"; convergent closure reaches layer:musky-skin-echo from both membrane and wood; cross-layer field={field.field_id}"
        ),
        PlaneId.MIXTURE: (
            "raw-stock roles="
            + "; ".join(
                f"step {item.step} {item.engine_material} {item.raw_ul:g} uL ({item.role})"
                for item in rows
            )
            + "; ingredient count earns no complexity credit"
        ),
        PlaneId.TEMPORAL: (
            f"required windows={','.join(request.time_windows)}; layer presence="
            + "; ".join(
                f"{item.layer_id}:{','.join(item.phase_presence)}" for item in commands
            )
            + "; exact handoff times are predicted, not observed"
        ),
        PlaneId.SPATIAL_COMPOSITION: (
            "positions="
            + "; ".join(f"{item.layer_id}:{item.spatial_role}" for item in commands)
            + f"; Iris Air Seam={field.spatial_role}; foreground, membrane, rear frame, and skin echo must remain distinguishable"
        ),
        PlaneId.PHYSICOCHEMICAL: (
            "nominal active ppm roles="
            + "; ".join(
                f"{item.engine_material}={item.active_ppm_in_concentrate:.4f}"
                for item in rows
            )
            + "; OAV and volatility are screening diagnostics, never perceived contribution"
        ),
        PlaneId.BIOLOGICAL_SENSITIVITY: (
            "adaptation, mixture masking, ionone and musk anosmia, individual sensitivity, and skin transformation "
            "remain assessor-specific unknowns"
        ),
        PlaneId.HEDONIC: (
            "identity, target fidelity, layer depth, richness, liking, projection, and defects remain separate endpoints"
        ),
        PlaneId.INVENTORY_BUILD: (
            "exact raw-volume rows="
            + "; ".join(
                f"{item.physical_stock_label}={item.raw_ul:g} uL [{item.analytical_status}]"
                for item in rows
            )
        ),
        PlaneId.EVIDENCE_AUTHORITY: (
            f"tiers={','.join(item.value for item in DHI2011EvidenceTier)}; "
            f"statuses={','.join(item.value for item in DHI2011ClaimStatus)}; "
            f"ceiling={request.target.claim_ceiling}"
        ),
        PlaneId.EXPERIMENT: (
            f"falsification probes={','.join(item.probe_id for item in request.controlled_probes)}; "
            "all changes require constant-total, carrier-matched arms and separate endpoints"
        ),
    }
    return prefix + values[plane_id]


def _claim_kind(plane_id: PlaneId) -> ClaimKind:
    if plane_id in {
        PlaneId.IDENTITY,
        PlaneId.MORPHOLOGY,
        PlaneId.FUNCTION,
        PlaneId.TEMPORAL,
        PlaneId.SPATIAL_COMPOSITION,
        PlaneId.EXPERIMENT,
    }:
        return ClaimKind.REQUIREMENT
    if plane_id in {PlaneId.INVENTORY_BUILD, PlaneId.EVIDENCE_AUTHORITY}:
        return ClaimKind.DIAGNOSTIC
    return ClaimKind.HYPOTHESIS


def _unknown(plane_id: PlaneId, layer_id: str, provenance: ProvenanceRef) -> UnknownFact:
    reason, needed = {
        PlaneId.IDENTITY: ("exact 05443/A molecular identity is not public", "authenticated analytical evidence from a documented 05443/A sample"),
        PlaneId.MORPHOLOGY: ("the proposed internal anatomy has not been observed", "coded descriptive comparison against a documented reference"),
        PlaneId.FUNCTION: ("causal layer ownership is predicted", "controlled omission with total and carrier held"),
        PlaneId.RELATION: ("layer-to-layer mediation has not been observed", "time-resolved relational ratings and omission controls"),
        PlaneId.MIXTURE: ("current material geometry is a design hypothesis", "constant-total dose and substitution frontiers"),
        PlaneId.TEMPORAL: ("exact handoff times are predicted", "repeated time-resolved reference comparison"),
        PlaneId.SPATIAL_COMPOSITION: ("foreground and sillage geometry are predicted", "standardized near/far-field observation"),
        PlaneId.PHYSICOCHEMICAL: ("stock densities and the complete carrier matrix are incomplete", "measured densities, assays, and matrix composition"),
        PlaneId.BIOLOGICAL_SENSITIVITY: ("adaptation and anosmia vary by assessor", "screened assessors and repeated controls"),
        PlaneId.HEDONIC: ("liking and target fidelity have not been measured", "blinded separate-endpoint evaluation"),
        PlaneId.INVENTORY_BUILD: ("raw volumes are exact but some active masses are nominal", "stock-basis and density measurements"),
        PlaneId.EVIDENCE_AUTHORITY: ("lineage evidence does not reveal exact proportions", "qualified primary analytical or archival evidence"),
        PlaneId.EXPERIMENT: ("the controlled probes have not been run", "recorded randomized and counterbalanced trial results"),
    }[plane_id]
    return UnknownFact(
        unknown_id=f"unknown:{layer_id}:{plane_id.value}",
        field_key=f"{layer_id}.{plane_id.value}.evidence_gap",
        reason=reason,
        needed_evidence=needed,
        provenance_refs=(provenance,),
    )


def _plane_conflicts(
    plane_id: PlaneId,
    resolution_id: str,
    claim_id: str,
    provenance: ProvenanceRef,
) -> tuple[PlaneConflict, ...]:
    if plane_id is PlaneId.EVIDENCE_AUTHORITY:
        return (
            PlaneConflict(
                conflict_id=f"conflict:{resolution_id}:version-evidence",
                claim_key=f"{resolution_id}.evidence_scope",
                alternatives=("DHI lineage continuity", "exact 05443/A applicability"),
                reason="lineage evidence cannot be silently promoted to exact-version quantitative truth",
                claim_ids=(claim_id,),
                provenance_refs=(provenance,),
            ),
        )
    if plane_id is PlaneId.INVENTORY_BUILD:
        return (
            PlaneConflict(
                conflict_id=f"conflict:{resolution_id}:raw-versus-mass",
                claim_key=f"{resolution_id}.build_completeness",
                alternatives=("exact raw-stock-volume delivery", "exact active-mass and carrier accounting"),
                reason="the base recipe is reproducible by raw volume while several analytical mass conversions remain unresolved",
                claim_ids=(claim_id,),
                provenance_refs=(provenance,),
            ),
        )
    if plane_id is PlaneId.RELATION:
        return (
            PlaneConflict(
                conflict_id=f"conflict:{resolution_id}:relation-outcome",
                claim_key=f"{resolution_id}.relation_outcome",
                alternatives=("integrated target-linked relation", "independently named note or collapsed block"),
                reason="the modeled relation has not yet been distinguished by controlled smelling",
                claim_ids=(claim_id,),
                provenance_refs=(provenance,),
            ),
        )
    return ()


def _plane_assessment(
    plane_id: PlaneId,
    resolution_id: str,
    focus: str,
    request: DHI2011ArchitectureRequestV1,
    rows: tuple[DHI2011CompoundRowV1, ...],
    commands: tuple[DHI2011LayerCommandV1, ...],
    rows_sha256: str,
    field: DHI2011StructuralFieldV1,
) -> PlaneAssessment:
    provenance_refs = _provenance_refs(request, resolution_id)
    computational_ref = provenance_refs[0]
    claim_id = f"claim:{resolution_id}:{plane_id.value}"
    claim = ScopedClaim(
        claim_id=claim_id,
        claim_key=f"dhi2011.{resolution_id}.{plane_id.value}",
        claim_value=_resolution_plane_claim_text(
            plane_id,
            resolution_id,
            focus,
            request,
            rows,
            commands,
            field,
        ),
        claim_kind=_claim_kind(plane_id),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=provenance_refs,
    )
    criterion = ParetoCriterion(
        criterion_id=f"{resolution_id}:{plane_id.value}:target-linkage",
        direction=CriterionDirection.PRESERVE,
        value=CriterionValue.unknown(
            "no controlled reference result exists for this layer-plane criterion"
        ),
        unit="separate target-linked criterion",
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(computational_ref,),
    )
    transition_failures = tuple(
        f"{item.transition_id}: omission={item.omission_failure}; overdose={item.overdose_failure}"
        for item in request.transitions
    )
    layer_failures = tuple(item.takeover_condition for item in commands)
    return PlaneAssessment(
        assessment_id=f"assessment:{resolution_id}:{plane_id.value}",
        module_id="dhi2011-deep-plane-adapter-v1",
        plane_id=plane_id,
        scope=AssessmentScope(
            target_scope=request.target.target_id,
            temporal_scope="opening_0s-to-drydown_4h",
            matrix_scope="dhi-11-velours-d-iris:6000ul-raw:30ml-nominal",
        ),
        claims=(claim,),
        support_intervals=(),
        conflicts=_plane_conflicts(plane_id, resolution_id, claim_id, computational_ref),
        unknowns=(_unknown(plane_id, resolution_id, computational_ref),),
        failure_modes=(*layer_failures, *transition_failures),
        proposed_experiments=tuple(item.probe_id for item in request.controlled_probes),
        provenance_refs=provenance_refs,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=(request.record_sha256, rows_sha256),
        native_criteria=(criterion,),
    )


def build_dhi_2011_deep_plane_request(
    architecture_request: DHI2011ArchitectureRequestV1,
    *,
    rows: tuple[DHI2011CompoundRowV1, ...] | None = None,
    layer_commands: tuple[DHI2011LayerCommandV1, ...] | None = None,
    structural_field: DHI2011StructuralFieldV1 | None = None,
) -> DeepPlaneRuntimeRequest:
    """Map the target graph onto four recursive thirteen-plane resolutions."""

    build_rows = _compound_rows() if rows is None else tuple(rows)
    commands = _layer_commands(architecture_request) if layer_commands is None else tuple(layer_commands)
    field = _structural_field() if structural_field is None else structural_field
    rows_sha256 = stable_json_hash([item.as_dict() for item in build_rows])
    layers: list[DeepPlaneLayerRequest] = []
    for depth, (resolution_id, focus) in enumerate(_resolution_specs()):
        layers.append(
            DeepPlaneLayerRequest(
                layer_id=resolution_id,
                depth=depth,
                parent_layer_id=(
                    None if depth == 0 else _resolution_specs()[depth - 1][0]
                ),
                assessments=tuple(
                    _plane_assessment(
                        plane_id,
                        resolution_id,
                        focus,
                        architecture_request,
                        build_rows,
                        commands,
                        rows_sha256,
                        field,
                    )
                    for plane_id in PlaneId
                ),
            )
        )
    return DeepPlaneRuntimeRequest(layers=tuple(layers))


def build_dhi_2011_compounder_command(
    architecture_request: DHI2011ArchitectureRequestV1,
    deep_plane_request: DeepPlaneRuntimeRequest,
    *,
    rows: tuple[DHI2011CompoundRowV1, ...] | None = None,
    layer_commands: tuple[DHI2011LayerCommandV1, ...] | None = None,
    structural_field: DHI2011StructuralFieldV1 | None = None,
) -> DHI2011CompounderCommandV1:
    """Build the exact no-invention handoff separate from runtime authority."""

    build_rows = _compound_rows() if rows is None else tuple(rows)
    commands = _layer_commands(architecture_request) if layer_commands is None else tuple(layer_commands)
    field = _structural_field() if structural_field is None else structural_field
    rows_sha256 = stable_json_hash([item.as_dict() for item in build_rows])
    return DHI2011CompounderCommandV1(
        command_id="command:dhi-2011-05443a:velours-d-iris:smooth-successor:raw-volume:v3",
        mode="EXPLORATORY_RAW_VOLUME_BUILD",
        target_id=architecture_request.target.target_id,
        architecture_request_sha256=architecture_request.record_sha256,
        deep_plane_request_sha256=deep_plane_request.content_sha256,
        formula_binding_ref=architecture_request.formula_binding_ref,
        formula_rows_sha256=rows_sha256,
        immediate_parent_ref=PARENT_FORMULA_REF,
        parent_semantics="constant-total 6000 uL successor to the rejected 14-row control; stock-basis labels remain bound and all active-dose changes are intentional architecture changes",
        raw_concentrate_ul=CONCENTRATE_UL,
        ethanol_96_addition_ul=ETHANOL_96_ADDITION_UL,
        nominal_finished_ul=NOMINAL_FINISHED_UL,
        finish_convention="positive addition: compound exactly 6000 uL raw stock, then add exactly 24000 uL ethanol 96 percent; 30000 uL is nominal and is not a q.s.-to-volume instruction",
        rows=build_rows,
        basket_checkpoints=_basket_checkpoints(build_rows),
        layer_commands=commands,
        structural_fields=(field,),
        artistic_layer_order=tuple(item.layer_id for item in commands),
        model_instructions=(
            "Read the target recognizers, forbidden drifts, all six layer commands, every transition, and the Iris Air Seam before touching the row list.",
            "Compound the base candidate exactly in step order; verify each of the seventeen basket checkpoints, including explicit SKIP rows, before moving upward.",
            "Use physical_stock_label to select the bottle and engine_material only for parser or model lookup; never silently substitute a neighboring stock.",
            "Dose raw_ul from the labeled stock, use a fresh tip for every material, and record actual delivered volume and any deviation.",
            "Do not add, optimize, rebalance, or activate a controlled variant while compounding this successor command.",
            "Judge smoothness and endpoint legibility separately: a muddy blend or an erased endpoint is not a successful seam.",
            "If an exact labeled stock is absent, heterogeneous, or physically unusable, stop that row and report it rather than inventing an equivalence.",
            "Add exactly 24000 uL ethanol 96 percent after the concentrate; do not top up to an assumed final volume.",
            "Keep target fidelity, liking, depth, projection, defects, safety, stability, and similarity as separate unobserved outcomes.",
            "Treat ppm, ODT, OAV, volatility, and the Deep Plane receipt as diagnostics; none is percent perceived contribution or a sensory pass.",
        ),
        unresolved_facts=(
            "Ambrettolide is confirmed as 10 percent w/w in DPG; stock-solution density is unavailable, so its 160 active-uL value remains a numerical screening proxy rather than literal active volume.",
            "Alpha Irone and Tonkarome are w/w stocks dosed by raw volume without measured stock density; active-uL and active-ppm remain nominal proxies.",
            "Mimosa Absolute, Osmanthus Absolute, and Ethyl 2-Methylbutyrate use declared DPG working stocks whose active-volume values are screening proxies.",
            "Natural lots are not batch-characterized, and the current vetiver is the live physical label Indian Vetiver EO volume grade mapped to engine identity Vetiver EO India.",
            "The complete embedded DPG, DEP, and TEC mass and volume matrix is not analytically closed.",
            "No authenticated quantitative 05443/A formula, controlled reference similarity result, or measured physical-performance result exists.",
            "Safety, IFRA, stability, and skin-use release remain separate decisions outside this structural handoff.",
        ),
    )


def build_default_dhi_2011_deep_plane_program() -> DHI2011DeepPlaneProgramV1:
    """Build and execute the complete deterministic DHI Deep Plane handoff."""

    architecture_request, architecture_result = build_default_dhi_2011_architecture()
    rows = _compound_rows()
    commands = _layer_commands(architecture_request)
    field = _structural_field()
    deep_request = build_dhi_2011_deep_plane_request(
        architecture_request,
        rows=rows,
        layer_commands=commands,
        structural_field=field,
    )
    deep_receipt = execute_deep_plane_runtime_candidate(deep_request)
    command = build_dhi_2011_compounder_command(
        architecture_request,
        deep_request,
        rows=rows,
        layer_commands=commands,
        structural_field=field,
    )
    return DHI2011DeepPlaneProgramV1(
        architecture_request=architecture_request,
        architecture_result=architecture_result,
        deep_plane_request=deep_request,
        deep_plane_receipt=deep_receipt,
        compounder_command=command,
    )


__all__ = [
    "BASKET_LABELS",
    "CONCENTRATE_UL",
    "DHI2011BasketCheckpointV1",
    "DHI2011ClaimStatus",
    "DHI2011CompoundRowV1",
    "DHI2011CompounderCommandV1",
    "DHI2011DeepPlaneProgramV1",
    "DHI2011LayerCommandV1",
    "DHI2011StructuralFieldV1",
    "ETHANOL_96_ADDITION_UL",
    "NOMINAL_FINISHED_UL",
    "build_default_dhi_2011_deep_plane_program",
    "build_dhi_2011_compounder_command",
    "build_dhi_2011_deep_plane_request",
]
