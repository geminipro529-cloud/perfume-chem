# Build C1 Thermophysical Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Do not use
> subagent-driven development: project policy forbids Codex subagents. DeepLuna
> Fast may perform only bounded read-only audits; Sol owns all design choices,
> implementation review, scientific interpretation, and final acceptance.

**Goal:** Add condition-aware, provenance-rich thermophysical property
contracts that consume Build B selected assertions and withhold unsupported
release-grade calculations.

**Architecture:** Add pure immutable contracts under `engine.physics`, with no
SQLAlchemy or backend dependency. Extend the existing B2 reconstruction payload
additively so a pure adapter can recover stored observation conditions, sources,
uncertainty, applicability, and provenance. A deterministic selector accepts one
explicit B2 assertion, never searches for another value, never calls a legacy
estimator, and never evaluates a thermodynamic equation.

**Tech Stack:** Python 3.11, frozen dataclasses, string enums, the existing
`engine.calibration.hashing` canonical JSON/SHA-256 implementation, pytest,
pytest-asyncio, Ruff, and basedpyright/mypy where already supported.

---

## Execution boundary and recovery evidence

- Phase: Build C, C1 only. C2 remains closed until the C1 commit and post-commit
  gate pass.
- C1 phase parent: `fddc07c12d914b8de9f81f2ecbb5c9423a6880a6`.
- Accepted design checkpoint:
  `488f05c7070330e06d9a39690b7438210065c4ee`.
- Implementation parent: the commit that seals this plan; record its full SHA in
  the C1 gate after the plan commit succeeds.
- Preserved prewrite archive:
  `D:\.backups\perfume-chem\build-c1-prewrite-20260802T163623+0700.tar`.
- Archive SHA-256:
  `ee3f9963fbb2f3937642c3ebd60ecac37bfed6fe6e2e1fe722af7288db305237`.
- Supported interpreter:
  `D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe`.
- All commands run without a PTY, with `NO_COLOR=1`, `TERM=dumb`, explicit
  timeouts, and separate stdout/stderr for gate-bearing runs.
- Never inspect or print environment values. Never modify a database or create a
  migration in C1.

## File map

- Create `engine/physics/__init__.py`: public C1 exports only.
- Create `engine/physics/properties.py`: property, identity, condition, datum,
  source, uncertainty, and result vocabulary.
- Create `engine/physics/vapor_pressure.py`: closed vapor-pressure
  representation schemas; no equation evaluator.
- Create `engine/physics/selection.py`: B2 reconstruction adapter and fail-closed
  selector.
- Create `tests/test_c1_thermophysical_contracts.py`: pure C1 RED/GREEN contract
  tests.
- Modify `backend/app/services/lab_properties.py`: expose existing B2 observation
  fields in reconstruction; no persistence change.
- Modify `backend/tests/unit/test_b2_property_service.py`: lock the additive B2
  reconstruction fields.
- Create `docs/verification/c1/thermophysical_contracts_gate.json`: machine gate
  evidence.
- Create `docs/verification/c1/thermophysical_contracts_gate.md`: human gate
  evidence.
- Create `docs/verification/c1/logs/*`: non-PTY stdout/stderr and bounded
  DeepLuna receipt generated during final verification.

### Task 1: Add the general thermophysical contract vocabulary

**Files:**

- Create: `tests/test_c1_thermophysical_contracts.py`
- Create: `engine/physics/properties.py`

- [ ] **Step 1: Write the failing vocabulary, canonical-scope, datum, and
  uncertainty tests**

Start the test file with imports from `engine.physics.properties` for the names
below and tests that assert the exact enum values and malformed-shape rejections.
The aggregate `engine.physics` public import is intentionally deferred to Task 5:

```python
REQUIRED_PROPERTIES = {
    "vapor_pressure",
    "molecular_weight",
    "density",
    "boiling_point",
    "enthalpy_of_vaporization",
    "water_solubility",
    "solvent_solubility",
    "logp",
    "logkow",
    "henry_constant",
    "activity_coefficient_parameters",
    "diffusion_coefficient",
    "mass_transfer_parameters",
    "substrate_sorption_parameters",
    "heat_capacity",
    "phase_data",
}

REQUIRED_UNCERTAINTY_KINDS = {
    "STANDARD_UNCERTAINTY",
    "INTERVAL",
    "EMPIRICAL_DISTRIBUTION",
    "PARAMETER_COVARIANCE",
    "BOUNDED_RANGE",
    "UNKNOWN",
}


def test_c1_property_and_uncertainty_vocabulary_is_closed():
    assert {item.value for item in ThermophysicalProperty} == REQUIRED_PROPERTIES
    assert {item.value for item in UncertaintyKind} == REQUIRED_UNCERTAINTY_KINDS


def test_canonical_scope_hash_is_mapping_order_independent():
    left = CanonicalScope.from_mapping({"temperature_k": 298.15, "matrix": "air"})
    right = CanonicalScope.from_mapping({"matrix": "air", "temperature_k": 298.15})
    assert left == right
    assert left.sha256 == right.sha256


@pytest.mark.parametrize(
    "payload",
    (
        {"schema": "c1-uncertainty-v1", "kind": "STANDARD_UNCERTAINTY", "value": 0.5, "unit": "Pa"},
        {"schema": "c1-uncertainty-v1", "kind": "INTERVAL", "interval_type": "CONFIDENCE", "coverage_probability": 0.95, "lower": 6.0, "upper": 8.0, "unit": "Pa"},
        {"schema": "c1-uncertainty-v1", "kind": "EMPIRICAL_DISTRIBUTION", "values": [6.8, 7.0, 7.2], "unit": "Pa"},
        {"schema": "c1-uncertainty-v1", "kind": "PARAMETER_COVARIANCE", "parameter_names": ["A", "B"], "matrix": [[1.0, 0.2], [0.2, 2.0]], "parameter_units": {"A": "1", "B": "K"}},
        {"schema": "c1-uncertainty-v1", "kind": "BOUNDED_RANGE", "lower": 5.0, "upper": 9.0, "unit": "Pa"},
        {"schema": "c1-uncertainty-v1", "kind": "UNKNOWN", "reason": "not reported"},
    ),
)
def test_all_six_uncertainty_shapes_validate(payload):
    assert UncertaintyDescriptor.from_mapping(payload).kind.value == payload["kind"]
```

Also add explicit failures for NaN/Infinity, negative standard uncertainty,
reversed intervals, invalid coverage probability, empty empirical samples,
duplicate covariance parameter names, non-square/asymmetric covariance, unit-key
mismatch, reversed bounded range, and numeric fields attached to `UNKNOWN`.

- [ ] **Step 2: Run the focused test to prove RED**

Run:

```powershell
$env:NO_COLOR='1'; $env:TERM='dumb'
D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B -m pytest -p no:cacheprovider --color=no tests/test_c1_thermophysical_contracts.py -q
```

Expected: FAIL during collection because `engine.physics` does not exist. A
timeout or unrelated import failure is not the expected RED result.

- [ ] **Step 3: Implement the minimal immutable general contracts**

`engine/physics/properties.py` must implement this closed API manifest. This is a
signature manifest, not partial executable code:

```text
ThermophysicalContractError extends ValueError

ThermophysicalProperty values:
  vapor_pressure, molecular_weight, density, boiling_point,
  enthalpy_of_vaporization, water_solubility, solvent_solubility, logp,
  logkow, henry_constant, activity_coefficient_parameters,
  diffusion_coefficient, mass_transfer_parameters,
  substrate_sorption_parameters, heat_capacity, phase_data

PropertyValueKind values:
  NUMERIC, CATEGORICAL, INTERVAL, DISTRIBUTION, CENSORED

UncertaintyKind values:
  STANDARD_UNCERTAINTY, INTERVAL, EMPIRICAL_DISTRIBUTION,
  PARAMETER_COVARIANCE, BOUNDED_RANGE, UNKNOWN

ClaimGrade values: RELEASE_GRADE, EXPLORATORY
SelectionStatus values: SELECTED, ADVISORY, WITHHELD

CanonicalScope fields: canonical_json: str; sha256: str
CanonicalScope.from_mapping(Mapping[str, Any]) -> CanonicalScope
CanonicalScope.to_mapping() -> dict[str, Any]

PropertyIdentity fields:
  identity_scope: str; subject: CanonicalScope; content_sha256: computed str
PropertyIdentity.from_mapping(Mapping[str, Any]) -> PropertyIdentity

PropertyConditions fields:
  scope: CanonicalScope; temperature_k: float | None;
  pressure_pa: float | None; relative_humidity_percent: float | None;
  matrix: str | None; phase: str | None; purity_fraction: float | None
PropertyConditions.from_mapping(Mapping[str, Any]) -> PropertyConditions
PropertyConditions.supports(PropertyConditions) -> bool

PropertyDatum fields:
  value_kind; canonical_unit; numeric_value; categorical_value;
  interval_lower; interval_upper; distribution; censoring_qualifier;
  censoring_limit; content_sha256
PropertyDatum.from_b2(Mapping[str, Any]) -> PropertyDatum

SourceReference fields:
  source_kind; source_version_id; extraction_record_id; model_source_id;
  locator; content_sha256
SourceReference.from_b2_observation(Mapping[str, Any]) -> SourceReference
SourceReference.from_model_mapping(Mapping[str, Any]) -> SourceReference

UncertaintyDescriptor fields:
  kind: UncertaintyKind; payload: CanonicalScope; content_sha256: computed str
UncertaintyDescriptor.from_mapping(Mapping[str, Any]) -> UncertaintyDescriptor
UncertaintyDescriptor.unknown(str) -> UncertaintyDescriptor
```

Use `canonical_json_bytes` and `stable_json_hash`; do not write another hash
algorithm. `CanonicalScope` accepts only mappings and returns a new dictionary on
read. Conditions preserve every supplied key while validating known convenience
fields: temperature and pressure are positive, humidity is 0..100, purity is
0..1, and known strings are nonblank. `supports` requires every canonical
requested key/value to be present and equal, while request-to-assertion equality
uses complete `CanonicalScope` equality.

`PropertyDatum` must accept exactly the five B2 value kinds (`NUMERIC`,
`CATEGORICAL`, `INTERVAL`, `DISTRIBUTION`, `CENSORED`), require one nonblank
canonical unit, and enforce the same mutually exclusive value shapes as B2.
`SourceReference` must enforce exactly one complete source form: B2
`source_version_id` plus `extraction_record_id`, or a declared model `source_id`;
both forms preserve a canonical locator.

For `UncertaintyDescriptor.from_mapping`, require schema
`c1-uncertainty-v1`, reject unknown fields, enforce finite values and the exact
shape in Step 1, require covariance symmetry, and never convert `UNKNOWN` into a
number. The observation adapter added later may construct a standard descriptor
from B2's explicit `standard_uncertainty`; it must not call
`engine.uncertainty`.

- [ ] **Step 4: Run the focused vocabulary tests to GREEN**

Expected: all Task 1 tests PASS with no warning treated as authority.

- [ ] **Step 5: Run static checks and commit the Task 1 paths**

Run Ruff on the two exact paths and basedpyright on `engine/physics/properties.py`.
Stage only those paths, run `git diff --cached --check`, inspect the staged path
list, and commit:

```text
feat(c1): add thermophysical property contracts
```

### Task 2: Add closed vapor-pressure representations

**Files:**

- Modify: `tests/test_c1_thermophysical_contracts.py`
- Create: `engine/physics/vapor_pressure.py`

- [ ] **Step 1: Add RED tests for representation shape and range policy**

Import the Task 2 names from `engine.physics.vapor_pressure` and add tests that
lock these exact enum values:

```python
REQUIRED_VAPOR_EQUATION_TYPES = {
    "MEASURED_TABLE",
    "ANTOINE",
    "WAGNER",
    "DIPPR_STYLE",
    "CLAUSIUS_CLAPEYRON",
    "OTHER_DECLARED_FORM",
}


def test_vapor_pressure_equation_vocabulary_is_exact():
    assert {item.value for item in VaporPressureEquationType} == REQUIRED_VAPOR_EQUATION_TYPES
```

Use one complete `MEASURED_TABLE` fixture and one complete `ANTOINE` fixture.
Assert that every representation carries model id/version, identity,
convention, declared pressure/temperature units, inclusive range, phase, purity,
source, optional fit evidence, uncertainty, extrapolation policy, and stable
content hash. Assert that measured tables require points and forbid coefficients;
all other equation types require uniquely named coefficients with finite values
and nonblank units. Assert positive ordered temperatures, positive measured
pressures, source completeness, and stable hash across mapping order.

- [ ] **Step 2: Run only the vapor tests to prove RED**

Expected: FAIL because `engine.physics.vapor_pressure` does not exist.

- [ ] **Step 3: Implement representation-only contracts**

Implement this exact API manifest in `engine/physics/vapor_pressure.py`:

```text
VaporPressureEquationType values:
  MEASURED_TABLE, ANTOINE, WAGNER, DIPPR_STYLE, CLAUSIUS_CLAPEYRON,
  OTHER_DECLARED_FORM

ExtrapolationPolicy values: FORBID, ADVISORY_ONLY_WITH_WARNING

VaporPressureCoefficient fields: name: str; value: float; unit: str
VaporPressurePoint fields:
  temperature_k: float; pressure: float; pressure_unit: str
TemperatureRange fields: lower_k: float; upper_k: float
TemperatureRange.contains(float) -> bool

VaporPressureRepresentation fields:
  model_id: str; model_version: str; identity: PropertyIdentity;
  equation_type: VaporPressureEquationType; equation_convention: str;
  coefficients: tuple[VaporPressureCoefficient, ...]; pressure_unit: str;
  temperature_unit: str; valid_temperature_range: TemperatureRange;
  phase_assumption: str; purity_assumption: CanonicalScope;
  source: SourceReference; measured_points: tuple[VaporPressurePoint, ...];
  fit_evidence: CanonicalScope | None; uncertainty: UncertaintyDescriptor;
  extrapolation_policy: ExtrapolationPolicy; content_sha256: computed str
VaporPressureRepresentation.from_mapping(Mapping[str, Any])
  -> VaporPressureRepresentation
VaporPressureRepresentation.to_mapping() -> dict[str, Any]
```

The closed payload schema is `c1-vapor-pressure-representation-v1`. Require
`temperature_unit == "K"` because C1 has no conversion engine. Preserve any fit
data/residual declaration as a canonical mapping, but do not manufacture fit
statistics and do not evaluate any equation. Hash the full canonical payload.

- [ ] **Step 4: Run Task 1 and Task 2 tests to GREEN**

Expected: all C1 tests currently present PASS.

- [ ] **Step 5: Run static checks and commit the Task 2 paths**

Commit exact staged paths with:

```text
feat(c1): add vapor pressure representations
```

### Task 3: Expose complete existing B2 observation evidence

**Files:**

- Modify: `backend/tests/unit/test_b2_property_service.py`
- Modify: `backend/app/services/lab_properties.py`

- [ ] **Step 1: Extend the existing reconstruction test to RED**

In
`test_assertion_reconstruction_uses_explicit_id_and_preserves_lineage`, locate
the selected candidate and assert these existing ORM values are present:

```python
selected = next(
    candidate
    for candidate in reconstructed["candidates"]
    if candidate["observation"]["id"] == first.id
)
observation = selected["observation"]
assert observation["pressure_pa"] == 101325.0
assert observation["relative_humidity_percent"] == 50.0
assert observation["phase"] == "gas"
assert observation["purity_fraction"] == 0.99
assert observation["source_version_id"] == first.source_version_id
assert observation["extraction_record_id"] == first.extraction_record_id
assert observation["source_locator"] == {"page": 12, "table": "2", "row": "Linalool"}
assert observation["replicate_count"] == 3
assert observation["statistic"] == "mean"
assert observation["standard_uncertainty"] == 0.5
assert observation["uncertainty_interval"] == {"coverage_factor": 2}
assert observation["evidence_class"] == "MEASURED"
assert observation["review_state"] == "REVIEWED"
assert observation["applicability_domain"] == {"matrix": "air"}
assert observation["provenance_activity"] == {"actor": "reviewer-1"}
```

- [ ] **Step 2: Run the one backend test to prove RED**

Run from the repository root with `PYTHONPATH` containing both the root and
`backend`. Expected: `KeyError: 'pressure_pa'` (or the first newly required
field), not a database/migration failure.

- [ ] **Step 3: Add only the existing fields to reconstruction**

Extend the candidate observation dictionary in
`reconstruct_selected_assertion` with exactly:

```python
"pressure_pa": observation.pressure_pa,
"relative_humidity_percent": observation.relative_humidity_percent,
"phase": observation.phase,
"purity_fraction": observation.purity_fraction,
"source_version_id": observation.source_version_id,
"extraction_record_id": observation.extraction_record_id,
"source_locator": observation.source_locator_json,
"replicate_count": observation.replicate_count,
"statistic": observation.statistic,
"standard_uncertainty": observation.standard_uncertainty,
"uncertainty_interval": observation.uncertainty_interval_json,
"evidence_class": observation.evidence_class,
"review_state": observation.review_state,
"applicability_domain": observation.applicability_domain_json,
"provenance_activity": observation.provenance_activity_json,
```

Do not modify a model, repository, migration, database, reconstruction schema
name, or existing key meaning.

- [ ] **Step 4: Run the focused backend service suite to GREEN**

Run all of `backend/tests/unit/test_b2_property_service.py`. Expected: every B2
service test passes, including the additive reconstruction assertion.

- [ ] **Step 5: Run backend Ruff and commit exact paths**

Commit:

```text
feat(c1): expose selected property provenance
```

### Task 4: Add the versioned B2 adapter and fail-closed selector

**Files:**

- Modify: `tests/test_c1_thermophysical_contracts.py`
- Create: `engine/physics/selection.py`

- [ ] **Step 1: Add a complete B2 reconstruction fixture**

Import the Task 4 names from `engine.physics.selection`. The fixture must use
schema `lab-selected-assertion-reconstruction-v1`, one explicit assertion, and
two visible candidates. Its selected candidate includes all Task 3 observation
fields. Add helpers that vary only identity, property, conditions, selection
kind, authority, interpolation state, applicability, source, unit, and selected
model.

- [ ] **Step 2: Add RED tests for every selection branch**

Define and test these exact public enums and reasons:

```python
class SelectionKind(str, Enum):
    OBSERVATION = "OBSERVATION"
    MODEL = "MODEL"
    NONE = "NONE"

class InterpolationState(str, Enum):
    EXACT = "EXACT"
    INTERPOLATED = "INTERPOLATED"
    EXTRAPOLATED = "EXTRAPOLATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class AuthorityState(str, Enum):
    AUTHORIZED_FOR_SCOPED_PROPERTY = "AUTHORIZED_FOR_SCOPED_PROPERTY"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    WITHHELD_CONFLICT = "WITHHELD_CONFLICT"
    WITHHELD_UNKNOWN = "WITHHELD_UNKNOWN"

class MissingDataReason(str, Enum):
    ASSERTION_ABSENT = "ASSERTION_ABSENT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    PROPERTY_MISMATCH = "PROPERTY_MISMATCH"
    CONDITIONS_MISMATCH = "CONDITIONS_MISMATCH"
    NO_SELECTION = "NO_SELECTION"
    WITHHELD_AUTHORITY = "WITHHELD_AUTHORITY"
    ADVISORY_NOT_ALLOWED = "ADVISORY_NOT_ALLOWED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SELECTED_OBSERVATION_MISSING = "SELECTED_OBSERVATION_MISSING"
    SOURCE_MISSING = "SOURCE_MISSING"
    UNIT_MISSING = "UNIT_MISSING"
    UNSUPPORTED_MODEL_SCHEMA = "UNSUPPORTED_MODEL_SCHEMA"
    INTERPOLATION_UNCERTAINTY_MISSING = "INTERPOLATION_UNCERTAINTY_MISSING"
    EXTRAPOLATION_FORBIDDEN = "EXTRAPOLATION_FORBIDDEN"
    MODEL_OUTSIDE_VALID_RANGE = "MODEL_OUTSIDE_VALID_RANGE"
```

Required cases:

- exact authorized observation selects with value, unit, source, conditions,
  standard uncertainty, applicability, authority, request hash, and assertion
  hash;
- explicitly uncertain interpolation selects and reports `INTERPOLATED`;
- interpolation with `UNKNOWN` uncertainty withholds;
- release-grade extrapolation always withholds;
- exploratory extrapolation selects only a valid C1 model when request opt-in
  and model policy are both present, and the result is `ADVISORY` with a warning;
- advisory B2 authority withholds for release and requires exploratory advisory
  opt-in;
- conflict/unknown authority, `NONE`, `NOT_APPLICABLE`, explicit
  `applicable: false`, identity/property/condition mismatch, missing selected
  candidate, source, or unit each return the exact reason above;
- generic B2 `selected_model` returns `UNSUPPORTED_MODEL_SCHEMA` rather than
  raising or calling a legacy model;
- model temperature outside its valid range is handled as extrapolation even if
  B2 mislabeled it `EXACT`;
- unknown reconstruction schema, unknown top-level fields, and unknown assertion
  fields raise `ThermophysicalContractError` because they are programmer/schema
  defects;
- absence of scientific evidence returns `WITHHELD` and does not raise.

- [ ] **Step 3: Run the selector tests to prove RED**

Expected: collection or import FAIL because `engine.physics.selection` is
missing.

- [ ] **Step 4: Implement the pure adapter and selector**

Implement this exact API manifest:

```text
SelectionKind values: OBSERVATION, MODEL, NONE
InterpolationState values: EXACT, INTERPOLATED, EXTRAPOLATED, NOT_APPLICABLE
AuthorityState values:
  AUTHORIZED_FOR_SCOPED_PROPERTY, ADVISORY_ONLY, WITHHELD_CONFLICT,
  WITHHELD_UNKNOWN

SelectedPropertyAssertion fields:
  assertion_id; requested_identity; property_type; requested_conditions;
  selection_kind; selected_observation_id; observation_identity;
  observation_conditions; observation_property; datum; source; model;
  adaptation_missing_reason; interpolation_state; uncertainty;
  applicability; authority_state; permitted_claim_wording;
  conflict_visible; content_sha256

PropertyRequest fields:
  identity; property_type; conditions; claim_grade; allow_advisory=False;
  allow_extrapolation=False; content_sha256=computed

PropertySelectionResult fields:
  status; datum; model; canonical_unit; source; conditions; uncertainty;
  interpolation_state; applicability; authority_state; missing_reason;
  warnings; request_sha256; assertion_sha256

selected_assertion_from_b2_reconstruction(Mapping[str, Any])
  -> SelectedPropertyAssertion | None

PropertySelectionService.select(
  PropertyRequest, SelectedPropertyAssertion | None
) -> PropertySelectionResult
```

The adapter must allow exactly the known v1 top-level/assertion keys, select the
candidate by explicit `selected_observation_id`, preserve all candidates and
conflict visibility, and convert only the selected candidate into a datum/source.
It may ignore unknown nested provenance or source-locator keys because those are
canonical payload boundaries. For observations, map explicit B2
`standard_uncertainty` to a standard descriptor in the canonical unit; otherwise
use `UNKNOWN`. For interpolated evidence, accept only a closed
`c1-uncertainty-v1` propagated uncertainty.

For models, parse only `c1-vapor-pressure-representation-v1` and only when the
requested property is `vapor_pressure`. Catch model-contract errors and preserve
`UNSUPPORTED_MODEL_SCHEMA` as expected missing evidence. Do not import
`engine.uncertainty`, `engine.property_estimator`, backend modules, SQLAlchemy, or
any runtime scalar registry.

The selector must compare the request to the assertion's complete requested
identity/property/condition scopes before considering evidence. It then verifies
the selected observation/model identity and applicability. Every selected or
advisory result carries exactly one datum or one model, a nonblank unit, a source,
conditions, uncertainty, interpolation state, applicability, authority, and both
hashes. Every withheld result carries no datum/model and one closed missing-data
reason.

- [ ] **Step 5: Run all C1 tests to GREEN and mutation-check critical branches**

Temporarily invert or remove one extrapolation guard and prove the corresponding
test fails, then restore the implementation with `apply_patch` and rerun GREEN.
Do the same for the source-completeness guard. Do not commit a mutation.

- [ ] **Step 6: Run static checks and commit exact Task 4 paths**

Commit:

```text
feat(c1): add fail-closed property selection
```

### Task 5: Publish the package boundary and run compatibility gates

**Files:**

- Create: `engine/physics/__init__.py`
- Modify: `tests/test_c1_thermophysical_contracts.py`

- [ ] **Step 1: Add RED public-import and dependency-boundary tests**

Assert every intended C1 type imports from `engine.physics`. Parse the three C1
source files with `ast` and assert they do not import `backend`, `sqlalchemy`,
`engine.uncertainty`, or any `property_estimator` module. Assert no public function
contains equation-evaluation names such as `evaluate`, `predict_pressure`, or
`estimate_vapor_pressure`.

- [ ] **Step 2: Run the public-boundary tests to prove RED**

Expected: FAIL because `engine/physics/__init__.py` is missing or does not export
the names.

- [ ] **Step 3: Add explicit public exports only**

Import and list every intended name in `__all__`; do not use wildcard imports.
The module docstring must state that C1 represents/selects evidence but does not
evaluate equations or authorize scientific release.

- [ ] **Step 4: Run the focused and compatibility matrix**

Run:

```text
tests/test_c1_thermophysical_contracts.py
tests/test_c0_physical_model_inventory.py
backend/tests/unit/test_b2_property_service.py
backend/tests/unit/test_b2_property_schema.py
backend/tests/unit/test_b1_source_service.py
```

Also run Ruff on every changed Python path and basedpyright on `engine/physics`.
If scoped mypy is available for the backend service, run it without expanding to
known unrelated import-graph failures.

- [ ] **Step 5: Prove the C1 scope stayed closed**

Check the diff from the C1 implementation parent. The changed-path set must
contain no `backend/alembic/versions`, database file, production caller,
headspace/temporal/optimizer module, or C2 path. Use `rg` to prove no legacy
estimator import exists in `engine/physics`. Run `git diff --check`.

- [ ] **Step 6: Commit the public boundary if it is a separate change**

Commit:

```text
feat(c1): publish thermophysical contract boundary
```

### Task 6: Seal the C1 executable gate

**Files:**

- Create: `docs/verification/c1/thermophysical_contracts_gate.json`
- Create: `docs/verification/c1/thermophysical_contracts_gate.md`
- Create mechanically: `docs/verification/c1/logs/*`

- [ ] **Step 1: Capture fresh non-PTY gate logs**

Run the Task 5 matrix with an external writable pytest temp directory, explicit
timeout, and separate stdout/stderr. Capture exact interpreter/tool versions,
commands, exit codes, test counts, durations, and SHA-256 of every log. Scan logs
for ANSI bytes and record only the count of credential-shaped matches; never
display matched values.

- [ ] **Step 2: Verify protected state and recovery evidence**

Hash `perfume_chem.db` and `data/perfumery_kb.db` before and after C1 verification,
run immutable/read-only SQLite quick checks when the files are valid SQLite, and
prove no database changed. Re-hash the C1 prewrite archive and verify its tar
member count/path-preserving extraction evidence. Record no secret-bearing paths
or environment values.

- [ ] **Step 3: Write the machine and human gate reports**

The JSON schema is `build-c1-thermophysical-contracts-gate-v1`. It must include:

- branch, starting parent, implementation commits, and verification head;
- exact property/equation/uncertainty counts;
- exact test/static commands and results;
- changed-path allowlist and explicit zero migration/database/C2 changes;
- extrapolation, advisory, identity, conditions, provenance, uncertainty, and
  withholding decisions;
- archive and protected-state hashes;
- known limitations, including no equation evaluation, no real-property data
  promotion, and no scientific-release authority;
- DeepLuna job/route/fallback evidence; and
- a closed exit-gate boolean map.

The Markdown must agree with the JSON and must not claim Build C or scientific
release is complete.

- [ ] **Step 4: Run a fresh exact-project DeepLuna gate and final bounded audit**

Run `deepseek_check` for `D:\chatbots\perfume-chem`. Only if `READY`, submit one
read-only `FLASH`, `NO_LUNA`, one-call audit over the final changed paths and gate
logs. Require file-line citations for every finding. Sol must reproduce every
finding locally, reject scope/architecture recommendations, and record zero
unsupported findings as accepted.

- [ ] **Step 5: Stage, inspect, and commit only C1 gate evidence**

Run focused tests against the staged tree, `git diff --cached --check`, inspect
every staged path, and commit:

```text
test(c1): seal thermophysical contract gate
```

- [ ] **Step 6: Run post-commit verification and decide the phase gate**

Re-run the focused C1 test, B2 reconstruction test, Ruff, dependency-boundary
scan, staged/index cleanliness check, commit path audit, protected-state hash
comparison, and gate JSON/Markdown reconciliation. C1 is `PASS` only if every
result is current and green. If any result is unknown, timed out, unsupported, or
conflicts with the canonical tree, C1 is `BLOCKED/UNKNOWN` and C2 remains closed.

## Inline execution decision

The user delegated implementation decisions to Sol and prohibited Codex
subagents and permission pauses. Execute this plan inline with
`superpowers:executing-plans`; do not ask for an execution-mode choice.
