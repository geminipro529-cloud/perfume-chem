"""Blind tests on the Your nose page: two saved formula versions as vials A and B.

Kenny picks two versions saved on the Edit a formula page. The server decides at
random which one is vial A, shows both vials' rows for mixing, and keeps the key
(which version is which) out of the page until he reveals it. Each strip time
gets one pick, A, B or no preference, and a 1 to 5 score for how much each vial
smells like its name. A pick can be changed until the reveal; after it, the test
is fixed.

Tests live in Kenny's own data/user folder as a hash-chained JSONL log, like the
formula versions; nothing here touches a card, the Lab database or stock.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.config import PROJECT_ROOT
from app.services import formula_versions

BLIND_TEST_PATH_ENV = "PERFUME_BLIND_TEST_PATH"
DEFAULT_BLIND_TEST_PATH = PROJECT_ROOT / "data" / "user" / "user_blind_tests.jsonl"
SCHEMA_VERSION = "workbench-blind-tests-v1"
# The strip times of the first blind test (app-review BLIND_TEST.md): 5 min, 1 h, 4 h.
TIMES = ("5 min", "1 h", "4 h")
_TEST_ID = re.compile(r"^[0-9a-f]{32}$")
_LOG_LOCK = threading.Lock()

_Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
_Label = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class BlindTestError(ValueError):
    """A blind test or pick that can't be recorded; the message says why."""


class BlindSide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
    version: int = Field(ge=1)
    # What this side is ("Composer", "Opus card"); hidden until the reveal.
    label: _Label = ""


class BlindTestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: _Title
    brief: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    first: BlindSide
    second: BlindSide


class BlindPick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: Literal["5 min", "1 h", "4 h"]
    choice: Literal["A", "B", "same"]
    name_a: int | None = Field(default=None, ge=1, le=5)
    name_b: int | None = Field(default=None, ge=1, le=5)
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=280)] = ""


def blind_test_path() -> Path:
    override = os.environ.get(BLIND_TEST_PATH_ENV, "").strip()
    return Path(override).resolve() if override else DEFAULT_BLIND_TEST_PATH


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
            raise BlindTestError(f"The blind test log is broken at line {number}; it was edited by hand.") from error
        if event.get("previous_line_sha256") != previous:
            raise BlindTestError(f"The blind test log is broken at line {number}; it was edited by hand.")
        previous = hashlib.sha256(line).hexdigest()
        events.append(event)
    return events


def _append(path: Path, event: dict[str, Any], events: list[dict[str, Any]]) -> None:
    previous = None
    if events:
        lines = [line for line in path.read_bytes().splitlines() if line.strip()]
        previous = hashlib.sha256(lines[-1]).hexdigest()
    line = json.dumps({**event, "previous_line_sha256": previous}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as handle:
        handle.write(line + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _fold(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """test_id -> the test with its latest pick per time and its reveal."""
    tests: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event"] == "BLIND_TEST_CREATED":
            test = event["test"]
            tests[test["test_id"]] = {**test, "picks": {}, "revealed_at": None}
        elif event["event"] == "PICK_RECORDED" and event["test_id"] in tests:
            tests[event["test_id"]]["picks"][event["pick"]["time"]] = {**event["pick"], "at": event["at"]}
        elif event["event"] == "REVEALED" and event["test_id"] in tests:
            tests[event["test_id"]]["revealed_at"] = event["at"]
    return tests


def _preferred(pick: dict[str, Any], key: dict[str, Any]) -> str | None:
    return None if pick["choice"] == "same" else key[pick["choice"]]["label"]


def _public(test: dict[str, Any]) -> dict[str, Any]:
    revealed = test["revealed_at"] is not None
    picks = [test["picks"][time] for time in test["times"] if time in test["picks"]]
    out: dict[str, Any] = {
        "test_id": test["test_id"],
        "title": test["title"],
        "brief": test["brief"],
        "created_at": test["created_at"],
        "times": test["times"],
        "vials": [{"letter": letter, "rows": test["vials"][letter]} for letter in ("A", "B")],
        "picks": picks,
        "revealed": revealed,
        "revealed_at": test["revealed_at"],
        # The key leaves the server only after the reveal.
        "key": None,
        "outcome": None,
    }
    if revealed:
        key = test["key"]
        out["key"] = key
        out["outcome"] = [{"time": pick["time"], "preferred": _preferred(pick, key)} for pick in picks]
    return out


def _tally(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per label over revealed tests: picks it was in, picks it won, and its mean name score."""
    by_label: dict[str, dict[str, Any]] = {}
    for test in tests:
        if test["revealed_at"] is None:
            continue
        for pick in test["picks"].values():
            for letter in ("A", "B"):
                label = test["key"][letter]["label"]
                row = by_label.setdefault(label.casefold(), {"label": label, "picks": 0, "preferred": 0, "names": []})
                row["picks"] += 1
                row["preferred"] += int(pick["choice"] == letter)
                score = pick["name_a" if letter == "A" else "name_b"]
                if score is not None:
                    row["names"].append(score)
    return [
        {
            "label": row["label"],
            "picks": row["picks"],
            "preferred": row["preferred"],
            "name_mean": round(sum(row["names"]) / len(row["names"]), 1) if row["names"] else None,
        }
        for row in sorted(by_label.values(), key=lambda row: (-row["preferred"], row["label"]))
    ]


def list_tests() -> dict[str, Any]:
    tests = list(_fold(_read_events(blind_test_path())).values())
    tests.sort(key=lambda test: test["created_at"], reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "times": list(TIMES),
        "tests": [_public(test) for test in tests],
        "tally": _tally(tests),
        "inventory_modified": False,
    }


def _side(side: BlindSide) -> tuple[dict[str, Any], dict[str, Any]]:
    """(rows, key entry) for one side, from the saved formula version."""
    version = formula_versions.get_version(side.formula_id, side.version)
    label = side.label or f"{version['name']} v{side.version}"
    key = {"formula_id": side.formula_id, "version": side.version, "name": version["name"], "label": label}
    return {"rows": version["rows"], "content_sha256": version["content_sha256"]}, key


def create_test(request: BlindTestCreate) -> dict[str, Any]:
    first, first_key = _side(request.first)
    second, second_key = _side(request.second)
    if first["content_sha256"] == second["content_sha256"]:
        raise BlindTestError("Both sides are the same formula; pick two different versions.")
    if first_key["label"].casefold() == second_key["label"].casefold():
        raise BlindTestError("Give the two sides different names, so the reveal can tell them apart.")
    sides = [(first["rows"], first_key), (second["rows"], second_key)]
    if secrets.randbelow(2):
        sides.reverse()
    test = {
        "test_id": uuid.uuid4().hex,
        "title": request.title,
        "brief": request.brief,
        "created_at": _now(),
        "times": list(TIMES),
        "vials": {"A": sides[0][0], "B": sides[1][0]},
        "key": {"A": sides[0][1], "B": sides[1][1]},
    }
    path = blind_test_path()
    with _LOG_LOCK:
        events = _read_events(path)
        _append(path, {"event": "BLIND_TEST_CREATED", "test": test}, events)
    return _public({**test, "picks": {}, "revealed_at": None})


def _open_test(events: list[dict[str, Any]], test_id: str) -> dict[str, Any]:
    test = _fold(events).get(test_id) if _TEST_ID.match(test_id) else None
    if test is None:
        raise LookupError("No blind test with that id.")
    return test


def record_pick(test_id: str, pick: BlindPick) -> dict[str, Any]:
    path = blind_test_path()
    with _LOG_LOCK:
        events = _read_events(path)
        test = _open_test(events, test_id)
        if test["revealed_at"] is not None:
            raise BlindTestError("This test is revealed, so its picks are fixed.")
        _append(path, {"event": "PICK_RECORDED", "test_id": test_id, "pick": pick.model_dump(), "at": _now()}, events)
        return _public(_open_test(_read_events(path), test_id))


def reveal(test_id: str) -> dict[str, Any]:
    path = blind_test_path()
    with _LOG_LOCK:
        events = _read_events(path)
        test = _open_test(events, test_id)
        if test["revealed_at"] is None:
            if not test["picks"]:
                raise BlindTestError("Pick at least one strip time before revealing which vial is which.")
            _append(path, {"event": "REVEALED", "test_id": test_id, "at": _now()}, events)
        return _public(_open_test(_read_events(path), test_id))
