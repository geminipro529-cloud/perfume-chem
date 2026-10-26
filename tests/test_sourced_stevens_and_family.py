"""Sourced Stevens exponents and odour families on data-spine records (2026-10-25).

A record's own exponent is used only when its provenance names a source; old values
with no source, or copied from the threshold table ("engine.odor_thresholds"), are not.
"""

from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.perception.oav import perceived_intensity_stevens, sourced_stevens_n


@pytest.mark.parametrize(
    ("name", "exponent"),
    [
        ("Benzaldehyde", 0.48),  # Moskowitz, Dravnieks & Klarman 1976, Table 1
        ("Vanillin", 0.35),
        ("Guaiacol", 0.21),
        ("Geraniol", 0.28),  # Cain 1969, Experiment 5
    ],
)
def test_sourced_exponent_is_used(name, exponent):
    record = load_registry().get(name)
    assert record is not None
    assert sourced_stevens_n(record) == pytest.approx(exponent)
    assert perceived_intensity_stevens(16.0, None, exponent=exponent) == pytest.approx(16.0**exponent)


@pytest.mark.parametrize("name", ["Birch Tar", "Cade Oil"])
def test_exponent_copied_from_the_threshold_table_is_not_used(name):
    record = load_registry().get(name)
    if record is None or record.stevens_n is None:
        pytest.skip(f"{name} has no stored exponent")
    assert record.provenance.get("stevens_n") in (None, "", "engine.odor_thresholds")
    assert sourced_stevens_n(record) is None


def test_without_a_sourced_exponent_the_family_default_applies():
    assert perceived_intensity_stevens(16.0, None) == perceived_intensity_stevens(16.0, None, exponent=None)


def test_loaded_odour_family_uses_the_engine_words():
    families = {m.odour_family for m in load_registry().all() if m.odour_family}
    assert families, "no odour_family loaded"
    allowed = {
        "floral", "woody", "gourmand", "citrus", "green", "rose", "iris", "spice", "amber",
        "aromatic", "fruity", "muguet", "smoky", "musk", "aldehydic", "animalic", "herbal",
        "aquatic", "earth", "balsamic", "moss", "lactonic",
    }
    assert families <= allowed, sorted(families - allowed)
