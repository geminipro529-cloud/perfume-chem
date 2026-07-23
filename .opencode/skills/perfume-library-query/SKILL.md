---
name: perfume-library-query
description: Query the local perfume knowledge base (perfume_kb.jsonl) for material data
---

## Location

`.opencode/library/perfume_kb.jsonl` — one JSON per line. No embedding. Lexical grep-based retrieval.

## Entry Types

| Source | ID prefix | Fields |
|---|---|---|
| Perfumer's World | `pw_sku_*` | base_name, dilution_pct, solvent, sku, price_usd_per_gram, in_local_inventory |
| Local inventory | `local_inv_*` | name, dilution, in_stock, in_perfumersworld, pw_skus |
| ODT data | `odt_*` | name, odt_air_ppb, odt_eth_ppm, vp_pa_25c, mw, logp |
| Reference contracts | `ref_*` | name, marker_groups, official_source, display_name |
| Family archetypes | `fam_*` | archetype, anchor_materials, forbidden_practices, drift_limits |
| Literature citations | `cit_*` | category, title, doi, finding |

## Retrieval Contract

```bash
# Find all entries for a material
grep -i '"name": "hedione"' .opencode/library/perfume_kb.jsonl

# Find Perfumer's World SKUs matching inventory
grep '"in_local_inventory": true' .opencode/library/perfume_kb.jsonl

# Find all family entries
grep '"source": "families_registry"' .opencode/library/perfume_kb.jsonl

# Find reference contracts
grep '"source": "reference_contracts"' .opencode/library/perfume_kb.jsonl
```

## Use Cases

1. **"Is X in inventory?"** -> grep for name, check `in_local_inventory`
2. **"What's the ODT of X?"** -> grep odt entries, read `odt_air_ppb`
3. **"What does X cost at Perfumer's World?"** -> grep pw entries, read `price_usd_per_gram`
4. **"What perfumes use Y?"** -> grep ref entries, check marker_groups
5. **"What family is Z?"** -> grep fam entries, check anchor_materials

## Cache

`.opencode/cache/retrieval/<query_hash>.json` — 24h TTL for repeated queries.
