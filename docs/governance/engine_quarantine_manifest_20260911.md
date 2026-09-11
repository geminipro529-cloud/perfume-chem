# Engine quarantine manifest — 2026-09-11

Purpose: record the engine modules that are **turned off and of no use**, so they
are preserved as source but are not developed, imported by runtime code, or
promoted without an explicit owner un-quarantine decision.

Machine-readable source of truth:
`docs/governance/engine_quarantine_manifest_20260911.json`.
Enforcement test: `tests/test_engine_quarantine_manifest.py`.

## Quarantined — dead code (zero inbound references, runtime or tests)

| Module | File | Disposition |
|---|---|---|
| `engine.corrections_patch` | `engine/corrections_patch.py` | dead code |
| `engine.ifra_checker` | `engine/ifra_checker.py` | superseded by `ifra_safety` / `ifra_constraints` |
| `engine.material_validator` | `engine/material_validator.py` | superseded by `chemical_data_validator` + material-data-validation |
| `engine.calibration.state_diff` | `engine/calibration/state_diff.py` | dead code |
| `engine.reconstruction.natural_lots` | `engine/reconstruction/natural_lots.py` | duplicate of live `engine.physics.natural_lots` |
| `engine.ingestion.__main__` | `engine/ingestion/__main__.py` | unreferenced CLI entry |

Each file carries a header banner:
`# QUARANTINED 2026-09-11 - no runtime references; do not develop.`

## Already retired — registry tombstones (do not develop)

State `RETIRED_BENCHMARK_UNDERPERFORMER` in
`configs/complexity/complexity_module_registry_v1.json` (citrus additionally
retired in the root repo's registry v2):

- `engine/perception/construction_complexity.py`
- `engine/perception/complexity_expansion.py`
- `engine/perception/musk_design.py`
- `engine/scientific_validation/complexity_model_admission.py`
- `engine/physics/model_lifecycle.py`
- `engine/sensory/within_sniff.py`
- `engine/sensory/temporal_observations.py`
- `engine/sensory/order_balance.py`
- `engine/sensory/panel_contract.py`
- `engine/perception/citrus_selection.py`

## Frozen research — not runtime, do not promote

- `engine/formulation_intelligence/` — `NOT_RELEASE_READY`; only reachable via
  `ReleaseGateConfig.deep_plane_diagnostics_enabled=True` (default `False`).
- `engine/receptor/` — advisory only (C0 verifier + `pipeline_audit`).
- `engine/experiments/` — probe only.
- `engine/delivery/`, `engine/orchestration/`, `engine/interaction_registry/` — zero external references.
- `future_modules/` — feature-detected research; keep frozen.

## Rule

Run `pytest tests/test_engine_quarantine_manifest.py` before merging engine
changes. A failure means either a quarantined module was removed/moved (update
this manifest) or runtime code started depending on quarantined code (revert).
