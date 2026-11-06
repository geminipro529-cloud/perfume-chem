"""Kenny, 5 Nov 2026: no strip tests. Set the MSR geranium and the Orange Peel EO from the literature.

- MySkinRecipes Geranium Bourbon gets the ISO 4731:2012 Bourbon-type midpoints, so it no longer
  shares the generic geranium profile with the Bontoux Geranium EO.
- Orange Peel EO (species not recorded) is read as sweet orange peel oil on the ISO 3140 profile;
  Blood Orange keeps the old orange table.
"""

from __future__ import annotations

from engine.pipeline import natural_absolute_decomposition as nad

BOURBON = "pelargonium bourbon type iso 4731 2012 midpoint profile"
SWEET = "citrus sinensis sweet orange iso 3140 2019 midpoint profile"


def test_msr_geranium_bourbon_has_its_own_iso_profile():
    key, _ = nad._resolve_profile_key("Geranium Bourbon Essential Oil")
    assert key == BOURBON
    rows = {r[0]: r[1] for r in nad.get_constituents("Geranium Bourbon Essential Oil")}
    assert rows["citronellol"] == 0.22 and rows["geraniol"] == 0.16 and rows["linalool"] == 0.095
    assert sum(rows.values()) < 1.0  # midpoints, not renormalized


def test_bontoux_geranium_keeps_the_generic_profile():
    key, _ = nad._resolve_profile_key("Geranium EO")
    assert key == "geranium eo"
    assert nad.get_constituents("Geranium EO") != nad.get_constituents("Geranium Bourbon Essential Oil")


def test_bourbon_profile_names_its_unresolved_rows():
    meta = nad.get_composite_metadata("Geranium Bourbon Essential Oil")
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    names = " ".join(item["name"] for item in nad._PARTIAL_PROFILE_EVIDENCE[BOURBON]["unresolved_constituents"])
    assert "guaia-6,9-diene" in names


def test_orange_peel_reads_as_sweet_orange_and_blood_orange_does_not():
    assert nad._resolve_profile_key("Orange Peel EO")[0] == SWEET
    assert nad._resolve_profile_key("Blood Orange Sicilian")[0] == "orange peel eo"
    assert nad.get_constituents("Orange Peel EO") != nad.get_constituents("Blood Orange Sicilian")
