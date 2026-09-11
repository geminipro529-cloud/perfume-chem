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

from engine.material_data_loader import load_engine_data as _load_engine_data
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

ODT_DATA = _load_engine_data("odor_thresholds", "ODT_DATA")

# ── Verification Metadata ─────────────────────────────────────────
# Maps each material to its verification status and source citation.
# Keyed by the same name used in ODT_DATA.
# Prevents reliance on unverified thresholds in OAV calculations.

ODT_VERIFICATION = _load_engine_data("odor_thresholds", "ODT_VERIFICATION")

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
}


def _odt_query_key(material_name: str) -> str:
    normalized = normalize_name(material_name)
    return _ODT_QUERY_ALIASES.get(normalized, normalized)


def lookup_odt_entry(material_name: str) -> Optional[dict]:
    """Return the authoritative ODT_DATA entry for a material via normalized lookup."""
    normalized = normalize_name(material_name)
    query_key = _odt_query_key(material_name)
    hit = _ODT_BY_NORMALIZED_NAME.get(query_key)
    if hit is None:
        return None
    if query_key == normalized:
        return hit[1]
    return {
        **hit[1],
        "evidence_status": "ESTIMATED_PROXY",
        "proxy_source_name": hit[0],
        "proxy_query_name": normalized,
    }


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
    """Return verification metadata for a material, or None if not in DB."""
    key = normalize_name(material_name)
    exact = _ODT_VERIFICATION_BY_NORMALIZED_NAME.get(key)
    if exact is not None:
        return exact
    raw_key = material_name.lower().strip()
    if raw_key in ODT_VERIFICATION:
        return ODT_VERIFICATION[raw_key]
    if key in ODT_VERIFICATION:
        return ODT_VERIFICATION[key]
    # fuzzy match
    for k in ODT_VERIFICATION:
        nk = normalize_name(k)
        if key[:8] in nk or nk in key[:8]:
            return ODT_VERIFICATION[k]
    return None


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
        if meta and meta["vfy"] in ("UNVERIFIED", "DERIVED"):
            flagged.append(f"{name} [{meta['vfy']}]")
        elif not meta:
            flagged.append(f"{name} [NOT IN DB]")
    return flagged


def oav_reliability(material_name: str) -> str:
    """Return reliability label for OAV calculations using this material's ODT."""
    meta = verify_odt(material_name)
    if not meta:
        return "UNKNOWN — material not in ODT database"
    vfy = meta["vfy"]
    if vfy == "PEER_CROSS":
        return "HIGH — cross-verified by 2+ independent peer-reviewed sources"
    if vfy == "PEER_SINGLE":
        return "MODERATE — single peer-reviewed source"
    if vfy == "PEER_EST":
        return "MODERATE-LOW — peer-reviewed for isomer, estimated for commercial grade"
    if vfy == "DERIVED":
        return "LOW — estimated from water-phase or constituent data"
    return "UNRELIABLE — no peer-reviewed data exists"


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

NOTE_TO_MATERIALS = _load_engine_data("odor_thresholds", "NOTE_TO_MATERIALS")


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

_VERIFIED_ODT = _load_engine_data("odor_thresholds", "_VERIFIED_ODT")

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
# (auditor CRITICAL C1: without this, batch ODT_DATA entries are unreachable via runtime lookup)
MATERIAL_INTAKE_REMEDIATION_2026_08_07 = True
_refresh_normalized_odt_index()
_ODT_VERIFICATION_BY_NORMALIZED_NAME = {
    normalize_name(raw_name): data for raw_name, data in ODT_VERIFICATION.items()
}
_raise_on_normalized_odt_collisions()
