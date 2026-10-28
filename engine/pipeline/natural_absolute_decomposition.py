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

from collections.abc import Sequence
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

# PerfumersWorld's 2026-10-19 email (STK-120): natural orris root extract
# (CAS 8002-73-1) in tricaprylin with residual ethanol, typically 1-5%
# alpha-irone, not measured on the lot. The "80-85% irone" on the product page
# was a typo copied from a generic orris-absolute entry. The 1-5% midpoint is
# modeled as an alpha-irone-equivalent pool; the remaining 97% (mostly the
# tricaprylin carrier, VP ~0) stays unknown and inert rather than renormalized.
_ORRIS_LIQUID_CONSTITUENTS = [
    ("irone pool (alpha-equivalent)", 0.03, 206.32, 0.559, 0.9, 1.3),
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

# Rosa damascena Mill. flower oil, North India: Ahmad, Sahoo, Ahmad & Tandon (2009)
# Asian J. Chem. 21:4643-4647, Table 1 (GC-FID, PE-Wax). Fractions are the
# midpoints of the four regional oils (Pantnagar, Lucknow, Moradabad, Kashmir).
# The stearoptene alkanes are mass-only rows; eicosane uses its formula mass
# (C20H42). cis-Rose oxide uses the rose oxide row. alpha-Humulene has no runtime
# input and stays unresolved. Nothing is renormalized.
_ROSE_EO_CONSTITUENTS = [
    ("citronellol", 0.21975, 156.27, 2.0, 5.0, 2.0),
    ("geraniol", 0.2561, 154.25, 4.0, 2.0, 1.5),
    ("nerol", 0.10315, 154.25, 2.02, 5.0, 1.5),
    ("nonadecane", 0.08665, 268.5, 0.0, 1e6, 0.5),
    ("heneicosane", 0.0567, 296.58, 0.0, 1e6, 0.5),
    ("geranyl acetate", 0.0226, 196.29, 5.0, 10.0, 2.0),
    ("farnesol", 0.0164, 222.37, 0.05, 3.0, 0.6),
    ("eugenol", 0.013, 164.2, 2.5, 0.5, 1.5),
    ("eicosane", 0.0121, 282.55, 0.0, 1e6, 0.5),
    ("linalool", 0.0104, 154.25, 21.3, 1.5, 2.0),
    ("alpha guaiene", 0.00715, 204.35, 1.0, 3.0, 1.2),
    ("geranial", 0.00465, 152.23, 3.0, 0.5, 1.5),
    ("phenylethyl alcohol", 0.0052, 122.16, 11.57, 26.0, 0.7),
    ("rose oxide", 0.00405, 154.25, 15.0, 0.5, 2.0),
]

_CASSIA_EO_CONSTITUENTS = [
    # PhytoChemia GC report for Plant Therapy cassia lot CA0101 (26 Feb 2016;
    # https://funyu-store.b-cdn.net/report/Cinnamon-Cassia-CA0101.pdf): cinnamaldehyde
    # 79.05, o-methoxycinnamaldehyde 8.77, cinnamyl acetate 3.30, coumarin 2.04,
    # benzaldehyde 0.89 %. One lot, not Kenny's; o-methoxycinnamaldehyde and cinnamyl
    # acetate are left out (no air-ODT input here). VPs and air ODTs are the engine's
    # rows (cinnamaldehyde 3.85 Pa HSDB / 62 ppb; coumarin 0.0876 Pa EPI / 0.7 ppb;
    # benzaldehyde 169 Pa / 140.5 ppb). The 2 % linalool of the old profile had no source.
    ("cinnamaldehyde", 0.7905, 132.16, 3.85, 62.0, 2.0),
    ("coumarin", 0.0204, 146.14, 0.0876, 0.7, 0.5),
    ("benzaldehyde", 0.0089, 106.12, 169.0, 140.5, 1.5),
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

# Pomelo (Citrus maxima = C. grandis) peel oil, limonene-dominant literature
# profile. Fractions are the midpoints of the min-max values across the three
# published GC profiles that agree on a limonene-dominant oil (Mondello et al.
# 1996; AJC 2020 doi:10.14233/AJCHEM.2020.22234; Dhaka Univ. J. Sci.), as
# compiled in the 2026-10-13 new-stock research note. It is a literature proxy,
# not an analysis of the owned bottle: species, extraction method and lot are
# unrecorded. Two of the three sources are distilled oils. Inputs reuse this
# module's existing runtime tuples (alpha-phellandrene reuses the Schinus class
# row; ocimene reuses the generic ocimene row). Linalool, citral and nootkatone
# are reported only for an oxygenated hydrodistilled pomelo oil and are not
# added. Nothing is renormalized: about 1.5% stays unidentified.
_POMELO_PEEL_OIL_LITERATURE_MIDPOINT_CONSTITUENTS = [
    ("limonene", 0.946, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.0203, 136.24, 400.0, 10.0, 3.0),
    ("alpha phellandrene", 0.00793, 136.24, 330.0, 20.0, 3.0),
    ("alpha pinene", 0.0063, 136.24, 400.0, 20.0, 3.0),
    ("beta pinene", 0.00248, 136.24, 250.0, 30.0, 3.0),
    ("ocimene", 0.0021, 136.24, 250.0, 20.0, 3.0),
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

# Distilled lime oil (Citrus aurantifolia Swingle), Mexico: Dugo, Cotroneo,
# Bonaccorsi & Mondello (1998) Flavour Fragr. J. 13:93-97, Table 1; fractions are
# the midpoints of the four Mexican oils' GC ranges. Citral is the owned SKU's
# PerfumersWorld 7CK00274 declaration (lot LIM00274/26298), which the paper's
# listed rows do not cover. alpha-Terpinene uses NIST, RIFM-quoted FMA (converted
# to 25 C) and Cometto-Muniz 1998 inputs; p-cymene and alpha-phellandrene reuse the
# Schinus class rows. Nine listed constituents have no runtime input and stay
# unresolved. Nothing is renormalized.
_LIME_DISTILLED_EO_CONSTITUENTS = [
    ("limonene", 0.41365, 136.24, 200.0, 20.0, 3.0),
    ("gamma terpinene", 0.09725, 136.24, 90.0, 50.0, 3.0),
    ("terpinolene", 0.0775, 136.23, 150.0, 30.0, 3.0),
    ("alpha terpineol", 0.07535, 154.25, 2.0, 10.0, 1.5),
    ("1,8-cineole", 0.073, 154.25, 200.0, 50.0, 2.0),
    ("p cymene", 0.03045, 134.22, 240.0, 30.0, 3.0),
    ("alpha-terpinene", 0.01885, 136.234, 96.6, 1418.0, 3.0),
    ("beta pinene", 0.0152, 136.24, 250.0, 30.0, 3.0),
    ("alpha pinene", 0.01055, 136.24, 400.0, 20.0, 3.0),
    ("myrcene", 0.00975, 136.24, 400.0, 10.0, 3.0),
    ("terpinen-4-ol", 0.0069, 154.25, 10.0, 50.0, 1.5),
    ("borneol", 0.00645, 154.25, 3.0, 10.0, 1.5),
    ("beta-caryophyllene", 0.00545, 204.35, 1.5, 10.0, 1.2),
    ("alpha phellandrene", 0.00395, 136.24, 330.0, 20.0, 3.0),
    ("citral", 0.007556, 152.23, 3.0, 0.5, 1.5),
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

# Sweet orange expressed oil (Citrus sinensis), Kenny's STK-112: limonene from his COA (95.28 %),
# the other 10 rows at ISO 3140:2019 Table 2 midpoints scaled x0.8725 so the volatiles total 100 %.
# A specification profile, not a lot GC. Valencene (0.18 %) and beta-sinensal have no runtime input.
_SWEET_ORANGE_ISO3140_CONSTITUENTS = [
    ("limonene", 0.9528, 136.24, 200.0, 38.0, 3.0),  # COA 95.28 %; Nagata 0.038 ppm
    ("myrcene", 0.0218, 136.24, 279.0, 38.0, 3.0),  # VP CRC; no air ODT, limonene analogue
    ("alpha pinene", 0.0052, 136.24, 633.0, 18.0, 3.0),  # Nagata 0.018 ppm
    ("sabinene", 0.0052, 136.24, 400.0, 33.0, 3.0),  # VP estimate; beta-pinene analogue ODT
    ("linalool", 0.0037, 154.25, 21.3, 0.51, 2.0),  # Elsharif 2015 3.2 ng/L
    ("decanal", 0.0035, 156.27, 12.3, 0.4, 2.5),  # Nagata 0.00040 ppm
    ("octanal", 0.0031, 128.21, 157.3, 0.17, 2.5),  # Cometto-Muniz 2010; Nagata 0.010 conflicts
    ("geranial", 0.0011, 152.23, 14.1, 4.337, 1.5),
    ("beta pinene", 0.0007, 136.24, 390.0, 33.0, 3.0),  # Nagata 0.033 ppm
    ("neral", 0.0006, 152.23, 14.1, 4.337, 1.5),
    ("nonanal", 0.0005, 142.24, 49.3, 0.34, 2.5),  # Nagata 0.00034 ppm
]

# Rum ether (pyroligneous acids ethyl esters, CAS 8030-89-5), Kenny's MySkinRecipes 2805 lot QI71T6
# (STK-109, neat). EFSA FGE.500 (2017, https://doi.org/10.2903/j.efsa.2017.4897) per-producer table, Company 2: mean of its three
# batch sets (2009/10, 2015, 2016; GC-FID % of peak area, water-free), put on a whole-product basis
# with its mean water 9.59% (x0.9041). Water and the 1.4% unknown remainder are not rows; nothing is
# renormalized. Company 2 is chosen because its ideal-mix density (~0.86-0.87) fits the COA
# 0.8644-0.8804 (Company 1, 83% ethanol, gives ~0.80): a scenario, not a GC of the lot.
# Air ODTs: Nagata (2003) Table 2 (https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf); VPs: PubChem/HSDB at 25 C. gamma 1.0 = ideal mixing.
_RUM_ETHER_EFSA_COMPANY2_CONSTITUENTS = [
    ("ethanol", 0.3850, 46.07, 7906.0, 520.0, 1.0),  # 42.58 % dry; Nagata 0.52 ppm; HSDB 59.3 mmHg
    ("ethyl acetate", 0.3984, 88.11, 12426.0, 870.0, 1.0),  # 44.07 % dry; Nagata 0.87; HSDB 93.2 mmHg
    ("ethyl formate", 0.0908, 74.08, 32664.0, 2700.0, 1.0),  # 10.04 % dry; Nagata 2.7; HSDB 245 mmHg
    ("ethyl propionate", 0.0143, 102.13, 4773.0, 7.0, 1.0),  # 1.58 % dry; Nagata 0.0070; HSDB 35.8 mmHg
    ("ethyl butyrate", 0.00157, 116.16, 2011.0, 0.040, 1.0),  # 0.173 % dry; Nagata 0.000040 ppm
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

# Piper nigrum fruit oil: Bagheri, Abdul Manap & Solati (2014) Talanta
# 121:220-228, hydrodistilled oil of var. Kuching (Sarawak, Malaysia), GC. The
# six major constituents (73.01%) are modeled as printed, not renormalized.
# The owned bottle's supplier is not recorded; PerfumersWorld 7SQ00359 declares
# d-limonene 20.82%, which is recorded in the evidence but not modeled.
_BLACK_PEPPER_EO_CONSTITUENTS = [
    ("beta-caryophyllene", 0.1864, 204.35, 1.5, 10.0, 1.2),
    ("limonene", 0.1495, 136.24, 200.0, 20.0, 3.0),
    ("sabinene", 0.1319, 136.24, 300.0, 30.0, 3.0),
    ("beta pinene", 0.0971, 136.24, 250.0, 30.0, 3.0),
    ("delta-3-carene", 0.0856, 136.23, 200.0, 50.0, 3.0),
    ("alpha pinene", 0.0796, 136.24, 400.0, 20.0, 3.0),
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
    ("isovalencenol", 0.13, 220.35, 0.01, 2.00, 0.5),
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

# Chinese cedarwood oil (Cupressus funebris wood oil, CAS 85085-29-6): The Good Scents Company
# typical GC (https://www.thegoodscentscompany.com/gca/gc1007241.html), citing R. P. Adams, "Cedarwood oil - analyses and properties"
# (Modern Methods of Plant Analysis NS 12) and P&F 23(5):55 (1998). Same sesquiterpenes as the
# Virginia profile above (molecular inputs reused), thujopsene-led instead of cedrene-led.
_CUPRESSUS_FUNEBRIS_TGSC_CONSTITUENTS = [
    ("thujopsene", 0.299, 204.35, 2.00, 5.00, 1.2),  # 29.90%
    ("alpha cedrene", 0.264, 204.35, 3.00, 10.0, 1.2),  # 26.40%
    ("cedrol", 0.096, 222.37, 0.001, 2.00, 0.5),  # 9.60%
    ("widdrol", 0.095, 222.37, 0.005, 1.00, 0.5),  # 9.50%
    ("beta cedrene", 0.092, 204.35, 2.00, 10.0, 1.2),  # 9.20%
    ("cuparene", 0.034, 202.34, 0.50, 3.00, 1.0),  # 3.40%
]
# Modeled: 88.0% of the typical GC.

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

# Rosa x centifolia absolute: PhytoChemia certificate 22D25-PTH03 (28 Apr 2022)
# for Plant Therapy lot R30111R, FAST GC-FID with a methyl octanoate internal
# standard, response factors corrected (Cachet et al. 2016), so fractions are % m/m.
# The listed constituents total 53.42%; the rest does not elute (waxes, heavier
# material). Palmitic acid and nonadecane are mass-only rows; five listed
# constituents have no runtime input and stay unresolved. Not renormalized.
_ROSE_DE_MAI_CONSTITUENTS = [
    ("phenylethyl alcohol", 0.3068, 122.16, 11.57, 26.0, 0.7),
    ("citronellol", 0.086, 156.27, 2.0, 5.0, 2.0),
    ("geraniol", 0.0521, 154.25, 4.0, 2.0, 1.5),
    ("palmitic acid", 0.0241, 256.42, 0.0, 1e6, 0.5),
    ("eugenol", 0.0048, 164.2, 2.5, 0.5, 1.5),
    ("nonadecane", 0.0023, 268.5, 0.0, 1e6, 0.5),
    ("nerol", 0.0022, 154.25, 2.02, 5.0, 1.5),
    ("methyl eugenol", 0.0011, 178.23, 2.0, 0.5, 1.5),
    ("benzyl alcohol", 0.001, 108.14, 8.0, 5.0, 1.5),
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
    # Styrene 0.5 % of Turkish storax (Hafizoglu 1982, as quoted by Askun et al. 2021,
    # Turk J Bot; a different source from Wang 2023); VP 853 Pa (Chao 1983); air ODT
    # 35 ppb (Nagata 2003, Table 2); gamma 3.0, this module's hydrocarbon-in-ethanol value.
    # Added 2026-10-28: it carries most of the odorant vapour above the tincture.
    ("styrene", 0.005, 104.15, 853.0, 35.0, 3.0),
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
    # Added 2026-10-28, only where every input exists. 4-Vinylguaiacol: 203.05 mg/kg
    # measured in the same oil (Foods 2023, 12, 2515, Table 6). 2-Furfurylthiol and
    # guaiacol: Semmelroch 1995 Arabica (1.08 and 4.2 mg/kg; FFJ 10:1) scaled x3.13, the
    # oil/bean ratio of 4-vinylguaiacol, the only odorant both papers measured
    # (estimate; different beans). 2-Furfurylthiol was not detected in the Foods 2023 oil
    # and oxidises, so its row is an upper bound. Air ODTs: 4-vinylguaiacol 0.4-0.8 ng/L
    # and 2-furfurylthiol 10-20 pg/L (van Gemert 2011 as cited in Molecules 2021, PMC8346979;
    # geometric means); guaiacol the engine row. VPs: TGSC estimates (0.019 and 3.98 mmHg
    # at 25 C) and HSDB 13.7 Pa. Gamma 1.0 (none measured). Pyrazines are left out: no
    # sourced VP or air ODT here.
    ("4-vinylguaiacol", 0.00020305, 150.17, 2.53, 0.092, 1.0),
    ("2-furfurylthiol", 0.00000338, 114.17, 531.0, 0.0030, 1.0),
    ("guaiacol", 0.0000132, 124.14, 13.7, 0.01654, 1.0),
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

# Lavender 40/42 trade grade (Kenny's Aroma&More Lav420811P; his call "You
# estimate", 25 Oct 2026). Fractions are the midpoints of two published 40/42
# GC reports: Shay & Company lot 13282 (France, GC-MS, Nov 2024) and Amphora
# Aromatics "Lavender Essential Oil 40-42 Blend" typical GC (2023). Both show
# the lavandin signature Aroma&More describe for their grade (camphor and
# 1,8-cineole near 3% each, borneol, little lavandulyl acetate or ocimene),
# unlike true lavender (ISO 3515: camphor <0.5-1.2%, cineole <1-2.5%). Inputs
# reuse this module's lavender rows (linalool, linalyl acetate, terpinen-4-ol,
# camphor, lavandulyl acetate, beta-caryophyllene) and its generic 1,8-cineole,
# limonene, borneol and ocimene rows. It is an estimate of the grade, not an
# analysis of the owned bottle. Nothing is renormalized: 6.58% stays unresolved.
_LAVENDER_40_42_GRADE_GC_MIDPOINT_CONSTITUENTS = [
    ("linalyl acetate", 0.3953, 196.29, 17.5, 2.7, 2.0),
    ("linalool", 0.3733, 154.25, 21.3, 1.5, 2.0),
    ("terpinen-4-ol", 0.035, 154.25, 10.0, 5.0, 1.5),
    ("camphor", 0.033, 152.23, 25.0, 20.0, 2.0),
    ("1,8-cineole", 0.03065, 154.25, 200.0, 50.0, 2.0),
    ("limonene", 0.01975, 136.24, 200.0, 20.0, 3.0),
    ("beta-caryophyllene", 0.0161, 204.35, 1.5, 10.0, 1.2),
    ("borneol", 0.0151, 154.25, 3.00, 10.0, 1.5),
    ("lavandulyl acetate", 0.00885, 196.29, 3.0, 5.0, 1.5),
    ("ocimene", 0.00715, 136.24, 250.0, 20.0, 3.0),
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

# Pogostemon cablin leaf oil: van Beek & Joulain (2018) Flavour Fragr. J., review,
# Table 4, averages over more than 100 published oil analyses (GC area %).
# Pogostone, a Chinese-chemotype marker, is left out as the review does for
# patchoulol-type oils. 77.27% is modeled, not renormalized; the
# sesquiterpenes without a runtime input stay unresolved.
_PATCHOULI_EO_CONSTITUENTS = [
    ("patchoulol", 0.39, 222.37, 0.005, 0.5, 0.5),
    ("alpha-bulnesene", 0.14, 204.35, 1.0, 5.0, 1.2),
    ("alpha-guaiene", 0.11, 204.35, 1.0, 5.0, 1.2),
    ("seychellene", 0.066, 204.35, 1.0, 5.0, 1.2),
    ("beta-caryophyllene", 0.031, 204.35, 1.5, 10.0, 1.2),
    ("pogostol", 0.024, 222.37, 0.005, 1.0, 0.5),
    ("caryophyllene oxide", 0.0073, 220.35, 0.1, 2.0, 0.6),
    ("beta pinene", 0.002, 136.24, 250.0, 30.0, 3.0),
    ("germacrene d", 0.0012, 204.35, 1.0, 5.0, 1.2),
    ("alpha pinene", 0.0009, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.0003, 136.24, 200.0, 20.0, 3.0),
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
# quantified for this product and stay unresolved. Carvone (l-carvone per the
# SDS) and alpha-terpinene take the 25 Oct 2026 constituent inputs; the other
# rows reuse this module's existing runtime tuples. Nothing is renormalized.
_ELEMI_PW_7QC00902_ALLERGEN_DECLARATION_CONSTITUENTS = [
    ("limonene", 0.450869, 136.23, 200.0, 20.0, 3.0),
    ("alpha terpineol", 0.030843, 154.25, 2.0, 10.0, 1.5),
    ("terpinolene", 0.005133, 136.23, 150.0, 30.0, 3.0),
    ("alpha pinene", 0.003888, 136.24, 400.0, 20.0, 3.0),
    ("methyl eugenol", 0.003068, 178.23, 2.0, 0.5, 1.5),
    ("gamma terpinene", 0.000507, 136.24, 90.0, 50.0, 3.0),
    ("geranial", 0.000359, 152.23, 3.0, 0.5, 1.5),
    ("camphor", 0.000334, 152.23, 25.0, 20.0, 2.0),
    ("(R)-carvone", 0.00123, 150.22, 20.16, 5.534, 2.0),
    ("alpha-terpinene", 0.000545, 136.234, 96.6, 1418.0, 3.0),
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
# Carvone (50-63%, the (S)-(+) enantiomer in caraway) takes PubChem's mass,
# RIFM's FMA vapour pressure (converted to 25 C) and Blank & Grosch's air
# threshold (van Gemert), added 25 Oct 2026. cis-Dihydrocarvone, trans-carveol
# and cis-carveol have no runtime headspace input and stay unresolved, not
# odorless. Nothing is renormalized.
_CARAWAY_ISO_8896_MIDPOINT_CONSTITUENTS = [
    ("(S)-carvone", 0.565, 150.22, 14.25, 4.883, 2.0),
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

# -- Proxy profiles, batch B (2026-10-09) --
# Same conventions as the block above: labelled literature or supplier proxies,
# reused runtime tuples, unresolved constituents kept, nothing renormalized.

# Magnolia officinalis flower bud essential oil, Liu, Wang, Cheng, Wang, Wu, Guo, Miao and Hu
# (2025), J Oleo Sci 74(10):915-927, doi:10.5650/jos.ess25113, Table 3 column S1 (GC-MS peak-area
# %; buds dried at 60 C and hydrodistilled by Chinese Pharmacopoeia Method A). Used for
# MySkinRecipes "Magnolia Absolute" (STK-170), whose page names the INCI Magnolia Officinalis
# Flower Extract (Kenny, 28 Oct 2026: "magnolia abolute takje the INCI on the mykinrecipe page"). No GC of an M. officinalis
# flower absolute was found; the bottle's non-volatile share is unknown, so nothing is scaled or
# renormalized. Seventeen printed constituents (30.73%) have no runtime input and stay unresolved.
_MAGNOLIA_OFFICINALIS_FLOS_LIU_2025_S1_CONSTITUENTS = [
    ("beta caryophyllene", 0.3007, 204.35, 1.0, 10.0, 1.2),
    ("caryophyllene oxide", 0.1872, 220.35, 0.1, 2.0, 0.6),
    ("bornyl acetate", 0.0252, 196.29, 3.0, 10.0, 1.5),
    ("linalool", 0.0167, 154.25, 21.3, 1.5, 2.0),
    ("geraniol", 0.0145, 154.25, 4.00, 2.00, 1.5),
    ("borneol", 0.0142, 154.25, 3.0, 10.0, 1.5),
    ("trans-beta-farnesene", 0.0106, 204.35, 3.0, 5.0, 1.2),
    ("alpha terpineol", 0.0043, 154.25, 2.0, 10.0, 1.5),
]

# Michelia alba D.C. flower essential oil, Punjee, Dilokkunanant, Sukkatta, Vajrodaya,
# Haruethaitanasan, Pitpiangchan and Rakthaworn (2009) Kasetsart J. (Nat. Sci.) 43(5):197-203,
# Table 2, steam distillation (fresh Thai flowers, 500 g, 4 h; GC-MS relative peak area, DB-5).
# Used for the owner's Magnolia EO, which is Michelia alba flower oil (owner-confirmed; Shopee
# shop "True Industry"; Kenny, 28 Oct 2026: "there i anotheer magnlia eo but it micahelia alba
# eo"). Replaces the Zhu (1993) table, which was read from scent.vn (not an accepted source).
# Only nine peaks were reported, so the percentages are shares of the identified peaks. Five
# constituents (5.09%) have no runtime input and stay unresolved; nothing is renormalized.
_MICHELIA_ALBA_FLOWER_PUNJEE_2009_STEAM_CONSTITUENTS = [
    ("linalool", 0.9174, 154.25, 21.3, 1.5, 2.0),
    ("methyl eugenol", 0.0136, 178.23, 2.0, 0.5, 1.5),
    ("beta caryophyllene", 0.0100, 204.35, 1.0, 10.0, 1.2),
    ("germacrene d", 0.0082, 204.35, 1.00, 5.00, 1.2),
]

# Hedychium spicatum rhizome essential oil, Gangwar et al. (2024) Sci Rep 14:28568,
# doi:10.1038/s41598-024-79712-5, Table 1 column HSSH (rhizomes shade-dried 13 days, Clevenger
# hydrodistilled 5 h, Uttarakhand; GC-FID/GC-MS area %, RXi-5). Used for PerfumersWorld
# 7NS25173 "Ginger Lily Oil", which PW leaves unidentified: Kenny's strip test reads ginger root
# (28 Oct 2026: "Ginger root, check on msr"), the commercial "ginger lily oil" (TGSC es1067151). Closest identity,
# not this lot. Nine constituents (63.25%) carry runtime inputs; the sesquiterpene alcohols
# (alpha-cadinol, elemol, germacren-4-ol, alpha-muurolol, eudesmols) have none and stay
# unresolved; nothing is renormalized.
_HEDYCHIUM_SPICATUM_RHIZOME_GANGWAR_2024_HSSH_CONSTITUENTS = [
    ("1,8-cineole", 0.5387, 154.25, 200.0, 50.0, 2.0),
    ("linalool", 0.0341, 154.25, 21.3, 1.5, 2.0),
    ("alpha terpineol", 0.0199, 154.25, 2.0, 10.0, 1.5),
    ("beta pinene", 0.0179, 136.24, 390.0, 33.0, 3.0),
    ("terpinen-4-ol", 0.0098, 154.25, 10.0, 50.0, 1.5),
    ("alpha pinene", 0.0054, 136.24, 400.0, 20.0, 3.0),
    ("sabinene", 0.0039, 136.24, 300.0, 30.0, 3.0),
    ("beta caryophyllene", 0.0019, 204.35, 1.0, 10.0, 1.2),
    ("germacrene d", 0.0009, 204.35, 1.00, 5.00, 1.2),
]

# PerfumersWorld IFRA certificate for "Champaca Flower Essential Oil", SKU
# 7NJ07740 (CAS 94333-99-0; PW synonym "Michaellia Alba FLOWER Oil"). These are
# supplier-declared levels of IFRA-relevant items only (57.0% listed), not a
# full composition or an analysis of the owned bottle. The certificate names
# "Linalool synthetic", so the product may be reconstituted or extended. The
# linalool-dominant pattern matches Michelia alba oil, not true Michelia champaca
# absolute (Kaiser 1989, phenylethyl alcohol/ester/ionone profile), which is
# non-equivalent and not used. Safrole has no runtime input; L-carvone takes the
# 25 Oct 2026 constituent inputs.
_CHAMPACA_PW_7NJ07740_IFRA_DECLARATION_CONSTITUENTS = [
    ("linalool", 0.529063, 154.25, 21.3, 1.5, 2.0),
    ("benzyl benzoate", 0.020679, 212.24, 0.02, 810.0, 0.5),
    ("benzyl salicylate", 0.009121, 228.24, 0.01, 50.0, 0.5),
    ("limonene", 0.006484, 136.23, 200.0, 20.0, 3.0),
    ("methyl eugenol", 0.004126, 178.23, 2.0, 0.5, 1.5),
    ("(R)-carvone", 6.7e-05, 150.22, 20.16, 5.534, 2.0),
]

# Peru balsam (Myroxylon balsamum var. pereirae). PerfumersWorld SKU 2QV00363
# ("Peru Balsam Resinoid") allergen values as relayed by the owner and not
# re-verified against the supplier document. They are declared levels of
# regulated allergens, not a full composition. Benzyl cinnamate (16.71%) and
# benzaldehyde (0.02%) have no runtime headspace input and stay unresolved;
# cinnamic acid, nerolidol and vanillin are reported in literature only as GC-MS
# peak areas, which cannot be converted to percent, and are not modeled.
_PERU_BALSAM_PW_2QV00363_ALLERGEN_DECLARATION_CONSTITUENTS = [
    ("benzyl benzoate", 0.268389, 212.24, 0.02, 810.0, 0.5),
    ("eugenol", 0.000300, 164.20, 2.50, 0.50, 1.5),
    ("coumarin", 0.000162, 146.14, 0.05, 2.0, 0.5),
]

# -- Proxy profiles for further owned naturals (2026-10-09, batch A) --
# Same conventions as the block above: labelled literature or supplier proxies,
# existing runtime tuples reused, constituents without a runtime headspace input
# kept unresolved (not odorless), nothing renormalized.

# Basil (Ocimum basilicum L.) oil, India, methyl chavicol (estragole) type.
# Botanic Universe "Basil Sweet Essential Oil India" supplier GC report
# (2018-03-21): estragole 75.16%, linalool 18.13%; Gulati 1977 (via scent.vn)
# reports an Indian oil at estragole 77.5% / linalool 19.1%. This origin-matched
# GC is used instead of ISO 11043:1998 because Indian oil's linalool (18-19%)
# lies far outside the standard's 0.5-3% range. Estragole, alpha-bisabolene,
# alpha-trans-bergamotene and alpha-humulene have no runtime headspace input and
# stay unresolved. trans-beta-Ocimene reuses the generic ocimene row.
_BASIL_INDIA_ESTRAGOLE_SUPPLIER_GC_CONSTITUENTS = [
    ("linalool", 0.1813, 154.25, 21.3, 1.5, 2.0),
    ("geranial", 0.0064, 152.23, 3.0, 0.5, 1.5),
    ("beta caryophyllene", 0.0040, 204.35, 1.0, 10.0, 1.2),
    ("germacrene d", 0.0038, 204.35, 1.0, 5.0, 1.2),
    ("neral", 0.0037, 152.23, 3.0, 0.5, 1.5),
    ("ocimene", 0.0027, 136.24, 250.0, 20.0, 3.0),
    ("menthol", 0.0026, 156.2652, 4.5, 1000.0 * 10.0 ** (-1.660), 2.0),
]

# Tagetes (Tagetes minuta L.) whole-plant oil, India, Bansal et al., J. Essent.
# Oil Res. 11:747 (1999), via scent.vn; 82.6% of the oil is listed. The
# character ketones (dihydrotagetone 48.7%, (Z)- and (E)-tagetone, (Z)-tagetenone,
# ocimenone) have no runtime headspace input and stay unresolved, so the modeled
# headspace does not represent tagetes character. (Z)-beta-Ocimene reuses the
# generic ocimene row.
_TAGETES_MINUTA_INDIA_BANSAL_1999_CONSTITUENTS = [
    ("ocimene", 0.080, 136.24, 250.0, 20.0, 3.0),
    ("limonene", 0.034, 136.24, 200.0, 20.0, 3.0),
]

# Helichrysum italicum subsp. italicum oil, industrial distilled Corsican oil,
# Bianchini et al., Flavour Fragr. J. 16:30 (2001), via scent.vn; 91.5% is
# listed. Corsican oil is used rather than the Croatian wild-population mean
# (Blazevic 1995) because it is an industrially distilled commercial oil and is
# the source the module's immortelle absolute profile already cites; the owned
# oil's origin is unknown. gamma-Curcumene reuses the immortelle absolute row.
# Neryl propionate, italicene, alpha-curcumene, eudesm-5-en-11-ol and the
# beta-diketones have no runtime headspace input and stay unresolved.
_HELICHRYSUM_CORSICA_BIANCHINI_2001_CONSTITUENTS = [
    ("neryl acetate", 0.326, 196.29, 3.0, 10.0, 1.5),
    ("gamma-curcumene", 0.117, 204.35, 0.5, 5.0, 1.2),
    ("limonene", 0.075, 136.24, 200.0, 20.0, 3.0),
    ("nerol", 0.047, 154.25, 2.02, 5.00, 1.5),
    ("alpha pinene", 0.018, 136.24, 400.0, 20.0, 3.0),
]

# Guaiacwood (Bulnesia sarmientoi, "palo santo") wood oil, steam-distilled
# trunk-wood shavings, Formosa, Argentina, GC-MS relative %, Enriquez &
# Orrabalis, Multequina 28:59-66 (2019), Table 1 "componentes principales";
# the six listed peaks sum to 99.39% and no total identified is stated. The
# owned stock has no supplier SKU, origin or lot record. Bulnesol (58.18%),
# guaiol (28.71%), elemol (10.17%) and alpha-gurjunene (1.08%) have no runtime
# headspace input and stay unresolved, so the modeled rows below do not carry
# guaiacwood character. alpha-Guaiene and beta-caryophyllene reuse this
# module's existing tuples (patchouli and cinnamon bark rows).
_GUAIACWOOD_ENRIQUEZ_2019_CONSTITUENTS = [
    ("alpha guaiene", 0.0067, 204.35, 1.00, 3.00, 1.2),
    ("beta caryophyllene", 0.0058, 204.35, 1.0, 10.0, 1.2),
]

# -- Proxy profiles, batch D (2026-10-09) --
# Same conventions as the blocks above: labelled literature or supplier proxies,
# reused runtime tuples, unresolved constituents kept, nothing renormalized.

# Rosa x damascena Mill. oil, Bulgaria: ISO 9842 ranges as reprinted on two
# Sanritsu certificates of analysis (N1507G25, N1507G26); the ISO edition is not
# stated. Fractions are range midpoints, as in the caraway ISO 8896 profile.
# beta-Phenylethanol (<3.5%) and ethanol (<2.0%) have only an upper bound, so no
# value is invented and both stay unresolved. Citronellol reuses the 2.0 Pa row
# (data-spine VP 2.26 Pa); geraniol and nerol reuse the module's rows. The
# stearoptene alkanes are mass-only rows (VP 0, as the mimosa alkanes are);
# heneicosane uses its formula mass (C21H44). Trace character odorants
# (beta-damascenone, rose oxide, methyl eugenol) are not in the ranges and are
# not modeled. The uncited "rose essential oil" profile is not reused.
_ROSE_OTTO_BULGARIA_ISO_9842_MIDPOINT_CONSTITUENTS = [
    ("citronellol", 0.27, 156.27, 2.0, 5.0, 2.0),
    ("geraniol", 0.185, 154.25, 4.00, 2.00, 1.5),
    ("nerol", 0.085, 154.25, 2.02, 5.00, 1.5),
    ("nonadecane", 0.115, 268.5, 0.0, 1e6, 0.5),
    ("heneicosane", 0.0425, 296.58, 0.0, 1e6, 0.5),
    ("heptadecane", 0.0175, 240.5, 0.0, 1e6, 0.5),
]

# Vetiver (Chrysopogon zizanioides) oil, Haiti: Amrita certificate of analysis,
# Organic Vetiver, lot 5101-LCAA, December 2024, GC on DB-5. Five constituents
# are listed (50.04%). Khusimol and trans-isovalencenol reuse the existing
# _VETIVER_EO_CONSTITUENTS rows; vetiselinenol, cyclocopacamphenol and
# beta-vetivenene have no runtime input and stay unresolved. Vetivones and
# khusimone are not listed, so the characteristic vetiver note is not modeled.
_VETIVER_HAITI_AMRITA_5101_LCAA_COA_CONSTITUENTS = [
    ("khusimol", 0.1980, 220.35, 0.001, 0.50, 0.4),
    ("isovalencenol", 0.1488, 220.35, 0.01, 2.00, 0.5),
]

# Hay absolute. PerfumersWorld allergen declaration for SKU 8NY00523 (neat):
# declared levels of regulated allergens only (1.7775% listed), basis not
# stated; not a full composition. "Terpineol" (CAS 8000-41-7, an isomer
# mixture) is mapped to the module's alpha-terpineol row. Vanillin reuses the
# 0.005 Pa / 0.6 ppb row used by the benzoin and tonka profiles.
_HAY_ABSOLUTE_PW_8NY00523_ALLERGEN_DECLARATION_CONSTITUENTS = [
    ("vanillin", 0.010262, 152.15, 0.005, 0.6, 0.5),
    ("linalyl acetate", 0.005326, 196.29, 17.5, 2.7, 2.0),
    ("alpha terpineol", 0.001609, 154.25, 2.0, 10.0, 1.5),
    ("coumarin", 0.000578, 146.14, 0.05, 2.0, 0.5),
]

# Orange flower absolute. PerfumersWorld IFRA and allergen tables for SKU
# 8NC00338 (neat); the owned 5NC07544 (10% in DPG) declares exactly one tenth
# of each. Only PW's declared levels are modeled: they differ row by row from
# the published absolutes (CIR 2021 linalool 34-48%) and declare no farnesol,
# so mixing in literature rows would contradict PW's own declaration. Benzyl
# cyanide, 7-methoxycoumarin, the two anthranilates and benzaldehyde have no
# row in this module and stay unresolved. Rows reuse this module's linalool,
# geraniol and limonene inputs.
_ORANGE_FLOWER_ABSOLUTE_PW_8NC00338_DECLARATION_CONSTITUENTS = [
    ("linalool", 0.142295, 154.25, 21.30, 1.50, 2.0),
    ("geraniol", 0.007383, 154.25, 4.00, 2.00, 1.5),
    ("limonene", 0.001722, 136.24, 200.0, 20.0, 3.0),
]

# Frangipani absolute. PerfumersWorld IFRA and allergen tables for SKU
# 8ON00534 (neat, Plumeria alba extract, CAS 94350-02-4); the owned 5ON09236
# (10% in DPG) declares exactly one tenth of each. Declared levels only, for
# the same reason as orange flower (published benzyl salicylate 27-45%, and
# farnesol PW does not declare). Benzaldehyde has no row here and stays
# unresolved. Rows reuse this module's inputs.
_FRANGIPANI_ABSOLUTE_PW_8ON00534_DECLARATION_CONSTITUENTS = [
    ("benzyl salicylate", 0.090958, 228.24, 0.01, 50.0, 0.5),
    ("benzyl benzoate", 0.016552, 212.24, 0.02, 810.0, 0.5),
    ("linalool", 0.007789, 154.25, 21.30, 1.50, 2.0),
    ("citronellol", 0.003794, 156.27, 7.00, 10.0, 1.5),
    ("benzyl alcohol", 0.002475, 108.14, 8.00, 5.00, 1.5),
    ("citral", 0.000785, 152.23, 3.00, 0.50, 1.5),
]

# Fir needle oil, PerfumersWorld 7KG07758 (CAS 8021-28-1, species not named by
# PW). CAS 8021-28-1 is Abies balsamea needle oil (Biolandes "Fir balsam",
# Canada), and PW's limonene sits inside Biolandes' 5-15%, so balsam fir is
# inferred. PW's declared rows (limonene, alpha-bisabolol, benzyl alcohol) are
# kept as declared; the main terpenes PW does not declare take the midpoints of
# Biolandes' ranges (beta-pinene 28-38, alpha-pinene 9-24, delta-3-carene
# <=18, bornyl acetate 2-12%), and camphene the midpoint of Canadian Flora's
# balsam fir specification (4-7%, CAS 8021-28-1). The declared traces
# cuminaldehyde and L-carvone take the 25 Oct 2026 constituent inputs; the
# other rows reuse this module's terpene inputs.
_FIR_NEEDLE_BALSAM_PW_7KG07758_BIOLANDES_MIDPOINT_CONSTITUENTS = [
    ("beta pinene", 0.33, 136.24, 250.0, 30.0, 3.0),
    ("alpha pinene", 0.165, 136.24, 400.0, 20.0, 3.0),
    ("delta-3-carene", 0.09, 136.23, 200.0, 50.0, 3.0),
    ("bornyl acetate", 0.07, 196.29, 3.0, 10.0, 1.5),
    ("limonene", 0.063682, 136.24, 200.0, 20.0, 3.0),
    ("camphene", 0.055, 136.24, 400.0, 50.0, 3.0),
    ("alpha-bisabolol", 0.00514, 222.37, 0.01, 5.0, 0.7),
    ("benzyl alcohol", 0.000201, 108.14, 8.00, 5.00, 1.5),
    ("cuminaldehyde", 0.000314, 148.2, 14.25, 14.19, 1.5),
    ("(R)-carvone", 0.000274, 150.22, 20.16, 5.534, 2.0),
]

# Fir needle oil (Canada), MySkinRecipes order 2200410, lot ECPT07 (STK-175; MSDS
# "ABIES BALSAMEA NEEDLE OIL 100%", CAS 85085-34-3, the EINECS number for balsam
# fir). Midpoints of the ranges Swor et al. (2022) Table 2 give for 10 commercial
# Canadian Abies balsamea oils; the represented 90.2% is not renormalized.
# beta-Phellandrene takes the module's class input (as in the Schinus profile);
# the other rows reuse this module's terpene inputs. The PerfumersWorld lot traces
# of the profile above are not carried over.
_FIR_NEEDLE_CANADA_SWOR_2022_MIDPOINT_CONSTITUENTS = [
    ("beta pinene", 0.2745, 136.24, 250.0, 30.0, 3.0),
    ("alpha pinene", 0.2455, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.176, 136.24, 200.0, 20.0, 3.0),
    ("beta phellandrene", 0.0925, 136.24, 300.0, 20.0, 3.0),
    ("delta-3-carene", 0.056, 136.23, 200.0, 50.0, 3.0),
    ("bornyl acetate", 0.0335, 196.29, 3.0, 10.0, 1.5),
    ("camphene", 0.024, 136.24, 400.0, 50.0, 3.0),
]

# Olibanum (frankincense) oil, MySkinRecipes order 2200410, lot 3S74J8 (STK-173;
# MSDS "BOSWELLIA CARTERII GUM OIL 100%", CAS 89957-98-2). Average composition of
# Somali Boswellia carterii oils from Woolley et al. (2012), J Chromatogr A 1261,
# 158-163, as printed in the abstract; the represented 74.4% is not renormalized.
# Every average sits inside the ranges Johnson et al. (2019, Plants 8, 88, Table 2)
# give for 13 commercial "carteri" oils. Limonene is printed together with
# beta-phellandrene and is modeled with the limonene inputs; alpha-thujene takes
# the sabinene inputs as a class input. The other rows reuse this module's inputs.
_OLIBANUM_CARTERII_WOOLLEY_2012_AVERAGE_CONSTITUENTS = [
    ("alpha pinene", 0.373, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.144, 136.24, 200.0, 20.0, 3.0),
    ("alpha thujene", 0.079, 136.24, 300.0, 30.0, 3.0),
    ("myrcene", 0.073, 136.24, 400.0, 10.0, 3.0),
    ("sabinene", 0.049, 136.24, 300.0, 30.0, 3.0),
    ("beta pinene", 0.018, 136.24, 250.0, 30.0, 3.0),
    ("camphene", 0.008, 136.24, 400.0, 50.0, 3.0),
]

# Galbanum resinoid, MySkinRecipes order 2200410, lot QM0D25 (STK-176; MSDS
# "GALBANUM, RESIN (FERULA SPP.) 100%", CAS 9000-24-2). Canton et al. (2025), Chem
# Biodivers e01442: a commercial galbanum resinoid supplied by RIFM, volatile
# fraction 34.5% of the whole by vacuum distillation, its GC-FID % in Table 1. Each
# fraction is the Table 1 % x 0.345, the paper's own volatile share, so the rows
# are on a whole-resinoid basis; nothing is renormalized. Only rows with inputs in
# this module are modeled (13.90% of the resinoid); bulnesol 7.2, guaiol 6.9, an
# unknown 6.5, 10-epi-alpha-eudesmol 3.5, germacrene B 2.5, gamma-elemene 2.1,
# delta-cadinene 1.9, (3E,5E)-undecatriene 0.5 (% of the volatile fraction) and
# the 65.5% non-volatile coumarin fraction are uncomputed, not odorless. Limonene
# coelutes with beta-phellandrene; both eudesmols take the eudesmol inputs.
# (3E,5Z)-undecatriene (0.7 %FID, added 28 Oct 2026): air ODT 0.202 ng/L = 0.033 ppb from
# Givaudan's log(OV) 6.65 (US 2019/0336413 A1) and headspace 904 ug/l at 25 C (US 2023/0151305 A1
# Table 12), the commercial Undecatriene (an isomer mix); VP 14.9 Pa from that headspace (ideal gas).
_GALBANUM_RESINOID_CANTON_2025_VF_CONSTITUENTS = [
    ("beta pinene", 0.08763, 136.24, 250.0, 30.0, 3.0),
    ("beta eudesmol", 0.00966, 222.37, 0.01, 2.00, 0.5),
    ("alpha eudesmol", 0.00897, 222.37, 0.01, 2.00, 0.5),
    ("limonene", 0.006555, 136.24, 200.0, 20.0, 3.0),
    ("delta-3-carene", 0.005865, 136.23, 200.0, 50.0, 3.0),
    ("alpha pinene", 0.00483, 136.24, 400.0, 20.0, 3.0),
    ("germacrene d", 0.004485, 204.35, 1.00, 5.00, 1.2),
    ("myrcene", 0.00414, 136.24, 400.0, 10.0, 3.0),
    ("alpha-bisabolol", 0.003105, 222.37, 0.01, 5.0, 0.7),
    ("beta caryophyllene", 0.00138, 204.35, 1.00, 10.0, 1.2),
    ("(3E,5Z)-1,3,5-undecatriene", 0.002415, 150.26, 14.9, 0.033, 3.0),
]

# Davana oil (Artemisia pallens), PerfumersWorld 5HH12466 "Davana Essential Oil 10%
# in DPG" (STK-184, 28 Oct 2026; PW lists CAS 8016-03-3 at 10%). PW publishes no
# composition. GC/MS report by R. S. Pappas on a commercial Indian oil (Revive lot 8F,
# made February 2024, analysed 29 Jan 2025), Conc. % as printed; its majors match the
# peer-reviewed Singh et al. (2021) abstract (cis-davanone 53.0, bicyclogermacrene 6.9,
# trans-ethyl cinnamate 4.9). Fractions are of the neat oil; the bottle's 10% is applied
# by the stock. Only rows with inputs in this module are modeled (3.13%): davanone
# 53.55, bicyclogermacrene 8.11, the davana ethers 9.41 and the ethyl cinnamates 5.42
# have no runtime input and are uncomputed, not odorless. Nothing is renormalized.
_DAVANA_PAPPAS_2025_REVIVE_8F_CONSTITUENTS = [
    ("germacrene d", 0.0104, 204.35, 1.00, 5.00, 1.2),
    ("alpha eudesmol", 0.0081, 222.37, 0.01, 2.00, 0.5),
    ("geranyl acetate", 0.0076, 196.29, 2.00, 10.0, 1.5),
    ("linalool", 0.0052, 154.25, 21.30, 1.50, 2.0),
]

# Lemon oil, terpeneless, PerfumersWorld 7CC24027 ("Lemon Terpeneless oil
# Sicilian", CAS 68648-39-5, FEMA 2626). PW publishes no composition (SDS: "No
# composition data available for this product") and no allergen rows. The
# British Pharmacopoeia grade is made by concentrating lemon oil in vacuo or by
# solvent partition and "has a citral content of 40-50%" (Trease and Evans'
# Pharmacognosy, as excerpted on ScienceDirect Topics "Lemon Oil", read 25 Oct
# 2026). Citral is modeled at the 45% midpoint with this module's citral row.
# PW's SG 0.885-0.897 fits an oil that is mostly oxygenated compounds (cold-
# pressed lemon is 0.849-0.855). It is an estimate of the grade, not an
# analysis of the owned bottle: the esters, alcohols and sesquiterpenes that
# make up most of the rest stay unresolved, and nothing is renormalized.
_LEMON_TERPENELESS_PW_7CC24027_BP_CITRAL_MIDPOINT_CONSTITUENTS = [
    ("citral", 0.45, 152.23, 3.00, 0.50, 1.5),
]

# ── Master Registry ───────────────────────────────────────────────────

# -- Profiles from the 25 Oct 2026 verified research pass (stock thread) --
# Each value was re-opened by a second reader before loading. Constituent
# rows reuse this module's existing runtime tuples, or cite the data-spine
# record or the constituent source named in the profile's input authority.
# Constituents without a runtime headspace input stay unresolved, not
# odorless. Nothing is renormalized.

# Cabreuva oil (Myrocarpus spp.): PerfumersWorld 7LW00863 IFRA certificate and
# allergen declaration, batch CAB00863/26298, % of the neat oil. (E)-Nerolidol, the
# main constituent (64.54% in Azzi et al. 2017; 60-89% by producer specification),
# has no traceable air ODT and stays unresolved, so the woody-floral character is
# not modeled. Nothing is renormalized.
_CABREUVA_PW_7LW00863_IFRA_DECLARATION_CONSTITUENTS = [
    ("alpha-bisabolol", 0.046708, 222.37, 0.01, 5.0, 0.7),
    ("farnesol", 0.021867, 222.37, 0.05, 3.0, 0.6),
    ("benzyl benzoate", 0.000945, 212.24, 0.02, 810.0, 0.5),
    ("citral", 0.000859, 152.23, 3.0, 0.5, 1.5),
    ("limonene", 0.000118, 136.24, 200.0, 20.0, 3.0),
]

# Pine oil: PerfumersWorld 7KQ07511 IFRA certificate and allergen declaration,
# batch PIN07511/26298 (the owned neat bottle). Only d-limonene (2.84%) has a
# runtime input; longifolene (8.88%) has no air ODT and stays unresolved.
# PerfumersWorld names no species; its levels fit neither Ph. Eur. Scots pine
# needle oil (limonene 7-12%) nor a published commercial Scots pine oil (11.58%),
# so neither is used as a proxy. Nothing is renormalized.
_PINE_PW_7KQ07511_IFRA_DECLARATION_CONSTITUENTS = [
    ("limonene", 0.028407, 136.24, 200.0, 20.0, 3.0),
]

# Santalum album L. oil: ISO 3518:2025 Table 2 chromatographic profile; fractions
# are the midpoints of the (Z)-alpha- and (Z)-beta-santalol ranges. Farnesol and
# lanceol (n.d.-1.0% and n.d.-5.0%) have upper bounds only and stay unresolved. The
# santalol rows use NIST masses, RIFM-printed EPI Suite VP estimates and the
# Bajgrowicz 1998 air thresholds (van Gemert). The owned PerfumersWorld 5WX12225
# names no species; S. album is inferred from its CAS. Nothing is renormalized.
_SANDALWOOD_ALBUM_ISO_3518_MIDPOINT_CONSTITUENTS = [
    ("(Z)-alpha-santalol", 0.48, 220.35, 0.004506, 0.8211, 0.5),
    ("(Z)-beta-santalol", 0.2, 220.35, 0.009826, 0.05992, 0.5),
]

# Tuberalia Base (owned as 'Tuberlia Base'): PerfumersWorld 6ND09663 allergen
# declaration and IFRA certificate, % of the base. A proprietary tuberose-type
# compound; the rest of its composition is undisclosed. Hexyl salicylate and hexyl
# cinnamal have no runtime input; constituents given only as SDS bands get no
# nominal fraction. All stay unresolved. Nothing is renormalized.
_TUBERALIA_BASE_PW_6ND09663_DECLARATION_CONSTITUENTS = [
    ("linalool", 0.087605, 154.25, 21.3, 1.5, 2.0),
    ("hydroxycitronellal", 0.067878, 172.27, 0.3, 1.0, 1.2),
    ("benzyl salicylate", 0.049065, 228.24, 0.01, 50.0, 0.5),
    ("eugenol", 0.016008, 164.2, 2.5, 0.5, 1.5),
    ("benzyl benzoate", 0.009623, 212.24, 0.02, 810.0, 0.5),
    ("benzyl alcohol", 0.006324, 108.14, 8.0, 5.0, 1.5),
]


# Siam benzoin (Styrax tonkinensis resin): FAO/JECFA 74th meeting (2011) Chemical
# and Technical Assessment, Table 2 means over 18 Laotian resin samples, % w/w of
# the resin. 30.6% is modeled, not renormalized; coniferyl benzoate
# (15-57%, HPLC) has no runtime input and stays unresolved. The owned stock is a
# 50% w/w DPG preparation; the stock fraction does the dilution.
_SIAM_BENZOIN_JECFA_2011_CONSTITUENTS = [
    ("benzoic acid", 0.273, 122.12, 0.0, 1000.0, 0.4),
    ("vanillin", 0.018, 152.15, 0.005, 0.6, 0.5),
    ("benzyl benzoate", 0.015, 212.24, 0.02, 810.0, 0.5),
]


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
    "citrus maxima peel oil limonene-dominant literature midpoint profile": (
        _POMELO_PEEL_OIL_LITERATURE_MIDPOINT_CONSTITUENTS
    ),
    "cedrat fcf sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "cedrat fcf oil sicilian": _CEDRAT_FCF_CONSTITUENTS,
    "petitgrain eo paraguay": _PETITGRAIN_EO_CONSTITUENTS,
    "lime distilled eo": _LIME_DISTILLED_EO_CONSTITUENTS,
    "orange peel eo": _ORANGE_PEEL_EO_CONSTITUENTS,
    "rum ether efsa fge500 company 2 scenario profile": _RUM_ETHER_EFSA_COMPANY2_CONSTITUENTS,
    "citrus sinensis sweet orange iso 3140 2019 midpoint profile": _SWEET_ORANGE_ISO3140_CONSTITUENTS,
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
    "cupressus funebris wood oil tgsc typical gc profile": _CUPRESSUS_FUNEBRIS_TGSC_CONSTITUENTS,
    "mentha piperita lk literature profile": _PEPPERMINT_LK_LITERATURE_CONSTITUENTS,
    "lavandula latifolia spanish type iso 4719 midpoint profile": (
        _SPIKE_LAVENDER_ISO_4719_MIDPOINT_CONSTITUENTS
    ),
    "lavender 40/42 grade two published gc midpoint profile": (
        _LAVENDER_40_42_GRADE_GC_MIDPOINT_CONSTITUENTS
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
    "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile": (
        _GUAIACWOOD_ENRIQUEZ_2019_CONSTITUENTS
    ),
    "ocimum basilicum oil india estragole type supplier gc profile": (
        _BASIL_INDIA_ESTRAGOLE_SUPPLIER_GC_CONSTITUENTS
    ),
    "tagetes minuta whole plant oil india bansal 1999 profile": (
        _TAGETES_MINUTA_INDIA_BANSAL_1999_CONSTITUENTS
    ),
    "helichrysum italicum oil corsica bianchini 2001 profile": (
        _HELICHRYSUM_CORSICA_BIANCHINI_2001_CONSTITUENTS
    ),
    "michelia alba flower oil punjee 2009 steam distillation profile": _MICHELIA_ALBA_FLOWER_PUNJEE_2009_STEAM_CONSTITUENTS,
    "magnolia officinalis flos essential oil liu 2025 stage s1 profile": _MAGNOLIA_OFFICINALIS_FLOS_LIU_2025_S1_CONSTITUENTS,
    "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile": _HEDYCHIUM_SPICATUM_RHIZOME_GANGWAR_2024_HSSH_CONSTITUENTS,
    "champaca flower oil perfumersworld 7nj07740 ifra declaration profile": (
        _CHAMPACA_PW_7NJ07740_IFRA_DECLARATION_CONSTITUENTS
    ),
    "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile": (
        _PERU_BALSAM_PW_2QV00363_ALLERGEN_DECLARATION_CONSTITUENTS
    ),
    "rosa x damascena bulgarian oil iso 9842 midpoint profile": (
        _ROSE_OTTO_BULGARIA_ISO_9842_MIDPOINT_CONSTITUENTS
    ),
    "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile": (
        _VETIVER_HAITI_AMRITA_5101_LCAA_COA_CONSTITUENTS
    ),
    "hay absolute perfumersworld 8ny00523 allergen declaration profile": (
        _HAY_ABSOLUTE_PW_8NY00523_ALLERGEN_DECLARATION_CONSTITUENTS
    ),
    "orange flower absolute perfumersworld 8nc00338 declaration profile": (
        _ORANGE_FLOWER_ABSOLUTE_PW_8NC00338_DECLARATION_CONSTITUENTS
    ),
    "frangipani absolute perfumersworld 8on00534 declaration profile": (
        _FRANGIPANI_ABSOLUTE_PW_8ON00534_DECLARATION_CONSTITUENTS
    ),
    "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile": (
        _FIR_NEEDLE_BALSAM_PW_7KG07758_BIOLANDES_MIDPOINT_CONSTITUENTS
    ),
    "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile": (
        _FIR_NEEDLE_CANADA_SWOR_2022_MIDPOINT_CONSTITUENTS
    ),
    "boswellia carterii oil woolley 2012 somali average profile": (
        _OLIBANUM_CARTERII_WOOLLEY_2012_AVERAGE_CONSTITUENTS
    ),
    "ferula galbaniflua resinoid canton 2025 volatile fraction profile": (
        _GALBANUM_RESINOID_CANTON_2025_VF_CONSTITUENTS
    ),
    "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile": (
        _DAVANA_PAPPAS_2025_REVIVE_8F_CONSTITUENTS
    ),
    "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile": (
        _LEMON_TERPENELESS_PW_7CC24027_BP_CITRAL_MIDPOINT_CONSTITUENTS
    ),
    "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile": (
        _CABREUVA_PW_7LW00863_IFRA_DECLARATION_CONSTITUENTS
    ),
    "pine oil perfumersworld 7kq07511 ifra declaration profile": (
        _PINE_PW_7KQ07511_IFRA_DECLARATION_CONSTITUENTS
    ),
    "santalum album oil iso 3518 midpoint profile": (
        _SANDALWOOD_ALBUM_ISO_3518_MIDPOINT_CONSTITUENTS
    ),
    "tuberalia base perfumersworld 6nd09663 declaration profile": (
        _TUBERALIA_BASE_PW_6ND09663_DECLARATION_CONSTITUENTS
    ),
    "styrax tonkinensis resin jecfa 2011 mean profile": _SIAM_BENZOIN_JECFA_2011_CONSTITUENTS,
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
    # Limonene-dominant literature pomelo peel-oil profile used as a labelled
    # proxy for the owned Pomelo EO (species and extraction unrecorded).
    "pomelo eo": "citrus maxima peel oil limonene-dominant literature midpoint profile",
    "pomelo essential oil": "citrus maxima peel oil limonene-dominant literature midpoint profile",
    "pomelo oil": "citrus maxima peel oil limonene-dominant literature midpoint profile",
    # The canonical registry identity still uses a non-lot literature profile.
    # Preserve that authority label after name normalization resolves seed EO.
    "coriander essential oil": "coriander essential oil",
    "coriander seed eo": "coriander essential oil",
    "bergamot eo": "citrus bergamia calabrian type iso 3520 midpoint profile",
    # Kenny's MSR Rum Ether (STK-109, neat): EFSA FGE.500 Company 2 scenario since 28 Oct 2026.
    "rum ether": "rum ether efsa fge500 company 2 scenario profile",
    # Kenny's sweet orange (STK-112, COA limonene 95.28 %): its own ISO 3140 profile since 28 Oct 2026.
    "sweet orange essential oil": "citrus sinensis sweet orange iso 3140 2019 midpoint profile",
    "blood orange sicilian": "orange peel eo",
    # MySkinRecipes order 2199302 stocks (Kenny chose "Link them", 16 Oct 2026): labelled
    # proxies onto the existing whole-oil profiles, not lot data. Bourbon geranium uses the
    # geranium EO profile and Texas cedar
    # (Juniperus mexicana, thujopsene/cedrene/cedrol like Virginia) the cedarwood EO profile.
    "geranium bourbon essential oil": "geranium eo",
    "cedarwood texas eo": "cedarwood eo",
    # Kenny's China cedarwood (V5 row 62, STK-229): Cupressus funebris as the closest identity,
    # by his 28 Oct 2026 rule for unidentified bottles ("select the one that is the closest").
    "cedarwood chinese essential oil": "cupressus funebris wood oil tgsc typical gc profile",
    "cedarwood eo (china; species unspecified)": "cupressus funebris wood oil tgsc typical gc profile",
    # PerfumersWorld Patchouli Light (decolorized patchouli, 7WB13670): same molecules as patchouli oil.
    "patchouli light essential oil": "patchouli eo",
    "patchouli light eo": "patchouli eo",
    # Kenny's Orris Butter 50% w/w in ethanol (2026-10-20): same orris butter scenario as his 10% stock.
    "orris butter 50% in etoh": "iris rhizome concrete 8 pct irone low grade scenario profile",
    "orris butter 50%": "iris rhizome concrete 8 pct irone low grade scenario profile",
    "ylang": "ylang ylang eo (extra grade)",
    "cedarwood virginia": "cedarwood eo",
    "benzoin sumatra resinoid": "benzoin resinoid",
    "lavender eo high altitude": "lavender eo",
    "geranium eo (pelargonium graveolens flower oil)": "geranium eo",
    # MySkinRecipes Galbanum Resinoid (STK-176, 27 Oct 2026): the resinoid's own published
    # volatile fraction replaces the galbanum essential-oil proxy.
    "galbanum resinoid": "ferula galbaniflua resinoid canton 2025 volatile fraction profile",
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
    "siam benzoin": "styrax tonkinensis resin jecfa 2011 mean profile",
    "siam benzoin (50% w/w in dpg)": "styrax tonkinensis resin jecfa 2011 mean profile",
    # Aroma&More SKU Lav420811P: a 40/42 trade grade with lavandin added at
    # production (supplier page). It uses the 40/42-grade GC estimate, not the
    # true-lavender profile of the BONTAUX oil (Kenny, 25 Oct 2026: "You estimate").
    "lavender 40/42, aroma&more": "lavender 40/42 grade two published gc midpoint profile",
    "lavender 40/42": "lavender 40/42 grade two published gc midpoint profile",
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
    # Owner stock "Magnolia EO (neat / as supplied)": Michelia alba flower oil
    # (owner-confirmed species; Shopee shop "True Industry").
    "magnolia eo": "michelia alba flower oil punjee 2009 steam distillation profile",
    # PerfumersWorld 7NS25173 Ginger Lily Oil: H. spicatum rhizome oil, the closest identity
    # (Kenny's strip test, 28 Oct 2026: "Ginger root, check on msr").
    "ginger lily oil": "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile",
    "ginger lily": "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile",
    "ginger lily eo": "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile",
    "ginger lily essential oil": "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile",
    # MySkinRecipes Magnolia Absolute, lot ZDHY6L (STK-170): its INCI, Magnolia officinalis
    # flower (Kenny, 28 Oct 2026). Not the MSR Magnolia Flower Extract (PG, 7871).
    "magnolia absolute": "magnolia officinalis flos essential oil liu 2025 stage s1 profile",
    # Owner stock "Champaca Flower EO"; PerfumersWorld 7NJ07740 is assumed.
    "champaca flower eo": "champaca flower oil perfumersworld 7nj07740 ifra declaration profile",
    # Owner stock "Peru Balsam Resinoid (50% w/w in DEP)" and the V5 requirement
    # row "Peru Balsam 10%" (10% stock not prepared): same balsam identity.
    "peru balsam resinoid": "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile",
    "peru balsam resinoid (50% w/w in dep)": "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile",
    "peru balsam": "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile",
    "peru balsam 10%": "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile",
    # Only the V5 row that names the chemotype ("ct. Methyl Chavicol") maps.
    # Profile lookup drops parentheticals, so the owner stock "Basil EO (India,
    # Ocimum Basilicum)" reads as a bare "Basil EO", whose chemotype is unknown
    # and which stays unresolved.
    "basil eo ct. methyl chavicol": (
        "ocimum basilicum oil india estragole type supplier gc profile"
    ),
    # Owner stock "Tagetes EO (10% in DPG)": Tagetes minuta; origin unknown.
    "tagetes eo": "tagetes minuta whole plant oil india bansal 1999 profile",
    "tagetes eo (10% in dpg)": "tagetes minuta whole plant oil india bansal 1999 profile",
    "tagetes eo 10%": "tagetes minuta whole plant oil india bansal 1999 profile",
    # Owner stock "Helichrysum EO": H. italicum (immortelle) oil; origin unknown.
    # Distinct from the immortelle absolute profile.
    "helichrysum eo": "helichrysum italicum oil corsica bianchini 2001 profile",
    # Owner stock "Guaiacwood EO (exactly 1/3 w/w in ethanol + DEP ...)":
    # Bulnesia sarmientoi wood oil; no supplier SKU, origin or lot recorded.
    "guaiacwood eo": "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile",
    "guaiacwood eo (exactly 1/3 w/w in ethanol + dep; components are 1/3 guaiacwood eo + 1/3 ethanol + 1/3 dep by mass)": (
        "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile"
    ),
    # Owner stock "Rose Otto Bulgarian (10% in DPG)", PerfumersWorld 5RR12478;
    # the profile is the neat oil (dilution is handled elsewhere).
    "rose otto bulgarian": "rosa x damascena bulgarian oil iso 9842 midpoint profile",
    "rose otto bulgarian (10% in dpg)": "rosa x damascena bulgarian oil iso 9842 midpoint profile",
    # Owner stock "Haitian Vetiver EO (neat / as supplied)" (owner corrected the
    # Indian-origin label 2026-09-10).
    "haitian vetiver eo": "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile",
    "haitian vetiver eo (neat / as supplied)": "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile",
    # Owner stock "Hay Absolute (10% w/w in DPG; homogeneous)" and the V5 row
    # "Hay Absolute 10%"; the profile is the neat absolute.
    "hay absolute": "hay absolute perfumersworld 8ny00523 allergen declaration profile",
    "hay absolute (10% w/w in dpg; homogeneous)": "hay absolute perfumersworld 8ny00523 allergen declaration profile",
    "hay absolute 10%": "hay absolute perfumersworld 8ny00523 allergen declaration profile",
    # Owner stock STK-148, PerfumersWorld 5NC07544 "Orange Flower Absolute 10%
    # in DPG"; the profile is the neat absolute (PW 8NC00338).
    "orange flower absolute": "orange flower absolute perfumersworld 8nc00338 declaration profile",
    "orange flower absolute 10% in dpg": "orange flower absolute perfumersworld 8nc00338 declaration profile",
    # Owner stock inventory.txt "Frangipani Absolute (10% in DPG)", PerfumersWorld
    # 5ON09236; the profile is the neat absolute (PW 8ON00534).
    "frangipani absolute": "frangipani absolute perfumersworld 8on00534 declaration profile",
    "frangipani absolute (10% in dpg)": "frangipani absolute perfumersworld 8on00534 declaration profile",
    "frangipani absolute 10% in dpg": "frangipani absolute perfumersworld 8on00534 declaration profile",
    # Owner stock STK-122 "Fir EO 10%" (10% w/w in DPG), bought as PerfumersWorld
    # 7KG07758 (order PW-260817-03422462b); the profile is the neat oil.
    "fir essential oil": "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile",
    "fir eo": "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile",
    "fir eo 10%": "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile",
    # MySkinRecipes stocks of 27 Oct 2026 (order 2200410): STK-175 Fir Needle Oil (Canada)
    # and STK-173 Olibanum Oil, each with its own published profile.
    "fir needle oil (canada)": "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile",
    "fir needle oil canada": "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile",
    "olibanum oil": "boswellia carterii oil woolley 2012 somali average profile",
    "olibanum (frankincense) oil": "boswellia carterii oil woolley 2012 somali average profile",
    # PerfumersWorld stock of 28 Oct 2026 (order PW-261024-211206f41): STK-184 Davana
    # Essential Oil, 10% in DPG, SKU 5HH12466.
    "davana essential oil": "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile",
    "davana essential oil 10% in dpg": "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile",
    "davana eo 10%": "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile",
    "davana oil": "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile",
    # Owner stock inventory.txt "Lemon Terpeneless Oil Sicilian (neat / as
    # supplied)", PerfumersWorld 7CC24027 (order 261004-055451ce1).
    "lemon terpeneless oil sicilian": "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile",
    "lemon terpeneless oil sicilian (neat / as supplied)": "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile",
    "cabreuva eo": "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile",
    "cabreuva eo (50% w/w in dpg)": "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile",
    "cabreuva eo 50% in dpg": "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile",
    "cabreuva essential oil": "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile",
    "pine eo": "pine oil perfumersworld 7kq07511 ifra declaration profile",
    "pine essential oil": "pine oil perfumersworld 7kq07511 ifra declaration profile",
    "sandalwood eo": "santalum album oil iso 3518 midpoint profile",
    "sandalwood eo (10% in dpg)": "santalum album oil iso 3518 midpoint profile",
    "sandalwood essential oil": "santalum album oil iso 3518 midpoint profile",
    # MySkinRecipes White Sandalwood Oil (China), lot W9F536 (STK-172): Kenny 28 Oct 2026,
    # "select the one that is the closest"; S. album is the closest identity.
    "white sandalwood oil (china)": "santalum album oil iso 3518 midpoint profile",
    "white sandalwood oil china": "santalum album oil iso 3518 midpoint profile",
    "tuberlia base": "tuberalia base perfumersworld 6nd09663 declaration profile",
    "tuberalia base": "tuberalia base perfumersworld 6nd09663 declaration profile",
}

_LAVENDER_40_42_PROXY_LIMITATIONS = (
    "Aroma&More SKU Lav420811P (https://aromaandmore.com/en/essential-oil-100-pure-/67-11388-lavender-4042-essential-oil-france.html) "
    "is sold as French steam-distilled Lavandula angustifolia flower oil standardized toward a 40/42 "
    "linalool and linalyl acetate target.",
    "The supplier states the current product does not fully meet that target, that another lavender or "
    "lavandin is added to raise the linalool/linalyl acetate content, and that high-altitude lavender is "
    "also added.",
    "The composition is a 40/42-grade estimate from two other suppliers' published GC reports (Shay & "
    "Company lot 13282; Amphora Aromatics typical), not an analysis of the Aroma&More product or lot; "
    "no Aroma&More GC, certificate of analysis or density was published.",
)

_POMELO_EO_PROXY_LIMITATIONS = (
    "The owned Pomelo EO (neat; PerfumersWorld lists SKU 7CN23708) has no recorded species "
    "(Citrus maxima / C. grandis), expression-or-distillation method, origin or furocoumarin content; "
    "the reused composition is a limonene-dominant literature midpoint profile, not an analysis of "
    "the owned product or lot.",
    "CAS trap: INCI 'Citrus Grandis (Grapefruit) Peel Oil', CAS 8016-20-4, is grapefruit, not pomelo; "
    "O&3 lists CAS 90045-43-5 for its pomelo oil, unmatched to a registry entry. Neither is used as "
    "identity evidence.",
    "This headspace proxy supplies no furocoumarin assay or skin-safety clearance.",
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
    "pomelo eo": _POMELO_EO_PROXY_LIMITATIONS,
    "pomelo essential oil": _POMELO_EO_PROXY_LIMITATIONS,
    "pomelo oil": _POMELO_EO_PROXY_LIMITATIONS,
    "coriander seed eo": (
        "PerfumersWorld SKU 7SL00125 identifies coriander seed oil; the reused published "
        "seed-oil fingerprint is not a supplier-product or lot assay and does not cover leaf oil.",
    ),
    "galbanum resinoid": (
        "The owned Galbanum Resinoid (MySkinRecipes lot QM0D25) is modeled from one published commercial resinoid (Canton et al. 2025, supplied by RIFM), not from an analysis of the owned lot.",
        "The lot's refractive index (1.5200) is below a neat resinoid's 1.525-1.548 and inside the range of a grade cut with 30% Hercolyn; MySkinRecipes states no diluent, so the bottle may be diluted and the profile may overstate it.",
        "Ventos sells the liquid trade grade as 'Contains hercolyn 30%.', 'Viscous liquid', RI nd20 1.5060-1.5400 (https://www.ventos.com/index.php/en/producto/5206); the lot's 1.5200 is inside it. Fractions stay unscaled until MySkinRecipes confirms a diluent (x0.70 if 30%).",
    ),
    "fir needle oil (canada)": (
        "The owned Fir Needle Oil (Canada) (MySkinRecipes lot ECPT07, Abies balsamea per its MSDS) is modeled from range midpoints of 10 commercial Canadian oils, not from an analysis of the owned lot.",
        "Producer bands differ: the Biolandes balsam fir SDS (B847) gives alpha-pinene, delta-3-carene and limonene each 10-20% and camphene 5-10%; delta-3-carene varies by chemotype.",
    ),
    "olibanum oil": (
        "The owned Olibanum Oil (MySkinRecipes lot 3S74J8, Boswellia carterii per its MSDS) is modeled from Woolley et al. (2012) Somali B. carterii averages, not from an analysis of the owned lot; its chemotype is unknown.",
        "Johnson et al. (2019) found a B. occulta marker (1-methoxydecane) in 9 of 13 commercial 'carteri' oils, so the owned oil may not match an authentic profile.",
    ),
    "davana essential oil": (
        "The owned Davana Essential Oil (PerfumersWorld 5HH12466, 10% in DPG, no lot published) is modeled from one GC/MS report on a commercial Indian oil (Pappas, Revive lot 8F), not from an analysis of the owned bottle.",
        "The report is a named analyst's lot report, not peer reviewed; its main rows agree with the Singh et al. (2021) abstract, while Bail et al. (2008, GC-FID) found cis-davanone 45.8% and trans-ethyl cinnamate only 0.9% in a 2008 lot.",
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
    "ginger lily oil": (
        "The owned Ginger Lily Oil (PerfumersWorld 7NS25173, 1 g) is modeled as Hedychium spicatum rhizome oil, the closest identity: PW gives no species, CAS or composition, and Kenny's strip test reads ginger root (28 Oct 2026: 'Ginger root, check on msr'). The candidates it rules out are H. coronarium flower absolute and flower oil.",
    ),
    "ginger lily": (
        "The owned Ginger Lily Oil (PerfumersWorld 7NS25173, 1 g) is modeled as Hedychium spicatum rhizome oil, the closest identity: PW gives no species, CAS or composition, and Kenny's strip test reads ginger root (28 Oct 2026: 'Ginger root, check on msr'). The candidates it rules out are H. coronarium flower absolute and flower oil.",
    ),
    "ginger lily eo": (
        "The owned Ginger Lily Oil (PerfumersWorld 7NS25173, 1 g) is modeled as Hedychium spicatum rhizome oil, the closest identity: PW gives no species, CAS or composition, and Kenny's strip test reads ginger root (28 Oct 2026: 'Ginger root, check on msr'). The candidates it rules out are H. coronarium flower absolute and flower oil.",
    ),
    "ginger lily essential oil": (
        "The owned Ginger Lily Oil (PerfumersWorld 7NS25173, 1 g) is modeled as Hedychium spicatum rhizome oil, the closest identity: PW gives no species, CAS or composition, and Kenny's strip test reads ginger root (28 Oct 2026: 'Ginger root, check on msr'). The candidates it rules out are H. coronarium flower absolute and flower oil.",
    ),
    "magnolia absolute": (
        "The owned Magnolia Absolute (MySkinRecipes #7870, lot ZDHY6L) is modeled as Magnolia officinalis flower, the identity the INCI on its MySkinRecipes page names (Kenny, 28 Oct 2026: 'magnolia abolute takje the INCI on the mykinrecipe page'); MySkinRecipes prints no CAS, origin, extraction solvent, composition or density.",
        "No GC of a Magnolia officinalis flower absolute or solvent extract was found; the only quantified composition is the pharmacopoeial hydrodistilled oil of dried buds, which is caryophyllene-rich. The same INCI is on MySkinRecipes' cosmetic extract 7871, so if the bottle smells sweet-floral the name may be carried over and Michelia x alba would fit better.",
    ),
    "cedarwood chinese essential oil": (
        "The owned China cedarwood (V5 row 62, species never stated) is modeled as Chinese cedarwood oil, Cupressus funebris wood oil, the closest identity under Kenny's 28 Oct 2026 rule ('select the one that is the closest'). Robertet sells 'Cedarwood China oil' as Cupressus funebris (https://matieres-premieres.robertet.com/cedarwood-china-oil); The Good Scents Company lists 'cedarwood oil china' as cupressus funebris wood oil, CAS 85085-29-6 (https://www.thegoodscentscompany.com/data/es1007241.html). Supplier and lot are not recorded.",
    ),
    "white sandalwood oil (china)": (
        "The owned White Sandalwood Oil (China) (MySkinRecipes lot W9F536) is modeled as Santalum album oil, the closest identity Kenny asked for on 28 Oct 2026: its name and the COA's nominal density (0.980, inside ISO 3518) point to S. album. MySkinRecipes prints no GC.",
        "Runner-up is S. spicatum, whose CAS 8024-35-9 the COA prints; that oil has about 21% (Z)-alpha-santalol and 10% farnesol instead of 48% and trace, so the santalol rows would be too high. The COA's nominal RI 1.500 is below ISO 3518's 1.503 and the price is far below genuine oil, so the bottle may be cut or compounded.",
    ),
    "guaiacwood eo": (
        "The owned Guaiacwood EO has no supplier SKU, origin or lot record; the reused composition is one published Argentine wood-oil GC-MS, not an analysis of that bottle.",
    ),
    "rose otto bulgarian": (
        "The owned Rose Otto Bulgarian (PerfumersWorld 5RR12478) is modeled from ISO 9842 range midpoints reprinted on a supplier certificate, not from an analysis of that lot.",
    ),
    "haitian vetiver eo": (
        "The owned Haitian Vetiver EO is modeled from one supplier lot certificate (Amrita 5101-LCAA), not from an analysis of the owned bottle.",
    ),
    "hay absolute": (
        "The owned Hay Absolute is modeled from PerfumersWorld 8NY00523 declared allergen levels (about 1.8% of the absolute); the bought SKU is unverified.",
    ),
    "orange flower absolute": (
        "The owned Orange Flower Absolute (PerfumersWorld 5NC07544, 10% in DPG) is modeled from PerfumersWorld's declared levels for the neat absolute 8NC00338 (about 15.1% of it), not from an analysis of the owned lot.",
    ),
    "frangipani absolute": (
        "The owned Frangipani Absolute (PerfumersWorld 5ON09236, 10% in DPG) is modeled from PerfumersWorld's declared levels for the neat absolute 8ON00534 (about 12.2% of it), not from an analysis of the owned lot.",
    ),
    "fir essential oil": (
        "The owned Fir EO (PerfumersWorld 7KG07758, held as 10% w/w in DPG) is modeled as balsam fir needle oil: PW does not name the species, which is inferred from its CAS 8021-28-1 and limonene level.",
    ),
    "lemon terpeneless oil sicilian": (
        "The owned Lemon Terpeneless Oil Sicilian (PerfumersWorld 7CC24027, neat) is modeled as citral at 45%, the midpoint of the British Pharmacopoeia grade's 40-50%; PW publishes no composition, so this is an estimate of the grade, not of the owned lot.",
    ),
}


_PROFILE_KEY_LIMITATIONS: dict[str, tuple[str, ...]] = {
    "tuberose absolute": (
        "The Eden Botanicals lot 966 COA these rows cite could not be found online (2026-10-28 "
        "search). The only other quantitative list for a commercial absolute, Petrzilka and Ehret "
        "(1991) as reproduced by Lawrence (Perfumer & Flavorist 29, 2004), gives methyl palmitate "
        "14.5, methyl benzoate 12.2, benzyl benzoate 10.4, ethyl oleate 5.3, alpha-terpineol 4.0, "
        "1,8-cineole 3.8, methyl salicylate 3.6, farnesol 3.5, methyl anthranilate 2.4 and methyl "
        "eugenol 2.2%, with no method printed. Methyl benzoate, alpha-terpineol, cineole and methyl "
        "anthranilate are missing here, jasmolactone (7.3%) and delta-decalactone (4.4%) are above "
        "that source's 0.1-1.0%, and methyl isoeugenol (23.4%) is not among its majors, so these "
        "rows stay a legacy lot reading until a current analysis is found.",
    ),
    "labdanum absolute": (
        "No published analysis of a labdanum absolute supports these rows: the 12% alpha-pinene "
        "and 6% labdanolic acid follow Weyerstahl 1998, an oil study. A 2026-10-27 search found "
        "no quantitative GC of a commercial absolute (Greche 2008 reports % within fractions of a "
        "lab ethanol extract), so the legacy rows stay until one is found.",
    ),
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
    "cupressus funebris wood oil tgsc typical gc profile": (
        "https://www.thegoodscentscompany.com/gca/gc1007241.html",
        "https://www.thegoodscentscompany.com/data/es1007241.html",
        "https://matieres-premieres.robertet.com/cedarwood-china-oil",
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
    "rum ether efsa fge500 company 2 scenario profile": (
        "https://doi.org/10.2903/j.efsa.2017.4897",
        "https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf",
    ),
    "citrus sinensis sweet orange iso 3140 2019 midpoint profile": (
        "https://cdn.standards.iteh.ai/samples/74546/29e56c6708e14f9996fc5bda21efc05b/ISO-3140-2019.pdf",
        "https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf",
        "https://thegoodscentscompany.com/data/es1030852.html",
    ),
    "lemon fcf oil sicilian": ("https://pubmed.ncbi.nlm.nih.gov/28231199/",),
    "neroli eo": ("https://pubmed.ncbi.nlm.nih.gov/24163946/",),
    "ginger eo": ("https://pubmed.ncbi.nlm.nih.gov/21366054/",),
    "galbanum eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10474915/",),
    "frankincense eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10603989/",),
    "clove eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10058340/",),
    "black pepper eo": (
        "https://doi.org/10.1016/j.talanta.2014.01.007",
    ),
    "red mandarin eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10985240/",),
    "eucalyptus essential oil": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10004840/",),
    "clary sage eo": ("https://pmc.ncbi.nlm.nih.gov/articles/PMC10049179/",),
    "tonka bean solvent extract literature profile": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12840717/",
    ),
    "roasted coffee oil literature profile": (
        "https://doi.org/10.3390/foods12132515",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8346979/",
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
    "lavender 40/42 grade two published gc midpoint profile": (
        "https://shayandcompany.com/wp-content/uploads/2018/08/Lavender-40-42-Essential-Oil-GCMS-Shay-and-Company-Lot13282.pdf",
        "https://www.amphora-aromatics.com/images/product/Lavender%2040_42%20Typical%20GC%20-%2026BLEND40_42.pdf",
        "https://aromaandmore.com/en/essential-oil-100-pure-/67-lavender-4042-essential-oil-france.html",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC9182314",
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
    "citrus maxima peel oil limonene-dominant literature midpoint profile": (
        "https://iris.unime.it/handle/11570/1892862",
        "https://www.doi.org/10.14233/AJCHEM.2020.22234",
        "https://journal.library.du.ac.bd/index.php/dujs/article/view/441/421",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC9720520",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7936692",
        "https://www.cir-safety.org/sites/default/files/cpeelo092014FR.pdf",
        "https://www.oand3.com/product/pomelo-essential-oil/",
    ),
    "magnolia officinalis flos essential oil liu 2025 stage s1 profile": (
        "https://doi.org/10.5650/jos.ess25113",
        "https://www.jstage.jst.go.jp/article/jos/74/10/74_ess25113/_pdf",
        "https://www.myskinrecipes.com/shop/en/absolute-solvent-extract/7870-magnolia-officinalis-flower-extract.html",
    ),
    "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC11576735/",
        "https://doi.org/10.1038/s41598-024-79712-5",
        "https://www.thegoodscentscompany.com/data/es1067151.html",
    ),
    "michelia alba flower oil punjee 2009 steam distillation profile": (
        "https://li01.tci-thaijo.org/index.php/anres/article/view/244814",
        "https://li01.tci-thaijo.org/index.php/anres/article/download/244814/167282",
        "https://thegoodscentscompany.com/data/es1068501.html",
    ),
    "champaca flower oil perfumersworld 7nj07740 ifra declaration profile": (
        "https://www.perfumersworld.com/ifra/IFRA/IFRA_7NJ07740.pdf",
        "https://www.perfumersworld.com/view.php?pro_id=7NJ07740",
    ),
    "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile": (
        "https://www.perfumersworld.com/view.php?pro_id=2QV00363",
        "https://keele-repository.worktribe.com/OutputFile/459690",
    ),
    "ocimum basilicum oil india estragole type supplier gc profile": (
        "https://cdn.shopify.com/s/files/1/1277/1723/files/Basil_Sweet_Essential_Oil_India_GC.pdf",
        "https://scent.vn/en/pages/oil/basil-india-1295",
        "https://cdn.standards.iteh.ai/samples/19023/cff9800fd51d45149a8e27345adaa0bf/ISO-11043-1998.pdf",
    ),
    "tagetes minuta whole plant oil india bansal 1999 profile": (
        "https://scent.vn/en/pages/oil/tagetes-india-6a-whole-plant-3230",
    ),
    "helichrysum italicum oil corsica bianchini 2001 profile": (
        "https://scent.vn/en/pages/oil/helichrysum-italicum-france-corsica-3417",
        "https://scent.vn/en/pages/oil/helichrysum-italicum-croatia-1a-2722",
    ),
    "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile": (
        "https://www.redalyc.org/journal/428/42862466009/42862466009.pdf",
        "Enriquez M.B., Orrabalis C.J. (2019) Multequina 28:59-66, Table 1",
    ),
    "rosa x damascena bulgarian oil iso 9842 midpoint profile": (
        "https://gigaplus.makeshop.jp/aromastore/images/download/N1507G25.pdf",
        "https://gigaplus.makeshop.jp/aromastore/images/download/N1507G26.pdf",
    ),
    "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile": (
        "https://www.amrita.net/content/product_files/CoA%20-%20EO5101%20Vetiver%20%28Organic%29%20LCAA%201-2-25.pdf",
    ),
    "hay absolute perfumersworld 8ny00523 allergen declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=8NY00523&tab=allergen",
    ),
    "orange flower absolute perfumersworld 8nc00338 declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=8NC00338",
        "https://www.perfumersworld.com/document-list.php?pro_id=5NC07544",
    ),
    "frangipani absolute perfumersworld 8on00534 declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=8ON00534",
        "https://www.perfumersworld.com/document-list.php?pro_id=5ON09236",
    ),
    "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile": (
        "https://journals.sagepub.com/doi/10.1177/1934578X221086901",
        "https://biolandes.com/wp-content/uploads/fiche-securite-B847.pdf",
    ),
    "boswellia carterii oil woolley 2012 somali average profile": (
        "https://doi.org/10.1016/j.chroma.2012.06.073",
        "https://www.mdpi.com/2223-7747/8/4/88",
    ),
    "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile": (
        "https://www.revive-eo.com/wp-content/uploads/2025/01/REVIVE-GCMS-Report-Davana-Oil-India-8F.pdf",
        "https://doi.org/10.1002/cbdv.202100531",
        "https://journals.sagepub.com/doi/10.1177/1934578X0800300705",
    ),
    "ferula galbaniflua resinoid canton 2025 volatile fraction profile": (
        "https://doi.org/10.1002/cbdv.202501442",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12715999/",
    ),
    "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=7KG07758",
        "https://www.biolandes.com/en/?p=43796",
        "https://www.canadianfloraessentialoils.com/_files/ugd/b15383_6c6f440923c8412aa4f8e32603cb7210.pdf",
    ),
    "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=7CC24027",
        "https://www.perfumersworld.com/view.php?pro_id=7CC24027",
        "https://www.sciencedirect.com/topics/medicine-and-dentistry/lemon-oil",
    ),
    "lime distilled eo": (
        "https://www.tomsic.co.jp/wp-content/themes/tomsic/images/product/mega/32.pdf",
        "https://www.perfumersworld.com/document-list.php?pro_id=7CK00274",
    ),
    "rose essential oil": (
        "https://asianpubs.org/index.php/ajchem/article/download/18212/18162/18291",
    ),
    "rose de mai absolute": (
        "https://www.planttherapy.com/cdn/shop/files/Rose_R30111.pdf",
    ),
    "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=7LW00863",
        "https://beilstein-journals.org/bjoc/articles/13/84",
        "https://www.alpacasa.com/wp-content/uploads/2024/05/DIN-PROD-017.-Ficha-tecnica.-Cabreuva-Oil-60-89_WEB.pdf",
    ),
    "pine oil perfumersworld 7kq07511 ifra declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=7KQ07511",
    ),
    "santalum album oil iso 3518 midpoint profile": (
        "https://cdn.standards.iteh.ai/sist-preview/88588/1b7516dd3de5489a8752a4f51f66838c/ISO-3518-2025.pdf",
        "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/11031-45-1.pdf",
        "https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0",
    ),
    "tuberalia base perfumersworld 6nd09663 declaration profile": (
        "https://www.perfumersworld.com/document-list.php?pro_id=6ND09663",
    ),
    "patchouli eo": (
        "https://onlinelibrary.wiley.com/doi/full/10.1002/ffj.3418",
    ),
    "styrax tonkinensis resin jecfa 2011 mean profile": (
        "https://www.fao.org/fileadmin/user_upload/agns/pdf/jecfa/cta/74/benzoe_tonkinensis.pdf",
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
            "(S)-carvone": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://pubchem.ncbi.nlm.nih.gov/compound/16724",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/6485-40-1.pdf",
                "vp_conversion": "0.07 mm Hg at 20 C (FMA, d-carvone column) = 9.33 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 14.25 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Blank & Grosch (1991a), (S)-(+)-carvone, as compiled in van Gemert (2011) AIR section; no detection/recognition flag printed",
                "odt_conversion": "0.03 mg/m3 x 24450 / 150.22 = 4.883 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
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
            "96.0% of nominal composition is modeled (carvone, limonene and myrcene). cis-Dihydrocarvone and the carveols remain uncomputed, not odorless.",
            "Carvone's 25 C vapour pressure is converted from a 20 C FMA figure, and its air threshold is a single compiled value (Blank & Grosch 1991a, detection or recognition not stated).",
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
    "citrus sinensis sweet orange iso 3140 2019 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.standards.iteh.ai/samples/74546/29e56c6708e14f9996fc5bda21efc05b/ISO-3140-2019.pdf",
                "document": "ISO 3140:2019 Essential oil of sweet orange expressed [Citrus sinensis (L.)]",
                "table": "Table 2, Chromatographic profile",
                "published_botanical_name": "Citrus sinensis (L.)",
                "published_type": "Expressed whole oil",
                "standard_range_pct": {
                    "alpha pinene": (0.4, 0.8), "beta pinene": (0.02, 0.15), "sabinene": (0.2, 1.0),
                    "myrcene": (1.5, 3.5), "limonene": (93.0, 96.0), "octanal": (0.1, 0.6),
                    "nonanal": (0.01, 0.1), "decanal": (0.1, 0.7), "linalool": (0.15, 0.7),
                    "neral": (0.03, 0.1), "valencene": (0.01, 0.4), "geranial": (0.05, 0.2),
                    "beta-sinensal": (0.01, 0.06),
                },
                "owned_lot_limonene_pct": 95.28,
                "fraction_rule": "COA_LIMONENE_PLUS_STANDARD_MIDPOINTS_SCALED_0_8725",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "COA_LIMONENE_ONLY",
                "owned_stock_label": "Sweet Orange Essential Oil (STK-112, label 'China, Sour')",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ('limonene', 'myrcene', 'alpha pinene', 'sabinene', 'linalool', 'decanal', 'octanal', 'geranial', 'beta pinene', 'neral', 'nonanal')},
        },
        "unresolved_constituents": (
            {"name": "valencene", "reported_fraction": 0.0018, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "Only limonene comes from Kenny's COA; the ten minor rows are ISO 3140 range midpoints scaled to fill the volatiles, not an analysis of his lot.",
            "The 23 ppb whole-oil threshold assumes additive odour units; octanal carries a third of it and its two measured air values differ 17x (0.17 and 0.010 ppb), so the threshold may be as low as 3.6 ppb.",
            "99.8% is modeled; valencene (0.18%) and beta-sinensal have no runtime input and are uncomputed, not odorless. Nothing is renormalized.",
        ),
    },
    "rum ether efsa fge500 company 2 scenario profile": {
        "analytical_method": "REGULATORY_ASSESSMENT_GC_FID_PRODUCER_BATCHES",
        "composition_basis": "PRODUCER_BATCH_MEAN_WHOLE_PRODUCT_SCENARIO_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "EFSA CEF Panel (2017) Scientific Opinion on Flavouring Group Evaluation 500 (FGE.500): rum ether. EFSA Journal 15(8):4897, doi:10.2903/j.efsa.2017.4897, per-producer composition table, Company 2",
                "company_2_dry_pct": {
                    "ethanol": (41.23, 42.97, 43.55), "ethyl acetate": (44.99, 44.01, 43.21),
                    "ethyl formate": (10.49, 9.66, 9.96), "ethyl propionate": (1.45, 1.67, 1.62),
                    "ethyl butyrate": (0.16, 0.19, 0.17), "ethyl crotonate": (0.16, 0.19, 0.17),
                },
                "company_2_water_pct": (10.14, 9.83, 8.79),
                "fraction_rule": "MEAN_OF_THREE_BATCH_SETS_TIMES_ONE_MINUS_MEAN_WATER_0_0959",
                "selection_rule": "DENSITY_MATCH_TO_OWNED_COA_0_8644_0_8804",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Rum Ether (STK-109, MySkinRecipes 2805 lot QI71T6, neat)",
            },
            **{name: {
                "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Nagata 2003 Table 2, triangle odor bag",
                "vp_status": "PUBLISHED_EXPERIMENTAL_VP_HSDB",
                "gamma_status": "IDEAL_MIXING_ASSUMED",
                "owned_oil_activity_measured": False,
            } for name in ("ethanol", "ethyl acetate", "ethyl formate", "ethyl propionate", "ethyl butyrate")},
        },
        "unresolved_constituents": (
            {"name": "water", "reported_fraction": 0.0959, "missing_input": "ODORLESS_SOLVENT_NOT_A_ROW", "odor_contribution": "UNCOMPUTED"},
            {"name": "ethyl crotonate", "reported_fraction": 0.00157, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "unidentified remainder", "reported_fraction": 0.0125, "missing_input": "NOT_QUANTIFIED_FOR_THIS_PRODUCT", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "A producer-type scenario chosen by density, not a GC of lot QI71T6: EFSA batches range ethanol 27-83% and ethyl acetate 2-49%; a Company 1-type lot (more ethanol, ethyl valerate/isovalerate 1.1-1.6%) would be about 10x more potent and more berry-fruity.",
            "Ideal mixing (gamma 1.0); esters in ethanol deviate positively, so ester headspace and potency are probably underestimated.",
            "Acetic acid, guaiacol, vanillin and ethyl acrylate (the burnt-woody, whiskey facet) are not quantified for Company 2 and are uncomputed, not odorless. Nothing is renormalized.",
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
    "citrus maxima peel oil limonene-dominant literature midpoint profile": {
        "analytical_method": "PUBLISHED_GC_PROFILES_CROSS_SOURCE_RANGE",
        "composition_basis": "LITERATURE_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "literature:cross-source midpoints of sources A-C as compiled in the 2026-10-13 new-stock research note (section 1.5)",
                "documents": (
                    "A: Mondello, Dugo, Cavazza, Dugo 1996, J. Essent. Oil Res. 8:311-314, C. grandis cv. Chandler oil (abstract; limonene 93.83%)",
                    "B: Asian J. Chem. 2020, doi:10.14233/AJCHEM.2020.22234, C. grandis, Ben Tre, Vietnam, hydro/steam distilled (abstract)",
                    "C: Dhaka Univ. J. Sci., C. maxima peel, Chittagong, hydrodistilled (Clevenger), DB-5ms (page)",
                ),
                "published_type": "Peel oil; sources B and C distilled, source A method not stated on the page read",
                "reported_range_pct": {
                    "limonene": (92.72, 96.49),
                    "myrcene": (1.644, 2.42),
                    "alpha pinene": (0.58, 0.686),
                    "beta pinene": (0.248, 0.248),
                    "alpha phellandrene": (0.793, 0.793),
                    "ocimene": (0.138, 0.29),
                },
                "fraction_rule": "MIDPOINT_OF_CROSS_SOURCE_MIN_MAX_SINGLE_VALUE_WHERE_ONE_SOURCE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_reference": "PerfumersWorld 7CN23708 (supplier page not found or read)",
                "owned_species_recorded": False,
                "owned_extraction_method_recorded": False,
                "owned_furocoumarin_content_recorded": False,
                "owned_bottle_sku_verified": False,
                "cas_identity_note": (
                    "CAS 8016-20-4 (INCI Citrus Grandis (Grapefruit) Peel Oil) is grapefruit, not pomelo; "
                    "O&3 lists 90045-43-5 for pomelo oil. Neither is used as identity evidence."
                ),
                "excluded_hydrodistilled_oxygenates_pct": {
                    "linalool": 6.5,
                    "citral (neral + geranial)": 6.0,
                    "nootkatone": 3.4,
                },
                "furocoumarin_evidence_text_only": (
                    "Li et al. 2021, Drug Des. Devel. Ther. 15:937-947, doi:10.2147/DDDT.S299678 (C. grandis "
                    "Liangping cultivar, HPLC): cold-pressed oil isoimperatorin about 350 mg/L, oxypeucedanin "
                    "about 110 mg/L, epoxybergamottin about 85 mg/L; bergapten, psoralen and xanthotoxin not "
                    "found. One cultivar; not converted to % w/w; no safety or IFRA-compliance claim is made."
                ),
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("limonene", "myrcene", "alpha phellandrene", "alpha pinene",
                            "beta pinene", "ocimene")},
        },
        "limitations": (
            "Literature proxy from published pomelo peel-oil GC profiles; it is not an analysis of the owned bottle, and the owned oil's species, extraction method and lot are unrecorded.",
            "Two of the three limonene-dominant sources are distilled oils; the one cold-pressed profile found (pomelo cv. Guan Xi, PMC6359654: limonene 55.92%, myrcene 31.17%) and an oxygenated hydrodistilled profile (Das et al. 2022, PMC9720520: limonene 67.58-73.82%) disagree strongly and are not modeled.",
            "Linalool (about 6.5%), citral (about 6.0%) and nootkatone (about 3.4%) are reported only for hydrodistilled pomelo oil (Das et al. 2022) and are not added to this limonene-dominant profile; they remain an allergen/oxygenate sensitivity scenario, not part of the modeled headspace.",
            "Only 98.511% of nominal composition is modeled; selinene, germacrene D and lilac alcohol (reported in one source) and the unidentified remainder have no runtime headspace input and remain uncomputed, not odorless.",
            "alpha-Phellandrene reuses the Schinus class row and ocimene the generic ocimene row; ocimene isomers are not distinguished.",
            "Cold-pressed pomelo oil contains furocoumarins (Li et al. 2021: isoimperatorin about 350, oxypeucedanin about 110, epoxybergamottin about 85 mg/L; bergapten not detected); this profile does not model them and makes no safety or IFRA-compliance claim.",
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
            "(R)-carvone": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://pubchem.ncbi.nlm.nih.gov/compound/439570",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/6485-40-1.pdf",
                "vp_conversion": "0.1 mm Hg at 20 C (FMA, l-carvone column) = 13.33 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 20.16 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Amoore (1982) detection, (R)-(-)-carvone, as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "0.034 mg/m3 x 24450 / 150.22 = 5.534 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
            "alpha-terpinene": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://webbook.nist.gov/cgi/cbook.cgi?ID=C99865",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/99-86-5.pdf",
                "vp_conversion": "0.5 mm Hg at 20 C (FMA) = 66.66 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 96.6 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Cometto-Muniz JE, Cain WS, Abraham MH, Kumarsingh R (1998) Pharmacol Biochem Behav 60:765-770, doi:10.1016/s0091-3057(98)00054-9, detection, as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "7.9 mg/m3 x 24450 / 136.234 = 1418 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
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
            "Only 49.7% of the oil is modeled. Published Canarium oils report elemol, elemicin and alpha-phellandrene as major constituents (for example Galovičová et al. 2020, Potravinarstvo 14:1088-1096, doi:10.5219/1490: d-limonene 36.4, elemol 16.7, alpha-phellandrene 12.2, elemicin 9.59 TIC area %); these remain uncomputed, not odorless.",
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
    "lavender 40/42 grade two published gc midpoint profile": {
        "analytical_method": "PUBLISHED_GC_PROFILES_CROSS_SOURCE_RANGE",
        "composition_basis": "LITERATURE_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "literature:midpoints of two published Lavender 40/42 GC reports (sources A-B)",
                "documents": (
                    "A: Shay & Company, Lavender 40/42 Essential Oil, lot 13282, France, steam distilled, GC-MS (Shimadzu QP2010 Ultra, ZB-5), analysed 15 Nov 2024; total identified 99.69%",
                    "B: Amphora Aromatics, Lavender Essential Oil 40-42 Blend, typical batch, GC-MS (Rxi-1ms), version 01, 1 May 2023; ten listed peaks",
                ),
                "published_type": "Lavender 40/42 trade grade, steam-distilled flower oil",
                "reported_range_pct": {
                    "linalyl acetate": (38.36, 40.7),
                    "linalool": (36.56, 38.1),
                    "terpinen-4-ol": (0.8, 6.2),
                    "camphor": (3.2, 3.4),
                    "1,8-cineole": (3.03, 3.1),
                    "limonene": (0.45, 3.5),
                    "beta-caryophyllene": (0.72, 2.5),
                    "borneol": (1.3, 1.72),
                    "lavandulyl acetate": (0.5, 1.27),
                    "ocimene": (0.5, 0.93),
                },
                "ocimene_rule": "SOURCE_A_CIS_PLUS_TRANS_0_49_PLUS_0_44_SOURCE_B_CIS_ONLY",
                "fraction_rule": "MIDPOINT_OF_CROSS_SOURCE_MIN_MAX",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_supplier_reference": "Aroma&More Lav420811P (supplier page read 25 Oct 2026; no GC, COA or density published)",
                "supplier_grade_statement": (
                    "Aroma&More: the 40/42 grade 'does not quite meet the 40/42 standard'; 'another species of "
                    "Lavender or Lavandin has been added to raise the linalyl/linalool content'; 'We also add a "
                    "premium quality high altitude Lavender'; no synthetics added or detected."
                ),
                "true_lavender_contrast": (
                    "ISO 3515:2002 French lavender: camphor <0.5%, 1,8-cineole <1%, lavandulyl acetate >1% "
                    "(Ph. Eur. camphor <1.2%, 1,8-cineole <2.5%); ISO 8902:2009 lavandin Grosso: camphor 6-8%, "
                    "1,8-cineole 4-7% (as cited in PMC9182314). Evidence text only, not modeled."
                ),
                "owned_bottle_sku_verified": True,
                "owned_lot_recorded": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("linalyl acetate", "linalool", "terpinen-4-ol", "camphor", "1,8-cineole",
                            "limonene", "beta-caryophyllene", "borneol", "lavandulyl acetate", "ocimene")},
        },
        "limitations": (
            "Estimate of the 40/42 trade grade from two other suppliers' published GC reports; it is not an analysis of the owned Aroma&More bottle, whose lot and lavandin share are unrecorded.",
            "The two sources disagree most on terpinen-4-ol (0.8-6.2%), limonene (0.45-3.5%) and beta-caryophyllene (0.72-2.5%); midpoints are nominal model inputs.",
            "Source B is a typical, not lot, analysis listing ten peaks; constituents it omits (3-octanone, myrcene, trans-beta-farnesene, geranyl acetate, lavandulol, alpha-terpineol, each under 1% in source A) are not modeled.",
            "Only 93.42% of nominal composition is modeled; the remainder has no runtime headspace input and stays uncomputed, not odorless.",
            "Ocimene isomers are not distinguished; the generic ocimene row is reused.",
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
    "cupressus funebris wood oil tgsc typical gc profile": {
        "input_authority": {
            "composition": {
                "source": "https://www.thegoodscentscompany.com/gca/gc1007241.html",
                "table": "Typical G.C. analysis, cedarwood oil china",
                "published_botanical_name": "Cupressus funebris",
                "published_plant_part": "wood",
                "quantitation": "TYPICAL_GC_AREA_PERCENT",
                "identification": "AS_PUBLISHED_BY_TGSC_CITING_ADAMS",
                "response_factor_correction": "UNSPECIFIED_IN_SOURCE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CLOSEST_IDENTITY_PROXY",
                "owned_bottle_sku_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("thujopsene", "alpha cedrene", "cedrol", "widdrol", "beta cedrene", "cuparene")},
        },
        "limitations": (
            "A typical analysis compiled by The Good Scents Company (citing Adams), not an analysis of the owned bottle; the bottle's species was never stated and Cupressus funebris is the closest-identity proxy.",
            "GC area percent with unspecified response factors; only 88.0% of the typical composition is modeled (alaskene, chamigrenes, selinenes, himachalenes, methyl chavicol and traces are not).",
            "Constituent vapour pressures and thresholds are the legacy runtime estimates shared with the Virginia cedarwood profile.",
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
    "magnolia officinalis flos essential oil liu 2025 stage s1 profile": {
        "analytical_method": "PUBLISHED_GC_PROFILE_HYDRODISTILLED_OIL",
        "composition_basis": "GC_MS_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "Liu Z-Y, Wang X-Y, Cheng Q-Q, Wang S, Wu Y, Guo T-Y, Miao W-J, Hu M-L. Assessment of Quality in Essential Oil from Magnolia officinalis flos at Different Developmental Stages by Anatomy, GC-MS, and Chemometric Methods. J Oleo Sci 2025;74(10):915-927, doi:10.5650/jos.ess25113, Table 3 column S1",
                "reported_pct": {
                    "linalool": 1.67,
                    "borneol": 1.42,
                    "alpha terpineol": 0.43,
                    "geraniol": 1.45,
                    "bornyl acetate": 2.52,
                    "alpha-cubebene": 0.22,
                    "geranyl butyrate": 1.48,
                    "beta caryophyllene": 30.07,
                    "trans-alpha-bergamotene": 1.28,
                    "1,4,7-cycloundecatriene, 1,5,9,9-tetramethyl-, (1Z,4Z,7Z)-": 3.79,
                    "trans-beta-farnesene": 1.06,
                    "beta-selinene": 4.19,
                    "alpha-selinene": 4.1,
                    "(Z,E)-alpha-farnesene": 2.24,
                    "alpha-muurolene": 0.39,
                    "cis-calamenene": 4.6,
                    "caryophyllene oxide": 18.72,
                    "humulene-1,2-epoxide": 2.09,
                    "T-cadinol": 2.19,
                    "copaene": 0.4,
                    "2-(4a,8-dimethyl-2,3,4,5,6,8a-hexahydro-1H-naphthalen-2-yl)propan-2-ol": 0.24,
                    "neointermedeol": 1.82,
                    "alpha-cadinol": 0.93,
                    "cadalene": 0.43,
                    "methyl linolenate": 0.34,
                },
                "reported_total_pct": 88.81,
                "unitemized_pct": 0.74,
                "sample": "essential oil hydrodistilled (Chinese Pharmacopoeia Method A) from M. officinalis flower buds dried at 60 C, stage S1 (bud length 4.1-6.0 cm), Hubei, China; peak-area normalization",
                "species": "Magnolia officinalis, the identity the INCI on MySkinRecipes product 7870 names (Kenny, 28 Oct 2026: 'magnolia abolute takje the INCI on the mykinrecipe page')",
                "species_asserted_by_supplier": True,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Magnolia Absolute (STK-170, neat as supplied)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "MySkinRecipes #7870, order 2200410, lot ZDHY6L, 5 g",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("beta caryophyllene", "caryophyllene oxide", "bornyl acetate", "linalool", "geraniol", "borneol", "trans-beta-farnesene", "alpha terpineol")},
        },
        "unresolved_constituents": (
            {"name": "cis-calamenene", "reported_fraction": 0.046, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "beta-selinene", "reported_fraction": 0.0419, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-selinene", "reported_fraction": 0.041, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "1,4,7-cycloundecatriene, 1,5,9,9-tetramethyl-, (1Z,4Z,7Z)-", "reported_fraction": 0.0379, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(Z,E)-alpha-farnesene", "reported_fraction": 0.0224, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "T-cadinol", "reported_fraction": 0.0219, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "humulene-1,2-epoxide", "reported_fraction": 0.0209, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "neointermedeol", "reported_fraction": 0.0182, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "geranyl butyrate", "reported_fraction": 0.0148, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "trans-alpha-bergamotene", "reported_fraction": 0.0128, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-cadinol", "reported_fraction": 0.0093, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "cadalene", "reported_fraction": 0.0043, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "copaene", "reported_fraction": 0.004, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-muurolene", "reported_fraction": 0.0039, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "methyl linolenate", "reported_fraction": 0.0034, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "2-(4a,8-dimethyl-2,3,4,5,6,8a-hexahydro-1H-naphthalen-2-yl)propan-2-ol", "reported_fraction": 0.0024, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-cubebene", "reported_fraction": 0.0022, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "Composition is the published hydrodistilled oil of oven-dried M. officinalis flower buds (stage S1), not an analysis of the owned lot and not a solvent absolute; the absolute's non-volatile share is unknown, so nothing is scaled or renormalized.",
            "57.34% is modeled; 30.73% is printed but has no runtime input, 0.74% is not itemized and four trace rows (<0.20%) carry no value. Later stages shift beta-caryophyllene (30.07 to 17.31%) to its oxide (18.72 to 33.81%).",
        ),
    },
    "michelia alba flower oil punjee 2009 steam distillation profile": {
        "analytical_method": "PUBLISHED_GC_MS_STEAM_DISTILLED_OIL",
        "composition_basis": "GC_MS_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://li01.tci-thaijo.org/index.php/anres/article/view/244814",
                "document": "Punjee P. et al. (2009) Scented extracts and essential oil extraction from Michelia alba D.C. Kasetsart J. (Nat. Sci.) 43(5):197-203, Table 2, steam distillation",
                "published_botanical_name": "Michelia alba D.C.",
                "published_type": "Steam-distilled essential oil of fresh flowers (Thailand)",
                "reported_pct": {
                    "methyl 2-methylbutyrate": 1.31,
                    "ethyl 2-methylbutyrate": 1.47,
                    "linalool": 91.74,
                    "beta-elemene": 1.42,
                    "methyl eugenol": 1.36,
                    "beta-caryophyllene": 1.00,
                    "alpha-humulene": 0.30,
                    "germacrene D": 0.82,
                    "beta-selinene": 0.59,
                },
                "reported_sum_pct": 100.01,
                "other_distillations_in_same_table": {
                    "water distillation": {"linalool": 85.78, "methyl eugenol": 3.59},
                    "water-steam distillation": {"linalool": 83.38, "methyl eugenol": 2.04},
                },
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Magnolia EO (neat / as supplied)",
                "owned_species": "Michelia alba (owner-confirmed; Kenny 28 Oct 2026)",
                "owned_supplier_reference": "Shopee shop True Industry",
                "owned_plant_part_recorded": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("linalool", "methyl eugenol", "beta caryophyllene", "germacrene d")},
        },
        "unresolved_constituents": (
            {
                "name": "methyl 2-methylbutyrate",
                "reported_fraction": 0.0131,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "ethyl 2-methylbutyrate",
                "reported_fraction": 0.0147,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-elemene",
                "reported_fraction": 0.0142,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-humulene",
                "reported_fraction": 0.003,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-selinene",
                "reported_fraction": 0.0059,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is one published Thai flower distillation (Punjee et al. 2009), not an analysis of the owned Shopee True Industry bottle; plant part and process of the owned oil are not recorded (steam-distilled flower oil is assumed).",
            "Only nine peaks were reported, so trace odorants are missing and the percentages are shares of the identified peaks. 94.92% is modeled; five constituents (5.09%, including the fruity methyl and ethyl 2-methylbutyrate) are uncomputed, not odorless. Nothing is renormalized.",
            "The same paper's water distillation gives more methyl eugenol (3.59%); IFRA uses that higher value.",
            "Michelia alba flower oil is non-equivalent to Michelia champaca absolute, to Michelia alba absolutes (indole and phenylethyl alcohol rich in the same paper) and to Magnolia leaf oils.",
        ),
    },
    "hedychium spicatum rhizome oil gangwar 2024 shade-dried profile": {
        "analytical_method": "PUBLISHED_GC_FID_GC_MS_HYDRODISTILLED_OIL",
        "composition_basis": "GC_FID_AREA_NOMINAL_MODEL_PROXY_NOT_MASS_FRACTION",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11576735/",
                "document": "Gangwar A. et al. (2024) Effect of drying conditions on the chemical compositions, molecular docking interactions and antioxidant activity of Hedychium spicatum Buch.-Ham. rhizome essential oil. Sci Rep 14:28568, Table 1, column HSSH",
                "published_botanical_name": "Hedychium spicatum Buch.-Ham.",
                "published_type": "Hydrodistilled essential oil of shade-dried rhizomes (Uttarakhand, India)",
                "reported_pct": {
                    "1,8-cineole": 53.87, "alpha-cadinol": 12.15, "elemol": 6.78, "germacrene-4-ol": 3.73,
                    "alpha-muurolol": 3.68, "linalool": 3.41, "alpha-terpineol": 1.99, "gamma-eudesmol": 1.84,
                    "beta-pinene": 1.79, "delta-cadinene": 1.67, "terpinene-4-ol": 0.98,
                    "10-epi-gamma-eudesmol": 0.86, "epi-cubebol": 0.64, "alpha-pinene": 0.54,
                    "humulene epoxide II": 0.53, "sabinene": 0.39, "delta-terpineol": 0.38,
                    "(E)-nerolidol": 0.23, "(E)-caryophyllene": 0.19, "alpha-humulene": 0.18,
                    "thujanol": 0.16, "gamma-cadinene": 0.16, "humulene epoxide I": 0.12,
                },
                "reported_total_pct": 96.85,
                "rows_below_0_10_pct_not_listed": True,
                "other_columns_same_table": {
                    "sun-dried HSS": {"1,8-cineole": 23.68, "alpha-cadinol": 25.06, "elemol": 15.00},
                    "fresh HSF": {"1,8-cineole": 14.62, "alpha-cadinol": 20.33, "elemol": 20.03},
                },
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "PROXY_IDENTITY_UNCONFIRMED",
                "owned_stock_label": "Ginger Lily Oil (PerfumersWorld 7NS25173, neat as supplied)",
                "owned_species": "unconfirmed; H. spicatum rhizome from Kenny's strip test (28 Oct 2026: 'Ginger root, check on msr')",
                "owned_plant_part_recorded": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ('1,8-cineole', 'linalool', 'alpha terpineol', 'beta pinene', 'terpinen-4-ol', 'alpha pinene', 'sabinene', 'beta caryophyllene', 'germacrene d')},
        },
        "unresolved_constituents": (
            {"name": "alpha-cadinol", "reported_fraction": 0.1215, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "elemol", "reported_fraction": 0.0678, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "germacren-4-ol", "reported_fraction": 0.0373, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-muurolol", "reported_fraction": 0.0368, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "gamma-eudesmol", "reported_fraction": 0.0184, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "delta-cadinene", "reported_fraction": 0.0167, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "10-epi-gamma-eudesmol", "reported_fraction": 0.0086, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "epi-cubebol", "reported_fraction": 0.0064, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "humulene epoxide II", "reported_fraction": 0.0053, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "delta-terpineol", "reported_fraction": 0.0038, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(E)-nerolidol", "reported_fraction": 0.0023, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "alpha-humulene", "reported_fraction": 0.0018, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "thujanol", "reported_fraction": 0.0016, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "gamma-cadinene", "reported_fraction": 0.0016, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "humulene epoxide I", "reported_fraction": 0.0012, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "The composition is one published Indian rhizome distillation (Gangwar et al. 2024, shade-dried), not an analysis of the owned PerfumersWorld bottle, whose species and part PW does not state; Kenny's strip test (ginger root) is the only identity evidence.",
            "1,8-Cineole runs 15-54% across drying methods in the same table and in other lots (Thomas & Mani 2023: alpha-cadinol 18.6, cineole 17.9), so the top note can be weaker and the woody alcohols stronger than modeled.",
            "63.25% is modeled; 33.11% (mostly the woody sesquiterpene alcohols) is printed but has no runtime input and is uncomputed, not odorless; nine rows under 0.10% (0.52% together) carry no value. Nothing is renormalized.",
        ),
    },
    "champaca flower oil perfumersworld 7nj07740 ifra declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_CERTIFICATE_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/ifra/IFRA/IFRA_7NJ07740.pdf",
                "document": "PerfumersWorld IFRA certificate, Champaca Flower Essential Oil, SKU 7NJ07740",
                "declared_pct": {
                    "linalool synthetic (78-70-6)": 52.9063,
                    "benzyl benzoate": 2.0679,
                    "benzyl salicylate": 0.9121,
                    "d-limonene": 0.6484,
                    "methyl eugenol": 0.4126,
                    "safrole": 0.0104,
                    "l-carvone": 0.0067,
                },
                "declared_sum_pct": 57.0,
                "supplier_cas": "94333-99-0",
                "supplier_synonym": "Michaellia Alba FLOWER Oil",
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Champaca Flower EO",
                "owned_bottle_sku_verified": False,
                "true_champaca_absolute_rows_used": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("linalool", "benzyl benzoate", "benzyl salicylate", "limonene",
                            "methyl eugenol")},
            "(R)-carvone": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://pubchem.ncbi.nlm.nih.gov/compound/439570",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/6485-40-1.pdf",
                "vp_conversion": "0.1 mm Hg at 20 C (FMA, l-carvone column) = 13.33 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 20.16 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Amoore (1982) detection, (R)-(-)-carvone, as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "0.034 mg/m3 x 24450 / 150.22 = 5.534 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            {
                "name": "safrole",
                "reported_fraction": 0.000104,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "An IFRA certificate declares regulated items only; it is not a full composition, its analytical basis is not stated, and the values are declared levels, not a lot analysis.",
            "Only 56.95% of the oil is modeled; the 43.0% undeclared remainder is uncomputed, not odorless. Nothing is renormalized.",
            "The certificate lists 'Linalool synthetic', so the product may be reconstituted or extended; its linalool-dominant pattern and the supplier synonym point to Michelia alba oil, not true Michelia champaca absolute (non-equivalent).",
            "The owned bottle's supplier SKU is assumed to be PerfumersWorld 7NJ07740 and has not been verified.",
        ),
    },
    "myroxylon balsamum peru balsam perfumersworld 2qv00363 allergen declaration profile": {
        "analytical_method": "SUPPLIER_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/view.php?pro_id=2QV00363",
                "document": "PerfumersWorld allergen values for Peru Balsam Resinoid, SKU 2QV00363, as relayed by the owner",
                "document_reverified": False,
                "declared_pct": {
                    "benzyl benzoate": 26.8389,
                    "benzyl cinnamate": 16.7053,
                    "eugenol": 0.0300,
                    "benzaldehyde": 0.0206,
                    "coumarin": 0.0162,
                },
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Peru Balsam Resinoid (50% w/w in DEP)",
                "owned_bottle_sku_verified": False,
                "literature_peak_areas_used": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("benzyl benzoate", "eugenol", "coumarin")},
        },
        "unresolved_constituents": (
            {
                "name": "benzyl cinnamate",
                "reported_fraction": 0.167053,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "benzaldehyde",
                "reported_fraction": 0.000206,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cinnamic acid, nerolidol, vanillin",
                "missing_input": "LITERATURE_PEAK_AREAS_ONLY_NOT_CONVERTIBLE_TO_PERCENT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "Allergen values are supplier-declared levels of regulated allergens, relayed by the owner and not re-verified against the supplier document; they are not a full composition or a lot analysis.",
            "Only 26.89% of the resinoid is modeled. Benzyl cinnamate (16.71%) and benzaldehyde have no runtime headspace input, and cinnamic acid, nerolidol and vanillin are known only as literature GC-MS peak areas; all remain uncomputed, not odorless. Nothing is renormalized.",
            "Peru balsam esters hydrolyse with age (literature historical sample); the owned lot's age and ester content are unknown.",
        ),
    },
    "ocimum basilicum oil india estragole type supplier gc profile": {
        "analytical_method": "SUPPLIER_GC_REPORT_METHOD_NOT_STATED",
        "composition_basis": "SUPPLIER_GC_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.shopify.com/s/files/1/1277/1723/files/Basil_Sweet_Essential_Oil_India_GC.pdf",
                "document": "Botanic Universe, Basil Sweet Essential Oil India, GC report dated 2018-03-21",
                "published_botanical_name": "Not stated on the report (sold as sweet basil, India)",
                "published_type": "Basil oil, India, methyl chavicol (estragole) type",
                "reported_pct": {
                    "estragole": 75.16,
                    "linalool": 18.13,
                    "alpha-bisabolene": 1.78,
                    "geranial": 0.64,
                    "alpha-trans-bergamotene": 0.48,
                    "beta-caryophyllene": 0.40,
                    "germacrene D": 0.38,
                    "neral": 0.37,
                    "trans-beta-ocimene": 0.27,
                    "menthol": 0.26,
                    "alpha-humulene": 0.20,
                },
                "reported_total_pct": 99.99,
                "corroborating_literature_pct": {"estragole": 77.5, "linalool": 19.1},
                "corroborating_literature": "Gulati 1977, 7th Int. Essential Oil Congress, Kyoto, via https://scent.vn/en/pages/oil/basil-india-1295",
                "iso_11043_1998_range_pct": {"methyl chavicol": (75.0, 87.0), "linalol": (0.5, 3.0)},
                "iso_11043_used": False,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Basil EO (India, Ocimum Basilicum)",
                "owned_origin_matches_source": True,
                "owned_chemotype_matches_source": True,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name, *_rest in _BASIL_INDIA_ESTRAGOLE_SUPPLIER_GC_CONSTITUENTS},
        },
        "unresolved_constituents": (
            {
                "name": "estragole",
                "reported_fraction": 0.7516,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-bisabolene",
                "reported_fraction": 0.0178,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-trans-bergamotene",
                "reported_fraction": 0.0048,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-humulene",
                "reported_fraction": 0.002,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is one supplier's GC report for an Indian sweet basil oil, not an analysis of the owned bottle or lot; the report states no botanical name, lot or GC method.",
            "Estragole (methyl chavicol, 75.16%), the character constituent, has no runtime headspace input and remains uncomputed, not odorless, so the modeled headspace is linalool-led and does not represent basil character.",
            "ISO 11043:1998 (methyl chavicol type) is not used: its linalol range of 0.5-3% conflicts with the 18-19% linalool both Indian analyses report; an ISO-conforming oil would carry far less linalool than modeled here.",
            "trans-beta-Ocimene and menthol reuse the existing generic ocimene and peppermint menthol rows; ocimene isomers are not distinguished.",
        ),
    },
    "tagetes minuta whole plant oil india bansal 1999 profile": {
        "analytical_method": "LITERATURE_GC_MS",
        "composition_basis": "LITERATURE_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://scent.vn/en/pages/oil/tagetes-india-6a-whole-plant-3230",
                "document": "Bansal et al., J. Essent. Oil Res. 11:747 (1999), as tabulated by scent.vn",
                "published_botanical_name": "Tagetes minuta L.",
                "published_type": "Whole-plant essential oil, India",
                "reported_pct": {
                    "dihydrotagetone": 48.7,
                    "(Z)-tagetone": 15.0,
                    "(Z)-beta-ocimene": 8.0,
                    "(Z)-tagetenone": 3.9,
                    "limonene": 3.4,
                    "(E)-tagetone": 1.9,
                    "ocimenone": 1.7,
                },
                "reported_total_pct": 82.6,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Tagetes EO (10% in DPG)",
                "owned_origin_recorded": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name, *_rest in _TAGETES_MINUTA_INDIA_BANSAL_1999_CONSTITUENTS},
        },
        "unresolved_constituents": (
            {
                "name": "dihydrotagetone",
                "reported_fraction": 0.487,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(Z)-tagetone",
                "reported_fraction": 0.15,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(Z)-tagetenone",
                "reported_fraction": 0.039,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(E)-tagetone",
                "reported_fraction": 0.019,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "ocimenone",
                "reported_fraction": 0.017,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is one published Indian whole-plant oil, not an analysis of the owned bottle, whose origin and plant part are unrecorded; tagetes composition varies strongly with origin and growth stage.",
            "Only 11.4% of the oil is modeled ((Z)-beta-ocimene and limonene). Dihydrotagetone, the tagetones, (Z)-tagetenone and ocimenone, the tagetes character ketones, have no runtime headspace input; they remain uncomputed, not odorless, so the modeled headspace does not represent tagetes character.",
            "(Z)-beta-Ocimene reuses the generic ocimene row; ocimene isomers are not distinguished.",
            "Only 82.6% of the oil is listed in the source; the remainder is unknown and nothing is renormalized.",
        ),
    },
    "helichrysum italicum oil corsica bianchini 2001 profile": {
        "analytical_method": "LITERATURE_GC_MS",
        "composition_basis": "LITERATURE_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://scent.vn/en/pages/oil/helichrysum-italicum-france-corsica-3417",
                "document": "Bianchini et al., Flavour Fragr. J. 16:30 (2001), as tabulated by scent.vn",
                "published_botanical_name": "Helichrysum italicum (Roth) G.Don subsp. italicum",
                "published_type": "Industrial distilled essential oil, Corsica",
                "reported_pct": {
                    "neryl acetate": 32.6,
                    "gamma-curcumene": 11.7,
                    "limonene": 7.5,
                    "neryl propionate": 5.8,
                    "nerol": 4.7,
                    "italicene": 2.6,
                    "alpha-curcumene": 2.5,
                    "eudesm-5-en-11-ol": 2.4,
                    "4,6,9-trimethyl-8-decene-3,5-dione": 2.2,
                    "alpha-pinene": 1.8,
                    "4,6-dimethyloctane-3,5-dione": 1.8,
                    "5,7,10-trimethylundec-9-ene-4,6-dione": 0.8,
                    "2,5,7,9-tetramethyl-2-decene-6,8-dione": 0.8,
                },
                "reported_total_pct": 91.5,
                "conflicting_origin_profile": {
                    "source": "https://scent.vn/en/pages/oil/helichrysum-italicum-croatia-1a-2722",
                    "document": "Blazevic et al., Acta Pharm. 45:517 (1995), mean of 7 Croatian locations",
                    "reported_pct": {
                        "alpha-curcumene": 15.0,
                        "alpha-pinene": 10.0,
                        "alpha-cedrene": 10.0,
                        "gamma-curcumene": 10.0,
                        "neryl acetate": 8.0,
                    },
                    "used": False,
                },
                "origin_choice_rule": "INDUSTRIAL_DISTILLED_COMMERCIAL_OIL_OVER_WILD_POPULATION_MEAN",
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Helichrysum EO",
                "owned_origin_recorded": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name, *_rest in _HELICHRYSUM_CORSICA_BIANCHINI_2001_CONSTITUENTS},
        },
        "unresolved_constituents": (
            {
                "name": "neryl propionate",
                "reported_fraction": 0.058,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "italicene",
                "reported_fraction": 0.026,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-curcumene",
                "reported_fraction": 0.025,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "eudesm-5-en-11-ol",
                "reported_fraction": 0.024,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "4,6,9-trimethyl-8-decene-3,5-dione",
                "reported_fraction": 0.022,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "4,6-dimethyloctane-3,5-dione",
                "reported_fraction": 0.018,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "5,7,10-trimethylundec-9-ene-4,6-dione",
                "reported_fraction": 0.008,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "2,5,7,9-tetramethyl-2-decene-6,8-dione",
                "reported_fraction": 0.008,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The owned oil's origin is unknown. Corsican industrial oil (neryl acetate 32.6%) is modeled; a Croatian wild-population mean (Blazevic 1995: neryl acetate 8.0%, alpha-curcumene 15.0%, alpha-pinene 10.0%, alpha-cedrene 10.0%) differs greatly, so origin alone can move the ester-to-hydrocarbon balance severalfold.",
            "The composition is a published analysis, not an analysis of the owned bottle or lot; 91.5% of the oil is listed and the remainder is unknown, with nothing renormalized.",
            "Neryl propionate, italicene, alpha-curcumene, eudesm-5-en-11-ol and the beta-diketones (the italidione family) have no runtime headspace input and remain uncomputed, not odorless.",
            "This is the essential oil; the immortelle absolute profile is a different extraction and is not equivalent.",
        ),
    },
    "bulnesia sarmientoi wood oil enriquez 2019 gc-ms profile": {
        "analytical_method": "LITERATURE_GC_MS",
        "composition_basis": "GC_MS_RELATIVE_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.redalyc.org/journal/428/42862466009/42862466009.pdf",
                "document": "Enriquez & Orrabalis, Multequina 28:59-66 (2019), Table 1",
                "published_botanical_name": "Bulnesia sarmientoi Lorentz ex Griseb.",
                "published_type": "Steam-distilled trunk-wood oil, Formosa, Argentina",
                "quantitation": "GC_MS_RELATIVE_AREA_PCT",
                "reported_pct": {
                    "bulnesol": 58.18,
                    "guaiol": 28.71,
                    "elemol": 10.17,
                    "alpha-gurjunene": 1.08,
                    "alpha-guaiene": 0.67,
                    "beta-caryophyllene": 0.58,
                },
                "reported_sum_pct": 99.39,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Guaiacwood EO (exactly 1/3 w/w in ethanol + DEP)",
                "owned_supplier_reference": None,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("alpha guaiene", "beta caryophyllene")},
        },
        "unresolved_constituents": (
            {
                "name": "bulnesol",
                "reported_fraction": 0.5818,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "guaiol",
                "reported_fraction": 0.2871,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "elemol",
                "reported_fraction": 0.1017,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-gurjunene",
                "reported_fraction": 0.0108,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is one published Argentine steam-distilled wood oil (Enriquez & Orrabalis 2019), not an analysis of the owned bottle, whose supplier, origin and lot are unknown.",
            "Table 1 lists only six main components (99.39% of relative area); GC-MS relative areas are nominal model inputs, not mass fractions.",
            "Only 1.25% of nominal composition is modeled (alpha-guaiene and beta-caryophyllene). Bulnesol, guaiol, elemol and alpha-gurjunene (98.14%) have no runtime headspace input; they remain uncomputed, not odorless, so the modeled headspace does not represent guaiacwood character.",
        ),
    },
    "rosa x damascena bulgarian oil iso 9842 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://gigaplus.makeshop.jp/aromastore/images/download/N1507G25.pdf",
                "document": "ISO 9842 (Rosa x damascena, Bulgaria) ranges as reprinted on Sanritsu certificates of analysis N1507G25 and N1507G26",
                "iso_edition": None,
                "published_botanical_name": "Rosa x damascena Mill.",
                "published_type": "Rose oil, Bulgaria",
                "standard_range_pct": {
                    "citronellol": (20.0, 34.0),
                    "nerol": (5.0, 12.0),
                    "geraniol": (15.0, 22.0),
                    "beta-phenylethanol": (None, 3.5),
                    "heptadecane": (1.0, 2.5),
                    "nonadecane": (8.0, 15.0),
                    "heneicosane": (3.0, 5.5),
                    "ethanol": (None, 2.0),
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "upper_bound_only_rule": "NO_VALUE_INVENTED_KEPT_UNRESOLVED",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Rose Otto Bulgarian (10% in DPG)",
                "owned_supplier_reference": "PerfumersWorld 5RR12478",
                "owned_supplier_sku_recorded": True,
                "profile_is_neat_oil": True,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("citronellol", "geraniol", "nerol", "nonadecane", "heptadecane")},
            "heneicosane": {
                "mw_status": "FORMULA_MASS_C21H44",
                "vp_status": "MASS_ONLY_NONVOLATILE_ROW_CONVENTION",
                "odt_status": "MASS_ONLY_NONVOLATILE_ROW_CONVENTION",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            {
                "name": "beta-phenylethanol",
                "reported_fraction_range": (None, 0.035),
                "missing_input": "UPPER_BOUND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "ethanol",
                "reported_fraction_range": (None, 0.02),
                "missing_input": "UPPER_BOUND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-damascenone, rose oxide, methyl eugenol",
                "missing_input": "NOT_IN_STANDARD_RANGES",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The ISO 9842 ranges are second-hand, reprinted on a supplier certificate of analysis whose ISO edition is unstated; midpoints describe a conforming commercial oil, not an analysis of the owned lot.",
            "Only 71.5% of nominal composition is modeled, and 17.5% of that is non-volatile stearoptene alkanes (mass only, no headspace). beta-Phenylethanol and ethanol have upper bounds only and stay unresolved; the remainder is uncomputed, not odorless. Nothing is renormalized.",
            "Trace character odorants (beta-damascenone, rose oxide, methyl eugenol) are not in the ranges and are not modeled, so the modeled headspace understates rose character.",
            "This profile is separate from the uncited 'rose essential oil' profile and does not reuse it.",
        ),
    },
    "chrysopogon zizanioides haiti oil amrita 5101-lcaa coa profile": {
        "analytical_method": "SUPPLIER_CERTIFICATE_OF_ANALYSIS_GC",
        "composition_basis": "GC_RELATIVE_AREA_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.amrita.net/content/product_files/CoA%20-%20EO5101%20Vetiver%20%28Organic%29%20LCAA%201-2-25.pdf",
                "document": "Amrita certificate of analysis, Organic Vetiver, lot 5101-LCAA, Haiti, December 2024 (GC, DB-5)",
                "published_type": "Vetiver root oil, Haiti",
                "reported_pct": {
                    "khusimol": 19.80,
                    "trans-isovalencenol": 14.88,
                    "vetiselinenol": 5.65,
                    "cyclocopacamphenol": 5.41,
                    "beta-vetivenene": 4.30,
                },
                "reported_sum_pct": 50.04,
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Haitian Vetiver EO (neat / as supplied)",
                "owned_supplier_reference": None,
                "existing_vetiver_eo_profile_verified": False,
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("khusimol", "isovalencenol")},
        },
        "unresolved_constituents": (
            {
                "name": "vetiselinenol",
                "reported_fraction": 0.0565,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cyclocopacamphenol",
                "reported_fraction": 0.0541,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-vetivenene",
                "reported_fraction": 0.0430,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "The composition is a single supplier lot certificate (Amrita 5101-LCAA), not an analysis of the owned bottle, whose supplier and lot are not recorded.",
            "Only 34.68% of nominal composition is modeled (khusimol, trans-isovalencenol); three listed constituents (15.36%) and the unlisted remainder are uncomputed, not odorless. Nothing is renormalized.",
            "Vetivones and khusimone are not listed, so the characteristic vetiver note is not modeled.",
            "Weyerstahl et al. (2000) Flavour Fragr. J. 15:395, 'Constituents of Haitian vetiver oil', is the existing 'vetiver eo' profile's cited paper, but its table could not be reached to verify that profile; that profile is unchanged and not reused.",
        ),
    },
    "hay absolute perfumersworld 8ny00523 allergen declaration profile": {
        "analytical_method": "SUPPLIER_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=8NY00523&tab=allergen",
                "document": "PerfumersWorld allergen declaration, Hay Absolute, SKU 8NY00523 (neat)",
                "declared_pct": {
                    "vanillin": 1.0262,
                    "linalyl acetate": 0.5326,
                    "terpineol (8000-41-7)": 0.1609,
                    "coumarin": 0.0578,
                },
                "declared_sum_pct": 1.7775,
                "declaration_basis_stated": False,
                "terpineol_mapping": "ISOMER_MIXTURE_MAPPED_TO_ALPHA_TERPINEOL_ROW",
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Hay Absolute (10% w/w in DPG; homogeneous)",
                "owned_bottle_sku_verified": False,
                "candidate_skus": ("8NY00523 (neat)", "5NY12745 (sold as 10% in DPG)"),
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("vanillin", "linalyl acetate", "alpha terpineol", "coumarin")},
        },
        "unresolved_constituents": (),
        "limitations": (
            "Allergen values are supplier-declared levels of regulated allergens with no stated basis; they are not a full composition or a lot analysis.",
            "Only 1.78% of the absolute is modeled; the undeclared 98.2% remainder is uncomputed, not odorless, so the modeled headspace does not represent hay character. Nothing is renormalized.",
            "Terpineol is declared as the isomer mixture (CAS 8000-41-7) and is modeled with the alpha-terpineol row.",
            "The bought SKU is ambiguous: 8NY00523 (neat absolute) or 5NY12745 (sold as 10% in DPG); the owned stock is 10% w/w in DPG.",
        ),
    },
    "orange flower absolute perfumersworld 8nc00338 declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_AND_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=8NC00338",
                "document": "PerfumersWorld IFRA certificate and allergen declaration, Orange Flower Absolute, SKU 8NC00338 (neat), read 25 Oct 2026",
                "declared_pct": {
                    "linalool": 14.2295,
                    "geraniol": 0.7383,
                    "benzyl cyanide": 0.4962,
                    "d-limonene": 0.1722,
                    "methyl n-formylanthranilate": 0.0385,
                    "benzaldehyde": 0.0061,
                    "methyl n-methylanthranilate": 0.0026,
                    "7-methoxycoumarin": 0.0017,
                },
                "declared_sum_pct": 15.6851,
                "declaration_basis_stated": False,
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Orange Flower Absolute 10% in DPG (STK-148)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "5NC07544 (Orange Flower Absolute 10% in DPG, batch ref ORA07544/26298), whose tables are one tenth of 8NC00338's",
                "literature_not_mixed_in": "CIR 2021 (Burnett et al., Int J Toxicol, doi 10.1177/10915818211040477) Table 5 gives linalool 34-48%, linalyl acetate 14-21%, farnesol 3.6-15.4%, nerolidol 4.9-8.9%, indole 2.6-9.9%; PW declares linalool 14.23% and no farnesol, so the published rows are not added",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("linalool", "geraniol", "limonene")},
        },
        "unresolved_constituents": (
            {"name": "benzyl cyanide", "reported_fraction": 0.004962, "reason": "no constituent row in this module; marked IFRA-prohibited on PW's certificate"},
            {"name": "methyl n-formylanthranilate", "reported_fraction": 0.000385, "reason": "no constituent row in this module"},
            {"name": "benzaldehyde", "reported_fraction": 0.000061, "reason": "no constituent row in this module"},
            {"name": "methyl n-methylanthranilate", "reported_fraction": 0.000026, "reason": "no constituent row in this module"},
            {"name": "7-methoxycoumarin", "reported_fraction": 0.000017, "reason": "no constituent row in this module; marked IFRA-prohibited on PW's certificate"},
        ),
        "limitations": (
            "Values are supplier-declared levels of IFRA-restricted materials and allergens with no stated basis; they are not a full composition or a lot analysis.",
            "Only 15.14% of the absolute is modeled (linalool, geraniol, limonene); 0.545% declared without a constituent row and the undeclared remainder are uncomputed, not odorless. Nothing is renormalized.",
            "Indole, methyl anthranilate, nerolidol, farnesol and phenylethyl alcohol, which carry orange flower character in published absolutes, are not declared by PW and are not modeled.",
        ),
    },
    "frangipani absolute perfumersworld 8on00534 declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_AND_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=8ON00534",
                "document": "PerfumersWorld IFRA certificate and allergen declaration, Frangipani Absolute, SKU 8ON00534 (neat, CAS 94350-02-4), read 25 Oct 2026",
                "declared_pct": {
                    "benzyl salicylate": 9.0958,
                    "benzyl benzoate": 1.6552,
                    "linalool": 0.7789,
                    "citronellol": 0.3794,
                    "benzyl alcohol": 0.2475,
                    "citral": 0.0785,
                    "benzaldehyde": 0.0501,
                },
                "declared_sum_pct": 12.2854,
                "declaration_basis_stated": False,
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Frangipani Absolute (10% in DPG)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "5ON09236 (Frangipani Absolute 10% in DPG, batch ref FRA09236/26298), whose tables are one tenth of 8ON00534's",
                "literature_not_mixed_in": "Published Plumeria absolutes and oils give benzyl salicylate about 27-45% and farnesol about 8%; PW declares 9.10% and no farnesol, so the published rows are not added",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("benzyl salicylate", "benzyl benzoate", "linalool", "citronellol", "benzyl alcohol", "citral")},
        },
        "unresolved_constituents": (
            {"name": "benzaldehyde", "reported_fraction": 0.000501, "reason": "no constituent row in this module"},
        ),
        "limitations": (
            "Values are supplier-declared levels of IFRA-restricted materials and allergens with no stated basis; they are not a full composition or a lot analysis.",
            "Only 12.24% of the absolute is modeled; 0.05% benzaldehyde and the undeclared remainder are uncomputed, not odorless. Nothing is renormalized.",
            "Citral is declared as the isomer mixture (CAS 5392-40-5) and is modeled with the citral row.",
        ),
    },
    "abies balsamea needle oil canadian commercial swor 2022 range midpoint profile": {
        "analytical_method": "PUBLISHED_GC_MS_RANGES_COMMERCIAL_OILS",
        "composition_basis": "PUBLISHED_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "Swor K, Poudel A, Rokaya A, Satyal P, Setzer WN. Nat Prod Commun 2022;17(3), doi:10.1177/1934578X221086901, Table 2 column 'A. balsamea' ('Based on 10 commercial samples from Canada')",
                "range_pct": {
                    "alpha pinene": (17.8, 31.3),
                    "beta pinene": (22.1, 32.8),
                    "limonene": (11.9, 23.3),
                    "beta phellandrene": (6.3, 12.2),
                    "delta-3-carene": (1.4, 9.8),
                    "bornyl acetate": (0.3, 6.4),
                    "camphene": (0.6, 4.2),
                },
                "species": "Abies balsamea, as the MySkinRecipes MSDS states ('ABIES BALSAMEA NEEDLE OIL 100%'); CAS 85085-34-3 on the COA is the EINECS number Biolandes also lists for its balsam fir oil",
                "species_asserted_by_supplier": True,
                "fraction_rule": "RANGE_MIDPOINT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Fir Needle Oil (Canada) (STK-175, neat)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "MySkinRecipes order 2200410, lot ECPT07, 5 g",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("beta pinene", "alpha pinene", "limonene", "delta-3-carene",
                            "bornyl acetate", "camphene")},
            "beta phellandrene": {
                "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
                "vp_status": "MONOTERPENE_HYDROCARBON_CLASS_INPUT",
                "odt_status": "MONOTERPENE_HYDROCARBON_CLASS_INPUT",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
        ),
        "limitations": (
            "Composition is the midpoint of published ranges for commercial Canadian oils, not an analysis of the owned lot.",
            "Only 90.2% of the oil is modeled; myrcene, tricyclene and the other minor terpenes are uncomputed, not odorless. Nothing is renormalized.",
            "beta-Phellandrene VP and ODT are monoterpene class inputs, not measured values.",
        ),
    },
    "boswellia carterii oil woolley 2012 somali average profile": {
        "analytical_method": "PUBLISHED_GC_MS_AVERAGES",
        "composition_basis": "PUBLISHED_AVERAGE_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "Woolley CL et al. Chemical differentiation of Boswellia sacra and Boswellia carterii essential oils by gas chromatography and chiral gas chromatography-mass spectrometry. J Chromatogr A 2012;1261:158-163, doi:10.1016/j.chroma.2012.06.073 (abstract averages for B. carterii)",
                "average_pct": {
                    "alpha thujene": 7.9,
                    "alpha pinene": 37.3,
                    "camphene": 0.8,
                    "sabinene": 4.9,
                    "beta pinene": 1.8,
                    "myrcene": 7.3,
                    "limonene + beta-phellandrene": 14.4,
                },
                "cross_check": "Johnson S et al. Plants 2019;8(4):88, doi:10.3390/plants8040088, Table 2 (13 commercial 'B. carteri' oils): alpha-pinene 24.4-47.5, limonene 4.5-25.7, alpha-thujene 1.2-11.9, sabinene 1.3-8.1, myrcene 2.4-8.1; every Woolley average is inside these ranges",
                "species": "Boswellia carterii, as the MySkinRecipes MSDS states ('BOSWELLIA CARTERII GUM OIL 100%'); CAS 89957-98-2 on the COA is the EINECS number for B. carterii extractives",
                "species_asserted_by_supplier": True,
                "fraction_rule": "PUBLISHED_AVERAGE_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Olibanum Oil (STK-173, neat)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "MySkinRecipes order 2200410, lot 3S74J8, 5 g",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("alpha pinene", "limonene", "myrcene", "sabinene", "beta pinene",
                            "camphene")},
            "alpha thujene": {
                "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
                "vp_status": "MONOTERPENE_HYDROCARBON_CLASS_INPUT",
                "odt_status": "MONOTERPENE_HYDROCARBON_CLASS_INPUT",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
        ),
        "limitations": (
            "Composition is a published species average, not an analysis of the owned lot; B. carterii oils fall into chemotypes (alpha-pinene, limonene or alpha-thujene rich).",
            "Only 74.4% of the oil is modeled; p-cymene, the sesquiterpenes and the remainder are uncomputed, not odorless. Nothing is renormalized.",
            "Limonene is printed together with beta-phellandrene and is modeled with limonene inputs; alpha-thujene VP and ODT are monoterpene class inputs.",
        ),
    },
    "ferula galbaniflua resinoid canton 2025 volatile fraction profile": {
        "analytical_method": "PUBLISHED_GC_FID_VOLATILE_FRACTION_WITH_MEASURED_FRACTION_SHARE",
        "composition_basis": "GC_FID_AREA_OF_VOLATILE_FRACTION_TIMES_MEASURED_VOLATILE_SHARE",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "Canton M et al. Chemical Profiling of Volatile and Non-Volatile Fractions of Galbanum (Ferula galbaniflua Boiss.) Used in Perfumery. Chem Biodivers 2025;22(12):e01442, doi:10.1002/cbdv.202501442, Table 1",
                "volatile_fraction_share_pct": 34.5,
                "volatile_fraction_quote": "VF of galbanum resinoid represented up to 34.5 \u00b1 1.5% of the whole substance",
                "volatile_fraction_pct_fid": {
                    "beta pinene": 25.4,
                    "beta eudesmol": 2.8,
                    "alpha eudesmol": 2.6,
                    "limonene (coeluting with beta-phellandrene)": 1.9,
                    "delta-3-carene": 1.7,
                    "alpha pinene": 1.4,
                    "germacrene d": 1.3,
                    "myrcene": 1.2,
                    "alpha-bisabolol": 0.9,
                    "beta caryophyllene": 0.4,
                    "(3E,5Z)-1,3,5-undecatriene": 0.7,
                },
                "species": "Ferula galbaniflua resinoid; the MySkinRecipes MSDS states 'GALBANUM, RESIN (FERULA SPP.) 100%', CAS 9000-24-2 (galbanum gum)",
                "species_asserted_by_supplier": True,
                "fraction_rule": "VOLATILE_FRACTION_PERCENT_TIMES_0.345_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Galbanum Resinoid (STK-176, neat as supplied)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "MySkinRecipes order 2200410, lot QM0D25, 5 g",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("beta pinene", "beta eudesmol", "alpha eudesmol", "limonene",
                            "delta-3-carene", "alpha pinene", "germacrene d", "myrcene",
                            "alpha-bisabolol", "beta caryophyllene")},
            "(3E,5Z)-1,3,5-undecatriene": {
                "mw_status": "NIST_WEBBOOK_MOLECULAR_MASS",
                "odt_status": "PRODUCER_PATENT_ODOUR_VALUE_COMMERCIAL_ISOMER_MIX",
                "odt_source": "Givaudan US 2019/0336413 A1 [0035]-[0045], '(3E,5Z)-undeca-1,3,5-triene (for example UNDECATRIENE, log(OV)=6.65)', OV = HS/ODT; HS 904 ug/l from US 2023/0151305 A1 Table 12 ('UNDECATRIENE 0.07 904 YES'); 904/10^6.65 ug/L = 0.202 ng/L = 0.033 ppb",
                "vp_status": "PRODUCER_PATENT_HEADSPACE_IDEAL_GAS",
                "vp_source": "US 2023/0151305 A1 [0022]: volatility = equilibrium headspace at 25 C; 0.904 g/m3 / 150.26 g/mol x RT = 14.9 Pa",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            # Volatile rows: %FID in the volatile fraction x its 34.5 % share of the resinoid.
            {"name": "bulnesol", "reported_fraction": 0.02484, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "guaiol", "reported_fraction": 0.023805, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "10-epi-alpha-eudesmol", "reported_fraction": 0.012075, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "germacrene B", "reported_fraction": 0.008625, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "gamma-elemene", "reported_fraction": 0.007245, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "delta-cadinene", "reported_fraction": 0.006555, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(3E,5E)-1,3,5-undecatriene", "reported_fraction": 0.001725, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            # Non-volatile coumarins: the paper's HPLC content in the raw resinoid (its Table 4).
            {"name": "galbanic acid", "reported_fraction": 0.11856, "missing_input": "NON_VOLATILE_NO_HEADSPACE", "odor_contribution": "UNCOMPUTED"},
            {"name": "farnesiferol A", "reported_fraction": 0.07929, "missing_input": "NON_VOLATILE_NO_HEADSPACE", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "Composition is one published commercial resinoid, not an analysis of the owned lot.",
            "Only 13.90% of the resinoid is modeled: the volatile rows with inputs in this module. The other volatile rows, including (3E,5E)-undecatriene, and the 65.5% non-volatile fraction are uncomputed, not odorless. Nothing is renormalized.",
            "The (3E,5Z)-undecatriene threshold is Givaudan's value for its commercial Undecatriene, a mix of about 55% (3E,5Z) with other isomers; if the others are weak, the pure isomer is about 0.018 ppb.",
            "Both eudesmols take one eudesmol input; limonene coelutes with beta-phellandrene.",
        ),
    },
    "artemisia pallens oil pappas 2025 revive lot 8f gc-ms profile": {
        "analytical_method": "GC_MS_LOT_REPORT_COMMERCIAL_OIL",
        "composition_basis": "GC_MS_CONC_PERCENT_AS_PRINTED_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "Pappas RS, GC/MS report 'Davana Oil, India', Revive lot 8F (Shimadzu GCMS-QP2010Ultra, ZB-5), analysed 1/29/2025, https://www.revive-eo.com/wp-content/uploads/2025/01/REVIVE-GCMS-Report-Davana-Oil-India-8F.pdf",
                "printed_pct": {
                    "davanone": 53.55,
                    "bicyclogermacrene": 8.11,
                    "davana ether II": 4.45,
                    "trans-ethyl cinnamate": 4.3,
                    "davana ether IV": 2.52,
                    "davana ether I": 1.45,
                    "tau-cadinol": 1.41,
                    "beta-selinene": 1.31,
                    "cis-ethyl cinnamate": 1.12,
                    "germacrene d": 1.04,
                    "davana ether III": 0.99,
                    "alpha eudesmol": 0.81,
                    "geranyl acetate": 0.76,
                    "linalool": 0.52,
                },
                "total_identified_pct": 92.78,
                "cross_check": "Singh S et al. Chem Biodivers 2021;18(11):e2100531, doi:10.1002/cbdv.202100531 (abstract: cis-davanone 53.0, bicyclogermacrene 6.9, trans-ethyl cinnamate 4.9, davana ether isomer 3.4, spathulenol 2.8%); Bail S et al. Nat Prod Commun 2008;3(7):1057-1062, doi:10.1177/1934578X0800300705 (Kurt Kitzing commercial oil, GC-FID: cis-davanone 45.8, bicyclogermacrene 9.6%)",
                "species": "Artemisia pallens (davana), inferred from PerfumersWorld's CAS 8016-03-3; PW names no species or origin",
                "species_asserted_by_supplier": False,
                "fraction_rule": "PRINTED_GC_MS_CONC_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Davana Essential Oil (STK-184, 10% w/w in DPG)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "5HH12466 (PW order PW-261024-211206f41, 2 g; no lot published)",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("germacrene d", "alpha eudesmol", "geranyl acetate", "linalool")},
        },
        "unresolved_constituents": (
            {"name": "davanone", "reported_fraction": 0.5355, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "bicyclogermacrene", "reported_fraction": 0.0811, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "davana ether II", "reported_fraction": 0.0445, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(E)-ethyl cinnamate", "reported_fraction": 0.043, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "davana ether IV", "reported_fraction": 0.0252, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "davana ether I", "reported_fraction": 0.0145, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "tau-cadinol", "reported_fraction": 0.0141, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "beta-selinene", "reported_fraction": 0.0131, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "davanone analogue (RI 1542)", "reported_fraction": 0.0127, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "unidentified (RI 1654)", "reported_fraction": 0.0118, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(Z)-ethyl cinnamate", "reported_fraction": 0.0112, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "davana ether III", "reported_fraction": 0.0099, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
            {"name": "(E)-methyl cinnamate", "reported_fraction": 0.0075, "missing_input": "NO_RUNTIME_HEADSPACE_INPUT", "odor_contribution": "UNCOMPUTED"},
        ),
        "limitations": (
            "Composition is one GC/MS report on a commercial Indian oil, not an analysis of the owned bottle; the GC/MS percentages are not FID response-corrected.",
            "Only 3.13% of the oil is modeled. Davanone (53.55%), which Bail et al. (2008) call practically odorless, and the davana ethers and ethyl cinnamates the same paper credits with the odour, have no runtime input, so the fruity-liqueur character is uncomputed, not absent. Nothing is renormalized.",
        ),
    },
    "abies balsamea needle oil perfumersworld 7kg07758 biolandes midpoint profile": {
        "analytical_method": "SUPPLIER_DECLARATION_PLUS_PRODUCER_SPECIFICATION_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "declared_source": "https://www.perfumersworld.com/document-list.php?pro_id=7KG07758",
                "declared_pct": {
                    "limonene": 6.3682,
                    "alpha-bisabolol": 0.5140,
                    "cuminaldehyde": 0.0314,
                    "l-carvone": 0.0274,
                    "benzyl alcohol": 0.0201,
                },
                "range_sources": {
                    "beta pinene": ("Biolandes Fir balsam EO, 28-38%", 0.33),
                    "alpha pinene": ("Biolandes Fir balsam EO, 9-24%", 0.165),
                    "delta-3-carene": ("Biolandes Fir balsam EO, up to 18%", 0.09),
                    "bornyl acetate": ("Biolandes Fir balsam EO, 2-12%", 0.07),
                    "camphene": ("Canadian Flora Essential Oils balsam fir TDS (20 Jun 2020), 4-7%", 0.055),
                },
                "species": "Abies balsamea, inferred: PW names no species; CAS 8021-28-1 is the balsam fir needle oil CAS (Biolandes, Canadian Flora, Ellemental) and PW's limonene 6.37% is inside Biolandes' 5-15%",
                "species_asserted_by_supplier": False,
                "fraction_rule": "DECLARED_PERCENT_OR_RANGE_MIDPOINT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Fir EO 10% (STK-122, 10% w/w in DPG)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "7KG07758 (PW order PW-260817-03422462b, 17 Aug 2026, 1 g)",
            },
            **{name: dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY)
               for name in ("beta pinene", "alpha pinene", "delta-3-carene", "bornyl acetate",
                            "limonene", "camphene", "alpha-bisabolol", "benzyl alcohol")},
            "cuminaldehyde": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://www.sciencedirect.com/science/article/pii/S0278691520303884",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://www.sciencedirect.com/science/article/pii/S0278691520303884",
                "vp_conversion": "0.07 mm Hg at 20 C (FMA) = 9.33 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 14.25 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Von Ranson & Belitz (1992b) detection, as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "0.086 mg/m3 x 24450 / 148.2 = 14.19 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
            "(R)-carvone": {
                "mw_status": "PUBLISHED_MOLECULAR_WEIGHT",
                "mw_source": "https://pubchem.ncbi.nlm.nih.gov/compound/439570",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/6485-40-1.pdf",
                "vp_conversion": "0.1 mm Hg at 20 C (FMA, l-carvone column) = 13.33 Pa; Clausius-Clapeyron to 25 C with dHvap = 70.0 - 3.82 ln(VP/Pa) kJ/mol (doi:10.1021/es980812j) = 20.16 Pa",
                "odt_status": "PUBLISHED_AIR_THRESHOLD",
                "odt_source": "Amoore (1982) detection, (R)-(-)-carvone, as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "0.034 mg/m3 x 24450 / 150.22 = 5.534 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
        ),
        "limitations": (
            "The species is inferred from the CAS and the limonene level; PerfumersWorld does not name it.",
            "PW's declared rows are kept as declared; the main terpenes are midpoints of producer specification ranges, not an analysis of the owned lot.",
            "Only 77.96% of the oil is modeled; myrcene, santene, tricyclene and the other minor terpenes and the remainder are uncomputed, not odorless. Nothing is renormalized.",
        ),
    },
    "lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile": {
        "analytical_method": "PHARMACOPOEIA_GRADE_CONTENT_RANGE",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.sciencedirect.com/topics/medicine-and-dentistry/lemon-oil",
                "document": "Trease and Evans' Pharmacognosy, terpeneless lemon oil, as excerpted on ScienceDirect Topics 'Lemon Oil' (read 25 Oct 2026): 'Terpeneless Lemon Oil of the BP is prepared by concentrating lemon oil in vacuo until most of the terpenes have been removed, or by solvent partition. The concentrate is the terpeneless oil, which has a citral content of 40-50%.'",
                "reported_range_pct": {"citral": (40.0, 50.0)},
                "pharmacopoeia_read_directly": False,
                "fraction_rule": "MIDPOINT_OF_GRADE_RANGE_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Lemon Terpeneless Oil Sicilian (neat / as supplied)",
                "owned_bottle_sku_verified": True,
                "owned_sku": "7CC24027 (PW order 261004-055451ce1, 2 g, received 7 Oct 2026)",
                "supplier_documents": "https://www.perfumersworld.com/document-list.php?pro_id=7CC24027: SDS 'No composition data available for this product'; allergen declaration 'No restricted materials found'; MSDS SG 0.885-0.897 at 25 C; product page SG 0.8850, RI 1.4780, CAS 68648-39-5, FEMA 2626",
                "supplier_ifra_certificate_conflict": "PW's IFRA certificate gives 25% for Category 4 fine fragrance, but a 40-50% citral oil would be limited to about 1.2-1.5% by the citral standard (0.6% in Category 4). The certificate appears to be generated from PW's empty composition table, so it is not relied on; the release gate keeps its IFRA hold on this stock.",
                "sicilian_origin_asserted_by_supplier": True,
            },
            "citral": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "limitations": (
            "Estimate of the British Pharmacopoeia terpeneless grade from its stated citral content, read through a pharmacognosy textbook, not the pharmacopoeia itself or an analysis of the owned bottle.",
            "Only citral (45%) is modeled. The esters (neryl and geranyl acetate), alcohols (alpha-terpineol, linalool, nerol, geraniol), aliphatic aldehydes and any sesquiterpenes that make up most of the rest are uncomputed, not odorless. Nothing is renormalized.",
            "Neral and geranial are not split; the module's lumped citral row is used.",
        ),
    },
    "black pepper eo": {
        "analytical_method": "PUBLISHED_GC_PROFILE_HYDRODISTILLED_OIL",
        "composition_basis": "LITERATURE_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://doi.org/10.1016/j.talanta.2014.01.007",
                "document": "Bagheri H, Abdul Manap MY, Solati Z (2014) Antioxidant activity of Piper nigrum L. essential oil extracted by supercritical CO2 extraction and hydro-distillation. Talanta 121:220-228 (hydrodistilled oil; the SFE oil is not used)",
                "published_origin": "Piper nigrum L. var. Kuching fruit, Malaysian Pepper Board, Sarawak, Malaysia",
                "reported_pct": {
                    "beta-caryophyllene": 18.64,
                    "limonene": 14.95,
                    "sabinene": 13.19,
                    "beta-pinene": 9.71,
                    "delta-3-carene": 8.56,
                    "alpha-pinene": 7.96,
                },
                "fraction_rule": "REPORTED_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Black Pepper EO (neat / as supplied)",
                "owned_supplier_sku_recorded": False,
                "supplier_declaration_not_modeled": {
                    "source": "https://www.perfumersworld.com/document-list.php?pro_id=7SQ00359",
                    "document": "PerfumersWorld 7SQ00359 IFRA certificate, batch BLA00359/26270",
                    "declared_pct": {
                        "d-limonene": 20.816,
                        "l-carvone": 0.1707,
                        "linalool": 0.1444,
                    },
                },
                "replaces": "uncited two-row profile (beta caryophyllene 0.3742, limonene 0.1335) attributed to PubMed 41245190",
            },
            "beta-caryophyllene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "sabinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "beta pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "delta-3-carene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "constituents below the six major ones",
                "missing_input": "NOT_LOADED_ONLY_MAJOR_CONSTITUENTS_VERIFIED",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "Literature proxy from one published Malaysian hydrodistilled oil; it is not an analysis of the owned bottle, whose supplier and lot are not recorded.",
            "Only the six major constituents (73.01%) are modeled; minor constituents, including the oxygenated odorants, are uncomputed, not odorless. Nothing is renormalized.",
            "PerfumersWorld 7SQ00359 declares d-limonene 20.82%, above this source's 14.95%; the supplier figure is recorded, not modeled.",
            "Rotundone, the peppery character odorant, is not quantified in the source and is not modeled.",
        ),
    },
    "lime distilled eo": {
        "analytical_method": "PUBLISHED_GC_PROFILES_RANGE_PLUS_SUPPLIER_DECLARATION",
        "composition_basis": "LITERATURE_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.tomsic.co.jp/wp-content/themes/tomsic/images/product/mega/32.pdf",
                "document": "Dugo P, Cotroneo A, Bonaccorsi I, Mondello L (1998) On the genuineness of citrus essential oils. Part LIII. Flavour Fragr. J. 13:93-97, Table 1 (distilled lime oils, Mexico 1-4)",
                "published_botanical_name": "Citrus aurantifolia Swingle",
                "published_type": "Distilled lime oil, four commercial Mexican oils (Peru and Ivory Coast columns not used)",
                "reported_range_pct": {
                    "limonene": "40.49-42.24",
                    "gamma-terpinene": "8.51-10.94",
                    "terpinolene": "6.91-8.59",
                    "alpha-terpineol": "7.03-8.04",
                    "1,8-cineole": "7.15-7.45",
                    "p-cymene": "1.81-4.28",
                    "1,4-cineole": "2.43-3.22",
                    "alpha-terpinene": "1.62-2.15",
                    "(E,E)-alpha-farnesene": "1.09-2.47",
                    "beta-pinene": "1.19-1.85",
                    "gamma-terpineol": "1.10-1.31",
                    "alpha-pinene": "0.94-1.17",
                    "terpinen-1-ol": "0.74-1.11",
                    "myrcene": "0.85-1.10",
                    "terpinen-4-ol": "0.56-0.82",
                    "cis-beta-terpineol": "0.60-0.91",
                    "alpha-fenchol": "0.66-0.83",
                    "alpha-fenchene (+ camphene, co-eluted)": "0.69-0.73",
                    "borneol": "0.59-0.70",
                    "trans-alpha-bergamotene": "0.45-0.80",
                    "beta-caryophyllene": "0.52-0.57",
                    "alpha-phellandrene": "0.34-0.45",
                },
                "fraction_rule": "MIDPOINT_OF_MEXICO_1_4_MIN_MAX_RANGE",
                "citral_source": {
                    "source": "https://www.perfumersworld.com/document-list.php?pro_id=7CK00274",
                    "document": "PerfumersWorld 7CK00274 allergen declaration and IFRA certificate, lot LIM00274/26298",
                    "declared_pct": {
                        "d-limonene": 47.9454,
                        "citral": 0.7556,
                        "l-carvone": 0.0094,
                    },
                    "rows_used": (
                        "citral",
                    ),
                },
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Lime Distilled EO",
                "owned_supplier_reference": "PerfumersWorld 7CK00274",
                "owned_species_recorded": False,
                "replaces": "uncited seven-row profile attributed to Chisholm et al. (2003), 47.2%",
            },
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "gamma terpinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "terpinolene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha terpineol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "1,8-cineole": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "beta pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "myrcene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "terpinen-4-ol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "borneol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "beta-caryophyllene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "citral": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "p cymene": {
                "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
                "vp_status": "MODELED_CLASS_INPUT_SCHINUS_ROW",
                "odt_status": "MODELED_CLASS_INPUT_SCHINUS_ROW",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
            "alpha phellandrene": {
                "mw_status": "EXISTING_RUNTIME_MOLECULAR_MASS",
                "vp_status": "MODELED_CLASS_INPUT_SCHINUS_ROW",
                "odt_status": "MODELED_CLASS_INPUT_SCHINUS_ROW",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
            "alpha-terpinene": {
                "mw_status": "NIST_WEBBOOK_C99865",
                "mw_source": "https://webbook.nist.gov/cgi/cbook.cgi?ID=C99865",
                "vp_status": "FMA_DATABASE_20C_VIA_RIFM_CONVERTED_TO_25C",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/99-86-5.pdf",
                "vp_conversion": "0.5 mm Hg at 20 C = 66.66 Pa; Clausius-Clapeyron to 25 C with dHvap 53.96 kJ/mol from 70.0 - 3.82 ln(VP/Pa) (doi:10.1021/es980812j) = 96.6 Pa",
                "odt_status": "PUBLISHED_AIR_DETECTION_THRESHOLD",
                "odt_source": "Cometto-Muniz JE, Cain WS, Abraham MH, Kumarsingh R (1998) Pharmacol Biochem Behav 60:765-770, doi:10.1016/s0091-3057(98)00054-9; 7.9 mg/m3 detection as compiled in van Gemert (2011) AIR section",
                "odt_conversion": "7.9 mg/m3 x 24450 / 136.234 = 1418 ppb",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            {
                "name": "1,4-cineole",
                "reported_fraction": 0.02825,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(E,E)-alpha-farnesene",
                "reported_fraction": 0.0178,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
                "note": "co-elutes with beta-bisabolene per the source table footnote, so the fraction is an upper bound for either",
            },
            {
                "name": "gamma-terpineol",
                "reported_fraction": 0.01205,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "terpinen-1-ol",
                "reported_fraction": 0.00925,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cis-beta-terpineol",
                "reported_fraction": 0.00755,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-fenchol",
                "reported_fraction": 0.00745,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "alpha-fenchene (+ camphene, co-eluted)",
                "reported_fraction": 0.0071,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "trans-alpha-bergamotene",
                "reported_fraction": 0.00625,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "Literature proxy from four published Mexican distilled lime oils; it is not an analysis of the owned PerfumersWorld 7CK00274 lot, whose species and origin PerfumersWorld does not state.",
            "85.1856% of nominal composition is modeled. 1,4-Cineole, (E,E)-alpha-farnesene (co-eluting with beta-bisabolene), gamma-terpineol, terpinen-1-ol, cis-beta-terpineol, alpha-fenchol, alpha-fenchene with camphene, trans-alpha-bergamotene and the unlisted remainder are uncomputed, not odorless. Nothing is renormalized.",
            "PerfumersWorld 7CK00274 declares d-limonene 47.95%, above the Mexican oils' 40.49-42.24%; limonene is modeled from the paper, citral from the declaration.",
            "p-Cymene and alpha-phellandrene reuse the Schinus class rows; alpha-terpinene's 25 C VP is converted from a 20 C FMA figure.",
            "Neral and geranial are not separately quantified; only the declared citral total is modeled.",
        ),
    },
    "rose essential oil": {
        "analytical_method": "PUBLISHED_GC_PROFILES_REGIONAL_RANGE",
        "composition_basis": "LITERATURE_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://asianpubs.org/index.php/ajchem/article/download/18212/18162/18291",
                "document": "Ahmad A, Sahoo D, Ahmad J, Tandon S (2009) GC-MS Composition of Rose Oil (Rosa damascena) of Different Agro Climatic Regions of North India. Asian J. Chem. 21(6):4643-4647, Table 1",
                "published_botanical_name": "Rosa damascena Mill.",
                "published_type": "Hydro-distilled flower oil (CIMAP improved cohobation units), four North Indian regions",
                "reported_range_pct": {
                    "citronellol": "13.51-30.44",
                    "geraniol": "19.48-31.74",
                    "nerol": "7.54-13.09",
                    "nonadecane": "5.90-11.43",
                    "heneicosane": "4.56-6.78",
                    "geranyl acetate": "0.36-4.16",
                    "farnesol": "1.05-2.23",
                    "eugenol": "0.70-1.90",
                    "eicosane": "0.90-1.52",
                    "linalool": "0.28-1.80",
                    "alpha-guaiene": "0.40-1.03",
                    "alpha-humulene": "0.33-1.05",
                    "geranial": "0.04-0.89",
                    "phenylethyl alcohol": "0.05-0.99",
                    "cis-rose oxide": "0.14-0.67",
                },
                "fraction_rule": "MIDPOINT_OF_FOUR_REGION_MIN_MAX_RANGE",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Rose Essential Oil (Rosa Damascena, India)",
                "owned_supplier_sku_recorded": False,
                "owned_origin_recorded": True,
                "replaces": "uncited four-row profile (citronellol 0.35, geraniol 0.20, linalool 0.03, phenethyl alcohol 0.03)",
            },
            "citronellol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "geraniol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "nerol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "nonadecane": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "heneicosane": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "geranyl acetate": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "farnesol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "eugenol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "linalool": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha guaiene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "geranial": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "phenylethyl alcohol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "rose oxide": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "eicosane": {
                "mw_status": "FORMULA_MASS_C20H42",
                "vp_status": "MASS_ONLY_NONVOLATILE_ROW_CONVENTION",
                "odt_status": "MASS_ONLY_NONVOLATILE_ROW_CONVENTION",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
            },
        },
        "unresolved_constituents": (
            {
                "name": "alpha-humulene",
                "reported_fraction": 0.0069,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "Literature proxy from four published North Indian oils; it is not an analysis of the owned bottle, whose supplier, region and lot are not recorded.",
            "81.79% of nominal composition is modeled, 15.545% of it non-volatile stearoptene alkanes (mass only, no headspace). alpha-Humulene and the unlisted remainder are uncomputed, not odorless. Nothing is renormalized.",
            "The regional oils differ widely (citronellol 13.51-30.44%, geraniol 19.48-31.74%); a midpoint describes no single oil. The paper's text gives Kashmir citronellol as 33.44% where the table prints 30.44%; the table is used.",
            "beta-Damascenone and other trace character odorants are not reported and are not modeled.",
        ),
    },
    "rose de mai absolute": {
        "analytical_method": "LAB_CERTIFICATE_INTERNAL_STANDARD_GC_FID",
        "composition_basis": "RESPONSE_FACTOR_CORRECTED_MASS_FRACTION_OTHER_LOT_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.planttherapy.com/cdn/shop/files/Rose_R30111.pdf",
                "document": "Laboratoire PhytoChemia certificate of analysis 22D25-PTH03, 'Rose - R30111R' (Plant Therapy), 28 Apr 2022",
                "published_botanical_name": "Rosa centifolia",
                "published_type": "Absolute; origin not stated",
                "reported_pct_m_m": {
                    "2-phenylethyl alcohol": 30.68,
                    "citronellol": 8.6,
                    "geraniol": 5.21,
                    "palmitic acid": 2.41,
                    "docosene isomer": 1.79,
                    "unknown oxygenated triterpene": 0.85,
                    "eugenol": 0.48,
                    "nonadecane": 0.23,
                    "nerol": 0.22,
                    "tetradecyl nonanoate": 0.19,
                    "nonadecene (9Z)": 0.17,
                    "pentadecyl octanoate": 0.16,
                    "methyl eugenol": 0.11,
                    "benzyl alcohol": 0.1,
                },
                "consolidated_total_pct_m_m": 53.42,
                "response_factor_correction": "CACHET_2016_CORRECTED_INTERNAL_STANDARD",
                "fraction_rule": "REPORTED_MASS_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "REPORTED_AS_MASS_FRACTION",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Rose de Mai Absolute (10% in DPG)",
                "owned_supplier_reference": "PerfumersWorld 5RM07856 (10% in DPG of 8RM00395)",
                "profile_is_neat_absolute": True,
                "replaces": "uncited six-row profile attributed to Kovats 1987 and Ohloff 1994 (citronellol 0.35, geraniol 0.18, nerol 0.08, phenylethyl alcohol 0.04, beta-damascenone 0.003, linalool 0.02)",
            },
            "phenylethyl alcohol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "citronellol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "geraniol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "palmitic acid": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "eugenol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "nonadecane": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "nerol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "methyl eugenol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl alcohol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "docosene isomer",
                "reported_fraction": 0.0179,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "unknown oxygenated triterpene",
                "reported_fraction": 0.0085,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "tetradecyl nonanoate",
                "reported_fraction": 0.0019,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "nonadecene (9Z)",
                "reported_fraction": 0.0017,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "pentadecyl octanoate",
                "reported_fraction": 0.0016,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "One lab certificate for another supplier's Rosa centifolia absolute (Plant Therapy lot R30111R); it is not an analysis of the owned PerfumersWorld lot.",
            "48.04% of the absolute is modeled; the listed docosene, triterpene and wax-ester constituents and the non-eluting 46.6% are uncomputed, not odorless. Nothing is renormalized.",
            "Trace character odorants (beta-damascenone, rose oxide, beta-ionone) are not listed on the certificate and are not modeled, so the modeled headspace understates rose character.",
        ),
    },
    "myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_AND_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=7LW00863",
                "document": "PerfumersWorld 7LW00863 Cabreuva Essential Oil, IFRA certificate and allergen declaration, batch CAB00863/26298",
                "supplier_botanical_label": "myrocarpus frondosus & m. fastigiatus (PerfumersWorld MSDS 'Occurs-in')",
                "owner_inventory_botanical_label": "Myrocarpus fastigiatus",
                "declared_pct": {
                    "alpha-bisabolol": 4.6708,
                    "farnesol": 2.1867,
                    "benzyl benzoate": 0.0945,
                    "citral": 0.0859,
                    "d-limonene": 0.0118,
                },
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Cabreuva EO (50% w/w in DPG)",
                "owned_supplier_reference": "PerfumersWorld 7LW00863",
                "owned_bottle_sku_verified": False,
                "profile_is_neat_oil": True,
                "main_constituent_evidence": {
                    "(E)-nerolidol": {
                        "azzi_2017_pct": 64.54,
                        "azzi_2017_source": "https://beilstein-journals.org/bjoc/articles/13/84",
                        "producer_specification_pct": "60-89",
                        "producer_specification_source": "https://www.alpacasa.com/wp-content/uploads/2024/05/DIN-PROD-017.-Ficha-tecnica.-Cabreuva-Oil-60-89_WEB.pdf",
                        "modeled": False,
                    },
                },
            },
            "alpha-bisabolol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "farnesol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl benzoate": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "citral": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "(E)-nerolidol",
                "reported_fraction": 0.6454,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
                "note": "64.54% in a commercial Myrocarpus fastigiatus oil (Azzi et al. 2017, Beilstein J. Org. Chem. 13); producer specification 60-89% (ALPACASA DIN-PROD-017). The engine's nerolidol air ODT (150 ppb) has no traceable primary source, so no row is added.",
            },
        ),
        "limitations": (
            "Declared levels of IFRA-restricted constituents and allergens for one supplier batch; not a full composition or an analysis of the owned bottle.",
            "Only 7.0497% of the oil is modeled (alpha-bisabolol, farnesol and traces). (E)-Nerolidol (about 60-89%) and the rest are uncomputed, not odorless, so the modeled headspace does not represent cabreuva character. Nothing is renormalized.",
            "The engine's nerolidol air ODT (150 ppb) could not be traced to a primary source (van Gemert 2011 lists water and ethanol values only), so nerolidol is not modeled.",
        ),
    },
    "pine oil perfumersworld 7kq07511 ifra declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_AND_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=7KQ07511",
                "document": "PerfumersWorld 7KQ07511 Pine Essential Oil, IFRA certificate and allergen declaration, batch PIN07511/26298",
                "supplier_cas": "84012-35-1 (Pinus sylvestris extractives)",
                "supplier_species_stated": False,
                "supplier_sds_description": "Proprietary Perfume Compound",
                "declared_pct": {
                    "longifolene": 8.8795,
                    "d-limonene": 2.8407,
                },
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Pine EO",
                "owned_supplier_reference": "PerfumersWorld 7KQ07511",
                "proxies_not_used": {
                    "ph_eur_pini_silvestris_aetheroleum_limonene_pct": "7-12",
                    "markowska_2022_commercial_scots_pine_limonene_pct": 11.58,
                    "reason": "the supplier's limonene (2.84%) and longifolene (8.88%) conflict with both",
                },
            },
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "longifolene",
                "reported_fraction": 0.088795,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
                "note": "no published air ODT was found (constituent research list 3)",
            },
        ),
        "limitations": (
            "Declared levels of two restricted constituents for the owned supplier batch; not a full composition. PerfumersWorld names no species or plant part and its SDS calls the product a proprietary perfume compound.",
            "Only 2.8407% of the oil is modeled (d-limonene). Longifolene (8.88%) and the undeclared remainder, including the pinenes, are uncomputed, not odorless, so the modeled headspace does not represent pine character. Nothing is renormalized.",
            "A longifolene level of 8.88% suggests a turpentine-type oil rather than Scots pine needle oil; this is an inference, not a supplier statement.",
        ),
    },
    "santalum album oil iso 3518 midpoint profile": {
        "analytical_method": "STANDARD_CHROMATOGRAPHIC_PROFILE_RANGES",
        "composition_basis": "SPECIFICATION_RANGE_MIDPOINT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://cdn.standards.iteh.ai/sist-preview/88588/1b7516dd3de5489a8752a4f51f66838c/ISO-3518-2025.pdf",
                "document": "ISO 3518:2025 Essential oil of sandalwood (Santalum album L.), 4th edition, Table 2 (SIST preview)",
                "standard_range_pct": {
                    "(Z)-alpha-santalol": "41.0-55.0",
                    "(Z)-beta-santalol": "16.0-24.0",
                    "(E,E)-farnesol": "n.d.-1.0",
                    "(Z)-lanceol": "n.d.-5.0",
                },
                "fraction_rule": "MIDPOINT_OF_STANDARD_MIN_MAX_RANGE",
                "upper_bound_only_rule": "NO_VALUE_INVENTED_KEPT_UNRESOLVED",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Sandalwood EO (10% in DPG)",
                "owned_supplier_reference": "PerfumersWorld 5WX12225 (batch SAN12225/26298)",
                "owned_species_recorded": False,
                "species_basis": "SUPPLIER_CAS_84787_70_2_EINECS_SANTALUM_ALBUM",
                "supplier_sds_description": "Proprietary Perfume Compound and Dipropylene Glycol",
                "profile_is_neat_oil": True,
                "cross_check_lot": {
                    "source": "https://www.revive-eo.com/wp-content/uploads/2026/03/REVIVE-GCMS-Report-Sandalwood-album-EO-6K.pdf",
                    "document": "REVIVE GC/MS report, Sandalwood (album) EO lot 6K, 16 Feb 2026",
                    "reported_pct": {
                        "cis-alpha-santalol": 45.24,
                        "cis-beta-santalol": 19.44,
                    },
                    "within_standard_ranges": True,
                },
            },
            "(Z)-alpha-santalol": {
                "mw_status": "NIST_WEBBOOK_FORMULA_MASS",
                "vp_status": "ESTIMATE_EPI_SUITE_V4_11_AS_PRINTED_BY_RIFM",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/11031-45-1.pdf",
                "odt_status": "PUBLISHED_AIR_THRESHOLD_DETECTION_OR_RECOGNITION_NOT_STATED",
                "odt_source": "Bajgrowicz JA, Frank I, Frater G, Hennig M (1998) Helv. Chim. Acta 81:1349-1358, as compiled in van Gemert (2011) AIR section (mg/m3)",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
                "odt_conversion": "0.0074 mg/m3 x 24450 / 220.35 = 0.8211 ppb",
            },
            "(Z)-beta-santalol": {
                "mw_status": "NIST_WEBBOOK_FORMULA_MASS",
                "vp_status": "ESTIMATE_EPI_SUITE_V4_11_AS_PRINTED_BY_RIFM",
                "vp_source": "https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/11031-45-1.pdf",
                "odt_status": "PUBLISHED_AIR_THRESHOLD_DETECTION_OR_RECOGNITION_NOT_STATED",
                "odt_source": "Bajgrowicz JA, Frank I, Frater G, Hennig M (1998) Helv. Chim. Acta 81:1349-1358, as compiled in van Gemert (2011) AIR section (mg/m3)",
                "gamma_status": "HEURISTIC_CLASS_INPUT",
                "owned_oil_activity_measured": False,
                "odt_conversion": "0.00054 mg/m3 x 24450 / 220.35 = 0.05992 ppb",
            },
        },
        "unresolved_constituents": (
            {
                "name": "(E,E)-farnesol",
                "reported_fraction_range": (0.0, 0.01),
                "missing_input": "UPPER_BOUND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "(Z)-lanceol",
                "reported_fraction_range": (0.0, 0.05),
                "missing_input": "UPPER_BOUND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "other constituents (cis-alpha-trans-bergamotol, epi-beta-santalol, nuciferols, santalenes and others)",
                "missing_input": "NOT_IN_STANDARD_RANGES",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "ISO 3518 ranges describe a conforming Santalum album oil, not the owned PerfumersWorld 5WX12225 lot. PerfumersWorld names no species (S. album is inferred from its CAS) and its SDS calls the product a proprietary perfume compound in DPG; if it is a compound, this profile does not describe it.",
            "68.0% of nominal composition is modeled ((Z)-alpha- and (Z)-beta-santalol). Farnesol and lanceol have upper bounds only; they, the other sesquiterpenols and the remainder are uncomputed, not odorless. Nothing is renormalized.",
            "Santalol VPs are EPI Suite estimates; the air thresholds are single-study values (Bajgrowicz 1998) with detection or recognition not stated.",
        ),
    },
    "tuberalia base perfumersworld 6nd09663 declaration profile": {
        "analytical_method": "SUPPLIER_IFRA_AND_ALLERGEN_DECLARATION",
        "composition_basis": "SUPPLIER_DECLARED_CONCENTRATION_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.perfumersworld.com/document-list.php?pro_id=6ND09663",
                "document": "PerfumersWorld 6ND09663 Tuberalia Base: SDS section 3, allergen declaration and IFRA restricted-materials table",
                "declared_pct": {
                    "linalool": 8.7605,
                    "hydroxycitronellal": 6.7878,
                    "benzyl salicylate": 4.9065,
                    "eugenol": 1.6008,
                    "benzyl benzoate": 0.9623,
                    "hexyl salicylate": 0.6406,
                    "benzyl alcohol": 0.6324,
                    "hexyl cinnamal": 0.2348,
                },
                "sds_section_3_band_pct": {
                    "linalool": (1.0, 10.0),
                    "benzyl salicylate": (1.0, 10.0),
                    "benzyl acetate": (1.0, 10.0),
                    "methyl benzoate": (1.0, 10.0),
                    "phenylethyl alcohol": (1.0, 10.0),
                    "cinnamyl alcohol": (0.1, 1.0),
                    "isoeugenol": (0.1, 1.0),
                    "methyl salicylate": (0.1, 1.0),
                },
                "band_only_rule": "SDS_HAZARD_BAND_NO_NOMINAL_FRACTION_KEPT_UNRESOLVED",
                "supplier_inconsistency": "SDS section 3 lists isoeugenol and cinnamyl alcohol at 0.1-1.0%, but neither appears in the allergen declaration or the IFRA restricted table",
                "fraction_rule": "DECLARED_CONCENTRATION_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Tuberlia Base",
                "owned_supplier_reference": "PerfumersWorld 6ND09663 (matched by name; the SKU is not recorded)",
                "owned_bottle_sku_verified": False,
            },
            "linalool": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "hydroxycitronellal": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl salicylate": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "eugenol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl benzoate": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl alcohol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "hexyl salicylate",
                "reported_fraction": 0.006406,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "hexyl cinnamal",
                "reported_fraction": 0.002348,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "benzyl acetate",
                "reported_fraction_range": (0.01, 0.1),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "methyl benzoate",
                "reported_fraction_range": (0.01, 0.1),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "phenylethyl alcohol",
                "reported_fraction_range": (0.01, 0.1),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cinnamyl alcohol",
                "reported_fraction_range": (0.001, 0.01),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "isoeugenol",
                "reported_fraction_range": (0.001, 0.01),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "methyl salicylate",
                "reported_fraction_range": (0.001, 0.01),
                "missing_input": "SDS_BAND_ONLY_NO_NOMINAL_FRACTION",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "A proprietary compound base: only declared allergen and IFRA-restricted levels are published, for an SKU matched by name, not an analysis of the owned bottle.",
            "Only 23.6503% of the base is modeled. Benzyl acetate, methyl benzoate and phenylethyl alcohol (1-10% bands), the 0.1-1% band constituents, hexyl salicylate, hexyl cinnamal and the undisclosed remainder are uncomputed, not odorless; tuberose character odorants (methyl anthranilate, indole and others) are not disclosed. Nothing is renormalized.",
        ),
    },
    "patchouli eo": {
        "analytical_method": "PUBLISHED_GC_LITERATURE_AVERAGE",
        "composition_basis": "LITERATURE_PERCENT_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://onlinelibrary.wiley.com/doi/full/10.1002/ffj.3418",
                "document": "van Beek TA, Joulain D (2018) The essential oil of patchouli, Pogostemon cablin: A review. Flavour Fragr J, doi:10.1002/ffj.3418, Table 4 (literature averages)",
                "reported_pct_average": {
                    "patchoulol": 39,
                    "alpha-bulnesene": 14,
                    "alpha-guaiene": 11,
                    "seychellene": 6.6,
                    "alpha-patchoulene": 4.5,
                    "(E)-beta-caryophyllene": 3.1,
                    "beta-patchoulene": 3.0,
                    "aciphyllene": 2.4,
                    "pogostol": 2.4,
                    "beta-elemene": 0.89,
                    "norpatchoulenol": 0.86,
                    "caryophyllene oxide": 0.73,
                    "alpha-humulene": 0.69,
                    "delta-elemene": 0.52,
                    "cycloseychellene": 0.46,
                    "beta-pinene": 0.2,
                    "germacrene D": 0.12,
                    "alpha-pinene": 0.09,
                    "limonene": 0.03,
                },
                "pogostone_excluded": "average 8.9%, range 0.1-27.7%, n = 24; Chinese-chemotype marker",
                "fraction_rule": "REPORTED_AVERAGE_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "HEURISTIC_NOMINAL_MODEL_PROXY",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Patchouli EO (Aroma&More, Indonesia, neat)",
                "owned_supplier_documents_found": False,
                "iso_3757_cross_check": {
                    "source": "https://cdn.standards.iteh.ai/samples/32035/01ce2b0f2fb947a5b31c02c63b4f3da3/ISO-3757-2002.pdf",
                    "patchoulol_pct": "27-35",
                    "alpha_bulnesene_pct": "13-21",
                    "alpha_guaiene_pct": "11-16",
                },
                "replaces": "uncited six-row profile (patchoulol 0.30, alpha-bulnesene 0.15, alpha-guaiene 0.12, seychellene 0.06, pogostol 0.03, beta-caryophyllene 0.03)",
            },
            "patchoulol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha-bulnesene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha-guaiene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "seychellene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "beta-caryophyllene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "pogostol": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "caryophyllene oxide": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "beta pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "germacrene d": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "alpha pinene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "limonene": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "alpha-patchoulene",
                "reported_fraction": 0.045,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-patchoulene",
                "reported_fraction": 0.03,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "aciphyllene",
                "reported_fraction": 0.024,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "beta-elemene",
                "reported_fraction": 0.0089,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "norpatchoulenol",
                "reported_fraction": 0.0086,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
                "note": "a key patchouli odorant at low level; no runtime headspace input in this module",
            },
            {
                "name": "alpha-humulene",
                "reported_fraction": 0.0069,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "delta-elemene",
                "reported_fraction": 0.0052,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
            {
                "name": "cycloseychellene",
                "reported_fraction": 0.0046,
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
            },
        ),
        "limitations": (
            "Literature average over oils of every origin; it is not an analysis of the owned Aroma&More Indonesian bottle, for which no supplier document was found.",
            "Only 77.27% of the oil is modeled. alpha-Patchoulene, beta-patchoulene, aciphyllene, norpatchoulenol and the other unresolved sesquiterpenes are uncomputed, not odorless. Nothing is renormalized.",
            "GC area percentages are used as nominal mass fractions.",
            "Patchouli Light Essential Oil, a lighter grade, reaches this whole-oil profile as a proxy.",
        ),
    },
    "styrax tonkinensis resin jecfa 2011 mean profile": {
        "analytical_method": "REGULATORY_ASSESSMENT_GC_FID_RESIN_SURVEY",
        "composition_basis": "REGULATORY_PERCENT_W_W_OF_RESIN_NOMINAL_MODEL_PROXY",
        "quantitative_evaluability": "PARTIAL_INPUT_COVERAGE",
        "input_authority": {
            "composition": {
                "source": "https://www.fao.org/fileadmin/user_upload/agns/pdf/jecfa/cta/74/benzoe_tonkinensis.pdf",
                "document": "FAO/JECFA 74th meeting (2011), Benzoe tonkinensis, Chemical and Technical Assessment (S. Rath), Tables 2 and 3",
                "reported_pct_w_w_of_resin": {
                    "benzoic acid": "17.5-46.3, mean 27.3",
                    "vanillin": "0.7-3.5, mean 1.8",
                    "benzyl benzoate": "0.8-2.4, mean 1.5",
                    "coniferyl benzoate": "15-57 (HPLC, 5 samples)",
                },
                "fraction_rule": "REPORTED_MEAN_PERCENT_DIVIDED_BY_100",
                "basis_to_mass_conversion": "REPORTED_AS_MASS_FRACTION_OF_RESIN",
                "owned_lot_match": "UNVERIFIED_CONDITIONAL_PROXY",
                "owned_stock_label": "Siam Benzoin (50% w/w in DPG)",
                "owned_supplier_recorded": False,
                "material_form_note": "JECFA analyses the raw resin; the owned stock is a resinoid preparation in DPG",
                "supplier_declaration_not_modeled": {
                    "source": "https://www.perfumersworld.com/document-list.php?pro_id=5QV13027",
                    "document": "PerfumersWorld 5QV13027 Benzoin Siam Resinoid 50% in DPG, allergen declaration (a matching product; the owned bottle's supplier is not recorded)",
                    "declared_pct_of_50pct_product": {
                        "benzyl benzoate": 1.0911,
                        "isoeugenol": 0.0915,
                        "eugenol": 0.0421,
                        "benzyl alcohol": 0.0146,
                    },
                },
                "replaces": "uncited six-row 'benzoin siam resinoid' profile for these stock names; that profile is unchanged for other names",
            },
            "benzoic acid": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "vanillin": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
            "benzyl benzoate": dict(_LEGACY_CONSTITUENT_INPUT_AUTHORITY),
        },
        "unresolved_constituents": (
            {
                "name": "coniferyl benzoate",
                "reported_fraction_range": (0.15, 0.57),
                "missing_input": "NO_RUNTIME_HEADSPACE_INPUT",
                "odor_contribution": "UNCOMPUTED",
                "note": "15-57% of the resin by HPLC (JECFA Table 3, 5 samples); essentially non-volatile",
            },
        ),
        "limitations": (
            "Regulatory survey of Laotian Siam benzoin resin; it is not an analysis of the owned stock, whose supplier is not recorded, and a resinoid can differ from the raw resin.",
            "Only 30.6% of the resin is modeled (benzoic acid, vanillin, benzyl benzoate). Coniferyl benzoate and the remainder are uncomputed, not odorless. Nothing is renormalized.",
            "PerfumersWorld 5QV13027 declares isoeugenol, eugenol and benzyl alcohol for a matching 50% DPG product; they are recorded, not modeled.",
        ),
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
    # Each contributing constituent's modeled vapour concentration (name, ppm v/v),
    # profile order. A note is read from one named constituent (yardstick note
    # markers), never from the summed ``oav`` (Rule 4).
    constituent_vapor_ppm: tuple[tuple[str, float], ...] = ()

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


def _profile_shares(constituents: Sequence[tuple]) -> tuple[tuple[float, ...], float]:
    """Return each row's nominal share and the unresolved remainder's share."""
    shares = tuple(max(0.0, float(row[1])) for row in constituents)
    characterized_fraction = min(
        1.0,
        max(0.0, sum(float(row[1]) for row in constituents)),
    )
    return shares, 1.0 - characterized_fraction


def _checked_remaining(row_count: int, remaining: Sequence[float]) -> tuple[float, ...]:
    """Return ``remaining`` as floats, or all 1.0 for an unevaporated natural."""
    if not remaining:
        return (1.0,) * (row_count + 1)
    if len(remaining) != row_count + 1:
        raise ValueError(
            f"remaining needs {row_count + 1} fractions (one per constituent row, "
            f"then the unresolved remainder); got {len(remaining)}"
        )
    return tuple(max(0.0, float(value)) for value in remaining)


def _mass_totals(
    shares: Sequence[float],
    unresolved: float,
    remaining: Sequence[float],
) -> tuple[float, float]:
    """Return the starting and current nominal mass totals of one natural."""
    start_total = sum(shares) + unresolved
    current_total = (
        sum(share * left for share, left in zip(shares, remaining, strict=False))
        + unresolved * remaining[-1]
    )
    return start_total, current_total


def _composition_weights(
    constituents: Sequence[tuple],
    remaining: Sequence[float],
) -> tuple[tuple[float, ...], float]:
    """Return per-row and remainder mass multipliers for a partly evaporated natural.

    ``remaining`` holds the fraction of each constituent row's starting mass
    still present (profile order), then that of the unresolved remainder; empty
    means nothing has evaporated and gives every multiplier exactly 1.0. The
    caller's ``active_g`` is what is left of the natural, so ``active_g *
    fraction * multiplier`` is the row's remaining starting mass and the rows
    plus the remainder add up to ``active_g`` again. No subset is rescaled to
    100%: the unresolved remainder keeps its own share.
    """
    left = _checked_remaining(len(constituents), remaining)
    shares, unresolved = _profile_shares(constituents)
    start_total, current_total = _mass_totals(shares, unresolved, left)
    if current_total <= 0.0:
        return (0.0,) * len(constituents), 0.0
    scale = start_total / current_total
    return tuple(value * scale for value in left[:-1]), left[-1] * scale


@dataclass(frozen=True, slots=True)
class NaturalCompositeVolatility:
    """Evaporation inputs of one natural profile at one temperature.

    One entry per constituent row in profile order, the order a ``remaining``
    tuple uses, then the unresolved remainder's nominal share.
    """

    fractions: tuple[float, ...]
    mw_g_mol: tuple[float, ...]
    escaping_tendency_pa: tuple[float, ...]
    unresolved_fraction: float

    def remaining_or_full(self, remaining: Sequence[float]) -> tuple[float, ...]:
        """Return ``remaining`` checked, or all 1.0 when nothing has evaporated."""
        return _checked_remaining(len(self.fractions), remaining)

    def mass_share(self, remaining: Sequence[float]) -> float:
        """Return the share of the natural's starting mass still present."""
        start_total, current_total = _mass_totals(
            tuple(max(0.0, fraction) for fraction in self.fractions),
            self.unresolved_fraction,
            self.remaining_or_full(remaining),
        )
        return current_total / start_total if start_total > 0.0 else 0.0


def composite_constituent_volatility(
    material_name: str,
    *,
    temperature_K: float = 298.15,  # noqa: N803
    gamma_estimate: float = 0.6,
) -> NaturalCompositeVolatility | None:
    """Return each constituent row's evaporation inputs for the temporal model.

    The escaping tendency is ``gamma * VP`` at ``temperature_K`` with the same
    temperature-adjusted VP and gamma that :func:`composite_headspace` uses, so
    a constituent leaves at the rate its own headspace implies. None when the
    natural has no profile.
    """
    raw_constituents = get_constituents(material_name)
    if raw_constituents is None:
        return None
    rows, _used_shared_fallback = _temperature_adjusted_constituent_rows(
        tuple(tuple(row) for row in raw_constituents),
        float(temperature_K),
        float(gamma_estimate),
        None,
    )
    _shares, unresolved = _profile_shares(rows)
    return NaturalCompositeVolatility(
        fractions=tuple(float(row[1]) for row in rows),
        mw_g_mol=tuple(float(row[2]) for row in rows),
        escaping_tendency_pa=tuple(float(row[5]) * float(row[3]) for row in rows),
        unresolved_fraction=unresolved,
    )


def composite_replacement_moles(
    material_name: str,
    active_g: float,
    parent_moles: float,
    *,
    remaining: Sequence[float] = (),
) -> float | None:
    """Return residual-parent plus resolved-constituent moles for a natural.

    The characterized model fraction is represented by constituent moles. The
    unresolved fraction uses the profile's harmonic-mean MW for mole-pool
    bookkeeping. Its uncomputed odor contribution is unknown, not odorless.
    GC-FID area fractions are nominal model proxies, not measured mass fractions.
    ``remaining`` describes a partly evaporated natural (see
    :func:`_composition_weights`); the remainder keeps the unevaporated
    profile's harmonic-mean MW.
    """
    constituents = get_constituents(material_name)
    if constituents is None:
        return None

    _ = parent_moles  # retained for API compatibility and caller bookkeeping
    row_weights, unresolved_weight = _composition_weights(constituents, remaining)
    characterized_fraction = min(
        1.0,
        max(0.0, sum(float(row[1]) for row in constituents)),
    )
    profile_moles_per_g = sum(
        max(0.0, float(fraction)) / float(mw)
        for _name, fraction, mw, _vp, _odt, _gamma in constituents
        if float(mw) > 0
    )
    resolved_moles_per_g = sum(
        max(0.0, float(row[1])) * weight / float(row[2])
        for row, weight in zip(constituents, row_weights, strict=True)
        if float(row[2]) > 0
    )
    resolved_constituent_moles = max(0.0, float(active_g)) * resolved_moles_per_g
    effective_profile_mw = (
        characterized_fraction / profile_moles_per_g
        if characterized_fraction > 0 and profile_moles_per_g > 0
        else None
    )
    residual_parent_moles = (
        max(0.0, float(active_g))
        * (1.0 - characterized_fraction)
        * unresolved_weight
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
    remaining: Sequence[float] = (),
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
        remaining: for a partly evaporated natural, the fraction of each
            constituent row's starting mass still present, then that of the
            unresolved remainder; empty means nothing has evaporated. See
            :func:`_composition_weights`.

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

    row_weights, _unresolved_weight = _composition_weights(constituents, remaining)
    for (name, fraction, mw, constituent_vp_pa, odt_ppb, gamma_value), weight in zip(
        constituents, row_weights, strict=True
    ):
        constituent_mass_g = active_g * fraction * weight
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
            remaining=remaining,
        )
        if replacement_moles is not None:
            effective_total_moles += replacement_moles - max(
                0.0,
                float(parent_moles),
            )

    if effective_total_moles <= 0:
        return None

    contributing_constituents = 0
    constituent_vapor: list[tuple[str, float]] = []
    for name, moles, constituent_vp_pa, odt_ppb, _fraction, gamma_value in constituent_rows:
        if moles <= 0:
            continue
        contributing_constituents += 1
        x_i = moles / effective_total_moles
        partial_pressure = gamma_value * x_i * constituent_vp_pa
        vapor_ppm = 1e6 * partial_pressure / P_ATM
        constituent_vapor.append((str(name), float(vapor_ppm)))
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
        constituent_vapor_ppm=tuple(constituent_vapor),
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
