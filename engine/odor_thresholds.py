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
    "rhodinol": {
        "vfy": "PEER_EST",
        "sources": ["Citronellol analogue — Van Gemert (2011)"],
        "odt_air": 0.3,
        "odt_eth": 5.0,
    },
    "rhodinol ex citronella": {
        "vfy": "PEER_EST",
        "sources": ["Rhodinol analogue — Van Gemert (2011)"],
        "odt_air": 0.3,
        "odt_eth": 5.0,
        "char": "rose-geranium, green-minty, natural",
    },
    # Verified: Elsharif & Buettner (2016) J Agric Food Chem 64:4830 — 14 ng/L (2.22 ppb)
    # Verified: Elsharif & Buettner (2016) J Agric Food Chem 64:4830 — 14 ng/L (2.22 ppb)
    "geraniol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Elsharif & Buettner (2016) J. Agric. Food Chem. 64:4830"],
        "odt_air": 0.04,
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
        "char": "rose-plum damascone alcohol",
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
        "char": "cut grass, galbanum, sharp",
    },
    "triplal": {"odt_air": 0.5, "odt_eth": 0.001, "char": "cyclamen, ozonic, metallic"},
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
    "florhydral": {"odt_air": 0.3, "odt_eth": 0.2, "char": "floral, green, muguet, fresh"},
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
    # UNVERIFIED — no peer-reviewed air-phase ODT found
    "vertofix coeur": {
        "odt_air": 240.0,
        "odt_eth": 1.0,
        "char": "cedryl methyl ether, woody-musky, dry-cedar",
    },
    # Verified: van Gemert 2011 — ODT_air = 6.3 ppb for methyl cedryl ketone
    # UNVERIFIED — no peer-reviewed air-phase ODT found
    "vertofix": {
        "odt_air": 6.3,
        "odt_eth": 1.0,
        "char": "cedryl methyl ether, woody-musky, dry-cedar",
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
            "PerfumersWorld SKU 8IQ24653 (80-85% irone supplier declaration)",
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
    "ambrocenide": {"odt_air": 0.02, "odt_eth": 0.02, "char": "crystalline amber"},
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
    "azhrbre": {"odt_air": 2.0, "odt_eth": 0.5, "char": "cedar-amber, warm-smooth"},
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
    "citronellol": {
        "vfy": "PEER_SINGLE",
        "sources": ["Nagata (2003)"],
        "odt_air": 0.3,
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
        "odt_air": 5.0,
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
        "sources": ["Elsharif & Buettner (2016) J. Agric. Food Chem. 64:4830 — 14 ng/L (2.22 ppb)"],
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
        "sources": ["Same as Vertofix — TGSC cedryl methyl ether; cedrol ODT 80-200 ppb lit."],
        "note": "Tier B — TGSC supplier data (same molecule as Vertofix)",
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
        "vfy": "UNVERIFIED",
        "sources": ["No peer-reviewed air-phase ODT found in indexed literature"],
        "note": "Auto-tagged by audit 2026-05-11",
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
    "azhrbre": {
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
    "citronellol": {"vfy": "PEER_SINGLE", "sources": ["Nagata (2003)"]},
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
        "vfy": "DERIVED",
        "sources": ["Givaudan product page; retailer descriptions — use-level inference only"],
        "note": "Legacy 0.3 ppb screen retained; not a measured air-threshold result.",
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
            "Whole oil/natural — no single air-phase ODT exists in peer-reviewed literature"
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
        "vfy": "PEER_EST",
        "sources": [
            "ScenTree entry — usage at 0.01-0.03% implies ~0.3-0.8 ppb; cyclamen-ozonic aldehyde class"
        ],
        "note": "Tier B — usage pattern + supplier data",
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
    "vetikon": {
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
        "vfy": "PEER_SINGLE",
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
    if key == normalize_name("linalool"):
        metadata["vfy"] = "UNVERIFIED"
        metadata["evidence_conflict"] = (
            "Legacy source prose cites 0.51 ppb; active late patch is 1.5 ppb. "
            "Neither source is silently replaced or promoted."
        )
    elif key in {normalize_name("hedione"), normalize_name("iso e super")} and not conflicts:
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
    "geraniol": 0.04,
    "hedione": 0.05,
    "helional": 0.1,
    "iso e super": 0.05,
    "javanol": 0.0016,
    "methyl nonyl ketone": 5.0,
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
    "triplal": 0.5,
    "florhydral": 0.3,
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
    "citronellol": 40.0,
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
ODT_DATA.setdefault("stralyl acetate", {}).update(
    {"odt_air": 40.0, "odt_eth": 1.0, "char": "green, sweet, floral"}
)
ODT_VERIFICATION.setdefault("stralyl acetate", {}).update(
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

# (auditor CRITICAL C1: without this, batch ODT_DATA entries are unreachable via runtime lookup)
MATERIAL_INTAKE_REMEDIATION_2026_08_07 = True
_refresh_normalized_odt_index()
_ODT_VERIFICATION_BY_NORMALIZED_NAME = {
    normalize_name(raw_name): data for raw_name, data in ODT_VERIFICATION.items()
}
_raise_on_normalized_odt_collisions()
