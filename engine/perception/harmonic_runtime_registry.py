"""Additive exact-byte admission registry for the Cypress harmonic runtime.

V5 is immutable historical provenance: its loader and hash-bound public files
remain unchanged.  This module loads that exact V5 registry, verifies the new
screening and confirmation receipts, verifies every V6 source and inventory
binding, and then creates a narrow additive view for the admitted CYP-02
architecture runtime.

The V6 admission does not admit evidence-only routing.  Temporal and
preference components therefore remain nonruntime evidence capabilities even
though architecture requests may retain them as claim-withholding boundaries.
No registry state grants formula, physical, sensory, hedonic, safety,
stability, purchase, scientific, or release authority.
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
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
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


def load_harmonic_runtime_registry(
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


__all__ = [
    "HarmonicRuntimeRegistryV6",
    "V6_ADMITTED_ARCHITECTURE_MODULE_IDS",
    "V6_EVIDENCE_ONLY_MODULE_IDS",
    "V6_GUARDRAIL_MODULE_IDS",
    "V6_REGISTRY_PATH",
    "load_harmonic_runtime_registry",
]
