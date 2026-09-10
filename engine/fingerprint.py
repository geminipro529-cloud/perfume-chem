"""Material and formula fingerprinting system.

Encodes materials as feature vectors for similarity search, clustering, and
synergy analysis. Analogous to molecular fingerprinting (ECFP/MACCS) in
cheminformatics — but operating in olfactive descriptor space rather than
substructure space.

Three fingerprint levels:
  1. MaterialFingerprint — per-material descriptor vector
  2. FormulaFingerprint — weighted aggregate of material fingerprints
  3. AccordFingerprint — sub-formula (top/heart/base or custom grouping)

Similarity metrics: cosine, Tanimoto (for binary), Euclidean distance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from engine.ingredient_intelligence import (
    DIMENSIONS,
    CharacterEvidenceStatus,
    MaterialProfile,
    get_all_profiles,
    get_profile,
)

# ── Extended feature dimensions beyond the 12 character dimensions ──
# These encode functional/structural properties for richer fingerprints.
FUNCTIONAL_FEATURES = [
    "is_fixative", "is_volume", "is_radiance", "is_trace", "is_bridge",
    "is_character", "is_modifier",
]
TEXTURE_FEATURES = [
    "tex_cocoon", "tex_cushion", "tex_lift", "tex_halo",
    "tex_veil", "tex_diffusion", "tex_skin_effect",
]
VOLATILITY_FEATURES = [
    "vol_top", "vol_heart", "vol_base",
]
PHYSICAL_FEATURES = [
    "log_mw", "log_vp", "clogp_norm",
]

ALL_FEATURES = DIMENSIONS + FUNCTIONAL_FEATURES + TEXTURE_FEATURES + VOLATILITY_FEATURES + PHYSICAL_FEATURES
FEATURE_COUNT = len(ALL_FEATURES)
_FEATURE_INDEX = {f: i for i, f in enumerate(ALL_FEATURES)}


# ═══════════════════════════════════════════════════════════════════════════════
# Material Fingerprint
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MaterialFingerprint:
    """Full feature vector for a single material."""
    name: str
    vector: list[float] = field(default_factory=list)
    binary_vector: list[int] = field(default_factory=list)  # Thresholded for Tanimoto
    character_status: CharacterEvidenceStatus = CharacterEvidenceStatus.MISSING

    def __len__(self) -> int:
        return len(self.vector)

    def dominant_features(self, n: int = 5) -> list[tuple[str, float]]:
        """Top N features by magnitude."""
        pairs = [(ALL_FEATURES[i], v) for i, v in enumerate(self.vector) if v > 0]
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs[:n]

    def character_signature(self) -> str:
        """Human-readable signature string: top 3 character dimensions."""
        if self.character_status is not CharacterEvidenceStatus.AVAILABLE:
            return f"unavailable ({self.character_status.value})"
        char_pairs = [(ALL_FEATURES[i], self.vector[i]) for i in range(len(DIMENSIONS))]
        char_pairs.sort(key=lambda x: x[1], reverse=True)
        top3 = [f"{name}({val:.0f})" for name, val in char_pairs[:3] if val > 0]
        return " / ".join(top3) if top3 else "neutral"


def _role_to_features(role: str) -> dict[str, float]:
    """Convert role string to functional feature values."""
    mapping = {
        "fixative": "is_fixative",
        "volume": "is_volume",
        "radiance": "is_radiance",
        "trace": "is_trace",
        "bridge": "is_bridge",
        "character": "is_character",
        "modifier": "is_modifier",
    }
    result = {f: 0.0 for f in FUNCTIONAL_FEATURES}
    feat = mapping.get(role)
    if feat:
        result[feat] = 1.0
    return result


def _texture_to_features(texture: str) -> dict[str, float]:
    """Convert texture string to texture feature values."""
    mapping = {
        "cocoon": "tex_cocoon",
        "cushion": "tex_cushion",
        "lift": "tex_lift",
        "halo": "tex_halo",
        "veil": "tex_veil",
        "diffusion": "tex_diffusion",
        "skin-effect": "tex_skin_effect",
    }
    result = {f: 0.0 for f in TEXTURE_FEATURES}
    feat = mapping.get(texture)
    if feat:
        result[feat] = 1.0
    return result


def _note_to_features(note: str) -> dict[str, float]:
    """Convert note class to volatility features."""
    result = {"vol_top": 0.0, "vol_heart": 0.0, "vol_base": 0.0}
    feat = f"vol_{note}"
    if feat in result:
        result[feat] = 1.0
    return result


def _physical_features(profile: MaterialProfile) -> dict[str, float]:
    """Normalize physical properties to 0-10 scale."""
    # log(MW) scaled: MW ranges ~100-310, log(100)=4.6, log(310)=5.7
    log_mw = 0.0
    if profile.mw and profile.mw > 0:
        log_mw = (math.log(profile.mw) - 4.6) / 1.1 * 10.0
        log_mw = max(0.0, min(10.0, log_mw))

    # log(VP) scaled: VP ranges 0.00001-5.0, log scale inverted
    # Higher VP = more volatile = higher value
    log_vp = 0.0
    if profile.vp and profile.vp > 0:
        # log10 range: -5 to 0.7 → normalize to 0-10
        log_vp = (math.log10(profile.vp) + 5) / 5.7 * 10.0
        log_vp = max(0.0, min(10.0, log_vp))

    # CLogP normalized: range ~0-7 → scale to 0-10
    clogp = 0.0
    if profile.clogp is not None:
        clogp = profile.clogp / 7.0 * 10.0
        clogp = max(0.0, min(10.0, clogp))

    return {"log_mw": log_mw, "log_vp": log_vp, "clogp_norm": clogp}


def fingerprint_material(name: str) -> MaterialFingerprint | None:
    """Generate a full fingerprint vector for a material."""
    profile = get_profile(name)
    if profile is None:
        return None

    vector = [0.0] * FEATURE_COUNT

    # Character dimensions (0-10 scale)
    character = profile.numeric_character
    for dim in DIMENSIONS:
        idx = _FEATURE_INDEX[dim]
        if character is not None:
            vector[idx] = character.get(dim, 0.0)

    # Functional role features (binary 0/1)
    for feat, val in _role_to_features(profile.role).items():
        vector[_FEATURE_INDEX[feat]] = val

    # Texture features (binary 0/1)
    for feat, val in _texture_to_features(profile.texture).items():
        vector[_FEATURE_INDEX[feat]] = val

    # Volatility class (binary 0/1)
    for feat, val in _note_to_features(profile.note).items():
        vector[_FEATURE_INDEX[feat]] = val

    # Physical properties (normalized 0-10)
    for feat, val in _physical_features(profile).items():
        vector[_FEATURE_INDEX[feat]] = val

    # Binary version: threshold at 2.0 for character dims, 0.5 for binary features
    binary = []
    for i, v in enumerate(vector):
        if i < len(DIMENSIONS):
            binary.append(1 if v >= 2.0 else 0)
        else:
            binary.append(1 if v >= 0.5 else 0)

    return MaterialFingerprint(
        name=name,
        vector=vector,
        binary_vector=binary,
        character_status=profile.character_status,
    )


def fingerprint_all_materials() -> dict[str, MaterialFingerprint]:
    """Generate fingerprints for all materials in the intelligence database."""
    all_profiles = get_all_profiles()
    result = {}
    for name in all_profiles:
        fp = fingerprint_material(name)
        if fp:
            result[name] = fp
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Formula Fingerprint
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FormulaFingerprint:
    """Aggregate fingerprint for an entire formula."""
    name: str
    vector: list[float] = field(default_factory=list)
    ingredient_count: int = 0
    total_mass: float = 0.0
    # Per-layer fingerprints
    top_vector: list[float] = field(default_factory=list)
    heart_vector: list[float] = field(default_factory=list)
    base_vector: list[float] = field(default_factory=list)
    # Coverage stats
    note_distribution: dict[str, float] = field(default_factory=dict)
    role_distribution: dict[str, float] = field(default_factory=dict)
    texture_distribution: dict[str, float] = field(default_factory=dict)
    # Materials included
    materials: list[str] = field(default_factory=list)
    # Materials not found in database
    unknown_materials: list[str] = field(default_factory=list)
    character_coverage_fraction: float = 0.0
    character_missing_materials: list[str] = field(default_factory=list)

    def character_radar(self) -> dict[str, float] | None:
        """Return a radar only when every formula mass has numeric evidence."""
        if self.character_coverage_fraction < 1.0:
            return None
        return {DIMENSIONS[i]: self.vector[i] for i in range(len(DIMENSIONS))}

    def dominant_character(self, n: int = 3) -> list[tuple[str, float]] | None:
        """Top N character dimensions, or None for incomplete evidence."""
        radar = self.character_radar()
        if radar is None:
            return None
        return sorted(radar.items(), key=lambda x: x[1], reverse=True)[:n]


def fingerprint_formula(
    name: str,
    ingredients: dict[str, float],
) -> FormulaFingerprint:
    """Generate a weighted fingerprint for a formula.

    Args:
        name: Formula name
        ingredients: {material_name: amount_in_uL_or_mL} — the absolute amounts.
                     Weights are computed as proportions of total.
    """
    total = sum(ingredients.values())
    if total <= 0:
        return FormulaFingerprint(name=name)

    agg = [0.0] * FEATURE_COUNT
    top_agg = [0.0] * FEATURE_COUNT
    heart_agg = [0.0] * FEATURE_COUNT
    base_agg = [0.0] * FEATURE_COUNT

    note_mass = {"top": 0.0, "heart": 0.0, "base": 0.0}
    role_mass: dict[str, float] = {}
    texture_mass: dict[str, float] = {}
    materials_used = []
    unknown = []
    character_missing: list[str] = []
    character_covered_mass = 0.0

    for mat_name, amount in ingredients.items():
        fp = fingerprint_material(mat_name)
        if fp is None:
            unknown.append(mat_name)
            continue

        weight = amount / total
        materials_used.append(mat_name)

        profile = get_profile(mat_name)
        note = profile.note if profile else "heart"
        if fp.character_status is CharacterEvidenceStatus.AVAILABLE:
            character_covered_mass += amount
        else:
            character_missing.append(mat_name)

        # Weight the vector by mass proportion
        for i in range(FEATURE_COUNT):
            agg[i] += fp.vector[i] * weight

        # Layer-specific aggregation
        layer = {"top": top_agg, "heart": heart_agg, "base": base_agg}.get(note, heart_agg)
        for i in range(FEATURE_COUNT):
            layer[i] += fp.vector[i] * weight

        note_mass[note] = note_mass.get(note, 0.0) + amount

        if profile:
            role_mass[profile.role] = role_mass.get(profile.role, 0.0) + amount
            if profile.texture:
                texture_mass[profile.texture] = texture_mass.get(profile.texture, 0.0) + amount

    # Normalize distributions to percentages
    note_dist = {k: round(v / total * 100, 1) for k, v in note_mass.items()}
    role_dist = {k: round(v / total * 100, 1) for k, v in role_mass.items()}
    tex_dist = {k: round(v / total * 100, 1) for k, v in texture_mass.items()}

    return FormulaFingerprint(
        name=name,
        vector=agg,
        ingredient_count=len(materials_used),
        total_mass=total,
        top_vector=top_agg,
        heart_vector=heart_agg,
        base_vector=base_agg,
        note_distribution=note_dist,
        role_distribution=role_dist,
        texture_distribution=tex_dist,
        materials=materials_used,
        unknown_materials=unknown,
        character_coverage_fraction=max(0.0, min(1.0, character_covered_mass / total)),
        character_missing_materials=sorted(set(character_missing + unknown)),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Similarity Metrics
# ═══════════════════════════════════════════════════════════════════════════════

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0-1.0."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def tanimoto_similarity(a: Sequence[int], b: Sequence[int]) -> float:
    """Tanimoto similarity between two binary fingerprints. Returns 0.0-1.0."""
    intersection = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    union = sum(1 for x, y in zip(a, b) if x == 1 or y == 1)
    if union == 0:
        return 0.0
    return intersection / union


def euclidean_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Euclidean distance between two vectors."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def material_similarity(
    name_a: str,
    name_b: str,
    method: str = "cosine",
) -> float | None:
    """Compute similarity between two materials.

    Methods: 'cosine', 'tanimoto', 'euclidean'
    Returns None if either material is unknown.
    """
    fp_a = fingerprint_material(name_a)
    fp_b = fingerprint_material(name_b)
    if (
        fp_a is None
        or fp_b is None
        or fp_a.character_status is not CharacterEvidenceStatus.AVAILABLE
        or fp_b.character_status is not CharacterEvidenceStatus.AVAILABLE
    ):
        return None

    if method == "cosine":
        return cosine_similarity(fp_a.vector, fp_b.vector)
    elif method == "tanimoto":
        return tanimoto_similarity(fp_a.binary_vector, fp_b.binary_vector)
    elif method == "euclidean":
        return euclidean_distance(fp_a.vector, fp_b.vector)
    else:
        return cosine_similarity(fp_a.vector, fp_b.vector)


def formula_similarity(
    fp_a: FormulaFingerprint,
    fp_b: FormulaFingerprint,
    method: str = "cosine",
) -> float | None:
    """Compute similarity between two formula fingerprints."""
    if (
        fp_a.character_coverage_fraction < 1.0
        or fp_b.character_coverage_fraction < 1.0
    ):
        return None
    if method == "cosine":
        return cosine_similarity(fp_a.vector, fp_b.vector)
    elif method == "euclidean":
        return euclidean_distance(fp_a.vector, fp_b.vector)
    return cosine_similarity(fp_a.vector, fp_b.vector)


def find_similar_materials(
    name: str,
    n: int = 10,
    method: str = "cosine",
) -> list[tuple[str, float]]:
    """Find the N most similar materials using fingerprint comparison.

    Returns (name, similarity_score) sorted by similarity descending for cosine/tanimoto,
    ascending for euclidean.
    """
    source = fingerprint_material(name)
    if source is None or source.character_status is not CharacterEvidenceStatus.AVAILABLE:
        return []

    all_fps = fingerprint_all_materials()
    results = []

    for other_name, other_fp in all_fps.items():
        if other_name == source.name:
            continue
        if other_fp.character_status is not CharacterEvidenceStatus.AVAILABLE:
            continue
        if method == "cosine":
            score = cosine_similarity(source.vector, other_fp.vector)
        elif method == "tanimoto":
            score = tanimoto_similarity(source.binary_vector, other_fp.binary_vector)
        else:
            score = euclidean_distance(source.vector, other_fp.vector)
        results.append((other_name, round(score, 4)))

    reverse = method != "euclidean"
    results.sort(key=lambda x: x[1], reverse=reverse)
    return results[:n]
