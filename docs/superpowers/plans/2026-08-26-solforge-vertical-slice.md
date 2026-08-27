# SolForge Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, shadow-only SolForge evidence loop that turns one hash-bound Sol hypothesis packet into at most one controlled experiment, validates backend-compatible evidence, and emits a non-authoritative decision receipt for four representative perfumery cases.

**Architecture:** A small state-machine orchestrator coordinates typed contracts, the existing Architectural Delta Engine, the existing Temporal Sensory Ledger, and the existing criterion-specific Preference Learner. Adapters isolate each subsystem. The authoritative V5 inventory is reparsed at execution. Synthetic evidence exists only in test fixtures. No live model adapter, physical execution, runtime ensemble admission, or release action is included.

**Tech Stack:** Python 3.12+, frozen dataclasses, enums, canonical JSON/SHA-256 from Gate Foundation, existing `openpyxl` inventory parser, existing sensory and preference contracts, Pydantic backend schemas, pytest, Ruff, Git.

**Spec:** `docs/superpowers/specs/2026-08-26-solforge-evidence-loop-design.md`

## Required Predecessor

This plan may begin only when `data/governance/solforge_gate_foundation_acceptance_v1.json` exists, validates against current source bytes, and records a passing Gate Foundation suite. A missing, stale, or failed receipt is a hard stop.

## Global Constraints

- Work inline in `C:\Users\ASUS\.codex\worktrees\a7e6\perfume-chem`; project policy forbids Codex subagents.
- Preserve unrelated dirty-worktree changes and stage only task files.
- Use a new Gate Foundation commit as the implementation base; do not implement against a mixed uncommitted gate rewrite.
- Keep target/ideal architecture separate from current-inventory build in every contract and receipt.
- Reparse every nonblank record in the authoritative V5 workbook at execution time and verify its SHA-256 against the inventory authority record.
- Zero change is a first-class result. Ingredient count, verbosity, novelty, prestige, and cost are never complexity evidence.
- Compile zero or one intervention. A multi-factor candidate is one `NARY_DESIGN`, not several uncontrolled interventions.
- For two-factor interaction claims, require exactly four constant-total arms: control, A only, B only, and A+B. Pairwise arms cannot prove interaction.
- Citrus target identity controls citrus selection. Zero citrus is valid. Neroli 10% is support-only unless neroli/orange blossom is explicitly central.
- Musk defaults to zero or one precise musk. Tonalide, Macrolide, and Musk Ketone remain exception-only. Habanolide and Romandolide are owned; Ambrettolide 10% is design-available/procurement-pending; Ethylene Brassylate is missing unless refreshed inventory proves otherwise.
- Synthetic execution and observation fixtures are accepted only when `test_only=True` and can never produce physical, sensory, hedonic, safety, purchase, compounding, or release authority.
- No live Sol/API adapter exists in this subproject. Hypothesis packets are external, exact-byte inputs with frozen model/prompt/input/output hashes.
- V1 and V2 registry bytes remain immutable. V3 is an additive overlay and remains nonruntime until Scientific Maturation and Admission succeeds.

---

### Task 1: Verify the Gate Foundation predecessor

**Files:**
- Create: `engine/solforge/__init__.py`
- Create: `engine/solforge/governance.py`
- Create: `tests/test_solforge_gate_preflight.py`

**Interfaces:**
- Produces `GateFoundationReceipt`, `GateFoundationPreflight`, and `verify_gate_foundation_receipt(project_root)`.

- [ ] **Step 1: Write failing receipt-preflight tests**

Test valid receipt, missing receipt, malformed JSON, failed recorded check, changed source hash, changed test hash, wrong repository commit, and any true authority flag.

```python
def test_solforge_refuses_stale_gate_foundation(tmp_path: Path) -> None:
    project = copy_gate_fixture(tmp_path)
    (project / "engine/hedonic_evidence.py").write_text("changed", encoding="utf-8")
    result = verify_gate_foundation_receipt(project)
    assert result.ready is False
    assert "source hash mismatch" in result.blockers[0]
```

- [ ] **Step 2: Run and verify the missing-module failure**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task1'
python -m pytest tests/test_solforge_gate_preflight.py -q -p no:cacheprovider --basetemp $sliceTemp
```

Expected: collection fails because `engine.solforge.governance` does not exist.

- [ ] **Step 3: Implement fail-closed predecessor verification**

The verifier reads the canonical receipt, rehashes every recorded file, confirms every command exit code is zero, confirms the receipt commit is an ancestor of `HEAD`, and returns blockers without mutating the repository.

```python
@dataclass(frozen=True, slots=True)
class GateFoundationPreflight:
    ready: bool
    acceptance_sha256: str | None
    blockers: tuple[str, ...]
```

- [ ] **Step 4: Run tests and Ruff**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task1'
python -m pytest tests/test_solforge_gate_preflight.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/__init__.py engine/solforge/governance.py tests/test_solforge_gate_preflight.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- engine/solforge/__init__.py engine/solforge/governance.py tests/test_solforge_gate_preflight.py
git commit -m "feat(solforge): require accepted gate foundation"
```

### Task 2: Closed, hash-bound SolForge contracts

**Files:**
- Create: `engine/solforge/contracts.py`
- Create: `tests/test_solforge_contracts.py`

**Interfaces:**
- Produces `SolForgeCaseV1`, `SolHypothesisV1`, `SolHypothesisSetV1`, `CompiledArmV1`, `CompiledExperimentV1`, `ExecutionReceiptV1`, `TemporalEvidencePacketV1`, `CriterionFitPacketV1`, and `DecisionReceiptV1`.

- [ ] **Step 1: Write failing construction, canonicalization, and lineage tests**

For every record, test:

- exact `schema_version`;
- closed required fields and enum values;
- lower-case SHA-256 validation;
- canonical key order and stable record hash;
- parent hash linkage;
- duplicate ID rejection;
- authority flags fixed false;
- synthetic execution rejected unless `test_only=True`;
- target/ideal and inventory-build fields cannot be equal by accidental aliasing of the same mutable mapping.

```python
def test_decision_receipt_hash_binds_every_parent() -> None:
    receipt = valid_decision_receipt()
    assert receipt.record_sha256 == sha256_hex(receipt.canonical_bytes())
    changed = replace(receipt, criterion_fit_sha256="f" * 64)
    assert changed.record_sha256 != receipt.record_sha256
```

- [ ] **Step 2: Run and verify missing contracts**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task2'
python -m pytest tests/test_solforge_contracts.py -q -p no:cacheprovider --basetemp $sliceTemp
```

Expected: collection fails because `engine.solforge.contracts` does not exist.

- [ ] **Step 3: Implement explicit versioned records**

Use this state vocabulary:

```python
class SolForgeCaseState(str, Enum):
    READY = "READY"
    HOLD = "HOLD"


class CompilationState(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    COMPILED = "COMPILED"
    HOLD = "HOLD"


class DecisionState(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    TEST_NEXT = "TEST_NEXT"
    RETAIN_CURRENT = "RETAIN_CURRENT"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    HOLD = "HOLD"
```

Minimum bindings:

- `SolForgeCaseV1`: case ID, target identity, ideal architecture, current build, exact inventory path/hash, formula/dose hashes, constraints, criterion, and forbidden claims.
- `SolHypothesisSetV1`: case hash, model identity, reasoning setting, prompt/input/output hashes, zero or more ranked hypotheses, and uncertainty.
- `CompiledExperimentV1`: case and hypothesis hashes, inventory refresh hash, delta state/kind, constant-total arms, blockers, omission loss, failure mode, and next comparison.
- `ExecutionReceiptV1`: experiment hash, executor, execution context, sample hashes, deviations, and `test_only`.
- `TemporalEvidencePacketV1`: execution hash, ledger payload hash, state, missing/duplicate cells, disagreement, safety stop, and next discriminator.
- `CriterionFitPacketV1`: temporal/comparison hashes, exact criterion, preference result hash, validation state, intervals, ties, heterogeneity, order effect, and next pair.
- `DecisionReceiptV1`: all parent hashes, final shadow decision, evidence limitations, and all-false authority flags.

Use shared Gate Foundation canonicalization; do not use `dataclasses.asdict()` for signed bytes.

- [ ] **Step 4: Add exact round-trip tests**

Every record implements `as_dict`, `from_dict`, `canonical_bytes`, and `record_sha256`. Round-trip must preserve exact canonical bytes and reject unknown fields.

- [ ] **Step 5: Run tests and Ruff**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task2'
python -m pytest tests/test_solforge_contracts.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/contracts.py tests/test_solforge_contracts.py
```

Expected: all checks pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add -- engine/solforge/contracts.py tests/test_solforge_contracts.py
git commit -m "feat(solforge): add hash-bound evidence-loop contracts"
```

### Task 3: Hypothesis validation and evidence-question routing

**Files:**
- Create: `engine/solforge/hypotheses.py`
- Create: `tests/test_solforge_hypotheses.py`

**Interfaces:**
- Produces `HypothesisValidationResult`, `EvidenceQuestionV1`, `validate_hypothesis_set`, and `questions_for_unsupported_hypotheses`.

- [ ] **Step 1: Write failing validation tests**

Reject invented inventory facts, formula mutations outside the case, target redefinition by inventory, ingredient-count rationales, beauty/liking assertions, sensory fabrication, unbound citations, multiple first interventions, and pairwise claims of n-ary synergy. Accept uncertainty and an empty hypothesis set leading to `NO_CHANGE` or `HOLD`.

- [ ] **Step 2: Implement deterministic validation**

`EvidenceQuestionV1` binds exact unresolved claim, target/function/material scope, required evidence type, preferred design/endpoint, behavior-changing result, forbidden authority, and search status. Validation returns structured blocker codes rather than searching literature or calling a model.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task3'
python -m pytest tests/test_solforge_hypotheses.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/hypotheses.py tests/test_solforge_hypotheses.py
```

Expected: all checks pass.

- [ ] **Step 4: Commit Task 3**

```powershell
git add -- engine/solforge/hypotheses.py tests/test_solforge_hypotheses.py
git commit -m "feat(solforge): validate hypothesis packets"
```

### Task 4: Architectural Delta compiler adapter

**Files:**
- Create: `engine/solforge/adapters.py`
- Modify: `engine/perception/architectural_delta.py`
- Create: `tests/test_solforge_architectural_adapter.py`
- Modify: `tests/test_architectural_delta.py`

**Interfaces:**
- Produces `compile_architectural_delta(case, hypotheses)`.
- Reuses `evaluate_architectural_delta`; it does not duplicate target, inventory, citrus, musk, or n-ary policy.

- [ ] **Step 1: Write failing adapter and n-ary completeness tests**

Test:

- empty/redundant hypotheses -> `NO_CHANGE`;
- more than one independent intervention -> `HOLD`;
- current inventory cannot rewrite ideal target;
- the full workbook is reparsed and source-row count/hash is recorded;
- Neroli support on a non-orange-blossom target cannot become primary citrus;
- zero citrus remains valid;
- generic musk layering is rejected;
- exception musks require explicit target role and exception justification;
- Habanolide x Romandolide compiles exactly control/H/R/H+R constant-total arms;
- missing any factorial arm or changing total dose -> `HOLD`;
- pairwise evidence cannot promote the interaction claim;
- all inventory statuses remain distinct.

```python
def test_two_factor_musk_design_has_complete_constant_total_arms() -> None:
    result = compile_architectural_delta(musk_case(), musk_hypotheses())
    assert tuple(arm.arm_id for arm in result.arms) == (
        "CONTROL", "HABANOLIDE", "ROMANDOLIDE", "HABANOLIDE_X_ROMANDOLIDE"
    )
    assert len({arm.total_active_mass_g for arm in result.arms}) == 1
```

- [ ] **Step 2: Run and verify expected n-ary/adaptation failures**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task4'
python -m pytest tests/test_solforge_architectural_adapter.py tests/test_architectural_delta.py -q -p no:cacheprovider --basetemp $sliceTemp
```

Expected: adapter imports fail and any incomplete existing n-ary behavior is exposed.

- [ ] **Step 3: Implement the thin adapter and focused design firewall**

Convert validated hypotheses to `ArchitecturalDeltaCandidate` values, call the existing engine once, then convert its result to `CompiledExperimentV1`. Add only the minimum `architectural_delta.py` changes needed to enforce complete constant-total two-factor arms and expose inventory refresh lineage. Keep the existing public request/result API compatible.

- [ ] **Step 4: Run compiler tests and Ruff**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task4'
python -m pytest tests/test_solforge_architectural_adapter.py tests/test_architectural_delta.py tests/test_complexity_design_contracts.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/adapters.py engine/perception/architectural_delta.py tests/test_solforge_architectural_adapter.py tests/test_architectural_delta.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4**

```powershell
git add -- engine/solforge/adapters.py engine/perception/architectural_delta.py tests/test_solforge_architectural_adapter.py tests/test_architectural_delta.py
git commit -m "feat(solforge): compile one controlled architectural delta"
```

### Task 5: Backend-compatible laboratory export with no migration

**Files:**
- Create: `backend/app/schemas/solforge.py`
- Modify: `backend/app/schemas/lab.py`
- Create: `backend/tests/test_solforge_schemas.py`
- Modify: `engine/solforge/adapters.py`
- Create: `tests/test_solforge_backend_export.py`

**Interfaces:**
- Produces `SolForgeProtocolContextV1`, `SolForgeObservationContextV1`, `SolForgeComparisonContextV1`, and `export_backend_lab_payloads(experiment)`.
- Serializes through existing `ExperimentCreate.protocol`, `ObservationCreate.observations`, and `PairwiseComparisonCreate.context`; no model or database migration.

- [ ] **Step 1: Write failing Pydantic and export tests**

Assert exact experiment/sample/application payload shapes, blind-code uniqueness, sample hash binding, constant-total dose preservation, protocol/schedule hashes, assessor/repeat/timepoint/endpoint keys, comparison criterion and first-position metadata, and rejection of unknown schema versions.

- [ ] **Step 2: Implement nested schema validators**

Keep existing lab request fields unchanged. Add optional validation helpers that parse nested `solforge` context when present and leave unrelated legacy dictionaries accepted.

```python
class SolForgeProtocolContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["solforge_protocol_context_v1"]
    compiled_experiment_sha256: str
    schedule_sha256: str
    arm_ids: tuple[str, ...]
    criterion_ids: tuple[str, ...]
    test_only: bool = False
```

- [ ] **Step 3: Implement pure export adapter**

The adapter returns dictionaries only. It performs no database write, bottle action, allocation, physical execution, or API call.

- [ ] **Step 4: Run root and backend tests separately**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task5-root'
python -m pytest tests/test_solforge_backend_export.py -q -p no:cacheprovider --basetemp $sliceTemp
$backendTemp = Join-Path $PWD '.tmp-solforge-slice-task5-backend'
python -m pytest backend/tests/test_solforge_schemas.py -q -p no:cacheprovider --basetemp $backendTemp
python -m ruff check backend/app/schemas/solforge.py backend/app/schemas/lab.py engine/solforge/adapters.py backend/tests/test_solforge_schemas.py tests/test_solforge_backend_export.py
```

Expected: both environments pass with no migration generated.

- [ ] **Step 5: Commit Task 5**

```powershell
git add -- backend/app/schemas/solforge.py backend/app/schemas/lab.py backend/tests/test_solforge_schemas.py engine/solforge/adapters.py tests/test_solforge_backend_export.py
git commit -m "feat(solforge): export backend-compatible lab protocols"
```

### Task 6: Temporal and criterion-fit evidence adapters

**Files:**
- Modify: `engine/solforge/adapters.py`
- Create: `tests/test_solforge_evidence_adapters.py`

**Interfaces:**
- Produces `analyze_execution_receipt`, `build_temporal_packet`, and `build_criterion_fit_packet`.
- Reuses `analyze_temporal_evidence`, `fit_preference_model`, and `evaluate_hedonic_evidence`.

- [ ] **Step 1: Write failing evidence-adapter tests**

Cover missing cells, duplicate cells, order imbalance, unqualified within-sniff data, safety events, repeatability failure, criterion mixing, ties, disconnected graph, assessor heterogeneity, order bias, held-out baseline failure, and deterministic next-pair selection.

Add a hard test that a synthetic execution can produce test diagnostics but its packet and decision retain `physical_execution_authority=False`, `sensory_authority=False`, `hedonic_authority=False`, and `release_authority=False`.

- [ ] **Step 2: Implement strict adapters**

- Parse observation context with `TemporalObservationCell.from_dict`.
- Construct `TemporalEvidenceRequest` with the exact schedule hash.
- Parse comparison context with `PairwisePreference.from_dict`.
- Fit exactly one declared criterion per packet.
- For `LIKING`, call Hedonic Evidence Gate V2; for fidelity, depth, and richness, retain separate criterion diagnostics.
- Never convert predicted volatility or synthetic fixture data into observed physical behavior.

- [ ] **Step 3: Run existing and new evidence tests**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task6'
python -m pytest tests/test_solforge_evidence_adapters.py tests/test_temporal_sensory_evidence.py tests/test_preference.py tests/test_scoped_preference.py tests/test_hedonic_evidence_gate_v2.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/adapters.py tests/test_solforge_evidence_adapters.py
```

Expected: all tests pass.

- [ ] **Step 4: Commit Task 6**

```powershell
git add -- engine/solforge/adapters.py tests/test_solforge_evidence_adapters.py
git commit -m "feat(solforge): adapt temporal and criterion evidence"
```

### Task 7: Deterministic orchestration state machine

**Files:**
- Create: `engine/solforge/orchestrator.py`
- Create: `tests/test_solforge_orchestrator.py`

**Interfaces:**
- Produces `SolForgeStage`, `SolForgeRunState`, and `run_solforge_shadow(case, hypotheses, execution=None)`.

- [ ] **Step 1: Write failing transition tests**

Allowed transitions:

```text
INTAKE -> INVENTORY_REFRESHED -> HYPOTHESES_VALIDATED
-> COMPILED -> EXPORTED -> EVIDENCE_ANALYZED -> DECIDED
```

Any blocker moves to `HELD`; no transition can skip a stage. `NO_CHANGE` moves from validated hypotheses directly to a `DECIDED` no-change receipt after recording inventory lineage. Missing execution ends at `EXPORTED` with `EVIDENCE_INSUFFICIENT`, not fabricated evidence.

- [ ] **Step 2: Implement the pure coordinator**

```python
def run_solforge_shadow(
    case: SolForgeCaseV1,
    hypotheses: SolHypothesisSetV1,
    *,
    execution: ExecutionReceiptV1 | None = None,
) -> SolForgeRunState:
    ...
```

The orchestrator calls adapters only, stores stage receipts, and never imports the legacy hedonic scorer, legacy OAV authority rank, or legacy unified release score.

- [ ] **Step 3: Add deterministic replay test**

Run the same inputs twice and assert byte-identical compiled experiment, evidence packet, decision receipt, and hashes. A one-byte parent change must alter all descendants.

- [ ] **Step 4: Run tests and Ruff**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task7'
python -m pytest tests/test_solforge_orchestrator.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/solforge/orchestrator.py tests/test_solforge_orchestrator.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit Task 7**

```powershell
git add -- engine/solforge/orchestrator.py tests/test_solforge_orchestrator.py
git commit -m "feat(solforge): orchestrate shadow evidence loop"
```

### Task 8: Extend the existing intervention command surface

**Files:**
- Modify: `scripts/intervention_recommend.py`
- Create: `tests/test_intervention_recommend_solforge.py`

**Interfaces:**
- Adds a third mutually exclusive source `--solforge-case` plus required `--solforge-hypotheses`.
- Adds optional `--solforge-execution` and required `--output-dir` for SolForge mode.

- [ ] **Step 1: Write failing CLI tests**

Test argument combinations, exact-byte input hashes, no-change output, held output, compiled experiment export, optional synthetic test execution, atomic output directory write, overwrite refusal, and legacy formula/bundle behavior unchanged.

- [ ] **Step 2: Implement SolForge dispatch without altering legacy report generation**

Write one file per record using its canonical bytes and name it `<schema-version>--<record-sha256>.json`. Write `MANIFEST.json` last with parent-child hashes. Use a sibling temporary directory and `Path.replace` for atomic publication. Refuse an existing nonempty output directory.

- [ ] **Step 3: Run CLI regressions**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task8'
python -m pytest tests/test_intervention_recommend_solforge.py tests/test_interventions.py tests/test_pipeline_interventions.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check scripts/intervention_recommend.py tests/test_intervention_recommend_solforge.py
```

Expected: SolForge and legacy CLI tests pass.

- [ ] **Step 4: Commit Task 8**

```powershell
git add -- scripts/intervention_recommend.py tests/test_intervention_recommend_solforge.py
git commit -m "feat(cli): add SolForge shadow workflow"
```

### Task 9: Add frozen V3 registry governance

**Files:**
- Create: `configs/complexity/complexity_module_registry_v3.json`
- Modify: `engine/perception/complexity_registry.py`
- Create: `tests/test_complexity_registry_v3.py`

**Interfaces:**
- Adds V3 states `PROVENANCE_TOMBSTONE`, `CATALOG_ONLY`, `RESEARCH_ONLY`, `DIAGNOSTIC_ONLY`, `EXPERIMENT_COMPILER`, `SHADOW_VALIDATED`, and `ADMITTED_RUNTIME`.
- V3 is an additive overlay over accepted V2 bytes.

- [ ] **Step 1: Freeze and test predecessor bytes**

At implementation start, compute and record exact SHA-256 for V1 and the accepted V2 file in the V3 `base_registry_chain`. Tests must assert those files remain byte-identical after every V3 operation.

- [ ] **Step 2: Write failing V3 loader and runtime-isolation tests**

Assert:

- wrong base hash fails closed;
- unknown state fails;
- only `ADMITTED_RUNTIME` may have a runtime `import_path`;
- SolForge starts as `EXPERIMENT_COMPILER` or `SHADOW_VALIDATED` with `import_path: null`;
- retired modules remain unreachable;
- tombstones preserve source/evidence hashes;
- V1/V2 bytes are unchanged;
- no registry state grants scientific or release authority.

- [ ] **Step 3: Generalize overlay loading without mutating V1/V2 semantics**

Load the exact base chain, apply V3 overrides/additions in memory, and return the new descriptor state. Keep existing V1 and V2 APIs and tests compatible.

- [ ] **Step 4: Add SolForge and replacement-module entries**

Register the orchestrator, Architectural Delta, Temporal Ledger, Preference Learner, topology candidates, and specialist programs with exact source hashes and nonruntime states. Record the Gate Foundation acceptance hash as required evidence.

- [ ] **Step 5: Run registry tests**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task9'
python -m pytest tests/test_complexity_registry_v3.py tests/test_complexity_registry.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check engine/perception/complexity_registry.py tests/test_complexity_registry_v3.py
```

Expected: all tests pass; predecessor hash assertions remain green.

- [ ] **Step 6: Commit Task 9**

```powershell
git add -- configs/complexity/complexity_module_registry_v3.json engine/perception/complexity_registry.py tests/test_complexity_registry_v3.py
git commit -m "feat(governance): add SolForge registry v3 overlay"
```

### Task 10: Four-case vertical-slice fixtures and integration

**Files:**
- Create: `tests/fixtures/solforge/vertical_slice_cases_v1.json`
- Create: `tests/fixtures/solforge/vertical_slice_cases_v1.sha256`
- Create: `tests/test_solforge_vertical_slice.py`
- Create: `tests/test_solforge_runtime_isolation.py`

- [ ] **Step 1: Build four closed fixtures**

Cases:

1. `ZERO_CITRUS_NO_CHANGE`: target excludes citrus; no-change is correct.
2. `NEROLI_SUPPORT_BRIDGE`: Neroli EO 10% in DPG is a support bridge, not primary citrus.
3. `ONE_PRECISE_MUSK`: one target-fit musk is selected; generic layering is rejected.
4. `HABANOLIDE_ROMANDOLIDE_FACTORIAL`: exactly four constant-total arms test a focused interaction.

Each fixture contains exact case, external hypothesis packet, execution/test observations where applicable, expected deterministic states, expected blocker codes, expected arm IDs, and expected record hashes. Create a minimal workbook per case during the test and verify every nonblank row is parsed.

- [ ] **Step 2: Write the full integration tests before finalizing fixture hashes**

Assert full lineage, exact inventory status, deterministic outputs, backend schema acceptance, criterion isolation, no-change calibration, interaction-arm completeness, test-only evidence restriction, and all-false authority flags.

- [ ] **Step 3: Add runtime isolation tests**

Repository-wide tests must prove:

- no admitted runtime ensemble imports `engine.solforge`;
- no retired complexity card becomes reachable;
- no SolForge module imports legacy hedonic/OAV/release scoring;
- registry V3 `import_path` is null for all non-admitted entries;
- no command can compound, reserve, purchase, release, or write laboratory rows.

- [ ] **Step 4: Freeze fixture hash and run the vertical slice**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task10'
python -m pytest tests/test_solforge_vertical_slice.py tests/test_solforge_runtime_isolation.py tests/test_solforge_orchestrator.py tests/test_solforge_architectural_adapter.py tests/test_solforge_evidence_adapters.py tests/test_solforge_backend_export.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check tests/test_solforge_vertical_slice.py tests/test_solforge_runtime_isolation.py
git diff --check
```

Expected: all tests pass, Ruff passes, and diff check is silent.

- [ ] **Step 5: Commit Task 10**

```powershell
git add -- tests/fixtures/solforge/vertical_slice_cases_v1.json tests/fixtures/solforge/vertical_slice_cases_v1.sha256 tests/test_solforge_vertical_slice.py tests/test_solforge_runtime_isolation.py
git commit -m "test(solforge): freeze four-case vertical slice"
```

### Task 11: Certify the shadow vertical slice

**Files:**
- Create: `scripts/verify_solforge_vertical_slice.py`
- Create: `tests/test_solforge_vertical_slice_receipt.py`
- Create after successful verification: `data/governance/solforge_vertical_slice_acceptance_v1.json`

- [ ] **Step 1: Write verifier and tamper tests**

The verifier must reject a stale Gate Foundation receipt, changed V3 base hash, changed fixture, failed test, unauthorized runtime import, nonconstant interaction arm, nonzero authority flag, or repository commit mismatch.

- [ ] **Step 2: Implement the fixed verification command**

Run the Task 10 suite plus all Gate Foundation receipt validation, contract, registry, CLI, backend-schema, and legacy regression tests. Hash every SolForge source, fixture, schema, test, predecessor receipt, and registry file.

- [ ] **Step 3: Run verifier tests and generate receipt**

Run:

```powershell
$sliceTemp = Join-Path $PWD '.tmp-solforge-slice-task11'
python -m pytest tests/test_solforge_vertical_slice_receipt.py -q -p no:cacheprovider --basetemp $sliceTemp
python -m ruff check scripts/verify_solforge_vertical_slice.py tests/test_solforge_vertical_slice_receipt.py
python scripts/verify_solforge_vertical_slice.py --output data/governance/solforge_vertical_slice_acceptance_v1.json
python -m pytest tests/test_solforge_vertical_slice_receipt.py -q -p no:cacheprovider --basetemp .tmp-solforge-slice-receipt
git diff --check
```

Expected: all commands pass and the acceptance receipt is written.

- [ ] **Step 4: Review and commit only vertical-slice certification files**

```powershell
git status --short
git diff --stat
git add -- scripts/verify_solforge_vertical_slice.py tests/test_solforge_vertical_slice_receipt.py data/governance/solforge_vertical_slice_acceptance_v1.json
git commit -m "chore(solforge): certify shadow vertical slice"
```

## Vertical Slice Completion Criteria

- Gate Foundation receipt is current and verified.
- All versioned records round-trip and hash deterministically.
- Four cases reach their expected no-change, support-only, single-musk, or complete-factorial decisions.
- Inventory V5 is fully reparsed at execution and cannot redefine the ideal target.
- Backend export validates without database migration or database writes.
- Temporal, preference, and hedonic evidence stay criterion- and scope-specific.
- Test-only fixtures cannot create physical or sensory authority.
- Registry V3 preserves V1/V2 bytes and keeps SolForge outside admitted runtime.
- `data/governance/solforge_vertical_slice_acceptance_v1.json` validates against current bytes.
