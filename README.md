# Perfume Chemistry API

AI-powered perfume chemistry and formulation platform with advanced fragrance analysis, formula creation, and IFRA compliance checking.

## Model Setup

Model IDs, local-path conventions, and env-file lookup rules are documented in [docs/MODEL_LOCATIONS.md](docs/MODEL_LOCATIONS.md).

Short version:

- Root `.env` is used when you run `python run_api_server.py` from the repo root.
- `backend/.env` is used when you start Uvicorn from inside `backend/`.
- `HF_LOCAL_MODEL_PATH` must point to a local Transformers model directory.
- `LLAMA_CPP_MODEL_PATH` must point to a local `.gguf` file.
- `OLLAMA_MODEL` is only the served model name, not a repo file path.

## Features

- 🧪 **Chemical Calculations**: Dilution, concentration, and volume conversions
- 🤖 **AI-Powered Analysis**: OpenAI-driven perfume composition analysis
- 📊 **Formula Management**: Create, analyze, and optimize fragrance formulas
- ✅ **IFRA Compliance**: Automatic safety guideline checking
- 🎯 **Note Distribution**: Analyze top, heart, and base note balance
- 💰 **Cost Estimation**: Calculate formula costs
- 🔍 **Ingredient Database**: Comprehensive chemical compound library

## 📦 Inventory

> **⚠️ RULE: Read [`inventory.txt`](inventory.txt) before constructing ANY fragrance.**  
> Materials, dilutions, and stock levels change. Never assume availability. Verify every material against the live inventory file before dosing.

> **⚠️ RULE: Optimize for the name, not just the numbers.**  
> When asked to optimize, enhance, or modify a formula, the target is the **name / concept / original brief** of the perfume — not numerical scores. The name is the north star. Numerical gates are floors to meet, not ceilings to chase.

> **⚠️ RULE: All perfume calculations must use ppm, ODT, and OAV.**  
> Concentrations are in **ppm** (parts per million w/w in concentrate). Odor detection thresholds are **ODT** (ppm for ethanol solution, ppb for air). Odor Activity Value is **OAV = concentration_ppm / ODT_ppm**. Every formula dose must be convertible to ppm, every threshold check must reference ODT, and every perceptibility claim must be backed by OAV. No exceptions.

**Current Materials: 104** (Updated 2026-03-09)  
📄 **[View Full Inventory →](inventory.txt)**

### By Category

| Category | Count | Notes |
|----------|-------|-------|
| **Citrus / Top Notes** | 14 | Citral, Citronellal, D-Limonene, Linalool, Aldehydes C10-C12, Bergamot, etc. |
| **Woods / Amber** | 16 | Iso E Super, Ambrox Super 30%, Cedramber, Amber Xtreme, Vertofix Coeur, etc. |
| **Floral** | 11 | Hedione, Hydroxycitronellal, Phenethyl Alcohol, Heliotropin, Florol, etc. |
| **Iris / Violet** | 10 | Alpha Irone 10%, Methyl Ionone, Orivone, Molecule Iris, ORRIS F-TEC, etc. |
| **Musks** | 10 | Galaxolide 100%, Romandolide, Habanolide, Ethylene Brassylate, Exaltolide, etc. |
| **Green / Fresh** | 8 | Dihydromyrcenol, cis-3-Hexenol, Verdox, Calone 1%, Floralozone, etc. |
| **Naturals** | 8 | Cedarwood EO, Vetiver EO, Lavender EO, Patchouli EO, Labdanum Abs, etc. |
| **Sweet / Gourmand** | 7 | Ethyl Maltol, Coumarin 20%, Vanillin, Maple Lactone, Benzoin, etc. |
| **Accord Bases / FTECs** | 7 | Black Pepper, Blackcurrant, Cardamom, Pink Pepper, Violet Fleuressence, etc. |
| **Solvents / Carriers** | 5 | Ethanol 96%, DPG, IPM, TEC, DEP |
| **Leather / Smoky** | 4 | IBQ, Birch Tar, Styrax FTEC, Guaiacol |
| **Fragrance Oils** | 4 | Jasmine FO, Leather FO, Tonka Bean FO, Sandalwood FO |

> See [inventory.txt](inventory.txt) for complete list with dilution details.

## Repository Structure

```
perfume-chem/
├── engine/                    Core scoring + optimizer + ingredient intelligence
│   ├── optimizer/             FormulaVector, FormulaScorer, FormulaOptimizer
│   ├── ingredient_intelligence/  Per-material profiles (10 dimensions)
│   ├── dose_response/         Hill / Stevens law dose models
│   ├── hedonic_model/         Pleasantness / liking predictions
│   ├── psychophysics/         γ(logP) VP weighting, ODT, OAV
│   ├── confidence.py          Formula confidence scoring
│   ├── inventory_parser.py    Parses inventory.txt → structured materials
│   └── chemical_data_validator.py
│
├── backend/                   FastAPI service (Poetry project)
├── frontend/                  UI
├── run_api_server.py          API entry point
│
├── engine/pipeline/            Formula release gates + OAV analysis (replaces pipelines/)
│
├── scripts/                   Small utility scripts
├── knowledge/                 Knowledge base (accord rules, fragrance facts)
├── data/                      Reference datasets
├── inventory.txt              ★ Current materials — read before formulating
│
├── formulas/                  Shipped formulas
│   ├── mixing_guides/         10 mL / 30 mL mixing guides
│   ├── collections/           Luxury / niche / masculine collections
│   └── reverse_engineering/   Opus V, Dior Homme Intense reconstructions
│
├── docs/                      Reference documentation
│   ├── references/            Scientific reference tables (A–Z)
│   ├── research/              Methodology + reverse-engineering research
│   ├── dosing_reference.md
│   ├── synergy_reference.md
│   ├── iris_synergy_reference.md
│   ├── perfumery_hacks_reference.md
│   ├── fragrance_families_reference.md
│   └── accord_quick_index.md
│
├── output/                    Runtime outputs (gitignored)
├── verification_runs/         Pipeline verification runs
└── archive/                   Scratch / experiments (gitignored)
    ├── scratch/               Throwaway `_*.py` diagnostic scripts
    ├── outputs/               Loose `*_out.txt` logs
    ├── json_runs/             Pipeline result JSON
    └── legacy_opus_v/         Superseded Opus V spreadsheets
```

### Pipeline Modules (engine/pipeline/)

| Module | Purpose |
|--------|---------|
| `engine/pipeline/formula_state.py` | Formula headspace state — OAV, mole fractions, activity coefficients |
| `engine/pipeline/gates.py` | Release gates — IFRA, pyramid, OAV authority, family drift |
| `engine/pipeline/simulator.py` | Temporal evolution — 5-window OAV simulation |
| `engine/pipeline/oav_intelligence.py` | OAV balance reports, performance projection, cliff detection |
| `engine/pipeline/oav_authority.py` | OAV confidence scoring + data quality assessment |
| `engine/pipeline/natural_absolute_decomposition.py` | Composite OAV for 35+ natural mixtures |
| `engine/pipeline/release_scoring.py` | Final release scoring + recommendations |
| `engine/pipeline/preflight.py` | Pre-gate validation — inventory, data completeness |
| `engine/pipeline/interventions.py` | Formula interventions — dosing, rebalancing |
| `engine/pipeline/robustness.py` | Robustness testing — dilution, temperature, aging |
| `engine/pipeline/audit_log.py` | Pipeline audit logging |
| `engine/pipeline/analysis.py` | Post-gate analysis formatting |

**Entry point**: `scripts/formula_release_gate.py` — orchestrates all engine/pipeline/ modules.

## Quick Start

### Prerequisites

| Tool | Version | Path |
|------|---------|------|
| Python 3.12 | 3.12.0 | `.venv\Scripts\python.exe` |
| Node.js | 26.3.0 | `C:\Program Files\nodejs\node.exe` |
| npm | 11.16.0 | `C:\Program Files\nodejs\npm.cmd` |
| Poetry | 2.4.1 | via `.venv\Scripts\python.exe -m poetry` |
| GitHub CLI | 2.95.0 | `C:\Program Files\GitHub CLI\gh.exe` |
| oh-my-opencode | 4.11.1 | `%APPDATA%\npm\oh-my-opencode.cmd` |
| OpenCode CLI | 1.17.8 | `%APPDATA%\npm\lildax.cmd` (alias: `opencode`) |
| AST-Grep | 0.43.0 | `%APPDATA%\npm\sg.cmd` |
| Ollama | — | `D:\ollama\ollama` |

### One-Command Setup

Run the startup script from the repo root:

```powershell
.\opencode-startup.ps1
```

This checks/installs: Node.js → npm → `@opencode-ai/cli` → `oh-my-opencode` → Python venv → copies node.exe for CLI wrapper compatibility.

### Manual Setup

#### 1. Python Virtual Environment

```powershell
# Create venv (one-time)
python -m venv .venv

# Install engine dependencies
.venv\Scripts\pip install -r requirements.txt

# Install backend dependencies
cd backend
..\.venv\Scripts\python -m poetry install
cd ..
```

#### 2. Node.js + OpenCode CLI

```powershell
# Install OpenCode v2 CLI
C:\Program Files\nodejs\npm.cmd install -g @opencode-ai/cli

# Create 'opencode' alias for 'lildax'
copy "$env:APPDATA\npm\lildax.cmd" "$env:APPDATA\npm\opencode.cmd"

# Copy node.exe for CLI wrapper (fixes PATH issues)
copy "C:\Program Files\nodejs\node.exe" "$env:APPDATA\npm\node.exe"
```

#### 3. oh-my-opencode (Agent Harness)

```powershell
npm install -g oh-my-opencode
oh-my-opencode install --no-tui --platform=opencode --claude=no --openai=no --gemini=no --copilot=yes --opencode-zen=no --skip-auth
```

#### 4. Environment Variables

Copy and edit:

```powershell
copy .env.example .env
# Edit .env with your API keys
# See backend/.env.example for full options
```

**Key vars in `.env`:**
- `AI_PROVIDER=deepseek`
- `DEEPSEEK_API_KEY=sk-...` (already set)
- `GITHUB_TOKEN=github_pat_...` (for GitHub MCP)

#### 5. Run the API

```powershell
python run_api_server.py
```

Or with auto PATH:

```powershell
$env:PATH = "C:\Program Files\nodejs;C:\Program Files\GitHub CLI;.venv\Scripts;$env:PATH"
python run_api_server.py
```

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Using Docker

```powershell
docker compose up -d
docker compose logs -f
docker compose down
```

## OpenCode + oh-my-opencode

This workspace uses **oh-my-opencode** (v4.11.1) as the agent orchestration layer over **OpenCode CLI** (v2, binary: `lildax`).

### Available Commands

| Command | What it does |
|---------|--------------|
| `oh-my-opencode --help` | Agent harness help |
| `omo run <message>` | Run with todo/background task enforcement |
| `omo doctor` | Check environment health |
| `lildax serve` | Start OpenCode v2 API server |
| `lildax --version` | Show version |

### Slash Commands (in OpenCode TUI)

| Command | Arguments | Action |
|---------|-----------|--------|
| `/gate` | `<formula> <uL> <brief>` | Run pipeline + analysis |
| `/audit` | `[brief]` | Historical formula scanning |
| `/inventory` | — | Read inventory.txt summary |
| `/lint` | — | `ruff check` + `mypy` |
| `/test-engine` | — | `pytest tests/` |
| `/test-backend` | — | `pytest --cov=app` |

## API Endpoints

### Formula Calculations

- `POST /api/v1/formulas/calculate-dilution` - Calculate dilution
- `GET /api/v1/formulas/drops-to-ml/{drops}` - Convert drops to ml
- `GET /api/v1/formulas/ml-to-drops/{volume}` - Convert ml to drops
- `POST /api/v1/formulas/analyze-formula` - Analyze formula properties

### AI Services

- `POST /api/v1/ai/analyze-perfume` - AI perfume analysis
- `POST /api/v1/ai/suggest-modifications` - Get formula improvement suggestions
- `POST /api/v1/ai/suggest-pairings` - Get ingredient pairing recommendations

## Development

### Run Tests

```bash
cd backend
poetry run pytest
```

### Run with Coverage

```bash
poetry run pytest --cov=app --cov-report=html
```

### Linting

```bash
poetry run ruff check app
poetry run black app
```
- `suggest` - Get AI recommendations
- `save` - Export formula
- `help` - Show all commands

## Rules Engine

Every formula is validated against:
- **Chemistry**: Solubility, concentration limits, pH compatibility, oxidation risk
- **IFRA**: Maximum usage levels, restricted materials, prohibited substances
- **Artistry**: Top/heart/base balance, accord coherence, longevity prediction
