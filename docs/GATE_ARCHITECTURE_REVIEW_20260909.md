# Gate architecture review — 2026-09-09

Scope: correct gate severity and remove unsupported verdicts from the existing
engine. No formulation quantities or inventory authority were changed.

## Implemented

- FAIL demotion is now allowed only for explicitly named aesthetic/advisory
  checks. Unclassified failures remain blocking. Unclassified gate exceptions
  also fail closed.
- Mode restrictions, chassis arithmetic, concentration basis, requested finished
  headspace scope, authority, solvent matrix, and phototoxic assessment failures
  survive final aggregation.
- Missing target/evidence ledgers produce NOT_EVALUATED, never invented zero
  authority dimensions. They warn for diagnostic reporting and fail for
  commercial, quantitative-claim, or RELEASE_REVIEW requests. Derivation errors
  propagate to the fail-closed wrapper.
- The phototoxic calculation was removed: substring matching did not establish
  grade identity, and concentrate volume percentages were compared with finished
  product limits. The gate now reports an unavailable assessment and blocks
  commercial/release requests. It does not establish that Grapefruit FCF contains
  furocoumarins or that the formula is phototoxic. A validated replacement still
  requires product-bound restrictions and finished-product mass exposure.
- Receptor percentage caps were removed. The gate returns SKIP with unsupported
  heuristic status; it cannot establish either receptor saturation or safety.

## Retained limits and next priorities

- Missing exact ppm or matrix inputs are legitimate diagnostic warnings when no
  exact claim is requested. Existing preflight escalates requested exact claims;
  the final policy now preserves that failure.
- Published partial natural profiles remain useful estimates with disclosed
  coverage. Mere use of a generic profile is not proof of formulation failure.
- Pyramid, style, ingredient-count and aesthetic rules remain advisory where
  explicitly registered. They cannot prove smell quality or repair missing data.
- The classical-vetiver brief mismatch and inherited baseline failures in the
  robustness test remain unresolved; no formula changes were made to satisfy
  those defaults.
- Finished-matrix modeling, density authority and the replacement phototoxicity
  evaluator remain separate implementation work. Earlier numerical perfume
  reports are historical and were not reissued as current results here.

## Verification

44 tests passed across test_gate_architectural_authority.py,
test_pipeline_gates.py and test_pipeline_preflight.py. Tests cover aggregation,
exceptions, an unclassified future contract, diagnostic versus release scope,
unknown authority, FCF assessment handling and retirement of receptor caps.
This verifies the changed contracts; it is not a new full perfume score or
physical/sensory test. git diff --check passed (line-ending notices only).
