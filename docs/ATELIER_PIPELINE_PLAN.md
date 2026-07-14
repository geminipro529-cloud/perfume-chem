# ATELIER Pipeline Plan — "Generating Amazing Perfume"

**Date:** 2026-06-20
**Status:** Locked, awaiting Phase 0
**Scope:** Adds a 7-stage generative pipeline on top of the existing analytical stack (23 gates, 10 scoring axes, 11 simulation phases, 214 formulas, 200+ profiled materials, 2,388 pairing rules, 1,211-material data spine).

> **⚠️ RULE 3: Optimize for the name, not just the numbers.** The name/concept/original brief of the perfume is the north star at every stage. Gates and optimizers are tools; the formula name is the north star.

## Why this plan exists

The current pipeline is **analytical, not generative** — it scores a finished formula but does not help you author a great one. To create "amazing" perfume, the pipeline must evolve from **gatekeeper to co-creator**.

## Locked defaults (8 open questions, all settled)

| # | Question | Default choice |
|---|---|---|
| 1 | IEC mode default | Auto-only; `--interactive` flag opts into human-in-loop |
| 2 | Edwards 14 vs current 4 | Map 14 sub-families → 4 main families; backward-compat |
| 3 | Novelty threshold | 0.3 default; configurable per call via `--novelty-min` |
| 4 | Creative spark mode | Opt-in `--creative` flag; default generates 1 candidate |
| 5 | PTD visualization | matplotlib (existing dep) |
| 6 | IEC optimizer | Sequential DE primary; CMA-ES auto-selected if DE stalls 3 gens |
| 7 | Brief input | Both free-text and `brief.json`; auto-convert one to the other |
| 8 | New module location | `engine/orchestration/` (NEW subpackage) |

## Locked 7-stage pipeline

```
[1] BRIEF ─► [2] METHODOLOGY ─► [3] FAMILY (Edwards 14 → 4 mapping)
        ─► [4] OAV PYRAMID + PTD preview (matplotlib)
        ─► [5] MATERIAL SELECTION (CAMD-style hard constraints)
        ─► [5b] NOVELTY CHECK (OAV-space distance vs 214 formulas)
        ─► [6] IEC (sequential DE; CMA-ES fallback; auto-only default)
        ─► [7] GATE + DIAGNOSIS + ARCHIVE (existing pipeline)
```

## Stage 1 — Brief Translation
**Inspired by:** Osmo Inspire, Sniff-AI (NER + classifier)
**Module:** `engine/orchestration/brief.py` (port from `future_modules/brief_translation.py`)

**Inputs:**
- `name` (string, required) — e.g. "Iris Cathedral", "Bleu Luxe Aldehyde"
- `brief_text` (string, optional) — free text
- `brief.json` (optional) — pre-existing structured brief
- `pinned_notes` (list, optional) — materials the user insists on

**Process:**
1. Parse `brief_text` with NER-lite (regex + keyword table) for known perfumery terms
2. Fallback to cosine similarity against our 200+ demo formulas
3. If ambiguous, ask 2-4 targeted questions
4. Output: `Brief` object with `material_anchors`, `oav_target_range`, `family_candidates`, `character_keywords`, `forbidden_materials`, `methodology_suggestion`, `pinned_notes`

**Output:** `brief.json`

## Stage 2 — Construction Methodology Selection
**Inspired by:** Philyra (learns methodology from history), Carles pyramid, Roudnitska
**Module:** `engine/orchestration/methodology.py` (port from `future_modules/construction_methodology.py`)

**10 methodologies** (already coded in `construction_methodology.py`):
- A. Pyramid Construction (Carles/Roudnitska) — default
- B. Accord-Based Construction (Carles/Jellinek)
- C. Hedonic Optimization (Computational)
- D. Single-Material Expansion (Roudnitska "One Truth")
- E. Constraint-Based (Regulatory/Cost/Safety)
- F. OAV-Targeted
- G. Texture-First (Ellena/Modern Minimalism)
- H. Performance-First
- I. Cost-Optimized (Commercial)
- J. Minimum-Material (Minimalist/Niche)

**Scoring:** each method scored 0-1 based on:
- Brief alignment (e.g. "minimalist" → D, J, G)
- Family alignment (e.g. chypre → B; transparent → G)
- Methodology history (`data/knowledge_graph/methodology_success.json`, NEW)
- User pinned notes (e.g. "Iso E Super" → G or D)

**Output:** `methodology.json` with `selected_method`, `alternatives`, `skeleton_strategy`

## Stage 3 — Family Archetype Resolution (Edwards 14)
**Inspired by:** Michael Edwards Fragrance Wheel
**Module:** `engine/orchestration/family_resolver.py` (uses `engine/families/registry.py`)

**Canonical taxonomy** (replace 4-family model with 14 sub-families):
- **Fresh**: Citrus, Water, Green, Fruity, Aromatic
- **Floral**: Floral, Soft Floral, Floral Amber
- **Amber**: Soft Amber, Amber, Woody Amber
- **Woody**: Woods, Mossy Woods, Dry Woods
- **Fougère** (central, bridging all 4)

**Per family** (backfill what's missing in registry):
- `anchors` — 3-5 defining materials
- `drift_limits` — max OAV ratios for character materials
- `oav_targets` — `pyramid_targets.py` already has this
- `forbidden_materials` — eg chypre without oakmoss = no chypre
- `repair_pool` — alternatives when an anchor is OOS

**Output:** `archetype.json`

## Stage 4 — OAV Pyramid + PTD Preview
**Inspired by:** Carles pyramid; PTD (Perfumery Ternary Diagrams, 2025)
**Modules:** `engine/orchestration/pyramid_planner.py` (NEW), reuse `engine.knowledge.pyramid_targets`

**Process:**
1. For the selected family + methodology, compute OAV target distribution across 5-7 pyramid slots
   (top-shimmer, top-anchor, heart-bridge, heart-character, base-foundation, base-fixative, base-trail)
2. For each slot, list 2-3 candidate materials with their typical OAV contributions
3. Generate **PTD previews** for the 3 dominant material triplets
4. Compute expected temporal evolution using existing `engine.pipeline.simulator`

**Output:** `pyramid.json` + `pyramid_ptd.png`

## Stage 5 — Material Selection (CAMD-style)
**Inspired by:** Philyra; Zhang et al. CAMD with RSML rules; `engine.ingredient_intelligence._PROFILES`
**Module:** `engine/orchestration/material_selector.py` (NEW)

**Process:**
1. For each pyramid slot, pick 1-3 materials from the candidate list:
   - Respect inventory (`engine.material_resolver`)
   - Respect dilution math (copilot-instructions §6)
   - Apply 2-3 material musk chord (copilot-instructions §10)
   - Apply VP-aware pair validation (`formula_diagnosis.diagnose_vp_pairs`)
   - Apply RULE 17 (family shift materials ceilings)
2. **Novelty check** (Philyra-style): compute distance-to-nearest-neighbor in OAV-space against the 214 existing formulas
3. **If novelty < 0.3 AND `--creative` mode**: run novelty injection using `engine.synergy_graph` and `material_interactions` to find "white-space" materials
4. Compute doses by inverse-ODT: `target_oav × odt_ppm × batch_volume_µL × dilution_factor` → µL
5. Generate 1 (default) or 3 (creative) candidate formulas

**Output:** `formula_candidate.md` × 1 or 3

## Stage 5b — Novelty Check
**Inspired by:** Philyra novelty dial (white-space identification)
**Module:** `engine/orchestration/novelty.py` (NEW)

**Process:**
1. For each candidate, compute OAV vector across the 14 Edwards sub-families
2. Compute distance to nearest neighbor in 214-formula OAV space
3. Reject if distance < `--novelty-min` (default 0.3)
4. Report nearest 3 neighbors for transparency

**Output:** `novelty_report.json` with distance + nearest neighbors

## Stage 6 — IEC Iteration Loop
**Inspired by:** Fukumoto et al. (CEC 2010, 2014, 2015) — Interactive Differential Evolution; CMA-ES from Bell/Queiroz 2024
**Module:** `engine/orchestration/iec_loop.py` (port + extend from `future_modules/iteration_protocol.py`)

**Two modes:**
1. **Auto mode** (default): the pipeline scores candidates with the 10-axis scorer, the IEC converges automatically
2. **Human-in-loop mode** (opt-in via `--interactive`): user scores 5–8 candidates per generation; DE operator uses those scores

**Algorithm:** Sequential Differential Evolution (Fukumoto 2014) with:
- Population: 8 candidates
- Generations: 10 (cap)
- Operator: DE/rand/1/bin
- Fitness: `0.6 × hedonic_score + 0.2 × oav_pyramid_match + 0.1 × novelty + 0.1 × ifra_clean`
- **CMA-ES fallback**: if no improvement in 3 generations, switch to CMA-ES for 3 more generations
- **Roudnitska stop criterion**: when no improvement > 0.5% in 3 generations, OR when max generations reached

**Output:** best candidate, full DE history, convergence plot

## Stage 7 — Gate + Diagnose + Archive
**Existing:** `scripts/formula_release_gate.py`, `engine/pipeline/interventions.py`

**Process:**
1. Run the existing 23-gate pipeline
2. Run `formula_diagnosis` (6 modules)
3. Append `## Pipeline Analysis` to formula file
4. Save to `formulas/complete/<Name>_<vol>mL_EDP.md`
5. Generate "design note" section at the top showing the 7-stage provenance

**Output:** `formulas/complete/Iris_Cathedral_30mL_EDP.md` (final formula with full provenance)

## Locked artifacts per stage

| Stage | File | Contents |
|---|---|---|
| 1 | `brief.json` | Structured brief, locked by user |
| 2 | `methodology.json` | Selected method + 3 alternatives |
| 3 | `archetype.json` | Family + 14-sub-family taxonomy, drift limits, OAV targets |
| 4 | `pyramid.json` + `pyramid_ptd.png` | 5-7 slot OAV targets, PTD visual |
| 5 | `formula_candidate.md` × 1-3 | Dosed formula candidates, novelty score |
| 5b | `novelty_report.json` | Distance + 3 nearest neighbors |
| 6 | `iec_history.json` + `convergence.png` | DE/GEN trace, per-cand fitness |
| 7 | `formulas/complete/<Name>_<vol>mL_EDP.md` | Final + 7-stage provenance header |

## File / module layout

```
engine/
├── orchestration/                    ← NEW
│   ├── __init__.py
│   ├── brief.py                      ← stage 1
│   ├── methodology.py                ← stage 2
│   ├── family_resolver.py            ← stage 3
│   ├── pyramid_planner.py            ← stage 4 (with PTD)
│   ├── material_selector.py          ← stage 5
│   ├── novelty.py                    ← stage 5b
│   ├── iec_loop.py                   ← stage 6
│   └── pipeline.py                   ← orchestrator
├── pipeline/                         ← EXISTING (untouched, analytical)
├── optimizer/oav_objective.py        ← EXISTING (used by IEC fitness)
└── families/registry.py              ← EXTEND with Edwards 14
scripts/
├── formula_release_gate.py           ← EXISTING, add --from-brief flag
└── _create_formula.py                ← NEW thin CLI wrapper
```

## Implementation phases

1. **Phase 0** — Wire 3 existing `future_modules/` stubs into `engine/orchestration/`
   (no new logic, just connectivity)
2. **Phase 1** — Stage 1 (Brief) + Stage 3 (Family, Edwards 14)
3. **Phase 2** — Stage 2 (Methodology) + Stage 4 (Pyramid + PTD)
4. **Phase 3** — Stage 5 (Material) + Stage 5b (Novelty)
5. **Phase 4** — Stage 6 (IEC with DE + CMA-ES fallback)
6. **Phase 5** — Stage 7 (Integration) + `_create_formula.py` CLI + docs + tests

## Constraints (respected throughout)

- **RULE 0**: Read `inventory.txt` before any material selection (already a hard gate)
- **RULE 1**: All calculations in ppm/ODT/OAV (no new exception)
- **RULE 2**: No new pipeline scripts (only `engine/orchestration/*.py` + a thin `_create_formula.py` CLI)
- **RULE 3**: Optimize for the name (every stage's loss function includes a name-similarity term)
- **RULE 4**: Composite OAV for naturals (already enforced by `formula_state.py:219, 567`)

## Literature sources (attribution in code comments)

- **Philyra / Carto / Osmo** — novelty + POM-style distance (Stages 5b)
- **Fukumoto et al. 2010, 2014, 2015** — IEC with sequential DE (Stage 6)
- **Bell 2024, Kumar 2024** — CMA-ES fallback + OV vector optimization
- **Kumar 2024** — 14-family OV vector → mapped to `pyramid_targets.py`
- **PTD 2025** — ternary diagram visualization (Stage 4)
- **Carles / Roudnitska** — pyramid construction, Roudnitska stop criterion
- **Michael Edwards 2010** — Fragrance Wheel 14-sub-family taxonomy
- **Sniff-AI (ksek87)** — NER + TF-IDF brief translation reference
- **Zhang et al. 2018, 2021** — CAMD with hard constraints (Stage 5)
- **OlfactionBase** — OR-mapping data for Stage 5 future-extension
- **Arctander 1960** — 88 odour families; 523 naturals blending knowledge (future Phase 2+)
- **DOPBO 2024** — One-Pot Bayesian Optimization; future material-optimizer backend

## Test plan (Phase 5)

- `tests/test_orchestration.py` — golden-set: re-create 3 known formulas
  (Iris Cathedral, Bleu Carbon, Cedre Azure) from name only; verify they gate PASS
  and reach the same family/archetype
- `tests/test_brief.py` — verify NER-lite extracts correct anchors from known free-text briefs
- `tests/test_novelty.py` — verify novelty score distinguishes duplicates from genuinely new formulas
- `tests/test_iec.py` — verify DE converges within 10 generations on a synthetic 2D fitness landscape
- `tests/test_methodology.py` — verify methodology scoring maps "minimalist" → D, J, G
- `tests/test_pyramid.py` — verify pyramid matches `pyramid_targets.py` for 3 families
- `tests/test_family.py` — verify Edwards 14-sub-family mapping to existing 4 main families

## Out of scope (deferred to future plans)

- **POM-style molecule embedding** (Osmo POM) — requires training a GNN, not in scope
- **GenAI fragrance molecule design** (CSIO-FPIL generative-odor) — beyond the brief
- **3D/2D molecular visualization** for materials
- **Backend API endpoint** for the orchestrator (Phase 5.1 in the original draft)
- **OlfactionBase OR integration** for adaptive receptor-aware optimization
- **Arctander knowledge graph backfill** for all 523 naturals
- **Real olfactory sensor integration** (DOPBO one-pot)
- **Visual formula editor UI** (ParfumFormula / PerfumeNuke-style)
