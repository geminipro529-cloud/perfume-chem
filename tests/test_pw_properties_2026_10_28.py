"""Properties for the PerfumersWorld bottles that arrived 28 Oct 2026 ("PW orders have arrived").

Every value was re-opened before loading. These pin the data and its sources; they make no
sensory claim.
"""
from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.ifra_standards import load_ifra_table
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata, get_constituents

_DAVANA = "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile"


@pytest.mark.parametrize("label", ["Davana Essential Oil", "Davana Essential Oil 10% in DPG", "Davana EO 10%"])
def test_davana_resolves_to_the_pappas_lot_profile(label):
    meta = get_composite_metadata(label)
    assert meta.profile_key == _DAVANA
    assert meta.resolution == "literature_proxy"
    assert meta.quantitative_evaluability == "PARTIAL_INPUT_COVERAGE"
    assert meta.characterized_fraction == pytest.approx(0.0313)
    assert meta.input_authority["composition"]["owned_lot_match"] == "UNVERIFIED_CONDITIONAL_PROXY"
    assert meta.sources[0].endswith("REVIVE-GCMS-Report-Davana-Oil-India-8F.pdf")


def test_davana_keeps_davanone_and_the_odorants_unresolved_not_renormalized():
    rows = {row[0]: row[1] for row in get_constituents("Davana Essential Oil")}
    assert rows == {"germacrene d": 0.0104, "alpha eudesmol": 0.0081, "geranyl acetate": 0.0076, "linalool": 0.0052}
    unresolved = {row["name"]: row["reported_fraction"] for row in get_composite_metadata("Davana Essential Oil").unresolved_constituents}
    assert unresolved["davanone"] == pytest.approx(0.5355)
    assert unresolved["(E)-ethyl cinnamate"] == pytest.approx(0.043)
    assert unresolved["davana ether II"] == pytest.approx(0.0445)


@pytest.mark.parametrize(
    ("record", "field", "value", "provenance_start"),
    [
        ("Davana Essential Oil", "density_25c_g_ml", 0.9586, "Measured: R. S. Pappas"),
        ("Fixative 505", "density_25c_g_ml", 1.082, "Firmenich SDS FIXATEUR 000505 E"),
        ("Vetiveryl Acetate", "density_25c_g_ml", 1.0025, "Ernesto Ventos"),
        ("Isolongifolanone", "density_25c_g_ml", 1.003, "RIFM fragrance ingredient safety assessment"),
        ("Isolongifolanone", "vp_25c_pa", 0.2275, "RIFM fragrance ingredient safety assessment"),
        ("Isolongifolanone", "logp", 4.2, "Givaudan"),
        ("Isolongifolanone", "mw_g_mol", 220.36, "Computed from C15H24O"),
    ],
)
def test_loaded_values_carry_a_dated_provenance(record, field, value, provenance_start):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    provenance = spine.provenance[field]
    assert provenance.startswith(provenance_start)
    assert "Loaded 2026-10-28" in provenance


@pytest.mark.parametrize(
    ("record", "character_source"),
    [
        ("Davana Essential Oil", "Robertet"),
        ("Fixative 505", "PerfumersWorld 4UY07514"),
        ("Isolongifolanone", "Givaudan"),
        ("Beta Caryophyllene", "Robertet"),
        ("Vetiveryl Acetate", "Ernesto Ventos"),
    ],
)
def test_owned_and_quoted_producer_odour_text(record, character_source):
    spine = load_registry().get(record)
    assert spine.character
    assert spine.provenance["character"].startswith(character_source)
    assert spine.user_in_inventory is True


def test_isolongifolanone_is_loaded_under_the_commercial_cas_not_pws():
    spine = load_registry().get("Isolongifolanone")
    assert spine.cas == "23787-90-8"
    assert "14727-47-0" in spine.notes
    assert load_registry().get("Isolongifolene ketone") is spine
    material = load_ifra_table().lookup("Isolongifolanone")
    assert (material.status, material.standard) == ("no_standard", None)


def test_fixative_505_is_a_base_with_no_borrowed_molecule_physics():
    spine = load_registry().get("Fixative 505")
    assert spine.mw_g_mol is None and spine.vp_25c_pa is None and spine.cas is None
    assert get_composite_metadata("Fixative 505") is None


@pytest.mark.parametrize("name", ["Ambrox Super", "Ambrofix"])
def test_ambroxide_vp_is_echas_measured_25c_value(name):
    spine = load_registry().get(name)
    assert spine.vp_25c_pa == pytest.approx(0.066)
    assert spine.vp_source == "measured_25C"
    assert "OECD Guideline 104" in spine.provenance["vp_25c_pa"]


def test_ibq_vp_is_givaudans_printed_value():
    spine = load_registry().get("IBQ")
    assert spine.vp_25c_pa == pytest.approx(0.13)
    assert spine.vp_source == "producer_T_unstated"
    assert spine.provenance["vp_25c_pa"].startswith("Givaudan, Butyl Quinoline Secondary")


def test_tuberose_density_and_the_legacy_profile_note():
    spine = load_registry().get("Tuberose Absolute")
    assert spine.density_25c_g_ml == pytest.approx(0.9703)
    assert spine.provenance["density_25c_g_ml"].startswith("Biolandes")
    meta = get_composite_metadata("Tuberose Absolute")
    assert any("Petrzilka and Ehret" in item for item in meta.limitations)


def test_magnolia_absolute_takes_its_inci_identity_without_renormalizing():
    # Kenny, 28 Oct 2026: "magnolia abolute takje the INCI on the mykinrecipe page".
    rows = {row[0]: row[1] for row in get_constituents("Magnolia Absolute")}
    assert rows["beta caryophyllene"] == pytest.approx(0.3007)
    assert rows["caryophyllene oxide"] == pytest.approx(0.1872)
    assert sum(rows.values()) == pytest.approx(0.5734)
    meta = get_composite_metadata("Magnolia Absolute")
    assert meta.profile_key == "magnolia officinalis flos essential oil liu 2025 stage s1 profile"
    assert meta.sources[0] == "https://doi.org/10.5650/jos.ess25113"
    unresolved = {row["name"]: row["reported_fraction"] for row in meta.unresolved_constituents}
    assert len(unresolved) == 17
    assert unresolved["cis-calamenene"] == pytest.approx(0.046)
    assert sum(unresolved.values()) == pytest.approx(0.3073)
    assert any("INCI" in item for item in meta.limitations)
    # The MSR cosmetic PG extract stays a separate, unmodelled stock.
    assert get_composite_metadata("Magnolia Flower Extract") is None
