# V4 prerequisite acceptance: descriptor eligibility, not new architecture activation

Date: 2026-10-07. Outcome: **focused prerequisite checks passed**.
The active adapter remains v3. The full research program is not complete.

## What changed

`material_capability_index.py` now excludes explicit unreviewed stock-intake
placeholder descriptions from own-material descriptor vocabulary. It preserves
independently annotated profile fields and separately reviewed exact-material
vocabulary. The change neither removes an owned stock nor changes its form,
carrier, concentration, quantity, status or compounding hold.

The closed requirement registry now supports rose, jasmine, bitter/resin/green,
watery/leaf and leaf/citrus/floral conjunctions, in addition to the existing fruit
predicate. These are **heuristic eligibility conditions**, not calibrated scent
recognizers. The existing solver rank and assignment checks enforce them; no
new role mapping activates them yet. Generic freshness, floral strength, stock
names, categories, labels, comments and synergy fields cannot supply a missing
required descriptor. Unknown requirements fail closed.

Explicit anchors, trace limits, stock holds, quantitative accounting, numerical
allocation templates, all three immutable adapter predecessors and the v3 corpus
were preserved. No formula or inventory file was edited by this change.

## Verification

- Red before implementation: **20 failed, 51 passed** in the new 71-case suite.
  Failures included the actual placeholder-evidence defect and the deliberately
  unimplemented new predicates. This is not a claim of 20 pre-existing defects.
- Final current-source focused run: **151 passed in 190.68 seconds**.
  It includes the new descriptor tests, existing fruit tests, v3 planning,
  receipt-binding adversaries, and five Formula Studio checks for exclusions,
  crystal mass, exact microlitre quantities, the Orris Liquid hold and unordered
  Deep Compose variants.
- Scoped Ruff: passed for the changed module and new test file.
- Scoped mypy: passed for one changed source file with explicit namespace bases
  and imported-module checking skipped. An earlier broad import-following run
  found a nullable-group narrowing issue; that was repaired. This is not a
  whole-project type-check result.
- `git diff --check`: passed. No formatter rewrote unrelated files.
- No network calls, physical work, empirical model admission, full verifier,
  push, merge or release-readiness claim occurred in this prerequisite pass.

Final focused command:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_architecture_descriptor_eligibility.py tests/test_fruit_recognizer_matching.py tests/test_architecture_v3.py tests/test_architecture_receipt_binding.py tests/test_formula_design_chat.py::test_formula_design_honors_natural_language_exclusions_before_selection tests/test_formula_design_chat.py::test_formula_design_honors_exact_crystal_mass_and_separate_liquid_total tests/test_formula_design_chat.py::test_formula_design_withholds_if_exact_requested_iris_stock_is_held tests/test_formula_design_chat.py::test_formula_design_keeps_nfkc_micro_quantity_exact tests/test_formula_design_chat.py::test_formula_design_deep_compose_returns_diverse_unordered_variants -q -p no:cacheprovider --tb=short
```

## Current annotation census and its limits

The runtime index still contains 357 stock candidates; that is not the raw
inventory-row or unique-material count. Its effective inventory hash is
`e8094e07505fbfbb7121d94693069e624531c4726d853e27b7a24f6c5d0fb280`.

The descriptor-only census found 15 unique rose-associated identities, three
jasmine-associated identities, one watery-leaf identity, and no bitter/resin/green
or leaf/citrus/floral identity satisfying all required tokens. These are not
15/3/1 executable alternatives: family, trace, quantity, availability, holds and
all other solver constraints still apply.

The watery-leaf match is Violet Leaf Absolute. Calone and Helional do not acquire
leaf eligibility from generic green/aquatic annotations. The unreviewed Rose
Otto Bulgarian intake placeholder no longer supplies a rose descriptor.

**A remaining content-quality issue was found before activation:** the Fructone B
profile combines odor description and application-like prose, ending with terms
such as jasmine/tuberose. Its token match does not establish an own jasmine odor
or justify a jasmine-bridge substitution. BerryFlor and Hedione also appear in
the descriptor-only jasmine census for different reasons. Review the exact
supplier descriptions and separate own odor from suggested uses before admitting
any new jasmine comparison. Do not rewrite the profile or promote a mapping merely
to satisfy this test. Placeholder rejection is not a complete semantic parser.

## What remains before v4 activation

1. Adjudicate the exact own-material descriptor evidence needed by the new
   options; retain unsupported options as unavailable rather than relaxing their
   conjunctions or treating another supplier's botanical grade as an owned lot.
2. Add an immutable v4 successor preserving all 44 v3 mappings and exact v1-v3
   predecessor hashes. Bind each new option to a closed descriptor requirement,
   source card, review receipt and existing numerical template.
3. Bind v4 in durable fingerprints; preserve v3 request-specificity ordering and
   historical replay. Missing or drifted predecessors must still withhold.
4. Freeze the expanded diagnostic corpus and configuration before execution.
   Assert planned options separately from returned formulas, and report option
   availability rather than calling a withheld branch an executed comparison.
5. Run the paired control/comparison and reverse-order diagnostic on current
   source and inventory. Only then consider switching the active adapter.

The earlier 56/56, 224-call v3 acceptance remains evidence for its recorded
source snapshot. It was not rerun wholesale after this prerequisite change and
must not be relabeled as a fresh full-corpus result for these new bytes.

No empirical capability or numeric calibration was added. The library remains
49 construction dossiers, 179 partial subtype cards, 44 mappings and 88 options.
CHIMIE L'HOMME still lacks its exact accepted brief/formula; adjacent fragrances
do not resolve that campaign identity.

## Frozen bytes for this prerequisite

| Object | SHA-256 |
|---|---|
| Changed material index | `c5a5496205addf22a1f1a9cbc7a6dced370e5edaaf5e9456877679f587c52edb` |
| New descriptor tests | `af88da7f868c957474462da872ecbcec63dc66156fd081c80067efc2d5f4cdbf` |
| Unchanged inventory | `116c39815c81d148f0a259332b8acf734b9f3eced484b5e390dc4bc7df38cc58` |
| Unchanged active v3 adapter | `70ec8bd60abefa7d5e09556fece34067caecacba539e6db1fcdea5d7d2f0111c` |
| Unchanged v3 corpus | `999810479674a7f7f041def9e992c4bdfc88a9eda20f7e6b4700612f75dfe34c` |

These receipts establish software behavior and provenance only. Sensory quality,
diffusion, longevity, liking, safety and physical execution remain untested here.
