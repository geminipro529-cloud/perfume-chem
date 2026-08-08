# b11 Authoritative Recovery — 2026-08-08

Batch of the perfume-chem recovery estate integrating the two user-downloaded packages:

| Package | Source ZIP (Downloads) | Canonical copy | Status |
|---|---|---|---|
| Module Recovery Audit 20260808 | `Perfume_Chem_Module_Recovery_Audit_20260808.zip` | `Perfume_Chem_Module_Recovery_Audit_20260808.zip` | INTEGRATED, 20/20 members hash-verified |
| Full Recovery Capture Kit 20260808 | `Perfume_Chem_Full_Recovery_Capture_Kit_20260808.zip` | `Perfume_Chem_Full_Recovery_Capture_Kit_20260808.zip` | INTEGRATED, 17/17 members hash-verified |

## Contents

- `Perfume_Chem_Module_Recovery_Audit_20260808.zip` — read-only audit of the 39 uploaded archive pile (23 unique byte sets), recovery verdicts, HOLDs, and P0 upload shortlist.
- `Perfume_Chem_Full_Recovery_Capture_Kit_20260808.zip` — forensic capture tooling (Downloads copy, Git forensics, credential quarantine, upload chunks) for the user's Windows machine.
- `verified-restore/module-recovery-audit/` — extracted audit package (RECOVERY_STATE.json, ZIP_INVENTORY, UPLOAD_AND_RECOVERY_SHORTLIST, SUPERSESSION_AND_AUTHORITY_RULES.md, etc.).
- `verified-restore/recovery-capture-kit/` — extracted kit (scripts, registers, validation, README_FIRST).
- `tunnel-forensics/` — read-only git estate capture of this repository at HEAD `a7bacff`:
  - `tunnel_status_porcelain_v2.txt`, `tunnel_index.patch` (79,687 B staged tools/), `tunnel_worktree.patch` (0 B — no unstaged edits),
  - `tunnel_reflog.txt`, `tunnel_branches.txt`, `tunnel_unreachable_objects.txt` (48,566 B),
  - `tunnel_stash_WIP_7e746221_full.patch` (17,851,120 B) — preserved WIP stash, NOT applied,
  - `tunnel_capture_sha256.json` — per-artifact SHA-256.

## Authority

No formula, inventory, physical-truth, or release mutations. Audit package authority statements (Inventory v5, MCV3, WAM V2, ACCORD final validation, SYNCED CrossBrand) remain advisory and are not re-promoted by this intake.

## Remaining recovery (from audit shortlist)

- **P0 — CLOSED** `PREQUALIFICATION_SNAPSHOT.zip` — the authentic snapshot EXISTS at `runs/CP6-20260805/corrective_plan_v6/CORRECTIVE_PLAN_APPROVAL_PACKET_v6.zip` (nested `PREQUALIFICATION_SNAPSHOT.zip`, SHA-256 `f9457996427bb61742e23a106fcff4ab183d7643124fa32920d9846c257d0e15`, 2,043,411 B byte-exact vs manifest, all 18 PIL fragments + SOURCE_HASHES verified). The audit's "absent" verdict covered only the uploaded Downloads pile.
- **P0** `FC-1_VALIDATED_EXTERNAL_CANDIDATE_*.zip` — upload for hash comparison.
- **P0 — DONE** Full Downloads + Git forensic capture — capture `PerfumeChem_Recovery_20260808_180024` (temp staging root; copy to a private external drive for preservation). 8 upload chunks, 14.39 GB, all-secrets quarantined.
- **P1** UNIVERSAL_ACCORD_INTELLIGENCE_MODULE_v1.zip, ACCORD estate harvest, PCV3 chat 1/2 packages, XHIGH post-freeze release, specialist packages, FC1 reconciliation bundle.

## Verification records

- `docs/verification/b11/logs/recovery_archive_check_audit.json` — PASS
- `docs/verification/b11/logs/recovery_archive_check_kit.json` — PASS
- `RECOVERY_INTAKE_MANIFEST.json` — canonical intake manifest with all hashes.
- `CAPTURE_VERIFICATION_FINAL.json` — final capture verification: **PASS** (167,632/167,632 manifest files hash-verified, 37/37 seal, 8/8 chunk CRC, 0 mismatches; PS verifier's 12,510 MAX_PATH false-positives re-verified via long-path Python verifier).
