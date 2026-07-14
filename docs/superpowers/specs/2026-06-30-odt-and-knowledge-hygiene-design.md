# ODT And Knowledge Hygiene Design

**Goal:** Reduce the highest-confidence integrity risks in the perfume chemistry repo by guarding against duplicate ODT definitions and cleaning the worst invalid structured knowledge rules.

**Scope:** This design covers two focused repairs only: `engine/odor_thresholds.py` source hygiene and `data/knowledge_graph/synergy_matrix.json` / validation hygiene. It does not attempt a full literature curation pass or broad dead-code deletion.

## Problem

The current audit shows two project-level integrity problems:

1. `engine/odor_thresholds.py` contains many textual duplicate keys, which are silently overwritten by Python dict semantics.
2. Structured knowledge rules contain invalid and generic entries, especially in `synergy_matrix.json`, including obvious extraction junk and umbrella phrases that are not exact material identities.

## Approach

Use a narrow, test-first repair sequence:

- add a source-level duplicate-key audit test for ODT definitions
- refactor ODT source structure just enough to remove duplicate textual definitions while preserving runtime lookup semantics
- add a knowledge-quality regression test around obvious invalid synergy entries
- clean or quarantine the worst invalid synergy rows and improve generic-reference detection so advisory entries are not misclassified as exact-runtime invalids

## Design

### ODT hygiene

- Add a test that scans `engine/odor_thresholds.py` source text and fails on duplicate raw dictionary keys in `ODT_DATA`.
- Refactor only the duplicate-prone portions needed to make the source text unique.
- Keep runtime APIs stable:
  - `lookup_odt_entry`
  - `lookup_odt_raw_name`
  - `odt_collision_names`

### Knowledge hygiene

- Add a test that asserts no obvious table-header or malformed rows remain in `synergy_matrix.json`.
- Expand generic-reference recognition for grouped phrases such as `Florals (...)`, `Musks (...)`, and `Marine notes (...)` so they are treated as advisory/generic instead of unknown exact materials.
- Remove or normalize obvious junk rows in `synergy_matrix.json` that came from markdown table extraction.

## Validation

- targeted pytest for new audit tests
- existing audit tests:
  - `tests/test_literature_rules_contract.py`
  - `tests/test_pipeline_audit_verify.py`
- rerun `python scripts/pipeline_audit.py verify --sample-limit 8 --json`

## Success Criteria

- zero duplicate textual keys detected by the new ODT audit test
- no obvious junk rows remain in `synergy_matrix.json`
- `knowledge_rule_quality.invalid_entries` decreases measurably
- all targeted tests pass
