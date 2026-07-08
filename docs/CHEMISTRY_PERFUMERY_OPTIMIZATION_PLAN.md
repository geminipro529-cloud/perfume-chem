# Whole-Program Chemistry and Perfumery Closure

Master audit of how the engine turns chemistry into perfumery behavior, what is now live in the runtime gates, what remains advisory, and where the real scientific data gaps still are.

**Date:** 2026-04-28  
**Verification run:** 2026-04-28 — `pytest -q tests/test_science_audit.py tests/test_ifra_safety.py tests/test_pipeline_formula_state.py tests/test_pipeline_gates.py tests/test_pipeline_part5.py tests/test_pipeline_robustness.py tests/test_gate_aware_optimizer.py` → `28 passed`

---

## Summary

### What is now implemented in the live runtime

- `engine/science_audit.py` no longer reports false 0% coverage from the wrong YAML shape. It now uses the real data-spine loader and `Material.completeness()`.
- `engine/pipeline/formula_state.py` now carries chemistry metadata per material:
  - `functional_groups`
  - `hsp`
  - `hsp_source`
- HSP lookup is now:
  1. data spine first
  2. `engine.science_data` fallback for the hand-curated core set
- `engine/pipeline/gates.py` now includes two new runtime chemistry gates:
  - `chemistry_stability`
  - `phase_compatibility`
- `engine/ifra_safety.py` still uses the stored IFRA Cat 4 finished-product limits as the formal pass/fail comparator, but now also reports:
  - `fraction_into_skin`
  - `effective_exposure_index`
  - uptake-weighted sensitizer diagnostics
- `engine/optimizer/gate_aware.py` now returns chemistry-specific block/rerun actions instead of collapsing these failures into the generic missing-data bucket.

### Previously closed and still valid

- VP-unit regression in `engine/diffusion_model.py` is fixed.
- Skin-temperature VP scaling now uses the shared thermodynamic path.
- Profile-level gamma plumbing into diffusion is live.
- ODT air vs ethanol usage has been re-audited and is correct in runtime consumers.
- Hansen-based skin substantivity fallback is already implemented in `engine/skin_interaction.py`.

### What is still not fully closed

- Full dynamic gamma unification is not done. The gate-aware pipeline computes mixture-specific gamma from HSP, but the legacy scorer still consumes profile-level `activity_coef`.
- IFRA is still legally evaluated against stored product-level limits, not a standards-grade dermal-dose model. The new dermal overlay is advisory, not the legal comparator.
- OR profiles, microbiome, genetics, and finite-film evaporation remain advisory or research-grade layers, not default hard gates.
- The structured data spine is still sparse enough that several science layers run on heuristics, not measured literature coverage.

### Thermodynamic posture

The runtime thermodynamic chain is internally coherent enough for release gating:

- Clausius-Clapeyron skin correction remains `~1.588x` from 298.15 K to 305.15 K for the default `ΔHvap = 50 kJ/mol`.
- Antoine-backed VP calculation is still the preferred route when coefficients exist.
- HSP-based gamma and phase checks are usable as a heuristic screening layer, but not yet a full measured-mixture thermodynamic system.

---

## 1. Live Runtime Blockers and Constraints

| Area | Runtime Status | What Changed | Remaining Constraint |
|---|---|---|---|
| Science audit coverage | ✅ Fixed | Loader-backed completeness replaced schema-broken YAML probing | Contract is accurate now, but the underlying coverage is still poor |
| Chemistry stability | ✅ New hard gate | Schiff-base, maturation shelf life, oxidation burden, photolability | Still heuristic because functional-group coverage is inferred, not curated in the spine |
| Phase compatibility | ✅ New gate | HSP-based RED screening is live | Hard fail only when HSP support is strong enough; partial coverage degrades to WARN |
| IFRA safety | ✅ Enriched | Dermal uptake overlay added | Formal legal comparator is still finished-product `%` vs stored IFRA limit |
| Gamma / headspace unification | ⚠ Partial | Gate-aware pipeline uses mixture gamma; legacy scorer still uses profile gamma | Not yet one single source of truth |
| Legacy vs gate-aware paths | ⚠ Mixed | Gate-aware runtime is now chemically stronger | Legacy analyzers still exist and should eventually be retired or migrated |

### Most important practical reading

- The engine is now much better at blocking formulas that are chemically unstable even when they look numerically attractive.
- The engine is now better at distinguishing a real phase-separation risk from a merely under-characterized formula.
- The engine still cannot pretend to have rich literature coverage when the spine is mostly empty for Antoine, HSP, OR, and IFRA fields.

---

## 2. New Runtime Chemistry Gates

### `chemistry_stability`

This gate now combines four chemistry checks:

1. **Schiff-base risk**
   - `FAIL` when aldehydes exceed `1%` of active formula and amines exceed `0.5%`.
   - Functional groups come from runtime chemistry metadata, using existing name/SAR heuristics when the registry is empty.

2. **Maturation shelf life**
   - Uses `predict_shelf_life_days()` at `295 K`, `threshold_pct = 10`, `bht_protected = False`.
   - `FAIL` below `180 days`
   - `WARN` at `180-365 days`

3. **Oxidation burden**
   - Uses `engine.science_data` stability classes.
   - `WARN` when oxidation-prone plus photolabile materials exceed `10%` of active mass.
   - Escalates to `FAIL` in `commercial_mode` above `20%`.

4. **Photolability**
   - Uses the existing stability tables plus `photolysis_remaining_fraction()` for diagnostics.

**Representative verification**

- `Reactive Jasmine` formula:
  - Aldehyde C12 MNA `33.3%` active
  - Indole `16.7%` active
  - predicted shelf life `7 days`
  - gate result: `FAIL`

**Perfumery reading**

- This is the right behavior.
- A formula can be beautiful on blotter and still be chemically unserious if it is building a jasmine/aldehydic effect through uncontrolled aldehyde plus amine contact.
- This gate now catches that before the optimizer gets to call it "good."

### `phase_compatibility`

This gate uses HSP-based `RED` screening through `micro_phase_risk()`.

**Runtime rules**

- Runs on active-mass weighting.
- Uses HSP from:
  1. data spine
  2. `engine.science_data` fallback
- If HSP coverage is too thin, the gate warns instead of pretending precision.

**Important implementation detail**

- The gate only hard-fails when HSP support is strong enough to justify it:
  - `>= 80%` of active mass covered
  - `>= 4` HSP-covered materials
- Otherwise, even strong RED excursions stay at `WARN`.

This is stricter than the old codebase and more honest than a naive hard fail on three fallback rows.

**Representative verification**

- `Phase Clash` formula:
  - Vanillin `30%`
  - D-Limonene `30%`
  - Galaxolide `30%`
  - Hedione `10%`
  - HSP coverage `100%`
  - Vanillin `RED = 1.83`
  - gate result: `FAIL`

**Perfumery reading**

- This is not saying "the perfume smells bad."
- It is saying "the solvent/matrix compatibility picture is bad enough that bloom, haze, or phase behavior is no longer a theoretical edge case."
- That is exactly what a runtime gate should do.

### `safety_ifra_allergen` dermal overlay

The legal gate semantics are intentionally unchanged:

- formal IFRA pass/fail still compares finished-product `%` to `IFRA_CAT4_LIMITS`
- commercial headroom logic is unchanged

What changed is the chemistry visibility:

- each material now reports:
  - `logp`
  - `mw_g_mol`
  - `fraction_into_skin`
  - `effective_exposure_index`
  - depot and sebum diagnostics
- uptake-weighted sensitizers are now surfaced explicitly

**Representative verification**

- `Hydroxycitronellal` at `1.3333%` finished product:
  - still a formal IFRA violation against the stored `1.0%` limit
  - `fraction_into_skin = 0.455865`
  - `effective_exposure_index = 0.607821`

**Perfumery reading**

- This is the right compromise for now.
- The gate still speaks legal compliance in the language the repo already uses.
- But it now also tells you which sensitizer load is likely to matter more on skin, instead of pretending all `% in product` comparisons are equally informative.

---

## 3. Dormant or Advisory Science Layers

These are real science modules in the repo, but they are not yet default hard gates.

| Layer | Current State | Why It Is Not a Default Blocker Yet | Next Step |
|---|---|---|---|
| Full dynamic gamma unification | Partial | Gate-aware state computes mixture gamma, legacy scorer still uses profile gamma | Move diffusion/scoring to the gate-aware thermodynamic state as the single source |
| OR profile vectors | Not done | Current OR family is single-valued and data coverage is 0% | Replace family bins with sparse receptor vectors for the most-used materials |
| Microbiome | Dormant | No user-specific wear context; default hard gating would be fake precision | Keep advisory until wearer-context inputs exist |
| OR genetics / anosmia | Advisory only | Population-average logic exists, but not integrated into release gates | Expose as alternate-perspective scoring, not default blocker |
| Finite-film evaporation | Not done | Current drydown remains heuristic | Track as a research-grade transport project |
| Legacy analysis path | Still present | Some analyzers remain outside the gate-aware chain | Migrate or deprecate legacy callers |

### Practical interpretation

- These are not "missing imports."
- They are unresolved modeling choices or data-coverage limits.
- The correct posture is to document them clearly and not over-claim scientific closure.

---

## 4. Real Data Coverage

`engine.science_audit` now reports real schema-aware coverage from the live data spine.

| Field | Coverage % |
|---|---:|
| MW | 10.6 |
| logP | 8.7 |
| VP @ 25 C | 8.6 |
| Antoine | 0.0 |
| dHvap | 0.0 |
| HSP | 0.0 |
| ODT air | 0.1 |
| OR targets | 0.0 |
| IFRA | 0.0 |
| Hedonic | 9.8 |
| TRP | 3.7 |
| SMILES | 0.0 |
| CAS | 0.0 |

### Additional loader-level fact

- Supplier coverage is `82.0%`.
- This does not appear in the `science_audit.json` contract because the contract keys were intentionally kept stable, but the underlying data-spine completeness shows it clearly.

### Interpretation

- The runtime chemistry is now structurally better than the old audit implied.
- The data spine is still materially underfilled.
- In other words:
  - the program now asks the right chemistry questions more often
  - but it still cannot answer all of them from measured literature data

The biggest missing domains remain:

- Antoine constants
- dHvap
- measured HSP coverage
- OR targets
- IFRA values in the structured spine
- CAS / SMILES identity completeness

---

## 5. Perfumer Interpretation Appendix

### What the engine now catches well

- **Reactive prettiness**
  - formulas that smell good in the abstract but are chemically likely to yellow, drift, or self-transform
- **False cleanliness from sparse math**
  - the phase gate now distinguishes a real incompatibility from a merely under-modeled formula
- **Citrus freshness with hidden liability**
  - oxidation-heavy formulas now surface their burden explicitly, especially in commercial mode
- **Legal safety without skin blindness**
  - IFRA remains legally readable, but the dermal overlay tells a more truthful wearer story

### What still needs a perfumer, not just a model

- Whether a WARN-level phase tension is artistically acceptable in a trial accord
- Whether oxidation burden is acceptable for a short-life, fresh-top concept
- Whether a dermal-overlay hotspot is tolerable for an exploratory mod versus a release candidate
- Whether the legacy scorer's profile gamma is still biasing aesthetic ranking compared with the gate-aware thermodynamic path

### Bottom line from a perfumer's point of view

- The program is now much harder to fool with chemically glamorous but operationally unserious formulas.
- It is still not a replacement for a perfumer's judgment on style, elegance, or wear beauty.
- The best reading is:
  - `FAIL` now means a more physically real problem than before
  - `WARN` still deserves a human nose and process judgment
  - `PASS` means "coherent under current science coverage," not "chemically complete"

---

## Current Priority Order

### Immediate

1. Unify the legacy scorer with the gate-aware mixture gamma path.
2. Backfill structured HSP, IFRA, Antoine, and dHvap data.
3. Decide whether dermal exposure should ever become a formal safety comparator instead of an overlay.

### Next wave

1. Upgrade OR-family logic to sparse receptor profiles.
2. Move genetics and microbiome into optional perspective scoring.
3. Retire or migrate the remaining legacy analysis path.

### Research grade

1. Finite-film evaporation with coupled skin sink.
2. Better measured maturation kinetics by material class.
3. Material-pair-specific psychophysical suppression and adaptation.
