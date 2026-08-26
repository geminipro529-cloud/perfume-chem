# A0.1 Repository and Worktree Baseline Capture

**Date:** 2026-07-29
**Phase:** A0 — Establish the Authoritative Truth Baseline
**Plan:** BUILD A: Canonical Convergence and Reconstruction Hardening

---

## Repository Identity

| Field | Value |
|-------|-------|
| Remote | `https://github.com/geminipro529-cloud/perfume-chem.git` |
| Branch | `codex/add-inventory-materials` |
| Commit SHA | `2e46e4ce5795014e92924102c38c1358d7a9fdca` |
| Upstream | `origin/codex/add-inventory-materials` |
| Other branches | `master` (`974ff47`, ahead 12) |

### Branch Verification Gate

**CONFIRMED:** `codex/add-inventory-materials` is the branch containing the reconstruction work. The untracked engine modules (`engine/reconstruction/`, `engine/evidence/`, `engine/target/`, `engine/inventory/`, `engine/bottle/`, `engine/versioning/`, `engine/analytical/`, `engine/safety/`, `engine/sensory/`, `engine/graphs/`, `engine/reports/`, `engine/identity/`, `engine/units/`, `engine/experiments/`) and 21 new test files are all present in this branch's working tree.

---

## Worktree State

| Metric | Count |
|--------|-------|
| Modified tracked files | 93 |
| Untracked files | 336 |
| Staged files | 0 |
| Diff insertions | 8,202 |
| Diff deletions | 2,278 |

---

## Preserved Baseline Artifacts

All preserved at `docs/verification/a0_baseline/`:

| Artifact | File | Size |
|----------|------|------|
| Binary-safe patch (tracked modifications) | `tracked_modifications.patch` | 16,570,132 bytes (~16.6 MB) |
| Untracked file manifest (SHA-256 + size + path) | `untracked_manifest.txt` | 43,288 bytes (336 entries) |
| Environment capture (secrets redacted) | `env_capture.txt` | See below |

### Files that could not be hashed (locked by running daemon)

- `.deepluna-home/daemon_stderr.log` (process lock)
- `.deepluna-home/daemon_stdout.log` (process lock)
- `.deepluna-home/projects/perfume-chem/daemon-v2/scheduler.sqlite3` (WAL lock)
- `.deepluna-home/projects/perfume-chem/daemon-v2/scheduler.sqlite3-shm` (WAL lock)
- `.deepluna-home/projects/perfume-chem/daemon-v2/scheduler.sqlite3-wal` (WAL lock)

These are daemon runtime files and do not affect the repository source state.

---

## Lockfile Digests

| File | SHA-256 |
|------|---------|
| `requirements.txt` | `915A89933EEFB56AB10C9F90FC9ABE86A5FADABA1DDF4B04EB64406F78B6638A` |
| `backend/poetry.lock` | `F48137C28C52F7A24F11B6186CE3B4E9A3B161B6F6B570DB7E2B56B30DE41FFD` |
| `backend/pyproject.toml` | `B1B08127C0B380148F6EA8CF750D165836696238DB011AB8F2DA4764C2DAB98E` |
| `pyproject.toml` (root) | `FAAACCEF1470EECC4F8EA1A9A8859384253993020E2CE8B2BD51C376FAA2086A` |
| `package-lock.json` | `38A0BD7C215848B671711AD985D06F927ED1969BA781E9C56521D94C104DAFFC` |

---

## Database State

| Item | Value |
|------|-------|
| Alembic ini | `backend/alembic.ini` exists |
| Alembic versions | 2 migration files: `20260716_0001_lab_beta.py`, `20260717_0001_phase_1a_domain.py` |
| DB files | Multiple `.db` files in working tree (gitignored) |

---

## Verification Artifacts

| Artifact | SHA-256 | Last Modified |
|----------|---------|---------------|
| `verification_runs/project_verification.json` | `51C3F60ACF3DEFFAA1E15C18B1B38896931BC24D28A671BBDFF030F1E6C70A2A` | 2026-07-27 11:08:06 |
| `verification_runs/science_audit.json` | `569C4DD700DC7AA6525861875530866D3636DD1A42FD48CBEE64C0A005739B0A` | (present) |
| `tests/fixtures/golden_formula_cases.sha256` | `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec` | (present) |

### Verifier Result Summary (from 2026-07-27)

| Outcome | Count | Items |
|---------|-------|-------|
| Passed | 18 | engine-compile, engine-lint, engine-typecheck, engine-tests-truth-core, engine-tests-data-knowledge, engine-tests-gates-families, engine-tests-legacy, backend-lint, backend-typecheck, backend-tests, scientific-audit, material-data-validation, knowledge-rule-validation, golden-formula-regression, golden-api-regression, package-build, package-wheel-smoke, golden-fixture-lock |
| Failed | 1 | `formula-artifact-validation` (uncommitted formula file modifications) |
| Skipped | 2 | `docker-build`, `docker-smoke-test` (infrastructure) |

**Note:** The verifier result is 2 days old. The working tree has changed since then. The `formula-artifact-validation` failure is expected to persist until formula files are committed or stashed.

---

## Environment Capture

| Variable | Status |
|----------|--------|
| `PYTHONPATH` | NOT_SET |
| `VIRTUAL_ENV` | NOT_SET |
| `PERFUME_PIPELINE_AUDIT_PATH` | NOT_SET |
| `OPENAI_API_KEY` | PRESENT (redacted) |
| `SECRET_KEY` | PRESENT (redacted) |
| `DEEPINFRA_API_TOKEN` | NOT_SET |
| `PERFUME_DEEPINFRA_API_KEY` | PRESENT (redacted) |
| `PERFUME_DEEPSEEK_API_KEY` | PRESENT (redacted) |
| `PERFUME_CHEAPLUNA_DEEPINFRA_API_TOKEN` | NOT_SET |
| `GITHUB_TOKEN` | PRESENT (redacted) |
| `USERPROFILE` | `C:\Users\ASUS` |

---

## Constraint Compliance

- [x] Uncommitted work preserved as binary-safe patch
- [x] File manifest with hashes created
- [x] Lockfile digests recorded
- [x] Alembic heads identified
- [x] Artifact hashes recorded
- [x] Environment variables captured with secrets redacted
- [x] No commit, stash, reset, regenerate, or rebind performed
- [x] Branch identity confirmed (`codex/add-inventory-materials`)