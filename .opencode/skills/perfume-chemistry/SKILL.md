# Perfume Chemistry — Formulation Skill

**MUST USE for ANY formula creation, modification, gating, or analysis.** This skill encodes the non-negotiable measurement, dilution, and calculation rules of the perfume-chem workbench.

---

## RULE 0: Read Inventory Before Formulating

Read `inventory.txt` in full before writing or modifying any formula. Materials have specific dilutions (1%, 10%, 20%, 30%, 50%, 80%) that affect dosing. Never rely on memory. Never assume availability.

## RULE 1: ppm / ODT / OAV — All Calculations

- **Concentration** in ppm (w/w in concentrate)
- **ODT** in ppm (ethanol solution) or ppb (air)
- **OAV = concentration_ppm / ODT_ppm**
- OAV < 1 = below threshold, not perceptible
- OAV 1–5 = perceptible but weak
- OAV 5–50 = clearly perceptible
- OAV > 50 = dominant

## RULE 2: Measurement Integrity (NON-NEGOTIABLE)

### Store Both Values
Every material entry MUST track:
- **Supplied amount** (what you measured: raw µL of stock solution)
- **Stock concentration** (dilution % from inventory)
- **Active amount** (calculated: supplied × dilution%)
- **Concentration in formula** (ppm w/w in concentrate)

### Never Silently Treat Dilution as Neat
A material at 10% dilution dosed at 100 µL = **10 µL active**. The dilution % is not optional. If you write "100 µL" for a 10% material without noting "10 µL active", you are wrong.

### Distinguish Measurement Types
- **Mass (g, mg)**: measured on a balance, exact within uncertainty
- **Volume (µL, mL)**: measured by pipette or graduated cylinder
- **Estimated volume**: calculated from mass ÷ density, labeled as estimate
- Never present estimated volume as measured volume

### Density Rule
**Never convert mass to volume without a recorded density.** If density is unknown, state "volume unknown, mass = X g". Do not assume 1.0 g/mL.

### Preserve Original Measurements
Always show the raw measurement AND the calculated result separately:
```
Raw dose: 300 µL of Ambrox Super 30% (= 90 µL active)
```
Never show only the derived value.

### Decimal Arithmetic for Totals
Use Python's `Decimal` or integer arithmetic (µL as integers) for formula totals. Binary floating-point (JavaScript `0.1 + 0.2`) produces rounding errors in percentage sums. Formula totals must sum to exactly 100.0%.

### Track Solvent Contribution
Every dilution contributes solvent (DPG, TEC, IPM, ethanol) to the concentrate. Track total solvent mass from dilutions. It affects:
- Concentrate total volume
- Active material % of concentrate
- Evaporation curve (solvent acts as low-volatility fixative)

## RULE 3: Unit System

Supported units in formulas:
| Unit | Use for |
|---|---|
| **µL** (microlitres) | Concentrate material dosing (primary unit) |
| **mL** (millilitres) | Ethanol, total bottle volume |
| **g** (grams) | Mass-based measurements (crystalline solids) |
| **mg** (milligrams) | Trace materials, crystalline solids |
| **%** (percent) | Concentrate composition, dilution ratios |
| **ppm** (parts per million) | Headspace concentration, IFRA limits |
| **ppb** (parts per billion) | ODT air values |

Always specify units. Never write a bare number.

## RULE 4: Material Identity

Each material must record:
- **Trade name** (as in inventory.txt)
- **CAS number** (from `data/materials/<LETTER>.yaml`)
- **Supplier** (when known)
- **Synonym/alias** (from `engine/name_utils.py` `_ALIASES`)
- **Stock dilution** (from inventory.txt)

Chemical identifiers are NOT interchangeable. "Hedione" ≠ "Hedione HC" — different CAS, different ODT.

## RULE 5: Safety Data (IFRA)

- IFRA limits are **versioned source data** in `engine/safety/ifra_limits.py`
- Never quote an IFRA limit from memory — always look it up
- Every IFRA claim needs: **provenance** (IFRA Standard, Annex, category), **effective date**, **restriction level**
- A material at 0.01% of concentrate ≠ "IFRA compliant" — must check specific IFRA category limit
- EU Allergen Annex III: 26 mandatory allergens, SCCS proposing 82+

## RULE 6: Formula Immutability

- Once a formula is **gated** (run through `formula_release_gate.py`), the version is immutable
- Modifications create a **new version** (v1 → v2) with dated changelog
- Never overwrite a gated formula file — create `Formula_Name_v2.md`
- The pipeline JSON output is the **canonical record** of the gated state

## RULE 7: Scaling and Rounding Tests

Before scaling any formula:
1. Verify the original at its batch size sums to 100%
2. Scale by exact ratio (not approximate)
3. After scaling, verify: every material × scale factor = expected, total = target
4. Round to pipette resolution (typically 5 µL increments for 10 µL pipette)
5. Re-verify total after rounding
6. Flag any material that rounds to zero at the new scale

**Test with hand-calculated examples before trusting automated scaling.**

## RULE 8: Formula Structure (Output Format)

All formulas must follow this structure:
```
## Formula: [Name] — [Concentration] [Batch Size]

| # | Ingredient | Dilution | Amount (µL) | Active (µL) | % of Concentrate |
|---|-----------|----------|-------------|-------------|------------------|
| 1 | Material A | neat     | 300         | 300         | 5.00%            |

**Concentrate total:** X,XXX µL (X.XX mL)
**Active total:** X,XXX µL
**Ethanol:** X.XX mL
**Final volume:** XX.00 mL
**Concentration:** XX%
```

Section headers (Top / Heart / Base) must use bold separator rows, not material entries.

## RULE 9: Accord Architecture

Before listing materials, state:
1. **Fragrance family** and subfamily
2. **Character** — what this smells like in perfumer vocabulary
3. **Architecture** — top-to-base structure, key accords
4. **Chemical rationale** — why these materials interact the way they do

Every material choice must answer: "Why THIS material and not the 3–8 alternatives in inventory?"

## RULE 10: Pipeline Verification

After any formula change:
1. Run `python scripts/formula_release_gate.py --formula-file <path> --expected-concentrate-ul <ul> --brief <family> --json`
2. Run `python scripts/format_pipeline_analysis.py --input output.json`
3. Present OAV headspace table BEFORE discussing gate outcomes
4. Check: any OAV < 1 for character/signature materials? Any IFRA edges? Any duplicate ODT entries?
5. Append analysis to formula file under `## Pipeline Analysis`

---

## Quick Reference: Key File Locations

| Need | Path |
|---|---|
| Inventory (stock, dilution) | `inventory.txt` |
| Material physical data | `data/materials/<LETTER>.yaml` |
| ODT values | `engine/odor_thresholds.py` |
| Material profiles (note, role, VP) | `engine/ingredient_intelligence.py` |
| Name aliases | `engine/name_utils.py` |
| Natural composite OAV | `engine/pipeline/natural_absolute_decomposition.py` |
| IFRA limits | `engine/safety/ifra_limits.py` |
| Formula state + OAV | `engine/pipeline/formula_state.py` |
| Release gate CLI | `scripts/formula_release_gate.py` |
| Analysis formatter | `scripts/format_pipeline_analysis.py` |
| Fragrance families | `docs/fragrance_families_reference.md` |

## Quick Reference: Common Pipetting Errors

| Error | Consequence | Prevention |
|---|---|---|
| Treating 10% dilution as neat | 10× overdose | Always multiply by dilution % |
| Assuming density = 1.0 | Volume error up to 20% | Look up or state "unknown" |
| Rounding before totaling | Sum ≠ 100% | Round after sum, not before |
| Mixing µL and mL in same column | 1000× error | Use µL throughout concentrate |
| Forgetting solvent from dilutions | Understated concentrate volume | Track DPG/TEC/IPM contribution |

## Activation

This skill activates for: formula creation, formula modification, formula gating, OAV analysis, dilution calculations, inventory checks, material dosing, pipeline runs, and any question about perfume formulation in this repository.
