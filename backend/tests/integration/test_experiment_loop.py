from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.lab import (
    LabApplication,
    LabObservation,
    LabOutcome,
    LabPairwiseComparison,
    LabPrediction,
)
from app.services.lab_service import LabService


@pytest.mark.asyncio
async def test_experiment_protocol_observations_comparison_prediction_and_outcome_persist(
    db_session,
):
    service = LabService(db_session)
    left_bottle = await service.create_bottle("Blind left", initial_mass_g=5.0)
    right_bottle = await service.create_bottle("Blind right", initial_mass_g=5.0)
    experiment = await service.create_experiment(
        "Iris wear trial",
        protocol={
            "application_mass_mg": 20.0,
            "observation_times_seconds": [0, 1800, 14400],
        },
    )
    left = await service.add_experiment_sample(
        experiment_id=experiment.id,
        bottle_id=left_bottle.id,
        blind_code="K7",
    )
    right = await service.add_experiment_sample(
        experiment_id=experiment.id,
        bottle_id=right_bottle.id,
        blind_code="M2",
    )
    application = await service.record_application(
        sample_id=left.id,
        applied_at=datetime(2026, 7, 16, 8, 0, tzinfo=timezone.utc),
        dose={"mass_mg": 20.0, "standard_uncertainty_mg": 0.5},
        context={"substrate": "blotter", "temperature_k": 298.15},
    )
    observation = await service.record_observation(
        application_id=application.id,
        elapsed_seconds=1800.0,
        observations={"iris_intensity": 7, "incense_intensity": 5},
    )
    comparison = await service.record_pairwise_comparison(
        experiment_id=experiment.id,
        left_sample_id=left.id,
        right_sample_id=right.id,
        preferred_sample_id=left.id,
        context={"criterion": "brief fidelity", "elapsed_seconds": 1800},
    )
    prediction = await service.record_prediction(
        experiment_id=experiment.id,
        sample_id=left.id,
        model_key="bradley_terry",
        model_version="diagnostic-v1",
        status="diagnostic",
        prediction={"preference_probability": 0.7, "validated": False},
    )
    outcome = await service.record_outcome(
        experiment_id=experiment.id,
        prediction_id=prediction.id,
        outcome={"preferred": True, "heldout": True},
    )

    assert (await db_session.execute(select(LabApplication))).scalar_one().id == application.id
    assert (await db_session.execute(select(LabObservation))).scalar_one().id == observation.id
    assert (await db_session.execute(select(LabPairwiseComparison))).scalar_one().id == comparison.id
    assert (await db_session.execute(select(LabPrediction))).scalar_one().id == prediction.id
    assert (await db_session.execute(select(LabOutcome))).scalar_one().id == outcome.id


@pytest.mark.asyncio
async def test_pairwise_comparison_rejects_samples_from_another_experiment(db_session):
    service = LabService(db_session)
    bottle = await service.create_bottle("Cross trial", initial_mass_g=1.0)
    first = await service.create_experiment("First", protocol={})
    second = await service.create_experiment("Second", protocol={})
    left = await service.add_experiment_sample(
        experiment_id=first.id,
        bottle_id=bottle.id,
        blind_code="A",
    )
    right = await service.add_experiment_sample(
        experiment_id=second.id,
        bottle_id=bottle.id,
        blind_code="B",
    )

    with pytest.raises(ValueError, match="same experiment"):
        await service.record_pairwise_comparison(
            experiment_id=first.id,
            left_sample_id=left.id,
            right_sample_id=right.id,
            preferred_sample_id=left.id,
            context={},
        )
