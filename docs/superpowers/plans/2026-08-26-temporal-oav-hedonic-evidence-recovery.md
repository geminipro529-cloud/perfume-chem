# Temporal OAV and Hedonic Evidence Recovery Implementation Plan

> **For the implementing agent:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and execute this plan inline, task by task. Project policy forbids Codex subagents. DeepLuna Chat may perform bounded, non-sensitive grunt work only; Sol owns architecture, science, code acceptance, benchmarking, and promotion.

**Goal:** Repair the two weakest scientific foundations in Perfume-Chem—a context-bound, time-resolved OAV error sentinel and a criterion-specific hedonic evidence path—then retest the Temporal Sensory Ledger and Hedonic Preference Learner against plain GPT-5.6 Sol xhigh before any further floral, wood, amber, citrus, or musk expansion.

**Architecture:** Extend the existing evidence gates and SolForge loop. Do not create a second pipeline or a universal beauty model. Exact stock dose feeds a typed temporal headspace/threshold receipt; measured and modeled evidence remain separate; the pre-mix guard consumes only a validated receipt. Physical sensory observations enter the existing temporal ledger. Blinded pairwise outcomes enter the existing Davidson preference implementation. Every stage emits a canonical hash-bound result, abstains when scope is insufficient, and keeps all authority flags false.

**Tech stack:** Python 3.11+, frozen dataclasses, standard-library deterministic math and resampling, canonical JSON/SHA-256, existing `QuantitativeEvidence`, existing SolForge evidence/protocol contracts, pytest, Ruff, primary peer-reviewed literature, and official standards metadata.

**Predecessors:**

- `docs/superpowers/specs/2026-08-26-solforge-evidence-loop-design.md`
- `docs/superpowers/plans/2026-08-26-solforge-gate-foundation.md`
- `docs/superpowers/plans/2026-08-26-complexity-evidence-augmentation-rebuild.md`
- Current publication baseline commit `e545237f5d41b063d7fe920401671e3603b71794`

## Why this is the next plan

The current branch already has strong structural safeguards:

- Architectural Delta passed its fresh benchmark and is the only admitted replacement complexity module.
- `engine/sensory/ledger.py` already binds exact observed temporal cells and fails closed on duplicate, missing, order-confounded, or unqualified evidence.
- `engine/preference.py` already separates criteria, supports Davidson ties, assessor-cluster bootstrap, held-out validation, heterogeneity, order diagnostics, and deterministic next-pair selection.
- `engine/pipeline/oav_evidence.py` already separates measured, modeled, partial, abstained, and invalid evidence.
- `engine/fuckups/pre_mix_guard.py` already treats active dose as a hard integrity concern and modeled OAV as an advisory warning.

The remaining weaknesses are narrower but consequential:

1. OAV evidence is currently one row per material, not a typed timepoint series with explicit uncertainty and compatibility rules.
2. The pre-mix guard accepts loosely shaped time-series mappings rather than a canonical OAV receipt.
3. Temporal and preference modules are scientifically safer than their predecessors but did not add enough deterministic value to beat plain Sol xhigh in the prior screen.
4. Real blinded, criterion-specific, held-out perfume observations are still missing; composition-derived scores cannot substitute for them.
5. Legacy scalar “hedonic” outputs remain available for historical replay and require a complete active-path leak audit.

## A/B/C/D execution pipeline

| Stage | Purpose | Terminal artifact | Sol level |
|---|---|---|---|
| **A. Authority and sources** | Freeze baseline, adjudicate literature transfer, define exact constructs and compatibility | source ledger V3 plus interface-freeze receipt | **Ultra** |
| **B. Build evidence engines** | Add typed temporal OAV, canonical guard adapter, protocol V2, hedonic augmentation receipt | provider-free code and tests | xhigh after the Stage A checkpoint |
| **C. Challenge and calibrate** | Run adversarial, metamorphic, recovery, leakage, and null tests | frozen falsification receipt | xhigh; Ultra reviews failures |
| **D. Decide and deploy** | Run fresh blinded comparisons, admit winners only, then queue downstream perfume systems | benchmark receipts plus additive registry V6 | **Ultra for corpus freeze and final admission** |

## Model and worker policy

- **Do not switch away from Sol Ultra yet.** Keep Ultra through Tasks 1 and 2, including source-transfer adjudication and the typed interface freeze.
- The exact switch point is a passing, committed `temporal_oav_hedonic_interface_freeze_v1` receipt at the end of Task 2. After that receipt exists, Sol xhigh may perform Tasks 3–8.
- Return to Sol Ultra for Task 9 benchmark-corpus freeze, Task 10 admission adjudication, and any scientific conflict or failed falsification gate.
- The benchmark target is plain GPT-5.6 Sol **xhigh**, because the program must demonstrate augmentation over that baseline. Use the same model, xhigh effort, Fast setting if exposed, tools policy, and frozen input for every compared arm.
- DeepLuna Chat may only enumerate fields, deduplicate bibliographic metadata, check links/identifiers, enumerate test permutations, hash artifacts, and perform other low-level extraction. It may not decide evidence transfer, construct validity, architecture, thresholds, code acceptance, scores, or admission.
- Before each DeepLuna transmission, run a fresh exact-project `deepseek_check`. Transmit only when `READY`; otherwise continue locally. Never use DeepLuna Fast, Luna fallback, or Codex subagents.

## Global constraints

- Preserve registry V1–V5, historical benchmark bytes, failed-source records, raw outputs, and tombstones exactly. Add versioned successors.
- Preserve `PairwisePreference(left_item, right_item, preferred_item)` and the current `OAVEvidenceRequest` API.
- Do not create a new pipeline script. Extend existing modules and existing CLIs.
- Active dose is a deterministic integrity quantity. OAV is an evidence-screening ratio, not percent contribution, salience, target fidelity, complexity, richness, liking, beauty, safety, stability, or release authority.
- A threshold is compatible only at its declared material identity, endpoint, medium/matrix, method, temperature, presentation/application, population, and concentration unit. Unresolved incompatibility produces `HOLD` or `ABSTAINED`.
- A modeled timepoint never becomes a measured timepoint. A predicted release curve never becomes a sensory observation. Missing cells remain missing; no interpolation is allowed for authority or promotion.
- Separate owner preference, trained-panel response, and consumer-population response. None may be generalized to another scope without direct held-out evidence.
- Fit `TARGET_FIDELITY`, `DEPTH`, `RICHNESS`, and `LIKING` separately. Never aggregate them into a beauty, luxury, or complexity score.
- Preserve TARGET/IDEAL versus CURRENT-INVENTORY separation. Inventory presence, ingredient count, formula frequency, supplier prose, price, novelty, and prestige are not evidence of target fit or liking.
- All formula mutation, inventory mutation, compounding, sensory truth, liking truth, safety, purchase, publication, release, and physical-execution authority flags remain false.
- Use `D:\chatbots\perfume-chem\.venv\Scripts\python.exe`, `-p no:cacheprovider`, and a unique `--basetemp` for each pytest run.
- Preserve the four pre-existing `.tmp-*` verifier directories in the publication worktree; do not stage, delete, or alter them.
- Stage only task-owned files. Commit after focused tests, Ruff, and `git diff --check` pass. Push the review branch; do not merge automatically.

## Scientific source boundaries

The implementation must record source identity, edition/date, design, population, matrix, endpoint, exposure, result used, limitations, and transfer disposition. At minimum, adjudicate:

- ISO 13301:2018 metadata for threshold methodology and uncertainty; it does not establish recognition, liking, or perfume contribution.
- ISO 5495:2005 metadata for paired-comparison design.
- ISO 11136:2014 metadata for controlled consumer hedonic testing.
- ISO 13299:2016 metadata for sensory profiling.
- ISO 8586:2023 metadata for assessor selection and training.
- Davidson (1970) for paired comparisons with ties.
- Temporal Dominance of Sensations methodology as a transferable dynamic-sensory method, not direct perfume truth.
- Peer-reviewed dynamic fragrance-release/headspace measurement work for apparatus and repeatability constraints, not sensory or liking inference.
- Human olfactory preference, repeated-exposure, and individual-variability literature for assessor and scope limitations.

Copyrighted standards text must not be copied into the repository. Store official metadata and a derived, scope-limited requirement statement only.

---

### Task 1: Freeze the exact baseline and candidate disposition

**Files:**

- Create: `data/governance/temporal_oav_hedonic_recovery_baseline_v1.json`
- Create: `data/governance/temporal_oav_hedonic_recovery_baseline_v1.sha256`
- Create: `tests/test_temporal_oav_hedonic_recovery_baseline.py`
- Modify: `scripts/scientific_truth_inventory.py`

**Inputs to record:**

- Exact commit, V5 registry hash, current runtime-reachable module IDs, and hashes of the OAV, pre-mix, temporal, preference, hedonic, topology, and wood files.
- Prior benchmark dispositions: Architectural Delta admitted; Temporal Sensory Ledger and Hedonic Preference Learner retired/withheld; topology and wood candidates nonruntime.
- Downloads candidate `OAV_TIME_DOSE_ERROR_SENTINEL_LITERATURE_BASIS_v1.md`: 40,307 bytes, expected SHA-256 `1094ef77c35b955ca0b6e13bc4d79981e6c78f2fcbaccaf6d34b5a175fa2e7c9`, `SOURCE_CANDIDATE_ONLY`.
- Retained downstream artifacts as dependency seeds only: Floral Coverage Foundation V2, Opus V V1R2, and Woody/Amber/Musk V2.
- Explicit rejections: ingredient-count microevent logic and any inventory claim that treats Ambrettolide 10% DPG as physically owned without an exact stock reference.

- [ ] Write a failing test that rejects baseline records with a drifting file hash, a runtime claim inconsistent with registry V5, or any true authority flag.
- [ ] Extend the existing scientific-truth inventory command to emit the baseline record; do not create a new script.
- [ ] Re-hash the Downloads candidate from exact bytes. If absent or mismatched, record `EXACT_BYTES_UNAVAILABLE` and continue without promoting its claims.
- [ ] Run the focused test, script, Ruff, and diff checks.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task1'
& $pythonExe -m pytest tests/test_temporal_oav_hedonic_recovery_baseline.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check scripts/scientific_truth_inventory.py tests/test_temporal_oav_hedonic_recovery_baseline.py
git diff --check
```

- [ ] Commit: `chore(evidence): freeze temporal OAV and hedonic baseline`

### Task 2: Adjudicate sources and freeze the typed interfaces

**Files:**

- Create: `configs/solforge/oav_temporal_policy_v1.json`
- Create: `configs/solforge/hedonic_protocol_policy_v1.json`
- Create: `configs/solforge/complexity_evidence_sources_v3.json`
- Create: `data/research/solforge/research_evidence_records_v3.json`
- Create: `data/research/solforge/research_evidence_records_v3.sha256`
- Create: `data/governance/temporal_oav_hedonic_interface_freeze_v1.json`
- Create: `data/governance/temporal_oav_hedonic_interface_freeze_v1.sha256`
- Modify: `engine/solforge/evidence_review.py`
- Modify: `engine/solforge/research_ingest.py`
- Modify: `tests/test_solforge_evidence_review.py`
- Modify: `tests/test_solforge_research_ingest.py`

**Frozen OAV interfaces:**

```python
@dataclass(frozen=True, slots=True)
class OAVTimepointKey:
    protocol_sha256: str
    sample_id: str
    material_id: str
    time_seconds: int
    endpoint: str


@dataclass(frozen=True, slots=True)
class OAVIntervalEvidence:
    p05: QuantitativeEvidence
    p50: QuantitativeEvidence
    p95: QuantitativeEvidence


@dataclass(frozen=True, slots=True)
class OAVTimepointEvidenceInput:
    key: OAVTimepointKey
    exact_stock_ref: str | None
    active_mass_g: float | None
    headspace_interval: OAVIntervalEvidence
    threshold_interval: OAVIntervalEvidence
    model_tier: str
    context_sha256: str


@dataclass(frozen=True, slots=True)
class TemporalOAVEvidenceRequest:
    formula_sha256: str
    dose_receipt_sha256: str
    protocol_sha256: str
    measurement_context_sha256: str
    cells: tuple[OAVTimepointEvidenceInput, ...]
```

The result must report exact observed cell count, modeled cell count, missing declared cells, duplicate cells, per-cell OAV P05/P50/P95, compatibility blockers, model tier, source hashes, and all-false authority. Canonical cell identity is the full `OAVTimepointKey`.

**Required policy decisions:**

- Canonical time uses nonnegative integer seconds; labels such as `5m` are display aliases only.
- Protocols declare their own timepoints. Do not hardcode 5 min/30 min/2 h/8 h/24 h as universal.
- Interval order must satisfy P05 <= P50 <= P95 and use compatible positive concentration/threshold units.
- OAV interval calculation is `headspace_p05 / threshold_p95`, `headspace_p50 / threshold_p50`, and `headspace_p95 / threshold_p05` only when every compatibility field passes.
- Relative threshold cancellation is allowed only for the same material identity, threshold source, matrix, method, temperature, application, endpoint, and unit. Otherwise return `THRESHOLD_CANCELLATION_INCOMPATIBLE`.
- Naturals and trade bases require constituent-specific evidence or remain whole-material screening rows; constituent estimates cannot be silently summed into strict material OAV.
- `T0_UNKNOWN`, `T1_TRANSFERRED`, `T2_MODELED`, `T3_CALIBRATED_MODELED`, and `T4_MEASURED` are evidence tiers, not confidence percentages or authority levels.

- [ ] Write red tests for every policy decision and for V2 ledger byte preservation.
- [ ] Use DeepLuna only for DOI/edition deduplication and required-field extraction after a fresh exact-project readiness check.
- [ ] Sol Ultra adjudicates every transfer disposition and source-to-code requirement.
- [ ] Freeze the V3 ledger and the interface receipt only when all source records and hashes validate.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task2'
& $pythonExe -m pytest tests/test_solforge_evidence_review.py tests/test_solforge_research_ingest.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m engine.solforge.research_ingest validate-v3 --input data/research/solforge/research_evidence_records_v3.json
& $pythonExe -m ruff check engine/solforge/evidence_review.py engine/solforge/research_ingest.py tests/test_solforge_evidence_review.py tests/test_solforge_research_ingest.py
git diff --check
```

- [ ] Commit: `research(solforge): freeze temporal OAV and hedonic interfaces`
- [ ] **Model checkpoint:** after this commit and a matching interface-freeze receipt, notify the user that routine implementation may switch from Sol Ultra to Sol xhigh.

### Task 3: Extend the existing OAV evidence gate with typed temporal cells

**Files:**

- Modify: `engine/pipeline/oav_evidence.py`
- Create: `tests/test_temporal_oav_evidence.py`
- Modify: `tests/test_oav_evidence_gate_v2.py`

**Interfaces:**

- Add the Task 2 frozen types and `evaluate_temporal_oav_evidence` to `engine/pipeline/oav_evidence.py`.
- Leave `OAVMaterialEvidenceInput`, `OAVEvidenceRequest`, `OAVEvidenceResult`, and `evaluate_oav_evidence` backward compatible.
- Add `TemporalOAVEvidenceResult` with canonical serialization, result hash, lineage hashes, exact state, blockers, limitations, and all-false authority.

- [ ] Write red tests for duplicate cells, undeclared/missing cells, noncanonical time, incompatible units, incompatible thresholds, invalid intervals, natural/preblend handling, missing stock lineage, mixed measured/modeled evidence, exact deterministic bytes, and export/import round-trip.
- [ ] Implement measured and modeled series as separate collections; never fill one from the other.
- [ ] Compute intervals only from compatible positive evidence and preserve raw evidence references.
- [ ] Return `STRICT_MEASURED_TIME_SERIES`, `MODELED_SCREEN`, `PARTIAL`, `ABSTAINED`, or `INVALID` without changing the V2 result schema.
- [ ] Run focused tests, Ruff, and diff checks.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task3'
& $pythonExe -m pytest tests/test_oav_evidence_gate_v2.py tests/test_temporal_oav_evidence.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/pipeline/oav_evidence.py tests/test_oav_evidence_gate_v2.py tests/test_temporal_oav_evidence.py
git diff --check
```

- [ ] Commit: `feat(oav): add typed temporal evidence receipts`

### Task 4: Bind the pre-mix guard to canonical OAV receipts

**Files:**

- Modify: `engine/fuckups/pre_mix_guard.py`
- Modify: `tests/test_pre_mix_guard.py`
- Create: `tests/test_pre_mix_temporal_oav_binding.py`

**Required behavior:**

- Preserve the existing untyped `parent_time_series` and `child_time_series` compatibility path as `LEGACY_MODELED_SCREEN_ONLY`.
- Add optional validated parent/child `TemporalOAVEvidenceResult` inputs and bind their receipt hashes in `PreMixGuardReport`.
- Active-dose equivalence and unauthorized active-dose jumps remain hard `FAIL` findings.
- Temporal OAV jumps, persistent modeled dominance, and interval overlap remain `WARN`/screening findings only.
- Compare timepoints only when exact key and compatibility scope match. Never compare nearest labels or interpolate.
- An invalid, partial, or hash-mismatched OAV receipt cannot suppress an active-dose finding.

- [ ] Write red tests for typed binding, hash mismatch, threshold cancellation, nonoverlapping timepoints, measured-versus-modeled separation, active-dose precedence, and legacy compatibility.
- [ ] Implement the narrow adapter in the existing guard module.
- [ ] Run focused tests and commit.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task4'
& $pythonExe -m pytest tests/test_pre_mix_guard.py tests/test_pre_mix_temporal_oav_binding.py tests/test_temporal_oav_evidence.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/fuckups/pre_mix_guard.py tests/test_pre_mix_guard.py tests/test_pre_mix_temporal_oav_binding.py
git diff --check
```

- [ ] Commit: `feat(guard): consume canonical temporal OAV evidence`

### Task 5: Complete the legacy hedonic claim-firewall audit

**Files:**

- Modify: `engine/optimizer/scoring.py`
- Modify only if an active leak is proven: relevant CLI/API/report adapter files identified by the audit
- Modify: `tests/test_legacy_hedonic_runtime_isolation.py`
- Create: `tests/test_hedonic_claim_firewall.py`
- Create: `data/governance/hedonic_active_path_audit_v1.json`
- Create: `data/governance/hedonic_active_path_audit_v1.sha256`

- [ ] Enumerate every import and output consumer of `engine/hedonic_model.py`, `score_legacy_replay`, “hedonic score,” “pleasantness,” “beauty,” and legacy aggregate objectives.
- [ ] Write a red test for each proven active-path leak before changing code.
- [ ] Preserve historical replay APIs and frozen output bytes, but label them `LEGACY_REPLAY_ONLY` and prevent them from entering current optimizer, release, API, report, or SolForge promotion records.
- [ ] Test that active scoring rejects nonzero hedonic objective weight and reports liking `NOT_TESTED` unless a valid exact-scope hedonic evidence receipt exists.
- [ ] Freeze an audit receipt listing inspected entry points, hashes, findings, fixes, and unresolved compatibility surfaces.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task5'
& $pythonExe -m pytest tests/test_legacy_hedonic_runtime_isolation.py tests/test_hedonic_claim_firewall.py tests/test_hedonic_evidence_gate_v2.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/optimizer/scoring.py tests/test_legacy_hedonic_runtime_isolation.py tests/test_hedonic_claim_firewall.py
git diff --check
```

- [ ] Commit: `fix(hedonic): close active legacy claim paths`

### Task 6: Version the prospective temporal and preference protocols

**Files:**

- Modify: `engine/solforge/protocols.py`
- Modify: `engine/solforge/adapters.py`
- Create: `data/research/solforge/protocol_templates_v2.json`
- Modify: `tests/test_solforge_protocols.py`
- Modify: `tests/test_solforge_evidence_adapters.py`
- Modify: `tests/test_temporal_sensory_evidence.py`

**Protocol V2 requirements:**

- Separate protocol scopes for owner, trained panel, and consumer population.
- Separate endpoints for target fidelity, depth, richness, liking, intensity, familiarity, and detectability.
- Bind sample, exact build/execution receipt, assessor, repeat, session, timepoint, sequence, schedule, washout, apparatus, safety stop, and deviation hashes.
- Declare counterbalancing/Williams sequence, repeats, primary endpoint, tie/indifference semantics, cluster unit, held-out unit, baseline, seed, and stopping rule before observation.
- Permit within-sniff timing only when apparatus and timing protocol are explicitly qualified.
- Preserve V1 protocol bytes and parsing.

- [ ] Write red tests for scope leakage, criterion collapse, missing counterbalance, post-outcome edits, unsafe exposure, synthetic result promotion, missing repeats, invalid held-out split, and V1 compatibility.
- [ ] Add V2 builders to the existing protocols module and CLI; do not add another script.
- [ ] Add adapters that create existing `TemporalEvidenceRequest` and `PreferenceFitRequest` objects without inventing observations.
- [ ] Run tests and commit.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task6'
& $pythonExe -m pytest tests/test_solforge_protocols.py tests/test_solforge_evidence_adapters.py tests/test_temporal_sensory_evidence.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/solforge/protocols.py engine/solforge/adapters.py tests/test_solforge_protocols.py tests/test_solforge_evidence_adapters.py
git diff --check
```

- [ ] Commit: `feat(solforge): version temporal and preference protocols`

### Task 7: Make Temporal Ledger produce a concise evidence delta

**Files:**

- Modify: `engine/sensory/ledger.py`
- Modify: `engine/solforge/adapters.py`
- Modify: `tests/test_temporal_sensory_evidence.py`
- Modify: `tests/test_solforge_evidence_adapters.py`

Do not replace the existing ledger. Add a deterministic augmentation view over its validated result:

- `AUGMENT` only when exact observations support one new finding or one next comparison.
- `NO_AUGMENTATION` when the question is resolved or no admissible comparison adds information.
- `HOLD` for missing/conflicted cells, scope mismatch, order/carryover failure, unqualified timing, unsafe exposure, or failed repeatability.
- Report one most discriminating comparison using observed uncertainty/disagreement and protocol constraints; do not use predicted OAV or prose confidence.
- Keep observed medians, dispersion, assessor disagreement, transition evidence, and missingness visible. Do not collapse them into one temporal complexity score.

- [ ] Add tests for resolved/no-action, one missing cell, duplicate conflict, temporal crossover, disagreement, carryover, order imbalance, within-sniff qualification, deterministic tie-breaking, and output round-trip.
- [ ] Add metamorphic tests proving row-order and blind-label invariance.
- [ ] Run focused tests and commit.

- [ ] Commit: `feat(sensory): emit bounded temporal evidence deltas`

### Task 8: Rebuild Hedonic Preference around augmentation value

**Files:**

- Modify: `engine/preference.py`
- Modify: `engine/preference_validation.py`
- Modify: `engine/hedonic_evidence.py`
- Modify: `engine/solforge/adapters.py`
- Modify: `tests/test_preference.py`
- Modify: `tests/test_scoped_preference.py`
- Modify: `tests/test_preference_validation.py`
- Modify: `tests/test_hedonic_evidence_gate_v2.py`
- Modify: `tests/test_solforge_evidence_adapters.py`

Preserve the current Davidson implementation unless fixed-seed recovery tests prove a defect. The rebuild targets decision value, not a more ornate model.

**Required result additions:**

- Separate item probabilities/intervals for exactly one criterion and exact protocol scope.
- Proper held-out score and declared baseline margin.
- Tie/indifference rate and Davidson tie parameter.
- Assessor-cluster interval, heterogeneity, influential-assessor diagnostic, order effect, carryover diagnostic, component connectivity, temporal crossover, and split hashes.
- Exactly zero or one next pair, selected deterministically under protocol, connectivity, exposure-balance, and expected-information constraints.
- `NO_AUGMENTATION` when plain counting or the declared baseline already resolves the decision, when no admissible next pair exists, or when the fitted model adds no validated predictive value.
- `WITHHELD`/`HOLD` for sparse, disconnected, unscoped, order-confounded, carryover-confounded, leakage-prone, unstable, or baseline-failing data.

- [ ] Write red tests for criterion isolation, ties, disconnected graphs, assessor clusters, one-assessor dominance, order reversal, carryover, repeated exposure, temporal aggregate reversal, held-out leakage, baseline failure, deterministic bootstrap, deterministic next pair, and no-useful-augmentation.
- [ ] Keep `random.Random(seed)` and standard-library math; add no dependency.
- [ ] Ensure a valid owner-scoped liking result cannot claim trained-panel or consumer preference.
- [ ] Ensure OAV, formula composition, luxury language, brand, price, and perfume identity are absent from directional fitting features.
- [ ] Run tests and commit.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task8'
& $pythonExe -m pytest tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_validation.py tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/preference.py engine/preference_validation.py engine/hedonic_evidence.py engine/solforge/adapters.py tests/test_preference.py tests/test_preference_validation.py
git diff --check
```

- [ ] Commit: `feat(preference): require validated hedonic augmentation value`

### Task 9: Freeze provider-free recovery and falsification gates

**Files:**

- Create: `tests/science/test_temporal_oav_recovery.py`
- Create: `tests/science/test_hedonic_preference_recovery_v2.py`
- Create: `tests/science/test_evidence_foundation_falsification_v1.py`
- Create: `data/benchmarks/solforge/evidence_foundation_recovery_v1/manifest.json`
- Create: `data/benchmarks/solforge/evidence_foundation_recovery_v1/manifest.sha256`

**OAV cases:** stock-strength substitution, active-dose rebase, unit mismatch, matrix mismatch, threshold-method mismatch, threshold cancellation, missing and duplicate timepoints, measured/modeled mixture, interval inversion, natural constituent ambiguity, context hash drift, and null change.

**Temporal cases:** missing cell, discordant duplicate, order/carryover confounding, unsafe exposure, unqualified within-sniff timing, assessor disagreement, true crossover, no transition, and resolved/no-next-test.

**Preference cases:** known Davidson utilities/ties, disconnected graph, cluster-versus-row bootstrap reversal, order bias, carryover, repeated-exposure change, subgroup reversal, criterion leakage, train/test leakage, null winner, calibration failure, baseline failure, and deterministic next-pair choice.

- [ ] Freeze generators, seeds, sample sizes, expected tolerances, and exact output hashes before running.
- [ ] Require zero false promotions and zero missed critical holds across all adversarial cases.
- [ ] Require utility/tie recovery and interval coverage within declared tolerances; do not tune tolerances after seeing failures.
- [ ] Require row-order, blind-label, irrelevant-prose, and brand-name invariance.
- [ ] Require all authority flags false and every receipt byte-reproducible.
- [ ] A failed gate returns to the owning task; it never proceeds to external benchmarking.

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-recovery-task9'
& $pythonExe -m pytest tests/science/test_temporal_oav_recovery.py tests/science/test_hedonic_preference_recovery_v2.py tests/science/test_evidence_foundation_falsification_v1.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check tests/science/test_temporal_oav_recovery.py tests/science/test_hedonic_preference_recovery_v2.py tests/science/test_evidence_foundation_falsification_v1.py
git diff --check
```

- [ ] Commit: `test(science): freeze OAV and hedonic recovery gates`
- [ ] **Model checkpoint:** return to Sol Ultra before authoring or freezing the benchmark corpus.

### Task 10: Run a fresh xhigh benchmark and admit winners only

**Files:**

- Create: `tests/fixtures/complexity_replacement_benchmark_cases_v7.json`
- Create: `tests/fixtures/complexity_replacement_benchmark_cases_v7.sha256`
- Modify: `engine/perception/complexity_replacement_benchmark.py`
- Modify: `tests/test_complexity_replacement_benchmark.py`
- Create during execution: `data/benchmarks/solforge/evidence_foundation_screen_v1/`
- Create only for screen passers: `data/benchmarks/solforge/evidence_foundation_confirmation_v1/`
- Create: `data/governance/evidence_foundation_admission_v1.json`
- Create: `data/governance/evidence_foundation_admission_v1.sha256`
- Create only if at least one retired module passes: `configs/complexity/complexity_module_registry_v6.json`
- Modify only if V6 exists: `engine/perception/complexity_registry.py`
- Create only if V6 exists: `tests/test_complexity_registry_v6.py`

**Candidates:**

1. Temporal OAV Error Sentinel, as a deterministic evidence/integrity augmenter—not a perfumer.
2. Temporal Sensory Ledger augmentation view.
3. Hedonic Preference Learner augmentation view.

Architectural Delta is a frozen regression control, not a candidate for re-admission.

**Case design:** Three blinded screening cases and three unseen confirmation cases per candidate. Include a positive calculation case, a correct-no-change/no-augmentation case, and a critical trap in each split. Required traps include inventory/stock mismatch, threshold incompatibility, missing evidence, count inflation, order/carryover confounding, criterion leakage, assessor heterogeneity, and an unseen variant.

**Arms:**

1. Plain GPT-5.6 Sol xhigh.
2. The same Sol xhigh plus a length-matched governance/placebo context.
3. The same Sol xhigh plus the deterministic candidate receipt.

Freeze model identity, xhigh effort, Fast availability/state, tools state, input, context, prompts, arm ordering, output bytes, scores, and hashes. Use fresh projectless conversations; do not resume the 27 frozen historical requests.

**Noncompensatory gate:**

- Screening: at least 2/3 wins against each control and zero critical errors.
- Final: at least 4/6 wins, median paired gain at least five points against each control, zero critical errors, provider-free gates passing, deterministic receipts, and no high-risk-stratum regression.
- Correct abstention/no augmentation earns full safety and efficiency credit.
- A failing candidate remains runtime unreachable and is retained as a provenance tombstone.
- No benchmark result establishes physical liking, sensory performance, safety, stability, or release.

- [ ] Freeze and validate the V7 corpus before dispatch.
- [ ] Run screen arms in fresh contexts and resolve each request by stable task ID before any retry.
- [ ] Stop failed candidates; do not spend confirmation requests on them.
- [ ] Run unseen confirmation for passers only.
- [ ] Have Sol Ultra perform blind final adjudication against machine-scored invariants and frozen rubrics.
- [ ] Create registry V6 only for exact-scope winners; preserve V1–V5 bytes and all losing tombstones.
- [ ] Run the full focused regression set, project verifier, Ruff, and `git diff --check`.
- [ ] Commit: `bench(solforge): freeze evidence foundation admission`

### Task 11: Start downstream perfume-system rebuilds only after foundation acceptance

This task creates planning/experiment records, not an all-at-once formula library. Each system uses Architectural Delta, the accepted evidence foundation, isolated constant-total arms, observed temporal cells, and criterion-specific blinded preference evidence.

**Order:**

1. **Floral and sweet Orris:** reconcile Floral Coverage Foundation V2 semantically; cover soliflores, two-flower pairs, and selected three-/four-factor designs without enumerating hundreds of formulas. Treat Orris root as a rhizome subject and include a distinct sweet-Orris frontier.
2. **Wood depth and perceptual topology:** test depth separately from darkness, intensity, total wood dose, and ingredient count. Use DHP 2025 and perfume exemplars such as Opus V only as target/reference descriptions until exact lawful evidence is available.
3. **Amber, resin, and incense:** build recognizer and omission/ratio protocols for storax, benzoin, myrrh, frankincense/olibanum, labdanum, vanilla/balsamic supports, and woods. Do not infer formula beauty from literature.
4. **Citrus architecture:** distinguish citrus families/extraction types and test heart “echo” strategies such as acetates, floral bridges, salicylates, green materials, and woods. Neroli 10% is support-only unless neroli/orange blossom is central.
5. **Musk architecture:** default to zero or one precise musk. Preserve Habanolide and Romandolide as owned only when refreshed V5 records confirm it; Ambrettolide 10% remains design-available/procurement-pending; Ethylene Brassylate remains missing unless refreshed evidence proves otherwise. Tonalide, Macrolide, and Musk Ketone remain exception-only.
6. **Opus V and Amouage regression library:** convert target descriptions and prior V1R2 work into blinded regression cases, not similarity or liking claims.

For every system, stop at `RESEARCH_ONLY` or `PROTOCOL_VALIDATED` until real prospective evidence exists. Each candidate must independently pass the same provider-free and Sol xhigh admission gates before runtime exposure.

### Task 12: Review, commit, and GitHub handoff

- [ ] Run the repository-prescribed focused suites followed by the full project verifier in the required order.
- [ ] Verify no secret, raw chat, protected workbook, unlicensed full text, Downloads path, or unrelated temporary artifact is staged.
- [ ] Verify registry and benchmark predecessor hashes and all authority flags.
- [ ] Review `git diff --stat`, `git diff --check`, and every changed binary/large file intentionally.
- [ ] Push `codex/complex-perfumery-publish`; do not force-push or merge.
- [ ] Update the GitHub pull request with exact tests, module dispositions, benchmark metrics, evidence limits, and remaining physical-work requirements.

## Completion criteria

- Exact baseline and source/interface receipts are frozen and hash-valid.
- Existing OAV V2 and preference three-argument APIs remain compatible.
- Typed temporal OAV cells reject duplicates, preserve missingness, enforce threshold compatibility, and separate measured from modeled evidence.
- The pre-mix guard consumes canonical OAV receipts while keeping active dose hard and OAV advisory.
- No active optimizer/release/API path consumes legacy composition-derived hedonic scoring.
- Protocol V2 separates criteria, assessor populations, order, repeats, time, held-out units, and safety.
- Temporal and preference modules produce a deterministic useful delta, correct no-augmentation, or hold—never filler prose.
- Provider-free recovery and falsification gates have zero false promotions and deterministic hashes.
- Fresh Sol xhigh screen and confirmation evidence exists for each candidate; only exact-scope winners are runtime reachable.
- Downstream floral, wood, amber, citrus, musk, and Opus V work begins only on the accepted evidence foundation.
- All physical, sensory, liking, safety, purchase, publication, and release authority remains false unless separately established by valid prospective evidence.

## Scientific references for source adjudication

- ISO 13301:2018, sensory analysis methodology for odour/flavour/texture detection threshold measurement: <https://www.iso.org/standard/68901.html>
- ISO 11136:2014, controlled consumer hedonic testing: <https://www.iso.org/standard/50125.html>
- ISO 13299:2016, sensory profile methodology: <https://www.iso.org/standard/58042.html>
- ISO 8586:2023, selection and training of sensory assessors: <https://www.iso.org/standard/76667.html>
- Davidson RR. *On Extending the Bradley-Terry Model to Accommodate Ties in Paired Comparison Experiments* (1970): <https://www.tandfonline.com/doi/abs/10.1080/01621459.1970.10481082>
- Temporal Dominance of Sensations methodological review: <https://www.sciencedirect.com/science/article/pii/S0924224414000879>
- Hadjiefstathiou et al. (2025), repeatable dynamic fragrance-release sampling: <https://pubmed.ncbi.nlm.nih.gov/39265418/>
- SSParoT pairwise hedonic ratings and test-retest design: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7581750/>
- Cross-cultural and individual variability in odour pleasantness: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11672226/>
- Repeated exposure and odour pleasantness: <https://pmc.ncbi.nlm.nih.gov/articles/PMC3989720/>
- Within-individual variability in olfactory performance: <https://pmc.ncbi.nlm.nih.gov/articles/PMC3493268/>
- Bayesian paired-comparison overview with repeated-subject concerns: <https://pmc.ncbi.nlm.nih.gov/articles/PMC9374650/>
