# Running formulas through the pipeline

> Moved out of `AGENTS.md` unchanged on 2026-10-08 so every session loads less; `AGENTS.md` links here. These are working notes and historical diagnostics, not universal policy: where they disagree with the rules in `AGENTS.md` (Rules 0-7 and the reviewed knowledge boundary), those rules win.

## Running Formulas Through the Pipeline

### Before running

1. **Read `docs/fragrance_families_reference.md`** to confirm the family exists and is buildable from inventory.
2. **Confirm every material is in stock** — check `inventory.txt` for DEPLETED markers and the gate's stock source (see RULE 0); report any disagreement.
3. **Confirm every material has physics data** — check `engine/odor_thresholds.py` ODT_DATA, `data/materials/<LETTER>.yaml` for MW/logP/VP/ODT, and `engine/ingredient_intelligence.py` _PROFILES for note/role/texture.
4. **Check for duplicate ODT entries** — `rg "material_name" engine/odor_thresholds.py` and count occurrences. The last entry wins.

### Running

```bash
python scripts/formula_release_gate.py \
    --formula-file formulas/My_Formula_30mL_EDP.md \
    --expected-concentrate-ul 6000 \
    --brief <family> \
    --json
```

Supported `--brief` values: `auto`, `generic`, `aromatic_fougere`, `layton_dna`, `vetiver_woody`. Pass `--family-archetype <key>` directly if the brief isn't in the defaults table.

### After running — read MORE than just gate status

The JSON output is ~6000 lines. Gates are only ~20%. Agents MUST extract these sections:

| Section | JSON path | What it tells you |
|---------|-----------|-------------------|
| **Headspace OAV** | `formulas[0].formula_state.materials[]` | Per-material OAV, VP, gamma, mole fraction, active µL |
| **Temporal evolution** | `formulas[0].time_series[]` | 5-window OAV (0s→5min→30min→2hr→4hr) |
| **Note distribution** | `formulas[0].formula_state.note_distribution` | OAV-weighted T/H/B split (more accurate than pyramid gate) |
| **Pyramid evaluation** | Gate `perfume_knowledge` → `data.pyramid` | VP-tier pyramid vs family targets |
| **OAV intelligence** | Gate `oav_intelligence` → `data` | Balance reports, performance projection, material cliff findings |
| **IFRA details** | Gate `safety_ifra_allergen` → `data` | Violations, edge dosing, allergen declarations |
| **Config** | `config_summary` | Confirm brief, archetype, temperature, concentration bracket |
| **Dermal exposure** | Gate `safety_ifra_allergen` → `data.dermal_exposure[]` | Per-material skin penetration estimates |

### Required: always present the OAV headspace table

After every pipeline run, format the per-material OAV table from
`formulas[0].formula_state.materials[]` in this exact column order:

```
| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | Vapor ppm | ODT ppm | OAV | Note |
```

Include `note_distribution` (T/H/B split) and `time_series` temporal
windows (opening → top → heart → late_heart → drydown). Present this
**before** discussing gate outcomes — raw headspace physics is more
diagnostic than pass/fail.

Flag any material with OAV < 1 (below perceptible threshold) if its
functional role requires perceptibility (e.g. projection musk,
character note, radiance amplifier). Materials with OAV < 1 whose role
is purely structural (fixative, inert base) are acceptable.

### Required: perfumer analysis format

After presenting the OAV headspace table and temporal evolution, produce a
complete perfumer analysis section covering these topics **in order**:

1. **Character** — What is the fragrance family? What classical reference perfumes does it evoke? Describe the dominant structural architecture (e.g. "top-to-base with thin heart").

2. **Opening (0-5min)** — Describe what the first blast smells like. Quote each lead material's OAV as a number (log10 OAV where helpful) and name the highest-OAV materials. Per AGENTS.md Rule 1, OAV is a detection-related diagnostic only; it is never perceived contribution or intensity (perceived strength grows far slower than concentration, differs per material, and mixture components suppress each other), so do not translate OAV into loudness words. Quote total vapor ppm.

3. **Heart (30min-2hr)** — How does the composition evolve as top notes burn off? Describe which materials emerge and what they contribute. Note the H/T/B distribution shift.

4. **Drydown (2hr-4hr+)** — What persists at 4h? Quote base % dominance at drydown. Describe the final character (mossy, woody, sweet, etc.). Flag any materials that functionally underperform.

5. **Sillage & Diffusion** — Identify primary OAV carriers. Quote opening vs drydown projection materials.

6. **Longevity** — Quote % raw evaporation over 4h, base persistence %, expected skin life.

7. **Balance** — Pyramid vs target, OAV range min-to-max, sigma-log contrast score, heart density assessment.

8. **Flags** — Sub-threshold materials by functional role, IFRA edges, data quality issues.


### Using the analysis script

The repo provides `scripts/format_pipeline_analysis.py` which reads a
pipeline JSON output and prints the full formatted analysis. Run:

```bash
python scripts/format_pipeline_analysis.py --input <pipeline_output.json>
```

This is the canonical human-readable analysis format. A read-only pipeline run
must write the complete output to an immutable, fingerprinted run artifact and
must not modify the formula file. In chat, present an exact concise summary and
the artifact path; paste the full analysis only when the user explicitly asks
for it. Appending a `## Pipeline Analysis` section to a formula is a separate,
explicitly authorized documentation change, never an automatic analysis side
effect.

### Integrated CLI usage

The pipeline CLI supports a `--print-analysis` flag that runs both the
release gates and the analysis script:

```bash
python scripts/formula_release_gate.py \
    --formula-file formulas/My_Formula_30mL_EDP.md \
    --expected-concentrate-ul 6000 \
    --brief vetiver_woody \
    --json 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); open('output.json','w').write(json.dumps(d,indent=2))"
python scripts/format_pipeline_analysis.py --input output.json
```

### Common pipeline bugs

| Symptom | Root cause | Fix location |
|---------|-----------|--------------|
| Pyramid shows T:0% H:100% B:0% for all formulas | note_map built with mixed-case keys, `.lower()` lookup returns "heart" default | `engine/pipeline/gates.py:720` — `.lower()` keys |
| Pyramid ignores dilutions | Called `raw_percentages()` not `active_percentages()` | `engine/pipeline/gates.py:722` |
| Material has 100M+ OAV | Duplicate ODT_DATA entries — later wrong value overwrites correct | `engine/odor_thresholds.py` — scan for duplicates |
| Material missing physics data | Added to inventory but not data_spine YAML or ingredient_intelligence profile | See "Adding a new material" below |
| `--brief` has no effect | perfume_knowledge gate reads family_archetype raw; brief never resolved | `engine/pipeline/gates.py:953` — add `infer_archetype()` fallback |
| Stale note/VPs in profiles | ingestion_intelligence profile VP differs from data_spine | Fix profile to match data_spine |

### Adding a new material to inventory

**Must touch 4 places:**

1. **`inventory.txt`** — add entry under correct category header
2. **`data/materials/<LETTER>.yaml`** — add with `mw_g_mol`, `logp`, `vp_25c_pa`, `odt_air_ppb`, `odt_eth_ppm`, `user_stock_dilution`, `user_in_inventory: true`
3. **`engine/ingredient_intelligence.py`** — add to `_PROFILES` (character, note, role, texture, mw, vp, clogp, synergies), `_TYPICAL_DOSE`, `_ODOR_FAMILY_MAP`, `_ACTIVITY_COEF_MAP`
4. **`engine/odor_thresholds.py`** — add to `ODT_DATA` dict

**Also check:** does `name_utils._ALIASES` need updating? Does `_generate_material_properties.py` need the alias?

### Adding a new family archetype

1. **`engine/families/registry.py`** — add material group tuples, add `ArchetypeSpec` with anchors/drift_limits/forbidden_materials/OAV_targets/repair_pool
2. **`engine/families/registry.py`** — add to `BRIEF_DEFAULTS`
3. **`engine/families/registry.py`** — add `novelty_assessment()` handler
4. **`scripts/formula_release_gate.py`** — add brief to argparse `choices`
5. **`scripts/pipeline_audit.py`** — add brief to argparse `choices`
6. **`engine/knowledge/perfume_knowledge.py`** — if new family key, add to `_FAMILY_TOKEN_MAP`
7. **`engine/knowledge/pyramid_targets.py`** — if new family, add pyramid ratios and OAV targets

**Verify:** run `python scripts/formula_release_gate.py --brief <key> --json` and check `family_drift_detector` PASSes.
