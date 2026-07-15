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

## Temporal, Longevity, And Sillage

The current temporal simulator applies an exponential loss-rate approximation
based on vapor pressure, activity coefficient, and molecular weight. It is
`HEURISTIC`. It has not been fitted to measured blotter or skin depletion curves
and does not explicitly model solvent evaporation, diffusion, or skin
absorption.

Consequently the canonical API returns:

```json
{
  "estimated_longevity_hours": null,
  "estimated_sillage": null
}
```

Temporal OAV frames remain available as heuristic diagnostic outputs.

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
