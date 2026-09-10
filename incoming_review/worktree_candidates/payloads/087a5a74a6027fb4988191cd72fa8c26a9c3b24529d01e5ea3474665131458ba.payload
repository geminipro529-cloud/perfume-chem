# Gin Vetiver - Cypress Air EDP: concurrent structural run

Date: 2026-09-09. Decision: **NO FORMULA CHANGE**.

Executed `optimize_concurrent_hedonic_design` against the actual saved v4 EDP,
not a synthetic two-material fixture. Full machine-readable receipt:
`output/gin_vetiver_concurrent_structural_20260909.json`.

## Source and stock verification

Source: `formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json`.
SHA256: `426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.
All 18 exact stock IDs resolved through `parse_current_inventory`, with owned,
execution-ready states and matching fraction, fraction basis and carrier.
No inventory, authority pins, source code or formula doses changed.

5400 uL nominal fragrance stocks plus the existing 24600 uL ethanol remains
the saved 30000 uL nominal batch. Exact active w/w ppm is not established from
these volume-dosed mass-fraction stocks; no density of 1 was silently imposed.
No new stock or deliberately declared DEP carrier was introduced. This is not
an analytical assay for DEP traces or proof of carrier odorlessness.

## Frozen evaluator

Version: `gin-vetiver-composition-preservation-v1`.
This is an explicit **baseline-preservation policy**, NOT a model of liking,
perceived richness, layering or temporal evolution.

Hard constraints:

- Keep juniper, natural Indian vetiver, cypress and Grapefruit FCF present.
- Juniper >=750 uL; natural vetiver >=700 uL; Grapefruit FCF >=320 uL.
- Cypress/juniper raw-volume ratio <=50/750, inherited from the earlier
  conservative design-preservation diagnostic, not a perceptual threshold.
- Preserve 5400 uL total and the same exact stock set.

Two explicit nonnegative losses, each `max(0, (baseline_group - current_group)
/ baseline_group)`:

- Body-stock retention: natural vetiver, Iso E Super, Clearwood, Vetikon,
  Hedione, Virginia cedar and Timberol; baseline group sum2870 uL.
- Citrus-bridge-stock retention: petitgrain, terpinyl acetate and coriander
  seed EO; baseline group sum300 uL.

These sums are composition bookkeeping. Equal raw volumes do not imply equal
odor strength, equivalent body or interchangeable functions. They are not OAV,
headspace contributions or predicted perceived shares. No such claim is made.

Search bounds are baseline +/-20% for explored neat stocks, except cypress
40-50 uL. These are exploratory limits, not literature-derived optimum ranges.
Other stocks, including grapefruit and both diluted stocks, remain fixed.
Existing declared carrier doses therefore remain unchanged.

## Concurrent lanes and execution

Every directed transfer within each group was offered, with steps50,25,10 uL:

1. Gin/citrus: juniper, petitgrain, terpinyl acetate, coriander seed EO, Hedione.
2. Vetiver/body: natural vetiver, Iso E Super, Clearwood, Vetikon, Hedione.
3. Cypress/finish: cypress, Virginia cedar, Timberol, Iso E Super.

Three workers; 12-parent-round maximum. One scenario:
`nominal_stock_composition`. No repeated identical evaluations were presented
as temperature or drydown robustness. No evaluator revision was supplied:
there was no independently supported replacement to admit in this run.

The controller returned `COMPUTATIONAL_TARGET_MET` in one parent round and
retained the baseline. Each lane evaluated only its starting formula because
both baseline losses were already zero. **This status does not mean hedonic
optimization was achieved.** It is expected for baseline-preservation losses.

To avoid presenting that early stop as a candidate tournament, a separate
parallel sweep evaluated the full declared one-transfer neighborhood:

| Outcome | Proposals |
|---|---:|
| Outside explicit search bounds | 67 |
| Violated hard design constraints | 18 |
| Regressed a stock-retention objective | 15 |
| Tied baseline on both stock-retention objectives | 56 |
| Total | 156 |

Four independent adverse examples were also rejected: complete juniper removal,
complete natural-vetiver removal, cypress increased to500 uL while reducing
juniper, and half the natural vetiver replaced with Hedione.

## Interpretation

The workflow runs on the real perfume and protects named design constraints.
It does **not** yet discriminate the 56 tied proposals by perceived body,
layering, quality or preference. There is no evidence-backed hedonic winner.
It would be misleading to turn one of these ties into a revised mixing card.

The saved v4 EDP remains unchanged. No release pipeline, physical compounding
or preliminary mixing requirement was invoked. The next model work is an
independently justified, target-specific ranking of body/texture/continuity
among constraint-preserving candidates, with counterexample tests and explicit
uncertainty. Raising ingredient counts or inventing target ratios is not that
model. This limitation does not require the user to mix a preliminary sample.
