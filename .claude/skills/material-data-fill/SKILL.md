---
name: material-data-fill
description: Fill missing physics, odor-threshold or composition data for perfume-chem inventory materials from cited sources, tracked in one gap ledger, and wire it into the engine.
---

# Material data fill

> **Status: DRAFT (2026-10-08).** Not yet proven over many runs. If any step here
> is wrong or missing when you use it, fix this file in the same change and add a
> line under "Known issues / change log". Keep `.claude/skills/` and
> `.agents/skills/` copies identical (`tests/test_skill_mirrors.py` checks this).

Use when the gate shows UNKNOWN MW/VP/ODT or a missing natural composite, or when a
material is added to inventory.

## 1. Fix names before researching
Much "missing" data is a spelling mismatch (e.g. Bergamot FCF vs Bergamot FCF oil
Sicilian) or a value present in one physics store but not another. Check
`name_utils._ALIASES`, the YAML `aliases`, and all four stores before searching.

## 2. Work from one gap ledger
Keep one row per owned material with a status per field (MW, log Kow, VP, air ODT,
composition for naturals, density, IFRA): FOUND / PARTIAL / NOT FOUND / HOLD, plus
the source and what was already searched, so nobody searches twice. Update the
existing ledger rather than starting a new list.

## 3. Priority
Materials in formulas being built now first, then by how many formulas use them.
Air thresholds first for anything meant to be smelled; composition first for
naturals.

## 4. Sources, cheapest first
1. The repo's other stores: `data/materials/<LETTER>.yaml`,
   `engine/odor_thresholds.py` ODT_DATA (count duplicate keys; the last wins),
   `engine/ingredient_intelligence.py` _PROFILES,
   `engine/pipeline/natural_absolute_decomposition.py`.
2. Kenny's local PerfumersWorld snapshot (read-only):
   `data\research\perfumersworld\20261007_01a1152f\document_texts_refined.jsonl.gz`.
   Query with `zcat | python3` filtering by SKU, never a recursive find. Map
   inventory lines through `inventory_crosswalk.json`. Allergen tables are supplier
   typical composition, not a lot assay.
3. Offline on Kenny's PC: `python D:\agent-cache\tools\chemprops.py <name|CAS|smiles:...>`
   gives MW and formula (RDKit, exact from the structure), a Crippen logP
   (a CALCULATED estimate: record it as `logp_source: rdkit-crippen-estimate`, never
   as measured) and VP at 25 C only from thermo correlations fitted to measured data
   (NIST WebBook Antoine, Landolt, Poling, Perry, VDI). It refuses thermo's
   estimation methods, which were 10-1000x off on fragrance materials. A VP flagged
   `extrapolated` comes from a fit outside 25 C: record it with that flag or prefer a
   measured 25 C value from step 4. Names resolve through NCBI (PubChem synonyms)
   because thermo's own name list has errors (it files nerol and geraniol under one
   CAS); any WARNING line means the VP was withheld, so treat it as a gap.
4. RIFM safety assessments (measured log Kow, VP).
5. Threshold papers (Buettner group, Czerny et al. 2008) and ISO standards.
6. The web: on Kenny's PC use the self-hosted crawler
   `python D:\agent-cache\webcrawl\webcrawl.py scrape|crawl|map|search` (cloud
   sessions run it through the desktop-commander device shell; see its README).
   Otherwise use the Firecrawl connector tools (the Firecrawl CLI and direct HTTP
   are blocked by the cloud proxy).

Batches of about 10 materials can run in parallel, each writing its own file, merged
once into the ledger.

## 5. Record
Quote values exactly with their source URL. Never estimate, average or renormalize
(the one exception: a labelled RDKit Crippen logP when no measured log Kow exists);
when sources disagree, list both. An odor threshold must state phase (air or
ethanol), units and method; a value on an incompatible basis is not an ODT
(Rule 1). Natural compositions keep the unknown remainder (Rule 4). Many air
thresholds were never measured: leave those on HOLD so the gate shows UNKNOWN, and
say whether a supplier CoA would close it.

## 6. Wire into the engine (on a PR branch, never master)
Until a single YAML source generates the other stores, a material must agree in
four places: `inventory.txt` (if new), `data/materials/<LETTER>.yaml` (`mw_g_mol`,
`logp`, `vp_25c_pa`, `odt_air_ppb`, `odt_eth_ppm`, aliases matching the inventory
name), `engine/ingredient_intelligence.py` (_PROFILES, _TYPICAL_DOSE,
_ODOR_FAMILY_MAP, _ACTIVITY_COEF_MAP) and `engine/odor_thresholds.py` ODT_DATA.
Composites go in `_ABSOLUTE_CONSTITUENTS` plus `name_utils._ALIASES`. Cite the
source next to each value. Run the focused tests
(`pytest tests/test_science_audit.py` and any material test), then re-gate an
affected formula with the `perfume-gate-run` skill to show the gap closed.

## Known issues / change log
- 2026-10-08: first draft, aligned with the gap-ledger workflow proposed in the
  material data gaps thread (names first, one ledger, priority, cheap sources first).
- 2026-10-08: added the self-hosted webcrawl tool as a web source.
- 2026-10-08: added the offline chemprops tool (RDKit + thermo, measured-only VP).
- 2026-10-08: chemprops resolves names via NCBI and refuses thermo's mismatched records.
