---
description: Guarded Phase C recovery resume (validates RESUME_GUARD_v1 before any queue)
agent: build
---

# PERFUME-RESUME — GUARDED PHASE C RECOVERY (hardened)

## 0. Guard validation (BEFORE anything else)
1. Locate `runs/CP6-20260805/phase_c/RESUME_GUARD_v1.json`. If absent -> STOP: RESUME BLOCKED (guard missing).
2. Compute its SHA-256 and compare against ALL of:
   - EMBEDDED EXPECTED HASH: `e1656ad35e6c3f2aad11a73f403798db2aff50a2d8af6e7e83bda75314deacf2`
   - `runs/CP6-20260805/phase_c/RESUME_GUARD_SHA256.json`
   - `runs/CP6-20260805/RESUME_GUARD_EXTERNAL_RECEIPT.json`
3. Confirm `run_id == "CP6-20260805"` and `mode == "PHASE_C_RECOVERY_ONLY"`. Any mismatch -> STOP: RESUME BLOCKED. Do NOT repair or normalize the guard automatically.

## 1. Recovery (from persisted files ONLY, no conversational memory)
- Recover run CP6-20260805 and the existing phase_c directory from disk.
- Do NOT rerun C0 or completed Phase C nodes (compare hashes against PHASE_C_SHA256SUMS_v2.json / _v3 ledger).
- Load the task graph from disk (CORRECTED_PHASE_C_TASK_GRAPH_v2.json). Recover the blocked state from PHASE_C_STATUS_v2.md.
- Verify the Phase A-B immutable snapshot unchanged (PREQUALIFICATION_SNAPSHOT.zip hash f9457996427bb61742e23a106fcff4ab183d7643124fa32920d9846c257d0e15) and all 18 formula fragments unchanged.

## 2. Allowed nodes (PHASE_C_RECOVERY_ONLY)
C11V3, C11Q-CHEAPLUNA-QUARANTINE-RECOVERY-VERIFY, C1V3-RUNTIME-CONFIG-LOCK, C4N-NATIVE-READ, C5N-NATIVE-WRITE, NATIVE-PERM, NATIVE-AUDIT, FALLBACK-AMENDMENT, PCV3-MANIFEST, PCG3-ARITHMETIC, CLDBG-01..07. REFUSE every node outside this list.

## 3. Hard refusals
- Refuse stale worker queues and superseded instructions (SUPERSEDED_INSTRUCTION_LEDGER.json): PIL revision relaunch, VER-*, AUD-01, PKG-01, formula Monte Carlo, ablation, perturbation, anti-collapse, formula audit, release packaging.
- Perform NO formula write and NO package write.
- `conversational_context_required` must be false.

## 4. First node after recovery
C11V3 (write 00_RESUME_TEST_v3.json/.md), then C11Q, then C1V3-RUNTIME-CONFIG-LOCK, then C4N/C5N etc.

## 5. Phase D/E/F guard recognition (added after Phase C fallback PASS)
- Locate `runs/CP6-20260805/phase_c/PHASE_DEF_EXECUTION_GUARD_v2.json`; compute SHA-256 and compare against:
  - PINNED DEF-GUARD HASH: `c1c701f9260cc0f87be6183abc7d30ca7a91d6460827428a49db99a37cb27e2e`
  - sidecar `PHASE_DEF_EXECUTION_GUARD_v2_SHA256.json`
  - external receipt `runs/CP6-20260805/PHASE_DEF_EXECUTION_GUARD_EXTERNAL_RECEIPT.json`
  - `00_RUNTIME_CONFIGURATION_LOCK_v4.json`
- Confirm mode PHASE_DEF_EXECUTION_ONLY and policy booleans (pilot_screen_design_writes true, final_perfume_formula_writes false, phase_artifact_packaging true, final_perfume_release_packaging false, cheapluna canonical false). Any mismatch -> STOP: DEF RESUME BLOCKED. Do not repair the guard automatically.
