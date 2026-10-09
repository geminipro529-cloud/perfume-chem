# AGENTS.md — Perfume Chemistry

> **⚠️ RULE 0: Check stock before constructing ANY fragrance.**  
> Materials, dilutions, and stock levels change. Never assume availability. Never rely on memory. `inventory.txt` is Kenny's hand-kept list; the release gate checks stock against the V5 workbook snapshot (`data/governance/inventory_v5_current_stock_snapshot.json`) plus the dated overlays `data/governance/inventory_user_authority_overlay_*.json` and the bottle details Kenny saves on the Lab app's Stock page (`data/user/` completion log). There is no command that prints that list; call `parse_current_inventory()` from `engine/inventory_parser.py` to see it. Check every material against `inventory.txt` and that gate list before dosing, and report any disagreement rather than guessing. This applies to all agents, all sessions, all formulas — no exceptions.

> **⚠️ RULE 1: Keep stock dose, delivered concentration, ODT, OAV, intensity, character, and liking separate.**
> Use exact stock and active-mass accounting for formula arithmetic. OAV is permitted only as a detection-related diagnostic when the numerator and threshold have compatible identity, phase, units, matrix, and protocol. Liquid ppm, formula percentage, and stock dose are not gas concentration. OAV is never perceived contribution, intensity, pleasantness, beauty, or an optimizer objective. A missing compatible ODT blocks the numerical OAV claim, not an independently supported endpoint.

> **⚠️ RULE 2: Don't add new pipeline entry scripts without Kenny's OK.** Extend `scripts/formula_release_gate.py` or the `engine/` modules instead. Scripts already in `scripts/` (including `scripts/reconstruct.py`) are allowed. Throwaway helpers go in `archive/` or `output/` (gitignored), prefixed `_`.

> **⚠️ RULE 3: Optimize for the name, not just the numbers.**  
> When optimizing, enhancing, or modifying a formula, the target is the **name / concept / original brief** of the perfume — not numerical scores. A formula named "Iris Cathedral" must be optimized toward iris-incense character, even if the optimizer suggests boosting radiance with Hedione and citrus. The name is the north star. Numerical gates (OAV, pyramid, IFRA compliance) are floors to meet — not ceilings to chase. This rule applies to all agents, all sessions, all formulas. When uncertain, re-read the formula name and ask: "Does this still smell like its name?"  
> **⚠️ RULE 4: Natural-mixture calculations preserve whole-product identity and explicit composition uncertainty.**
> A measured whole-product threshold or response curve may be used only for the same product and supported conditions. Constituent decomposition in `engine/pipeline/natural_absolute_decomposition.py` is a versioned scenario, not exact lot truth: retain unknown remainder, do not silently renormalize identified peaks to 100%, and do not sum constituent OAVs as a universal whole-natural intensity or accuracy claim. Missing composition, phase, threshold, or release applicability remains `HOLD`/`UNAVAILABLE`.

> **⚠️ RULE 5: Every revised compounding formula must pass the pre-mix active-dose + OAV-per-time guard.**  
> Supply the immediate parent formula to the release gate. A stock-strength change must preserve active dose unless an explicit dose change is intended. `STOCK_REBASE_ACTIVE_EQUIVALENCE` is a hard arithmetic failure. OAV-per-time is a screening alarm only, never percent perceived contribution or a final aesthetic/similarity gate. Regression cases include the Prada L'Homme citronellol and Lemonile 10%-to-neat patterns. See `docs/PRE_MIX_OAV_GUARD.md`.

> **⚠️ RULE 6: Keep personal scent research easy and evidence-proportionate.**
> A formula plus a plain-language sensory goal is sufficient to generate non-authoritative clues and small controlled-comparison hypotheses. Observations and preserve/avoid criteria are optional but useful. Do not demand photographs, receipts, lots, density, instrumental measurements, safety paperwork, or a fully bound physical build unless the specific requested conversion, claim, experiment, or compounding action actually requires them. Default user output is concise; detailed diagnostics are opt-in.

## Reviewed formulation knowledge

### Temporary user compounding exclusions

`data/governance/inventory_compounding_holds.json` records user-requested
exclusions independently of physical stock ownership. PerfumersWorld **Orris
Liquid (8IQ24653), including the owned 9% w/w in DEP stock, must not be selected
for new compounding formulas or bottle additions** until the user supplies more
information and explicitly clears the hold. Preserve historical formulas and
stock receipts; do not mark it depleted, infer that it is unsafe, or automatically
substitute another iris material. Completing stock details does not clear a hold.

`data/formulation_knowledge/literature_v1.json` contains source-bounded facts,
manufacturer descriptions and explicitly uncalibrated architecture hypotheses.
`prior_research_corpus_v1.json` indexes prior local research by exact bytes;
indexing is not full-text review, empirical capability admission or action authority.
Formula Studio and goal analysis retrieve these locally with no runtime web calls.
Exact material grades, iris root/butter/cosmetic/transparent/woody profiles, violet
petals, violet powder and violet leaf remain distinct. Explicit user constraints
take precedence. Literature guidance cannot fabricate doses, receptor maps,
physical properties, intensity, pleasantness or liking measurements.

`construction_library_v1.json` adds initial advisory dossiers for all 49 frozen
construction packages. It is a separate runtime library, not activation of the
planning manifest. Functional connections and architectural alternatives are
untested hypotheses; unreviewed subtype scope remains explicit. Exact source
records and review receipts are required for retrieval. Do not turn these cards
into empirical doses, automatic stock aliases, performance or liking claims.
Formula Studio exposes the raw dossier options inside optional research details.

`subtype_research_v4.json` is the active, separately hashed partial subtype layer;
its v1–v3 predecessors and parent library remain immutable and byte-bound.
Successors preserve prior cards, botanical declarations, addenda and campaign
holds. Species, organs, flower stages and exact extract/reconstruction grades
remain distinct. The Tilia card requires both the corrected paper and notice.
Match all required request facets, preserve
negations, and keep source observations separate from construction hypotheses.
Food/tea studies do not provide perfume doses or performance. A detailed card is
not exhaustive subtype review; unavailable or drifted sources withhold that card.
All 13 planned floral packages now have additional partial subtype research;
this is not exhaustive botanical coverage. Named campaigns whose exact brief or
formula is unavailable must not inherit adjacent commercial-fragrance identities.

`architecture_adapters_v5.json` is the active, separate, closed Deep Compose bridge;
it binds immutable v1/v2/v3/v4 bytes and preserves their ordered mappings. All five
versions participate in durable fingerprints. It prioritizes complete positive
request matches over title-only matches, then qualified subtypes over umbrella
cards; this is request specificity, not quality ranking.
Its 104 mappings and 168 options supply
explicitly supported subtype-to-role mappings. Keep the original control and at
most two unordered source-bound comparison briefs; solve and critique each with
its own roles. Preserve exact anchors, protected recognizers, avoid constraints,
stock holds and quantities. Numeric allocation comes only from separately hashed
local heuristic templates, never paper prose or source peak percentages. Missing
campaign governance is not an empty hold list. Unsupported mappings remain
advisory; a different composition does not establish a better-smelling perfume.
Fruit roles require own-material odor annotations, not a berry token in a stock
name, category proxy, comment or synergy partner. Named fruits remain explicit
intent with untested recognition. Structural role coverage is not sensory request
accuracy. Diagnostic signatures must be recomputed from executable role records;
exact option/template/policy lineage and protected roles must replay from the
control. Missing authority records, conflicting source receipts, malformed
physical quantities and inconsistent separate totals fail verification. Empty,
withheld or physically duplicate alternatives cannot inflate executable coverage.
V4 chypre/cologne options require exact own-odor predicates. Every planned option
must be attempted and accounted for. An unavailable option needs an exhaustively
verified empty admissible stock pool; consumed stock, solver failure and critic
rejection are not empty-pool evidence. Botanical organs and suggested applications
are not own-odor annotations. Scarce required descriptor roles use bounded forward
checking without weakening stock, trace, exclusion or identity gates.
Numerically equal doses and split rows describe the same physical composition.
Suppressed duplicates retain bounded physical rows and an earlier retained
reference; verify their conservation, identity and complete attempt accounting.
Relabeled failure states or mismatched attempt IDs must not bypass that check.
Historical protocols use fixed predecessor paths and hashes, never the active
manifest as a substitute. An active mapping is not full-corpus acceptance;
consult the versioned research coverage progress and its exact input hashes.

V5 uses a closed own-odor operation registry. Application suggestions, synergy
partners, negated descriptions and botanical origin cannot supply odor roles.
Exact product refinements must strengthen the canonical role without changing
its quantities, function or protected constraints. Avoid constraints apply to
the entire comparison, including unchanged background roles; missing odor words
do not certify absence. Source review assessments must match the current
canonical review bytes, not merely a caller-supplied allowed flag.
`subtype_implementation_dispositions_v1.json` accounts for the 132 cards that
lacked v4 mappings. Its dispositions separate architecture, exact-product,
omission and evidence/input needs. After v5, 75 cards still have no executable
mapping. This is honest coverage accounting, not exhaustive research or a claim
that all mapped options are feasible with current stocks.

The optional `OMISSION_COMPARISON_PLAN` job creates a fixed-row, equal-total-mass
control/omission plan with explicit carrier blanks. It does not re-solve the
background, preserve total fragrance-active mass, authenticate inventory, remove
anything from an existing bottle, or authorize a physical action. Missing exact
mass/basis/blank information withholds that experiment only. The protocol handoff
is planning-only, not an executed or privately blinded session. Ordinary personal
clues and observations still need no photographs, lots or formal paperwork.

`data/governance/campaign_reference_chimie_lhomme_v1.json` recovers the exact
historical Terre-heart CHIMIE L'HOMME design from saved chat sources. It is not
Sport Citrus / Dry Amber. The archived 5,510 uL liquid stocks and 600 mg Ambrox
crystals are design totals, not a reconstruction of the current physical bottle.
The later user correction says fixed ethanol was used and final volume was not
measured. Read-only retrieval may display this hash-bound recovery context;
it must not import historical dilutions into inventory or bypass the existing
campaign-generation hold. The original no-reference hold is historical evidence,
not a reason to keep asking the user to find a reference now recovered locally.

Older session learnings and numeric tables below are historical diagnostics,
not universal scientific or formulation policy. Where they contradict Rules 1,
4 or the reviewed knowledge boundary, those rules take precedence. In particular,
OAV bands do not establish intensity, natural decomposition does not establish
an accuracy multiplier, and chemical-family difference does not prove a clash.

## `$sol-ultra-delegate` authority boundary

- `$sol-ultra-delegate` is an explicit, project-scoped command for bounded, non-sensitive, read-only packets.
- Its supervising GPT-5.6 Sol Ultra child uses the authenticated `perfume-chem-sol-ultra` DeepMimo project. The server-owned HTTP-provider order is exactly DeepSeek `deepseek-flash` then Xiaomi MiMo `mimo-v2.6-pro`; only those two providers are allowed and Luna is disabled. Sol Ultra is a task-level original-model handoff, not a DeepMimo HTTP provider.
- The helper requests `X-DeepMimo-Original-Model-Handoff: enabled`; DeepMimo may return a machine-validated, non-retryable `providers-exhausted` handoff receipt but does not select or launch a native fallback.
- The supervising child automatically creates exactly one native GPT-5.6 Sol Ultra fallback only after that validated handoff or when a route-valid completed answer fails the lane's predefined local quality check. It chooses the fallback's bounded role, task name, scope, prompt, and verification check. Invalid or ineligible packets, authentication failures, quota or policy rejection, router or receipt failures, and helper `BLOCKED` outcomes remain `BLOCKED` with no native fallback.
- The native fallback must not call DeepMimo, spawn another agent, or recurse. Delegated output remains untrusted evidence until the root verifies it locally.
- The existing global `$delegate`/OpenRouter path remains unused and unchanged.
- No delegated worker gains compounding, scientific-promotion, evidence-admission, safety, regulatory, purchase, or release authority.

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

## Verification order (important)

The local pre-push gate runs
`scripts/pipeline_audit.py project-verify --quick --json`; run the full command
without `--quick` before merging or publishing a release.
For backend checks, preserve this order: `ruff check app` ->
`mypy app --ignore-missing-imports` -> `pytest --cov=app`.

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

2. **Opening (0-5min)** — Describe what the first blast smells like. Reference OAV ratios: which materials dominate, what is their perceptibility (massive >1000, very strong 100-1000, strong 50-100, moderate 10-50, perceptible 5-10, at threshold 1-5, sub-threshold <1). Quote total vapor ppm.

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

## Key conventions

- **Always check stock before formulating (RULE 0): read `inventory.txt` and the gate's stock source.** The `.github/copilot-instructions.md` contains extensive rules for perfume formulation, material selection, and dosing. Agents creating formulas **must** read it.
- **Two test directories**: `tests/` (engine-level tests, runs from root) and `backend/tests/` (API tests, runs via Poetry). Each has its own `conftest.py` with different `sys.path` and fixture setups.
- **Test env vars**: `OPENAI_API_KEY=test-key`, `SECRET_KEY=test-secret-key-for-ci`, and `PERFUME_PIPELINE_AUDIT_PATH` (auto-set by root `conftest.py` to a tempfile).
- **`inventory.txt` format**: `--- CATEGORY ---` headers, `- Material Name (dilution%)` bullets. Parsed by `engine/inventory_parser.py` which deduplicates by keeping the highest-dilution entry.
- **`archive/` and `output/` are gitignored** — scratch scripts (prefix `_`) and generated outputs go there.
- **The repo root holds only config and entry points.** Root-level `_*`, `*.json`, `*.jsonl` and `*.txt` files are gitignored (except the named config files and `inventory.txt`/`requirements.txt`); older root reference docs live in `docs/legacy-root/`.
- **Pipeline logic** lives in `engine/pipeline/` (gates, formula_state, simulator, oav_intelligence, etc.). The entry point is `scripts/formula_release_gate.py`. The old `pipelines/` directory has been removed — all orchestration now imports `engine/` modules directly.
- **`.vscode/`, `.claude/`, `*.db`, `*.xlsx`, `*.csv`, `*.png` are gitignored.**
- **`engine/` dependencies** (`sentence-transformers`, `faiss-cpu`, `torch`, etc.) are in root `requirements.txt`, not in the Poetry project.

## When formulating perfumes

The `.github/copilot-instructions.md` file has mandatory rules: no material defaults (evaluate every option), use perfumer vocabulary, justify every material choice, and always check stock first (see RULE 0: `inventory.txt` and the gate's stock source). A single precisely chosen musk is valid; multiple musks require distinct target-linked roles plus pairwise nonredundancy and controlled omission/alternative comparisons. Tonalide, Macrolide, and Musk Ketone are omitted by default and are exception-only under the complete design-call and inventory-separation contract.

> **⚠️ RULE 7: When optimizing longevity, scan ALL categories for low-VP materials — don't just reach for "base" or "musk" materials.**
> Materials in Citrus, Floral, and Accord Bases/Other categories can have surprisingly low vapor pressure (Paradisamide VP=0.002 Pa, Lemonile VP=0.2 Pa, Pamzest VP=30 Pa). Run `engine.formula_recommendations.find_hidden_fixatives()` to surface materials whose VP qualifies them as fixatives but whose note/role places them in top/heart categories. This prevents the blind spot of treating "citrus" and "fixative" as mutually exclusive.

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

### 2. ~~Hedione/Hedione HC ODT collision~~ (FIXED 2026-05-25)
Fixed: Both `"hedione"` and `"hedione hc"` in ODT_DATA now correctly use `odt_air=0.05`. `ODT_DATA` and `ODT_VERIFICATION` are separate dicts — the collision was due to a wrong numeric value (20.0 → 0.05) in `ODT_DATA`, not an alias issue.

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

## Agentic Workflow (for DeepSeek)

When tasks involve multiple domains (e.g., research + code + test), break them into sub-tasks using `sequential_thinking` first, then use `rg` and the built-in search tools for research before writing code. This compensates for DeepSeek's tendency to shortcut complex reasoning chains.

## Tool usage rules

MCP servers configured in `opencode.json`: `github`, `playwright`, `sequential_thinking`, `pubchem`, `memory`, `perfume_kb`, `cheapluna`. Use only these.
Use `github` for GitHub code patterns, `sequential_thinking` for step-by-step decomposition, and `pubchem` for compound data (MW, logP, VP, ODT, CAS).
For docs, code search and project structure, use the built-in tools and `rg`.

## Agents for synergy/pairing discovery

Use `@agent-citrus-top` for citrus, green, and top-note material pairings.
Use `@agent-floral-heart` for floral and heart-note material pairings.
Use `@agent-woody-base` for woody, amber, and base-structure material pairings.
Use `@agent-musk-fixative` for musk, fixative, gourmand, and leather material pairings.
Use `@agent-spice-aromatic` for spice, aromatic, and specialty material pairings.

Each agent reads `inventory.txt`, evaluates pairs against perfumery + chemistry criteria, and appends findings to `data/knowledge_graph/pairing_rules_discovered.json`. Run all 5 agents in parallel to cover the full inventory.

## Token efficiency

MCP servers consume context tokens just by being loaded. Only invoke them when they will provide concrete benefit — do not call them reflexively. Prefer built-in tools (`read`, `grep`, `glob`, `bash`) for simple queries; save MCP calls for cases where they genuinely add value (cross-referencing external code, searching docs, deep architecture mapping).

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

---

## Reconstruction Pipeline

> **New: `scripts/reconstruct.py`** — Evidence-driven formula reconstruction CLI.
> **New: `engine/reconstruction/`** — Purpose-built reconstruction engine (10 modules).
> **New: `engine/identity/`, `engine/units/`, `engine/versioning/`, `engine/inventory/`, `engine/evidence/`, `engine/target/`, `engine/bottle/`** — Foundation service modules.
> **New: `engine/graphs/`, `engine/reports/`** — Accord graph and report generation.

### Architecture

The reconstruction system uses a **layered ledger architecture** — nothing jumps across layers:

```
Evidence → Target hypothesis → Accepted target → Accord/DNA graph →
Chassis derivation → Inventory mapping → Build formula →
Bottle events → Analytical/sensory results → Updated target
```

- **Evidence ledger**: What sources claim (notes, labels, GC-MS, rosters)
- **Target ledger**: Best current hypothesis, independent of inventory
- **Inventory ledger**: What is physically available (stock, lot, concentration)
- **Build ledger**: Inventory-mapped formula with explicit substitutions
- **Bottle ledger**: Event-sourced physical bottle state (immutable events)
- **Analysis ledger**: Model runs and analytical instrument outputs
- **Sensory ledger**: Coded sample evaluations with time-resolved ratings

**Critical rule**: Missed inventory must NEVER alter the target. Substitutions are in the build layer only.

### Operating Modes

All engine operations require an explicit mode:

| Mode | Purpose |
|------|---------|
| `RECONSTRUCTION` | Evidence gathering, identity inference, dose distributions |
| `CREATIVE_FORMULATION` | New materials, hedonic optimization, cost constraints |
| `STRUCTURAL_CHASSIS` | Partition target into core + module, derive flankers |
| `FLANKER_MODULE` | Design alternative socket modules |
| `INVENTORY_MAPPING` | Map target to available stock with substitution reports |
| `LIVE_BATCH` | Propose/confirm/commit physical bottle additions |
| `BATCH_RESCUE` | Corrective additions to already-mixed bottles |
| `SENSORY_EXPERIMENT` | Design/evaluate coded blind trials |
| `ANALYTICAL_INTERPRETATION` | Import instrument data (GC-MS, HS-SPME, GC-O) |
| `COMPLIANCE_BUILD` | Generate jurisdiction-specific compliant formulas |
| `RELEASE_REVIEW` | Full gate evaluation for release |

### CLI Usage

```bash
# Reconstruct from evidence
python scripts/reconstruct.py --mode RECONSTRUCTION build \
    --evidence evidence.json --brief prada_clean_iris \
    --output target.json

# Derive chassis partition
python scripts/reconstruct.py --mode STRUCTURAL_CHASSIS chassis \
    --target target.json \
    --envelope configs/reconstruction/prada_lhomme_envelope.json \
    --output chassis.md

# Generate alternative module
python scripts/reconstruct.py --mode FLANKER_MODULE module \
    --chassis chassis.json --direction "soft_amber_tonka" \
    --output module.json

# Validate chassis integrity
python scripts/reconstruct.py validate --chassis chassis.json
```

### New Pipeline Gates

Three new gates added to `engine/pipeline/gates.py`:
- **`mode_protection`**: Blocks actions inappropriate for current operating mode
- **`chassis_integrity`**: Validates core+module=target row-by-row arithmetic (SKIP if no chassis)
- **`authority_vector`**: Reports per-dimension authority (identity, quantity, grade, sensory, safety, etc.) — NEVER averaged into one score

### Material Identity Model

Materials are tracked through an identity chain, NOT silently collapsed:

- **Synthetic**: `chemical_entity → stereoisomer → trade_grade → supplier_product → supplier_lot → stock_solution`
- **Natural**: `botanical_species → plant_part → chemotype → origin → extraction_method → supplier_lot → analytical_composition → stock_solution`

Non-equivalent materials that must NOT be collapsed: Habanolide↔Galaxolide, Muscenone Delta↔Exaltolide, Alpha Isomethyl Ionone↔Methyl Ionone Gamma Coeur, Bacdanol↔Sandalore, Haitian↔Indian vetiver, Lavender↔Lavandin.

### Concentration Basis Enforcement

All concentrations must declare basis: `10% w/w`, `50% in DPG`, `30% v/v`. Naked `10%` fails validation. Use `engine/units/concentration.parse_concentration()`.

### Active Accounting Fix

DPG and carriers are NOT odorant-active. `engine/units/concentration.compute_active_accounting()` separates `odorant_active_ul`, `technical_active_ul`, `carrier_ul`, `solvent_ul`. The formula L'Homme chassis previously reported 3,692 µL active — the corrected odorant-active is 3,592 µL.

### Module Envelopes

Config files in `configs/reconstruction/` define chassis partition constraints:
- `protected_anchor_floors_in_core_uL`: Minimum core retention per recognizer
- `required_module_roles`: Functional roles the module MUST cover
- `forbidden_drift`: Character directions the module MUST NOT take
- Module volume alone is insufficient — envelopes track active mass, carrier mass, volatility centroid, T/H/B distribution, odor-family vector, polarity, and color risk.

### Event-Sourced Bottles

Bottle state is reconstructed from immutable events. Never delete — CORRECT_ENTRY for fixes. AI can only PROPOSE; user CONFIRMS → MEASURES → COMMITS. One irreversible action at a time.

### Known Limitations

- OAV from the pipeline is heuristic, matrix-omitted, and not a sensory-equivalence claim
- Naturals need lot-specific composition profiles for accurate modeling
- Unknown/captive materials remain as UNKNOWN_* nodes; do not force into catalog names
- Markdown formula files are GENERATED VIEWS; structured JSON is canonical source of truth
- A hash verifies content — it does not store or reconstruct content

## Tools & Token Optimization

### MCP Toggle Script

**Windows/PowerShell only; it cannot run under Claude Code on Linux.** `scripts/toggle-mcp.ps1` manages which MCP servers are loaded. Each active MCP consumes context tokens — disable unused ones to maximize token budget.

```powershell
# View current MCP status
.\scripts\toggle-mcp.ps1 -Status

# Apply named profiles:
.\scripts\toggle-mcp.ps1 -Profile formula   # chemistry/formula work (pubchem+memory+seq on, rest off)
.\scripts\toggle-mcp.ps1 -Profile dev       # full development (all on)
.\scripts\toggle-mcp.ps1 -Profile minimal   # maximum token efficiency (all off)

# Toggle specific MCPs:
.\scripts\toggle-mcp.ps1 -Enable github,playwright
.\scripts\toggle-mcp.ps1 -Disable playwright
```

**Restart OpenCode after toggling** for changes to take effect.

### MCP Server Profiles

| Profile | github | playwright | seq_think | pubchem | memory | Best for |
|---------|--------|------------|-----------|---------|--------|----------|
| `formula` | OFF | OFF | ON | ON | ON | Formula gating, material analysis, chemistry work |
| `dev` | ON | ON | ON | ON | ON | Full development, PRs, code changes |
| `minimal` | OFF | OFF | OFF | OFF | OFF | Max token efficiency, simple queries |
| `full` | ON | ON | ON | ON | ON | Same as dev |

### Token Optimization Strategy

**MCP servers consume context tokens just by being loaded.** Each active MCP adds its tool definitions to the system prompt. For maximum token efficiency:

1. **Formula/chemistry sessions**: Use `formula` profile. You rarely need GitHub or Playwright when gating formulas or analyzing OAV data.
2. **Code development sessions**: Use `dev` profile (or toggle on needed MCPs individually).
3. **Quick lookups**: Use `minimal` profile if the built-in tools (grep, glob, read) suffice.

**High-impact toggles**: `playwright` and `github` are the heaviest token consumers. Disable them first when not needed.

### Available Tools Overview

| Tool | Type | Use when |
|------|------|----------|
| `grep` | Built-in | Content search in codebase |
| `glob` | Built-in | File pattern matching |
| `rg` (ripgrep) | Shell | Fast regex search (already installed: 15.1.0) |
| `sg` (ast-grep) | Shell/skill | AST-aware structural search (0.43.0) |
| `basedpyright` | LSP | Python type checking (1.39.8, configured as default) |
| `ruff` | Formatter | Python formatting |
| `gh` | Shell | GitHub CLI operations (2.95.0) |
| `npx` | Shell | Node package runner (11.16.0) |
| `docker compose` | Shell | Container management |

### MCP Servers Reference

| MCP | Package | Purpose | Token cost |
|-----|---------|---------|------------|
| `github` | `@modelcontextprotocol/server-github` | Code search, PRs, issues, repo ops | High |
| `playwright` | `@playwright/mcp` | Browser automation, web testing | High |
| `sequential_thinking` | `@modelcontextprotocol/server-sequential-thinking` | Multi-step reasoning | Medium |
| `pubchem` | `@cyanheads/pubchem-mcp-server` | Chemical compound data (MW, logP, VP, ODT) | Medium |
| `memory` | `@modelcontextprotocol/server-memory` | Persistent knowledge graph | Low-Medium |

### LSP

The workspace uses **basedpyright** (1.39.8) for Python type checking, configured in `opencode.json`. It replaces the deprecated `pyright`. Both `.py` and `.pyi` files are covered.

---

## Agent Failure Registry (Session 2026-07-06 - Cassis Iris Smoke)

Every systemic failure from this session. Read before formulating. Learn or repeat.

### F1. OAKMOSS COMPOSITE OAV - 300x UNDERESTIMATE
- Symptom: Perfumer smelled dominant oakmoss. Pipeline said OAV 0.03.
- Root cause: Composite decomposition had 5 constituents at 23% weight. Missing: atranorin degradation on skin (time-dependent, not equilibrium), methyl beta-orcinol carboxylate (primary olfactory monoaryl), orcinol phenolics (highest VP oakmoss constituents at 0.15-0.50 Pa).
- Fix: Expanded to 10 constituents at 46% weight. Added degradation pathway. Composite OAV 0.03 to 0.28 (10x) but still below threshold - equilibrium models cannot capture reaction kinetics.
- Learning: Natural absolute OAV models are PERCEPTUALLY FLOORS. Trust the nose over the model. Applicable to all naturals with degradation pathways (labdanum, tonka, vanilla, patchouli).

### F2. HEDIONE CROWDING - 18% = ONE-NOTE
- Symptom: All character voices buried under Hedione radiance.
- Root cause: Hedione at 18% of concentrate. Below 12% it is a carrier. Above 15% it IS the perfume.
- Fix: Cannot reduce in mixed bottle. Only counter: brute-force character material dosing above Hedione OAV.
- Learning: CHECK HEDIONE DOSE BEFORE MIXING. Max 12% for chypre. Max 15% for floral.

### F3. SILENT PASSENGERS - MATERIALS BELOW OAV 1
- Symptom: 20/44 materials below OAV 1 despite character/signature labeling.
- Root cause: VP below 0.05 Pa + low dose = headspace vacuum. VP wall is absolute.
- Fix: Cut them or reclassify as structural. Jasmine, Indole, Cade cut. Cade replaced with IBQ (VP 1 Pa).
- Learning: VP below 0.05 Pa = skin-only. Do not label as character/signature.
- **Withdrawn (2026-10-08):** this entry relied on vapour pressures about 100x too low (guaiacol is about 13.7 Pa and indole about 1.63 Pa at 25 °C); the corrected values come with the material data PR. Don't use its VP cut-offs as rules.

### F4. PIPELINE PARSER BUG - SECTION HEADERS AS MATERIALS
- Symptom: Accord headers parsed as material entries, inflating concentrate total.
- Root cause: Number + uL + % triggers row parser regardless of prefix.
- Fix: Use flat single-table format. Remove section headers for first gate.
- Learning: Check exact_subtotal in JSON. If parsed > expected, headers are being read as materials.

### F5. GUAIACOL IFRA VIOLATION
- Symptom: Boosted to 180 uL of 10% (0.3% active), 3x IFRA Cat4 limit.
- Root cause: Chasing headspace OAV without checking IFRA. VP 0.053 Pa will never project strongly regardless of dose.
- Fix: Revert to 60 uL (0.1%). Use IBQ and Birch Tar for headspace smoke.
- Learning: Materials with VP below 0.1 Pa hit IFRA limits before meaningful headspace OAV. Use higher-VP analogs.
- **Withdrawn (2026-10-08):** this entry relied on vapour pressures about 100x too low (guaiacol is about 13.7 Pa and indole about 1.63 Pa at 25 °C); the corrected values come with the material data PR. Don't use its VP cut-offs as rules.

### F6. IONONE RECEPTOR SATURATION
- Historical observation: Alpha Irone increases reportedly gave diminishing returns in one formulation; this is not a universal dose-response finding.
- Withdrawn explanation: OR5AN1 assignment, a fixed 200 uL ceiling and receptor-orthogonal pairings were not established by evidence.
- Reviewed boundary: Jaeger et al. (2013), DOI 10.1016/j.cub.2013.07.030, supports OR5A1-related beta-ionone sensitivity differences, not those claims.
- Design response: Compare recognizer, root texture and support roles under the locked brief, with matched controls. Do not infer receptor affinities from chemical-family labels.

### F7. SUBAGENT MODEL FORMAT FAILURE
- Symptom: All task() calls fail with model format errors.
- Root cause: oh-my-openagent.json uses bare names (deepseek-chat) but system expects provider/model format.
- Fix: Edit config, restart session. Workaround: direct execution.
- Learning: Check subagent availability first. If broken, proceed directly.

### F8. DILUTION MISMATCH
- Symptom: Formula labels mismatch inventory dilutions.
- Root cause: Formula text includes non-dilution text. Inventory has duplicate entries at different dilutions.
- Fix: Run evaluate_formula.py or /validate before gating.
- Learning: Three minutes of preflight saves three hours of debugging.

### F9. PIPELINE BRIEF MISMATCH
- Symptom: generic brief expects generic floral pyramid. Chypre flagged as FAIL.
- Root cause: No chypre fruity/modern brief. Available archetype targets Mitsouko, not modern pineapple-iris.
- Fix: Gate with generic, ignore perfume_knowledge FAIL, evaluate pyramid manually.
- Learning: Brief system needs expansion for modern chypre/fruity territory.

### F10. OAKMOSS FIX IS TEMPLATE FOR ALL NATURALS
- Learning: Before gating, check if natural has composite decomposition in natural_absolute_decomposition.py. If absent, OAV is significantly underestimated.

### F11. NATURAL LUXURY KITCHEN-SINK FAILURE — L'HOMME RESERVE (2026-07-07)
- Symptom: 28-material L'Homme Reserve smelled "muddy/chaotic" — unrecognizable as L'Homme EDT. User wasted 225µL Alpha Irone 30% (expensive iris butter).
- Historical hypothesis: particular natural additions reportedly made the target muddy. Their constituent-family differences do not establish physical incompatibility, a reaction, or an inevitable sensory clash.
- Fix: Cut 7 materials. v3 = 21 materials: kept only chemically compatible families (Ginger zingiberene + Bergamot limonene/linalool + Rose citronellol/geraniol + Clove eugenol + Iris irones + Violet Leaf + woody-amber synthetics).
- Reviewed learning: separate solubility, chemical stability, sensory masking and target drift. Each needs its own evidence; chemical taxonomy alone decides none of them.
- Design response: retain the control and compare a small omission/addition or block alternative. Natural complexity must earn a target-linked function rather than being included as an automatic luxury upgrade.
