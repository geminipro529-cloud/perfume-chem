# Build C7 lot-aware natural-material gate

Decision: **PASS**

Evidence commit `be8f4509c4c2b37f5176bd2e3a8732bf29266e6e` replayed successfully at that exact commit.
C8 software work is open. C5 empirical status remains `BLOCKED_PENDING_DATA`:
no actual instrument or natural-lot dataset was added, and empirical promotion
is not allowed.

## Implemented authority

- Immutable lot identity covers botanical, chemotype or variety, plant part,
  origin, harvest or production date, extraction and processing, supplier
  product and lot, receipt/opening, storage, oxidation/stability, source
  documents, analytical runs, and authenticity state.
- All nine constituent bases remain explicit. Normalized area percent is not
  concentration and is never promoted by this contract.
- Exact-lot quantified, exact-lot relative, supplier batch, specific
  literature proxy, generic proxy, and unknown precedence is fail-closed.
- Unknown peaks, coelution, unresolved groups, unidentified GC-O events,
  below-quantitation items, and unassigned mass or area remain visible.
- Olfactory/headspace, regulatory/allergen, and identity/authenticity
  projections are separate and basis-preserving.
- Aging snapshots version state without changing lot identity.

## Exact-commit evidence

- The passing replay ran 24 jobs with zero failures, zero timeouts, and zero
  stderr bytes.
- C7 focused: 49 passed; complete root suite: 1,583 passed.
- C6/C5/C4/C3/C2/C1/C0 compatibility, dependency isolation, pip, Ruff,
  basedpyright, mypy, archive, scope, evidence, log hygiene, empirical-boundary,
  and protected-state checks all passed.
- All passing-attempt files are strict UTF-8, ANSI-free, and contain no
  credential-shaped matches.
- Protected database/WAL/SHM hashes and immutable database checks are unchanged.

## Replay transparency

Attempt 1 is preserved. Its only failed job requested a nonexistent pytest node
and exited 4 before running a test; the 1,583-test root suite in that same
attempt passed. The corrected exact node passed in isolation and in attempt 2.
No production failure is inferred from the selector error.

## DeepLuna Fast and Sol reconciliation

The C7 audit used DeepInfra Priority DeepSeek V4 Flash with `NO_LUNA`, one
provider call, no fallback, no scope deviation, and no negative findings. Sol
independently reproduced the gate-bearing behavior and accepted only locally
verified evidence. Provider findings remained advisory.

## Boundary

C8 is open for software work only. Actual natural-lot data, calibrated
composition claims, regulatory projection release, and empirical promotion
remain blocked until governed data and the applicable later gates pass.
