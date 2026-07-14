"""Schema validation and data quality auditing for the knowledge graph.

Scans the flat JSON files, identifies corrupted entries, missing fields,
naming inconsistencies, and produces a structured report.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KG_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_graph"

# Fields that every well-formed material should have
REQUIRED_MATERIAL_FIELDS = {"name"}
IMPORTANT_MATERIAL_FIELDS = {
    "mw", "bp", "vp", "clp", "odt",
    "sar_class", "carles_position", "typical_pct_range",
}
NUMERIC_FIELDS = {"mw", "bp", "vp", "clp", "odt"}

# CAS number regex: digits-digits-digit
CAS_RE = re.compile(r"\d{2,7}-\d{2}-\d")

# Known non-CAS values that are valid for perfumery materials
CAS_VALID_NON_NUMERIC = {
    "n/a", "na", "proprietary", "proprietary mixture",
    "supplier-specific", "supplier specific",
    "not publicly listed",
}


def _is_valid_cas(value: str) -> bool:
    """Check if a CAS field value is valid — either matches CAS format or is a known non-numeric value."""
    if not value:
        return False
    stripped = value.strip()
    if not stripped:
        return False
    if CAS_RE.search(stripped):
        return True
    low = stripped.lower().rstrip(".)]}").lstrip()
    for valid in CAS_VALID_NON_NUMERIC:
        if valid in low:
            return True
    return False

# Patterns that indicate corruption (filename leaked into data)
CORRUPTION_PATTERNS = [
    re.compile(r"\.\w{2,4}[a-z]", re.IGNORECASE),  # e.g. ".mdzoate"
    re.compile(r"_and_"),          # description-style strings in name fields
    re.compile(r"\.md"),           # markdown filename fragments
    re.compile(r"\.txt"),          # text filename fragments
]


@dataclass
class ValidationIssue:
    severity: str  # "error", "warning", "info"
    file: str
    index: int | None
    field: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def summary(self) -> dict[str, Any]:
        return {
            "total_issues": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "info": len(self.issues) - len(self.errors) - len(self.warnings),
            "stats": self.stats,
        }

    def to_markdown(self) -> str:
        lines = ["# Schema Validation Report\n"]
        s = self.summary()
        lines.append(f"**Errors:** {s['errors']}  |  **Warnings:** {s['warnings']}  |  **Info:** {s['info']}\n")

        if self.stats:
            lines.append("## Statistics\n")
            for k, v in self.stats.items():
                lines.append(f"- {k}: {v}")
            lines.append("")

        for sev in ("error", "warning", "info"):
            items = [i for i in self.issues if i.severity == sev]
            if items:
                lines.append(f"## {sev.upper()}S ({len(items)})\n")
                for i in items:
                    idx_str = f"[{i.index}]" if i.index is not None else ""
                    lines.append(f"- **{i.file}**{idx_str} `{i.field}`: {i.message}")
                lines.append("")

        return "\n".join(lines)


class SchemaValidator:
    """Validates knowledge graph JSON files and produces a quality report."""

    def __init__(self, kg_dir: Path | None = None):
        self.kg_dir = kg_dir or KG_DIR
        self.report = ValidationReport()

    def validate_all(self) -> ValidationReport:
        """Run all validations and return the combined report."""
        self._validate_materials()
        self._validate_pairing_rules()
        self._validate_synergy_matrix()
        self._validate_theory_rules()
        self._cross_validate()
        return self.report

    # ── Material properties ─────────────────────────────────────────────

    def _validate_materials(self):
        path = self.kg_dir / "material_properties.json"
        if not path.exists():
            self._issue("error", "material_properties.json", None, "file", "File not found")
            return

        data = self._load(path)
        if not isinstance(data, list):
            self._issue("error", "material_properties.json", None, "root", "Expected a JSON array")
            return

        self.report.stats["total_materials"] = len(data)
        names_seen: set[str] = set()
        complete_count = 0

        for i, mat in enumerate(data):
            fname = "material_properties.json"

            # Required field check
            if "name" not in mat or not mat["name"]:
                self._issue("error", fname, i, "name", "Missing required field 'name'")
                continue

            name = mat["name"]

            # Duplicate check
            norm = name.strip().upper()
            if norm in names_seen:
                self._issue("warning", fname, i, "name", f"Duplicate material name: '{name}'")
            names_seen.add(norm)

            # Corruption check — filename fragments in name
            for pat in CORRUPTION_PATTERNS:
                if pat.search(name):
                    self._issue("error", fname, i, "name",
                                f"Corrupted name (contains filename fragment): '{name}'")

            # CAS validation
            cas = mat.get("cas")
            if cas and not _is_valid_cas(cas):
                self._issue("warning", fname, i, "cas", f"Invalid CAS format: '{cas}'")

            # Numeric field validation
            for nf in NUMERIC_FIELDS:
                val = mat.get(nf)
                if val is not None and not isinstance(val, (int, float)):
                    self._issue("error", fname, i, nf, f"Expected numeric, got {type(val).__name__}: {val!r}")

            # Completeness check
            important_filled = sum(1 for f in IMPORTANT_MATERIAL_FIELDS if mat.get(f) is not None)
            completeness = important_filled / len(IMPORTANT_MATERIAL_FIELDS) * 100
            if completeness == 100:
                complete_count += 1
            elif completeness < 50:
                missing = [f for f in IMPORTANT_MATERIAL_FIELDS if mat.get(f) is None]
                self._issue("warning", fname, i, "completeness",
                            f"'{name}' is only {completeness:.0f}% complete. Missing: {missing}")

            # Casing inconsistency
            if name != name.upper() and name != name.title():
                self._issue("info", fname, i, "name",
                            f"Inconsistent casing: '{name}' (expected UPPER or Title)")

        self.report.stats["complete_materials"] = complete_count
        self.report.stats["completeness_pct"] = round(
            complete_count / max(len(data), 1) * 100, 1
        )

    # ── Pairing rules ──────────────────────────────────────────────────

    def _validate_pairing_rules(self):
        path = self.kg_dir / "pairing_rules.json"
        if not path.exists():
            self._issue("error", "pairing_rules.json", None, "file", "File not found")
            return

        data = self._load(path)
        if not isinstance(data, list):
            self._issue("error", "pairing_rules.json", None, "root", "Expected a JSON array")
            return

        self.report.stats["total_pairing_rules"] = len(data)

        for i, rule in enumerate(data):
            fname = "pairing_rules.json"
            a = rule.get("material_a", "")
            b = rule.get("material_b", "")

            if not a or not b:
                self._issue("error", fname, i, "material_a/b", "Missing material name(s)")

            # Check if the material_a field looks like a description, not a name
            if len(a) > 100 or "\n" in a:
                self._issue("error", fname, i, "material_a",
                            f"Field looks like a description, not a material name: '{a[:80]}...'")
            if len(b) > 100 or "\n" in b:
                self._issue("error", fname, i, "material_b",
                            f"Field looks like a description, not a material name: '{b[:80]}...'")

            # Corruption check
            for pat in CORRUPTION_PATTERNS:
                if pat.search(a):
                    self._issue("error", fname, i, "material_a",
                                f"Corrupted (filename fragment): '{a}'")
                if pat.search(b):
                    self._issue("error", fname, i, "material_b",
                                f"Corrupted (filename fragment): '{b}'")

    # ── Synergy matrix ─────────────────────────────────────────────────

    def _validate_synergy_matrix(self):
        path = self.kg_dir / "synergy_matrix.json"
        if not path.exists():
            self._issue("error", "synergy_matrix.json", None, "file", "File not found")
            return

        data = self._load(path)
        if not isinstance(data, list):
            self._issue("error", "synergy_matrix.json", None, "root", "Expected a JSON array")
            return

        self.report.stats["total_synergy_rules"] = len(data)
        corrupted = 0

        for i, rule in enumerate(data):
            fname = "synergy_matrix.json"
            a = rule.get("material_a", "")
            b = rule.get("material_b", "")

            if not a or not b:
                self._issue("error", fname, i, "material_a/b", "Missing material name(s)")
                corrupted += 1
                continue

            # Corruption: filename concatenated into name
            for pat in CORRUPTION_PATTERNS:
                if pat.search(a):
                    self._issue("error", fname, i, "material_a",
                                f"Corrupted entry: '{a}'")
                    corrupted += 1
                    break

            # Corruption: description in name field
            if len(a) > 80:
                self._issue("error", fname, i, "material_a",
                            f"Looks like description/ratio, not a name: '{a[:60]}...'")
                corrupted += 1

        self.report.stats["corrupted_synergy_entries"] = corrupted

    # ── Theory rules ───────────────────────────────────────────────────

    def _validate_theory_rules(self):
        path = self.kg_dir / "theory_rules.json"
        if not path.exists():
            self._issue("error", "theory_rules.json", None, "file", "File not found")
            return

        data = self._load(path)
        if not isinstance(data, dict):
            self._issue("error", "theory_rules.json", None, "root", "Expected a JSON object")
            return

        self.report.stats["theory_frameworks"] = list(data.keys())

    # ── Cross-validation ───────────────────────────────────────────────

    def _cross_validate(self):
        """Check references between files."""
        mat_path = self.kg_dir / "material_properties.json"
        pair_path = self.kg_dir / "pairing_rules.json"
        syn_path = self.kg_dir / "synergy_matrix.json"

        if not all(p.exists() for p in (mat_path, pair_path, syn_path)):
            return

        materials = self._load(mat_path)
        mat_names = set()
        for m in materials:
            n = m.get("name", "").strip().upper()
            if n:
                mat_names.add(n)
            alt = m.get("alt_name", "")
            if alt:
                mat_names.add(alt.strip().upper())

        # Check pairing rules reference known materials
        pairings = self._load(pair_path)
        orphan_materials: set[str] = set()
        for rule in pairings:
            for key in ("material_a", "material_b"):
                name = rule.get(key, "").strip().upper()
                if name and name not in mat_names:
                    orphan_materials.add(rule.get(key, ""))

        if orphan_materials:
            self.report.stats["orphan_materials_in_rules"] = len(orphan_materials)
            # Only report first 20 to avoid noise
            for name in sorted(orphan_materials)[:20]:
                self._issue("info", "cross-validation", None, "orphan",
                            f"Material '{name}' in pairing_rules but not in material_properties")

    # ── Helpers ─────────────────────────────────────────────────────────

    def _load(self, path: Path) -> Any:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _issue(self, severity: str, file: str, index: int | None,
               field: str, message: str):
        self.report.issues.append(
            ValidationIssue(severity=severity, file=file, index=index,
                            field=field, message=message)
        )


def run_validation(kg_dir: Path | None = None) -> ValidationReport:
    """Run schema validation and return report."""
    validator = SchemaValidator(kg_dir)
    return validator.validate_all()


if __name__ == "__main__":
    report = run_validation()
    print(report.to_markdown())
