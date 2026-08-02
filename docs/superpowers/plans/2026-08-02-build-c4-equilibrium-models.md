# Build C4 equilibrium-model implementation plan

Design: `docs/superpowers/specs/2026-08-02-build-c4-equilibrium-models-design.md`
Phase parent: `2fef4916ed3259f839599e8c9aeedf00261e5350`

## Preconditions

1. Confirm `docs/verification/c3/model_interface_gate.json` is `PASS` with `c4_open=true`.
2. Preserve the complete dirty/untracked baseline and planned C4 targets in a verified path-preserving archive.
3. Keep production callers, databases, migrations, generated artifacts, and legacy thermo code unchanged.
4. Use Python 3.11, non-PTY execution, no ANSI, separate stdout/stderr, and explicit timeouts.

The prewrite archive is `D:\.backups\perfume-chem\build-c4-prewrite-20260802T234123+0700.tar`, SHA-256 `0008fc9784ded2567ae3ba5cfd7f3123e2db4c88349e83c80fea5a9b3e353424`. Verification passed for 435 manifest files, including all 429 current dirty/untracked files, with zero unsafe names, duplicates, content mismatches, or current-work mismatches.

## Task 1: freeze executable tests (RED)

Create `tests/test_c4_equilibrium_models.py` before implementation. Cover:

- input-selection authority, hash, source, numeric-kind, and unit validation;
- deterministic input-set ordering and C3 reference binding;
- pure-component and binary analytic Raoult cases;
- mole fraction, mass fraction, absolute mass, and amount bases;
- exact closure and mass round-trip evidence;
- incomplete/mixed/volume-basis and unit mismatch abstention;
- stage, environment, phase, temperature, identity, and available-property checks;
- total bubble pressure above system pressure abstention;
- unavailable Henry, empirical, UNIFAC, and COSMO-RS releases;
- router integration, result authority, uncertainty warning, and hash round trip;
- proof that the new module does not import the legacy thermo headspace/activity modules.

Run only the new test file and capture the expected import/contract failure as RED evidence.

## Task 2: implement the pure C4 contracts

Create `engine/physics/equilibrium.py` with:

- `EquilibriumModelContractError`;
- `SelectedNumericPropertyInput`;
- `IdealRaoultInputSet` and its exact C3 input reference;
- deterministic supported-basis conversion and closure helpers;
- ideal release and applicability-domain factories;
- explicit unavailable-release factories for Henry, empirical, UNIFAC, and COSMO-RS;
- `IdealRaoultAdapter` and `UnavailableEquilibriumAdapter`.

Use immutable dataclasses, canonical mappings, stable hashes, finite checks, `math.fsum`, exact units, and no implicit conversion or default values.

Run the focused C4 tests until GREEN. Run Ruff, basedpyright, and mypy on the new file and tests.

## Task 3: export and verifier integration

Update only:

- `engine/physics/__init__.py` to export accepted C4 contracts;
- `engine/project_verification.py` to add the C4 test to `truth-core` and the C4 module to the bounded lint/typecheck slices.

Run C4, C3, C2, C1, and C0 focused tests plus verifier contract tests.

## Task 4: adversarial and mutation evidence

Independently mutate temporary copies or restore the exact source after each bounded mutation:

1. replace `x_i * p_i*` with a defective expression and prove analytic tests fail;
2. remove the bubble-pressure guard and prove the boiling-guard test fails;
3. relax the exact input-set hash binding and prove the tamper test fails.

Verify the exact source SHA-256 is restored after every mutation.

## Task 5: C4 gate matrix

Capture separate stdout/stderr, return code, duration, timeout state, and command identity for:

- C4 focused tests;
- C3, C2, C1, and C0 ancestor tests;
- complete root test suite;
- dependency consistency;
- Ruff, basedpyright, and mypy;
- project-verifier focused slice;
- archive verification;
- protected database hashes and SQLite `quick_check`;
- scope/protected-path validation;
- evidence-manifest validation.

Do not treat a hung terminal, partial output, nonempty unexpected stderr, or a narrow test as broad acceptance.

## Task 6: bounded DeepLuna audit and Sol acceptance

After all local evidence is green:

1. run a fresh exact-project `deepseek_check`;
2. submit one bounded DeepLuna Fast read-only audit of committed C4 code/tests/evidence, one call, `FLASH`, `NO_LUNA`;
3. locally reproduce every negative or gate-bearing finding;
4. commit the evidence seal;
5. replay the gate against that exact commit with a clean index and preserved unrelated worktree changes;
6. write and commit `docs/verification/c4/equilibrium_model_gate.json` and `.md` only if all exit criteria pass;
7. verify the decision commit's parent, changed-path scope, focused C4 tests, evidence validator, protected state, and empty index.

C5 opens only when the canonical C4 gate says `decision=PASS` and `c5_open=true` and exact-commit replay independently agrees.
