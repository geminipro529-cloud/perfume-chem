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
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA_VERSION = "scientific-truth-inventory-v1"
RECOVERY_BASELINE_SCHEMA_VERSION = "temporal_oav_hedonic_recovery_baseline_v1"

RECOVERY_BASELINE_FILES = (
    "engine/pipeline/oav_evidence.py",
    "engine/fuckups/pre_mix_guard.py",
    "engine/sensory/ledger.py",
    "engine/preference.py",
    "engine/hedonic_evidence.py",
    "engine/hedonic_model.py",
    "engine/perception/perceptual_topology.py",
    "engine/perception/wood_depth.py",
)

RECOVERY_BASELINE_MODULES = (
    "architectural-delta-engine",
    "temporal-sensory-ledger",
    "hedonic-preference-learner",
    "universal-perceptual-topology-core",
    "perfumery-art-composition-topology-v1",
    "wood-depth-model-v2",
)

RECOVERY_BASELINE_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "inventory_mutation": False,
    "physical_execution": False,
    "publication": False,
    "purchase": False,
    "release": False,
    "runtime": False,
    "safety": False,
    "scientific": False,
    "sensory": False,
}

RECOVERY_BASELINE_BOUNDARIES = {
    "modeled_oav_is_hedonic_evidence": False,
    "modeled_oav_is_sensory_evidence": False,
    "retained_downstream_artifacts_runtime_installed": False,
    "target_ideal_separate_from_current_inventory": True,
}

RECOVERY_BASELINE_UNTRACKED_PATHS = (
    ".tmp-publish-complexity-solforge/",
    ".tmp-publish-registry/",
    ".tmp-solforge-gate-verifier/",
    ".tmp-solforge-slice-verifier/",
)

RECOVERY_SOURCE_CANDIDATE = {
    "name": "OAV_TIME_DOSE_ERROR_SENTINEL_LITERATURE_BASIS_v1.md",
    "byte_length": 40307,
    "sha256": "1094ef77c35b955ca0b6e13bc4d79981e6c78f2fcbaccaf6d34b5a175fa2e7c9",
}

RECOVERY_DOWNSTREAM_ARTIFACTS = (
    {
        "name": "FLORAL_COVERAGE_FOUNDATION_v2.zip",
        "disposition": "SEMANTIC_REFERENCE_ONLY",
    },
    {
        "name": "COMPLEX_PERFUMERY_OPUS_V_COMPLEXITY_SYSTEM_V1R2_20260811.zip",
        "disposition": "REGRESSION_PROVENANCE_ONLY",
    },
    {
        "name": "Woody_Amber_Musk_Extreme_Research_Bundle_V2.zip",
        "disposition": "SOURCE_TRIAGE_ONLY_OBSOLETE_INVENTORY_V3",
    },
    {
        "name": "Top_Complexity_Microevent_Bundle_v2.zip",
        "disposition": "REJECTED_INGREDIENT_COUNT_TRAP",
    },
    {
        "name": "Perfumery_Formula_Control_Ensemble_v2_1.md",
        "disposition": "PROVENANCE_ONLY_INVENTORY_CONFLICT",
    },
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

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


def _git_output(repo_root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout.strip() if text else result.stdout


def _repository_identity(
    repo_root: Path,
    *,
    repository_commit: str | None,
    repository_branch: str | None,
) -> tuple[str, str]:
    commit = (
        str(_git_output(repo_root, "rev-parse", "HEAD"))
        if repository_commit is None
        else repository_commit.strip().lower()
    )
    branch = (
        str(_git_output(repo_root, "branch", "--show-current"))
        if repository_branch is None
        else " ".join(repository_branch.split())
    )
    if not _GIT_COMMIT_RE.fullmatch(commit):
        raise ValueError("repository_commit must be a 40-character Git commit")
    if not branch:
        raise ValueError("repository_branch must be nonblank")
    _git_output(repo_root, "cat-file", "-e", f"{commit}^{{commit}}")
    return commit, branch


def _git_blob(repo_root: Path, commit: str, relative_path: str) -> bytes:
    return bytes(
        _git_output(repo_root, "show", f"{commit}:{relative_path}", text=False)
    )


def _blob_record(repo_root: Path, commit: str, relative_path: str) -> dict[str, Any]:
    payload = _git_blob(repo_root, commit, relative_path)
    return {
        "path": relative_path,
        "byte_length": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _candidate_expectation(
    value: Mapping[str, object] | None,
) -> dict[str, object]:
    expectation = dict(RECOVERY_SOURCE_CANDIDATE if value is None else value)
    if set(expectation) != {"name", "byte_length", "sha256"}:
        raise ValueError("candidate expectation keys are closed")
    name = expectation["name"]
    byte_length = expectation["byte_length"]
    digest = expectation["sha256"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate name must be nonblank")
    if isinstance(byte_length, bool) or not isinstance(byte_length, int):
        raise TypeError("candidate byte_length must be an integer")
    if byte_length < 0:
        raise ValueError("candidate byte_length must be nonnegative")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ValueError("candidate sha256 must be a lowercase SHA-256 digest")
    return {
        "name": " ".join(name.split()),
        "byte_length": byte_length,
        "sha256": digest,
    }


def _source_candidate_record(
    candidate_path: Path | None,
    expectation: Mapping[str, object],
) -> dict[str, Any]:
    expected = _candidate_expectation(expectation)
    observed_length: int | None = None
    observed_sha256: str | None = None
    blocker: str | None = "SOURCE_CANDIDATE_EXACT_BYTES_UNAVAILABLE"
    if candidate_path is not None and candidate_path.is_file():
        observed_length = candidate_path.stat().st_size
        observed_sha256 = _sha256(candidate_path)
        if (
            candidate_path.name == expected["name"]
            and observed_length == expected["byte_length"]
            and observed_sha256 == expected["sha256"]
        ):
            blocker = None
        else:
            blocker = "SOURCE_CANDIDATE_EXACT_BYTES_MISMATCH"
    return {
        "name": expected["name"],
        "expected_byte_length": expected["byte_length"],
        "expected_sha256": expected["sha256"],
        "observed_byte_length": observed_length,
        "observed_sha256": observed_sha256,
        "exact_bytes_status": (
            "VERIFIED" if blocker is None else "EXACT_BYTES_UNAVAILABLE"
        ),
        "disposition": "SOURCE_CANDIDATE_ONLY",
        "blockers": [] if blocker is None else [blocker],
    }


@lru_cache(maxsize=8)
def _recovery_registry_census_json(repo_root_text: str, commit: str) -> str:
    from engine.perception.complexity_registry import load_complexity_registry

    repo_root = Path(repo_root_text)
    relative = "configs/complexity/complexity_module_registry_v5.json"
    blob = _git_blob(repo_root, commit, relative)
    registry_names = tuple(
        f"configs/complexity/complexity_module_registry_v{version}.json"
        for version in range(1, 6)
    )
    snapshot_paths = set(registry_names)
    registry_blobs: dict[str, bytes] = {}
    for registry_name in registry_names:
        registry_blob = _git_blob(repo_root, commit, registry_name)
        registry_blobs[registry_name] = registry_blob
        payload = json.loads(registry_blob.decode("utf-8"))

        def collect_paths(value: object) -> None:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    if key == "path" and isinstance(item, str):
                        snapshot_paths.add(item)
                    else:
                        collect_paths(item)
            elif isinstance(value, list):
                for item in value:
                    collect_paths(item)

        collect_paths(payload)

    with tempfile.TemporaryDirectory(prefix="perfume-chem-recovery-registry-") as temp:
        snapshot = Path(temp)
        for snapshot_path in sorted(snapshot_paths):
            relative_path = Path(snapshot_path)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            try:
                exact = registry_blobs.get(snapshot_path) or _git_blob(
                    repo_root, commit, snapshot_path
                )
            except subprocess.CalledProcessError:
                continue
            target = snapshot / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(exact)
        registry = load_complexity_registry(snapshot, snapshot / relative)
    blob_sha256 = hashlib.sha256(blob).hexdigest()
    if registry.registry_sha256 != blob_sha256:
        raise ValueError("registry V5 working bytes differ from the baseline commit")
    selected: dict[str, dict[str, Any]] = {}
    for module_id in RECOVERY_BASELINE_MODULES:
        module = registry.module_by_id(module_id)
        selected[module_id] = {
            "state": module.state.value,
            "import_path": module.import_path,
            "runtime_eligible": module.runtime_eligible,
        }
    result = {
        "registry": {
            "path": relative,
            "schema_version": registry.schema_version,
            "sha256": blob_sha256,
        },
        "module_dispositions": selected,
    }
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def _recovery_registry_census(repo_root: Path, commit: str) -> dict[str, Any]:
    return json.loads(
        _recovery_registry_census_json(str(repo_root.resolve()), commit)
    )


def build_recovery_baseline(
    repo_root: Path,
    candidate_path: Path | None,
    *,
    candidate_expectation: Mapping[str, object] | None = None,
    repository_commit: str | None = None,
    repository_branch: str | None = None,
) -> dict[str, Any]:
    """Build the frozen Task 1 baseline without granting scientific authority."""

    root = repo_root.resolve()
    if not (root / "data" / "materials").is_dir():
        raise ValueError("repository root must contain data/materials")
    commit, branch = _repository_identity(
        root,
        repository_commit=repository_commit,
        repository_branch=repository_branch,
    )
    registry = _recovery_registry_census(root, commit)
    expectation = _candidate_expectation(candidate_expectation)
    core = {
        "repository": {"branch": branch, "commit": commit},
        "registry": registry["registry"],
        "module_dispositions": registry["module_dispositions"],
        "source_files": [
            _blob_record(root, commit, relative)
            for relative in RECOVERY_BASELINE_FILES
        ],
        "source_candidate": _source_candidate_record(candidate_path, expectation),
        "downstream_artifacts": [dict(item) for item in RECOVERY_DOWNSTREAM_ARTIFACTS],
        "boundaries": dict(RECOVERY_BASELINE_BOUNDARIES),
        "preserved_untracked_paths": list(RECOVERY_BASELINE_UNTRACKED_PATHS),
        "authority_flags": dict(RECOVERY_BASELINE_AUTHORITY_FLAGS),
    }
    return {
        "schema_version": RECOVERY_BASELINE_SCHEMA_VERSION,
        "acceptance_core": core,
        "acceptance_sha256": _canonical_hash(core),
    }


def _candidate_record_issues(candidate: object) -> list[str]:
    if not isinstance(candidate, Mapping):
        return ["source candidate record is missing or malformed"]
    issues: list[str] = []
    try:
        expected = _candidate_expectation(
            {
                "name": candidate.get("name"),
                "byte_length": candidate.get("expected_byte_length"),
                "sha256": candidate.get("expected_sha256"),
            }
        )
    except (TypeError, ValueError):
        return ["source candidate record is malformed"]
    if candidate.get("disposition") != "SOURCE_CANDIDATE_ONLY":
        issues.append("source candidate disposition is not provenance-only")
    status = candidate.get("exact_bytes_status")
    if status == "VERIFIED":
        if (
            candidate.get("observed_byte_length") != expected["byte_length"]
            or candidate.get("observed_sha256") != expected["sha256"]
            or candidate.get("blockers") != []
        ):
            issues.append("source candidate VERIFIED claim does not match exact bytes")
    elif status == "EXACT_BYTES_UNAVAILABLE":
        blockers = candidate.get("blockers")
        if blockers not in (
            ["SOURCE_CANDIDATE_EXACT_BYTES_UNAVAILABLE"],
            ["SOURCE_CANDIDATE_EXACT_BYTES_MISMATCH"],
        ):
            issues.append("source candidate unavailable state lacks an exact blocker")
    else:
        issues.append("source candidate exact-bytes state is invalid")
    return issues


def validate_recovery_baseline(
    repo_root: Path,
    record: object,
    *,
    candidate_path: Path | None = None,
    candidate_expectation: Mapping[str, object] | None = None,
) -> tuple[str, ...]:
    """Validate a frozen Task 1 record against its bound Git snapshot."""

    if not isinstance(record, Mapping):
        return ("recovery baseline must be a mapping",)
    issues: list[str] = []
    if set(record) != {"schema_version", "acceptance_core", "acceptance_sha256"}:
        issues.append("recovery baseline top-level keys are closed")
    if record.get("schema_version") != RECOVERY_BASELINE_SCHEMA_VERSION:
        issues.append("recovery baseline schema version mismatch")
    core = record.get("acceptance_core")
    if not isinstance(core, Mapping):
        return tuple(issues + ["acceptance_core must be a mapping"])
    core_keys = {
        "repository",
        "registry",
        "module_dispositions",
        "source_files",
        "source_candidate",
        "downstream_artifacts",
        "boundaries",
        "preserved_untracked_paths",
        "authority_flags",
    }
    if set(core) != core_keys:
        issues.append("recovery baseline acceptance_core keys are closed")
    if record.get("acceptance_sha256") != _canonical_hash(core):
        issues.append("acceptance SHA-256 mismatch")

    repository = core.get("repository")
    if not isinstance(repository, Mapping):
        return tuple(issues + ["repository identity is missing or malformed"])
    commit = repository.get("commit")
    branch = repository.get("branch")
    if not isinstance(commit, str) or not _GIT_COMMIT_RE.fullmatch(commit):
        return tuple(issues + ["repository commit is invalid"])
    if not isinstance(branch, str) or not branch.strip():
        issues.append("repository branch is invalid")

    root = repo_root.resolve()
    try:
        expected_source_files = [
            _blob_record(root, commit, relative)
            for relative in RECOVERY_BASELINE_FILES
        ]
    except (OSError, subprocess.CalledProcessError):
        expected_source_files = []
        issues.append("baseline repository snapshot is unavailable")
    if core.get("source_files") != expected_source_files:
        issues.append("source file census mismatch")

    try:
        registry = _recovery_registry_census(root, commit)
    except (OSError, ValueError, subprocess.CalledProcessError):
        registry = None
        issues.append("baseline registry snapshot is unavailable")
    if registry is not None:
        if core.get("registry") != registry["registry"]:
            issues.append("registry census mismatch")
        if core.get("module_dispositions") != registry["module_dispositions"]:
            issues.append("module disposition census mismatch")

    if core.get("authority_flags") != RECOVERY_BASELINE_AUTHORITY_FLAGS:
        issues.append("authority flags are not the required all-false mapping")
    if core.get("boundaries") != RECOVERY_BASELINE_BOUNDARIES:
        issues.append("evidence boundaries do not match the frozen policy")
    if core.get("preserved_untracked_paths") != list(
        RECOVERY_BASELINE_UNTRACKED_PATHS
    ):
        issues.append("preserved untracked path set mismatch")
    if core.get("downstream_artifacts") != [
        dict(item) for item in RECOVERY_DOWNSTREAM_ARTIFACTS
    ]:
        issues.append("downstream artifact dispositions mismatch")

    issues.extend(_candidate_record_issues(core.get("source_candidate")))
    if candidate_path is not None:
        expectation = _candidate_expectation(candidate_expectation)
        expected_candidate = _source_candidate_record(candidate_path, expectation)
        if core.get("source_candidate") != expected_candidate:
            issues.append("source candidate exact-byte census mismatch")
    return tuple(dict.fromkeys(issues))


def write_recovery_baseline(
    record: Mapping[str, object],
    output: Path,
    sha_output: Path,
) -> None:
    """Write a deterministic recovery record and exact-file hash sidecar."""

    payload = (
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    sha_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    sha_output.write_text(f"{digest}  {output.name}\n", encoding="ascii")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recovery-baseline-output", type=Path)
    parser.add_argument("--recovery-baseline-sha-output", type=Path)
    parser.add_argument("--downloads-candidate", type=Path)
    parser.add_argument("--repository-commit")
    parser.add_argument("--repository-branch")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.recovery_baseline_output is not None:
        if args.recovery_baseline_sha_output is None:
            raise ValueError("--recovery-baseline-sha-output is required")
        record = build_recovery_baseline(
            args.repo_root,
            args.downloads_candidate,
            repository_commit=args.repository_commit,
            repository_branch=args.repository_branch,
        )
        write_recovery_baseline(
            record,
            args.recovery_baseline_output,
            args.recovery_baseline_sha_output,
        )
        return 0
    if args.output is None:
        raise ValueError("--output or --recovery-baseline-output is required")
    report = build_inventory(args.repo_root)
    write_inventory(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
