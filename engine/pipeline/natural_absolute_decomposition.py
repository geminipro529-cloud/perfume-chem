"""Natural Mixture Decomposition Model — ALL EOs, Absolutes, Naturals.

Replaces the monomolecular OAV for natural mixtures by decomposing
them into known GC-O constituents and summing individual OAVs.

Covers: flower absolutes, citrus EOs, resinoids, complex naturals.

Reference data:
  - Osmanthus: Hong et al. (2023), Guo et al. (2024/2025), Jia et al. (2025)
  - Rose: Ohloff (1994), van Gemert (2011)
  - Jasmine: Braun & Sim (1983), Kaiser (1988)
  - Tuberose: Kaiser (1993), Pickenhagen et al. (2004)
  - Bergamot/Petitgrain: Dugo et al. (2011)
  - Patchouli: van Beek & Joulain (2018)
  - Oakmoss: Joulain & Tabacchi (2009)
  - Ylang: Gaydou et al. (1986)
  - Vetiver: Weyerstahl et al. (2000)
  - Labdanum: Weyerstahl et al. (1998)
  - Orris Liquid: PerfumersWorld SKU 8IQ24653; Shanaida et al. (2020)
  - Olibanum: PerfumersWorld SKU 2QK21856; Woolley et al. (2012)

Format: (constituent name, weight fraction, MW, VP at 25C Pa, ODT air ppb, gamma)
"""

# ── Flower Absolutes ────────────────────────────────────────────────

_OSMANTHUS_CONSTITUENTS = [
    ("beta ionone", 0.10, 192.30, 1.20, 0.10, 1.5),
    ("dihydro beta ionone", 0.08, 194.31, 0.50, 0.30, 1.5),
    ("linalool", 0.08, 154.25, 21.30, 1.50, 2.0),
    ("linalool oxide", 0.06, 170.25, 5.00, 1.00, 1.5),
    ("gamma decalactone", 0.03, 170.25, 0.50, 1.50, 1.8),
    ("alpha ionone", 0.03, 192.30, 1.00, 0.50, 1.5),
    ("geraniol", 0.03, 154.25, 4.00, 2.00, 1.5),
    ("theaspirane", 0.015, 194.27, 0.80, 0.10, 1.2),
    ("phenethyl alcohol", 0.05, 122.16, 0.12, 200.0, 0.7),
    ("hotrienol", 0.02, 152.23, 2.00, 5.00, 1.5),
]

# Supplier declares 80-85% irone but does not publish an isomer split. The
# midpoint is modeled as an alpha-irone-equivalent pool; 17.5% remains unknown.
_ORRIS_LIQUID_CONSTITUENTS = [
    ("irone pool (alpha-equivalent)", 0.825, 206.32, 0.559, 0.9, 1.3),
]

_ROSE_DE_MAI_CONSTITUENTS = [
    ("citronellol", 0.18, 156.27, 7.00, 10.0, 1.5),
    ("geraniol", 0.10, 154.25, 4.00, 2.00, 1.5),
    ("nerol", 0.05, 154.25, 2.02, 5.00, 1.5),
    ("phenethyl alcohol", 0.15, 122.16, 0.12, 200.0, 0.7),
    ("linalool", 0.03, 154.25, 21.30, 1.50, 2.0),
    ("beta damascone", 0.0005, 192.30, 0.50, 0.002, 1.5),
    ("beta ionone", 0.01, 192.30, 1.20, 0.10, 1.5),
    ("rose oxide", 0.005, 154.25, 15.00, 0.50, 2.0),
    ("eugenol", 0.008, 164.20, 2.50, 0.50, 1.5),
    ("farnesol", 0.03, 222.37, 0.05, 3.00, 0.6),
]

_JASMINE_SAMBAC_CONSTITUENTS = [
    ("benzyl acetate", 0.15, 150.17, 20.00, 2.00, 2.0),
    ("linalool", 0.10, 154.25, 21.30, 1.50, 2.0),
    ("indole", 0.005, 117.15, 1.20, 0.14, 1.8),
    ("methyl anthranilate", 0.03, 151.16, 0.10, 15.0, 1.2),
    ("benzyl alcohol", 0.08, 108.14, 8.00, 5.00, 1.5),
    ("cis-jasmone", 0.02, 164.24, 0.50, 1.00, 1.8),
    ("methyl jasmonate", 0.01, 224.30, 0.10, 0.20, 1.8),
    ("farnesene", 0.05, 204.35, 3.00, 5.00, 1.2),
    ("phenethyl alcohol", 0.05, 122.16, 0.12, 200.0, 0.7),
]

_TUBEROSE_CONSTITUENTS = [
    ("methyl benzoate", 0.08, 136.15, 50.00, 0.50, 2.0),
    ("methyl salicylate", 0.04, 152.15, 7.00, 10.0, 1.5),
    ("benzyl benzoate", 0.06, 212.24, 0.02, 810.0, 0.5),
    ("eugenol", 0.02, 164.20, 2.50, 0.50, 1.5),
    ("indole", 0.005, 117.15, 1.20, 0.14, 1.8),
    ("methyl anthranilate", 0.01, 151.16, 0.10, 15.0, 1.2),
    ("linalool", 0.05, 154.25, 21.30, 1.50, 2.0),
    ("benzyl acetate", 0.03, 150.17, 20.00, 2.00, 2.0),
]

_IMMORTELLE_CONSTITUENTS = [
    ("neryl acetate", 0.15, 196.29, 3.00, 10.0, 1.5),
    ("gamma curcumene", 0.05, 202.34, 0.50, 5.00, 1.2),
    ("beta diketone", 0.03, 220.35, 0.01, 0.50, 0.5),
    ("linalool", 0.05, 154.25, 21.30, 1.50, 2.0),
    ("alpha pinene", 0.02, 136.24, 400.0, 20.0, 3.0),
]

_ROSE_EO_CONSTITUENTS = [
    ("citronellol", 0.35, 156.27, 2.0, 5.0, 2.0),
    ("geraniol", 0.20, 154.25, 4.0, 2.0, 1.5),
    ("linalool", 0.03, 154.25, 21.3, 1.5, 2.0),
    ("phenethyl alcohol", 0.03, 122.16, 2.0, 3.0, 2.0),
]

_CASSIA_EO_CONSTITUENTS = [
    ("cinnamaldehyde", 0.80, 132.16, 3.0, 0.5, 2.0),
    ("coumarin", 0.02, 146.14, 0.05, 2.0, 0.5),
    ("linalool", 0.02, 154.25, 21.3, 1.5, 2.0),
]

_YLANG_YLANG_CONSTITUENTS = [
    ("linalool", 0.12, 154.25, 21.30, 1.50, 2.0),
    ("benzyl acetate", 0.10, 150.17, 20.00, 2.00, 2.0),
    ("benzyl benzoate", 0.05, 212.24, 0.02, 810.0, 0.5),
    ("methyl benzoate", 0.05, 136.15, 50.00, 0.50, 2.0),
    ("para-cresyl methyl ether", 0.04, 122.16, 3.00, 1.00, 1.5),
    ("caryophyllene", 0.05, 204.35, 1.00, 10.0, 1.2),
    ("geranyl acetate", 0.05, 196.29, 2.00, 10.0, 1.5),
    ("farnesene", 0.03, 204.35, 3.00, 5.00, 1.2),
    ("eugenol", 0.02, 164.20, 2.50, 0.50, 1.5),
]

# ── Citrus EOs ───────────────────────────────────────────────────────

_BERGAMOT_FCF_CONSTITUENTS = [
    ("limonene", 0.38, 136.24, 200.0, 20.0, 3.0),
    ("linalool", 0.15, 154.25, 21.30, 1.50, 2.0),
    ("linalyl acetate", 0.28, 196.29, 17.50, 2.70, 2.0),
    ("gamma terpinene", 0.08, 136.24, 90.0, 50.0, 3.0),
    ("beta pinene", 0.06, 136.24, 250.0, 30.0, 3.0),
    ("geranial", 0.005, 152.23, 3.00, 0.50, 1.5),
]

_GRAPEFRUIT_FCF_CONSTITUENTS = [
    ("limonene", 0.65, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.02, 136.24, 400.0, 10.0, 3.0),
    ("alpha pinene", 0.01, 136.24, 400.0, 20.0, 3.0),
    ("octanal", 0.005, 128.21, 300.0, 0.50, 2.5),
    ("nootkatone", 0.003, 218.33, 0.05, 0.01, 1.5),
    ("linalool", 0.01, 154.25, 21.30, 1.50, 2.0),
]

_CEDRAT_FCF_CONSTITUENTS = [
    ("limonene", 0.50, 136.24, 200.0, 20.0, 3.0),
    ("gamma terpinene", 0.15, 136.24, 90.0, 50.0, 3.0),
    ("linalool", 0.05, 154.25, 21.30, 1.50, 2.0),
    ("linalyl acetate", 0.03, 196.29, 17.50, 2.70, 2.0),
    ("citral", 0.02, 152.23, 3.00, 0.50, 1.5),
]

_PETITGRAIN_EO_CONSTITUENTS = [
    ("linalool", 0.25, 154.25, 21.30, 1.50, 2.0),
    ("linalyl acetate", 0.45, 196.29, 17.50, 2.70, 2.0),
    ("alpha terpineol", 0.06, 154.25, 2.00, 10.0, 1.5),
    ("geraniol", 0.04, 154.25, 4.00, 2.00, 1.5),
    ("nerol", 0.03, 154.25, 2.02, 5.00, 1.5),
    ("alpha pinene", 0.02, 136.24, 400.0, 20.0, 3.0),
]

# ── Resinoids / Base Naturals ────────────────────────────────────────

_OAKMOSS_ABSOLUTE_CONSTITUENTS = [
    # Primary volatile monoaryls — the odor carriers
    ("ethyl orsellinate", 0.06, 196.20, 0.10, 1.00, 0.6),
    ("methyl beta-orcinol carboxylate", 0.05, 210.23, 0.08, 1.00, 0.6),
    # Evernyl class — synthetic analog, naturally present at trace
    ("evernyl", 0.15, 196.20, 0.05, 1.00, 0.6),
    # Orcinol derivatives — higher VP phenolics
    ("orcinol", 0.02, 124.14, 0.50, 5.00, 0.5),
    ("beta-orcinol", 0.01, 168.19, 0.15, 3.00, 0.5),
    # Atranorin degradation products — potent odorants formed on skin
    # Atranorin (40-60% of absolute) + skin moisture → atranol + evernic acid
    # Effective steady-state concentration: ~0.5-1% of absolute
    ("atranol", 0.08, 240.21, 0.01, 0.10, 0.5),
    # Chloroatranorin → chloroatranol (same pathway)
    ("chloroatranol", 0.03, 274.66, 0.005, 0.05, 0.5),
    # Usnic acid — non-volatile, anti-microbial, lichen character
    ("usnic acid", 0.03, 344.32, 0.001, 0.10, 0.4),
    # Additional volatiles identified by GC-MS (Joulain 2009, Chittiboyina 2020)
    ("ethyl everninate", 0.02, 210.23, 0.05, 2.00, 0.6),
    ("methyl orsellinate", 0.01, 182.18, 0.20, 3.00, 0.6),
]

_PATCHOULI_EO_CONSTITUENTS = [
    ("patchoulol", 0.30, 222.37, 0.005, 1.00, 0.5),
    ("alpha bulnesene", 0.12, 204.35, 0.50, 5.00, 1.2),
    ("alpha guaiene", 0.10, 204.35, 1.00, 3.00, 1.2),
    ("seychellene", 0.05, 204.35, 0.80, 5.00, 1.2),
    ("nor patchoulenol", 0.04, 206.32, 0.01, 0.50, 0.5),
    ("caryophyllene", 0.03, 204.35, 1.00, 10.0, 1.2),
]

_LABDANUM_RESINOID_CONSTITUENTS = [
    ("alpha pinene", 0.15, 136.24, 400.0, 20.0, 3.0),
    ("camphene", 0.05, 136.24, 400.0, 50.0, 3.0),
    ("labdanolic acid", 0.10, 306.49, 0.001, 1.00, 0.4),
    ("ambrinol", 0.02, 236.39, 0.05, 0.50, 0.5),
    ("cistus ladaniferus resin", 0.20, 300.0, 0.0001, 5.00, 0.4),
    ("benzyl benzoate", 0.03, 212.24, 0.02, 810.0, 0.5),
]

_BENZOIN_RESINOID_CONSTITUENTS = [
    ("benzyl benzoate", 0.10, 212.24, 0.02, 810.0, 0.5),
    ("vanillin", 0.05, 152.15, 0.01, 0.10, 0.5),
    ("coniferyl benzoate", 0.15, 284.31, 0.001, 5.00, 0.4),
    ("cinnamic acid", 0.08, 148.16, 0.005, 5.00, 0.5),
    ("benzoic acid", 0.05, 122.12, 0.10, 50.0, 0.6),
]

# SKU 2QK21856 declares about 30% benzyl benzoate. The terpene fractions are a
# deliberately partial, conservative Boswellia carteri volatile model; the
# uncharacterized nonvolatile resin matrix is not normalized into these values.
_OLIBANUM_RESINOID_CONSTITUENTS = [
    ("benzyl benzoate", 0.30, 212.24, 0.02, 810.0, 0.7),
    ("alpha pinene", 0.015, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.006, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.003, 136.24, 400.0, 10.0, 3.0),
    ("sabinene", 0.002, 136.24, 300.0, 30.0, 3.0),
]

_VETIVER_EO_CONSTITUENTS = [
    ("khusimol", 0.15, 220.35, 0.001, 0.50, 0.4),
    ("vetivone", 0.10, 218.33, 0.005, 1.00, 0.5),
    ("vetiselinenol", 0.05, 222.37, 0.01, 2.00, 0.5),
    ("nootkatone", 0.01, 218.33, 0.05, 0.01, 1.5),
    ("cedrene", 0.08, 204.35, 3.00, 10.0, 1.2),
]

_CEDARWOOD_EO_CONSTITUENTS = [
    ("cedrol", 0.30, 222.37, 0.001, 2.00, 0.5),
    ("thujopsene", 0.15, 204.35, 2.00, 5.00, 1.2),
    ("alpha cedrene", 0.15, 204.35, 3.00, 10.0, 1.2),
    ("beta cedrene", 0.10, 204.35, 2.00, 10.0, 1.2),
    ("widdrol", 0.05, 222.37, 0.005, 1.00, 0.5),
]

_LAVENDER_EO_CONSTITUENTS = [
    ("linalool", 0.30, 154.25, 21.30, 1.50, 2.0),
    ("linalyl acetate", 0.35, 196.29, 17.50, 2.70, 2.0),
    ("lavandulol", 0.03, 154.25, 3.00, 10.0, 1.5),
    ("terpinen-4-ol", 0.04, 154.25, 10.00, 50.0, 1.5),
    ("camphor", 0.05, 152.23, 25.00, 100.0, 2.0),
    ("1,8-cineole", 0.03, 154.25, 200.0, 50.0, 2.0),
    ("ocimene", 0.04, 136.24, 250.0, 20.0, 3.0),
]

_CARDAMOM_EO_CONSTITUENTS = [
    ("1,8-cineole", 0.30, 154.25, 200.0, 50.0, 2.0),
    ("alpha terpinyl acetate", 0.35, 196.29, 2.00, 50.0, 1.5),
    ("limonene", 0.05, 136.24, 200.0, 20.0, 3.0),
    ("linalool", 0.05, 154.25, 21.30, 1.50, 2.0),
    ("sabinene", 0.03, 136.24, 300.0, 30.0, 3.0),
    ("myrcene", 0.02, 136.24, 400.0, 10.0, 3.0),
]

_GERANIUM_EO_CONSTITUENTS = [
    ("citronellol", 0.25, 156.27, 7.00, 10.0, 1.5),
    ("geraniol", 0.15, 154.25, 4.00, 2.00, 1.5),
    ("linalool", 0.08, 154.25, 21.30, 1.50, 2.0),
    ("citronellyl formate", 0.08, 184.28, 2.00, 20.0, 1.5),
    ("geranyl formate", 0.05, 182.26, 1.50, 20.0, 1.5),
    ("rose oxide", 0.01, 154.25, 15.00, 0.50, 2.0),
]

_JUNIPER_BERRY_EO_CONSTITUENTS = [
    ("alpha pinene", 0.35, 136.24, 400.0, 20.0, 3.0),
    ("myrcene", 0.12, 136.24, 400.0, 10.0, 3.0),
    ("sabinene", 0.10, 136.24, 300.0, 30.0, 3.0),
    ("limonene", 0.08, 136.24, 200.0, 20.0, 3.0),
    ("terpinen-4-ol", 0.04, 154.25, 10.00, 50.0, 1.5),
    ("beta pinene", 0.05, 136.24, 250.0, 30.0, 3.0),
]

_ROSEMARY_EO_CONSTITUENTS = [
    ("1,8-cineole", 0.35, 154.25, 200.0, 50.0, 2.0),
    ("alpha pinene", 0.15, 136.24, 400.0, 20.0, 3.0),
    ("camphor", 0.12, 152.23, 25.00, 100.0, 2.0),
    ("camphene", 0.05, 136.24, 400.0, 50.0, 3.0),
    ("borneol", 0.03, 154.25, 3.00, 10.0, 1.5),
    ("verbenone", 0.02, 150.22, 2.00, 5.00, 1.5),
]

_NAGARMOTHA_CONSTITUENTS = [
    ("cyperene", 0.25, 204.35, 1.00, 5.00, 1.2),
    ("cyperotundone", 0.15, 218.33, 0.05, 1.00, 0.5),
    ("rotundene", 0.10, 204.35, 0.80, 5.00, 1.2),
    ("mustakone", 0.05, 218.33, 0.01, 0.50, 0.5),
    ("caryophyllene oxide", 0.05, 220.35, 0.10, 2.00, 0.6),
]

# ── Cassis Base 345B (Firmenich) — reconstructed from IFRA cert + ScenTree 345F + cassis absolute GC-MS ──

_CASSIS_BASE_345B_CONSTITUENTS = [
    # Terpene backbone (~40%, from natural cassis absolute profile + labeled ingredients)
    ("alpha pinene", 0.10, 136.24, 400.0, 20.0, 3.0),
    ("beta pinene", 0.12, 136.24, 250.0, 30.0, 3.0),
    ("limonene", 0.06, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.04, 136.24, 400.0, 10.0, 3.0),
    ("terpinolene", 0.06, 136.24, 90.0, 50.0, 2.5),
    ("beta caryophyllene", 0.03, 204.35, 1.0, 10.0, 1.2),
    # Character molecules (from ScenTree 345F + IFRA certificate)
    ("citronellol", 0.10, 156.27, 7.0, 10.0, 1.5),  # IFRA: 3.0%
    ("triplal", 0.04, 152.24, 0.5, 0.001, 1.5),  # IFRA: 1.25%
    ("rose oxide", 0.05, 154.25, 15.0, 0.5, 2.0),
    ("dynascone", 0.01, 168.23, 0.001, 0.001, 0.6),
    ("hydroxycitronellal", 0.03, 172.27, 0.3, 1.0, 1.2),
    ("veloutone", 0.02, 166.26, 0.1, 0.1, 1.0),  # IFRA: 0.125%
    ("methyl atrarate", 0.01, 196.20, 0.01, 0.5, 0.5),
    # Sulfur trace — THE cassis molecule
    ("buchu mercaptan", 0.00005, 186.31, 1.0, 0.0001, 1.0),
    # Floral-fruity traces
    ("geraniol", 0.002, 154.25, 4.0, 2.0, 1.5),  # IFRA: 0.02%
    ("citral", 0.0001, 152.24, 12.0, 10.0, 2.0),  # IFRA: 0.0006%
    ("beta damascenone", 0.0005, 190.28, 0.01, 0.002, 0.7),
    # Solvent/carrier balance (~25%)
    ("dipropylene glycol", 0.25, 134.17, 1.0, 10000.0, 0.5),
]

# ── Master Registry ───────────────────────────────────────────────────

_ABSOLUTE_CONSTITUENTS = {
    # Flower absolutes
    "osmanthus absolute": _OSMANTHUS_CONSTITUENTS,
    "orris liquid": _ORRIS_LIQUID_CONSTITUENTS,
    "orris liquid (30%)": _ORRIS_LIQUID_CONSTITUENTS,
    "rose de mai absolute": _ROSE_DE_MAI_CONSTITUENTS,
    "jasmine sambac": _JASMINE_SAMBAC_CONSTITUENTS,
    "jasmine sambac (10% in dpg)": _JASMINE_SAMBAC_CONSTITUENTS,
    "tuberose absolute": _TUBEROSE_CONSTITUENTS,
    "tuberose absolute (india)": _TUBEROSE_CONSTITUENTS,
    "immortelle absolute": _IMMORTELLE_CONSTITUENTS,
    "ylang ylang eo (extra grade)": _YLANG_YLANG_CONSTITUENTS,
    "ylang comoros complete eo f3255": _YLANG_YLANG_CONSTITUENTS,
    "ylang comoros iii eo f3295": _YLANG_YLANG_CONSTITUENTS,
    # Citrus EOs
    "bergamot fcf": _BERGAMOT_FCF_CONSTITUENTS,
    "grapefruit fcf": _GRAPEFRUIT_FCF_CONSTITUENTS,
    "cedrat fcf sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "cedrat fcf oil sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "petitgrain eo paraguay": _PETITGRAIN_EO_CONSTITUENTS,
    # Resinoids / Base naturals
    "oakmoss absolute": _OAKMOSS_ABSOLUTE_CONSTITUENTS,
    "oakmoss absolute (10% in dpg)": _OAKMOSS_ABSOLUTE_CONSTITUENTS,
    "patchouli eo": _PATCHOULI_EO_CONSTITUENTS,
    "labdanum resinoid": _LABDANUM_RESINOID_CONSTITUENTS,
    "labdanum resinoid (10% in dpg)": _LABDANUM_RESINOID_CONSTITUENTS,
    "benzoin resinoid": _BENZOIN_RESINOID_CONSTITUENTS,
    "benzoin resinoid (50% in dpg)": _BENZOIN_RESINOID_CONSTITUENTS,
    "olibanum resinoid": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid (viscous)": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid (viscous, 3 g)": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid absolute": _OLIBANUM_RESINOID_CONSTITUENTS,
    "vetiver eo (india)": _VETIVER_EO_CONSTITUENTS,
    "vetiver eo": _VETIVER_EO_CONSTITUENTS,
    "cedarwood eo": _CEDARWOOD_EO_CONSTITUENTS,
    "nagarmortha oil": _NAGARMOTHA_CONSTITUENTS,
    "nagar motha oil": _NAGARMOTHA_CONSTITUENTS,
    # Other EOs
    "lavender eo (bontaux sas)": _LAVENDER_EO_CONSTITUENTS,
    "lavender eo": _LAVENDER_EO_CONSTITUENTS,
    "cardamom eo": _CARDAMOM_EO_CONSTITUENTS,
    "geranium flower eo": _GERANIUM_EO_CONSTITUENTS,
    "juniper berry eo": _JUNIPER_BERRY_EO_CONSTITUENTS,
    "rosemary eo": _ROSEMARY_EO_CONSTITUENTS,
    "rosemary eo (french rosmarinus officinalis leaf oil)": _ROSEMARY_EO_CONSTITUENTS,
    "geranium eo": _GERANIUM_EO_CONSTITUENTS,
    # Specialty bases
    "cassis base 345b": _CASSIS_BASE_345B_CONSTITUENTS,
    # New EOs 2026-06-15
    "rose essential oil": _ROSE_EO_CONSTITUENTS,
    "cassia essential oil": _CASSIA_EO_CONSTITUENTS,
}


def get_constituents(material_name: str) -> list[tuple] | None:
    """Return constituent list for a known natural mixture, or None."""
    key = material_name.lower().strip()
    return _ABSOLUTE_CONSTITUENTS.get(key)


def composite_oav(
    material_name: str,
    active_g: float,
    total_moles_in_formula: float,
    gamma_estimate: float = 0.6,
) -> float | None:
    """Compute the composite OAV for a natural mixture.

    Decomposes the mixture into its known GC-O constituents and sums
    the individual OAVs computed via modified Raoult's law.

    Args:
        material_name: canonical name (e.g. "osmanthus absolute")
        active_g: active mass in grams in the formula
        total_moles_in_formula: sum of moles of all formula materials
        gamma_estimate: default activity coefficient if none specified

    Returns:
        Composite OAV as float, or None if material not known.
    """
    constituents = get_constituents(material_name)
    if constituents is None:
        return None

    P_ATM = 101_325.0  # Pa
    total_oav = 0.0

    for _name, fraction, mw, vp_Pa, odt_ppb, gamma in constituents:
        constituent_mass_g = active_g * fraction
        if constituent_mass_g <= 0:
            continue
        moles = constituent_mass_g / mw
        x_i = moles / total_moles_in_formula if total_moles_in_formula > 0 else 0.0
        partial_pressure = gamma * x_i * vp_Pa
        vapor_ppm = 1e6 * partial_pressure / P_ATM
        odt_ppm = odt_ppb / 1000.0
        if odt_ppm > 0:
            total_oav += vapor_ppm / odt_ppm

    return total_oav if total_oav > 0 else None
