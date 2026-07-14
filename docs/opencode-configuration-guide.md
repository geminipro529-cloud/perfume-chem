# OpenCode Configuration Guide — Perfume Chemistry

All OpenCode features, MCP servers, commands, skills, agents, plugins, and optimizations configured for this project. Restart OpenCode for changes to take effect.

---

## 1. Core Config (`opencode.json`)

### What was added

| Key | Value | Why |
|-----|-------|-----|
| `model` | (provider default) | No hardcoded model — configure per your provider in `.env`. |
| `instructions` | `[".github/copilot-instructions.md"]` | Auto-loads perfume formulation rules into EVERY session. No more "please read this file" prompts. |
| `compaction` | `{"auto": true, "prune": true, "reserved": 12000}` | Pipeline JSON output is ~6000 lines + 473-line AGENTS.md. Without compaction tuning, long formula sessions blow the context window. `prune` removes stale tool outputs. 12K reserved tokens provide generous buffer. |
| `permission` | `.env` denied, bash asks, pipeline scripts allowed | Security baseline. Blocks reading/writing `.env` files (secrets). Safe bash commands auto-allowed (`git status`, `ruff`, `pytest`, `python scripts/*`). Destructive commands prompt for approval. |
| `lsp` | `{"pyright": {}}` | Catches Python type errors in `engine/` and `backend/` as agents edit files. Auto-detects from pyproject.toml. |
| `formatter` | `{"ruff": {}}` | Auto-formats `.py` files after every edit. Matches your CI's `ruff check` step — no more CI failure surprises. |
| `watcher` | Excludes `__pycache__`, `*.pyc`, `node_modules`, `output/`, `archive/`, `*.db`, `*.xlsx` | Reduces file-watching noise from build artifacts, generated data, and database files. |

### How to use

- **Compaction** fires automatically when context nears limits — no user action needed
- **Permissions** prompt interactively in the TUI when a disallowed action is attempted
- **LSP** starts automatically when a `.py` file is opened in an agent session
- **Formatter** runs automatically after every `edit` or `write` to `.py` files

---

## 2. MCP Servers

### Existing (unchanged)

| Server | Purpose |
|--------|---------|
| `filesystem` | Secure file operations with configurable access controls |
| `git` | Read, search, and manipulate Git repositories |
| `github` | Repository management, file operations, GitHub API |
| `playwright` | Browser automation and web scraping |
| `context7` | Search library documentation and code examples |
| `fetch` | Web content fetching and conversion |
| `sequential_thinking` | Step-by-step reasoning for complex problems |
| `grep` (Vercel) | Search code patterns across GitHub repositories |
| `repo_map` | Project structure visualization and module tracing |
| `pubchem` | Chemical compound lookup — MW, logP, VP, ODT, CAS, structures |

### New

| Server | Config | Purpose |
|--------|--------|---------|
| `memory` | `npx -y @modelcontextprotocol/server-memory` | **Persistent knowledge graph across sessions.** Remembers formula iterations, material decisions, pipeline results. No more "what did we decide last time?" |

### How to use

Reference MCP servers by name in prompts:
```
use context7 to search for FastAPI query parameter documentation
use pubchem to find the vapor pressure of linalool
use memory to recall our last vetiver formula iteration
```

**Important:** MCP servers consume context tokens. Prefer built-in tools (`read`, `grep`, `glob`, `bash`) for simple operations. Use MCPs when they add concrete value.

---

## 3. Slash Commands

Type `/` in the TUI to see all available commands. Custom commands take arguments.

### Perfume Pipeline Commands

| Command | Arguments | What it does |
|---------|-----------|--------------|
| `/gate` | `<formula-file> <concentrate-uL> <brief-family>` | Full pipeline: inventory check → gate run → format analysis → present OAV table + perfumer analysis → append to formula file |
| `/audit` | `[brief-family]` | Historical formula scanning via `pipeline_audit.py` |
| `/analyze` | `[json-file]` | Format analysis from an existing pipeline JSON output |
| `/inventory` | _none_ | Read inventory.txt and produce structured summary: categories, depleted markers, dilutions, data gaps |

### Quality Commands

| Command | Arguments | What it does |
|---------|-----------|--------------|
| `/lint` | _none_ | CI-order linting: `ruff check app` → `mypy app` (Poetry environment) |
| `/test-backend` | _none_ | Backend tests with coverage: `poetry run pytest --cov=app` |
| `/test-engine` | _none_ | Engine tests: `pytest tests/` (pip environment) |

### Examples
```
/gate formulas/My_Formula_30mL_EDP.md 6000 vetiver_woody
/audit layton_dna
/lint
```

---

## 4. Agent Skills

Skills are reusable behavior units loaded on-demand via the `skill` tool. Agents see available skills and load full content when needed.

### `formula-gate` — Full Pipeline Workflow

**When to use:** Running any formula through the release gate pipeline.

**Covers:**
1. Pre-flight: read inventory.txt, verify all materials in stock, confirm family exists, verify ODT/physics/profile data, check for duplicate ODT entries
2. Run `scripts/formula_release_gate.py` with correct parameters
3. Run `scripts/format_pipeline_analysis.py` on output
4. Present OAV headspace table, temporal evolution, note distribution, and perfumer analysis
5. Append analysis to formula markdown file

**Rules enforced:** Never skip inventory, present OAV table before gates, append verbatim, flag OAV < 1 materials.

### `material-audit` — 4-Place Verification

**When to use:** Adding materials, debugging wrong OAV values, checking pipeline readiness.

**Checks 4 locations plus extras:**
1. `inventory.txt` — exists? dilution? depleted?
2. `data/materials/<LETTER>.yaml` — mw, logp, vp, odt_air, odt_eth, stock_dilution, in_inventory
3. `engine/ingredient_intelligence.py` — _PROFILES, _TYPICAL_DOSE, _ODOR_FAMILY_MAP, _ACTIVITY_COEF_MAP
4. `engine/odor_thresholds.py` — ODT_DATA entries, duplicate count
5. Alias check in `name_utils._ALIASES`

### `duplicate-odt-scanner` — ODT Data Quality

**When to use:** Before pipeline runs, after editing ODT_DATA, investigating 100M+ OAVs.

**Checks:** Parses ODT_DATA, counts key occurrences, flags duplicates with conflicting values, cross-references against inventory.txt (in-stock only), reports which value "wins" (last entry in file).

---

## 5. Custom Agents

Five perfume-domain subagents, each with:
- **Temperature 0.1** for deterministic research
- **Read-only** (edit: deny, bash: deny) — they only read inventory and write pairing JSON
- **Domain-specific prompts** covering material families, volatility, synergy, dosing, and IFRA

| Agent | Domain | Key competencies |
|-------|--------|------------------|
| `agent-citrus-top` | Citrus, green, top-note | Volatility matching, odor synergy, Schiff base conflicts, ester hydrolysis |
| `agent-floral-heart` | Floral, heart-note | Floral classification, hedione radiance, ionone diffusion, salicylate fixation |
| `agent-woody-base` | Woody, amber, base | Cedar/sandal/vetiver families, ISO E Super boosting, Ambroxan radiance |
| `agent-musk-fixative` | Musks, fixatives, gourmand, leather | Musk chord construction (depth/projection/character-echo), vanillin-coumarin warmth |
| `agent-spice-aromatic` | Spice, aromatic, specialty | Fougere triad, spice families, aldehydic construction, calone/ozonic |

### How to use

Invoke directly via `@mention`:
```
@agent-citrus-top evaluate bergamot + linalool + petitgrain pairing
```

Agents are also invoked automatically by the Task tool when primary agents delegate.

---

## 6. Plugin: `env-guard.js`

**Location:** `.opencode/plugins/env-guard.js`

**What it does:**
1. **Blocks reading** `.env` files (except `.env.example`) — `tool.execute.before` hook throws error
2. **Blocks writing** `.env` files — prevents accidental secret leakage
3. **Injects test env vars** — `OPENAI_API_KEY=test-key`, `SECRET_KEY=test-secret-key-for-ci` into all shell execution environments

**Why:** Your `AGENTS.md` and CI config reference these test keys. The plugin ensures agents in test mode always have the right environment without manual setup.

---

## 7. File Structure

```
.opencode/
  commands/
    gate.md              /gate <formula> <uL> <brief>
    audit.md             /audit [brief]
    analyze.md           /analyze [json-file]
    inventory.md         /inventory
    lint.md              /lint
    test-backend.md      /test-backend
    test-engine.md       /test-engine
  skills/
    formula-gate/SKILL.md         Full pipeline workflow skill
    material-audit/SKILL.md       4-place material verification skill
    duplicate-odt-scanner/SKILL.md ODT_DATA duplicate detection skill
  plugins/
    env-guard.js         .env protection + test env injection
  prompts/
    agent-citrus-top.txt
    agent-floral-heart.txt
    agent-woody-base.txt
    agent-musk-fixative.txt
    agent-spice-aromatic.txt

opencode.json            Core config (modified: +model, +instructions, +compaction,
                          +permission, +lsp, +formatter, +watcher, +memory MCP,
                          upgraded all 5 agent configs)
```

---

## 8. Quick Reference

### Pipeline workflow (old vs new)

**Before:**
```bash
# Step 1: Read inventory manually
# Step 2: Verify each material's ODT/physics/profile data
# Step 3: Run gate
python scripts/formula_release_gate.py --formula-file formulas/X.md --expected-concentrate-ul 6000 --brief vetiver_woody --json > output/result.json
# Step 4: Run analysis
python scripts/format_pipeline_analysis.py --input output/result.json
# Step 5: Manually append to formula file
```

**After:**
```
/gate formulas/X.md 6000 vetiver_woody
```

### Material verification

```
load skill material-audit
check geraniol
```

### Code quality

```
/lint
/test-backend
/test-engine
```

---

## 9. Best Practices

1. **Use `/gate` not manual pipeline runs** — it enforces inventory checks and proper formatting
2. **Use `sequential_thinking` before complex tasks** — your AGENTS.md recommends this for DeepSeek
3. **Use `context7` and `grep` for research** — not web search or raw grep
4. **Use `pubchem` for compound data** — MW, logP, VP, ODT lookups
5. **MCP servers consume tokens** — only invoke when they add unique value beyond built-in `read`/`grep`/`glob`
6. **Run `/inventory` before formulating** — AGENTS.md Rule 0 compliance
7. **Permissions protect secrets** — `.env` files are blocked, bash commands require approval for destructive operations

## 10. Windows Launcher Fix

If `opencode db` or `opencode models` errors with SQLite write failures on this machine, launch OpenCode through the repo wrapper:

```powershell
.\scripts\start_opencode.ps1
```

That wrapper pins `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, and `TMPDIR` into `D:\tmp`, which avoids the default user-profile state path problems in this environment.
