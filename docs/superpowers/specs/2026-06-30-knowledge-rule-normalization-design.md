# Knowledge Rule Normalization Design

**Goal:** Reduce the remaining false-invalid and orphaned structured knowledge-rule references without inventing chemistry or overstating source authority.

**Scope:** This design covers the next cleanup pass for `engine/knowledge/literature_rules.py` and the structured rule JSON assets it validates. It does not attempt a full literature rewrite, broad alias expansion across the whole engine, or dead-code deletion.

## Problem

The current audit is cleaner than before, but `knowledge_rule_quality` still reports a large advisory/invalid tail:

- many entries are generic labels rather than exact materials
- some entries are obvious legacy naming variants that should resolve to existing inventory-backed materials
- some warnings are academically acceptable as advisory language, but are currently mixed with exact-runtime validation outcomes

For a professor-facing audit, we want the system to distinguish these cases honestly:

1. **Exact material reference** -> should resolve cleanly
2. **Generic/advisory grouping** -> should be marked advisory, not invalid
3. **Truly unknown material** -> should remain invalid until curated

## Recommended Approach

Use a narrow, evidence-based normalization pass:

- profile the highest-frequency remaining invalid references
- add a failing regression test for the most defensible names to normalize
- improve generic-reference handling only where the phrase is clearly non-exact
- add or route only obvious exact aliases that map to existing known materials
- leave ambiguous or speculative names invalid

This keeps the audit more honest than bulk-coercing everything into canonical materials.

## Design

### Reference classes

We will treat remaining rule references in three buckets:

- **Generic/advisory labels**
  - examples: grouped families, note umbrellas, broad style phrases
  - outcome: advisory
- **Defensible exact aliases**
  - examples: common spelling or casing variants that clearly map to an existing material
  - outcome: valid after normalization
- **Ambiguous/unsupported names**
  - examples: vague fragrance-oil labels, shorthand with no clear authoritative mapping
  - outcome: invalid until manually curated

### Code changes

- Add a targeted test covering the highest-impact references we intend to normalize.
- Update the rule-validation path in `engine/knowledge/literature_rules.py` only as needed to:
  - recognize additional generic grouped labels
  - normalize a short list of defensible exact aliases
- If needed, add alias support in the existing name-resolution path rather than inventing a separate rule-only resolver.

### Data changes

- Only edit structured rule JSON when the row itself is clearly malformed or uses a trivially correctable exact-material spelling.
- Do not rewrite advisory literature statements into faux-exact chemistry rows.

## Validation

- targeted failing test first, then passing
- `pytest tests/test_literature_rules_contract.py -q`
- `pytest tests/test_pipeline_audit_verify.py tests/test_oav_authority.py -q`
- `python scripts/pipeline_audit.py verify --sample-limit 8 --json`

## Success Criteria

- `knowledge_rule_quality.invalid_entries` decreases again
- `knowledge_rule_quality.orphan_material_refs` decreases again
- no speculative aliasing is introduced
- targeted and existing audit tests pass
- `docs/project_audit_2026-06-30.md` reflects the updated numbers and remaining risks clearly
