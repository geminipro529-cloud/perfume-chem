# Perfume Workbench Truth Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one evidence-labeled formula-analysis service and an exact mass-balance bottle-addition calculator, then expose both through the backend without speculative receptor predictions.

**Architecture:** `engine.workbench.PerfumeWorkbench` is the application boundary. It delegates formula physics to the existing canonical `FormulaState`/simulator path and bottle corrections to a new independent `AdditionSolver`; backend routes only validate, adapt, and serialize. Scientific classifications travel with every result so current heuristic headspace and temporal models cannot be mistaken for measurements.

**Tech Stack:** Python 3.11+, dataclasses, Pydantic 2.12, FastAPI, pytest, Poetry, Docker Compose.

---

## File Map

- Create `engine/scientific_contract.py`: output classification and evidence metadata.
- Create `engine/bottle_addition.py`: exact bottle arithmetic, uncertainty, pipette rounding, and mass ledger.
- Create `engine/workbench.py`: canonical application service.
- Modify `engine/pipeline/simulator.py`: stop emitting family-proxy receptor numbers.
- Modify `backend/app/schemas/chemical.py`: stock and exact-addition request schemas.
- Modify `backend/app/schemas/perfume.py`: Pydantic 2 validators and formula stock metadata.
- Modify `backend/app/core/models_config.py`: Pydantic 2 validator compatibility.
- Modify `backend/app/api/v1/endpoints/formulas.py`: workbench adapter and exact-addition endpoint.
- Create `pyproject.toml`: installable lightweight root engine package.
- Modify `backend/pyproject.toml` and `backend/poetry.lock`: local engine dependency.
- Modify `backend/Dockerfile` and `docker-compose.yml`: root build context and engine/data runtime.
- Create `docs/scientific_contract.md` and `docs/model_inventory.md`: permanent truth posture.
- Create focused engine/backend tests for each contract.

### Task 1: Restore Pydantic 2.12 Schema Compatibility

**Files:**
- Create: `backend/tests/unit/test_schema_compatibility.py`
- Modify: `backend/app/schemas/perfume.py`
- Modify: `backend/app/core/models_config.py`

- [ ] **Step 1: Write the failing schema import and validation tests**

```python
from app.core.models_config import ModelConfig
from app.schemas.perfume import FormulaCreate


def test_formula_schema_imports_and_validates_balanced_formula():
    formula = FormulaCreate(
        name="Schema smoke",
        ingredients=[
            {"name": "Hedione", "percentage": 60.0},
            {"name": "Iso E Super", "percentage": 40.0},
        ],
    )
    assert formula.name == "Schema smoke"


def test_model_config_rejects_non_iso_date():
    field = ModelConfig.model_fields["last_validated"]
    assert field is not None
```

- [ ] **Step 2: Run the import test and confirm the existing failure**

Run: `cd backend; $env:PYTHONPATH='..'; ..\.venv\Scripts\python.exe -m pytest tests/unit/test_schema_compatibility.py -q`

Expected: import fails with Pydantic's ``@validator` cannot be applied to instance methods`` error.

- [ ] **Step 3: Convert deprecated validators to Pydantic 2 field validators**

Use `from pydantic import BaseModel, Field, field_validator`, then apply:

```python
@field_validator("ingredients")
@classmethod
def validate_formula_balance(cls, value):
    total = sum(ingredient.percentage for ingredient in value)
    if not (99.0 <= total <= 101.0):
        raise ValueError(f"Formula must sum to 100%, got {total}%")
    return value
```

Apply the same classmethod pattern to `PerfumeCreate.ingredients` and `ModelConfig.last_validated`.

- [ ] **Step 4: Run the schema and API import smoke tests**

Run: `cd backend; $env:PYTHONPATH='..'; ..\.venv\Scripts\python.exe -m pytest tests/unit/test_schema_compatibility.py tests/integration/test_api_endpoints.py::test_root_endpoint -q`

Expected: PASS.

- [ ] **Step 5: Commit the compatibility fix**

```powershell
git add backend/app/schemas/perfume.py backend/app/core/models_config.py backend/tests/unit/test_schema_compatibility.py
git commit -m "fix: restore pydantic schema compatibility"
```

### Task 2: Add Scientific Output Contracts

**Files:**
- Create: `engine/scientific_contract.py`
- Create: `tests/test_scientific_contract.py`

- [ ] **Step 1: Write failing classification serialization tests**

```python
from engine.scientific_contract import EvidenceDescriptor, ScientificClass


def test_evidence_descriptor_serializes_truth_posture():
    evidence = EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis="aromatic-only mole fraction with fallback activity coefficients",
        sources=("engine.pipeline.formula_state",),
        assumptions=("finished solvent matrix not represented",),
        limitations=("not a measured headspace concentration",),
    )
    payload = evidence.as_dict()
    assert payload["classification"] == "HEURISTIC"
    assert payload["sources"] == ["engine.pipeline.formula_state"]
```

- [ ] **Step 2: Run the focused test and verify missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scientific_contract.py -q`

Expected: FAIL with `ModuleNotFoundError: engine.scientific_contract`.

- [ ] **Step 3: Implement the stable vocabulary and immutable descriptor**

```python
class ScientificClass(str, Enum):
    EXACT = "EXACT"
    LITERATURE_DERIVED = "LITERATURE_DERIVED"
    EMPIRICALLY_CALIBRATED = "EMPIRICALLY_CALIBRATED"
    HEURISTIC = "HEURISTIC"
    SPECULATIVE = "SPECULATIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EvidenceDescriptor:
    classification: ScientificClass
    basis: str
    sources: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "basis": self.basis,
            "sources": list(self.sources),
            "assumptions": list(self.assumptions),
            "limitations": list(self.limitations),
        }
```

- [ ] **Step 4: Run the contract tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scientific_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the scientific vocabulary**

```powershell
git add engine/scientific_contract.py tests/test_scientific_contract.py
git commit -m "feat: add scientific output contracts"
```

### Task 3: Build the Exact Bottle-Addition Solver

**Files:**
- Create: `engine/bottle_addition.py`
- Create: `tests/test_bottle_addition.py`

- [ ] **Step 1: Write failing exact-arithmetic and conservation tests**

```python
import pytest

from engine.bottle_addition import (
    AdditionRequest,
    AdditionSolver,
    BottleSnapshot,
    PipetteProfile,
    StockSolution,
)


def test_reach_target_accounts_for_existing_active_mass_and_added_stock_mass():
    request = AdditionRequest(
        bottle=BottleSnapshot(total_mass_g=30.0, active_material_mass_g=0.03),
        stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
        target_active_mass_fraction=0.002,
        pipette=PipetteProfile(minimum_ul=10.0, increment_ul=5.0, maximum_single_step_ul=200.0),
    )
    result = AdditionSolver().reach_target_active_fraction(request)
    assert result.exact_stock_mass_g == pytest.approx(0.30612244898)
    assert result.exact_stock_volume_ul == pytest.approx(306.12244898)
    assert result.mass_ledger["after"]["total_mass_g"] == pytest.approx(
        result.mass_ledger["before"]["total_mass_g"]
        + result.mass_ledger["addition"]["stock_mass_g"]
    )
    assert sum(result.staged_additions_ul) == result.rounded_stock_volume_ul


def test_missing_density_preserves_mass_result_but_withholds_volume_plan():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=0.2),
            target_active_mass_fraction=0.01,
        )
    )
    assert result.exact_stock_mass_g > 0
    assert result.exact_stock_volume_ul is None
    assert result.pipette_feasible is False
```

- [ ] **Step 2: Add failing adversarial and uncertainty tests**

```python
def test_target_below_current_fraction_is_not_an_additive_operation():
    with pytest.raises(ValueError, match="below current"):
        AdditionSolver().reach_target_active_fraction(
            AdditionRequest(
                bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.2),
                stock=StockSolution(active_mass_fraction=0.1, density_g_ml=1.0),
                target_active_mass_fraction=0.01,
            )
        )


def test_target_must_be_lower_than_stock_fraction():
    with pytest.raises(ValueError, match="stock"):
        AdditionSolver().reach_target_active_fraction(
            AdditionRequest(
                bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
                stock=StockSolution(active_mass_fraction=0.1, density_g_ml=1.0),
                target_active_mass_fraction=0.1,
            )
        )


def test_subminimum_addition_is_reported_as_infeasible():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=1.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=1.0, density_g_ml=1.0),
            target_active_mass_fraction=0.000001,
            pipette=PipetteProfile(minimum_ul=10.0, increment_ul=1.0),
        )
    )
    assert result.pipette_feasible is False
    assert result.rounded_stock_volume_ul is None


def test_solver_is_scale_invariant():
    solver = AdditionSolver()
    small = solver.reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.01),
            stock=StockSolution(active_mass_fraction=0.1),
            target_active_mass_fraction=0.002,
        )
    )
    large = solver.reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=100.0, active_material_mass_g=0.1),
            stock=StockSolution(active_mass_fraction=0.1),
            target_active_mass_fraction=0.002,
        )
    )
    assert large.exact_stock_mass_g == pytest.approx(10 * small.exact_stock_mass_g)
```

- [ ] **Step 3: Run the tests and verify the module is absent**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_bottle_addition.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement validated immutable input types**

Implement `BottleSnapshot`, `StockSolution`, `PipetteProfile`, `AdditionRequest`, `AdditionResult`, and `AdditionCalculationError`. Validate all fractions and quantities in `__post_init__`; never provide a default density or pipette precision.

- [ ] **Step 5: Implement exact mass balance and uncertainty propagation**

Use:

```python
numerator = target * bottle.total_mass_g - bottle.active_material_mass_g
denominator = stock.active_mass_fraction - target
stock_mass_g = numerator / denominator
```

Propagate standard uncertainty with the analytic partial derivatives of `x = (tM - m_a)/(s - t)` and, when density exists, `v = 1000*x/rho`. Attach an `EXACT` arithmetic evidence descriptor while distinguishing measured input uncertainty from algebraic exactness.

- [ ] **Step 6: Implement pipette rounding and staging**

Round to the nearest declared increment. If the rounded dose is below `minimum_ul`, mark it infeasible and return no staged plan. Otherwise split integer increment units across the minimum number of steps that respect `maximum_single_step_ul`.

- [ ] **Step 7: Run the solver tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_bottle_addition.py -q`

Expected: PASS.

- [ ] **Step 8: Commit the solver**

```powershell
git add engine/bottle_addition.py tests/test_bottle_addition.py
git commit -m "feat: add exact bottle addition solver"
```

### Task 4: Quarantine Unsupported Receptor Predictions

**Files:**
- Modify: `engine/pipeline/simulator.py`
- Create: `tests/test_receptor_evidence_quarantine.py`

- [ ] **Step 1: Write the failing production-output test**

```python
from engine.pipeline.simulator import simulate_formula


def test_simulation_does_not_emit_family_proxy_receptor_numbers():
    frame = simulate_formula({"Hedione": 1000.0}, windows=(("opening", 0.0),))[0]
    payload = frame.as_dict()
    assert payload["receptor_activation"] is None
    assert payload["receptor_source"] == "unavailable:material_specific_assay_required"
```

- [ ] **Step 2: Run the test and observe the current family-prior output**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_receptor_evidence_quarantine.py -q`

Expected: FAIL because `receptor_activation` contains numerical proxy values.

- [ ] **Step 3: Remove proxy computation from the production simulator**

Delete the simulator imports of `ligands_from_family` and `or_occupancy`, remove `_receptor_activation`, make `SimulationFrame.receptor_activation` optional, and use the permanent unavailable source label. Keep `engine/receptor/binding.py` as an explicitly exploratory module; do not use it in scoring or simulation.

- [ ] **Step 4: Run receptor and pipeline-state tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_receptor_evidence_quarantine.py tests/test_pipeline_formula_state.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the quarantine**

```powershell
git add engine/pipeline/simulator.py tests/test_receptor_evidence_quarantine.py
git commit -m "fix: quarantine unsupported receptor predictions"
```

### Task 5: Add the Canonical PerfumeWorkbench Service

**Files:**
- Create: `engine/workbench.py`
- Create: `tests/test_workbench.py`

- [ ] **Step 1: Write failing deterministic-analysis tests**

```python
from engine.bottle_addition import AdditionRequest, BottleSnapshot, StockSolution
from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest


def test_workbench_analysis_exposes_canonical_state_and_truth_labels():
    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Workbench smoke",
            ingredients_ul={"Hedione": 1000.0, "Iso E Super": 1000.0},
            dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
            batch_volume_ml=10.0,
        )
    )
    payload = result.as_dict()
    assert payload["formula_state"]["total_raw_ul"] == 2000.0
    assert payload["evidence"]["headspace"]["classification"] == "HEURISTIC"
    assert payload["evidence"]["threshold_visibility"]["classification"] in {
        "LITERATURE_DERIVED", "HEURISTIC"
    }
    assert payload["time_series"][0]["receptor_activation"] is None


def test_workbench_delegates_exact_addition():
    workbench = PerfumeWorkbench()
    result = workbench.calculate_addition(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=30.0, active_material_mass_g=0.03),
            stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
            target_active_mass_fraction=0.002,
        )
    )
    assert result.evidence.classification.value == "EXACT"
```

- [ ] **Step 2: Run the tests and verify missing service failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_workbench.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement request/result types and orchestration**

`PerfumeWorkbench.analyze()` calls `build_formula_state()` once and passes the state to `simulate_formula(initial_state=state)`. The result includes canonical state, full time series, note distribution, evidence descriptors, assumptions, and limitations. `calculate_addition()` delegates directly to `AdditionSolver`.

- [ ] **Step 4: Run workbench and canonical engine tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_workbench.py tests/test_pipeline_formula_state.py tests/test_pipeline_interventions.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the workbench**

```powershell
git add engine/workbench.py tests/test_workbench.py
git commit -m "feat: add canonical perfume workbench service"
```

### Task 6: Route the Backend Through the Workbench

**Files:**
- Modify: `backend/app/schemas/chemical.py`
- Modify: `backend/app/api/v1/endpoints/formulas.py`
- Modify: `backend/tests/integration/test_api_endpoints.py`

- [ ] **Step 1: Replace the old API assertions with canonical contract assertions**

```python
@pytest.mark.asyncio
async def test_analyze_formula_uses_canonical_workbench(client, sample_formula):
    response = await client.post("/api/v1/formulas/analyze-formula", json=sample_formula)
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_engine"] == "engine.workbench.PerfumeWorkbench"
    assert "formula_state" in data
    assert "material_oav_table" in data
    assert data["evidence"]["headspace"]["classification"] == "HEURISTIC"
    assert data["estimated_longevity_hours"] is None
    assert data["estimated_sillage"] is None
```

Add an integration test for `POST /api/v1/formulas/calculate-addition` using the 30 g, 0.03 g active, 10% stock, 0.2% target example.

- [ ] **Step 2: Run the endpoint tests and observe missing canonical fields**

Run: `cd backend; $env:PYTHONPATH='..'; ..\.venv\Scripts\python.exe -m pytest tests/integration/test_api_endpoints.py -q`

Expected: FAIL on `analysis_engine` and missing addition route.

- [ ] **Step 3: Extend request schemas without breaking old clients**

Add optional `stock_active_fraction` and `stock_density_g_ml` to `FormulaIngredient`. Add Pydantic request models for bottle mass, current active mass, stock fraction/density, target fraction, and optional pipette profile.

- [ ] **Step 4: Replace endpoint calculations with adapter logic**

The endpoint separates `role == "solvent"` rows, converts non-solvent percentages to microlitres on either the explicit finished-formula basis or concentrate basis, records every default in `assumptions`, invokes `PerfumeWorkbench.analyze()`, and attaches existing advisory validation. It must not call `calculate_note_distribution`, `estimate_longevity`, or `estimate_sillage`.

- [ ] **Step 5: Add the exact-addition endpoint**

Convert the Pydantic request to `AdditionRequest`, call `PerfumeWorkbench.calculate_addition()`, return `result.as_dict()`, and convert `AdditionCalculationError` to HTTP 400.

- [ ] **Step 6: Run backend integration and unit tests**

Run: `cd backend; $env:PYTHONPATH='..'; ..\.venv\Scripts\python.exe -m pytest tests -q`

Expected: PASS.

- [ ] **Step 7: Commit the API bridge**

```powershell
git add backend/app/schemas/chemical.py backend/app/api/v1/endpoints/formulas.py backend/tests/integration/test_api_endpoints.py
git commit -m "feat: route formula API through perfume workbench"
```

### Task 7: Make the Shared Engine a Real Runtime Dependency

**Files:**
- Create: `pyproject.toml`
- Modify: `backend/pyproject.toml`
- Modify: `backend/poetry.lock`
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `run_api_server.py`
- Create: `backend/tests/unit/test_engine_packaging.py`

- [ ] **Step 1: Write a backend import smoke test**

```python
def test_backend_imports_canonical_workbench_from_installed_engine():
    from engine.workbench import PerfumeWorkbench

    assert PerfumeWorkbench.__module__ == "engine.workbench"
```

- [ ] **Step 2: Add root package metadata**

Create a setuptools PEP 621 project named `perfume-chem-engine`, include namespace packages matching `engine*`, require Python 3.11+, and declare only `PyYAML>=6.0` for the lightweight workbench path.

- [ ] **Step 3: Add the backend path dependency and regenerate the lock**

Add:

```toml
perfume-chem-engine = {path = "..", develop = true}
```

Run: `cd backend; ..\.venv\Scripts\python.exe -m poetry lock`

Expected: lock succeeds and records the local directory dependency.

- [ ] **Step 4: Install and verify the backend environment**

Run: `cd backend; ..\.venv\Scripts\python.exe -m poetry install --with dev`

Run: `cd backend; ..\.venv\Scripts\python.exe -m poetry run pytest tests/unit/test_engine_packaging.py -q`

Expected: PASS without setting `PYTHONPATH`.

- [ ] **Step 5: Update Docker to use the repository root context**

Set Compose `build.context` to `.` and `dockerfile` to `backend/Dockerfile`. In the Dockerfile, copy root package metadata, `engine/`, `data/`, and backend lock files before installing; copy backend application files afterward. Use an in-project virtual environment copied into the runtime stage.

- [ ] **Step 6: Remove `sys.path` mutation from the launcher**

Import `uvicorn` and run `app.main:app` after changing the process working directory to `backend`, relying on the installed engine package rather than injecting paths.

- [ ] **Step 7: Verify package and Compose configuration**

Run: `cd backend; ..\.venv\Scripts\python.exe -m poetry check`

Run: `docker compose config`

If Docker is available, run: `docker compose build api`

Expected: package check and Compose config pass; image build passes when Docker daemon is available.

- [ ] **Step 8: Commit packaging and runtime changes**

```powershell
git add pyproject.toml backend/pyproject.toml backend/poetry.lock backend/Dockerfile docker-compose.yml run_api_server.py backend/tests/unit/test_engine_packaging.py
git commit -m "build: package engine for backend runtime"
```

### Task 8: Document the Truth Boundary and Verify the Whole Slice

**Files:**
- Create: `docs/scientific_contract.md`
- Create: `docs/model_inventory.md`
- Modify: `README.md`

- [ ] **Step 1: Write the scientific contract**

Document each classification, the mass-balance equation, ppm/ODT/OAV scope, receptor evidence requirements, and the rule that missing density or physical data remains unavailable rather than silently defaulted.

- [ ] **Step 2: Write the model inventory**

Classify current bottle arithmetic as `EXACT`, ODT-derived threshold visibility as mixed `LITERATURE_DERIVED/HEURISTIC`, headspace and temporal models as `HEURISTIC`, fixed hedonic values as `HEURISTIC`, family receptor profiles as `SPECULATIVE`, and calibration records as `EMPIRICALLY_CALIBRATED` only when held-out evidence exists.

- [ ] **Step 3: Update product identity and API examples**

Change the README framing from AI authority to local-first workbench, document `/analyze-formula` truth metadata and `/calculate-addition`, and link the scientific contract and model inventory.

- [ ] **Step 4: Run focused and broad verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_scientific_contract.py tests/test_bottle_addition.py tests/test_receptor_evidence_quarantine.py tests/test_workbench.py tests/test_pipeline_formula_state.py tests/test_pipeline_interventions.py -q
cd backend
..\.venv\Scripts\python.exe -m poetry run ruff check app
..\.venv\Scripts\python.exe -m poetry run mypy app --ignore-missing-imports
..\.venv\Scripts\python.exe -m poetry run pytest tests -q
```

Expected: all commands pass.

- [ ] **Step 5: Review the final diff and scientific labels**

Run:

```powershell
git diff --check
git status --short
rg -n "family_prior_proxy|estimate_longevity|estimate_sillage" engine/pipeline/simulator.py backend/app/api/v1/endpoints/formulas.py
```

Expected: no whitespace errors; the two untracked root planning notes remain untouched; no production receptor proxy or old API estimate call remains.

- [ ] **Step 6: Commit documentation**

```powershell
git add docs/scientific_contract.md docs/model_inventory.md README.md
git commit -m "docs: define perfume workbench scientific contract"
```
