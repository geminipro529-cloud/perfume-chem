# Laboratory Beta Operations

## Release Boundary

The Laboratory Beta is an operational local-first formulation ledger. It is
ready for controlled personal laboratory use when its local verification,
migration, and backup gates pass. It is not a regulatory certificate and is not
a scientifically calibrated sensory predictor.

The software reports two separate outcomes:

- **Laboratory Beta:** code, typed data contracts, local integration tests,
  migration, and backup/restore verification.
- **Scientific Release:** all beta gates plus a preregistered held-out sensory
  evaluation that beats the declared baseline.

No blended score can hide a failed axis. Preference predictions remain
`UNKNOWN` until the minimum-data, graph-connectivity, and held-out gates pass.

## Start Safely

From `backend/`, install dependencies and run the backup-first migration:

```powershell
poetry install --with dev
poetry run python -c "from alembic.config import Config; from app.db_bootstrap import upgrade_database; print(upgrade_database(Config('alembic.ini')))"
poetry run uvicorn app.main:app --reload
```

Open `http://localhost:8000/app`. The interface is dependency-free and does not
load fonts, scripts, or styles from a CDN.

For an existing file-backed SQLite database, the migration helper first checks
whether a migration is pending. Only when one is, it:

1. runs `PRAGMA integrity_check` on the source;
2. creates a consistent SQLite backup and SHA-256 manifest;
3. records the pre-upgrade schema fingerprint; and
4. runs the frozen Alembic migration only after the snapshot succeeds.

A database already at the current schema, and an empty or not-yet-created
database, get no pre-upgrade snapshot. Snapshots go in `pre-upgrade-snapshots/`
beside the database. On each start the helper deletes old ones, keeping the 5
newest and any younger than 30 days.

## Canonical Records

- Materials and stock solutions identify active fraction and fraction basis.
- Formula versions are immutable and sequential per formula.
- Bottle events, effects, and inventory movements are append-only.
- One command ID cannot be reused with a different request payload.
- Bottle and stock mass changes are committed atomically.
- Corrections are one-time compensating events linked to the original event.
- Experiments preserve blind codes, application time and dose, timed
  observations, pairwise choices, model version, evidence ID, and outcome.
- Datetimes are normalized to UTC at the database boundary.

The portable workspace export preserves stable UUIDs, dependency order, units,
and provenance. Re-importing the same packet is idempotent; a UUID with
different content is rejected as a conflict.

## Backup And Recovery

Use the application backup endpoint or the **Backup & Export** view to create a
snapshot. A valid restore candidate must remain inside the managed backup
directory and pass all of these checks:

- SQLite integrity;
- snapshot SHA-256 against its manifest;
- schema fingerprint against its manifest; and
- exact application schema revision.

The HTTP API validates and stages a restore but never replaces the live
database. After staging, the page shows the exact command that finishes the
restore. To apply it:

1. stop the app (close the window running `python run_api_server.py`);
2. from the repository root, run
   `python run_api_server.py --restore <backup>`, where `<backup>` is the
   backup's file name as the app shows it (for example
   `lab-manual-20261008T101500000000Z-ab12cd34.sqlite`) or a path to the backup
   file inside the managed backup directory; and
3. start the app again and run the health and laboratory smoke tests.

The command restores and exits without starting the server. It:

- validates the backup with the same checks as above and refuses a missing or
  damaged backup;
- refuses, changing nothing, while the app still answers on
  `127.0.0.1:8000` or another program holds a lock on the database;
- takes a fresh pre-restore backup of the live database, then atomically
  replaces it and checks the restored database;
- prints where the pre-restore backup is and the command that undoes the
  restore (`python run_api_server.py --restore <pre-restore backup name>`); and
- removes its staged copy. Staging a new restore from the app also removes
  earlier staged copies (`.<database name>-restore-stage-*.sqlite` beside the
  database).

Never delete the pre-restore backup until the recovered workspace has been
inspected.

## Scientific Truth Boundary

- Exact: stated mass balance, unit conversion when required inputs exist,
  event replay, stock balance, hashes, and persisted records.
- Literature-derived: sourced material properties and restrictions with an
  explicit source/version.
- Heuristic: uncalibrated headspace and temporal models.
- Unknown: missing density/matrix/constituent/restriction evidence and any
  sensory claim that has not passed its declared empirical gate.

Natural-mixture composite OAV supports olfactory headspace analysis only. It is
not constituent composition for IFRA assessment. An opaque natural with missing
constituent evidence must remain `unverified`, never silently pass.
If disclosed evidence already proves a category limit exceedance, the result is
`fail` even when other constituents remain unresolved; missing evidence cannot
reverse a known violation or turn it into a pass.

## Verification

From the repository root:

```powershell
python -m pytest tests -q
python scripts/pipeline_audit.py project-verify --json
```

From `backend/`:

```powershell
poetry run ruff check app
poetry run mypy app --ignore-missing-imports
poetry run pytest --cov=app --cov-report=term
```

Treat `PASS_WITH_SKIPS` as a limitation report, not as evidence that skipped
infrastructure ran. Held-out sensory work retains its own status.
