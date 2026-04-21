"""Niche Texture Collection — 10 Perfumes Built on Theory + Texture

Budget-conscious niche formulas using affordable synthetics as workhorses.
Every composition emphasises a specific *texture* quality (silky, powdery,
velvety, dry, grainy, crisp, smooth, warm, translucent, plush) while
respecting all 5 theory frameworks:

  - Carles method:  ~20% top / 35-40% heart / 40-50% base
  - Roudnitska:     6 roles (eclat, transparence, noblesse, peau, chaleur, profondeur)
  - Jellinek:       span ≥ 2 quadrants
  - SAR / Arctander: material class coverage
  - Compositional:  note-family diversity

Engine: theory-first (balance ×1.5, theory ×1.5, synergy ×0.3 bonus only)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from engine.optimizer.models import (
    FormulaVector, ObjectiveWeights,
    get_materials_db, get_theory_rules,
    _lookup_material, classify_note,
)
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer
from accord_pipeline import theory_provenance


# ═══════════════════════════════════════════════════════════════════════════
# 10 NICHE TEXTURE PERFUME DESIGNS
# ═══════════════════════════════════════════════════════════════════════════

NICHE_FORMULAS = [

    # ─────────────────────────────────────────────────────────────────────
    # 1. VELVET SMOKE — Smoky Leather Oriental
    #    Texture: velvety, warm, slightly grainy
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Velvet Smoke",
        "concept": "A velvety smoky leather built on affordable workhorse "
                   "materials. Birch-tar DNA meets warm Styrax resin, "
                   "wrapped in a coumarin-vanilla blanket. The texture "
                   "is dense and grain-like, smoothed by Cashmeran and "
                   "Iso E Super into something wearable and addictive.",
        "style": "Tuscan Leather / Ombré Leather territory",
        "pyramid": {
            "top": "Black Pepper FTEC, Bergamot FCF, Pink Pepper Base, "
                   "Cardamom FTEC",
            "heart": "Styrax FTEC, Guaiacol, IBQ, Cashmeran, "
                     "Benzyl Salicylate, Hedione, Labdanum",
            "base": "Iso E Super, Ambrox Super, Vanillin, Vertofix, "
                    "Galaxolide, Ethylene Brassylate, Coumarin",
        },
        "ingredients": {
            # TOP 15%
            "Black Pepper FTEC": 3.0,
            "Bergamot FCF": 5.0,
            "Pink Pepper Base": 3.0,
            "Cardamom FTEC (10%)": 4.0,
            # HEART 35%
            "Styrax FTEC": 6.0,
            "Guaiacol": 2.0,
            "Isobutyl Quinoline (10%)": 1.0,
            "Cashmeran (20%)": 8.0,
            "Benzyl Salicylate": 6.0,
            "Hedione": 6.0,
            "Labdanum": 6.0,
            # BASE 50%
            "Iso E Super": 12.0,
            "Ambrox Super (30%)": 6.0,
            "Vanillin (10%)": 5.0,
            "Vertofix": 8.0,
            "Galaxolide (80%)": 8.0,
            "Ethylene Brassylate": 5.0,
            "Coumarin (20%)": 6.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (pepper/bergamot), Transparence (hedione), "
                          "Noblesse (styrax/guaiacol character), Peau (iso e super/"
                          "cashmeran), Chaleur (labdanum/vanillin/coumarin), "
                          "Profondeur (vertofix/ethylene brassylate)",
            "carles": "Top 15% / Heart 35% / Base 50% — base-heavy for "
                      "orientals per Carles method",
            "jellinek": "Warm-Narcotic (leather/amber) + Fresh-Stimulating "
                        "(pepper/bergamot) = 2 quadrants",
            "twist": "IBQ at 1% — the merest whisper of leather quinoline "
                     "gives authenticity without animalic overload",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 2. SILK MUSK — Sheer Skin Scent
    #    Texture: silky, transparent, clean
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Silk Musk",
        "concept": "Pure silky transparency. Six different musks layer "
                   "to create a skin-scent that reads as 'you but better.' "
                   "Hedione at 15% gives radical diffusion; minimal top "
                   "notes let the musk cloud happen immediately. Ultra-"
                   "affordable — virtually all cheap synthetics.",
        "style": "Juliette Has a Gun Not a Perfume / Glossier You",
        "pyramid": {
            "top": "Linalool, Bergamot FCF, Aldehyde C11, Dihydromyrcenol",
            "heart": "Hedione, Hydroxycitronellal, PEA, Benzyl Salicylate, "
                     "Ambrox Super",
            "base": "Galaxolide, Romandolide, Habanolide, Ethylene Brassylate, "
                    "Iso E Super, Cashmeran",
        },
        "ingredients": {
            # TOP 12%
            "Linalool": 4.0,
            "Bergamot FCF": 3.0,
            "Aldehyde C11 (1%)": 2.0,
            "Dihydromyrcenol": 3.0,
            # HEART 38%
            "Hedione": 15.0,
            "Hydroxycitronellal": 5.0,
            "Phenethyl Alcohol (PEA)": 4.0,
            "Benzyl Salicylate": 8.0,
            "Ambrox Super (30%)": 6.0,
            # BASE 50%
            "Galaxolide (80%)": 15.0,
            "Romandolide": 8.0,
            "Habanolide": 6.0,
            "Ethylene Brassylate": 8.0,
            "Iso E Super": 8.0,
            "Cashmeran (20%)": 5.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot/dihydromyrcenol), Transparence "
                          "(hedione 15% — massive diffusion), Noblesse "
                          "(hydroxycitronellal lily), Peau (ambrox/iso e super/"
                          "cashmeran — the skin envelope), Chaleur (benzyl "
                          "salicylate warmth), Profondeur (ethylene brassylate/"
                          "habanolide fixation)",
            "carles": "Top 12% / Heart 38% / Base 50% — radically base-"
                      "heavy for the skin-scent illusion",
            "jellinek": "Cool-Narcotic (musks/clean) + Warm-Narcotic "
                        "(ambrox/cashmeran) = soft narcotic envelope",
            "twist": "Hedione at 15% — an abnormally high dose creates "
                     "the hyper-diffusive aura that makes skin scents work",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 3. POWDER BLUE — Iris-Marine Powdery
    #    Texture: powdery, cool, airy
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Powder Blue",
        "concept": "A cool powder-blue iris that drifts between ozonic "
                   "marine air and violet powder. Affordable ionones do "
                   "the iris heavy-lifting while Floralozone and Calone "
                   "add an oceanic transparency. The texture is like "
                   "talcum on damp skin — powdery yet fresh.",
        "style": "Prada Luna Rossa Ocean / Issey Miyake territory",
        "pyramid": {
            "top": "Cedrat FCF, Calone, Dihydromyrcenol, Methyl Pamplemousse, "
                   "Floralozone",
            "heart": "Alpha Ionone, AIMI, Methyl Ionone, Beta Ionone, Hedione, "
                     "Cyclamen Aldehyde, Benzyl Salicylate",
            "base": "Iso E Super, Cashmeran, Galaxolide, Ambrox Super, "
                    "Vertofix, Ethylene Brassylate, Coumarin",
        },
        "ingredients": {
            # TOP 18%
            "Cedrat FCF oil Sicilian": 4.0,
            "Calone (1%)": 2.0,
            "Dihydromyrcenol": 4.0,
            "Methyl Pamplemousse (10% in TEC)": 3.0,
            "Floralozone (10%)": 5.0,
            # HEART 40%
            "Alpha Ionone": 6.0,
            "Alpha-Isomethyl Ionone (AIMI)": 8.0,
            "Methyl Ionone": 3.0,
            "Beta Ionone": 2.0,
            "Hedione": 10.0,
            "Cyclamen Aldehyde": 3.0,
            "Benzyl Salicylate": 8.0,
            # BASE 42%
            "Iso E Super": 10.0,
            "Cashmeran (20%)": 6.0,
            "Galaxolide (80%)": 8.0,
            "Ambrox Super (30%)": 4.0,
            "Vertofix": 6.0,
            "Ethylene Brassylate": 4.0,
            "Coumarin (20%)": 4.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (cedrat/dihydromyrcenol), Transparence "
                          "(hedione/floralozone/calone — the blue airiness), "
                          "Noblesse (methyl ionone/beta ionone/alpha ionone — pure iris nobility), "
                          "Peau (iso e super/cashmeran/ambrox), Chaleur "
                          "(coumarin/benzyl salicylate), Profondeur "
                          "(vertofix/ethylene brassylate)",
            "carles": "Top 18% / Heart 40% / Base 42% — balanced; iris "
                      "needs generous heart to read properly",
            "jellinek": "Cool-Narcotic (iris/marine/powder) + Fresh-"
                        "Stimulating (calone/citrus) + Warm-Narcotic "
                        "(ambrox/musk) = 3 quadrants",
            "twist": "Calone at trace dose — normally an aquatic cliché, "
                     "but at 1% it becomes an ethereal coolness that lifts "
                     "the powdery iris into something unexpected",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 4. DRY EARTH — Earthy Woody
    #    Texture: dry, mineral, textured
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Dry Earth",
        "concept": "Bone-dry earth after months without rain. Vetiver "
                   "and patchouli provide the cracked-clay mineral core "
                   "while Clearwood adds modern transparent woodiness. "
                   "The texture is deliberately arid — no sweetness, no "
                   "flowers, no softness. The only concession is "
                   "Norlimbanol at 1% for subterranean depth.",
        "style": "Terre d'Hermès / Encre Noire territory",
        "pyramid": {
            "top": "Black Pepper FTEC, Bergamot FCF, Galbanum Resinoid, "
                   "cis-3-Hexenol, Pink Pepper Base",
            "heart": "Patchouli EO, Vetiver EO, Clearwood, Hedione, "
                     "Cedarwood EO, Javanol",
            "base": "Iso E Super, Vertofix, Norlimbanol, Ambrox Super, "
                    "Galaxolide, Labdanum, Vetival, Cashmeran",
        },
        "ingredients": {
            # TOP 15%
            "Black Pepper FTEC": 4.0,
            "Bergamot FCF": 4.0,
            "Galbanum Resinoid (10%)": 3.0,
            "cis-3-Hexenol": 2.0,
            "Pink Pepper Base": 2.0,
            # HEART 40%
            "Patchouli EO": 8.0,
            "Vetiver EO": 6.0,
            "Clearwood": 8.0,
            "Hedione": 6.0,
            "Cedarwood EO": 6.0,
            "Javanol": 6.0,
            # BASE 45%
            "Iso E Super": 10.0,
            "Vertofix": 8.0,
            "Norlimbanol Dextro (1%)": 2.0,
            "Ambrox Super (30%)": 4.0,
            "Galaxolide (80%)": 8.0,
            "Labdanum": 5.0,
            "Vetival": 4.0,
            "Cashmeran (20%)": 4.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (pepper/bergamot), Transparence (hedione/"
                          "galbanum), Noblesse (vetiver EO — the star), "
                          "Peau (iso e super/cashmeran/javanol), Chaleur "
                          "(labdanum/patchouli), Profondeur (norlimbanol/"
                          "vertofix/vetival — deep fixation)",
            "carles": "Top 15% / Heart 40% / Base 45% — woody-heavy base "
                      "as Carles prescribes for chypre-woody families",
            "jellinek": "Cool-Stimulating (galbanum/vetiver/green) + "
                        "Warm-Narcotic (labdanum/amber) = austere duality",
            "twist": "Norlimbanol at 1% — at trace dose this 'dark woody' "
                     "molecule creates the subterranean rumble that gives "
                     "the dry earth its sense of depth and weight",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 5. AMBER GLASS — Transparent Amber
    #    Texture: smooth, warm, glowing
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Amber Glass",
        "concept": "An amber that glows like light through cathedral glass. "
                   "Five different amber molecules stack to create depth "
                   "without muddiness. Frankincense and benzoin add "
                   "liturgical gravitas while Hedione keeps everything "
                   "transparent. The texture is molten — smooth, warm, "
                   "and radiant.",
        "style": "Tom Ford Amber Absolute / Ambre Nuit territory",
        "pyramid": {
            "top": "Bergamot FCF, Linalool, Cardamom FTEC, Citral",
            "heart": "Hedione, Benzyl Salicylate, Aurantiol, Labdanum, "
                     "Styrax FTEC, Olibanum Resinoid, Benzoin Resinoid",
            "base": "Ambrox Super, Amber Xtreme, Ambermax, Iso E Super, "
                    "Cashmeran, Vanillin, Galaxolide, Ethylene Brassylate, "
                    "Coumarin",
        },
        "ingredients": {
            # TOP 12%
            "Bergamot FCF": 4.0,
            "Linalool": 3.0,
            "Cardamom FTEC (10%)": 3.0,
            "Citral": 2.0,
            # HEART 35%
            "Hedione": 8.0,
            "Benzyl Salicylate": 6.0,
            "Aurantiol": 4.0,
            "Labdanum": 6.0,
            "Styrax FTEC": 4.0,
            "Olibanum Resinoid": 4.0,
            "Benzoin Resinoid (50% in DPG)": 3.0,
            # BASE 53%
            "Ambrox Super (30%)": 8.0,
            "Amber Xtreme": 6.0,
            "Ambermax (10%)": 4.0,
            "Iso E Super": 10.0,
            "Cashmeran (20%)": 5.0,
            "Vanillin (10%)": 5.0,
            "Galaxolide (80%)": 8.0,
            "Ethylene Brassylate": 4.0,
            "Coumarin (20%)": 3.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot/citral), Transparence (hedione/"
                          "aurantiol), Noblesse (olibanum — sacred resin), "
                          "Peau (ambrox/iso e super/cashmeran — the skin-"
                          "amber core), Chaleur (labdanum/benzoin/vanillin/"
                          "coumarin — four warm balsamic layers), Profondeur "
                          "(amber xtreme/ethylene brassylate)",
            "carles": "Top 12% / Heart 35% / Base 53% — radically base-"
                      "heavy as ambers demand",
            "jellinek": "Warm-Narcotic (amber/resin/balsam — dominant) + "
                        "Fresh-Stimulating (citrus/hedione — lift) = "
                        "2 quadrants with warm dominance",
            "twist": "Five stacked amber molecules (Ambrox, Amber Xtreme, "
                     "Ambermax, Iso E Super, Cashmeran) — each contributing "
                     "a different facet of ambergris-amber character",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 6. GREEN PEPPER — Spicy Green Aromatic
    #    Texture: crisp, sharp, herbaceous
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Green Pepper",
        "concept": "A bracing aromatic fougère built on pepper and green "
                   "notes. Double pepper (black + pink) gives a crisp "
                   "bite that's tempered by lavender and galbanum. No "
                   "sweetness, no florals — just clean, sharp, angular "
                   "greenness over a woody base. Very inexpensive to make.",
        "style": "Grey Vetiver / Terre d'Hermès territory",
        "pyramid": {
            "top": "Black Pepper FTEC, Pink Pepper Base, Grapefruit FCF, "
                   "cis-3-Hexenol, Galbanum Resinoid, Dihydromyrcenol",
            "heart": "Hedione, Lavender EO, Geraniol, Patchouli EO, "
                     "Cedarwood EO, Clearwood, Vetiver EO, Eugenol",
            "base": "Iso E Super, Vertofix, Ambrox Super, Galaxolide, "
                    "Romandolide, Cashmeran, Coumarin, Benzyl Salicylate",
        },
        "ingredients": {
            # TOP 22%
            "Black Pepper FTEC": 5.0,
            "Pink Pepper Base": 4.0,
            "Grapefruit FCF": 4.0,
            "cis-3-Hexenol": 3.0,
            "Galbanum Resinoid (10%)": 3.0,
            "Dihydromyrcenol": 3.0,
            # HEART 38%
            "Hedione": 8.0,
            "Lavender EO": 5.0,
            "Geraniol": 4.0,
            "Patchouli EO": 5.0,
            "Cedarwood EO": 5.0,
            "Clearwood": 5.0,
            "Vetiver EO": 3.0,
            "Eugenol": 3.0,
            # BASE 40%
            "Iso E Super": 10.0,
            "Vertofix": 6.0,
            "Ambrox Super (30%)": 4.0,
            "Galaxolide (80%)": 6.0,
            "Romandolide": 4.0,
            "Cashmeran (20%)": 4.0,
            "Coumarin (20%)": 3.0,
            "Benzyl Salicylate": 3.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (pepper/grapefruit/dihydromyrcenol), "
                          "Transparence (hedione/galbanum — green airiness), "
                          "Noblesse (lavender EO — classic fougère nobility), "
                          "Peau (iso e super/cashmeran/ambrox), Chaleur "
                          "(patchouli/coumarin — fougère warmth), Profondeur "
                          "(vertofix/clearwood — deep woody fixation)",
            "carles": "Top 22% / Heart 38% / Base 40% — generous top for "
                      "the aromatic impact that fougères need",
            "jellinek": "Cool-Stimulating (green/galbanum/pepper) + "
                        "Warm-Stimulating (spice/lavender) = energetic "
                        "masculine duality",
            "twist": "Double pepper (black + pink) at 9% combined — "
                     "creates a three-dimensional peppery bite that's "
                     "more complex than either alone",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 7. DARK FRUIT — Fruity Dark Woods
    #    Texture: plush, dense, velvety
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Dark Fruit",
        "concept": "Blackcurrant and blood orange meet dark patchouli and "
                   "labdanum in a plush, gourmand-adjacent composition. "
                   "The texture is like velvet curtains in a warm room — "
                   "dense but not heavy. Rose Oxide at trace dose bridges "
                   "the fruit-flower gap. Affordable fruit FTECs and "
                   "cheap synthetics keep the cost down.",
        "style": "By Kilian Angels' Share / Black Phantom territory",
        "pyramid": {
            "top": "Blackcurrant FTEC, Blood Orange, Dewberry FTEC, "
                   "Gamma Decalactone, Raspberry Ketone",
            "heart": "PEA, Hedione, Benzyl Salicylate, Rose Oxide, "
                     "Patchouli EO, Labdanum, Styrax FTEC, Cashmeran",
            "base": "Iso E Super, Vanillin, Benzoin Resinoid, Ambrox Super, "
                    "Galaxolide, Ethylene Brassylate, Vertofix, Coumarin",
        },
        "ingredients": {
            # TOP 18%
            "Blackcurrant FTEC": 5.0,
            "Blood Orange oil Sicilian": 4.0,
            "Dewberry FTEC": 3.0,
            "Gamma Decalactone": 3.0,
            "Raspberry Ketone": 3.0,
            # HEART 35%
            "Phenethyl Alcohol (PEA)": 4.0,
            "Hedione": 6.0,
            "Benzyl Salicylate": 5.0,
            "Rose Oxide (10%)": 2.0,
            "Patchouli EO": 5.0,
            "Labdanum": 5.0,
            "Styrax FTEC": 3.0,
            "Cashmeran (20%)": 5.0,
            # BASE 47%
            "Iso E Super": 10.0,
            "Vanillin (10%)": 5.0,
            "Benzoin Resinoid (50% in DPG)": 4.0,
            "Ambrox Super (30%)": 4.0,
            "Galaxolide (80%)": 8.0,
            "Ethylene Brassylate": 4.0,
            "Vertofix": 6.0,
            "Coumarin (20%)": 6.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (blood orange/blackcurrant — fruit burst), "
                          "Transparence (hedione/rose oxide — diffusion), "
                          "Noblesse (patchouli EO — the dark star), Peau "
                          "(iso e super/cashmeran/ambrox — skin warmth), "
                          "Chaleur (labdanum/vanillin/benzoin/coumarin — "
                          "gourmand warmth), Profondeur (vertofix/ethylene "
                          "brassylate — deep fixation)",
            "carles": "Top 18% / Heart 35% / Base 47% — classic oriental "
                      "distribution with base emphasis",
            "jellinek": "Warm-Narcotic (gourmand/balsam/musk) + Fresh-"
                        "Stimulating (citrus fruit/berry) = sweet-dark "
                        "contrast across 2 quadrants",
            "twist": "Blackcurrant FTEC + Blood Orange — a citrus-berry "
                     "combination that tricks the nose into reading 'ripe "
                     "dark fruit' rather than either note alone",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 8. WARM COTTON — Clean Aldehydic Musk
    #    Texture: warm, soft, fabric-like
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Warm Cotton",
        "concept": "Fresh laundry in morning sunlight. Three waxy aldehydes "
                   "give the characteristic 'clean fabric' sparkle, while "
                   "a generous Hedione dose creates the billowing airiness "
                   "of sheets drying in wind. The musk base (four types) "
                   "gives the warm-skin finish. Extremely inexpensive — "
                   "almost entirely cheap synthetics.",
        "style": "Clean Reserve Skin / Maison Margiela Lazy Sunday territory",
        "pyramid": {
            "top": "Aldehyde C10, C11, C12 MNA, Linalool, Bergamot FCF, "
                   "Dihydromyrcenol",
            "heart": "Hedione, Hydroxycitronellal, Benzyl Salicylate, "
                     "Florol, Lilyreal, Helional",
            "base": "Galaxolide, Romandolide, Habanolide, Iso E Super, "
                    "Cashmeran, Ethylene Brassylate, Coumarin, Vanillin",
        },
        "ingredients": {
            # TOP 18%
            "Aldehyde C10 (1%)": 2.0,
            "Aldehyde C11 (1%)": 2.0,
            "Aldehyde C12 MNA (1%)": 2.0,
            "Linalool": 4.0,
            "Bergamot FCF": 4.0,
            "Dihydromyrcenol": 4.0,
            # HEART 35%
            "Hedione": 10.0,
            "Hydroxycitronellal": 5.0,
            "Benzyl Salicylate": 8.0,
            "Florol": 4.0,
            "Lilyreal ND": 4.0,
            "Helional": 4.0,
            # BASE 47%
            "Galaxolide (80%)": 12.0,
            "Romandolide": 6.0,
            "Habanolide": 5.0,
            "Iso E Super": 8.0,
            "Cashmeran (20%)": 4.0,
            "Ethylene Brassylate": 5.0,
            "Coumarin (20%)": 4.0,
            "Vanillin (10%)": 3.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (aldehydes/bergamot/dihydromyrcenol — waxy "
                          "sparkle), Transparence (hedione 10% — billowing "
                          "diffusion), Noblesse (hydroxycitronellal/florol — "
                          "muguet purity), Peau (iso e super/cashmeran — "
                          "skin warmth), Chaleur (coumarin/vanillin — gentle "
                          "warmth), Profondeur (ethylene brassylate/habanolide "
                          "— powdery musk depth)",
            "carles": "Top 18% / Heart 35% / Base 47% — aldehydic needs "
                      "generous top but strong musk base for the clean finish",
            "jellinek": "Cool-Narcotic (clean/musk/aldehydic) + Fresh-"
                        "Stimulating (citrus/aldehydes) = pristine freshness",
            "twist": "Triple aldehyde stack (C10, C11, C12 MNA) — each "
                     "at trace dose for a shimmering waxy envelope without "
                     "the soapy heaviness of higher concentrations",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 9. INCENSE RAIN — Incense Aquatic
    #    Texture: smoky-wet, ethereal, translucent
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Incense Rain",
        "concept": "Frankincense smoke drifting through rain. An unlikely "
                   "pairing of sacred resins with aquatic transparency. "
                   "Olibanum and myrrh provide the church-incense core "
                   "while Floralozone and Calone create the rain-on-"
                   "pavement petrichor. The texture is gauze-like — "
                   "translucent smoke you can almost see through.",
        "style": "CdG Avignon / Byredo Mojave Ghost territory",
        "pyramid": {
            "top": "Calone, Dihydromyrcenol, Bergamot FCF, Floralozone, "
                   "Methyl Pamplemousse, Linalool",
            "heart": "Olibanum Resinoid, Myrrh EO, Hedione, Lavender EO, "
                     "Benzyl Salicylate, Clearwood, Cedarwood EO",
            "base": "Iso E Super, Ambrox Super, Galaxolide, Vertofix, "
                    "Labdanum, Cashmeran, Ethylene Brassylate, Coumarin",
        },
        "ingredients": {
            # TOP 18%
            "Calone (1%)": 2.0,
            "Dihydromyrcenol": 4.0,
            "Bergamot FCF": 4.0,
            "Floralozone (10%)": 3.0,
            "Methyl Pamplemousse (10% in TEC)": 2.0,
            "Linalool": 3.0,
            # HEART 37%
            "Olibanum Resinoid": 6.0,
            "Myrrh EO": 4.0,
            "Hedione": 8.0,
            "Lavender EO": 3.0,
            "Benzyl Salicylate": 6.0,
            "Clearwood": 5.0,
            "Cedarwood EO": 5.0,
            # BASE 45%
            "Iso E Super": 10.0,
            "Ambrox Super (30%)": 5.0,
            "Galaxolide (80%)": 8.0,
            "Vertofix": 6.0,
            "Labdanum": 4.0,
            "Cashmeran (20%)": 4.0,
            "Ethylene Brassylate": 4.0,
            "Coumarin (20%)": 4.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot/dihydromyrcenol), Transparence "
                          "(hedione/floralozone/calone — the aquatic veil), "
                          "Noblesse (olibanum/myrrh — sacred resin character), "
                          "Peau (iso e super/cashmeran/ambrox — skin warmth), "
                          "Chaleur (labdanum/coumarin — balsamic), Profondeur "
                          "(vertofix/ethylene brassylate — deep fixation)",
            "carles": "Top 18% / Heart 37% / Base 45% — balanced distribution "
                      "that gives both the aquatic top and the incense heart "
                      "room to breathe",
            "jellinek": "Cool-Stimulating (aquatic/marine/fresh) + Warm-"
                        "Narcotic (incense/resin/labdanum) = dramatic "
                        "contrast across 2 quadrants",
            "twist": "Frankincense + Calone — the collision of sacred smoke "
                     "and synthetic ocean creates a wholly new category: "
                     "'wet incense' — petrichor in a cathedral",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # 10. ROSE CUIR — Floral Leather
    #    Texture: velvety-smooth, warm, leathery
    # ─────────────────────────────────────────────────────────────────────
    {
        "name": "Rose Cuir",
        "concept": "A rose encased in soft leather. PEA and Geraniol build "
                   "the rose facet while IBQ and Birch Tar create an "
                   "authentic leather impression. Styrax and Isoeugenol "
                   "bridge the floral-leather gap with smoky-spicy warmth. "
                   "The texture is like soft calfskin — supple, warm, "
                   "with a velvety nap.",
        "style": "Rose 31 / Ombré Nomade territory",
        "pyramid": {
            "top": "Bergamot FCF, Geraniol, Citronellol, Cardamom FTEC",
            "heart": "PEA, Rose Oxide, Hedione, IBQ, Birch Tar, Styrax FTEC, "
                     "Isoeugenol, Patchouli EO, Benzyl Salicylate, Labdanum",
            "base": "Iso E Super, Cashmeran, Ambrox Super, Galaxolide, "
                    "Vertofix, Vanillin, Coumarin, Ethylene Brassylate",
        },
        "ingredients": {
            # TOP 15%
            "Bergamot FCF": 4.0,
            "Geraniol": 4.0,
            "Citronellol": 4.0,
            "Cardamom FTEC (10%)": 3.0,
            # HEART 40%
            "Phenethyl Alcohol (PEA)": 6.0,
            "Rose Oxide (10%)": 2.0,
            "Hedione": 8.0,
            "Isobutyl Quinoline (10%)": 2.0,
            "Birch Tar Rectified": 2.0,
            "Styrax FTEC": 4.0,
            "Isoeugenol": 3.0,
            "Patchouli EO": 5.0,
            "Benzyl Salicylate": 4.0,
            "Labdanum": 4.0,
            # BASE 45%
            "Iso E Super": 10.0,
            "Cashmeran (20%)": 5.0,
            "Ambrox Super (30%)": 5.0,
            "Galaxolide (80%)": 8.0,
            "Vertofix": 5.0,
            "Vanillin (10%)": 3.0,
            "Coumarin (20%)": 4.0,
            "Ethylene Brassylate": 5.0,
        },
        "theory_notes": {
            "roudnitska": "Eclat (bergamot/geraniol/citronellol — rosy "
                          "citrus lift), Transparence (hedione — jasminic "
                          "diffusion), Noblesse (PEA/rose oxide — rose is "
                          "the queen), Peau (iso e super/cashmeran/ambrox — "
                          "skin embrace), Chaleur (labdanum/styrax/vanillin/"
                          "coumarin — smoky sweetness), Profondeur (vertofix/"
                          "ethylene brassylate/birch tar — dark anchoring)",
            "carles": "Top 15% / Heart 40% / Base 45% — heart-heavy to "
                      "give the floral-leather bridge maximum presence",
            "jellinek": "Cool-Narcotic (rose/floral) + Warm-Stimulating "
                        "(leather/spice/birch) + Warm-Narcotic (musk/"
                        "amber) = 3 quadrants",
            "twist": "IBQ + Birch Tar at trace amounts — two aggressive "
                     "leather molecules tamed to whisper rather than shout, "
                     "creating authentic suede rather than motorcycle jacket",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# BUILD + SCORE + SAVE
# ═══════════════════════════════════════════════════════════════════════════

def build_formula_vector(design: dict) -> FormulaVector:
    """Convert a design dict into a FormulaVector for the engine."""
    return FormulaVector(ingredients=dict(design["ingredients"]))


def main():
    print("=" * 70)
    print("NICHE TEXTURE COLLECTION — 10 Theory-First Perfumes")
    print("=" * 70)

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    conf_scorer = ConfidenceScorer()

    results = []

    for i, design in enumerate(NICHE_FORMULAS, 1):
        print(f"\n{'─' * 70}")
        print(f"  {i}. {design['name']}")
        print(f"     {design['concept'][:80]}...")
        print(f"{'─' * 70}")

        fv = build_formula_vector(design)
        total = fv.total_pct
        dist = fv.note_distribution()
        print(f"\n  Total: {total:.1f}%  |  Top {dist['top']:.0f}%  "
              f"Heart {dist['heart']:.0f}%  Base {dist['base']:.0f}%")

        # Score
        scores = scorer.score(fv)
        print(f"\n  ▸ Initial Score: {scores['total']:.1f}")
        print(f"    Balance={scores['balance']:.1f}  Theory={scores['theory']:.1f}  "
              f"Longevity={scores['longevity']:.1f}  Sillage={scores['sillage']:.1f}  "
              f"Synergy={scores['synergy']:.1f}")

        # Optimize
        result = optimizer.optimize(fv)
        opt_scores = result.scores
        print(f"\n  ▸ Optimized Score: {result.total_score:.1f} "
              f"({result.total_score - scores['total']:+.1f})")
        print(f"    Balance={opt_scores['balance']:.1f}  "
              f"Theory={opt_scores['theory']:.1f}  "
              f"Longevity={opt_scores['longevity']:.1f}  "
              f"Sillage={opt_scores['sillage']:.1f}  "
              f"Synergy={opt_scores['synergy']:.1f}")

        if result.suggestions:
            print(f"  Suggestions:")
            for sug in result.suggestions[:3]:
                print(f"    • {sug}")

        # Confidence
        conf = conf_scorer.score(fv.ingredients)
        print(f"\n  ▸ Confidence: {conf['confidence_grade']} "
              f"(data={conf['data_confidence']:.0f}  "
              f"pairing={conf['pairing_confidence']:.0f}  "
              f"overall={conf['overall_confidence']:.0f})")

        # Theory provenance
        prov = theory_provenance(fv)
        roud_roles = list(prov["roudnitska_roles"].keys())
        missing = prov["roudnitska_missing"]
        jell_quads = list(prov["jellinek_quadrants"].keys())
        print(f"\n  ▸ Theory Provenance:")
        print(f"    Roudnitska roles: "
              f"{', '.join(roud_roles) if roud_roles else 'none'}")
        if missing:
            print(f"    Missing roles: {', '.join(missing)}")
        print(f"    Jellinek quadrants: "
              f"{', '.join(jell_quads) if jell_quads else 'none'}")
        print(f"    SAR classes: {prov['sar_classes']}")

        results.append({
            "name": design["name"],
            "concept": design["concept"],
            "style": design["style"],
            "pyramid": design["pyramid"],
            "ingredients": fv.ingredients,
            "total_pct": total,
            "note_distribution": dist,
            "initial_scores": scores,
            "optimized_scores": opt_scores,
            "optimized_total": result.total_score,
            "suggestions": result.suggestions,
            "confidence": conf,
            "theory_provenance": prov,
            "theory_notes": design["theory_notes"],
        })

    # ── Save JSON ──
    json_path = Path(__file__).parent / "niche_texture_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n→ Saved: {json_path.name}")

    # ── Save Markdown ──
    md_path = Path(__file__).parent / "niche_texture_collection.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Niche Texture Collection\n\n")
        f.write("10 theory-driven niche perfumes emphasising **texture** — "
                "built on affordable synthetics,\\\n")
        f.write("scored by 5 classical frameworks.\\\n")
        f.write("**Engine**: Theory-first (balance ×1.5, theory ×1.5, "
                "synergy ×0.3 bonus only)\n\n")
        f.write("---\n\n")

        for i, r in enumerate(results, 1):
            s = r["optimized_scores"]
            d = r["note_distribution"]

            f.write(f"## {i}. {r['name']}\n\n")
            f.write(f"**Style**: {r['style']}\\\n")
            f.write(f"**Concept**: {r['concept']}\n\n")

            f.write(f"**Score**: {r['initial_scores']['total']:.1f} → "
                    f"**{r['optimized_total']:.1f}** (optimized)\n\n")

            # Score breakdown
            f.write("| Axis | Score |\n|------|-------|\n")
            for axis in ["balance", "theory", "longevity", "sillage",
                         "synergy", "cost"]:
                f.write(f"| {axis.title()} | {s.get(axis, 0):.1f} |\n")

            conf = r["confidence"]
            f.write(f"\n**Confidence**: "
                    f"{conf.get('confidence_grade', 'N/A')} "
                    f"(overall={conf.get('overall_confidence', 0):.0f})\n\n")

            # Pyramid
            pyr = r["pyramid"]
            f.write("### Pyramid\n\n")
            f.write(f"- **Top** ({d['top']:.0f}%): {pyr['top']}\n")
            f.write(f"- **Heart** ({d['heart']:.0f}%): {pyr['heart']}\n")
            f.write(f"- **Base** ({d['base']:.0f}%): {pyr['base']}\n\n")

            # Formula table
            f.write("### Formula (% of concentrate)\n\n")
            f.write("| Material | % | Note |\n|----------|---|------|\n")
            for mat, pct in sorted(r["ingredients"].items(),
                                   key=lambda x: -x[1]):
                note = classify_note(mat)
                f.write(f"| {mat} | {pct:.1f} | {note} |\n")
            f.write(f"| **TOTAL** | **{r['total_pct']:.1f}** | |\n")

            # Theory provenance
            prov = r["theory_provenance"]
            tn = r["theory_notes"]
            f.write(f"\n### Theory\n\n")
            f.write(f"- **Roudnitska**: {tn['roudnitska']}\n")
            f.write(f"- **Carles**: {tn['carles']}\n")
            f.write(f"- **Jellinek**: {tn['jellinek']}\n")
            f.write(f"- **The Twist**: {tn['twist']}\n")

            if r.get("suggestions"):
                f.write(f"\n### Optimizer Suggestions\n\n")
                for sug in r["suggestions"]:
                    f.write(f"- {sug}\n")

            # Texture note
            f.write(f"\n### Texture & Usage\n\n")
            f.write(f"- **Concentration**: EDP 15-20% in ethanol\n")
            f.write(f"- **Maceration**: 2-4 weeks minimum\n")
            f.write(f"- **30mL EDP** at 18%: {30 * 0.18:.1f}g concentrate "
                    f"+ {30 * 0.82:.1f}g ethanol\n")

            f.write("\n---\n\n")

        # Summary table
        f.write("## Summary\n\n")
        f.write("| # | Name | Score | Confidence | Top/Heart/Base "
                "| Ingredients |\n")
        f.write("|---|------|-------|------------|----------------"
                "|-------------|\n")
        for i, r in enumerate(results, 1):
            d = r["note_distribution"]
            f.write(f"| {i} | {r['name']} | {r['optimized_total']:.1f} "
                    f"| {r['confidence'].get('confidence_grade', 'N/A')} "
                    f"| {d['top']:.0f}/{d['heart']:.0f}/{d['base']:.0f} "
                    f"| {len(r['ingredients'])} |\n")

    print(f"→ Saved: {md_path.name}")
    print(f"\n{'=' * 70}")
    print("COMPLETE — 10 Niche Texture Perfumes, Theory-First")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
