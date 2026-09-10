# Perfume-Chem V19/V20 Gap-Closure Report

**Candidate:** `PERFUME_CHEM_V20_GAP_CLOSURE_CANDIDATE_2026-08-17`  
**Result:** `PASS_STANDALONE_CANDIDATE__REPOSITORY_AND_EVIDENCE_HOLDS_PRESERVED`  
**Repository:** `BRIDGE_BLOCKED`  
**Install/deploy:** `NOT PERFORMED`

## 1. Executive decision

The previously identified gaps have been split into two categories:

1. **Executable contract gaps**, which can be closed safely in a standalone candidate with deterministic tests.
2. **Evidence, exact-byte, and repository gaps**, which must remain `HOLD` or `BRIDGE_BLOCKED` because they require source bytes, physical stock evidence, or a verified local checkout.

The package closes the first category. It does not relabel the second category as complete.

The current candidate compiles and passes **76 of 76** unit and regression tests. It also replays five Meaningful Complexity V3 fixtures with the expected class and state, while reporting `G14` as `NON_GOVERNING`. The old Qualification v1 package remains unchanged and quarantined at 15/16. Its current-policy adapter now shows that the EQ-02 mismatch disappears only when the obsolete aggregate G14 expectation is excluded from current authority.

## 2. Gap-by-gap closure

### V20-VAL-004: legacy V2 policy conflict isolation

**Candidate state:** `CLOSED_STANDALONE`

Implemented in `complexity_dispatch.py`:

- a 49-row formula cannot fail solely for having 49 rows;
- a padded 65-row formula cannot pass solely for having 65 rows;
- `quality_score` is retained only as non-governing legacy metadata;
- V2 payloads round-trip without entering current decision logic;
- a missing V3 policy returns `HOLD_CURRENT_POLICY_UNAVAILABLE` and never falls back to V2;
- an authoritative target-specific identity floor remains enforceable separately;
- compact and layered declared scopes are not silently relabeled upward;
- physical and hedonic claims remain capped by evidence.

The exact V3 classification rules and test cases are preserved under `reference/meaningful_complexity_v3/`.

### V20-VAL-005: legacy Qualification v1 mismatch

**Candidate state:** `CLOSED_CURRENT_POLICY_ADAPTER_SCOPE`  
**Legacy package state:** `FAIL_15_OF_16__QUARANTINED`

Implemented in `qualification_adapter.py`:

- raw legacy fixtures and results remain unchanged;
- G14 is marked non-governing only in the current-policy view;
- EQ-02 expected and observed failure sets become identical after excluding G14;
- EQ-16's quality-score-only failure produces no current-policy gate failure;
- no current PASS or release is inferred;
- the target Perfume-Chem engine remains `NOT RUN` in this packet.

This closes the adapter defect without falsifying the historical 15/16 result.

### V20-VAL-006: formula-artifact validation blocker

**Candidate state:** `DIAGNOSIS_CLOSED__REPAIR_ENGINE_VALIDATED__ACTUAL_SUCCESSOR_HELD`

The later revalidation evidence resolves the old diagnostic uncertainty. The structural defect is a derived dose-export residual in six formulas:

| Perfume | Residual µL |
|---|---:|
| DHP25 | -0.0007 |
| AHS | -0.0012 |
| ELIXIR | -0.0001 |
| LHOMME | -0.0018 |
| LANUIT | -0.0002 |
| BDCP | +0.0001 |

`formula_artifact.py` now:

- recomputes every derived dose from canonical Decimal `parts_per_1000`;
- requires canonical parts to total exactly `1000`;
- closes exact and display totals deterministically;
- records any display-rounding adjustment explicitly on a declared balance line;
- preserves canonical formula parts unchanged;
- gives the successor export a new hash linked to its parent;
- validates canonical content, analysis input, renderer, generated analysis, source, and parent bindings;
- blocks blind commit, stash, reset, regeneration, and rebind.

A synthetic regression export closes exactly. The six actual successor exports were **not** created because the exact parent formula rows are not materialized in this runtime. They must not be reconstructed from signatures or prose.

### V20-VAL-007: operation-scoped quarantine

**Candidate state:** `CLOSED_STANDALONE`

`source_admission.py` allows only:

- `VERIFY_BYTES` when exact bytes are present;
- bounded `READ_MANIFEST_FOR_QUARANTINE` when policy permits.

For unresolved source rights it denies:

- module, schema, registry, formula, and evidence-ledger imports;
- execution;
- promotion.

A matching SHA-256 cannot bypass source rights. The Floral Heart and Complexity Discovery parents remain quarantined and unused.

### V20-VAL-008: exact-byte dependency behavior

**Candidate state:** `GUARD_CLOSED__BYTE_HOLDS_REMAIN`

`exact_bytes.py` verifies:

- exact filename;
- byte size;
- SHA-256;
- ZIP/WHL validity and CRC;
- member count where known;
- no unsafe paths, symlinks, duplicate paths, or case-fold collisions;
- explicit rejection of the stale Universal Accord `8a9c...` variant.

The four original byte streams remain unavailable. The correct state therefore remains `HOLD_EXACT_BYTES_UNAVAILABLE`, not compatible-substitute acceptance.

### V20-VAL-009: exact stock and dose contract

**Candidate state:** `CLOSED_STANDALONE`  
**Evidence state:** `63 ROWS STILL HOLD`

`exact_quantities.py` proves:

- missing stock strength remains null and cannot become neat;
- an unknown carrier remains unknown;
- opaque product basis remains non-decomposed;
- mass fraction, volume fraction, and mole fraction remain distinct;
- cross-basis conversion requires conditioned, authoritative density evidence;
- planned acquisition and procurement pending cannot become physically owned;
- preparable does not mean prepared;
- physical execution requires an `ExactStockRef`;
- binary float input is rejected at the authority boundary;
- screening output cannot become physical, sensory, strict-OAV, or release authority.

The 63 real row-level holds remain open:

| Hold class | Rows |
|---|---:|
| `LABEL_STRENGTH_CONFLICT` | 3 |
| `LOT_OR_LABEL_DETAIL_OPEN` | 11 |
| `PLANNED_ACQUISITION_OR_PHYSICAL_PENDING` | 9 |
| `PREPARE` | 24 |
| `PREPARE_AND_VERIFY` | 1 |
| `SPECIES_UNRESOLVED` | 1 |
| `VERIFY_FIRST` | 14 |

No module can honestly synthesize the missing bottle labels, lots, preparation receipts, species identity, or physical receipt.

### V20-VAL-010: ratio-bound n-ary interaction contract

**Candidate state:** `CLOSED_STANDALONE`

`nary_interactions.py` rejects:

- arity below two;
- missing participant IDs, roles, or members;
- duplicate participant IDs;
- absent matrix, phase, or context;
- nonpositive or nonclosing ratio vectors;
- pair-score multiplication masquerading as n-ary evidence;
- exact-formula derivation without a source formula hash;
- a designed record labeled physically observed.

Designed and source-supported records remain `NOT_TESTED` and `FORMULA_SIGNATURE_SUPPORT_ONLY` until linked empirical evidence exists.

### V20-VAL-011: DeepLuna runtime policy

**Candidate state:** `CLOSED_STANDALONE_POLICY_GUARD__DEPLOYMENT_HOLD`

`runtime_policy.py` permits only:

```text
project: perfume-chem-cheapluna-isolated
profile: cheapluna-chat
route: DIRECT_PRO
luna_mode: NO_LUNA
DeepLuna Fast: disabled
alternate fallback: disabled
```

Wrong project, profile, route, mode, Fast use, and alternate fallback are rejected. Provider failure remains failure rather than silently rerouting.

This guard has not been deployed into the real repository.

### V20-VAL-012: current repository validation

**State:** `BRIDGE_BLOCKED`

No verified filesystem connector or current remote canary was available. This packet inspected no current HEAD, branch, worktree, migration state, CI result, protected database, installed package, or deployed runtime.

## 3. Validation summary

| Check | Result |
|---|---|
| Python compilation | PASS |
| Unit and regression tests | 76/76 PASS |
| V3 fixture replay | 5/5 class and state match |
| Legacy EQ-02 current-policy adapter | PASS, legacy remains quarantined |
| Legacy EQ-16 quality-score firewall | PASS |
| Exact Decimal synthetic export | PASS, exact total closed |
| Source hash checks | 3/3 PASS |
| Repository-native tests | NOT RUN |
| Python 3.11 replay | NOT RUN |
| Real canary / deployment | BRIDGE_BLOCKED |

## 4. Authority boundary

All of the following remain false:

```text
source admission
package installation
formula authority
inventory mutation
stock authority
bottle authority
physical execution
sensory authority
analytical authority
strict empirical OAV
safety authority
procurement authority
compounding authority
publication authority
repository promotion
release authority
```

This is a tested bridge segment on the workshop floor, not proof that the bridge has been bolted into the mountain.
