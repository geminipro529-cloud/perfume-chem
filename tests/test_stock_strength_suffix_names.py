"""A row label naming its stock strength keeps the bare material's physics.

Stock names such as "Eugenol 10%" or "Ethyl Maltol 1% v/v in ethanol" are how
the Stock page and inventory name materials. Only the trailing strength suffix
may be dropped for physics lookups; identity text never is, an unknown bare
name stays unknown, and a label with its own registered record keeps it.
"""

from __future__ import annotations

import pytest

from engine.material_resolver import resolve_material, strip_stock_strength_suffix
from engine.pipeline.formula_state import FormulaState
from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Eugenol 10%", "Eugenol"),
        ("Cocoa CO2 Extract 7.7%", "Cocoa CO2 Extract"),
        ("Ethyl Maltol 1% v/v in ethanol", "Ethyl Maltol"),
        ("Geraniol 10% w/w in DPG", "Geraniol"),
        ("Vanillin 5 % in TEC", "Vanillin"),
        ("Eugenol", "Eugenol"),
        ("Iso E Super", "Iso E Super"),
        ("Aldehyde C-12 MNA", "Aldehyde C-12 MNA"),
        ("Geraniol (10% in DPG)", "Geraniol (10% in DPG)"),
        ("Eugenol 10% extra", "Eugenol 10% extra"),
        ("10%", "10%"),
    ],
)
def test_strip_removes_only_a_trailing_stock_strength(label: str, expected: str) -> None:
    assert strip_stock_strength_suffix(label) == expected


def test_unknown_suffixed_label_resolves_as_bare_material() -> None:
    stock = resolve_material("Eugenol 10%")
    bare = resolve_material("Eugenol")
    assert stock.is_known
    assert stock.requested_name == "Eugenol 10%"
    assert stock.matched_name == "Eugenol"
    assert stock.profile_name == bare.profile_name
    assert stock.registry_name == bare.registry_name
    assert stock.canonical_name == bare.canonical_name


def test_registry_alias_of_bare_record_also_takes_bare_profile() -> None:
    stock = resolve_material("Ethyl Maltol 1%")
    bare = resolve_material("Ethyl Maltol")
    assert stock.matched_name == "Ethyl Maltol"
    assert stock.profile is not None
    assert stock.profile_name == bare.profile_name
    assert stock.registry_name == bare.registry_name


def test_label_with_its_own_registry_record_is_unchanged() -> None:
    resolved = resolve_material("Geraniol 10%")
    assert resolved.matched_name == "Geraniol 10%"
    assert resolved.registry_name != resolve_material("Geraniol").registry_name


def test_unknown_bare_name_stays_unknown() -> None:
    resolved = resolve_material("Foo 10%")
    assert not resolved.is_known
    assert resolved.matched_name == "Foo 10%"


def _analyze(label: str, raw_ul: float, dilution: float):
    return PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="t",
            ingredients_ul={label: raw_ul, "Iso E Super": 500.0},
            batch_volume_ml=30.0,
            dilutions={label: dilution},
        )
    )


def _row(analysis, label: str):
    return {m.name: m for m in analysis.formula_state.materials}[label]


def _physics(material) -> tuple:
    return (
        material.oav,
        material.odt_air_ppm,
        material.vp_pure_pa,
        material.sources.get("odt"),
        material.sources.get("oav_model"),
    )


@pytest.mark.parametrize(
    ("label", "bare", "raw_ul", "dilution"),
    [
        ("Eugenol 10%", "Eugenol", 60.0, 0.1),
        ("Cocoa CO2 Extract 7.7%", "Cocoa CO2 Extract", 250.0, 0.077),
        ("Ethyl Maltol 1%", "Ethyl Maltol", 150.0, 0.01),
    ],
)
def test_suffixed_row_gets_bare_material_physics(
    label: str, bare: str, raw_ul: float, dilution: float
) -> None:
    stock = _row(_analyze(label, raw_ul, dilution), label)
    reference = _row(_analyze(bare, raw_ul, dilution), bare)
    assert stock.name == label
    assert stock.oav is not None
    assert stock.sources.get("odt") != "missing"
    assert _physics(stock) == _physics(reference)


def test_cocoa_stock_row_uses_composite_decomposition() -> None:
    label = "Cocoa CO2 Extract 7.7%"
    analysis = _analyze(label, 250.0, 0.077)
    assert _row(analysis, label).sources.get("oav_model") == (
        "modeled:natural_constituent_composite"
    )
    rescaled = FormulaState.from_base(
        analysis.formula_state,
        new_raw_ul={label: 125.0, "Iso E Super": 500.0},
    )
    rescaled_row = {m.name: m for m in rescaled.materials}[label]
    assert rescaled_row.oav is not None


def test_registered_stock_and_unknown_rows_keep_current_results() -> None:
    geraniol = _row(_analyze("Geraniol 10%", 60.0, 0.1), "Geraniol 10%")
    assert geraniol.sources.get("odt") == "registry:data_spine.odt_air_ppb"
    unknown = _row(_analyze("Foo 10%", 60.0, 0.1), "Foo 10%")
    assert unknown.oav is None
    assert unknown.sources.get("odt") == "missing"
