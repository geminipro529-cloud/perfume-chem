# Build C2 Matrix and Application-Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Do not use
> subagent-driven development: project policy forbids Codex subagents. DeepLuna
> Fast may perform only bounded read-only audits; Sol owns all design choices,
> implementation, scientific interpretation, provenance judgment, and final
> acceptance.

**Goal:** Add immutable, versioned matrix and application-environment contracts
whose complete snapshots and hashes are mandatory in every C2 model request.

**Architecture:** Add one pure contract module beside the C1 property contracts,
reuse the existing canonical JSON/SHA-256 and closed uncertainty representation,
and export the public types from `engine.physics`. Do not adapt a ledger, evaluate
an equation, migrate persistence, or move a production caller.

**Tech Stack:** Python 3.11, frozen dataclasses with slots, string enums, the
existing `engine.calibration.hashing.stable_json_hash`, C1
`UncertaintyDescriptor`, pytest, Ruff, basedpyright, and mypy where supported.

---

## Execution boundary and recovery evidence

- Phase: Build C, C2 only. C3 remains closed until the C2 commit and post-commit
  gate pass.
- C2 phase parent: `e6c6d5bed3a41362e21bf07752a98fd952781a59`.
- Accepted design checkpoint:
  `1fe41a4` (`docs(c2): accept matrix environment design`).
- Implementation parent: the commit that seals this plan; record its full SHA in
  the C2 gate after the plan commit succeeds.
- Preserved prewrite archive:
  `D:\.backups\perfume-chem\build-c2-prewrite-20260802T190634+0700.tar`.
- Archive length: `118417920` bytes.
- Archive SHA-256:
  `35325c26d526619623ce1c2f05c72484ad8377ed534f488b4191a2e7e649d023`.
- Archive verification: 444 manifest files and 429 Git-visible dirty/untracked
  paths matched length and SHA-256; zero unsafe members, duplicate members, or
  content mismatches. The manifest records 1203 excluded DeepLuna runtime paths.
- Supported interpreter:
  `D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe`.
- All gate-bearing commands run without a PTY, with `NO_COLOR=1`, `TERM=dumb`,
  explicit timeouts, and separate stdout/stderr.
- Never inspect or print environment values. Never modify a database, migration,
  generated scientific artifact, current physical caller, `MixtureState`, or
  `SolventLedger` in C2.

## File map

- Create `engine/physics/matrix_environment.py`: all C2 closed vocabulary,
  immutable records, validation, canonical serialization, parsing, and hashes.
- Modify `engine/physics/__init__.py`: explicit C2 public exports and package
  docstring update; preserve every C1 export.
- Create `tests/test_c2_matrix_environment.py`: pure RED/GREEN contract,
  tamper-detection, dependency-boundary, and C2 exit tests.
- Create `docs/verification/c2/matrix_environment_gate.json`: machine-readable
  C2 evidence and exit decision.
- Create `docs/verification/c2/matrix_environment_gate.md`: human-readable C2
  evidence and limitations.
- Create mechanically `docs/verification/c2/logs/*` and
  `docs/verification/c2/postcommit/*`: non-PTY stdout/stderr, hashes, protected
  state, DeepLuna receipt, and committed-tree verification.

### Task 1: Add quantity, component, and matrix contracts

**Files:**

- Create: `tests/test_c2_matrix_environment.py`
- Create: `engine/physics/matrix_environment.py`

- [ ] **Step 1: Write failing closed-vocabulary and quantity tests**

Start the test file with these exact sets and imports from
`engine.physics.matrix_environment`:

```python
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from engine.physics.matrix_environment import (
    CompositionCompleteness,
    DeclaredQuantity,
    MatrixComponent,
    MatrixComponentRole,
    MatrixComposition,
    MatrixEnvironmentContractError,
    MatrixMissingField,
    MatrixQuantityBasis,
    MatrixStage,
)
from engine.physics.properties import UncertaintyDescriptor


REQUIRED_MATRIX_STAGES = {
    "STOCK_SOLUTION",
    "CONCENTRATE",
    "FINISHED_PERFUME",
    "APPLICATION_FILM",
    "SAMPLED_HEADSPACE",
}
REQUIRED_COMPONENT_ROLES = {
    "ETHANOL",
    "WATER",
    "DPG",
    "DEP",
    "TEC",
    "IPM",
    "OTHER_CARRIER",
    "ACTIVE_FRAGRANCE",
    "DISSOLVED_SOLID",
    "OTHER_PRODUCT_PHASE",
}
REQUIRED_QUANTITY_BASES = {
    "MASS_FRACTION",
    "VOLUME_FRACTION",
    "MOLE_FRACTION",
    "MASS",
    "VOLUME",
    "AMOUNT",
}


def unknown(reason: str = "not quantified") -> UncertaintyDescriptor:
    return UncertaintyDescriptor.unknown(reason)


def q(value: float, unit: str) -> DeclaredQuantity:
    return DeclaredQuantity(value=value, unit=unit)


def test_c2_matrix_vocabulary_is_closed() -> None:
    assert {item.value for item in MatrixStage} == REQUIRED_MATRIX_STAGES
    assert {item.value for item in MatrixComponentRole} == REQUIRED_COMPONENT_ROLES
    assert {item.value for item in MatrixQuantityBasis} == REQUIRED_QUANTITY_BASES


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_declared_quantity_rejects_non_finite_or_boolean(value: object) -> None:
    with pytest.raises(MatrixEnvironmentContractError):
        DeclaredQuantity(value=value, unit="g")  # type: ignore[arg-type]


def test_declared_quantity_requires_an_explicit_unit_and_is_frozen() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="unit"):
        q(1.0, " ")
    quantity = q(1.0, "g")
    with pytest.raises(FrozenInstanceError):
        quantity.value = 2.0  # type: ignore[misc]
```

- [ ] **Step 2: Add failing component and matrix behavior tests**

Use these complete fixtures:

```python
def component(
    component_id: str,
    name: str,
    role: MatrixComponentRole,
    value: float,
    basis: MatrixQuantityBasis = MatrixQuantityBasis.MASS_FRACTION,
    unit: str = "1",
) -> MatrixComponent:
    return MatrixComponent(
        component_id=component_id,
        name=name,
        role=role,
        basis=basis,
        quantity=q(value, unit),
        source_reference=f"formula-declaration:{component_id}:v1",
        uncertainty=unknown(),
    )


def exact_matrix(
    *,
    stage: MatrixStage = MatrixStage.FINISHED_PERFUME,
    ethanol_fraction: float = 0.8,
    gas_comparison: bool = False,
) -> MatrixComposition:
    return MatrixComposition(
        matrix_id="matrix:formula-17:finished",
        matrix_version="1",
        stage=stage,
        components=(
            component(
                "cas:64-17-5",
                "ethanol",
                MatrixComponentRole.ETHANOL,
                ethanol_fraction,
            ),
            component(
                "formula:active-fragrance",
                "active fragrance",
                MatrixComponentRole.ACTIVE_FRAGRANCE,
                1.0 - ethanol_fraction,
            ),
        ),
        temperature=q(298.15, "K"),
        pressure=q(101325.0, "Pa"),
        relative_humidity=q(50.0, "%") if gas_comparison else None,
        gas_comparison=gas_comparison,
        total_mass=q(25.0, "g"),
        total_volume=q(30.0, "mL"),
        uncertainty=unknown("matrix uncertainty not measured"),
        phase_assumptions=("single liquid phase",),
        completeness=CompositionCompleteness.EXACT,
        missing_fields=(),
    )
```

Add assertions that:

```python
def test_fraction_component_requires_unit_one_and_closed_range() -> None:
    with pytest.raises(MatrixEnvironmentContractError, match="unit 1"):
        component(
            "cas:64-17-5",
            "ethanol",
            MatrixComponentRole.ETHANOL,
            0.8,
            unit="%",
        )
    with pytest.raises(MatrixEnvironmentContractError, match="between 0 and 1"):
        component(
            "cas:64-17-5",
            "ethanol",
            MatrixComponentRole.ETHANOL,
            1.1,
        )


def test_exact_fraction_matrix_requires_fraction_closure() -> None:
    matrix = exact_matrix()
    assert sum(item.quantity.value for item in matrix.components) == 1.0
    with pytest.raises(MatrixEnvironmentContractError, match="sum to 1"):
        replace(
            matrix,
            components=(
                component("ethanol", "ethanol", MatrixComponentRole.ETHANOL, 0.7),
                component(
                    "active",
                    "active fragrance",
                    MatrixComponentRole.ACTIVE_FRAGRANCE,
                    0.2,
                ),
            ),
        )


def test_component_order_does_not_change_matrix_identity() -> None:
    matrix = exact_matrix()
    reversed_matrix = replace(matrix, components=tuple(reversed(matrix.components)))
    assert reversed_matrix.components == matrix.components
    assert reversed_matrix.content_sha256 == matrix.content_sha256


def test_matrix_stage_and_composition_change_identity() -> None:
    finished = exact_matrix()
    film = replace(finished, stage=MatrixStage.APPLICATION_FILM)
    wetter = exact_matrix(ethanol_fraction=0.75)
    assert len({finished.content_sha256, film.content_sha256, wetter.content_sha256}) == 3
```

Also test blank component identity/name/source, negative absolute quantity,
duplicate component IDs under case folding, empty components, blank matrix
ID/version/phase assumption, non-positive pressure, negative totals, and a
non-`UncertaintyDescriptor` value.

Test completeness with these exact branches:

- `EXACT` rejects any `missing_fields`, absent temperature, pressure, total mass,
  or total volume;
- `PARTIAL` and `UNRESOLVED` reject an empty `missing_fields` tuple;
- an absent optional matrix field is accepted only when its matching closed
  `MatrixMissingField` is declared;
- `gas_comparison=True` rejects absent humidity unless a non-exact matrix declares
  `MatrixMissingField.RELATIVE_HUMIDITY`;
- `gas_comparison=False` permits absent humidity without calling it missing;
- `MatrixMissingField.COMPONENT_COMPOSITION` prevents fraction-closure authority
  for a partial matrix.

- [ ] **Step 3: Run the focused test to prove RED**

Run:

```powershell
$env:NO_COLOR='1'; $env:TERM='dumb'
D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B -m pytest -p no:cacheprovider --color=no tests/test_c2_matrix_environment.py -q
```

Expected: FAIL during collection because
`engine.physics.matrix_environment` does not exist. A timeout or unrelated import
failure is not the expected RED result.

- [ ] **Step 4: Implement the minimal quantity, component, and matrix API**

Create `engine/physics/matrix_environment.py` with this exact public vocabulary:

```text
MatrixEnvironmentContractError extends ValueError

MatrixStage values:
  STOCK_SOLUTION, CONCENTRATE, FINISHED_PERFUME, APPLICATION_FILM,
  SAMPLED_HEADSPACE

MatrixComponentRole values:
  ETHANOL, WATER, DPG, DEP, TEC, IPM, OTHER_CARRIER,
  ACTIVE_FRAGRANCE, DISSOLVED_SOLID, OTHER_PRODUCT_PHASE

MatrixQuantityBasis values:
  MASS_FRACTION, VOLUME_FRACTION, MOLE_FRACTION, MASS, VOLUME, AMOUNT

CompositionCompleteness values: EXACT, PARTIAL, UNRESOLVED

MatrixMissingField values:
  COMPONENT_COMPOSITION, TEMPERATURE, PRESSURE, RELATIVE_HUMIDITY,
  TOTAL_MASS, TOTAL_VOLUME

DeclaredQuantity fields: value: float; unit: str
DeclaredQuantity.from_mapping(Mapping[str, Any]) -> DeclaredQuantity
DeclaredQuantity.to_mapping() -> dict[str, object]

MatrixComponent fields:
  component_id: str; name: str; role: MatrixComponentRole;
  basis: MatrixQuantityBasis; quantity: DeclaredQuantity;
  source_reference: str; uncertainty: UncertaintyDescriptor;
  content_sha256: computed str
MatrixComponent.from_mapping(Mapping[str, Any]) -> MatrixComponent
MatrixComponent.to_mapping() -> dict[str, object]

MatrixComposition fields:
  matrix_id: str; matrix_version: str; stage: MatrixStage;
  components: tuple[MatrixComponent, ...];
  temperature: DeclaredQuantity | None;
  pressure: DeclaredQuantity | None;
  relative_humidity: DeclaredQuantity | None; gas_comparison: bool;
  total_mass: DeclaredQuantity | None; total_volume: DeclaredQuantity | None;
  uncertainty: UncertaintyDescriptor; phase_assumptions: tuple[str, ...];
  completeness: CompositionCompleteness;
  missing_fields: tuple[MatrixMissingField, ...];
  content_sha256: computed str
MatrixComposition.from_mapping(Mapping[str, Any]) -> MatrixComposition
MatrixComposition.to_mapping() -> dict[str, object]
```

Use schema tags `c2-declared-quantity-v1`, `c2-matrix-component-v1`, and
`c2-matrix-composition-v1`. Every parser requires the exact key set and verifies
the supplied `content_sha256` for component and matrix payloads. Serialization
includes that hash but the hash input excludes its own hash field.

Normalize nonblank strings by stripping outer whitespace. Require enum instances
in direct constructors; mapping parsers convert closed string values and translate
invalid values to `MatrixEnvironmentContractError`. Convert numbers to finite
floats while rejecting booleans. Sort components case-insensitively by
`component_id`, reject duplicate IDs, and sort unique missing fields and phase
assumptions before hashing.

For exact matrices made entirely from one fraction basis, require the fractions
to sum to 1 with `math.isclose(..., rel_tol=0.0, abs_tol=1e-12)`; never renormalize
them. Validate humidity only as an explicitly declared quantity in C2; do not
convert `%` and fraction units. Serialize uncertainty through
`uncertainty.payload.to_mapping()` and parse it with
`UncertaintyDescriptor.from_mapping()`.

- [ ] **Step 5: Run Task 1 tests to GREEN, mutation-check, and commit**

Run the focused file. Then temporarily remove the exact-fraction closure guard and
prove `test_exact_fraction_matrix_requires_fraction_closure` fails; restore the
guard with `apply_patch` and rerun GREEN. Stage only the two Task 1 paths, run
`git diff --cached --check`, inspect the staged path list, and commit:

```text
feat(c2): add versioned matrix contracts
```

### Task 2: Add application-environment contracts

**Files:**

- Modify: `tests/test_c2_matrix_environment.py`
- Modify: `engine/physics/matrix_environment.py`

- [ ] **Step 1: Add RED environment vocabulary and classification tests**

Extend imports with `ApplicationEnvironment`, `ApplicationEnvironmentKind`, and
`EnvironmentField`. Lock these exact values:

```python
REQUIRED_ENVIRONMENT_KINDS = {
    "SEALED_EQUILIBRIUM_VIAL",
    "OPEN_LIQUID_SURFACE",
    "BLOTTER",
    "SKIN",
    "SKIN_SURROGATE",
    "FABRIC",
    "CREAM_OR_EMULSION",
    "SOAP_OR_CLEANSER",
    "OTHER_PRODUCT_MATRIX",
}
REQUIRED_ENVIRONMENT_FIELDS = {
    "dose",
    "area",
    "film_thickness",
    "geometry",
    "substrate",
    "temperature",
    "relative_humidity",
    "airflow",
    "equilibration_or_drying_time",
    "sampling_time",
    "sampling_method",
    "vessel_volume",
    "headspace_volume",
}


def test_c2_environment_vocabulary_is_closed() -> None:
    assert {item.value for item in ApplicationEnvironmentKind} == REQUIRED_ENVIRONMENT_KINDS
    assert {item.value for item in EnvironmentField} == REQUIRED_ENVIRONMENT_FIELDS
```

Use this complete blotter fixture:

```python
def blotter_environment() -> ApplicationEnvironment:
    return ApplicationEnvironment(
        environment_id="environment:blotter:standard-1",
        environment_version="1",
        kind=ApplicationEnvironmentKind.BLOTTER,
        dose=q(0.05, "mL"),
        area=q(5.0, "cm2"),
        film_thickness=None,
        geometry="1 cm application line on paper blotter",
        substrate="cellulose fragrance blotter lot B-17",
        temperature=q(298.15, "K"),
        relative_humidity=q(50.0, "%"),
        airflow=q(0.1, "m/s"),
        equilibration_or_drying_time=q(60.0, "s"),
        sampling_time=q(300.0, "s"),
        sampling_method="dynamic headspace at blotter centerline",
        vessel_volume=None,
        headspace_volume=None,
        uncertainty=unknown("environment uncertainty not measured"),
        missing_fields=(),
        not_applicable_fields=(
            EnvironmentField.FILM_THICKNESS,
            EnvironmentField.VESSEL_VOLUME,
            EnvironmentField.HEADSPACE_VOLUME,
        ),
    )
```

Add tests proving:

- every absent field must be in exactly one of `missing_fields` or
  `not_applicable_fields`;
- a present field cannot be classified absent;
- the two classification sets cannot overlap and reject unknown strings;
- quantities that represent dose, area, thickness, humidity, airflow, time, or
  volume reject negative values;
- present geometry, substrate, and sampling method reject blank strings;
- blank environment ID/version and a non-uncertainty descriptor fail;
- changing kind, substrate, dose, humidity, airflow, sampling time, sampling
  method, vessel volume, or headspace volume changes `content_sha256`;
- canonical classification order does not change the hash;
- `SEALED_EQUILIBRIUM_VIAL` requires non-null vessel volume, headspace volume,
  sampling time, and sampling method even if a caller marks them missing or not
  applicable.

Build a valid sealed-vial fixture with all four apparatus/sampling fields and
classify only genuinely absent surface fields as not applicable.

- [ ] **Step 2: Run the environment subset to prove RED**

Run:

```powershell
D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe -B -m pytest -p no:cacheprovider --color=no tests/test_c2_matrix_environment.py -q -k environment
```

Expected: collection/import FAIL because the three environment types are not yet
defined.

- [ ] **Step 3: Implement the minimal environment API**

Add this exact vocabulary:

```text
ApplicationEnvironmentKind values:
  SEALED_EQUILIBRIUM_VIAL, OPEN_LIQUID_SURFACE, BLOTTER, SKIN,
  SKIN_SURROGATE, FABRIC, CREAM_OR_EMULSION, SOAP_OR_CLEANSER,
  OTHER_PRODUCT_MATRIX

EnvironmentField values:
  dose, area, film_thickness, geometry, substrate, temperature,
  relative_humidity, airflow, equilibration_or_drying_time, sampling_time,
  sampling_method, vessel_volume, headspace_volume

ApplicationEnvironment fields:
  environment_id: str; environment_version: str;
  kind: ApplicationEnvironmentKind;
  dose: DeclaredQuantity | None; area: DeclaredQuantity | None;
  film_thickness: DeclaredQuantity | None; geometry: str | None;
  substrate: str | None; temperature: DeclaredQuantity | None;
  relative_humidity: DeclaredQuantity | None;
  airflow: DeclaredQuantity | None;
  equilibration_or_drying_time: DeclaredQuantity | None;
  sampling_time: DeclaredQuantity | None; sampling_method: str | None;
  vessel_volume: DeclaredQuantity | None;
  headspace_volume: DeclaredQuantity | None;
  uncertainty: UncertaintyDescriptor;
  missing_fields: tuple[EnvironmentField, ...];
  not_applicable_fields: tuple[EnvironmentField, ...];
  content_sha256: computed str
ApplicationEnvironment.from_mapping(Mapping[str, Any])
  -> ApplicationEnvironment
ApplicationEnvironment.to_mapping() -> dict[str, object]
```

Use schema `c2-application-environment-v1`. Direct construction and parsing must
apply the same validation. Create one field-to-value map in `__post_init__`; its
keys must equal the closed `EnvironmentField` set. Compute absent fields from
`None`, then require the disjoint classification union to equal that exact absent
set. Sort both tuples by enum value. The sealed-vial required set is exactly
`VESSEL_VOLUME`, `HEADSPACE_VOLUME`, `SAMPLING_TIME`, and `SAMPLING_METHOD`.

The parser requires every schema field, including explicit `null` values and both
classification arrays, and verifies `content_sha256`. It must reject rather than
ignore unknown top-level keys.

- [ ] **Step 4: Run all C2 tests to GREEN, mutation-check, and commit**

Temporarily allow an unclassified absent field and prove the classification test
fails; restore with `apply_patch` and rerun GREEN. Run Ruff and basedpyright on the
two exact Task 2 paths, stage them, inspect the staged diff, and commit:

```text
feat(c2): add application environment contracts
```

### Task 3: Add mandatory matrix-aware requests and public exports

**Files:**

- Modify: `tests/test_c2_matrix_environment.py`
- Modify: `engine/physics/matrix_environment.py`
- Modify: `engine/physics/__init__.py`

- [ ] **Step 1: Add RED request identity, round-trip, and public-boundary tests**

Extend imports with `MatrixAwareModelRequest` and add:

```python
FORMULA_SHA256 = "a" * 64


def model_request(
    *,
    matrix: MatrixComposition | None = None,
    environment: ApplicationEnvironment | None = None,
) -> MatrixAwareModelRequest:
    return MatrixAwareModelRequest(
        purpose="c2 distinguishability contract test",
        formula_id="formula:17",
        formula_sha256=FORMULA_SHA256,
        matrix=matrix or exact_matrix(),
        environment=environment or blotter_environment(),
    )


def test_same_formula_in_different_matrix_or_environment_changes_request() -> None:
    baseline = model_request()
    changed_matrix = model_request(matrix=exact_matrix(ethanol_fraction=0.75))
    changed_environment = model_request(
        environment=replace(blotter_environment(), substrate="cotton fabric lot C-2")
    )
    assert len(
        {
            baseline.content_sha256,
            changed_matrix.content_sha256,
            changed_environment.content_sha256,
        }
    ) == 3


def test_request_serialization_embeds_both_snapshots_and_hashes() -> None:
    request = model_request()
    payload = request.to_mapping()
    assert payload["matrix_sha256"] == request.matrix.content_sha256
    assert payload["environment_sha256"] == request.environment.content_sha256
    assert payload["matrix"]["content_sha256"] == request.matrix.content_sha256
    assert payload["environment"]["content_sha256"] == request.environment.content_sha256
    assert MatrixAwareModelRequest.from_mapping(payload) == request
```

Also prove blank purpose/formula ID, uppercase/short/non-hex formula hashes, wrong
matrix/environment types, mismatched repeated context hashes, a tampered nested
component/environment, wrong schema, missing key, and unknown top-level key fail
closed. Assert that request hashes are stable across a full mapping round trip.

Import every C2 public name from `engine.physics` in one test. Parse
`matrix_environment.py` with `ast` and assert imports do not begin with `backend`,
`sqlalchemy`, `engine.mixture`, or `engine.solvent_matrix`, and do not contain
legacy estimator/model imports. Assert the module exposes no equation evaluation
function.

- [ ] **Step 2: Run only request/public tests to prove RED**

Expected: FAIL because `MatrixAwareModelRequest` and aggregate C2 exports are not
present.

- [ ] **Step 3: Implement the request and explicit exports**

Add this exact API:

```text
MatrixAwareModelRequest fields:
  purpose: str; formula_id: str; formula_sha256: str;
  matrix: MatrixComposition; environment: ApplicationEnvironment;
  content_sha256: computed str
MatrixAwareModelRequest.from_mapping(Mapping[str, Any])
  -> MatrixAwareModelRequest
MatrixAwareModelRequest.to_mapping() -> dict[str, object]
```

Use schema `c2-matrix-aware-model-request-v1`. Require a lowercase 64-character
hex formula hash with `re.fullmatch(r"[0-9a-f]{64}", value)`. The canonical
request hash input contains schema, purpose, formula ID/hash, full matrix mapping,
full environment mapping, and both repeated context hashes. The parser verifies
matrix, environment, and request hashes after parsing the nested exact schemas.

Update `engine.physics.__init__` with explicit imports and `__all__` entries for:

```text
ApplicationEnvironment
ApplicationEnvironmentKind
CompositionCompleteness
DeclaredQuantity
EnvironmentField
MatrixAwareModelRequest
MatrixComponent
MatrixComponentRole
MatrixComposition
MatrixEnvironmentContractError
MatrixMissingField
MatrixQuantityBasis
MatrixStage
```

Preserve every C1 export. Update only the package docstring to say the package
also represents versioned matrix/application context; keep the statements that it
does not evaluate equations or authorize scientific release.

- [ ] **Step 4: Run round-trip, dependency, and compatibility tests to GREEN**

Run:

```text
tests/test_c2_matrix_environment.py
tests/test_c1_thermophysical_contracts.py
tests/test_c0_physical_model_inventory.py
```

Run Ruff on the three changed Python paths, basedpyright on
`engine/physics/matrix_environment.py` and `tests/test_c2_matrix_environment.py`,
and scoped mypy on `engine/physics/matrix_environment.py`. Expected: all tests and
static checks pass with no import or equation evaluation added.

- [ ] **Step 5: Prove scope closure and commit Task 3**

Diff from the C2 implementation parent. The path set must contain only the design,
plan, C2 module/test, package export, and C2 evidence paths. Prove zero changes
under `backend/alembic/versions`, zero database files, zero generated artifacts,
and zero changes to `engine/mixture.py`, `engine/solvent_matrix.py`, workbench,
headspace, temporal, optimizer, or release modules. Commit exact Task 3 paths:

```text
feat(c2): require matrix context in model requests
```

### Task 4: Seal the C2 executable gate

**Files:**

- Create: `docs/verification/c2/matrix_environment_gate.json`
- Create: `docs/verification/c2/matrix_environment_gate.md`
- Create mechanically: `docs/verification/c2/logs/*`
- Create mechanically after the evidence commit:
  `docs/verification/c2/postcommit/*`

- [ ] **Step 1: Capture fresh non-PTY verification logs**

Use the supported interpreter, an external writable pytest temp directory,
`NO_COLOR=1`, `TERM=dumb`, `-p no:cacheprovider`, `--color=no`, and explicit
timeouts. Capture stdout and stderr separately for:

```text
focused C2 test file
focused C1 compatibility file
C0 physical-model inventory file
complete root pytest suite
Ruff check of all C2 Python paths
Ruff format --check of all C2 Python paths
basedpyright of the C2 module and tests
scoped mypy of the C2 module
```

Record exact commands, interpreter/tool versions, exit codes, test counts,
durations, log byte lengths, and log SHA-256 values. Empty stderr must be recorded
as empty, not discarded. A timeout is `BLOCKED/UNKNOWN`, never a pass.

- [ ] **Step 2: Verify recovery evidence, protected state, and scope**

Re-hash the C2 archive, reopen its embedded manifest, and independently verify all
file lengths/hashes and tar member safety. Hash `perfume_chem.db` and
`data/perfumery_kb.db` before and after verification; run immutable/read-only
SQLite `quick_check` where valid. Prove no migration, database, generated
artifact, current caller, ledger, or `MixtureState` path changed from the C2
implementation parent.

Scan logs as bytes/UTF-8 for ANSI and credential-shaped values. Store only match
counts and scanner outcomes; never display matched values or environment content.

- [ ] **Step 3: Write the machine and human gate reports**

The JSON schema is `build-c2-matrix-environment-gate-v1`. It must include:

- branch, C2 phase parent, accepted design, plan, implementation commits, and
  verification head;
- exact stage/role/basis/environment-kind/field counts;
- exact test/static commands and results;
- explicit same-formula matrix and environment distinguishability results;
- deterministic hash/round-trip/tamper-detection outcomes;
- changed-path allowlist and zero migration/database/caller/model changes;
- archive and protected-state evidence;
- DeepLuna job, Fast-only route, call count, fallback state, and cost delta;
- limitations: declared context only, no equation, no automatic adapter, no
  prediction/measurement value, no scientific-release authority; and
- a closed exit-gate boolean map plus `c3_open`.

The Markdown must agree with the JSON and must not claim Build C or scientific
release is complete.

- [ ] **Step 4: Run a fresh exact-project DeepLuna gate and bounded final audit**

Run `deepseek_check` for `D:\chatbots\perfume-chem`. Only if `READY`, submit one
read-only `FLASH`, `NO_LUNA`, one-call audit over the final C2 changed paths and
verification summaries. Require file-line evidence and ask only whether the
authoritative C2 requirements are met or contradicted. Sol must reproduce every
finding locally and remains final authority. Do not transmit dirty unrelated
files, logs containing sensitive matches, environment values, database contents,
or secrets.

- [ ] **Step 5: Commit only verified C2 gate evidence**

Run focused tests against the staged tree, `git diff --cached --check`, inspect
every staged path, and commit:

```text
test(c2): seal matrix environment gate
```

- [ ] **Step 6: Run post-commit verification and decide the phase gate**

Re-run focused C2/C1 tests, full root pytest, Ruff, basedpyright, mypy, dependency
scan, index-cleanliness check, commit path audit, protected-state comparison,
archive verification, and JSON/Markdown reconciliation against the committed
tree. Commit the post-commit evidence and final decision separately if the
evidence contract requires immutable committed paths.

C2 is `PASS` only if every current result is green and the same formula produces
distinct, traceable requests under both a matrix change and an environment
change. If any result is unknown, timed out, stale, unsupported, or conflicts
with the canonical tree, set C2 to `BLOCKED/UNKNOWN`; C3 remains closed.

## Inline execution decision

The user delegated implementation decisions to Sol and prohibited Codex
subagents and permission pauses. Execute this plan inline with
`superpowers:executing-plans`; do not ask for an execution-mode choice.
