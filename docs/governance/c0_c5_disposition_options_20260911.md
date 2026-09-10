# C0 / C5 disposition options — 2026-09-11

Provenance: drafted by gate lane `D:\chatbots\.gate-lanes-20260911\O-transition-docs`, a detached
worktree of the integration repository at `6a3d77e6` ("Fix the swallowed tuberose absolute fields and
the duplicate tuberose eo alias"). Draft target: `docs/governance/c0_c5_disposition_options_20260911.md`.
Inputs read: `docs/governance/verification_20260911_full_gate_classification.md` (committed at
`3e7f4eac`, body plus addendum) and `D:\chatbots\.gate-lanes-20260911\H-truthcore-triage\_lane_out\H-truthcore-triage.md`.
Every re-measurement below was run in this lane with
`D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe` (CPython 3.11.15); the lane was
read-only apart from `_lane_out/` and two gitignored runtime artifacts (§Facts). No release authority is
granted by this paper or by any lane of this gate.

## Decision

The repository owner chose **Option A — documented historical holds** on 2026-09-11. **Option B — versioned
re-derivation** is declined and recorded in full, with the trigger that would revive it.

## Option A — documented historical holds (CHOSEN)

Three test nodes stay red. They are listed here with the state measured in this lane at `6a3d77e6`
(`3 failed in 2.27 s`, reproduced in one pytest invocation):

| Test node | Assertion that fails | Measured state (this lane, `6a3d77e6`) |
|---|---|---|
| `tests/test_c0_physical_model_inventory.py::test_inventory_covers_every_c0_category_and_only_allowed_classes` | `assert errors == []` (`:44`) | `scripts/verify_c0_physical_model_inventory.py` returns exit 1, `status FAIL`, `error_count 63` — 35 `stale source hash`, 20 `call_edges[i]: token ... absent`, 8 `symbol/line drift` |
| `tests/test_c0_physical_model_inventory.py::test_legacy_fixture_lock_and_replay` | `assert errors == []` (`:196`) | same frozen-record errors; the fixture's own lock is intact (`e66c5e94217913db83487897079131dfef6e2e6d321ee4a7216e4c74302f89b8`). Replay of the 24 frozen cases: 23 identical, `C0-LH-005` divergent |
| `tests/test_c5_calibration_program.py::test_material_panel_matches_inventory_snapshot_and_required_domains` | `assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == C5_INVENTORY_SHA256` (`:362`) | working-tree `inventory.txt` = `28a71fda7af3549c09127f269892b393581053e29f2f824f273a2f654bc0c2ec`; pin = `9d778721db1f5a0a10d1f278eeef9b7fab0bc73ce7f0d58b26c501be70fe0eb8` |

Why the holds cost nothing and are already recorded:

- The C0 inventory record mixes three provenances in one pin table: 8 paths whose pin equals the LF `HEAD`
  blob while the checkout is CRLF (class B — repaired content-neutrally at `a32571c7` with `text eol=lf`
  and no pinned constant changed), and 11 paths pinned to an older commit, to live-uncommitted bytes, or
  to nothing reachable (classes C/D/E). The residual 63 messages are the un-repairable remainder plus the
  mechanically derivable line drift and call-edge tokens; editing them would edit a frozen authority.
- `C5_INVENTORY_SHA256` equals the 2026-08-05 inventory snapshot recorded in
  `data/pipeline_audit/events.jsonl`, and the inventory authority moved in `601d203c` (2026-09-10). The
  comparison hashes raw working-tree bytes, and `inventory.txt` carries no `eol` attribute. Re-binding a
  fail-closed calibration contract to a different inventory authority is a scientific decision.
- Both holds are evidence-complete in
  `docs/governance/verification_20260911_full_gate_classification.md` and in the lane H triage report;
  the differential effort for Option A is zero.

Compounding is not affected by these holds. `docs/verification/c0/physical_model_inventory.json` is read by
`scripts/verify_c0_physical_model_inventory.py`, `engine/project_verification.py`,
`tests/test_c0_physical_model_inventory.py` and dated `docs/verification/**` records only; searching
`scripts/formula_release_gate.py` and `engine/pipeline/**` for `calibration_program` / `C5_INVENTORY_SHA256`
returns no hits. The dose path binds to `inventory.txt` and the inventory stock contract instead — see the
`formula-dose-receipt-v1` receipt produced by the release gate, which carries `inventory_snapshot_sha256`
and its own `status`.

## Option B — versioned re-derivation (DECLINED, recorded with cost)

What it would take, in order:

1. **A freeze/successor generator, which does not exist.** Checked:
   `scripts/verify_c0_physical_model_inventory.py` exposes only `--inventory`, `--adr`, `--fixtures`,
   `--fixture-sha`, prints a JSON verdict to stdout and returns an exit code. It has no `--write` /
   `--freeze` mode and no code path that rewrites the pinned table, so the capability must be built first.
2. **Adjudicate `C0-LH-005` first.** It is the one genuine post-freeze behaviour change: ΔHvap fallback
   added (one fewer constituent, 9 → 8 modelled constituents) and the model now reports
   `literature_correlation:doi:10.1021/es980812j;fallback=60_kj_mol`; OAV moved
   `6789.897320595568 → 7906.955757087607`. A re-freeze that ignores this would freeze the change in
   silently.
3. **Produce C0 v2 and a C5 successor receipt bound to the current inventory**, with v1 kept immutable.
4. **Rebind the affected tests to v2** and re-run the truth-core and calibration checks.
5. **Record the successor decision** in governance, as an owner decision rather than a bookkeeping edit.

Estimated cost: **UNKNOWN** — no measured effort figure exists anywhere in the gate inputs. Structurally it
is five artifacts (generator capability, `C0-LH-005` adjudication, C0 v2 inventory, C5 successor receipt,
test rebind) plus a re-run; any hour figure would be invented.

Principal risk of Option B: baking a post-freeze behaviour change into the reference table, so that a
later reader treats today's model output as the frozen original. Option A keeps the divergence visible
instead of absorbing it.

**Revival trigger:** publishing, merging into canonical, or an external reader requiring a green gate.

## Facts, and what was not established

- Nothing outside `_lane_out/` was written except two gitignored runtime artifacts created by the
  documented commands used for verification: `data/perfumery_kb.db` (a regenerated knowledge base) and
  `data/_lane_o_kb_check.db`. No tracked file in the lane, the canonical checkout, or the main integration
  checkout was modified. A release-gate smoke run did append to `formulas/WM_Optimized_30mL_EDP.md` and
  `data/pipeline_audit/events.jsonl`; both were restored from `HEAD` and the lane is clean apart from
  `_lane_out/` (`git status --porcelain` → `?? _lane_out/`).
- The main-checkout quick gate result (`10 passed / 0 failed`) is taken from the classification record's
  addendum; it was not re-executed here.
- `C0-LH-005`'s divergent values are quoted from the lane H triage report and were not re-derived in this
  lane.
- No release authority is granted. The remaining red checks are recorded governance and scientific holds,
  not unexplained regressions.
