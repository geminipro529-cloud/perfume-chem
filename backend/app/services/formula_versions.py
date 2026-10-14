"""Saved versions of formulas from the Edit a formula page.

Every save appends a version to a hash-chained JSONL log in data/user (Kenny's
own folder, never in the repository), beside the stock prices and batch records.
A version is never changed: saving again makes the next version, and saving
content identical to an existing version returns that version.

A version holds the editor's rows exactly (each amount as a fraction "n" or
"n/d": µL of the stock for a liquid, mg for a solid) and the card table the
bench sheet and the Batch page read. A version is locked once a batch is made
from it: a batch record whose card hash is this version's card hash. Lab bottles
are tied to a version by Kenny, and untied if he tied the wrong one.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.config import PROJECT_ROOT

VERSION_LOG_PATH_ENV = "PERFUME_FORMULA_VERSION_PATH"
DEFAULT_VERSION_LOG_PATH = PROJECT_ROOT / "data" / "user" / "user_formula_versions.jsonl"
SCHEMA_VERSION = "workbench-formula-versions-v1"
_AMOUNT = re.compile(r"^[1-9]\d{0,29}(/[1-9]\d{0,29})?$")
_FORMULA_ID = re.compile(r"^[0-9a-f]{32}$")
_NOTES = ("", "top", "heart", "base")
_LOG_LOCK = threading.Lock()

_Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
_Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class FormulaVersionError(ValueError):
    """A save or a bottle tie that can't be recorded; the message says why."""


class SavedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: _Name
    stock_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    fraction: _Short = ""
    basis: _Short = ""
    carrier: _Short | None = None
    solid: bool = False
    # An exact fraction: "600" or "1000/3".
    amount: str
    note: str = ""

    @field_validator("amount")
    @classmethod
    def _exact(cls, value: str) -> str:
        if not _AMOUNT.match(value):
            raise ValueError("amount must be a whole number or a fraction such as 1000/3, above 0")
        return value

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        if value not in _NOTES:
            raise ValueError("note must be top, heart, base or empty")
        return value


class FormulaVersionSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Left out for a formula's first save; the server gives it an id.
    formula_id: str | None = None
    # The version the editor started from, when there was one.
    parent_version: int | None = Field(default=None, ge=1)
    name: _Name
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    bottle_ml: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] = ""
    rows: list[SavedRow] = Field(min_length=1, max_length=400)
    # The card table as the bench sheet and the Batch page read it.
    card_text: Annotated[str, StringConstraints(min_length=1, max_length=200_000)]


class BottleTie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bottle_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    tied: bool = True


def version_log_path() -> Path:
    override = os.environ.get(VERSION_LOG_PATH_ENV, "").strip()
    return Path(override).resolve() if override else DEFAULT_VERSION_LOG_PATH


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    previous = None
    for number, line in enumerate(path.read_bytes().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise FormulaVersionError(f"The formula version log is broken at line {number}; it was edited by hand.") from error
        if event.get("previous_line_sha256") != previous:
            raise FormulaVersionError(f"The formula version log is broken at line {number}; it was edited by hand.")
        previous = hashlib.sha256(line).hexdigest()
        events.append(event)
    return events


def _append(path: Path, event: dict[str, Any], previous: str | None) -> dict[str, Any]:
    stamped = {**event, "previous_line_sha256": previous}
    line = json.dumps(stamped, ensure_ascii=False, sort_keys=True).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as handle:
        handle.write(line + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return stamped


def _last_line_sha(path: Path) -> str | None:
    if not path.exists():
        return None
    lines = [line for line in path.read_bytes().splitlines() if line.strip()]
    return hashlib.sha256(lines[-1]).hexdigest() if lines else None


def _fold(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """formula_id -> {name, versions: {number: version with its bottle ties}}."""
    formulas: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event"] == "VERSION_SAVED":
            version = event["version"]
            formula = formulas.setdefault(version["formula_id"], {"formula_id": version["formula_id"], "versions": {}})
            formula["name"] = version["name"]
            formula["versions"][version["version"]] = {**version, "bottles": {}}
        elif event["event"] in ("BOTTLE_TIED", "BOTTLE_UNTIED"):
            version = formulas.get(event["formula_id"], {}).get("versions", {}).get(event["version"])
            if version is None:
                continue
            if event["event"] == "BOTTLE_TIED":
                version["bottles"][event["bottle_id"]] = {"bottle_id": event["bottle_id"], "label": event["label"], "tied_at": event["at"]}
            else:
                version["bottles"].pop(event["bottle_id"], None)
    return formulas


def _content_sha256(name: str, rows: list[dict[str, Any]], bottle_ml: str) -> str:
    canonical = json.dumps({"name": name, "rows": rows, "bottle_ml": bottle_ml}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _batches_by_card() -> dict[str, list[str]]:
    """Card hash -> lots made from it, from the Batch page's records."""
    from app.services.batch_production import BatchError, list_records

    lots: dict[str, list[str]] = {}
    try:
        records = list_records()
    except (BatchError, json.JSONDecodeError) as error:
        # Without the batch records no version can be shown as unlocked safely.
        raise FormulaVersionError(f"The Batch page's records can't be read, so locks can't be checked: {error}") from error
    for record in records:
        lots.setdefault(str(record.get("source_sha256") or ""), []).append(str(record["lot"]))
    return lots


def _public(version: dict[str, Any], lots: dict[str, list[str]], *, full: bool) -> dict[str, Any]:
    locked_by = sorted(lots.get(version["card_sha256"], []))
    keys = ("formula_id", "version", "name", "parent_version", "note", "saved_at", "bottle_ml", "card_sha256", "content_sha256")
    out: dict[str, Any] = {key: version[key] for key in keys}
    out["locked"] = bool(locked_by)
    out["locked_by"] = locked_by
    out["bottles"] = sorted(version["bottles"].values(), key=lambda bottle: bottle["tied_at"])
    out["row_count"] = len(version["rows"])
    if full:
        out["rows"] = version["rows"]
        out["card_text"] = version["card_text"]
    return out


def list_formulas() -> dict[str, Any]:
    formulas = _fold(_read_events(version_log_path()))
    lots = _batches_by_card()
    listed = []
    for formula in formulas.values():
        versions = [_public(formula["versions"][n], lots, full=False) for n in sorted(formula["versions"])]
        listed.append({"formula_id": formula["formula_id"], "name": formula["name"], "latest": versions[-1]["version"],
                       "updated_at": versions[-1]["saved_at"], "versions": versions})
    listed.sort(key=lambda formula: formula["updated_at"], reverse=True)
    return {"schema_version": SCHEMA_VERSION, "formulas": listed, "inventory_modified": False, "compounding_authority": False}


def get_version(formula_id: str, number: int) -> dict[str, Any]:
    formula = _fold(_read_events(version_log_path())).get(formula_id)
    version = (formula or {}).get("versions", {}).get(number)
    if version is None:
        raise LookupError("No saved version with that number.")
    return {"schema_version": SCHEMA_VERSION, **_public(version, _batches_by_card(), full=True)}


def save_version(request: FormulaVersionSave) -> tuple[dict[str, Any], bool]:
    """Append the next version, or return the existing one with the same content. (record, created)"""
    rows = [row.model_dump() for row in request.rows]
    content = _content_sha256(request.name, rows, request.bottle_ml)
    path = version_log_path()
    with _LOG_LOCK:
        events = _read_events(path)
        formulas = _fold(events)
        if request.formula_id is None:
            formula_id = uuid.uuid4().hex
            versions: dict[int, dict[str, Any]] = {}
            if request.parent_version is not None:
                raise FormulaVersionError("A new formula has no version to start from.")
        else:
            formula_id = request.formula_id
            if not _FORMULA_ID.match(formula_id) or formula_id not in formulas:
                raise LookupError("No saved formula with that id.")
            versions = formulas[formula_id]["versions"]
            if request.parent_version is not None and request.parent_version not in versions:
                raise FormulaVersionError(f"Version {request.parent_version} of this formula was not found.")
            same = next((v for v in versions.values() if v["content_sha256"] == content), None)
            if same is not None:
                return get_version(formula_id, same["version"]), False
        number = max(versions, default=0) + 1
        version = {
            "formula_id": formula_id,
            "version": number,
            "name": request.name,
            "parent_version": request.parent_version,
            "note": request.note,
            "saved_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "bottle_ml": request.bottle_ml,
            "rows": rows,
            "card_text": request.card_text,
            "card_sha256": hashlib.sha256(request.card_text.encode("utf-8")).hexdigest(),
            "content_sha256": content,
        }
        _append(path, {"event": "VERSION_SAVED", "version": version}, _last_line_sha(path))
    return get_version(formula_id, number), True


def tie_bottle(formula_id: str, number: int, bottle_id: str, label: str, tied: bool) -> dict[str, Any]:
    """Tie a Lab bottle to a version (made from it), or untie it."""
    path = version_log_path()
    with _LOG_LOCK:
        formulas = _fold(_read_events(path))
        version = formulas.get(formula_id, {}).get("versions", {}).get(number)
        if version is None:
            raise LookupError("No saved version with that number.")
        if tied:
            for other in formulas.values():
                for saved in other["versions"].values():
                    if bottle_id in saved["bottles"] and saved is not version:
                        raise FormulaVersionError(
                            f"That bottle is tied to {other['name']} version {saved['version']}; untie it there first."
                        )
        elif bottle_id not in version["bottles"]:
            raise FormulaVersionError("That bottle is not tied to this version.")
        if not tied or bottle_id not in version["bottles"]:
            _append(path, {
                "event": "BOTTLE_TIED" if tied else "BOTTLE_UNTIED",
                "formula_id": formula_id,
                "version": number,
                "bottle_id": bottle_id,
                "label": label,
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
            }, _last_line_sha(path))
    return get_version(formula_id, number)
