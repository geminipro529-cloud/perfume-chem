# Gin Vétiver — Cypress Air EDP: selected computational candidate C1

Date: 2026-09-09. **This bounded pre-mixing design pass is complete and selects one revised computational candidate. It does not establish that the full perfume is hedonically optimal, smelled, or mixing-ready. No preliminary physical mixture is required.**

## Decision

Choose **gin-forward with a developed vetiver/wood base**, not the slightly higher-scoring but less juniper-led alternatives. The original v4 formula is preserved. Candidate C1 moves more allocation to natural vetiver, juniper and dry woody support while keeping cypress at 50 raw µL and the fragrance-stock subtotal at 5,400 raw µL.

The final source-bound run evaluated **512 optimizer proposals + 512 independent random proposals + the baseline**, then separately evaluated the rounded engineer-selected candidate: **1,026 composition evaluations / 3,078 scenario predictions**. These are repeated computational evaluations, not human measurements. The rounded candidate is not silently called a sampled Pareto point.

## Actual three-direction comparison

One common bounded search was post-filtered into three overlapping engineer-declared envelopes. There were NOT three equal-budget independent optimizations.

| Declared envelope | Candidate memberships | Adaptive / random | Pareto points | Best nominal partial pleasantness |
|---|---:|---:|---:|---:|
| Vetiver-bodied | 394 | 150 / 244 | 1 | 6.068 |
| Gin-forward, developed base | 130 | 57 / 73 | 1 | 6.020 |
| Rounded woody-vetiver | 340 | 241 / 99 | 2 | 6.094 |

Pareto axes are the three scenario-specific pleasantness losses. All other learned descriptors remain diagnostics; there is no learned richness, layering or EDP-body axis. Membership counts overlap and do not sum to the total search count.

The gin-forward source point came from the independent random arm. It allocates about 932 µL juniper and 937 µL natural vetiver. The highest partial-model woody alternatives instead allocate about 454–529 µL juniper and 1,419–1,451 µL natural vetiver. Selecting the gin-forward point is a deliberate preference for the requested identity, not maximum numerical pleasantness. Overall adaptive/random best loss difference was only -0.0000049435 in this run; no search-method superiority is established.

## Selected computational quantities

These are **raw stock-volume design variables, not a released compounding card**. Exact active mass ppm and headspace OAV are not inferred from these volume values. Stocks with w/w preparations remain at their original quantities; carrier-bearing stocks have not been rebased.

| Material | Current stock form | v4 raw µL | C1 raw µL | Change µL |
|---|---|---:|---:|---:|
| Iso E Super | Neat | 850 | 1330 | +480 |
| Ambrox Super | 25% w/w; dpg + ipm + ethanol | 400 | 400 | 0 |
| Hedione | Neat | 600 | 310 | -290 |
| Vetival | Neat | 80 | 80 | 0 |
| Benzyl Benzoate | Neat | 200 | 20 | -180 |
| Vetiver EO (India) | Neat | 700 | 940 | +240 |
| Cedarwood Virginia | Neat | 100 | 70 | -30 |
| Cypress EO | Neat | 50 | 50 | 0 |
| Clearwood | Neat | 200 | 200 | 0 |
| Timberol | Neat | 70 | 70 | 0 |
| Vetikon | Neat | 350 | 100 | -250 |
| Ambrettolide | 10% w/w; dpg | 250 | 250 | 0 |
| Habanolide | Neat | 180 | 180 | 0 |
| Juniper Berry EO | Neat | 750 | 930 | +180 |
| Coriander Seed EO | Neat | 60 | 120 | +60 |
| Grapefruit FCF oil Sicilian | Neat | 320 | 200 | -120 |
| Petitgrain EO Paraguay | Neat | 160 | 90 | -70 |
| Terpinyl Acetate | Neat | 80 | 60 | -20 |
| **Fragrance-stock subtotal** | | **5400** | **5400** | **0** |

Ethanol 96% remains a nominal 24,600 µL. The batch remains nominally 30 mL and 18% fragrance-stock volume, not 18% exact odorant-active w/w. No selected stock declares DEP; no deliberate DEP addition is proposed. Trace impurities are not analytically excluded.

## Why this remains the requested perfume

- **Gin identity:** juniper increases 750 → 930 µL. Coriander seed increases 60 → 120 µL as the botanical-spice detail; grapefruit FCF remains the only citrus oil requested for this role.
- **Vetiver subject:** natural Indian vetiver increases 700 → 940 µL. It is not replaced by generic woody material. Vetikon falls 350 → 100 µL, favoring the natural root material over this supporting bridge.
- **EDP body hypothesis:** Iso E Super increases 850 → 1,330 µL as abstract woody support; existing Clearwood, mineral-amber stock, restrained Timberol and musks remain. This is an intended architecture, not measured richness or a longevity prediction.
- **Light cypress:** unchanged at 50 µL; no move toward a heavy cypress perfume.
- **Reduced diffuse/citrus support:** Hedione 600 → 310 µL, grapefruit 320 → 200 µL, petitgrain 160 → 90 µL. Hedione remains permitted, without constructing a jasmine accord. No coffee or ginger enters.
- The six frozen stocks are retained to localize this experiment, not certified optimal. The inherited two-musk relationship has not been empirically validated by this pass.

Source-backed roles remain in the plan: IFF Iso E Super, dsm-firmenich Hedione/Clearwood/coriander, Symrise Vetikon/Timberol, Robertet petitgrain. These supplier descriptions support material roles, not these exact ratios.

## Measured-data model results after stereochemistry correction

Values are raw **predictions for the modeled partial composition**, not measured perfume ratings and not percentages.

| Representative composition scenario | v4 predicted pleasantness | C1 predicted pleasantness | Difference |
|---|---:|---:|---:|
| Nominal profile | 5.84917 | 6.02276 | +0.17359 |
| Hydrocarbon-richer engineering stress | 5.82459 | 5.99757 | +0.17299 |
| Oxygenated-richer engineering stress | 5.87875 | 6.05526 | +0.17651 |

The stress multipliers (0.8 and 1.15 by declared constituent class) are engineering sensitivity probes, not supplier-lot ranges, statistical confidence intervals or samples from a fitted uncertainty distribution.

**Counterevidence retained:** nominal Woody decreases 0.55595 → 0.48865; Pine decreases 0.51445 → 0.50565; Intensity decreases 6.06867 → 5.99844. Citrus increases 1.05893 → 1.16846. The model therefore does NOT corroborate a woody-intensity or total-intensity gain. Those endpoints have limited source-domain ratio-ranking validity, and the model has no richness/layering labels. Increasing woody stock allocation is not asserted to prove increased perceived woodiness.

The pleasantness gain (~0.17) is smaller than the model's source-domain held-out RMSE (~0.73). That RMSE is not a prediction interval for this EDP, and this comparison does not establish a statistically reliable or noticeable improvement.

## Coverage and extrapolation

- Twelve of eighteen stocks represented wholly or partly; six opaque, identity-unresolved or carrier-bearing stocks remain frozen and unmodeled.
- Nominal modeled raw-equivalent quantity: **3,128.69 / 5,400**, or **57.94%** of the raw stock basket under the proxy convention. Unresolved: **2,271.31**. This is NOT active-mass coverage or percentage of perceived smell.
- Baseline nominal modeled raw-equivalent quantity was 3,320.51. C1's coverage falls because more natural vetiver is allocated, and much of its profile is unresolved. Missing material is not treated as neutral.
- Expanded mixtures contain **32 molecular entries; training mixtures contain at most 10**. Every scenario flags component-count extrapolation. Shared component count between baseline and C1 does not establish transfer validity.
- Supplied natural lots are not assayed. Generic cedrene, eudesmol and isovalencenol remain unresolved rather than silently assigned questionable structures. Unreported fractions remain explicit; no renormalization to 100%.
- Geraniol and nerol now use separate PubChem E/Z SMILES. Repeated occurrences of truly identical represented molecules aggregate across oils.
- Nominal volume/fraction proxies do not supply densities, exact mass ppm, liquid/air ODT equivalence or OAV. No perceptibility, longevity or sillage claim is made. This hedonic research pass did not run the physical-release pipeline.

## Gate meaning and stopping point

- Search: **FINITE_BUDGET_COMPLETE**.
- Stock identity/form checks: **18 passed**.
- Selected proposal: **ENGINEER_SELECTED_COMPUTATIONAL_CANDIDATE**.
- Whole-perfume model coverage: **FAIL_TARGET_AND_MIXTURE_COVERAGE**.
- Sensory validation / physical release: **not established**.
- Mandatory preliminary physical trial: **none**.

The full-coverage failure remains visible and the research CLI returns nonzero; it does not invalidate the observed computational run or prove the perfume smells bad. It prevents presenting partial predictions as a complete-perfume guarantee. This is the stopping point for this approved bounded pass: one revised proposal, explicit comparative evidence, retained counterevidence, and no demand to mix before finishing the computational work. Further endless optimization of this same surrogate would not close its scientific gaps.

## Verification and artifacts

- 75 focused tests passed (global search, CLI, natural scenarios, DREAM mixture/dose regressions).
- Scoped Ruff passed; git diff --check passed.
- Final targeted audit: engine compile/lint/typecheck, golden formula/API regressions and fixture lock passed.
- Full repository audit: **10 checks passed, 9 failed, 2 Docker checks skipped**. Failures include pre-existing inventory/artifact consistency, Python 3.14 collection errors, backend source contracts and science-coverage checks. The repository is not globally release-clean.
- All three independent-review P2 issues were fixed: E/Z collapse, silently ignored unknown scenario multiplier names, and unverified candidate lineage. The final run checks the cited receipt hash, source arm, envelope front and component-wise 10-µL rounding before recording verified lineage.
- No inventory changes, parent formula edits, new worktree, new pipeline script, commit, push or physical mixing.

Files:
- Selected computational record: `data/design_briefs/gin_vetiver_edp_selected_candidate_20260909.json`
- Reproducible plan: `data/design_briefs/gin_vetiver_edp_natural_selected_v2.json`
- Final numerical receipt: `output/design_portfolios/20260909_201623_839780.json`
- Receipt SHA256: `bd9b65f04145a3aaaa339d486a0633a6e745a7d1b7f865d4608f23122a692927`
- Natural source manifest: `output/optimizer_research_20260909/natural_structures/manifest_stereo_v2.json`
- Full audit: `output/optimizer_research_20260909/natural_core_full_verification.json`
- Final code audit: `output/optimizer_research_20260909/natural_core_final_code_verification.json`
