---
name: formula-gate
description: Full perfume formula pipeline workflow — inventory check, gate analysis, formatting, and archival
---

## What I do
- Guide the agent through the complete formula release pipeline
- Verify inventory availability before any gate run
- Run `scripts/formula_release_gate.py` with correct parameters
- Run `scripts/format_pipeline_analysis.py` on the output
- Ensure analysis is appended to the formula markdown file

## When to use me
Use this when running any formula through the release gate pipeline, especially:
- New formula validation
- Formula iterations and reformulation
- Pre-commit quality checks

## Workflow (in order)

### Phase 1: Pre-flight checks
1. Read `inventory.txt` — confirm every material in the formula is in stock
2. Read `docs/fragrance_families_reference.md` — confirm the family exists
3. For each material in the formula, verify it has:
   - ODT data in `engine/odor_thresholds.py`
   - Physics data in `data/materials/<LETTER>.yaml`
   - Profile in `engine/ingredient_intelligence.py`
4. Check for duplicate ODT entries with grep on material name

### Phase 2: Run gates
```bash
python scripts/formula_release_gate.py \
    --formula-file <path> \
    --expected-concentrate-ul <ul> \
    --brief <family> \
    --json > output/pipeline_result.json
```

### Phase 3: Format analysis
```bash
python scripts/format_pipeline_analysis.py --input output/pipeline_result.json
```

### Phase 4: Present and archive
1. Present the full OAV headspace table (Material, Dil, Raw uL, Act uL, MW, MF%, VP Pa, gamma, Vapor ppm, ODT ppm, OAV, Note)
2. Present temporal evolution (opening, top, heart, late_heart, drydown)
3. Present note distribution (T/H/B split)
4. Present complete perfumer analysis (character, opening, heart, drydown, sillage, longevity, balance, flags)
5. Append the entire analysis under `## Pipeline Analysis` in the formula markdown file

### Critical rules
- NEVER skip inventory verification
- NEVER present gate results before the OAV headspace table
- NEVER summarize or paraphrase the analysis — present it verbatim
- ALWAYS flag materials with OAV < 1 if their role requires perceptibility

### Metadata Block Requirement

Every formula file MUST have a metadata block before gating. If missing, refuse to gate:

```markdown
**Date:** YYYY-MM-DD
**Claim mode:** named_reference | unclaimed
**Reference contract:** <contract_id> | none
**Reference scope:** architecture | quantitative_similarity | sensory_similarity
**Family archetype:** <key>
**Reference evidence:** <one-sentence>
**Official source:** <URL>
**Concentration:** <uL concentrate> + <uL ethanol>; <final volume>; <% v/v>
**Status:** Research control | Pending bench | Released
```

If metadata is missing, prompt: "Formula missing metadata block. Add explicit metadata or set `Reference claim: none`."

### Preflight Guard Checks

Before any gate run, the `pipeline_preflight_guard()` checks:
1. Metadata block present (hard block unless `unclaimed`)
2. Inventory stock contract OK (hard block)
3. Quantitative authority chain intact (hard block if claimed)
4. Chemical family compatibility for natural pairs (warn)
5. Thai retail bracket cost (warn)
6. EU 2023/1545 82-allergen compliance (warn — not hard block per user)

### Verification Protocol

After gating, Tier 2 GLM-5.2 max reviews:
- A.1 OAV physics (γ not 1.0, VP source)
- A.2 EU allergens + auto-substitution
- A.3 Phototoxicity + auto-substitution
- A.4 Receptor saturation
- A.5 Composite OAV for naturals
- A.6 Skin degradation (warn only for oakmoss)
- A.7 VP source hierarchy
- A.8 Sensomics disclaimer append

