"""Perfume pyramid ratios and OAV targets by family and concentration.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Contains:
- Top/Heart/Base % ratios for every family × concentration bracket
- Per-family OAV targets at each time window
- Material role distribution targets
- Cross-family compatibility matrix
- Fixative loading guidelines
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.knowledge.perfume_taxonomy import ConcentrationBracket, PerfumeFamily


@dataclass(frozen=True, slots=True)
class PyramidRatio:
    """Top:Heart:Base ratio as % of concentrate."""

    top: float
    heart: float
    base: float
    bracket: ConcentrationBracket
    description: str = ""


PYRAMID_RATIOS: dict[str, dict[ConcentrationBracket, PyramidRatio]] = {
    # ── CITRUS ──
    "citrus": {
        ConcentrationBracket.EDC: PyramidRatio(
            50,
            35,
            15,
            ConcentrationBracket.EDC,
            "Bright hesperidic cologne, rapid evolution",
        ),
        ConcentrationBracket.EDT: PyramidRatio(
            40,
            35,
            25,
            ConcentrationBracket.EDT,
            "Citrus top extended by aromatic heart",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            30, 35, 35, ConcentrationBracket.EDP, "Citrus anchored by woody-floral body"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            20, 35, 45, ConcentrationBracket.EXTRAIT, "Deep citrus-woody, tenacious"
        ),
    },
    "citrus_classical": {
        ConcentrationBracket.EDC: PyramidRatio(
            50,
            35,
            15,
            ConcentrationBracket.EDC,
            "Classical eau de cologne: hesperidic top, neroli-petitgrain heart",
        ),
        ConcentrationBracket.EDT: PyramidRatio(
            42,
            35,
            23,
            ConcentrationBracket.EDT,
            "Citrus classical pushed into an EDT study concentration",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            30,
            38,
            32,
            ConcentrationBracket.EDP,
            "Modern-safe cologne study with extra heart and fixative support",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            20,
            38,
            42,
            ConcentrationBracket.EXTRAIT,
            "Dense citrus study, more educational than historical",
        ),
    },
    "citrus_aromatic": {
        ConcentrationBracket.EDC: PyramidRatio(
            45, 35, 20, ConcentrationBracket.EDC, "Bright citrus + herb sparkle"
        ),
        ConcentrationBracket.EDT: PyramidRatio(
            35,
            38,
            27,
            ConcentrationBracket.EDT,
            "Lavender/rosemary bridge citrus to wood",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            25, 38, 37, ConcentrationBracket.EDP, "Aromatic citrus with coumarin base"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            18, 35, 47, ConcentrationBracket.EXTRAIT, "Deep herbaceous-citrus tenacity"
        ),
    },
    "citrus_woody": {
        ConcentrationBracket.EDC: PyramidRatio(
            40, 30, 30, ConcentrationBracket.EDC, "Bright citrus over cedar"
        ),
        ConcentrationBracket.EDT: PyramidRatio(
            30, 30, 40, ConcentrationBracket.EDT, "Terre d'Hermès balance"
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20, 30, 50, ConcentrationBracket.EDP, "Wood-dominant citrus, vetiver rich"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15, 25, 60, ConcentrationBracket.EXTRAIT, "Deep woody with citrus lift"
        ),
    },
    "dior_homme_cologne": {
        ConcentrationBracket.EDC: PyramidRatio(
            42,
            38,
            20,
            ConcentrationBracket.EDC,
            "Citrus cologne with transparent white-floral heart",
        ),
        ConcentrationBracket.EDT: PyramidRatio(
            32,
            42,
            26,
            ConcentrationBracket.EDT,
            "Extended citrus over neroli-hedione body",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            22,
            48,
            30,
            ConcentrationBracket.EDP,
            "Thai flanker: heart-lifted citrus cologne with clean woody persistence",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            16,
            44,
            40,
            ConcentrationBracket.EXTRAIT,
            "Dense white-citrus cologne with polished musky base",
        ),
    },
    # ── FOUGERE ──
    "fougere": {
        ConcentrationBracket.EDT: PyramidRatio(
            30,
            40,
            30,
            ConcentrationBracket.EDT,
            "Classical fougère: lavender/coumarin/oakmoss",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            25,
            40,
            35,
            ConcentrationBracket.EDP,
            "Fougère: aromatic heart over mossy base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            20,
            35,
            45,
            ConcentrationBracket.EXTRAIT,
            "Deep fougère, coumarin-heavy base",
        ),
    },
    "aromatic_fougere": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            40,
            35,
            ConcentrationBracket.EDT,
            "Aromatic fougère: lavender+citrus over coumarin",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20, 40, 40, ConcentrationBracket.EDP, "Modern aromatic fougère, balanced"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15, 35, 50, ConcentrationBracket.EXTRAIT, "Rich aromatic base-heavy fougère"
        ),
    },
    "fougere_classical": {
        ConcentrationBracket.EDT: PyramidRatio(
            30,
            40,
            30,
            ConcentrationBracket.EDT,
            "Classical fougere: lavender-oakmoss-coumarin triangle",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            25,
            40,
            35,
            ConcentrationBracket.EDP,
            "Classical fougere EdP: more moss and fixative weight",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            18,
            35,
            47,
            ConcentrationBracket.EXTRAIT,
            "Deep heritage fougere: coumarin and moss emphasized",
        ),
    },
    "fougere_modern_mineral": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            42,
            33,
            ConcentrationBracket.EDT,
            "Mineral fougère: fresh opening over moss",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            42,
            40,
            ConcentrationBracket.EDP,
            "Mineral-aromatic, cold stone + lavender",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            38,
            50,
            ConcentrationBracket.EXTRAIT,
            "Deep mineral fougère, norlimbanol base",
        ),
    },
    "fougere_modern_tonka": {
        ConcentrationBracket.EDT: PyramidRatio(
            22,
            43,
            35,
            ConcentrationBracket.EDT,
            "Tonka mass: coumarin + vanilla opening",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            40,
            42,
            ConcentrationBracket.EDP,
            "Gourmand-fougère: tonka + apple over woods",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            14,
            36,
            50,
            ConcentrationBracket.EXTRAIT,
            "Rich tonka-fougère, vanillic base",
        ),
    },
    # ── FLORAL ──
    "floral": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            50,
            25,
            ConcentrationBracket.EDT,
            "Fresh floral: green-citrus top over heart",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            50,
            30,
            ConcentrationBracket.EDP,
            "Classical floral: heart-dominant with musk base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            45,
            40,
            ConcentrationBracket.EXTRAIT,
            "Rich floral: deep base anchors bouquet",
        ),
    },
    "floral_soliflore": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            60,
            25,
            ConcentrationBracket.EDT,
            "Soliflore: focus on middle, light top/base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            10,
            60,
            30,
            ConcentrationBracket.EDP,
            "Soliflore: flower dominates, minimal distraction",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            55,
            37,
            ConcentrationBracket.EXTRAIT,
            "Soliflore extrait: rich flower + fixative",
        ),
    },
    "floral_bouquet": {
        ConcentrationBracket.EDT: PyramidRatio(
            22,
            56,
            22,
            ConcentrationBracket.EDT,
            "Bouquet: multi-floral heart with restrained top and supporting base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            55,
            27,
            ConcentrationBracket.EDP,
            "Classical bouquet: heart dominant with soft musky-woody frame",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            50,
            38,
            ConcentrationBracket.EXTRAIT,
            "Rich bouquet extrait: dense floral heart with deeper foundation",
        ),
    },
    "floral_white": {
        ConcentrationBracket.EDT: PyramidRatio(
            20,
            52,
            28,
            ConcentrationBracket.EDT,
            "White floral: jasmine/gardenia forward",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            52,
            33,
            ConcentrationBracket.EDP,
            "White floral: tuberose richness, musk drydown",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12, 48, 40, ConcentrationBracket.EXTRAIT, "Narcotic white floral extrait"
        ),
    },
    "floral_muguet": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            55,
            20,
            ConcentrationBracket.EDT,
            "Muguet: airy top over a dewy lily-of-the-valley heart",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            57,
            25,
            ConcentrationBracket.EDP,
            "Muguet EdP study: still heart dominant, lightly fixed",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            52,
            36,
            ConcentrationBracket.EXTRAIT,
            "Dense muguet study with stronger supporting base",
        ),
    },
    "floral_carnation": {
        ConcentrationBracket.EDT: PyramidRatio(
            22,
            48,
            30,
            ConcentrationBracket.EDT,
            "Carnation: spiced floral heart over powdery-fixative base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            16,
            49,
            35,
            ConcentrationBracket.EDP,
            "Carnation EdP: richer clove-floral body and soft balsamic base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            45,
            43,
            ConcentrationBracket.EXTRAIT,
            "Dense carnation extrait with warmer powder structure",
        ),
    },
    "floral_powdery": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            44,
            38,
            ConcentrationBracket.EDT,
            "Powdery floral: restrained top, heart-to-base powder arc",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            45,
            43,
            ConcentrationBracket.EDP,
            "Powder floral EdP: iris-heliotrope-coumarin cushion",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            40,
            52,
            ConcentrationBracket.EXTRAIT,
            "Powder floral extrait: deep iris-tonka base",
        ),
    },
    "floral_green": {
        ConcentrationBracket.EDT: PyramidRatio(
            24,
            50,
            26,
            ConcentrationBracket.EDT,
            "Green floral: stemmy opening, floral center, restrained base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            50,
            32,
            ConcentrationBracket.EDP,
            "Green floral EdP: more iris/wood persistence below the stemmy heart",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            45,
            43,
            ConcentrationBracket.EXTRAIT,
            "Deep green floral with a more pronounced base shadow",
        ),
    },
    "floral_rose": {
        ConcentrationBracket.EDT: PyramidRatio(
            22, 52, 26, ConcentrationBracket.EDT, "Rose: green-citrus top, rose heart"
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            55,
            30,
            ConcentrationBracket.EDP,
            "Rose: PEA/citronellol/geraniol over woods",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            50,
            40,
            ConcentrationBracket.EXTRAIT,
            "Deep rose: damascone richness, musk base",
        ),
    },
    "floral_aldehydic": {
        ConcentrationBracket.EDT: PyramidRatio(
            30,
            45,
            25,
            ConcentrationBracket.EDT,
            "Aldehydic floral: sparkling aldehydic top",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            25,
            45,
            30,
            ConcentrationBracket.EDP,
            "Chanel No.5 style: aldehydes + rose/jasmine",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            20,
            40,
            40,
            ConcentrationBracket.EXTRAIT,
            "Rich aldehydic: aldehydes meld into musk",
        ),
    },
    # ── CHYPRE ──
    "chypre": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            30,
            45,
            ConcentrationBracket.EDT,
            "Classical chypre: bergamot/oakmoss/patchouli",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            30,
            50,
            ConcentrationBracket.EDP,
            "Chypre: citrus-flash over deep mossy base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            25,
            60,
            ConcentrationBracket.EXTRAIT,
            "Rich chypre: labdanum-heavy, moss tenacity",
        ),
    },
    "chypre_classical": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            30,
            45,
            ConcentrationBracket.EDT,
            "Classical chypre: bergamot over labdanum-moss base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            30,
            50,
            ConcentrationBracket.EDP,
            "Classical chypre EdP: deeper moss and patchouli persistence",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            25,
            60,
            ConcentrationBracket.EXTRAIT,
            "Classical chypre extrait: heavy labdanum-moss drydown",
        ),
    },
    "chypre_floral": {
        ConcentrationBracket.EDT: PyramidRatio(
            22,
            38,
            40,
            ConcentrationBracket.EDT,
            "Floral chypre: bergamot + rose over moss",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            38,
            44,
            ConcentrationBracket.EDP,
            "Floral chypre: rose-jasmine heart, patchouli base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12, 35, 53, ConcentrationBracket.EXTRAIT, "Rich floral chypre extrait"
        ),
    },
    "chypre_fruity": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            35,
            40,
            ConcentrationBracket.EDT,
            "Fruity chypre: peach/apricot over moss",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            38,
            42,
            ConcentrationBracket.EDP,
            "Mitsouko style: peach lactone + oakmoss",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EXTRAIT,
            "Rich fruity chypre, gamma decalactone base",
        ),
    },
    "chypre_green": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            35,
            40,
            ConcentrationBracket.EDT,
            "Green chypre: bitter-green opening over mossy base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            35,
            45,
            ConcentrationBracket.EDP,
            "Green chypre EdP: more moss and woody retention",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EXTRAIT,
            "Green chypre extrait: dense galbanum-moss structure",
        ),
    },
    "chypre_leathery": {
        ConcentrationBracket.EDT: PyramidRatio(
            20,
            30,
            50,
            ConcentrationBracket.EDT,
            "Leather chypre: bitter opening, leather shadow in the base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDP,
            "Leather chypre EdP: stronger base dominance and smoky fixation",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            25,
            63,
            ConcentrationBracket.EXTRAIT,
            "Leather chypre extrait: dark leather/moss foundation",
        ),
    },
    "chypre_modern": {
        ConcentrationBracket.EDT: PyramidRatio(
            22,
            33,
            45,
            ConcentrationBracket.EDT,
            "Modern chypre: Evernyl + Clearwood base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            18,
            32,
            50,
            ConcentrationBracket.EDP,
            "Modern chypre: bergamot/Evernyl/patchouli triad",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            13,
            30,
            57,
            ConcentrationBracket.EXTRAIT,
            "Rich modern chypre, Galbanum green edge",
        ),
    },
    # ── ORIENTAL ──
    "oriental": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            32,
            50,
            ConcentrationBracket.EDT,
            "Classical oriental: vanilla/resin base dominant",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDP,
            "Oriental: balsamic amber, vanilla-anchored",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            25,
            65,
            ConcentrationBracket.EXTRAIT,
            "Rich oriental: deep resinous base",
        ),
    },
    "oriental_classical": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            32,
            50,
            ConcentrationBracket.EDT,
            "Classical oriental: citrus opening over vanilla-resin base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDP,
            "Shalimar style: balsamic amber with plush base dominance",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            25,
            65,
            ConcentrationBracket.EXTRAIT,
            "Classical oriental extrait: maximal resin-vanilla depth",
        ),
    },
    "oriental_soft": {
        ConcentrationBracket.EDT: PyramidRatio(
            20,
            35,
            45,
            ConcentrationBracket.EDT,
            "Soft oriental: bright aromatic opening and lighter amber floor",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            16,
            36,
            48,
            ConcentrationBracket.EDP,
            "Soft amber EdP: bergamot-lavender over smooth benzoin-vanilla base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            32,
            58,
            ConcentrationBracket.EXTRAIT,
            "Soft oriental extrait with gentle but persistent base",
        ),
    },
    "oriental_amber": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDT,
            "Amber oriental: benzoin/labdanum/vanilla",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            28,
            60,
            ConcentrationBracket.EDP,
            "Warm amber: Ambrox+benzoin+vanillin trinity",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            22,
            70,
            ConcentrationBracket.EXTRAIT,
            "Rich amber: labdanum absolute, vanilla resinoid",
        ),
    },
    "oriental_spicy": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            34,
            48,
            ConcentrationBracket.EDT,
            "Spicy oriental: cinnamon/cardamom + vanilla",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            14,
            32,
            54,
            ConcentrationBracket.EDP,
            "Spiced amber: eugenol/isoeugenol + benzoin",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            28,
            62,
            ConcentrationBracket.EXTRAIT,
            "Rich spiced oriental, clove-carnation base",
        ),
    },
    "oriental_gourmand": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDT,
            "Gourmand oriental: ethyl maltol + vanilla",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            28,
            60,
            ConcentrationBracket.EDP,
            "Gourmand: coumarin/vanillin/ethyl maltol",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            22,
            70,
            ConcentrationBracket.EXTRAIT,
            "Rich gourmand: caramel-vanilla-tonka base",
        ),
    },
    "oriental_floral": {
        ConcentrationBracket.EDT: PyramidRatio(
            16,
            40,
            44,
            ConcentrationBracket.EDT,
            "Floral oriental: powder-floral heart over amber base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            40,
            48,
            ConcentrationBracket.EDP,
            "Floral oriental EdP: L'Heure Bleue style floral-powder glow",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            35,
            57,
            ConcentrationBracket.EXTRAIT,
            "Floral oriental extrait: powder and resin fully fused",
        ),
    },
    # ── WOODY ──
    "woody": {
        ConcentrationBracket.EDT: PyramidRatio(
            20,
            35,
            45,
            ConcentrationBracket.EDT,
            "Classical woody: cedar/sandalwood/vetiver",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDP,
            "Woody: Iso E Super aura, sandalwood core",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            25,
            65,
            ConcentrationBracket.EXTRAIT,
            "Rich woody: deep sandalwood, norlimbanol",
        ),
    },
    "woody_amber": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            32,
            50,
            ConcentrationBracket.EDT,
            "Woody amber: Ambrox + Iso E Super + cedar",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            30,
            58,
            ConcentrationBracket.EDP,
            "Amber-woods: transparent radiance + sandalwood",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            25,
            67,
            ConcentrationBracket.EXTRAIT,
            "Deep amber-woods: cashmeran, norlimbanol",
        ),
    },
    "woody_mineral": {
        ConcentrationBracket.EDT: PyramidRatio(
            20, 30, 50, ConcentrationBracket.EDT, "Mineral woody: flint/cold cedar"
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12, 28, 60, ConcentrationBracket.EDP, "Ellena style: transparent cold woods"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            22,
            70,
            ConcentrationBracket.EXTRAIT,
            "Deep mineral: Timberol + Norlimbanol + Ambrox",
        ),
    },
    "woody_oriental": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDT,
            "Woody oriental: oud + sandalwood + amber",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            10,
            28,
            62,
            ConcentrationBracket.EDP,
            "Oud-woody: synthetic oud + vanilla + wood",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            22,
            70,
            ConcentrationBracket.EXTRAIT,
            "Rich oud-woody, balsamic-resinous base",
        ),
    },
    # ── WOODY FLORAL MUSK ──
    "woody_floral_musk": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            38,
            44,
            ConcentrationBracket.EDT,
            "Woody floral musk: citrus-aromatic lift, floral-woody heart, clean musk base",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            35,
            50,
            ConcentrationBracket.EDP,
            "Classic woody floral musk: iris-sandalwood core, transparent musk persistence",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            12,
            30,
            58,
            ConcentrationBracket.EXTRAIT,
            "Rich woody floral musk: deep sandalwood-musk, minimal top",
        ),
    },
    # ── LEATHER ──
    "leather": {
        ConcentrationBracket.EDT: PyramidRatio(
            18, 32, 50, ConcentrationBracket.EDT, "Classical leather: IBQ + birch tar"
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDP,
            "Leather: suederal/IBQ/Styrax over woods",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            25,
            65,
            ConcentrationBracket.EXTRAIT,
            "Rich leather: labdanum + birch + styrax",
        ),
    },
    "leather_suede": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            35,
            50,
            ConcentrationBracket.EDT,
            "Suede: soft leather, powdery-violet overcast",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            10,
            33,
            57,
            ConcentrationBracket.EDP,
            "Soft suede: Suederal + Cashmeran + Violet",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            28,
            64,
            ConcentrationBracket.EXTRAIT,
            "Rich suede: Vetival + Iso E Super + Cashmeran",
        ),
    },
    # ── MARINE/AQUATIC ──
    "marine_aquatic": {
        ConcentrationBracket.EDT: PyramidRatio(
            30,
            40,
            30,
            ConcentrationBracket.EDT,
            "Aquatic fresh: calone/floralozone + hedione",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            22,
            40,
            38,
            ConcentrationBracket.EDP,
            "Marine: dihydromyrcenol + hedione + musk",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            38,
            47,
            ConcentrationBracket.EXTRAIT,
            "Deep marine: Ambrox + musk + ozonic persist",
        ),
    },
    # ── GOURMAND ──
    "gourmand": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            30,
            55,
            ConcentrationBracket.EDT,
            "Gourmand: ethyl maltol + vanilla + tonka",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            28,
            60,
            ConcentrationBracket.EDP,
            "Gourmand sweet: vanilla/caramel/chocolate base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            22,
            70,
            ConcentrationBracket.EXTRAIT,
            "Rich gourmand: coumarin/benzoin/vanillin depth",
        ),
    },
    # ── MUSK ──
    "musk": {
        ConcentrationBracket.EDT: PyramidRatio(
            15,
            35,
            50,
            ConcentrationBracket.EDT,
            "Clean musk: galaxolide/habanolide/ethylene brassylate",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            10,
            35,
            55,
            ConcentrationBracket.EDP,
            "Skin musk: intimate, warm macrocyclics",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            30,
            62,
            ConcentrationBracket.EXTRAIT,
            "Rich musk: ambrettolide/exaltolide deep",
        ),
    },
    "musk_clean": {
        ConcentrationBracket.EDT: PyramidRatio(
            18,
            37,
            45,
            ConcentrationBracket.EDT,
            "Laundry musk: DHM + galaxolide + zenolide",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            36,
            52,
            ConcentrationBracket.EDP,
            "Clean white musk: transparent, bright",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            32,
            60,
            ConcentrationBracket.EXTRAIT,
            "Deep clean musk: habanolide + romandolide",
        ),
    },
    "musk_skin": {
        ConcentrationBracket.EDT: PyramidRatio(
            12,
            33,
            55,
            ConcentrationBracket.EDT,
            "Skin musk: ethylene brassylate + ambrox",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            8, 30, 62, ConcentrationBracket.EDP, "Intimate skin: exaltolide + cashmeran"
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            5,
            25,
            70,
            ConcentrationBracket.EXTRAIT,
            "Rich skin musk: minimal top, body-close base",
        ),
    },
    # ── GREEN ──
    "green": {
        ConcentrationBracket.EDT: PyramidRatio(
            30,
            40,
            30,
            ConcentrationBracket.EDT,
            "Green fresh: galbanum + cis-3-hexenol top",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            22,
            40,
            38,
            ConcentrationBracket.EDP,
            "Green: galbanum/violet leaf over vetiver",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            38,
            47,
            ConcentrationBracket.EXTRAIT,
            "Deep green: galbanum + oakmoss + vetiver",
        ),
    },
    # ── ALDEHYDIC ──
    "aldehydic": {
        ConcentrationBracket.EDT: PyramidRatio(
            35,
            40,
            25,
            ConcentrationBracket.EDT,
            "Aldehydic: C10/C11/C12 sparkle over florals",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            28,
            42,
            30,
            ConcentrationBracket.EDP,
            "Chanel style: aldehydes + rose/jasmine + musk",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            20,
            40,
            40,
            ConcentrationBracket.EXTRAIT,
            "Rich aldehydic: aldehydes meld into sandalwood",
        ),
    },
    "floral_aldehydic_amber": {
        ConcentrationBracket.EDT: PyramidRatio(
            25,
            40,
            35,
            ConcentrationBracket.EDT,
            "Aldehydic floral-amber: sparkling top over warm amber",
        ),
        ConcentrationBracket.EDP: PyramidRatio(
            20,
            40,
            40,
            ConcentrationBracket.EDP,
            "Floral aldehydic amber: aldehydes + rose/jasmine + amber base",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            15,
            35,
            50,
            ConcentrationBracket.EXTRAIT,
            "Rich floral aldehydic amber: deep amber-woody base",
        ),
    },
    # ── IRIS-AMBER-WOODY (DHI/DHP niche DNA) ──
    "iris_amber_woody": {
        ConcentrationBracket.EDP: PyramidRatio(
            12,
            35,
            53,
            ConcentrationBracket.EDP,
            "Iris-amber-woody: DHI niche DNA, base-dominant iris-coumarin-vanilla-cashmeran skeleton",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            8,
            30,
            62,
            ConcentrationBracket.EXTRAIT,
            "Rich iris-amber: deep coumarin-vanilla-labdanum base",
        ),
    },
    "iris_leather_amber": {
        ConcentrationBracket.EDP: PyramidRatio(
            10,
            30,
            60,
            ConcentrationBracket.EDP,
            "Iris-leather-amber: DHP leather DNA, IBQ-iris-oud skeleton, base-dominant by design",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            7,
            25,
            68,
            ConcentrationBracket.EXTRAIT,
            "Deep leather-iris: IBQ+oud+labdanum+amber base",
        ),
    },
    # ── GOURMAND FLORAL ──
    "gourmand_floral": {
        ConcentrationBracket.EDP: PyramidRatio(
            15,
            45,
            40,
            ConcentrationBracket.EDP,
            "Gourmand-floral hybrid: floral heart dominant, substantial gourmand-woody base for cocoa-vanilla persistence",
        ),
        ConcentrationBracket.EXTRAIT: PyramidRatio(
            10,
            40,
            50,
            ConcentrationBracket.EXTRAIT,
            "Rich gourmand-floral extrait: deeper vanilla-coumarin base with tuberose-jasmine heart",
        ),
    },
}

DEFAULT_PYRAMID: dict[ConcentrationBracket, PyramidRatio] = {
    ConcentrationBracket.EDC: PyramidRatio(
        40, 35, 25, ConcentrationBracket.EDC, "Classical cologne pyramid"
    ),
    ConcentrationBracket.EDT: PyramidRatio(
        30, 40, 30, ConcentrationBracket.EDT, "Standard EDT pyramid"
    ),
    ConcentrationBracket.EDP: PyramidRatio(
        20,
        40,
        40,
        ConcentrationBracket.EDP,
        "Standard EDP pyramid: heart+base dominant",
    ),
    ConcentrationBracket.EXTRAIT: PyramidRatio(
        12, 33, 55, ConcentrationBracket.EXTRAIT, "Extrait: base dominant, top reduced"
    ),
    ConcentrationBracket.BODY_SPRAY: PyramidRatio(
        35, 40, 25, ConcentrationBracket.BODY_SPRAY, "Body spray: top-fresh dominant"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# OAV TARGETS BY FAMILY — Aggregate OAV targets per time window
# ═══════════════════════════════════════════════════════════════════════════════

OAV_TARGETS_BY_FAMILY: dict[str, dict[str, dict[str, float]]] = {
    "citrus": {
        "top": {"citrus": 4000, "fresh": 600, "green": 200},
        "heart": {"citrus": 400, "floral": 300, "green": 150},
        "base": {"wood": 40, "musk": 15},
    },
    "citrus_classical": {
        "top": {"citrus": 1500, "fresh": 300, "floral": 140},
        "heart": {"citrus": 500, "floral": 220, "green": 80},
        "base": {"wood": 10, "musk": 16},
    },
    "citrus_aromatic": {
        "top": {"citrus": 3000, "aromatic": 300, "fresh": 500},
        "heart": {"citrus": 350, "aromatic": 250, "floral": 200},
        "base": {"wood": 50, "musk": 18, "aromatic": 25},
    },
    "citrus_woody": {
        "top": {"citrus": 2500, "fresh": 400, "green": 250},
        "heart": {"citrus": 300, "wood": 85, "floral": 150},
        "base": {"wood": 120, "musk": 22},
    },
    "dior_homme_cologne": {
        "top": {"citrus": 20000, "aromatic": 5000},
        "heart": {"citrus": 20000, "floral": 5000, "wood": 5000},
        "base": {"wood": 3500, "floral": 5000},
    },
    "fougere_classical": {
        "top": {"citrus": 900, "aromatic": 260, "fresh": 210},
        "heart": {"aromatic": 260, "coumarin": 16, "green": 80},
        "base": {"aromatic": 95, "wood": 45, "moss": 10, "coumarin": 12},
    },
    "aromatic_fougere": {
        "top": {"citrus": 1500, "aromatic": 220, "fresh": 400},
        "heart": {"aromatic": 550, "coumarin": 18, "green": 90},
        "base": {"wood": 55, "musk": 20, "coumarin": 14},
    },
    "fougere_modern_mineral": {
        "top": {"citrus": 1800, "fresh": 1200, "aromatic": 180, "marine": 45},
        "heart": {"fresh": 3200, "aromatic": 700, "marine": 260},
        "base": {"marine": 160, "wood": 70, "aromatic": 30},
    },
    "fougere_modern_tonka": {
        "top": {"citrus": 1500, "fruity": 160, "aromatic": 180},
        "heart": {"aromatic": 700, "fruity": 900, "coumarin": 18},
        "base": {"wood": 40, "musk": 18, "coumarin": 12},
    },
    "floral": {
        "top": {"green": 200, "citrus": 400, "fruity": 120},
        "heart": {"floral": 800, "rose": 300, "muguet": 200},
        "base": {"musk": 30, "wood": 25, "powder": 15},
    },
    "floral_soliflore": {
        "top": {"green": 100, "citrus": 150},
        "heart": {"floral": 1200, "rose": 500, "muguet": 300},
        "base": {"musk": 20, "wood": 15},
    },
    "floral_bouquet": {
        "top": {"floral": 420, "citrus": 220, "aldehydic": 180},
        "heart": {"floral": 1100, "rose": 260, "jasmine": 220, "muguet": 160},
        "base": {"musk": 20, "wood": 12, "amber": 8},
    },
    "floral_white": {
        "top": {"citrus": 350, "green": 150},
        "heart": {"floral": 1000, "gardenia": 200, "muguet": 200},
        "base": {"musk": 30, "salicylate": 40},
    },
    "floral_muguet": {
        "top": {"muguet": 220, "green": 100, "citrus": 140},
        "heart": {"muguet": 420, "floral": 700},
        "base": {"musk": 16, "wood": 8},
    },
    "floral_carnation": {
        "top": {"spicy": 140, "floral": 180},
        "heart": {"spicy": 220, "floral": 700, "rose": 120},
        "base": {"powder": 30, "musk": 14, "wood": 10},
    },
    "floral_powdery": {
        "top": {"powder": 60, "citrus": 120, "floral": 220},
        "heart": {"powder": 180, "floral": 720, "iris": 80},
        "base": {"powder": 45, "musk": 18, "amber": 12},
    },
    "floral_green": {
        "top": {"green": 260, "citrus": 220, "floral": 140},
        "heart": {"green": 220, "floral": 620, "powder": 40},
        "base": {"wood": 18, "musk": 14, "green": 30},
    },
    "floral_rose": {
        "top": {"citrus": 300, "green": 180, "fruity": 60},
        "heart": {"rose": 600, "PEA": 80, "geraniol": 100, "citronellol": 150},
        "base": {"musk": 25, "wood": 20},
    },
    "floral_aldehydic": {
        "top": {"aldehydic": 300, "citrus": 500, "green": 150},
        "heart": {"floral": 600, "rose": 350, "jasmine": 250},
        "base": {"musk": 35, "wood": 30, "iris": 15},
    },
    "chypre": {
        "top": {"citrus": 900, "green": 180, "galbanum": 8},
        "heart": {"floral": 400, "patchouli": 25, "spicy": 30},
        "base": {"moss": 25, "wood": 60, "labdanum": 15, "musk": 20},
    },
    "chypre_classical": {
        "top": {"citrus": 700, "green": 80},
        "heart": {"floral": 260, "moss": 16, "wood": 30},
        "base": {"moss": 22, "wood": 52, "amber": 12, "musk": 14},
    },
    "chypre_floral": {
        "top": {"citrus": 700, "green": 150},
        "heart": {"floral": 550, "rose": 250, "patchouli": 20},
        "base": {"moss": 20, "wood": 55, "musk": 22},
    },
    "chypre_fruity": {
        "top": {"citrus": 800, "fruity": 100},
        "heart": {"floral": 350, "peach": 25, "rose": 180},
        "base": {"moss": 22, "wood": 50, "musk": 18},
    },
    "chypre_green": {
        "top": {"green": 300, "citrus": 420},
        "heart": {"green": 180, "floral": 260, "moss": 12},
        "base": {"moss": 18, "wood": 48, "musk": 14},
    },
    "chypre_leathery": {
        "top": {"green": 100, "citrus": 240},
        "heart": {"leather": 20, "wood": 40, "moss": 14},
        "base": {"leather": 18, "wood": 60, "moss": 18, "musk": 12},
    },
    "chypre_modern": {
        "top": {"citrus": 600, "green": 140, "fresh": 300},
        "heart": {"floral": 350, "evernyl": 12, "patchouli": 18},
        "base": {"moss": 16, "wood": 55, "musk": 22, "amber": 10},
    },
    "oriental": {
        "top": {"citrus": 500, "spicy": 100},
        "heart": {"floral": 300, "spicy": 150, "amber": 60},
        "base": {"vanilla": 40, "resin": 50, "musk": 15, "wood": 35},
    },
    "oriental_classical": {
        "top": {"citrus": 420, "spicy": 90},
        "heart": {"floral": 220, "amber": 80, "resin": 45},
        "base": {"vanilla": 38, "resin": 52, "wood": 28, "musk": 12},
    },
    "oriental_soft": {
        "top": {"citrus": 550, "aromatic": 180},
        "heart": {"floral": 220, "amber": 55, "coumarin": 16},
        "base": {"vanilla": 26, "musk": 18, "wood": 18, "resin": 28},
    },
    "oriental_amber": {
        "top": {"citrus": 300, "spicy": 60},
        "heart": {"amber": 100, "benzoin": 25, "floral": 150},
        "base": {"vanilla": 50, "labdanum": 25, "resin": 60, "musk": 12},
    },
    "oriental_spicy": {
        "top": {"citrus": 400, "spicy": 120, "cinnamon": 10},
        "heart": {"spicy": 200, "clove": 30, "floral": 200},
        "base": {"vanilla": 35, "resin": 45, "musk": 15, "wood": 30},
    },
    "oriental_gourmand": {
        "top": {"citrus": 200, "fruity": 80},
        "heart": {"gourmand": 150, "vanilla": 30, "coumarin": 20, "floral": 150},
        "base": {"vanilla": 60, "caramel": 25, "tonka": 20, "musk": 12},
    },
    "oriental_floral": {
        "top": {"floral": 240, "citrus": 100, "powder": 50},
        "heart": {"floral": 700, "amber": 80, "powder": 120},
        "base": {"vanilla": 30, "resin": 34, "powder": 35, "musk": 16},
    },
    "woody": {
        "top": {"citrus": 350, "fresh": 250, "green": 120},
        "heart": {"wood": 150, "cedar": 80, "floral": 120},
        "base": {"wood": 80, "musk": 25, "amber": 15},
    },
    "woody_amber": {
        "top": {"citrus": 250, "fresh": 300},
        "heart": {"wood": 120, "amber": 80, "floral": 80},
        "base": {"wood": 100, "musk": 30, "amber": 40},
    },
    "woody_mineral": {
        "top": {"citrus": 200, "marine": 60, "green": 150},
        "heart": {"wood": 100, "mineral": 40, "cedar": 70},
        "base": {"wood": 90, "musk": 18, "mineral": 25},
    },
    "woody_oriental": {
        "top": {"citrus": 200, "spicy": 80},
        "heart": {"wood": 80, "oud": 15, "floral": 100},
        "base": {"wood": 100, "oud": 25, "resin": 40, "musk": 20},
    },
    "leather": {
        "top": {"citrus": 250, "green": 100},
        "heart": {"leather": 30, "floral": 120, "styrax": 15},
        "base": {"leather": 20, "wood": 60, "birch": 5, "musk": 18},
    },
    "leather_suede": {
        "top": {"citrus": 150, "green": 80},
        "heart": {"suede": 20, "powder": 15, "floral": 100},
        "base": {"suede": 15, "wood": 50, "musk": 22, "cashmeran": 8},
    },
    "marine_aquatic": {
        "top": {"citrus": 800, "marine": 200, "fresh": 600},
        "heart": {"marine": 300, "floral": 250, "linalool": 80},
        "base": {"marine": 50, "musk": 30, "wood": 25},
    },
    "marine_ozonic": {
        "top": {"citrus": 700, "ozonic": 150, "fresh": 800},
        "heart": {"ozonic": 200, "marine": 200, "floral": 200},
        "base": {"marine": 40, "musk": 25, "wood": 20},
    },
    "gourmand": {
        "top": {"citrus": 150, "fruity": 100},
        "heart": {"fruity": 150, "gourmand": 200, "vanilla": 35, "floral": 100},
        "base": {"vanilla": 65, "caramel": 30, "tonka": 22, "musk": 12},
    },
    "musk": {
        "top": {"citrus": 150, "fresh": 200},
        "heart": {"floral": 150, "musk": 40, "powder": 15},
        "base": {"musk": 80, "wood": 20, "amber": 10},
    },
    "musk_clean": {
        "top": {"citrus": 200, "fresh": 300},
        "heart": {"floral": 100, "musk": 35, "fresh": 150},
        "base": {"musk": 90, "wood": 15},
    },
    "musk_skin": {
        "top": {"fresh": 80},
        "heart": {"musk": 30, "floral": 60},
        "base": {"musk": 100, "amber": 15, "wood": 12},
    },
    "green": {
        "top": {"green": 300, "galbanum": 15, "citrus": 400},
        "heart": {"green": 200, "floral": 200, "violet_leaf": 12},
        "base": {"green": 60, "wood": 45, "musk": 18},
    },
    "aldehydic": {
        "top": {"aldehydic": 350, "citrus": 500},
        "heart": {"floral": 500, "rose": 300, "muguet": 200},
        "base": {"musk": 35, "wood": 30, "iris": 15},
    },
    "layton_dna_fresh": {
        "top": {"citrus": 1700, "fruity": 85, "fresh": 420, "aromatic": 230},
        "heart": {"citrus": 900, "fruity": 110, "fresh": 780, "amber": 140},
        "base": {"amber": 280, "wood": 45, "musk": 24, "gourmand": 12},
    },
    "layton_dna_indoor": {
        "top": {"citrus": 1150, "fruity": 65, "aromatic": 175, "amber": 190},
        "heart": {"amber": 145, "fruity": 85, "radiance": 140, "wood": 70},
        "base": {"amber": 145, "wood": 42, "musk": 24, "gourmand": 12},
    },
    "layton_dna_night": {
        "top": {"citrus": 1200, "fruity": 85, "aromatic": 180, "amber": 190},
        "heart": {"amber": 165, "fruity": 115, "radiance": 105, "wood": 70},
        "base": {"amber": 165, "wood": 72, "musk": 25, "gourmand": 20},
    },
    "floral_aldehydic_amber": {
        "top": {"aldehydic": 250, "citrus": 450, "green": 100},
        "heart": {"floral": 800, "rose": 300, "jasmine": 200},
        "base": {"amber": 100, "musk": 25, "wood": 30},
    },
    "iris_amber_woody": {
        "top": {"citrus": 200, "iris": 40, "powder": 30, "spicy": 20},
        "heart": {"iris": 500, "powder": 200, "wood": 80, "amber": 60, "floral": 150},
        "base": {
            "wood": 150,
            "amber": 100,
            "vanilla": 50,
            "musk": 25,
            "coumarin": 18,
            "iris": 30,
        },
    },
    "iris_leather_amber": {
        "top": {"citrus": 150, "iris": 30, "spicy": 20, "aromatic": 40},
        "heart": {"iris": 350, "leather": 50, "powder": 150, "wood": 80, "floral": 120},
        "base": {
            "leather": 60,
            "wood": 150,
            "amber": 80,
            "musk": 25,
            "resin": 20,
            "oud": 15,
        },
    },
    "gourmand_floral": {
        "top": {"citrus": 350, "gourmand": 35, "floral": 180, "green": 60},
        "heart": {"floral": 900, "gourmand": 65, "vanilla": 25, "coumarin": 18},
        "base": {
            "gourmand": 100,
            "vanilla": 45,
            "coumarin": 25,
            "wood": 35,
            "musk": 25,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIAL ROLE RATIOS — Expected % of concentrate by role type
# ═══════════════════════════════════════════════════════════════════════════════

MATERIAL_ROLE_RATIOS: dict[str, dict[str, tuple[float, float]]] = {
    "citrus_cologne": {
        "character": (40, 60),
        "modifier": (15, 25),
        "fixative": (10, 20),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
    "fougere": {
        "character": (25, 40),
        "modifier": (15, 25),
        "fixative": (20, 35),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 2),
    },
    "floral": {
        "character": (35, 55),
        "modifier": (10, 20),
        "fixative": (15, 30),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 2),
    },
    "chypre": {
        "character": (30, 45),
        "modifier": (15, 25),
        "fixative": (20, 35),
        "volume": (5, 10),
        "bridge": (5, 10),
        "trace": (0, 2),
    },
    "oriental": {
        "character": (25, 40),
        "modifier": (15, 25),
        "fixative": (25, 45),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 2),
    },
    "woody": {
        "character": (30, 45),
        "modifier": (15, 25),
        "fixative": (20, 35),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
    "marine": {
        "character": (25, 40),
        "modifier": (20, 35),
        "fixative": (10, 20),
        "volume": (10, 20),
        "bridge": (5, 15),
        "trace": (0, 2),
    },
    "gourmand": {
        "character": (30, 50),
        "modifier": (10, 20),
        "fixative": (15, 30),
        "volume": (10, 20),
        "bridge": (5, 10),
        "trace": (0, 2),
    },
    "musk_centric": {
        "character": (35, 55),
        "modifier": (10, 20),
        "fixative": (15, 25),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
    "soliflore": {
        "character": (45, 65),
        "modifier": (10, 20),
        "fixative": (10, 20),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
    "iris_amber_woody": {
        "character": (25, 45),
        "modifier": (10, 20),
        "fixative": (25, 45),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
    "iris_leather_amber": {
        "character": (25, 45),
        "modifier": (10, 20),
        "fixative": (25, 45),
        "volume": (5, 15),
        "bridge": (5, 10),
        "trace": (0, 3),
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-FAMILY COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════════

CROSS_FAMILY_COMPATIBILITY: dict[tuple[str, str], str] = {
    ("citrus", "floral"): "high",
    ("citrus", "aromatic_fougere"): "high",
    ("citrus", "marine_aquatic"): "high",
    ("citrus", "green"): "high",
    ("floral", "woody"): "high",
    ("floral", "oriental"): "high",
    ("floral", "chypre"): "high",
    ("floral", "aldehydic"): "high",
    ("floral_rose", "oud_woody"): "high",
    ("floral_jasmine", "chypre"): "high",
    ("aromatic_fougere", "chypre"): "high",
    ("aromatic_fougere", "leather"): "medium",
    ("chypre", "leather"): "high",
    ("chypre", "gourmand"): "medium",
    ("oriental", "woody"): "high",
    ("oriental", "gourmand"): "high",
    ("oriental", "leather"): "high",
    ("woody_amber", "oriental_amber"): "high",
    ("gourmand", "oriental_amber"): "high",
    ("marine_aquatic", "floral_rose"): "medium",
    ("marine_aquatic", "woody"): "medium",
    ("citrus", "leather"): "low",
    ("marine_aquatic", "gourmand"): "low",
    ("marine_aquatic", "oriental"): "low",
    ("citrus", "amber_oriental"): "medium",
    ("floral_jasmine", "leather"): "low",
    ("marine_aquatic", "amber_oriental"): "very_low",
    ("aldehydic", "citrus"): "medium",
    ("aldehydic", "gourmand"): "low",
    ("iris_amber_woody", "oriental_amber"): "high",
    ("iris_amber_woody", "woody_amber"): "high",
    ("iris_amber_woody", "floral_powdery"): "high",
    ("iris_amber_woody", "oriental"): "high",
    ("iris_leather_amber", "leather"): "high",
    ("iris_leather_amber", "woody_oriental"): "high",
    ("iris_leather_amber", "chypre_leathery"): "medium",
    ("iris_leather_amber", "oriental"): "high",
    ("iris_amber_woody", "gourmand"): "medium",
}


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_pyramid(
    key: str, bracket: ConcentrationBracket | None = None
) -> PyramidRatio | None:
    """Return pyramid ratio for a family key and concentration bracket. Falls back to defaults."""
    if bracket is None:
        bracket = ConcentrationBracket.EDP
    family_pyramids = PYRAMID_RATIOS.get(key)
    if family_pyramids:
        return family_pyramids.get(bracket) or family_pyramids.get(
            ConcentrationBracket.EDP
        )
    return DEFAULT_PYRAMID.get(bracket)


def get_oav_targets(family: str) -> dict[str, dict[str, float]]:
    """Return OAV targets for a family, or empty dict."""
    return OAV_TARGETS_BY_FAMILY.get(family, {})


def get_oav_target(family: str, time_window: str, odour_family: str) -> float | None:
    """Return a specific OAV target value."""
    targets = OAV_TARGETS_BY_FAMILY.get(family, {})
    window = targets.get(time_window, {})
    return window.get(odour_family)


def get_compatibility(family_a: str, family_b: str) -> str:
    """Return compatibility level between two families (high/medium/low/very_low/unknown)."""
    key = (family_a.lower(), family_b.lower())
    result = CROSS_FAMILY_COMPATIBILITY.get(key)
    if result:
        return result
    key_rev = (family_b.lower(), family_a.lower())
    return CROSS_FAMILY_COMPATIBILITY.get(key_rev, "unknown")


def get_material_role_range(family_style: str, role: str) -> tuple[float, float] | None:
    """Return the expected % range for a material role in a given family style."""
    roles = MATERIAL_ROLE_RATIOS.get(family_style, {})
    return roles.get(role)


def all_pyramid_keys() -> list[str]:
    """Return all family keys that have pyramid ratios defined."""
    return sorted(PYRAMID_RATIOS.keys())


def all_oav_target_keys() -> list[str]:
    """Return all family keys that have OAV targets defined."""
    return sorted(OAV_TARGETS_BY_FAMILY.keys())
