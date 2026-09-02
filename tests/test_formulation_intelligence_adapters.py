from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.formulation_intelligence.adapters import (
    AdapterAdmissionState,
    ClosureRelation,
    FieldDisposition,
    ImportClosureEntry,
    LegacyAdapterDefinition,
    LegacyAdapterResult,
    LegacyFieldRule,
    LegacySourceStateClass,
    adapt_legacy_output,
    verify_import_closure,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_tree(tmp_path: Path) -> tuple[Path, tuple[ImportClosureEntry, ...]]:
    root = tmp_path / "legacy_topology.py"
    dependency = tmp_path / "legacy_contract.py"
    root.write_text("from legacy_contract import STATE\n", encoding="utf-8")
    dependency.write_text('STATE = "FUTURE_CANDIDATE_NOT_VALIDATED"\n', encoding="utf-8")
    return root, (
        ImportClosureEntry(
            relative_path="legacy_topology.py",
            sha256=_digest(root),
            relation=ClosureRelation.SOURCE_ROOT,
        ),
        ImportClosureEntry(
            relative_path="legacy_contract.py",
            sha256=_digest(dependency),
            relation=ClosureRelation.DIRECT_IMPORT,
        ),
    )


def _definition(tmp_path: Path) -> LegacyAdapterDefinition:
    source, closure = _source_tree(tmp_path)
    source_sha256 = _digest(source)
    return LegacyAdapterDefinition(
        adapter_id="perceptual-topology-read-only-v1",
        source_module_id="universal-perceptual-topology-core",
        source_path="legacy_topology.py",
        source_schema_version="universal_perceptual_topology_core_v1",
        source_state="FUTURE_CANDIDATE_NOT_VALIDATED",
        source_state_class=LegacySourceStateClass.FUTURE,
        adapter_admission_state=AdapterAdmissionState.QUARANTINED,
        plane_id=PlaneId.SPATIAL_COMPOSITION,
        source_authority_ceiling=AuthorityCeiling.DESIGN_ONLY,
        adapter_authority_ceiling=AuthorityCeiling.HYPOTHESIS_ONLY,
        import_closure=closure,
        transitive_closure_complete=True,
        source_provenance=(
            ProvenanceRef(
                provenance_id="legacy-topology-source",
                source_ref="legacy_topology.py",
                evidence_class=EvidenceClass.COMPUTATIONAL_MODEL,
                independence_key="legacy-topology-source",
                source_sha256=source_sha256,
            ),
        ),
        subject_field="subject",
        target_scope_field="target_scope",
        temporal_scope_field="temporal_scope",
        matrix_scope_field="matrix_scope",
        condition_field="condition",
        output_state_field="state",
        field_rules=(
            LegacyFieldRule(
                source_field="layers",
                disposition=FieldDisposition.CLAIM,
                claim_key="topology_layer",
                claim_kind=ClaimKind.HYPOTHESIS,
                cardinality=ClaimCardinality.ORDERED_MEMBER,
            ),
            LegacyFieldRule(
                source_field="unknown_oav_basis",
                disposition=FieldDisposition.UNKNOWN,
                claim_key="oav_basis",
                reason="legacy output does not bind measured headspace or exact ODT",
                needed_evidence="bound gas evidence and threshold evidence",
            ),
            LegacyFieldRule(
                source_field="shape_alternatives",
                disposition=FieldDisposition.CONFLICT,
                claim_key="shape_hypothesis",
                reason="legacy output preserves unresolved shape alternatives",
            ),
            LegacyFieldRule(
                source_field="beauty_score",
                disposition=FieldDisposition.EXCLUDE,
                reason="legacy scalar is quarantined and has no hedonic authority",
            ),
        ),
    )


def _payload() -> dict[str, object]:
    return {
        "schema_version": "universal_perceptual_topology_core_v1",
        "subject": "  Magnolia / orris subject  ",
        "target_scope": "TARGET:Magnolia-Orris",
        "temporal_scope": "opening -> heart -> drydown",
        "matrix_scope": "ethanol; exact concentration UNKNOWN",
        "condition": "Bangkok 35 C; predicted, not observed",
        "state": "DESIGN_READY_NOT_EMPIRICAL",
        "layers": ["luminous floral surface", "mineral orris shadow"],
        "unknown_oav_basis": None,
        "shape_alternatives": ["narrow luminous column", "wide translucent field"],
        "beauty_score": 87.25,
    }


def test_adapter_is_lazy_and_does_not_import_heavy_or_legacy_modules() -> None:
    repository = Path(__file__).resolve().parents[1]
    code = """
import sys
import engine.formulation_intelligence.adapters
forbidden = ('torch', 'faiss', 'sentence_transformers', 'matplotlib',
             'engine.pipeline.formula_state', 'engine.perception.perceptual_topology')
loaded = [name for name in forbidden if name in sys.modules]
if loaded:
    raise SystemExit(','.join(loaded))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_adapter_preserves_state_context_payload_and_authority_ceiling(
    tmp_path: Path,
) -> None:
    definition = _definition(tmp_path)
    payload = _payload()

    result = adapt_legacy_output(definition, payload, repository_root=tmp_path)

    assert result.definition.source_state == "FUTURE_CANDIDATE_NOT_VALIDATED"
    assert result.definition.adapter_admission_state is AdapterAdmissionState.QUARANTINED
    assert result.source_output_state == "DESIGN_READY_NOT_EMPIRICAL"
    assert result.context.subject == "  Magnolia / orris subject  "
    assert result.context.condition == "Bangkok 35 C; predicted, not observed"
    assert json.loads(result.source_payload_canonical_json) == payload
    assert result.assessment.plane_id is PlaneId.SPATIAL_COMPOSITION
    assert result.assessment.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY
    assert all(
        claim.authority_ceiling is AuthorityCeiling.HYPOTHESIS_ONLY
        for claim in result.assessment.claims
    )
    assert tuple(claim.order_index for claim in result.assessment.claims) == (0, 1)
    assert not result.assessment.support_intervals
    assert not result.assessment.native_criteria
    assert result.assessment.unknowns[0].field_key == "oav_basis"
    assert result.assessment.conflicts[0].alternatives == (
        "narrow luminous column",
        "wide translucent field",
    )
    assert result.quarantined_fields[0].source_field == "beauty_score"
    assert result.quarantined_fields[0].canonical_value_json == "87.25"
    assert result.formula_authority is False
    assert result.sensory_authority is False
    assert result.safety_authority is False
    assert result.release_authority is False


def test_closed_source_schema_rejects_unknown_missing_and_wrong_version(
    tmp_path: Path,
) -> None:
    definition = _definition(tmp_path)

    extra = _payload()
    extra["surprise"] = "unmapped field"
    with pytest.raises(ValueError, match="closed source schema"):
        adapt_legacy_output(definition, extra, repository_root=tmp_path)

    missing = _payload()
    del missing["condition"]
    with pytest.raises(ValueError, match="closed source schema"):
        adapt_legacy_output(definition, missing, repository_root=tmp_path)

    wrong_version = _payload()
    wrong_version["schema_version"] = "future_schema_v2"
    with pytest.raises(ValueError, match="source schema_version"):
        adapt_legacy_output(definition, wrong_version, repository_root=tmp_path)


def test_hash_bound_import_closure_fails_after_any_source_change(tmp_path: Path) -> None:
    definition = _definition(tmp_path)
    verify_import_closure(definition, tmp_path)
    (tmp_path / "legacy_contract.py").write_text("STATE = 'CHANGED'\n", encoding="utf-8")

    with pytest.raises(ValueError, match="import closure hash mismatch"):
        verify_import_closure(definition, tmp_path)
    with pytest.raises(ValueError, match="import closure hash mismatch"):
        adapt_legacy_output(definition, _payload(), repository_root=tmp_path)


def test_every_source_field_must_be_accounted_for_exactly_once(tmp_path: Path) -> None:
    definition = _definition(tmp_path)
    duplicate_rule = LegacyFieldRule(
        source_field="layers",
        disposition=FieldDisposition.EXCLUDE,
        reason="duplicate mapping must fail",
    )

    with pytest.raises(ValueError, match="unique source_field"):
        LegacyAdapterDefinition(
            **{
                **definition.constructor_dict(),
                "field_rules": (*definition.field_rules, duplicate_rule),
            }
        )


def test_legacy_scalar_is_never_promoted_to_a_pareto_or_hedonic_criterion(
    tmp_path: Path,
) -> None:
    result = adapt_legacy_output(_definition(tmp_path), _payload(), repository_root=tmp_path)

    assert result.assessment.native_criteria == ()
    assert all(claim.claim_key != "beauty_score" for claim in result.assessment.claims)
    assert "87.25" in result.source_payload_canonical_json
    assert result.quarantined_fields[0].reason == (
        "legacy scalar is quarantined and has no hedonic authority"
    )


def test_explicit_source_hold_is_preserved_and_forces_withheld_authority(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["state"] = "HOLD_MISSING_EMPIRICAL_BINDING"

    result = adapt_legacy_output(
        _definition(tmp_path),
        payload,
        repository_root=tmp_path,
    )

    assert result.source_output_state == "HOLD_MISSING_EMPIRICAL_BINDING"
    assert result.assessment.authority_ceiling is AuthorityCeiling.WITHHELD
    assert all(
        claim.authority_ceiling is AuthorityCeiling.WITHHELD
        for claim in result.assessment.claims
    )
    assert "source output state is HOLD_MISSING_EMPIRICAL_BINDING" in (
        result.assessment.failure_modes
    )


def test_collection_claim_conversion_rejects_lossy_or_ambiguous_values(
    tmp_path: Path,
) -> None:
    definition = _definition(tmp_path)
    scalar_for_collection = _payload()
    scalar_for_collection["layers"] = "one untyped layer"
    with pytest.raises(TypeError, match="ordered_member.*array"):
        adapt_legacy_output(definition, scalar_for_collection, repository_root=tmp_path)

    duplicate_members = _payload()
    duplicate_members["layers"] = ["same", "same"]
    with pytest.raises(ValueError, match="unique canonical members"):
        adapt_legacy_output(definition, duplicate_members, repository_root=tmp_path)


@pytest.mark.parametrize(
    "source_state_class",
    (
        LegacySourceStateClass.HISTORICAL,
        LegacySourceStateClass.UNSUPPORTED,
        LegacySourceStateClass.RETIRED,
    ),
)
def test_historical_unsupported_and_retired_sources_are_forced_to_withheld(
    tmp_path: Path,
    source_state_class: LegacySourceStateClass,
) -> None:
    current = _definition(tmp_path)

    with pytest.raises(ValueError, match="must remain withheld"):
        LegacyAdapterDefinition(
            **{
                **current.constructor_dict(),
                "source_state": f"EXACT_{source_state_class.value}_STATE",
                "source_state_class": source_state_class,
                "adapter_authority_ceiling": AuthorityCeiling.HYPOTHESIS_ONLY,
            }
        )


def test_result_round_trip_is_strict_and_content_addressed(tmp_path: Path) -> None:
    result = adapt_legacy_output(_definition(tmp_path), _payload(), repository_root=tmp_path)
    restored = LegacyAdapterResult.from_dict(result.as_dict())

    assert restored == result
    assert restored.content_sha256 == result.content_sha256

    unexpected = result.as_dict()
    unexpected["unexpected"] = "not part of legacy_adapter_result_v1"
    with pytest.raises(ValueError, match="closed schema"):
        LegacyAdapterResult.from_dict(unexpected)

    tampered = result.as_dict()
    tampered["source_payload_canonical_json"] = tampered[
        "source_payload_canonical_json"
    ].replace("87.25", "99.0")
    with pytest.raises(ValueError, match="source_payload_sha256"):
        LegacyAdapterResult.from_dict(tampered)


def test_deserialization_rederives_hold_authority_and_governance(tmp_path: Path) -> None:
    payload = _payload()
    payload["state"] = "HOLD_MISSING_EMPIRICAL_BINDING"
    result = adapt_legacy_output(_definition(tmp_path), payload, repository_root=tmp_path)

    promoted = result.as_dict()
    promoted["assessment"]["authority_ceiling"] = AuthorityCeiling.HYPOTHESIS_ONLY.value
    for claim in promoted["assessment"]["claims"]:
        claim["authority_ceiling"] = AuthorityCeiling.HYPOTHESIS_ONLY.value
    with pytest.raises(ValueError, match="does not match derived state"):
        LegacyAdapterResult.from_dict(promoted)

    stripped = result.as_dict()
    stripped["assessment"]["failure_modes"] = []
    stripped["quarantined_fields"] = []
    with pytest.raises(ValueError, match="does not match derived state"):
        LegacyAdapterResult.from_dict(stripped)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("scope", {"schema_version": "assessment_scope_v1", "target_scope": "forged", "temporal_scope": "opening -> heart -> drydown", "matrix_scope": "ethanol; exact concentration unknown"}),
        ("freshness_hashes", ["d" * 64]),
    ),
)
def test_deserialization_rejects_forged_derived_assessment_fields(
    tmp_path: Path,
    field_name: str,
    replacement: object,
) -> None:
    result = adapt_legacy_output(_definition(tmp_path), _payload(), repository_root=tmp_path)
    tampered = result.as_dict()
    tampered["assessment"][field_name] = replacement

    with pytest.raises(ValueError, match="does not match derived state"):
        LegacyAdapterResult.from_dict(tampered)


@pytest.mark.parametrize(
    "authority_field",
    ("formula_authority", "sensory_authority", "safety_authority", "release_authority"),
)
def test_deserialization_never_accepts_promoted_top_level_authority(
    tmp_path: Path,
    authority_field: str,
) -> None:
    result = adapt_legacy_output(_definition(tmp_path), _payload(), repository_root=tmp_path)
    tampered = result.as_dict()
    tampered[authority_field] = True

    with pytest.raises(ValueError, match="cannot be promoted by an adapter"):
        LegacyAdapterResult.from_dict(tampered)
