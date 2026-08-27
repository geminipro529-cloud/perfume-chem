# Complexity Evidence-Augmentation Rebuild Implementation Plan

> **For the implementing agent:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Project policy forbids Codex subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Architectural Delta, Temporal Sensory Ledger, and Hedonic Preference as scientifically sourced deterministic evidence augmenters that emit zero or one useful delta, then admit only modules that outperform plain GPT-5.6 Sol and a length-matched governance control.

**Architecture:** Extend the existing Perfume-Chem and SolForge code rather than creating a parallel pipeline. A versioned source-transfer ledger and construct registry feed one shared `EvidenceDeltaReceiptV1`; the existing architectural, temporal, and preference modules produce `AUGMENT`, `NO_AUGMENTATION`, or `HOLD`, and existing SolForge adapters carry those receipts into a fresh blinded admission benchmark.

**Tech Stack:** Python 3.11+, frozen dataclasses, standard-library deterministic numerical routines, existing PyYAML/openpyxl environment, canonical JSON and SHA-256, pytest, Ruff, primary peer-reviewed literature, authoritative ISO/ASTM metadata, fresh projectless GPT-5.6 Sol Max/Ultra comparisons.

**Spec:** `docs/superpowers/specs/2026-08-26-complexity-evidence-augmentation-rebuild-design.md`

## Global Constraints

- Execute inline in `C:\Users\ASUS\.codex\worktrees\a7e6\perfume-chem`; project policy forbids Codex subagents, so the viable execution skill is `superpowers:executing-plans`.
- Use GPT-5.6 Sol Ultra for scientific architecture, benchmark design, and final admission; use Sol Max for bounded implementation/review work. Use Fast execution only when the host exposes it, and identically for every compared benchmark arm.
- `Fast` never means DeepLuna Fast. Do not invoke, start, or fall back to the retired DeepLuna Fast workflow.
- Preserve the pre-existing untracked `.tmp-solforge-*` directories. Do not delete, move, stage, or modify them.
- Preserve frozen registry V1 bytes and every historical benchmark, prompt, output, receipt, and provenance tombstone. Use versioned successors.
- Define target identity and its functional architecture before inventory matching; material count and availability never redefine the target.
- Parse the authoritative V5 inventory workbook at every Architectural Delta execution; keep TARGET/IDEAL separate from CURRENT-INVENTORY.
- Add no new runtime dependency. Implement the Davidson numerical core with the Python standard library unless an already-approved dependency is proven present and exact-version bound.
- Preserve `PairwisePreference(left_item, right_item, preferred_item)` construction and existing serialization compatibility.
- One observation, fit, or benchmark criterion never authorizes another criterion. `LIKING`, `PERCEIVED_RICHNESS`, `PERCEIVED_DEPTH`, `TARGET_FIDELITY`, intensity, familiarity, and detectability remain separate.
- OAV, headspace, formula count, GC-peak count, supplier prose, model prose, novelty, price, and prestige never establish liking, richness, depth, contribution, or beauty.
- Every scientific rule requires a source-tier and transfer assessment. Public standards metadata does not authorize reproduction of copyrighted standard text.
- Missing, conflicted, unscoped, nonidentifiable, order-confounded, carryover-confounded, or unstable evidence fails closed.
- All formula, inventory-mutation, compounding, physical-execution, sensory-truth, liking-truth, safety, purchase, publication, and release authority flags remain false.
- Use `D:\chatbots\perfume-chem\.venv\Scripts\python.exe` and a unique `--basetemp` with `-p no:cacheprovider` for pytest because the default Windows pytest temporary root is not reliable.
- Stage only paths named by the active task. Commit each task only after its focused tests, Ruff checks, and `git diff --check` pass.
- Do not start fresh external model requests until provider-free corpus, scorer, receipt, and hash validation pass. Never retry an ambiguous paid request without resolving its stable identifier.

---

## File and responsibility map

- `engine/solforge/evidence_review.py` -- versioned source tiers, study-quality checks, transfer assessment, and operative evidence bindings; leaves `engine/solforge/research.py` V1 compatibility intact.
- `configs/solforge/complexity_construct_registry_v1.json` -- closed criterion wording, anchors, population, matrix, time, outcome vocabulary, indifference region, and forbidden claims.
- `configs/solforge/complexity_evidence_sources_v2.json` and `data/research/solforge/research_evidence_records_v2.json` -- expanded primary-source/standards ledger with current status and transfer limits.
- `engine/evidence/augmentation.py` -- shared `AUGMENT`/`NO_AUGMENTATION`/`HOLD` receipt, canonical serialization, and all-false authority envelope.
- `engine/perception/architectural_delta.py` -- target/inventory compiler, comparison closure, citrus/musk policy, and architectural augmentation disposition.
- `engine/sensory/ledger.py` -- observed-cell analysis plus resolved/incomplete/conflicted/protocol-hold/insufficient-scope audit.
- `engine/preference_davidson.py` -- deterministic penalized Davidson likelihood, analytic derivatives, convergence receipt, and probability calculation.
- `engine/preference_validation.py` -- assessor-cluster bootstrap, proper scoring/calibration, transitivity diagnostics, and constrained next-pair selection.
- `engine/preference.py` -- backward-compatible public API, outcome semantics, scope gates, and orchestration of fitting/validation.
- `engine/hedonic_evidence.py` -- exact-scope evidence receipt updated for proper scoring, temporal/order diagnostics, and tie semantics.
- `engine/solforge/adapters.py` and `engine/solforge/contracts.py` -- versioned packet adapters and canonical receipt transport; V1 packet parsing remains compatible.
- `engine/perception/complexity_replacement_benchmark.py` -- reuse the existing three-arm benchmark and add V4 abstention/objective-receipt requirements without altering historical receipts.
- `configs/complexity/complexity_module_registry_v4.json` -- versioned nonruntime overlay for rebuilt candidates; import paths stay null until admission passes.
- `tests/fixtures/complexity_replacement_benchmark_cases_v4.json` -- three screen and three unseen confirmation cases for each rebuilt module.

---

### Task 1: Version the scientific evidence and construct layer

**Files:**
- Create: `engine/solforge/evidence_review.py`
- Create: `tests/test_solforge_evidence_review.py`
- Create: `configs/solforge/complexity_construct_registry_v1.json`
- Create: `configs/solforge/complexity_evidence_sources_v2.json`
- Create: `data/research/solforge/research_evidence_records_v2.json`
- Create: `data/research/solforge/research_evidence_records_v2.sha256`
- Modify: `engine/solforge/research_ingest.py`
- Modify: `tests/test_solforge_research_ingest.py`

**Interfaces:**
- Consumes: `ResearchEvidenceRecordV1`, `ResearchLedgerV1`, and `canonical_json_bytes`.
- Produces: `EvidenceSourceTier`, `TransferDisposition`, `SourceQualityAssessmentV1`, `OperativeEvidenceBindingV1`, `EvidenceReviewLedgerV1`, `load_construct_registry`, and `validate_evidence_review`.

- [ ] **Step 1: Write failing evidence-tier and transfer tests**

```python
def test_food_sensory_method_cannot_directly_support_perfume_liking() -> None:
    binding = OperativeEvidenceBindingV1(
        requirement_id="HEDONIC_LIKING_DIRECT",
        source_record_sha256="a" * 64,
        source_tier=EvidenceSourceTier.TRANSFERABLE_SENSORY_METHOD,
        requested_claim="BLIND-A is preferred as a perfume",
        demonstrated_scope="temporal dominance in flavored gels",
        transfer_disposition=TransferDisposition.HOLD,
        limitations=("matrix and endpoint do not match",),
    )
    assert binding.transfer_disposition is TransferDisposition.HOLD


def test_systematic_review_requires_primary_source_traceability() -> None:
    assessment = SourceQualityAssessmentV1(
        source_id="REVIEW-1",
        tier=EvidenceSourceTier.SYSTEMATIC_SYNTHESIS,
        primary_source_ids=(),
        population_declared=True,
        matrix_declared=True,
        endpoint_declared=True,
        order_control_reported=False,
        assessor_dependence_reported=True,
        limitations=("heterogeneous matrices",),
    )
    assert "PRIMARY_TRACE_MISSING" in assessment.failures
```

- [ ] **Step 2: Run the focused tests and verify the missing-module failure**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-evidence-review-red'
& $pythonExe -m pytest tests/test_solforge_evidence_review.py -q -p no:cacheprovider --basetemp $testRoot
```

Expected: collection fails because `engine.solforge.evidence_review` does not exist.

- [ ] **Step 3: Implement the closed evidence and construct contracts**

```python
class EvidenceSourceTier(str, Enum):
    DIRECT_FINE_FRAGRANCE = "DIRECT_FINE_FRAGRANCE"
    DIRECT_HUMAN_OLFACTION = "DIRECT_HUMAN_OLFACTION"
    SYSTEMATIC_SYNTHESIS = "SYSTEMATIC_SYNTHESIS"
    TRANSFERABLE_SENSORY_METHOD = "TRANSFERABLE_SENSORY_METHOD"
    STATISTICAL_FOUNDATION = "STATISTICAL_FOUNDATION"
    HYPOTHESIS_ONLY = "HYPOTHESIS_ONLY"


class TransferDisposition(str, Enum):
    DIRECT = "DIRECT"
    METHOD_ONLY = "METHOD_ONLY"
    NARROWER_SCOPE = "NARROWER_SCOPE"
    HOLD = "HOLD"
```

Use frozen dataclasses with closed `from_dict`, `as_dict`, canonical bytes, and record hashes. Reject an operative binding when the requested claim exceeds the demonstrated population, matrix, endpoint, time, or evidence tier.

- [ ] **Step 4: Freeze the construct registry and expanded evidence ledger**

The construct registry must contain exactly:

```json
[
  "LIKING",
  "PERCEIVED_RICHNESS",
  "PERCEIVED_DEPTH",
  "CONFIGURATIONAL_INTEGRATION",
  "HIERARCHY_CONTRAST",
  "TEMPORAL_DIFFERENTIATION",
  "TARGET_FIDELITY",
  "INTENSITY",
  "FAMILIARITY",
  "DETECTABILITY"
]
```

Add the core sources listed in design-spec Section 14, current ISO metadata, and ASTM E2263-25. Every record must include design, population, matrix, exposure, endpoint, result used, limitations, source tier, transfer disposition, rights state, and exact code requirement. Retain only licensed/open bytes; otherwise store metadata and derived summaries.

- [ ] **Step 5: Extend the ingestion CLI with V2 validation and freeze commands**

Add `validate-v2` and `freeze-v2` actions. `freeze-v2` sorts records by `source_id`, rejects duplicate stable identifiers, serializes UTF-8 canonical JSON, and writes the digest sidecar. It never converts a search result snippet into a study result.

- [ ] **Step 6: Run evidence tests, CLI validation, and Ruff**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-evidence-review-green'
& $pythonExe -m pytest tests/test_solforge_evidence_review.py tests/test_solforge_research.py tests/test_solforge_research_ingest.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m engine.solforge.research_ingest validate-v2 --input data/research/solforge/research_evidence_records_v2.json
& $pythonExe -m engine.solforge.research_ingest freeze-v2 --input data/research/solforge/research_evidence_records_v2.json --sha-output data/research/solforge/research_evidence_records_v2.sha256
& $pythonExe -m ruff check engine/solforge/evidence_review.py engine/solforge/research_ingest.py tests/test_solforge_evidence_review.py tests/test_solforge_research_ingest.py
git diff --check
```

Expected: all checks pass and the sidecar equals the exact V2 ledger file hash.

- [ ] **Step 7: Commit Task 1**

```powershell
git add -- engine/solforge/evidence_review.py engine/solforge/research_ingest.py tests/test_solforge_evidence_review.py configs/solforge/complexity_construct_registry_v1.json configs/solforge/complexity_evidence_sources_v2.json data/research/solforge/research_evidence_records_v2.json data/research/solforge/research_evidence_records_v2.sha256 tests/test_solforge_research_ingest.py
git commit -m "research(solforge): version complexity evidence review"
```

### Task 2: Add the shared evidence-augmentation receipt

**Files:**
- Create: `engine/evidence/augmentation.py`
- Create: `tests/test_evidence_augmentation.py`
- Modify: `engine/solforge/contracts.py`
- Modify: `tests/test_solforge_contracts.py`

**Interfaces:**
- Consumes: `canonical_json_bytes`, `sha256_hex`, and source-binding hashes from Task 1.
- Produces: `EvidenceAugmentationState`, `DecisionDeltaV1`, `EvidenceDeltaReceiptV1`, `no_augmentation_receipt`, and `hold_receipt`.

- [ ] **Step 1: Write failing canonical and authority tests**

```python
def test_no_augmentation_is_successful_and_grants_no_authority() -> None:
    receipt = no_augmentation_receipt(
        module_id="temporal_sensory_ledger",
        exact_scope="P1/BLIND-A/DEPTH/60-1800s",
        input_sha256="a" * 64,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    assert receipt.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert receipt.next_action is None
    assert set(receipt.authority.values()) == {False}
    assert EvidenceDeltaReceiptV1.from_dict(receipt.as_dict()).receipt_sha256 == receipt.receipt_sha256
```

Also test unknown fields, nonfinite numbers, duplicate reason codes, multiple decision deltas, and any true authority flag.

- [ ] **Step 2: Run the red test**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-augmentation-red'
& $pythonExe -m pytest tests/test_evidence_augmentation.py -q -p no:cacheprovider --basetemp $testRoot
```

Expected: collection fails because `engine.evidence.augmentation` does not exist.

- [ ] **Step 3: Implement the receipt and one-delta invariant**

```python
class EvidenceAugmentationState(str, Enum):
    AUGMENT = "AUGMENT"
    NO_AUGMENTATION = "NO_AUGMENTATION"
    HOLD = "HOLD"


@dataclass(frozen=True, slots=True)
class DecisionDeltaV1:
    delta_id: str
    decision_effect: str
    observed_facts: tuple[str, ...]
    derived_calculations: tuple[str, ...]
    hypotheses: tuple[str, ...]
    forbidden_inferences: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceDeltaReceiptV1:
    module_id: str
    exact_scope: str
    state: EvidenceAugmentationState
    input_sha256: str
    evidence_sha256: str
    policy_sha256: str
    source_binding_sha256: tuple[str, ...]
    reason_codes: tuple[str, ...]
    delta: DecisionDeltaV1 | None
    blockers: tuple[str, ...]
    next_action: str | None
```

Enforce `delta is not None` only for `AUGMENT`, `delta is None` for the other states, and at most one `next_action`. Include canonical schema/version/output hash and the exact all-false authority mapping.

- [ ] **Step 4: Add a versioned SolForge transport field without breaking V1 packets**

Add optional `evidence_delta_receipt` to new V2 packet constructors in `engine/solforge/contracts.py`; leave every V1 `from_dict` closed schema unchanged. Tests must prove old frozen V1 packet bytes and hashes remain unchanged.

- [ ] **Step 5: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-augmentation-green'
& $pythonExe -m pytest tests/test_evidence_augmentation.py tests/test_solforge_contracts.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/evidence/augmentation.py engine/solforge/contracts.py tests/test_evidence_augmentation.py tests/test_solforge_contracts.py
git diff --check
git add -- engine/evidence/augmentation.py tests/test_evidence_augmentation.py engine/solforge/contracts.py tests/test_solforge_contracts.py
git commit -m "feat(evidence): add conditional augmentation receipt"
```

### Task 3: Rebuild Architectural Delta comparison closure and abstention

**Files:**
- Modify: `engine/perception/architectural_delta.py`
- Modify: `engine/solforge/adapters.py`
- Modify: `tests/test_architectural_delta.py`
- Modify: `tests/test_solforge_architectural_adapter.py`

**Interfaces:**
- Consumes: `EvidenceDeltaReceiptV1`, V5 inventory workbook/catalog, existing `ArchitecturalDeltaRequest`, and n-ary contracts.
- Produces: `ComparisonClosureV1`, `ArchitecturalEvidenceDeltaResultV2`, and `evaluate_architectural_evidence_delta` while retaining `evaluate_architectural_delta`.

- [ ] **Step 1: Write failing closure and abstention tests**

```python
def test_complete_architectural_question_emits_no_augmentation(v5_paths) -> None:
    result = evaluate_architectural_evidence_delta(
        complete_no_change_request(),
        inventory_catalog_path=v5_paths.catalog,
        inventory_workbook_path=v5_paths.workbook,
    )
    assert result.receipt.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert result.receipt.next_action is None


def test_neroli_primary_vs_support_holds_total_citrus_constant(v5_paths) -> None:
    result = evaluate_architectural_evidence_delta(
        neroli_role_request(),
        inventory_catalog_path=v5_paths.catalog,
        inventory_workbook_path=v5_paths.workbook,
    )
    closure = result.comparison_closure
    assert closure.rejected_alternative == "NEROLI_PRIMARY"
    assert closure.compliant_treatment == "NEROLI_SUPPORT_ONLY"
    assert "TOTAL_CITRUS_DOSE" in closure.constant_constraints
    assert closure.primary_endpoints == ("BITTER_PEEL_IDENTITY", "ORANGE_BLOSSOM_DRIFT")
```

Add tests for unsupported `unique`, count traps, redundant additions, exact target versus inventory, all inventory statuses, Ambrettolide design/procurement split, Ethylene Brassylate missing, sparse musk, exception-only musks, and complete n-ary arms.

- [ ] **Step 2: Run the architectural red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-architectural-v2-red'
& $pythonExe -m pytest tests/test_architectural_delta.py tests/test_solforge_architectural_adapter.py -q -p no:cacheprovider --basetemp $testRoot
```

Expected: new V2 symbols or assertions fail while existing V1 tests remain green.

- [ ] **Step 3: Add `ComparisonClosureV1` and candidate evidence strength**

```python
@dataclass(frozen=True, slots=True)
class ComparisonClosureV1:
    rejected_alternative: str
    compliant_treatment: str
    primary_endpoints: tuple[str, ...]
    failure_endpoints: tuple[str, ...]
    changed_factor: str
    constant_constraints: tuple[str, ...]
    blinding_rule: str
    order_rule: str
    time_windows: tuple[str, ...]
    accept_rule: str
    reject_rule: str
```

Add optional closure fields to `ArchitecturalDeltaCandidate` with defaults so old construction remains valid. Add an explicit `uniqueness_evidence_refs`; the word `unique` in target role or nonredundancy text without those refs causes `HOLD`.

- [ ] **Step 4: Implement V2 disposition**

`evaluate_architectural_evidence_delta` calls the existing evaluator, then:

- returns `NO_AUGMENTATION/NO_TARGET_DEFICIENCY` for valid no-change;
- returns `HOLD` for inventory/provenance/policy/closure failures;
- returns `AUGMENT` only for one eligible intervention whose closure names the rejected alternative, endpoints, factor, constant-total constraints, and exact decision rules.

For Neroli role comparisons, require direct `PRIMARY` versus `SUPPORT_ONLY` arms and constant total citrus dose. For musks, default to zero/one; layering requires distinct functions and complete nonredundancy/factorial evidence.

Preserve the target-first material policy explicitly: zero citrus is valid; Neroli 10% is support-only unless orange blossom/neroli is central; Habanolide and Romandolide are expected owned; Ambrettolide 10% is computationally design-available but procurement-pending; Ethylene Brassylate is missing unless the execution-time V5 refresh proves otherwise. Keep Tonalide, Macrolide, and Musk Ketone out unless an explicit target-linked exception is declared and isolated. These are policy assertions around the freshly parsed workbook, never a hardcoded replacement inventory.

- [ ] **Step 5: Update the SolForge adapter**

Add `compile_architectural_delta_v2(case, hypotheses, ...) -> ArchitecturalEvidenceDeltaResultV2`. Export only the receipt delta to Sol when state is `AUGMENT`; preserve `NO_AUGMENTATION` and `HOLD` reason codes in the decision receipt without verbose card prose.

- [ ] **Step 6: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-architectural-v2-green'
& $pythonExe -m pytest tests/test_architectural_delta.py tests/test_solforge_architectural_adapter.py tests/test_complexity_inventory.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/perception/architectural_delta.py engine/solforge/adapters.py tests/test_architectural_delta.py tests/test_solforge_architectural_adapter.py
git diff --check
git add -- engine/perception/architectural_delta.py engine/solforge/adapters.py tests/test_architectural_delta.py tests/test_solforge_architectural_adapter.py
git commit -m "feat(perception): close architectural evidence deltas"
```

### Task 4: Rebuild Temporal Ledger as an evidence-sufficiency auditor

**Files:**
- Modify: `engine/sensory/ledger.py`
- Modify: `engine/solforge/adapters.py`
- Modify: `tests/test_temporal_sensory_evidence.py`
- Modify: `tests/test_solforge_evidence_adapters.py`

**Interfaces:**
- Consumes: `TemporalEvidenceRequest`, `TemporalEvidenceResult`, and `EvidenceDeltaReceiptV1`.
- Produces: `TemporalEvidenceDisposition`, `TemporalEvidenceAuditResultV2`, and `audit_temporal_evidence`.

- [ ] **Step 1: Write failing state and zero-next-test tests**

```python
def test_complete_matched_timepoints_are_resolved_without_new_test() -> None:
    audit = audit_temporal_evidence(complete_transition_request())
    assert audit.disposition is TemporalEvidenceDisposition.RESOLVED
    assert audit.receipt.state is EvidenceAugmentationState.AUGMENT
    assert audit.receipt.next_action is None
    assert audit.next_discriminator is None


def test_duplicate_cell_audits_provenance_before_remeasurement() -> None:
    audit = audit_temporal_evidence(conflicted_duplicate_request())
    assert audit.disposition is TemporalEvidenceDisposition.CONFLICTED
    assert audit.receipt.state is EvidenceAugmentationState.HOLD
    assert audit.next_discriminator == "AUDIT_PROVENANCE:protocol/sample/assessor/repeat/timepoint/endpoint"
```

Add tests for an exact missing cell, invalid schedule, order imbalance, unqualified within-sniff timing, adverse-event hold, repeatability hold, insufficient requested scope, and export round trip.

- [ ] **Step 2: Run the temporal red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-temporal-v2-red'
& $pythonExe -m pytest tests/test_temporal_sensory_evidence.py tests/test_solforge_evidence_adapters.py -q -p no:cacheprovider --basetemp $testRoot
```

Expected: new disposition symbols fail while V1 compatibility assertions continue to pass.

- [ ] **Step 3: Implement the five-state audit**

```python
class TemporalEvidenceDisposition(str, Enum):
    RESOLVED = "RESOLVED"
    INCOMPLETE = "INCOMPLETE"
    CONFLICTED = "CONFLICTED"
    PROTOCOL_HOLD = "PROTOCOL_HOLD"
    INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"
```

`audit_temporal_evidence` wraps the existing observed-only analysis. It excludes duplicate canonical cells from dependent summaries, preserves every source row, emits exactly one missing cell for `INCOMPLETE`, and emits provenance audit before remeasurement for `CONFLICTED`.

- [ ] **Step 4: Remove blanket next-comparison behavior in the V2 path**

For `RESOLVED`, compute the requested medians, dispersion, disagreement, repeatability, and paired transitions and set `next_discriminator=None`. Disagreement alone does not force a repeat unless the frozen protocol declares a decision threshold that remains unresolved.

- [ ] **Step 5: Update SolForge temporal packet construction**

Add a V2 adapter mapping all five dispositions and the augmentation receipt. The existing V1 mapping of `COMPLETE/INCOMPLETE/HOLD` remains unchanged for historical replay.

Keep Williams scheduling as an internal randomized-order design utility and test its schedule-hash binding; do not expose it as an admitted complexity module. Admit within-sniff timing only when apparatus identity, clock source, timing tolerance, and qualification evidence are present.

- [ ] **Step 6: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-temporal-v2-green'
& $pythonExe -m pytest tests/test_temporal_sensory_evidence.py tests/test_solforge_evidence_adapters.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/sensory/ledger.py engine/solforge/adapters.py tests/test_temporal_sensory_evidence.py tests/test_solforge_evidence_adapters.py
git diff --check
git add -- engine/sensory/ledger.py engine/solforge/adapters.py tests/test_temporal_sensory_evidence.py tests/test_solforge_evidence_adapters.py
git commit -m "feat(sensory): audit temporal evidence sufficiency"
```

### Task 5: Add explicit preference outcomes and deterministic Davidson fitting

**Files:**
- Create: `engine/preference_davidson.py`
- Create: `tests/test_preference_davidson.py`
- Modify: `engine/preference.py`
- Modify: `tests/test_preference.py`
- Modify: `tests/test_scoped_preference.py`

**Interfaces:**
- Consumes: backward-compatible `PairwisePreference` rows.
- Produces: `PreferenceOutcome`, `DavidsonFitConfig`, `DavidsonFitReceipt`, `fit_davidson`, and V2 fields on `PreferenceFitRequest`/`PreferenceFitResult`.

- [ ] **Step 1: Write failing backward-compatibility and outcome tests**

```python
def test_three_argument_preference_constructor_maps_none_to_legacy_no_preference() -> None:
    row = PairwisePreference("A", "B", None)
    assert row.outcome is PreferenceOutcome.NO_PREFERENCE
    assert row.legacy_outcome_semantics is True


def test_ties_participate_in_davidson_likelihood() -> None:
    fit = fit_davidson(
        items=("A", "B"),
        comparisons=balanced_rows_with_ties(),
        config=DavidsonFitConfig(regularization=0.1, maximum_iterations=200),
    )
    assert fit.tie_parameter > 0
    assert abs(sum(fit.utilities.values())) < 1e-10
    assert fit.converged
```

Also test `NO_PERCEPTIBLE_DIFFERENCE`, `CANNOT_JUDGE`, `PROTOCOL_ABORT`, mixed criteria, missing assessor identity, and exact round trips.

- [ ] **Step 2: Run the preference red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-davidson-red'
& $pythonExe -m pytest tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py -q -p no:cacheprovider --basetemp $testRoot
```

Expected: missing Davidson symbols and outcome fields fail.

- [ ] **Step 3: Extend `PairwisePreference` without changing positional construction**

```python
class PreferenceOutcome(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NO_PREFERENCE = "NO_PREFERENCE"
    NO_PERCEPTIBLE_DIFFERENCE = "NO_PERCEPTIBLE_DIFFERENCE"
    CANNOT_JUDGE = "CANNOT_JUDGE"
    PROTOCOL_ABORT = "PROTOCOL_ABORT"
```

Append optional fields after existing fields: `outcome`, `session_id`, `matrix_id`, `time_window_id`, `previous_presented_item`, `position_in_session`, `protocol_sha256`, and `sample_sha256`. Derive `LEFT/RIGHT/NO_PREFERENCE` from legacy `preferred_item` when `outcome` is absent; reject contradictions when both are provided.

- [ ] **Step 4: Implement the pure-Python Davidson solver**

Use log merits with `sum(u)=0` and `log_nu` for a positive tie parameter. Implement negative penalized log likelihood, analytic gradient, analytic Hessian, deterministic damped Newton steps, fixed starting point, backtracking schedule, gradient tolerance, finite-value checks, and convergence receipt.

```python
@dataclass(frozen=True, slots=True)
class DavidsonFitReceipt:
    utilities: dict[str, float]
    tie_parameter: float
    objective_value: float
    iterations: int
    gradient_norm: float
    converged: bool
    convergence_code: str
    parameter_order: tuple[str, ...]
```

Tie rows enter the likelihood. `CANNOT_JUDGE`, `PROTOCOL_ABORT`, and discrimination-only outcomes do not.

- [ ] **Step 5: Add synthetic recovery tests**

Generate fixed-seed two-, three-, and five-item data with known utilities/tie parameter. Assert deterministic bytes, winner direction, tie-parameter recovery tolerance, utility-centering, and failure on separation/boundary/insufficient data.

- [ ] **Step 6: Integrate V2 fitting in `fit_preference_model` behind an explicit model family**

Add `model_family="DAVIDSON_V1"` to new requests while accepting `BRADLEY_TERRY_LEGACY` only for historical replay. New scientific/admission paths must reject the legacy family. Record full convergence fields and pair probabilities in the V2 result.

- [ ] **Step 7: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-davidson-green'
& $pythonExe -m pytest tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/preference.py engine/preference_davidson.py tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py
git diff --check
git add -- engine/preference.py engine/preference_davidson.py tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py
git commit -m "feat(preference): fit deterministic Davidson ties"
```

### Task 6: Add clustered uncertainty, proper validation, transitivity, and one-pair selection

**Files:**
- Create: `engine/preference_validation.py`
- Create: `tests/test_preference_validation.py`
- Modify: `engine/preference.py`
- Modify: `tests/test_scoped_preference.py`

**Interfaces:**
- Consumes: `DavidsonFitReceipt`, scoped comparison rows, frozen split configuration, and eligible pair constraints.
- Produces: `ClusterBootstrapReceipt`, `HeldoutValidationReceipt`, `TransitivityReceipt`, `NextPairReceipt`, `cluster_bootstrap`, `validate_heldout`, `assess_transitivity`, and `select_next_pair`.

- [ ] **Step 1: Write failing cluster/bootstrap and validation tests**

```python
def test_missing_assessor_ids_never_fall_back_to_row_bootstrap() -> None:
    with pytest.raises(ValueError, match="assessor identity"):
        cluster_bootstrap(rows_with_missing_assessor(), config=bootstrap_config())


def test_disconnected_graph_selects_one_lexicographic_best_bridge() -> None:
    receipt = select_next_pair(
        fitted=two_component_fit(),
        eligible_pairs=(("A", "C"), ("A", "D"), ("B", "C"), ("B", "D")),
        constraints=balanced_constraints(),
    )
    assert receipt.selected_pair == ("A", "C")
    assert receipt.reason_code == "CONNECTIVITY_FIRST"
```

Add tests for deterministic bootstrap, failed/boundary replicates, leave-one-assessor influence, subgroup reversal, temporal crossover, multinomial log loss, Brier score, calibration, grouped split leakage, baseline lower-bound failure, frozen-test exclusion, exposure limits, order balance, carryover risk, exploration quota, and no-next-pair when resolved.

- [ ] **Step 2: Run the validation red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-preference-validation-red'
& $pythonExe -m pytest tests/test_preference_validation.py tests/test_scoped_preference.py -q -p no:cacheprovider --basetemp $testRoot
```

- [ ] **Step 3: Implement assessor-cluster resampling**

Use `random.Random(seed)`. Sort assessor IDs and rows canonically before sampling. Preserve every chosen assessor's sessions, ties, order, predecessor, and time rows; support optional nested session resampling only when explicitly configured. Record failed/boundary fits, effective unique assessors, graph support, interval method, seed, and leave-one-assessor stability.

- [ ] **Step 4: Implement grouped held-out proper scoring**

```python
@dataclass(frozen=True, slots=True)
class HeldoutValidationReceipt:
    split_unit: str
    heldout_count: int
    multinomial_log_loss: float
    brier_score: float
    calibration_intercept: float | None
    calibration_slope: float | None
    baseline_log_loss: float
    paired_gain_interval: tuple[float, float]
    practical_margin: float
    passed: bool
    leakage_codes: tuple[str, ...]
```

Model selection, regularization, knots, and active selection stay inside training. Validation passes only when the lower gain bound exceeds the declared practical margin.

- [ ] **Step 5: Implement transitivity and temporal diagnostics**

Return `NONTRANSITIVE_OR_MISSPECIFIED` when stable cycles exceed the frozen tolerance. Report window-specific pair and tie probabilities; withhold a global winner when a practically important crossover is hidden.

- [ ] **Step 6: Implement constrained one-pair selection**

Score only eligible pairs using deterministic uncertainty reduction proxy, connectivity gain, order/exposure balance, burden, and carryover risk. Use connectivity-first before uncertainty sampling and a frozen exploration quota. Return `None` when the declared decision is resolved.

- [ ] **Step 7: Integrate V2 result fields and run tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-preference-validation-green'
& $pythonExe -m pytest tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py tests/test_preference_validation.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/preference.py engine/preference_validation.py tests/test_preference_validation.py tests/test_scoped_preference.py
git diff --check
git add -- engine/preference.py engine/preference_validation.py tests/test_preference_validation.py tests/test_scoped_preference.py
git commit -m "feat(preference): validate clustered scoped evidence"
```

### Task 7: Rebuild the hedonic gate and SolForge preference adapter

**Files:**
- Modify: `engine/hedonic_evidence.py`
- Modify: `engine/solforge/adapters.py`
- Modify: `engine/solforge/contracts.py`
- Modify: `tests/test_hedonic_evidence_gate_v2.py`
- Modify: `tests/test_solforge_evidence_adapters.py`
- Modify: `tests/test_solforge_contracts.py`

**Interfaces:**
- Consumes: V2 preference fit, validation, and augmentation receipts.
- Produces: `PreferenceFitEvidenceReceiptV2`, `CriterionFitPacketV2`, and `build_criterion_fit_packet_v2`.

- [ ] **Step 1: Write failing exact-scope gate tests**

Test that `VALIDATED_EXACT_SCOPE` requires Davidson fitting, assessor IDs, isolated `LIKING`, grouped held-out proper scoring, lower-bound practical gain, stable clustered uncertainty, balanced/estimated order, no concealed temporal crossover, and a valid source-transfer binding. Test that depth/richness/fidelity data cannot enter the liking gate.

```python
def test_accuracy_only_fit_cannot_validate_liking() -> None:
    result = evaluate_hedonic_evidence(v1_accuracy_only_receipt())
    assert result.state is HedonicEvidenceState.FAILED_HELDOUT_BASELINE
    assert "PROPER_SCORING_REQUIRED" in result.blockers
```

- [ ] **Step 2: Run the gate red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-hedonic-v2-red'
& $pythonExe -m pytest tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py tests/test_solforge_contracts.py -q -p no:cacheprovider --basetemp $testRoot
```

- [ ] **Step 3: Add V2 evidence and criterion packets**

V2 binds formula/build, sample, protocol, criterion wording, construct registry, assessor/session/repeat, matrix, exposure, time window, order/predecessor, tie semantics, Davidson fit, clustered intervals, influence, transitivity, proper scoring, calibration, active-pair receipt, source-transfer bindings, and all-false authority.

- [ ] **Step 4: Update exact-scope gate mapping**

Map failed source transfer, criterion mix, order/carryover, model fit, bootstrap, transitivity, temporal, leakage, and held-out margin to explicit `INVALID_OR_CONFOUNDED`, `INSUFFICIENT_EVIDENCE`, `DIAGNOSTIC`, or `FAILED_HELDOUT_BASELINE`. Only complete evidence produces `VALIDATED_EXACT_SCOPE`.

- [ ] **Step 5: Update SolForge adapter output restraint**

The treatment packet includes only exact calculations, holds, and the selected pair. It must not repeat generic safeguards already present in the common prompt. A correct obvious order-confound may emit `NO_AUGMENTATION` when no additional calculation or schedule is needed.

- [ ] **Step 6: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-hedonic-v2-green'
& $pythonExe -m pytest tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py tests/test_solforge_contracts.py tests/test_legacy_hedonic_runtime_isolation.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/hedonic_evidence.py engine/solforge/adapters.py engine/solforge/contracts.py tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py
git diff --check
git add -- engine/hedonic_evidence.py engine/solforge/adapters.py engine/solforge/contracts.py tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py tests/test_solforge_contracts.py
git commit -m "feat(solforge): bind hedonic evidence augmentation"
```

### Task 8: Add nonruntime V4 registry and integrated augmentation routing

**Files:**
- Create: `configs/complexity/complexity_module_registry_v4.json`
- Modify: `engine/perception/complexity_registry.py`
- Modify: `engine/solforge/orchestrator.py`
- Modify: `tests/test_complexity_registry_v3.py`
- Create: `tests/test_complexity_registry_v4.py`
- Modify: `tests/test_solforge_orchestrator.py`
- Modify: `tests/test_solforge_runtime_isolation.py`

**Interfaces:**
- Consumes: V3 registry chain and three V2 module receipts.
- Produces: V4 overlay parsing and an orchestrator route that forwards only `AUGMENT` deltas while preserving `NO_AUGMENTATION`/`HOLD` receipts.

- [ ] **Step 1: Write failing registry and route tests**

Assert V1/V2/V3 hashes remain exact, V4 base chain is exact, rebuilt entries have `FUTURE_CANDIDATE_NOT_VALIDATED`, `import_path=null`, source hashes match current files, and retired cards remain unreachable. Assert a no-augmentation case produces no module prose but retains its receipt hash.

- [ ] **Step 2: Run the routing red tests**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-registry-v4-red'
& $pythonExe -m pytest tests/test_complexity_registry_v3.py tests/test_complexity_registry_v4.py tests/test_solforge_orchestrator.py tests/test_solforge_runtime_isolation.py -q -p no:cacheprovider --basetemp $testRoot
```

- [ ] **Step 3: Implement V4 overlay parsing**

Follow the existing V3 loader pattern with a closed top-level schema, exact parent-registry hashes, exact source hashes, and no import path for unadmitted rebuilds. Do not mutate existing registry files.

- [ ] **Step 4: Implement conditional orchestration**

The orchestrator records all receipts but places only the single `DecisionDeltaV1` from `AUGMENT` into the Sol-facing packet. `NO_AUGMENTATION` contributes zero advisory text. `HOLD` contributes stable blockers and forbidden-inference codes only.

- [ ] **Step 5: Run tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-registry-v4-green'
& $pythonExe -m pytest tests/test_complexity_registry_v3.py tests/test_complexity_registry_v4.py tests/test_solforge_orchestrator.py tests/test_solforge_runtime_isolation.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/perception/complexity_registry.py engine/solforge/orchestrator.py tests/test_complexity_registry_v4.py tests/test_solforge_orchestrator.py
git diff --check
git add -- configs/complexity/complexity_module_registry_v4.json engine/perception/complexity_registry.py engine/solforge/orchestrator.py tests/test_complexity_registry_v3.py tests/test_complexity_registry_v4.py tests/test_solforge_orchestrator.py tests/test_solforge_runtime_isolation.py
git commit -m "feat(solforge): route nonruntime evidence deltas"
```

### Task 9: Build the synthetic recovery and falsification suite

**Files:**
- Create: `tests/science/test_complexity_evidence_recovery.py`
- Create: `tests/science/test_preference_model_recovery.py`
- Create: `tests/science/test_augmentation_falsification.py`
- Create: `data/benchmarks/solforge/rebuild_science_v1/manifest.json`

**Interfaces:**
- Consumes: all rebuilt module APIs and frozen deterministic generators.
- Produces: a hash-bound provider-free science manifest and pass/fail metrics required before external benchmarking.

- [ ] **Step 1: Write fixed-seed synthetic generators and recovery thresholds**

Generate Davidson ties, assessor clusters, order effects, predecessor effects, temporal crossovers, latent subgroup reversals, disconnected graphs, and nontransitive matrices. Freeze seeds and expected tolerances in the manifest.

- [ ] **Step 2: Add architectural and temporal falsification cases**

Cover count inflation, redundant addition, target/inventory inversion, unsupported uniqueness, incomplete n-ary arms, Neroli role, musk exceptions, resolved/no-next-test, missing exact cell, conflicted duplicate, order imbalance, and unqualified within-sniff timing.

- [ ] **Step 3: Add preference falsification cases**

Cover label permutation, tie injection, row-versus-cluster interval reversal, one-assessor influence, temporal aggregate reversal, carryover comparable to item contrast, leakage, poor calibration, active policy worse than balanced random, and OAV/narrative ablation.

- [ ] **Step 4: Define noncompensatory provider-free gates**

Require exact deterministic bytes, no false winner in null simulations above the declared tolerance, interval coverage within frozen bounds, no missed critical holds, correct zero-next-action behavior, and all authority flags false. Any failure blocks Task 10.

- [ ] **Step 5: Run science tests and commit**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-rebuild-science-green'
& $pythonExe -m pytest tests/science/test_complexity_evidence_recovery.py tests/science/test_preference_model_recovery.py tests/science/test_augmentation_falsification.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check tests/science/test_complexity_evidence_recovery.py tests/science/test_preference_model_recovery.py tests/science/test_augmentation_falsification.py
git diff --check
git add -- tests/science/test_complexity_evidence_recovery.py tests/science/test_preference_model_recovery.py tests/science/test_augmentation_falsification.py data/benchmarks/solforge/rebuild_science_v1/manifest.json
git commit -m "test(solforge): freeze rebuild science gates"
```

### Task 10: Freeze the V4 blinded benchmark corpus and scorer

**Files:**
- Create: `tests/fixtures/complexity_replacement_benchmark_cases_v4.json`
- Create: `tests/fixtures/complexity_replacement_benchmark_cases_v4.sha256`
- Modify: `engine/perception/complexity_replacement_benchmark.py`
- Modify: `tests/test_complexity_replacement_benchmark.py`
- Modify: `tests/test_complexity_module_retest.py`

**Interfaces:**
- Consumes: V4 module receipts and the existing three-arm screen/confirmation machinery.
- Produces: V4 corpus loading, objective receipt scoring, abstention scoring, and unchanged 2/3 screen plus 4/6 admission thresholds.

- [ ] **Step 1: Write failing V4 corpus tests**

Require exactly six cases per module: three screen and three unseen confirmation, including positive, safe-countercase, and critical-trap roles. Require at least one `NO_AUGMENTATION` success case per module and one nontrivial deterministic-calculation case per module.

- [ ] **Step 2: Author Architectural Delta cases**

Include unsupported uniqueness/bridge evidence, complete no-change, Neroli support-versus-primary at constant total citrus, sparse musk, exception-only musk, and unseen inventory mismatch.

- [ ] **Step 3: Author Temporal Ledger cases**

Include a resolved transition requiring no new comparison, one exact missing cell, duplicate conflict requiring provenance-first audit, order/carryover hold, temporal scope mismatch, and an unseen within-sniff qualification trap.

- [ ] **Step 4: Author Hedonic Preference cases**

Include validated exact-scope probabilities/intervals with one next pair, disconnected graph requiring one bridge, obvious order-confound/no augmentation, ties and no-difference semantics, temporal crossover, and unseen held-out calibration/leakage failure.

- [ ] **Step 5: Extend scorer and receipt validation**

Primary machine-scored fields are decision state, reason codes, exact calculations, one-next-action limit, tie semantics, split/cluster/temporal correctness, and authority. Narrative scoring remains secondary. A correct `NO_AUGMENTATION` receives full experimental-efficiency credit; empty output without a receipt does not.

- [ ] **Step 6: Run corpus/scorer tests and freeze the sidecar**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-replacement-v4-green'
& $pythonExe -m pytest tests/test_complexity_replacement_benchmark.py tests/test_complexity_module_retest.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/perception/complexity_replacement_benchmark.py tests/test_complexity_replacement_benchmark.py tests/test_complexity_module_retest.py
git diff --check
```

Expected: corpus bytes and sidecar match; all historical corpus and receipt tests remain unchanged.

- [ ] **Step 7: Commit Task 10**

```powershell
git add -- tests/fixtures/complexity_replacement_benchmark_cases_v4.json tests/fixtures/complexity_replacement_benchmark_cases_v4.sha256 engine/perception/complexity_replacement_benchmark.py tests/test_complexity_replacement_benchmark.py tests/test_complexity_module_retest.py
git commit -m "test(solforge): freeze evidence augmentation benchmark"
```

### Task 11: Run screen, confirmation, admission, and GitHub handoff

**Files:**
- Create during execution: `data/benchmarks/solforge/evidence_augmentation_v1/`
- Create after terminal decision: `data/governance/solforge_evidence_augmentation_status_20260826.json`
- Modify only after a passing admission: `configs/complexity/complexity_module_registry_v4.json`
- Modify only after a passing admission: `tests/test_complexity_registry_v4.py`

**Interfaces:**
- Consumes: frozen V4 corpus/scorer, science manifest, V4 registry, and fresh model outputs.
- Produces: exact screen/confirmation manifests, raw outputs, blind judgments, receipts, terminal module decisions, and a reviewable GitHub branch.

- [ ] **Step 1: Verify the complete provider-free preflight**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-evidence-admission-preflight'
& $pythonExe -m pytest tests/test_evidence_augmentation.py tests/test_architectural_delta.py tests/test_temporal_sensory_evidence.py tests/test_preference.py tests/test_scoped_preference.py tests/test_preference_davidson.py tests/test_preference_validation.py tests/test_hedonic_evidence_gate_v2.py tests/test_solforge_evidence_adapters.py tests/test_complexity_registry_v4.py tests/test_complexity_replacement_benchmark.py tests/science/test_complexity_evidence_recovery.py tests/science/test_preference_model_recovery.py tests/science/test_augmentation_falsification.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/evidence/augmentation.py engine/perception/architectural_delta.py engine/sensory/ledger.py engine/preference.py engine/preference_davidson.py engine/preference_validation.py engine/hedonic_evidence.py engine/solforge
git diff --check
```

Expected: all checks pass. Any failure blocks external requests.

- [ ] **Step 2: Freeze the screen manifest before generation**

Use fresh projectless GPT-5.6 Sol Ultra conversations for all three arms and judges. If the product exposes Fast execution, enable it for every arm and record it; otherwise record `FAST_MODE_NOT_EXPOSED`. Freeze model, effort, tools, common input, treatment receipt, placebo bytes, arm order, prompts, nonce, and hashes before dispatch.

- [ ] **Step 3: Generate and freeze all screen outputs**

Run the three new screen cases per module against:

1. plain Sol Ultra;
2. length-matched governance/no-op control; and
3. the rebuilt deterministic receipt.

Use new conversations; do not resume the historical 27 requests. Resolve every request by stable conversation/task ID before retrying. Freeze exact output bytes and hashes.

- [ ] **Step 4: Blind, judge, and apply the screen gate**

Require at least 2/3 treatment wins against each control and zero critical regressions for each module. Score deterministic gate correctness before narrative quality. Stop a failing module; do not send its confirmation cases.

- [ ] **Step 5: Run unseen confirmation only for screen passers**

Freeze a confirmation manifest bound to the validated screen receipt. Run three unseen cases per surviving module with identical model/effort/Fast/tool settings and fresh contexts. Preserve failures and partial results.

- [ ] **Step 6: Apply final admission**

Require at least 4/6 wins, median paired gain at least five points against both controls, zero critical errors, byte-reproducible receipts, passed science recovery/calibration, no high-risk-stratum regression, and justified cost/latency. A failed module remains runtime unreachable and becomes a provenance tombstone.

- [ ] **Step 7: Update V4 registry only for proven winners**

Passing modules may receive an admitted import path at the exact validated scope. Failing modules retain `import_path=null` and `RETIRED_BENCHMARK_UNDERPERFORMER_REBUILD_REQUIRED` or `PROVENANCE_TOMBSTONE`. No physical or release authority changes.

- [ ] **Step 8: Run final verification and commit terminal evidence**

```powershell
$pythonExe = 'D:\chatbots\perfume-chem\.venv\Scripts\python.exe'
$testRoot = 'C:\Users\ASUS\AppData\Local\Temp\perfume-chem-evidence-admission-final'
& $pythonExe -m pytest tests/test_complexity_registry_v4.py tests/test_solforge_runtime_isolation.py tests/test_complexity_replacement_benchmark.py tests/test_complexity_module_retest.py tests/test_solforge_candidate_status.py -q -p no:cacheprovider --basetemp $testRoot
& $pythonExe -m ruff check engine/perception/complexity_replacement_benchmark.py tests/test_complexity_registry_v4.py
git diff --check
git add -- data/benchmarks/solforge/evidence_augmentation_v1 data/governance/solforge_evidence_augmentation_status_20260826.json configs/complexity/complexity_module_registry_v4.json tests/test_complexity_registry_v4.py
git commit -m "bench(solforge): freeze evidence augmentation admission"
```

- [ ] **Step 9: Publish the reviewed branch without merging**

```powershell
git status --short
git log --oneline --decorate --max-count 25
git push -u origin codex/complex-perfumery-integration
```

Create or update a GitHub pull request only after reviewing the committed scope for secrets, raw chats, protected workbook bytes, and unrelated files. State exact module dispositions, benchmark gains, science gates, authority ceiling, and remaining physical-evidence requirements. Do not force-push or merge automatically.

## Completion criteria

- The V2 evidence ledger and construct registry validate and are hash-frozen.
- Every operative code behavior is bound to a primary/authoritative source and transfer assessment.
- All three modules emit `AUGMENT`, `NO_AUGMENTATION`, or `HOLD` through one shared canonical receipt.
- Architectural Delta produces zero/one closed comparison and preserves all citrus/musk/inventory constraints.
- Temporal Ledger distinguishes resolved, incomplete, conflicted, protocol hold, and insufficient scope without interpolation or redundant experiments.
- Preference uses explicit outcomes, Davidson ties, assessor-cluster uncertainty, proper held-out scoring, temporal/order diagnostics, transitivity holds, and zero/one next pair.
- Existing V1 APIs and frozen historical bytes remain compatible.
- Provider-free recovery/falsification gates pass before any external request.
- The new 3+3 benchmark is fresh, blinded, hash-frozen, and compares identical Sol Ultra/Fast settings across treatment and controls.
- Only modules meeting every noncompensatory threshold become runtime reachable.
- Failed modules remain preserved, hash-bound, and unreachable.
- All physical, sensory, liking, safety, purchase, publication, and release authority remains false.
- The branch is pushed for GitHub review without automatic merge.
