# Perfume-Chem V19/V20 Debug and Validation Report

**Generated:** 2026-08-17T05:37:49Z  
**Mode:** read-only evidence validation  
**Repository state:** `BRIDGE_BLOCKED`  
**Overall state:** `HOLD_CURRENT_REPOSITORY__LOCAL_FOUNDATION_VALIDATED_WITH_ONE_LEGACY_HARNESS_FAILURE`

## Executive verdict

The 2026-08-17 current-build notice is internally conservative and compatible with the mounted evidence. The local foundation supports the new policy direction: Inventory V5 is byte-verified; Meaningful Complexity V3 is intact and explicitly rejects universal row-count authority and an overall quality score; the recovered floral and complexity-discovery materials describe themselves as review-only, nonimplemented, and nonpromoting.

The current Perfume-Chem candidate itself is **not independently validated here**. No repository checkout, current verifier log, V19/V20 patch tree, runtime canary, or deployed DeepLuna policy guard was available. The correct current state therefore remains `HOLD`, not PASS.

A concrete legacy defect was reproduced: the Verification Engine Qualification v1 harness still returns **15/16**. Fixture `EQ-02-KNOWN-INVALID` expects `G14` in the failed-gate set, while the checker emits the same `REBUILD` state without `G14`. That mismatch confirms that the old aggregate-score-era qualification package must remain legacy and must not govern the current nonaggregate policy.

## Local checks actually run

### Inventory V5

Mounted file:

`/mnt/data/Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5(1).xlsx`

- Bytes: `199,635`
- SHA-256: `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`
- Result: **PASS exact source identity**

This proves workbook identity only. It does not create physical stock lots, containers, bottle receipts, or `ExactStockRef` records.

### Meaningful Complexity V3

Mounted package:

`/mnt/data/PCV3_CHAT1_MEANINGFUL_COMPLEXITY_MODEL_V3_COMPLETE.zip`

- Bytes: `37,405`
- SHA-256: `10acff0eb8f9e40dc0bd0e8152e04eb3c6440393c39dc950ccc3e96dccc1f6e1`
- ZIP CRC: PASS
- Members: 11
- Internal SHA-256 entries checked: 10
- Internal hash/size failures: 0
- JSON parse failures: 0
- Draft 2020-12 schema self-check: PASS

Policy alignment:

- no universal ingredient-count threshold;
- legacy 50/65 bands are compatibility descriptors and compression-review triggers;
- no overall quality score;
- classification remains multidimensional and noncompensatory;
- physical and hedonic claims remain capped by evidence.

The V3 package remains foundation evidence rather than proof of current installation. Its historical source manifest also references Inventory V3, so current stock-sensitive execution must come from the V5-bound native contracts.

### Legacy V2 conflict

The mounted V2 audit and schema still encode:

- 50-row accord minimum;
- 65-row perfume minimum;
- aggregate G14 score with a 92/100 threshold.

Those rules are valid historical ancestry but conflict with the current same-scope policy. The current runtime must use an explicit V2 legacy adapter, preserve raw round-trip, and structurally prevent V2 row count or `quality_score` from affecting current gate status. There must be no silent fallback to V2 when the current adapter is unavailable.

### Verification Engine Qualification v1 replay

Mounted package SHA-256:

`af2b207bda605058472c868d94f907ea1b6540a8baf1a6458472a55193f7f07d`

- ZIP CRC: PASS
- Fixtures: 16
- Passed: 15
- Failed: 1
- State: FAIL
- Mismatch: `EQ-02-KNOWN-INVALID`
- Expected terminal state: `REBUILD`
- Observed terminal state: `REBUILD`
- Failed-gate mismatch: expected set contains `G14`; observed set does not.

This is a fixture/contract mismatch, not a target-engine result. The package itself states the target Perfume-Chem engine was not run.

## Main debug findings

### P0-1: Formula-artifact validation is the immediate executable blocker

The current notice says quick verification is blocked by formula-artifact validation, but the current failing paths and hashes are not mounted. A prior project state showed the same class of failure when formula Markdown changed without corresponding analysis-hash rebinding. That is a useful lead, not proof of the current cause.

Required triage:

1. Capture exact validator command, commit, working-tree status, exit code, JSON/stdout, and failing paths.
2. For every failing artifact record expected and actual:
   - canonical formula/content hash;
   - analysis-input hash;
   - renderer version;
   - generated-analysis hash;
   - source file hash.
3. Strip generated analysis and compute a semantic source diff.
4. Classify each failure as:
   - unintended source mutation;
   - intentional source mutation not rebound;
   - stale generated analysis;
   - renderer/version drift;
   - missing dependency or source bytes;
   - malformed binding metadata.
5. Restore unintended differences from the protected backup, or explicitly review and rebind intentional differences with the supported command.
6. Rerun the focused formula-artifact validator.
7. Only after that passes, rerun quick verification.

Do not commit, stash, reset, regenerate, or rebind blindly. A clean tree is not sufficient if the wrong formula bytes were accepted.

### P0-2: Current complexity policy needs a hard dispatch firewall

Negative tests must prove:

- a 49-row formula cannot fail solely because it has 49 rows;
- a 65-row padded formula cannot pass because it has 65 rows;
- `quality_score` cannot change current status;
- V2 data may round-trip as historical metadata but cannot affect the current decision;
- missing current policy does not trigger a V2 fallback;
- target-specific identity floors remain separately enforceable when genuinely sourced.

### P0-3: Exact-stock and dose paths must fail closed

Required negative tests:

- missing stock strength never becomes 1.0/neat;
- unknown carrier remains unknown;
- opaque product basis remains opaque;
- mass fraction and volume fraction are never treated as equivalent;
- cross-basis conversion requires conditioned density evidence;
- planned acquisition cannot become physically owned;
- binary float input is rejected at the authority boundary;
- screening output cannot become formula release, sensory, or physical authority.

### P0-4: Source quarantine must be operation-scoped

For recovered packages with unresolved rights:

- `VERIFY_BYTES`: allowed;
- `READ_MANIFEST_FOR_QUARANTINE`: allowed if policy permits;
- `IMPORT_MODULE`, `IMPORT_SCHEMA`, `IMPORT_REGISTRY`, `IMPORT_FORMULA`, `IMPORT_EVIDENCE_LEDGER`, `EXECUTE`, `PROMOTE`: denied.

A matching SHA-256 must not bypass source-rights policy.

### P0-5: Missing exact-byte dependencies must remain hard HOLDs

The four missing dependencies may not be replaced by:

- same-name stale variants;
- regenerated packages;
- reconstructed members;
- receipt-only replicas;
- compatible-looking wheels;
- a newer package presented as the original.

Absence must remain explicit and nonfatal only for operations that do not require those bytes.

### P1: Ratio-bound n-ary interactions

The native contract should reject:

- arity below two;
- missing participant roles;
- invalid or nonclosing ratio vectors;
- absent matrix, phase, or context;
- pair-score multiplication used as n-ary evidence;
- any designed interaction labeled observed.

### P1: DeepLuna runtime policy

Before deployment, replay guards for:

- exact project `perfume-chem-cheapluna-isolated`;
- profile `cheapluna-chat`;
- route `DIRECT_PRO`;
- `NO_LUNA`;
- DeepLuna Fast disabled;
- alternate fallback disabled;
- provider failure preserved as failure rather than silently rerouted.

## Acceptance state

### Locally validated

- Inventory V5 byte identity.
- Meaningful Complexity V3 package CRC and internal checksum closure.
- V3 nonaggregate policy alignment.
- Legacy V2 conflict exists and must be isolated.
- Legacy qualification v1 still fails 15/16 exactly as replayed.
- Mounted source artifacts do not support physical, sensory, analytical, safety, or release promotion.

### Not independently validated

- V19/V20 repository changes.
- Clean-room native module source and tests.
- Current formula-artifact validator failure details.
- Candidate runtime hardening.
- DeepLuna policy deployment.
- Current quick verifier result.
- Exact-byte recovery of the four missing dependencies.
- Installation, publication, physical testing, sensory testing, analytical testing, strict OAV, safety, or release.

## Final state

`BRIDGE_BLOCKED`

No repository mutation was performed. All source-admission, package-installation, formula, inventory, stock, physical, sensory, analytical, strict empirical OAV, safety, procurement, publication, and release authority flags remain false.
