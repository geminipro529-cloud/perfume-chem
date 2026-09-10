# Full-gate classification record — 2026-09-11

Provenance: drafted by gate lane `D:\chatbots\.gate-lanes-20260911\L-classification-doc` from the six
shard-lane reports and the three triage lanes. The body below records the state at the gate baseline
`0e82b314`; the addendum at the end carries the parent's authoritative post-fix measurements at
`a32571c7`. Nothing in the body was re-derived during harvesting.

---
# Full-gate classification record — 2026-09-11

**Draft target (do not commit from this lane):** `docs/governance/verification_20260911_full_gate_classification.md`

## Baseline and method

- **Baseline commit: `0e82b314e4e1cd79e680bdbac64301d630232fa6`** — "Pin LF checkout for the raw-byte-pinned D0 control formulas" (integration repository).
- Every gate lane was a detached worktree of that commit; no lane committed, merged, pushed, reset, cleaned, or created a worktree, and no lane wrote outside its own `_lane_out/`.
- Interpreter used by the engine lanes and by lane G's authoritative backend run:
  `D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe` (CPython 3.11.15).
  Lane G additionally used the main checkout's Poetry environment
  `C:\Users\ASUS\AppData\Local\pypoetry\Cache\virtualenvs\perfume-chem-api-zbbAKNtf-py3.11\Scripts\python.exe`.
- Inputs read (all under `D:\chatbots\.gate-lanes-20260911\`): `A-truth-core`, `B-data-knowledge`, `C-gates-families`,
  `D-legacy-integration`, `E-backend`, `F-package-docker` (`_lane_out\*.md` + `*.json`), triage `H-truthcore-triage`,
  `I-extensions-triage`, `J-legacy-triage`, and `G-backend-tests` (report present, not PENDING).
- Every value below is copied from those inputs. Anything a lane did not establish is written `UNKNOWN` or `NOT TESTED`;
  no number was inferred, averaged, or invented.

## The 21 verifier checks

The 21 names are the verifier's own set: the single selected check plus the 20 `omitted_checks` recorded in every lane JSON
(`A-truth-core/_lane_out/A-truth-core.json`). "Lane result" is what that lane executed at `0e82b314`.

| # | Check | Lane result (lane) | Authoritative main-checkout result | Classification | Evidence path |
|---|---|---|---|---|---|
| 1 | engine-compile | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | listed in `omitted_checks` of A–F JSON |
| 2 | engine-lint | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | same |
| 3 | engine-typecheck | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | same |
| 4 | formula-artifact-validation | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | same |
| 5 | engine-tests-truth-core | **FAIL** — 4 failed / 962 passed, 52.20 s (lane A) | UNKNOWN as an executed result; H proved the four failures byte-identical in `D:\chatbots\perfume-chem-integration-20260909` at `0e82b314` | **mixed** — 3 stale authority/environment pins + 1 genuine replay divergence + 1 provable code defect (see §Truth-core) | `A-truth-core/_lane_out/A-truth-core.md`, `H-truthcore-triage/_lane_out/H-truthcore-triage.md` |
| 6 | engine-tests-data-knowledge | **FAIL** — 40 failed / 212 passed / 1 skipped, 52.27 s (lane B) | UNKNOWN — not executed there (the ignored KB file exists in the main checkout) | **environmental** — `sqlite3.OperationalError: unable to open database file` from the gitignored `data/perfumery_kb.db` | `B-data-knowledge/_lane_out/B-data-knowledge.md` |
| 7 | engine-tests-gates-families | **PASS** — 629 passed / 0 failed, 135.88 s (lane C) | UNKNOWN | **green** | `C-gates-families/_lane_out/C-gates-families.md` |
| 8 | engine-tests-legacy | **FAIL** — 1 failed / 46 passed / 26 errors, 24.9 s (lane D) | UNKNOWN as an executed result; J showed the census pin still drifts in the main checkout | **mixed** — 26 errors environmental, 1 failure governance hold | `D-legacy-integration/_lane_out/D-legacy-integration.md`, `J-legacy-triage/_lane_out/J-legacy-triage.md` |
| 9 | engine-tests-integration-extensions | **FAIL** — 14 failed / 924 passed, 230.2 s (lane D) | UNKNOWN as an executed result; the 14 ids are recorded as identical in the main checkout by `GATE.md` Lane I | **mixed** — 13 stale expectations (fix drafted in lane K) + 1 governance hold | `D-legacy-integration/_lane_out/D-legacy-integration.md`, `I-extensions-triage/_lane_out/I-extensions-triage.md`, `K-extensions-fix/_lane_out/K-extensions-fix.md` |
| 10 | backend-lint | **PASS** — `ruff check app`, exit 0 (lane E) | UNKNOWN | **green** | `E-backend/_lane_out/E-backend.md` |
| 11 | backend-typecheck | **FAIL** — 142 errors in 19 files, 116 sources checked (lane E) | UNKNOWN | **software defect** (static type errors, dominated by 119 `no-any-return` and 22 `valid-type`) | `E-backend/_lane_out/E-backend.md`, `E-backend.mypy.txt` |
| 12 | backend-tests | **BLOCKED in lane E** (Poetry env for that lane has no project dependencies); **FAIL** in lane G's authoritative run — 1 failed / 629 passed, 715.26 s (11:55) | UNKNOWN as an executed result; G verified the failing corpus files hash identically in the main checkout | **environmental** for lane E's BLOCKED state (lane-local empty venv) + **stale expectation** for the real failure (frozen `IDENTITY_SNAPSHOT["source_corpus_sha256"]` vs current `data/knowledge_graph/`) | `E-backend/_lane_out/E-backend.md`, `G-backend-tests/_lane_out/G-backend-tests.md`, `G-backend-tests.log` |
| 13 | scientific-audit | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | `omitted_checks` in A–F JSON |
| 14 | material-data-validation | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | same |
| 15 | knowledge-rule-validation | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | same |
| 16 | golden-formula-regression | NOT TESTED as a check (not selected by any lane) — the verifier's separate `golden_output_changes` signal is `unchanged` / `changed=false`, expected == actual == `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec`, in all six lane JSONs | UNKNOWN | NOT TESTED (signal green, check not run) | `_lane_out/*.json` (`golden_output_changes`) in A–F |
| 17 | golden-api-regression | NOT TESTED (no lane assigned) | UNKNOWN | NOT TESTED | `omitted_checks` in A–F JSON |
| 18 | docker-build | **NOT TESTED** — Docker CLI absent on this host (lane F: `Get-Command docker` resolves to nothing; nothing installed) | UNKNOWN | NOT TESTED | `F-package-docker/_lane_out/F-package-docker.md` |
| 19 | docker-smoke-test | **NOT TESTED** — same reason | UNKNOWN | NOT TESTED | same |
| 20 | package-build | **PASS** — exit 0, 25.1 s; `perfume_chem_engine-0.1.0-py3-none-any.whl`, 1,657,027 bytes, sha256 `09122d04f16bab5874ebe73fa65bc4c209ac3dbc41eba146a234340e5f4880b0` (lane F) | UNKNOWN | **green** | `F-package-docker/_lane_out/F-package-docker.md` |
| 21 | package-wheel-smoke | **PASS** — exit 0, 36.6 s (lane F) | UNKNOWN | **green** | same |

Aggregate from the lane JSONs: `verification_scope = "partial"` in every lane (a gate lane selects a subset, so its
`completion_gate` of `FAIL`, `NOT_EVALUATED` or its `release_readiness` of `blocked` describes that slice only).
`docker_status = "SKIPPED"` in all six lane JSONs.

## Environmental cause: the lanes lack ignored runtime artifacts

The gate lanes are detached worktrees of a repository that git-ignores its runtime state, so lane-only failures are
**candidates, not verdicts**:

- `data/perfumery_kb.db` (2,084,864 bytes) is ignored by `.gitignore` (`*.db`). It exists in the canonical checkout and in
  `D:\chatbots\perfume-chem-integration-20260909\data\`, but was never seeded into the gate worktrees. This single cause
  accounts for **40 of 40** engine-tests-data-knowledge failures (lane B) and **26 of the 26** errors in the legacy shard
  (lane D, `tests/test_interaction_graph.py`). Lane D's supplementary (non-gate) diagnostic copied the DB into its lane and
  got `26 passed in 1.53s`, then removed the copy.
- Prior `verification_runs/*.xml` are ignored (`verification_runs/`). The lane worktree contains **0** `*.xml` artifacts,
  while the main checkout carries `backend.xml`, `engine-truth-core.xml`, `engine-data-knowledge.xml`,
  `engine-gates-families.xml`, `engine-legacy.xml`, `engine-integration-extensions.xml`.
- Line-ending state is a second environmental axis: `core.autocrlf = true` materialises CRLF for paths that lack a
  `text eol=lf` attribute, which affects every raw-byte-pinned check. Lane J proved
  `incoming_review/Meaningful_Complexity_Audit_v2.md` is pure EOL drift (pin == committed LF blob) while
  `engine/temporal_graph.py` is genuine content drift; lane H classified the 19 failing C0 source pins into 8 EOL-only
  (class B) and 11 non-recoverable (classes C/D/E).

## Truth-core failure breakdown (lane A items, triaged in lane H)

| Item | Fails at | Defect is in | Classification | Disposition |
|---|---|---|---|---|
| H-1 `test_inventory_covers_every_c0_category_and_only_allowed_classes` | `tests/test_c0_physical_model_inventory.py:44` (58 validator errors) | authority record (`docs/verification/c0/physical_model_inventory.json`), not the test | **scientific hold / governance hold** — class B (8 paths) provably repairable content-neutrally; classes C/D/E (11 paths) need an owner re-freeze | documented hold |
| H-2 `test_legacy_fixture_lock_and_replay` | `tests/test_c0_physical_model_inventory.py:196` (22 validator errors) + 1 replay divergence | pins: stale authority; `C0-LH-005`: **code** | **mixed** — stale authority (hold) + one genuine post-freeze behaviour change in `natural_absolute_decomposition` / `antoine` | documented hold; divergence must be adjudicated |
| H-3 `test_material_panel_matches_inventory_snapshot_and_required_domains` | `tests/test_c5_calibration_program.py:362` | superseded 2026-08-05 snapshot + raw-byte compare | **scientific hold** — do not regenerate the constant as a drive-by fix | documented hold |
| H-4 `test_engine_shards_cover_every_test_file_once` | `tests/test_project_verification.py:69` (`engine/project_verification.py:35` manifest) | **code** — 5 test files unassigned (`test_gap_detector_character_evidence.py`, `test_inventory_stock_clarifications_2026_09_10.py`, `test_numeric_character_contract.py`, `test_post_cutoff_supplement_20260910.py`, `test_sambac_proxy_identity.py`) | **software defect**, provable by exact set equality | fixable |

## Integration-extensions breakdown (lane D items, triaged in lane I, fixed in lane K)

13 of the 14 failures are **stale expectations** pinned to the superseded collapsed successor label
`USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20260907` and to pre-`601d203c` `inventory.txt` text. The governing policy is
committed in `docs/governance/repository_verification_comparison_20260909.md` ("Update obsolete stock assertions against
the actual current authority") and `docs/governance/consolidation_execution_20260910.md:128-129`. Lane K's draft diff
updates only the superseded expectations and moves the pair from `13 failed / 36 passed` to `0 failed / 49 passed`.
Lane K left one item open for the parent: the four re-declared working-stock labels
(`Anisaldehyde 10% v/v in ethanol`, `Ethyl Maltol 1% v/v in ethanol`, `Hexyl Acetate 1% v/v in DPG`,
`Helional 10% v/v in ethanol`) are still unregistered in the data spine.

## The two census holds — owner decision recorded verbatim

Both census checks are classified **governance hold**. The owner decision, recorded verbatim:

> **do not unfreeze `complexity_module_registry_v1.json`**

| Check | Failing test | Lane result | Main checkout | Evidence |
|---|---|---|---|---|
| engine-tests-legacy (census half) | `tests/test_pipeline_audit_verify.py::test_complexity_benchmark_census_json` | 1 of the 1 legacy failure; `assert rc == 0` fails because the census returns `state = "HOLD"` (lane D, reproduced by lane J in 4.90 s) | reproduces: lane J measured the `engine/temporal_graph.py` pin still drifting in the main checkout (`34b286e7a84e…`) | `J-legacy-triage/_lane_out/J-legacy-triage.md`, `J-census.json` |
| engine-tests-integration-extensions (census half) | `tests/test_complexity_registry.py::test_repository_census_has_exactly_one_classification_per_finding` | 1 of the 14; `assert result.state == "PASS"` fails, `HOLD` returned, `hash_drift = ["engine/temporal_graph.py", "incoming_review/Meaningful_Complexity_Audit_v2.md"]` | `incoming_review/…` matches its pin in the main checkout (EOL artifact only); `engine/temporal_graph.py` still drifts | `I-extensions-triage/_lane_out/I-extensions-triage.md`, lane K's 3-file run (`1 failed, 67 passed`) |

Census detail common to both: classification coverage is complete
(`finding_count = 56`, `unclassified = []`, `missing = []`, `multiply_classified = []`,
`registry_sha256 = 40057a83ead2f29351d5a530382d7c1ea46a3d109ad6c480b711076347479fc1`, `provider_calls = 0`);
the `HOLD` is caused only by module-hash drift in `engine/perception/complexity_registry.py:344-357`.
Lane K was instructed not to touch these two tests, and did not.

## Docker

**docker-build and docker-smoke-test: NOT TESTED.** The Docker CLI is not available on this host
(`docker --version` → "not recognized"; `Get-Command docker` resolves to nothing; `docker-compose` likewise absent).
Nothing was installed. The verifier reports `docker_status = "SKIPPED"` and lists both checks under `omitted_checks`;
neither appears with a pass/fail verdict anywhere in the gate evidence.

## Release authority

**No release authority is granted by this document or by any lane in this gate.** Every lane ran at a detached
`0e82b314` with `verification_scope = "partial"`; no check result here constitutes admission, promotion, publication,
production activation, or scientific release. `release_readiness` in the lane JSONs is `blocked` on the code, data,
validation and infrastructure axes, and the external blocker "held-out sensory validation is still required" remains
open (lanes A–D JSONs).

## UNKNOWN and out-of-scope notes

- Checks 1–4, 13–15, 17 were not selected by any lane: their state at `0e82b314` is `NOT TESTED`, not "passing".
- Checks 18–19 are `NOT TESTED` because the Docker CLI is absent; this is not a defect finding.
- No lane executed a test command inside `D:\chatbots\perfume-chem-integration-20260909` itself; every "main-checkout"
  column entry above is either `UNKNOWN` or a byte-identity inference, and is labelled as such.
- A `M-truthcore-fixes` lane directory also exists under `D:\chatbots\.gate-lanes-20260911\`, but it is **not** one of the
  inputs the gate brief lists for this document, so nothing from it is incorporated here. Its contents were not evaluated.

---

# Addendum — authoritative post-fix results (parent, 2026-09-11)

Two evidence-clean repairs landed after the body above was drafted, and every number below was
measured in the main integration checkout, not in a lane. This addendum supersedes the affected rows.

| Commit | Repair |
| --- | --- |
| `c1e2d74e` | Identity-reconciliation tests track the current per-generation inventory authority (13 expectations). |
| `a32571c7` | EOL-only C0 pins (8 paths, 15 pin rows) declare `text eol=lf`; five missing test files assigned to engine shards. |

## Measured results before and after

| Check | At `0e82b314` (lane) | Authoritative main checkout | At `a32571c7` (main) |
| --- | --- | --- | --- |
| compile / lint / typecheck / formula-artifact-validation / scientific-audit / material-data-validation / knowledge-rule-validation / golden-formula-regression / golden-api-regression / golden-fixture-lock | not run in lanes | quick gate 10 passed / 0 failed at `0e82b314` | **quick gate 10 passed / 0 failed** (`_state/quick_gate_a32571c7.json`) |
| engine-tests-truth-core | 4 failed / 962 passed | reproduced identically | **3 failed / 963 passed** — shard-coverage failure fixed; the rest are holds |
| engine-tests-data-knowledge | 40 failed / 212 passed | **253 passed / 0 failed** — lane failures were the missing ignored `data/perfumery_kb.db` | unchanged (ground: green) |
| engine-tests-gates-families | 629 passed / 0 failed | — | unchanged (ground: green) |
| engine-tests-legacy | 1 failed / 46 passed / 26 errors | 1 failed / 72 passed — the 26 errors were lane artifacts | unchanged (ground: 1 hold) |
| engine-tests-integration-extensions | 14 failed / 924 passed | 14 failed / 924 passed | **1 failed / 948 passed** — only the census hold remains |
| backend-lint | PASS | PASS | unchanged |
| backend-typecheck | 142 errors (lane) | **Success: no issues found in 116 source files** — the lane result was an empty-venv artifact | unchanged (ground: green) |
| backend-tests | BLOCKED in lane E; lane G (authoritative env): 1 failed / 629 passed, 715 s | — | unchanged (1 hold) |
| package-build / package-wheel-smoke | PASS | — | unchanged (ground: green) |
| docker-build / docker-smoke-test | NOT TESTED (Docker CLI absent) | — | unchanged (NOT TESTED) |

## Holds recorded, with the owner's decisions

| Hold | Evidence | Decision |
| --- | --- | --- |
| Complexity census pin for `engine/temporal_graph.py` (drives two failures: the legacy census test and the registry census test) | the pin equals neither the LF blob `4f655236…` nor its CRLF form; the v1 registry was generated from a CRLF checkout and the module legitimately changed in `8916c30b`; the overlay schema admits only *additions* of unvalidated candidates, so it cannot re-bind a base pin | **Registry stays frozen — do not unfreeze.** Governance hold. |
| C0 pins in classes C/D/E (older commit, live-uncommitted checkout, or nothing reachable), plus 8 line drifts and 20 call-edge tokens | `H-truthcore-triage.md` §2; validator error count fell 80 → 63 after the EOL-only repair, leaving 35 stale-hash, 20 call-edge and 8 line-drift messages | Documented hold; a re-freeze is an owner decision |
| `C0-LH-005` replay divergence (ΔHvap fallback, one fewer constituent, changed OAV) | `H-truthcore-triage.md` §3 — 23 of 24 frozen cases replay identically | Documented hold; a real behaviour change to adjudicate before any re-freeze |
| C5 inventory binding constant `9d778721…` | pin equals the 2026-08-05 snapshot recorded in `data/pipeline_audit/events.jsonl`; the raw-byte compare is EOL-sensitive and the authority moved in `601d203c` | Documented hold — do not auto-update |
| Backend frozen corpus baseline (`test_b4_legacy_rule_adapter`) | `IDENTITY_SNAPSHOT["source_corpus_sha256"]` differs for `synergy_matrix.json` and `theory_rules.json` | Documented hold — semantic review before a new baseline or a revert |
| Docker groups | Docker CLI not installed | `NOT TESTED`, never "passed" |

No release authority is granted by this record. The remaining red checks are governance and
scientific holds, not unexplained regressions.
