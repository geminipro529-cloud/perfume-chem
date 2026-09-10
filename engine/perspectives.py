"""Multi-perspective formula evaluation — 5 master perfumer frameworks + science.

Each perspective evaluates a formula through a distinct philosophical lens,
returning a score (0-100) and diagnostic notes. Perspectives:

  1. Roudnitska  — Aesthetic coherence: 6 aesthetic roles, pedigree, noblesse
  2. Ellena      — Transparency index: material economy, diffusion clarity
  3. Laudamiel   — Molecular sculpture: spatial coherence, productive conflict
  4. Carles      — Methodological rigour: pyramid discipline, role enforcement
  5. Boix Camps  — Production viability: stability, solubility, batch consistency

  Science       — Physicochemical validity: VP coverage, reactivity flags,
                   olfactory adaptation awareness, Hansen solubility warnings

References: Roudnitska (1991) L'Esthétique en question;
            Ellena (2007) Le parfum; Laudamiel craft lectures;
            Carles (1961) sequential method; Boix Camps production doctrines.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .ingredient_intelligence import get_profile
from .optimizer.models import FormulaVector, _lookup_material

# ── Material metadata lookups ──────────────────────────────────

# Roudnitska's 6 aesthetic roles mapped to inventory materials
_ROUDNITSKA_ROLE_MAP: dict[str, set[str]] = {
    "transparence": {
        "hedione", "linalool", "linalyl acetate", "dihydromyrcenol",
        "hexyl salicylate", "aldehyde c10", "aldehyde c11",
        "aldehyde c12 mna", "bergamot fcf", "grapefruit fcf",
        "cedrat fcf sicilian", "calone", "floralozone", "scentenal",
        "allyl amyl glycolate", "freesia hdi",
    },
    "chaleur": {
        "vanillin", "benzoin resinoid", "coumarin", "labdanum absolute",
        "tonka bean fo", "maple lactone", "ethyl vanillin",
        "benzyl benzoate", "styrax ftec",
    },
    "noblesse": {
        "rose absolute", "neroli eo", "jasmine fo", "ylang comoros complete eo",
        "ylang comoros iii eo", "alpha irone", "orris ftec", "i-iris ftec",
        "orivone", "ultralia", "iris root ftec", "tuberose absolute",
    },
    "peau": {
        "iso e super", "benzyl salicylate", "hexyl salicylate",
        "galaxolide", "habanolide", "cashmeran", "ambrox super",
        "javanol", "ebanol", "musk t",
    },
    "eclat": {
        "bergamot fcf", "bergamot fcf sicilian", "blood orange sicilian",
        "grapefruit fcf", "red mandarin eo", "d-limonene", "citral",
        "citronellal", "neroli eo", "petitgrain eo", "cedrat fcf sicilian",
        "methyl pamplemousse",
    },
    "profondeur": {
        "patchouli eo", "vetiver eo", "myrrh eo", "evernyl",
        "cedarwood atlas eo", "cedarwood virginia eo", "sandalwood eo",
        "oud oil", "labdanum absolute", "guaiacol", "isobutyl quinoline",
        "birch tar rectified", "kephalis", "vertofix coeur",
        "amberwood f", "vetival",
    },
}

# Ellena: materials classified as transparent vs opaque
_TRANSPARENT_MATERIALS: set[str] = {
    "hedione", "iso e super", "linalool", "linalyl acetate",
    "bergamot fcf", "grapefruit fcf", "cedrat fcf sicilian",
    "dihydromyrcenol", "hexyl salicylate", "habanolide",
    "galaxolide", "allyl amyl glycolate", "calone", "floralozone",
    "scentenal", "freesia hdi", "amberwood f",
}

_OPAQUE_MATERIALS: set[str] = {
    "patchouli eo", "rose absolute", "labdanum absolute",
    "benzoin resinoid", "myrrh eo", "sandalwood eo",
    "vetiver eo", "vanillin", "styrax ftec",
    "ylang comoros complete eo", "birch tar rectified",
    "guaiacol", "indole",
}

# Laudamiel: molecular isolation levels (10 = pure synthetic, 1 = complex natural blend)
_ISOLATION_LEVELS: dict[str, int] = {
    # Pure molecules = 10
    "hedione": 10, "iso e super": 10, "linalool": 10, "geraniol": 10,
    "vanillin": 10, "coumarin": 10, "galaxolide": 10, "habanolide": 10,
    "benzyl salicylate": 10, "hexyl salicylate": 10, "dihydromyrcenol": 10,
    "ambrox super": 10, "cashmeran": 10, "javanol": 10, "ebanol": 10,
    "kephalis": 10, "vertofix coeur": 10, "evernyl": 10,
    "phenethyl alcohol": 10, "hydroxycitronellal": 10,
    "indole": 10, "guaiacol": 10, "eugenol": 10,
    "allyl amyl glycolate": 10, "calone": 10, "floralozone": 10,
    "scentenal": 10, "dynascone": 10, "cyclamen aldehyde": 10,
    "ethyl safranate": 10, "dbca": 10, "paradisamide": 10,
    "lilyreal nd": 10, "bourgeonal": 10, "orivone": 10,
    "ultralia": 10, "suederal": 10, "timberol": 10, "koavone": 10,
    "cedramber": 10, "amberwood f": 10, "vetival": 10,
    "isobutyl quinoline": 10, "musk t": 10,
    # FTECs / accords = 3-5
    "orris ftec": 4, "i-iris ftec": 4, "iris root ftec": 4,
    "styrax ftec": 4, "cardamom ftec": 4,
    # Natural EOs = 2-3 (hundreds of molecules)
    "bergamot fcf": 3, "bergamot fcf sicilian": 3,
    "grapefruit fcf": 3, "blood orange sicilian": 3,
    "red mandarin eo": 2, "neroli eo": 2, "petitgrain eo": 2,
    "lavender eo": 2, "clary sage eo": 2, "cedarwood atlas eo": 2,
    "cedarwood virginia eo": 2, "patchouli eo": 2, "vetiver eo": 2,
    "sandalwood eo": 2, "myrrh eo": 2, "carrot seed eo": 2,
    "ylang comoros complete eo": 2, "ylang comoros iii eo": 2,
    # Absolutes / naturals = 1-2
    "rose absolute": 1, "labdanum absolute": 1, "benzoin resinoid": 1,
    "birch tar rectified": 2,
    # Fragrance oils = 1-3
    "jasmine fo": 1, "tonka bean fo": 1,
}

# Boix Camps: batch variability percentages (higher = less consistent)
_BATCH_VARIABILITY: dict[str, float] = {
    # Synthetics: very consistent
    "iso e super": 0.5, "hedione": 0.5, "galaxolide": 0.5,
    "habanolide": 0.5, "benzyl salicylate": 0.5, "vanillin": 0.5,
    "coumarin": 0.5, "dihydromyrcenol": 0.5, "linalool": 1.0,
    "geraniol": 1.0, "ambrox super": 0.5, "cashmeran": 0.5,
    # FCF citrus: standardised
    "bergamot fcf": 3.0, "grapefruit fcf": 3.0,
    "cedrat fcf sicilian": 3.0, "bergamot fcf sicilian": 3.0,
    # Raw EOs: moderate to high variability
    "blood orange sicilian": 8.0, "red mandarin eo": 8.0,
    "neroli eo": 10.0, "lavender eo": 5.0, "patchouli eo": 7.0,
    "vetiver eo": 8.0, "sandalwood eo": 12.0,
    "cedarwood atlas eo": 5.0, "cedarwood virginia eo": 5.0,
    "ylang comoros complete eo": 10.0, "ylang comoros iii eo": 8.0,
    "clary sage eo": 6.0, "myrrh eo": 10.0, "carrot seed eo": 7.0,
    # Absolutes: high variability
    "rose absolute": 15.0, "labdanum absolute": 12.0,
    "benzoin resinoid": 8.0, "birch tar rectified": 10.0,
    # FOs: vendor-dependent
    "jasmine fo": 5.0, "tonka bean fo": 5.0,
}

# Stability: approximate shelf-life in years
_SHELF_LIFE_YEARS: dict[str, float] = {
    "iso e super": 10, "hedione": 10, "galaxolide": 10,
    "benzyl salicylate": 10, "hexyl salicylate": 10,
    "vanillin": 8, "coumarin": 8, "ambrox super": 10,
    "dihydromyrcenol": 5, "linalool": 3, "geraniol": 3,
    "d-limonene": 1, "citral": 2, "citronellal": 3,
    "bergamot fcf": 3, "neroli eo": 1.5, "lavender eo": 3,
    "patchouli eo": 5, "vetiver eo": 5, "cedarwood atlas eo": 5,
    "rose absolute": 3, "labdanum absolute": 5,
    "benzoin resinoid": 5, "sandalwood eo": 5,
}

# Olfactory adaptation timescales (minutes to significant anosmia)
_ADAPTATION_TIMESCALE: dict[str, float] = {
    "iso e super": 12, "galaxolide": 25, "cashmeran": 22,
    "habanolide": 28, "coumarin": 35, "ambrox super": 30,
    "musk t": 20, "benzyl salicylate": 40,
    # Florals/citrus: slow or minimal adaptation
    "hedione": 180, "linalool": 120, "bergamot fcf": 90,
    "rose absolute": 60,
}


# ── Helper functions ───────────────────────────────────────────

def _key(name: str) -> str:
    """Normalise material name for lookup."""
    return re.sub(r"\s*\(.*?\)", "", name).strip().lower()


def _roudnitska_roles(name: str) -> set[str]:
    k = _key(name)
    return {role for role, mats in _ROUDNITSKA_ROLE_MAP.items() if k in mats}


def _pct_map(fv: FormulaVector) -> dict[str, float]:
    """Return {normalised_key: effective_pct} for the formula."""
    eff = fv.effective_ingredients()
    return {_key(n): p for n, p in eff.items()}


# ── Individual perspective evaluations ─────────────────────────

@dataclass
class PerspectiveResult:
    """Result of one perspective evaluation."""
    perspective: str
    score: float                  # 0-100
    diagnostics: list[str] = field(default_factory=list)
    sub_scores: dict[str, float] = field(default_factory=dict)


def evaluate_roudnitska(fv: FormulaVector) -> PerspectiveResult:
    """Roudnitska Aesthetic Coherence (0-100).

    Sub-scores:
      role_coverage (40)  — how many of 6 aesthetic roles are filled
      pedigree (20)       — proportion of materials with "noblesse" pedigree
      ratio_balance (20)  — transparence 15-35%, noblesse 5-20%, peau 20-40%
      aesthetic_tension (20) — productive tension between roles (not monocolor)
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    names = list(pcts.keys())

    # 1. Role coverage (40 pts) — aim for 4-6 roles
    roles_filled: dict[str, float] = {}
    for n in names:
        for role in _roudnitska_roles(n):
            roles_filled.setdefault(role, 0.0)
            roles_filled[role] += pcts.get(n, 0)
    n_roles = len(roles_filled)
    role_pts = min(round(40 * (1 - (1 - n_roles / 6) ** 1.5)), 40) if n_roles > 0 else 0
    diag.append(f"roles filled: {n_roles}/6 ({', '.join(sorted(roles_filled))})")

    # 2. Noblesse pedigree (20 pts)
    noblesse_mats = _ROUDNITSKA_ROLE_MAP.get("noblesse", set())
    noblesse_pct = sum(pcts.get(n, 0) for n in names if n in noblesse_mats)
    total_pct = sum(pcts.values()) or 1
    noblesse_ratio = noblesse_pct / total_pct
    # Optimal: 5-20% noblesse
    if 0.05 <= noblesse_ratio <= 0.20:
        ped_pts = 20
    elif noblesse_ratio > 0:
        ped_pts = round(20 * min(noblesse_ratio / 0.05, 1.0))
    else:
        ped_pts = 0
        diag.append("no noblesse materials present")

    # 3. Aesthetic ratio balance (20 pts)
    role_ratios = {r: v / total_pct for r, v in roles_filled.items()}
    ratio_pts = 0
    targets = {"transparence": (0.15, 0.35), "peau": (0.20, 0.40), "eclat": (0.05, 0.25)}
    for role, (lo, hi) in targets.items():
        actual = role_ratios.get(role, 0)
        if lo <= actual <= hi:
            ratio_pts += 7
        elif actual > 0:
            ratio_pts += 3
    ratio_pts = min(ratio_pts, 20)

    # 4. Aesthetic tension (20 pts) — reward 2-3 contrasting role pairs
    contrasts = [
        ("transparence", "profondeur"), ("eclat", "chaleur"),
        ("noblesse", "peau"),
    ]
    tension_pts = 0
    for a, b in contrasts:
        if a in roles_filled and b in roles_filled:
            tension_pts += 7
    tension_pts = min(tension_pts, 20)
    if tension_pts == 0:
        diag.append("monocolor aesthetic: no contrasting role pairs")

    total = role_pts + ped_pts + ratio_pts + tension_pts
    return PerspectiveResult(
        perspective="roudnitska",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "role_coverage": role_pts,
            "pedigree": ped_pts,
            "ratio_balance": ratio_pts,
            "aesthetic_tension": tension_pts,
        },
    )


def evaluate_ellena(fv: FormulaVector) -> PerspectiveResult:
    """Ellena Transparency Index (0-100).

    Sub-scores:
      transparency_ratio (30) — proportion of transparent vs opaque materials
      material_economy (25)   — fewer materials = higher score (ideal 5-12)
      hedione_centrality (20) — Hedione at 15-50% of concentrate = ideal
      diffusion_efficiency (25) — diffusive materials dominate the formula
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    names = list(pcts.keys())
    total_pct = sum(pcts.values()) or 1

    # 1. Transparency ratio (30 pts)
    trans_pct = sum(pcts[n] for n in names if n in _TRANSPARENT_MATERIALS)
    opaque_pct = sum(pcts[n] for n in names if n in _OPAQUE_MATERIALS)
    trans_ratio = trans_pct / total_pct
    if trans_ratio >= 0.60:
        trans_pts = 30
    elif trans_ratio >= 0.40:
        trans_pts = round(30 * (trans_ratio - 0.20) / 0.40)
    else:
        trans_pts = round(30 * max(trans_ratio, 0) / 0.40)
    diag.append(f"transparent {trans_ratio:.0%} | opaque {opaque_pct / total_pct:.0%}")

    # 2. Material economy (25 pts) — Ellena uses 5-12 materials
    n_mats = len(pcts)
    if 5 <= n_mats <= 12:
        econ_pts = 25
    elif n_mats <= 15:
        econ_pts = 15
    elif n_mats <= 20:
        econ_pts = 8
    else:
        econ_pts = 0
        diag.append(f"Ellena: {n_mats} materials is too many (ideal 5-12)")

    # 3. Hedione centrality (20 pts)
    hed_pct = pcts.get("hedione", 0)
    hed_ratio = hed_pct / total_pct
    if 0.15 <= hed_ratio <= 0.50:
        hed_pts = 20
    elif 0.05 <= hed_ratio < 0.15:
        hed_pts = 10
    elif hed_ratio > 0:
        hed_pts = 5
    else:
        hed_pts = 0
        diag.append("no Hedione: Ellena's transparency hero absent")

    # 4. Diffusion efficiency (25 pts) — high VP / high radiance materials
    diffusive = 0
    for n in names:
        prof = get_profile(n)
        if prof and prof.numeric_character is not None:
            rad = prof.numeric_character.get("radiance", 0)
            fresh = prof.numeric_character.get("freshness", 0)
            if rad >= 6 or fresh >= 6:
                diffusive += pcts[n]
        elif n in _TRANSPARENT_MATERIALS:
            diffusive += pcts[n]
    diff_ratio = diffusive / total_pct
    diff_pts = round(25 * min(diff_ratio / 0.50, 1.0))

    total = trans_pts + econ_pts + hed_pts + diff_pts
    return PerspectiveResult(
        perspective="ellena",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "transparency_ratio": trans_pts,
            "material_economy": econ_pts,
            "hedione_centrality": hed_pts,
            "diffusion_efficiency": diff_pts,
        },
    )


def evaluate_laudamiel(fv: FormulaVector) -> PerspectiveResult:
    """Laudamiel Molecular Sculpture Index (0-100).

    Sub-scores:
      molecular_isolation (25) — pure synthetics vs blends/naturals
      spatial_narrative (25)   — materials span top→mid→base position journey
      productive_conflict (25) — intentionally contrasting pairings
      novelty (25)             — unusual material combinations
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    names = list(pcts.keys())
    total_pct = sum(pcts.values()) or 1

    # 1. Molecular isolation (25 pts)
    weighted_iso = 0
    for n in names:
        lvl = _ISOLATION_LEVELS.get(n, 5)
        weighted_iso += lvl * pcts[n]
    avg_iso = weighted_iso / total_pct if total_pct else 5
    iso_pts = round(25 * min(avg_iso / 10, 1.0))
    diag.append(f"avg molecular isolation: {avg_iso:.1f}/10")

    # 2. Spatial narrative (25 pts) — materials should span note positions
    note_layers: dict[str, float] = {"top": 0, "heart": 0, "base": 0}
    for n in names:
        prof = get_profile(n)
        if prof:
            note_layers[prof.note] = note_layers.get(prof.note, 0) + pcts[n]
        else:
            mat = _lookup_material(n)
            if mat:
                pos = (mat.get("carles_position") or "").lower()
                if "top" in pos:
                    note_layers["top"] += pcts[n]
                elif "heart" in pos or "mid" in pos:
                    note_layers["heart"] += pcts[n]
                else:
                    note_layers["base"] += pcts[n]
    filled = sum(1 for v in note_layers.values() if v > 2)
    spat_pts = {0: 0, 1: 8, 2: 17, 3: 25}[min(filled, 3)]

    # 3. Productive conflict (25 pts) — contrasting families co-existing
    conflict_pairs = [
        ({"green", "galbanum", "dynascone", "parmavert"},
         {"vanillin", "benzoin resinoid", "tonka bean fo", "maple lactone"}),
        ({"iso e super", "cashmeran", "ambrox super"},
         {"birch tar rectified", "guaiacol", "styrax ftec"}),
        ({"aldehydes", "aldehyde c10", "aldehyde c11", "aldehyde c12 mna"},
         {"indole", "isobutyl quinoline"}),
        ({"calone", "floralozone", "scentenal"},
         {"patchouli eo", "labdanum absolute", "myrrh eo"}),
    ]
    name_set = set(names)
    conflicts_found = 0
    for group_a, group_b in conflict_pairs:
        if name_set & group_a and name_set & group_b:
            conflicts_found += 1
    conf_pts = min(conflicts_found * 8, 25)
    if conflicts_found == 0:
        diag.append("Laudamiel: no productive chemical conflicts detected")

    # 4. Novelty (25 pts) — materials from rarely-combined olfactive families
    families_present: set[str] = set()
    for n in names:
        prof = get_profile(n)
        if prof and prof.numeric_character is not None:
            # Use highest-scoring character dimensions as "family"
            top_dims = sorted(
                prof.numeric_character.items(), key=lambda x: x[1], reverse=True
            )[:2]
            for dim, val in top_dims:
                if val >= 5:
                    families_present.add(dim)
    # Novelty = number of distinct families (>5 = unusual breadth)
    nov_pts = min(len(families_present) * 4, 25)

    total = iso_pts + spat_pts + conf_pts + nov_pts
    return PerspectiveResult(
        perspective="laudamiel",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "molecular_isolation": iso_pts,
            "spatial_narrative": spat_pts,
            "productive_conflict": conf_pts,
            "novelty": nov_pts,
        },
    )


def evaluate_carles(fv: FormulaVector) -> PerspectiveResult:
    """Carles Methodological Rigour (0-100).

    Sub-scores:
      pyramid_discipline (30) — top 10-30%, heart 25-50%, base 30-55%
      role_enforcement (25)   — character material ≥ 30% of its note layer
      star_dominance (20)     — clear star ingredient (≥1.5× average)
      ingredient_count (15)   — 5-12 ingredients ideal
      tenacity_spectrum (10)  — top/heart/base layers all present
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    total_pct = sum(pcts.values()) or 1

    # Build note distribution
    note_pcts: dict[str, float] = {"top": 0, "heart": 0, "base": 0}
    for n, p in pcts.items():
        prof = get_profile(n)
        if prof:
            note_pcts[prof.note] += p
        else:
            mat = _lookup_material(n)
            pos = (mat.get("carles_position", "") if mat else "").lower()
            if "top" in pos:
                note_pcts["top"] += p
            elif "heart" in pos or "mid" in pos:
                note_pcts["heart"] += p
            else:
                note_pcts["base"] += p

    note_ratios = {k: v / total_pct for k, v in note_pcts.items()}

    # 1. Pyramid discipline (30 pts)
    pyr_pts = 0
    targets = {"top": (0.10, 0.30), "heart": (0.25, 0.50), "base": (0.30, 0.55)}
    for layer, (lo, hi) in targets.items():
        actual = note_ratios.get(layer, 0)
        if lo <= actual <= hi:
            pyr_pts += 10
        elif actual > 0:
            pyr_pts += 4
            diag.append(
                f"Carles: {layer} at {actual:.0%} "
                f"(ideal {lo:.0%}-{hi:.0%})"
            )
    pyr_pts = min(pyr_pts, 30)

    # 2. Role enforcement (25 pts) — character material should dominate its note
    role_pts = 0
    for n, p in pcts.items():
        prof = get_profile(n)
        if prof and prof.role == "character":
            note = prof.note
            layer_total = note_pcts.get(note, 0) or 1
            char_ratio = p / layer_total
            if char_ratio >= 0.30:
                role_pts += 13
            elif char_ratio >= 0.15:
                role_pts += 6
                diag.append(f"Carles: {n} is character but only {char_ratio:.0%} of {note}")
    role_pts = min(role_pts, 25)
    if role_pts == 0:
        diag.append("Carles: no character-role materials identified")

    # 3. Star dominance (20 pts)
    star_pts = 0
    if pcts:
        max_pct = max(pcts.values())
        avg_pct = sum(pcts.values()) / len(pcts)
        if max_pct >= avg_pct * 2.0:
            star_pts = 20
        elif max_pct >= avg_pct * 1.5:
            star_pts = 14
        elif max_pct >= avg_pct * 1.2:
            star_pts = 8
        else:
            diag.append("Carles: no clear star ingredient (all materials at similar %)")

    # 4. Ingredient count (15 pts)
    # Original 5-12 range was for standalone accords.  Full EDP formulas
    # legitimately use 25-80 materials (Roudnitska: "A perfume is not a
    # recipe of 5 ingredients").  Niche standard: 25-60, haute: 60-80+.
    # Penalise only <3 (too simple) or >100 (truly excessive).
    n_mats = len(pcts)
    if 5 <= n_mats <= 80:
        count_pts = 15           # professional range: 5-80 all valid
    elif 3 <= n_mats < 5:
        count_pts = 10           # lean but viable
    elif 80 < n_mats <= 100:
        count_pts = 10           # complex but defensible
    elif n_mats > 100:
        count_pts = 5
        diag.append(f"Carles: {n_mats} ingredients — extreme complexity")
    else:
        count_pts = 5
        diag.append(f"Carles: {n_mats} ingredients — very minimal")

    # 5. Tenacity spectrum (10 pts)
    ten_layers = set(k for k, v in note_ratios.items() if v > 0.05)
    ten_pts = min(len(ten_layers) * 3, 10)

    total = pyr_pts + role_pts + star_pts + count_pts + ten_pts
    return PerspectiveResult(
        perspective="carles",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "pyramid_discipline": pyr_pts,
            "role_enforcement": role_pts,
            "star_dominance": star_pts,
            "ingredient_count": count_pts,
            "tenacity_spectrum": ten_pts,
        },
    )


def evaluate_boix_camps(fv: FormulaVector) -> PerspectiveResult:
    """Boix Camps Production Viability (0-100).

    Sub-scores:
      batch_consistency (30) — low-variability materials preferred
      stability (30)         — shelf-life of weakest-link material
      material_simplicity (20) — readily available, non-exotic materials
      adaptation_risk (20)   — anosmia-prone materials flagged
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    names = list(pcts.keys())
    total_pct = sum(pcts.values()) or 1

    # 1. Batch consistency (30 pts)
    weighted_var = 0
    for n in names:
        var = _BATCH_VARIABILITY.get(n, 5.0)
        weighted_var += var * pcts[n]
    avg_var = weighted_var / total_pct if total_pct else 5
    # <3% avg = perfect, >10% = poor
    if avg_var <= 3:
        batch_pts = 30
    elif avg_var <= 6:
        batch_pts = round(30 * (1 - (avg_var - 3) / 7))
    else:
        batch_pts = max(0, round(30 * (1 - (avg_var - 3) / 12)))
    diag.append(f"avg batch variability: {avg_var:.1f}%")

    # 2. Stability (30 pts) — weakest link determines shelf life
    min_life = 10.0
    weakest = ""
    for n in names:
        if pcts[n] > 1:  # only consider materials > 1% of formula
            life = _SHELF_LIFE_YEARS.get(n, 5.0)
            if life < min_life:
                min_life = life
                weakest = n
    if min_life >= 5:
        stab_pts = 30
    elif min_life >= 3:
        stab_pts = 20
    elif min_life >= 1.5:
        stab_pts = 10
        diag.append(f"shelf-life limited by {weakest} ({min_life:.1f}yr)")
    else:
        stab_pts = 0
        diag.append(f"WARNING: {weakest} limits shelf-life to {min_life:.1f}yr")

    # 3. Material simplicity (20 pts) — synthetic/FCF preferred
    iso_sum = 0
    for n in names:
        iso_sum += _ISOLATION_LEVELS.get(n, 5) * pcts[n]
    avg_iso = iso_sum / total_pct if total_pct else 5
    simp_pts = round(20 * min(avg_iso / 10, 1.0))

    # 4. Adaptation risk (20 pts) — materials that cause rapid anosmia
    rapid_adapt = 0
    for n in names:
        tau = _ADAPTATION_TIMESCALE.get(n)
        if tau is not None and tau <= 30 and pcts[n] > 2:
            rapid_adapt += pcts[n]
            diag.append(f"{n}: anosmia risk ({tau}min) at {pcts[n]:.1f}%")
    adapt_ratio = rapid_adapt / total_pct
    if adapt_ratio <= 0.10:
        adapt_pts = 20
    elif adapt_ratio <= 0.30:
        adapt_pts = 12
    elif adapt_ratio <= 0.50:
        adapt_pts = 5
    else:
        adapt_pts = 0

    total = batch_pts + stab_pts + simp_pts + adapt_pts
    return PerspectiveResult(
        perspective="boix_camps",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "batch_consistency": batch_pts,
            "stability": stab_pts,
            "material_simplicity": simp_pts,
            "adaptation_risk": adapt_pts,
        },
    )


def evaluate_science(fv: FormulaVector) -> PerspectiveResult:
    """Scientific Physicochemical Validity (0-100).

    Sub-scores:
      data_coverage (25)      — % of materials with complete VP/MW/ODT data
      reactivity_safety (25)  — no dangerous aldehyde+amine Schiff base pairs
      vp_spread (25)          — proper volatility gradient (top→base)
      terpene_stability (25)  — oxidation-prone terpenes controlled
    """
    diag: list[str] = []
    pcts = _pct_map(fv)
    names = list(pcts.keys())
    total_pct = sum(pcts.values()) or 1

    # 1. Data coverage (25 pts)
    covered = 0
    for n in names:
        mat = _lookup_material(n)
        if mat and mat.get("mw") and mat.get("vp") is not None:
            covered += 1
    cov_ratio = covered / len(names) if names else 0
    cov_pts = round(25 * cov_ratio)
    if cov_ratio < 0.70:
        diag.append(f"data gap: only {covered}/{len(names)} materials have VP+MW")

    # 2. Reactivity safety (25 pts)
    react_pts = 25
    aldehydes = {n for n in names if any(k in n for k in ("aldehyde", "citral", "citronellal", "hydroxycitronellal", "florol", "cyclamen"))}
    amines = {n for n in names if any(k in n for k in ("indole", "methyl anthranilate"))}
    if aldehydes and amines:
        # Schiff base formation risk
        ald_pct = sum(pcts[a] for a in aldehydes)
        amine_pct = sum(pcts[a] for a in amines)
        if ald_pct > 1 and amine_pct > 0.5:
            react_pts = 10
            diag.append(
                f"Schiff base risk: {', '.join(aldehydes)} + "
                f"{', '.join(amines)} — possible yellowing / odor shift"
            )
        elif aldehydes and amines:
            react_pts = 18
            diag.append("aldehyde+amine present: minor Schiff base concern at trace levels")

    # 3. VP spread (25 pts) — should have materials spanning 3+ decades of VP
    vps: list[float] = []
    for n in names:
        mat = _lookup_material(n)
        if mat and mat.get("vp") is not None:
            vp_val = mat["vp"]
            if isinstance(vp_val, (int, float)) and vp_val > 0:
                vps.append(vp_val)
    if len(vps) >= 3:
        vp_range = math.log10(max(vps) / min(vps)) if min(vps) > 0 else 0
        # 3 decades = excellent, 1 = poor
        spread_pts = min(round(25 * vp_range / 3), 25)
        diag.append(f"VP range: {vp_range:.1f} decades")
    else:
        spread_pts = 5
        diag.append("insufficient VP data for spread analysis")

    # 4. Terpene oxidation risk (25 pts)
    terp_pts = 25
    oxidation_prone = {"d-limonene", "linalool", "geraniol", "citral",
                       "citronellal", "bergamot fcf"}  # bergamot has ~50% limonene
    risky_total = 0
    for n in names:
        if n in oxidation_prone:
            risky_total += pcts[n]
    risky_ratio = risky_total / total_pct
    if risky_ratio > 0.20:
        terp_pts = 5
        diag.append(f"HIGH oxidation risk: {risky_ratio:.0%} terpene-prone materials")
    elif risky_ratio > 0.10:
        terp_pts = 15
        diag.append(f"moderate oxidation risk: {risky_ratio:.0%} terpene-prone")
    elif risky_ratio > 0:
        terp_pts = 22

    total = cov_pts + react_pts + spread_pts + terp_pts
    return PerspectiveResult(
        perspective="science",
        score=min(total, 100),
        diagnostics=diag,
        sub_scores={
            "data_coverage": cov_pts,
            "reactivity_safety": react_pts,
            "vp_spread": spread_pts,
            "terpene_stability": terp_pts,
        },
    )


# ── Combined evaluation ───────────────────────────────────────

@dataclass
class MultiPerspectiveReport:
    """Complete evaluation across all 6 perspectives."""
    formula_name: str
    perspectives: list[PerspectiveResult]
    composite_score: float      # weighted average
    consensus_notes: list[str]  # cross-perspective insights

    def summary_table(self) -> str:
        """Human-readable perspective comparison table."""
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            f"║  MULTI-PERSPECTIVE REPORT: {self.formula_name:<25s} ║",
            "╠══════════════════════════════════════════════════════╣",
            f"║  {'Perspective':<16s} │ {'Score':>5s} │ {'Key Insight':<25s} ║",
            "╠──────────────────┼───────┼───────────────────────────╣",
        ]
        for p in self.perspectives:
            insight = p.diagnostics[0][:25] if p.diagnostics else ""
            lines.append(
                f"║  {p.perspective:<16s} │ {p.score:5.1f} │ {insight:<25s} ║"
            )
        lines.append("╠══════════════════════════════════════════════════════╣")
        lines.append(f"║  {'COMPOSITE':16s} │ {self.composite_score:5.1f} │                           ║")
        lines.append("╚══════════════════════════════════════════════════════╝")
        if self.consensus_notes:
            lines.append("")
            lines.append("CONSENSUS NOTES:")
            for note in self.consensus_notes:
                lines.append(f"  • {note}")
        return "\n".join(lines)


def evaluate_all_perspectives(
    fv: FormulaVector,
    formula_name: str = "unnamed",
    *,
    weights: dict[str, float] | None = None,
) -> MultiPerspectiveReport:
    """Run all 6 perspective evaluations and produce a composite report.

    Default weights: equal (1/6 each). Override with a dict like
    {"roudnitska": 0.25, "ellena": 0.15, ...}.
    """
    evaluators = {
        "roudnitska": evaluate_roudnitska,
        "ellena": evaluate_ellena,
        "laudamiel": evaluate_laudamiel,
        "carles": evaluate_carles,
        "boix_camps": evaluate_boix_camps,
        "science": evaluate_science,
    }

    w = weights or {k: 1 / len(evaluators) for k in evaluators}
    w_total = sum(w.values()) or 1

    results: list[PerspectiveResult] = []
    for name, func in evaluators.items():
        results.append(func(fv))

    composite = sum(
        r.score * w.get(r.perspective, 1 / len(evaluators))
        for r in results
    ) / w_total

    # Cross-perspective consensus analysis
    consensus: list[str] = []
    scores = {r.perspective: r.score for r in results}

    # Identify strongest and weakest perspectives
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    worst = min(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] - scores[worst] > 30:
        consensus.append(
            f"Large gap: {best} ({scores[best]:.0f}) vs "
            f"{worst} ({scores[worst]:.0f}) — formula favours one philosophy"
        )

    # Artistic vs production tension
    artistic_avg = (scores.get("roudnitska", 50) + scores.get("laudamiel", 50)) / 2
    practical_avg = (scores.get("boix_camps", 50) + scores.get("science", 50)) / 2
    if artistic_avg > practical_avg + 20:
        consensus.append("artistically ambitious but production-risk concerns")
    elif practical_avg > artistic_avg + 20:
        consensus.append("production-safe but artistically conservative")

    # Material economy vs complexity tension
    ellena_s = scores.get("ellena", 50)
    laudamiel_s = scores.get("laudamiel", 50)
    if ellena_s >= 70 and laudamiel_s >= 70:
        consensus.append("rare: both transparent AND sculpturally complex")
    elif ellena_s < 40 and laudamiel_s < 40:
        consensus.append("formula lacks both clarity and sculptural intent")

    return MultiPerspectiveReport(
        formula_name=formula_name,
        perspectives=results,
        composite_score=round(composite, 1),
        consensus_notes=consensus,
    )
