"""Accord-First Formula Discovery Pipeline

Builds perfume formulas from the project's accord library, scored by
classical perfumery theory (Carles, Roudnitska, Jellinek, OPK SAR, Arctander).
Synergy is a bonus — accords and theory drive everything.

Sources:
  - perfume_accord_library.txt  (12 pre-designed accords)
  - theory_rules.json           (5 book frameworks)
  - materials DB                (101 materials with theory positions)
  - inventory.txt               (parsed dynamically from current inventory)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from engine.optimizer.models import (
    FormulaVector, ObjectiveWeights,
    get_theory_rules, get_accord_library,
    _lookup_material, classify_note, materials_match, resolve_material_name,
    material_roudnitska_roles, material_jellinek_quadrant_key,
)
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer
from engine.ingredient_intelligence import get_profile, DIMENSIONS
from engine.inventory_parser import inventory_names
from engine.chemical_data_validator import is_blocked_chemical


def load_inventory() -> list[str]:
    return [
        name
        for name in inventory_names(
            unique=True,
            include_solvents=False,
            include_unavailable=False,
        )
        if not is_blocked_chemical(name)
    ]


def _concrete_inventory_match(name: str, inventory: list[str] | None = None) -> str | None:
    """Return a concrete inventory name for a generic descriptor when possible."""
    if inventory:
        for candidate in inventory:
            if materials_match(name, candidate):
                return candidate
    resolved = resolve_material_name(name)
    return resolved or None


def match_accord_to_inventory(accord: dict, inventory: list[str]) -> dict:
    """Check which accord ingredients are available in inventory."""
    available = {}
    missing = []
    total_orig = sum(accord["ingredients"].values())

    for mat_name, pct in accord["ingredients"].items():
        # Strip dilution suffix
        clean = re.sub(r'\s*[\u2014\u2013-]\s*\d+%\s*$', '', mat_name).strip()
        matched = None
        for inv_mat in inventory:
            if materials_match(clean, inv_mat):
                matched = inv_mat
                break
        if matched:
            available[matched] = pct
        else:
            missing.append(clean)

    total_available = sum(available.values())
    coverage = total_available / total_orig if total_orig > 0 else 0

    return {
        "name": accord["name"],
        "available": available,
        "missing": missing,
        "coverage": round(coverage * 100, 1),
        "viable": coverage >= 0.5 and len(available) >= 3,
        "target": accord.get("target", ""),
        "good_for": accord.get("good_for", ""),
        "use_at": accord.get("use_at", ""),
    }


# Solvents/carriers/functional materials — never pick as star
_SOLVENTS = {"diethyl phthalate", "dipropylene glycol", "isopropyl myristate",
             "triethyl citrate", "benzyl benzoate"}

_GENERIC_STAR_PENALTIES = {
    "linalyl acetate": 2.5,
    "linalool": 1.5,
    "citronellal": 1.5,
    "bergamot fcf": 1.0,
    "iso e super": 1.0,
    "hedione": 1.0,
}

_DEFAULT_STYLE_PROFILE = {
    "name": "classical",
    "keywords": (),
    "dimensions": {"radiance": 0.4, "floral": 0.3, "woody": 0.3},
    "avoid_dimensions": {},
    "preferred_tokens": (),
    "note_weights": {"top": 0.4, "heart": 0.8, "base": 0.4},
    "scorer_style": "classical",
}

_STYLE_PROFILES = [
    {
        "name": "amber_oriental",
        "keywords": (
            "amber", "oriental", "gourmand", "resin", "incense",
            "church", "evening wear", "mfk", "br540",
        ),
        "dimensions": {"warmth": 1.3, "sweetness": 0.9, "woody": 0.6, "creamy": 0.6, "smoky": 0.4},
        "avoid_dimensions": {"freshness": 0.9, "green": 0.3},
        "preferred_tokens": (
            "amber", "ambrox", "benzoin", "labdanum", "vanillin", "tonka",
            "coumarin", "styrax", "resin", "incense", "cashmeran",
        ),
        "note_weights": {"top": -0.7, "heart": 0.9, "base": 1.2},
        "scorer_style": "oriental",
    },
    {
        "name": "aquatic_fresh",
        "keywords": (
            "aquatic", "marine", "ozonic", "fresh-floral", "office-safe",
            "acqua di gio", "clean, marine", "transparent",
        ),
        "dimensions": {"freshness": 1.4, "radiance": 1.0, "green": 0.4, "floral": 0.4},
        "avoid_dimensions": {"smoky": 1.0, "animalic": 0.8, "sweetness": 0.4},
        "preferred_tokens": (
            "calone", "floralozone", "marine", "ozone", "aldehyde",
            "cyclamen", "dihydromyrcenol", "aquatic", "helional",
        ),
        "note_weights": {"top": 1.1, "heart": 0.6, "base": -0.5},
        "scorer_style": "cologne",
    },
    {
        "name": "cassis_dark",
        "keywords": (
            "cassis", "berry", "fruity", "narciso", "dark feminine", "chypre",
        ),
        "dimensions": {"sweetness": 1.0, "green": 0.7, "animalic": 0.4, "powdery": 0.4, "woody": 0.3},
        "avoid_dimensions": {"freshness": 0.5, "smoky": 0.3},
        "preferred_tokens": (
            "cassis", "currant", "berry", "raspberry", "dewberry",
            "peonile", "ionone", "violet", "fruit",
        ),
        "note_weights": {"top": 0.3, "heart": 1.0, "base": 0.3},
        "scorer_style": "chypre",
    },
    {
        "name": "clean_musk",
        "keywords": (
            "clean musk", "laundry", "skin scent", "invisible skin", "universal base",
            "cleanliness", "warm clean skin",
        ),
        "dimensions": {"freshness": 0.8, "creamy": 0.8, "radiance": 0.7, "powdery": 0.3},
        "avoid_dimensions": {"smoky": 1.2, "spicy": 0.6},
        "preferred_tokens": (
            "musk", "olide", "brassylate", "cashmeran",
            "ambrettolide", "zenolide", "galaxolide", "habanolide",
        ),
        "note_weights": {"top": 0.0, "heart": 0.7, "base": 0.9},
        "scorer_style": "skin_scent",
    },
    {
        "name": "iris",
        "keywords": (
            "iris", "dior homme", "prada l'homme", "powdery", "suede gloves",
        ),
        "dimensions": {"powdery": 1.4, "woody": 0.5, "creamy": 0.5, "floral": 0.4},
        "avoid_dimensions": {"freshness": 1.0, "green": 0.5, "smoky": 0.3},
        "preferred_tokens": (
            "iris", "irone", "ionone", "orris", "orivone",
            "violet", "heliotropin", "suede",
        ),
        "note_weights": {"top": -0.4, "heart": 1.2, "base": 0.4},
        "scorer_style": "classical",
    },
    {
        "name": "leather",
        "keywords": (
            "leather", "gentleman's study", "oud-leather", "biker chic",
            "worn leather", "fireplace",
        ),
        "dimensions": {"animalic": 1.2, "smoky": 1.1, "woody": 0.8, "warmth": 0.4},
        "avoid_dimensions": {"freshness": 1.2, "floral": 0.5},
        "preferred_tokens": (
            "leather", "suede", "birch", "quinoline", "styrax",
            "guaiacol", "labdanum", "safran", "cade", "vetiver",
        ),
        "note_weights": {"top": -1.2, "heart": 0.6, "base": 1.2},
        "scorer_style": "oriental",
    },
    {
        "name": "muguet",
        "keywords": (
            "muguet", "lily-of-the-valley", "diorissimo", "spring daytime",
        ),
        "dimensions": {"floral": 1.2, "freshness": 0.9, "green": 0.5, "radiance": 0.6},
        "avoid_dimensions": {"smoky": 1.0, "animalic": 0.8, "woody": 0.3},
        "preferred_tokens": (
            "muguet", "lily", "hydroxycitronellal", "florol", "cyclamen",
            "rose oxide", "neroli", "aldehyde", "linalool", "geraniol",
        ),
        "note_weights": {"top": 0.7, "heart": 1.1, "base": -0.7},
        "scorer_style": "soliflore",
    },
    {
        "name": "pepper_spice",
        "keywords": (
            "pepper", "cardamom", "spicy-fresh", "pink pepper", "aromatic",
        ),
        "dimensions": {"spicy": 1.3, "freshness": 0.5, "woody": 0.4, "warmth": 0.4},
        "avoid_dimensions": {"powdery": 0.5, "sweetness": 0.5, "creamy": 0.3},
        "preferred_tokens": (
            "pepper", "cardamom", "galbanum", "safran",
            "eugenol", "cinnamon", "clove", "spice",
        ),
        "note_weights": {"top": 0.8, "heart": 0.8, "base": -0.2},
        "scorer_style": "classical",
    },
    {
        "name": "vetiver_woody",
        "keywords": (
            "vetiver", "terre d'hermès", "earthy-woody masculine", "sycomore",
            "dry, earthy, mineral",
        ),
        "dimensions": {"woody": 1.2, "green": 0.8, "smoky": 0.3, "spicy": 0.3, "freshness": 0.2},
        "avoid_dimensions": {"sweetness": 0.6, "powdery": 0.4, "creamy": 0.3},
        "preferred_tokens": (
            "vetiver", "patchouli", "cedar", "wood", "bacdanol",
            "ebanol", "norlimbanol", "cashmeran",
        ),
        "note_weights": {"top": -0.5, "heart": 0.8, "base": 0.9},
        "scorer_style": "classical",
    },
]

def _is_creative_material(mat_name: str) -> bool:
    """True if this is a real perfumery material, not a solvent/carrier."""
    if is_blocked_chemical(mat_name):
        return False
    if mat_name.lower().strip() in _SOLVENTS:
        return False
    mat = _lookup_material(mat_name)
    if mat:
        pos = (mat.get("carles_position") or "").lower()
        if "functional" in pos or "carrier" in pos or "solvent" in pos:
            return False
    return mat is not None  # must exist in DB


def _preferred_note_for_roles(missing_roles: set[str]) -> str | None:
    if {"eclat", "transparence"} & missing_roles:
        return "top"
    if {"noblesse"} & missing_roles:
        return "heart"
    if {"peau", "chaleur", "profondeur"} & missing_roles:
        return "base"
    return None


def _accord_character_vector(accord_match: dict) -> dict[str, float]:
    dim_totals = {dim: 0.0 for dim in DIMENSIONS}
    total_weight = 0.0
    for material, pct in accord_match["available"].items():
        profile = get_profile(material)
        if not profile:
            continue
        for dim in DIMENSIONS:
            dim_totals[dim] += profile.character.get(dim, 0.0) * pct
        total_weight += pct
    if total_weight == 0:
        return dim_totals
    return {dim: dim_totals[dim] / total_weight for dim in DIMENSIONS}


def _infer_style_profile(accord_match: dict) -> dict:
    text = " ".join(
        [
            accord_match.get("name", ""),
            accord_match.get("target", ""),
            accord_match.get("good_for", ""),
            accord_match.get("use_at", ""),
        ]
    ).lower()

    best_profile = _DEFAULT_STYLE_PROFILE
    best_score = 0
    for profile in _STYLE_PROFILES:
        score = sum(1 for keyword in profile["keywords"] if keyword in text)
        if score > best_score:
            best_score = score
            best_profile = profile
    return best_profile


def _missing_roudnitska_roles(accord_match: dict) -> set[str]:
    roles_covered = set()
    for mat_name in accord_match["available"]:
        roles_covered.update(material_roudnitska_roles(mat_name))
    return {"transparence", "chaleur", "noblesse", "peau", "eclat", "profondeur"} - roles_covered


def _theme_matches(candidate: str, style_profile: dict) -> list[str]:
    candidate_key = candidate.lower()
    return [token for token in style_profile.get("preferred_tokens", ()) if token in candidate_key]


def _score_profile_style_fit(profile, style_profile: dict) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    style_dim_score = sum(
        profile.character.get(dim, 0.0) * weight
        for dim, weight in style_profile.get("dimensions", {}).items()
    )
    if style_dim_score:
        score += style_dim_score * 0.45

    avoid_dim_score = sum(
        profile.character.get(dim, 0.0) * weight
        for dim, weight in style_profile.get("avoid_dimensions", {}).items()
    )
    if avoid_dim_score:
        score -= avoid_dim_score * 0.28

    strong_dims = [dim for dim in DIMENSIONS if profile.character.get(dim, 0.0) >= 5.0]
    if strong_dims:
        reasons.append("/".join(strong_dims[:2]))

    return score, reasons


def _score_gap_filler_candidate(
    candidate: str,
    accord_vector: dict[str, float],
    style_profile: dict,
    target_note: str,
) -> tuple[float, str]:
    profile = get_profile(candidate)
    note = classify_note(candidate)
    score = 0.0
    reasons: list[str] = []

    if note != target_note:
        return -999.0, "wrong note"

    note_weight = style_profile["note_weights"].get(note, 0.0)
    score += note_weight * 3.0
    if note_weight > 0.4:
        reasons.append(f"{style_profile['name']} note-position fit")

    token_matches = _theme_matches(candidate, style_profile)
    if token_matches:
        score += min(3.0, len(token_matches) * 1.25)
        reasons.append("theme match")

    if not profile:
        return score, ", ".join(reasons) if reasons else "gap fill"

    if profile.role in {"bridge", "modifier", "radiance"}:
        score += 1.5
    elif profile.role == "trace":
        score += 0.2
    elif profile.role == "character":
        score += 0.8
    elif profile.role == "fixative":
        score -= 1.0

    similarity = sum(
        min(profile.character.get(dim, 0.0), accord_vector.get(dim, 0.0))
        for dim in DIMENSIONS
    )
    score += similarity * 0.25

    style_score, style_reasons = _score_profile_style_fit(profile, style_profile)
    score += style_score
    reasons.extend(style_reasons)

    return score, ", ".join(reasons) if reasons else "gap fill"


def _score_optimization_candidate(
    candidate: str,
    accord_match: dict,
    missing_roles: set[str],
    accord_vector: dict[str, float],
    style_profile: dict,
) -> tuple[float, str]:
    material = _lookup_material(candidate)
    profile = get_profile(candidate)
    note = classify_note(candidate)
    score = 0.0
    reasons: list[str] = []

    if not _is_creative_material(candidate):
        return -999.0, "non-creative"

    score += style_profile["note_weights"].get(note, 0.0) * 2.0

    token_matches = _theme_matches(candidate, style_profile)
    if token_matches:
        score += min(3.0, len(token_matches) * 1.2)
        reasons.append("theme match")

    matched_roles = sorted(material_roudnitska_roles(candidate) & missing_roles)
    if matched_roles:
        score += 2.0
        reasons.append(f"fills {'/'.join(matched_roles[:2])}")

    if profile:
        if profile.role in {"bridge", "modifier", "radiance"}:
            score += 1.5
        elif profile.role == "character":
            score += 1.0
        elif profile.role == "trace":
            score -= 1.2

        similarity = sum(
            min(profile.character.get(dim, 0.0), accord_vector.get(dim, 0.0))
            for dim in DIMENSIONS
        )
        score += similarity * 0.25

        style_score, style_reasons = _score_profile_style_fit(profile, style_profile)
        score += style_score
        reasons.extend(style_reasons)

    return score, ", ".join(reasons) if reasons else "style fit"


def _build_optimization_inventory(
    accord_match: dict,
    formula: FormulaVector,
    inventory: list[str],
) -> list[str]:
    accord_vector = _accord_character_vector(accord_match)
    style_profile = _infer_style_profile(accord_match)
    missing_roles = _missing_roudnitska_roles(accord_match)
    used = {name.lower() for name in formula.ingredients}

    ranked_candidates: list[tuple[float, str]] = []
    for mat_name in inventory:
        if mat_name.lower() in used:
            continue
        score, _ = _score_optimization_candidate(
            mat_name,
            accord_match,
            missing_roles,
            accord_vector,
            style_profile,
        )
        if score >= 4.0:
            ranked_candidates.append((score, mat_name))

    ranked_candidates.sort(reverse=True)
    return [name for _, name in ranked_candidates[:36]]


def _score_star_candidate(
    candidate: str,
    accord_match: dict,
    missing_roles: set[str],
    accord_vector: dict[str, float],
    style_profile: dict,
    inventory: list[str],
    scorer: FormulaScorer,
) -> tuple[float, str]:
    material = _lookup_material(candidate)
    profile = get_profile(candidate)
    note = classify_note(candidate)
    reasons: list[str] = []
    score = 0.0
    style_note_bonus = style_profile["note_weights"].get(note, 0.0)

    roles = sorted(material_roudnitska_roles(candidate))
    matched_roles = [role for role in roles if role in missing_roles]
    if matched_roles:
        score += 6.0
        reasons.append(f"fills missing {'/'.join(matched_roles[:2])}")
    elif roles:
        score += 1.0
        reasons.append(f"has {'/'.join(roles[:2])} role")

    preferred_note = _preferred_note_for_roles(missing_roles)
    if preferred_note and note == preferred_note and style_note_bonus >= -0.1:
        score += 2.5
        reasons.append(f"preferred {preferred_note} note")
    elif note == "heart":
        score += 1.0

    score += style_note_bonus * 3.0
    if style_note_bonus > 0.4:
        reasons.append(f"{style_profile['name']} note-position fit")
    elif style_note_bonus < -0.4:
        reasons.append(f"{style_profile['name']} note-position penalty")

    token_matches = _theme_matches(candidate, style_profile)
    if token_matches:
        score += min(3.5, len(token_matches) * 1.4)
        reasons.append("theme match")

    if profile:
        if profile.role in {"character", "radiance", "volume"}:
            score += 2.0
            reasons.append(f"{profile.role} role")
        elif profile.role == "bridge":
            score += 0.5
        elif profile.role == "trace":
            score -= 4.0
            reasons.append("trace penalty")

        similarity = sum(
            min(profile.character.get(dim, 0.0), accord_vector.get(dim, 0.0))
            for dim in DIMENSIONS
        )
        score += similarity * 0.35

        complement = sum(
            max(0.0, 3.5 - accord_vector.get(dim, 0.0)) * profile.character.get(dim, 0.0)
            for dim in DIMENSIONS
        )
        score += complement * 0.05

        style_score, style_reasons = _score_profile_style_fit(profile, style_profile)
        score += style_score
        reasons.extend(style_reasons)

    preview_formula = build_accord_formula(candidate, accord_match, inventory)
    preview_scores = scorer.score(preview_formula)
    preview_total = preview_scores["total"]
    score += preview_total * 0.04
    preview_balance = preview_scores.get("balance", 50)
    score += preview_balance * 0.03

    key = candidate.lower().strip()
    for generic_name, penalty in _GENERIC_STAR_PENALTIES.items():
        if generic_name in key:
            score -= penalty
            reasons.append("generic penalty")
            break

    if material and material.get("completeness_pct") is not None:
        score += float(material["completeness_pct"]) / 100.0

    return score, ", ".join(reasons) if reasons else "best overall fit"


def select_star_for_accord(accord_match: dict, inventory: list[str]) -> tuple[str, str]:
    """Select a star material that fills a missing Roudnitska role.

    Prefers materials with theory data; excludes solvents/carriers.
    """
    accord_mats_lower = {m.lower() for m in accord_match["available"]}
    missing_roles = _missing_roudnitska_roles(accord_match)
    accord_vector = _accord_character_vector(accord_match)
    style_profile = _infer_style_profile(accord_match)
    scorer = FormulaScorer()
    ranked_candidates: list[tuple[float, str, str]] = []
    fallback_candidates: list[str] = []

    for mat_name in inventory:
        if mat_name.lower() in accord_mats_lower:
            continue
        if not _is_creative_material(mat_name):
            continue

        fallback_candidates.append(mat_name)
        score, explanation = _score_star_candidate(
            mat_name,
            accord_match,
            missing_roles,
            accord_vector,
            style_profile,
            inventory,
            scorer,
        )
        ranked_candidates.append((score, mat_name, explanation))

    if ranked_candidates:
        ranked_candidates.sort(key=lambda item: item[0], reverse=True)
        _, material_name, explanation = ranked_candidates[0]
        return material_name, explanation

    # Fallback: any creative heart-note material
    for mat_name in fallback_candidates:
        if classify_note(mat_name) == "heart":
            return mat_name, "heart bridge"

    # Last resort
    for mat_name in fallback_candidates:
        return mat_name, "complement"

    return inventory[0], "default"


def build_accord_formula(star: str, accord_match: dict, inventory: list[str]) -> FormulaVector:
    """Build a formula from star + accord, following Carles method."""
    fv = FormulaVector()

    # Star at prominence percentage
    star_note = classify_note(star)
    star_pct = {"top": 5.0, "heart": 12.0, "base": 8.0}.get(star_note, 10.0)
    fv.ingredients[star] = star_pct

    # Add accord at library ratios, scaled to ~55%
    accord_total = sum(accord_match["available"].values())
    target_pct = 55.0
    scale = target_pct / accord_total if accord_total > 0 else 1.0

    for mat, pct in accord_match["available"].items():
        if mat != star:
            fv.ingredients[mat] = round(pct * scale, 1)

    # Fill pyramid gaps
    dist = fv.note_distribution()
    remaining = 100.0 - fv.total_pct
    used = {m.lower() for m in fv.ingredients}
    accord_vector = _accord_character_vector(accord_match)
    style_profile = _infer_style_profile(accord_match)

    if dist.get("heart", 0) < 25 and remaining > 5:
        ranked_heart_fillers: list[tuple[float, str]] = []
        for mat_name in inventory:
            if mat_name.lower() in used or not _is_creative_material(mat_name):
                continue
            score, _ = _score_gap_filler_candidate(
                mat_name,
                accord_vector,
                style_profile,
                target_note="heart",
            )
            ranked_heart_fillers.append((score, mat_name))
        ranked_heart_fillers.sort(reverse=True)
        if ranked_heart_fillers and ranked_heart_fillers[0][0] > -100:
            add = min(6.0, remaining * 0.4)
            chosen = ranked_heart_fillers[0][1]
            fv.ingredients[chosen] = round(add, 1)
            remaining -= add
            used.add(chosen.lower())

    if dist.get("top", 0) < 10 and remaining > 3:
        ranked_top_fillers: list[tuple[float, str]] = []
        for mat_name in inventory:
            if mat_name.lower() in used or not _is_creative_material(mat_name):
                continue
            score, _ = _score_gap_filler_candidate(
                mat_name,
                accord_vector,
                style_profile,
                target_note="top",
            )
            ranked_top_fillers.append((score, mat_name))
        ranked_top_fillers.sort(reverse=True)
        if ranked_top_fillers and ranked_top_fillers[0][0] > -100:
            add = min(4.0, remaining * 0.3)
            chosen = ranked_top_fillers[0][1]
            fv.ingredients[chosen] = round(add, 1)
            remaining -= add

    return fv


def theory_provenance(fv: FormulaVector, inventory: list[str] | None = None) -> dict:
    """Show which book principles are fulfilled."""
    theory = get_theory_rules()

    # Roudnitska roles (using keyword mapping)
    roles = {}
    for name in fv.ingredient_list():
        for role in material_roudnitska_roles(name):
            roles.setdefault(role, []).append(name)

    # Jellinek quadrants
    quads = {}
    jellinek = theory.get("jellinek_map", {}).get("quadrants", {})
    for name in fv.ingredient_list():
        qk = material_jellinek_quadrant_key(name)
        if qk and qk in jellinek:
            qname = jellinek[qk].get("name", qk)
            quads.setdefault(qname, []).append(name)

    # Carles positions
    positions = {"top": [], "heart": [], "base": []}
    for name in fv.ingredient_list():
        positions[classify_note(name)].append(name)

    # SAR classes
    sar = {}
    for name in fv.ingredient_list():
        mat = _lookup_material(name)
        if mat and mat.get("sar_class"):
            sar.setdefault(mat["sar_class"], []).append(name)

    all_roud_roles = ["transparence", "chaleur", "noblesse", "peau", "eclat", "profondeur"]
    roud_roles = theory.get("roudnitska_roles", {}).get("roles", {})
    role_examples = {}
    for role in all_roud_roles:
        info = roud_roles.get(role, {})
        examples = info.get("examples", [])[:3]
        concrete_examples = []
        for example in examples:
            concrete = _concrete_inventory_match(example, inventory)
            if concrete and concrete not in concrete_examples:
                concrete_examples.append(concrete)
        if concrete_examples:
            role_examples[role] = concrete_examples

    return {
        "roudnitska_roles": roles,
        "roudnitska_missing": [r for r in all_roud_roles if r not in roles],
        "roudnitska_examples": role_examples,
        "jellinek_quadrants": quads,
        "carles_distribution": {k: len(v) for k, v in positions.items()},
        "sar_classes": len(sar),
        "sar_detail": sar,
    }


def main():
    print("=" * 70)
    print("ACCORD-FIRST FORMULA DISCOVERY PIPELINE")
    print("Theory drives quality. Synergy is only a bonus.")
    print("=" * 70)

    # ── Phase 1: Load accord library ──
    print("\n▸ Phase 1: Loading accord library...")
    library = get_accord_library()
    print(f"  Parsed {len(library)} accords from perfume_accord_library.txt")
    for acc in library:
        print(f"    • {acc['name']} ({len(acc['ingredients'])} ingredients)")

    # ── Phase 2: Match accords to inventory ──
    print("\n▸ Phase 2: Matching accords to inventory...")
    inventory = load_inventory()
    print(f"  Inventory: {len(inventory)} materials")

    accord_matches = []
    for acc in library:
        match = match_accord_to_inventory(acc, inventory)
        accord_matches.append(match)
        status = "✓ VIABLE" if match["viable"] else "✗ insufficient"
        print(f"    {match['name']}: {match['coverage']:.0f}% coverage "
              f"({len(match['available'])}/{len(acc['ingredients'])} materials) — {status}")
        if match["missing"]:
            print(f"      Missing: {', '.join(match['missing'][:4])}")

    viable = [m for m in accord_matches if m["viable"]]
    print(f"\n  → {len(viable)} viable accords from library")

    if not viable:
        print("  No viable accords found. Check inventory vs accord library.")
        return

    # ── Phase 3: Build formulas (Carles method) ──
    print("\n▸ Phase 3: Building formulas from accords (Carles method)...")
    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    conf_scorer = ConfidenceScorer()

    candidates = []
    for match in viable:
        star, star_role = select_star_for_accord(match, inventory)
        fv = build_accord_formula(star, match, inventory)
        scores = scorer.score(fv)

        candidates.append({
            "accord": match["name"],
            "star": star,
            "star_role": star_role,
            "formula": fv,
            "scores": scores,
            "target": match["target"],
            "good_for": match["good_for"],
        })
        print(f"    {match['name']}: star={star} ({star_role}), "
              f"total={scores['total']:.1f} "
              f"[tex={scores['texture']:.0f} lux={scores['luxury']:.0f} "
              f"syn={scores['synergy']:.0f}]")

    # ── Phase 4: Rank by theory-first scores ──
    print("\n▸ Phase 4: Ranking by theory-first scores...")
    candidates.sort(key=lambda c: c["scores"]["total"], reverse=True)

    for i, c in enumerate(candidates, 1):
        s = c["scores"]
        print(f"  #{i} {c['accord']} (star: {c['star']})")
        print(f"      Total: {s['total']:.1f}  |  Texture: {s['texture']:.1f}  "
              f"Luxury: {s['luxury']:.1f}  Longevity: {s['longevity']:.1f}  "
              f"Sillage: {s['sillage']:.1f}  Synergy: {s['synergy']:.1f}")

    # ── Phase 5: Optimize top formulas ──
    top_n = min(5, len(candidates))
    print(f"\n▸ Phase 5: Optimizing top {top_n} formulas...")
    for i in range(top_n):
        c = candidates[i]
        optimizer = FormulaOptimizer(weights)
        optimizer._inventory = _build_optimization_inventory(
            next(match for match in viable if match["name"] == c["accord"]),
            c["formula"],
            inventory,
        )
        result = optimizer.optimize(c["formula"])
        old_total = c["scores"]["total"]
        new_total = result.total_score
        c["optimized_formula"] = result.formula
        c["optimized_scores"] = result.scores
        c["optimized_total"] = new_total
        c["suggestions"] = result.suggestions
        c["reasoning"] = result.reasoning
        print(f"    {c['accord']}: {old_total:.1f} → {new_total:.1f} "
              f"({new_total - old_total:+.1f})")

    # ── Phase 6: Confidence scoring ──
    print(f"\n▸ Phase 6: Confidence scoring...")
    for i in range(top_n):
        c = candidates[i]
        fv = c.get("optimized_formula", c["formula"])
        conf = conf_scorer.score(fv.ingredients)
        c["confidence"] = conf
        print(f"    {c['accord']}: {conf['confidence_grade']} "
              f"(data={conf['data_confidence']:.0f} "
              f"pairing={conf['pairing_confidence']:.0f} "
              f"overall={conf['overall_confidence']:.0f})")

    # ── Phase 7: Theory provenance ──
    print("\n▸ Phase 7: Theory provenance (which books drive each formula)...")
    for i in range(top_n):
        c = candidates[i]
        fv = c.get("optimized_formula", c["formula"])
        prov = theory_provenance(fv, inventory)
        c["provenance"] = prov
        print(f"\n  {c['accord']}:")
        print(f"    Roudnitska roles: {list(prov['roudnitska_roles'].keys())}")
        if prov["roudnitska_missing"]:
            if prov.get("roudnitska_examples"):
                role_bits = []
                for role in prov["roudnitska_missing"]:
                    examples = prov["roudnitska_examples"].get(role, [])
                    if examples:
                        role_bits.append(f"{role} ({', '.join(examples)})")
                    else:
                        role_bits.append(role)
                print(f"    Missing roles: {role_bits}")
            else:
                print(f"    Missing roles: {prov['roudnitska_missing']}")
        print(f"    Jellinek quadrants: {list(prov['jellinek_quadrants'].keys())}")
        dist = fv.note_distribution()
        print(f"    Carles pyramid: top={dist['top']:.0f}% heart={dist['heart']:.0f}% "
              f"base={dist['base']:.0f}% (target: 20/40/40)")
        print(f"    SAR classes: {prov['sar_classes']}")

    # ── Phase 8: Save results ──
    print("\n▸ Phase 8: Saving results...")
    results_data = []
    for c in candidates[:top_n]:
        fv = c.get("optimized_formula", c["formula"])
        entry = {
            "accord": c["accord"],
            "star": c["star"],
            "star_role": c["star_role"],
            "target": c["target"],
            "good_for": c["good_for"],
            "ingredients": fv.ingredients,
            "scores": c.get("optimized_scores", c["scores"]),
            "original_scores": c["scores"],
            "confidence": c.get("confidence", {}),
            "suggestions": c.get("suggestions", []),
            "theory_provenance": theory_provenance(fv, inventory),
        }
        results_data.append(entry)

    json_path = Path(__file__).parent / "accord_discovery_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, default=str)
    print(f"  → {json_path.name}")

    # Save markdown
    md_path = Path(__file__).parent / "accord_discovery_formulas.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Accord-First Formula Discovery Results\n\n")
        f.write("Built on classical perfumery theory. Synergy is a bonus only.\n\n")
        f.write("## Scoring Weights (Theory-First)\n\n")
        f.write(f"| Axis | Weight | Source |\n")
        f.write(f"|------|--------|--------|\n")
        f.write(f"| Longevity | ×{weights.longevity} | Physical chemistry |\n")
        f.write(f"| Sillage | ×{weights.sillage} | Physical chemistry |\n")
        f.write(f"| Synergy | ×{weights.synergy} | *bonus only* |\n")
        f.write(f"| Luxury | ×{weights.luxury} | Ingredient quality |\n")
        f.write(f"| Texture | ×{weights.texture} | Haptic/sensory |\n")
        f.write(f"| Stacking Depth | ×{weights.stacking_depth} | Structural layering |\n")
        f.write(f"| Skin Performance | ×{weights.skin_performance} | Reservoir kinetics |\n")
        f.write(f"| Hedonic | ×{weights.hedonic} | Intrinsic pleasantness |\n")
        f.write(f"| Perceptual Clarity | ×{weights.perceptual_clarity} | Mixture suppression |\n")
        f.write("\n---\n\n")

        for i, entry in enumerate(results_data, 1):
            s = entry["scores"]
            orig = entry["original_scores"]
            f.write(f"## #{i}: {entry['accord']}\n\n")
            f.write(f"**Star material**: {entry['star']} ({entry['star_role']})\\\n")
            f.write(f"**Target**: {entry['target']}\\\n")
            f.write(f"**Good for**: {entry['good_for']}\n\n")
            f.write(f"**Score**: {orig['total']:.1f} → **{s['total']:.1f}** (optimized)\n\n")

            f.write("| Axis | Score |\n|------|-------|\n")
            for axis in ["longevity", "sillage", "synergy", "luxury", "texture",
                         "stacking_depth", "skin_performance", "hedonic", "perceptual_clarity"]:
                label = axis.replace("_", " ").title()
                f.write(f"| {label} | {s.get(axis, 0):.1f} |\n")

            conf = entry.get("confidence", {})
            if conf:
                f.write(f"\nConfidence: **{conf.get('confidence_grade', 'N/A')}** "
                        f"(overall={conf.get('overall_confidence', 0):.0f})\n")

            f.write("\n### Formula\n\n")
            f.write("| Material | % |\n|----------|---|\n")
            for mat, pct in sorted(entry["ingredients"].items(), key=lambda x: -x[1]):
                f.write(f"| {mat} | {pct:.1f}% |\n")

            prov = entry["theory_provenance"]
            f.write(f"\n### Theory Provenance\n\n")
            f.write(f"- **Roudnitska roles**: {', '.join(prov['roudnitska_roles'].keys()) or 'none'}\n")
            if prov["roudnitska_missing"]:
                missing_lines = []
                for role in prov["roudnitska_missing"]:
                    examples = prov.get("roudnitska_examples", {}).get(role, [])
                    if examples:
                        missing_lines.append(f"{role} ({', '.join(examples)})")
                    else:
                        missing_lines.append(role)
                f.write(f"- **Missing roles**: {', '.join(missing_lines)}\n")
            f.write(f"- **Jellinek quadrants**: {', '.join(prov['jellinek_quadrants'].keys()) or 'none'}\n")
            cd = prov["carles_distribution"]
            f.write(f"- **Carles layers**: top={cd['top']}, heart={cd['heart']}, base={cd['base']} materials\n")
            f.write(f"- **SAR diversity**: {prov['sar_classes']} classes\n")

            if entry.get("suggestions"):
                f.write(f"\n### Suggestions\n\n")
                for sug in entry["suggestions"]:
                    f.write(f"- {sug}\n")

            f.write("\n---\n\n")

    print(f"  → {md_path.name}")
    print(f"\n{'=' * 70}")
    print("COMPLETE — Formulas built from accords, scored by theory.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
