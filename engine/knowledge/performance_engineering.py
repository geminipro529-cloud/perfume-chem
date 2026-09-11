"""Function-balance doctrine for the canonical pipeline.

The live *release gate* adapter lives in :mod:`engine.pipeline.gates`
(``_gate_function_balance``). This module is the import-safe knowledge surface,
holding the function model, the peer-reviewed citation registry and the
classification/balance logic. It deliberately has no dependency on the pipeline
package so it can be reasoned about and tested in isolation.

Function layer
--------------

The Heart / Modifier / Blender / Fixative / X-Factor layer is the practitioner
"Grammar of Perfumery" model (Dowthwaite 1999, 2004) built on top of the Carles
pyramid (Carles 1961). The key doctrine is that there are **no fixed material
lists**: a material's function is contextual, determined by its dose and by the
other materials present, and more than one function can be served by a single
material.

Research anchors (the numeric criteria used below)
--------------------------------------------------

Tier A (peer reviewed)
  * Rodrigues, Nogueira & Faria 2021, *Molecules* 26(11):3095 — perfume
    engineering review. Odor Value ``OV = C_gas / ODT`` (perceptible at OV>1);
    Strongest Component Model (``OV_mixture = max OV_i``) so the heart is the
    dominant odor value; Carles pyramid with middle notes giving the *character*
    (3–4 h) and base notes giving *substantivity* (>4 h); performance parameters
    impact/tenacity/diffusion/volume.
  * Mata, Gomes & Rodrigues 2005, *AIChE J* 51(9):2565 — fixatives lower the
    evaporative release of the perfume into the headspace.
  * Teixeira, Rodríguez, Mata & Rodrigues 2009, *Chem. Eng. Sci.* 64:2570 and
    Teixeira, Rodríguez & Rodrigues 2013, *AIChE J* 59(9):3350 — 1-D/3-D
    evaporation and diffusion; base notes/fixatives shape the lasting phase.
  * Laing & Francis 1989, *Physiol. Behav.* 46:809; Livermore & Laing 1996,
    *J. Exp. Psychol. Hum. Percept. Perform.* 22:267; Jinks & Laing 1999,
    *Perception* 28:395 — humans identify only ~3-4 components in a mixture, so
    an identifiable subject must stay small.
  * Stevens 1957, *Psychol. Rev.* 64:153 and 1971, *Psychol. Rev.* 78:426; Cain
    1969, *Percept. Psychophys.* 5:347 — perceived intensity follows a power law
    ``I = OV**n`` with family-dependent, sub-unity exponents (odor among the
    lowest).
  * Murphy & Cain 1980, *Physiol. Behav.* 24:493 — the perceived harmony of a
    mixture governs whether components add or interact.

Tier C (practitioner)
  * Dowthwaite 1999, "The ABCs of Perfumery", *Perfumer & Flavorist* — relative
    impact measured against Linalool Synthetic; blenders have impact <= 100,
    otherwise they present as modifiers; modifiers that are overdosed become the
    subject/heart.
  * Dowthwaite 2004, "The Grammar of Perfumery" — subject/modifiers/blenders/
    fixatives and the balance diagnostic.
  * Carles 1961, *A Method of Creation in Perfumery* — pyramid / Modifier / Base
    construction.

All numeric criteria below are **evidence classed**; nothing here is promoted to
measured truth, and the gate is opt-in and advisory.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

# ---------------------------------------------------------------------------
# Backwards-compatible knowledge surface (pre-existing API)
# ---------------------------------------------------------------------------

PERFORMANCE_ENGINEERING_REFERENCES = {
    "projection": (
        "Use OAV carriers, diffusion boosters, and volatility layering to create "
        "projection without collapsing the formula into one loud material."
    ),
    "fixation": (
        "Fixative logic should combine multiple mechanisms such as caging, "
        "mw/logP persistence, and hydrogen-bond support rather than one brute-force base."
    ),
    "legibility": (
        "Performance gains do not justify unreadable overdosing; structural waste "
        "and sensory crowding should remain visible in the release path."
    ),
}


def get_performance_engineering_references() -> dict[str, str]:
    return dict(PERFORMANCE_ENGINEERING_REFERENCES)


# ---------------------------------------------------------------------------
# Function model constants
# ---------------------------------------------------------------------------

HEART = "heart"
MODIFIER = "modifier"
BLENDER = "blender"
FIXATIVE = "fixative"
X_FACTOR = "x_factor"
FUNCTIONAL_ROLES: tuple[str, ...] = (HEART, MODIFIER, BLENDER, FIXATIVE, X_FACTOR)

FUNCTION_BALANCE_SCHEMA_VERSION = "function_balance_v1"

# Evidence classes
TIER_A_PEER_REVIEWED = "A_peer_reviewed"
TIER_B_CLASSICAL_TEXT = "B_classical_text"
TIER_C_PRACTITIONER = "C_practitioner"

# Research-derived thresholds -------------------------------------------------
# Perceptibility floor: OV = C_gas/ODT, perceptible at OV > 1 (Rodrigues 2021).
PERCEPTIBILITY_OAV_FLOOR = 1.0
# Base notes last > 4 h on skin (Rodrigues 2021); fixatives must persist.
FIXATIVE_ODOUR_LIFE_MIN_HRS = 4.0
# Base tier volatility ceiling (repo note tier; base notes are the lasting phase).
FIXATIVE_VP_MAX_PA = 0.1
# Blenders measured against Linalool Synthetic = 100 and must stay <= 100
# otherwise they present as modifiers (Dowthwaite 1999).
LINALOOL_REFERENCE_IMPACT = 100.0
BLENDER_IMPACT_MAX = 100.0
# Modifiers are decoration/traces; above this they risk becoming the subject.
MODIFIER_TRACE_MAX_PCT = 5.0
# Humans identify only ~3-4 components in a mixture (Laing 1989; Livermore 1996;
# Jinks 1999), so the identifiable subject/heart should stay within that bound.
HEART_COMPONENT_LIMIT = 4
# "Special modifier" accent that only reads as an X-Factor at trace dose.
X_FACTOR_MAX_PCT = 2.0
X_FACTOR_MIN_IMPACT = 1000.0


# ---------------------------------------------------------------------------
# Citation registry
# ---------------------------------------------------------------------------

FUNCTIONAL_BALANCE_CITATIONS: dict[str, dict[str, str]] = {
    "dowthwaite_1999": {
        "tier": TIER_C_PRACTITIONER,
        "authors": "Dowthwaite, S. V.",
        "title": "The ABCs of Perfumery",
        "source": "Perfumer & Flavorist, May/June 1999",
        "url": "https://www.perfumersworld.com/abcs-perfumery.php",
        "used_for": "Function layer; relative impact vs Linalool=100; blender/modifier/fixative definitions",
    },
    "dowthwaite_2004": {
        "tier": TIER_C_PRACTITIONER,
        "authors": "Dowthwaite, S. V.",
        "title": "The Grammar of Perfumery",
        "source": "Practitioner codification",
        "url": "",
        "used_for": "Subject/modifiers/blenders/fixatives and the balance diagnostic",
    },
    "carles_1961": {
        "tier": TIER_C_PRACTITIONER,
        "authors": "Carles, J.",
        "title": "A Method of Creation in Perfumery",
        "source": "Classical perfumery text",
        "url": "",
        "used_for": "Pyramid / Modifier / Base construction",
    },
    "rodrigues_2021": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Rodrigues, A. E.; Nogueira, I.; Faria, R. P. V.",
        "title": "Perfume and Flavor Engineering: A Chemical Engineering Perspective",
        "source": "Molecules 2021, 26(11):3095",
        "url": "https://doi.org/10.3390/molecules26113095",
        "used_for": "OV = C_gas/ODT; Strongest Component Model; Carles pyramid timing; base/fixative lasting phase",
    },
    "mata_2005": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Mata, V. G.; Gomes, P. B.; Rodrigues, A. E.",
        "title": "Engineering perfumes",
        "source": "AIChE Journal 2005, 51(9):2565",
        "url": "https://doi.org/10.1002/aic.10530",
        "used_for": "Fixatives lower evaporative release into the headspace",
    },
    "teixeira_2009": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Teixeira, M. A.; Rodríguez, O.; Mata, V. G.; Rodrigues, A. E.",
        "title": "The diffusion of perfume mixtures and the odor performance",
        "source": "Chemical Engineering Science 2009, 64:2570",
        "url": "https://doi.org/10.1016/j.ces.2009.01.064",
        "used_for": "Evaporation/diffusion; base notes and fixatives shape lasting phase",
    },
    "teixeira_2013": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Teixeira, M. A.; Rodríguez, O.; Rodrigues, A. E.",
        "title": "Diffusion and performance of fragranced products: Prediction and validation",
        "source": "AIChE Journal 2013, 59(9):3350",
        "url": "https://doi.org/10.1002/aic.14106",
        "used_for": "Performance parameters (impact/tenacity/diffusion/volume)",
    },
    "laing_francis_1989": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Laing, D. G.; Francis, G. W.",
        "title": "The capacity of humans to identify odors in mixtures",
        "source": "Physiology & Behavior 1989, 46:809",
        "url": "https://doi.org/10.1016/0031-9384(89)90041-3",
        "used_for": "3-4 component identification limit for an identifiable subject",
    },
    "livermore_laing_1996": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Livermore, A.; Laing, D. G.",
        "title": "Influence of training and experience on the perception of multicomponent odor mixtures",
        "source": "J. Exp. Psychol. Hum. Percept. Perform. 1996, 22(2):267",
        "url": "https://pubmed.ncbi.nlm.nih.gov/8934843/",
        "used_for": "3-4 component identification limit, training independent",
    },
    "jinks_laing_1999": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Jinks, A.; Laing, D. G.",
        "title": "A limit in the processing of components in odour mixtures",
        "source": "Perception 1999, 28(3):395",
        "url": "https://doi.org/10.1068/p2898",
        "used_for": "Component identification ceiling",
    },
    "stevens_1957": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Stevens, S. S.",
        "title": "On the psychophysical law",
        "source": "Psychological Review 1957, 64(3):153",
        "url": "https://doi.org/10.1037/h0046162",
        "used_for": "Perceived intensity power law I = OV**n",
    },
    "cain_1969": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Cain, W. S.",
        "title": "Odor intensity: Differences in the exponent of the psychophysical function",
        "source": "Perception & Psychophysics 1969, 5(6):347",
        "url": "https://doi.org/10.3758/BF03212789",
        "used_for": "Family/material-dependent sub-unity intensity exponents",
    },
    "murphy_cain_1980": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Murphy, C.; Cain, W. S.",
        "title": "Taste and olfaction: independence vs interaction",
        "source": "Physiology & Behavior 1980, 24(3):493",
        "url": "https://doi.org/10.1016/0031-9384(80)90257-7",
        "used_for": "Harmony governs mixture additivity/interaction",
    },
    "vuilleumier_1995": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Vuilleumier, C.; Flament, I.; Sauvegrain, P.",
        "title": "Headspace analysis study of evaporation rate of perfume ingredients applied onto skin",
        "source": "International Journal of Cosmetic Science 1995, 17:61",
        "url": "https://doi.org/10.1111/j.1467-2494.1995.tb00110.x",
        "used_for": "Measured fixative effect of a musk on evaporation rate",
    },
    "santana_2021": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Santana, V. V.; Martins, M. A. F.; Loureiro, J. M.; et al.",
        "title": "Optimal fragrances formulation using a deep learning neural network architecture",
        "source": "Computers & Chemical Engineering 2021, 149:107282",
        "url": "https://doi.org/10.1016/j.compchemeng.2021.107282",
        "used_for": "Systematic computational formulation; functional balance as a design target",
    },
    "zhang_2021": {
        "tier": TIER_A_PEER_REVIEWED,
        "authors": "Zhang, X.; Zhou, T.; Ng, K. M.",
        "title": "Optimization-based cosmetic formulation",
        "source": "AIChE Journal 2021, 67:e17064",
        "url": "https://doi.org/10.1002/aic.17064",
        "used_for": "Optimization-based formulation with heuristics",
    },
    # --- Architecture: composition structure, olfactory form/Gestalt, mixtures ---
    "holley_2002": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Holley, A.",
        "title": "Cognitive aspects of olfaction in perfumer practice",
        "source": "In: Olfaction, Taste, and Cognition, Cambridge University Press, 2002, pp. 16-26",
        "url": "https://doi.org/10.1017/CBO9780511546389.005",
        "used_for": "Perfume composition as an 'olfactory form' (a Gestalt / complex perceptual structure)",
    },
    "thomas_danguin_2014": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Thomas-Danguin, T.; Sinding, C.; Romagny, S.; et al.",
        "title": "The perception of odor objects in everyday life: a review on the processing of odor mixtures",
        "source": "Frontiers in Psychology 2014, 5:504",
        "url": "https://doi.org/10.3389/fpsyg.2014.00504",
        "used_for": "Configurational processing: identity is a configuration, not a component list",
    },
    "weiss_2012": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Weiss, T.; Snitz, K.; Yablonka, A.; Khan, R. M.; et al.",
        "title": "Perceptual convergence of multi-component mixtures in olfaction implies an olfactory white",
        "source": "PNAS 2012, 109(49):19959",
        "url": "https://doi.org/10.1073/pnas.1208110109",
        "used_for": "Over-many balanced components converge to a generic percept (collapse risk)",
    },
    "snitz_2013": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Snitz, K.; Yablonka, A.; Weiss, T.; Frumin, I.; Khan, R. M.; Sobel, N.",
        "title": "Predicting odor perceptual similarity from odor structure",
        "source": "PLoS Computational Biology 2013, 9(9):e1003184",
        "url": "https://doi.org/10.1371/journal.pcbi.1003184",
        "used_for": "Perceptual similarity of mixtures from structure",
    },
    "jinks_laing_2001": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Jinks, A.; Laing, D. G.",
        "title": "The analysis of odor mixtures by humans: evidence for a configurational process",
        "source": "Physiology & Behavior 2001, 72(1-2):51",
        "url": "https://doi.org/10.1016/S0031-9384(00)00407-8",
        "used_for": "Mixtures are processed as configurations",
    },
    # --- Hedonism: odor pleasantness / hedonic valence ---
    "khan_2007": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Khan, R. M.; Luk, C.-H.; Flinker, A.; Aggarwal, A.; et al.",
        "title": "Predicting odor pleasantness from odorant structure: pleasantness as a reflection of the physical world",
        "source": "Journal of Neuroscience 2007, 27(37):10015",
        "url": "https://doi.org/10.1523/JNEUROSCI.1158-07.2007",
        "used_for": "Structure-based hedonic model (R^2 ~ 0.55); pleasantness is physicochemical",
    },
    "zarzo_2011": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Zarzo, M.",
        "title": "Hedonic judgments of chemical compounds are correlated with molecular size",
        "source": "Sensors 2011, 11(4):3667",
        "url": "https://doi.org/10.3390/s110403667",
        "used_for": "Molecular descriptors correlate with hedonic valence",
    },
    "arshamian_2022": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Arshamian, A.; et al.",
        "title": "The perception of odor pleasantness is shared across cultures",
        "source": "Current Biology 2022, 32(9):2061",
        "url": "https://doi.org/10.1016/j.cub.2022.02.062",
        "used_for": "Hedonic valence is largely shared (molecular identity 41%, culture ~6%)",
    },
    "bierling_2021": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Bierling, A. L.; Croy, I.; Hummel, T.; Cuniberti, G.; Croy, A.",
        "title": "Olfactory perception in relation to the physicochemical odor space",
        "source": "Brain Sciences 2021, 11(5):563",
        "url": "https://doi.org/10.3390/brainsci11050563",
        "used_for": "Hedonic valence is a primary dimension of the physicochemical odor space",
    },
    "joussain_2011": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Joussain, P.; Chakirian, A.; Kermen, F.; Rouby, C.; Bensafi, M.",
        "title": "Physicochemical influence on odor hedonics: Where does it occur first?",
        "source": "Communicative & Integrative Biology 2011, 4(5):563",
        "url": "https://doi.org/10.4161/cib.15811",
        "used_for": "Physicochemical determinants of odor hedonic valence",
    },
    "bontempi_2024": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Bontempi, C.; Brand, G.; Jacquot, L.",
        "title": "Variability in odor hedonic perception: A challenge for neurosensory and behavioral research",
        "source": "Behavioral Neuroscience 2024",
        "url": "https://doi.org/10.1037/bne0000587",
        "used_for": "Large individual variability: hedonic prediction is low-confidence",
    },
    # --- Theory: mixture interaction, suppression, harmony ---
    "lawless_1986": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Lawless, H. T.",
        "title": "Sensory interactions in mixtures",
        "source": "Journal of Sensory Studies 1986, 1(3-4):217",
        "url": "https://doi.org/10.1111/j.1745-459X.1986.tb00177.x",
        "used_for": "Mixture suppression predicts hedonic response",
    },
    "grabenhorst_2007": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Grabenhorst, F.; Rolls, E. T.; Margot, C.; et al.",
        "title": "How pleasant and unpleasant stimuli combine in different brain regions: odor mixtures",
        "source": "Journal of Neuroscience 2007, 27(49):13532",
        "url": "https://doi.org/10.1523/JNEUROSCI.2407-07.2007",
        "used_for": "Hedonic combination of mixture components",
    },
    "ma_2021": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Ma, Y.; Tang, K.; Xu, Y.; Thomas-Danguin, T.",
        "title": "Perceptual interactions among food odors: Major influences on odor intensity evidenced with a set of 222 binary mixtures of key odorants",
        "source": "Food Chemistry 2021, 359:129848",
        "url": "https://doi.org/10.1016/j.foodchem.2021.129848",
        "used_for": "Perceptual interaction (suppression) among odorants",
    },
    "yeshurun_sobel_2010": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Yeshurun, Y.; Sobel, N.",
        "title": "An odor is not worth a thousand words: from multidimensional odors to unidimensional odor objects",
        "source": "Annual Review of Psychology 2010, 61:219",
        "url": "https://doi.org/10.1146/annurev.psych.60.110707.163639",
        "used_for": "Valence and intensity are the primary perceptual dimensions",
    },
    "ferreira_2012": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Ferreira, V.",
        "title": "Revisiting psychophysical work on the quantitative and qualitative odour properties of simple odour mixtures",
        "source": "Flavour and Fragrance Journal 2012, 27(2):124",
        "url": "https://doi.org/10.1002/ffj.2090",
        "used_for": "Quantitative/qualitative odour properties of binary and ternary mixtures",
    },
    "prescott_2004": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Prescott, J.; Johnstone, V.; Francis, J.",
        "title": "Odor-taste interactions: effects of attentional strategies during exposure",
        "source": "Chemical Senses 2004, 29(4):331",
        "url": "https://doi.org/10.1093/chemse/bjh036",
        "used_for": "Cross-modal suppression and hedonic interaction",
    },
    "laing_eddy_best_1994": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "theory",
        "authors": "Laing, D. G.; Eddy, A.; Best, D. J.",
        "title": "Perceptual characteristics of binary, trinary, and quaternary odor mixtures consisting of unpleasant constituents",
        "source": "Physiology & Behavior 1994, 55(5):915",
        "url": "https://doi.org/10.1016/0031-9384(94)90264-X",
        "used_for": "Mixture suppression and hedonic characteristics scale with component count",
    },
    # --- Architecture (extended) ---
    "wilson_stevenson_2006": {
        "tier": TIER_B_CLASSICAL_TEXT,
        "domain": "architecture",
        "authors": "Wilson, D. A.; Stevenson, R. J.",
        "title": "Learning to Smell: Olfactory Perception from Neurobiology to Behavior",
        "source": "Johns Hopkins University Press, 2006",
        "url": "",
        "used_for": "Synthetic/configurational processing of odor objects and mixtures",
    },
    "keller_2016": {
        "tier": TIER_B_CLASSICAL_TEXT,
        "domain": "architecture",
        "authors": "Keller, A.",
        "title": "Philosophy of Olfactory Perception",
        "source": "Palgrave Macmillan, 2016",
        "url": "https://doi.org/10.1007/978-3-319-33645-9",
        "used_for": "Perceptual quality space; qualities of odor mixtures",
    },
    "young_2014": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Young, B. D.; Keller, A.; Rosenthal, D.",
        "title": "Quality-space theory in olfaction",
        "source": "Frontiers in Psychology 2014, 5:1",
        "url": "https://doi.org/10.3389/fpsyg.2014.00001",
        "used_for": "Quality-space account of odor mixture perception",
    },
    "shiner_2015": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "architecture",
        "authors": "Shiner, L.",
        "title": "Art scents: Perfume, design and olfactory art",
        "source": "The British Journal of Aesthetics 2015, 55(3):375",
        "url": "https://doi.org/10.1093/aesthj/ayv011",
        "used_for": "Perfume as composed form/design",
    },
    # --- Hedonism (extended) ---
    "spence_2022": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Spence, C.",
        "title": "Odour hedonics and the ubiquitous appeal of vanilla",
        "source": "Nature Food 2022, 3:832",
        "url": "https://doi.org/10.1038/s43016-022-00611-x",
        "used_for": "Molecular vs learned accounts of odor pleasantness",
    },
    "keller_vosshall_2016": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Keller, A.; Vosshall, L. B.",
        "title": "Olfactory perception of chemically diverse molecules",
        "source": "BMC Neuroscience 2016, 17:55",
        "url": "https://doi.org/10.1186/s12868-016-0287-2",
        "used_for": "Predicting pleasantness across chemically diverse molecules",
    },
    "chacko_2020": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Chacko, R.; Jain, D.; Patwardhan, M.; Puri, A.; Karande, S.; et al.",
        "title": "Data based predictive models for odor perception",
        "source": "Scientific Reports 2020, 10:17136",
        "url": "https://doi.org/10.1038/s41598-020-73978-1",
        "used_for": "Predictive hedonic/pleasantness models from molecular data",
    },
    "haddad_2010": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "hedonism",
        "authors": "Haddad, R.; Medhanie, A.; Roth, Y.; Harel, D.; Sobel, N.",
        "title": "Predicting odor pleasantness with an electronic nose",
        "source": "PLoS Computational Biology 2010, 6(4):e1000740",
        "url": "https://doi.org/10.1371/journal.pcbi.1000740",
        "used_for": "Physicochemical signal predicts pleasantness",
    },
    # --- Neuroscience: intensity/valence coding, integration, adaptation ---
    "anderson_2003": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Anderson, A. K.; Christoff, K.; Stappen, I.; Panitz, D.; et al.",
        "title": "Dissociated neural representations of intensity and valence in human olfaction",
        "source": "Nature Neuroscience 2003, 6(2):196",
        "url": "https://doi.org/10.1038/nn1001",
        "used_for": "Amygdala codes intensity, OFC codes valence; the two are dissociable",
    },
    "winston_2005": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Winston, J. S.; Gottfried, J. A.; Kilner, J. M.; Dolan, R. J.",
        "title": "Integrated neural representations of odor intensity and affective valence in human amygdala",
        "source": "Journal of Neuroscience 2005, 25(39):8903",
        "url": "https://doi.org/10.1523/JNEUROSCI.1569-05.2005",
        "used_for": "Intensity x valence interaction: intensity is not hedonically neutral",
    },
    "rolls_2010": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Rolls, E. T.; Grabenhorst, F.; Parris, B. A.",
        "title": "Neural systems underlying decisions about affective odors",
        "source": "Journal of Cognitive Neuroscience 2010, 22(5):1069",
        "url": "https://doi.org/10.1162/jocn.2009.21235",
        "used_for": "Medial PFC/OFC integrate pleasantness vs intensity; decision load rises with channels",
    },
    "grabenhorst_rolls_2011": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Grabenhorst, F.; Rolls, E. T.",
        "title": "Value, pleasure and choice in the ventral prefrontal cortex",
        "source": "Trends in Cognitive Sciences 2011, 15(2):56",
        "url": "https://doi.org/10.1016/j.tics.2010.12.004",
        "used_for": "Ventral PFC represents subjective value/pleasantness; integration capacity",
    },
    "pellegrino_2017": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Pellegrino, R.; Sinding, C.; de Wijk, R. A.; Hummel, T.",
        "title": "Habituation and adaptation to odors in humans",
        "source": "Physiology & Behavior 2017, 177:13",
        "url": "https://doi.org/10.1016/j.physbeh.2017.04.006",
        "used_for": "Perceived intensity decrements with continued exposure (receptor/label specific)",
    },
    "sinding_2017": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Sinding, C.; Valadier, F.; Al-Hassani, V.; Feron, G.; et al.",
        "title": "New determinants of olfactory habituation",
        "source": "Scientific Reports 2017, 7:41047",
        "url": "https://doi.org/10.1038/srep41047",
        "used_for": "Habituation depends on odorant properties/label; single-note tops fatigue fastest",
    },
    "dalton_wysocki_1996": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Dalton, P.; Wysocki, C. J.",
        "title": "The nature and duration of adaptation following long-term odor exposure",
        "source": "Perception & Psychophysics 1996, 58(5):781",
        "url": "https://doi.org/10.3758/BF03213109",
        "used_for": "Adaptation develops and recovers on a usable time course",
    },
    "ferdenzi_2014": {
        "tier": TIER_A_PEER_REVIEWED,
        "domain": "neuroscience",
        "authors": "Ferdenzi, C.; Poncelet, J.; Rouby, C.; Bensafi, M.",
        "title": "Repeated exposure to odors induces affective habituation of perception and sniffing",
        "source": "Frontiers in Behavioral Neuroscience 2014, 8:119",
        "url": "https://doi.org/10.3389/fnbeh.2014.00119",
        "used_for": "Affective habituation: pleasantness also declines with repeated exposure",
    },
}


# Which evidence domain each citation supports. Keeps one flat registry while
# still letting the model expose a hedonism/architecture/theory reading list.
_CITATION_DOMAIN: dict[str, str] = {
    "dowthwaite_1999": "function",
    "dowthwaite_2004": "function",
    "carles_1961": "function",
    "rodrigues_2021": "function",
    "mata_2005": "function",
    "teixeira_2009": "function",
    "teixeira_2013": "function",
    "laing_francis_1989": "function",
    "livermore_laing_1996": "function",
    "jinks_laing_1999": "function",
    "stevens_1957": "theory",
    "cain_1969": "theory",
    "murphy_cain_1980": "theory",
    "vuilleumier_1995": "function",
    "santana_2021": "function",
    "zhang_2021": "function",
    "holley_2002": "architecture",
    "thomas_danguin_2014": "architecture",
    "weiss_2012": "architecture",
    "snitz_2013": "architecture",
    "jinks_laing_2001": "architecture",
    "khan_2007": "hedonism",
    "zarzo_2011": "hedonism",
    "arshamian_2022": "hedonism",
    "bierling_2021": "hedonism",
    "joussain_2011": "hedonism",
    "bontempi_2024": "hedonism",
    "lawless_1986": "theory",
    "grabenhorst_2007": "theory",
    "ma_2021": "theory",
    "yeshurun_sobel_2010": "theory",
    "ferreira_2012": "theory",
    "prescott_2004": "theory",
    "laing_eddy_best_1994": "theory",
    "wilson_stevenson_2006": "architecture",
    "keller_2016": "architecture",
    "young_2014": "architecture",
    "shiner_2015": "architecture",
    "spence_2022": "hedonism",
    "keller_vosshall_2016": "hedonism",
    "chacko_2020": "hedonism",
    "haddad_2010": "hedonism",
    "anderson_2003": "neuroscience",
    "winston_2005": "neuroscience",
    "rolls_2010": "neuroscience",
    "grabenhorst_rolls_2011": "neuroscience",
    "pellegrino_2017": "neuroscience",
    "sinding_2017": "neuroscience",
    "dalton_wysocki_1996": "neuroscience",
    "ferdenzi_2014": "neuroscience",
}

EVIDENCE_DOMAINS: tuple[str, ...] = (
    "function", "architecture", "hedonism", "theory", "neuroscience",
)


def get_citations_for_domain(domain: str) -> dict[str, dict[str, str]]:
    return {
        key: {**value, "domain": _CITATION_DOMAIN.get(key, "function")}
        for key, value in FUNCTIONAL_BALANCE_CITATIONS.items()
        if _CITATION_DOMAIN.get(key, "function") == domain
    }


@dataclass(frozen=True, slots=True)
class FunctionRoleEvidence:
    role: str
    definition: str
    numeric_criteria: tuple[str, ...]
    citations: tuple[str, ...]


# The five functions with their doctrine and the exact criteria the model uses.
FUNCTION_ROLE_EVIDENCE: tuple[FunctionRoleEvidence, ...] = (
    FunctionRoleEvidence(
        role=HEART,
        definition=(
            "The essential/subject smell of the fragrance that carries the identity "
            "(Dowthwaite 1999; Carles 1961). Identified by the Strongest Component "
            "Model as the dominant odor value family (Rodrigues 2021)."
        ),
        numeric_criteria=(
            "contains the material with max OV (Rodrigues 2021 eq. 3)",
            f"identifiable heart components <= {HEART_COMPONENT_LIMIT} (Laing et al.)",
        ),
        citations=("dowthwaite_1999", "carles_1961", "rodrigues_2021", "laing_francis_1989",
                   "livermore_laing_1996", "jinks_laing_1999"),
    ),
    FunctionRoleEvidence(
        role=MODIFIER,
        definition=(
            "Decoration: adds style, naturalness, freshness or diffusion. If "
            "overdosed it becomes the subject/heart (Dowthwaite 1999)."
        ),
        numeric_criteria=(
            f"trace/decorative dose <= {MODIFIER_TRACE_MAX_PCT:.1f}% active mass",
            f"high relative impact >= {X_FACTOR_MIN_IMPACT:.0f} (vs Linalool=100)",
        ),
        citations=("dowthwaite_1999", "stevens_1957", "cain_1969"),
    ),
    FunctionRoleEvidence(
        role=BLENDER,
        definition=(
            "Bridges, rounds and harmonizes different heart and modifier notes "
            "(Dowthwaite 1999). Blenders must not dominate the headspace."
        ),
        numeric_criteria=(
            f"relative impact <= {BLENDER_IMPACT_MAX:.0f} (Linalool reference = 100)",
            "does not hold the max OV (SCM, Rodrigues 2021)",
        ),
        citations=("dowthwaite_1999", "murphy_cain_1980", "rodrigues_2021"),
    ),
    FunctionRoleEvidence(
        role=FIXATIVE,
        definition=(
            "Gives completion, depth and background; supports the structure and "
            "lowers evaporative release (Dowthwaite 1999; Mata 2005)."
        ),
        numeric_criteria=(
            f"odour life >= {FIXATIVE_ODOUR_LIFE_MIN_HRS:.0f} h on strip",
            f"vapour pressure <= {FIXATIVE_VP_MAX_PA:.2f} Pa (base tier)",
        ),
        citations=("dowthwaite_1999", "mata_2005", "teixeira_2009", "teixeira_2013",
                   "vuilleumier_1995", "rodrigues_2021"),
    ),
    FunctionRoleEvidence(
        role=X_FACTOR,
        definition=(
            "A special class of modifier: the hook / 'je ne sais quoi' that catches "
            "attention (Dowthwaite 1999)."
        ),
        numeric_criteria=(
            f"trace dose <= {X_FACTOR_MAX_PCT:.1f}% active mass",
            f"relative impact >= {X_FACTOR_MIN_IMPACT:.0f}",
        ),
        citations=("dowthwaite_1999",),
    ),
)


def get_function_role_evidence(role: str | None = None) -> tuple[FunctionRoleEvidence, ...]:
    if role is None:
        return FUNCTION_ROLE_EVIDENCE
    return tuple(e for e in FUNCTION_ROLE_EVIDENCE if e.role == role)


def get_functional_balance_citations() -> dict[str, dict[str, str]]:
    return {k: dict(v) for k, v in FUNCTIONAL_BALANCE_CITATIONS.items()}


# ---------------------------------------------------------------------------
# Declared-role -> function mapping (from ingredient_intelligence profiles)
# ---------------------------------------------------------------------------

_DECLARED_ROLE_TO_FUNCTION: dict[str, str] = {
    "character": HEART,
    "heart": HEART,
    "core": HEART,
    "base": HEART,
    "modifier": MODIFIER,
    "trace": MODIFIER,
    "top": MODIFIER,
    "bridge": BLENDER,
    "fixative": FIXATIVE,
    "volume": FIXATIVE,
    "stabilizer": FIXATIVE,
    "radiance": FIXATIVE,
    "solvent": "",
}

# Documented function assignments (Dowthwaite function layer + master organ
# guide). These are practitioner evidence class, not measured truth; they only
# seed the provisional role which contextual rules may still override.
_CURATED_FUNCTION: dict[str, str] = {
    # Blenders (bridge/round/transparent)
    "hedione": BLENDER,
    "iso e super": BLENDER,
    "linalool": BLENDER,
    "dihydromyrcenol": BLENDER,
    "linalyl acetate": BLENDER,
    "helional": BLENDER,
    "florol": BLENDER,
    "vertsol": BLENDER,
    # Heart / character
    "alpha isomethyl ionone": HEART,
    "methyl ionone": HEART,
    "alpha-ionone": HEART,
    "ionone beta": HEART,
    "hydroxycitronellal": HEART,
    "cyclamen aldehyde": HEART,
    "phenethyl alcohol": HEART,
    "phenyl ethyl acetate": HEART,
    "benzyl salicylate": HEART,
    "cetone v": HEART,
    # Modifiers / accents that are documented as functional modifiers
    "undecavertol": MODIFIER,
    "cashmeran": MODIFIER,
    "suederal": MODIFIER,
    # Fixatives / foundation
    "galaxolide": FIXATIVE,
    "habanolide": FIXATIVE,
    "ethylene brassylate": FIXATIVE,
    "ambroxan": FIXATIVE,
    "ambrox super": FIXATIVE,
    "ambrofix": FIXATIVE,
    "patchouli light": FIXATIVE,
    "vertofix coeur": FIXATIVE,
    "bacdanol": FIXATIVE,
    "ebanol": FIXATIVE,
    "evernyl": FIXATIVE,
    "coumarin": FIXATIVE,
    "vanillin": FIXATIVE,
}

# Distinctive "hook" accents. Only reads as an X-Factor at trace dose.
_CURATED_X_FACTOR: frozenset[str] = frozenset({
    "birch tar", "isobutyl quinoline", "ethyl maltol", "safranal", "saffron",
    "calone", "geosmin", "rose oxide", "triplal", "aldehyde c-10",
    "aldehyde c-11", "aldehyde c-12 mna", "scentenal", "orivone", "indole",
    "castoreum", "cis-3-hexenol",
})


# ---------------------------------------------------------------------------
# PerfumersWorld supplier data (relative impact / odour life on strip)
# ---------------------------------------------------------------------------

_PW_DATA_FILENAME = "pw_material_data_merged.json"


def _repo_root() -> Path:
    # engine/knowledge/performance_engineering.py -> repo root
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=4)
def load_pw_material_data(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load PerfumersWorld per-material fields keyed by lower-case name.

    Returns ``{}`` when the intake file is absent (fail-open knowledge surface).
    """
    target = Path(path) if path else _repo_root() / "data" / "knowledge_graph" / _PW_DATA_FILENAME
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records = payload.get("materials", payload if isinstance(payload, list) else [])
    out: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("inventory_name") or record.get("pw_name") or "").strip().lower()
        if not name:
            continue
        fields = record.get("fields") or {}
        out[name] = {
            "relative_impact": _to_float(fields.get("relative_impact")),
            "odour_life_hrs": _to_float(fields.get("odour_life_hrs")),
            "pw_class": fields.get("notes_pyramid_raw"),
            "cas": fields.get("cas"),
            "evidence_class": record.get("evidence_class", "SUPPLIER_TECHNICAL"),
        }
    return out


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pw_for(name: str, pw_data: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    key = name.strip().lower()
    data = pw_data.get(key)
    if data is not None:
        return data
    # Trim trailing dilution descriptors, e.g. "Galaxolide 50%".
    for suffix in (" 100%", " 50%", " 30%", " 20%", " 10%", " 5%", " 1%"):
        if key.endswith(suffix):
            found = pw_data.get(key[: -len(suffix)].strip())
            if found is not None:
                return found
    return {}


# ---------------------------------------------------------------------------
# Material hedonic valence (structure-linked pleasantness priors)
# ---------------------------------------------------------------------------

_MP_DATA_FILENAME = "material_properties.json"


@lru_cache(maxsize=4)
def load_hedonic_valence(path: str | None = None) -> dict[str, float]:
    """Load per-material hedonic valence keyed by lower-case name.

    Source: ``data/knowledge_graph/material_properties.json`` (structure-linked
    pleasantness priors; see Khan 2007, Zarzo 2011). Values are only used as a
    *relative* composition prior, never as measured pleasantness.
    """
    target = Path(path) if path else _repo_root() / "data" / "knowledge_graph" / _MP_DATA_FILENAME
    if not target.exists():
        return {}
    try:
        records = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, float] = {}
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        name = str(record.get("name") or "").strip().lower()
        value = _to_float(record.get("hedonic"))
        if name and value is not None:
            out[name] = value
    return out


def _hedonic_for(name: str, table: Mapping[str, float]) -> float | None:
    key = name.strip().lower()
    if key in table:
        return table[key]
    for suffix in (" 100%", " 50%", " 30%", " 20%", " 10%", " 5%", " 1%"):
        if key.endswith(suffix):
            found = table.get(key[: -len(suffix)].strip())
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# Architecture + hedonism assessments
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ArchitectureAssessment:
    status: str
    tier_coverage: dict[str, int]
    volatility_windows: dict[str, float]
    empty_windows: tuple[str, ...]
    ov_dominance: float
    collapse_risk: bool
    findings: tuple[str, ...]
    citations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tier_coverage": dict(self.tier_coverage),
            "volatility_windows": {k: round(v, 2) for k, v in self.volatility_windows.items()},
            "empty_windows": list(self.empty_windows),
            "ov_dominance": round(self.ov_dominance, 4),
            "collapse_risk": self.collapse_risk,
            "findings": list(self.findings),
            "citations": list(self.citations),
        }


@dataclass(frozen=True, slots=True)
class NeuroscienceAssessment:
    status: str
    perceptible_channels: int
    integration_limit: int
    habituation_risk: bool
    findings: tuple[str, ...]
    citations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "perceptible_channels": self.perceptible_channels,
            "integration_limit": self.integration_limit,
            "habituation_risk": self.habituation_risk,
            "findings": list(self.findings),
            "citations": list(self.citations),
        }


@dataclass(frozen=True, slots=True)
class HedonicAssessment:
    status: str
    coverage_pct: float
    weighted_valence: float | None
    confidence: str
    findings: tuple[str, ...]
    citations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "coverage_pct": round(self.coverage_pct, 2),
            "weighted_valence": (
                None if self.weighted_valence is None else round(self.weighted_valence, 4)
            ),
            "confidence": self.confidence,
            "findings": list(self.findings),
            "citations": list(self.citations),
        }


def evaluate_architecture(
    odorant: Sequence[Any],
    *,
    max_oav: float,
    tone_floor: float = 0.2,
) -> ArchitectureAssessment:
    """Composition architecture: Carles pyramid coverage + olfactory-form integrity.

    Grounded in Carles 1961 and Rodrigues 2021 (pyramid/timing), Holley 2002 and
    Thomas-Danguin 2014 (composition as a configurational 'olfactory form'),
    Jinks & Laing 2001 (configurational processing), and Weiss 2012 (perceptual
    convergence to an 'olfactory white' when many balanced components are mixed).
    """
    findings: list[str] = []
    tiers = {"top": 0, "heart": 0, "base": 0}
    for m in odorant:
        note = str(_field(m, "note", "") or "").lower()
        if note in tiers:
            tiers[note] += 1

    if not tiers["heart"]:
        findings.append(
            "No heart-tier material: the pyramid lacks its character body "
            "(Carles 1961; Rodrigues 2021)."
        )
    if not tiers["base"]:
        findings.append(
            "No base-tier material: the pyramid lacks a lasting phase "
            "(Carles 1961; Rodrigues 2021)."
        )
    if not tiers["top"]:
        findings.append(
            "No top-tier material: the pyramid lacks an opening (Carles 1961)."
        )

    # Olfactory-white collapse: many components, none dominant -> generic percept.
    total_oav = sum((_to_float(_field(m, "oav")) or 0.0) for m in odorant)
    dominance = (max_oav / total_oav) if total_oav > 0 else 0.0
    n_perceptible = sum(
        1 for m in odorant if (_to_float(_field(m, "oav")) or 0.0) >= PERCEPTIBILITY_OAV_FLOOR
    )
    collapse_risk = n_perceptible >= 6 and dominance < tone_floor
    if collapse_risk:
        findings.append(
            f"{n_perceptible} perceptible components with max OV share {dominance:.0%}: "
            "risk of perceptual convergence to a generic percept (Weiss 2012; "
            "Thomas-Danguin 2014)."
        )

    # Carles volatility windows: the release architecture must populate every
    # evaporation window, or the composition has a temporal hole (Carles 1961;
    # Rodrigues 2021; Teixeira 2009/2013).
    windows = {"1h_top": 0.0, "3h_top_heart": 0.0, "6h_heart": 0.0,
               "12h_heart_base": 0.0, "24h_base": 0.0}
    total_share = 0.0
    for m in odorant:
        share = _to_float(_field(m, "active_g")) or 0.0
        if share <= 0:
            share = _to_float(_field(m, "active_ul")) or 0.0
        total_share += share
    if total_share > 0:
        for m in odorant:
            vp = _to_float(_field(m, "vp_pure_pa")) or 0.0
            share = (_to_float(_field(m, "active_g")) or 0.0) or (
                _to_float(_field(m, "active_ul")) or 0.0
            )
            pct = 100.0 * share / total_share
            if vp > 2.0:
                windows["1h_top"] += pct
            elif vp > 0.5:
                windows["3h_top_heart"] += pct
            elif vp > 0.1:
                windows["6h_heart"] += pct
            elif vp > 0.02:
                windows["12h_heart_base"] += pct
            else:
                windows["24h_base"] += pct
    empty_windows = tuple(k for k, v in windows.items() if v < 2.0)
    if empty_windows and total_share > 0:
        findings.append(
            "Under-populated Carles volatility windows (<2% active): "
            f"{', '.join(empty_windows)} (Carles 1961; Rodrigues 2021)."
        )

    status = "WARN" if (collapse_risk or empty_windows) else "PASS"
    return ArchitectureAssessment(
        status=status,
        tier_coverage=tiers,
        volatility_windows=windows,
        empty_windows=empty_windows,
        ov_dominance=dominance,
        collapse_risk=collapse_risk,
        findings=tuple(findings),
        citations=("carles_1961", "rodrigues_2021", "holley_2002",
                   "thomas_danguin_2014", "jinks_laing_2001", "weiss_2012",
                   "teixeira_2009", "teixeira_2013"),
    )


# Integration-capacity limit and intensity threshold carried from the pipeline
# neuroscience advisory (engine/pipeline/neuroscience.py).
INTEGRATION_CHANNEL_LIMIT = 5
INTEGRATION_CHANNEL_OAV = 10.0
HABITUATION_TOP_DOMINANCE = 0.6


def evaluate_neuroscience(
    odorant: Sequence[Any],
    *,
    channel_oav: float = INTEGRATION_CHANNEL_OAV,
    channel_limit: int = INTEGRATION_CHANNEL_LIMIT,
    top_dominance_floor: float = HABITUATION_TOP_DOMINANCE,
) -> NeuroscienceAssessment:
    """Cognitive integration + adaptation risk for the mixture.

    Channels: the pipeline already warns when more than ~5 materials are
    simultaneously perceptible (vmPFC/OFC integration capacity); this is grounded
    in Anderson 2003, Winston 2005, Rolls 2010 and Grabenhorst & Rolls 2011.

    Habituation: receptor/label-specific adaptation means a top dominated by a
    single material fatigues fastest (Pellegrino 2017; Sinding 2017; Dalton &
    Wysocki 1996; Ferdenzi 2014).
    """
    findings: list[str] = []

    perceptible = [
        m for m in odorant if (_to_float(_field(m, "oav")) or 0.0) >= channel_oav
    ]
    if len(perceptible) > channel_limit:
        findings.append(
            f"{len(perceptible)} materials with OV >= {channel_oav:.0f} exceed the "
            f"~{channel_limit}-channel integration capacity (Anderson 2003; "
            "Rolls 2010; Grabenhorst & Rolls 2011)."
        )

    # Top-note dominance: single material share of the highest-volatility OV pool.
    top_ov: dict[str, float] = {}
    for m in odorant:
        vp = _to_float(_field(m, "vp_pure_pa")) or 0.0
        if vp <= 2.0:
            continue
        top_ov[_material_name(m)] = (_to_float(_field(m, "oav")) or 0.0)
    habituation_risk = False
    if top_ov:
        total_top = sum(top_ov.values())
        if total_top > 0:
            leader, leader_ov = max(top_ov.items(), key=lambda kv: kv[1])
            if leader_ov / total_top >= top_dominance_floor:
                habituation_risk = True
                findings.append(
                    f"Top-note OV dominated by {leader} "
                    f"({leader_ov / total_top:.0%}); single-material tops habituale "
                    "fastest (Pellegrino 2017; Sinding 2017; Dalton & Wysocki 1996)."
                )

    return NeuroscienceAssessment(
        status="WARN" if findings else "PASS",
        perceptible_channels=len(perceptible),
        integration_limit=channel_limit,
        habituation_risk=habituation_risk,
        findings=tuple(findings),
        citations=("anderson_2003", "winston_2005", "rolls_2010",
                   "grabenhorst_rolls_2011", "pellegrino_2017", "sinding_2017",
                   "dalton_wysocki_1996", "ferdenzi_2014"),
    )


def evaluate_hedonics(
    odorant: Sequence[Any],
    *,
    hedonic_table: Mapping[str, float] | None = None,
    coverage_floor: float = 0.5,
) -> HedonicAssessment:
    """OV-weighted hedonic-valence prior for the composition.

    Pleasantness is structure-linked and largely shared (Khan 2007; Zarzo 2011;
    Bierling 2021; Arshamian 2022) but individual variation is large (Bontempi
    2024), so the result is explicitly a low-confidence prior, never a measured
    sensory claim. The composition is compared to the loaded valence distribution
    rather than an invented absolute threshold.
    """
    table = hedonic_table if hedonic_table is not None else load_hedonic_valence()
    if not table:
        return HedonicAssessment(
            status="ABSTAIN", coverage_pct=0.0, weighted_valence=None, confidence="none",
            findings=("No hedonic valence data available; hedonic prior withheld.",),
            citations=("khan_2007", "zarzo_2011", "arshamian_2022", "bontempi_2024"),
        )

    weights: list[float] = []
    values: list[float] = []
    covered = 0.0
    total = 0.0
    for m in odorant:
        weight = _to_float(_field(m, "oav")) or 0.0
        total += weight
        value = _hedonic_for(_material_name(m), table)
        if value is None:
            continue
        covered += weight
        weights.append(weight)
        values.append(value)

    coverage = (covered / total) if total > 0 else 0.0
    if coverage < coverage_floor or not values:
        weighted = (
            sum(w * v for w, v in zip(weights, values)) / sum(weights)
            if weights and sum(weights) > 0 else None
        )
        return HedonicAssessment(
            status="ABSTAIN", coverage_pct=100.0 * coverage, weighted_valence=weighted,
            confidence="low",
            findings=(
                f"Hedonic coverage {coverage:.0%} < {coverage_floor:.0%} of OV weight; "
                "hedonic prior withheld.",
            ),
            citations=("khan_2007", "zarzo_2011", "arshamian_2022", "bontempi_2024"),
        )

    weighted = sum(w * v for w, v in zip(weights, values)) / sum(weights)
    ordered = sorted(table.values())
    q1 = ordered[len(ordered) // 4]
    findings: list[str] = []
    if weighted <= q1:
        findings.append(
            f"OV-weighted hedonic prior {weighted:.2f} is in the bottom quartile "
            f"(<= {q1:.2f}) of the loaded valence distribution; composition leans on "
            "low-valence materials (Khan 2007; Zarzo 2011)."
        )
    status = "WARN" if findings else "PASS"
    return HedonicAssessment(
        status=status,
        coverage_pct=100.0 * coverage,
        weighted_valence=weighted,
        confidence="low",
        findings=tuple(findings),
        citations=("khan_2007", "zarzo_2011", "bierling_2021", "arshamian_2022",
                   "bontempi_2024", "spence_2022"),
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FunctionAssignment:
    name: str
    role: str
    source: str
    reason: str
    declared_role: str = ""
    active_share_pct: float = 0.0
    oav: float | None = None
    relative_impact: float | None = None
    odour_life_hrs: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "source": self.source,
            "reason": self.reason,
            "declared_role": self.declared_role,
            "active_share_pct": round(self.active_share_pct, 4),
            "oav": None if self.oav is None else round(self.oav, 6),
            "relative_impact": self.relative_impact,
            "odour_life_hrs": self.odour_life_hrs,
        }


def _field(material: Any, name: str, default: Any = None) -> Any:
    return getattr(material, name, default)


def _material_name(material: Any) -> str:
    return str(_field(material, "canonical_name") or _field(material, "name") or "")


def _curated_lookup(key: str, table: Mapping[str, Any] | frozenset[str]) -> Any:
    """Exact match, else word-boundary prefix match (e.g. 'Birch Tar Rectified')."""
    if key in table:
        return table[key] if isinstance(table, Mapping) else True
    for candidate in table:
        if key.startswith(candidate + " ") or key.startswith(candidate + ","):
            return table[candidate] if isinstance(table, Mapping) else True
    return None


def _active_share(material: Any, total_active_g: float) -> float:
    grams = _to_float(_field(material, "active_g"))
    if grams is None:
        ul = _to_float(_field(material, "active_ul"))
        grams = ul if ul is not None else 0.0
    if total_active_g <= 0:
        return 0.0
    return 100.0 * grams / total_active_g


def _is_ov_dominant(material: Any, max_oav: float) -> bool:
    value = _to_float(_field(material, "oav"))
    return value is not None and max_oav > 0 and value >= max_oav - 1e-9


def _provisional_assignment(
    material: Any,
    *,
    declared_role: str,
    active_share_pct: float,
    oav_value: float | None,
    pw: Mapping[str, Any],
    max_oav: float,
    overrides: Mapping[str, str],
) -> FunctionAssignment:
    name = _material_name(material)
    key = name.strip().lower()
    impact = _to_float(pw.get("relative_impact"))
    life = _to_float(pw.get("odour_life_hrs"))
    vp = _to_float(_field(material, "vp_pure_pa"))

    # 1. Explicit caller override.
    if key in overrides:
        return FunctionAssignment(
            name=name, role=overrides[key], source="override",
            reason="caller override", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )

    # 2. X-Factor: a distinctive hook only at trace dose (Dowthwaite 1999).
    if _curated_lookup(key, _CURATED_X_FACTOR) and active_share_pct <= X_FACTOR_MAX_PCT:
        return FunctionAssignment(
            name=name, role=X_FACTOR, source="curated:dowthwaite_1999",
            reason="documented signature accent at trace dose", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )

    # 3. Curated function doctrine (Dowthwaite function layer / master organ).
    curated_role = _curated_lookup(key, _CURATED_FUNCTION)
    if curated_role is not None:
        return FunctionAssignment(
            name=name, role=curated_role, source="curated:function_layer",
            reason="documented function assignment", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )

    # 4. Contextual physical rules.
    # Fixative: persists on the strip / low volatility and is not the subject.
    if declared_role in ("fixative", "volume", "stabilizer", "radiance"):
        return FunctionAssignment(
            name=name, role=FIXATIVE, source="declared+physical",
            reason="declared foundation/fixative function", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )
    if declared_role not in ("character", "heart", "core", "base"):
        if life is not None and life >= FIXATIVE_ODOUR_LIFE_MIN_HRS:
            return FunctionAssignment(
                name=name, role=FIXATIVE, source="physical:odour_life",
                reason=f"odour life {life:.1f} h >= {FIXATIVE_ODOUR_LIFE_MIN_HRS:.0f} h",
                declared_role=declared_role, active_share_pct=active_share_pct,
                oav=oav_value, relative_impact=impact, odour_life_hrs=life,
            )
        if vp is not None and 0.0 < vp <= FIXATIVE_VP_MAX_PA:
            return FunctionAssignment(
                name=name, role=FIXATIVE, source="physical:vapour_pressure",
                reason=f"VP {vp:.3f} Pa <= {FIXATIVE_VP_MAX_PA:.2f} Pa", declared_role=declared_role,
                active_share_pct=active_share_pct, oav=oav_value,
                relative_impact=impact, odour_life_hrs=life,
            )

    # Blender: low relative impact and not the strongest odor.
    if declared_role == "bridge":
        return FunctionAssignment(
            name=name, role=BLENDER, source="declared", reason="declared bridge",
            declared_role=declared_role, active_share_pct=active_share_pct,
            oav=oav_value, relative_impact=impact, odour_life_hrs=life,
        )
    if (impact is not None and impact <= BLENDER_IMPACT_MAX
            and not _is_ov_dominant(material, max_oav)):
        return FunctionAssignment(
            name=name, role=BLENDER, source="physical:relative_impact",
            reason=f"impact {impact:.0f} <= {BLENDER_IMPACT_MAX:.0f} (Linalool reference)",
            declared_role=declared_role, active_share_pct=active_share_pct,
            oav=oav_value, relative_impact=impact, odour_life_hrs=life,
        )

    # Modifier: declared decoration, or a high-impact trace.
    if declared_role in ("modifier", "trace", "top"):
        return FunctionAssignment(
            name=name, role=MODIFIER, source="declared", reason="declared modifier/trace",
            declared_role=declared_role, active_share_pct=active_share_pct,
            oav=oav_value, relative_impact=impact, odour_life_hrs=life,
        )
    if (impact is not None and impact >= X_FACTOR_MIN_IMPACT
            and active_share_pct <= MODIFIER_TRACE_MAX_PCT):
        return FunctionAssignment(
            name=name, role=MODIFIER, source="physical:impact_trace",
            reason=f"impact {impact:.0f} at {active_share_pct:.1f}%", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )

    # Heart: declared character, the OV-dominant material, or mass-dominant.
    if declared_role in ("character", "heart", "core", "base") or _is_ov_dominant(material, max_oav):
        return FunctionAssignment(
            name=name, role=HEART, source="contextual",
            reason="declared character or dominant odor value", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )
    if active_share_pct >= 20.0:
        return FunctionAssignment(
            name=name, role=HEART, source="contextual:mass",
            reason=f"mass-dominant at {active_share_pct:.1f}%", declared_role=declared_role,
            active_share_pct=active_share_pct, oav=oav_value,
            relative_impact=impact, odour_life_hrs=life,
        )

    return FunctionAssignment(
        name=name, role=MODIFIER, source="fallback",
        reason="no strong contextual signal; treated as modifier", declared_role=declared_role,
        active_share_pct=active_share_pct, oav=oav_value,
        relative_impact=impact, odour_life_hrs=life,
    )


def _apply_context(
    assignment: FunctionAssignment,
    *,
    heart_share_pct: float,
) -> tuple[FunctionAssignment, str | None]:
    """Second pass: contextual reclassification.

    Dowthwaite 1999: a modifier that is overdosed becomes the subject/heart.
    """
    if assignment.role == MODIFIER and assignment.active_share_pct >= heart_share_pct > 0.0:
        moved = FunctionAssignment(
            name=assignment.name, role=HEART, source="contextual:modifier_overdose",
            reason=(
                f"modifier at {assignment.active_share_pct:.1f}% >= heart share "
                f"{heart_share_pct:.1f}% (overdosed -> becomes subject)"
            ),
            declared_role=assignment.declared_role,
            active_share_pct=assignment.active_share_pct, oav=assignment.oav,
            relative_impact=assignment.relative_impact, odour_life_hrs=assignment.odour_life_hrs,
        )
        return moved, moved.reason
    return assignment, None


# ---------------------------------------------------------------------------
# Balance evaluation
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FunctionBalanceReport:
    status: str
    detail: str
    assignments: tuple[FunctionAssignment, ...]
    role_mass_share: dict[str, float]
    role_oav_share: dict[str, float]
    role_counts: dict[str, int]
    present: dict[str, bool]
    heart_components: tuple[str, ...]
    findings: tuple[str, ...]
    architecture: ArchitectureAssessment
    hedonics: HedonicAssessment
    neuroscience: NeuroscienceAssessment
    evidence: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FUNCTION_BALANCE_SCHEMA_VERSION,
            "status": self.status,
            "detail": self.detail,
            "assignments": [a.as_dict() for a in self.assignments],
            "role_mass_share": {k: round(v, 3) for k, v in self.role_mass_share.items()},
            "role_oav_share": {k: round(v, 3) for k, v in self.role_oav_share.items()},
            "role_counts": dict(self.role_counts),
            "present": dict(self.present),
            "heart_components": list(self.heart_components),
            "findings": list(self.findings),
            "architecture": self.architecture.as_dict(),
            "hedonics": self.hedonics.as_dict(),
            "neuroscience": self.neuroscience.as_dict(),
            "evidence": self.evidence,
        }


def evaluate_function_balance(
    materials: Sequence[Any],
    *,
    pw_data: Mapping[str, dict[str, Any]] | None = None,
    hedonic_table: Mapping[str, float] | None = None,
    overrides: Mapping[str, str] | None = None,
) -> FunctionBalanceReport:
    """Classify materials into Heart/Modifier/Blender/Fixative/X-Factor and score balance."""
    pw = pw_data if pw_data is not None else load_pw_material_data()
    override_map = {k.strip().lower(): v for k, v in (overrides or {}).items()}

    rows = [m for m in materials if _material_name(m)]
    odorant = [m for m in rows if str(_field(m, "role", "")).lower() != "solvent"]
    total_active_g = sum((_to_float(_field(m, "active_g")) or 0.0) for m in odorant)
    if total_active_g <= 0:
        total_active_g = sum((_to_float(_field(m, "active_ul")) or 0.0) for m in odorant)
    max_oav = max((_to_float(_field(m, "oav")) or 0.0) for m in odorant) if odorant else 0.0

    # Pass 1: provisional assignments.
    provisional: list[tuple[Any, FunctionAssignment]] = []
    for m in odorant:
        declared = str(_field(m, "role", "") or "").lower()
        assignment = _provisional_assignment(
            m,
            declared_role=declared,
            active_share_pct=_active_share(m, total_active_g),
            oav_value=_to_float(_field(m, "oav")),
            pw=_pw_for(_material_name(m), pw),
            max_oav=max_oav,
            overrides=override_map,
        )
        provisional.append((m, assignment))

    # Pass 2: contextual reclassification (modifier overdose -> heart).
    heart_share_pct = sum(
        a.active_share_pct for _, a in provisional if a.role == HEART
    )
    notes: list[str] = []
    assignments: list[FunctionAssignment] = []
    for _, a in provisional:
        adjusted, note = _apply_context(a, heart_share_pct=heart_share_pct)
        assignments.append(adjusted)
        if note:
            notes.append(f"{adjusted.name}: {note}")

    # Aggregate.
    role_mass: dict[str, float] = {r: 0.0 for r in FUNCTIONAL_ROLES}
    role_oav: dict[str, float] = {r: 0.0 for r in FUNCTIONAL_ROLES}
    counts: dict[str, int] = {r: 0 for r in FUNCTIONAL_ROLES}
    for a in assignments:
        role_mass[a.role] = role_mass.get(a.role, 0.0) + a.active_share_pct
        if a.oav is not None:
            role_oav[a.role] = role_oav.get(a.role, 0.0) + a.oav
        counts[a.role] = counts.get(a.role, 0) + 1

    total_oav = sum(role_oav.values())
    role_oav_share = {
        r: (100.0 * role_oav[r] / total_oav if total_oav > 0 else 0.0) for r in FUNCTIONAL_ROLES
    }
    present = {r: counts.get(r, 0) > 0 for r in FUNCTIONAL_ROLES}
    heart_components = tuple(a.name for a in assignments if a.role == HEART)

    # Architecture (Carles pyramid + olfactory-form integrity) and hedonism prior.
    architecture = evaluate_architecture(odorant, max_oav=max_oav)
    hedonics = evaluate_hedonics(odorant, hedonic_table=hedonic_table)
    neuroscience = evaluate_neuroscience(odorant)

    # Findings: hard failures are structural (a missing function), not artistic.
    fails: list[str] = []
    warns: list[str] = []

    if not present[HEART]:
        fails.append(
            "No heart/subject: no material carries the dominant odor value "
            "(Rodrigues 2021, Strongest Component Model)."
        )
    elif len(heart_components) > HEART_COMPONENT_LIMIT:
        warns.append(
            f"Heart crowding: {len(heart_components)} heart components exceeds the "
            f"{HEART_COMPONENT_LIMIT}-component identification limit (Laing et al.)."
        )
    if not present[BLENDER]:
        fails.append(
            "No blender: no low-impact material rounds or bridges the composition "
            "(Dowthwaite 1999)."
        )
    if not present[FIXATIVE]:
        fails.append(
            "No fixative: no persistent/low-volatility material supports the lasting "
            "phase (Dowthwaite 1999; Mata 2005)."
        )
    if present[MODIFIER] and role_mass[MODIFIER] >= role_mass[HEART] > 0.0:
        warns.append(
            f"Modifier mass {role_mass[MODIFIER]:.1f}% >= heart mass "
            f"{role_mass[HEART]:.1f}%; modifiers risk becoming the subject "
            "(Dowthwaite 1999)."
        )
    if not present[X_FACTOR]:
        warns.append(
            "No X-Factor accent: composition may read as generic (Dowthwaite 1999)."
        )
    perceptible = any((a.oav or 0.0) >= PERCEPTIBILITY_OAV_FLOOR for a in assignments)
    if not perceptible:
        fails.append(
            f"No material reaches the perceptibility floor OV >= {PERCEPTIBILITY_OAV_FLOOR:.0f} "
            "(Rodrigues 2021)."
        )

    # Architecture + hedonism + neuroscience findings are advisory, never failures.
    warns.extend(architecture.findings)
    warns.extend(hedonics.findings)
    warns.extend(neuroscience.findings)

    if fails:
        status = "FAIL"
    elif warns:
        status = "WARN"
    else:
        status = "PASS"

    detail_parts = [
        f"{counts[HEART]} heart/{counts[MODIFIER]} modifier/{counts[BLENDER]} blender/"
        f"{counts[FIXATIVE]} fixative/{counts[X_FACTOR]} x-factor",
        f"heart {role_mass[HEART]:.0f}% mass/{role_oav_share[HEART]:.0f}% OV",
    ]
    if fails:
        detail_parts.append(f"{len(fails)} missing function(s)")
    elif warns:
        detail_parts.append(f"{len(warns)} balance warning(s)")

    evidence = {
        "evidence_class": "LITERATURE + SUPPLIER_TECHNICAL",
        "domains": {
            domain: sorted(get_citations_for_domain(domain).keys())
            for domain in EVIDENCE_DOMAINS
        },
        "roles": {e.role: {"criteria": list(e.numeric_criteria), "citations": list(e.citations)}
                  for e in FUNCTION_ROLE_EVIDENCE},
        "thresholds": {
            "perceptibility_oav_floor": PERCEPTIBILITY_OAV_FLOOR,
            "fixative_odour_life_min_hrs": FIXATIVE_ODOUR_LIFE_MIN_HRS,
            "fixative_vp_max_pa": FIXATIVE_VP_MAX_PA,
            "blender_impact_max": BLENDER_IMPACT_MAX,
            "linalool_reference_impact": LINALOOL_REFERENCE_IMPACT,
            "modifier_trace_max_pct": MODIFIER_TRACE_MAX_PCT,
            "x_factor_max_pct": X_FACTOR_MAX_PCT,
            "heart_component_limit": HEART_COMPONENT_LIMIT,
            "olfactory_white_tone_floor": 0.2,
            "hedonic_coverage_floor": 0.5,
            "integration_channel_limit": INTEGRATION_CHANNEL_LIMIT,
            "integration_channel_oav": INTEGRATION_CHANNEL_OAV,
            "habituation_top_dominance": HABITUATION_TOP_DOMINANCE,
        },
        "citations": FUNCTIONAL_BALANCE_CITATIONS,
        "pw_supplier_records_matched": sum(
            1 for a in assignments if a.relative_impact is not None or a.odour_life_hrs is not None
        ),
        "hedonic_records_matched": sum(
            1 for m in odorant if _hedonic_for(_material_name(m), load_hedonic_valence()) is not None
        ),
    }

    return FunctionBalanceReport(
        status=status,
        detail=", ".join(detail_parts),
        assignments=tuple(assignments),
        role_mass_share=role_mass,
        role_oav_share=role_oav_share,
        role_counts=counts,
        present=present,
        heart_components=heart_components,
        findings=tuple(notes + fails + warns),
        architecture=architecture,
        hedonics=hedonics,
        neuroscience=neuroscience,
        evidence=evidence,
    )
