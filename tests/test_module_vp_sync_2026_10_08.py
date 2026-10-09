"""Older modules carry their own vapour-pressure tables; keep the synced rows equal to the YAML.

On 2026-10-08 the musk vapour pressures (and the materials re-sourced that day) were synced from
``data/materials/*.yaml`` into ``engine/diffusion_model.py``, ``engine/temporal_volatility.py`` and
``engine/vapor_pressure_modeling.py``. Before that, Habanolide was 0.001-0.02 Pa there against a
measured 0.076 Pa, and Romandolide 0.0005 Pa against 0.1 Pa. This pins the synced rows so a later
YAML change shows up here instead of leaving the modules silently stale.
"""

from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.diffusion_model import DIFFUSION_DATA
from engine.temporal_volatility import MATERIAL_VOLATILITY
from engine.vapor_pressure_modeling import VAPOR_PRESSURE_DATA

_REGISTRY = load_registry()

_DIFFUSION_ROWS = (
    "Galaxolide",
    "Habanolide",
    "Ethylene Brassylate",
    "Exaltolide",
    "Musk Ketone",
    "Ambrettolide",
    "Romandolide",
    "Zenolide",
    "Ultralia",
    "Vetival",
    "Hydroxycitronellal",
    "Ethyl Vanillin",
)
_LOWERCASE_ROWS = ("Galaxolide", "Habanolide", "Hydroxycitronellal", "Ethyl Vanillin")


def _yaml(name: str):
    material = _REGISTRY.get(name)
    assert material is not None, name
    assert material.vp_25c_pa is not None, name
    return material


@pytest.mark.parametrize("name", _DIFFUSION_ROWS)
def test_diffusion_model_row_matches_yaml(name: str) -> None:
    material = _yaml(name)
    row = DIFFUSION_DATA[name]
    assert row["VP_25"] == pytest.approx(material.vp_25c_pa, rel=1e-9)
    assert row["MW"] == pytest.approx(material.mw_g_mol, rel=1e-9)


@pytest.mark.parametrize("name", _LOWERCASE_ROWS)
def test_temporal_volatility_row_matches_yaml(name: str) -> None:
    material = _yaml(name)
    assert MATERIAL_VOLATILITY[name.lower()]["vp_25c"] == pytest.approx(
        material.vp_25c_pa, rel=1e-9
    )


@pytest.mark.parametrize("name", _LOWERCASE_ROWS)
def test_vapor_pressure_modeling_row_matches_yaml(name: str) -> None:
    material = _yaml(name)
    row = VAPOR_PRESSURE_DATA[name.lower()]
    assert row["vp_25c"] == pytest.approx(material.vp_25c_pa, rel=1e-9)
    assert row["mw"] == pytest.approx(material.mw_g_mol, rel=1e-9)
