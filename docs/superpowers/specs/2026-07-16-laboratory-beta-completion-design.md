# Perfume Chem Laboratory Beta Completion Design

**Date:** 2026-07-16
**Status:** Self-approved under the user's delegated approval
**Source:** `docs/legacy-root/Perfume-Chem Completion Roadmap.txt`, `docs/legacy-root/PERFUME_CHEM_PLAN.txt`, and `docs/legacy-root/PERFUME_CHEM_IMPLEMENTATION.txt`

## Objective

Finish Perfume Chem as a local-first laboratory beta whose calculations are deterministic, unit-explicit, evidence-labeled, reversible where practical, and available through one application authority. The beta must support a complete workflow from materials and stock solutions through immutable formula versions, batches, bottle events, analysis, interventions, experiments, observations, comparisons, backup, and restore.

The beta is software-complete when all implemented workflows pass local acceptance tests. It is not a scientifically validated performance predictor until held-out wear-test and headspace data satisfy the release gates. Unsupported longevity, sillage, receptor, mood, and universal pleasantness claims remain `UNKNOWN`.

## Research Basis

- IUPAC defines mass fraction as constituent mass divided by total mixture mass and mass concentration as constituent mass divided by mixture volume. NIST recommends naming the quantity kind instead of using ambiguous bare ppm. Internally, dimensionless quantities therefore store a fraction plus an explicit basis such as `mass_fraction`, `volume_fraction`, `amount_fraction`, or `gas_amount_fraction`; dimensionful liquid mass concentration uses a separate unit-bearing quantity stored in g/L. API output may include familiar ppm/ppb labels only with the physical basis in the field name.
- SQLAlchemy documents history-table and temporal-row versioning patterns. The lab uses immutable version rows and append-only events rather than mutating scientific history.
- SQLite guarantees transactional writes and provides an online backup API. A bottle event and its inventory movement are committed in one transaction; backup uses the Python SQLite backup binding rather than copying a live file.
- IFRA Standards change by amendment and depend on product category and contributions from other sources. Every safety result therefore records the standard source, amendment, category, concentration basis, and unresolved constituent assumptions.
- Bradley and Terry's paired-comparison model is suitable only after the comparison graph is identifiable. The beta stores comparisons immediately but withholds fitted preference claims until minimum data and connectivity gates pass.

## Authority Boundary

`engine.workbench.PerfumeWorkbench` is the sole application-facing calculation authority.

- Engine modules perform scientific and bottle arithmetic.
- `LabService` is the API-facing orchestration and transaction authority. It persists facts and events but delegates every scientific calculation to Workbench.
- Workbench is a pure deterministic calculator over typed requests and reconstructed snapshots. It never opens the backend database.
- FastAPI schemas validate and translate inputs but do not duplicate formulas.
- The assistant parses a constrained request into a deterministic tool plan and renders a returned evidence packet. The hashed scientific payload uses canonical JSON key order, stable list ordering, a declared decimal policy, and state/event/evidence dataset revisions; timestamps live in an unhashed envelope. Ambiguous requests are refused. Optional LLM prose is explicitly non-deterministic and cannot add facts or numbers. It cannot invent material properties, calculations, safety conclusions, or formula changes.
- The interface calls the API only. It never calculates concentrations, OAV, additions, or safety in browser code.

## Canonical Domain

### Quantities

Strict immutable value objects cover volume, mass, density, temperature, duration, molar mass, fraction, vapor pressure, odor threshold, OAV, and uncertainty. Constructors reject non-finite values, invalid signs, and incompatible conversions. Ambiguous concentration names are prohibited.

Every calculation request declares `strict` or `compatibility` mode. Strict mode requires stock fraction and fraction basis, finished solvent composition, and all inputs used by an exact conversion. Compatibility mode may preserve legacy defaults for exploratory analysis, but every dependent result is `HEURISTIC` or `UNKNOWN` and may not authorize ledger writes, safety conclusions, or dosing instructions.

### Materials and Evidence

- `Material`: canonical identity only.
- `MaterialAlias`: normalized alternate identity.
- `MaterialProperty`: one value, unit, conditions, uncertainty, and evidence record.
- `Restriction`: standard source, version/amendment, category, basis, limit, and scope.
- `Constituent`: natural or preblend constituent contribution with provenance.
- `EvidenceRecord`: one claim, classification, source locator, method, assumptions, limitations, and verification time.

Legacy JSON/YAML remains importable and is preserved in source payloads. It is not silently promoted to verified evidence.

### Stock and Inventory

- `StockSolution`: material, supplier/lot, active fraction and basis, density, solvent, quantity, and measurement metadata.
- `InventoryMovement`: immutable signed mass movement, reason, source event effect, and timestamp. Measured volume is retained as metadata and converted only when an explicit density is present.
- Current inventory is reconstructed by summing mass movements on one declared conservation basis per stock. It is never a freely editable total.

### Formulas, Batches, and Bottles

- `Formula`: stable identity and name.
- `FormulaVersion`: immutable brief, constraints, concentration target, and source metadata.
- `FormulaComponent`: stock/material reference and explicit requested quantity.
- `Batch`: execution of one formula version with measured actuals.
- `Bottle`: physical container identity.
- `BottleEvent`: append-only create, add, remove, transfer, dilute, measure, observe, and discard events with `(bottle_id, stream_sequence)` uniqueness, command idempotency key, and optional correction reference.
- `BottleEventEffect`: explicit mass effect linking an event to one or more source/destination bottles and stock movements.
- `BottleMeasurement`: measured mass, volume, temperature, or density with uncertainty.

Bottle state is reconstructed by stream sequence, never wall-clock time. Commands declare `expected_sequence` for optimistic concurrency and an idempotency key for safe retry. Additions, transfers, splits, combines, and their inventory effects commit atomically. Corrections are linked compensating events, never history edits. Database triggers reject update/delete of event, effect, version, prediction, and outcome history.

### Experiments and Preference

- `Experiment`, `Sample`, `Application`, `Observation`, `PairwiseComparison`, `Prediction`, and `Outcome` store protocol, timing, context, raw answers, and model/version metadata.
- Predictions are written before outcomes and remain immutable.
- Pairwise fitting requires enough comparisons, a connected comparison graph, and explicit regularization. A fit may be shown for diagnostics.
- Predictions remain `UNKNOWN/not_validated` until a predeclared held-out evaluation beats the declared simple baselines.

## Mixture and Analysis Contract

`MixtureRequest` represents the finished liquid, not only odorants. It includes aromatic stocks, ethanol, water, and other solvents when known. Each component tracks raw dose, active dose, mass, amount, fraction kind, provenance, and missing inputs.

Model tiers are explicit:

1. `EXACT`: bottle and mass-balance arithmetic for stated inputs.
2. `LITERATURE_DERIVED`: direct equation with sourced constants and declared conditions.
3. `HEURISTIC`: uncalibrated mixture/headspace or temporal estimate.
4. `EMPIRICALLY_CALIBRATED`: only after frozen model and held-out validation.
5. `UNKNOWN`: required data absent or validation gate unmet.

No density, molecular weight, vapor pressure, ODT, activity coefficient, natural constituent, or receptor datum is silently invented for an exact result. Existing fallbacks may support explicitly heuristic compatibility output and must appear in limitations.

## Workbench Operations

The completed authority exposes:

- analyze a formula or reconstructed bottle;
- calculate and preview a stock addition;
- reconstruct a bottle and inventory state;
- compare before/after states;
- screen safety against a named regulatory dataset;
- generate conservative, inventory-valid intervention candidates that satisfy explicit brief constraints;
- calculate over observations, experiments, predictions, outcomes, and pairwise comparisons supplied as typed snapshots;
- produce an evidence packet and deterministic assistant response.

Interventions are constrained by must-preserve notes, forbidden materials, maximum additions, stock availability, measurement feasibility, and safety posture. Satisfying machine-readable brief constraints is exact; predicted preservation of sensory identity remains `HEURISTIC` until evaluated. Ranking is Pareto-based; no single opaque luxury or pleasantness score is authoritative.

## API and Interface

The FastAPI lab router exposes resources for dashboard, materials, stocks, formulas, bottles, experiments, analysis, interventions, assistant packets, backup, and restore validation.

The offline interface is a dependency-free static application served by FastAPI. Offline means no external network, CDN, paid model, or Node runtime; the local API process is required. Its visual direction is an archival perfumer's bench: warm paper, ink, brass, and glass rather than generic dashboard styling. It supports desktop and mobile and includes:

- readiness dashboard;
- bottle ledger and addition preview;
- formula version viewer and analyzer;
- material/evidence lookup;
- experiment and comparison capture;
- deterministic assistant panel;
- backup/export controls.

The UI displays evidence class and missing-data warnings beside every scientific output.

## Persistence and Migration

Use SQLAlchemy 2 typed mappings with `lab_*` table names so the existing `materials` and other legacy tables cannot collide. Before migration, resolve one absolute database path shared by runtime, Alembic, backup, and restore; create a SQLite snapshot; fingerprint the legacy schema; and record the result. Add Alembic as the migration authority and provide an idempotent baseline migration. New installations upgrade to head; existing databases retain legacy rows and gain the lab schema. Import uses an explicit legacy crosswalk, produces a report, and never drops source tables.

SQLite foreign keys are enabled on every connection. Write workflows use one transaction. Migration tests cover empty, populated-current, partially migrated, corrupted, and newer-than-supported databases.

## Privacy, Backup, and Security

- Local SQLite is the default and no cloud service is required.
- Secrets stay in environment variables and are never exported.
- Backup uses SQLite's consistent snapshot operation and includes a manifest with schema revision and SHA-256 digest.
- Restore validates the manifest, digest, schema compatibility, and database integrity into a staged file while the server is running. Replacement occurs only in maintenance mode or a stopped-server command, after a pre-restore snapshot and engine disposal.
- Formula, bottle, and experiment exports use stable UUIDs and user-invoked JSON documents with provenance. Re-import is idempotent and preserves references.

## Release Gates

### Laboratory Beta

- Local engine and backend tests pass.
- Canonical workflows use Workbench and explicit quantities.
- Formula versions and scientific events are immutable.
- Bottle and inventory mass balance reconcile.
- Evidence and safety outputs are versioned and limitations are visible.
- Offline interface completes the primary lab workflow.
- Backup and restore round-trip succeeds.
- Deterministic assistant reproduces the same packet for the same state.

### Scientific Release

These remain blocked until external evidence exists:

- held-out longevity and sillage calibration;
- validated natural/preblend constituent coverage for safety;
- personalized preference model outperforming declared baselines on held-out comparisons;
- measured uncertainty and repeatability targets;
- successful hosted CI on the actual default branch.

The readiness report must distinguish code status, data status, validation status, and infrastructure status. It may never collapse them into one optimistic score.

## Cost-Benefit Decisions

- Build typed domain primitives directly instead of adding Pint to the lightweight engine package.
- Use SQLite and SQLAlchemy already present instead of introducing a separate event store.
- Serve a static offline application instead of adding a Node toolchain.
- Store pairwise data and implement a gated deterministic fitter, but do not add large ML frameworks.
- Reuse existing pipeline physics and formula-state logic through Workbench instead of rewriting the engine.
- Add versioned safety infrastructure and honest `unverified` results rather than copying an incomplete IFRA table and calling it compliant.
