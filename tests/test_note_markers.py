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
    row = _Natural("Lavender EO", "lavender eo", {"linalyl acetate": 0.0027, "linalool": 9.0})
    (reading,) = nm.marker_readings(row)
    assert reading["constituent"] == "linalyl acetate"
    assert reading["air_odt_ppb"] == 2.7
    assert math.isclose(reading["screening_oav"], 1.0)
    assert reading["identified_share"] == 0.7
    assert nm.detects(row)


def test_a_generic_constituent_never_judges_the_note() -> None:
    # Limonene far above its threshold does not make an orange oil detectable (Rule 3).
    row = _Natural("Orange EO", "orange peel eo", {"limonene": 50.0, "octanal": 1e-6})
    assert not nm.detects(row)
    names = {row.name}
    assert ys._note_status([row], names, ["orange"]) == "unknown_physics"


def test_an_uncited_threshold_gives_no_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    # The spine's citral air threshold has no source, so it cannot carry a verdict.
    assert nm.cited_air_odt_ppb("citral") is None
    monkeypatch.setitem(nm.NOTE_MARKERS, "test lemon", (nm.Marker("citral", "citral", "-"),))
    row = _Natural("Lemon EO", "test lemon", {"citral": 1e3})
    assert nm.marker_readings(row) == []
    assert ys._note_status([row], {row.name}, ["lemon"]) == "unknown_physics"


@pytest.mark.parametrize(("ppm", "status"), [(0.0054, "detectable"), (0.0013, "unknown_physics")])
def test_a_marker_below_threshold_keeps_the_note_held_not_missed(ppm, status) -> None:
    row = _Natural("Lavender EO", "lavender eo", {"linalyl acetate": ppm})
    assert ys._note_status([row], {row.name}, ["lavender"]) == status


def test_a_lavender_note_is_judged_through_linalyl_acetate_on_the_card() -> None:
    formula = {"name": "t", "batch_volume_ml": 30.0, "rows": [
        {"material": "Lavender EO (BONTAUX SAS)", "amount": "300", "unit": "uL",
         "active_fraction": "1", "tier": "heart"},
        {"material": "Iso E Super", "amount": "300", "unit": "uL", "active_fraction": "1",
         "tier": "base"},
    ]}
    brief = {"id": "t", "named_notes": [
        {"name": "lavender", "window": "heart", "materials": ["lavender"]}]}
    card = ys.score_formula(formula, brief)
    (note,) = card["name_parts"]["named_notes"]
    assert note["status"] == "detectable" and note["score"] == 1
    assert note["via_marker"]["constituent"] == "linalyl acetate"
    assert note["via_marker"]["material"] == "Lavender EO (BONTAUX SAS)"
    assert card["name_status"] == "SCORED"
    readings = card["diagnostics"]["note_markers"]["lavender"]
    assert readings[0]["screening_oav"] >= 1 and readings[0]["marker_source"].startswith("Guo")
