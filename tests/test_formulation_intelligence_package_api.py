from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import engine.formulation_intelligence as package

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "engine.formulation_intelligence"
STABLE_CORE_MODULES = frozenset(
    {
        f"{PACKAGE_NAME}.contracts",
        f"{PACKAGE_NAME}.plane_synthesis",
    }
)
STABLE_CORE_EXPORTS = (
    "AssessmentScope",
    "AuthorityCeiling",
    "ClaimCardinality",
    "ClaimKind",
    "CriterionDirection",
    "CriterionValue",
    "EvidenceClass",
    "HarmonizedClaim",
    "ParetoCriterion",
    "PlaneAssessment",
    "PlaneAssessmentAdapter",
    "PlaneConflict",
    "PlaneId",
    "PlaneSynthesisResult",
    "ProvenanceRef",
    "ScopedClaim",
    "ScopedNativeCriterion",
    "ScopedUnknown",
    "SupportInterval",
    "SupportMeasure",
    "SynthesisConflict",
    "UnitInterval",
    "UnknownFact",
    "ValueState",
    "synthesize_plane_assessments",
    "synthesize_planes",
)
RUNTIME_ENABLEMENT_NAMES = frozenset(
    {
        "ADMITTED_MODULES",
        "ENABLED_MODULES",
        "RUNTIME_ENABLED",
        "RUNTIME_INTEGRATION_ENABLED",
        "RUNTIME_MODULES",
        "admitted_modules",
        "enabled_modules",
        "runtime_enabled",
        "runtime_integration_enabled",
        "runtime_modules",
    }
)


def _run_fresh_import(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_package_all_is_exactly_the_stable_structural_core() -> None:
    assert tuple(package.__all__) == STABLE_CORE_EXPORTS
    assert len(package.__all__) == len(set(package.__all__))


def test_every_package_export_exists_and_is_bound_to_a_stable_core_module() -> None:
    for export_name in package.__all__:
        exported = getattr(package, export_name)
        defining_module_name = getattr(exported, "__module__", None)

        assert defining_module_name in STABLE_CORE_MODULES
        defining_module = importlib.import_module(defining_module_name)
        assert getattr(defining_module, export_name) is exported


def test_fresh_package_import_loads_only_the_stable_core() -> None:
    code = f"""
import json
import sys

import {PACKAGE_NAME}

package_prefix = {PACKAGE_NAME!r}
loaded_package_modules = sorted(
    name
    for name in sys.modules
    if name == package_prefix or name.startswith(package_prefix + ".")
)
forbidden_prefixes = (
    "faiss",
    "sentence_transformers",
    "torch",
    "engine.formula",
    "engine.pipeline",
    "engine.target.formula",
)
forbidden_loaded = sorted(
    name
    for name in sys.modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
)
print(json.dumps({{
    "loaded_package_modules": loaded_package_modules,
    "forbidden_loaded": forbidden_loaded,
}}, sort_keys=True))
"""

    completed = _run_fresh_import(code)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    result = json.loads(completed.stdout)
    assert result == {
        "forbidden_loaded": [],
        "loaded_package_modules": [PACKAGE_NAME, *sorted(STABLE_CORE_MODULES)],
    }


def test_package_import_performs_no_application_file_network_or_process_io() -> None:
    code = f"""
import builtins
import json
import os
import pathlib
import socket
import subprocess
import sys
import urllib.request

blocked_calls = []
audit_events = []

def deny(label):
    def denied(*args, **kwargs):
        blocked_calls.append(label)
        raise AssertionError("import-time side effect: " + label)
    return denied

write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
mutation_events = {{
    "os.chdir",
    "os.chmod",
    "os.link",
    "os.mkdir",
    "os.remove",
    "os.rename",
    "os.rmdir",
    "os.symlink",
    "os.system",
    "os.truncate",
    "subprocess.Popen",
}}

def audit(event, args):
    if event == "open":
        mode = str(args[1] or "")
        flags = int(args[2]) if isinstance(args[2], int) else 0
        if any(marker in mode for marker in ("a", "+", "w", "x")) or flags & write_flags:
            audit_events.append(event)
    elif event.startswith("socket.") or event.startswith("os.spawn"):
        audit_events.append(event)
    elif event in mutation_events:
        audit_events.append(event)

sys.addaudithook(audit)

builtins.open = deny("builtins.open")
os.open = deny("os.open")
os.popen = deny("os.popen")
os.system = deny("os.system")
pathlib.Path.open = deny("Path.open")
pathlib.Path.read_bytes = deny("Path.read_bytes")
pathlib.Path.read_text = deny("Path.read_text")
pathlib.Path.write_bytes = deny("Path.write_bytes")
pathlib.Path.write_text = deny("Path.write_text")
socket.create_connection = deny("socket.create_connection")
socket.socket = deny("socket.socket")
subprocess.Popen = deny("subprocess.Popen")
subprocess.call = deny("subprocess.call")
subprocess.check_call = deny("subprocess.check_call")
subprocess.check_output = deny("subprocess.check_output")
subprocess.run = deny("subprocess.run")
urllib.request.urlopen = deny("urllib.request.urlopen")

import {PACKAGE_NAME}

print(json.dumps({{
    "audit_events": audit_events,
    "blocked_calls": blocked_calls,
}}, sort_keys=True))
"""

    completed = _run_fresh_import(code)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout) == {"audit_events": [], "blocked_calls": []}


def test_unadmitted_modules_have_no_package_or_runtime_enablement_surface() -> None:
    package_dir = Path(package.__file__).resolve().parent
    unadmitted_module_names = {
        path.stem
        for path in package_dir.glob("*.py")
        if path.stem not in {"__init__", "contracts", "plane_synthesis"}
    }

    assert unadmitted_module_names
    code = f"""
import json
import {PACKAGE_NAME} as package

unadmitted = {sorted(unadmitted_module_names)!r}
runtime_names = {sorted(RUNTIME_ENABLEMENT_NAMES)!r}
print(json.dumps({{
    "exposed_unadmitted": sorted(set(unadmitted) & set(vars(package))),
    "runtime_names": sorted(set(runtime_names) & set(vars(package))),
    "has_dynamic_getattr": "__getattr__" in vars(package),
}}, sort_keys=True))
"""
    completed = _run_fresh_import(code)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(completed.stdout) == {
        "exposed_unadmitted": [],
        "has_dynamic_getattr": False,
        "runtime_names": [],
    }
