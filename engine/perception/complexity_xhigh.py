"""Sealed, provider-neutral contracts for the paired ChatGPT xhigh benchmark.

This module prepares and validates benchmark artifacts.  It deliberately has
no network client and cannot submit a provider request.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from engine.calibration.hashing import canonical_json_bytes, stable_json_hash
from engine.perception.complexity_ensemble import (
    ComplexityBundle,
    ComplexityCasePacket,
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")

RESPONSE_TOP_LEVEL_KEYS = (
    "target_identity",
    "functional_architecture",
    "depth_and_richness_analysis",
    "target_ideal_formula",
    "current_inventory_build",
    "missing_chemical_impact",
    "controlled_test_plan",
    "claims",
    "conflicts_and_holds",
    "answer_markdown",
)

DEPTH_FIELD_KEYS = (
    "identity_linked_facets",
    "coherent_richness",
    "temporal_unfolding",
    "restraint_or_subtraction",
    "hedonic_potential_hypotheses",
    "complication_risks",
)

COMMON_OUTPUT_CONTRACT: Mapping[str, Any] = MappingProxyType(
    {
        "format": "ONE_JSON_OBJECT",
        "json_only": True,
        "markdown_fences_forbidden": True,
        "additional_top_level_keys": False,
        "required_top_level_keys": RESPONSE_TOP_LEVEL_KEYS,
        "formula_fields_may_be_null_when_not_formula_bearing": True,
        "depth_and_richness_required_keys": DEPTH_FIELD_KEYS,
        "hedonic_hypothesis_contract": {
            "required_state": "DESIGN_HYPOTHESIS_NOT_TESTED",
            "required_fields": (
                "state",
                "target_linked_mechanism",
                "controlled_sensory_comparison",
                "evidence_refs",
            ),
            "forbidden_support": (
                "raw counts",
                "response length",
                "jargon",
                "ornamentation",
            ),
        },
        "claim_required_keys": (
            "claim",
            "state",
            "evidence_refs",
            "authority_ceiling",
        ),
        "field_contracts": {
            "target_identity": {
                "type": "object",
                "required_keys": ("identity", "preserved", "evidence_refs"),
                "requirements": (
                    "identity must exactly equal case.target_identity",
                    "preserved must be true",
                    "evidence_refs must be nonempty and use only allowed_evidence_refs",
                ),
            },
            "functional_architecture": {
                "type": "object",
                "required_nonempty_keys": (
                    "roles",
                    "temporal_handoffs",
                    "failure_boundaries",
                ),
                "role_item_keys": ("function", "target_link"),
            },
            "depth_and_richness_analysis": {
                "type": "object",
                "required_keys": DEPTH_FIELD_KEYS,
                "required_nonempty_keys": (
                    "identity_linked_facets",
                    "coherent_richness",
                    "temporal_unfolding",
                    "restraint_or_subtraction",
                    "hedonic_potential_hypotheses",
                ),
                "identity_linked_facet_item_keys": (
                    "facet",
                    "target_link",
                    "evidence_refs",
                ),
            },
            "target_ideal_formula": {
                "type": "object_or_null",
                "required_keys_when_object": (
                    "state",
                    "materials",
                    "inventory_independent",
                    "exception_calls",
                ),
                "scored_requirements": (
                    "inventory_independent must be true",
                    "materials must differ from current_inventory_build.materials",
                ),
                "exception_calls_contract": {
                    "type": "object keyed by exact material name; never an array",
                    "required_fields_per_exception_material": (
                        "target_tonal_role",
                        "why_alternatives_fail",
                        "loss_if_omitted",
                        "failure_mode",
                        "omission_control",
                        "alternative_control",
                    ),
                },
            },
            "current_inventory_build": {
                "type": "object_or_null",
                "required_keys_when_object": (
                    "state",
                    "materials",
                    "exact_stock_refs",
                    "exception_calls",
                ),
                "requirements": (
                    "do not assert ownership or physical compounding without case evidence",
                    "keep target ideal and current build separate",
                ),
                "exception_calls_contract": {
                    "type": "object keyed by exact material name; never an array",
                    "required_fields_per_exception_material": (
                        "target_tonal_role",
                        "why_alternatives_fail",
                        "loss_if_omitted",
                        "failure_mode",
                        "omission_control",
                        "alternative_control",
                    ),
                },
            },
            "missing_chemical_impact": {
                "type": "object",
                "required_keys": (
                    "strongly_covered",
                    "weakly_covered",
                    "genuinely_missing",
                    "controlled_comparison",
                ),
                "controlled_comparison_must_be_nonempty": True,
            },
            "controlled_test_plan": {
                "type": "object",
                "required_nonempty_keys": (
                    "isolation",
                    "controls",
                    "dose_time_substrate",
                    "blinding",
                    "endpoints",
                    "decision_rule",
                ),
            },
            "claims": {
                "type": "nonempty_array",
                "item_required_keys": (
                    "claim",
                    "state",
                    "evidence_refs",
                    "authority_ceiling",
                ),
                "requirements": (
                    "include at least one claim for every required_claim_state",
                    "every evidence_refs list must be nonempty and use only allowed_evidence_refs",
                    "every authority_ceiling must exactly equal claim_authority_ceiling",
                ),
            },
            "conflicts_and_holds": {
                "type": "array",
                "minimum_items": 1,
                "item_required_keys": ("issue", "state", "next_action"),
                "requirements": (
                    "preserve unresolved same-scope conflicts as holds",
                    "every item must have a nonempty next_action",
                ),
            },
            "answer_markdown": {
                "type": "string",
                "maximum_characters": 2000,
                "required_literal": "NOT TESTED",
            },
        },
    }
)


def _sha256(value: object, *, field_name: str = "SHA-256") -> str:
    normalized = str(value).strip().lower()
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} must be 64 lowercase hexadecimal characters")
    return normalized


def _nonblank(value: object, *, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


class _FrozenList(tuple[Any, ...]):
    def __eq__(self, other: object) -> bool:
        if isinstance(other, (list, tuple)):
            return tuple(self) == tuple(other)
        return NotImplemented

    __hash__ = tuple.__hash__


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return _FrozenList(_deep_freeze(item) for item in value)
    return value


def _response_bytes(value: bytes | str) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


class BenchmarkArm(str, Enum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"
    ABLATION = "ABLATION"


@dataclass(frozen=True, slots=True)
class XHighRequest:
    request_id: str
    case_id: str
    arm: BenchmarkArm
    nonce: str
    model_requirement: str
    reasoning_effort: str
    common_input_sha256: str
    prompt_payload: Mapping[str, Any]
    prompt_sha256: str
    attachment_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        _nonblank(self.request_id, field_name="request_id")
        _nonblank(self.case_id, field_name="case_id")
        _nonblank(self.nonce, field_name="nonce")
        _nonblank(self.model_requirement, field_name="model_requirement")
        if self.reasoning_effort != "xhigh":
            raise ValueError("reasoning_effort must be xhigh")
        _sha256(self.common_input_sha256, field_name="common_input_sha256")
        _sha256(self.prompt_sha256, field_name="prompt_sha256")
        for value in self.attachment_sha256s:
            _sha256(value, field_name="attachment_sha256")

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "case_id": self.case_id,
            "arm": self.arm.value,
            "nonce": self.nonce,
            "model_requirement": self.model_requirement,
            "reasoning_effort": self.reasoning_effort,
            "common_input_sha256": self.common_input_sha256,
            "prompt_payload": dict(self.prompt_payload),
            "prompt_sha256": self.prompt_sha256,
            "attachment_sha256s": list(self.attachment_sha256s),
        }


@dataclass(frozen=True, slots=True)
class XHighExecutionReceipt:
    request_id: str
    nonce: str
    provider: str
    product: str
    model_identity: str
    reasoning_effort: str
    context_clean: bool
    prior_case_transcript_visible: bool
    prompt_sha256: str
    attachment_sha256s: tuple[str, ...]
    submitted_at: str
    completed_at: str
    completion_state: str
    conversation_id: str
    response_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    price_usd: Decimal | None

    def __post_init__(self) -> None:
        _sha256(self.prompt_sha256, field_name="prompt_sha256")
        _sha256(self.response_sha256, field_name="response_sha256")
        for value in self.attachment_sha256s:
            _sha256(value, field_name="attachment_sha256")
        for field_name in ("input_tokens", "output_tokens", "latency_ms"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be nonnegative")
        if self.price_usd is not None and self.price_usd < 0:
            raise ValueError("price_usd must be nonnegative")

    @property
    def telemetry_state(self) -> str:
        values = (
            self.input_tokens,
            self.output_tokens,
            self.latency_ms,
            self.price_usd,
        )
        if all(value is None for value in values):
            return "NOT_EXPOSED"
        if all(value is not None for value in values):
            return "EXPOSED"
        return "PARTIAL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "nonce": self.nonce,
            "provider": self.provider,
            "product": self.product,
            "model_identity": self.model_identity,
            "reasoning_effort": self.reasoning_effort,
            "context_clean": self.context_clean,
            "prior_case_transcript_visible": self.prior_case_transcript_visible,
            "prompt_sha256": self.prompt_sha256,
            "attachment_sha256s": list(self.attachment_sha256s),
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
            "completion_state": self.completion_state,
            "conversation_id": self.conversation_id,
            "response_sha256": self.response_sha256,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "price_usd": str(self.price_usd) if self.price_usd is not None else None,
            "telemetry_state": self.telemetry_state,
        }


@dataclass(frozen=True, slots=True)
class XHighValidationResult:
    state: str
    blockers: tuple[str, ...]
    telemetry_state: str


@dataclass(frozen=True, slots=True)
class AnonymizedResponse:
    anonymous_label: str
    response_sha256: str
    response_bytes: bytes


def _common_prompt(case: ComplexityCasePacket) -> dict[str, Any]:
    evidence_packets = [
        {
            "evidence_packet_id": f"E{index:02d}",
            "payload": case.module_inputs[family_id],
        }
        for index, family_id in enumerate(case.relevant_families, start=1)
    ]
    output_contract = dict(COMMON_OUTPUT_CONTRACT)
    output_contract.update(
        {
            "required_claim_states": tuple(
                case.expected_invariants["required_claim_states"]
            ),
            "allowed_evidence_refs": case.evidence_refs,
            "claim_authority_ceiling": case.permitted_claim_ceiling,
            "musk_exception_contract": case.expected_invariants[
                "complexity_definition"
            ]["musk_policy"],
        }
    )
    return {
        "schema_version": "complexity_xhigh_prompt_v3",
        "case": {
            "case_id": case.case_id,
            "category": case.category,
            "target_name": case.target_name,
            "target_identity": case.target_identity,
            "brief": case.brief,
            "inventory_authority_sha256": case.inventory_authority_sha256,
            "local_inventory_sha256": case.local_inventory_sha256,
            "inventory_reconciliation_state": case.inventory_reconciliation_state,
            "evidence_refs": case.evidence_refs,
            "evidence_sha256s": case.evidence_sha256s,
            "permitted_claim_ceiling": case.permitted_claim_ceiling,
        },
        "evidence_packets": evidence_packets,
        "complexity_definition": case.expected_invariants["complexity_definition"],
        "output_contract": output_contract,
    }


def prepare_xhigh_request(
    case: ComplexityCasePacket,
    arm: BenchmarkArm,
    *,
    bundle: ComplexityBundle | None,
) -> XHighRequest:
    if arm is BenchmarkArm.CONTROL and bundle is not None:
        raise ValueError("control request must not include a module bundle")
    if arm is not BenchmarkArm.CONTROL:
        if bundle is None or bundle.state != "PASS":
            raise ValueError("treatment or ablation request requires a passing bundle")
        if bundle.case_id != case.case_id or bundle.case_input_sha256 != case.input_sha256:
            raise ValueError("module bundle must bind the exact case")

    common = _common_prompt(case)
    common_input_sha256 = stable_json_hash(common)
    prompt: dict[str, Any] = dict(common)
    if bundle is not None:
        prompt["module_bundle"] = bundle.as_dict()
    prompt_sha256 = stable_json_hash(prompt)
    nonce_digest = hashlib.sha256(
        f"{case.nonce}:{arm.value}:{prompt_sha256}".encode()
    ).hexdigest()
    nonce = f"{case.case_id}-{arm.value.lower()}-{nonce_digest[:16]}"
    request_id = f"cxreq-{case.case_id.lower()}-{arm.value.lower()}-{nonce_digest[16:28]}"
    attachments = tuple(
        dict.fromkeys(
            (
                case.inventory_authority_sha256,
                case.local_inventory_sha256,
                *case.evidence_sha256s,
            )
        )
    )
    return XHighRequest(
        request_id=request_id,
        case_id=case.case_id,
        arm=arm,
        nonce=nonce,
        model_requirement="ChatGPT-current",
        reasoning_effort="xhigh",
        common_input_sha256=common_input_sha256,
        prompt_payload=_deep_freeze(prompt),
        prompt_sha256=prompt_sha256,
        attachment_sha256s=attachments,
    )


def validate_xhigh_execution(
    request: XHighRequest,
    receipt: XHighExecutionReceipt,
    *,
    seen_nonces: frozenset[str],
    response_bytes: bytes | str | None = None,
) -> XHighValidationResult:
    checks = (
        (
            request.nonce in seen_nonces,
            "BENCHMARK_BLOCKED_DUPLICATE_NONCE",
            "nonce already exists in the run ledger",
        ),
        (
            receipt.request_id != request.request_id or receipt.nonce != request.nonce,
            "BENCHMARK_BLOCKED_REQUEST_IDENTITY_MISMATCH",
            "receipt does not bind the exact request and nonce",
        ),
        (
            receipt.provider.casefold() != "openai"
            or receipt.product.casefold() != "chatgpt",
            "BENCHMARK_BLOCKED_UNVERIFIED_CHATGPT",
            "provider/product identity is not verified ChatGPT",
        ),
        (
            receipt.model_identity != request.model_requirement,
            "BENCHMARK_BLOCKED_UNVERIFIED_XHIGH",
            "model identity does not match the sealed requirement",
        ),
        (
            receipt.reasoning_effort != "xhigh",
            "BENCHMARK_BLOCKED_UNVERIFIED_XHIGH",
            "reasoning effort is not xhigh",
        ),
        (
            not receipt.context_clean or receipt.prior_case_transcript_visible,
            "BENCHMARK_BLOCKED_CONTEXT_NOT_CLEAN",
            "context isolation is not proven",
        ),
        (
            receipt.prompt_sha256 != request.prompt_sha256
            or receipt.attachment_sha256s != request.attachment_sha256s,
            "BENCHMARK_BLOCKED_INPUT_HASH_MISMATCH",
            "prompt or attachment hashes drifted",
        ),
        (
            receipt.completion_state != "SUCCEEDED",
            "BENCHMARK_BLOCKED_AMBIGUOUS_COMPLETION"
            if receipt.completion_state in {"AMBIGUOUS", "TIMEOUT", "UNKNOWN"}
            else "BENCHMARK_BLOCKED_INCOMPLETE",
            "provider completion is not a verified terminal success",
        ),
        (
            not receipt.conversation_id.strip(),
            "BENCHMARK_BLOCKED_MISSING_PROVIDER_ID",
            "provider conversation identity is missing",
        ),
    )
    for failed, state, blocker in checks:
        if failed:
            return XHighValidationResult(state, (blocker,), receipt.telemetry_state)

    if response_bytes is not None:
        digest = hashlib.sha256(_response_bytes(response_bytes)).hexdigest()
        if digest != receipt.response_sha256:
            return XHighValidationResult(
                "BENCHMARK_BLOCKED_RESPONSE_HASH_MISMATCH",
                ("response bytes do not match the execution receipt",),
                receipt.telemetry_state,
            )
    return XHighValidationResult("PASS", (), receipt.telemetry_state)


def anonymize_response_pair(
    corpus_sha256: str,
    case_id: str,
    responses: Mapping[BenchmarkArm, bytes | str],
) -> tuple[AnonymizedResponse, ...]:
    corpus_digest = _sha256(corpus_sha256, field_name="corpus_sha256")
    if set(responses) != {BenchmarkArm.CONTROL, BenchmarkArm.TREATMENT}:
        raise ValueError("response pair must contain exactly control and treatment")
    packets = []
    for arm, response in responses.items():
        raw = _response_bytes(response)
        label = hashlib.sha256(
            f"{corpus_digest}{case_id}{arm.value}".encode()
        ).hexdigest()[:12]
        packets.append(
            AnonymizedResponse(
                anonymous_label=label,
                response_sha256=hashlib.sha256(raw).hexdigest(),
                response_bytes=raw,
            )
        )
    return tuple(sorted(packets, key=lambda item: item.anonymous_label))


def prompt_bytes(request: XHighRequest) -> bytes:
    """Return the exact canonical prompt bytes recorded by ``prompt_sha256``."""

    return canonical_json_bytes(request.prompt_payload)
