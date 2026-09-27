"""Deterministic identity adjudication for governed scientific capabilities."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import yaml

from engine.calibration.hashing import (
    UTF8_TEXT_FILE_HASH_ALGORITHM,
    stable_utf8_text_file_hash,
)
from engine.dose_response import (
    MEASURED_INTENSITY_MANIFEST,
    corrected_wakayama_threshold_ng_l,
    measured_intensity_curve,
)

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WAKAYAMA_ADJUDICATION_RULES = (
    REPOSITORY_ROOT
    / "data"
    / "governance"
    / "wakayama_identity_adjudication_rules_v1.json"
)
_CAS_PATTERN = re.compile(r"^(\d{2,7})-(\d{2})-(\d)$")


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_label(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(character for character in text if character.isalnum())


def _valid_cas(value: str) -> bool:
    match = _CAS_PATTERN.fullmatch(value)
    if match is None:
        return False
    digits = match.group(1) + match.group(2)
    checksum = sum(
        int(digit) * multiplier
        for multiplier, digit in enumerate(reversed(digits), start=1)
    ) % 10
    return checksum == int(match.group(3))


def load_local_identity_index(
    material_directory: str | Path = REPOSITORY_ROOT / "data" / "materials",
) -> dict[str, Any]:
    """Read CAS/name facts without importing side-effectful data generators."""

    root = Path(material_directory)
    by_cas: dict[str, list[dict[str, Any]]] = defaultdict(list)
    file_hashes: list[dict[str, str]] = []
    for path in sorted(root.glob("*.yaml"), key=lambda item: item.name.casefold()):
        try:
            source_path = path.relative_to(REPOSITORY_ROOT).as_posix()
        except ValueError:
            source_path = path.relative_to(root).as_posix()
        file_hashes.append(
            {
                "path": source_path,
                "sha256": stable_utf8_text_file_hash(path),
            }
        )
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if loaded is None:
            continue
        if not isinstance(loaded, list):
            raise ValueError(f"material identity file is not a list: {path}")
        for row_number, row in enumerate(loaded, start=1):
            if not isinstance(row, Mapping):
                raise ValueError(f"material row is not an object: {path}:{row_number}")
            cas = str(row.get("cas") or "").strip()
            name = str(row.get("canonical_name") or "").strip()
            if not cas or not name:
                continue
            aliases = [str(value).strip() for value in row.get("aliases", []) if str(value).strip()]
            by_cas[cas].append(
                {
                    "canonical_name": name,
                    "aliases": aliases,
                    "source_path": source_path,
                    "source_row": row_number,
                    "cas_valid": _valid_cas(cas),
                }
            )
    manifest_contract = {
        "schema_version": "local-material-identity-index-v2",
        "file_hash_semantics": UTF8_TEXT_FILE_HASH_ALGORITHM,
        "files": file_hashes,
    }
    return {
        "schema_version": manifest_contract["schema_version"],
        "file_hash_semantics": manifest_contract["file_hash_semantics"],
        "by_cas": dict(by_cas),
        "file_manifest": file_hashes,
        "file_manifest_sha256": stable_payload_hash(manifest_contract),
    }


def adjudicate_wakayama_identities(
    *,
    manifest_path: str | Path = MEASURED_INTENSITY_MANIFEST,
    rules_path: str | Path = WAKAYAMA_ADJUDICATION_RULES,
    material_directory: str | Path = REPOSITORY_ROOT / "data" / "materials",
) -> dict[str, Any]:
    """Assign every source row exactly one conservative identity state.

    Exact chemical binding requires a valid CAS and an exact normalized local
    canonical name or admitted alias.  This binds a chemical identity only; it
    never binds a commercial product, stock lot, or formula row.
    """

    manifest_file = Path(manifest_path).resolve()
    rules_file = Path(rules_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    rules = json.loads(rules_file.read_text(encoding="utf-8"))
    if rules.get("source_manifest_id") != manifest.get("manifest_id"):
        raise ValueError("adjudication rules target a different source manifest")
    if any(bool(rules.get("action_authority", {}).get(key)) for key in FALSE_ACTION_AUTHORITY):
        raise ValueError("identity rules cannot grant action authority")

    source = manifest["source"]
    source_artifact = REPOSITORY_ROOT / source["source_artifact_path"]
    transcription = REPOSITORY_ROOT / source["transcription_artifact_path"]
    source_valid = _file_sha256(source_artifact) == source["source_artifact_sha256"]
    transcription_valid = (
        _file_sha256(transcription) == source["transcription_artifact_sha256"]
    )
    license_valid = bool(str(source.get("license", "")).strip())
    local = load_local_identity_index(material_directory)
    conflicts = {
        (str(row["source_cas"]), _normalized_label(row["source_name"])): row
        for row in rules.get("manual_conflicts", [])
    }
    manual_exact = {
        (str(row["source_cas"]), _normalized_label(row["source_name"])): row
        for row in rules.get("manual_exact_bindings", [])
    }

    rows: list[dict[str, Any]] = []
    with transcription.open("r", encoding="utf-8", newline="") as handle:
        for source_row, row in enumerate(csv.DictReader(handle, delimiter="\t"), start=2):
            cas = str(row["CAS"]).strip()
            name = str(row["Name"]).strip()
            normalized = _normalized_label(name)
            key = (cas, normalized)
            slope = float(row["D"])
            imax = float(row["I_max"])
            candidates = local["by_cas"].get(cas, [])
            exact_name_candidates = [
                candidate
                for candidate in candidates
                if normalized
                in {
                    _normalized_label(candidate["canonical_name"]),
                    *(_normalized_label(alias) for alias in candidate["aliases"]),
                }
            ]

            state: str
            reasons: list[str]
            material_id: str | None = None
            if not source_valid or not transcription_valid or not license_valid:
                state = "WITHHELD_LICENSE_OR_SOURCE"
                reasons = [
                    reason
                    for condition, reason in (
                        (source_valid, "SOURCE_ARTIFACT_HASH_MISMATCH"),
                        (transcription_valid, "TRANSCRIPTION_ARTIFACT_HASH_MISMATCH"),
                        (license_valid, "LICENSE_MISSING"),
                    )
                    if not condition
                ]
            elif key in conflicts:
                state = "CAS_NAME_CONFLICT"
                reasons = ["MANUALLY_REVIEWED_CAS_NAME_CONFLICT"]
            elif slope <= 0 or imax <= 0:
                state = "NOT_APPLICABLE"
                reasons = ["NONPOSITIVE_SOURCE_CURVE_PARAMETER"]
            elif key in manual_exact:
                state = "EXACT_IDENTITY_BOUND"
                reasons = ["MANUALLY_REVIEWED_EXACT_CHEMICAL_IDENTITY"]
                material_id = str(manual_exact[key]["material_id"])
            elif _valid_cas(cas) and exact_name_candidates:
                state = "EXACT_IDENTITY_BOUND"
                reasons = ["VALID_CAS_AND_EXACT_NORMALIZED_LOCAL_NAME_OR_ALIAS"]
                material_id = f"cas:{cas}"
            elif candidates:
                state = "PRODUCT_OR_GRADE_AMBIGUOUS"
                reasons = ["LOCAL_CAS_EXISTS_WITHOUT_EXACT_ADMITTED_NAME_BINDING"]
            else:
                state = "NO_LOCAL_IDENTITY"
                reasons = ["NO_LOCAL_CAS_IDENTITY"]

            threshold_roundtrip: dict[str, Any] | None = None
            if slope > 0 and imax > 1.4:
                threshold_ng_l = corrected_wakayama_threshold_ng_l(
                    imax=imax,
                    midpoint_log10_ug_l=float(row["C"]),
                    slope=slope,
                )
                response = measured_intensity_curve(
                    threshold_ng_l / 1000.0,
                    imax=imax,
                    midpoint_log10_ug_l=float(row["C"]),
                    slope=slope,
                )
                threshold_roundtrip = {
                    "threshold_ng_l_air": threshold_ng_l,
                    "threshold_ug_l_air": threshold_ng_l / 1000.0,
                    "forward_response": response,
                    "criterion": 1.4,
                    "passed": math_isclose(response, 1.4, absolute_tolerance=1e-12),
                }
            rows.append(
                {
                    "source_row": source_row,
                    "source_cas": cas,
                    "source_name": name,
                    "source_parameters": {
                        "imax": imax,
                        "midpoint_log10_ug_l": float(row["C"]),
                        "slope": slope,
                    },
                    "adjudication_state": state,
                    "reason_codes": reasons,
                    "canonical_material_id": material_id,
                    "local_candidates": candidates,
                    "stock_binding_authorized": False,
                    "observed_range_ug_l_air": None,
                    "threshold_roundtrip": threshold_roundtrip,
                }
            )

    if len(rows) != source["source_parameter_rows"]:
        raise ValueError("source row count does not match governed manifest")
    states = Counter(row["adjudication_state"] for row in rows)
    positive_curves = sum(
        row["source_parameters"]["slope"] > 0
        and row["source_parameters"]["imax"] > 0
        for row in rows
    )
    report_core = {
        "schema_version": "wakayama-identity-adjudication-report-v2",
        "manifest_id": manifest["manifest_id"],
        "source_manifest_sha256": _file_sha256(manifest_file),
        "rules_sha256": _file_sha256(rules_file),
        "local_identity_manifest_schema_version": local["schema_version"],
        "local_identity_hash_semantics": local["file_hash_semantics"],
        "local_identity_manifest_sha256": local["file_manifest_sha256"],
        "source_artifact_verified": source_valid,
        "transcription_artifact_verified": transcription_valid,
        "license_present": license_valid,
        "source_row_count": len(rows),
        "positive_curve_count": positive_curves,
        "state_counts": dict(sorted(states.items())),
        "rows": rows,
        "exact_stock_binding_count": 0,
        "observed_range_bound_count": 0,
        "capability_admission_state": "HOLD_EXACT_STOCK_RANGE_MATRIX_BINDING",
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report_core, "report_sha256": stable_payload_hash(report_core)}


def math_isclose(value: float, target: float, *, absolute_tolerance: float) -> bool:
    """Small local helper keeps the adjudication result JSON deterministic."""

    return abs(value - target) <= absolute_tolerance


__all__ = [
    "WAKAYAMA_ADJUDICATION_RULES",
    "adjudicate_wakayama_identities",
    "load_local_identity_index",
]
