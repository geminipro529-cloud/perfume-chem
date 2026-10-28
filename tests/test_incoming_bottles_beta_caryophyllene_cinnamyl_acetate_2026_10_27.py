"""Beta-Caryophyllene and Cinnamyl Acetate get data-spine rows and IFRA "no standard" rows.

Both were incoming PerfumersWorld bottles (3WS00089, 3SQ00109) that the spine held only as
empty stubs, and the IFRA Category 4 table could not recognise, so the gate held any formula
that used them. Values are RIFM's printed physical data (Food Chem Toxicol 159 (2022)
112707 and 112692); the 20 C FMA vapour pressures are converted to 25 C the way the other
FMA-sourced rows are. The 6x higher pressure that technical-grade SDSs print for
beta-caryophyllene is recorded as a conflict in the row, not loaded.
"""

from __future__ import annotations

import math

import pytest

from engine.ifra_standards import load_ifra_table
from engine.material_resolver import resolve_material
from engine.pipeline.natural_absolute_decomposition import cited_vp_substitutions

TABLE = load_ifra_table()
MM_HG_PA = 133.322


def _row(name: str):
    return resolve_material(name).registry_material


def _clausius_clapeyron_25c(vp_20c_pa: float) -> float:
    d_hvap = (70.0 - 3.82 * math.log(vp_20c_pa)) * 1000.0
    return vp_20c_pa * math.exp(d_hvap / 8.314462 * (1 / 293.15 - 1 / 298.15))


@pytest.mark.parametrize(
    "name",
    ["Beta Caryophyllene", "Beta-Caryophyllene", "beta-caryophyllene", "(E)-Caryophyllene", "Caryophyllene"],
)
def test_every_beta_caryophyllene_name_reaches_the_one_row(name: str) -> None:
    material = _row(name)
    assert material is not None
    assert material.canonical_name == "Beta Caryophyllene"


def test_beta_caryophyllene_values_are_rifms() -> None:
    material = _row("Beta-Caryophyllene")
    assert str(material.cas) == "87-44-5"
    assert material.mw_g_mol == pytest.approx(204.35)
    assert material.density_25c_g_ml == pytest.approx(0.91)
    assert material.logp == pytest.approx(6.23)
    # 0.007 mm Hg at 20 C (FMA, quoted by RIFM) converted to 25 C
    assert material.vp_25c_pa == pytest.approx(_clausius_clapeyron_25c(0.007 * MM_HG_PA), abs=0.001)
    assert material.vp_source == "producer_20C_converted"
    # 2026-10-28: Givaudan's measured odour value over the engine VP (PEER_EST), 1.3x from Ruth 1986.
    assert material.odt_air_ppb == pytest.approx(49.0)


def test_beta_caryophyllene_vp_records_the_conflict_it_did_not_load() -> None:
    text = _row("Beta-Caryophyllene").provenance["vp_25c_pa"]
    assert "CONFLICT RECORDED, NOT USED" in text
    assert "0.06 hPa at 20 C" in text and "0.09 hPa = 9 Pa at 25 C" in text
    assert "Reasoning, not a source" in text


def test_cinnamyl_acetate_values_are_rifms() -> None:
    material = _row("Cinnamyl Acetate")
    assert str(material.cas) == "103-54-8"
    assert material.mw_g_mol == pytest.approx(176.21)
    assert material.density_25c_g_ml == pytest.approx(1.05)
    assert material.logp == pytest.approx(2.7)
    assert material.vp_25c_pa == pytest.approx(_clausius_clapeyron_25c(0.008 * MM_HG_PA), abs=0.001)
    # RIFM's EPI Suite estimate at 25 C (0.0121 mm Hg) agrees within 10 %
    assert material.vp_25c_pa == pytest.approx(0.0121 * MM_HG_PA, rel=0.1)
    assert material.vp_source == "producer_20C_converted"


@pytest.mark.parametrize("field", ["cas", "mw_g_mol", "density_25c_g_ml", "logp", "vp_25c_pa"])
@pytest.mark.parametrize("name, url", [
    ("Beta Caryophyllene", "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/87-44-5.pdf"),
    ("Cinnamyl Acetate", "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/103-54-8.pdf"),
])
def test_each_loaded_field_cites_the_rifm_assessment(name: str, url: str, field: str) -> None:
    assert url in _row(name).provenance[field]


@pytest.mark.parametrize(
    "name, canonical, cas",
    [
        ("Beta-Caryophyllene", "Beta Caryophyllene", "87-44-5"),
        ("Caryophyllene", "Beta Caryophyllene", "87-44-5"),
        ("beta-caryophyllene 10% in DPG", "Beta Caryophyllene", "87-44-5"),
        ("Cinnamyl Acetate", "Cinnamyl Acetate", "103-54-8"),
        ("Cinnamyl acetate 10% in DPG", "Cinnamyl Acetate", "103-54-8"),
    ],
)
def test_ifra_table_records_no_standard_with_cas_and_source(
    name: str, canonical: str, cas: str
) -> None:
    material = TABLE.lookup(name)
    assert material is not None
    assert material.name == canonical
    assert material.status == "no_standard"
    assert material.standard is None
    assert cas in (material.note or "")
    assert material.source_url and "ifra-51st-amendment---index-of-ifra-standards.pdf" in material.source_url


def test_the_new_rows_do_not_capture_their_neighbours() -> None:
    assert TABLE.lookup("Caryophyllene Acetate").name == "Caryophyllene Acetate"
    assert TABLE.lookup("Caryophyllene Oxide") is None
    assert TABLE.lookup("Cinnamyl Alcohol").status == "restricted"
    assert TABLE.lookup("Cinnamyl Alcohol").standard is not None


def test_natural_profiles_keep_their_caryophyllene_vp_within_a_third() -> None:
    # The cited spine VP now replaces the table VP inside naturals. It stays near the
    # 1.0-1.5 Pa those tables already held, so no profile moves more than 3x.
    rows = [s for s in cited_vp_substitutions() if "caryophyllene" in s.constituent.casefold()
            and "acetate" not in s.constituent.casefold() and "oxide" not in s.constituent.casefold()]
    assert rows
    for sub in rows:
        assert sub.registry_vp_25c_pa == pytest.approx(1.513, abs=0.001)
        ratio = sub.registry_vp_25c_pa / sub.table_vp_25c_pa
        assert 1 / 3 < ratio < 3
