"""Materials that blanked the gate's 4-hour headspace on Kenny's cards (4 Nov 2026).

Each one now gets a sourced, partial constituent model, so the card prints screening
numbers again while the partial coverage still warns.
"""

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.pipeline.preflight import _natural_composite_coverage_check

_RED_SAFFRON_KEY = "red saffron infusion perfumersworld 5es18560 ifra certificate profile"


def test_red_saffron_infusion_models_only_the_certificate_safranal():
    rows = get_constituents("Red Saffron Infusion")
    assert rows is not None
    assert [row[0] for row in rows] == ["safranal"]
    assert rows[0][1] == pytest.approx(0.000519)  # IFRA certificate 0.0519 %, not rescaled
    meta = get_composite_metadata("Red Saffron Infusion")
    assert meta.profile_key == _RED_SAFFRON_KEY
    assert meta.unresolved_fraction == pytest.approx(1 - 0.000519)
    assert meta.input_authority["composition"]["declared_pct"] == {"safranal (116-26-7)": 0.0519}
    unresolved = {row["name"] for row in meta.unresolved_constituents}
    assert "dipropylene glycol" in unresolved


def test_red_saffron_infusion_prints_screening_headspace_but_still_warns():
    state = build_formula_state({"Red Saffron Infusion": 60.0, "Hedione": 900.0})
    row = next(m for m in state.materials if m.name == "Red Saffron Infusion")
    assert row.physics_status == "SCREENING_SENSITIVITY_ONLY"
    assert row.screening_vapor_ppm is not None and row.screening_vapor_ppm > 0
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert "NATURAL_COMPOSITE_PARTIAL" in row.physics_blockers
    assert _natural_composite_coverage_check(state).status == "WARN"


_GIVCO_KEY = "orris givco 204/2/20 givaudan sds band lower bound profile"


@pytest.mark.parametrize("name", ["Orris Givco 204", "Orris Givco 204/20", "Orris Givco 204/2/20"])
def test_orris_givco_uses_the_givaudan_sds_band_lower_bounds(name):
    rows = get_constituents(name)
    assert rows is not None
    fractions = {row[0]: row[1] for row in rows}
    # Givaudan SDS v4.0 section 3: ">= 50 - < 70" beta-ionone, ">= 25 - < 30" dihydro.
    assert fractions["beta ionone"] == pytest.approx(0.50)
    assert fractions["dihydro beta ionone"] == pytest.approx(0.25)
    assert sum(fractions.values()) == pytest.approx(0.7745)  # floors only, never rescaled
    meta = get_composite_metadata(name)
    assert meta.profile_key == _GIVCO_KEY
    assert meta.composition_basis == "SDS_BAND_LOWER_BOUND_NOMINAL_MODEL_PROXY"
    unresolved = {row["name"] for row in meta.unresolved_constituents}
    assert {"acetyl cedrene", "ethyl heptanoate", "Okoumal"} <= unresolved


def test_orris_givco_prints_screening_headspace_but_still_warns():
    state = build_formula_state({"Orris Givco 204": 100.0, "Hedione": 900.0})
    row = next(m for m in state.materials if m.name == "Orris Givco 204")
    assert row.physics_status == "SCREENING_SENSITIVITY_ONLY"
    assert row.screening_vapor_ppm is not None and row.screening_vapor_ppm > 0
    assert "NATURAL_COMPOSITE_PARTIAL" in row.physics_blockers


_OPOPONAX_KEY = "commiphora guidottii opoponax resinoid baser 2003 oil scaled profile"


@pytest.mark.parametrize("name", ["Opoponax Resinoid", "Opoponax Resinoid (50% in DEP)"])
def test_opoponax_resinoid_scales_the_baser_oil_by_the_lower_bound_oil_fraction(name):
    rows = get_constituents(name)
    assert rows is not None
    fractions = {row[0]: row[1] for row in rows}
    # Baser 2003 oil %: decanol 1.2, limonene 0.2; 5% oil in the resinoid, never rescaled.
    assert fractions["1-decanol"] == pytest.approx(0.012 * 0.05)
    assert fractions["limonene"] == pytest.approx(0.002 * 0.05)
    meta = get_composite_metadata(name)
    assert meta.profile_key == _OPOPONAX_KEY
    assert meta.input_authority["composition"]["resinoid_volatile_oil_fraction"] == 0.05
    unresolved = {row["name"]: row for row in meta.unresolved_constituents}
    assert unresolved["(E)-beta-ocimene"]["reported_fraction"] == pytest.approx(0.0165)
    assert unresolved["(E)-beta-ocimene"]["missing_input"] == "NO_PRIMARY_AIR_ODT"


def test_opoponax_resinoid_prints_screening_headspace_but_still_warns():
    state = build_formula_state({"Opoponax Resinoid": 100.0, "Hedione": 900.0})
    row = next(m for m in state.materials if m.name == "Opoponax Resinoid")
    assert row.physics_status == "SCREENING_SENSITIVITY_ONLY"
    assert row.sources["oav_model"] == "modeled:natural_constituent_composite"
    assert "NATURAL_COMPOSITE_PARTIAL" in row.physics_blockers
