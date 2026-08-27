"""Immutable case packets and separated, authority-withheld complexity bundles."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping

from engine.calibration.hashing import stable_json_hash
from engine.perception.complexity_registry import (
    ComplexityRegistry,
    ModuleRole,
)

INVENTORY_AUTHORITY_SHA256 = (
    "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
)
LOCAL_INVENTORY_SHA256 = (
    "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
)
USEFUL_COMPLEXITY_DEFINITION: Mapping[str, Any] = {
    "positive_evidence": [
        "identity-linked facets",
        "coherent perceptual planes, contrasts, and textures",
        "meaningful temporal unfolding",
        "testable hedonic-potential mechanisms",
        "restraint, spacing, dosage control, or negative space",
    ],
    "invalid_proxies": [
        "ingredient count",
        "module count",
        "interaction count",
        "descriptor count",
        "novelty",
        "response length",
        "jargon",
        "technical density",
    ],
    "claim_ceiling": "DESIGN_HYPOTHESIS_NOT_TESTED",
    "musk_policy": {
        "selection_rule": (
            "one exact musk or distinct-role layers; never reward musk count"
        ),
        "exception_only_materials": ["Tonalide", "Macrolide", "Musk Ketone"],
        "exception_fields": [
            "target_tonal_role",
            "why_alternatives_fail",
            "loss_if_omitted",
            "failure_mode",
            "omission_control",
            "alternative_control",
        ],
        "current_depleted_exception_state": "HOLD_PROCUREMENT_REQUIRED",
    },
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CASE_ID = re.compile(r"^CX-[A-D][0-9]{2}$")
_FORBIDDEN_AGGREGATE_KEYS = frozenset(
    {
        "overall_score",
        "complexity_score",
        "hedonic_score",
        "quality_score",
        "beauty_score",
    }
)


def _sha256(value: object) -> str:
    normalized = str(value).strip().lower()
    if _SHA256.fullmatch(normalized) is None:
        raise ValueError("SHA-256 must be 64 lowercase hexadecimal characters")
    return normalized


def _nonblank(value: object, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("case and module mapping keys must be strings")
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported immutable packet value: {type(value).__name__}")


def _deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(item) for item in value]
    return value


def _contains_aggregate_score(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(str(key).casefold() in _FORBIDDEN_AGGREGATE_KEYS for key in value):
            return True
        return any(_contains_aggregate_score(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_aggregate_score(item) for item in value)
    return False


@dataclass(frozen=True, slots=True)
class ComplexityCasePacket:
    case_id: str
    category: str
    target_name: str
    target_identity: str
    brief: str
    inventory_authority_sha256: str
    local_inventory_sha256: str
    inventory_reconciliation_state: str
    evidence_refs: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    relevant_families: tuple[str, ...]
    module_inputs: Mapping[str, Mapping[str, Any]]
    expected_invariants: Mapping[str, Any]
    permitted_claim_ceiling: str
    nonce: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ComplexityCasePacket":
        required = {
            "case_id",
            "category",
            "target_name",
            "target_identity",
            "brief",
            "inventory_authority_sha256",
            "local_inventory_sha256",
            "inventory_reconciliation_state",
            "evidence_refs",
            "evidence_sha256s",
            "relevant_families",
            "module_inputs",
            "expected_invariants",
            "permitted_claim_ceiling",
            "nonce",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("case packet keys must match the v1 contract exactly")
        raw_relevant = value["relevant_families"]
        if not isinstance(raw_relevant, (list, tuple)):
            raise ValueError("relevant family IDs must be a sequence")
        relevant = tuple(_nonblank(item, "relevant family ID") for item in raw_relevant)
        if not relevant or len(relevant) != len(set(relevant)):
            raise ValueError("relevant family IDs must be nonempty and unique")
        if relevant != tuple(sorted(relevant)):
            raise ValueError("relevant family IDs must be sorted")
        raw_inputs = value["module_inputs"]
        if not isinstance(raw_inputs, Mapping):
            raise ValueError("module_inputs must be a mapping")
        inputs: dict[str, Mapping[str, Any]] = {}
        for key, item in raw_inputs.items():
            family_id = _nonblank(key, "module input family")
            if not isinstance(item, Mapping):
                raise ValueError("each module input must be a mapping")
            inputs[family_id] = _deep_freeze(item)
        if not set(inputs).issubset(relevant):
            raise ValueError("module input keys must be relevant family IDs")
        raw_refs = value["evidence_refs"]
        raw_hashes = value["evidence_sha256s"]
        if not isinstance(raw_refs, (list, tuple)) or not isinstance(
            raw_hashes, (list, tuple)
        ):
            raise ValueError("evidence references and hashes must be sequences")
        refs = tuple(_nonblank(item, "evidence reference") for item in raw_refs)
        hashes = tuple(_sha256(item) for item in raw_hashes)
        if not refs or not hashes:
            raise ValueError("at least one evidence reference and hash are required")
        if len(hashes) != len(set(hashes)) or hashes != tuple(sorted(hashes)):
            raise ValueError("evidence SHA-256 values must be unique and sorted")
        expected = value["expected_invariants"]
        if not isinstance(expected, Mapping):
            raise ValueError("expected_invariants must be a mapping")
        packet = cls(
            case_id=_nonblank(value["case_id"], "case_id"),
            category=_nonblank(value["category"], "category"),
            target_name=_nonblank(value["target_name"], "target_name"),
            target_identity=_nonblank(value["target_identity"], "target_identity"),
            brief=_nonblank(value["brief"], "brief"),
            inventory_authority_sha256=_sha256(value["inventory_authority_sha256"]),
            local_inventory_sha256=_sha256(value["local_inventory_sha256"]),
            inventory_reconciliation_state=_nonblank(
                value["inventory_reconciliation_state"],
                "inventory_reconciliation_state",
            ),
            evidence_refs=refs,
            evidence_sha256s=hashes,
            relevant_families=relevant,
            module_inputs=MappingProxyType(inputs),
            expected_invariants=_deep_freeze(expected),
            permitted_claim_ceiling=_nonblank(
                value["permitted_claim_ceiling"], "permitted_claim_ceiling"
            ),
            nonce=_nonblank(value["nonce"], "nonce"),
        )
        packet._validate()
        return packet

    def _validate(self) -> None:
        if self.inventory_authority_sha256 != INVENTORY_AUTHORITY_SHA256:
            raise ValueError("inventory authority hash does not match the frozen workbook")
        if self.local_inventory_sha256 != LOCAL_INVENTORY_SHA256:
            raise ValueError("local inventory hash does not match the frozen text inventory")
        if self.inventory_reconciliation_state != "MATCH":
            raise ValueError("inventory reconciliation must be MATCH")
        if _CASE_ID.fullmatch(self.case_id) is None:
            raise ValueError("case_id must match CX-[A-D][0-9]{2}")
        if re.fullmatch(rf"{re.escape(self.case_id)}-[0-9a-f]{{16}}", self.nonce) is None:
            raise ValueError("nonce must match the case-bound v1 format")
        definition = self.expected_invariants.get("complexity_definition")
        if _deep_thaw(definition) != USEFUL_COMPLEXITY_DEFINITION:
            raise ValueError("complexity definition must match the frozen depth contract")

    @property
    def input_sha256(self) -> str:
        return stable_json_hash(self.as_dict(include_hash=False))

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "case_id": self.case_id,
            "category": self.category,
            "target_name": self.target_name,
            "target_identity": self.target_identity,
            "brief": self.brief,
            "inventory_authority_sha256": self.inventory_authority_sha256,
            "local_inventory_sha256": self.local_inventory_sha256,
            "inventory_reconciliation_state": self.inventory_reconciliation_state,
            "evidence_refs": list(self.evidence_refs),
            "evidence_sha256s": list(self.evidence_sha256s),
            "relevant_families": list(self.relevant_families),
            "module_inputs": _deep_thaw(self.module_inputs),
            "expected_invariants": _deep_thaw(self.expected_invariants),
            "permitted_claim_ceiling": self.permitted_claim_ceiling,
            "nonce": self.nonce,
        }
        if include_hash:
            payload["input_sha256"] = self.input_sha256
        return payload


Adapter = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ModuleRun:
    family_id: str
    state: str
    input_sha256: str | None
    output_sha256: str | None
    blocker: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComplexityBundle:
    case_id: str
    state: str
    case_input_sha256: str
    registry_sha256: str
    omitted_families: tuple[str, ...]
    family_outputs: Mapping[str, Mapping[str, Any]]
    module_runs: tuple[ModuleRun, ...]
    blockers: tuple[str, ...]
    source_admission_authority: bool = field(default=False, init=False)
    formula_authority: bool = field(default=False, init=False)
    inventory_authority: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "state": self.state,
            "case_input_sha256": self.case_input_sha256,
            "registry_sha256": self.registry_sha256,
            "omitted_families": list(self.omitted_families),
            "family_outputs": _deep_thaw(self.family_outputs),
            "module_runs": [item.as_dict() for item in self.module_runs],
            "blockers": list(self.blockers),
            "source_admission_authority": self.source_admission_authority,
            "formula_authority": self.formula_authority,
            "inventory_authority": self.inventory_authority,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "safety_authority": self.safety_authority,
            "release_authority": self.release_authority,
        }


def evaluate_complexity_case(
    case: ComplexityCasePacket,
    registry: ComplexityRegistry,
    *,
    adapters: Mapping[str, Adapter],
    omitted_families: frozenset[str] = frozenset(),
) -> ComplexityBundle:
    unknown_omissions = omitted_families.difference(case.relevant_families)
    if unknown_omissions:
        raise ValueError("omitted families must be relevant to the case")
    outputs: dict[str, Mapping[str, Any]] = {}
    runs: list[ModuleRun] = []
    blockers: list[str] = []
    for family_id in case.relevant_families:
        descriptors = registry.modules_for_family(family_id)
        if not descriptors or not any(item.runtime_eligible for item in descriptors):
            blocker = f"{family_id}: no runtime-eligible module"
            blockers.append(blocker)
            runs.append(ModuleRun(family_id, "HOLD", None, None, blocker))
            continue
        if family_id in omitted_families:
            runs.append(ModuleRun(family_id, "OMITTED", None, None, None))
            continue
        payload = case.module_inputs.get(family_id)
        adapter = adapters.get(family_id)
        if payload is None or adapter is None:
            blocker = f"{family_id}: missing input or adapter"
            blockers.append(blocker)
            runs.append(ModuleRun(family_id, "HOLD", None, None, blocker))
            continue
        input_sha256 = stable_json_hash(payload)
        try:
            raw_output = adapter(payload)
            if not isinstance(raw_output, Mapping):
                raise TypeError("adapter output must be a mapping")
            if _contains_aggregate_score(raw_output):
                raise ValueError("aggregate score fields are forbidden")
            output = _deep_freeze(raw_output)
        except Exception as exc:  # adapters are a fail-closed trust boundary
            blocker = f"{family_id}: {exc}"
            blockers.append(blocker)
            runs.append(ModuleRun(family_id, "HOLD", input_sha256, None, str(exc)))
            continue
        outputs[family_id] = output
        runs.append(
            ModuleRun(
                family_id,
                "PASS",
                input_sha256,
                stable_json_hash(output),
                None,
            )
        )
    return ComplexityBundle(
        case_id=case.case_id,
        state="HOLD" if blockers else "PASS",
        case_input_sha256=case.input_sha256,
        registry_sha256=registry.registry_sha256,
        omitted_families=tuple(sorted(omitted_families)),
        family_outputs=MappingProxyType(outputs),
        module_runs=tuple(runs),
        blockers=tuple(blockers),
    )


def ablate_complexity_case(
    case: ComplexityCasePacket,
    registry: ComplexityRegistry,
    *,
    omitted_family: str,
    adapters: Mapping[str, Adapter],
) -> ComplexityBundle:
    if omitted_family not in case.relevant_families:
        raise ValueError("omitted family must be relevant to the case")
    if registry.family_role(omitted_family) is ModuleRole.GUARDRAIL:
        raise ValueError("mandatory guardrail cannot be omitted from normal treatment")
    return evaluate_complexity_case(
        case,
        registry,
        adapters=adapters,
        omitted_families=frozenset({omitted_family}),
    )
