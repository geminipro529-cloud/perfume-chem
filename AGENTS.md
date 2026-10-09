# AGENTS.md — Perfume Chemistry

> **⚠️ RULE 0: Check stock before constructing ANY fragrance.**  
> Materials, dilutions, and stock levels change. Never assume availability. Never rely on memory. `inventory.txt` is Kenny's hand-kept list; the release gate checks stock against the V5 workbook snapshot (`data/governance/inventory_v5_current_stock_snapshot.json`) plus the dated overlays `data/governance/inventory_user_authority_overlay_*.json`. There is no command that prints that list; call `parse_current_inventory()` from `engine/inventory_parser.py` to see it. Check every material against both before dosing, and report any disagreement rather than guessing. This applies to all agents, all sessions, all formulas — no exceptions.

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
exclusions independently of physical stock ownership. The user cleared the
PerfumersWorld Orris Liquid (8IQ24653) hold on 2026-10-08, so no material is held
now. A hold is cleared only by the user's explicit word; completing stock details
does not clear one.

### Literature boundary

`data/formulation_knowledge/literature_v1.json` contains source-bounded facts,
manufacturer descriptions and explicitly uncalibrated architecture hypotheses.
`prior_research_corpus_v1.json` indexes prior local research by exact bytes;
indexing is not full-text review, empirical capability admission or action authority.
Formula Studio and goal analysis retrieve these locally with no runtime web calls.
Exact material grades, iris root/butter/cosmetic/transparent/woody profiles, violet
petals, violet powder and violet leaf remain distinct. Explicit user constraints
take precedence. Literature guidance cannot fabricate doses, receptor maps,
physical properties, intensity, pleasantness or liking measurements.

The construction library, subtype research, Deep Compose architecture adapters,
the omission comparison plan and the recovered CHIMIE L'HOMME design are described
in `docs/agents/formulation-knowledge.md`. Read it before changing or relying on any
of them.

### Historical notes

The session learnings, numeric tables and failure registry in `docs/agents/` are
historical diagnostics, not universal scientific or formulation policy. Where they
contradict Rules 1, 4 or the reviewed knowledge boundary, those rules take
precedence. In particular, OAV bands do not establish intensity, natural
decomposition does not establish an accuracy multiplier, and chemical-family
difference does not prove a clash.

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

## Running formulas through the gate

Before a run: confirm the family in `docs/fragrance_families_reference.md`, check
stock (RULE 0), and confirm every material has physics data (`ODT_DATA` in
`engine/odor_thresholds.py`, `data/materials/<LETTER>.yaml`, and `_PROFILES` in
`engine/ingredient_intelligence.py`). Duplicate `ODT_DATA` entries: the last one wins.

```bash
python scripts/formula_release_gate.py \
    --formula-file formulas/My_Formula_30mL_EDP.md \
    --expected-concentrate-ul 6000 \
    --brief <family> \
    --json
```

A read-only pipeline run must write the complete output to an immutable,
fingerprinted run artifact and must not modify the formula file. In chat, present
an exact concise summary and the artifact path; paste the full analysis
(`scripts/format_pipeline_analysis.py --input <json>`) only when the user explicitly
asks for it.

Before presenting a run, read `docs/agents/pipeline-runs.md`. It holds the JSON
sections to read beyond gate status, the required OAV headspace table and
perfumer-analysis order, common pipeline bugs, and the places to touch when
adding a material or a family archetype.

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

## Reference docs (open only when the task needs them)

These sections moved out of this file unchanged on 2026-10-08, so every session
and worker loads less. The rules above take precedence over them.

| File | Open it when you are |
|------|----------------------|
| `docs/agents/formulation-knowledge.md` | working on Formula Studio, Deep Compose, the construction library, subtype research, architecture adapters, omission plans, or CHIMIE L'HOMME history |
| `docs/agents/pipeline-runs.md` | presenting or debugging a gate run, or adding a material or family archetype |
| `docs/agents/data-and-learnings.md` | tracing material data between `ODT_DATA`, `_PROFILES` and `material_properties.json`, or checking known data issues and past fixes and session learnings |
| `docs/agents/science-reference.md` | using the headspace OAV formula, activity coefficients, VP note tiers, psychophysics, temperature correction or EU allergen limits |
| `docs/agents/reconstruction.md` | using `scripts/reconstruct.py`, operating modes, ledgers, chassis and module envelopes, or event-sourced bottles |
| `docs/agents/failure-registry.md` | checking failures F1-F11 (code and data cite them as "AGENTS.md F2", "AGENTS.md F11") |
| `docs/agents/tools-and-mcp.md` | setting up OpenCode or DeepSeek: MCP toggle profiles, tool usage rules, synergy-discovery agents |
