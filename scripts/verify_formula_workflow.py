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
import math
import re
import sys
import unicodedata
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.chemical_data_validator import blocked_reason
from engine.chemical_life_graph import build_chemical_life_graph
from engine.confidence import ConfidenceScorer
from engine.fingerprint import find_similar_materials, fingerprint_formula
from engine.formula_rating import compute_star_ratings
from engine.formula_recommendations import (
    generate_intervention_recommendations,
    generate_recommendations,
    load_inventory,
)
from engine.ifra_standards import CARRIER_DENSITY_G_ML
from engine.inventory_parser import parse_stock_specification
from engine.material_resolver import resolve_material
from engine.mixer.instructions import build_formula_compounding_protocol
from engine.mixer.prebonding import PreBondingAnalyzer
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
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
    from engine.advisory_stock_strength import declared_stock_fraction

    return declared_stock_fraction(raw)


def _serialize_recommendation(rec: object) -> dict:
    payload = dict(rec) if isinstance(rec, dict) else asdict(rec)
    payload["authority_state"] = "UNVALIDATED_ADVISORY"
    payload["proposal_status"] = "UNVALIDATED_ADVISORY"
    payload["formula_optimization_authority"] = False
    payload["compounding_action_authority"] = False
    payload["requires_controlled_comparison"] = True
    payload["selection_basis"] = "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"
    return payload


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


_BLANK_CELLS = frozenset({"", "-", "--", "---", "\u2014", "\u2013", "na", "n/a"})
# "1:10" / "1/10" with optional basis and carrier after it ("1:10 w/w in DPG").
_RATIO_STRENGTH_RE = re.compile(
    r"^\s*1\s*[:/]\s*(\d+(?:\.\d+)?)(?![\d.,:/])(.*)$", re.DOTALL
)
# A number written with exact 3-digit thousands groups ("1,500", "1 168"),
# or any other run of digits with commas/dots (validated after matching).
_AMOUNT_NUMBER_RE = re.compile(
    r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:\.\d+)?(?!\d)"
    r"|\d[\d,]*(?:\.\d+)?|\.\d+"
)
_EXACT_THOUSANDS_RE = re.compile(r"\d{1,3}(?:[, \u00a0\u202f]\d{3})+(?:\.\d+)?")
_AMOUNT_UNIT_RE = re.compile(
    r"(?<![a-z])(ul|ml|mg|kg|g|drops?)(?![a-z])", re.IGNORECASE
)
# A bare number in a strength column, optionally followed by a basis and/or
# "in <carrier>" ("0.20", "0.1 in DPG", "0.1 w/w in DPG"); anything else
# after the number ("15g/10mL in EtOH") is not a bare number.
_BARE_STRENGTH_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?|\.\d+)((?:\s+(?:w\s*/\s*w|w\s*/\s*v|v\s*/\s*v))?"
    r"(?:\s+in\s+\S.*)?)\s*$",
    re.IGNORECASE | re.DOTALL,
)
_AS_SUPPLIED_CELL_RE = re.compile(r"^\s*(?:neat|as\s+supplied)", re.IGNORECASE)
# A percent or a 1:N / 1/N ratio anywhere in a cell.
_STRENGTH_VALUE_RE = re.compile(r"\d\s*%|(?<![\d.])1\s*[:/]\s*\d")
_PERCENT_VALUE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_STRENGTH_PROBLEM_MESSAGES = {
    "ambiguous_bare_number": (
        "Strength '{cell}' for {material} is ambiguous "
        "(a bare number above 1 may be a percent or a ratio); write 10% w/w in DPG"
    ),
    "neat_with_strength": (
        "Strength '{cell}' for {material} says neat and also gives a strength; "
        "write the strength of the stock used, e.g. neat or 10% w/w in DPG"
    ),
    "ratio_percent_conflict": (
        "Strength '{cell}' for {material} gives a ratio and a percent that disagree; "
        "write one, e.g. 10% w/w in DPG"
    ),
}
_VOLUME_UL_PER_UNIT = {"ul": 1.0, "ml": 1000.0}
_MASS_UNITS = frozenset({"g", "mg", "kg"})
_MASS_G_PER_UNIT = {"mg": 0.001, "g": 1.0, "kg": 1000.0}
# The unit a column header gives its amounts in ("Weigh stock g", "mg").
_MASS_HEADER_UNIT_RE = re.compile(r"(?<![a-z0-9])(mg|kg|g)(?![a-z])")
# A gram column that weighs a carrier, not the stock ("DPG g").
_NOT_STOCK_MASS_HEADER_RE = re.compile(
    r"\b(?:dpg|dep|tec|ipm|ethanol|alcohol|carrier|solvent|diluent)\b"
)
# The batch a gram column is written for ("Add for 10 g trial, g").
_MASS_BATCH_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*g\s+(?:trial|batch|bottle)\b", re.IGNORECASE
)
# Rows of a gram card that sum or top up the stocks above them.
_MASS_CARD_SUM_ROW_RE = re.compile(
    r"\btotals?\b|\bblend\b|\balcohol\b|finished batch"
)
# A header cell that names an amount, in any unit (for the no-rows message).
_AMOUNT_HEADER_RE = re.compile(
    r"amount|weigh|drops?|(?<![a-z0-9])(?:ul|ml|mg|kg|g)(?![a-z])|%|\u00b5l|\u03bcl"
)


def _registry_density_g_ml(material: str) -> float | None:
    """The material's density on record, the same one formula_state uses."""
    registry = resolve_material(material).registry_material
    density = getattr(registry, "density_25c_g_ml", None)
    return float(density) if density else None


def mass_row_ul(
    material: str, mass_g: float, spec: dict[str, object]
) -> tuple[float | None, str | None]:
    """Volume in uL of ``mass_g`` grams of the stock ``spec`` describes.

    A neat stock is its mass over the material's density on record. A diluted
    stock adds its carrier's volume: w/w splits the mass into material and
    carrier (ideal mixing, as the IFRA finished-product estimate does), v/v
    weighs one mL of stock as both parts. No density is ever assumed: a
    missing material or carrier density, an unwritten strength or a basis
    other than w/w or v/v returns ``(None, reason)``.
    """

    if not spec.get("declared"):
        return None, "no strength written; a weighed stock's volume depends on it"
    density = _registry_density_g_ml(material)
    if density is None:
        return None, "no density on record for the material"
    fraction = float(spec.get("fraction") or 0.0)  # type: ignore[arg-type]
    basis = str(spec.get("fraction_basis", "unspecified"))
    if fraction >= 1.0 or basis == "neat":
        return mass_g / density * 1000.0, None
    carrier = str(spec.get("carrier", "") or "").strip()
    carrier_density = CARRIER_DENSITY_G_ML.get(carrier.casefold())
    if carrier_density is None:
        return None, f"carrier {carrier or 'not named'} has no density on record"
    if basis == "mass_fraction":
        return (
            fraction * mass_g / density + (1.0 - fraction) * mass_g / carrier_density
        ) * 1000.0, None
    if basis == "volume_fraction":
        return mass_g / (fraction * density + (1.0 - fraction) * carrier_density) * 1000.0, None
    return None, "strength basis is not w/w or v/v"


def amount_columns_seen(text: str) -> list[str]:
    """Every table header cell in ``text`` that names an amount, in order."""

    lines = text.splitlines()
    seen: list[str] = []
    for idx, line in enumerate(lines[:-1]):
        if not line.strip().startswith("|"):
            continue
        if not re.fullmatch(r"\|[\s:\-|]+\|?", lines[idx + 1].strip()):
            continue
        for cell in line.strip().strip("|").split("|"):
            clean = cell.strip().replace("**", "").replace("`", "")
            if _AMOUNT_HEADER_RE.search(clean.lower()) and clean not in seen:
                seen.append(clean)
    return seen


def read_strength_cell(
    cell: str, header: str = ""
) -> tuple[float | None, dict[str, object], str | None]:
    """Read one formula-row strength cell.

    Returns ``(dilution, stock_spec, problem)``. ``dilution`` always equals
    ``stock_spec["fraction"]``. A blank cell keeps the historical undeclared
    1.0; ``neat``/``100%`` and percent cells are read by
    ``parse_stock_specification``; ``1:N``/``1/N`` cells are read exactly as
    the equivalent percent cell. Any other non-blank cell is unreadable: the
    fraction is ``None`` (never neat) and ``problem`` names why.

    A cell starting with ``neat`` or ``as supplied`` reads as plain ``neat``,
    unless it also gives a percent or ratio (``neat (pre-dil. 10% in DPG)``),
    which is refused (``neat_with_strength``). A ratio cell that also gives a
    percent reads only when the two agree (``1:10 (10%)``); otherwise it is
    refused (``ratio_percent_conflict``).
    A bare number is a percent when the column ``header`` contains ``%``;
    otherwise 0 < n <= 1 is a fraction and n > 1 is refused as ambiguous
    (``ambiguous_bare_number``). A bare number with no basis or carrier stays
    undeclared; with them it follows the equivalent percent cell.
    """

    clean = str(cell or "").strip().replace("**", "").replace("`", "")
    if _AS_SUPPLIED_CELL_RE.match(clean):
        if _STRENGTH_VALUE_RE.search(clean):
            # "neat (pre-dil. 10% in DPG)" says two strengths; read neither.
            spec = parse_stock_specification(clean).as_dict()
            spec["fraction"] = None
            spec["readable"] = False
            return None, spec, "neat_with_strength"
        stock = parse_stock_specification("neat")
        return stock.fraction, stock.as_dict(), None
    stock = parse_stock_specification(clean)
    ratio = _RATIO_STRENGTH_RE.match(clean)
    percent = _PERCENT_VALUE_RE.search(clean)
    if ratio is not None and percent is not None and not math.isclose(
        100.0 / float(ratio.group(1)) if float(ratio.group(1)) else math.inf,
        float(percent.group(1).replace(",", ".")),
        rel_tol=1e-9,
    ):
        # "1:10 (5%)": the ratio and the percent disagree; read neither.
        spec = stock.as_dict()
        spec["fraction"] = None
        spec["readable"] = False
        return None, spec, "ratio_percent_conflict"
    bare = None if stock.declared else _BARE_STRENGTH_RE.match(clean)
    if bare is not None:
        number = float(bare.group(1))
        rest = bare.group(2)
        if "%" in header:
            fraction = number / 100.0
            valid = 0.0 < number <= 100.0
        else:
            fraction = number
            valid = 0.0 < number <= 1.0
        if not valid:
            spec = stock.as_dict()
            spec["fraction"] = None
            spec["readable"] = False
            return None, spec, "ambiguous_bare_number"
        stock = replace(
            parse_stock_specification(f"{fraction * 100.0!r}%{rest}"),
            fraction=fraction,
            raw=clean,
        )
        if not rest.strip():
            stock = replace(stock, fraction_basis="unspecified", declared=False)
        return stock.fraction, stock.as_dict(), None
    if not stock.declared:
        if ratio is not None and float(ratio.group(1)) >= 1.0:
            denominator = float(ratio.group(1))
            equivalent = f"{100.0 / denominator!r}%{ratio.group(2)}"
            stock = replace(
                parse_stock_specification(equivalent),
                fraction=1.0 / denominator,
                raw=clean,
            )
    if stock.declared or clean.lower() in _BLANK_CELLS:
        return stock.fraction, stock.as_dict(), None
    spec = stock.as_dict()
    spec["fraction"] = None
    spec["readable"] = False
    return None, spec, "unreadable_strength"


def read_amount_cell(cell: str, column_unit: str) -> tuple[float | None, str | None]:
    """Read one amount cell in ``column_unit`` (``ul``, ``ml``, ``%``, ``g``, ``mg``, ``kg``).

    Returns ``(value, refusal)``. Parenthesised text is a note and ignored.
    A volume unit written in the cell is converted to the column's unit; a
    mass unit (or drops) is refused, as is more than one number (an edit such
    as ``50 -> 60``) or a comma that is not an exact 3-digit thousands group.
    A blank cell is ``(None, None)``.
    """

    clean = str(cell or "").strip().replace("**", "").replace("`", "")
    if clean.lower() in _BLANK_CELLS:
        return None, None
    outside = re.sub(r"\([^()]*\)", " ", clean)
    outside = outside.replace("\u00b5", "u").replace("\u03bc", "u")
    numbers = _AMOUNT_NUMBER_RE.findall(outside)
    if not numbers:
        return None, None
    if len(numbers) > 1:
        return None, "more than one number outside parentheses"
    token = numbers[0]
    if "," in token and not _EXACT_THOUSANDS_RE.fullmatch(token):
        return None, "comma is not a 3-digit thousands separator"
    value = float(re.sub(r"[, \u00a0\u202f]", "", token))
    if re.search(r"-\s*" + re.escape(token), outside):
        value = -value
    units = {unit.lower() for unit in _AMOUNT_UNIT_RE.findall(outside)}
    if len(units) > 1:
        return None, "more than one unit"
    if units:
        unit = units.pop()
        if unit.startswith("drop"):
            return None, "drops are not a volume"
        if column_unit in _MASS_G_PER_UNIT:
            if unit not in _MASS_UNITS:
                return None, f"unit '{unit}' in a {column_unit} column"
            return value * _MASS_G_PER_UNIT[unit] / _MASS_G_PER_UNIT[column_unit], None
        if unit in _MASS_UNITS:
            return None, f"mass unit '{unit}' in a {column_unit} column"
        if column_unit not in _VOLUME_UL_PER_UNIT:
            return None, f"volume unit '{unit}' in a {column_unit} column"
        value = value * _VOLUME_UL_PER_UNIT[unit] / _VOLUME_UL_PER_UNIT[column_unit]
    return value, None


def _weighed_stock_column(headers: list[str]) -> tuple[int | None, str]:
    """The column giving each row's weighed stock mass, and its mass unit.

    A header's unit is the last ``g``/``mg``/``kg`` word in it ("Add for 10 g
    trial, g" is grams). Carrier columns ("DPG g") and undiluted-product
    columns ("Product g", "Product mass g") are not the weighed stock. Of the
    rest, "practical" beats "weigh", then "add", then "stock", then the first.
    """

    candidates: list[tuple[int, str]] = []
    for idx, header in enumerate(headers):
        units = _MASS_HEADER_UNIT_RE.findall(header)
        if not units or _NOT_STOCK_MASS_HEADER_RE.search(header):
            continue
        if "product" in header and "stock" not in header and "weigh" not in header:
            continue
        candidates.append((idx, units[-1]))
    for word in ("practical", "weigh", "add", "stock"):
        for idx, unit in candidates:
            if word in headers[idx]:
                return idx, unit
    return candidates[0] if candidates else (None, "")


def _parse_formula_rows(
    body: str,
    blockers: list[dict[str, object]] | None = None,
    mass_card: dict[str, object] | None = None,
) -> tuple[dict[str, float], dict[str, float | None], dict[str, dict[str, object]]]:
    """Parse formula rows; a card with no volume rows is read by its gram column.

    Volume and percent tables parse exactly as before. Only when they give no
    row and no hold are weighed-stock columns (``g``/``mg``/``kg``) read: each
    mass row becomes uL through :func:`mass_row_ul`, and a row it can't convert
    is held with its reason in ``blockers``. ``mass_card`` (when given) is
    filled with the card's unit, stock mass, converted volume and stated batch.
    """

    volume_blockers: list[dict[str, object]] = []
    parsed = _parse_formula_rows_by_column(body, volume_blockers)
    if parsed[0] or volume_blockers:
        if blockers is not None:
            blockers.extend(volume_blockers)
        return parsed
    card: dict[str, object] = {}
    parsed = _parse_formula_rows_by_column(body, blockers, card)
    if card and mass_card is not None:
        mass_card.update(card)
    return parsed


def _parse_formula_rows_by_column(
    body: str,
    blockers: list[dict[str, object]] | None = None,
    mass_card: dict[str, object] | None = None,
) -> tuple[dict[str, float], dict[str, float | None], dict[str, dict[str, object]]]:
    """Parse formula rows from a markdown table. Accepts multiple formats.

    Supported:
      | # | Ingredient | Dilution | µL | mL |   (canonical)
      | Ingredient | Dilution | µL |               (no row number)
      | Ingredient | % |                         (percentages, neat)
      | Ingredient | % | Dilution |               (percentages with dilution)

    Handles section headers (**Top**, **Heart**, **Base**) and inline dilutions
    like "(10% in DPG)", "10%" or "1:10 in DPG".

    A row whose strength or amount cell can't be read is held out of the
    returned ingredients (so no physics models it); its strength is ``None``
    in ``dilutions`` and ``stock_specs``, and a blocking message naming the
    material and quoting the cell is appended to ``blockers`` when given.

    With ``mass_card`` given, a table with no uL/mL/% column is read by its
    weighed-stock gram column (never a carrier or undiluted-product column).
    """
    dilutions: dict[str, float | None] = {}
    stock_specs: dict[str, dict[str, object]] = {}
    # Keep percentage rows separate from volume rows.  A value below 100 is
    # not evidence that a table is expressed as percentages: many valid
    # recipes contain small explicit uL transfers.  Percentages are converted
    # only when the amount column itself is explicitly a percent column.
    volume_amounts_ul: dict[str, float] = {}
    percentage_amounts: dict[str, float] = {}
    ingredient_order: list[str] = []
    held_out: set[str] = set()
    unreadable_strength: dict[str, dict[str, object]] = {}
    # Every readable row's own stock spec and amount, in table order, so two
    # rows of one material at two strengths are never read at one strength.
    row_specs: dict[str, list[dict[str, object]]] = {}
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

    def _is_amount_header(header: str) -> bool:
        return bool(
            "amount" in header
            or re.search(r"(?<![a-z])(?:ul|ml|mg|g)(?![a-z])", header)
            or ("formula" in header and "%" in header)
        )

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

    def _is_diagnostic_percent_context(headers: list[str]) -> bool:
        """Identify report columns that describe a result rather than a dose."""

        diagnostic_tokens = (
            "active",
            "air",
            "analysis",
            "bottle",
            "concentration",
            "delta",
            "efficiency",
            "edp",
            "finished",
            "gc-ms",
            "gcms",
            "headspace",
            "ifra",
            "intensity",
            "in stock",
            "margin",
            "oav",
            "odt",
            "percept",
            "rank",
            "score",
            "share",
            "signal",
            "smell",
            "status",
            "target",
            "typical",
            "vapor",
            "verified",
        )
        return any(
            token in header
            for header in headers
            for token in diagnostic_tokens
        )

    def _is_formula_context(section: str, headers: list[str]) -> bool:
        """Return whether a table is labelled as a formula or dosing table."""

        section_text = section.lower().strip()
        if any(
            token in section_text
            for token in (
                "accord",
                "composition",
                "concentrate",
                "dose",
                "formula",
                "ingredient",
                "mix",
                "recipe",
                "stock",
            )
        ):
            return True
        return any(
            token in header
            for header in headers
            for token in ("dilution", "stock")
        )

    def _is_formula_percent_header(
        header: str,
        *,
        section: str,
        headers: list[str],
    ) -> bool:
        """Recognize composition columns without consuming diagnostic percentages.

        A bare ``%``/``percent``/``percentage`` column is the documented
        formula-table form. Longer composition labels are accepted only when
        the table is visibly a formula/dosing table. ``% of total`` is kept
        out of this grammar because it is the common OAV/share report form;
        formula tables should use an explicit concentrate/formula label.
        """

        if _is_diagnostic_percent_context(headers):
            return False
        if header in {"%", "percent", "percentage"}:
            return _is_formula_context(section, headers)
        if not _is_formula_context(section, headers):
            return False
        return any(
            marker in header
            for marker in (
                "formula",
                "of concentrate",
                "of accord",
                "of conc",
                "raw %",
                "dose (% conc",
                "parts %",
            )
        )

    def _skip_ingredient(name: str) -> bool:
        low = re.sub(r"\s+", " ", name.strip().lower())
        if not low:
            return True
        if "~~" in low:
            # Historical formula files retain removed rows with Markdown
            # strikethrough.  They are audit history, not active doses.
            return True
        if low in {"#", "ingredient", "material", "component", "layer", "ord"}:
            return True
        if re.fullmatch(r"[\d.,\s]+(?:u?l|ml|g|%)?", low):
            return True
        if re.search(r"\b(?:sub[- ]?total|total)\b", low):
            return True
        if (
            "ethanol" in low
            or "matured concentrate" in low
            or "final bottle" in low
            or "finished bottle" in low
        ):
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
            "headspace",
            "oav",
            "diagnostic",
            "report",
            "mixing order",
            "accord architecture",
            "material selection rationale",
            "what you'll need",
            "equipment",
            "procedure",
            "finished matrix inputs",
        )
        return any(token in low for token in blocked_tokens)

    def _extract_total_concentrate_ul(text: str) -> float | None:
        """Extract only an explicit, unit-bearing concentrate or batch total."""

        number = r"[+-]?(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d+)?"
        volume_unit = r"(?:mL|[uµμ]L)"
        label_unit_patterns = (
            rf"\bconcentrate\s+(?:target|total|volume)\s*\(\s*({volume_unit})\s*\)[^\n]*?({number})\b",
            rf"\b(?:target|total)\s+concentrate\s*\(\s*({volume_unit})\s*\)[^\n]*?({number})\b",
        )
        for pattern in label_unit_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = _parse_amount(match.group(2))
            if value is None:
                continue
            unit = match.group(1).lower()
            total_ul = value * 1000.0 if unit == "ml" else value
            if total_ul <= 0.0:
                raise ValueError(
                    "explicit concentrate/batch total volume must be positive"
                )
            return total_ul
        patterns = (
            rf"composition of bottle:[^\n]*?({number})\s*({volume_unit})\s+concentrate\b",
            rf"\bconcentrate\s+(?:target|total|volume)\b[^\n]*?({number})\s*({volume_unit})\b",
            rf"\b(?:target|total)\s+concentrate\b[^\n]*?({number})\s*({volume_unit})\b",
            rf"\bbatch\s+(?:target|total|volume)\b[^\n]*?({number})\s*({volume_unit})\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = _parse_amount(match.group(1))
            if value is None:
                continue
            unit = match.group(2).lower()
            total_ul = value * 1000.0 if unit == "ml" else value
            if total_ul <= 0.0:
                raise ValueError(
                    "explicit concentrate/batch total volume must be positive"
                )
            return total_ul
        return None

    lines = body.splitlines()
    total_ul_val = _extract_total_concentrate_ul(body)

    # Parse ingredient rows from markdown tables with usable headers.
    current_headers: list[str] | None = None
    title_match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    current_section = title_match.group(1).strip() if title_match else ""
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
            if _is_formula_percent_header(
                header,
                section=current_section,
                headers=current_headers,
            ):
                percent_idx = i
                break
        amount_mass_idx: int | None = None
        amount_mass_unit = ""
        if (
            mass_card is not None
            and amount_ul_idx is None
            and amount_ml_idx is None
            and percent_idx is None
        ):
            amount_mass_idx, amount_mass_unit = _weighed_stock_column(current_headers)
            if name_idx is None and amount_mass_idx is not None:
                # Gram cards name the row's material "Named product" / "PW product".
                name_idx = next(
                    (
                        i
                        for i, header in enumerate(current_headers)
                        if "product" in header
                        and "%" not in header
                        and not _MASS_HEADER_UNIT_RE.search(header)
                    ),
                    None,
                )
            if amount_mass_idx is not None:
                mass_card.setdefault("amount_unit", amount_mass_unit)
                mass_card.setdefault("amount_column", current_headers[amount_mass_idx])
                # Only the amount column's own header says what batch it fills.
                batch = _MASS_BATCH_RE.search(current_headers[amount_mass_idx])
                mass_card.setdefault(
                    "stated_batch_mass_g", float(batch.group(1)) if batch else None
                )

        if name_idx is None:
            continue
        if (
            amount_ul_idx is None
            and amount_ml_idx is None
            and percent_idx is None
            and amount_mass_idx is None
        ):
            continue
        # An amount column ("Formula %", "Amount (uL stock)") is never the
        # strength column; a "dilution" header wins over other strength words.
        # ("conc" is not one: "% concentrate" / "% of conc" are share columns.)
        amount_cols = {amount_ul_idx, amount_ml_idx, percent_idx, amount_mass_idx}
        strength_cols = [
            i
            for i, header in enumerate(current_headers)
            if i not in amount_cols and not _is_amount_header(header)
        ]
        dilution_idx = next(
            (i for i in strength_cols if "dilution" in current_headers[i]),
            next(
                (
                    i
                    for i in strength_cols
                    if any(
                        token in current_headers[i]
                        for token in ("form", "stock", "strength")
                    )
                ),
                None,
            ),
        )

        if name_idx >= len(parts):
            continue
        ingredient = parts[name_idx].strip()
        if _skip_ingredient(ingredient):
            continue
        if amount_mass_idx is not None and _MASS_CARD_SUM_ROW_RE.search(ingredient.lower()):
            # A gram card's totals, blend and alcohol top-up rows are not stocks.
            continue

        amount_ul: float | None = None
        amount_is_percentage = False
        amount_refusal: tuple[str, str] | None = None
        # If both cells are present, the explicit physical volume remains
        # authoritative. Percentage columns in these tables are derived
        # diagnostics; retaining this precedence avoids double-counting the
        # same row while keeping the historical parser contract stable.
        for column_idx, column_unit in (
            (amount_ul_idx, "ul"),
            (percent_idx, "%"),
            (amount_ml_idx, "ml"),
            (amount_mass_idx, amount_mass_unit),
        ):
            if column_idx is None or column_idx >= len(parts):
                continue
            value, refusal = read_amount_cell(parts[column_idx], column_unit)
            if refusal is not None:
                amount_refusal = (parts[column_idx].strip(), refusal)
                break
            if value is not None:
                amount_ul = value * 1000.0 if column_unit == "ml" else value
                amount_is_percentage = column_unit == "%"
                break
        if amount_refusal is not None:
            held_out.add(ingredient)
            if ingredient not in ingredient_order:
                ingredient_order.append(ingredient)
            if blockers is not None:
                cell_text, refusal = amount_refusal
                blockers.append(
                    {
                        "material": ingredient,
                        "field": "amount",
                        "cell": cell_text,
                        "reason": refusal,
                        "message": (
                            f"Amount '{cell_text}' for {ingredient} can't be read "
                            f"({refusal}); write one number in the column's unit"
                        ),
                    }
                )
            continue
        if amount_ul is None or amount_ul <= 0.0:
            continue

        dilution_cell = ""
        if dilution_idx is not None and dilution_idx < len(parts):
            dilution_cell = parts[dilution_idx]
        dilution, spec, strength_problem = read_strength_cell(
            dilution_cell,
            current_headers[dilution_idx] if dilution_idx is not None else "",
        )

        if ingredient not in ingredient_order:
            ingredient_order.append(ingredient)
        if amount_mass_idx is not None and mass_card is not None and strength_problem is None:
            # amount_ul holds the weighed amount in the column's unit until here.
            mass_g = amount_ul * _MASS_G_PER_UNIT[amount_mass_unit]
            mass_card["stock_mass_g"] = float(mass_card.get("stock_mass_g", 0.0)) + mass_g  # type: ignore[arg-type]
            converted_ul, density_problem = mass_row_ul(ingredient, mass_g, spec)
            if converted_ul is None:
                held_out.add(ingredient)
                if blockers is not None:
                    cell_text = parts[amount_mass_idx].strip()
                    blockers.append(
                        {
                            "material": ingredient,
                            "field": "density",
                            "cell": cell_text,
                            "reason": density_problem,
                            "message": (
                                f"Weighed amount '{cell_text} {amount_mass_unit}' for "
                                f"{ingredient} can't be turned into uL ({density_problem})"
                            ),
                        }
                    )
                continue
            amount_ul = converted_ul
            spec = {**spec, "row_mass_g": mass_g}
        if strength_problem is not None:
            held_out.add(ingredient)
            unreadable_strength[ingredient] = spec
            if blockers is not None:
                cell_text = str(spec.get("raw", ""))
                blockers.append(
                    {
                        "material": ingredient,
                        "field": "strength",
                        "cell": cell_text,
                        "reason": strength_problem,
                        "message": _STRENGTH_PROBLEM_MESSAGES.get(
                            strength_problem,
                            "Strength '{cell}' for {material} can't be read; "
                            "write it as a percent with basis and carrier, "
                            "e.g. 10% w/w in DPG",
                        ).format(cell=cell_text, material=ingredient),
                    }
                )
            continue

        if amount_is_percentage:
            percentage_amounts[ingredient] = (
                percentage_amounts.get(ingredient, 0.0) + amount_ul
            )
        else:
            volume_amounts_ul[ingredient] = (
                volume_amounts_ul.get(ingredient, 0.0) + amount_ul
            )
        if ingredient not in dilutions or dilution != 1.0:
            dilutions[ingredient] = dilution
        stock_specs[ingredient] = spec
        row_specs.setdefault(ingredient, []).append(
            {**spec, "row_amount": amount_ul, "row_amount_is_percentage": amount_is_percentage}
        )

    # An unreadable strength is None in both outputs, never neat; an unreadable
    # strength or amount holds the whole material out of the ingredient rows.
    for ingredient, spec in unreadable_strength.items():
        dilutions[ingredient] = None
        stock_specs[ingredient] = spec

    if mass_card is not None and ingredient_order:
        mass_card["converted_concentrate_ul"] = sum(volume_amounts_ul.values())
        mass_card["held_rows"] = len(held_out)

    if percentage_amounts and total_ul_val is None:
        raise ValueError(
            "formula percentage amount rows require an explicit total "
            "concentrate volume before conversion to uL"
        )

    # Convert only rows whose amount header was explicitly '%' (and preserve
    # any independently declared uL/mL rows for the same material).
    ingredients_ul = {}
    for name in ingredient_order:
        if name in held_out:
            continue
        ingredients_ul[name] = volume_amounts_ul.get(name, 0.0) + (
            percentage_amounts.get(name, 0.0)
            * (float(total_ul_val) / 100.0 if total_ul_val is not None else 0.0)
        )

    for name, rows in row_specs.items():
        if name in ingredients_ul:
            merged = _merge_stock_rows(rows, total_ul_val, name)
            if merged is not None:
                stock_specs[name] = merged
                dilutions[name] = float(merged["fraction"])  # type: ignore[arg-type]

    return ingredients_ul, dilutions, stock_specs


_STOCK_IDENTITY_KEYS = ("fraction", "fraction_basis", "carrier", "declared")


def _strength_unwritten(row: dict[str, object]) -> bool:
    """True for a row whose strength cell gives no strength (read as 1.0)."""
    return not row.get("declared") and row.get("fraction") == 1.0


def _percent_text(fraction: float) -> str:
    return f"{fraction * 100.0:g}%"


def _merge_stock_rows(
    rows: list[dict[str, object]], total_ul_val: float | None, name: str = ""
) -> dict[str, object] | None:
    """One stock spec for a material written on rows with different stocks.

    Returns ``None`` when every row names the same stock. Otherwise the rows
    are two stock lines (for example a neat bottle and a 10% dilution), and no
    row's strength may stand for the others: the merged ``fraction`` is the
    summed active volume over the summed raw volume, so raw x fraction equals
    each row's own raw x strength added up, whatever the row order. The spec
    keeps ``conflict`` (one material name can bind only one live stock) and
    lists every row in ``variants`` with its own raw uL; a basis or carrier the
    rows don't share is left unspecified rather than borrowed from one row.

    A row with no strength written is not a neat stock line: it takes the
    strength of the material's written rows (the highest, if they disagree).
    When that strength is below neat the spec carries ``unwritten_strength``,
    a plain reason the safety gate holds on; rows that are all neat are not
    flagged.
    """
    written = [row for row in rows if not _strength_unwritten(row)]
    unwritten_count = len(rows) - len(written)
    adopted: dict[str, object] | None = None
    if written and unwritten_count:
        adopted = max(written, key=lambda row: float(row["fraction"]))  # type: ignore[arg-type]
        rows = [
            row
            if not _strength_unwritten(row)
            else {
                **adopted,
                "raw": row.get("raw", ""),
                "strength_adopted": True,
                "row_amount": row["row_amount"],
                "row_amount_is_percentage": row["row_amount_is_percentage"],
            }
            for row in rows
        ]
    unwritten_reason: str | None = None
    if adopted is not None and float(adopted["fraction"]) < 1.0:  # type: ignore[arg-type]
        strengths = sorted(
            {float(row["fraction"]) for row in written},  # type: ignore[arg-type]
            reverse=True,
        )
        unwritten_reason = (
            f"{name}: "
            + ("one row gives" if unwritten_count == 1 else f"{unwritten_count} rows give")
            + " no strength, "
            + ("another gives " if len(written) == 1 else "others give ")
            + ", ".join(_percent_text(value) for value in strengths)
            + (
                f" (read at the highest, {_percent_text(strengths[0])})"
                if len(strengths) > 1
                else ""
            )
            + "; confirm which bottle"
        )
    distinct: list[dict[str, object]] = []
    for row in rows:
        if not any(
            all(row.get(key) == seen.get(key) for key in _STOCK_IDENTITY_KEYS)
            for seen in distinct
        ):
            distinct.append(row)
    if len(distinct) < 2:
        if adopted is None:
            return None
        single = {
            key: value
            for key, value in adopted.items()
            if key not in ("row_amount", "row_amount_is_percentage")
        }
        single["declared"] = False
        if unwritten_reason is not None:
            single["unwritten_strength"] = unwritten_reason
        return single
    variants: list[dict[str, object]] = []
    raw_total = 0.0
    active_total = 0.0
    for row in rows:
        amount = float(row["row_amount"])  # type: ignore[arg-type]
        if row.get("row_amount_is_percentage"):
            amount *= float(total_ul_val) / 100.0 if total_ul_val is not None else 0.0
        variant = {
            key: value
            for key, value in row.items()
            if key not in ("row_amount", "row_amount_is_percentage")
        }
        variant["row_raw_ul"] = amount
        variants.append(variant)
        raw_total += amount
        active_total += amount * float(row["fraction"])  # type: ignore[arg-type]
    fractions = {float(row["fraction"]) for row in rows}  # type: ignore[arg-type]
    fraction = (
        fractions.pop()
        if len(fractions) == 1
        else active_total / raw_total
        if raw_total > 0
        else max(fractions)
    )
    bases = {str(row.get("fraction_basis", "unspecified")) for row in rows}
    carriers = {
        str(row.get("carrier", ""))
        for row in rows
        if str(row.get("fraction_basis")) != "neat"
    }
    merged = dict(variants[-1])
    merged.pop("row_raw_ul", None)
    merged.update(
        {
            "fraction": fraction,
            "fraction_basis": bases.pop() if len(bases) == 1 else "unspecified",
            "carrier": carriers.pop() if len(carriers) == 1 else "",
            "declared": not unwritten_count
            and all(bool(row.get("declared")) for row in rows),
            "approximate": any(bool(row.get("approximate")) for row in rows),
            "raw": " + ".join(str(row.get("raw", "")) for row in rows),
            "conflict": True,
            "variants": variants,
            "active_ul": active_total,
        }
    )
    if unwritten_reason is not None:
        merged["unwritten_strength"] = unwritten_reason
    return merged


PIPELINE_ANALYSIS_START = "<!-- PIPELINE_ANALYSIS_START -->"
PIPELINE_ANALYSIS_END = "<!-- PIPELINE_ANALYSIS_END -->"
_PIPELINE_ANALYSIS_HEADING_RE = re.compile(
    r"(?m)^##\s+Pipeline Analysis\b[^\r\n]*\r?$"
)
_PIPELINE_ANALYSIS_MANIFEST_RE = re.compile(
    r"<!--\s*pipeline-analysis-manifest:\s*(\{.*?\})\s*-->",
    flags=re.DOTALL,
)


def split_generated_pipeline_analysis(text: str) -> tuple[str, str]:
    """Return formula source and its generated artifact without cross-contamination."""

    sentinel_index = text.find(PIPELINE_ANALYSIS_START)
    if sentinel_index >= 0:
        return text[:sentinel_index].rstrip(), text[sentinel_index:]
    heading = _PIPELINE_ANALYSIS_HEADING_RE.search(text)
    if heading:
        return text[: heading.start()].rstrip(), text[heading.start() :]
    return text, ""


def parse_pipeline_analysis_manifest(artifact: str) -> dict[str, object] | None:
    match = _PIPELINE_ANALYSIS_MANIFEST_RE.search(artifact or "")
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {"manifest_status": "INVALID_JSON"}
    if not isinstance(parsed, dict):
        return {"manifest_status": "INVALID_TYPE"}
    return parsed


def _infer_family_archetype(body: str) -> str:
    match = re.search(r"\*\*Family archetype:\*\*\s*`?([A-Za-z0-9_.-]+)`?", body)
    return match.group(1).strip() if match else ""


def _parse_finished_matrix(
    body: str,
    dilutions: dict[str, float],
) -> dict[str, object]:
    """Parse an explicit finished-matrix table without treating solvents as odorants.

    The section is deliberately opt-in.  Free prose such as "top up with
    ethanol" is not enough to alter physical calculations; every component
    needs a volume, density, molar mass, and source.
    """

    heading = re.search(
        r"(?im)^#{2,6}\s+finished matrix inputs\s*$",
        body,
    )
    if heading is None:
        return {
            "matrix_components": [],
            "matrix_moles": {},
            "matrix_mass_g": 0.0,
            "matrix_source": "omitted",
        }
    next_heading = re.search(r"(?m)^#{2,6}\s+", body[heading.end() :])
    end = (
        heading.end() + next_heading.start()
        if next_heading is not None
        else len(body)
    )
    section = body[heading.end() : end]
    authority_match = re.search(
        r"(?im)^\s*\*\*matrix authority:\*\*\s*`?([a-z0-9_.-]+)`?\s*$",
        section,
    )
    authority = (
        authority_match.group(1).strip().casefold()
        if authority_match is not None
        else "explicit"
    )
    allowed_authorities = {
        "explicit",
        "declared_volume_proxy",
        "incomplete_stock_carrier",
    }
    if authority not in allowed_authorities:
        raise ValueError(f"Unsupported finished matrix authority: {authority}")

    def cells(line: str) -> list[str]:
        parts = [part.strip() for part in line.strip().split("|")]
        if parts and not parts[0]:
            parts = parts[1:]
        if parts and not parts[-1]:
            parts = parts[:-1]
        return parts

    def normalized(value: str) -> str:
        value = value.replace("µ", "u").replace("μ", "u")
        return re.sub(r"\s+", " ", value.replace("**", "").strip().casefold())

    def number(value: str, label: str) -> float:
        match = re.search(r"[-+]?\d[\d,\s]*(?:\.\d+)?", value)
        if match is None:
            raise ValueError(f"Finished matrix {label} is not numeric: {value!r}")
        parsed = float(match.group(0).replace(",", "").replace(" ", ""))
        if parsed <= 0.0:
            raise ValueError(f"Finished matrix {label} must be greater than zero")
        return parsed

    lines = section.splitlines()
    headers: list[str] | None = None
    components: list[dict[str, object]] = []
    names: set[str] = set()
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        if index + 1 < len(lines) and re.fullmatch(
            r"\|[\s:\-|]+\|?", lines[index + 1].strip()
        ):
            headers = [normalized(cell) for cell in cells(line)]
            continue
        if headers is None or re.fullmatch(r"\|[\s:\-|]+\|?", line.strip()):
            continue
        row = cells(line)
        if len(row) != len(headers):
            raise ValueError("Finished Matrix Inputs row does not match its header")
        values = dict(zip(headers, row))
        name = (values.get("component") or values.get("material") or "").strip()
        if not name:
            raise ValueError("Finished Matrix Inputs requires a Component column")
        key = name.casefold()
        if key in names:
            raise ValueError(f"Duplicate finished matrix component: {name}")
        names.add(key)
        volume_header = next(
            (header for header in headers if "volume" in header),
            None,
        )
        density_header = next(
            (header for header in headers if "density" in header),
            None,
        )
        mw_header = next(
            (header for header in headers if header == "mw g/mol" or "molar mass" in header),
            None,
        )
        source_header = next(
            (header for header in headers if header == "source"),
            None,
        )
        if not all((volume_header, density_header, mw_header, source_header)):
            raise ValueError(
                "Finished Matrix Inputs requires Volume, Density, MW/Molar Mass, and Source columns"
            )
        volume = number(values[volume_header], f"{name} volume")
        if "ml" in volume_header and "ul" not in volume_header:
            volume *= 1000.0
        density = number(values[density_header], f"{name} density")
        molar_mass = number(values[mw_header], f"{name} molar mass")
        source = values[source_header].replace("**", "").replace("`", "").strip()
        if not source:
            raise ValueError(f"Finished matrix component {name} requires a source")
        mass_g = volume / 1000.0 * density
        moles = mass_g / molar_mass
        components.append(
            {
                "name": name,
                "volume_ul": volume,
                "density_g_ml": density,
                "molar_mass_g_mol": molar_mass,
                "mass_g": mass_g,
                "moles": moles,
                "source": source,
            }
        )

    if not components:
        raise ValueError("Finished Matrix Inputs section contains no component rows")
    if authority == "explicit" and any(value < 1.0 for value in dilutions.values()):
        authority = "incomplete_stock_carrier"
    return {
        "matrix_components": components,
        "matrix_moles": {str(row["name"]): float(row["moles"]) for row in components},
        "matrix_mass_g": sum(float(row["mass_g"]) for row in components),
        "matrix_source": authority,
    }


def _parse_compounding_rows(
    body: str,
    ingredients_ul: dict[str, float],
) -> dict[str, object]:
    """Read only explicitly basket-bound physical transfer rows.

    The formula parser accepts several historical dose-table formats.  That is
    appropriate for chemical analysis, but it is not enough authority for a
    physical compounding card: physical rows must retain their raw transfer,
    basket, stock label, and any prepared-dilution identity.  This parser is
    deliberately narrower.  It never infers a basket from note, volatility,
    name, or table order.
    """

    def split_row(line: str) -> list[str]:
        cells = [cell.strip().replace("**", "") for cell in line.split("|")]
        if cells and not cells[0]:
            cells = cells[1:]
        if cells and not cells[-1]:
            cells = cells[:-1]
        return cells

    def normalize(value: str) -> str:
        value = value.strip().replace("**", "").replace("`", "")
        value = value.replace("µ", "u").replace("μ", "u")
        return re.sub(r"\s+", " ", value.casefold())

    def separator(line: str) -> bool:
        stripped = line.strip()
        return bool(
            stripped.startswith("|")
            and re.fullmatch(r"\|[\s:\-|]+\|?", stripped)
        )

    def parse_amount(value: str) -> float | None:
        clean = value.strip().replace("**", "").replace("`", "")
        if clean.casefold() in {"", "-", "--", "---", "—", "–", "na", "n/a"}:
            return None
        match = re.search(r"[-+]?\d[\d,\s]*(?:\.\d+)?", clean)
        if not match:
            return None
        try:
            return float(match.group(0).replace(",", "").replace(" ", ""))
        except ValueError:
            return None

    def find_column(headers: list[str], *phrases: str) -> int | None:
        for index, header in enumerate(headers):
            if any(phrase in header for phrase in phrases):
                return index
        return None

    def cell(cells: list[str], index: int | None) -> str:
        return cells[index].strip() if index is not None and index < len(cells) else ""

    def parse_operation(raw: str) -> tuple[str, str | None]:
        value = normalize(raw)
        if not value or value in {"direct", "direct add", "add"}:
            return "DIRECT_ADD", None
        if value in {"precharge", "pre-charge", "carrier precharge", "pre charge"}:
            return "PRECHARGE", None
        if value in {
            "postcharge",
            "post-charge",
            "post charge",
            "final make-up",
            "final makeup",
            "make-up",
            "makeup",
        }:
            return "POSTCHARGE", None
        return "DIRECT_ADD", f"UNRECOGNIZED_COMPOUNDING_OPERATION:{raw.strip()}"

    lines = body.splitlines()
    current_basket: int | None = None
    headers: list[str] | None = None
    rows: list[dict[str, object]] = []
    blockers: list[str] = []
    explicit_context_seen = False

    for line_index, line in enumerate(lines, 1):
        raw = line.strip()
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", raw)
        if heading:
            basket_match = re.search(
                r"\bbasket\s+([0-9]{1,2})\b",
                heading.group(1),
                flags=re.IGNORECASE,
            )
            if basket_match:
                explicit_context_seen = True
                parsed_basket = int(basket_match.group(1))
                if 1 <= parsed_basket <= 17:
                    current_basket = parsed_basket
                else:
                    current_basket = None
                    blockers.append(
                        f"INVALID_BASKET_AT_SOURCE_LINE:{line_index}:{parsed_basket}"
                    )
            else:
                current_basket = None
            headers = None
            continue

        if not raw.startswith("|"):
            headers = None
            continue
        if separator(raw):
            continue
        if line_index < len(lines) and separator(lines[line_index]):
            headers = [normalize(value) for value in split_row(raw)]
            if find_column(headers, "basket") is not None:
                explicit_context_seen = True
            continue
        if headers is None:
            continue

        cells = split_row(raw)
        name_index = find_column(headers, "ingredient", "material")
        ul_index = find_column(headers, "amount (ul", "amount ul", "raw ul", "transfer ul", "dose ul")
        ml_index = find_column(headers, "amount (ml", "amount ml", "raw ml", "transfer ml", "dose ml")
        basket_index = find_column(headers, "basket")
        if name_index is None or (ul_index is None and ml_index is None):
            continue
        if basket_index is None and current_basket is None:
            continue

        material = cell(cells, name_index).replace("`", "").strip()
        material_key = normalize(material)
        if (
            not material
            or material_key in {"total", "subtotal", "fragrance sub-total", "final bottle total"}
            or "~~" in cell(cells, name_index)
        ):
            continue

        raw_ul = parse_amount(cell(cells, ul_index))
        if raw_ul is None:
            raw_ml = parse_amount(cell(cells, ml_index))
            raw_ul = raw_ml * 1000.0 if raw_ml is not None else None
        if raw_ul is None or raw_ul <= 0.0:
            continue

        basket = current_basket
        basket_cell = cell(cells, basket_index)
        if basket_cell:
            basket_match = re.search(r"\d{1,2}", basket_cell)
            if basket_match:
                parsed_basket = int(basket_match.group(0))
                if 1 <= parsed_basket <= 17:
                    basket = parsed_basket
                else:
                    basket = None
                    blockers.append(
                        f"INVALID_BASKET_AT_SOURCE_LINE:{line_index}:{parsed_basket}"
                    )
            else:
                basket = None
                blockers.append(f"INVALID_BASKET_AT_SOURCE_LINE:{line_index}")

        operation_index = find_column(headers, "operation", "addition method")
        operation, operation_blocker = parse_operation(cell(cells, operation_index))
        if operation_blocker:
            blockers.append(f"{operation_blocker}:SOURCE_LINE_{line_index}")

        stock_label_index = find_column(headers, "physical stock", "stock label", "bottle label")
        dilution_index = find_column(headers, "dilution", "stock strength")
        stock_label = cell(cells, stock_label_index)
        dilution_label = cell(cells, dilution_index)
        if not stock_label:
            stock_label = (
                f"{material} [{dilution_label}]" if dilution_label else material
            )

        prepared_index = find_column(
            headers,
            "prepared dilution id",
            "prepared dilution",
            "dilution id",
        )
        prepared_dilution_id = cell(cells, prepared_index) or None
        row_id_index = find_column(headers, "row id", "transfer id")
        row_id = cell(cells, row_id_index) or f"source-line-{line_index:04d}"
        rows.append(
            {
                "row_id": row_id,
                "material": material,
                "physical_stock_label": stock_label,
                "raw_ul": float(raw_ul),
                "basket": basket,
                "operation": operation,
                "prepared_dilution_id": prepared_dilution_id,
            }
        )

    if not explicit_context_seen:
        return {
            "compounding_rows": [],
            "compounding_row_status": "UNAVAILABLE",
            "compounding_row_blockers": [
                "EXPLICIT_BASKET_ASSIGNMENTS_NOT_DECLARED"
            ],
        }

    if not rows:
        blockers.append("NO_POSITIVE_PHYSICAL_TRANSFER_ROWS_IN_BASKET_CONTEXT")
    else:
        row_ids = [str(row["row_id"]) for row in rows]
        if len(row_ids) != len(set(row_ids)):
            blockers.append("DUPLICATE_PHYSICAL_TRANSFER_ROW_ID")

        parsed_totals: dict[str, float] = {}
        for row in rows:
            if row["operation"] != "DIRECT_ADD":
                continue
            material = str(row["material"])
            parsed_totals[material] = parsed_totals.get(material, 0.0) + float(
                row["raw_ul"]
            )
        for material, expected_ul in ingredients_ul.items():
            actual_ul = parsed_totals.get(material)
            if actual_ul is None or not math.isclose(
                actual_ul,
                float(expected_ul),
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                blockers.append(f"FORMULA_TO_PHYSICAL_ROW_MISMATCH:{material}")
        for material in parsed_totals:
            if material not in ingredients_ul:
                blockers.append(f"PHYSICAL_ROW_NOT_IN_FORMULA:{material}")

    blockers = list(dict.fromkeys(blockers))
    return {
        "compounding_rows": rows,
        "compounding_row_status": "COMPLETE" if not blockers else "WITHHELD",
        "compounding_row_blockers": blockers,
    }


def _build_formula_record(
    number: int,
    name: str,
    body: str,
    ingredients_ul: dict[str, float],
    dilutions: dict[str, float | None],
    stock_specs: dict[str, dict[str, object]],
    embedded_analysis: str = "",
    row_parse_blockers: list[dict[str, object]] | None = None,
    mass_card: dict[str, object] | None = None,
) -> dict:
    total_ul = sum(ingredients_ul.values()) or 1.0
    ingredients_pct = {
        material: round((amount / total_ul) * 100, 4)
        for material, amount in ingredients_ul.items()
    }
    concentrate_ml = round(total_ul / 1000.0, 3)
    matrix = _parse_finished_matrix(body, dilutions)
    compounding_contract = _parse_compounding_rows(body, ingredients_ul)
    return {
        "number": number,
        "name": name,
        "ingredients_ul": ingredients_ul,
        "ingredients_pct": ingredients_pct,
        "dilutions": dilutions,
        "stock_specs": stock_specs,
        # Rows held out of ingredients_ul because a strength or amount cell
        # could not be read. Any entry blocks release and physics output.
        "row_parse_blockers": list(row_parse_blockers or []),
        # Set only for a card read by its weighed-stock gram column.
        **({"mass_card": dict(mass_card)} if mass_card else {}),
        **compounding_contract,
        "concentrate_ml": concentrate_ml,
        "body": body,
        "family_archetype": _infer_family_archetype(body),
        **matrix,
        "embedded_analysis": {
            "present": bool(embedded_analysis),
            "format": (
                "bound_v1"
                if PIPELINE_ANALYSIS_START in embedded_analysis
                else "legacy_unbound"
                if embedded_analysis
                else "none"
            ),
            "manifest": parse_pipeline_analysis_manifest(embedded_analysis),
        },
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
    full_text = path.read_text(encoding="utf-8")
    text, embedded_analysis = split_generated_pipeline_analysis(full_text)
    sections = re.split(r"^##\s+(\d+)\.\s+(.+?)$", text, flags=re.MULTILINE)
    formulas: list[dict] = []

    for idx in range(1, len(sections) - 2, 3):
        number = int(sections[idx])
        name = sections[idx + 1].strip()
        body = sections[idx + 2]
        blockers: list[dict[str, object]] = []
        card: dict[str, object] = {}
        ingredients_ul, dilutions, stock_specs = _parse_formula_rows(body, blockers, card)
        if not ingredients_ul and not blockers:
            continue
        formulas.append(
            _build_formula_record(
                number,
                name,
                body,
                ingredients_ul,
                dilutions,
                stock_specs,
                embedded_analysis,
                blockers,
                card,
            )
        )

    if formulas:
        return formulas

    blockers = []
    card = {}
    ingredients_ul, dilutions, stock_specs = _parse_formula_rows(text, blockers, card)
    if not ingredients_ul and not blockers:
        return []

    title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    name = title_match.group(1).strip() if title_match else path.stem.replace("_", " ")
    return [
        _build_formula_record(
            1,
            name,
            text,
            ingredients_ul,
            dilutions,
            stock_specs,
            embedded_analysis,
            blockers,
            card,
        )
    ]


def formula_row_parse_blocker_messages(formula: dict) -> list[str]:
    """Blocking messages for rows held out because a cell could not be read."""

    return [
        str(blocker.get("message", ""))
        for blocker in formula.get("row_parse_blockers", []) or []
    ]


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


def build_verification_bundle(
    formula: dict,
    *,
    include_advisory_recommendations: bool = False,
) -> dict:
    from engine.advisory_stock_strength import validated_advisory_dilutions

    row_blockers = formula_row_parse_blocker_messages(formula)
    if row_blockers:
        raise ValueError("advisory scoring abstained: " + "; ".join(row_blockers))
    dilutions = validated_advisory_dilutions(
        formula["ingredients_pct"], formula.get("dilutions", {}),
        stock_specs=formula.get("stock_specs"), context="advisory scoring",
    )
    fv = FormulaVector(
        ingredients=dict(formula["ingredients_pct"]),
        dilutions=dilutions,
    )

    _install_formula_vector_compatibility()
    scorer = FormulaScorer()
    scores = scorer.score(fv)
    radar = scorer.formula_character_radar(fv)
    scores = _normalize_legacy_score_axes(fv, scores, radar)
    stars = compute_star_ratings(fv, scores, radar)
    confidence = ConfidenceScorer().score(fv.ingredients)
    if include_advisory_recommendations:
        inventory = load_inventory()
        recommendations = generate_recommendations(
            fv,
            scores,
            inventory=inventory,
            top_n=5,
            scorer=scorer,
            include_unvalidated_advisory=True,
        )
        # The public generate_recommendations default is pre_mix, so retain
        # that exact result for the pre-mix intervention section. This avoids
        # a second equivalent candidate search.
        pre_mix_engine = recommendations
        between_mix_engine = generate_intervention_recommendations(
            fv,
            scores,
            inventory=inventory,
            top_n=5,
            mode="between_mix",
            scorer=scorer,
            include_unvalidated_advisory=True,
        )
        post_mix_engine = generate_intervention_recommendations(
            fv,
            scores,
            inventory=inventory,
            top_n=5,
            mode="post_mix",
            batch_volume_ml=30.0,
            scorer=scorer,
            include_unvalidated_advisory=True,
        )
        advisory_status = "COMPUTED_EXPLICITLY_REQUESTED"
    else:
        # Candidate search is optimization work, not a prerequisite for a
        # verification/compounding bundle. Routine runs remain diagnostic and
        # deterministic without spending time on three independent searches.
        recommendations = []
        pre_mix_engine = []
        between_mix_engine = []
        post_mix_engine = []
        advisory_status = "SKIPPED_NOT_REQUESTED"

    prebond = PreBondingAnalyzer().analyze_formula(fv.ingredients)
    instructions = build_formula_compounding_protocol(
        formula,
        prebond_analysis=prebond,
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
        "recommendations": [
            _serialize_recommendation(rec) for rec in recommendations
        ],
        "ranking": {
            "status": "WITHHELD",
            "value": None,
            "formula_optimization_authority": False,
            "diagnostic_total": scores.get("total"),
            "blockers": [
                "Legacy verification scores are heuristic diagnostics, not a validated formula-quality endpoint.",
                "Any advisory candidate requires a controlled comparison before recompounding authority.",
            ],
        },
        "advisory_recommendation_status": advisory_status,
        "advisory_recommendations_requested": include_advisory_recommendations,
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
        lines.append(
            "- Top-dominance model window: "
            f"~{temporal.get('top_dominance_model_minutes', 0):.0f} model-min"
        )
        base_window = temporal.get("base_dominance_model_hours")
        if base_window is None:
            lines.append("- Base-dominance model window: not reached")
        else:
            lines.append(
                f"- Base-dominance model window: ~{base_window:.0f} model-hr"
            )
        lines.append(
            "- Absolute longevity: unavailable; calibrated skin or blotter "
            "measurements required"
        )
        lines.append(
            f"- Temporal authority: {temporal.get('authority', 'UNKNOWN')}"
        )
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
        "All model-generated dose changes are unvalidated advisory proposals. They do not authorize recompounding; use a controlled comparison.",
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
        "**Ranking authority:** WITHHELD. Scores below are heuristic diagnostics, not a beauty, liking, or recompounding objective.",
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


def _bound_partial_mixture_evaluator(formula: dict, plan: dict):
    """Load one explicit numerical JSON model; never deserialize arbitrary code.

    Only a mapped molecular subcomposition is predicted. Frozen omitted stocks
    remain outside the model, not zero-intensity ingredients or known context.
    """
    import hashlib
    import math

    from scripts.train_odor_predictor import predict_dream_mixture

    spec = plan["numerical_model"]
    if spec.get("kind") != "dream2025_partial_support_v1":
        raise ValueError("Unsupported bound numerical model")

    def bound_bytes(path_string, expected):
        path = (PROJECT_ROOT / path_string).resolve()
        if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file():
            raise ValueError("Numerical model source missing or outside project")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Numerical model source hash drift: {path_string}")
        return content

    receipt = json.loads(bound_bytes(spec["path"], spec["sha256"]))
    model = receipt["fitted_model"]
    for path, digest in model["source_hashes"].items():
        bound_bytes(path, digest)
    mapped = spec["structures"]
    ingredients = {row["material"]: row for row in formula["ingredients"]}
    if not mapped or not set(mapped) <= set(ingredients):
        raise ValueError("Model structure map must match actual formula stocks")
    for name, ingredient in ingredients.items():
        low, high = plan["bounds"][name]
        if name not in mapped and (low != high or low != ingredient["raw_ul"]):
            raise ValueError("Every unmodeled stock must remain frozen")
        if name in mapped:
            if ingredient["stock_fraction_basis"] != "neat" or ingredient["carrier"]:
                raise ValueError("Partial molecular model requires neat mapped stocks")
            source = mapped[name]
            data = json.loads(bound_bytes(source["path"], source["sha256"]))
            record = data["PropertyTable"]["Properties"][0]
            if record["ConnectivitySMILES"] != source["smiles"]:
                raise ValueError("Molecular structure differs from bound PubChem record")
    volume = float(spec["nominal_finished_volume_ul"])
    if not math.isfinite(volume) or volume <= sum(r["raw_ul"] for r in ingredients.values()):
        raise ValueError("Explicit positive nominal finished volume required")

    def evaluate(candidate):
        prediction = predict_dream_mixture(model, [
            {"smiles": row["smiles"], "nominal_fraction": candidate[name] / volume}
            for name, row in sorted(mapped.items())])
        value = prediction["predictions"]["Pleasantness"]
        if not math.isfinite(value):
            raise ValueError("Nonfinite partial-mixture prediction")
        # Monotone loss, not a normalized hedonic score or calibrated probability.
        loss = max(-value, 0.) + math.log1p(math.exp(-abs(value)))
        return {
            "basis": "measured_model_prediction", "losses": {"partial_pleasantness": loss},
            "partial_mixture_prediction": prediction,
            "predicted_full_perfume_liking": None, "perceived_richness": None,
            "perceived_layering": None,
            "sources": [spec["sha256"]],
            "scope": "EXPLORATORY_ISOLATED_MOLECULAR_SUBCOMPOSITION_NOT_FULL_PERFUME",
        }

    return evaluate, {"model_sha256": spec["sha256"], "source_hashes": model["source_hashes"],
                      "mapped_materials": sorted(mapped),
                      "unmodeled_frozen_materials": sorted(set(ingredients) - set(mapped)),
                      "mapped_raw_stock_ul": sum(ingredients[n]["raw_ul"] for n in mapped),
                      "nominal_finished_volume_ul": volume,
                      "matrix_transfer_validated": False, "full_formula_prediction": False}


def _verify_engineering_lineage(proposal):
    """Verify a declared 10-uL rounding lineage without granting model authority."""
    import hashlib

    lineage = proposal.get('lineage')
    if not lineage:
        return {'verified': False, 'status': 'NO_LINEAGE_CLAIM'}
    path = (PROJECT_ROOT / lineage['path']).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file():
        raise ValueError('Engineering lineage receipt missing or outside project')
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != lineage['sha256']:
        raise ValueError('Engineering lineage receipt hash drift')
    receipt = json.loads(content)
    front = receipt.get('design_envelope_fronts', {}).get(lineage['envelope'], {}).get('pareto', [])
    matches = [r for r in front if r.get('source') == lineage['source']
               and {n: round(v / 10) * 10 for n, v in r['formula'].items()} == proposal['formula']]
    if not matches:
        raise ValueError('Engineering candidate does not match cited source/front and 10-uL rounding')
    return {**lineage, 'verified': True, 'rounding_grid_raw_ul': 10,
            'scope': 'HISTORICAL_SEARCH_POINT_LINEAGE_NOT_SENSORY_OR_CURRENT_MODEL_VALIDATION'}


def _validate_engineering_candidate(candidate, baseline, bounds):
    """Parent-selected computational proposal must obey the same stock domain."""
    import math

    if (set(candidate) != set(baseline)
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or not bounds[n][0] <= v <= bounds[n][1]
                   for n, v in candidate.items())
            or not math.isclose(math.fsum(candidate.values()), math.fsum(baseline.values()),
                                rel_tol=1e-12, abs_tol=1e-9)):
        raise ValueError('Engineering candidate violates stock keys, total or bounds')
    return dict(candidate)


def _natural_design_envelopes(candidate):
    """Engineer-declared raw allocation relationships, NOT perceptual laws."""
    c = candidate
    gin = c['Juniper Berry EO'] + c['Coriander Seed EO'] + c['Grapefruit FCF oil Sicilian']
    root = c['Vetiver EO (India)'] + c['Vetikon'] + c['Vetival']
    wood = c['Iso E Super'] + c['Cedarwood Virginia'] + c['Clearwood'] + c['Timberol']
    modifiers = c['Petitgrain EO Paraguay'] + c['Terpinyl Acetate']
    if (c['Cypress EO'] > .10 * c['Juniper Berry EO'] or gin < modifiers
            or c['Vetiver EO (India)'] < .5 * c['Iso E Super']):
        return []
    envelopes = []
    if root >= wood and gin >= .5 * root:
        envelopes.append('vetiver_bodied')
    if gin >= root and root + wood >= 1.5 * gin:
        envelopes.append('gin_forward_developed_base')
    if .75 * wood <= root <= 1.25 * wood and root + wood >= 2 * gin:
        envelopes.append('rounded_woody_vetiver')
    return envelopes


def _bound_natural_mixture_evaluator(formula, plan):
    """Source-bound representative natural expansion, not a whole-perfume model."""
    import hashlib
    import math

    from engine.hedonic_model import expand_natural_scenario
    from scripts.train_odor_predictor import predict_dream_mixture

    spec = plan['numerical_model']
    if spec.get('kind') != 'dream2025_natural_scenarios_v1':
        raise ValueError('Unsupported natural numerical model')

    def bound(path_string, expected):
        path = (PROJECT_ROOT / path_string).resolve()
        if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file():
            raise ValueError('Natural model source missing or outside project')
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f'Natural model source hash drift: {path_string}')
        return json.loads(content) if path.suffix == '.json' else content

    manifest = bound(spec['natural_manifest']['path'], spec['natural_manifest']['sha256'])
    profile_source = manifest['source_hashes']['natural_profile_source']
    bound(profile_source['path'], profile_source['sha256'])
    for path, digest in manifest['source_hashes']['primary_records'].items():
        bound(path, digest)
    model = bound(spec['path'], spec['sha256'])['fitted_model']
    for path, digest in model['source_hashes'].items():
        bound(path, digest)
    natural = manifest['natural_profiles']
    structures = spec['structures']
    ingredients = {r['material']: r for r in formula['ingredients']}
    mapped = set(natural) | set(structures)
    if not mapped or not mapped <= set(ingredients) or set(natural) & set(structures):
        raise ValueError('Natural structure map must match disjoint formula stocks')
    for source in list(structures.values()) + [r for rows in natural.values() for r in rows if r.get('smiles')]:
        record = bound(source['path'], source['sha256'])['PropertyTable']['Properties'][0]
        property_name = source.get('smiles_property', 'ConnectivitySMILES')
        if property_name not in {'ConnectivitySMILES', 'SMILES', 'IsomericSMILES'}:
            raise ValueError('Unsupported source SMILES property')
        if record.get(property_name) != source['smiles']:
            raise ValueError('Natural molecular structure differs from bound record')
    for name, ingredient in ingredients.items():
        low, high = plan['bounds'][name]
        if name not in mapped and (low != high or low != ingredient['raw_ul']):
            raise ValueError('Every unmodeled stock must remain frozen')
        if name in mapped and (ingredient['stock_fraction_basis'] != 'neat' or ingredient['carrier']):
            raise ValueError('Natural molecular model requires neat mapped stocks')
    volume = float(spec['nominal_finished_volume_ul'])
    if not math.isfinite(volume) or volume <= sum(r['raw_ul'] for r in ingredients.values()):
        raise ValueError('Explicit positive nominal finished volume required')
    scenarios = spec['composition_scenarios']
    if not scenarios or len({s['name'] for s in scenarios}) != len(scenarios):
        raise ValueError('Unique named composition scenarios required')

    def evaluate(candidate):
        predictions, losses = {}, {}
        for scenario in scenarios:
            expanded = expand_natural_scenario(candidate,
                {n: r['smiles'] for n, r in structures.items()}, natural, volume,
                multipliers=scenario.get('multipliers'))
            prediction = predict_dream_mixture(model, expanded['components'])
            value = prediction['predictions']['Pleasantness']
            loss = max(-value, 0.) + math.log1p(math.exp(-abs(value)))
            losses[scenario['name']] = loss
            predictions[scenario['name']] = {'prediction': prediction, 'coverage': expanded}
        return {'basis': 'measured_model_prediction', 'losses': losses,
                'scenario_predictions': predictions,
                'design_envelopes': _natural_design_envelopes(candidate),
                'predicted_full_perfume_liking': None, 'perceived_richness': None,
                'perceived_layering': None,
                'scope': 'REPRESENTATIVE_PARTIAL_COMPOSITION_EXPLORATION'}

    return evaluate, {'model_sha256': spec['sha256'],
        'natural_manifest': spec['natural_manifest'], 'mapped_materials': sorted(mapped),
        'unmodeled_frozen_materials': sorted(set(ingredients) - mapped),
        'composition_scenarios': scenarios, 'matrix_transfer_validated': False,
        'full_formula_prediction': False, 'nominal_finished_volume_ul': volume}


def run_design_portfolio(
    formula_path: Path, plan_path: Path, *, review_path: Path | None = None,
    numerical_evaluator=None, numerical_evaluator_version: str | None = None,
) -> dict:
    """Stock-bound research mode; no release pipeline, scoring bundle or mixing card."""
    import hashlib
    import math

    from engine.hedonic_model import evaluate_design_roles, evaluate_targeted_hedonics
    from engine.inventory_parser import materialize_current_inventory
    from engine.optimizer.gate_aware import finalize_design_portfolio, optimize_evidence_portfolio

    formula_bytes, plan_bytes = formula_path.read_bytes(), plan_path.read_bytes()
    formula, plan = json.loads(formula_bytes), json.loads(plan_bytes)
    global_mode = plan.get("schema") == "global_design_portfolio_v1"
    if numerical_evaluator is not None or numerical_evaluator_version is not None:
        raise ValueError("Unbound numerical callbacks are not accepted by the global stock runner")
    if global_mode and review_path is not None:
        raise ValueError("Legacy neighbourhood reviews cannot finalize a global design run")
    formula_hash = hashlib.sha256(formula_bytes).hexdigest()
    inventory_hash = hashlib.sha256((PROJECT_ROOT / "inventory.txt").read_bytes()).hexdigest()
    materialized = materialize_current_inventory()
    inventory_authority = {key: getattr(materialized, key) for key in (
        "source_workbook_sha256", "snapshot_sha256", "overlay_sha256")}
    if (plan.get("schema") not in {"evidence_design_portfolio_v1", "global_design_portfolio_v1"}
            or plan.get("formula_sha256") != formula_hash
            or plan.get("inventory_sha256") != inventory_hash
            or plan.get("inventory_authority") != inventory_authority):
        raise ValueError("Design plan source drift: rebind against current formula/inventory")
    review, review_bytes = None, None
    evidence_hashes = {}
    if review_path is not None:
        review_bytes = review_path.read_bytes()
        review = json.loads(review_bytes)
        if (review.get("schema") != "design_evaluator_review_v1"
                or review.get("formula_sha256") != formula_hash
                or review.get("plan_sha256") != hashlib.sha256(plan_bytes).hexdigest()):
            raise ValueError("Evaluator review source drift: formula/plan mismatch")
        evidence = review.get("evidence_files")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError("Evaluator review requires evidence files")
        for key, item in evidence.items():
            path = (PROJECT_ROOT / item["path"]).resolve()
            if not path.is_relative_to(PROJECT_ROOT.resolve()) or not path.is_file():
                raise ValueError("Evaluator review evidence drift: missing/outside project")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != item["sha256"]:
                raise ValueError(f"Evaluator review evidence drift: {key}")
            evidence_hashes[key] = digest
        for proposal in review["proposals"]:
            if not set(proposal.get("evidence", [])) <= set(evidence):
                raise ValueError("Evaluator review cites unbound evidence")
    stocks = materialized.stocks
    by_id = {}
    for stock in stocks:
        by_id.setdefault(stock.stock_id, []).append(stock)
    baseline = {}
    for ingredient in formula["ingredients"]:
        name = ingredient["material"]
        if name in baseline:
            raise ValueError("Duplicate formula material")
        matches = by_id.get(ingredient["stock_id"], [])
        if len(matches) != 1:
            raise ValueError(f"Exact stock identity unresolved: {name}")
        stock = matches[0]
        if (stock.status != "owned" or not stock.execution_ready
                or stock.identity_name != ingredient["inventory_identity"]
                or stock.fraction_basis != ingredient["stock_fraction_basis"]
                or stock.carrier != ingredient["carrier"]
                or not math.isclose(stock.dilution, ingredient["stock_fraction"], rel_tol=1e-12)):
            raise ValueError(f"Current stock form mismatch: {name}")
        baseline[name] = float(ingredient["raw_ul"])
        low, high = plan["bounds"][name]
        if (low != high and (stock.fraction_basis != "neat" or stock.carrier)):
            raise ValueError(f"Design search cannot change carrier/active-dose basis: {name}")
    if not math.isclose(sum(baseline.values()), formula["nominal_fragrance_stock_subtotal_ul"]):
        raise ValueError("Formula stock subtotal mismatch")

    def feasible(candidate):
        report = evaluate_targeted_hedonics(candidate, target=plan["target"])
        return not report["target_identity"]["violations"]

    def evaluate(candidate, scenario):
        return evaluate_design_roles(candidate, baseline=baseline,
                                     profiles=plan["profiles"], context=scenario)

    if global_mode:
        model_binding = None
        if plan.get("numerical_model"):
            binder = (_bound_natural_mixture_evaluator
                      if plan['numerical_model'].get('kind') == 'dream2025_natural_scenarios_v1'
                      else _bound_partial_mixture_evaluator)
            numerical_evaluator, model_binding = binder(formula, plan)
        if numerical_evaluator is None:
            # A completed qualitative review is not a numerical response model.
            # Do not burn the search budget evaluating the same absent endpoint.
            result = {
                "status": "FAIL_NUMERICAL_EVALUATOR_UNAVAILABLE",
                "search_complete": False, "evaluated_candidates": 0,
                "archive": [], "ranked_candidates": [], "proposal_ledger": [],
                "experimental_recommendation": None, "predicted_liking": None,
                "hedonic_optimization_achieved": False, "sensory_validated": False,
                "release_authorized": False, "requires_premix_trial": False,
                "proposal_counts": {}, "pending_proposals": 0,
                "failure": {
                    "kind": "MISSING_FORMULA_INPUT_TO_ENDPOINT_MODEL",
                    "message": "Material roles and isolated intensity curves do not predict "
                               "full-formula liking, richness or layering. Supply a numerical "
                               "evaluator with supported inputs; do not substitute starting "
                               "ratios, OAV sums or generic pleasantness constants.",
                    "original_recipe_is_winner": False,
                },
            }
        else:
            from engine.optimizer.gate_aware import optimize_global_design
            result = optimize_global_design(
                baseline, evaluate=numerical_evaluator, bounds=plan["bounds"],
                feasible=feasible, budget=plan["budget"], seed=plan["seed"],
                max_workers=plan["max_workers"],
            )
            result.update(
                evaluated_candidates=result["evaluation_counts"]["optimizer"],
                proposal_ledger=[], proposal_counts={}, pending_proposals=0,
                predicted_liking=None, hedonic_optimization_achieved=False,
                requires_premix_trial=False,
                numerical_model_binding=model_binding,
            )
            # Completion of an isolated support-mixture experiment is not a
            # recommendation for the 18-stock gin/vetiver perfume.
            result["partial_model_best_observed"] = result["best_observed_candidate"]
            result["experimental_recommendation"] = None
            result["full_perfume_gate"] = "FAIL_TARGET_AND_MIXTURE_COVERAGE"
            if plan['numerical_model']['kind'] == 'dream2025_natural_scenarios_v1':
                from engine.hedonic_model import pareto_minimize
                records = [r for r in result['archive'] + result['comparator']['archive'] if r['valid']]
                for r in records:
                    r['loss_vector'] = [r['losses'][s['name']]
                                        for s in plan['numerical_model']['composition_scenarios']]
                result['design_envelope_fronts'] = {}
                for name in ('vetiver_bodied', 'gin_forward_developed_base', 'rounded_woody_vetiver'):
                    members = [r for r in records if name in r['evaluation']['design_envelopes']]
                    result['design_envelope_fronts'][name] = {
                        'candidate_count': len(members),
                        'optimizer_count': sum(r['source'] != 'random' for r in members),
                        'random_count': sum(r['source'] == 'random' for r in members),
                        'pareto': pareto_minimize(members),
                    }
                result['engineering_selection_required'] = True
                result['envelope_sampling'] = 'Common broad-domain search; post-filtered allocations, not equal per-envelope budgets'
                if plan.get('engineering_candidate'):
                    proposal = plan['engineering_candidate']
                    if not isinstance(proposal.get('rationale'), str) or not proposal['rationale'].strip():
                        raise ValueError('Explicit engineering selection rationale required')
                    candidate = _validate_engineering_candidate(proposal['formula'], baseline, plan['bounds'])
                    if not _natural_design_envelopes(candidate):
                        raise ValueError('Engineering candidate is outside all declared envelopes')
                    lineage = _verify_engineering_lineage(proposal)
                    result['engineering_candidate'] = {
                        'status': 'ENGINEER_SELECTED_COMPUTATIONAL_CANDIDATE',
                        'formula': candidate, 'rationale': proposal['rationale'],
                        'lineage': lineage,
                        'evaluation': numerical_evaluator(candidate),
                        'mix_ready': False, 'sensory_validated': False,
                        'requires_premix_trial': False, 'release_authorized': False,
                        'exact_active_ppm_ww': None,
                    }
                    result['engineering_candidate_evaluations'] = 1
    else:
        result = optimize_evidence_portfolio(
            baseline, evaluate=evaluate, evaluator_version=plan["evaluator_version"],
            criteria=plan["criteria"], scenarios=plan["scenarios"], lanes=plan["lanes"],
            step_sizes=plan["step_sizes"], bounds=plan["bounds"], feasible=feasible,
            max_rounds=plan["max_rounds"], max_candidates=plan["max_candidates"],
            max_workers=plan["max_workers"],
        )
    groups = []
    for hypothesis in ([] if global_mode else plan.get("priority_hypotheses", [])):
        candidates = [r for r in result["archive"]
                      if r["origin"].get("donor") == hypothesis["donor"]
                      and r["origin"].get("receiver") == hypothesis["receiver"]]
        groups.append({**hypothesis, "amounts_ul_unranked": [
            r["origin"]["amount"] for r in candidates], "candidate_count": len(candidates),
            "proposals": [e for e in result["proposal_ledger"]
                          if e["origin"].get("donor") == hypothesis["donor"]
                          and e["origin"].get("receiver") == hypothesis["receiver"]]})
    result.update(
        formula_sha256=formula_hash, inventory_sha256=inventory_hash,
        inventory_authority=inventory_authority,
        plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
        source_hashes={path: hashlib.sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
                       for path in ("engine/optimizer/gate_aware.py", "engine/hedonic_model.py",
                                    "scripts/verify_formula_workflow.py", "engine/inventory_parser.py")},
        stock_checks_passed=len(baseline), priority_hypotheses=groups,
        profiles=plan["profiles"], design_plan=plan, exact_active_ppm_ww=None,
        release_pipeline_run=False, formula_modified=False,
        scope=plan["scope"],
        evaluator_version=plan["evaluator_version"],
    )
    if review is not None:
        result.update(
            final_decision=finalize_design_portfolio(result, review=review),
            review_sha256=hashlib.sha256(review_bytes).hexdigest(),
            review_evidence_hashes=evidence_hashes,
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone formula verification harness")
    parser.add_argument(
        "--formula-file",
        required=True,
        help="Markdown file containing one or more formulas",
    )
    parser.add_argument("--formula", type=int, help="Formula number to verify")
    parser.add_argument("--name", help="Partial formula name to verify")
    parser.add_argument(
        "--include-advisory-recommendations",
        action="store_true",
        help=(
            "Opt into the slower pre-mix, between-mix, and post-mix candidate "
            "search. Routine verification skips this optimizer work."
        ),
    )
    parser.add_argument("--design-plan", type=Path,
                        help="Run source-bound evidence portfolio on a JSON formula record; no mixing bundle")
    parser.add_argument("--evaluator-review", type=Path,
                        help="Finalize a bounded design run against a hash-bound evaluator review")
    args = parser.parse_args()
    if args.evaluator_review and not args.design_plan:
        parser.error("--evaluator-review requires --design-plan")

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    if not formula_path.exists():
        raise FileNotFoundError(f"Formula file not found: {formula_path}")

    if args.design_plan:
        if args.formula is not None or args.name:
            parser.error("--design-plan uses one JSON record, not --formula/--name")
        plan_path = args.design_plan
        if not plan_path.is_absolute():
            plan_path = PROJECT_ROOT / plan_path
        review_path = args.evaluator_review
        if review_path is not None and not review_path.is_absolute():
            review_path = PROJECT_ROOT / review_path
        result = run_design_portfolio(formula_path, plan_path, review_path=review_path)
        output_dir = PROJECT_ROOT / "output" / "design_portfolios"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json")
        output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({k: result[k] for k in (
            "status", "evaluated_candidates", "stock_checks_passed", "formula_modified",
            "predicted_liking", "proposal_counts", "pending_proposals")}, indent=2))
        print(f"Receipt: {output}")
        if result["design_plan"]["schema"] == "global_design_portfolio_v1":
            print(json.dumps({key: result.get(key) for key in (
                "search_complete", "experimental_recommendation", "evaluation_counts",
                "benchmark_equal_budget", "full_perfume_gate", "failure")}, indent=2))
            return 0 if (result["search_complete"]
                         and not str(result.get("full_perfume_gate", "")).startswith("FAIL")) else 2
        if "final_decision" in result:
            print(json.dumps({key: result["final_decision"][key] for key in (
                "disposition", "bounded_run_complete", "formula_action",
                "hedonic_optimization_achieved", "pending_reviews", "evaluation_error_count"
            )}, indent=2))
            return 0 if result["final_decision"]["bounded_run_complete"] else 2
        return 0

    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")

    formula = select_formula(formulas, args.formula, args.name)
    bundle = build_verification_bundle(
        formula,
        include_advisory_recommendations=args.include_advisory_recommendations,
    )
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
