# Native receipt API integration — 2026-09-09

Scope: isolated integration checkout, native gate/OAV/pre-mix API compatibility.
No scientific data, inventory authority pins, formula doses, release policy, or
diagnostic activation changed. This is not repository-wide release acceptance.

## Contract and implementation

Local contract sources reviewed before editing: `FormulaDoseReceipt` and exact
input projection in `engine/pipeline/preflight.py`; `GateReport` and the opt-in
caller in `engine/pipeline/gates.py`; exact state/frame checksum and simulation
replay in `engine/pipeline/simulator.py`; native `OAVGateBinding.from_native_results`
and its existing canary in `tests/test_complexity_model_admission.py`.

- Gate reports now retain and serialize the actual optional dose receipt.
  With diagnostics disabled, the existing UNBOUND state and preflight behavior
  remain unchanged. Invalid inputs that cannot construct a receipt still reach
  the default fail-closed preflight; diagnostic-mode construction errors propagate.
- OAV requests may carry an expected receipt SHA256 and formula UID. Explicit
  zero dilutions are no longer silently rewritten to neat stock in the request
  projection. Malformed expected hashes and hashes without a report are rejected.
- Explicit binding reconstructs the receipt against current inventory and the
  exact request, verifies report identity, rebuilds the full formula state, and
  replays every simulation frame. This checks exact dataclass values, not rounded
  display values. Default-mode frames without stored provenance require the same
  complete deterministic replay; no missing checksum is treated as proof.
- Bound analysis recomputes ODT/scaling/intelligence policy outcomes under the
  request's configuration rather than accepting cached gate verdicts. Legacy
  calls without an expected receipt remain explicitly UNBOUND.
- BOUND_GATE_RECEIPT means exact replay identity only. Both BOUND and ABSTAINED
  stock receipts can identify a computation. Strict OAV remains ABSTAINED because
  this API has no compatible measured-air evidence input; release authority is
  explicitly false. Existing preflight and complexity HOLDs are retained.
- `PreMixGuardReport.gate_status` is a compatibility alias of `status`, preserving
  PASS/WARN/FAIL exactly. No active-equivalence threshold or finding was changed.

Checksums are not signatures, trusted-execution attestations, or scientific validation.

## Verification

- Reproduced the original missing GateReport receipt failure before editing.
- The first 44-test run progressed to a second missing API: pre-mix `gate_status`.
  The compatibility alias resolved that failure without editing the pinned consumer.
- Initial repair/adversarial suite: 120 passed.
- Wider integration/guard suite: 280 passed, recorded in
  `D:/codex-preservation/perfume-chem-20260909/receipt-api-integration-20260909.xml`.
- Additional tests cover fabricated cached PASS/FAIL policies, changed scaling
  requests, explicit unrequested binding, and genuinely ABSTAINED stock receipts.
  The original Javanol 20% canary has a BOUND stock receipt; a separate mismatched
  10% regression fixture verifies ABSTAINED identity without authority promotion.
- Latest combined supplemental/repair run: **1120 passed, 2 failed**, 102.57s.
  This includes all 63 integration-extension test files plus seven focused
  repair/guard modules, deduplicated. JUnit:
  `D:/codex-preservation/perfume-chem-20260909/receipt-api-supplemental-final-20260909.xml`.
  Remaining failures are `test_repository_census_has_exactly_one_classification_per_finding`
  (three unclassified modules) and
  `test_live_cloud_registry_links_exactly_three_xhigh_openai_lanes`
  (missing historical collaboration registry). The native receipt adapter canary
  now passes. Counts from overlapping test runs are not added together.
- Scoped Ruff and `git diff --check` passed.
- `oav_authority.py` passes scoped mypy. Expanded scoped mypy on `gates.py` and
  `pre_mix_guard.py` reports 67 diagnostics; the clean-base checkout produces the
  exact same diagnostic sequence after removing line numbers. This is a failing
  pre-existing static-check scope, not a claimed whole-engine typecheck pass.
- One OpenAI-native worker independently reviewed the bounded diff read-only.
  Its test suggestions were implemented and checked by the parent; delegated
  review was not substituted for local execution.

## Exact changed source/test hashes

| Path | SHA256 |
|---|---|
| engine/pipeline/oav_authority.py | 834273eac7a37a224dd714605ca1d4dbb3857f4a934eb08938a4cfd17d5ee126 |
| engine/pipeline/gates.py | 67ba2483edda1d2d6779bb2ddc552ff4f34df4b74d8a2048f8816e7f9c073439 |
| engine/fuckups/pre_mix_guard.py | 88f69657c5cefd271928d9f4d4de9d76fb172528a1e1ad070a06e2fbc6414f67 |
| tests/test_oav_authority.py | e91c201719cc82f78fbed53ca115e6b4529641002c2c9cdb6fa656ffba3d4288 |
| tests/test_pre_mix_guard.py | 8acee332b4781f0cb6b2c2d61e234ce02b70982bad48c0c31463f330eb451f23 |

No full verifier rerun or release claim accompanies this bounded repair. Existing
scientific data gaps and historical registry/artifact mismatches remain open.
No commit, merge, push, publication, or production activation occurred.
