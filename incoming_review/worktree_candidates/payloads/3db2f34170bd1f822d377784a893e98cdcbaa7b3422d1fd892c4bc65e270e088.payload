"""Exact-byte registry and non-executing census for complexity artifacts.

The registry classifies bytes; it does not import modules or grant scientific,
formula, sensory, inventory, safety, or release authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RUNTIME_STATES = frozenset(
    {"ACTIVE_CANDIDATE", "MANDATORY_GUARDRAIL", "ADMITTED_RUNTIME"}
)
_GENERATED_PARTS = frozenset({"__pycache__", ".pytest_cache"})
_GENERATED_SUFFIXES = frozenset({".pyc", ".pyo"})
CURRENT_COMPLEXITY_REGISTRY_PATH = Path(
    "configs/complexity/complexity_module_registry_v8.json"
)
_V5_ARCHITECTURAL_DELTA_SHA256 = (
    "5c5d43ee138078bffb4d447ff78307572cec9ccc63b55fb9dac3dc4562e4bf60"
)
_V6_ARCHITECTURAL_DELTA_SHA256 = _V5_ARCHITECTURAL_DELTA_SHA256
_V7_ARCHITECTURAL_DELTA_SHA256 = _V6_ARCHITECTURAL_DELTA_SHA256
_V8_ARCHITECTURAL_DELTA_SHA256 = _V7_ARCHITECTURAL_DELTA_SHA256


class ModuleState(str, Enum):
    ACTIVE_CANDIDATE = "ACTIVE_CANDIDATE"
    MANDATORY_GUARDRAIL = "MANDATORY_GUARDRAIL"
    EVIDENCE_ONLY_NOT_ADMITTED = "EVIDENCE_ONLY_NOT_ADMITTED"
    FUTURE_CANDIDATE_NOT_VALIDATED = "FUTURE_CANDIDATE_NOT_VALIDATED"
    REDUNDANT_NOT_INVOKED = "REDUNDANT_NOT_INVOKED"
    RETIRED_BENCHMARK_UNDERPERFORMER = "RETIRED_BENCHMARK_UNDERPERFORMER"
    NOT_EVALUATED_NO_RELEVANT_CASE = "NOT_EVALUATED_NO_RELEVANT_CASE"
    PROVENANCE_TOMBSTONE = "PROVENANCE_TOMBSTONE"
    CATALOG_ONLY = "CATALOG_ONLY"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    EXPERIMENT_COMPILER = "EXPERIMENT_COMPILER"
    SHADOW_VALIDATED = "SHADOW_VALIDATED"
    ADMITTED_RUNTIME = "ADMITTED_RUNTIME"


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


def _module_descriptor_from_row(
    project_root: Path,
    row: Any,
) -> ModuleDescriptor:
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
    return ModuleDescriptor(
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


def _load_registry_overlay(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    required = {
        "schema_version",
        "base_registry",
        "module_overrides",
        "module_additions",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v2 top-level keys are closed")
    base_name = _nonblank(payload.get("base_registry"), "base_registry")
    if Path(base_name).name != base_name:
        raise ValueError("base_registry must be a sibling filename")
    base_path = registry_path.parent / base_name
    if base_path.resolve() == registry_path.resolve():
        raise ValueError("base_registry cannot reference itself")
    base = load_complexity_registry(project_root, base_path)
    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    overrides = payload.get("module_overrides")
    if not isinstance(overrides, list):
        raise ValueError("module_overrides must be a list")
    seen_overrides: set[str] = set()
    override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    for override in overrides:
        if not isinstance(override, dict) or not set(override).issubset(override_fields):
            raise ValueError("module override contains unknown fields")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        if module_id in seen_overrides:
            raise ValueError("module override IDs must be unique")
        seen_overrides.add(module_id)
        if module_id not in index_by_id:
            raise ValueError(f"unknown module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root, row
        )
    additions = payload.get("module_additions")
    if not isinstance(additions, list):
        raise ValueError("module_additions must be a list")
    modules.extend(
        _module_descriptor_from_row(project_root, row) for row in additions
    )
    ids = tuple(item.module_id for item in modules)
    paths = tuple(item.path.casefold() for item in modules)
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("module IDs and paths must be unique")
    return ComplexityRegistry(
        schema_version="complexity_module_registry_v2",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


_V3_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "scientific": False,
    "sensory": False,
}


def _load_registry_v3(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    required = {
        "schema_version",
        "base_registry_chain",
        "module_overrides",
        "module_additions",
        "required_evidence",
        "authority_flags",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v3 top-level keys are closed")
    chain = payload.get("base_registry_chain")
    if not isinstance(chain, list) or len(chain) < 2:
        raise ValueError("base_registry_chain must contain V1 and V2")
    chain_paths: list[Path] = []
    for item in chain:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("base registry chain entries are closed")
        name = _nonblank(item.get("path"), "base registry path")
        if Path(name).name != name:
            raise ValueError("base registry path must be a sibling filename")
        digest = _nonblank(item.get("sha256"), "base registry sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("base registry sha256 must be lower-case SHA-256")
        path = registry_path.parent / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"base registry hash mismatch: {name}")
        chain_paths.append(path)
    if [path.name for path in chain_paths[:2]] != [
        "complexity_module_registry_v1.json",
        "complexity_module_registry_v2.json",
    ]:
        raise ValueError("base registry chain must begin with V1 then V2")
    base = load_complexity_registry(project_root, chain_paths[-1])

    authority = payload.get("authority_flags")
    if authority != _V3_AUTHORITY_FLAGS:
        raise ValueError("V3 authority flags must be the exact all-false mapping")
    evidence = payload.get("required_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("required_evidence must be a nonempty list")
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "sha256",
            "acceptance_sha256",
        }:
            raise ValueError("required evidence entries are closed")
        relative = _relative_path(item.get("path"), "required evidence path")
        digest = _nonblank(item.get("sha256"), "required evidence sha256")
        acceptance = _nonblank(
            item.get("acceptance_sha256"), "required acceptance sha256"
        )
        if not _SHA256.fullmatch(digest) or not _SHA256.fullmatch(acceptance):
            raise ValueError("required evidence hashes must be lower-case SHA-256")
        path = _inside_root(project_root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"required evidence hash mismatch: {relative}")
        evidence_payload = json.loads(path.read_text(encoding="utf-8"))
        if evidence_payload.get("acceptance_sha256") != acceptance:
            raise ValueError(f"required acceptance hash mismatch: {relative}")

    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    overrides = payload.get("module_overrides")
    if not isinstance(overrides, list):
        raise ValueError("module_overrides must be a list")
    seen: set[str] = set()
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    for override in overrides:
        if not isinstance(override, dict) or not set(override).issubset(
            allowed_override_fields
        ):
            raise ValueError("module override contains unknown fields")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        if module_id in seen:
            raise ValueError("module override IDs must be unique")
        seen.add(module_id)
        if module_id not in index_by_id:
            raise ValueError(f"unknown module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root, row
        )
    additions = payload.get("module_additions")
    if not isinstance(additions, list):
        raise ValueError("module_additions must be a list")
    modules.extend(_module_descriptor_from_row(project_root, row) for row in additions)
    ids = tuple(item.module_id for item in modules)
    paths = tuple(item.path.casefold() for item in modules)
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("module IDs and paths must be unique")
    if any(
        module.import_path is not None
        and module.state is not ModuleState.ADMITTED_RUNTIME
        for module in modules
    ):
        raise ValueError("only ADMITTED_RUNTIME may have a V3 import_path")
    return ComplexityRegistry(
        schema_version="complexity_module_registry_v3",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _load_registry_v4(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    required = {
        "schema_version",
        "base_registry_chain",
        "module_overrides",
        "module_additions",
        "source_bindings",
        "authority_flags",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v4 top-level keys are closed")
    chain = payload.get("base_registry_chain")
    expected_names = [
        "complexity_module_registry_v1.json",
        "complexity_module_registry_v2.json",
        "complexity_module_registry_v3.json",
    ]
    if not isinstance(chain, list) or len(chain) != len(expected_names):
        raise ValueError("base_registry_chain must contain exact V1/V2/V3 parents")
    chain_paths: list[Path] = []
    for item in chain:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("base registry chain entries are closed")
        name = _nonblank(item.get("path"), "base registry path")
        if Path(name).name != name:
            raise ValueError("base registry path must be a sibling filename")
        digest = _nonblank(item.get("sha256"), "base registry sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("base registry sha256 must be lower-case SHA-256")
        path = registry_path.parent / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"base registry hash mismatch: {name}")
        chain_paths.append(path)
    if [path.name for path in chain_paths] != expected_names:
        raise ValueError("base registry chain must be exact V1 then V2 then V3")
    base = load_complexity_registry(project_root, chain_paths[-1])

    if payload.get("authority_flags") != _V3_AUTHORITY_FLAGS:
        raise ValueError("V4 authority flags must be the exact all-false mapping")
    source_bindings = payload.get("source_bindings")
    if not isinstance(source_bindings, list) or not source_bindings:
        raise ValueError("source_bindings must be a nonempty list")
    bound_paths: set[str] = set()
    for item in source_bindings:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("source binding entries are closed")
        relative = _relative_path(item.get("path"), "source binding path")
        if relative.casefold() in bound_paths:
            raise ValueError("source binding paths must be unique")
        bound_paths.add(relative.casefold())
        digest = _nonblank(item.get("sha256"), "source binding sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("source binding sha256 must be lower-case SHA-256")
        path = _inside_root(project_root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"source binding hash mismatch: {relative}")

    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    overrides = payload.get("module_overrides")
    if not isinstance(overrides, list):
        raise ValueError("module_overrides must be a list")
    seen: set[str] = set()
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    for override in overrides:
        if not isinstance(override, dict) or not set(override).issubset(
            allowed_override_fields
        ):
            raise ValueError("module override contains unknown fields")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        if module_id in seen:
            raise ValueError("module override IDs must be unique")
        seen.add(module_id)
        if module_id not in index_by_id:
            raise ValueError(f"unknown module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root, row
        )
    additions = payload.get("module_additions")
    if not isinstance(additions, list):
        raise ValueError("module_additions must be a list")
    modules.extend(_module_descriptor_from_row(project_root, row) for row in additions)
    ids = tuple(item.module_id for item in modules)
    paths = tuple(item.path.casefold() for item in modules)
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("module IDs and paths must be unique")
    if any(
        module.import_path is not None
        and module.state is not ModuleState.ADMITTED_RUNTIME
        for module in modules
    ):
        raise ValueError("only ADMITTED_RUNTIME may have a V4 import_path")
    return ComplexityRegistry(
        schema_version="complexity_module_registry_v4",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _load_registry_v5(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    required = {
        "schema_version",
        "base_registry",
        "module_overrides",
        "admission_evidence",
        "runtime_bindings",
        "authority_flags",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v5 top-level keys are closed")
    base_record = payload.get("base_registry")
    if not isinstance(base_record, dict) or set(base_record) != {"path", "sha256"}:
        raise ValueError("base_registry must be one closed path/hash record")
    base_name = _nonblank(base_record.get("path"), "base registry path")
    if base_name != "complexity_module_registry_v4.json":
        raise ValueError("V5 base registry must be the exact V4 sibling")
    base_sha256 = _nonblank(base_record.get("sha256"), "base registry sha256")
    if not _SHA256.fullmatch(base_sha256):
        raise ValueError("base registry sha256 must be lower-case SHA-256")
    base_path = registry_path.parent / base_name
    if not base_path.is_file() or hashlib.sha256(base_path.read_bytes()).hexdigest() != (
        base_sha256
    ):
        raise ValueError("base registry hash mismatch: complexity_module_registry_v4.json")
    base = load_complexity_registry(project_root, base_path)

    if payload.get("authority_flags") != _V3_AUTHORITY_FLAGS:
        raise ValueError("V5 authority flags must be the exact all-false mapping")
    runtime_bindings = payload.get("runtime_bindings")
    expected_runtime_paths = {
        "engine/perception/complexity_registry.py",
        "engine/solforge/runtime.py",
        "scripts/intervention_recommend.py",
    }
    if not isinstance(runtime_bindings, list) or len(runtime_bindings) != len(
        expected_runtime_paths
    ):
        raise ValueError("V5 runtime_bindings must contain three exact records")
    observed_runtime_paths: set[str] = set()
    for item in runtime_bindings:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("runtime binding entries are closed")
        relative = _relative_path(item.get("path"), "runtime binding path")
        if relative in observed_runtime_paths:
            raise ValueError("runtime binding paths must be unique")
        observed_runtime_paths.add(relative)
        digest = _nonblank(item.get("sha256"), "runtime binding sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("runtime binding sha256 must be lower-case SHA-256")
        path = _inside_root(project_root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"runtime binding hash mismatch: {relative}")
    if observed_runtime_paths != expected_runtime_paths:
        raise ValueError("V5 runtime binding paths must be exact")
    evidence_rows = payload.get("admission_evidence")
    if not isinstance(evidence_rows, list) or len(evidence_rows) != 3:
        raise ValueError("V5 admission_evidence must contain three exact records")
    evidence_payloads: dict[str, Mapping[str, Any]] = {}
    for item in evidence_rows:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("admission evidence entries are closed")
        relative = _relative_path(item.get("path"), "admission evidence path")
        if relative in evidence_payloads:
            raise ValueError("admission evidence paths must be unique")
        digest = _nonblank(item.get("sha256"), "admission evidence sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("admission evidence sha256 must be lower-case SHA-256")
        path = _inside_root(project_root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"admission evidence hash mismatch: {relative}")
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(evidence, Mapping):
            raise ValueError("admission evidence must contain one JSON object")
        evidence_payloads[relative] = evidence

    screen_path = (
        "data/benchmarks/solforge/replacement_screen_v6_r1/"
        "status.normalized_v2.json"
    )
    confirmation_result_path = (
        "data/benchmarks/solforge/replacement_confirmation_v6_r1/"
        "confirmation_result.serialized_v2.json"
    )
    confirmation_status_path = (
        "data/benchmarks/solforge/replacement_confirmation_v6_r1/"
        "status.serialized_v2.json"
    )
    if set(evidence_payloads) != {
        screen_path,
        confirmation_result_path,
        confirmation_status_path,
    }:
        raise ValueError("V5 admission evidence paths must be exact")
    screen = evidence_payloads[screen_path]
    if (
        screen.get("state") != "SCREEN_COMPLETE"
        or screen.get("proceed_modules") != ["architectural_delta"]
        or set(screen.get("stopped_modules", ()))
        != {"temporal_sensory_ledger", "hedonic_preference_learner"}
        or screen.get("runtime_reachable") is not False
    ):
        raise ValueError("V5 screen evidence does not admit only architectural delta")
    confirmation_status = evidence_payloads[confirmation_status_path]
    if (
        confirmation_status.get("state") != "CONFIRMATION_COMPLETE"
        or confirmation_status.get("admitted_modules") != ["architectural_delta"]
        or confirmation_status.get("runtime_integration_authorized_by_gate") is not True
        or confirmation_status.get("runtime_reachable") is not False
    ):
        raise ValueError("V5 confirmation status is not admission-complete")
    confirmation = evidence_payloads[confirmation_result_path]
    decisions = confirmation.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 1:
        raise ValueError("V5 confirmation must contain one module decision")
    decision = decisions[0]
    if (
        not isinstance(decision, Mapping)
        or decision.get("module_id") != "architectural_delta"
        or decision.get("state") != "ADMITTED"
        or decision.get("reasons") != []
    ):
        raise ValueError("V5 architectural decision is not admitted")
    for control_name in ("plain_control", "placebo"):
        control = decision.get(control_name)
        if not isinstance(control, Mapping):
            raise ValueError("V5 confirmation control summary is missing")
        try:
            median_gain = Decimal(str(control.get("median_paired_delta")))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("V5 confirmation median gain is invalid") from exc
        if (
            control.get("state") != "REACTIVATE"
            or control.get("treatment_wins", 0) < 4
            or median_gain < Decimal("5")
            or control.get("reasons") != []
        ):
            raise ValueError("V5 confirmation control gate did not pass")

    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    overrides = payload.get("module_overrides")
    expected_override_ids = {
        "advanced-musk-intelligence",
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    }
    if not isinstance(overrides, list) or {
        item.get("module_id") for item in overrides if isinstance(item, dict)
    } != expected_override_ids:
        raise ValueError(
            "V5 module overrides must cover the three replacements and the "
            "nonruntime musk provenance rebind exactly"
        )
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    for override in overrides:
        if not isinstance(override, dict) or set(override) != allowed_override_fields:
            raise ValueError("V5 module override schema is closed")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root, row
        )
    runtime_modules = tuple(module for module in modules if module.runtime_eligible)
    if len(runtime_modules) != 1 or runtime_modules[0].module_id != (
        "architectural-delta-engine"
    ):
        raise ValueError("V5 may admit only architectural-delta-engine")
    architecture = runtime_modules[0]
    if (
        architecture.state is not ModuleState.ADMITTED_RUNTIME
        or architecture.import_path != "engine.perception.architectural_delta"
        or architecture.sha256 != _V5_ARCHITECTURAL_DELTA_SHA256
    ):
        raise ValueError("V5 architectural runtime binding is invalid")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = modules[index_by_id[module_id]]
        if (
            module.state is not ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
            or module.import_path is not None
        ):
            raise ValueError("V5 underperformers must remain runtime-unreachable")
    advanced_musk = modules[index_by_id["advanced-musk-intelligence"]]
    if (
        advanced_musk.state is not ModuleState.FUTURE_CANDIDATE_NOT_VALIDATED
        or advanced_musk.import_path is not None
        or advanced_musk.runtime_eligible
    ):
        raise ValueError("V5 musk provenance rebind must remain runtime-unreachable")
    return ComplexityRegistry(
        schema_version="complexity_module_registry_v5",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _load_registry_v6(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    required = {
        "schema_version",
        "change_class",
        "predecessor_registry_chain",
        "base_registry",
        "module_overrides",
        "screen_evidence",
        "runtime_bindings",
        "provenance_bindings",
        "authority_flags",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v6 top-level keys are closed")
    if payload.get("change_class") != "RUNTIME_ISOLATION_REPAIR_NO_NEW_ADMISSION":
        raise ValueError("V6 change class must deny new admission")

    chain = payload.get("predecessor_registry_chain")
    expected_names = [
        f"complexity_module_registry_v{version}.json" for version in range(1, 6)
    ]
    if not isinstance(chain, list) or len(chain) != len(expected_names):
        raise ValueError("V6 predecessor chain must contain exact V1 through V5")
    chain_paths: dict[str, Path] = {}
    for expected_name, item in zip(expected_names, chain, strict=True):
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V6 predecessor entries are closed")
        name = _nonblank(item.get("path"), "predecessor path")
        if name != expected_name:
            raise ValueError("V6 predecessor order must be exact V1 through V5")
        digest = _nonblank(item.get("sha256"), "predecessor sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("V6 predecessor sha256 must be lower-case SHA-256")
        path = registry_path.parent / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"V6 predecessor hash mismatch: {name}")
        chain_paths[name] = path

    base_record = payload.get("base_registry")
    if not isinstance(base_record, dict) or set(base_record) != {"path", "sha256"}:
        raise ValueError("V6 base registry must be one closed record")
    if base_record.get("path") != "complexity_module_registry_v3.json":
        raise ValueError("V6 must reconstruct from the last source-stable V3 registry")
    if base_record.get("sha256") != next(
        item["sha256"]
        for item in chain
        if item["path"] == "complexity_module_registry_v3.json"
    ):
        raise ValueError("V6 base registry must match the frozen V3 predecessor")
    base = load_complexity_registry(
        project_root,
        chain_paths["complexity_module_registry_v3.json"],
    )

    if payload.get("authority_flags") != _V3_AUTHORITY_FLAGS:
        raise ValueError("V6 authority flags must be the exact all-false mapping")

    evidence_rows = payload.get("screen_evidence")
    expected_evidence_paths = {
        "tests/fixtures/complexity_replacement_benchmark_cases_v8.json",
        "data/benchmarks/solforge/evidence_foundation_screen_v2/effective_manifest.json",
        "data/benchmarks/solforge/evidence_foundation_screen_v2/execution_receipt.json",
        "data/benchmarks/solforge/evidence_foundation_screen_v2/receipt.json",
        "data/benchmarks/solforge/evidence_foundation_screen_v2/screen_decisions.json",
    }
    if not isinstance(evidence_rows, list) or len(evidence_rows) != len(
        expected_evidence_paths
    ):
        raise ValueError("V6 screen evidence must contain five exact records")
    evidence_payloads: dict[str, Mapping[str, Any]] = {}
    for item in evidence_rows:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V6 screen evidence entries are closed")
        relative = _relative_path(item.get("path"), "screen evidence path")
        digest = _nonblank(item.get("sha256"), "screen evidence sha256")
        if not _SHA256.fullmatch(digest):
            raise ValueError("V6 screen evidence sha256 must be lower-case SHA-256")
        path = _inside_root(project_root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"V6 screen evidence hash mismatch: {relative}")
        parsed = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, Mapping):
            raise ValueError("V6 screen evidence must contain one JSON object")
        evidence_payloads[relative] = parsed
    if set(evidence_payloads) != expected_evidence_paths:
        raise ValueError("V6 screen evidence paths must be exact")
    decisions = evidence_payloads[
        "data/benchmarks/solforge/evidence_foundation_screen_v2/screen_decisions.json"
    ]
    decision_rows = decisions.get("decisions")
    expected_failed_ids = {
        "temporal_oav_error_sentinel",
        "temporal_sensory_ledger",
        "hedonic_preference_learner",
    }
    if (
        not isinstance(decision_rows, list)
        or {row.get("module_id") for row in decision_rows if isinstance(row, Mapping)}
        != expected_failed_ids
        or any(row.get("state") != "STOP" for row in decision_rows)
    ):
        raise ValueError("V6 screen evidence must stop every evidence candidate")

    runtime_rows = payload.get("runtime_bindings")
    expected_runtime_paths = {
        "engine/perception/complexity_registry.py",
        "engine/perception/architectural_delta.py",
        "engine/solforge/architectural_adapter.py",
        "engine/solforge/runtime.py",
        "scripts/intervention_recommend.py",
    }
    if not isinstance(runtime_rows, list) or len(runtime_rows) != len(
        expected_runtime_paths
    ):
        raise ValueError("V6 runtime bindings must contain five exact records")
    observed_runtime_paths: set[str] = set()
    for item in runtime_rows:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V6 runtime binding entries are closed")
        relative = _relative_path(item.get("path"), "runtime binding path")
        digest = _nonblank(item.get("sha256"), "runtime binding sha256")
        path = _inside_root(project_root, relative)
        if (
            not _SHA256.fullmatch(digest)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"V6 runtime binding hash mismatch: {relative}")
        observed_runtime_paths.add(relative)
    if observed_runtime_paths != expected_runtime_paths:
        raise ValueError("V6 runtime binding paths must be exact")

    provenance_rows = payload.get("provenance_bindings")
    expected_provenance_paths = {
        "engine/hedonic_evidence.py",
        "engine/hedonic_model.py",
        "engine/pipeline/oav_evidence.py",
        "engine/preference.py",
        "engine/preference_davidson.py",
        "engine/preference_validation.py",
        "engine/sensory/ledger.py",
        "engine/solforge/adapters.py",
        "engine/solforge/orchestrator.py",
    }
    if not isinstance(provenance_rows, list) or len(provenance_rows) != len(
        expected_provenance_paths
    ):
        raise ValueError("V6 provenance bindings must contain nine exact records")
    observed_provenance_paths: set[str] = set()
    for item in provenance_rows:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V6 provenance binding entries are closed")
        relative = _relative_path(item.get("path"), "provenance binding path")
        digest = _nonblank(item.get("sha256"), "provenance binding sha256")
        path = _inside_root(project_root, relative)
        if (
            not _SHA256.fullmatch(digest)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"V6 provenance binding hash mismatch: {relative}")
        observed_provenance_paths.add(relative)
    if observed_provenance_paths != expected_provenance_paths:
        raise ValueError("V6 provenance binding paths must be exact")
    if observed_runtime_paths.intersection(observed_provenance_paths):
        raise ValueError("V6 runtime and provenance bindings must be disjoint")

    overrides = payload.get("module_overrides")
    expected_override_ids = {
        "advanced-musk-intelligence",
        "architectural-delta-engine",
        "hedonic-evidence-gate-v2",
        "hedonic-model-future",
        "hedonic-preference-learner",
        "solforge-shadow-orchestrator",
        "temporal-sensory-ledger",
    }
    if not isinstance(overrides, list) or {
        item.get("module_id") for item in overrides if isinstance(item, dict)
    } != expected_override_ids:
        raise ValueError("V6 module overrides must cover the exact isolation set")
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    for override in overrides:
        if not isinstance(override, dict) or set(override) != allowed_override_fields:
            raise ValueError("V6 module override schema is closed")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        if module_id not in index_by_id:
            raise ValueError(f"unknown V6 module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root,
            row,
        )

    runtime_modules = tuple(module for module in modules if module.runtime_eligible)
    if tuple(module.module_id for module in runtime_modules) != (
        "architectural-delta-engine",
    ):
        raise ValueError("V6 may retain only architectural-delta-engine at runtime")
    architecture = runtime_modules[0]
    if (
        architecture.state is not ModuleState.ADMITTED_RUNTIME
        or architecture.import_path != "engine.perception.architectural_delta"
        or architecture.sha256 != _V6_ARCHITECTURAL_DELTA_SHA256
    ):
        raise ValueError("V6 architectural runtime binding is invalid")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = modules[index_by_id[module_id]]
        if (
            module.state is not ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
            or module.import_path is not None
        ):
            raise ValueError("V6 underperformers must remain runtime-unreachable")
    shadow = modules[index_by_id["solforge-shadow-orchestrator"]]
    if shadow.state is not ModuleState.PROVENANCE_TOMBSTONE or shadow.import_path:
        raise ValueError("V6 full shadow orchestrator must be a provenance tombstone")

    return ComplexityRegistry(
        schema_version="complexity_module_registry_v6",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _load_registry_v7(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    """Load the post-retest registry while preserving V6 as frozen provenance."""

    required = {
        "schema_version",
        "change_class",
        "predecessor_registry_chain",
        "base_registry",
        "module_overrides",
        "benchmark_evidence",
        "runtime_bindings",
        "provenance_bindings",
        "authority_flags",
    }
    if set(payload) != required:
        raise ValueError("complexity registry v7 top-level keys are closed")
    if payload.get("change_class") != "BENCHMARK_RETEST_TOMBSTONES_NO_NEW_ADMISSION":
        raise ValueError("V7 change class must deny new admission")

    chain = payload.get("predecessor_registry_chain")
    expected_names = [
        f"complexity_module_registry_v{version}.json" for version in range(1, 7)
    ]
    if not isinstance(chain, list) or len(chain) != len(expected_names):
        raise ValueError("V7 predecessor chain must contain exact V1 through V6")
    chain_paths: dict[str, Path] = {}
    for expected_name, item in zip(expected_names, chain, strict=True):
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V7 predecessor entries are closed")
        name = _nonblank(item.get("path"), "predecessor path")
        digest = _nonblank(item.get("sha256"), "predecessor sha256")
        if name != expected_name or not _SHA256.fullmatch(digest):
            raise ValueError("V7 predecessor order or hash syntax is invalid")
        path = registry_path.parent / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"V7 predecessor hash mismatch: {name}")
        chain_paths[name] = path

    base_record = payload.get("base_registry")
    if not isinstance(base_record, dict) or set(base_record) != {"path", "sha256"}:
        raise ValueError("V7 base registry must be one closed record")
    if base_record.get("path") != "complexity_module_registry_v3.json":
        raise ValueError("V7 must reconstruct from the source-stable V3 registry")
    if base_record.get("sha256") != next(
        item["sha256"]
        for item in chain
        if item["path"] == "complexity_module_registry_v3.json"
    ):
        raise ValueError("V7 base registry must match the frozen V3 predecessor")
    base = load_complexity_registry(
        project_root,
        chain_paths["complexity_module_registry_v3.json"],
    )
    if payload.get("authority_flags") != _V3_AUTHORITY_FLAGS:
        raise ValueError("V7 authority flags must be the exact all-false mapping")

    def validate_bindings(
        field_name: str,
        expected_paths: set[str],
    ) -> dict[str, Path]:
        rows = payload.get(field_name)
        if not isinstance(rows, list) or len(rows) != len(expected_paths):
            raise ValueError(f"V7 {field_name} must contain exact records")
        observed: dict[str, Path] = {}
        for item in rows:
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                raise ValueError(f"V7 {field_name} entries are closed")
            relative = _relative_path(item.get("path"), f"{field_name} path")
            digest = _nonblank(item.get("sha256"), f"{field_name} sha256")
            path = _inside_root(project_root, relative)
            if (
                not _SHA256.fullmatch(digest)
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest
            ):
                raise ValueError(f"V7 {field_name} hash mismatch: {relative}")
            observed[relative] = path
        if set(observed) != expected_paths:
            raise ValueError(f"V7 {field_name} paths must be exact")
        return observed

    benchmark_paths = {
        "data/governance/protected_evidence_retest_admission_v1.json",
        "data/governance/protected_evidence_retest_admission_v1.sha256",
    }
    benchmark = validate_bindings("benchmark_evidence", benchmark_paths)
    status_path = benchmark[
        "data/governance/protected_evidence_retest_admission_v1.json"
    ]
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if (
        not isinstance(status, Mapping)
        or status.get("decision")
        != "ARCHITECTURAL_ONLY_TEMPORAL_AND_HEDONIC_RETIRED"
    ):
        raise ValueError("V7 benchmark evidence must retain architectural-only runtime")
    dispositions = status.get("module_dispositions")
    if not isinstance(dispositions, Mapping):
        raise ValueError("V7 benchmark evidence lacks module dispositions")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        disposition = dispositions.get(module_id)
        if (
            not isinstance(disposition, Mapping)
            or disposition.get("state") != "RETIRED_BENCHMARK_UNDERPERFORMER"
            or disposition.get("runtime_reachable") is not False
        ):
            raise ValueError("V7 failed evidence modules must remain retired")

    runtime_paths = {
        "engine/perception/complexity_registry.py",
        "engine/perception/architectural_delta.py",
        "engine/solforge/architectural_adapter.py",
        "engine/solforge/runtime.py",
        "scripts/intervention_recommend.py",
    }
    runtime = validate_bindings("runtime_bindings", runtime_paths)
    provenance_paths = {
        "engine/hedonic_evidence.py",
        "engine/hedonic_model.py",
        "engine/pipeline/oav_evidence.py",
        "engine/preference.py",
        "engine/preference_davidson.py",
        "engine/preference_validation.py",
        "engine/sensory/ledger.py",
        "engine/solforge/adapters.py",
        "engine/solforge/orchestrator.py",
        "engine/solforge/protected_evidence.py",
        "engine/solforge/protected_evidence_corpus.py",
    }
    provenance = validate_bindings("provenance_bindings", provenance_paths)
    if set(runtime).intersection(provenance):
        raise ValueError("V7 runtime and provenance bindings must be disjoint")

    overrides = payload.get("module_overrides")
    expected_override_ids = {
        "advanced-musk-intelligence",
        "architectural-delta-engine",
        "hedonic-evidence-gate-v2",
        "hedonic-model-future",
        "hedonic-preference-learner",
        "solforge-shadow-orchestrator",
        "temporal-sensory-ledger",
    }
    if not isinstance(overrides, list) or {
        item.get("module_id") for item in overrides if isinstance(item, dict)
    } != expected_override_ids:
        raise ValueError("V7 module overrides must cover the exact isolation set")
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    for override in overrides:
        if not isinstance(override, dict) or set(override) != allowed_override_fields:
            raise ValueError("V7 module override schema is closed")
        module_id = _nonblank(override.get("module_id"), "module override module_id")
        if module_id not in index_by_id:
            raise ValueError(f"unknown V7 module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root,
            row,
        )

    runtime_modules = tuple(module for module in modules if module.runtime_eligible)
    if tuple(module.module_id for module in runtime_modules) != (
        "architectural-delta-engine",
    ):
        raise ValueError("V7 may retain only architectural-delta-engine at runtime")
    architecture = runtime_modules[0]
    if (
        architecture.state is not ModuleState.ADMITTED_RUNTIME
        or architecture.import_path != "engine.perception.architectural_delta"
        or architecture.sha256 != _V7_ARCHITECTURAL_DELTA_SHA256
    ):
        raise ValueError("V7 architectural runtime binding is invalid")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = modules[index_by_id[module_id]]
        if (
            module.state is not ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
            or module.import_path is not None
        ):
            raise ValueError("V7 underperformers must remain runtime-unreachable")
    shadow = modules[index_by_id["solforge-shadow-orchestrator"]]
    if shadow.state is not ModuleState.PROVENANCE_TOMBSTONE or shadow.import_path:
        raise ValueError("V7 full shadow orchestrator must remain a tombstone")

    return ComplexityRegistry(
        schema_version="complexity_module_registry_v7",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _load_registry_v8(
    project_root: Path,
    registry_path: Path,
    raw: bytes,
    payload: Mapping[str, Any],
) -> ComplexityRegistry:
    expected_fields = {
        "schema_version",
        "change_class",
        "base_registry",
        "benchmark_evidence",
        "runtime_bindings",
        "provenance_bindings",
        "provenance_rebindings",
        "module_overrides",
        "authority_flags",
    }
    if set(payload) != expected_fields:
        raise ValueError("V8 registry schema is closed")
    if payload.get("change_class") != "TOPOLOGY_SCREEN_TOMBSTONES_NO_NEW_ADMISSION":
        raise ValueError("V8 change class is invalid")

    base_record = payload.get("base_registry")
    if not isinstance(base_record, dict) or set(base_record) != {"path", "sha256"}:
        raise ValueError("V8 base registry must be one closed record")
    if base_record.get("path") != "complexity_module_registry_v7.json":
        raise ValueError("V8 must overlay the frozen V7 registry")
    base_path = registry_path.parent / "complexity_module_registry_v7.json"
    base_digest = _nonblank(base_record.get("sha256"), "V8 base registry sha256")
    if (
        not _SHA256.fullmatch(base_digest)
        or not base_path.is_file()
        or hashlib.sha256(base_path.read_bytes()).hexdigest() != base_digest
    ):
        raise ValueError("V8 base registry hash mismatch")
    frozen_v7 = json.loads(base_path.read_text(encoding="utf-8"))
    if (
        not isinstance(frozen_v7, Mapping)
        or frozen_v7.get("schema_version") != "complexity_module_registry_v7"
    ):
        raise ValueError("V8 base registry must be the frozen V7 overlay")
    v7_base_record = frozen_v7.get("base_registry")
    if (
        not isinstance(v7_base_record, Mapping)
        or v7_base_record.get("path") != "complexity_module_registry_v3.json"
    ):
        raise ValueError("V8 frozen V7 overlay must reconstruct from V3")
    v3_path = registry_path.parent / "complexity_module_registry_v3.json"
    v3_digest = _nonblank(v7_base_record.get("sha256"), "V8 V3 base sha256")
    if (
        not _SHA256.fullmatch(v3_digest)
        or not v3_path.is_file()
        or hashlib.sha256(v3_path.read_bytes()).hexdigest() != v3_digest
    ):
        raise ValueError("V8 frozen V3 base hash mismatch")
    base = load_complexity_registry(project_root, v3_path)
    if base.schema_version != "complexity_module_registry_v3":
        raise ValueError("V8 frozen base must resolve to V3")

    modules = list(base.modules)
    index_by_id = {item.module_id: index for index, item in enumerate(modules)}
    v7_overrides = frozen_v7.get("module_overrides")
    v7_override_fields = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    if not isinstance(v7_overrides, list):
        raise ValueError("V8 frozen V7 overrides are missing")
    for override in v7_overrides:
        if not isinstance(override, dict) or set(override) != v7_override_fields:
            raise ValueError("V8 frozen V7 override schema is invalid")
        module_id = _nonblank(override.get("module_id"), "V8 frozen V7 module_id")
        if module_id not in index_by_id:
            raise ValueError(f"unknown frozen V7 module override: {module_id}")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root,
            row,
        )
    if payload.get("authority_flags") != _V3_AUTHORITY_FLAGS:
        raise ValueError("V8 authority flags must be the exact all-false mapping")

    expected_evidence_paths = {
        "data/governance/protected_evidence_retest_admission_v1.json",
        "data/governance/protected_evidence_retest_admission_v1.sha256",
        "data/governance/topology_xhigh_screen_20260827_v1.json",
        "data/governance/topology_xhigh_screen_20260827_v1.sha256",
    }
    evidence = payload.get("benchmark_evidence")
    if not isinstance(evidence, list) or len(evidence) != len(expected_evidence_paths):
        raise ValueError("V8 benchmark evidence must contain exact records")
    evidence_paths: dict[str, Path] = {}
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("V8 benchmark evidence entries are closed")
        relative = _relative_path(item.get("path"), "V8 benchmark evidence path")
        digest = _nonblank(item.get("sha256"), "V8 benchmark evidence sha256")
        path = _inside_root(project_root, relative)
        if (
            relative not in expected_evidence_paths
            or not _SHA256.fullmatch(digest)
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"V8 benchmark evidence hash mismatch: {relative}")
        evidence_paths[relative] = path
    if set(evidence_paths) != expected_evidence_paths:
        raise ValueError("V8 benchmark evidence paths must be exact")

    prior_status_path = evidence_paths[
        "data/governance/protected_evidence_retest_admission_v1.json"
    ]
    prior_status = json.loads(prior_status_path.read_text(encoding="utf-8"))
    if (
        not isinstance(prior_status, Mapping)
        or prior_status.get("decision")
        != "ARCHITECTURAL_ONLY_TEMPORAL_AND_HEDONIC_RETIRED"
    ):
        raise ValueError("V8 must preserve the V7 architectural-only decision")
    prior_dispositions = prior_status.get("module_dispositions")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        disposition = (
            prior_dispositions.get(module_id)
            if isinstance(prior_dispositions, Mapping)
            else None
        )
        if (
            not isinstance(disposition, Mapping)
            or disposition.get("state") != "RETIRED_BENCHMARK_UNDERPERFORMER"
            or disposition.get("runtime_reachable") is not False
        ):
            raise ValueError("V8 must preserve V7 evidence-module retirement")

    receipt_path = evidence_paths[
        "data/governance/topology_xhigh_screen_20260827_v1.json"
    ]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("decision")
        != "TOPOLOGY_CANDIDATES_RETAINED_AS_PROVENANCE_TOMBSTONES"
        or receipt.get("confirmation", {}).get("state")
        != "NOT_RUN_SCREEN_GATE_FAILED"
        or receipt.get("raw_conversations_committed") is not False
    ):
        raise ValueError("V8 receipt must record corrected non-admission")
    receipt_authority = receipt.get("authority")
    if not isinstance(receipt_authority, Mapping) or not receipt_authority or any(
        value is not False for value in receipt_authority.values()
    ):
        raise ValueError("V8 receipt authority must remain all false")
    dispositions = receipt.get("module_dispositions")
    topology_ids = {
        "universal-perceptual-topology-core",
        "perfumery-art-composition-topology-v1",
        "wood-depth-model-v2",
    }
    if not isinstance(dispositions, Mapping) or set(dispositions) != topology_ids:
        raise ValueError("V8 receipt must cover the exact topology candidates")
    for disposition in dispositions.values():
        if (
            not isinstance(disposition, Mapping)
            or disposition.get("screen_state") != "FAILED"
            or disposition.get("runtime_state") != "PROVENANCE_TOMBSTONE"
            or disposition.get("runtime_reachable") is not False
        ):
            raise ValueError("V8 topology candidates must remain tombstoned")

    sidecar_path = evidence_paths[
        "data/governance/topology_xhigh_screen_20260827_v1.sha256"
    ]
    expected_sidecar = (
        f"{hashlib.sha256(receipt_path.read_bytes()).hexdigest()}  "
        f"{receipt_path.name}\n"
    )
    if sidecar_path.read_text(encoding="utf-8") != expected_sidecar:
        raise ValueError("V8 receipt sidecar does not bind the receipt")

    def validate_bindings(
        field_name: str,
        expected_paths: set[str],
    ) -> dict[str, Path]:
        rows = payload.get(field_name)
        if not isinstance(rows, list) or len(rows) != len(expected_paths):
            raise ValueError(f"V8 {field_name} must contain exact records")
        observed: dict[str, Path] = {}
        for item in rows:
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                raise ValueError(f"V8 {field_name} entries are closed")
            relative = _relative_path(item.get("path"), f"V8 {field_name} path")
            digest = _nonblank(item.get("sha256"), f"V8 {field_name} sha256")
            path = _inside_root(project_root, relative)
            if (
                relative not in expected_paths
                or not _SHA256.fullmatch(digest)
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest
            ):
                raise ValueError(f"V8 {field_name} hash mismatch: {relative}")
            observed[relative] = path
        if set(observed) != expected_paths:
            raise ValueError(f"V8 {field_name} paths must be exact")
        return observed

    runtime_paths = {
        "engine/perception/complexity_registry.py",
        "engine/perception/architectural_delta.py",
        "engine/solforge/architectural_adapter.py",
        "engine/solforge/runtime.py",
        "scripts/intervention_recommend.py",
    }
    provenance_paths = {
        ".gitattributes",
        "engine/hedonic_evidence.py",
        "engine/hedonic_model.py",
        "engine/pipeline/oav_evidence.py",
        "engine/preference.py",
        "engine/preference_davidson.py",
        "engine/preference_validation.py",
        "engine/sensory/ledger.py",
        "engine/solforge/adapters.py",
        "engine/solforge/orchestrator.py",
        "engine/solforge/protected_evidence.py",
        "engine/solforge/protected_evidence_corpus.py",
    }
    runtime = validate_bindings("runtime_bindings", runtime_paths)
    provenance = validate_bindings("provenance_bindings", provenance_paths)
    if set(runtime).intersection(provenance):
        raise ValueError("V8 runtime and provenance bindings must be disjoint")

    rebindings = payload.get("provenance_rebindings")
    rebind_fields = {
        "module_id",
        "path",
        "old_sha256",
        "sha256",
        "reason",
    }
    if not isinstance(rebindings, list) or len(rebindings) != 1:
        raise ValueError("V8 must declare one provenance line-ending rebinding")
    rebinding = rebindings[0]
    if not isinstance(rebinding, dict) or set(rebinding) != rebind_fields:
        raise ValueError("V8 provenance rebinding schema is closed")
    module_id = _nonblank(rebinding.get("module_id"), "V8 rebound module_id")
    relative = _relative_path(rebinding.get("path"), "V8 rebound path")
    old_digest = _nonblank(rebinding.get("old_sha256"), "V8 rebound old sha256")
    digest = _nonblank(rebinding.get("sha256"), "V8 rebound sha256")
    if (
        module_id != "hedonic-model-future"
        or relative != "engine/hedonic_model.py"
        or rebinding.get("reason") != "GIT_CANONICAL_LF_REBIND"
        or not _SHA256.fullmatch(old_digest)
        or not _SHA256.fullmatch(digest)
    ):
        raise ValueError("V8 provenance rebinding is invalid")
    module = modules[index_by_id[module_id]]
    canonical_bytes = provenance[relative].read_bytes()
    attributes = set(
        provenance[".gitattributes"].read_text(encoding="utf-8").splitlines()
    )
    required_lf_rules = {
        "/engine/hedonic_model.py text eol=lf",
        "/data/governance/topology_xhigh_screen*.json text eol=lf",
        "/data/governance/topology_xhigh_screen*.sha256 text eol=lf",
    }
    if (
        module.path != relative
        or module.sha256 != old_digest
        or hashlib.sha256(canonical_bytes).hexdigest() != digest
        or b"\r\n" in canonical_bytes
        or not required_lf_rules.issubset(attributes)
    ):
        raise ValueError("V8 provenance rebinding must use Git-canonical LF bytes")
    row = module.as_dict()
    row.pop("runtime_eligible")
    row["sha256"] = digest
    modules[index_by_id[module_id]] = _module_descriptor_from_row(
        project_root,
        row,
    )

    overrides = payload.get("module_overrides")
    allowed_override_fields = {
        "module_id",
        "state",
        "import_path",
        "path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    if not isinstance(overrides, list) or {
        item.get("module_id") for item in overrides if isinstance(item, dict)
    } != topology_ids:
        raise ValueError("V8 module overrides must cover the exact topology set")

    for override in overrides:
        if not isinstance(override, dict) or set(override) != allowed_override_fields:
            raise ValueError("V8 module override schema is closed")
        module_id = _nonblank(override.get("module_id"), "V8 module_id")
        if module_id not in index_by_id:
            raise ValueError(f"unknown V8 module override: {module_id}")
        if (
            override.get("state") != "PROVENANCE_TOMBSTONE"
            or override.get("import_path") is not None
            or override.get("evidence_refs")
            != ["data/governance/topology_xhigh_screen_20260827_v1.json"]
        ):
            raise ValueError("V8 topology override must be a receipt-bound tombstone")
        row = modules[index_by_id[module_id]].as_dict()
        row.pop("runtime_eligible")
        if override.get("path") != row["path"]:
            raise ValueError("V8 topology override may not change source path")
        row.update(override)
        modules[index_by_id[module_id]] = _module_descriptor_from_row(
            project_root,
            row,
        )

    runtime_modules = tuple(module for module in modules if module.runtime_eligible)
    if tuple(module.module_id for module in runtime_modules) != (
        "architectural-delta-engine",
    ):
        raise ValueError("V8 may retain only architectural-delta-engine at runtime")
    architecture = runtime_modules[0]
    if (
        architecture.state is not ModuleState.ADMITTED_RUNTIME
        or architecture.import_path != "engine.perception.architectural_delta"
        or architecture.sha256 != _V8_ARCHITECTURAL_DELTA_SHA256
    ):
        raise ValueError("V8 architectural runtime binding is invalid")
    for module_id in topology_ids:
        module = modules[index_by_id[module_id]]
        if (
            module.state is not ModuleState.PROVENANCE_TOMBSTONE
            or module.import_path is not None
        ):
            raise ValueError("V8 topology underperformers must remain tombstones")

    return ComplexityRegistry(
        schema_version="complexity_module_registry_v8",
        discovery=base.discovery,
        modules=tuple(modules),
        artifact_rules=base.artifact_rules,
        dismissal_rules=base.dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def load_complexity_registry(root: Path, path: Path) -> ComplexityRegistry:
    project_root = root.resolve()
    registry_path = path if path.is_absolute() else project_root / path
    raw = registry_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("complexity registry must be a JSON object")
    if payload.get("schema_version") == "complexity_module_registry_v8":
        return _load_registry_v8(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v7":
        return _load_registry_v7(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v6":
        return _load_registry_v6(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v5":
        return _load_registry_v5(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v4":
        return _load_registry_v4(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v3":
        return _load_registry_v3(project_root, registry_path, raw, payload)
    if payload.get("schema_version") == "complexity_module_registry_v2":
        return _load_registry_overlay(project_root, registry_path, raw, payload)
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
        descriptor = _module_descriptor_from_row(project_root, row)
        if descriptor.module_id in ids or descriptor.path.casefold() in paths:
            raise ValueError("module IDs and paths must be unique")
        ids.add(descriptor.module_id)
        paths.add(descriptor.path.casefold())
        modules.append(descriptor)

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
        schema_version=payload["schema_version"],
        discovery=normalized_discovery,
        modules=tuple(modules),
        artifact_rules=artifact_rules,
        dismissal_rules=dismissal_rules,
        registry_sha256=hashlib.sha256(raw).hexdigest(),
    )


def load_current_complexity_registry(root: Path) -> ComplexityRegistry:
    """Load the admitted registry and verify every executable module byte-for-byte."""

    project_root = root.resolve()
    registry = load_complexity_registry(
        project_root,
        project_root / CURRENT_COMPLEXITY_REGISTRY_PATH,
    )
    if registry.schema_version != "complexity_module_registry_v8":
        raise ValueError("current complexity runtime must use registry V8")
    runtime_modules = tuple(item for item in registry.modules if item.runtime_eligible)
    if tuple(item.module_id for item in runtime_modules) != (
        "architectural-delta-engine",
    ):
        raise ValueError("current complexity runtime admits only architectural delta")
    for module in runtime_modules:
        source = _inside_root(project_root, module.path)
        if hashlib.sha256(source.read_bytes()).hexdigest() != module.sha256:
            raise ValueError(f"runtime module hash mismatch: {module.module_id}")
    return registry


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
    for descriptor in registry.modules:
        path = _inside_root(project_root, descriptor.path)
        if not path.is_file():
            missing.append(descriptor.path)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor.sha256:
            hash_drift.append(descriptor.path)

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
        classified_module = module_paths.get(relative.casefold())
        if classified_module is not None:
            findings.append(
                CensusFinding(
                    relative,
                    classified_module.state.value,
                    f"module:{classified_module.module_id}",
                )
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
