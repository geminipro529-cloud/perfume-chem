"""Natural Mixture Decomposition Model — ALL EOs, Absolutes, Naturals.

Replaces the monomolecular OAV for natural mixtures by decomposing
them into literature constituent profiles and summing modeled OAV contributions.
Analytical methods and input authority are profile-specific; a constituent
profile is not evidence of GC-O measurement or complete quantitative coverage.

Covers: flower absolutes, citrus EOs, resinoids, complex naturals.

Reference data:
  - Osmanthus: Hong et al. (2023), Guo et al. (2024/2025), Jia et al. (2025)
  - Rose: Ohloff (1994), van Gemert (2011)
  - Jasmine: Braun & Sim (1983), Kaiser (1988)
  - Tuberose: Kaiser (1993), Pickenhagen et al. (2004)
  - Bergamot/Petitgrain: Dugo et al. (2011)
  - Distilled lime: Chisholm, Wilson & Gaskey (2003), DOI 10.1002/ffj.1172
  - Cocoa liquor: Tuenter et al. (2020), DOI 10.1016/j.foodres.2019.108943
  - Cocoa SFE: Sanagi, Hung & Yasir (1997), DOI 10.1016/S0021-9673(97)00569-4
  - Cocoa aldehyde air ODTs: Sakuma et al. (2013), Exp. Anim. 62, 101-107
  - Trimethylpyrazine air ODT: Liang et al. (2022), DOI 10.1021/acs.jafc.2c06418
  - Patchouli: van Beek & Joulain (2018)
  - Oakmoss: Joulain & Tabacchi (2009)
  - Ylang: Gaydou et al. (1986)
  - Vetiver: Weyerstahl et al. (2000)
  - Labdanum: Weyerstahl et al. (1998)
  - Orris Liquid: PerfumersWorld SKU 8IQ24653; Shanaida et al. (2020)
  - Olibanum: PerfumersWorld SKU 2QK21856; Woolley et al. (2012)

Format: (constituent name, nominal model fraction, MW, VP at 25C Pa, ODT air ppb, gamma)
The fraction basis is profile-specific. GC-FID areas used as nominal mass-model
inputs are proxies, not measured mass fractions; subsets are never rescaled.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from engine.name_utils import normalize_name
from engine.thermo.antoine import (
    DEFAULT_DHVAP_ESTIMATE_KJ_MOL,
    VP25_DHVAP_CORRELATION_SOURCE,
    estimate_dhvap_from_vp_25c,
    vp_pa,
)

# ── Flower Absolutes ────────────────────────────────────────────────

_OSMANTHUS_CONSTITUENTS = [
    # Kaiser & Lamparsky 1981 "Volatile Constituents of Osmanthus Absolute"
    # in Essential Oils, Allured Publ. Corp., pp. 159-191.
    # Extraction: solvent extraction (petroleum ether/hexane) -> absolute.
    # Note: 48% is non-volatile fatty acids/waxes from solvent extraction
    # that contribute mass but ZERO headspace OAV (VP ~ 0 Pa).
    ("beta ionone", 0.076, 192.30, 1.20, 0.10, 1.5),  # Character compound — fruity-floral
    ("dihydro beta ionone", 0.064, 194.31, 0.50, 0.30, 1.5),  # Woody-violet supporting ionone
    ("gamma decalactone", 0.040, 170.25, 0.50, 1.50, 1.8),  # Peach-creamy lactone
    ("linalool", 0.030, 154.25, 21.30, 1.50, 2.0),  # Fresh floral lift
    ("alpha ionone", 0.010, 192.30, 1.00, 0.50, 1.5),  # Woody-violet minor ionone
    ("geraniol", 0.008, 154.25, 4.00, 2.00, 1.5),  # Rosy-floral alcohol
    # Non-volatile fatty acid/wax fraction (VP=0.0 — mass only, no odor)
    ("linolenic acid", 0.174, 278.43, 0.0, 1e6, 0.5),
    ("9,12-octadecadienoic acid", 0.087, 280.45, 0.0, 1e6, 0.5),
    ("palmitic acid", 0.086, 256.42, 0.0, 1e6, 0.5),
    ("oleic acid", 0.070, 282.46, 0.0, 1e6, 0.5),
    ("ethyl linolenate", 0.063, 306.48, 0.0, 1e6, 0.5),
]
# Total volatile odor-active fraction: ~23.8%
# Total including non-volatile carriers: ~71.8%

# The in-stock volume grade is documented as a lower-beta-ionone structural
# grade, but no supplier batch GC-MS/GC-O is available.  Published osmanthus
# profiles vary materially by cultivar and extraction (Hu et al., 2009,
# doi:10.1365/s10337-009-1255-0; Zhang et al., 2017,
# doi:10.1186/s12918-017-0523-0).  Preserve the literature fingerprint while
# scaling its characterized odor-active fraction by the repository's existing
# effective-ODT ratio: premium 0.5 ppb / volume grade 2.0 ppb = 0.25.  The
# uncharacterized remainder is deliberately left inert rather than normalized.
_OSMANTHUS_VOLUME_GRADE_POTENCY = 0.25
_OSMANTHUS_VOLUME_GRADE_CONSTITUENTS = [
    (name, fraction * _OSMANTHUS_VOLUME_GRADE_POTENCY, mw, vp, odt, gamma)
    for name, fraction, mw, vp, odt, gamma in _OSMANTHUS_CONSTITUENTS
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
    # Eden Botanicals commercial tuberose absolute COA (Lot 966, 92.97% total).
    # Extraction: hexane solvent extraction -> absolute. Key character: methyl isoeugenol
    # (spicy-clove carnation), jasmolactone (creamy lactonic), methyl benzoate (fruity).
    ("methyl isoeugenol", 0.234, 178.23, 0.50, 0.10, 1.2),  # Dominant odorant — spicy carnation
    ("palmitic acid", 0.098, 256.42, 0.0, 1e6, 0.5),  # Fatty acid (solvent artifact — non-volatile)
    ("linolenic acid", 0.080, 278.43, 0.0, 1e6, 0.5),  # Fatty acid (solvent artifact)
    ("jasmolactone", 0.073, 168.23, 0.30, 2.00, 1.8),  # Creamy lactonic — characteristic
    ("benzyl benzoate", 0.062, 212.24, 0.02, 810.0, 0.5),  # Waxy-floral fixative
    ("linoleic acid", 0.048, 280.45, 0.0, 1e6, 0.5),  # Fatty acid (solvent artifact)
    ("delta decalactone", 0.044, 170.25, 0.50, 1.50, 1.8),  # Peachy lactone
    ("oleic acid", 0.031, 282.46, 0.0, 1e6, 0.5),  # Fatty acid (solvent artifact)
    ("methyl salicylate", 0.032, 152.15, 7.00, 10.0, 1.5),  # Sharp wintergreen edge
    ("stearic acid", 0.031, 284.48, 0.0, 1e6, 0.5),  # Fatty acid (solvent artifact)
    ("benzyl salicylate", 0.025, 228.24, 0.01, 50.0, 0.5),  # Floral fixative
    ("germacrene d", 0.021, 204.35, 1.00, 5.00, 1.2),  # Sesquiterpene — green-woody
    ("methyl eugenol", 0.014, 178.23, 2.00, 0.50, 1.5),  # Spicy-clove
    ("isoeugenol", 0.013, 164.20, 1.00, 0.10, 1.5),  # Spicy-phenolic (IFRA restricted)
    ("alpha farnesene", 0.013, 204.35, 0.50, 1.00, 1.2),  # Mild woody-green
    ("ethyl palmitate", 0.009, 284.48, 0.0, 1e6, 0.5),  # Fatty ester (solvent artifact)
    ("linalool", 0.002, 154.25, 21.30, 1.50, 2.0),  # Trace floral
]
# Total identified: 82.6% (volatile odor-active: ~31%, non-volatile carriers: ~52%)
# IFRA note: Tuberose absolute is unrestricted BUT constituents (isoeugenol, methyl eugenol,
# benzyl benzoate, methyl salicylate) have individual IFRA Cat4 limits.

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

# ISO 3520:2022, Table 2 (chromatographic profile of essential oil of
# bergamot, Citrus bergamia Risso et Poit., Calabrian type, whole expressed
# oil). Fractions are the midpoints of the standard's min-max ranges. They
# describe a conforming commercial Calabrian whole oil, not the owned bottle,
# and not a furocoumarin-free (FCF) oil: the standard requires bergaptene
# 0.18-0.38% (HPLC), which FCF processing removes. Inputs reuse this module's
# existing runtime tuples (the same rows the earlier unsourced bergamot FCF
# composite used). beta-Bisabolene (0.3-0.7%) has no runtime headspace input
# and stays unresolved, not odorless. Nothing is renormalized. This replaces an
# unsourced composite (limonene 0.38, linalool 0.15, linalyl acetate 0.28,
# beta-pinene 0.06, geranial 0.005).
_BERGAMOT_ISO_3520_MIDPOINT_CONSTITUENTS = [
    ("limonene", 0.395, 136.24, 200.0, 20.0, 3.0),
    ("linalyl acetate", 0.290, 196.29, 17.50, 2.70, 2.0),
    ("linalool", 0.090, 154.25, 21.30, 1.50, 2.0),
    ("gamma terpinene", 0.080, 136.24, 90.0, 50.0, 3.0),
    ("beta pinene", 0.0625, 136.24, 250.0, 30.0, 3.0),
    ("geranial", 0.00375, 152.23, 3.00, 0.50, 1.5),
]

# ISO 3053:2004, Table 1 (normative chromatographic profile of oil of
# grapefruit, Citrus x paradisi Macfad., obtained by expression). Fractions are
# the midpoints of the standard's min-max ranges. They describe a conforming
# commercial expressed oil, not the owned bottle, and not a furocoumarin-free
# (FCF) oil: ISO 3053 covers whole expressed oil. Inputs reuse this module's
# existing runtime tuples (the nootkatone, octanal, myrcene and limonene rows
# are the ones the earlier unsourced grapefruit composite used). n-Nonanal
# (0.04-0.1%) and n-decanal (0.1-0.6%) have no runtime headspace input and stay
# unresolved, not odorless. Nothing is renormalized. This replaces an unsourced
# composite (limonene 0.65, linalool 0.01) that sat below the standard's 92%
# limonene minimum and listed linalool, which the standard does not profile.
_GRAPEFRUIT_ISO_3053_MIDPOINT_CONSTITUENTS = [
    ("limonene", 0.940, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.020, 136.24, 400.0, 10.0, 3.0),
    ("octanal", 0.005, 128.21, 300.0, 0.50, 2.5),
    ("nootkatone", 0.00405, 218.33, 0.05, 0.01, 1.5),
    ("alpha pinene", 0.004, 136.24, 400.0, 20.0, 3.0),
    ("sabinene", 0.0035, 136.24, 300.0, 30.0, 3.0),
    ("beta caryophyllene", 0.0035, 204.35, 1.00, 10.0, 1.2),
    ("beta pinene", 0.00125, 136.24, 250.0, 30.0, 3.0),
    ("neral", 0.0003, 152.23, 3.0, 0.5, 1.5),
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

# Commercial distilled-key-lime composition from Chisholm et al. (2003),
# Table 1.  The paper's GC-O analysis identifies geranial, neral and linalool
# as the dominant fresh citrus odorants, while also documenting substantial
# batch/process variability.  Only constituents with both quantified commercial
# fractions and established physical/ODT parameters in this model are included;
# unquantified linalool and minor odorants are deliberately omitted rather than
# assigned invented percentages.  The result is a conservative partial composite.
_LIME_DISTILLED_EO_CONSTITUENTS = [
    ("alpha pinene", 0.016, 136.24, 400.0, 20.0, 3.0),
    ("beta pinene", 0.027, 136.24, 250.0, 30.0, 3.0),
    ("myrcene", 0.012, 136.24, 400.0, 10.0, 3.0),
    ("limonene", 0.299, 136.24, 200.0, 20.0, 3.0),
    ("neral", 0.013, 152.23, 3.0, 0.5, 1.5),
    ("geranial", 0.004, 152.23, 3.0, 0.5, 1.5),
    ("alpha terpineol", 0.101, 154.25, 2.0, 10.0, 1.5),
]

# Conservative partial fingerprints. Each retains only quantified constituents
# for which this module has usable headspace physics; omitted fractions remain
# unknown rather than being normalized to 100%.
_ORANGE_PEEL_EO_CONSTITUENTS = [
    ("limonene", 0.945, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.010, 136.24, 400.0, 10.0, 3.0),
    ("linalool", 0.007, 154.25, 21.30, 1.50, 2.0),
    ("octanal", 0.003, 128.21, 300.0, 0.50, 2.5),
]

_LEMON_FCF_EO_CONSTITUENTS = [
    ("limonene", 0.5139, 136.24, 200.0, 20.0, 3.0),
    ("beta pinene", 0.1704, 136.24, 250.0, 30.0, 3.0),
    ("gamma terpinene", 0.1346, 136.24, 90.0, 50.0, 3.0),
]

_NEROLI_EO_CONSTITUENTS = [
    ("limonene", 0.275, 136.24, 200.0, 20.0, 3.0),
    ("alpha terpineol", 0.140, 154.25, 2.00, 10.0, 1.5),
    ("alpha terpinyl acetate", 0.117, 196.29, 2.00, 50.0, 1.5),
]

_GINGER_EO_CONSTITUENTS = [
    ("1,8-cineole", 0.109, 154.25, 200.0, 50.0, 2.0),
    ("linalool", 0.048, 154.25, 21.30, 1.50, 2.0),
    ("borneol", 0.056, 154.25, 3.00, 10.0, 1.5),
    ("alpha terpineol", 0.036, 154.25, 2.00, 10.0, 1.5),
    ("neral", 0.081, 152.23, 3.00, 0.50, 1.5),
    ("geraniol", 0.145, 154.25, 4.00, 2.00, 1.5),
    ("geranial", 0.095, 152.23, 3.00, 0.50, 1.5),
    ("geranyl acetate", 0.063, 196.29, 2.00, 10.0, 1.5),
]

_GALBANUM_EO_CONSTITUENTS = [
    ("alpha pinene", 0.0323, 136.24, 400.0, 20.0, 3.0),
    ("beta pinene", 0.0977, 136.24, 250.0, 30.0, 3.0),
    ("sabinene", 0.1023, 136.24, 300.0, 30.0, 3.0),
    ("terpinen-4-ol", 0.0756, 154.25, 10.0, 50.0, 1.5),
]

_FRANKINCENSE_EO_CONSTITUENTS = [
    ("alpha pinene", 0.3934, 136.24, 400.0, 20.0, 3.0),
    ("beta pinene", 0.0189, 136.24, 250.0, 30.0, 3.0),
    ("myrcene", 0.0174, 136.24, 400.0, 10.0, 3.0),
]

_CLOVE_EO_CONSTITUENTS = [
    ("eugenol", 0.7678, 164.20, 2.50, 0.50, 1.5),
    ("beta caryophyllene", 0.2124, 204.35, 1.00, 10.0, 1.2),
]

_BLACK_PEPPER_EO_CONSTITUENTS = [
    ("beta caryophyllene", 0.3742, 204.35, 1.00, 10.0, 1.2),
    ("limonene", 0.1335, 136.24, 200.0, 20.0, 3.0),
]

# Schinus molle fruit EO — midpoint of the constituent ranges reported for
# Peruvian fruit-oil samples by Huaman et al. (2004). The represented 89.7%
# is intentionally not renormalized, and this is not an Aroma&More batch assay.
# No Schinus-specific GC-O/AEDA study was located in the bounded literature
# review. Phellandrene, p-cymene, and methyl-octanoate VP/ODT/gamma values are
# explicitly modeled class inputs rather than measured lot data.
_SCHINUS_MOLLE_EO_CONSTITUENTS = [
    ("alpha pinene", 0.044, 136.24, 400.0, 20.0, 3.0),
    ("myrcene", 0.342, 136.24, 400.0, 10.0, 3.0),
    ("alpha phellandrene", 0.145, 136.24, 330.0, 20.0, 3.0),
    ("limonene", 0.144, 136.24, 200.0, 20.0, 3.0),
    ("beta phellandrene", 0.087, 136.24, 300.0, 20.0, 3.0),
    ("p cymene", 0.115, 134.22, 240.0, 30.0, 3.0),
    ("methyl octanoate", 0.013, 158.24, 2.0, 10.0, 1.5),
    ("beta caryophyllene", 0.007, 204.35, 1.0, 10.0, 1.2),
]

# Additional high-coverage literature fingerprints.  These profiles retain
# only constituents with established headspace inputs already used elsewhere
# in this module.  Missing constituents (for example p-cymene) are omitted,
# never redistributed across the represented fraction.
_RED_MANDARIN_EO_CONSTITUENTS = [
    ("limonene", 0.807, 136.24, 200.0, 20.0, 3.0),
    ("gamma terpinene", 0.088, 136.24, 90.0, 50.0, 3.0),
    ("myrcene", 0.022, 136.24, 400.0, 10.0, 3.0),
]

_EUCALYPTUS_GLOBULUS_EO_CONSTITUENTS = [
    ("1,8-cineole", 0.631, 154.25, 200.0, 50.0, 2.0),
    ("alpha pinene", 0.073, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.069, 136.24, 200.0, 20.0, 3.0),
    ("gamma terpinene", 0.036, 136.24, 90.0, 50.0, 3.0),
    ("beta pinene", 0.030, 136.24, 250.0, 30.0, 3.0),
    ("myrcene", 0.017, 136.24, 400.0, 10.0, 3.0),
]

_CLARY_SAGE_EO_CONSTITUENTS = [
    ("linalyl acetate", 0.491, 196.29, 17.50, 2.70, 2.0),
    ("linalool", 0.206, 154.25, 21.30, 1.50, 2.0),
    ("beta caryophyllene", 0.051, 204.35, 1.00, 10.0, 1.2),
    ("geranyl acetate", 0.044, 196.29, 2.00, 10.0, 1.5),
    ("alpha pinene", 0.024, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.022, 136.24, 200.0, 20.0, 3.0),
    ("neryl acetate", 0.017, 196.29, 3.00, 10.0, 1.5),
]

# The cited study measured 83.97-90.31% coumarin in solvent extracts.  The
# lower result is used as a conservative proxy for the in-stock tonka absolute;
# it is intentionally resolved through _PROFILE_ALIASES so downstream metadata
# cannot mistake it for a supplier-batch assay of the user's material.
_TONKA_SOLVENT_EXTRACT_PROXY_CONSTITUENTS = [
    ("coumarin", 0.8397, 146.14, 0.05, 2.0, 0.5),
]

# ── Cocoa extracts ───────────────────────────────────────────────────
# No supplier batch GC-MS is available for either in-stock cocoa material.
# These are therefore deliberately conservative, non-normalized lower-bound
# fingerprints, not claims about the exact composition of the user's bottles.
#
# Tuenter et al. (2020), Tables 2-3, quantified the West African cocoa-liquor
# concentrations used below.  The two cocoa-defining Strecker aldehyde mass
# fractions are reconstructed from concentration = OAV * OTV:
#   3-methylbutanal: 109.8 * 5.4 ng/g = 592.92 ng/g
#   2-methylbutanal:  52.5 * 2.2 ng/g = 115.50 ng/g
# The same study measured 2,3,5-trimethylpyrazine at 1.59 microgram/g and
# linalool at 12.8 * 37 ng/g = 473.6 ng/g.  Air-phase aldehyde ODTs are from
# Sakuma et al. (2013).  The trimethylpyrazine ODT of approximately 50 ng/L
# air reported by Liang et al. (2022) converts to approximately 10 ppbv at
# 25 C; its 193 Pa vapor pressure is the RIFM/EPI-Suite 25 C estimate.
_COCOA_ABSOLUTE_CONSTITUENTS = [
    ("3-methylbutanal", 5.9292e-7, 86.13, 6100.0, 0.10, 2.0),
    ("2-methylbutanal", 1.1550e-7, 86.13, 6320.0, 0.18, 2.0),
    ("2,3,5-trimethylpyrazine", 1.5900e-6, 122.17, 193.0, 10.0, 1.2),
    ("linalool", 4.7360e-7, 154.25, 21.30, 1.50, 2.0),
]

# Supercritical CO2 does not reproduce a solvent absolute.  Sanagi et al.
# directly recovered six pyrazines from roasted cocoa with CO2, including
# 2,3,5-trimethylpyrazine.  The perfumery-oriented SFE study by Azila & Aida
# (2013) additionally quantified cocoa hexenal in extract, but no defensible
# air ODT was published, so it is omitted rather than assigned a guessed ODT.
# Until supplier GC-MS is available, retain only the quantified cocoa-liquor
# trimethylpyrazine floor.  The uncharacterized cocoa-butter matrix is inert in
# OAV space, making this numeric result intentionally conservative.
_COCOA_CO2_EXTRACT_CONSTITUENTS = [
    ("2,3,5-trimethylpyrazine", 1.5900e-6, 122.17, 193.0, 10.0, 1.2),
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
    ("khusimone", 0.005, 204.31, 0.002, 0.005, 0.4),
    ("alpha-vetivone", 0.04, 218.33, 0.005, 0.01, 0.5),
    ("beta-vetivone", 0.025, 218.33, 0.005, 0.01, 0.5),
    ("isovalencenol", 0.13, 222.37, 0.01, 2.00, 0.5),
    ("eudesmol", 0.10, 222.37, 0.01, 2.00, 0.5),
    ("nootkatone", 0.01, 218.33, 0.05, 0.01, 1.5),
    ("cedrene", 0.08, 204.35, 3.00, 10.0, 1.2),
]

_CEDARWOOD_EO_CONSTITUENTS = [
    # Setzer & Satyal 2026, Plants 15(4), 659 — 56 commercial J. virginiana
    # wood EO samples at Aromatic Plant Research Center (APRC).
    # Extraction: steam distillation. Character: α-cedrene (OR10J5 receptor,
    # Woo 2017), cis-thujopsene (woody), cedrol (persistent, sedative via GABA).
    ("alpha cedrene", 0.318, 204.35, 3.00, 10.0, 1.2),  # 31.8% ± 3.8%
    ("thujopsene", 0.194, 204.35, 2.00, 5.00, 1.2),  # 19.4% ± 1.5%
    ("cedrol", 0.134, 222.37, 0.001, 2.00, 0.5),  # 13.4% ± 2.2%
    ("widdrol", 0.111, 222.37, 0.005, 1.00, 0.5),  # 11.1% ± 2.5%
    ("beta cedrene", 0.058, 204.35, 2.00, 10.0, 1.2),  # 5.8% ± 0.6%
    ("cuparene", 0.012, 202.34, 0.50, 3.00, 1.0),  # 1.2% ± 0.3%
]
# Total identified: 82.7% — excellent coverage (APRC 56-sample mean)

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

# ── Wave 2: Literature-Verified Constituents (PubChem MW/logP verified) ─

_ROSE_DE_MAI_CONSTITUENTS = [
    # Kovats 1987 (J Chrom), Ohloff 1994 (Scent & Fragrances).
    # Extraction: hexane solvent -> absolute. Major character: citronellol (rosy),
    # geraniol (fresh rose), nerol (green-rose), beta-damascenone (fruity-apple trace).
    ("citronellol", 0.35, 156.26, 2.0, 5.0, 2.0),
    ("geraniol", 0.18, 154.25, 4.0, 2.0, 1.5),
    ("nerol", 0.08, 154.25, 3.0, 2.0, 1.5),
    ("phenylethyl alcohol", 0.04, 122.16, 0.12, 200.0, 0.7),
    ("beta-damascenone", 0.003, 190.28, 0.05, 0.002, 1.5),
    ("linalool", 0.02, 154.25, 21.3, 1.5, 2.0),
]

_JASMINE_ABSOLUTE_CONSTITUENTS = [
    # Kaiser 1988 (Helv Chim Acta), Mookherjee 1989 (Dev Food Sci).
    # Extraction: hexane -> absolute. Major character: benzyl acetate (fruity-jasmine),
    # indole (animalic-fecal at trace), cis-jasmone (green-jasmine).
    ("benzyl acetate", 0.22, 150.17, 20.0, 2.0, 2.0),
    ("benzyl benzoate", 0.16, 212.24, 0.02, 810.0, 0.5),
    ("linalool", 0.075, 154.25, 21.3, 1.5, 2.0),
    ("phytol", 0.08, 296.5, 0.0, 1e6, 0.5),  # Non-volatile terpenoid alcohol
    ("indole", 0.025, 117.15, 1.2, 0.14, 1.8),
    ("cis-jasmone", 0.015, 164.24, 0.5, 1.0, 1.8),
    ("benzyl alcohol", 0.03, 108.14, 8.0, 5.0, 1.5),
    ("methyl jasmonate", 0.01, 224.30, 0.1, 0.2, 1.8),
]

_MIMOSA_ABSOLUTE_CONSTITUENTS = [
    # Demole 1960 (Helv Chim Acta), Kaiser 1993 (The Scent of Orchids).
    # Extraction: hexane -> absolute. Note: 25-35% is long-chain alkanes (non-volatile,
    # contribute no headspace). Key character: methyl anisate (anise-floral).
    ("heptadecane", 0.18, 240.5, 0.0, 1e6, 0.5),
    ("nonadecane", 0.12, 268.5, 0.0, 1e6, 0.5),
    ("palmitic acid", 0.10, 256.42, 0.0, 1e6, 0.5),
    ("benzyl alcohol", 0.04, 108.14, 8.0, 5.0, 1.5),
    ("methyl anisate", 0.025, 166.17, 0.5, 2.0, 1.5),
    ("linalool", 0.02, 154.25, 21.3, 1.5, 2.0),
]

_IMMORTELLE_ABSOLUTE_CONSTITUENTS = [
    # Bianchini 2001 (Flav Fragr J), Mastelic 2008 (Chem Nat Compd).
    # Extraction: hexane -> absolute. Character: neryl acetate (floral-fruity),
    # gamma-curcumene (spicy-woody), italidione (curry-maple character — unique).
    ("neryl acetate", 0.25, 196.29, 3.0, 10.0, 1.5),
    ("gamma-curcumene", 0.10, 204.35, 0.5, 5.0, 1.2),
    ("italidione", 0.06, 218.29, 0.05, 0.5, 1.2),
    ("limonene", 0.04, 136.23, 200.0, 20.0, 3.0),
    ("linalool", 0.03, 154.25, 21.3, 1.5, 2.0),
    ("alpha-pinene", 0.02, 136.23, 400.0, 20.0, 3.0),
]

_VIOLET_LEAF_ABSOLUTE_CONSTITUENTS = [
    # Kaiser 1993, Braun 1998 (Parfum Kosmet). Critical: violet leaf absolute is
    # GREEN-ALDEHYDIC, NOT ionone-floral. trans-2,cis-6-nonadienal is the violet
    # leaf character compound (cucumber-green), NOT beta-ionone.
    # Extraction: hexane -> absolute. 60-70% is non-volatile waxes/pigments.
    ("trans-2,cis-6-nonadienal", 0.01, 138.21, 5.0, 0.001, 2.0),
    ("trans-2-nonenal", 0.005, 140.22, 3.0, 0.005, 2.0),
    ("hexanal", 0.008, 100.16, 1500.0, 4.0, 3.0),
    ("hexanol", 0.04, 102.17, 80.0, 50.0, 2.0),
    ("palmitic acid", 0.15, 256.42, 0.0, 1e6, 0.5),
    ("linolenic acid", 0.10, 278.43, 0.0, 1e6, 0.5),
]

_LABDANUM_ABSOLUTE_CONSTITUENTS = [
    # Weyerstahl 1998 (Flav Fragr J), Baser 2011. Cistus ladaniferus.
    # Extraction: ethanol/hexane -> absolute. Resinoid content ~30-40% non-volatile.
    # Character: alpha-pinene (pine-fresh), bornyl acetate (pine-herbal),
    # labdanolic acid/ambrein (ambergris-like — formed slowly on skin).
    ("alpha-pinene", 0.12, 136.23, 400.0, 20.0, 3.0),
    ("camphene", 0.04, 136.23, 300.0, 50.0, 3.0),
    ("bornyl acetate", 0.03, 196.29, 3.0, 10.0, 1.5),
    ("limonene", 0.03, 136.23, 200.0, 20.0, 3.0),
    ("labdanolic acid", 0.06, 324.5, 0.0, 1e6, 0.5),  # Non-volatile acid
    ("ambrein", 0.008, 428.7, 0.0, 0.01, 0.4),  # Ambregris precursor — extreme persistence
]

_BENZOIN_SIAM_CONSTITUENTS = [
    # Salim 2018, Fernandez 2003. Styrax tonkinensis resinoid.
    # Extraction: ethanol -> resinoid. 40-50% non-volatile resin acids.
    # Character: coniferyl benzoate (balsamic), vanillin (sweet), benzyl benzoate (floral).
    ("coniferyl benzoate", 0.20, 284.31, 0.0, 1e6, 0.4),
    ("benzyl benzoate", 0.15, 212.24, 0.02, 810.0, 0.5),
    ("benzoic acid", 0.12, 122.12, 0.0, 1000.0, 0.4),
    ("vanillin", 0.05, 152.15, 0.005, 0.6, 0.5),
    ("cinnamic acid", 0.06, 148.16, 0.0, 500.0, 0.4),
    ("benzyl alcohol", 0.02, 108.14, 8.0, 5.0, 1.5),
]

# Generic resin-tincture screening proxies. These profiles deliberately retain
# only constituents for which this module already has compatible headspace
# inputs. Fractions are never renormalized, and the user's starting-charge
# stock fraction is applied separately by formula_state.
_TURKISH_STORAX_TINCTURE_GENERIC_CONSTITUENTS = [
    # Liquidambar orientalis Styrax GC-TOF-MS area percentages reported by
    # Wang et al. (2023), doi:10.1093/jpp/rgad093. Major cinnamate esters are
    # omitted because compatible air-ODT inputs are not established here.
    ("cinnamyl alcohol", 0.1117, 134.18, 0.03, 3.0, 0.8),
    ("beta caryophyllene", 0.0247, 204.35, 1.0, 10.0, 1.2),
    ("cinnamaldehyde", 0.0202, 132.16, 3.0, 62.0, 2.0),
]

_VIETNAMESE_BENZOIN_TINCTURE_GENERIC_CONSTITUENTS = list(
    _BENZOIN_SIAM_CONSTITUENTS
)

_KENYAN_MYRRH_TINCTURE_GENERIC_CONSTITUENTS = [
    # Direct ethanol extraction of Commiphora myrrha resin reported 0.13%
    # limonene by GC-MS area (Ahamad et al., 2017). The many identified
    # sesquiterpenoids remain uncomputed because compatible air ODTs are absent.
    ("limonene", 0.0013, 136.24, 200.0, 20.0, 3.0),
]

# Reviews of Boswellia sacra report 5-9% volatile oil in whole gum resin. Use
# the 5% lower bound to scale the existing partial frankincense-oil fingerprint.
# This is a genus-level screening proxy because the user's Oman resin species
# and the actual ethanol recovery of its volatile fraction are unmeasured.
_OMAN_FRANKINCENSE_TINCTURE_GENERIC_CONSTITUENTS = [
    (name, fraction * 0.05, mw, vp, odt, gamma)
    for name, fraction, mw, vp, odt, gamma in _FRANKINCENSE_EO_CONSTITUENTS
]

_TONKA_BEAN_ABSOLUTE_CONSTITUENTS = [
    # Ehlers 1995, Bruneton 1999. Dipteryx odorata absolute.
    # Extraction: ethanol -> absolute. Dominant: coumarin 40-70%.
    # IFRA restricted: coumarin Cat4 limit ~1.6% in finished product (leave-on).
    ("coumarin", 0.55, 146.14, 0.05, 2.0, 0.5),
    ("dihydrocoumarin", 0.02, 148.16, 0.1, 10.0, 0.5),
    ("vanillin", 0.008, 152.15, 0.005, 0.6, 0.5),
    ("o-coumaric acid", 0.03, 164.16, 0.0, 1e6, 0.4),  # Non-volatile acid
]

_VANILLA_ABSOLUTE_CONSTITUENTS = [
    # Bruneton 1999, Sinha 2008. Vanilla planifolia absolute.
    # Extraction: ethanol -> absolute. vanillin content 1-2% in absolute
    # (vs 20% in vanilla extract — absolute is the wax/resin fraction).
    ("vanillin", 0.02, 152.15, 0.005, 0.6, 0.5),
    ("4-hydroxybenzaldehyde", 0.008, 122.12, 0.01, 0.5, 0.5),
    ("vanillic acid", 0.008, 168.15, 0.0, 1e6, 0.4),
    ("guaiacol", 0.002, 124.14, 5.0, 0.01, 1.5),
]

_BLACKCURRANT_ABSOLUTE_CONSTITUENTS = [
    # Rigaud 1986 (Sci Aliments), Frerot 2005 (Flav Fragr J). Ribes nigrum.
    # Extraction: hexane -> absolute. Character: 4-methoxy-2-methyl-2-butanethiol
    # (cat ketone) at 0.02% — extreme odor impact (ODT ~0.00001 ppb).
    # beta-damascenone provides the fruity-apple dimension.
    ("delta-3-carene", 0.08, 136.23, 200.0, 50.0, 3.0),
    ("terpinolene", 0.03, 136.23, 150.0, 30.0, 3.0),
    ("beta-damascenone", 0.002, 190.28, 0.05, 0.002, 1.5),
    ("4-methoxy-2-methyl-2-butanethiol", 0.0002, 134.24, 10.0, 0.00001, 2.0),
    ("palmitic acid", 0.10, 256.42, 0.0, 1e6, 0.5),
]

_COFFEE_ABSOLUTE_GRASSE_CONSTITUENTS = [
    # Quantified volatile subset from supercritical-CO2 coffee oil, expressed
    # as measured mg/kg divided by 1e6. This deliberately remains a partial
    # extraction-profile proxy, not a supplier-batch assay of the Grasse
    # absolute. Constituents lacking compatible air-ODT model inputs are
    # omitted rather than assigned water-threshold values.
    ("furfuryl alcohol", 0.00236302, 98.10, 0.30, 1.0, 0.7),
    ("5-methylfurfural", 0.00021703, 110.11, 15.0, 0.1, 1.2),
    ("furfuryl acetate", 0.00016063, 140.14, 0.50, 0.1, 1.0),
    ("furfural", 0.00007546, 96.08, 100.0, 1.0, 1.5),
]

_CORIANDER_EO_CONSTITUENTS = [
    # Representative GC-MS fingerprint for coriander seed essential oil.
    # The four compatible constituents below account for 79.75% of the
    # measured oil; p-cymene is omitted because this module lacks a compatible
    # evidence-bound air ODT input for it.
    ("linalool", 0.5757, 154.25, 21.3, 1.5, 2.0),
    ("geranyl acetate", 0.1590, 196.29, 5.0, 10.0, 2.0),
    ("beta-caryophyllene", 0.0326, 204.35, 1.5, 10.0, 1.2),
    ("camphor", 0.0302, 152.23, 25.0, 20.0, 2.0),
]

# ── Wave 2: EO Literature-Verified Constituents ──────────────────────────

_LAVENDER_EO_CONSTITUENTS = [
    # Cavanagh 2002 (Phytother Res), Woronuk 2010 (Planta Med).
    # Extraction: steam distillation. Dominant: linalool + linalyl acetate at 50-75%.
    ("linalool", 0.32, 154.25, 21.3, 1.5, 2.0),
    ("linalyl acetate", 0.30, 196.29, 17.5, 2.7, 2.0),
    ("terpinen-4-ol", 0.04, 154.25, 10.0, 5.0, 1.5),
    ("camphor", 0.015, 152.23, 25.0, 20.0, 2.0),
    ("lavandulyl acetate", 0.03, 196.29, 3.0, 5.0, 1.5),
    ("beta-caryophyllene", 0.03, 204.35, 1.5, 10.0, 1.2),
]

_BERGAMOT_EO_CONSTITUENTS = [
    # Dugo 2000 (J Agric Food Chem), Costa 2010 (J Essent Oil Res).
    # Extraction: cold expression (peel). Contains bergaptene 0.3-0.4% — PHOTOTOXIC.
    # IFRA: regular bergamot max 0.4% leave-on. FCF bergamot has bergaptene removed.
    ("limonene", 0.38, 136.23, 200.0, 20.0, 3.0),
    ("linalyl acetate", 0.20, 196.29, 17.5, 2.7, 2.0),
    ("linalool", 0.12, 154.25, 21.3, 1.5, 2.0),
    ("gamma-terpinene", 0.08, 136.23, 90.0, 50.0, 3.0),
    ("beta-pinene", 0.06, 136.23, 300.0, 30.0, 3.0),
    ("bergaptene", 0.0035, 216.19, 0.001, 0.01, 0.5),  # PHOTOTOXIC furanocoumarin
]

_PATCHOULI_EO_CONSTITUENTS = [
    # van Beek 1992 (Flav Fragr J), Donelian 2009 (Perfum Flavor).
    # Extraction: steam distillation. Character: patchoulol (woody-earthy-camphoraceous).
    # Note: patchouli alcohol has anti-inflammatory COX-2 activity (pharmacological).
    ("patchoulol", 0.30, 222.37, 0.005, 0.5, 0.5),
    ("alpha-bulnesene", 0.15, 204.35, 1.0, 5.0, 1.2),
    ("alpha-guaiene", 0.12, 204.35, 1.0, 5.0, 1.2),
    ("seychellene", 0.06, 204.35, 1.0, 5.0, 1.2),
    ("pogostol", 0.03, 222.37, 0.005, 1.0, 0.5),
    ("beta-caryophyllene", 0.03, 204.35, 1.5, 10.0, 1.2),
]

_GERANIUM_EO_CONSTITUENTS = [
    # Boukhatem 2013 (S Afr J Bot), Sharopov 2014 (Med Aromat Pl).
    # Extraction: steam distillation. Pelargonium graveolens.
    # Character: citronellol (rosy-citrus), geraniol (fresh rose), isomenthone (minty-green).
    ("citronellol", 0.28, 156.26, 2.0, 5.0, 2.0),
    ("geraniol", 0.15, 154.25, 4.0, 2.0, 1.5),
    ("linalool", 0.06, 154.25, 21.3, 1.5, 2.0),
    ("citronellyl formate", 0.08, 184.28, 5.0, 10.0, 2.0),
    ("isomenthone", 0.06, 154.25, 10.0, 5.0, 2.0),
    ("beta-caryophyllene", 0.03, 204.35, 1.5, 10.0, 1.2),
]

_YLANG_YLANG_EO_CONSTITUENTS = [
    # Gaydou 1986 (J Agric Food Chem), Stashenko 2008 (J Sep Sci).
    # Extraction: steam distillation. Cananga odorata.
    # Character: benzyl acetate (fruity-floral), p-cresyl methyl ether (medicinal-narcotic).
    ("benzyl acetate", 0.22, 150.17, 20.0, 2.0, 2.0),
    ("linalool", 0.10, 154.25, 21.3, 1.5, 2.0),
    ("germacrene d", 0.08, 204.35, 1.0, 5.0, 1.2),
    ("benzyl benzoate", 0.06, 212.24, 0.02, 810.0, 0.5),
    ("methyl benzoate", 0.05, 136.15, 50.0, 0.5, 2.0),
    ("p-cresyl methyl ether", 0.04, 122.16, 30.0, 1.0, 2.0),
    ("beta-caryophyllene", 0.03, 204.35, 1.5, 10.0, 1.2),
    ("geranyl acetate", 0.02, 196.29, 5.0, 10.0, 2.0),
]

_BLUE_CHAMOMILE_EO_CONSTITUENTS = [
    # Matricaria chamomilla — GC-O constituents from published literature.
    # References: Orav et al. (2008) J. Essent. Oil Res. 20, 6—12;
    # Tolouee et al. (2010) J. Essent. Oil Bear. Pl. 13, 113—120.
    # Extraction: steam distillation.
    # Character: chamazulene (blue pigment, sweet-herbaceous),
    # alpha-bisabolol (sweet floral-herbal, key odorant), bisabolol oxides.
    ("chamazulene", 0.20, 184.28, 0.05, 1.0, 1.2),
    ("alpha-bisabolol", 0.25, 222.37, 0.01, 5.0, 0.7),
    ("bisabolol oxide a", 0.15, 238.37, 0.005, 10.0, 0.7),
    ("bisabolol oxide b", 0.10, 238.37, 0.005, 10.0, 0.7),
    ("trans-beta-farnesene", 0.07, 204.35, 3.0, 5.0, 1.2),
    ("matricin", 0.03, 306.35, 0.0001, 20.0, 0.5),
    ("germacrene d", 0.05, 204.35, 1.0, 8.0, 1.2),
]

_TOBACCO_ABSOLUTE_CONSTITUENTS = [
    # Nicotiana tabacum absolute — GC-O constituents from published literature.
    # References: Mookherjee & Wilson (1988) Perfumer & Flavorist 13, 27-35;
    # Roberts & Acree (1994) J. Agr. Food Chem. 42, 2055-2060.
    # Extraction: solvent extraction of cured tobacco leaves.
    ("beta-damascenone", 0.008, 190.28, 0.50, 0.002, 1.5),
    ("megastigmatrienone a", 0.035, 190.28, 0.30, 0.01, 1.5),
    ("megastigmatrienone b", 0.025, 190.28, 0.30, 0.01, 1.5),
    ("solanone", 0.12, 194.31, 0.50, 2.0, 1.2),
    ("geranyl acetone", 0.05, 194.31, 2.0, 5.0, 2.0),
    ("beta-ionone", 0.03, 192.30, 1.20, 0.10, 1.5),
    ("farnesol", 0.04, 222.37, 0.05, 3.0, 0.6),
    ("phenylacetic acid", 0.02, 136.15, 0.01, 20.0, 0.5),
    ("2-ethyl-3,5-dimethylpyrazine", 0.005, 136.20, 50.0, 0.05, 2.0),
]

_CARROT_SEED_EO_CONSTITUENTS = [
    ("carotol", 0.35, 222.37, 0.01, 5.0, 0.6),
    ("daucene", 0.08, 204.35, 1.0, 8.0, 1.2),
    ("beta-caryophyllene", 0.07, 204.35, 1.5, 10.0, 1.2),
    ("geranyl acetate", 0.04, 196.29, 5.0, 10.0, 2.0),
]

# Partial external-oil profiles. Fractions retain reported peak areas, with no
# normalization. The existing mass-based calculation uses these only as nominal
# composition proxies, not analytically established mass fractions of owned oil.
# Galovicova et al. (2023), Table 1: Hanus Cupressus sempervirens leaf oil.
_CYPRESS_LEAF_LITERATURE_CONSTITUENTS = [
    ("alpha pinene", 0.405, 136.24, 400.0, 20.0, 3.0),
    ("delta-3-carene", 0.244, 136.23, 200.0, 50.0, 3.0),
    ("limonene", 0.043, 136.24, 200.0, 20.0, 3.0),
]
# Dwivedi et al. (2004), Table 2, LK control (var. Kukrail, CIMAP Lucknow).
# p-Menthone is 33.0% of reported area but excluded: compatible air ODT unverified.
# Menthol: C1 log10(1/ODT ppm)=1.660, Abraham et al. (2012), Table 3;
# hence ppb=1000*10**(-1.660). VP is a DL metastable-liquid correlation proxy.
_PEPPERMINT_LK_LITERATURE_CONSTITUENTS = [
    ("menthol", 0.298, 156.2652, 4.5, 1000.0 * 10.0 ** (-1.660), 2.0),
    ("1,8-cineole", 0.065, 154.25, 200.0, 50.0, 2.0),
    ("isomenthone", 0.050, 154.25, 10.0, 5.0, 2.0),
    ("limonene", 0.007, 136.24, 200.0, 20.0, 3.0),
]
# ISO 4719:2012, Table 1 (chromatographic profile of essential oil of spike
# lavender, Lavandula latifolia Medikus, Spanish type). Fractions are the
# midpoints of the standard's min-max ranges; linalyl acetate is "n.d." to 1.6%,
# so its midpoint is 0.8%. They describe a conforming commercial oil, not the
# owned bottle. Inputs reuse this module's existing runtime tuples (the same
# linalool and camphor rows the lavender EO profile uses). trans-alpha-Bisabolene
# (0.4-2.5%) has no runtime headspace input and stays unresolved, not odorless.
# Nothing is renormalized.
_SPIKE_LAVENDER_ISO_4719_MIDPOINT_CONSTITUENTS = [
    ("linalool", 0.420, 154.25, 21.3, 1.5, 2.0),
    ("1,8-cineole", 0.275, 154.25, 200.0, 50.0, 2.0),
    ("camphor", 0.120, 152.23, 25.0, 20.0, 2.0),
    ("limonene", 0.0175, 136.24, 200.0, 20.0, 3.0),
    ("alpha terpineol", 0.011, 154.25, 2.0, 10.0, 1.5),
    ("linalyl acetate", 0.008, 196.29, 17.5, 2.7, 2.0),
]

# PerfumersWorld allergen declaration for Elemi Essential Oil, SKU 7QC00902
# (document list for that SKU; values identical in the 2026-10-07 snapshot and
# the 2026-10-08 page). These are supplier-declared concentrations for the
# product the owner buys, not an analysis of the owned bottle. The declaration
# covers allergens only: elemol, elemicin, alpha-phellandrene, sabinene and
# p-cymene, which published Canarium oils report as major constituents, are not
# quantified for this product and stay unresolved. Carvone and alpha-terpinene
# are declared but have no runtime headspace input. Inputs reuse this module's
# existing runtime tuples. Nothing is renormalized.
_ELEMI_PW_7QC00902_ALLERGEN_DECLARATION_CONSTITUENTS = [
    ("limonene", 0.450869, 136.23, 200.0, 20.0, 3.0),
    ("alpha terpineol", 0.030843, 154.25, 2.0, 10.0, 1.5),
    ("terpinolene", 0.005133, 136.23, 150.0, 30.0, 3.0),
    ("alpha pinene", 0.003888, 136.24, 400.0, 20.0, 3.0),
    ("methyl eugenol", 0.003068, 178.23, 2.0, 0.5, 1.5),
    ("gamma terpinene", 0.000507, 136.24, 90.0, 50.0, 3.0),
    ("geranial", 0.000359, 152.23, 3.0, 0.5, 1.5),
    ("camphor", 0.000334, 152.23, 25.0, 20.0, 2.0),
]

# ISO 3215:1998, Table 1 (normative chromatographic profile of oil of nutmeg,
# Indonesian type, Myristica fragrans Houtt.). Fractions are the midpoints of
# the standard's min-max ranges. They describe a conforming commercial oil, not
# the owned bottle: Aroma&More sells Indonesian seed oil it calls East Indian
# type but publishes no composition and claims no ISO conformity. Inputs reuse
# this module's existing runtime tuples. Safrole (1.0-2.5%) and myristicin
# (5-12%) have no runtime headspace inputs and stay unresolved, not odorless.
# Nothing is renormalized.
_NUTMEG_INDONESIAN_ISO_3215_MIDPOINT_CONSTITUENTS = [
    ("alpha pinene", 0.215, 136.24, 400.0, 20.0, 3.0),
    ("sabinene", 0.215, 136.24, 300.0, 30.0, 3.0),
    ("beta pinene", 0.155, 136.24, 250.0, 30.0, 3.0),
    ("limonene", 0.045, 136.23, 200.0, 20.0, 3.0),
    ("gamma terpinene", 0.040, 136.24, 90.0, 50.0, 3.0),
    ("terpinen-4-ol", 0.040, 154.25, 10.0, 50.0, 1.5),
    ("delta-3-carene", 0.0125, 136.23, 200.0, 50.0, 3.0),
]
# ISO 8896:2016, Table 1 (chromatographic profile of essential oil of
# caraway, Carum carvi L., dried ripe fruit, steam distilled). Fractions are the
# midpoints of the standard's min-max ranges; trans-carveol is "traces"
# (<0.01%) to 0.5%, so its lower bound is taken as 0 (midpoint 0.25%). They
# describe a conforming commercial oil, not the owned bottle, which is not
# certified to the standard. Inputs reuse this module's existing runtime tuples.
# Carvone (50-63%), cis-dihydrocarvone, trans-carveol and cis-carveol have no
# runtime headspace input and stay unresolved, not odorless: the character
# constituent is therefore not modeled. Nothing is renormalized.
_CARAWAY_ISO_8896_MIDPOINT_CONSTITUENTS = [
    ("limonene", 0.390, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.0045, 136.24, 400.0, 10.0, 3.0),
]

# -- Proxy profiles for owned naturals without a lot analysis (2026-10-09) --
# Each profile is a labelled literature or supplier proxy, not an analysis of
# the owned bottle. Inputs reuse this module's existing runtime tuples where the
# constituent is modeled elsewhere. Constituents without a runtime headspace
# input stay unresolved, not odorless. Nothing is renormalized.

# Cinnamon bark (not leaf) oil. Supplier certificate of analysis, amrita.net
# CoA EO3231-CBBL, "Cinnamon Bark Organic, Sri Lanka" (Cinnamomum zeylanicum),
# GC-FID on DB-5, produced 2022-03-22; it lists only five constituents summing
# to 96.37%. The owned Telvada lot has no published composition, species or
# origin. Cinnamaldehyde reuses the ODT_DATA-consistent air ODT (62 ppb,
# engine/odor_thresholds.py) that the storax row uses. (E)-Cinnamyl acetate
# (4.02%) has no runtime headspace input and stays unresolved. Leaf-oil
# profiles (eugenol-dominant) are non-equivalent and are not used.
_CINNAMON_BARK_SRI_LANKA_COA_CONSTITUENTS = [
    ("cinnamaldehyde", 0.7971, 132.16, 3.0, 62.0, 2.0),
    ("eugenol", 0.0600, 164.20, 2.50, 0.50, 1.5),
    ("linalool", 0.0486, 154.25, 21.3, 1.5, 2.0),
    ("beta caryophyllene", 0.0178, 204.35, 1.0, 10.0, 1.2),
]

# Lavandin (Lavandula x intermedia) supercritical-CO2 extract, Pellerin,
# Perfumer & Flavorist 16(4):37 (1991), as tabulated by The Good Scents Company
# (thegoodscentscompany.com/gca/gc1045781.html) under "lavandin absolute".
# 57.3% of the extract is listed; 42.7% is an unknown remainder. A CO2 extract
# is not a solvent-extracted absolute. Herniarin (2.6%) has no runtime input,
# and beta-caryophyllene + alpha-humulene (2.4%) is reported only as a sum with
# no split; both stay unresolved.
_LAVANDIN_CO2_PELLERIN_1991_CONSTITUENTS = [
    ("linalyl acetate", 0.284, 196.29, 17.5, 2.7, 2.0),
    ("linalool", 0.101, 154.25, 21.3, 1.5, 2.0),
    ("coumarin", 0.077, 146.14, 0.05, 2.0, 0.5),
    ("lavandulyl acetate", 0.018, 196.29, 3.0, 5.0, 1.5),
    ("camphor", 0.017, 152.23, 25.0, 20.0, 2.0),
    ("borneol", 0.015, 154.25, 3.00, 10.0, 1.5),
    ("terpinen-4-ol", 0.011, 154.25, 10.0, 50.0, 1.5),
]

# Ambrette (Abelmoschus moschatus) seed OIL, GC-MS area %, NIST library IDs,
# Arokiyaraj et al., Molecules 2015, 20:384 (PMC6272330), Table 1. This is a
# seed oil, not the owned absolute. The reported "ambrettolide" peak is a NIST
# library ID and may be (Z)-hexadec-7-en-16-olide or a related isomer; it uses
# the data-spine MW 252.4 and VP 0.003 Pa (an uncited engine estimate) with
# the ODT_DATA air ODT 0.136 ppb (Kraft 2005); gamma 0.5 is the macrocyclic
# musk class input. Farnesyl acetate (51.45%), the alkyl acetates and the
# alkenyl acetates have no runtime headspace input and stay unresolved.
# Linoleic acid is a non-volatile mass row, as in the tuberose profile.
_AMBRETTE_SEED_OIL_AROKIYARAJ_2015_CONSTITUENTS = [
    ("ambrettolide", 0.1296, 252.4, 0.003, 0.136, 0.5),
    ("farnesol", 0.0266, 222.37, 0.05, 3.00, 0.6),
    ("alpha guaiene", 0.0116, 204.35, 1.00, 3.00, 1.2),
    ("linoleic acid", 0.0203, 280.45, 0.0, 1e6, 0.5),
]

# Orris concrete / butter (Iris pallida or I. germanica rhizome). Supplier
# grade labels "ORRIS CONCRETE 8% IRONE" and "15% IRONE" exist
# (thegoodscentscompany.com/data/co1001091.html); the owned PerfumersWorld
# grade's irone content is unknown, so the conservative low grade (8% total
# irones) is modeled with the module's existing orris irone-pool input.
# Myristic acid is the midpoint of the 60-85% range (Premiere Peau glossary)
# and is a non-volatile mass row, as the palmitic acid rows are.
_ORRIS_CONCRETE_8PCT_IRONE_CONSTITUENTS = [
    ("irone pool (alpha-equivalent)", 0.08, 206.32, 0.559, 0.9, 1.3),
    ("myristic acid", 0.725, 228.38, 0.0, 1e6, 0.5),
]

# ── Master Registry ───────────────────────────────────────────────────

_ABSOLUTE_CONSTITUENTS = {
    # Flower absolutes
    "osmanthus absolute": _OSMANTHUS_CONSTITUENTS,
    "osmanthus absolute (volume grade)": _OSMANTHUS_VOLUME_GRADE_CONSTITUENTS,
    "orris liquid": _ORRIS_LIQUID_CONSTITUENTS,
    "orris liquid (30%)": _ORRIS_LIQUID_CONSTITUENTS,
    "rose de mai absolute": _ROSE_DE_MAI_CONSTITUENTS,
    "jasmine sambac": _JASMINE_SAMBAC_CONSTITUENTS,
    "jasmine sambac (10% in dpg)": _JASMINE_SAMBAC_CONSTITUENTS,
    "jasmine absolute": _JASMINE_ABSOLUTE_CONSTITUENTS,
    "tuberose absolute": _TUBEROSE_CONSTITUENTS,
    "tuberose absolute (india)": _TUBEROSE_CONSTITUENTS,
    "immortelle absolute": _IMMORTELLE_ABSOLUTE_CONSTITUENTS,
    "mimosa absolute": _MIMOSA_ABSOLUTE_CONSTITUENTS,
    "violet leaf absolute": _VIOLET_LEAF_ABSOLUTE_CONSTITUENTS,
    "ylang ylang eo (extra grade)": _YLANG_YLANG_EO_CONSTITUENTS,
    "ylang comoros complete eo f3255": _YLANG_YLANG_EO_CONSTITUENTS,
    "ylang comoros iii eo f3295": _YLANG_YLANG_EO_CONSTITUENTS,
    # Citrus EOs
    "citrus bergamia calabrian type iso 3520 midpoint profile": (
        _BERGAMOT_ISO_3520_MIDPOINT_CONSTITUENTS
    ),
    "bergamot essential oil": _BERGAMOT_EO_CONSTITUENTS,
    "citrus paradisi expressed oil iso 3053 midpoint profile": (
        _GRAPEFRUIT_ISO_3053_MIDPOINT_CONSTITUENTS
    ),
    "cedrat fcf sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "cedrat fcf oil sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "petitgrain eo paraguay": _PETITGRAIN_EO_CONSTITUENTS,
    "lime distilled eo": _LIME_DISTILLED_EO_CONSTITUENTS,
    "orange peel eo": _ORANGE_PEEL_EO_CONSTITUENTS,
    "lemon fcf oil sicilian": _LEMON_FCF_EO_CONSTITUENTS,
    "neroli eo": _NEROLI_EO_CONSTITUENTS,
    "ginger eo": _GINGER_EO_CONSTITUENTS,
    "red mandarin eo": _RED_MANDARIN_EO_CONSTITUENTS,
    "eucalyptus essential oil": _EUCALYPTUS_GLOBULUS_EO_CONSTITUENTS,
    # Cocoa extracts (keep the neat absolute and CO2 stock distinct)
    "cocoa absolute": _COCOA_ABSOLUTE_CONSTITUENTS,
    "cocoa co2 extract": _COCOA_CO2_EXTRACT_CONSTITUENTS,
    # Resinoids / Base naturals
    "oakmoss absolute": _OAKMOSS_ABSOLUTE_CONSTITUENTS,
    "oakmoss absolute (10% in dpg)": _OAKMOSS_ABSOLUTE_CONSTITUENTS,
    "patchouli eo": _PATCHOULI_EO_CONSTITUENTS,
    "labdanum": _LABDANUM_RESINOID_CONSTITUENTS,
    "labdanum resinoid": _LABDANUM_RESINOID_CONSTITUENTS,
    "labdanum resinoid (10% in dpg)": _LABDANUM_RESINOID_CONSTITUENTS,
    "labdanum absolute": _LABDANUM_ABSOLUTE_CONSTITUENTS,
    "benzoin resinoid": _BENZOIN_RESINOID_CONSTITUENTS,
    "benzoin resinoid (50% in dpg)": _BENZOIN_RESINOID_CONSTITUENTS,
    "benzoin siam resinoid": _BENZOIN_SIAM_CONSTITUENTS,
    "benzoin sumatra resinoid": _BENZOIN_SIAM_CONSTITUENTS,
    "liquidambar orientalis resin ethanol tincture generic profile": (
        _TURKISH_STORAX_TINCTURE_GENERIC_CONSTITUENTS
    ),
    "styrax tonkinensis resin ethanol tincture generic profile": (
        _VIETNAMESE_BENZOIN_TINCTURE_GENERIC_CONSTITUENTS
    ),
    "commiphora myrrha resin ethanol tincture generic profile": (
        _KENYAN_MYRRH_TINCTURE_GENERIC_CONSTITUENTS
    ),
    "oman boswellia resin ethanol tincture generic profile": (
        _OMAN_FRANKINCENSE_TINCTURE_GENERIC_CONSTITUENTS
    ),
    "tonka bean absolute": _TONKA_BEAN_ABSOLUTE_CONSTITUENTS,
    "vanilla absolute": _VANILLA_ABSOLUTE_CONSTITUENTS,
    "blackcurrant absolute": _BLACKCURRANT_ABSOLUTE_CONSTITUENTS,
    "roasted coffee oil literature profile": _COFFEE_ABSOLUTE_GRASSE_CONSTITUENTS,
    "olibanum resinoid": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid (viscous)": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid (viscous, 3 g)": _OLIBANUM_RESINOID_CONSTITUENTS,
    "olibanum resinoid absolute": _OLIBANUM_RESINOID_CONSTITUENTS,
    "vetiver eo (india)": _VETIVER_EO_CONSTITUENTS,
    "vetiver eo": _VETIVER_EO_CONSTITUENTS,
    "cedarwood eo": _CEDARWOOD_EO_CONSTITUENTS,
    "nagarmortha oil": _NAGARMOTHA_CONSTITUENTS,
    "nagar motha oil": _NAGARMOTHA_CONSTITUENTS,
    "galbanum eo": _GALBANUM_EO_CONSTITUENTS,
    "frankincense eo": _FRANKINCENSE_EO_CONSTITUENTS,
    # Other EOs
    "lavender eo (bontaux sas)": _LAVENDER_EO_CONSTITUENTS,
    "lavender eo": _LAVENDER_EO_CONSTITUENTS,
    "lavender eo high altitude": _LAVENDER_EO_CONSTITUENTS,
    "cardamom eo": _CARDAMOM_EO_CONSTITUENTS,
    "geranium flower eo": _GERANIUM_EO_CONSTITUENTS,
    "juniper berry eo": _JUNIPER_BERRY_EO_CONSTITUENTS,
    "rosemary eo": _ROSEMARY_EO_CONSTITUENTS,
    "rosemary eo (french rosmarinus officinalis leaf oil)": _ROSEMARY_EO_CONSTITUENTS,
    "geranium eo": _GERANIUM_EO_CONSTITUENTS,
    "clove eo": _CLOVE_EO_CONSTITUENTS,
    "black pepper eo": _BLACK_PEPPER_EO_CONSTITUENTS,
    "pink pepper eo": _SCHINUS_MOLLE_EO_CONSTITUENTS,
    "clary sage eo": _CLARY_SAGE_EO_CONSTITUENTS,
    "blue chamomile eo": _BLUE_CHAMOMILE_EO_CONSTITUENTS,
    "tobacco absolute": _TOBACCO_ABSOLUTE_CONSTITUENTS,
    "carrot seed eo": _CARROT_SEED_EO_CONSTITUENTS,
    "coriander essential oil": _CORIANDER_EO_CONSTITUENTS,
    # Literature-only proxy identities (not supplier-batch identities).
    "cupressus sempervirens leaf oil literature profile": _CYPRESS_LEAF_LITERATURE_CONSTITUENTS,
    "mentha piperita lk literature profile": _PEPPERMINT_LK_LITERATURE_CONSTITUENTS,
    "lavandula latifolia spanish type iso 4719 midpoint profile": (
        _SPIKE_LAVENDER_ISO_4719_MIDPOINT_CONSTITUENTS
    ),
    "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile": (
        _ELEMI_PW_7QC00902_ALLERGEN_DECLARATION_CONSTITUENTS
    ),
    "myristica fragrans indonesian type iso 3215 midpoint profile": (
        _NUTMEG_INDONESIAN_ISO_3215_MIDPOINT_CONSTITUENTS
    ),
    "carum carvi fruit oil iso 8896 midpoint profile": _CARAWAY_ISO_8896_MIDPOINT_CONSTITUENTS,
    "cinnamomum zeylanicum bark oil sri lanka supplier coa profile": (
        _CINNAMON_BARK_SRI_LANKA_COA_CONSTITUENTS
    ),
    "lavandula x intermedia supercritical co2 extract pellerin 1991 profile": (
        _LAVANDIN_CO2_PELLERIN_1991_CONSTITUENTS
    ),
    "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile": (
        _AMBRETTE_SEED_OIL_AROKIYARAJ_2015_CONSTITUENTS
    ),
    "iris rhizome concrete 8 pct irone low grade scenario profile": (
        _ORRIS_CONCRETE_8PCT_IRONE_CONSTITUENTS
    ),
    "tonka bean solvent extract literature profile": _TONKA_SOLVENT_EXTRACT_PROXY_CONSTITUENTS,
    # Specialty bases
    "cassis base 345b": _CASSIS_BASE_345B_CONSTITUENTS,
    # New EOs 2026-06-15
    "rose essential oil": _ROSE_EO_CONSTITUENTS,
    "cassia essential oil": _CASSIA_EO_CONSTITUENTS,
}


_PROFILE_ALIASES = {
    # Volatile headspace proxies with the same botanical material or a stated
    # close extraction/grade variant. Metadata marks every proxy explicitly.
    # Calabrian whole-oil ISO profile used as a labelled proxy for Sicilian FCF
    # bergamot oil (and for the unqualified bergamot EO label it already served).
    "bergamot fcf": "citrus bergamia calabrian type iso 3520 midpoint profile",
    "bergamot fcf sicilian": "citrus bergamia calabrian type iso 3520 midpoint profile",
    # Expressed-oil ISO profile used as a labelled proxy for FCF grapefruit oil.
    "grapefruit fcf": "citrus paradisi expressed oil iso 3053 midpoint profile",
    "grapefruit fcf oil sicilian": "citrus paradisi expressed oil iso 3053 midpoint profile",
    # The canonical registry identity still uses a non-lot literature profile.
    # Preserve that authority label after name normalization resolves seed EO.
    "coriander essential oil": "coriander essential oil",
    "coriander seed eo": "coriander essential oil",
    "bergamot eo": "citrus bergamia calabrian type iso 3520 midpoint profile",
    "blood orange sicilian": "orange peel eo",
    "ylang": "ylang ylang eo (extra grade)",
    "cedarwood virginia": "cedarwood eo",
    "benzoin sumatra resinoid": "benzoin resinoid",
    "lavender eo high altitude": "lavender eo",
    "geranium eo (pelargonium graveolens flower oil)": "geranium eo",
    "galbanum resinoid": "galbanum eo",
    "tonka bean absolute": "tonka bean solvent extract literature profile",
    "coffee absolute grasse": "roasted coffee oil literature profile",
    "cypress eo": "cupressus sempervirens leaf oil literature profile",
    "cypress essential oil": "cupressus sempervirens leaf oil literature profile",
    "peppermint essential oil": "mentha piperita lk literature profile",
    "spike lavender eo": "lavandula latifolia spanish type iso 4719 midpoint profile",
    "spike lavender": "lavandula latifolia spanish type iso 4719 midpoint profile",
    "elemi eo": "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile",
    "elemi essential oil": "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile",
    # Aroma&More "Nutmeg Essential oil, Indonesia" (ref NutId0612B): seed oil,
    # East Indian type per the supplier. Mace (aril) oil is not mapped.
    "nutmeg eo": "myristica fragrans indonesian type iso 3215 midpoint profile",
    "nutmeg essential oil": "myristica fragrans indonesian type iso 3215 midpoint profile",
    # Owner stock "Caraway Seed Oil (10% w/w in DPG)": Carum carvi seed oil.
    "caraway seed eo": "carum carvi fruit oil iso 8896 midpoint profile",
    "caraway seed oil (10% w/w in dpg)": "carum carvi fruit oil iso 8896 midpoint profile",
    # Owner stock "Cinnamon Bark EO - Telvada USDA Organic (neat)": bark oil,
    # lot species and origin unknown. Leaf oil is not mapped.
    "cinnamon bark eo": "cinnamomum zeylanicum bark oil sri lanka supplier coa profile",
    "cinnamon bark eo - telvada usda organic": (
        "cinnamomum zeylanicum bark oil sri lanka supplier coa profile"
    ),
    # Owner stock "Lavandin Absolute (neat / as supplied)", PerfumersWorld 8HY00554.
    "lavandin absolute": "lavandula x intermedia supercritical co2 extract pellerin 1991 profile",
    "lavandin absolute (neat / as supplied)": (
        "lavandula x intermedia supercritical co2 extract pellerin 1991 profile"
    ),
    # Owner stock "Ambrette Seed Absolute (10% in DPG)", PerfumersWorld 5XU12235.
    "ambrette seed absolute": "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile",
    "ambrette seed absolute (10% in dpg)": (
        "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile"
    ),
    # Owner stock "Orris Concrete Orris Butter (10% in DPG)", PerfumersWorld
    # 5IA07847; distinct from Orris Liquid 8IQ24653.
    "orris concrete orris butter": "iris rhizome concrete 8 pct irone low grade scenario profile",
    "orris concrete orris butter (10% in dpg)": (
        "iris rhizome concrete 8 pct irone low grade scenario profile"
    ),
    # Owner stock "Siam Benzoin (50% w/w in DPG)": same Styrax tonkinensis
    # resinoid identity as the existing Siam benzoin profile.
    "siam benzoin": "benzoin siam resinoid",
    "siam benzoin (50% w/w in dpg)": "benzoin siam resinoid",
    # Aroma&More SKU Lav420811P: sold as French Lavandula angustifolia oil.
    # It reuses the generic L. angustifolia profile as a labelled proxy.
    "lavender 40/42, aroma&more": "lavender eo",
    "lavender 40/42": "lavender eo",
    "olibanum": "olibanum resinoid",
    "turkish storax tincture": (
        "liquidambar orientalis resin ethanol tincture generic profile"
    ),
    "turkish storax": (
        "liquidambar orientalis resin ethanol tincture generic profile"
    ),
    "turkish storax liquidambar orientalis resin ethanol tincture": (
        "liquidambar orientalis resin ethanol tincture generic profile"
    ),
    "vietnamese benzoin tincture": (
        "styrax tonkinensis resin ethanol tincture generic profile"
    ),
    "benzoin styrax tonkinensis tincture": (
        "styrax tonkinensis resin ethanol tincture generic profile"
    ),
    "vietnamese benzoin styrax tonkinensis resin ethanol tincture": (
        "styrax tonkinensis resin ethanol tincture generic profile"
    ),
    "kenyan myrrh ethanol tincture": (
        "commiphora myrrha resin ethanol tincture generic profile"
    ),
    "kenyan myrrh resin ethanol tincture": (
        "commiphora myrrha resin ethanol tincture generic profile"
    ),
    "oman frankincense ethanol tincture": (
        "oman boswellia resin ethanol tincture generic profile"
    ),
    "oman frankincense resin ethanol tincture": (
        "oman boswellia resin ethanol tincture generic profile"
    ),
}

_LAVENDER_40_42_PROXY_LIMITATIONS = (
    "Aroma&More SKU Lav420811P (https://aromaandmore.com/en/essential-oil-100-pure-/67-11388-lavender-4042-essential-oil-france.html) "
    "is sold as French steam-distilled Lavandula angustifolia flower oil standardized toward a 40/42 "
    "linalool and linalyl acetate target.",
    "The supplier states the current product does not fully meet that target and that lavandin or another "
    "lavender can be added at production; any such admixture is not represented here.",
    "The reused generic L. angustifolia literature profile is not an analysis of that product or lot; "
    "no supplier GC, certificate of analysis, or density was located.",
)

_BERGAMOT_FCF_PROXY_LIMITATIONS = (
    "The owned oil is Sicilian furocoumarin-free bergamot; ISO 3520:2022 describes Calabrian whole "
    "expressed oil, which must contain bergaptene 0.18-0.38%. FCF processing removes bergaptene "
    "(bergapten) and can shift the volatile profile.",
    "The reused composition is the ISO 3520 range midpoint profile, not an analysis of the owned "
    "product or lot.",
    "This headspace proxy supplies no furocoumarin assay or skin-safety clearance.",
)

_PROFILE_PROXY_LIMITATIONS: dict[str, tuple[str, ...]] = {
    "bergamot fcf sicilian": _BERGAMOT_FCF_PROXY_LIMITATIONS,
    "bergamot fcf": _BERGAMOT_FCF_PROXY_LIMITATIONS,
    "lavender 40/42, aroma&more": _LAVENDER_40_42_PROXY_LIMITATIONS,
    "lavender 40/42": _LAVENDER_40_42_PROXY_LIMITATIONS,
    "grapefruit fcf oil sicilian": (
        "PerfumersWorld identifies SKU 7CA24030 as Sicilian furocoumarin-free grapefruit oil; "
        "the reused composition is the ISO 3053:2004 expressed-oil range midpoint profile, "
        "not an analysis of that supplier product or lot.",
        "The PerfumersWorld SDS CAS 68917-32-8 is the grapefruit-terpenes CAS (whole expressed oil is "
        "8016-20-4); it is not used as identity evidence.",
        "This headspace proxy supplies no furocoumarin assay or skin-safety clearance.",
    ),
    "coriander seed eo": (
        "PerfumersWorld SKU 7SL00125 identifies coriander seed oil; the reused published "
        "seed-oil fingerprint is not a supplier-product or lot assay and does not cover leaf oil.",
    ),
    "galbanum resinoid": (
        "Composition source is galbanum essential oil, not the in-stock resinoid extraction.",
    ),
    "tonka bean absolute": (
        "Composition source is a published solvent-extract range, not a supplier-batch assay of the in-stock absolute.",
    ),
    "coffee absolute grasse": (
        "Composition source is a quantified supercritical-CO2 coffee-oil volatile subset, not the supplier-batch Grasse absolute.",
        "Only constituents with compatible air-ODT model inputs are included.",
    ),
    "pink pepper eo": (
        "Composition is the midpoint of published Peruvian Schinus molle fruit-EO ranges, not an Aroma&More lot GC-MS or GC-O assay.",
        "No Schinus-specific GC-O/AEDA profile was located; phellandrene, p-cymene, and methyl-octanoate VP/ODT inputs are modeled by class.",
        "Plant part, origin, extraction, oxidation state, density, and current leave-on IFRA conformity for the user's bottle remain unverified.",
    ),
}


_PROFILE_KEY_LIMITATIONS: dict[str, tuple[str, ...]] = {
    "liquidambar orientalis resin ethanol tincture generic profile": (
        "Generic published Liquidambar orientalis Styrax composition, not an analysis of the user's Turkish tincture or resin lot.",
        "GC-TOF-MS area percentages are nominal model fractions, not measured mass fractions in the final filtrate.",
        "Only 15.66% of reported chromatographic area has compatible headspace inputs; major cinnamate esters remain uncomputed, not odorless.",
        "The user's 20% starting charge scales the screen but is not an assay of ethanol extraction recovery.",
    ),
    "styrax tonkinensis resin ethanol tincture generic profile": (
        "Generic Siam benzoin literature profile for Styrax tonkinensis, not an analysis of the user's Vietnamese resin lot or tincture.",
        "The existing resin/resinoid fingerprint is reused as a tincture screening proxy; extraction recovery and final dissolved-solids fraction remain unmeasured.",
        "The user's 40% starting charge scales the screen but does not establish exact active mass in the filtrate.",
    ),
    "commiphora myrrha resin ethanol tincture generic profile": (
        "Generic Arabian Commiphora myrrha ethanol-extract composition, not an analysis of the user's Kenya-origin resin lot.",
        "The exact botanical normalization of the user's Commiphora label remains unresolved.",
        "Only the reported 0.13% limonene area has compatible headspace inputs; all other reported extract constituents remain uncomputed, not odorless.",
        "The user's 20% starting charge scales the screen but is not an assay of ethanol extraction recovery.",
    ),
    "oman boswellia resin ethanol tincture generic profile": (
        "Generic Boswellia resin proxy; the botanical species of the user's Oman frankincense remains unresolved.",
        "The profile scales a partial frankincense-oil fingerprint by the published 5% lower bound for volatile oil in whole resin; it is not a measurement of ethanol recovery.",
        "Only 2.1485% of resin mass is represented by modeled volatile constituents; the remaining odor contribution is uncomputed, not zero.",
        "The user's 33% starting charge scales the screen but does not establish exact active mass in the filtrate.",
    ),
}


_PROFILE_SOURCES: dict[str, tuple[str, ...]] = {
    "liquidambar orientalis resin ethanol tincture generic profile": (
        "https://doi.org/10.1093/jpp/rgad093",
    ),
    "styrax tonkinensis resin ethanol tincture generic profile": (
        "https://doi.org/10.1016/j.foodchem.2016.05.015",
        "https://doi.org/10.1002/pca.1048",
    ),
    "commiphora myrrha resin ethanol tincture generic profile": (
        "https://doi.org/10.1016/j.jsps.2016.10.011",
    ),
    "oman boswellia resin ethanol tincture generic profile": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8881160/",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10603989/",
    ),
    "cupressus sempervirens leaf oil literature profile": (
        "https://doi.org/10.3390/plants12051097",
        "https://aromaandmore.com/en/essential-oil-100-pure-/42-cypress-essential-oil-france.html",
    ),
    "mentha piperita lk literature profile": (
        "https://doi.org/10.1002/ffj.1333",
        "https://doi.org/10.1093/chemse/bjr094",
        "https://doi.org/10.1016/0031-9384(90)90217-R",
        "https://trc.nist.gov/ThermoML/10.1016/j.jct.2016.11.027.html",
        "https://webbook.nist.gov/cgi/cbook.cgi?ID=2216-51-5",
    ),
    "orange peel eo": ("https://pubmed.ncbi.nlm.nih.gov/12862384/",),
    "lemon fcf oil sicilian": ("https://pubmed.ncbi.nlm.nih.gov/28231199/",),
    "neroli eo": ("https://pubmed.ncbi.nlm.nih.gov/24163946/",),
    "ginger eo": ("https://pubmed.ncbi.nlm.nih.gov/21366054/",),
    "galbanum eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10474915/",),
    "frankincense eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10603989/",),
    "clove eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10058340/",),
    "black pepper eo": ("https://pubmed.ncbi.nlm.nih.gov/41245190/",),
    "red mandarin eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10985240/",),
    "eucalyptus essential oil": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10004840/",),
    "clary sage eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10049179/",),
    "tonka bean solvent extract literature profile": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12840717/",
    ),
    "roasted coffee oil literature profile": (
        "https://doi.org/10.3390/foods12132515",
    ),
    "coriander essential oil": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC3512302/",
    ),
    "pink pepper eo": (
        "https://doi.org/10.1080/0972060X.2004.10643396",
    ),
    "lavandula latifolia spanish type iso 4719 midpoint profile": (
        "https://www.iso.org/standard/55964.html",
    ),
    "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=7QC00902",
        "https://www.perfumersworld.com/view.php?pro_id=7QC00902",
    ),
    "myristica fragrans indonesian type iso 3215 midpoint profile": (
        "https://www.iso.org/standard/8418.html",
        "https://cdn.standards.iteh.ai/samples/8418/25f1579e1e374221b2ca9c0dfd38a3af/ISO-3215-1998.pdf",
    ),
    "carum carvi fruit oil iso 8896 midpoint profile": (
        "https://www.iso.org/standard/66253.html",
        "https://cdn.standards.iteh.ai/samples/66253/ec9d0977d3e24e3a85813e08ef968e27/ISO-8896-2016.pdf",
    ),
    "cinnamomum zeylanicum bark oil sri lanka supplier coa profile": (
        "amrita.net certificate of analysis EO3231-CBBL, Cinnamon Bark Organic, Sri Lanka (2022-03-22)",
    ),
    "lavandula x intermedia supercritical co2 extract pellerin 1991 profile": (
        "https://www.thegoodscentscompany.com/gca/gc1045781.html",
        "Pellerin P. (1991) Perfumer & Flavorist 16(4):37",
    ),
    "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6272330/",
        "https://thegoodscentscompany.com/data/ab1029391.html",
    ),
    "iris rhizome concrete 8 pct irone low grade scenario profile": (
        "https://thegoodscentscompany.com/data/co1001091.html",
        "https://premierepeau.com/pages/glossary-terms/orris-concrete",
        "https://www.perfumersworld.com/view.php?pro_id=8IA00344",
    ),
    "citrus bergamia calabrian type iso 3520 midpoint profile": (
        "https://www.iso.org/standard/81602.html",
        "https://cdn.standards.iteh.ai/samples/81602/2b45583f486b4ae29289d765e8a46f9c/ISO-3520-2022.pdf",
    ),
    "citrus paradisi expressed oil iso 3053 midpoint profile": (
        "https://www.iso.org/standard/32040.html",
        "https://cdn.standards.iteh.ai/samples/32040/5decda805f4f4d28af4cdb41a472155b/ISO-3053-2004.pdf",
    ),
}


# Per-input authority for the new partial profiles. Reused tuples retain their
# existing model values and are not promoted to independently verified data.
_LEGACY_CONSTITUENT_INPUT_AUTHORITY = {
    "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
    "odt_status": "LEGACY_RUNTIME_ESTIMATE_NOT_INDEPENDENTLY_VERIFIED",
    "vp_status": "LEGACY_RUNTIME_ESTIMATE_NOT_INDEPENDENTLY_VERIFIED",
    "gamma_status": "HEURISTIC_CLASS_INPUT",
    "owned_oil_activity_measured": False,
}
_PARTIAL_PROFILE_EVIDENCE = {
    "carum carvi fruit oil iso 8896 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.standards.iteh.ai/samples/66253/ec9d0977d3e24e3a85813e08ef968e27/ISO-8896-2016.pdf",
                "document": "ISO 8896:2016 Essential oil of caraway (Carum carvi L.)",
                "table": "Table 1, Chromatographic profile",
                "published_botanical_name": "Carum carvi L.",
                "published_type": "Dried ripe fruit, steam distilled",
                "standard_range_pct": {
                    "myrcene": (0.2, 0.7),
                    "limonene": (33.0, 45.0),
                    "cis-dihydrocarvone": (0.1, 1.5),
                    "trans-carveol": (0.0, 0.5),
                    "cis-carveol": (0.2, 0.5),
                    "carvone": (50.0, 63.0),
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "trans_carveol_lower_bound": "TRACES_BELOW_0_01_PCT_TAKEN_AS_ZERO",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Caraway Seed Oil (10% w/w in DPG)",
                "owned_supplier_and_origin_recorded": False,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("limonene", "myrcene")},
        },
        "unresolved_constituents": (
            {
                "name": "carvone",
                "reported_fraction": 0.565,
                "reported_fraction_range": (0.50, 0.63),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cis-dihydrocarvone",
                "reported_fraction": 0.008,
                "reported_fraction_range": (0.001, 0.015),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cis-carveol",
                "reported_fraction": 0.0035,
                "reported_fraction_range": (0.002, 0.005),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "trans-carveol",
                "reported_fraction": 0.0025,
                "reported_fraction_range": (0.0, 0.005),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 8896 describes a conforming commercial caraway oil; it is not an analysis of the owned bottle, whose supplier, origin and lot are not recorded.",
            "Range midpoints are nominal model inputs; a conforming oil can sit anywhere in each range (carvone 50-63%, limonene 33-45%). The range minima sum to 83.5% and the maxima to 111.2%.",
            "Only 39.45% of nominal composition is modeled (limonene and myrcene). Carvone, the caraway character constituent, has no runtime headspace input; it and the other unresolved constituents remain uncomputed, not odorless, so the modeled headspace does not represent caraway character.",
        ),
    },
    "cinnamomum zeylanicum bark oil sri lanka supplier coa profile": {
        "analytical_method": "SUPPLIER_COA_GC_FID",
        "composition_basis": "SUPPLIER_COA_GC_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "amrita.net certificate of analysis EO3231-CBBL",
                "document": "Cinnamon Bark Organic, Sri Lanka, CoA EO3231-CBBL (produced 2022-03-22)",
                "published_botanical_name": "Cinnamomum zeylanicum (C. verum)",
                "published_type": "Bark oil, organic, Sri Lanka",
                "quantitation": "GC_FID_DB5_AREA_PCT",
                "reported_pct": {
                    "(E)-cinnamaldehyde": 79.71,
                    "eugenol": 6.00,
                    "linalool": 4.86,
                    "(E)-cinnamyl acetate": 4.02,
                    "beta-caryophyllene": 1.78,
                },
                "reported_sum_pct": 96.37,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Cinnamon Bark EO - Telvada USDA Organic (neat)",
                "owned_species_and_origin_recorded": False,
                "leaf_oil_rows_used": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("cinnamaldehyde", "eugenol", "linalool", "beta caryophyllene")},
        },
        "unresolved_constituents": (
            {
                "name": "(E)-cinnamyl acetate",
                "reported_fraction": 0.0402,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is one supplier's certificate for a Sri Lanka organic bark oil, not an analysis of the owned Telvada bottle, whose species, origin and lot composition are unknown.",
            "The certificate lists only five constituents (96.37% of area); GC-FID areas are nominal model inputs, not measured mass fractions.",
            "Bark oil only: cinnamon leaf oil (eugenol-dominant) is non-equivalent and must not be mapped to this profile.",
            "Cinnamaldehyde uses the ODT_DATA air ODT of 62 ppb; the cassia profile keeps an older 0.5 ppb input, so the two cinnamaldehyde-rich profiles are not on the same ODT basis.",
            "(E)-Cinnamyl acetate (4.02%) has no runtime headspace input and remains uncomputed, not odorless.",
        ),
    },
    "lavandula x intermedia supercritical co2 extract pellerin 1991 profile": {
        "analytical_method": "LITERATURE_GC_SUPERCRITICAL_CO2_EXTRACT",
        "composition_basis": "LITERATURE_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.thegoodscentscompany.com/gca/gc1045781.html",
                "document": "Pellerin P. (1991) Perfumer & Flavorist 16(4):37, as tabulated by The Good Scents Company",
                "published_botanical_name": "Lavandula x intermedia (species not stated in the tabulation)",
                "published_type": "Supercritical CO2 extract labelled lavandin absolute",
                "reported_pct": {
                    "linalyl acetate": 28.4,
                    "linalool": 10.1,
                    "coumarin": 7.7,
                    "herniarin": 2.6,
                    "beta-caryophyllene + alpha-humulene": 2.4,
                    "lavandulyl acetate": 1.8,
                    "camphor": 1.7,
                    "borneol": 1.5,
                    "terpinen-4-ol": 1.1,
                },
                "reported_sum_pct": 57.3,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Lavandin Absolute (neat / as supplied)",
                "owned_supplier_reference": "PerfumersWorld 8HY00554",
                "owned_extraction_matches_source": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("linalyl acetate", "linalool", "coumarin", "lavandulyl acetate",
                            "camphor", "borneol", "terpinen-4-ol")},
        },
        "unresolved_constituents": (
            {
                "name": "herniarin",
                "reported_fraction": 0.026,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-caryophyllene + alpha-humulene",
                "reported_fraction": 0.024,
                "missing_input": "CO_REPORTED_SUM_NOT_SPLIT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The source is a supercritical CO2 extract; the owned PerfumersWorld 8HY00554 material is sold as a solvent absolute. The two extractions are non-equivalent (coumarin, herniarin and non-volatile fractions can differ).",
            "Only 57.3% of the extract is listed; the 42.7% unknown remainder is uncomputed, not odorless, and nothing is renormalized.",
            "Herniarin (2.6%) has no runtime headspace input, and beta-caryophyllene + alpha-humulene (2.4%) is reported only as a sum; both remain uncomputed.",
            "This is a 1991 literature profile, not an analysis of the owned product or lot.",
        ),
    },
    "abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile": {
        "analytical_method": "LITERATURE_GC_MS_NIST_LIBRARY_ID",
        "composition_basis": "GC_MS_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6272330/",
                "document": "Arokiyaraj et al., Molecules 2015, 20:384, Table 1",
                "published_botanical_name": "Abelmoschus moschatus Medik.",
                "published_type": "Seed oil (not an absolute); extraction method not verified",
                "quantitation": "GC_MS_AREA_PCT_NIST_LIBRARY_ID_NO_RI_NO_CALIBRATION",
                "reported_pct": {
                    "farnesol acetate": 51.45,
                    "ambrettolide": 12.96,
                    "lauryl acetate": 7.80,
                    "decyl acetate": 6.53,
                    "(Z)-5-tetradecen-1-ol acetate": 3.74,
                    "(E)-farnesol": 2.66,
                    "(Z)-5-dodecen-1-ol acetate": 2.09,
                    "linoleic acid": 2.03,
                    "alpha-guaiene": 1.16,
                },
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Ambrette Seed Absolute (10% in DPG)",
                "owned_supplier_reference": "PerfumersWorld 5XU12235",
                "owned_extraction_matches_source": False,
            },
            "ambrettolide": {
                "mw_status": "DATA_SPINE_MOLECULAR_MASS",
                "odt_status": "ODT_DATA_PEER_SINGLE_KRAFT_2005",
                "vp_status": "DATA_SPINE_UNCITED_ENGINE_ESTIMATE",
                "gamma_status": "HEURISTIC_MACROCYCLIC_MUSK_CLASS",
                "isomer_identity": "NIST_LIBRARY_ID_NOT_VERIFIED_AS_Z_HEXADEC_7_EN_16_OLIDE",
                "owned_oil_activity_measured": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("farnesol", "alpha guaiene", "linoleic acid")},
        },
        "unresolved_constituents": (
            {
                "name": "farnesyl acetate",
                "reported_fraction": 0.5145,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "lauryl acetate",
                "reported_fraction": 0.078,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "decyl acetate",
                "reported_fraction": 0.0653,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(Z)-5-tetradecen-1-ol acetate",
                "reported_fraction": 0.0374,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(Z)-5-dodecen-1-ol acetate",
                "reported_fraction": 0.0209,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is a published seed OIL GC-MS, not an analysis of an ambrette absolute or of the owned PerfumersWorld 5XU12235 lot; no absolute-specific table was found.",
            "Peaks are NIST library identifications without retention indices or calibration; GC-MS areas are nominal model inputs, not mass fractions.",
            "The 'ambrettolide' peak may be (Z)-hexadec-7-en-16-olide or a related isomer; its VP is an uncited data-spine engine estimate.",
            "Farnesyl acetate (51.45%), the alkyl and alkenyl acetates and about 24 minor peaks are not modeled; they remain uncomputed, not odorless. A 2,2-dimethylpropanoic acid peak (1.45%) looks like a library mis-ID and is not used.",
        ),
    },
    "iris rhizome concrete 8 pct irone low grade scenario profile": {
        "analytical_method": "SUPPLIER_GRADE_LABEL_AND_REFERENCE_RANGE",
        "composition_basis": "LOW_GRADE_SCENARIO_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://thegoodscentscompany.com/data/co1001091.html",
                "document": "Supplier grade labels ORRIS CONCRETE 8% IRONE and ORRIS CONCRETE 15% IRONE; Premiere Peau orris concrete glossary",
                "published_botanical_name": "Iris pallida or Iris germanica rhizome",
                "published_type": "Concrete / butter (not an absolute)",
                "modeled_total_irone_pct": 8.0,
                "known_supplier_irone_grades_pct": (8.0, 15.0),
                "myristic_acid_range_pct": (60.0, 85.0),
                "irone_rule": "LOWEST_KNOWN_SUPPLIER_GRADE_CONSERVATIVE_SCENARIO",
                "myristic_acid_rule": "MIDPOINT_OF_REFERENCE_RANGE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Orris Concrete Orris Butter (10% in DPG)",
                "owned_supplier_reference": "PerfumersWorld 5IA07847",
                "owned_grade_irone_pct_known": False,
            },
            "irone pool (alpha-equivalent)": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "myristic acid": {
                "mw_status": "DATA_SPINE_MOLECULAR_MASS",
                "vp_status": "MODELED_NON_VOLATILE_MASS_ROW",
                "odt_status": "MODELED_NON_VOLATILE_MASS_ROW",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "limitations": (
            "The owned PerfumersWorld 5IA07847 grade's irone content is unknown; this models the lowest known supplier grade (8% total irones) as the conservative scenario. A 15% irone grade would roughly double the irone headspace.",
            "Irones use the module's alpha-irone-equivalent pool input; the cis/trans and alpha/gamma isomer split of the owned material is not modeled.",
            "Myristic acid is the 60-85% reference-range midpoint and is treated as a non-volatile mass row; the remaining aromatic fraction beyond irones is uncomputed, not odorless.",
            "Concrete/butter is non-equivalent to orris absolute and to the PerfumersWorld Orris Liquid 8IQ24653.",
        ),
    },
    "citrus bergamia calabrian type iso 3520 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.standards.iteh.ai/samples/81602/2b45583f486b4ae29289d765e8a46f9c/ISO-3520-2022.pdf",
                "document": "ISO 3520:2022 Essential oil of bergamot (Citrus bergamia Risso et Poit.), Calabrian type",
                "table": "Table 2, Chromatographic profile",
                "published_botanical_name": "Citrus bergamia Risso et Poit.",
                "published_type": "Calabrian type, whole expressed oil (not furocoumarin-free)",
                "standard_range_pct": {
                    "beta pinene": (4.0, 8.5),
                    "limonene": (32.0, 47.0),
                    "gamma terpinene": (6.0, 10.0),
                    "linalool": (3.0, 15.0),
                    "linalyl acetate": (22.0, 36.0),
                    "geranial": (0.25, 0.5),
                    "beta-bisabolene": (0.3, 0.7),
                },
                "standard_bergaptene_pct_hplc": (0.18, 0.38),
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Bergamot FCF oil Sicilian",
                "owned_supplier_iso_conformity_claimed": False,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("limonene", "linalyl acetate", "linalool", "gamma terpinene",
                            "beta pinene", "geranial")},
        },
        "unresolved_constituents": (
            {
                "name": "beta-bisabolene",
                "reported_fraction": 0.005,
                "reported_fraction_range": (0.003, 0.007),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 3520 describes a conforming Calabrian whole expressed commercial oil; it is not an analysis of the owned bottle and does not describe furocoumarin-free processing or Sicilian origin.",
            "Range midpoints are nominal model inputs; a conforming oil can sit anywhere in each range (limonene 32-47%, linalyl acetate 22-36%, linalool 3-15%). The range minima sum to 67.55% and the maxima to 117.7%.",
            "Only 92.125% of nominal composition is modeled; beta-bisabolene and unlisted constituents remain uncomputed, not odorless. Bergaptene is a whole-oil HPLC specification, not part of the modeled headspace.",
        ),
    },
    "citrus paradisi expressed oil iso 3053 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.standards.iteh.ai/samples/32040/5decda805f4f4d28af4cdb41a472155b/ISO-3053-2004.pdf",
                "document": "ISO 3053:2004 Oil of grapefruit (Citrus x paradisi Macfad.), obtained by expression",
                "table": "Table 1, Chromatographic profile (normative)",
                "published_type": "Expressed whole oil (not furocoumarin-free)",
                "standard_range_pct": {
                    "alpha pinene": (0.2, 0.6),
                    "sabinene": (0.1, 0.6),
                    "beta pinene": (0.05, 0.2),
                    "myrcene": (1.5, 2.5),
                    "limonene": (92.0, 96.0),
                    "octanal": (0.2, 0.8),
                    "nonanal": (0.04, 0.1),
                    "decanal": (0.1, 0.6),
                    "neral": (0.02, 0.04),
                    "beta caryophyllene": (0.2, 0.5),
                    "nootkatone": (0.01, 0.8),
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_reference": "PerfumersWorld 7CA24030",
                "owned_supplier_sds_cas": "68917-32-8 (grapefruit oil terpenes; not used as identity evidence)",
                "owned_supplier_iso_conformity_claimed": False,
                "owned_supplier_and_origin_recorded": True,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("limonene", "myrcene", "octanal", "nootkatone", "alpha pinene",
                            "sabinene", "beta caryophyllene", "beta pinene", "neral")},
        },
        "unresolved_constituents": (
            {
                "name": "decanal",
                "reported_fraction": 0.0035,
                "reported_fraction_range": (0.001, 0.006),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "nonanal",
                "reported_fraction": 0.0007,
                "reported_fraction_range": (0.0004, 0.001),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 3053 describes a conforming expressed commercial grapefruit oil; it is not an analysis of the owned bottle and does not describe the furocoumarin-free process.",
            "Range midpoints are nominal model inputs; a conforming oil can sit anywhere in each range (limonene 92-96%, nootkatone 0.01-0.8%). The range minima sum to 94.42% and the maxima to 102.74%.",
            "Only 98.16% of nominal composition is modeled; n-decanal, n-nonanal and unlisted constituents remain uncomputed, not odorless.",
        ),
    },
    "canarium elemi oil perfumersworld 7qc00902 allergen declaration profile": {
        "analytical_method": "SUPPLIER_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=7QC00902",
                "document": "PerfumersWorld Allergen Declaration, Elemi Essential Oil, SKU 7QC00902",
                "declared_pct": {
                    "limonene (5989-27-5)": 45.0869,
                    "terpineol (98-55-5, alpha-terpineol)": 3.0843,
                    "terpinolene (586-62-9)": 0.5133,
                    "pinene (80-56-8, alpha-pinene)": 0.3888,
                    "methyl eugenol (93-15-2)": 0.3068,
                    "carvone (99-49-0)": 0.1230,
                    "alpha-terpinene (99-86-5)": 0.0545,
                    "gamma-terpinene (99-85-4)": 0.0507,
                    "geranial (141-27-5)": 0.0359,
                    "camphor (464-49-3)": 0.0334,
                },
                "sds_section_3_range_pct": {
                    "d-limonene": (40.0, 50.0),
                    "alpha terpineol": (1.0, 10.0),
                    "beta-pinene": (1.0, 10.0),
                    "para-cymene": (1.0, 10.0),
                    "alpha pinene": (0.1, 1.0),
                    "methyl eugenol": (0.1, 1.0),
                    "l-carvone": (0.1, 1.0),
                },
                "supplier_species_label": "Canarium indicum (PerfumersWorld synonyms and CoA; also listed as Manila Elemi)",
                "owner_inventory_species_label": "Canarium luzonicum",
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_and_origin_recorded": True,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("limonene", "alpha terpineol", "terpinolene", "alpha pinene",
                            "methyl eugenol", "gamma terpinene", "geranial", "camphor")},
        },
        "unresolved_constituents": (
            {
                "name": "carvone",
                "reported_fraction": 0.001230,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-terpinene",
                "reported_fraction": 0.000545,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-pinene",
                "reported_fraction_range": (0.01, 0.10),
                "missing_input": "SDS_HAZARD_BAND_ONLY_NOT_A_COMPOSITION_VALUE",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "para-cymene",
                "reported_fraction_range": (0.01, 0.10),
                "missing_input": "SDS_HAZARD_BAND_ONLY_NOT_A_COMPOSITION_VALUE",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "elemol",
                "missing_input": "NOT_QUANTIFIED_FOR_THIS_PRODUCT_AND_NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "elemicin",
                "missing_input": "NOT_QUANTIFIED_FOR_THIS_PRODUCT_AND_NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-phellandrene",
                "missing_input": "NOT_QUANTIFIED_FOR_THIS_PRODUCT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "An allergen declaration lists regulated allergens only; it is not a full composition and its analytical basis is not stated.",
            "Only 49.5% of the oil is modeled. Published Canarium oils report elemol, elemicin and alpha-phellandrene as major constituents (for example Galovičová et al. 2020, Potravinarstvo 14:1088-1096, doi:10.5219/1490: d-limonene 36.4, elemol 16.7, alpha-phellandrene 12.2, elemicin 9.59 TIC area %); these remain uncomputed, not odorless.",
            "PerfumersWorld labels the oil Canarium indicum while the owner's inventory says Canarium luzonicum; species identity is unresolved.",
            "The supplier SDS lists hexyl salicylate at 0.1-1%, which is not a known elemi constituent; supplier documents may follow a template.",
        ),
    },
    "lavandula latifolia spanish type iso 4719 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.iso.org/standard/55964.html",
                "document": "ISO 4719:2012 Essential oil of spike lavender (Lavandula latifolia Medikus), Spanish type",
                "table": "Table 1, Chromatographic profile",
                "published_botanical_name": "Lavandula latifolia Medikus",
                "published_type": "Spanish type",
                "standard_range_pct": {
                    "limonene": (0.5, 3.0),
                    "1,8-cineole": (16.0, 39.0),
                    "camphor": (8.0, 16.0),
                    "linalool": (34.0, 50.0),
                    "linalyl acetate": (0.0, 1.6),
                    "alpha terpineol": (0.2, 2.0),
                    "trans-alpha-bisabolene": (0.4, 2.5),
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "linalyl_acetate_lower_bound": "NOT_DETECTABLE_TAKEN_AS_ZERO",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_and_origin_recorded": False,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ('linalool', '1,8-cineole', 'camphor', 'limonene', 'alpha terpineol', 'linalyl acetate')},
        },
        "unresolved_constituents": (
            {
                "name": "trans-alpha-bisabolene",
                "reported_fraction": 0.0145,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 4719 describes a conforming Spanish-type commercial oil; it is not an analysis of the owned bottle, whose supplier and origin are not recorded.",
            "Range midpoints are nominal model inputs; a conforming oil can sit anywhere in each range (linalool 34-50%, 1,8-cineole 16-39%, camphor 8-16%).",
            "Only 85.15% of nominal composition is modeled; trans-alpha-bisabolene and unlisted constituents remain uncomputed, not odorless.",
            "Spike lavender oils of other origins, and lavandin, are not covered by this profile.",
        ),
    },
    "myristica fragrans indonesian type iso 3215 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.iso.org/standard/8418.html",
                "document": "ISO 3215:1998 Oil of nutmeg, Indonesian type (Myristica fragrans Houtt.)",
                "table": "Table 1, Chromatographic profile (normative)",
                "published_botanical_name": "Myristica fragrans Houtt.",
                "published_type": "Indonesian type",
                "standard_range_pct": {
                    "alpha pinene": (15.0, 28.0),
                    "beta pinene": (13.0, 18.0),
                    "sabinene": (14.0, 29.0),
                    "delta-3-carene": (0.5, 2.0),
                    "limonene": (2.0, 7.0),
                    "gamma terpinene": (2.0, 6.0),
                    "terpinen-4-ol": (2.0, 6.0),
                    "safrole": (1.0, 2.5),
                    "myristicin": (5.0, 12.0),
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_page": "https://aromaandmore.com/en/essential-oil-100-pure-/86-nutmeg-essential-oil-indonesia.html",
                "owned_supplier_reference": "NutId0612B",
                "owned_supplier_type_statement": "Indonesia normally produces the East Indian type of Nutmeg.",
                "owned_supplier_iso_conformity_claimed": False,
                "owned_supplier_and_origin_recorded": True,
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("alpha pinene", "sabinene", "beta pinene", "limonene",
                            "gamma terpinene", "terpinen-4-ol", "delta-3-carene")},
        },
        "unresolved_constituents": (
            {
                "name": "myristicin",
                "reported_fraction": 0.085,
                "reported_fraction_range": (0.05, 0.12),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "safrole",
                "reported_fraction": 0.0175,
                "reported_fraction_range": (0.01, 0.025),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 3215 describes a conforming Indonesian-type commercial oil; it is not an analysis of the owned bottle. Aroma&More lists Indonesian steam-distilled seed oil of East Indian type but publishes no composition or CoA and claims no ISO conformity.",
            "Range midpoints are nominal model inputs; a conforming oil can sit anywhere in each range (sabinene 14-29%, alpha-pinene 15-28%, myristicin 5-12%). The range minima sum to 54.5% and the maxima to 110.5%.",
            "Single lots can fall outside the standard: a water-distilled Bogor seed oil (Muchtaridi et al. 2010, Int. J. Mol. Sci. 11:4771, doi:10.3390/ijms11114771) reported alpha-pinene 10.23%, terpinen-4-ol 13.92%, safrole 4.28% and myristicin 13.57%.",
            "Only 72.25% of nominal composition is modeled; myristicin, safrole and unlisted constituents remain uncomputed, not odorless.",
            "Safrole is restricted by IFRA Standard 179 (safrole, isosafrole and dihydrosafrole together at most 0.01% of the finished product); this composition scenario does not feed the IFRA screen.",
            "Mace (aril) oil and West Indian nutmeg oil are not covered by this profile.",
        ),
    },
    "cupressus sempervirens leaf oil literature profile": {
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.3390/plants12051097",
                "table": "Table 1",
                "published_sample_supplier": "Hanus s.r.o.",
                "published_botanical_name": "Cupressus sempervirens",
                "published_plant_part": "leaf",
                "quantitation": "GC_FID_SEMI_QUANTITATIVE",
                "identification": "GC_MS_RETENTION_INDICES_AND_SPECTRA",
                "response_factor_correction": "UNSPECIFIED_IN_SOURCE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_candidate": "Aroma&More French Cupressus sempervirens steam-distilled needles/leaves",
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("alpha pinene", "delta-3-carene", "limonene")},
        },
        "limitations": (
            "External Hanus leaf-oil sample; the Aroma&More French Cupressus sempervirens supplier page is only a conditional identity match, not an owned-bottle or lot assay.",
            "The source reports semi-quantitative GC-FID and GC-MS; FID response-factor correction is unspecified.",
            "Only 69.2% of reported composition is modeled; omitted constituents have unresolved odor contributions.",
            "This proxy does not cover blue cypress, Hinoki, or other botanical species.",
        ),
    },
    "mentha piperita lk literature profile": {
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.1002/ffj.1333",
                "table": "Table 2, LK control",
                "published_botanical_name": "Mentha x piperita",
                "published_accession": "LK (var. Kukrail), CIMAP Lucknow",
                "published_plant_part": "fresh herbage",
                "published_extraction": "hydrodistillation",
                "quantitation": "RELATIVE_GC_FID_PEAK_AREA",
                "identification": "GC_MS_AND_RETENTION_INDICES",
                "response_factor_correction": "NONE_REPORTED_UNCORRECTED_AREAS",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("1,8-cineole", "isomenthone", "limonene")},
            "menthol": {
                "mw_status": "NIST_WEBBOOK_MOLECULAR_MASS",
                "mw_source": "https://webbook.nist.gov/cgi/cbook.cgi?ID=2216-51-5",
                "odt_status": "AUTHOR_REREPORTED_EXPERIMENTAL_C1_ENDPOINT",
                "odt_source": "https://doi.org/10.1093/chemse/bjr094",
                "odt_primary_source": "https://doi.org/10.1016/0031-9384(90)90217-R",
                "odt_table": "Table 3, C1 experimental series",
                "odt_log10_inverse_ppm": 1.660,
                "odt_conversion": "air ppb = 1000 * 10 ** (-1.660)",
                "odt_stereochemistry": "NOT_RESOLVED_BY_THIS_MODEL",
                "vp_status": "LITERATURE_CORRELATION_DL_METASTABLE_LIQUID_PROXY",
                "vp_source": "https://trc.nist.gov/ThermoML/10.1016/j.jct.2016.11.027.html",
                "vp_temperature_K": 298.15,
                "vp_reported_uncertainty_pa": 0.44,
                "vp_method": "CORRELATION_GAS_CHROMATOGRAPHY",
                "gamma_status": "HEURISTIC_MONOTERPENE_ALCOHOL_CLASS",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            {
                "name": "p-menthone",
                "reported_fraction": 0.330,
                "missing_input": "AIR_ODT_NOT_VERIFIED",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "External Mentha x piperita LK control; this is not an owned-oil or supplier-lot composition assay.",
            "Uncorrected GC-FID areas are nominal composition-model inputs, not measured mass fractions.",
            "Only 42.0% of reported area is modeled. Major p-menthone (33.0%) lacks a verified compatible air ODT; its odor contribution and the other omitted constituents remain uncomputed, not zero.",
            "Menthol vapor pressure uses a DL metastable-liquid correlation as a physical proxy; gamma=2 is a heuristic monoterpene-alcohol class input, not activity measured in this oil.",
            "This peppermint proxy does not cover spearmint or Mentha spicata.",
        ),
    },
    "liquidambar orientalis resin ethanol tincture generic profile": {
        "analytical_method": "GC_TOF_MS",
        "composition_basis": "AREA_NORMALIZATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.1093/jpp/rgad093",
                "published_botanical_name": "Liquidambar orientalis",
                "published_material": "Styrax resin extract",
                "quantitation": "GC_TOF_MS_AREA_NORMALIZATION",
                "owned_lot_match": "GENERIC_PROXY_ONLY",
            },
            **{
                name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
                for name in (
                    "cinnamyl alcohol",
                    "beta caryophyllene",
                    "cinnamaldehyde",
                )
            },
        },
    },
    "styrax tonkinensis resin ethanol tincture generic profile": {
        "analytical_method": "GC_MS_AND_HPLC_LITERATURE_COMPOSITE",
        "composition_basis": "GENERIC_RESIN_PROFILE_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.1016/j.foodchem.2016.05.015",
                "published_botanical_name": "Styrax tonkinensis",
                "published_material": "Siam benzoin balsam",
                "owned_lot_match": "GENERIC_PROXY_ONLY",
            },
            **{
                name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
                for name, *_rest in _VIETNAMESE_BENZOIN_TINCTURE_GENERIC_CONSTITUENTS
            },
        },
    },
    "commiphora myrrha resin ethanol tincture generic profile": {
        "analytical_method": "GC_MS",
        "composition_basis": "GC_MS_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.1016/j.jsps.2016.10.011",
                "table": "Table 3",
                "published_botanical_name": "Commiphora myrrha",
                "published_extraction": "48-hour room-temperature ethanol extraction",
                "quantitation": "GC_MS_RELATIVE_AREA",
                "owned_lot_match": "GENERIC_PROXY_ONLY",
            },
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
    },
    "oman boswellia resin ethanol tincture generic profile": {
        "analytical_method": "DERIVED_GENERIC_RESIN_AND_GC_MS_OIL_PROFILE",
        "composition_basis": "LOWER_BOUND_VOLATILE_OIL_SCALED_NOMINAL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8881160/",
                "published_material": "Boswellia sacra gum resin and volatile oil",
                "resin_volatile_oil_fraction": 0.05,
                "fraction_policy": "PUBLISHED_RANGE_LOWER_BOUND",
                "owned_species_match": "UNRESOLVED_GENERIC_PROXY",
            },
            **{
                name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
                for name, *_rest in _OMAN_FRANKINCENSE_TINCTURE_GENERIC_CONSTITUENTS
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class NaturalCompositeMetadata:
    profile_key: str
    resolution: str
    characterized_fraction: float
    composition_authority: str
    batch_specific: bool
    sources: tuple[str, ...]
    limitations: tuple[str, ...]
    analytical_method: str = "UNSPECIFIED_LEGACY_METHOD"
    composition_basis: str = "UNSPECIFIED_LEGACY_BASIS"
    unresolved_fraction: float = 0.0
    quantitative_evaluability: str = "UNASSESSED_LEGACY_PROFILE"
    unresolved_odor_contribution: str = "UNKNOWN_NOT_ZERO"
    unresolved_constituents: tuple[dict[str, object], ...] = ()
    input_authority: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NaturalCompositeHeadspace:
    """Constituent-resolved headspace authority for one natural mixture."""

    oav: float
    vapor_ppm: float
    partial_pressure_pa: float
    constituent_count: int
    temperature_K: float  # noqa: N815
    temperature_model: str = (
        "heuristic:clausius_clapeyron_vp25_dhvap_correlation"
    )
    dhvap_model: str = (
        f"literature_correlation:{VP25_DHVAP_CORRELATION_SOURCE}"
    )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _build_normalized_profile_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for raw_key, constituents in _ABSOLUTE_CONSTITUENTS.items():
        normalized = normalize_name(raw_key)
        previous = index.get(normalized)
        if previous is not None and _ABSOLUTE_CONSTITUENTS[previous] != constituents:
            raise ValueError(
                f"Natural profile collision: {previous!r} and {raw_key!r} "
                f"both normalize to {normalized!r}"
            )
        index[normalized] = raw_key
    return index


_NORMALIZED_PROFILE_INDEX = _build_normalized_profile_index()


# Qualitative character-impact multipliers retained for future accord/salience
# analysis. They MUST NOT be applied to quantitative OAV: the constituent ODT
# already captures odor potency, so multiplying OAV again would double-count it.
_CHARACTER_IMPACT_BONUS: dict[str, dict[str, float]] = {
    "vetiver eo (india)": {"khusimone": 20, "alpha-vetivone": 5, "beta-vetivone": 5},
    "osmanthus absolute": {"beta-ionone": 5},
    "osmanthus absolute (volume grade)": {"beta-ionone": 3},
    "cedarwood oil virginia": {"alpha cedrene": 5, "thujopsene": 3},
    "cedarwood eo": {"alpha cedrene": 5, "thujopsene": 3},
    "oakmoss absolute": {
        "atranol": 3,
        "ethyl orsellinate": 2,
        "orcinol": 5,
        "methyl beta-orcinol": 3,
    },
    "oakmoss absolute (10% in dpg)": {
        "atranol": 3,
        "ethyl orsellinate": 2,
        "orcinol": 5,
        "methyl beta-orcinol": 3,
    },
}


def _character_bonus(material_name: str, constituent_name: str) -> float:
    """Return a qualitative character-impact multiplier, never an OAV factor."""
    canonical = str(material_name or "").strip().casefold()
    bonus_map = _CHARACTER_IMPACT_BONUS.get(canonical, {})
    const_lower = constituent_name.lower()
    for key, bonus in bonus_map.items():
        if key.lower() in const_lower or const_lower in key.lower():
            return bonus
    return 1.0


def audit_constituent_completeness() -> dict[str, dict]:
    """Flag naturals with constituent sum < 30% as incomplete."""
    results = {}
    for key, constituents in _ABSOLUTE_CONSTITUENTS.items():
        total_fraction = sum(c[1] for c in constituents)
        results[key] = {
            "constituent_count": len(constituents),
            "total_fraction": round(total_fraction, 3),
            "status": "OK" if total_fraction >= 0.30 else f"WARN: {total_fraction:.0%} < 30%",
        }
    return results


@lru_cache(maxsize=1024)
def _resolve_profile_key(material_name: str) -> tuple[str | None, str]:
    raw_key = str(material_name or "").strip().casefold()
    normalized = normalize_name(material_name)
    alias_target = _PROFILE_ALIASES.get(normalized)
    if alias_target is not None and alias_target in _ABSOLUTE_CONSTITUENTS:
        return alias_target, "literature_proxy"
    if raw_key in _ABSOLUTE_CONSTITUENTS:
        return raw_key, "direct_identity"
    direct = _NORMALIZED_PROFILE_INDEX.get(normalized)
    if direct is not None:
        return direct, "normalized_identity"
    return None, "unresolved"


# ── Constituent VP from the data spine (diagnosis V3) ───────────────────
#
# Naturals use cited data-spine VPs: a constituent inside a natural evaporates
# with the same 25 C vapour pressure as the same molecule dosed on its own,
# whenever that molecule's data-spine row carries a cited VP source. Only the
# VP column is substituted; fractions, MW, ODT, gamma and the unresolved
# remainder of every profile are unchanged and never renormalized.
CONSTITUENT_VP_POLICY = "naturals_use_cited_data_spine_vp_v1"

# Provenance tags that name an internal default, an override or an estimate
# rather than an external measurement or assessment. A data-spine VP with one
# of these tags (or with no tag) is not cited, so the profile row keeps its VP.
_UNCITED_VP_PROVENANCE_PREFIXES = (
    "engine.",
    "manual:",
    "heuristic:",
    "estimated",
    "synced",
)
_UNCITED_VP_PROVENANCE_MARKERS = ("proxy", "fallback", "component_weighted")


@dataclass(frozen=True, slots=True)
class ConstituentVpSubstitution:
    """One profile row whose table VP was replaced by a cited registry VP."""

    profile_key: str
    constituent: str
    registry_name: str
    table_vp_25c_pa: float
    registry_vp_25c_pa: float
    source: str


def _cited_vp_source(material) -> str | None:
    """Return the cited VP provenance of a data-spine row, else None."""
    if material is None or getattr(material, "vp_25c_pa", None) is None:
        return None
    source = (getattr(material, "provenance", None) or {}).get("vp_25c_pa")
    text = str(source or "").strip()
    folded = text.casefold()
    if not text or folded.startswith(_UNCITED_VP_PROVENANCE_PREFIXES):
        return None
    if any(marker in folded for marker in _UNCITED_VP_PROVENANCE_MARKERS):
        return None
    return text


@lru_cache(maxsize=1024)
def _registry_vp_for_constituent(name: str) -> tuple[str, float, str] | None:
    """Resolve a constituent like a single dosed material; cited VP only."""
    from engine.material_resolver import resolve_material  # noqa: PLC0415

    material = resolve_material(name).registry_material
    source = _cited_vp_source(material)
    if source is None:
        return None
    return material.canonical_name, float(material.vp_25c_pa), source


@lru_cache(maxsize=1024)
def _rows_with_cited_vp(rows: tuple[tuple, ...]) -> tuple[tuple, ...]:
    adjusted: list[tuple] = []
    for row in rows:
        cited = _registry_vp_for_constituent(str(row[0]))
        if cited is None:
            adjusted.append(row)
        else:
            adjusted.append((row[0], row[1], row[2], cited[1], *row[4:]))
    return tuple(adjusted)


def cited_vp_substitutions() -> tuple[ConstituentVpSubstitution, ...]:
    """Every profile row whose VP now comes from a cited data-spine value."""
    records: list[ConstituentVpSubstitution] = []
    for key, rows in _ABSOLUTE_CONSTITUENTS.items():
        for row in rows:
            cited = _registry_vp_for_constituent(str(row[0]))
            if cited is None or float(cited[1]) == float(row[3]):
                continue
            records.append(
                ConstituentVpSubstitution(
                    profile_key=key,
                    constituent=str(row[0]),
                    registry_name=cited[0],
                    table_vp_25c_pa=float(row[3]),
                    registry_vp_25c_pa=float(cited[1]),
                    source=cited[2],
                )
            )
    return tuple(records)


def get_constituents(material_name: str) -> list[tuple] | None:
    """Return constituent list for a known natural mixture, or None.

    Rows carry the cited data-spine VP where one exists (see
    ``CONSTITUENT_VP_POLICY``); every other column is the profile's own.
    """
    key, _resolution = _resolve_profile_key(material_name)
    if key is None:
        return None
    rows = _ABSOLUTE_CONSTITUENTS.get(key)
    if rows is None:
        return None
    return list(_rows_with_cited_vp(tuple(tuple(row) for row in rows)))


def _input_authority_with_cited_vp(key: str, evidence: dict) -> dict[str, object]:
    """Profile input authority, marking rows whose VP now comes from the data spine."""
    authority = deepcopy(evidence.get("input_authority", {}))
    for substitution in cited_vp_substitutions():
        row_authority = authority.get(substitution.constituent)
        if substitution.profile_key == key and isinstance(row_authority, dict):
            row_authority["vp_status"] = "CITED_DATA_SPINE_VP"
            row_authority["vp_source"] = substitution.source
    return authority


def get_composite_metadata(material_name: str) -> NaturalCompositeMetadata | None:
    """Return provenance and modeled-coverage limits for a natural profile."""
    key, resolution = _resolve_profile_key(material_name)
    if key is None:
        return None
    constituents = _ABSOLUTE_CONSTITUENTS[key]
    proxy_limitations = _PROFILE_PROXY_LIMITATIONS.get(normalize_name(material_name), ())
    profile_limitations = _PROFILE_KEY_LIMITATIONS.get(key, ())
    evidence = _PARTIAL_PROFILE_EVIDENCE.get(key, {})
    characterized_fraction = round(sum(float(row[1]) for row in constituents), 9)
    return NaturalCompositeMetadata(
        profile_key=key,
        resolution=resolution,
        characterized_fraction=characterized_fraction,
        unresolved_fraction=max(0.0, round(1.0 - characterized_fraction, 9)),
        analytical_method=str(
            evidence.get(
                "analytical_method",
                "GC_FID_AND_GC_MS" if evidence else "UNSPECIFIED_LEGACY_METHOD",
            )
        ),
        composition_basis=(
            str(evidence["composition_basis"])
            if evidence.get("composition_basis")
            else (
                "GC_FID_AREA_NOMINAL_MODEL_PROXY_NOT_MASS_FRACTION"
                if evidence
                else "UNSPECIFIED_LEGACY_BASIS"
            )
        ),
        quantitative_evaluability=(
            str(evidence["quantitative_evaluability"])
            if evidence.get("quantitative_evaluability")
            else (
                "PARTIAL_INPUT_COVERAGE"
                if evidence
                else "UNASSESSED_LEGACY_PROFILE"
            )
        ),
        unresolved_constituents=deepcopy(evidence.get("unresolved_constituents", ())),
        input_authority=_input_authority_with_cited_vp(key, evidence),
        composition_authority=(
            "LITERATURE_PARTIAL_PROXY"
            if resolution == "literature_proxy"
            else "LITERATURE_PARTIAL_PROFILE"
        ),
        batch_specific=False,
        sources=_PROFILE_SOURCES.get(key, ("repository:legacy_literature_profile",)),
        limitations=(
            "Not a supplier-batch GC-MS or GC-O certificate.",
            "The unresolved model fraction uses the characterized profile's harmonic-mean "
            "molecular weight for mole-pool bookkeeping; its odor contribution is "
            "uncomputed and must not be interpreted as zero.",
            "Constituent ODT and activity coefficients remain modeled inputs.",
            "Constituent VP is temperature-corrected from 25 C with a "
            "VP-derived ambient-temperature enthalpy correlation when measured "
            "data are unavailable; this is not batch-specific thermodynamic data.",
        )
        + profile_limitations
        + proxy_limitations
        + evidence.get("limitations", ()),
    )


def composite_replacement_moles(
    material_name: str,
    active_g: float,
    parent_moles: float,
) -> float | None:
    """Return residual-parent plus resolved-constituent moles for a natural.

    The characterized model fraction is represented by constituent moles. The
    unresolved fraction uses the profile's harmonic-mean MW for mole-pool
    bookkeeping. Its uncomputed odor contribution is unknown, not odorless.
    GC-FID area fractions are nominal model proxies, not measured mass fractions.
    """
    constituents = get_constituents(material_name)
    if constituents is None:
        return None

    _ = parent_moles  # retained for API compatibility and caller bookkeeping
    characterized_fraction = min(
        1.0,
        max(0.0, sum(float(row[1]) for row in constituents)),
    )
    resolved_moles_per_g = sum(
        max(0.0, float(fraction)) / float(mw)
        for _name, fraction, mw, _vp, _odt, _gamma in constituents
        if float(mw) > 0
    )
    resolved_constituent_moles = max(0.0, float(active_g)) * resolved_moles_per_g
    effective_profile_mw = (
        characterized_fraction / resolved_moles_per_g
        if characterized_fraction > 0 and resolved_moles_per_g > 0
        else None
    )
    residual_parent_moles = (
        max(0.0, float(active_g))
        * (1.0 - characterized_fraction)
        / effective_profile_mw
        if effective_profile_mw is not None
        else 0.0
    )
    return residual_parent_moles + resolved_constituent_moles


@lru_cache(maxsize=4096)
def _temperature_adjusted_constituent_rows(
    constituents: tuple[tuple, ...],
    temperature_K: float,  # noqa: N803
    gamma_estimate: float,
    dhvap_estimate_kj_mol: float | None,
) -> tuple[tuple[tuple, ...], bool]:
    """Bind immutable profile rows to one temperature without changing math.

    Robustness and temporal audits evaluate the same natural profile many
    times at one temperature while only dose and formula mole totals change.
    Vapor-pressure correction is independent of those changing quantities, so
    cache that exact deterministic work.  The constituent tuple itself is part
    of the key, which keeps monkeypatched/test profiles and future source edits
    from reusing stale values.
    """

    adjusted: list[tuple] = []
    used_shared_fallback = False
    for name, fraction, mw, vp_25c_pa, odt_ppb, constituent_gamma in constituents:
        gamma_value = (
            float(constituent_gamma)
            if constituent_gamma is not None
            else float(gamma_estimate)
        )
        effective_dhvap = dhvap_estimate_kj_mol
        if effective_dhvap is None:
            try:
                effective_dhvap = estimate_dhvap_from_vp_25c(float(vp_25c_pa))
            except ValueError:
                effective_dhvap = DEFAULT_DHVAP_ESTIMATE_KJ_MOL
                used_shared_fallback = True
        constituent_vp_pa = vp_pa(
            float(temperature_K),
            vp_25c_pa=float(vp_25c_pa),
            dhvap_kj_mol=float(effective_dhvap),
        )
        adjusted.append(
            (
                name,
                fraction,
                mw,
                constituent_vp_pa,
                odt_ppb,
                gamma_value,
            )
        )
    return tuple(adjusted), used_shared_fallback


def composite_headspace(
    material_name: str,
    active_g: float,
    total_moles_in_formula: float,
    gamma_estimate: float = 0.6,
    *,
    parent_moles: float | None = None,
    temperature_K: float = 298.15,  # noqa: N803
    dhvap_estimate_kj_mol: float | None = None,
) -> NaturalCompositeHeadspace | None:
    """Compute constituent-resolved vapor and OAV for a natural mixture.

    Uses available constituent inputs to sum modeled partial pressure, vapor
    concentration, and OAV contributions via modified Raoult's law. This is a
    partial subtotal when coverage is incomplete; omitted odor is unknown.
    Per-profile metadata declares analytical method and nominal fraction basis.

    Args:
        material_name: canonical name (e.g. "osmanthus absolute")
        active_g: active mass in grams in the formula
        total_moles_in_formula: sum of moles of all formula materials, including
            the natural's parent pseudo-component
        gamma_estimate: default activity coefficient if a constituent has none
        parent_moles: moles assigned to the unresolved parent natural. When
            supplied, the characterized fraction is replaced by constituent
            moles instead of being double-represented in the denominator.
        temperature_K: formula-state temperature
        dhvap_estimate_kj_mol: optional caller-supplied shared
            Clausius-Clapeyron enthalpy. When omitted, each constituent uses
            the published ambient-temperature VP25 correlation.

    Returns:
        NaturalCompositeHeadspace, or None if material not known.
    """
    raw_constituents = get_constituents(material_name)
    if raw_constituents is None:
        return None
    constituents, used_shared_fallback = _temperature_adjusted_constituent_rows(
        tuple(tuple(row) for row in raw_constituents),
        float(temperature_K),
        float(gamma_estimate),
        None if dhvap_estimate_kj_mol is None else float(dhvap_estimate_kj_mol),
    )

    P_ATM = 101_325.0  # Pa  # noqa: N806
    total_oav = 0.0
    total_vapor_ppm = 0.0
    total_partial_pressure_pa = 0.0
    constituent_rows: list[tuple[str, float, float, float, float, float]] = []
    resolved_constituent_moles = 0.0

    for name, fraction, mw, constituent_vp_pa, odt_ppb, gamma_value in constituents:
        constituent_mass_g = active_g * fraction
        moles = constituent_mass_g / mw if constituent_mass_g > 0 else 0.0
        resolved_constituent_moles += moles
        constituent_rows.append(
            (name, moles, constituent_vp_pa, odt_ppb, fraction, gamma_value)
        )

    effective_total_moles = float(total_moles_in_formula)
    if parent_moles is not None:
        replacement_moles = composite_replacement_moles(
            material_name,
            active_g,
            parent_moles,
        )
        if replacement_moles is not None:
            effective_total_moles += replacement_moles - max(
                0.0,
                float(parent_moles),
            )

    if effective_total_moles <= 0:
        return None

    contributing_constituents = 0
    for _name, moles, constituent_vp_pa, odt_ppb, _fraction, gamma_value in constituent_rows:
        if moles <= 0:
            continue
        contributing_constituents += 1
        x_i = moles / effective_total_moles
        partial_pressure = gamma_value * x_i * constituent_vp_pa
        vapor_ppm = 1e6 * partial_pressure / P_ATM
        odt_ppm = odt_ppb / 1000.0
        oav_contribution = vapor_ppm / odt_ppm if odt_ppm > 0 else 0.0
        total_partial_pressure_pa += partial_pressure
        total_vapor_ppm += vapor_ppm
        total_oav += oav_contribution

    if dhvap_estimate_kj_mol is not None:
        temperature_model = "caller_supplied:clausius_clapeyron_shared_dhvap"
        dhvap_model = f"caller_supplied:shared_{float(dhvap_estimate_kj_mol):g}_kj_mol"
    elif used_shared_fallback:
        temperature_model = "heuristic:clausius_clapeyron_mixed_dhvap_fallback"
        dhvap_model = (
            f"literature_correlation:{VP25_DHVAP_CORRELATION_SOURCE};"
            f"fallback={DEFAULT_DHVAP_ESTIMATE_KJ_MOL:g}_kj_mol"
        )
    else:
        temperature_model = (
            "heuristic:clausius_clapeyron_vp25_dhvap_correlation"
        )
        dhvap_model = (
            f"literature_correlation:{VP25_DHVAP_CORRELATION_SOURCE}"
        )

    return NaturalCompositeHeadspace(
        oav=total_oav,
        vapor_ppm=total_vapor_ppm,
        partial_pressure_pa=total_partial_pressure_pa,
        constituent_count=contributing_constituents,
        temperature_K=float(temperature_K),
        temperature_model=temperature_model,
        dhvap_model=dhvap_model,
    )


def composite_oav(
    material_name: str,
    active_g: float,
    total_moles_in_formula: float,
    gamma_estimate: float = 0.6,
    *,
    parent_moles: float | None = None,
    temperature_K: float = 298.15,  # noqa: N803
    dhvap_estimate_kj_mol: float | None = None,
) -> float | None:
    """Backward-compatible OAV-only view of constituent headspace."""
    result = composite_headspace(
        material_name,
        active_g,
        total_moles_in_formula,
        gamma_estimate,
        parent_moles=parent_moles,
        temperature_K=temperature_K,
        dhvap_estimate_kj_mol=dhvap_estimate_kj_mol,
    )
    if result is None or result.oav <= 0:
        return None
    return result.oav
