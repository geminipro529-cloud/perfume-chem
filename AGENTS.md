# AGENTS.md — Perfume Chemistry

> **⚠️ RULE 0: Read [`inventory.txt`](/inventory.txt) before constructing ANY fragrance.**  
> Materials, dilutions, and stock levels change. Never assume availability. Never rely on memory. Verify every material against the live inventory before dosing. This applies to all agents, all sessions, all formulas — no exceptions.

> **⚠️ RULE 1: All perfume calculations must use ppm, ODT, and OAV.**  
> Concentrations are in **ppm** (parts per million w/w in concentrate). Odor detection thresholds are **ODT** (in ppm for ethanol solution, or ppb for air). Odor Activity Value is **OAV = concentration_ppm / ODT_ppm**. Every formula dose must be convertible to ppm, every threshold check must reference ODT, and every perceptibility claim must be backed by OAV. No exceptions — this applies to formulation, dosing, gating, scoring, and all pipeline modules.

## Repo architecture

Two separate Python environments — they don't share a package manager:

| Scope | Entry | Package manager | Location |
|-------|-------|-----------------|----------|
| `engine/` (+ root scripts & pipelines) | `import engine.xxx` | pip `requirements.txt` | repo root |
| `backend/` FastAPI app | `import app.xxx` | Poetry | `backend/` |

`engine/` is a namespace package (no `__init__.py`). Root scripts and pipelines register the workspace root on `sys.path` to resolve `engine.xxx` imports. `backend/` is an independent Poetry project that does **not** depend on `engine/` — they run in separate processes.

## Commands

### Backend (FastAPI)
```bash
cd backend
poetry install
poetry run ruff check app              # lint
poetry run mypy app --ignore-missing-imports   # typecheck
poetry run pytest --cov=app --cov-report=term  # test (needs OPENAI_API_KEY=test-key)
poetry run uvicorn app.main:app --reload       # dev server
```

### Engine + root tests
```bash
pip install -r requirements.txt
pytest tests/                          # from repo root (conftest adjusts sys.path)
```

### Run the API from root
```bash
python run_api_server.py               # manually sets up sys.path, then runs uvicorn
```
Or via Docker: `docker compose up -d`

### Run a single test
```bash
cd backend && poetry run pytest tests/unit/test_xxx.py -k test_name
```
```bash
pytest tests/test_pipeline_gates.py -k test_gate_blocks
```

## CI order (important)

From `.github/workflows/ci.yml`: `ruff check app` → `mypy app --ignore-missing-imports` → `pytest --cov=app`. Same order applies locally.

## Key conventions

- **Always read `inventory.txt` before formulating.** The `.github/copilot-instructions.md` contains extensive rules for perfume formulation, material selection, and dosing. Agents creating formulas **must** read it.
- **Two test directories**: `tests/` (engine-level tests, runs from root) and `backend/tests/` (API tests, runs via Poetry). Each has its own `conftest.py` with different `sys.path` and fixture setups.
- **Test env vars**: `OPENAI_API_KEY=test-key`, `SECRET_KEY=test-secret-key-for-ci`, and `PERFUME_PIPELINE_AUDIT_PATH` (auto-set by root `conftest.py` to a tempfile).
- **`inventory.txt` format**: `--- CATEGORY ---` headers, `- Material Name (dilution%)` bullets. Parsed by `engine/inventory_parser.py` which deduplicates by keeping the highest-dilution entry.
- **`archive/` and `output/` are gitignored** — scratch scripts (prefix `_`) and generated outputs go there.
- **Pipeline scripts** in `pipelines/` are depth-1 orchestrators that self-register the repo root on `sys.path` and import `engine/` modules directly.
- **`.vscode/`, `.claude/`, `*.db`, `*.xlsx`, `*.csv`, `*.png` are gitignored.**
- **`engine/` dependencies** (`sentence-transformers`, `faiss-cpu`, `torch`, etc.) are in root `requirements.txt`, not in the Poetry project.

## When formulating perfumes

The `.github/copilot-instructions.md` file has mandatory rules: no material defaults (evaluate every option), use perfumer vocabulary, justify every material choice, build 2–3 material musk chords across depth/projection/character-echo axes, and always read `inventory.txt` first. Agents generating formulas should treat that file as a required reference.

---

## Running Formulas Through the Pipeline

### Before running

1. **Read `docs/fragrance_families_reference.md`** to confirm the family exists and is buildable from inventory.
2. **Confirm every material is in stock** — check `inventory.txt` for DEPLETED markers.
3. **Confirm every material has physics data** — check `engine/odor_thresholds.py` ODT_DATA, `data/materials/<LETTER>.yaml` for MW/logP/VP/ODT, and `engine/ingredient_intelligence.py` _PROFILES for note/role/texture.
4. **Check for duplicate ODT entries** — `grepp "material_name" engine/odor_thresholds.py` and count occurrences. The last entry wins.

### Running

```bash
python scripts/formula_release_gate.py \
    --formula-file formulas/My_Formula_30mL_EDP.md \
    --expected-concentrate-ul 6000 \
    --brief <family> \
    --json
```

Supported `--brief` values: `generic`, `aromatic_fougere`, `layton_dna`, `vetiver_woody`. Pass `--family-archetype <key>` directly if the brief isn't in the defaults table.

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

---

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

### 2. Hedione/Hedione HC ODT collision
`engine/name_utils.py` aliases `"hedione hc" → "hedione"`. This causes `ODT_DATA` keys for both to normalize to the same name, and the later entry (`hedione hc` with `odt_air=20.0`) overwrites the earlier (`hedione` with `odt_air=0.05`). The peer-reviewed pure-isomer ODT (0.05 ppb) is therefore inaccessible for the formula_state pipeline. The practical value (20.0 ppb) is used for both.

### 3. Non-inventory legacy entries
`material_properties.json` contains entries with `"in_inventory": false` — materials that existed in the knowledge graph but are no longer in `inventory.txt`. These were previously copied as-is without validation. The generator now force-overrides their physical properties (MW, VP, cLogP, ODT) from `_PROFILES` on regeneration.

### 4. Name normalization inconsistencies
`inventory_parser._canonical_name()` strips trailing parentheticals (e.g., `"Rosemary EO (French...)"` → `"Rosemary EO"`), but `normalize_name()` in `name_utils.py` preserves them. The generator ALIASES dict bridges this gap, but must be kept in sync with inventory additions. The non-inventory enrichment loop also uses ALIASES for alias resolution.

### 5. `_generate_material_properties.py` is NOT import-safe
Running `import _generate_material_properties` executes the full generation pipeline at module level. Import for function access will trigger a full regenerate + PubChem API calls. The ALIASES and CAS_MAP dicts are defined at module scope and cannot be imported separately without side effects.

## Scientific Constraints (codified from system reference docs)

### Headspace OAV calculation
```
p_i = γ_i × x_i × P_i*   (Modified Raoult)
OAV = p_i / P_atm × 1e6 / ODT_ppb
```
- `x_i` = mole fraction (must convert from weight via `n_i = w_i / MW_i`)
- `P_i*` = pure-component VP (Pa at 25°C)
- `γ_i` = activity coefficient in ethanol matrix (NEVER silently 1.0)

### Activity coefficient ranges (ethanol matrix, ~20°C)
| Class | γ |
|---|---|
| Non-polar hydrocarbons (limonene, pinenes, terpenes) | 3.0–3.2 |
| Polar esters (benzyl acetate, linalyl acetate) | 1.5–2.0 |
| Mid-polarity sesquiterpenes/alcohols | 1.2–1.8 |
| H-bond donors/acceptors (vanillin, coumarin, musks) | 0.5–0.7 |
| Macrocyclic musks | 0.4–0.6 |

### Note tier from VP
| Tier | VP range |
|---|---|
| Top | > 2 Pa (bergamot 40, petitgrain 6, linalool 20, limonene 200) |
| Heart | 0.1–2 Pa (geraniol 4*, hedione 0.09*) |
| Base | < 0.1 Pa (vetiver 0.04, iso e super 0.15*, musks ≤ 0.02) |
*Note: pipeline uses ingredient_intelligence profiles for tier, not these thresholds. These are reference ranges for formulation thinking.

### Psychophysics
- Weber-Fechner: `I = k × log(C / ODT)`
- Stevens Power Law: `I = k × C^n` (n typically 0.2–0.6)
- OAV > 1 = perceptible. OAV < 0.1 = dormant filler.
- Humans can discriminate at most 3–4 components in a mixture (Livermore & Laing)
- Adaptation: citrus adapts ~5 min, florals ~15–20 min, musks ~45–60 min

### Clausius-Clapeyron temperature correction
`ln(P2/P1) = (ΔHvap/R) × (1/T1 - 1/T2)` where ΔHvap ≈ 60 kJ/mol (working approximation). 10°C rise → VP × ~1.9. Bangkok (35°C) vs Paris (22°C): VP × ~2.8.

### EU Allergen labeling (Reg 1223/2009 Annex III)
26 mandatory allergens must be declared if exceeding 0.001% in leave-on or 0.010% in rinse-off products. SCCS Opinion SCCS/1525/21 proposes expansion to 82+ allergens as of 2026–2027.

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
