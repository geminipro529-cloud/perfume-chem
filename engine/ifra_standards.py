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
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

_T = TypeVar("_T")

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

CONSTITUENTS_SCHEMA_VERSION = "ifra_annex1_constituents/1"
DEFAULT_CONSTITUENTS_PATH = DEFAULT_TABLE_PATH.parent / "ifra_annex1_constituents.json"
UNDISCLOSED_BASES_SCHEMA_VERSION = "ifra_undisclosed_bases/1"
DEFAULT_UNDISCLOSED_BASES_PATH = DEFAULT_TABLE_PATH.parent / "ifra_undisclosed_bases.json"

_TOLERANCE = 1e-12
_PERCENT_NUMBER = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
# Stock-name suffixes that hide the material name: "(...)", " 20% EtOH", " F3255".
_TRAILING_PARENTHETICAL = re.compile(r"\s*\([^()]*\)\s*$")
# One strength phrase: the number, the "%" and the text up to the next "(" or the end.
_STRENGTH_PHRASE = re.compile(r"\s+\d+(?:[.,]\d+)?\s*%[^(]*")
_TRAILING_LOT_CODE = re.compile(r"\s+[A-Za-z]{0,4}\d{3,}[A-Za-z0-9-]*\s*$")


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
    # Said on the row's own gate message, e.g. a stock whose species is not recorded.
    identity_note: str | None = None


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
    # Word-order-free keys ("Damascone Alpha" = "Alpha Damascone"); a key that two
    # materials share maps to None so it never picks either.
    _order_index: Mapping[str, IFRAMaterial | None] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        index: dict[str, IFRAMaterial] = {}
        order_index: dict[str, IFRAMaterial | None] = {}
        for material in self.materials.values():
            for name in (material.name, *material.aliases):
                index[_normalise(name)] = material
                key = _order_key(name)
                if order_index.get(key, material) is not material:
                    order_index[key] = None
                else:
                    order_index[key] = material
        object.__setattr__(self, "_index", index)
        object.__setattr__(self, "_order_index", order_index)

    def lookup(self, *names: str | None) -> IFRAMaterial | None:
        """Return the first material matching any name, case/whitespace-insensitive.

        Every name is tried exactly first; only when none matches is each retried without
        its stock suffix (see ``stock_base_name``), so an exact name always wins. Only when
        that fails too are the same forms compared with their words in any order, so
        "Damascone Alpha" finds "Alpha Damascone". Words are never dropped or added:
        "Methyl Ionone" and "Ionone" stay different names.
        """
        return self._match(names)[1]

    def _match(self, names: Sequence[str | None]) -> tuple[str | None, IFRAMaterial | None]:
        given = [name for name in names if name and name.strip()]
        for name in given:
            material = self._index.get(_normalise(name))
            if material is not None:
                return name, material
        # Least-stripped form first, across all given names, before any more-stripped form.
        levels = [_stripped_forms(name) for name in given]
        depths = range(max((len(forms) for forms in levels), default=0))
        for depth in depths:
            for name, forms in zip(given, levels):
                if depth < len(forms):
                    for form in forms[depth]:
                        material = self._index.get(_normalise(form))
                        if material is not None:
                            return name, material
        # Then the same forms, in the same order, with their words in any order.
        for name in given:
            material = self._order_index.get(_order_key(name))
            if material is not None:
                return name, material
        for depth in depths:
            for name, forms in zip(given, levels):
                if depth < len(forms):
                    for form in forms[depth]:
                        material = self._order_index.get(_order_key(form))
                        if material is not None:
                            return name, material
        return None, None

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
    # The matched table material's canonical name, which group "members" are keyed by.
    ifra_name: str | None = None


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
class IFRAConstituentContributor:
    # Table canonical name; the key of this material in the group check's member_pcts.
    material: str
    # "natural" (an Annex I constituent), "schiff_base" (the substance's share by mass of a
    # Schiff base made from it) or "synthetic" (the substance's own row)
    kind: str
    pct: float  # the material's own finished-product % w/w
    # natural: its Annex I level of the substance, %; schiff_base: the substance's mass share
    constituent_pct: float | None
    ncs_name: str | None  # natural only: the Annex I row that level comes from
    contribution_pct: float  # finished-product % w/w of the substance from this material


@dataclass(frozen=True)
class IFRAConstituentTotal:
    substance: str
    standard: str
    total: float
    limit_pct: float
    contributors: tuple[IFRAConstituentContributor, ...]


@dataclass(frozen=True)
class SchiffBase:
    """A Schiff base whose share of a restricted aldehyde counts toward that aldehyde's total."""

    name: str
    standard: str
    substance: str
    share_pct: float  # % of the Schiff base's mass that is the restricted substance
    source: str


@dataclass(frozen=True)
class UndisclosedBase:
    """A supplier base whose composition is not published: flagged, never counted."""

    name: str
    reason: str


@dataclass(frozen=True)
class NaturalConstituents:
    """IFRA Annex I levels of restricted substances in owned naturals, per stock.

    ``stocks`` maps a stock's IFRA-table canonical name to {standard id: (level %, NCS
    name)}; the level is the highest across the stock's candidate NCS rows, never a sum.
    ``schiff_bases`` maps a Schiff base's name to the restricted substance it is made from.
    """

    amendment: int | None
    amendment_year: int | None
    verification: str | None
    stocks: Mapping[str, Mapping[str, tuple[float, str]]]
    standards: frozenset[str] = frozenset()  # every standard the file has rows for
    schiff_bases: Mapping[str, SchiffBase] = field(default_factory=dict)

    def schiff_base(self, names: Sequence[str | None]) -> SchiffBase | None:
        """The Schiff base a row names, by any of its names with stock suffixes stripped."""
        return _match_by_name(self.schiff_bases, names)

    def coverage_note(self, table: IFRATable) -> str:
        names = sorted({table.standards[sid].name for sid in self.standards})
        return (
            f"Restricted constituents of naturals are counted for {len(names)} substances "
            f"({', '.join(names)}), using the highest level IFRA Amendment "
            f"{self.amendment} ({self.amendment_year}) Annex I reports for each natural. "
            "Each value was read twice by independent automated readers and has not been "
            "checked by a person. Annexes of other restricted substances were not read, so "
            "their amounts in naturals are not counted."
        )


@dataclass(frozen=True)
class IFRAEvaluation:
    checks: tuple[IFRACheck, ...]
    group_checks: tuple[IFRAGroupCheck, ...]
    constituent_totals: tuple[IFRAConstituentTotal, ...] = ()

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


def load_natural_constituents(path: str | Path | None = None) -> NaturalConstituents:
    """Load the Annex I constituent levels. The default path is cached; explicit paths are not."""
    if path is None:
        return _load_default_constituents()
    return _load_constituents(Path(path))


@lru_cache(maxsize=1)
def _load_default_constituents() -> NaturalConstituents:
    return _load_constituents(DEFAULT_CONSTITUENTS_PATH)


def _load_constituents(path: Path) -> NaturalConstituents:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != CONSTITUENTS_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version {raw.get('schema_version')!r} is not "
            f"{CONSTITUENTS_SCHEMA_VERSION!r}"
        )
    rows_by_ncs: dict[str, list[Mapping]] = {}
    for row in raw.get("rows", []):
        if not _is_number(row.get("max_pct")):
            raise ValueError(f"{path}: row {row!r} has no numeric max_pct")
        rows_by_ncs.setdefault(row["ncs_name"], []).append(row)
    stocks: dict[str, dict[str, tuple[float, str]]] = {}
    for stock, rec in raw.get("stocks", {}).items():
        levels: dict[str, tuple[float, str]] = {}
        for ncs in rec.get("ncs_names", ()):
            if ncs not in rows_by_ncs:
                raise ValueError(f"{path}: stock {stock!r} names unknown NCS row {ncs!r}")
            # Several candidate rows (or one substance under several CAS numbers): the
            # highest level per standard, never the sum.
            for row in rows_by_ncs[ncs]:
                level = float(row["max_pct"])
                if row["standard"] not in levels or level > levels[row["standard"]][0]:
                    levels[row["standard"]] = (level, ncs)
        stocks[stock] = levels
    schiff_bases = {}
    for name, rec in raw.get("schiff_bases", {}).items():
        if not _is_number(rec.get("share_pct")) or not 0 < rec["share_pct"] <= 100:
            raise ValueError(f"{path}: Schiff base {name!r} needs a share_pct in (0, 100]")
        schiff_bases[name] = SchiffBase(
            name, rec["standard"], rec["substance"], float(rec["share_pct"]), rec["source"]
        )
    return NaturalConstituents(
        amendment=raw.get("amendment"),
        amendment_year=raw.get("amendment_year"),
        verification=raw.get("verification"),
        stocks=stocks,
        standards=frozenset(row["standard"] for rows in rows_by_ncs.values() for row in rows),
        schiff_bases=schiff_bases,
    )


def load_undisclosed_bases(path: str | Path | None = None) -> tuple[UndisclosedBase, ...]:
    """Load the supplier bases whose composition is not published. Default path is cached."""
    if path is None:
        return _load_default_undisclosed_bases()
    return _load_undisclosed_bases(Path(path))


@lru_cache(maxsize=1)
def _load_default_undisclosed_bases() -> tuple[UndisclosedBase, ...]:
    return _load_undisclosed_bases(DEFAULT_UNDISCLOSED_BASES_PATH)


def _load_undisclosed_bases(path: Path) -> tuple[UndisclosedBase, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != UNDISCLOSED_BASES_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version {raw.get('schema_version')!r} is not "
            f"{UNDISCLOSED_BASES_SCHEMA_VERSION!r}"
        )
    return tuple(UndisclosedBase(b["name"], b["reason"]) for b in raw.get("bases", ()))


def undisclosed_base(
    bases: Iterable[UndisclosedBase], names: Sequence[str | None]
) -> UndisclosedBase | None:
    """The undisclosed base a row names, by any of its names with stock suffixes stripped."""
    return _match_by_name({b.name: b for b in bases}, names)


def _match_by_name(entries: Mapping[str, _T], names: Sequence[str | None]) -> _T | None:
    keyed = {_normalise(name): entry for name, entry in entries.items()}
    for name in names:
        if not name:
            continue
        for form in (name, stock_base_name(name)):
            if (entry := keyed.get(_normalise(form))) is not None:
                return entry
    return None


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
        identity_note=rec.get("identity_note"),
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


def _order_key(name: str) -> str:
    return " ".join(sorted(_normalise(name).split()))


def stock_base_name(name: str) -> str:
    """Strip trailing stock suffixes: a parenthetical, a strength ("20% EtOH") or a lot code.

    "Coumarin 20% EtOH", "Coumarin (20%)" and "Coumarin F3255" all give "Coumarin". Suffixes
    are removed repeatedly until none is left. A name that would be stripped to nothing is
    returned unchanged.
    """
    base = name.strip()
    while True:
        stripped = base
        for pattern in (_TRAILING_PARENTHETICAL, _STRENGTH_PHRASE, _TRAILING_LOT_CODE):
            stripped = _collapse(pattern.sub(" ", stripped))
        if stripped == base:
            break
        base = stripped
    return base or name


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _stripped_forms(name: str) -> list[list[str]]:
    """Stripped forms of a name by number of suffix removals: index 0 is one removal away.

    A removal is one trailing parenthetical, one strength phrase ("10%" and the text after it
    up to the next "("), or a trailing lot code. No duplicates, no empty strings, never the
    original name.
    """
    seen = {_collapse(name)}
    frontier = [_collapse(name)]
    levels: list[list[str]] = []
    while frontier:
        level: list[str] = []
        for current in frontier:
            for form in _one_removal(current):
                if form and form not in seen:
                    seen.add(form)
                    level.append(form)
        if level:
            levels.append(level)
        frontier = level
    return levels


def _one_removal(name: str) -> list[str]:
    forms = []
    paren = _TRAILING_PARENTHETICAL.search(name)
    if paren:
        forms.append(_collapse(name[: paren.start()] + " " + name[paren.end():]))
    for match in _STRENGTH_PHRASE.finditer(name):
        forms.append(_collapse(name[: match.start()] + " " + name[match.end():]))
    lot = _TRAILING_LOT_CODE.search(name)
    if lot:
        forms.append(_collapse(name[: lot.start()] + " " + name[lot.end():]))
    return forms


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
    constituents: NaturalConstituents | None = None,
) -> IFRAEvaluation:
    """Evaluate finished-product % w/w per formula row against the Category 4 table.

    A natural with IFRA Annex I levels in ``constituents`` adds its share of each restricted
    substance to that substance's total (group ``<standard>_constituents``), which replaces
    the synthetic-only standard total. ``constituents`` defaults to the shipped Annex I file
    when the table is the default one; with any other table it is used only when passed.
    """
    table = table if table is not None else load_ifra_table()
    if constituents is None and table is _load_default_table():
        constituents = load_natural_constituents()
    alt_names = alt_names or {}
    checks: list[IFRACheck] = []
    pct_by_member: dict[str, float] = {}
    restricted_rows: dict[str, list[str]] = {}
    natural_pcts: dict[str, float] = {}
    schiff_pcts: dict[str, float] = {}
    for row_name, pct in pct_by_material.items():
        extra = alt_names.get(row_name, ())
        candidates = [row_name, *([extra] if isinstance(extra, str) else extra)]
        matched_name, material = table._match(candidates)
        pct = float(pct)
        schiff = (
            constituents.schiff_base(candidates)
            if material is None and constituents is not None
            else None
        )
        if schiff is not None:
            schiff_pcts[schiff.name] = schiff_pcts.get(schiff.name, 0.0) + pct
            checks.append(_schiff_base_row(row_name, schiff, pct))
            continue
        if material is None:
            checks.append(IFRACheck(
                row_name, None, None, None, pct, None, None, "unchecked",
                f"{row_name} at {_fmt(pct)} % is not in the IFRA Category 4 table; unchecked.",
            ))
            continue
        pct_by_member[material.name] = pct_by_member.get(material.name, 0.0) + pct
        if material.status == "restricted" and material.standard is not None:
            restricted_rows.setdefault(material.standard, []).append(material.name)
        if constituents is not None and material.name in constituents.stocks:
            natural_pcts[material.name] = natural_pcts.get(material.name, 0.0) + pct
        checks.append(_check_row(row_name, matched_name, material, pct, edge_ratio, headroom))
    totals = _constituent_totals(
        table, constituents, natural_pcts, schiff_pcts, pct_by_member, restricted_rows
    )
    counted = {t.standard for t in totals}
    rules = [
        *table.group_rules,
        *(r for r in _standard_total_rules(table, restricted_rows) if r.standard not in counted),
    ]
    group_checks = [
        g
        for rule in rules
        if (g := _check_group(rule, table, pct_by_member, edge_ratio, headroom)) is not None
    ]
    group_checks.extend(_constituent_group_check(t, table, edge_ratio, headroom) for t in totals)
    if totals:
        checks = [_natural_row_counted(c, totals) for c in checks]
    return IFRAEvaluation(
        checks=tuple(checks), group_checks=tuple(group_checks), constituent_totals=totals
    )


def _constituent_totals(
    table: IFRATable,
    constituents: NaturalConstituents | None,
    natural_pcts: Mapping[str, float],
    schiff_pcts: Mapping[str, float],
    pct_by_member: Mapping[str, float],
    restricted_rows: Mapping[str, Sequence[str]],
) -> tuple[IFRAConstituentTotal, ...]:
    """Per standard a natural or Schiff base contributes to: synthetic rows plus shares."""
    if constituents is None or not (natural_pcts or schiff_pcts):
        return ()
    shares: dict[str, list[IFRAConstituentContributor]] = {}
    for name, pct in schiff_pcts.items():
        schiff = constituents.schiff_bases[name]
        shares.setdefault(schiff.standard, []).append(IFRAConstituentContributor(
            name, "schiff_base", pct, schiff.share_pct, None, pct * schiff.share_pct / 100.0
        ))
    for natural, pct in natural_pcts.items():
        for sid, (level, ncs) in constituents.stocks[natural].items():
            contribution = pct * level / 100.0
            if contribution <= 0:
                continue
            shares.setdefault(sid, []).append(
                IFRAConstituentContributor(natural, "natural", pct, level, ncs, contribution)
            )
    totals = []
    for sid in sorted(shares):
        standard = table.standards[sid]
        limit = standard.cat4_limit_pct
        assert limit is not None  # the Annex I file covers Category 4 limits only
        synthetic = [
            IFRAConstituentContributor(
                name, "synthetic", pct_by_member[name], None, None, pct_by_member[name]
            )
            for name in dict.fromkeys(restricted_rows.get(sid, ()))
        ]
        contributors = (*synthetic, *shares[sid])
        totals.append(IFRAConstituentTotal(
            substance=standard.name,
            standard=sid,
            total=sum(c.contribution_pct for c in contributors),
            limit_pct=limit,
            contributors=contributors,
        ))
    return tuple(totals)


def _constituent_group_check(
    total: IFRAConstituentTotal, table: IFRATable, edge_ratio: float, headroom: float
) -> IFRAGroupCheck:
    rule = IFRAGroupRule(
        id=f"{total.standard}_constituents",
        standard=total.standard,
        rule="sum_le_limit",
        limit_pct=total.limit_pct,
        members=tuple(c.material for c in total.contributors),
        quote=None,
    )
    # Keyed by table canonical name: the optimizer scales every row whose ifra_name is a
    # member, and a natural's share scales with its row.
    member_pcts = {c.material: c.contribution_pct for c in total.contributors}
    group = _check_group(rule, table, member_pcts, edge_ratio, headroom)
    assert group is not None  # every total has at least one contributor
    if group.verdict == "fail":
        lead = "exceeds"
    elif group.verdict == "warn":
        lead = f"is {total.total / total.limit_pct:.0%} of"
    else:
        lead = "is within"
    parts = ", ".join(_contribution_text(c) for c in total.contributors)
    kinds = {c.kind for c in total.contributors}
    sources = [
        *(["naturals' IFRA Annex I constituents"] if "natural" in kinds else []),
        *(["Schiff bases' share"] if "schiff_base" in kinds else []),
    ]
    message = (
        f"{total.substance} ({total.standard}) including {' and '.join(sources)}: "
        f"{parts}; total {_fmt(total.total)} % {lead} the IFRA Category 4 "
        f"limit of {_fmt(total.limit_pct)} %"
        + (f" (headroom {headroom:g})." if headroom != 1 else ".")
    )
    return replace(group, message=message)


def _contribution_text(c: IFRAConstituentContributor) -> str:
    if c.kind == "synthetic":
        return f"{c.material} {_fmt(c.contribution_pct)} %"
    if c.kind == "schiff_base":
        return (
            f"{c.material} {_fmt(c.contribution_pct)} % ({_fmt(c.pct)} % of the product x "
            f"{_fmt(c.constituent_pct or 0.0)} % by mass, Schiff base)"
        )
    return (
        f"{c.material} {_fmt(c.contribution_pct)} % ({_fmt(c.pct)} % of the product x up "
        f"to {_fmt(c.constituent_pct or 0.0)} % in {c.ncs_name})"
    )


def _schiff_base_row(row_name: str, schiff: SchiffBase, pct: float) -> IFRACheck:
    """A Schiff base's own row passes; its share of the restricted substance is in the total."""
    return IFRACheck(
        material=row_name,
        matched_name=schiff.name,
        status="schiff_base",
        standard=schiff.standard,
        pct=pct,
        limit_pct=None,
        ratio=None,
        verdict="pass",
        message=(
            f"{row_name} at {_fmt(pct)} % is a Schiff base of {schiff.substance}; "
            f"{_fmt(schiff.share_pct)} % of it ({_fmt(pct * schiff.share_pct / 100.0)} % of "
            f"the product) is counted toward the {schiff.substance} ({schiff.standard}) "
            f"total. Source: {schiff.source}."
        ),
        ifra_name=schiff.name,
    )


def _natural_row_counted(check: IFRACheck, totals: Sequence[IFRAConstituentTotal]) -> IFRACheck:
    """Say on a mapped natural's own row what was counted; its verdict is kept."""
    if check.status != "natural_no_own_standard":
        return check
    counted = [
        (t, c)
        for t in totals
        for c in t.contributors
        if c.kind == "natural" and c.material == check.ifra_name
    ]
    if not counted:
        return check
    name = check.ifra_name
    label = check.material if check.material == name else f"{check.material} ({name})"
    parts = ", ".join(
        f"{t.substance} up to {_fmt(c.constituent_pct or 0.0)} % "
        f"({_fmt(c.contribution_pct)} % of the product)"
        for t, c in counted
    )
    message = (
        f"{label} at {_fmt(check.pct)} % is a natural with no IFRA standard of its own; its "
        f"IFRA Annex I constituents are counted toward their Category 4 totals: {parts}. "
        "Other restricted constituents are not counted."
    )
    return replace(check, message=message)


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
    else:  # natural_no_own_standard (evaluate_ifra rewords it if constituents were counted)
        verdict = "warn"
        message = (
            f"{label} at {_fmt(pct)} % is a natural with no IFRA standard of its own; its "
            f"restricted constituents are not summed here."
        )
    if material.identity_note:
        message = f"{message} {material.identity_note}"
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
        ifra_name=material.name,
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
    fraction_basis: str = "unspecified"
    stock_density_g_ml: float | None = None


# How a diluted stock's ``active_fraction`` is meant, in formula_state's words and short forms.
_FRACTION_BASES = {
    "mass_fraction": "w/w",
    "w/w": "w/w",
    "volume_fraction": "v/v",
    "v/v": "v/v",
    "neat": "v/v",
    "mass_per_volume": "w/v",
    "w/v": "w/v",
}
_BASIS_DISAGREEMENT = 0.005


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
    is ``active_g`` when known (its carrier then taken as the remaining volume fraction).
    Otherwise a diluted stock is read by its ``fraction_basis``: v/v (active volume times its
    density), w/w (that share of the stock's mass, the stock density given or by ideal mixing)
    or w/v (fraction x stock mL in grams). An unspecified basis takes whichever of the v/v and
    w/w readings gives more active mass, the conservative side of an upper limit. Missing
    densities fall back to 1.0 g/mL; these and any basis choice are listed in ``assumptions``.
    When the stocks alone exceed the bottle, ``overfilled`` is set and no ethanol is added.
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
        if row.active_g is None and 0.0 < fraction < 1.0:
            mass, carrier_g = _diluted_stock_masses(row, stock_ml, fraction, assumptions)
            active_mass[row.name] = active_mass.get(row.name, 0.0) + mass
            carrier_mass_g += carrier_g
            continue
        if row.active_g is not None:
            mass = float(row.active_g)
        else:
            mass = stock_ml * fraction * _active_density(row, assumptions)
        active_mass[row.name] = active_mass.get(row.name, 0.0) + mass
        carrier_ml = stock_ml * (1.0 - fraction)
        if carrier_ml > 0:
            carrier_mass_g += carrier_ml * _carrier_density(row, assumptions)
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


def _active_density(row: FinishedProductRow, assumptions: list[str]) -> float:
    if row.active_density_g_ml is not None:
        return float(row.active_density_g_ml)
    assumptions.append(f"{row.name}: density unknown, {DEFAULT_DENSITY_G_ML} g/mL used")
    return DEFAULT_DENSITY_G_ML


def _carrier_density(row: FinishedProductRow, assumptions: list[str]) -> float:
    carrier = (row.carrier or "").strip()
    density = CARRIER_DENSITY_G_ML.get(carrier.casefold())
    if density is not None:
        return density
    assumptions.append(
        f"{row.name}: carrier {carrier or 'not recorded'} has no density here, "
        f"{DEFAULT_DENSITY_G_ML} g/mL used"
    )
    return DEFAULT_DENSITY_G_ML


def _diluted_stock_masses(
    row: FinishedProductRow, stock_ml: float, fraction: float, assumptions: list[str]
) -> tuple[float, float]:
    """Active and carrier grams of a diluted stock without a known active mass."""
    basis = _FRACTION_BASES.get(str(row.fraction_basis).strip().casefold(), "unspecified")
    if basis == "w/w" and row.stock_density_g_ml is not None:
        stock_g = stock_ml * float(row.stock_density_g_ml)
        return fraction * stock_g, (1.0 - fraction) * stock_g
    active_density = _active_density(row, assumptions)
    carrier_density = _carrier_density(row, assumptions)
    if basis == "w/v":
        active_g = fraction * stock_ml
        carrier_ml = max(stock_ml - active_g / active_density, 0.0)
        return active_g, carrier_ml * carrier_density
    by_volume = (
        stock_ml * fraction * active_density,
        stock_ml * (1.0 - fraction) * carrier_density,
    )
    stock_density = 1.0 / (fraction / active_density + (1.0 - fraction) / carrier_density)
    by_weight = (fraction * stock_ml * stock_density, (1.0 - fraction) * stock_ml * stock_density)
    if basis == "v/v":
        return by_volume
    if basis == "w/w":
        return by_weight
    chosen, other, reading = (
        (by_weight, by_volume, "w/w")
        if by_weight[0] >= by_volume[0]
        else (by_volume, by_weight, "v/v")
    )
    if chosen[0] > 0 and (chosen[0] - other[0]) / chosen[0] > _BASIS_DISAGREEMENT:
        assumptions.append(
            f"{row.name}: dilution basis not recorded, read as {reading} "
            "(the reading with more active material)"
        )
    return chosen
