from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.solforge.protocols import (
    PROTOCOL_AUTHORITY_FLAGS,
    PhysicalEvidenceIntakeError,
    ProtocolDesignClass,
    build_protocol,
    ingest_physical_results,
    load_protocol_templates,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "data/research/solforge/protocol_templates_v1.json"


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
