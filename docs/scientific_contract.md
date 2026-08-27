# Scientific Contract

This document defines how Perfume Chemistry labels, calculates, and reports
scientific outputs. It is normative for `engine.workbench.PerfumeWorkbench` and
the formula API. The more detailed code-path audit is in
[`model_inventory.md`](model_inventory.md).

## Core Rule

Every output must say what kind of claim it is. A deterministic calculation is
not automatically a measurement, and a literature value is not automatically
valid in a different matrix. Missing data remains missing; the system must not
invent density, precision, receptor activity, longevity, or sillage.

The vocabulary is implemented by
[`engine/scientific_contract.py`](../engine/scientific_contract.py):

| Class | Meaning | Required disclosure |
|---|---|---|
| `EXACT` | The result follows exactly from stated inputs and an algebraic or discrete rule. | Inputs, equation or rule, units, and any rounding. `EXACT` does not assert that measured inputs are error-free. |
| `LITERATURE_DERIVED` | A value or transformation is traceable to identified literature or a standard. | Source, matrix or population, conversion, and applicability limits. |
| `EMPIRICALLY_CALIBRATED` | A model has been fitted and evaluated against representative observed outcomes. | Dataset identity, split policy, sample count, metric, uncertainty, and model version. |
| `HEURISTIC` | A useful engineering approximation lacks sufficient validation for predictive authority. | Formula, assumptions, known failure modes, and no measurement language. |
| `SPECULATIVE` | A research hypothesis or proxy lacks the required material-specific evidence. | Explicit non-production status and evidence needed for promotion. |
| `UNKNOWN` | The value is unavailable or cannot be supported from current evidence. | Why it is unavailable and which input or assay would make it calculable. |

The vocabulary is ordinal only in evidence posture, not in usefulness. An
`EXACT` unit conversion can be less decision-relevant than a well-calibrated
empirical model.

## Measurement And Provenance

The JCGM vocabulary treats a measurement result as a quantity value together
with relevant information, normally including uncertainty. Measurement
uncertainty characterizes the dispersion attributable to the measurand from the
information used. Therefore:

- Modeled headspace ppm is not described as measured headspace ppm.
- A value labeled `EXACT` must state that exactness belongs to the equation.
- User-supplied standard uncertainties are carried separately from algebraic
  rounding error.
- Claim-level evidence is split when one response combines exact arithmetic
  with literature-derived uncertainty propagation.
- Evidence descriptors include `basis`, `sources`, `assumptions`, and
  `limitations`, following the same provenance intent as W3C PROV-O.

References:

- [JCGM VIM 2.9: measurement result](https://jcgm.bipm.org/vim/en/2.9.html)
- [JCGM VIM 2.26: measurement uncertainty](https://jcgm.bipm.org/vim/en/2.26.html)
- [JCGM 100:2008 Guide to uncertainty in measurement](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)

## Bottle Addition

The additive solver works on active-material mass fraction. Define:

- `M`: current total bottle mass in grams
- `m_a`: current active-material mass in grams
- `s`: active mass fraction of the stock solution
- `t`: target active mass fraction in the final bottle
- `x`: stock mass to add in grams

Mass conservation gives:

```text
(m_a + s*x) / (M + x) = t
x = (t*M - m_a) / (s - t)
```

The calculation is valid for an additive correction when:

```text
0 <= m_a/M <= t < s <= 1
```

If `t < m_a/M`, addition cannot reach the target because adding mass cannot
remove active material. If `t >= s`, that stock cannot raise the bottle to the
target. Both are errors, not negative or infinite doses.

Mass fraction follows the IUPAC definition of constituent mass divided by
mixture mass. The corresponding concentration is:

```text
active_ppm_w/w = active_mass_fraction * 1,000,000
```

Reference: [IUPAC Gold Book: mass fraction](https://goldbook.iupac.org/terms/view/M03722).

### Density And Pipettes

- Mass output does not require density.
- Volume is calculated only when the caller supplies a positive stock density:
  `volume_uL = 1000*x/density_g_mL`.
- Density is never silently set to `1.0 g/mL` in the bottle solver.
- A pipette plan is produced only when density and a pipette profile are both
  present.
- The exact volume is rounded to the nearest declared increment.
- If the rounded dose is below the declared minimum, the plan is infeasible.
  The solver does not round upward to the minimum and change the formula.
- Staged doses contain integer increments and respect the declared maximum
  single-step volume.
- `standard_uncertainty_ul` is the independent random standard uncertainty of
  one transfer. `systematic_standard_uncertainty_ul` is shared across transfers.

ISO 8655-2 defines metrological requirements for piston pipettes. This project
does not claim ISO conformity from a user-entered profile; calibration status
and handling technique remain external inputs.

Reference: [ISO 8655-2:2022](https://www.iso.org/standard/68797.html).

### Standard Uncertainty

For `x = (tM - m_a)/(s - t)`, with the target treated as an exact setpoint and
declared inputs treated as uncorrelated:

```text
dx/dM   =  t/(s-t)
dx/dm_a = -1/(s-t)
dx/ds   = -x/(s-t)
```

The combined standard uncertainty is the root-sum-square of each sensitivity
coefficient multiplied by its declared standard uncertainty. For
`v = 1000*x/rho`, mass and density components are propagated in the same way.
The output is zero only when every contributing declared uncertainty is zero.

For a plan with `n` transfers, per-transfer random uncertainty `u_r`, and
shared systematic uncertainty `u_s`, the delivered-volume standard uncertainty
is:

```text
u_plan = sqrt(n*u_r^2 + (n*u_s)^2)
```

The random terms are treated as independent. The systematic term is treated as
fully correlated because the same declared instrument effect applies to every
transfer. The plan uncertainty, density uncertainty, bottle-mass uncertainty,
active-mass uncertainty, and stock-fraction uncertainty are then propagated by
first-order sensitivity coefficients into
`resulting_active_mass_fraction_standard_uncertainty`.

The response evidence therefore separates:

- `stock_mass_arithmetic`: `EXACT`
- `pipette_plan`: `EXACT` for discrete arithmetic on the declared profile
- `uncertainty_propagation`: `LITERATURE_DERIVED`
- `pipette_delivery_uncertainty`: `LITERATURE_DERIVED`

Unmodeled covariance between bottle, composition, or density inputs remains a
limitation. Zero means no uncertainty was declared; it does not prove exact
measurement.

## PPM, ODT, And OAV

The canonical formula path is:

```text
raw uL -> active uL -> mass -> moles -> mole fraction
       -> modeled partial pressure -> vapor ppm -> OAV
```

`FormulaState` preserves raw dose, active dose, ppm, odor detection threshold
(ODT), and odor activity value (OAV).

```text
active_aromatic_concentrate_ppm_i = active_mass_i / sum(active_mass) * 1,000,000
```

This arithmetic is `EXACT` only when every active row has a sourced density.
If any density is missing, `active_concentrate_ppm_w_w` is `null` and its
evidence class is `UNKNOWN`; the 1 g/mL fallback remains available only inside
the explicitly heuristic headspace model. If a carrier or finished-product
solvent matrix is omitted, even an exact active-concentrate value is not a
finished-product regulatory ppm and that omission remains a limitation.

For a monomolecular material with an air threshold:

```text
OAV = modeled_vapor_ppm / ODT_air_ppm
```

Natural mixtures covered by
[`natural_absolute_decomposition.py`](../engine/pipeline/natural_absolute_decomposition.py)
use composite constituent OAV rather than a monomolecular natural-material
proxy.

Composite OAV estimates olfactory headspace contribution from a documented
constituent model. It must not be reused as a natural's regulatory constituent,
allergen, or IFRA composition. Without a versioned source, category, product
concentration basis, and supplier/batch composition, the canonical workbench
returns regulatory status `unverified`.

The current headspace result is `HEURISTIC`, even when an individual ODT is
literature-derived, because:

- Liquid-phase mole fractions are normalized over aromatic actives rather than
  the complete ethanol-water-solvent matrix.
- Activity coefficients and physical properties may use fallbacks.
- Vapor ppm is modeled and has not been calibrated against formula-specific
  headspace measurements.
- Detection thresholds depend on matrix and psychophysical method.

The matrix dependence of odor thresholds has been demonstrated experimentally:
[Perry and Hayes, 2016](https://pubmed.ncbi.nlm.nih.gov/28231131/).

## Scientific Coverage Scope

The data-spine completeness percentage uses the full local material catalogue
as its denominator. It is a project-health and backfill metric. It is not a
formula-confidence input because most catalogue rows are absent from any one
formula.

Formula release confidence is scoped to the formula's actual model inputs.
The preflight reports identity, MW, VP, ODT, OAV, HSP, and structured IFRA
coverage for the parsed materials, while the dedicated `odt_authority`,
`data_authority`, and `material_identity_and_physics` checks own penalties and
fail-closed decisions. Missing Antoine constants, HSP, receptor, or regulatory
records remain visible as unsupported or advisory axes; the pipeline does not
invent those values and does not treat an absent IFRA record as proof that a
material is unrestricted.

The aggregate confidence adjustment is labeled `preflight_evidence_penalty`.
Its separately reported `science_preflight_penalty` contains only the
formula-scoped science-coverage component; it must not be used as an alias for
ODT authority, data authority, knowledge quality, or other preflight evidence.

This scoping follows the JCGM measurement-model principle that an output is a
function of the input quantities on which it depends. Uncertainty or
completeness gaps in unrelated catalogue rows are not input quantities for the
formula result:
[JCGM 100:2008, section 4.1](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf).

## Activity-Coefficient Authority

IUPAC defines a liquid-mixture activity coefficient through chemical potential
and the complete set of mixture mole fractions. The canonical headspace path
currently uses a Hansen-distance, regular-solution-style heuristic when a
material-specific profile constant is absent. Both paths are
`HEURISTIC_UNCALIBRATED`; a non-unity gamma is not evidence that the value is
correct.

The `oav_physics_gamma` gate reports each material's source and authority. For
monomolecular OAV only, it also reports the OAV obtained by replacing the point
estimate with gamma=1. This is a comparison scenario that exposes model
leverage. It is not an uncertainty interval, not a lower or upper bound, and
not applicable to natural-composite OAV, whose constituents have separate
activity estimates.

UNIFAC is not active. The original method requires molecular functional-group
assignments and group-pair interaction parameters. Promotion additionally
requires a versioned implementation and validation in the intended perfume
matrix/domain. Package availability alone is insufficient:

- [IUPAC Gold Book: activity coefficient](https://goldbook.iupac.org/terms/view/A00116)
- [Fredenslund, Jones, and Prausnitz, 1975](https://doi.org/10.1002/aic.690210607)

### Diluted-stock carrier reconciliation

The `solvent_matrix` gate reads the carrier and concentration basis already
attached to each parsed stock. It never assumes that the finished bottle is
entirely ethanol, and it does not infer an exact carrier quantity from a bare
percentage. IUPAC defines mass fraction and volume fraction as different
quantities; only an explicit volume fraction supports a direct
residual-volume calculation:

- [IUPAC Gold Book: fraction](https://goldbook.iupac.org/terms/view/F02494)
- [IUPAC Gold Book: mass fraction](https://goldbook.iupac.org/terms/view/M03722)
- [IUPAC Gold Book: volume fraction](https://goldbook.iupac.org/terms/view/V06643)

For diagnostic reconciliation, the gate may show `raw stock volume x
(1 - declared fraction)` as a `RESIDUAL_VOLUME_PROXY`. Named and unknown
carriers are reported separately, along with the actual declared bulk-matrix
components. These proxy carrier volumes are not silently injected into
headspace mole fractions, because doing so could double-count a carrier or
convert a mass-basis declaration into a volume basis.

The local DPG reconciliation property records use the Shell DPG technical data
sheet (molecular weight 134.2 g/mol and density 1027 kg/m3 at 20 C). This
supports the identity/property conversion only; it does not establish the
preparation basis or batch composition of a user's diluted stock:
[Shell DPG Technical Data Sheet U1521](https://www.shell.com/content/dam/shell/assets/en/business-functions/chemical/documents/tds-dpg-updated-sept-2023.pdf).

## Temporal, Longevity, And Sillage

The current temporal simulator integrates a bounded-step exponential
relative-loss approximation based on canonical modeled headspace escaping
tendency and molecular weight. Activity coefficients and natural-composite
headspace are recomputed as the modeled composition changes. It remains
`HEURISTIC_UNCALIBRATED`: the relative-loss scale has not been fitted to
measured blotter or skin depletion curves and does not explicitly model solvent
evaporation, diffusion, or skin absorption.

Consequently the canonical API returns:

```json
{
  "estimated_longevity_hours": null,
  "estimated_sillage": null
}
```

Temporal OAV frames remain available as heuristic diagnostic outputs.
Their `remaining_quantity_basis` is
`heuristic_remaining_stock_volume_equivalent_ul`; reports must call the derived
percentage an uncalibrated loss index, not measured evaporation.

Optimizer and release-scoring surfaces may retain bounded 0-100 indices for
relative search and diagnosis. These indices are not outcome predictions. The
release payload therefore attaches `score_contract.classification =
HEURISTIC_DIAGNOSTIC_INDICES`, per-axis authority, an empty
`release_authorized_axes` list, and `release_authority = false`. In particular,
numeric `longevity`, `sillage`, and `skin_performance` indices must never be
presented as hours of skin life, measured projection/sillage, or a validated
skin outcome.

The legacy Chemical Life Graph follows the same boundary. Its temporal
structure may report explicitly labeled `model-min` or `model-hr` windows for
top/base dominance and a relative linearity diagnostic. It must emit
`longevity_hours = null`, mark temporal authority
`HEURISTIC_UNCALIBRATED`, and must not let model-window timing change the
formula health score.

## Intervention Safety Authority

An addition-only rescue changes the finished-product composition. Quantitative
IFRA limits apply to the finished consumer product, and conformity
documentation does not replace a product safety assessment:

- [IFRA: Using the Standards](https://ifrafragrance.org/using-the-standards)
- [IFRA: Certification of IFRA Standards](https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards/certification-of-ifra-standards)

Accordingly, a client-supplied `safety_status = pass` is an observation, not
authority. `rank_interventions()` may rank a safety-passing candidate only when
all of the following are present:

1. authority is `versioned_finished_product_assessment`;
2. evidence has a non-unknown scientific classification and at least one
   traceable source;
3. the assessment is bound to the exact 64-character SHA-256 formula-state
   identity supplied by the intervention request; and
4. the assessed active concentration covers the achieved concentration after
   stock dilution and dispensing-increment rounding.

The public `/lab/interventions` request deliberately cannot supply this trusted
evidence package. It therefore remains diagnostic and fails closed: even a
caller-declared `pass` is rejected from ranking. A future server-side assessment
adapter may attach the required versioned binding after evaluating the whole
finished formula in its product category. Neither a ranked diagnostic nor an
IFRA conformity statement is permission for skin use.

The exact aliquot trial planner remains separate. It preserves the source
bottle, calculates the requested final concentration from current active mass,
and withholds skin authorization while safety is unverified.

## Allergen-Label Reconstruction Authority

An ingredient-list fragrance-allergen declaration supports constituent
presence above the applicable notification threshold. It does not establish
that the constituent was added as a standalone aroma chemical, identify which
natural complex substance supplied it, or quantify a natural-material dose.
Under Article 19 of Regulation (EC) No 1223/2009, ingredients below 1% may be
listed in any order. Therefore package position is not a concentration scale:
[Regulation (EC) No 1223/2009, Article 19](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009R1223).

The expanded fragrance-allergen regime continues to apply thresholded
individual labelling in the finished product; it does not convert the label
into a formula disclosure:
[Commission Regulation (EU) 2023/1545](https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng).

Natural complex substances additionally have source and batch composition
variation. Typical compositional data are useful for screening but are not the
analytical composition of the target bottle:
[IFRA NCS Task Force procedure](https://ifrafragrance.org/docs/default-source/guidelines/ifra-ncs-tf-procedure-to-derive-ncs-compositional-data-rev1---final-june-23-2021.pdf).

Accordingly:

- label-derived evidence is retained as non-material constituent evidence;
- it cannot create a standalone material hypothesis;
- raw-material source and concentration remain unresolved;
- list order cannot generate concentration ranges or a reconstruction score;
- absent-label upper bounds are withheld unless the applicable market/date
  regime and complete required-allergen universe are explicitly verified.

## Receptor Biology

Production analysis does not infer numerical receptor activation from odor
family labels. Odorant mixtures commonly show receptor-specific antagonism,
suppression, addition, and inverse agonism. Quantitative receptor outputs need
material-specific affinity, efficacy, dose-response, and mixture data.

The production contract is therefore:

```json
{
  "receptor_activation": null,
  "receptor_source": "unavailable:material_specific_assay_required"
}
```

The exploratory family-prior code may remain in the repository, but it is
`SPECULATIVE` and must not feed production scoring or API analysis.

References:

- [Zak et al., 2020, mixture modulation of receptor response patterns](https://pubmed.ncbi.nlm.nih.gov/32061665/)
- [Reddy et al., 2020, receptor inhibition in odor encoding](https://pubmed.ncbi.nlm.nih.gov/32470365/)
- [Oka et al., 2004, olfactory receptor antagonism](https://pubmed.ncbi.nlm.nih.gov/14685265/)

## Calibration Promotion Rule

An output may be labeled `EMPIRICALLY_CALIBRATED` only when all of the following
are recorded:

1. The observed endpoint and protocol are defined.
2. Formula and dataset identities are immutable or content-hashed.
3. Training and evaluation observations are separated by a documented policy.
4. Performance is reported on held-out representative observations.
5. Sample count, error metric, uncertainty, model version, and date are stored.
6. The calibration is applied only within its validated domain.

An in-sample regression with a small minimum sample count is still a
`HEURISTIC`, even if it stores a slope, intercept, R-squared, and MAE.

## API Interpretation Rules

`POST /api/v1/formulas/analyze-formula` uses two explicit interpretations:

- If any row has `role: "solvent"`, all percentages are finished-product volume
  fractions. Solvent rows are excluded from the current aromatic state, and
  that omission is disclosed.
- If no solvent rows exist, percentages are concentrate composition. They are
  scaled by `concentration_percent`; a missing value uses 15% and records that
  assumption.
- Missing `total_volume_ml` uses a 100 mL calculation basis and records that
  assumption.
- Duplicate material rows are combined using an effective active fraction that
  preserves total raw and active volume.

Optional language-model services may explain deterministic outputs, but they
are not the authority for arithmetic, safety, ppm, ODT, OAV, or evidence class.
