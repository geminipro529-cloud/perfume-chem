"""Regression contract for the 2026-09-07 ingredient-intelligence repair.

Entity/role evidence is not stock, sensory, safety, or release authority.
"""

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_all_profiles, get_profile
from engine.name_utils import names_match
from engine.pipeline.natural_absolute_decomposition import get_constituents


@pytest.mark.parametrize(
    "label", ["Hydroxycitronellal", "hydroxycitronellal", "7-Hydroxycitronellal", "107-75-5"]
)
def test_hydroxycitronellal_is_a_muguet_character_material(label):
    profile = get_profile(label)
    assert profile is not None
    assert profile.name == "Hydroxycitronellal"
    assert profile.cas == "107-75-5"
    assert (profile.note, profile.role, profile.or_family) == ("heart", "character", "muguet")
    assert "muguet_character" in profile.formulation_roles
    assert profile.evidence["role"]["status"] == "SOURCE_BACKED_ROLE_INTERPRETATION"


def test_hydroxycitronellol_stays_a_distinct_historical_chemical():
    aldehyde = get_profile("Hydroxycitronellal")
    diol = get_profile("Hydroxycitronellol")
    assert diol is not None
    assert diol.cas == "107-74-4"
    assert diol.mw == pytest.approx(174.28)
    assert diol.role == "modifier"
    assert diol.or_family == "rose"
    assert aldehyde.odt != diol.odt
    assert not names_match(aldehyde.name, diol.name)
    assert get_profile("Hydroxycitronell") is None


@pytest.mark.parametrize(
    "name,mw",
    [
        ("Florol", 172.26),
        ("Bourgeonal", 190.28),
        ("Mayol", 156.26),
        ("Floralozone", 190.28),
        ("Apritone", 220.35),
        ("Allyl Amyl Glycolate", 186.25),
        ("Ebanol", 208.34),
        ("Ethyl Safranate", 194.27),
    ],
)
def test_confirmed_entity_mass_matches_profile_and_pipeline_registry(name, mw):
    profile = get_profile(name)
    material = load_registry().get(name)
    assert profile.mw == pytest.approx(mw)
    assert material.mw_g_mol == pytest.approx(mw)
    assert profile.evidence["mw"]["status"] == "SOURCE_BACKED_ENTITY_MASS"
    assert profile.evidence["mw"]["sources"]


def test_florol_is_in_muguet_family_without_forcing_same_role():
    assert get_profile("Florol").or_family == "muguet"
    assert get_profile("Florol").role == "modifier"


def test_geranium_profile_is_natural_proxy_not_a_bontoux_lot_assay():
    profile = get_profile("Geranium EO (Pelargonium graveolens flower oil)")
    assert profile is not None
    assert profile.name == "Geranium EO"
    assert profile.material_kind == "NATURAL_MIXTURE"
    assert profile.or_family == "rose"
    assert profile.evidence["mw"]["status"] == "COMPOSITE_REQUIRED_NO_ENTITY_MASS"
    assert profile.mw is profile.vp is profile.clogp is None
    assert "Bontoux" not in profile.name
    assert get_constituents("Geranium EO")
    assert get_profile("Geranium Flower EO") is None  # no new stock/grade alias


def test_opaque_lilyreal_is_not_promoted_to_a_single_chemical():
    profile = get_profile("Lilyreal ND")
    assert profile.material_kind == "OPAQUE_PREBLEND"
    assert profile.cas is None
    assert profile.evidence["mw"]["status"] == "OPAQUE_BLEND_PROXY"


def test_hydroxycitronellal_pressure_preserves_temperature_and_source_units():
    evidence = get_profile("Hydroxycitronellal").evidence["vp"]
    assert evidence["status"] == "HOLD_REFERENCE_TEMPERATURE_MISMATCH"
    assert evidence["reference_temperature_c"] == 20
    assert evidence["reference_value_hpa"] == pytest.approx(0.005472)
    assert evidence["reference_value_pa"] == pytest.approx(0.5472)
    assert get_profile("Hydroxycitronellal").vp == pytest.approx(0.005)


def test_heuristic_gamma_and_hedonics_are_explicit_not_measurements():
    hca = get_profile("Hydroxycitronellal")
    diol = get_profile("Hydroxycitronellol")
    assert hca.evidence["activity_coef"]["status"] == "IDEAL_DEFAULT_UNMEASURED"
    assert diol.evidence["activity_coef"]["status"] == "HEURISTIC_OVERRIDE"
    assert hca.evidence["hedonic"]["status"] == "HEURISTIC_OVERRIDE"
    assert diol.evidence["hedonic"]["status"] == "CHARACTER_DERIVED_HEURISTIC"
    for profile in get_all_profiles().values():
        assert profile.evidence["activity_coef"]["status"]
        assert profile.evidence["hedonic"]["status"]


def test_existing_correct_entity_masses_are_not_replaced_from_bad_cache():
    for name, mw in [("Peonile", 197.27), ("Aurantiol", 305.4), ("Dipropylene Glycol", 134.17)]:
        assert get_profile(name).mw == pytest.approx(mw)


def test_profile_default_is_not_a_stock_concentration_confirmation():
    assert get_profile("Coumarin").evidence["dilution"]["status"] == "NOT_CURRENT_STOCK_AUTHORITY"


def test_late_intake_prose_does_not_crash_numeric_character_consumers():
    for profile in get_all_profiles().values():
        assert len(profile.dimension_vector()) == 13
        assert isinstance(profile.character_tags(), list)
        assert profile.note in {"top", "heart", "base", "carrier"}
        assert profile.role not in {"top", "heart", "base"}
    profile = get_profile("hay absolute")
    assert profile.odor_description == "coumarinic hay, dry, natural"
    assert profile.character == {}  # unknown scores, not invented measurements
    assert profile.note == "base"
    assert profile.role == "modifier"
