# Material data, known issues and past learnings

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Data Pipeline Architecture

### Data flow

```
ODT_DATA (odor_thresholds.py) ──→ ingredient_intelligence._PROFILES ──→ _generate_material_properties.py ──→ material_properties.json
        ↕ (enrich at import)              ↕ (alias resolution)                                 ↑
   ODT_VERIFICATION                  name_utils._ALIASES                                         ├─ CAS_MAP (generator)
                                                                                                 ├─ TYPICAL_DOSE (generator)
                                                                                                 └─ PubChem live API (generator)
```

Three separate data paths consume material properties:
1. **`material_properties.json`** — used by scoring, OAV guards, and analysis scripts
2. **`ingredient_intelligence._PROFILES`** — used directly by pipeline gates, formula_state, and direct profile lookups
3. **`ODT_DATA`** — used by pipeline formula_state._lookup_odt(), ingredient_intelligence auto-populate

**Critical: These three paths are NOT automatically synchronized.** Changes to one often leave stale values in another. Run `python _generate_material_properties.py` to resync.

### `material_properties.json` coverage (verified 2026-05-11)

| Field | Coverage |
|---|---|
| MW, VP, cLogP | 210/210 (100%) |
| ODT air, ODT ethanol | 210/210 (100%) |
| OAV typical | 210/210 (100%) |
| Smell strength, anosmic risk | 210/210 (100%) |
| Note, role, activity_coef | 210/210 (100%) |
| Odor family | 209/210 (99%) |
| Texture, synergies | 204/210 (97%) |
| Hedonic | 161/210 (77%) |
| IFRA Cat4 limit | 87/210 (41% — expected, not all restricted) |
| Hill EC50 | 25/210 (12%) |

## Known Data Quality Issues

### 1. ODT_VERIFICATION vs ODT_DATA duplication
`odor_thresholds.py` has TWO dicts — `ODT_DATA` (numeric values) and `ODT_VERIFICATION` (metadata only). Both contain entries for the same materials. **Numeric ODT values must exist in BOTH** — the last entry wins in `ODT_DATA`, so `ODT_VERIFICATION` entries that appear later in the file do NOT affect lookups. However, `_lookup_odt()` only reads `ODT_DATA`.

### 2. ~~Hedione/Hedione HC ODT collision~~ (FIXED 2026-05-25)
Fixed: Both `"hedione"` and `"hedione hc"` in ODT_DATA now correctly use `odt_air=0.05`. `ODT_DATA` and `ODT_VERIFICATION` are separate dicts — the collision was due to a wrong numeric value (20.0 → 0.05) in `ODT_DATA`, not an alias issue.

### 3. Non-inventory legacy entries
`material_properties.json` contains entries with `"in_inventory": false` — materials that existed in the knowledge graph but are no longer in `inventory.txt`. These were previously copied as-is without validation. The generator now force-overrides their physical properties (MW, VP, cLogP, ODT) from `_PROFILES` on regeneration.

### 4. Name normalization inconsistencies
`inventory_parser._canonical_name()` strips trailing parentheticals (e.g., `"Rosemary EO (French...)"` → `"Rosemary EO"`), but `normalize_name()` in `name_utils.py` preserves them. The generator ALIASES dict bridges this gap, but must be kept in sync with inventory additions. The non-inventory enrichment loop also uses ALIASES for alias resolution.

### 5. `_generate_material_properties.py` is NOT import-safe
Running `import _generate_material_properties` executes the full generation pipeline at module level. Import for function access will trigger a full regenerate + PubChem API calls. The ALIASES and CAS_MAP dicts are defined at module scope and cannot be imported separately without side effects.

## Recent Changes (2026-05-11)

### Fixed: Benzoin Resinoid ODT in DHC V Formula
- ODT was 50.0 ppb (wrong), corrected to 3.0 ppb
- OAV recalculated from 0 to 5
- Material_properties.json physical properties corrected to match profile (VP=0.02 Pa, MW=212, cLogP=2.5)

### Fixed: ODT_DATA numeric values lost
32 materials had numeric `odt_air`/`odt_eth` values accidentally replaced by verification-only metadata in a previous edit. Restored from git HEAD with verification metadata preserved. Affected materials include: alpha-isomethyl ionone, alpha/beta ionone, hedione, iso e super, coumarin, vanillin, linalool, citronellol, geraniol, eugenol, indole, and others.

### Fixed: Generator force-override for non-inventory entries
`_generate_material_properties.py` now force-overrides physical properties (MW, VP, cLogP, note, role, texture, ODT) from profiles for ALL entries, including non-inventory legacy entries. Previously only filled NULL fields.

### Fixed: Missing profiles added
Added profiles to `ingredient_intelligence.py` for: Diethyl Phthalate, Dipropylene Glycol, Ethanol, Isopropyl Myristate, Triethyl Citrate, Lemon FCF oil Sicilian, Heliotropin, Molecule Iris. Added ODT entries for solvents (DEP, DPG, IPM, TEC).

### Fixed: Alias mapping errors
- `Cyclimal Aldehyde`: was aliased to `Florol` (wrong), corrected to `Cyclamen Aldehyde`
- Generator ALIASES: `amyl cinnamic aldehyde` → `ACA`, `rosemary eo` → `Rosemary EO (French Rosmarinus Officinalis leaf oil)`, `lemon fcf oil sicilian` → `Lemon FCF oil Sicilian`
- Added aliases for legacy variants with parenthetical names

## Session Learnings (2026-06-05)

### Composite OAV Model
- `engine/pipeline/natural_absolute_decomposition.py` decomposes 35+ naturals into GC-O constituents
- Injected at `formula_state.py:219` and `formula_state.py:567`
- Osmanthus absolute composite OAV is 100-500,000× higher than monomolecular
- When naturals show OAV 0, check: is the composite model covering this material?
- Common missing naturals: add to both `_ABSOLUTE_CONSTITUENTS` dict in decomposition module AND `name_utils._ALIASES` AND add YAML aliases in `data/materials/<LETTER>.yaml`

### Material Audit Checklist
Every new material must exist in 4 locations:
1. `inventory.txt`
2. `data/materials/<LETTER>.yaml` (with aliases matching inventory name)
3. `engine/ingredient_intelligence.py` (`_PROFILES`, `_TYPICAL_DOSE`)
4. `engine/odor_thresholds.py` (`ODT_DATA` — check for duplicates, last entry wins)

### Formula Optimization Workflow
1. Gate with `python scripts/formula_release_gate.py --formula-file <path> --expected-concentrate-ul <ul> --brief generic --json`
2. OAV report with `python scripts/format_oav_report.py <output.json>`
3. Full analysis with `python scripts/format_pipeline_analysis.py --input <output.json>`
4. Full scoring with `python scripts/verify_formula_workflow.py --formula-file <path>`
5. Always present the OAV ranking BEFORE discussing gate outcomes
6. Osmanthus at 500-700 µL of 10% is a clear lead (not a soliflore)
7. Bergamot at >100 µL creates a limonene pool that persists 4h+ — the nose adapts in 90s

### Perfumery Literature References
- Calkin & Jellinek (1994): chypre ratios, fixative loading
- Carles (1961): pyramid structure, accord ratios, material counts
- Ellena (2011): transparent watercolor, Hedione:Iso E ratio, material count ≤18
- Sinding et al. (2017): olfactory adaptation — high VP citrus habituates in 45-90s
- Laing & Francis (1989): humans track 3-4 components maximum
- Shiseido Féminité du Bois GCMS: gold standard woody-floral skeleton (Iso E 45.5%, Sandalore 9.4%, Cashmeran 1%)
- Dior Homme Parfum (Demachy, 2014): Sandalwood + Oud + Cedar + Leather base
- Hong et al. (2023): GC-MS-O of osmanthus — β-ionone is the dominant character compound
- Guo et al. (2024): osmanthus absolute composite OAV = 1,371,872 floral
- Fraterworks: Methylionones are softer, more iris-like than ionones

### Key Material Data (Verified)
- Tonkarome is 20% in TEC (not 10% in DPG)
- Methyl Ionone Pure VP = 0.4 Pa (was erroneously 0.01, fixed 2026-05-31)
- Osmanthus Absolute effective ODT = 0.5 ppb (composite, β-ionone weighted)
- Geraniol 10% in DPG: prepared for rose-accord dosing at pipeline-safe OAV
- Lavender HA = Lavender EO High Altitude
- cis-3-Hexenol NOT in inventory — use Parmavert instead
- Freesia HDI IS in inventory at line 84
- Petitgrain EO Paraguay IS in inventory at line 41
