# SCIENCE_PLAN — perfume-chem physical simulator

This document is the contract between the `perfume-chem` simulator and any
external scientific reviewer / AI assistant. It states **what we model**,
**what we approximate**, and **what we do not yet handle**.

## Architecture (as built)

| Phase | Module                            | Role |
|-------|-----------------------------------|------|
| 0     | `engine/data_spine/`              | YAML A–Z material catalog (1,211 materials, 82% PerfumersWorld coverage) |
| 1     | `engine/thermo/antoine.py`        | Vapor pressure: Antoine → CC fallback |
| 1     | `engine/thermo/activity.py`       | γᵢ via UNIFAC stub → Hansen-distance heuristic |
| 1     | `engine/thermo/headspace.py`      | Modified-Raoult: pᵢ = γᵢ·xᵢ·Pᵢᵛ |
| 2     | `engine/thermo/trajectory.py`     | Fick + VLE Euler integration; bloom detection |
| 3     | `engine/skin_compartments.py`     | Potts–Guy Kp; sebum factor; depot τ |
| 4     | `engine/perception/oav.py`        | OAV; Stevens / Weber; mixture-shifted ODT |
| 5     | `engine/receptor/binding.py`      | Competitive Hill occupancy across an OR array |
| 5     | `engine/receptor/adaptation.py`   | Three-pool Ca²⁺ / CaMKII / GRK adaptation |
| 6     | `engine/receptor/bulb.py`         | Lateral inhibition; novelty; Laing-limit blur |
| 7     | `engine/chemistry/maturation.py`  | Arrhenius reactor: acetal, Schiff, autoxid, isomer |
| 7b    | `engine/chemistry/photochem.py`   | UV first-order loss for citrals/furocoumarins |
| 8     | `engine/thermo/phase.py`          | HSP-sphere RED for micro-phase / bloom-on-dilution |
| 9     | `engine/delivery/spray.py`        | Log-normal droplet, d²-law, Stokes settling |
| 9     | `engine/delivery/sniff.py`        | Tidal/sniff profile; cleft fraction; Sherwood kg |
| 10    | `engine/optimizer/oav_objective.py` | OAV-space objective + DE search |
| 11    | `engine/biology/microbiome.py`    | Endogenous axillary background |
| 11    | `engine/biology/genetics.py`      | OR polymorphism (OR7D4, OR5A1, OR11H7) |
| 12    | `engine/science_audit.py`         | Coverage report + machine-readable contract |
| 12    | `verification_runs/`              | Golden-set regression harness |

## Locked design decisions

1. **Thermo backend** = `thermo` (Caleb Bell, MIT) + RDKit, both *optional*; heuristics fall back if either is missing.
2. **Optimizer rollout** = A/B incremental — DE coexists with the existing hill-climb scorer until parity is shown.
3. **OR data sources** = Mainland 2014 + Trimmer 2019 + structural-similarity prior; per-material EC50s remain a backfill task.
4. **User OR profile** = population averages (`engine.biology.genetics.population_average_response`).

## Known weaknesses & open questions

See `python -m engine.science_audit` for the live machine-readable
report. Highlights:

- **Antoine A/B/C**: 0% coverage in the current data spine. VP(T) above 40 °C
  is extrapolated from VP_25 + ΔHvap (Clausius–Clapeyron), which under-
  estimates volatility for branched/macrocyclic structures.
- **UNIFAC**: thermo's UNIFAC needs SMARTS group decomposition per material;
  presently stubbed. Hansen-distance heuristic is calibrated to limonene-in-
  EtOH only.
- **OR EC50s**: 0% coverage. Family→OR-affinity prior (8 OR genes) is a
  caricature of the 396-locus human OR repertoire.
- **Adaptation τ**: rat single-cell values; human bulb-level feedback may
  differ by 2–3×.
- **Maturation kinetics**: Arrhenius A/Ea per reaction class, calibrated to
  Blakeway 1987 only.

## Open questions for external reviewers

1. Should mixture-shift β be material-pair-specific or kept globally fixed?
2. Stevens' law per OR vs Weber–Fechner — pick one as default?
3. Retronasal vs orthonasal weight in the optimizer for skin fragrance?
4. Lateral-inhibition kernel: ring-uniform (current) vs structural-similarity-
   weighted?
5. Granularity: 8-OR caricature (current) vs full 396 ORs?

## How to run

```powershell
# Re-audit data coverage
.\.venv\Scripts\python.exe -m engine.data_spine.audit

# Re-build the data spine from inventory + PerfumersWorld
.\.venv\Scripts\python.exe -m engine.data_spine.migrate

# Golden-set regression
.\.venv\Scripts\python.exe -m verification_runs.run_golden

# Science audit (writes verification_runs/science_audit.json)
.\.venv\Scripts\python.exe -m engine.science_audit
```

## Permanent formula-construction rules (user-issued 2026-04-23)

1. Formulas are expressed in **VP / OAV-relative units**, not absolute µL —
   they must scale across batch sizes without re-derivation.
2. **No pre-blended materials**: no FTECs, Fleuressences, FOs, Accord/Core
   bases, or any opaque-composition material. Only single-molecule aroma
   chemicals and EOs of known composition.

These rules are encoded in `engine.data_spine.migrate._ingest_perfumersworld`
which tags pre-blended materials with `families: ["pre-blended"]` so the
optimizer can filter them out at search-space construction time.
