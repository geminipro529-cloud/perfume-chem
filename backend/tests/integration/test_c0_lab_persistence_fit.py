from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.lab import (
    LabApplication,
    LabExperiment,
    LabObservation,
    LabOutcome,
    LabSample,
)
from app.services.c0_semantic_readback import (
    C0SemanticReadbackState,
    revalidate_c0_lab_persistence_graph,
)
from app.services.lab_service import LabService

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "c0_lab_persistence_projection_v1.json"
)


def _stable_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_projection() -> dict[str, object]:
    raw = _FIXTURE.read_bytes()
    sidecar = _FIXTURE.with_suffix(".sha256").read_text(encoding="utf-8")
    assert sidecar == f"{hashlib.sha256(raw).hexdigest()}  {_FIXTURE.name}\n"
    value = json.loads(raw)
    assert isinstance(value, dict)
    return value


def _application_key(context: dict) -> str:
    key_payload = {
        "blind_code": context["blind_code"],
        "participant_token_sha256": context["participant_token_sha256"],
        "session_token_sha256": context["session_token_sha256"],
        "repeat_index": context["repeat_index"],
    }
    return _stable_hash(key_payload)


def _application_sort_key(record: dict) -> tuple[object, ...]:
    context = record["context_json"]
    return (
        context["blind_code"],
        context["participant_token_sha256"],
        context["session_token_sha256"],
        context["repeat_index"],
    )


def _observation_cell(payload: dict) -> tuple[object, ...]:
    observation = payload["panel_observation"]
    return (
        observation["blind_code"],
        observation["participant_token_sha256"],
        observation["session_token_sha256"],
        observation["repeat_index"],
        observation["sniff_time_seconds"],
    )


@pytest.mark.asyncio
async def test_exact_engine_c0_projection_round_trips_storage_without_migration(
    db_session,
) -> None:
    """Prove storage fidelity only; native semantic revalidation remains required."""

    projection = _load_projection()
    protocol_json = projection["experiment_protocol"]
    application_records = projection["application_records"]
    observation_records = projection["observation_records"]
    outcome_json = projection["outcome"]
    assert isinstance(protocol_json, dict)
    assert isinstance(application_records, list)
    assert isinstance(observation_records, list)
    assert isinstance(outcome_json, dict)

    service = LabService(db_session)
    bottle_by_code = {
        "K7Q": await service.create_bottle("Synthetic C0 K7Q", initial_mass_g=1.0),
        "M2R": await service.create_bottle("Synthetic C0 M2R", initial_mass_g=1.0),
    }
    experiment = await service.create_experiment(
        "C0 exact engine projection persistence fit",
        protocol=protocol_json,
        status="planned",
    )
    sample_by_code = {}
    for blind_code, bottle in bottle_by_code.items():
        sample_by_code[blind_code] = await service.add_experiment_sample(
            experiment_id=experiment.id,
            bottle_id=bottle.id,
            blind_code=blind_code,
        )

    application_id_by_key: dict[str, str] = {}
    for index, record in enumerate(application_records):
        assert isinstance(record, dict)
        blind_code = record["blind_code"]
        application = await service.record_application(
            sample_id=sample_by_code[blind_code].id,
            applied_at=datetime(2026, 8, 11, 2, index, tzinfo=timezone.utc),
            dose=record["dose_json"],
            context=record["context_json"],
        )
        application_id_by_key[record["application_key_sha256"]] = application.id
    for record in observation_records:
        assert isinstance(record, dict)
        await service.record_observation(
            application_id=application_id_by_key[record["application_key_sha256"]],
            elapsed_seconds=float(record["elapsed_seconds"]),
            observations=record["observations_json"],
        )
    await service.record_outcome(
        experiment_id=experiment.id,
        prediction_id=None,
        outcome=outcome_json,
    )

    stored_experiment = (
        await db_session.execute(select(LabExperiment).where(LabExperiment.id == experiment.id))
    ).scalar_one()
    stored_samples = (
        (
            await db_session.execute(
                select(LabSample).where(LabSample.experiment_id == experiment.id)
            )
        )
        .scalars()
        .all()
    )
    stored_applications = (
        (
            await db_session.execute(
                select(LabApplication)
                .join(LabSample, LabApplication.sample_id == LabSample.id)
                .where(LabSample.experiment_id == experiment.id)
            )
        )
        .scalars()
        .all()
    )
    stored_observations = (
        (
            await db_session.execute(
                select(LabObservation)
                .join(
                    LabApplication,
                    LabObservation.application_id == LabApplication.id,
                )
                .join(LabSample, LabApplication.sample_id == LabSample.id)
                .where(LabSample.experiment_id == experiment.id)
            )
        )
        .scalars()
        .all()
    )
    stored_outcome = (
        await db_session.execute(
            select(LabOutcome).where(LabOutcome.experiment_id == experiment.id)
        )
    ).scalar_one()

    sample_by_id = {sample.id: sample for sample in stored_samples}
    reloaded_applications: list[dict[str, object]] = []
    application_key_by_id: dict[str, str] = {}
    for application in stored_applications:
        key = _application_key(application.context_json)
        application_key_by_id[application.id] = key
        reloaded_applications.append(
            {
                "application_key_sha256": key,
                "blind_code": sample_by_id[application.sample_id].blind_code,
                "dose_json": application.dose_json,
                "context_json": application.context_json,
            }
        )
    reloaded_applications.sort(key=_application_sort_key)

    reloaded_observations = [
        {
            "application_key_sha256": application_key_by_id[item.application_id],
            "elapsed_seconds": (
                int(item.elapsed_seconds)
                if item.elapsed_seconds.is_integer()
                else item.elapsed_seconds
            ),
            "observations_json": item.observations_json,
        }
        for item in stored_observations
    ]
    reloaded_observations.sort(key=lambda item: _observation_cell(item["observations_json"]))

    persisted_graph = {
        "experiment_protocol": stored_experiment.protocol_json,
        "application_records": reloaded_applications,
        "observation_records": reloaded_observations,
        "outcome": stored_outcome.outcome_json,
    }
    expected_graph = {
        "experiment_protocol": protocol_json,
        "application_records": application_records,
        "observation_records": observation_records,
        "outcome": outcome_json,
    }
    assert persisted_graph == expected_graph
    assert _stable_hash(persisted_graph) == _stable_hash(expected_graph)
    readback_receipt = revalidate_c0_lab_persistence_graph(persisted_graph)
    assert readback_receipt.state is C0SemanticReadbackState.PASS
    assert readback_receipt.semantic_revalidation_passed is True
    assert readback_receipt.expected_cell_count == 24
    assert readback_receipt.observed_cell_count == 24
    assert readback_receipt.blockers == ()

    assert len(stored_samples) == 2
    assert all(sample.bottle_id for sample in stored_samples)
    assert {sample.blind_code for sample in stored_samples} == {"K7Q", "M2R"}
    expected_cells = {
        (
            item["blind_code"],
            item["participant_token_sha256"],
            item["session_token_sha256"],
            item["repeat_index"],
            item["sniff_time_seconds"],
        )
        for item in stored_experiment.protocol_json["expected_observation_manifest"]
    }
    observed_cells = [_observation_cell(item.observations_json) for item in stored_observations]
    assert len(observed_cells) == len(set(observed_cells)) == 24
    assert set(observed_cells) == expected_cells
    assert stored_experiment.protocol_json["persistence_fit_scope"] == ("STORAGE_FIDELITY_ONLY")
    assert stored_experiment.protocol_json["semantic_revalidation_required_after_readback"] is True
    assert stored_experiment.protocol_json["human_execution_authorized"] is False
    assert stored_experiment.protocol_json["transfer_claims"] == []
    assert stored_outcome.outcome_json["study_authority"] is False
    assert stored_outcome.outcome_json["release_authority"] is False
