"""Literature physics batch, 25 Oct 2026 (stock thread). Kenny: "parse all the information
that is missing into the engine". Vapour pressure, log P, density, molecular weight and
enthalpy of vaporisation from producer, regulatory and measured sources; a second reader
re-opened every page. Values at 20-24 C are converted to 25 C by Clausius-Clapeyron, and
estimates say so in their provenance and vp_source."""

from __future__ import annotations

import pytest

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile

# (spine record, field, value, is an estimate)
LOADED = [
    ('Neryl Acetate', 'vp_25c_pa', 6.17, False),
    ('Aldehyde C-12 Lauric Dodecanal', 'vp_25c_pa', 1.12, False),
    ('Clearwood', 'vp_25c_pa', 1.51, False),
    ('Clearwood', 'density_25c_g_ml', 0.9563, False),
    ('Terpinyl Acetate', 'vp_25c_pa', 4.26, False),
    ('Terpinyl Acetate', 'logp', 4.34, True),
    ('Vetikon', 'logp', 2.77, False),
    ('Methyl Laitone', 'logp', 2.0, False),
    ('Aldehyde C-8 Octanal', 'vp_25c_pa', 148.3, False),
    ('Aldehyde C-8 Octanal', 'logp', 3.5, False),
    ('Alpha Damascone', 'vp_25c_pa', 3.2, False),
    ('Para-Cresyl Phenyl Acetate', 'logp', 3.7, False),
    ('Phenyl Acetaldehyde', 'vp_25c_pa', 58.2, False),
    ('Alpha Isomethyl Ionone', 'vp_25c_pa', 1.29, False),
    ('Alpha Isomethyl Ionone', 'density_25c_g_ml', 0.93, False),
    ('Ultralia', 'vp_25c_pa', 1.08, False),
    ('Ultralia', 'density_25c_g_ml', 0.93, False),
    ('Dihydromyrcenol', 'vp_25c_pa', 18.0, False),
    ('Dihydromyrcenol', 'density_25c_g_ml', 0.83, False),
    ('Gamma Decalactone', 'vp_25c_pa', 1.7, False),
    ('Gamma Decalactone', 'density_25c_g_ml', 0.955, False),
    ('Styralyl Acetate', 'vp_25c_pa', 8.42, False),
    ('Galaxolide', 'logp', 5.3, False),
    ('Buccoxime', 'logp', 2.94, False),
    ('Methyl Salicylate', 'logp', 2.55, False),
    ('Methyl Salicylate', 'density_25c_g_ml', 1.1805, False),
    ('Diethyl Malonate', 'vp_25c_pa', 25.33, False),
    ('Diethyl Malonate', 'logp', 0.96, False),
    ('Isoeugenol', 'logp', 3.04, False),
    ('Benzaldehyde', 'mw_g_mol', 106.1219, False),
    ('Benzaldehyde', 'dhvap_kj_mol', 48.6, False),
    ('Cyclamen Aldehyde', 'dhvap_kj_mol', 72.6, False),
    ('Cinnamaldehyde', 'dhvap_kj_mol', 62.4, False),
    ('Aldehyde C-8 Octanal', 'dhvap_kj_mol', 51.0, False),
    ('Maple Lactone', 'logp', 0.4, False),
    ('Cedroxyde', 'vp_25c_pa', 0.317, False),
    ('Cedroxyde', 'logp', 4.88, False),
    ('Ethyl Linalyl Acetate', 'logp', 4.7, False),
    ('Isobutyl Quinoline', 'logp', 4.4, False),
    ('Ambrettolide', 'logp', 6.7, False),
    ('Vetikon', 'density_25c_g_ml', 0.9722, False),
    ('Neryl Acetate', 'logp', 4.2, False),
    ('Dihydro Beta Ionone', 'vp_25c_pa', 3.8, False),
    ('Dihydro Beta Ionone', 'logp', 3.83, False),
    ('Aldehyde C-9 Nonanal', 'logp', 3.4, False),
    ('Aldehyde C-9 Nonanal', 'density_25c_g_ml', 0.824, False),
    ('D-Limonene', 'vp_25c_pa', 200.0, False),
    ('D-Limonene', 'logp', 4.38, False),
    ('D-Limonene', 'density_25c_g_ml', 0.844, False),
    ('Farnesol', 'logp', 4.72, False),
    ('phenyl ethyl acetate', 'vp_25c_pa', 8.17, False),
    ('Gamma Octalactone', 'vp_25c_pa', 14.1, False),
    ('Gamma Octalactone', 'density_25c_g_ml', 0.975, False),
    ('Aldehyde C-18 Gamma Nonalactone', 'vp_25c_pa', 4.16, False),
    ('Aldehyde C-18 Gamma Nonalactone', 'density_25c_g_ml', 0.962, False),
    ('Gamma Nonalactone', 'vp_25c_pa', 4.16, False),
    ('Gamma Nonalactone', 'density_25c_g_ml', 0.962, False),
    ('Gamma Undecalactone', 'vp_25c_pa', 0.441, False),
    ('Nerol', 'density_25c_g_ml', 0.88, False),
    ('2-Acetyl Pyrazine', 'vp_25c_pa', 9.48, True),
    ('2-Acetyl Pyrazine', 'logp', -0.38, True),
    ('Coumarin', 'vp_25c_pa', 0.08759, True),
    ('coumarin (neat powder)', 'vp_25c_pa', 0.08759, True),
    ('Triplal', 'vp_25c_pa', 52.5, False),
    ('Triplal', 'logp', 2.8, False),
    ('Benzyl Alcohol', 'mw_g_mol', 108.1378, False),
    ('Benzyl Alcohol', 'dhvap_kj_mol', 66.2, False),
    ('Methyl Nonyl Ketone', 'dhvap_kj_mol', 67.0, False),
    ('Aldehyde C-9 Nonanal', 'dhvap_kj_mol', 55.3, False),
    ('Terpinyl Acetate', 'dhvap_kj_mol', 68.1, False),
    ('Cis-3 Hexenyl Hexanoate', 'logp', 4.44, True),
    ('Cinnamyl Alcohol', 'vp_25c_pa', 3.0, False),
    ('Cinnamyl Alcohol', 'logp', 1.95, False),
    ('Mayol', 'logp', 3.45, False),
    ('Lemonile', 'logp', 3.9, False),
    ('jessemal (jasmonyl)', 'vp_25c_pa', 0.466, False),
    ('jessemal (jasmonyl)', 'logp', 2.6, False),
    ('Butyl Butyrate', 'density_25c_g_ml', 0.8721, False),
    ('Cyclogalbanate', 'logp', 2.72, True),
    ('Hindinol', 'vp_25c_pa', 0.03, False),
    ('Alpha Ionone', 'vp_25c_pa', 3.62, True),
    ('Berry Hexanoate (berryflor)', 'vp_25c_pa', 2.37, False),
    ('Berry Hexanoate (berryflor)', 'density_25c_g_ml', 1.00796, False),
    ('Phenyl Ethyl Dimethyl Carbinol', 'logp', 2.93, True),
    ('Vetival', 'logp', 4.36, False),
    ('Cashmeran', 'density_25c_g_ml', 0.969, False),
    ('Geranyl Acetate', 'vp_25c_pa', 2.06, False),
    ('Hydroxycitronellal', 'vp_25c_pa', 0.889, False),
    ('Dimethyl Benzyl Carbinol', 'vp_25c_pa', 8.17, False),
    ('Dimethyl Benzyl Carbinol', 'logp', 1.7, False),
    ('Citronellol', 'logp', 3.1, False),
    ('Citronellol', 'density_25c_g_ml', 0.86, False),
    ('Aldehyde C10', 'vp_25c_pa', 12.3, False),
    ('Aldehyde C10', 'logp', 3.8, False),
    ('Dihydrojasmone', 'vp_25c_pa', 2.12, False),
    ('Dihydrojasmone', 'logp', 3.77, True),
    ('Dihydrojasmone', 'density_25c_g_ml', 0.917, False),
    ('Alpha Ionone', 'density_25c_g_ml', 0.93, False),
    ('Adoxal', 'vp_25c_pa', 0.655, False),
    ('Linalool', 'logp', 2.9, False),
    ('Vanillin', 'vp_25c_pa', 0.01573, True),
    ('Farnesol', 'density_25c_g_ml', 0.8871, False),
    ('Geraniol', 'logp', 2.6, False),
    ('geraniol (10% in dpg)', 'logp', 2.6, False),
    ('Cis Jasmone', 'logp', 2.8, False),
    ('Cis Jasmone', 'density_25c_g_ml', 0.94, False),
    ('Phenyl Ethyl Dimethyl Carbinol', 'mw_g_mol', 164.2441, False),
    ('Aldehyde C10', 'dhvap_kj_mol', 59.5, False),
    ('D-Limonene', 'dhvap_kj_mol', 48.9, False),
    ('Cis-3 Hexenyl Hexanoate', 'density_25c_g_ml', 0.88, False),
    ('Ethyl Safranate', 'logp', 4.2, False),
    ('Undecavertol', 'vp_25c_pa', 2.93, False),
    ('Undecavertol', 'logp', 3.9, False),
    ('Koavone', 'vp_25c_pa', 17.5, False),
    ('Koavone', 'logp', 4.4, False),
    ('Phenyl Ethyl Dimethyl Carbinyl Acetate', 'vp_25c_pa', 1.7, False),
    ('Cyclamen Aldehyde', 'vp_25c_pa', 0.494, False),
    ('Cyclamen Aldehyde', 'logp', 3.4, False),
    ('Calone', 'vp_25c_pa', 0.87, False),
    ('Allyl Amyl Glycolate', 'vp_25c_pa', 19.7, False),
    ('Allyl Amyl Glycolate', 'logp', 1.96, False),
    ('Allyl Amyl Glycolate', 'density_25c_g_ml', 0.94, False),
    ('Benzyl Alcohol', 'vp_25c_pa', 12.0, False),
    ('Benzyl Alcohol', 'logp', 1.05, False),
    ('Benzyl Alcohol', 'density_25c_g_ml', 1.045, False),
    ('Aldehyde C11', 'logp', 4.8, False),
    ('Geraniol', 'density_25c_g_ml', 0.885, False),
    ('Irotyl', 'logp', 3.74, True),
    ('Leafovert', 'vp_25c_pa', 58.2, False),
    ('Liffarome', 'vp_25c_pa', 58.2, False),
    ('Ethyl 2-Methylbutyrate', 'vp_25c_pa', 1010.0, False),
    ('Ethyl 2-Methylbutyrate', 'logp', 2.26, True),
    # (Peach Ketone logp 5.3 left this list on 2026-10-28: ECHA OECD 117 4.8.)
    ('Guaiacol', 'density_25c_g_ml', 1.1287, False),
    ('Methyl Anthranilate', 'density_25c_g_ml', 1.168, False),
    ('Cis-3 Hexenyl Acetate', 'vp_25c_pa', 214.0, False),
    ('Cis-3 Hexenyl Acetate', 'logp', 2.7, True),
    ('Delta Damascone', 'vp_25c_pa', 3.28, False),
    ('Allyl Ionone', 'logp', 5.4, False),
    ('Cedryl Acetate', 'vp_25c_pa', 0.081, False),
    ('Floralozone', 'vp_25c_pa', 0.526, False),
    ('Vetival', 'vp_25c_pa', 14.27, True),
    ('Vetival', 'density_25c_g_ml', 0.9135, False),
    ('Ethyl Linalool', 'vp_25c_pa', 4.16, False),
    ('Ethyl Linalool', 'logp', 3.3, False),
    ('Ethyl Linalool', 'density_25c_g_ml', 0.866, False),
    ('Cinnamaldehyde', 'logp', 1.9, False),
    ('Romandolide', 'vp_25c_pa', 0.0914, False),
    ('Nerolidol', 'logp', 4.8, False),
    ('Manzanate', 'vp_25c_pa', 279.0, False),
    ('Damascenone', 'vp_25c_pa', 3.0, False),
    ('Damascenone', 'logp', 3.4, False),
    ('Hexyl Acetate', 'density_25c_g_ml', 0.875, False),
    ('Evernyl', 'vp_25c_pa', 0.00227, False),
    ('Hedione HC', 'vp_25c_pa', 0.2104, False),
    ('Iso E Super', 'logp', 5.65, False),
    ('Floralozone', 'logp', 3.6, True),
    ('Phenyl Acetaldehyde Dimethyl Acetal (padma)', 'vp_25c_pa', 4.16, False),
    ('Phenyl Acetaldehyde Dimethyl Acetal (padma)', 'logp', 2.23, False),
    ('Phenyl Acetaldehyde Dimethyl Acetal (padma)', 'mw_g_mol', 166.22, False),
    ('Aldehyde C11 Undecylenic', 'vp_25c_pa', 6.17, False),
    ('Linalyl Acetate', 'logp', 4.0, False),
    ('Linalyl Acetate', 'density_25c_g_ml', 0.9, False),
    ('Amyl Cinnamic Aldehyde (ACA)', 'logp', 4.7, False),
    ('Amyl Cinnamic Aldehyde (ACA)', 'mw_g_mol', 202.29, False),
    ('Dimethyl Benzyl Carbinyl Acetate', 'vp_25c_pa', 2.12, False),
    ('Ethyl Maltol', 'vp_25c_pa', 0.01933, True),
    ('Ethyl Maltol', 'logp', 0.3, True),
    ('Citral', 'vp_25c_pa', 14.1, False),
    ('Citral', 'density_25c_g_ml', 0.89, False),
    # (Methyl Diantilis vp_25c_pa left this list on 2026-10-28: ECHA key study 0.003 Pa at 20 C, converted.)
    ('Beta Ionone', 'vp_25c_pa', 0.972, False),
    ('Beta Ionone', 'logp', 4.1, False),
    ('Beta Ionone', 'density_25c_g_ml', 0.943, False),
    ('Aldehyde C-12 Lauric Dodecanal', 'dhvap_kj_mol', 68.3, False),
    ('Safraleine', 'vp_25c_pa', 1.2, False),
    ('Safraleine', 'logp', 2.9, False),
    ('Aldehyde C12 MNA', 'vp_25c_pa', 6.0, False),
    ('Scentenal', 'vp_25c_pa', 0.655, False),
    ('Safranal', 'vp_25c_pa', 14.1, False),
    ('Safranal', 'logp', 2.7, False),
    ('Safranal', 'density_25c_g_ml', 0.974, False),
    ('Aldehyde C-16 Ethyl Methyl Phenyl Glycidate', 'logp', 2.8, False),
    ('Benzaldehyde', 'vp_25c_pa', 169.0, False),
    ('Benzaldehyde', 'logp', 1.4, False),
    ('Hexyl Salicylate', 'vp_25c_pa', 0.0955, False),
    ('Hedione', 'logp', 2.8, False),
    ('Hedione HC', 'logp', 2.93, False),
    ('Cinnamaldehyde', 'density_25c_g_ml', 1.05, False),
    ('Para-Cresyl Methyl Ether', 'vp_25c_pa', 243.0, False),
    ('Citronellal', 'vp_25c_pa', 26.0, False),
    ('Citronellal', 'density_25c_g_ml', 0.857, False),
    ('Bourgeonal', 'vp_25c_pa', 0.333, False),
    ('Bourgeonal', 'logp', 3.2, False),
    ('Bourgeonal', 'density_25c_g_ml', 0.962, False),
    ('Magnolan', 'vp_25c_pa', 0.208, True),
    ('Sandalore', 'vp_25c_pa', 0.0591, True),
    ('Delta Decalactone', 'logp', 2.57, True),
    ('Delta Decalactone', 'density_25c_g_ml', 0.973, False),
    ('Verdox', 'vp_25c_pa', 10.2, False),
    ('Aurantiol', 'vp_25c_pa', 0.284, False),
    ('Aurantiol', 'logp', 4.8, False),
    ('Aurantiol', 'density_25c_g_ml', 1.05796, False),
    ('Apritone', 'logp', 5.6, False),
    ('Clearwood', 'logp', 5.31, False),
    ('Dynascone', 'vp_25c_pa', 2.28, False),
    ('Florol', 'logp', 2.22, False),
    ('Isobutavan', 'logp', 2.0, False),
    ('Methyl Diantilis', 'logp', 1.1, False),
    ('Cedramber', 'vp_25c_pa', 0.616, False),
    ('Cedramber', 'logp', 6.0, False),
    ('Ethylene Brassylate', 'vp_25c_pa', 0.0302, False),
    ('Ethylene Brassylate', 'logp', 4.3, False),
    ('Nerolidol', 'mw_g_mol', 222.37, False),
]


@pytest.mark.parametrize(("record", "field", "value", "estimate"), LOADED)
def test_value_is_loaded_with_a_dated_provenance(record, field, value, estimate):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    provenance = spine.provenance[field]
    assert "2026-10-25" in provenance
    assert provenance.startswith("ESTIMATE") == estimate
    for host in ("thegoodscents", "scentree", "fragrantica", "wikipedia"):
        assert host not in provenance.lower()
    if field == "vp_25c_pa":
        assert spine.vp_source.endswith("_est") == estimate


# Values a second reader flagged stay as they were.
HELD = [
    ("Melonal", "vp_25c_pa", 239.0),  # OECD 104 at 25 C vs RIFM 53 Pa at 20 C
    ("Hedione", "vp_25c_pa", 0.09466),  # ECHA's figure is for the high-cis grade
    ("Citronellol", "vp_25c_pa", 2.26),  # 9.52 Pa has no printed temperature
    ("Veloutone", "vp_25c_pa", 9.2),  # FMA 53 Pa at 20 C stays out; ECHA OECD 104 9.2 Pa loaded 2026-10-28
    ("Allyl Ionone", "vp_25c_pa", 0.0664),  # Givaudan 13 Pa has no temperature
    ("Acetoin", "logp", -0.36),  # the source's 0.36 lost its minus sign
]


@pytest.mark.parametrize(("record", "field", "value"), HELD)
def test_flagged_values_were_not_loaded(record, field, value):
    assert getattr(load_registry().get(record), field) == pytest.approx(value)


# Measured values the batch must not replace with a weaker figure (an FMA number with one
# significant figure, or a product page with no method).
KEPT_MEASURED = [
    ("Canthoxal", "vp_25c_pa", 0.3),  # ECHA key study at 24 C, not RIFM's FMA 0.006 mm Hg
    ("Phenoxy Ethyl Isobutyrate", "vp_25c_pa", 0.77),  # ECHA key study at 25 C
    ("Hexyl Salicylate", "logp", 5.5),  # RIFM 1996 measurement, not Givaudan's 4.9
    ("Alpha Irone", "logp", 3.9),  # mean of RIFM's two measurements, not Givaudan's 4.4
]


@pytest.mark.parametrize(("record", "field", "value"), KEPT_MEASURED)
def test_measured_values_are_kept_over_weaker_figures(record, field, value):
    spine = load_registry().get(record)
    assert getattr(spine, field) == pytest.approx(value)
    assert "Kept on 2026-10-25" in spine.provenance[field]


def test_fma_figures_are_not_labelled_measured():
    # The FMA database is member-supplied with no method, so its figures are producer data.
    for spine in load_registry().all():
        provenance = (spine.provenance or {}).get("vp_25c_pa") or ""
        if "2026-10-25" in provenance and "FMA database figure" in provenance:
            assert spine.vp_source.startswith("producer_"), spine.canonical_name


def test_acetylpyrazine_uses_the_epi_figure_not_the_fma_one():
    spine = load_registry().get("2-Acetyl Pyrazine")
    assert spine.vp_25c_pa == pytest.approx(9.48)
    assert spine.vp_source == "EPI_est"


@pytest.mark.parametrize("name", ["Dynascone", "Calone", "Vanillin", "Ethyl Maltol"])
def test_profile_vapour_pressure_follows_the_spine(name):
    assert get_profile(name).vp == pytest.approx(load_registry().get(name).vp_25c_pa)
