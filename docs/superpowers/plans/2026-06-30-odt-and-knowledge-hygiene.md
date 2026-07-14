# ODT And Knowledge Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add regression guards for duplicate ODT source entries and clean the worst invalid structured knowledge rules.

**Architecture:** Add audit-style tests first, then make the smallest source and data changes needed to pass them. Preserve existing runtime APIs and avoid broad curation work outside ODT source hygiene and synergy-rule hygiene.

**Tech Stack:** Python, pytest, JSON, existing audit utilities

---

### Task 1: Guard ODT Source Keys

**Files:**
- Modify: `tests/test_oav_authority.py`
- Modify: `engine/odor_thresholds.py`

- [ ] **Step 1: Write the failing test**

```python
def test_odt_source_has_no_duplicate_textual_keys():
    from pathlib import Path
    import re
    from collections import Counter

    text = Path("engine/odor_thresholds.py").read_text(encoding="utf-8")
    keys = re.findall(r'^\s*"([^"]+)"\s*:\s*\{', text, flags=re.M)
    counts = Counter(keys)
    duplicates = {key: count for key, count in counts.items() if count > 1}
    assert duplicates == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_oav_authority.py -k duplicate_textual_keys -q`
Expected: FAIL with duplicate keys reported from `engine/odor_thresholds.py`

- [ ] **Step 3: Write minimal implementation**

Refactor `engine/odor_thresholds.py` so raw `ODT_DATA` source definitions are textually unique while preserving current lookup behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_oav_authority.py -k duplicate_textual_keys -q`
Expected: PASS

### Task 2: Guard Synergy Rule Junk

**Files:**
- Modify: `tests/test_literature_rules_contract.py`
- Modify: `engine/knowledge/literature_rules.py`
- Modify: `data/knowledge_graph/synergy_matrix.json`

- [ ] **Step 1: Write the failing test**

```python
def test_synergy_matrix_has_no_table_header_or_blank_effect_rows():
    import json
    from pathlib import Path

    rows = json.loads(Path("data/knowledge_graph/synergy_matrix.json").read_text(encoding="utf-8"))
    bad = []
    for row in rows:
        a = str(row.get("material_a", "")).strip()
        b = str(row.get("material_b", "")).strip()
        effect = str(row.get("effect", "")).strip()
        if a in {"Goal", "1:4"}:
            bad.append(row)
        if not effect:
            bad.append(row)
        if "(" in b and ")" in b and any(token in b.lower() for token in ("florals", "musks", "notes")):
            bad.append(row)
    assert bad == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_literature_rules_contract.py -k synergy_matrix_has_no_table_header_or_blank_effect_rows -q`
Expected: FAIL with bad rows from `synergy_matrix.json`

- [ ] **Step 3: Write minimal implementation**

Remove obvious extracted junk rows from `data/knowledge_graph/synergy_matrix.json` and broaden generic-reference detection in `engine/knowledge/literature_rules.py` for grouped phrases like `Florals (...)`, `Musks (...)`, and `Marine notes (...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_literature_rules_contract.py -k synergy_matrix_has_no_table_header_or_blank_effect_rows -q`
Expected: PASS

### Task 3: Re-verify Audit Output

**Files:**
- Modify: `docs/project_audit_2026-06-30.md`

- [ ] **Step 1: Run focused verification**

Run: `pytest tests/test_oav_authority.py tests/test_literature_rules_contract.py tests/test_pipeline_audit_verify.py -q`
Expected: PASS

- [ ] **Step 2: Run audit snapshot**

Run: `python scripts/pipeline_audit.py verify --sample-limit 8 --json`
Expected: JSON output with reduced invalid knowledge-rule counts and unchanged runtime contract shape

- [ ] **Step 3: Update audit report**

Document the before/after improvements and remaining risks in `docs/project_audit_2026-06-30.md`.
