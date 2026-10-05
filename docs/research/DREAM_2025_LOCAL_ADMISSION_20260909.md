# DREAM 2025: local installation and optimizer admission

## Scope

User authorized installation in the existing environment and continued research
for computer-only pre-mixing optimization. No new worktree, no physical trial
prerequisite, and no formula changes. Installation does not grant a model final
optimization authority.

Source snapshot: Satarifard/Olfactory-Mixtures-Prediction-2025,
`1aff2ea1764b8434e703a0eb8c27302ec2910f60`.
Dependency: laurahsisson/dream, `32c25530535aa8354107ee6f587afd691ba6c1f0`.
Downloaded sources and pip receipts are in `output/dataset_suitability_20260909`.

## Frozen small benchmark protocol (before fitting)

This is a new baseline experiment, not reproduction of the published model.
Use only Task 1 definition and training CSVs. Join exact stimulus IDs; require
exactly one H and one L observation per molecule, positive dilution, matching
solvent, finite 51-descriptor ratings, and different H/L dilution.
Keep both translation directions of each molecule in the same split. Order
molecule IDs by SHA-256 of `dream2025-local-v1:<ID>`; reserve the first 20%
(rounded up) as held-out molecules. Do not tune on held-out results.

Predict the target profile from the known opposite-concentration profile and
log10(target/source dilution). Compare unchanged-profile baseline with one
CPU CatBoost model: 100 iterations, depth 4, learning rate 0.05, MultiRMSE,
seed 20260909, two threads, no file-writing side effects. Clip negative
predictions to zero. No Optuna search. Report pooled RMSE and per-molecule
paired error differences; do not promote on correlation alone.

This model needs a measured known-concentration profile. It is not a
formula-only predictor for the user's unmeasured materials. No pleasantness,
richness, layering, or temporal endpoints occur in these 51 labels.

## Source-code admission decisions

- Task 2 dataset notebook drops dilution (Colab/dataset cell 18), then drops
  Intensity and Pleasantness (cell 23). Its graphs carry identities, not doses.
  Reject the unmodified model for same-palette ratio ranking and hedonic scoring.
- Cloud/finetune cell 7 derives target caps before splitting; derive any future
  preprocessing from training only. Cell 25 uses row ShuffleSplit; group all
  equivalent molecular representations together before splitting.
- Cloud/finetune cell 13 deep-copies a model but changes the original model's
  prediction head. Do not execute this notebook as an unattended training job.
- Downloaded Task 2 has no final 2025 fitted checkpoint. The external dependency
  contains pretrained checkpoints; loading those is not loading a validated
  final 2025 predictor.
- Preserve MIT notices. Dataset and Task 1 redistribution/commercial terms are
  not inferred from Task 2's code license.

## What can reach final optimizer passes

1. Exact identity, active-dose arithmetic, stock feasibility, and preservation
   of gin-vetiver with a light cypress accent remain independently testable.
2. Admit a numerical perceptual objective only after endpoint alignment,
   formula-computable inputs, dose sensitivity for dose decisions, grouped
   held-out improvement over simple baselines, and uncertainty/domain checks.
3. Raw measured pleasantness is eligible for a separately developed model;
   it is not evidence that the provided descriptor model predicts pleasantness.
4. Keep richness, layering and target-character hypotheses explicit rather
   than manufacturing them from descriptor count, OAV or generic liking priors.
5. Retain candidates whose improvement is unresolved; do not force a scalar
   winner. Stop at an evidence boundary or predeclared budget, not by weakening
   gates until they pass. Computer-only completion and sensory proof differ.

## Primary-source research

- https://github.com/Satarifard/Olfactory-Mixtures-Prediction-2025
- https://github.com/laurahsisson/dream
- https://www.synapse.org/Synapse:syn64743570/datasets/
- https://academic.oup.com/chemse/article/33/7/599/330603
  Lapid et al.: ratio-sensitive binary pleasantness modeling uses measured
  constituent pleasantness and intensities; it does not justify substituting
  OAV for human intensity or directly extrapolating to a full perfume.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8144660/
  Ma et al.: useful independent binary-mixture intensity/pleasantness data;
  source component measurements and experimental matrix must be preserved.

## Executed findings

The parent independently verified 393 raw rated mixtures, each with intensity
and pleasantness, and 355 distinct sorted CID multisets. Eleven identity groups
have multiple dilution/solvent configurations (42 observations); eight retain
the same per-component solvents. These are priority concentration-variation
cases, not yet verified final-mixture weight ratios. See the generated
`task2_concentration_variant_audit.json` receipt.

The official data wiki was retrieved through the public Synapse API and saved
as `synapse_data_wiki_632380.json`. It explicitly defines a component as a
molecule at a specified dilution in a specified solvent. The retrieved page
does not specify dilution units or component combination volumes. It also
identifies OpenPOM_Dream_RATA.csv as model-generated, not human-measured data.
Exclude those generated profiles from independent human-label validation.
Official source: https://www.synapse.org/Synapse:syn64743570/wiki/632380

The processed train CSV has 650 rows and 590 distinct sorted semicolon-split
SMILES tuples (without chemical canonicalization). Forty repeated tuples
contain 100 rows; 11 of 130 processed test rows share a tuple with training.
These are representation-overlap counts, not proof of identical-label leakage.

The frozen Task 1 benchmark retained 100 valid paired molecules, with 80
training and 20 held out (40 direction-specific test rows). Of the 151 joined
molecules, 31 lack a complete H/L pair and 20 complete pairs fail the protocol's
other admissibility checks. Unchanged-profile RMSE: 0.263070. Small CatBoost
translation RMSE: 0.289364. Twelve held-out molecules improve in mean squared
error, but pooled error worsens about 10%. Reject promotion of this fitted
baseline; do not retune against this now-observed holdout. This is not a test
of the authors' descriptor-rich tuned model. Result receipt:
`task1_grouped_baseline_result.json`.

## Concrete next model-development pass

Prioritize source protocol/units resolution for the eight solvent-matched
mixture-variation groups. Establish exact component identity and final delivery
basis before treating dilution values as quantitative mixture inputs. Then
compare concentration-aware simple predictors against identity-only and
unchanged-profile controls, holding complete identity groups out. Preserve
pleasantness and intensity as separate measured endpoints, never use mixture
outcomes as predictors, and keep all preprocessing training-only. These small
groups can challenge dose blindness; they cannot alone establish full-perfume
richness or personal liking. Do not use post hoc hyperparameter search to erase
the failed baseline result.

Installed in the existing Python 3.14 environment: CatBoost 1.2.10, Optuna 5.0.0,
odor-pair 1.0 from the pinned source, torch-geometric 2.8.0.post1, RDKit 2026.3.6,
OGB 1.3.6, h5py 3.16.0 and torchmetrics 1.9.0 plus dependencies. Repaired
incompatible pre-existing compiled packages at the same versions: torch,
scikit-learn, matplotlib, PyYAML, Pillow, contourpy, kiwisolver and regex.
No source notebook was run wholesale or installed as an automatic optimizer.
The pretrained dependency loads on CPU and a two-molecule forward pass returns
finite 128-dimensional embeddings and 101 logits. That is an infrastructure
smoke test, not the final 51-descriptor DREAM 2025 model.

The existing optimizer's five focused test modules pass: 76 tests. Formula and
inventory SHA-256 values remain unchanged. Full-project release verification
was not repeated, and remaining unrelated platform mismatches are reported by
the final installation receipt rather than claimed fixed.
