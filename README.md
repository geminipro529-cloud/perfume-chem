# Perfume Chemistry Workbench

Perfume Chemistry is a local-first formulation workbench for deterministic
bottle arithmetic, ppm/ODT/OAV analysis, evidence-labeled formula diagnostics,
and advisory release gates.

The primary application boundary is
[`engine.workbench.PerfumeWorkbench`](engine/workbench.py). Language-model
services are optional renderers and ideation tools; they are not the authority
for arithmetic, inventory, safety, or scientific classification.

## Truth Posture

Every canonical result uses one of six evidence classes:

- `EXACT`
- `LITERATURE_DERIVED`
- `EMPIRICALLY_CALIBRATED`
- `HEURISTIC`
- `SPECULATIVE`
- `UNKNOWN`

Current bottle mass balance is exact for stated inputs. Current headspace and
temporal evolution are heuristic. Canonical longevity, sillage, and receptor
activation are withheld rather than guessed.

This repository is a **Research Preview**. Passing verification means the
declared software and scientific-truth contracts are internally consistent; it
does not make modeled headspace a measurement, golden fixtures a sensory panel,
or the safety screen a regulatory certificate.

Read:

- [Scientific contract](docs/scientific_contract.md)
- [Model inventory](docs/model_inventory.md)
- [Fragrance family reference](docs/fragrance_families_reference.md)

## Phase 0 Verification

Run the bounded repository verifier from the root:

```powershell
.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify --json
```

For a fast truth-core and scientific-data pass:

```powershell
.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify --quick --json
```

Docker is optional locally and is never silently assumed:

```powershell
.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify --include-docker --json
```

Completion gates mean:

- `PASS`: the full canonical check set ran and passed without skips.
- `PASS_WITH_SKIPS`: the full canonical check set passed, but a declared
  optional environment check was skipped with a reason.
- `NOT_EVALUATED`: a quick, selected, or custom subset passed; this is useful
  evidence for that scope but is not a Phase 0 completion claim.
- `FAIL`: at least one selected required check failed.

Full-scope JSON evidence is written to
`verification_runs/project_verification.json`; non-full runs use a scope suffix
so they cannot replace canonical completion evidence. The report lists its
scope, selected checks, and omitted checks. CI runs the same named checks in
separate jobs and uploads JUnit, science-audit, package, and distribution artifacts.
Full legacy Ruff and backend mypy cleanup remain recorded debt;
canonical truth-core slices are blocking and may not expand their debt.

## Non-Negotiable Formulation Rules

1. Read [`inventory.txt`](inventory.txt) before constructing or modifying any
   fragrance. Stock, dilution, and availability are live data.
2. Preserve raw dose, active dose, ppm, ODT, and OAV. Perceptibility claims
   require OAV support.
3. Natural mixtures use composite constituent OAV where covered by the natural
   decomposition model.
   Composite OAV is an olfactory headspace model, not constituent composition
   for IFRA or allergen assessment.
4. Optimize for the perfume name and brief. Numerical gates are floors, not the
   creative target.
5. Missing density, physical data, calibration, or assay evidence remains
   unavailable and must not be silently defaulted in exact bottle arithmetic.

## What Is Canonical

| Need | Canonical path |
|---|---|
| Formula physical state and OAV table | `engine/pipeline/formula_state.py` |
| Temporal diagnostic frames | `engine/pipeline/simulator.py` |
| Evidence-labeled application service | `engine/workbench.py` |
| Exact bottle addition | `engine/bottle_addition.py` |
| Scientific class vocabulary | `engine/scientific_contract.py` |
| Release-gate CLI | `scripts/formula_release_gate.py` |
| FastAPI adapter | `backend/app/api/v1/endpoints/formulas.py` |

## Setup

Requirements:

- Python 3.11 or newer
- Poetry 2.x for the backend
- Docker Compose only if using containers

### Engine

Install the lightweight workbench package:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
```

The root `requirements.txt` contains the larger optional modeling and retrieval
stack. Install it only when those modules are needed:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Backend

The backend has an editable Poetry dependency on the root engine package:

```powershell
cd backend
..\.venv\Scripts\python.exe -m poetry env use ..\.venv\Scripts\python.exe
..\.venv\Scripts\python.exe -m poetry install --with dev
..\.venv\Scripts\python.exe -m poetry run uvicorn app.main:app --reload
```

From a shared environment that already contains backend dependencies, the root
launcher is also available:

```powershell
.venv\Scripts\python.exe run_api_server.py
```

API documentation is served at `http://localhost:8000/docs`.

### Docker

The Compose build context is the repository root so the backend can install the
engine path dependency and carry `data/materials` at runtime:

```powershell
docker compose up --build
```

The engine wheel also includes `data/materials`; packaging tests build and
install a non-editable wheel in isolation to prevent editable-checkout false
positives.

## Formula Analysis API

`POST /api/v1/formulas/analyze-formula` returns:

- canonical `formula_state`
- full `material_oav_table`
- note distribution
- temporal frames
- evidence class, basis, sources, assumptions, and limitations by claim
- `null` instead of unsupported longevity, sillage, or receptor predictions
- advisory validation warnings when applicable

### Concentrate Input

When no row has `role: "solvent"`, percentages describe the concentrate and are
scaled by `concentration_percent`:

```json
{
  "name": "Workbench example",
  "total_volume_ml": 30,
  "concentration_percent": 15,
  "ingredients": [
    {"name": "Hedione", "percentage": 60, "stock_active_fraction": 1.0},
    {"name": "Iso E Super", "percentage": 40, "stock_active_fraction": 1.0}
  ]
}
```

When solvent rows are present, all percentages describe the finished product.
The current aromatic state excludes those rows and discloses the omitted solvent
matrix as a limitation.

## Exact Bottle Addition API

`POST /api/v1/formulas/calculate-addition` solves the final mass balance while
accounting for material already in the bottle and mass added by the stock:

```json
{
  "bottle": {
    "total_mass_g": 30.0,
    "active_material_mass_g": 0.03,
    "total_mass_standard_uncertainty_g": 0.01,
    "active_mass_standard_uncertainty_g": 0.001
  },
  "stock": {
    "active_mass_fraction": 0.10,
    "density_g_ml": 1.0,
    "active_fraction_standard_uncertainty": 0.001,
    "density_standard_uncertainty_g_ml": 0.005
  },
  "target_active_mass_fraction": 0.002,
  "pipette": {
    "minimum_ul": 10,
    "increment_ul": 5,
    "maximum_single_step_ul": 200,
    "standard_uncertainty_ul": 1,
    "systematic_standard_uncertainty_ul": 0.5
  }
}
```

The response includes exact stock mass, propagated standard uncertainty, exact
volume when density is supplied, a rounded pipette plan when feasible, target
error in ppm, delivered-fraction standard uncertainty, claim-level evidence,
and before/addition/after mass ledgers. Random uncertainty is combined across
independent transfers; a declared shared systematic component is propagated as
fully correlated. No density means no volume plan; a subminimum volume is
reported infeasible rather than rounded upward.

## Release Pipeline

Before running a formula, verify inventory, family, and material data as
described in [`AGENTS.md`](AGENTS.md). Then run:

```powershell
.venv\Scripts\python.exe scripts\formula_release_gate.py `
  --formula-file formulas\My_Formula_30mL_EDP.md `
  --expected-concentrate-ul 6000 `
  --brief generic `
  --json
```

Format the complete OAV and temporal analysis with:

```powershell
.venv\Scripts\python.exe scripts\format_pipeline_analysis.py --input output.json
```

Gate status is advisory. Review the material OAV table, note distribution,
temporal frames, data provenance, IFRA details, and limitations before making a
formulation decision.

## Tests

Focused canonical engine tests:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests\test_scientific_contract.py `
  tests\test_bottle_addition.py `
  tests\test_receptor_evidence_quarantine.py `
  tests\test_workbench.py -q
```

Backend CI order:

```powershell
cd backend
..\.venv\Scripts\python.exe -m poetry run ruff check app
..\.venv\Scripts\python.exe -m poetry run mypy `
  app/core/config.py app/core/security.py app/schemas --ignore-missing-imports
..\.venv\Scripts\python.exe -m poetry run pytest tests -q
```

The repository currently has known legacy Ruff and mypy debt outside the
canonical engine/API slices. Runtime shards and changed-module static checks are
the enforced evidence for this Research Preview increment; see the model
inventory for the exact boundary.
