from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from engine.formulation_intelligence.admission import (
    MANDATORY_AUTHORITY_EXCLUSIONS,
    ArtifactClosure,
    ArtifactKind,
)
from engine.formulation_intelligence.contracts import AuthorityCeiling
from engine.formulation_intelligence.runtime_closure import (
    RuntimeClosureBundle,
    RuntimeModuleSpec,
    RuntimeResourceSpec,
    build_runtime_closure_bundle,
    load_runtime_closure_config,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _workspace(tmp_path: Path) -> Path:
    _write(tmp_path / "engine/formulation_intelligence/__init__.py", "from .core import X\n")
    _write(
        tmp_path / "engine/formulation_intelligence/core.py",
        "from __future__ import annotations\nfrom .leaf import VALUE\nX = VALUE\n",
    )
    _write(tmp_path / "engine/formulation_intelligence/leaf.py", "VALUE = 1\n")
    _write(tmp_path / "configs/formulation_intelligence/runtime.json", "{}\n")
    _write(tmp_path / "schemas/formulation_intelligence/registry.json", "{}\n")
    _write(tmp_path / "data/formulation_intelligence/corpus.json", "[]\n")
    return tmp_path


def _module_specs() -> tuple[RuntimeModuleSpec, ...]:
    return (
        RuntimeModuleSpec(
            module_id="package-init",
            module_name="engine.formulation_intelligence",
            capability_ids=("stable-package-boundary",),
            schema_artifact_ids=("schema:registry",),
            resource_artifact_ids=("config:runtime",),
            authority_ceiling=AuthorityCeiling.WITHHELD,
            exclusions=MANDATORY_AUTHORITY_EXCLUSIONS,
        ),
        RuntimeModuleSpec(
            module_id="core",
            module_name="engine.formulation_intelligence.core",
            capability_ids=("core-capability",),
            schema_artifact_ids=("schema:registry",),
            resource_artifact_ids=("data:corpus",),
            authority_ceiling=AuthorityCeiling.WITHHELD,
            exclusions=MANDATORY_AUTHORITY_EXCLUSIONS,
        ),
    )


def _resources() -> tuple[RuntimeResourceSpec, ...]:
    return (
        RuntimeResourceSpec(
            artifact_id="config:runtime",
            artifact_kind=ArtifactKind.CONFIG,
            relative_path="configs/formulation_intelligence/runtime.json",
        ),
        RuntimeResourceSpec(
            artifact_id="schema:registry",
            artifact_kind=ArtifactKind.SCHEMA,
            relative_path="schemas/formulation_intelligence/registry.json",
        ),
        RuntimeResourceSpec(
            artifact_id="data:corpus",
            artifact_kind=ArtifactKind.DATA,
            relative_path="data/formulation_intelligence/corpus.json",
        ),
    )


def test_generated_bundle_is_transitive_hash_bound_closed_and_deterministic(
    tmp_path: Path,
) -> None:
    root = _workspace(tmp_path)
    first = build_runtime_closure_bundle(
        root,
        package_prefix="engine.formulation_intelligence",
        closure_id="closure:test:v1",
        modules=_module_specs(),
        resources=_resources(),
    )
    second = build_runtime_closure_bundle(
        root,
        package_prefix="engine.formulation_intelligence",
        closure_id="closure:test:v1",
        modules=tuple(reversed(_module_specs())),
        resources=tuple(reversed(_resources())),
    )

    assert first == second
    assert first.content_sha256 == second.content_sha256
    assert RuntimeClosureBundle.from_dict(first.as_dict()) == first
    assert ArtifactClosure.from_dict(first.artifact_closure.as_dict()) == (
        first.artifact_closure
    )
    artifacts = {item.artifact_id: item for item in first.artifact_closure.artifacts}
    assert {item.artifact_kind for item in artifacts.values()} == set(ArtifactKind)
    assert {
        "source:engine.formulation_intelligence",
        "source:engine.formulation_intelligence.core",
        "source:engine.formulation_intelligence.leaf",
    }.issubset(artifacts)
    assert artifacts["source:engine.formulation_intelligence.core"].dependency_ids == (
        "data:corpus",
        "schema:registry",
        "source:engine.formulation_intelligence.leaf",
    )
    assert first.module_manifests[0].exclusions == tuple(
        sorted(MANDATORY_AUTHORITY_EXCLUSIONS)
    )


def test_content_change_invalidates_source_manifest_closure_and_bundle(
    tmp_path: Path,
) -> None:
    root = _workspace(tmp_path)
    first = build_runtime_closure_bundle(
        root,
        package_prefix="engine.formulation_intelligence",
        closure_id="closure:test:v1",
        modules=_module_specs(),
        resources=_resources(),
    )
    _write(root / "engine/formulation_intelligence/leaf.py", "VALUE = 2\n")
    second = build_runtime_closure_bundle(
        root,
        package_prefix="engine.formulation_intelligence",
        closure_id="closure:test:v1",
        modules=_module_specs(),
        resources=_resources(),
    )

    assert first.content_sha256 != second.content_sha256
    assert (
        first.artifact_closure.content_sha256
        != second.artifact_closure.content_sha256
    )
    assert {
        item.artifact_sha256
        for item in first.artifact_closure.artifacts
        if item.artifact_id.endswith(".leaf")
    } != {
        item.artifact_sha256
        for item in second.artifact_closure.artifacts
        if item.artifact_id.endswith(".leaf")
    }


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("import importlib\nX = importlib.import_module('engine.x')\n", "dynamic import"),
        ("X = __import__('engine.x')\n", "dynamic import"),
        ("from ...outside import X\n", "escapes package_prefix"),
    ),
)
def test_dynamic_or_package_escaping_imports_fail_closed(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    root = _workspace(tmp_path)
    _write(root / "engine/formulation_intelligence/core.py", source)
    with pytest.raises(ValueError, match=message):
        build_runtime_closure_bundle(
            root,
            package_prefix="engine.formulation_intelligence",
            closure_id="closure:test:v1",
            modules=_module_specs(),
            resources=_resources(),
        )


def test_local_import_cycle_and_missing_resource_fail_closed(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _write(root / "engine/formulation_intelligence/leaf.py", "from .core import X\n")
    with pytest.raises(ValueError, match="import cycle"):
        build_runtime_closure_bundle(
            root,
            package_prefix="engine.formulation_intelligence",
            closure_id="closure:test:v1",
            modules=_module_specs(),
            resources=_resources(),
        )

    root = _workspace(tmp_path / "missing")
    bad_resources = (
        *_resources()[:-1],
        RuntimeResourceSpec(
            artifact_id="data:corpus",
            artifact_kind=ArtifactKind.DATA,
            relative_path="data/formulation_intelligence/missing.json",
        ),
    )
    with pytest.raises(ValueError, match="does not exist"):
        build_runtime_closure_bundle(
            root,
            package_prefix="engine.formulation_intelligence",
            closure_id="closure:test:v1",
            modules=_module_specs(),
            resources=bad_resources,
        )


def test_exact_byte_seal_is_verified_and_bound_as_a_dependency(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    corpus = root / "data/formulation_intelligence/corpus.json"
    seal = root / "data/formulation_intelligence/corpus.sha256"
    _write(seal, sha256(corpus.read_bytes()).hexdigest() + "\n")
    resources = (
        *_resources(),
        RuntimeResourceSpec(
            artifact_id="data:corpus-seal",
            artifact_kind=ArtifactKind.DATA,
            relative_path="data/formulation_intelligence/corpus.sha256",
            content_sha256_of="data:corpus",
        ),
    )
    modules = tuple(
        RuntimeModuleSpec(
            module_id=item.module_id,
            module_name=item.module_name,
            capability_ids=item.capability_ids,
            schema_artifact_ids=item.schema_artifact_ids,
            resource_artifact_ids=(
                ("data:corpus-seal",)
                if item.module_id == "core"
                else item.resource_artifact_ids
            ),
            authority_ceiling=item.authority_ceiling,
            exclusions=item.exclusions,
        )
        for item in _module_specs()
    )
    bundle = build_runtime_closure_bundle(
        root,
        package_prefix="engine.formulation_intelligence",
        closure_id="closure:test:sealed:v1",
        modules=modules,
        resources=resources,
    )
    artifacts = {item.artifact_id: item for item in bundle.artifact_closure.artifacts}
    assert artifacts["data:corpus-seal"].dependency_ids == ("data:corpus",)

    _write(seal, "0" * 64 + "\n")
    with pytest.raises(ValueError, match="does not match"):
        build_runtime_closure_bundle(
            root,
            package_prefix="engine.formulation_intelligence",
            closure_id="closure:test:sealed:v1",
            modules=modules,
            resources=resources,
        )


def test_closed_config_loader_rejects_duplicate_keys_and_unknown_fields(
    tmp_path: Path,
) -> None:
    config = tmp_path / "runtime.json"
    config.write_text('{"schema_version":"runtime_closure_config_v1", "x":1, "x":2}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_runtime_closure_config(config)

    config.write_text(
        json.dumps(
            {
                "schema_version": "runtime_closure_config_v1",
                "package_prefix": "engine.formulation_intelligence",
                "closure_id": "closure:test:v1",
                "modules": [],
                "resources": [],
                "unexpected": True,
            }
        )
    )
    with pytest.raises(ValueError, match="closed schema"):
        load_runtime_closure_config(config)
