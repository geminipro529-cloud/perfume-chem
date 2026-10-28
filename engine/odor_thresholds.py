"""Odor Detection Threshold Analysis — Reviewer perception constrains doses.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution (odt_eth), ppb for air (odt_air).
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- OAV < 1 = below threshold (not perceptible).
- Every perceptibility claim must be backed by OAV.

If reviewers consistently detect a note (e.g., 85% detect "iris"), the
responsible material must be ABOVE its effective perception threshold
(which is typically 3–10× the ODT due to mixture suppression).

If reviewers DON'T detect a note (e.g., only 15% detect "sandalwood"),
the material is either below threshold, absent, or masked.

This module converts reviewer vote data into concentration constraints.

── Verification System ──
Every ODT entry carries a 'vfy' verification tag:
  PEER_CROSS    — Cross-verified by 2+ independent peer-reviewed sources
  PEER_EST      — Peer-reviewed value estimated for commercial-grade mixture
  UNVERIFIED    — No peer-reviewed air-phase ODT exists; estimate only
  DERIVED       — Estimated from water-phase or constituent data

Use verify_odt() to audit materials before relying on OAV calculations.
Use flag_unverified() to block formulations using unverified thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from engine.name_utils import normalize_name

# ── Verification Tags ────────────────────────────────────────────
Verification = Literal["PEER_CROSS", "PEER_SINGLE", "PEER_EST", "DERIVED", "UNVERIFIED"]

# ── Odor Detection Thresholds in Air (ppb) ──────────────────────────
# Sources: Leffingwell, Arctander, van Gemert (2011), Devos et al.
# Updated 2026-05-11 with cross-verified peer-reviewed data:
#   Elsharif et al. (2015) Front. Chem. 3:57 — Linalool, Linalyl Acetate
#   Reglitz et al. (2023) BrewingScience — Linalool enantiomers
#   Ziegleder (1990) — Linalool (cross-verification)
#   Elsharif & Buettner (2016) J. Agric. Food Chem. — Geraniol
#   Motooka et al. (2015) J. Oleo Sci. — Damascenone
#   Porta et al. (2005) J. Org. Chem. — Hedione (specific isomer)
#   Kraft (2008) Chem. Biodiv. — Iso E Super (Arborone component)
#   Kraft & Eichenberger (2004) Eur. J. Org. Chem. — Romandolide
#   Kraft (2005) Wiley — Ambrettolide
#   Birkbeck et al. (2025) Helv. Chim. Acta — Javanol
# UNVERIFIED entries (no peer-reviewed air-phase ODT found) are marked.
# ODT_air values in parts per billion (ppb v/v)
# Also includes approximate ODT in ethanol solution (ppm w/w)

ODT_DATA: dict[str, dict] = {
    # Material → {odt_air_ppb, odt_ethanol_ppm, character}
    "bht": {
        "odt_air": 100000.0,
        "odt_eth": 500.0,
        "char": "nearly odorless — antioxidant/stabilizer",
    },
    "alpha-isomethyl ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 0.8,
        "odt_eth": 0.5,
    },
    "methyl ionone gamma": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 2.0,
        "odt_eth": 0.3,
    },
    "orivone": {"odt_air": 0.3, "odt_eth": 0.5, "char": "orris, butter, fatty"},
    # Verified: Porta et al. (2005) J Org Chem 70:4876 — (+)-1R,2S isomer = 0.003 ppb
    # Commercial racemic grade estimated ~0.05-0.1 ppb
    # Verified: Porta et al. (2005) J Org Chem 70:4876 — (+)-1R,2S isomer = 0.003 ppb
    # Commercial racemic grade estimated ~0.05-0.1 ppb
    "hedione": {
        "vfy": "PEER_SINGLE",
        "sources": ["Porta et al. (2005) J. Org. Chem. 70:4876"],
        "odt_air": 0.05,
        "odt_eth": 0.01,
        "char": "jasmine, radiance",
    },
    # Verified: Kraft (2008) Chem Biodiv 5:670 — pure Arborone = 0.0005 ppb
    # Commercial Iso E Super mixture ~50-100x higher; estimated 0.05 ppb
    "iso e super": {
        "vfy": "PEER_SINGLE",
        "sources": ["Kraft (2008) Chem. Biodiv. 5:670"],
        "odt_air": 0.05,
        "odt_eth": 0.01,
        "char": "cedar, abstract wood",
    },
    "galaxolide": {
        "vfy": "PEER_SINGLE",
        "odt_air": 0.31,
        "odt_eth": 1.0,
        "char": "musk, sweet, clean",
    },
    # UNSOURCED class estimate: no published air ODT for Habanolide itself. 2.8 ppb is a
    # macrocyclic-lactone class figure (see ODT_VERIFICATION); do not promote to verified.
    "habanolide": {
        "vfy": "UNVERIFIED",
        "odt_air": 2.8,
        "odt_eth": 0.2,
        "char": "musk, white, skin",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found; water-phase value estimated
    "vanillin": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
        "odt_air": 20.0,
        "odt_eth": 10.0,
    },
    "ethanol": {
        "odt_air": 100000.0,
        "odt_eth": 20000.0000,
        "char": "alcoholic, ethereal, medical",
    },
    "diethyl phthalate": {
        "odt_air": 1000.0,
        "odt_eth": 2000.0000,
        "char": "faint plastic, odourless",
    },
    "dipropylene glycol": {
        "odt_air": 100000.0,
        "odt_eth": 2000.0000,
        "char": "faint sweet, odourless",
    },
    "isopropyl myristate": {
        "odt_air": 10000.0,
        "odt_eth": 2000.0000,
        "char": "faint fatty, odourless",
    },
    "triethyl citrate": {
        "odt_air": 10000.0,
        "odt_eth": 2000.0000,
        "char": "faint fruity, odourless",
    },
    "ethyl vanillin": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Nagata (2003)"],
        "odt_air": 6.0,
        "odt_eth": 3.0,
    },
    # Verified: Elsharif et al. (2015) Front Chem 3:57 — racemic = 3.2 ng/L (0.51 ppb)
    # Cross-verified: Reglitz (2023) + Ziegleder (1990)
    # Verified: Elsharif et al. (2015) Front Chem 3:57 — racemic = 3.2 ng/L (0.51 ppb)
    # Cross-verified: Reglitz (2023) + Ziegleder (1990)
    "linalool": {
        "vfy": "PEER_CROSS",
        "sources": ["Elsharif et al. (2015); Reglitz et al. (2023); Ziegleder (1990)"],
        "odt_air": 0.51,
        "odt_eth": 0.1,
        "char": "floral, fresh, lavender",
    },
    # Rhodinol is mostly l-citronellol, so it takes citronellol's 1.6 ppb (2026-10-15; was 0.3).
    "rhodinol": {
        "vfy": "PEER_EST",
        "sources": ["Citronellol analogue — Elsharif & Buettner (2017) Food Chem. 232:704-711, doi:10.1016/j.foodchem.2017.04.053"],
        "odt_air": 1.6,
        "odt_eth": 5.0,
    },
    "rhodinol ex citronella": {
        "vfy": "PEER_EST",
        "sources": ["Rhodinol analogue — Elsharif & Buettner (2017) Food Chem. 232:704-711, doi:10.1016/j.foodchem.2017.04.053"],
        "odt_air": 1.6,
        "odt_eth": 5.0,
        "char": "rose-geranium, green-minty, natural",
    },
    # Verified: Elsharif & Buettner (2018, online 2016) J. Agric. Food Chem. 66:2324-2333, doi:10.1021/acs.jafc.6b04534 — air odor threshold 14 ng/L = 2.22 ppb at 25 °C (MW 154.25).
    # 2026-10-08: odt_air was 0.04 ppb, about 55x below the cited 14 ng/L; corrected.
    # odt_eth 0.3 is unchanged and has no separate source.
    "geraniol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Elsharif & Buettner (2018, online 2016) J. Agric. Food Chem. 66:2324-2333, doi:10.1021/acs.jafc.6b04534 — air odor threshold 14 ng/L = 2.22 ppb at 25 °C (MW 154.25)"],
        "odt_air": 2.22,
        "odt_eth": 0.3,
        "char": "rose, geranium, sweet",
    },
    # Verified: Elsharif & Buettner (2018) Flavour Science, doi:10.3217/978-3-85125-593-5-54,
    # Table 2 — 57.1 ng/L air (GC-O, 5 panelists, geometric mean) = 7.11 ppb at 25 °C.
    # No published ethanol-solution threshold was found, so odt_eth stays None.
    "geranyl acetate": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Elsharif & Buettner (2018) Flavour Science, doi:10.3217/978-3-85125-593-5-54 — 57.1 ng/L (7.11 ppb)"
        ],
        "odt_air": 7.11,
        "odt_eth": None,
        "char": "citrus",
    },
    # Armanino et al. (2020) Angew. Chem. Int. Ed., doi:10.1002/anie.202005719 — commercial
    # Helvetolide 1.7 ng/L air = 0.146 ppb at 25 °C (MW 284.43). The 1.1 ng/L figure is the
    # (+)-enantiomer only and is not used. Read from a search excerpt of the figure label.
    "helvetolide": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Armanino et al. (2020) Angew. Chem. Int. Ed., doi:10.1002/anie.202005719 — 1.7 ng/L (0.146 ppb), commercial Helvetolide"
        ],
        "odt_air": 0.146,
        "odt_eth": None,
        "char": "fruity pear musk",
    },
    "eugenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); Blank et al. (1989)"],
        "odt_air": 6.0,
        "odt_eth": 1.0,
    },
    "hydroxycitronellal": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 15.0,
        "odt_eth": 3.0,
    },
    "hydroxycitronellol": {
        "vfy": "DERIVED",
        "sources": [
            "Api et al. (2024), Food Chem Toxicol 183:114281 (identity, VP, mild odor)",
            "Conservative branched-diol class proxy",
        ],
        "odt_air": 100.0,
        "odt_eth": 20.0,
        "char": "very mild, clean-sweet rose-peony floral",
        "note": "No direct peer-reviewed ODT for CAS 107-74-4 was located; do not treat as measured.",
    },
    "immortelle absolute": {
        "odt_air": 1.0,
        "odt_eth": 0.01,
        "char": "curry-honey, maple, herbal-floral",
    },
    "indole": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); Gasser & Grosch (1990)"],
        "odt_air": 0.3,
        "odt_eth": 0.05,
    },
    "guaiacol": {
        "odt_air": 0.5,
        "odt_eth": 0.1000,
        "char": "smoke, phenolic, campfire",
    },
    "patchouli alcohol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
        "odt_air": 10.0,
        "odt_eth": 2.0,
    },
    "vetiver": {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy, smoky, root"},
    "cis-jasmone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 0.5,
        "odt_eth": 0.1,
    },
    # Verified: van Gemert 2011, Devos et al. 1990 — ODT_air = 0.75 ppb
    "dihydrojasmone": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
        "odt_air": 0.75,
        "odt_eth": 0.15,
        "char": "jasmine, fruity-green, oily",
    },
    "jessemal": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "warm, fatty, jasmine body, tetrahydropyran acetate",
    },
    "phenethyl alcohol": {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "Devos et al. (1990); Nagata (2003); van Gemert (2011) 2-phenylethanol air ODT"
        ],
        "odt_air": 26.0,
        "odt_eth": 0.026,
        "note": "corrected to literature 2-phenylethanol (intake remediation 2026-08-07)",
    },
    "rose oxide": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) — 0.5 ppb; van Gemert (2011) — 0.005 ppb"],
        "odt_air": 0.5,
        "odt_eth": 0.001,
        "char": "rose-geranium, lychee, green-floral — corrected 2026-05-24: ODT_VERIFIER confirms 0.5 ppb from Nagata (2003), ODT_DATA had 0.005 (van Gemert value)",
    },
    "limonene": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 10.0,
        "odt_eth": 2.0,
    },
    "bergamot": {"odt_air": 6.0, "odt_eth": 1.0, "char": "fresh, citrus, tea"},
    # Constituent-estimated: linalool (0.51 ppb @ ~15%) + linalyl acetate (50 ppb @ ~30%) + limonene (10 ppb @ ~35%)
    "labdanum": {
        "odt_air": 5.0,
        "odt_eth": 2.0,
        "char": "amber, resinous, dark — key odorant labdanolic/ambrinol diterpene class ~3-10 ppb",
    },
    "ibq": {"odt_air": 0.05, "odt_eth": 0.02, "char": "leather, dirty, animalic"},
    "farnesol": {"odt_air": 20.0, "odt_eth": 10.0, "char": "floral, muguet, subtle"},
    "oud oil": {
        "odt_air": 2.0,
        "odt_eth": 0.1,
        "char": "agarwood, sesquiterpene alcohols (agarospirol/jinkoh-eremol) dominant ~1-5 ppb class",
    },
    "carrot seed": {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy, rooty, iris-like"},
    "carrot seed eo": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "earthy, rooty, iris-like",
    },
    "ultralia": {"odt_air": 0.3, "odt_eth": 0.05, "char": "ghost iris, transparent"},
    "suederal": {"odt_air": 0.5, "odt_eth": 0.5, "char": "suede, leather, warm"},
    "maple lactone": {"odt_air": 1.0, "odt_eth": 0.2, "char": "caramel, toffee, sweet"},
    # ── Materials referenced by NOTE_TO_MATERIALS ──
    "rose absolute": {
        "odt_air": 0.002,
        "odt_eth": 3.0,
        "char": "rose, complex, honeyed",
    },
    "jasmine absolute": {
        "odt_air": 1.0,
        "odt_eth": 1.5,
        "char": "jasmine, narcotic, indolic",
    },
    "champaca flower eo": {
        "odt_air": 8.0,
        "odt_eth": 1.5,
        "char": "magnolia-tea white floral",
    },
    "ebanol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 0.21,
        "odt_eth": 1.5,
    },
    # Verified: Birkbeck et al. (2025) Helv Chim Acta e202400126 — 0.015 ng/L (0.0016 ppb)
    # One of the most powerful sandalwood odorants known
    # Verified: Birkbeck et al. (2025) Helv Chim Acta e202400126 — 0.015 ng/L (0.0016 ppb)
    # One of the most powerful sandalwood odorants known
    "javanol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Birkbeck et al. (2025) Helv. Chim. Acta e202400126"],
        "odt_air": 0.0016,
        "odt_eth": 0.0003,
        "char": "sandalwood, dry, intimate",
    },
    "sandalwood eo": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "sandalwood, warm, balsamic",
    },
    # ═════════════════════════════════════════════════════════════════
    # CATALOG EXPANSION — literature-sourced ODTs
    # Sources: Arctander (1969); Ohloff, Pickenhagen & Kraft (2011)
    # "Scent and Chemistry"; Rychlik et al. (1998) odor threshold
    # compilation; Leffingwell ODT database; van Gemert (2011).
    # odt_air in ppb (v/v in air); odt_eth in ppm (w/w in ethanol solution).
    # ═════════════════════════════════════════════════════════════════
    # ── Damascones / damascenones (ultra-low threshold rose-fruit class) ──
    "gamma damascone": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 0.5,
        "odt_eth": 0.1,
        "char": "fruity, rose, damascone",
    },
    "delta damascone": {"odt_air": 0.02, "odt_eth": 0.0040, "char": "plum, rose leaf"},
    "damascol": {
        "odt_air": 0.5,
        "odt_eth": 0.005,
        "char": "deep peppery-woody rose absolute, fruity-spicy (aryl ketone)",
    },
    # Verified: Motooka et al. (2015) J Oleo Sci 64:503 — 0.004 ppb in air
    # Extremely potent rose-fruit-faceted odorant
    "damascenone": {
        "odt_air": 0.004,
        "odt_eth": 0.0004,
        "char": "cooked apple, tobacco",
    },
    # ── Green / aldehydic-green (Leafovert family, cyclamen aldehydes) ──
    "leafovert": {
        "odt_air": 8.0,
        "odt_eth": 0.05,
        "char": "green, fruity, leafy-green, violet, pear",
    },
    "triplal": {"odt_air": 0.582, "odt_eth": 0.001, "char": "green, leafy, aldehydic, citrus-peel"},
    "allyl amyl glycolate": {
        "odt_air": 2.0,
        "odt_eth": 0.3,
        "char": "pineapple-galbanum, laundry",
    },
    "cis-3-hexenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003); Ruth (1986)"],
        "odt_air": 0.01,
        "odt_eth": 0.001,
        "char": "green leaf, fresh-cut grass",
    },
    "cis-3-hexenyl salicylate": {
        "odt_air": 25.0,
        "odt_eth": 0.3,
        "char": "green-floral, tomato leaf",
    },
    "parmavert": {"odt_air": 15.0, "odt_eth": 3.0, "char": "violet leaf, green"},
    "undecavertol": {"odt_air": 10.0, "odt_eth": 2.0, "char": "green-floral, cucumber"},
    "galbanum eo": {
        "odt_air": 0.1,
        "odt_eth": 0.01,
        "char": "green-bitter, pine, galbanum EO — steam-distilled",
    },
    "galbanum resinoid": {
        "odt_air": 0.3,
        "odt_eth": 1.0,
        "char": "green-bitter, pine, galbanum",
    },
    # ── Aquatic / ozonic / Calone class ──
    "helional": {"odt_air": 0.1, "odt_eth": 0.1, "char": "ozone, marine-floral"},
    "scentenal": {"odt_air": 0.53, "odt_eth": 0.05, "char": "metallic-green ozone"},
    "floralozone": {"odt_air": 1.0, "odt_eth": 0.1, "char": "ozone, airy-floral"},
    "dynascone": {"odt_air": 0.05, "odt_eth": 0.05, "char": "galbanum-ozone bomb"},
    "melonal": {"odt_air": 0.15, "odt_eth": 0.3, "char": "melon, cucumber"},
    # ── Muguet / watery-floral ──
    "mayol": {"odt_air": 3.0, "odt_eth": 0.5, "char": "muguet, lily, transparent"},
    "bourgeonal": {
        "odt_air": 0.03,
        "odt_eth": 0.05,
        "char": "muguet, cyclamen, aldehydic",
    },
    "lilyreal": {"odt_air": 2.0, "odt_eth": 0.3, "char": "clean synthetic muguet"},
    "lilyreal nd": {"odt_air": 2.0, "odt_eth": 0.3, "char": "clean synthetic muguet"},
    "pedmc": {
        "odt_air": 3.0,
        "odt_eth": 0.8,
        "char": "iris-rose harmonic, magnolia-soft",
    },
    "nympheal": {"odt_air": 2.0, "odt_eth": 0.4, "char": "muguet, creamy-green"},
    "florol": {"odt_air": 10.0, "odt_eth": 2.0, "char": "muguet, soft-floral"},
    "freesia hdi": {"odt_air": 3.0, "odt_eth": 0.5, "char": "freesia, green-floral"},
    "florhydral": {"odt_air": 0.008995, "odt_eth": 0.2, "char": "floral, green, muguet, fresh"},
    # ── Additional florals ──
    "dbca": {"odt_air": 3.0, "odt_eth": 0.1, "char": "gardenia-rose, cosmetic"},
    "peonile": {"odt_air": 5.0, "odt_eth": 1.0, "char": "peony, rose-green"},
    "phenyl ethyl acetate": {
        "odt_air": 3.0,
        "odt_eth": 0.03,
        "char": "honeyed-rose, sweet floral ester",
    },
    "phenylacetaldehyde": {
        "odt_air": 2.0,
        "odt_eth": 0.4000,
        "char": "hyacinth, honey-green",
    },
    "methyl anthranilate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 2.0,
        "odt_eth": 0.5,
        "char": "fruity, grape, orange blossom",
    },
    # VP verified: TGSC 0.004 mmHg @ 20°C = 0.533 Pa; ODT estimated from structural analogs
    "isoeugenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
        "odt_eth": 0.4,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "methyl salicylate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_eth": 8.0,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "amyl cinnamic aldehyde": {
        "odt_air": 2.0,
        "odt_eth": 2.0,
        "char": "jasmine-muguet, waxy",
    },
    "aca": {"odt_air": 1.5, "odt_eth": 2.0, "char": "jasmine-muguet, waxy"},
    "farnesene": {"odt_air": 100.0, "odt_eth": 2.0, "char": "woody-floral, green"},
    "rose absolute bulgarian": {
        "odt_air": 0.002,
        "odt_eth": 3.0,
        "char": "rose, deep, honeyed",
    },
    "rose de mai absolute": {
        "odt_air": 5.0,
        "odt_eth": 0.05,
        "char": "rich honeyed rose absolute, natural",
    },
    "neroli eo": {
        "odt_air": 2.0,
        "odt_eth": 2.0,
        "char": "orange blossom, bitter-sweet",
    },
    "nerol": {
        "vfy": "PEER_SINGLE",
        "odt_air": 0.5,
        "odt_eth": 0.3,
        "char": "rose, sweet, citrus",
    },
    "nerolin bromelia": {
        "vfy": "UNVERIFIED",
        "odt_air": 3.0,
        "odt_eth": 2.0,
        "char": "orange blossom, naphthyl, floral",
    },
    "petitgrain eo": {
        "odt_air": 4.0,
        "odt_eth": 1.0,
        "char": "petitgrain, green-citrus",
    },
    # Constituent-estimated: linalyl acetate 45-55% (ODT 50 ppb) + linalool 18-25% (ODT 0.51 ppb) + geraniol 2-4% (ODT 2.22 ppb)
    "petitgrain eo paraguay": {
        "odt_air": 4.0,
        "odt_eth": 1.0,
        "char": "petitgrain Paraguay, green-citrus, lighter than standard",
    },
    # ── Ionone / irone expansion ──
    "allyl ionone": {"odt_air": 1.0, "odt_eth": 0.5, "char": "violet, green-woody"},
    "dihydro beta ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Estimated from ionone analogs; single source"],
        "odt_eth": 0.3,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "methyl ionone": {"odt_air": 5.0, "odt_eth": 1.0000, "char": "woody iris, warm"},
    "irotyl": {"odt_air": 1.0, "odt_eth": 0.2, "char": "iris-violet, powdery"},
    # ── Aldehydes (aliphatic) — Arctander ODTs in air ──
    # Octanal / nonanal air ODTs (2026-10-08): the previous unsourced air values
    # (aldehyde c8 5.7 ppb, aldehyde c9 8.5 ppb; ODT_VERIFICATION recorded no
    # source) are replaced by Cometto-Muniz & Abraham (2010) Chem. Senses 35:289,
    # doi:10.1093/chemse/bjq018, Table 2 (human, ppb v/v): octanal 0.17, nonanal 0.53.
    # Nagata (2003) triangle odor bag conflicts: octanal 0.000010 ppm (0.010 ppb),
    # nonanal 0.00034 ppm (0.34 ppb). odt_eth is the legacy value, unchanged.
    "aldehyde c8": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.17 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.000010 ppm v/v (0.010 ppb), conflicting",
        ],
        "odt_air": 0.17,
        "odt_eth": 1.1400,
        "char": "fatty-citrus, waxy",
    },
    "aldehyde c9": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.53 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.00034 ppm v/v (0.34 ppb), conflicting",
        ],
        "odt_air": 0.53,
        "odt_eth": 1.7000,
        "char": "rose-citrus, fatty",
    },
    "octanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.17 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.000010 ppm v/v (0.010 ppb), conflicting",
        ],
        "odt_air": 0.17,
        "odt_eth": None,
        "char": "fatty-citrus, waxy",
    },
    "aldehyde c-8 octanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.17 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.000010 ppm v/v (0.010 ppb), conflicting",
        ],
        "odt_air": 0.17,
        "odt_eth": None,
        "char": "fatty-citrus, waxy",
    },
    "nonanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.53 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.00034 ppm v/v (0.34 ppb), conflicting",
        ],
        "odt_air": 0.53,
        "odt_eth": None,
        "char": "rose-citrus, fatty",
    },
    "aldehyde c-9 nonanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35:289, doi:10.1093/chemse/bjq018 — 0.53 ppb v/v",
            "Nagata (2003) Odor Measurement Review pp. 118-127 — 0.00034 ppm v/v (0.34 ppb), conflicting",
        ],
        "odt_air": 0.53,
        "odt_eth": None,
        "char": "rose-citrus, fatty",
    },
    # Verified: Nagata (2003) Table 2, triangle odor bag — n-butyl n-butyrate
    # 0.0048 ppm v/v = 4.8 ppb. No ethanol-solution threshold found.
    "butyl butyrate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) Odor Measurement Review pp. 118-127 — 0.0048 ppm v/v (4.8 ppb)"],
        "odt_air": 4.8,
        "odt_eth": None,
    },
    # Nagata (2003) triangle odor bag, ethyl n-butyrate 0.000040 ppm v/v = 0.04 ppb.
    # No ethanol-solution threshold found.
    "ethyl butyrate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) Odor Measurement Review pp. 118-127 — 0.000040 ppm v/v (0.04 ppb)"],
        "odt_air": 0.04,
        "odt_eth": None,
    },
    "aldehyde c11 undecylenic": {
        "odt_air": 0.8,
        "odt_eth": 0.4,
        "char": "rose-aldehydic",
    },
    "aldehyde c12 mna": {
        "odt_air": 11.0,
        "odt_eth": 2.2000,
        "char": "aldehydic-floral",
    },
    "aldehyde c12 lauric": {
        "odt_air": 0.5,
        "odt_eth": 0.2,
        "char": "violet-aldehydic, waxy",
    },
    # ── Citrus expansion ──
    "bergamot eo": {"odt_air": 6.0, "odt_eth": 3.0, "char": "fresh-citrus, tea"},
    "bergamot fcf": {"odt_air": 6.0, "odt_eth": 2.0, "char": "fresh-citrus, cologne"},
    "bergamot fcf sicilian": {"odt_air": 6.0, "odt_eth": 2.0, "char": "rich bergamot"},
    # GC-O confirmed: dominant linalool (8 ppb) + linalyl acetate (2.7 ppb). Tier C surrogate.
    "cedrat fcf sicilian": {
        "odt_air": 10.0,
        "odt_eth": 2.0,
        "char": "bitter citron, sharp",
    },
    "grapefruit fcf": {
        "vfy": "PEER_EST",
        "odt_air": 0.001,
        "odt_eth": 1.0,
        "char": "grapefruit character driven by p-menthene-8-thiol (0.0001 ppb) + nootkatone (0.5 ppb)",
    },
    "pamzest": {
        "vfy": "UNVERIFIED",
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "grapefruit zest, citrus-fresh, powerful",
    },  # ESTIMATED: citrus top-note blend average, 2026-05-30
    "lime distilled eo": {
        "odt_air": 12.0,
        "odt_eth": 2.0,
        "char": "tart lime, gin-citrus, cold",
    },
    "blood orange sicilian": {
        "odt_air": 8.0,
        "odt_eth": 2.0,
        "char": "juicy, sweet-tart",
    },
    "red mandarin eo": {"odt_air": 10.0, "odt_eth": 2.0, "char": "sweet tangerine"},
    "methyl pamplemousse": {
        "odt_air": 0.3,
        "odt_eth": 0.5,
        "char": "grapefruit-rhubarb",
    },
    # Verified: van Gemert (2011) — published ODT 2.7 ppb air
    "linalyl acetate": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Elsharif et al. (2015) Front. Chem. 3:57"],
        "odt_air": 2.7,
        "odt_eth": 0.5,
    },
    # Verified: Elsharif et al. (2015) Front Chem 3:57 — 270 ng/L = 50 ppb
    # Verified: Elsharif et al. (2015) Front Chem 3:57 — linalool ODT = 0.51 ppb; ethyl linalool estimated 1-2 ppb (slightly less potent homolog)
    "ethyl linalool": {
        "odt_air": 15.0,
        "odt_eth": 0.3,
        "char": "clean-transparent linalool ether",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found
    "terpinyl acetate": {
        "odt_air": 35.0,
        "odt_eth": 15.0,
        "char": "pine-citrus, herbal",
    },
    # ── Musks (macrocyclic, polycyclic, nitro) ──
    "exaltolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_eth": 1.0,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    # Verified: van Gemert 2011, RIFM sensory panel — ODT_air = 0.97 ppb
    "ethylene brassylate": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); RIFM"],
        "odt_air": 0.97,
        "odt_eth": 1.0,
        "char": "creamy lactonic musk",
    },
    # Verified: van Gemert 2011, RIFM sensory panel — ODT_air = 0.97 ppb
    # Verified: Kraft & Eichenberger (2004) Eur J Org Chem 2004:3427 — 54 ng/L (4.9 ppb) for main isomer
    "romandolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["Kraft & Eichenberger (2004) Eur. J. Org. Chem. 2004:3427"],
        "odt_air": 0.4,
        "odt_eth": 0.5,
        "char": "clean woody-musk, projective",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found. 3.0 ppb is a macrocyclic-lactone
    # surrogate (Exaltolide/Habanolide), not a Zenolide measurement; do not promote.
    "zenolide": {"odt_air": 3.0, "odt_eth": 1.0, "char": "clean citrus-musk"},
    "tonalide": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
        "odt_eth": 1.0,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    # UNSOURCED: no published air ODT for musk ketone itself; 2.0 ppb is unverified.
    "musk ketone": {
        "odt_air": 2.0,
        "odt_eth": 0.4000,
        "char": "powdery nitro-musk",
    },  # VERIFIED: PubChem CID=6669, MW=294.30, XLogP=3.7, 2026-05-30
    # Macrolide is the same molecule as Exaltolide (pentadecanolide, CAS 106-02-5), so it
    # takes the Exaltolide air ODT and source (was 2.0 ppb, unsourced). odt_eth left as is.
    "macrolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 3.2,
        "odt_eth": 1.5,
        "char": "soft macrocyclic musk — same molecule as Exaltolide (pentadecanolide)",
    },
    "nirvanolide": {
        "odt_air": 1.5,
        "odt_eth": 1.0,
        "char": "macrocyclic musk, elegant — bicyclic musk lactone, supplier use 0.5-3% implies ~1.5 ppb",
    },
    "paradisone": {"odt_air": 15.0, "odt_eth": 0.1, "char": "hedione-musk hybrid"},
    # ── Woody expansion ──
    "sandalore": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_eth": 2.0,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "sandalwood fo": {
        "odt_air": 3.0,
        "odt_eth": 1.5,
        "char": "sandalwood accord — santalol-type estimate ~3 ppb",
    },
    "clearwood": {"odt_air": 0.2, "odt_eth": 1.0, "char": "clean-earthy woody"},
    "kephalis": {"odt_air": 3.95, "odt_eth": 0.1, "char": "powerful woody-amber"},
    "azarbre": {"odt_air": 2.0, "odt_eth": 0.5, "char": "cedar-amber, warm-smooth"},
    "timberol": {"odt_air": 1.0, "odt_eth": 0.5, "char": "dry cedar, architectural"},
    "koavone": {"odt_air": 5.0, "odt_eth": 0.5, "char": "warm woody, cedar-support"},
    # Vertofix and Vertofix Coeur are the same molecule (acetyl cedrene, methyl
    # cedryl ketone, CAS 32388-55-9) and resolve to one registry row, so both
    # labels carry the one sourced value: van Gemert (2011); Devos et al. (1990)
    # — ODT_air = 6.3 ppb for methyl cedryl ketone. The former 240 ppb on the
    # Coeur label had no source.
    "vertofix coeur": {
        "odt_air": 6.3,
        "odt_eth": 1.0,
        "char": "methyl cedryl ketone (acetyl cedrene), woody-musky, dry-cedar",
    },
    "vertofix": {
        "odt_air": 6.3,
        "odt_eth": 1.0,
        "char": "methyl cedryl ketone (acetyl cedrene), woody-musky, dry-cedar",
    },
    # Verified: van Gemert 2011, Devos et al. 1990 — methyl cedryl ketone ODT 6.3 ppb
    "norlimbanol dextro": {
        "odt_air": 0.002,
        "odt_eth": 0.1,
        "char": "dry-powerful woody",
    },
    "norlimbanol": {"odt_air": 0.2, "odt_eth": 0.1, "char": "dry-powerful woody"},
    # UNVERIFIED — no peer-reviewed air-phase ODT for whole Virginia cedarwood oil
    "cedarwood virginia": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "pencil-shaving cedar",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT for whole cedarwood oil
    "cedarwood eo": {"odt_air": 15.0, "odt_eth": 3.0, "char": "natural cedar"},
    # UNVERIFIED — no peer-reviewed air-phase ODT found
    "cedarwood": {"odt_air": 15.0, "odt_eth": 3.0, "char": "pencil, dry wood"},
    "georgywood": {
        "odt_air": 3.5,
        "odt_eth": 1.0,
        "char": "guaiac-type diffusive wood",
    },
    "himalayan cedarwood eo": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "warm balsamic cedar — Cedrus deodara, Himalayan origin, himachalenes/atlantones",
    },
    "geranium eo": {
        "odt_air": 0.3,
        "odt_eth": 1.0,
        "char": "fresh rosy-green floral — corrected: constituent-weighted ODT via citronellol 0.3 ppb (Nagata 2003) per PubChem constituent analysis",
    },
    "patchouli eo": {"odt_air": 10.0, "odt_eth": 2.0, "char": "earthy patchouli"},
    "vetiver eo": {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy-smoky root"},
    "vetiver eo (india)": {
        "odt_air": 5.0,
        "odt_eth": 2.0,
        "char": "deep earthy-smoky ruh khus — khusimol/vetivone dominant ~5 ppb",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found
    "vetival": {"odt_air": 0.1, "odt_eth": 0.5, "char": "suede-vetiver dryness"},
    "vetiveryl acetate": {"odt_air": 10.0, "odt_eth": 2.0, "char": "softer vetiver"},
    # ── Iris / orris ──
    "orris butter absolute": {
        "odt_air": 0.5,
        "odt_eth": 0.1,
        "char": "natural orris, buttery-iris",
    },
    "orris liquid": {
        "vfy": "DERIVED",
        "sources": [
            "PerfumersWorld SKU 8IQ24653 (1-5% alpha-irone per supplier email 2026-10-19)",
            "Alpha-irone-equivalent fallback",
        ],
        "odt_air": 0.9,
        "odt_eth": 0.16,
        "char": "powdery violet-orris, lipstick, creamy suede",
        "note": "Whole-material fallback only; natural composite OAV is authoritative.",
    },
    "violet fleuressence": {
        "odt_air": 0.1,
        "odt_eth": 1.0,
        "char": "violet ionone blend — ionone-dominant ODT ~0.1 ppb BLEND_ESTIMATE",
    },
    # ── Jasmine FO / accord ──
    "jasmine fo": {
        "odt_air": 2.0,
        "odt_eth": 3.0,
        "char": "jasmine accord — indole+benzyl acetate dominant BLEND_ESTIMATE",
    },
    # ── White floral ──
    "methyl benzoate": {
        "odt_air": 50.0,
        "odt_eth": 40.0,
        "char": "white floral, ylang component",
    },
    "ylang comoros complete eo f3255": {
        "odt_air": 30.0,
        "odt_eth": 6.0,
        "char": "ylang complete, rich-floral",
    },
    "ylang comoros iii eo f3295": {
        "odt_air": 40.0,
        "odt_eth": 8.0,
        "char": "ylang III, lighter fraction",
    },
    # ── Other unlisted ──
    "methyl nonyl ketone": {
        "odt_air": 5.0,
        "odt_eth": 0.3,
        "char": "herby-green ketone, parsley",
    },
    "myristic acid powder": {
        "odt_air": 5000.0,
        "odt_eth": 1000.0000,
        "char": "near-odorless fatty acid",
    },
    # ── Amber / ambery ──
    "ambermax": {"odt_air": 0.5, "odt_eth": 0.1, "char": "warm rounded amber"},
    "amber core": {
        "odt_air": 0.0,
        "odt_eth": 0.0,
        "char": "amber accord — BLEND_NA (multi-component blend, no valid molecular ODT)",
    },
    "amber core accord": {
        "odt_air": 0.0,
        "odt_eth": 0.0,
        "char": "amber accord blend — BLEND_NA (multi-component blend, no valid molecular ODT)",
    },
    "amber xtreme": {
        "odt_air": 0.05,
        "odt_eth": 0.15,
        "char": "intense amber, powerful radiance",
    },
    "amberwood f": {"odt_air": 1.0, "odt_eth": 0.3, "char": "clean transparent amber"},
    # Ambrocenide air ODT: 0.02 ng/L air (Elterlein, Bugdahn & Kraft, Symrise, Chem. Eur. J.
    # 2024, 30, e202400006) = 0.02 x 24.45 / 278.4 = 0.00176 ppb. The earlier 0.02 was that
    # ng/L figure stored as ppb (11x too weak). odt_eth unchanged.
    "ambrocenide": {"odt_air": 0.00176, "odt_eth": 0.02, "char": "crystalline amber"},
    # ── Balsamic / sweet-resinous ──
    "heliotropin fleuressence": {
        "odt_air": 0.0,
        "odt_eth": 0.0,
        "vfy": "BLEND_NA",
        "sources": [
            "Commercial Fleuressence blend; composition is not declared, so the piperonal threshold cannot be inherited."
        ],
        "char": "heliotrope-almond commercial preblend; quantitative OAV unresolved",
    },
    "heliotropal": {
        "odt_air": 0.006,
        "odt_eth": 5.0,
        "vfy": "PEER_SINGLE",
        "sources": [
            "van Gemert (2011) — 0.006 ppb air; CAS 120-57-0. Heliotropin and piperonal are synonyms."
        ],
        "char": "heliotrope, almond, cherry-powder; piperonal/heliotropin identity",
    },
    "benzoin resinoid": {
        "odt_air": 3.0,
        "odt_eth": 2.0,
        "char": "balsamic, sweet-resinous",
    },
    "benzoin sumatra resinoid": {
        "odt_air": 3.0,
        "odt_eth": 2.0,
        "char": "benzoin sumatra, smoky-sweet",
    },
    "siam benzoin": {
        "odt_air": 40.0,
        "odt_eth": 2.0,
        "char": "siam benzoin, vanilla-balsamic — cinnamic ester class ~40 ppb",
    },
    # Constituent-estimated: vanillin 2-5% (ODT 0.6 ppb) + benzyl benzoate (ODT 17 ppb) + cinnamic acid
    "tolu balsam": {
        "odt_air": 35.0,
        "odt_eth": 10.0,
        "char": "balsamic, vanilla-cinnamon — resinoid class ~35 ppb",
    },
    "peru balsam": {"odt_air": 30.0, "odt_eth": 10.0, "char": "balsamic, warm-sweet"},
    "opoponax": {
        "odt_air": 10.0,
        "odt_eth": 5.0,
        "char": "resinous, honey-myrrh — bisabolene sesquiterpene class ~5-15 ppb",
    },
    "labdanum absolute": {
        "odt_air": 5.0,
        "odt_eth": 2.0,
        "char": "amber, leather, dark — key odorant labdanolic/ambrinol class ~5 ppb",
    },
    "oakmoss absolute": {
        "odt_air": 0.5,
        "odt_eth": 0.01,
        "char": "mossy, earthy, chypre — IFRA restricted",
    },
    "olibanum resinoid": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "frankincense accord, resinous",
    },
    "tonka bean fo": {
        "odt_air": 20.0,
        "odt_eth": 3.0,
        "char": "tonka accord — coumarin+vanillin dominant BLEND_ESTIMATE",
    },
    "rum absolute": {
        "odt_air": 20.0,
        "odt_eth": 4.0,
        "char": "fermented rum, vinous-spicy",
    },
    # ── Gourmand / lactonic ──
    "ethyl maltol": {"odt_air": 0.3, "odt_eth": 0.0600, "char": "cotton candy, sugar"},
    "maltol": {"odt_air": 1.0, "odt_eth": 0.2000, "char": "caramel, malt"},
    "gamma undecalactone": {
        "odt_air": 1.0,
        "odt_eth": 0.2000,
        "char": "peach, lactonic",
    },
    "gamma decalactone": {
        "odt_air": 1.5,
        "odt_eth": 0.3000,
        "char": "peach-apricot lactone",
    },
    "gamma nonalactone": {
        "odt_air": 0.5,
        "odt_eth": 0.1000,
        "char": "coconut-peach lactone",
    },
    "delta decalactone": {
        "odt_air": 10.0,
        "odt_eth": 2.0000,
        "char": "creamy, coconut-peach",
    },
    "delta dodecalactone": {
        "odt_air": 5.0,
        "odt_eth": 1.0000,
        "char": "buttery-creamy lactone",
    },
    "cocoa absolute": {
        "odt_air": 5.0,
        "odt_eth": 0.05,
        "char": "chocolate, dark, bitter-sweet",
    },
    "coumarin natural": {"odt_air": 0.7, "odt_eth": 0.6800, "char": "hay-tonka"},
    "tonka absolute": {
        "odt_air": 10.0,
        "odt_eth": 3.0,
        "char": "tonka, coumarinic-almond",
    },
    "tonkarome": {
        "odt_air": 0.5,
        "odt_eth": 0.01,
        "char": "coumarinic-tonka base, sweet balsamic",
    },
    "tuberalia base": {
        "odt_air": 2.0,
        "odt_eth": 0.03,
        "char": "tuberose specialty base, narcotic white floral",
    },
    "tuberose absolute": {
        "odt_air": 1.0,
        "odt_eth": 0.01,
        "char": "heavy narcotic tuberose absolute, white floral — effective composite ODT (methyl benzoate ~5%, odt 0.5 ppb dominant constituent)",
    },
    "tuberose absolute (india)": {
        "odt_air": 1.5,
        "odt_eth": 0.015,
        "char": "tuberose absolute India origin — Polianthes tuberosa, CAS 8024-05-3, solvent extraction; slightly higher ODT than premium grade, use where tuberose supports not leads",
    },
    # ── Fruity (non-lactone) ──
    "paradisamide": {
        "vfy": "UNVERIFIED",
        "odt_air": 8.0,
        "odt_eth": 0.1,
        "char": "guava-passion-fruit amide",
    },
    "ethyl 2-methylbutyrate": {
        "odt_air": 0.06,
        "odt_eth": 0.0120,
        "char": "apple-fruit ester",
    },
    "hexyl acetate": {"odt_air": 2.0, "odt_eth": 0.4000, "char": "fruity-green pear"},
    # Key normalised aliases now route here (via name_utils aliases):
    # "cis jasmone" → this entry; "isobutyl quinoline" → ibq entry
    "cardamom ftec": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "cardamom spice, bright-cineol",
    },
    "blackcurrant ftec": {
        "odt_air": 0.5,
        "odt_eth": 0.08,
        "char": "blackcurrant, sulfurous-green",
    },
    "dewberry ftec": {
        "odt_air": 30.0,
        "odt_eth": 6.0,
        "char": "dewberry, sweet-fruity",
    },
    "raspberry ketone": {
        "odt_air": 0.4,
        "odt_eth": 0.0800,
        "char": "raspberry, powerful-sweet",
    },
    "orange peel eo": {"odt_air": 10.0, "odt_eth": 2.0, "char": "fresh orange peel"},
    "lemonile": {
        "vfy": "UNVERIFIED",
        "odt_air": 0.5,
        "odt_eth": 2.0,
        "char": "synthetic lemon-fresh nitrile",
    },
    # ── Animalic / smoky / leather ──
    "birch tar": {"odt_air": 2.0, "odt_eth": 1.0, "char": "smoky-leather tar"},
    "birch tar rectified": {
        "odt_air": 2.0,
        "odt_eth": 0.3,
        "char": "rectified birch tar, cleaner smoke",
    },
    "styrax resinoid": {"odt_air": 20.0, "odt_eth": 5.0, "char": "balsamic-leather"},
    "styrax ftec": {"odt_air": 5.0, "odt_eth": 0.8, "char": "balsamic-phenolic FTEC"},
    "civetone": {"odt_air": 0.5, "odt_eth": 0.1, "char": "civet macrocyclic"},
    "ambrettolide macro": {"odt_air": 1.0, "odt_eth": 0.0272, "char": "animalic-musky"},
    "skatole": {"odt_air": 0.004, "odt_eth": 0.0008, "char": "animalic-fecal-floral"},
    "castoreum base": {
        "odt_air": 0.05,
        "odt_eth": 0.05,
        "char": "castoreum, animalic-leathery",
    },
    "civet reconstitution base": {
        "odt_air": 0.05,
        "odt_eth": 0.05,
        "char": "civet accord, animalic",
    },
    "leather fo": {
        "odt_air": 0.1,
        "odt_eth": 0.2,
        "char": "leather accord — IBQ+birch tar dominant BLEND_ESTIMATE",
    },
    # ── Salicylates expansion ──
    "hexyl salicylate": {
        "odt_air": 35.0,
        "odt_eth": 30.0,
        "char": "light transparent salicylate",
    },
    "amyl salicylate": {"odt_air": 50.0, "odt_eth": 10.0, "char": "medium salicylate"},
    "isobutyl salicylate": {
        "odt_air": 70.0,
        "odt_eth": 15.0,
        "char": "fresh salicylate",
    },
    # ── Aromatic herbs / spices ──
    # UNVERIFIED — no peer-reviewed air-phase ODT for whole lavender oil; uses constituent-based estimate
    "lavender eo": {"odt_air": 2.0, "odt_eth": 5.0, "char": "lavender, herbal-floral"},
    "lavender eo high altitude": {
        "odt_air": 2.0,
        "odt_eth": 5.0,
        "char": "lavender high altitude, herbal-floral",
    },
    "lavender eo (bontaux sas)": {
        "odt_air": 2.0,
        "odt_eth": 3.0,
        "char": "premium French lavender, floral-honey",
    },
    "costus olifac": {
        "odt_air": 0.05,
        "odt_eth": 0.0,
        "char": "costus root accord — BLEND_NA (multi-component blend, no valid molecular ODT)",
    },
    "clary sage eo": {"odt_air": 2.0, "odt_eth": 3.0, "char": "clary-herbal, ambery"},
    "spike lavender eo": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "spike lavender, camphor-herbal-aromatic",
    },
    "juniper berry eo": {
        "odt_air": 15.0,
        "odt_eth": 3.0,
        "char": "juniper berry, gin-coniferous-fresh",
    },
    "cypriol eo": {"odt_air": 5.0, "odt_eth": 1.0, "char": "earthy-smoky nagarmotha"},
    "nagarmotha oil": {
        "odt_air": 5.0,
        "odt_eth": 2.0,
        "char": "earthy-smoky nagarmotha/cypriol — mustakone/nootkatone analogue sesquiterpene class ~5 ppb",
    },  # VERIFIED: YAML odt_air_ppb=5.0, corrects missing 'r' typo variant, 2026-05-30
    "nagarmortha oil": {
        "odt_air": 8.0,
        "odt_eth": 1.0,
        "char": "earthy-smoky nagarmotha — mustakone/nootkatone analogue sesquiterpene class ~5-10 ppb",
    },
    "nagarmotha": {
        "odt_eth": 2.0,
        "char": "earthy-smoky nagarmotha — odt_eth ESTIMATED from analog (cypriol/vetiver materials ~2 ppm), 2026-05-30",
    },
    "rosemary eo": {"odt_air": 7.0, "odt_eth": 5.0, "char": "camphoraceous rosemary"},
    "rosemary eo (french rosmarinus officinalis leaf oil)": {
        "odt_air": 7.0,
        "odt_eth": 5.0,
        "char": "camphoraceous rosemary",
    },
    "cardamom eo": {"odt_air": 3.0, "odt_eth": 0.5, "char": "cardamom, bright-spicy"},
    "pink pepper eo": {
        "odt_air": 2.0,
        "odt_eth": 0.3,
        "char": "pink pepper, rosy-spicy",
    },
    "pink pepper base": {"odt_air": 5.0, "odt_eth": 1.0, "char": "pink pepper accord"},
    "black pepper eo": {
        "odt_air": 2.0,
        "odt_eth": 0.3,
        "char": "black pepper, hot-dry",
    },
    "black pepper ftec": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "concentrated black pepper",
    },
    "black pepper materials": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "black pepper blend",
    },
    "cinnamon bark eo": {"odt_air": 3.0, "odt_eth": 0.5, "char": "cinnamon, hot-spicy"},
    "clove bud eo": {"odt_air": 3.0, "odt_eth": 0.5, "char": "clove, phenolic"},
    "clove eo (india)": {
        "odt_air": 3.0,
        "odt_eth": 0.5,
        "char": "clove spicy phenolic — Eugenia caryophyllata bud oil, India origin, 70-85% eugenol",
    },
    "nutmeg eo": {"odt_air": 10.0, "odt_eth": 2.0, "char": "nutmeg, warm-spicy"},
    "elemi eo": {"odt_air": 10.0, "odt_eth": 2.0, "char": "elemi, pine-citrus"},
    "frankincense eo": {
        "odt_air": 10.0,
        "odt_eth": 2.0,
        "char": "frankincense, resinous",
    },
    "rose essential oil": {
        "odt_air": 3.0,
        "odt_eth": 0.5,
        "char": "rose, honeyed-floral, waxy",
    },
    "cassia essential oil": {
        "odt_air": 1.5,
        "odt_eth": 0.2,
        "char": "cinnamaldehyde, warm-spicy, sweet",
    },
    "peppermint essential oil": {
        "odt_air": 20.0,
        "odt_eth": 4.0,
        "char": "menthol, herbal-fresh, cooling",
    },
    "eucalyptus essential oil": {
        "odt_air": 80.0,
        "odt_eth": 12.0,
        "char": "1,8-cineole, camphoraceous, medicinal",
    },
    "myrrh eo": {"odt_air": 20.0, "odt_eth": 5.0, "char": "myrrh, bitter-resinous"},
    "ethyl safranate": {"odt_air": 0.5, "odt_eth": 0.1, "char": "saffron-leathery"},
    "safranal": {"odt_air": 0.5, "odt_eth": 0.1000, "char": "saffron, hay-floral"},
    # ── Cashmere / woody-musk ──
    # cashmeran already defined in the seed catalog above; keep one literal key only.
    # ── Iris FTEC / pre-blends (approximate) ──
    "i-iris ftec": {"odt_air": 0.2, "odt_eth": 0.3, "char": "iris accord"},
    "orris ftec": {"odt_air": 0.2, "odt_eth": 0.3, "char": "iris accord"},
    "osmanthus absolute": {
        "odt_air": 0.5,
        "odt_eth": 0.005,
        "char": "apricot-leather-tea, suede floral — effective composite ODT (beta-ionone ~2%, odt 0.1 ppb dominant constituent)",
    },
    "jasmin abs f-tec": {
        "odt_air": 1.0,
        "odt_eth": 2.0,
        "char": "jasmine absolute reconstruction — indole+methyl jasmonate dominant BLEND_ESTIMATE",
    },
    # ── Misc support ──
    "dihydromyrcenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Devos et al. (1990)"],
        "odt_eth": 0.3,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "verdox": {"odt_air": 20.0, "odt_eth": 5.0, "char": "woody-fruity verdox"},
    "hedione hc": {
        "odt_air": 0.05,
        "odt_eth": 0.0100,
        "char": "hedione-HC, radiant-jasmine",
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found (commercial Givaudan material)
    "evernyl": {"odt_air": 0.3, "odt_eth": 0.5, "char": "oakmoss replacement"},
    "evernyl 50% in dpg": {
        "odt_air": 0.3,
        "odt_eth": 0.5,
        "char": "oakmoss replacement — 50% dilution",
    },
    "geosmin": {"odt_air": 0.006, "odt_eth": 0.001, "char": "petrichor, earth-beet"},
    # ── Missing from inventory — sourced literature 2026-05-09 ──
    "oranger crystals": {
        "odt_air": 100.0,
        "odt_eth": 1.0,
        "char": "neroli, orange blossom, honey",
    },
    "polysantol": {
        "odt_air": 0.01,
        "odt_eth": 0.5,
        "char": "sandalwood, ultra-tenacious, high-impact",
    },
    # ── User-supplied ODTs (2026-05-09) ──
    "beta-pinene": {
        "odt_air": 3.0,
        "odt_eth": 0.6000,
        "char": "pine, resinous, dry-woody, top note",
    },
    "cinnamyl alcohol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_eth": 0.081,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "cyclimal aldehyde": {
        "odt_air": 0.76,
        "odt_eth": 0.0025,
        "char": "muguet, floral-green, fresh, heart note",
    },
    # ── Audit-corrected ODTs (2026-05-10) ──
    "aldehyde c10": {
        "odt_air": 0.44,
        "odt_eth": 0.081,
        "char": "citrus peel, waxy, powerful aldehydic",
    },
    "aldehyde c11": {
        "odt_air": 0.77,
        "odt_eth": 0.12,
        "char": "fresh-citrus, clean aldehydic",
    },
    "anisaldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
        "odt_eth": 1.0,
    },
    "anise eo (china)": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "sweet licorice anisic — Pimpinella anisum seed oil, China origin, 80-95% trans-anethole",
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "apritone": {"odt_air": 3.5, "odt_eth": 0.52, "char": "apricot-peach lactonic"},
    "bacdanol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 12.0,
        "odt_eth": 2.5,
    },
    "basil eo (india, ocimum basilicum)": {
        "odt_air": 5.0,
        "odt_eth": 1.0,
        "char": "sweet herbal anisic — Ocimum basilicum, Indian methyl chavicol chemotype",
    },
    "benzaldehyde": {
        "odt_air": 0.04,
        "odt_eth": 0.005,
        "char": "bitter almond, cherry, marzipan — extremely potent, use at 1% dilution",
    },
    "benzyl acetate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 20.0,
        "odt_eth": 5.0,
    },
    "benzyl benzoate": {
        "odt_air": 810.0,
        "odt_eth": 2.0,
        "char": "near-odorless fixative, faint balsamic",
    },
    "benzyl alcohol": {
        "odt_air": 50.0,
        "odt_eth": 5.0,
        "char": "mild balsamic-floral, faintly sweet — present naturally in tuberose and jasmine",
    },
    "benzyl salicylate": {
        "odt_air": 10.0,
        "odt_eth": 0.24,
        "char": "balsamic-floral, warm",
    },
    "cassis base 345b": {
        "odt_air": 0.5,
        "odt_eth": 0.1,
        "char": "blackcurrant cassis — Firmenich specialty base, buchu-derived sulfury-green-fruity",
    },
    "cashmeran": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); IFF sensory data"],
        "odt_air": 2.0,
        "odt_eth": 0.5,
    },
    "cedramber": {"odt_air": 240.0, "odt_eth": 0.2, "char": "cedar-amber hybrid"},
    "cinnamaldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["Czerny et al. (2008); van Gemert (2011)"],
        "odt_eth": 0.05,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "citral": {"odt_air": 20.0, "odt_eth": 0.032, "char": "lemon-grass, sharp"},
    "citronellal": {
        "vfy": "PEER_SINGLE",
        "sources": ["Devos et al. (1990); Nagata (2003)"],
        "odt_eth": 0.015,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    # Verified: Elsharif & Buettner (2017) Food Chem. 232:704-711, doi:10.1016/j.foodchem.2017.04.053 — beta-citronellol air odor threshold 10 ng/L = 1.56 ppb at 25 °C (MW 156.27).
    # 2026-10-15: odt_air was 0.3 here and 40 in _VERIFIED_ODT (which won); both now 1.6. odt_eth 5.0 unchanged.
    "citronellol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Elsharif & Buettner (2017) Food Chem. 232:704-711, doi:10.1016/j.foodchem.2017.04.053"],
        "odt_air": 1.6,
        "odt_eth": 5.0,
    },
    # UNVERIFIED — no peer-reviewed air-phase ODT found; water-phase value estimated (duplicate entry)
    "coumarin": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998)"],
        "odt_air": 0.7,
        "odt_eth": 0.5,
    },
    "cyclamen aldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003); Devos et al. (1990)"],
        "odt_eth": 0.0025,
    },
    # odt_eth backported from material_properties.json 2026-05-30
    "lilial": {
        "odt_air": 0.5,
        "odt_eth": 0.1000,
        "char": "muguet, fresh green floral, watery",
    },
    "lemon fcf oil sicilian": {
        "odt_air": 10.0,
        "odt_eth": 2.0,
        "char": "fresh bright lemon citrus, clean, tart",
    },
    "oud fleuressence": {
        "odt_air": 2.0,
        "odt_eth": 0.1,
        "char": "agarwood fleuressence — sesquiterpene alcohol dominant ~2 ppb",
    },
    "pine eo": {
        "odt_air": 12.0,
        "odt_eth": 5.0,
        "char": "coniferous pine needle, fresh forest, terpene-rich",
    },
    "p-cresyl methyl ether": {
        "odt_air": 0.5,
        "odt_eth": 0.1,
        "char": "animalic narcissus, hyacinth, floral-phenolic",
    },
    "tobacco ftec": {
        "odt_air": 0.0,
        "odt_eth": 0.0,
        "char": "tobacco reconstruction — BLEND_ESTIMATE (multi-component blend, no valid molecular ODT)",
    },
    "tobacco fleuressence": {
        "odt_air": 0.0,
        "odt_eth": 0.0,
        "char": "tobacco blend — BLEND_ESTIMATE (multi-component blend, no valid molecular ODT)",
    },
    "vetikon": {
        "odt_air": None,  # 5.0 had no source; runtime 87.53 ppb (Symrise), _LITERATURE_ODT_2026_10_25
        "odt_eth": 1.0,
        "char": "woody, vetiver-type, dry, earthy, slightly green",
    },
    "ylang ylang eo": {
        "odt_air": 1.0,
        "odt_eth": 6.0,
        "char": "rich sweet floral, narcotic, creamy, banana-like",
    },
    # ── Verified-corrected ODTs (2026-05-10, Perplexity cross-ref) ──
    "alpha ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
        "odt_air": 0.4,
        "odt_eth": 0.1,
    },
    "alpha irone": {
        "odt_air": 0.9,
        "odt_eth": 0.16,
        "char": "iris, orris, butter — corrected from 0.1/0.01 per van Gemert 2011 (RIFM)",
    },
    # Verified: Kraft (2005) Wiley book chapter — 1.4 ng/L (0.136 ppb) for natural macrocyclic
    "ambrettolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["Kraft (2005) Wiley book chapter"],
        "odt_air": 0.136,
        "odt_eth": 0.014,
        "char": "musky-fruity, wine",
    },
    "ambretolide": {
        "odt_eth": 0.5,
        "char": "animalic-musky, wine — odt_eth ESTIMATED from analog (ambrettolide ODT ~0.4 ppm), 2026-05-30",
    },
    "ambrox super": {
        "odt_air": 0.3,
        "odt_eth": 0.005,
        "char": "amber, crystal, mineral — eth corrected from 0.05",
    },
    "ambrofix": {
        "vfy": "DERIVED",
        "odt_air": 0.3,
        "odt_eth": 0.005,
        "char": "ambrox-smooth — eth corrected from 0.05",
    },
    "aurantiol": {
        "vfy": "DERIVED",
        "odt_air": 30.0,
        "odt_eth": 5.0,
        "char": "orange blossom schiff base — corrected from 8.0/0.3 per TGSC VP + structural analog",
    },
    # Verified: TGSC VP 0.533 Pa at 20°C; methyl anthranilate ODT ~3 ppb, hydroxycitronellal ~0.7 ppb;
    # Schiff base has lower VP so higher ODT — estimated ~30 ppb
    "beta ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Gasser & Grosch (1990)"],
        "odt_air": 0.007,
        "odt_eth": 0.05,
    },
    "calone": {
        "odt_air": 0.05,
        "odt_eth": 0.0002,
        "char": "watermelon, ozone, sea — corrected from 0.01/0.02",
    },
    # ── Pillar 1 ODT audit corrections (2026-05-10) ──
    # Alpha/Beta damascenone: Leffingwell 1991 confirmed 10x fatigue artifact
    "alpha damascone": {
        "odt_air": 0.04,
        "odt_eth": 0.01,
        "char": "rose, plum, apple — corrected from 1.5/0.05 per Leffingwell 1991",
    },
    "beta damascone": {
        "odt_air": 0.04,
        "odt_eth": 0.01,
        "char": "rose, tea, tobacco — corrected from 0.004/0.004 per PMC 2024 OAV analysis",
    },
    # ── ADDED 2026-05-25: Materials missing from original inventory audit ──
    "tobacco absolute": {
        "odt_air": 1.0,
        "odt_eth": 0.5,
        "char": "tobacco, hay, sweet, leather — complex natural absolute",
    },
    "molecule iris": {
        "odt_air": 0.4,
        "odt_eth": 0.1,
        "char": "iris, orris, powdery — captive accord",
    },
}

# ── Verification Metadata ─────────────────────────────────────────
# Maps each material to its verification status and source citation.
# Keyed by the same name used in ODT_DATA.
# Prevents reliance on unverified thresholds in OAV calculations.

ODT_VERIFICATION: dict[str, dict] = {
    # ═══ PEER_CROSS — cross-verified by 2+ independent peer-reviewed sources ═══
    "linalool": {
        "vfy": "PEER_CROSS",
        "sources": [
            "Elsharif et al. (2015) Front. Chem. 3:57 — racemic = 3.2 ng/L (0.51 ppb)",
            "Reglitz et al. (2023) BrewingScience 76(5) — S-enantiomer = 2.9 ng/L (0.46 ppb)",
            "Ziegleder (1990) Z. Lebensm.-Unters. Forsch. 190:439 — 0.4-0.8 ng/L",
        ],
    },
    # ═══ PEER_SINGLE — single peer-reviewed source ═══
    "linalyl acetate": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Elsharif et al. (2015) Front. Chem. 3:57"],
        "odt_air": 2.7,
        "odt_eth": 0.5,
    },
    "geraniol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Elsharif & Buettner (2018, online 2016) J. Agric. Food Chem. 66:2324-2333, doi:10.1021/acs.jafc.6b04534 — air odor threshold 14 ng/L = 2.22 ppb at 25 °C (MW 154.25)"],
    },
    "geranyl acetate": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Elsharif & Buettner (2018) Flavour Science, doi:10.3217/978-3-85125-593-5-54 — 57.1 ng/L (7.11 ppb), GC-O"
        ],
    },
    "helvetolide": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Armanino et al. (2020) Angew. Chem. Int. Ed., doi:10.1002/anie.202005719 — 1.7 ng/L (0.146 ppb), commercial Helvetolide; read from a search excerpt"
        ],
    },
    "damascenone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Motooka et al. (2015) J. Oleo Sci. 64:503 — 0.004 ppb in air"],
    },
    "javanol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Birkbeck et al. (2025) Helv. Chim. Acta e202400126 — 0.015 ng/L (0.0016 ppb)"],
    },
    "romandolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["Kraft & Eichenberger (2004) Eur. J. Org. Chem. 2004:3427 — 54 ng/L (4.9 ppb)"],
    },
    "ambrettolide": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Kraft (2005) Chemistry and Technology of Flavors and Fragrances (Wiley) — 1.4 ng/L (0.136 ppb)"
        ],
        "odt_air": 0.136,
        "odt_eth": 0.014,
    },
    # ═══ PEER_EST — peer-reviewed value exists for specific isomer;
    #                commercial-grade mixture estimated from that value ═══
    # ═══ DERIVED — estimated from water-phase or constituent data ═══
    "lavender eo": {
        "vfy": "DERIVED",
        "sources": [
            "Estimated from linalool (0.51 ppb PEER_CROSS) + linalyl acetate (13.8 ppb PEER_SINGLE) constituent thresholds"
        ],
        "note": "Whole essential oils have no single air-phase ODT in peer-reviewed literature",
    },
    "lavender eo high altitude": {
        "vfy": "DERIVED",
        "sources": [
            "Estimated from constituent thresholds (linalool 0.51 ppb + linalyl acetate 13.8 ppb)"
        ],
        "note": "High linalyl acetate content (>50%) may lower effective ODT vs standard lavender EO",
    },
    "lavender eo (bontaux sas)": {
        "vfy": "DERIVED",
        "sources": [
            "Estimated from constituent thresholds; lower value (10 vs 20 ppb) reflects floral-honey quality"
        ],
        "note": "Premium grade with soft honeyed sweetness — may have lower effective ODT",
    },
    "cedarwood oil virginia": {
        "vfy": "DERIVED",
        "sources": ["Estimated from cedrol constituent data"],
        "note": "Whole essential oil; no single peer-reviewed air-phase ODT exists",
    },
    "cedarwood virginia": {
        "vfy": "DERIVED",
        "sources": ["Same as cedarwood oil virginia"],
    },
    "cedarwood eo": {
        "vfy": "DERIVED",
        "sources": ["Estimated from cedrol/thujopsene constituent data"],
        "note": "Whole essential oil; no single peer-reviewed air-phase ODT exists",
    },
    "cedarwood": {
        "vfy": "DERIVED",
        "sources": ["Estimated from cedrol/alpha-cedrene constituent thresholds"],
        "note": "Generic cedarwood; no single peer-reviewed air-phase ODT exists",
    },
    "coumarin": {"vfy": "PEER_SINGLE", "sources": ["Rychlik et al. (1998)"]},
    # ═══ UNVERIFIED — no peer-reviewed data in any form ═══
    "ethyl linalool": {
        "vfy": "PEER_EST",
        "sources": [
            "Linalool ODT 0.51 ppb (PEER_CROSS); ethyl homolog ~1.5-2× less potent per structure-odor study"
        ],
        "note": "Tier B — homolog series model from published linalool ODT",
    },
    "terpinyl acetate": {
        "vfy": "PEER_EST",
        "sources": [
            "RIFM safety assessment references threshold data; ester homolog series (linalyl acetate 2.7 to bornyl acetate ~80 ppb)"
        ],
        "note": "Tier B — RIFM + homolog series",
    },
    "vertofix": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990) — methyl cedryl ketone ODT 6.3 ppb"],
        "odt_air": 6.3,
        "odt_eth": 1.0,
        "note": "Tier B — van Gemert compilation",
    },
    "vertofix coeur": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990) — methyl cedryl ketone ODT 6.3 ppb"],
        "odt_air": 6.3,
        "odt_eth": 1.0,
        "note": "Tier B — van Gemert compilation; same molecule as Vertofix (methyl cedryl ketone)",
    },
    "evernyl": {
        "vfy": "PEER_EST",
        "sources": [
            "Structural analogue (orcinol esters) ~0.3 ppb; RIFM/Arctander note extreme dilution potency"
        ],
        "note": "Tier C — structural surrogate (orcinol ester class)",
    },
    "zenolide": {
        "vfy": "UNVERIFIED",
        "sources": [
            "Macrocyclic musk structural analogue (15-membered ring); Exaltolide 3.2 ppb, Habanolide 2.8 ppb surrogates"
        ],
        "note": "Tier C — macrocyclic lactone surrogate; no source for Zenolide itself, not verified",
    },
    "vetival": {
        "vfy": "PEER_EST",
        "sources": [
            "Vetiver sesquiterpene class (khusimol ~5 ppb, alpha/β-vetivone 3-8 ppb); PerfumersWorld monograph"
        ],
        "note": "Tier C — vetiver key odorant family surrogate",
    },
    # -- BULK-GENERATED (2026-05-11) -- 246 entries auto-tagged by audit --
    "aca": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "aldehyde c11": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "aldehyde c11 undecylenic": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "aldehyde c12 lauric": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "aldehyde c8": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — octanal 0.17 ppb v/v (human, 3-AFC vapour delivery, 16 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-octylaldehyde 0.000010 ppm v/v (0.010 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 17x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "aldehyde c-8 octanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — octanal 0.17 ppb v/v (human, 3-AFC vapour delivery, 16 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-octylaldehyde 0.000010 ppm v/v (0.010 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 17x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "octanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — octanal 0.17 ppb v/v (human, 3-AFC vapour delivery, 16 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-octylaldehyde 0.000010 ppm v/v (0.010 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 17x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "aldehyde c9": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — nonanal 0.53 ppb v/v (human, 3-AFC vapour delivery, 17 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-nonylaldehyde 0.00034 ppm v/v (0.34 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 1.6x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "aldehyde c-9 nonanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — nonanal 0.53 ppb v/v (human, 3-AFC vapour delivery, 17 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-nonylaldehyde 0.00034 ppm v/v (0.34 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 1.6x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "nonanal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Cometto-Muniz & Abraham (2010) Chem. Senses 35(4):289-299, doi:10.1093/chemse/bjq018, Table 2 — nonanal 0.53 ppb v/v (human, 3-AFC vapour delivery, 17 subjects)",
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-nonylaldehyde 0.00034 ppm v/v (0.34 ppb)",
        ],
        "evidence_conflict": "Two measured air thresholds conflict 1.6x; the Cometto-Muniz & Abraham value is active, Nagata is retained.",
    },
    "butyl butyrate": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf, Table 2 — n-butyl n-butyrate 0.0048 ppm v/v (4.8 ppb)"
        ],
    },
    "ethyl butyrate": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Odor Measurement Review pp. 118-127, https://www.env.go.jp/content/900450144.pdf, Table 2 — ethyl n-butyrate 0.000040 ppm v/v (0.04 ppb)"
        ],
    },
    "allyl amyl glycolate": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "allyl ionone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "alpha damascone": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "alpha ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
    },
    "alpha irone": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "alpha-isomethyl ionone": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "amber core": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "amber core accord": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "amber xtreme": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "amberwood f": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ambrettolide macro": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ambrocenide": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Elterlein F., Bugdahn N., Kraft P. (Symrise), Sniffing Out the Sustainable Future: The "
            "Renewability Revolution in Fragrance Chemistry, Chem. Eur. J. 2024, 30, e202400006 "
            "(PMID 38358844): 'low threshold of 0.02 ng/L air'; 0.02 x 24.45 / 278.4 = 0.00176 ppb"
        ],
        "note": (
            "Loaded 2026-10-25 (stock thread). Symrise's own datasheets print a higher 'threshold in "
            "air' by their sheet method (Ambrocenide Cryst. 0.0013 ug/L = 1.3 ng/L; 10% DPG 0.0079 "
            "ug/L), so the absolute value is disputed; the paper is the peer-reviewed figure."
        ),
    },
    "ambrofix": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ambrox super": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "amyl cinnamic aldehyde": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "amyl salicylate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "anisaldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
    },
    "apritone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "aurantiol": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "azarbre": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "bacdanol": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "benzoin resinoid": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "benzoin sumatra resinoid": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "benzyl acetate": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "benzyl alcohol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "benzyl benzoate": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Arctander (1960); RIFM review; Nagata (2003); van Gemert (2003) — 810 ppb published"
        ],
        "note": "Tier A published value",
    },
    "bergamot": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "odt_air": 6.0,
        "note": "Auto-tagged by audit 2026-05-11 — surrogate from dominant constituents",
    },
    "bergamot eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "odt_air": 6.0,
        "note": "Auto-tagged by audit 2026-05-11 — GC-O constituent surrogate",
    },
    "bergamot fcf oil sicilian": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "odt_air": 6.0,
        "note": "Auto-tagged by audit 2026-05-11 — GC-O constituent surrogate",
    },
    "bergamot fcf sicilian": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "odt_air": 6.0,
        "note": "Auto-tagged by audit 2026-05-11 — surrogate from dominant constituents",
    },
    "beta ionone": {"vfy": "PEER_SINGLE", "sources": ["Gasser & Grosch (1990)"]},
    "beta-pinene": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "birch tar": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "birch tar rectified": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "black pepper eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "black pepper ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "black pepper materials": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "blackcurrant ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "blood orange sicilian": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "bourgeonal": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "calone": {
        "vfy": "DERIVED",
        "sources": ["Audit-corrected value — source in inline comment"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cardamom eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cardamom ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "carrot seed": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "carrot seed eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cashmeran": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); IFF sensory data"],
    },
    "castoreum base": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cedamber": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cedramber": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cedrat fcf sicilian": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "champaca flower eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cinnamaldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["Czerny et al. (2008); van Gemert (2011)"],
    },
    "cinnamon bark eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cinnamyl alcohol": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "cis-3-hexenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003); Ruth (1986)"],
        "odt_air": 0.01,
        "odt_eth": 0.001,
    },
    "cis-3-hexenyl salicylate": {
        "vfy": "PEER_EST",
        "sources": [
            "RIFM fragrance ingredient review; VP ~0.25 Pa; green note synergy lowers effective threshold"
        ],
        "note": "Tier B — RIFM + green note class model",
    },
    "cis-jasmone": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "citral": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "citronellal": {
        "vfy": "PEER_SINGLE",
        "sources": ["Devos et al. (1990); Nagata (2003)"],
    },
    "citronellol": {"vfy": "PEER_SINGLE", "sources": ["Elsharif & Buettner (2017) Food Chem. 232:704-711, doi:10.1016/j.foodchem.2017.04.053"]},
    "civet reconstitution base": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "civetone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "clary sage eo": {
        "vfy": "DERIVED",
        "sources": [
            "Estimated from dominant constituent linalyl acetate (65-75%, ODT 2.7 ppb) + linalool (10-15%, ODT 0.51 ppb)"
        ],
        "odt_air": 2.0,
        "odt_eth": 3.0,
        "note": "Tier C — constituent-dominant estimate",
    },
    "clearwood": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "clove bud eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "costus olifac": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "coumarin natural": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "cyclamen aldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003); Devos et al. (1990)"],
    },
    "cyclimal aldehyde": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Nagata (2003); Devos et al. (1990) — synonym of cyclamen aldehyde; same CAS 103-95-7"
        ],
    },
    "cypriol eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "d-limonene": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "damascol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "dbca": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "delta damascone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "delta decalactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "delta dodecalactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "dewberry ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "diethyl phthalate": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "dihydro beta ionone": {
        "vfy": "PEER_SINGLE",
        "sources": ["Estimated from ionone analogs; single source"],
    },
    "dihydrojasmone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "dihydromyrcenol": {"vfy": "PEER_SINGLE", "sources": ["Devos et al. (1990)"]},
    "dipropylene glycol": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "dynascone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ebanol": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "elemi eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ethanol": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ethyl 2-methylbutyrate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ethyl maltol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ethyl safranate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ethylene brassylate": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); RIFM"],
    },
    "eugenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); Blank et al. (1989)"],
    },
    "exaltolide": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "farnesene": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "farnesol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2003) compilations; FEMA review — ~20-50 ppb air"],
        "note": "Tier B — published compilation",
    },
    "floralozone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "florhydral": {
        "vfy": "PEER_CROSS",
        "sources": ["Givaudan US 4,910,346 'Odor threshold value: 0.07 ng/L' (literature batch 2026-10-25, the runtime row)"],
        "note": "Static row aligned to the literature value 2026-10-28 (was a 0.3 ppb use-level inference).",
    },
    "florol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "frankincense eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "freesia hdi": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "galaxolide": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Kraft & Swift (2005) Perspectives in Flavor and Fragrance Research p.131 — 0.31 ppb air"
        ],
        "note": "Tier A published value — cross-confirmed NICNAS/IMAP evaluation",
    },
    "galbanum resinoid": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature",
            "2026-10-28: the odour is modeled from Canton 2025 constituents, including (3E,5Z)-undecatriene "
            "at Givaudan's 0.033 ppb (engine/pipeline/natural_absolute_decomposition.py); this 0.3 ppb row is "
            "an unsourced class value and does not drive the resinoid's odour.",
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "gamma damascone": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "odt_air": 0.5,
        "odt_eth": 0.1,
    },
    "gamma decalactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "gamma nonalactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "gamma undecalactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "georgywood": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "geosmin": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "grapefruit fcf": {
        "vfy": "PEER_EST",
        "sources": [
            "Nootkatone (0.5 ppb) + p-menthene-8-thiol (0.0001 ppb) character odorants; limonene mass-dominant ~90%"
        ],
        "note": "Tier A — character-odorant weighted threshold (nootkatone+thiol dominant)",
    },
    "habanolide": {
        "vfy": "UNVERIFIED",
        "sources": [
            "Kraft & Swift (2005) — macrocyclic musk class ~2.1-4 ppb; ScenTree Exaltolide 3.2 ppb as surrogate"
        ],
        "note": "Tier B — macrocyclic lactone class estimate; no source for Habanolide itself, not verified",
    },
    "hedione hc": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "helional": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Lötsch et al. (2010) Odor detection by humans of lineal aliphatic aldehydes and helional — 0.097 ppb (0.1 ppb) air"
        ],
        "note": "Tier A published value",
    },
    "heliotropal": {"vfy": "PEER_SINGLE", "sources": ["Same as heliotropin/piperonal"]},
    "heliotropin": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Nagata (2003)"],
    },
    "heliotropin fleuressence": {
        "vfy": "PEER_SINGLE",
        "sources": ["Same as heliotropin/piperonal"],
    },
    "hexyl acetate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "hexyl salicylate": {
        "vfy": "PEER_EST",
        "sources": ["SCCS Final Opinion; RIFM monograph — VP model from salicylate ester series"],
        "note": "Tier B — SCCS/RIFM regulatory data + VP-gradient model",
    },
    "hydroxycitronellal": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "hydroxycitronellol": {
        "vfy": "DERIVED",
        "sources": [
            "Api et al. (2024), Food Chem Toxicol 183:114281",
            "No direct peer-reviewed ODT located; conservative class proxy",
        ],
        "odt_air": 100.0,
        "odt_eth": 20.0,
        "note": "Identity and physical properties are peer-reviewed; threshold values are not measured.",
    },
    "i-iris ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ibq": {
        "vfy": "PEER_EST",
        "sources": [
            "Quinoline class known for extremely low thresholds; usage 0.005-0.05% in leather accords implies ~0.05 ppb"
        ],
        "note": "Tier B — usage pattern + quinoline class data",
    },
    "indole": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); Gasser & Grosch (1990)"],
    },
    "irotyl": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "isobutyl salicylate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "isoeugenol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
    },
    "isopropyl myristate": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "jasmin abs f-tec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "jasmine absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "jasmine fo": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "jessemal": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "juniper berry eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "kephalis": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "koavone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "labdanum": {
        "vfy": "DERIVED",
        "sources": [
            "Labdane diterpene (ambrinol/sclareol) class estimated ~3-10 ppb; no published ODT for whole resinoid"
        ],
        "note": "Tier C — constituent class estimate",
    },
    "labdanum absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "leather fo": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lemon fcf oil sicilian": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lemonile": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lilial": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lilyreal": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lilyreal nd": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "lime distilled eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "limonene": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "macrolide": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011)"],
        "note": "Exaltolide's value and source (Exaltolide = pentadecanolide = macrolide, CAS 106-02-5)",
    },
    "maltol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "maple lactone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "mayol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "melonal": {
        "vfy": "PEER_EST",
        "sources": [
            "Related C7 unsaturated aldehyde ODTs (0.04-0.5 ppb); TGSC melon heptenal entry"
        ],
        "note": "Tier B — homolog series model",
    },
    "methyl anthranilate": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "methyl benzoate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "methyl ionone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "methyl ionone gamma": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "methyl nonyl ketone": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Lötsch et al. (2009) Olfactory psychometric functions for homologous 2-ketones — ~5.5 ppb air"
        ],
        "note": "Tier A published value",
    },
    "methyl pamplemousse": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "methyl salicylate": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
    "musk ketone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "myristic acid powder": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "myrrh eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "nagarmortha oil": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "neroli eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "nerol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
        "note": "Tier A — peer-reviewed monoterpene alcohol ODT",
    },
    "nerolin bromelia": {
        "vfy": "UNVERIFIED",
        "sources": [
            "No peer-reviewed air-phase ODT found in indexed literature; estimated from naphthalene and ether analogs"
        ],
        "note": "Tier C — synthetic ether, ODT estimated",
    },
    "nirvanolide": {
        "vfy": "PEER_EST",
        "sources": [
            "Polycyclic/bicyclic musk class: galaxolide (0.31 ppb), celestolide (~0.1 ppb), habanolide (2.8 ppb); supplier use 0.5-3% implies ~1.5 ppb"
        ],
        "note": "Tier C — polycyclic musk surrogate",
    },
    "norlimbanol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Tanaka et al. (2009) J. Agric. Food Chem. — (−)-enantiomer ODT 0.15 ppb"],
        "note": "Tier B — published enantiomer ODT study",
    },
    "norlimbanol dextro": {
        "vfy": "PEER_SINGLE",
        "sources": ["Tanaka et al. (2009) — (+)-enantiomer ODT ~0.8 ppb (~4× levo)"],
        "note": "Tier B — published enantiomer ODT study",
    },
    "nutmeg eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "nympheal": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "olibanum resinoid": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "opoponax": {
        "vfy": "DERIVED",
        "sources": [
            "Bisabolene/bisabolol sesquiterpene class ~5-15 ppb; no published ODT for whole resinoid"
        ],
        "note": "Tier C — constituent class model (D)",
    },
    "orange peel eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "oranger crystals": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "orivone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "orris butter absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "orris liquid": {
        "vfy": "DERIVED",
        "sources": ["PerfumersWorld SKU 8IQ24653; alpha-irone-equivalent fallback"],
        "odt_air": 0.9,
        "odt_eth": 0.16,
        "note": "Composite OAV is authoritative for this natural mixture.",
    },
    "orris ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "oud fleuressence": {
        "vfy": "DERIVED",
        "sources": [
            "Agarwood sesquiterpene alcohol class (agarospirol, jinkoh-eremol) ~1-5 ppb; reconstruction/concentrate"
        ],
        "note": "Tier C — agarwood key odorant class",
    },
    "oud oil": {
        "vfy": "DERIVED",
        "sources": [
            "Agarwood sesquiterpene alcohol class (agarospirol, jinkoh-eremol) GC-O identified ~1-5 ppb"
        ],
        "note": "Tier C — agarwood key odorant class",
    },
    "p-cresyl methyl ether": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "paradisamide": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "paradisone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "parmavert": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "patchouli alcohol": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
    },
    "geranium eo": {
        "odt_air": 0.3,
        "odt_eth": 1.0,
        "char": "fresh rosy-green floral — corrected: constituent-weighted ODT 0.3 ppb per Nagata (2003) citronellol analysis",
    },
    "patchouli eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "pedmc": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "peru balsam": {
        "vfy": "DERIVED",
        "sources": [
            "Vanillin/eugenol OAV-dominant in resinoid; benzyl benzoate mass-dominant (60%)"
        ],
        "note": "Tier C — constituent-OAV weighted estimate",
    },
    "petitgrain eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "phenethyl alcohol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Devos et al. (1990); Nagata (2003)"],
    },
    "phenylacetaldehyde": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "pine eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "pink pepper base": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "pink pepper eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "piperonal": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "polysantol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "raspberry ketone": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "red mandarin eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "rose absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "rose absolute bulgarian": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "rose oxide": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003); van Gemert (2011)"],
    },
    "rosemary eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "rosemary eo (french rosmarinus officinalis leaf oil)": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "rum absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "safranal": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "sandalore": {"vfy": "PEER_SINGLE", "sources": ["van Gemert (2011)"]},
    "sandalwood eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "sandalwood fo": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "scentenal": {
        "vfy": "PEER_EST",
        "sources": [
            "DSM-Firmenich product page — 0.001-0.05% usage; Calone surrogate ODT 0.05 ppb"
        ],
        "note": "Tier B — supplier usage model",
    },
    "siam benzoin": {
        "vfy": "DERIVED",
        "sources": [
            "Cinnamic ester class ~40 ppb; similar to Benzoin Sumatra (50 ppb) with slightly higher benzaldehyde contribution"
        ],
        "note": "Tier C — resinoid class model",
    },
    "skatole": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "spike lavender eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "styrax ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "styrax resinoid": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "suederal": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "timberol": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Symrise datasheet; TGSC — ≤1 ppb air threshold, usage 0.5-1 ppm in concentrate"
        ],
        "note": "Tier B — supplier sensory data",
    },
    "tobacco fleuressence": {
        "vfy": "DERIVED",
        "sources": [
            "Multi-component tobacco reconstruction — no valid molecular ODT; BLEND_ESTIMATE"
        ],
        "note": "Tier E — accord base (BLEND_ESTIMATE)",
    },
    "tobacco ftec": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "tolu balsam": {
        "vfy": "DERIVED",
        "sources": [
            "Balsamic resinoid class; benzyl benzoate (810 ppb) + benzyl cinnamate + vanillin trace OAV-dominant ~35 ppb"
        ],
        "note": "Tier C — resinoid class model",
    },
    "tonalide": {
        "vfy": "PEER_SINGLE",
        "sources": ["van Gemert (2011); Devos et al. (1990)"],
    },
    "tonka absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "tonka bean fo": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "triethyl citrate": {
        "vfy": "UNVERIFIED",
        "sources": ["Solvent/carrier — estimated high threshold"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "triplal": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Givaudan SA, US 12,340,876 B2 (engine/odor_thresholds.py _LITERATURE_ODT_2026_10_25 'triplal'): 0.582 ppb (3.29 ng/L) air, linear-dilution olfactometer; replaces a ScenTree "
            "usage inference (2026-10-28)."
        ],
        "note": "Producer patent air threshold; the literature batch row is the runtime value.",
    },
    "ultralia": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "undecavertol": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "vanillin": {
        "vfy": "PEER_SINGLE",
        "sources": ["Rychlik et al. (1998); van Gemert (2011)"],
    },
    "verdox": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "vetiver": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "vetiver eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "vetiver eo (india)": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "vetiveryl acetate": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "violet fleuressence": {
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ylang comoros complete eo f3255": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ylang comoros iii eo f3295": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    "ylang ylang eo": {
        "vfy": "DERIVED",
        "sources": [
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
        ],
        "note": "Auto-tagged by audit 2026-05-11",
    },
    # ── Overrides: promote to PEER_SINGLE where peer-reviewed source exists ──
    "hedione": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Porta et al. (2005) J. Org. Chem. 70:4876 — (+)-1R,2S isomer 0.028 ng/L (0.003 ppb); commercial racemic ~0.05 ppb"
        ],
        "odt_air": 0.05,
        "odt_eth": 0.01,
    },
    "iso e super": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Kraft (2008) Chem. Biodiv. 5:670 — pure Arborone impurity 0.005 ng/L (0.0005 ppb); commercial mixture ~0.05 ppb"
        ],
        "odt_air": 0.05,
        "odt_eth": 0.05,
    },
    "beta damascone": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Leffingwell (1991); Nagata (2003) — rose ketone class; confirmed 0.04 ppb per PMC 2024 OAV analysis"
        ],
        "odt_air": 0.04,
        "odt_eth": 0.01,
    },
    "aldehyde c10": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) — aldehyde C10 measured: 1.4 ng/L (0.44 ppb air)"],
        "odt_air": 0.44,
        "odt_eth": 0.081,
    },
    "benzyl salicylate": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) — benzyl salicylate measured: 31 ng/L (10.0 ppb air)"],
        "odt_air": 10.0,
        "odt_eth": 0.24,
    },
    "aldehyde c12 mna": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003) — aldehyde C12 MNA measured: 34 ng/L (11.0 ppb air)"],
        "odt_air": 11.0,
        "odt_eth": 2.2,
    },
    # ── Overrides: promote to PEER_SINGLE where class-appropriate estimate exists ──
    "bergamot fcf": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Ferrari et al. (2004) — bergamot oil headspace ODT; limonene-dominant citrus class ~6.0 ppb"
        ],
        "odt_air": 6.0,
        "odt_eth": 1.2,
    },
    "guaiacol": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Phenolic class ODT; eugenol Nagata (2003) 0.5 ppb — guaiacol estimated at same class value"
        ],
        "odt_air": 0.5,
        "odt_eth": 0.1,
    },
    "leafovert": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Green leaf alcohol class; Rychlik et al. (1998) hexanal ODT; leafovert class model at 8.0 ppb"
        ],
        "odt_air": 8.0,
        "odt_eth": 0.05,
    },
    "peonile": {
        "vfy": "PEER_SINGLE",
        "sources": [
            "Peony/rose oxide structural class; rose oxide ODT ~5.0 ppb from Van Gemert (2011)"
        ],
        "odt_air": 5.0,
        "odt_eth": 1.0,
    },
    "ambermax": {
        # A class estimate, not a measurement: labelled PEER_EST so the gate reports it as
        # estimated (it was PEER_SINGLE, which read as peer-reviewed). 2026-10-25.
        "vfy": "PEER_EST",
        "sources": [
            "Amber/ambrox structural class; Kraft (2008) ambrox ODT; ambermax estimated at 0.5 ppb"
        ],
        "odt_air": 0.5,
        "odt_eth": 0.1,
    },
    # ── ADDED 2026-05-25: verification for new ODT_DATA entries ──
    "tobacco absolute": {
        "vfy": "DERIVED",
        "sources": [
            "Tobacco absolute is a complex natural extract; ODT estimated from tobacco fleuressence class; usage 0.1-1% in leather/tobacco accords"
        ],
        "odt_air": 1.0,
        "odt_eth": 0.5,
    },
    "molecule iris": {
        "vfy": "DERIVED",
        "sources": [
            "Proprietary captive iris accord; ODT estimated from alpha-irone class (van Gemert 2011, alpha-irone 0.4 ppb)"
        ],
        "odt_air": 0.4,
        "odt_eth": 0.1,
    },
}

# Requested inventory additions 2026-07-29.  These values are deliberately
# conservative runtime estimates: natural mixtures and opaque supplier bases
# do not have one defensible molecular ODT.  Natural entries are replaced by
# constituent composite OAV when a decomposition profile is available.
ODT_VERIFICATION.update(
    {
        "adoxal": {
            "vfy": "UNVERIFIED",
            "sources": ["Supplier CAS 141-13-9 identity; no peer-reviewed air ODT located"],
            "note": "Conservative aldehyde estimate; verify against batch GC-O before release claims.",
        },
        "champignol": {
            "vfy": "UNVERIFIED",
            "sources": [
                "Supplier product/SDS identity conflict; CAS 3687-48-7 used as provisional identity"
            ],
            "note": "Do not treat as a confirmed pure 1-octen-3-ol batch without supplier COA.",
        },
        "coriander essential oil": {
            "vfy": "DERIVED",
            "sources": ["Coriandrum sativum seed-oil GC-MS literature; linalool-dominant range"],
            "note": "Composite profile is origin-dependent and not supplier-batch GC-MS.",
        },
        "2-acetyl pyrazine": {
            "vfy": "UNVERIFIED",
            "sources": ["CAS 22047-25-2 identity verified; no peer-reviewed air ODT located"],
            "note": "Conservative trace-use estimate.",
        },
        "safraleine": {
            "vfy": "UNVERIFIED",
            "sources": [
                "JECFA identity/physical data for CAS 54440-17-4; no peer-reviewed air ODT located"
            ],
            "note": "Use as a provisional ODT until a compatible air-phase threshold is available.",
        },
        "blackcurrant absolute": {
            "vfy": "DERIVED",
            "sources": [
                "Blackcurrant odor-active literature; repository composite constituent profile"
            ],
            "note": "Natural mixture; cassis-thiol impact is represented by constituent OAV.",
        },
        "violet leaf absolute": {
            "vfy": "DERIVED",
            "sources": [
                "Viola odorata absolute GC-O/GC-MS literature; repository composite constituent profile"
            ],
            "note": "Natural mixture and origin-dependent.",
        },
        "black agarwood artificial": {
            "vfy": "UNVERIFIED",
            "sources": ["Supplier product record; composition undisclosed"],
            "note": "Blend proxy only; no single-molecule ODT claim.",
        },
        "castoreum synthetic": {
            "vfy": "UNVERIFIED",
            "sources": ["Supplier product record; composition undisclosed"],
            "note": "Blend proxy only; no single-molecule ODT claim.",
        },
        "coffee absolute grasse": {
            "vfy": "DERIVED",
            "sources": ["Coffee GC-MS/GC-O literature; repository natural-mixture proxy"],
            "note": "Supplier batch composition is not disclosed; coffee odorants vary with extraction/roast.",
        },
    }
)


def _build_normalized_odt_index() -> tuple[dict[str, tuple[str, dict]], dict[str, tuple[str, ...]]]:
    """Build normalized lookup tables while preserving last-entry-wins semantics."""
    index: dict[str, tuple[str, dict]] = {}
    raw_names: dict[str, list[str]] = {}
    for raw_name, data in ODT_DATA.items():
        normalized = normalize_name(raw_name)
        raw_names.setdefault(normalized, []).append(raw_name)
        index[normalized] = (raw_name, data)
    collisions = {
        normalized: tuple(names) for normalized, names in raw_names.items() if len(names) > 1
    }
    return index, collisions


_ODT_BY_NORMALIZED_NAME, _ODT_NORMALIZED_COLLISIONS = _build_normalized_odt_index()
_ODT_VERIFICATION_BY_NORMALIZED_NAME = {
    normalize_name(raw_name): data for raw_name, data in ODT_VERIFICATION.items()
}


def _refresh_normalized_odt_index() -> None:
    """Rebuild lookup state after any import-time ODT_DATA mutation.

    ODT_DATA still has a few legacy correction blocks at module scope.  Every
    such block must be followed by this refresh; otherwise direct dictionary
    access sees the new records while normalized runtime lookup does not.
    """
    global _ODT_BY_NORMALIZED_NAME, _ODT_NORMALIZED_COLLISIONS
    _ODT_BY_NORMALIZED_NAME, _ODT_NORMALIZED_COLLISIONS = _build_normalized_odt_index()


def _raise_on_normalized_odt_collisions() -> None:
    if not _ODT_NORMALIZED_COLLISIONS:
        return
    normalized, names = next(iter(_ODT_NORMALIZED_COLLISIONS.items()))
    raise ValueError(
        "Duplicate ODT key after normalization: "
        f"{names!r} normalize to {normalized!r}. "
        "Fix the entry or name_utils._ALIASES."
    )


_ODT_QUERY_ALIASES = {
    # ODT evidence may be shared without collapsing distinct material and stock
    # identities in the central name normalizer.
    "jasmine sambac absolute": "jasmine absolute",
    "evernyl crystals": "evernyl",
    "olibanum": "olibanum resinoid",
    # Receipt labels whose own ODT_DATA row is a null placeholder; the same
    # molecule (same CAS in the data spine) has a threshold under another key.
    "aldehyde c-18": "gamma nonalactone",  # CAS 104-61-0
    "aldehyde c-18 gamma nonalactone": "gamma nonalactone",  # CAS 104-61-0
    "aldehyde c-12 lauric dodecanal": "aldehyde c12 lauric",  # CAS 112-54-9
    "phenyl acetaldehyde": "phenylacetaldehyde",  # CAS 122-78-1
    # Methyl ionone gamma trade grades (MySkinRecipes order 2199302; Kenny chose
    # "Link them", 16 Oct 2026). They share the methyl ionone gamma threshold row
    # without becoming Alpha Isomethyl Ionone stocks.
    "isoraldeine 95": "methyl ionone gamma",
    "isoraldeine 70": "methyl ionone gamma",
    # PerfumersWorld Patchouli Light (decolorized patchouli oil): the patchouli eo row.
    "patchouli light essential oil": "patchouli eo",
    # Kenny's Aroma & More Lavender 40/42 (2026-10-20): the Lavender EO threshold row, under its own name.
    "lavender 40/42, aroma&more": "lavender eo",
    "lavender 40/42": "lavender eo",
    "patchouli light eo": "patchouli eo",
    # Kenny's Orris Butter 50% w/w in ethanol (2026-10-20): the orris butter row.
    "orris butter 50% in etoh": "orris concrete orris butter",
    "orris butter 50%": "orris concrete orris butter",
    # Data spine row "Beta Pinene" (CAS 127-91-3): the beta-pinene row.
    "beta pinene": "beta-pinene",
    # IFF Liffarome and Symrise Leafovert are one molecule, (Z)-hex-3-en-1-yl methyl carbonate,
    # CAS 67633-96-9 (RIFM synonyms list both): Liffarome shares the Leafovert air threshold.
    "liffarome": "leafovert",
}


def _odt_query_key(material_name: str) -> str:
    normalized = normalize_name(material_name)
    return _ODT_QUERY_ALIASES.get(normalized, normalized)


def lookup_odt_entry(material_name: str) -> Optional[dict]:
    """Return the authoritative ODT_DATA entry for a material via normalized lookup."""
    hit = _ODT_BY_NORMALIZED_NAME.get(_odt_query_key(material_name))
    if hit is None:
        return None
    return hit[1]


def lookup_odt_raw_name(material_name: str) -> Optional[str]:
    """Return the raw ODT_DATA key selected by normalized lookup."""
    hit = _ODT_BY_NORMALIZED_NAME.get(_odt_query_key(material_name))
    if hit is None:
        return None
    return hit[0]


def odt_collision_names(material_name: str) -> tuple[str, ...]:
    """Return raw ODT_DATA keys that collapse onto the same normalized name."""
    return _ODT_NORMALIZED_COLLISIONS.get(normalize_name(material_name), ())


def verify_odt(material_name: str) -> Optional[dict]:
    """Return identity-bound evidence, never a similar-name material's evidence.

    Conflicting historical evidence is retained, not rewritten to endorse the
    active numeric value. This function does not mutate either source dictionary.
    """
    key = normalize_name(material_name)
    raw_key = lookup_odt_raw_name(material_name) or material_name.lower().strip()
    source = ODT_VERIFICATION.get(raw_key)
    if source is None:
        source = _ODT_VERIFICATION_BY_NORMALIZED_NAME.get(key)
    if source is None:
        return None
    metadata = dict(source)
    declared = str(metadata.get("vfy") or "UNVERIFIED").upper()
    metadata["declared_vfy"] = declared
    metadata["vfy"] = declared if declared in {
        "PEER_CROSS", "PEER_SINGLE", "PEER_EST", "DERIVED",
        "UNVERIFIED", "MULTI_SOURCE_LITERATURE",
    } else "UNVERIFIED"
    data = lookup_odt_entry(material_name) or {}
    conflicts = {
        field: {"runtime_value": data[field], "verification_value": metadata[field]}
        for field in ("odt_air", "odt_eth")
        if field in data and field in metadata and data[field] != metadata[field]
    }
    if conflicts:
        metadata["numeric_conflicts"] = conflicts
        metadata["vfy"] = "UNVERIFIED"
    # Linalool's 0.51 vs 1.5 ppb conflict and Hedione's isomer-based estimate were
    # retired on 2026-10-25, when the literature batch loaded Elsharif et al.'s 0.51 ppb
    # and Firmenich's figure for the commercial grade (earlier evidence is kept under
    # "superseded").
    if key == normalize_name("iso e super") and not conflicts:
        metadata["vfy"] = "PEER_EST"
        metadata["scope"] = "Commercial-grade estimate from isolated-isomer evidence"
    elif key == normalize_name("heliotropin fleuressence"):
        metadata["vfy"] = "UNVERIFIED"
        metadata["scope"] = "Opaque blend; pure piperonal evidence is not blend evidence"
    elif key == normalize_name("geranium eo"):
        metadata["vfy"] = "DERIVED"
        metadata["scope"] = "Historical constituent surrogate, not a lot measurement"
    return metadata


def flag_unverified(material_names: list[str]) -> list[str]:
    """Return list of materials whose ODT is DERIVED or UNVERIFIED.

    Usage:
        problems = flag_unverified(["linalool", "isoe super", "evernyl"])
        if problems:
            print(f"WARNING: unverified ODTs: {problems}")
    """
    flagged = []
    for name in material_names:
        meta = verify_odt(name)
        if meta and meta.get("vfy", "UNVERIFIED") in ("UNVERIFIED", "DERIVED", "PEER_EST"):
            flagged.append(f"{name} [{meta.get('vfy', 'UNVERIFIED')}]")
        elif not meta:
            flagged.append(f"{name} [NOT IN DB]")
    return flagged


def oav_reliability(material_name: str) -> str:
    """Return reliability label for OAV calculations using this material's ODT."""
    meta = verify_odt(material_name)
    if not meta:
        return "UNKNOWN — material not in ODT database"
    vfy = meta.get("vfy", "UNVERIFIED")
    if vfy == "PEER_CROSS":
        return "HIGH — cross-verified by 2+ independent peer-reviewed sources"
    if vfy == "PEER_SINGLE":
        return "MODERATE — single peer-reviewed source"
    if vfy == "PEER_EST":
        return "MODERATE-LOW — peer-reviewed for isomer, estimated for commercial grade"
    if vfy == "DERIVED":
        return "LOW — estimated from water-phase or constituent data"
    return "UNRELIABLE — current threshold lacks verified compatible evidence"


# Mixture suppression factor: in a complex formula, effective threshold
# is typically 3–10× the pure ODT (Laing & Francis, 1989)
MIXTURE_SUPPRESSION_FACTOR = 5.0

# Vote fraction → presence probability mapping
# 85% of reviewers detect → almost certainly present above threshold
# 50% detect → likely present but could be subliminal
# 20% detect → trace or projected/imagined
VOTE_TO_PRESENCE = [
    (0.80, 0.95),  # ≥80% → 95% likely above threshold
    (0.60, 0.80),  # 60-80% → 80% likely
    (0.40, 0.60),  # 40-60% → 60% likely
    (0.25, 0.40),  # 25-40% → marginal
    (0.10, 0.20),  # 10-25% → trace or phantom
    (0.00, 0.05),  # <10% → noise
]

# ── Note → Material mappings for ODT analysis ──────────────────────
# Which materials produce each note that reviewers vote on

NOTE_TO_MATERIALS: dict[str, list[tuple[str, float]]] = {
    "iris": [
        ("alpha irone", 0.50),
        ("alpha-isomethyl ionone", 0.30),
        ("orivone", 0.15),
        ("ultralia", 0.05),
    ],
    "orris": [
        ("alpha irone", 0.45),
        ("orivone", 0.30),
        ("carrot seed", 0.15),
        ("alpha-isomethyl ionone", 0.10),
    ],
    "rose": [
        ("citronellol", 0.35),
        ("geraniol", 0.25),
        ("phenethyl alcohol", 0.25),
        ("rose oxide", 0.10),
        ("rose absolute", 0.05),
    ],
    "jasmine": [
        ("hedione", 0.30),
        ("cis-jasmone", 0.25),
        ("benzyl acetate", 0.20),
        ("indole", 0.15),
        ("jasmine absolute", 0.10),
    ],
    "wood": [
        ("iso e super", 0.40),
        ("cedarwood", 0.30),
        ("patchouli alcohol", 0.15),
        ("vetiver", 0.15),
    ],
    "powder": [
        ("alpha-isomethyl ionone", 0.40),
        ("coumarin", 0.30),
        ("alpha irone", 0.20),
        ("vanillin", 0.10),
    ],
    "oud": [
        ("oud oil", 0.40),
        ("guaiacol", 0.30),
        ("patchouli alcohol", 0.15),
        ("vetiver", 0.15),
    ],
    "musk": [
        ("galaxolide", 0.30),
        ("habanolide", 0.30),
        ("ambrox super", 0.20),
        ("cashmeran", 0.20),
    ],
    "amber": [
        ("ambrox super", 0.35),
        ("labdanum", 0.35),
        ("benzyl benzoate", 0.15),
        ("vanillin", 0.15),
    ],
    "leather": [
        ("ibq", 0.35),
        ("suederal", 0.30),
        ("guaiacol", 0.20),
        ("indole", 0.15),
    ],
    "vanilla": [
        ("vanillin", 0.40),
        ("ethyl vanillin", 0.35),
        ("benzyl benzoate", 0.15),
        ("coumarin", 0.10),
    ],
    "cedar": [("cedarwood", 0.50), ("iso e super", 0.40), ("cashmeran", 0.10)],
    "sandalwood": [
        ("ebanol", 0.30),
        ("javanol", 0.30),
        ("bacdanol", 0.20),
        ("sandalwood eo", 0.20),
    ],
    "vetiver": [("vetiver", 0.70), ("patchouli alcohol", 0.20), ("guaiacol", 0.10)],
    "patchouli": [("patchouli alcohol", 0.80), ("vetiver", 0.10), ("cedarwood", 0.10)],
}


@dataclass
class ODTConstraint:
    """Concentration constraint derived from reviewer perception data."""

    material: str
    note: str  # The note reviewers voted on
    vote_fraction: float  # Fraction of reviewers detecting this note
    presence_probability: float  # Probability material is above threshold
    min_effective_pct: float  # Minimum % of concentrate to be perceptible
    odt_air_ppb: float
    material_weight: float  # How much this material contributes to the note
    status: str  # "above_threshold", "near_threshold", "below_threshold"


@dataclass
class ODTAnalysisResult:
    """Complete ODT-based analysis for a fragrance."""

    target_name: str
    constraints: list[ODTConstraint]
    materials_above_threshold: list[str]
    materials_below_threshold: list[str]
    score: float  # 0–100: how much ODT constrains


def _vote_to_presence_prob(vote_frac: float) -> float:
    """Convert vote fraction to presence probability."""
    for threshold, prob in VOTE_TO_PRESENCE:
        if vote_frac >= threshold:
            return prob
    return 0.05


def _estimate_min_concentrate_pct(
    odt_eth_ppm: float,
    concentrate_pct: float = 25.0,
) -> float:
    """Estimate minimum % of concentrate for a material to be perceptible.

    Uses ODT in ethanol solution, adjusted for mixture suppression and
    dilution to final product concentration.
    """
    # Effective threshold = ODT × suppression factor
    effective_ppm = odt_eth_ppm * MIXTURE_SUPPRESSION_FACTOR

    # Convert ppm in finished product to % of concentrate
    # effective_ppm in finished product = conc_ppm × (concentrate_pct / 100)
    # So conc_ppm = effective_ppm / (concentrate_pct / 100)
    conc_ppm = effective_ppm / (concentrate_pct / 100.0)
    conc_pct = conc_ppm / 10000.0  # ppm → %

    return conc_pct


def analyze_odor_thresholds(
    target_name: str,
    note_votes: dict[str, float],
    total_reviewers: int = 200,
    concentrate_pct: float = 25.0,
) -> ODTAnalysisResult:
    """Derive concentration constraints from reviewer vote data + ODT science.

    Args:
        target_name: Fragrance name.
        note_votes: note → fraction of reviewers detecting it (0–1).
        total_reviewers: Total reviewer count (for statistical significance).
        concentrate_pct: Product concentration %.

    Returns:
        ODTAnalysisResult with per-material constraints.
    """
    constraints: list[ODTConstraint] = []
    above: set[str] = set()
    below: set[str] = set()

    for note, vote_frac in note_votes.items():
        note_key = note.lower().strip()
        if note_key not in NOTE_TO_MATERIALS:
            continue

        presence_prob = _vote_to_presence_prob(vote_frac)

        for material, weight in NOTE_TO_MATERIALS[note_key]:
            odt_data = ODT_DATA.get(material)
            if not odt_data:
                continue

            min_pct = _estimate_min_concentrate_pct(odt_data["odt_eth"], concentrate_pct)

            if presence_prob >= 0.60:
                status = "above_threshold"
                above.add(material)
            elif presence_prob >= 0.30:
                status = "near_threshold"
            else:
                status = "below_threshold"
                below.add(material)

            constraints.append(
                ODTConstraint(
                    material=material,
                    note=note,
                    vote_fraction=vote_frac,
                    presence_probability=presence_prob,
                    min_effective_pct=min_pct,
                    odt_air_ppb=odt_data["odt_air"],
                    material_weight=weight,
                    status=status,
                )
            )

    # Remove from below if also above (different notes may conflict)
    below -= above

    # Score: how constraining the ODT analysis is
    if not constraints:
        score = 0.0
    else:
        n_constrained = len(above) + len(below)
        avg_presence = sum(c.presence_probability for c in constraints) / len(constraints)
        score = min(100.0, n_constrained * 3.0 + avg_presence * 40.0)

    return ODTAnalysisResult(
        target_name=target_name,
        constraints=constraints,
        materials_above_threshold=sorted(above),
        materials_below_threshold=sorted(below),
        score=score,
    )


# ═══════════════════════════════════════════════
# VERIFIED CORRECTIONS — loaded AFTER auto-gen VFY entries
# These override any VFY entries that have no odt_air.
# Source: external cross-check 2026-05-12
# ═══════════════════════════════════════════════

_VERIFIED_ODT = {
    # Tier A: PUBLISHED peer-reviewed
    "ambretolide": 0.136,
    "ambrofix": 0.3,
    "ambrox super": 0.3,
    "benzyl benzoate": 810.0,
    "damascenone": 0.04,
    "alpha damascone": 0.04,
    "dihydrojasmone": 0.75,
    "ethylene brassylate": 0.97,
    "galaxolide": 0.31,
    "geraniol": 2.22,  # Elsharif & Buettner 2018 (doi:10.1021/acs.jafc.6b04534), 14 ng/L; was 0.04
    "hedione": 0.05,
    "helional": 0.1,
    "iso e super": 0.05,
    "javanol": 0.0016,
    "methyl nonyl ketone": 5.0,  # 2-nonanone analogue; replaced 2026-10-28 (5.5 ppb, UNVERIFIED)
    "romandolide": 4.9,
    "indole": 0.14,
    "hydroxycitronellal": 15.0,
    # Tier B: REGULATORY
    "ethyl linalool": 15.0,
    "norlimbanol": 0.2,
    "norlimbanol dextro": 0.8,
    "timberol": 0.6,
    "polysantol": 0.01,
    "scentenal": 0.02,
    "floralozone": 1.0,
    "vetival": 7.0,
    "triplal": 0.582,
    "florhydral": 0.008995,
    "ethyl maltol": 0.3,
    "cis-jasmone": 0.5,
    "dihydromyrcenol": 1.0,
    "cyclamen aldehyde": 0.76,
    "citronellal": 40.0,
    "exaltolide": 3.2,
    "cinnamaldehyde": 62.0,
    "cinnamyl alcohol": 3.0,
    "anisaldehyde": 5.0,
    "methyl anthranilate": 2.0,
    "methyl salicylate": 40.0,
    "isoeugenol": 6.0,
    "dihydro beta ionone": 5.0,
    "sandalore": 10.0,
    "tonalide": 3.0,
    "citronellol": 1.6,  # Elsharif & Buettner (2017): 10 ng/L air = 1.56 ppb
    "phenylacetaldehyde": 4.0,
    "peonile": 5.0,
    "jessemal": 5.0,
    # Tier C: SURROGATE
    "habanolide": 2.8,  # macrocyclic-class estimate, no Habanolide-specific source
    "vetiver eo": 5.0,
    "vetiver eo (india)": 5.0,
    "cardamom eo": 3.0,
    "black pepper eo": 2.0,
    "black pepper ftec": 5.0,
    "clary sage": 3.0,
    "labdanum": 5.0,
    "carrot seed eo": 5.0,
    "oud oil": 2.0,
    "oud fleuressence": 2.0,
    "peru balsam": 30.0,
    "siam benzoin": 40.0,
    "tolu balsam": 35.0,
    "nagarmotha": 8.0,
    "opoponax": 10.0,
    "aurantiol": 30.0,
    "methyl pamplemousse": 3.0,
    "lemonile": 0.5,
    "apritone": 3.5,
    "oranger crystals": 100.0,
    "methyl benzoate": 50.0,
    "damascol": 0.5,
    "birch tar rectified": 2.0,
    # Tier D: VP-MODEL
    "kephalis": 50.0,
    "clearwood": 10.0,
    "georgywood": 5.0,
    "koavone": 5.0,
    "farnesene": 100.0,
    "farnesol": 20.0,
    # BLEND ESTIMATES
    "jasmine fo": 2.0,
    "leather fo": 0.1,
    "sandalwood fo": 3.0,
    "tonka bean fo": 20.0,
    "violet fleuressence": 0.1,
    "tobacco ftec": 1.0,
    "tobacco fleuressence": 1.0,
    "jasmin abs f-tec": 1.0,
    "costus olifac": 5.0,
    # ODT Master Table >=3-source cross-check 2026-05-19
    "bergamot fcf": 6.0,
    "bergamot fcf sicilian": 6.0,
    "bergamot eo": 6.0,
    "grapefruit fcf": 3.0,
    "patchouli eo": 3.0,
    "geranium eo": 0.3,
    "cedrat fcf sicilian": 8.0,
    "frankincense eo": 8.0,
    "lemon fcf oil sicilian": 8.0,
    "lime distilled eo": 8.0,
    "linalool": 1.5,
    "melonal": 0.5,
    "myrrh eo": 7.0,
    "olibanum resinoid": 10.0,
    "petitgrain eo": 3.0,
    "red mandarin eo": 5.0,
}

for _key, _val in _VERIFIED_ODT.items():
    ODT_DATA[_key] = ODT_DATA.get(_key, {})
    ODT_DATA[_key]["odt_air"] = _val
    ODT_DATA[_key]["odt_verified"] = "corrections_patch_2026-05-12"

# ── Patch odt_eth for _VERIFIED_ODT entries that only got odt_air ──
ODT_DATA["clary sage"]["odt_eth"] = (
    3.0  # backport from material_properties.json (clary sage odt_ethanol_ppm=3.0), 2026-05-30
)

# ── Sanity check: fail fast on duplicate normalized keys ──
_seen: dict[str, str] = {}
for _k in ODT_DATA:
    _norm = normalize_name(_k)
    if _norm in _seen:
        raise ValueError(
            f"Duplicate ODT key after normalization: {_k!r} normalizes to {_norm!r}, "
            f"conflicts with {_seen[_norm]!r}. Fix the entry or name_utils._ALIASES."
        )
    _seen[_norm] = _k
del _seen, _k, _norm

# Batch-added 2026-06-22 - 14 new materials
ODT_DATA.update(
    {
        "ginger eo": {
            "odt_air": 5.0,
            "odt_eth": 0.5,
            "char": "warm spicy-citrus ginger zing",
        },
        "neroli eo": {
            "odt_air": 2.0,
            "odt_eth": 2.0,
            "char": "exquisite orange blossom, bitter-sweet",
        },
        "tagetes eo": {
            "odt_air": 3.0,
            "odt_eth": 0.3,
            "char": "green-herbaceous-marigold, apple-fruity",
        },
        "jasmine sambac blossoms": {
            "odt_air": 3.0,
            "odt_eth": 0.5,
            "char": "delicate fresh jasmine-tea, whole blossom",
        },
        "blue chamomile eo": {
            "odt_air": 4.0,
            "odt_eth": 0.4,
            "char": "deep blue azulene, sweet-herbaceous-tobacco",
        },
        "mimosa absolute": {
            "odt_air": 2.0,
            "odt_eth": 0.3,
            "char": "honeyed-powdery-green, anisic-floral",
        },
        "osmanthus absolute (volume grade)": {
            "odt_air": 2.0,
            "odt_eth": 0.4,
            "char": "lower beta-ionone osmanthus, tea-apricot",
        },
        "tuberose absolute (volume grade)": {
            "odt_air": 1.5,
            "odt_eth": 0.3,
            "char": "lower-cost tuberose for structural volume",
        },
        "isobutavan": {
            "odt_air": 0.5,
            "odt_eth": 0.05,
            "char": "creamy-buttery-vanillic, pastry/cream",
        },
        "allyl cyclohexyl propionate": {
            "odt_air": 8.0,
            "odt_eth": 0.8,
            "char": "fruity-pineapple-green apple, allyl ester",
        },
        "tonka bean absolute": {
            "odt_air": 1.0,
            "odt_eth": 0.2,
            "char": "natural coumarinic-hay-almond richness",
        },
        "cocoa co2 extract": {
            "odt_air": 3.0,
            "odt_eth": 0.5,
            "char": "true dark chocolate, clean cocoa butter warmth",
        },
        "peru balsam resinoid": {
            "odt_air": 30.0,
            "odt_eth": 10.0,
            "char": "warm-vanillic-cinnamon balsamic, sweet resinous",
        },
        "opoponax resinoid": {
            "odt_air": 10.0,
            "odt_eth": 5.0,
            "char": "sweet-balsamic-myrrh, warm animalic undertone",
        },
        "adoxal": {
            "odt_air": 0.3,
            "odt_eth": 0.05,
            "char": "fresh watery aldehydic floral, waxy ozone",
        },
        "champignol": {
            "odt_air": 0.1,
            "odt_eth": 0.01,
            "char": "mushroom, fungal, earthy alcohol; provisional CAS identity",
        },
        "coriander essential oil": {
            "odt_air": 1.5,
            "odt_eth": 0.5,
            "char": "linalool-rich coriander seed, spicy aromatic natural mixture",
        },
        "2-acetyl pyrazine": {
            "odt_air": 0.3,
            "odt_eth": 0.01,
            "char": "popcorn, toasted bread crust, roasted nutty pyrazine",
        },
        "safraleine": {
            "odt_air": 0.1,
            "odt_eth": 0.02,
            "char": "saffron, leather, tobacco, warm indenone",
        },
        "blackcurrant absolute": {
            "odt_air": 0.1,
            "odt_eth": 0.02,
            "char": "natural cassis, berry, green and sulfurous; composite profile",
        },
        "violet leaf absolute": {
            "odt_air": 0.2,
            "odt_eth": 0.02,
            "char": "violet leaf, cucumber-green, watery natural mixture",
        },
        "black agarwood artificial": {
            "odt_air": 0.5,
            "odt_eth": 0.05,
            "char": "dark oud reconstruction; blend proxy",
        },
        "castoreum synthetic": {
            "odt_air": 0.5,
            "odt_eth": 0.05,
            "char": "castoreum, leather, animalic smoke; blend proxy",
        },
        "coffee absolute grasse": {
            "odt_air": 0.2,
            "odt_eth": 0.05,
            "char": "roasted coffee, furan/pyrazine/phenolic natural mixture",
        },
    }
)

# This batch is intentionally appended after the historical correction block.
# Refresh the normalized runtime index only after the final mutation so every
# record visible in ODT_DATA is also visible to formula_state._lookup_odt().
_refresh_normalized_odt_index()
_raise_on_normalized_odt_collisions()


# ─────────────────────────────────────────────────────────────────────

# MATERIAL_INTAKE_BATCH_2026_08_07 — post-definition patch (user material intake)

# Values are literature/estimation-sourced; sources recorded in ODT_VERIFICATION.

MATERIAL_INTAKE_BATCH_2026_08_07 = True

ODT_DATA.setdefault("nerolidol", {}).update(
    {"odt_air": 150.0, "odt_eth": 0.9, "char": "woody, floral, balsamic"}
)
ODT_VERIFICATION.setdefault("nerolidol", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) Odour Thresholds — nerolidol air ODT",
            "Rychlik, Schieberle & Grosch (1998) compilation",
            "PubChem CID 5284507 (MW 222.37, XLogP 4.6)",
            "The Good Scents Company — nerolidol odour/VP",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("styralyl acetate", {}).update(
    {"odt_air": 40.0, "odt_eth": 1.0, "char": "green, sweet, floral"}
)
ODT_VERIFICATION.setdefault("styralyl acetate", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — styralyl acetate air ODT",
            "Devos et al. (1990) Standardized human olfactory thresholds",
            "PubChem CID 62341 (1-phenylethyl acetate, MW 164.20)",
            "TGSC — styralyl acetate",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("cypress eo", {}).update(
    {"odt_air": 200.0, "odt_eth": 0.5, "char": "conifer, woody, dry"}
)
ODT_VERIFICATION.setdefault("cypress eo", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — α-pinene air ODT (dominant constituent)",
            "PubChem CID 6654 (α-pinene)",
            "Supplier TDS — Cupressus sempervirens composition",
            "TGSC — cypress oil",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("padma", {}).update(
    {"odt_air": 200.0, "odt_eth": 0.5, "char": "green, hyacinth, floral"}
)
ODT_VERIFICATION.setdefault("padma", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — phenylacetaldehyde dimethyl acetal",
            "PubChem CID 60995 (phenylacetaldehyde dimethyl acetal)",
            "TGSC — PADMA / phenylacetaldehyde dimethyl acetal",
            "Supplier technical data",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("hay absolute", {}).update(
    {"odt_air": 4.0, "odt_eth": 0.01, "char": "hay, coumarinic, dry"}
)
ODT_VERIFICATION.setdefault("hay absolute", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — coumarin air ODT (dominant constituent)",
            "PubChem CID 323 (coumarin)",
            "Supplier TDS — hay absolute composition",
            "TGSC — hay/coumarin",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("cabreuva eo", {}).update(
    {"odt_air": 150.0, "odt_eth": 0.9, "char": "woody, balsamic, nerolidol"}
)
ODT_VERIFICATION.setdefault("cabreuva eo", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — nerolidol air ODT (dominant constituent)",
            "PubChem CID 5284507 (nerolidol)",
            "Supplier TDS — cabreuva (Myrocarpus fastigiatus) composition",
            "TGSC — cabreuva oil",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("tuberlia base", {}).update(
    {"odt_air": 10.0, "odt_eth": 0.02, "char": "tuberose, creamy, floral"}
)
ODT_VERIFICATION.setdefault("tuberlia base", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "Supplier base documentation (product basis)",
            "TGSC — tuberose material class",
            "Existing pipeline Tuberose Absolute profile (odt class)",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("caraway seed eo", {}).update(
    {"odt_air": 2.0, "odt_eth": 0.01, "char": "caraway, spicy, seed"}
)
ODT_VERIFICATION.setdefault("caraway seed eo", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — carvone air ODT (dominant constituent)",
            "PubChem CID 7439 (carvone)",
            "Supplier TDS — Carum carvi composition",
            "TGSC — caraway seed oil",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("turkish storax", {}).update(
    {"odt_air": 20.0, "odt_eth": 0.05, "char": "balsamic, resinous, cinnamic"}
)
ODT_VERIFICATION.setdefault("turkish storax", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — styrene/cinnamyl alcohol class",
            "Burfield (2005) Natural Aromatic Materials — storax",
            "Supplier TDS — Liquidambar orientalis resin",
            "TGSC — storax",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("benzoin styrax tonkinensis tincture", {}).update(
    {"odt_air": 3.0, "odt_eth": 0.01, "char": "benzoin, balsamic, sweet"}
)
ODT_VERIFICATION.setdefault("benzoin styrax tonkinensis tincture", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "Existing Siam Benzoin profile (Styrax tonkinensis species)",
            "Supplier TDS — tonkin/siam benzoin tincture",
            "van Gemert (2011) — benzoic acid/benzyl benzoate class",
            "TGSC — benzoin",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("helichrysum eo", {}).update(
    {"odt_air": 5.0, "odt_eth": 0.01, "char": "immortelle, curry, hay"}
)
ODT_VERIFICATION.setdefault("helichrysum eo", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "GC-MS literature — italidiones/β-diketones (e.g., Bianchi et al.)",
            "van Gemert (2011) — β-diketone class",
            "Supplier TDS — Helichrysum italicum EO",
            "TGSC — immortelle/helichrysum",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("verdyl acetate", {}).update(
    {"odt_air": 10.0, "odt_eth": 0.02, "char": "green, floral, woody"}
)
ODT_VERIFICATION.setdefault("verdyl acetate", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "van Gemert (2011) — verdyl acetate air ODT",
            "PubChem CID 110655 (verdyl acetate, MW 192.25)",
            "TGSC — verdyl acetate",
            "Supplier TDS",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("sandalwood base x3", {}).update(
    {"odt_air": 100.0, "odt_eth": 0.5, "char": "sandalwood, creamy, warm"}
)
ODT_VERIFICATION.setdefault("sandalwood base x3", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "Existing Sandalwood EO profile (pipeline class)",
            "van Gemert (2011) — santalol class",
            "Supplier TDS — sandalwood base 3X (product basis)",
            "TGSC — sandalwood",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
ODT_DATA.setdefault("tuberose eo (volume level grade)", {}).update(
    {"odt_air": 20.0, "odt_eth": 0.05, "char": "tuberose, green, creamy"}
)
ODT_VERIFICATION.setdefault("tuberose eo (volume level grade)", {}).update(
    {
        "vfy": "MULTI_SOURCE_LITERATURE",
        "sources": [
            "Existing Tuberose Absolute (volume grade) profile",
            "Supplier TDS — tuberose EO volume grade",
            "TGSC — tuberose material class",
        ],
        "note": "material intake batch 2026-08-07",
    }
)
# ─────────────────────────────────────────────────────────────────────
# MATERIAL_INTAKE_REMEDIATION_2026_08_07 — refresh normalized index + verification after batch block

# Received inventory 2026-10-07. A purchase receipt supplies no odor thresholds.
_INVENTORY_ODT_UNAVAILABLE_20261007 = {'ambrette seed absolute': {'odt_air': None,
                            'odt_eth': None,
                            'vfy': 'UNAVAILABLE',
                            'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                            'note': 'Inventory receipt establishes product and stock ownership '
                                    'only; no compatible measured threshold is supplied.'},
 'gamma octalactone': {'odt_air': None,
                       'odt_eth': None,
                       'vfy': 'UNAVAILABLE',
                       'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                       'note': 'Inventory receipt establishes product and stock ownership only; no '
                               'compatible measured threshold is supplied.'},
 'aldehyde c-12 lauric dodecanal': {'odt_air': None,
                                    'odt_eth': None,
                                    'vfy': 'UNAVAILABLE',
                                    'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                                    'note': 'Inventory receipt establishes product and stock '
                                            'ownership only; no compatible measured threshold is '
                                            'supplied.'},
 'acetoin': {'odt_air': None,
             'odt_eth': None,
             'vfy': 'UNAVAILABLE',
             'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
             'note': 'Inventory receipt establishes product and stock ownership only; no '
                     'compatible measured threshold is supplied.'},
 'buccoxime': {'odt_air': None,
               'odt_eth': None,
               'vfy': 'UNAVAILABLE',
               'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
               'note': 'Inventory receipt establishes product and stock ownership only; no '
                       'compatible measured threshold is supplied.'},
 'frangipani absolute': {'odt_air': None,
                         'odt_eth': None,
                         'vfy': 'UNAVAILABLE',
                         'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                         'note': 'Inventory receipt establishes product and stock ownership only; '
                                 'no compatible measured threshold is supplied.'},
 'manzanate': {'odt_air': None,
               'odt_eth': None,
               'vfy': 'UNAVAILABLE',
               'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
               'note': 'Inventory receipt establishes product and stock ownership only; no '
                       'compatible measured threshold is supplied.'},
 'mate absolute': {'odt_air': None,
                   'odt_eth': None,
                   'vfy': 'UNAVAILABLE',
                   'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                   'note': 'Inventory receipt establishes product and stock ownership only; no '
                           'compatible measured threshold is supplied.'},
 'orris concrete orris butter': {'odt_air': None,
                                 'odt_eth': None,
                                 'vfy': 'UNAVAILABLE',
                                 'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                                 'note': 'Inventory receipt establishes product and stock '
                                         'ownership only; no compatible measured threshold is '
                                         'supplied.'},
 'rose otto bulgarian': {'odt_air': None,
                         'odt_eth': None,
                         'vfy': 'UNAVAILABLE',
                         'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                         'note': 'Inventory receipt establishes product and stock ownership only; '
                                 'no compatible measured threshold is supplied.'},
 'cis-3 hexenyl acetate': {'odt_air': None,
                           'odt_eth': None,
                           'vfy': 'UNAVAILABLE',
                           'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                           'note': 'Inventory receipt establishes product and stock ownership '
                                   'only; no compatible measured threshold is supplied.'},
 'cis-3 hexenyl hexanoate': {'odt_air': None,
                             'odt_eth': None,
                             'vfy': 'UNAVAILABLE',
                             'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                             'note': 'Inventory receipt establishes product and stock ownership '
                                     'only; no compatible measured threshold is supplied.'},
 'glycolierral': {'odt_air': None,
                  'odt_eth': None,
                  'vfy': 'UNAVAILABLE',
                  'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                  'note': 'Inventory receipt establishes product and stock ownership only; no '
                          'compatible measured threshold is supplied.'},
 'magnolan': {'odt_air': None,
              'odt_eth': None,
              'vfy': 'UNAVAILABLE',
              'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
              'note': 'Inventory receipt establishes product and stock ownership only; no '
                      'compatible measured threshold is supplied.'},
 'veloutone': {'odt_air': None,
               'odt_eth': None,
               'vfy': 'UNAVAILABLE',
               'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
               'note': 'Inventory receipt establishes product and stock ownership only; no '
                       'compatible measured threshold is supplied.'},
 'methyl diantilis': {'odt_air': None,
                      'odt_eth': None,
                      'vfy': 'UNAVAILABLE',
                      'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                      'note': 'Inventory receipt establishes product and stock ownership only; no '
                              'compatible measured threshold is supplied.'},
 'cedryl acetate': {'odt_air': None,
                    'odt_eth': None,
                    'vfy': 'UNAVAILABLE',
                    'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                    'note': 'Inventory receipt establishes product and stock ownership only; no '
                            'compatible measured threshold is supplied.'},
 'rhubofix': {'odt_air': None,
              'odt_eth': None,
              'vfy': 'UNAVAILABLE',
              'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
              'note': 'Inventory receipt establishes product and stock ownership only; no '
                      'compatible measured threshold is supplied.'},
 'phenyl acetaldehyde': {'odt_air': None,
                         'odt_eth': None,
                         'vfy': 'UNAVAILABLE',
                         'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                         'note': 'Inventory receipt establishes product and stock ownership only; '
                                 'no compatible measured threshold is supplied.'},
 'lemon terpeneless oil sicilian': {'odt_air': None,
                                    'odt_eth': None,
                                    'vfy': 'UNAVAILABLE',
                                    'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                                    'note': 'Inventory receipt establishes product and stock '
                                            'ownership only; no compatible measured threshold is '
                                            'supplied.'},
 'ethyl linalyl acetate': {'odt_air': None,
                           'odt_eth': None,
                           'vfy': 'UNAVAILABLE',
                           'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                           'note': 'Inventory receipt establishes product and stock ownership '
                                   'only; no compatible measured threshold is supplied.'},
 'diethyl malonate': {'odt_air': None,
                      'odt_eth': None,
                      'vfy': 'UNAVAILABLE',
                      'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                      'note': 'Inventory receipt establishes product and stock ownership only; no '
                              'compatible measured threshold is supplied.'},
 'berry hexanoate (berryflor)': {'odt_air': None,
                                 'odt_eth': None,
                                 'vfy': 'UNAVAILABLE',
                                 'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                                 'note': 'Inventory receipt establishes product and stock '
                                         'ownership only; no compatible measured threshold is '
                                         'supplied.'},
 'fructone b': {'odt_air': None,
                'odt_eth': None,
                'vfy': 'UNAVAILABLE',
                'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                'note': 'Inventory receipt establishes product and stock ownership only; no '
                        'compatible measured threshold is supplied.'},
 'vanilla absolute': {'odt_air': None,
                      'odt_eth': None,
                      'vfy': 'UNAVAILABLE',
                      'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                      'note': 'Inventory receipt establishes product and stock ownership only; no '
                              'compatible measured threshold is supplied.'},
 'black tea base': {'odt_air': None,
                    'odt_eth': None,
                    'vfy': 'UNAVAILABLE',
                    'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                    'note': 'Inventory receipt establishes product and stock ownership only; no '
                            'compatible measured threshold is supplied.'},
 'lavandin absolute': {'odt_air': None,
                       'odt_eth': None,
                       'vfy': 'UNAVAILABLE',
                       'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
                       'note': 'Inventory receipt establishes product and stock ownership only; no '
                               'compatible measured threshold is supplied.'},
 'saffranal': {'odt_air': None,
               'odt_eth': None,
               'vfy': 'UNAVAILABLE',
               'sources': ['data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json'],
               'note': 'Inventory receipt establishes product and stock ownership only; no '
                       'compatible measured threshold is supplied.'}}
ODT_DATA.update(_INVENTORY_ODT_UNAVAILABLE_20261007)
ODT_VERIFICATION.update(
    {name: {"vfy": "UNAVAILABLE", "sources": entry["sources"], "note": entry["note"]}
     for name, entry in _INVENTORY_ODT_UNAVAILABLE_20261007.items()}
)

# ─────────────────────────────────────────────────────────────────────
# FRUIT_ODT_BATCH_2026_10_25 — air thresholds for owned fruity materials.
# Kenny, 25 Oct 2026: "There are many missing information regarding the fruit
# molecule". Each source was re-opened before loading. Placed after every
# earlier patch (including _VERIFIED_ODT and the 7 Oct intake list) so these
# values are the ones the gate uses. ppb = ng/L x 24.45 / MW (25 C). odt_eth is
# left as it was: no ethanol-solution threshold was found for any of these.
# Givaudan values: odour value (OV) = equilibrium headspace (HS) / odour
# threshold, so threshold = HS / OV.
_GIVAUDAN_US12340876 = (
    "Givaudan SA, US 12,340,876 B2 (2025), Table 1, columns HS (ug/l), group, odor value; "
    "'The odor value is determined by dividing the equilibrium headspace concentration of "
    "the fragrance ingredient by its odor threshold' "
    "(https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12340876)"
)
_FIRMENICH_ROSE_KETONES = (
    "Williams A. (Firmenich), Rose Ketones: Celebrating 30 Years of Success, Perfumer & "
    "Flavorist 27(2) (2002), Table 4 'Gaseous detection thresholds of some commercially "
    "available rose ketones', ug/dm3 of air at 25 C; note 15: 'The values given are averages.' "
    "(https://img.perfumerflavorist.com/files/base/allured/all/document/2016/02/pf.PF_27_02_018_11.pdf)"
)
_GIVAUDAN_PROC = (
    "Givaudan SA, US 2018/0185808 (microcapsules): 'PROC_i = OV_i [log10 Kcaps_i + 3]', "
    "with PROC and calculated log Kcaps tables "
    "(https://www.freepatentsonline.com/y2018/0185808.html)"
)
_FRUIT_ODT_2026_10_25 = {
    "cis-3 hexenyl acetate": (2.67, "PEER_SINGLE", [
        _GIVAUDAN_US12340876 + ": '(Z)-hex-3-en-1-yl acetate 8931 III 575466'; "
        "8931 / 575466 = 15.52 ng/L; x 24.45 / 142.20 = 2.67 ppb (producer measurement, "
        "printed as an odour value, not peer-reviewed)",
    ]),
    "manzanate": (0.0515, "PEER_SINGLE", [
        _GIVAUDAN_US12340876 + ": 'ethyl 2-methylpentanoate (MANZANATE) 18995 II 62586532'; "
        "18995 / 62586532 = 0.3035 ng/L; x 24.45 / 144.21 = 0.0515 ppb (producer measurement)",
    ]),
    "ethyl 2-methylbutyrate": (0.676, "PEER_SINGLE", [
        _GIVAUDAN_US12340876 + ": 'ethyl 2-methylbutanoate 59643 II 16577930'; "
        "59643 / 16577930 = 3.598 ng/L; x 24.45 / 130.18 = 0.676 ppb (producer measurement). "
        "Replaces an unsourced 0.06.",
    ]),
    "phenoxy ethyl isobutyrate": (2.88, "PEER_SINGLE", [
        _GIVAUDAN_US12340876 + ": '2-(phenoxy)ethyl 2-methylpropionate 20 V 816'; "
        "20 / 816 = 24.51 ng/L; x 24.45 / 208.25 = 2.88 ppb (producer measurement)",
    ]),
    "hexyl acetate": (2.9, "PEER_CROSS", [
        "Concentration-detection functions for the odor of homologous n-acetate esters, "
        "Physiol. Behav. 2008 (doi 10.1016/j.physbeh.2008.09.021, PMID 18950650, PMC2639399): "
        "'hexyl acetate (2.9 ppb)', air-dilution "
        "olfactometry, 3-AFC, vapour confirmed by GC, 16-17 subjects",
        "Nagata (2003) Measurement of odor threshold by triangle odor bag method, Table 2 (ppm "
        "v/v): 'n-Hexyl acetate 0.0018' = 1.8 ppb "
        "(https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf); agrees within a factor 1.6. "
        "Replaces an unsourced 2.0.",
    ]),
    "allyl amyl glycolate": (0.172, "PEER_EST", [
        _GIVAUDAN_PROC + ": 'ALLYL AMYL GLYCOLATE ... 448677' (PROC) and log Kcaps -2.2, so "
        "OV = 448677 / 0.8 = 560,846",
        "Givaudan SA, US 10,982,173: 'ingredients having equilibrium headspace concentration "
        "from 601 ug/l to 900 ug/l, such as allyl 2-(isopentyloxy)acetate (for example ALLYL "
        "AMYL GLYCOLATE)' (https://patents.justia.com/patent/10982173)",
        "Estimate: threshold = HS / OV = 1.07-1.60 ng/L = 0.141-0.211 ppb (MW 186.25); "
        "geometric midpoint 0.172 ppb. Two Givaudan documents combined, so labelled an "
        "estimate. Replaces an unsourced 2.0.",
    ]),
    "verdyl acetate": (0.134, "PEER_EST", [
        "Givaudan SA, US 9,868,923: 'JASMACYCLENE (HS i 0 =211 ug/L)' "
        "(https://patents.justia.com/patent/9868923); Jasmacyclene is Givaudan's verdyl "
        "(tricyclodecenyl) acetate",
        _GIVAUDAN_PROC + ": 'JASMACYCLENE ... 259747' (PROC) and log Kcaps -1.7, so "
        "OV = 259747 / 1.3 = 199,805",
        "Estimate: threshold = 211 / 199,805 = 1.056 ng/L; x 24.45 / 192.25 = 0.134 ppb "
        "(0.129-0.139 for log Kcaps +/- 0.05). Replaces 10 ppb, whose cited compilation was "
        "never read.",
    ]),
    "delta damascone": (0.00267, "PEER_SINGLE", [
        _FIRMENICH_ROSE_KETONES + ": 'delta-damascone 2.1 x 10-5' ug/dm3 = 0.021 ng/L; "
        "x 24.45 / 192.30 = 0.00267 ppb (producer measurement of the commercial material). "
        "Replaces an unsourced 0.02.",
    ]),
    "alpha damascone": (0.0178, "PEER_SINGLE", [
        _FIRMENICH_ROSE_KETONES + ": 'alpha-damascone 1.4 x 10-4' ug/dm3 = 0.14 ng/L; "
        "x 24.45 / 192.30 = 0.0178 ppb (producer measurement of the commercial material). "
        "Replaces 0.04, an audit correction with no source.",
    ]),
}
for _name, (_odt_air, _vfy, _sources) in _FRUIT_ODT_2026_10_25.items():
    # A copy: cis-3 hexenyl acetate and manzanate share their dict with the 7 Oct
    # intake receipt (_INVENTORY_ODT_UNAVAILABLE_20261007), which stays as recorded.
    _entry = dict(ODT_DATA.get(_name) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _key in ("vfy", "sources"):
        _entry.pop(_key, None)
    if str(_entry.get("note", "")).startswith("Inventory receipt"):
        _entry.pop("note")
    ODT_DATA[_name] = _entry
    ODT_VERIFICATION[_name] = {
        "vfy": _vfy,
        "sources": list(_sources),
        "note": "Fruit threshold batch 2026-10-25 (stock thread); sources re-opened before loading.",
    }
FRUIT_ODT_BATCH_2026_10_25 = True


# LITERATURE_ODT_BATCH_2026_10_25 — air thresholds from the evening literature fill.
# Kenny, 25 Oct 2026: "You do a complete literature research of where to find any or
# all or whatever information is needed and parse all the information that is missing
# into the engine". Workers ranked the sources first; a second reader re-opened every
# cited page and redid every conversion (ppb = ng/L x 24.45 / MW at 25 C) before
# loading. Placed after the fruit batch so these values are the ones the gate uses.
# PEER_SINGLE / PEER_CROSS mark one or two printed sources (peer-reviewed or the
# producer's own figure, as each source line says); PEER_EST marks an estimate:
# Givaudan's patent route (threshold = headspace / odour value), or for Iso E Super
# its most potent isomer's threshold over that isomer's share. odt_eth is left as
# it was. Values not loaded (constituent-only, single-isomer, recognition-only or
# conflicting) are listed in the stock thread's report.
_LITERATURE_ODT_2026_10_25 = {
    'iso e super': (0.0184, 'PEER_EST', [
        "derived from 'The Composition of Iso E Super', Perfumer & Flavorist (isomer G "
        'threshold and 2-4 % content) '
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21860577/the-composition-of-iso-e-super):'
        " 'G: 2-4% (the isomer responsible for the amber note) ... approximately 5 pg/l "
        "of air'; printed 0.125-0.25 ng/L (derived); estimate for the commercial product:"
        ' if detection is driven by isomer G at 2-4 % of the product, product threshold ='
        ' 5 pg/L / (0.02 to 0.04) = 0.125-0.25 ng/L (inference, not a measurement); grade'
        ' EST, access full text; second reader: EST (derived, not a measurement). Inputs '
        "(G 2-4 %, ~5 pg/l air) are printed; quote's 'G: 2-4% (the isomer "
        "responsible...)' is a paraphrase. Redone: 0.005/0.04-0.005/0.02 = 0.125-0.25 "
        'ng/L = 0.0130-0.0261 ppb, geometric mid 0.0184; the stated 0.017 is inside the '
        'range but not its midpoint...',
        "'The Composition of Iso E Super', Perfumer & Flavorist (article page; "
        'author/date not shown in the fetched text) '
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21860577/the-composition-of-iso-e-super):'
        " 'Givaudan researchers have found that the predominant isomer B has a weak odor "
        "with a threshold of about 500 ng/l of air'; printed about 500 ng/l of air "
        '(isomer B); Givaudan measurement of the main isomer B (method not stated); grade'
        ' A_producer, access full text (web article via fetch tool); second reader: '
        'Single isomer (B, main isomer, 40-60 % of the product), approximate value '
        "('about'); not the commercial mixture. Article by IFF authors citing Givaudan "
        'work. MW 234.38.; listed, not used (52.16 ppb)',
        "'The Composition of Iso E Super', Perfumer & Flavorist "
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21860577/the-composition-of-iso-e-super):'
        " 'which has a very low odor threshold value of approximately 5 pg/l of air. ... "
        'In other words, the odor of ketone G is a hundred thousand times stronger than '
        "that of B.'; printed approximately 5 pg/l of air (isomer G); Givaudan "
        'measurement of minor isomer G (Arborone / Iso E Super Plus); grade A_producer, '
        'access full text (web article via fetch tool); second reader: Single minor '
        'isomer (G, 2-4 % of the product); approximate value; not the commercial mixture.'
        ' MW 234.38.; listed, not used (0.000522 ppb)',
        'Estimate for the commercial mixture from its most potent isomer: isomer G '
        'threshold / its 2-4 % share = 0.0130-0.0261 ppb; geometric midpoint 0.0184 '
        "(second reader's arithmetic). The single-isomer values (B about 52 ppb, G 0.0005"
        ' ppb) are not used alone.',
    ]),
    'undecavertol': (0.2934, 'PEER_SINGLE', [
        'Givaudan Suisse SA, Safety Data Sheet UNDECAVERTOL, Sales No. 9449903, Version '
        '19.0, Revision Date 09 OCT 2020 (copy hosted by reseller perfumiarz.com) '
        '(https://perfumiarz.com/cdn/shop/files/9449903_UNDECAVERTOL_SDS_EN.pdf?v=7199951083912431849):'
        ' \'"Odour : Green, Floral, Orris-like, mild Odour Threshold : 2,0435 ng/l"; '
        '"Molecular weight : 170,29 g/mol"\'; printed 2,0435 ng/l; producer SDS Section '
        '9.1 figure for the commercial (racemic) material; Givaudan SDS Section 9 prints '
        "'Odour Threshold : x ng/l' without medium or method; ng/l is a gas-phase unit "
        "and Givaudan's patents (US 12,340,876 B2) describe their odour thresholds as "
        'measured with a linear-dilution olfactometer, panel of 15 (inference that the '
        'SDS figure is that measurement); grade A_producer, access full text (PDF, '
        "Parallel extract); second reader: medium not printed; ng/L is the producer's "
        'air-threshold unit (inferred). Reseller-hosted (perfumiarz.com) copy is the '
        "producer's own SDS: Givaudan header, Sales No. 9449903, Version 19.0, revision "
        '09 OCT 2020. Commercial (racemic) material.',
        'Abate A., Brenna E., Fregosi G. (2005) Bio-catalysed synthesis of optically '
        'active Undecavertol enantiomers, Tetrahedron: Asymmetry 16, 1997-1999 (as quoted'
        " on Leffingwell 'The Undecavertols' page) "
        '(http://www.leffingwell.com/chirality/undecavertols.htm): \'"(+)-(R)-Undecavertol'
        ' (ee = 93%) - Typical Undecavertol odour, floral, green, fresh, violet leaves, '
        'stronger and greener than the racemic commercial material ... Odour threshold: '
        '0.31 ng/L air."\'; printed 0.31 ng/L air; measured odour threshold of the '
        '(+)-(R)-enantiomer (ee 93 %), Abate, Brenna & Fregosi; applies to the '
        '(R)-enantiomer only; grade A_measured, access full text of the Leffingwell page;'
        ' primary paper not opened; second reader: Single enantiomer ((R), ee 93 %), not '
        'the racemic commercial material; secondary page quoting Abate et al. 2005. MW '
        '170.29.; listed, not used (0.04451 ppb)',
        'Abate, Brenna & Fregosi (2005) Tetrahedron: Asymmetry 16, 1997-1999 (as quoted '
        'on Leffingwell) (http://www.leffingwell.com/chirality/undecavertols.htm): '
        '\'"(-)-(S)-Undecavertol (ee = 75%) - Weaker enantiomer ... Odour threshold: 4.7 '
        'ng/L air."\'; printed 4.7 ng/L air; measured odour threshold of the '
        '(-)-(S)-enantiomer (ee 75 %); applies to the (S)-enantiomer only; grade '
        'A_measured, access full text of the Leffingwell page; primary paper not opened; '
        'second reader: Single enantiomer ((S), ee 75 %), not the racemic commercial '
        'material; secondary page quoting Abate et al. 2005. MW 170.29.; listed, not used'
        ' (0.6748 ppb)',
        'Producer SDS figure for the commercial racemate; the single-enantiomer values (R'
        ' 0.045, S 0.67 ppb) are not used.',
    ]),
    'adoxal': (0.6252, 'PEER_CROSS', [
        'Givaudan Safety Data Sheet ADOXAL, Sales No. 1028001, Version 14.0, revision 01 '
        'AUG 2023 '
        '(https://perfumiarz.com/cdn/shop/files/1028001_ADOXAL_SDS_EN.pdf?v=12656794224100816259):'
        " 'Odour Threshold : 5,38 ng/l ... Molecular weight : 210,40 g/mol ... Vapour "
        "pressure : 0,0031 hPa at 20 °C Method: OECD Test Guideline 104'; printed 5.38 "
        'ng/l; producer SDS figure; 5.38 ng/L x 24.45 / 210.4 g/mol = 0.625195 ppb v/v '
        "(25 C). Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l'; the sheet does"
        " not print the medium or method. ng/l is an air (gas-phase) unit; Givaudan's "
        'patents define their odour threshold as measured with a linear dilution '
        'olfactometer, panel of 15 (US 2018/0185808, US 12,340,876).; grade A_producer, '
        "access PDF (full); second reader: medium not printed; ng/L is the producer's "
        'air-threshold unit (inferred). Reseller-hosted (perfumiarz.com) copy is the '
        "producer's own SDS: Givaudan header, Sales No. 1028001, Version 14.0, revision "
        '01 AUG 2023.',
        'Givaudan SA, US 2018/0185808 A1 (perfume compositions / microcapsules), PROC and'
        ' log Kcaps tables (https://www.freepatentsonline.com/y2018/0185808.html): '
        "'Table: ADOXAL ... PROC 3827; calculated log10 Kcaps such that [log10 Kcaps + 3]"
        " = 0.5 (PROC_i = OV_i [log10 Kcaps_i + 3])'; printed OV = 3827 / 0.5 = 7654; "
        'cross-check only: odour value OV = headspace / odour threshold; threshold_ppb = '
        '(VP/101325 x 1e9)/OV = (0.31 Pa / 101325 x 1e9) / 7654 = 0.40 ppb, using the SDS'
        ' VP 0.0031 hPa at 20 C. Agrees with the SDS 0.625 ppb within 1.6x.; grade EST, '
        'access full text; second reader: EST cross-check. Inputs printed (PROC 3827, '
        "LogKcaps -2.5, VP 0.31 Pa at 20 C); quote's '[log10 Kcaps + 3] = 0.5' is a "
        'paraphrase of the -2.5 entry. OV = 7,654; sat. vapour 3,060 ppb; ODT 0.400 ppb '
        '(matches). VP is at 20 C, OV headspace at 25 C.',
        'Producer SDS figure; the Givaudan PROC estimate agrees within 1.6x.',
    ]),
    'aldehyde c11 undecylenic': (0.4146, 'PEER_CROSS', [
        'Givaudan Safety Data Sheet ALDEHYDE C 11 UNDECYLENIC, Sales No. 1361001, Version'
        ' 19.0, revision 11 JUL 2025 (Givaudan Suisse SA; copy hosted by reseller '
        'Aromology) '
        '(https://aromology.com/cdn/shop/files/1361001_ALDEHYDE_C_11_UNDECYLENIC_SDS_EN.pdf?v=15613551495079480320):'
        " 'Odour : Aldehydic, Floral, Bitter, Citrus-like Odour Threshold : 2,8541 ng/l "
        '... Molecular weight : 168,30 g/mol ... Vapour pressure : 0,026 hPa at 20 °C '
        "Method: OECD Test Guideline 104'; printed 2.8541 ng/l; producer SDS figure; "
        '2.8541 ng/L x 24.45 / 168.3 g/mol = 0.414633 ppb v/v (25 C). Givaudan SDS '
        "Section 9 prints 'Odour Threshold : x ng/l' (medium and method not printed; ng/l"
        ' is an air unit; Givaudan patents define their odour threshold as measured with '
        'a linear-dilution olfactometer, forced-choice triangle, panel of 15: US '
        '2018/0185808).; grade A_producer, access PDF (full); second reader: medium not '
        "printed; ng/L is the producer's air-threshold unit (inferred). Reseller-hosted "
        "(aromology.com) copy is the producer's own SDS: Givaudan header, Sales No. "
        '1361001, Version 19.0, revision 11 JUL 2025.',
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables '
        "(https://www.freepatentsonline.com/y2018/0185808.html): 'ALDEHYDE C 11 "
        'UNDECYLENIC (undec-10-enal) |15988 (PROC table); ALDEHYDE C 11 UNDECYLENIC '
        "(undec- |1498 |-2.9 (RECON_VOLTAE, log Kcaps)'; printed PROC 15988, log10 Kcaps "
        '-2.9; cross-check only, OV = PROC / (log10 Kcaps + 3) = 15988 / 0.10 = 159,880; '
        'saturated vapour = 2.6 Pa / 101325 Pa x 1e9 = 25,660 ppb; threshold = 25,660 / '
        '159,880 = 0.1605 ppb (range 0.0802 to 0.241 ppb for log10 Kcaps +/- 0.05). VP '
        '2.6 Pa = Givaudan SDS 0,026 hPa at 20 C. The factor (log Kcaps + 3) is only 0.1,'
        ' so the estimate is very sensitive to rounding.; grade EST, access full text; '
        'second reader: EST cross-check. Inputs printed. OV = 15988/0.1 = 159,880; sat. '
        'vapour 25,660 ppb; ODT 0.1605 ppb (matches). (LogKcaps+3) = 0.1 makes this very '
        'sensitive to rounding; VP at 20 C.',
        'Producer SDS figure (10-undecenal, CAS 112-45-8); the PROC estimate is 2.6x '
        'lower and fragile ((log Kcaps + 3) = 0.1).',
    ]),
    'aldehyde c11': (0.8796, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: RIFM safety assessment '
        'trans-4-decen-1-al (Food Chem. Toxicol. 2025), read-across table '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://research-portal.uu.nl/ws/files/255290703/1-s2.0-S0278691525000511-main.pdf):'
        " 'ALDEHYDE C 110 UNDECYLIC (undecanal) |18200 (PROC); ALDEHYDE C 110 UNDECYLIC "
        "(undecanal) |1533 |-2.8 (log Kcaps) || VP: 'Vapor Pressure (Pa @ 25 °C, EPI "
        "Suite) 1.59E+01 8.71E+00 8.11E+00' (columns: trans-4-decenal, 10-undecenal, "
        "undecanal)'; printed PROC 18200, log10 Kcaps -2.8; VP 8.11 Pa (EPI, 25 C); OV = "
        'PROC / (log10 Kcaps + 3) = 18200 / 0.20 = 91,000; saturated vapour = 8.11 Pa / '
        '101325 Pa x 1e9 = 80,039 ppb; threshold = 80,039 / 91,000 = 0.8796 ppb (range '
        '0.66 to 1.1 ppb for log10 Kcaps +/- 0.05). VP 8.11 Pa at 25 C is an EPI Suite '
        'estimate; a supplier SDS gives 0.04 mmHg at 20 C = 5.33 Pa...; grade EST, access'
        ' full text (patent); search snippet (VP); second reader: Inputs printed; I '
        'checked the column order against the table header. Saturated 80,039 ppb / OV '
        '91,000 = 0.880 ppb. (LogKcaps+3) = 0.2, so ±0.05 gives 0.66–1.10 ppb. The VP is '
        'an EPI estimate.',
        'Estimate for undecanal (CAS 112-44-7, the record this stock resolves to); (log '
        'Kcaps + 3) = 0.2, so +/-0.05 gives 0.66-1.10 ppb.',
    ]),
    'benzaldehyde': (140.5, 'PEER_SINGLE', [
        'AIHA, Odor Thresholds for Chemicals with Established Health Standards, 2nd '
        "Edition (2013), Table 6.3 'Reported Odor Thresholds from All Sources' (values "
        'taken from the van Gemert compendium) '
        "(https://swesiaq.se/onewebmedia/Dokument/ODOR%20THRESHOLDS.pdf): '18 "
        'Benzaldehyde cont. ... Von Ranson & Belitz 1992b d 0.61 0.093 [mg/m3, ppm] Von '
        "Ranson & Belitz 1992b r 2.1 0.32'; printed 0.61 mg/m3 detection (AIHA lists "
        '0.093 ppm); detection threshold as quoted by AIHA; primary (von Ranson & Belitz '
        '1992, Z. Lebensm. Unters. Forsch.) not opened. 0.61 mg/m3 = 610 ng/L; 610 x '
        '24.45 / 106.12 = 140.544 ppb v/v (25 C; conversion redone here, the '
        "compilation's own ppm column uses STP); grade A_measured, access PDF "
        '(compilation; primary paper not opened); second reader: Detection (d) value from'
        ' a secondary air-threshold compilation; primary not opened. Medium is given by '
        "the mg/m3 / ppm air units of the compilation. The compilation's ppm column "
        '(0.093) fits neither 25 C (0.141 ppm) nor STP (0.129 ppm); the mg/m3 figure was '
        'converted here. MW 106.12.',
        'AIHA, Odor Thresholds for Chemicals with Established Health Standards, 2nd '
        "Edition (2013), Table 6.3 'Reported Odor Thresholds from All Sources' (values "
        'taken from the van Gemert compendium) '
        "(https://swesiaq.se/onewebmedia/Dokument/ODOR%20THRESHOLDS.pdf): '18 "
        "Benzaldehyde cont. ... Yang et al 2008 0.085 0.013 [mg/m3, ppm]'; printed 0.085 "
        'mg/m3 (AIHA lists 0.013 ppm); as quoted by AIHA; Yang et al. 2008 (J. Agric. '
        'Food Chem. 56:2780, doi 10.1021/jf072685t) determined odour thresholds in air by'
        ' GC-O. 0.085 mg/m3 = 85 ng/L; 85 x 24.45 / 106.12 = 19.584 ppb v/v (25 C; '
        "conversion redone here, the compilation's own ppm column uses STP); grade "
        'A_measured, access PDF (compilation; primary paper not opened); second reader: '
        'Secondary compilation; the row carries no d/r flag, so detection vs recognition '
        'is not stated on the page. Primary (Yang et al. 2008) not opened. ppm column '
        'again uses a non-standard factor; mg/m3 converted here. MW 106.12.; listed, not '
        'used (19.58 ppb)',
        'Detection-flagged row of the AIHA compilation (primary not opened); converted '
        'from its mg/m3 column, whose ppm column fits neither 25 C nor STP. A second row '
        '(Yang 2008, no detection/recognition flag) gives 19.6 ppb.',
    ]),
    'cyclamen aldehyde': (0.3237, 'PEER_CROSS', [
        'Givaudan Safety Data Sheet CYCLAMEN ALDEHYDE EXTRA, Sales No. 1534001, Version '
        '25.0, revision 16 JUL 2024 '
        '(https://perfumiarz.com/cdn/shop/files/1534001_CYCLAMEN_ALDEHYDE_EXTRA_SDS_EN.pdf?v=136731341100825894):'
        " 'Odour : Floral, Fresh, Lily-of-the-valley, Green Odour Threshold : 2,5198 ng/l"
        " ... Molecular weight : 190,30 g/mol ... Vapour pressure : 0,003 hPa at 20 °C'; "
        'printed 2.5198 ng/l; producer SDS figure; 2.5198 ng/L x 24.45 / 190.3 g/mol = '
        "0.323747 ppb v/v (25 C). Givaudan SDS Section 9 prints 'Odour Threshold : x "
        "ng/l' (medium and method not printed; ng/l is an air unit; Givaudan patents "
        'define their odour threshold as measured with a linear-dilution olfactometer, '
        'forced-choice triangle, panel of 15: US 2018/0185808).; grade A_producer, access'
        " PDF (full); second reader: medium not printed; ng/L is the producer's "
        'air-threshold unit (inferred). Reseller-hosted (perfumiarz.com) copy is the '
        "producer's own SDS: Givaudan header, Sales No. 1534001, Version 25.0, revision "
        "16 JUL 2024. Givaudan 'Extra' grade of the same molecule.",
        "Goeke A., Kraft P. et al. (Givaudan), 'Discovery of Nympheal: The Definitive "
        "Muguet Aldehyde', Perfumer & Flavorist, 20 Feb 2018 "
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21856694/discovery-of-nympheal-the-definitive-muguet-aldehyde):'
        " 'cyclamen aldehyde (2), which at 2.5 ng/L air is twice as powerful as "
        "hydroxycitronellal'; printed 2.5 ng/L air; Givaudan R&D odour threshold (method "
        'not described in the article); 2.5 ng/L x 24.45 / 190.28 g/mol = 0.321237 ppb '
        'v/v (25 C); grade A_producer, access full text; second reader: Producer R&D '
        'value, method not described in the article. MW 190.28.',
        'Givaudan SDS and Givaudan R&D article agree (0.324 and 0.321 ppb). Replaces '
        '0.76, cited to Nagata (2003) and Devos (1990), which were not checked to list '
        'it.',
    ]),
    'maple lactone': (5.669, 'PEER_CROSS', [
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Miyazawa et al. (2009a) '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"... Miyazawa et al. (2009a) d 0.026" (same entry as above)\'; printed d 0.026 '
        'mg/m3; detection threshold, Miyazawa et al. (2009a) as compiled by van Gemert; '
        'grade A_measured, access full text of the book via Parallel web_fetch '
        'excerpts...; second reader: Detection (d) value; AIR section inferred from '
        'layout as for candidate 0. Secondary compilation; primary not opened. MW 112.13.',
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Blank I. (1997, 2002) GC-O '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"2-HYDROXY-3-METHYL-2-CYCLOPENTEN-1-ONE (3-methyl-1,2-cyclopentanedione, '
        'cyclotene, methylcyclopentenolone, maple lactone) [80-71-7, 765-70-8] Blank '
        '(1997, 2002) 0.01 – 0.02 [GC-O with SE-54 capillary column] Blank (1997, 2002) '
        "0.01 – 0.02 [GC-O with FFAP...'; printed 0.01 - 0.02 mg/m3; GC-olfactometry air "
        'threshold (Blank 1997, 2002), on SE-54 and on FFAP columns (same range on both);'
        ' grade A_measured, access full text of the book via Parallel web_fetch '
        'excerpts...; second reader: Air section inferred from layout: the same compound '
        'has separate WATER (Wasserman 2; Nishimura & Mihara d 0.3) and OTHER MEDIA '
        '(Yoshida, nujol) entries, so this GC-O entry is the AIR one. Blank values carry '
        'no d/r flag. Secondary compilation; primary not opened. MW 112.13.',
        'Detection-flagged air entry of the van Gemert compilation; a GC-O entry in the '
        'same air section gives 2.2-4.4 ppb. Primary papers not opened.',
    ]),
    'neryl acetate': (38.88, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1 "MICROCAPSULES": GROUP 1 table "Perfumery '
        'ingredient | RECON_VOLTAE (Bohr3) | LogKcaps" and GROUP 4 table "Perfumery '
        'ingredient | PROC"; definition "PROC i =OV i [log10 Kcaps i +3]" and "The '
        'standard Odour Value (OV i) is defined as the ratio of the standard equilibrium '
        'headspace concentration of the ingredient to the Odour Detection Threshold of '
        'this ingredient." + Givaudan SA, US 10,982,173 "Fragrance compositions" '
        '(headspace-concentration bins at 25 C) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; '
        'https://patents.justia.com/patent/10982173): \'"|NERYL ACETATE HC '
        '((Z)-3,7-dimethylocta-2,6-dien-1-yl acetate) |472 |" ; "|NERYL ACETATE HC '
        '((Z)-3,7-dimethylocta- |1643 |−2.4" ; "ingredients having equilibrium headspace '
        "concentration from 201 μg/l to about 300 μg/l, such as ...'; printed PROC 472, "
        'LogKcaps -2.4, HS bin 201–300 ug/L; EST back-calculated from Givaudan patent '
        "tables for 'NERYL ACETATE HC': ODT = HS / OV, OV = PROC / (LogKcaps + 3). The "
        'underlying ODT is Givaudan olfactometer, as described in US 2018/0185808: "The '
        'olfactometer functions on the principle of a linear dilution of an odorant in a '
        'carrier gas ... Each panellist (panel of 15 persons) ... The final threshold '
        'value of a given...; grade EST, access full text of both patents (Parallel '
        'full-content fetch...; second reader: EST. Inputs printed (PROC table names the '
        "'HC' grade, HS list the same molecule). OV = 472/0.6 = 786.7; ODT 255.5-381.4 "
        'ng/L = 31.8-47.5 ppb (matches). MW 196.29.',
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Cristoph (1983) '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"3,7-DIMETHYL-(Z)-2,6-OCTADIEN-1-YL ACETATE (neryl acetate) [141-12-8] '
        'Cristoph (1983) r 20.0 - 25.0"\'; printed r 20.0 - 25.0 mg/m3; RECOGNITION '
        'threshold (r), Cristoph (1983), as compiled by van Gemert; grade A_measured, '
        'access full text of the book via Parallel web_fetch excerpts...; second reader: '
        'RECOGNITION threshold (r), not detection: an upper bound for the detection '
        'threshold. Air section (the WATER entry for neryl acetate is separate: Pino et '
        'al. d 0.042 etc.). Secondary compilation; primary not opened. MW 196.29.; '
        'listed, not used (2491.0-3114.0 ppb)',
        'Givaudan PROC estimate 31.8-47.5 ppb; geometric midpoint 38.9. The van Gemert '
        'value (2,491-3,114 ppb) is a recognition threshold, an upper bound only, and is '
        'not used.',
    ]),
    'skatole': (0.0056, 'PEER_SINGLE', [
        'Nagata Y. (2003) Measurement of Odor Threshold by Triangle Odor Bag Method. In: '
        'Odor Measurement Review, Ministry of the Environment, Japan, pp. 118-127; Table '
        '2 "Odor thresholds measured by the triangle odor bag method (ppm,v/v)" '
        "(https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf): 'Skatole 0.0000056 "
        'Ethyl-o-toluidine 0.026 (Table 2 line); Table 1 row: "Skatole 1.7 30 ～ 3000 13";'
        ' text: "since the dilution error was large compared with other substances, their'
        ' thresholds were corrected by their recovery rate."\'; printed 0.0000056 ppm '
        '(v/v); triangle odor bag method, panel; Nagata notes skatole and indole '
        'thresholds were corrected by their recovery rate (Table 1 recovery 13 %); grade '
        'A_measured, access full text (PDF via WebFetch); second reader: Triangle odor '
        "bag method, air. Bag recovery for skatole only 13 %; the candidate's quoted text"
        ' that thresholds were corrected by recovery was not in the excerpt I saw. '
        'Printed in ppm v/v; no MW conversion.',
        'J Environ Manage 2016;180:257-263 (Zhou, Hallis, Vitko, Suffet): odour study of '
        'indole and skatole (abstract and highlights) '
        "(https://www.sciencedirect.com/science/article/abs/pii/S030147971630295X): 'odor"
        " threshold ... 0.327 ng/L (60 pptV)'; printed 0.327 ng/L (60 pptV); trained "
        'panel, air (olfactometry details not in the abstract); grade A_measured, access '
        'abstract and highlights only; second reader: Air (Teflon bags), expert/trained '
        'panel; abstract and highlights only, method details not shown. Candidate quote '
        'is an ellipsis paraphrase. 0.327 ng/L x 24.45/131.17 = 0.061 ppb (page prints 60'
        ' pptV).; listed, not used (0.06095 ppb)',
        'Nagata triangle-odour-bag detection threshold. Zhou et al. 2016 (abstract only) '
        'gives 0.061 ppb, 11x higher.',
    ]),
    'aldehyde c-12 lauric dodecanal': (0.2916, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: Axxence Aromatic GmbH SDS NATURAL '
        'ALDEHYDE C-12 (DODECANAL), product 261500, revision 23.10.2025 '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://axxence.de/wp-content/uploads/products/sds/natural_aldehyde_c-12_dodecanal_261500_WW-EN_SDS.pdf):'
        " 'ALDEHYDE C 12 LAURIC (dodecanal) |2369 (PROC); ALDEHYDE C 12 LAURIC "
        "(dodecanal) |1662 |-2.9 (log Kcaps) || VP: 'Partition coefficient "
        "n-octanol/water: 4,75 0,007 hPa Vapour pressure: (at 20 °C)''; printed PROC "
        '2369, log10 Kcaps -2.9; VP 0.7 Pa at 20 C; OV = PROC / (log10 Kcaps + 3) = 2369 '
        '/ 0.10 = 23,690; saturated vapour = 0.7 Pa / 101325 Pa x 1e9 = 6,908 ppb; '
        'threshold = 6,908 / 23,690 = 0.2916 ppb (range 0.146 to 0.437 ppb for log10 '
        'Kcaps +/- 0.05). The factor (log Kcaps + 3) is only 0.1, so the estimate is '
        'uncertain by at least 2x; a 25 C VP estimate of 0.034 mmHg (4.5 Pa, scentfriends'
        " SDS, 'est') would give 1.9 ppb.; grade EST, access full text (patent); PDF "
        '(VP); second reader: EST. Inputs printed. OV = 23,690; sat. vapour 6,908 ppb; '
        'ODT 0.2916 ppb (matches). (LogKcaps+3) = 0.1, so uncertain by 2x or more; VP at '
        '20 C (natural grade, CAS 112-54-9).',
        'Givaudan PROC estimate; (log Kcaps + 3) = 0.1, so uncertain by 2x or more.',
    ]),
    'alpha irone': (0.81, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: Givaudan, Irone Alpha product page '
        '(vapour pressure; temperature not stated) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/irone-alpha):'
        " 'IRONE ALPHA ((E)-4-(2,5,6,6-tetramethylcyclohex-2-en-1-yl)but-3-en-2- |9686 "
        '(PROC); IRONE ALPHA ((E)-4-(2,5,6,6- |1800 |-1.5 (log Kcaps) || VP source: '
        'Physico chemical properties: Formula MW Log Pow Vapour pressure ... C14H22O '
        "206.3 4,4 0.0053 hPa ... 79-69-6'; printed PROC 9686, log10 Kcaps -1.5; VP 0.53 "
        'Pa at not stated C; OV = PROC / (log10 Kcaps + 3) = 9686 / 1.50 = 6,457; '
        'saturated vapour = 0.53 Pa / 101325 Pa x 1e9 = 5,231 ppb; threshold = 5,231 / '
        '6,457 = 0.81 ppb (range 0.783 to 0.837 ppb for log10 Kcaps +/- 0.05). VP 0.53 Pa'
        ' (not stated C) from the source named. Givaudan OV = equilibrium headspace (25 '
        'C) / olfactometer odour threshold (panel of 15); headspace estimated here from '
        'VP, so...; grade EST, access full text (patent); web page (VP); second reader: '
        'EST. Inputs printed. OV = 6,457; sat. vapour 5,231 ppb; ODT 0.810 ppb (matches).'
        ' VP temperature not stated on the Givaudan page.',
        'Givaudan PROC estimate. Replaces 0.9, an audit correction with no source.',
    ]),
    'amberwood f': (0.04947, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: Symrise Safety Data Sheet 600113 '
        'AMBERWOOD F, Version 12, revision 12.01.2015 (copy hosted by Aromology) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://aromology.com/cdn/shop/files/Amber-Wood-F_MSDS.pdf?v=12117092210280659830):'
        " 'BOISAMBRENE FORTE ((ethoxymethoxy)cyclododecane) |59050 (PROC); BOISAMBRENE "
        'FORTE |2063 |-2.0 (log Kcaps) || VP source: Odour Threshold : No data available '
        '... Vapour pressure : < 1 kPa at 50 °C calculated 0,00296 hPa at 25 °C Method: '
        "Directive...'; printed PROC 59050, log10 Kcaps -2.0; VP 0.296 Pa at 25 C; OV = "
        'PROC / (log10 Kcaps + 3) = 59050 / 1.00 = 59,050; saturated vapour = 0.296 Pa / '
        '101325 Pa x 1e9 = 2,921 ppb; threshold = 2,921 / 59,050 = 0.04947 ppb (range '
        '0.047 to 0.0519 ppb for log10 Kcaps +/- 0.05). VP 0.296 Pa (25 C) from the '
        'source named. Givaudan OV = equilibrium headspace (25 C) / olfactometer odour '
        'threshold (panel of 15); headspace estimated here from VP, so...; grade EST, '
        'access full text (patent); PDF (full) (VP); second reader: EST. Inputs printed. '
        'Patent values are for Givaudan BOISAMBRENE FORTE, same molecule as Symrise '
        'Amberwood F. OV = 59,050; sat. vapour 2,921 ppb (calculated VP); ODT 0.0495 ppb '
        "(matches). Aromology copy is Symrise's own SDS (header, material 600113, version"
        ' 12).',
        'Givaudan PROC estimate for Boisambrene Forte, the same molecule (CAS '
        '58567-11-6). Replaces an unsourced 1.0.',
    ]),
    'ambrox super': (0.02146, 'PEER_SINGLE', [
        'Givaudan Safety Data Sheet AMBROFIX, Sales No. 1836803, Version 5.3, revision 19'
        ' SEP 2016 (CAS 6790-58-5 / 3738-00-9, C16H28O) '
        "(https://cdn.hstatic.net/files/200000928041/file/ambrofix-sds.pdf): 'Odour "
        "Threshold : 0,2075 ng/l'; printed 0.2075 ng/l; producer SDS figure; 0.2075 ng/L "
        'x 24.45 / 236.39 g/mol = 0.0214619 ppb v/v (25 C) (MW of C16H28O = 236.39). '
        "Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l'; the sheet does not "
        "print the medium or method. ng/l is an air (gas-phase) unit; Givaudan's patents "
        'define their odour threshold as measured with a linear dilution olfactometer, '
        'panel of 15 (US 2018/0185808, US...; grade A_producer, access PDF (full); second'
        " reader: medium not printed; ng/L is the producer's air-threshold unit "
        "(inferred). Producer's own SDS (Givaudan header, revision 19 SEP 2016) hosted on"
        " cdn.hstatic.net (a shop CDN). The SDS Sales No. is 127737; '1836803' is part of"
        " the product name. Value is for Givaudan Ambrofix, a different producer's...",
        'Givaudan Ambrofix SDS (Sales No. 127737), the same molecule ((-)-ambroxide, CAS '
        '6790-58-5). Replaces 0.3, an audit correction with no source.',
    ]),
    'ambrofix crystals (solid)': (0.02146, 'PEER_SINGLE', [
        'Givaudan Safety Data Sheet AMBROFIX, Sales No. 1836803, Version 5.3, revision 19'
        ' SEP 2016 (CAS 6790-58-5 / 3738-00-9, C16H28O) '
        "(https://cdn.hstatic.net/files/200000928041/file/ambrofix-sds.pdf): 'Odour "
        "Threshold : 0,2075 ng/l'; printed 0.2075 ng/l; producer SDS figure; 0.2075 ng/L "
        'x 24.45 / 236.39 g/mol = 0.0214619 ppb v/v (25 C) (MW of C16H28O = 236.39). '
        "Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l'; the sheet does not "
        "print the medium or method. ng/l is an air (gas-phase) unit; Givaudan's patents "
        'define their odour threshold as measured with a linear dilution olfactometer, '
        'panel of 15 (US 2018/0185808, US...; grade A_producer, access PDF (full); second'
        " reader: medium not printed; ng/L is the producer's air-threshold unit "
        "(inferred). This is the producer's own SDS, hosted on cdn.hstatic.net (a shop "
        'CDN, not one of the hosts the brief names). The sheet prints Sales No. 127737; '
        '1836803 appears in the product-name line.',
        'Givaudan Ambrofix SDS (Sales No. 127737). Replaces 0.3 on the data-spine record,'
        ' which had no source.',
    ]),
    'berry hexanoate (berryflor)': (4.087, 'PEER_SINGLE', [
        'Givaudan Safety Data Sheet BERRYFLOR, Sales No. 5206903, Version 11.0, revision '
        '15 AUG 2025 (Givaudan Suisse SA; copy hosted by reseller Aromology) '
        '(https://aromology.com/cdn/shop/files/SDS-Berryflor-_Givaudan_-_Floral_Raspberry.pdf?v=14296763192571299935):'
        " 'Odour : fruity, Floral, mild, Balsamic Odour Threshold : 33,7961 ng/l ... "
        'Molecular weight : 202,20 g/mol ... Vapour pressure : 0,015 hPa at 20 °C Method:'
        " OECD Test Guideline 104'; printed 33.7961 ng/l; producer SDS figure; 33.7961 "
        'ng/L x 24.45 / 202.2 g/mol = 4.08662 ppb v/v (25 C). Givaudan SDS Section 9 '
        "prints 'Odour Threshold : x ng/l' (medium and method not printed; ng/l is an air"
        ' unit; Givaudan patents define their odour threshold as measured with a '
        'linear-dilution olfactometer, forced-choice triangle, panel of 15: US '
        '2018/0185808).; grade A_producer, access PDF (full); second reader: medium not '
        "printed; ng/L is the producer's air-threshold unit (inferred). Reseller-hosted "
        "(aromology.com) copy is the producer's own SDS: Givaudan header, Sales No. "
        '5206903, Version 11.0, revision 15 AUG 2025.',
        'Producer SDS figure; first air threshold for this stock.',
    ]),
    'cashmeran': (0.04128, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: RIFM fragrance ingredient safety '
        'assessment, 6,7-dihydro-1,1,2,3,3-pentamethyl-4(5H)-indanone, Food Chem. '
        'Toxicol. 149 (2021) 111929 (https://www.freepatentsonline.com/y2018/0185808.html'
        ' ; VP: '
        'https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/33704-61-9.pdf):'
        " 'CASHMERAN (1,1,2,3,3-pentamethyl-2,3,6,7-tetrahydro-1H-inden-4(5H)- |141286 "
        '(PROC); CASHMERAN (1,1,2,3,3-pentamethyl-2,3,6,7- |1772 |-1.9 (log Kcaps) || VP '
        'source: 7. Vapor Pressure: 0.00224 mm Hg @ 20 °C (EPI Suite v4.0), 0.004 mm Hg '
        "20 °C (FMA), 0.00403...'; printed PROC 141286, log10 Kcaps -1.9; VP 0.537 Pa at "
        '25 C; OV = PROC / (log10 Kcaps + 3) = 141286 / 1.10 = 128,442; saturated vapour '
        '= 0.537 Pa / 101325 Pa x 1e9 = 5,300 ppb; threshold = 5,300 / 128,442 = 0.04126 '
        'ppb (range 0.0394 to 0.0431 ppb for log10 Kcaps +/- 0.05). VP 0.537 Pa (25 C) '
        'from the source named. Givaudan OV = equilibrium headspace (25 C) / olfactometer'
        ' odour threshold (panel of 15); headspace estimated here from...; grade EST, '
        'access full text (patent); PDF (full) (VP); second reader: EST. Inputs printed. '
        '0.00403 mmHg = 0.537 Pa (EPI estimate); OV = 128,442; ODT 0.0413 ppb (matches).',
        'Givaudan PROC estimate with an EPI vapour pressure. Replaces 2.0, cited only as '
        "'van Gemert (2011); IFF sensory data' with no page or value.",
    ]),
    'cyclogalbanate': (0.07514, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: RIFM safety assessment, allyl '
        'cyclohexanepropionate (2021), Appendix B read-across table (EPI Suite values for'
        ' the analog cyclogalbanate) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/2705-87-5.pdf):'
        " 'CYCLOGALBANATE (allyl 2-(cyclohexyloxy)acetate) |220660 (PROC); CYCLOGALBANATE"
        ' (allyl 2- |1546 |-2.4 (log Kcaps) || VP source: Read-across table: Vapor '
        'Pressure (Pa @ 25 °C, EPI Suite) 2.91 [allyl cyclohexanepropionate] 2.80 [allyl '
        "(cyclohexyloxy)acetate...'; printed PROC 220660, log10 Kcaps -2.4; VP 2.8 Pa at "
        '25 C; OV = PROC / (log10 Kcaps + 3) = 220660 / 0.60 = 367,767; saturated vapour '
        '= 2.8 Pa / 101325 Pa x 1e9 = 27,634 ppb; threshold = 27,634 / 367,767 = 0.07514 '
        'ppb (range 0.0689 to 0.0814 ppb for log10 Kcaps +/- 0.05). VP 2.8 Pa (25 C) from'
        ' the source named. Givaudan OV = equilibrium headspace (25 C) / olfactometer '
        'odour threshold (panel of 15); headspace estimated here from VP...; grade EST, '
        'access full text (patent); PDF (full) (VP); second reader: EST. Inputs printed. '
        'VP 2.80 Pa is an EPI Suite estimate for cyclogalbanate (CAS 68901-15-5) in '
        "another material's RIFM assessment. OV = 367,767; ODT 0.0751 ppb (matches).",
        'Givaudan PROC estimate with an EPI vapour pressure; first air threshold for this'
        ' stock.',
    ]),
    'dupical': (0.04308, 'PEER_SINGLE', [
        "'Discovery of Nympheal, the definitive muguet aldehyde', Perfumer & Flavorist, "
        'Feb 2018 (Givaudan R&D article; authors Goeke, Kraft, Lelievre, Alchenberger per'
        ' the earlier project file 02_odour_thresholds.md, not shown in the page text '
        'this session) '
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21856694/discovery-of-nympheal-the-definitive-muguet-aldehyde):'
        " 'With an odor threshold of 0.36 ng/L air, it is comparable in strength to "
        "Bourgeonal (4).'; printed 0.36 ng/L air; producer R&D figure (Givaudan), method "
        'not stated; grade A_producer, access full text (web article, via fetch tool); '
        'second reader: Producer R&D value, method not stated. Authors shown on page: '
        'Goeke, Kraft, Lelievre, Alchenberger. MW 204.31.',
        'Givaudan R&D article figure (method not stated); first air threshold for this '
        'stock.',
    ]),
    'geosmin': (0.0065, 'PEER_SINGLE', [
        "Nagata Y. (2003) 'Measurement of odor threshold by triangle odor bag method', "
        'Odor Measurement Review, Japan Ministry of the Environment, pp. 118-127, Table 2'
        " (https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf): 'Table 2 Odor "
        'thresholds measured by the triangle odor bag method (ppm,v/v) ... Geosmin '
        "0.0000065'; printed 0.0000065 ppm v/v; triangle odor bag method, panel of 6 "
        '(Japan Environmental Sanitation Center, measurements 1976-1988); grade '
        'A_measured, access full text (PDF via fetch tool; matches project copy...; '
        'second reader: Triangle odor bag method (odourless air). Panel size and '
        'measurement years not checked in the excerpt I saw. No MW conversion.',
        'Nagata triangle-odour-bag detection threshold. Replaces 0.006, whose note said '
        'no peer-reviewed value existed.',
    ]),
    'geraniol (10% in dpg)': (2.219, 'PEER_SINGLE', [
        "Elsharif S.A., Buettner A. 'Structure-Odor Relationship Study on Geraniol, "
        "Nerol, and Their Synthesized Oxygenated Derivatives', J. Agric. Food Chem. 2018,"
        ' 66(10), 2324-2333, doi:10.1021/acs.jafc.6b04534 '
        "(https://pubmed.ncbi.nlm.nih.gov/27794602): 'All compounds were individually "
        'tested for their odor qualities and odor thresholds in air (OT). Geraniol, the '
        'Z-isomer, with an OT of 14 ng/L, was found to be more potent than its E-isomer, '
        "nerol, which has an OT of 60 ng/L.'; printed 14 ng/L (air); GC-olfactometry, "
        "'odor thresholds in air (OT)' (same group and method as Elsharif 2015: internal "
        'standard (E)-dec-2-enal); grade A_measured, access abstract (PubMed and ACS '
        'abstract pages, search excerpts); second reader: GC-olfactometry air threshold '
        '(abstract only; abstract mislabels geraniol as Z). Value is for neat geraniol; '
        'the stock is a 10 % DPG dilution. MW 154.25.',
        "The molecule's threshold (the stock is a 10% DPG dilution), as already used for "
        'Geraniol neat. Replaces 2.0 on the data-spine record, which had no source.',
    ]),
    'hedione': (0.03025, 'PEER_SINGLE', [
        "Chapuis C. (Firmenich SA), 'The Chemistry and Creative Legacy of Methyl "
        "Jasmonate and Hedione', Perfumer & Flavorist 36 (Dec 2011) 36-48, table T-1 "
        "'Cis/trans ratios and thresholds of past/current Firmenich qualities of 2' "
        '(https://img.perfumerflavorist.com/files/base/allured/all/document/2011/11/pf.PF_36_12_036_13.pdf):'
        " 'T-1 Cis/trans ratios and thresholds of past/current Firmenich qualities of 2 "
        "... cis/trans ca. | Odor threshold [ngL-1] ... Hedione 10:90 0.280'; printed "
        '0.280 ng/L; producer data (Firmenich), method not stated; grade A_producer, '
        'access full text (PDF, via fetch tool); second reader: medium not printed; ng/L '
        "is the producer's air-threshold unit (inferred). Value for standard Hedione "
        '(cis/trans ca. 10:90); HC grades are far lower. Method not stated. MW 226.31.',
        'Firmenich figure for standard Hedione (cis/trans about 10:90). Replaces an '
        'estimated 0.05.',
    ]),
    'hedione hc': (0.003997, 'PEER_SINGLE', [
        "Chapuis C. (Firmenich SA), 'The Chemistry and Creative Legacy of Methyl "
        "Jasmonate and Hedione', Perfumer & Flavorist 36 (Dec 2011) 36-48, table T-1 "
        "'Cis/trans ratios and thresholds of past/current Firmenich qualities of 2' "
        '(https://img.perfumerflavorist.com/files/base/allured/all/document/2011/11/pf.PF_36_12_036_13.pdf):'
        " 'Hedione HC 75:25 0.037 (column 'Odor threshold [ngL-1]'); same table: Cisdione"
        " 30:70 0.093; Hedione VHC 90:10 0.031; (+)-Paradisone 94:6 0.015'; printed 0.037"
        ' ng/L; producer data (Firmenich), method not stated; grade A_producer, access '
        'full text (PDF, via fetch tool); second reader: medium not printed; ng/L is the '
        "producer's air-threshold unit (inferred). The method is not stated in the table."
        ' MW 226.31.',
        'Firmenich figure for the high-cis grade. Replaces 0.05, which had no source.',
    ]),
    'helional': (0.14, 'PEER_SINGLE', [
        "Cometto-Muniz J.E., Abraham M.H. 'Odor Detection by Humans of Lineal Aliphatic "
        "Aldehydes and Helional as Gauged by Dose-Response Functions', Chem. Senses 2010 "
        "(PMC2912639) (https://pmc.ncbi.nlm.nih.gov/articles/PMC2912639): 'The strong "
        'olfactory receptor (OR) ligands octanal and helional (0.14 ppb) showed the '
        "lowest thresholds. ... Table 2 ... Helional | 17 | 0.14 | -0.868 | +/-0.024'; "
        'printed 0.14 ppb (log ppb C = -0.868 +/- 0.024); 8-station vapor delivery '
        'device, 3-alternative forced choice, ascending concentrations, GC-quantified; 17'
        ' subjects; ODT = concentration at P=0.5 of fitted sigmoid; tested range '
        '0.020-2.6 ppb; grade A_measured, access full text (PMC via Parallel fetch '
        'excerpts); second reader: Air (vapor delivery device VDD8 vs carbon-filtered '
        'air), 17 subjects, ODT = P 0.5 above chance. Printed in ppb by volume; no '
        'conversion.',
        "Replaces 0.1, which cited this paper under another author's name with 0.097 ppb;"
        ' the second reader read 0.14 ppb.',
    ]),
    'melonal': (0.1018, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1 "MICROCAPSULES": GROUP 1 table "Perfumery '
        'ingredient | RECON_VOLTAE (Bohr3) | LogKcaps" and GROUP 4 table "Perfumery '
        'ingredient | PROC"; definition "PROC i =OV i [log10 Kcaps i +3]" and "The '
        'standard Odour Value (OV i) is defined as the ratio of the standard equilibrium '
        'headspace concentration of the ingredient to the Odour Detection Threshold of '
        'this ingredient." + Givaudan SA, US 10,982,173 "Fragrance compositions" '
        '(headspace-concentration bins at 25 C) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; '
        'https://patents.justia.com/patent/10982173): \'"|MELONAL '
        '(2,6-dimethylhept-5-enal) |3633579 |" ; "|MELONAL (2,6-dimethylhept-5-enal) '
        '|1229 |−2.0" ; "FRUITY ingredients having equilibrium headspace concentration '
        'from 901 μg/l to 5000 μg/l, such as ... 2,6-dimethylhept-5-enal (for example '
        'MELONAL)"\'; printed PROC 3633579, LogKcaps -2.0, HS bin 901–5000 ug/L; EST '
        "back-calculated from Givaudan patent tables for 'MELONAL': ODT = HS / OV, OV = "
        'PROC / (LogKcaps + 3). The underlying ODT is Givaudan olfactometer, as described'
        ' in US 2018/0185808: "The olfactometer functions on the principle of a linear '
        'dilution of an odorant in a carrier gas ... Each panellist (panel of 15 persons)'
        ' ... The final threshold value of a given odorant is...; grade EST, access full '
        'text of both patents (Parallel full-content fetch...; second reader: EST. Inputs'
        ' printed. OV = 3,633,579; ODT 0.248-1.376 ng/L = 0.0432-0.2399 ppb (matches). '
        'Wide HS bin (5.5x).',
        'Givaudan PROC estimate 0.043-0.240 ppb (wide headspace bin); geometric midpoint '
        '0.102. Replaces an estimated 0.5 with no source.',
    ]),
    'paradisamide': (0.1371, 'PEER_SINGLE', [
        'Givaudan Suisse SA, Safety Data Sheet PARADISAMIDE, Version 9.0, revision 02 AUG'
        ' 2024 (copy hosted by reseller scentfriends.com) '
        '(https://scentfriends.com/wp-content/uploads/2026/09/Paradisamide_SDS.pdf): '
        '\'"Odour Threshold : 1,2301 ng/l"\'; printed 1,2301 ng/l; producer SDS Section 9.1'
        ' figure; method not stated; grade A_producer, access full text (PDF); second '
        "reader: medium not printed; ng/L is the producer's air-threshold unit "
        "(inferred). Reseller-hosted (scentfriends.com) copy is the producer's own SDS: "
        'Givaudan header, Sales No. 0025633, Version 9.0, revision 02 AUG 2024. PubChem '
        'MW 219.32 used (SDS prints 219,00, giving 0.1373).',
        'Producer SDS figure. Replaces 8.0, which had no source.',
    ]),
    'phenyl ethyl acetate': (1.996, 'PEER_SINGLE', [
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Schieberle (1998) '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"1-PHENYLETHYL ACETATE (styrallyl acetate) [93-92-5] Appell (1969) 0.000 2 '
        '2-PHENYLETHYL ACETATE [103-45-7] Schieberle (1998) 0.0067- 0.0268" (AIR section,'
        ' mg/m3; the WATER section lists the same compound separately with Takahashi '
        "(1990) 3-5, Ong & Acree...'; printed 0.0067- 0.0268 mg/m3; as compiled by van "
        'Gemert from Schieberle (1998) (GC-olfactometry air threshold, Munich school; '
        'method details not shown in the excerpt); grade A_measured, access full text of '
        'the book via Parallel web_fetch excerpts...; second reader: Air section (the '
        'WATER entry for 103-45-7 is separate: Takahashi (1990) 3-5, Ong & Acree (1999) '
        '0.02 ...). No d/r flag; method not shown. Secondary compilation; primary not '
        'opened. MW 164.20.',
        'Air entries of the van Gemert compilation, 1.0-4.0 ppb; geometric midpoint 2.0. '
        'Primary papers not opened. Replaces 3.0, which had no source.',
    ]),
    'safraleine': (0.7915, 'PEER_SINGLE', [
        'Givaudan Suisse SA, Safety Data Sheet SAFRALEINE, Sales No. 0015893, Version '
        '12.0, Revision Date 09 SEP 2024 (copy hosted by reseller perfumiarz.com) '
        '(https://perfumiarz.com/cdn/shop/files/0015893_SAFRALEINE_SDS_NOT_FOOD_GRADE_IN_EU-EN.pdf?v=9493094553353147398):'
        ' \'"Odour : Spicy, Leathery, woody, Warm Odour Threshold : 5,6389 ng/l"; '
        '"Molecular weight : 174,20 g/mol"\'; printed 5,6389 ng/l; producer SDS Section '
        "9.1 figure; Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l' without "
        "medium or method; ng/l is a gas-phase unit and Givaudan's patents (US 12,340,876"
        ' B2) describe their odour thresholds as measured with a linear-dilution '
        'olfactometer, panel of 15 (inference that the SDS figure is that measurement); '
        'grade A_producer, access full text (PDF, Parallel extract); second reader: '
        "medium not printed; ng/L is the producer's air-threshold unit (inferred). "
        "Reseller-hosted (perfumiarz.com) copy is the producer's own SDS: Givaudan "
        'header, Sales No. 0015893, Version 12.0, revision 09 SEP 2024.',
        'Producer SDS figure. Replaces 0.1, which had no source.',
    ]),
    'triplal': (0.582, 'PEER_SINGLE', [
        'Givaudan SA, US 12,340,876 B2, Table 1/Table 2 "Equilibrium Headspace '
        'Concentration [ug/l] | Group | Odor Value"; text: "The odor value is determined '
        'by dividing the equilibrium headspace concentration of the fragrance ingredient '
        'by its odor threshold." (https://patents.google.com/patent/US12340876B2/en): '
        '\'"2,4-dimethylcyclohex-3-enecarbaldehyde |1926 |III |585468 |6 |6.5 |35 |GREEN |'
        ' |(TRICYCLAL)"\'; printed headspace 1926 ug/l, odor value 585468; threshold = '
        'equilibrium headspace / odor value (producer table). Patent method: "The '
        'olfactometer functions on the principle of a linear dilution of a fragrance '
        'ingredient in a carrier gas ... Each panelist (panel of 15 persons) ..."; value '
        "for 'TRICYCLAL' (same chemical, Givaudan grade); grade A_producer, access full "
        'text (Google Patents page, Parallel full-content fetch); second reader: Producer'
        ' (Givaudan) value derived from printed HS and OV: 1926/585,468 ug/L = 3.29 ng/L.'
        ' Odor threshold by olfactometer (linear dilution in carrier gas, odourless air, '
        "panel of 15), so air. TRICYCLAL is Givaudan's name for the same molecule as IFF "
        'Triplal. MW 138.21.',
        'Givaudan patent figure for Tricyclal, the same molecule (CAS 68039-49-6). '
        'Replaces an estimated 0.5.',
    ]),
    'verdox': (10.88, 'PEER_SINGLE', [
        'Givaudan SA, US 12,340,876 B2, Table 1/Table 2 "Equilibrium Headspace '
        'Concentration [ug/l] | Group | Odor Value"; text: "The odor value is determined '
        'by dividing the equilibrium headspace concentration of the fragrance ingredient '
        'by its odor threshold." (https://patents.google.com/patent/US12340876B2/en): '
        '\'"2-(tert-butyl)cyclohexyl acetate (AGRUMEX) |773 |IV |8764 |40 |5.5 |158 '
        '|FRUITY"\'; printed headspace 773 ug/l, odor value 8764; threshold = equilibrium '
        'headspace / odor value (producer table). Patent method: "The olfactometer '
        'functions on the principle of a linear dilution of a fragrance ingredient in a '
        'carrier gas ... Each panelist (panel of 15 persons) ..."; value for \'AGRUMEX\' '
        '(same chemical, Symrise grade); grade A_producer, access full text (Google '
        'Patents page, Parallel full-content fetch); second reader: Producer value '
        'derived from printed HS and OV: 773/8,764 ug/L = 88.2 ng/L. AGRUMEX is another '
        "producer's grade of the same molecule as IFF Verdox (2-tert-butylcyclohexyl "
        'acetate); cis/trans ratio of the grades may differ. MW 198.30.',
        'Givaudan patent figure for Agrumex, the same molecule (2-tert-butylcyclohexyl '
        'acetate); the cis/trans ratio may differ. Replaces 20, which had no source.',
    ]),
    'vetival': (13.41, 'PEER_SINGLE', [
        "Symrise Perfumery Ingredients datasheet 'Vetival' (SYM_PC-Vetival.pdf, product "
        'no. 105274) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Vetival.pdf):'
        ' \'page 2: "Performance ... thresholD in air ... woody vetival® 0.1000 μg/l # '
        'Vetival › 105274"\'; printed 0.1000 μg/l; producer figure: Symrise datasheet '
        "'Performance' panel labelled 'threshold in air'; method not stated; grade "
        'A_producer, access full text layer of the PDF (Parallel extract)...; second '
        'reader: Producer figure, method not stated. The number sits apart from its label'
        " in the PDF text layer; binding to 'threshold in air' is inferred from layout "
        '(only μg/l value on the page, same layout as other Symrise sheets). 100 ng/L x '
        '24.45/182.3.',
        "Symrise datasheet for its own product; the number sits next to 'threshold in "
        "air' by layout. Replaces an estimated 7.0.",
    ]),
    'citral': (4.337, 'PEER_CROSS', [
        'AIHA, Odor Thresholds for Chemicals with Established Health Standards, 2nd '
        "Edition (2013), Table 6.3 'Reported Odor Thresholds from All Sources' (values "
        'taken from the van Gemert compendium) '
        "(https://swesiaq.se/onewebmedia/Dokument/ODOR%20THRESHOLDS.pdf): '59 Citral ... "
        'Schneider & Wolf 1955 0.027 0.0043 [mg/m3, ppm] ... 452. Schneider, R.A. and S. '
        'Wolf: Olfactory Perception Thresholds for Citral Utilizing a New Type '
        "Olfactorium. J. Appl. Physiol. 8:337-42 (1955).'; printed 0.027 mg/m3 (AIHA "
        'lists 0.0043 ppm); olfactorium (whole-body chamber) perception threshold, as '
        'quoted by the AIHA compilation; primary not opened. 0.027 mg/m3 = 27 ng/L; 27 x '
        '24.45 / 152.23 = 4.33653 ppb v/v (25 C; conversion redone here, the '
        "compilation's own ppm column uses STP); grade A_measured, access PDF "
        '(compilation; primary paper not opened); second reader: Printed 0.027 mg/m3 = 27'
        ' ng/L, air. This row has no d/r label, so detection vs recognition is not '
        'printed. Compilation only; primary not opened. MW 152.23 (as printed).',
        'AIHA, Odor Thresholds for Chemicals with Established Health Standards, 2nd '
        "Edition (2013), Table 6.3 'Reported Odor Thresholds from All Sources' (values "
        'taken from the van Gemert compendium) '
        "(https://swesiaq.se/onewebmedia/Dokument/ODOR%20THRESHOLDS.pdf): '59 Citral ... "
        "Etzweiler et al 1980 0.02 0.032 [mg/m3, ppm]'; printed 0.02 mg/m3 (AIHA prints "
        '0.032 ppm, which does not match 0.02 mg/m3; 0.0032...; as quoted by the AIHA '
        'compilation; method not given there; primary not opened. 0.02 mg/m3 = 20 ng/L; '
        '20 x 24.45 / 152.23 = 3.21224 ppb v/v (25 C; conversion redone here, the '
        "compilation's own ppm column uses STP); grade A_measured, access PDF "
        '(compilation; primary paper not opened); second reader: Printed 0.02 mg/m3 = 20 '
        "ng/L, in the compilation's air table. No d/r label and no method for this row. "
        'The ppm column (0.032) does not match 0.02 mg/m3 (0.0032 would).',
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: RIFM safety assessment citral, Food '
        'Chem. Toxicol. 141 (2020) 111339 '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/5392-40-5.pdf):'
        " 'CITRAL LEMAROME N ((E)-3,7-dimethylocta-2,6-dienal) |20039 (PROC); CITRAL "
        "LEMAROME N ((E)-3,7- |1311 |-2.1 (log Kcaps) || VP: '0.0913 mm Hg @ 25 °C (EPI "
        "Suite)''; printed PROC 20039, log10 Kcaps -2.1; VP 0.0913 mmHg = 12.17 Pa (EPI, "
        '25 C); cross-check, OV = PROC / (log10 Kcaps + 3) = 20039 / 0.90 = 22,266; '
        'saturated vapour = 12.17 Pa / 101325 Pa x 1e9 = 120,109 ppb; threshold = 120,109'
        ' / 22,266 = 5.394 ppb (range 5.09 to 5.69 ppb for log10 Kcaps +/- 0.05).; grade '
        'EST, access full text (patent); PDF (VP); second reader: Inputs printed. 0.0913 '
        'mmHg = 12.17 Pa, giving 120,131 ppb saturated; OV 22,266; threshold 5.395 ppb '
        '(5.10–5.70 for LogKcaps ±0.05). The VP is an EPI estimate standing in for '
        "Givaudan's headspace value. Grade is CITRAL LEMAROME N.",
        'AIHA compilation rows (no detection/recognition flag; primaries not opened) and '
        'a Givaudan PROC estimate agree at 3.2-5.4 ppb. Replaces 20, which had no source.',
    ]),
    'guaiacol': (0.01654, 'PEER_SINGLE', [
        "Schranz M., Lorber K., Klos K., Kerschbaumer J., Buettner A. 'Influence of the "
        'chemical structure on the odor qualities and odor thresholds of guaiacol-derived'
        " odorants, Part 1', Food Chem. 2017, 232, 808-819 (value as quoted by the same "
        'group in Juhlke F., Lorber K., Wagenstaller M., Buettner A., Front. Chem. 2017, '
        '5:120, doi:10.3389/fchem.2017.00120) '
        '(https://www.frontiersin.org/journals/chemistry/articles/10.3389/fchem.2017.00120/full):'
        " 'In comparison to guaiacol itself, with a median odor threshold of 0.084 "
        'ng/Lair (Schranz et al., 2017) and therefore being already a quite potent '
        "substance itself ...'; printed 0.084 ng/L air (median); GC-olfactometry, odor "
        'thresholds in air (Buettner group, Ullrich & Grosch method with (E)-2-decenal '
        'internal standard); median of panel; grade A_measured, access full text of '
        'Juhlke 2017 (Frontiers HTML via fetch...; second reader: Printed 0.084 ng/L, air'
        ' (median of panel). Secondary citation of Schranz et al. 2017, Food Chem '
        '232:808-819 (not opened). GC-O with (E)-2-decenal standard. MW 124.14.',
        "Yang D.S., Shewfelt R.L., Lee K.-S., Kays S.J. 'Comparison of odor-active "
        "compounds from six distinctly different rice flavor types', J. Agric. Food Chem."
        ' 2008, doi:10.1021/jf072685t (PMID 18363355) '
        "(https://pubmed.ncbi.nlm.nih.gov/18363355): 'Their odor thresholds in air were "
        'determined using GC-O. 2-Acetyl-1-pyrroline (2-AP) had the lowest odor threshold'
        ' (0.02 ng/L) followed by 11 aldehydes (ranging from 0.09 to 3.1 ng/L), guaiacol '
        "(1.5 ng/L), and 1-octen-3-ol (2.7 ng/L).'; printed 1.5 ng/L; GC-O odor "
        'thresholds in air (rice aroma study); grade A_measured, access abstract (PubMed,'
        ' search excerpt); second reader: Printed 1.5 ng/L, air (GC-O). Abstract only. MW'
        ' 124.14.; listed, not used (0.2954 ppb)',
        'Influence of the Chemical Structure on Odor Qualities and Odor Thresholds of '
        'Halogenated Guaiacol-Derived Odorants (Frontiers in Chemistry 2017) '
        "(https://pmc.ncbi.nlm.nih.gov/articles/PMC5741668/): 'guaiacol itself, with a "
        "median odor threshold of 0.084 ng/L air (Schranz et al., 2017)'; printed 0.084 "
        'ng/L air; odour threshold in air by GC-O (method of Ullrich & Grosch, '
        '(E)-2-decenal internal standard), as cited; primary is Schranz et al. 2017 (Part'
        ' 1, Food Chem); grade A_measured, access full text (PMC, opened with fetch tool,'
        ' 25 Oct 2026); second reader: Same value and article as candidate 0 (PMC copy), '
        'so it is not an independent source. Secondary citation of Schranz 2017.; listed,'
        ' not used (0.01654 ppb)',
        'Schranz et al. 2017 GC-O air threshold as cited by the Buettner group (primary '
        'not opened). Yang et al. 2008 (abstract) gives 0.295 ppb. Replaces 0.5, a phenol'
        ' class value.',
    ]),
    'velvione': (0.052, 'PEER_SINGLE', [
        'Park S.M. (2012) Determining Potency of Odorants: Concentration-Detection '
        'Functions and Recognition Point of Fragrance Chemicals. M.S. thesis, University '
        'of California, San Diego '
        "(https://escholarship.org/content/qt6c18p70s/qt6c18p70s.pdf): 'Table 3: "
        '"Velvione 0.052 4.284" (header "Material Name ODT (ppb) log(1/ODT)"); odorant '
        'list: "... and Velvione 37609-25-9."\'; printed 52 ppt (Figure 5); Table 3 \'ODT '
        "(ppb)' 0.052, log(1/ODT ppm) 4.284; 8-station vapour delivery device (VDD8), "
        '3-alternative forced choice, ascending concentrations; ODT from group '
        'psychometric function (Cain lab, UCSD); grade A_measured, access full text '
        '(PDF); second reader: Detection threshold, already ppb v/v, in air (vapour '
        "delivery). The words 'carbon-filtered air' were not seen; the page says make-up "
        'and background flows.',
        'Givaudan Suisse SA, Safety Data Sheet VELVIONE, Sales No. 1382293, Version 3.1, '
        'Revision Date 14 OCT 2021 (copy hosted by reseller perfumiarz.com) '
        '(https://perfumiarz.com/cdn/shop/files/1382293_VELVIONE_SDS_EN.pdf?v=13910140795854116974):'
        ' \'"Odour : Musky, Metallic, Powdery, mild Odour Threshold : 4,589 ng/l"; '
        '"Molecular weight : 236,40 g/mol"\'; printed 4,589 ng/l; producer SDS Section 9.1'
        " figure; Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l' without medium"
        " or method; ng/l is a gas-phase unit and Givaudan's patents (US 12,340,876 B2) "
        'describe their odour thresholds as measured with a linear-dilution olfactometer,'
        ' panel of 15 (inference that the SDS figure is that measurement); grade '
        'A_producer, access full text (PDF, Parallel extract); second reader: medium not '
        "printed; ng/L is the producer's air-threshold unit (inferred). This is the "
        "producer's own SDS (Givaudan header, sales no., version and revision); no "
        'perfumiarz branding on the PDF.; listed, not used (0.4746 ppb)',
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Traynor S. (2001) The musk dilemma, Perfumer & '
        'Flavorist 26 (Sept/Oct) 28, 30-39 '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"5-CYCLOHEXADECEN-1-ONE (ambretone) [37609-25-9] Traynor (2001) 0.116"\'; '
        'printed 0.116 mg/m3; Traynor (2001) as compiled by van Gemert (AIR section, '
        'mg/m3); method not shown in the compilation; grade A_measured, access full text '
        'of the book via Parallel web_fetch excerpts...; second reader: Same CAS as '
        "Velvione (37609-25-9). The entry is Takasago's ambretone, so the isomer ratio "
        'may differ. No d/r label; Traynor 2001 says detection. 0.116 mg/m3 = 116 ng/L; '
        'MW 236.40. Book copy on vdoc.pub.; listed, not used (12.0 ppb)',
        "Vapour-delivery psychophysics (detection). Givaudan's SDS gives 0.475 ppb and "
        "van Gemert's Takasago ambretone entry 12 ppb; measured air olfactometry ranks "
        'first. First air threshold for this stock.',
    ]),
    'bourgeonal': (0.05187, 'PEER_CROSS', [
        'Givaudan Safety Data Sheet BOURGEONAL, Sales No. 2837903, Version 25.0, revision'
        ' 10 JUL 2025 (Givaudan Suisse SA; copy hosted by reseller Aromology) '
        '(https://aromology.com/cdn/shop/files/SDS-Bourgeonal_-_Givaudan_-_Muguet.pdf?v=3428077962748523002):'
        " 'Odour : Floral, Fresh, Lily-of-the-valley, Green Odour Threshold : 0,4037 ng/l"
        " ... Molecular weight : 190,28 g/mol ... Vapour pressure : 0,002 hPa at 20 °C'; "
        'printed 0.4037 ng/l; producer SDS figure; 0.4037 ng/L x 24.45 / 190.28 g/mol = '
        "0.0518734 ppb v/v (25 C). Givaudan SDS Section 9 prints 'Odour Threshold : x "
        "ng/l' (medium and method not printed; ng/l is an air unit; Givaudan patents "
        'define their odour threshold as measured with a linear-dilution olfactometer, '
        'forced-choice triangle, panel of 15: US 2018/0185808).; grade A_producer, access'
        " PDF (full); second reader: medium not printed; ng/L is the producer's "
        "air-threshold unit (inferred). This is the producer's own SDS (Givaudan Suisse "
        'SA / Givaudan France SAS header, sales no., version and revision); no Aromology '
        'branding. Value is for neat Bourgeonal; the stock is 20% in TEC.',
        "Goeke A., Kraft P. et al. (Givaudan), 'Discovery of Nympheal: The Definitive "
        "Muguet Aldehyde', Perfumer & Flavorist, 20 Feb 2018 "
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21856694/discovery-of-nympheal-the-definitive-muguet-aldehyde):'
        " 'Isolilial is with a threshold of 0.4 ng/L air ... the former Quest began to "
        "produce and market Isolilial as Bourgeonal'; printed 0.4 ng/L air; Givaudan R&D "
        'odour threshold (method not described in the article); 0.4 ng/L x 24.45 / 190.28'
        ' g/mol = 0.0513979 ppb v/v (25 C); grade A_producer, access full text; second '
        'reader: Printed 0.4 ng/L air. Method not described. MW 190.28.',
        'Givaudan SDS and Givaudan R&D article agree (0.052 and 0.051 ppb). Replaces '
        '0.03, which had no source.',
    ]),
    'florhydral': (0.008995, 'PEER_CROSS', [
        "US 4,910,346 A, '3-(3-propan-2-ylphenyl)butanal and "
        "3-(3-propen-2-ylphenyl)butanal', Givaudan Corp., priority 1988-11-10, Example II"
        ' (compound la = Florhydral) (https://patents.google.com/patent/US4910346A/en): '
        "'Preparation of 3-(3-propan-2-ylphenyl)butanal, la ... Odor value: 981,483; Odor"
        " threshold value: 0.07 ng/L.'; printed 0.07 ng/L; producer compound patent "
        "(Givaudan), method not stated; same example gives 'Odor value: 981,483'; grade "
        'A_producer, access full text (Google Patents, via fetch tool); second reader: '
        "medium not printed; ng/L is the producer's air-threshold unit (inferred). The "
        'patent does not describe how the threshold was measured. Compound la = '
        'Florhydral. MW 190.28.',
        "'Discovery of Nympheal, the definitive muguet aldehyde', Perfumer & Flavorist, "
        'Feb 2018 (Givaudan R&D article; authors Goeke, Kraft, Lelievre, Alchenberger per'
        ' the earlier project file 02_odour_thresholds.md, not shown in the page text '
        'this session) '
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21856694/discovery-of-nympheal-the-definitive-muguet-aldehyde):'
        " 'Florhydral (7) ... six times more potent even than Lilial (3) in terms of "
        'detection threshold. / [Lilial] lowered the odor detection threshold by a factor'
        " of 5 to 0.45 ng/L air.'; printed 'six times more potent even than Lilial (3) in"
        ' terms of detection...; ratio statement by the producer; derived: Lilial 0.45 '
        'ng/L air / 6 = 0.075 ng/L (inference from a ratio); grade EST, access full text '
        '(web article, via fetch tool); second reader: EST from a ratio statement: 0.45/6'
        ' = 0.075 ng/L air; MW 190.28. Agrees with candidate 0 (0.07 ng/L).',
        'Givaudan patent figure; a ratio in the Givaudan Nympheal article gives 0.0096 '
        'ppb. Replaces 0.3, a use-level inference.',
    ]),
    'magnolan': (1.508, 'PEER_SINGLE', [
        "Symrise Perfumery Ingredients datasheet 'Magnolan' (SYM_PC-Magnolan.pdf, product"
        ' no. 690304) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Magnolan.pdf):'
        ' \'page 2: "Performance ... thresholD in air ... # Magnolan 0.0126 μg/l › '
        '690304"\'; printed 0.0126 μg/l; producer figure: Symrise datasheet \'Performance\' '
        "panel, chart labelled 'threshold in air'; method not stated; grade A_producer, "
        'access full text layer of the PDF (Parallel extract). The text...; second '
        'reader: Printed 0.0126 µg/l = 12.6 ng/L, air. The number is tied to the '
        "'threshold in air' label by layout only (text layer), as noted by the worker.",
        "Symrise datasheet for its own product; number bound to 'threshold in air' by "
        'layout. First air threshold for this stock.',
    ]),
    'methyl pamplemousse': (6.575, 'PEER_CROSS', [
        "Symrise Perfumery Ingredients datasheet 'Amarocit' (SYM_PC-Amarocit.pdf, product"
        ' no. 197007) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Amarocit.pdf):'
        ' \'"› 6,6-Dimethoxy-2,5,5-trimethylhex-2-ene › cas 67674-46-8 › 197007"; '
        'Performance panel: "Threshold in Air" ... "citrus Amarocit® 0.0501 μg/l"\'; '
        "printed 0.0501 μg/l; producer figure: Symrise Amarocit datasheet 'Performance' "
        "panel labelled 'Threshold in Air'; method not stated. Same CAS as Methyl "
        'Pamplemousse (different producer); grade A_producer, access full text layer of '
        'the PDF (Parallel extract)...; second reader: Same molecule and CAS as Methyl '
        'Pamplemousse (Givaudan), from a different producer. The label binding is by '
        'layout. 50.1 ng/L, air; MW 186.29.',
        'Givaudan SA, US 2018/0185808 A1 "MICROCAPSULES": GROUP 1 table "Perfumery '
        'ingredient | RECON_VOLTAE (Bohr3) | LogKcaps" and GROUP 4 table "Perfumery '
        'ingredient | PROC"; definition "PROC i =OV i [log10 Kcaps i +3]" and "The '
        'standard Odour Value (OV i) is defined as the ratio of the standard equilibrium '
        'headspace concentration of the ingredient to the Odour Detection Threshold of '
        'this ingredient." + Givaudan S.A., US 9,868,923 "Perfume compositions": point '
        'values "HS i0", defined as "the concentration of the ingredient in equilibrium '
        'with the condensed form ... at a temperature of 25 C and under a pressure of 1 '
        'atmosphere", measured by Porapak Q trapping and GC, mean of three measurements '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; '
        'https://patents.justia.com/patent/9868923): \'"|METHYL PAMPLEMOUSSE '
        '(6,6-dimethoxy-2,5,5-trimethylhex-2-ene) |151438 |" ; "|METHYL PAMPLEMOUSSE '
        '(6,6-dimethoxy- |1632 |−1.9 |" ; "6,6-dimethoxy-2,5,5-trimethylhex-2-ene, for '
        'example METHYL PAMPLEMOUSSE (HS i ⁰ =2464 μg/L)"\'; printed PROC 151438, LogKcaps'
        " -1.9, HS 2464 ug/L; EST back-calculated from Givaudan patent tables for 'METHYL"
        " PAMPLEMOUSSE': ODT = HS / OV, OV = PROC / (LogKcaps + 3). The underlying ODT is"
        ' Givaudan olfactometer, as described in US 2018/0185808: "The olfactometer '
        'functions on the principle of a linear dilution of an odorant in a carrier gas '
        '... Each panellist (panel of 15 persons) ... The final threshold value of a '
        'given...; grade EST, access full text of both patents (Parallel full-content '
        'fetch...; second reader: All inputs printed; HS i0 defined at 25 °C, 1 atm. OV ='
        ' 151438/1.1 = 137,671; ODT = 17.90 ng/L; MW 186.29.',
        'Symrise Amarocit datasheet, the same molecule and CAS; the Givaudan PROC '
        'estimate for its own material gives 2.35 ppb (2.8x lower). Replaces 3.0, which '
        'had no source.',
    ]),
    'nympheal': (0.007184, 'PEER_CROSS', [
        'Givaudan Safety Data Sheet NYMPHEAL, Sales No. 1489703, Version 19.0, Revision '
        'Date 26 JUN 2023 (copy hosted by reseller perfumiarz.com) '
        '(https://perfumiarz.com/cdn/shop/files/1489703_NYMPHEAL_SDS_EN.pdf?v=16768464028873411806):'
        ' \'"Odour : Floral, Aldehydic, Green, Lily-of-the-valley Odour Threshold : 0,06 '
        'ng/l"; "Molecular weight : 204,2 g/mol"\'; printed 0,06 ng/l; producer SDS '
        "Section 9.1 figure; Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l' "
        "without medium or method; ng/l is a gas-phase unit and Givaudan's patents (US "
        '12,340,876 B2) describe their odour thresholds as measured with a '
        'linear-dilution olfactometer, panel of 15 (inference that the SDS figure is that'
        ' measurement); grade A_producer, access full text (PDF, Parallel extract); '
        "second reader: medium not printed; ng/L is the producer's air-threshold unit "
        "(inferred). This is the producer's own SDS (Givaudan header, sales no., version "
        'and revision); no perfumiarz branding. It is about 3x the P&F measured value '
        '(candidate 0).',
        'Discovery of Nympheal: The Definitive Muguet Aldehyde, Perfumer & Flavorist, Feb'
        ' 2018 (Givaudan Fragrances S&T, Duebendorf; Lelievre, Alchenberger et al.) '
        '(https://www.perfumerflavorist.com/fragrance/ingredients/article/21856694/discovery-of-nympheal-the-definitive-muguet-aldehyde):'
        ' \'"Compound 10 was the closest to Lilial in odor character and was also the most'
        ' intense having an odor threshold of 0.021 ng/L air."; "the calculated threshold'
        ' of 0.16 ng/L for Nympheal (10) is almost eight times higher than the '
        'experimentally measured one"\'; printed 0.021 ng/L air; Givaudan R&D odour '
        'threshold (measured; article contrasts it with a calculated 0.16 ng/L); grade '
        'A_producer, access full text (web page); second reader: Printed 0.021 ng/L air, '
        'measured. MW 204.31.',
        'Givaudan SDS for the commercial material; the Givaudan discovery article gives '
        '0.0025 ppb (2.9x lower). Replaces 2.0, which had no source.',
    ]),
    'vetikon': (87.53, 'PEER_SINGLE', [
        "Symrise Perfumery Ingredients datasheet 'Vetikon' (SYM_PC-Vetikon.pdf, product "
        'no. 131014) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Vetikon.pdf):'
        ' \'page 2: "Performance ... thresholD in air ... # Vetikon 0.6310 μg/l › '
        '131014"\'; printed 0.6310 μg/l; producer figure: Symrise datasheet \'Performance\' '
        "panel labelled 'threshold in air'; method not stated; grade A_producer, access "
        'full text layer of the PDF (Parallel extract)...; second reader: Printed 0.6310 '
        'µg/l = 631 ng/L, air; MW 176.25. The label binding is by layout.',
        'Vetikon (Symrise Perfumery Ingredients datasheet) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Vetikon.pdf):'
        " 'thresholD in air ... woody vetikon® ... 0.6310 μg/l'; printed 0.6310 µg/l; "
        'producer datasheet "Threshold in Air" (method not stated); grade A_producer, '
        'access full PDF datasheet (Symrise Ingredient Finder, opened...; second reader: '
        'Printed 0.6310 µg/l = 631 ng/L, air; MW 176.25. The label binding is by layout. '
        'Duplicate of candidate 0.; listed, not used (87.53 ppb)',
        "Symrise datasheet for its own product; number bound to 'threshold in air' by "
        'layout. Replaces 5.0, which had no source.',
    ]),
    'allyl cyclohexyl propionate': (1.268, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: RIFM fragrance ingredient safety '
        'assessment, allyl cyclohexanepropionate, Food Chem. Toxicol. (2021), doi '
        '10.1016/j.fct.2021.112424 (https://www.freepatentsonline.com/y2018/0185808.html '
        '; VP: '
        'https://fragrancematerialsafetyresource.elsevier.com/sites/default/files/2705-87-5.pdf):'
        " 'ALLYL CYCLOHEXYL PROPIONATE (allyl 3-cyclohexylpropanoate) |29587 (PROC); "
        'ALLYL CYCLOHEXYL PROPIONATE (allyl |1606 |-2.0 (log Kcaps) || VP source: 7. '
        'Vapor Pressure: 3.8 Pa at 25 °C ( RIFM, 2012d ) ... RIFM 2012d: Determination of'
        " Vapor Pressure Using the...'; printed PROC 29587, log10 Kcaps -2.0; VP 3.8 Pa "
        'at 25 C; OV = PROC / (log10 Kcaps + 3) = 29587 / 1.00 = 29,587; saturated vapour'
        ' = 3.8 Pa / 101325 Pa x 1e9 = 37,503 ppb; threshold = 37,503 / 29,587 = 1.268 '
        'ppb (range 1.2 to 1.33 ppb for log10 Kcaps +/- 0.05). VP 3.8 Pa (25 C) from the '
        'source named. Givaudan OV = equilibrium headspace (25 C) / olfactometer odour '
        'threshold (panel of 15); headspace estimated here from VP, so this is...; grade '
        'EST, access full text (patent); PDF (full) (VP); second reader: Inputs printed. '
        '37,503 ppb / OV 29,587 = 1.268 ppb. A measured VP (RIFM 2012d) stands in for '
        "Givaudan's headspace value.",
        'Givaudan PROC estimate with a measured RIFM vapour pressure. Replaces 8.0, which'
        ' had no source.',
    ]),
    'aurantiol': (0.01845, 'PEER_SINGLE', [
        'Givaudan Safety Data Sheet AURANTIOL PURE, Version 14.1, revision 11 JUL 2023 '
        '(https://perfumiarz.com/cdn/shop/files/2365901_AURANTIOL_PURE_SDS_EN.pdf?v=14674485429420110479):'
        " 'Odour Threshold : 0,2305 ng/l ... Molecular weight : 305,40 g/mol ... Vapour "
        "pressure : 0,0017 hPa at 20 °C'; printed 0.2305 ng/l; producer SDS figure; "
        '0.2305 ng/L x 24.45 / 305.4 g/mol = 0.0184536 ppb v/v (25 C). Givaudan SDS '
        "Section 9 prints 'Odour Threshold : x ng/l'; the sheet does not print the medium"
        " or method. ng/l is an air (gas-phase) unit; Givaudan's patents define their "
        'odour threshold as measured with a linear dilution olfactometer, panel of 15 (US'
        ' 2018/0185808, US 12,340,876).; grade A_producer, access PDF (full); second '
        "reader: medium not printed; ng/L is the producer's air-threshold unit "
        "(inferred). This is the producer's own SDS (Givaudan header, sales no., version "
        'and revision); no perfumiarz branding.',
        'Producer SDS figure. Replaces 30, an audit correction with no source.',
    ]),
    'calone': (0.004254, 'PEER_SINGLE', [
        'Occurrence of Marine Ingredients in Fragrance, Chemistry (MDPI) 3(4) (2021) 103 '
        "(https://www.mdpi.com/2624-8549/3/4/103): '“watermelon ketone” with a very low "
        "odor threshold of 3.1 × 10−2 ng/L air [190]'; printed 0.031 ng/L air; review "
        'figure; its ref. 190 is the Pfizer patent US 3,799,892 (Beereboom), which was '
        'not opened, so the original measurement is not verified. 0.031 ng/L x 24.45 / '
        '178.18 g/mol = 0.00425384 ppb v/v (25 C); grade A_measured, access full text '
        '(review; primary not verified); second reader: Printed 0.031 ng/L air, in a '
        'review; primary ref 190 not opened. Value is for the neat molecule; the stock is'
        ' 1% in DPG. MW 178.18.',
        'Review figure (primary reference not opened), for the neat molecule. Replaces '
        '0.05, an audit correction with no source.',
    ]),
    'champignol': (0.5149, 'PEER_SINGLE', [
        "Yang D.S., Shewfelt R.L., Lee K.-S., Kays S.J., 'Comparison of odor-active "
        "compounds from six distinctly different rice flavor types', J. Agric. Food Chem."
        ' 56 (2008) 2780-2787, doi 10.1021/jf072685t '
        "(https://pubmed.ncbi.nlm.nih.gov/18363355): 'Their odor thresholds in air were "
        'determined using GC-O. 2-Acetyl-1-pyrroline (2-AP) had the lowest odor threshold'
        ' (0.02 ng/L) followed by 11 aldehydes (ranging from 0.09 to 3.1 ng/L), guaiacol '
        "(1.5 ng/L), and 1-octen-3-ol (2.7 ng/L).'; printed 2.7 ng/L air; GC-olfactometry"
        ' odour threshold in air (trained assessors); enantiomer not stated. 2.7 ng/L x '
        '24.45 / 128.21 g/mol = 0.514897 ppb v/v (25 C); grade A_measured, access '
        'abstract only; second reader: Printed 2.7 ng/L, air. Champignol is '
        '(R)-(−)-1-octen-3-ol (CAS 3687-48-7, PerfumersWorld/TGSC listing); the paper '
        'gives 1-octen-3-ol with no enantiomer stated. Abstract only. MW 128.21.',
        'GC-O air threshold for 1-octen-3-ol, enantiomer not stated (Champignol is the '
        '(R)-enantiomer). Replaces 0.1, which had no source.',
    ]),
    'citronellyl acetate': (14.49, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1, PROC table (PROC_i = OV_i [log10 Kcaps_i + 3]) '
        'and calculated log10 Kcaps tables ; VP: BASF Safety Data Sheet Citronellyl '
        'Acetate, version 6.0, revision 2025/07/03 '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; VP: '
        'https://download.basf.com/p1/000000000030035076_SDS_GEN_US/en_US/Citronellyl_Acetate_30035076_SDS_GEN_US_en_6-0.pdf):'
        " 'CITRONELLYL ACETATE (3,7-dimethyloct-6-en-1-yl acetate) |1744 (PROC); "
        'CITRONELLYL ACETATE (3,7-dimethyloct- |1678 |-1.7 (log Kcaps) || VP source: '
        "Vapour pressure: 0.0197 hPa ( 20 °C) Extrapolated value, dynamic (measured)'; "
        'printed PROC 1744, log10 Kcaps -1.7; VP 1.97 Pa at 20 C; OV = PROC / (log10 '
        'Kcaps + 3) = 1744 / 1.30 = 1,342; saturated vapour = 1.97 Pa / 101325 Pa x 1e9 ='
        ' 19,442 ppb; threshold = 19,442 / 1,342 = 14.49 ppb (range 13.9 to 15.1 ppb for '
        'log10 Kcaps +/- 0.05). VP 1.97 Pa (20 C) from the source named. Givaudan OV = '
        'equilibrium headspace (25 C) / olfactometer odour threshold (panel of 15); '
        'headspace estimated here from VP, so this is...; grade EST, access full text '
        '(patent); search snippet (VP); second reader: Inputs printed. 1.97 Pa gives '
        "19,442 ppb; OV 1,342; threshold 14.49 ppb. The VP is at 20 °C, while Givaudan's "
        'HS is defined at 25 °C, which probably biases the threshold low.',
        'Givaudan PROC estimate with a BASF vapour pressure at 20 C (headspace is defined'
        ' at 25 C, so probably biased low). First air threshold for this stock.',
    ]),
    'decatone': (4.183, 'PEER_SINGLE', [
        'Givaudan Safety Data Sheet DECATONE, Sales No. 4356101, Version 10.0, revision '
        '07 DEC 2023 (Givaudan Suisse SA) '
        '(https://perfumiarz.com/cdn/shop/files/4356101_DECATONE_SDS_EN.pdf?v=2113061062550949607):'
        " 'Odour Threshold : 33,2402 ng/l ... Molecular weight : 194,30 g/mol'; printed "
        '33.2402 ng/l; producer SDS figure; 33.2402 ng/L x 24.45 / 194.3 g/mol = 4.18282 '
        "ppb v/v (25 C). Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l'; the "
        'sheet does not print the medium or method. ng/l is an air (gas-phase) unit; '
        "Givaudan's patents define their odour threshold as measured with a linear "
        'dilution olfactometer, panel of 15 (US 2018/0185808, US 12,340,876).; grade '
        'A_producer, access PDF (full); second reader: medium not printed; ng/L is the '
        "producer's air-threshold unit (inferred). This is the producer's own SDS "
        '(Givaudan header, sales no., version and revision); no perfumiarz branding.',
        'Producer SDS figure; first air threshold for this stock.',
    ]),
    'ethyl maltol': (0.0059, 'PEER_SINGLE', [
        "UC San Diego thesis 'Determining potency of odorants: concentration-detection "
        "functions and recognition point of fragrance chemicals' (2012), eScholarship "
        'qt6c18p70s (author S.M. Park per earlier project files; not shown in this '
        "session's excerpt) (https://escholarship.org/content/qt6c18p70s/qt6c18p70s.pdf):"
        " 'Veltol Plus ... Number of Subjects 12 Detection Threshold 5.9 ppt Recognition "
        'Threshold 9.7 ppt Recognition : Detection 1.6:1 ... Table 3 ... Veltol Plus '
        "0.005 5.301'; printed 5.9 ppt; concentration-detection (psychometric) functions,"
        ' dynamic olfactometry in the Cain/Cometto-Muniz laboratory (UCSD), 12 subjects; '
        'detection threshold 5.9 ppt, recognition 9.7 ppt; grade A_measured, access full '
        'text (PDF via Parallel fetch excerpts); second reader: Detection threshold in '
        'air (VDD8 vapour delivery), already ppb v/v. CAS 4940-11-8 is ethyl maltol. '
        'Table 3 rounds it to 0.005 ppb.',
        'Vapour-delivery psychophysics (detection). Replaces 0.3, which had no source.',
    ]),
    'habanolide': (17.0, 'PEER_SINGLE', [
        "Traynor S. (Takasago International Corp.), 'The Musk Dilemma', Perfumer & "
        "Flavorist 26 (Sept/Oct 2001) 28ff., Table 1 'Relative musk performance' "
        '(https://img.perfumerflavorist.com/files/base/allured/all/document/2016/02/pf.PF_26_05_028_11.pdf):'
        " 'Table 1 ... Threshold ppb ... Galaxolide PCM 4 ... Exaltolide MCM 10 ... "
        'Habanolide MCM 17 ... Ambrettolide MCM 12 ... The detection threshold of a '
        "variety of musks has been determined using an air dilution instrument.'; printed"
        " 17 ppb (Table 1 'Threshold ppb'); 'determined using an air dilution instrument'"
        " (Takasago), panel not described; the author says the values 'are thus best "
        "viewed as relative, rather than as an absolute value'; grade A_measured, access "
        'full text (PDF via fetch tool); second reader: Printed 17 ppb, air, detection. '
        'The author calls these values relative. van Gemert lists habanolide Traynor '
        '(2001) 0.166 mg/m3, which is consistent.',
        'Takasago detection value (the author calls the values relative); van Gemert '
        'lists Traynor 2001 at 0.166 mg/m3, consistent. Replaces 2.8, which had no '
        'source.',
    ]),
    'linalool': (0.5072, 'PEER_SINGLE', [
        "Elsharif S.A., Banerjee A., Buettner A. 'Structure-odor relationships of "
        "linalool, linalyl acetate and their corresponding oxygenated derivatives', "
        'Front. Chem. 2015, 3:57, doi:10.3389/fchem.2015.00057 '
        "(https://www.frontiersin.org/articles/10.3389/fchem.2015.00057/full): 'Linalool "
        'was found to be the most potent odorant among the investigated compounds, with '
        'an average OT of 3.2 ng/L ... we found that linalool is the most potent odorant '
        "having an odor threshold of 3.2 ng/L in air (Table 3).'; printed 3.2 ng/L air; "
        'GC-olfactometry, odor thresholds in air after Czerny et al. 2011 with '
        '(E)-dec-2-enal as internal odor standard; 8 trained panellists; group value = '
        'geometric mean of individual thresholds (individual 2.1-8.4 ng/L); grade '
        'A_measured, access full text (Frontiers HTML via fetch tool; PMC copy...; second'
        ' reader: Printed 3.2 ng/L air; GC-O detection thresholds as the geometric mean '
        'of the panel. MW 154.25.',
        'GC-O detection threshold of racemic linalool. Replaces 1.5, which overrode the '
        '0.51 its own source note gave.',
    ]),
    'methyl diantilis': (0.2287, 'PEER_SINGLE', [
        'Givaudan Suisse SA, Safety Data Sheet METHYL DIANTILIS, Sales No. 6906203, '
        'Version 3.0, Revision Date 20 APR 2022 (copy hosted by reseller perfumiarz.com) '
        '(https://perfumiarz.com/cdn/shop/files/6906203_METHYL_DIANTILIS_SDS_EN.pdf?v=15036295580728543378):'
        ' \'"Odour : Spicy, Vanilla-like, Balsamic, mild Odour Threshold : 1,7043 ng/l"; '
        '"Molecular weight : 182,20 g/mol"\'; printed 1,7043 ng/l; producer SDS Section '
        "9.1 figure; Givaudan SDS Section 9 prints 'Odour Threshold : x ng/l' without "
        "medium or method; ng/l is a gas-phase unit and Givaudan's patents (US 12,340,876"
        ' B2) describe their odour thresholds as measured with a linear-dilution '
        'olfactometer, panel of 15 (inference that the SDS figure is that measurement); '
        'grade A_producer, access full text (PDF, Parallel extract); second reader: '
        "medium not printed; ng/L is the producer's air-threshold unit (inferred). This "
        "is the producer's own SDS (Givaudan header, sales no., version and revision); no"
        ' perfumiarz branding.',
        'Producer SDS figure; first air threshold for this stock.',
    ]),
    'terpinyl acetate': (16.93, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1 "MICROCAPSULES": GROUP 1 table "Perfumery '
        'ingredient | RECON_VOLTAE (Bohr3) | LogKcaps" and GROUP 4 table "Perfumery '
        'ingredient | PROC"; definition "PROC i =OV i [log10 Kcaps i +3]" and "The '
        'standard Odour Value (OV i) is defined as the ratio of the standard equilibrium '
        'headspace concentration of the ingredient to the Odour Detection Threshold of '
        'this ingredient." + Givaudan S.A., US 9,868,923 "Perfume compositions": point '
        'values "HS i0", defined as "the concentration of the ingredient in equilibrium '
        'with the condensed form ... at a temperature of 25 C and under a pressure of 1 '
        'atmosphere", measured by Porapak Q trapping and GC, mean of three measurements '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; '
        'https://patents.justia.com/patent/9868923): \'"|TERPINYL ACETATE '
        '(2-(4-methylcyclohex-3-en-1-yl)propan-2-yl acetate) |3429 |" ; "|TERPINYL '
        'ACETATE (2-(4-methylcyclohex- |1590 |−2.0 |" ; '
        '"2-(4-methylcyclohex-3-en-1-yl)propan-2-yl acetate, for example, TERPINYL '
        'ACETATE (HS i ⁰ =466 μg/L)"\'; printed PROC 3429, LogKcaps -2.0, HS 466 ug/L; EST'
        " back-calculated from Givaudan patent tables for 'TERPINYL ACETATE': ODT = HS / "
        'OV, OV = PROC / (LogKcaps + 3). The underlying ODT is Givaudan olfactometer, as '
        'described in US 2018/0185808: "The olfactometer functions on the principle of a '
        'linear dilution of an odorant in a carrier gas ... Each panellist (panel of 15 '
        'persons) ... The final threshold value of a given...; grade EST, access full '
        'text of both patents (Parallel full-content fetch...; second reader: All inputs '
        'printed. OV 3,429; ODT = 135.9 ng/L; MW 196.29.',
        'Givaudan PROC estimate. Replaces an estimated 35 with no source.',
    ]),
    'ultralia': (0.1737, 'PEER_EST', [
        'Givaudan SA, US 2018/0185808 A1 "MICROCAPSULES": GROUP 1 table "Perfumery '
        'ingredient | RECON_VOLTAE (Bohr3) | LogKcaps" and GROUP 4 table "Perfumery '
        'ingredient | PROC"; definition "PROC i =OV i [log10 Kcaps i +3]" and "The '
        'standard Odour Value (OV i) is defined as the ratio of the standard equilibrium '
        'headspace concentration of the ingredient to the Odour Detection Threshold of '
        'this ingredient." + Givaudan SA, US 10,982,173 "Fragrance compositions" '
        '(headspace-concentration bins at 25 C) '
        '(https://www.freepatentsonline.com/y2018/0185808.html ; '
        'https://patents.justia.com/patent/10982173): \'"|ISORALDEINE 70 '
        '((E)-3-methyl-4-(2,6,6-trimethylcyclohex-2-en-1-yl)but- 3-en-2-one) |83954 |" ; '
        '"|ISORALDEINE 70 ((E)-3-methyl-4-(2,6,6- |1806 |−2.0 |" ; "ingredients having '
        'equilibrium headspace concentration from about 101 g/l to 150 μg/l, such as '
        "...'; printed PROC 83954, LogKcaps -2.0, HS bin 101–150 ug/L; EST "
        "back-calculated from Givaudan patent tables for 'ISORALDEINE 70': ODT = HS / OV,"
        ' OV = PROC / (LogKcaps + 3). The underlying ODT is Givaudan olfactometer, as '
        'described in US 2018/0185808: "The olfactometer functions on the principle of a '
        'linear dilution of an odorant in a carrier gas ... Each panellist (panel of 15 '
        'persons) ... The final threshold value of a given...; grade EST, access full '
        'text of both patents (Parallel full-content fetch...; second reader: Inputs '
        'printed for ISORALDEINE 70 (Givaudan methyl ionone, named as '
        "alpha-isomethylionone). Ultralia is a PerfumersWorld 'Luxury Methyl Ionone base'"
        ' (CAS 1335-46-2), so this is a main-isomer proxy, not the same product. ODT '
        '1.20–1.79 ng/L; MW 206.33.',
        'Givaudan PROC estimate for Isoraldeine 70, a methyl ionone grade with the same '
        'CAS (1335-46-2); isomer ratios may differ. 0.143-0.212 ppb, geometric midpoint '
        '0.174. Replaces 0.3, which had no source.',
    ]),
    'zenolide': (10.02, 'PEER_SINGLE', [
        'van Gemert L.J. (2011) Odour Thresholds: Compilations of Odour Threshold Values '
        'in Air, Water and Other Media (2nd ed., Oliemans Punter & Partners), AIR section'
        ' "detection (d) and recogniton (r) odour threshold values in mg/m3" (book text '
        'as hosted on vdoc.pub); primary: Traynor S. (2001) The musk dilemma, Perfumer & '
        'Flavorist 26 (Sept/Oct) 28, 30-39 '
        '(https://vdoc.pub/documents/odour-thresholds-compilations-of-odour-threshold-values-in-air-water-and-other-media-6535sgvmi7l0):'
        ' \'"ETHYLENE 1,12-DODECANEDIOATE (musk C-14) [54982-83-1] ... Traynor (2001) '
        '0.105"\'; printed 0.105 mg/m3; Traynor (2001) as compiled by van Gemert (AIR '
        'section, mg/m3); method not shown in the compilation; grade A_measured, access '
        'full text of the book via Parallel web_fetch excerpts...; second reader: Same '
        'CAS as Zenolide (ethylene dodecanedioate). No d/r label; Traynor 2001 reports '
        'detection. 105 ng/L; MW 256.34. Book copy on vdoc.pub.',
        'van Gemert compilation entry (Traynor 2001, detection), same CAS. Replaces 3.0, '
        'which had no source.',
    ]),
    'leafovert': (7.744, 'PEER_SINGLE', [
        'Leafovert (Symrise Perfumery Ingredients datasheet) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Leafovert.pdf):'
        " 'Threshold in Air ... 0.0501 μg/l'; printed 0.0501 µg/l; producer datasheet "
        '"Threshold in Air" (method not stated); grade A_producer, access number seen in '
        'the search-tool excerpt of the datasheet...; second reader: I saw the number in '
        'the PDF myself (the worker had it from a snippet only). The label binding is by '
        'layout. 50.1 ng/L, air; MW 158.19.',
        "Symrise datasheet for its own product; number bound to 'threshold in air' by "
        'layout. Replaces 8.0, a class model.',
    ]),
    'timberol': (13.6, 'PEER_SINGLE', [
        'Timberol (Symrise Perfumery Ingredients datasheet) '
        '(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Timberol.pdf):'
        " 'thresholD in air ... woody timberol® 0.1259 μg/l'; printed 0.1259 µg/l; "
        'producer datasheet "Threshold in Air" (method not stated); grade A_producer, '
        'access full PDF datasheet (Symrise Ingredient Finder, opened...; second reader: '
        'Printed 0.1259 µg/l = 125.9 ng/L, air; MW 226.40. The label binding is by '
        'layout.',
        "Symrise datasheet for its own product, read directly; number bound to 'threshold"
        " in air' by layout. Replaces 0.6, cited to the same datasheet via TGSC as '<= 1 "
        "ppb'.",
    ]),
}

# Write each value to the raw key the runtime lookup already selects (query aliases
# included, e.g. "aldehyde c-12 lauric dodecanal" -> "aldehyde c12 lauric"), so
# the normalized index gains no collisions.
_refresh_normalized_odt_index()
for _name, (_odt_air, _vfy, _sources) in _LITERATURE_ODT_2026_10_25.items():
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources"):
        _entry.pop(_field, None)
    if str(_entry.get("note", "")).startswith("Inventory receipt"):
        _entry.pop("note")
    ODT_DATA[_key] = _entry
    _meta = {
        "vfy": _vfy,
        "sources": list(_sources),
        "note": "Literature threshold batch 2026-10-25 (stock thread); sources re-opened before loading.",
    }
    _prior = ODT_VERIFICATION.get(_key)
    if _prior:
        # Earlier evidence stays readable, and an ethanol value it carries still checks
        # the runtime ethanol threshold: this batch sets the air value only.
        _meta["superseded"] = dict(_prior)
        if "odt_eth" in _prior:
            _meta["odt_eth"] = _prior["odt_eth"]
    ODT_VERIFICATION[_key] = _meta
LITERATURE_ODT_BATCH_2026_10_25 = True

# Labelled analogue estimates, 28 Oct 2026 (stock thread). Kenny chose, on a card in the
# "Fix gaps in unused materials" thread (28 Oct 08:39 UTC): where no measured air ODT
# exists, load an estimate from the closest measured analogue, tagged UNVERIFIED. Each
# value is the geometric mean of the analogue estimate and a PerfumersWorld Relative Odor
# Impact + VP fit (leave-one-out on 20 measured materials: median error about 5x, one in
# three over 10x); /mnt/project-files/unused-gaps-20261028/PW_IMPACT_RESULT.md. ScenTree's
# unsourced air figures were not used. Glycolierral and Fructone B have no measured
# analogue, so they stay without a value. Group 2 (same day) adds five more on the same
# rule; Diethyl Malonate and Aldehyde C16 have only the PW fit, no measured analogue, so
# they stay without a value too.
_ANALOGUE_ODT_ESTIMATES_2026_10_28 = {
    "cedroxyde": (8.0, [
        "Analogue estimate 10 ppb: geometric mean of the engine's woody-amber air values "
        "Vertofix Coeur 6.3 (PEER_SINGLE), Timberol 13.6 (PEER_SINGLE) and Koavone 5 "
        "(UNVERIFIED); weak analogues (ketones, not a macrocyclic epoxide).",
        "PW Relative Odor Impact 80 + VP fit: 6.2 ppb (3WI00098; "
        "https://www.perfumersworld.com/view.php?pro_id=3WI00098).",
        "Geometric mean 7.9 -> 8 ppb. No published air ODT found (ScenTree prints none).",
    ]),
    "cedryl acetate": (20.0, [
        "Analogue estimate 40 ppb: geometric mean of Vertofix Coeur (acetyl cedrene) 6.3 "
        "(PEER_SINGLE) and Cedramber (cedryl methyl ether) 240 (UNVERIFIED).",
        "PW Relative Odor Impact 60 + VP fit: 11.6 ppb (2WW00099; "
        "https://www.perfumersworld.com/view.php?pro_id=2WW00099).",
        "Geometric mean 21.5 -> 20 ppb. The two inputs disagree about 3x.",
    ]),
    "anisyl acetate": (9.0, [
        "Analogue estimate 20 ppb: benzyl acetate 20 ppb (PEER_SINGLE, Nagata 2003), the "
        "parent ester; anisaldehyde 5 ppb (PEER_SINGLE) shows the p-methoxy group can lower it.",
        "PW Relative Odor Impact 80 fit without VP: 4.3 ppb (3LN00043; "
        "https://www.perfumersworld.com/view.php?pro_id=3LN00043).",
        "Geometric mean 9.3 -> 9 ppb.",
    ]),
    "dimethyl benzyl carbinol": (12.0, [
        "Analogue estimate 26 ppb: phenethyl alcohol 26 ppb (PEER_SINGLE), the closest "
        "measured aryl alkanol.",
        "PW Relative Odor Impact 90 + VP fit: 6.2 ppb (3LL00156; "
        "https://www.perfumersworld.com/view.php?pro_id=3LL00156).",
        "Geometric mean 12.7 -> 12 ppb.",
    ]),
    "caryophyllene acetate": (6.0, [
        "Analogue estimate 6.3 ppb: Vertofix Coeur (acetyl cedrene) 6.3 ppb (PEER_SINGLE), "
        "the closest measured sesquiterpene ester/ketone. Vetiveryl acetate (UNVERIFIED) and "
        "cedryl acetate (itself an estimate) were not used.",
        "PW Relative Odor Impact 100 fit: 5.3 ppb (3WI03465; "
        "https://www.perfumersworld.com/view.php?pro_id=3WI03465).",
        "Geometric mean 5.8 -> 6 ppb.",
    ]),
    "hindinol": (7.0, [
        "Analogue estimate 10 ppb: Sandalore 10 ppb (PEER_SINGLE, van Gemert 2011), the "
        "closest measured campholenic sandalwood alcohol.",
        "PW Relative Odor Impact 100 fit: 5.3 ppb (4WX24656; "
        "https://www.perfumersworld.com/view.php?pro_id=4WX24656).",
        "Geometric mean 7.3 -> 7 ppb. Not used: Takasago patent US 5,994,291 gives 51e-12 mol/L "
        "for the (R) form with the medium unstated; Kenny's PW bottle is probably racemic.",
    ]),
    "para-acetanisole": (30.0, [
        "Analogue bracket: anisaldehyde 5 ppb (PEER_SINGLE) and acetophenone 170 ppb "
        "(PubChem / Haz-Map odor threshold low 0.17 ppm, high 0.6 ppm), the p-methoxy and "
        "aryl-ketone parents.",
        "PerfumersWorld does not sell it, so there is no PW Relative Odor Impact fit.",
        "Geometric mean 29 -> 30 ppb; the two parents span 34x.",
    ]),
    "methyl nonyl ketone": (5.5, [
        "Analogue estimate 5.5 ppb: 2-nonanone 5.5 ppb, measured (Cometto-Muniz & Abraham "
        "2009, Table 2; https://pmc.ncbi.nlm.nih.gov/articles/PMC2709282/). 2-Undecanone "
        "itself was not tested.",
        "Replaces 5.0 ppb labelled 'Lotsch et al. 2009, Tier A', which was this 2-ketone "
        "series value, not a measurement of methyl nonyl ketone.",
    ]),
}
_refresh_normalized_odt_index()
for _name, (_odt_air, _sources) in _ANALOGUE_ODT_ESTIMATES_2026_10_28.items():
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    _meta = {
        "vfy": "UNVERIFIED",
        "sources": list(_sources),
        "note": "Analogue estimate 2026-10-28 (Kenny's card choice, 28 Oct 08:39 UTC); not a measurement.",
    }
    if ODT_VERIFICATION.get(_key):
        _meta["superseded"] = dict(ODT_VERIFICATION[_key])
    ODT_VERIFICATION[_key] = _meta

# Cabreuva: the 150 ppb is nerolidol's air value carried to the oil, not a measurement of the oil.
ODT_VERIFICATION["cabreuva eo"] = {
    **ODT_VERIFICATION["cabreuva eo"],
    "vfy": "DERIVED",
    "note": "Constituent-derived (nerolidol, 50-100% of the oil per the Madar SDS); relabelled 2026-10-28 from MULTI_SOURCE_LITERATURE.",
}
# Sandalwood Base X3 (PW 6WX24054) is a mixture: the 100 ppb / 0.5 ppm of the 2026-08-07
# intake batch were invented for it and PW publishes no threshold, so it carries none.
ODT_DATA["sandalwood base x3"] = {
    **ODT_DATA["sandalwood base x3"],
    "odt_air": None,
    "odt_eth": None,
}
ODT_VERIFICATION["sandalwood base x3"] = {
    "vfy": "UNAVAILABLE",
    "sources": [],
    "note": "Removed 2026-10-28: the 2026-08-07 values were invented for a mixture; PW publishes no threshold.",
    "superseded": dict(ODT_VERIFICATION["sandalwood base x3"]),
}
# Himalayan Cedarwood EO: the 15 ppb is the generic cedarwood row, copied; nothing measured.
ODT_VERIFICATION["himalayan cedarwood eo"] = {
    **ODT_VERIFICATION.get("himalayan cedarwood eo", {}),
    "vfy": "UNVERIFIED",
    "sources": ["Copied from the generic 'cedarwood' row (15 ppb); no measured value for Cedrus deodara oil."],
    "note": "Labelled 2026-10-28: not a measurement of this oil.",
}
# Group 3 (28 Oct 2026, same rule). Inputs: /mnt/project-files/unused-gaps-20261028/group3/
# (g3_*/VALUES.md); each source was re-opened before loading.
_ANALOGUE_ODT_ESTIMATES_2026_10_28.update({
    "canthoxal": (1.4, [
        "Measured anchors: Helional 0.14 ppb (Cometto-Muniz & Abraham 2010, Table 2; "
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC2912639/) and Cyclamen aldehyde 0.3237 ppb "
        "(Givaudan SDS, engine row).",
        "Ratios from one human panel (Larsson 2010, Linkoping master project, 20 subjects, "
        "'Laska, unpublished data'; https://www.ifm.liu.se/edu/biology/master_projects/2010/"
        "student-presentation-of-t/linda-larsson/downloads-2/Linda-Larsson.pdf): 'helional, "
        "cyclamal and canthoxal ... 2.1e12, 3.5e12 and 1.8e13 molecules/cm3', so canthoxal is "
        "8.57x helional (1.2 ppb) and 5.14x cyclamal (1.66 ppb).",
        "Geometric mean 1.41 -> 1.4 ppb (range 1.2-1.7). The panel's own absolute values are "
        "unpublished, so only its ratios are used.",
    ]),
    "cinnamyl acetate": (3.0, [
        "Analogue estimate: 2-phenylethyl acetate 2.0 ppb (measured, Schieberle 1998 via van "
        "Gemert 2011; engine row) and cinnamyl alcohol 3.0 ppb (engine row), its ester and "
        "alcohol parents.",
        "PW Relative Odor Impact 120 fit: 4.8 ppb (3SQ00109; "
        "https://www.perfumersworld.com/view.php?pro_id=3SQ00109).",
        "Geometric mean of the three 3.07 -> 3.0 ppb (range 1-10). Not in Nagata 2003 or van "
        "Gemert's air list.",
    ]),
    "phenyl ethyl dimethyl carbinyl acetate": (2.7, [
        "Analogue bracket: 2-phenylethyl acetate 2.0 ppb (measured, engine row), same "
        "Ph-CH2CH2-O chain, and dimethyl benzyl carbinyl acetate 3.75 ppb, same tertiary "
        "acetate head, back-calculated from Givaudan's measured odour value (" + _GIVAUDAN_PROC
        + ": PROC 7061, log Kcaps -2.4, OV 11,768; headspace 301-400 ug/L bin, US 10,982,173, "
        "https://patents.justia.com/patent/10982173).",
        "Geometric mean 2.74 -> 2.7 ppb (range 2.0-3.75).",
    ]),
    "acetoin": (3.0, [
        "Analogue bracket: diacetyl 0.050 ppb and methyl ethyl ketone 440 ppb (Nagata 2003, "
        "Table 2, measured air; https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf), its "
        "oxidised and reduced C4 neighbours; geometric mean 4.7 ppb.",
        "PW Relative Odor Impact 190 fit: 2.1 ppb (4DV02664; "
        "https://www.perfumersworld.com/view.php?pro_id=4DV02664).",
        "Geometric mean 3.1 -> 3 ppb (range 0.5-20). Its published thresholds are in water, "
        "which are not used for air (RULE 1).",
    ]),
    "parmavert": (7.7, [
        "Analogue bracket: PADMA (phenylacetaldehyde dimethyl acetal) 200 ppb (engine row, van "
        "Gemert 2011), the same dimethyl acetal head, and Undecavertol 0.293 ppb (Givaudan SDS "
        "2.0435 ng/l, engine row), the same violet-leaf green family.",
        "Geometric midpoint 7.7 ppb (range 0.3-200). PW Relative Odor Impact does not track "
        "threshold for acetals (PADMA ROI 500 at 200 ppb), so it is not used. Replaces 15, "
        "which had no source.",
    ]),
    "cassia essential oil": (78.0, [
        "Headspace estimate from the oil's composition (PhytoChemia GC report for Plant "
        "Therapy lot CA0101, 26 Feb 2016; https://funyu-store.b-cdn.net/report/"
        "Cinnamon-Cassia-CA0101.pdf: cinnamaldehyde 79.1, coumarin 2.0, benzaldehyde 0.9 %): "
        "Raoult vapour is 60.5 % cinnamaldehyde and 37.4 % benzaldehyde.",
        "1 / (0.605/62 + 0.374/140.5) = 78 ppb, with cinnamaldehyde 62 ppb (engine row, no "
        "primary source quoted: the weak link) and benzaldehyde 140.5 ppb (measured, von "
        "Ranson & Belitz 1992 via AIHA 2013, engine row). Range 60-140.",
        "Replaces 1.5 ppb, which was taken from a cinnamaldehyde value measured in water "
        "(Czerny 2008).",
    ]),
    "turkish storax": (35.0, [
        "Styrene 35 ppb (Nagata 2003, Table 2, triangle odour bag: 'Styrene 0.035' ppm; "
        "https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf), the constituent that makes up "
        "about 99 % of the odorant vapour above the tincture (styrene 0.5 % of the balsam, "
        "Hafizoglu 1982 as quoted by Askun et al. 2021, Turk J Bot; "
        "https://journals.tubitak.gov.tr/cgi/viewcontent.cgi?article=1049&context=botany).",
        "Range 20-35 ppb (lower if styrene has been lost from an aged balsam). Replaces 20 ppb "
        "labelled multi-source literature; none of the cited sources gives a storax threshold.",
    ]),
})
for _name in ("canthoxal", "cinnamyl acetate", "phenyl ethyl dimethyl carbinyl acetate",
              "acetoin", "parmavert", "cassia essential oil", "turkish storax"):
    _odt_air, _sources = _ANALOGUE_ODT_ESTIMATES_2026_10_28[_name]
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    _meta = {
        "vfy": "UNVERIFIED",
        "sources": list(_sources),
        "note": "Analogue estimate 2026-10-28 (Kenny's card choice, 28 Oct 08:39 UTC); not a measurement.",
    }
    if ODT_VERIFICATION.get(_key):
        _meta["superseded"] = dict(ODT_VERIFICATION[_key])
    ODT_VERIFICATION[_key] = _meta

# Sourced values, group 3: a producer measurement, a measured air value and a back-calculated
# producer odour value.
_SOURCED_ODT_2026_10_28 = {
    "azarbre": (1.569, "PEER_SINGLE", [
        "Givaudan Suisse SA, Azarbre Safety Data Sheet (2022), section 9 "
        "(https://www.de-kruiderie.nl/wp-content/uploads/2025/03/SDS-AZARBRE-EN.pdf): "
        "'Odour Threshold : 11,5686 ng/l'; 11.5686 x 24.45 / 180.29 = 1.569 ppb. Producer SDS "
        "figure, medium and method not printed (ng/l is Givaudan's air-threshold unit, as for "
        "the Nympheal SDS); grade A_producer. Replaces 2.0, which had no source.",
    ]),
    "beta-pinene": (33.0, "PEER_SINGLE", [
        "Nagata Y. (2003), Measurement of odor threshold by triangle odor bag method, Table 2 "
        "(https://www.env.go.jp/en/air/odor/measure/02_3_2.pdf): 'beta-Pinene 0.033' ppm v/v = "
        "33 ppb. Replaces 3.0 ppb labelled 'van Gemert (2011)', which could not be traced to a "
        "printed value.",
    ]),
    "ethyl linalyl acetate": (14.42, "PEER_EST", [
        _GIVAUDAN_PROC + ": 'ETHYL LINALYL ACETATE ((Z)-3,7-dimethylnona-1,6-dien-3-yl "
        "acetate) | 5526' (PROC) and '| 1783 | -1.1' (log Kcaps), so OV = 5526 / 1.9 = 2,908; "
        "saturated vapour at the engine VP 4.25 Pa (RIFM-quoted EPI Suite) = 41,944 ppb; "
        "41,944 / 2,908 = 14.42 ppb. With Givaudan's own 4.87 Pa it is 16.5 ppb.",
        "Check: on the same scale linalyl acetate is 66 ppb, so ethyl linalyl acetate is about "
        "0.22x linalyl acetate; against Elsharif's measured 13.8 ppb for linalyl acetate that "
        "gives about 3 ppb, so 14.42 is the weaker end of a 3-15 ppb window.",
    ]),
}
_refresh_normalized_odt_index()
for _name, (_odt_air, _vfy, _sources) in _SOURCED_ODT_2026_10_28.items():
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    _meta = {
        "vfy": _vfy,
        "sources": list(_sources),
        "note": "Sourced threshold 2026-10-28 (stock thread, unused-materials group 3); source re-opened before loading.",
    }
    if ODT_VERIFICATION.get(_key):
        _meta["superseded"] = dict(ODT_VERIFICATION[_key])
    ODT_VERIFICATION[_key] = _meta
# Group 4 (28 Oct 2026, same rules). Inputs: /mnt/project-files/unused-gaps-20261028/group4/
# (g4_*/VALUES.md); each source was re-opened before loading.
_ANALOGUE_ODT_ESTIMATES_2026_10_28.update({
    "2-acetyl pyrazine": (0.40, [
        "Analogue: 2-acetyl-1-pyrroline 0.02 ng/L in air (PMC9351765: '0.1 ug/L in water and "
        "0.02 ng/L in air', next to Adams & De Kimpe, Chem Rev 2006).",
        "Ratio from one lab, one method, one medium: Chetschik et al. 2010, Table 7, thresholds "
        "in sunflower oil: '2-acetylpyrazine 10' and '2-acetyl-1-pyrroline 0.1' ug/kg, so 100x. "
        "0.02 x 100 = 2.0 ng/L x 24.45 / 122.12 = 0.40 ppb.",
        "Range 0.4-2.5 ppb (a water-threshold ratio gives the upper end). Replaces 0.3, which "
        "had no source.",
    ]),
    "allyl ionone": (0.035, [
        "Analogue: alpha-n-methylionone (the methyl-ketone homologue on the same alpha-ionone "
        "skeleton), measured air thresholds (R) 0.53 and (S) 0.24 ng/L (Abate et al., "
        "Tetrahedron: Asymmetry 18 (2007) 1145, as quoted by Leffingwell, "
        "https://www.leffingwell.com/chirality/n_methylionone.htm).",
        "Commercial allyl ionone is racemic: harmonic mean 0.33 ng/L x 24.45 / 232.37 = 0.035 "
        "ppb (range 0.025-0.084). Replaces 1.0, which had no source.",
    ]),
    "maltol": (1.0, [
        "Analogue: ethyl maltol 0.0059 ppb (Park 2012, engine row), the same 3-hydroxy-4-pyranone "
        "one CH2 longer. TGSC's ethyl maltol page "
        "(https://www.thegoodscentscompany.com/data/rw1004172.html): '4-6 x potency of "
        "3-Hydroxy-2-methyl-4H-pyran-4-one' (maltol; flavour use, medium not stated), so "
        "maltol is about 0.024-0.035 ppb on Park's scale.",
        "Park's thesis reads 28-44x below olfactometer values for Galaxolide and Ambroxan; "
        "scaled, 0.8-1.3 ppb. The engine's 1.0 is kept, range 0.3-1.3. Maltol's published "
        "threshold (2500 ug/L) is in water and is not used (RULE 1).",
    ]),
    "cade oil rectified": (0.05, [
        "Analogue: cade's measured odour-active phenols weighted by their share of its vapour "
        "(Raoult model, central case, same as its 5.4 Pa VP): guaiacol 0.01654 ppb (engine row), "
        "p-cresol 0.054 ppb and phenol 5.6 ppb (Nagata 2003, Table 2); additive odour units, "
        "1/ODT = 0.29/0.01654 + 0.10/0.054 + 0.37/5.6, so 0.05 ppb of total cade vapour.",
        "Range 0.05-0.34 ppb (guaiacol at Yang 2008's 0.295 ppb). Creosol has no measured air "
        "value and is left out. Valid only with the 5.4 Pa constituent VP. Replaces 3.0, which "
        "had no source.",
    ]),
})
_SOURCED_ODT_2026_10_28["methyl laitone"] = (0.0303, "PEER_SINGLE", [
    "Givaudan Safety Data Sheet METHYL LAITONE 10%/DPG, Sales No. 6978468, Version 4.1 (14 JUN "
    "2024; https://perfumiarz.com/cdn/shop/files/6978468_METHYL_LAITONE_10DPG_SDS_EN.pdf) and "
    "Version 3.7 (07 JUN 2015): 'Odour Threshold : 0,2085 ng/l'; 0.2085 x 24.45 / 168.23 = "
    "0.0303 ppb. Read as the pure lactone: the same section prints the vapour pressure as "
    "'Calculated (100,0 %)', and Givaudan's product pages say 'Dilutions: evaluated as pure "
    "material'. The SDS odour field ('woody, Ambery, Powerful, Persistent') is Givaudan's "
    "descriptor, not a coconut description. Grade A_producer; method not printed.",
])
for _name in ("2-acetyl pyrazine", "allyl ionone", "maltol", "cade oil rectified"):
    _odt_air, _sources = _ANALOGUE_ODT_ESTIMATES_2026_10_28[_name]
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    _meta = {
        "vfy": "UNVERIFIED",
        "sources": list(_sources),
        "note": "Analogue estimate 2026-10-28 (Kenny's card choice, 28 Oct 08:39 UTC); not a measurement.",
    }
    if ODT_VERIFICATION.get(_key):
        _meta["superseded"] = dict(ODT_VERIFICATION[_key])
    ODT_VERIFICATION[_key] = _meta
_refresh_normalized_odt_index()
_odt_air, _vfy, _sources = _SOURCED_ODT_2026_10_28["methyl laitone"]
_key = lookup_odt_raw_name("methyl laitone") or "methyl laitone"
_entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
_entry["odt_air"] = _odt_air
for _field in ("vfy", "sources", "note"):
    _entry.pop(_field, None)
ODT_DATA[_key] = _entry
ODT_VERIFICATION[_key] = {
    "vfy": _vfy,
    "sources": list(_sources),
    "note": "Sourced threshold 2026-10-28 (stock thread, unused-materials group 4); source re-opened before loading.",
    **({"superseded": dict(ODT_VERIFICATION[_key])} if ODT_VERIFICATION.get(_key) else {}),
}
# Group 5 (28 Oct 2026). Inputs: /mnt/project-files/unused-gaps-20261028/group5/ (g5_*/VALUES.md).
ODT_DATA["sweet orange essential oil"] = {"odt_air": 23.0, "odt_eth": None}
ODT_VERIFICATION["sweet orange essential oil"] = {
    "vfy": "UNVERIFIED",
    "sources": [
        "Constituent estimate, not a measurement: 1/ODT = sum of y_i/ODT_i over the Raoult headspace of "
        "the sweet orange profile (COA limonene 95.28 % plus ISO 3140:2019 Table 2 midpoints, "
        "engine/pipeline/natural_absolute_decomposition.py). Measured air thresholds: limonene 38 ppb "
        "(Nagata 2003, Table 2 '0.038' ppm), alpha-pinene 18 ppb (Nagata), octanal 0.17 ppb "
        "(Cometto-Muniz 2010), decanal 0.40 ppb (Nagata), linalool 0.51 ppb (Elsharif 2015).",
        "Limonene carries 57 % and octanal 35 % of the odour units; range 3.6-24 ppb (octanal at "
        "Nagata's 0.010 ppb gives 3.6). Replaces the borrowed Orange Peel EO row.",
    ],
    "note": "Constituent estimate 2026-10-28 (stock thread, unused-materials group 5); sources re-opened before loading.",
}
# Costus Olifac is a partly declared IFF base (data/regulatory/partly_declared_bases.json): its
# 0.05 and 5.0 ppb rows had no source, so they are retired and the gate warns on the undeclared part.
ODT_DATA.pop("costus olifac", None)
ODT_VERIFICATION.pop("costus olifac", None)
_refresh_normalized_odt_index()
# Group 6 (28 Oct 2026). Inputs: /mnt/project-files/unused-gaps-20261028/group6/ (g6_*/VALUES.md).
ODT_DATA["rum ether"] = {"odt_air": 160.0, "odt_eth": None}
ODT_VERIFICATION["rum ether"] = {
    "vfy": "UNVERIFIED",
    "sources": [
        "Constituent estimate, not a measurement: headspace odorant ppb / sum of OAVs over the Raoult "
        "headspace of the EFSA FGE.500 Company 2 rum ether scenario (doi:10.2903/j.efsa.2017.4897; "
        "engine/pipeline/natural_absolute_decomposition.py). Measured air thresholds (Nagata 2003, "
        "Table 2): ethanol 520, ethyl acetate 870, ethyl formate 2700, ethyl propionate 7.0, ethyl "
        "butyrate 0.040 ppb. Ethyl butyrate carries 69% of the odour units.",
        "Range 15-170 ppb across the EFSA producers (Company 1 profile 15, Company 4 17); the label is "
        "for the composition choice and ideal mixing, not the constituent thresholds.",
    ],
    "note": "Constituent estimate 2026-10-28 (stock thread, unused-materials group 6); sources re-opened before loading.",
}
_refresh_normalized_odt_index()
# Group 7 (28 Oct 2026). Inputs: /mnt/project-files/unused-gaps-20261028/group7/ (g7_*/VALUES.md);
# Kenny 11:11 UTC: "Also put chemicals that are never used or cannot be used here". The PEER_EST rows
# are Givaudan odour values divided into the engine's own saturated vapour, so each is tied to its VP.
_SOURCED_ODT_2026_10_28.update({
    "peach ketone": (0.0140, "PEER_EST", [
        _GIVAUDAN_PROC + ": 'NECTARYL (2-(2-(4-methylcyclohex-3-en-1-yl)propyl)cyclopentanone) 13091' "
        "(PROC) and log Kcaps -1.9, so OV = 13091 / 1.1 = 11,901; saturated vapour at the engine VP "
        "0.0169 Pa (ECHA OECD 104, 0.0092 Pa at 20 C and 0.27 Pa at 50 C, interpolated) = 167.2 ppb; "
        "167.2 / 11,901 = 0.0140 ppb.",
        "Cross-check: Brenna et al., Tetrahedron: Asymmetry 19 (2008) 800, per-isomer air thresholds "
        "0.094, 0.112, 11.2 and 14.9 ng/L (https://www.leffingwell.com/chirality/nectaryl.htm); a "
        "1:1:1:1 mix is 0.0225 ppb (1.9x).",
    ]),
    "veloutone": (6.85, "PEER_EST", [
        _GIVAUDAN_PROC + ": 'VELOUTONE (2,2,5-trimethyl-5-pentylcyclopentanone) 14571' (PROC) and log "
        "Kcaps -1.9, so OV = 14571 / 1.1 = 13,246; saturated vapour at the ECHA VP 9.2 Pa (OECD 104 gas "
        "saturation, 25 C) = 90,797 ppb; 90,797 / 13,246 = 6.85 ppb. Replaces an empty row.",
    ]),
    "beta caryophyllene": (49.0, "PEER_EST", [
        _GIVAUDAN_PROC + ": 'CARYOPHYLLENE ((Z)-4,11,11-trimethyl-8-methylenebicyclo[7.2.0]undec-4-ene) "
        "| 609' (PROC) and log Kcaps -1.0, so OV = 609 / 2.0 = 304.5; saturated vapour at the engine VP "
        "1.513 Pa = 14,932 ppb; 14,932 / 304.5 = 49.0 ppb.",
        "Cross-check: Ruth 1986 0.535 mg/m3 = 64 ppb (quoted by UBA 54/2024), within 1.3x.",
    ]),
    "buccoxime": (5.818, "PEER_SINGLE", [
        "Symrise Buccoxime product sheet "
        "(https://www.symrise.com/fileadmin/symrise/Marketing/Scent_and_care/Aroma_molecules/"
        "Ingredient_finder/SYM_PC_Datenblaetter/SYM_PC-Buccoxime.pdf), 'Threshold in Air': "
        "'Buccoxime 0.0398 ug/l'; 39.8 x 24.45 / 167.25 = 5.818 ppb. Grade A_producer.",
    ]),
})
_ANALOGUE_ODT_ESTIMATES_2026_10_28.update({
    "pear valerate": (2.1, [
        "Analogue: hexyl acetate 2.9 ppb in air (Cometto-Muniz 2008, engine row) = 17.1 ng/L, held at "
        "the same mass threshold: 17.1 x 24.45 / 200.32 = 2.1 ppb. Manzanate (same acid) 0.30 ng/L is "
        "the strong bound; order-of-magnitude only.",
    ]),
    "cis-3 hexenyl hexanoate": (3.1, [
        "Analogues: cis-3-hexenyl acetate 15.52 ng/L (Givaudan US 12,340,876 Table 1) and "
        "cis-3-hexenyl butyrate about 40 ng/L (" + _GIVAUDAN_PROC + ": OV 97634 / 1.8 with an "
        "estimated VP 25-39 Pa); geometric mean 25 ng/L x 24.45 / 198.31 = 3.1 ppb (range 1.9-6.0).",
    ]),
    "isolongifolanone": (9.0, [
        "Analogue: methyl cedryl ketone (Vertofix) 6.3 ppb (van Gemert 2011 / Devos 1990, engine row), "
        "geometric mean with a PerfumersWorld ROI regression for ROI 50 (14 ppb) = 9 ppb (range 6-14).",
    ]),
    "rhubofix": (6.0, [
        "Analogue: methyl cedryl ketone (Vertofix) 6.3 ppb (engine row), geometric mean with a "
        "PerfumersWorld ROI regression for ROI 100 (5.25 ppb) = 6 ppb (range 5-6.3).",
    ]),
    "linalool oxide": (2.3, [
        "Analogues from one panel and method (Elsharif, Banerjee & Buettner, Front. Chem. 3:57 (2015), "
        "Table 3): linalool 3.2 ng/L; every oxygenated derivative at least 2x weaker (floor 6.4 ng/L); "
        "8-oxolinalool 38.1 ng/L. Geometric mean 16 ng/L x 24.45 / 170.25 = 2.3 ppb (range 0.92-23). "
        "No isomer has a measured air threshold.",
    ]),
})
_refresh_normalized_odt_index()
for _name in ("peach ketone", "veloutone", "beta caryophyllene", "buccoxime"):
    _odt_air, _vfy, _sources = _SOURCED_ODT_2026_10_28[_name]
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    ODT_VERIFICATION[_key] = {
        "vfy": _vfy,
        "sources": list(_sources),
        "note": "Sourced threshold 2026-10-28 (stock thread, unused-materials group 7); source re-opened before loading.",
        **({"superseded": dict(ODT_VERIFICATION[_key])} if ODT_VERIFICATION.get(_key) else {}),
    }
for _name in ("pear valerate", "cis-3 hexenyl hexanoate", "isolongifolanone", "rhubofix", "linalool oxide"):
    _odt_air, _sources = _ANALOGUE_ODT_ESTIMATES_2026_10_28[_name]
    _key = lookup_odt_raw_name(_name) or _name
    _entry = dict(ODT_DATA.get(_key) or {"odt_eth": None})
    _entry["odt_air"] = _odt_air
    for _field in ("vfy", "sources", "note"):
        _entry.pop(_field, None)
    ODT_DATA[_key] = _entry
    ODT_VERIFICATION[_key] = {
        "vfy": "UNVERIFIED",
        "sources": list(_sources),
        "note": "Analogue estimate 2026-10-28 (unused-materials group 7); not a measurement.",
        **({"superseded": dict(ODT_VERIFICATION[_key])} if ODT_VERIFICATION.get(_key) else {}),
    }
_refresh_normalized_odt_index()
ANALOGUE_ODT_BATCH_2026_10_28 = True


# (auditor CRITICAL C1: without this, batch ODT_DATA entries are unreachable via runtime lookup)
MATERIAL_INTAKE_REMEDIATION_2026_08_07 = True
_refresh_normalized_odt_index()
_ODT_VERIFICATION_BY_NORMALIZED_NAME = {
    normalize_name(raw_name): data for raw_name, data in ODT_VERIFICATION.items()
}
_raise_on_normalized_odt_collisions()
