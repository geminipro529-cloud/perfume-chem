"""Standalone intervention recommendation CLI.

This script reads either:
- a formula markdown file with numbered formula sections, or
- a verification bundle directory containing verification_summary.json.

It emits three recommendation views:
- pre_mix
- post_mix
- between_mix

The script is intentionally thin. It uses the shared engine APIs when they are
present, but it also keeps local fallback parsing and reporting so the operator
workflow remains stable if the shared recommendation layer changes later.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

try:
    from engine.formula_recommendations import (
        format_recommendations,
        generate_intervention_recommendations,
        load_inventory,
    )
except Exception:  # pragma: no cover - fallback path for future refactors
    generate_intervention_recommendations = None  # type: ignore[assignment]
    format_recommendations = None  # type: ignore[assignment]
    load_inventory = None  # type: ignore[assignment]

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.ingredient_intelligence import get_profile
from engine.intervention_context import (
    BottleAddition,
    BottleState,
    InterventionContext,
    ObservationProfile,
)
from engine.optimizer.models import FormulaVector, _lookup_material
from engine.optimizer.optimizer import FormulaOptimizer
from engine.optimizer.scoring import FormulaScorer
from engine.solforge.contracts import (
    ExecutionReceiptV1,
    SolForgeCaseV1,
    SolHypothesisSetV1,
)
from engine.solforge.orchestrator import run_solforge_shadow

MODES = ("pre_mix", "post_mix", "between_mix")
DEFAULT_BATCH_ML = 30.0

LOCAL_MODE_PROFILES: dict[str, dict[str, Any]] = {
    "pre_mix": {
        "label": "Pre-mix",
        "purpose": "Formulation-time optimization",
        "dose_scale": 1.0,
        "note": "Use when the formula is still editable.",
    },
    "post_mix": {
        "label": "Post-mix",
        "purpose": "Add-only bottle correction",
        "dose_scale": 0.35,
        "note": "Keep changes micro-dose and additive only.",
    },
    "between_mix": {
        "label": "Between-mix",
        "purpose": "Next-batch iteration informed by observations",
        "dose_scale": 0.65,
        "note": "Use wear-test notes, comparison data, or intent tags.",
    },
}


@dataclass
class SourceFormula:
    number: int | None
    name: str
    ingredients_pct: dict[str, float]
    dilutions: dict[str, float]
    body: str = ""
    source_kind: str = "formula_markdown"
    source_path: str = ""
    bundle_dir: str = ""


def _parse_recorded_addition(value: str) -> BottleAddition:
    """Parse CLI bottle-addition strings like 'Hedione=300'."""
    raw = value.strip()
    if not raw:
        raise ValueError("Empty bottle addition.")

    match = re.match(r"(.+?)(?:=|:)([\d.]+)\s*(ul|uL|µl|pct|%)?\s*$", raw)
    if not match:
        raise ValueError(
            f"Invalid --record-addition '{value}'. Use Material=amount_uL or Material=amount%."
        )

    material = match.group(1).strip()
    amount = float(match.group(2))
    unit = (match.group(3) or "ul").lower()
    if unit in {"pct", "%"}:
        return BottleAddition(material=material, dose_pct=amount)
    return BottleAddition(material=material, amount_ul=amount)


def _load_bottle_state(path: Path) -> BottleState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        return BottleState.from_mapping(payload)
    raise ValueError(f"Invalid bottle state payload in {path}")


def _merge_bottle_state(
    base_state: BottleState | None,
    *,
    source: SourceFormula,
    batch_ml: float,
    recorded_additions: Sequence[BottleAddition],
) -> BottleState | None:
    if base_state is None and not recorded_additions:
        return None

    additions: list[BottleAddition] = []
    notes: list[str] = []
    if base_state is not None:
        additions.extend(base_state.additions)
        notes.extend(base_state.notes)

    timestamp = datetime.now().isoformat(timespec="seconds")
    for addition in recorded_additions:
        additions.append(
            BottleAddition(
                material=addition.material,
                amount_ul=addition.amount_ul,
                dose_pct=addition.dose_pct,
                dilution=addition.dilution,
                note=addition.note,
                recorded_at=addition.recorded_at or timestamp,
            )
        )

    return BottleState(
        batch_volume_ml=batch_ml,
        additions=additions,
        notes=notes,
        source_formula=source.name,
        source_path=source.source_path,
    )


def _write_bottle_state(path: Path, state: BottleState, source: SourceFormula) -> None:
    payload = asdict(state)
    payload["saved_at"] = datetime.now().isoformat(timespec="seconds")
    payload["source_formula"] = source.name
    payload["source_path"] = source.source_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_dilution(raw: str) -> float:
    text = raw.strip()
    if not text:
        return 1.0
    match = re.match(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1)) / 100.0
    return 1.0


def _parse_formula_markdown(path: Path) -> list[SourceFormula]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"^##\s+(\d+)\.\s+(.+?)$", text, flags=re.MULTILINE)
    formulas: list[SourceFormula] = []

    for idx in range(1, len(sections) - 2, 3):
        number = int(sections[idx])
        name = sections[idx + 1].strip()
        body = sections[idx + 2]
        ingredients_ul: dict[str, float] = {}
        dilutions: dict[str, float] = {}

        for line in body.splitlines():
            match = re.match(
                r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
                line,
            )
            if not match:
                continue

            ingredient = match.group(2).replace("**", "").strip()
            dilution_raw = match.group(3).strip()
            amount_ul = float(match.group(4))

            if "ethanol" in ingredient.lower() or "total" in ingredient.lower():
                continue

            ingredients_ul[ingredient] = amount_ul
            dilutions[ingredient] = _parse_dilution(dilution_raw)

        if not ingredients_ul:
            continue

        total_ul = sum(ingredients_ul.values()) or 1.0
        ingredients_pct = {
            ing: round((amount / total_ul) * 100, 4)
            for ing, amount in ingredients_ul.items()
        }

        formulas.append(
            SourceFormula(
                number=number,
                name=name,
                ingredients_pct=ingredients_pct,
                dilutions=dilutions,
                body=body,
                source_kind="formula_markdown",
                source_path=str(path),
            )
        )

    if formulas:
        return formulas

    ingredients_ul: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for line in text.splitlines():
        match = re.match(
            r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
            line,
        )
        if not match:
            continue
        ingredient = match.group(2).replace("**", "").strip()
        dilution_raw = match.group(3).strip()
        amount_ul = float(match.group(4))
        if "ethanol" in ingredient.lower() or "total" in ingredient.lower():
            continue
        ingredients_ul[ingredient] = amount_ul
        dilutions[ingredient] = _parse_dilution(dilution_raw)

    if not ingredients_ul:
        return []

    header_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = header_match.group(1).strip() if header_match else path.stem.replace("_", " ")
    total_ul = sum(ingredients_ul.values()) or 1.0
    ingredients_pct = {
        ing: round((amount / total_ul) * 100, 4)
        for ing, amount in ingredients_ul.items()
    }
    return [
        SourceFormula(
            number=None,
            name=title,
            ingredients_pct=ingredients_pct,
            dilutions=dilutions,
            body=text,
            source_kind="single_formula_markdown",
            source_path=str(path),
        )
    ]




def _select_formula(
    formulas: list[SourceFormula],
    formula_number: int | None,
    formula_name: str | None,
) -> SourceFormula:
    if formula_number is not None:
        for formula in formulas:
            if formula.number == formula_number:
                return formula
        raise ValueError(f"Formula #{formula_number} not found.")

    if formula_name:
        target = formula_name.lower().strip()
        for formula in formulas:
            if target in formula.name.lower():
                return formula
        raise ValueError(f"No formula name matched '{formula_name}'.")

    if len(formulas) == 1:
        return formulas[0]

    raise ValueError("Provide --formula or --name when the file contains multiple formulas.")


def _read_bundle(bundle_dir: Path) -> tuple[SourceFormula, dict[str, Any]]:
    summary_path = bundle_dir / "verification_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing verification_summary.json in {bundle_dir}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    formula = summary.get("formula", {})
    source = SourceFormula(
        number=formula.get("number"),
        name=formula.get("name", bundle_dir.name),
        ingredients_pct=dict(formula.get("ingredients_pct", {})),
        dilutions=dict(formula.get("dilutions", {})),
        body=formula.get("body", ""),
        source_kind="verification_bundle",
        source_path=str(summary_path),
        bundle_dir=str(bundle_dir),
    )
    return source, summary


def _bundle_observation_rows(bundle_dir: Path) -> list[dict[str, str]]:
    path = bundle_dir / "observations.csv"
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle)]
    return [row for row in rows if any((value or "").strip() for value in row.values())]


def _build_formula_vector(formula: SourceFormula) -> FormulaVector:
    return FormulaVector(
        ingredients=dict(formula.ingredients_pct),
        dilutions=dict(formula.dilutions),
    )


def _patch_volatility_helper() -> None:
    """Patch FormulaVector.weighted_volatility_index for the current session.

    A concurrent shared-engine change can leave the method expecting dict-like
    profile objects. The CLI only needs a stable score path, so we replace the
    helper with a safe attribute-based version when required.
    """

    def _safe_weighted_volatility_index(self) -> float | None:
        import math

        eff = self.effective_ingredients()
        total_w = 0.0
        weighted = 0.0
        for name, pct in eff.items():
            mat = _lookup_material(name)
            vp = None
            mw = None
            if mat:
                vp = mat.get("vp")
                mw = mat.get("mw")
            if vp is None or mw is None:
                profile = get_profile(name)
                if profile is not None:
                    if vp is None:
                        vp = getattr(profile, "vp", None)
                    if mw is None:
                        mw = getattr(profile, "mw", None)
            if vp is not None and mw is not None and mw > 0:
                weighted += pct * vp / math.sqrt(mw)
                total_w += pct
        return weighted / total_w if total_w > 0 else None

    FormulaVector.weighted_volatility_index = _safe_weighted_volatility_index  # type: ignore[assignment]


def _maybe_call(func, *args, **kwargs):
    signature = inspect.signature(func)
    supported = {}
    for key, value in kwargs.items():
        if key in signature.parameters:
            supported[key] = value
    return func(*args, **supported)


def _load_inventory_records() -> list[dict[str, Any]]:
    if load_inventory is not None:
        try:
            return load_inventory()
        except Exception:
            pass

    from engine.chemical_data_validator import is_blocked_chemical
    from engine.inventory_parser import inventory_names

    records: list[dict[str, Any]] = []
    for name in inventory_names(
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    ):
        if is_blocked_chemical(name):
            continue
        records.append({"name": name, "dilution": 1.0})
    return records


def _load_mode_profile(mode: str) -> dict[str, Any]:
    normalized = _normalize_mode(mode)
    try:
        import engine.intervention_profiles as intervention_profiles  # type: ignore
    except Exception:
        return dict(LOCAL_MODE_PROFILES[normalized])

    if hasattr(intervention_profiles, "get_mode_profile"):
        profile = intervention_profiles.get_mode_profile(normalized)
        if isinstance(profile, Mapping):
            return dict(profile)

    if hasattr(intervention_profiles, "MODE_PROFILES"):
        profiles = getattr(intervention_profiles, "MODE_PROFILES")
        if isinstance(profiles, Mapping) and normalized in profiles:
            profile = profiles[normalized]
            if isinstance(profile, Mapping):
                return dict(profile)

    return dict(LOCAL_MODE_PROFILES[normalized])


def _normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MODES:
        raise ValueError(f"Unsupported mode '{mode}'. Choose from: {', '.join(MODES)}")
    return normalized


def _build_observation_profile(
    *,
    extra_observations: list[str],
    intent_tags: list[str],
    issue_tags: list[str],
    desired_effects: list[str],
    must_preserve: list[str],
    must_avoid: list[str],
) -> ObservationProfile:
    return ObservationProfile(
        issue_tags=issue_tags,
        desired_effects=[*desired_effects, *intent_tags],
        must_preserve=must_preserve,
        must_avoid=must_avoid,
        notes=extra_observations,
    )


def _format_bottle_state_summary(state: BottleState | None) -> list[str]:
    if state is None or not state.additions:
        return ["none"]
    lines = [
        f"batch_volume_ml: {state.batch_volume_ml}" if state.batch_volume_ml is not None else "batch_volume_ml: unknown",
        f"total_added_ul: {state.total_added_ul()}",
    ]
    for addition in state.additions:
        dose_bits: list[str] = []
        if addition.amount_ul is not None:
            dose_bits.append(f"{addition.amount_ul:.1f} uL")
        if addition.dose_pct is not None:
            dose_bits.append(f"{addition.dose_pct:.4f}%")
        detail = ", ".join(dose_bits) if dose_bits else "dose unknown"
        if addition.recorded_at:
            detail = f"{detail}, recorded_at={addition.recorded_at}"
        lines.append(f"{addition.material}: {detail}")
    return lines


def _extract_observations(
    summary: dict[str, Any] | None,
    bundle_rows: list[dict[str, str]] | None,
    extra_observations: list[str],
    intent_tags: list[str],
    observation_profile: ObservationProfile | None = None,
) -> dict[str, Any]:
    notes: list[str] = []

    if summary:
        comparison = summary.get("comparison")
        if comparison:
            notes.append(f"comparison={json.dumps(comparison, ensure_ascii=False)}")
        blocked = summary.get("blocked_materials")
        if blocked:
            notes.append(f"blocked_materials={json.dumps(blocked, ensure_ascii=False)}")
        confidence = summary.get("confidence")
        if confidence is not None:
            notes.append(f"confidence={json.dumps(confidence, ensure_ascii=False)}")

    if bundle_rows:
        notes.append(f"observations_csv={json.dumps(bundle_rows, ensure_ascii=False)}")

    notes.extend(extra_observations)

    payload: dict[str, Any] = {}
    if notes:
        payload["notes"] = notes
    if intent_tags:
        payload["intent_tags"] = intent_tags
    if observation_profile is not None:
        if observation_profile.issue_tags:
            payload["issue_tags"] = list(observation_profile.issue_tags)
        if observation_profile.desired_effects:
            payload["desired_effects"] = list(observation_profile.desired_effects)
        if observation_profile.must_preserve:
            payload["must_preserve"] = list(observation_profile.must_preserve)
        if observation_profile.must_avoid:
            payload["must_avoid"] = list(observation_profile.must_avoid)
    return payload


def _call_shared_recommendations(
    fv: FormulaVector,
    scores: dict[str, Any],
    *,
    mode: str,
    observations: dict[str, Any] | None,
    intent_tags: list[str],
    style_fingerprint: dict[str, Any],
    batch_ml: float,
    top_n: int,
    context: InterventionContext | None = None,
) -> list[Any]:
    inventory = _load_inventory_records()
    func = generate_intervention_recommendations
    if func is None:  # pragma: no cover - fallback for future refactors
        raise RuntimeError("engine.formula_recommendations is unavailable")

    category_hint, target_style = _derive_style_hints(style_fingerprint)
    kwargs = {
        "inventory": inventory,
        "top_n": top_n,
        "mode": mode,
        "observations": observations,
        "intent_tags": intent_tags,
        "batch_volume_ml": batch_ml,
        "category_hint": category_hint,
        "target_style": target_style,
        "context": context,
    }
    return _maybe_call(func, fv, scores, **kwargs)


def _call_optimizer_notes(
    fv: FormulaVector,
    *,
    mode: str,
    observations: dict[str, Any] | None,
) -> list[str]:
    optimizer = FormulaOptimizer()
    suggest = optimizer.suggest
    try:
        kwargs = {"context": mode}
        if observations is not None:
            kwargs["observations"] = observations
        return list(_maybe_call(suggest, fv, **kwargs))
    except Exception:
        return list(_maybe_call(suggest, fv))


def _format_style_summary(fingerprint: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    dominant = fingerprint.get("dominant_style")
    primary = fingerprint.get("primary_candidate", {})
    if dominant:
        lines.append(f"dominant_style: {dominant}")
    if primary:
        lines.append(
            "primary_candidate: "
            f"{primary.get('style')} "
            f"(kind={primary.get('kind')}, score={primary.get('score')}, "
            f"confidence={primary.get('confidence')})"
        )

    style_candidates = fingerprint.get("style_candidates", []) or []
    category_candidates = fingerprint.get("category_candidates", []) or []
    if style_candidates:
        top = ", ".join(
            f"{item.get('style')}:{item.get('score')}[{item.get('confidence')}]"
            for item in style_candidates[:3]
        )
        lines.append(f"style_candidates: {top}")
    if category_candidates:
        top = ", ".join(
            f"{item.get('style')}:{item.get('score')}[{item.get('confidence')}]"
            for item in category_candidates[:3]
        )
        lines.append(f"category_candidates: {top}")
    return lines


def _derive_style_hints(fingerprint: dict[str, Any]) -> tuple[str | None, str | None]:
    """Infer category/style hints for profile-aware intervention logic."""
    primary = fingerprint.get("primary_candidate", {})
    target_style = None
    if isinstance(primary, Mapping):
        value = str(primary.get("style", "")).strip()
        if value:
            target_style = value
    if target_style is None:
        dominant = str(fingerprint.get("dominant_style", "")).strip()
        if dominant:
            target_style = dominant

    category_hint = None
    for bucket in ("category_candidates", "style_candidates", "candidates"):
        items = fingerprint.get(bucket, [])
        if not isinstance(items, Sequence):
            continue
        for candidate in items:
            if not isinstance(candidate, Mapping):
                continue
            value = str(candidate.get("style", "")).strip()
            if not value:
                continue
            normalized = value.lower().replace("-", "_").replace(" ", "_")
            if normalized in {
                "white_floral",
                "citrus_floral",
                "gourmand",
                "amber",
                "leather",
                "chypre",
                "skin_scent",
                "aquatic",
                "iris",
                "muguet",
                "woody",
                "rose",
            }:
                category_hint = value
                break
        if category_hint:
            break

    return category_hint, target_style


def _recommendation_to_dict(rec: Any, batch_ml: float) -> dict[str, Any]:
    if isinstance(rec, Mapping):
        data = dict(rec)
    else:
        data = asdict(rec)
    data = {key: _json_safe_value(value) for key, value in data.items()}
    dose_pct = float(data.get("dose_pct", 0.0) or 0.0)
    approx_add_ul = data.get("dose_ul")
    if approx_add_ul in (None, ""):
        approx_add_ul = round(batch_ml * 10.0 * dose_pct, 1)
    data["approx_add_ul"] = approx_add_ul
    return data


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _extract_provenance(rec: Any) -> Any:
    if isinstance(rec, Mapping):
        return rec.get("provenance")
    return getattr(rec, "provenance", None)


def _coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        items: list[str] = []
        for key, item in value.items():
            sub_items = _coerce_text_list(item)
            if sub_items:
                for sub_item in sub_items:
                    items.append(f"{key}: {sub_item}")
            else:
                items.append(f"{key}: {item}")
        return [item for item in items if str(item).strip()]
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_coerce_text_list(item))
        return [item for item in items if item.strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_provenance(value: Any) -> list[tuple[str, list[str]]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        items: list[tuple[str, list[str]]] = []
        for key, item in value.items():
            details = _coerce_text_list(item)
            if details:
                items.append((str(key), details))
        return items
    if isinstance(value, (list, tuple, set)):
        items: list[tuple[str, list[str]]] = []
        for entry in value:
            if isinstance(entry, Mapping):
                label = (
                    entry.get("label")
                    or entry.get("source")
                    or entry.get("module")
                    or entry.get("name")
                    or entry.get("logic")
                    or "provenance"
                )
                details: list[str] = []
                for key in ("details", "reasons", "reason", "support", "notes", "value"):
                    if key in entry:
                        details.extend(_coerce_text_list(entry.get(key)))
                if not details:
                    details = [
                        f"{key}: {item}"
                        for key, item in entry.items()
                        if key not in {"label", "source", "module", "name", "logic"}
                    ]
                normalized = [detail for detail in details if str(detail).strip()]
                if normalized:
                    items.append((str(label), normalized))
            else:
                details = _coerce_text_list(entry)
                if details:
                    items.append(("provenance", details))
        return items
    details = _coerce_text_list(value)
    return [("provenance", details)] if details else []


def _has_provenance(recommendations: Sequence[Any]) -> bool:
    return any(_extract_provenance(rec) is not None for rec in recommendations)


def _format_provenance_block(rec: Any) -> list[str]:
    provenance = _normalize_provenance(_extract_provenance(rec))
    if not provenance:
        return []

    lines = ["- Provenance:"]
    for label, details in provenance:
        if len(details) == 1:
            lines.append(f"  - {label}: {details[0]}")
            continue
        lines.append(f"  - {label}:")
        for detail in details:
            lines.append(f"    - {detail}")
    return lines


def _format_recommendation_block(rec: Any, batch_ml: float, index: int) -> list[str]:
    data = _recommendation_to_dict(rec, batch_ml=batch_ml)
    lines = [f"### {index}. {data.get('material', 'Recommendation')}"]
    action = data.get("action")
    if action:
        lines.append(f"- Action: {action}")
    family = data.get("family")
    if family:
        lines.append(f"- Family: {family}")
    profile = data.get("profile")
    if profile:
        lines.append(f"- Profile: {profile}")
    dose_pct_raw = data.get("dose_pct")
    try:
        dose_pct = float(dose_pct_raw) if dose_pct_raw is not None else None
    except (TypeError, ValueError):
        dose_pct = None
    approx_add_ul = data.get("approx_add_ul")
    if dose_pct is not None:
        if approx_add_ul is not None:
            lines.append(f"- Dose: {dose_pct:.4f}% (~{approx_add_ul:.1f} uL)")
        else:
            lines.append(f"- Dose: {dose_pct:.4f}%")
    rationale = data.get("rationale")
    if rationale:
        lines.append(f"- Rationale: {rationale}")
    target_axis = data.get("target_axis")
    if target_axis:
        lines.append(f"- Target axis: {target_axis}")
    delta = data.get("delta")
    new_axis_score = data.get("new_axis_score")
    if delta is not None or new_axis_score is not None:
        axis_line = "- Axis score:"
        parts = []
        if new_axis_score is not None:
            parts.append(f"new={new_axis_score}")
        if delta is not None:
            parts.append(f"delta={delta}")
        lines.append(f"{axis_line} " + ", ".join(parts) if parts else axis_line)
    composite = data.get("new_composite")
    composite_delta = data.get("composite_delta")
    if composite is not None or composite_delta is not None:
        comp_line = "- Composite:"
        parts = []
        if composite is not None:
            parts.append(f"new={composite}")
        if composite_delta is not None:
            parts.append(f"delta={composite_delta}")
        lines.append(f"{comp_line} " + ", ".join(parts) if parts else comp_line)
    provenance_lines = _format_provenance_block(rec)
    if provenance_lines:
        lines.extend(provenance_lines)
    return lines


def _render_markdown(
    *,
    source: SourceFormula,
    mode_payloads: dict[str, dict[str, Any]],
    modes: Sequence[str],
    style_fingerprint: dict[str, Any],
    scores: dict[str, Any],
    batch_ml: float,
    inventory_count: int,
    bottle_state: BottleState | None,
    observation_profile: ObservationProfile,
) -> str:
    lines: list[str] = []
    lines.append("# Intervention Recommendations")
    lines.append("")
    lines.append(f"- Formula: {source.name}")
    if source.number is not None:
        lines.append(f"- Formula number: {source.number}")
    lines.append(f"- Source kind: {source.source_kind}")
    lines.append(f"- Batch assumption: {batch_ml:.1f} mL")
    lines.append(f"- Inventory records available: {inventory_count}")
    lines.append("")

    lines.append("## Bottle State")
    for line in _format_bottle_state_summary(bottle_state):
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Observation Schema")
    summary_lines = observation_profile.as_summary_lines()
    if summary_lines:
        for line in summary_lines:
            lines.append(f"- {line}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Style Context")
    for line in _format_style_summary(style_fingerprint):
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Scores")
    for key, value in sorted(scores.items()):
        if key.startswith("_"):
            continue
        if isinstance(value, (int, float)):
            lines.append(f"- {key}: {value}")
    lines.append("")

    for mode in modes:
        payload = mode_payloads[mode]
        lines.append(f"## {mode}")
        lines.append(f"- Purpose: {payload['mode_profile'].get('purpose', '')}")
        note = payload["mode_profile"].get("note")
        if note:
            lines.append(f"- Mode note: {note}")
        observations_used = payload.get("observations_summary")
        if observations_used:
            lines.append(f"- Observations used: {observations_used}")
        lines.append("")

        recs_raw = payload["recommendations_raw"]
        if _has_provenance(recs_raw):
            for idx, rec in enumerate(recs_raw, start=1):
                lines.extend(_format_recommendation_block(rec, batch_ml=batch_ml, index=idx))
                lines.append("")
        elif format_recommendations is not None:
            lines.append(
                format_recommendations(
                    source.name,
                    recs_raw,
                    scores,
                    mode=mode,
                )
            )
        else:  # pragma: no cover - fallback for future refactors
            lines.append("  Recommendation table unavailable.")

        notes = payload.get("engine_notes", [])
        if notes:
            lines.append("### Engine Notes")
            for note_line in notes:
                lines.append(f"- {note_line}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_json(
    *,
    source: SourceFormula,
    mode_payloads: dict[str, dict[str, Any]],
    modes: Sequence[str],
    style_fingerprint: dict[str, Any],
    scores: dict[str, Any],
    batch_ml: float,
    inventory_count: int,
    bottle_state: BottleState | None,
    observation_profile: ObservationProfile,
) -> str:
    payload = {
        "source": asdict(source),
        "batch_ml": batch_ml,
        "inventory_count": inventory_count,
        "bottle_state": asdict(bottle_state) if bottle_state is not None else None,
        "observation_profile": asdict(observation_profile),
        "style_fingerprint": style_fingerprint,
        "scores": scores,
        "modes": {},
    }
    for mode in modes:
        mode_payload = mode_payloads[mode]
        payload["modes"][mode] = {
            "mode_profile": mode_payload["mode_profile"],
            "observations_summary": mode_payload.get("observations_summary"),
            "recommendations": mode_payload["recommendations"],
            "engine_notes": mode_payload.get("engine_notes", []),
        }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _build_mode_payload(
    *,
    fv: FormulaVector,
    scores: dict[str, Any],
    source: SourceFormula,
    summary: dict[str, Any] | None,
    bundle_rows: list[dict[str, str]] | None,
    mode: str,
    batch_ml: float,
    style_fingerprint: dict[str, Any],
    extra_observations: list[str],
    intent_tags: list[str],
    observation_profile: ObservationProfile,
    bottle_state: BottleState | None,
    top_n: int,
) -> dict[str, Any]:
    mode_profile = _load_mode_profile(mode)

    observation_payload = _extract_observations(
        summary=summary,
        bundle_rows=bundle_rows if mode == "between_mix" else None,
        extra_observations=extra_observations if mode == "between_mix" else [],
        intent_tags=intent_tags,
        observation_profile=observation_profile,
    )
    if mode == "between_mix" and not observation_payload:
        observation_payload = {"notes": ["between_mix requested with no observations; using formula state only."]}

    category_hint, target_style = _derive_style_hints(style_fingerprint)
    context = InterventionContext(
        mode=mode,
        batch_volume_ml=batch_ml,
        category_hint=category_hint,
        target_style=target_style,
        observations=list(observation_profile.issue_tags),
        observation_profile=observation_profile,
        bottle_state=bottle_state,
    )

    recs = _call_shared_recommendations(
        fv,
        scores,
        mode=mode,
        observations=observation_payload,
        intent_tags=intent_tags,
        style_fingerprint=style_fingerprint,
        batch_ml=batch_ml,
        top_n=top_n,
        context=context,
    )
    engine_notes = _call_optimizer_notes(
        fv,
        mode=mode,
        observations=observation_payload,
    )

    formatted_recs = [_recommendation_to_dict(rec, batch_ml=batch_ml) for rec in recs]

    observations_summary = None
    if observation_payload.get("notes"):
        notes = observation_payload["notes"]
        if isinstance(notes, list):
            observations_summary = "; ".join(str(item) for item in notes[:3])
        else:
            observations_summary = str(notes)
    if intent_tags:
        tag_summary = ", ".join(intent_tags)
        observations_summary = f"{observations_summary}; intent_tags={tag_summary}" if observations_summary else f"intent_tags={tag_summary}"
    profile_summary = observation_profile.as_summary_lines()
    if profile_summary:
        joined = "; ".join(profile_summary)
        observations_summary = f"{observations_summary}; {joined}" if observations_summary else joined

    return {
        "mode_profile": mode_profile,
        "observations_summary": observations_summary,
        "recommendations_raw": recs,
        "recommendations": formatted_recs,
        "engine_notes": engine_notes,
        "batch_ml": batch_ml,
        "context_payload": asdict(context),
    }


def build_report(
    source: SourceFormula,
    *,
    summary: dict[str, Any] | None = None,
    bundle_rows: list[dict[str, str]] | None = None,
    modes: Sequence[str] = MODES,
    batch_ml: float = DEFAULT_BATCH_ML,
    extra_observations: list[str] | None = None,
    intent_tags: list[str] | None = None,
    issue_tags: list[str] | None = None,
    desired_effects: list[str] | None = None,
    must_preserve: list[str] | None = None,
    must_avoid: list[str] | None = None,
    bottle_state: BottleState | None = None,
    top_n: int = 5,
    output_format: str = "markdown",
) -> str:
    _patch_volatility_helper()
    fv = _build_formula_vector(source)
    scorer = FormulaScorer()

    extra_observations = extra_observations or []
    intent_tags = intent_tags or []
    observation_profile = _build_observation_profile(
        extra_observations=extra_observations,
        intent_tags=intent_tags,
        issue_tags=issue_tags or [],
        desired_effects=desired_effects or [],
        must_preserve=must_preserve or [],
        must_avoid=must_avoid or [],
    )
    if bottle_state is not None:
        if bottle_state.batch_volume_ml is None:
            bottle_state.batch_volume_ml = batch_ml
        fv = bottle_state.apply_to_formula(fv)

    raw_scores = summary.get("scores") if summary and bottle_state is None else None
    scores = dict(raw_scores) if isinstance(raw_scores, Mapping) else {}
    if not scores:
        scores = scorer.score(fv)

    style_fingerprint = scorer.style_fingerprint(fv)
    inventory_count = len(_load_inventory_records())

    mode_payloads: dict[str, dict[str, Any]] = {}
    for mode in modes:
        mode_payloads[mode] = _build_mode_payload(
            fv=fv,
            scores=scores,
            source=source,
            summary=summary,
            bundle_rows=bundle_rows,
            mode=mode,
            batch_ml=batch_ml,
            style_fingerprint=style_fingerprint,
            extra_observations=extra_observations,
            intent_tags=intent_tags,
            observation_profile=observation_profile,
            bottle_state=bottle_state,
            top_n=top_n,
        )

    if output_format == "json":
        return _render_json(
            source=source,
            mode_payloads=mode_payloads,
            modes=modes,
            style_fingerprint=style_fingerprint,
            scores=scores,
            batch_ml=batch_ml,
            inventory_count=inventory_count,
            bottle_state=bottle_state,
            observation_profile=observation_profile,
        )

    return _render_markdown(
        source=source,
        mode_payloads=mode_payloads,
        modes=modes,
        style_fingerprint=style_fingerprint,
        scores=scores,
        batch_ml=batch_ml,
        inventory_count=inventory_count,
        bottle_state=bottle_state,
        observation_profile=observation_profile,
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Standalone intervention recommendation CLI"
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--formula-file",
        help="Markdown file containing one or more formulas",
    )
    source_group.add_argument(
        "--bundle-dir",
        help="Verification bundle directory containing verification_summary.json",
    )
    source_group.add_argument(
        "--solforge-case",
        help="Canonical solforge_case_v1 JSON input",
    )
    parser.add_argument(
        "--solforge-hypotheses",
        help="Canonical sol_hypothesis_set_v1 JSON input",
    )
    parser.add_argument(
        "--solforge-execution",
        help="Optional canonical execution_receipt_v1 JSON input",
    )
    parser.add_argument(
        "--output-dir",
        help="Required atomic artifact directory for SolForge mode",
    )
    parser.add_argument("--formula", type=int, help="Formula number to select")
    parser.add_argument("--name", help="Partial formula name to select")
    parser.add_argument(
        "--mode",
        choices=["all", *MODES],
        default="all",
        help="Which intervention mode(s) to render",
    )
    parser.add_argument(
        "--batch-ml",
        type=float,
        default=DEFAULT_BATCH_ML,
        help="Batch size used to translate dose%% into approximate microliters",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Maximum recommendations per mode",
    )
    parser.add_argument(
        "--intent-tag",
        action="append",
        default=[],
        help="Optional intent tag to bias between-mix recommendations",
    )
    parser.add_argument(
        "--observation",
        action="append",
        default=[],
        help="Free-text observation to bias between-mix recommendations",
    )
    parser.add_argument(
        "--issue-tag",
        action="append",
        default=[],
        help="Structured issue tag such as top_fades_fast or too_flat",
    )
    parser.add_argument(
        "--desired-effect",
        action="append",
        default=[],
        help="Structured desired effect such as more sophisticated or more lift",
    )
    parser.add_argument(
        "--must-preserve",
        action="append",
        default=[],
        help="Identity cue that must stay intact, such as blood orange dominant",
    )
    parser.add_argument(
        "--must-avoid",
        action="append",
        default=[],
        help="Direction to avoid, such as greener or darker",
    )
    parser.add_argument(
        "--state-file",
        help="JSON bottle-state file to load before scoring recommendations",
    )
    parser.add_argument(
        "--save-state",
        help="Optional path to write the merged bottle state after applying --record-addition",
    )
    parser.add_argument(
        "--record-addition",
        action="append",
        default=[],
        help="Persisted bottle add in the form Material=amount_uL or Material=amount%%",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        help="Optional output file. Defaults to stdout.",
    )
    args = parser.parse_args()

    if args.solforge_case:
        if not args.solforge_hypotheses or not args.output_dir:
            parser.error(
                "--solforge-case requires --solforge-hypotheses and --output-dir"
            )
        return _run_solforge_cli(
            case_path=Path(args.solforge_case),
            hypotheses_path=Path(args.solforge_hypotheses),
            execution_path=(
                Path(args.solforge_execution) if args.solforge_execution else None
            ),
            output_dir=Path(args.output_dir),
        )

    extra_observations = list(args.observation or [])
    intent_tags = list(args.intent_tag or [])
    issue_tags = list(args.issue_tag or [])
    desired_effects = list(args.desired_effect or [])
    must_preserve = list(args.must_preserve or [])
    must_avoid = list(args.must_avoid or [])
    recorded_additions = [_parse_recorded_addition(item) for item in (args.record_addition or [])]

    if args.formula_file:
        source_path = Path(args.formula_file)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
        if not source_path.exists():
            raise FileNotFoundError(f"Formula file not found: {source_path}")

        formulas = _parse_formula_markdown(source_path)
        if not formulas:
            raise ValueError(f"No parseable formulas found in {source_path}")

        source = _select_formula(formulas, args.formula, args.name)
        summary = None
        bundle_rows = None
    else:
        bundle_dir = Path(args.bundle_dir)
        if not bundle_dir.is_absolute():
            bundle_dir = PROJECT_ROOT / bundle_dir
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Bundle directory not found: {bundle_dir}")

        source, summary = _read_bundle(bundle_dir)
        bundle_rows = _bundle_observation_rows(bundle_dir)

    bottle_state = None
    state_path = None
    if args.state_file:
        state_path = Path(args.state_file)
        if not state_path.is_absolute():
            state_path = PROJECT_ROOT / state_path
        if state_path.exists():
            bottle_state = _load_bottle_state(state_path)
        elif not recorded_additions:
            raise FileNotFoundError(f"Bottle state file not found: {state_path}")

    bottle_state = _merge_bottle_state(
        bottle_state,
        source=source,
        batch_ml=args.batch_ml,
        recorded_additions=recorded_additions,
    )
    save_state_path = None
    if args.save_state:
        save_state_path = Path(args.save_state)
        if not save_state_path.is_absolute():
            save_state_path = PROJECT_ROOT / save_state_path
    elif state_path is not None and recorded_additions:
        save_state_path = state_path

    modes = MODES if args.mode == "all" else (args.mode,)
    report = build_report(
        source,
        summary=summary,
        bundle_rows=bundle_rows,
        modes=modes,
        batch_ml=args.batch_ml,
        extra_observations=extra_observations,
        intent_tags=intent_tags,
        issue_tags=issue_tags,
        desired_effects=desired_effects,
        must_preserve=must_preserve,
        must_avoid=must_avoid,
        bottle_state=bottle_state,
        top_n=args.top_n,
        output_format=args.format,
    )

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        output_path.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    if save_state_path is not None and bottle_state is not None:
        _write_bottle_state(save_state_path, bottle_state, source)

    return 0


def _project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_json_bytes(path: Path) -> tuple[bytes, dict[str, Any]]:
    exact = path.read_bytes()
    payload = json.loads(exact.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"SolForge input must be a JSON object: {path}")
    return exact, payload


def _run_solforge_cli(
    *,
    case_path: Path,
    hypotheses_path: Path,
    execution_path: Path | None,
    output_dir: Path,
) -> int:
    """Publish one shadow run atomically without changing legacy CLI behavior."""

    case_path = _project_path(case_path)
    hypotheses_path = _project_path(hypotheses_path)
    execution_path = _project_path(execution_path) if execution_path else None
    output_dir = _project_path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing existing nonempty output directory: {output_dir}")

    case_bytes, case_payload = _read_json_bytes(case_path)
    hypothesis_bytes, hypothesis_payload = _read_json_bytes(hypotheses_path)
    case = SolForgeCaseV1.from_dict(case_payload)
    hypotheses = SolHypothesisSetV1.from_dict(hypothesis_payload)
    input_hashes = {
        str(case_path): hashlib.sha256(case_bytes).hexdigest(),
        str(hypotheses_path): hashlib.sha256(hypothesis_bytes).hexdigest(),
    }
    execution = None
    if execution_path is not None:
        execution_bytes, execution_payload = _read_json_bytes(execution_path)
        execution = ExecutionReceiptV1.from_dict(execution_payload)
        input_hashes[str(execution_path)] = hashlib.sha256(execution_bytes).hexdigest()

    state = run_solforge_shadow(case, hypotheses, execution=execution)
    records = [case, hypotheses]
    for record in (
        state.compiled_experiment,
        execution,
        state.temporal_evidence,
        state.criterion_fit,
        state.decision_receipt,
    ):
        if record is not None:
            records.append(record)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists():
        output_dir.rmdir()
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent
    ) as temporary:
        temporary_path = Path(temporary)
        record_files: list[dict[str, str]] = []
        for record in records:
            payload = record.as_dict()
            schema_version = str(payload["schema_version"])
            filename = f"{schema_version}--{record.record_sha256}.json"
            exact = record.canonical_bytes()
            (temporary_path / filename).write_bytes(exact)
            record_files.append(
                {
                    "filename": filename,
                    "record_sha256": record.record_sha256,
                    "file_sha256": hashlib.sha256(exact).hexdigest(),
                }
            )
        if state.backend_export is not None:
            export_bytes = canonical_json_bytes(state.backend_export)
            export_sha256 = sha256_hex(export_bytes)
            filename = f"solforge_backend_lab_export_v1--{export_sha256}.json"
            (temporary_path / filename).write_bytes(export_bytes)
            record_files.append(
                {
                    "filename": filename,
                    "record_sha256": export_sha256,
                    "file_sha256": export_sha256,
                }
            )
        manifest = {
            "schema_version": "solforge_artifact_manifest_v1",
            "stage": state.stage.value,
            "history": [stage.value for stage in state.history],
            "input_file_sha256": input_hashes,
            "records": record_files,
            "blockers": list(state.blockers),
            "publication_authorized": False,
            "database_write_authorized": False,
            "physical_execution_authorized": False,
            "release_authorized": False,
        }
        (temporary_path / "MANIFEST.json").write_bytes(
            canonical_json_bytes(manifest)
        )
        temporary_path.replace(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
