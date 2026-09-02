"""Read-only recursive candidate facade for exact thirteen-plane synthesis.

Every ordered layer contains one assessment for each architectural plane at one
exact scope. A shallower layer embeds and hashes the immediately deeper layer
receipt, so any deep change propagates to the root receipt. This module remains
an unadmitted structural candidate: it performs no I/O and grants no formula,
inventory, physical, sensory, outcome, safety, stability, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, cast

from .contracts import (
    AssessmentScope,
    AuthorityCeiling,
    PlaneAssessment,
    PlaneId,
    ScopedNativeCriterion,
    ScopedUnknown,
    _canonical_json_bytes,
    _CanonicalRecord,
    _payload,
)
from .plane_synthesis import PlaneSynthesisResult, SynthesisConflict, synthesize_planes

_CANDIDATE_STATE = "future_candidate_not_validated"
MAX_RECURSIVE_LAYERS = 16
_AUTHORITY_FLAGS = (
    "empirical_authority",
    "formula_generation_authorized",
    "formula_mutation_authorized",
    "inventory_mutation_authorized",
    "runtime_integration_authorized",
    "production_runtime_admission_authorized",
    "physical_execution_authorized",
    "compounding_authorized",
    "purchase_authority",
    "pass_fail_authority",
    "sensory_authority",
    "liking_authority",
    "beauty_authority",
    "hedonic_outcome_authority",
    "hedonic_score_authorized",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "release_authority",
)


def _canonical_assessments(
    values: Iterable[PlaneAssessment],
) -> tuple[PlaneAssessment, ...]:
    assessments = tuple(values)
    if any(not isinstance(item, PlaneAssessment) for item in assessments):
        raise TypeError("assessments must contain PlaneAssessment values")

    plane_counts = {
        plane_id: sum(item.plane_id is plane_id for item in assessments)
        for plane_id in PlaneId
    }
    duplicates = tuple(
        plane_id.value for plane_id, count in plane_counts.items() if count > 1
    )
    if duplicates:
        raise ValueError(
            "deep-plane layer contains duplicate planes: "
            + ", ".join(sorted(duplicates))
        )
    missing = tuple(
        plane_id.value for plane_id, count in plane_counts.items() if count == 0
    )
    if missing:
        raise ValueError(
            "deep-plane layer is missing required planes: "
            + ", ".join(sorted(missing))
        )
    if len(assessments) != len(PlaneId):
        raise ValueError("deep-plane layer requires exactly thirteen assessments")

    scopes = {item.scope.key for item in assessments}
    if len(scopes) != 1:
        raise ValueError("deep-plane layer requires one consistent exact scope")
    assessment_ids = tuple(item.assessment_id for item in assessments)
    if len(assessment_ids) != len(set(assessment_ids)):
        raise ValueError("deep-plane layer requires unique assessment_id values")
    return tuple(sorted(assessments, key=lambda item: item.plane_id.value))


def _normalized_id(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _validate_false_authorities(record: object) -> None:
    for field_name in _AUTHORITY_FLAGS:
        value = getattr(record, field_name)
        if not isinstance(value, bool):
            raise TypeError(f"{field_name} must be bool")
        if value:
            raise ValueError(f"{field_name} must remain false")


def _validate_serialized_false_authorities(data: Mapping[str, Any]) -> None:
    for field_name in _AUTHORITY_FLAGS:
        if data[field_name] is not False:
            raise ValueError(f"{field_name} must remain false")


@dataclass(frozen=True, slots=True)
class DeepPlaneLayerRequest(_CanonicalRecord):
    """One ordered recursive layer containing all thirteen planes."""

    SCHEMA_VERSION = "deep_plane_runtime_layer_request_v1"

    layer_id: str
    depth: int
    parent_layer_id: str | None
    assessments: tuple[PlaneAssessment, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "layer_id",
            _normalized_id(self.layer_id, field_name="layer_id"),
        )
        if isinstance(self.depth, bool) or not isinstance(self.depth, int):
            raise TypeError("depth must be an integer")
        if self.depth < 0:
            raise ValueError("depth must be non-negative")
        if self.parent_layer_id is not None:
            object.__setattr__(
                self,
                "parent_layer_id",
                _normalized_id(self.parent_layer_id, field_name="parent_layer_id"),
            )
        object.__setattr__(
            self,
            "assessments",
            _canonical_assessments(self.assessments),
        )

    @property
    def scope(self) -> AssessmentScope:
        return self.assessments[0].scope

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DeepPlaneLayerRequest:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            layer_id=data["layer_id"],
            depth=data["depth"],
            parent_layer_id=data["parent_layer_id"],
            assessments=tuple(
                PlaneAssessment.from_dict(item) for item in data["assessments"]
            ),
        )


@dataclass(frozen=True, slots=True)
class DeepPlaneRuntimeRequest(_CanonicalRecord):
    """Root-to-deep ordered layers under one exact structural scope."""

    SCHEMA_VERSION = "deep_plane_runtime_request_v1"

    layers: tuple[DeepPlaneLayerRequest, ...]

    def __post_init__(self) -> None:
        layers = tuple(self.layers)
        if not layers:
            raise ValueError("deep-plane runtime request requires at least one layer")
        if len(layers) > MAX_RECURSIVE_LAYERS:
            raise ValueError(
                "deep-plane runtime request exceeds the safe maximum of "
                f"{MAX_RECURSIVE_LAYERS} layers"
            )
        if any(not isinstance(item, DeepPlaneLayerRequest) for item in layers):
            raise TypeError("layers must contain DeepPlaneLayerRequest values")
        layer_ids = tuple(item.layer_id for item in layers)
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError("deep-plane runtime request requires unique layer_id values")
        for expected_depth, layer in enumerate(layers):
            if layer.depth != expected_depth:
                raise ValueError("layers must be ordered from depth zero without gaps")
            expected_parent = (
                None if expected_depth == 0 else layers[expected_depth - 1].layer_id
            )
            if layer.parent_layer_id != expected_parent:
                raise ValueError("each deep layer must name its immediate shallower parent")
        if len({layer.scope.key for layer in layers}) != 1:
            raise ValueError("all recursive layers must share one exact scope")
        object.__setattr__(self, "layers", layers)

    @property
    def scope(self) -> AssessmentScope:
        return self.layers[0].scope

    @property
    def assessments(self) -> tuple[PlaneAssessment, ...]:
        """Return root-layer assessments for single-layer-compatible callers."""

        return self.layers[0].assessments

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DeepPlaneRuntimeRequest:
        data = _payload(payload, cls.SCHEMA_VERSION)
        return cls(
            layers=tuple(
                DeepPlaneLayerRequest.from_dict(item) for item in data["layers"]
            )
        )


@dataclass(frozen=True, slots=True)
class DeepPlaneLayerReceipt(_CanonicalRecord):
    """One layer receipt bound to its immediate deeper child, when present."""

    SCHEMA_VERSION = "deep_plane_runtime_layer_receipt_v1"

    layer: DeepPlaneLayerRequest
    synthesis: PlaneSynthesisResult
    assessment_sha256s: tuple[str, ...]
    child_receipt: DeepPlaneLayerReceipt | None
    child_receipt_sha256: str | None
    authority_ceiling: AuthorityCeiling = field(
        default=AuthorityCeiling.WITHHELD,
        init=False,
    )
    empirical_authority: bool = field(default=False, init=False)
    formula_generation_authorized: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    inventory_mutation_authorized: bool = field(default=False, init=False)
    runtime_integration_authorized: bool = field(default=False, init=False)
    production_runtime_admission_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    pass_fail_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    beauty_authority: bool = field(default=False, init=False)
    hedonic_outcome_authority: bool = field(default=False, init=False)
    hedonic_score_authorized: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.layer, DeepPlaneLayerRequest):
            raise TypeError("layer must be a DeepPlaneLayerRequest")
        if not isinstance(self.synthesis, PlaneSynthesisResult):
            raise TypeError("synthesis must be a PlaneSynthesisResult")
        expected_synthesis = synthesize_planes(
            self.layer.assessments,
            authority_ceiling=AuthorityCeiling.WITHHELD,
        )
        if self.synthesis != expected_synthesis:
            raise ValueError("layer synthesis is not canonical for its assessments")
        expected_hashes = tuple(
            assessment.content_sha256 for assessment in self.layer.assessments
        )
        if self.assessment_sha256s != expected_hashes:
            raise ValueError("assessment_sha256s do not match the layer assessments")

        if self.child_receipt is None:
            if self.child_receipt_sha256 is not None:
                raise ValueError("leaf layer cannot declare a child receipt hash")
        else:
            if not isinstance(self.child_receipt, DeepPlaneLayerReceipt):
                raise TypeError("child_receipt must be a DeepPlaneLayerReceipt")
            if self.child_receipt.layer.depth != self.layer.depth + 1:
                raise ValueError("child receipt must be exactly one depth deeper")
            if self.child_receipt.layer.parent_layer_id != self.layer.layer_id:
                raise ValueError("child receipt does not name this layer as parent")
            if self.child_receipt.layer.scope != self.layer.scope:
                raise ValueError("child receipt scope does not match its parent")
            if self.child_receipt_sha256 != self.child_receipt.content_sha256:
                raise ValueError("child_receipt_sha256 does not bind the child receipt")
        if self.authority_ceiling is not AuthorityCeiling.WITHHELD:
            raise ValueError("deep-plane layer authority must remain withheld")
        _validate_false_authorities(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DeepPlaneLayerReceipt:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data["authority_ceiling"] != AuthorityCeiling.WITHHELD.value:
            raise ValueError("deep-plane layer authority must remain withheld")
        _validate_serialized_false_authorities(data)
        child_payload = data["child_receipt"]
        child = (
            None
            if child_payload is None
            else DeepPlaneLayerReceipt.from_dict(child_payload)
        )
        return cls(
            layer=DeepPlaneLayerRequest.from_dict(data["layer"]),
            synthesis=PlaneSynthesisResult.from_dict(data["synthesis"]),
            assessment_sha256s=tuple(data["assessment_sha256s"]),
            child_receipt=child,
            child_receipt_sha256=data["child_receipt_sha256"],
        )


def _build_layer_receipt(
    layers: tuple[DeepPlaneLayerRequest, ...],
    index: int = 0,
) -> DeepPlaneLayerReceipt:
    layer = layers[index]
    child = (
        _build_layer_receipt(layers, index + 1)
        if index + 1 < len(layers)
        else None
    )
    synthesis = synthesize_planes(
        layer.assessments,
        authority_ceiling=AuthorityCeiling.WITHHELD,
    )
    return DeepPlaneLayerReceipt(
        layer=layer,
        synthesis=synthesis,
        assessment_sha256s=tuple(
            assessment.content_sha256 for assessment in layer.assessments
        ),
        child_receipt=child,
        child_receipt_sha256=None if child is None else child.content_sha256,
    )


def _receipt_id(
    request: DeepPlaneRuntimeRequest,
    root_layer_receipt: DeepPlaneLayerReceipt,
) -> str:
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "deep_plane_runtime_receipt_identity_v2",
                "candidate_state": _CANDIDATE_STATE,
                "request_sha256": request.content_sha256,
                "root_layer_receipt_sha256": root_layer_receipt.content_sha256,
                "scope_sha256": request.scope.content_sha256,
                "authority_ceiling": AuthorityCeiling.WITHHELD.value,
            }
        )
    ).hexdigest()
    return f"deep-plane-runtime-candidate:{digest}"


@dataclass(frozen=True, slots=True)
class DeepPlaneRuntimeReceipt(_CanonicalRecord):
    """Canonical recursive result with every downstream authority withheld."""

    SCHEMA_VERSION = "deep_plane_runtime_receipt_v2"

    receipt_id: str
    request: DeepPlaneRuntimeRequest
    root_layer_receipt: DeepPlaneLayerReceipt
    layer_receipt_sha256s: tuple[str, ...]
    candidate_state: str = field(default=_CANDIDATE_STATE, init=False)
    authority_ceiling: AuthorityCeiling = field(
        default=AuthorityCeiling.WITHHELD,
        init=False,
    )
    empirical_authority: bool = field(default=False, init=False)
    formula_generation_authorized: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    inventory_mutation_authorized: bool = field(default=False, init=False)
    runtime_integration_authorized: bool = field(default=False, init=False)
    production_runtime_admission_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    pass_fail_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    liking_authority: bool = field(default=False, init=False)
    beauty_authority: bool = field(default=False, init=False)
    hedonic_outcome_authority: bool = field(default=False, init=False)
    hedonic_score_authorized: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, DeepPlaneRuntimeRequest):
            raise TypeError("request must be a DeepPlaneRuntimeRequest")
        if not isinstance(self.root_layer_receipt, DeepPlaneLayerReceipt):
            raise TypeError("root_layer_receipt must be a DeepPlaneLayerReceipt")
        expected_root = _build_layer_receipt(self.request.layers)
        if self.root_layer_receipt != expected_root:
            raise ValueError("recursive layer receipt is not canonical for its request")
        expected_hashes = tuple(layer.content_sha256 for layer in self.layer_receipts)
        if self.layer_receipt_sha256s != expected_hashes:
            raise ValueError("layer_receipt_sha256s do not bind the recursive chain")
        expected_id = _receipt_id(self.request, self.root_layer_receipt)
        if self.receipt_id != expected_id:
            raise ValueError("receipt_id does not match the canonical receipt identity")
        if self.candidate_state != _CANDIDATE_STATE:
            raise ValueError("deep-plane runtime candidate state cannot be promoted")
        if self.authority_ceiling is not AuthorityCeiling.WITHHELD:
            raise ValueError("deep-plane runtime candidate authority must remain withheld")
        _validate_false_authorities(self)

    @property
    def layer_receipts(self) -> tuple[DeepPlaneLayerReceipt, ...]:
        values: list[DeepPlaneLayerReceipt] = []
        current: DeepPlaneLayerReceipt | None = self.root_layer_receipt
        while current is not None:
            values.append(current)
            current = current.child_receipt
        return tuple(values)

    @property
    def synthesis(self) -> PlaneSynthesisResult:
        """Return root synthesis for single-layer-compatible callers."""

        return self.root_layer_receipt.synthesis

    @property
    def scope(self) -> AssessmentScope:
        return self.request.scope

    @property
    def conflicts(self) -> tuple[SynthesisConflict, ...]:
        return tuple(
            conflict
            for layer in self.layer_receipts
            for conflict in layer.synthesis.conflicts
        )

    @property
    def unknowns(self) -> tuple[ScopedUnknown, ...]:
        return tuple(
            unknown
            for layer in self.layer_receipts
            for unknown in layer.synthesis.unknowns
        )

    @property
    def native_criteria(self) -> tuple[ScopedNativeCriterion, ...]:
        return tuple(
            criterion
            for layer in self.layer_receipts
            for criterion in layer.synthesis.native_criteria
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DeepPlaneRuntimeReceipt:
        data = _payload(payload, cls.SCHEMA_VERSION)
        if data["candidate_state"] != _CANDIDATE_STATE:
            raise ValueError("deep-plane runtime candidate state cannot be promoted")
        if data["authority_ceiling"] != AuthorityCeiling.WITHHELD.value:
            raise ValueError("deep-plane runtime candidate authority must remain withheld")
        _validate_serialized_false_authorities(data)
        return cls(
            receipt_id=data["receipt_id"],
            request=DeepPlaneRuntimeRequest.from_dict(data["request"]),
            root_layer_receipt=DeepPlaneLayerReceipt.from_dict(
                data["root_layer_receipt"]
            ),
            layer_receipt_sha256s=tuple(data["layer_receipt_sha256s"]),
        )


def execute_deep_plane_runtime_candidate(
    values: (
        Iterable[PlaneAssessment]
        | Iterable[DeepPlaneLayerRequest]
        | DeepPlaneRuntimeRequest
    ),
) -> DeepPlaneRuntimeReceipt:
    """Execute the recursive structural candidate without I/O or admission."""

    if isinstance(values, DeepPlaneRuntimeRequest):
        request = values
    else:
        items = tuple(values)
        if all(isinstance(item, PlaneAssessment) for item in items):
            assessments = cast(tuple[PlaneAssessment, ...], items)
            request = DeepPlaneRuntimeRequest(
                layers=(
                    DeepPlaneLayerRequest(
                        layer_id="layer:root",
                        depth=0,
                        parent_layer_id=None,
                        assessments=assessments,
                    ),
                )
            )
        elif all(isinstance(item, DeepPlaneLayerRequest) for item in items):
            request = DeepPlaneRuntimeRequest(
                layers=cast(tuple[DeepPlaneLayerRequest, ...], items)
            )
        else:
            raise TypeError(
                "runtime input must contain only PlaneAssessment values or only "
                "DeepPlaneLayerRequest values"
            )
    root_layer_receipt = _build_layer_receipt(request.layers)
    layer_receipts: list[DeepPlaneLayerReceipt] = []
    current: DeepPlaneLayerReceipt | None = root_layer_receipt
    while current is not None:
        layer_receipts.append(current)
        current = current.child_receipt
    return DeepPlaneRuntimeReceipt(
        receipt_id=_receipt_id(request, root_layer_receipt),
        request=request,
        root_layer_receipt=root_layer_receipt,
        layer_receipt_sha256s=tuple(
            layer.content_sha256 for layer in layer_receipts
        ),
    )


__all__ = [
    "DeepPlaneLayerReceipt",
    "DeepPlaneLayerRequest",
    "DeepPlaneRuntimeReceipt",
    "DeepPlaneRuntimeRequest",
    "MAX_RECURSIVE_LAYERS",
    "execute_deep_plane_runtime_candidate",
]
