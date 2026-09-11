"""Ingredient Intelligence Database — Per-material character dimensions and properties.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- Every formula dose must be convertible to ppm.
- Every threshold check must reference ODT.
- Every perceptibility claim must be backed by OAV.
- No exceptions — this applies to formulation, dosing, gating, scoring, and all pipeline modules.

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

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from engine.material_data_loader import load_engine_data as _load_engine_data
from engine.material_identity import resolve_material_identity

# Character dimension names (order matters for radar plot)
DIMENSIONS = [
    "warmth",
    "sweetness",
    "freshness",
    "powdery",
    "green",
    "animalic",
    "radiance",
    "woody",
    "spicy",
    "floral",
    "smoky",
    "creamy",
    "transparency",
]


class CharacterEvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PROSE_ONLY = "PROSE_ONLY"
    MISSING = "MISSING"
    INVALID_NUMERIC = "INVALID_NUMERIC"


class NumericCharacterUnavailable(ValueError):  # noqa: N818 - public contract name
    """Raised when a numeric character operation has no valid vector evidence."""


@dataclass
class MaterialProfile:
    """Complete intelligence profile for one material."""

    name: str
    # Compatibility input. After validation this is either the same numeric
    # mapping as ``numeric_character`` or None; prose is never treated as data.
    character: Mapping[str, float] | str | None = None
    character_description: str | None = None
    numeric_character: Mapping[str, float] | None = None
    character_status: CharacterEvidenceStatus = field(init=False)
    character_reason: str = field(init=False, default="")
    # Keys supplied outside the accepted 13-dimension contract. They are never
    # consumed as evidence; they are recorded so nothing is dropped silently.
    character_excluded: tuple[str, ...] = field(init=False, default=())
    # Physical properties
    mw: float | None = None
    vp: float | None = None
    clogp: float | None = None
    odt: float | None = None  # ppb in air — for temporal diffusion / headspace math
    odt_ppm: float | None = None  # ppm in ethanol solution — for OAV math in concentrate
    # Classification
    note: str = "heart"  # top / heart / base
    role: str = "modifier"  # character, modifier, fixative, volume, radiance, bridge, trace
    texture: str = ""  # skin-effect, diffusion, cushion, lift, cocoon, veil, halo
    material_kind: str = ""
    # Relationships
    synergies: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    # Dilution in inventory
    dilution: float = 1.0  # 1.0 = neat, 0.1 = 10%, etc.
    # Scientific extensions (added per Perplexity consultation 2026-04-23)
    activity_coef: float = 1.0  # γᵢ, Raoult non-ideality. 1.0 = ideal; <1.0 = matrix-suppressed headspace; >1.0 = matrix-boosted.
    hedonic: float = 0.0  # panel-style pleasantness rating, −5..+5. 0 = neutral / unmeasured.
    or_family: str | None = (
        None  # olfactory-receptor bin: citrus, rose, muguet, musk, amber, iris, green, aldehydic, gourmand, smoky, animalic, woody, aquatic, aromatic, indolic, ozone
    )

    def __post_init__(self) -> None:
        description = self.character_description
        if isinstance(self.character, str):
            description = description or self.character.strip() or None
        raw = self.numeric_character if self.numeric_character is not None else self.character
        if isinstance(raw, str):
            raw = None

        status = CharacterEvidenceStatus.MISSING
        reason = "numeric character evidence is missing"
        validated: dict[str, float] | None = None
        excluded: list[str] = []
        if raw is None:
            if description:
                status = CharacterEvidenceStatus.PROSE_ONLY
                reason = "descriptive character prose is not a numeric vector"
        elif not isinstance(raw, Mapping):
            status = CharacterEvidenceStatus.INVALID_NUMERIC
            reason = "numeric character evidence is not a mapping"
        elif not raw:
            status = CharacterEvidenceStatus.MISSING
            reason = "numeric character mapping is empty"
        else:
            invalid: list[str] = []
            candidate: dict[str, float] = {}
            for dimension, value in raw.items():
                if dimension not in DIMENSIONS:
                    # Non-contract keys were never consumed by the 13-dimension
                    # contract; exclude and record them instead of voiding the
                    # profile's valid dimensions.
                    excluded.append(str(dimension))
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    invalid.append(f"{dimension} is not a real number")
                    continue
                numeric = float(value)
                if not math.isfinite(numeric) or not 0.0 <= numeric <= 10.0:
                    invalid.append(f"{dimension} is outside the finite 0..10 contract")
                    continue
                candidate[str(dimension)] = numeric
            if invalid:
                status = CharacterEvidenceStatus.INVALID_NUMERIC
                reason = "; ".join(invalid)
            elif not candidate:
                status = CharacterEvidenceStatus.INVALID_NUMERIC
                reason = (
                    "no accepted numeric dimensions; excluded non-contract keys: "
                    + ", ".join(sorted(excluded))
                )
            else:
                validated = candidate
                status = CharacterEvidenceStatus.AVAILABLE
                reason = (
                    "excluded non-contract character keys: "
                    + ", ".join(sorted(excluded))
                    if excluded
                    else ""
                )

        self.character_description = description
        self.numeric_character = validated
        self.character = validated
        self.character_status = status
        self.character_reason = reason
        self.character_excluded = tuple(sorted(excluded))

    def require_numeric_character(self) -> Mapping[str, float]:
        if self.numeric_character is None:
            raise NumericCharacterUnavailable(
                f"{self.name}: {self.character_status.value}: {self.character_reason}"
            )
        return self.numeric_character

    def dimension_vector(self) -> list[float]:
        """Return ordered vector of character dimensions."""
        character = self.require_numeric_character()
        return [character.get(d, 0.0) for d in DIMENSIONS]

    def dominant_character(self) -> str:
        """Return the highest-scoring dimension name."""
        character = self.require_numeric_character()
        return max(character, key=character.get)

    def character_tags(self, threshold: float = 4.0) -> list[str]:
        """Return dimensions above threshold, sorted by strength."""
        character = self.require_numeric_character()
        return sorted(
            [d for d, v in character.items() if v >= threshold],
            key=lambda d: character[d],
            reverse=True,
        )


# ── Complete inventory intelligence database ──
# Every material from inventory.txt with expert-assigned character dimensions.
# Values: 0=absent, 1-2=trace, 3-4=noticeable, 5-6=moderate, 7-8=strong, 9-10=defining

_PROFILES = _load_engine_data("ingredient_intelligence", "_PROFILES")

# Aliases for common naming variants
_ALIASES = _load_engine_data("ingredient_intelligence", "_ALIASES")


# ── Transparency dimension injection (Ellena axis) ──
# Inject "transparency" into character dicts based on material classification.
# 8-10 = highly transparent (sheer, diaphanous), 4-7 = neutral, 0-3 = opaque/dense
_TRANSPARENCY_SCORES = _load_engine_data("ingredient_intelligence", "_TRANSPARENCY_SCORES")

# ── Chemical Family Map for Natural Compatibility (F11) ──────────────────
# Maps complex naturals to their dominant chemical families.
# Two naturals that share ZERO families are flagged as potentially incompatible.
# Families follow structural chemistry taxonomy: same backbone/shared biosynthetic origin.
_CHEMICAL_FAMILY_MAP = _load_engine_data("ingredient_intelligence", "_CHEMICAL_FAMILY_MAP")

# Define incompatible family pairs — when naturals carry these families they clash.
# Per F11: azulene + benzenoid clashed (Blue Chamomile vs Rose)
# Per F11: ionone + phenylpropanoid clashed (Osmanthus vs Clove)
# Per F11: alcohol_terpenoid + aldehyde_green clashed (Geranium vs Violet Leaf)
_INCOMPATIBLE_FAMILIES: list[tuple[str, str]] = [
    ("azulene", "benzenoid"),
    ("ionone", "phenylpropanoid"),
    ("alcohol_terpenoid", "aldehydic_green"),
    ("phenylpropanoid", "coumarin"),
    ("indolic", "pyrazine"),
    ("phenolic_orcinol", "lactone_indolic"),
]


def check_natural_compatibility(material_names: list[str]) -> list[str] | None:
    """Return list of incompatible natural pairs, or None if all compatible."""
    warnings: list[str] = []
    profiles = [(n, _CHEMICAL_FAMILY_MAP.get(n)) for n in material_names]
    naturals = [(n, f) for n, f in profiles if f is not None]

    for i in range(len(naturals)):
        for j in range(i + 1, len(naturals)):
            ni, fi = naturals[i]
            nj, fj = naturals[j]
            for fa, fb in _INCOMPATIBLE_FAMILIES:
                if fa in fi and fb in fj and not (set(fi) & set(fj)):
                    warnings.append(
                        f"{ni} + {nj}: potentially incompatible ({fa} vs {fb}, no shared family)"
                    )
                    break
    return warnings or None


for _name, _score in _TRANSPARENCY_SCORES.items():
    if _name in _PROFILES:
        _PROFILES[_name]["character"].setdefault("transparency", _score)
del _name, _score  # clean up module namespace

# ── Auto-populate ODT from ODT_DATA ──────────────────────────────
# Enrich _PROFILES with odt values from the canonical ODT database.
# Two fields are populated:
#   odt      : ppb in air   — used by temporal_graph / headspace diffusion.
#   odt_ppm  : ppm in ethanol solution — used by scorers comparing to
#              concentrate-level dose (ppm_in_conc = pct * 10000).
# Keeping both units avoids the semantic mismatch of comparing a
# concentrate-level ppm dose to a headspace-ppb threshold.
try:
    from engine.name_utils import normalize_name as _nn
    from engine.odor_thresholds import ODT_DATA as _ODT_SRC

    _odt_air_index = {_nn(k): v.get("odt_air") for k, v in _ODT_SRC.items()}
    _odt_eth_index = {_nn(k): v.get("odt_eth") for k, v in _ODT_SRC.items()}
    for _pname in _PROFILES:
        _key = _nn(_pname)
        if "odt" not in _PROFILES[_pname] or _PROFILES[_pname].get("odt") is None:
            _odt_air_val = _odt_air_index.get(_key)
            if _odt_air_val is not None:
                _PROFILES[_pname]["odt"] = _odt_air_val
        if "odt_ppm" not in _PROFILES[_pname] or _PROFILES[_pname].get("odt_ppm") is None:
            _odt_eth_val = _odt_eth_index.get(_key)
            if _odt_eth_val is not None:
                _PROFILES[_pname]["odt_ppm"] = _odt_eth_val
    # Clean up module namespace (some names may be unset if dicts were empty)
    for _n in (
        "_odt_air_index",
        "_odt_eth_index",
        "_odt_air_val",
        "_odt_eth_val",
        "_pname",
        "_key",
        "_ODT_SRC",
        "_nn",
    ):
        if _n in dir():
            try:
                del globals()[_n]
            except KeyError:
                pass
except Exception:
    pass  # Graceful fallback: odt/odt_ppm stay None if import fails


# ── Auto-populate or_family / activity_coef / hedonic ─────────────
# Added per Perplexity consultation 2026-04-23. Provides the physical
# and perceptual data the scorer needs to move beyond pure OAV-ratio
# classification toward Raoult-corrected airborne dose and panel-style
# pleasantness. Defaults are cheap heuristics from name/role/character;
# overrides capture the well-known non-ideal / hedonic outliers.

# Explicit OR-family overrides — the safest bins first, so character-
# dimension fallback handles the long tail.
_OR_FAMILY_OVERRIDES = _load_engine_data("ingredient_intelligence", "_OR_FAMILY_OVERRIDES")

# Activity coefficient γᵢ — how much the ethanol matrix suppresses
# (<1) or boosts (>1) the material's partial pressure relative to
# Raoult-ideal. Values from Perplexity consultation.
_ACTIVITY_COEF_OVERRIDES = _load_engine_data("ingredient_intelligence", "_ACTIVITY_COEF_OVERRIDES")

# Hedonic scalars −5..+5 — panel-style pleasantness. Coarse seed; use
# dominant character as a fallback heuristic.
_HEDONIC_OVERRIDES = _load_engine_data("ingredient_intelligence", "_HEDONIC_OVERRIDES")

# Character-dimension → OR-family fallback (only used when no override).
_CHAR_TO_FAMILY = _load_engine_data("ingredient_intelligence", "_CHAR_TO_FAMILY")

for _pname, _pdata in _PROFILES.items():
    # or_family
    if _pdata.get("or_family") is None:
        fam = _OR_FAMILY_OVERRIDES.get(_pname)
        if fam is None:
            # derive from dominant character
            ch = _pdata.get("character", {})
            if ch:
                dom = max(ch, key=ch.get)
                fam = _CHAR_TO_FAMILY.get(dom)
        if fam is not None:
            _pdata["or_family"] = fam
    # activity_coef
    if "activity_coef" not in _pdata:
        gamma = _ACTIVITY_COEF_OVERRIDES.get(_pname, 1.0)
        _pdata["activity_coef"] = gamma
    # hedonic
    if "hedonic" not in _pdata:
        hed = _HEDONIC_OVERRIDES.get(_pname)
        if hed is None:
            # cheap fallback: 0.5 × (sum of pleasant dims) − (sum of harsh dims), clamped
            ch = _pdata.get("character", {})
            pleasant = (
                ch.get("floral", 0)
                + ch.get("rosy", 0)
                + ch.get("gourmand", 0)
                + ch.get("powdery", 0)
                + ch.get("citrus", 0)
            ) / 5.0
            harsh = (ch.get("smoky", 0) + ch.get("animalic", 0) + ch.get("metallic", 0)) / 3.0
            hed = max(-3.0, min(3.0, 0.4 * pleasant - 0.3 * harsh))
        _pdata["hedonic"] = round(hed, 2)

for _n in ("_pname", "_pdata", "fam", "ch", "dom", "gamma", "hed", "pleasant", "harsh"):
    if _n in dir():
        try:
            del globals()[_n]
        except KeyError:
            pass


def _name_variants(name: str) -> list[str]:
    greek_map = str.maketrans(
        {
            "α": "a",
            "β": "b",
            "γ": "g",
            "δ": "d",
            "’": "'",
        }
    )
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
        if data is None and key is not None:
            for profile_key, profile_value in _PROFILES.items():
                if profile_key.lower() == str(key).lower():
                    data = profile_value
                    key = profile_key
                    break
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
            odt_ppm=data.get("odt_ppm"),
            note=data.get("note", "heart"),
            role=data.get("role", "modifier"),
            texture=data.get("texture", ""),
            material_kind=data.get("material_kind", ""),
            synergies=data.get("synergies", []),
            avoid=data.get("avoid", []),
            dilution=data.get("dilution", 1.0),
            activity_coef=data.get("activity_coef", 1.0),
            hedonic=data.get("hedonic", 0.0),
            or_family=data.get("or_family"),
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


@dataclass(frozen=True)
class CharacterSimilarityResult:
    ranked: tuple[tuple[str, float], ...]
    unavailable: tuple[str, ...]
    source_status: CharacterEvidenceStatus


def find_similar_with_evidence(name: str, n: int = 5) -> CharacterSimilarityResult:
    """Rank only numerically comparable profiles and report unavailable identities."""

    source = get_profile(name)
    if source is None:
        return CharacterSimilarityResult((), (), CharacterEvidenceStatus.MISSING)
    if source.numeric_character is None:
        return CharacterSimilarityResult((), (), source.character_status)
    results: list[tuple[str, float]] = []
    unavailable: list[str] = []
    for other_name in _PROFILES:
        if other_name == source.name:
            continue
        other = get_profile(other_name)
        if other is None or other.numeric_character is None:
            unavailable.append(other_name)
            continue
        dist = character_distance(source, other)
        results.append((other_name, round(dist, 2)))
    results.sort(key=lambda item: item[1])
    return CharacterSimilarityResult(
        tuple(results[:n]), tuple(sorted(unavailable)), source.character_status
    )


def find_similar(name: str, n: int = 5) -> list[tuple[str, float]]:
    """Find the n most similar materials to the given one by character profile.
    Returns (name, distance) pairs sorted by distance."""
    return list(find_similar_with_evidence(name, n=n).ranked)


# ═══════════════════════════════════════════════
# VERIFIED VP CORRECTIONS — overrides auto-generated values
# Source: external cross-check 2026-05-12 via Indenta SDS, BASF SDS,
# Vigon SDS, Firmenich official, ChemBook, NIST WebBook
# ═══════════════════════════════════════════════

_VERIFIED_VP = _load_engine_data("ingredient_intelligence", "_VERIFIED_VP")

_VERIFIED_VP_SOURCE = _load_engine_data("ingredient_intelligence", "_VERIFIED_VP_SOURCE")

for _key, _val in _VERIFIED_VP.items():
    if _key in _PROFILES:
        _PROFILES[_key]["vp"] = _val
        _PROFILES[_key]["vp_source"] = _VERIFIED_VP_SOURCE.get(
            _key, "VERIFIED external cross-check 2026-05-12"
        )
        _PROFILES[_key]["vp_flag"] = (
            "ESTIMATED_FROM_OFFICIAL_20C" if _key == "Habanolide" else "VERIFIED_EXTERNAL"
        )
    else:
        # Attempt to find by normalized name
        from engine.name_utils import normalize_name

        for _pn in list(_PROFILES.keys()):
            if normalize_name(_pn) == normalize_name(_key):
                _PROFILES[_pn]["vp"] = _val
                _PROFILES[_pn]["vp_source"] = "VERIFIED external cross-check 2026-05-12"
                _PROFILES[_pn]["vp_flag"] = "VERIFIED_EXTERNAL"
                break


def suggest_replacement(missing_name: str, inventory_names: set[str]) -> str:
    """Suggest an in-inventory replacement for a missing material.

    Matches by odor character or note tier from _PROFILES.
    Returns "no close match" if nothing found.
    """
    from engine.name_utils import normalize_name

    missing_norm = normalize_name(missing_name)
    missing_profile = get_profile(missing_norm)

    if missing_profile is None:
        return "no profile data — check inventory manually"

    target_char = missing_profile.numeric_character
    target_note = missing_profile.note
    if target_char is None:
        return "numeric character evidence unavailable — browse inventory by note"

    best_match = ""
    best_score = 0
    for name, profile in _PROFILES.items():
        inv_name = normalize_name(name)
        if not any(inv_name in inv or inv in inv_name for inv in inventory_names):
            continue
        candidate_profile = get_profile(name)
        pchar = candidate_profile.numeric_character if candidate_profile else None
        pnote = candidate_profile.note if candidate_profile else ""
        if pchar is None:
            continue
        distance = sum(
            (target_char.get(dimension, 0.0) - pchar.get(dimension, 0.0)) ** 2
            for dimension in DIMENSIONS
        ) ** 0.5
        score = max(0.0, 10.0 - distance)
        if pnote == target_note and target_note:
            score += 1.0
        if score > best_score:
            best_score = score
            best_match = name

    return best_match if best_score >= 7 else "no close match — browse inventory by note/character"


# ─────────────────────────────────────────────────────────────────────

# MATERIAL_INTAKE_BATCH_2026_08_07 — post-definition patch (user material intake)

MATERIAL_INTAKE_BATCH_2026_08_07 = True

_PROFILES.setdefault("nerolidol", {}).update(
    {
        "character": "woody-floral balsamic sesquiterpene alcohol",
        "note": "floral",
        "role": "heart",
        "texture": "soft, balmy",
        "mw": 222.37,
        "vp": 0.006,
        "clogp": 4.6,
        "odt_air_ppb": 150.0,
        "odt_eth_ppm": 0.9,
        "odor_family": "floral_woody",
        "activity_coef": 1.2,
        "hedonic": 0.6,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("stralyl acetate", {}).update(
    {
        "character": "green-sweet gardenia-floral ester",
        "note": "floral",
        "role": "heart",
        "texture": "sweet, green",
        "mw": 164.2,
        "vp": 7.0,
        "clogp": 2.0,
        "odt_air_ppb": 40.0,
        "odt_eth_ppm": 1.0,
        "odor_family": "floral",
        "activity_coef": 1.8,
        "hedonic": 0.6,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("cypress eo", {}).update(
    {
        "character": "dry conifer-woody-aromatic natural",
        "note": "woody",
        "role": "heart",
        "texture": "dry, resinous",
        "mw": 136.0,
        "vp": 250.0,
        "clogp": 3.8,
        "odt_air_ppb": 200.0,
        "odt_eth_ppm": 0.5,
        "odor_family": "conifer",
        "activity_coef": 3.0,
        "hedonic": 0.4,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("padma", {}).update(
    {
        "character": "green-hyacinth floral acetal",
        "note": "floral",
        "role": "heart",
        "texture": "green, stemmy",
        "mw": 166.22,
        "vp": 20.0,
        "clogp": 2.1,
        "odt_air_ppb": 200.0,
        "odt_eth_ppm": 0.5,
        "odor_family": "green_floral",
        "activity_coef": 1.5,
        "hedonic": 0.5,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("hay absolute", {}).update(
    {
        "character": "coumarinic hay, dry, natural",
        "note": "hay",
        "role": "base",
        "texture": "dry, powdery",
        "mw": 146.0,
        "vp": 0.3,
        "clogp": 1.4,
        "odt_air_ppb": 4.0,
        "odt_eth_ppm": 0.01,
        "odor_family": "hay",
        "activity_coef": 0.7,
        "hedonic": 0.7,
        "impact": 3,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("cabreuva eo", {}).update(
    {
        "character": "woody-balsamic nerolidol-rich oil",
        "note": "woody",
        "role": "base",
        "texture": "soft, balsamic",
        "mw": 222.0,
        "vp": 0.006,
        "clogp": 4.6,
        "odt_air_ppb": 150.0,
        "odt_eth_ppm": 0.9,
        "odor_family": "woody",
        "activity_coef": 1.2,
        "hedonic": 0.6,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("tuberlia base", {}).update(
    {
        "character": "tuberose-creamy captive base",
        "note": "floral",
        "role": "heart",
        "texture": "creamy, waxy",
        "mw": 190.0,
        "vp": 0.1,
        "clogp": 2.5,
        "odt_air_ppb": 10.0,
        "odt_eth_ppm": 0.02,
        "odor_family": "tuberose",
        "activity_coef": 0.6,
        "hedonic": 0.7,
        "impact": 3,
        "product_basis": True,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("caraway seed eo", {}).update(
    {
        "character": "caraway-seed spicy natural",
        "note": "spice",
        "role": "heart",
        "texture": "sharp, seed",
        "mw": 150.0,
        "vp": 6.0,
        "clogp": 2.6,
        "odt_air_ppb": 2.0,
        "odt_eth_ppm": 0.01,
        "odor_family": "spice",
        "activity_coef": 2.5,
        "hedonic": 0.4,
        "impact": 3,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("turkish storax", {}).update(
    {
        "character": "balsamic-cinnamic resin tincture",
        "note": "balsamic",
        "role": "base",
        "texture": "warm, resinous",
        "mw": 148.0,
        "vp": 1.0,
        "clogp": 2.0,
        "odt_air_ppb": 20.0,
        "odt_eth_ppm": 0.05,
        "odor_family": "balsamic",
        "activity_coef": 1.2,
        "hedonic": 0.6,
        "impact": 3,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("benzoin styrax tonkinensis tincture", {}).update(
    {
        "character": "benzoin-balsamic sweet resin tincture",
        "note": "balsamic",
        "role": "base",
        "texture": "sweet, resinous",
        "mw": 212.0,
        "vp": 0.02,
        "clogp": 2.5,
        "odt_air_ppb": 3.0,
        "odt_eth_ppm": 0.01,
        "odor_family": "balsamic",
        "activity_coef": 0.6,
        "hedonic": 0.7,
        "impact": 3,
        "product_basis": True,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("helichrysum eo", {}).update(
    {
        "character": "immortelle hay-curry-floral natural",
        "note": "floral",
        "role": "heart",
        "texture": "hay, curry",
        "mw": 180.0,
        "vp": 0.5,
        "clogp": 3.0,
        "odt_air_ppb": 5.0,
        "odt_eth_ppm": 0.01,
        "odor_family": "immortelle",
        "activity_coef": 1.0,
        "hedonic": 0.5,
        "impact": 3,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("verdyl acetate", {}).update(
    {
        "character": "green-floral-woody acetate",
        "note": "floral",
        "role": "heart",
        "texture": "green, woody",
        "mw": 192.25,
        "vp": 2.0,
        "clogp": 2.2,
        "odt_air_ppb": 10.0,
        "odt_eth_ppm": 0.02,
        "odor_family": "green_floral",
        "activity_coef": 2.0,
        "hedonic": 0.5,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("sandalwood base x3", {}).update(
    {
        "character": "creamy-warm sandalwood pre-blend",
        "note": "woody",
        "role": "base",
        "texture": "creamy, smooth",
        "mw": 220.0,
        "vp": 0.1,
        "clogp": 3.5,
        "odt_air_ppb": 100.0,
        "odt_eth_ppm": 0.5,
        "odor_family": "sandalwood",
        "activity_coef": 0.6,
        "hedonic": 0.8,
        "impact": 3,
        "product_basis": True,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("tuberose eo (volume level grade)", {}).update(
    {
        "character": "tuberose green-creamy natural",
        "note": "floral",
        "role": "heart",
        "texture": "creamy, green",
        "mw": 190.0,
        "vp": 0.1,
        "clogp": 2.5,
        "odt_air_ppb": 20.0,
        "odt_eth_ppm": 0.05,
        "odor_family": "tuberose",
        "activity_coef": 0.6,
        "hedonic": 0.7,
        "impact": 3,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)
_PROFILES.setdefault("elemi eo", {}).update(
    {
        "character": "elemi pine-citrus-balsamic resin oil",
        "note": "citrus",
        "role": "top",
        "texture": "fresh, balsamic",
        "mw": 204.0,
        "vp": 5.0,
        "clogp": 4.0,
        "odt_air_ppb": 10.0,  # aligned to pre-existing ODT_DATA elemi eo (remediation 2026-08-07)
        "odt_eth_ppm": 2.0,
        "odor_family": "citrus_balsamic",
        "activity_coef": 2.5,
        "hedonic": 0.5,
        "impact": 2,
        "product_basis": False,
        "source": "material intake batch 2026-08-07",
    }
)

# ─────────────────────────────────────────────────────────────────────
# MATERIAL_INTAKE_REMEDIATION_2026_08_07 — MaterialProfile reads "odt"/"odt_ppm" (auditor CRITICAL C2)
MATERIAL_INTAKE_REMEDIATION_2026_08_07 = True
# backfill Phenethyl Alcohol (legacy profile) odt keys (auditor C2b)
from engine.odor_thresholds import ODT_DATA as _INTAKE_ODT_DATA  # noqa: E402

_PEA = _PROFILES.setdefault("Phenethyl Alcohol", {})
_PEA.setdefault("odt", _INTAKE_ODT_DATA.get("phenethyl alcohol", {}).get("odt_air"))
_PEA.setdefault("odt_ppm", _INTAKE_ODT_DATA.get("phenethyl alcohol", {}).get("odt_eth"))

for _mi_name in [
    "nerolidol",
    "stralyl acetate",
    "cypress eo",
    "padma",
    "hay absolute",
    "cabreuva eo",
    "tuberlia base",
    "caraway seed eo",
    "turkish storax",
    "benzoin styrax tonkinensis tincture",
    "helichrysum eo",
    "verdyl acetate",
    "sandalwood base x3",
    "tuberose eo (volume level grade)",
]:
    _mi_prof = _PROFILES.setdefault(_mi_name, {})
    _mi_prof.setdefault("odt", _mi_prof.get("odt_air_ppb"))
    _mi_prof.setdefault("odt_ppm", _mi_prof.get("odt_eth_ppm"))
# elemi eo: align profile with pre-existing ODT_DATA (10.0/2.0) and drop the unsourced 5.0/0.05
_PROFILES.setdefault("elemi eo", {}).update(
    {"odt_air_ppb": 10.0, "odt_eth_ppm": 2.0, "odt": 10.0, "odt_ppm": 2.0}
)
