"""Sourced IFRA Category 4 table: load, validate, look up and evaluate.

The table lives in a JSON data file (``data/regulatory/ifra_cat4_51.json``).
Every Category 4 limit belongs to an IFRA Standard record that carries the
verbatim quote it was read from; a material only points at its standard and
never carries a number of its own. Limits are % w/w of the finished product.

This module is a library: it reads the table and evaluates finished-product
percentages against it. It makes no pipeline-gate decisions of its own.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

SCHEMA_VERSION = "ifra_cat4_table/1"
DEFAULT_TABLE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "regulatory" / "ifra_cat4_51.json"
)

STANDARD_KINDS = frozenset({
    "restriction",
    "prohibition",
    "specification",
    "restriction_specification",
    "prohibition_specification",
    "restriction_prohibition",
    "prohibition_restriction_specification",
})
MATERIAL_STATUSES = frozenset({
    "restricted",
    "prohibited",
    "specification",
    "restricted_unverified",
    "no_standard",
    "natural_no_own_standard",
})
GROUP_RULES = frozenset({"sum_le_limit", "sum_of_ratios_le_1"})

_TOLERANCE = 1e-12
_PERCENT_NUMBER = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


@dataclass(frozen=True)
class IFRAStandard:
    id: str
    name: str
    cas: tuple[str, ...]
    kind: str
    amendment: str | None
    cat4_limit_pct: float | None
    cat4_quote: str | None
    url: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class IFRAMaterial:
    name: str
    status: str
    standard: str | None
    aliases: tuple[str, ...]
    cat4_limit_pct: float | None
    authority: str | None
    note: str | None
    source_url: str | None = None


@dataclass(frozen=True)
class IFRAGroupRule:
    id: str
    standard: str
    rule: str
    limit_pct: float | None
    members: tuple[str, ...]
    quote: str | None


@dataclass(frozen=True)
class IFRATable:
    schema_version: str
    amendment_in_force: int | None
    category: str
    basis: str
    library_url: str | None
    verified_on: str | None
    standards: Mapping[str, IFRAStandard]
    materials: Mapping[str, IFRAMaterial]
    group_rules: tuple[IFRAGroupRule, ...]
    _index: Mapping[str, IFRAMaterial] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        index: dict[str, IFRAMaterial] = {}
        for material in self.materials.values():
            for name in (material.name, *material.aliases):
                index[_normalise(name)] = material
        object.__setattr__(self, "_index", index)

    def lookup(self, *names: str | None) -> IFRAMaterial | None:
        """Return the first material matching any name, case/whitespace-insensitive."""
        for name in names:
            if name and name.strip():
                material = self._index.get(_normalise(name))
                if material is not None:
                    return material
        return None

    def cat4_limits(self) -> dict[str, float]:
        """Restricted materials only, keyed by canonical name and every alias as written."""
        limits: dict[str, float] = {}
        for material in self.materials.values():
            if material.status == "restricted" and material.cat4_limit_pct is not None:
                for name in (material.name, *material.aliases):
                    limits[name] = material.cat4_limit_pct
        return limits

    def prohibited_names(self) -> frozenset[str]:
        return self._names_with_status("prohibited")

    def specification_names(self) -> frozenset[str]:
        return self._names_with_status("specification")

    def _names_with_status(self, status: str) -> frozenset[str]:
        return frozenset(
            name
            for material in self.materials.values()
            if material.status == status
            for name in (material.name, *material.aliases)
        )


@dataclass(frozen=True)
class IFRACheck:
    material: str
    matched_name: str | None
    status: str | None
    standard: str | None
    pct: float
    limit_pct: float | None
    ratio: float | None
    verdict: str
    message: str


@dataclass(frozen=True)
class IFRAGroupCheck:
    id: str
    standard: str
    rule: str
    member_pcts: Mapping[str, float]
    total: float
    limit_pct: float | None
    verdict: str
    message: str


@dataclass(frozen=True)
class IFRAEvaluation:
    checks: tuple[IFRACheck, ...]
    group_checks: tuple[IFRAGroupCheck, ...]

    @property
    def failures(self) -> tuple[IFRACheck | IFRAGroupCheck, ...]:
        return self._with_verdict("fail", include_groups=True)

    @property
    def warnings(self) -> tuple[IFRACheck | IFRAGroupCheck, ...]:
        return self._with_verdict("warn", include_groups=True)

    @property
    def holds(self) -> tuple[IFRACheck, ...]:
        return tuple(c for c in self.checks if c.verdict == "hold")

    @property
    def unchecked(self) -> tuple[IFRACheck, ...]:
        return tuple(c for c in self.checks if c.verdict == "unchecked")

    @property
    def notes(self) -> tuple[IFRACheck, ...]:
        return tuple(c for c in self.checks if c.verdict == "note")

    def _with_verdict(
        self, verdict: str, *, include_groups: bool
    ) -> tuple[IFRACheck | IFRAGroupCheck, ...]:
        rows: list[IFRACheck | IFRAGroupCheck] = [c for c in self.checks if c.verdict == verdict]
        if include_groups:
            rows.extend(g for g in self.group_checks if g.verdict == verdict)
        return tuple(rows)


# --------------------------------------------------------------------------- loading


def load_ifra_table(path: str | Path | None = None) -> IFRATable:
    """Load and validate a table. The default path is cached; explicit paths are not."""
    if path is None:
        return _load_default_table()
    return _load_table(Path(path))


@lru_cache(maxsize=1)
def _load_default_table() -> IFRATable:
    return _load_table(DEFAULT_TABLE_PATH)


def _load_table(path: Path) -> IFRATable:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version {raw.get('schema_version')!r} is not {SCHEMA_VERSION!r}"
        )
    standards = {sid: _parse_standard(sid, rec) for sid, rec in raw.get("standards", {}).items()}
    materials = {
        name: _parse_material(name, rec, standards)
        for name, rec in raw.get("materials", {}).items()
    }
    _check_name_collisions(materials.values())
    group_rules = tuple(
        _parse_group_rule(rec, standards, materials) for rec in raw.get("group_rules", [])
    )
    return IFRATable(
        schema_version=raw["schema_version"],
        amendment_in_force=raw.get("amendment_in_force"),
        category=str(raw.get("category")),
        basis=str(raw.get("basis")),
        library_url=raw.get("library_url"),
        verified_on=raw.get("verified_on"),
        standards=standards,
        materials=materials,
        group_rules=group_rules,
    )


def _parse_standard(sid: str, rec: Mapping) -> IFRAStandard:
    kind = rec.get("kind")
    if kind not in STANDARD_KINDS:
        raise ValueError(f"standard {sid}: unknown kind {kind!r}")
    limit = rec.get("cat4_limit_pct")
    quote = rec.get("cat4_quote")
    if limit is not None:
        if not _is_number(limit):
            raise ValueError(f"standard {sid}: cat4_limit_pct {limit!r} is not a number")
        if not _quote_states_limit(quote, float(limit)):
            raise ValueError(
                f"standard {sid}: cat4_quote {quote!r} does not state the limit {limit} %"
            )
    return IFRAStandard(
        id=sid,
        name=rec.get("name", ""),
        cas=tuple(rec.get("cas", ())),
        kind=kind,
        amendment=rec.get("amendment"),
        cat4_limit_pct=None if limit is None else float(limit),
        cat4_quote=quote,
        url=rec.get("url"),
        notes=tuple(rec.get("notes", ())),
    )


def _parse_material(
    name: str, rec: Mapping, standards: Mapping[str, IFRAStandard]
) -> IFRAMaterial:
    status = rec.get("status")
    if status not in MATERIAL_STATUSES:
        raise ValueError(f"material {name!r}: unknown status {status!r}")
    if "cat4_limit_pct" in rec:
        raise ValueError(
            f"material {name!r}: carries its own cat4_limit_pct; limits come from its standard"
        )
    sid = rec.get("standard")
    if sid is not None and sid not in standards:
        raise ValueError(f"material {name!r}: references unknown standard {sid!r}")
    limit = None
    if status == "restricted":
        if sid is None or standards[sid].cat4_limit_pct is None:
            raise ValueError(
                f"material {name!r}: status 'restricted' needs a standard with a numeric "
                f"cat4_limit_pct (standard {sid!r})"
            )
        limit = standards[sid].cat4_limit_pct
    return IFRAMaterial(
        name=name,
        status=status,
        standard=sid,
        aliases=tuple(rec.get("aliases", ())),
        cat4_limit_pct=limit,
        authority=rec.get("authority", "IFRA") if status == "prohibited" else None,
        note=rec.get("note"),
        source_url=rec.get("source_url"),
    )


def _check_name_collisions(materials: Iterable[IFRAMaterial]) -> None:
    owner: dict[str, str] = {}
    for material in materials:
        for name in (material.name, *material.aliases):
            key = _normalise(name)
            other = owner.setdefault(key, material.name)
            if other != material.name:
                raise ValueError(
                    f"name {name!r} of material {material.name!r} collides with "
                    f"material {other!r}"
                )


def _parse_group_rule(
    rec: Mapping,
    standards: Mapping[str, IFRAStandard],
    materials: Mapping[str, IFRAMaterial],
) -> IFRAGroupRule:
    gid = rec.get("id")
    rule = rec.get("rule")
    if rule not in GROUP_RULES:
        raise ValueError(f"group rule {gid!r}: unknown rule {rule!r}")
    sid = rec.get("standard")
    if sid not in standards:
        raise ValueError(f"group rule {gid!r}: references unknown standard {sid!r}")
    members = tuple(rec.get("members", ()))
    for member in members:
        if member not in materials:
            raise ValueError(f"group rule {gid!r}: member {member!r} is not a material")
        if rule == "sum_of_ratios_le_1" and materials[member].status != "restricted":
            raise ValueError(
                f"group rule {gid!r}: sum_of_ratios_le_1 member {member!r} is not 'restricted'"
            )
    limit = rec.get("limit_pct")
    if rule == "sum_le_limit" and not _is_number(limit):
        raise ValueError(f"group rule {gid!r}: sum_le_limit needs a numeric limit_pct")
    if rule == "sum_of_ratios_le_1" and limit is not None:
        raise ValueError(f"group rule {gid!r}: sum_of_ratios_le_1 takes limit_pct null")
    return IFRAGroupRule(
        id=gid,
        standard=sid,
        rule=rule,
        limit_pct=None if limit is None else float(limit),
        members=members,
        quote=rec.get("quote"),
    )


def _normalise(name: str) -> str:
    return " ".join(name.split()).casefold()


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ".")).normalize()
    except InvalidOperation:
        return None


def _quote_states_limit(quote: object, limit: float) -> bool:
    """True when the quote contains the limit as a percentage ("0.10 %" states 0.1)."""
    if not isinstance(quote, str):
        return False
    wanted = Decimal(repr(limit)).normalize()
    return any(_decimal(m.group(1)) == wanted for m in _PERCENT_NUMBER.finditer(quote))


# --------------------------------------------------------------------------- evaluation


def evaluate_ifra(
    pct_by_material: Mapping[str, float],
    *,
    table: IFRATable | None = None,
    alt_names: Mapping[str, Sequence[str] | str] | None = None,
    edge_ratio: float = 0.7,
    headroom: float = 1.0,
) -> IFRAEvaluation:
    """Evaluate finished-product % w/w per formula row against the Category 4 table."""
    table = table if table is not None else load_ifra_table()
    alt_names = alt_names or {}
    checks: list[IFRACheck] = []
    pct_by_member: dict[str, float] = {}
    restricted_rows: dict[str, list[str]] = {}
    for row_name, pct in pct_by_material.items():
        extra = alt_names.get(row_name, ())
        candidates = [row_name, *([extra] if isinstance(extra, str) else extra)]
        matched_name, material = None, None
        for candidate in candidates:
            material = table.lookup(candidate)
            if material is not None:
                matched_name = candidate
                break
        pct = float(pct)
        if material is None:
            checks.append(IFRACheck(
                row_name, None, None, None, pct, None, None, "unchecked",
                f"{row_name} at {_fmt(pct)} % is not in the IFRA Category 4 table; unchecked.",
            ))
            continue
        pct_by_member[material.name] = pct_by_member.get(material.name, 0.0) + pct
        if material.status == "restricted" and material.standard is not None:
            restricted_rows.setdefault(material.standard, []).append(material.name)
        checks.append(_check_row(row_name, matched_name, material, pct, edge_ratio, headroom))
    rules = [*table.group_rules, *_standard_total_rules(table, restricted_rows)]
    group_checks = tuple(
        g
        for rule in rules
        if (g := _check_group(rule, table, pct_by_member, edge_ratio, headroom)) is not None
    )
    return IFRAEvaluation(checks=tuple(checks), group_checks=group_checks)


def _standard_total_rules(
    table: IFRATable, restricted_rows: Mapping[str, Sequence[str]]
) -> list[IFRAGroupRule]:
    """A standard's limit covers every row in its scope, so rows sharing one are totalled.

    Two rows of the same material (a neat and a diluted stock, say) or two materials under
    one standard each pass alone and can still exceed the limit together. Standards that an
    explicit ``sum_le_limit`` rule already totals are left to that rule.
    """
    totalled = {r.standard for r in table.group_rules if r.rule == "sum_le_limit"}
    rules = []
    for sid, names in restricted_rows.items():
        if len(names) < 2 or sid in totalled:
            continue
        limit = table.standards[sid].cat4_limit_pct
        assert limit is not None  # restricted materials need a numeric standard limit
        rules.append(IFRAGroupRule(
            id=f"{sid}_total",
            standard=sid,
            rule="sum_le_limit",
            limit_pct=limit,
            members=tuple(dict.fromkeys(names)),
            quote=None,
        ))
    return rules


def _check_row(
    row_name: str,
    matched_name: str | None,
    material: IFRAMaterial,
    pct: float,
    edge_ratio: float,
    headroom: float,
) -> IFRACheck:
    std = material.standard or "no standard"
    label = row_name if row_name == material.name else f"{row_name} ({material.name})"
    limit, ratio = None, None
    status = material.status
    if status == "restricted":
        limit = material.cat4_limit_pct
        assert limit is not None  # guaranteed by validation
        ratio = pct / limit
        allowed = limit * headroom
        if pct > allowed + _TOLERANCE:
            verdict = "fail"
            message = (
                f"{label} at {_fmt(pct)} % exceeds the IFRA Category 4 limit of "
                f"{_fmt(limit)} % ({std})"
                + (f" with headroom {headroom:g} ({_fmt(allowed)} %)." if headroom != 1 else ".")
            )
        elif ratio >= edge_ratio:
            verdict = "warn"
            message = (
                f"{label} at {_fmt(pct)} % is {ratio:.0%} of the IFRA Category 4 limit of "
                f"{_fmt(limit)} % ({std})."
            )
        else:
            verdict = "pass"
            message = (
                f"{label} at {_fmt(pct)} % is within the IFRA Category 4 limit of "
                f"{_fmt(limit)} % ({std})."
            )
    elif status == "prohibited":
        authority = material.authority or "IFRA"
        if pct > 0:
            verdict = "fail"
            message = f"{label} at {_fmt(pct)} % is prohibited by {authority} ({std})."
        else:
            verdict = "pass"
            message = f"{label} is prohibited by {authority} ({std}) and is present at 0 %."
    elif status == "specification":
        verdict = "note"
        message = (
            f"{label} at {_fmt(pct)} % is covered by specification standard {std}, which sets "
            f"no Category 4 % limit; check the material grade."
        )
    elif status == "restricted_unverified":
        verdict = "hold"
        message = (
            f"{label} at {_fmt(pct)} % is restricted by {std} but its Category 4 limit is not "
            f"recorded; hold until verified."
        )
    elif status == "no_standard":
        verdict = "pass"
        message = f"{label} at {_fmt(pct)} % has no IFRA standard of its own."
    else:  # natural_no_own_standard
        verdict = "warn"
        message = (
            f"{label} at {_fmt(pct)} % is a natural with no IFRA standard of its own; its "
            f"restricted constituents are not summed here."
        )
    return IFRACheck(
        material=row_name,
        matched_name=matched_name,
        status=status,
        standard=material.standard,
        pct=pct,
        limit_pct=limit,
        ratio=ratio,
        verdict=verdict,
        message=message,
    )


def _check_group(
    rule: IFRAGroupRule,
    table: IFRATable,
    pct_by_member: Mapping[str, float],
    edge_ratio: float,
    headroom: float,
) -> IFRAGroupCheck | None:
    member_pcts = {m: pct_by_member[m] for m in rule.members if m in pct_by_member}
    if not member_pcts:
        return None
    parts = ", ".join(f"{m} {_fmt(p)} %" for m, p in member_pcts.items())
    if rule.rule == "sum_le_limit":
        assert rule.limit_pct is not None  # guaranteed by validation
        total = sum(member_pcts.values())
        fraction = total / rule.limit_pct
        over = total > rule.limit_pct * headroom + _TOLERANCE
        subject, limit_text = f"total {_fmt(total)} %", f"group limit of {_fmt(rule.limit_pct)} %"
    else:
        total = sum(
            p / table.materials[m].cat4_limit_pct  # type: ignore[operator]
            for m, p in member_pcts.items()
        )
        fraction = total
        over = total > headroom + _TOLERANCE
        subject, limit_text = f"sum of limit ratios {total:.3g}", "allowed sum of 1"
    if over:
        verdict, lead = "fail", "exceeds"
    elif fraction >= edge_ratio:
        verdict, lead = "warn", f"is {fraction:.0%} of"
    else:
        verdict, lead = "pass", "is within"
    message = (
        f"Group {rule.id} ({rule.standard}): {parts}; {subject} {lead} the {limit_text}"
        + (f" (headroom {headroom:g})." if headroom != 1 else ".")
    )
    return IFRAGroupCheck(
        id=rule.id,
        standard=rule.standard,
        rule=rule.rule,
        member_pcts=member_pcts,
        total=total,
        limit_pct=rule.limit_pct,
        verdict=verdict,
        message=message,
    )


def _fmt(value: float) -> str:
    return f"{value:.4g}"


# --------------------------------------------------------------------------- finished product mass

ETHANOL_DENSITY_G_ML = 0.789
# Densities at about 20-25 °C of the carriers stocks are diluted in.
CARRIER_DENSITY_G_ML: Mapping[str, float] = {
    "ethanol": 0.789,
    "dipropylene glycol": 1.023,
    "dpg": 1.023,
    "diethyl phthalate": 1.12,
    "dep": 1.12,
    "triethyl citrate": 1.137,
    "tec": 1.137,
    "isopropyl myristate": 0.853,
    "ipm": 0.853,
    "benzyl benzoate": 1.118,
    "water": 0.997,
}
DEFAULT_DENSITY_G_ML = 1.0


@dataclass(frozen=True)
class FinishedProductRow:
    """One formula row: ``stock_ul`` of a stock holding ``active_fraction`` of the material."""

    name: str
    stock_ul: float
    active_fraction: float = 1.0
    active_g: float | None = None
    active_density_g_ml: float | None = None
    carrier: str | None = None


@dataclass(frozen=True)
class FinishedProductEstimate:
    pct_w_w: Mapping[str, float]
    finished_mass_g: float
    concentrate_ml: float
    ethanol_ml: float
    batch_volume_ml: float
    overfilled: bool
    assumptions: tuple[str, ...]


def estimate_finished_product_pct_w_w(
    rows: Iterable[FinishedProductRow], batch_volume_ml: float
) -> FinishedProductEstimate:
    """Estimate each row's active material as % w/w of the finished bottle.

    The bottle is the stocks plus ethanol topped up to ``batch_volume_ml``. The finished mass
    is every row's active mass, plus its carrier's mass, plus the ethanol. A row's active mass
    is ``active_g`` when known, otherwise its active volume times its density. The carrier
    share of a diluted stock is taken as a volume fraction. Missing densities fall back to
    1.0 g/mL and are listed in ``assumptions``. When the stocks alone exceed the bottle,
    ``overfilled`` is set and no ethanol is added.
    """
    if batch_volume_ml <= 0:
        raise ValueError(f"batch_volume_ml must be positive, got {batch_volume_ml}")
    assumptions: list[str] = []
    active_mass: dict[str, float] = {}
    carrier_mass_g = 0.0
    concentrate_ml = 0.0
    for row in rows:
        stock_ml = max(float(row.stock_ul), 0.0) / 1000.0
        fraction = min(max(float(row.active_fraction), 0.0), 1.0)
        concentrate_ml += stock_ml
        if row.active_g is not None:
            mass = float(row.active_g)
        else:
            density = row.active_density_g_ml
            if density is None:
                density = DEFAULT_DENSITY_G_ML
                assumptions.append(f"{row.name}: density unknown, {DEFAULT_DENSITY_G_ML} g/mL used")
            mass = stock_ml * fraction * density
        active_mass[row.name] = active_mass.get(row.name, 0.0) + mass
        carrier_ml = stock_ml * (1.0 - fraction)
        if carrier_ml > 0:
            carrier = (row.carrier or "").strip()
            carrier_density = CARRIER_DENSITY_G_ML.get(carrier.casefold())
            if carrier_density is None:
                carrier_density = DEFAULT_DENSITY_G_ML
                assumptions.append(
                    f"{row.name}: carrier {carrier or 'not recorded'} has no density here, "
                    f"{DEFAULT_DENSITY_G_ML} g/mL used"
                )
            carrier_mass_g += carrier_ml * carrier_density
    ethanol_ml = batch_volume_ml - concentrate_ml
    overfilled = ethanol_ml < 0
    ethanol_ml = max(ethanol_ml, 0.0)
    finished_mass_g = sum(active_mass.values()) + carrier_mass_g + ethanol_ml * ETHANOL_DENSITY_G_ML
    pct = {
        name: (100.0 * mass / finished_mass_g if finished_mass_g > 0 else 0.0)
        for name, mass in active_mass.items()
    }
    return FinishedProductEstimate(
        pct_w_w=pct,
        finished_mass_g=finished_mass_g,
        concentrate_ml=concentrate_ml,
        ethanol_ml=ethanol_ml,
        batch_volume_ml=float(batch_volume_ml),
        overfilled=overfilled,
        assumptions=tuple(assumptions),
    )
