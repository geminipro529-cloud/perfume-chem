"""Note markers: judge a natural's note by one constituent that marks it (plan A4).

Library module only (no CLI; AGENTS.md RULE 2). Read-only.

A decomposed natural's screening OAV is a sum of constituent OAVs, and Rule 4 never reads
that sum as a whole-natural detection claim, so the yardstick holds a note such a row
carries. This module lets the yardstick judge the note anyway, through one constituent:

* a primary source names the constituent as the one that gives the natural its odour
  (listed with the marker below); a natural whose character the literature calls emergent,
  with no single impact compound, gets no marker;
* its air odour threshold is cited in the data spine (``engine.odor_thresholds``) at peer
  level (``PEER_CROSS`` or ``PEER_SINGLE``); an unverified or uncited threshold never counts;
* that one constituent's modeled vapour, divided by that threshold, reaches 1 in the note's
  window. The constituent's vapour comes from the simulator's constituent profile
  (``MaterialState.constituent_vapor_ppm``) and is never summed with other constituents.

A generic constituent (limonene in an orange oil, alpha-pinene in olibanum, benzyl alcohol
in benzoin, linalool, found in most florals and citrus) is never a marker: it reaching its
threshold does not say the formula smells of that natural (Rule 3). A marker below 1 says
nothing, because the unidentified remainder may still carry the note, so the note stays held.
Every reading reports the share of the natural its profile identifies.

Rule 1: odour activity is used here only as a detection floor (screening OAV >= 1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DETECTION_FLOOR = 1.0
# Threshold verification levels a marker may rely on (engine.odor_thresholds tags).
CITED_LEVELS = frozenset({"PEER_CROSS", "PEER_SINGLE"})


@dataclass(frozen=True)
class Marker:
    """One constituent that marks a natural's character."""

    constituent: str  # row name in the natural's constituent profile
    odt_key: str  # data-spine name of the same molecule
    source: str  # primary source for its marker role


_TONKA = Marker(
    "coumarin", "coumarin",
    "Kim D-S, Iida F (2022) Nutritional Composition of Tonka Bean (Dipteryx odorata) and Its "
    "Application as an Elder-Friendly Food with Gelling Agent. Gels 8(11):704, "
    "doi:10.3390/gels8110704, Introduction: tonka beans contain about 1-3% coumarin, \"which is "
    "responsible for the pleasant odor of the seeds\" (a literature statement, not a GC-O result). "
    "Toma AC, Stegmuller S, Richling E (2025) Eur Food Res Technol 251:513-517, "
    "doi:10.1007/s00217-024-04648-z: coumarin is tonka's flavouring compound, with a sweet, "
    "vanilla-like odour.",
)

# Natural constituent-profile key (engine.pipeline.natural_absolute_decomposition) -> markers.
# Checked and left out (20 Oct 2026), so their notes still hold:
# * lavender oil: no single impact compound; "lavender character" is "an emergent perceptual
#   property arising from the mixing of these volatiles" (Johnson, Hirson & Ebeler 2012, PLoS
#   ONE 7:e42693, GC-recomposition-olfactometry). Guo & Wang 2020 call linalyl acetate the most
#   characteristic compound of lavender extracts, not of the oil.
# * orange oil: "No single compound exhibited the characteristic aroma of orange oil"
#   (Hognadottir & Rouseff 2003, J Chromatogr A 998:201); cold-pressed peel oil GC-O names a
#   group, not one compound (Qiao et al. 2008, Molecules 13:1333).
NOTE_MARKERS: Mapping[str, tuple[Marker, ...]] = {
    "tonka bean absolute": (_TONKA,),
    "tonka bean solvent extract literature profile": (_TONKA,),
}


def cited_air_odt_ppb(odt_key: str) -> tuple[float, str] | None:
    """Return (air ODT in ppb v/v, its first source) when the spine cites it at peer level."""
    from engine.odor_thresholds import lookup_odt_entry, verify_odt

    entry = lookup_odt_entry(odt_key) or {}
    evidence = verify_odt(odt_key) or {}
    value = entry.get("odt_air")
    sources = evidence.get("sources") or []
    # The effective level: verify_odt downgrades a declared level the evidence does not bear.
    level = evidence.get("vfy")
    if value is None or float(value) <= 0 or not sources or level not in CITED_LEVELS:
        return None
    return float(value), str(sources[0])


def marker_readings(material: Any) -> list[dict[str, Any]]:
    """Every marker reading of one simulator row (a decomposed natural), best first.

    Empty when the row is not a profiled natural, has no listed marker, or no marker has a
    cited threshold. A reading is diagnostic data; only ``screening_oav >= 1`` is a verdict.
    """
    metadata = getattr(material, "natural_composite_metadata", None) or {}
    markers = NOTE_MARKERS.get(str(metadata.get("profile_key") or ""), ())
    vapour = dict(getattr(material, "constituent_vapor_ppm", ()) or ())
    readings = []
    for marker in markers:
        ppm = vapour.get(marker.constituent)
        threshold = cited_air_odt_ppb(marker.odt_key)
        if ppm is None or threshold is None:
            continue
        odt_ppb, odt_source = threshold
        value = float(ppm) / (odt_ppb / 1000.0)
        readings.append({
            "material": str(getattr(material, "name", "")),
            "constituent": marker.constituent,
            "screening_oav": value,
            "reaches_threshold": value >= DETECTION_FLOOR,
            "air_odt_ppb": odt_ppb,
            "air_odt_source": odt_source,
            "marker_source": marker.source,
            "profile_key": str(metadata.get("profile_key")),
            "identified_share": metadata.get("characterized_fraction"),
        })
    return sorted(readings, key=lambda r: -r["screening_oav"])


def detects(material: Any) -> bool:
    """True when one cited marker of this natural row reaches screening OAV 1."""
    return any(r["screening_oav"] >= DETECTION_FLOOR for r in marker_readings(material))
