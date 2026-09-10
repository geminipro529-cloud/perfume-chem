from __future__ import annotations

from engine.solforge.adapters import export_backend_lab_payloads
from engine.solforge.contracts import CompilationState, CompiledArmV1, CompiledExperimentV1

H = "a" * 64


def _experiment() -> CompiledExperimentV1:
    arms = tuple(
        CompiledArmV1(
            arm_id=arm_id,
            formula={"factor": arm_id != "CONTROL"},
            total_active_mass_g=1.0,
            blind_code=blind,
            sample_sha256=digest * 64,
        )
        for arm_id, blind, digest in (
            ("CONTROL", "B17", "c"), ("TREATMENT", "K42", "d")
        )
    )
    return CompiledExperimentV1(
        case_sha256=H, hypothesis_set_sha256="b" * 64,
        inventory_refresh_sha256="c" * 64, inventory_source_row_count=190,
        state=CompilationState.COMPILED, delta_kind="ADDITION",
        selected_hypothesis_id="H1", arms=arms, blockers=(),
        inventory_statuses=(("Habanolide", "OWNED"),), omission_loss="less depth",
        failure_mode="blur", next_comparison="control versus treatment",
    )


def test_export_is_deterministic_and_preserves_blinding_and_constant_total() -> None:
    experiment = _experiment()
    first = export_backend_lab_payloads(experiment)
    second = export_backend_lab_payloads(experiment)
    assert first == second
    assert first["compiled_experiment_sha256"] == experiment.record_sha256
    assert len(first["schedule_sha256"]) == 64
    assert first["experiment"]["protocol"]["solforge"]["arm_ids"] == [
        "CONTROL", "TREATMENT"
    ]
    assert [sample["blind_code"] for sample in first["samples"]] == ["B17", "K42"]
    assert len(set(sample["blind_code"] for sample in first["samples"])) == 2
    assert {item["dose"]["total_active_mass_g"] for item in first["applications"]} == {1.0}


def test_export_binds_observation_and_comparison_context() -> None:
    payload = export_backend_lab_payloads(_experiment())
    observation = payload["observations"][0]
    context = observation["observations"]["solforge"]
    assert {
        "sample_id", "sample_sha256", "assessor_id", "repeat_index",
        "timepoint_seconds", "endpoint", "presentation_sequence", "schedule_sha256",
    }.issubset(context)
    comparison = payload["comparisons"][0]["context"]["solforge"]
    assert comparison["criterion"] == "TARGET_FIDELITY"
    assert comparison["first_presented_item"] == "CONTROL"


def test_export_has_no_write_or_action_authority() -> None:
    payload = export_backend_lab_payloads(_experiment())
    assert payload["publication_authorized"] is False
    assert payload["database_write_authorized"] is False
    assert payload["physical_execution_authorized"] is False
