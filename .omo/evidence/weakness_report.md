# Systemic Weakness Report — Plan v5 Audit

## Summary
1,364 truths accumulated across 9 categories from a target of 5,500 (24%). The audit reveals 5 systemic weaknesses, each with a root cause and remediation path.

---

## 1. Hedonic Data Desert (CRITICAL)
**Impact**: 89% of materials lack hedonic valence data. The pipeline cannot assess pleasantness, consumer preference, or predict hedonic drift — essential for commercial formulation.

**Root cause**: Only 135 of 1,251 YAML materials have hedonic_valence populated. 0 profiles in ingredient_intelligence.py carry explicit hedonic data. The `_HEDONIC_OVERRIDES` dict is empty.

**Recommended fix** (Effort: HIGH):
- Populate `_HEDONIC_OVERRIDES` from published hedonic studies (RIFM consumer panel data, GC-O hedonic assessments, Dravnieks atlas)
- Add PubChem `pubchem_get_bioactivity()` hedonic-adjacent data (e.g., "pleasant" descriptors)
- Minimum target: 50 materials covered for MVP formulation

**If unfixed**: The formulation engine cannot distinguish between equally OAV-strong but hedocially opposite materials. Formulations will pass OAV gates but smell unpleasant.

---

## 2. VP Source Vacuum (CRITICAL)
**Impact**: All 264 materials have `vp_source: UNKNOWN`. The pipeline cannot verify VP data provenance — a release-blocker for production-grade formulas. The A.7 check ("NIST/EPI/PubChem_exp required for production-release") has zero coverage.

**Root cause**: The vp_source field was added structurally (all 26 YAML files populated with `vp_source: null`) but never populated with actual source annotations.

**Recommended fix** (Effort: HIGH):
- Tier 1: Cross-reference VPs in `data/materials/*.yaml` against NIST Chemistry WebBook (for pure compounds with well-characterized VP)
- Tier 2: Run EPI Suite estimation for materials without experimental data
- Tier 3: Flag PubChem experimental VP entries where available
- Automation: `scripts/audit_vp_sources.py` that loops over YAML + PubChem API

**If unfixed**: Production release gate will HARD BLOCK on A.7. All formulas become draft-only.

---

## 3. Biochemical/Neurotransmitter Near-Zero Coverage (HIGH)
**Impact**: Only 10 materials have verified biochemical/neurotransmitter data (extracted from AGENTS.md references). The `_PSYCHOACTIVE_EFFECTS` dict in neuroscience.py appears empty or inaccessible. Receptor data is sparse (33 materials with mappings, mostly from PubChem).

**Root cause**: The neuroscience module was scaffolded but never populated with systematic PubChem/PubMed data. The deep delegation agents were cancelled at the PubChem API call stage due to tool limits.

**Recommended fix** (Effort: MEDIUM):
- Populate `_PSYCHOACTIVE_EFFECTS` with known material-receptor pairs (minimum: linalool→GABA-A, limonene→5-HT/DA, eugenol→TRPV1, menthol→TRPM8, β-caryophyllene→CB2)
- Batch PubChem search for remaining inventory materials using saved CID list
- Add `scripts/populate_receptor_data.py` that does this at build time

**If unfixed**: The receptor saturation gate and hedonic neuroscience gate will return NO_DATA for most materials, making bioactivity assessment impossible.

---

## 4. EU Allergen Incompleteness (MEDIUM)
**Impact**: Only 53 of 82 required EU 2023/1545 allergens are in the database. 29 allergens are missing — non-compliant for EU-market formulations.

**Root cause**: The allergen database was built from the pre-2023 26-allergen framework (Reg 1223/2009 Annex III) and partially extended. The 2023/1545 expansion to 82 allergens was not fully implemented.

**Recommended fix** (Effort: MEDIUM):
- Complete the `eu_2023_1545_allergens.json` file with full 82-allergen list
- Add CAS numbers and typical occurrence data for each
- Cross-reference with `data/materials/*.yaml` to flag materials containing these allergens

**If unfixed**: `_gate_eu_allergen_declaration` will miss declaration requirements. PI-labeling may be non-compliant for EU market.

---

## 5. Batch Testing Pipeline Gap (MEDIUM)
**Impact**: The batch gate script runs but most formulas are blocked by INVENTORY_MISSING preflight — materials in formulas don't match inventory.txt names. Only 5 of 100+ formulas tested (all blocked).

**Root cause**: Formula files use varied naming conventions (e.g., "Romandolide" vs "Romandolide (10%)", "EB" abbreviation). The preflight guard is working correctly but reveals a data normalization gap. Formulas written before the preflight guard existed.

**Recommended fix** (Effort: MEDIUM):
- Add alias normalization to preflight guard (use `name_utils._ALIASES`)
- Run `scripts/evaluate_formula.py` on all formula files to identify normalization mismatches
- Add a `--skip-prefight` flag for historical audit runs

**If unfixed**: Cannot batch-validate existing formulas. New formulas must be written against current inventory.

---

## Category-Specific Truth Scorecard

| Category | Count | Target | Assessment |
|----------|-------|--------|------------|
| material_perfume_effect | 500 | 1,000 | Good — all profiles covered |
| odt_sources | 315 | 500 | Good — major materials sourced |
| data_consistency | 243 | 500 | Good — 4-source cross-ref complete |
| hedonic_valence | 135 | 500 | Weak — 89% missing |
| eo_absolute_composition | 61 | 500 | Fair — 54 naturals decomposed |
| ifra_allergen | 53 | 500 | Weak — 29 EU allergens missing |
| receptor_mapping | 33 | 500 | Weak — only PubChem-verified |
| phototoxicity | 14 | 500 | Weak — coverage adequate for known oils |
| biochem_neuro | 10 | 500 | Critical — near-zero |
| vp_source | 0 | 500 | Critical — all UNKNOWN |

---

## Remediation Priority
1. **VP Source** — blocks production release (A.7)
2. **Hedonic Data** — blocks quality formulation
3. **EU Allergens** — blocks EU-market compliance
4. **Biochem/Neuro** — blocks bioactivity assessment
5. **Batch Testing** — blocks validation pipeline
