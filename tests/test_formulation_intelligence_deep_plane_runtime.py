from __future__ import annotations

import builtins
import json
import os
import pathlib
import socket
import subprocess
import sys
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from engine.formulation_intelligence.admission import MANDATORY_AUTHORITY_EXCLUSIONS
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
    MAX_RECURSIVE_LAYERS,
    DeepPlaneLayerRequest,
    DeepPlaneRuntimeReceipt,
    DeepPlaneRuntimeRequest,
    execute_deep_plane_runtime_candidate,
)
from engine.formulation_intelligence.runtime_closure import (
    build_runtime_closure_from_config,
    load_runtime_closure_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "formulation_intelligence"
    / "deep_plane_runtime_candidate_v1.json"
)
SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "formulation_intelligence"
    / "deep_plane_runtime_request_v1.json"
)

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


def _scope() -> AssessmentScope:
    return AssessmentScope(
        target_scope="deep-plane:test-target",
        temporal_scope="opening-to-residue",
        matrix_scope="structural-only:no-physical-matrix",
    )


def _provenance(plane_id: PlaneId, layer_id: str = "root") -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=f"deep-plane:{layer_id}:{plane_id.value}",
        source_ref=f"test://deep-plane/{layer_id}/{plane_id.value}",
        evidence_class=EvidenceClass.HEURISTIC,
        independence_key=f"test-method:{layer_id}:{plane_id.value}",
        source_sha256=sha256(
            f"{layer_id}:{plane_id.value}".encode("utf-8")
        ).hexdigest(),
    )


def _assessment(
    plane_id: PlaneId,
    *,
    scope: AssessmentScope | None = None,
    layer_id: str = "root",
) -> PlaneAssessment:
    provenance = _provenance(plane_id, layer_id)
    conflict = (
        PlaneConflict(
            conflict_id=f"{layer_id}:relation:bridge-alternatives",
            claim_key="relation.bridge",
            alternatives=("continuous", "punctuated"),
            reason="both structural transitions remain plausible",
            provenance_refs=(provenance,),
        ),
    ) if plane_id is PlaneId.RELATION else ()
    unknown = (
        UnknownFact(
            unknown_id=f"{layer_id}:temporal:residue-continuity",
            field_key="temporal.residue_continuity",
            reason="no time-resolved observation",
            needed_evidence="a blinded time-resolved observation",
            provenance_refs=(provenance,),
        ),
    ) if plane_id is PlaneId.TEMPORAL else ()
    criterion = (
        ParetoCriterion(
            criterion_id=f"{layer_id}:experiment_information_gain",
            direction=CriterionDirection.MAXIMIZE,
            value=CriterionValue.unknown("no controlled comparison result"),
            unit="native structural scale",
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(provenance,),
        ),
    ) if plane_id is PlaneId.EXPERIMENT else ()
    claim = ScopedClaim(
        claim_id=f"claim:{layer_id}:{plane_id.value}",
        claim_key=f"plane.{plane_id.value}",
        claim_value=f"{layer_id} structural packet for {plane_id.value}",
        claim_kind=ClaimKind.HYPOTHESIS,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(provenance,),
    )
    return PlaneAssessment(
        assessment_id=f"assessment:{layer_id}:{plane_id.value}",
        module_id=f"test-module:{layer_id}:{plane_id.value}",
        plane_id=plane_id,
        scope=scope or _scope(),
        claims=(claim,),
        support_intervals=(),
        conflicts=conflict,
        unknowns=unknown,
        failure_modes=(),
        proposed_experiments=(),
        provenance_refs=(provenance,),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        freshness_hashes=(provenance.source_sha256,),
        native_criteria=criterion,
    )


def _all_planes(layer_id: str = "root") -> tuple[PlaneAssessment, ...]:
    return tuple(_assessment(plane_id, layer_id=layer_id) for plane_id in PlaneId)


def _recursive_layers() -> tuple[DeepPlaneLayerRequest, ...]:
    return (
        DeepPlaneLayerRequest("layer:surface", 0, None, _all_planes("surface")),
        DeepPlaneLayerRequest(
            "layer:structure",
            1,
            "layer:surface",
            _all_planes("structure"),
        ),
        DeepPlaneLayerRequest(
            "layer:residue",
            2,
            "layer:structure",
            _all_planes("residue"),
        ),
    )


def test_successful_all_plane_execution_preserves_structural_outputs() -> None:
    receipt = execute_deep_plane_runtime_candidate(_all_planes())

    assert {item.plane_id for item in receipt.request.assessments} == set(PlaneId)
    assert len(receipt.request.assessments) == 13
    assert receipt.scope == _scope()
    assert receipt.authority_ceiling is AuthorityCeiling.WITHHELD
    assert receipt.synthesis.authority_ceiling is AuthorityCeiling.WITHHELD
    assert receipt.candidate_state == "future_candidate_not_validated"
    assert receipt.receipt_id.startswith("deep-plane-runtime-candidate:")
    assert len(receipt.receipt_id.rpartition(":")[2]) == 64
    assert len(receipt.content_sha256) == 64
    assert receipt.conflicts
    assert receipt.conflicts[0].explicit_conflict_ids == (
        "root:relation:bridge-alternatives",
    )
    assert receipt.unknowns[0].unknown.unknown_id == (
        "root:temporal:residue-continuity"
    )
    assert receipt.native_criteria[0].criterion.criterion_id == (
        "root:experiment_information_gain"
    )


def test_recursive_layers_bind_every_deep_result_into_the_root_receipt() -> None:
    receipt = execute_deep_plane_runtime_candidate(_recursive_layers())

    assert [item.layer.layer_id for item in receipt.layer_receipts] == [
        "layer:surface",
        "layer:structure",
        "layer:residue",
    ]
    assert [item.layer.depth for item in receipt.layer_receipts] == [0, 1, 2]
    assert all(
        len(layer.layer.assessments) == len(PlaneId)
        for layer in receipt.layer_receipts
    )
    assert receipt.layer_receipts[0].child_receipt_sha256 == (
        receipt.layer_receipts[1].content_sha256
    )
    assert receipt.layer_receipts[1].child_receipt_sha256 == (
        receipt.layer_receipts[2].content_sha256
    )
    assert receipt.layer_receipts[2].child_receipt_sha256 is None
    assert len(receipt.conflicts) == 3
    assert len(receipt.unknowns) == 3
    assert len(receipt.native_criteria) == 3
    assert all(
        len(layer.synthesis.provenance_refs) == len(PlaneId)
        for layer in receipt.layer_receipts
    )

    permuted = execute_deep_plane_runtime_candidate(
        tuple(
            replace(layer, assessments=tuple(reversed(layer.assessments)))
            for layer in _recursive_layers()
        )
    )
    assert permuted == receipt
    assert permuted.receipt_id == receipt.receipt_id

    changed_layers = list(_recursive_layers())
    deepest = list(changed_layers[-1].assessments)
    identity_index = next(
        index
        for index, assessment in enumerate(deepest)
        if assessment.plane_id is PlaneId.IDENTITY
    )
    identity = deepest[identity_index]
    changed_claim = replace(
        identity.claims[0],
        claim_value="deep residue identity changed",
    )
    deepest[identity_index] = replace(identity, claims=(changed_claim,))
    changed_layers[-1] = replace(changed_layers[-1], assessments=tuple(deepest))
    changed = execute_deep_plane_runtime_candidate(changed_layers)

    assert changed.layer_receipts[-1].content_sha256 != (
        receipt.layer_receipts[-1].content_sha256
    )
    assert changed.root_layer_receipt.content_sha256 != (
        receipt.root_layer_receipt.content_sha256
    )
    assert changed.receipt_id != receipt.receipt_id


def test_missing_duplicate_and_scope_mismatched_planes_fail_closed() -> None:
    assessments = _all_planes()
    with pytest.raises(ValueError, match="missing required planes"):
        execute_deep_plane_runtime_candidate(assessments[:-1])
    with pytest.raises(ValueError, match="duplicate planes"):
        execute_deep_plane_runtime_candidate((*assessments, assessments[0]))

    mismatched = list(assessments)
    mismatched[-1] = replace(
        mismatched[-1],
        scope=AssessmentScope("other-target", "opening-to-residue", "structural-only"),
    )
    with pytest.raises(ValueError, match="one consistent exact scope"):
        execute_deep_plane_runtime_candidate(mismatched)


def test_recursive_layer_order_parent_and_scope_are_exact() -> None:
    layers = _recursive_layers()
    with pytest.raises(ValueError, match="ordered from depth zero"):
        execute_deep_plane_runtime_candidate((layers[1], layers[0], layers[2]))

    wrong_parent = replace(layers[1], parent_layer_id="layer:wrong")
    with pytest.raises(ValueError, match="immediate shallower parent"):
        execute_deep_plane_runtime_candidate((layers[0], wrong_parent, layers[2]))

    other_scope_assessments = tuple(
        replace(
            assessment,
            scope=AssessmentScope(
                "other-target",
                "opening-to-residue",
                "structural-only:no-physical-matrix",
            ),
        )
        for assessment in layers[2].assessments
    )
    other_scope = replace(layers[2], assessments=other_scope_assessments)
    with pytest.raises(ValueError, match="all recursive layers"):
        execute_deep_plane_runtime_candidate((layers[0], layers[1], other_scope))


def test_recursive_depth_is_bounded_before_receipt_recursion() -> None:
    layers = tuple(
        DeepPlaneLayerRequest(
            layer_id=f"layer:{depth}",
            depth=depth,
            parent_layer_id=None if depth == 0 else f"layer:{depth - 1}",
            assessments=_all_planes(f"depth-{depth}"),
        )
        for depth in range(MAX_RECURSIVE_LAYERS + 1)
    )

    with pytest.raises(ValueError, match="safe maximum"):
        execute_deep_plane_runtime_candidate(layers)


def test_input_order_is_invariant() -> None:
    assessments = _all_planes()
    forward = execute_deep_plane_runtime_candidate(assessments)
    reverse = execute_deep_plane_runtime_candidate(reversed(assessments))

    assert reverse == forward
    assert reverse.as_dict() == forward.as_dict()
    assert reverse.receipt_id == forward.receipt_id
    assert reverse.content_sha256 == forward.content_sha256


def test_serialization_is_closed_and_rejects_deep_tampering() -> None:
    receipt = execute_deep_plane_runtime_candidate(_recursive_layers())
    payload = json.loads(json.dumps(receipt.as_dict(), sort_keys=True))

    assert DeepPlaneRuntimeReceipt.from_dict(payload) == receipt
    assert DeepPlaneRuntimeRequest.from_dict(receipt.request.as_dict()) == receipt.request

    for field_name in _AUTHORITY_FLAGS:
        promoted = deepcopy(payload)
        promoted[field_name] = True
        with pytest.raises(ValueError, match="must remain false"):
            DeepPlaneRuntimeReceipt.from_dict(promoted)

        promoted_layer = deepcopy(payload)
        promoted_layer["root_layer_receipt"][field_name] = True
        with pytest.raises(ValueError, match="must remain false"):
            DeepPlaneRuntimeReceipt.from_dict(promoted_layer)

    forged_id = deepcopy(payload)
    forged_id["receipt_id"] = "deep-plane-runtime-candidate:" + "0" * 64
    with pytest.raises(ValueError, match="receipt_id"):
        DeepPlaneRuntimeReceipt.from_dict(forged_id)

    forged_synthesis = deepcopy(payload)
    forged_synthesis["root_layer_receipt"]["synthesis"]["unknowns"] = []
    with pytest.raises(ValueError, match="canonical"):
        DeepPlaneRuntimeReceipt.from_dict(forged_synthesis)

    forged_deep_child = deepcopy(payload)
    deep_child = forged_deep_child["root_layer_receipt"]["child_receipt"]
    deep_child["child_receipt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="child_receipt_sha256"):
        DeepPlaneRuntimeReceipt.from_dict(forged_deep_child)

    removed_deep_unknown = deepcopy(payload)
    leaf = removed_deep_unknown["root_layer_receipt"]["child_receipt"][
        "child_receipt"
    ]
    leaf["synthesis"]["unknowns"] = []
    with pytest.raises(ValueError, match="canonical"):
        DeepPlaneRuntimeReceipt.from_dict(removed_deep_unknown)

    with_extra = deepcopy(payload)
    with_extra["unexpected"] = "rejected"
    with pytest.raises(ValueError, match="closed schema"):
        DeepPlaneRuntimeReceipt.from_dict(with_extra)

    with pytest.raises(FrozenInstanceError):
        receipt.receipt_id = "mutated"  # type: ignore[misc]


def test_candidate_import_is_silent_in_a_fresh_process() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import engine.formulation_intelligence.deep_plane_runtime",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""


def test_runtime_call_performs_no_file_network_or_process_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layers = _recursive_layers()

    def denied(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("runtime candidate attempted forbidden I/O")

    for target, name in (
        (builtins, "open"),
        (os, "open"),
        (os, "popen"),
        (os, "system"),
        (pathlib.Path, "open"),
        (pathlib.Path, "read_bytes"),
        (pathlib.Path, "read_text"),
        (pathlib.Path, "write_bytes"),
        (pathlib.Path, "write_text"),
        (socket, "create_connection"),
        (socket, "socket"),
        (subprocess, "Popen"),
        (subprocess, "call"),
        (subprocess, "check_call"),
        (subprocess, "check_output"),
        (subprocess, "run"),
    ):
        monkeypatch.setattr(target, name, denied)

    receipt = execute_deep_plane_runtime_candidate(layers)

    assert len(receipt.layer_receipts) == 3
    assert all(len(item.layer.assessments) == 13 for item in receipt.layer_receipts)


def test_every_authority_flag_is_hard_false() -> None:
    receipt = execute_deep_plane_runtime_candidate(_recursive_layers())

    assert all(getattr(receipt, field_name) is False for field_name in _AUTHORITY_FLAGS)
    assert all(
        getattr(layer, field_name) is False
        for layer in receipt.layer_receipts
        for field_name in _AUTHORITY_FLAGS
    )
    assert receipt.authority_ceiling is AuthorityCeiling.WITHHELD
    assert receipt.synthesis.formula_generation_authorized is False
    assert receipt.synthesis.inventory_mutation_authorized is False
    assert receipt.synthesis.compounding_authorized is False
    assert receipt.synthesis.sensory_authority is False
    assert receipt.synthesis.safety_authority is False
    assert receipt.synthesis.release_authority is False


def test_candidate_config_and_request_schema_load_as_closed_json() -> None:
    config = load_runtime_closure_config(CONFIG_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    receipt = execute_deep_plane_runtime_candidate(_recursive_layers())
    validator = Draft202012Validator(schema)
    validator.check_schema(schema)
    validator.validate(receipt.request.as_dict())
    validator.validate(receipt.as_dict())

    assert config.package_prefix == "engine.formulation_intelligence"
    assert config.closure_id == "closure:deep-plane-runtime-candidate:v1"
    assert {item.module_name for item in config.modules} == {
        "engine.formulation_intelligence",
        "engine.formulation_intelligence.deep_plane_runtime",
    }
    assert all(item.authority_ceiling is AuthorityCeiling.WITHHELD for item in config.modules)
    assert all(
        set(MANDATORY_AUTHORITY_EXCLUSIONS).issubset(item.exclusions)
        for item in config.modules
    )
    request_schema = schema["$defs"]["runtime_request"]
    assert request_schema["additionalProperties"] is False
    assert request_schema["properties"]["layers"]["minItems"] == 1
    assert request_schema["properties"]["layers"]["maxItems"] == (
        MAX_RECURSIVE_LAYERS
    )
    assessments = schema["$defs"]["assessment_array"]
    assert assessments["minItems"] == len(PlaneId)
    assert assessments["maxItems"] == len(PlaneId)
    assert len(assessments["allOf"]) == len(PlaneId)

    malformed_request = deepcopy(receipt.request.as_dict())
    malformed_request["layers"][0]["assessments"][0]["claims"] = [
        {"junk": True}
    ]
    with pytest.raises(ValidationError):
        validator.validate(malformed_request)

    malformed_receipt = deepcopy(receipt.as_dict())
    malformed_receipt["root_layer_receipt"]["unexpected"] = "rejected"
    with pytest.raises(ValidationError):
        validator.validate(malformed_receipt)


def test_real_workspace_transitive_closure_is_exact_and_deterministic() -> None:
    config = load_runtime_closure_config(CONFIG_PATH)
    first = build_runtime_closure_from_config(PROJECT_ROOT, config)
    second = build_runtime_closure_from_config(PROJECT_ROOT, config)

    assert second == first
    assert second.content_sha256 == first.content_sha256
    assert {item.module_id for item in first.module_manifests} == {
        "deep-plane-package-init-candidate",
        "deep-plane-runtime-candidate",
    }
    assert all(
        item.authority_ceiling is AuthorityCeiling.WITHHELD
        for item in first.module_manifests
    )
    assert all(
        set(MANDATORY_AUTHORITY_EXCLUSIONS).issubset(item.exclusions)
        for item in first.module_manifests
    )
    artifact_paths = {
        item.artifact_path for item in first.artifact_closure.artifacts
    }
    assert artifact_paths == {
        "configs/formulation_intelligence/deep_plane_runtime_candidate_v1.json",
        "docs/superpowers/specs/2026-08-31-perfume-intelligence-plane-synthesis-design.md",
        "engine/formulation_intelligence/__init__.py",
        "engine/formulation_intelligence/contracts.py",
        "engine/formulation_intelligence/deep_plane_runtime.py",
        "engine/formulation_intelligence/plane_synthesis.py",
        "schemas/formulation_intelligence/deep_plane_runtime_request_v1.json",
    }
