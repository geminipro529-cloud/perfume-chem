from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.data_spine.loader import load_materials, load_registry
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import parse_inventory
from engine.name_utils import names_match, normalize_name
from engine.odor_thresholds import ODT_DATA, lookup_odt_entry, lookup_odt_raw_name
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import (
    _ABSOLUTE_CONSTITUENTS,
    composite_oav,
    get_composite_metadata,
    get_constituents,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_requested_stock_is_available_at_recorded_dilutions() -> None:
    available = {
        item.name: item
        for item in parse_inventory(include_unavailable=False)
    }

    assert available["Alpha Irone"].dilution == pytest.approx(0.30)
    assert available["Orris Liquid"].dilution == pytest.approx(0.30)
    assert available["Hydroxycitronellol"].dilution == pytest.approx(1.0)
    assert available["Olibanum Resinoid"].dilution == pytest.approx(1.0)
    assert available["Cocoa Absolute"].dilution == pytest.approx(1.0)
    assert available["Cocoa CO2 Extract"].dilution == pytest.approx(0.077)
    assert "Hydroxycitronellal" not in available
    assert "Olibanum Resinoid Absolute" not in available
    assert "Cocoa CO2 Absolute" not in available


def test_inventory_parser_accepts_approximate_percent_stock_notation(
    tmp_path: Path,
) -> None:
    inventory_path = tmp_path / "inventory.txt"
    inventory_path.write_text(
        """--- AMBER MATERIALS ---
- Ambrox Super (~33% w/v in DEP:EtOH)
- Ambrettolide (10%)
- Zenolide
""",
        encoding="utf-8",
    )

    available = {item.name: item for item in parse_inventory(inventory_path)}

    assert available["Ambrox Super"].dilution == pytest.approx(0.33)
    assert available["Ambrettolide"].dilution == pytest.approx(0.10)
    assert available["Zenolide"].dilution == pytest.approx(1.0)


def test_requested_materials_have_runtime_data() -> None:
    registry = load_registry()
    hydroxycitronellol = registry.get("Hydroxycitronellol")
    orris_liquid = registry.get("Orris Liquid")
    olibanum = registry.get("Olibanum Resinoid")

    assert hydroxycitronellol is not None
    assert hydroxycitronellol.cas == "107-74-4"
    assert hydroxycitronellol.mw_g_mol == pytest.approx(174.28)
    assert hydroxycitronellol.vp_25c_pa == pytest.approx(0.0736)
    assert hydroxycitronellol.user_in_inventory is True

    assert orris_liquid is not None
    assert orris_liquid.user_stock_dilution is not None
    assert orris_liquid.user_stock_dilution.startswith("30%")
    assert orris_liquid.user_in_inventory is True

    assert olibanum is not None
    assert olibanum.user_stock_dilution == "neat"
    assert olibanum.user_in_inventory is True

    for name in (
        "Alpha Irone",
        "Orris Liquid",
        "Hydroxycitronellol",
        "Olibanum Resinoid",
    ):
        assert get_profile(name) is not None


def test_new_names_resolve_without_collapsing_distinct_molecules() -> None:
    assert normalize_name("Alpha Irone (30% w/w in IPM)") == "alpha irone"
    assert normalize_name("Orris Liquid (30%)") == "orris liquid"
    assert (
        normalize_name("Olibanum Resinoid (viscous, 3 g)")
        == "olibanum resinoid"
    )
    assert not names_match("Hydroxycitronellol", "Hydroxycitronellal")
    assert normalize_name("Cocoa Absolute") == "cocoa absolute"
    assert normalize_name("Cocoa CO2 Extract") == "cocoa co2 extract"
    assert normalize_name("Cocoa CO2 Absolute") == "cocoa co2 extract"
    assert names_match("Cocoa CO2 Absolute", "Cocoa CO2 Extract")
    assert not names_match("Cocoa Absolute", "Cocoa CO2 Extract")


def test_cocoa_absolute_and_co2_extract_have_distinct_runtime_records() -> None:
    cocoa_names = [
        material.canonical_name.casefold()
        for material in load_materials()
        if material.canonical_name.casefold()
        in {"cocoa absolute", "cocoa co2 extract"}
    ]
    assert cocoa_names.count("cocoa absolute") == 1
    assert cocoa_names.count("cocoa co2 extract") == 1

    registry = load_registry()
    absolute = registry.get("Cocoa Absolute")
    co2_extract = registry.get("Cocoa CO2 Extract")

    assert absolute is not None
    assert absolute.canonical_name == "Cocoa Absolute"
    assert absolute.user_stock_dilution == "neat"
    assert absolute.user_in_inventory is True

    assert co2_extract is not None
    assert co2_extract.canonical_name == "Cocoa CO2 Extract"
    assert co2_extract.user_stock_dilution == "7.7%"
    assert co2_extract.user_in_inventory is True
    assert registry.get("Cocoa CO2 Absolute") is co2_extract

    absolute_profile = get_profile("Cocoa Absolute")
    co2_profile = get_profile("Cocoa CO2 Extract")
    assert absolute_profile is not None
    assert absolute_profile.name == "Cocoa Absolute"
    assert co2_profile is not None
    assert co2_profile.name == "Cocoa CO2 Extract"

    assert ODT_DATA["cocoa absolute"]["odt_air"] == pytest.approx(5.0)
    assert ODT_DATA["cocoa co2 extract"]["odt_air"] == pytest.approx(3.0)


@pytest.mark.parametrize(
    "name",
    [
        "Ginger EO",
        "Neroli EO",
        "Tagetes EO",
        "Jasmine Sambac Blossoms",
        "Blue Chamomile EO",
        "Mimosa Absolute",
        "Osmanthus Absolute (volume grade)",
        "Tuberose Absolute (volume grade)",
        "Isobutavan",
        "Allyl Cyclohexyl Propionate",
        "Tonka Bean Absolute",
        "Cocoa CO2 Extract",
        "Peru Balsam Resinoid",
        "Opoponax Resinoid",
    ],
)
def test_late_added_odt_records_are_visible_to_normalized_runtime_lookup(
    name: str,
) -> None:
    entry = lookup_odt_entry(name)

    assert entry is not None
    assert float(entry["odt_air"]) > 0.0
    assert lookup_odt_raw_name(name) is not None


def test_hydroxycitronellol_odt_is_positive_and_labeled_as_derived() -> None:
    odt = ODT_DATA["hydroxycitronellol"]

    assert odt["odt_air"] > 0
    assert odt["odt_eth"] > 0
    assert odt["vfy"] == "DERIVED"
    assert "direct" in odt["note"].lower()


def test_legacy_material_properties_mirror_live_stock_and_thresholds() -> None:
    materials = json.loads(
        (PROJECT_ROOT / "data" / "knowledge_graph" / "material_properties.json")
        .read_text(encoding="utf-8")
    )
    by_name = {material["name"].casefold(): material for material in materials}

    expected = {
        "alpha irone": ("79-69-6", 0.30, 0.9, 0.16),
        "hydroxycitronellol": ("107-74-4", 1.0, 100.0, 20.0),
        "olibanum resinoid": ("8016-36-2", 1.0, 10.0, 3.0),
        "orris liquid": ("8002-73-1", 0.30, 0.9, 0.16),
    }
    for name, (cas, dilution, odt_air, odt_eth) in expected.items():
        material = by_name[name]
        assert material["cas"] == cas
        assert material["in_inventory"] is True
        assert material["dilution_pct"] == pytest.approx(dilution)
        assert material["odt"] == pytest.approx(odt_air)
        assert material["odt_ethanol_ppm"] == pytest.approx(odt_eth)

    cocoa_absolute = by_name["cocoa absolute"]
    cocoa_co2 = by_name["cocoa co2 extract"]
    assert cocoa_absolute["in_inventory"] is True
    assert cocoa_absolute["dilution_pct"] == pytest.approx(1.0)
    assert cocoa_co2["in_inventory"] is True
    assert cocoa_co2["dilution_pct"] == pytest.approx(0.077)


@pytest.mark.parametrize(
    "name",
    [
        "Orris Liquid",
        "Olibanum Resinoid",
        "Olibanum Resinoid (Viscous)",
        "Lime Distilled EO",
        "Osmanthus Absolute (volume grade)",
        "Cocoa Absolute",
        "Cocoa CO2 Extract",
    ],
)
def test_natural_mixtures_use_positive_composite_oav(name: str) -> None:
    assert get_constituents(name)
    assert composite_oav(
        name,
        active_g=0.1,
        total_moles_in_formula=0.1,
    ) > 0


def test_volume_grade_osmanthus_uses_conservative_composite_potency() -> None:
    premium = composite_oav(
        "Osmanthus Absolute",
        active_g=0.1,
        total_moles_in_formula=0.1,
    )
    volume_grade = composite_oav(
        "Osmanthus Absolute (volume grade)",
        active_g=0.1,
        total_moles_in_formula=0.1,
    )

    assert premium is not None
    assert volume_grade == pytest.approx(premium * 0.25)


def test_cocoa_absolute_and_co2_extract_use_distinct_composite_fingerprints() -> None:
    absolute = get_constituents("Cocoa Absolute")
    co2_extract = get_constituents("Cocoa CO2 Extract")

    assert absolute is not None
    assert co2_extract is not None
    assert absolute != co2_extract
    assert {constituent[0] for constituent in co2_extract} == {
        "2,3,5-trimethylpyrazine"
    }
    assert "3-methylbutanal" in {
        constituent[0] for constituent in absolute
    }


@pytest.mark.parametrize(
    "inventory_name",
    [
        "Bergamot EO",
        "Bergamot FCF oil Sicilian",
        "Blood Orange oil Sicilian",
        "Ylang Ylang EO",
        "Cedarwood oil Virginia",
        "Benzoin Sumatra Resinoid",
        "Lavender EO High Altitude",
        "Jasmine Sambac Absolute",
    ],
)
def test_defensible_natural_aliases_resolve_to_explicit_proxy_metadata(
    inventory_name: str,
) -> None:
    metadata = get_composite_metadata(inventory_name)

    assert get_constituents(inventory_name)
    assert metadata is not None
    assert metadata.resolution == "literature_proxy"
    assert metadata.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert metadata.batch_specific is False
    assert 0.0 < metadata.characterized_fraction <= 1.0


def test_new_partial_natural_profiles_have_primary_sources_and_valid_fractions() -> None:
    for name in (
        "Orange Peel EO",
        "Lemon FCF oil Sicilian",
        "Neroli EO",
        "Ginger EO",
        "Galbanum EO",
        "Frankincense EO",
        "Clove EO",
        "Black Pepper EO",
        "Red Mandarin EO",
        "Eucalyptus Essential Oil",
        "Clary Sage EO",
    ):
        metadata = get_composite_metadata(name)
        assert metadata is not None
        assert metadata.sources
        assert all(source.startswith("http") for source in metadata.sources)
        assert 0.0 < metadata.characterized_fraction <= 1.0

    for constituents in _ABSOLUTE_CONSTITUENTS.values():
        assert all(len(row) == 6 for row in constituents)
        assert all(0.0 < float(row[1]) <= 1.0 for row in constituents)
        assert sum(float(row[1]) for row in constituents) <= 1.0 + 1e-12


def test_formula_state_exposes_natural_profile_scope_and_coverage() -> None:
    state = build_formula_state({"Neroli EO": 100.0, "Hedione": 900.0})
    neroli = next(row for row in state.materials if row.name == "Neroli EO")

    assert neroli.oav is not None
    assert "LITERATURE_PARTIAL_PROFILE" in neroli.sources["natural_composite"]
    assert "batch_specific=false" in neroli.sources["natural_composite"]


def test_unknown_chemotype_remains_unresolved_instead_of_using_a_generic_proxy() -> None:
    assert get_constituents("Basil EO") is None
    assert get_composite_metadata("Basil EO") is None


def test_extraction_mismatch_profiles_are_explicit_literature_proxies() -> None:
    galbanum = get_composite_metadata("Galbanum Resinoid")
    tonka = get_composite_metadata("Tonka Bean Absolute")

    assert galbanum is not None
    assert galbanum.resolution == "literature_proxy"
    assert any("essential oil" in item for item in galbanum.limitations)

    assert tonka is not None
    assert tonka.resolution == "literature_proxy"
    assert tonka.profile_key == "tonka bean solvent extract literature profile"
    assert tonka.characterized_fraction == pytest.approx(0.8397)
    assert all(source.startswith("http") for source in tonka.sources)
    assert any("supplier-batch" in item for item in tonka.limitations)
