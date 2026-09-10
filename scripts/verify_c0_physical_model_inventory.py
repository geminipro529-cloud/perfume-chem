#!/usr/bin/env python3
"""Verify Build C0 physical-model inventory and frozen legacy behavior.

This verifier is intentionally read-only. It validates metadata against the
checked-out source and replays explicit legacy fixtures, but it never writes or
promotes a physical-model result.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_CLASSIFICATIONS = {
    "EXACT_PHYSICAL_ARITHMETIC",
    "MEASURED_LOOKUP",
    "EMPIRICALLY_CALIBRATED_MODEL",
    "LITERATURE_DERIVED_MODEL",
    "HEURISTIC",
    "STUB",
    "DISCONNECTED_LEGACY",
    "UNSUPPORTED",
}

REQUIRED_CATEGORIES = {
    "formula_state_headspace",
    "temporal_simulator_trajectory",
    "thermo_headspace",
    "vapor_pressure_estimation",
    "antoine_clausius_clapeyron_dippr",
    "activity_coefficients",
    "unifac",
    "hansen_solubility_distance",
    "cosmo_rs",
    "dose_response_psychophysics",
    "natural_material_decomposition",
    "maturation_aging_kinetics",
    "receptor_models",
    "adaptation",
    "hedonic_longevity_sillage_diffusion_projection",
}

REQUIRED_RECORD_FIELDS = {
    "id",
    "category",
    "name",
    "classification",
    "source",
    "inputs",
    "outputs",
    "conditions",
    "consumers",
    "evidence_labels",
    "tests",
    "claim_impact",
    "runtime_status",
    "disposition",
    "source_sha256",
}

REQUIRED_ADR_STATEMENTS = (
    "engine.physics",
    "one selected implementation",
    "Build B selected assertions",
    "Laboratory Beta",
    "WITHHELD",
    "C0 changes no production runtime path",
    "LEGACY_HEURISTIC",
)

# A successor record is the only sanctioned way to move a frozen C0 pin
# forward. It never edits the frozen store: it is anchored to the exact value
# it supersedes, and it must carry the commit, reason, evidence file and
# approving authority that justify the change.
SUCCESSOR_SCHEMA_VERSION = "c0-pin-successors-v1"
SUCCESSOR_KINDS = frozenset({"eol_only", "committed_revision", "owner_rebaseline"})
SUCCESSOR_FIELDS = frozenset(
    {
        "record_id",
        "target",
        "superseded_sha256",
        "successor_sha256",
        "kind",
        "commit",
        "reason",
        "evidence",
        "approved_by",
        "approved_at",
    }
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def canonical_json_bytes(payload: Any, *, trailing_newline: bool = False) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashes and fixture locks."""

    text = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    if trailing_newline:
        text += "\n"
    return text.encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def load_inventory(path: str | Path) -> dict[str, Any]:
    return _load_json(Path(path))


def load_legacy_fixtures(path: str | Path) -> dict[str, Any]:
    return _load_json(Path(path))


def _repo_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"Path escapes repository root: {relative}")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _lf_sha256_file(path: Path) -> str:
    """Hash the LF representation of the file, independent of checkout EOL."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _crlf_sha256_file(path: Path) -> str:
    """Hash the CRLF materialisation of the file's LF representation."""
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return hashlib.sha256(data).hexdigest()


def _nonblank(value: Any, field: str) -> str:
    text = value if isinstance(value, str) else ""
    if not text.strip():
        raise ValueError(f"successor {field} must be a non-empty string")
    return text.strip()


def load_pin_successors(path: str | Path, *, root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Load the optional anchored successor overlay for a frozen pin store.

    Returns an empty list when the overlay file does not exist. Raises
    ValueError when the overlay is malformed, so the caller refuses to load it
    rather than silently accepting an unanchored re-bind.
    """
    overlay_path = Path(path)
    if not overlay_path.is_file():
        return []
    payload = _load_json(overlay_path)
    if set(payload) != {"schema_version", "successors"}:
        raise ValueError("successor overlay keys are closed")
    if payload["schema_version"] != SUCCESSOR_SCHEMA_VERSION:
        raise ValueError(f"successor overlay schema_version must be {SUCCESSOR_SCHEMA_VERSION}")
    records = payload["successors"]
    if not isinstance(records, list) or not records:
        raise ValueError("successor overlay must carry a nonempty successors list")
    loaded: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != SUCCESSOR_FIELDS:
            raise ValueError("successor record keys are closed")
        record_id = _nonblank(record["record_id"], "record_id")
        target = _nonblank(record["target"], "target")
        key = (record_id, target)
        if key in seen:
            raise ValueError("successor overlay must not repeat a (record_id, target)")
        seen.add(key)
        superseded = _nonblank(record["superseded_sha256"], "superseded_sha256")
        successor = _nonblank(record["successor_sha256"], "successor_sha256")
        for digest in (superseded, successor):
            if not _SHA256.fullmatch(digest):
                raise ValueError("successor digests must be sha256 hex digests")
        if superseded == successor:
            raise ValueError("successor must change the pin")
        kind = _nonblank(record["kind"], "kind")
        if kind not in SUCCESSOR_KINDS:
            raise ValueError(f"unknown successor kind {kind!r}")
        if not _COMMIT_SHA.fullmatch(_nonblank(record["commit"], "commit")):
            raise ValueError("successor commit must be a full commit sha")
        _nonblank(record["reason"], "reason")
        _nonblank(record["approved_by"], "approved_by")
        _nonblank(record["approved_at"], "approved_at")
        evidence = _repo_path(root, _nonblank(record["evidence"], "evidence"))
        if not evidence.is_file():
            raise ValueError("successor evidence must be an existing file")
        loaded.append(dict(record))
    return loaded


def bind_pin_successors(
    records: Sequence[Mapping[str, Any]],
    stored_pins: Mapping[tuple[str, str], str],
    *,
    root: Path,
    label: str,
) -> tuple[dict[tuple[str, str], str], list[str]]:
    """Anchor-check successors against the stored pins and return the re-binds.

    Every record must name an existing (record_id, target) pin and carry the
    exact stored digest as its anchor. An eol_only successor additionally has
    to prove that the superseded digest is the CRLF materialisation of the
    current LF bytes, and every successor must equal the current LF digest
    (never a CRLF preference).
    """
    records = list(records)
    errors: list[str] = []
    bound: dict[tuple[str, str], str] = {}
    for record in records:
        key = (str(record["record_id"]), str(record["target"]))
        prefix = f"successor {key[0]}:{key[1]}"
        stored = stored_pins.get(key)
        if stored is None:
            errors.append(f"{prefix}: targets a pin that is not declared in {label}")
            continue
        if stored != record["superseded_sha256"]:
            errors.append(f"{prefix}: anchor does not match the stored pin")
            continue
        successor = str(record["successor_sha256"])
        try:
            path = _repo_path(root, key[1])
        except ValueError as exc:
            errors.append(f"{prefix}: {exc}")
            continue
        if not path.is_file():
            errors.append(f"{prefix}: source file is missing")
            continue
        actual_lf = _lf_sha256_file(path)
        if actual_lf != successor:
            errors.append(
                f"{prefix}: successor is stale: expected {successor}, actual {actual_lf}"
            )
            continue
        if record["kind"] == "eol_only" and _crlf_sha256_file(path) != record["superseded_sha256"]:
            errors.append(
                f"{prefix}: eol_only successor is not provable: the superseded digest "
                "is not the CRLF materialisation of the current LF bytes"
            )
            continue
        bound[key] = successor
    return bound, errors


def _python_symbols(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols[node.name] = node.lineno
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols[f"{node.name}.{child.name}"] = child.lineno
    return symbols


def _validate_absence_query(
    record: Mapping[str, Any],
    *,
    root: Path,
) -> list[str]:
    query = record.get("absence_query")
    if not isinstance(query, Mapping):
        return [f"{record.get('id')}: unsupported/absent record needs absence_query"]
    try:
        pattern = re.compile(str(query["pattern"]))
    except (KeyError, re.error) as exc:
        return [f"{record.get('id')}: invalid absence query: {exc}"]
    extensions = {str(item) for item in query.get("extensions", [".py"])}
    excluded_paths = {str(item).replace("\\", "/") for item in query.get("exclude_paths", [])}
    matches: list[str] = []
    for root_name in query.get("roots", []):
        try:
            query_root = _repo_path(root, str(root_name))
        except ValueError as exc:
            matches.append(str(exc))
            continue
        if not query_root.exists():
            matches.append(f"missing query root {root_name}")
            continue
        for path in sorted(query_root.rglob("*")):
            if not path.is_file() or path.suffix not in extensions:
                continue
            relative_path = path.relative_to(root).as_posix()
            if relative_path in excluded_paths:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if pattern.search(text):
                matches.append(relative_path)
    if matches:
        return [f"{record.get('id')}: absence query matched {', '.join(matches)}"]
    return []


def validate_inventory(
    inventory: Mapping[str, Any],
    *,
    root: Path = REPO_ROOT,
    adr_path: str | Path | None = None,
    successors: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Return all fail-closed inventory errors without mutating the repository."""

    errors: list[str] = []
    if inventory.get("schema_version") != "c0-physical-model-inventory-v1":
        errors.append("inventory schema_version must be c0-physical-model-inventory-v1")
    if set(inventory.get("required_categories", [])) != REQUIRED_CATEGORIES:
        errors.append("required_categories does not exactly match the C0 contract")
    if set(inventory.get("allowed_classifications", [])) != ALLOWED_CLASSIFICATIONS:
        errors.append("allowed_classifications does not exactly match the C0 vocabulary")
    if inventory.get("canonical_decision", {}).get("c0_runtime_changes") is not False:
        errors.append("canonical_decision must declare c0_runtime_changes=false")

    records = inventory.get("implementations")
    if not isinstance(records, list) or not records:
        return errors + ["implementations must be a non-empty list"]

    stored_pins: dict[tuple[str, str], str] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        record_id = str(record.get("id", "<missing-id>"))
        source_hashes = record.get("source_sha256")
        if isinstance(source_hashes, Mapping):
            for relative, digest in source_hashes.items():
                stored_pins[(record_id, str(relative))] = str(digest)
    if successors is None:
        try:
            successors = load_pin_successors(
                root / "docs" / "verification" / "c0" / "physical_model_inventory_successors.json",
                root=root,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load successor overlay: {exc}")
            successors = []
    rebound, bind_errors = bind_pin_successors(
        successors, stored_pins, root=root, label="the C0 inventory"
    )
    errors.extend(bind_errors)

    identifiers: set[str] = set()
    represented: set[str] = set()
    symbol_cache: dict[Path, dict[str, int]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            errors.append("implementation record is not an object")
            continue
        record_id = str(record.get("id", "<missing-id>"))
        missing_fields = sorted(REQUIRED_RECORD_FIELDS - set(record))
        if missing_fields:
            errors.append(f"{record_id}: missing fields {', '.join(missing_fields)}")
        if record_id in identifiers:
            errors.append(f"{record_id}: duplicate implementation id")
        identifiers.add(record_id)

        category = str(record.get("category", ""))
        represented.add(category)
        if category not in REQUIRED_CATEGORIES:
            errors.append(f"{record_id}: unknown category {category!r}")
        classification = str(record.get("classification", ""))
        if classification not in ALLOWED_CLASSIFICATIONS:
            errors.append(f"{record_id}: unknown classification {classification!r}")
        for text_field in ("name", "claim_impact", "runtime_status", "disposition"):
            if not str(record.get(text_field, "")).strip():
                errors.append(f"{record_id}: {text_field} must be non-empty")
        for list_field in (
            "source",
            "inputs",
            "outputs",
            "conditions",
            "consumers",
            "evidence_labels",
            "tests",
        ):
            if not isinstance(record.get(list_field), list):
                errors.append(f"{record_id}: {list_field} must be a list")

        source_entries = record.get("source", [])
        source_hashes = record.get("source_sha256", {})
        if not isinstance(source_hashes, Mapping):
            errors.append(f"{record_id}: source_sha256 must be an object")
            source_hashes = {}
        source_paths: set[str] = set()
        for source in source_entries if isinstance(source_entries, list) else []:
            if not isinstance(source, Mapping):
                errors.append(f"{record_id}: source entry must be an object")
                continue
            relative = str(source.get("path", ""))
            symbol = str(source.get("symbol", ""))
            if not relative or not symbol:
                errors.append(f"{record_id}: source path and symbol are required")
                continue
            source_paths.add(relative)
            try:
                path = _repo_path(root, relative)
            except ValueError as exc:
                errors.append(f"{record_id}: {exc}")
                continue
            if not path.is_file():
                errors.append(f"{record_id}: missing source file {relative}")
                continue
            expected_hash = str(source_hashes.get(relative, ""))
            successor = rebound.get((record_id, relative))
            if successor is not None:
                actual_hash = _lf_sha256_file(path)
                if actual_hash != successor:
                    errors.append(
                        f"{record_id}: successor is stale for {relative}: "
                        f"expected {successor}, actual {actual_hash}"
                    )
            else:
                actual_hash = _sha256_file(path)
                if expected_hash != actual_hash:
                    errors.append(
                        f"{record_id}: stale source hash for {relative}: "
                        f"expected {expected_hash or '<missing>'}, actual {actual_hash}"
                    )
            if path.suffix == ".py":
                try:
                    symbols = symbol_cache.setdefault(path, _python_symbols(path))
                except (OSError, SyntaxError) as exc:
                    errors.append(f"{record_id}: cannot parse {relative}: {exc}")
                    continue
                if symbol not in symbols:
                    errors.append(f"{record_id}: symbol {symbol!r} missing from {relative}")
                declared_line = source.get("line")
                if symbol in symbols and declared_line != symbols[symbol]:
                    errors.append(
                        f"{record_id}: {relative}:{symbol} line is {symbols[symbol]}, "
                        f"inventory declares {declared_line}"
                    )
        if set(source_hashes) != source_paths:
            errors.append(f"{record_id}: source_sha256 keys must exactly match source paths")
        if not source_entries:
            if classification != "UNSUPPORTED":
                errors.append(f"{record_id}: source-free record must be UNSUPPORTED")
            errors.extend(_validate_absence_query(record, root=root))

        for test_name in record.get("tests", []) if isinstance(record.get("tests"), list) else []:
            try:
                test_path = _repo_path(root, str(test_name))
            except ValueError as exc:
                errors.append(f"{record_id}: {exc}")
                continue
            if not test_path.is_file():
                errors.append(f"{record_id}: missing recorded test {test_name}")

    missing_categories = sorted(REQUIRED_CATEGORIES - represented)
    if missing_categories:
        errors.append(f"unrepresented C0 categories: {', '.join(missing_categories)}")

    edges = inventory.get("call_edges")
    if not isinstance(edges, list) or not edges:
        errors.append("call_edges must be a non-empty list")
    else:
        for index, edge in enumerate(edges):
            prefix = f"call_edges[{index}]"
            if not isinstance(edge, Mapping):
                errors.append(f"{prefix}: edge must be an object")
                continue
            if edge.get("callee_id") not in identifiers:
                errors.append(f"{prefix}: dangling callee_id {edge.get('callee_id')!r}")
            if not str(edge.get("caller", "")).strip() or not str(edge.get("kind", "")).strip():
                errors.append(f"{prefix}: caller and kind are required")
            evidence = edge.get("evidence")
            if not isinstance(evidence, Mapping):
                errors.append(f"{prefix}: evidence object is required")
                continue
            relative = str(evidence.get("path", ""))
            token = str(evidence.get("token", ""))
            line_number = evidence.get("line")
            try:
                path = _repo_path(root, relative)
                lines = path.read_text(encoding="utf-8").splitlines()
                if not isinstance(line_number, int) or line_number < 1 or line_number > len(lines):
                    errors.append(f"{prefix}: invalid evidence line {relative}:{line_number}")
                elif token not in lines[line_number - 1]:
                    errors.append(f"{prefix}: token {token!r} absent at {relative}:{line_number}")
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(f"{prefix}: invalid evidence path: {exc}")

    if adr_path is not None:
        adr = Path(adr_path)
        if not adr.is_file():
            errors.append(f"missing consolidation ADR: {adr}")
        else:
            text = adr.read_text(encoding="utf-8")
            for statement in REQUIRED_ADR_STATEMENTS:
                if statement not in text:
                    errors.append(f"ADR missing required statement: {statement}")
    return errors


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if hasattr(value, "tolist"):
        return _normalize(value.tolist())
    if hasattr(value, "__dataclass_fields__"):
        return {key: _normalize(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    raise TypeError(f"Unsupported legacy fixture output type: {type(value).__name__}")


LegacyCapture = Callable[[Mapping[str, Any]], Any]


def _tuples_by_name(values: Mapping[str, Sequence[float]] | None) -> dict[str, tuple[float, ...]]:
    return {str(name): tuple(float(item) for item in row) for name, row in (values or {}).items()}


def _capture_formula_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    from engine.pipeline.formula_state import build_formula_state

    build_formula_state.cache_clear()
    state = build_formula_state(
        payload["ingredients_ul"],
        payload.get("dilutions"),
        batch_volume_ml=float(payload.get("batch_volume_ml", 30.0)),
        temperature_K=float(payload.get("temperature_K", 305.0)),
        context=str(payload.get("context", "skin")),
        matrix_moles=payload.get("matrix_moles"),
        matrix_mass_g=float(payload.get("matrix_mass_g", 0.0)),
        matrix_source=str(payload.get("matrix_source", "omitted")),
    )
    return {
        "headspace_basis": state.headspace_basis,
        "matrix_source": state.matrix_source,
        "total_active_ul": state.total_active_ul,
        "total_vapor_ppm": state.total_vapor_ppm,
        "uncertainty": state.as_dict()["uncertainty"],
        "materials": [
            {
                "name": row.name,
                "mole_fraction": row.mole_fraction,
                "gamma": row.gamma,
                "partial_pressure_pa": row.partial_pressure_pa,
                "vapor_ppm": row.vapor_ppm,
                "oav": row.oav,
                "vp_source": row.sources.get("vp"),
                "gamma_source": row.sources.get("gamma"),
                "oav_model": row.sources.get("oav_model"),
            }
            for row in state.materials
        ],
    }


def _capture_pipeline_temporal(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    from engine.pipeline.formula_state import build_formula_state
    from engine.pipeline.simulator import simulate_formula

    build_formula_state.cache_clear()
    windows = tuple((str(label), float(seconds)) for label, seconds in payload["windows"])
    frames = simulate_formula(
        payload["ingredients_ul"],
        payload.get("dilutions"),
        batch_volume_ml=float(payload.get("batch_volume_ml", 30.0)),
        temperature_K=float(payload.get("temperature_K", 305.0)),
        context=str(payload.get("context", "skin")),
        windows=windows,
    )
    return [
        {
            "label": frame.label,
            "t_seconds": frame.t_seconds,
            "total_vapor_ppm": frame.state.total_vapor_ppm,
            "materials": [
                {"name": row.name, "raw_ul": row.raw_ul, "gamma": row.gamma, "oav": row.oav}
                for row in frame.state.materials
            ],
        }
        for frame in frames
    ]


def _capture_thermo_headspace(payload: Mapping[str, Any]) -> Any:
    from engine.thermo.headspace import headspace_from_wt_pct

    return headspace_from_wt_pct(
        payload["wt_pct"],
        T_K=float(payload.get("temperature_K", 305.0)),
        mw_table=payload.get("mw_table"),
        vp_table=payload.get("vp_table"),
        antoine_table=_tuples_by_name(payload.get("antoine_table")),
        dhvap_table=payload.get("dhvap_table"),
        hsp_table=_tuples_by_name(payload.get("hsp_table")),
    )


def _capture_thermo_trajectory(payload: Mapping[str, Any]) -> Any:
    from engine.thermo.trajectory import evaporate

    return evaporate(
        payload["wt_pct"],
        initial_mass_g=float(payload.get("initial_mass_g", 0.05)),
        surface_area_m2=float(payload.get("surface_area_m2", 5e-4)),
        kg_m_s=float(payload.get("kg_m_s", 0.005)),
        T_K=float(payload.get("temperature_K", 305.0)),
        duration_s=float(payload.get("duration_s", 60.0)),
        n_steps=int(payload.get("n_steps", 3)),
        mw_table=payload.get("mw_table"),
        vp_table=payload.get("vp_table"),
        antoine_table=_tuples_by_name(payload.get("antoine_table")),
        dhvap_table=payload.get("dhvap_table"),
        hsp_table=_tuples_by_name(payload.get("hsp_table")),
    )


def _capture_natural_composite(payload: Mapping[str, Any]) -> Any:
    from engine.pipeline.natural_absolute_decomposition import composite_headspace

    return composite_headspace(
        str(payload["material_name"]),
        float(payload["active_g"]),
        float(payload["total_moles_in_formula"]),
        float(payload.get("gamma_estimate", 0.6)),
        parent_moles=(
            float(payload["parent_moles"]) if payload.get("parent_moles") is not None else None
        ),
        temperature_K=float(payload.get("temperature_K", 298.15)),
        dhvap_estimate_kj_mol=(
            float(payload["dhvap_estimate_kj_mol"])
            if payload.get("dhvap_estimate_kj_mol") is not None
            else None
        ),
    )


def _capture_hansen_phase(payload: Mapping[str, Any]) -> dict[str, Any]:
    from engine.thermo.phase import bloom_on_dilution_risk, micro_phase_risk

    hsp_table = _tuples_by_name(payload["hsp_table"])
    radius = float(payload.get("radius", 10.0))
    return {
        "micro_phase": micro_phase_risk(
            payload["composition_wt"],
            hsp_table,
            radii={str(name): radius for name in payload["composition_wt"]},
        ),
        "bloom": bloom_on_dilution_risk(
            tuple(float(v) for v in payload["hsp_solute"]),
            tuple(float(v) for v in payload["initial_solvent"]),
            tuple(float(v) for v in payload["final_solvent"]),
            radius=radius,
        ),
    }


def _capture_diffusion(payload: Mapping[str, Any]) -> Any:
    from engine.diffusion_model import score_diffusion

    return score_diffusion(
        dict(payload["ingredients"]),
        dict(payload.get("dilutions", {})),
        dict(payload.get("gamma_map", {})),
    )


def _capture_skin_interaction(payload: Mapping[str, Any]) -> Any:
    from engine.skin_interaction import score_skin_interaction

    return score_skin_interaction(
        dict(payload["ingredients"]),
        dict(payload.get("dilutions", {})),
    )


def _capture_vapor_pressure_classifier(payload: Mapping[str, Any]) -> Any:
    from engine.vapor_pressure_modeling import analyze_vapor_pressure

    return analyze_vapor_pressure(
        str(payload["target_name"]),
        dict(payload["material_posteriors"]),
        {str(key): list(value) for key, value in payload["declared_pyramid"].items()},
        float(payload.get("concentrate_pct", 25.0)),
    )


def _capture_temporal_consistency(payload: Mapping[str, Any]) -> Any:
    from engine.temporal_volatility import analyze_temporal_consistency

    reviewer_timing = payload.get("reviewer_timing")
    return analyze_temporal_consistency(
        str(payload["target_name"]),
        dict(payload["material_posteriors"]),
        {str(key): list(value) for key, value in payload["declared_pyramid"].items()},
        (
            {str(key): list(value) for key, value in reviewer_timing.items()}
            if isinstance(reviewer_timing, Mapping)
            else None
        ),
    )


def _capture_dose_response(payload: Mapping[str, Any]) -> Any:
    from engine.dose_response import score_dose_response

    return score_dose_response(
        dict(payload["ingredients"]),
        dict(payload.get("dilutions", {})),
        float(payload.get("total_volume_ul", 10000.0)),
    )


def _capture_psychophysics(payload: Mapping[str, Any]) -> Any:
    from engine.psychophysics import score_psychophysics

    return score_psychophysics(
        dict(payload["ingredients"]),
        dict(payload.get("dilutions", {})),
    )


def _capture_maturation(payload: Mapping[str, Any]) -> dict[str, Any]:
    from engine.chemistry.maturation import MaturationReactor, predict_shelf_life_days

    functional_groups = {
        str(name): {str(group) for group in groups}
        for name, groups in payload.get("functional_groups", {}).items()
    }
    composition = {str(name): float(value) for name, value in payload["composition_g"].items()}
    reactor = MaturationReactor(
        dict(composition),
        t_k=float(payload.get("temperature_K", 295.0)),
        bht_protected=bool(payload.get("bht_protected", False)),
    )
    reactor.step(float(payload.get("step_days", 30.0)), functional_groups=functional_groups)
    return {
        "after_step": reactor.composition_g,
        "days_aged": reactor.days_aged,
        "shelf_life_days": predict_shelf_life_days(
            composition,
            t_k=float(payload.get("temperature_K", 295.0)),
            bht_protected=bool(payload.get("bht_protected", False)),
            threshold_pct=float(payload.get("threshold_pct", 10.0)),
            functional_groups=functional_groups,
            max_days=int(payload.get("max_days", 365)),
        ),
    }


def _capture_receptor_binding(payload: Mapping[str, Any]) -> dict[str, float]:
    from engine.receptor.binding import ligands_from_family, or_occupancy

    families = {str(name): str(family) for name, family in payload["families"].items()}
    ligand_table = {name: ligands_from_family(name, family) for name, family in families.items()}
    return or_occupancy(
        {str(name): float(value) for name, value in payload["concentrations_uM"].items()},
        ligand_table,
        adaptation={
            str(name): float(value) for name, value in payload.get("adaptation", {}).items()
        },
    )


def _capture_receptor_adaptation(payload: Mapping[str, Any]) -> Any:
    from engine.receptor.adaptation import AdaptationState, step_adaptation

    initial = payload.get("initial", {})
    state = AdaptationState(
        fast={str(k): float(v) for k, v in initial.get("fast", {}).items()},
        med={str(k): float(v) for k, v in initial.get("med", {}).items()},
        slow={str(k): float(v) for k, v in initial.get("slow", {}).items()},
    )
    return step_adaptation(
        state,
        {str(name): float(value) for name, value in payload["occupancy"].items()},
        float(payload["dt_seconds"]),
    )


def _capture_hedonic(payload: Mapping[str, Any]) -> Any:
    from engine.hedonic_model import score_hedonic

    return score_hedonic(
        dict(payload["ingredients"]),
        dict(payload.get("dilutions", {})),
    )


def _source_functions(path: Path, names: set[str]) -> dict[str, Callable[..., Any]]:
    """Load exact standalone function ASTs without importing unrelated app wiring."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    found = {node.name for node in selected}
    if found != names:
        raise ValueError(f"Missing source functions in {path}: {sorted(names - found)}")
    future = ast.ImportFrom(
        module="__future__",
        names=[ast.alias(name="annotations")],
        level=0,
    )
    module = ast.Module(body=[future, *selected], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, Any] = {"__name__": "c0_legacy_source_capture"}
    exec(compile(module, str(path), "exec"), namespace)
    return {name: namespace[name] for name in names}


def _capture_backend_longevity(payload: Mapping[str, Any]) -> float:
    functions = _source_functions(
        REPO_ROOT / "backend" / "app" / "domain" / "ingredients" / "chemistry.py",
        {"estimate_longevity"},
    )

    return functions["estimate_longevity"](dict(payload["note_distribution"]))


def _capture_backend_sillage(payload: Mapping[str, Any]) -> str:
    functions = _source_functions(
        REPO_ROOT / "backend" / "app" / "domain" / "ingredients" / "chemistry.py",
        {"estimate_sillage"},
    )

    return functions["estimate_sillage"](
        float(payload["top_percent"]),
        float(payload["concentration"]),
        float(payload["avg_vp"]) if payload.get("avg_vp") is not None else None,
        float(payload["avg_mw"]) if payload.get("avg_mw") is not None else None,
    )


def _capture_temporal_graph(payload: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np

    from engine.temporal_graph import TemporalEngine

    engine = TemporalEngine(np.asarray(payload["time_grid_hours"], dtype=float))
    profile = engine.simulate(str(payload["formula_name"]), dict(payload["ingredients_pct"]))
    return {
        "formula_name": profile.formula_name,
        "time_hours": profile.time_hours,
        "total_headspace_ppb": profile.total_headspace_ppb,
        "projection_cm": profile.projection_cm,
        "note_evolution": profile.note_evolution,
        "perceptual_half_life_hr": profile.perceptual_half_life_hr,
        "longevity_hr": profile.longevity_hr,
    }


def _capture_oav_script(payload: Mapping[str, Any]) -> dict[str, Any]:
    from scripts.oav_headspace_analyze import compute

    formula_data = [
        (str(name), float(stock_ul), float(dilution_pct))
        for name, stock_ul, dilution_pct in payload["formula_data"]
    ]
    result = compute(formula_data)
    return {
        "total_conc": result["total_conc"],
        "edp_pct": result["edp_pct"],
        "n_materials": result["n_materials"],
        "total_oav_simple": result["total_oav_simple"],
        "total_oav_headspace": result["total_oav_headspace"],
        "materials": result["materials"],
        "headspace": result["headspace"],
    }


def _capture_formula_simulator(payload: Mapping[str, Any]) -> dict[str, Any]:
    from scripts.formula_simulator import simulate

    result = simulate(dict(payload["formula"]), dict(payload.get("deltas", {})))
    return {
        "scores": result["scores"],
        "industry": result["industry"],
        "perceptible": result["perceptible"],
        "total_vapor": result["total_vapor"],
    }


def _capture_optimizer_scores(payload: Mapping[str, Any]) -> dict[str, float]:
    from engine.optimizer.models import FormulaVector, ObjectiveWeights
    from engine.optimizer.scoring import FormulaScorer

    vector = FormulaVector(
        ingredients={str(name): float(value) for name, value in payload["ingredients_pct"].items()},
        dilutions={str(name): float(value) for name, value in payload.get("dilutions", {}).items()},
    )
    result = FormulaScorer(ObjectiveWeights()).score(vector)
    return {
        str(name): float(value)
        for name, value in result.items()
        if isinstance(value, (int, float)) and not str(name).startswith("_")
    }


def _capture_unified_release(payload: Mapping[str, Any]) -> dict[str, Any]:
    from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
    from engine.pipeline.release_scoring import compute_unified_release_scores

    formula = dict(payload["formula"])
    request = OAVAuthorityRequest(
        formula_name=str(formula.get("name", "C0 legacy release")),
        ingredients_ul=dict(formula["ingredients_ul"]),
        dilutions=dict(formula.get("dilutions", {})),
        batch_volume_ml=float(payload.get("batch_volume_ml", 30.0)),
        temperature_K=float(payload.get("temperature_K", 305.0)),
    )
    oav_result = analyze_oav_authority(request)
    result = compute_unified_release_scores(
        formula,
        oav_result,
        dict(payload.get("gate_report", {"gates": [], "preflight": {"checks": []}})),
    ).as_dict()
    result["scores"] = {
        str(name): value
        for name, value in result["scores"].items()
        if isinstance(value, (int, float, str, bool)) and not str(name).startswith("_")
    }
    return result


def _capture_in_sample_calibration(payload: Mapping[str, Any]) -> Any:
    from engine.calibration import ScoreCalibrationPipeline

    return ScoreCalibrationPipeline().train_from_rows(list(payload["rows"])).as_dict()


LEGACY_CAPTURES: dict[str, LegacyCapture] = {
    "backend_longevity_v1": _capture_backend_longevity,
    "backend_sillage_v1": _capture_backend_sillage,
    "diffusion_v1": _capture_diffusion,
    "dose_response_v1": _capture_dose_response,
    "formula_simulator_v1": _capture_formula_simulator,
    "formula_state_headspace_v1": _capture_formula_state,
    "hansen_phase_v1": _capture_hansen_phase,
    "hedonic_v1": _capture_hedonic,
    "in_sample_calibration_v1": _capture_in_sample_calibration,
    "natural_composite_v1": _capture_natural_composite,
    "oav_script_v1": _capture_oav_script,
    "optimizer_scores_v1": _capture_optimizer_scores,
    "pipeline_temporal_v1": _capture_pipeline_temporal,
    "psychophysics_v1": _capture_psychophysics,
    "receptor_adaptation_v1": _capture_receptor_adaptation,
    "receptor_binding_v1": _capture_receptor_binding,
    "skin_interaction_v1": _capture_skin_interaction,
    "temporal_consistency_v1": _capture_temporal_consistency,
    "temporal_graph_v1": _capture_temporal_graph,
    "thermo_headspace_v1": _capture_thermo_headspace,
    "thermo_trajectory_v1": _capture_thermo_trajectory,
    "unified_release_v1": _capture_unified_release,
    "vapor_pressure_classifier_v1": _capture_vapor_pressure_classifier,
    "maturation_v1": _capture_maturation,
}


def capture_legacy_case(selector: str, input_payload: Mapping[str, Any]) -> Any:
    """Capture one normalized, read-only legacy output by stable selector."""

    capture = LEGACY_CAPTURES.get(selector)
    if capture is None:
        raise KeyError(f"Unknown legacy capture selector: {selector}")
    return _normalize(capture(input_payload))


def compare_normalized(
    expected: Any,
    actual: Any,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
    path: str = "$",
) -> list[str]:
    """Recursively compare normalized structures and return concise differences."""

    differences: list[str] = []
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected != actual:
            differences.append(f"{path}: expected {expected!r}, actual {actual!r}")
        return differences
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not math.isclose(
            float(expected),
            float(actual),
            rel_tol=relative_tolerance,
            abs_tol=absolute_tolerance,
        ):
            differences.append(f"{path}: expected {expected!r}, actual {actual!r}")
        return differences
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        expected_keys = set(expected)
        actual_keys = set(actual)
        if expected_keys != actual_keys:
            differences.append(
                f"{path}: key mismatch expected={sorted(expected_keys)} actual={sorted(actual_keys)}"
            )
            return differences
        for key in sorted(expected_keys, key=str):
            differences.extend(
                compare_normalized(
                    expected[key],
                    actual[key],
                    absolute_tolerance=absolute_tolerance,
                    relative_tolerance=relative_tolerance,
                    path=f"{path}.{key}",
                )
            )
        return differences
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: length mismatch expected={len(expected)} actual={len(actual)}"]
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(
                compare_normalized(
                    expected_item,
                    actual_item,
                    absolute_tolerance=absolute_tolerance,
                    relative_tolerance=relative_tolerance,
                    path=f"{path}[{index}]",
                )
            )
        return differences
    if expected != actual:
        differences.append(f"{path}: expected {expected!r}, actual {actual!r}")
    return differences


def validate_legacy_fixtures(
    fixtures: Mapping[str, Any],
    inventory: Mapping[str, Any],
    *,
    root: Path = REPO_ROOT,
    fixture_path: str | Path,
    fixture_sha_path: str | Path,
    successors: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if fixtures.get("schema_version") != "c0-legacy-physical-model-fixtures-v1":
        errors.append("fixture schema_version must be c0-legacy-physical-model-fixtures-v1")
    cases = fixtures.get("cases")
    if not isinstance(cases, list) or not cases:
        return errors + ["fixture cases must be a non-empty list"]
    stored_pins: dict[tuple[str, str], str] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        case_id = str(case.get("id", "<missing-id>"))
        source_hashes = case.get("source_sha256")
        if isinstance(source_hashes, Mapping):
            for relative, digest in source_hashes.items():
                stored_pins[(case_id, str(relative))] = str(digest)
    if successors is None:
        try:
            successors = load_pin_successors(
                root / "tests" / "fixtures" / "c0_legacy_physical_model_cases_successors.json",
                root=root,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load successor overlay: {exc}")
            successors = []
    rebound, bind_errors = bind_pin_successors(
        successors, stored_pins, root=root, label="the C0 legacy fixtures"
    )
    errors.extend(bind_errors)
    implementations = {
        record.get("id"): record
        for record in inventory.get("implementations", [])
        if isinstance(record, Mapping)
    }
    implementation_ids = set(implementations)
    seen: set[str] = set()
    selector_cases: dict[str, list[str]] = {}
    for case in cases:
        if not isinstance(case, Mapping):
            errors.append("fixture case must be an object")
            continue
        case_id = str(case.get("id", "<missing-id>"))
        if case_id in seen:
            errors.append(f"{case_id}: duplicate fixture id")
        seen.add(case_id)
        implementation_id = case.get("implementation_id")
        if implementation_id not in implementation_ids:
            errors.append(f"{case_id}: unknown implementation_id {implementation_id!r}")
        if case.get("classification") != "LEGACY_HEURISTIC":
            errors.append(f"{case_id}: classification must be LEGACY_HEURISTIC")
        warning = str(case.get("warning", ""))
        if "not scientific validation" not in warning.casefold():
            errors.append(f"{case_id}: warning must state not scientific validation")
        selector = str(case.get("selector", ""))
        if selector not in LEGACY_CAPTURES:
            errors.append(f"{case_id}: unknown selector {selector!r}")
        else:
            selector_cases.setdefault(selector, []).append(case_id)
        input_payload = case.get("input")
        if not isinstance(input_payload, Mapping):
            errors.append(f"{case_id}: input must be an object")
        else:
            actual_input_hash = hashlib.sha256(canonical_json_bytes(input_payload)).hexdigest()
            if case.get("input_sha256") != actual_input_hash:
                errors.append(f"{case_id}: stale input_sha256")
        source_hashes = case.get("source_sha256")
        if not isinstance(source_hashes, Mapping) or not source_hashes:
            errors.append(f"{case_id}: source_sha256 must be a non-empty object")
        else:
            implementation = implementations.get(implementation_id)
            if isinstance(implementation, Mapping):
                declared_sources = {
                    str(source.get("path"))
                    for source in implementation.get("source", [])
                    if isinstance(source, Mapping) and source.get("path")
                }
                missing_sources = sorted(declared_sources - set(source_hashes))
                if missing_sources:
                    errors.append(
                        f"{case_id}: source_sha256 does not bind implementation source "
                        f"paths: {', '.join(missing_sources)}"
                    )
            for relative, expected_hash in source_hashes.items():
                try:
                    path = _repo_path(root, str(relative))
                    successor = rebound.get((case_id, str(relative)))
                    if successor is not None:
                        actual_hash = _lf_sha256_file(path)
                        if actual_hash != successor:
                            errors.append(f"{case_id}: successor is stale for {relative}")
                    else:
                        actual_hash = _sha256_file(path)
                        if actual_hash != expected_hash:
                            errors.append(f"{case_id}: stale source hash for {relative}")
                except (OSError, ValueError) as exc:
                    errors.append(f"{case_id}: invalid source path {relative}: {exc}")
        if "output" not in case:
            errors.append(f"{case_id}: output is required")

    missing_selectors = sorted(set(LEGACY_CAPTURES) - set(selector_cases))
    if missing_selectors:
        errors.append(f"missing legacy selectors: {', '.join(missing_selectors)}")
    for selector, case_ids in sorted(selector_cases.items()):
        if len(case_ids) > 1:
            errors.append(f"duplicate legacy selector {selector}: {', '.join(case_ids)}")

    fixture_file = Path(fixture_path)
    sha_file = Path(fixture_sha_path)
    if not fixture_file.is_file():
        errors.append(f"missing fixture file: {fixture_file}")
    else:
        canonical = canonical_json_bytes(fixtures, trailing_newline=True)
        if fixture_file.read_bytes() != canonical:
            errors.append(
                "fixture file is not canonical sorted compact JSON with one trailing newline"
            )
    if not sha_file.is_file():
        errors.append(f"missing fixture SHA file: {sha_file}")
    else:
        expected_sha = sha_file.read_text(encoding="ascii").strip().split()[0]
        actual_sha = hashlib.sha256(
            canonical_json_bytes(fixtures, trailing_newline=True)
        ).hexdigest()
        if expected_sha != actual_sha:
            errors.append(f"fixture SHA mismatch: expected {expected_sha}, actual {actual_sha}")
    return errors


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=REPO_ROOT / "docs" / "verification" / "c0" / "physical_model_inventory.json",
    )
    parser.add_argument(
        "--adr",
        type=Path,
        default=REPO_ROOT
        / "docs"
        / "architecture"
        / "ADR-2026-08-02-c0-physical-model-consolidation.md",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "c0_legacy_physical_model_cases.json",
    )
    parser.add_argument(
        "--fixture-sha",
        type=Path,
        default=REPO_ROOT / "tests" / "fixtures" / "c0_legacy_physical_model_cases.sha256",
    )
    parser.add_argument(
        "--inventory-successors",
        type=Path,
        default=REPO_ROOT
        / "docs"
        / "verification"
        / "c0"
        / "physical_model_inventory_successors.json",
    )
    parser.add_argument(
        "--fixture-successors",
        type=Path,
        default=REPO_ROOT
        / "tests"
        / "fixtures"
        / "c0_legacy_physical_model_cases_successors.json",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    inventory = load_inventory(args.inventory)
    errors: list[str] = []
    inventory_successors: Sequence[Mapping[str, Any]] | None = None
    try:
        inventory_successors = load_pin_successors(args.inventory_successors, root=REPO_ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load inventory successor overlay: {exc}")
        inventory_successors = []
    errors.extend(
        validate_inventory(
            inventory, root=REPO_ROOT, adr_path=args.adr, successors=inventory_successors
        )
    )
    try:
        fixtures = load_legacy_fixtures(args.fixtures)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load legacy fixtures: {exc}")
        fixtures = None
    if fixtures is not None:
        fixture_successors: Sequence[Mapping[str, Any]] | None = None
        try:
            fixture_successors = load_pin_successors(args.fixture_successors, root=REPO_ROOT)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load fixture successor overlay: {exc}")
            fixture_successors = []
        errors.extend(
            validate_legacy_fixtures(
                fixtures,
                inventory,
                root=REPO_ROOT,
                fixture_path=args.fixtures,
                fixture_sha_path=args.fixture_sha,
                successors=fixture_successors,
            )
        )
    if errors:
        print(
            json.dumps({"status": "FAIL", "error_count": len(errors), "errors": errors}, indent=2)
        )
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "implementation_count": len(inventory["implementations"]),
                "call_edge_count": len(inventory["call_edges"]),
                "fixture_count": len(fixtures["cases"]),
                "classifications": sorted(ALLOWED_CLASSIFICATIONS),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
