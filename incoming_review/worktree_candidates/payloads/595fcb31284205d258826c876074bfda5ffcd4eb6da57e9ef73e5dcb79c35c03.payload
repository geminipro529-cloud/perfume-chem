# Targeted hedonic evaluator implementation plan

Standing user approval: three separate outputs (target identity, predicted
liking, confidence), computer-only; preserve the gin-vetiver EDP formula.

1. Extend the existing hedonic module without changing legacy callers' scores.
2. Add explicit design constraints: required anchors, caller-defined lower
   bounds and ratio ceilings. These are formulation intentions, not fitted
   perceptual thresholds. A pass is not proof of perceived identity.
3. Add an experimental intensity-weighted binary liking estimator, following
   the scope of Lapid et al. (2008), DOI 10.1093/chemse/bjn026. Require exact
   stimulus-name, concentration and context binding plus source provenance.
   Do not infer mass ppm from stock microlitres or multiply w/w by volume as
   exact accounting. Missing matched data yields no score. Larger mixtures
   remain outside this estimator's scope.
4. Report coverage separately from model validation; even full input coverage
   does not automatically admit an experimental estimator to optimization.
5. Connect a rejection-aware adapter to the existing search API. Retest the
   saved perfume and deliberate identity-breaking counterexamples. Save a
   diagnostic receipt without altering formulas or inventory.

Evidence: docs/research/HEDONIC_EVIDENCE_ACROSS_PERFUME_FAMILIES_20260909.md.
No new pipeline script, non-OpenAI provider, physical trial or release action.
