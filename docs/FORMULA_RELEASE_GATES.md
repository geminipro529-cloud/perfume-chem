# Formula Release Gates

This project can generate convincing formulas before the science stack is fully trustworthy. A formula should not be called release-ready unless it passes these gates.

## Hard Gates

| Gate | Required behavior | Current status |
|---|---|---|
| Safety composite | IFRA/allergen/banned-material failures must fail release, not merely lower score. | Implemented in `engine.pipeline.gates`; legacy scorer still reports separately. |
| Batch assumptions | Every scorer must receive actual batch volume, concentration, dilution, and solvent. | `FormulaState` carries batch volume; legacy modules still need migration. |
| Dilution accounting | Keep raw stock volume, active neat-equivalent, carrier, final-product ppm, and OAV separate. | Implemented in `engine.pipeline.formula_state`. |
| Strict formula grammar | Reject subtotal mismatch, duplicate canonical identities, malformed dilution labels, silent skipped rows, and impossible units. | Added `scripts/formula_release_gate.py` as a first-pass blocker. |
| ODT/VP/logP/MW coverage | Missing ODT/VP/logP/MW must lower confidence or block release depending on role. | Implemented as `physics_data_coverage` and `odt_coverage`. |
| OAV guard | PPM/OAV checks must flag single-material flooding, pipette-floor traces, missing ODT, and unrealistic threshold crossings. | Implemented as `oav_scaling_guard` for requested proportional batch targets; broader OAV flooding remains covered by `oav_legibility`/sensory gates. |
| Unknown material behavior | Unknown materials must be `unknown`, not silently treated as `heart` or generic. | Implemented through shared resolver use in `FormulaState` and severe legacy scorer penalty. |
| Chemical-life floor | Very low chemical-life health must block release or require an explicit waiver. | Currently reported as diagnostic in some outputs. |
| Confidence floor | LOW confidence cannot be presented as trusted verification. | Implemented as `confidence_minimum` with pipeline uncertainty. |
| Reproducibility manifest | Verification bundles need git hash, data hashes, random seed, scorer config, and dependency versions. | Partially covered by pipeline audit events; full dependency manifest still missing. |
| Robustness | Optimized formulas need perturbation checks: small dose changes should not flip class or collapse score. | Implemented as `robustness_perturbation`; WARN in technical mode, blocker in commercial mode. |
| Perfumer-logic rerun | If the scalar optimum violates the olfactory brief, rerun the optimizer with revised bounds/weights instead of accepting the best numeric score. | Added first-pass `perfumer_logic` gate. |
| Sensory panel | Model-pass formulas remain candidates until blotter/skin reads confirm top, heart, drydown, projection, and acceptability. | `engine.calibration` now stores observed wear-test and panel records. |

## Gate-First Pipeline

New release tooling runs through the reusable `engine.pipeline` layer:

1. `engine.pipeline.formula_state.build_formula_state` preserves raw uL, dilution, active uL, mass, moles, mole fraction, gamma, vapor ppm, OAV, intensity, family, data sources, and uncertainty.
2. `engine.pipeline.simulator.simulate_formula` produces time-window frames for opening, top, heart, late heart, and drydown. The evaporation backend is currently labeled heuristic until finite-film calibration is added.
3. `engine.pipeline.gates.gate_formula` applies hard gates for subtotal, identity, physics coverage, ODT coverage, opaque preblends, blocked materials, pipette floor, OAV scaling, IFRA/allergen safety, brief grammar, OAV legibility, sensory overcrowding, master-perfumer readability, robustness, and confidence.
4. `engine.optimizer.gate_aware.optimize_until_release_ready` wraps optimizer outputs, repairs deterministic failures, and records blocked rerun requirements.
5. `engine.pipeline.audit_log` records compact gate/optimizer events to `data/pipeline_audit/events.jsonl` by default.
6. `scripts/formula_release_gate.py` is now only a CLI wrapper around `engine.pipeline.gates`.

Generated "Optimized" formulas should include:

- Time-series ppm/OAV tables from the simulation frames.
- Gate status and commercial-readiness status.
- Combined confidence grade from old data confidence plus pipeline uncertainty.
- A statement that model-pass formulas are candidates until skin/blotter calibration confirms the prediction.
- IFRA headroom, commercial-mode status, robustness repairs, and audit event ID.

## Immediate Recommendation

Use `scripts/formula_release_gate.py` before running the expensive verifier:

```powershell
python scripts\formula_release_gate.py --formula-file formulas\collections\Layton_DNA_Mass_Market_3_Optimized.md
```

If this gate fails, do not trust downstream star ratings. Fix the formula table or data coverage first.

For brief-specific logic, either rely on auto-detection or pass the brief explicitly:

```powershell
python scripts\formula_release_gate.py --formula-file formulas\collections\Thai_Aromatic_Fougere_3_Optimized.md --brief aromatic_fougere
python scripts\formula_release_gate.py --formula-file formulas\collections\Layton_DNA_Mass_Market_3_Optimized.md --brief layton_dna
```

If `perfumer_logic` fails, the correct response is another optimizer pass with stronger constraints, not manual acceptance of a high score.

## Gate-Aware Repair Loop

The Part 2 optimizer wrapper intentionally does not rewrite every objective. It accepts a candidate formula from an existing optimizer, runs the release gates, and then applies only deterministic repairs:

- IFRA violations become hard raw-uL caps. For the current 30 mL Cat 4 model, technical `Evernyl` is capped to `<= 30 uL` neat stock; commercial mode uses 80% headroom, so the direct cap is `<= 24 uL`.
- Commercial robustness repair can tighten that further. If `Evernyl + 5 uL` would breach headroom, the repair loop caps the row by the perturbation delta and rebalances the displaced volume through the legal repair pool.
- Displaced unsafe volume is rebalanced through an explicit legal repair pool, usually woods, musks, balsams, or radiance materials already present in the palette.
- Neat traces below the pipette floor are raised to the floor by borrowing volume from the largest feasible donor.
- Unknown materials, missing physics/ODT data, blocked materials, unwaived opaque preblends, and wrong-brief formulas are blocked or routed to a caller-provided rerun callback.
- Every repair is recorded as a `GateRepairAction` so generated markdown can show whether the result improved artistically or merely became safer.

Low confidence is still a warning in technical mode. In strict commercial-ready mode, LOW confidence is a hard blocker.

## Calibration and Robustness

Part 3 adds the empirical feedback path without applying fitted corrections yet:

- Record one wear-test or panel observation with `scripts/record_calibration.py`; records append to `data/calibration/wear_tests.jsonl` unless `--output` or `PERFUME_CALIBRATION_PATH` is provided.
- Calibration records are attached to a stable formula hash based on formula name, raw uL rows, and dilutions, independent of markdown row order.
- `ConfidenceScorer` now counts JSONL calibration records as observed outcomes in addition to any SQLite formulation outcomes.
- Release gates now include `robustness_perturbation`, which perturbs every material up/down by `max(5 uL, 5% raw dose)` while preserving subtotal.
- Robustness is warning-only in technical mode. In commercial mode it becomes a blocker and the optimizer wrapper can repair safety-margin perturbation failures.

Example calibration entry:

```powershell
python scripts\record_calibration.py --formula-file formulas\collections\Thai_Aromatic_Fougere_3_Optimized.md --formula-number 1 --time-min 30 --substrate skin --projection-cm 45 --intensity 6.5 --dominant-note lavender --comment "clean aromatic heart"
```

## Commercial Mode and Audit Log

Part 4 adds opt-in commercial strictness and a retroactive audit trail:

- `ReleaseGateConfig(commercial_mode=True)` defaults to `ifra_headroom=0.8`.
- `--commercial-ready` on `scripts/formula_release_gate.py` applies 80% IFRA headroom, blocks robustness warnings, blocks LOW confidence, and blocks opaque preblends even if normally waived.
- `--ifra-headroom` can override the multiplier for stricter or exploratory runs.
- `--no-audit` disables JSONL audit logging for a run.
- `scripts/pipeline_audit.py summarize` ranks recurring gate failures from the audit log.
- `scripts/pipeline_audit.py scan-formulas --glob "formulas/**/*.md"` gates historical markdown outputs without rewriting them.
- `scripts/pipeline_audit.py suggest-repairs --material Evernyl` prints recurring material-specific repair suggestions.

Commercial scan example:

```powershell
python scripts\formula_release_gate.py --formula-file formulas\collections\Thai_Aromatic_Fougere_3_Optimized.md --brief aromatic_fougere --commercial-ready
python scripts\pipeline_audit.py scan-formulas --glob "formulas/**/*.md" --commercial-ready
python scripts\pipeline_audit.py suggest-repairs --material Evernyl
```

To run exploratory formulas that intentionally use FTEC/FO/base materials, pass an explicit waiver:

```powershell
python scripts\formula_release_gate.py --formula-file formulas\collections\Layton_DNA_Mass_Market_3_Optimized.md --brief layton_dna --allow-preblends
```

## Commercial-Trial Mode and Scaling Guard

Part 5 separates sellable commercial-ready outputs from safer trial candidates:

- `--commercial-trial` applies commercial safety/buildability rules: 80% IFRA headroom by default, robustness warnings as blockers, and opaque preblends blocked.
- In commercial-trial mode, LOW confidence is a warning instead of a blocker and readiness becomes `COMMERCIAL_TRIAL_READY_LOW_CONFIDENCE`.
- Trial outputs are not sellable until calibrated with real wear-test or panel records.
- `--commercial-ready` remains strict: LOW confidence blocks release.
- `--scaling-target-ml` can be repeated to run `oav_scaling_guard` for proportional batch scaling. Scaling `warn` becomes a blocker in commercial-ready and commercial-trial modes.
- Unknown materials now remain unresolved: release gates fail `material_spine_coverage`, and the legacy scorer reports `_unknown_materials` with a severe score penalty instead of assigning a generic profile.

Trial scan examples:

```powershell
python scripts\formula_release_gate.py --formula-file formulas\collections\Thai_Aromatic_Fougere_3_Optimized.md --brief aromatic_fougere --commercial-trial --scaling-target-ml 15
python scripts\pipeline_audit.py scan-formulas --glob "formulas/collections/Layton_DNA_Mass_Market_3_Optimized.md" --brief layton_dna --commercial-trial --no-audit

## Physics/Chemistry Corrections (2026-04-28)

The following corrections were applied in this session. Formulas evaluated before this date have inaccurate scores on the affected axes.

### VP units fix — P0

11 entries in `engine/diffusion_model.py:DIFFUSION_DATA` had `VP_25` written in mmHg-magnitude instead of Pa (Pa = mmHg × 133.322). Affected materials: Alpha Isomethyl Ionone, Apritone, Benzyl Acetate, Cardamom FTEC, Cis Jasmone, Ethyl 2-Methylbutyrate (14→1860 Pa), Hexyl Acetate (1.4→190 Pa), Ethyl Linalool, Norlimbanol Dextro, Sandalore, Zenolide. Correction restores 10–100× higher projection for these materials. Every diffusion/sillage score from the v4a, F1 Le Barbier de Grasse, Layton DNA, and Thai Aromatic Fougere optimizations used the wrong constants.

### Skin-temperature VP — P1.1

`diffusion_model.py` now scales `VP_25` to skin temperature (305 K) via `vp_pa()` from `engine/thermo/antoine.py` — the same shared helper used by `headspace.py`. The Clausius–Clapeyron correction (ΔHvap ≈ 50 kJ/mol) gives ~1.59× higher vapor pressure at skin temp vs 25 °C, aligning diffusion estimates with headspace chemistry. Hand-curated `Kaw_eff` entries are untouched.

### Stevens' power law on OAV — P1.3

`engine/pipeline/formula_state.py` applies `perceived_intensity_stevens(oav, family)` from `engine/perception/oav.py`, with per-family exponents (musk 0.30, wood 0.38, floral 0.42, citrus 0.55, default 0.40). The `_gate_sensory_overcrowding` gate uses Stevens-corrected intensity instead of raw OAV.

### Dilution fix — latent bug

`engine/optimizer/scoring.py:_science_ingredients` now reads dilution factors from `FormulaVector.dilutions` instead of the removed profile-level `dilution` field. IFRA compliance and skin-interaction scores now correctly apply dilution.
```
