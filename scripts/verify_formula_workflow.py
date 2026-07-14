"""Standalone formula verification harness.

Creates a self-contained verification bundle for an existing formula without
integrating into the main pipeline. The bundle includes:

1. Predicted technical scores and star ratings
2. Character radar and confidence report
3. Mixing protocol and chemistry interaction notes
4. Wear-test templates for capturing observed results later

Usage examples:
    python scripts/verify_formula_workflow.py --formula-file luxury_formulas_2026-03-26.md --formula 1
    python scripts/verify_formula_workflow.py --formula-file luxury_formulas_2026-03-26.md --name "Iris Imperiale"
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.confidence import ConfidenceScorer
from engine.chemical_data_validator import blocked_reason
from engine.chemical_life_graph import build_chemical_life_graph
from engine.fingerprint import fingerprint_formula, find_similar_materials
from engine.formula_rating import compute_star_ratings
from engine.formula_recommendations import (
    generate_intervention_recommendations,
    generate_recommendations,
    load_inventory,
)
from engine.mixer.instructions import InstructionGenerator
from engine.mixer.prebonding import PreBondingAnalyzer
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import FormulaVector
from engine.synergy_graph import SynergyGraph
from engine.volatility import VolatilityCurveSimulator


OUTPUT_ROOT = PROJECT_ROOT / "verification_runs"
DEFAULT_BATCH_VOLUME_ML = 30.0

SCORE_AXES = [
    "geometric_total",
    "arithmetic_total",
    "longevity",
    "sillage",
    "balance",
    "theory",
    "radiance",
    "texture",
    "complexity",
    "character_balance",
    "synergy",
    "cost",
]

WEAR_TEST_AXES = [
    ("opening", "Opening"),
    ("heart", "Heart"),
    ("drydown", "Drydown"),
    ("longevity", "Longevity"),
    ("projection", "Projection"),
    ("balance", "Balance"),
    ("overall", "Overall"),
]

INTERVENTION_PHASES = [
    {
        "key": "pre_mix",
        "title": "Pre-Mix Recommendations",
        "context": "Use before combining ingredients or before building the next batch. Focus on prebonding, dissolution, and safety checks.",
        "observation_tags": ["pre_mix", "compatibility", "dissolution", "safety"],
        "template": [
            "Confirm any must-prebond pairs before combining the concentrate.",
            "Resolve crystalline or stubborn materials before they reach the bulk batch.",
            "Record phase-specific notes in observations.csv using observation_tags and intervention_context.",
        ],
    },
    {
        "key": "between_mix",
        "title": "Between-Mix Recommendations",
        "context": "Use when planning the next trial or corrective addition after the current mix exists. Treat these as next-variant candidates, not retroactive edits.",
        "observation_tags": ["between_mix", "iteration", "adjustment"],
        "template": [
            "Use this section for candidate changes in the next batch or next additive trial.",
            "If you apply a correction, mark the observation with between_mix and a short intervention_context note.",
        ],
    },
    {
        "key": "post_mix",
        "title": "Post-Mix Recommendations",
        "context": "Use after blending and during wear testing or maceration. Focus on follow-up reads and deciding whether a new variant is needed.",
        "observation_tags": ["post_mix", "wear_test", "maceration"],
        "template": [
            "Record the opening, heart, and drydown after the mix has settled.",
            "If a correction is needed, create a new between_mix variant rather than mutating the existing bottle.",
            "Capture any intervention tags alongside the wear-test notes.",
        ],
    },
]


def _slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "formula"


def _parse_dilution(raw: str) -> float:
    raw = raw.strip().lower()
    if raw in ("", "neat", "pure"):
        return 1.0
    match = re.match(r"(\d+(?:\.\d+)?)\s*%", raw)
    if match:
        return float(match.group(1)) / 100.0
    return 1.0


def _serialize_recommendation(rec: object) -> dict:
    if isinstance(rec, dict):
        return dict(rec)
    return asdict(rec)


def _stringify_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return str(value).strip()


def _format_provenance_lines(provenance: object, indent: str = "  ") -> list[str]:
    if not provenance:
        return []

    if isinstance(provenance, str):
        text = provenance.strip()
        return [f"{indent}- Provenance: {text}"] if text else []

    lines: list[str] = []

    if isinstance(provenance, dict):
        lines.append(f"{indent}- Provenance:")
        for key, value in provenance.items():
            if value in (None, "", [], {}, ()):
                continue
            if isinstance(value, list):
                items = [_stringify_value(item) for item in value if _stringify_value(item)]
                if not items:
                    continue
                if len(items) == 1:
                    lines.append(f"{indent}  - {key}: {items[0]}")
                else:
                    lines.append(f"{indent}  - {key}:")
                    for item in items:
                        lines.append(f"{indent}    - {item}")
                continue
            if isinstance(value, dict):
                nested_parts = []
                for nested_key, nested_value in value.items():
                    nested_text = _stringify_value(nested_value)
                    if nested_text:
                        nested_parts.append(f"{nested_key}: {nested_text}")
                if nested_parts:
                    lines.append(f"{indent}  - {key}: {', '.join(nested_parts)}")
                continue
            lines.append(f"{indent}  - {key}: {_stringify_value(value)}")
        return lines if len(lines) > 1 else []

    if isinstance(provenance, list):
        lines.append(f"{indent}- Provenance:")
        for item in provenance:
            if isinstance(item, dict):
                source = (
                    item.get("source")
                    or item.get("perfumer")
                    or item.get("module")
                    or item.get("label")
                    or item.get("name")
                    or item.get("axis")
                    or "logic"
                )
                detail = (
                    item.get("logic")
                    or item.get("reason")
                    or item.get("text")
                    or item.get("note")
                    or item.get("description")
                    or item.get("value")
                )
                if detail is None:
                    detail_parts = []
                    for nested_key, nested_value in item.items():
                        if nested_key in {"source", "perfumer", "module", "label", "name", "axis"}:
                            continue
                        nested_text = _stringify_value(nested_value)
                        if nested_text:
                            detail_parts.append(f"{nested_key}: {nested_text}")
                    detail = ", ".join(detail_parts)
                detail_text = _stringify_value(detail)
                if detail_text:
                    lines.append(f"{indent}  - {source}: {detail_text}")
                else:
                    lines.append(f"{indent}  - {source}")
            else:
                text = _stringify_value(item)
                if text:
                    lines.append(f"{indent}  - {text}")
        return lines if len(lines) > 1 else []

    text = _stringify_value(provenance)
    return [f"{indent}- Provenance: {text}"] if text else []


def _format_recommendation_entry(entry: dict) -> list[str]:
    action = entry.get("action", "Recommend")
    material = entry.get("material", "material")
    target_axis = entry.get("target_axis")
    delta = entry.get("delta")
    composite_delta = entry.get("composite_delta")
    rationale = entry.get("rationale")
    family = entry.get("family")
    profile = entry.get("profile")

    header = f"- {action} {material}"
    if target_axis:
        header += f" for {target_axis}"
    if delta is not None or composite_delta is not None:
        header += f" (axis delta {delta}, total delta {composite_delta})"

    lines = [header]
    if rationale:
        lines.append(f"  - Rationale: {rationale}")
    if family:
        lines.append(f"  - Family: {family}")
    if profile:
        lines.append(f"  - Profile: {profile}")
    lines.extend(_format_provenance_lines(entry.get("provenance")))
    return lines


def _is_recommendation_entry(entry: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("kind") == "recommendation":
        return True
    return any(key in entry for key in ("target_axis", "material", "action", "delta", "composite_delta", "rationale"))


def _pre_mix_recommendations(prebond: dict, blocked_materials: dict[str, str]) -> list[dict]:
    recommendations: list[dict] = []
    for material_a, material_b, details in prebond["must_prebond"]:
        recommendations.append(
            {
                "kind": "must_prebond",
                "material_a": material_a,
                "material_b": material_b,
                "details": details,
            }
        )
    for material_a, material_b, details in prebond["benefits"]:
        recommendations.append(
            {
                "kind": "beneficial_premix",
                "material_a": material_a,
                "material_b": material_b,
                "details": details,
            }
        )
    for material_a, material_b, details in prebond["keep_separate"]:
        recommendations.append(
            {
                "kind": "keep_separate",
                "material_a": material_a,
                "material_b": material_b,
                "details": details,
            }
        )
    for ingredient, reason in blocked_materials.items():
        recommendations.append(
            {
                "kind": "blocked_material",
                "material": ingredient,
                "reason": reason,
            }
        )
    return recommendations


def _build_intervention_sections(
    recommendations: list[dict],
    pre_mix_engine: list[dict],
    between_mix_engine: list[dict],
    post_mix_engine: list[dict],
    prebond: dict,
    blocked_materials: dict[str, str],
) -> dict:
    sections: dict[str, dict] = {}
    pre_mix_recommendations = _pre_mix_recommendations(prebond, blocked_materials)
    pre_mix_recommendations.extend(_serialize_recommendation(rec) for rec in pre_mix_engine)
    between_mix_recommendations = [_serialize_recommendation(rec) for rec in between_mix_engine]
    post_mix_recommendations = [_serialize_recommendation(rec) for rec in post_mix_engine]
    post_mix_recommendations.extend([
        {
            "kind": "follow_up_check",
            "label": "Opening read",
            "text": "Capture the first 15 minutes separately from the later wear-test reads.",
        },
        {
            "kind": "follow_up_check",
            "label": "Heart read",
            "text": "Capture the main evolution window and note whether the character shifts after maceration.",
        },
        {
            "kind": "follow_up_check",
            "label": "Drydown read",
            "text": "Capture the final drydown, stability, and any off-notes before deciding on a correction.",
        },
        {
            "kind": "follow_up_check",
            "label": "Next-variant planning",
            "text": "If a correction is needed, create a new between_mix trial instead of mutating the current bottle.",
        },
    ])

    for phase in INTERVENTION_PHASES:
        key = phase["key"]
        if key == "pre_mix":
            phase_recommendations = pre_mix_recommendations
        elif key == "between_mix":
            phase_recommendations = between_mix_recommendations
        else:
            phase_recommendations = post_mix_recommendations

        sections[key] = {
            "title": phase["title"],
            "context": phase["context"],
            "observation_tags": phase["observation_tags"],
            "recommendations": phase_recommendations,
            "template": phase["template"],
        }

    return sections


def _safe_weighted_volatility_index(self) -> float | None:
    """Compatibility shim for the standalone verifier.

    The current engine scorer expects ingredient intelligence profiles to be dicts
    in one volatility fallback branch, but the project now returns a dataclass.
    This local shim keeps the standalone workflow runnable without changing the
    engine code.
    """
    import math

    eff = self.effective_ingredients()
    total_w = 0.0
    weighted = 0.0
    for name, pct in eff.items():
        mat = None
        try:
            from engine.optimizer.models import _lookup_material  # type: ignore

            mat = _lookup_material(name)
        except Exception:
            mat = None

        vp = None
        mw = None
        if mat:
            vp = mat.get("vp")
            mw = mat.get("mw")

        if vp is None or mw is None:
            try:
                from engine.ingredient_intelligence import get_profile

                profile = get_profile(name)
                if profile is not None:
                    if vp is None:
                        vp = getattr(profile, "vp", None)
                    if mw is None:
                        mw = getattr(profile, "mw", None)
            except Exception:
                pass

        if vp is not None and mw is not None and mw > 0:
            weighted += pct * vp / math.sqrt(mw)
            total_w += pct
    return weighted / total_w if total_w > 0 else None


def _install_formula_vector_compatibility() -> None:
    current = getattr(FormulaVector, "weighted_volatility_index", None)
    if current is not _safe_weighted_volatility_index:
        FormulaVector.weighted_volatility_index = _safe_weighted_volatility_index  # type: ignore[method-assign]


def _parse_formula_rows(body: str) -> tuple[dict[str, float], dict[str, float]]:
    """Parse formula rows from a markdown table. Accepts multiple formats.
    
    Supported:
      | # | Ingredient | Dilution | µL | mL |   (canonical)
      | Ingredient | Dilution | µL |               (no row number)
      | Ingredient | % |                         (percentages, neat)
      | Ingredient | % | Dilution |               (percentages with dilution)
    
    Handles section headers (**Top**, **Heart**, **Base**) and inline dilutions
    like "(10% in DPG)" or "10%".
    """
    ingredients_ul: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    total_ul_val: float | None = None

    def _split_row(line: str) -> list[str]:
        parts = [p.strip().replace("**", "") for p in line.split("|")]
        if parts and parts[0] == "":
            parts = parts[1:]
        if parts and parts[-1] == "":
            parts = parts[:-1]
        return parts

    def _normalize_header(cell: str) -> str:
        cell = cell.strip().replace("**", "").replace("`", "")
        cell = cell.replace("µ", "u").replace("μ", "u")
        cell = re.sub(r"\s+", " ", cell.lower())
        return cell

    def _is_separator_row(line: str) -> bool:
        stripped = line.strip()
        return bool(stripped.startswith("|") and re.fullmatch(r"\|[\s:\-|]+\|?", stripped))

    def _find_col(headers: list[str], *tokens: str) -> int | None:
        for idx, header in enumerate(headers):
            if any(token in header for token in tokens):
                return idx
        return None

    def _parse_amount(v: str) -> float | None:
        clean = v.strip().replace("**", "").replace("`", "")
        if clean.lower() in {"", "-", "--", "---", "—", "–", "na", "n/a"}:
            return None
        match = re.search(r"[-+]?\d[\d,\s]*(?:\.\d+)?", clean)
        if not match:
            return None
        token = match.group(0).replace(",", "").replace(" ", "")
        try:
            return float(token)
        except ValueError:
            return None

    def _parse_dil(v: str) -> float:
        clean = v.strip().replace("**", "").replace("`", "")
        low = clean.lower()
        if low in ("", "neat", "pure", "-", "--", "---", "—", "–"):
            return 1.0
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", clean)
        if m:
            return float(m.group(1).replace(",", ".")) / 100.0
        numeric = _parse_amount(clean)
        if numeric is None:
            return 1.0
        if 0.0 < numeric <= 1.0:
            return numeric
        return 1.0

    def _skip_ingredient(name: str) -> bool:
        low = re.sub(r"\s+", " ", name.strip().lower())
        if not low:
            return True
        if low in {"#", "ingredient", "material", "component", "layer", "ord"}:
            return True
        if "subtotal" in low or low == "total" or "batch total" in low:
            return True
        if "ethanol" in low or "concentrate total" in low or "matured concentrate" in low:
            return True
        if low.startswith("—") or low.startswith("-") or low.startswith("top:") or low.startswith("heart:") or low.startswith("base:"):
            return True
        return False

    def _section_is_excluded(section: str) -> bool:
        low = section.lower().strip()
        if not low:
            return False
        blocked_tokens = (
            "release gate audit",
            "calibration summary",
            "repair history",
            "gate time-series oav leaders",
            "family oav envelope",
            "vapor ppm / odt / oav leaders",
            "mixing order",
            "accord architecture",
            "material selection rationale",
            "what you'll need",
            "equipment",
            "procedure",
        )
        return any(token in low for token in blocked_tokens)

    def _extract_total_concentrate_ul(text: str) -> float | None:
        patterns = (
            (r"composition of bottle:[^\n]*?([0-9][0-9,\s]*(?:\.\d+)?)\s*ml\s+concentrate", "ml"),
            (r"concentrate target:[^\n]*?([0-9][0-9,\s]*(?:\.\d+)?)\s*u?l", "ul"),
            (r"concentrate total[^\n]*?([0-9][0-9,\s]*(?:\.\d+)?)\s*u?l", "ul"),
            (r"concentrate total[^\n]*?([0-9][0-9,\s]*(?:\.\d+)?)\s*ml", "ml"),
        )
        for pattern, unit in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = _parse_amount(match.group(1))
            if value is None:
                continue
            if unit == "ml":
                return value * 1000.0
            return value
        return None

    lines = body.splitlines()
    total_ul_val = _extract_total_concentrate_ul(body)
    
    # First pass: find total concentrate volume
    if total_ul_val is None:
        for line in lines:
            clean = line.strip().lower()
            if "**total**" in clean or "concentrate" in clean:
                for token in clean.split("|"):
                    val = _parse_amount(token)
                    if val is not None and val >= 100:
                        total_ul_val = val
                        break
                if total_ul_val is not None:
                    break

    # Second pass: parse ingredient rows from markdown tables with usable headers.
    current_headers: list[str] | None = None
    current_section = ""
    for idx, line in enumerate(lines):
        raw = line.strip()
        heading_match = re.match(r"^#{2,6}\s+(.+?)\s*$", raw)
        if heading_match:
            current_section = heading_match.group(1).strip()
            current_headers = None
            continue
        if not raw.startswith("|"):
            current_headers = None
            continue

        if idx + 1 < len(lines) and _is_separator_row(lines[idx + 1]):
            current_headers = [_normalize_header(part) for part in _split_row(raw)]
            continue

        if _is_separator_row(raw) or current_headers is None or _section_is_excluded(current_section):
            continue

        parts = _split_row(raw)
        if len(parts) < 2:
            continue

        name_idx = _find_col(current_headers, "ingredient", "material", "component")
        dilution_idx = _find_col(current_headers, "dilution", "form", "stock")
        amount_ul_idx = None
        amount_ml_idx = None
        percent_idx = None
        for i, header in enumerate(current_headers):
            if "ul" in header and ("amount" in header or header == "ul" or "µl" in header):
                amount_ul_idx = i
                break
        for i, header in enumerate(current_headers):
            if "ml" in header and ("amount" in header or header == "ml"):
                amount_ml_idx = i
                break
        for i, header in enumerate(current_headers):
            if header == "%" or "percent" in header:
                percent_idx = i
                break

        if name_idx is None:
            continue
        if amount_ul_idx is None and amount_ml_idx is None and percent_idx is None:
            continue

        if name_idx >= len(parts):
            continue
        ingredient = parts[name_idx].strip()
        if _skip_ingredient(ingredient):
            continue

        amount_ul: float | None = None
        if amount_ul_idx is not None and amount_ul_idx < len(parts):
            amount_ul = _parse_amount(parts[amount_ul_idx])
        if amount_ul is None and percent_idx is not None and percent_idx < len(parts):
            amount_ul = _parse_amount(parts[percent_idx])
        if amount_ul is None and amount_ml_idx is not None and amount_ml_idx < len(parts):
            amount_ml = _parse_amount(parts[amount_ml_idx])
            if amount_ml is not None:
                amount_ul = amount_ml * 1000.0
        if amount_ul is None:
            continue

        dilution = 1.0
        if dilution_idx is not None and dilution_idx < len(parts):
            dilution = _parse_dil(parts[dilution_idx])

        ingredients_ul[ingredient] = ingredients_ul.get(ingredient, 0.0) + amount_ul
        if ingredient not in dilutions or dilution != 1.0:
            dilutions[ingredient] = dilution

    # Convert percentages to µL if total_ul is known and values look like pcts
    vals = list(ingredients_ul.values())
    if vals and total_ul_val and all(v < 100 for v in vals):
        for name in list(ingredients_ul):
            ingredients_ul[name] = ingredients_ul[name] * total_ul_val / 100.0
    
    return ingredients_ul, dilutions


def _infer_family_archetype(body: str) -> str:
    match = re.search(r"\*\*Family archetype:\*\*\s*`?([A-Za-z0-9_.-]+)`?", body)
    return match.group(1).strip() if match else ""


def _build_formula_record(number: int, name: str, body: str, ingredients_ul: dict[str, float], dilutions: dict[str, float]) -> dict:
    total_ul = sum(ingredients_ul.values()) or 1.0
    ingredients_pct = {
        material: round((amount / total_ul) * 100, 4)
        for material, amount in ingredients_ul.items()
    }
    concentrate_ml = round(total_ul / 1000.0, 3)
    return {
        "number": number,
        "name": name,
        "ingredients_ul": ingredients_ul,
        "ingredients_pct": ingredients_pct,
        "dilutions": dilutions,
        "concentrate_ml": concentrate_ml,
        "body": body,
        "family_archetype": _infer_family_archetype(body),
    }


def _infer_batch_volume_ml(formula: dict) -> float:
    concentrate_ml = float(formula.get("concentrate_ml", 0.0) or 0.0)
    if concentrate_ml <= 0:
        return DEFAULT_BATCH_VOLUME_ML

    body = str(formula.get("body", ""))
    name = str(formula.get("name", ""))
    text = f"{name}\n{body}".lower()

    standalone_module_markers = (
        "accord concentrate",
        "booster module",
        "module set",
        "standalone accord",
        "1000 ul accord",
        "1000ul accord",
        "1000 ul booster",
        "1000ul booster",
        "build this as a **1000 ul",
        "build this as a **1000u",
    )
    finished_perfume_markers = (
        "30 ml",
        "50 ml",
        "bottle build",
        "ethanol",
        "mixing guide",
        "edp",
        "perfume formula",
    )

    if any(marker in text for marker in standalone_module_markers) and not any(
        marker in text for marker in finished_perfume_markers
    ):
        return concentrate_ml

    return DEFAULT_BATCH_VOLUME_ML


def _infer_structure_mode(formula: dict) -> str:
    body = str(formula.get("body", ""))
    name = str(formula.get("name", ""))
    text = f"{name}\n{body}".lower()
    module_markers = (
        "accord concentrate",
        "booster module",
        "module set",
        "standalone accord",
        "1000 ul accord",
        "1000ul accord",
        "1000 ul booster",
        "1000ul booster",
    )
    return "module" if any(marker in text for marker in module_markers) else "formula"


def parse_formula_markdown(path: Path) -> list[dict]:
    """Parse formula sections from markdown files.

    Supports both:
    - numbered multi-formula files using `## 1. Name`
    - standalone single-formula accord guides with one formula table
    """
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s+(\d+)\.\s+(.+?)$", text, flags=re.MULTILINE)
    formulas: list[dict] = []

    for idx in range(1, len(sections) - 2, 3):
        number = int(sections[idx])
        name = sections[idx + 1].strip()
        body = sections[idx + 2]
        ingredients_ul, dilutions = _parse_formula_rows(body)
        if not ingredients_ul:
            continue
        formulas.append(_build_formula_record(number, name, body, ingredients_ul, dilutions))

    if formulas:
        return formulas

    ingredients_ul, dilutions = _parse_formula_rows(text)
    if not ingredients_ul:
        return []

    title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    name = title_match.group(1).strip() if title_match else path.stem.replace("_", " ")
    return [_build_formula_record(1, name, text, ingredients_ul, dilutions)]


def select_formula(formulas: list[dict], formula_number: int | None, formula_name: str | None) -> dict:
    if formula_number is not None:
        for formula in formulas:
            if formula["number"] == formula_number:
                return formula
        raise ValueError(f"Formula #{formula_number} not found.")

    if formula_name:
        target = formula_name.lower().strip()
        for formula in formulas:
            if target in formula["name"].lower():
                return formula
        raise ValueError(f"No formula name matched '{formula_name}'.")

    if len(formulas) == 1:
        return formulas[0]

    raise ValueError("Provide --formula or --name when the file contains multiple formulas.")


def build_verification_bundle(formula: dict) -> dict:
    fv = FormulaVector(
        ingredients=dict(formula["ingredients_pct"]),
        dilutions=dict(formula["dilutions"]),
    )

    _install_formula_vector_compatibility()
    scorer = FormulaScorer()
    scores = scorer.score(fv)
    radar = scorer.formula_character_radar(fv)
    scores = _normalize_legacy_score_axes(fv, scores, radar)
    stars = compute_star_ratings(fv, scores, radar)
    confidence = ConfidenceScorer().score(fv.ingredients)
    inventory = load_inventory()
    recommendations = generate_recommendations(fv, scores, inventory=inventory, top_n=5)
    pre_mix_engine = generate_intervention_recommendations(
        fv,
        scores,
        inventory=inventory,
        top_n=5,
        mode="pre_mix",
    )
    between_mix_engine = generate_intervention_recommendations(
        fv,
        scores,
        inventory=inventory,
        top_n=5,
        mode="between_mix",
    )
    post_mix_engine = generate_intervention_recommendations(
        fv,
        scores,
        inventory=inventory,
        top_n=5,
        mode="post_mix",
        batch_volume_ml=30.0,
    )

    prebond = PreBondingAnalyzer().analyze_formula(fv.ingredients)
    instructions = InstructionGenerator().generate(
        ingredients=fv.ingredients,
        formula_name=formula["name"],
    )
    blocked_materials = {
        ingredient: blocked_reason(ingredient)
        for ingredient in formula["ingredients_pct"]
        if blocked_reason(ingredient)
    }

    raw_ingredients = dict(formula.get("ingredients_ul") or {})
    if not raw_ingredients:
        raw_ingredients = {
            name: pct
            for name, pct in formula["ingredients_pct"].items()
        }

    formula_fingerprint = fingerprint_formula(formula["name"], raw_ingredients)
    synergy_graph = SynergyGraph()
    synergy_graph.build(list(raw_ingredients.keys()))

    style_fingerprint = scores.get("_style_fingerprint", {})
    style_name = "classical"
    if isinstance(style_fingerprint, dict):
        primary = style_fingerprint.get("primary_candidate", {}) or {}
        dominant_style = str(style_fingerprint.get("dominant_style", "")).lower().strip()
        candidate_style = str(primary.get("style", "")).lower().strip() if isinstance(primary, dict) else ""
        style_hint = candidate_style or dominant_style
        if "fresh" in style_hint:
            style_name = "fresh"
        elif "woody" in style_hint:
            style_name = "woody"
        elif "oriental" in style_hint or "amber" in style_hint:
            style_name = "oriental"
        elif "chypre" in style_hint:
            style_name = "chypre"
        elif "skin" in style_hint:
            style_name = "skin_scent"

    batch_volume_ml = formula.get("batch_volume_ml")
    if batch_volume_ml is None:
        batch_volume_ml = _infer_batch_volume_ml(formula)
    structure_mode = _infer_structure_mode(formula)
    concentrate_ml = float(formula.get("concentrate_ml", 0.0) or 0.0)
    ethanol_ml = max(0.0, float(batch_volume_ml) - concentrate_ml)
    life_graph = build_chemical_life_graph(
        formula_name=formula["name"],
        ingredients=raw_ingredients,
        ethanol_ml=ethanol_ml,
        style=style_name,
        structure_mode=structure_mode,
        synergy_graph=synergy_graph,
    )
    temporal_graph = _build_temporal_graph_payload(formula)

    formula_fingerprint_dict = asdict(formula_fingerprint)
    formula_fingerprint_dict["character_radar"] = formula_fingerprint.character_radar()
    formula_fingerprint_dict["dominant_character"] = formula_fingerprint.dominant_character()
    formula_fingerprint_dict["materials"] = [
        name
        for name, _ in sorted(raw_ingredients.items(), key=lambda item: item[1], reverse=True)
    ]
    life_graph_dict = asdict(life_graph)
    synergy_summary = {
        "node_count": len(synergy_graph.nodes),
        "edge_count": len(synergy_graph.edges),
        "overall_synergy": life_graph.synergy_report.overall_synergy,
        "strongest_pairs": life_graph.synergy_report.strongest_pairs,
        "weakest_pairs": life_graph.synergy_report.weakest_pairs,
        "clash_pairs": life_graph.synergy_report.clash_pairs,
        "stacks": [asdict(stack) for stack in life_graph.synergy_report.stacks],
        "musk_compatibility": asdict(life_graph.musk_analysis),
    }

    star_scores = stars.as_dict()
    recommendation_sections = _build_intervention_sections(
        recommendations,
        pre_mix_engine,
        between_mix_engine,
        post_mix_engine,
        prebond,
        blocked_materials,
    )
    comparison = {
        "score_axes": {axis: scores.get(axis, 0) for axis in SCORE_AXES},
        "wear_axes": {field: None for field, _ in WEAR_TEST_AXES},
        "star_axes": {axis: star_scores.get(axis) for axis in star_scores},
        "intervention_axes": {
            phase: {
                "title": section["title"],
                "context": section["context"],
                "observation_tags": section["observation_tags"],
            }
            for phase, section in recommendation_sections.items()
        },
    }

    return {
        "formula": formula,
        "scores": scores,
        "character_radar": radar,
        "star_ratings": star_scores,
        "star_average": round(stars.average(), 2),
        "confidence": confidence,
        "recommendations": [asdict(rec) for rec in recommendations],
        "recommendation_sections": recommendation_sections,
        "intervention_phases": [phase["key"] for phase in INTERVENTION_PHASES],
        "comparison": comparison,
        "fingerprint": formula_fingerprint_dict,
        "synergy_graph": synergy_summary,
        "chemical_life_graph": life_graph_dict,
        "temporal_graph": temporal_graph,
        "prebond_analysis": {
            "must_prebond": [
                {"material_a": a, "material_b": b, **details}
                for a, b, details in prebond["must_prebond"]
            ],
            "benefits": [
                {"material_a": a, "material_b": b, **details}
                for a, b, details in prebond["benefits"]
            ],
            "keep_separate": [
                {"material_a": a, "material_b": b, **details}
                for a, b, details in prebond["keep_separate"]
            ],
            "crystalline": list(prebond["crystalline"]),
        },
        "blocked_materials": blocked_materials,
        "mixing_protocol": instructions,
    }


def _normalize_legacy_score_axes(
    fv: FormulaVector,
    scores: dict,
    radar: dict,
) -> dict:
    normalized = dict(scores)
    style_fp = normalized.get("_style_fingerprint", {}) or {}
    primary = style_fp.get("primary_candidate", {}) if isinstance(style_fp, dict) else {}
    note_dist = fv.note_distribution() if hasattr(fv, "note_distribution") else {}
    top = float(note_dist.get("top", 0.0))
    heart = float(note_dist.get("heart", 0.0))
    base = float(note_dist.get("base", 0.0))
    balance_distance = abs(top - 20.0) + abs(heart - 40.0) + abs(base - 40.0)
    balance_score = max(0.0, 100.0 - balance_distance * 1.2)

    theory_score = (
        normalized.get("synergy", 50.0) * 0.45
        + normalized.get("stacking_depth", 50.0) * 0.35
        + normalized.get("luxury", 50.0) * 0.20
    )
    complexity_score = (
        normalized.get("texture", 50.0) * 0.35
        + normalized.get("hedonic", 50.0) * 0.25
        + normalized.get("perceptual_clarity", 50.0) * 0.20
        + min(len(getattr(fv, "ingredients", {}) or {}), 20) * 1.0
    )
    radiance_score = min(max(float(radar.get("radiance", 0.0)) * 10.0, 0.0), 100.0)
    character_values = [float(v) for v in radar.values() if isinstance(v, (int, float))]
    if character_values:
        mean_val = sum(character_values) / len(character_values)
        spread = sum(abs(v - mean_val) for v in character_values) / len(character_values)
        character_balance = max(0.0, min(100.0, 100.0 - spread * 10.0))
    else:
        character_balance = 50.0

    normalized.setdefault("balance", round(primary.get("balance_score", balance_score), 1))
    normalized.setdefault("theory", round(theory_score, 1))
    normalized.setdefault("radiance", round(radiance_score, 1))
    normalized.setdefault("complexity", round(min(complexity_score, 100.0), 1))
    normalized.setdefault("character_balance", round(character_balance, 1))
    normalized.setdefault("cost", 50.0)
    return normalized


def _format_material_signature_lines(fp: dict, inventory_names: set[str], formula_names: set[str]) -> list[str]:
    lines: list[str] = []
    radar = fp.get("character_radar", {}) or {}
    dominant = sorted(
        radar.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    if dominant:
        lines.append("### Fingerprint Radar")
        for dim, value in dominant:
            lines.append(f"- {dim}: {value:.2f}")
        lines.append("")

    top_materials = fp.get("materials", [])[:8]
    if top_materials:
        lines.append("### Top Materials")
        for material in top_materials:
            lines.append(f"- {material}")
        lines.append("")

    anchor_materials = [str(name) for name in top_materials[:3]]
    if anchor_materials:
        lines.append("### Inventory Neighbor Scan")
        for anchor in anchor_materials:
            matches = [
                (name, score)
                for name, score in find_similar_materials(anchor, n=8)
                if name in inventory_names and name not in formula_names and name != anchor
            ]
            if matches:
                joined = ", ".join(f"{name} ({score:.2f})" for name, score in matches[:4])
                lines.append(f"- {anchor}: {joined}")
        lines.append("")

    unknown = fp.get("unknown_materials", [])
    if unknown:
        lines.append("### Unknown Materials")
        for material in unknown:
            lines.append(f"- {material}")
        lines.append("")

    return lines


def _format_synergy_lines(synergy: dict) -> list[str]:
    lines: list[str] = [
        "### Synergy Graph",
        f"- Nodes: {synergy.get('node_count', 0)}",
        f"- Edges: {synergy.get('edge_count', 0)}",
        f"- Overall synergy: {synergy.get('overall_synergy', 0):+.3f}",
        "",
    ]
    strongest = synergy.get("strongest_pairs") or []
    if strongest:
        lines.append("#### Strongest Pairs")
        for a, b, score in strongest[:5]:
            lines.append(f"- {a} + {b} ({score:+.3f})")
        lines.append("")
    clashes = synergy.get("clash_pairs") or []
    if clashes:
        lines.append("#### Clash Pairs")
        for a, b, score in clashes[:5]:
            lines.append(f"- {a} + {b} ({score:+.3f})")
        lines.append("")
    stacks = synergy.get("stacks") or []
    if stacks:
        lines.append("#### Synergy Stacks")
        for stack in stacks[:3]:
            materials = " + ".join(stack.get("materials", []))
            lines.append(f"- {materials} (avg={stack.get('avg_synergy', 0):.3f})")
        lines.append("")
    musk = synergy.get("musk_compatibility") or {}
    if musk:
        lines.append("#### Musk Compatibility")
        for musk_name, score, reason in (musk.get("recommended") or [])[:3]:
            lines.append(f"- Recommended: {musk_name} ({score:+.3f}) - {reason}")
        for musk_name, score, reason in (musk.get("too_heavy") or [])[:2]:
            lines.append(f"- Too heavy: {musk_name} ({score:+.3f}) - {reason}")
        lines.append("")
    return lines


def _format_life_graph_lines(life_graph: dict) -> list[str]:
    lines: list[str] = [
        "### Chemical Life Graph",
        f"- Health score: {life_graph.get('health_score', 0):.1f}/100",
        f"- Structure mode: {life_graph.get('structure_mode', 'formula')}",
        f"- Ingredient count: {life_graph.get('ingredient_count', 0)}",
        f"- Total mass: {life_graph.get('total_mass_ul', 0):.0f} µL",
        f"- Concentrate pct: {life_graph.get('concentrate_pct', 0):.1f}%",
        "",
    ]

    weight = life_graph.get("weight_diagnosis") or {}
    if weight:
        lines.append("#### Weight Diagnosis")
        for dim, delta in (weight.get("overweight") or [])[:3]:
            lines.append(f"- Overweight: {dim} (+{delta:.1f})")
        for dim, delta in (weight.get("underweight") or [])[:3]:
            lines.append(f"- Underweight: {dim} (-{delta:.1f})")
        lines.append(f"- Balance score: {weight.get('balance_score', 0):.1f}/100")
        lines.append("")

    gaps = life_graph.get("structural_gaps") or []
    if gaps:
        lines.append("#### Structural Gaps")
        for gap in gaps[:5]:
            lines.append(
                f"- [{gap.get('severity', 0):.0%}] {gap.get('gap_type')}: {gap.get('name')}"
            )
            suggestion = gap.get("suggestion")
            if suggestion:
                lines.append(f"  - {suggestion}")
            candidates = gap.get("candidates") or []
            if candidates:
                lines.append(f"  - Candidates: {', '.join(candidates[:5])}")
        lines.append("")

    temporal = life_graph.get("temporal") or {}
    if temporal:
        lines.append("#### Temporal Evolution")
        lines.append(f"- Top dominance: ~{temporal.get('top_dominance_minutes', 0):.0f} min")
        lines.append(f"- Estimated longevity: ~{temporal.get('longevity_hours', 0):.0f} hr")
        lines.append(f"- Linearity: {temporal.get('linear_score', 0):.0%}")
        lines.append("- Detailed curve file: temporal_graph.md")
        lines.append("")

    return lines


def _ascii_bar(value: float, width: int = 20, scale: float = 100.0) -> str:
    if scale <= 0:
        scale = 1.0
    filled = max(0, min(width, int(round((value / scale) * width))))
    return "#" * filled + "." * (width - filled)


def _stage_blurb(note_pct: dict, dominant: str) -> str:
    top = float(note_pct.get("top", 0))
    heart = float(note_pct.get("heart", 0))
    base = float(note_pct.get("base", 0))

    if dominant == "top":
        if top >= 60:
            return "Bright opening. The top is clearly in charge."
        if top >= 45:
            return "Still opening-led, but the heart is already rising."
        return "The opening is fading and the heart is about to take over."
    if dominant == "heart":
        if heart >= 70:
            return "The heart fully owns the perfume now."
        if heart >= 50:
            return "This is the handoff point where the heart takes control."
        return "The heart is leading, but the opening still matters."
    if dominant == "base":
        if base >= 70:
            return "Full drydown. The base is doing most of the work."
        return "The base is now more noticeable than the opening."
    return "Mixed stage."


def _top_material_names_at_time(top_curves: list[dict], index: int, n: int = 3) -> str:
    ranked = []
    for entry in top_curves:
        curve = entry.get("curve") or []
        if index < len(curve):
            ranked.append((entry.get("name", "material"), float(curve[index])))
    ranked.sort(key=lambda item: item[1], reverse=True)
    names = [name for name, value in ranked[:n] if value > 0]
    return ", ".join(names) if names else "-"


def _classify_material_timing(top_curves: list[dict]) -> tuple[list[str], list[str], list[str]]:
    early, mid, late = [], [], []
    for entry in top_curves:
        name = entry.get("name", "material")
        fadeout = str(entry.get("fadeout") or "")
        if fadeout in {"15min", "4hr"}:
            early.append(name)
        elif fadeout in {"8hr", "24hr"}:
            mid.append(name)
        elif fadeout == ">24hr":
            late.append(name)
    return early, mid, late


def _build_temporal_graph_payload(formula: dict) -> dict:
    simulator = VolatilityCurveSimulator()
    profile = simulator.simulate(dict(formula["ingredients_pct"]))
    summary = simulator.summary(profile)

    ranked_curves = sorted(
        profile.curves.items(),
        key=lambda item: sum(item[1]),
        reverse=True,
    )
    top_material_curves = [
        {
            "name": name,
            "curve": list(curve),
            "fadeout": summary["fadeout_times"].get(name),
        }
        for name, curve in ranked_curves[:8]
    ]

    return {
        "time_points": list(profile.time_points),
        "time_labels": list(profile.time_labels),
        "dominant_notes": list(profile.dominant_notes),
        "note_evolution": list(profile.note_evolution),
        "opening_note": summary.get("opening_note"),
        "drydown_note": summary.get("drydown_note"),
        "transitions": list(summary.get("transitions", [])),
        "fadeout_times": dict(summary.get("fadeout_times", {})),
        "top_material_curves": top_material_curves,
    }


def _format_temporal_graph_lines(temporal_graph: dict) -> list[str]:
    if not temporal_graph:
        return ["No temporal graph data available."]

    time_labels = temporal_graph.get("time_labels", [])
    note_evolution = temporal_graph.get("note_evolution") or []
    dominant_notes = temporal_graph.get("dominant_notes") or []
    top_curves = temporal_graph.get("top_material_curves") or []
    opening_note = temporal_graph.get("opening_note", "unknown")
    drydown_note = temporal_graph.get("drydown_note", "unknown")
    early, mid, late = _classify_material_timing(top_curves)

    lines: list[str] = [
        "### Temporal Graph",
        "![Temporal Graph](temporal_graph.png)",
        "",
        "- Plain-English wear map for the formula over time.",
        "",
        "#### At a Glance",
        f"- Starts as: {opening_note}-led.",
        f"- Ends as: {drydown_note}-led.",
    ]

    transitions = temporal_graph.get("transitions") or []
    if transitions:
        first = transitions[0]
        lines.append(
            f"- Main handoff: {first.get('from', 'unknown')} -> {first.get('to', 'unknown')} at {first.get('at', '?')}."
        )
    else:
        lines.append("- Main handoff: no major note-family switch detected.")
    if early:
        lines.append(f"- Early flash materials: {', '.join(early[:4])}.")
    if mid:
        lines.append(f"- Mid-phase support: {', '.join(mid[:4])}.")
    if late:
        lines.append(f"- Late drydown carriers: {', '.join(late[:4])}.")
    lines.append("")

    if note_evolution and time_labels:
        lines.append("#### Visual Time Series")
        lines.append("- The rendered chart above is the image version of this wear curve.")
        lines.append("")

    if transitions:
        lines.append("#### Note Transitions")
        for item in transitions:
            lines.append(
                f"- {item.get('from', 'unknown')} -> {item.get('to', 'unknown')} at {item.get('at', '?')}"
            )
        lines.append("")

    if note_evolution and time_labels:
        lines.append("#### Wear Map")
        lines.append("| Time | What Happens | Main Drivers | Balance |")
        lines.append("|---|---|---|---|")
        for idx, note_pct in enumerate(note_evolution):
            label = time_labels[idx] if idx < len(time_labels) else str(idx)
            dominant = dominant_notes[idx] if idx < len(dominant_notes) else ""
            summary = _stage_blurb(note_pct, dominant)
            drivers = _top_material_names_at_time(top_curves, idx)
            balance = f"T {note_pct.get('top', 0):.0f} / H {note_pct.get('heart', 0):.0f} / B {note_pct.get('base', 0):.0f}"
            lines.append(f"| {label} | {summary} | {drivers} | {balance} |")
        lines.append("")

        lines.append("#### Technical Note Balance")
        lines.append("| Time | Top | Heart | Base | Dominant |")
        lines.append("|---|---:|---:|---:|---|")
        for idx, note_pct in enumerate(note_evolution):
            label = time_labels[idx] if idx < len(time_labels) else str(idx)
            dominant = dominant_notes[idx] if idx < len(dominant_notes) else ""
            lines.append(
                f"| {label} | {note_pct.get('top', 0):.1f} | {note_pct.get('heart', 0):.1f} | {note_pct.get('base', 0):.1f} | {dominant} |"
            )
        lines.append("")

    if top_curves and time_labels:
        lines.append("#### Main Materials Over Time")
        lines.append("| Material | Role In Wear | Fades By |")
        lines.append("|---|---|---|")
        for entry in top_curves:
            fadeout = entry.get("fadeout") or "-"
            name = entry.get("name", "material")
            if fadeout in {"15min", "4hr"}:
                role = "opening material"
            elif fadeout in {"8hr", "24hr"}:
                role = "middle-to-late support"
            elif fadeout == ">24hr":
                role = "late drydown carrier"
            else:
                role = "supporting material"
            lines.append(f"| {name} | {role} | {fadeout} |")
        lines.append("")

    return lines


def _render_temporal_graph_svg(temporal_graph: dict, title: str) -> str:
    time_labels = temporal_graph.get("time_labels") or []
    note_evolution = temporal_graph.get("note_evolution") or []
    if not time_labels or not note_evolution:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="240">'
            '<rect width="100%" height="100%" fill="#fffaf2"/>'
            '<text x="40" y="60" font-family="Segoe UI, Arial, sans-serif" font-size="22" fill="#2f241f">'
            'No temporal graph data available'
            "</text></svg>"
        )

    width = 900
    height = 420
    left = 80
    right = 40
    top = 70
    bottom = 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    step_x = plot_w / max(1, len(time_labels) - 1)

    def point(i: int, value: float) -> tuple[float, float]:
        x = left + (step_x * i)
        y = top + plot_h - ((value / 100.0) * plot_h)
        return round(x, 2), round(y, 2)

    top_points = [point(i, float(row.get("top", 0))) for i, row in enumerate(note_evolution)]
    heart_points = [point(i, float(row.get("heart", 0))) for i, row in enumerate(note_evolution)]
    base_points = [point(i, float(row.get("base", 0))) for i, row in enumerate(note_evolution)]

    def polyline(points: list[tuple[float, float]]) -> str:
        return " ".join(f"{x},{y}" for x, y in points)

    grid = []
    for tick in [0, 25, 50, 75, 100]:
        y = top + plot_h - ((tick / 100.0) * plot_h)
        grid.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" y2="{y:.2f}" stroke="#e7ddd2" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{left-12}" y="{y+5:.2f}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#6a5a50">{tick}</text>'
        )

    x_labels = []
    for i, label in enumerate(time_labels):
        x, _ = point(i, 0)
        x_labels.append(
            f'<text x="{x:.2f}" y="{height-30}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#6a5a50">{label}</text>'
        )

    def circles(points: list[tuple[float, float]], color: str) -> str:
        return "".join(
            f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="#fffaf2" stroke-width="2"/>'
            for x, y in points
        )

    legend = """
    <g transform="translate(620,28)">
      <line x1="0" y1="0" x2="26" y2="0" stroke="#d97706" stroke-width="4" stroke-linecap="round"/>
      <text x="34" y="5" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#2f241f">Top</text>
      <line x1="90" y1="0" x2="116" y2="0" stroke="#0f766e" stroke-width="4" stroke-linecap="round"/>
      <text x="124" y="5" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#2f241f">Heart</text>
      <line x1="200" y1="0" x2="226" y2="0" stroke="#7c3aed" stroke-width="4" stroke-linecap="round"/>
      <text x="234" y="5" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#2f241f">Base</text>
    </g>
    """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#fffaf2"/>
  <text x="{left}" y="34" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="700" fill="#2f241f">{title}</text>
  <text x="{left}" y="56" font-family="Segoe UI, Arial, sans-serif" font-size="13" fill="#6a5a50">Top, heart, and base balance across the wear curve</text>
  {''.join(grid)}
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#8d7d72" stroke-width="1.5"/>
  <line x1="{left}" y1="{top+plot_h}" x2="{width-right}" y2="{top+plot_h}" stroke="#8d7d72" stroke-width="1.5"/>
  <polyline fill="none" stroke="#d97706" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{polyline(top_points)}"/>
  <polyline fill="none" stroke="#0f766e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{polyline(heart_points)}"/>
  <polyline fill="none" stroke="#7c3aed" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{polyline(base_points)}"/>
  {circles(top_points, '#d97706')}
  {circles(heart_points, '#0f766e')}
  {circles(base_points, '#7c3aed')}
  {''.join(x_labels)}
  {legend}
</svg>"""
    return svg


def _write_temporal_graph_png(path: Path, temporal_graph: dict, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    time_labels = temporal_graph.get("time_labels") or []
    note_evolution = temporal_graph.get("note_evolution") or []

    fig, ax = plt.subplots(figsize=(9.2, 4.8), dpi=150)
    fig.patch.set_facecolor("#fffaf2")
    ax.set_facecolor("#fffaf2")

    if not time_labels or not note_evolution:
        ax.text(
            0.5,
            0.5,
            "No temporal graph data available",
            ha="center",
            va="center",
            fontsize=16,
            color="#2f241f",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        xs = list(range(len(time_labels)))
        top_vals = [float(row.get("top", 0)) for row in note_evolution]
        heart_vals = [float(row.get("heart", 0)) for row in note_evolution]
        base_vals = [float(row.get("base", 0)) for row in note_evolution]

        ax.plot(xs, top_vals, color="#d97706", marker="o", linewidth=3, markersize=6, label="Top")
        ax.plot(xs, heart_vals, color="#0f766e", marker="o", linewidth=3, markersize=6, label="Heart")
        ax.plot(xs, base_vals, color="#7c3aed", marker="o", linewidth=3, markersize=6, label="Base")

        ax.set_title(title, loc="left", fontsize=16, fontweight="bold", color="#2f241f", pad=16)
        ax.text(
            0.0,
            1.02,
            "Top, heart, and base balance across the wear curve",
            transform=ax.transAxes,
            fontsize=10,
            color="#6a5a50",
        )
        ax.set_xticks(xs)
        ax.set_xticklabels(time_labels, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_ylabel("Relative Presence", fontsize=10, color="#4b3b33")
        ax.grid(axis="y", color="#e7ddd2", linewidth=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#8d7d72")
        ax.spines["bottom"].set_color("#8d7d72")
        ax.tick_params(colors="#6a5a50")
        legend = ax.legend(loc="upper right", frameon=False, ncol=3)
        for text in legend.get_texts():
            text.set_color("#2f241f")

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _write_aux_report(path: Path, title: str, lines: list[str]) -> None:
    path.write_text("\n".join([f"# {title}", "", *lines]) + "\n", encoding="utf-8")


def write_observations_csv(path: Path) -> None:
    rows = [
        [
            "date",
            "batch_id",
            "formula_name",
            "intervention_phase",
            "recommendation_section",
            "observation_tags",
            "issue_tags",
            "desired_effects",
            "must_preserve",
            "must_avoid",
            "intervention_context",
            "bottle_state_file",
            "additions_applied",
            "maceration_days",
            "wear_test_hours",
            "opening_score_10",
            "heart_score_10",
            "drydown_score_10",
            "longevity_score_10",
            "projection_score_10",
            "balance_score_10",
            "overall_score_10",
            "notes",
        ]
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def _format_intervention_entry(entry: dict) -> list[str]:
    kind = entry.get("kind", "note")
    if kind == "recommendation" or _is_recommendation_entry(entry):
        return _format_recommendation_entry(entry)
    if kind == "must_prebond":
        return [
            f"- Must prebond: {entry['material_a']} + {entry['material_b']}",
            f"  - Details: {entry.get('details', {})}",
        ]
    if kind == "beneficial_premix":
        return [
            f"- Beneficial premix: {entry['material_a']} + {entry['material_b']}",
            f"  - Details: {entry.get('details', {})}",
        ]
    if kind == "keep_separate":
        return [
            f"- Keep separate: {entry['material_a']} + {entry['material_b']}",
            f"  - Details: {entry.get('details', {})}",
        ]
    if kind == "blocked_material":
        return [
            f"- Blocked material: {entry['material']}",
            f"  - Reason: {entry.get('reason')}",
        ]
    if kind == "follow_up_check":
        return [
            f"- {entry.get('label', 'Follow-up check')}: {entry.get('text', '')}",
        ]
    return [f"- {entry}"]


def write_intervention_recommendations(path: Path, bundle: dict) -> None:
    formula = bundle["formula"]
    sections = bundle["recommendation_sections"]

    lines = [
        f"# Intervention Recommendations - {formula['name']}",
        "",
        "This file is the standalone intervention surface for the verification bundle.",
        "It keeps the current flat recommendations intact while also exposing explicit pre_mix, between_mix, and post_mix sections.",
        "",
    ]

    for phase in INTERVENTION_PHASES:
        section = sections[phase["key"]]
        lines.extend(
            [
                f"## {section['title']}",
                "",
                f"- Context: {section['context']}",
                f"- Observation tags: {', '.join(section['observation_tags'])}",
                "",
            ]
        )

        if section["recommendations"]:
            lines.append("### Recommendations")
            for entry in section["recommendations"]:
                lines.extend(_format_intervention_entry(entry))
            lines.append("")
        else:
            lines.append("- No explicit recommendations captured yet.")
            lines.append("")

        lines.append("### Template")
        for bullet in section["template"]:
            lines.append(f"- {bullet}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wear_test_template(path: Path, bundle: dict) -> None:
    formula = bundle["formula"]
    scores = bundle["scores"]
    stars = bundle["star_ratings"]
    confidence = bundle["confidence"]
    sections = bundle["recommendation_sections"]

    lines = [
        f"# Wear Test Template - {formula['name']}",
        "",
        "## Predicted Baseline",
        "",
        f"- Geometric total: {scores['geometric_total']}",
        f"- Star average: {bundle['star_average']}/10",
        f"- Confidence grade: {confidence['confidence_grade']}",
        "",
        "## Batch Metadata",
        "",
        "- Batch ID:",
        "- Date mixed:",
        "- Concentration:",
        "- Solvent/carrier:",
        "- Maceration start:",
        "- Maceration end:",
        "- Intervention phase (pre_mix / between_mix / post_mix):",
        "- Recommendation section:",
        "- Observation tags (comma-separated):",
        "- Intervention context:",
        "",
        "## Observed Performance",
        "",
    ]

    for _, label in WEAR_TEST_AXES:
        lines.append(f"- {label} (0-10):")

    lines.extend(
        [
            "",
            "## Observation Notes",
            "",
            "- First 15 minutes:",
            "- 1 hour:",
            "- 4 hours:",
            "- Final drydown:",
            "- Any off-notes or instability:",
            "",
            "## Intervention Hooks",
            "",
            f"- Pre-mix context: {sections['pre_mix']['context']}",
            f"- Between-mix context: {sections['between_mix']['context']}",
            f"- Post-mix context: {sections['post_mix']['context']}",
            "- Use observation_tags to record which phase was actually used.",
            "",
            "## Predicted Reference",
            "",
        ]
    )

    for axis in SCORE_AXES:
        lines.append(f"- {axis}: {scores.get(axis, 0)}")

    lines.extend(["", "## Star Ratings"])
    for key, value in stars.items():
        lines.append(f"- {key}: {round(value, 2)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_predicted_report(path: Path, bundle: dict) -> None:
    formula = bundle["formula"]
    scores = bundle["scores"]
    radar = bundle["character_radar"]
    confidence = bundle["confidence"]
    recommendations = bundle["recommendations"]
    recommendation_sections = bundle["recommendation_sections"]
    prebond = bundle["prebond_analysis"]
    blocked_materials = bundle["blocked_materials"]
    fingerprint = bundle.get("fingerprint", {})
    synergy = bundle.get("synergy_graph", {})
    life_graph = bundle.get("chemical_life_graph", {})
    inventory_names = {item["name"] for item in load_inventory()}
    formula_names = set(formula["ingredients_pct"].keys())

    lines = [
        f"# Verification Report - {formula['name']}",
        "",
        "## Formula",
        "",
        f"- Formula number: {formula['number']}",
        f"- Ingredient count: {len(formula['ingredients_pct'])}",
        f"- Total concentrate: {round(sum(formula['ingredients_pct'].values()), 2)}%",
        "",
        "## Predicted Scores",
        "",
    ]

    for axis in SCORE_AXES:
        lines.append(f"- {axis}: {scores.get(axis, 0)}")

    lines.extend(["", "## Character Radar", ""])
    for dim, value in radar.items():
        lines.append(f"- {dim}: {value}")

    lines.extend(
        [
            "",
            "## Confidence",
            "",
            f"- Grade: {confidence['confidence_grade']}",
            f"- Data confidence: {confidence['data_confidence']}",
            f"- Pairing confidence: {confidence['pairing_confidence']}",
            f"- Prediction confidence: {confidence['prediction_confidence']}",
            f"- Overall confidence: {confidence['overall_confidence']}",
            "",
            "## Chemistry Checks",
            "",
            f"- Must prebond pairs: {len(prebond['must_prebond'])}",
            f"- Beneficial premixes: {len(prebond['benefits'])}",
            f"- Keep separate pairs: {len(prebond['keep_separate'])}",
            f"- Crystalline materials: {', '.join(prebond['crystalline']) if prebond['crystalline'] else 'none'}",
            f"- Blocked materials: {', '.join(blocked_materials) if blocked_materials else 'none'}",
            "",
            "## Top Recommendations",
            "",
        ]
    )

    if recommendations:
        for rec in recommendations:
            lines.extend(_format_recommendation_entry(rec))
    else:
        lines.append("- No high-impact recommendations produced.")

    lines.extend(["", "## Intervention Sections", ""])
    for phase in INTERVENTION_PHASES:
        section = recommendation_sections[phase["key"]]
        lines.append(
            f"- {phase['key']}: {len(section['recommendations'])} recommendation(s), "
            f"{len(section['template'])} template line(s)"
        )

    lines.extend(["", "## Ingredients", ""])
    for ingredient, pct in sorted(formula["ingredients_pct"].items(), key=lambda item: -item[1]):
        dilution = formula["dilutions"].get(ingredient, 1.0)
        lines.append(f"- {ingredient}: {round(pct, 3)}% raw, dilution factor {dilution}")

    if blocked_materials:
        lines.extend(["", "## Data Safety Warnings", ""])
        for ingredient, reason in blocked_materials.items():
            lines.append(f"- {ingredient}: {reason}")

    lines.extend(["", "## Fingerprint", ""])
    lines.extend(_format_material_signature_lines(fingerprint, inventory_names, formula_names))

    lines.extend(["", "## Synergy Graph", ""])
    lines.extend(_format_synergy_lines(synergy))

    lines.extend(["", "## Chemical Life Graph", ""])
    lines.extend(_format_life_graph_lines(life_graph))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison_template(path: Path, bundle: dict) -> None:
    formula = bundle["formula"]
    scores = bundle["scores"]
    stars = bundle["star_ratings"]
    comparison = bundle["comparison"]
    intervention_sections = bundle["recommendation_sections"]

    lines = [
        f"# Comparison Template - {formula['name']}",
        "",
        "Use this file after a wear test. Compare the predicted values below against the observed values you record in the wear-test template.",
        "",
        "## Technical Score Comparison",
        "",
        "| Axis | Predicted | Observed | Delta | Notes |",
        "|---|---:|---:|---:|---|",
    ]

    for axis in SCORE_AXES:
        predicted = comparison["score_axes"].get(axis, scores.get(axis, 0))
        lines.append(f"| {axis} | {predicted} |  |  | |")

    lines.extend(
        [
            "",
            "## Wear-Test Comparison",
            "",
            "| Field | Target | Observed | Delta | Notes |",
            "|---|---:|---:|---:|---|",
        ]
    )

    for _, label in WEAR_TEST_AXES:
        lines.append(f"| {label} |  |  |  | |")

    lines.extend(
        [
            "",
            "## Star Ratings",
            "",
            "| Metric | Predicted | Observed | Delta |",
            "|---|---:|---:|---:|",
        ]
    )

    for key, value in stars.items():
        lines.append(f"| {key} | {round(value, 2)} |  |  |")

    lines.extend(
        [
            "",
            "## Intervention Comparison",
            "",
            "| Phase | Planned Context | Observed Context | Observation Tags | Notes |",
            "|---|---|---|---|---|",
        ]
    )

    for phase in INTERVENTION_PHASES:
        section = intervention_sections[phase["key"]]
        lines.append(
            f"| {phase['key']} | {section['context']} |  | {', '.join(section['observation_tags'])} | |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bundle(bundle: dict, source_file: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    formula = bundle["formula"]
    output_dir = OUTPUT_ROOT / f"{timestamp}-{_slugify(formula['name'])}"
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at": datetime.now().isoformat(),
        "source_file": str(source_file),
        "formula_number": formula["number"],
        "formula_name": formula["name"],
        "bundle_type": "standalone_verification",
    }

    manifest = {
        "created_at": metadata["created_at"],
        "bundle_type": metadata["bundle_type"],
        "source_file": metadata["source_file"],
        "formula_number": formula["number"],
        "formula_name": formula["name"],
        "files": [
            "metadata.json",
            "bundle_manifest.json",
            "verification_summary.json",
            "predicted_report.md",
            "fingerprint_report.md",
            "synergy_report.md",
            "chemical_life_graph.md",
            "temporal_graph.md",
            "temporal_graph.svg",
            "temporal_graph.png",
            "intervention_recommendations.md",
            "mixing_protocol.txt",
            "wear_test_template.md",
            "comparison_template.md",
            "observations.csv",
        ],
        "schemas": {
            "score_axes": SCORE_AXES,
            "wear_test_axes": [label for _, label in WEAR_TEST_AXES],
            "star_axes": list(bundle["star_ratings"].keys()),
            "intervention_phases": [phase["key"] for phase in INTERVENTION_PHASES],
            "observation_fields": [
                "date",
                "batch_id",
                "formula_name",
                "intervention_phase",
                "recommendation_section",
                "observation_tags",
                "issue_tags",
                "desired_effects",
                "must_preserve",
                "must_avoid",
                "intervention_context",
                "bottle_state_file",
                "additions_applied",
                "maceration_days",
                "wear_test_hours",
                "opening_score_10",
                "heart_score_10",
                "drydown_score_10",
                "longevity_score_10",
                "projection_score_10",
                "balance_score_10",
                "overall_score_10",
                "notes",
            ],
        },
    }

    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    (output_dir / "bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    (output_dir / "verification_summary.json").write_text(
        json.dumps(bundle, indent=2),
        encoding="utf-8",
    )
    (output_dir / "mixing_protocol.txt").write_text(
        bundle["mixing_protocol"]["full_text"] + "\n",
        encoding="utf-8",
    )

    write_predicted_report(output_dir / "predicted_report.md", bundle)
    _write_aux_report(
        output_dir / "fingerprint_report.md",
        f"Fingerprint Report - {formula['name']}",
        _format_material_signature_lines(
            bundle.get("fingerprint", {}),
            {item["name"] for item in load_inventory()},
            set(formula["ingredients_pct"].keys()),
        ),
    )
    _write_aux_report(
        output_dir / "synergy_report.md",
        f"Synergy Report - {formula['name']}",
        _format_synergy_lines(bundle.get("synergy_graph", {})),
    )
    _write_aux_report(
        output_dir / "chemical_life_graph.md",
        f"Chemical Life Graph - {formula['name']}",
        _format_life_graph_lines(bundle.get("chemical_life_graph", {})),
    )
    _write_aux_report(
        output_dir / "temporal_graph.md",
        f"Temporal Graph - {formula['name']}",
        _format_temporal_graph_lines(bundle.get("temporal_graph", {})),
    )
    (output_dir / "temporal_graph.svg").write_text(
        _render_temporal_graph_svg(bundle.get("temporal_graph", {}), f"{formula['name']} - Temporal Graph"),
        encoding="utf-8",
    )
    _write_temporal_graph_png(
        output_dir / "temporal_graph.png",
        bundle.get("temporal_graph", {}),
        f"{formula['name']} - Temporal Graph",
    )
    write_intervention_recommendations(output_dir / "intervention_recommendations.md", bundle)
    write_wear_test_template(output_dir / "wear_test_template.md", bundle)
    write_comparison_template(output_dir / "comparison_template.md", bundle)
    write_observations_csv(output_dir / "observations.csv")

    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone formula verification harness")
    parser.add_argument(
        "--formula-file",
        required=True,
        help="Markdown file containing one or more formulas",
    )
    parser.add_argument("--formula", type=int, help="Formula number to verify")
    parser.add_argument("--name", help="Partial formula name to verify")
    args = parser.parse_args()

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    if not formula_path.exists():
        raise FileNotFoundError(f"Formula file not found: {formula_path}")

    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")

    formula = select_formula(formulas, args.formula, args.name)
    bundle = build_verification_bundle(formula)
    output_dir = write_bundle(bundle, formula_path)

    print("Verification bundle created")
    print(f"Formula: {formula['name']} (#{formula['number']})")
    print(f"Output: {output_dir}")
    print("Files:")
    for filename in [
        "metadata.json",
        "bundle_manifest.json",
        "verification_summary.json",
        "predicted_report.md",
        "fingerprint_report.md",
        "synergy_report.md",
        "chemical_life_graph.md",
        "temporal_graph.md",
        "temporal_graph.svg",
        "temporal_graph.png",
        "intervention_recommendations.md",
        "mixing_protocol.txt",
        "wear_test_template.md",
        "comparison_template.md",
        "observations.csv",
    ]:
        print(f"  - {filename}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
