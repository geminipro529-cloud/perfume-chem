from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from engine.solforge.protocols import (
    PROTOCOL_AUTHORITY_FLAGS,
    ParticipantScopeV2,
    PhysicalEvidenceIntakeError,
    PreregisteredProtocolV1,
    PreregisteredProtocolV2,
    ProtocolAnalysisUnitV2,
    ProtocolDesignClass,
    ProtocolEndpointV2,
    build_protocol,
    build_protocol_v2,
    ingest_physical_results,
    load_protocol_templates,
    load_protocol_templates_v2,
    validate_protocol,
    validate_protocol_v2,
)
from engine.solforge.protocols import (
    main as protocol_main,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "data/research/solforge/protocol_templates_v1.json"
TEMPLATES_V2 = ROOT / "data/research/solforge/protocol_templates_v2.json"


def _bindings() -> dict[str, object]:
    return {
        "program_sha256": "a" * 64,
        "formula_build_sha256": "b" * 64,
        "dose_receipt_sha256": "c" * 64,
        "inventory_sha256": "d" * 64,
        "sample_sha256": {
            "CONTROL": "1" * 64,
            "A": "2" * 64,
            "B": "3" * 64,
            "A_X_B": "4" * 64,
        },
    }


def _bindings_v2(
    *,
    participant_scope: str = "OWNER",
    assessor_ids: list[str] | None = None,
    within_sniff: bool = False,
) -> dict[str, object]:
    assessors = assessor_ids or (["OWNER-1"] if participant_scope == "OWNER" else ["A1", "A2"])
    return {
        "program_sha256": "a" * 64,
        "formula_build_sha256": "b" * 64,
        "dose_receipt_sha256": "c" * 64,
        "inventory_sha256": "d" * 64,
        "execution_plan_sha256": "e" * 64,
        "deviation_policy_sha256": "f" * 64,
        "sample_sha256": {"CONTROL": "1" * 64, "TREATMENT": "2" * 64},
        "participant_scope": participant_scope,
        "assessor_ids": assessors,
        "repeat_ids": ["R1", "R2"],
        "session_ids": ["S1", "S2"],
        "timepoints_seconds": [0.0, 3600.0],
        "apparatus_id": "QUALIFIED-BLOTTER-RACK",
        "apparatus_qualification_sha256": "3" * 64,
        "within_sniff": within_sniff,
        "within_sniff_apparatus_qualified": within_sniff,
        "within_sniff_timing_protocol_qualified": within_sniff,
        "timing_protocol_sha256": "4" * 64 if within_sniff else None,
        "timing_clock_source": "MONOTONIC-LAB-CLOCK" if within_sniff else None,
        "timing_tolerance_ms": 50.0 if within_sniff else None,
    }


def test_six_design_templates_build_deterministically_and_have_no_authority() -> None:
    templates = load_protocol_templates(TEMPLATES)
    assert {template.design_class for template in templates} == set(ProtocolDesignClass)
    for template in templates:
        first = build_protocol(template, _bindings())
        second = build_protocol(template, _bindings())
        assert first.canonical_bytes() == second.canonical_bytes()
        assert validate_protocol(first) == ()
        assert first.as_dict()["authority_flags"] == PROTOCOL_AUTHORITY_FLAGS
        assert first.status == "PREREGISTERED_NOT_EXECUTED"


def test_two_factor_template_has_complete_constant_total_arms() -> None:
    template = next(
        item
        for item in load_protocol_templates(TEMPLATES)
        if item.design_class is ProtocolDesignClass.TWO_FACTOR_FOUR_ARM_MIXTURE
    )
    protocol = build_protocol(template, _bindings())
    assert tuple(arm.arm_id for arm in protocol.arms) == (
        "CONTROL",
        "A",
        "B",
        "A_X_B",
    )
    assert len({arm.total_active_mass_g for arm in protocol.arms}) == 1


def test_protocol_includes_blinding_order_washout_repeats_and_stops() -> None:
    protocol = build_protocol(load_protocol_templates(TEMPLATES)[0], _bindings())
    assert all(arm.blind_code.startswith("SF-") for arm in protocol.arms)
    assert protocol.schedule_sha256
    assert protocol.washout_seconds > 0
    assert protocol.repeat_count >= 2
    assert protocol.assessor_scope
    assert protocol.stopping_rule
    assert protocol.safety_stop
    assert protocol.primary_endpoint != protocol.secondary_endpoints


def test_protocol_validation_rejects_missing_control_and_unmatched_total() -> None:
    protocol = build_protocol(load_protocol_templates(TEMPLATES)[2], _bindings())
    no_control = replace(protocol, arms=protocol.arms[1:])
    assert "CONTROL" in " ".join(validate_protocol(no_control))
    changed_arm = replace(protocol.arms[-1], total_active_mass_g=2.0)
    unmatched = replace(protocol, arms=(*protocol.arms[:-1], changed_arm))
    assert "matched total" in " ".join(validate_protocol(unmatched))


def test_physical_intake_rejects_synthetic_or_post_outcome_protocol_change() -> None:
    protocol = build_protocol(load_protocol_templates(TEMPLATES)[0], _bindings())
    result = {
        "protocol_sha256": protocol.record_sha256,
        "formula_build_sha256": protocol.formula_build_sha256,
        "dose_receipt_sha256": protocol.dose_receipt_sha256,
        "inventory_sha256": protocol.inventory_sha256,
        "sample_sha256": dict(protocol.sample_sha256),
        "schedule_sha256": protocol.schedule_sha256,
        "assessor_ids": ["A1", "A2"],
        "observations": [],
        "test_only": True,
        "synthetic": True,
    }
    with pytest.raises(PhysicalEvidenceIntakeError, match="synthetic"):
        ingest_physical_results(protocol, result)
    result.update(test_only=False, synthetic=False, protocol_sha256="f" * 64)
    with pytest.raises(PhysicalEvidenceIntakeError, match="protocol hash"):
        ingest_physical_results(protocol, result)


def test_missing_observations_remain_missing_in_physical_intake() -> None:
    protocol = build_protocol(load_protocol_templates(TEMPLATES)[0], _bindings())
    result = {
        "protocol_sha256": protocol.record_sha256,
        "formula_build_sha256": protocol.formula_build_sha256,
        "dose_receipt_sha256": protocol.dose_receipt_sha256,
        "inventory_sha256": protocol.inventory_sha256,
        "sample_sha256": dict(protocol.sample_sha256),
        "schedule_sha256": protocol.schedule_sha256,
        "assessor_ids": ["A1", "A2"],
        "observations": [],
        "expected_observation_ids": ["O1", "O2"],
        "test_only": False,
        "synthetic": False,
    }
    receipt = ingest_physical_results(protocol, result)
    assert receipt["missing_observation_ids"] == ["O1", "O2"]
    assert receipt["observations"] == []
    assert receipt["physical_claim_authorized"] is False


def test_template_file_has_closed_nonauthority() -> None:
    payload = json.loads(TEMPLATES.read_text(encoding="utf-8"))
    assert payload["authority_flags"] == PROTOCOL_AUTHORITY_FLAGS


def test_v2_templates_cover_each_separate_endpoint_and_no_authority() -> None:
    templates = load_protocol_templates_v2(TEMPLATES_V2)
    endpoints = {
        endpoint
        for template in templates
        for endpoint in (template.primary_endpoint, *template.secondary_endpoints)
    }

    assert endpoints == set(ProtocolEndpointV2)
    assert json.loads(TEMPLATES_V2.read_text(encoding="utf-8"))["authority_flags"] == (
        PROTOCOL_AUTHORITY_FLAGS
    )


def test_v2_build_is_deterministic_closed_and_round_trips() -> None:
    template = load_protocol_templates_v2(TEMPLATES_V2)[0]
    first = build_protocol_v2(template, _bindings_v2())
    second = build_protocol_v2(template, _bindings_v2())
    payload = first.as_dict()

    assert first.canonical_bytes() == second.canonical_bytes()
    assert PreregisteredProtocolV2.from_dict(payload) == first
    assert validate_protocol_v2(first) == ()
    assert payload["authority_flags"] == PROTOCOL_AUTHORITY_FLAGS
    assert first.participant_scope is ParticipantScopeV2.OWNER
    assert first.assessor_ids == ("OWNER-1",)
    assert first.repeat_ids == ("R1", "R2")
    assert first.session_ids == ("S1", "S2")
    assert first.session_sequence_ids == (
        ("S1", "SEQUENCE-1"),
        ("S2", "SEQUENCE-2"),
    )
    assert first.timepoints_seconds == (0.0, 3600.0)
    assert first.schedule_sequences
    assert first.apparatus_id == "QUALIFIED-BLOTTER-RACK"
    assert first.deviation_policy_sha256 == "f" * 64


def test_v2_scope_leakage_and_criterion_collapse_fail_closed() -> None:
    template = load_protocol_templates_v2(TEMPLATES_V2)[0]
    with pytest.raises(ValueError, match="OWNER scope requires exactly one assessor"):
        build_protocol_v2(
            template,
            _bindings_v2(assessor_ids=["OWNER-1", "OWNER-2"]),
        )
    with pytest.raises(ValueError, match="panel and consumer scopes require"):
        build_protocol_v2(
            template,
            _bindings_v2(participant_scope="TRAINED_PANEL", assessor_ids=["A1"]),
        )

    protocol = build_protocol_v2(template, _bindings_v2())
    collapsed = replace(
        protocol,
        secondary_endpoints=(protocol.primary_endpoint,),
    )
    assert any("primary and secondary endpoints" in issue for issue in validate_protocol_v2(collapsed))


def test_v2_counterbalance_repeats_heldout_and_exposure_fail_closed() -> None:
    protocol = build_protocol_v2(
        load_protocol_templates_v2(TEMPLATES_V2)[0],
        _bindings_v2(),
    )
    bad_schedule = replace(protocol, schedule_sha256="0" * 64)
    missing_schedule = replace(protocol, schedule_sequences=())
    one_repeat = replace(protocol, repeat_ids=("R1",), repeat_count=1)
    bad_heldout = replace(protocol, heldout_unit=ProtocolAnalysisUnitV2.ASSESSOR)
    unsafe = replace(protocol, maximum_exposures_per_session=0)

    assert any("Williams" in issue for issue in validate_protocol_v2(bad_schedule))
    assert any("Williams" in issue for issue in validate_protocol_v2(missing_schedule))
    assert any("at least two repeats" in issue for issue in validate_protocol_v2(one_repeat))
    assert any("OWNER heldout unit" in issue for issue in validate_protocol_v2(bad_heldout))
    assert any("exposure" in issue for issue in validate_protocol_v2(unsafe))


def test_v2_within_sniff_requires_qualified_apparatus_and_timing() -> None:
    template = load_protocol_templates_v2(TEMPLATES_V2)[0]
    bad = _bindings_v2(within_sniff=True)
    bad["within_sniff_timing_protocol_qualified"] = False
    with pytest.raises(ValueError, match="within-sniff"):
        build_protocol_v2(template, bad)

    qualified = build_protocol_v2(template, _bindings_v2(within_sniff=True))
    assert qualified.within_sniff is True
    assert qualified.timing_protocol_sha256 == "4" * 64
    assert qualified.timing_tolerance_ms == 50.0


def test_v2_rejects_post_outcome_status_edit_and_preserves_v1_bytes() -> None:
    v1 = build_protocol(load_protocol_templates(TEMPLATES)[0], _bindings())
    frozen_v1 = v1.canonical_bytes()
    v1_round_trip = PreregisteredProtocolV1.from_dict(v1.as_dict())
    v2 = build_protocol_v2(
        load_protocol_templates_v2(TEMPLATES_V2)[0],
        _bindings_v2(),
    )
    payload = v2.as_dict()
    payload["status"] = "OBSERVED"

    with pytest.raises(ValueError, match="PREREGISTERED_NOT_EXECUTED"):
        PreregisteredProtocolV2.from_dict(payload)
    assert v1_round_trip.canonical_bytes() == frozen_v1


def test_v2_cli_builds_and_validates_through_existing_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bindings_path = tmp_path / "bindings.json"
    protocol_path = tmp_path / "protocol-v2.json"
    bindings_path.write_text(
        json.dumps(_bindings_v2(), sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "protocols",
            "build-v2",
            "--templates",
            str(TEMPLATES_V2),
            "--template-id",
            "TEMPORAL-EVIDENCE-V2",
            "--bindings",
            str(bindings_path),
            "--output",
            str(protocol_path),
        ],
    )
    assert protocol_main() == 0
    built = PreregisteredProtocolV2.from_dict(
        json.loads(protocol_path.read_text(encoding="utf-8"))
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["protocols", "validate-v2", "--protocol", str(protocol_path)],
    )
    assert protocol_main() == 0
    assert validate_protocol_v2(built) == ()
