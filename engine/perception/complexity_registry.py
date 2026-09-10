"""Exact-byte registry and non-executing census for complexity artifacts.

The registry classifies bytes; it does not import modules or grant scientific,
formula, sensory, inventory, safety, or release authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")

# A successor record is the only sanctioned way to move a frozen V1 pin
# forward. It never edits the frozen registry: it is anchored to the exact
# value it supersedes, and it must carry the commit, reason, evidence file
# and approving authority that justify the change.
_SUCCESSOR_FIELDS = {
    "module_id",
    "path",
    "superseded_sha256",
    "successor_sha256",
    "commit",
    "reason",
    "evidence",
    "approved_by",
    "approved_at",
}
_RUNTIME_STATES = frozenset({"ACTIVE_CANDIDATE", "MANDATORY_GUARDRAIL"})
_GENERATED_PARTS = frozenset({"__pycache__", ".pytest_cache"})
_GENERATED_SUFFIXES = frozenset({".pyc", ".pyo"})
CURRENT_REGISTRY_PATH = Path("configs/complexity/complexity_module_registry_integration_20260910.json")


class ModuleState(str, Enum):
    ACTIVE_CANDIDATE = "ACTIVE_CANDIDATE"
    MANDATORY_GUARDRAIL = "MANDATORY_GUARDRAIL"
    EVIDENCE_ONLY_NOT_ADMITTED = "EVIDENCE_ONLY_NOT_ADMITTED"
    FUTURE_CANDIDATE_NOT_VALIDATED = "FUTURE_CANDIDATE_NOT_VALIDATED"
    REDUNDANT_NOT_INVOKED = "REDUNDANT_NOT_INVOKED"
    RETIRED_BENCHMARK_UNDERPERFORMER = "RETIRED_BENCHMARK_UNDERPERFORMER"
    NOT_EVALUATED_NO_RELEVANT_CASE = "NOT_EVALUATED_NO_RELEVANT_CASE"


class ModuleRole(str, Enum):
    CAPABILITY = "CAPABILITY"
    GUARDRAIL = "GUARDRAIL"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    module_id: str
    family_id: str
    role: ModuleRole
    state: ModuleState
    path: str
    import_path: str | None
    sha256: str
    evidence_refs: tuple[str, ...]
    notes: tuple[str, ...] = ()

    @property
    def runtime_eligible(self) -> bool:
        return self.state.value in _RUNTIME_STATES and self.import_path is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "family_id": self.family_id,
            "role": self.role.value,
            "state": self.state.value,
            "path": self.path,
            "import_path": self.import_path,
            "sha256": self.sha256,
            "evidence_refs": list(self.evidence_refs),
            "notes": list(self.notes),
            "runtime_eligible": self.runtime_eligible,
        }


@dataclass(frozen=True, slots=True)
class ComplexityRegistry:
    schema_version: str
    discovery: Mapping[str, Any]
    modules: tuple[ModuleDescriptor, ...]
    artifact_rules: tuple[Mapping[str, Any], ...]
    dismissal_rules: tuple[Mapping[str, Any], ...]
    registry_sha256: str

    def modules_for_family(self, family_id: str) -> tuple[ModuleDescriptor, ...]:
        return tuple(item for item in self.modules if item.family_id == family_id)

    def family_role(self, family_id: str) -> ModuleRole:
        roles = {item.role for item in self.modules_for_family(family_id)}
        if len(roles) != 1:
            raise ValueError(f"family {family_id!r} must have exactly one role")
        return roles.pop()

    def module_by_id(self, module_id: str) -> ModuleDescriptor:
        matches = tuple(item for item in self.modules if item.module_id == module_id)
        if len(matches) != 1:
            raise KeyError(module_id)
        return matches[0]


@dataclass(frozen=True, slots=True)
class CensusFinding:
    path: str
    classification: str
    rule_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "classification": self.classification,
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True, slots=True)
class CensusResult:
    state: str
    findings: tuple[CensusFinding, ...]
    hash_drift: tuple[str, ...]
    missing: tuple[str, ...]
    unclassified: tuple[str, ...]
    multiply_classified: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "findings": [item.as_dict() for item in self.findings],
            "hash_drift": list(self.hash_drift),
            "missing": list(self.missing),
            "unclassified": list(self.unclassified),
            "multiply_classified": list(self.multiply_classified),
        }


def _nonblank(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonblank string")
    return value.strip()


def _relative_path(value: Any, field: str = "path") -> str:
    raw = _nonblank(value, field).replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or ":" in raw:
        raise ValueError(f"{field} must be repository-relative")
    normalized = path.as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"{field} must identify a repository-relative file")
    return normalized


def _inside_root(root: Path, relative: str) -> Path:
    candidate = (root / Path(relative)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path must be repository-relative") from exc
    return candidate


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(value)


def _apply_module_successors(
    base: Mapping[str, Any],
    merged: list[Any],
    successors: Any,
    project_root: Path,
) -> list[Any]:
    """Rebind frozen V1 module pins through anchored successor records.

    The frozen registry stays byte-identical. Each record must name the exact
    pin it supersedes, so a successor that does not describe the value in the
    frozen file is rejected rather than silently accepted.
    """
    if not isinstance(successors, list) or not successors:
        raise ValueError("overlay module_successors must be a nonempty list")
    frozen = {row["module_id"]: row for row in base["modules"]}
    seen: set[str] = set()
    rebindings: dict[str, str] = {}
    for record in successors:
        if not isinstance(record, dict) or set(record) != _SUCCESSOR_FIELDS:
            raise ValueError("module successor keys are closed")
        module_id = _nonblank(record["module_id"], "module_id")
        if module_id in seen:
            raise ValueError("module successor must not repeat a module_id")
        seen.add(module_id)
        frozen_row = frozen.get(module_id)
        if frozen_row is None:
            raise ValueError("module successor must target a frozen V1 module")
        if _nonblank(record["path"], "path") != frozen_row["path"]:
            raise ValueError("module successor path must match the frozen V1 module")
        superseded = _nonblank(record["superseded_sha256"], "superseded_sha256")
        if superseded != frozen_row["sha256"]:
            raise ValueError("module successor anchor does not match the frozen V1 pin")
        successor = _nonblank(record["successor_sha256"], "successor_sha256")
        if not _SHA256.fullmatch(successor):
            raise ValueError("module successor hash must be a sha256 hex digest")
        if successor == superseded:
            raise ValueError("module successor must change the pin")
        if not _COMMIT_SHA.fullmatch(_nonblank(record["commit"], "commit")):
            raise ValueError("module successor commit must be a full commit sha")
        _nonblank(record["reason"], "reason")
        _nonblank(record["approved_by"], "approved_by")
        _nonblank(record["approved_at"], "approved_at")
        evidence = _relative_path(record["evidence"], "evidence")
        if not _inside_root(project_root, evidence).is_file():
            raise ValueError("module successor evidence must be an existing file")
        rebindings[module_id] = successor
    updated: list[Any] = []
    for row in merged:
        module_id = row.get("module_id") if isinstance(row, dict) else None
        if module_id in rebindings:
            row = {**row, "sha256": rebindings[module_id]}
        updated.append(row)
    return updated


def _validate_rule(rule: Any, *, dismissal: bool) -> Mapping[str, Any]:
    if not isinstance(rule, dict):
        raise ValueError("registry rules must be objects")
    _nonblank(rule.get("rule_id"), "rule_id")
    selectors = [key for key in ("path_prefix", "path_glob", "path") if key in rule]
    if len(selectors) != 1:
        raise ValueError("each registry rule requires exactly one path selector")
    selector = selectors[0]
    if selector in {"path_prefix", "path"}:
        _relative_path(rule[selector], selector)
    else:
        _nonblank(rule[selector], selector)
    required = "reason" if dismissal else "classification"
    _nonblank(rule.get(required), required)
    return dict(rule)


def load_complexity_registry(root: Path, path: Path) -> ComplexityRegistry:
    project_root = root.resolve()
    registry_path = path if path.is_absolute() else project_root / path
    raw = registry_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("complexity registry must be a JSON object")
    source_schema = _nonblank(payload.get("schema_version"), "schema_version")
    if source_schema == "complexity_module_registry_overlay_v1":
        required_overlay_keys = {
            "schema_version", "base_registry", "base_registry_sha256", "module_additions",
        }
        optional_overlay_keys = {"module_successors"}
        if not required_overlay_keys <= set(payload) or set(payload) - required_overlay_keys - optional_overlay_keys:
            raise ValueError("complexity registry overlay keys are closed")
        base_path = _inside_root(project_root, _relative_path(payload["base_registry"]))
        base_raw = base_path.read_bytes()
        if hashlib.sha256(base_raw).hexdigest() != payload["base_registry_sha256"]:
            raise ValueError("frozen base registry hash mismatch")
        base = json.loads(base_raw.decode("utf-8"))
        if not isinstance(base, dict) or base.get("schema_version") != "complexity_module_registry_v1":
            raise ValueError("overlay base must be a frozen V1 registry")
        additions = payload["module_additions"]
        if not isinstance(additions, list) or not additions:
            raise ValueError("overlay module_additions must be a nonempty list")
        for row in additions:
            if (not isinstance(row, dict)
                    or row.get("state") != "FUTURE_CANDIDATE_NOT_VALIDATED"
                    or row.get("import_path") is not None):
                raise ValueError("overlay additions must be unvalidated non-runtime candidates")
        # Reuse the complete V1 validator below. Its closed fields, duplicate
        # IDs/paths, filesystem containment and census hashes remain mandatory.
        merged_modules: list[Any] = [*base["modules"], *additions]
        if "module_successors" in payload:
            merged_modules = _apply_module_successors(
                base, merged_modules, payload["module_successors"], project_root
            )
        payload = {**base, "modules": merged_modules}
    required = {
        "schema_version",
        "discovery",
        "modules",
        "artifact_rules",
        "dismissal_rules",
    }
    if set(payload) != required:
        raise ValueError("complexity registry top-level keys are closed")
    if payload["schema_version"] != "complexity_module_registry_v1":
        raise ValueError("unsupported complexity registry schema")
    discovery = payload["discovery"]
    if not isinstance(discovery, dict):
        raise ValueError("discovery must be an object")
    roots = _string_tuple(discovery.get("roots"), "discovery.roots")
    terms = _string_tuple(discovery.get("terms"), "discovery.terms")
    metadata_keys = _string_tuple(
        discovery.get("metadata_keys"), "discovery.metadata_keys"
    )
    for discovery_root in roots:
        _relative_path(discovery_root, "discovery root")
    if not terms or any(not item.strip() for item in terms):
        raise ValueError("discovery terms must be nonblank")

    raw_modules = payload["modules"]
    if not isinstance(raw_modules, list) or not raw_modules:
        raise ValueError("modules must be a nonempty list")
    modules: list[ModuleDescriptor] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for row in raw_modules:
        if not isinstance(row, dict):
            raise ValueError("module rows must be objects")
        allowed = {
            "module_id",
            "family_id",
            "role",
            "state",
            "path",
            "import_path",
            "sha256",
            "evidence_refs",
            "notes",
        }
        if not set(row).issubset(allowed):
            raise ValueError("module row contains unknown fields")
        module_id = _nonblank(row.get("module_id"), "module_id")
        family_id = _nonblank(row.get("family_id"), "family_id")
        relative = _relative_path(row.get("path"))
        digest = _nonblank(row.get("sha256"), "sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError(f"module {module_id!r} requires a lowercase SHA-256")
        if module_id in ids or relative.casefold() in paths:
            raise ValueError("module IDs and paths must be unique")
        ids.add(module_id)
        paths.add(relative.casefold())
        try:
            role = ModuleRole(row.get("role"))
            state = ModuleState(row.get("state"))
        except ValueError as exc:
            raise ValueError(f"module {module_id!r} has an unknown role or state") from exc
        import_path = row.get("import_path")
        if import_path is not None:
            import_path = _nonblank(import_path, "import_path")
        if state.value in _RUNTIME_STATES and import_path is None:
            raise ValueError(f"runtime candidate {module_id!r} requires import_path")
        if state.value not in _RUNTIME_STATES and import_path is not None:
            raise ValueError(f"non-runtime module {module_id!r} cannot have import_path")
        module_path = _inside_root(project_root, relative)
        if not module_path.is_file():
            raise ValueError(f"registered module is missing: {relative}")
        modules.append(
            ModuleDescriptor(
                module_id=module_id,
                family_id=family_id,
                role=role,
                state=state,
                path=relative,
                import_path=import_path,
                sha256=digest,
                evidence_refs=_string_tuple(row.get("evidence_refs", []), "evidence_refs"),
                notes=_string_tuple(row.get("notes", []), "notes"),
            )
        )

    artifact_rules = tuple(
        _validate_rule(rule, dismissal=False) for rule in payload["artifact_rules"]
    )
    dismissal_rules = tuple(
        _validate_rule(rule, dismissal=True) for rule in payload["dismissal_rules"]
    )
    rule_ids = [rule["rule_id"] for rule in (*artifact_rules, *dismissal_rules)]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("registry rule IDs must be unique")
    normalized_discovery = {
        "roots": roots,
        "terms": tuple(item.casefold() for item in terms),
        "metadata_keys": metadata_keys,
    }
    return ComplexityRegistry(
        schema_version=source_schema,
        discovery=normalized_discovery,
        modules=tuple(modules),
        artifact_rules=artifact_rules,
        dismissal_rules=dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _rule_matches(path: str, rule: Mapping[str, Any]) -> bool:
    folded = path.casefold()
    if "path" in rule:
        return folded == str(rule["path"]).replace("\\", "/").casefold()
    if "path_prefix" in rule:
        prefix = str(rule["path_prefix"]).replace("\\", "/").rstrip("/") + "/"
        return folded.startswith(prefix.casefold())
    pattern = str(rule["path_glob"]).replace("\\", "/").casefold()
    return fnmatchcase(folded, pattern)


def _metadata_matches(path: Path, terms: tuple[str, ...], keys: tuple[str, ...]) -> bool:
    if path.suffix.casefold() != ".json" or not keys or path.stat().st_size > 2 * 1024 * 1024:
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    values = " ".join(str(payload[key]) for key in keys if key in payload).casefold()
    return any(term in values for term in terms)


def census_complexity_artifacts(
    root: Path,
    registry: ComplexityRegistry,
) -> CensusResult:
    project_root = root.resolve()
    hash_drift: list[str] = []
    missing: list[str] = []
    for registered_module in registry.modules:
        path = _inside_root(project_root, registered_module.path)
        if not path.is_file():
            missing.append(registered_module.path)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != registered_module.sha256:
            hash_drift.append(registered_module.path)

    module_paths = {item.path.casefold(): item for item in registry.modules}
    discovered: set[str] = set()
    terms = tuple(registry.discovery["terms"])
    metadata_keys = tuple(registry.discovery["metadata_keys"])
    for relative_root in registry.discovery["roots"]:
        scan_root = _inside_root(project_root, relative_root)
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(project_root).as_posix()
            parts = {part.casefold() for part in PurePosixPath(relative).parts}
            if parts.intersection(_GENERATED_PARTS) or path.suffix.casefold() in _GENERATED_SUFFIXES:
                continue
            folded = relative.casefold()
            if any(term in folded for term in terms) or _metadata_matches(
                path, terms, metadata_keys
            ):
                discovered.add(relative)

    findings: list[CensusFinding] = []
    unclassified: list[str] = []
    multiply_classified: list[str] = []
    for relative in sorted(discovered, key=str.casefold):
        module = module_paths.get(relative.casefold())
        if module is not None:
            findings.append(
                CensusFinding(relative, module.state.value, f"module:{module.module_id}")
            )
            continue
        matches: list[tuple[str, str]] = []
        for rule in registry.artifact_rules:
            if _rule_matches(relative, rule):
                matches.append((str(rule["classification"]), str(rule["rule_id"])))
        for rule in registry.dismissal_rules:
            if _rule_matches(relative, rule):
                matches.append(("DISMISSED_NON_MODULE", str(rule["rule_id"])))
        if not matches:
            unclassified.append(relative)
        elif len(matches) > 1:
            multiply_classified.append(relative)
        else:
            classification, rule_id = matches[0]
            findings.append(CensusFinding(relative, classification, rule_id))

    blocked = bool(hash_drift or missing or unclassified or multiply_classified)
    return CensusResult(
        state="HOLD" if blocked else "PASS",
        findings=tuple(findings),
        hash_drift=tuple(sorted(hash_drift)),
        missing=tuple(sorted(missing)),
        unclassified=tuple(unclassified),
        multiply_classified=tuple(multiply_classified),
    )
