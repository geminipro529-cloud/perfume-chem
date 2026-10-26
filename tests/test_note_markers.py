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
    # Iso E Super is declared PEER_EST, but its ethanol value conflicts with the runtime
    # one, so verify_odt downgrades it: the effective level rules.
    from engine.odor_thresholds import ODT_VERIFICATION, verify_odt

    assert verify_odt("iso e super")["declared_vfy"] == "PEER_EST"
    assert verify_odt("iso e super")["vfy"] == "UNVERIFIED"
    assert nm.cited_air_odt_ppb("iso e super") is None
    # A threshold with no source cannot carry a verdict. Citral's own is cited since the
    # 2026-10-25 literature batch, so its evidence is blanked for this check.
    monkeypatch.setitem(ODT_VERIFICATION, "citral", {"vfy": "UNVERIFIED", "sources": []})
    assert nm.cited_air_odt_ppb("citral") is None
    monkeypatch.setitem(nm.NOTE_MARKERS, "test lemon", (nm.Marker("citral", "citral", "-"),))
    row = _Natural("Lemon EO", "test lemon", {"citral": 1e3})
    assert nm.marker_readings(row) == []
    assert ys._note_status([row], {row.name}, ["lemon"]) == "unknown_physics"


@pytest.mark.parametrize(("ppm", "status"), [(0.0014, "detectable"), (0.00035, "unknown_physics")])
def test_a_marker_below_threshold_keeps_the_note_held_not_missed(ppm, status) -> None:
    row = _Natural("Tonka Bean Absolute", "tonka bean absolute", {"coumarin": ppm})
    assert ys._note_status([row], {row.name}, ["tonka"]) == status


def test_other_constituents_never_add_to_the_marker() -> None:
    # Rule 4: half of coumarin's threshold stays half, however loud the rest of the absolute is.
    row = _Natural("Tonka Bean Absolute", "tonka bean absolute",
                   {"coumarin": 0.00035, "ethyl cinnamate": 10.0, "benzoic acid": 10.0})
    (reading,) = nm.marker_readings(row)
    assert math.isclose(reading["screening_oav"], 0.5) and not reading["reaches_threshold"]
    assert ys._note_status([row], {row.name}, ["tonka"]) == "unknown_physics"


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


def test_the_marker_is_read_in_the_notes_own_window() -> None:
    # 150 uL of 10% tonka: coumarin is far below its threshold on the first spray and far
    # above it in the drydown, so each note is judged from its own window's vapour.
    formula = {"name": "t", "batch_volume_ml": 30.0, "rows": [
        {"material": "Tonka Bean Absolute", "amount": "150", "unit": "uL",
         "active_fraction": "0.1", "fraction_basis": "mass_fraction", "carrier": "DPG",
         "tier": "base"},
        {"material": "Iso E Super", "amount": "300", "unit": "uL", "active_fraction": "1",
         "tier": "base"},
    ]}
    brief = {"id": "t", "named_notes": [
        {"name": "sweet early", "window": "opening", "materials": ["tonka"]},
        {"name": "sweet", "window": "drydown", "materials": ["tonka"]}]}
    card = ys.score_formula(formula, brief)
    early, late = card["name_parts"]["named_notes"]
    assert early["status"] == "unknown_physics" and "via_marker" not in early
    assert late["status"] == "detectable" and late["via_marker"]["constituent"] == "coumarin"
    readings = card["diagnostics"]["note_markers"]
    assert not readings["sweet early (opening)"][0]["reaches_threshold"]
    assert readings["sweet (drydown)"][0]["reaches_threshold"]
