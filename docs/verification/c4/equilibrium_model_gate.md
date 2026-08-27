# Build C4 equilibrium-model gate

Decision: **PASS**. The local implementation, evidence matrix, final DeepLuna Fast audit, Sol reconciliation, evidence commit, and exact-commit replay are green. C5 is open.

## Accepted executable boundary

C4 adds one executable model: `IDEAL_RAOULT_BASELINE` version `c4-ideal-raoult-v1`. It is a transparent theoretical comparison baseline using `p_i = x_i * p_i_star` and `gamma_i = 1`. It does not renormalize gas fractions. It accepts only exact C1-selected vapor pressure in Pa at the C2 matrix temperature and molecular weight in g/mol, with exact C2 matrix/environment and C3 request/input-reference hashes.

Supported matrix bases are mole fraction, mass fraction, mass, and amount. Supported stages are stock solution, concentrate, and finished perfume. Supported environments are sealed equilibrium vial and open liquid surface, with a single liquid phase. Volume fractions, mixed or implicit conversions, incomplete composition, mismatched identity/property bindings, unsupported units or stages, and bubble pressure above system pressure abstain before computation.

The result may **not** feed OAV screening. Its uncertainty is `UNKNOWN`, it carries `C5_UNCERTAINTY_PROPAGATION_REQUIRED`, and it is not measured, calibrated, validated for accuracy, or a canonical production headspace.

## Explicitly withheld capability

Henry-law dilute baseline, empirical matrix correction, UNIFAC or modified UNIFAC, and imported COSMO-RS are explicit unavailable releases. They cannot compute and may not feed OAV screening. The C0 inventory reconciliation recognizes only these declarations; it does **not** activate a COSMO-RS import or calculation. The legacy Hansen/headspace heuristic is not UNIFAC and was not adapted.

## Reproducible verification

The non-PTY matrix ran 24 jobs with ANSI disabled, separate stdout/stderr, explicit timeouts, and sensitive environment names removed without logging values. All jobs passed with empty captured stderr:

- C4 focused: 41 passed.
- C3 compatibility: 105 passed.
- C2 compatibility: 79 passed.
- C1 compatibility: 96 passed.
- C0 compatibility: 24 passed.
- Complete root suite: 1,443 passed.
- C4 dependency invariant: 1 passed.
- C0 standalone inventory verifier: PASS with 48 implementations, 29 call edges, and 24 fixtures.
- Ruff check/format, basedpyright, and mypy: PASS.

Three temporary mutations proved that tests catch removal of Raoult multiplication, removal of the bubble-pressure applicability guard, and omission of the exact input-reference content hash. Each mutation failed as expected. All were restored, and `engine/physics/equilibrium.py` returned to SHA-256 `c2b92a6ba72fc1e64253d155b65bec3e031015eb8150709b45b4ef975bbd7e16` before the authoritative matrix.

The recovery archive is restorable and path-preserving at `D:\.backups\perfume-chem\build-c4-prewrite-20260802T234123+0700.tar`, SHA-256 `0008fc9784ded2567ae3ba5cfd7f3123e2db4c88349e83c80fea5a9b3e353424`. It preserves all 429 existing dirty or untracked paths. Protected databases are byte-identical before and after verification and pass immutable SQLite quick checks. The implementation range changes exactly nine authorized paths and no production caller, migration, database, scientific data artifact, or legacy thermo path.

Primary terminology is anchored to the IUPAC Gold Book entries for [amount fraction](https://goldbook.iupac.org/terms/view/A00296/plain), [Raoult's law](https://goldbook.iupac.org/terms/view/15349/plain), and [partial pressure](https://goldbook.iupac.org/terms/view/P04819).

## Reconciliation notes

A preliminary standalone C0 command used the unsupported `--fixture-sha256` option and failed before verification. The supported `--fixture-sha` command then passed and is the only command in the authoritative matrix. The initial C4 DeepLuna compact inventory omitted its requested citation structure, so Sol reused only facts independently reproduced from local source and made no retry or capability decision from uncited provider text.

DeepLuna Fast is exact-project READY on `perfume-chem`, Fast-only through DeepInfra Priority, with zero open or unknown reservations and no Luna, GLM, or Codex-worker fallback. Its final audit returned PASS with no negative findings or scope deviation. Some compact positive text was truncated, so Sol independently reproduced all six boundary findings locally. Provider claims remain advisory; Sol owns scope, provenance, scientific judgment, and final acceptance.

## Remaining limitations

C4 does not evaluate vapor-pressure equations, propagate uncertainty, implement nonideal models, validate predictive accuracy, authorize OAV use, switch production callers, create persistence, or complete Build C. The sealed evidence commit `30a03dfd0c61f23cfa3bfc71d42038f5ae903ebe` replayed all 19 jobs successfully, so C5 is now open.
