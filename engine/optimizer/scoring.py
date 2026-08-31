"""Multi-axis scoring engine for perfume formulas.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every perceptibility claim must be backed by OAV. No exceptions.

Active diagnostics exclude any composition-derived liking or beauty axis.

Legacy replay formerly exposed 10 axes:
  longevity   (×0.8) — MW, CLP, base note percentage
  sillage     (×0.8) — VP, projection boosters, note distribution
  synergy     (×0.5) — pairing rule hits + SynergyGraph
  luxury      (×0.8) — ingredient quality perception (not price)
  texture     (×0.8) — haptic/sensory: rounded, creamy, harsh, silky
  stacking    (×0.8) — intentional structural layering (craftsmanship)
  safety      (×1.2) — IFRA compliance + allergen + sensitization
  skin_perf   (×0.7) — reservoir kinetics + fabric substantivity
  hedonic     (×0.5) — intrinsic pleasantness (Khan 2007)
  perceptual  (×0.6) — mixture suppression + cross-adaptation

Composite: geometric mean = ∏(si)^(wi/Σw), penalizes weakness.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from ..diffusion_model import score_diffusion
from ..dose_response import score_dose_response
from ..hedonic_model import score_hedonic

# ── Science modules ──
from ..ifra_safety import score_ifra_compliance
from ..ingredient_catalog import find_ingredient
from ..ingredient_intelligence import (
    DIMENSIONS,
    get_profile,
)
from ..material_resolver import unknown_materials
from ..psychophysics import CROSS_ADAPTATION_GROUPS, score_psychophysics
from ..skin_interaction import score_skin_interaction
from ..trigeminal import score_trigeminal
from .models import (
    FormulaVector,
    LegacyObjectiveWeightsV1,
    ObjectiveWeights,
    _lookup_material,
    analyze_formula_rule_coverage,
)

if TYPE_CHECKING:
    from ..pipeline.formula_state import FormulaState, MaterialState
    from ..synergy_graph import SynergyGraph
    from ..temporal_graph import TemporalProfile


class FormulaScorer:
    """Score a formula across multiple objectives."""

    # Style-aware balance targets (Carles pyramid variants)
    BALANCE_TARGETS = {
        "classical": (20, 40, 40),
        "chypre": (15, 30, 55),
        "cologne": (40, 35, 25),
        "skin_scent": (10, 55, 35),
        "oriental": (15, 35, 50),
        "soliflore": (10, 60, 30),
        "fougere": (25, 40, 35),
        "linear": (33, 34, 33),
    }

    # Richer style/category fingerprints used for downstream creative reasoning.
    # These are intentionally broader than BALANCE_TARGETS so one formula can
    # expose multiple plausible interpretations without changing score math.
    STYLE_FINGERPRINTS = {
        # Canonical styles
        "classical": {
            "kind": "style",
            "balance": (20, 40, 40),
            "keywords": {"classical", "balanced", "elegant", "polished", "structured"},
            "anchors": {"hedione", "iso e super", "ambrox", "galaxolide"},
            "positive_dims": {"freshness": 0.8, "floral": 0.8, "woody": 0.8, "radiance": 0.7},
            "negative_dims": {"smoky": 0.4, "animalic": 0.3},
        },
        "chypre": {
            "kind": "style",
            "balance": (15, 30, 55),
            "keywords": {
                "chypre",
                "oakmoss",
                "moss",
                "labdanum",
                "patchouli",
                "bergamot",
                "evernyl",
            },
            "anchors": {"oakmoss", "evernyl", "labdanum", "patchouli"},
            "positive_dims": {"green": 1.3, "woody": 1.0, "freshness": 0.8, "smoky": 0.4},
            "negative_dims": {"sweetness": 0.7, "creamy": 0.4},
        },
        "cologne": {
            "kind": "style",
            "balance": (40, 35, 25),
            "keywords": {"cologne", "bergamot", "citrus", "neroli", "lemon", "lime", "aldehyde"},
            "anchors": {
                "bergamot",
                "cedrat",
                "citron",
                "neroli",
                "aldehyde c12 mna",
                "dihydromyrcenol",
            },
            "positive_dims": {"freshness": 1.4, "radiance": 1.0, "green": 0.6},
            "negative_dims": {"sweetness": 0.6, "animalic": 0.3, "smoky": 0.3},
        },
        "fougere": {
            "kind": "style",
            "balance": (25, 40, 35),
            "keywords": {"fougere", "lavender", "coumarin", "tonka", "moss", "aromatic"},
            "anchors": {"lavender", "coumarin", "oakmoss", "tonka", "bergamot"},
            "positive_dims": {"green": 1.0, "woody": 0.8, "spicy": 0.7, "freshness": 0.6},
            "negative_dims": {"sweetness": 0.5, "creamy": 0.4},
        },
        "oriental": {
            "kind": "style",
            "balance": (15, 35, 50),
            "keywords": {
                "oriental",
                "amber",
                "resin",
                "balsam",
                "labdanum",
                "benzoin",
                "vanilla",
                "spice",
            },
            "anchors": {"labdanum", "benzoin", "patchouli", "vanillin", "ambermax", "cashmeran"},
            "positive_dims": {
                "warmth": 1.3,
                "sweetness": 1.0,
                "spicy": 0.8,
                "creamy": 0.6,
                "smoky": 0.4,
            },
            "negative_dims": {"freshness": 0.5, "green": 0.4},
        },
        "skin_scent": {
            "kind": "style",
            "balance": (10, 55, 35),
            "keywords": {"skin", "musk", "musky", "clean", "amber", "diffusive"},
            "anchors": {
                "iso e super",
                "ambrox",
                "cashmeran",
                "habanolide",
                "galaxolide",
                "ethylene brassylate",
            },
            "positive_dims": {"creamy": 1.2, "radiance": 1.0, "woody": 0.8, "warmth": 0.5},
            "negative_dims": {"smoky": 0.6, "animalic": 0.5},
        },
        "soliflore": {
            "kind": "style",
            "balance": (10, 60, 30),
            "keywords": {
                "soliflore",
                "rose",
                "jasmine",
                "iris",
                "violet",
                "muguet",
                "lily",
                "peony",
                "powder",
            },
            "anchors": {
                "rose absolute",
                "jasmine absolute",
                "orris",
                "iris",
                "peonile",
                "muguet",
                "heliotropin",
            },
            "positive_dims": {"floral": 1.4, "powdery": 1.0, "creamy": 0.6, "radiance": 0.5},
            "negative_dims": {"smoky": 0.6, "woody": 0.4, "spicy": 0.4, "green": 0.4},
        },
        "linear": {
            "kind": "style",
            "balance": (33, 34, 33),
            "keywords": {"linear", "transparent", "diffusive", "modern", "clean"},
            "anchors": {
                "hedione",
                "iso e super",
                "ambrox",
                "galaxolide",
                "habanolide",
                "dihydromyrcenol",
            },
            "positive_dims": {"radiance": 1.1, "freshness": 0.8, "creamy": 0.7, "woody": 0.5},
            "negative_dims": {"smoky": 0.4, "animalic": 0.4, "green": 0.3},
        },
        "iris_powdery": {
            "kind": "style",
            "balance": (8, 42, 50),
            "keywords": {
                "iris",
                "irone",
                "orris",
                "powder",
                "ionone",
                "heliotropin",
                "orivone",
                "ultralia",
                "violet",
                "suede",
            },
            "anchors": {
                "orivone",
                "alpha irone",
                "ultralia",
                "heliotropin",
                "musk ketone",
                "cashmeran",
                "coumarin",
                "beta ionone",
            },
            "positive_dims": {
                "powdery": 1.3,
                "floral": 1.0,
                "creamy": 0.8,
                "radiance": 0.7,
                "warmth": 0.4,
            },
            "negative_dims": {"green": 0.5, "animalic": 0.4, "smoky": 0.3},
        },
        "iris_crystalline": {
            "kind": "style",
            "balance": (12, 38, 50),
            "keywords": {
                "iris",
                "irone",
                "crystalline",
                "mineral",
                "transparent",
                "cold",
                "architectural",
                "glass",
                "helional",
                "metallic",
            },
            "anchors": {
                "alpha irone",
                "helional",
                "scentenal",
                "cyclamen aldehyde",
                "timberol",
                "javanol",
                "zenolide",
                "hedione",
                "clearwood",
                "iso e super",
                "norlimbanol dextro",
            },
            "positive_dims": {
                "transparency": 1.5,
                "radiance": 1.2,
                "freshness": 1.0,
                "powdery": 0.8,
                "floral": 0.6,
            },
            "negative_dims": {
                "warmth": 0.8,
                "sweetness": 0.7,
                "creamy": 0.5,
                "animalic": 0.5,
                "smoky": 0.4,
            },
        },
        # Broader category lenses
        "fresh": {
            "kind": "category",
            "balance": (35, 40, 25),
            "keywords": {"fresh", "citrus", "bergamot", "neroli", "green", "clean", "air", "lift"},
            "anchors": {
                "bergamot",
                "cedrat",
                "dihydromyrcenol",
                "hedione",
                "linalool",
                "linalyl acetate",
            },
            "positive_dims": {"freshness": 1.5, "radiance": 0.9, "green": 0.8},
            "negative_dims": {"sweetness": 0.5, "smoky": 0.4},
        },
        "floral": {
            "kind": "category",
            "balance": (15, 55, 30),
            "keywords": {
                "floral",
                "flower",
                "rose",
                "jasmine",
                "iris",
                "muguet",
                "peony",
                "powdery",
            },
            "anchors": {
                "rose absolute",
                "jasmine absolute",
                "orris",
                "iris",
                "peonile",
                "heliotropin",
            },
            "positive_dims": {"floral": 1.5, "powdery": 0.8, "creamy": 0.6, "radiance": 0.4},
            "negative_dims": {"smoky": 0.5, "green": 0.4},
        },
        "woody": {
            "kind": "category",
            "balance": (15, 25, 60),
            "keywords": {"woody", "wood", "cedar", "patchouli", "vetiver", "sandalwood", "dry"},
            "anchors": {
                "iso e super",
                "ambrox",
                "patchouli eo",
                "sandalwood eo",
                "cedarwood",
                "vetiver eo",
            },
            "positive_dims": {"woody": 1.5, "smoky": 0.8, "warmth": 0.5, "creamy": 0.4},
            "negative_dims": {"freshness": 0.5, "floral": 0.4},
        },
        "amber": {
            "kind": "category",
            "balance": (15, 35, 50),
            "keywords": {
                "amber",
                "warm",
                "resin",
                "balsam",
                "labdanum",
                "benzoin",
                "vanilla",
                "gourmand",
            },
            "anchors": {"labdanum", "benzoin", "vanillin", "ambermax", "cashmeran", "patchouli"},
            "positive_dims": {"warmth": 1.5, "sweetness": 1.0, "creamy": 0.7, "smoky": 0.4},
            "negative_dims": {"freshness": 0.5, "green": 0.4},
        },
        "green": {
            "kind": "category",
            "balance": (25, 40, 35),
            "keywords": {"green", "leaf", "moss", "herbal", "aromatic", "crisp"},
            "anchors": {"oakmoss", "galbanum", "cis-3-hexenol", "evernyl", "vetiver eo"},
            "positive_dims": {"green": 1.6, "freshness": 0.9, "woody": 0.5},
            "negative_dims": {"sweetness": 0.5, "creamy": 0.4},
        },
        "spicy": {
            "kind": "category",
            "balance": (15, 30, 55),
            "keywords": {"spicy", "pepper", "cardamom", "clove", "cinnamon", "aromatic"},
            "anchors": {"black pepper ftec", "cardamom", "clove", "cinnamon", "ginger"},
            "positive_dims": {"spicy": 1.6, "warmth": 1.0, "smoky": 0.4},
            "negative_dims": {"freshness": 0.5, "creamy": 0.4},
        },
        "musky": {
            "kind": "category",
            "balance": (10, 50, 40),
            "keywords": {"musk", "musky", "skin", "clean", "cotton", "soft"},
            "anchors": {
                "galaxolide",
                "habanolide",
                "ethylene brassylate",
                "musk ketone",
                "ambrettolide",
            },
            "positive_dims": {"creamy": 1.3, "radiance": 1.0, "woody": 0.5},
            "negative_dims": {"smoky": 0.4, "animalic": 0.4},
        },
    }

    def __init__(
        self,
        weights: ObjectiveWeights | None = None,
        synergy_graph: SynergyGraph | None = None,
        temporal_profile: TemporalProfile | None = None,
        catalog_index: dict | None = None,
        batch_volume_ml: float = 10.0,
    ):
        self.weights = weights or ObjectiveWeights()
        self.synergy_graph = synergy_graph
        self.temporal_profile = temporal_profile
        self.catalog_index = catalog_index
        # Batch volume assumed for converting percentage formulas back to
        # absolute µL for science-axis scoring. Changing this affects OAV
        # calculations non-linearly for trace materials — use
        # engine.optimizer.oav_guard.check_proportional_scaling to verify.
        self.batch_volume_ml = float(batch_volume_ml)

    # ── Catalog ↔ Style vocabulary bridge ──
    # Maps free-form catalog best_in/avoid_in tokens to STYLE_FINGERPRINTS keys.
    _STYLE_TOKEN_MAP: dict[str, set[str]] = {
        "classical": {"classical", "balanced", "elegant", "luxury", "polished"},
        "chypre": {"chypre", "oakmoss", "moss"},
        "chypre_classical": {"chypre", "oakmoss", "moss", "bergamot", "labdanum"},
        "chypre_floral": {"chypre", "rose", "jasmine", "moss"},
        "chypre_fruity": {"chypre", "fruit", "peach", "bergamot", "moss"},
        "chypre_green": {"chypre", "green", "galbanum", "moss"},
        "chypre_leathery": {"chypre", "leather", "birch", "moss"},
        "cologne": {"cologne", "citrus", "hesperidic", "sport"},
        "citrus_classical": {"cologne", "citrus", "hesperidic", "neroli", "orange"},
        "citrus_aromatic": {"citrus", "aromatic", "lavender", "rosemary", "bergamot"},
        "fougere": {"fougere", "fougère", "aromatic", "herbal"},
        "fougere_classical": {"fougere", "lavender", "coumarin", "moss", "bergamot"},
        "oriental": {"oriental", "amber", "resin", "balsamic", "gourmand", "sweet"},
        "oriental_classical": {"oriental", "amber", "benzoin", "vanilla", "incense"},
        "oriental_soft": {"soft", "amber", "lavender", "tonka", "vanilla"},
        "oriental_floral": {"floral", "amber", "rose", "ylang", "powdery"},
        "skin_scent": {"skin", "musk", "musky", "clean", "intimate", "minimal"},
        "soliflore": {
            "soliflore",
            "iris",
            "rose",
            "jasmine",
            "muguet",
            "violet",
            "tuberose",
            "powdery",
        },
        "floral_soliflore": {"soliflore", "rose", "single", "petal", "dewy"},
        "floral_bouquet": {"bouquet", "rose", "jasmine", "muguet", "floral"},
        "floral_white": {"white", "floral", "jasmine", "tuberose", "indolic"},
        "floral_muguet": {"muguet", "lily", "hydroxycitronellal", "bourgeonal"},
        "floral_carnation": {"carnation", "clove", "spicy", "floral"},
        "floral_powdery": {"powdery", "heliotrope", "iris", "violet"},
        "floral_green": {"green", "floral", "galbanum", "leaf"},
        "floral_aldehydic": {"aldehydic", "floral", "soapy", "sparkle"},
        "iris_crystalline": {
            "crystalline",
            "mineral",
            "transparent",
            "cold iris",
            "glass",
            "architectural",
        },
        "linear": {"linear", "transparent", "diffusive", "modern"},
        "fresh": {"fresh", "aquatic", "ozone", "marine", "clean", "sport"},
        "floral": {"floral", "flower", "white floral", "indolic"},
        "woody": {"woody", "wood", "cedar", "sandalwood", "vetiver", "dry"},
        "amber": {"amber", "warm", "resinous", "vanilla", "gourmand"},
        "green": {"green", "leaf", "galbanum", "herbal"},
        "spicy": {"spicy", "pepper", "cardamom", "incense"},
        "musky": {"musk", "musky", "skin scent", "cotton"},
        "leather": {"leather", "suede", "animalic", "dark"},
    }

    # ── Extended perfume taxonomy fingerprints from engine.knowledge ──
    # These bridge the complete perfume taxonomy into the scoring system,
    # enabling richer family classification beyond the core 16 styles.
    EXTENDED_STYLE_FINGERPRINTS: dict[str, dict] = {
        "citrus_classical": {
            "kind": "subfamily",
            "balance": (42, 33, 25),
            "keywords": {
                "cologne",
                "4711",
                "bergamot",
                "lemon",
                "orange",
                "neroli",
                "petitgrain",
                "lavender",
            },
            "anchors": {
                "bergamot fcf oil sicilian",
                "lemon fcf oil sicilian",
                "orange peel eo",
                "oranger crystals",
                "nerol",
                "lavender eo",
            },
            "positive_dims": {"freshness": 1.5, "radiance": 0.8, "green": 0.6},
            "negative_dims": {"sweetness": 0.5, "smoky": 0.4, "animalic": 0.3},
        },
        "citrus_aromatic": {
            "kind": "subfamily",
            "balance": (35, 38, 27),
            "keywords": {"citrus", "aromatic", "herb", "bergamot", "lavender", "rosemary"},
            "anchors": {
                "bergamot fcf",
                "lavender eo",
                "rosemary eo",
                "linalool",
                "linalyl acetate",
                "petitgrain",
            },
            "positive_dims": {"freshness": 1.3, "green": 0.9, "aromatic": 0.8},
            "negative_dims": {"sweetness": 0.5, "smoky": 0.4},
        },
        "floral_soliflore": {
            "kind": "subfamily",
            "balance": (12, 58, 30),
            "keywords": {"soliflore", "single floral", "rose", "petal", "dewy", "tea rose"},
            "anchors": {
                "phenethyl alcohol",
                "geraniol",
                "citronellol",
                "nerol",
                "rose oxide",
                "damascenone",
            },
            "positive_dims": {"floral": 1.6, "freshness": 0.5, "powdery": 0.4},
            "negative_dims": {"smoky": 0.4, "woody": 0.4, "animalic": 0.3},
        },
        "floral_bouquet": {
            "kind": "subfamily",
            "balance": (18, 54, 28),
            "keywords": {"bouquet", "rose", "jasmine", "muguet", "aldehydic", "multi floral"},
            "anchors": {
                "phenethyl alcohol",
                "hedione",
                "benzyl acetate",
                "hydroxycitronellal",
                "benzyl salicylate",
                "ylang ylang eo",
            },
            "positive_dims": {"floral": 1.6, "radiance": 0.8, "creamy": 0.5},
            "negative_dims": {"smoky": 0.4, "green": 0.3},
        },
        "floral_muguet": {
            "kind": "subfamily",
            "balance": (16, 58, 26),
            "keywords": {"muguet", "lily of the valley", "dewy", "green floral", "diorissimo"},
            "anchors": {
                "hydroxycitronellal",
                "bourgeonal",
                "lilyreal nd",
                "mayol",
                "cyclimal aldehyde",
                "farnesol",
            },
            "positive_dims": {"floral": 1.5, "green": 0.9, "freshness": 0.7},
            "negative_dims": {"sweetness": 0.4, "smoky": 0.4},
        },
        "floral_carnation": {
            "kind": "subfamily",
            "balance": (14, 52, 34),
            "keywords": {
                "carnation",
                "clove",
                "spicy floral",
                "bellodgia",
                "eugenol",
                "isoeugenol",
            },
            "anchors": {
                "eugenol",
                "isoeugenol",
                "phenethyl alcohol",
                "ylang ylang eo",
                "benzyl salicylate",
            },
            "positive_dims": {"floral": 1.2, "spicy": 1.1, "warmth": 0.5},
            "negative_dims": {"freshness": 0.4, "smoky": 0.4},
        },
        "floral_powdery": {
            "kind": "subfamily",
            "balance": (12, 50, 38),
            "keywords": {"powdery", "heliotrope", "iris", "violet", "apres londee", "heliotropal"},
            "anchors": {
                "alpha isomethyl ionone",
                "alpha ionone",
                "beta ionone",
                "heliotropal",
                "musk ketone",
                "vanillin",
            },
            "positive_dims": {"powdery": 1.5, "floral": 1.0, "creamy": 0.7},
            "negative_dims": {"green": 0.4, "smoky": 0.3},
        },
        "floral_green": {
            "kind": "subfamily",
            "balance": (20, 46, 34),
            "keywords": {"green floral", "galbanum", "iris", "leaf", "stem", "no 19"},
            "anchors": {
                "galbanum resinoid",
                "hydroxycitronellal",
                "mayol",
                "alpha isomethyl ionone",
                "vetiver eo",
                "evernyl",
            },
            "positive_dims": {"green": 1.4, "floral": 1.0, "freshness": 0.7},
            "negative_dims": {"sweetness": 0.5, "gourmand": 0.4},
        },
        "citrus_woody": {
            "kind": "subfamily",
            "balance": (20, 30, 50),
            "keywords": {"citrus", "woody", "vetiver", "cedar", "mineral", "earthy"},
            "anchors": {"vetiver eo", "cedarwood eo", "iso e super", "bergamot fcf", "cedramber"},
            "positive_dims": {"woody": 1.2, "freshness": 0.9, "green": 0.6},
            "negative_dims": {"sweetness": 0.5, "creamy": 0.4},
        },
        "floral_white": {
            "kind": "subfamily",
            "balance": (15, 52, 33),
            "keywords": {"white floral", "jasmine", "gardenia", "tuberose", "narcotic", "indolic"},
            "anchors": {
                "jasmine absolute",
                "gardenia",
                "tuberose",
                "ylang",
                "indole",
                "methyl anthranilate",
            },
            "positive_dims": {"floral": 1.5, "creamy": 0.7, "animalic": 0.5},
            "negative_dims": {"green": 0.4, "freshness": 0.3},
        },
        "floral_aldehydic": {
            "kind": "subfamily",
            "balance": (25, 45, 30),
            "keywords": {"aldehydic", "floral", "sparkle", "chanel", "waxy", "soapy"},
            "anchors": {
                "aldehyde c10",
                "aldehyde c11",
                "aldehyde c12 mna",
                "rose",
                "jasmine",
                "musk ketone",
            },
            "positive_dims": {"radiance": 1.2, "floral": 1.0, "powdery": 0.7, "freshness": 0.5},
            "negative_dims": {"green": 0.4, "smoky": 0.3},
        },
        "fougere_classical": {
            "kind": "subfamily",
            "balance": (24, 40, 36),
            "keywords": {
                "fougere royale",
                "classical fougere",
                "lavender",
                "coumarin",
                "moss",
                "bergamot",
            },
            "anchors": {
                "lavender eo",
                "coumarin",
                "evernyl",
                "bergamot fcf oil sicilian",
                "patchouli eo",
                "geraniol",
            },
            "positive_dims": {"aromatic": 1.2, "green": 0.8, "freshness": 0.6, "woody": 0.5},
            "negative_dims": {"sweetness": 0.4, "gourmand": 0.4},
        },
        "woody_amber": {
            "kind": "subfamily",
            "balance": (12, 30, 58),
            "keywords": {
                "woody",
                "amber",
                "ambrox",
                "iso e super",
                "transparent",
                "radiant",
                "modern",
            },
            "anchors": {
                "ambrox super",
                "iso e super",
                "sandalore",
                "cashmeran",
                "norlimbanol dextro",
            },
            "positive_dims": {"radiance": 1.2, "woody": 1.0, "warmth": 0.6, "creamy": 0.4},
            "negative_dims": {"green": 0.4, "animalic": 0.3},
        },
        "chypre_classical": {
            "kind": "subfamily",
            "balance": (16, 28, 56),
            "keywords": {
                "classic chypre",
                "coty chypre",
                "bergamot",
                "labdanum",
                "oakmoss",
                "patchouli",
            },
            "anchors": {
                "bergamot fcf oil sicilian",
                "evernyl",
                "patchouli eo",
                "labdanum absolute",
                "vetiver eo",
            },
            "positive_dims": {"green": 1.0, "woody": 1.0, "warmth": 0.5},
            "negative_dims": {"sweetness": 0.7, "creamy": 0.4},
        },
        "chypre_floral": {
            "kind": "subfamily",
            "balance": (16, 36, 48),
            "keywords": {"floral chypre", "rose", "jasmine", "moss", "patchouli", "miss dior"},
            "anchors": {
                "phenethyl alcohol",
                "hedione",
                "patchouli eo",
                "evernyl",
                "bergamot fcf oil sicilian",
                "labdanum absolute",
            },
            "positive_dims": {"floral": 1.2, "green": 0.8, "woody": 0.8},
            "negative_dims": {"sweetness": 0.6, "gourmand": 0.4},
        },
        "chypre_fruity": {
            "kind": "subfamily",
            "balance": (18, 34, 48),
            "keywords": {"fruity chypre", "mitsouko", "peach", "bergamot", "moss", "patchouli"},
            "anchors": {
                "bergamot fcf oil sicilian",
                "damascenone",
                "gamma undecalactone",
                "patchouli eo",
                "evernyl",
                "labdanum absolute",
            },
            "positive_dims": {"green": 0.9, "woody": 0.8, "fruity": 0.7},
            "negative_dims": {"sweetness": 0.7, "creamy": 0.5},
        },
        "chypre_green": {
            "kind": "subfamily",
            "balance": (18, 34, 48),
            "keywords": {"green chypre", "vent vert", "galbanum", "leafy", "moss", "patchouli"},
            "anchors": {
                "galbanum resinoid",
                "bergamot fcf oil sicilian",
                "evernyl",
                "patchouli eo",
                "vetiver eo",
                "cyclamen aldehyde",
            },
            "positive_dims": {"green": 1.5, "freshness": 0.8, "woody": 0.7},
            "negative_dims": {"sweetness": 0.5, "gourmand": 0.4},
        },
        "chypre_leathery": {
            "kind": "subfamily",
            "balance": (12, 30, 58),
            "keywords": {"leather chypre", "bandit", "ibq", "birch tar", "moss", "patchouli"},
            "anchors": {
                "isobutyl quinoline",
                "birch tar rectified",
                "evernyl",
                "patchouli eo",
                "labdanum absolute",
                "vetiver eo",
            },
            "positive_dims": {"woody": 0.9, "smoky": 0.8, "green": 0.7},
            "negative_dims": {"sweetness": 0.6, "creamy": 0.4},
        },
        "woody_mineral": {
            "kind": "subfamily",
            "balance": (12, 28, 60),
            "keywords": {
                "mineral",
                "cold",
                "transparent",
                "architectural",
                "stone",
                "jce",
                "ellena",
            },
            "anchors": {
                "timberol",
                "javanol",
                "iso e super",
                "norlimbanol dextro",
                "scentenal",
                "clearwood",
            },
            "positive_dims": {"transparency": 1.4, "freshness": 0.8, "woody": 0.8},
            "negative_dims": {"warmth": 0.6, "sweetness": 0.5, "creamy": 0.4},
        },
        "oriental_classical": {
            "kind": "subfamily",
            "balance": (12, 30, 58),
            "keywords": {
                "shalimar",
                "classic amber",
                "oriental",
                "benzoin",
                "vanilla",
                "incense",
                "citrus",
            },
            "anchors": {
                "benzoin sumatra resinoid",
                "siam benzoin",
                "vanillin",
                "olibanum resinoid absolute",
                "patchouli eo",
                "bergamot fcf oil sicilian",
            },
            "positive_dims": {"warmth": 1.5, "sweetness": 0.8, "smoky": 0.5, "creamy": 0.5},
            "negative_dims": {"green": 0.4, "marine": 0.4},
        },
        "oriental_soft": {
            "kind": "subfamily",
            "balance": (16, 34, 50),
            "keywords": {
                "soft oriental",
                "jicky",
                "lavender",
                "bergamot",
                "tonka",
                "vanilla",
                "benzoin",
            },
            "anchors": {
                "lavender eo",
                "bergamot fcf oil sicilian",
                "coumarin",
                "vanillin",
                "tonka bean fo",
                "benzoin sumatra resinoid",
            },
            "positive_dims": {"warmth": 1.1, "aromatic": 0.8, "freshness": 0.6, "creamy": 0.5},
            "negative_dims": {"marine": 0.4, "green": 0.4},
        },
        "oriental_amber": {
            "kind": "subfamily",
            "balance": (12, 28, 60),
            "keywords": {
                "amber",
                "warm",
                "benzoin",
                "labdanum",
                "vanilla",
                "resinous",
                "grand soir",
            },
            "anchors": {
                "benzoin resinoid",
                "labdanum absolute",
                "vanillin",
                "ambermax",
                "ambrox super",
            },
            "positive_dims": {"warmth": 1.5, "creamy": 0.8, "sweetness": 0.7},
            "negative_dims": {"freshness": 0.4, "green": 0.3},
        },
        "oriental_floral": {
            "kind": "subfamily",
            "balance": (14, 40, 46),
            "keywords": {
                "floral oriental",
                "floral amber",
                "lheure bleue",
                "rose",
                "ylang",
                "vanilla",
                "benzoin",
            },
            "anchors": {
                "phenethyl alcohol",
                "ylang ylang eo",
                "benzoin sumatra resinoid",
                "vanillin",
                "heliotropal",
                "musk ketone",
            },
            "positive_dims": {"floral": 1.2, "warmth": 1.0, "powdery": 0.8, "creamy": 0.6},
            "negative_dims": {"green": 0.4, "marine": 0.4},
        },
        "oriental_spicy": {
            "kind": "subfamily",
            "balance": (14, 32, 54),
            "keywords": {"spicy", "clove", "cinnamon", "eugenol", "carnation", "opium"},
            "anchors": {"eugenol", "isoeugenol", "cinnamon", "clove", "vanillin", "benzoin"},
            "positive_dims": {"spicy": 1.4, "warmth": 1.0, "smoky": 0.4},
            "negative_dims": {"freshness": 0.5, "green": 0.3},
        },
        "gourmand_vanilla": {
            "kind": "subfamily",
            "balance": (8, 22, 70),
            "keywords": {
                "gourmand",
                "vanilla",
                "caramel",
                "sweet",
                "ethyl maltol",
                "tonka",
                "dessert",
            },
            "anchors": {
                "vanillin",
                "ethyl vanillin",
                "ethyl maltol",
                "coumarin",
                "benzoin resinoid",
            },
            "positive_dims": {"sweetness": 1.5, "creamy": 0.8, "warmth": 0.6},
            "negative_dims": {"freshness": 0.4, "green": 0.3, "smoky": 0.3},
        },
        "leather_suede": {
            "kind": "subfamily",
            "balance": (10, 33, 57),
            "keywords": {"suede", "soft leather", "powder", "cashmere", "violet", "brushed"},
            "anchors": {"suederal", "cashmeran", "violet fleuressence", "iso e super", "vetival"},
            "positive_dims": {"powdery": 1.0, "woody": 0.8, "creamy": 0.6, "radiance": 0.4},
            "negative_dims": {"green": 0.4, "freshness": 0.3},
        },
        "marine_ozonic": {
            "kind": "subfamily",
            "balance": (25, 40, 35),
            "keywords": {"marine", "aquatic", "ozone", "calone", "ocean", "sea", "fresh", "water"},
            "anchors": {"calone", "floralozone", "dihydromyrcenol", "hedione", "linalool"},
            "positive_dims": {"freshness": 1.6, "radiance": 0.8, "green": 0.4},
            "negative_dims": {"sweetness": 0.4, "smoky": 0.3, "warmth": 0.3},
        },
        "musk_skin": {
            "kind": "subfamily",
            "balance": (8, 30, 62),
            "keywords": {"skin", "intimate", "warm", "bare", "exaltolide", "musk", "body"},
            "anchors": {
                "ethylene brassylate",
                "exaltolide",
                "habanolide",
                "iso e super",
                "ambrox super",
            },
            "positive_dims": {"creamy": 1.0, "radiance": 0.7, "warmth": 0.6},
            "negative_dims": {"green": 0.4, "freshness": 0.3},
        },
        "aromatic_fougere_modern_mineral": {
            "kind": "subfamily",
            "balance": (18, 42, 40),
            "keywords": {"mineral", "fougere", "aromatic", "cold", "stone", "lavender", "marine"},
            "anchors": {
                "lavender eo",
                "dihydromyrcenol",
                "calone",
                "scentenal",
                "coumarin",
                "evernyl",
            },
            "positive_dims": {"freshness": 1.1, "green": 0.8, "aromatic": 0.7, "woody": 0.5},
            "negative_dims": {"sweetness": 0.5, "creamy": 0.4},
        },
        "aromatic_fougere_modern_tonka": {
            "kind": "subfamily",
            "balance": (18, 40, 42),
            "keywords": {"tonka", "mass appeal", "apple", "vanilla", "fruity", "fougere"},
            "anchors": {
                "coumarin",
                "vanillin",
                "apritone",
                "lavender eo",
                "iso e super",
                "habanolide",
            },
            "positive_dims": {"sweetness": 0.9, "freshness": 0.8, "fruity": 0.7, "aromatic": 0.6},
            "negative_dims": {"green": 0.4, "smoky": 0.3},
        },
        "soliflore_rose": {
            "kind": "subfamily",
            "balance": (15, 55, 30),
            "keywords": {"rose", "citronellol", "geraniol", "pea", "damascone", "tea rose"},
            "anchors": {
                "citronellol",
                "geraniol",
                "phenethyl alcohol",
                "damascone beta",
                "rose oxide",
            },
            "positive_dims": {"floral": 1.6, "green": 0.5, "freshness": 0.5},
            "negative_dims": {"smoky": 0.3, "animalic": 0.3, "spicy": 0.3},
        },
        "soliflore_jasmine": {
            "kind": "subfamily",
            "balance": (20, 52, 28),
            "keywords": {
                "jasmine",
                "indolic",
                "hedione",
                "benzyl acetate",
                "cis jasmone",
                "narcotic",
            },
            "anchors": {
                "hedione hc",
                "benzyl acetate",
                "cis jasmone",
                "indole",
                "methyl anthranilate",
            },
            "positive_dims": {"floral": 1.5, "animalic": 0.5, "radiance": 0.5},
            "negative_dims": {"smoky": 0.3, "green": 0.4},
        },
    }

    def _fingerprint_corpus(self) -> dict[str, dict]:
        corpus = dict(self.STYLE_FINGERPRINTS)
        corpus.update(self.EXTENDED_STYLE_FINGERPRINTS)
        return corpus

    def _archetype_alignment(self, fv: FormulaVector) -> tuple[float, list[str]]:
        """Score how well each material's catalog archetype fits the formula style.

        Returns (score 0-15, list of diagnostic strings).
        Uses best_in / avoid_in from ingredient_catalog cross-referenced against
        detected style fingerprints.
        """
        candidates = self._style_fingerprint_candidates(fv, limit=3)
        if not candidates:
            return 0.0, ["no style detected"]

        # Build token set from top detected styles (union of keys + keywords)
        style_tokens: set[str] = set()
        corpus = self._fingerprint_corpus()
        for c in candidates:
            style_key = c["style"]
            style_tokens.add(style_key)
            fp = corpus.get(style_key, {})
            style_tokens.update(fp.get("keywords", set()))

        diagnostics = []
        aligned = 0
        misaligned = 0
        neutral = 0

        for name in fv.ingredient_list():
            entry = find_ingredient(name)
            if not entry:
                neutral += 1
                continue

            best_in = entry.get("best_in", [])
            avoid_in = entry.get("avoid_in", [])

            # Tokenize catalog terms and match against style tokens
            mat_best_tokens = set()
            for phrase in best_in:
                mat_best_tokens.update(phrase.lower().split())
            mat_avoid_tokens = set()
            for phrase in avoid_in:
                mat_avoid_tokens.update(phrase.lower().split())

            # Also check reverse: do any style fingerprint keys appear in
            # the catalog's best_in/avoid_in terms?
            best_match = bool(mat_best_tokens & style_tokens)
            avoid_match = bool(mat_avoid_tokens & style_tokens)

            # Fallback: check if any _STYLE_TOKEN_MAP entry for our detected
            # styles overlaps with the full best_in/avoid_in phrases
            if not best_match:
                for c in candidates:
                    bridge = self._STYLE_TOKEN_MAP.get(c["style"], set())
                    if mat_best_tokens & bridge:
                        best_match = True
                        break
            if not avoid_match:
                for c in candidates:
                    bridge = self._STYLE_TOKEN_MAP.get(c["style"], set())
                    if mat_avoid_tokens & bridge:
                        avoid_match = True
                        break

            if best_match and not avoid_match:
                aligned += 1
            elif avoid_match and not best_match:
                misaligned += 1
                diagnostics.append(
                    f"{name}: avoid_in matches detected style "
                    f"({'|'.join(c['style'] for c in candidates[:2])})"
                )
            elif best_match and avoid_match:
                # Ambiguous — treat as slight positive
                aligned += 1
                diagnostics.append(f"{name}: mixed archetype signals")
            else:
                neutral += 1

        total = aligned + misaligned + neutral
        if total == 0:
            return 0.0, diagnostics

        # Score: ratio of aligned materials, with penalty for misaligned
        alignment_ratio = (aligned - misaligned * 0.5) / total
        score = max(0.0, min(15.0, round(15.0 * alignment_ratio, 1)))
        diagnostics.insert(
            0,
            f"archetype: {aligned} aligned, {misaligned} misaligned, "
            f"{neutral} neutral → {score}/15",
        )
        return score, diagnostics

    def _style_fingerprint_candidates(
        self,
        fv: FormulaVector,
        limit: int = 5,
        include_categories: bool = True,
    ) -> list[dict[str, object]]:
        """Return ranked style/category candidates with signal breakdowns."""
        # Per-FV cache (keyed on fv identity + params)
        cache_key = (id(fv), limit, include_categories)
        if not hasattr(self, "_sfc_cache"):
            self._sfc_cache = {}
        if cache_key in self._sfc_cache:
            return self._sfc_cache[cache_key]
        result = self._style_fingerprint_candidates_uncached(fv, limit, include_categories)
        self._sfc_cache[cache_key] = result
        return result

    def _style_fingerprint_candidates_uncached(
        self,
        fv: FormulaVector,
        limit: int = 5,
        include_categories: bool = True,
    ) -> list[dict[str, object]]:
        """Return ranked style/category candidates with signal breakdowns."""
        radar = self.formula_character_radar(fv)
        dist = fv.note_distribution()
        names_lower = {n.lower().strip() for n in fv.ingredient_list()}
        eff = fv.effective_ingredients()
        ingredient_count = len(fv.ingredients)

        candidates: list[dict[str, object]] = []
        for label, profile in self._fingerprint_corpus().items():
            if not include_categories and profile.get("kind") != "style":
                continue

            keywords = profile.get("keywords", set())
            anchors = profile.get("anchors", set())
            positive_dims = profile.get("positive_dims", {})
            negative_dims = profile.get("negative_dims", {})
            target = profile.get("balance")

            matched_keywords = sorted(
                term for term in keywords if any(term in name for name in names_lower)
            )
            matched_anchors = sorted(
                term for term in anchors if any(term in name for name in names_lower)
            )

            keyword_score = min(len(matched_keywords) * 8.0, 24.0)
            anchor_score = min(len(matched_anchors) * 10.0, 30.0)

            if target:
                target_top, target_heart, target_base = target
                actual = [dist.get("top", 0), dist.get("heart", 0), dist.get("base", 0)]
                distance = math.sqrt(sum((a - t) ** 2 for a, t in zip(actual, target)))
                balance_score = max(0.0, 100.0 - distance * 1.5)
            else:
                balance_score = 50.0

            positive_score = sum(
                radar.get(dim, 0.0) * weight for dim, weight in positive_dims.items()
            )
            positive_score = min(positive_score * 2.0, 30.0)

            negative_score = sum(
                max(radar.get(dim, 0.0) - 2.5, 0.0) * weight
                for dim, weight in negative_dims.items()
            )
            negative_score = min(negative_score * 2.0, 18.0)

            breadth_bonus = 0.0
            active_dims = [dim for dim, value in radar.items() if value > 1.5]
            if profile.get("kind") == "style":
                if label in {"soliflore", "skin_scent"}:
                    breadth_bonus = 10.0 if len(active_dims) <= 5 else 4.0
                elif label in {"classical", "linear"}:
                    breadth_bonus = 8.0 if 4 <= len(active_dims) <= 8 else 3.0
                elif label in {"oriental", "amber"}:
                    breadth_bonus = 8.0 if radar.get("warmth", 0) > 3.0 else 3.0
                elif label == "iris_powdery":
                    breadth_bonus = 8.0 if radar.get("powdery", 0) > 1.5 else 3.0
                elif label == "iris_crystalline":
                    breadth_bonus = 10.0 if radar.get("transparency", 0) > 2.5 else 3.0
            else:
                if label in {"fresh", "green"}:
                    breadth_bonus = 8.0 if radar.get("freshness", 0) > 3.0 else 2.0
                elif label in {"floral", "musky"}:
                    breadth_bonus = (
                        8.0 if radar.get("floral", 0) > 3.0 or radar.get("creamy", 0) > 3.0 else 2.0
                    )
                elif label in {"woody", "amber"}:
                    breadth_bonus = (
                        8.0 if radar.get("woody", 0) > 3.0 or radar.get("warmth", 0) > 3.0 else 2.0
                    )
                elif label == "spicy":
                    breadth_bonus = 8.0 if radar.get("spicy", 0) > 2.5 else 2.0

            # Small boost for richer formulas and clearer signal separation.
            separation_bonus = 0.0
            if ingredient_count >= 5:
                separation_bonus += min(len(matched_anchors) * 2.0, 6.0)
            if len(eff) >= 5:
                separation_bonus += 2.0

            raw_score = (
                balance_score * 0.30
                + keyword_score * 1.0
                + anchor_score * 0.9
                + positive_score
                + breadth_bonus
                + separation_bonus
                - negative_score
            )
            score = round(max(0.0, min(raw_score, 100.0)), 1)
            candidates.append(
                {
                    "style": label,
                    "kind": profile.get("kind", "style"),
                    "score": score,
                    "confidence": 0.0,  # filled after ranking
                    "signals": {
                        "matched_keywords": matched_keywords,
                        "matched_anchors": matched_anchors,
                        "balance_target": target,
                        "balance_score": round(balance_score, 1),
                        "positive_dims": {
                            dim: round(radar.get(dim, 0.0), 2) for dim in positive_dims
                        },
                        "negative_dims": {
                            dim: round(radar.get(dim, 0.0), 2) for dim in negative_dims
                        },
                        "radar": {dim: round(val, 2) for dim, val in radar.items()},
                        "note_distribution": {k: round(v, 2) for k, v in dist.items()},
                    },
                }
            )

        candidates.sort(key=lambda item: (item["score"], item["style"]), reverse=True)

        if not candidates:
            return []

        top_score = float(candidates[0]["score"])
        second_score = float(candidates[1]["score"]) if len(candidates) > 1 else 0.0
        spread = max(top_score - second_score, 0.0)
        for idx, cand in enumerate(candidates):
            score = float(cand["score"])
            confidence = min(0.96, max(0.25, (score / 100.0) * 0.55 + min(spread / 40.0, 0.35)))
            if idx == 0:
                confidence = min(0.99, confidence + 0.05)
            cand["confidence"] = round(confidence, 2)

        return candidates[: max(1, limit)]

    def detect_style_candidates(
        self,
        fv: FormulaVector,
        limit: int = 5,
        include_categories: bool = True,
    ) -> list[dict[str, object]]:
        """Return ranked plausible styles/categories for downstream reasoning."""
        return self._style_fingerprint_candidates(
            fv,
            limit=limit,
            include_categories=include_categories,
        )

    def style_fingerprint(
        self,
        fv: FormulaVector,
        limit: int = 5,
        include_categories: bool = True,
    ) -> dict[str, object]:
        """Return a richer style/category fingerprint for a formula.

        The fingerprint preserves the legacy single-style heuristic via
        `detect_style()` while exposing additional plausible interpretations
        for downstream creative recommendation logic.
        """
        candidates = self._style_fingerprint_candidates(
            fv,
            limit=limit,
            include_categories=include_categories,
        )
        radar = self.formula_character_radar(fv)
        dist = fv.note_distribution()

        style_candidates = [c for c in candidates if c.get("kind") == "style"]
        category_candidates = [c for c in candidates if c.get("kind") == "category"]

        primary = (
            candidates[0]
            if candidates
            else {
                "style": self.detect_style(fv),
                "kind": "style",
                "score": 0.0,
                "confidence": 0.0,
                "signals": {},
            }
        )

        return {
            "dominant_style": self.detect_style(fv),
            "primary_candidate": primary,
            "style_candidates": style_candidates,
            "category_candidates": category_candidates,
            "candidates": candidates,
            "radar": radar,
            "note_distribution": dist,
            "ingredient_count": len(fv.ingredients),
            "has_dilution_data": bool(getattr(fv, "has_dilution_data", False)),
        }

    def identity_signature(
        self,
        fv: FormulaVector,
        scores: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Capture the baseline identity a recommendation should preserve."""
        effective = fv.effective_ingredients()
        weighted_materials = sorted(
            effective.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        if scores is None:
            scores = self.score(fv)
        fingerprint = scores.get("_style_fingerprint") if isinstance(scores, dict) else None
        if not isinstance(fingerprint, dict):
            fingerprint = self.style_fingerprint(fv)
        primary = fingerprint.get("primary_candidate", {}) if isinstance(fingerprint, dict) else {}
        return {
            "dominant_style": fingerprint.get("dominant_style"),
            "primary_style": primary.get("style") if isinstance(primary, dict) else None,
            "primary_kind": primary.get("kind") if isinstance(primary, dict) else None,
            "style_labels": [
                str(item.get("style")).lower().strip()
                for item in fingerprint.get("candidates", [])
                if isinstance(item, dict) and item.get("style")
            ]
            if isinstance(fingerprint, dict)
            else [],
            "radar": dict(fingerprint.get("radar", {}))
            if isinstance(fingerprint, dict)
            else self.formula_character_radar(fv),
            "note_distribution": dict(fingerprint.get("note_distribution", {}))
            if isinstance(fingerprint, dict)
            else fv.note_distribution(),
            "top_materials": [name for name, _ in weighted_materials[:8]],
        }

    def identity_preservation(
        self,
        base_signature: dict[str, object],
        candidate_scores: dict[str, object],
        *,
        candidate_fv: FormulaVector | None = None,
        target_style: str | None = None,
        category_hint: str | None = None,
        must_preserve: list[str] | None = None,
        must_avoid: list[str] | None = None,
    ) -> dict[str, object]:
        """Score how well a candidate preserves the baseline perfume identity."""

        def _descriptor_matches(text: str, descriptor: str) -> bool:
            tokens = [
                token
                for token in re.split(r"[^a-z0-9]+", descriptor.lower())
                if token
                and token not in {"dominant", "led", "lead", "keep", "preserve", "note", "accord"}
            ]
            if not tokens:
                return descriptor.lower() in text
            return all(token in text for token in tokens)

        fingerprint = candidate_scores.get("_style_fingerprint", {})
        if not isinstance(fingerprint, dict):
            fingerprint = {}

        candidate_primary = fingerprint.get("primary_candidate", {})
        candidate_primary_style = (
            str(candidate_primary.get("style")).lower().strip()
            if isinstance(candidate_primary, dict) and candidate_primary.get("style")
            else None
        )
        candidate_dominant = str(fingerprint.get("dominant_style", "")).lower().strip() or None
        candidate_labels = {
            str(item.get("style")).lower().strip()
            for item in fingerprint.get("candidates", [])
            if isinstance(item, dict) and item.get("style")
        }

        base_dominant = str(base_signature.get("dominant_style", "")).lower().strip() or None
        base_primary = str(base_signature.get("primary_style", "")).lower().strip() or None
        base_radar = dict(base_signature.get("radar", {}))
        candidate_radar = dict(fingerprint.get("radar", candidate_scores.get("_radar", {})))
        base_dist = dict(base_signature.get("note_distribution", {}))
        candidate_dist = dict(fingerprint.get("note_distribution", {}))
        base_top_materials = [
            str(name).lower().strip() for name in base_signature.get("top_materials", [])
        ]
        candidate_top_materials: list[str] = []
        if candidate_fv is not None:
            weighted_materials = sorted(
                candidate_fv.effective_ingredients().items(),
                key=lambda item: (item[1], item[0]),
                reverse=True,
            )
            candidate_top_materials = [
                str(name).lower().strip() for name, _ in weighted_materials[:8]
            ]

        style_alignment = 45.0
        if base_dominant and candidate_dominant == base_dominant:
            style_alignment = 100.0
        elif base_dominant and base_dominant in candidate_labels:
            style_alignment = 82.0
        elif base_primary and candidate_dominant == base_primary:
            style_alignment = 74.0

        primary_alignment = 50.0
        if base_primary and candidate_primary_style == base_primary:
            primary_alignment = 100.0
        elif base_primary and base_primary in candidate_labels:
            primary_alignment = 80.0
        elif base_dominant and candidate_primary_style == base_dominant:
            primary_alignment = 70.0

        radar_deltas = [
            abs(float(candidate_radar.get(dim, 0.0)) - float(base_radar.get(dim, 0.0)))
            for dim in DIMENSIONS
        ]
        mean_radar_delta = sum(radar_deltas) / len(radar_deltas) if radar_deltas else 0.0
        radar_preservation = max(0.0, 100.0 - mean_radar_delta * 18.0)

        dist_keys = ("top", "heart", "base")
        pyramid_distance = math.sqrt(
            sum(
                (float(candidate_dist.get(key, 0.0)) - float(base_dist.get(key, 0.0))) ** 2
                for key in dist_keys
            )
        )
        pyramid_preservation = max(0.0, 100.0 - pyramid_distance * 2.5)

        target_checks: list[float] = []
        normalized_target_style = str(target_style or "").lower().strip()
        if normalized_target_style:
            target_checks.append(
                100.0
                if normalized_target_style == candidate_dominant
                or normalized_target_style in candidate_labels
                else 60.0
            )
        normalized_category = str(category_hint or "").lower().strip()
        if normalized_category:
            target_checks.append(
                100.0
                if normalized_category == candidate_dominant
                or normalized_category in candidate_labels
                else 70.0
            )
        target_alignment = sum(target_checks) / len(target_checks) if target_checks else 100.0

        candidate_text = " ".join(
            [
                candidate_dominant or "",
                candidate_primary_style or "",
                *candidate_top_materials,
            ]
        ).strip()
        if not candidate_text:
            candidate_text = " ".join(base_top_materials)

        preserve_terms = [
            str(term).lower().strip() for term in (must_preserve or []) if str(term).strip()
        ]
        if preserve_terms:
            preserve_scores = []
            baseline_text = " ".join(
                [*(base_top_materials or []), base_dominant or "", base_primary or ""]
            ).strip()
            for term in preserve_terms:
                if _descriptor_matches(candidate_text, term):
                    preserve_scores.append(100.0)
                elif _descriptor_matches(baseline_text, term):
                    preserve_scores.append(55.0)
                else:
                    preserve_scores.append(75.0)
            preserve_alignment = sum(preserve_scores) / len(preserve_scores)
        else:
            preserve_alignment = 100.0

        avoid_terms = [
            str(term).lower().strip() for term in (must_avoid or []) if str(term).strip()
        ]
        if avoid_terms:
            avoid_scores = [
                35.0 if _descriptor_matches(candidate_text, term) else 100.0 for term in avoid_terms
            ]
            avoid_alignment = sum(avoid_scores) / len(avoid_scores)
        else:
            avoid_alignment = 100.0

        components = {
            "style_alignment": round((style_alignment + primary_alignment) / 2.0, 1),
            "radar_preservation": round(radar_preservation, 1),
            "pyramid_preservation": round(pyramid_preservation, 1),
            "target_alignment": round(target_alignment, 1),
            "preserve_alignment": round(preserve_alignment, 1),
            "avoid_alignment": round(avoid_alignment, 1),
        }
        weighted = (
            components["style_alignment"] * 0.38
            + components["radar_preservation"] * 0.22
            + components["pyramid_preservation"] * 0.16
            + components["target_alignment"] * 0.12
            + components["preserve_alignment"] * 0.08
            + components["avoid_alignment"] * 0.04
        )

        drift_notes: list[str] = []
        if base_dominant and candidate_dominant and candidate_dominant != base_dominant:
            drift_notes.append(
                f"dominant style shifts from {base_dominant} to {candidate_dominant}"
            )
        if mean_radar_delta > 0.45:
            drift_notes.append(
                f"character radar drift is moderate ({mean_radar_delta:.2f} average delta)"
            )
        if pyramid_distance > 4.0:
            drift_notes.append(
                f"note pyramid drift is noticeable ({pyramid_distance:.1f} distance)"
            )
        if preserve_terms and preserve_alignment < 80.0:
            drift_notes.append("one or more must-preserve cues weaken")
        if avoid_terms and avoid_alignment < 100.0:
            drift_notes.append("one or more must-avoid cues are being touched")
        if not drift_notes:
            drift_notes.append("style fingerprint and note balance stay close to the baseline")

        return {
            "score": round(weighted, 1),
            "components": components,
            "drift_notes": drift_notes,
            "candidate_dominant_style": candidate_dominant,
            "candidate_primary_style": candidate_primary_style,
        }

    # ── Individual scoring functions ──

    def detect_style(self, fv: FormulaVector) -> str:
        """Auto-detect fragrance style from fingerprint matching.

        Uses the full STYLE_FINGERPRINTS corpus (17 entries) via
        detect_style_candidates(), returning the top-ranked *style*
        (kind == "style") candidate. Falls back to heuristic rules
        only when fingerprint matching gives no confident result.
        """
        # Prefer the fingerprint-scored approach — covers all 17 entries
        candidates = self.detect_style_candidates(fv, limit=3, include_categories=False)
        if candidates:
            top = candidates[0]
            if top.get("confidence", 0) >= 0.15:
                return str(top.get("style", "classical"))

        # Fallback: lightweight heuristic rules
        radar = self.formula_character_radar(fv)
        names_lower = {n.lower().strip() for n in fv.ingredient_list()}

        chypre_mats = {"evernyl", "oakmoss", "labdanum"}
        if any(any(cm in n for cm in chypre_mats) for n in names_lower):
            return "chypre"

        if radar.get("warmth", 0) > 5.0 and radar.get("sweetness", 0) > 3.0:
            return "oriental"

        dist = fv.note_distribution()
        if dist.get("top", 0) > 35 and radar.get("freshness", 0) > 5.0:
            return "cologne"

        return "classical"

    def score_longevity(self, fv: FormulaVector) -> float:
        """Score longevity (0-100): how long the composition persists on skin.

        Perfumery literature anchors
          • Arctander, *Perfume and Flavor Chemicals* (1969): tenacity
            classes A (<1 h) → E (>24 h), driven primarily by vapor
            pressure and skin substantivity.
          • Calkin & Jellinek, *Perfumery: Practice and Principles*
            (1994), Ch. 5: base notes act as slow-releasing anchors that
            extend the composition by trapping middle/top molecules in a
            low-VP matrix.
          • Sell, *The Chemistry of Fragrances* (2nd ed., 2006), Ch. 12:
            Clausius–Clapeyron evaporation — longer-chain / higher-MW
            molecules have exponentially lower vapor pressure and therefore
            longer headspace persistence.
          • Ellena, *The Diary of a Nose* (2013): CLogP ≈ 4–5 is the skin-
            reservoir optimum (too hydrophilic washes; too lipophilic
            absorbs sub-dermally).

        Blends physics-based Clausius-Clapeyron evaporation simulation
        with a heuristic that weights avg MW, CLogP, and base-note mass.
        Range: 0-100.
        """
        # ── Physics-based score from temporal simulation ──
        tp = self.temporal_profile
        if tp is not None and tp.longevity_hr > 0:
            # Map longevity_hr to a 0-100 score
            # 2hr → 20, 6hr → 45, 12hr → 70, 18hr → 85, 24hr → 95
            lon_hr = tp.longevity_hr
            physics_score = min(100, 10 + lon_hr * 3.75)

            # Half-life bonus: long perceptual half-life = more linear wear
            if tp.perceptual_half_life_hr > 8:
                physics_score += 5
            elif tp.perceptual_half_life_hr > 4:
                physics_score += 2

            physics_score = min(100, physics_score)

            # Blend: 70% physics, 30% heuristic for backwards compat
            heuristic = self._score_longevity_heuristic(fv)
            return round(physics_score * 0.7 + heuristic * 0.3, 1)

        return self._score_longevity_heuristic(fv)

    def _score_longevity_heuristic(self, fv: FormulaVector) -> float:
        """Heuristic longevity score from MW, CLogP, base note %.

        Targets calibrated for EDP-concentration compositions:
        - MW 265 (balanced formula avg, not single-material max)
        - CLogP 4.5 (optimal skin-reservoir retention, PubChem-verified)
        - Base 50% (allows strong heart register in iris/floral EDPs)
        """
        avg_mw = fv.avg_property("mw")
        avg_clp = fv.avg_property("clp")
        dist = fv.note_distribution()

        score = 0.0
        # MW contribution: ideal avg MW for EDP longevity ~220-265
        if avg_mw is not None:
            mw_score = min(avg_mw / 265, 1.0) * 40
            score += mw_score

        # CLP contribution: higher = more lipophilic = longer lasting
        # Target 4.5 aligned with PubChem-verified CLogP distribution
        if avg_clp is not None:
            clp_score = min(max(avg_clp, 0) / 4.5, 1.0) * 30
            score += clp_score

        # Base note percentage: more base = longer
        base_pct = dist.get("base", 0)
        base_score = min(base_pct / 50, 1.0) * 30
        score += base_score

        return round(score, 1)

    def score_sillage(self, fv: FormulaVector) -> float:
        """Score sillage / projection (0-100): the "signature in the air."

        Perfumery literature anchors
          • Roudnitska, *Le Parfum* (1980): sillage defined as the
            olfactive trail that surrounds the wearer — the outward-
            projecting plume distinct from "skin scent" (which is
            lingering residue).
          • Carles, "A Method of Creation in Perfumery" (1961):
            projection is carried by heart diffusers (Hedione,
            salicylates, ionones), not top-note flash — top notes
            create first-minute impact but fall off within 30–90 min.
          • Sell (2006): Fickian diffusion radius ≈ √(D · t); the
            diffusion coefficient D scales inversely with √MW. Small,
            light molecules project fastest but clear quickly; mid-MW
            diffusers (Iso E Super, Hedione) give sustained projection.
          • Givaudan / Symrise technical literature: "bloom diffusers"
            — materials with VP > 0.005 mmHg AND transparency ≥ 5
            (Hedione, Ambrox, Nympheal, Floralozone) produce sustained
            outward projection rather than immediate burnoff.

        Blends a Fickian diffusion physics simulation (when available)
        with a heuristic combining vapor pressure, volatility index
        (VP / √MW), top/heart mass, and a curated diffuser booster
        list. Range: 0-100.
        """
        tp = self.temporal_profile
        if tp is not None and hasattr(tp, "projection_cm") and tp.projection_cm is not None:
            import numpy as np

            proj = tp.projection_cm
            # Average projection over first 2 hours (the "sillage window")
            t = tp.time_hours
            mask_2h = t <= 2.0
            avg_proj_2h = float(np.mean(proj[mask_2h])) if np.any(mask_2h) else 0.0
            # Peak projection (usually at spray)
            peak_proj = float(np.max(proj))

            # Map projection_cm to score:
            # 10cm (touching) → 20, 30cm (close) → 40, 100cm (arm's length) → 65,
            # 200cm (across room) → 85, 300cm+ → 95
            physics_score = min(100, 15 + avg_proj_2h * 0.3)
            # Peak bonus
            if peak_proj > 200:
                physics_score += 5
            physics_score = min(100, physics_score)

            heuristic = self._score_sillage_heuristic(fv)
            return round(physics_score * 0.7 + heuristic * 0.3, 1)

        return self._score_sillage_heuristic(fv)

    def _score_sillage_heuristic(self, fv: FormulaVector) -> float:
        """Heuristic sillage score from VP, volatility index, and boosters."""
        avg_vp, vi = self._thermodynamic_projection_properties(fv)
        dist = fv.note_distribution()

        score = 0.0

        # Tiered VP scoring (handles heavy synthetics like Cashmeran/Galaxolide)
        if avg_vp is not None:
            if avg_vp > 1.0:
                vp_score = 20 + min((avg_vp - 1.0) / 4.0, 1.0) * 5
            elif avg_vp > 0.01:
                vp_score = 8 + min((avg_vp - 0.01) / 1.0, 1.0) * 12
            else:
                vp_score = min(avg_vp / 0.01, 1.0) * 8
            score += vp_score

        # Volatility index bonus (VP/√MW captures real projection better)
        if vi is not None:
            # VI typical range: 0.0001 (heavy base) to 0.3 (light citrus)
            # EDP-calibrated target 0.08 (EDTs ~0.10-0.15, EDPs ~0.02-0.06)
            # Map to 0-10 bonus points
            vi_score = min(vi / 0.08, 1.0) * 10
            score += vi_score

        # Top note percentage
        # EDP-calibrated: luxury EDPs typically 8-15% top notes (not 30%+
        # which is EDT/EDC territory). Target 20% for max score.
        top_pct = dist.get("top", 0)
        top_score = min(top_pct / 20, 1.0) * 20
        score += top_score

        # Heart note percentage (heart diffusers are key for sillage)
        heart_pct = dist.get("heart", 0)
        heart_score = min(heart_pct / 40, 1.0) * 20

        score += heart_score

        # Sillage boosters — bloom diffusion and projection materials
        # Derived from ingredient_intelligence profiles where texture includes
        # "diffusion", "bloom", or "projection" and VP > 0.005
        from engine.name_utils import normalize_name

        boosters = {
            "hedione",
            "iso e super",
            "ambrox super",
            "dihydromyrcenol",
            "cashmeran",
            "galaxolide",
            "habanolide",
            "paradisone",
            "benzyl salicylate",
            "hexyl salicylate",
            # Modern diffusers
            "scentenal",
            "dynascone",
            "nympheal",
            "lilyreal nd",
            "floralozone",
            "helional",
            "allyl amyl glycolate",
            # Macrocyclic musks (bloom projection)
            "ambrettolide",
            "exaltolide",
            "ethylene brassylate",
            "romandolide",
            "tonalide",
            # Woody diffusers
            "clearwood",
            "javanol",
            "sandalore",
        }
        booster_count = sum(1 for name in fv.ingredient_list() if normalize_name(name) in boosters)
        score += min(booster_count * 5, 30)

        # Sustained-projection bonus: heart-diffuser-heavy EDPs generate
        # sillage through slow radiance (Hedione, salicylates, IES), not
        # top-note flash.  When booster count is high AND heart% dominates,
        # compensate for low top notes.
        if booster_count >= 4 and heart_pct > 35:
            # Scale: max +10 when top is very low + heart is very high
            top_deficit = max(0, 20 - top_pct)  # how far below 20% top
            heart_surplus = max(0, heart_pct - 35)  # how far above 35% heart
            sustained = min(top_deficit / 20, 1.0) * min(heart_surplus / 15, 1.0) * 10
            score += sustained

        return round(min(score, 100), 1)

    def score_synergy(self, fv: FormulaVector) -> float:
        """Score synergy / accord cohesion (0-100).

        Perfumery literature anchors
          • Jellinek, *The Practice of Modern Perfumery* (1959):
            the odour-effects diagram — materials in adjacent
            effect quadrants (refreshing↔stimulating, soothing↔
            anti-erogenous) reinforce; diagonally opposite materials
            clash unless bridged.
          • Poucher, *Perfumes, Cosmetics and Soaps* (1974): accord
            construction — each named accord (chypre, fougère, oriental)
            requires at least one bridge material per quadrant
            transition or the composition fractures.
          • Calkin & Jellinek (1994), Ch. 4: "compatibility" is the
            ratio of positive pairwise interactions to the total number
            of pairs; > 0.6 defines a cohesive accord.
          • Modern synergy-graph work (Firmenich, Givaudan 2010s):
            pairwise synergies learned from expert-tagged formulas +
            fingerprint similarity reproduce classical accord theory.

        Combines per-axis magnitude-weighted pairing rules with SynergyGraph
        edge weights (when loaded) — an effect-first blend that rewards
        measurable benefit (depth, texture, hedonic, performance, sillage,
        complexity) rather than raw hit-counting. Range: 0-100.

        If OAV data is available via `self._material_oavs`, each pair's
        contribution is weighted by the perceptibility of both materials:
        pairs where either material has OAV < 1 are discounted.
        """
        oav_data = self._thermodynamic_oav_map(fv)
        ingredients = fv.ingredient_list()

        # ── Effect-weighted pairing rules ──
        coverage = analyze_formula_rule_coverage(ingredients)
        positive_hits = len(coverage["positive_pairs"])
        conflict_hits = len(coverage["conflict_pairs"])
        axis_scores = coverage.get("axis_scores", {})

        # Base from coverage (legacy minimum)
        rules_score = min(positive_hits * 1.0 + 30, 95)
        conflict_penalty = conflict_hits * 5

        # Effect-weighted bonus: sum of per-axis contributions
        axis_weights = {
            "sillage": 1.2,
            "depth": 1.0,
            "texture": 1.0,
            "hedonic": 0.8,
            "complexity": 0.8,
            "performance": 0.6,
        }
        effect_bonus = 0.0
        for axis, weight in axis_weights.items():
            score = axis_scores.get(axis, 0.0)
            effect_bonus += min(score, 100.0) * weight / 6.0

        rules_score = max(0, min(100, rules_score + effect_bonus - conflict_penalty))

        # ── OAV perceptibility weighting ──
        # Discount pair contributions where either material is below perception
        if oav_data and len(ingredients) >= 2:
            perceptible_count = sum(1 for m in ingredients if oav_data.get(m, 0) >= 1.0)
            total_count = len(ingredients)
            perceptibility_ratio = perceptible_count / max(total_count, 1)
            # Scale: if <50% materials are perceptible, heavily discount
            oav_discount = max(0.0, 1.0 - (1.0 - perceptibility_ratio) * 1.5)
            rules_score = round(rules_score * oav_discount, 1)

        # ── SynergyGraph enrichment ──
        sg = self.synergy_graph
        if sg is not None and sg.edges:
            ingredients = fv.ingredient_list()
            avg_syn = sg.formula_synergy_score(ingredients)
            graph_score = max(0, min(100, 50 + avg_syn * 100))

            clashes = []
            for i, a in enumerate(ingredients):
                for b in ingredients[i + 1 :]:
                    w = sg.pair_synergy(a, b)
                    if w < -0.2:
                        clashes.append((a, b, round(w, 3)))
            graph_score -= len(clashes) * 3

            stacks = sg.find_synergy_stacks(ingredients, min_stack_size=3)
            if stacks:
                graph_score += min(len(stacks) * 3, 10)
            graph_score = max(0, min(100, graph_score))

            self._last_synergy_detail = {
                "formula_synergy_score": round(avg_syn, 4),
                "synergy_stacks": [(s.name, s.avg_synergy) for s in stacks[:5]],
                "clashes": clashes[:10],
                "total_edges": len(sg.edges),
                "axis_scores": {k: round(v, 2) for k, v in axis_scores.items()},
                "axis_total_magnitude": coverage.get("raw_axis_magnitudes", {}),
                "effect_bonus": round(effect_bonus, 2),
            }

            return round(rules_score * 0.5 + graph_score * 0.5, 1)

        self._last_synergy_detail = None
        # Set synergy detail even without SynergyGraph (for per-axis boost)
        self._last_synergy_detail = {
            "formula_synergy_score": 0.0,
            "axis_scores": {k: round(v, 2) for k, v in axis_scores.items()},
            "axis_total_magnitude": coverage.get("raw_axis_magnitudes", {}),
        }

        return round(rules_score, 1)

    def score_luxury(self, fv: FormulaVector) -> float:
        """Score luxury: olfactive quality grounded in perfumery literature.

        Literature anchors:
          - Edmond Roudnitska, *Le parfum* (PUF, 1980): luxury is intentional
            restraint; "editing" is the compositional signature of quality.
          - Jean-Claude Ellena, *The Diary of a Nose* (Penguin, 2013) and
            *Perfume: The Alchemy of Scent* (Arcade, 2011): transparency and
            the role of sub-threshold "shadow" materials (Iris Ukiyoé orris
            sits below threshold to create depth without declaring iris;
            pp. 89–91).
          - Luca Turin & Tania Sanchez, *Perfumes: The Guide* (Viking, 2008):
            quality ≈ "effect per note"; volume-filler is the mark of
            commercial formulation, not luxury.
          - Chandler Burr, *The Perfect Scent* (Henry Holt, 2008): luxury
            niche is defined by natural content AND premium synthetic
            captives in dialogue, not substitution.
          - Arcadi Boix Camps, *Perfumery: Techniques in Evolution*, 2nd ed.
            (Allured, 2014): canonical premium captive catalog (Hedione,
            Iso E Super, Ambrox, Javanol, Clearwood, DBCA, Paradisamide,
            Ambrettolide, et al.).
          - Mandy Aftel, *Essence and Alchemy* (North Point, 2001):
            naturals as luxury baseline (12–30% of concentrate mass;
            above 40% reads rustic, below 5% reads cheap synthetic).
          - Jean Carles, "A Method of Creation in Perfumery" (*Soap,
            Perfumery & Cosmetics*, 1961): top/heart/base architectural
            coherence across volatility ranges.

        Six literature-grounded components (0–100 total):
          1. Natural baseline (0–20) — Aftel/Arctander mass-weighted
             EO/absolute/resinoid fraction; plateau 12–30%; penalty >40%.
          2. Premium captive density (0–20) — Boix Camps/Burr mass-weighted
             premium synthetic fraction; saturating ≥25%; pre-blend penalty.
          3. Carles architecture (0–15) — Carles/Roudnitska top/heart/base
             coherence (modern niche target 18/42/40).
          4. Effect-per-note (0–15) — Turin/Sanchez character expression
             per material; penalizes volume-filler mass.
          5. Trace complexity shadow (0–15) — Ellena/Roudnitska count of
             materials in the 0.1–1.0× ODT zone (sub- to near-threshold,
             the editor's fingerprint). DOSE-RESPONSIVE.
          6. Compositional restraint (0–15) — Ellena/Roudnitska penalty
             for redundant dominant characters and unjustified fillers.

        Components 3, 4, and 5 are dose-responsive: moving a material
        between OAV 0.3 and 0.6 shifts mass contributions, VP-weighted
        note split, and trace-shadow membership.

        Range: 0–100.
        """
        from engine.name_utils import normalize_name

        # Premium captive canon (Boix Camps 2014, Ch. 7–9; Burr 2008 Appx.).
        _premium_synthetics = {
            # Macrocyclic / alicyclic musks
            "ambrettolide",
            "habanolide",
            "romandolide",
            "ethylene brassylate",
            "exaltolide",
            "muscenone",
            "nirvanolide",
            "velvione",
            "zenolide",
            "macrolide",
            # Ambers — crystalline / mineral / warm
            "ambrox super",
            "ambrox",
            "ambrofix",
            "ambermax",
            "amberwood f",
            "cetalox",
            "ysamber k",
            "cedramber",
            "cedamber",
            # Premium woods and captives
            "iso e super",
            "javanol",
            "ebanol",
            "bacdanol",
            "sandalore",
            "polysantol",
            "norlimbanol",
            "norlimbanol dextro",
            "clearwood",
            "timberol",
            "kephalis",
            "koavone",
            "vertofix coeur",
            "azarbre",
            "cashmeran",
            "georgywood",
            "okoumal",
            "sylvamber",
            # Radiance / Hedione family
            "hedione",
            "hedione hc",
            "paradisone",
            "methyl dihydrojasmonate",
            # Premium florals
            "dbca",
            "lilyreal",
            "mayol",
            "bourgeonal",
            "florhydral",
            "cyclamen aldehyde",
            "alpha irone",
            "alpha ionone",
            "beta ionone",
            "methyl ionone",
            "orivone",
            "ultralia",
            "farnesol",
            "paradisamide",
            "peonile",
            # Mineral / ozonic / aldehydic
            "helional",
            "scentenal",
            "floralozone",
            "calone",
            "triplal",
            # Gourmand / lactonic
            "lactoscone",
            "prismantol",
            "gamma decalactone",
            "delta decalactone",
            # Salicylate fixative architecture
            "hexyl salicylate",
            "benzyl salicylate",
        }
        _natural_suffixes = ("eo", "absolute", "resinoid", "co2")
        _preblend_markers = ("ftec", " fo", "fleuressence", "accord", "core")

        eff = fv.effective_ingredients()
        if not eff:
            return 30.0

        total_pct = sum(eff.values()) or 1.0

        natural_mass = 0.0
        premium_mass = 0.0
        preblend_mass = 0.0
        filler_mass = 0.0
        n_filler = 0
        effect_sum = 0.0
        n_declared = 0  # declared notes (≥1× ODT or unknown)
        dominant_counts: dict[str, int] = {}
        roles_used: set[str] = set()
        trace_shadow_count = 0  # Ellena shadow zone (0.1–1.0× ODT)
        note_mass = {"top": 0.0, "heart": 0.0, "base": 0.0}
        # Perplexity 2026-04-23 extensions
        or_family_counts: dict[str, int] = {}
        hedonic_weighted = 0.0
        hedonic_mass = 0.0
        thermodynamic_rows = self._thermodynamic_material_map(fv)

        # Ellena/Roudnitska principle: materials in the shadow zone are not
        # "notes" — they are compositional grain below perception threshold.
        # They contribute to trace_score but NOT to effect-per-note, natural,
        # premium, architecture, or restraint components.
        for name, pct in eff.items():
            norm = normalize_name(name)
            prof = get_profile(name)

            # Classify the perceptual zone from canonical headspace OAV. This
            # preserves one ppm -> mole fraction -> gamma*VP -> air ODT chain
            # instead of mixing concentrate ppm with a profile-level gamma.
            is_shadow = False
            is_silent = False
            dose_ratio = 0.0
            thermo_row = thermodynamic_rows.get(name)
            if thermo_row is not None and thermo_row.oav is not None:
                dose_ratio = max(0.0, float(thermo_row.oav))
                if dose_ratio < 0.1:
                    is_silent = True
                elif dose_ratio <= 1.0:
                    is_shadow = True

            if is_silent:
                # Below 0.1× ODT: ignored entirely (not even shadow).
                continue

            if is_shadow:
                trace_shadow_count += 1
                continue

            # Declared note: participates in all mass/character components.
            is_preblend = any(m in norm for m in _preblend_markers)
            if is_preblend:
                preblend_mass += pct

            is_natural = any(norm.endswith(s) for s in _natural_suffixes)
            if is_natural and not is_preblend:
                natural_mass += pct

            if norm in _premium_synthetics:
                premium_mass += pct

            n_declared += 1

            if prof:
                # Turin/Sanchez effect-per-note with Hill-saturating OAV.
                # When ODT is known, reward materials in the productive
                # perceptual band (OAV ratio 1–10) with a saturating curve
                # rather than raw log(1+mass). n=1.5, K=3.0 places the
                # half-max at 3× ODT, plateau ≈10× ODT — matching the
                # psychophysical compression of ORN response.
                strong = sum(max(0.0, v - 4.0) for v in prof.character.values())
                if dose_ratio > 0:
                    K = 3.0  # noqa: N806
                    n = 1.5
                    impact = (dose_ratio**n) / (dose_ratio**n + K**n)
                    # Scale so saturation ≈ log1p(10) ≈ 2.4 (keeps the
                    # score range compatible with the pre-Hill calibration)
                    effect_sum += strong * impact * 2.4
                else:
                    # No ODT data: retain the legacy mass-based form.
                    effect_sum += strong * math.log1p(pct)

                dom = prof.dominant_character()
                if dom and dom != "neutral":
                    dominant_counts[dom] = dominant_counts.get(dom, 0) + 1

                if prof.or_family:
                    or_family_counts[prof.or_family] = or_family_counts.get(prof.or_family, 0) + 1

                hed = getattr(prof, "hedonic", 0.0) or 0.0
                hedonic_weighted += hed * pct
                hedonic_mass += pct

                if prof.role:
                    roles_used.add(prof.role)
                if prof.role == "volume" and pct > 5.0:
                    n_filler += 1
                    filler_mass += pct

                note = prof.note if prof.note in note_mass else "heart"
                note_mass[note] += pct
            else:
                if pct > 5.0:
                    n_filler += 1
                    filler_mass += pct

        # ── 1. Natural baseline (0–20) — Aftel/Arctander ──
        nat_frac = natural_mass / total_pct
        if nat_frac <= 0.05:
            natural_score = (nat_frac / 0.05) * 8.0
        elif nat_frac <= 0.12:
            natural_score = 8.0 + (nat_frac - 0.05) / 0.07 * 6.0
        elif nat_frac <= 0.30:
            natural_score = 14.0 + (nat_frac - 0.12) / 0.18 * 6.0
        elif nat_frac <= 0.40:
            natural_score = 20.0
        else:
            # rustic over-natural penalty
            natural_score = max(12.0, 20.0 - (nat_frac - 0.40) * 20.0)

        # ── 2. Premium captive density (0–20) — Boix Camps/Burr ──
        prem_frac = premium_mass / total_pct
        premium_score = min(prem_frac / 0.25 * 20.0, 20.0)
        preblend_frac = preblend_mass / total_pct
        premium_score = max(0.0, premium_score - preblend_frac * 30.0)

        # ── 3. Carles architecture (0–15) — Carles/Roudnitska ──
        note_total = sum(note_mass.values()) or 1.0
        note_frac = {k: v / note_total for k, v in note_mass.items()}
        target = {"top": 0.18, "heart": 0.42, "base": 0.40}
        deviation = sum(abs(note_frac[k] - target[k]) for k in target)
        architecture_score = max(0.0, 15.0 - deviation * 15.0)

        # ── 4. Effect-per-note (0–15) — Turin/Sanchez ──
        epn = effect_sum / max(n_declared, 1)
        effect_score = min(epn / 5.0 * 15.0, 15.0)
        filler_penalty = min(filler_mass / 5.0 * 2.0, 10.0)
        effect_score = max(0.0, effect_score - filler_penalty)
        # Hedonic nudge: mass-weighted mean pleasantness scales the
        # effect band by up to ±15%. Keeps EPN dominant but rewards
        # compositions whose materials are individually pleasant.
        if hedonic_mass > 0:
            mean_hed = hedonic_weighted / hedonic_mass
            effect_score *= max(0.85, min(1.15, 1.0 + mean_hed * 0.03))
            effect_score = min(effect_score, 15.0)

        # ── 5. Trace complexity shadow (0–15) — Ellena/Roudnitska ──
        # DOSE-RESPONSIVE: OAV membership changes with dose.
        if trace_shadow_count < 2:
            trace_score = trace_shadow_count / 2.0 * 6.0
        elif trace_shadow_count <= 10:
            trace_score = 6.0 + (trace_shadow_count - 2) / 8.0 * 9.0
        elif trace_shadow_count <= 14:
            trace_score = 15.0 - (trace_shadow_count - 10) * 0.5
        else:
            trace_score = max(8.0, 13.0 - (trace_shadow_count - 14) * 0.5)

        # ── 6. Compositional restraint (0–15) — Ellena/Roudnitska ──
        redundancy = sum(max(0, c - 2) for c in dominant_counts.values())
        # OR-family overload: if more than 3 materials share an olfactory-
        # receptor bin (e.g., 4+ musks or 4+ citrus), perceptual masking
        # causes the marginal contribution to collapse. Penalise to guide
        # the optimiser away from redundant stacking.
        or_overload = sum(max(0, c - 3) for c in or_family_counts.values())
        role_breadth = min(len(roles_used) * 2.0, 8.0)
        filler_frac = n_filler / max(n_declared, 1)
        restraint_score = max(
            0.0, 7.0 + role_breadth - redundancy * 0.8 - or_overload * 1.0 - filler_frac * 20.0
        )
        restraint_score = min(restraint_score, 15.0)

        score = (
            natural_score
            + premium_score
            + architecture_score
            + effect_score
            + trace_score
            + restraint_score
        )
        return round(max(0.0, min(score, 100.0)), 1)

    def score_texture(self, fv: FormulaVector) -> float:
        """Score texture (0-100): the haptic / sensory feel of the composition.

        Perfumery literature anchors
          • Roudnitska (1980): "grain" of a perfume — the tactile
            resolution of its materials; too-smooth = flat, too-rough =
            vulgar. Grain is a function of character-dimension variety
            plus VP staggering.
          • Ellena, *Perfume: The Alchemy of Scent* (2011): transparency
            as texture — an editing principle where subtraction (fewer
            materials, each at its own register) reads as silk rather
            than cotton wool.
          • Turin & Sanchez, *Perfumes: The Guide* (2008, 2018): texture
            vocabulary ("grainy," "silky," "powdery," "angular,"
            "architectural") mapped to character dimensions — powder +
            creamy = silk, woody + smoky − creamy = architectural.
          • Laudamiel (interviews, 2015–2020): category-specific texture
            targets — orientals are rounded / enveloping, chypres are
            mossy-dry with cushion, florals are silky-transparent.

        Evaluates ACTUAL sensory texture from character dimension profiles.
        Different perfume categories have different ideal textures:
          - Oriental/gourmand → rounded, creamy, enveloping (warmth + sweetness + creamy)
          - Fresh/citrus → crisp, clean, transparent (freshness + transparency)
          - Woody/leather → dry, architectural, angular (woody + smoky - creamy)
          - Floral → silky, soft, skin-like (floral + creamy + transparency)
          - Chypre → mossy-dry tension with cushion (green + woody + creamy)

        Components:
          Texture coherence (35 pts) — dimensions reinforce rather than fight
          Sensory richness (25 pts) — multiple tactile facets present
          Category fit (20 pts) — texture matches detected style
          Roundness/harshness balance (20 pts) — intentional, not accidental

        Range: 0-100.
        """
        # ── Compute weighted-average character dimensions ──
        dim_sums: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        total_pct = 0.0
        oav_data = self._thermodynamic_oav_map(fv)
        eff = fv.effective_ingredients()
        for name, pct in eff.items():
            prof = get_profile(name)
            if prof and prof.character:
                oav = float(oav_data.get(name, 0) or 0)
                weight = min(oav, 1.0) if oav >= 1.0 else 0.0
                for d in DIMENSIONS:
                    dim_sums[d] += prof.character.get(d, 0) * pct * weight
                total_pct += pct * weight
        if total_pct == 0:
            return 30.0
        dims = {d: v / total_pct for d, v in dim_sums.items()}

        # ── Derived texture axes (from character dimensions) ──
        roundness = (
            dims.get("creamy", 0) + dims.get("warmth", 0) + dims.get("sweetness", 0) * 0.5
        ) / 2.5
        crispness = (
            dims.get("freshness", 0) + dims.get("transparency", 0) + dims.get("green", 0) * 0.5
        ) / 2.5
        dryness = dims.get("woody", 0) + dims.get("smoky", 0) * 0.7 - dims.get("creamy", 0) * 0.3
        silkiness = (
            dims.get("floral", 0) * 0.6
            + dims.get("creamy", 0) * 0.4
            + dims.get("transparency", 0) * 0.3
        )
        harshness = (
            dims.get("spicy", 0) * 0.5 + dims.get("animalic", 0) * 0.5 + dims.get("smoky", 0) * 0.3
        )
        # Clamp derived axes
        roundness = max(0, min(roundness, 10))
        crispness = max(0, min(crispness, 10))
        dryness = max(0, min(dryness, 10))
        silkiness = max(0, min(silkiness, 10))
        harshness = max(0, min(harshness, 10))

        # ── 1. Texture coherence (0-35) ──
        # Materials should reinforce a coherent texture, not fight
        # Competing axes: roundness vs crispness, silkiness vs harshness
        round_crisp_tension = abs(roundness - crispness)
        silk_harsh_tension = abs(silkiness - harshness)
        # Some tension is fine (creates interest), but too much = incoherent
        coherence = 35
        if round_crisp_tension > 5:
            coherence -= (round_crisp_tension - 5) * 3
        if silk_harsh_tension > 4:
            coherence -= (silk_harsh_tension - 4) * 3
        coherence = max(0, coherence)

        # ── 2. Sensory richness (0-25) ──
        # How many tactile facets are meaningfully present (> 2.0)?
        tactile_facets = [roundness, crispness, dryness, silkiness]
        active_facets = sum(1 for f in tactile_facets if f > 2.0)
        richness = min(active_facets * 7, 25)

        # ── 3. Category fit (0-20) ──
        # What texture does this style call for?
        style = self.detect_style(fv)
        fit = 10  # default neutral
        if style in ("oriental", "gourmand"):
            # Warm, rounded, enveloping
            fit = min(20, roundness * 2.5) if roundness > 2 else 5
        elif style in ("fresh", "citrus", "aquatic", "cologne"):
            # Crisp, clean, transparent
            fit = min(20, crispness * 2.5) if crispness > 2 else 5
        elif style in ("woody", "leather", "chypre"):
            # Dry, architectural
            fit = min(20, max(dryness, 0) * 2.5) if dryness > 1 else 5
        elif style == "iris_crystalline":
            # Transparent, crisp, glass-like — same crispness axis as fresh
            fit = min(20, crispness * 2.5) if crispness > 2 else 5
        elif style in ("floral", "white_floral", "rose_oud", "soliflore", "iris_powdery"):
            # Silky, soft, powdery
            fit = min(20, silkiness * 2.5) if silkiness > 2 else 5
        elif style in ("skin_scent", "linear"):
            # Smooth, skin-like (roundness + silkiness - harshness)
            smoothness = (roundness + silkiness - harshness) / 2
            fit = min(20, smoothness * 3.0) if smoothness > 1.5 else 5

        # ── 4. Roundness/harshness balance (0-20) ──
        # Harshness OK in leather/woody, but should be tempered in florals
        balance = 15
        if style in (
            "floral",
            "white_floral",
            "fresh",
            "skin_scent",
            "soliflore",
            "iris_powdery",
            "iris_crystalline",
        ):
            if harshness > 3:
                balance -= (harshness - 3) * 3
        elif style in ("leather", "woody", "chypre"):
            # Some harshness is desirable — reward controlled edge
            if 1.5 < harshness < 4:
                balance = 20
        # Universal: extreme harshness (>6) penalizes any style
        if harshness > 6:
            balance -= (harshness - 6) * 4
        balance = max(0, min(balance, 20))

        score = coherence + richness + fit + balance
        return round(max(0, min(score, 100)), 1)

    def score_stacking_depth(self, fv: FormulaVector) -> float:
        """Score stacking depth (0-100): perceptual depth via cross-adaptation.

        Perfumery literature anchors
          • Laing & Francis, "The capacity of humans to identify odours
            in mixtures," *Physiology & Behavior* 46 (1989): three-
            material mixtures already exceed human identification
            limits — proper stacking CREATES depth by making the
            individual components unresolvable.
          • Laing, "Perceptual and chemical similarities of mixtures of
            odors" (1991): cross-adaptation fatigues the receptor for
            one material while a stack partner remains audible — a
            second sandalwood (Ebanol + Javanol) reads LONGER than
            either alone.
          • Roudnitska on Diorissimo / *Le Parfum* (1980): deep stacking
            of watery muguet materials (hydroxycitronellal + bourgeonal
            + mayol + farnesol) created an otherwise unsynthesisable
            lily-of-the-valley illusion.
          • Givaudan "chorus" theory (2000s): ≥3 materials in the same
            olfactive family, declared doses, different VP/CLogP curves
            produce a temporal cascade that reads as ONE deep note.

        A trained perfumer builds depth by stacking multiple materials from the
        same chemical family at different registers. Musk stacking (macrocyclic
        depth + polycyclic projection + nitro powder), floral stacking (muguet +
        jasmine + rose facets), wood stacking (abstract + architectural + natural).

        Each stack is scored on:
          - Stack count (2+ materials from same family = 1 stack)
          - Register diversity within each stack (top/heart/base spread)
          - Role diversity within each stack (character + modifier + fixative)

        NOT raw ingredient count. A formula with 40 materials but no intentional
        stacking scores lower than 12 materials with 4 well-built stacks.

        Components:
          Number of stacks (30 pts) — how many families are deliberately layered
          Register spread (30 pts) — volatility diversity within stacks
          Role complementarity (20 pts) — functional diversity within stacks
          Stack quality bonus (20 pts) — 3+ deep stacks = master-level layering

        Range: 0-100.
        """
        from engine.name_utils import normalize_name

        oav_data = self._thermodynamic_oav_map(fv)

        # Map each formula material to its cross-adaptation group(s)
        # A material can appear in multiple groups (rare but possible)
        material_groups: dict[str, list[str]] = {}  # group_name → [material_names]
        eff = fv.effective_ingredients()

        for name in eff:
            oav = float(oav_data.get(name, 0) or 0)
            if oav < 1.0:
                continue
            norm = normalize_name(name)
            for group_name, members in CROSS_ADAPTATION_GROUPS.items():
                member_norms = [normalize_name(m) for m in members]
                if norm in member_norms:
                    material_groups.setdefault(group_name, []).append(name)

        # Also check knowledge graph odor_family for materials not in
        # cross-adaptation groups (catches EOs, FTECs, etc.)
        _family_map = {
            "musk": "musk_extra",
            "floral": "floral_extra",
            "woody": "woody_extra",
            "amber": "amber_extra",
            "citrus": "citrus_extra",
            "green": "green_extra",
            "balsamic": "balsamic_extra",
            "spicy": "spicy_extra",
            "powdery": "powdery_extra",
        }
        for name in eff:
            norm = normalize_name(name)
            # Skip if already classified
            already = any(name in members for members in material_groups.values())
            if already:
                continue
            mat = _lookup_material(name)
            if mat:
                fam = (
                    (mat.get("odor_family") or "").lower().split()[0]
                    if mat.get("odor_family")
                    else ""
                )
                mapped = _family_map.get(fam)
                if mapped:
                    material_groups.setdefault(mapped, []).append(name)

        # ── Identify stacks (groups with 2+ materials) ──
        stacks: list[tuple[str, list[str]]] = [
            (group, members) for group, members in material_groups.items() if len(members) >= 2
        ]
        n_stacks = len(stacks)

        # ── 1. Number of stacks (0-30) ──
        # 1 stack = 8, 2 = 16, 3 = 24, 4+ = 30
        stack_count_score = min(n_stacks * 8, 30)

        # ── 2. Register spread within stacks (0-30) ──
        # For each stack, check if materials span top/heart/base
        spread_score = 0.0
        for group, members in stacks:
            notes_in_stack: set[str] = set()
            for name in members:
                prof = get_profile(name)
                if prof and prof.note:
                    notes_in_stack.add(prof.note)
            # 1 register = 0, 2 = 5, 3 = 10 (full spread)
            spread_score += min((len(notes_in_stack) - 1) * 5, 10)
        spread_score = min(spread_score, 30)

        # ── 3. Role complementarity within stacks (0-20) ──
        # Materials in same family but different roles = intentional layering
        role_score = 0.0
        for group, members in stacks:
            roles_in_stack: set[str] = set()
            for name in members:
                prof = get_profile(name)
                if prof and prof.role:
                    roles_in_stack.add(prof.role)
            # 1 role = 0, 2 = 3, 3+ = 7
            if len(roles_in_stack) >= 3:
                role_score += 7
            elif len(roles_in_stack) == 2:
                role_score += 3
        role_score = min(role_score, 20)

        # ── 4. Stack quality bonus (0-20) ──
        # Deep stacks (3+ materials) show master-level layering
        deep_stacks = sum(1 for _, members in stacks if len(members) >= 3)
        quality_bonus = min(deep_stacks * 8, 20)

        score = stack_count_score + spread_score + role_score + quality_bonus
        return round(max(0, min(score, 100)), 1)

    def formula_character_radar(self, fv: FormulaVector) -> dict[str, float]:
        """Compute the weighted-average character radar for a formula.
        Returns {dimension_name: 0-10 score}."""
        # Per-FV cache: radar is a pure function of ingredient percentages
        cache_key = id(fv)
        if hasattr(self, "_radar_cache_key") and self._radar_cache_key == cache_key:
            return self._radar_cache_val
        dim_sums: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
        total_pct = 0.0
        eff = fv.effective_ingredients()
        for name, pct in eff.items():
            prof = get_profile(name)
            if prof and prof.character:
                for d in DIMENSIONS:
                    dim_sums[d] += prof.character.get(d, 0) * pct
                total_pct += pct
        if total_pct == 0:
            result = {d: 0.0 for d in DIMENSIONS}
        else:
            result = {d: round(v / total_pct, 2) for d, v in dim_sums.items()}
        self._radar_cache_key = cache_key
        self._radar_cache_val = result
        return result

    # ── Science module axes (5 new scored dimensions) ──

    @staticmethod
    def _formula_vector_fingerprint(
        fv: FormulaVector,
    ) -> tuple[tuple[tuple[str, float], ...], tuple[tuple[str, float], ...]]:
        """Return the raw-stock identity used to bind an injected state."""
        ingredients = tuple(
            sorted(
                (str(name), max(0.0, float(value or 0.0)))
                for name, value in fv.ingredients.items()
            )
        )
        dilutions = tuple(
            sorted(
                (str(name), float(value))
                for name, value in fv.dilutions.items()
                if value is not None
            )
        )
        return ingredients, dilutions

    @classmethod
    def _validate_formula_state_override(
        cls,
        fv: FormulaVector,
        formula_state: FormulaState,
    ) -> None:
        """Reject injected state that does not describe this raw-stock vector."""
        vector_raw = {
            str(name): max(0.0, float(value or 0.0))
            for name, value in fv.ingredients.items()
            if float(value or 0.0) > 0.0
        }
        state_raw = {
            row.name: max(0.0, float(row.raw_ul))
            for row in formula_state.materials
            if float(row.raw_ul) > 0.0
        }
        if set(vector_raw) != set(state_raw):
            raise ValueError(
                "formula_state material labels do not match FormulaVector raw stocks"
            )

        vector_total = sum(vector_raw.values())
        state_total = sum(state_raw.values())
        if (vector_total > 0.0) != (state_total > 0.0):
            raise ValueError("formula_state raw total does not match FormulaVector")
        if vector_total > 0.0 and state_total > 0.0:
            for name in vector_raw:
                vector_fraction = vector_raw[name] / vector_total
                state_fraction = state_raw[name] / state_total
                if not math.isclose(
                    vector_fraction,
                    state_fraction,
                    rel_tol=1e-9,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        f"formula_state raw proportion does not match FormulaVector: {name}"
                    )

        state_dilutions = {
            row.name: float(row.dilution)
            for row in formula_state.materials
            if float(row.raw_ul) > 0.0
        }
        for name in vector_raw:
            vector_dilution = float(fv.dilutions.get(name, 1.0) or 1.0)
            if not math.isclose(
                vector_dilution,
                state_dilutions.get(name, 1.0),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"formula_state dilution does not match FormulaVector: {name}"
                )

    def _formula_state_override_matches(self, fv: FormulaVector) -> bool:
        """Return whether an injected state remains bound to this vector."""
        return (
            getattr(self, "_formula_state_override", None) is not None
            and getattr(self, "_formula_state_override_fv", None) is fv
            and getattr(self, "_formula_state_override_fingerprint", None)
            == self._formula_vector_fingerprint(fv)
        )

    def _science_ingredients(self, fv: FormulaVector) -> tuple[dict[str, float], dict[str, float]]:
        """Extract raw stock µL and stock fractions without double dilution."""
        override = getattr(self, "_formula_state_override", None)
        if self._formula_state_override_matches(fv):
            return (
                {row.name: float(row.raw_ul) for row in override.materials},
                {
                    row.name: float(row.dilution)
                    for row in override.materials
                    if float(row.dilution) != 1.0
                },
            )

        raw = {
            str(name): max(0.0, float(pct or 0.0))
            for name, pct in fv.ingredients.items()
        }
        dilution_items = tuple(
            sorted(
                (str(name), float(value))
                for name, value in fv.dilutions.items()
                if value is not None
            )
        )
        cache_key = (
            tuple(sorted(raw.items())),
            dilution_items,
            float(self.batch_volume_ml),
        )
        if hasattr(self, "_sci_cache_key") and self._sci_cache_key == cache_key:
            return self._sci_cache_val
        # Convert percentages back to absolute µL using the configured batch
        # volume. Previously hardcoded to 10 mL — this caused silently-wrong
        # OAV values on any other batch size (e.g. 15 mL split, 30 mL build).
        total = sum(raw.values()) or 1.0
        batch_ul = self.batch_volume_ml * 1000.0
        ingredients = {name: (pct / total) * batch_ul for name, pct in raw.items()}
        # Dilution comes from the formula vector (FormulaVector.dilutions), not
        # ingredient profiles — profile-level dilution fields were removed as an
        # architectural fix (stock prep metadata doesn't belong on a molecule).
        dilutions = {
            str(name): float(value)
            for name, value in fv.dilutions.items()
            if value is not None and float(value) != 1.0
        }
        self._sci_cache_key = cache_key
        self._sci_cache_val = (ingredients, dilutions)
        return ingredients, dilutions

    def _thermodynamic_state(self, fv: FormulaVector) -> FormulaState:
        """Return the canonical physical state for this optimizer formula."""
        from ..pipeline.formula_state import build_formula_state

        override = getattr(self, "_formula_state_override", None)
        if self._formula_state_override_matches(fv):
            return override
        ingredients, dilutions = self._science_ingredients(fv)
        return build_formula_state(
            ingredients,
            dilutions,
            batch_volume_ml=self.batch_volume_ml,
        )

    def _thermodynamic_material_map(self, fv: FormulaVector) -> dict[str, MaterialState]:
        """Index canonical state rows by the exact formula label."""
        return {row.name: row for row in self._thermodynamic_state(fv).materials}

    def _thermodynamic_oav_map(self, fv: FormulaVector) -> dict[str, float]:
        """Return state OAVs, with same-formula release authority when supplied."""
        values = {
            row.name: float(row.oav)
            for row in self._thermodynamic_state(fv).materials
            if row.oav is not None
        }
        if self._formula_state_override_matches(fv):
            values.update(getattr(self, "_material_oavs", {}) or {})
        return values

    def _thermodynamic_projection_properties(
        self, fv: FormulaVector
    ) -> tuple[float | None, float | None]:
        """Return active-mass weighted gamma*VP and gamma*VP/sqrt(MW)."""
        vp_weight = 0.0
        vp_sum = 0.0
        vi_weight = 0.0
        vi_sum = 0.0
        for row in self._thermodynamic_state(fv).materials:
            weight = max(0.0, float(row.active_g or 0.0))
            vp = row.vp_pure_pa
            if weight <= 0 or vp is None or vp <= 0:
                continue
            effective_vp = float(row.gamma) * float(vp)
            vp_sum += weight * effective_vp
            vp_weight += weight
            if row.mw_g_mol is not None and row.mw_g_mol > 0:
                vi_sum += weight * effective_vp / math.sqrt(float(row.mw_g_mol))
                vi_weight += weight
        avg_vp = vp_sum / vp_weight if vp_weight > 0 else None
        volatility_index = vi_sum / vi_weight if vi_weight > 0 else None
        return avg_vp, volatility_index

    def score_safety(self, fv: FormulaVector) -> float:
        """IFRA compliance + allergen + sensitization risk (0-100)."""
        ingredients, dilutions = self._science_ingredients(fv)
        report = score_ifra_compliance(ingredients, dilutions)
        self._last_safety_report = report
        return report.score

    def score_skin_performance(self, fv: FormulaVector) -> float:
        """Skin reservoir kinetics + fabric substantivity (0-100)."""
        ingredients, dilutions = self._science_ingredients(fv)
        report = score_skin_interaction(ingredients, dilutions)
        self._last_skin_report = report
        return report.score

    def score_hedonic(self, fv: FormulaVector) -> float:
        """Intrinsic pleasantness / hedonic valence (0-100)."""
        ingredients, dilutions = self._science_ingredients(fv)
        report = score_hedonic(ingredients, dilutions)
        self._last_hedonic_report = report
        return report.score

    def score_perceptual_clarity(self, fv: FormulaVector) -> float:
        """Mixture suppression + cross-adaptation + genetic anosmia (0-100)."""
        ingredients, dilutions = self._science_ingredients(fv)
        report = score_psychophysics(ingredients, dilutions)
        self._last_psychophysics_report = report
        return report.score

    def score_photorealism(self, fv: FormulaVector) -> float:
        """Score photorealistic transparency (0-100) — how glass-like and
        high-definition the formula reads perceptually.

        Perfumery literature anchors
          • Ellena, *The Diary of a Nose* (2013) & *Perfume: The Alchemy
            of Scent* (2011): "minimalism" / "photographic clarity" — a
            composition is photorealistic when each material reads as a
            distinct, sharply-delineated channel with visible negative
            space around it, like looking through glass rather than
            frosted plastic.
          • Laudamiel, interviews on Humiecki & Graef / Editions de
            Parfums (2010s): photorealism = "I can see every brushstroke"
            — no muddy overlap of character axes, every register enters
            and exits at its own VP-driven moment.
          • Hermès "haiku" principle (Ellena house style, 2000s
            onward): 12–20 declared materials, ≤3 per olfactive register,
            deliberate negative space in warmth/sweetness/animalic axes.

        Photorealism ≠ perceptual clarity.  Clarity asks "can you perceive
        distinct notes?" (Laing channels).  Photorealism asks "does it feel
        like looking through glass?" — every material sharply delineated in
        time and character, with deliberate negative space.

        Components:
          Transparency dominance (25 pts) — mass-weighted transparency axis
              minus opacifying dimensions (warmth, sweetness, smoky, animalic)
          Temporal resolution (20 pts) — VP diversity across materials creates
              time-domain pixels; each material enters/exits at its own moment
          Channel purity (25 pts) — cross-adaptation groups kept lean (≤2
              significant members); many channels, few materials per channel
          Negative space (15 pts) — what the formula does NOT have; absence
              of heavy, opaque, dark dimensions
          Dose discipline (15 pts) — powerhouses controlled, trace materials
              not overdosed, no single material dominates >30% of mass

        Range: 0-100.
        """
        import math as _math

        from engine.name_utils import normalize_name

        thermodynamic_state = self._thermodynamic_state(fv)
        thermodynamic_rows = {row.name: row for row in thermodynamic_state.materials}
        oav_data = self._thermodynamic_oav_map(fv)
        eff = fv.effective_ingredients()
        if not eff:
            return 20.0

        n_materials = len(eff)
        n_perceptible = sum(1 for name in eff if float(oav_data.get(name, 0) or 0) >= 1.0)
        percept_ratio = n_perceptible / max(n_materials, 1)
        total_pct = sum(eff.values()) or 1.0

        # ── 1. Transparency dominance (0-25) ──
        radar = self.formula_character_radar(fv)
        positive_axes = (
            radar.get("transparency", 0) * 1.5
            + radar.get("freshness", 0) * 0.6
            + radar.get("radiance", 0) * 0.8
            + radar.get("green", 0) * 0.3
        ) * percept_ratio
        negative_axes = (
            radar.get("warmth", 0) * 0.8
            + radar.get("sweetness", 0) * 0.9
            + radar.get("smoky", 0) * 1.0
            + radar.get("animalic", 0) * 0.7
            + radar.get("creamy", 0) * 0.4
        )
        # Net transparency: positive minus negative, scaled to 0-25
        # A purely transparent formula: positive ~15, negative ~0 → 25
        # A warm-sweet formula: positive ~3, negative ~10 → ~0
        net_transparency = max(0, positive_axes - negative_axes)
        transparency_score = min(net_transparency * 1.7, 25)

        # ── 2. Temporal resolution (0-20) ──
        # VP diversity: materials at many different vapor pressures create
        # time-domain resolution.  Measured by how many VP decades are covered
        # and how evenly materials spread across them.
        # Uses FormulaState's per-formula gamma-corrected VP.
        vp_values = []
        for name, pct in eff.items():
            row = thermodynamic_rows.get(name)
            if row is not None and row.vp_pure_pa is not None and row.vp_pure_pa > 0:
                vp_eff = float(row.gamma) * float(row.vp_pure_pa)
                vp_values.append((name, _math.log10(vp_eff), pct))

        temporal_score = 0.0
        if len(vp_values) >= 3:
            log_vps = [lv for _, lv, _ in vp_values]
            vp_range = max(log_vps) - min(log_vps)  # decades spanned
            # Decade bins: [-4,-3), [-3,-2), [-2,-1), [-1,0), [0,1), [1,+)
            bins = {}
            for _, lv, pct in vp_values:
                decade = int(_math.floor(lv))
                bins[decade] = bins.get(decade, 0) + pct
            n_decades = len(bins)
            # Range bonus: 3 decades = good, 4+ = excellent
            range_pts = min(vp_range * 3.5, 12)
            # Evenness: how evenly mass distributes across bins
            if n_decades > 1:
                bin_vals = list(bins.values())
                mean_bin = sum(bin_vals) / len(bin_vals)
                variance = sum((v - mean_bin) ** 2 for v in bin_vals) / len(bin_vals)
                cv = _math.sqrt(variance) / max(mean_bin, 0.01)
                # Lower CV = more even = more photorealistic
                evenness_pts = max(0, 8 - cv * 4)
            else:
                evenness_pts = 0
            temporal_score = min(range_pts + evenness_pts, 20)
        elif len(vp_values) >= 1:
            temporal_score = 5.0  # minimal data

        # ── 3. Channel purity (0-25) ──
        # Cross-adaptation groups: photorealism needs many channels with
        # few materials per channel.  A group with 3+ significant members
        # (>10% of group mass) causes internal masking → blur.
        ingredients_ul, dilutions = self._science_ingredients(fv)
        group_members: dict[str, list[tuple[str, float]]] = {}
        for name, ul in ingredients_ul.items():
            norm = normalize_name(name)
            for grp_name, members in CROSS_ADAPTATION_GROUPS.items():
                member_norms = [normalize_name(m) for m in members]
                if norm in member_norms:
                    group_members.setdefault(grp_name, []).append((name, ul))

        active_groups = 0
        crowded_groups = 0
        for grp_name, mem_list in group_members.items():
            if len(mem_list) < 1:
                continue
            active_groups += 1
            grp_total = sum(ul for _, ul in mem_list)
            if grp_total == 0:
                continue
            significant = sum(1 for _, ul in mem_list if ul / grp_total > 0.10)
            if significant >= 3:
                crowded_groups += 1

        # Many channels + few crowded = high purity
        if active_groups > 0:
            channel_pts = min(active_groups * 2.5, 15)
            purity_ratio = 1.0 - (crowded_groups / active_groups)
            purity_pts = purity_ratio * 10
            channel_score = min(channel_pts + purity_pts, 25)
        else:
            channel_score = 5.0

        # ── 4. Negative space (0-15) ──
        # Photorealism rewards ABSENCE of opacifying dimensions.
        # warmth < 2, sweetness < 2, smoky < 1, animalic < 1 = full marks.
        warmth_penalty = max(0, radar.get("warmth", 0) - 2.0) * 2.0
        sweet_penalty = max(0, radar.get("sweetness", 0) - 2.0) * 2.0
        smoke_penalty = max(0, radar.get("smoky", 0) - 0.5) * 3.0
        animal_penalty = max(0, radar.get("animalic", 0) - 0.5) * 3.0
        creamy_penalty = max(0, radar.get("creamy", 0) - 2.5) * 1.5
        total_opacity_penalty = (
            warmth_penalty + sweet_penalty + smoke_penalty + animal_penalty + creamy_penalty
        )
        negative_space_score = max(0, 15 - total_opacity_penalty)

        # ── 5. Dose discipline (0-15) ──
        # No single material should dominate >30% of concentrate mass.
        # Trace-dosed materials (dilutions < 0.1) should be ≤5% of mass.
        # Powerhouses (VP > 0.1 Pa) should be ≤25% of mass combined.
        dose_score = 15.0
        max_pct = max(eff.values())
        if max_pct / total_pct > 0.30:
            dose_score -= (max_pct / total_pct - 0.30) * 30  # -3 per 10% over
        if max_pct / total_pct > 0.45:
            dose_score -= 3  # additional penalty for heavy dominance

        # Powerhouse check: high effective-headspace-VP materials massed too heavily.
        # Uses γ·VP (activity-corrected) so hydrophobic musks (γ>1) that dominate
        # the headspace disproportionately are counted even if raw VP < 0.1 Pa.
        powerhouse_pct = 0.0
        for name, pct in eff.items():
            row = thermodynamic_rows.get(name)
            if (
                row is not None
                and row.vp_pure_pa is not None
                and float(row.gamma) * float(row.vp_pure_pa) > 0.1
            ):
                powerhouse_pct += pct
        if powerhouse_pct / total_pct > 0.25:
            dose_score -= (powerhouse_pct / total_pct - 0.25) * 15

        dose_score = max(0, min(dose_score, 15))

        score = (
            transparency_score + temporal_score + channel_score + negative_space_score + dose_score
        )
        return round(max(0, min(score, 100)), 1)

    def score_family_alignment(
        self, fv: FormulaVector, family_key: str = "", bracket: str = "EdP"
    ) -> dict:
        """Score how well a formula aligns with its target perfume family taxonomy.

        Uses the complete perfume knowledge taxonomy (engine.knowledge.perfume_knowledge)
        to evaluate pyramid balance, OAV targets, and odour family composition
        against verified family archetypes.

        Args:
            fv: Formula vector with ingredients
            family_key: Target family (e.g. "floral_rose", "fougere_aromatic")
            bracket: Concentration bracket ("EdC", "EdT", "EdP", "Extrait")

        Returns:
            dict with alignment scores and diagnostic data
        """
        from engine.ingredient_intelligence import get_profile
        from engine.knowledge.perfume_knowledge import (
            evaluate_oav_family_targets,
            evaluate_pyramid_balance,
            get_oav_targets,
            resolve_family_key,
        )

        resolved = resolve_family_key(family_key or "floral")
        targets = get_oav_targets(resolved)

        # Build note map from profiles
        note_map: dict[str, str] = {}
        material_families: dict[str, str] = {}
        material_oavs: dict[str, float] = {}
        raw_pct = fv.raw_percentages()

        for name in fv.ingredient_list():
            prof = get_profile(name)
            if prof:
                note_map[name] = getattr(prof, "note", "heart")
                material_families[name] = getattr(prof, "or_family", "unknown")
                # Estimate OAV from formula context
                material_oavs[name] = max(0.0, float(raw_pct.get(name, 0.0)))

        pyramid_eval = evaluate_pyramid_balance(
            raw_pct,
            family=family_key,
            bracket=bracket,
            note_map=note_map,
        )

        top_eval = evaluate_oav_family_targets(material_oavs, material_families, family_key, "top")
        heart_eval = evaluate_oav_family_targets(
            material_oavs, material_families, family_key, "heart"
        )
        base_eval = evaluate_oav_family_targets(
            material_oavs, material_families, family_key, "base"
        )

        # Composite alignment score (0-100)
        pyramid_weight = 0.35
        oav_weights = {"top": 0.20, "heart": 0.25, "base": 0.20}

        pyramid_score = pyramid_eval.overall_fit * pyramid_weight
        oav_score = sum(
            eval_obj.overall_fit * oav_weights[window]
            for window, eval_obj in [("top", top_eval), ("heart", heart_eval), ("base", base_eval)]
        )
        combined = (
            (pyramid_score + oav_score) * 100.0 / (pyramid_weight + sum(oav_weights.values()))
        )

        return {
            "family_key": resolved,
            "bracket": bracket,
            "combined_score": round(combined, 1),
            "pyramid": pyramid_eval.as_dict(),
            "oav_targets": {
                "top": top_eval.as_dict(),
                "heart": heart_eval.as_dict(),
                "base": base_eval.as_dict(),
            },
            "available_targets": {k: list(v.keys()) for k, v in (targets or {}).items()},
        }

    def _run_enhancer_modules(self, fv: FormulaVector) -> dict:
        """Run trigeminal, dose-response, and diffusion modules for diagnostics.

        These enhance existing axes rather than creating new ones:
          trigeminal → texture enhancement
          dose_response → complexity enhancement
          diffusion → sillage enhancement
        """
        ingredients, dilutions = self._science_ingredients(fv)
        self._last_trigeminal_report = score_trigeminal(ingredients, dilutions)
        total_ul = sum(ingredients.values())
        self._last_dose_report = score_dose_response(ingredients, dilutions, total_ul)
        # Replace each diffusion row's reference gamma with FormulaState's
        # per-formula value.
        gamma_map = {
            row.name: float(row.gamma)
            for row in self._thermodynamic_state(fv).materials
        }
        self._last_diffusion_report = score_diffusion(ingredients, dilutions, gamma_map)
        return {
            "trigeminal": self._last_trigeminal_report,
            "dose_response": self._last_dose_report,
            "diffusion": self._last_diffusion_report,
        }

    # ── Combined scoring ──

    _AXIS_DISPATCH: dict[str, str] = {
        "longevity": "score_longevity",
        "sillage": "score_sillage",
        "synergy": "score_synergy",
        "luxury": "score_luxury",
        "texture": "score_texture",
        "stacking_depth": "score_stacking_depth",
        "skin_performance": "score_skin_performance",
        "perceptual_clarity": "score_perceptual_clarity",
        "photorealism": "score_photorealism",
    }

    def score_axis(self, fv: FormulaVector, axis: str) -> float:
        """Score a single axis without running enhancers or temporal.

        Used for fast pre-screening in the recommendation engine.
        """
        if axis == "hedonic":
            raise ValueError("hedonic is evidence-gated")
        method_name = self._AXIS_DISPATCH.get(axis)
        if method_name is None:
            return 0.0
        return getattr(self, method_name)(fv)

    def score(
        self,
        fv: FormulaVector,
        *,
        formula_state: FormulaState | None = None,
    ) -> dict[str, object]:
        """Compute active diagnostics with liking explicitly NOT_TESTED."""

        if self.weights.hedonic != 0:
            raise ValueError("hedonic is evidence-gated")
        return self._score_impl(
            fv,
            formula_state=formula_state,
            objective_weights=self.weights.as_dict(),
            include_legacy_hedonic=False,
        )

    def score_legacy_replay(
        self,
        fv: FormulaVector,
        *,
        formula_state: FormulaState | None = None,
        weights: LegacyObjectiveWeightsV1 | None = None,
    ) -> dict[str, object]:
        """Reproduce the frozen V1 heuristic payload for historical replay."""

        legacy_weights = weights or LegacyObjectiveWeightsV1()
        return self._score_impl(
            fv,
            formula_state=formula_state,
            objective_weights=legacy_weights.as_dict(),
            include_legacy_hedonic=True,
        )

    def _score_impl(
        self,
        fv: FormulaVector,
        *,
        formula_state: FormulaState | None = None,
        objective_weights: dict[str, float],
        include_legacy_hedonic: bool,
    ) -> dict[str, object]:
        """Compute all scores with axis-specific synergy pre-multipliers.

        Synergy is NOT a standalone axis. It modifies other axes:
          sillage pairs -> boost sillage
          depth pairs   -> boost stacking_depth + skin_performance
          texture pairs -> boost texture
          performance pairs -> boost longevity
          complexity pairs -> boost photorealism
          hedonic pairs -> NO EFFECT (hedonic is intrinsic)

        Zero synergy pairs = zero boost = no penalty.
        """
        # Canonical release callers inject their already-built state so every
        # optimizer axis consumes identical thermodynamic/OAV authority.
        if formula_state is not None:
            self._validate_formula_state_override(fv, formula_state)
        self._formula_state_override = formula_state
        self._formula_state_override_fv = fv if formula_state is not None else None
        self._formula_state_override_fingerprint = (
            self._formula_vector_fingerprint(fv)
            if formula_state is not None
            else None
        )

        # Clear per-FV caches for fresh scoring
        self._sfc_cache = {}
        self._last_synergy_detail = None
        unknown = unknown_materials(fv.ingredient_list())

        # Compute base scores first
        scores: dict[str, object] = {
            "longevity": self.score_longevity(fv),
            "sillage": self.score_sillage(fv),
            "synergy_raw": self.score_synergy(fv),
            "luxury": self.score_luxury(fv),
            "texture": self.score_texture(fv),
            "stacking_depth": self.score_stacking_depth(fv),
            "skin_performance": self.score_skin_performance(fv),
            "perceptual_clarity": self.score_perceptual_clarity(fv),
            "photorealism": self.score_photorealism(fv),
        }
        if include_legacy_hedonic:
            scores["hedonic"] = self.score_hedonic(fv)

        # Run enhancer modules (trigeminal, dose-response, diffusion)
        self._run_enhancer_modules(fv)

        # ── Compute per-axis synergy multipliers ──
        # From the last synergy detail, extract per-axis magnitude sums
        sd = self._last_synergy_detail or {}
        axis_total_mag = sd.get("axis_total_magnitude", {})
        if not axis_total_mag and hasattr(self, "_last_synergy_axis_mags"):
            axis_total_mag = self._last_synergy_axis_mags

        # Map synergy axis -> scoring axis with boost factor (capped at 20%)
        _synergy_boost_map = [
            ("sillage", "sillage", 0.04),
            ("depth", "stacking_depth", 0.04),
            ("depth", "skin_performance", 0.03),
            ("texture", "texture", 0.04),
            ("performance", "longevity", 0.04),
            ("complexity", "photorealism", 0.04),
        ]

        synergy_info = {}
        for syn_axis, score_key, factor in _synergy_boost_map:
            total_mag = float(axis_total_mag.get(syn_axis, 0))
            boost = min(total_mag * factor, 0.20)  # cap at 20%
            if boost > 0.001:
                old = scores.get(score_key, 50)
                scores[score_key] = round(old * (1 + boost), 1)
                synergy_info[score_key + "_boost"] = round(boost, 4)

        synergy_info["axis_total_magnitudes"] = axis_total_mag
        scores["_synergy_applied"] = synergy_info

        # Legacy synergy score (informational, not in geometric mean)
        raw_syn = scores.pop("synergy_raw", 50)
        scores["synergy"] = raw_syn

        weights = objective_weights
        total_weight = sum(weights.values()) or 1.0

        # Arithmetic mean
        weighted_sum = sum(scores[k] * weights.get(k, 0) for k in scores if k in weights)
        scores["arithmetic_total"] = round(weighted_sum / total_weight, 1)

        # Geometric mean: ∏(si)^(wi/Σw)
        # Floor scores at 5.0 — a zero-scoring axis is a critical failure
        # that must visibly drag the composite down, not be masked by log(1)=0.
        log_sum = 0.0
        hard_fail_axes: list[str] = []
        for k in scores:
            if k in weights and weights[k] > 0:
                raw = scores[k]
                if raw < 5.0:
                    hard_fail_axes.append(k)
                s = max(raw, 5.0)  # floor at 5 to prevent log(0)
                log_sum += (weights[k] / total_weight) * math.log(s)
        scores["geometric_total"] = round(math.exp(log_sum), 1)
        if hard_fail_axes:
            scores["_hard_fail_axes"] = hard_fail_axes
            scores.setdefault("_diagnostics", []).append(
                f"CRITICAL: {', '.join(hard_fail_axes)} scored <5 (hard failure)"
            )

        # Character radar (not a score, but useful for analysis)
        scores["_radar"] = self.formula_character_radar(fv)
        scores["_style_fingerprint"] = self.style_fingerprint(fv)
        scores["_style_candidates"] = self.detect_style_candidates(fv)

        # Temporal diagnostics + coherence modifier (when available)
        tp = self.temporal_profile
        if tp is not None:
            subliminal = []
            for name, mt in tp.materials.items():
                peak_oav = float(mt.oav.max()) if hasattr(mt.oav, "max") else 0
                if peak_oav < 1.0:
                    subliminal.append((name, round(peak_oav, 2)))

            # Temporal coherence modifier: penalize formulas where many
            # materials are subliminal or where opening/drydown are empty
            n_mats = len(tp.materials)
            n_subliminal = len(subliminal)
            subliminal_ratio = n_subliminal / max(1, n_mats)
            temporal_penalty = 0.0
            temporal_notes: list[str] = []

            # Penalty if >30% of materials are subliminal (wasted mass)
            if subliminal_ratio > 0.3:
                temporal_penalty += (subliminal_ratio - 0.3) * 10.0
                temporal_notes.append(
                    f"{n_subliminal}/{n_mats} materials subliminal "
                    f"({subliminal_ratio:.0%}) — wasted mass"
                )

            # Penalty if opening or drydown character is empty/undefined
            if not tp.opening_character:
                temporal_penalty += 2.0
                temporal_notes.append("Empty opening character — top notes missing")
            if not tp.drydown_character:
                temporal_penalty += 2.0
                temporal_notes.append("Empty drydown character — base notes missing")

            # Apply penalty to geometric total (capped at -8 points)
            if temporal_penalty > 0:
                temporal_penalty = min(temporal_penalty, 8.0)
                scores["geometric_total"] = round(
                    max(1.0, scores["geometric_total"] - temporal_penalty), 1
                )
                scores["total"] = scores["geometric_total"]

            scores["_temporal"] = {
                "longevity_hr": round(tp.longevity_hr, 1),
                "half_life_hr": round(tp.perceptual_half_life_hr, 1),
                "perceptible_count": n_mats - n_subliminal,
                "subliminal": subliminal,
                "transitions": tp.transitions,
                "opening_character": tp.opening_character,
                "drydown_character": tp.drydown_character,
                "coherence_penalty": round(temporal_penalty, 1),
                "coherence_notes": temporal_notes,
            }

        # Synergy diagnostics — reuse from score_synergy() when available
        if hasattr(self, "_last_synergy_detail") and self._last_synergy_detail is not None:
            scores["_synergy_detail"] = self._last_synergy_detail
        elif self.synergy_graph is not None and self.synergy_graph.edges:
            ingredients = fv.ingredient_list()
            stacks = self.synergy_graph.find_synergy_stacks(ingredients, min_stack_size=3)
            clashes = []
            for i, a in enumerate(ingredients):
                for b in ingredients[i + 1 :]:
                    w = self.synergy_graph.pair_synergy(a, b)
                    if w < -0.2:
                        clashes.append((a, b, round(w, 3)))
            scores["_synergy_detail"] = {
                "formula_synergy_score": round(
                    self.synergy_graph.formula_synergy_score(ingredients), 4
                ),
                "synergy_stacks": [(s.name, s.avg_synergy) for s in stacks[:5]],
                "clashes": clashes[:10],
                "total_edges": len(self.synergy_graph.edges),
            }

        # Science module diagnostics (8 modules, rich reports)
        science_diagnostics = {
            "skin": {
                "reservoir_score": getattr(self, "_last_skin_report", None)
                and self._last_skin_report.reservoir_score,
                "substantivity_score": getattr(self, "_last_skin_report", None)
                and self._last_skin_report.substantivity_score,
                "diagnostics": getattr(self, "_last_skin_report", None)
                and self._last_skin_report.diagnostics,
            },
            "psychophysics": {
                "perceptible": getattr(self, "_last_psychophysics_report", None)
                and self._last_psychophysics_report.perceptible_count,
                "suppression": getattr(self, "_last_psychophysics_report", None)
                and self._last_psychophysics_report.mixture_suppression_level,
                "anosmia_risk": getattr(self, "_last_psychophysics_report", None)
                and self._last_psychophysics_report.anosmia_risk_materials,
                "diagnostics": getattr(self, "_last_psychophysics_report", None)
                and self._last_psychophysics_report.diagnostics,
            },
            "trigeminal": {
                "dominant": getattr(self, "_last_trigeminal_report", None)
                and self._last_trigeminal_report.dominant_effect,
                "diagnostics": getattr(self, "_last_trigeminal_report", None)
                and self._last_trigeminal_report.diagnostics,
            },
            "dose_response": {
                "overdosed": getattr(self, "_last_dose_report", None)
                and self._last_dose_report.overdosed,
                "character_map": getattr(self, "_last_dose_report", None)
                and self._last_dose_report.character_map,
                "diagnostics": getattr(self, "_last_dose_report", None)
                and self._last_dose_report.diagnostics,
            },
            "diffusion": {
                "sillage_class": getattr(self, "_last_diffusion_report", None)
                and self._last_diffusion_report.sillage_class,
                "field_pct": getattr(self, "_last_diffusion_report", None)
                and {
                    "far": self._last_diffusion_report.far_field_pct,
                    "mid": self._last_diffusion_report.mid_field_pct,
                    "near": self._last_diffusion_report.near_field_pct,
                },
                "diagnostics": getattr(self, "_last_diffusion_report", None)
                and self._last_diffusion_report.diagnostics,
            },
        }
        if include_legacy_hedonic:
            science_diagnostics["hedonic"] = {
                "valence": getattr(self, "_last_hedonic_report", None)
                and self._last_hedonic_report.weighted_valence,
                "pleasantness": getattr(self, "_last_hedonic_report", None)
                and self._last_hedonic_report.pleasantness_class,
                "diagnostics": getattr(self, "_last_hedonic_report", None)
                and self._last_hedonic_report.diagnostics,
            }
        scores["_science"] = science_diagnostics
        if not include_legacy_hedonic:
            scores["_hedonic_evidence"] = {
                "state": "NOT_TESTED",
                "basis": (
                    "No exact-scope blinded LIKING receipt supplied to FormulaScorer."
                ),
                "legacy_heuristic_available_for_replay": True,
            }

        scores["_decision_authority"] = {
            "state": (
                "LEGACY_REPLAY_ONLY"
                if include_legacy_hedonic
                else "DIAGNOSTIC_ONLY"
            ),
            "ranking_authority": False,
            "formula_mutation_authority": False,
            "sensory_claim_authority": False,
            "basis": (
                "Composition-derived heuristic axes cannot establish target fidelity, "
                "depth, richness, liking, or beauty."
            ),
        }

        # Primary total uses geometric mean
        scores["total"] = scores["geometric_total"]
        if unknown:
            scores["_unknown_materials"] = unknown
            scores.setdefault("_diagnostics", []).append(
                "BLOCKED_UNKNOWN_MATERIALS: "
                + ", ".join(unknown)
                + "; scorer did not assign generic fallback profiles"
            )
            scores["arithmetic_total"] = min(float(scores.get("arithmetic_total", 0.0)), 5.0)
            scores["geometric_total"] = min(float(scores.get("geometric_total", 0.0)), 5.0)
            scores["total"] = scores["geometric_total"]

        return scores
