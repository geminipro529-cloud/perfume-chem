from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RosterRow:
    rank: int
    identity: str
    stock_fraction: float = 1.0
    required: bool = True
    lower_active_parts: float = 0.0
    upper_active_parts: float = math.inf
    manual_multiplier: float = 1.0
    block: str = "unassigned"
    roles: str = ""
    evidence_status: str = "ranked_identity"
    notes: str = ""


@dataclass(frozen=True)
class FormulaRow:
    rank: int
    identity: str
    active_parts: float
    stock_fraction: float
    raw_stock_parts: float
    embedded_carrier_parts: float
    block: str
    roles: str
    evidence_status: str
    notes: str


def canonical_name(name: str) -> str:
    """Normalize names for deterministic matching without claiming chemical equivalence."""
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def canonical_hash(records: Iterable[dict]) -> str:
    payload = json.dumps(
        list(records), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rank_prior(ranks: Sequence[int], total_active_parts: float, exponent: float = 0.7,
               offset: float = 0.0) -> list[float]:
    if total_active_parts <= 0:
        raise ValueError("total_active_parts must be positive")
    if exponent <= 0:
        raise ValueError("exponent must be positive")
    if any(r <= 0 for r in ranks):
        raise ValueError("ranks must be positive integers")
    weights = [(r + offset) ** (-exponent) for r in ranks]
    scale = total_active_parts / sum(weights)
    return [w * scale for w in weights]


def bounded_normalize(seed: Sequence[float], lower: Sequence[float], upper: Sequence[float],
                      total: float, tolerance: float = 1e-9) -> list[float]:
    """Water-filling projection preserving seed ratios among non-bound rows."""
    if not (len(seed) == len(lower) == len(upper)):
        raise ValueError("seed, lower and upper must have equal lengths")
    if sum(lower) - total > tolerance:
        raise ValueError("lower bounds exceed total")
    if sum(upper) + tolerance < total:
        raise ValueError("upper bounds are below total")
    if any(lo < 0 or hi < lo for lo, hi in zip(lower, upper)):
        raise ValueError("invalid bounds")

    x = [0.0] * len(seed)
    free = set(range(len(seed)))
    remaining = total

    while free:
        denom = sum(max(seed[i], 0.0) for i in free)
        if denom <= 0:
            tentative = {i: remaining / len(free) for i in free}
        else:
            tentative = {i: remaining * max(seed[i], 0.0) / denom for i in free}

        hit = False
        for i in list(free):
            if tentative[i] < lower[i] - tolerance:
                x[i] = lower[i]
                remaining -= x[i]
                free.remove(i)
                hit = True
            elif tentative[i] > upper[i] + tolerance:
                x[i] = upper[i]
                remaining -= x[i]
                free.remove(i)
                hit = True
        if not hit:
            for i in free:
                x[i] = tentative[i]
            free.clear()

    drift = total - sum(x)
    if abs(drift) > tolerance:
        candidates = [i for i, value in enumerate(x)
                      if lower[i] + tolerance < value < upper[i] - tolerance]
        if not candidates:
            candidates = list(range(len(x)))
        x[candidates[0]] += drift
    return x


def build_target(rows: Sequence[RosterRow], total_active_parts: float,
                 exponent: float = 0.7, offset: float = 0.0) -> list[FormulaRow]:
    ordered = sorted(rows, key=lambda row: row.rank)
    ranks = [row.rank for row in ordered]
    prior = rank_prior(ranks, total_active_parts, exponent, offset)
    seed = [p * max(row.manual_multiplier, 0.0) for p, row in zip(prior, ordered)]
    lower = [max(row.lower_active_parts, 1e-12 if row.required else 0.0) for row in ordered]
    upper = [row.upper_active_parts for row in ordered]
    active = bounded_normalize(seed, lower, upper, total_active_parts)

    formula: list[FormulaRow] = []
    for row, amount in zip(ordered, active):
        if not (0 < row.stock_fraction <= 1):
            raise ValueError(f"Invalid stock fraction for {row.identity}")
        raw = amount / row.stock_fraction
        formula.append(FormulaRow(
            rank=row.rank,
            identity=row.identity,
            active_parts=amount,
            stock_fraction=row.stock_fraction,
            raw_stock_parts=raw,
            embedded_carrier_parts=raw - amount,
            block=row.block,
            roles=row.roles,
            evidence_status=row.evidence_status,
            notes=row.notes,
        ))
    return formula


def choose_stock_fraction(active_amount: float, min_weighable: float = 5.0,
                          max_weighable: float = 100.0,
                          candidates: Sequence[float] = (1.0, 0.5, 0.2, 0.1, 0.05, 0.01, 0.001)) -> float:
    """Choose the strongest stock that puts the raw dose inside a measurable window."""
    if active_amount <= 0:
        raise ValueError("active_amount must be positive")
    viable = []
    for fraction in candidates:
        raw = active_amount / fraction
        if min_weighable <= raw <= max_weighable:
            viable.append(fraction)
    if viable:
        return max(viable)
    # If no exact fit exists, choose the fraction whose raw amount is closest on log scale.
    target = math.sqrt(min_weighable * max_weighable)
    return min(candidates, key=lambda f: abs(math.log((active_amount / f) / target)))


def read_roster(path: Path) -> list[RosterRow]:
    rows: list[RosterRow] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for record in csv.DictReader(handle):
            upper_text = (record.get("upper_active_parts") or "").strip()
            rows.append(RosterRow(
                rank=int(record["rank"]),
                identity=record["identity"].strip(),
                stock_fraction=float(record.get("stock_fraction") or 1.0),
                required=(record.get("required", "true").strip().casefold() in {"1", "true", "yes", "y"}),
                lower_active_parts=float(record.get("lower_active_parts") or 0.0),
                upper_active_parts=float(upper_text) if upper_text else math.inf,
                manual_multiplier=float(record.get("manual_multiplier") or 1.0),
                block=(record.get("block") or "unassigned").strip(),
                roles=(record.get("roles") or "").strip(),
                evidence_status=(record.get("evidence_status") or "ranked_identity").strip(),
                notes=(record.get("notes") or "").strip(),
            ))
    ranks = [row.rank for row in rows]
    if len(ranks) != len(set(ranks)):
        raise ValueError("Duplicate ranks in roster")
    canonical = [canonical_name(row.identity) for row in rows]
    if len(canonical) != len(set(canonical)):
        raise ValueError("Duplicate canonical identities in roster")
    return rows


def write_formula(path: Path, formula: Sequence[FormulaRow]) -> None:
    fields = list(asdict(formula[0]).keys()) if formula else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in formula:
            writer.writerow(asdict(row))


def read_amount_ledger(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            identity = row["identity"].strip()
            key = canonical_name(identity)
            if key in result:
                raise ValueError(f"Duplicate identity in ledger: {identity}")
            result[key] = row
    return result


def diff_ledgers(target_csv: Path, bottle_csv: Path) -> dict:
    target = read_amount_ledger(target_csv)
    bottle = read_amount_ledger(bottle_csv)
    missing, extra, mismatched, matched = [], [], [], []

    for key, target_row in target.items():
        if key not in bottle:
            missing.append(target_row["identity"])
            continue
        bottle_row = bottle[key]
        target_amount = float(target_row.get("raw_stock_parts") or target_row.get("amount") or 0)
        bottle_amount = float(bottle_row.get("raw_stock_parts") or bottle_row.get("amount") or 0)
        if not math.isclose(target_amount, bottle_amount, rel_tol=1e-6, abs_tol=1e-9):
            mismatched.append({
                "identity": target_row["identity"],
                "target": target_amount,
                "bottle": bottle_amount,
                "delta": bottle_amount - target_amount,
            })
        else:
            matched.append(target_row["identity"])

    for key, bottle_row in bottle.items():
        if key not in target:
            extra.append(bottle_row["identity"])

    return {"missing": missing, "extra": extra, "mismatched": mismatched, "matched": matched}


def anti_compression_report(mapping_csv: Path) -> dict:
    """Flag one build material representing multiple target identities."""
    by_build: dict[str, list[dict]] = {}
    missing_loss = []
    with mapping_csv.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            target = row["target_identity"].strip()
            build = row["build_identity"].strip()
            if not build:
                continue
            by_build.setdefault(canonical_name(build), []).append(row)
            if canonical_name(target) != canonical_name(build) and not (row.get("loss_statement") or "").strip():
                missing_loss.append({"target": target, "build": build})

    collapsed = []
    for group in by_build.values():
        targets = sorted({row["target_identity"].strip() for row in group})
        if len(targets) > 1:
            allowed = all((row.get("allow_multi_target") or "").strip().casefold() in {"1", "true", "yes"}
                          for row in group)
            collapsed.append({
                "build_identity": group[0]["build_identity"].strip(),
                "target_identities": targets,
                "allowed": allowed,
                "loss_statements_present": all(bool((row.get("loss_statement") or "").strip()) for row in group),
            })
    return {"collapsed_mappings": collapsed, "missing_loss_statements": missing_loss}


def cmd_build(args: argparse.Namespace) -> None:
    rows = read_roster(Path(args.roster))
    formula = build_target(rows, args.total_active, args.exponent, args.offset)
    write_formula(Path(args.output), formula)
    target_hash = canonical_hash(asdict(row) for row in formula)
    raw_total = sum(row.raw_stock_parts for row in formula)
    carrier = sum(row.embedded_carrier_parts for row in formula)
    print(json.dumps({
        "output": args.output,
        "target_hash": target_hash,
        "active_total": sum(row.active_parts for row in formula),
        "raw_stock_total": raw_total,
        "embedded_carrier_total": carrier,
    }, indent=2))


def cmd_diff(args: argparse.Namespace) -> None:
    print(json.dumps(diff_ledgers(Path(args.target), Path(args.bottle)), indent=2))


def cmd_hash(args: argparse.Namespace) -> None:
    ledger = read_amount_ledger(Path(args.csv))
    records = [ledger[key] for key in sorted(ledger)]
    print(canonical_hash(records))


def cmd_compression(args: argparse.Namespace) -> None:
    print(json.dumps(anti_compression_report(Path(args.mapping)), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic helpers for non-compressed perfume reconstruction")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build a target prior from a ranked identity roster")
    build.add_argument("--roster", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--total-active", type=float, required=True)
    build.add_argument("--exponent", type=float, default=0.7)
    build.add_argument("--offset", type=float, default=0.0)
    build.set_defaults(func=cmd_build)

    diff = sub.add_parser("diff", help="Diff a target formula against the physical bottle ledger")
    diff.add_argument("--target", required=True)
    diff.add_argument("--bottle", required=True)
    diff.set_defaults(func=cmd_diff)

    hash_cmd = sub.add_parser("hash", help="Hash a CSV ledger canonically")
    hash_cmd.add_argument("--csv", required=True)
    hash_cmd.set_defaults(func=cmd_hash)

    compression = sub.add_parser("compression", help="Audit substitution mappings for multi-target collapse")
    compression.add_argument("--mapping", required=True)
    compression.set_defaults(func=cmd_compression)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
