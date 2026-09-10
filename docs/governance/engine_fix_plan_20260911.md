# Engine fix plan — 2026-09-11

Status: first two workstreams landed locally (see §1). Everything below is
measured in `D:\chatbots\perfume-chem-integration-20260909` at `31d7f392`.
No release authority is granted by this document.

## 1. What landed

| Commit | Change |
|---|---|
| `4f7a7bab` | `text eol=lf` for every raw-byte-pinned path (42 text + 1 binary `-text`); 40 working copies renormalised CRLF→LF, all content-neutral (staging showed only `.gitattributes` changed) |
| `e26ae430` | Anchored `module_successors` on the complexity overlay + `docs/governance/pin_successor_ledger_20260911.md` |
| `31d7f392` | `tests/test_verification_invariants.py` (pinned-path EOL stability + engine shard coverage), assigned to the `truth-core` shard |

Quick gate: **10 passed / 0 failed** after each commit.

Measured effect: **two red test nodes closed** —
`test_complexity_benchmark_census_json` (legacy) and
`test_repository_census_has_exactly_one_classification_per_finding` (extensions).
`tests/test_complexity_registry.py` is 29 passed; the frozen V1 registry is
still byte-identical (`7567f3ca…`).

Lane L1's census drove this: 326 pinned rows across ~25 stores — 247 match,
3 LF-only, 75 content drift, 1 unreachable — and 42 text paths with no
`eol=lf` attribute.

## 2. The structural finding

The red set is not five bugs. It is one defect with a dependency the earlier
run could not see:

1. Pins in several stores were generated from an **un-normalised checkout**
   while the committed representation is LF. They pass only on a CRLF
   workstation.
2. There was **no mechanism to move a pin forward**, so a legitimate change to
   a pinned module produced a permanent red.

**Track 2 cannot be done before Track 1.** Adding `eol=lf` is what exposes the
wrong pins: in the C0 store, 0 pins are LF-based, 16 are CRLF-derived
(content unchanged, pin wrong) and 11 are genuine content drift. The C0
validator's error count rose 63 → 103 for exactly that reason — 16 paths that
had been passing by accident. The three C0/C5 test nodes themselves are
unchanged; the report is simply truer.

## 3. Remaining red set

| Store | Node | Root cause | Fix |
|---|---|---|---|
| C0 inventory | `test_inventory_covers_every_c0_category_and_only_allowed_classes` | 27 paths: 16 CRLF-derived pins, 11 content drift; plus 8 symbol/line drift and 20 call-edge tokens | successor overlay (see §4) |
| C0 fixtures | `test_legacy_fixture_lock_and_replay` | same, plus `C0-LH-005` replay divergence | successor overlay + owner call on §5 |
| C5 calibration | `test_material_panel_matches_inventory_snapshot_and_required_domains` | `C5_INVENTORY_SHA256` = the 2026-08-05 snapshot; `inventory.txt` moved in `601d203c` | owner decision (§5) |
| Backend corpus | `test_b4_legacy_rule_adapter` | frozen `source_corpus_sha256` vs current `synergy_matrix.json`, `theory_rules.json` | same successor pattern |
| Docker | `docker-build`, `docker-smoke-test` | no Docker CLI on this host | environment |

## 4. C0 successor overlay (next implementation)

Mirror the registry mechanism, in `scripts/verify_c0_physical_model_inventory.py`:

- Optional `docs/verification/c0/physical_model_inventory_successors.json`,
  anchored per `(record_id, target)`; the anchor must equal the stored value,
  or the verifier refuses to load.
- Re-bind the 27 hash pins: 16 declared EOL-only (provable), 11 declared as
  owner re-baselines (see the reproducibility rule below).
- **Do not auto-rewrite the 8 symbol/line drifts or 20 call-edge tokens.**
  Those describe where code moved; each needs a human read of the new
  location. They are mechanical but not automatic.
- Keep `tests/fixtures/c0_legacy_physical_model_cases.json` separate: it has
  its own 17 drifting rows and its own validator.

### Reproducibility rule (measured, apply before any C0 re-bind)

Every superseded digest must be reproducible, or the record must say it is not.
Measured for C0's 35 `(path, digest)` pairs: 8 still match the current bytes;
27 drift and **none of the 27 matches any committed revision on any ref**;
16 of those 27 match the CRLF materialisation of the current blob (content
unchanged, provably safe to re-bind); the other **11 match nothing reachable** —
not the current bytes, not their LF or CRLF form, not any revision. Those 11
need an owner re-baseline receipt, not a successor that implies continuity.

Two rules follow: **R1** a successor may only be issued when the superseded
digest equals the current bytes or a committed revision; **R2** a successor must
never encode a CRLF preference, because the committed representation is LF.

## 5. Decisions the owner has to make

1. **`C0-LH-005`** — the ΔHvap fallback genuinely changed model behaviour
   (9 → 8 modelled constituents, OAV `6789.897320595568` → `7906.955757087607`;
   23 of 24 frozen cases replay identically). Freeze the new behaviour into a
   C0 successor, or treat it as a defect and revert. Nothing else in the red
   set is a behaviour question.
2. **C5** — re-binding the calibration constant to the current `inventory.txt`
   authority asserts that the calibration panel still applies to the newer
   inventory. That is a scientific claim, not bookkeeping.
3. **Backend corpus baseline** — re-baseline `synergy_matrix.json` /
   `theory_rules.json`, or restore the corpus the frozen baseline describes.

## 6. Environment

Docker CLI is absent. Closing `docker-build` / `docker-smoke-test` needs
Docker Desktop with a WSL2 backend, then the two verifier checks; until then
they stay `NOT TESTED` and must never be reported as passing.

## 7. The other half — the engine's science

Green tests do not make the engine good. Current coverage, from the gate's own
report: Antoine 0%, HSP 0%, OR targets 0%, ΔHvap 0.16%, SMILES 1.2%, IFRA 1.1%,
Trp 3.9%, ODT-air 7.8%, hedonic 10.8%, logP 17.2%, VP 23.1%, MW 23.3%. ODT
evidence is 108 UNVERIFIED, 90 DERIVED, 72 PEER_SINGLE, 14 PEER_EST,
14 multi-source, 1 peer-crossed. Temporal evolution is heuristic and
uncalibrated to skin or blotter; longevity, sillage, receptor activation and
emotion outputs are unsupported, and held-out sensory validation is the
standing external blocker.

Ordering matters: expand data only after the pin machinery is complete.
Otherwise every data update re-reds the gate, which is how the previous run
ended with documented holds instead of a working update path.
