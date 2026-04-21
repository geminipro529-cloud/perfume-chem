"""Ingredient Intelligence Database — Per-material character dimensions and properties.

Every material scored on 13 perceptual character dimensions (0–10 scale)
plus physical-chemical properties for formula-level computation.

Character dimensions (Perplexity-recommended odor radar):
  warmth     — warm/amber/balsamic vs cool/fresh
  sweetness  — sugar/honey/vanilla character
  freshness  — clean/citrus/aquatic/ozonic lift
  powdery    — iris/musk/coumarin powder
  green      — leafy/herbaceous/galbanum
  animalic   — musk/leather/indolic depth
  radiance   — hedione-like projection halo, luminosity
  woody      — cedar/sandalwood/vetiver
  spicy      — pepper/cardamom/cinnamon
  floral     — rose/jasmine/muguet
  smoky      — incense/birch/guaiacol
  creamy     — lactonic/sandalwood/vanilla smoothness
  transparency — sheer/clean/skin-adjacent clarity

Physical properties (from DB or estimated):
  mw         — molecular weight (g/mol)
  vp         — vapor pressure at 25°C (Pa)
  clogp      — calculated octanol-water partition coefficient
  odt        — odor detection threshold (ppb in air)

Functional tags:
  note       — top / heart / base
  role       — character, modifier, fixative, volume, radiance, bridge, trace
  synergies  — list of best-with materials
  avoid      — list of materials that clash
  texture    — skin-effect, diffusion, cushion, lift, cocoon, veil, halo

Sources: Arctander, PerfumersWorld ABC, Carles method, Roudnitska aesthetics,
         Jellinek quadrants, OPK SAR classes, Perplexity multi-dimensional model.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from dataclasses import dataclass, field

from engine.material_identity import resolve_material_identity

# Character dimension names (order matters for radar plot)
DIMENSIONS = [
    "warmth", "sweetness", "freshness", "powdery", "green",
    "animalic", "radiance", "woody", "spicy", "floral",
    "smoky", "creamy", "transparency",
]


@dataclass
class MaterialProfile:
    """Complete intelligence profile for one material."""
    name: str
    # 13 character dimensions, each 0-10
    character: dict[str, float] = field(default_factory=dict)
    # Physical properties
    mw: float | None = None
    vp: float | None = None
    clogp: float | None = None
    odt: float | None = None
    # Classification
    note: str = "heart"          # top / heart / base
    role: str = "modifier"       # character, modifier, fixative, volume, radiance, bridge, trace
    texture: str = ""            # skin-effect, diffusion, cushion, lift, cocoon, veil, halo
    # Relationships
    synergies: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    # Dilution in inventory
    dilution: float = 1.0        # 1.0 = neat, 0.1 = 10%, etc.

    def dimension_vector(self) -> list[float]:
        """Return ordered vector of character dimensions."""
        return [self.character.get(d, 0.0) for d in DIMENSIONS]

    def dominant_character(self) -> str:
        """Return the highest-scoring dimension name."""
        if not self.character:
            return "neutral"
        return max(self.character, key=self.character.get)

    def character_tags(self, threshold: float = 4.0) -> list[str]:
        """Return dimensions above threshold, sorted by strength."""
        return sorted(
            [d for d, v in self.character.items() if v >= threshold],
            key=lambda d: self.character[d],
            reverse=True,
        )


# ── Complete inventory intelligence database ──
# Every material from inventory.txt with expert-assigned character dimensions.
# Values: 0=absent, 1-2=trace, 3-4=noticeable, 5-6=moderate, 7-8=strong, 9-10=defining

_PROFILES: dict[str, dict] = {
    # ═══════════════════════ CITRUS / TOP ═══════════════════════
    "Citral": {
        "character": {"freshness": 9, "green": 5, "floral": 2, "sweetness": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 152.23, "vp": 3.5, "clogp": 2.76,
        "synergies": ["Linalool", "Geraniol", "Citronellal"],
    },
    "Citronellal": {
        "character": {"freshness": 8, "green": 4, "floral": 3, "sweetness": 1},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 154.25, "vp": 2.8, "clogp": 3.09,
        "synergies": ["Citral", "Hydroxycitronellal", "Geraniol"],
    },
    "D-Limonene": {
        "character": {"freshness": 8, "sweetness": 2, "green": 1},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 136.23, "vp": 1.98, "clogp": 4.57,
        "synergies": ["Linalool", "Bergamot FCF"],
    },
    "Linalool": {
        "character": {"freshness": 7, "floral": 6, "sweetness": 2, "woody": 1},
        "note": "top", "role": "bridge", "texture": "lift",
        "mw": 154.25, "vp": 0.16, "clogp": 2.97,
        "synergies": ["Linalyl Acetate", "Hedione", "Geraniol", "Bergamot FCF"],
    },
    # Ethyl Linalool (linalool ethyl ether): sharper, cleaner, more transparent
    # than linalool. Less sweet, more citrus-ether character. Terpene alcohol family.
    "Ethyl Linalool": {
        "character": {"freshness": 8, "floral": 4, "woody": 2, "green": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 182.30, "vp": 0.08, "clogp": 3.5,
        "synergies": ["Linalool", "Hedione", "Dihydromyrcenol", "Bergamot FCF"],
    },
    "Linalyl Acetate": {
        "character": {"freshness": 8, "floral": 4, "sweetness": 3, "green": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 196.29, "vp": 0.07, "clogp": 3.56,
        "synergies": ["Linalool", "Lavender EO", "Bergamot FCF"],
    },
    "Terpinyl Acetate": {
        "character": {"freshness": 6, "woody": 4, "green": 5, "spicy": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 196.29, "vp": 0.05, "clogp": 3.48,
        "synergies": ["Lavender EO", "Cedarwood EO", "Linalyl Acetate"],
    },
    "Hexyl Acetate": {
        "character": {"freshness": 7, "green": 5, "sweetness": 3},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 144.21, "vp": 1.4, "clogp": 2.83,
        "synergies": ["cis-3-Hexenol", "Bergamot FCF"],
        "dilution": 0.1,
    },
    "Aldehyde C10": {
        "character": {"freshness": 5, "sweetness": 3, "floral": 4, "radiance": 6},
        "note": "top", "role": "trace", "texture": "lift",
        "mw": 156.27, "vp": 0.24, "clogp": 3.76,
        "synergies": ["Aldehyde C11", "Aldehyde C12 MNA", "Benzyl Salicylate"],
        "dilution": 0.01,
    },
    "Aldehyde C11": {
        "character": {"freshness": 4, "sweetness": 2, "floral": 3, "radiance": 7, "powdery": 2},
        "note": "top", "role": "trace", "texture": "lift",
        "mw": 170.29, "vp": 0.09, "clogp": 4.3,
        "synergies": ["Aldehyde C10", "Aldehyde C12 MNA", "Benzyl Salicylate"],
        "dilution": 0.01,
    },
    "Aldehyde C11 undecylenic": {
        "character": {"freshness": 5, "green": 4, "floral": 3, "radiance": 5},
        "note": "top", "role": "trace", "texture": "lift",
        "mw": 168.28, "vp": 0.1, "clogp": 3.8,
        "synergies": ["Aldehyde C11", "Rose Oxide"],
    },
    "Aldehyde C12 MNA": {
        "character": {"freshness": 3, "floral": 5, "sweetness": 2, "radiance": 8, "powdery": 3},
        "note": "top", "role": "trace", "texture": "halo",
        "mw": 184.32, "vp": 0.04, "clogp": 4.83,
        "synergies": ["Aldehyde C10", "Aldehyde C11", "Benzyl Salicylate", "Hedione"],
        "dilution": 0.01,
    },
    "Methyl Pamplemousse": {
        "character": {"freshness": 8, "green": 3, "sweetness": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 168.23, "vp": 0.5, "clogp": 2.1,
        "synergies": ["Grapefruit FCF", "Hedione", "Allyl Amyl Glycolate"],
        "dilution": 0.1,
    },
    "Bergamot EO": {
        "character": {"freshness": 8, "floral": 3, "sweetness": 2, "green": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 1.5, "clogp": 3.5,
        "synergies": ["Linalool", "Hedione", "Neroli EO"],
    },
    "Bergamot FCF": {
        "character": {"freshness": 8, "floral": 3, "sweetness": 2, "green": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 1.5, "clogp": 3.2,
        "synergies": ["Linalool", "Hedione", "Iso E Super"],
    },
    "Bergamot FCF oil Sicilian": {
        "character": {"freshness": 8, "floral": 4, "sweetness": 2, "green": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 1.5, "clogp": 3.2,
        "synergies": ["Linalool", "Hedione", "Neroli EO"],
    },
    "Grapefruit FCF": {
        "character": {"freshness": 9, "green": 3, "sweetness": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 218.34, "vp": 0.8, "clogp": 4.2,
        "synergies": ["Methyl Pamplemousse", "Iso E Super", "Vetiver EO"],
    },
    "Cedrat FCF oil Sicilian": {
        "character": {"freshness": 7, "green": 4, "sweetness": 1, "woody": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 168.0, "vp": 1.2, "clogp": 3.0,
        "synergies": ["Bergamot FCF", "Iso E Super", "Ambrox Super"],
    },
    "Blood Orange oil Sicilian": {
        "character": {"freshness": 7, "sweetness": 4, "warmth": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 136.23, "vp": 1.9, "clogp": 4.57,
        "synergies": ["Bergamot FCF", "Neroli EO", "Cedrat FCF oil Sicilian"],
    },
    "Red Mandarin EO": {
        "character": {"freshness": 6, "sweetness": 5, "warmth": 3},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 136.23, "vp": 1.8, "clogp": 4.4,
        "synergies": ["Neroli EO", "Vanillin", "Coumarin"],
    },
    "Ethyl 2-Methylbutyrate": {
        "character": {"freshness": 6, "sweetness": 5, "green": 3},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 130.18, "vp": 5.0, "clogp": 1.9,
        "synergies": ["Gamma Decalactone", "Allyl Amyl Glycolate"],
    },

    # ═══════════════════════ GREEN / FRESH / MARINE ═══════════════════════
    "Dihydromyrcenol": {
        "character": {"freshness": 9, "green": 3, "woody": 2, "radiance": 4},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 156.27, "vp": 0.3, "clogp": 3.47,
        "synergies": ["Iso E Super", "Hedione", "Ambrox Super"],
    },
    "cis-3-Hexenol": {
        "character": {"green": 10, "freshness": 5},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 100.16, "vp": 1.4, "clogp": 1.61,
        "synergies": ["Galbanum Resinoid", "Hexyl Acetate", "Parmavert"],
    },
    "Verdox": {
        "character": {"green": 7, "freshness": 5, "floral": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 170.25, "vp": 0.3, "clogp": 3.2,
        "synergies": ["cis-3-Hexenol", "Hedione"],
    },
    "Galbanum Resinoid": {
        "character": {"green": 9, "woody": 3, "spicy": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 200.0, "vp": 0.1, "clogp": 2.5,
        "synergies": ["cis-3-Hexenol", "Dynascone", "Parmavert"],
        "dilution": 0.1,
    },
    "Cyclamen Aldehyde": {
        "character": {"green": 6, "floral": 5, "freshness": 4},
        "note": "heart", "role": "modifier", "texture": "lift",
        "mw": 164.24, "vp": 0.08, "clogp": 3.1,
        "synergies": ["Hedione", "Floralozone", "Parmavert"],
    },
    "Scentenal": {
        "character": {"green": 4, "freshness": 6, "woody": 3},
        "note": "heart", "role": "trace", "texture": "veil",
        "mw": 166.22, "vp": 0.01, "clogp": 2.8,
        "synergies": ["Iso E Super", "Ambrox Super"],
        "dilution": 0.01,
    },
    "Calone": {
        "character": {"freshness": 7, "green": 5, "sweetness": 2},
        "note": "heart", "role": "trace", "texture": "veil",
        "mw": 192.21, "vp": 0.005, "clogp": 1.4,
        "synergies": ["Floralozone", "Hedione", "Dihydromyrcenol"],
        "dilution": 0.01,
    },
    "Floralozone": {
        "character": {"freshness": 7, "floral": 4, "green": 3},
        "note": "heart", "role": "modifier", "texture": "veil",
        "mw": 192.26, "vp": 0.02, "clogp": 2.6,
        "synergies": ["Hedione", "Calone", "Cyclamen Aldehyde"],
        "dilution": 0.1,
    },
    "Undecavertol": {
        "character": {"green": 6, "freshness": 5, "floral": 3},
        "note": "heart", "role": "modifier", "texture": "lift",
        "mw": 170.29, "vp": 0.06, "clogp": 3.8,
        "synergies": ["Hedione", "cis-3-Hexenol"],
    },
    "Dynascone": {
        "character": {"green": 10, "freshness": 3, "spicy": 2},
        "note": "top", "role": "trace", "texture": "lift",
        "mw": 192.30, "vp": 0.15, "clogp": 3.4,
        "synergies": ["Galbanum Resinoid", "cis-3-Hexenol"],
        "dilution": 0.1,
    },
    "Parmavert": {
        "character": {"green": 8, "floral": 3, "powdery": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 192.30, "vp": 0.1, "clogp": 3.5,
        "synergies": ["Alpha Ionone", "Beta Ionone", "cis-3-Hexenol"],
    },
    "Leafovert": {
        "character": {"green": 9, "freshness": 4},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 154.25, "vp": 0.5, "clogp": 3.0,
        "synergies": ["cis-3-Hexenol", "Parmavert"],
    },

    # ═══════════════════════ FLORAL MATERIALS ═══════════════════════
    "Hedione": {
        "character": {"radiance": 10, "floral": 6, "freshness": 5, "sweetness": 1},
        "note": "heart", "role": "radiance", "texture": "halo",
        "mw": 226.31, "vp": 0.003, "clogp": 3.0,
        "synergies": ["Benzyl Salicylate", "Iso E Super", "Linalool", "Bergamot FCF", "Neroli EO"],
    },
    "Hydroxycitronellal": {
        "character": {"floral": 7, "sweetness": 4, "freshness": 3, "powdery": 2, "creamy": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 172.27, "vp": 0.005, "clogp": 1.6,
        "synergies": ["Hedione", "Linalool", "Lilyreal ND"],
    },
    "Phenethyl Alcohol": {
        "character": {"floral": 8, "sweetness": 2, "green": 1},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 122.16, "vp": 0.09, "clogp": 1.36,
        "synergies": ["Citronellol", "Geraniol", "Rose Oxide"],
    },
    "Florol": {
        "character": {"floral": 6, "green": 4, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "lift",
        "mw": 154.25, "vp": 0.05, "clogp": 2.3,
        "synergies": ["Hedione", "Hydroxycitronellal", "Lilyreal ND", "Bourgeonal"],
    },
    "Nympheal": {
        # Local formulas consistently use Nympheal as a radiant, diffusive muguet/waterlily material.
        "character": {"floral": 6, "freshness": 5, "green": 3, "radiance": 7, "creamy": 2},
        "note": "heart", "role": "radiance", "texture": "halo",
        "mw": 204.31, "vp": 0.01, "clogp": 3.8,
        "synergies": ["Hedione", "Hydroxycitronellal", "Lilyreal ND", "Freesia HDI"],
    },
    "Peonile": {
        "character": {"floral": 7, "green": 3, "sweetness": 3, "freshness": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 156.22, "vp": 0.02, "clogp": 2.5,
        "synergies": ["Hedione", "Phenethyl Alcohol"],
    },
    "Aurantiol": {
        "character": {"floral": 6, "sweetness": 4, "warmth": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 251.28, "vp": 0.001, "clogp": 3.0,
        "synergies": ["Hedione", "Neroli EO"],
    },
    "Geraniol": {
        "character": {"floral": 7, "sweetness": 3, "freshness": 4, "green": 1},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 154.25, "vp": 0.03, "clogp": 3.56,
        "synergies": ["Citronellol", "Phenethyl Alcohol", "Rose Oxide"],
    },
    "Citronellol": {
        "character": {"floral": 6, "freshness": 4, "sweetness": 2, "green": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 156.27, "vp": 0.02, "clogp": 3.91,
        "synergies": ["Geraniol", "Phenethyl Alcohol", "Rose Oxide"],
    },
    "Rose Oxide": {
        "character": {"floral": 7, "green": 4, "spicy": 2, "freshness": 3},
        "note": "heart", "role": "character", "texture": "lift",
        "mw": 154.25, "vp": 0.5, "clogp": 3.2,
        "synergies": ["Citronellol", "Geraniol", "Phenethyl Alcohol"],
        "dilution": 0.1,
    },
    "Benzyl Salicylate": {
        "character": {"floral": 3, "sweetness": 2, "powdery": 4, "warmth": 3, "creamy": 3, "radiance": 4},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 228.24, "vp": 0.001, "clogp": 4.31,
        "synergies": ["Hedione", "DBCA", "Iso E Super", "Aldehydes"],
    },
    "Hexyl Salicylate": {
        "character": {"floral": 4, "green": 4, "freshness": 3, "powdery": 2, "radiance": 3},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 222.28, "vp": 0.002, "clogp": 4.87,
        "synergies": ["Hedione", "Benzyl Salicylate", "Paradisamide", "Iso E Super"],
    },
    "Benzyl Benzoate": {
        "character": {"sweetness": 2, "warmth": 2, "floral": 1},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 212.24, "vp": 0.001, "clogp": 3.97,
        "synergies": ["Benzyl Salicylate", "Vanillin"],
    },
    "Benzyl Acetate": {
        "character": {"floral": 6, "sweetness": 4, "freshness": 3, "green": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 150.17, "vp": 0.22, "clogp": 1.96,
        "synergies": ["Hedione", "Indole", "Linalool"],
    },
    "Indole": {
        "character": {"floral": 5, "animalic": 8, "sweetness": 1},
        "note": "heart", "role": "trace", "texture": "diffusion",
        "mw": 117.15, "vp": 0.01, "clogp": 2.14,
        "synergies": ["Benzyl Acetate", "Hedione", "Jasmine FO"],
        "dilution": 0.1,
    },
    "Bourgeonal": {
        "character": {"floral": 6, "freshness": 4, "green": 3, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 176.25, "vp": 0.01, "clogp": 2.9,
        "synergies": ["Lilyreal ND", "Hydroxycitronellal", "DBCA"],
    },
    "Freesia HDI": {
        "character": {"floral": 5, "green": 5, "freshness": 4},
        "note": "heart", "role": "modifier", "texture": "veil",
        "mw": 170.25, "vp": 0.02, "clogp": 2.8,
        "synergies": ["Paradisamide", "Lilyreal ND", "DBCA"],
    },
    "Lilyreal ND": {
        "character": {"floral": 7, "freshness": 3, "sweetness": 1, "powdery": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 192.30, "vp": 0.01, "clogp": 3.5,
        "synergies": ["Bourgeonal", "Freesia HDI", "DBCA", "Hydroxycitronellal"],
    },
    "Helional": {
        "character": {"freshness": 5, "green": 4, "floral": 4, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "lift",
        "mw": 192.21, "vp": 0.01, "clogp": 1.7,
        "synergies": ["Hedione", "Cyclamen Aldehyde"],
    },
    "Heliotropin Fleuressence": {
        "character": {"sweetness": 6, "floral": 5, "powdery": 4, "warmth": 3, "creamy": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 150.13, "vp": 0.003, "clogp": 0.87,
        "synergies": ["Vanillin", "Coumarin", "Benzyl Benzoate"],
    },
    # Heliotropal (piperonal): benzodioxole aldehyde, MW 150.13.
    # Lower VP than Heliotropin → deeper fixative, less volatile.
    # OR5A1/OR5A2 receptor target → sweet-powdery-almond subliminal warmth.
    "Heliotropal": {
        "character": {"sweetness": 5, "powdery": 6, "floral": 4, "warmth": 4, "creamy": 3},
        "note": "base", "role": "modifier", "texture": "cushion",
        "mw": 150.13, "vp": 0.001, "clogp": 0.87,
        "synergies": ["Heliotropin Fleuressence", "Vanillin", "Coumarin", "Alpha Irone"],
    },
    "Petitgrain EO": {
        "character": {"freshness": 6, "green": 5, "floral": 3, "woody": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 1.0, "clogp": 2.8,
        "synergies": ["Neroli EO", "Bergamot FCF", "Linalool"],
    },
    "Neroli EO": {
        "character": {"floral": 7, "freshness": 6, "sweetness": 2, "green": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 1.2, "clogp": 2.5,
        "synergies": ["Petitgrain EO", "Bergamot FCF", "Linalool", "Hedione"],
    },

    # ═══════════════════════ IRIS / VIOLET ═══════════════════════
    "Alpha Irone": {
        "character": {"powdery": 8, "floral": 6, "woody": 4, "creamy": 5},
        "note": "heart", "role": "character", "texture": "halo",
        "mw": 206.33, "vp": 0.005, "clogp": 3.8,
        "synergies": ["Orivone", "Ultralia", "Cashmeran", "Suederal"],
        "dilution": 0.1,
    },
    "Alpha Ionone": {
        "character": {"floral": 5, "powdery": 4, "woody": 3, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 192.30, "vp": 0.02, "clogp": 3.86,
        "synergies": ["Beta Ionone", "Parmavert", "Alpha Irone"],
    },
    "Beta Ionone": {
        "character": {"floral": 4, "woody": 5, "powdery": 3, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 192.30, "vp": 0.02, "clogp": 4.42,
        "synergies": ["Alpha Ionone", "Parmavert", "Cedarwood EO"],
    },
    "Allyl Ionone": {
        "character": {"floral": 4, "powdery": 4, "woody": 4, "green": 3},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 218.33, "vp": 0.01, "clogp": 4.2,
        "synergies": ["Alpha Ionone", "Beta Ionone"],
    },
    "Irotyl": {
        "character": {"powdery": 6, "woody": 4, "floral": 3},
        "note": "heart", "role": "modifier", "texture": "halo",
        "mw": 206.33, "vp": 0.005, "clogp": 3.5,
        "synergies": ["Alpha Irone", "Orivone"],
    },
    "Dihydro Beta Ionone": {
        "character": {"woody": 5, "powdery": 3, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 194.31, "vp": 0.02, "clogp": 4.5,
        "synergies": ["Beta Ionone", "Cedarwood EO"],
    },
    "Alpha-Isomethyl Ionone": {
        "character": {"floral": 6, "powdery": 5, "woody": 3, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 206.33, "vp": 0.008, "clogp": 4.1,
        "synergies": ["Alpha Irone", "Orivone", "Hedione"],
    },
    "Orivone": {
        "character": {"powdery": 7, "creamy": 6, "warmth": 4, "woody": 3, "floral": 3},
        "note": "heart", "role": "character", "texture": "cushion",
        "mw": 206.33, "vp": 0.003, "clogp": 3.5,
        "synergies": ["Alpha Irone", "Ultralia", "Cashmeran"],
    },
    "Ultralia": {
        "character": {"powdery": 6, "floral": 3, "freshness": 2, "creamy": 2},
        "note": "heart", "role": "trace", "texture": "halo",
        "mw": 222.37, "vp": 0.002, "clogp": 4.0,
        "synergies": ["Alpha Irone", "Orivone", "Iso E Super"],
    },
    "I-IRIS F-TEC": {
        "character": {"powdery": 7, "floral": 5, "woody": 3, "creamy": 4},
        "note": "heart", "role": "character", "texture": "halo",
        "mw": 200.0, "vp": 0.005, "clogp": 3.5,
        "synergies": ["Alpha Irone", "Orivone"],
    },
    "Orris F-TEC": {
        "character": {"powdery": 8, "creamy": 5, "woody": 4, "floral": 4},
        "note": "heart", "role": "character", "texture": "halo",
        "mw": 200.0, "vp": 0.005, "clogp": 3.5,
        "synergies": ["Alpha Irone", "Orivone", "Suederal"],
    },
    "Violet Fleuressence": {
        "character": {"powdery": 6, "floral": 5, "sweetness": 3, "green": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 190.0, "vp": 0.01, "clogp": 3.0,
        "synergies": ["Alpha Ionone", "Beta Ionone"],
    },
    "Carrot Seed EO": {
        "character": {"woody": 5, "green": 4, "powdery": 3, "warmth": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 220.0, "vp": 0.01, "clogp": 3.5,
        "synergies": ["Alpha Irone", "Vetiver EO"],
    },

    # ═══════════════════════ WOODS / AMBER / STRUCTURE ═══════════════════════
    "Iso E Super": {
        "character": {"woody": 8, "warmth": 4, "radiance": 6, "creamy": 3},
        "note": "base", "role": "volume", "texture": "cocoon",
        "mw": 234.38, "vp": 0.003, "clogp": 4.73,
        "synergies": ["Hedione", "Ambrox Super", "Cashmeran", "Vertofix Coeur"],
    },
    "Cashmeran": {
        "character": {"warmth": 7, "woody": 5, "sweetness": 4, "creamy": 5, "powdery": 3},
        "note": "base", "role": "volume", "texture": "cocoon",
        "mw": 192.30, "vp": 0.01, "clogp": 3.6,
        "synergies": ["Iso E Super", "Alpha Irone", "Orivone"],
        "dilution": 0.2,
    },
    "Cedramber": {
        "character": {"woody": 7, "freshness": 3, "warmth": 2},
        "note": "base", "role": "modifier", "texture": "veil",
        "mw": 234.38, "vp": 0.002, "clogp": 5.0,
        "synergies": ["Iso E Super", "Clearwood"],
    },
    "Cedamber": {
        "character": {"woody": 6, "warmth": 3, "sweetness": 2},
        "note": "base", "role": "modifier", "texture": "veil",
        "mw": 234.38, "vp": 0.002, "clogp": 5.0,
        "synergies": ["Cedramber", "Iso E Super"],
        "dilution": 0.1,
    },
    "Ambermax": {
        "character": {"warmth": 7, "sweetness": 4, "woody": 3, "powdery": 2},
        "note": "base", "role": "volume", "texture": "cushion",
        "mw": 234.0, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Ambrox Super", "Labdanum Absolute"],
    },
    "Amber Xtreme": {
        "character": {"warmth": 8, "woody": 4, "sweetness": 3, "radiance": 3},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 236.0, "vp": 0.001, "clogp": 4.5,
        "synergies": ["Ambrox Super", "Iso E Super"],
    },
    "Amber Core": {
        "character": {"warmth": 7, "sweetness": 3, "woody": 3},
        "note": "base", "role": "modifier", "texture": "cushion",
        "mw": 230.0, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Ambrox Super", "Labdanum Absolute"],
        "dilution": 0.1,
    },
    "Amber Core Accord": {
        "character": {"warmth": 7, "sweetness": 4, "woody": 3, "powdery": 2},
        "note": "base", "role": "volume", "texture": "cushion",
        "mw": 230.0, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Ambrox Super", "Vanillin"],
    },
    "Ambrox Super": {
        "character": {"warmth": 6, "woody": 5, "radiance": 5, "animalic": 3, "powdery": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 236.40, "vp": 0.0003, "clogp": 4.92,
        "synergies": ["Iso E Super", "Cashmeran", "Hedione"],
        "dilution": 0.3,
    },
    "Ambrofix": {
        "character": {"warmth": 5, "woody": 4, "radiance": 4, "animalic": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 236.40, "vp": 0.0003, "clogp": 4.9,
        "synergies": ["Ambrettolide", "Iso E Super"],
        "dilution": 0.1,
    },
    "Kephalis": {
        "character": {"woody": 9, "warmth": 5, "radiance": 3},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 234.38, "vp": 0.001, "clogp": 5.2,
        "synergies": ["Iso E Super", "Vertofix Coeur", "Timberol"],
    },
    "Bacdanol": {
        "character": {"woody": 5, "creamy": 7, "warmth": 4, "sweetness": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 210.36, "vp": 0.001, "clogp": 3.8,
        "synergies": ["Javanol", "Ebanol", "Sandalore"],
    },
    "Ebanol": {
        "character": {"woody": 5, "creamy": 8, "warmth": 3, "sweetness": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 220.35, "vp": 0.001, "clogp": 4.5,
        "synergies": ["Javanol", "Bacdanol"],
    },
    "Sandalore": {
        "character": {"woody": 5, "creamy": 6, "warmth": 3, "sweetness": 2},
        "note": "base", "role": "modifier", "texture": "skin-effect",
        "mw": 210.36, "vp": 0.001, "clogp": 4.2,
        "synergies": ["Javanol", "Bacdanol", "Ebanol"],
    },
    "Vetival": {
        "character": {"woody": 6, "green": 3, "animalic": 3, "smoky": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 218.33, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Vetiver EO", "Iso E Super"],
    },
    "Vertofix Coeur": {
        "character": {"woody": 8, "warmth": 4, "creamy": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 234.38, "vp": 0.0005, "clogp": 5.2,
        "synergies": ["Iso E Super", "Patchouli EO", "Evernyl"],
    },
    "Vertofix": {
        "character": {"woody": 7, "warmth": 3, "creamy": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 234.38, "vp": 0.0005, "clogp": 5.0,
        "synergies": ["Vertofix Coeur", "Iso E Super"],
    },
    "Suederal": {
        "character": {"animalic": 5, "woody": 4, "warmth": 3, "creamy": 3},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 168.28, "vp": 0.01, "clogp": 3.0,
        "synergies": ["Alpha Irone", "Cashmeran", "Iso E Super"],
        "dilution": 0.1,
    },
    "Javanol": {
        "character": {"woody": 5, "creamy": 8, "warmth": 4, "sweetness": 2, "radiance": 3},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 210.36, "vp": 0.001, "clogp": 3.5,
        "synergies": ["Ambrox Super", "Cashmeran", "Bacdanol", "Ebanol"],
    },
    "Amberwood F": {
        "character": {"woody": 6, "warmth": 5, "sweetness": 2},
        "note": "base", "role": "modifier", "texture": "cocoon",
        "mw": 234.0, "vp": 0.001, "clogp": 4.5,
        "synergies": ["Iso E Super", "Ambrox Super"],
    },
    "Timberol": {
        "character": {"woody": 8, "freshness": 2, "warmth": 2},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 210.36, "vp": 0.002, "clogp": 4.1,
        "synergies": ["Kephalis", "Cedarwood EO", "Iso E Super"],
    },
    "Koavone": {
        "character": {"woody": 7, "warmth": 4, "sweetness": 2},
        "note": "base", "role": "modifier", "texture": "cocoon",
        "mw": 206.33, "vp": 0.002, "clogp": 4.0,
        "synergies": ["Cedarwood EO", "Timberol"],
    },
    "Cedarwood EO": {
        "character": {"woody": 8, "warmth": 2, "sweetness": 1},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 222.37, "vp": 0.005, "clogp": 4.9,
        "synergies": ["Iso E Super", "Vertofix Coeur", "Vetiver EO"],
    },
    "Cedarwood oil Virginia": {
        "character": {"woody": 8, "warmth": 3, "sweetness": 1, "smoky": 1},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 222.37, "vp": 0.005, "clogp": 5.0,
        "synergies": ["Cedarwood EO", "Iso E Super"],
    },
    "Vetiver EO": {
        "character": {"woody": 7, "green": 5, "smoky": 3, "animalic": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 222.37, "vp": 0.003, "clogp": 4.5,
        "synergies": ["Iso E Super", "Vetival", "Patchouli EO"],
    },
    "Clearwood": {
        "character": {"woody": 6, "freshness": 3, "warmth": 2},
        "note": "base", "role": "modifier", "texture": "veil",
        "mw": 222.37, "vp": 0.002, "clogp": 4.3,
        "synergies": ["Cedramber", "Iso E Super", "Patchouli EO"],
    },

    # ═══════════════════════ MUSKS ═══════════════════════
    "Galaxolide": {
        "character": {"sweetness": 4, "warmth": 3, "powdery": 3, "radiance": 3, "floral": 1},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 258.40, "vp": 0.0001, "clogp": 5.9,
        "synergies": ["Habanolide", "Ambrettolide", "Iso E Super"],
        "dilution": 0.8,
    },
    "Tonalide": {
        "character": {"sweetness": 5, "warmth": 3, "powdery": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 258.40, "vp": 0.0001, "clogp": 5.7,
        "synergies": ["Galaxolide"],
        "dilution": 0.1,
    },
    "Ambrettolide": {
        "character": {"animalic": 3, "warmth": 4, "creamy": 5, "sweetness": 2, "radiance": 3},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 252.39, "vp": 0.0001, "clogp": 6.8,
        "synergies": ["Galaxolide", "Habanolide", "Javanol"],
        "dilution": 0.1,
    },
    "Habanolide": {
        "character": {"freshness": 4, "warmth": 2, "powdery": 3, "radiance": 3},
        "note": "base", "role": "fixative", "texture": "veil",
        "mw": 238.37, "vp": 0.0002, "clogp": 5.5,
        "synergies": ["Galaxolide", "Ambrettolide", "Iso E Super"],
    },
    "Zenolide": {
        "character": {"freshness": 3, "sweetness": 3, "warmth": 2, "powdery": 3},
        "note": "base", "role": "modifier", "texture": "veil",
        "mw": 254.41, "vp": 0.0001, "clogp": 6.0,
        "synergies": ["Galaxolide", "Habanolide"],
    },
    "Exaltolide": {
        "character": {"sweetness": 4, "warmth": 3, "powdery": 4, "animalic": 2},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 240.38, "vp": 0.0001, "clogp": 5.3,
        "synergies": ["Galaxolide", "Ambrettolide"],
        "dilution": 0.1,
    },
    "Macrolide": {
        "character": {"freshness": 2, "sweetness": 2, "warmth": 3, "animalic": 3},
        "note": "base", "role": "modifier", "texture": "skin-effect",
        "mw": 254.41, "vp": 0.0001, "clogp": 6.5,
        "synergies": ["Ambrettolide", "Galaxolide"],
        "dilution": 0.1,
    },
    "Musk Ketone": {
        "character": {"sweetness": 4, "warmth": 3, "powdery": 5, "animalic": 2},
        "note": "base", "role": "fixative", "texture": "halo",
        "mw": 294.26, "vp": 0.00001, "clogp": 3.0,
        "synergies": ["Galaxolide", "Vanillin"],
        "dilution": 0.1,
    },

    # ═══════════════════════ SWEET / GOURMAND / BALSAMIC ═══════════════════════
    "Ethyl Maltol": {
        "character": {"sweetness": 10, "warmth": 4, "creamy": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 140.14, "vp": 0.001, "clogp": 0.03,
        "synergies": ["Vanillin", "Coumarin", "Benzoin Resinoid"],
        "dilution": 0.1,
    },
    "Coumarin": {
        "character": {"sweetness": 6, "warmth": 6, "powdery": 5, "creamy": 2},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 146.14, "vp": 0.001, "clogp": 1.39,
        "synergies": ["Vanillin", "Lavender EO", "Tonka Bean FO"],
        "dilution": 0.2,
    },
    "Vanillin": {
        "character": {"sweetness": 9, "warmth": 6, "creamy": 5, "powdery": 2},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 152.15, "vp": 0.0003, "clogp": 1.21,
        "synergies": ["Ethyl Vanillin", "Coumarin", "Benzoin Resinoid", "Ethyl Maltol"],
        "dilution": 0.1,
    },
    "Ethyl Vanillin": {
        "character": {"sweetness": 10, "warmth": 5, "creamy": 5, "powdery": 2},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 166.17, "vp": 0.0002, "clogp": 1.58,
        "synergies": ["Vanillin", "Benzoin Resinoid"],
    },
    "Maple Lactone": {
        "character": {"sweetness": 8, "warmth": 5, "creamy": 6},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 128.13, "vp": 0.01, "clogp": 0.1,
        "synergies": ["Vanillin", "Coumarin", "Ethyl Maltol"],
        "dilution": 0.2,
    },
    "Raspberry Ketone": {
        "character": {"sweetness": 7, "floral": 3, "freshness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 164.20, "vp": 0.001, "clogp": 1.5,
        "synergies": ["Gamma Decalactone", "Ethyl Maltol"],
    },
    "Benzoin Resinoid": {
        "character": {"sweetness": 7, "warmth": 7, "creamy": 4, "smoky": 2},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 212.24, "vp": 0.0001, "clogp": 2.5,
        "synergies": ["Vanillin", "Labdanum Absolute", "Styrax FTEC"],
        "dilution": 0.5,
    },
    "Benzoin Sumatra Resinoid": {
        "character": {"sweetness": 7, "warmth": 6, "creamy": 4, "smoky": 3},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 212.24, "vp": 0.0001, "clogp": 2.5,
        "synergies": ["Vanillin", "Labdanum Absolute"],
        "dilution": 0.1,
    },
    "Labdanum Absolute": {
        "character": {"warmth": 8, "animalic": 4, "sweetness": 4, "woody": 3, "smoky": 2},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 304.47, "vp": 0.00001, "clogp": 5.0,
        "synergies": ["Benzoin Resinoid", "Ambrox Super", "Vanillin"],
        "dilution": 0.1,
    },
    "Labdanum": {
        "character": {"warmth": 7, "animalic": 3, "sweetness": 3, "woody": 3},
        "note": "base", "role": "fixative", "texture": "cocoon",
        "mw": 300.0, "vp": 0.00001, "clogp": 5.0,
        "synergies": ["Labdanum Absolute", "Benzoin Resinoid"],
    },
    "Anisaldehyde": {
        "character": {"sweetness": 6, "floral": 3, "warmth": 2, "spicy": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 136.15, "vp": 0.04, "clogp": 1.76,
        "synergies": ["Vanillin", "Heliotropin Fleuressence"],
    },
    "Gamma Decalactone": {
        "character": {"sweetness": 5, "creamy": 7, "warmth": 2, "floral": 2},
        "note": "heart", "role": "character", "texture": "cushion",
        "mw": 170.25, "vp": 0.005, "clogp": 2.9,
        "synergies": ["Gamma Undecalactone", "Raspberry Ketone", "Vanillin"],
    },
    "Gamma Undecalactone": {
        "character": {"sweetness": 5, "creamy": 8, "warmth": 2},
        "note": "heart", "role": "character", "texture": "cushion",
        "mw": 184.28, "vp": 0.002, "clogp": 3.4,
        "synergies": ["Gamma Decalactone", "Vanillin"],
    },
    "Delta Decalactone": {
        "character": {"sweetness": 4, "creamy": 8, "warmth": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 170.25, "vp": 0.003, "clogp": 2.5,
        "synergies": ["Gamma Decalactone", "Vanillin"],
    },
    "Allyl Amyl Glycolate": {
        "character": {"green": 5, "freshness": 7, "sweetness": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 158.19, "vp": 0.2, "clogp": 1.5,
        "synergies": ["Hedione", "Floralozone", "Methyl Pamplemousse"],
    },

    # ═══════════════════════ LEATHER / SMOKY / PHENOLIC ═══════════════════════
    "Isobutyl Quinoline": {
        "character": {"animalic": 7, "smoky": 4, "woody": 2, "warmth": 2},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 185.27, "vp": 0.005, "clogp": 3.5,
        "synergies": ["Styrax FTEC", "Birch Tar Rectified", "Suederal"],
        "dilution": 0.1,
    },
    "Birch Tar Rectified": {
        "character": {"smoky": 9, "animalic": 5, "woody": 3, "warmth": 2},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 124.14, "vp": 0.01, "clogp": 1.5,
        "synergies": ["Guaiacol", "Styrax FTEC", "Isobutyl Quinoline"],
        "avoid": ["Floralozone", "Calone"],
    },
    "Styrax FTEC": {
        "character": {"smoky": 6, "sweetness": 4, "warmth": 5, "animalic": 3},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 200.0, "vp": 0.005, "clogp": 2.5,
        "synergies": ["Benzoin Resinoid", "Birch Tar Rectified", "Labdanum Absolute"],
    },
    "Guaiacol": {
        "character": {"smoky": 8, "animalic": 4, "warmth": 3, "spicy": 2},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 124.14, "vp": 0.02, "clogp": 1.32,
        "synergies": ["Birch Tar Rectified", "Eugenol", "Isobutyl Quinoline"],
    },
    "Evernyl": {
        "character": {"woody": 5, "green": 4, "animalic": 3, "smoky": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 196.20, "vp": 0.001, "clogp": 2.1,
        "synergies": ["Patchouli EO", "Vertofix Coeur", "Coumarin"],
    },

    # ═══════════════════════ SPICE / AROMATIC ═══════════════════════
    "Black Pepper FTEC": {
        "character": {"spicy": 8, "warmth": 4, "woody": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 204.35, "vp": 0.1, "clogp": 3.5,
        "synergies": ["Pink Pepper Base", "Cardamom FTEC"],
    },
    "Black Pepper materials": {
        "character": {"spicy": 7, "warmth": 3, "woody": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 204.35, "vp": 0.1, "clogp": 3.5,
        "synergies": ["Black Pepper FTEC"],
    },
    "Cardamom FTEC": {
        "character": {"spicy": 7, "freshness": 4, "warmth": 3, "woody": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.25, "vp": 0.5, "clogp": 2.5,
        "synergies": ["Black Pepper FTEC", "Alpha Irone", "Bergamot FCF"],
        "dilution": 0.1,
    },
    "Pink Pepper Base": {
        "character": {"spicy": 6, "freshness": 4, "sweetness": 2, "floral": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 136.23, "vp": 0.3, "clogp": 3.0,
        "synergies": ["Black Pepper FTEC", "Bergamot FCF"],
    },
    "Ethyl Safranate": {
        "character": {"spicy": 7, "warmth": 5, "woody": 2, "sweetness": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 168.23, "vp": 0.05, "clogp": 2.5,
        "synergies": ["Labdanum Absolute", "Benzoin Resinoid", "Alpha Irone"],
    },
    "Eugenol": {
        "character": {"spicy": 8, "warmth": 5, "sweetness": 2, "smoky": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 164.20, "vp": 0.01, "clogp": 2.49,
        "synergies": ["Isoeugenol", "Cinnamaldehyde", "Vanillin"],
    },
    "Isoeugenol": {
        "character": {"spicy": 6, "warmth": 5, "sweetness": 3, "floral": 3},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 164.20, "vp": 0.005, "clogp": 2.58,
        "synergies": ["Eugenol", "Vanillin"],
    },
    "Cinnamaldehyde": {
        "character": {"spicy": 9, "warmth": 6, "sweetness": 3},
        "note": "heart", "role": "character", "texture": "lift",
        "mw": 132.16, "vp": 0.05, "clogp": 1.9,
        "synergies": ["Eugenol", "Vanillin", "Coumarin"],
    },
    "Lavender EO": {
        "character": {"freshness": 6, "floral": 5, "green": 4, "woody": 2, "spicy": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 170.0, "vp": 0.5, "clogp": 2.5,
        "synergies": ["Linalyl Acetate", "Coumarin", "Geraniol", "Terpinyl Acetate"],
    },
    "Patchouli EO": {
        "character": {"woody": 7, "warmth": 4, "animalic": 3, "sweetness": 2, "green": 2},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 222.37, "vp": 0.001, "clogp": 4.5,
        "synergies": ["Evernyl", "Vertofix Coeur", "Vetiver EO"],
    },
    "Myrrh EO": {
        "character": {"warmth": 6, "smoky": 4, "sweetness": 3, "woody": 3, "animalic": 2},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 222.37, "vp": 0.001, "clogp": 3.5,
        "synergies": ["Olibanum Resinoid", "Labdanum Absolute"],
    },
    "Olibanum Resinoid": {
        "character": {"smoky": 5, "warmth": 5, "spicy": 3, "woody": 3, "freshness": 2},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 220.0, "vp": 0.002, "clogp": 3.0,
        "synergies": ["Myrrh EO", "Labdanum Absolute", "Benzoin Resinoid"],
    },

    # ═══════════════════════ ACCORD BASES / FTECs / OTHER ═══════════════════════
    "Blackcurrant FTEC": {
        "character": {"green": 5, "sweetness": 4, "animalic": 3, "freshness": 3},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 180.0, "vp": 0.1, "clogp": 2.5,
        "synergies": ["Hedione", "Beta Ionone"],
    },
    "Dewberry FTEC": {
        "character": {"sweetness": 5, "freshness": 4, "floral": 3},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 180.0, "vp": 0.1, "clogp": 2.0,
        "synergies": ["Hedione", "Gamma Decalactone"],
    },
    "Jasmine FO": {
        "character": {"floral": 7, "sweetness": 4, "animalic": 2, "warmth": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 200.0, "vp": 0.01, "clogp": 3.0,
        "synergies": ["Hedione", "Benzyl Acetate", "Indole"],
    },
    "Leather FO": {
        "character": {"animalic": 6, "smoky": 5, "woody": 3, "warmth": 3},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 200.0, "vp": 0.005, "clogp": 3.0,
        "synergies": ["Isobutyl Quinoline", "Birch Tar Rectified"],
    },
    "Tonka Bean FO": {
        "character": {"sweetness": 7, "warmth": 5, "powdery": 4, "creamy": 3},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 180.0, "vp": 0.001, "clogp": 2.0,
        "synergies": ["Coumarin", "Vanillin", "Benzoin Resinoid"],
    },
    "Sandalwood FO": {
        "character": {"woody": 6, "creamy": 6, "warmth": 4, "sweetness": 2},
        "note": "base", "role": "modifier", "texture": "skin-effect",
        "mw": 210.0, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Javanol", "Bacdanol"],
    },
    "Melonal": {
        "character": {"green": 6, "freshness": 6, "sweetness": 2},
        "note": "top", "role": "modifier", "texture": "lift",
        "mw": 156.22, "vp": 0.5, "clogp": 2.5,
        "synergies": ["Floralozone", "Hedione"],
    },
    "Paradisamide": {
        "character": {"tropical": 8, "citrus": 6, "green": 5, "fruity": 7, "freshness": 5},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 215.0, "vp": 0.002, "clogp": 2.5,
        # Givaudan GF: guava/passion-fruit/grapefruit/rhubarb/cassis; 150hr strip life; impact 150
        # Typical use 0.1-1%, max 10%; long-lasting tropical-fruity modifier NOT a muguet material
        "synergies": ["Methyl Pamplemousse", "Blood Orange Sicilian", "Grapefruit FCF", "Hedione"],
    },
    "DBCA": {
        "character": {"floral": 7, "sweetness": 3, "freshness": 2, "powdery": 2, "creamy": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 204.27, "vp": 0.005, "clogp": 3.2,
        "synergies": ["Paradisamide", "Benzyl Salicylate", "Freesia HDI", "Lilyreal ND"],
    },
    "Methyl Nonyl Ketone": {
        "character": {"freshness": 3, "green": 4, "woody": 2, "sweetness": 1},
        "note": "heart", "role": "modifier", "texture": "veil",
        "mw": 170.29, "vp": 0.05, "clogp": 3.5,
        "synergies": ["Floralozone"],
    },

    # ═══════════════════════ ADDITIONAL MATERIALS ═══════════════════════
    "Bergamot FCF Sicilian": {
        "character": {"freshness": 8, "sweetness": 2, "green": 3, "floral": 2, "warmth": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 136.23, "vp": 2.5, "clogp": 2.8,
        "synergies": ["Hedione", "Neroli EO", "Linalool"],
    },
    "Blood Orange Sicilian": {
        "character": {"freshness": 7, "sweetness": 4, "warmth": 2, "green": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 136.23, "vp": 3.0, "clogp": 3.5,
        "synergies": ["Red Mandarin EO", "Bergamot FCF"],
    },
    "Cedrat FCF Sicilian": {
        "character": {"freshness": 8, "green": 4, "woody": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 152.23, "vp": 2.0, "clogp": 2.7,
        "synergies": ["Grapefruit FCF", "Scentenal", "Hedione"],
    },
    "Methyl Ionone": {
        "character": {"floral": 5, "powdery": 6, "woody": 3, "sweetness": 2},
        "note": "heart", "role": "character", "texture": "cushion",
        "mw": 206.33, "vp": 0.01, "clogp": 3.8,
        "synergies": ["Alpha Irone", "Orivone", "Cashmeran"],
    },
    "Norlimbanol Dextro": {
        "character": {"woody": 9, "warmth": 3, "animalic": 1},
        "note": "base", "role": "character", "texture": "cocoon",
        "mw": 224.38, "vp": 0.001, "clogp": 5.2,
        "synergies": ["Iso E Super", "Cedarwood EO", "Vertofix Coeur"],
    },
    "Romandolide": {
        "character": {"sweetness": 3, "freshness": 4, "warmth": 2, "powdery": 2, "radiance": 4},
        "note": "base", "role": "fixative", "texture": "veil",
        "mw": 256.38, "vp": 0.0001, "clogp": 5.5,
        "synergies": ["Galaxolide", "Ambrettolide", "Habanolide"],
    },
    "Apritone": {
        "character": {"sweetness": 6, "freshness": 4, "green": 2, "warmth": 3, "floral": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 178.27, "vp": 0.05, "clogp": 3.2,
        "synergies": ["Hedione", "Methyl Pamplemousse", "Cedrat FCF Sicilian"],
        "dilution": 0.1,
    },
    "Lemonile": {
        "character": {"freshness": 9, "green": 3, "sweetness": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 151.23, "vp": 0.2, "clogp": 2.8,
        "synergies": ["Bergamot FCF", "Petitgrain EO", "Clary Sage EO"],
    },
    "Orange Peel EO": {
        "character": {"freshness": 8, "sweetness": 3, "green": 1},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 136.23, "vp": 1.9, "clogp": 4.57,
        "synergies": ["D-Limonene", "Bergamot FCF", "Petitgrain EO"],
    },
    "Ylang Comoros Complete EO F3255": {
        "character": {"floral": 8, "sweetness": 5, "warmth": 4, "creamy": 3},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 200.0, "vp": 0.05, "clogp": 3.0,
        "synergies": ["Methyl Benzoate", "Benzyl Salicylate", "Hedione"],
    },
    "Ylang Comoros III EO F3295": {
        "character": {"floral": 7, "sweetness": 4, "warmth": 3, "creamy": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 200.0, "vp": 0.03, "clogp": 3.2,
        "synergies": ["Ylang Comoros Complete EO F3255", "Hedione"],
    },
    "Champaca Flower EO": {
        "character": {"floral": 7, "sweetness": 4, "warmth": 4, "spicy": 2, "creamy": 2},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 200.0, "vp": 0.03, "clogp": 3.0,
        "synergies": ["Methyl Benzoate", "Jasmine FO", "Benzyl Salicylate"],
    },
    "Methyl Benzoate": {
        "character": {"floral": 6, "sweetness": 2, "freshness": 1},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 136.15, "vp": 0.4, "clogp": 2.12,
        "synergies": ["Ylang Comoros Complete EO F3255", "Cis Jasmone", "Jasmine FO"],
    },
    "Cis Jasmone": {
        "character": {"floral": 6, "green": 4, "sweetness": 2},
        "note": "heart", "role": "modifier", "texture": "diffusion",
        "mw": 164.24, "vp": 0.02, "clogp": 2.78,
        "synergies": ["Hedione", "Methyl Benzoate", "Jasmine FO"],
    },
    "Methyl Salicylate": {
        "character": {"freshness": 5, "green": 4, "floral": 3, "sweetness": 1},
        "note": "heart", "role": "modifier", "texture": "veil",
        "mw": 152.15, "vp": 5.3, "clogp": 2.55,
        "synergies": ["Benzyl Salicylate", "Clary Sage EO", "Lavender EO"],
    },
    "Methyl Anthranilate": {
        "character": {"floral": 6, "sweetness": 4, "warmth": 2, "animalic": 1},
        "note": "heart", "role": "modifier", "texture": "cushion",
        "mw": 151.16, "vp": 0.03, "clogp": 1.88,
        "synergies": ["Neroli EO", "Orange Blossom", "Petitgrain EO"],
    },
    "Ethylene Brassylate": {
        "character": {"powdery": 4, "creamy": 4, "warmth": 2, "floral": 2},
        "note": "base", "role": "fixative", "texture": "veil",
        "mw": 270.37, "vp": 0.0005, "clogp": 3.89,
        "synergies": ["Galaxolide", "Habanolide", "Cashmeran"],
    },
    "Siam Benzoin": {
        "character": {"sweetness": 7, "warmth": 7, "creamy": 4, "smoky": 1},
        "note": "base", "role": "fixative", "texture": "cushion",
        "mw": 212.24, "vp": 0.0001, "clogp": 2.5,
        "synergies": ["Vanillin", "Labdanum Absolute", "Coumarin"],
        "dilution": 0.5,
    },
    "Clary Sage EO": {
        "character": {"green": 5, "freshness": 4, "spicy": 3, "woody": 2},
        "note": "top", "role": "character", "texture": "lift",
        "mw": 196.29, "vp": 0.07, "clogp": 3.5,
        "synergies": ["Lemonile", "Lavender EO", "Petitgrain EO"],
    },
    "Rose Absolute": {
        "character": {"floral": 8, "sweetness": 4, "green": 2, "warmth": 1},
        "note": "heart", "role": "character", "texture": "veil",
        "mw": 220.0, "vp": 0.02, "clogp": 3.5,
        "synergies": ["Geraniol", "Citronellol", "Phenethyl Alcohol", "Hedione"],
    },
    "Jasmine Absolute": {
        "character": {"floral": 8, "sweetness": 4, "animalic": 3, "green": 1},
        "note": "heart", "role": "character", "texture": "diffusion",
        "mw": 200.0, "vp": 0.01, "clogp": 3.0,
        "synergies": ["Hedione", "Benzyl Acetate", "Indole", "Methyl Benzoate"],
    },
    "Cypriol EO": {
        "character": {"woody": 7, "smoky": 5, "spicy": 3, "green": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 220.0, "vp": 0.005, "clogp": 4.0,
        "synergies": ["Oud Oil", "Georgywood", "Vetiver EO", "Patchouli EO"],
    },
    "Georgywood": {
        "character": {"woody": 8, "warmth": 3, "radiance": 3, "smoky": 1},
        "note": "base", "role": "character", "texture": "diffusion",
        "mw": 218.34, "vp": 0.001, "clogp": 5.0,
        "synergies": ["Oud Oil", "Cypriol EO", "Iso E Super", "Ambrox Super"],
    },
    "Orris Butter Absolute": {
        "character": {"powdery": 9, "creamy": 5, "floral": 4, "woody": 2},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 206.33, "vp": 0.005, "clogp": 3.8,
        "synergies": ["Alpha Irone", "Methyl Ionone", "Hedione", "Sandalwood EO"],
    },
    "Oud Oil": {
        "character": {"woody": 8, "smoky": 5, "animalic": 3, "warmth": 4, "spicy": 2},
        "note": "base", "role": "character", "texture": "skin-effect",
        "mw": 222.37, "vp": 0.001, "clogp": 4.5,
        "synergies": ["Cypriol EO", "Georgywood", "Rose Absolute", "Sandalwood EO"],
    },
    "Rum Absolute": {
        "character": {"warmth": 6, "sweetness": 5, "spicy": 2, "smoky": 1},
        "note": "heart", "role": "modifier", "texture": "veil",
        "mw": 150.0, "vp": 0.01, "clogp": 1.5,
        "synergies": ["Vanillin", "Coumarin", "Patchouli EO", "Labdanum Absolute"],
    },
    "Sandalwood EO": {
        "character": {"woody": 7, "creamy": 7, "warmth": 4},
        "note": "base", "role": "character", "texture": "cushion",
        "mw": 220.0, "vp": 0.001, "clogp": 4.0,
        "synergies": ["Rose Absolute", "Orris Butter Absolute", "Javanol", "Benzyl Salicylate"],
    },
    "Castoreum Base": {
        "character": {"animalic": 7, "smoky": 4, "warmth": 4, "woody": 2},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 200.0, "vp": 0.001, "clogp": 3.0,
        "synergies": ["Civet Reconstitution Base", "Isobutyl Quinoline", "Oud Oil"],
        "dilution": 0.1,
    },
    "Civet Reconstitution Base": {
        "character": {"animalic": 8, "warmth": 4, "sweetness": 1},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 200.0, "vp": 0.001, "clogp": 3.0,
        "synergies": ["Castoreum Base", "Indole", "Skatole", "Jasmine Absolute"],
        "dilution": 0.1,
    },
    "Skatole": {
        "character": {"animalic": 10, "floral": 2, "sweetness": 1},
        "note": "base", "role": "trace", "texture": "skin-effect",
        "mw": 131.17, "vp": 0.01, "clogp": 2.6,
        "synergies": ["Indole", "Jasmine Absolute", "Civet Reconstitution Base"],
        "dilution": 0.01,
    },
}

# Aliases for common naming variants
_ALIASES = {
    "Dimethyl Benzyl Carbinyl Acetate": "DBCA",
    "Dimethyl Benzyl Carbinyl Acetate (DBCA)": "DBCA",
    "PEA": "Phenethyl Alcohol",
    "Phenyl Ethyl Alcohol": "Phenethyl Alcohol",
    "Ketone V": "Allyl Ionone",
    "Cetone V": "Allyl Ionone",
    "Allyl Ionone (Ketone V)": "Allyl Ionone",
    "Allyl Ionone (Cetone V)": "Allyl Ionone",
    "AIMI": "Alpha-Isomethyl Ionone",
    "Alpha-Isomethyl Ionone (AIMI)": "Alpha-Isomethyl Ionone",
    "IBQ": "Isobutyl Quinoline",
    "Isobutyl Quinoline (10%)": "Isobutyl Quinoline",
    "Ambermax (10%)": "Ambermax",
    "Ambermax (50%)": "Ambermax",
    "Methyl Ionone Pure": "Alpha-Isomethyl Ionone",
    "Alpha Isomethyl Ionone": "Alpha-Isomethyl Ionone",
    "Orris Hexanone": "Orivone",
    "Orris Capronate": "Irotyl",
    "Ambroxide": "Ambrox Super",
    "Ambroxide (Ambrox Super / Ambrofix)": "Ambrox Super",
    "Ambrofix": "Ambrox Super",
    "Cedrat FCF oil Sicilian": "Cedrat FCF Sicilian",
    "Blood Orange oil Sicilian": "Blood Orange Sicilian",
    "Ylang Comoros Complete F3255": "Ylang Comoros Complete EO F3255",
    "Ylang Comoros III F3295": "Ylang Comoros III EO F3295",
    "I-Iris FTEC": "I-IRIS F-TEC",
    "ORRIS FTEC": "Orris F-TEC",
    "Castoreum Base (synthetic reconstitution)": "Castoreum Base",
    "Civet Reconstitution Base (synthetic)": "Civet Reconstitution Base",
    "Cypriol EO (Nagarmotha)": "Cypriol EO",
    "Hedione (Methyl Dihydrojasmonate)": "Hedione",
    "Hedione HC": "Hedione",
    "Jasmine Absolute (J. grandiflorum)": "Jasmine Absolute",
    "Methyl Dihydrojasmonate": "Hedione",
    "Methyl Ionone (α-Isomethyl Ionone)": "Alpha-Isomethyl Ionone",
    "Methyl Ionone (a-Isomethyl Ionone)": "Alpha-Isomethyl Ionone",
    "Orris Butter Absolute (15% α-irone)": "Orris Butter Absolute",
    "Orris Butter Absolute (15% a-irone)": "Orris Butter Absolute",
    "Iris Butter Absolute": "Orris Butter Absolute",
    "Oud Oil (Aquilaria crassna, Laotian plantation)": "Oud Oil",
    "Oud Oil (Assam)": "Oud Oil",
    "Rose Absolute (R. damascena)": "Rose Absolute",
    "Sandalwood": "Sandalwood EO",
    "Sandalwood (East Indian Santalum album)": "Sandalwood EO",
    "Tonka": "Tonka Bean FO",
    "Tonka FO": "Tonka Bean FO",
    "Limonene": "D-Limonene",
    "EB": "Ethylene Brassylate",
    "Vetiver EO (Haitian or Bourbon)": "Vetiver EO",
    "Vetiver EO (Haiti)": "Vetiver EO",
}


# ── Transparency dimension injection (Ellena axis) ──
# Inject "transparency" into character dicts based on material classification.
# 8-10 = highly transparent (sheer, diaphanous), 4-7 = neutral, 0-3 = opaque/dense
_TRANSPARENCY_SCORES: dict[str, int] = {
    # Highly transparent materials (8-10)
    "Hedione": 10, "Iso E Super": 9, "Hexyl Salicylate": 9,
    "Dihydromyrcenol": 9, "Linalool": 8, "Linalyl Acetate": 8,
    "Allyl Amyl Glycolate": 9, "Calone": 8, "Floralozone": 8,
    "Scentenal": 8, "Freesia HDI": 8, "Amberwood F": 8,
    "Habanolide": 8, "Galaxolide": 7, "Cashmeran": 7,
    "DBCA": 8, "Lilyreal ND": 8, "Ultralia": 9,
    # Medium-high (6-7)
    "Bergamot FCF": 7, "Grapefruit FCF": 7, "Cedrat FCF Sicilian": 7,
    "Benzyl Salicylate": 6, "Geraniol": 7, "Phenethyl Alcohol": 6,
    "Hydroxycitronellal": 7, "Bourgeonal": 7, "Ambrox Super": 6,
    "Javanol": 7, "Ebanol": 7, "Musk T": 7,
    # Medium (4-5)
    "Coumarin": 5, "Alpha Irone": 5, "Orivone": 5,
    "Cedarwood Atlas EO": 5, "Cedarwood Virginia EO": 5,
    "Vertofix Coeur": 4, "Kephalis": 4, "Timberol": 5,
    "Ethyl Vanillin": 4, "Eugenol": 4,
    "Lavender EO": 6, "Neroli EO": 6, "Petitgrain EO": 6,
    # Low transparency / opaque (0-3)
    "Patchouli EO": 2, "Rose Absolute": 3, "Labdanum Absolute": 1,
    "Benzoin Resinoid": 2, "Myrrh EO": 2, "Sandalwood EO": 3,
    "Vetiver EO": 3, "Vanillin": 3, "Styrax FTEC": 2,
    "Ylang Comoros Complete EO": 3, "Birch Tar Rectified": 1,
    "Guaiacol": 1, "Indole": 2, "Isobutyl Quinoline": 2,
}

for _name, _score in _TRANSPARENCY_SCORES.items():
    if _name in _PROFILES:
        _PROFILES[_name]["character"].setdefault("transparency", _score)
del _name, _score  # clean up module namespace

# ── Auto-populate ODT from ODT_DATA ──────────────────────────────
# Enrich _PROFILES with odt_air values from the canonical ODT database
# so every MaterialProfile.odt is available without separate lookups.
try:
    from engine.odor_thresholds import ODT_DATA as _ODT_SRC
    from engine.name_utils import normalize_name as _nn

    _odt_index = {_nn(k): v["odt_air"] for k, v in _ODT_SRC.items()}
    for _pname in _PROFILES:
        if "odt" not in _PROFILES[_pname] or _PROFILES[_pname].get("odt") is None:
            _odt_val = _odt_index.get(_nn(_pname))
            if _odt_val is not None:
                _PROFILES[_pname]["odt"] = _odt_val
    del _odt_index, _odt_val, _pname, _ODT_SRC, _nn
except Exception:
    pass  # Graceful fallback: odt stays None if import fails


def _name_variants(name: str) -> list[str]:
    greek_map = str.maketrans({
        "α": "a",
        "β": "b",
        "γ": "g",
        "δ": "d",
        "’": "'",
    })
    clean = name.strip().replace("**", "").translate(greek_map)
    variants: list[str] = []
    seen: set[str] = set()

    def add(value: str):
        value = re.sub(r"\s+", " ", value.strip())
        if value and value not in seen:
            variants.append(value)
            seen.add(value)

    add(clean)
    add(re.sub(r"\s*\([^)]*\)\s*$", "", clean))
    if "(" in clean and ")" not in clean:
        add(clean.split("(", 1)[0])
    if "=" in clean:
        add(clean.split("=", 1)[0])
    return variants


_profile_cache: dict[str, MaterialProfile | None] = {}


def get_profile(name: str) -> MaterialProfile | None:
    """Look up a material profile by name, with alias resolution."""
    if name in _profile_cache:
        return _profile_cache[name]
    result = _get_profile_uncached(name)
    _profile_cache[name] = result
    return result


def _get_profile_uncached(name: str) -> MaterialProfile | None:
    """Internal uncached profile lookup."""
    for candidate in _name_variants(name):
        identity = resolve_material_identity(candidate)
        key = identity.profile_name if identity is not None else None
        if key is None:
            key = _ALIASES.get(candidate)
        if key is None:
            low = candidate.lower()
            for alias, canonical in _ALIASES.items():
                if alias.lower() == low:
                    key = canonical
                    break
        if key is None:
            key = candidate

        data = _PROFILES.get(key)
        if data is None:
            for k, v in _PROFILES.items():
                if k.lower() == candidate.lower():
                    data = v
                    key = k
                    break
        if data is None:
            continue

        return MaterialProfile(
            name=key,
            character=data.get("character", {}),
            mw=data.get("mw"),
            vp=data.get("vp"),
            clogp=data.get("clogp"),
            odt=data.get("odt"),
            note=data.get("note", "heart"),
            role=data.get("role", "modifier"),
            texture=data.get("texture", ""),
            synergies=data.get("synergies", []),
            avoid=data.get("avoid", []),
            dilution=data.get("dilution", 1.0),
        )
    return None


def get_all_profiles() -> dict[str, MaterialProfile]:
    """Return all profiles indexed by canonical name."""
    return {name: get_profile(name) for name in _PROFILES}


def character_distance(a: MaterialProfile, b: MaterialProfile) -> float:
    """Euclidean distance between two materials in character space (0-10 scale).
    Lower = more similar."""
    va = a.dimension_vector()
    vb = b.dimension_vector()
    return sum((x - y) ** 2 for x, y in zip(va, vb)) ** 0.5


def find_similar(name: str, n: int = 5) -> list[tuple[str, float]]:
    """Find the n most similar materials to the given one by character profile.
    Returns (name, distance) pairs sorted by distance."""
    source = get_profile(name)
    if source is None:
        return []
    results = []
    for other_name in _PROFILES:
        if other_name == source.name:
            continue
        other = get_profile(other_name)
        if other:
            dist = character_distance(source, other)
            results.append((other_name, round(dist, 2)))
    results.sort(key=lambda x: x[1])
    return results[:n]
