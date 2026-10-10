"""Post-compose detection pass: can each role be detected in its intended window?

After the composer allocates doses, every liquid row is run through the
temporal screening simulator (``engine.pipeline.simulator``). A role counts
as ``detectable`` when its screening odour-activity value reaches 1 in any of
its intended windows. A role below 1 is raised stepwise, re-simulated and
re-checked, staying inside every limit the composer already applies:

* the composer's own design cap (``composition_planner._design_cap_ul``: the
  role's raw-share cap, an identity hard cap, and the normal-use ceiling);
* the semantic layers' combined share budget (``_LAYER_SHARE_BUDGET``);
* the gate's composition checks (IFRA Cat 4, Hedione share, musk count): a
  raise that creates a FAIL the formula did not already have is rejected.

The added microlitres come from the volume/diffusion row(s) first, then
proportionally from other detectable non-character rows, so the liquid total
is unchanged. No row is dropped or swapped, user-fixed quantities and
must-preserve/explicit anchors are never changed, and weighed solids (mg) are
not simulated.

AGENTS.md Rule 1: odour activity is used here only as a detection floor
(screening OAV >= 1). It is never maximised, balanced or used to rank
materials, and a missing threshold is reported as ``no_threshold_data``,
never as silent.
"""

from __future__ import annotations

import re
from decimal import ROUND_FLOOR, Decimal
from typing import Any, Mapping, Sequence

WINDOWS = ("opening", "top", "heart", "late_heart", "drydown")
NOTE_WINDOWS = {
    "top": ("opening", "top"),
    "heart": ("heart", "late_heart"),
    "base": ("late_heart", "drydown"),
}
DETECTION_FLOOR = 1.0
DOMINATE_RATIO = 10.0
STEP_FACTOR = 2
MAX_ROUNDS = 5
# A donor row keeps at least this share of its composed dose.
DONOR_FLOOR = Decimal("0.5")
SCHEMA_VERSION = "detection-check-v1"
NOTE = (
    "Odour activity is a detection screen only: a role counts as detectable when "
    "its screening odour-activity value reaches 1 in a window it is meant for. "
    "It is not loudness, contribution to the scent, or liking."
)
_LAYER_PROVENANCES = {
    "LAYERED_BASE_ARCHITECTURE", "LAYERED_TOP_ARCHITECTURE",
    "LAYERED_HEART_ARCHITECTURE", "ACCENT_LAYER",
}


def intended_windows(row: Mapping[str, Any]) -> tuple[str, ...]:
    """Windows a role is meant to be detected in.

    * top-note rows (character, layer, accent) -> opening/top;
    * heart-note rows -> heart/late_heart;
    * base-note character/lead rows -> late_heart/drydown;
    * other base rows (structure, base layers, base accents) -> drydown;
    * bridges -> their note's windows plus the adjacent window on each side.
    """

    note = str(row.get("note") or "heart")
    role = str(row.get("role") or "")
    windows = NOTE_WINDOWS.get(note, NOTE_WINDOWS["heart"])
    if role == "bridge":
        first = WINDOWS.index(windows[0])
        last = WINDOWS.index(windows[-1])
        return WINDOWS[max(0, first - 1): min(len(WINDOWS), last + 2)]
    if note == "base" and role != "character":
        return ("drydown",)
    return windows


def _uL(row: Mapping[str, Any]) -> Decimal | None:
    if row.get("amount_unit") != "uL":
        return None
    try:
        value = Decimal(str(row.get("amount_decimal")))
    except ArithmeticError:
        return None
    return value if value.is_finite() else None


def _fraction(row: Mapping[str, Any]) -> float:
    try:
        return float(Decimal(str(row.get("stock_fraction_decimal"))))
    except ArithmeticError:
        return 1.0


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _simulate(rows: Sequence[Mapping[str, Any]], amounts: Mapping[int, Decimal]) -> dict[str, dict[str, float | None]]:
    """Return {identity_name: {window: screening_oav or None}}."""

    from engine.pipeline.simulator import simulate_formula

    ingredients: dict[str, float] = {}
    dilutions: dict[str, float] = {}
    for index, amount in amounts.items():
        name = str(rows[index].get("identity_name") or rows[index].get("material") or "")
        fraction = _fraction(rows[index])
        volume = float(amount)
        if name in dilutions and dilutions[name] and dilutions[name] != fraction:
            # Same material at a second strength: equivalent volume of the first.
            volume = volume * fraction / dilutions[name]
            fraction = dilutions[name]
        ingredients[name] = ingredients.get(name, 0.0) + volume
        dilutions[name] = fraction
    frames = simulate_formula(ingredients, dilutions)
    oavs: dict[str, dict[str, float | None]] = {name: {} for name in ingredients}
    for frame in frames:
        for material in frame.state.materials:
            if material.name in oavs:
                value = material.screening_oav
                oavs[material.name][frame.label] = None if value is None else float(value)
    return oavs


def _role_records(role_plan: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole

    roles: dict[str, Any] = {}
    for item in role_plan or ():
        try:
            role = SemanticRole(**{
                **item,
                "query_terms": tuple(item["query_terms"]),
                "character_weights": tuple(tuple(w) for w in item["character_weights"]),
            })
        except (TypeError, KeyError):
            continue
        roles[role.role_id] = role
    return roles


def _row_cap(
    row: Mapping[str, Any], role: Any, index: Any, liquid_total_ul: int,
) -> tuple[Decimal | None, str]:
    """The composer's own design cap for this row, and which limit binds."""

    if role is None or index is None:
        return None, "no composer role record for this row"
    capability = next(
        (c for c in index.capabilities if c.stock_id == row.get("stock_id")), None,
    )
    if capability is None:
        return None, "stock not in the capability index"
    from engine.formulation_intelligence.formula_solver import _role_spec
    from engine.research.composition_planner import (
        Choice,
        _hard_cap_ul,
        _normal_use_ceiling_cap_ul,
        _role_cap_ul,
    )

    choice = Choice(_role_spec(role), capability.candidate, 0.0, ())
    hard = _hard_cap_ul(choice.candidate, liquid_total_ul)
    ceiling = _normal_use_ceiling_cap_ul(choice.candidate, liquid_total_ul)
    if hard is not None:
        cap, limit = hard, "identity hard cap"
    else:
        share = role.max_raw_share
        cap = _role_cap_ul(choice, liquid_total_ul)
        limit = (
            f"role cap ({float(share) * 100:g}% of the formula)" if share is not None
            else "role cap"
        )
    if ceiling is not None and ceiling < cap:
        cap, limit = ceiling, "normal-use ceiling"
    from engine.formulation_intelligence.formula_solver import (
        _BRIDGE_MAX_RAW_SHARE,
        _BRIDGE_PROVENANCE,
    )

    bridge_cap = int(liquid_total_ul * _BRIDGE_MAX_RAW_SHARE)
    if role.provenance in _BRIDGE_PROVENANCE and bridge_cap < cap:
        # The composer never lets a generic bridge carry the formula.
        cap, limit = bridge_cap, f"bridge cap ({_BRIDGE_MAX_RAW_SHARE * 100:g}% of the formula)"
    return Decimal(cap), limit


def _blocking_checks(formula: Mapping[str, Any], name: str) -> set[str]:
    from engine.formulation_intelligence.composition_checks import composition_checks

    result = composition_checks(formula, formula_name=name)
    return {
        f"{check.get('check')}: {check.get('message')}"
        for check in result.get("checks", []) if check.get("status") == "FAIL"
    }


def _limit_label(check: str) -> str:
    kind = check.split(":", 1)[0]
    return {"ifra": "IFRA Cat 4", "hedione_share": "Hedione share", "musk_count": "musk count"}.get(
        kind, kind,
    )


def apply_detection_pass(
    formula: Mapping[str, Any],
    *,
    role_plan: Sequence[Mapping[str, Any]] | None,
    interpretation: Mapping[str, Any] | None,
    formula_name: str,
    index: Any = None,
) -> dict[str, Any]:
    """Return a copy of ``formula`` with raised doses and a ``detection_check`` block."""

    rows = [dict(row) for row in formula.get("rows", [])]
    interpretation = interpretation or {}
    roles = _role_records(role_plan)
    original = {i: amount for i, row in enumerate(rows) if (amount := _uL(row)) is not None}
    liquid_total = sum(original.values(), Decimal(0))
    total_int = int(liquid_total)
    explicit = [_key(str(m)) for m in interpretation.get("explicit_materials", ()) or ()]
    preserved = [_key(str(m)) for m in interpretation.get("must_preserve", ()) or ()]
    fixed_names = [
        _key(str(q.get("material") or q.get("identity_name") or ""))
        for q in interpretation.get("explicit_quantities", ()) or () if isinstance(q, Mapping)
    ]

    def named(row: Mapping[str, Any], names: Sequence[str]) -> bool:
        probe = f" {_key(str(row.get('identity_name') or row.get('material') or ''))} "
        return any(n and f" {n} " in probe for n in names)

    def anchored(i: int) -> bool:
        row = rows[i]
        role = roles.get(str(row.get("slot")))
        return (
            str(row.get("slot", "")).startswith("explicit_anchor")
            or bool(getattr(role, "exact_material", None))
            or named(row, preserved) or named(row, fixed_names)
        )

    def is_layer(i: int) -> bool:
        role = roles.get(str(rows[i].get("slot")))
        return getattr(role, "provenance", None) in _LAYER_PROVENANCES

    caps: dict[int, tuple[Decimal | None, str]] = {}
    # A list holder lets several formulas share one lazily built index.
    index_ref = index if isinstance(index, list) else [index]

    def cap_for(i: int) -> tuple[Decimal | None, str]:
        if i not in caps:
            if index_ref[0] is None and roles:
                from engine.formulation_intelligence.material_capability_index import (
                    build_material_capability_index,
                )

                index_ref[0] = build_material_capability_index().with_explicit_materials(
                    tuple(interpretation.get("explicit_materials", ()) or ()),
                )
            caps[i] = _row_cap(rows[i], roles.get(str(rows[i].get("slot"))), index_ref[0], total_int)
        return caps[i]

    def windows_of(i: int) -> tuple[str, ...]:
        return intended_windows(rows[i])

    def best(oavs: Mapping[str, Mapping[str, float | None]], i: int) -> tuple[bool, float | None]:
        values = oavs.get(str(rows[i].get("identity_name") or rows[i].get("material") or ""), {})
        intended = [values.get(w) for w in windows_of(i)]
        if not intended or all(v is None for v in intended):
            return False, None
        return True, max(v for v in intended if v is not None)

    def as_formula(current: Mapping[int, Decimal]) -> dict[str, Any]:
        out = [dict(row) for row in rows]
        for i, amount in current.items():
            if amount != original[i]:
                out[i]["amount_decimal"] = _plain(amount)
        return {**formula, "rows": out}

    baseline_fail = _blocking_checks(formula, formula_name) if original else set()

    def run_raises(
        frozen: Mapping[int, str],
    ) -> tuple[dict[int, Decimal], dict[str, dict[str, float | None]], dict[int, str]]:
        amounts = dict(original)
        limit_hit: dict[int, str] = dict(frozen)
        oavs = _simulate(rows, amounts) if amounts else {}
        for _ in range(MAX_ROUNDS):
            wants: dict[int, Decimal] = {}
            for i in amounts:
                has_threshold, value = best(oavs, i)
                if not has_threshold or (value is not None and value >= DETECTION_FLOOR):
                    continue
                if i in limit_hit or anchored(i):
                    limit_hit.setdefault(i, "user-fixed or must-preserve dose")
                    continue
                cap, label = cap_for(i)
                if cap is None or amounts[i] >= cap:
                    limit_hit[i] = label
                    continue
                target = min(cap, amounts[i] * STEP_FACTOR).to_integral_value(rounding=ROUND_FLOOR)
                if target > amounts[i]:
                    wants[i] = target
                else:
                    limit_hit[i] = label
            if not wants:
                break
            # Layer budget: semantic layers together stay within their share.
            from engine.formulation_intelligence.semantic_brief_adapter import _LAYER_SHARE_BUDGET

            layer_room = Decimal(str(_LAYER_SHARE_BUDGET)) * liquid_total - sum(
                (amounts[i] for i in amounts if is_layer(i)), Decimal(0),
            )
            for i in sorted(wants):
                if is_layer(i):
                    extra = min(wants[i] - amounts[i], max(Decimal(0), layer_room))
                    layer_room -= extra
                    if extra <= 0:
                        limit_hit[i] = "layer share budget"
                        del wants[i]
                    else:
                        wants[i] = amounts[i] + extra
            # Donors: volume/diffusion rows first, then other detectable non-character rows.
            donors = [
                i for i in amounts if i not in wants and not anchored(i)
                and str(rows[i].get("role")) != "character" and best(oavs, i)[1] is not None
                and (best(oavs, i)[1] or 0) >= DETECTION_FLOOR
            ]
            volume = [i for i in donors if str(rows[i].get("role")) == "volume"]
            others = [i for i in donors if i not in volume]
            room = {i: amounts[i] - (original[i] * DONOR_FLOOR).to_integral_value() for i in donors}
            needed = sum((wants[i] - amounts[i] for i in wants), Decimal(0))
            available = sum((max(Decimal(0), room[i]) for i in donors), Decimal(0))
            if available < needed:
                # Scale the raises down to what the donors can give.
                scale = available / needed if needed else Decimal(0)
                for i in sorted(wants):
                    extra = ((wants[i] - amounts[i]) * scale).to_integral_value(rounding=ROUND_FLOOR)
                    if extra <= 0:
                        limit_hit[i] = "volume available from other rows"
                        del wants[i]
                    else:
                        wants[i] = amounts[i] + extra
                needed = sum((wants[i] - amounts[i] for i in wants), Decimal(0))
            if not wants:
                break
            trial = dict(amounts)
            trial.update(wants)
            remaining = needed
            for group in (volume, others):
                pool = sum((max(Decimal(0), room[i]) for i in group), Decimal(0))
                if remaining <= 0 or pool <= 0:
                    continue
                take = min(remaining, pool)
                shares = {
                    i: (take * max(Decimal(0), room[i]) / pool).to_integral_value(rounding=ROUND_FLOOR)
                    for i in group
                }
                short = take - sum(shares.values(), Decimal(0))
                for i in sorted(group, key=lambda j: -room[j]):
                    if short <= 0:
                        break
                    if shares[i] < room[i]:
                        shares[i] += 1
                        short -= 1
                for i, value in shares.items():
                    trial[i] -= value
                remaining -= take
            new_fail = _blocking_checks(as_formula(trial), formula_name) - baseline_fail
            if new_fail:
                blamed = [
                    i for i in wants
                    if any(_key(str(rows[i].get("identity_name") or "")) in _key(check) for check in new_fail)
                ] or list(wants)
                label = _limit_label(sorted(new_fail)[0])
                for i in blamed:
                    limit_hit[i] = label
                continue
            amounts = trial
            oavs = _simulate(rows, amounts)
        return amounts, oavs, limit_hit

    # A raise that still leaves the row below detection only takes volume from
    # other rows, so such rows keep their composed dose and the pass reruns.
    frozen: dict[int, str] = {}
    tried: dict[int, Decimal] = {}
    while True:
        amounts, oavs, limit_hit = run_raises(frozen)
        wasted = [
            i for i in amounts
            if amounts[i] > original[i] and (best(oavs, i)[1] or 0) < DETECTION_FLOOR
        ]
        if not wasted:
            break
        for i in wasted:
            tried[i] = max(tried.get(i, amounts[i]), amounts[i])
            frozen[i] = limit_hit.get(i) or cap_for(i)[1]

    lead = _lead_index(rows, roles)
    adjusted = as_formula(amounts)
    statuses: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        entry: dict[str, Any] = {
            "row_id": row.get("row_id"),
            "slot": row.get("slot"),
            "material": row.get("identity_name") or row.get("material"),
            "role": row.get("role"),
            "intended_windows": list(windows_of(i)),
        }
        if i not in amounts:
            entry.update({"status": "not_checked", "reason": "weighed solid (mg) is not simulated"})
            statuses.append(entry)
            continue
        has_threshold, value = best(oavs, i)
        entry.update({
            "dose_before_ul": _plain(original[i]),
            "dose_after_ul": adjusted["rows"][i]["amount_decimal"],
            "max_screening_oav_in_intended_windows": None if value is None else round(value, 3),
        })
        if not has_threshold:
            entry["status"] = "no_threshold_data"
        elif value is not None and value >= DETECTION_FLOOR:
            entry["status"] = "raised" if amounts[i] > original[i] else "detectable"
        else:
            entry["status"] = "silent_at_cap"
            entry["binding_limit"] = limit_hit.get(i) or cap_for(i)[1]
            if i in tried:
                entry["highest_dose_tried_ul"] = _plain(tried[i])
        statuses.append(entry)
    flags = _dominate_flags(rows, amounts, oavs, lead, explicit)
    adjustments = [
        {"row_id": rows[i].get("row_id"), "row_index": i,
         "amount_before_decimal": rows[i]["amount_decimal"],
         "amount_after_decimal": adjusted["rows"][i]["amount_decimal"]}
        for i in sorted(amounts) if amounts[i] != original[i]
    ]
    adjusted["detection_check"] = {
        "schema_version": SCHEMA_VERSION,
        "detection_floor_screening_oav": DETECTION_FLOOR,
        "lead_slot": rows[lead].get("slot") if lead is not None else None,
        "roles": statuses,
        "flags": flags,
        "adjustments": adjustments,
        "liquid_total_ul_before": _plain(liquid_total),
        "liquid_total_ul_after": _plain(sum(amounts.values(), Decimal(0))),
        "note": NOTE,
    }
    return adjusted


def _lead_index(rows: Sequence[Mapping[str, Any]], roles: Mapping[str, Any]) -> int | None:
    for i, row in enumerate(rows):
        if str(row.get("slot", "")).startswith("explicit_anchor") and _uL(row) is not None:
            return i
    for i, row in enumerate(rows):
        if row.get("role") == "character" and "__accord" not in str(row.get("slot", "")) and _uL(row) is not None:
            return i
    return None


def _dominate_flags(
    rows: Sequence[Mapping[str, Any]],
    amounts: Mapping[int, Decimal],
    oavs: Mapping[str, Mapping[str, float | None]],
    lead: int | None,
    explicit: Sequence[str],
) -> list[dict[str, Any]]:
    """Unnamed materials at >= 10x the lead's screening OAV: smell-check only."""

    if lead is None:
        return []
    lead_name = str(rows[lead].get("identity_name") or "")
    lead_values = oavs.get(lead_name, {})
    flags: list[dict[str, Any]] = []
    for i in sorted(amounts):
        row = rows[i]
        name = str(row.get("identity_name") or "")
        probe = f" {_key(name)} "
        slot = str(row.get("slot", ""))
        # Rows filling a note the brief asked for (its facets and their accords)
        # are requested, so only unrequested rows are flagged.
        if (i == lead or name == lead_name or slot.startswith(("explicit_anchor", "facet_"))
                or any(n and f" {n} " in probe for n in explicit)):
            continue
        # Compared only in the lead's own windows where the lead is detectable.
        windows = [
            w for w in intended_windows(rows[lead])
            if (lead_values.get(w) or 0) >= DETECTION_FLOOR and (oavs.get(name, {}).get(w) or 0)
            >= DOMINATE_RATIO * float(lead_values[w] or 0)
        ]
        if windows:
            flags.append({
                "flag": "may_dominate_smell_check",
                "slot": row.get("slot"),
                "material": name,
                "lead_material": lead_name,
                "windows": windows,
                "message": (
                    f"{name} screens at 10x or more the lead ({lead_name}) in "
                    f"{', '.join(windows)}: smell-check that it does not take over. "
                    "Flag only; no dose was changed."
                ),
            })
    return flags


def solver_formula(formula: Mapping[str, Any]) -> dict[str, Any]:
    """The formula as the solver allocated it, before the detection pass.

    Raises ``ValueError`` when the recorded adjustments do not match the rows,
    or when they changed the liquid total.
    """

    check = formula.get("detection_check")
    rows = [dict(row) for row in formula.get("rows", [])]
    if not check:
        return {**formula, "rows": rows}
    for adjustment in check.get("adjustments", []):
        i = adjustment["row_index"]
        if (rows[i].get("row_id") != adjustment["row_id"]
                or rows[i].get("amount_decimal") != adjustment["amount_after_decimal"]):
            raise ValueError("detection adjustment does not match its row")
        rows[i]["amount_decimal"] = adjustment["amount_before_decimal"]
    before = sum((v for row in rows if (v := _uL(row)) is not None), Decimal(0))
    after = sum((v for row in formula.get("rows", []) if (v := _uL(row)) is not None), Decimal(0))
    if before != after:
        raise ValueError("detection adjustment changed the liquid total")
    restored = {key: value for key, value in formula.items() if key != "detection_check"}
    return {**restored, "rows": rows}


def attach_detection_checks(report: dict[str, Any]) -> dict[str, Any]:
    """Run the pass on the main formula and every design variant."""

    interpretation = report.get("request_interpretation") or {}
    name = str(report.get("formula_name") or "Composed formula")
    variants = list(report.get("design_variants") or [])
    plans: dict[int, Any] = {}
    for variant in variants:
        formula = variant.get("formula") if isinstance(variant, Mapping) else None
        if isinstance(formula, Mapping):
            plans.setdefault(id(formula), variant.get("role_plan"))
    done: dict[int, dict[str, Any]] = {}
    shared_index: list[Any] = [None]

    def run(formula: Mapping[str, Any]) -> dict[str, Any]:
        key = id(formula)
        if key not in done:
            done[key] = apply_detection_pass(
                formula, role_plan=plans.get(key), interpretation=interpretation,
                formula_name=name, index=shared_index,
            )
        return done[key]

    enhanced = dict(report)
    for field in ("optimized_formula", "initial_formula"):
        formula = enhanced.get(field)
        if isinstance(formula, Mapping) and formula.get("rows"):
            enhanced[field] = run(formula)
    if "design_variants" in enhanced:
        enhanced["design_variants"] = [
            {**v, "formula": run(v["formula"])}
            if isinstance(v, Mapping) and isinstance(v.get("formula"), Mapping) and v["formula"].get("rows")
            else v
            for v in variants
        ]
    return enhanced


__all__ = [
    "NOTE",
    "apply_detection_pass",
    "attach_detection_checks",
    "intended_windows",
    "solver_formula",
]
