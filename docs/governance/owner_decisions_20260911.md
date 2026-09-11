# Owner decisions — C5 inventory pin and backend corpus baseline

Date: 2026-09-11. Scope: the two decisions the session handoff listed as open.
This record grants no release authority; it documents facts and the options so the
owner can decide. Do not edit any frozen store from this document.

## 1. C5 inventory pin — DECIDED (documented hold), re-confirmed here

Decision already recorded by the owner in
`docs/governance/c0_c5_disposition_options_20260911.md`: **Option A — documented
historical holds** (Option B, versioned re-derivation, declined).

| Item | Value |
|---|---|
| Pin (`engine/physics/calibration_program.py:23`) | `9d778721db1f5a0a10d1f278eeef9b7fab0bc73ce7f0d58b26c501be70fe0eb8` (2026-08-05 snapshot) |
| Inventory measured at `6a3d77e6` (decision doc) | `28a71fda7af3549c09127f269892b393581053e29f2f824f273a2f654bc0c2ec` |
| Current `inventory.txt` (this record) | `270a47be538694b72ffcfb3806e0874ce5cc9b8fcf0a2111247dac7e0c0b2d24` |
| Failing node | `tests/test_c5_calibration_program.py::test_material_panel_matches_inventory_snapshot_and_required_domains` |
| Compounding impact | none (no `calibration_program` / `C5_INVENTORY_SHA256` references under `engine/pipeline/**` or `scripts/formula_release_gate.py`) |

Status: **hold stands**. The inventory authority has moved again since the
decision doc (28a71fda → 270a47be); the pin remains the 2026-08-05 snapshot.
Re-binding a fail-closed calibration contract to a different inventory authority
is a scientific decision and requires a C5 successor receipt with owner
sign-off, not a bookkeeping edit.

## 2. Backend corpus baseline (`test_b4_legacy_rule_adapter`) — HOLD, options below

Frozen baseline: `backend/tests/fixtures/b4_identity_resolution_baseline.json`
(`source_corpus_sha256`). Current files re-hashed in this record.

| Source file | Frozen | Current | State |
|---|---|---|---|
| `data/knowledge_graph/theory_rules.json` | `4237619f7fdddbfc15b373c42f40e2d30fc587537ac8f782b2111d6f61f53b90` | `77fb606a4cfaeb0dec48872931e744e82e6e321d8020dcc2358fcd744198d56d` | drift |
| `data/knowledge_graph/synergy_matrix.json` | `7b194c2f7ea19efcfbcc1bafef5e4c0dfdcac69739dff5720b1c91fe0b7d7b9d` | `951614cb91569a928410ed306f684b1e86b282a565c3b6549d5b71b0cb668d80` | drift |
| `data/knowledge_graph/pairing_rules.json` | `fc4370b8017334e070b873463bcec1db8cd781b156db214a8b1c0382483cf8d1` | `a102eeafe05cbbc68436c490acffa1fa44e3e68e2f5bd42b543e1a266dc22dda` | drift |
| `data/knowledge_graph/pairing_rules_discovered.json` | `2dd23d496cda1b6dbd61ff147f977d4bbb7d919048b591e018785ba0bde9e044` | `5c15f7c0f4f66ef320905dff81178a92882cda0f6605fdef8185564d9454b325` | drift |

Failing node: `backend/tests/unit/test_b4_legacy_rule_adapter.py`
(also classified `IDENTITY_SNAPSHOT["source_corpus_sha256"] differs` in
`docs/governance/verification_20260911_full_gate_classification.md:176`,
already labelled a documented hold).

### Options

- **A — Documented hold (recommended).** Leave the frozen baseline immutable;
  keep the node red with this record as evidence. Zero effort, preserves the
  ability to detect accidental corpus edits.
- **B — Versioned successor re-baseline.** Add a v2 baseline with a successor
  receipt; rebind the test. Requires a **semantic review** of what changed in
  the four rule corpora (new/removed/edited rules), because a hash cannot say
  whether the change is a correction or a regression.
- **C — Restore the frozen corpus.** Revert the four files to the bytes the
  frozen baseline describes. Only valid if the post-freeze edits are known to
  be invalid.

Acceptance criteria for B (do not start without 1–3):

1. Semantic diff of the four corpora reviewed and recorded (added/removed/
   changed rules, with rationale per corpus).
2. Successor receipt binding `superseded_sha256 → successor_sha256` per file,
   `approved_by`, `approved_at`, and the evidence reference.
3. Test rebound to the v2 baseline with the v1 fixture preserved byte-for-byte.

Recommendation: **Option A for now**, matching the C5 hold, until a semantic
review is scheduled.
