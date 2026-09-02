"""Deterministic, path-confined runtime artifact-closure generation.

The builder statically traverses only imports inside the declared package,
hashes the exact source/config/schema/data bytes, and emits the admission
contracts consumed by :mod:`engine.formulation_intelligence.admission`.  It
does not import candidate modules, execute dynamic imports, scan unrelated
repository state, or grant runtime admission.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from .admission import (
    ArtifactBinding,
    ArtifactClosure,
    ArtifactKind,
    CapabilityBinding,
    ModuleAdmissionManifest,
    SchemaBinding,
)
from .contracts import AuthorityCeiling, _canonical_json_bytes

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _identifier(value: str, field_name: str) -> str:
    normalized = _text(value, field_name)
    if _IDENTIFIER.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} is not a valid identifier")
    return normalized


def _module_name(value: str, field_name: str) -> str:
    normalized = _text(value, field_name)
    if _MODULE.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} is not a valid Python module name")
    return normalized


def _unique_text(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_identifier(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _unique_free_text(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return tuple(sorted(normalized))


def _relative_path(value: str, field_name: str) -> str:
    normalized = _text(value, field_name).replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field_name} must be a confined relative path")
    return path.as_posix()


def _strict_fields(
    payload: Mapping[str, Any],
    expected: set[str],
    record_name: str,
) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{record_name} uses a closed schema; missing={missing!r}, extra={extra!r}"
        )


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{field_name} keys must be str")
    return value


def _sequence(value: Any, field_name: str) -> tuple[Any, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a JSON array")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class RuntimeResourceSpec:
    """One explicit non-source artifact included in the runtime closure."""

    SCHEMA_VERSION = "runtime_closure_resource_spec_v1"

    artifact_id: str
    artifact_kind: ArtifactKind
    relative_path: str
    dependency_ids: tuple[str, ...] = ()
    content_sha256_of: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_id",
            _identifier(self.artifact_id, "artifact_id"),
        )
        kind = ArtifactKind(self.artifact_kind)
        if kind is ArtifactKind.SOURCE:
            raise ValueError("RuntimeResourceSpec cannot declare source artifacts")
        object.__setattr__(self, "artifact_kind", kind)
        object.__setattr__(
            self,
            "relative_path",
            _relative_path(self.relative_path, "relative_path"),
        )
        dependencies = _unique_text(self.dependency_ids, "dependency_ids")
        if self.artifact_id in dependencies:
            raise ValueError("a resource cannot depend on itself")
        object.__setattr__(self, "dependency_ids", dependencies)
        target = (
            _identifier(self.content_sha256_of, "content_sha256_of")
            if self.content_sha256_of is not None
            else None
        )
        if target == self.artifact_id:
            raise ValueError("a seal resource cannot seal itself")
        object.__setattr__(self, "content_sha256_of", target)
        if target is not None:
            object.__setattr__(
                self,
                "dependency_ids",
                tuple(sorted({*dependencies, target})),
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind.value,
            "relative_path": self.relative_path,
            "dependency_ids": list(self.dependency_ids),
            "content_sha256_of": self.content_sha256_of,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RuntimeResourceSpec:
        _strict_fields(
            payload,
            {
                "schema_version",
                "artifact_id",
                "artifact_kind",
                "relative_path",
                "dependency_ids",
                "content_sha256_of",
            },
            cls.__name__,
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("unsupported RuntimeResourceSpec schema_version")
        return cls(
            artifact_id=payload["artifact_id"],
            artifact_kind=ArtifactKind(payload["artifact_kind"]),
            relative_path=payload["relative_path"],
            dependency_ids=tuple(_sequence(payload["dependency_ids"], "dependency_ids")),
            content_sha256_of=payload["content_sha256_of"],
        )


@dataclass(frozen=True, slots=True)
class RuntimeModuleSpec:
    """One runtime entrypoint and its declared interface/resource bindings."""

    SCHEMA_VERSION = "runtime_closure_module_spec_v1"

    module_id: str
    module_name: str
    capability_ids: tuple[str, ...]
    schema_artifact_ids: tuple[str, ...]
    resource_artifact_ids: tuple[str, ...]
    authority_ceiling: AuthorityCeiling
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _identifier(self.module_id, "module_id"))
        object.__setattr__(
            self,
            "module_name",
            _module_name(self.module_name, "module_name"),
        )
        capabilities = _unique_text(self.capability_ids, "capability_ids")
        schemas = _unique_text(self.schema_artifact_ids, "schema_artifact_ids")
        resources = _unique_text(self.resource_artifact_ids, "resource_artifact_ids")
        exclusions = _unique_free_text(self.exclusions, "exclusions")
        if not capabilities:
            raise ValueError("capability_ids must not be empty")
        if not schemas:
            raise ValueError("schema_artifact_ids must not be empty")
        if not exclusions:
            raise ValueError("exclusions must not be empty")
        object.__setattr__(self, "capability_ids", capabilities)
        object.__setattr__(self, "schema_artifact_ids", schemas)
        object.__setattr__(self, "resource_artifact_ids", resources)
        object.__setattr__(self, "authority_ceiling", AuthorityCeiling(self.authority_ceiling))
        object.__setattr__(self, "exclusions", exclusions)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_id": self.module_id,
            "module_name": self.module_name,
            "capability_ids": list(self.capability_ids),
            "schema_artifact_ids": list(self.schema_artifact_ids),
            "resource_artifact_ids": list(self.resource_artifact_ids),
            "authority_ceiling": self.authority_ceiling.value,
            "exclusions": list(self.exclusions),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RuntimeModuleSpec:
        _strict_fields(
            payload,
            {
                "schema_version",
                "module_id",
                "module_name",
                "capability_ids",
                "schema_artifact_ids",
                "resource_artifact_ids",
                "authority_ceiling",
                "exclusions",
            },
            cls.__name__,
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("unsupported RuntimeModuleSpec schema_version")
        return cls(
            module_id=payload["module_id"],
            module_name=payload["module_name"],
            capability_ids=tuple(_sequence(payload["capability_ids"], "capability_ids")),
            schema_artifact_ids=tuple(
                _sequence(payload["schema_artifact_ids"], "schema_artifact_ids")
            ),
            resource_artifact_ids=tuple(
                _sequence(payload["resource_artifact_ids"], "resource_artifact_ids")
            ),
            authority_ceiling=AuthorityCeiling(payload["authority_ceiling"]),
            exclusions=tuple(_sequence(payload["exclusions"], "exclusions")),
        )


@dataclass(frozen=True, slots=True)
class RuntimeClosureConfig:
    SCHEMA_VERSION = "runtime_closure_config_v1"

    package_prefix: str
    closure_id: str
    modules: tuple[RuntimeModuleSpec, ...]
    resources: tuple[RuntimeResourceSpec, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "package_prefix",
            _module_name(self.package_prefix, "package_prefix"),
        )
        object.__setattr__(self, "closure_id", _identifier(self.closure_id, "closure_id"))
        modules = tuple(sorted(self.modules, key=lambda item: item.module_id))
        resources = tuple(sorted(self.resources, key=lambda item: item.artifact_id))
        if not modules or not resources:
            raise ValueError("runtime closure config requires modules and resources")
        if len({item.module_id for item in modules}) != len(modules):
            raise ValueError("modules must contain unique module_id values")
        if len({item.module_name for item in modules}) != len(modules):
            raise ValueError("modules must contain unique module_name values")
        if len({item.artifact_id for item in resources}) != len(resources):
            raise ValueError("resources must contain unique artifact_id values")
        object.__setattr__(self, "modules", modules)
        object.__setattr__(self, "resources", resources)


@dataclass(frozen=True, slots=True)
class RuntimeClosureBundle:
    """Generated closure plus exact module manifests and entrypoint roots."""

    SCHEMA_VERSION = "runtime_closure_bundle_v1"

    package_prefix: str
    artifact_closure: ArtifactClosure
    module_manifests: tuple[ModuleAdmissionManifest, ...]
    entrypoint_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        prefix = _module_name(self.package_prefix, "package_prefix")
        object.__setattr__(self, "package_prefix", prefix)
        if not isinstance(self.artifact_closure, ArtifactClosure):
            raise TypeError("artifact_closure must be an ArtifactClosure")
        manifests = tuple(sorted(self.module_manifests, key=lambda item: item.module_id))
        if not manifests or any(
            not isinstance(item, ModuleAdmissionManifest) for item in manifests
        ):
            raise TypeError("module_manifests must contain ModuleAdmissionManifest records")
        if len({item.module_id for item in manifests}) != len(manifests):
            raise ValueError("module_manifests must contain unique module_id values")
        entrypoints = _unique_text(
            self.entrypoint_artifact_ids,
            "entrypoint_artifact_ids",
        )
        expected = tuple(sorted(item.source_artifact_id for item in manifests))
        if entrypoints != expected:
            raise ValueError("entrypoint_artifact_ids must match every module manifest")
        artifacts = {item.artifact_id: item for item in self.artifact_closure.artifacts}
        for manifest in manifests:
            source = artifacts.get(manifest.source_artifact_id)
            if source is None or source.artifact_kind is not ArtifactKind.SOURCE:
                raise ValueError("module manifest source is absent from closure")
            if source.artifact_path != manifest.module_path:
                raise ValueError("module manifest path does not match closure")
            if source.artifact_sha256 != manifest.source_sha256:
                raise ValueError("module manifest hash does not match closure")
            for schema in manifest.schemas:
                artifact = artifacts.get(schema.schema_id)
                if artifact is None or artifact.artifact_kind is not ArtifactKind.SCHEMA:
                    raise ValueError("module manifest schema is absent from closure")
                if artifact.artifact_sha256 != schema.schema_sha256:
                    raise ValueError("module manifest schema hash does not match closure")
        object.__setattr__(self, "module_manifests", manifests)
        object.__setattr__(self, "entrypoint_artifact_ids", entrypoints)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "package_prefix": self.package_prefix,
            "artifact_closure": self.artifact_closure.as_dict(),
            "module_manifests": [item.as_dict() for item in self.module_manifests],
            "entrypoint_artifact_ids": list(self.entrypoint_artifact_ids),
        }

    @property
    def content_sha256(self) -> str:
        return sha256(_canonical_json_bytes(self.as_dict())).hexdigest()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RuntimeClosureBundle:
        _strict_fields(
            payload,
            {
                "schema_version",
                "package_prefix",
                "artifact_closure",
                "module_manifests",
                "entrypoint_artifact_ids",
            },
            cls.__name__,
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("unsupported RuntimeClosureBundle schema_version")
        return cls(
            package_prefix=payload["package_prefix"],
            artifact_closure=ArtifactClosure.from_dict(
                _mapping(payload["artifact_closure"], "artifact_closure")
            ),
            module_manifests=tuple(
                ModuleAdmissionManifest.from_dict(
                    _mapping(item, "module_manifests item")
                )
                for item in _sequence(payload["module_manifests"], "module_manifests")
            ),
            entrypoint_artifact_ids=tuple(
                _sequence(payload["entrypoint_artifact_ids"], "entrypoint_artifact_ids")
            ),
        )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_runtime_closure_config(path: Path) -> RuntimeClosureConfig:
    """Load a strict config without importing or executing candidate modules."""

    if not isinstance(path, Path):
        raise TypeError("path must be a pathlib.Path")
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    payload = _mapping(data, "runtime closure config")
    _strict_fields(
        payload,
        {"schema_version", "package_prefix", "closure_id", "modules", "resources"},
        RuntimeClosureConfig.__name__,
    )
    if payload["schema_version"] != RuntimeClosureConfig.SCHEMA_VERSION:
        raise ValueError("unsupported runtime closure config schema_version")
    return RuntimeClosureConfig(
        package_prefix=payload["package_prefix"],
        closure_id=payload["closure_id"],
        modules=tuple(
            RuntimeModuleSpec.from_dict(_mapping(item, "modules item"))
            for item in _sequence(payload["modules"], "modules")
        ),
        resources=tuple(
            RuntimeResourceSpec.from_dict(_mapping(item, "resources item"))
            for item in _sequence(payload["resources"], "resources")
        ),
    )


def _confined_file(root: Path, relative_path: str) -> Path:
    candidate = root.joinpath(*PurePosixPath(relative_path).parts)
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    if candidate.is_symlink() or is_junction(candidate):
        raise ValueError(f"closure artifact may not be a symlink: {relative_path}")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ValueError(f"closure artifact escapes workspace root: {relative_path}")
    if not candidate.is_file():
        raise ValueError(f"closure artifact does not exist: {relative_path}")
    return candidate


def _stable_file_sha256(path: Path, relative_path: str) -> str:
    before = path.stat()
    with path.open("rb") as handle:
        payload = handle.read()
        during = os.fstat(handle.fileno())
    after = path.stat()
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_during = (
        during.st_dev,
        during.st_ino,
        during.st_size,
        during.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_during or identity_before != identity_after:
        raise ValueError(f"closure artifact changed while hashing: {relative_path}")
    return sha256(payload).hexdigest()


def _module_relative_path(
    root: Path,
    package_prefix: str,
    module_name: str,
) -> str:
    if module_name != package_prefix and not module_name.startswith(package_prefix + "."):
        raise ValueError(f"module {module_name!r} escapes package_prefix")
    parts = module_name.split(".")
    module_file = root.joinpath(*parts).with_suffix(".py")
    package_file = root.joinpath(*parts, "__init__.py")
    if module_name == package_prefix and package_file.is_file():
        path = package_file
    elif module_file.is_file():
        path = module_file
    elif package_file.is_file():
        path = package_file
    else:
        raise ValueError(f"local module does not exist: {module_name}")
    relative = path.relative_to(root).as_posix()
    _confined_file(root, relative)
    return relative


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return None


def _local_imports(
    *,
    root: Path,
    package_prefix: str,
    module_name: str,
    relative_path: str,
) -> tuple[str, ...]:
    source_path = _confined_file(root, relative_path)
    try:
        tree = ast.parse(source_path.read_bytes(), filename=relative_path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot statically parse {relative_path}: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) in {
            "__import__",
            "importlib.import_module",
        }:
            raise ValueError(f"dynamic import is forbidden in runtime closure: {relative_path}")

    current_is_package = relative_path.endswith("/__init__.py")
    current_package = module_name if current_is_package else module_name.rpartition(".")[0]
    result: set[str] = set()
    for node in ast.walk(tree):
        targets: tuple[str, ...] = ()
        if isinstance(node, ast.Import):
            targets = tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative_name = "." * node.level + (node.module or "")
                try:
                    base = importlib.util.resolve_name(relative_name, current_package)
                except (ImportError, ValueError) as exc:
                    raise ValueError(
                        f"relative import escapes package_prefix in {relative_path}"
                    ) from exc
                targets = (
                    tuple(f"{base}.{alias.name}" for alias in node.names)
                    if node.module is None
                    else (base,)
                )
            elif node.module is not None:
                targets = (node.module,)
        for target in targets:
            if target == package_prefix or target.startswith(package_prefix + "."):
                _module_relative_path(root, package_prefix, target)
                result.add(target)
            elif isinstance(node, ast.ImportFrom) and node.level:
                raise ValueError(
                    f"relative import escapes package_prefix in {relative_path}: {target}"
                )
    return tuple(sorted(result))


def _assert_acyclic(dependencies: Mapping[str, tuple[str, ...]]) -> None:
    state: dict[str, int] = {}

    def visit(artifact_id: str, stack: tuple[str, ...]) -> None:
        marker = state.get(artifact_id, 0)
        if marker == 1:
            cycle = " -> ".join((*stack, artifact_id))
            raise ValueError(f"runtime import cycle detected: {cycle}")
        if marker == 2:
            return
        state[artifact_id] = 1
        for dependency in dependencies.get(artifact_id, ()):
            if dependency.startswith("source:"):
                visit(dependency, (*stack, artifact_id))
        state[artifact_id] = 2

    for artifact_id in sorted(dependencies):
        visit(artifact_id, ())


def build_runtime_closure_bundle(
    workspace_root: Path,
    *,
    package_prefix: str,
    closure_id: str,
    modules: Iterable[RuntimeModuleSpec],
    resources: Iterable[RuntimeResourceSpec],
) -> RuntimeClosureBundle:
    """Generate an exact static closure and its admission manifests."""

    if not isinstance(workspace_root, Path):
        raise TypeError("workspace_root must be a pathlib.Path")
    root = workspace_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    prefix = _module_name(package_prefix, "package_prefix")
    normalized_closure_id = _identifier(closure_id, "closure_id")
    module_records = tuple(sorted(modules, key=lambda item: item.module_id))
    resource_records = tuple(sorted(resources, key=lambda item: item.artifact_id))
    if not module_records or any(
        not isinstance(item, RuntimeModuleSpec) for item in module_records
    ):
        raise TypeError("modules must contain RuntimeModuleSpec records")
    if not resource_records or any(
        not isinstance(item, RuntimeResourceSpec) for item in resource_records
    ):
        raise TypeError("resources must contain RuntimeResourceSpec records")
    if len({item.module_id for item in module_records}) != len(module_records):
        raise ValueError("modules must contain unique module_id values")
    if len({item.module_name for item in module_records}) != len(module_records):
        raise ValueError("modules must contain unique module_name values")
    if len({item.artifact_id for item in resource_records}) != len(resource_records):
        raise ValueError("resources must contain unique artifact_id values")
    if len({item.module_id.casefold() for item in module_records}) != len(module_records):
        raise ValueError("modules contain a case-fold module_id collision")
    if len({item.module_name.casefold() for item in module_records}) != len(
        module_records
    ):
        raise ValueError("modules contain a case-fold module_name collision")
    if len({item.artifact_id.casefold() for item in resource_records}) != len(
        resource_records
    ):
        raise ValueError("resources contain a case-fold artifact_id collision")
    if len({item.relative_path.casefold() for item in resource_records}) != len(
        resource_records
    ):
        raise ValueError("resources contain a case-fold path collision")
    if not any(item.module_name == prefix for item in module_records):
        raise ValueError("modules must include the package initializer entrypoint")

    resource_bindings: dict[str, ArtifactBinding] = {}
    for resource in resource_records:
        path = _confined_file(root, resource.relative_path)
        resource_bindings[resource.artifact_id] = ArtifactBinding(
            artifact_id=resource.artifact_id,
            artifact_kind=resource.artifact_kind,
            artifact_path=resource.relative_path,
            artifact_sha256=_stable_file_sha256(path, resource.relative_path),
            dependency_ids=resource.dependency_ids,
        )
    resource_ids = set(resource_bindings)
    for resource in resource_records:
        missing = sorted(set(resource.dependency_ids) - resource_ids)
        if missing:
            raise ValueError(
                f"resource {resource.artifact_id!r} cites missing dependencies: {missing!r}"
            )
    for resource in resource_records:
        if resource.content_sha256_of is None:
            continue
        target = resource_bindings.get(resource.content_sha256_of)
        if target is None:
            raise ValueError(
                f"seal resource {resource.artifact_id!r} cites missing target "
                f"{resource.content_sha256_of!r}"
            )
        seal_path = _confined_file(root, resource.relative_path)
        seal_text = seal_path.read_text(encoding="ascii").strip()
        if re.fullmatch(r"[0-9a-f]{64}", seal_text) is None:
            raise ValueError(
                f"seal resource {resource.artifact_id!r} must contain one lowercase digest"
            )
        if seal_text != target.artifact_sha256:
            raise ValueError(
                f"seal resource {resource.artifact_id!r} does not match "
                f"{resource.content_sha256_of!r}"
            )

    spec_by_module = {item.module_name: item for item in module_records}
    pending = list(spec_by_module)
    source_paths: dict[str, str] = {}
    source_imports: dict[str, tuple[str, ...]] = {}
    while pending:
        module_name = pending.pop()
        if module_name in source_paths:
            continue
        relative_path = _module_relative_path(root, prefix, module_name)
        imports = _local_imports(
            root=root,
            package_prefix=prefix,
            module_name=module_name,
            relative_path=relative_path,
        )
        source_paths[module_name] = relative_path
        source_imports[module_name] = imports
        pending.extend(item for item in imports if item not in source_paths)

    source_bindings: dict[str, ArtifactBinding] = {}
    dependency_graph: dict[str, tuple[str, ...]] = {}
    for module_name in sorted(source_paths):
        artifact_id = f"source:{module_name}"
        spec = spec_by_module.get(module_name)
        declared_resources = (
            (*spec.resource_artifact_ids, *spec.schema_artifact_ids) if spec else ()
        )
        missing = sorted(set(declared_resources) - resource_ids)
        if missing:
            raise ValueError(
                f"module {module_name!r} cites missing resources: {missing!r}"
            )
        dependencies = tuple(
            sorted(
                {
                    *(f"source:{item}" for item in source_imports[module_name]),
                    *declared_resources,
                }
            )
        )
        relative_path = source_paths[module_name]
        source_path = _confined_file(root, relative_path)
        source_bindings[artifact_id] = ArtifactBinding(
            artifact_id=artifact_id,
            artifact_kind=ArtifactKind.SOURCE,
            artifact_path=relative_path,
            artifact_sha256=_stable_file_sha256(source_path, relative_path),
            dependency_ids=dependencies,
        )
        dependency_graph[artifact_id] = dependencies
    _assert_acyclic(dependency_graph)

    artifacts = {**source_bindings, **resource_bindings}
    entrypoint_ids = tuple(
        sorted(f"source:{item.module_name}" for item in module_records)
    )
    reachable: set[str] = set()
    stack = list(entrypoint_ids)
    while stack:
        artifact_id = stack.pop()
        if artifact_id in reachable:
            continue
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"closure dependency is absent: {artifact_id}")
        reachable.add(artifact_id)
        stack.extend(artifact.dependency_ids)
    unreachable = sorted(set(artifacts) - reachable)
    if unreachable:
        raise ValueError(f"runtime closure contains unreachable artifacts: {unreachable!r}")
    present_kinds = {item.artifact_kind for item in artifacts.values()}
    if present_kinds != set(ArtifactKind):
        missing_kinds = sorted(item.value for item in set(ArtifactKind) - present_kinds)
        raise ValueError(f"runtime closure is missing artifact kinds: {missing_kinds!r}")

    closure = ArtifactClosure(
        closure_id=normalized_closure_id,
        artifacts=tuple(artifacts.values()),
    )
    manifests: list[ModuleAdmissionManifest] = []
    for spec in module_records:
        source = source_bindings[f"source:{spec.module_name}"]
        capabilities = tuple(
            CapabilityBinding(
                capability_id=f"{spec.module_id}:{capability_id}",
                capability_sha256=sha256(
                    _canonical_json_bytes(
                        {
                            "schema_version": "runtime_capability_identity_v1",
                            "module_id": spec.module_id,
                            "capability_id": capability_id,
                            "source_sha256": source.artifact_sha256,
                        }
                    )
                ).hexdigest(),
            )
            for capability_id in spec.capability_ids
        )
        schemas = tuple(
            SchemaBinding(
                schema_id=artifact_id,
                schema_sha256=resource_bindings[artifact_id].artifact_sha256,
            )
            for artifact_id in spec.schema_artifact_ids
        )
        manifests.append(
            ModuleAdmissionManifest(
                module_id=spec.module_id,
                module_path=source.artifact_path,
                source_sha256=source.artifact_sha256,
                source_artifact_id=source.artifact_id,
                capabilities=capabilities,
                schemas=schemas,
                authority_ceiling=spec.authority_ceiling,
                exclusions=spec.exclusions,
            )
        )
    return RuntimeClosureBundle(
        package_prefix=prefix,
        artifact_closure=closure,
        module_manifests=tuple(manifests),
        entrypoint_artifact_ids=entrypoint_ids,
    )


def build_runtime_closure_from_config(
    workspace_root: Path,
    config: RuntimeClosureConfig,
) -> RuntimeClosureBundle:
    if not isinstance(config, RuntimeClosureConfig):
        raise TypeError("config must be a RuntimeClosureConfig")
    return build_runtime_closure_bundle(
        workspace_root,
        package_prefix=config.package_prefix,
        closure_id=config.closure_id,
        modules=config.modules,
        resources=config.resources,
    )


__all__ = [
    "RuntimeClosureBundle",
    "RuntimeClosureConfig",
    "RuntimeModuleSpec",
    "RuntimeResourceSpec",
    "build_runtime_closure_bundle",
    "build_runtime_closure_from_config",
    "load_runtime_closure_config",
]
