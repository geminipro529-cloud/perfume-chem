"""Shared material-name normalisation across all engine modules.

Centralises the canonical form so that cross-module lookups
(ODT, VP, profiles, SAR, psychophysics, synergy graph, etc.)
never fail due to Title Case vs lowercase vs trailing whitespace.

Usage:
    from engine.name_utils import normalize_name, names_match

    key = normalize_name("Iso E Super")   # -> "iso e super"
    if names_match(user_input, profile_key):
        ...
"""

from __future__ import annotations

import re

# Canonical aliases – map common spelling variants to a single form.
# All keys **must** already be lowercase-stripped.
_ALIASES: dict[str, str] = {
    "labdanum resinoid": "labdanum",
    "labdanum resinoid (10% in dpg)": "labdanum",
    "d-limonene": "limonene",
    "ambrox": "ambrox super",
    "ambrox dl": "ambrox super",
    "ambrox super 20": "ambrox super 33% dep/etoh",
    "ambrox super dep": "ambrox super 33% dep/etoh",
    "ambrox super 33": "ambrox super 33% dep/etoh",
    "iso-e-super": "iso e super",
    "isoesuper": "iso e super",
    "benz salicylate": "benzyl salicylate",
    "benz sal": "benzyl salicylate",
    "hex sal": "hexyl salicylate",
    "hexsal": "hexyl salicylate",
    "eb": "ethylene brassylate",
    "pea": "phenethyl alcohol",
    "oranger crystals 10": "oranger crystals",  # 10% in DPG stock
    "polysantol neat": "polysantol",
    "phenethyl alcohol (pea)": "phenethyl alcohol",
    "phenyl ethyl dimethyl carbinol (pedmc)": "phenyl ethyl dimethyl carbinol",
    # Hyphenated forms that the normaliser preserves but profiles use space
    "cis-jasmone": "cis jasmone",
    # Greek letter normalisation (β-Ionone → b-ionone → beta ionone)
    "b-ionone": "beta ionone",
    "a-ionone": "alpha ionone",
    "cis-3-hexenol": "cis 3 hexenol",
    "cis-3-hexenyl salicylate": "cis 3 hexenyl salicylate",
    "alpha-damascone": "alpha damascone",
    "beta-damascone": "beta damascone",
    "gamma-damascone": "gamma damascone",
    "delta-damascone": "delta damascone",
    # Word-order variants (inventory uses "Damascone Beta", ODT uses "beta damascone")
    "damascone alpha": "alpha damascone",
    "damascone beta": "beta damascone",
    "damascone gamma": "gamma damascone",
    "damascone delta": "delta damascone",
    "alpha isomethyl ionone": "alpha-isomethyl ionone",
    "alpha isomethyl ionone (methyl ionone pure)": "alpha-isomethyl ionone",
    "aimi": "alpha-isomethyl ionone",
    "alpha irone (30% in dep)": "alpha irone",
    "alpha irone (30% w/w in ipm)": "alpha irone",
    "orris liquid (30%)": "orris liquid",
    # IBQ and FTEC variants
    "ibq": "isobutyl quinoline",
    "isobutyl quinoline (10%)": "isobutyl quinoline",
    # FTEC name variants (space vs hyphen in suffix)
    "i-iris f-tec": "i-iris ftec",
    "orris f-tec": "orris ftec",
    # EO / "oil" suffix normalisations
    "cedarwood oil virginia": "cedarwood virginia",
    "cedarwood virginia eo": "cedarwood virginia",
    "cedrat fcf oil sicilian": "cedrat fcf sicilian",
    "cedrat fcf": "cedrat fcf sicilian",
    "blood orange oil sicilian": "blood orange sicilian",
    "bergamot fcf oil sicilian": "bergamot fcf sicilian",
    "methyl ionone pure": "methyl ionone",
    "ylang comoros complete eo": "ylang comoros complete eo f3255",
    "ylang ylang eo (extra grade)": "ylang",
    # Jasmine sambac is a subspecies of jasmine absolute — share ODT data
    "jasmine sambac absolute": "jasmine absolute",
    "jasmine sambac abs": "jasmine absolute",
    "jasminum sambac absolute": "jasmine absolute",
    "jasminum sambac abs": "jasmine absolute",
    # Ethanol / solvent normalisation
    "ethanol 96%": "ethanol",
    # Myristic acid
    "myristic acid": "myristic acid powder",
    "galaxolide (50% in dep)": "galaxolide",
    "heliotropal (piperonal)": "heliotropal",
    "vanillin (10%)": "vanillin",
    "ethyl vanillin (10%)": "ethyl vanillin",
    "ethyl vanillin (10% in dpg)": "ethyl vanillin",
    "coumarin (20%)": "coumarin",
    "siam benzoin (50% in dpg)": "siam benzoin",
    "benzoin sumatra resinoid (10%)": "benzoin sumatra resinoid",
    "olibanum resinoid absolute": "olibanum resinoid",
    "olibanum resinoid absolute (10%)": "olibanum resinoid",
    "olibanum resinoid absolute - solid": "olibanum resinoid",
    "olibanum resinoid (viscous)": "olibanum resinoid",
    "olibanum resinoid (viscous, 3 g)": "olibanum resinoid",
    "dimethyl benzyl carbinyl acetate (dbca)": "dimethyl benzyl carbinyl acetate",
    # ── Inventory aliases 2026-05-23 ──
    "nerolia bromelia": "nerolin bromelia",
    "nerolin": "nerolin bromelia",
    "ylang ylang eo": "ylang",
    "black pepper ftec": "black pepper",
    "rose absolute (r. damascena)": "rose absolute",
    # ── Geranium ──
    "geranium flower eo": "geranium eo",
    "geranium eo": "geranium eo",
    # ── Jasmine ──
    "jasmine sambac": "jasmine sambac absolute",
    "jasmine sambac (10% in dpg)": "jasmine sambac absolute",
    "jasmine sambac (10%)": "jasmine sambac absolute",
    # ── Stabilizers ──
    "butylated hydroxytoluene (bht) antioxidant": "bht",
    "butylated hydroxytoluene": "bht",
    # ── Inventory additions 2026-06-03 ──
    "rose de mai absolute (10% in dpg)": "rose de mai absolute",
    "osmanthus absolute (10% in dpg)": "osmanthus absolute",
    "tonkarome (10% in dpg)": "tonkarome",
    "tuberose absolute (10% in dpg)": "tuberose absolute",
    "tuberose absolute (india)": "tuberose absolute (india)",
    "tuberose eo": "tuberose absolute (india)",
    "cocoa absolute (10% in tec)": "cocoa absolute",
    "oakmoss absolute (10% in dpg)": "oakmoss absolute",
    "evernyl (50% in dpg)": "evernyl",
    # ── EO Aliases ──
    "lavender ha": "lavender eo high altitude",
    "nagar motha oil": "nagarmortha oil",
    "immortelle absolute (10% in dpg)": "immortelle absolute",
    "rose essential oil (rosa damascena, india)": "rose essential oil",
    "rose eo": "rose essential oil",
    "cassia essential oil (cinnamomum cassia, india)": "cassia essential oil",
    "cassia eo": "cassia essential oil",
    "peppermint essential oil (mentha piperita, india)": "peppermint essential oil",
    "peppermint eo": "peppermint essential oil",
    "eucalyptus essential oil (eucalyptus globulus, india)": "eucalyptus essential oil",
    "eucalyptus eo": "eucalyptus essential oil",
    "petitgrain eo paraguay": "petitgrain eo paraguay",
    "galbanum eo": "galbanum eo",
    "phenyl ethyl acetate": "phenyl ethyl acetate",
    "tuberalia base": "tuberalia base",
    # ── Inventory additions 2026-06-14 ──
    "himalayan cedarwood eo": "himalayan cedarwood eo",
    "cassis base 345b": "cassis base 345b",
    "cassis base 345": "cassis base 345b",
    "cassis 345b": "cassis base 345b",
    "clove eo (india)": "clove eo",
    "clove eo india": "clove eo",
    "anise eo (china)": "anise eo",
    "anise eo china": "anise eo",
    "basil eo (india, ocimum basilicum)": "basil eo",
    "basil eo (india)": "basil eo",
    "sweet basil eo": "basil eo",
}


def normalize_name(name: str) -> str:
    """Return the canonical lowercase key for *name*.

    Steps:
        1. Strip leading/trailing whitespace.
        2. Collapse internal whitespace to a single space.
        3. Lower-case the result.
        4. Resolve known aliases.
    """
    if not name:
        return ""
    n = re.sub(r"\s+", " ", name.strip()).lower()
    return _ALIASES.get(n, n)


def names_match(a: str, b: str) -> bool:
    """Return True when *a* and *b* resolve to the same canonical name."""
    return normalize_name(a) == normalize_name(b)
