from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from engine.analytical.ledger import AnalyticalLedger
from engine.evidence.ledger import EvidenceClaim, EvidenceLedger, EvidenceSource

from app.adapters.lab_legacy import (
    LegacyAdapterError,
    analytical_ledger_import_drafts,
    evidence_ledger_import_drafts,
    project_analytical_ledger,
    project_bottle_batch,
    project_formula_version,
    project_regulatory_snapshot,
    project_sensory_trial,
    project_stock_solution,
)
from app.models.lab import (
    LabApplication,
    LabBottle,
    LabBottleEvent,
    LabBottleEventEffect,
    LabExperiment,
    LabFormulaVersion,
    LabObservation,
    LabSample,
    LabStockSolution,
)
from app.models.lab_science import (
    LabAnalyticalMethodVersion,
    LabAnalyticalPeak,
    LabAnalyticalRun,
    LabGCOEvent,
    LabRegulatoryAssessmentVersion,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
HASH = "a" * 64


def test_stock_projection_requires_density_and_preserves_mass():
    stock = LabStockSolution(
        id="stock",
        created_at=NOW,
        material_id="material",
        supplier="supplier",
        lot_number="lot",
        active_fraction=0.1,
        fraction_basis="mass_fraction",
        density_g_ml=0.8,
        solvent_name="ethanol",
        initial_mass_g=16.0,
        remaining_mass_g=8.0,
        source_json={"grade": "analytical", "stability_status": "verified"},
    )

    projection = project_stock_solution(stock, material_name="Material")

    assert projection.material_id == "stock"
    assert projection.amount_remaining_ml == pytest.approx(10.0)
    assert projection.concentration == pytest.approx(0.1)
    stock.density_g_ml = None
    with pytest.raises(LegacyAdapterError, match="density_g_ml"):
        project_stock_solution(stock, material_name="Material")


def test_bottle_projection_replays_canonical_effects_without_writing():
    bottle = LabBottle(id="bottle", created_at=NOW, label="Bottle", status="active")
    create = LabBottleEvent(
        id="event-create",
        created_at=NOW,
        bottle_id="bottle",
        stream_sequence=1,
        expected_sequence=0,
        command_id="create",
        transaction_id="transaction-create",
        event_type="create",
        payload_json={},
    )
    dose = LabBottleEvent(
        id="event-dose",
        created_at=NOW,
        bottle_id="bottle",
        stream_sequence=2,
        expected_sequence=1,
        command_id="dose",
        transaction_id="transaction-dose",
        event_type="add_stock",
        payload_json={},
    )
    effect = LabBottleEventEffect(
        id="effect-dose",
        created_at=NOW,
        event_id="event-dose",
        bottle_id="bottle",
        stock_solution_id="stock",
        material_id="material",
        mass_delta_g=2.5,
        measured_volume_ul=2500.0,
    )

    projection = project_bottle_batch(
        bottle,
        [dose, create],
        effects_by_event={"event-dose": [effect]},
        stock_labels={"stock": "Material"},
    )

    assert projection.replay()["materials"] == {"Material": 2.5}
    assert projection.event_count() == 2


def test_formula_projection_requires_explicit_hash_and_parent():
    version = LabFormulaVersion(
        id="version",
        created_at=NOW,
        formula_id="formula",
        version_number=2,
        brief_json={},
        constraints_json={},
        source_json={
            "formula_hash": HASH,
            "change_type": "REBALANCE",
            "changes": [],
            "description": "bounded projection",
        },
    )

    projection = project_formula_version(version, parent_version_id="parent")

    assert projection.version_id == "version"
    assert projection.parent_version_id == "parent"
    assert projection.formula_hash == HASH
    version.source_json = {}
    with pytest.raises(LegacyAdapterError, match="formula_hash"):
        project_formula_version(version, parent_version_id="parent")


def test_analytical_projection_preserves_run_peak_and_gco_fields():
    method = LabAnalyticalMethodVersion(
        id="method-version",
        created_at=NOW,
        method_id="method",
        version_number=1,
        schema_version="1",
        technique="GCMS",
        intended_use="identity",
        status="VALIDATED",
        method_json={
            "column": "DB-5MS",
            "temperature_program": "40-280C",
            "injection_mode": "split",
            "injection_volume_ul": 1.0,
        },
        evidence_record_id="evidence",
        content_sha256=HASH,
    )
    run = LabAnalyticalRun(
        id="run",
        created_at=NOW,
        run_id="stable-run",
        method_version_id="method-version",
        run_kind="GCMS",
        status="QC_ACCEPTED",
        instrument_identifier="instrument",
        acquired_at=NOW,
        parameters_json={},
        deviations_json=[],
        processing_version="processor-1",
        sample_id="sample",
        content_sha256="b" * 64,
    )
    peak = LabAnalyticalPeak(
        id="peak",
        created_at=NOW,
        analytical_run_id="run",
        peak_key="peak-1",
        retention_time_minutes=3.5,
        retention_index=1200.0,
        area=42.0,
        response_factor=1.2,
        qualifier_ions_json=["91", "105"],
        tentative_identity="Material",
        identity_state="TENTATIVE",
        match_score=0.91,
        content_sha256="c" * 64,
    )
    gco = LabGCOEvent(
        id="gco",
        created_at=NOW,
        analytical_run_id="run",
        event_key="gco-1",
        retention_time_minutes=3.5,
        retention_index=1200.0,
        descriptor="floral",
        intensity=0.8,
        assessor_pseudonym="panel-1",
        repeatability_json={"legacy_label": "consistent"},
        content_sha256="d" * 64,
    )

    projection = project_analytical_ledger(
        methods_by_id={"method-version": method},
        runs=[run],
        peaks_by_run={"run": [peak]},
        gco_events=[gco],
    )
    payload = projection.to_dict()

    assert payload["gcms_runs"][0]["run"]["run_id"] == "run"
    assert payload["gcms_runs"][0]["peaks"][0]["match_score"] == pytest.approx(91.0)
    assert payload["gco_events"][0]["intensity"] == "very_strong"
    drafts = analytical_ledger_import_drafts(projection)
    assert [draft.destination for draft in drafts] == [
        "lab_analytical_runs",
        "lab_gco_events",
    ]


def test_sensory_and_regulatory_projections_require_explicit_context():
    experiment = LabExperiment(
        id="experiment",
        created_at=NOW,
        name="Trial",
        protocol_json={},
        status="closed",
    )
    sample = LabSample(
        id="sample",
        created_at=NOW,
        experiment_id="experiment",
        bottle_id="bottle",
        blind_code="ABC",
    )
    application = LabApplication(
        id="application",
        created_at=NOW,
        sample_id="sample",
        applied_at=NOW,
        dose_json={"application_mass_g": 0.01},
        context_json={
            "substrate": "blotter",
            "room_temperature_c": 22.0,
            "room_humidity_pct": 50.0,
        },
    )
    observation = LabObservation(
        id="observation",
        created_at=NOW,
        application_id="application",
        elapsed_seconds=300.0,
        observations_json={
            "assessor": "panel-1",
            "opening_identity": 4.0,
            "heart_identity": 3.0,
            "drydown_identity": 2.0,
            "transition_quality": 3.0,
            "texture": 3.0,
            "diffusion": 4.0,
            "longevity": 3.0,
            "overall_similarity": 3.5,
            "preference": 4.0,
        },
    )

    sensory = project_sensory_trial(
        experiment=experiment,
        samples=[sample],
        applications_by_sample={"sample": application},
        observations_by_application={"application": [observation]},
        formula_ids_by_bottle={"bottle": "formula"},
        reference_sample_id="sample",
    )
    assert sensory.summarize("sample")["avg_overall"] == pytest.approx(3.5)

    assessment = LabRegulatoryAssessmentVersion(
        id="assessment",
        created_at=NOW,
        assessment_id="stable-assessment",
        version_number=1,
        schema_version="1",
        subject_type="FORMULA_VERSION",
        subject_id="formula",
        standard_identifier="IFRA",
        standard_amendment="51",
        standard_state="CURRENT",
        jurisdiction="GLOBAL",
        product_category="4",
        concentration_basis="mass_fraction",
        effective_date=date(2023, 6, 30),
        evaluated_at=NOW,
        result_state="PASS",
        assumptions_json=[],
        unresolved_json=[],
        content_sha256="e" * 64,
    )
    regulatory = project_regulatory_snapshot(assessment)
    assert regulatory.rule_set == "IFRA 51"
    assert regulatory.effective_date == "2023-06-30"


def test_evidence_import_drafts_are_deterministic_and_non_persisting():
    ledger = EvidenceLedger.from_records(
        sources=[EvidenceSource("source", "A", doi="10.1000/example")],
        claims=[
            EvidenceClaim(
                "claim",
                "source",
                "product",
                "identity_presence",
                subject_material_name="Material",
            )
        ],
    )

    first = evidence_ledger_import_drafts(ledger)
    second = evidence_ledger_import_drafts(ledger)

    assert first == second
    assert first[0].destination == "lab_evidence_records"
    assert first[0].payload()["legacy_claim"]["claim_id"] == "claim"
    assert len(first[0].content_sha256) == 64

    missing_source = EvidenceLedger.from_records(
        sources=[],
        claims=[EvidenceClaim("claim", "missing", "product", "identity_presence")],
    )
    with pytest.raises(LegacyAdapterError, match="missing source"):
        evidence_ledger_import_drafts(missing_source)


def test_empty_analytical_projection_is_a_read_only_ledger():
    projection = project_analytical_ledger(
        methods_by_id={},
        runs=[],
        peaks_by_run={},
    )
    assert isinstance(projection, AnalyticalLedger)
    assert projection.to_dict() == {
        "gcms_runs": [],
        "hsspme_runs": [],
        "gco_events": [],
    }
