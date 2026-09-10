"""Versioned admission and compatibility registries for the Cypress runtime.

V4 through V6 remain immutable historical provenance.  V7 verifies that
frozen chain, preserves the exact admitted V6 architecture and evidence, and
rebinds only the declared current inventory, material-data, loader, and
evidence-only ledger inputs.  Temporal and preference components remain
nonruntime.  No registry state grants formula, physical, sensory, hedonic,
safety, stability, purchase, scientific, or release authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from engine.perception.complexity_registry import (
    ComplexityRegistry,
    ModuleDescriptor,
    ModuleRole,
    ModuleState,
    load_complexity_registry,
)

V6_REGISTRY_PATH = Path("configs/complexity/complexity_module_registry_v6.json")
V7_REGISTRY_PATH = Path("configs/complexity/complexity_module_registry_v7.json")
CURRENT_HARMONIC_RUNTIME_REGISTRY_PATH = V7_REGISTRY_PATH
V6_ADMITTED_ARCHITECTURE_MODULE_IDS = (
    "material-capability-atlas",
    "cypress-heart-frontier",
    "family-depth",
    "architecture-compiler",
    "architectural-delta-engine",
    "harmonic-synthesis",
    "cypress-harmonic-program",
)
V6_EVIDENCE_ONLY_MODULE_IDS = (
    "temporal-sensory-ledger",
    "hedonic-preference-learner",
)
V6_GUARDRAIL_MODULE_IDS = ("harmonic-request-router",)
V7_ADMITTED_ARCHITECTURE_MODULE_IDS = V6_ADMITTED_ARCHITECTURE_MODULE_IDS
V7_EVIDENCE_ONLY_MODULE_IDS = V6_EVIDENCE_ONLY_MODULE_IDS
V7_GUARDRAIL_MODULE_IDS = V6_GUARDRAIL_MODULE_IDS

_SHA256_LENGTH = 64
_EXPECTED_SCOPE = {
    "cypress_target_architecture": True,
    "target_variant_rebuild": True,
    "inventory_and_authority_guarding": True,
    "experiment_design": True,
    "evidence_only_request_routing": False,
}
_ALL_FALSE_AUTHORITY = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "scientific": False,
    "sensory": False,
    "similarity": False,
    "stability": False,
}
_ALL_FALSE_RECEIPT_AUTHORITY = {
    "formula_mutation": False,
    "physical_execution": False,
    "compounding": False,
    "purchase": False,
    "sensory": False,
    "hedonic": False,
    "similarity": False,
    "performance": False,
    "safety": False,
    "stability": False,
    "release": False,
}
_EXPECTED_EVIDENCE_PATHS = {
    "data/governance/cypress_xhigh_screening_receipt_20260831.json",
    "data/governance/cypress_xhigh_admission_receipt_20260831.json",
}
_EXPECTED_SOURCE_PATHS = {
    "data/governance/depth_module_import_manifest_20260831.json",
    "data/governance/depth_module_supporting_artifacts_manifest_20260831.json",
    "data/governance/inventory_user_authority_overlay_20260828.json",
    "data/governance/inventory_v5_current_stock_snapshot.json",
    "data/governance/inventory_worktree_sync_20260831.json",
    "engine/evidence_contracts.py",
    "engine/inventory/authority.py",
    "engine/inventory_parser.py",
    "engine/material_capability_atlas.py",
    "engine/perception/architectural_delta.py",
    "engine/perception/architecture_compiler.py",
    "engine/perception/architecture_contracts.py",
    "engine/perception/cypress_harmonic_program.py",
    "engine/perception/cypress_heart_frontier.py",
    "engine/perception/cypress_benchmark.py",
    "engine/perception/depth_contracts.py",
    "engine/perception/depth_evaluation.py",
    "engine/perception/depth_family_adapters.py",
    "engine/perception/harmonic_request_router.py",
    "engine/perception/harmonic_runtime_registry.py",
    "engine/perception/harmonic_synthesis.py",
    "engine/solforge/harmonic_runtime.py",
    "inventory.txt",
}
_EXPECTED_V7_SOURCE_PATHS = (
    _EXPECTED_SOURCE_PATHS
    - {
        "data/governance/inventory_user_authority_overlay_20260828.json",
        "data/governance/inventory_worktree_sync_20260831.json",
    }
) | {
    "data/governance/inventory_user_authority_overlay_20260831.json",
    "data/governance/inventory_worktree_sync_20260831_003.json",
    "data/knowledge_graph/ingredient_catalog.json",
    "data/knowledge_graph/material_properties.json",
    "engine/name_utils.py",
    "engine/sensory/ledger.py",
}


@dataclass(frozen=True, slots=True)
class HarmonicRuntimeRegistryV6:
    schema_version: str
    registry_sha256: str
    base_registry_sha256: str
    modules: tuple[ModuleDescriptor, ...]
    base_module_ids: tuple[str, ...]
    admitted_scope: Mapping[str, bool]
    authority_flags: Mapping[str, bool]
    full_gate: Mapping[str, Any]
    source_bindings: tuple[Mapping[str, str], ...]
    material_data_fingerprint: str

    @property
    def admitted_architecture_module_ids(self) -> tuple[str, ...]:
        admitted = {
            item.module_id
            for item in self.modules
            if item.state is ModuleState.ADMITTED_RUNTIME
        }
        return tuple(
            module_id
            for module_id in V6_ADMITTED_ARCHITECTURE_MODULE_IDS
            if module_id in admitted
        )

    @property
    def evidence_only_module_ids(self) -> tuple[str, ...]:
        evidence_only = {
            item.module_id
            for item in self.modules
            if item.state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED
        }
        return tuple(
            module_id
            for module_id in V6_EVIDENCE_ONLY_MODULE_IDS
            if module_id in evidence_only
        )

    @property
    def guardrail_module_ids(self) -> tuple[str, ...]:
        guardrails = {
            item.module_id
            for item in self.modules
            if item.state is ModuleState.MANDATORY_GUARDRAIL
        }
        return tuple(
            module_id for module_id in V6_GUARDRAIL_MODULE_IDS if module_id in guardrails
        )

    @property
    def nonruntime_base_module_ids(self) -> tuple[str, ...]:
        base_ids = set(self.base_module_ids)
        return tuple(
            item.module_id
            for item in self.modules
            if item.module_id in base_ids and not item.runtime_eligible
        )


@dataclass(frozen=True, slots=True)
class HarmonicRuntimeRegistryV7(HarmonicRuntimeRegistryV6):
    predecessor_registry_sha256: str
    compatibility_rebindings: tuple[Mapping[str, Any], ...]
    hash_policy: Mapping[str, str]


def _relative_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonblank repository-relative path")
    raw = value.strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or ":" in raw:
        raise ValueError(f"{field} must be repository-relative")
    return path.as_posix()


def _inside_root(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes project root") from exc
    return candidate


def _sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be lower-case SHA-256")
    return value


def _verify_hash_record(
    root: Path,
    record: Any,
    *,
    label: str,
) -> tuple[str, str]:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError(f"{label} entries are closed path/hash records")
    relative = _relative_path(record["path"], f"{label} path")
    expected = _sha256(record["sha256"], f"{label} sha256")
    source = _inside_root(root, relative)
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError(f"{label} hash mismatch: {relative}")
    return relative, expected


def _material_data_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    data_dir = root / "data/materials"
    for path in sorted(data_dir.glob("*.yaml"), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(_normalized_utf8_bytes(path))
    return digest.hexdigest()


def _module_from_row(root: Path, row: Any) -> ModuleDescriptor:
    required = {
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
    if not isinstance(row, dict) or set(row) != required:
        raise ValueError("V6 module additions use a closed schema")
    path = _relative_path(row["path"], "module path")
    digest = _sha256(row["sha256"], "module sha256")
    source = _inside_root(root, path)
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError(f"module source hash mismatch: {path}")
    try:
        state = ModuleState(row["state"])
        role = ModuleRole(row["role"])
    except ValueError as exc:
        raise ValueError("V6 module role or state is invalid") from exc
    import_path = row["import_path"]
    if import_path is not None and (
        not isinstance(import_path, str) or not import_path.strip()
    ):
        raise ValueError("module import_path must be null or nonblank")
    if state in {ModuleState.ADMITTED_RUNTIME, ModuleState.MANDATORY_GUARDRAIL}:
        if import_path is None:
            raise ValueError("runtime V6 modules require import_path")
    elif import_path is not None:
        raise ValueError("nonruntime V6 modules cannot expose import_path")
    evidence_refs = row["evidence_refs"]
    notes = row["notes"]
    if not isinstance(evidence_refs, list) or not all(
        isinstance(item, str) and item.strip() for item in evidence_refs
    ):
        raise ValueError("module evidence_refs must be nonblank strings")
    if not isinstance(notes, list) or not all(
        isinstance(item, str) and item.strip() for item in notes
    ):
        raise ValueError("module notes must be nonblank strings")
    for reference in evidence_refs:
        if reference.startswith(("data/", "tests/", "docs/", "configs/")):
            reference_path = _inside_root(root, _relative_path(reference, "evidence ref"))
            if not reference_path.exists():
                raise ValueError(f"module evidence ref is missing: {reference}")
    return ModuleDescriptor(
        module_id=str(row["module_id"]),
        family_id=str(row["family_id"]),
        role=role,
        state=state,
        path=path,
        import_path=import_path,
        sha256=digest,
        evidence_refs=tuple(evidence_refs),
        notes=tuple(notes),
    )


def _apply_module_overrides(
    root: Path,
    base: ComplexityRegistry,
    rows: Any,
) -> tuple[ModuleDescriptor, ...]:
    required_ids = {
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    }
    if not isinstance(rows, list) or {
        row.get("module_id") for row in rows if isinstance(row, dict)
    } != required_ids:
        raise ValueError("V6 module overrides must cover the three replacements exactly")
    allowed = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    modules = list(base.modules)
    indexes = {item.module_id: index for index, item in enumerate(modules)}
    for row in rows:
        if not isinstance(row, dict) or set(row) != allowed:
            raise ValueError("V6 module overrides use a closed schema")
        module_id = row["module_id"]
        base_module = modules[indexes[module_id]]
        digest = _sha256(row["sha256"], "module override sha256")
        source = _inside_root(root, base_module.path)
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError(f"module source hash mismatch: {base_module.path}")
        state = ModuleState(row["state"])
        import_path = row["import_path"]
        if state is ModuleState.ADMITTED_RUNTIME:
            if not isinstance(import_path, str) or not import_path.strip():
                raise ValueError("admitted module override requires import_path")
        elif state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED:
            if import_path is not None:
                raise ValueError("evidence-only module override must remain nonruntime")
        else:
            raise ValueError("V6 replacement override state is outside the closed policy")
        evidence_refs = row["evidence_refs"]
        notes = row["notes"]
        if not isinstance(evidence_refs, list) or not all(
            isinstance(item, str) and item.strip() for item in evidence_refs
        ):
            raise ValueError("override evidence refs are invalid")
        if not isinstance(notes, list) or not all(
            isinstance(item, str) and item.strip() for item in notes
        ):
            raise ValueError("override notes are invalid")
        modules[indexes[module_id]] = replace(
            base_module,
            state=state,
            import_path=import_path,
            sha256=digest,
            evidence_refs=tuple(evidence_refs),
            notes=tuple(notes),
        )
    return tuple(modules)


def _load_harmonic_runtime_registry_v6(
    root: Path,
    *,
    registry_path: Path | None = None,
) -> HarmonicRuntimeRegistryV6:
    project_root = root.resolve()
    path = (registry_path or project_root / V6_REGISTRY_PATH).resolve()
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    required = {
        "schema_version",
        "base_registry",
        "admission_evidence",
        "source_bindings",
        "material_data_fingerprint",
        "module_overrides",
        "module_additions",
        "runtime_entrypoint",
        "admitted_scope",
        "authority_flags",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("complexity registry V6 top-level keys are closed")
    if payload["schema_version"] != "complexity_module_registry_v6":
        raise ValueError("unsupported harmonic runtime registry schema")

    base_record = payload["base_registry"]
    base_relative, base_digest = _verify_hash_record(
        project_root,
        base_record,
        label="base registry",
    )
    if base_relative != "configs/complexity/complexity_module_registry_v5.json":
        raise ValueError("V6 base registry must be exact V5")
    base = load_complexity_registry(project_root, project_root / base_relative)
    if base.schema_version != "complexity_module_registry_v5" or any(
        item.runtime_eligible for item in base.modules
    ):
        raise ValueError("V6 base must be immutable nonruntime V5")

    if payload["authority_flags"] != _ALL_FALSE_AUTHORITY:
        raise ValueError("V6 authority flags must be the exact all-false mapping")
    if payload["admitted_scope"] != _EXPECTED_SCOPE:
        raise ValueError("V6 admitted scope does not match the frozen receipt")

    evidence_rows = payload["admission_evidence"]
    if not isinstance(evidence_rows, list):
        raise ValueError("V6 admission evidence must be a list")
    evidence_payloads: dict[str, Mapping[str, Any]] = {}
    for row in evidence_rows:
        relative, _ = _verify_hash_record(
            project_root,
            row,
            label="admission evidence",
        )
        if relative in evidence_payloads:
            raise ValueError("V6 admission evidence paths must be unique")
        loaded = json.loads(_inside_root(project_root, relative).read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping):
            raise ValueError("V6 admission evidence must contain JSON objects")
        evidence_payloads[relative] = loaded
    if set(evidence_payloads) != _EXPECTED_EVIDENCE_PATHS:
        raise ValueError("V6 admission evidence paths must be exact")

    screen = evidence_payloads[
        "data/governance/cypress_xhigh_screening_receipt_20260831.json"
    ]
    screen_gate = screen.get("screening_gate")
    if (
        screen.get("schema_version") != "cypress_xhigh_screening_receipt_v1"
        or not isinstance(screen_gate, Mapping)
        or screen_gate.get("passed") is not True
        or screen_gate.get("case_count") != 3
        or screen_gate.get("wins_vs_plain", 0) < 2
        or screen_gate.get("wins_vs_placebo", 0) < 2
        or screen_gate.get("integrated_critical_errors") != []
    ):
        raise ValueError("V6 screening receipt did not pass the frozen gate")

    admission = evidence_payloads[
        "data/governance/cypress_xhigh_admission_receipt_20260831.json"
    ]
    gate = admission.get("admission_gate")
    if (
        admission.get("schema_version") != "cypress_xhigh_admission_receipt_v1"
        or admission.get("admitted_scope") != _EXPECTED_SCOPE
        or not isinstance(gate, Mapping)
        or gate.get("stage") != "FULL"
        or gate.get("passed") is not True
        or gate.get("case_count") != 6
        or gate.get("wins_vs_plain", 0) < 4
        or gate.get("wins_vs_placebo", 0) < 4
        or float(gate.get("median_gain_vs_plain", 0)) < 5
        or float(gate.get("median_gain_vs_placebo", 0)) < 5
        or gate.get("integrated_critical_errors") != []
        or gate.get("reasons") != []
    ):
        raise ValueError("V6 full admission receipt did not pass the frozen gate")
    regression = admission.get("known_noncritical_regression")
    if (
        not isinstance(regression, Mapping)
        or regression.get("case_id") != "CYP-XH-C2-ORDER-CONFOUNDING"
        or regression.get("destructive_trash") is not False
        or regression.get("provenance_preserved") is not True
    ):
        raise ValueError("V6 known regression provenance is incomplete")
    receipt_authority = admission.get("authority")
    if not isinstance(receipt_authority, Mapping) or any(receipt_authority.values()):
        raise ValueError("V6 admission receipt authority must remain all false")

    source_rows = payload["source_bindings"]
    if not isinstance(source_rows, list):
        raise ValueError("V6 source bindings must be a list")
    observed_source_paths: set[str] = set()
    normalized_source_rows: list[Mapping[str, str]] = []
    for row in source_rows:
        relative, digest = _verify_hash_record(
            project_root,
            row,
            label="source binding",
        )
        if relative in observed_source_paths:
            raise ValueError("V6 source binding paths must be unique")
        observed_source_paths.add(relative)
        normalized_source_rows.append({"path": relative, "sha256": digest})
    if observed_source_paths != _EXPECTED_SOURCE_PATHS:
        raise ValueError("V6 source binding paths must be exact")
    benchmark_digest = hashlib.sha256(
        (project_root / "engine/perception/cypress_benchmark.py").read_bytes()
    ).hexdigest()
    if admission.get("benchmark_module_sha256") != benchmark_digest:
        raise ValueError("V6 benchmark module hash does not match the frozen receipt")

    material_fingerprint = _sha256(
        payload["material_data_fingerprint"],
        "material data fingerprint",
    )
    if _material_data_fingerprint(project_root) != material_fingerprint:
        raise ValueError("V6 material data fingerprint mismatch")

    modules = list(_apply_module_overrides(project_root, base, payload["module_overrides"]))
    additions = payload["module_additions"]
    if not isinstance(additions, list):
        raise ValueError("V6 module additions must be a list")
    modules.extend(_module_from_row(project_root, row) for row in additions)
    ids = [item.module_id for item in modules]
    paths = [item.path.casefold() for item in modules]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("V6 module IDs and paths must be unique")

    runtime_ids = tuple(
        item.module_id
        for item in modules
        if item.state is ModuleState.ADMITTED_RUNTIME
    )
    if set(runtime_ids) != set(V6_ADMITTED_ARCHITECTURE_MODULE_IDS):
        raise ValueError("V6 admitted architecture module set is not exact")
    guardrail_ids = tuple(
        item.module_id
        for item in modules
        if item.state is ModuleState.MANDATORY_GUARDRAIL
    )
    if guardrail_ids != V6_GUARDRAIL_MODULE_IDS:
        raise ValueError("V6 guardrail module set is not exact")
    evidence_only_ids = {
        item.module_id
        for item in modules
        if item.state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED
    }
    if not set(V6_EVIDENCE_ONLY_MODULE_IDS).issubset(evidence_only_ids):
        raise ValueError("V6 evidence-only replacements must remain nonruntime")

    entrypoint = payload["runtime_entrypoint"]
    required_entrypoint = {"path", "sha256", "import_path", "callable"}
    if not isinstance(entrypoint, dict) or set(entrypoint) != required_entrypoint:
        raise ValueError("V6 runtime entrypoint schema is closed")
    entrypoint_relative = _relative_path(entrypoint["path"], "runtime entrypoint path")
    if (
        entrypoint_relative != "engine/solforge/harmonic_runtime.py"
        or entrypoint["import_path"] != "engine.solforge.harmonic_runtime"
        or entrypoint["callable"] != "run_admitted_cypress_harmonic"
    ):
        raise ValueError("V6 runtime entrypoint is not exact")
    entrypoint_digest = _sha256(entrypoint["sha256"], "runtime entrypoint sha256")
    source_digests = {
        item["path"]: item["sha256"] for item in normalized_source_rows
    }
    if source_digests.get(entrypoint_relative) != entrypoint_digest:
        raise ValueError("V6 runtime entrypoint is not source-bound")

    full_gate = {
        "case_count": gate["case_count"],
        "wins_vs_plain": gate["wins_vs_plain"],
        "wins_vs_placebo": gate["wins_vs_placebo"],
        "median_gain_vs_plain": gate["median_gain_vs_plain"],
        "median_gain_vs_placebo": gate["median_gain_vs_placebo"],
        "integrated_critical_errors": gate["integrated_critical_errors"],
    }
    return HarmonicRuntimeRegistryV6(
        schema_version="complexity_module_registry_v6",
        registry_sha256=hashlib.sha256(raw).hexdigest(),
        base_registry_sha256=base_digest,
        modules=tuple(modules),
        base_module_ids=tuple(item.module_id for item in base.modules),
        admitted_scope=dict(payload["admitted_scope"]),
        authority_flags=dict(payload["authority_flags"]),
        full_gate=full_gate,
        source_bindings=tuple(normalized_source_rows),
        material_data_fingerprint=material_fingerprint,
    )


def _normalized_utf8_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise ValueError(f"bare CR is forbidden in text binding: {path.as_posix()}")
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n")


def _normalized_utf8_sha256(path: Path) -> str:
    return hashlib.sha256(_normalized_utf8_bytes(path)).hexdigest()


def _matches_historical_text_sha256(path: Path, expected: str) -> bool:
    """Accept only EOL-equivalent materializations of a frozen text record."""

    raw = path.read_bytes()
    normalized = _normalized_utf8_bytes(path)
    candidates = {
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(normalized).hexdigest(),
        hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest(),
    }
    return expected in candidates


def _validate_frozen_text_records(
    root: Path,
    rows: Any,
    *,
    label: str,
    exempt_paths: frozenset[str] = frozenset(),
) -> Mapping[str, str]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label} must be a nonempty list")
    records: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError(f"{label} entries are closed path/hash records")
        relative = _relative_path(row["path"], f"{label} path")
        digest = _sha256(row["sha256"], f"{label} sha256")
        if relative in records:
            raise ValueError(f"{label} paths must be unique")
        records[relative] = digest
        if relative in exempt_paths:
            continue
        source = _inside_root(root, relative)
        if not source.is_file() or not _matches_historical_text_sha256(
            source,
            digest,
        ):
            raise ValueError(f"{label} hash mismatch: {relative}")
    return records


def _verify_normalized_hash_record(
    root: Path,
    record: Any,
    *,
    label: str,
) -> tuple[str, str]:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError(f"{label} entries are closed path/hash records")
    relative = _relative_path(record["path"], f"{label} path")
    expected = _sha256(record["sha256"], f"{label} sha256")
    source = _inside_root(root, relative)
    if not source.is_file() or _normalized_utf8_sha256(source) != expected:
        raise ValueError(f"{label} hash mismatch: {relative}")
    return relative, expected


def _frozen_registry_payload(
    root: Path,
    relative: str,
    expected_sha256: str,
    *,
    schema_version: str,
) -> Mapping[str, Any]:
    path = _inside_root(root, _relative_path(relative, "frozen registry path"))
    expected = _sha256(expected_sha256, "frozen registry sha256")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"frozen registry hash mismatch: {relative}")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != schema_version:
        raise ValueError(f"frozen registry schema mismatch: {relative}")
    return payload


def _replay_historical_overrides(
    modules: tuple[ModuleDescriptor, ...],
    rows: Any,
    *,
    label: str,
) -> tuple[ModuleDescriptor, ...]:
    allowed = {
        "module_id",
        "state",
        "import_path",
        "sha256",
        "evidence_refs",
        "notes",
    }
    if not isinstance(rows, list):
        raise ValueError(f"{label} module overrides must be a list")
    output = list(modules)
    indexes = {item.module_id: index for index, item in enumerate(output)}
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != allowed:
            raise ValueError(f"{label} module override schema is closed")
        module_id = str(row["module_id"])
        if module_id in seen or module_id not in indexes:
            raise ValueError(f"{label} module override IDs are invalid")
        seen.add(module_id)
        state = ModuleState(row["state"])
        import_path = row["import_path"]
        if import_path is not None and (
            not isinstance(import_path, str) or not import_path.strip()
        ):
            raise ValueError(f"{label} import_path is invalid")
        evidence_refs = row["evidence_refs"]
        notes = row["notes"]
        if not isinstance(evidence_refs, list) or not all(
            isinstance(item, str) and item.strip() for item in evidence_refs
        ):
            raise ValueError(f"{label} evidence refs are invalid")
        if not isinstance(notes, list) or not all(
            isinstance(item, str) and item.strip() for item in notes
        ):
            raise ValueError(f"{label} notes are invalid")
        output[indexes[module_id]] = replace(
            output[indexes[module_id]],
            state=state,
            import_path=import_path,
            sha256=_sha256(row["sha256"], f"{label} module sha256"),
            evidence_refs=tuple(evidence_refs),
            notes=tuple(notes),
        )
    return tuple(output)


def _v7_admission_gate(
    root: Path,
    rows: Any,
    frozen_rows: Any,
    current_sources: Mapping[str, str],
) -> Mapping[str, Any]:
    if not isinstance(rows, list):
        raise ValueError("V7 admission evidence must be a list")
    if not isinstance(frozen_rows, list):
        raise ValueError("frozen V6 admission evidence must be a list")
    frozen: dict[str, str] = {}
    for row in frozen_rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError("frozen V6 admission evidence records are closed")
        relative = _relative_path(row["path"], "frozen V6 admission evidence path")
        digest = _sha256(row["sha256"], "frozen V6 admission evidence sha256")
        if relative in frozen:
            raise ValueError("frozen V6 admission evidence paths must be unique")
        frozen[relative] = digest
    if set(frozen) != _EXPECTED_EVIDENCE_PATHS:
        raise ValueError("frozen V6 admission evidence paths must be exact")
    evidence: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        relative, _ = _verify_normalized_hash_record(
            root,
            row,
            label="V7 admission evidence",
        )
        source = _inside_root(root, relative)
        if not _matches_historical_text_sha256(source, frozen.get(relative, "")):
            raise ValueError(f"V7 admission evidence drifted from V6: {relative}")
        loaded = json.loads(_inside_root(root, relative).read_text(encoding="utf-8"))
        if relative in evidence or not isinstance(loaded, Mapping):
            raise ValueError("V7 admission evidence is duplicate or invalid")
        evidence[relative] = loaded
    if set(evidence) != _EXPECTED_EVIDENCE_PATHS:
        raise ValueError("V7 admission evidence paths must be exact")

    screen = evidence[
        "data/governance/cypress_xhigh_screening_receipt_20260831.json"
    ]
    screen_gate = screen.get("screening_gate")
    if (
        screen.get("schema_version") != "cypress_xhigh_screening_receipt_v1"
        or not isinstance(screen_gate, Mapping)
        or screen_gate.get("passed") is not True
        or screen_gate.get("case_count") != 3
        or screen_gate.get("wins_vs_plain", 0) < 2
        or screen_gate.get("wins_vs_placebo", 0) < 2
        or screen_gate.get("integrated_critical_errors") != []
        or screen.get("authority") != _ALL_FALSE_RECEIPT_AUTHORITY
    ):
        raise ValueError("V7 screening receipt did not pass the frozen gate")

    admission = evidence[
        "data/governance/cypress_xhigh_admission_receipt_20260831.json"
    ]
    gate = admission.get("admission_gate")
    if (
        admission.get("schema_version") != "cypress_xhigh_admission_receipt_v1"
        or admission.get("admitted_scope") != _EXPECTED_SCOPE
        or not isinstance(gate, Mapping)
        or gate.get("stage") != "FULL"
        or gate.get("passed") is not True
        or gate.get("case_count") != 6
        or gate.get("wins_vs_plain", 0) < 4
        or gate.get("wins_vs_placebo", 0) < 4
        or float(gate.get("median_gain_vs_plain", 0)) < 5
        or float(gate.get("median_gain_vs_placebo", 0)) < 5
        or gate.get("integrated_critical_errors") != []
        or gate.get("reasons") != []
        or admission.get("authority") != _ALL_FALSE_RECEIPT_AUTHORITY
    ):
        raise ValueError("V7 full admission receipt did not pass the frozen gate")
    regression = admission.get("known_noncritical_regression")
    if (
        not isinstance(regression, Mapping)
        or regression.get("case_id") != "CYP-XH-C2-ORDER-CONFOUNDING"
        or regression.get("destructive_trash") is not False
        or regression.get("provenance_preserved") is not True
    ):
        raise ValueError("V7 known regression provenance is incomplete")
    benchmark_digest = _sha256(
        admission.get("benchmark_module_sha256"),
        "V7 admission benchmark module sha256",
    )
    if current_sources.get("engine/perception/cypress_benchmark.py") != (
        benchmark_digest
    ):
        raise ValueError("V7 admission benchmark module binding drifted")
    return gate


def _load_harmonic_runtime_registry_v7(
    project_root: Path,
    registry_path: Path,
) -> HarmonicRuntimeRegistryV7:
    raw = registry_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    required = {
        "schema_version",
        "predecessor_registry",
        "hash_policy",
        "compatibility_policy",
        "compatibility_rebindings",
        "material_data_rebinding",
        "admission_evidence",
        "current_source_bindings",
        "material_data_fingerprint",
        "admitted_scope",
        "authority_flags",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("complexity registry V7 top-level keys are closed")
    if payload["schema_version"] != "complexity_module_registry_v7":
        raise ValueError("unsupported harmonic runtime registry schema")
    expected_hash_policy = {
        "registry_bytes": "RAW_SHA256",
        "utf8_text_bindings": "CRLF_TO_LF_THEN_SHA256",
        "bare_cr": "REJECT",
    }
    if payload["hash_policy"] != expected_hash_policy:
        raise ValueError("V7 hash policy must be exact")
    expected_compatibility_policy = {
        "compatibility_successor_only": True,
        "new_module_admission": False,
        "runtime_module_set_changed": False,
        "target_scope_changed": False,
        "evidence_only_request_routing_admitted": False,
        "historical_registry_rewritten": False,
        "historical_receipt_rewritten": False,
    }
    if payload["compatibility_policy"] != expected_compatibility_policy:
        raise ValueError("V7 compatibility policy must be exact and non-promoting")
    if payload["admitted_scope"] != _EXPECTED_SCOPE:
        raise ValueError("V7 admitted scope must remain exact")
    if payload["authority_flags"] != _ALL_FALSE_AUTHORITY:
        raise ValueError("V7 authority flags must remain all false")

    predecessor_record = payload["predecessor_registry"]
    predecessor_relative, predecessor_digest = _verify_hash_record(
        project_root,
        predecessor_record,
        label="V7 predecessor registry",
    )
    if predecessor_relative != V6_REGISTRY_PATH.as_posix():
        raise ValueError("V7 predecessor must be the exact V6 registry")
    v6 = _frozen_registry_payload(
        project_root,
        predecessor_relative,
        predecessor_digest,
        schema_version="complexity_module_registry_v6",
    )
    if v6.get("authority_flags") != _ALL_FALSE_AUTHORITY or v6.get(
        "admitted_scope"
    ) != _EXPECTED_SCOPE:
        raise ValueError("frozen V6 predecessor authority or scope drifted")

    v5_record = v6.get("base_registry")
    if not isinstance(v5_record, dict) or set(v5_record) != {"path", "sha256"}:
        raise ValueError("frozen V6 base registry record is invalid")
    v5_relative = _relative_path(v5_record["path"], "V6 base registry path")
    v5 = _frozen_registry_payload(
        project_root,
        v5_relative,
        str(v5_record["sha256"]),
        schema_version="complexity_module_registry_v5",
    )
    v4_record = v5.get("base_registry")
    if not isinstance(v4_record, dict) or set(v4_record) != {"path", "sha256"}:
        raise ValueError("frozen V5 base registry record is invalid")
    v4_relative = (
        Path(v5_relative).parent / _relative_path(v4_record["path"], "V5 base path")
    ).as_posix()
    v4 = _frozen_registry_payload(
        project_root,
        v4_relative,
        str(v4_record["sha256"]),
        schema_version="complexity_module_registry_v4",
    )
    chain = v4.get("base_registry_chain")
    if not isinstance(chain, list) or [item.get("path") for item in chain] != [
        "complexity_module_registry_v1.json",
        "complexity_module_registry_v2.json",
        "complexity_module_registry_v3.json",
    ]:
        raise ValueError("frozen V4 registry chain is not exact")
    for version, item in enumerate(chain, start=1):
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("frozen V4 registry chain records are closed")
        relative = (Path(v4_relative).parent / str(item["path"])).as_posix()
        _frozen_registry_payload(
            project_root,
            relative,
            str(item["sha256"]),
            schema_version=f"complexity_module_registry_v{version}",
        )

    v4_source_bindings = _validate_frozen_text_records(
        project_root,
        v4.get("source_bindings"),
        label="frozen V4 source binding",
        exempt_paths=frozenset({"engine/sensory/ledger.py"}),
    )
    _validate_frozen_text_records(
        project_root,
        v5.get("admission_evidence"),
        label="frozen V5 admission evidence",
    )
    _validate_frozen_text_records(
        project_root,
        v5.get("runtime_bindings"),
        label="frozen V5 runtime binding",
    )

    v3_path = project_root / Path(v4_relative).parent / str(chain[-1]["path"])
    base = load_complexity_registry(project_root, v3_path)
    modules = _replay_historical_overrides(
        base.modules,
        v4.get("module_overrides"),
        label="V4 historical",
    )
    modules = _replay_historical_overrides(
        modules,
        v5.get("module_overrides"),
        label="V5 historical",
    )

    source_rows = payload["current_source_bindings"]
    if not isinstance(source_rows, list):
        raise ValueError("V7 current source bindings must be a list")
    current_sources: dict[str, str] = {}
    for row in source_rows:
        relative, digest = _verify_normalized_hash_record(
            project_root,
            row,
            label="V7 current source binding",
        )
        if relative in current_sources:
            raise ValueError("V7 current source bindings must be unique")
        current_sources[relative] = digest
    if set(current_sources) != _EXPECTED_V7_SOURCE_PATHS:
        raise ValueError("V7 current source binding paths must be exact")

    v6_source_rows = v6.get("source_bindings")
    if not isinstance(v6_source_rows, list):
        raise ValueError("frozen V6 source bindings are invalid")
    v6_sources = {
        _relative_path(row["path"], "V6 source path"): _sha256(
            row["sha256"], "V6 source sha256"
        )
        for row in v6_source_rows
        if isinstance(row, dict) and set(row) == {"path", "sha256"}
    }
    if set(v6_sources) != _EXPECTED_SOURCE_PATHS:
        raise ValueError("frozen V6 source binding paths are not exact")

    expected_rebindings = {
        "temporal-ledger": (
            "engine/sensory/ledger.py",
            "engine/sensory/ledger.py",
            "NONRUNTIME_TYPECHECK_AND_INPUT_VALIDATION_HARDENING",
        ),
        "inventory-overlay": (
            "data/governance/inventory_user_authority_overlay_20260828.json",
            "data/governance/inventory_user_authority_overlay_20260831.json",
            "USER_AUTHORITY_SUCCESSOR",
        ),
        "inventory-sync": (
            "data/governance/inventory_worktree_sync_20260831.json",
            "data/governance/inventory_worktree_sync_20260831_003.json",
            "PROVENANCE_RECEIPT_SUCCESSOR",
        ),
        "inventory-parser": (
            "engine/inventory_parser.py",
            "engine/inventory_parser.py",
            "CURRENT_AUTHORITY_BINDING_SUCCESSOR",
        ),
        "legacy-inventory-text": (
            "inventory.txt",
            "inventory.txt",
            "LEGACY_TEXT_SUCCESSOR",
        ),
        "harmonic-registry-loader": (
            "engine/perception/harmonic_runtime_registry.py",
            "engine/perception/harmonic_runtime_registry.py",
            "REGISTRY_VERSION_ROUTING_ONLY",
        ),
    }
    rebinding_rows = payload["compatibility_rebindings"]
    if not isinstance(rebinding_rows, list):
        raise ValueError("V7 compatibility rebindings must be a list")
    rebindings: dict[str, Mapping[str, Any]] = {}
    current_by_historical: dict[tuple[str, str], str] = {}
    for row in rebinding_rows:
        if not isinstance(row, dict) or set(row) != {
            "binding_id",
            "historical",
            "current",
            "change_class",
            "authority_effect",
        }:
            raise ValueError("V7 compatibility rebinding schema is closed")
        binding_id = str(row["binding_id"])
        if binding_id in rebindings or binding_id not in expected_rebindings:
            raise ValueError("V7 compatibility rebinding IDs must be exact")
        old_path, new_path, change_class = expected_rebindings[binding_id]
        historical = row["historical"]
        current = row["current"]
        if (
            not isinstance(historical, dict)
            or set(historical) != {"path", "sha256"}
            or not isinstance(current, dict)
            or set(current) != {"path", "sha256"}
            or row["authority_effect"] != "NONE"
            or row["change_class"] != change_class
            or historical["path"] != old_path
            or current["path"] != new_path
        ):
            raise ValueError("V7 compatibility rebinding contract drifted")
        old_digest = _sha256(historical["sha256"], "historical rebinding sha256")
        new_digest = _sha256(current["sha256"], "current rebinding sha256")
        if binding_id == "temporal-ledger":
            temporal_override = next(
                item
                for item in v6["module_overrides"]
                if item["module_id"] == "temporal-sensory-ledger"
            )
            v5_temporal_override = next(
                item
                for item in v5["module_overrides"]
                if item["module_id"] == "temporal-sensory-ledger"
            )
            if (
                old_digest != temporal_override["sha256"]
                or old_digest != v5_temporal_override["sha256"]
                or old_digest
                != v4_source_bindings.get("engine/sensory/ledger.py")
            ):
                raise ValueError("V7 temporal ledger predecessor hash drifted")
        elif v6_sources.get(old_path) != old_digest:
            raise ValueError("V7 historical source rebinding is not V6-bound")
        if old_path != new_path:
            historical_source = _inside_root(project_root, old_path)
            if not historical_source.is_file() or not _matches_historical_text_sha256(
                historical_source,
                old_digest,
            ):
                raise ValueError(
                    f"V7 preserved historical source hash mismatch: {old_path}"
                )
        if current_sources.get(new_path) != new_digest:
            raise ValueError("V7 current source rebinding is not current-bound")
        current_by_historical[(old_path, old_digest)] = new_digest
        rebindings[binding_id] = row
    if set(rebindings) != set(expected_rebindings):
        raise ValueError("V7 compatibility rebinding set must be exact")

    rebound_historical_paths = {
        expected_rebindings[binding_id][0] for binding_id in rebindings
    }
    for relative, historical_digest in v6_sources.items():
        if relative in rebound_historical_paths:
            continue
        source = _inside_root(project_root, relative)
        if (
            not source.is_file()
            or current_sources.get(relative) != _normalized_utf8_sha256(source)
            or not _matches_historical_text_sha256(source, historical_digest)
        ):
            raise ValueError(
                f"V7 undeclared historical source drift is forbidden: {relative}"
            )

    material_rebinding = payload["material_data_rebinding"]
    if not isinstance(material_rebinding, dict) or set(material_rebinding) != {
        "historical_sha256",
        "current_sha256",
        "change_class",
        "authority_effect",
    }:
        raise ValueError("V7 material data rebinding schema is closed")
    historical_material_digest = _sha256(
        material_rebinding["historical_sha256"],
        "historical material data sha256",
    )
    current_material_digest = _sha256(
        material_rebinding["current_sha256"],
        "current material data sha256",
    )
    if (
        historical_material_digest != v6.get("material_data_fingerprint")
        or current_material_digest != payload["material_data_fingerprint"]
        or material_rebinding["change_class"] != "CURRENT_MATERIAL_DATA_SUCCESSOR"
        or material_rebinding["authority_effect"] != "NONE"
    ):
        raise ValueError("V7 material data rebinding is invalid")
    if _material_data_fingerprint(project_root) != current_material_digest:
        raise ValueError("V7 material data fingerprint mismatch")

    gate = _v7_admission_gate(
        project_root,
        payload["admission_evidence"],
        v6.get("admission_evidence"),
        current_sources,
    )

    v6_overrides = v6.get("module_overrides")
    if not isinstance(v6_overrides, list) or {
        row.get("module_id") for row in v6_overrides if isinstance(row, dict)
    } != {
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    }:
        raise ValueError("frozen V6 module overrides are not exact")
    output = list(modules)
    indexes = {item.module_id: index for index, item in enumerate(output)}
    for row in v6_overrides:
        if not isinstance(row, dict) or set(row) != {
            "module_id",
            "state",
            "import_path",
            "sha256",
            "evidence_refs",
            "notes",
        }:
            raise ValueError("frozen V6 module override schema is closed")
        module_id = str(row["module_id"])
        base_module = output[indexes[module_id]]
        old_digest = _sha256(row["sha256"], "V6 module override sha256")
        current_digest = current_by_historical.get(
            (base_module.path, old_digest), old_digest
        )
        if _normalized_utf8_sha256(_inside_root(project_root, base_module.path)) != (
            current_digest
        ):
            raise ValueError(f"V7 module source hash mismatch: {base_module.path}")
        state = ModuleState(row["state"])
        import_path = row["import_path"]
        if state is ModuleState.ADMITTED_RUNTIME:
            if not isinstance(import_path, str) or not import_path.strip():
                raise ValueError("V7 admitted override requires import_path")
        elif state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED:
            if import_path is not None:
                raise ValueError("V7 evidence-only override must remain nonruntime")
        else:
            raise ValueError("V7 override state is outside the admitted policy")
        output[indexes[module_id]] = replace(
            base_module,
            state=state,
            import_path=import_path,
            sha256=current_digest,
            evidence_refs=tuple(row["evidence_refs"]),
            notes=tuple(row["notes"]),
        )

    additions = v6.get("module_additions")
    if not isinstance(additions, list):
        raise ValueError("frozen V6 module additions must be a list")
    for row in additions:
        if not isinstance(row, dict) or set(row) != {
            "module_id",
            "family_id",
            "role",
            "state",
            "path",
            "import_path",
            "sha256",
            "evidence_refs",
            "notes",
        }:
            raise ValueError("frozen V6 module additions use a closed schema")
        relative = _relative_path(row["path"], "V6 addition path")
        old_digest = _sha256(row["sha256"], "V6 addition sha256")
        current_digest = current_by_historical.get((relative, old_digest), old_digest)
        if _normalized_utf8_sha256(_inside_root(project_root, relative)) != current_digest:
            raise ValueError(f"V7 module source hash mismatch: {relative}")
        current_row = dict(row)
        current_row["sha256"] = current_digest
        # `_module_from_row` additionally validates role/state/import and evidence refs;
        # the file hash is normalized here to make the V7 platform policy explicit.
        descriptor = ModuleDescriptor(
            module_id=str(current_row["module_id"]),
            family_id=str(current_row["family_id"]),
            role=ModuleRole(current_row["role"]),
            state=ModuleState(current_row["state"]),
            path=relative,
            import_path=current_row["import_path"],
            sha256=current_digest,
            evidence_refs=tuple(current_row["evidence_refs"]),
            notes=tuple(current_row["notes"]),
        )
        if descriptor.state in {
            ModuleState.ADMITTED_RUNTIME,
            ModuleState.MANDATORY_GUARDRAIL,
        }:
            if not isinstance(descriptor.import_path, str) or not descriptor.import_path:
                raise ValueError("V7 runtime additions require import_path")
        elif descriptor.import_path is not None:
            raise ValueError("V7 nonruntime additions cannot expose import_path")
        for reference in descriptor.evidence_refs:
            if reference.startswith(("data/", "tests/", "docs/", "configs/")) and not (
                _inside_root(project_root, _relative_path(reference, "evidence ref")).exists()
            ):
                raise ValueError(f"V7 module evidence ref is missing: {reference}")
        output.append(descriptor)

    ids = [item.module_id for item in output]
    paths = [item.path.casefold() for item in output]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("V7 module IDs and paths must be unique")
    runtime_ids = {
        item.module_id for item in output if item.state is ModuleState.ADMITTED_RUNTIME
    }
    guardrail_ids = tuple(
        item.module_id
        for item in output
        if item.state is ModuleState.MANDATORY_GUARDRAIL
    )
    evidence_only_ids = {
        item.module_id
        for item in output
        if item.state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED
    }
    if runtime_ids != set(V7_ADMITTED_ARCHITECTURE_MODULE_IDS):
        raise ValueError("V7 admitted architecture module set is not exact")
    if guardrail_ids != V7_GUARDRAIL_MODULE_IDS:
        raise ValueError("V7 guardrail module set is not exact")
    if not set(V7_EVIDENCE_ONLY_MODULE_IDS).issubset(evidence_only_ids):
        raise ValueError("V7 evidence-only modules must remain nonruntime")
    temporal = output[indexes["temporal-sensory-ledger"]]
    if (
        temporal.state is not ModuleState.EVIDENCE_ONLY_NOT_ADMITTED
        or temporal.import_path is not None
        or temporal.sha256
        != current_sources["engine/sensory/ledger.py"]
    ):
        raise ValueError("V7 temporal ledger compatibility must remain evidence-only")

    entrypoint = v6.get("runtime_entrypoint")
    if not isinstance(entrypoint, dict) or set(entrypoint) != {
        "path",
        "sha256",
        "import_path",
        "callable",
    }:
        raise ValueError("frozen V6 runtime entrypoint schema is closed")
    if (
        entrypoint["path"] != "engine/solforge/harmonic_runtime.py"
        or entrypoint["import_path"] != "engine.solforge.harmonic_runtime"
        or entrypoint["callable"] != "run_admitted_cypress_harmonic"
        or current_sources.get(entrypoint["path"])
        != _sha256(entrypoint["sha256"], "V6 runtime entrypoint sha256")
    ):
        raise ValueError("V7 runtime entrypoint is not the frozen V6 entrypoint")

    full_gate = {
        "case_count": gate["case_count"],
        "wins_vs_plain": gate["wins_vs_plain"],
        "wins_vs_placebo": gate["wins_vs_placebo"],
        "median_gain_vs_plain": gate["median_gain_vs_plain"],
        "median_gain_vs_placebo": gate["median_gain_vs_placebo"],
        "integrated_critical_errors": gate["integrated_critical_errors"],
    }
    return HarmonicRuntimeRegistryV7(
        schema_version="complexity_module_registry_v7",
        registry_sha256=hashlib.sha256(raw).hexdigest(),
        base_registry_sha256=predecessor_digest,
        modules=tuple(output),
        base_module_ids=tuple(item.module_id for item in base.modules),
        admitted_scope=dict(payload["admitted_scope"]),
        authority_flags=dict(payload["authority_flags"]),
        full_gate=full_gate,
        source_bindings=tuple(
            {"path": path, "sha256": digest}
            for path, digest in current_sources.items()
        ),
        material_data_fingerprint=current_material_digest,
        predecessor_registry_sha256=predecessor_digest,
        compatibility_rebindings=tuple(rebinding_rows),
        hash_policy=dict(payload["hash_policy"]),
    )


def load_harmonic_runtime_registry(
    root: Path,
    *,
    registry_path: Path | None = None,
) -> HarmonicRuntimeRegistryV6 | HarmonicRuntimeRegistryV7:
    project_root = root.resolve()
    selected = registry_path or project_root / CURRENT_HARMONIC_RUNTIME_REGISTRY_PATH
    path = selected if selected.is_absolute() else project_root / selected
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = payload.get("schema_version") if isinstance(payload, Mapping) else None
    if schema == "complexity_module_registry_v6":
        return _load_harmonic_runtime_registry_v6(
            project_root,
            registry_path=path,
        )
    if schema == "complexity_module_registry_v7":
        return _load_harmonic_runtime_registry_v7(project_root, path)
    raise ValueError("unsupported harmonic runtime registry schema")


__all__ = [
    "HarmonicRuntimeRegistryV6",
    "HarmonicRuntimeRegistryV7",
    "CURRENT_HARMONIC_RUNTIME_REGISTRY_PATH",
    "V6_ADMITTED_ARCHITECTURE_MODULE_IDS",
    "V6_EVIDENCE_ONLY_MODULE_IDS",
    "V6_GUARDRAIL_MODULE_IDS",
    "V6_REGISTRY_PATH",
    "V7_ADMITTED_ARCHITECTURE_MODULE_IDS",
    "V7_EVIDENCE_ONLY_MODULE_IDS",
    "V7_GUARDRAIL_MODULE_IDS",
    "V7_REGISTRY_PATH",
    "load_harmonic_runtime_registry",
]
