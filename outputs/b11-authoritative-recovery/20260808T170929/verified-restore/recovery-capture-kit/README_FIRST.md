# Perfume-Chem Full Recovery Capture Kit

## Do you need to copy the Downloads folder?

**Yes. Copy the complete Downloads folder once, before sorting, deleting, renaming, extracting, or moving anything.**

The purpose is not to dump Downloads into Git. The purpose is to preserve the original research estate so that old batches, revisions, failed builds, ZIP nesting, filenames, timestamps, and lineage can be recovered without guesswork.

The capture tool creates four distinct layers:

1. A forensic copy of Downloads with directory structure and timestamps preserved.
2. A forensic copy of the local `perfume-chem` repository plus Git state, patches, refs, stashes, reflog, worktrees, unreachable objects, and a full Git bundle.
3. A private local-only credential quarantine that is never staged for upload.
4. Sanitized upload ZIP chunks containing research candidates and recovery manifests.

It does not alter the original Downloads folder or repository.

## Before running

1. **Rotate any exposed API key now.** The screenshot showed a file named `openai-api-key`. Do not upload it. After rotation, keeping the old key has no research value.
2. Close Excel, VS Code, Codex, Git clients, archive managers, and programs currently writing files.
3. Connect a private external drive, or choose another protected drive with enough free space. A safe target is at least the combined size of Downloads and the repository, plus 30 percent.
4. Do not use OneDrive, Dropbox, Google Drive, or another automatically synchronized folder for the full private snapshot.
5. Keep the original Downloads folder unchanged until capture and verification both pass.

## Run

Double-click:

```text
RUN_RECOVERY_CAPTURE.cmd
```

The script asks for:

- destination directory;
- local `perfume-chem` repository path;
- any additional project folders, separated by semicolons.

Typical additional folders include:

```text
Desktop\Perfume*
Documents\Perfume*
local run directories
Codex worktrees
OpenCode output folders
old project export folders
```

## What to upload afterward

Upload **only** the ZIP files created in:

```text
07_UPLOAD_CHUNKS\
```

Do not upload:

```text
99_PRIVATE_LOCAL_ONLY_DO_NOT_UPLOAD\
```

The chunks exclude suspected credentials, dependency caches, installers, model binaries, and unrelated personal files. They retain all classified perfume research, formulas, workbooks, source files, patches, databases, images, reports, and ZIP packages.

## Verification

After capture completes, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\Verify-PerfumeChemRecovery.ps1 `
  -CaptureRoot "X:\path\to\PerfumeChem_Recovery_YYYYMMDD_HHMMSS"
```

A successful verification reports `PASS` and writes:

```text
04_MANIFESTS\VERIFICATION_REPORT.json
```

## Important preservation rule

Exact duplicate bytes may share a content hash, but every alias and original location remains in the manifests. Superseded batches are not deleted. They are retained as ancestry, negative evidence, alternate design hypotheses, or regression fixtures.

Current authority remains separate from preservation. Inventory v5 stays the stock and preparation authority, while older inventories and formulas remain historical provenance.
