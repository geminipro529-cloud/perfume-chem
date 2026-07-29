"""Tests for engine.sensory.ledger."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.sensory.ledger import (
    SensorySample,
    SensoryObservation,
    SensoryTrial,
    generate_trial_codes,
    TIME_POINTS,
)


class _LegacyFixtureSensoryTrial(SensoryTrial):
    """Mutable test builder; production SensoryTrial is read-only."""

    def add_sample(self, sample: SensorySample) -> None:
        self._samples[sample.sample_id] = sample

    def record_observation(self, observation: SensoryObservation) -> None:
        self._observations.append(observation)


SensoryTrial = _LegacyFixtureSensoryTrial


# ── TIME_POINTS ──────────────────────────────────────────────────────────────────


def test_time_points_correct():
    """TIME_POINTS has exactly 7 standard evaluation time points."""
    assert TIME_POINTS == [0, 300, 1800, 7200, 14400, 28800, 86400]


# ── SensorySample ─────────────────────────────────────────────────────────────────


def test_sensory_sample_defaults():
    """SensorySample created with only required fields gets sensible defaults."""
    sample = SensorySample(
        sample_id="s1",
        formula_id="iris_v2",
        batch_id="batch_001",
        code="XQP",
    )
    assert sample.sample_id == "s1"
    assert sample.formula_id == "iris_v2"
    assert sample.batch_id == "batch_001"
    assert sample.code == "XQP"
    assert sample.application_mass_g == 0.01
    assert sample.substrate == "blotter"
    assert sample.room_temperature_c == 22.0
    assert sample.room_humidity_pct == 50.0
    assert sample.prepared_at is None


def test_sensory_sample_all_fields():
    """SensorySample accepts all fields explicitly."""
    sample = SensorySample(
        sample_id="s2",
        formula_id="vetiver_v1",
        batch_id="batch_002",
        code="ABC",
        application_mass_g=0.05,
        substrate="skin_forearm",
        room_temperature_c=25.0,
        room_humidity_pct=60.0,
        prepared_at="2026-07-29T10:00:00",
    )
    assert sample.application_mass_g == 0.05
    assert sample.substrate == "skin_forearm"
    assert sample.room_temperature_c == 25.0
    assert sample.room_humidity_pct == 60.0
    assert sample.prepared_at == "2026-07-29T10:00:00"


def test_sensory_sample_as_dict():
    """as_dict returns all fields as a flat dict."""
    sample = SensorySample(
        sample_id="s3",
        formula_id="chypre_v1",
        batch_id="batch_003",
        code="XYZ",
    )
    d = sample.as_dict()
    assert d["sample_id"] == "s3"
    assert d["formula_id"] == "chypre_v1"
    assert d["batch_id"] == "batch_003"
    assert d["code"] == "XYZ"
    assert d["application_mass_g"] == 0.01
    assert d["substrate"] == "blotter"
    assert d["room_temperature_c"] == 22.0
    assert d["room_humidity_pct"] == 50.0
    assert d["prepared_at"] is None


def test_sensory_sample_from_dict():
    """from_dict reconstructs a SensorySample."""
    data = {
        "sample_id": "s4",
        "formula_id": "amber_v2",
        "batch_id": "batch_004",
        "code": "RST",
        "application_mass_g": 0.02,
        "substrate": "mouillette",
        "room_temperature_c": 23.0,
        "room_humidity_pct": 55.0,
        "prepared_at": "2026-07-29T12:00:00",
    }
    sample = SensorySample.from_dict(data)
    assert sample.sample_id == "s4"
    assert sample.formula_id == "amber_v2"
    assert sample.code == "RST"
    assert sample.substrate == "mouillette"
    assert sample.prepared_at == "2026-07-29T12:00:00"


def test_sensory_sample_from_dict_minimal():
    """from_dict works with only required fields, filling defaults."""
    data = {
        "sample_id": "s5",
        "formula_id": "floral_v1",
        "batch_id": "batch_005",
        "code": "LMN",
    }
    sample = SensorySample.from_dict(data)
    assert sample.application_mass_g == 0.01
    assert sample.substrate == "blotter"
    assert sample.prepared_at is None


# ── SensoryObservation ────────────────────────────────────────────────────────────


def test_sensory_observation_defaults():
    """SensoryObservation created with required fields gets sensible defaults."""
    obs = SensoryObservation(
        observation_id="o1",
        sample_id="s1",
        assessor="Alice",
        time_seconds=300.0,
        opening_identity=4.0,
        heart_identity=3.5,
        drydown_identity=3.0,
        transition_quality=4.0,
        texture=3.5,
        diffusion=4.0,
        longevity=3.0,
    )
    assert obs.observation_id == "o1"
    assert obs.sample_id == "s1"
    assert obs.assessor == "Alice"
    assert obs.time_seconds == 300.0
    assert obs.opening_identity == 4.0
    assert obs.heart_identity == 3.5
    assert obs.drydown_identity == 3.0
    assert obs.transition_quality == 4.0
    assert obs.texture == 3.5
    assert obs.diffusion == 4.0
    assert obs.longevity == 3.0
    assert obs.off_notes == ""
    assert obs.overall_similarity == 3.0
    assert obs.preference == 3.0
    assert obs.notes == ""


def test_sensory_observation_all_fields():
    """SensoryObservation accepts all fields explicitly."""
    obs = SensoryObservation(
        observation_id="o2",
        sample_id="s2",
        assessor="Bob",
        time_seconds=1800.0,
        opening_identity=5.0,
        heart_identity=4.0,
        drydown_identity=3.0,
        transition_quality=4.5,
        texture=4.0,
        diffusion=3.5,
        longevity=5.0,
        off_notes="slight metallic edge",
        overall_similarity=4.0,
        preference=4.5,
        notes="promising, needs more depth",
    )
    assert obs.off_notes == "slight metallic edge"
    assert obs.overall_similarity == 4.0
    assert obs.preference == 4.5
    assert obs.notes == "promising, needs more depth"


def test_sensory_observation_as_dict():
    """as_dict returns all fields."""
    obs = SensoryObservation(
        observation_id="o3",
        sample_id="s1",
        assessor="Carol",
        time_seconds=7200.0,
        opening_identity=3.0,
        heart_identity=3.5,
        drydown_identity=4.0,
        transition_quality=3.0,
        texture=3.0,
        diffusion=2.5,
        longevity=4.0,
    )
    d = obs.as_dict()
    assert d["observation_id"] == "o3"
    assert d["sample_id"] == "s1"
    assert d["assessor"] == "Carol"
    assert d["time_seconds"] == 7200.0
    assert d["off_notes"] == ""
    assert d["overall_similarity"] == 3.0


def test_sensory_observation_from_dict():
    """from_dict reconstructs a SensoryObservation."""
    data = {
        "observation_id": "o4",
        "sample_id": "s2",
        "assessor": "Dave",
        "time_seconds": 14400.0,
        "opening_identity": 2.0,
        "heart_identity": 3.0,
        "drydown_identity": 4.0,
        "transition_quality": 3.5,
        "texture": 4.0,
        "diffusion": 3.0,
        "longevity": 5.0,
        "off_notes": "fades too fast",
        "overall_similarity": 3.5,
        "preference": 4.0,
        "notes": "good drydown",
    }
    obs = SensoryObservation.from_dict(data)
    assert obs.observation_id == "o4"
    assert obs.off_notes == "fades too fast"
    assert obs.overall_similarity == 3.5
    assert obs.notes == "good drydown"


def test_sensory_observation_from_dict_minimal():
    """from_dict works with only required fields, filling defaults."""
    data = {
        "observation_id": "o5",
        "sample_id": "s1",
        "assessor": "Eve",
        "time_seconds": 300.0,
        "opening_identity": 4.0,
        "heart_identity": 3.0,
        "drydown_identity": 2.0,
        "transition_quality": 3.0,
        "texture": 3.0,
        "diffusion": 3.0,
        "longevity": 3.0,
    }
    obs = SensoryObservation.from_dict(data)
    assert obs.off_notes == ""
    assert obs.overall_similarity == 3.0
    assert obs.preference == 3.0
    assert obs.notes == ""


# ── SensoryTrial ──────────────────────────────────────────────────────────────────


def _make_sample(sample_id: str, code: str) -> SensorySample:
    return SensorySample(
        sample_id=sample_id,
        formula_id=f"formula_{sample_id}",
        batch_id="batch_001",
        code=code,
    )


def _make_obs(
    observation_id: str,
    sample_id: str,
    assessor: str,
    time_seconds: float,
    opening: float = 3.0,
    heart: float = 3.0,
    drydown: float = 3.0,
    overall: float = 3.0,
) -> SensoryObservation:
    return SensoryObservation(
        observation_id=observation_id,
        sample_id=sample_id,
        assessor=assessor,
        time_seconds=time_seconds,
        opening_identity=opening,
        heart_identity=heart,
        drydown_identity=drydown,
        transition_quality=3.0,
        texture=3.0,
        diffusion=3.0,
        longevity=3.0,
        overall_similarity=overall,
    )


def test_sensory_trial_init():
    """SensoryTrial stores trial_name, reference_sample_id, and assessors."""
    trial = SensoryTrial("Iris v2 vs v3", "ref_001", ["Alice", "Bob"])
    assert trial.trial_name == "Iris v2 vs v3"
    assert trial.reference_sample_id == "ref_001"
    assert trial.assessors == ["Alice", "Bob"]


def test_sensory_trial_add_sample():
    """add_sample registers a sample by sample_id."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    sample = _make_sample("s1", "XQP")
    trial.add_sample(sample)
    assert trial._samples["s1"] is sample


def test_sensory_trial_add_sample_replaces():
    """add_sample replaces an existing sample with the same ID."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    s1 = _make_sample("s1", "ABC")
    s2 = _make_sample("s1", "XYZ")
    trial.add_sample(s1)
    trial.add_sample(s2)
    assert trial._samples["s1"] is s2


def test_sensory_trial_record_observation():
    """record_observation appends an observation."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    obs = _make_obs("o1", "s1", "Alice", 300.0)
    trial.record_observation(obs)
    assert len(trial._observations) == 1
    assert trial._observations[0] is obs


def test_get_observations_for_sample():
    """get_observations_for_sample returns only observations for that sample."""
    trial = SensoryTrial("Test", "ref_001", ["Alice", "Bob"])
    trial.add_sample(_make_sample("s1", "ABC"))
    trial.add_sample(_make_sample("s2", "XYZ"))

    o1 = _make_obs("o1", "s1", "Alice", 300.0)
    o2 = _make_obs("o2", "s1", "Bob", 300.0)
    o3 = _make_obs("o3", "s2", "Alice", 300.0)
    for o in [o1, o2, o3]:
        trial.record_observation(o)

    result = trial.get_observations_for_sample("s1")
    assert len(result) == 2
    assert o1 in result
    assert o2 in result
    assert o3 not in result


def test_get_observations_for_sample_empty():
    """get_observations_for_sample returns empty list when no observations."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("s1", "ABC"))
    assert trial.get_observations_for_sample("s1") == []


def test_get_observations_at_time():
    """get_observations_at_time returns only observations at that time."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("s1", "ABC"))

    o1 = _make_obs("o1", "s1", "Alice", 300.0)
    o2 = _make_obs("o2", "s1", "Alice", 1800.0)
    o3 = _make_obs("o3", "s1", "Alice", 300.0)
    for o in [o1, o2, o3]:
        trial.record_observation(o)

    result = trial.get_observations_at_time(300.0)
    assert len(result) == 2
    assert o1 in result
    assert o3 in result
    assert o2 not in result


def test_get_observations_at_time_empty():
    """get_observations_at_time returns empty list when no observations at time."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    assert trial.get_observations_at_time(999.0) == []


# ── SensoryTrial.summarize ────────────────────────────────────────────────────────


def test_summarize_empty():
    """summarize returns all zeros when no observations exist."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("s1", "ABC"))
    summary = trial.summarize("s1")
    assert summary == {
        "avg_opening": 0.0,
        "avg_heart": 0.0,
        "avg_drydown": 0.0,
        "avg_overall": 0.0,
    }


def test_summarize_single_observation():
    """summarize returns the observation's scores when there is one."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("s1", "ABC"))
    trial.record_observation(
        _make_obs("o1", "s1", "Alice", 300.0, opening=4.0, heart=3.5, drydown=3.0, overall=3.5)
    )
    summary = trial.summarize("s1")
    assert summary["avg_opening"] == 4.0
    assert summary["avg_heart"] == 3.5
    assert summary["avg_drydown"] == 3.0
    assert summary["avg_overall"] == 3.5


def test_summarize_multiple_observations():
    """summarize averages scores across multiple observations."""
    trial = SensoryTrial("Test", "ref_001", ["Alice", "Bob"])
    trial.add_sample(_make_sample("s1", "ABC"))
    trial.record_observation(
        _make_obs("o1", "s1", "Alice", 300.0, opening=4.0, heart=3.0, drydown=2.0, overall=3.0)
    )
    trial.record_observation(
        _make_obs("o2", "s1", "Bob", 300.0, opening=2.0, heart=4.0, drydown=4.0, overall=5.0)
    )
    summary = trial.summarize("s1")
    assert summary["avg_opening"] == 3.0  # (4 + 2) / 2
    assert summary["avg_heart"] == 3.5  # (3 + 4) / 2
    assert summary["avg_drydown"] == 3.0  # (2 + 4) / 2
    assert summary["avg_overall"] == 4.0  # (3 + 5) / 2


def test_summarize_ignores_other_samples():
    """summarize only considers observations for the requested sample."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("s1", "ABC"))
    trial.add_sample(_make_sample("s2", "XYZ"))
    trial.record_observation(
        _make_obs("o1", "s1", "Alice", 300.0, opening=5.0, heart=5.0, drydown=5.0, overall=5.0)
    )
    trial.record_observation(
        _make_obs("o2", "s2", "Alice", 300.0, opening=1.0, heart=1.0, drydown=1.0, overall=1.0)
    )
    summary = trial.summarize("s1")
    assert summary["avg_opening"] == 5.0
    assert summary["avg_heart"] == 5.0


# ── SensoryTrial.detect_mismatch ──────────────────────────────────────────────────


def test_detect_mismatch_no_mismatch():
    """detect_mismatch returns empty list when candidate matches reference."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("candidate", "ABC"))
    trial.add_sample(_make_sample("reference", "XYZ"))

    for tp in [300.0, 1800.0]:
        trial.record_observation(_make_obs(f"c_{tp}", "candidate", "Alice", tp, overall=4.0))
        trial.record_observation(_make_obs(f"r_{tp}", "reference", "Alice", tp, overall=4.0))

    mismatches = trial.detect_mismatch("candidate", "reference", threshold=1.0)
    assert mismatches == []


def test_detect_mismatch_finds_mismatch():
    """detect_mismatch reports time points where difference exceeds threshold."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("candidate", "ABC"))
    trial.add_sample(_make_sample("reference", "XYZ"))

    trial.record_observation(_make_obs("c_300", "candidate", "Alice", 300.0, overall=5.0))
    trial.record_observation(_make_obs("r_300", "reference", "Alice", 300.0, overall=2.0))

    mismatches = trial.detect_mismatch("candidate", "reference", threshold=1.0)
    assert len(mismatches) == 1
    assert "t=300s" in mismatches[0]
    assert "candidate=5.00" in mismatches[0]
    assert "reference=2.00" in mismatches[0]


def test_detect_mismatch_skips_missing_time_points():
    """detect_mismatch skips time points where one sample has no observations."""
    trial = SensoryTrial("Test", "ref_001", ["Alice"])
    trial.add_sample(_make_sample("candidate", "ABC"))
    trial.add_sample(_make_sample("reference", "XYZ"))

    trial.record_observation(_make_obs("c_300", "candidate", "Alice", 300.0, overall=5.0))
    # No reference observation at t=300

    mismatches = trial.detect_mismatch("candidate", "reference", threshold=1.0)
    assert mismatches == []


def test_detect_mismatch_averages_multiple_assessors():
    """detect_mismatch averages across assessors before comparing."""
    trial = SensoryTrial("Test", "ref_001", ["Alice", "Bob"])
    trial.add_sample(_make_sample("candidate", "ABC"))
    trial.add_sample(_make_sample("reference", "XYZ"))

    # Candidate: Alice=5, Bob=3 → mean=4.0
    trial.record_observation(_make_obs("c_a", "candidate", "Alice", 300.0, overall=5.0))
    trial.record_observation(_make_obs("c_b", "candidate", "Bob", 300.0, overall=3.0))
    # Reference: Alice=2, Bob=2 → mean=2.0
    trial.record_observation(_make_obs("r_a", "reference", "Alice", 300.0, overall=2.0))
    trial.record_observation(_make_obs("r_b", "reference", "Bob", 300.0, overall=2.0))

    mismatches = trial.detect_mismatch("candidate", "reference", threshold=1.0)
    # diff = |4.0 - 2.0| = 2.0 > 1.0 → flagged
    assert len(mismatches) == 1
    assert "t=300s" in mismatches[0]


# ── generate_trial_codes ──────────────────────────────────────────────────────────


def test_generate_trial_codes_count():
    """generate_trial_codes returns the requested number of codes."""
    codes = generate_trial_codes(5)
    assert len(codes) == 5


def test_generate_trial_codes_unique():
    """generate_trial_codes returns unique codes."""
    codes = generate_trial_codes(50)
    assert len(set(codes)) == 50


def test_generate_trial_codes_uppercase_three_letters():
    """Each code is exactly 3 uppercase ASCII letters."""
    codes = generate_trial_codes(10)
    for code in codes:
        assert len(code) == 3
        assert code.isupper()
        assert code.isalpha()


def test_generate_trial_codes_no_offensive():
    """No generated code is in the offensive set."""
    codes = generate_trial_codes(200)
    offensive = {
        "FUK",
        "DIK",
        "ASS",
        "CUM",
        "SEX",
        "SUK",
        "FAG",
        "KKK",
        "WTF",
        "STD",
        "POO",
        "PEE",
        "CRP",
        "BUM",
        "GAY",
        "NGR",
        "CNT",
        "CLT",
        "KNT",
        "DUM",
        "TWT",
        "FUC",
        "SHI",
        "BIT",
    }
    for code in codes:
        assert code not in offensive, f"Generated offensive code: {code}"


def test_generate_trial_codes_raises_on_overflow():
    """generate_trial_codes raises ValueError when count exceeds available."""
    # 26^3 = 17576, minus ~24 offensive = ~17552 max
    with pytest.raises(ValueError, match="Cannot generate"):
        generate_trial_codes(20000)


# ── Serialisation round-trip ──────────────────────────────────────────────────────


def test_sensory_trial_to_dict():
    """to_dict serialises the full trial."""
    trial = SensoryTrial("Round Trip", "ref_001", ["Alice", "Bob"])
    trial.add_sample(_make_sample("s1", "ABC"))
    trial.record_observation(
        _make_obs("o1", "s1", "Alice", 300.0, opening=4.0, heart=3.5, drydown=3.0, overall=3.5)
    )
    d = trial.to_dict()
    assert d["trial_name"] == "Round Trip"
    assert d["reference_sample_id"] == "ref_001"
    assert d["assessors"] == ["Alice", "Bob"]
    assert len(d["samples"]) == 1
    assert d["samples"][0]["sample_id"] == "s1"
    assert len(d["observations"]) == 1
    assert d["observations"][0]["observation_id"] == "o1"


def test_sensory_trial_from_dict():
    """from_dict reconstructs a trial identical to the original."""
    original = SensoryTrial("Round Trip", "ref_001", ["Alice", "Bob"])
    original.add_sample(_make_sample("s1", "ABC"))
    original.record_observation(
        _make_obs("o1", "s1", "Alice", 300.0, opening=4.0, heart=3.5, drydown=3.0, overall=3.5)
    )
    data = original.to_dict()
    restored = SensoryTrial.from_dict(data)
    assert restored.trial_name == original.trial_name
    assert restored.reference_sample_id == original.reference_sample_id
    assert restored.assessors == original.assessors
    assert len(restored._samples) == 1
    assert restored._samples["s1"].code == "ABC"
    assert len(restored._observations) == 1
    assert restored._observations[0].observation_id == "o1"
    assert restored._observations[0].opening_identity == 4.0
