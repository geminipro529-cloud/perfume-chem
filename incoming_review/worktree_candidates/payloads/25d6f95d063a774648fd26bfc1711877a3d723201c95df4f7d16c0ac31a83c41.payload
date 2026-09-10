"""Constraint-based synthesis across Perfume-Chem design and evidence modules.

This module is deliberately not an ensemble vote.  Repeated compatible claims
are collapsed to one scoped claim with provenance; incompatible claims at the
same scope remain an explicit tension no matter how many modules repeat either
side.  Target identity, current-stock capability, computational architecture,
observed temporal evidence, and criterion-scoped preference evidence retain
their own namespaces and authority ceilings.

The result is an experiment-design receipt.  It never proves perception,
liking, similarity, safety, stability, physical performance, or release, and
it never authorizes formula mutation, preparation, purchase, or compounding.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, Iterable

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.material_capability_atlas import (
    MaterialCapabilityAtlas,
    MaterialCapabilityRecord,
)


class HarmonicSynthesisState(str, Enum):
    DESIGN_READY = "DESIGN_READY"
    NO_CHANGE = "NO_CHANGE"
    HOLD = "HOLD"


class HarmonicModuleState(str, Enum):
    READY = "READY"
    WITHHELD = "WITHHELD"
    HOLD = "HOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class HarmonicAssertionKind(str, Enum):
    REQUIREMENT = "REQUIREMENT"
    PROHIBITION = "PROHIBITION"
    CAPABILITY = "CAPABILITY"
    OBSERVATION = "OBSERVATION"
    DESIGN_HYPOTHESIS = "DESIGN_HYPOTHESIS"


class HarmonicEvidenceState(str, Enum):
    TARGET_CONTRACT = "TARGET_CONTRACT"
    CURRENT_INVENTORY = "CURRENT_INVENTORY"
    COMPUTATIONAL_DESIGN = "COMPUTATIONAL_DESIGN"
    OBSERVED = "OBSERVED"
    WITHHELD = "WITHHELD"


class HarmonicMaterialState(str, Enum):
    CURRENT_READY = "CURRENT_READY"
    CURRENT_HOLD = "CURRENT_HOLD"
    IDEAL_AVAILABLE = "IDEAL_AVAILABLE"
    IDEAL_ONLY_GAP = "IDEAL_ONLY_GAP"
    OPTIONAL_AVAILABLE = "OPTIONAL_AVAILABLE"
    OPTIONAL_UNAVAILABLE = "OPTIONAL_UNAVAILABLE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(
    values: Iterable[str],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _sha256(value: object, field_name: str) -> str:
    normalized = _text(value, field_name).casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a SHA-256 hexadecimal digest")
    return normalized


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
    SCHEMA_VERSION: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _json_value(getattr(self, item.name)) for item in fields(self)},
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class HarmonicTargetContractV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_target_contract_v1"

    target_id: str
    target_identity: str
    primary_subject: str
    supporting_subjects: tuple[str, ...]
    positive_invariants: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    ideal_formula_ref: str
    current_inventory_build_ref: str
    claim_ceiling: str

    def __post_init__(self) -> None:
        for field_name in (
            "target_id",
            "target_identity",
            "primary_subject",
            "ideal_formula_ref",
            "current_inventory_build_ref",
            "claim_ceiling",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "supporting_subjects",
            _text_tuple(
                self.supporting_subjects,
                "supporting_subjects",
                allow_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "positive_invariants",
            _text_tuple(self.positive_invariants, "positive_invariants"),
        )
        object.__setattr__(
            self,
            "forbidden_drift",
            _text_tuple(self.forbidden_drift, "forbidden_drift"),
        )
        if self.ideal_formula_ref == self.current_inventory_build_ref:
            raise ValueError(
                "TARGET/IDEAL and CURRENT-INVENTORY references must remain distinct"
            )
        ceiling = self.claim_ceiling.casefold()
        forbidden = ("sensory_confirmed", "hedonic_validated", "release_ready")
        if any(value in ceiling for value in forbidden):
            raise ValueError("claim_ceiling exceeds computational design authority")


@dataclass(frozen=True, slots=True)
class HarmonicAssertionV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_assertion_v1"

    assertion_id: str
    module_id: str
    scope_key: str
    claim_key: str
    claim_value: str
    kind: HarmonicAssertionKind
    evidence_state: HarmonicEvidenceState
    rationale: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "assertion_id",
            "module_id",
            "scope_key",
            "claim_key",
            "claim_value",
            "rationale",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        object.__setattr__(self, "kind", HarmonicAssertionKind(self.kind))
        object.__setattr__(
            self,
            "evidence_state",
            HarmonicEvidenceState(self.evidence_state),
        )
        object.__setattr__(
            self,
            "source_refs",
            _text_tuple(self.source_refs, "source_refs"),
        )


@dataclass(frozen=True, slots=True)
class HarmonicModuleReportV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_module_report_v1"

    module_id: str
    module_sha256: str
    state: HarmonicModuleState
    assertions: tuple[HarmonicAssertionV1, ...]
    blockers: tuple[str, ...]
    next_action: str
    authority_flags: tuple[tuple[str, bool], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _text(self.module_id, "module_id"))
        object.__setattr__(
            self,
            "module_sha256",
            _sha256(self.module_sha256, "module_sha256"),
        )
        object.__setattr__(self, "state", HarmonicModuleState(self.state))
        assertions = tuple(self.assertions)
        if any(not isinstance(value, HarmonicAssertionV1) for value in assertions):
            raise TypeError("assertions must contain HarmonicAssertionV1 values")
        assertion_ids = tuple(value.assertion_id for value in assertions)
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion IDs must be unique within a module report")
        if any(value.module_id != self.module_id for value in assertions):
            raise ValueError("assertion module_id must match its module report")
        object.__setattr__(self, "assertions", assertions)
        object.__setattr__(
            self,
            "blockers",
            _text_tuple(self.blockers, "blockers", allow_empty=True),
        )
        object.__setattr__(
            self,
            "next_action",
            _text(self.next_action, "next_action"),
        )
        flags = tuple(self.authority_flags)
        names: list[str] = []
        for name, value in flags:
            normalized = _text(name, "authority flag name")
            if not isinstance(value, bool):
                raise TypeError("authority flag values must be boolean")
            if value:
                raise ValueError(
                    f"module report may not grant authority through {normalized}"
                )
            names.append(normalized)
        if len(names) != len(set(names)):
            raise ValueError("authority flag names must be unique")
        object.__setattr__(
            self,
            "authority_flags",
            tuple((name, value) for name, (_, value) in zip(names, flags, strict=True)),
        )


@dataclass(frozen=True, slots=True)
class HarmonicRelationV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_relation_v1"

    relation_id: str
    source_node: str
    target_node: str
    relation_kind: str
    target_link: str
    omission_loss: str
    failure_mode: str
    temporal_windows: tuple[str, ...]
    probe_ref: str
    module_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "relation_id",
            "source_node",
            "target_node",
            "relation_kind",
            "target_link",
            "omission_loss",
            "failure_mode",
            "probe_ref",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        if self.source_node == self.target_node:
            raise ValueError("a harmonic relation must connect distinct nodes")
        object.__setattr__(
            self,
            "temporal_windows",
            _text_tuple(self.temporal_windows, "temporal_windows"),
        )
        object.__setattr__(
            self,
            "module_ids",
            _text_tuple(self.module_ids, "module_ids"),
        )


@dataclass(frozen=True, slots=True)
class HarmonicMaterialIntentV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_material_intent_v1"

    intent_id: str
    material_name: str
    role_id: str
    target_function: str
    ideal_required: bool
    current_build_intent: bool
    quantitative_required: bool
    omission_loss: str
    failure_mode: str

    def __post_init__(self) -> None:
        for field_name in (
            "intent_id",
            "material_name",
            "role_id",
            "target_function",
            "omission_loss",
            "failure_mode",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name),
            )
        for field_name in (
            "ideal_required",
            "current_build_intent",
            "quantitative_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be boolean")


@dataclass(frozen=True, slots=True)
class HarmonicResolvedClaimV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_resolved_claim_v1"

    scope_key: str
    claim_key: str
    claim_value: str
    assertion_kind: HarmonicAssertionKind
    evidence_states: tuple[HarmonicEvidenceState, ...]
    supporting_module_ids: tuple[str, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HarmonicTensionV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_tension_v1"

    scope_key: str
    claim_key: str
    incompatible_values: tuple[str, ...]
    module_ids: tuple[str, ...]
    required_resolution: str


@dataclass(frozen=True, slots=True)
class HarmonicMaterialDispositionV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_material_disposition_v1"

    intent_id: str
    material_name: str
    canonical_name: str
    role_id: str
    state: HarmonicMaterialState
    inventory_state: str
    knowledge_state: str
    qualitative_selectable: bool
    quantitative_execution_ready: bool
    blockers: tuple[str, ...]
    atlas_conflicts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HarmonicSynthesisRequestV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_synthesis_request_v1"

    target: HarmonicTargetContractV1
    required_module_ids: tuple[str, ...]
    design_gate_module_ids: tuple[str, ...]
    module_reports: tuple[HarmonicModuleReportV1, ...]
    relations: tuple[HarmonicRelationV1, ...]
    material_intents: tuple[HarmonicMaterialIntentV1, ...]
    no_change_reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.target, HarmonicTargetContractV1):
            raise TypeError("target must be a HarmonicTargetContractV1")
        required = _text_tuple(self.required_module_ids, "required_module_ids")
        design_gates = _text_tuple(
            self.design_gate_module_ids,
            "design_gate_module_ids",
            allow_empty=True,
        )
        if not set(design_gates).issubset(required):
            raise ValueError("design_gate_module_ids must be required modules")
        object.__setattr__(self, "required_module_ids", required)
        object.__setattr__(self, "design_gate_module_ids", design_gates)
        reports = tuple(self.module_reports)
        if any(not isinstance(value, HarmonicModuleReportV1) for value in reports):
            raise TypeError("module_reports must contain HarmonicModuleReportV1 values")
        report_ids = tuple(value.module_id for value in reports)
        if len(report_ids) != len(set(report_ids)):
            raise ValueError("module report IDs must be unique")
        object.__setattr__(self, "module_reports", reports)
        relations = tuple(self.relations)
        if any(not isinstance(value, HarmonicRelationV1) for value in relations):
            raise TypeError("relations must contain HarmonicRelationV1 values")
        relation_ids = tuple(value.relation_id for value in relations)
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("relation IDs must be unique")
        object.__setattr__(self, "relations", relations)
        intents = tuple(self.material_intents)
        if any(not isinstance(value, HarmonicMaterialIntentV1) for value in intents):
            raise TypeError(
                "material_intents must contain HarmonicMaterialIntentV1 values"
            )
        intent_ids = tuple(value.intent_id for value in intents)
        if len(intent_ids) != len(set(intent_ids)):
            raise ValueError("material intent IDs must be unique")
        object.__setattr__(self, "material_intents", intents)
        object.__setattr__(
            self,
            "no_change_reason",
            _text(self.no_change_reason, "no_change_reason"),
        )


@dataclass(frozen=True, slots=True)
class HarmonicSynthesisResultV1(_CanonicalRecord):
    SCHEMA_VERSION = "harmonic_synthesis_result_v1"

    state: HarmonicSynthesisState
    target: HarmonicTargetContractV1
    request_sha256: str
    resolved_claims: tuple[HarmonicResolvedClaimV1, ...]
    tensions: tuple[HarmonicTensionV1, ...]
    retained_relations: tuple[HarmonicRelationV1, ...]
    material_dispositions: tuple[HarmonicMaterialDispositionV1, ...]
    structural_blockers: tuple[str, ...]
    empirical_gaps: tuple[str, ...]
    next_comparison: str | None
    claim_ceiling: str
    vote_counting_used: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    @property
    def synthesis_sha256(self) -> str:
        return self.record_sha256


def _resolved_claims(
    reports: tuple[HarmonicModuleReportV1, ...],
) -> tuple[tuple[HarmonicResolvedClaimV1, ...], tuple[HarmonicTensionV1, ...]]:
    grouped: dict[tuple[str, str], list[HarmonicAssertionV1]] = {}
    for report in reports:
        if report.state is not HarmonicModuleState.READY:
            continue
        for assertion in report.assertions:
            if assertion.evidence_state is HarmonicEvidenceState.WITHHELD:
                continue
            grouped.setdefault((assertion.scope_key, assertion.claim_key), []).append(
                assertion
            )

    resolved: list[HarmonicResolvedClaimV1] = []
    tensions: list[HarmonicTensionV1] = []
    for (scope_key, claim_key), assertions in sorted(grouped.items()):
        values = tuple(sorted({item.claim_value for item in assertions}))
        module_ids = tuple(sorted({item.module_id for item in assertions}))
        if len(values) != 1:
            tensions.append(
                HarmonicTensionV1(
                    scope_key=scope_key,
                    claim_key=claim_key,
                    incompatible_values=values,
                    module_ids=module_ids,
                    required_resolution=(
                        "preserve all exact-scope alternatives and run a target-linked "
                        "controlled comparison; repetition is not a vote"
                    ),
                )
            )
            continue
        kinds = tuple(sorted({item.kind for item in assertions}, key=lambda item: item.value))
        if len(kinds) != 1:
            tensions.append(
                HarmonicTensionV1(
                    scope_key=scope_key,
                    claim_key=claim_key,
                    incompatible_values=tuple(item.value for item in kinds),
                    module_ids=module_ids,
                    required_resolution=(
                        "claim kind conflict requires exact-scope reconciliation before use"
                    ),
                )
            )
            continue
        evidence_states = tuple(
            sorted(
                {item.evidence_state for item in assertions},
                key=lambda item: item.value,
            )
        )
        source_refs = tuple(
            sorted({ref for assertion in assertions for ref in assertion.source_refs})
        )
        resolved.append(
            HarmonicResolvedClaimV1(
                scope_key=scope_key,
                claim_key=claim_key,
                claim_value=values[0],
                assertion_kind=kinds[0],
                evidence_states=evidence_states,
                supporting_module_ids=module_ids,
                source_refs=source_refs,
            )
        )
    return tuple(resolved), tuple(tensions)


def _material_state(
    intent: HarmonicMaterialIntentV1,
    record: MaterialCapabilityRecord,
) -> HarmonicMaterialState:
    if intent.current_build_intent:
        ready = (
            record.quantitative_execution_ready
            if intent.quantitative_required
            else record.qualitative_selectable
        )
        return (
            HarmonicMaterialState.CURRENT_READY
            if ready
            else HarmonicMaterialState.CURRENT_HOLD
        )
    if intent.ideal_required:
        return (
            HarmonicMaterialState.IDEAL_AVAILABLE
            if record.qualitative_selectable
            else HarmonicMaterialState.IDEAL_ONLY_GAP
        )
    return (
        HarmonicMaterialState.OPTIONAL_AVAILABLE
        if record.qualitative_selectable
        else HarmonicMaterialState.OPTIONAL_UNAVAILABLE
    )


def _material_disposition(
    intent: HarmonicMaterialIntentV1,
    atlas: MaterialCapabilityAtlas,
) -> HarmonicMaterialDispositionV1:
    record = atlas.project(intent.material_name)
    state = _material_state(intent, record)
    blockers = list(record.blockers)
    if state is HarmonicMaterialState.CURRENT_HOLD:
        required = "quantitative execution" if intent.quantitative_required else "selection"
        blockers.append(f"CURRENT_BUILD_REQUIRES_{required.upper().replace(' ', '_')}")
    conflicts = tuple(
        f"{item.field}:{item.prior_value}->{item.effective_value}:{item.resolution}"
        for item in record.conflicts
    )
    return HarmonicMaterialDispositionV1(
        intent_id=intent.intent_id,
        material_name=intent.material_name,
        canonical_name=record.canonical_name,
        role_id=intent.role_id,
        state=state,
        inventory_state=record.inventory_state.value,
        knowledge_state=record.knowledge_state.value,
        qualitative_selectable=record.qualitative_selectable,
        quantitative_execution_ready=record.quantitative_execution_ready,
        blockers=tuple(dict.fromkeys(blockers)),
        atlas_conflicts=conflicts,
    )


_AUTHORITY_FIELD_NAMES = (
    "empirical_authority",
    "formula_authority",
    "formula_mutation_authorized",
    "inventory_authority",
    "physical_execution_authorized",
    "compounding_authorized",
    "purchase_authority",
    "sensory_authority",
    "hedonic_authority",
    "liking_authority",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "release_authority",
)


def _authority_flags_from(*objects: object) -> tuple[tuple[str, bool], ...]:
    values: dict[str, bool] = {}
    for field_name in _AUTHORITY_FIELD_NAMES:
        observed = tuple(
            getattr(value, field_name)
            for value in objects
            if hasattr(value, field_name)
        )
        if not observed:
            continue
        if any(not isinstance(value, bool) for value in observed):
            raise TypeError(f"{field_name} authority field must be boolean")
        combined = any(observed)
        if combined:
            raise ValueError(
                f"harmonic adapter refuses source authority grant: {field_name}"
            )
        values[field_name] = False
    return tuple(sorted(values.items()))


def _payload_sha256(payload: dict[str, object]) -> str:
    return sha256_hex(canonical_json_bytes(payload))


def report_from_material_atlas(
    atlas: MaterialCapabilityAtlas,
    *,
    material_names: tuple[str, ...],
) -> HarmonicModuleReportV1:
    """Project stock and knowledge state without importing legacy beauty fields."""

    if not isinstance(atlas, MaterialCapabilityAtlas):
        raise TypeError("atlas must be a MaterialCapabilityAtlas")
    names = _text_tuple(material_names, "material_names")
    projected = tuple((name, atlas.project(name)) for name in names)
    refs = (
        f"inventory-text-sha256:{atlas.inventory_text_sha256}",
        f"v5-workbook-sha256:{atlas.v5_workbook_sha256}",
        f"v5-snapshot-sha256:{atlas.v5_snapshot_sha256}",
        f"user-overlay-sha256:{atlas.user_overlay_sha256}",
        f"material-data-fingerprint:{atlas.material_data_fingerprint}",
    )
    assertions: list[HarmonicAssertionV1] = []
    for requested_name, record in projected:
        values = (
            ("inventory_state", record.inventory_state.value),
            ("knowledge_state", record.knowledge_state.value),
            ("qualitative_selectable", str(record.qualitative_selectable).lower()),
            (
                "quantitative_execution_ready",
                str(record.quantitative_execution_ready).lower(),
            ),
        )
        for suffix, value in values:
            assertions.append(
                HarmonicAssertionV1(
                    assertion_id=f"atlas:{requested_name}:{suffix}",
                    module_id="material-capability-atlas",
                    scope_key=f"material:{record.identity_key}",
                    claim_key=f"material.{requested_name}.{suffix}",
                    claim_value=value,
                    kind=HarmonicAssertionKind.CAPABILITY,
                    evidence_state=HarmonicEvidenceState.CURRENT_INVENTORY,
                    rationale=(
                        "current-stock and field-provenance projection; no sensory or "
                        "hedonic inference"
                    ),
                    source_refs=refs,
                )
            )
    payload = {
        "inventory_text_sha256": atlas.inventory_text_sha256,
        "v5_workbook_sha256": atlas.v5_workbook_sha256,
        "v5_snapshot_sha256": atlas.v5_snapshot_sha256,
        "user_overlay_sha256": atlas.user_overlay_sha256,
        "material_data_fingerprint": atlas.material_data_fingerprint,
        "materials": [
            {
                "requested_name": name,
                "canonical_name": record.canonical_name,
                "inventory_state": record.inventory_state.value,
                "knowledge_state": record.knowledge_state.value,
                "qualitative_selectable": record.qualitative_selectable,
                "quantitative_execution_ready": record.quantitative_execution_ready,
                "blockers": list(record.blockers),
            }
            for name, record in projected
        ],
    }
    return HarmonicModuleReportV1(
        module_id="material-capability-atlas",
        module_sha256=_payload_sha256(payload),
        state=HarmonicModuleState.READY,
        assertions=tuple(assertions),
        blockers=(),
        next_action=(
            "bind only target-selected materials; resolve every current-build hold "
            "before quantitative dosing"
        ),
        authority_flags=(),
    )


def report_from_family_depth(
    profile: object,
    evaluation: object,
) -> HarmonicModuleReportV1:
    """Adapt a universal family-depth profile and its closed-design evaluation."""

    from engine.perception.depth_contracts import (
        DepthArchitectureProfileV1,
        DepthDesignState,
        DepthEvaluationResultV1,
    )

    if not isinstance(profile, DepthArchitectureProfileV1):
        raise TypeError("profile must be a DepthArchitectureProfileV1")
    if not isinstance(evaluation, DepthEvaluationResultV1):
        raise TypeError("evaluation must be a DepthEvaluationResultV1")
    if evaluation.profile_sha256 != profile.profile_sha256:
        raise ValueError("depth evaluation does not bind the supplied profile")
    state = (
        HarmonicModuleState.READY
        if evaluation.state is DepthDesignState.DESIGN_READY
        else HarmonicModuleState.NOT_APPLICABLE
        if evaluation.state is DepthDesignState.NOT_APPLICABLE
        else HarmonicModuleState.HOLD
    )
    scope_key = f"target:{profile.profile_id}"
    source_refs = tuple(profile.source_refs) or (
        f"depth-profile-sha256:{profile.profile_sha256}",
    )
    assertions = [
        HarmonicAssertionV1(
            assertion_id="family-depth:target-identity",
            module_id="family-depth",
            scope_key=scope_key,
            claim_key="target.identity",
            claim_value=profile.target_identity,
            kind=HarmonicAssertionKind.REQUIREMENT,
            evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
            rationale="target identity is locked before family adaptation",
            source_refs=source_refs,
        ),
        HarmonicAssertionV1(
            assertion_id="family-depth:family",
            module_id="family-depth",
            scope_key=scope_key,
            claim_key="target.family",
            claim_value=profile.family.value,
            kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
            evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
            rationale="family selects questions and controls, not a material recipe",
            source_refs=source_refs,
        ),
    ]
    for contract in profile.dimension_contracts:
        assertions.append(
            HarmonicAssertionV1(
                assertion_id=f"family-depth:{contract.dimension.value}",
                module_id="family-depth",
                scope_key=scope_key,
                claim_key=f"dimension.{contract.dimension.value}",
                claim_value=contract.target_definition,
                kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
                evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
                rationale=(
                    "dimension-specific target and falsification surface; ingredient "
                    "count supplies no sensory evidence"
                ),
                source_refs=tuple(contract.evidence_refs) or source_refs,
            )
        )
    blockers = tuple(evaluation.blockers)
    if state is HarmonicModuleState.HOLD and not blockers:
        blockers = tuple(evaluation.reason_codes)
    return HarmonicModuleReportV1(
        module_id="family-depth",
        module_sha256=profile.profile_sha256,
        state=state,
        assertions=tuple(assertions) if state is HarmonicModuleState.READY else (),
        blockers=blockers,
        next_action=(
            profile.probes[0].probe_id
            if profile.probes
            else "supply a closed target-linked family-depth probe"
        ),
        authority_flags=_authority_flags_from(profile, evaluation),
    )


def report_from_architecture_compiler(result: object) -> HarmonicModuleReportV1:
    """Adapt the relational architecture compiler without promoting its model output."""

    from engine.perception.architecture_compiler import ArchitectureCompileResult
    from engine.perception.architecture_contracts import ArchitectureCompilationState

    if not isinstance(result, ArchitectureCompileResult):
        raise TypeError("result must be an ArchitectureCompileResult")
    state = (
        HarmonicModuleState.HOLD
        if result.state is ArchitectureCompilationState.HOLD
        else HarmonicModuleState.READY
    )
    source_refs = (
        f"target-lock-sha256:{result.target_lock_sha256}",
        f"formula-lineage-sha256:{result.formula_lineage_sha256}",
        f"rule-registry-sha256:{result.rule_registry_sha256}",
        f"strategy-registry-sha256:{result.strategy_registry_sha256}",
    )
    assertions = (
        HarmonicAssertionV1(
            assertion_id="architecture-compiler:state",
            module_id="architecture-compiler",
            scope_key=f"target:{result.target_lock_sha256}",
            claim_key="architecture.state",
            claim_value=result.state.value,
            kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
            evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
            rationale="relational compiler state with no sensory or liking authority",
            source_refs=source_refs,
        ),
        HarmonicAssertionV1(
            assertion_id="architecture-compiler:primary-strategy",
            module_id="architecture-compiler",
            scope_key=f"target:{result.target_lock_sha256}",
            claim_key="architecture.primary_strategy",
            claim_value=result.primary_strategy.value,
            kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
            evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
            rationale="strategy owns functions but does not predict a liked perfume",
            source_refs=source_refs,
        ),
    )
    flags = tuple(sorted((str(key), bool(value)) for key, value in result.authority_flags.items()))
    return HarmonicModuleReportV1(
        module_id="architecture-compiler",
        module_sha256=result.compilation_sha256,
        state=state,
        assertions=assertions if state is HarmonicModuleState.READY else (),
        blockers=tuple(dict.fromkeys((*result.blockers, *result.current_build_blockers))),
        next_action=result.next_action,
        authority_flags=flags,
    )


def report_from_architectural_delta(result: object) -> HarmonicModuleReportV1:
    """Adapt zero-or-one architectural intervention selection."""

    from engine.perception.architectural_delta import (
        ArchitecturalDeltaResult,
        ArchitecturalDeltaState,
    )

    if not isinstance(result, ArchitecturalDeltaResult):
        raise TypeError("result must be an ArchitecturalDeltaResult")
    state = (
        HarmonicModuleState.HOLD
        if result.state is ArchitecturalDeltaState.HOLD
        else HarmonicModuleState.READY
    )
    source_refs = (
        f"formula-lineage-sha256:{result.formula_lineage_sha256}",
        f"inventory-workbook-sha256:{result.inventory_workbook_sha256}",
    )
    assertions: list[HarmonicAssertionV1] = [
        HarmonicAssertionV1(
            assertion_id="architectural-delta:state",
            module_id="architectural-delta",
            scope_key=f"target:{result.formula_lineage_sha256}",
            claim_key="architectural_delta.state",
            claim_value=result.state.value,
            kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
            evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
            rationale="zero-or-one target-linked intervention disposition",
            source_refs=source_refs,
        )
    ]
    if result.selected_candidate is not None:
        candidate = result.selected_candidate
        for suffix, value in (
            ("material", candidate.material),
            ("kind", candidate.kind.value),
            ("target_role", candidate.target_role),
        ):
            assertions.append(
                HarmonicAssertionV1(
                    assertion_id=f"architectural-delta:candidate:{suffix}",
                    module_id="architectural-delta",
                    scope_key=f"candidate:{candidate.candidate_id}",
                    claim_key=f"architectural_delta.candidate.{suffix}",
                    claim_value=value,
                    kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
                    evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
                    rationale=(
                        "selected intervention remains a controlled experiment, not a "
                        "formula mutation"
                    ),
                    source_refs=tuple(candidate.evidence_refs) or source_refs,
                )
            )
    payload = {
        "state": result.state.value,
        "target_identity": result.target_identity,
        "ideal_formula_ref": result.ideal_formula_ref,
        "current_build_ref": result.current_build_ref,
        "formula_lineage_sha256": result.formula_lineage_sha256,
        "inventory_workbook_sha256": result.inventory_workbook_sha256,
        "inventory_source_row_count": result.inventory_source_row_count,
        "selected_candidate_id": (
            result.selected_candidate.candidate_id
            if result.selected_candidate is not None
            else None
        ),
        "controlled_arms": list(result.controlled_arms),
        "blockers": list(result.blockers),
        "next_comparison": result.next_comparison,
    }
    return HarmonicModuleReportV1(
        module_id="architectural-delta",
        module_sha256=_payload_sha256(payload),
        state=state,
        assertions=tuple(assertions) if state is HarmonicModuleState.READY else (),
        blockers=tuple(result.blockers),
        next_action=(
            result.next_comparison
            or "retain the current architecture; no extra material count is rewarded"
        ),
        authority_flags=_authority_flags_from(result),
    )


def report_from_cypress_heart_frontier(result: object) -> HarmonicModuleReportV1:
    """Adapt the Cypress-native Pareto frontier without inventing a winner.

    Only a uniquely theory-selected, inventory-eligible candidate becomes a
    ready design report.  An equal/non-dominated frontier remains a design
    HOLD so that the harmonic engine cannot break the tie by module count,
    material count, alphabetical order, or an aggregate number.
    """

    from engine.perception.cypress_heart_frontier import (
        CypressHeartFrontierResultV1,
        CypressHeartFrontierState,
    )

    if not isinstance(result, CypressHeartFrontierResultV1):
        raise TypeError("result must be a CypressHeartFrontierResultV1")

    ready = (
        result.state is CypressHeartFrontierState.THEORY_SELECTED
        and result.selected_candidate is not None
    )
    state = HarmonicModuleState.READY if ready else HarmonicModuleState.HOLD
    assertions: list[HarmonicAssertionV1] = []
    if ready:
        candidate = result.selected_candidate
        assert candidate is not None
        source_refs = tuple(
            dict.fromkeys(
                ref
                for assessment in candidate.assessments
                for ref in assessment.evidence_refs
            )
        ) or (f"cypress-frontier-sha256:{result.record_sha256}",)
        scope_key = f"target:{result.target.target_id}"
        for assertion_id, claim_key, claim_value, rationale in (
            (
                "cypress-frontier:primary-subject",
                "target.primary_subject",
                result.target.primary_subject,
                "the named target subject is locked before heart selection",
            ),
            (
                "cypress-frontier:heart-identity",
                "heart.identity",
                candidate.heart_identity,
                "unique Pareto frontier member at the frozen computational scope",
            ),
            (
                "cypress-frontier:heart-relation",
                "heart.relation_to_cypress",
                candidate.relation_to_cypress,
                "relational heart contract keeps the floral system subordinate to Cypress",
            ),
            (
                "cypress-frontier:floral-subjects",
                "heart.floral_subjects",
                " | ".join(candidate.floral_subjects),
                "explicit floral registers prevent a generic undifferentiated heart",
            ),
        ):
            assertions.append(
                HarmonicAssertionV1(
                    assertion_id=assertion_id,
                    module_id="cypress-heart-frontier",
                    scope_key=scope_key,
                    claim_key=claim_key,
                    claim_value=claim_value,
                    kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
                    evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
                    rationale=rationale,
                    source_refs=source_refs,
                )
            )
        for assessment in candidate.assessments:
            assertions.append(
                HarmonicAssertionV1(
                    assertion_id=(
                        "cypress-frontier:criterion:"
                        f"{assessment.criterion.value.casefold()}"
                    ),
                    module_id="cypress-heart-frontier",
                    scope_key=scope_key,
                    claim_key=(
                        "heart.criterion."
                        f"{assessment.criterion.value}.support_level"
                    ),
                    claim_value=assessment.support_level.name,
                    kind=HarmonicAssertionKind.DESIGN_HYPOTHESIS,
                    evidence_state=HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
                    rationale=(
                        f"{assessment.rationale} Uncertainty: {assessment.uncertainty} "
                        f"Failure mode: {assessment.failure_mode}"
                    ),
                    source_refs=assessment.evidence_refs,
                )
            )

    blockers = tuple(dict.fromkeys((*result.blockers, *result.inventory_holds)))
    if result.state is CypressHeartFrontierState.FRONTIER:
        blockers = (
            "UNRESOLVED_CYPRESS_HEART_FRONTIER",
            *blockers,
        )
    elif state is HarmonicModuleState.HOLD and not blockers:
        blockers = ("CYPRESS_HEART_FRONTIER_HOLD",)

    return HarmonicModuleReportV1(
        module_id="cypress-heart-frontier",
        module_sha256=result.record_sha256,
        state=state,
        assertions=tuple(assertions),
        blockers=blockers,
        next_action=(
            result.next_comparison
            or "resolve the exact Cypress-heart frontier before formula construction"
        ),
        authority_flags=_authority_flags_from(result),
    )


def report_from_temporal_evidence(result: object) -> HarmonicModuleReportV1:
    """Adapt observed-only temporal evidence; incomplete cells remain withheld."""

    from engine.sensory.ledger import TemporalEvidenceResult, TemporalEvidenceState

    if not isinstance(result, TemporalEvidenceResult):
        raise TypeError("result must be a TemporalEvidenceResult")
    if result.safety_stop_triggered:
        state = HarmonicModuleState.HOLD
    elif result.state is TemporalEvidenceState.COMPLETE:
        state = HarmonicModuleState.READY
    else:
        state = HarmonicModuleState.WITHHELD
    source_refs = (
        f"schedule-sha256:{result.schedule_sha256}",
        f"protocol:{result.protocol_id}",
    )
    assertions: tuple[HarmonicAssertionV1, ...] = ()
    if state is HarmonicModuleState.READY:
        assertions = (
            HarmonicAssertionV1(
                assertion_id="temporal-ledger:cell-closure",
                module_id="temporal-ledger",
                scope_key=f"protocol:{result.protocol_id}",
                claim_key="temporal.observed_cell_closure",
                claim_value=(
                    f"{result.observed_cell_count}/{result.expected_cell_count}"
                ),
                kind=HarmonicAssertionKind.OBSERVATION,
                evidence_state=HarmonicEvidenceState.OBSERVED,
                rationale="observed cells only; no interpolation or volatility substitution",
                source_refs=source_refs,
            ),
        )
    payload = {
        "state": result.state.value,
        "protocol_id": result.protocol_id,
        "schedule_sha256": result.schedule_sha256,
        "expected_cell_count": result.expected_cell_count,
        "observed_cell_count": result.observed_cell_count,
        "missing_cell_count": len(result.missing_cells),
        "duplicate_cell_count": len(result.duplicate_cells),
        "summary_count": len(result.summaries),
        "transition_count": len(result.transitions),
        "order_balance_state": result.order_balance_state.value,
        "blockers": list(result.blockers),
        "safety_stop_triggered": result.safety_stop_triggered,
    }
    blockers = tuple(result.blockers)
    if state is not HarmonicModuleState.READY and not blockers:
        blockers = (result.state.value,)
    return HarmonicModuleReportV1(
        module_id="temporal-ledger",
        module_sha256=_payload_sha256(payload),
        state=state,
        assertions=assertions,
        blockers=blockers,
        next_action=(
            result.next_discriminator
            or "collect the next complete blinded temporal cell set"
        ),
        authority_flags=_authority_flags_from(result),
    )


def report_from_preference(result: object) -> HarmonicModuleReportV1:
    """Adapt criterion-scoped preference validation without a synthetic beauty score."""

    from engine.preference import PreferenceFitResult, PreferenceFitStatus

    if not isinstance(result, PreferenceFitResult):
        raise TypeError("result must be a PreferenceFitResult")
    state = (
        HarmonicModuleState.READY
        if result.status is PreferenceFitStatus.VALIDATED and result.validated
        else HarmonicModuleState.WITHHELD
    )
    assertions: tuple[HarmonicAssertionV1, ...] = ()
    criterion = result.criterion_id or "UNSCOPED"
    source_refs = tuple(result.evidence.sources) or (
        f"preference-model:{result.model_family.value}",
    )
    if state is HarmonicModuleState.READY:
        assertions = (
            HarmonicAssertionV1(
                assertion_id=f"hedonic-preference:{criterion}:validated",
                module_id="hedonic-preference",
                scope_key=f"criterion:{criterion}",
                claim_key=f"preference.{criterion}.validation_state",
                claim_value="VALIDATED_ABOVE_DECLARED_BASELINE",
                kind=HarmonicAssertionKind.OBSERVATION,
                evidence_state=HarmonicEvidenceState.OBSERVED,
                rationale=(
                    "criterion-specific held-out validation; no cross-criterion beauty "
                    "aggregation"
                ),
                source_refs=source_refs,
            ),
        )
    payload = {
        "status": result.status.value,
        "validated": result.validated,
        "comparison_count": result.comparison_count,
        "connected": result.connected,
        "heldout_accuracy": result.heldout_accuracy,
        "baseline_accuracy": result.baseline_accuracy,
        "gate_failures": list(result.gate_failures),
        "criterion_id": result.criterion_id,
        "tie_rate": result.tie_rate,
        "bootstrap_replicates": result.bootstrap_replicates,
        "bootstrap_seed": result.bootstrap_seed,
        "model_family": result.model_family.value,
        "converged": result.converged,
        "convergence_code": result.convergence_code,
    }
    blockers = tuple(result.gate_failures)
    if state is HarmonicModuleState.WITHHELD and not blockers:
        blockers = (f"PREFERENCE_{result.status.value.upper()}",)
    if result.next_comparison is None:
        next_action = "collect a scoped, blinded, order-balanced held-out comparison"
    else:
        next_action = (
            f"compare {result.next_comparison[0]} against {result.next_comparison[1]} "
            f"for criterion {criterion}"
        )
    return HarmonicModuleReportV1(
        module_id="hedonic-preference",
        module_sha256=_payload_sha256(payload),
        state=state,
        assertions=assertions,
        blockers=blockers,
        next_action=next_action,
        authority_flags=(),
    )


def synthesize_harmonically(
    request: HarmonicSynthesisRequestV1,
    *,
    atlas: MaterialCapabilityAtlas,
) -> HarmonicSynthesisResultV1:
    """Reconcile exact-scope module contracts without voting or score averaging."""

    if not isinstance(request, HarmonicSynthesisRequestV1):
        raise TypeError("request must be a HarmonicSynthesisRequestV1")
    if not isinstance(atlas, MaterialCapabilityAtlas):
        raise TypeError("atlas must be a MaterialCapabilityAtlas")

    reports_by_id = {item.module_id: item for item in request.module_reports}
    structural_blockers: list[str] = []
    empirical_gaps: list[str] = []
    for module_id in request.required_module_ids:
        report = reports_by_id.get(module_id)
        if report is None:
            structural_blockers.append(f"{module_id}:MISSING_MODULE_REPORT")
            continue
        if module_id in request.design_gate_module_ids:
            if report.state is not HarmonicModuleState.READY:
                detail = "|".join(report.blockers) or report.state.value
                structural_blockers.append(f"{module_id}:{detail}")
        elif report.state is not HarmonicModuleState.READY:
            details = report.blockers or (report.state.value,)
            empirical_gaps.extend(f"{module_id}:{detail}" for detail in details)

    resolved_claims, tensions = _resolved_claims(request.module_reports)
    for tension in tensions:
        structural_blockers.append(
            f"CLAIM_TENSION:{tension.scope_key}:{tension.claim_key}"
        )

    report_ids = set(reports_by_id)
    retained_relations: list[HarmonicRelationV1] = []
    for relation in request.relations:
        missing_modules = set(relation.module_ids) - report_ids
        held_modules = {
            module_id
            for module_id in relation.module_ids
            if module_id in reports_by_id
            and reports_by_id[module_id].state is not HarmonicModuleState.READY
        }
        if missing_modules:
            structural_blockers.append(
                f"{relation.relation_id}:MISSING_MODULES:{','.join(sorted(missing_modules))}"
            )
        elif held_modules:
            structural_blockers.append(
                f"{relation.relation_id}:HELD_MODULES:{','.join(sorted(held_modules))}"
            )
        else:
            retained_relations.append(relation)

    material_dispositions = tuple(
        _material_disposition(intent, atlas) for intent in request.material_intents
    )
    for intent, disposition in zip(
        request.material_intents,
        material_dispositions,
        strict=True,
    ):
        if disposition.state is HarmonicMaterialState.CURRENT_HOLD:
            detail = "|".join(disposition.blockers) or "CURRENT_BUILD_NOT_READY"
            structural_blockers.append(
                f"{intent.material_name}:{intent.role_id}:{detail}"
            )

    structural = tuple(dict.fromkeys(structural_blockers))
    gaps = tuple(sorted(set(empirical_gaps)))
    if structural:
        state = HarmonicSynthesisState.HOLD
    elif not retained_relations and not request.material_intents and not resolved_claims:
        state = HarmonicSynthesisState.NO_CHANGE
    else:
        state = HarmonicSynthesisState.DESIGN_READY

    if tensions:
        next_comparison: str | None = tensions[0].required_resolution
    elif any(
        item.state is HarmonicMaterialState.CURRENT_HOLD
        for item in material_dispositions
    ):
        held = next(
            item
            for item in material_dispositions
            if item.state is HarmonicMaterialState.CURRENT_HOLD
        )
        next_comparison = (
            f"resolve current-stock authority for {held.material_name} before dosing"
        )
    elif retained_relations:
        next_comparison = retained_relations[0].probe_ref
    elif gaps:
        next_comparison = gaps[0]
    else:
        next_comparison = request.no_change_reason

    return HarmonicSynthesisResultV1(
        state=state,
        target=request.target,
        request_sha256=request.record_sha256,
        resolved_claims=resolved_claims,
        tensions=tensions,
        retained_relations=tuple(retained_relations),
        material_dispositions=material_dispositions,
        structural_blockers=structural,
        empirical_gaps=gaps,
        next_comparison=next_comparison,
        claim_ceiling=request.target.claim_ceiling,
    )


__all__ = [
    "HarmonicAssertionKind",
    "HarmonicAssertionV1",
    "HarmonicEvidenceState",
    "HarmonicMaterialDispositionV1",
    "HarmonicMaterialIntentV1",
    "HarmonicMaterialState",
    "HarmonicModuleReportV1",
    "HarmonicModuleState",
    "HarmonicRelationV1",
    "HarmonicResolvedClaimV1",
    "HarmonicSynthesisRequestV1",
    "HarmonicSynthesisResultV1",
    "HarmonicSynthesisState",
    "HarmonicTargetContractV1",
    "HarmonicTensionV1",
    "report_from_architectural_delta",
    "report_from_architecture_compiler",
    "report_from_cypress_heart_frontier",
    "report_from_family_depth",
    "report_from_material_atlas",
    "report_from_preference",
    "report_from_temporal_evidence",
    "synthesize_harmonically",
]
