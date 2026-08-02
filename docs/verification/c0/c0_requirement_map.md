# Build C0 requirement-to-evidence map

Date: 2026-08-02
Authoritative checkout: `D:\chatbots\perfume-chem`
Baseline commit: `9e88f5d80ee6b1c001ff90b7e5ac6d125d60b871`
Master contract: `SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md` lines 3154-3208
Master contract SHA-256: `7050f2e77160e9039241e8925f844beb3d32374ad075742fe958518ac0eca349`

This map binds the C0 contract to repository artifacts and executable checks.
It does not promote any legacy output or authorize C1 by itself. C1 remains
closed until the final DeepLuna review and staged-scope gate recorded below pass.

## Requirement mapping

| Contract requirement | Authoritative evidence | Local result |
| --- | --- | --- |
| Inventory every implementation and caller for all 15 claim families (lines 3158-3174) | `physical_model_inventory.json`, `physical_model_inventory.md`, `scripts/verify_c0_physical_model_inventory.py` | PASS: 48 implementation records, 29 source-bound call edges, and all 15 required categories |
| Record unsupported or inactive capabilities rather than infer them | Inventory records `C0-PM-017`, `C0-PM-025`, and `C0-PM-026`; verifier absence queries | PASS: DIPPR-style equations and COSMO-RS are `UNSUPPORTED`; UNIFAC is an inactive `STUB` |
| Use only the eight C0 classifications (lines 3176-3187) | Inventory vocabulary, verifier, `test_inventory_covers_every_c0_category_and_only_allowed_classes` | PASS: every record is constrained to the exact eight-value vocabulary; no current model is promoted as empirically calibrated |
| Record inputs, outputs, conditions, consumers, evidence labels, tests, and claim impact (line 3189) | Inventory schema, source/symbol hashes, caller-edge evidence, `test_inventory_records_are_source_bound_and_claim_explicit` | PASS: required fields are non-empty where applicable and source-bound |
| Choose one canonical interface and one structural runtime per supported claim (lines 3191-3200) | `ADR-2026-08-02-c0-physical-model-consolidation.md`, especially `Claim-family routing decision`; ADR test | PASS: all claim families route toward one versioned `engine.physics` boundary; current compatibility authorities and withheld/advisory paths are explicit |
| Prevent two silently different headspace engines from answering one request (line 3200) | ADR one-implementation rule and claim-family table; inventory runtime/disposition fields | PASS at the C0 architecture gate: only the named compatibility authority may answer until its later phase gate passes; alternatives are advisory, fixture-only, deprecated, or withheld |
| Preserve current outputs as `LEGACY_HEURISTIC` fixtures with input hashes and warnings (lines 3202-3204) | `c0_legacy_physical_model_cases.json`, companion SHA, fixture validator and replay tests | PASS: 24 selectors have exactly one frozen case, non-promotion warning, canonical input hash, implementation-source hash binding, and deterministic replay |
| Treat fixtures as regression/migration evidence, not scientific promotion (line 3204) | Fixture warnings, ADR compatibility disposition, inventory evidence labels, tests | PASS: every case states that it is not scientific validation |
| Complete model/call graph, ADR, and fixtures before new model implementation (lines 3206-3208) | Inventory/report, ADR, fixtures, verifier/test/lint logs, staged-scope gate | LOCAL PASS; final DeepLuna evidence pending below |

## Honest legacy defect lock

`engine.skin_interaction.score_skin_interaction` appends known-material
classification and mass inside its known-data branch and again in a shared
post-branch block. Frozen case `C0-LH-008` therefore contains duplicate reservoir
rows and `reservoir_pct = 140.0`. C0 records and replays this defect without
changing production behavior or treating it as physical evidence.

## Reproducible local gate

All commands were non-interactive, had 120-second timeouts, disabled color where
supported, and captured stdout/stderr separately.

| Gate | Evidence | Result |
| --- | --- | --- |
| C0 verifier | `logs/c0-verifier.result.json`, `logs/c0-verifier.stdout.txt`, `logs/c0-verifier.stderr.txt` | PASS; 48 implementations, 29 edges, 24 fixtures; stderr empty |
| Focused pytest | `logs/c0-focused-pytest.result.json`, `logs/c0-focused-pytest.stdout.txt`, `logs/c0-focused-pytest.stderr.txt` | PASS; 24 tests; stderr empty |
| Ruff check | `logs/c0-ruff-check.result.json`, `logs/c0-ruff-check.stdout.txt`, `logs/c0-ruff-check.stderr.txt` | PASS; JSON result `[]`; stderr empty |
| Ruff format check | `logs/c0-ruff-format-check.result.json`, `logs/c0-ruff-format-check.stdout.txt`, `logs/c0-ruff-format-check.stderr.txt` | PASS; two files already formatted; stderr empty |
| Canonical fixture bytes | `tests/fixtures/c0_legacy_physical_model_cases.sha256` | PASS; `e66c5e94217913db83487897079131dfef6e2e6d321ee4a7216e4c74302f89b8` |
| Cross-checkout line endings | `.gitattributes` fixture-specific `eol=lf` rules | PASS locally after Git attribute and byte-hash verification |

## Preservation and final gates

- Pre-write archive:
  `D:\.backups\perfume-chem\build-c0-prewrite-20260802T150417+0700\build-c0-prewrite-dirty-overlay.zip`
- Archive SHA-256:
  `f235aa61720f7665d98123e1215b0c92e497ae7dd012dea031d454f6ec4aae8f`
- Archive size: 43,506,759 bytes; previously verified path-preserving restore
  against 1,542 source files plus its manifest.
- Production-runtime behavior: unchanged by the C0 artifact set. The final staged
  path list must contain no `engine/**`, `backend/**`, migration, database, or
  unrelated path.
- DeepLuna Fast final review: **SUPPORTING PASS**; job
  `DS-375b37a505088193c8ca6561df64b1d5`, `FLASH`, `NO_LUNA`, positive evidence
  verdict, no negative findings. The malformed final phrase in its summary is
  recorded without retry in `deepluna_final_validation.json` and is not used as
  gate authority.
- Staged-scope gate: **PASS**; 23 C0 files, zero paths outside the explicit
  allowlist, zero `engine/**`, `backend/**`, migration, or database paths, and
  `git diff --cached --check` exits 0.
- C0 exit decision: **PASS, accepted by Sol after local reproduction**. C1
  remains closed until the C0 checkpoint commit and post-commit verification
  succeed.
