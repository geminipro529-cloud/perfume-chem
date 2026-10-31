"""Properties for the MySkinRecipes orders #2200410 and #2200413 (Kenny, 27 Oct 2026: "Stock data
from msr emails and find all of the properties.").

Fir needle, olibanum and galbanum get published compositions. White Sandalwood Oil (China) has no
established identity; on 28 Oct 2026 Kenny asked for the closest one ("select the one that is the
closest"), so it takes that identity's profile as a labelled proxy. Magnolia Absolute takes the
identity its INCI names ("magnolia abolute takje the INCI on the mykinrecipe page"). Every value was re-opened before loading. These pin the data and its sources; they make
no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.ifra_standards import load_ifra_table, load_natural_constituents
from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)

_FIR = "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile"
# 2026-10-31: Olibanum Oil moved from the Woolley (2012) averages (0.744) to the median of four
# Somaliland B. carterii GC/MS tables (Acqua di Gio Luxe research, R7, second-read); Woolley stays
# in that profile's evidence as a cross-check.
_OLIBANUM = "boswellia carterii oil somaliland four-lot gc-ms median profile"
_GALBANUM = "ferula galbaniflua resinoid canton 2025 volatile fraction profile"

_PROFILES = {
    "Fir Needle Oil (Canada)": (_FIR, 0.902, "https://journals.sagepub.com/doi/10.1177/1934578X221086901"),
    "Olibanum Oil": (_OLIBANUM, 0.7845, "https://pmc.ncbi.nlm.nih.gov/articles/PMC9415502/"),
    "Olibanum (Frankincense) Oil": (_OLIBANUM, 0.7845, "https://pmc.ncbi.nlm.nih.gov/articles/PMC9415502/"),
    "Galbanum Resinoid": (_GALBANUM, 0.139035, "https://doi.org/10.1002/cbdv.202501442"),
}


@pytest.mark.parametrize("label", sorted(_PROFILES))
def test_msr_naturals_resolve_to_a_cited_partial_profile(label):
    key, characterized, source = _PROFILES[label]
    meta = get_composite_metadata(label)
    assert meta.profile_key == key
    assert meta.resolution == "literature_proxy"
    assert meta.characterized_fraction == pytest.approx(characterized)
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert meta.input_authority["composition"]["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
    assert meta.sources[0] == source


def test_galbanum_resinoid_models_only_its_volatile_fraction():
    rows = {name: row[1] for name, row in ((r[0], r) for r in get_constituents("Galbanum Resinoid"))}
    # Canton et al. 2025 volatile-fraction %FID scaled by the 34.5 % volatile share.
    assert rows["beta pinene"] == pytest.approx(0.08763)
    assert rows["alpha-bisabolol"] == pytest.approx(0.003105)
    # 2026-10-28: (3E,5Z)-undecatriene (0.7 %FID) is modeled with Givaudan's air threshold.
    assert rows["(3E,5Z)-1,3,5-undecatriene"] == pytest.approx(0.002415)
    assert sum(rows.values()) == pytest.approx(0.139035)
    meta = get_composite_metadata("Galbanum Resinoid")
    assert any("1.5200" in item for item in meta.limitations)
    unresolved = {row["name"]: row["reported_fraction"] for row in meta.unresolved_constituents}
    assert unresolved["bulnesol"] == pytest.approx(0.02484)
    assert unresolved["galbanic acid"] == pytest.approx(0.11856)  # non-volatile, never renormalized
    # His 10 % dilution is a separate, unmade stock.
    assert get_composite_metadata("Galbanum Resinoid 10%") is None


def test_labdanum_absolute_keeps_its_legacy_rows_and_says_they_are_unsupported():
    meta = get_composite_metadata("Labdanum Absolute")
    assert meta.quantitative_evaluability == "UNASSESSED_LEGACY_PROFILE"
    assert any("Weyerstahl 1998, an oil study" in item for item in meta.limitations)


def test_unidentified_msr_bottles_take_a_labelled_proxy_identity():
    # Kenny, 28 Oct 2026: "select the one that is the closest", then for the magnolia
    # "magnolia abolute takje the INCI on the mykinrecipe page".
    for label, key, phrase in (
        ("Magnolia Absolute", "magnolia officinalis flos essential oil liu 2025 stage s1 profile", "INCI"),
        ("White Sandalwood Oil (China)", "santalum album oil iso 3518 midpoint profile", "closest identity"),
    ):
        meta = get_composite_metadata(label)
        assert meta.profile_key == key
        assert meta.input_authority["composition"]["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
        assert any(phrase in item for item in meta.limitations)


@pytest.mark.parametrize(
    ("record", "field", "value", "provenance_start"),
    [
        ("Phenyl Ethyl Dimethyl Carbinol", "vp_25c_pa", 1.933, "RIFM fragrance ingredient safety assessment"),
        ("Farnesol", "vp_25c_pa", 0.005253, "ESTIMATE (EPI Suite v4.11)"),
        ("Labdanum Absolute", "density_25c_g_ml", 1.0215, "Biolandes"),
        ("Fir Needle Oil (Canada)", "density_25c_g_ml", 0.8709, "Biolandes"),
    ],
)
def test_loaded_physics_carry_a_dated_provenance(record, field, value, provenance_start):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    provenance = spine.provenance[field]
    assert provenance.startswith(provenance_start)
    assert "Loaded 2026-10-27" in provenance


def test_vp_sources_name_their_method():
    registry = load_registry()
    assert registry.get("Phenyl Ethyl Dimethyl Carbinol").vp_source == "producer_20C_converted"
    assert registry.get("Farnesol").vp_source == "EPI"


@pytest.mark.parametrize(
    ("record", "cas", "character_source"),
    [
        ("Labdanum Absolute", "8016-26-0", "Robertet"),
        ("Galbanum Resinoid", "9000-24-2", "dsm-firmenich"),
        ("Fir Needle Oil (Canada)", "85085-34-3", "Biolandes"),
        ("Olibanum Oil", "89957-98-2", "Robertet"),
    ],
)
def test_coa_cas_and_producer_odour_text(record, cas, character_source):
    spine = load_registry().get(record)
    assert spine.cas == cas
    assert spine.character
    assert spine.provenance["character"].startswith(character_source)
    assert spine.user_in_inventory is True


def test_proxy_identity_bottles_carry_no_molecule_physics_or_borrowed_density():
    registry = load_registry()
    magnolia = registry.get("Magnolia Absolute")
    sandalwood = registry.get("White Sandalwood Oil (China)")
    assert magnolia.cas is None
    assert sandalwood.cas == "8024-35-9"  # as printed by MySkinRecipes, not proof of contents
    # No density is published for a Magnolia officinalis flower extract, so none is borrowed.
    assert magnolia.density_25c_g_ml is None and magnolia.character is None
    assert "Magnolia Officinalis Flower Extract" in magnolia.notes
    assert sandalwood.density_25c_g_ml == pytest.approx(0.9782)
    assert sandalwood.provenance["density_25c_g_ml"].startswith("MySkinRecipes COA lot W9F536")
    assert sandalwood.provenance["character"].startswith("ISO 3518:2025")
    assert sandalwood.character
    for spine in (magnolia, sandalwood):
        assert spine.vp_25c_pa is None and spine.mw_g_mol is None
    assert registry.get("Olibanum (Frankincense) Oil").canonical_name == "Olibanum Oil"


TABLE = load_ifra_table()
LEVELS = load_natural_constituents().stocks


@pytest.mark.parametrize(
    ("stock", "status", "standard", "levels"),
    [
        ("Fir Needle Oil (Canada)", "specification", "IFRA_STD_184", {"IFRA_STD_199": 0.2}),
        ("Olibanum Oil", "natural_no_own_standard", None, {"IFRA_STD_102": 0.5, "IFRA_STD_016": 0.3}),
        ("Galbanum Resinoid", "natural_no_own_standard", None, {"IFRA_STD_026": 0.1}),
        ("Magnolia Absolute", "natural_no_own_standard", None, {"IFRA_STD_037": 1.45, "IFRA_STD_100": 2.8}),
        (
            "White Sandalwood Oil (China)",
            "natural_no_own_standard",
            None,
            {"IFRA_STD_036": 11.0, "IFRA_STD_192": 0.6, "IFRA_STD_197": 0.2},
        ),
        ("Davana Essential Oil", "natural_no_own_standard", None, {"IFRA_STD_007": 0.2}),
    ],
)
def test_ifra_rows_and_annex_constituents(stock, status, standard, levels):
    material = TABLE.lookup(stock)
    assert material.name == stock
    assert (material.status, material.standard) == (status, standard)
    assert {sid: level for sid, (level, _ncs) in LEVELS[stock].items()} == levels


def test_olibanum_takes_the_thujone_sum_row_not_the_isomers():
    # Annex I 'Olibanum oil': alpha 0.1 + beta 0.4 = the printed sum row 0.5.
    assert LEVELS["Olibanum Oil"]["IFRA_STD_102"] == (0.5, "Olibanum oil")
    assert TABLE.lookup("Olibanum (Frankincense) Oil").name == "Olibanum Oil"
