"""Yardstick: a code-only scorecard for one formula against a brief, and a duel verdict.

Library module only (no CLI; AGENTS.md RULE 2). Deterministic and read-only: it calls the
release gate's pure functions (stock contract, IFRA safety, musk count, family skeletons,
pre-mix guard) and never runs the gate itself, which writes files.

Rule 1: no score uses an OAV magnitude or OAV share. Named-note detection is binary
(a matching material with screening OAV >= 1 in the note's window, as the brief benchmark
does); swamping uses active-mass share; OAV numbers appear only under ``diagnostics``.
Rule 4: a HOLD is never counted as a pass; it is listed under ``holds``, and a side holding a
floor cannot win a duel against a clean side. A decomposed natural's screening OAV is a sum
of constituent OAVs and the frame exposes no per-constituent values, so such a row gives no
detection verdict (the note holds as ``unknown_physics``).

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
import math
import re
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

FLOOR_IDS = ("F1_owned_stock", "F2_ifra", "F3_pre_mix_guard", "F4_bottle", "F5_pours", "F6_musks")

Scorecard = dict[str, Any]
Verdict = dict[str, Any]


# ── Formula adapters ────────────────────────────────────────────────────────


def formula_from_markdown(
    path: str | Path,
    *,
    parent_path: str | Path | None = None,
    batch_volume_ml: float | None = None,
) -> dict[str, Any]:
    """Load a formula file with the release gate's own parser (first formula in the file).

    The batch is the file's own (the release gate's ``resolve_batch_volume``: title, then
    file name, then 30 mL) unless ``batch_volume_ml`` is given. A ``parent_path`` that is
    set but missing is recorded as ``parent_missing`` (F3 holds). Rows the parser could not
    read are kept as ``row_parse_blockers`` (F1 holds: a blocked row could hide anything).
    """
    from scripts.formula_release_gate import resolve_batch_volume
    from scripts.verify_formula_workflow import parse_formula_markdown

    records = parse_formula_markdown(Path(path))
    if not records:
        raise ValueError(f"no formula rows could be read in {path}")
    record = records[0]
    if batch_volume_ml is None:
        batch_volume_ml, _, _ = resolve_batch_volume(None, str(record.get("name", "")), path)
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
    missing_parent = {}
    if parent_path is not None:
        if Path(parent_path).is_file():
            parent = formula_from_markdown(parent_path)
        else:
            missing_parent = {"parent_missing": str(parent_path)}
    blockers = [
        " ".join(str(b.get("message") or b).split())
        for b in record.get("row_parse_blockers", []) or []
    ]
    return {
        "name": record["name"],
        "batch_volume_ml": float(batch_volume_ml),
        "rows": rows,
        "parent": parent,
        "gate_record": record,
        **missing_parent,
        **({"row_parse_blockers": blockers} if blockers else {}),
    }


def formula_from_composer(result: Mapping[str, Any], *, batch_volume_ml: float = BOTTLE_ML) -> dict:
    """Rows from ``design_formula``'s optimized (else initial) formula.

    ``liquid_concentrate_ul_decimal`` (default "6000") is the liquid stock-charge total for
    one 30 mL bottle (20 %), the same default as the release gate's DEFAULT_CONCENTRATE_UL.
    """
    formula = result.get("optimized_formula") or result.get("initial_formula") or {}
    withheld = None if formula.get("rows") else str(
        result.get("assistant_message") or "the composer returned no formula"
    )
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
        **({"withheld_reason": withheld} if withheld else {}),
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
            "fraction_basis": str(
                row.get("fraction_basis") or ("neat" if fraction == 1.0 else "unspecified")
            ),
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


def _lacks_physics(m: Any) -> bool:
    """No usable screening OAV for detection.

    A decomposed natural's screening OAV is the sum of its constituents' OAVs (Rule 4: never
    a whole-natural detection claim), and the frame exposes no per-constituent OAVs, so such
    a row has no detection basis here.
    """
    return (
        m.screening_oav is None
        or m.odt_air_ppm is None
        or "odt_air_ppm" in m.missing_fields
        or bool(getattr(m, "has_constituent_resolved_oav", False))
    )


def _note_status(mats: Sequence[Any], formula_names: set[str], subs: Sequence[str]) -> str:
    """Binary detection (screening OAV >= 1) as the brief benchmark's ``_note_eval``.

    Detectable when any matching row with physics reaches 1; otherwise a note with any
    matching row lacking physics is ``unknown_physics`` (a hold), not ``below_threshold``.
    """
    rows = [m for m in mats if m.name in formula_names and _matches(m.name, subs)]
    if not rows:
        return "absent"
    if any(not _lacks_physics(m) and m.screening_oav >= 1 for m in rows):
        return "detectable"
    if any(_lacks_physics(m) for m in rows):
        return "unknown_physics"
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


# Stock-contract reasons where the gate's stock list lacks the material or disagrees with
# the row (preflight _dilution_consistency_check). Formula defects (no, invalid or
# conflicting stock fraction) are not here: they are hard whatever inventory.txt says.
# Nor are carrier and basis mismatches: the stock lists record carrier and basis, so a
# row asking for another carrier or basis names a stock the user does not have.
_GATE_DISAGREEMENT_REASONS = frozenset({
    "stock_id_not_in_current_inventory", "not_in_inventory", "inventory_gap",
    "inventory_stock_unavailable", "inventory_stock_metadata_incomplete",
    "inventory_stock_non_executable", "stock_fraction_mismatch", "ambiguous_live_stock",
})

# The gate's own stock list says this stock is made at the bench from an owned stock.
_GATE_PREPARABLE_REASONS = frozenset({"preparation_required"})

# As engine/personal_inventory.py: a stock whose name or form says it is a solid.
_SOLID_MARKERS = ("crystal", "powder", "solid", "flakes")


@functools.lru_cache(maxsize=1)
def _inventory_txt_owned() -> dict[str, tuple[Any, ...]]:
    """inventory.txt's owned stocks (every strength) by normalised name.

    The list the composer designs from (engine/personal_inventory.py
    ``materialize_personal_inventory`` reads the same ``parse_inventory`` owned rows),
    minus the user's compounding holds: a held material is excluded, not merely unbound.
    """
    from engine.inventory_parser import (
        apply_user_compounding_holds,
        is_user_compounding_held,
        parse_inventory,
    )

    live = tuple(
        s for s in parse_inventory(unique=False, include_unavailable=False)
        if s.status.casefold() == "owned" and s.dilution > 0
    )
    index: dict[str, list[Any]] = {}
    for s in apply_user_compounding_holds(live)[0]:
        if is_user_compounding_held(s):
            continue
        for key in {_lookup_key(s.identity_name or s.name), _lookup_key(s.name)}:
            index.setdefault(key, []).append(s)
    return {k: tuple(v) for k, v in index.items()}


_STRENGTH_SUFFIX = re.compile(r"\s+\d+(?:\.\d+)?\s*%.*$")


def _lookup_key(name: str) -> str:
    """A stock-list key that ignores hyphen-versus-space spelling ("cis-3-Hexenyl" and
    "Cis-3 Hexenyl") and a strength written into the name ("Cocoa Absolute 10%": the
    row's own fraction carries the strength)."""
    return re.sub(r"[\s\-_]+", " ", normalize_name(_STRENGTH_SUFFIX.sub("", name))).strip()


def _inventory_txt_stocks(material: str) -> list[Any]:
    """inventory.txt's owned stocks of ``material`` (alias crosswalk applied)."""
    from engine.inventory_parser import load_current_inventory_alias_crosswalk

    keys = {_lookup_key(material)}
    alias = load_current_inventory_alias_crosswalk().resolve(material)
    if alias:
        keys.add(_lookup_key(alias.destination))
    index = _inventory_txt_owned()
    seen: dict[int, Any] = {}
    for key in keys:
        for s in index.get(key, ()):
            seen.setdefault(id(s), s)
    return list(seen.values())


def _known(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.casefold() in {"", "unspecified"} else text


def _basis_compatible(spec: Mapping[str, Any], stock: Any) -> bool:
    """The gate's rule: two known fraction bases must be equal."""
    row, owned = _known(spec.get("fraction_basis")), _known(stock.fraction_basis)
    return not (row and owned and row != owned)


def _carrier_compatible(spec: Mapping[str, Any], stock: Any) -> bool:
    """The gate's rule: two known carriers must be equal."""
    row, owned = normalize_name(_known(spec.get("carrier"))), normalize_name(_known(stock.carrier))
    return not (row and owned and row != owned)


def _is_solid(stock: Any) -> bool:
    probe = " ".join(
        str(getattr(stock, f, "") or "")
        for f in ("physical_form", "raw_name", "name", "identity_name")
    ).casefold()
    return any(marker in probe for marker in _SOLID_MARKERS)


def _owned_on_inventory_txt(
    material: str, fraction: float | None, spec: Mapping[str, Any] | None = None
) -> bool:
    """Whether inventory.txt owns ``material`` at ``fraction`` (the gate's tolerance) in a
    carrier and fraction basis compatible with the row's."""
    from engine.pipeline.preflight import _same_stock_fraction

    if fraction is None:
        return False
    spec = spec or {}
    return any(
        _same_stock_fraction(float(fraction), float(s.dilution))
        and _basis_compatible(spec, s)
        and _carrier_compatible(spec, s)
        for s in _inventory_txt_stocks(material)
    )


def _issue_holdable(
    check: Mapping[str, Any], issue: Mapping[str, Any], record: Mapping[str, Any]
) -> bool:
    """A stock issue holds when it only needs data, or when the gate's list lacks or
    disagrees with a material inventory.txt owns at the row's active fraction. Decided
    from the material, never from where the row came from (composer or reference file)."""
    from engine.inventory_parser import USER_COMPOUNDING_HOLD
    from engine.pipeline.gates import _classify_preflight_check

    alone = {**check, "data": {**dict(check.get("data") or {}), "issues": [dict(issue)]}}
    if _classify_preflight_check(alone)[0] == "HOLD":
        return True  # the gate's own classifier: missing data only
    if issue.get("reason") not in _GATE_DISAGREEMENT_REASONS | _GATE_PREPARABLE_REASONS:
        return False
    if any(USER_COMPOUNDING_HOLD in str(h) for h in issue.get("execution_holds", []) or []):
        return False
    if issue.get("reason") in _GATE_PREPARABLE_REASONS:
        return True
    material = str(issue.get("material", ""))
    fraction = (record.get("dilutions") or {}).get(material)
    spec = dict((record.get("stock_specs") or {}).get(material) or {})
    return _owned_on_inventory_txt(material, fraction, spec) or _preparable_from_inventory_txt(
        material, fraction, spec
    )


def _preparable_from_inventory_txt(
    material: str, fraction: float | None, spec: Mapping[str, Any] | None = None
) -> bool:
    """Whether the row's stock is one bench dilution away from an owned stock: a hold, not
    a material the user lacks.

    The source must be stronger than ``fraction`` and either neat (diluted into the row's
    carrier, on the row's basis) or a dilution in the row's own carrier and basis
    (diluting a DPG stock with ethanol gives a mixed carrier, not the row's). A solid
    cannot be dissolved to any strength, so it counts only up to the strongest dilution of
    the material the user already owns.
    """
    if fraction is None or float(fraction) <= 0:
        return False
    spec = spec or {}
    target = float(fraction)
    stocks = _inventory_txt_stocks(material)
    row_carrier = normalize_name(_known(spec.get("carrier")))
    liquid_ceiling = max(
        (float(s.dilution) for s in stocks if float(s.dilution) < 1.0), default=0.0
    )
    for s in stocks:
        strength = float(s.dilution)
        if strength <= target + 1e-9:
            continue
        if strength < 1.0:  # a neat stock dilutes into any carrier, on any basis
            owned_carrier = normalize_name(_known(s.carrier))
            if (row_carrier and owned_carrier != row_carrier) or not _basis_compatible(spec, s):
                continue
        if _is_solid(s) and target > liquid_ceiling + 1e-9:
            continue
        return True
    return False


def _f1_stock(stock_contract: Any, record: Mapping[str, Any]) -> dict[str, Any]:
    """FAIL if any hard stock issue, else HOLD if any holdable one (Rule 0: a disagreement
    between inventory.txt and the gate's stock list is reported, not guessed)."""
    from engine.pipeline.gates import _classify_preflight_check

    check = stock_contract.as_dict()
    status, detail, _ = _classify_preflight_check(check)
    if status not in {"PASS", "FAIL", "HOLD"}:
        status = "PASS" if status == "WARN" else "HOLD"
    raw_issues = list(stock_contract.data.get("issues", []) or [])
    issues = [f"{i.get('material')}: {i.get('reason')}" for i in raw_issues]
    if status != "FAIL" or not raw_issues:
        return _floor(status, detail, issues=issues)
    hard, holdable = [], []
    for issue in raw_issues:
        (holdable if _issue_holdable(check, issue, record) else hard).append(issue)
    held_detail = (
        f"{len(holdable)} material(s) owned on inventory.txt that the gate's stock list lacks "
        "or disagrees with, that need a dilution prepared from a stronger owned stock, or "
        "that need data (complete them on the Stock page): "
        + ", ".join(str(i.get("material")) for i in holdable)
    ) if holdable else ""
    if hard:
        fails = ", ".join(f"{i.get('material')} ({i.get('reason')})" for i in hard)
        detail = f"{len(hard)} material(s) cannot be built as written: {fails}" + (
            f". {held_detail}" if held_detail else "")
        return _floor("FAIL", detail, issues=issues)
    return _floor("HOLD", held_detail, issues=issues)


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

    if formula.get("parent_missing"):
        return _floor("HOLD", f"parent formula is set but missing: {formula['parent_missing']}")
    parent = formula.get("parent")
    if not parent:
        return _floor("NOT_APPLICABLE", "new formula: no parent to compare against")
    prec = _gate_record(parent)
    # A revision's dose changes on the same stock are what the user asked for, so each is
    # authorised. A material whose stock strength changed is not: Rule 5 keeps
    # STOCK_REBASE_ACTIVE_EQUIVALENCE (and every other FAIL finding) a hard failure.
    parent_dil = {normalize_name(n): float(d) for n, d in prec["dilutions"].items()}
    same_stock = {
        n: "dose change in the revision as written"
        for n, d in record["dilutions"].items()
        if normalize_name(n) in parent_dil
        and math.isclose(parent_dil[normalize_name(n)], float(d), rel_tol=1e-9, abs_tol=1e-12)
    }
    try:
        report = evaluate_pre_mix_guard(
            child_ingredients_ul=record["ingredients_ul"],
            child_dilutions=record["dilutions"],
            parent_ingredients_ul=prec["ingredients_ul"],
            parent_dilutions=prec["dilutions"],
            authorized_active_dose_changes=same_stock,
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
    # mg rows count 1 mg ~ 1 uL, the assumption reference files make (they are exempt
    # only from the pour floor, F5).
    liquid = sum(float(Decimal(str(r["amount"]))) for r in formula["rows"])
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

    if not any(float(Decimal(str(r.get("amount") or "0"))) > 0 for r in formula.get("rows") or []):
        return _no_formula_card(formula, brief)
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
    f1 = _f1_stock(stock_contract, record)
    blocked = list(formula.get("row_parse_blockers") or [])
    if blocked and f1["status"] != "FAIL":
        # A row the parser could not read could hide Tonalide or a named-note material.
        f1 = _floor("HOLD", f"{len(blocked)} row(s) could not be read: " + "; ".join(blocked)
                    + (f". {f1['detail']}" if f1["status"] == "HOLD" else ""),
                    issues=f1.get("issues", []), blocked_rows=blocked)
    floors = {
        "F1_owned_stock": f1,
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
            if _matches(str(row["material"]), [sub]):  # mg rows count 1 mg ~ 1 uL
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


def _no_formula_card(formula: Mapping[str, Any], brief: Mapping[str, Any]) -> Scorecard:
    """A formula with no positive dose (e.g. the composer withheld): disqualified, scores 0."""
    detail = str(formula.get("withheld_reason") or "no formula rows with a positive amount")
    return {
        "formula": str(formula.get("name") or ""),
        "brief": str(brief.get("id") or ""),
        "floors": {fid: _floor("FAIL", detail) for fid in FLOOR_IDS},
        "disqualified": True,
        "holds": [],
        "name_score": 0.0,
        "name_parts": {},
        "craft_score": 0.0,
        "craft_parts": {},
        "liking": None,
        "rows": [],
        "diagnostics": {"no_formula": detail},
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
    holds = {"engine": _floor_holds(engine_card),
             "reference": _floor_holds(reference_card) if reference_card else []}

    def out(verdict: str, step: str, detail: str) -> Verdict:
        return {"verdict": verdict, "deciding_step": step, "detail": detail,
                "engine": _side(engine_card),
                "reference": _side(reference_card) if reference_card else None,
                "floor_holds": holds}

    if reference_card is None:
        return out("NO_REFERENCE", "1_reference", "no reference formula for this brief")
    e_dq, r_dq = engine_card["disqualified"], reference_card["disqualified"]
    if e_dq and r_dq:
        return out("BOTH_DISQUALIFIED", "2_floors", "both sides fail a floor")
    if e_dq or r_dq:
        verdict, step, detail = (
            "REFERENCE_WINS" if e_dq else "ENGINE_WINS", "2_floors",
            ("engine" if e_dq else "reference") + " fails a floor",
        )
    else:
        verdict, step, detail = _compare_scores(engine_card, reference_card)
    # Rule 4: a HOLD is never a pass, so a side holding any floor never wins: it is only
    # "ahead, held", whether it got ahead on scores or because the other side failed.
    held_text = "; ".join(
        f"{side} holds {', '.join(holds[side])}" for side in ("engine", "reference") if holds[side]
    )
    for side in ("ENGINE", "REFERENCE"):
        if verdict == f"{side}_WINS" and holds[side.lower()]:
            return out(f"{side}_AHEAD_HELD", step,
                       f"{detail}; {held_text}, so {side.lower()} cannot win")
    e_held, r_held = bool(holds["engine"]), bool(holds["reference"])
    if verdict == "TIE" and e_held != r_held:
        return out("REFERENCE_WINS" if e_held else "ENGINE_WINS", "2_floor_holds",
                   f"level on every step; {held_text}")
    return out(verdict, step, f"{detail}; {held_text}" if held_text else detail)


def _floor_holds(card: Scorecard) -> list[str]:
    return sorted(fid for fid, f in (card.get("floors") or {}).items() if f["status"] == "HOLD")


def _compare_scores(engine_card: Scorecard, reference_card: Scorecard) -> tuple[str, str, str]:
    """Name, then craft, then crowd liking; the first step past its margin decides."""
    for step, key, margin in (("3_name", "name_score", SCORE_MARGIN),
                              ("4_craft", "craft_score", SCORE_MARGIN)):
        diff = float(engine_card[key]) - float(reference_card[key])
        if abs(diff) >= margin:
            return ("ENGINE_WINS" if diff > 0 else "REFERENCE_WINS", step,
                    f"{key} differs by {diff:+.2f} (margin {margin:g})")
    ev, rv = engine_card["liking"].get("valence"), reference_card["liking"].get("valence")
    if ev is not None and rv is not None and abs(float(ev) - float(rv)) >= LIKING_MARGIN - _EPS:
        diff = float(ev) - float(rv)
        return ("ENGINE_WINS" if diff > 0 else "REFERENCE_WINS", "5_liking",
                f"crowd valence differs by {diff:+.3f} (margin {LIKING_MARGIN:g})")
    return ("TIE", "6_tie", "no step separated the two formulas")


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
