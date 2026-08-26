from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.solforge_workbench import (
    ArmSummaryV1,
    ArtifactRecordSummaryV1,
    SolForgeWorkbenchDesignRequestV1,
    SolForgeWorkbenchDesignResponseV1,
    SolForgeWorkbenchStatusV1,
)

FALSE_FLAGS = {
    "compounding": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}
H = "a" * 64


def _case_packet() -> dict:
    return {
        "schema_version": "solforge_case_v1",
        "state": "READY",
        "case_id": "WB-1",
        "target_identity": "austere sweet orris root",
        "ideal_architecture": {"heart": ["orris root"]},
        "current_inventory_build": {"materials": {"Orris accord": 1.0}},
        "inventory_path": "D:/inventory.xlsx",
        "inventory_sha256": H,
        "formula_sha256": "b" * 64,
        "dose_receipt_sha256": "c" * 64,
        "constraints": ["CONSTANT_TOTAL_ACTIVE_MASS"],
        "criterion": "DEPTH",
        "forbidden_claims": ["sensory"],
        "authority_flags": dict(FALSE_FLAGS),
    }


def _hypothesis_packet() -> dict:
    return {
        "schema_version": "sol_hypothesis_set_v1",
        "case_sha256": "d" * 64,
        "model_identity": "gpt-5.6-sol",
        "reasoning_setting": "ultra",
        "prompt_sha256": "e" * 64,
        "input_sha256": "f" * 64,
        "output_sha256": "1" * 64,
        "hypotheses": [],
        "uncertainty": "No nonredundant change justified.",
        "authority_flags": dict(FALSE_FLAGS),
    }


def _request() -> dict:
    return {
        "schema_version": "solforge_workbench_design_request_v1",
        "case": _case_packet(),
        "hypotheses": _hypothesis_packet(),
    }


def test_design_request_accepts_only_closed_packets() -> None:
    parsed = SolForgeWorkbenchDesignRequestV1.model_validate(_request())

    assert parsed.case["authority_flags"] == FALSE_FLAGS
    assert parsed.hypotheses["schema_version"] == "sol_hypothesis_set_v1"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.update(extra=True),
        lambda payload: payload["case"].update(schema_version="future_case"),
        lambda payload: payload["hypotheses"].update(schema_version="future_hypotheses"),
        lambda payload: payload["case"]["authority_flags"].update(sensory=True),
        lambda payload: payload["hypotheses"]["authority_flags"].update(hedonic=True),
    ],
)
def test_design_request_rejects_open_or_authority_escalating_packets(mutation) -> None:
    payload = _request()
    mutation(payload)

    with pytest.raises(ValidationError):
        SolForgeWorkbenchDesignRequestV1.model_validate(payload)


def test_design_response_keeps_verified_summary_closed_and_all_false() -> None:
    response = SolForgeWorkbenchDesignResponseV1(
        schema_version="solforge_workbench_design_response_v1",
        run_id="sf-" + "1" * 32,
        stage="DECIDED",
        history=("INTAKE", "DECIDED"),
        decision="NO_CHANGE",
        blockers=(),
        evidence_limitations=("No nonredundant target-faithful delta was justified.",),
        next_action="Retain the current target architecture.",
        registry_sha256=H,
        admitted_module_ids=("architectural-delta-engine",),
        compiled_experiment_sha256="b" * 64,
        selected_hypothesis_id=None,
        delta_kind=None,
        arms=(),
        inventory_statuses=(),
        manifest_sha256="c" * 64,
        records=(
            ArtifactRecordSummaryV1(
                filename="decision_receipt_v1--" + "d" * 64 + ".json",
                schema_version="decision_receipt_v1",
                record_sha256="d" * 64,
                file_sha256="d" * 64,
            ),
        ),
        artifact_download_available=False,
        authority_flags=FALSE_FLAGS,
    )

    assert response.decision == "NO_CHANGE"
    assert not any(response.authority_flags.values())
    with pytest.raises(ValidationError):
        SolForgeWorkbenchDesignResponseV1.model_validate(
            {**response.model_dump(), "authority_flags": {**FALSE_FLAGS, "release": True}}
        )


def test_arm_and_status_models_are_closed() -> None:
    arm = ArmSummaryV1(
        arm_id="CONTROL",
        blind_code="SF-12345678",
        sample_sha256=H,
        total_active_mass_g=1.0,
        factor_presence={"Habanolide": False},
    )
    status = SolForgeWorkbenchStatusV1(
        schema_version="solforge_workbench_status_v1",
        ready=True,
        blockers=(),
        completed_run_count=0,
        artifact_bytes=0,
        max_runs=50,
        max_artifact_bytes=104_857_600,
        max_concurrent_runs=1,
        artifact_download_available=False,
        authority_flags=FALSE_FLAGS,
    )

    assert arm.factor_presence == {"Habanolide": False}
    assert status.ready is True
    with pytest.raises(ValidationError):
        ArmSummaryV1.model_validate({**arm.model_dump(), "extra": True})
