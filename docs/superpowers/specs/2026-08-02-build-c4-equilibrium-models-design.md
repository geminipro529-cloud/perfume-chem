# Build C4 equilibrium-model design

Status: accepted by Sol on 2026-08-02
Phase parent: `2fef4916ed3259f839599e8c9aeedf00261e5350`
Authoritative requirement: `D:\.prompts\perfume chem\SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md`, C4.1-C4.6 and the C4 exit gate

## Decision

C4 will support exactly one executable equilibrium family: a transparent ideal-solution Raoult baseline. It is a theoretical comparison and failure-detection baseline, not measured headspace, a calibrated perfume-release model, a non-ideal activity model, or production truth.

The following C3 families remain explicitly unavailable in C4:

- `HENRY_LAW_DILUTE_BASELINE`: no matrix-specific validated Henry assertions are bound.
- `EMPIRICAL_MATRIX_CORRECTION`: no validated Build B training/validation set is bound.
- `UNIFAC_OR_MODIFIED_UNIFAC`: no versioned subgroup decomposition, interaction-parameter table, coverage report, or reference benchmark implementation exists.
- `IMPORTED_COSMO_RS`: no licensed/versioned calculation import with quantum-chemistry, conformer, sigma-profile, condition, and digest provenance exists.

The legacy `engine/thermo/headspace.py` and `engine/thermo/activity.py` path is not adapted or promoted. It silently normalizes composition, defaults missing molecular weight to 200 g/mol, substitutes zero vapor pressure, and applies an uncalibrated Hansen-distance heuristic while explicitly declaring UNIFAC inactive. C4 creates a separate fail-closed implementation under `engine/physics`.

No production caller changes, database writes, schema changes, migrations, artifact regeneration, or C5 work are in scope.

## Scientific definition

For each liquid component `i`, the supported calculation is:

`p_i = x_i * p_i*`

where:

- `x_i` is the declared or explicitly mass-to-mole-derived liquid amount fraction;
- `p_i*` is a C1-authorized numeric pure-component vapor-pressure assertion in Pa at the exact matrix temperature;
- the activity coefficient is fixed and disclosed as `gamma_i = 1`;
- `p_i` is the component partial pressure in Pa;
- `p_i / P_system` is reported as the component's fraction of the declared system pressure, without renormalizing away inert/background gas.

IUPAC defines amount fraction as constituent amount divided by total mixture amount, and its Raoult-law entry relates equilibrium component fugacity to activity and the pure-component reference. The ideal baseline is the `gamma_i = 1` limiting comparison, not a claim that the perfume matrix is ideal.

Primary terminology sources:

- IUPAC Gold Book, [amount fraction](https://goldbook.iupac.org/terms/view/A00296/plain), DOI `10.1351/goldbook.A00296`.
- IUPAC Gold Book, [Raoult's law](https://goldbook.iupac.org/terms/view/15349/plain), DOI `10.1351/goldbook.15349`.
- IUPAC Gold Book, [pressure and partial pressure](https://goldbook.iupac.org/terms/view/P04819), DOI `10.1351/goldbook.P04819`.

## Input binding

### C1 selected properties

Each matrix component is bound to two `SelectedNumericPropertyInput` values:

1. `ThermophysicalProperty.VAPOR_PRESSURE`, numeric, unit `Pa`, strictly positive, at the exact matrix temperature.
2. `ThermophysicalProperty.MOLECULAR_WEIGHT`, numeric, unit `g/mol`, strictly positive.

Each input carries its `PropertyRequest`, `PropertySelectionResult`, component ID, and a stable C4 content hash. Construction fails unless:

- selection status is `SELECTED`, never advisory or withheld;
- authority is `AUTHORIZED_FOR_SCOPED_PROPERTY`;
- request and selection hashes bind exactly;
- the selected value is a numeric observation, not an unevaluated C1 equation declaration;
- source, assertion hash, conditions, uncertainty, datum hash, and canonical unit are present and consistent.

The C1 `VaporPressureRepresentation` remains a declaration-only contract. C4 does not invent an Antoine, Wagner, DIPPR, or other evaluator. Such a selection abstains until a separately verified property evaluator exists.

### C2 matrix and environment

The adapter consumes the embedded `MatrixAwareModelRequest` already bound by C3. It requires:

- `CompositionCompleteness.EXACT` and no missing fields;
- one common component basis from `MOLE_FRACTION`, `MASS_FRACTION`, `MASS`, or `AMOUNT`;
- exact units: fraction unit `1`, temperature `K`, pressure `Pa`, and common absolute units where applicable;
- `gas_comparison=true`;
- an exact positive matrix temperature and system pressure;
- matching environment temperature;
- stage `STOCK_SOLUTION`, `CONCENTRATE`, or `FINISHED_PERFUME`;
- environment `SEALED_EQUILIBRIUM_VIAL` or `OPEN_LIQUID_SURFACE`;
- explicit `single_liquid_phase` in both matrix assumptions and C3 applicability context;
- C3 identity hashes and available-property declarations matching the bound C4 property input set.

`VOLUME_FRACTION`, `VOLUME`, mixed bases, and implicit unit conversion are unsupported because they require additional density/conversion authority.

### C3 request reference

`IdealRaoultInputSet` is immutable, sorted by component/property, and hash-bound. The versioned request must contain exactly one `ModelInputReference`:

- role: `c4_equilibrium_input_set`
- input ID: the declared input-set ID
- content SHA-256: the input-set hash

Missing, duplicate, extra, or mismatched references produce `INSUFFICIENT_INPUT`; they never fall back.

## Composition and conservation

- Mole-fraction input is used only after exact C2 closure has passed.
- Mass-fraction and absolute-mass input are converted through `n_i = m_i / MW_i`, then divided by `sum(n_i)`.
- Absolute-amount input is divided by `sum(n_i)` only when every component uses the same explicit amount unit.
- Fraction bases are never silently normalized.
- Absolute mass must match the declared total mass in the same unit within a fixed absolute tolerance of `1e-12`.
- All sums use `math.fsum`; the output records mole-fraction closure, input-basis closure, mass round-trip closure when applicable, and partial-pressure summation closure.

The model abstains if a denominator is non-positive, closure fails, units differ, or any required property is invalid.

## Applicability and boiling guard

The available ideal release supports only `PREDICT_EQUILIBRIUM_HEADSPACE`. Its adapter evaluates applicability before computation.

- Missing or unbound data yields `INSUFFICIENT_INPUT` with exact missing-input codes.
- Unsupported matrix stage, environment, basis, phase behavior, or unit yields `OUTSIDE_APPLICABILITY_DOMAIN` with exact reasons.
- A total ideal bubble pressure greater than the declared system pressure (tolerance `1e-12` Pa) yields `OUTSIDE_APPLICABILITY_DOMAIN`; C4 will not report a single-liquid equilibrium state that violates its own pressure assumption.
- Only an in-domain request reaches `compute`.

The release evidence class is `THEORETICAL_BASELINE`, `may_feed_oav_screening=false`, and its permitted/forbidden wording is carried unchanged through C3 results.

## Output contract

The C3 `ModelOutput` has quantity `equilibrium_headspace_partial_pressures`, unit `Pa`, and a canonical payload with:

- schema and equation identity;
- request, matrix, environment, formula, input-set, and release hashes;
- declared temperature and system pressure;
- sorted component records containing component ID, source identity hash, liquid mole fraction, selected pure vapor pressure, fixed activity coefficient, partial pressure, and system-pressure fraction;
- total ideal bubble pressure and total modeled system-pressure fraction;
- explicit assumptions and closure checks;
- an explicit statement that inert/background gas is not modeled and gas fractions are not renormalized.

Input uncertainty is preserved in the bound property evidence but not propagated numerically in C4. The computation returns `UncertaintyDescriptor.UNKNOWN` and a `C5_UNCERTAINTY_PROPAGATION_REQUIRED` warning. C5 remains closed until C4 passes.

## Unavailable-family authority

Unavailable adapters expose immutable `ModelRelease` records and are registered through the C3 router. The router therefore returns an `ABSTAINED` result with `MODEL_NOT_VALIDATED` before any unavailable adapter can compute.

- UNIFAC is never labeled active without a declared original/Dortmund/other parameter version, molecular subgroup decomposition, combinatorial and residual terms, temperature dependence, interaction parameters, complete coverage, numerical tests, and trusted reference benchmarks. Pure-molecule decomposition is forbidden for naturals, opaque bases, and unknown supplier blends.
- COSMO-RS remains a separate imported-computation family and cannot become available from an interface stub.
- Empirical correction remains unavailable without immutable Build B train/validation provenance.
- Hansen distance is not UNIFAC and remains a legacy heuristic only.

No synthetic second computed model is created merely to exercise C3 comparison. Advanced comparison is not applicable until another model independently passes its own authority gate.

## Verification

C4 acceptance requires, at minimum:

- analytic pure-component and binary benchmarks;
- mole-, mass-fraction, absolute-mass, and amount-basis tests;
- exact unit, temperature, identity, source, assertion, and input-reference binding tests;
- mass/mole/partial-pressure closure tests;
- system-pressure boiling guard;
- matrix/environment/phase/basis abstention tests;
- explicit unavailable UNIFAC, COSMO-RS, Henry, and empirical releases;
- proof that the legacy Hansen/headspace path is not imported or called;
- C3 router integration and serialization/hash round trips;
- focused mutation tests that fail when the Raoult multiplication or pressure guard is removed;
- focused pytest, ancestor regressions C1-C3/C0, root suite, dependency check, Ruff, basedpyright, mypy, archive verification, protected-database verification, and exact-commit replay;
- a bounded DeepLuna Fast final audit followed by independent Sol reproduction.

The gate passes only from executable evidence. A worker, document, or interface declaration cannot promote C4 by assertion.
