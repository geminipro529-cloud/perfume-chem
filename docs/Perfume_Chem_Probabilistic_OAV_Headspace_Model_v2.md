# Perfume-Chem Probabilistic OAV(t) + Headspace Model v2

**Status:** literature-derived model specification; computational screening only until calibrated against measured headspace and sensory data.

## 1. Purpose

This module has two distinct jobs and MUST NOT be used as an automatic perfume-design optimizer.

1. **Dose-error sentinel:** catch stock-strength mistakes, accidental 3x/10x dose jumps, unit/basis errors, and gross potency anomalies before compounding.
2. **Temporal behavior estimator:** estimate perfume release, local headspace concentration, threshold exceedance, and likely perceptual salience over time with explicit uncertainty.

It does **not** establish beauty, similarity, final dominance, hedonic quality, safety, or release readiness.

## 2. Governing separation

The model keeps these layers separate:

- active target mass
- physical stock mass and active fraction
- surface/deposit mass over time
- predicted gas-phase headspace concentration
- odor-detection probability / OAV screening
- receptor interaction evidence
- mixture-perception model
- sensory validation

No phase or unit conversion may be silently substituted for another.

## 3. Layer A — deterministic dose-integrity firewall

For every formula row i:

- `active_i = stock_mass_i * active_fraction_i`
- verify active fraction against canonical inventory/ExactStockRef
- compare against parent formula and target active amount
- compute `dose_ratio_i = active_new / active_parent`
- compute `stock_rebase_error_i = active_after_stock_change / intended_active`

Default sentinel states:

- <1.5x: PASS
- 1.5x to <3x: REVIEW
- >=3x: FAIL unless explicit intentional-dose-change authority exists
- 9.5x to 10.5x: CANONICAL_TENFOLD_CATASTROPHE

This layer catches 10% -> neat copy errors without requiring any odor-threshold assumption.

## 4. Layer B — finite-dose physicochemical release model

For each material i, track surface/deposit mass `M_s,i`, skin/substrate mass `M_k,i`, and local gas concentration `C_g,i`.

A practical coupled mass-balance form is:

`dM_s,i/dt = -A*J_i - k_perm,i*M_s,i + k_back,i*M_k,i`

`dM_k,i/dt =  k_perm,i*M_s,i - k_back,i*M_k,i - k_loss,i*M_k,i`

`dC_g,i/dt = (A/V)*J_i - k_vent*C_g,i`

with interfacial flux:

`J_i = k_g,i * (C*_g,i - C_g,i)`

The equilibrium/interfacial gas concentration uses the best available authority:

1. measured matrix-specific Henry constant;
2. measured activity coefficient + vapor pressure;
3. validated UNIFAC or COSMO-RS prediction;
4. declared uncertainty envelope around ideal modified-Raoult sensitivity.

For a Raoult/activity form:

`p_i* = x_i * gamma_i * P_sat,i(T)`

and `C*_g,i` is obtained from the ideal gas relation on a consistent mass or molar basis.

The model MUST update `x_i(t)` as volatile components leave the finite deposit. Constant-composition evaporation is not permitted for long time windows unless explicitly selected as a sensitivity scenario.

## 5. Matrix and application state

Mandatory inputs/uncertain inputs:

- perfume matrix: ethanol/water/DPG/DEP/TEC/oil/etc.
- fragrance concentration
- applied mass or volume and density
- application area
- substrate: blotter / skin / fabric / inert surface
- temperature
- airflow / ventilation
- headspace volume / sampling geometry
- skin permeation or substrate sorption parameters when applicable

Parameters are matrix- and substrate-specific; cross-matrix transfer is explicitly penalized.

## 6. Layer C — probabilistic threshold model

A single scalar ODT is not treated as universal.

Preferred form when concentration-detection data exist:

`P_detect_i(c | person j) = logistic(alpha_i + u_ij + beta_i * log10(c))`

where `u_ij` is a subject/random sensitivity effect.

Population detection probability is the posterior/predictive expectation over people.

When only a threshold estimate is available:

`log10(T_i) ~ Normal(mu_T,i, sigma_T,i)`

with `sigma_T,i` determined from source quality, method, population, matrix, and any reported uncertainty. Direct standardized gas-phase measurements receive narrower distributions than compilations, analogs, supplier estimates, or cross-matrix proxies.

For every Monte Carlo/posterior draw s:

`OAV_i^(s)(t) = C_g,i^(s)(t) / T_i^(s)`

Primary outputs at each required timepoint:

- median `C_g,i(t)`
- 50%, 90%, 95% predictive intervals for `C_g,i(t)`
- median `log10 OAV_i(t)`
- 50%, 90%, 95% intervals for OAV
- `P(OAV>1)`
- `P(OAV>3)`
- `P(OAV>10)`
- `P(OAV>100)` for catastrophe screening only

Required Perfume-Chem windows remain 5 min, 30 min, 2 h, 8 h, 24 h; the numerical solver may use much smaller internal steps.

## 7. Layer D — receptor interaction module, optional and evidence-gated

Receptor calculations are enabled only for material-receptor pairs with compatible experimental evidence.

For receptor r, use a competitive occupancy/efficacy model rather than additive receptor activation. A generic form is:

`R_r = (sum_i epsilon_ir * c_i/K_ir) / (1 + sum_i c_i/K_ir)`

with extensions for Hill slopes, partial agonism, inverse agonism, and noncompetitive antagonism only when supported.

Outputs are receptor-response predictions, not odor labels.

Known human genotype-sensitive materials should use mixture/population strata when evidence exists, e.g. beta-ionone/OR5A1 and several musk receptor systems. Population uncertainty must therefore include genotype mixtures or a user-specific genotype only if actually known.

## 8. Layer E — mixture perception ensemble

OAVs are never summed into perceived intensity.

Candidate psychophysical mixture models are carried as an ensemble, including:

- strongest-component model
- Euclidean/vector interaction model
- hypoadditive power-law model
- calibrated regression model using component-alone and in-mixture intensities

No single law is universal. Model weights are learned from calibration data using out-of-sample predictive performance. If there is insufficient relevant calibration data, the model returns the separate scenarios rather than a fake consensus.

## 9. Adaptation / salience layer

Adaptation is modeled separately from physical disappearance.

A simple state model is:

`dA_i/dt = k_adapt,i * I_i(t) * (1-A_i) - k_recover,i*A_i`

`effective_salience_i(t) = I_i(t) * (1-A_i(t))`

This layer is disabled or assigned very wide priors unless material/class-specific temporal sensory data exist. It may explain unmasking and changing component salience; it may not be used to rewrite the physical headspace curve.

## 10. Dose-error and headspace-anomaly sentinel

The safety sentinel is intentionally more conservative than the design model.

A row is BLOCKED/REVIEWED before compounding if any of the following occurs without explicit authority:

- active-dose ratio to parent >=3x;
- stock-strength substitution changes active dose >=3x;
- active-dose or headspace/OAV trajectory changes by >=1 log10 (10x) at any required timepoint;
- a proposed row has an unresolved active fraction;
- incompatible threshold phase/unit is used;
- a critical property is silently defaulted;
- the 95% upper predictive bound creates a new extreme-outlier trajectory relative to the parent/formula class.

A high OAV by itself does NOT force a dose reduction. The sentinel asks: **is this an unexplained discontinuity or probable compounding error?**

## 11. Uncertainty propagation

Use distribution propagation / Monte Carlo consistent with JCGM GUM principles.

Uncertain inputs include, as applicable:

- weighed/pipetted dose
- density
- active fraction
- temperature
- vapor pressure parameters
- Henry constant / activity coefficient
- matrix model error
- application area
- evaporation mass-transfer coefficient
- ventilation
- permeation/sorption parameters
- ODT psychometric parameters
- genotype/population sensitivity
- natural-material composition

Preserve covariance when inputs share a source or fitted model.

## 12. Statistical calibration and confidence

There is NO single global confidence percentage.

### 12.1 Predictive calibration

For measured headspace datasets, evaluate held-out predictions using:

- empirical coverage of 50%, 80%, 90%, and 95% intervals
- interval width / sharpness
- log predictive density or CRPS
- calibration intercept and slope
- residual bias by material class, matrix, time window, and volatility

Temporal prediction uses leave-future-out cross-validation when the target task is future timepoints.

### 12.2 Model comparison / ensemble weighting

Competing physical models (measured-Henry, UNIFAC, COSMO-RS, empirical release) are compared by held-out predictive score. Bayesian predictive stacking may combine models after calibration. Before calibration, scenario outputs remain separate.

### 12.3 Conformal calibration

When a sufficiently large exchangeable calibration set exists within the same matrix/application domain, conformal calibration can wrap the predictor to target empirical interval coverage. It is not transferred blindly across skin, blotter, fabric, DPG, and ethanol-water domains.

### 12.4 Applicability-domain score

Every prediction receives an in-domain/out-of-domain diagnostic based on whether its matrix, temperature, application, molecular-property range, and material class are represented in calibration data. Out-of-domain predictions widen uncertainty or abstain.

## 13. Claim-specific confidence vector

Each formula report contains separate fields:

- `dose_integrity_status`
- `stock_lineage_confidence`
- `headspace_model_authority`
- `headspace_interval_coverage_empirical`
- `threshold_authority`
- `P_detect_calibration_status`
- `receptor_layer_authority`
- `mixture_model_authority`
- `applicability_domain_status`
- `sensitivity_top_uncertainty_drivers`
- `strict_empirical_OAV_available`
- `measured_headspace_available`

Suggested categorical states:

- MEASURED/CALIBRATED
- CALIBRATED_PREDICTED
- MODELED_SCREENING
- PROXY/LOW_AUTHORITY
- OUT_OF_DOMAIN
- ABSTAIN/HOLD

## 14. Minimum validation program

The model is not considered calibrated until it is tested on deliberately adversarial and ordinary formulas.

Mandatory regression cases:

1. Prada L'Homme Citronellol 10% -> neat copy error: must hard-block ~10x active error.
2. Deliberate 10x Lemonile dose: must flag dose and OAV/headspace discontinuity without automatically redesigning the perfume.
3. 10% -> neat substitutions with exact active restitution: must PASS.
4. High-OAV but intentionally correct trace: may REVIEW but must not auto-delete.
5. High-dose low-volatility musk: physical headspace must remain governed by measured/predicted release rather than liquid concentration alone.
6. beta-Ionone: population uncertainty must widen materially because receptor-genotype sensitivity is unusually heterogeneous.
7. Naturals: whole-material OAV must remain proxy/abstain unless a defensible composite or measured headspace exists.

## 15. Literature basis integrated into the model

### Fragrance release / headspace

- Schwarzenbach R, Bertschi L. Models to assess perfume diffusion from skin. Int J Cosmet Sci. 2001. DOI 10.1046/j.1467-2494.2001.00067.x.
- Teixeira MA, Rodriguez O, Rodrigues AE. Diffusion and performance of fragranced products: Prediction and validation. AIChE J. 2013. DOI 10.1002/aic.14106.
- Costa P et al. Modeling Fragrance Components Release from a Simplified Matrix Used in Toiletries and Household Products. Ind Eng Chem Res. 2015. DOI 10.1021/acs.iecr.5b03852.
- Almeida RN et al. Evaporation and permeation of fragrance applied to the skin. Ind Eng Chem Res. 2019. DOI 10.1021/acs.iecr.9b01004.
- Almeida RN et al. Radial diffusion model for fragrance materials: Prediction and validation. AIChE J. 2021. DOI 10.1002/aic.17351.
- 2025 Talanta study on in-vivo/in-vitro fragrance evaporation measurement, DOI 10.1016/j.talanta.2024.126851.
- Dupeux T et al. COSMO-RS prediction of fragrance physicochemical properties. Flavour Fragr J. 2022. DOI 10.1002/ffj.3690.

### Thresholds / detection

- Walker JC et al. Human odor detectability: methodology, threshold, and variation. Chem Senses. 2003. DOI 10.1093/chemse/bjg075.
- Cometto-Muniz JE et al. Concentration-detection functions and calibrated vapor delivery studies support sigmoid/logistic detection functions in humans.
- ODT methodology literature shows large between-person and between-method variation; threshold distributions therefore replace single universal constants.

### Mixture / receptor interactions

- Oka Y et al. Olfactory receptor antagonism between odorants. EMBO J. 2004. DOI 10.1038/sj.emboj.7600032.
- Pfister P et al. Odorant Receptor Inhibition Is Fundamental to Odor Encoding. Curr Biol. 2020. DOI 10.1016/j.cub.2020.04.086.
- de March CA et al. Modulation of combinatorial odorant-receptor response patterns in mixtures. Mol Cell Neurosci. 2020. DOI 10.1016/j.mcn.2020.103469.
- Human mixture studies support suppression, configural perception, ratio dependence, and adaptation/unmasking; these are modeled separately from headspace physics.

### Human variability

- Jaeger SR et al. beta-Ionone sensitivity and OR5A1 genotype. Curr Biol. 2013. DOI 10.1016/j.cub.2013.07.030.
- Trimmer C et al. Genetic variation across the human olfactory receptor repertoire alters odor perception. PNAS. 2019. DOI 10.1073/pnas.1804106115.
- The 2024 human musk receptor study demonstrates large genotype-associated threshold shifts for selective musk ligands.

### Statistical uncertainty

- JCGM 101:2008 — propagation of distributions using Monte Carlo.
- JCGM 102:2011 — multivariate uncertainty propagation.
- JCGM GUM-6:2020 — developing and using measurement models.

## 16. Required interpretation banner

Every report must state:

> OAV(t) is a time-resolved above-threshold screening distribution, not percent sensory contribution, beauty, similarity, or final perceived intensity. Predicted headspace is not measured headspace. Receptor predictions are mechanistic hypotheses unless directly calibrated to human sensory data. The dose-error sentinel may block unexplained dose/stock discontinuities independently of OAV.

## 17. Runtime binding status — 2026-08-09

The pre-presentation sentinel is now bound into the live gate-first pipeline as hard gate `g15_oav_firewall`.

- `engine/fuckups/pre_mix_guard.py` owns the deterministic active-dose and stock-rebase comparison plus modeled temporal/static OAV screening.
- An unexplained same-stock active-dose increase >=3x is a hard `ACTIVE_DOSE_REVISION_JUMP` failure even if temporal OAV data are unavailable.
- A stock-strength change that causes >=3x active-dose drift is a hard `STOCK_REBASE_ACTIVE_EQUIVALENCE` failure.
- Intentional >=3x dose changes require an explicit external authority reason and remain visible as `AUTHORIZED_ACTIVE_DOSE_CHANGE` warnings; the override is never silent.
- `engine/pipeline/gates.py` runs G15 as a member of `HARD_BLOCKING_GATES`. A declared `parent_formula_uid` without a supplied, identity-verifiable parent baseline fails closed.
- `scripts/formula_release_gate.py` passes `--parent-formula-file` into G15 before report/scoring output and exposes repeatable `--authorize-active-dose-change MATERIAL=AUTHORITY` for deliberate experiments.
- `engine/optimizer/gate_aware.py` compares each optimization pass after the first against the immediately preceding candidate, so optimizer-induced order-of-magnitude jumps cannot bypass the same guard.
- `engine/pipeline/audit_log.py` preserves G15 as run evidence, including parent/child lineage hashes, G15 dilution maps, findings, and explicit dose-change authority.

This binding completes the deterministic pre-presentation error-firewall chain. It does **not** convert modeled OAV or predicted headspace into measured/calibrated headspace, sensory similarity, hedonic quality, or safety authority.
