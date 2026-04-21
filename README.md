# Perfume Chemistry API

AI-powered perfume chemistry and formulation platform with advanced fragrance analysis, formula creation, and IFRA compliance checking.

## Features

- 🧪 **Chemical Calculations**: Dilution, concentration, and volume conversions
- 🤖 **AI-Powered Analysis**: OpenAI-driven perfume composition analysis
- 📊 **Formula Management**: Create, analyze, and optimize fragrance formulas
- ✅ **IFRA Compliance**: Automatic safety guideline checking
- 🎯 **Note Distribution**: Analyze top, heart, and base note balance
- 💰 **Cost Estimation**: Calculate formula costs
- 🔍 **Ingredient Database**: Comprehensive chemical compound library

## 📦 Inventory

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
├── pipelines/                 Pipeline entry points (depth-1 orchestrators)
│   ├── accord_pipeline.py
│   ├── luxury_niche_pipeline.py
│   ├── luxury_v2_pipeline.py
│   ├── masculine_luxury_pipeline.py
│   ├── niche_discovery_pipeline.py
│   ├── niche_ideas_pipeline.py
│   ├── niche_texture_collection.py
│   ├── run_opus_v_pipeline.py
│   ├── iris_cathedral_formula.py
│   ├── opus_v/                Opus V reverse-engineering + temporal modules
│   ├── temporal/              Temporal-release formula simulators
│   ├── analysis/              Scoring / rating / ODT analysis
│   └── utilities/             Knowledge dump + xlsx extract helpers
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

### Pipeline Entry Points

| Pipeline | Purpose |
|----------|---------|
| `pipelines/accord_pipeline.py` | Generate + score accord-level compositions |
| `pipelines/luxury_niche_pipeline.py` | Luxury niche formula discovery |
| `pipelines/luxury_v2_pipeline.py` | Luxury V2 (γ-weighted photorealism) |
| `pipelines/masculine_luxury_pipeline.py` | Masculine luxury discovery |
| `pipelines/niche_discovery_pipeline.py` | Broad niche accord exploration |
| `pipelines/niche_ideas_pipeline.py` | Concept-seeded niche ideas |
| `pipelines/niche_texture_collection.py` | Texture-driven niche collection |
| `pipelines/run_opus_v_pipeline.py` | Opus V reconstruction pipeline |
| `pipelines/iris_cathedral_formula.py` | Iris cathedral architectural formula |
| `pipelines/opus_v/opus_v_analyzer.py` | Opus V module-level analysis |
| `pipelines/opus_v/opus_v_bayesian_reconstruction.py` | Bayesian Opus V reconstruction |
| `pipelines/opus_v/opus_v_temporal_analysis.py` | Temporal release Opus V |
| `pipelines/temporal/aperture_iris_temporal.py` | Aperture Iris temporal simulator |
| `pipelines/temporal/porcelaine_poudree_temporal.py` | Porcelaine Poudrée temporal simulator |
| `pipelines/analysis/rate_all_formulas.py` | Batch-rate every formula in `formulas/` |
| `pipelines/analysis/score_iris.py` | Iris-specific scoring |
| `pipelines/analysis/analyze_formulas.py` | Multi-axis formula analysis |
| `pipelines/utilities/dump_knowledge.py` | Export knowledge graph |
| `pipelines/utilities/extract_knowledge_graph.py` | Build knowledge graph |

Each pipeline script self-registers the workspace root on `sys.path` and imports the live `engine/` modules.

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd perfume-chem
   ```

2. **Backend Setup**
   ```bash
   cd backend
   poetry install
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Run the API**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Interactive Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Using Docker

```bash
# Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env and add your OPENAI_API_KEY

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

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