# Capture Scope and Upload Policy

## Offline master capture

Preserve the complete source directories, including:

- all ZIP, 7z, and RAR packages;
- every formula workbook and CSV;
- all Markdown, JSON, schemas, ledgers, manifests, hashes, patches, and source code;
- screenshots and preview images;
- old, failed, superseded, and duplicate batches;
- Git metadata, uncommitted changes, stashes, reflog, worktrees, and unreachable-object reports.

## Private local-only material

The collector separates suspected credentials into a private local-only directory. It records path, size, timestamps, and SHA-256 but never includes the contents in upload staging.

Examples:

- `openai-api-key`;
- `.env`;
- API tokens;
- private keys;
- credential JSON files;
- password databases.

Rotate exposed credentials immediately.

## Upload staging

The upload tree includes research-bearing files and broad scientific/programming artifacts. It excludes:

- suspected secrets;
- `.git` object storage;
- package dependencies and caches;
- application installers;
- local language-model weights;
- unrelated personal files.

Exclusion from upload does not mean deletion from the offline master capture.

## Authority boundary

Preservation does not confer authority. The integration layer must retain:

- exact byte identity;
- source path and alias lineage;
- declared scope;
- evidence class;
- supersession relationship;
- target/inventory/build/bottle separation;
- physical-result and release boundaries.
