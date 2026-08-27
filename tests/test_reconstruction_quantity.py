"""Tests for engine.reconstruction.quantity_inference."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.quantity_inference import (
    override_rank_prior,
    functional_correction,
    potency_correction,
    reconcile_total,
    PotencyCorrection,
    FunctionalConstraint,
    DoseRange,
)


def test_override_no_constraints():
    prior = {"A": 300, "B": 200, "C": 100}
    result = override_rank_prior(prior, [], [])
    assert result == prior


def test_override_with_potency():
    prior = {"A": 300, "B": 200}
    corrections = [PotencyCorrection(material="A", factor=0.5, justification="test", source="test")]
    result = override_rank_prior(prior, [], corrections)
    assert result["A"] == 150.0
    assert result["B"] == 200.0


def test_override_with_constraints():
    prior = {"A": 300, "B": 200}
    constraints = [
        FunctionalConstraint(
            material="A",
            role="test",
            min_dose=500,
            max_dose=600,
            required_oav=1.0,
            notes="",
        )
    ]
    result = override_rank_prior(prior, constraints, [])
    assert result["A"] >= 500


def test_functional_correction_radiance():
    factor = functional_correction("Hedione", "radiance amplifier", "floral")
    assert factor > 1.0


def test_functional_correction_trace():
    factor = functional_correction("Indole", "trace accent", "animalic")
    assert factor < 1.0


def test_potency_correction_high_potency():
    factor = potency_correction("Geosmin", 0.000006)
    assert factor < 0.1


def test_potency_correction_weak():
    factor = potency_correction("DPG", 10000.0)
    assert factor > 1.0


def test_reconcile_total():
    doses = {"A": 100, "B": 200, "C": 300}
    result = reconcile_total(doses, 300)
    assert abs(sum(result.values()) - 300) < 0.1


def test_dose_range():
    dr = DoseRange(median=100, p05=80, p95=120)
    assert dr.median == 100
    assert dr.p05 < dr.p95
