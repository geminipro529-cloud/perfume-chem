---
slug: next-run-phase1-v1
status: executing
intent: clear — close 3 highest-impact gaps from weakness report
approach: 3 parallel workstreams: (1) EU allergen completion, (2) batch testing fix, (3) receptor/hedonic enrichment via PubChem
---

# Plan: Next Run — Phase 1 Gap Closure

## Priority (from weakness report)
| # | Gap | Impact | Effort | Approach |
|---|-----|--------|--------|----------|
| 1 | EU Allergens — 29 missing | Blocks EU compliance | Low | Complete JSON from authoritative source |
| 2 | Batch Testing — name normalization | Blocks formula validation | Medium | Add alias resolution to preflight |
| 3 | Receptor Mapping — 33 only | Blocks bioactivity | Medium | Batch PubChem search for known receptors |

## Tasks (all parallel)
1. Complete eu_2023_1545_allergens.json to 82 entries
2. Add name alias normalization to pipeline_preflight_guard
3. Batch PubChem receptor search for top 50 materials
4. Verify compound fixes with formula gate test
