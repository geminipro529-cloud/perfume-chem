"""requirements.txt must cover every third-party package engine/ and scripts/ import.

AST-scans engine/ and scripts/ so a fresh ``pip install -r requirements.txt``
does not miss a package. Imports guarded by ``try: ... except ImportError`` are
optional and are not required. The reverse direction (requirements entries that
nothing imports) is deliberately not asserted: sentence-transformers, torch and
others are used indirectly.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("engine", "scripts")

# import name -> distribution name in requirements.txt (compared normalized)
IMPORT_TO_DISTRIBUTION = {
    "numpy": "numpy",
    "pandas": "pandas",
    "requests": "requests",
    "psutil": "psutil",
    "scipy": "scipy",
    "yaml": "PyYAML",
    "openpyxl": "openpyxl",
    "rdkit": "rdkit",
    "sklearn": "scikit-learn",
    "sqlalchemy": "SQLAlchemy",
    "matplotlib": "matplotlib",
    "mcp": "mcp",
    "opentelemetry": "opentelemetry-sdk",
    "sentence_transformers": "sentence-transformers",
    "faiss": "faiss-cpu",
    "thermo": "thermo",
    "chemicals": "chemicals",
    "fluids": "fluids",
    "torch": "torch",
    "transformers": "transformers",
    "huggingface_hub": "huggingface-hub",
}

# Imports that only ever appear inside a ``try`` that catches ImportError.
# Listed explicitly so a new optional import is a reviewed decision.
OPTIONAL_IMPORTS: set[str] = {
    "pooch",  # engine/ingestion/scientific.py: optional download helper
    "pyrfume",  # scripts/integrate_external_data.py: optional dataset source
}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_names() -> set[str]:
    names = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
        if match:
            names.add(_normalize(match.group(0)))
    return names


def _local_names() -> set[str]:
    local = {"engine", "app", "scripts", "tests", "backend"}
    for base in (ROOT, ROOT / "scripts", ROOT / "engine", ROOT / "tests"):
        for item in base.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir() or item.suffix == ".py":
                local.add(item.stem if item.suffix == ".py" else item.name)
    return local


def _catches_import_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        types = []
        if isinstance(handler.type, ast.Tuple):
            types = handler.type.elts
        elif handler.type is not None:
            types = [handler.type]
        for item in types:
            if isinstance(item, ast.Name) and item.id in {
                "ImportError",
                "ModuleNotFoundError",
            }:
                return True
    return False


def _collect() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (required, optional): top-level import name -> files importing it."""
    required: dict[str, set[str]] = {}
    optional: dict[str, set[str]] = {}
    local = _local_names()
    stdlib = set(sys.stdlib_module_names)

    def visit(node: ast.AST, guarded: bool, rel: str) -> None:
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [] if node.level or not node.module else [node.module]
        else:
            modules = []
        for module in modules:
            top = module.split(".", 1)[0]
            if top in stdlib or top in local or top == "__future__":
                continue
            (optional if guarded else required).setdefault(top, set()).add(rel)
        for child in ast.iter_child_nodes(node):
            child_guarded = guarded
            if isinstance(node, ast.Try) and child in node.body and _catches_import_error(node):
                child_guarded = True
            visit(child, child_guarded, rel)

    for directory in SCAN_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            try:
                tree = ast.parse(path.read_bytes())
            except SyntaxError:
                continue
            visit(tree, False, rel)
    return required, optional


def test_every_required_third_party_import_has_a_requirements_entry():
    required, optional = _collect()
    unmapped = sorted(name for name in required if name not in IMPORT_TO_DISTRIBUTION)
    assert not unmapped, (
        "Third-party imports with no import-name -> distribution mapping in this "
        f"test (add the mapping and a requirements.txt line): {unmapped}"
    )
    present = _requirement_names()
    missing = sorted(
        {
            IMPORT_TO_DISTRIBUTION[name]
            for name in required
            if _normalize(IMPORT_TO_DISTRIBUTION[name]) not in present
        }
    )
    assert not missing, f"requirements.txt is missing distributions: {missing}"
    # optional imports must be a reviewed list, not silently grown
    unreviewed = sorted(
        name
        for name in optional
        if name not in required
        and name not in IMPORT_TO_DISTRIBUTION
        and name not in OPTIONAL_IMPORTS
    )
    assert not unreviewed, f"Unreviewed optional imports; list them in OPTIONAL_IMPORTS: {unreviewed}"
