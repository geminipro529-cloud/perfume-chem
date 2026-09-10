# Concurrent hedonic workflow implementation

Scope: callable computer-only structural search and evaluator admission.
No formula doses, inventory entries, release gates or safety policies changed.
No new pipeline script or worktree. Existing dirty changes preserved.

## Behavior verified

- Named search lanes execute concurrently under one evaluator per round.
- Shared evaluations coalesce within a version; revisions have separate caches.
- Parent compares whole candidates against the same round incumbent.
- Every criterion/scenario is protected; accepted changes preserve total and bounds.
- Missing liking data does not prevent explicit structural optimization.
- Missing/invalid structural losses do not become zero or success.
- Hard identity constraints cannot be traded for body improvement.
- Revision admission uses caller-frozen regression intervals, independent of scores.
- Accepted revisions rescore baseline, incumbent and retained lane winners.
- A broken initial evaluator can be replaced by an admitted supplied revision.
- Recursion stops at target, plateau, unavailable evaluation or round budget.
- No physical preliminary mix, sensory validation or release claim is produced.

## Fresh focused verification

Command: `.venv/Scripts/python.exe -m pytest tests/test_concurrent_hedonic_design.py tests/test_targeted_hedonic_evidence.py tests/test_hedonic_design_loop.py tests/test_gate_architectural_authority.py -q`

Result: **68 passed**; 1,680 existing pytest-asyncio deprecation warnings.
New tests were observed failing before their corresponding changes; the final
suite includes 14 concurrent-workflow cases. Ruff passed for both changed
engine modules and the new test file. `git diff --check` reported no whitespace
errors (Git emitted line-ending conversion notices).

Saved EDP record SHA256 remains
`426857f85ad9cd666e6cc55cdb9391de8cd6b5858bbc6f06e8d0d1a239aa3fc3`.

The full project verification command returned **FAIL**: 10 checks passed,
9 failed and 2 Docker checks were skipped. Report:
`verification_runs/project_verification.json`. Failures include protobuf
collection errors under Python 3.14, backend missing source-study contracts,
inventory/data mismatches, artifact validation, gate/legacy tests and scientific
coverage (84.959 against a >85 requirement). Those broader failures were not
repaired or bypassed in this change. The audit overlapped the final focused
hardening edits, so it is diagnostic rather than an immutable final-source
release receipt. The focused 68-test run and lint were run after those edits.
No full-project green or release claim is made.

## Deliberate limits

This is an optimization mechanism, not a newly calibrated perfume predictor.
The caller must provide explicit target-specific structural losses, scenarios,
stock/active/carrier feasibility and independent adversarial admission cases.
Raw amounts, OAV or generic pleasantness are not silently converted into liking.
Evaluator revisions are supplied implementations; the loop does not write code
or weaken its regression cases. Pure bounded thread-safe callbacks are required.
There is no forced cancellation of hung callbacks. The CLI and actual EDP
adapter have not been wired to this new mode, and no revised perfume has been
selected by these synthetic software tests.
