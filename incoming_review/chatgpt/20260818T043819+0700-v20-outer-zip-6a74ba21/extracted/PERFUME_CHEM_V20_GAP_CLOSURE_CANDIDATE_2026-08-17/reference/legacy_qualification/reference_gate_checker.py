
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Z95 = 1.959963984540054

def wilson_interval(successes: int, draws: int, z: float = Z95) -> tuple[float, float]:
    if draws <= 0:
        raise ValueError("draws must be positive")
    p = successes / draws
    denom = 1 + z*z/draws
    center = (p + z*z/(2*draws)) / denom
    margin = z * math.sqrt((p*(1-p)/draws) + z*z/(4*draws*draws)) / denom
    return max(0.0, center-margin), min(1.0, center+margin)

def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    failures: dict[str, list[str]] = {}
    warnings: list[str] = []
    p = payload

    def fail(gate: str, reason: str) -> None:
        failures.setdefault(gate, []).append(reason)

    # G1 inventory and product-basis integrity.
    if p.get("product_basis_fraction_guessed", False):
        fail("G1", "Product-basis active fraction was guessed.")

    # G2 arithmetic and executable dosing.
    if abs(float(p.get("parts_total", 0)) - 1000.0) > 1e-9:
        fail("G2", "Formula does not total exactly 1,000 parts.")
    if int(p.get("direct_sub1_5ml_doses", 0)) > 0:
        fail("G2", "Unresolved direct sub-1 µL dose exists in the 5 mL pilot.")

    # G3 meaningful complexity.
    formula_class = p.get("formula_class", "")
    minimum = 65 if formula_class == "high_complexity_perfume" else 50
    if int(p.get("distinct_odor_materials", 0)) < minimum:
        fail("G3", f"Distinct odor-material count is below {minimum}.")
    if float(p.get("microtexture_ratio", 1.0)) > 0.20:
        fail("G3", "Microtexture ratio exceeds 20%.")
    if p.get("technical_rows_counted", False):
        fail("G3", "Technical rows were counted as odor complexity.")
    if p.get("duplicate_canonical_materials", []):
        fail("G3", "Duplicate canonical materials were counted separately.")

    # G4 functional coverage.
    if int(p.get("sensory_systems", 0)) < 5:
        fail("G4", "Fewer than five sensory systems.")
    if int(p.get("bridge_rows", 0)) < 6:
        fail("G4", "Fewer than six documented bridge rows.")

    # G5 interaction coherence.
    if not p.get("interaction_records_complete", False):
        fail("G5", "Major interaction records are incomplete.")

    # G6 dominance.
    if float(p.get("max_material_share", 1.0)) > 0.22:
        fail("G6", "Single modeled contributor exceeds 22%.")
    if float(p.get("max_wood_block_share", 1.0)) > 0.35:
        fail("G6", "Single wood exceeds 35% of the wood block.")
    if float(p.get("max_musk_block_share", 1.0)) > 0.45:
        fail("G6", "Single musk exceeds 45% of the musk block.")
    if float(p.get("max_amberwood_block_share", 1.0)) > 0.35:
        fail("G6", "Single amberwood exceeds 35% of the amberwood block.")

    # G7 temporal architecture.
    if int(p.get("temporal_phases", 0)) < 3:
        fail("G7", "Fewer than three temporal phases.")

    # G8 Monte Carlo.
    successes = int(p.get("mc_successes", 0))
    draws = int(p.get("mc_draws", 0))
    lower, upper = wilson_interval(successes, draws)
    estimate = successes / draws
    near_threshold = 0.88 <= estimate <= 0.93
    if estimate < 0.90 or lower < 0.90 or near_threshold:
        fail("G8", "Monte Carlo release criterion not closed.")
        if near_threshold:
            warnings.append("100,000-draw independent-seed confirmation required.")

    # G9 ablation.
    if not p.get("ablation_complete", True):
        fail("G9", "Material-by-material ablation is incomplete.")

    # G10 perturbation.
    if not p.get("perturbation_complete", True):
        fail("G10", "Required dose perturbation is incomplete.")

    # G11 anti-collapse.
    if float(p.get("collision_similarity", 1.0)) >= 0.76:
        fail("G11", "Sibling collision similarity is at or above 0.76.")

    # G12 physical chemistry.
    if not p.get("physical_chemistry_complete", False):
        fail("G12", "Physical-chemistry review is incomplete.")

    # G13 evidence and claim integrity.
    if p.get("computed_headspace_labeled_measured", False):
        fail("G13", "Computed headspace was mislabeled as measured.")
    if p.get("strict_oav_without_measured_air", False):
        fail("G13", "Strict OAV was claimed without measured gas-phase concentration.")

    # G14 quality score.
    if float(p.get("quality_score", 0)) < 92:
        fail("G14", "Quality score is below 92.")

    failed = sorted(failures)
    structural = {f"G{i}" for i in range(1,8)} | {"G9", "G10", "G11"}
    if any(g in structural for g in failed):
        state = "REBUILD"
    elif "G13" in failed or "G12" in failed:
        state = "HOLD"
    elif "G8" in failed:
        state = "RERUN REQUIRED"
    elif "G14" in failed:
        state = "CONDITIONAL"
    else:
        state = "COMPUTATIONAL DESIGN PASS"

    canonical = {
        "state": state,
        "failed_gates": failed,
        "failures": failures,
        "warnings": warnings,
        "mc": {
            "successes": successes,
            "draws": draws,
            "estimate": estimate,
            "wilson_95_lower": lower,
            "wilson_95_upper": upper,
            "near_threshold": near_threshold,
        },
    }
    canonical["result_hash"] = hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return canonical
