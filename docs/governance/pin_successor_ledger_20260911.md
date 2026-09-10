# Pin successor ledger — 2026-09-11

## What this records

The complexity registry's frozen V1 file (`configs/complexity/complexity_module_registry_v1.json`)
stores a SHA-256 per module. Every red test node in the 2026-09-11 full-gate characterisation traced
to one of those pins, or to a pin of the same shape in another store, describing bytes that had
legitimately moved. Until this change there was no mechanism to move a pin forward: the overlay
schema accepted only additions of unvalidated candidates, so the only options were to leave the gate
red or to hand-edit frozen evidence.

This ledger accompanies the first such mechanism. **The frozen V1 registry is unchanged, byte for
byte** — `test_current_overlay_preserves_exact_frozen_registry` continues to assert its SHA-256 as
`7567f3ca00ccbf3e1b2b41f50645ed21f4d163612872b8449db6cc022818c639`. A pin moves only through a
successor record that names the exact value it supersedes.

## Why the pins had drifted

Two independent causes were measured, and they are not the same thing:

1. **Un-normalised pin generation (3 modules + 3 overlay additions).** The pin equals the CRLF form
   of the current bytes. The source content never changed: the pin was computed from a checkout
   materialised by `core.autocrlf=true`, while the committed representation is LF. These pins passed
   only by accident, and would fail in any freshly cloned or re-normalised checkout.
2. **A real post-freeze revision (1 module).** `engine/temporal_graph.py` changed in `8916c30b`
   ("Add explicit numeric character evidence contract"). Its pin equals neither the LF nor the CRLF
   form of the current bytes, so it describes a previous revision rather than an EOL artefact.

## The successor mechanism

`engine/perception/complexity_registry.py` accepts an optional `module_successors` list on the
overlay. Each record is closed to exactly these fields:

`module_id`, `path`, `superseded_sha256`, `successor_sha256`, `commit`, `reason`, `evidence`,
`approved_by`, `approved_at`.

A record is rejected unless: the module exists in the frozen V1 file; the declared `path` matches the
frozen row; `superseded_sha256` equals the frozen pin exactly (the anchor); `successor_sha256` is a
well-formed digest that actually differs; `commit` is a full 40-hex commit; a non-blank reason,
approver and date are present; and `evidence` resolves to a real file inside the repository. The
unknown key `module_overrides` remains rejected — `tests/test_complexity_registry.py` pins that
behaviour.

The anchor is the point of the design: a successor that does not describe the frozen value is a
mistake, not an override, and it fails to load rather than silently rebinding.

## Re-bindings applied

| Module | Path | Superseded pin | Successor pin | Commit | Cause |
|---|---|---|---|---|---|
| `temporal-graph-future` | `engine/temporal_graph.py` | `9b2b72f5…` | `4f655236…` | `8916c30b` | post-freeze revision; superseded digest not reproducible (see below) |
| `temporal-volatility-future` | `engine/temporal_volatility.py` | `a7411771…` | `89b23e97…` | `4f7a7bab` | EOL only |
| `hedonic-model-future` | `engine/hedonic_model.py` | `c5a25a93…` | `7d5c8d6b…` | `4f7a7bab` | EOL only |
| `advanced-musk-intelligence` | `future_modules/advanced_musk_intelligence.py` | `28745ddb…` | `cc0c789b…` | `4f7a7bab` | EOL only |

The three overlay *additions* (`formulation-intelligence-*`) carried the same CRLF-derived defect.
They are additions, not frozen V1 rows, so their digests were corrected in place in the overlay
itself rather than through a successor record.

`/engine*` paths gained `text eol=lf` in the same change (`4f7a7bab`), so a fresh checkout can no
longer reproduce the CRLF form. That commit also normalised the working copies of 42 raw-byte-pinned
paths; every rewrite was content-neutral, and staging after it showed only `.gitattributes` changed.

## What this does not do

## Anchor reproducibility — a rule this change establishes

An independent audit asked whether each superseded digest matches *any*
committed revision of its path, on any ref. The answer matters because a
successor record that says "the frozen pin describes a previous revision" is
making a claim about history, and that claim must be checkable.

Measured for the C0 store's 35 `(path, digest)` pairs:

- **8** still match the current bytes — nothing to move.
- **27** drift, and **none of the 27 matches any committed revision** of its
  path (`git rev-list --all -- <path>` plus `cat-file blob` per revision,
  compared raw and LF-normalised).
- Of those 27, **16 match the CRLF materialisation of the current blob** — the
  content never changed, only the representation a Windows checkout produced.
  These are explained, and provably safe to re-bind.
- The remaining **11 match nothing reachable at all**: not the current bytes,
  not their LF or CRLF form, not any committed revision. Their provenance
  cannot be established from this repository.

**Rule R1 — a successor record may only be issued when the superseded digest is
reproducible**: it must equal either the current bytes or a committed revision
of that path. A digest that matches nothing is not "stale"; it is unauditable,
and the honest instrument is an owner re-baseline receipt that says so, not a
successor that implies continuity.

**Rule R2 — a successor must never encode a CRLF preference.** The committed
representation is LF. Re-binding to a CRLF-form digest would preserve the
defect this work exists to remove.

The `temporal-graph-future` record above is therefore worded as a re-baseline
rather than a continuity claim: its superseded digest is one of the
unreproducible ones, and the record says so.

- It does not touch `configs/complexity/complexity_module_registry_v1.json`.
- It grants no execution, admission, promotion or release authority. Every module state is unchanged:
  the additions remain `FUTURE_CANDIDATE_NOT_VALIDATED` with `import_path: null`.
- It does not re-bind any pin in `docs/verification/c0/physical_model_inventory.json`, the C5
  calibration constant, or the backend corpus snapshot. Those stores need the same treatment and are
  recorded as open work.
- It does not decide `C0-LH-005`, where the model genuinely diverged after the freeze
  (ΔHvap fallback, 9 → 8 modelled constituents, OAV 6789.897320595568 → 7906.955757087607).

## C0 successor overlay — applied 2026-09-11

The C0 stores received the same mechanism in
`scripts/verify_c0_physical_model_inventory.py`, through two optional overlays:

- `docs/verification/c0/physical_model_inventory_successors.json` (the 48-record inventory);
- `tests/fixtures/c0_legacy_physical_model_cases_successors.json` (the 24-case legacy fixture set).

Each record is closed to `record_id`, `target`, `superseded_sha256`, `successor_sha256`, `kind`,
`commit`, `reason`, `evidence`, `approved_by`, `approved_at`. The frozen stores are unchanged; a
record is rejected unless its anchor equals the stored pin, its successor equals the current LF
digest, and — for `eol_only` — the superseded digest is provably the CRLF materialisation of the
current LF bytes. Owner re-baselines carry no continuity claim by design (R1).

Measured effect on `scripts/verify_c0_physical_model_inventory.py`: **103 errors → 49**.
47 pins were re-bound across the two stores:

| Store | EOL-only | Committed-revision | Re-bound |
|---|---|---|---|
| C0 inventory (`C0-PM-*`) | 19 | 6 | 25 |
| C0 legacy fixtures (`C0-LH-*`) | 15 | 7 | 22 |

Still open, with measured counts:

1. **21 owner re-baseline rows (7 distinct paths).** The superseded digests are not reproducible as
   successors under R1. Affected paths: `engine/pipeline/simulator.py`, `engine/thermo/antoine.py`
   (7 rows), `engine/diffusion_model.py`, `engine/optimizer/scoring.py` (4 rows),
   `engine/pipeline/oav_intelligence.py`, `engine/workbench.py`, `engine/calibration.py`. These need
   an owner re-baseline receipt, not a successor.
2. **8 symbol/line drifts and 20 call-edge tokens.** Metadata describing where code moved; each
   needs a human read of the new location. One edge was corrected in this change because the
   verifier edit itself moved it (`call_edges[22]`,
   `scripts/verify_c0_physical_model_inventory.py:594 → 772`).
3. **`C0-LH-005` replay divergence** (the ΔHvap behaviour change) remains an owner decision.

One consequence worth recording: adding the successor mechanism to the verifier shifted a line that
a C0 call edge pins, and the verifier failed honest rather than passing stale. That is the intended
behaviour — but it is also why the remaining symbol/line and call-edge metadata is deferred to a
deliberate human pass instead of an automatic rewrite.

## C0 re-baseline and C0-LH-005 freeze — owner decision 2026-09-11

The repository owner approved two decisions on 2026-09-11.

**1. 21 owner re-baseline receipts** (7 distinct paths). The superseded
digests match no reachable revision, LF or CRLF form (rule R1), so these are recorded as
`owner_rebaseline` successors with no continuity claim. Paths: `engine/calibration.py`, `engine/diffusion_model.py`, `engine/optimizer/scoring.py`, `engine/pipeline/oav_intelligence.py`, `engine/pipeline/simulator.py`, `engine/thermo/antoine.py`, `engine/workbench.py`.

**2. `C0-LH-005` frozen as C0 v2.** The post-migration dHvap fallback models one fewer
constituent (9 -> 8) and moves OAV 6789.897320595568 -> 7906.955757087607; 23 of 24 frozen
cases replay identically. The owner accepted the new behaviour into the frozen fixture store
rather than reverting the migration. The case carries a `c0_v2_freeze` receipt and the fixture
lock was regenerated.
