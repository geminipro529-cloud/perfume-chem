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
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    }
    if not isinstance(overrides, list) or {
        item.get("module_id") for item in overrides if isinstance(item, dict)
    } != expected_override_ids:
        raise ValueError("V5 module overrides must cover the three replacements exactly")
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
    ):
        raise ValueError("V5 architectural runtime binding is invalid")
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = modules[index_by_id[module_id]]
        if (
            module.state is not ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
            or module.import_path is not None
        ):
            raise ValueError("V5 underperformers must remain runtime-unreachable")
    return ComplexityRegistry(
        schema_version="complexity_module_registry_v5",
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
    for module in registry.modules:
        path = _inside_root(project_root, module.path)
        if not path.is_file():
            missing.append(module.path)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != module.sha256:
            hash_drift.append(module.path)

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
