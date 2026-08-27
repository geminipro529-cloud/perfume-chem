# SolForge Gate Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace operative composition-derived hedonic scoring and aggregate OAV/release authority with typed, hash-bound OAV, hedonic, and release evidence gates that fail closed and preserve legacy outputs only for historical replay.

**Architecture:** Add three independent evidence gates over shared canonical provenance types. Migrate the release CLI and active optimizer to those gates, while retaining `engine/hedonic_model.py`, `engine/pipeline/oav_authority.py`, and `engine/pipeline/release_scoring.py` as explicitly named compatibility surfaces. The new release decision is a conjunction of hard evidence axes; diagnostics are never averaged into authority.

**Tech Stack:** Python 3.12+, frozen dataclasses, enums, canonical JSON and SHA-256, existing `FormulaState`, existing `PreferenceFitResult`, pytest, Ruff, PowerShell, Git.

**Spec:** `docs/superpowers/specs/2026-08-26-solforge-evidence-loop-design.md`

## Global Constraints

- Work inline in `C:\Users\ASUS\.codex\worktrees\a7e6\perfume-chem`; project policy forbids Codex subagents.
- Preserve unrelated dirty-worktree changes and stage only files named in the active task.
- Run every test with a fresh repository-local `--basetemp` and `-p no:cacheprovider` because the repository has known stale pytest-temp permission failures.
- Keep all physical liking, similarity, sensory, stability, safety, purchase, compounding, and release authority false unless exact-scope evidence independently grants it.
- Preserve `engine/hedonic_model.py`, `engine/pipeline/oav_authority.py`, and `engine/pipeline/release_scoring.py` for frozen historical replay; do not silently reinterpret their old payloads.
- Unknown ODT, headspace, stock basis, context, units, or sensory evidence remains unknown. Never coerce unknown to zero, neutral, or 50.
- OAV is a threshold-screening ratio in a declared context. Never sum OAV into odor contribution, balance, beauty, liking, synergy, or release authority.
- `LIKING` is the only criterion accepted by the hedonic gate. Fidelity, depth, richness, intensity, familiarity, and elegance remain separate endpoints.
- A valid preference fit remains scope-relative and is not folded into `FormulaScorer`'s geometric or arithmetic total.
- Existing deterministic formula, stock-lineage, G15, safety, and laboratory gates remain controlling; this plan replaces only false scientific authority and aggregation behavior.
- The Gate Foundation is complete only after its acceptance receipt is generated from a clean focused run. The SolForge Vertical Slice must reject a missing or stale receipt.

---

### Task 1: Shared canonical evidence primitives

**Files:**
- Create: `engine/evidence_contracts.py`
- Create: `tests/test_evidence_contracts.py`

**Interfaces:**
- Produces `EvidenceBasis`, `EvidenceSourceRef`, `QuantitativeEvidence`, `canonical_json_bytes`, and `sha256_hex`.
- Consumed by all three V2 gates and later SolForge records.

- [ ] **Step 1: Write failing canonicalization and validation tests**

```python
def test_quantitative_evidence_requires_explicit_units_context_and_source() -> None:
    with pytest.raises(ValueError, match="unit"):
        QuantitativeEvidence(
            value=1.2,
            unit="",
            context="air threshold",
            method="GC-O",
            basis=EvidenceBasis.MEASURED,
            source=source_ref(),
        )


def test_canonical_bytes_are_order_independent_and_hash_stable() -> None:
    left = canonical_json_bytes({"b": 2, "a": 1})
    right = canonical_json_bytes({"a": 1, "b": 2})
    assert left == right == b'{"a":1,"b":2}'
    assert sha256_hex(left) == hashlib.sha256(left).hexdigest()
```

Also test non-finite values, invalid SHA-256, missing retrieval date, negative uncertainty, and rejection of booleans as numbers.

- [ ] **Step 2: Run the focused test and verify the missing-module failure**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task1'
python -m pytest tests/test_evidence_contracts.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: collection fails because `engine.evidence_contracts` does not exist.

- [ ] **Step 3: Implement the closed shared contract**

```python
class EvidenceBasis(str, Enum):
    MEASURED = "MEASURED"
    MODELED = "MODELED"
    TRANSFERRED = "TRANSFERRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EvidenceSourceRef:
    source_id: str
    source_uri: str
    retrieved_on: str
    source_sha256: str | None


@dataclass(frozen=True, slots=True)
class QuantitativeEvidence:
    value: float | None
    unit: str
    context: str
    method: str
    basis: EvidenceBasis
    source: EvidenceSourceRef | None
    uncertainty: float | None = None
```

Rules:

- `UNKNOWN` requires `value is None`; all other bases require a finite value and a source.
- Unit, context, and method are mandatory for known values.
- `canonical_json_bytes` uses UTF-8, sorted keys, separators `(',', ':')`, `allow_nan=False`, and a terminating newline only when explicitly requested.
- SHA helpers accept bytes only and emit lowercase 64-character hex.
- Every dataclass has `as_dict()` with explicit schema-relevant fields; no generic `asdict()` serialization enters a signed payload.

- [ ] **Step 4: Run Task 1 tests and Ruff**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task1'
python -m pytest tests/test_evidence_contracts.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/evidence_contracts.py tests/test_evidence_contracts.py
```

Expected: all tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- engine/evidence_contracts.py tests/test_evidence_contracts.py
git commit -m "feat(evidence): add canonical evidence primitives"
```

### Task 2: OAV Evidence Gate V2

**Files:**
- Create: `engine/pipeline/oav_evidence.py`
- Create: `tests/test_oav_evidence_gate_v2.py`
- Modify: `engine/pipeline/__init__.py`

**Interfaces:**
- Produces `OAVEvidenceState`, `OAVMaterialEvidenceInput`, `OAVMaterialEvidenceResult`, `OAVEvidenceRequest`, `OAVEvidenceResult`, `evaluate_oav_evidence`, and `oav_evidence_request_from_formula_state`.
- Consumes exact formula and dose-receipt hashes plus row-level stock, headspace, and ODT evidence.

- [ ] **Step 1: Write failing state and firewall tests**

Cover these exact cases:

1. all exact dose/stock lineage plus measured applicable headspace and threshold -> `STRICT_MEASURED`;
2. exact dose/stock lineage plus modeled headspace and applicable threshold -> `MODELED_SCREEN`;
3. transferred threshold or mixed measured/modeled fields -> `PARTIAL`;
4. missing ODT or headspace -> `ABSTAINED` for that row and no numeric OAV;
5. contradictory units, context, formula binding, natural/preblend treatment, or source hash -> `INVALID`;
6. increasing perceptible-material count cannot improve evidence state;
7. no total OAV, percent contribution, liking, synergy, similarity, transition, or release field exists;
8. natural material remains one formula row while constituent uncertainty is nested diagnostic evidence;
9. `OAV >= 1` is labeled threshold-screening only;
10. `oav_evidence_request_from_formula_state` classifies simulator output as modeled, never measured.

```python
def test_perceptible_count_cannot_promote_oav_evidence_state() -> None:
    one = evaluate_oav_evidence(request(rows=(modeled_row("A"),)))
    many = evaluate_oav_evidence(
        request(rows=tuple(modeled_row(f"A-{index}") for index in range(20)))
    )
    assert one.state is OAVEvidenceState.MODELED_SCREEN
    assert many.state is OAVEvidenceState.MODELED_SCREEN
    assert not hasattr(many, "authority_rank_score")
```

- [ ] **Step 2: Run the test and verify the missing-module failure**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task2'
python -m pytest tests/test_oav_evidence_gate_v2.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: collection fails because `engine.pipeline.oav_evidence` does not exist.

- [ ] **Step 3: Implement the typed request and result**

```python
class OAVEvidenceState(str, Enum):
    STRICT_MEASURED = "STRICT_MEASURED"
    MODELED_SCREEN = "MODELED_SCREEN"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class OAVMaterialEvidenceInput:
    material_name: str
    exact_stock_ref: str | None
    supplied_strength_fraction: float | None
    carrier: str | None
    active_mass_g: float | None
    formula_matrix: str
    headspace: QuantitativeEvidence
    threshold: QuantitativeEvidence
    natural_or_preblend: bool = False
    constituent_evidence: tuple[QuantitativeEvidence, ...] = ()


@dataclass(frozen=True, slots=True)
class OAVEvidenceRequest:
    formula_sha256: str
    dose_receipt_sha256: str
    measurement_context: str
    rows: tuple[OAVMaterialEvidenceInput, ...]


@dataclass(frozen=True, slots=True)
class OAVEvidenceResult:
    state: OAVEvidenceState
    formula_sha256: str
    dose_receipt_sha256: str
    rows: tuple[OAVMaterialEvidenceResult, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
```

Compute `oav = headspace / threshold` only when units and contexts are explicitly compatible and threshold is positive. Missing stock or dose lineage makes the affected row `PARTIAL`; contradictory lineage makes it `INVALID`. Aggregate state is `INVALID` for any invalid row, `ABSTAINED` when every row abstains, `PARTIAL` for a mixture containing partial/abstained rows, `STRICT_MEASURED` only when every row is strict, and otherwise `MODELED_SCREEN`. Preserve every missing row and blocker. Do not implement an authority rank.

- [ ] **Step 4: Add the `FormulaState` compatibility adapter**

The adapter must:

- accept an already-built `FormulaState`, exact formula hash, exact dose-receipt hash, and explicit source mappings;
- preserve one natural formula row;
- map simulator vapor concentration to `MODELED` only;
- map missing ODT to `UNKNOWN` rather than zero;
- refuse a formula-state/dose-receipt mismatch; and
- never call `analyze_oav_authority` internally.

- [ ] **Step 5: Export V2 without changing the V1 compatibility import**

Add explicit V2 exports to `engine/pipeline/__init__.py`. Do not alias V2 types to the existing `OAVAuthority*` names.

- [ ] **Step 6: Run OAV V2 plus existing OAV regressions**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task2'
python -m pytest tests/test_oav_evidence_gate_v2.py tests/test_oav_authority.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/pipeline/oav_evidence.py engine/pipeline/__init__.py tests/test_oav_evidence_gate_v2.py
```

Expected: V2 tests pass; legacy OAV tests remain unchanged and pass.

- [ ] **Step 7: Commit Task 2**

```powershell
git add -- engine/pipeline/oav_evidence.py engine/pipeline/__init__.py tests/test_oav_evidence_gate_v2.py
git commit -m "feat(oav): add evidence-state gate v2"
```

### Task 3: Hedonic Evidence Gate V2

**Files:**
- Create: `engine/hedonic_evidence.py`
- Create: `tests/test_hedonic_evidence_gate_v2.py`

**Interfaces:**
- Produces `HedonicScope`, `HedonicEvidenceState`, `PreferenceFitEvidenceReceiptV1`, `HedonicEvidenceRequest`, `HedonicEvidenceResult`, `bind_preference_fit_evidence`, and `evaluate_hedonic_evidence`.
- Wraps an existing `PreferenceFitRequest`/`PreferenceFitResult` pair in an exact-scope receipt binding sample, formula/build, protocol, criterion, assessor, order, timepoint, comparison packets, model configuration, and bootstrap values.

- [ ] **Step 1: Write failing criterion and scope tests**

Cover:

- no fit -> `NOT_TESTED`, with no neutral score;
- non-`LIKING` criterion -> `INVALID_OR_CONFOUNDED`;
- withheld fit -> `INSUFFICIENT_EVIDENCE`;
- diagnostic fit -> `DIAGNOSTIC`;
- held-out baseline failure -> `FAILED_HELDOUT_BASELINE`;
- validated exact-scope `LIKING` fit -> `VALIDATED_EXACT_SCOPE`;
- formula, sample, protocol, assessor, criterion, timepoint, order, seed, or model-config mismatch -> `INVALID_OR_CONFOUNDED`;
- owner, trained-panel, and consumer scopes are non-interchangeable;
- ties remain in the evidence count but are not directional wins;
- safety events prevent validation;
- no beauty score or universal-preference field exists.

```python
def test_missing_liking_evidence_is_not_tested_without_default_score() -> None:
    result = evaluate_hedonic_evidence(request(fit_receipt=None))
    assert result.state is HedonicEvidenceState.NOT_TESTED
    assert result.utility_intervals == {}
    assert not hasattr(result, "score")
```

- [ ] **Step 2: Run and verify the missing-module failure**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task3'
python -m pytest tests/test_hedonic_evidence_gate_v2.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: collection fails because `engine.hedonic_evidence` does not exist.

- [ ] **Step 3: Implement exact-scope hedonic evidence evaluation**

```python
class HedonicScope(str, Enum):
    OWNER = "OWNER"
    TRAINED_PANEL = "TRAINED_PANEL"
    CONSUMER_POPULATION = "CONSUMER_POPULATION"


class HedonicEvidenceState(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DIAGNOSTIC = "DIAGNOSTIC"
    VALIDATED_EXACT_SCOPE = "VALIDATED_EXACT_SCOPE"
    FAILED_HELDOUT_BASELINE = "FAILED_HELDOUT_BASELINE"
    INVALID_OR_CONFOUNDED = "INVALID_OR_CONFOUNDED"


@dataclass(frozen=True, slots=True)
class PreferenceFitEvidenceReceiptV1:
    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    time_seconds: float
    schedule_sha256: str
    training_comparisons_sha256: str
    heldout_comparisons_sha256: str
    fit_request_sha256: str
    fit_result: PreferenceFitResult
    fit_result_sha256: str
    model_configuration_sha256: str


@dataclass(frozen=True, slots=True)
class HedonicEvidenceRequest:
    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    time_seconds: float
    schedule_sha256: str
    fit_receipt: PreferenceFitEvidenceReceiptV1 | None
    safety_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HedonicEvidenceResult:
    state: HedonicEvidenceState
    scope: HedonicScope
    criterion_id: str
    utility_intervals: dict[str, tuple[float, float]]
    tie_rate: float | None
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    universal_preference_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
```

`bind_preference_fit_evidence` canonicalizes the exact training and held-out comparison records and the fit configuration, then verifies the supplied result corresponds to that request before issuing the receipt. Map `PreferenceFitStatus` conservatively. Require `validated is True`, `status is VALIDATED`, held-out accuracy strictly above the declared baseline, isolated `LIKING`, a connected graph, scoped validation, nonempty exact hashes, matching request/result configuration, and no order/safety blocker before exact-scope validation.

- [ ] **Step 4: Run hedonic gate and preference regressions**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task3'
python -m pytest tests/test_hedonic_evidence_gate_v2.py tests/test_preference.py tests/test_scoped_preference.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/hedonic_evidence.py tests/test_hedonic_evidence_gate_v2.py
```

Expected: all tests pass; the three-argument `PairwisePreference` constructor remains compatible.

- [ ] **Step 5: Commit Task 3**

```powershell
git add -- engine/hedonic_evidence.py tests/test_hedonic_evidence_gate_v2.py
git commit -m "feat(hedonic): require blinded exact-scope liking evidence"
```

### Task 4: Release Evidence Gate V2

**Files:**
- Create: `engine/pipeline/release_evidence.py`
- Create: `tests/test_release_evidence_gate_v2.py`
- Modify: `engine/pipeline/__init__.py`

**Interfaces:**
- Produces `EvidenceAxisState`, `ReleaseEvidenceStatus`, `ReleaseEvidenceAxis`, `ReleaseEvidenceRequest`, `ReleaseEvidenceResult`, and `evaluate_release_evidence`.
- Consumes deterministic gate outcomes, OAV V2, hedonic V2, laboratory/sensory state, and separately labeled diagnostics.

- [ ] **Step 1: Write failing noncompensatory release tests**

Test:

- one failed hard axis yields `HOLD` even when every diagnostic is 100;
- `NOT_TESTED` hedonic or sensory evidence remains visible and yields `HOLD`;
- an invalid OAV result yields `INVALID`;
- all required axes passing yields `READY_FOR_HUMAN_REVIEW`, never release authority;
- diagnostics cannot be averaged and do not expose `total`, `beauty`, or `hedonic_score`;
- changing legacy unified scores cannot change V2 status;
- axis payloads bind source hashes and exact scope.

```python
def test_diagnostics_cannot_compensate_for_missing_hedonic_evidence() -> None:
    result = evaluate_release_evidence(
        request(
            hedonic=hedonic_result(HedonicEvidenceState.NOT_TESTED),
            diagnostics={"legacy_total": 100.0, "luxury": 100.0},
        )
    )
    assert result.status is ReleaseEvidenceStatus.HOLD
    assert result.release_authority is False
```

- [ ] **Step 2: Run and verify the missing-module failure**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task4'
python -m pytest tests/test_release_evidence_gate_v2.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: collection fails because `engine.pipeline.release_evidence` does not exist.

- [ ] **Step 3: Implement typed axes and conjunction logic**

```python
class EvidenceAxisState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    NOT_TESTED = "NOT_TESTED"
    INVALID = "INVALID"


class ReleaseEvidenceStatus(str, Enum):
    HOLD = "HOLD"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceResult:
    status: ReleaseEvidenceStatus
    axes: tuple[ReleaseEvidenceAxis, ...]
    diagnostics: Mapping[str, object]
    blockers: tuple[str, ...]
    release_authority: bool = field(default=False, init=False)
```

Required axis IDs are `source_rights`, `target_formula_identity`, `inventory_lineage`, `active_dose_rebase`, `oav_evidence`, `safety_ifra`, `laboratory_execution`, `sensory_evidence`, and `hedonic_evidence`. Reject duplicates, missing required axes, and unknown axis IDs. Overall logic is `INVALID` if any axis is invalid, `READY_FOR_HUMAN_REVIEW` only when every required axis passes, otherwise `HOLD`.

- [ ] **Step 4: Add adapters for existing deterministic gate reports**

Create pure functions in the same module:

```python
def release_axes_from_gate_report(gate_report: Mapping[str, object]) -> tuple[ReleaseEvidenceAxis, ...]: ...
def release_axis_from_oav(result: OAVEvidenceResult) -> ReleaseEvidenceAxis: ...
def release_axis_from_hedonic(result: HedonicEvidenceResult) -> ReleaseEvidenceAxis: ...
```

Adapters must preserve `FAIL`, `HOLD`, `NOT TESTED`, absent, and malformed states distinctly. They must not inspect legacy numeric scores.

- [ ] **Step 5: Run release V2 tests and existing release regressions**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task4'
python -m pytest tests/test_release_evidence_gate_v2.py tests/test_release_scoring_contract.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/pipeline/release_evidence.py engine/pipeline/__init__.py tests/test_release_evidence_gate_v2.py
```

Expected: new and compatibility tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add -- engine/pipeline/release_evidence.py engine/pipeline/__init__.py tests/test_release_evidence_gate_v2.py
git commit -m "feat(release): add noncompensatory evidence gate v2"
```

### Task 5: Remove legacy hedonic scoring from active optimization

**Files:**
- Modify: `engine/optimizer/models.py`
- Modify: `engine/optimizer/scoring.py`
- Modify: `engine/family_scorer.py`
- Modify: `engine/formula_analyzer.py`
- Modify: `engine/formula_recommendations.py`
- Modify: `scripts/optimize_cobalt_cedar_air.py`
- Modify: `scripts/score_collection_formulas.py`
- Modify: `scripts/score_designer_prestige_18.py`
- Modify: `scripts/verify_formula_workflow.py`
- Modify: `scripts/verify_c0_physical_model_inventory.py`
- Create: `tests/test_legacy_hedonic_runtime_isolation.py`
- Create: `tests/test_active_scoring_consumers.py`

**Interfaces:**
- Active `FormulaScorer.score()` omits operative `hedonic` and rejects nonzero hedonic weights.
- New `LegacyObjectiveWeightsV1` and `FormulaScorer.score_legacy_replay()` preserve historical replay shape, old default weights, and old fixed-valence calculations.

- [ ] **Step 1: Freeze the compatibility behavior before changing production code**

Write tests proving:

- direct `engine.hedonic_model.score_hedonic` remains importable;
- `score_legacy_replay()` reproduces one fixed literal formula's current `hedonic`, arithmetic total, geometric total, and science diagnostics;
- active `score()` has no top-level numeric `hedonic` key;
- active totals do not change when legacy hedonic values are monkeypatched;
- `score_axis(fv, "hedonic")` raises `ValueError("hedonic is evidence-gated")`;
- nonzero `ObjectiveWeights.hedonic` in active scoring raises the same error;
- no active recommendation or release path calls `engine.hedonic_model.score_hedonic`.

- [ ] **Step 2: Run and verify the expected active-path failures**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task5'
python -m pytest tests/test_legacy_hedonic_runtime_isolation.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: failures show active `FormulaScorer.score()` still calls `score_hedonic` and returns an operative hedonic axis.

- [ ] **Step 3: Split active and replay scoring**

- Change `ObjectiveWeights.hedonic` default to `0.0`, retain the field for constructor compatibility, and document that only zero is accepted by active scoring. Add immutable `LegacyObjectiveWeightsV1` with the exact former defaults solely for replay.
- Remove `hedonic` from active `_AXIS_DISPATCH`, the base score mapping, arithmetic/geometric totals, hard-fail axes, and active `_science` diagnostics.
- Move the exact old implementation behind `score_legacy_replay()` and make it use `LegacyObjectiveWeightsV1`; do not alter frozen replay arithmetic.
- Emit a nested active diagnostic:

```python
scores["_hedonic_evidence"] = {
    "state": "NOT_TESTED",
    "basis": "No exact-scope blinded LIKING receipt supplied to FormulaScorer.",
    "legacy_heuristic_available_for_replay": True,
}
```

- Do not substitute a neutral value in totals.

- [ ] **Step 4: Migrate current consumers**

- Set all family/profile `hedonic=` weights to `0.0` and remove prose claiming intrinsic beauty or pleasantness.
- Replace display/index accesses to `scores["hedonic"]` with explicit `NOT_TESTED` evidence-state rendering.
- Remove hedonic values from optimization vectors and collection ranks.
- Keep `scripts/verify_c0_physical_model_inventory.py` on `score_legacy_replay()` because it verifies frozen legacy fixtures.
- Add an `rg`-backed test that allows `score_hedonic` calls only in `engine/hedonic_model.py`, the replay method, legacy verification, and isolation tests.
- Add import/smoke cases in `tests/test_active_scoring_consumers.py` for the family scorer, analyzer, recommendations, collection scorer, designer scorer, workflow verifier, and Cobalt Cedar optimizer so removed top-level hedonic values cannot leave a latent `KeyError` or formatting failure.

- [ ] **Step 5: Run focused scorer and consumer tests**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task5'
python -m pytest tests/test_legacy_hedonic_runtime_isolation.py tests/test_active_scoring_consumers.py tests/test_optimizer_thermodynamic_unification.py tests/test_golden_formula_regression.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/optimizer/models.py engine/optimizer/scoring.py engine/family_scorer.py engine/formula_analyzer.py engine/formula_recommendations.py scripts/optimize_cobalt_cedar_air.py scripts/score_collection_formulas.py scripts/score_designer_prestige_18.py scripts/verify_formula_workflow.py scripts/verify_c0_physical_model_inventory.py tests/test_legacy_hedonic_runtime_isolation.py tests/test_active_scoring_consumers.py
```

Expected: focused tests pass; the census test finds no unauthorized active call.

- [ ] **Step 6: Commit Task 5**

```powershell
git add -- engine/optimizer/models.py engine/optimizer/scoring.py engine/family_scorer.py engine/formula_analyzer.py engine/formula_recommendations.py scripts/optimize_cobalt_cedar_air.py scripts/score_collection_formulas.py scripts/score_designer_prestige_18.py scripts/verify_formula_workflow.py scripts/verify_c0_physical_model_inventory.py tests/test_legacy_hedonic_runtime_isolation.py tests/test_active_scoring_consumers.py
git commit -m "refactor(scoring): isolate legacy hedonic heuristic"
```

### Task 6: Migrate the release command to V2 evidence

**Files:**
- Modify: `scripts/formula_release_gate.py`
- Create: `tests/test_formula_release_evidence_cli.py`

**Interfaces:**
- `scripts/formula_release_gate.py` emits `release_evidence_v2` as the controlling payload.
- Legacy unified scores may appear only under `compatibility.legacy_unified_scores_v1` when explicitly requested with `--include-legacy-diagnostics`.

- [ ] **Step 1: Write failing CLI payload tests**

Assert:

- default output includes `release_evidence` with `schema_version == "release_evidence_v2"`;
- default output has no operative `scores`, `industry_10`, `rank_score`, or numeric hedonic field;
- modeled OAV appears as `MODELED_SCREEN` and cannot independently pass release;
- missing liking returns `NOT_TESTED` and overall `HOLD`;
- `--include-legacy-diagnostics` nests old values only under `compatibility`;
- monkeypatching compatibility scores to 100 does not change V2 status or blockers;
- every authority flag remains false.

- [ ] **Step 2: Run and verify old payload failures**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task6'
python -m pytest tests/test_formula_release_evidence_cli.py -q -p no:cacheprovider --basetemp $gateTemp
```

Expected: failures show the CLI still publishes the legacy score payload at the top level.

- [ ] **Step 3: Wire V2 gates into the existing single-state pipeline**

Within each formula loop:

1. build `gate_result` once;
2. adapt its `FormulaState` into an OAV V2 request;
3. evaluate OAV V2;
4. create `HedonicEvidenceResult(NOT_TESTED)` unless an exact external liking packet is supplied in a later subproject;
5. adapt hard gate axes;
6. evaluate release V2;
7. serialize the V2 result as the controlling report.

Keep the existing legacy OAV/unified calculation behind `--include-legacy-diagnostics`; it must not be evaluated by default.

- [ ] **Step 4: Run CLI, gate, and G15 regressions**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task6'
python -m pytest tests/test_formula_release_evidence_cli.py tests/test_release_evidence_gate_v2.py tests/test_oav_evidence_gate_v2.py tests/test_pre_mix_guard.py tests/test_oav_authority.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check scripts/formula_release_gate.py tests/test_formula_release_evidence_cli.py
```

Expected: all tests pass and legacy diagnostics remain opt-in.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- scripts/formula_release_gate.py tests/test_formula_release_evidence_cli.py
git commit -m "feat(release): migrate formula gate to evidence v2"
```

### Task 7: Cross-gate integration and adversarial regressions

**Files:**
- Create: `tests/test_solforge_gate_foundation_integration.py`
- Modify: `engine/evidence/unsupported_science.py`
- Modify: `scripts/scientific_truth_inventory.py`

- [ ] **Step 1: Write the end-to-end adversarial test matrix**

Create parametrized tests for exact-stock strength mismatch, carrier mismatch, active-dose hash mismatch, natural-composite ambiguity, ODT medium mismatch, modeled-as-measured fraud, perceptible-count gaming, synthetic liking injection, criterion substitution, order confounding, held-out baseline failure, and 100-point diagnostic compensation.

Each case must assert the precise V2 state, blocker code, and all-false authority flags.

- [ ] **Step 2: Update scientific-truth inventory classifications**

Classify:

- fixed-valence hedonic scorer -> `LEGACY_HEURISTIC_PROVENANCE`;
- OAV authority rank -> `LEGACY_HEURISTIC_PROVENANCE`;
- unified score payload -> `LEGACY_HEURISTIC_PROVENANCE`;
- OAV V2 -> `COMPUTATIONAL_OR_MEASURED_EVIDENCE_STATE`, conditional on row basis;
- Hedonic V2 -> `OBSERVED_EXACT_SCOPE_ONLY`;
- Release V2 -> `NONCOMPENSATORY_DECISION_SUPPORT`.

Do not delete old unsupported-science entries; update their permitted use and replacement references.

- [ ] **Step 3: Run the complete Gate Foundation suite**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task7'
python -m pytest tests/test_evidence_contracts.py tests/test_oav_evidence_gate_v2.py tests/test_hedonic_evidence_gate_v2.py tests/test_release_evidence_gate_v2.py tests/test_legacy_hedonic_runtime_isolation.py tests/test_formula_release_evidence_cli.py tests/test_solforge_gate_foundation_integration.py tests/test_oav_authority.py tests/test_release_scoring_contract.py tests/test_preference.py tests/test_scoped_preference.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check engine/evidence_contracts.py engine/pipeline/oav_evidence.py engine/hedonic_evidence.py engine/pipeline/release_evidence.py engine/optimizer/models.py engine/optimizer/scoring.py scripts/formula_release_gate.py engine/evidence/unsupported_science.py scripts/scientific_truth_inventory.py tests/test_solforge_gate_foundation_integration.py
git diff --check
```

Expected: all named tests pass, Ruff passes, and `git diff --check` is silent.

- [ ] **Step 4: Commit Task 7**

```powershell
git add -- tests/test_solforge_gate_foundation_integration.py engine/evidence/unsupported_science.py scripts/scientific_truth_inventory.py
git commit -m "test(evidence): enforce gate foundation firewalls"
```

### Task 8: Generate the hash-bound Gate Foundation acceptance receipt

**Files:**
- Create: `scripts/verify_solforge_gate_foundation.py`
- Create: `tests/test_solforge_gate_foundation_receipt.py`
- Create after successful verification: `data/governance/solforge_gate_foundation_acceptance_v1.json`

**Interfaces:**
- The verifier runs the fixed Task 7 test list, Ruff list, source census, and `git diff --check` in subprocesses.
- The receipt binds repository commit, command arrays, source hashes, test hashes, exit codes, and all-false authority flags.

- [ ] **Step 1: Write failing receipt verifier tests**

Test rejection of a missing source, changed hash, failed command, nonzero hedonic weight, unauthorized `score_hedonic` call, mutable timestamp inside the hashed core, and any true authority flag.

- [ ] **Step 2: Implement deterministic verification and receipt writing**

```python
def verify_gate_foundation(
    project_root: Path,
    *,
    output_path: Path,
) -> dict[str, object]:
    """Run the frozen checks and write a canonical acceptance receipt on success."""
```

Use a temporary directory created under `.tmp-solforge-gate-verifier`, a fixed UTF-8 environment, and `sys.executable`. Hash the exact source and test files named in Tasks 1-7. Put execution time outside the canonical `acceptance_core`; `acceptance_sha256` hashes only stable inputs and outcomes.

- [ ] **Step 3: Run verifier tests**

Run:

```powershell
$gateTemp = Join-Path $PWD '.tmp-solforge-gate-task8'
python -m pytest tests/test_solforge_gate_foundation_receipt.py -q -p no:cacheprovider --basetemp $gateTemp
python -m ruff check scripts/verify_solforge_gate_foundation.py tests/test_solforge_gate_foundation_receipt.py
```

Expected: all tests pass and Ruff passes.

- [ ] **Step 4: Generate and validate the acceptance receipt**

Run:

```powershell
python scripts/verify_solforge_gate_foundation.py --output data/governance/solforge_gate_foundation_acceptance_v1.json
python -m pytest tests/test_solforge_gate_foundation_receipt.py -q -p no:cacheprovider --basetemp .tmp-solforge-gate-receipt
git diff --check
```

Expected: verifier exits 0, writes the receipt, the receipt test passes, and no whitespace errors are reported.

- [ ] **Step 5: Review the final diff and commit only Gate Foundation files**

Run:

```powershell
git status --short
git diff --stat
git diff -- data/governance/solforge_gate_foundation_acceptance_v1.json
```

Confirm unrelated pre-existing paths are unstaged.

```powershell
git add -- scripts/verify_solforge_gate_foundation.py tests/test_solforge_gate_foundation_receipt.py data/governance/solforge_gate_foundation_acceptance_v1.json
git commit -m "chore(evidence): certify SolForge gate foundation"
```

## Gate Foundation Completion Criteria

- Active optimization and release decisions contain no fixed-valence hedonic score.
- Missing liking is `NOT_TESTED`; no neutral fallback exists.
- OAV V2 reports evidence states and row-level provenance without aggregate authority rank.
- Release V2 is a noncompensatory conjunction of hard axes and never grants release authority.
- Frozen legacy outputs remain replayable only through explicit compatibility entry points.
- The fixed focused suite, Ruff, census, and diff checks pass from the recorded commit.
- `data/governance/solforge_gate_foundation_acceptance_v1.json` validates against current bytes.
