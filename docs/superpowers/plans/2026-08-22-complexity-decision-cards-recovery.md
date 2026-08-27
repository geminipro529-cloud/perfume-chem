# Complexity Decision Cards Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the retired raw complexity prompt projections with ten compact decision-card candidates, benchmark each candidate against normal ChatGPT xhigh, and reactivate only modules that meet the approved retention gate.

**Architecture:** Keep the existing scientific engines unchanged and add a deterministic projection layer that binds each compact card to one native-result hash. Add a separate target-first citrus selector and a module-level retest harness with frozen paired cases, placebo controls, blinded scoring, and recoverable registry transitions. The retired registry states remain controlling until external results pass.

**Tech Stack:** Python 3.12+, frozen dataclasses, `Decimal`, canonical JSON/SHA-256, pytest, Ruff, existing Perfume-Chem complexity registry and xhigh receipt patterns.

**Spec:** `docs/superpowers/specs/2026-08-22-complexity-decision-cards-recovery-design.md`

## Global Constraints

- Work inline in `D:\chatbots\perfume-chem`; Codex subagents are forbidden by project policy.
- Preserve all unrelated dirty-worktree changes and stage only task paths.
- Preserve native scientific engine bytes unless a failing regression proves a native defect.
- Keep all repaired modules runtime-ineligible until their individual external benchmark passes.
- A serialized decision card is at most 1,600 UTF-8 bytes.
- Complexity means identity-linked perceptual depth and richness, not complication or count.
- `HOLD` and `NONE` are valid decisions.
- Tonalide, Macrolide, and Musk Ketone are exception-only.
- Target/ideal architecture precedes current-inventory build selection.
- `DHC_CITRUS_SCORING.txt` never enters runtime imports or benchmark evidence.
- No software or xhigh result creates physical liking, safety, sensory, formula, inventory, compounding, publication, or release authority.

---

### Task 1: Decision-card value object and closed contract

**Files:**
- Create: `engine/perception/complexity_decision_cards.py`
- Create: `tests/test_complexity_decision_cards.py`

**Interfaces:**
- Consumes: a module ID, one native result mapping containing `result_sha256`, and the target identity.
- Produces: `DecisionCard`, `DecisionCardState`, and `build_decision_card(module_id, native_result, target_identity)`.

- [ ] **Step 1: Write the failing contract tests**

```python
def test_decision_card_is_hash_bound_closed_and_bounded() -> None:
    card = DecisionCard(
        module_id="construction_profile",
        decision_kind="TARGET_DEFINING_RELATION",
        state=DecisionCardState.DECIDE,
        decision_question="Which relation creates the target's depth?",
        decisive_evidence=("foreground ownership changes at drydown",),
        preserve="recognizable iris",
        reject="ingredient-count reasoning",
        controlled_comparison="full design versus relation omission",
        claim_ceiling="COMPUTATIONAL_DESIGN_ONLY",
        source_result_sha256="a" * 64,
    )
    assert card.as_dict()["schema_version"] == "complexity_decision_card_v1"
    assert len(card.to_json_bytes()) <= 1600
    assert card.card_sha256 == hashlib.sha256(card.to_json_bytes()).hexdigest()


def test_decision_card_rejects_more_than_three_evidence_facts() -> None:
    with pytest.raises(ValueError, match="at most three"):
        valid_card(decisive_evidence=("a", "b", "c", "d"))
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run: `python -m pytest tests/test_complexity_decision_cards.py -q`

Expected: collection fails because `engine.perception.complexity_decision_cards` does not exist.

- [ ] **Step 3: Implement the closed value object**

```python
class DecisionCardState(str, Enum):
    DECIDE = "DECIDE"
    HOLD = "HOLD"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class DecisionCard:
    module_id: str
    decision_kind: str
    state: DecisionCardState
    decision_question: str
    decisive_evidence: tuple[str, ...]
    preserve: str
    reject: str
    controlled_comparison: str
    claim_ceiling: str
    source_result_sha256: str

    def to_json_bytes(self) -> bytes:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        encoded = payload.encode("utf-8")
        if len(encoded) > 1600:
            raise ValueError("decision card exceeds 1600 UTF-8 bytes")
        return encoded
```

Validate nonblank text, exactly one lowercase SHA-256, one to three decisive facts, and no unknown fields through the dataclass constructor. Compute `card_sha256` from the exact canonical bytes without embedding that hash inside the hashed payload.

- [ ] **Step 4: Run the focused tests and verify green**

Run: `python -m pytest tests/test_complexity_decision_cards.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- engine/perception/complexity_decision_cards.py tests/test_complexity_decision_cards.py
git commit -m "feat(complexity): add bounded decision-card contract"
```

### Task 2: Nine native-result projections

**Files:**
- Modify: `engine/perception/complexity_decision_cards.py`
- Modify: `tests/test_complexity_decision_cards.py`

**Interfaces:**
- Consumes: sealed outputs from the existing construction, expansion, musk, admission, lifecycle, within-sniff, temporal, order-balance, and panel adapters.
- Produces: one compact `DecisionCard` per native module via `build_decision_card`.

- [ ] **Step 1: Add one failing behavior test per projector**

Use literal native-result fixtures and assert decision-changing outputs, not source wording. Include these mutations:

```python
@pytest.mark.parametrize(
    ("module_id", "expected_kind"),
    [
        ("construction_profile", "TARGET_DEFINING_RELATION"),
        ("complexity_expansion", "MINIMUM_NONREDUNDANT_MOVE"),
        ("musk_design_restraint", "STRONGEST_SINGLE_MUSK"),
        ("model_admission", "EXACT_SCOPE_ADMISSION"),
        ("model_lifecycle", "RELEASE_LIFECYCLE_ACTION"),
        ("within_sniff", "APPARATUS_INTERPRETABILITY"),
        ("temporal_observations", "OBSERVED_TIME_CELLS"),
        ("order_balance", "POSITION_CARRYOVER_BALANCE"),
        ("panel_contract", "ESTIMAND_AND_CLAIM_CEILING"),
    ],
)
def test_native_projection_resolves_one_module_specific_decision(
    module_id: str, expected_kind: str
) -> None:
    card = build_decision_card(module_id, native_result(module_id), "target")
    assert card.decision_kind == expected_kind
    assert len(card.decisive_evidence) <= 3
    assert len(card.to_json_bytes()) <= 1600
```

Add separate tests proving: construction ignores row counts; expansion returns `NONE` for a redundant frontier; musk returns `HOLD` for an incomplete exception; admission names the decisive failed gate; lifecycle binds exact release scope; within-sniff holds unqualified observed-effect claims; temporal does not interpolate missing cells; order names first-position or predecessor imbalance; panel keeps pleasantness separate from construction endpoints.

- [ ] **Step 2: Run and verify the unsupported-module failures**

Run: `python -m pytest tests/test_complexity_decision_cards.py -q`

Expected: failures identify missing projector dispatch or incorrect module-specific state.

- [ ] **Step 3: Implement nine private projector functions and dispatch**

```python
_PROJECTORS: dict[str, Callable[[Mapping[str, Any], str], DecisionCard]] = {
    "construction_profile": _construction_card,
    "complexity_expansion": _expansion_card,
    "musk_design_restraint": _musk_card,
    "model_admission": _admission_card,
    "model_lifecycle": _lifecycle_card,
    "within_sniff": _within_sniff_card,
    "temporal_observations": _temporal_card,
    "order_balance": _order_card,
    "panel_contract": _panel_card,
}


def build_decision_card(
    module_id: str,
    native_result: Mapping[str, Any],
    target_identity: str,
) -> DecisionCard:
    projector = _PROJECTORS.get(module_id)
    if projector is None:
        raise ValueError(f"unsupported decision-card module: {module_id}")
    return projector(_closed_native_result(native_result), _text(target_identity))
```

Each projector selects no more than three decisive native facts, maps missing or failed evidence to `HOLD`, and uses one module-specific controlled comparison. It must never include repeated authority booleans or the full native result.

- [ ] **Step 4: Run focused and existing adapter regressions**

Run: `python -m pytest tests/test_complexity_decision_cards.py tests/test_complexity_adapters.py -q`

Expected: all tests pass and existing sealed adapters remain unchanged.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- engine/perception/complexity_decision_cards.py tests/test_complexity_decision_cards.py
git commit -m "feat(complexity): project nine decision-changing cards"
```

### Task 3: Target-first citrus architecture selector

**Files:**
- Create: `engine/perception/citrus_selection.py`
- Create: `tests/test_citrus_selection.py`
- Modify: `engine/perception/complexity_decision_cards.py`
- Modify: `tests/test_complexity_decision_cards.py`

**Interfaces:**
- Produces: `CitrusCandidate`, `CitrusSelectionRequest`, `CitrusSelectionResult`, and `select_citrus_architecture(request)`.
- The decision-card layer consumes `CitrusSelectionResult.as_dict()` under module ID `citrus_selection`.

- [ ] **Step 1: Write failing selector tests**

```python
def test_selects_one_primary_and_one_distinct_bridge_without_count_reward() -> None:
    result = select_citrus_architecture(
        citrus_request(
            primary_role="DRY_BITTER_PRISM",
            support_role="GREEN_AROMATIC_BRIDGE",
            candidates=(
                candidate("Bergamot FCF Oil Sicilian", roles=("DRY_BITTER_PRISM",)),
                candidate("Petitgrain EO Paraguay", roles=("GREEN_AROMATIC_BRIDGE",)),
                candidate("Blood Orange Oil Sicilian", roles=("JUICY_WARM_BODY",)),
            ),
        )
    )
    assert result.target_primary == "Bergamot FCF Oil Sicilian"
    assert result.target_support == "Petitgrain EO Paraguay"


def test_returns_none_when_non_citrus_brightness_already_serves_target() -> None:
    result = select_citrus_architecture(
        citrus_request(citrus_required=False, non_citrus_brightness_satisfies_target=True)
    )
    assert result.state == "NONE"


def test_out_of_stock_red_mandarin_is_not_silently_replaced() -> None:
    result = select_citrus_architecture(
        citrus_request(
            primary_role="JUICY_WARM_CONTINUITY",
            candidates=(
                candidate("Red Mandarin EO", roles=("JUICY_WARM_CONTINUITY",), inventory_state="OUT_OF_STOCK"),
                candidate("Blood Orange Oil Sicilian", roles=("JUICY_WARM_BODY",)),
            ),
        )
    )
    assert result.target_primary == "Red Mandarin EO"
    assert result.current_build_primary is None
    assert result.current_build_state == "HOLD_TARGET_SPECIFIC_GAP"
```

Also test ambiguous strongest-single candidates return `HOLD`, overlapping support is rejected, Cedrat remains non-substitutable, axis conflicts block selection, and no code imports or reads `DHC_CITRUS_SCORING.txt`.

- [ ] **Step 2: Run and verify missing-selector failures**

Run: `python -m pytest tests/test_citrus_selection.py -q`

Expected: collection fails because the selector does not exist.

- [ ] **Step 3: Implement the strict non-scalar selector**

```python
def select_citrus_architecture(request: CitrusSelectionRequest) -> CitrusSelectionResult:
    if not request.citrus_required and request.non_citrus_brightness_satisfies_target:
        return CitrusSelectionResult.none(request)
    primary = tuple(
        item for item in request.candidates
        if request.primary_role in item.roles and not item.axis_conflicts
    )
    if len(primary) != 1:
        return CitrusSelectionResult.hold(request, "STRONGEST_SINGLE_UNRESOLVED")
    support = _distinct_support(request, primary[0])
    return CitrusSelectionResult.from_target_choice(request, primary[0], support)
```

Do not compute a hedonic, complexity, novelty, naturalness, price, frequency, or ingredient-count score. Build current inventory only after the target choice, requiring exact stock reference for owned material.

- [ ] **Step 4: Add and test the citrus decision-card projection**

Run: `python -m pytest tests/test_citrus_selection.py tests/test_complexity_decision_cards.py -q`

Expected: selector and compact citrus card tests pass.

- [ ] **Step 5: Commit Task 3**

```powershell
git add -- engine/perception/citrus_selection.py engine/perception/complexity_decision_cards.py tests/test_citrus_selection.py tests/test_complexity_decision_cards.py
git commit -m "feat(complexity): add target-first citrus selector"
```

### Task 4: Frozen module-level retest corpus and prompt builder

**Files:**
- Create: `engine/perception/complexity_module_retest.py`
- Create: `tests/fixtures/complexity_module_retest_cases_v1.json`
- Create: `tests/fixtures/complexity_module_retest_cases_v1.sha256`
- Create: `tests/test_complexity_module_retest.py`

**Interfaces:**
- Produces: `ModuleRetestCase`, `ModuleRetestArm`, `ModuleRetestRequest`, `load_module_retest_cases`, and `prepare_module_retest_request`.
- Each module has exactly six cases with phases `SCREEN` or `CONFIRM` and roles `POSITIVE`, `SAFE_COUNTERCASE`, `CRITICAL_TRAP`, `INVENTORY_MISMATCH`, `CONTROL`, or `UNSEEN_VARIANT`.

- [ ] **Step 1: Write failing corpus and prompt-isolation tests**

```python
def test_corpus_has_six_role_complete_cases_per_module() -> None:
    cases = load_module_retest_cases(ROOT / FIXTURE)
    by_module = group_cases(cases)
    assert set(by_module) == set(EXPECTED_MODULE_IDS)
    assert all(len(items) == 6 for items in by_module.values())
    assert all({item.phase for item in items} == {"SCREEN", "CONFIRM"} for items in by_module.values())


def test_treatment_diff_is_only_one_card_and_placebo_is_length_matched() -> None:
    control = prepare_module_retest_request(case, ModuleRetestArm.CONTROL, card=None)
    treatment = prepare_module_retest_request(case, ModuleRetestArm.TREATMENT, card=card)
    placebo = prepare_module_retest_request(case, ModuleRetestArm.PLACEBO, card=card)
    assert "decision_card" not in control.prompt_payload
    assert treatment.prompt_payload["decision_card"] == card.as_dict()
    assert abs(placebo.card_byte_count - treatment.card_byte_count) <= 16
    assert placebo.prompt_payload["decision_card"] != card.as_dict()
```

- [ ] **Step 2: Run and verify missing-harness failures**

Run: `python -m pytest tests/test_complexity_module_retest.py -q`

Expected: collection fails because the retest harness does not exist.

- [ ] **Step 3: Implement immutable cases, request hashing, and placebo generation**

Reuse the existing canonical JSON and SHA-256 conventions. The common prompt contains the same target, evidence, inventory state, output contract, and claim ceiling for every arm. Generate placebo text from module-neutral process reminders that contain no module decision, answer, or specialist discriminator.

- [ ] **Step 4: Populate and lock sixty fresh cases**

Create six cases for each of the ten exact module IDs. Change names, values, and surface wording between screening and confirmation. Include the citrus `NONE`, inventory-mismatch, and handoff cases and the musk strongest-single and exception traps. Compute the sidecar as the lowercase SHA-256 of the exact JSON bytes followed by a newline.

- [ ] **Step 5: Run corpus and request tests**

Run: `python -m pytest tests/test_complexity_module_retest.py -q`

Expected: exact case count, role coverage, hash lock, arm isolation, card byte bound, and placebo length checks pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add -- engine/perception/complexity_module_retest.py tests/fixtures/complexity_module_retest_cases_v1.json tests/fixtures/complexity_module_retest_cases_v1.sha256 tests/test_complexity_module_retest.py
git commit -m "feat(complexity): freeze module-level xhigh retest"
```

### Task 5: Blinded scorer, retention gate, and receipt

**Files:**
- Modify: `engine/perception/complexity_module_retest.py`
- Modify: `tests/test_complexity_module_retest.py`

**Interfaces:**
- Produces: `ModulePairScore`, `ModuleRetentionDecision`, `decide_module_retention`, `build_module_retest_receipt`, and `decide_combined_interaction`.

- [ ] **Step 1: Write failing literal-score tests**

```python
def test_four_wins_median_five_no_critical_and_placebo_gain_passes() -> None:
    scores = pair_scores(deltas=(8, 6, 5, 5, 0, -1), wins=4)
    decision = decide_module_retention(scores, placebo_delta=Decimal("3"))
    assert decision.state == "REACTIVATE"


@pytest.mark.parametrize(
    "mutation",
    ["THREE_WINS", "MEDIAN_BELOW_FIVE", "CRITICAL_REGRESSION", "FAILED_COUNTERCASE", "FAILED_TRAP", "PLACEBO_NOT_BEATEN"],
)
def test_each_noncompensatory_failure_retires(mutation: str) -> None:
    assert decide_module_retention(mutated_scores(mutation)).state == "RETIRED_BENCHMARK_UNDERPERFORMER"
```

- [ ] **Step 2: Run and verify gate failures**

Run: `python -m pytest tests/test_complexity_module_retest.py -q`

Expected: failures identify missing retention and receipt functions.

- [ ] **Step 3: Implement deterministic gate and semantic receipt**

Use literal rubric totals from blinded scoring packets. The decision function must require all six conditions, never average away a critical error, and record case hashes, card hashes, response hashes, blinded labels, pair scores, placebo result, telemetry state, and authority-false fields.

- [ ] **Step 4: Run focused scorer tests**

Run: `python -m pytest tests/test_complexity_module_retest.py -q`

Expected: every pass and fail mutation behaves exactly as specified.

- [ ] **Step 5: Commit Task 5**

```powershell
git add -- engine/perception/complexity_module_retest.py tests/test_complexity_module_retest.py
git commit -m "feat(complexity): gate module retest retention"
```

### Task 6: Candidate freeze and provider-free verification

**Files:**
- Modify only if required by census: `configs/complexity/complexity_module_registry_v1.json`
- Create: `data/governance/complexity_decision_card_candidate_freeze_20260822.json`
- Modify: `tests/test_complexity_registry.py`
- Create: `tests/test_complexity_decision_card_freeze.py`

**Interfaces:**
- Candidate receipt records exact source, fixture, spec, plan, and registry hashes while keeping repaired modules retired.

- [ ] **Step 1: Add the failing freeze test**

```python
def test_candidate_freeze_matches_exact_bytes_and_grants_no_runtime_authority() -> None:
    receipt = load_receipt()
    assert_hashes_match(receipt["candidate_artifacts"])
    registry = load_complexity_registry(ROOT, REGISTRY_PATH)
    assert all(not registry.module_by_id(item).runtime_eligible for item in receipt["repaired_module_ids"])
    assert receipt["authority"] == authority_false_contract()
```

- [ ] **Step 2: Run and verify missing-receipt failure**

Run: `python -m pytest tests/test_complexity_decision_card_freeze.py -q`

Expected: fails because the candidate freeze receipt does not exist.

- [ ] **Step 3: Write the exact candidate-freeze receipt and classify new files**

Add the new card and citrus paths to the registry as `FUTURE_CANDIDATE_NOT_VALIDATED` only if the census requires executable-path classification. Do not reactivate any predecessor module.

- [ ] **Step 4: Run complete provider-free focused verification**

Run:

```powershell
python -m pytest tests/test_complexity_decision_cards.py tests/test_citrus_selection.py tests/test_complexity_module_retest.py tests/test_complexity_adapters.py tests/test_complexity_registry.py tests/test_complexity_ensemble.py -q
python -m ruff check engine/perception/complexity_decision_cards.py engine/perception/citrus_selection.py engine/perception/complexity_module_retest.py tests/test_complexity_decision_cards.py tests/test_citrus_selection.py tests/test_complexity_module_retest.py
python -m compileall -q engine/perception
```

Expected: zero failures, zero Ruff findings, successful compilation, and passing registry census.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- configs/complexity/complexity_module_registry_v1.json data/governance/complexity_decision_card_candidate_freeze_20260822.json tests/test_complexity_registry.py tests/test_complexity_decision_card_freeze.py
git commit -m "chore(complexity): freeze repaired card candidates"
```

### Task 7: Execute staged ChatGPT xhigh comparisons

**Files:**
- Create under ignored run root: `output/complexity_module_retest/CMR-20260822-decision-cards-v1/`
- No source changes while scored prompts are running.

**Interfaces:**
- Consumes exact frozen request bytes.
- Produces exact response bytes and execution receipts for control, treatment, and passing-module placebo arms.

- [ ] **Step 1: Prepare screening requests from frozen bytes**

Run the retest preparation operation and verify each request identifies normal ChatGPT 5.6 Sol Extra High, Extra High reasoning, a fresh projectless conversation, exact prompt hash, and a unique nonce.

- [ ] **Step 2: Execute three screening pairs per module**

Use one fresh projectless ChatGPT conversation per request. Capture exact response bytes and observed product/model metadata. Do not expose the paired response, score, expected decision, or arm identity to the responding chat.

- [ ] **Step 3: Validate screening executions**

Reject duplicate nonces, stale context, model/effort mismatch, response-hash mismatch, ambiguous completion, or attachment drift. A module without three valid pairs remains `BENCHMARK_BLOCKED`, not failed.

- [ ] **Step 4: Execute three unseen confirmation pairs for credible screens**

Freeze the confirmation request bytes before opening any confirmation chat. Do not alter cards or rubric after observing screening results.

- [ ] **Step 5: Blind, score, and run placebo comparisons**

Strip arm identity and request IDs before scoring. For each module meeting the six-pair quality gate, execute the prebuilt length-matched placebo comparison and apply the noncompensatory retention rule.

- [ ] **Step 6: Validate the complete external run**

Run the harness validation and score operations. Expected output is one explicit state per module: `REACTIVATE`, `RETIRED_BENCHMARK_UNDERPERFORMER`, or `BENCHMARK_BLOCKED`.

### Task 8: Apply dispositions and test surviving interactions

**Files:**
- Modify: `configs/complexity/complexity_module_registry_v1.json`
- Create: `data/governance/complexity_module_retest_CMR-20260822-decision-cards-v1.json`
- Modify: `tests/test_complexity_registry.py`
- Modify: `tests/test_complexity_benchmark_receipt.py`

**Interfaces:**
- Consumes the validated external run and exact module decisions.
- Produces a registry revision, final semantic receipt, and combined-survivor decision.

- [ ] **Step 1: Write failing registry-transition tests from actual decisions**

For every passing card, assert the predecessor module receives the exact admitted state selected by its role and a current byte hash. For every failure, assert `RETIRED_BENCHMARK_UNDERPERFORMER`, `runtime_eligible is False`, and source preservation. A blocked result must not promote or retire on performance grounds.

- [ ] **Step 2: Run and verify tests fail against the pre-disposition registry**

Run: `python -m pytest tests/test_complexity_registry.py tests/test_complexity_benchmark_receipt.py -q`

Expected: disposition assertions fail until the registry and receipt are updated.

- [ ] **Step 3: Update only evidence-authorized registry states and hashes**

Record the exact external receipt ID and card hash in each transition. Do not modify unrelated module records or activate the legacy DHC citrus scorer.

- [ ] **Step 4: Run the four-arm combined-survivor interaction test**

Compare normal control, best single card, relevant-card bundle, and length-matched placebo bundle. Preserve passing cards individually if the bundle does not beat the best single card.

- [ ] **Step 5: Write the final governance receipt**

Record all case, prompt, response, card, corpus, registry, and source hashes; observed model context; per-module scores; placebo results; interaction decision; preserved paths; zero unauthorized deletions; telemetry state; and all authority ceilings.

- [ ] **Step 6: Run final verification**

Run:

```powershell
python -m pytest tests/test_complexity_decision_cards.py tests/test_citrus_selection.py tests/test_complexity_module_retest.py tests/test_complexity_adapters.py tests/test_complexity_registry.py tests/test_complexity_ensemble.py tests/test_complexity_benchmark_receipt.py -q
python -m ruff check engine/perception/complexity_decision_cards.py engine/perception/citrus_selection.py engine/perception/complexity_module_retest.py tests/test_complexity_decision_cards.py tests/test_citrus_selection.py tests/test_complexity_module_retest.py
python -m compileall -q engine/perception
python scripts/project_verify.py --quick --json
git diff --check
```

Report focused success separately from any pre-existing full-project blocker.

- [ ] **Step 7: Commit final dispositions**

```powershell
git add -- configs/complexity/complexity_module_registry_v1.json data/governance/complexity_module_retest_*.json tests/test_complexity_registry.py tests/test_complexity_benchmark_receipt.py
git commit -m "test(complexity): record module retest dispositions"
```

## Self-review

- Spec coverage: all ten cards, citrus-specific gates, individual six-pair tests, placebo controls, combined interaction, authority ceilings, registry transitions, and preservation are assigned to tasks.
- Placeholder scan: no unfinished implementation markers or unspecified error-handling steps remain.
- Type consistency: `DecisionCard`, `CitrusSelectionResult`, `ModuleRetestCase`, `ModuleRetestRequest`, and `ModuleRetentionDecision` names are stable across producer and consumer tasks.
- Execution choice: project policy forbids the nominal subagent-driven recommendation, so this plan is executed inline with `superpowers:executing-plans`.
