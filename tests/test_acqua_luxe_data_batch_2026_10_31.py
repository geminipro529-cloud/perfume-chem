"""Acqua di Gio Luxe data batch, 31 Oct 2026 (stock thread). Kenny: "If some information is
missing, research it and then put it in the system and make sure it is not biased."

Loads HANDOFF.md section 1 of /mnt/project-files/studio/acqua-di-gio-luxe/data-research-20261031/:
the Floralozone air threshold (Symrise Florazon sheet), Amber Xtreme identity and RIFM vapour
pressure, neat and solid densities, the elemi and olibanum lot-median profiles, the patchouli
ISO 3757 profile, sandalwood minor constituents, a bergamot FCF cross-check lot, provenance for
values that stay (Iso E Super, beta-santalol, linalool, beta damascone) and sourced odour
descriptions. Disputed values (section 2), identity flags (section 3) and the w/w stock
densities (section 4, an engine gap) are not loaded. These pin the data and its sources; they
make no sensory claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION, lookup_odt_entry
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_DATE = "2026-10-31"
_BANNED_HOSTS = ("scentree", "fragrantica", "wikipedia", "scent.vn", "scribd", "basenotes")

# (spine record, field, value)
LOADED = [
    ("Floralozone", "odt_air_ppb", 6.44),
    ("Amber Xtreme", "mw_g_mol", 264.45),
    ("Amber Xtreme", "vp_25c_pa", 0.38),
    ("Ambrox Super", "density_25c_g_ml", 1.052),
    ("Calone", "density_25c_g_ml", 1.353),
    ("Olibanum Oil", "density_25c_g_ml", 0.8723),
    ("Neroli EO", "density_25c_g_ml", 0.864),
    ("Jojoba Oil - Fixed Oil", "density_25c_g_ml", 0.870),
    ("Isopropyl Myristate (IPM)", "density_25c_g_ml", 0.851),
    ("Isopropyl Myristate", "density_25c_g_ml", 0.851),
    ("Damascone Beta", "vp_25c_pa", 2.6),
]

# Values that stay; only the provenance changed.
PROVENANCE_ONLY = [
    ("Iso E Super", "odt_air_ppb", 0.0184, "0.0104-0.0261"),
    ("Linalool", "vp_25c_pa", 21.3, "OECD SIDS"),
    ("Beta Damascone", "vp_25c_pa", 2.6, "EC 245-842-1"),
]

# (spine record, sourced odour description, source host)
DESCRIPTIONS = [
    ("Parmavert", "A powerful green, floral, violet leaf odor.", "bedoukian.com"),
    ("Aldehyde C11 Undecylenic", "waxy aldehydic rose mandarin citrus soapy fatty", "thegoodscentscompany.com"),
    ("Methyl Benzoate", "phenolic wintergreen almond floral cananga", "thegoodscentscompany.com"),
    ("Champaca Flower EO", "dry tea orangeflower ylang carnation guaiacwood", "thegoodscentscompany.com"),
    ("Eucalyptus Essential Oil", "herbal eucalyptol camphor", "thegoodscentscompany.com"),
    ("Basil EO (India, Ocimum Basilicum)", "sweet herbal tarragon green spicy", "thegoodscentscompany.com"),
    ("Butylated Hydroxytoluene (BHT) Antioxidant", "mild phenolic camphor", "thegoodscentscompany.com"),
]


def _provenance(record: str, field: str) -> str:
    return str((load_registry().get(record).provenance or {}).get(field) or "")


@pytest.mark.parametrize("record, field, value", LOADED)
def test_value_is_loaded_with_a_dated_sourced_provenance(record, field, value):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    text = _provenance(record, field)
    assert _DATE in text and "https://" in text
    assert not text.startswith("engine.")
    assert not any(host in text.casefold() for host in _BANNED_HOSTS)


@pytest.mark.parametrize("record, field, value, marker", PROVENANCE_ONLY)
def test_kept_value_gains_its_source(record, field, value, marker):
    assert getattr(load_registry().get(record), field) == pytest.approx(value)
    text = _provenance(record, field)
    assert _DATE in text and marker in text and "https://" in text


@pytest.mark.parametrize("record, description, host", DESCRIPTIONS)
def test_odour_description_is_the_sourced_text(record, description, host):
    spine = load_registry().get(record)
    assert spine.character == description
    text = _provenance(record, "character")
    assert description in text and host in text and _DATE in text


def test_descriptions_without_a_new_source_are_not_touched():
    # Allyl Ionone and Spike Lavender already carry producer descriptions; Azarbre follows
    # Kenny's 28 Oct answer. None of them is in this batch.
    for record in ("Allyl Ionone (Ketone V)", "spike lavender eo", "Azarbre"):
        spine = load_registry().get(record)
        if spine is not None:
            assert _DATE not in _provenance(record, "character")


def test_floralozone_threshold_is_the_symrise_producer_figure():
    assert lookup_odt_entry("Floralozone")["odt_air"] == pytest.approx(6.44)
    meta = ODT_VERIFICATION["floralozone"]
    assert meta["vfy"] == "PEER_SINGLE"
    assert "0.0501" in meta["sources"][0] and "equivalent grade" in meta["sources"][0]
    # The static row underneath is aligned to the same source (it was 1.0 ppb, unsourced).
    assert meta["superseded"]["vfy"] == "PEER_SINGLE"
    assert "was 1.0 ppb" in meta["superseded"]["note"]


def test_iso_e_super_static_rows_no_longer_cite_the_wrong_paper():
    assert ODT_DATA["iso e super"]["odt_air"] == pytest.approx(0.0184)
    for source in ODT_VERIFICATION["iso e super"]["superseded"]["sources"]:
        assert "5:670" not in source
    assert "0.0104-0.0261" in json.dumps(ODT_VERIFICATION["iso e super"]["sources"])


def test_amber_xtreme_identity_and_profile_follow_the_spine():
    spine = load_registry().get("Amber Xtreme")
    profile = get_profile("Amber Xtreme")
    assert profile.vp == pytest.approx(spine.vp_25c_pa) == pytest.approx(0.38)
    assert profile.mw == pytest.approx(264.45)
    assert "C18H32O" in spine.notes and "not an acetal" in spine.notes
    assert "0.7354" in _provenance("Amber Xtreme", "vp_25c_pa")  # IFF kept as the second source
    kg = json.loads(Path("data/knowledge_graph/material_properties.json").read_text(encoding="utf-8"))
    entry = next(e for e in kg if e["name"] == "AMBER XTREME")
    assert "acetal" not in entry["sar_class"]
    assert "cyclic ether" in entry["olfactophore"]


def test_beta_damascone_records_and_profile_agree():
    registry = load_registry()
    assert registry.get("Damascone Beta").vp_25c_pa == pytest.approx(registry.get("Beta Damascone").vp_25c_pa)
    assert get_profile("Damascone Beta").vp == pytest.approx(2.6)


@pytest.mark.parametrize("record", ["Ambrox Super", "Calone"])
def test_solid_densities_say_they_are_solid_true_densities(record):
    text = _provenance(record, "density_25c_g_ml")
    assert "OECD 109" in text and "solid's true" in text and "not 25 C" in text
    assert _provenance(record, "density_basis").startswith("solid_true_density_measured")


def test_neroli_density_is_no_longer_a_temperature_unstated_sg():
    assert _provenance("Neroli EO", "density_basis") != "supplier_sg_temperature_unstated"


def test_vertofix_vp_and_absolute_ethanol_were_not_loaded():
    registry = load_registry()
    for spine in registry.all():
        if "vertofix" in spine.canonical_name.casefold():
            assert spine.vp_25c_pa != pytest.approx(250.0)
    assert registry.get("Ethanol 96%").density_25c_g_ml is None


def test_elemi_resolves_to_the_three_lot_median():
    meta = get_composite_metadata("Elemi EO")
    assert meta.profile_key == "canarium luzonicum oil three-lot gc-ms median profile"
    rows = {row[0]: row[1] for row in get_constituents("Elemi EO")}
    assert rows["limonene"] == pytest.approx(0.5077)
    assert rows["alpha phellandrene"] == pytest.approx(0.1437)
    assert {u["name"] for u in meta.unresolved_constituents} == {"elemol", "elemicin"}
    assert len(meta.sources) == 4


def test_olibanum_resolves_to_the_four_lot_median_and_keeps_woolley_as_cross_check():
    meta = get_composite_metadata("Olibanum Oil")
    assert meta.profile_key == "boswellia carterii oil somaliland four-lot gc-ms median profile"
    rows = {row[0]: row[1] for row in get_constituents("Olibanum Oil")}
    assert rows["alpha pinene"] == pytest.approx(0.3642)
    assert rows["limonene"] == pytest.approx(0.09635)
    assert rows["myrcene"] == pytest.approx(0.03255)
    assert meta.characterized_fraction == pytest.approx(0.7845)
    woolley = meta.input_authority["composition"]["replaced_profile_cross_check"]
    assert woolley["woolley_2012_average_pct"]["myrcene"] == pytest.approx(7.3)
    assert any("1-methoxydecane" in text for text in meta.limitations)


def test_sandalwood_minor_constituents_are_named_but_not_modeled():
    meta = get_composite_metadata("Sandalwood EO")
    assert meta.characterized_fraction == pytest.approx(0.68)  # the modeled rows are unchanged
    unresolved = {u["name"]: u for u in meta.unresolved_constituents}
    assert unresolved["epi-beta-santalol"]["reported_fraction_range"] == (0.0353, 0.041)
    assert all("reported_fraction" not in u for u in meta.unresolved_constituents)
    beta = meta.input_authority["(Z)-beta-santalol"]
    assert "0.0555" in beta["odt_cross_check"]
    lot = meta.input_authority["composition"]["cross_check_lot"]["reported_pct"]
    assert lot["cis-alpha-trans-bergamotol"] == pytest.approx(8.05)


def test_bergamot_model_is_unchanged_and_the_fcf_lot_is_a_cross_check():
    meta = get_composite_metadata("Bergamot FCF")
    assert meta.characterized_fraction == pytest.approx(0.92125)
    lot = meta.input_authority["composition"]["cross_check_lot"]
    assert lot["reported_pct"]["linalool"] == pytest.approx(14.34)
    assert lot["within_standard_ranges"] is False
