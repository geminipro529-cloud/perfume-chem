# A0 restoration instructions - capture 20260801_011431

These instructions restore the exact source state used for the A0 gate. The large archives are intentionally outside Git under `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work`.

## Authority files

| File | SHA-256 |
|---|---|
| `a0_repository_all_refs_20260801_011431.bundle` | `4d10101200fa321a1f44923f989c62ec35814fcc6ab8100d8b1504dfa89506ef` |
| `a0_complete_source_state_20260801_011431.tar` | `4b1a4c325d1d69c5d54535b6ad14acda9872698c8bf00f9847753c0bdadb223b` |
| `a0_complete_source_state_20260801_011431_manifest.json` | `8e05bf58670d2bdb452c16961e0c78cb8b270d5479274463294535111e2f606a` |
| `a0_formula_artifacts_20260801_011431.tar` | `e58681bf79e34677d17c341d08701d9444dc2e3ac52c7e793eab7c5bb5b2772c` |
| `a0_formula_artifact_manifest_20260801_011431.json` | `e85d4f6018c75e50368d9a3916d5c09583b089720913181b47b03c400e8e3c53` |
| `a0_complete_source_state_20260801_011431_final_verification.json` | `30aad3115b59a8b64268e2ba7cc59a22eebc01a908a7a7772dbd01119924e762` |

The complete source archive contains all 3,429 tracked paths and all 937 non-ignored untracked paths. It excludes ignored files, including `.env`, virtual environments, caches, and generated output. The separate formula archive adds all 535 formula and fixture artifacts, including seven ignored PNG/CSV artifacts.

## Restore into a new directory

Do not overlay an existing repository. Choose a new short Windows path to avoid path-length failures.

```powershell
$evidence = 'C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work'
$restore = 'C:\A0_RESTORE_NEW'
Get-FileHash -Algorithm SHA256 -LiteralPath "$evidence\a0_repository_all_refs_20260801_011431.bundle"
Get-FileHash -Algorithm SHA256 -LiteralPath "$evidence\a0_complete_source_state_20260801_011431.tar"
git -c core.longpaths=true clone --no-checkout "$evidence\a0_repository_all_refs_20260801_011431.bundle" $restore
git -C $restore config core.longpaths true
git -C $restore checkout codex/add-inventory-materials
py -V:Astral/CPython3.11.15 -m tarfile -e "$evidence\a0_complete_source_state_20260801_011431.tar" $restore
```

The proven restore is retained at `C:\A0S_full_20260801_011431`. Its HEAD is `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435`, all 4,366 source hashes match, tracked and untracked path lists match, and byte-captured `git diff --binary --full-index` has the same SHA-256 as the source.

Because global `core.autocrlf=true` can make a clean clone revalidate LF worktree files, do not use raw `git status` count equality as the only restoration test. Use the manifest hashes and semantic diff digest recorded in the final verification report.

## Formula artifacts

The complete source archive contains 528 of the 535 formula/fixture artifacts. Restore the seven ignored artifacts, or the whole artifact set, from the dedicated archive:

```powershell
py -V:Astral/CPython3.11.15 -m tarfile -e "$evidence\a0_formula_artifacts_20260801_011431.tar" $restore
```

The proven artifact extraction at `C:\A0F_20260801_011431` has 535 members and zero hash mismatches.

## Databases

Transaction-consistent SQLite backups are under `a0_database_backups_20260801_011431`. Their machine report is `a0_database_backup_20260801_011431_verification.json` with SHA-256 `02597d94e02299d2f2f3fa772dabec0b2ba10f5106d04b03a57d9f16c9e8f4ce`.

Do not overwrite an active database. Close the application, validate the candidate with `BackupService.validate_restore`, stage it with `BackupService.stage_restore`, and only then perform an explicitly authorized replacement. A0 did not perform a restore or migration.

## Secret boundary

Secret-bearing ignored files were intentionally not opened or included. Restore credentials separately through the project's protected environment mechanism. Never commit `.env` or provider credentials.
