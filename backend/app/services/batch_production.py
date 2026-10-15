"""Production batches: scale a formula card, rerun the release gate, keep a record.

Kenny fills 30 mL bottles to sell. A batch takes one formula card (a project
formula file or a pasted table), scales every row by one factor, reruns the
release gate on the scaled card, and appends a batch record to a personal,
append-only log in ``data/user`` (gitignored: formulas, gate output and batch
records never go into the public repository).

Scaling keeps every stock and every strength; only amounts change:

    factor = bottles * bottle_ml / card_total_ml * (1 + loss_percent / 100)

Amounts are exact Decimals and are rounded once, to whole µL or whole mg.
The batch record keeps the planned rows and, later, what was actually weighed,
in a shape that could be imported as Lab bottle events (not built here).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.config import PROJECT_ROOT
from app.services.formula_import import (
    FormulaAnalysisImportParser,
    FormulaAnalysisLibrary,
    ParsedAnalysisRow,
)

BATCH_RECORD_PATH_ENV = "PERFUME_BATCH_RECORD_PATH"
BATCH_DIR_ENV = "PERFUME_BATCH_DIR"
BATCH_RECORD_LOG_NAME = "user_batch_records.jsonl"
DEFAULT_BATCH_RECORD_PATH = PROJECT_ROOT / "data" / "user" / BATCH_RECORD_LOG_NAME
DEFAULT_BATCH_DIR = PROJECT_ROOT / "data" / "user" / "batches"
GATE_SCRIPT = PROJECT_ROOT / "scripts" / "formula_release_gate.py"
GATE_TIMEOUT_SECONDS = 60 * 60

RECORD_SCHEMA = "user-batch-record-v1"
ROUNDING_NOTE = "Scaled amounts are rounded to the nearest whole µL or whole mg."
_UNIT_TO_BASE = {"uL": ("uL", Decimal(1)), "mL": ("uL", Decimal(1000)), "mg": ("mg", Decimal(1)), "g": ("mg", Decimal(1000))}
_UNIT_LABEL = {"uL": "µL", "mg": "mg"}
_LOT_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_VOLUME_IN_NAME = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*-?\s*ml\b", re.IGNORECASE)

# One release gate at a time in this checkout, across every request thread.
_GATE_LOCK = threading.Lock()
# Reentrant: record_actuals holds it across its read, check and append.
_LOG_LOCK = threading.RLock()
_RUNS_LOCK = threading.Lock()
_RUNS: dict[str, dict[str, Any]] = {}


class BatchError(ValueError):
    """A batch request that can't be carried out; the message says why."""


class BatchConflictError(BatchError):
    """The batch changed since the device that sent this loaded it.

    `code` is BATCH_CHANGED when another device saved weighed amounts in
    between, or BATCH_REPLACED when the lot is now a different batch.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Scaling (pure)


def _decimal(value: Any, label: str, *, positive: bool = True, allow_zero: bool = False) -> Decimal:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise BatchError(f"{label} must be a number.") from None
    if not number.is_finite():
        raise BatchError(f"{label} must be a number.")
    if positive and (number < 0 or (number == 0 and not allow_zero)):
        raise BatchError(f"{label} must be more than 0." if not allow_zero else f"{label} can't be below 0.")
    return number


def _text(value: Decimal) -> str:
    rendered = format(value.normalize(), "f") if value != 0 else "0"
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def card_volume_from_name(*names: str | None) -> Decimal | None:
    """The mL a card says it makes in its title or file name ("30mL EDP")."""

    for name in names:
        match = _VOLUME_IN_NAME.search((name or "").replace("_", " "))
        if match:
            value = Decimal(match.group(1))
            if Decimal(1) <= value <= Decimal(1000):
                return value
    return None


def strength_words(row: ParsedAnalysisRow) -> str:
    """The strength cell for the scaled card: as written on the source card."""

    if row.strength_text:
        return row.strength_text
    if row.concentration_basis == "NEAT":
        return "neat"
    if row.concentration_fraction_decimal is None:
        return ""
    percent = _text(Decimal(row.concentration_fraction_decimal) * 100)
    basis = {"W_W": " w/w", "V_V": " v/v"}.get(row.concentration_basis, "")
    return f"{percent}%{basis}"


def scale_card(
    rows: list[ParsedAnalysisRow],
    *,
    bottles: Any,
    bottle_ml: Any = "30",
    card_total_ml: Any,
    loss_percent: Any = "3",
) -> dict[str, Any]:
    """Scale a card's rows to ``bottles`` bottles of ``bottle_ml`` plus a loss allowance."""

    if not rows:
        raise BatchError("The formula has no rows to scale.")
    bottle_count = _decimal(bottles, "Number of bottles")
    if bottle_count != bottle_count.to_integral_value():
        raise BatchError("Number of bottles must be a whole number.")
    bottle = _decimal(bottle_ml, "Bottle size")
    card_total = _decimal(card_total_ml, "Card total volume")
    loss = _decimal(loss_percent, "Loss allowance", allow_zero=True)
    if loss > 100:
        raise BatchError("Loss allowance can't be above 100%.")

    factor = bottle_count * bottle / card_total * (1 + loss / 100)
    finished_ml = bottle_count * bottle * (1 + loss / 100)
    scaled_rows: list[dict[str, Any]] = []
    totals = {"uL": Decimal(0), "mg": Decimal(0)}
    card_totals = {"uL": Decimal(0), "mg": Decimal(0)}
    warnings: list[str] = []
    worst_deviation = Decimal(0)
    for index, row in enumerate(rows, start=1):
        unit, per_unit = _UNIT_TO_BASE[row.amount_unit]
        card_amount = Decimal(row.amount_decimal) * per_unit
        exact = card_amount * factor
        rounded = exact.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        if rounded == 0:
            warnings.append(
                f"{row.material} comes to {_text(exact)} {_UNIT_LABEL[unit]}, which rounds to 0; "
                "use a weaker dilution or a bigger batch."
            )
        else:
            worst_deviation = max(worst_deviation, abs(rounded - exact) / exact)
        totals[unit] += rounded
        card_totals[unit] += card_amount
        scaled_rows.append(
            {
                "line": index,
                "material": row.material,
                "strength": strength_words(row),
                "concentration_fraction_decimal": row.concentration_fraction_decimal,
                "concentration_basis": row.concentration_basis,
                "unit": unit,
                "card_amount": _text(card_amount),
                "exact_amount": _text(exact),
                "planned_amount": _text(rounded),
            }
        )
    units = {row["unit"] for row in scaled_rows}
    return {
        "factor": _text(factor),
        "bottles": _text(bottle_count),
        "bottle_ml": _text(bottle),
        "card_total_ml": _text(card_total),
        "loss_percent": _text(loss),
        "finished_volume_ml": _text(finished_ml),
        "rows": scaled_rows,
        "totals": {
            "planned_ul": _text(totals["uL"]),
            "planned_mg": _text(totals["mg"]),
            "card_ul": _text(card_totals["uL"]),
            "card_mg": _text(card_totals["mg"]),
        },
        "units": sorted(units),
        "mixed_units": len(units) > 1,
        "rounding": ROUNDING_NOTE,
        # Every row keeps its stock and strength; only rounding moves a ratio.
        "proportionality": {
            "strengths_unchanged": True,
            "largest_rounding_change_percent": _text((worst_deviation * 100).quantize(Decimal("0.001"))),
        },
        "warnings": warnings,
    }


def scaled_formula_text(name: str, lot: str, scaled: dict[str, Any]) -> str:
    """A Markdown card of the scaled rows that the release gate parses."""

    units = scaled["units"]
    if len(units) != 1:
        raise BatchError("The card mixes µL and mg rows; the gate can only read one kind at a time.")
    unit = units[0]
    amount_header = "µL" if unit == "uL" else "Add, mg"
    clean = lambda text: str(text).replace("|", "/").replace("\n", " ").strip()  # noqa: E731
    lines = [
        f"# {clean(name)} - batch {clean(lot)}",
        "",
        f"Production batch: {scaled['bottles']} x {scaled['bottle_ml']} mL with "
        f"{scaled['loss_percent']}% loss allowance (factor {scaled['factor']}). {ROUNDING_NOTE}",
        "",
        f"| # | Ingredient | Dilution | {amount_header} |",
        "|---|---|---|---:|",
    ]
    for row in scaled["rows"]:
        lines.append(
            f"| {row['line']} | {clean(row['material'])} | {clean(row['strength'])} | {row['planned_amount']} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Sources


def load_card(source_path: str | None, text: str | None, name: str | None) -> dict[str, Any]:
    """Read a project formula or pasted table; return its rows, name and hash."""

    library = FormulaAnalysisLibrary()
    if source_path:
        # load_source validates the path (inside formulas/, Markdown, size).
        library.load_source(source_path)
        relative = PurePosixPath(source_path.strip())
        source_bytes = library.root.joinpath(*relative.parts).read_bytes()
        default_name = relative.stem
    elif text and text.strip():
        source_bytes = text.encode("utf-8")
        if len(source_bytes) > library.MAX_SOURCE_BYTES:
            raise BatchError("The pasted formula is too long.")
        default_name = (name or "").strip() or "Pasted formula"
    else:
        raise BatchError("Choose a project formula or paste a formula table.")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    result = FormulaAnalysisImportParser.parse_text(
        source_bytes.decode("utf-8"), default_name=default_name, source_sha256=source_hash
    )
    if result.errors:
        raise BatchError(" ".join(result.errors))
    return {
        "source_path": source_path.strip() if source_path else None,
        "source_sha256": source_hash,
        "formula_name": result.formula_name,
        "rows": result.rows,
        "warnings": result.warnings,
    }


def plan_batch(
    *,
    source_path: str | None,
    text: str | None,
    name: str | None,
    bottles: Any,
    bottle_ml: Any,
    card_total_ml: Any,
    loss_percent: Any,
) -> dict[str, Any]:
    """Load a card and scale it; the card's own mL is used when none is given."""

    card = load_card(source_path, text, name)
    given = str(card_total_ml).strip() if card_total_ml is not None else ""
    if given:
        total: Any = given
        total_source = "given"
    else:
        found = card_volume_from_name(card["formula_name"], source_path)
        if found is None:
            raise BatchError(
                "The card doesn't say how many mL it makes. Enter the card's total volume, "
                "stocks plus alcohol, in mL."
            )
        total = found
        total_source = "formula name"
    scaled = scale_card(
        card["rows"], bottles=bottles, bottle_ml=bottle_ml, card_total_ml=total, loss_percent=loss_percent
    )
    return {
        "source_path": card["source_path"],
        "source_sha256": card["source_sha256"],
        "formula_name": card["formula_name"],
        "card_total_ml_source": total_source,
        "parse_warnings": card["warnings"],
        **scaled,
    }


# ---------------------------------------------------------------------------
# Lot numbers and the batch record log


def check_lot(lot: str) -> str:
    value = str(lot or "").strip()
    if not _LOT_PATTERN.fullmatch(value):
        raise BatchError("A lot number uses letters, digits, '-', '_' or '.', up to 64 characters.")
    return value


def suggest_lot(initials: str, day: date, taken: set[str]) -> str:
    """``<INITIALS>-YYYYMMDD-NN``, the first number not already used."""

    prefix = re.sub(r"[^A-Za-z]", "", initials or "").upper()[:4] or "LOT"
    stem = f"{prefix}-{day:%Y%m%d}"
    for number in range(1, 1000):
        lot = f"{stem}-{number:02d}"
        if lot not in taken:
            return lot
    raise BatchError("Too many lots on one day; type a lot number.")


def batch_record_path() -> Path:
    override = os.environ.get(BATCH_RECORD_PATH_ENV, "").strip()
    return Path(override).resolve() if override else DEFAULT_BATCH_RECORD_PATH


def batch_dir() -> Path:
    override = os.environ.get(BATCH_DIR_ENV, "").strip()
    return Path(override).resolve() if override else DEFAULT_BATCH_DIR


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    previous = None
    for number, line in enumerate(path.read_bytes().splitlines(), start=1):
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("previous_line_sha256") != previous:
            raise BatchError(f"The batch record log is broken at line {number}; it was edited by hand.")
        previous = hashlib.sha256(line).hexdigest()
        events.append(event)
    return events


def _append_event(event: dict[str, Any]) -> dict[str, Any]:
    path = batch_record_path()
    with _LOG_LOCK:
        _read_events(path)  # refuse to extend a broken chain
        previous = None
        if path.exists():
            lines = [line for line in path.read_bytes().splitlines() if line.strip()]
            previous = hashlib.sha256(lines[-1]).hexdigest() if lines else None
        stamped = {**event, "previous_line_sha256": previous}
        line = json.dumps(stamped, ensure_ascii=False, sort_keys=True).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as handle:
            handle.write(line + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    return stamped


def _fold(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for event in events:
        lot = event["lot"]
        if event["event"] == "BATCH_RECORDED":
            records[lot] = {**event["record"], "actuals": [], "actuals_recorded_at": None, "actuals_version": 0}
        elif event["event"] == "ACTUALS_RECORDED" and lot in records:
            records[lot]["actuals"] = event["actuals"]
            records[lot]["actuals_recorded_at"] = event["recorded_at"]
            # Counts the saves, so a device can say which set its changes started from.
            records[lot]["actuals_version"] += 1
            if event.get("notes"):
                records[lot]["actual_notes"] = event["notes"]
    return records


def list_records() -> list[dict[str, Any]]:
    return sorted(_fold(_read_events(batch_record_path())).values(), key=lambda r: r["recorded_at"], reverse=True)


def get_record(lot: str) -> dict[str, Any]:
    record = _fold(_read_events(batch_record_path())).get(check_lot(lot))
    if record is None:
        raise LookupError("No batch with that lot number.")
    return record


def taken_lots() -> set[str]:
    return set(_fold(_read_events(batch_record_path())))


def record_batch(
    *,
    lot: str,
    made_on: str,
    made_by: str,
    plan: dict[str, Any],
    gate_run_id: str | None,
    notes: str,
) -> dict[str, Any]:
    lot = check_lot(lot)
    if lot in taken_lots():
        raise BatchError(f"Lot {lot} is already recorded; choose another lot number.")
    try:
        day = date.fromisoformat(made_on)
    except ValueError:
        raise BatchError("Date must look like 2026-10-13.") from None
    gate: dict[str, Any] | None = None
    if gate_run_id:
        run = gate_run_status(gate_run_id)
        if run["lot"] != lot:
            raise BatchError("That gate run was for another lot number.")
        gate = {key: run.get(key) for key in ("run_id", "state", "status", "gate_json_path", "not_pass")}
    record = {
        "schema_version": RECORD_SCHEMA,
        "lot": lot,
        "made_on": day.isoformat(),
        "made_by": str(made_by or "").strip()[:120],
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "formula_name": plan["formula_name"],
        "source_path": plan["source_path"],
        "source_sha256": plan["source_sha256"],
        "bottles": plan["bottles"],
        "bottle_ml": plan["bottle_ml"],
        "card_total_ml": plan["card_total_ml"],
        "loss_percent": plan["loss_percent"],
        "factor": plan["factor"],
        "finished_volume_ml": plan["finished_volume_ml"],
        "rounding": plan["rounding"],
        "planned_rows": plan["rows"],
        "gate": gate,
        "notes": str(notes or "").strip()[:4000],
    }
    _append_event({"event": "BATCH_RECORDED", "lot": lot, "record": record})
    return get_record(lot)


# A stock's density, from the material data and its carrier on the bench sheet
# (bench-sheet.js benchStockDensity); outside this range it is a typing slip.
_DENSITY_RANGE = (Decimal("0.5"), Decimal("2.5"))


def _given(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _actual_amount(line: Any, unit: str, item: dict[str, Any]) -> dict[str, str]:
    """The amount in the line's own unit, typed or worked out from grams weighed.

    The phone's bench mode weighs a µL line on the balance: the grams and the
    stock density it used are kept, and the µL is worked out here, to 0.1 µL.
    """

    if not _given(item.get("weighed_g")):
        amount = _decimal(item.get("actual_amount"), f"Line {line} actual amount", allow_zero=True)
        return {"actual_amount": _text(amount)}
    if _given(item.get("actual_amount")):
        raise BatchError(f"Line {line}: give the amount or the grams weighed, not both.")
    grams = _decimal(item.get("weighed_g"), f"Line {line} grams weighed", allow_zero=True)
    if unit == "mg":
        return {"actual_amount": _text(grams * 1000), "weighed_g": _text(grams)}
    density = _decimal(item.get("density_g_ml"), f"Line {line} density")
    if not _DENSITY_RANGE[0] <= density <= _DENSITY_RANGE[1]:
        raise BatchError(f"Line {line} density must be between 0.5 and 2.5 g/mL.")
    microlitres = (grams * 1000 / density).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return {"actual_amount": _text(microlitres), "weighed_g": _text(grams), "density_g_ml": _text(density)}


def _kept_grams(item: dict[str, Any], saved: dict[str, Any] | None) -> dict[str, Any]:
    """An amount sent unchanged keeps the grams it was worked out from.

    The PC's table shows and sends a line's amount only; a line weighed in grams
    on the phone and sent back unchanged keeps its grams and density.
    """

    if not saved or not saved.get("weighed_g") or _given(item.get("weighed_g")) or not _given(item.get("actual_amount")):
        return item
    try:
        same = Decimal(str(item["actual_amount"]).strip()) == Decimal(str(saved["actual_amount"]))
    except (InvalidOperation, ValueError):
        return item
    if not same:
        return item
    kept = {"line": item.get("line"), "weighed_g": saved["weighed_g"]}
    if saved.get("density_g_ml"):
        kept["density_g_ml"] = saved["density_g_ml"]
    return kept


def record_actuals(
    lot: str,
    actuals: list[dict[str, Any]],
    notes: str,
    *,
    based_on: int | None = None,
    batch_recorded_at: str | None = None,
) -> dict[str, Any]:
    """Save what was actually weighed for each planned line (any subset).

    Each save replaces the batch's earlier weighed amounts. Two devices save the
    same batch (the PC's table and the phone's bench mode), so a device says
    which batch it loaded (`batch_recorded_at`, the record's `recorded_at`) and
    which saved set its changes started from (`based_on`, the record's
    `actuals_version`). If another device saved in between, the save is refused
    with BatchConflictError and nothing is lost: the device reloads, merges and sends
    again. Sending exactly what is already saved changes nothing, so a send whose
    answer was lost can be sent again.
    """

    with _LOG_LOCK:
        record = get_record(lot)
        if batch_recorded_at is not None and batch_recorded_at != record["recorded_at"]:
            raise BatchConflictError(
                f"Lot {record['lot']} is now a different batch (recorded {record['recorded_at']}); "
                "these amounts were weighed for an earlier one.",
                "BATCH_REPLACED",
            )
        lines = {row["line"]: row for row in record["planned_rows"]}
        saved = {row["line"]: row for row in record["actuals"]}
        cleaned = []
        for item in actuals:
            line = item.get("line")
            if line not in lines:
                raise BatchError(f"Line {line} is not on this batch.")
            unit = lines[line]["unit"]
            amount = _actual_amount(line, unit, _kept_grams(item, saved.get(line)))
            cleaned.append({"line": line, "material": lines[line]["material"], "unit": unit, **amount})
        cleaned.sort(key=lambda row: row["line"])
        clean_notes = str(notes or "").strip()[:4000]
        # Blank notes leave the saved notes as they are (see _fold).
        if cleaned == record["actuals"] and (not clean_notes or clean_notes == record.get("actual_notes", "")):
            return record
        if based_on is not None and based_on != record["actuals_version"]:
            raise BatchConflictError(
                f"The weighed amounts for lot {record['lot']} were saved from another device since these were loaded.",
                "BATCH_CHANGED",
            )
        _append_event(
            {
                "event": "ACTUALS_RECORDED",
                "lot": record["lot"],
                "actuals": cleaned,
                "notes": clean_notes,
                "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
        return get_record(record["lot"])


# ---------------------------------------------------------------------------
# Release gate rerun


def _run_gate_command(
    formula_file: Path, expected_ul: str, batch_volume_ml: str, audit_path: Path
) -> dict[str, Any]:
    """Run the release gate script read-only and return its JSON."""

    env = {**os.environ, "PERFUME_PIPELINE_AUDIT_PATH": str(audit_path)}
    completed = subprocess.run(  # noqa: S603 - fixed script, no shell
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--formula-file", str(formula_file),
            "--expected-concentrate-ul", expected_ul,
            "--batch-volume-ml", batch_volume_ml,
            "--brief", "auto",
            "--json",
            "--no-append-analysis",
            "--no-audit",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=GATE_TIMEOUT_SECONDS,
        check=False,
    )
    start = completed.stdout.find("{")
    if start < 0:
        tail = (completed.stderr or completed.stdout).strip()[-500:]
        raise BatchError(f"The gate gave no result (exit {completed.returncode}). {tail}")
    payload: dict[str, Any] = json.loads(completed.stdout[start:])
    return payload


def gate_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Overall status and every gate that is not PASS, in plain words."""

    formulas = payload.get("formulas") or [{}]
    first = formulas[0]
    not_pass = [
        {
            "gate": str(gate.get("gate", "")),
            "status": str(gate.get("status", "")),
            "detail": str(gate.get("detail") or gate.get("message") or ""),
        }
        for gate in first.get("gates") or []
        if str(gate.get("status", "")).upper() != "PASS"
    ]
    return {"status": str(first.get("status") or payload.get("overall") or "UNKNOWN"), "not_pass": not_pass}


def _execute_run(run_id: str, lot_dir: Path, formula_text: str, expected_ul: str, volume_ml: str) -> None:
    with _GATE_LOCK:
        _set_run(run_id, state="RUNNING")
        try:
            lot_dir.mkdir(parents=True, exist_ok=True)
            formula_file = lot_dir / "formula.md"
            formula_file.write_text(formula_text, encoding="utf-8")
            with tempfile.TemporaryDirectory(prefix="batch-gate-audit-") as scratch:
                payload = _run_gate_command(formula_file, expected_ul, volume_ml, Path(scratch) / "audit.jsonl")
            gate_json = lot_dir / "gate.json"
            gate_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            _set_run(run_id, state="FINISHED", gate_json_path=str(gate_json), **gate_summary(payload))
        except Exception as error:  # noqa: BLE001 - shown to the user as the run's result
            _set_run(run_id, state="FAILED", error=str(error)[:1000])


def _set_run(run_id: str, **changes: Any) -> None:
    with _RUNS_LOCK:
        _RUNS[run_id].update(changes, updated_at=datetime.now(UTC).isoformat(timespec="seconds"))


def start_gate_run(lot: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Start the gate on the scaled card in a background thread; poll its status."""

    lot = check_lot(lot)
    if plan["mixed_units"] or plan["units"] != ["uL"]:
        raise BatchError(
            "The batch gate rerun reads µL cards only for now; this card has mg rows."
        )
    formula_text = scaled_formula_text(plan["formula_name"], lot, plan)
    run_id = f"batch-gate-{uuid.uuid4().hex[:12]}"
    with _RUNS_LOCK:
        _RUNS[run_id] = {
            "run_id": run_id,
            "lot": lot,
            "state": "QUEUED",
            "status": None,
            "not_pass": [],
            "gate_json_path": None,
            "error": None,
            "parent_formula_compared": False,
            "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    thread = threading.Thread(
        target=_execute_run,
        args=(run_id, batch_dir() / lot, formula_text, plan["totals"]["planned_ul"], plan["finished_volume_ml"]),
        name=run_id,
        daemon=True,
    )
    thread.start()
    return gate_run_status(run_id)


def gate_run_status(run_id: str) -> dict[str, Any]:
    with _RUNS_LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            raise LookupError("No gate run with that id in this session.")
        return dict(run)
