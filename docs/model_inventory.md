# Model Inventory

Audit date: 2026-07-15

This inventory classifies code that can influence perfume calculations or user
claims. The class describes the current evidence posture, not the sophistication
or usefulness of the implementation. See
[`scientific_contract.md`](scientific_contract.md) for definitions.

## Canonical Workbench Path

| Output or component | Code path | Current class | Production status | Main limitation or promotion requirement |
|---|---|---|---|---|
| Raw-to-active volume arithmetic | `engine/pipeline/formula_state.py` | `EXACT` | Active | Exact for supplied volumes and active fractions; dispensing accuracy remains an input issue. |
| Bottle target mass balance | `engine/bottle_addition.py` | `EXACT` | Active | Exact algebra under no-loss mixing and supplied mass-fraction assumptions. |
| Pipette increment rounding and staging | `engine/bottle_addition.py` | `EXACT` | Active | Exact discrete plan for the declared profile; not evidence of instrument calibration or operator performance. |
| First-order standard uncertainty propagation | `engine/bottle_addition.py` | `LITERATURE_DERIVED` | Active | GUM-style uncorrelated propagation; correlated inputs and target uncertainty are not modeled. |
| Material identity and property lookup | `engine/material_resolver.py`, `engine/data_spine/` | Mixed `LITERATURE_DERIVED` / `HEURISTIC` / `UNKNOWN` | Active | Classification varies by each field's source label. Missing values must remain visible. |
| Monomolecular ODT lookup | `engine/odor_thresholds.py`, `engine/pipeline/formula_state.py` | Mixed `LITERATURE_DERIVED` / `HEURISTIC` / `UNKNOWN` | Active | Verification tags vary; matrix and method may not match application conditions. |
| Natural-mixture composite OAV | `engine/pipeline/natural_absolute_decomposition.py` | `LITERATURE_DERIVED` with heuristic transfer | Active for covered naturals | Constituent data may be literature-derived, but batch composition and matrix transfer are not formula-specific measurements. |
| Headspace partial pressure and vapor ppm | `engine/pipeline/formula_state.py` | `HEURISTIC` | Active, explicitly labeled | Aromatic-only mole fractions omit the finished solvent matrix; physical-property and activity-coefficient fallbacks remain. Promote only after matrix-complete modeling and headspace validation. |
| Threshold visibility and OAV | `engine/pipeline/formula_state.py`, `engine/workbench.py` | `HEURISTIC` at output level | Active, explicitly labeled | Combines modeled vapor ppm with mixed-provenance ODT. OAV is a screening ratio, not measured intensity. |
| Active-volume top/heart/base distribution | `FormulaState.note_distribution()` | `HEURISTIC` | Active | Uses active volume and note labels, not measured perception or OAV-weighted salience. |
| Temporal OAV frames | `engine/pipeline/simulator.py` | `HEURISTIC` | Active, explicitly labeled | Generic exponential loss approximation lacks blotter/skin calibration and solvent dynamics. |
| Longevity in hours | `engine/workbench.py` | `UNKNOWN` | Withheld as `null` | Needs defined protocol and held-out wear-test calibration. |
| Sillage category or distance | `engine/workbench.py` | `UNKNOWN` | Withheld as `null` | Needs measured projection endpoint, environment, panel/instrument protocol, and validation. |
| Receptor activation | `engine/pipeline/simulator.py` | `UNKNOWN` | Withheld as `null` | Needs material-specific receptor affinity, efficacy, dose-response, and mixture interaction data. |
| Evidence descriptor serialization | `engine/scientific_contract.py` | `EXACT` | Active | Exact vocabulary serialization; accuracy depends on assigning the correct class at each call site. |
| Formula API percentage adapter | `backend/app/api/v1/endpoints/formulas.py` | `EXACT` transformation with disclosed assumptions | Active | Interpretation depends on explicit solvent roles and supplied/default batch metadata. |

## Advisory And Legacy Paths

| Output or component | Code path | Current class | Production status | Main limitation or promotion requirement |
|---|---|---|---|---|
| Family-prior receptor occupancy | `engine/receptor/binding.py` | `SPECULATIVE` | Exploratory only; removed from production simulator | Odor-family priors are not material-receptor assay data and cannot support numerical occupancy claims. |
| Fixed material hedonic valence | `engine/hedonic_model.py` | `HEURISTIC` | Legacy/advisory | Hand-curated constants and formula rules are not a validated population-specific liking model. Require protocol-defined panel data and held-out evaluation. |
| Release impact, tenacity, diffusion, lift, and balance scores | `engine/pipeline/release_scoring.py` | `HEURISTIC` | Release-gate advisory | Deterministic transformations of heuristic OAV and family rules; scores are not physical measurements. |
| OAV intelligence targets and cliff rules | `engine/pipeline/oav_intelligence.py` | `HEURISTIC` | Advisory | Contains target bands and degraded fallbacks; needs formula-class-specific sensory validation. |
| Family archetypes and pyramid gates | `engine/families/registry.py`, `engine/pipeline/gates.py` | `HEURISTIC`, sometimes literature-informed | Advisory | Useful style constraints, not universal sensory laws. The perfume name and brief remain the design authority. |
| IFRA and allergen rule checks | `engine/ifra_safety.py`, pipeline safety gates | `LITERATURE_DERIVED` rule snapshot | Safety screening only | Depends on source version, product category, natural constituent data, and legal context; not a regulatory certificate. |
| Legacy backend longevity/sillage functions | `backend/app/domain/ingredients/chemistry.py` | `HEURISTIC` | Not called by canonical formula API | Note-percentage rules have no empirical wear calibration. |
| In-sample score correction | `engine/calibration.py` | `HEURISTIC` | Optional legacy feedback path | OLS can train with three samples and reports in-sample metrics; no held-out split or domain validation. It is not `EMPIRICALLY_CALIBRATED`. |
| Wear-test and panel record storage | `engine/calibration/models.py`, `engine/calibration/store.py` | `EXACT` storage/provenance utility | Available | Storage readiness counts are not model validation. Promotion requires a protocol and held-out analysis. |
| Backend outcome/calibration records | `backend/app/services/outcome_store.py` | `EXACT` storage; calibration status depends on analysis | Available | Database fields alone do not establish calibration quality. |
| LLM-generated analysis or suggestions | `backend/app/services/ai/` | `UNKNOWN` unless each claim is independently sourced | Optional renderer/advisor | LLM text must not override deterministic arithmetic, inventory, safety, or evidence labels. |

## Evidence Promotion Checklist

### To `LITERATURE_DERIVED`

- Record a stable source identifier or direct publication/standard URL.
- Record the original unit, matrix, temperature, method, and population when
  relevant.
- Record every conversion and transfer assumption.
- Preserve `UNKNOWN` when the source cannot support the requested context.

### To `EMPIRICALLY_CALIBRATED`

- Define the endpoint before fitting.
- Hash formula inputs and dataset versions.
- Separate training from evaluation by formula, wearer, batch, or another
  leakage-safe grouping appropriate to the claim.
- Report held-out sample count, MAE or another endpoint-appropriate metric,
  uncertainty, and baseline comparison.
- Store the validated domain and reject or downgrade out-of-domain use.

### To Production Receptor Output

- Use material-specific receptor data rather than odor-family labels.
- Include concentration-response, affinity, efficacy, antagonism, and mixture
  conditions.
- Validate the transfer from assay concentration to modeled exposure.
- Keep receptor activation distinct from perceived quality or liking.

## Known System Boundaries

1. The complete finished solvent matrix is not yet represented in canonical
   headspace mole fractions.
2. Density and molecular-weight fallbacks remain in `FormulaState`; their
   source labels and uncertainty must stay visible.
3. Temporal frames are diagnostic approximations, not hours-of-wear claims.
4. Canonical API longevity, sillage, and receptor values are intentionally
   unavailable rather than guessed.
5. The backend repository has existing mypy debt outside the canonical API
   slice; passing runtime tests does not imply repository-wide static typing.
6. Docker configuration is source-backed and package-tested, but image build
   still requires a host with Docker installed.
