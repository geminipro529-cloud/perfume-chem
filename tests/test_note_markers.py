"""Plan A4: a natural's note is judged through one cited marker constituent, never a sum."""

from __future__ import annotations

import math

import pytest

from engine.formulation_intelligence import note_markers as nm
from engine.formulation_intelligence import yardstick as ys
from engine.pipeline.natural_absolute_decomposition import composite_headspace


class _Natural:
    """Stand-in for a simulator MaterialState row of a decomposed natural."""

    def __init__(self, name: str, profile_key: str, vapour: dict[str, float]) -> None:
        self.name = name
        self.screening_oav = 1e6  # a summed natural OAV: never a verdict by itself
        self.odt_air_ppm = None
        self.missing_fields: tuple = ()
        self.has_constituent_resolved_oav = True
        self.natural_composite_metadata = {"profile_key": profile_key,
                                           "characterized_fraction": 0.7}
        self.constituent_vapor_ppm = tuple(vapour.items())


def test_headspace_reports_each_constituent_and_they_sum_to_the_total() -> None:
    result = composite_headspace("lavender eo", 0.05, 1.0)
    per = dict(result.constituent_vapor_ppm)
    assert {"linalool", "linalyl acetate"} <= set(per)
    assert math.isclose(sum(per.values()), result.vapor_ppm, rel_tol=1e-9)


def test_a_cited_marker_reading_is_its_vapour_over_its_spine_threshold() -> None:
    # Coumarin's cited air threshold is 0.7 ppb (Rychlik et al. 1998), i.e. 0.0007 ppm.
    row = _Natural("Tonka Bean Absolute", "tonka bean absolute", {"coumarin": 0.0007})
    (reading,) = nm.marker_readings(row)
    assert reading["constituent"] == "coumarin"
    assert reading["air_odt_ppb"] == 0.7
    assert math.isclose(reading["screening_oav"], 1.0) and reading["reaches_threshold"]
    assert reading["identified_share"] == 0.7
    assert reading["marker_source"].startswith("Kim D-S, Iida F (2022)")
    assert nm.detects(row)


@pytest.mark.parametrize(
    ("name", "key", "vapour"),
    [
        # Limonene far above its threshold does not make an orange oil detectable (Rule 3).
        ("Orange EO", "orange peel eo", {"limonene": 50.0, "octanal": 5.0}),
        # Lavender's character is emergent: no single constituent judges it.
        ("Lavender EO", "lavender eo", {"linalool": 50.0, "linalyl acetate": 50.0}),
    ],
)
def test_a_natural_with_no_single_impact_compound_stays_held(name, key, vapour) -> None:
    row = _Natural(name, key, vapour)
    assert nm.marker_readings(row) == [] and not nm.detects(row)
    assert ys._note_status([row], {row.name}, [name.split()[0].lower()]) == "unknown_physics"


def test_an_uncited_threshold_gives_no_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    # The spine's citral air threshold has no source, so it cannot carry a verdict.
    assert nm.cited_air_odt_ppb("citral") is None
    # Linalool is declared PEER_CROSS, but verify_odt downgrades it: the effective level rules.
    from engine.odor_thresholds import verify_odt

    assert verify_odt("linalool")["declared_vfy"] == "PEER_CROSS"
    assert nm.cited_air_odt_ppb("linalool") is None
    monkeypatch.setitem(nm.NOTE_MARKERS, "test lemon", (nm.Marker("citral", "citral", "-"),))
    row = _Natural("Lemon EO", "test lemon", {"citral": 1e3})
    assert nm.marker_readings(row) == []
    assert ys._note_status([row], {row.name}, ["lemon"]) == "unknown_physics"


@pytest.mark.parametrize(("ppm", "status"), [(0.0014, "detectable"), (0.00035, "unknown_physics")])
def test_a_marker_below_threshold_keeps_the_note_held_not_missed(ppm, status) -> None:
    row = _Natural("Tonka Bean Absolute", "tonka bean absolute", {"coumarin": ppm})
    assert ys._note_status([row], {row.name}, ["tonka"]) == status


def test_a_tonka_note_is_judged_through_coumarin_on_the_card() -> None:
    formula = {"name": "t", "batch_volume_ml": 30.0, "rows": [
        {"material": "Tonka Bean Absolute", "amount": "1500", "unit": "uL",
         "active_fraction": "0.1", "fraction_basis": "mass_fraction", "carrier": "DPG",
         "tier": "base"},
        {"material": "Iso E Super", "amount": "300", "unit": "uL", "active_fraction": "1",
         "tier": "base"},
    ]}
    brief = {"id": "t", "named_notes": [
        {"name": "sweet", "window": "drydown", "materials": ["tonka"]}]}
    card = ys.score_formula(formula, brief)
    (note,) = card["name_parts"]["named_notes"]
    assert note["status"] == "detectable" and note["score"] == 1
    assert note["via_marker"] == {"material": "Tonka Bean Absolute", "constituent": "coumarin",
                                  "identified_share": 0.8397}
    assert card["name_status"] == "SCORED"
    readings = card["diagnostics"]["note_markers"]["sweet (drydown)"]
    assert readings[0]["reaches_threshold"] and readings[0]["screening_oav"] >= 1
    # Rule 1: the marker's OAV number appears only under diagnostics.
    import json

    assert "screening_oav" not in json.dumps({k: v for k, v in card.items() if k != "diagnostics"})
