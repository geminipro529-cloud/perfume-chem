# Perfume-Chem Project Audit

Date: `2026-06-30`

## Scope

This audit reviewed the perfume-chemistry core of the repository with focus on:

- material data integrity and schema consistency
- duplicate or conflicting chemistry rows
- heuristic or manually generated data presented as runtime inputs
- knowledge-graph quality for pairings and synergy rules
- dead, disconnected, or duplicate code paths
- release-readiness evidence suitable for academic review

## Executive Summary

The project is ambitious and scientifically structured, but it is not yet in a "professor-ready, fully authoritative" state without qualification.

Strengths:

- the release pipeline is real, tested, and reproducible
- literature inventory coverage is broad and indexed
- preflight, gate, OAV, IFRA, and audit layers are already wired together
- focused regression tests pass after the repairs made in this audit

Primary risks:

- large portions of chemistry and psychophysics still rely on heuristics, fallbacks, or manually approximated values
- structured knowledge rules are mostly advisory rather than exact-runtime quality
- chemistry authorities still need stronger normalization and provenance discipline
- several modules are marked as disconnected, deprecated, or candidates for consolidation

## What Was Fixed During This Audit

1. Restored 15 malformed material rows in `data/materials/*.yaml`.

These rows used `name` instead of `canonical_name`, causing the live data spine loader to skip them entirely. The affected materials included:

- `Blue Chamomile EO`
- `Cocoa CO2 Absolute`
- `Ginger EO`
- `Isobutavan`
- `Jasmine Sambac Blossoms`
- `Mimosa Absolute`
- `Neroli EO` (2 rows)
- `Osmanthus Absolute (volume grade)`
- `Opoponax Resinoid`
- `Peru Balsam Resinoid`
- `Tagetes EO`
- `Tuberose Absolute (volume grade)`
- `Tonka Bean Absolute`

2. Hardened the data spine loader.

- `engine/data_spine/material.py` now accepts legacy `name` rows by mapping them to `canonical_name`
- `engine/data_spine/loader.py` now logs malformed rows safely with ASCII output instead of using a console-breaking Unicode arrow

3. Added loader regression coverage.

- `tests/test_data_spine_loader.py` ensures the loader accepts both modern `canonical_name` records and legacy `name` records

4. Removed duplicate textual keys from the ODT source authorities.

- `engine/odor_thresholds.py` now has `0` duplicate textual keys in the `ODT_DATA` literal
- `engine/odor_thresholds.py` now has `0` duplicate textual keys in the `ODT_VERIFICATION` literal
- `tests/test_oav_authority.py` now locks this in with a source-level duplicate-key regression test

5. Removed extracted-table junk from the synergy knowledge graph and tightened generic-reference detection.

- deleted the fake rows `Goal -> Amplifier` and `1:4 -> 2-3x sillage` from `data/knowledge_graph/synergy_matrix.json`
- `engine/knowledge/literature_rules.py` now treats grouped labels such as `Musks (Galaxolide, Habanolide)` and `Florals (Rose, Jasmine)` as advisory generic references instead of false-invalid exact materials
- `tests/test_literature_rules_contract.py` now locks this behavior with regression coverage

6. Repaired defensible exact-alias resolution for structured knowledge rules.

- `engine/ingredient_intelligence.py` now resolves the exact rule aliases `Ambrox`, `DHM`, and `DEP`
- alias canonical targets are now matched case-insensitively against `_PROFILES`, fixing a real resolver bug rather than hiding warnings
- ambiguous shortcuts such as `patchouli`, `olibanum`, `pink pepper`, and `lavender` remain unresolved on purpose

7. Switched audit sampling to shipped-formula defaults.

- `scripts/pipeline_audit.py` now excludes underscore-prefixed scratch formulas from `verify` and `scan-formulas` by default
- scratch formulas remain available via explicit `--include-scratch`
- `tests/test_pipeline_audit_verify.py` now locks in the default exclusion behavior

8. Added explicit evidence-posture labeling to the audit JSON.

- `scripts/pipeline_audit.py verify --json` now emits `evidence_posture`
- authoritative internal checks, mixed-authority chemistry coverage, and heuristic/partial science are now labeled separately
- this makes the professor-facing audit materially clearer without pretending heuristic layers are authoritative

## Verified State After Repair

Commands run:

- `pytest tests/test_data_spine_loader.py tests/test_science_audit.py tests/test_pipeline_audit_verify.py tests/test_literature_rules_contract.py tests/test_oav_authority.py -q`
- `python scripts/pipeline_audit.py verify --sample-limit 8 --json`

Result:

- `14` focused verification tests passed after submission-hardening updates
- malformed material rows remaining: `0`
- duplicate textual keys remaining in `ODT_DATA`: `0`
- duplicate textual keys remaining in `ODT_VERIFICATION`: `0`
- corrupted synergy entries remaining: `0`

## Findings

### 1. Material data completeness remains low

From `scripts/pipeline_audit.py verify` after the repair:

- `mw`: `21.84%`
- `logp`: `15.66%`
- `vp_25c`: `21.60%`
- `odt_air`: `6.01%`
- `hedonic`: `10.68%`
- `ifra`: `1.11%`
- `cas`: `3.96%`
- `antoine`: `0.0%`
- `hsp`: `0.0%`
- `or_targets`: `0.0%`

Interpretation:

- runtime can still operate
- scientific confidence is not yet commensurate with the breadth of claims implied by the architecture
- hedonic and receptor-driven layers are especially under-supported by primary data

### 2. ODT authority is still mostly heuristic

ODT verification coverage:

- authoritative (`PEER_CROSS`, `PEER_SINGLE`, `PEER_EST`): `31.8%`
- heuristic (`DERIVED`, `UNVERIFIED`, `UNKNOWN`): `68.2%`

Interpretation:

- OAV math may be mechanically correct
- but many underlying thresholds are not authoritative enough for high-confidence scientific claims

### 3. ODT source duplication was real, and is now repaired

Interpretation:

- before this cleanup, duplicate textual keys in `engine/odor_thresholds.py` created silent overwrite risk
- after this cleanup, both source literals are deduplicated and protected by a regression test
- the remaining risk is no longer duplicate literals, but long-term provenance discipline and authority quality

### 4. Knowledge rules are mostly advisory, not runtime-grade

`knowledge_rule_quality` status is `WARN`:

- total structured entries: `2452`
- valid: `11`
- advisory: `2311`
- invalid: `130`
- orphan material refs: `149`
- generic material refs: `302`

Examples of invalid/advisory knowledge entries:

- `Iso E Super` -> `Musks (Galaxolide, Habanolide)`
- `Dihydromyrcenol` -> `Florals (Rose, Jasmine)`
- generic placeholders such as `orange`, `rose`, `jasmine`, `musks`, `__avoid__`

Interpretation:

- the literature corpus exists
- but most pairing and synergy rules are still not normalized to exact material identities
- some previously invalid rows were correctly downgraded to advisory generic references rather than exact-material failures
- a second pass also converted a small set of defensible exact aliases into known materials without coercing ambiguous note/family shortcuts
- this weakens downstream confidence, explainability, and determinism

### 5. Some chemistry inputs are explicitly estimated or placeholder-based

Observed patterns include:

- `manual:*` provenance across many `data/materials/*.yaml` rows
- `estimated from analog` and constituent-weighted approximations for naturals and EOs
- `engine/allergen_solver.py` contains an explicit placeholder mapping:
  - `"vetiver": 100.0`
- `engine/science_audit.py` itself states:
  - Antoine constants absent
  - UNIFAC integration stubbed
  - OR targets not ingested
  - Ferreira mixture-shift beta hard-coded

Interpretation:

- the project is honest about its limitations
- but it currently mixes authoritative and estimated science within the same operational pipeline
- this needs clearer separation if presented as a scientific system

### 6. Disconnected and potentially redundant code still exists

The audit utility already marks these modules for review:

- `engine.formulator` -> deprecated from pipeline narrative
- `engine.opus_v_workbook` -> deprecated from pipeline narrative
- `engine.reconstruction_pipeline` -> deprecated from pipeline narrative
- `engine.family_scorer` -> audit for duplication
- `engine.formula_analyzer` -> audit for duplication
- `engine.thermo.headspace` -> consolidate or deprecate
- `engine.thermo.trajectory` -> consolidate or deprecate

Quick reference scan suggests:

- `engine/formula_analyzer.py` appears effectively unused outside audit labeling
- `engine/formulator.py` has no substantive runtime import usage in the current release path
- `engine/thermo/headspace.py` and pipeline headspace logic likely overlap conceptually and should be reconciled

Interpretation:

- there is meaningful cleanup potential
- but deletion should follow a dependency review, not blind removal

### 7. Audit sampling is now closer to a release-review workflow

`scripts/pipeline_audit.py verify --sample-limit 8 --json` now excludes underscore-prefixed scratch formulas by default.

Interpretation:

- representative runs are now closer to a shipped-formula review set
- scratch and temporary formulas no longer dilute the professor-facing audit snapshot
- exploratory formulas are still available when explicitly requested with `--include-scratch`

## Cut / Cleanup Candidates

High-confidence cleanup candidates:

- `engine/formula_analyzer.py`
- `engine/formulator.py`

Needs consolidation review before removal:

- `engine/thermo/headspace.py`
- `engine/thermo/trajectory.py`
- legacy or narrative-only orchestration around `engine/reconstruction_pipeline.py`

Should be retained but promoted or integrated more clearly:

- `engine/optimizer/gate_aware.py`
- `engine/odt_verifier.py`

## Recommended Next Steps

### Priority 1: Scientific credibility

- split runtime-authoritative data from heuristic/estimated data in reports
- add a strict mode that refuses heuristic ODTs for professor/demo outputs
- keep `engine/odor_thresholds.py` under duplicate-key regression coverage

### Priority 2: Knowledge-graph quality

- normalize generic rule references to exact material identities where possible
- move placeholders like `orange`, `rose`, `musks`, `Florals (Rose, Jasmine)` into explicit advisory-only sections
- fail CI when invalid structured rule references increase

### Priority 3: Codebase clarity

- remove or archive clearly disconnected modules after import-trace confirmation
- keep underscore scratch formulas excluded from default audit sampling
- keep the new source-level hygiene tests in the default verification path

## Bottom-Line Assessment

Current state:

- good engineering prototype
- meaningful scientific framing
- not yet clean enough to present as a fully authoritative perfume-science platform without caveats

After this audit, the project is stronger and less fragile, but the remaining blockers are not cosmetic:

- weak source authority for many ODTs
- low chemistry metadata coverage
- advisory-heavy knowledge rules
- broad reliance on heuristic science layers

If this is being sent to a professor, the safest framing is:

"This is a working research-grade perfumery engineering system with explicit auditability, but several subsystems still rely on heuristic or manually approximated data and should be presented as such."
