# aventus-chypre-fruity - Work Plan

## TL;DR (For humans)

**What you'll get:** A reformulated Creed Aventus-inspired perfume at 30mL EdP 20% with ~47 materials — corrected from the existing Pineapple Chypre Luxe reconstruction using published Aventus formula data (Olfactorian, Jamal's Substack, GC-MS consensus). Substitutes depleted Hydroxycitronellal. Runs through the pipeline for OAV headspace, temporal evolution, and IFRA analysis.

**Why this approach:** The existing 61-material formula has the right architecture but wrong proportions (pineapple 27× too large, Ambrox 8× too low, Hedione too low) and uses a depleted material. Adapting it is faster than starting from scratch; the corrections are well-supported by published Aventus analysis.

**What it will NOT do:** NOT a 1:1 clone (Helvetolide, Cassis Base 345, Paradisone, Lyral unavailable). NOT 61 materials. NOT 30% Extrait. NOT a new family archetype.

**Effort:** Medium
**Risk:** Medium — proportion rebalancing constrained by 6,000 µL budget and Ambrox 33% dilution stock. Damascone Beta requires IFRA-compliant reduction (60→12 µL). Subagents (momus/explore/librarian) may fail — plan includes inline QA as fallback.
**Decisions to sanity-check:** (1) Pineapple accord at ~2% vs. original's 0.2% — bold but our materials differ. (2) Ambrox boost to ~5% vs. original's 10% — constrained by 33% dilution stock. (3) Luxury accents as optional section.

Your next move: approve, then I write the formula file and gate it through the pipeline. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Medium risk. Adapt existing Aventus formula → 30mL EdP 20%, ~40 materials, correct proportions, substitute depleted material, pipeline gate with --brief generic, present OAV analysis, iterate.

## Scope

### Must have
- Reformulated formula file at `formulas/Aventus_Chypre_Fruity_30mL_EdP.md`
- ~40 core materials (not 61) — closer to original Aventus transparency
- 30mL EdP 20% (6,000 µL concentrate + 24 mL ethanol)
- Hydroxycitronellal substituted (Mayol + Farnesol)
- Hedione HC boosted toward 20%+ of concentrate (original: 23%)
- Ambrox boosted toward 5%+ active (original: ~10%)
- Pineapple accord reduced to ~2% (original: 0.2%, but our materials differ)
- Woods trimmed from 11 to 5-6 (original Aventus has simple woody base)
- Luxury accents in separate optional section
- Pipeline gated with --brief generic
- Full OAV analysis presented (headspace table, temporal evolution, perfumer analysis)

### Must NOT have (guardrails, anti-slop, scope boundaries)
- NO materials outside inventory.txt
- NO depleted materials (verify Hydroxycitronellal, Petitgrain EO, Ambrox Super 30%)
- NO 61-material formula
- NO 30% Extrait concentration
- NO new pipeline scripts or engine code
- NO new family archetype creation
- NO materials at wrong dilutions (must match inventory.txt)
- NO Damascone Beta exceeding 12 µL of 10% stock (IFRA Cat4 0.02% active limit)

## Verification strategy
> Zero human intervention — all verification is agent-executed.
- **Test decision**: tests-after (pipeline IS the test; we verify pipeline output)
- **Evidence**: .omo/evidence/task-<N>-aventus-chypre-fruity.<ext>

Each task verified by:
- Formula file: inventory guard script confirms all materials in stock
- Pipeline gate: exit code 0, JSON output produced
- Analysis: format_pipeline_analysis.py runs without error
- OAV: no material with OAV < 1 for character-carrying roles

## Execution strategy

### Wave 1 — Formula creation (sequential, 1 task)
Build the reformulated formula file from the adapted existing formula.
- Task 1: Write the formula file

### Wave 2 — Verification (parallel, 2 tasks)
- Task 2: Inventory guard — verify all materials
- Task 3: Pipeline gate — run formula_release_gate.py

### Wave 3 — Analysis (sequential, depends on Wave 2)
- Task 4: Format and present pipeline analysis
- Task 5: Perfumer analysis and iteration plan

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
|------|-----------|--------|---------------------|
| T1 | — | T2, T3 | — |
| T2 | T1 | T4 | T3 |
| T3 | T1 | T4 | T2 |
| T4 | T2, T3 | T5 | — |
| T5 | T4 | — | — |

## Todos

### Wave 1: Formula Creation

- [ ] 1. Write reformulated Aventus formula file
  **What to do:** Create `formulas/Aventus_Chypre_Fruity_30mL_EdP.md` with the adapted formula. Must contain:
  - Header with name, date, concentration, batch size
  - Design philosophy section explaining deviations from original
  - 7 accord sections in established format (Top/Heart/Base with tables)
  - Correct inventory names (Cedrat FCF oil Sicilian, not "Cedrat FCF Sicilian")
  - Correct dilutions from inventory.txt
  - ~40 core materials total
  - Luxury accents in optional flagged section
  - Mixing protocol
  - Adjustment knobs
  
  **Must NOT do:**
  - Use depleted materials (Hydroxycitronellal → Mayol + Farnesol)
  - Use Ambrox Super 30% (use Ambrox Super ~33% in DEP:EtOH)
  - Use Petitgrain EO (use Petitgrain EO Paraguay)
  - Exceed 6,000 µL total concentrate
  - Include wrong dilution (e.g., Dynascone is 10%, not neat)
  
  **Key proportion targets (from Aventus literature):**
  | Material | Original Aventus | Target for this formula | Rationale |
  |----------|-----------------|------------------------|-----------|
  | Hedione HC | 23% | 18-22% | Boost from current 14%; constrained by 6,000 µL budget |
  | Iso E Super | 13% | 12-15% | Near original |
  | Musks (total active) | Helvetolide 14% + Ambrettolide 2% | 11-14% (5-musk chord) | Keep existing musk architecture |
  | Ambrox (active) | ~10% | 3-5% | Boost from 1.2%; **severely constrained by 33% dilution stock** — 5% active = 909 µL stock (15% of budget). Original 10% is unachievable without neat Ambrox. Document as inventory limitation. |
  | Bergamot | ~30% | 8-12% | Scaled for 20% EdP (vs. original ~15-20% EdP) |
  | Pineapple accord | 0.2% | 1.5-2.5% | Reduced from 5.5%; our materials differ from originals |
  | Chypre spine | ~10% | 8-12% | Patchouli + Evernyl + Oakmoss + Labdanum |
  | Woods | ~10% | 8-12% | 5-6 materials (was 11) |

  **Materials to KEEP (core):**
  - Diffusion: Hedione HC, Iso E Super, Habanolide, Romandolide, Ethylene Brassylate, Cashmeran, Ambrettolide 10%, Ambrox Super 33%
  - Pineapple: Ethyl 2-Methylbutyrate 0.1%, Allyl Amyl Glycolate 10%, Dynascone 10%, Undecavertol 1%, Melonal, Ethyl Maltol 10%, Triplal, Ylang Extra, Damascone Beta 10%, D-Limonene
  - **⚠️ Damascone Beta IFRA**: limit 0.02% active in concentrate (Category 4). 0.02% of 6,000 µL = 1.2 µL active = **12 µL max of 10% stock**. Existing formula uses 60 µL → MUST reduce to ≤12 µL. Document as IFRA constraint.
  - **⚠️ Ylang Extra ≠ Cassis Base 345**: Original Aventus uses Cassis Base 345 for blackcurrant-tart fruit. Our Ylang Extra substitution provides banana-floral-tropical fruit instead. The fruit profile will read more tropical-banana than blackcurrant-tart. Document this character shift. Cassis Base 345B (in inventory) could supplement but is an accord base, not the Firmenich captive.
  - **⚠️ No Coranol/DHMOL equivalent**: Original Aventus has a fresh-linalool transparency component (Coranol/DHMOL-like). Our formula has Linalool but no DHMOL (intentional — avoids laundry character). Document as intentional creative choice.
  - Citrus-Spice: Bergamot FCF oil Sicilian, Linalyl Acetate, Linalool, Petitgrain EO Paraguay, Black Pepper EO, Cardamom EO, Juniper Berry EO, Orange Peel EO, Clary Sage EO
  - Smoky Heart: Patchouli EO, Nagarmortha Oil, Birch Tar Rectified, Guaiacol 10%, IBQ 10%, Suederal 10%, Labdanum Resinoid 10%, Evernyl, Oakmoss Absolute 10%
  - Woods: Cedarwood oil Virginia, Vertofix, Clearwood, Bacdanol, Vetiver EO (India), Javanol
  - Structural: Benzyl Salicylate, Benzyl Benzoate, Coumarin 20%
  - Muguet substitute: Mayol (30-50 µL, muguet transparency) + Farnesol (10-18 µL, lily fixative, IFRA-restricted check). Total ~40-68 µL replacing depleted Hydroxycitronellal's 36 µL. If Farnesol IFRA concerns arise, use Mayol alone at 40-60 µL.

  **Materials to MOVE to optional luxury section:**
  - Ethyl Safranate, Heliotropal, Carrot Seed EO, Alpha Irone 30%, Rose de Mai Absolute 10%, Jasmine Sambac 10%, Rhodinol ex Citronella, Rosemary EO
  - **RETAINED in core** (structural green notes, not luxury): Galbanum EO, Beta-Pinene, Cedrat FCF oil Sicilian — these are Aventus green-character materials per GCMS/Olfactorian analysis, not decorative accents.

  **References:**
  - Base formula: formulas/Pineapple_Chypre_Luxe_30mL_Extrait.md (full file)
  - Inventory: inventory.txt (all lines — verify every material)
  - Aventus data: Olfactorian formula 435, Jamal's Substack, GC-MS consensus
  - Formula format convention: formulas/Osmanthus_Bois_DHP_30mL_EdP.md (for EdP format reference)

  **Acceptance criteria:**
  - File exists at formulas/Aventus_Chypre_Fruity_30mL_EdP.md
  - 7 accord sections present
  - Concentrate total = 6,000 µL (± 50 µL)
  - No depleted materials in core formula
  - All material names match inventory.txt
  - All dilutions match inventory.txt
  - Luxury accents in separate section marked "(OPTIONAL LUXURY LAYER)"
  - IFRA-conscious: Oakmoss ≤0.1% active, Birch Tar ≤0.2%, **Damascone Beta ≤12 µL of 10% stock** (= 0.02% active in concentrate, IFRA Cat4 limit)
  - Material count: ~47 core materials (was claimed ~40; actual count after retaining structural green notes is 47)

  **QA scenarios:**
  - Happy: Formula file parses correctly by pipeline parser → evidence: pipeline gate runs without parse errors
  - Failure: If a material name doesn't match inventory, inventory guard catches it → evidence: inventory guard output
  - **Evidence:** .omo/evidence/ta[REDACTED_PROVIDER_KEY].md

  **Commit:** Y | feat(formulas): add Aventus Chypre Fruity 30mL EdP formula

### Wave 2: Verification (parallel)

- [ ] 2. Inventory guard — verify all materials
  **What to do:** Run the inventory guard skill to verify every material in the new formula against inventory.txt. Check for:
  - Material exists in inventory
  - Correct dilution matches inventory
  - Material is not depleted
  - Material has complete data (ODT, profile, YAML)
  
  **Must NOT do:** Skip any material. Accept partial matches.
  
  **References:**
  - inventory.txt (full file)
  - engine/inventory_parser.py
  - Skill: /inventory-guard

  **Acceptance criteria:**
  - All core materials confirmed in stock
  - Depleted materials flagged (if any found — should be zero)
  - Dilution mismatches flagged (should be zero after correction)
  
  **QA scenarios:**
  - Happy: All materials found → inventory guard reports 0 issues
  - Failure: Missing material flagged → fix formula, re-run guard
  - **Evidence:** .omo/evidence/ta[REDACTED_PROVIDER_KEY].txt

  **Commit:** N (verification only)

- [ ] 3. Pipeline gate — run formula_release_gate.py
  **What to do:** Run the full pipeline gate on the new formula.
  ```bash
  python scripts/formula_release_gate.py \
      --formula-file formulas/Aventus_Chypre_Fruity_30mL_EdP.md \
      --expected-concentrate-ul 6000 \
      --brief generic \
      --json > output/aventus_chypre_fruity_gate.json
  ```
  
  **Must NOT do:** Use a mismatched archetype. Skip JSON output.
  
  **References:**
  - scripts/formula_release_gate.py (entry point)
  - engine/pipeline/gates.py (gate logic)
  - engine/pipeline/formula_state.py (OAV computation)

  **Acceptance criteria:**
  - Pipeline exits with code 0 (no crashes)
  - JSON output written to output/aventus_chypre_fruity_gate.json
  - Gate statuses extracted from JSON
  - No critical IFRA violations
  - OAV data present for all materials
  
  **QA scenarios:**
  - Happy: Pipeline completes, JSON produced, gates evaluated → evidence: exit code 0 + JSON file exists
  - Failure: Pipeline crashes on parse error → fix formula format, re-run
  - **Evidence:** output/aventus_chypre_fruity_gate.json

  **Commit:** N (output artifact)

### Wave 3: Analysis (sequential)

- [ ] 4. Format and present pipeline analysis
  **What to do:** Run the pipeline analysis script and present results.
  ```bash
  python scripts/format_pipeline_analysis.py --input output/aventus_chypre_fruity_gate.json
  ```
  
  Present in chat:
  1. OAV headspace table (| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | Vapor ppm | ODT ppm | OAV | Note |)
  2. Note distribution (T/H/B split)
  3. Temporal evolution (5 windows)
  4. Gate outcomes (IFRA, pyramid, OAV intelligence, **allergen declarations**)
  5. Full perfumer analysis (Character, Opening, Heart, Drydown, Sillage, Longevity, Balance, Flags)
  
  Append analysis to formula file under `## Pipeline Analysis` section.
  
  **Must NOT do:** Skip the chat presentation. Summarize or paraphrase analysis output.
  
  **References:**
  - scripts/format_pipeline_analysis.py
  - output/aventus_chypre_fruity_gate.json
  - AGENTS.md sections: "Required: always present the OAV headspace table", "Required: perfumer analysis format"
  - Skill: /pipeline-analysis

  **Acceptance criteria:**
  - Full OAV table presented in chat
  - Temporal evolution presented
  - Perfumer analysis (8 sections) presented verbatim
  - Analysis appended to formula file
  
  **QA scenarios:**
  - Happy: Analysis script runs, all sections produced → evidence: analysis output in chat + appended to formula file
  - Failure: Analysis script errors → check JSON validity, re-run
  - **Evidence:** .omo/evidence/ta[REDACTED_PROVIDER_KEY].md (analysis output)

  **Commit:** Y | docs(formulas): add pipeline analysis to Aventus Chypre Fruity

- [ ] 5. Perfumer analysis and iteration plan
  **What to do:** After reviewing pipeline output, produce:
  1. Assessment of how well the formula matches Aventus character
  2. Flag any OAV < 1 materials that carry character roles
  3. Flag IFRA edge cases
  4. Suggest specific dose adjustments for next iteration
  5. Compare against Aventus literature proportions
  
  **Must NOT do:** Change the fragrance family. Over-correct based on numbers alone (RULE 3: optimize for the name, not just numbers).
  
  **References:**
  - Aventus literature data (Olfactorian, Jamal's Substack)
  - Pipeline output from T4
  - RULE 3 (AGENTS.md): "Optimize for the name, not just the numbers"
  
  **Acceptance criteria:**
  - Specific dose adjustments proposed (not "maybe increase X")
  - Each adjustment justified with OAV data or Aventus reference
  - Priority ordered (what to fix first)
  
  **QA scenarios:**
  - Happy: Clear iteration plan with specific µL adjustments → evidence: iteration plan in chat
  - Failure: If formula is perfect on first pass (unlikely), document why no changes needed
  - **Evidence:** .omo/evidence/ta[REDACTED_PROVIDER_KEY].md

  **Commit:** N (analysis only)

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE.

- [ ] F1. Plan compliance audit — Verify all 5 tasks completed, all evidence files exist, all acceptance criteria met. Evidence: .omo/evidence/ directory listing matching all task IDs.
- [ ] F2. Formula integrity — Re-run inventory guard on final formula. Verify no regressions. Evidence: inventory guard output.
- [ ] F3. Pipeline re-gate — Re-run pipeline on final formula. Verify all gates still pass after any adjustments. Evidence: final gate JSON output.
- [ ] F4. Scope fidelity — Verify no depleted materials used, no materials outside inventory, concentrate = 6,000 µL ± 50, ~40 materials, luxury accents in optional section.

## Commit strategy
- T1: Single commit with formula file
- T4: Single commit appending analysis
- Others: No commits (verification/analysis artifacts only)
- Final: One squashed commit if iterating

## Success criteria
1. Formula file at `formulas/Aventus_Chypre_Fruity_30mL_EdP.md` with ~40 core materials
2. All materials in inventory, no depleted materials used
3. Pipeline gates pass (no critical IFRA violations, pyramid balanced)
4. OAV analysis presented with full perfumer analysis
5. Pineapple note perceptible but not dominant (OAV 5-50 range at opening)
6. Birch smoke perceptible at heart (OAV > 1)
7. Musk base persistent at drydown (OAV > 1 at 4h)
8. Clear iteration path identified from pipeline data
