# Inventory Blocker Closure — 2026-09-15

## Status

`PARTIAL`: all stock facts supplied by the user on 2026-09-15 are represented
in the live successor authority, inventory text, material registry, and derived
cache. Eight stock rows became executable, Maple Lactone was removed, and four
filtered tinctures now have generic literature-composite OAV screening models.

The remaining holds require stock-preparation facts or chemical model evidence
that is absent from the repository. The implementation leaves those values
unknown instead of converting them into exact ppm, OAV, or release claims.

## Current Result

| Measure | Before this receipt | Current | Change |
|---|---:|---:|---:|
| Parsed physical stock rows | 237 | 236 | -1 |
| Execution-ready stock rows | 179 | 187 | +8 |
| Held stock rows | 58 | 49 | -9 |
| Inventory text rows | 285 | 287 | +2 |
| Canonical requirements: `OWNED` | 194 | 194 | 0 |
| Canonical requirements: `PREPARATION_REQUIRED` | 25 | 25 | 0 |
| Canonical requirements: `GAP` | 43 | 43 | 0 |
| Canonical requirements: `UNRESOLVED` | 18 | 18 | 0 |

The successor overlay is pinned to normalized inventory SHA-256
`80bba680df969c0ca9d51bb74e81c417ff6b9734357c58ed5321b9b4d847060e`.
The material cache is synchronized to overlay SHA-256
`d0ee1d77b015152c4ffc76a351a693067bf61475eb71a9bf60aecf3fcb9842a2`;
the rebuilt cache SHA-256 is
`ff9bab57af275d150ec81bece76fb36da28e2f5f93d121870cd5f7b4aa1453ed`.

## Stock Facts Applied

| Material | Current stock contract | Execution state | Quantitative limit |
|---|---|---|---|
| Romandolide | Neat / as supplied | Ready | Lot assay and density remain unverified. |
| Liffarome | 10% w/w in DEP | Ready for raw-volume transfer | Exact active mass from a volume dose requires stock density. |
| Methyl Laitone | 20% v/v in ethanol | Ready for raw-volume transfer | OAV in w/w ppm still requires density; VP and ODT model fields remain unknown. |
| Castoreum Synthetic | 10% w/w in DEP | Ready for raw-volume transfer | Exact active mass from a volume dose requires stock density. |
| Siam Benzoin | 50% w/w in DPG | Ready for raw-volume transfer | Exact active mass from a volume dose requires stock density. |
| Peru Balsam Resinoid | 50% w/w in DEP | Ready for raw-volume transfer | A separately labeled 10% preparation is still required where a formula requests 10%. |
| Maple Lactone | Not owned | Removed | Formulas requesting it remain inventory gaps. |
| Evernyl | 10% w/w in DPG, fully dissolved | Ready for raw-volume transfer | Exact active mass from a volume dose requires stock density. The separate neat Evernyl Crystals stock remains ready. |
| 2-Acetyl Pyrazine | 1% in DPG | Held | Percentage basis is unconfirmed. The separate neat stock remains ready. |
| Skatole | 1% in DPG | Held | Percentage basis is unconfirmed. |
| Methyl Pamplemousse | 10% w/w in ethanol | Ready for raw-volume transfer | Exact active mass from a volume dose requires stock density. |
| Gamma Nonalactone | 10% in ethanol | Held | Percentage basis is unconfirmed. |

The user's `wthanol` spelling was normalized to `ethanol`; no other stock fact
was inferred from the typo.

## Citrus and Evernyl Coverage

The live `CITRUS / TOP` section contains 29 stock lines that deduplicate to 26
material identities for formula-state screening. All 26 currently produce a
modeled OAV. The ten natural oils in that set use constituent-composite OAV:
Bergamot FCF, Blood Orange, Cedrat FCF, Ginger, Grapefruit FCF, Lime Distilled,
Neroli, Orange Peel, Petitgrain Paraguay, and Red Mandarin. These are literature
screening models, not supplier-lot headspace assays.

Evernyl 10% w/w in DPG is fully dissolved and execution-ready. Its mass-fraction
basis is known; an exact conversion from a raw-volume dose to active mass still
requires the working stock density. The separate neat Evernyl Crystals stock is
also execution-ready.

Methyl Pamplemousse 10% w/w in ethanol is execution-ready for raw-volume
transfer. There is no current Citrus/Top identity whose only owned stock is held.
Four legacy aldehyde working stocks remain held because their basis and carrier
were never recorded, but each identity has an executable alternative: Aldehyde
C10 has 1% v/v ethanol and neat stocks, Aldehyde C11 has a neat stock, and
Aldehyde C12 MNA has 1% v/v ethanol and neat stocks.

## Tincture Model

The following percentages now act as user-authorized nominal property-model
fractions:

| Tincture | Starting-charge model | Generic characterized subset | Modeling state | Release state |
|---|---:|---:|---|---|
| Turkish Storax | 20% w/w in ethanol | 15.66% of GC area | Composite OAV screen enabled | Held |
| Vietnamese Benzoin | 40% w/w in ethanol | 60% generic resin fingerprint | Composite OAV screen enabled | Held |
| Kenyan Myrrh | 20% w/w in ethanol | 0.13% of GC-MS area | Composite OAV screen enabled | Held |
| Oman Frankincense | 33% w/w in ethanol | 2.1485% of resin mass proxy | Composite OAV screen enabled | Held |

Complete extraction and funnel draining support use of the preparation
percentage as the requested design-model input. They do not measure the mass of
resin dissolved in the final filtrate. Each record therefore carries
`nominal_property_model_ready=true`, `approximate=true`, and
`FINAL_DISSOLVED_FRACTION_UNMEASURED`. The optimizer may use these fractions for
screening and candidate ranking. The OAV runtime now applies partial generic
constituent profiles without renormalizing the characterized subset. The
unmodeled constituents remain unknown, not odorless. Preflight and release stay
held against an exact active-dose claim.

The proxy sources are [Wang et al. on Liquidambar orientalis
Styrax](https://doi.org/10.1093/jpp/rgad093), [Burger et al. on Siam benzoin and
Styrax tonkinensis](https://doi.org/10.1016/j.foodchem.2016.05.015), [Ahamad et
al. on an ethanol extract of Commiphora
myrrha](https://doi.org/10.1016/j.jsps.2016.10.011), and a [Boswellia sacra
review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8881160/) combined with the
repository's existing partial frankincense-oil fingerprint. None is an assay of
the user's current bottle or resin lot.

**Retention decision: `KEEP`.** The generic profiles remove four live
OAV-unknown screening blockers and let regular optimization rank these tinctures
without waiting for bottle assays. This is a validation-workflow improvement;
the change does not claim lower CPU time per formula-state calculation.

## Remaining 49 Physical-Stock Holds

| Missing fact or identity issue | Held rows | What closes it |
|---|---:|---|
| Legacy diluted working-stock preparation details | 39 | Record percentage basis and carrier for each V5 working stock. |
| Percentage basis missing after carrier confirmation | 3 | State `w/w` or `v/v` for 2-Acetyl Pyrazine 1% DPG, Skatole 1% DPG, and Gamma Nonalactone 10% ethanol. |
| Filtered tincture final dissolved fraction unmeasured | 4 | Required only for exact active-dose/release claims; nominal optimization is already enabled. |
| Carrier unspecified | 2 | State the carrier for Caryophyllene Acetate 20% w/w and Cis-3-Hexenyl Salicylate 20% w/w. |
| Cedarwood identity unresolved | 1 | State the botanical species for the neat China-origin Cedarwood EO. |
| **Total** | **49** | |

The optimizer now excludes held stocks from automatic stock-fraction inference.
Only the four explicitly authorized tincture records may enter through the
nominal-model exception. This prevents an incomplete stock descriptor from
silently becoming an optimization input.

## Remaining Model-Data Limits

These do not negate the stock updates, but they can still prevent complete
headspace OAV validation:

- Liffarome lacks identity-bound MW, VP, and ODT values in the active data
  spine.
- Methyl Laitone has a manufacturer-bound molecular weight; VP, logP, and ODT
  remain unknown for the active entity.
- All four tinctures now have explicit generic composite profiles for screening.
  Their characterized fractions are partial: Turkish Storax 15.66%, Vietnamese
  Benzoin 60%, Kenyan Myrrh 0.13%, and Oman Frankincense 2.1485%. The unmodeled
  fractions remain unknown and prevent a complete tincture OAV claim.
- None of the four generic profiles establishes extraction recovery, density,
  dissolved-solids fraction, or composition for the user's specific tincture.
  The Kenyan label and Oman resin species also remain unresolved. Exact ppm,
  active-dose equivalence, IFRA, and release decisions still require
  bottle-specific evidence.
- The repository-wide reconciliation report currently identifies 89 inventory
  rows with profile-versus-registry scalar disagreements. These are data-quality
  review items and are not overridden by a stock receipt.

Five existing exact stock labels were also bound to their already-recorded
chemical identities: Anisaldehyde 10% v/v in ethanol, Ethyl Maltol 1% v/v in
ethanol, Helional 10% v/v in ethanol, Hexyl Acetate 1% v/v in DPG, and Cinnamyl
Alcohol 50% w/w in DPG. No chemical properties were added. The audit was also
corrected so unresolved materials with a numeric zero placeholder no longer
count as modeled OAV coverage. Together, the fixes changed truthful live OAV
screening coverage from 84.615% (209/247) to 85.83% (212/247). Adding the four
generic tincture composites raises current screening coverage to 87.449%
(216/247).

The ambiguous global alias `Olibanum` to `Olibanum Resinoid` was removed. Exact
resinoid labels still resolve; a generic literature term no longer receives a
specific stock identity.

## Verification

- Offline material reconciliation: 383 cache records, all original names
  preserved, 236 current physical stock rows, and current overlay hash verified.
- Focused inventory, authority, cache, optimizer, alias, preflight, science,
  material-data, knowledge-rule, and performance checks: `220 passed, 1 skipped`.
- Focused Ruff check: passed.
- `git diff --check`: passed with line-ending warnings only.
- The earlier quick project-verification snapshot predates the current v14 stock
  authority and generic tincture profiles and is superseded for this change. A
  full release verifier was not run because this is a screening-data and
  inventory update, not a formula release.
- No formula pipeline was run, so this change makes no sensory, OAV-headspace,
  IFRA, or release claim.
