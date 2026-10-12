"""Yardstick: a code-only scorecard for one formula against a brief, and a duel verdict.

Library module only (no CLI; AGENTS.md RULE 2). Deterministic and read-only: it calls the
release gate's pure functions (stock contract, IFRA safety, musk count, family skeletons,
pre-mix guard) and never runs the gate itself, which writes files.

Rule 1: no score uses an OAV magnitude or OAV share. Named-note detection is binary
(a matching material with screening OAV >= 1 in the note's window, as the brief benchmark
does); swamping uses active-mass share; OAV numbers appear only under ``diagnostics``.
Rule 4: a HOLD is never counted as a pass; it is listed under ``holds``.

Formula input (a plain dict)::

    {"name": str, "batch_volume_ml": 30.0, "parent": <same shape> | None,
     "rows": [{"material": str, "amount": "120", "unit": "uL" | "mg",
               "active_fraction": "0.1", "fraction_basis": str, "carrier": str,
               "stock_id": str, "tier": "top" | "heart" | "base", "role": str}],
     "gate_record": <parse_formula_markdown record, optional>}

``formula_from_markdown`` and ``formula_from_composer`` build it. Every result is a plain,
JSON-serialisable dict (floats rounded; Decimal amounts carried as strings).
"""

from __future__ import annotations

import dataclasses
import functools
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from engine.name_utils import normalize_name

# Finished bottle the bench builds, in mL (user bench rule: bottles are 30 mL).
BOTTLE_ML = 30.0
# Smallest pour the bench makes, in uL (user bench rule: nothing poured under 10 uL).
MIN_POUR_UL = 10.0
# Name-score weights: named notes detectable in their window, excluded notes absent,
# family core groups present. A part with nothing to score is dropped and the rest renormalised.
NAME_WEIGHTS = {"named_notes": 0.70, "excluded_notes": 0.15, "family_architecture": 0.15}
# Family architecture part is multiplied by this when the family's skeleton gate FAILs.
SKELETON_FAIL_FACTOR = 0.5
# Craft-score weights: note support (>= 2 matching materials), no swamping, material count,
# precious-stock caps. A part with nothing to score is dropped and the rest renormalised.
CRAFT_WEIGHTS = {"support": 0.40, "no_swamping": 0.25, "material_count": 0.20, "precious": 0.15}
# Distinct formula materials a named note needs to count as supported.
SUPPORT_MIN_MATERIALS = 2
# Release gate _gate_coty_single_material_limit: advisory max single-material % of active mass.
SINGLE_MATERIAL_LIMIT_PCT = 40.0
# Release gate _gate_master_perfumer: material_count < 6 and > 32 are count issues.
MATERIAL_COUNT_MIN = 6
MATERIAL_COUNT_MAX = 32
# Material count within this many materials outside the band earns half marks.
MATERIAL_COUNT_HALF_MARGIN = 13
# Points taken off the craft total when musks exceed the release gate's musk_count limit.
MUSK_OVER_LIMIT_PENALTY = 5.0
# Duel: a name or craft difference of at least this many points decides the duel.
SCORE_MARGIN = 5.0
# Duel: a crowd-liking difference of at least this much decides. The scale is the crowd
# module's weighted mean valence (-1..1); its 0-100 score is (valence + 1) / 2 * 100, so
# 0.05 valence equals 2.5 score points.
LIKING_MARGIN = 0.05
# Exact-match rows under this amount are treated as absent.
_EPS = 1e-9

# Stock ids the composer gives inventory.txt stocks the gate's stock list doesn't hold
# (engine/personal_inventory.py _live_design_stock).
DESIGN_ONLY_STOCK_PREFIX = "inventory:text-design-only:"

FLOOR_IDS = ("F1_owned_stock", "F2_ifra", "F3_pre_mix_guard", "F4_bottle", "F5_pours", "F6_musks")

Scorecard = dict[str, Any]
Verdict = dict[str, Any]


# ── Formula adapters ────────────────────────────────────────────────────────


def formula_from_markdown(
    path: str | Path,
    *,
    parent_path: str | Path | None = None,
    batch_volume_ml: float = BOTTLE_ML,
) -> dict[str, Any]:
    """Load a formula file with the release gate's own parser (first formula in the file)."""
    from scripts.verify_formula_workflow import parse_formula_markdown

    records = parse_formula_markdown(Path(path))
    if not records:
        raise ValueError(f"no formula rows could be read in {path}")
    record = records[0]
    specs = record.get("stock_specs", {}) or {}
    rows = []
    for name, amount in record["ingredients_ul"].items():
        spec = dict(specs.get(name, {}) or {})
        rows.append({
            "material": name,
            "amount": str(amount),
            "unit": "uL",
            "active_fraction": str(record.get("dilutions", {}).get(name, spec.get("fraction", 1.0))),
            "fraction_basis": str(spec.get("fraction_basis", "")),
            "carrier": str(spec.get("carrier", "")),
        })
    parent = None
    if parent_path is not None:
        parent = formula_from_markdown(parent_path, batch_volume_ml=batch_volume_ml)
    return {
        "name": record["name"],
        "batch_volume_ml": batch_volume_ml,
        "rows": rows,
        "parent": parent,
        "gate_record": record,
    }


def formula_from_composer(result: Mapping[str, Any], *, batch_volume_ml: float = BOTTLE_ML) -> dict:
    """Rows from ``design_formula``'s optimized (else initial) formula.

    ``liquid_concentrate_ul_decimal`` (default "6000") is the liquid stock-charge total for
    one 30 mL bottle (20 %), the same default as the release gate's DEFAULT_CONCENTRATE_UL.
    """
    formula = result.get("optimized_formula") or result.get("initial_formula") or {}
    rows = []
    for row in formula.get("rows", []) or []:
        rows.append({
            "material": row["identity_name"],
            "amount": str(row["amount_decimal"]),
            "unit": str(row.get("amount_unit") or "uL"),
            "active_fraction": str(row.get("stock_fraction_decimal") or "1"),
            "fraction_basis": str(row.get("fraction_basis") or ""),
            "carrier": str(row.get("carrier") or ""),
            "stock_id": str(row.get("stock_id") or ""),
            "role": str(row.get("role") or ""),
            **({"tier": row["tier"]} if row.get("tier") else {}),
        })
    return {
        "name": str(formula.get("name") or result.get("name") or "composer formula"),
        "batch_volume_ml": batch_volume_ml,
        "rows": rows,
        "parent": None,
    }


def _gate_record(formula: Mapping[str, Any]) -> dict[str, Any]:
    """The parsed-formula record the release gate reads. mg rows are modelled 1 mg ~ 1 uL."""
    if formula.get("gate_record"):
        return dict(formula["gate_record"])
    ingredients: dict[str, float] = {}
    active: dict[str, float] = {}
    specs: dict[str, dict[str, Any]] = {}
    for row in formula["rows"]:
        name = str(row["material"])
        amount = float(Decimal(str(row["amount"])))
        fraction = float(Decimal(str(row.get("active_fraction") or "1")))
        ingredients[name] = ingredients.get(name, 0.0) + amount
        active[name] = active.get(name, 0.0) + amount * fraction
        spec = {
            "fraction": fraction,
            "fraction_basis": str(row.get("fraction_basis") or ("neat" if fraction == 1.0 else "")),
            "carrier": str(row.get("carrier") or ""),
            "approximate": False,
            "declared": True,
            "raw": "neat" if fraction == 1.0 else f"{fraction * 100:g}%",
        }
        if row.get("stock_id"):
            spec["stock_id"] = str(row["stock_id"])
        if name in specs and specs[name]["fraction"] != fraction:
            spec["conflict"] = True
        specs[name] = spec
    dilutions = {n: (active[n] / ingredients[n] if ingredients[n] else 1.0) for n in ingredients}
    return {
        "name": str(formula.get("name") or "formula"),
        "ingredients_ul": ingredients,
        "dilutions": dilutions,
        "stock_specs": specs,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _floor(status: str, detail: str, **data: Any) -> dict[str, Any]:
    return {"status": status, "detail": " ".join(str(detail).split())[:400], **data}


def _matches(name: str, subs: Sequence[str]) -> bool:
    low = name.lower()
    return any(str(s).lower() in low for s in subs)


def _note_status(mats: Sequence[Any], formula_names: set[str], subs: Sequence[str]) -> str:
    """Detection status as the brief benchmark's ``_note_eval`` computes it (binary OAV >= 1)."""
    rows = [m for m in mats if m.name in formula_names and _matches(m.name, subs)]
    if not rows:
        return "absent"
    if all(
        m.screening_oav is None or m.odt_air_ppm is None or "odt_air_ppm" in m.missing_fields
        for m in rows
    ):
        return "unknown_physics"
    if any(m.screening_oav is not None and m.screening_oav >= 1 for m in rows):
        return "detectable"
    return "below_threshold"


def _weighted(parts: Mapping[str, float | None], weights: Mapping[str, float]) -> float:
    present = {k: v for k, v in parts.items() if v is not None}
    total_w = sum(weights[k] for k in present)
    if not total_w:
        return 0.0
    return sum(weights[k] * v for k, v in present.items()) / total_w * 100.0


def _r(x: float, nd: int = 4) -> float:
    return round(float(x), nd)


@functools.lru_cache(maxsize=1)
def _owned_stocks() -> tuple[Any, ...]:
    from engine.inventory_parser import parse_current_inventory

    return tuple(
        r for r in parse_current_inventory(unique=False, include_unavailable=True)
        if r.status == "owned"
    )


def _weaker_pourable(name: str, amount_ul: float, fraction: float) -> list[str]:
    """Owned stocks of the same identity, weaker than the row's, that make it >= MIN_POUR_UL."""
    key = normalize_name(name)
    active = amount_ul * fraction
    out = []
    for r in _owned_stocks():
        if key not in {normalize_name(r.identity_name or ""), normalize_name(r.name)}:
            continue
        d = float(r.dilution or 0.0)
        if 0.0 < d < fraction and active / d >= MIN_POUR_UL:
            out.append(f"{r.name} at {d * 100:g}% ({active / d:.4g} uL)")
    return sorted(set(out))


def _gate_call(fn: Callable[[], Any]) -> tuple[str, str, dict]:
    try:
        res = fn()
    except Exception as exc:  # a gate that cannot run holds; it never passes
        return "HOLD", f"check could not run: {type(exc).__name__}: {exc}", {}
    return str(res.status), str(res.detail), dict(res.data or {})


# ── Floors ──────────────────────────────────────────────────────────────────


def _f1_stock(stock_contract: Any) -> dict[str, Any]:
    from engine.pipeline.gates import _classify_preflight_check

    status, detail, _ = _classify_preflight_check(stock_contract.as_dict())
    if status not in {"PASS", "FAIL", "HOLD"}:
        status = "PASS" if status == "WARN" else "HOLD"
    raw_issues = list(stock_contract.data.get("issues", []) or [])
    issues = [f"{i.get('material')}: {i.get('reason')}" for i in raw_issues]
    unbound = [i for i in raw_issues if _is_unbound_design_stock(i)]
    if status == "FAIL" and raw_issues and len(unbound) == len(raw_issues):
        # Owned on the user's inventory.txt, but not yet in the gate's stock list
        # (the composer marks these EXECUTION_STOCK_BINDING_REQUIRED). Rule 0 asks
        # for the disagreement to be reported, not guessed: a hold, never a pass.
        names = ", ".join(str(i.get("material")) for i in unbound)
        detail = (
            f"{len(unbound)} material(s) are owned on inventory.txt but not bound to the "
            f"gate's stock list (complete them on the Stock page): {names}"
        )
        status = "HOLD"
    return _floor(status, detail, issues=issues)


def _is_unbound_design_stock(issue: Mapping[str, Any]) -> bool:
    return issue.get("reason") == "stock_id_not_in_current_inventory" and str(
        issue.get("stock_id", "")
    ).startswith(DESIGN_ONLY_STOCK_PREFIX)


def _f2_ifra(safety: tuple[str, str, dict]) -> dict[str, Any]:
    status, detail, data = safety
    if status in {"FAIL", "HOLD"}:
        return _floor(status, detail)
    counted = {
        c.get("material")
        for t in data.get("constituent_totals", []) or []
        for c in t.get("contributors", []) or []
        if c.get("kind") == "natural"
    }
    not_checked = [u["material"] for u in data.get("undisclosed_bases", []) or []]
    not_checked += [
        w.get("material")
        for w in data.get("warnings", []) or []
        if w.get("ifra_status") == "natural_no_own_standard"
        and w.get("ifra_name") not in counted
        and w.get("material") not in counted
    ]
    if not_checked:
        return _floor(
            "HOLD",
            "IFRA could not check every material (composition not counted): "
            + ", ".join(sorted(set(map(str, not_checked)))),
        )
    return _floor("PASS", detail)


def _f3_pre_mix(formula: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
    from engine.fuckups.pre_mix_guard import PreMixGuardError, evaluate_pre_mix_guard

    parent = formula.get("parent")
    if not parent:
        return _floor("NOT_APPLICABLE", "new formula: no parent to compare against")
    prec = _gate_record(parent)
    try:
        report = evaluate_pre_mix_guard(
            child_ingredients_ul=record["ingredients_ul"],
            child_dilutions=record["dilutions"],
            parent_ingredients_ul=prec["ingredients_ul"],
            parent_dilutions=prec["dilutions"],
        )
    except PreMixGuardError as exc:
        return _floor("HOLD", f"pre-mix guard could not compare: {exc}")
    hard = [f for f in report.findings if f.severity == "FAIL"]
    if hard:
        return _floor(
            "FAIL",
            "; ".join(f"{f.code} {f.material}: {f.detail}" for f in hard),
            codes=sorted({f.code for f in hard}),
        )
    warns = [f.code for f in report.findings]
    return _floor("PASS", "active dose preserved against parent" + (
        f" (warnings: {', '.join(warns)})" if warns else ""), codes=[])


def _f4_bottle(formula: Mapping[str, Any]) -> dict[str, Any]:
    batch = float(formula.get("batch_volume_ml") or 0.0)
    liquid = sum(
        float(Decimal(str(r["amount"]))) for r in formula["rows"] if r.get("unit", "uL") == "uL"
    )
    pct = liquid / (BOTTLE_ML * 1000.0) * 100.0
    problems = []
    if abs(batch - BOTTLE_ML) > _EPS:
        problems.append(f"batch volume {batch:g} mL is not {BOTTLE_ML:g} mL")
    if liquid > BOTTLE_ML * 1000.0:
        problems.append(f"liquid concentrate {liquid:g} uL exceeds {BOTTLE_ML * 1000:g} uL")
    status = "FAIL" if problems else "PASS"
    detail = "; ".join(problems) or f"liquid concentrate {liquid:g} uL = {pct:.2f}% of the bottle"
    return _floor(status, detail, concentrate_ul=_r(liquid, 3), concentrate_pct=_r(pct, 3))


def _f5_pours(formula: Mapping[str, Any]) -> dict[str, Any]:
    short = []
    for row in formula["rows"]:
        if row.get("unit", "uL") != "uL":
            continue  # weighed rows are exempt
        amount = float(Decimal(str(row["amount"])))
        if amount < MIN_POUR_UL:
            fraction = float(Decimal(str(row.get("active_fraction") or "1")))
            fixes = _weaker_pourable(str(row["material"]), amount, fraction)
            short.append(
                f"{row['material']} {amount:g} uL"
                + (f" (pourable as {'; '.join(fixes)})" if fixes else " (no owned weaker dilution)")
            )
    if short:
        return _floor("FAIL", f"rows under {MIN_POUR_UL:g} uL: " + ", ".join(short))
    return _floor("PASS", f"every uL row is at least {MIN_POUR_UL:g} uL")


def _f6_musks(names: Sequence[str]) -> dict[str, Any]:
    from engine.pipeline.gates import _EXCEPTION_ONLY_MUSKS

    hits = sorted(
        n for n in names if any(m in normalize_name(n) for m in _EXCEPTION_ONLY_MUSKS)
    )
    if hits:
        return _floor("FAIL", "exception-only musk present: " + ", ".join(hits))
    return _floor("PASS", "no Tonalide, Macrolide or Musk Ketone")


# ── Scorecard ───────────────────────────────────────────────────────────────


_SKELETON_GATES = (
    "_gate_fougere_skeleton",
    "_gate_chypre_skeleton",
    "_gate_oriental_skeleton",
    "_gate_aquatic_skeleton",
    "_gate_gourmand_skeleton",
)


def score_formula(formula: Mapping[str, Any], brief: Mapping[str, Any]) -> Scorecard:
    """Judge one formula against a brief: floors, holds, name score, craft score, liking."""
    from engine.formulation_intelligence.pleasantness import score_hedonic_crowd
    from engine.pipeline import gates as g
    from engine.pipeline.simulator import simulate_formula

    record = _gate_record(formula)
    batch = float(formula.get("batch_volume_ml") or BOTTLE_ML)
    config = g._resolve_gate_config(record, g.ReleaseGateConfig(batch_volume_ml=batch))
    if brief.get("family"):
        config = dataclasses.replace(config, family_archetype=str(brief["family"]))
    state, stock_contract, _ = g._gate_formula_state(record, config)
    names = sorted(record["ingredients_ul"])
    name_set = set(names)

    safety = _gate_call(lambda: g._gate_safety(
        state, config, g._stock_conflict_materials(record), g._unwritten_strength_reasons(record)
    ))
    floors = {
        "F1_owned_stock": _f1_stock(stock_contract),
        "F2_ifra": _f2_ifra(safety),
        "F3_pre_mix_guard": _f3_pre_mix(formula, record),
        "F4_bottle": _f4_bottle(formula),
        "F5_pours": _f5_pours(formula),
        "F6_musks": _f6_musks(names),
    }
    holds: list[dict[str, str]] = [
        {"source": fid, "detail": f["detail"]} for fid, f in floors.items() if f["status"] == "HOLD"
    ]

    frames = simulate_formula(
        record["ingredients_ul"], record["dilutions"], batch_volume_ml=batch, initial_state=state
    )
    mats_by_label = {fr.label: fr.state.materials for fr in frames}

    # Name score.
    notes = []
    for note in brief.get("named_notes", []) or []:
        status = _note_status(mats_by_label.get(note["window"], []), name_set, note["materials"])
        notes.append({
            "name": note["name"], "window": note["window"], "status": status,
            "score": 1 if status == "detectable" else 0,
        })
        if status == "unknown_physics":
            holds.append({"source": "named_note", "detail": f"{note['name']} ({note['window']})"})
    exclusions = []
    for note in brief.get("excluded_notes", []) or []:
        hits = sorted(n for n in names if _matches(n, note["materials"]))
        exclusions.append({"name": note["name"], "matched": hits, "score": 0 if hits else 1})
    groups = []
    for group in brief.get("family_core_groups", []) or []:
        hits = sorted(n for n in names if _matches(n, group))
        groups.append({"group": list(group), "matched": hits, "score": 1 if hits else 0})
    skeletons = []
    for gate_name in _SKELETON_GATES:
        status, detail, _ = _gate_call(lambda fn=getattr(g, gate_name): fn(state, config))
        if detail != "not applicable":
            skeletons.append({"gate": gate_name.removeprefix("_gate_"), "status": status,
                              "detail": detail})
    family_part = None
    if groups:
        family_part = sum(g["score"] for g in groups) / len(groups)
        if any(s["status"] == "FAIL" for s in skeletons):
            family_part *= SKELETON_FAIL_FACTOR
    name_parts = {
        "named_notes": sum(n["score"] for n in notes) / len(notes) if notes else None,
        "excluded_notes": (
            sum(e["score"] for e in exclusions) / len(exclusions) if exclusions else None
        ),
        "family_architecture": family_part,
    }
    name_score = _weighted(name_parts, NAME_WEIGHTS)

    # Craft score.
    support = []
    for note in brief.get("named_notes", []) or []:
        hits = sorted(n for n in names if _matches(n, note["materials"]))
        support.append({"name": note["name"], "materials": hits,
                        "supported": len(hits) >= SUPPORT_MIN_MATERIALS})
    mass_pct = state.active_mass_percentages()
    basis = "active_mass_pct"
    if mass_pct is None:  # exact mass unavailable: fall back to active uL share
        total_active = sum(m.active_ul for m in state.materials) or 1.0
        mass_pct = {}
        for m in state.materials:
            mass_pct[m.name] = mass_pct.get(m.name, 0.0) + m.active_ul / total_active * 100.0
        basis = "active_ul_pct (exact active mass unavailable)"
    top_name, top_pct = max(mass_pct.items(), key=lambda kv: kv[1]) if mass_pct else ("", 0.0)
    count = int(state.material_count)
    if MATERIAL_COUNT_MIN <= count <= MATERIAL_COUNT_MAX:
        count_part = 1.0
    elif MATERIAL_COUNT_MIN - MATERIAL_COUNT_HALF_MARGIN <= count <= (
        MATERIAL_COUNT_MAX + MATERIAL_COUNT_HALF_MARGIN
    ):
        count_part = 0.5
    else:
        count_part = 0.0
    caps = dict(brief.get("precious_caps", {}) or {})
    cap_breaches = []
    for sub, cap in sorted(caps.items()):
        for row in formula["rows"]:
            if row.get("unit", "uL") == "uL" and _matches(str(row["material"]), [sub]):
                ul_per_bottle = float(Decimal(str(row["amount"]))) * BOTTLE_ML / batch
                if ul_per_bottle > float(cap) + _EPS:
                    cap_breaches.append(f"{row['material']} {ul_per_bottle:g} uL > {cap} uL")
    musk_status, musk_detail, musk_data = _gate_call(lambda: g._gate_musk_count(state, config))
    musks = list(musk_data.get("musks", []) or [])
    musk_limit = int(musk_data.get("limit", g._MUSK_COUNT_LIMIT))
    musk_over = len(musks) > musk_limit
    craft_parts = {
        "support": sum(s["supported"] for s in support) / len(support) if support else None,
        "no_swamping": 1.0 if top_pct <= SINGLE_MATERIAL_LIMIT_PCT else 0.0,
        "material_count": count_part,
        "precious": 0.0 if cap_breaches else 1.0,
    }
    craft_score = max(
        0.0, _weighted(craft_parts, CRAFT_WEIGHTS) - (MUSK_OVER_LIMIT_PENALTY if musk_over else 0.0)
    )

    # Liking (tie-break only).
    active_ul = {n: record["ingredients_ul"][n] * record["dilutions"][n] for n in names}
    hed = score_hedonic_crowd(dict(record["ingredients_ul"]), dict(record["dilutions"]))
    if hed.coverage_status in {"NO_ACTIVE_MATERIALS", "ZERO_TABLE_COVERAGE"}:
        liking = {"valence": None, "score": None,
                  "reason": f"crowd table cannot score this formula ({hed.coverage_status})"}
    else:
        liking = {"valence": hed.weighted_valence, "score": hed.score,
                  "coverage": hed.coverage_status,
                  "rated_active_fraction": _r(hed.rated_active_fraction)}

    # Diagnostics (never scored).
    top_oav = {}
    for fr in frames:
        ranked = sorted(
            ((m.name, float(m.screening_oav)) for m in fr.state.materials
             if m.name in name_set and m.screening_oav is not None),
            key=lambda kv: (-kv[1], kv[0]),
        )[:3]
        top_oav[fr.label] = [{"material": n, "screening_oav": _r(v, 3)} for n, v in ranked]

    disqualified = any(f["status"] == "FAIL" for f in floors.values())
    return {
        "formula": str(formula.get("name") or record.get("name") or ""),
        "brief": str(brief.get("id") or ""),
        "floors": floors,
        "disqualified": disqualified,
        "holds": holds,
        "name_score": _r(name_score, 2),
        "name_parts": {
            "parts": {k: (None if v is None else _r(v)) for k, v in name_parts.items()},
            "weights": NAME_WEIGHTS,
            "named_notes": notes,
            "excluded_notes": exclusions,
            "family_core_groups": groups,
            "skeleton_gates": skeletons,
        },
        "craft_score": _r(craft_score, 2),
        "craft_parts": {
            "parts": {k: (None if v is None else _r(v)) for k, v in craft_parts.items()},
            "weights": CRAFT_WEIGHTS,
            "support": support,
            "largest_material": {"material": top_name, "share_pct": _r(top_pct, 2),
                                 "limit_pct": SINGLE_MATERIAL_LIMIT_PCT, "basis": basis},
            "material_count": count,
            "material_count_band": [MATERIAL_COUNT_MIN, MATERIAL_COUNT_MAX],
            "precious_cap_breaches": cap_breaches,
            "musks": musks,
            "musk_limit": musk_limit,
            "musk_penalty": MUSK_OVER_LIMIT_PENALTY if musk_over else 0.0,
        },
        "liking": liking,
        "rows": [
            {"material": str(r["material"]), "amount": str(r["amount"]),
             "unit": str(r.get("unit", "uL")), "active_fraction": str(r.get("active_fraction", "1")),
             **({"tier": str(r["tier"])} if r.get("tier") else {})}
            for r in formula["rows"]
        ],
        "diagnostics": {
            "top_screening_oav_by_window": top_oav,
            "material_count": count,
            "concentrate_pct": floors["F4_bottle"]["concentrate_pct"],
            "active_ul": {n: _r(v, 3) for n, v in active_ul.items()},
        },
    }


# ── Closeness and duel ──────────────────────────────────────────────────────


def _tier(row: Mapping[str, Any]) -> str | None:
    for key in ("tier", "role"):
        value = str(row.get(key) or "").strip().lower()
        if value in {"top", "heart", "base"}:
            return value
    return None


def _jaccard(a: set[str], b: set[str]) -> float | None:
    union = a | b
    return _r(len(a & b) / len(union)) if union else None


def closeness(engine_formula: Mapping[str, Any], reference_formula: Mapping[str, Any]) -> dict:
    """Shown, never scored: material overlap and whether the engine has the reference's top 5."""
    def ids(f: Mapping[str, Any], tier: str | None = None) -> set[str]:
        return {
            normalize_name(str(r["material"]))
            for r in f["rows"]
            if tier is None or _tier(r) == tier
        }

    engine_ids = ids(engine_formula)
    active: dict[str, float] = {}
    for r in reference_formula["rows"]:
        a = float(Decimal(str(r["amount"]))) * float(Decimal(str(r.get("active_fraction") or "1")))
        active[str(r["material"])] = active.get(str(r["material"]), 0.0) + a
    top5 = sorted(active.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {
        "jaccard_all": _jaccard(engine_ids, ids(reference_formula)),
        "jaccard_by_tier": {
            t: _jaccard(ids(engine_formula, t), ids(reference_formula, t))
            for t in ("top", "heart", "base")
        },
        "reference_top5_by_active_amount": [
            {"material": n, "active_amount": _r(v, 3),
             "engine_has": normalize_name(n) in engine_ids}
            for n, v in top5
        ],
        "basis": "active amount = amount x active fraction (uL rows; mg rows as written)",
    }


def _side(card: Scorecard) -> dict[str, Any]:
    return {"formula": card["formula"], "disqualified": card["disqualified"],
            "name_score": card["name_score"], "craft_score": card["craft_score"],
            "liking_valence": card["liking"].get("valence")}


def duel_verdict(engine_card: Scorecard, reference_card: Scorecard | None) -> Verdict:
    """Engine vs reference on one brief; the first deciding step wins."""
    def out(verdict: str, step: str, detail: str) -> Verdict:
        return {"verdict": verdict, "deciding_step": step, "detail": detail,
                "engine": _side(engine_card),
                "reference": _side(reference_card) if reference_card else None}

    if reference_card is None:
        return out("NO_REFERENCE", "1_reference", "no reference formula for this brief")
    e_dq, r_dq = engine_card["disqualified"], reference_card["disqualified"]
    if e_dq and r_dq:
        return out("BOTH_DISQUALIFIED", "2_floors", "both sides fail a floor")
    if e_dq or r_dq:
        return out("REFERENCE_WINS" if e_dq else "ENGINE_WINS", "2_floors",
                   ("engine" if e_dq else "reference") + " fails a floor")
    for step, key, margin in (("3_name", "name_score", SCORE_MARGIN),
                              ("4_craft", "craft_score", SCORE_MARGIN)):
        diff = float(engine_card[key]) - float(reference_card[key])
        if abs(diff) >= margin:
            return out("ENGINE_WINS" if diff > 0 else "REFERENCE_WINS", step,
                       f"{key} differs by {diff:+.2f} (margin {margin:g})")
    ev, rv = engine_card["liking"].get("valence"), reference_card["liking"].get("valence")
    if ev is not None and rv is not None and abs(float(ev) - float(rv)) >= LIKING_MARGIN - _EPS:
        diff = float(ev) - float(rv)
        return out("ENGINE_WINS" if diff > 0 else "REFERENCE_WINS", "5_liking",
                   f"crowd valence differs by {diff:+.3f} (margin {LIKING_MARGIN:g})")
    return out("TIE", "6_tie", "no step separated the two formulas")


__all__ = [
    "FLOOR_IDS",
    "Scorecard",
    "Verdict",
    "closeness",
    "duel_verdict",
    "formula_from_composer",
    "formula_from_markdown",
    "score_formula",
]
