from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.inventory_parser import parse_inventory
from engine.name_utils import names_match, normalize_name
from engine.odor_thresholds import ODT_DATA
from engine.pipeline.natural_absolute_decomposition import composite_oav, get_constituents


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
    assert "Hydroxycitronellal" not in available
    assert "Olibanum Resinoid Absolute" not in available


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


@pytest.mark.parametrize(
    "name",
    ["Orris Liquid", "Olibanum Resinoid", "Olibanum Resinoid (Viscous)"],
)
def test_natural_mixtures_use_positive_composite_oav(name: str) -> None:
    assert get_constituents(name)
    assert composite_oav(
        name,
        active_g=0.1,
        total_moles_in_formula=0.1,
    ) > 0
