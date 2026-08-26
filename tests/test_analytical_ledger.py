"""Tests for engine.analytical.ledger."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.analytical.ledger import (
    AnalyticalLedger,
    GCOEvent,
    GCMSRun,
    GCMSPeak,
    HSSPMERun,
    QualityControls,
)


class _LegacyFixtureAnalyticalLedger(AnalyticalLedger):
    """Mutable test builder; production AnalyticalLedger is read-only."""

    def add_gcms_run(self, run: GCMSRun, peaks: list[GCMSPeak]) -> None:
        self._gcms_runs[run.run_id] = run
        self._gcms_peaks[run.run_id] = list(peaks)

    def add_hsspme_run(self, run: HSSPMERun) -> None:
        self._hsspme_runs[run.run_id] = run

    def add_gco_event(self, event: GCOEvent) -> None:
        self._gco_events.append(event)


AnalyticalLedger = _LegacyFixtureAnalyticalLedger


# ── GCMSRun ──────────────────────────────────────────────────────────────────────


def test_gcms_run_creation():
    run = GCMSRun(
        run_id="550e8400-e29b-41d4-a716-446655440000",
        instrument="Agilent 7890B",
        column="DB-5MS 30m x 0.25mm x 0.25um",
        temperature_program="40C(1min)-8C/min-280C(5min)",
        injection_mode="splitless",
        injection_volume_ul=1.0,
        carrier_gas="Helium",
        flow_rate_ml_min=1.2,
        internal_standard="Toluene-d8",
        internal_standard_amount_ug=50.0,
        date_run="2026-07-01",
    )
    assert run.run_id == "550e8400-e29b-41d4-a716-446655440000"
    assert run.instrument == "Agilent 7890B"
    assert run.column == "DB-5MS 30m x 0.25mm x 0.25um"
    assert run.temperature_program == "40C(1min)-8C/min-280C(5min)"
    assert run.injection_mode == "splitless"
    assert run.injection_volume_ul == 1.0
    assert run.carrier_gas == "Helium"
    assert run.flow_rate_ml_min == 1.2
    assert run.internal_standard == "Toluene-d8"
    assert run.internal_standard_amount_ug == 50.0
    assert run.date_run == "2026-07-01"


def test_gcms_run_defaults():
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="split",
        injection_volume_ul=0.5,
    )
    assert run.carrier_gas == "Helium"
    assert run.flow_rate_ml_min == 1.0
    assert run.internal_standard == ""
    assert run.internal_standard_amount_ug == 0.0
    assert run.date_run == ""


def test_gcms_run_as_dict():
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="split",
        injection_volume_ul=0.5,
    )
    d = run.as_dict()
    assert d["run_id"] == "r1"
    assert d["carrier_gas"] == "Helium"
    assert d["flow_rate_ml_min"] == 1.0


def test_gcms_run_from_dict():
    d = {
        "run_id": "r1",
        "instrument": "Agilent 7890B",
        "column": "DB-5MS",
        "temperature_program": "40-280",
        "injection_mode": "split",
        "injection_volume_ul": 0.5,
    }
    run = GCMSRun.from_dict(d)
    assert run.run_id == "r1"
    assert run.carrier_gas == "Helium"
    assert run.flow_rate_ml_min == 1.0


# ── GCMSPeak ─────────────────────────────────────────────────────────────────────


def test_gcms_peak_creation():
    peak = GCMSPeak(
        peak_id="660e8400-e29b-41d4-a716-446655440001",
        run_id="550e8400-e29b-41d4-a716-446655440000",
        retention_time_min=12.34,
        retention_index=1350.0,
        peak_area=1.23e6,
        tentative_identity="Linalool",
        identity_authority="B",
        match_score=95.0,
        qualifier_ions=("93", "121", "136"),
        response_factor=1.5,
        notes="Good match",
    )
    assert peak.peak_id == "660e8400-e29b-41d4-a716-446655440001"
    assert peak.retention_index == 1350.0
    assert peak.qualifier_ions == ("93", "121", "136")
    assert peak.identity_authority == "B"
    assert peak.match_score == 95.0
    assert peak.response_factor == 1.5
    assert peak.notes == "Good match"


def test_gcms_peak_retention_index_none():
    peak = GCMSPeak(
        peak_id="p1",
        run_id="r1",
        retention_time_min=5.0,
        retention_index=None,
        peak_area=50000.0,
    )
    assert peak.retention_index is None


def test_gcms_peak_defaults():
    peak = GCMSPeak(
        peak_id="p1",
        run_id="r1",
        retention_time_min=5.0,
        retention_index=800.0,
        peak_area=50000.0,
    )
    assert peak.response_factor == 1.0
    assert peak.qualifier_ions == ()
    assert peak.tentative_identity == ""
    assert peak.identity_authority == "UNCONFIRMED"
    assert peak.match_score == 0.0
    assert peak.notes == ""


# ── HSSPMERun ────────────────────────────────────────────────────────────────────


def test_hsspme_run_creation():
    run = HSSPMERun(
        run_id="770e8400-e29b-41d4-a716-446655440002",
        fiber="DVB/CAR/PDMS 50/30um",
        sample_mass_g=0.5,
        vial_volume_ml=20.0,
        incubation_temperature_c=40.0,
        incubation_time_min=15.0,
        extraction_time_min=30.0,
        agitation_rpm=250,
        substrate="blotter",
        application_age_min=5.0,
        date_run="2026-07-01",
    )
    assert run.run_id == "770e8400-e29b-41d4-a716-446655440002"
    assert run.fiber == "DVB/CAR/PDMS 50/30um"
    assert run.incubation_temperature_c == 40.0
    assert run.extraction_time_min == 30.0
    assert run.agitation_rpm == 250
    assert run.substrate == "blotter"
    assert run.application_age_min == 5.0
    assert run.date_run == "2026-07-01"


def test_hsspme_run_defaults():
    run = HSSPMERun(
        run_id="h1",
        fiber="PDMS 100um",
        sample_mass_g=1.0,
        vial_volume_ml=10.0,
        incubation_temperature_c=37.0,
        incubation_time_min=10.0,
        extraction_time_min=20.0,
        agitation_rpm=500,
        substrate="skin",
        application_age_min=30.0,
    )
    assert run.date_run == ""


# ── GCOEvent ─────────────────────────────────────────────────────────────────────


def test_gco_event_creation():
    event = GCOEvent(
        event_id="880e8400-e29b-41d4-a716-446655440003",
        run_id="550e8400-e29b-41d4-a716-446655440000",
        position=12.34,
        descriptor="citrus, bergamot-like",
        intensity="strong",
        assessor="Alice",
        repeatability="consistent",
        aligned_retention_index=1352.0,
        notes="Very clear odour",
    )
    assert event.event_id == "880e8400-e29b-41d4-a716-446655440003"
    assert event.descriptor == "citrus, bergamot-like"
    assert event.intensity == "strong"
    assert event.repeatability == "consistent"
    assert event.aligned_retention_index == 1352.0
    assert event.notes == "Very clear odour"


def test_gco_event_defaults():
    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="floral",
        intensity="moderate",
        assessor="Bob",
        repeatability="once",
    )
    assert event.aligned_retention_index is None
    assert event.notes == ""


# ── QualityControls ──────────────────────────────────────────────────────────────


def test_quality_controls_passed_true():
    qc = QualityControls(
        solvent_blank=True,
        vial_blank=True,
        matrix_blank=True,
        internal_standard_present=True,
        retention_index_standard=False,
        duplicate_injections=0,
        control_fragrance_included=False,
    )
    assert qc.passed() is True


def test_quality_controls_passed_false():
    qc = QualityControls(
        solvent_blank=True,
        vial_blank=True,
        matrix_blank=True,
        internal_standard_present=False,
        retention_index_standard=False,
        duplicate_injections=0,
        control_fragrance_included=False,
    )
    assert qc.passed() is False


def test_quality_controls_passed_edge_three_true():
    qc = QualityControls(
        solvent_blank=True,
        vial_blank=True,
        matrix_blank=True,
        internal_standard_present=False,
        retention_index_standard=False,
        duplicate_injections=0,
        control_fragrance_included=False,
    )
    assert qc.passed() is False


def test_quality_controls_passed_duplicate_injections_counts():
    qc = QualityControls(
        solvent_blank=True,
        vial_blank=True,
        matrix_blank=True,
        internal_standard_present=False,
        retention_index_standard=False,
        duplicate_injections=2,
        control_fragrance_included=False,
    )
    assert qc.passed() is True


def test_quality_controls_defaults():
    qc = QualityControls()
    assert qc.passed() is False
    assert qc.duplicate_injections == 0


# ── AnalyticalLedger ─────────────────────────────────────────────────────────────


def test_add_gcms_run_with_peaks():
    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
            match_score=95.0,
        ),
        GCMSPeak(
            peak_id="p2",
            run_id="r1",
            retention_time_min=12.5,
            retention_index=1350.0,
            peak_area=5e5,
            tentative_identity="Linalool",
            match_score=90.0,
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    assert len(ledger._gcms_runs) == 1
    assert len(ledger._gcms_peaks["r1"]) == 2


def test_add_gcms_run_replaces_existing():
    ledger = AnalyticalLedger()
    run1 = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    run2 = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="HP-5MS",
        temperature_program="50-300",
        injection_mode="split",
        injection_volume_ul=2.0,
    )
    ledger.add_gcms_run(run1, [])
    ledger.add_gcms_run(run2, [])
    assert ledger._gcms_runs["r1"].column == "HP-5MS"


def test_get_identified_materials():
    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
            match_score=95.0,
        ),
        GCMSPeak(
            peak_id="p2",
            run_id="r1",
            retention_time_min=12.5,
            retention_index=1350.0,
            peak_area=5e5,
            tentative_identity="Linalool",
            match_score=90.0,
        ),
        GCMSPeak(
            peak_id="p3",
            run_id="r1",
            retention_time_min=15.0,
            retention_index=1500.0,
            peak_area=2e5,
            tentative_identity="",
            match_score=0.0,
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    identified = ledger.get_identified_materials("r1")
    assert identified == ["Limonene", "Linalool"]


def test_get_identified_materials_low_match_score():
    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
            match_score=75.0,
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    assert ledger.get_identified_materials("r1") == []


def test_get_identified_materials_unknown_run():
    ledger = AnalyticalLedger()
    assert ledger.get_identified_materials("nonexistent") == []


def test_add_hsspme_run():
    ledger = AnalyticalLedger()
    run = HSSPMERun(
        run_id="h1",
        fiber="DVB/CAR/PDMS 50/30um",
        sample_mass_g=0.5,
        vial_volume_ml=20.0,
        incubation_temperature_c=40.0,
        incubation_time_min=15.0,
        extraction_time_min=30.0,
        agitation_rpm=250,
        substrate="blotter",
        application_age_min=5.0,
    )
    ledger.add_hsspme_run(run)
    assert len(ledger._hsspme_runs) == 1
    assert ledger._hsspme_runs["h1"].fiber == "DVB/CAR/PDMS 50/30um"


def test_add_hsspme_run_replaces_existing():
    ledger = AnalyticalLedger()
    run1 = HSSPMERun(
        run_id="h1",
        fiber="PDMS 100um",
        sample_mass_g=1.0,
        vial_volume_ml=10.0,
        incubation_temperature_c=37.0,
        incubation_time_min=10.0,
        extraction_time_min=20.0,
        agitation_rpm=500,
        substrate="skin",
        application_age_min=30.0,
    )
    run2 = HSSPMERun(
        run_id="h1",
        fiber="DVB/CAR/PDMS 50/30um",
        sample_mass_g=0.5,
        vial_volume_ml=20.0,
        incubation_temperature_c=40.0,
        incubation_time_min=15.0,
        extraction_time_min=30.0,
        agitation_rpm=250,
        substrate="blotter",
        application_age_min=5.0,
    )
    ledger.add_hsspme_run(run1)
    ledger.add_hsspme_run(run2)
    assert ledger._hsspme_runs["h1"].fiber == "DVB/CAR/PDMS 50/30um"


def test_add_gco_event():
    ledger = AnalyticalLedger()
    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=12.34,
        descriptor="citrus, bergamot-like",
        intensity="strong",
        assessor="Alice",
        repeatability="consistent",
    )
    ledger.add_gco_event(event)
    assert len(ledger._gco_events) == 1


def test_add_gco_event_appends():
    ledger = AnalyticalLedger()
    e1 = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="floral",
        intensity="moderate",
        assessor="Alice",
        repeatability="once",
    )
    e2 = GCOEvent(
        event_id="e2",
        run_id="r1",
        position=15.0,
        descriptor="woody",
        intensity="strong",
        assessor="Bob",
        repeatability="2_of_3",
    )
    ledger.add_gco_event(e1)
    ledger.add_gco_event(e2)
    assert len(ledger._gco_events) == 2


def test_search_by_retention_index():
    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
        ),
        GCMSPeak(
            peak_id="p2",
            run_id="r1",
            retention_time_min=12.5,
            retention_index=1350.0,
            peak_area=5e5,
            tentative_identity="Linalool",
        ),
        GCMSPeak(
            peak_id="p3",
            run_id="r1",
            retention_time_min=15.0,
            retention_index=1500.0,
            peak_area=2e5,
            tentative_identity="Geraniol",
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    hits = ledger.search_by_retention_index(1350.0, tolerance=5)
    assert len(hits) == 1
    assert hits[0].tentative_identity == "Linalool"


def test_search_by_retention_index_multiple_runs():
    ledger = AnalyticalLedger()
    run1 = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    run2 = GCMSRun(
        run_id="r2",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks1 = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
        ),
    ]
    peaks2 = [
        GCMSPeak(
            peak_id="p2",
            run_id="r2",
            retention_time_min=12.5,
            retention_index=1201.0,
            peak_area=5e5,
            tentative_identity="Limonene",
        ),
    ]
    ledger.add_gcms_run(run1, peaks1)
    ledger.add_gcms_run(run2, peaks2)
    hits = ledger.search_by_retention_index(1200.0, tolerance=2)
    assert len(hits) == 2


def test_search_by_retention_index_excludes_none():
    ledger = AnalyticalLedger()
    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=None,
            peak_area=1e6,
            tentative_identity="Unknown",
        ),
    ]
    ledger.add_gcms_run(run, peaks)
    hits = ledger.search_by_retention_index(1000.0, tolerance=100)
    assert len(hits) == 0


def test_search_by_odor_descriptor():
    ledger = AnalyticalLedger()
    e1 = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="citrus, bergamot-like",
        intensity="strong",
        assessor="Alice",
        repeatability="consistent",
    )
    e2 = GCOEvent(
        event_id="e2",
        run_id="r1",
        position=15.0,
        descriptor="woody, cedar-like",
        intensity="moderate",
        assessor="Bob",
        repeatability="2_of_3",
    )
    e3 = GCOEvent(
        event_id="e3",
        run_id="r1",
        position=20.0,
        descriptor="floral, rose-like",
        intensity="weak",
        assessor="Alice",
        repeatability="once",
    )
    ledger.add_gco_event(e1)
    ledger.add_gco_event(e2)
    ledger.add_gco_event(e3)
    hits = ledger.search_by_odor_descriptor("citrus")
    assert len(hits) == 1
    assert hits[0].event_id == "e1"


def test_search_by_odor_descriptor_case_insensitive():
    ledger = AnalyticalLedger()
    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="Citrus, Bergamot-Like",
        intensity="strong",
        assessor="Alice",
        repeatability="consistent",
    )
    ledger.add_gco_event(event)
    hits = ledger.search_by_odor_descriptor("CITRUS")
    assert len(hits) == 1


def test_search_by_odor_descriptor_substring():
    ledger = AnalyticalLedger()
    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="sweet floral with citrus top",
        intensity="moderate",
        assessor="Alice",
        repeatability="once",
    )
    ledger.add_gco_event(event)
    hits = ledger.search_by_odor_descriptor("floral")
    assert len(hits) == 1


def test_search_by_odor_descriptor_no_match():
    ledger = AnalyticalLedger()
    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="woody",
        intensity="moderate",
        assessor="Alice",
        repeatability="once",
    )
    ledger.add_gco_event(event)
    hits = ledger.search_by_odor_descriptor("citrus")
    assert len(hits) == 0


# ── Serialisation round-trip ─────────────────────────────────────────────────────


def test_to_dict_and_from_dict():
    ledger = AnalyticalLedger()

    run = GCMSRun(
        run_id="r1",
        instrument="Agilent 7890B",
        column="DB-5MS",
        temperature_program="40-280",
        injection_mode="splitless",
        injection_volume_ul=1.0,
    )
    peaks = [
        GCMSPeak(
            peak_id="p1",
            run_id="r1",
            retention_time_min=10.0,
            retention_index=1200.0,
            peak_area=1e6,
            tentative_identity="Limonene",
            match_score=95.0,
        ),
    ]
    ledger.add_gcms_run(run, peaks)

    hs_run = HSSPMERun(
        run_id="h1",
        fiber="PDMS 100um",
        sample_mass_g=1.0,
        vial_volume_ml=10.0,
        incubation_temperature_c=37.0,
        incubation_time_min=10.0,
        extraction_time_min=20.0,
        agitation_rpm=500,
        substrate="skin",
        application_age_min=30.0,
    )
    ledger.add_hsspme_run(hs_run)

    event = GCOEvent(
        event_id="e1",
        run_id="r1",
        position=10.0,
        descriptor="citrus",
        intensity="strong",
        assessor="Alice",
        repeatability="consistent",
    )
    ledger.add_gco_event(event)

    data = ledger.to_dict()
    restored = AnalyticalLedger.from_dict(data)

    assert len(restored._gcms_runs) == 1
    assert len(restored._gcms_peaks["r1"]) == 1
    assert restored._gcms_peaks["r1"][0].tentative_identity == "Limonene"
    assert len(restored._hsspme_runs) == 1
    assert restored._hsspme_runs["h1"].fiber == "PDMS 100um"
    assert len(restored._gco_events) == 1
    assert restored._gco_events[0].descriptor == "citrus"
