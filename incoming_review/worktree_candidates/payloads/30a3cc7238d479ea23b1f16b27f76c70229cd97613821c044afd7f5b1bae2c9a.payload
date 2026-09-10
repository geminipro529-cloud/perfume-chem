"""Build a deterministic, non-secret scientific truth baseline.

The scanner is intentionally read-only. It inventories allowlisted scientific
inputs, material-property cells, structured knowledge rules, module constants,
runtime references, and preserved compatibility fixtures. It does not infer
scientific authority from passing tests or promote legacy data.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "scientific-truth-inventory-v1"

PROPERTY_SPECS: dict[str, dict[str, Any]] = {
    "cas": {
        "unit": None,
        "conditions": {},
        "claims": ("identity", "safety_compliance_screening"),
    },
    "smiles": {
        "unit": None,
        "conditions": {},
        "claims": ("identity", "property_value"),
    },
    "inchikey": {
        "unit": None,
        "conditions": {},
        "claims": ("identity",),
    },
    "mw_g_mol": {
        "unit": "g/mol",
        "conditions": {},
        "claims": ("identity", "mass_volume_conversion", "headspace_prediction"),
    },
    "density_25c_g_ml": {
        "unit": "g/mL",
        "conditions": {"temperature_c": 25.0},
        "claims": ("quantity", "mass_volume_conversion"),
    },
    "logp": {
        "unit": "dimensionless",
        "conditions": {},
        "claims": ("property_value", "headspace_prediction"),
    },
    "vp_25c_pa": {
        "unit": "Pa",
        "conditions": {"temperature_c": 25.0},
        "claims": ("property_value", "headspace_prediction", "intervention_recommendation"),
    },
    "antoine": {
        "unit": "equation_parameters",
        "conditions": {},
        "claims": ("property_value", "headspace_prediction"),
    },
    "dhvap_kj_mol": {
        "unit": "kJ/mol",
        "conditions": {},
        "claims": ("property_value", "headspace_prediction"),
    },
    "kaw_eff": {
        "unit": "declared_convention_required",
        "conditions": {},
        "claims": ("property_value", "headspace_prediction"),
    },
    "hsp": {
        "unit": "MPa^0.5_components",
        "conditions": {},
        "claims": ("property_value", "headspace_prediction"),
    },
    "odt_air_ppb": {
        "unit": "ppb_v/v",
        "conditions": {"medium": "air", "endpoint": "unspecified", "route": "unspecified"},
        "claims": ("threshold_screening", "headspace_prediction"),
    },
    "odt_eth_ppm": {
        "unit": "ppm_w/w",
        "conditions": {
            "medium": "ethanol_solution",
            "endpoint": "unspecified",
            "route": "unspecified",
        },
        "claims": ("threshold_screening",),
    },
    "stevens_n": {
        "unit": "dimensionless",
        "conditions": {},
        "claims": ("sensory_intensity",),
    },
    "or_targets": {
        "unit": None,
        "conditions": {},
        "claims": ("property_value",),
    },
    "trp_targets": {
        "unit": None,
        "conditions": {},
        "claims": ("property_value",),
    },
    "hedonic_valence": {
        "unit": "dimensionless",
        "conditions": {},
        "claims": ("sensory_intensity", "intervention_recommendation"),
    },
    "ifra_max_pct_edp": {
        "unit": "percent_finished_product",
        "conditions": {"product_type": "edp", "category": "unspecified"},
        "claims": ("safety_compliance_screening", "release"),
    },
    "user_stock_dilution": {
        "unit": "mass_or_volume_fraction_unspecified",
        "conditions": {},
        "claims": ("quantity", "mass_volume_conversion"),
    },
}

SCIENTIFIC_PATH_KEYWORDS = (
    "analyt",
    "allergen",
    "antoine",
    "calibrat",
    "family",
    "headspace",
    "hedonic",
    "ifra",
    "interaction",
    "knowledge",
    "natural",
    "neuroscience",
    "oav",
    "odor",
    "property",
    "receptor",
    "regulat",
    "safety",
    "science",
    "scientific",
    "sensory",
    "skin",
    "thermo",
    "threshold",
    "vapor",
)

CLAIM_TYPES = (
    "identity",
    "quantity",
    "mass_volume_conversion",
    "threshold_screening",
    "headspace_prediction",
    "sensory_intensity",
    "formula_similarity",
    "natural_authenticity",
    "analytical_identification",
    "analytical_quantitation",
    "safety_compliance_screening",
    "family_classification",
    "intervention_recommendation",
    "release",
)


SOLFORGE_RUNTIME_AUTHORITY: dict[str, dict[str, object]] = {
    "legacy_fixed_valence_hedonic": {
        "classification": "LEGACY_HEURISTIC_PROVENANCE",
        "runtime_path": "engine/hedonic_model.py",
        "permitted_use": "EXPLICIT_HISTORICAL_REPLAY_ONLY",
        "authority": False,
    },
    "legacy_oav_authority_rank": {
        "classification": "LEGACY_HEURISTIC_PROVENANCE",
        "runtime_path": "engine/pipeline/oav_authority.py",
        "permitted_use": "EXPLICIT_HISTORICAL_REPLAY_ONLY",
        "authority": False,
    },
    "legacy_unified_score": {
        "classification": "LEGACY_HEURISTIC_PROVENANCE",
        "runtime_path": "engine/pipeline/release_scoring.py",
        "permitted_use": "EXPLICIT_HISTORICAL_REPLAY_ONLY",
        "authority": False,
    },
    "oav_evidence_v2": {
        "classification": "COMPUTATIONAL_OR_MEASURED_EVIDENCE_STATE",
        "runtime_path": "engine/pipeline/oav_evidence.py",
        "authority": "CONDITIONAL_ON_EACH_ROW_BASIS_AND_SCOPE",
    },
    "hedonic_evidence_v2": {
        "classification": "OBSERVED_EXACT_SCOPE_ONLY",
        "runtime_path": "engine/hedonic_evidence.py",
        "authority": "EXACT_RECORDED_SCOPE_ONLY",
    },
    "release_evidence_v2": {
        "classification": "NONCOMPENSATORY_DECISION_SUPPORT",
        "runtime_path": "engine/pipeline/release_evidence.py",
        "authority": "READY_FOR_HUMAN_REVIEW_ONLY",
    },
}


def _is_generated_or_metadata(path: Path, repo_root: Path) -> bool:
    relative = path.relative_to(repo_root)
    relative_posix = relative.as_posix().casefold()
    lowered_parts = {part.casefold() for part in relative.parts}
    if lowered_parts.intersection(
        {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    ):
        return True
    if path.suffix.casefold() in {".pyc", ".pyo"}:
        return True
    if relative_posix.endswith((".db-wal", ".db-shm")):
        return True
    if relative_posix.startswith(
        ("verification_runs/wheel-smoke/", "docs/verification/b0/")
    ):
        return True
    return relative_posix in {
        "scripts/scientific_truth_inventory.py",
        "tests/test_scientific_truth_inventory.py",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _scientific_files(repo_root: Path) -> list[Path]:
    candidates: set[Path] = set()
    data_root = repo_root / "data"
    if data_root.exists():
        candidates.update(
            path
            for path in data_root.rglob("*")
            if path.is_file() and not _is_generated_or_metadata(path, repo_root)
        )

    engine_root = repo_root / "engine"
    if engine_root.exists():
        for path in engine_root.rglob("*"):
            if not path.is_file():
                continue
            if _is_generated_or_metadata(path, repo_root):
                continue
            relative = path.relative_to(repo_root).as_posix().casefold()
            if path.suffix == ".py" or any(keyword in relative for keyword in SCIENTIFIC_PATH_KEYWORDS):
                candidates.add(path)

    for root_name in ("backend/app", "scripts", "docs", "verification_runs", "tests"):
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if _is_generated_or_metadata(path, repo_root):
                continue
            relative = path.relative_to(repo_root).as_posix().casefold()
            if any(keyword in relative for keyword in SCIENTIFIC_PATH_KEYWORDS):
                candidates.add(path)
            if relative in {
                "tests/fixtures/golden_formula_cases.json",
                "tests/fixtures/golden_formula_cases.sha256",
            }:
                candidates.add(path)

    return sorted(candidates, key=lambda path: path.relative_to(repo_root).as_posix())


def _python_files(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for root_name in ("engine", "backend/app", "scripts", "tests"):
        root = repo_root / root_name
        if root.exists():
            paths.extend(
                path
                for path in root.rglob("*.py")
                if path.is_file() and not _is_generated_or_metadata(path, repo_root)
            )
    return sorted(paths, key=lambda path: path.relative_to(repo_root).as_posix())


def _source_authority(source_locator: str | None, value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    source = (source_locator or "").casefold()
    if not source:
        return "UNATTRIBUTED_LEGACY"
    if any(token in source for token in ("heuristic", "estimate", "model", "analog")):
        return "LEGACY_HEURISTIC"
    if any(token in source for token in ("supplier", "coa", "sds", "ifra certificate")):
        return "SUPPLIER_PROVIDED"
    if any(token in source for token in ("pubchem", "nist", "doi:", "pmid:", "primary:")):
        return "LITERATURE_DERIVED"
    if "inventory.txt" in source:
        return "LOCAL_RECORD"
    return "LEGACY_TRACEABLE"


def _property_consumers(property_type: str) -> list[str]:
    routes = {
        "mw_g_mol": ["engine/quantities.py", "engine/thermo", "engine/property_estimator.py"],
        "density_25c_g_ml": ["engine/quantities.py", "engine/pipeline"],
        "logp": ["engine/thermo/activity.py", "engine/property_estimator.py"],
        "vp_25c_pa": ["engine/thermo", "engine/pipeline/simulator.py"],
        "antoine": ["engine/thermo/antoine.py"],
        "dhvap_kj_mol": ["engine/thermo/antoine.py"],
        "odt_air_ppb": ["engine/odor_thresholds.py", "engine/pipeline/oav_authority.py"],
        "odt_eth_ppm": ["engine/odor_thresholds.py", "engine/pipeline/oav_authority.py"],
        "ifra_max_pct_edp": ["engine/ifra_safety.py", "engine/authority_gates.py"],
        "hedonic_valence": ["engine/hedonic_model.py"],
        "or_targets": ["engine/receptor"],
        "trp_targets": ["engine/pipeline/neuroscience.py"],
    }
    return routes.get(property_type, ["engine/data_spine/loader.py"])


def _material_observations(repo_root: Path) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    material_count = 0
    material_root = repo_root / "data" / "materials"
    for path in sorted(material_root.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if not isinstance(payload, list):
            continue
        for row_index, material in enumerate(payload):
            if not isinstance(material, dict):
                continue
            material_count += 1
            subject = str(material.get("canonical_name") or f"row-{row_index}")
            provenance = material.get("provenance")
            provenance = provenance if isinstance(provenance, dict) else {}
            for property_type, spec in PROPERTY_SPECS.items():
                if property_type not in material:
                    continue
                value = _json_safe(material.get(property_type))
                source_locator = provenance.get(property_type)
                if property_type == "vp_25c_pa" and not source_locator:
                    source_locator = material.get("vp_source")
                authority = _source_authority(
                    str(source_locator) if source_locator is not None else None,
                    value,
                )
                impacts = list(spec["claims"])
                records.append(
                    {
                        "observation_id": (
                            f"legacy-material:{path.stem}:{row_index}:{property_type}"
                        ),
                        "subject_id": subject,
                        "identity_scope": "canonical_name_legacy",
                        "property_type": property_type,
                        "current_value": value,
                        "original_unit": spec["unit"],
                        "canonical_unit": spec["unit"],
                        "conditions": spec["conditions"],
                        "source_locator": source_locator,
                        "evidence_class": authority,
                        "uncertainty_status": (
                            "UNKNOWN" if value is not None else "NOT_APPLICABLE"
                        ),
                        "authority_label": authority,
                        "review_state": "LEGACY_UNREVIEWED",
                        "runtime_path": path.relative_to(repo_root).as_posix(),
                        "runtime_consumers": _property_consumers(property_type),
                        "claim_impacts": impacts,
                        "affects_blocking_gate": any(
                            claim
                            in {
                                "identity",
                                "quantity",
                                "mass_volume_conversion",
                                "threshold_screening",
                                "safety_compliance_screening",
                                "release",
                            }
                            for claim in impacts
                        ),
                        "conflict_set": None,
                        "deprecation_or_replacement_candidate": authority
                        in {"UNKNOWN", "UNATTRIBUTED_LEGACY", "LEGACY_HEURISTIC"},
                        "content_sha256": _canonical_hash(
                            {
                                "subject": subject,
                                "property_type": property_type,
                                "value": value,
                                "unit": spec["unit"],
                                "source": source_locator,
                            }
                        ),
                    }
                )

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record["subject_id"].casefold(), record["property_type"])].append(record)
    for group in grouped.values():
        distinct = {record["content_sha256"] for record in group}
        if len(group) > 1 and len(distinct) > 1:
            conflict_id = "conflict:" + _canonical_hash(
                sorted(record["observation_id"] for record in group)
            )[:16]
            for record in group:
                record["conflict_set"] = conflict_id

    return records, material_count


def _knowledge_rules(repo_root: Path) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    root = repo_root / "data" / "knowledge_graph"
    if not root.exists():
        return rules
    for path in sorted(root.glob("*.json")):
        if not any(token in path.name.casefold() for token in ("rule", "synergy", "pairing")):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        candidates: list[tuple[str, dict[str, Any]]] = []
        if isinstance(payload, list):
            candidates.extend((str(index), item) for index, item in enumerate(payload) if isinstance(item, dict))
        elif isinstance(payload, dict):
            if any(key in payload for key in ("subject", "material_a", "source")):
                candidates.append(("root", payload))
            else:
                for key, value in payload.items():
                    if isinstance(value, dict):
                        candidates.append((str(key), value))
                    elif isinstance(value, list):
                        candidates.extend(
                            (f"{key}:{index}", item)
                            for index, item in enumerate(value)
                            if isinstance(item, dict)
                        )
        for locator, item in candidates:
            subject = item.get("subject", item.get("material_a", item.get("source", item.get("name"))))
            relation = item.get("relation", item.get("type", item.get("effect", "UNSTRUCTURED")))
            object_value = item.get(
                "object",
                item.get("material_b", item.get("target", item.get("pairs_with"))),
            )
            rules.append(
                {
                    "rule_id": f"legacy-rule:{path.stem}:{locator}",
                    "runtime_path": path.relative_to(repo_root).as_posix(),
                    "exact_locator": locator,
                    "subject": _json_safe(subject),
                    "relation": _json_safe(relation),
                    "object": _json_safe(object_value),
                    "current_value_sha256": _canonical_hash(item),
                    "source": item.get("source"),
                    "evidence_class": item.get("evidence_class", "UNKNOWN"),
                    "authority_label": item.get("status", "ADVISORY_LEGACY"),
                    "claim_impacts": [
                        "family_classification",
                        "intervention_recommendation",
                    ],
                    "affects_blocking_gate": False,
                    "deprecation_or_replacement_candidate": True,
                }
            )
    return rules


def _constant_value(node: ast.AST) -> tuple[Any, dict[str, Any]]:
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, MemoryError, RecursionError):
        return None, {"kind": node.__class__.__name__}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value, {"kind": type(value).__name__}
    if isinstance(value, dict):
        return None, {"kind": "dict", "length": len(value)}
    if isinstance(value, (list, tuple, set, frozenset)):
        return None, {"kind": type(value).__name__, "length": len(value)}
    return None, {"kind": type(value).__name__}


def _code_constants(repo_root: Path) -> list[dict[str, Any]]:
    parsed: dict[Path, ast.Module] = {}
    for path in _python_files(repo_root):
        try:
            parsed[path] = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

    definitions: list[tuple[Path, str, ast.AST, int]] = []
    for path, tree in parsed.items():
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value_node = node.value
            if value_node is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    relative = path.relative_to(repo_root).as_posix().casefold()
                    if any(keyword in relative for keyword in SCIENTIFIC_PATH_KEYWORDS):
                        definitions.append((path, target.id, value_node, node.lineno))

    load_locations: dict[str, list[str]] = defaultdict(list)
    names = {name for _, name, _, _ in definitions}
    for path, tree in parsed.items():
        relative = path.relative_to(repo_root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in names:
                load_locations[node.id].append(f"{relative}:{node.lineno}")

    records: list[dict[str, Any]] = []
    for path, name, value_node, line in definitions:
        scalar, shape = _constant_value(value_node)
        relative = path.relative_to(repo_root).as_posix()
        consumers = sorted(set(load_locations.get(name, [])))
        records.append(
            {
                "constant_id": f"{relative}:{name}",
                "name": name,
                "runtime_path": relative,
                "definition_line": line,
                "current_value": scalar,
                "value_shape": shape,
                "value_ast_sha256": hashlib.sha256(
                    ast.dump(value_node, include_attributes=False).encode("utf-8")
                ).hexdigest(),
                "consumers": consumers,
                "evidence_class": "CODE_CONSTANT",
                "uncertainty_status": "UNDECLARED",
                "authority_label": "LEGACY_CODE_PARAMETER",
                "claim_impacts": _claim_impacts_for_text(f"{relative} {name}"),
                "affects_blocking_gate": any(
                    token in name
                    for token in ("IFRA", "ODT", "THRESHOLD", "LIMIT", "DENSITY", "MW")
                ),
                "deprecation_or_replacement_candidate": True,
            }
        )
    return sorted(records, key=lambda item: item["constant_id"])


def _claim_impacts_for_text(text: str) -> list[str]:
    lowered = text.casefold()
    impacts: set[str] = set()
    mappings = {
        "identity": ("identity", "cas", "smiles", "inchikey"),
        "quantity": ("quantity", "density", "mass", "volume"),
        "mass_volume_conversion": ("density", "molecular_weight", "mw_"),
        "threshold_screening": ("odt", "threshold", "oav"),
        "headspace_prediction": ("headspace", "vapor", "antoine", "thermo"),
        "sensory_intensity": ("sensory", "hedonic", "stevens", "receptor"),
        "formula_similarity": ("similarity", "distance"),
        "natural_authenticity": ("natural", "botanical", "chemotype"),
        "analytical_identification": (
            "analyt",
            "gcms",
            "gc_ms",
            "retention",
            "spectrum",
        ),
        "analytical_quantitation": ("analyt", "calibrat", "response_factor", "quant"),
        "safety_compliance_screening": ("ifra", "allergen", "regulat", "safety"),
        "family_classification": ("family", "taxonomy"),
        "intervention_recommendation": ("interaction", "pairing", "recommend"),
        "release": ("release", "authority", "gate"),
    }
    for claim, tokens in mappings.items():
        if any(token in lowered for token in tokens):
            impacts.add(claim)
    return sorted(impacts)


def _consumer_text_index(repo_root: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for path in _python_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        records.append((path.relative_to(repo_root).as_posix(), text))
    return records


def _source_digests(repo_root: Path) -> list[dict[str, Any]]:
    text_index = _consumer_text_index(repo_root)
    results: list[dict[str, Any]] = []
    for path in _scientific_files(repo_root):
        relative = path.relative_to(repo_root).as_posix()
        basename = path.name
        consumers = sorted(
            consumer_path
            for consumer_path, text in text_index
            if basename in text and consumer_path != relative
        )
        results.append(
            {
                "path": relative,
                "byte_length": path.stat().st_size,
                "sha256": _sha256(path),
                "runtime_consumers": consumers,
                "claim_impacts": _claim_impacts_for_text(relative),
            }
        )
    return results


def _legacy_fixture(repo_root: Path, relative: str) -> dict[str, Any] | None:
    path = repo_root / relative
    if not path.is_file():
        return None
    return {
        "path": relative,
        "byte_length": path.stat().st_size,
        "sha256": _sha256(path),
        "classification": "LEGACY_REGRESSION_REFERENCE_NOT_SCIENTIFIC_AUTHORITY",
    }


def build_inventory(repo_root: Path) -> dict[str, Any]:
    """Return a deterministic scientific truth inventory for *repo_root*."""
    repo_root = repo_root.resolve()
    material_root = repo_root / "data" / "materials"
    if not material_root.is_dir():
        raise ValueError("repository root must contain data/materials")

    material_observations, material_count = _material_observations(repo_root)
    knowledge_rules = _knowledge_rules(repo_root)
    constants = _code_constants(repo_root)
    digests = _source_digests(repo_root)

    impact_counts = {claim: 0 for claim in CLAIM_TYPES}
    for item in (*material_observations, *knowledge_rules, *constants, *digests):
        for claim in item.get("claim_impacts", []):
            if claim in impact_counts:
                impact_counts[claim] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "repository_root": str(repo_root),
        "summary": {
            "source_digest_count": len(digests),
            "material_count": material_count,
            "material_property_observation_count": len(material_observations),
            "knowledge_rule_count": len(knowledge_rules),
            "code_constant_count": len(constants),
        },
        "source_digests": digests,
        "material_property_observations": material_observations,
        "knowledge_rules": knowledge_rules,
        "code_constants": constants,
        "claim_impact_map": impact_counts,
        "solforge_runtime_authority": SOLFORGE_RUNTIME_AUTHORITY,
        "legacy_fixtures": {
            "science_audit": _legacy_fixture(
                repo_root, "verification_runs/science_audit.json"
            ),
            "golden_formula_cases": _legacy_fixture(
                repo_root, "tests/fixtures/golden_formula_cases.json"
            ),
            "golden_formula_lock": _legacy_fixture(
                repo_root, "tests/fixtures/golden_formula_cases.sha256"
            ),
        },
        "authority_warning": (
            "Inventory membership and passing tests do not promote scientific authority."
        ),
    }


def write_inventory(report: dict[str, Any], output: Path) -> None:
    """Write *report* as stable JSON, optionally with deterministic gzip."""
    payload = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.name.casefold().endswith(".json.gz"):
        output.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
        return
    output.write_bytes(payload)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = build_inventory(args.repo_root)
    write_inventory(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
