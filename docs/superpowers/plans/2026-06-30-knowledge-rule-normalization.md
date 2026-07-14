# Knowledge Rule Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce false-invalid and orphaned structured knowledge-rule references without introducing speculative chemistry aliases.

**Architecture:** Keep the fix narrow: profile the remaining invalid references, add regression tests for the highest-confidence cases, normalize only exact aliases that clearly map to existing known materials, and keep grouped/category labels advisory. Prefer resolver-path improvements over ad hoc rule-specific hacks.

**Tech Stack:** Python, `pytest`, JSON knowledge-graph assets, existing material resolver and literature-rule validator.

---

### Task 1: Profile remaining invalid references

**Files:**
- Modify: `docs/project_audit_2026-06-30.md`
- Test: `tests/test_literature_rules_contract.py`

- [ ] **Step 1: Gather the highest-frequency invalid references**

```powershell
$env:PYTHONIOENCODING='utf-8'; @'
from collections import Counter
from engine.knowledge.literature_rules import STRUCTURED_RULE_FILES, _safe_load_json, _normalized_rule_metadata, _is_generic_reference
from engine.material_resolver import resolve_material

counter = Counter()
for label in ("pairing_rules", "synergy_matrix"):
    rows = _safe_load_json(STRUCTURED_RULE_FILES[label]) or []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            continue
        row = _normalized_rule_metadata(raw_row, source_hint=str(raw_row.get("source", label)), runtime_consumers=["audit"])
        for field in ("material_a", "material_b"):
            value = str(row.get(field, "")).strip()
            if not value or _is_generic_reference(value):
                continue
            resolved = resolve_material(value)
            if resolved is not None and not resolved.is_known:
                counter[value] += 1
for value, count in counter.most_common(25):
    print(f"{count:3} | {value}")
'@ | python -
```

- [ ] **Step 2: Pick only defensible normalization targets**

Allowed examples:

```text
Ambrox -> Ambroxan
DHM -> Dihydromyrcenol
```

Disallowed examples:

```text
patchouli -> Patchouli EO     # too generic
vanilla -> Vanillin           # not chemically equivalent
SANDALWOOD FRAGRANCE OIL -> ? # unsupported marketing label
```

- [ ] **Step 3: Record the chosen targets in the audit report notes**

Add a short note to `docs/project_audit_2026-06-30.md` describing that this pass only normalizes exact aliases and leaves ambiguous names invalid.

### Task 2: Add failing regression coverage

**Files:**
- Modify: `tests/test_literature_rules_contract.py`

- [ ] **Step 1: Write the failing test**

```python
def test_defensible_rule_aliases_resolve_as_known_materials():
    for raw_name in ("Ambrox", "DHM"):
        resolved = resolve_material(raw_name)
        assert resolved is not None
        assert resolved.is_known is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_literature_rules_contract.py -k defensible_rule_aliases_resolve_as_known_materials -q`

Expected: FAIL because one or both aliases do not currently resolve as known materials.

- [ ] **Step 3: Keep grouped-label tests green**

Run: `pytest tests/test_literature_rules_contract.py -k grouped_rule_labels_are_treated_as_generic_references -q`

Expected: PASS.

### Task 3: Implement minimal normalization

**Files:**
- Modify: `engine/name_utils.py`
- Modify: `engine/knowledge/literature_rules.py`
- Test: `tests/test_literature_rules_contract.py`

- [ ] **Step 1: Add only the chosen exact aliases to the existing alias path**

```python
_ALIASES.update(
    {
        "ambrox": "Ambroxan",
        "dhm": "Dihydromyrcenol",
    }
)
```

- [ ] **Step 2: Keep generic/advisory classification strict**

Do not turn broad note/family labels into exact materials. If a phrase remains grouped, descriptive, or marketing-style, it stays advisory or invalid.

- [ ] **Step 3: Run the failing test again**

Run: `pytest tests/test_literature_rules_contract.py -k defensible_rule_aliases_resolve_as_known_materials -q`

Expected: PASS.

### Task 4: Verify audit improvement

**Files:**
- Modify: `docs/project_audit_2026-06-30.md`

- [ ] **Step 1: Run focused verification**

Run: `pytest tests/test_literature_rules_contract.py tests/test_pipeline_audit_verify.py tests/test_oav_authority.py -q`

Expected: PASS.

- [ ] **Step 2: Rerun the audit**

Run: `python scripts/pipeline_audit.py verify --sample-limit 8 --json`

Expected: `knowledge_rule_quality.invalid_entries` and `orphan_material_refs` decrease or stay flat only if the chosen aliases were absent from current invalid counts.

- [ ] **Step 3: Update the audit report**

Add the post-pass counts and a short note that ambiguous names were intentionally left unresolved for scientific honesty.
