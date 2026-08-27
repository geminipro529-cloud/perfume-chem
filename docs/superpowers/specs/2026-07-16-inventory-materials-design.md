# Inventory Material Sync Design

**Date:** 2026-07-16

**Goal:** Add the newly received Alpha Irone, Orris Liquid, hydroxycitronellol, and viscous olibanum stock without leaving inventory, identity, physical-property, ODT/OAV, or natural-mixture paths inconsistent.

## Decision

Use a full data-path sync rather than an inventory-only update.

1. Record only the stock facts supplied by the user: Alpha Irone at 30% in the existing IPM preparation, Orris Liquid at 30% with no assumed solvent, neat hydroxycitronellol, and 3 g of viscous olibanum resinoid.
2. Correct availability parsing so `DEPLETED` entries are not returned when callers request available stock only.
3. Add or update data-spine records, canonical aliases, ingredient profiles, odor-family/activity-coefficient metadata, and ODT records.
4. Model Orris Liquid and viscous olibanum as natural mixtures using composite OAV. Retain effective single-material values only as explicitly labeled fallbacks for modules that do not yet consume composite OAV.
5. Add regression tests before production edits, then run focused and broader scientific-contract tests.

## Alternatives Considered

### Inventory Only

Rejected. It would make the materials visible to the inventory parser while leaving profile, vapor-pressure, threshold, and formula-state lookups incomplete.

### Four-Location Sync Without Composite OAV

Rejected. Orris Liquid and olibanum resinoid are mixtures; assigning either a monomolecular OAV would violate the repository's natural-mixture contract and overstate precision.

### Full Sync With Transparent Proxies

Selected. It preserves runtime compatibility while distinguishing measured values, supplier declarations, literature-derived mixture fractions, and heuristic threshold fallbacks.

## Evidence Basis

- Hydroxycitronellol identity and physical data: Api et al., *Food and Chemical Toxicology* 183 (2024), DOI `10.1016/j.fct.2023.114281`; CAS 107-74-4, MW 174.28 g/mol, measured log Kow 1.5, density 0.928 g/mL, and vapor pressure 0.000552 mmHg at 25 C. The paper describes a very mild, tenacious, clean-sweet rose-peony floral odor and distinguishes it from hydroxycitronellal.
- Hydroxycitronellol structure: PubChem CID 249494. Direct ODT data for CAS 107-74-4 were not found, so the runtime ODT will be tagged `DERIVED`, not peer-verified.
- Alpha Irone identity and stock character: CAS 79-69-6 and supplier SKU 8II00243; the existing 30% IPM preparation is already recorded in inventory and will be confirmed rather than duplicated.
- Orris Liquid stock: PerfumersWorld SKU 8IQ24653, CAS 8002-73-1, density 0.930, and supplier description of an 80-85% irone liquid. The composite model will use the midpoint, 82.5%, as an alpha-irone-equivalent pool because the supplier does not publish the isomer split.
- Orris composition context: `Iris pallida` GC-MS literature identifies alpha-irone, gamma-irone, and other ionone-family character compounds, while published commercial orris oils vary substantially. The supplier-specific assay therefore takes precedence over generic orris-butter composition.
- Viscous olibanum stock: PerfumersWorld SKU 2QK21856, CAS 8016-36-2, specifies about 30% benzyl benzoate and a non-pourable Boswellia carteri resinoid.
- Olibanum volatile context: published Boswellia carteri analyses consistently identify alpha-pinene, limonene, myrcene, and sabinene but show strong chemotype and extraction variability. The composite model will include the declared benzyl benzoate plus a conservative partial volatile fraction and leave the uncharacterized resin matrix unmodeled.

## Data Boundaries

- Supplier usage ranges are guidance, not IFRA maxima, and will not be written into `ifra_max_pct_edp`.
- Hydroxycitronellol's reported 95th-percentile fine-fragrance exposure of 0.14% is not a legal or IFRA cap.
- Composite constituent fractions are OAV modeling inputs, not a certificate of analysis for the user's physical bottle.
- Unknown Orris Liquid solvent and unavailable olibanum density will remain explicit rather than being invented.

## Acceptance Criteria

- Available-stock parsing returns Alpha Irone at 30%, Orris Liquid at 30%, hydroxycitronellol neat, and olibanum resinoid neat; it excludes depleted hydroxycitronellal and depleted olibanum 10% stock.
- All four requested names resolve to canonical data and ingredient profiles without confusing hydroxycitronellol with hydroxycitronellal.
- Hydroxycitronellol has ppm-compatible ODT metadata marked as derived.
- Orris Liquid and olibanum resinoid return non-empty constituent lists and positive composite OAV values.
- Focused tests and the repository's scientific-contract tests pass.
- Only intended files are committed; the user's untracked root `.txt` files remain untouched.
