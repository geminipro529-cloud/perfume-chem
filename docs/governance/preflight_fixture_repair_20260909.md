# Preflight fixture repair — 2026-09-09

Status: focused checkpoint PASS; repository release remains HOLD.

## Change

Updated three monkeypatch targets in `tests/test_run_evidence_contract.py` from the removed `engine.pipeline.preflight.parse_inventory` to the currently consumed `engine.pipeline.preflight.parse_current_inventory`. No production code, inventory authority, material data, test expectations, or gate thresholds changed in this checkpoint.

The tests still exercise the real stock resolver and gates. They require rejection of a stock-strength substitution (including its 5.5x aggregate active-dose impact), rejection by stock/quantitative/reference contracts in the integrated caller, and rejection of an essential-oil request when only an absolute is present. No fake passing stock-contract result was introduced.

## Fresh verification

- Three formerly failing incident tests: **3 passed**.
- Complete evidence-contract, artifact-rebind, pre-mix guard, pipeline-preflight, and Deep Plane caller test modules: **82 passed**, 2,353 warnings, 22.74 seconds.
- Ruff for the changed test file: passed.
- Scoped `git diff --check`: passed, with the existing Git line-ending conversion warning.
- JUnit: `D:/codex-preservation/perfume-chem-20260909/preflight-fixture-repair-final.xml`.

The earlier artifact repair's three residual fixture failures are resolved by this checkpoint. The 82-test run also exercises the preceding artifact binding and LF/CRLF rollback repairs. It is not a full-repository or release verification result.

## Fingerprint

- `tests/test_run_evidence_contract.py`: SHA256 `949586BB05B3313833C41BEFAC78E912539057A16D8FEAE654F4BEC1D3D50F67`
- `scripts/formula_release_gate.py` (unchanged this checkpoint): SHA256 `B02A6567A9F0233FA117C008C91B4546527CF78FEBA9B72CE79E94ED32B292E3`

Remaining work includes the previously documented isolated-environment prerequisites, outdated stock assertions, unresolved OAV coverage, and broader verifier failures. Deep Plane remains disabled by default. No commits, merges, publication, historical artifact rewrites, or dependency changes were performed.
