# Perfume Workbench Truth Core Design

Date: 2026-07-15
Status: approved under the user's autonomous one-shot authorization

## Outcome

Build a truth-first vertical slice that turns the existing deterministic engine into the application authority for formula analysis and adds an exact, operator-facing bottle-addition solver. Preserve the current release pipeline, but expose each output with a scientific classification, provenance, assumptions, and limitations.

The slice must be useful without an LLM. It must not claim that OAV predicts liking, that heuristic evaporation predicts measured longevity, or that odor-family proxies predict receptor activation.

## Approaches Considered

### 1. Big-bang platform rewrite

Move all engine and backend code into a new domain/evidence/calculator/application hierarchy, replace every API and chat route, add solvent-inclusive thermodynamics, and migrate all persisted data at once.

Benefit: reaches the long-term architecture directly.

Cost and risk: very high. The engine contains broad heuristic and data dependencies, the backend is a separate Poetry environment, and current formula gates are already relied upon. A large migration would make changed scientific behavior difficult to attribute.

### 2. Exact calculator only

Add a mass-balance function and tests without changing the API or analysis architecture.

Benefit: low risk and immediate utility.

Cost and risk: leaves the application's two competing analysis paths intact and does not create a reusable scientific contract.

### 3. Truth-first vertical slice

Add a canonical `PerfumeWorkbench` service, scientific output classifications, typed bottle-addition inputs and results, an exact mass-balance solver, and route `/analyze-formula` through the workbench. Keep the existing OAV engine as the computational backend, but label its current headspace and temporal outputs according to their evidence posture. Remove family-proxy receptor values from production simulation output.

Benefit: high user value, high truth improvement, and unlocks later physical-model work without destabilizing formula-release behavior.

Decision: approach 3.

## Scope

### Included

- A stable scientific classification vocabulary:
  - `EXACT`
  - `LITERATURE_DERIVED`
  - `EMPIRICALLY_CALIBRATED`
  - `HEURISTIC`
  - `SPECULATIVE`
  - `UNKNOWN`
- A structured evidence descriptor attached to workbench outputs.
- Typed bottle, stock, target, pipette, and uncertainty inputs.
- Exact mass-fraction addition arithmetic that accounts for material already present and for the added stock increasing total mass.
- Density-based mass-to-volume conversion when density is supplied.
- Pipette rounding, feasibility, staged additions, rounding error, and a before/after mass ledger.
- A canonical `PerfumeWorkbench.analyze()` surface based on the existing formula-state and temporal engine.
- A canonical `PerfumeWorkbench.calculate_addition()` surface based on the exact solver.
- Backward-compatible `/analyze-formula` request parsing.
- Replacement of fixed note-percentage longevity and sillage values with structured canonical analysis plus compatibility fields explicitly marked heuristic/deprecated.
- Production quarantine of family-prior receptor activation. The simulator may report that receptor evidence is unavailable; it must not emit invented numerical receptor activation.
- A packaging/runtime bridge so the backend and Docker image use the same root engine code.
- Pydantic 2.12-compatible schema validators so backend tests can import the application.
- Scientific contract and model inventory documentation.

### Excluded

- A full UNIFAC, NRTL, or finite-film evaporation implementation.
- Silent solvent inference inside the existing release-gate pipeline.
- Universal pleasantness or mood prediction.
- A personalized Bradley-Terry model, pending sufficient paired observations.
- Full migration of AI, optimizer, and chat endpoints. They remain follow-up consumers of the workbench.
- New pipeline scripts, as prohibited by repository policy.

## Scientific Contracts

### Exact bottle addition

For current bottle mass `M`, current active target-material mass `m_a`, stock active mass fraction `s`, desired final active mass fraction `t`, and stock mass to add `x`:

```text
(m_a + s*x) / (M + x) = t
x = (t*M - m_a) / (s - t)
```

Preconditions:

- all masses are non-negative;
- `0 < s <= 1`;
- `0 <= t < s`;
- current active mass cannot exceed total bottle mass;
- the requested target cannot be below the current fraction for an additive operation;
- density must be positive when a volume result is requested.

The solver never silently assumes density. If density is absent, exact mass remains available and volume is unavailable.

### PPM, ODT, and OAV

The existing OAV calculation remains available and is identified as threshold-relative analysis. OAV supports a perceptibility-screening claim only when concentration, phase, threshold unit, and matrix are compatible. It is not evidence of pleasantness, mixture quality, or receptor activation.

The current formula-state headspace estimate is classified `HEURISTIC` because aromatic mole fractions omit an explicit finished solvent matrix and activity coefficients include heuristic fallbacks. Temporal estimates are also `HEURISTIC` until calibrated against measured evaporation or wear data.

### Receptor evidence

Numerical receptor activation requires an odorant-specific receptor, species, assay system, concentration unit, EC50 or equivalent response curve, efficacy, and source. Family labels and vapor ppm do not satisfy this contract. Until complete rows exist, production simulation reports no receptor prediction.

## Architecture

```text
API / CLI / future chat
        |
        v
PerfumeWorkbench
  |             |
  v             v
analyze      calculate_addition
  |             |
  v             v
FormulaState  AdditionSolver
  |
  v
temporal simulation without speculative receptor numbers
```

New domain modules remain small and independent:

- `engine/scientific_contract.py`: classifications and evidence descriptors.
- `engine/bottle_addition.py`: typed inputs, exact solver, ledgers, uncertainty, and staging.
- `engine/workbench.py`: application-facing orchestration only.

The backend endpoint is an adapter. It converts request percentages into a deterministic batch basis, delegates to `PerfumeWorkbench`, and serializes the result. It does not calculate note distribution, longevity, sillage, OAV, or bottle arithmetic itself.

## API Data Flow

For `/analyze-formula`:

1. Validate the request and 100% balance using Pydantic and the existing advisory validator.
2. Use `total_volume_ml` when supplied; otherwise use a documented 100 mL calculation basis.
3. Treat ingredients whose role is `solvent` as non-aromatic and report them in bottle composition.
4. Convert each non-solvent percentage to raw microlitres on the calculation basis.
5. Use optional `stock_active_fraction`; default to `1.0` only with an explicit `request_default` assumption in the output.
6. Run `PerfumeWorkbench.analyze()`.
7. Return formula state, OAV table, time windows, evidence descriptors, assumptions, and limitations.
8. Keep legacy response keys for one compatibility cycle, but classify them as deprecated heuristics and derive note distribution from the canonical state. Do not fabricate longevity hours or sillage labels; return `null` where the current model cannot support them.

## Error Handling

- Invalid units, fractions, densities, and impossible targets raise domain-specific `ValueError` subclasses.
- API adapters convert domain input errors to HTTP 400.
- Missing physical data remains visible in material `missing_fields` and evidence limitations.
- Missing density does not fail a mass calculation; it makes volume and pipette planning unavailable.
- Additions below pipette minimum are marked infeasible instead of being rounded up silently.
- Receptor evidence absence is represented as unavailable, not as zero activation.

## Packaging and Runtime

The backend must import the same `engine` package used by root tests. The runtime solution will:

- make the root engine installable as a local package;
- add it as a backend path dependency for development;
- build Docker from the repository root so engine and material data are available inside the image;
- remove the need for the API launcher to mutate `sys.path`.

Only the lightweight dependencies required by the workbench import path are mandatory for the backend. Heavy model dependencies remain optional and outside this slice.

## Testing

Test-first implementation will cover:

- exact addition algebra and conservation;
- target already reached;
- target below current concentration;
- target at or above stock concentration;
- density absent versus present;
- pipette rounding and sub-minimum infeasibility;
- staged additions and maximum single-step size;
- dilution equivalence and scale invariance;
- uncertainty propagation;
- workbench deterministic output and evidence classes;
- no numerical receptor activation from family priors;
- API compatibility and canonical result presence;
- Pydantic 2.12 application import;
- Docker/packaging import smoke checks where local tooling permits.

## Literature Basis

- IUPAC defines mass fraction as constituent mass divided by total mixture mass: https://goldbook.iupac.org/terms/view/M03722
- IUPAC defines mole fraction over all mixture constituents and states the Raoult-law relationship between activity, activity coefficient, mole fraction, and equilibrium vapor behavior: https://goldbook.iupac.org/terms/view/A00296 and https://goldbook.iupac.org/terms/view/15349
- JCGM 100:2008 provides the uncertainty-propagation framework used for reported combined standard uncertainty: https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf
- ISO 8655-2:2022 defines pipette requirements and maximum permissible errors; the application therefore accepts an instrument profile instead of inventing universal precision: https://www.iso.org/standard/68797.html
- Perry and Hayes found that OAV thresholds should be evaluated in the same matrix because detection thresholds are matrix-dependent: https://pmc.ncbi.nlm.nih.gov/articles/PMC5302346/
- Singh et al. showed that competitive-binding predictions require measured single-odorant receptor response data: https://pmc.ncbi.nlm.nih.gov/articles/PMC6511041/
- Oka et al. demonstrated odorant-specific receptor antagonism and non-additive mixture response: https://pmc.ncbi.nlm.nih.gov/articles/PMC1271670/

## Acceptance Criteria

- One workbench service is the backend formula-analysis authority.
- Exact addition results conserve mass and active material to numerical tolerance.
- No operator-facing recommendation silently assumes density or pipette precision.
- Formula analysis reports ppm, ODT, OAV, provenance, assumptions, and limitations.
- Production temporal output contains no numerical family-proxy receptor prediction.
- Existing focused engine tests remain green.
- New engine and backend tests pass.
- Backend import works under the repository's supported Python environment.
- No existing user formula or untracked root note is modified.

