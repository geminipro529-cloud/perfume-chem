"""Tiered literature reference database for perfumery science.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

Encodes the tiered reference database from the Formulation Intelligence Database
(Part XIII). References are organized by tier:

  Tier A: Peer-Reviewed Journal Articles
  Tier B: Classical Perfumery Texts
  Tier C: Practitioner Codifications
  Tier D: Regulatory Documents
  Tier E: Author Estimates (flagged)

Each reference includes:
  - Short key for citation
  - Full title with source
  - Source quality tier
  - Key data provided
  - URL (where available)

This module provides cite() for generating reference annotations and
get_references_by_topic() for curated reading lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ._shared_types import Reference, ReferenceTier


# ---------------------------------------------------------------------------
# Tier A: Peer-Reviewed Journal Articles
# ---------------------------------------------------------------------------

TIER_A: tuple[Reference, ...] = (
    Reference(
        "Livermore & Laing 1996",
        "Influence of training and experience on the perception of multicomponent odor mixtures. J Exp Psychol Hum Percept Perform 22(2):267-277",
        ReferenceTier.A_PEER_REVIEWED,
        "3-4 component limit, training-independent; expert panel of 8 perfumers confirmed",
        "https://pubmed.ncbi.nlm.nih.gov/8934843/",
    ),
    Reference(
        "Jinks & Laing 1999",
        "A limit in the processing of components in odour mixtures. Perception 28(3):395-404",
        ReferenceTier.A_PEER_REVIEWED,
        "Limit to 4 object odors confirmed; chance-level identification at 16 odorants due to competitive OR inhibition",
        "https://pubmed.ncbi.nlm.nih.gov/10615476/",
    ),
    Reference(
        "Laing & Francis 1989",
        "The capacity of humans to identify odors in mixtures. Physiol Behav 46(5):809-814",
        ReferenceTier.A_PEER_REVIEWED,
        "Original 3-4 component capacity establishment; 123 subjects tested",
        "https://pubmed.ncbi.nlm.nih.gov/2628992/",
    ),
    Reference(
        "Wallrabenstein et al. 2015",
        "The smelling of Hedione results in sex-differentiated human brain activity. NeuroImage",
        ReferenceTier.A_PEER_REVIEWED,
        "Hedione activates VN1R1 pheromone receptor; sex-differentiated limbic activation (amygdala, hippocampus)",
        "https://pubmed.ncbi.nlm.nih.gov/25797832/",
    ),
    Reference(
        "PMC 2017 — Hedione reciprocity",
        "Exposure to Hedione Increases Reciprocity in Humans. PMC",
        ReferenceTier.A_PEER_REVIEWED,
        "Hedione increases prosocial behavior in humans; confirmatory VN1R1 pathway evidence",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC5411439/",
    ),
    Reference(
        "Takase et al. 2025",
        "An odorant receptor for a key odor constituent of ambergris. Commun Biol 8:792",
        ReferenceTier.A_PEER_REVIEWED,
        "OR7A17 identified for ambroxide; non-functional alleles prevalent in East Asia (~20%)",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12102163/",
    ),
    Reference(
        "Wysocki & Beauchamp 1989",
        "Ability to perceive androstenone can be acquired by ostensibly anosmic people. PNAS 86(20):7976",
        ReferenceTier.A_PEER_REVIEWED,
        "~50% apparent anosmia to androstenone; heritable and trainable in ~50% of apparent anosmic subjects",
        "https://www.pnas.org/doi/10.1073/pnas.86.20.7976",
    ),
    Reference(
        "Chem Senses 2003",
        "The Prevalence of Androstenone Anosmia. Chem Senses",
        ReferenceTier.A_PEER_REVIEWED,
        "True non-detection of androstenone = 1.8-5.96% in young healthy adults (forced-choice)",
        "https://pubmed.ncbi.nlm.nih.gov/12826538/",
    ),
    Reference(
        "Cosmetics Business 2020",
        "Picking up a stink: Scientists pinpoint receptors linked to body odour and musk perception",
        ReferenceTier.A_PEER_REVIEWED,
        "OR4D6 identified as first human OR for musk-specific anosmia (galaxolide); M263T, S151T variants",
        "https://cosmeticsbusiness.com/picking-up-a-stink-scientists-pinpoint-receptors-linked-to-body-odour-and-musk-perception--198556",
    ),
    Reference(
        "Menashe et al. 2007",
        "A Genetic Basis for Hypersensitivity to Sweaty Odors in Humans. PLoS Biol",
        ReferenceTier.A_PEER_REVIEWED,
        "Genetic basis of specific anosmia; OR mutations documented",
        "https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0050298",
    ),
    Reference(
        "Demole, Enggist & Ohloff 1982",
        "1-p-Menthene-8-thiol: A powerful flavor impact constituent of grapefruit juice. Helv. Chim. Acta 65:1785",
        ReferenceTier.A_PEER_REVIEWED,
        "Grapefruit mercaptan ODT = 0.000034 ng/L air; most potent flavor compound in nature",
        "https://onlinelibrary.wiley.com/doi/10.1002/hlca.19820650614",
    ),
    Reference(
        "Pub. Chem. 2016",
        "Structure-Odor Activity Studies on Monoterpenoid Mercaptans. Pub. Chem.",
        ReferenceTier.A_PEER_REVIEWED,
        "ODT confirmation for 1-p-Menthene-8-thiol; structure-odor-activity relationships",
        "https://pubmed.ncbi.nlm.nih.gov/27121638/",
    ),
    Reference(
        "RIFM linalool",
        "Update to RIFM fragrance ingredient safety assessment, linalool, CAS 78-70-6",
        ReferenceTier.A_PEER_REVIEWED,
        "Systemic safety and RIFM framework for linalool",
        "https://pubmed.ncbi.nlm.nih.gov/34800550/",
    ),
    Reference(
        "RIFM geranyl linalool",
        "RIFM fragrance ingredient safety assessment, geranyl linalool, CAS 1113-21-9",
        ReferenceTier.A_PEER_REVIEWED,
        "RIFM safety assessment methodology example",
        "https://pubmed.ncbi.nlm.nih.gov/39236864/",
    ),
)


# ---------------------------------------------------------------------------
# Tier B: Classical Perfumery Texts
# ---------------------------------------------------------------------------

TIER_B: tuple[Reference, ...] = (
    Reference(
        "Arctander 1969",
        "Perfume and Flavor Chemicals (Aroma Chemicals). Two volumes.",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Standard monograph reference for material descriptions, odor characteristics, and usage",
        None,
    ),
    Reference(
        "Ohloff, Pickenhagen & Kraft 2011",
        "Scent and Chemistry: The Molecular World of Odors",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Definitive modern synthesis of fragrance chemistry; structure-odor relationships",
        None,
    ),
    Reference(
        "Sell 2006",
        "The Chemistry of Fragrances: From Perfumer to Consumer. 2nd ed.",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Chemistry-focused practitioner reference; formulation principles",
        None,
    ),
    Reference(
        "Turin 2006",
        "The Secret of Scent: Adventures in Perfume and the Science of Smell",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Receptor theory; vibrational theory of olfaction; material-specific descriptions",
        None,
    ),
    Reference(
        "Jellinek 1997",
        "The Psychological Basis of Perfumery. 4th ed.",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Psychophysiology, accord theory, hedonic psychology, consumer perception",
        None,
    ),
    Reference(
        "Roudnitska",
        "L'Art du Parfum and collected essays on perfumery methodology",
        ReferenceTier.B_CLASSICAL_TEXT,
        "One truth methodology; indispensable flaw principle; maceration timeline (4-week rule)",
        None,
    ),
    Reference(
        "Carles 1961",
        "A Method of Creation in Perfumery",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Accord-based construction; pyramid system (top-heart-base); the Carles method",
        None,
    ),
    Reference(
        "Ellena 2011",
        "Perfume: The Alchemy of Scent",
        ReferenceTier.B_CLASSICAL_TEXT,
        "Minimalism; texture-first construction; transparency; the Hermès approach",
        None,
    ),
)


# ---------------------------------------------------------------------------
# Tier C: Practitioner Codifications
# ---------------------------------------------------------------------------

TIER_C: tuple[Reference, ...] = (
    Reference(
        "Leffingwell ODT database",
        "Odor Detection Thresholds & References. Leffingwell & Associates.",
        ReferenceTier.C_PRACTITIONER,
        "ODT compilation for 2000+ compounds in air and water; widely cited by RIFM and industry",
        "http://www.leffingwell.com/odorthre.htm",
    ),
    Reference(
        "van Gemert 2011",
        "Compilations of Odour Threshold Values in Air, Water and Other Media",
        ReferenceTier.C_PRACTITIONER,
        "Comprehensive multi-matrix ODT compilation; standard industry reference for thresholds",
        None,
    ),
    Reference(
        "Devos et al. 1990",
        "Standardized Human Olfactory Thresholds",
        ReferenceTier.C_PRACTITIONER,
        "Standardized threshold methodology and inter-laboratory comparison",
        None,
    ),
    Reference(
        "TGSC",
        "The Good Scents Company — material profiles and supplier data",
        ReferenceTier.C_PRACTITIONER,
        "Odor descriptions, supplier data, CAS numbers, IUPAC names, physical properties",
        "https://www.thegoodscentscompany.com/",
    ),
    Reference(
        "P&F Indole",
        "An Aroma Chemical Profile: Indole. Perfumer & Flavorist.",
        ReferenceTier.C_PRACTITIONER,
        "Practitioner dosing guidance; LD50 data; concentration-dependent character zones",
        "https://img.perfumerflavorist.com/files/base/allured/all/document/2016/02/pf.9514.pdf",
    ),
    Reference(
        "Teixeira et al. 2013",
        "Perfume Engineering: Design, Performance and Classification",
        ReferenceTier.C_PRACTITIONER,
        "OAV-based engineering model for perfume; thermodynamic release modeling; quantitative approach",
        "https://books.google.com/books/about/Perfume_Engineering.html?id=ZtM1iJq9XPIC",
    ),
    Reference(
        "Olfactive Aesthetics",
        "Fragrance Building Principles: Method of Perfume Creation",
        ReferenceTier.C_PRACTITIONER,
        "Accord building methodology; modern molecules review; chypre and fougère construction",
        "https://olfactiveaesthetics.com/",
    ),
    Reference(
        "Premiere Peau",
        "Indole in Perfumery — Jasmine's Dark Engine; Iso E Super molecular guide",
        ReferenceTier.C_PRACTITIONER,
        "Narcotic jasmine zone < 0.1% indole; fecal cliff > 1%; dilution guidance",
        "https://premierepeau.com/",
    ),
)


# ---------------------------------------------------------------------------
# Tier D: Regulatory Documents
# ---------------------------------------------------------------------------

TIER_D: tuple[Reference, ...] = (
    Reference(
        "IFRA 51st Amendment",
        "Official Notice on IFRA 51st Amendment (June 2023). MS Star / EQGest",
        ReferenceTier.D_REGULATORY,
        "All concentration limits by category; 59 new rules; implementation timeline through Oct 2025",
        "https://msstar.eu/2023/07/19/official-notice-on-ifra-51st-amendment/",
    ),
    Reference(
        "IFRA Galaxolide CoC",
        "Galaxolide Compliance with IFRA Standards — Certificate of Conformity",
        ReferenceTier.D_REGULATORY,
        "Galaxolide confirmed unrestricted in Cat4 (fine fragrance leave-on)",
        None,
    ),
    Reference(
        "EU 1223/2009 Annex III",
        "EU Cosmetics Regulation — List of substances which cosmetic products must not contain except subject to restrictions",
        ReferenceTier.D_REGULATORY,
        "26 allergen declaration requirements at > 0.001% leave-on / > 0.010% rinse-off",
        None,
    ),
    Reference(
        "SCCS/1525/21",
        "SCCS Opinion on fragrance allergens in cosmetic products",
        ReferenceTier.D_REGULATORY,
        "Proposed expansion to 82+ allergens; Iso E Super recommended for EU allergen declaration",
        None,
    ),
    Reference(
        "Scentspiracy IFRA",
        "IFRA Limits, The 26 most common — Cat4 reference",
        ReferenceTier.D_REGULATORY,
        "Quick reference for Cat4 limits: oakmoss 0.1%, coumarin 1.5%, benzyl benzoate 4.8%, etc.",
        "https://www.scentspiracy.com/blog/ifra-limits",
    ),
)


# ---------------------------------------------------------------------------
# Tier E: Author Estimates
# ---------------------------------------------------------------------------

TIER_E: tuple[Reference, ...] = (
    Reference(
        "AUTHOR_ESTIMATE",
        "Values derived by structural analogy, VP-logP correlations, or expert extrapolation where no primary source exists.",
        ReferenceTier.E_AUTHOR_ESTIMATE,
        "VP values for natural EOs; hedonic ratings for synthetics; Hill parameters; OAV in complex mixtures; synergistic hedonic impacts",
        None,
    ),
)


# ---------------------------------------------------------------------------
# All references
# ---------------------------------------------------------------------------

ALL_REFERENCES: tuple[Reference, ...] = TIER_A + TIER_B + TIER_C + TIER_D + TIER_E


# ---------------------------------------------------------------------------
# Topic-based curation
# ---------------------------------------------------------------------------

TOPIC_REFERENCES: dict[str, tuple[str, ...]] = {
    "mixture_perception": (
        "Livermore & Laing 1996", "Jinks & Laing 1999", "Laing & Francis 1989",
    ),
    "hedione_vn1r1": (
        "Wallrabenstein et al. 2015", "PMC 2017 — Hedione reciprocity",
    ),
    "anosmia_receptors": (
        "Takase et al. 2025", "Wysocki & Beauchamp 1989", "Chem Senses 2003",
        "Cosmetics Business 2020", "Menashe et al. 2007",
    ),
    "odor_thresholds": (
        "Demole, Enggist & Ohloff 1982", "Pub. Chem. 2016",
        "Leffingwell ODT database", "van Gemert 2011", "Devos et al. 1990",
    ),
    "perfumery_methodology": (
        "Roudnitska", "Carles 1961", "Ellena 2011", "Jellinek 1997",
        "Teixeira et al. 2013",
    ),
    "material_reference": (
        "Arctander 1969", "Ohloff, Pickenhagen & Kraft 2011", "Sell 2006",
        "TGSC", "P&F Indole", "Olfactive Aesthetics", "Premiere Peau",
    ),
    "ifra_regulatory": (
        "IFRA 51st Amendment", "IFRA Galaxolide CoC", "EU 1223/2009 Annex III",
        "SCCS/1525/21", "Scentspiracy IFRA",
    ),
    "safety_toxicology": (
        "RIFM linalool", "RIFM geranyl linalool",
    ),
    "receptor_science": (
        "Takase et al. 2025", "Turin 2006", "Cosmetics Business 2020",
        "Wallrabenstein et al. 2015", "Menashe et al. 2007",
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_reference(key: str) -> Reference | None:
    """Return a reference by its key (case-insensitive partial match)."""
    key_lower = key.lower()
    for ref in ALL_REFERENCES:
        if key_lower in ref.key.lower():
            return ref
    return None


def get_references_by_tier(tier: ReferenceTier) -> tuple[Reference, ...]:
    """Return all references of a given quality tier."""
    return tuple(r for r in ALL_REFERENCES if r.tier == tier)


def get_references_by_topic(topic: str) -> tuple[Reference, ...]:
    """Return references curated for a specific topic.

    Valid topics: mixture_perception, hedione_vn1r1, anosmia_receptors,
    odor_thresholds, perfumery_methodology, material_reference,
    ifra_regulatory, safety_toxicology, receptor_science.
    """
    keys = TOPIC_REFERENCES.get(topic, ())
    refs = []
    for key in keys:
        ref = get_reference(key)
        if ref:
            refs.append(ref)
    return tuple(refs)


def get_all_references() -> tuple[Reference, ...]:
    """Return all references in the database."""
    return ALL_REFERENCES


def cite(key: str) -> str:
    """Generate a citation string for a reference.

    Returns a formatted citation like "[Livermore & Laing 1996]" or
    "[AUTHOR_ESTIMATE]" for untrusted values.
    """
    ref = get_reference(key)
    if ref is None:
        return f"[?{key}]"

    if ref.tier == ReferenceTier.E_AUTHOR_ESTIMATE:
        return f"[AUTHOR_ESTIMATE: {key}]"
    if ref.tier == ReferenceTier.D_REGULATORY:
        return f"[REG: {key}]"
    if ref.tier == ReferenceTier.A_PEER_REVIEWED:
        return f"[{key}]"
    return f"[{ref.tier.value}: {key}]"


def get_topic_keys() -> tuple[str, ...]:
    """Return all available topic names for curation."""
    return tuple(TOPIC_REFERENCES.keys())


def get_tier_counts() -> dict[str, int]:
    """Return count of references by tier."""
    counts: dict[str, int] = {}
    for ref in ALL_REFERENCES:
        tier_name = ref.tier.value
        counts[tier_name] = counts.get(tier_name, 0) + 1
    return counts
