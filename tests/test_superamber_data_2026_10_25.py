"""Super-amber data (Kenny, 25 Oct 2026: "Find a way for the engine to tell super-ambers apart";
research in the Prada L'Homme thread, loaded in the stock thread).

Pins the sourced Ambrocenide threshold, the honest labels on Ambermax's estimated threshold and
vapour pressure, and the identity fixes in the KB export. No sensory claim.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.odor_thresholds import lookup_odt_entry, verify_odt
from engine.pipeline.formula_state import build_formula_state

_KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_graph" / "material_properties.json"


def _material(name: str):
    build_formula_state.cache_clear()
    return build_formula_state({name: 1000.0}, {name: 1.0}, temperature_K=298.15).materials[0]


def _kb_row(name: str) -> dict:
    return next(row for row in json.loads(_KB.read_text(encoding="utf-8")) if row["name"] == name)


def test_ambrocenide_threshold_is_the_peer_reviewed_ng_per_litre_figure_in_ppb():
    # 0.02 ng/L air (Chem. Eur. J. 2024, e202400006) x 24.45 / 278.4 g/mol
    assert lookup_odt_entry("Ambrocenide")["odt_air"] == pytest.approx(0.02 * 24.45 / 278.4, rel=0.01)
    assert "e202400006" in " ".join(verify_odt("Ambrocenide")["sources"])
    material = _material("Ambrocenide")
    assert material.odt_air_ppm == pytest.approx(0.00176 / 1000.0)
    assert material.sources["odt"] == "literature:peer_reviewed.odt_air"


def test_ambermax_threshold_and_vapour_pressure_read_as_estimates():
    material = _material("Ambermax")
    assert material.sources["odt"].startswith("estimated:")
    assert material.vp_pure_pa == pytest.approx(0.01)
    assert material.sources["vp"].startswith("estimated:")


def test_kb_export_carries_the_maker_identities():
    ambermax = _kb_row("AMBERMAX")
    assert ambermax["cas"] == "929625-08-1 / 1001252-30-7"
    assert ambermax["formula_str"] == "C₁₈H₃₀O"
    assert "cedarwood" in ambermax["odor_profile"]
    assert _kb_row("KEPHALIS")["formula_str"] == "C₁₄H₂₄O₂"
    ambrocenide = _kb_row("Ambrocenide")
    assert (ambrocenide["cas"], ambrocenide["odor_family"]) == ("211299-54-6", "amber")
