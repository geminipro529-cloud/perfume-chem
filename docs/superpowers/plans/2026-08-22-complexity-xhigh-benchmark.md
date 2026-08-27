# Complexity Ensemble and ChatGPT xhigh Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Perfume-Chem prohibits Codex subagents, so `superpowers:subagent-driven-development` is not permitted.

**Goal:** Admit the existing native complexity modules, combine them behind one fail-closed library contract, and run a frozen, paired benchmark against plain ChatGPT xhigh to determine whether they improve integrated perceptual depth, coherent richness, and testable hedonic-potential reasoning—not mere complication—with evidence-based retain, repair, or recoverable retirement decisions.

**Architecture:** A hash-bound registry classifies every discovered complexity artifact. A pure ensemble layer invokes only admitted native module families and emits separated structured evidence; both benchmark arms receive the same frozen definition of useful complexity and the same depth-analysis output contract. A separate benchmark layer prepares sealed control/treatment requests, validates imported xhigh receipts, rejects count/verbosity proxies, scores structured responses deterministically, and computes ensemble and ablation decisions. The existing `scripts/pipeline_audit.py` exposes these operations without adding a new pipeline script or network client.

**Tech Stack:** Python 3.12+, standard-library dataclasses/enums/pathlib/hashlib/json/statistics, existing `engine.calibration.hashing`, pytest, Ruff, existing Perfume-Chem audit CLI, append-only JSON governance receipts, ChatGPT xhigh through clean projectless conversations outside repository runtime.

**Spec:** `docs/superpowers/specs/2026-08-22-complexity-xhigh-benchmark-design.md`

## Global Constraints

- Work only in `D:\chatbots\perfume-chem`; treat the ChatGPT project mirror's `sources/` as read-only.
- Preserve the dirty tree. Archive exact parent bytes before edits, stage exact paths only, and inspect `git diff --cached --name-status` before every commit.
- Do not create a new pipeline script, truth store, database schema, or provider client.
- Do not install or import code, schemas, registries, formulas, or data from `incoming_review/` or any unknown-rights package.
- DeepLuna Fast, Luna fallback, alternate-provider fallback, and Codex subagents remain disabled.
- The user selected online ChatGPT Pro work chats for bounded advisory delegation. Record their chat IDs and response hashes, keep them separate from benchmark contexts, and make no DeepLuna provider transmission in this implementation.
- The user selected online ChatGPT Pro work chats for bounded delegation. Their outputs are advisory candidate evidence only; they receive no credentials, cannot claim repository writes, and never become benchmark control/treatment observations. Sol verifies everything locally and retains architecture, scientific, security, provenance, and final-acceptance authority.
- The user-requested ChatGPT xhigh runs are benchmark observations, not DeepLuna fallback, implementation authority, or scientific authority.
- Plain ChatGPT xhigh is the control. It receives only the frozen brief, current inventory evidence, canonical evidence, and common output contract.
- The initial corpus is exactly 16 cases: four cases in each of four categories. Freeze case and rubric hashes before any xhigh response is obtained.
- Useful complexity means identity-linked perceptual depth, coherent richness, meaningful contrast and texture, temporal unfolding, testable hedonic-potential logic, and restraint. Raw ingredient/module/interaction/descriptor counts, novelty, response length, jargon, and technical density are not positive evidence.
- At least eight frozen cases must discriminate useful complexity from mere complication, including bloat, redundancy, mud, superficial diversity, flat development, incoherent novelty, and cases where subtraction or negative space creates more depth.
- Musk complexity may be sparse or layered: never force a fixed musk count. Each selected musk requires a target-linked nonredundant role. Tonalide, Macrolide, and Musk Ketone are exception-only and remain omitted unless the complete design-call contract passes; their current depleted state still blocks the current-inventory build.
- An ensemble win requires at least 12/16 paired wins, median improvement of at least 5 points, zero new critical failures, no category median regression greater than 2 points, and valid execution receipts.
- If treatment quality passes but median provider cost is more than 2.0 times control, hold activation under `QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED` and rerun the four most expensive cases after bundle compression.
- Formal retention ablation starts only after the ensemble passes. Diagnostic traces after an ensemble failure are not retention evidence.
- A module family gets at most one repair cycle and exactly four unseen holdout cases. The corpus, rubric, and original response bytes never change during repair.
- Retirement means registry state `RETIRED_BENCHMARK_UNDERPERFORMER`, active-ensemble removal, and an append-only receipt. Do not irreversibly delete source or evidence bytes.
- Inventory authority is `Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5(1).xlsx`, current SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`. The current local `inventory.txt` SHA-256 is `dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec`. Drift requires a new freeze; disagreement requires HOLD.
- Never infer physical liking, similarity, stability, measured headspace, strict empirical OAV, safety, sensory outcome, compounding, procurement, installation, publication, or release authority from this benchmark.
- A hedonic-potential mechanism may be reported only as a design hypothesis paired with a controlled sensory test; physical richness, beauty, liking, delight, or success remains `NOT TESTED`.
- Use TDD for new behavior. Run each failing test before implementation, then rerun it after the minimal change.

## File Map

### Existing local native files to admit without sweeping unrelated changes

- `engine/perception/construction_complexity.py`
- `engine/perception/complexity_expansion.py`
- `engine/scientific_validation/complexity_design_contracts.py`
- `engine/scientific_validation/complexity_model_admission.py`
- `engine/physics/model_lifecycle.py`
- `engine/sensory/within_sniff.py`
- `engine/sensory/temporal_observations.py`
- `engine/sensory/order_balance.py`
- `engine/sensory/panel_contract.py`
- Their nine focused tests named in Task 1
- Only the complexity-specific hunks in `engine/workbench.py`, `engine/perception/__init__.py`, `engine/physics/__init__.py`, `engine/scientific_validation/__init__.py`, `docs/master_prompt_governing.md`, and `prompts/DeepSeek_V4_Flash_0731_Perfume_Orchestrator_Master_Prompt.md`

### New focused implementation files

- `engine/perception/complexity_registry.py` — module descriptors, discovery, exact-hash census, and classification validation
- `engine/perception/complexity_adapters.py` — JSON-to-native adapters for the six admitted module families
- `engine/perception/complexity_ensemble.py` — immutable case packet, relevance selection, separated bundle, and omission contract
- `engine/perception/musk_design.py` — clean-room sparse/layered musk selection, distinct-role validation, exception-only gating, and target/build inventory separation
- `engine/perception/complexity_xhigh.py` — sealed request/response receipts, prompt construction, import validation, nonce accounting, and anonymization
- `engine/perception/complexity_benchmark.py` — deterministic hard gates, rubric scoring, aggregate decisions, ablation, cost review, repair count, and retirement proposals
- `configs/complexity/complexity_module_registry_v1.json` — explicit module/artifact classification and current hashes
- `tests/fixtures/complexity_xhigh_cases_v1.json` — frozen 16-case corpus and rubric invariants
- `tests/fixtures/complexity_xhigh_cases_v1.sha256` — canonical fixture hash
- `data/governance/complexity_native_module_admission_20260822.json` — native exact-byte admission receipt
- `docs/research/PERFUME_CHEM_COMPLEXITY_XHIGH_BENCHMARK_RUNBOOK_2026-08-22.md` — provider-free and live execution runbook

### New tests

- `tests/test_complexity_native_module_admission.py`
- `tests/test_complexity_registry.py`
- `tests/test_complexity_ensemble.py`
- `tests/test_musk_design.py`
- `tests/test_complexity_adapters.py`
- `tests/test_complexity_xhigh_contract.py`
- `tests/test_complexity_benchmark_scoring.py`
- `tests/test_complexity_benchmark_receipt.py`
- `tests/complexity_benchmark_fixtures.py` — explicit reusable constructors for the frozen test case, native payloads, xhigh receipts, score evidence, and family decisions

### Existing files to modify

- `scripts/pipeline_audit.py` — add one local-only `complexity-benchmark` operation
- `tests/test_pipeline_audit_verify.py` — test the new CLI operation

---

### Task 1: Admit the Native Complexity Baseline by Exact Bytes

**Files:**
- Create: `data/governance/complexity_native_module_admission_20260822.json`
- Create: `tests/test_complexity_native_module_admission.py`
- Add existing: the nine native module files and nine focused test files listed below
- Modify by complexity-only staged hunks: `engine/workbench.py`, `engine/perception/__init__.py`, `engine/physics/__init__.py`, `engine/scientific_validation/__init__.py`, `docs/master_prompt_governing.md`, `prompts/DeepSeek_V4_Flash_0731_Perfume_Orchestrator_Master_Prompt.md`

**Interfaces:**
- Consumes: current V16 native installation receipt and exact local source bytes
- Produces: a tracked, reproducible native baseline with `source_admission=false`, `formula_authority=false`, `physical_execution=false`, `sensory_authority=false`, and `release_authority=false`

- [ ] **Step 1: Recheck current exact bytes and stop on drift**

Run:

```powershell
$paths = @(
  'engine/perception/construction_complexity.py',
  'engine/perception/complexity_expansion.py',
  'engine/scientific_validation/complexity_design_contracts.py',
  'engine/scientific_validation/complexity_model_admission.py',
  'engine/physics/model_lifecycle.py',
  'engine/sensory/within_sniff.py',
  'engine/sensory/temporal_observations.py',
  'engine/sensory/order_balance.py',
  'engine/sensory/panel_contract.py'
)
$paths | ForEach-Object {
  $hash = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower()
  "$hash  $_"
}
```

Expected module hashes, in the same order:

```text
f8dd92ae5da1a9aa409ed27ad2e5e789874f32bc77a156e28a65870dae871ab1
69b0e2a38f33545efa94e8e3a832091a2ce72d9496b9b211edcd60c0c8afb54e
ef905b8adb6c7c8bdf02372c56040295054fdbeb4dcfe39c3410cb09390ae968
484a0d3902eb96b946f9b3e566d3caa1083187655f12ed456942c9353e0a3710
c320593f3e1bea8dd16014794e32ca5adffd557effb749f82193d487988acaaf
2ac737b87a3a9e237647b4f2bd7fe4601c5634926d7267c240c606726b269caa
e730484f30ecbab428e02d31042649990db46b389d0da6bbfa13e93a6006770b
fe71999d09c7d2366f2ba7c6f27718ba04282435125fd37a02a06051dba5807c
418ecf7f42454ba335c8113487570458fb81210db016cfe778abce72955898cc
```

- [ ] **Step 2: Create and verify a path-preserving rollback archive**

Create a tar archive outside the repository containing all Task 1 paths plus their current `git diff` patch. Use an explicit destination under `D:\perfume-chem-rollback\20260822-complexity-native-admission\`; verify the archive with `tar -tf` and SHA-256 before staging.

- [ ] **Step 3: Run the existing focused baseline**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_construction_complexity.py tests/test_complexity_expansion_native.py tests/test_complexity_design_contracts.py tests/test_complexity_model_admission.py tests/test_model_lifecycle.py tests/test_within_sniff.py tests/test_temporal_observations.py tests/test_order_balance.py tests/test_sensory_panel_contract.py -q -p no:cacheprovider
```

Expected: `56 passed`. Any failure is a HOLD; do not rewrite the admission receipt to match a failure.

- [ ] **Step 4: Write the failing admission receipt test**

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/governance/complexity_native_module_admission_20260822.json"

EXPECTED = {
    "engine/perception/construction_complexity.py": "f8dd92ae5da1a9aa409ed27ad2e5e789874f32bc77a156e28a65870dae871ab1",
    "engine/perception/complexity_expansion.py": "69b0e2a38f33545efa94e8e3a832091a2ce72d9496b9b211edcd60c0c8afb54e",
    "engine/scientific_validation/complexity_design_contracts.py": "ef905b8adb6c7c8bdf02372c56040295054fdbeb4dcfe39c3410cb09390ae968",
    "engine/scientific_validation/complexity_model_admission.py": "484a0d3902eb96b946f9b3e566d3caa1083187655f12ed456942c9353e0a3710",
    "engine/physics/model_lifecycle.py": "c320593f3e1bea8dd16014794e32ca5adffd557effb749f82193d487988acaaf",
    "engine/sensory/within_sniff.py": "2ac737b87a3a9e237647b4f2bd7fe4601c5634926d7267c240c606726b269caa",
    "engine/sensory/temporal_observations.py": "e730484f30ecbab428e02d31042649990db46b389d0da6bbfa13e93a6006770b",
    "engine/sensory/order_balance.py": "fe71999d09c7d2366f2ba7c6f27718ba04282435125fd37a02a06051dba5807c",
    "engine/sensory/panel_contract.py": "418ecf7f42454ba335c8113487570458fb81210db016cfe778abce72955898cc",
}


def test_admitted_native_files_match_exact_receipt() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    recorded = {row["path"]: row["sha256"] for row in payload["native_modules"]}
    assert recorded == EXPECTED
    for relative, expected in EXPECTED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_admission_grants_no_scientific_or_release_authority() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert payload["state"] == "NATIVE_CLEAN_ROOM_BASELINE_ADMITTED"
    assert payload["focused_tests"] == {"passed": 56, "failed": 0}
    assert all(value is False for value in payload["authority"].values())
```

- [ ] **Step 5: Run the admission test to verify it fails**

Run: `python -m pytest tests/test_complexity_native_module_admission.py -q -p no:cacheprovider`

Expected: FAIL because the receipt does not exist.

- [ ] **Step 6: Add the minimal receipt**

Create JSON with this exact contract and the nine verified module rows:

```json
{
  "schema_version": "perfume_chem_complexity_native_module_admission_v1",
  "recorded_at": "2026-08-22T18:34:28.7992415+07:00",
  "state": "NATIVE_CLEAN_ROOM_BASELINE_ADMITTED",
  "source_package_code_installed": false,
  "native_modules": [
    {"path": "engine/perception/construction_complexity.py", "sha256": "f8dd92ae5da1a9aa409ed27ad2e5e789874f32bc77a156e28a65870dae871ab1"},
    {"path": "engine/perception/complexity_expansion.py", "sha256": "69b0e2a38f33545efa94e8e3a832091a2ce72d9496b9b211edcd60c0c8afb54e"},
    {"path": "engine/scientific_validation/complexity_design_contracts.py", "sha256": "ef905b8adb6c7c8bdf02372c56040295054fdbeb4dcfe39c3410cb09390ae968"},
    {"path": "engine/scientific_validation/complexity_model_admission.py", "sha256": "484a0d3902eb96b946f9b3e566d3caa1083187655f12ed456942c9353e0a3710"},
    {"path": "engine/physics/model_lifecycle.py", "sha256": "c320593f3e1bea8dd16014794e32ca5adffd557effb749f82193d487988acaaf"},
    {"path": "engine/sensory/within_sniff.py", "sha256": "2ac737b87a3a9e237647b4f2bd7fe4601c5634926d7267c240c606726b269caa"},
    {"path": "engine/sensory/temporal_observations.py", "sha256": "e730484f30ecbab428e02d31042649990db46b389d0da6bbfa13e93a6006770b"},
    {"path": "engine/sensory/order_balance.py", "sha256": "fe71999d09c7d2366f2ba7c6f27718ba04282435125fd37a02a06051dba5807c"},
    {"path": "engine/sensory/panel_contract.py", "sha256": "418ecf7f42454ba335c8113487570458fb81210db016cfe778abce72955898cc"}
  ],
  "focused_tests": {"passed": 56, "failed": 0},
  "authority": {
    "source_admission": false,
    "formula": false,
    "inventory": false,
    "physical_execution": false,
    "sensory": false,
    "safety": false,
    "installation": false,
    "publication": false,
    "release": false
  }
}
```

The timestamp above records the approved admission-plan freeze. Before creating
the receipt, rerun Step 1 and require every byte to match; any drift requires a
new reviewed receipt timestamp and hash set rather than editing these values to
fit changed code.

- [ ] **Step 7: Run focused admission and native tests**

Run the Step 3 command plus `tests/test_complexity_native_module_admission.py`.

Expected: `58 passed`.

- [ ] **Step 8: Stage only the native baseline**

Use `git add` with the explicit Task 1 file list. For the six already-modified tracked integration files, use patch staging and accept only complexity-specific hunks. Do not stage `engine/sensory/__init__.py`, `opencode.json`, or any unrelated dirty path.

Run: `git diff --cached --check` and `git diff --cached --name-status`.

Expected: only Task 1 paths; no external package bytes and no unrelated edits.

- [ ] **Step 9: Commit the native baseline**

```powershell
git commit -m "feat(complexity): admit native clean-room modules"
```

### Task 2: Build the Hash-Bound Complexity Registry and Census

**Files:**
- Create: `engine/perception/complexity_registry.py`
- Create: `configs/complexity/complexity_module_registry_v1.json`
- Create: `tests/test_complexity_registry.py`

**Interfaces:**
- Produces: `ModuleState`, `ModuleRole`, `ModuleDescriptor`, `ComplexityRegistry`, `CensusFinding`, `CensusResult`, `load_complexity_registry(root, path)`, and `census_complexity_artifacts(root, registry)`
- Consumes later: Task 3 ensemble eligibility and Task 8 retirement transitions

- [ ] **Step 1: Write failing registry tests**

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.perception.complexity_registry import (
    ModuleState,
    census_complexity_artifacts,
    load_complexity_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "configs/complexity/complexity_module_registry_v1.json"


def _write_registry_fixture(root: Path):
    module = root / "engine/perception/construction_complexity.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n", encoding="utf-8")
    digest = hashlib.sha256(module.read_bytes()).hexdigest()
    registry_path = root / "registry.json"
    registry_path.write_text(json.dumps({
        "schema_version": "complexity_module_registry_v1",
        "discovery": {"roots": ["engine", "future_modules"], "terms": ["complexity", "hedonic", "musk"], "metadata_keys": []},
        "modules": [{
            "module_id": "construction-profile",
            "family_id": "construction_profile",
            "role": "CAPABILITY",
            "state": "ACTIVE_CANDIDATE",
            "path": "engine/perception/construction_complexity.py",
            "import_path": "engine.perception.construction_complexity",
            "sha256": digest,
            "evidence_refs": []
        }],
        "artifact_rules": [],
        "dismissal_rules": []
    }), encoding="utf-8")
    return load_complexity_registry(root, registry_path)


def test_registry_loads_only_exact_hash_bound_native_candidates(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    assert registry.modules[0].state is ModuleState.ACTIVE_CANDIDATE
    assert census_complexity_artifacts(tmp_path, registry).state == "PASS"


def test_census_holds_on_hash_drift_or_unclassified_match(tmp_path: Path) -> None:
    registry = _write_registry_fixture(tmp_path)
    (tmp_path / registry.modules[0].path).write_text("VALUE = 2\n", encoding="utf-8")
    candidate = tmp_path / "future_modules/family_hedonic_optimizer.py"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("VALUE = 3\n", encoding="utf-8")
    result = census_complexity_artifacts(tmp_path, registry)
    assert result.state == "HOLD"
    assert result.hash_drift
    assert result.unclassified


def test_unknown_rights_rule_can_never_be_runtime_eligible() -> None:
    registry = load_complexity_registry(PROJECT_ROOT, REGISTRY_PATH)
    external = [m for m in registry.modules if m.state is ModuleState.EVIDENCE_ONLY_NOT_ADMITTED]
    assert external
    assert all(not item.runtime_eligible for item in external)
```

- [ ] **Step 2: Run registry tests to verify import failure**

Run: `python -m pytest tests/test_complexity_registry.py -q -p no:cacheprovider`

Expected: FAIL with `ModuleNotFoundError: engine.perception.complexity_registry`.

- [ ] **Step 3: Implement the registry types and strict loader**

```python
class ModuleState(str, Enum):
    ACTIVE_CANDIDATE = "ACTIVE_CANDIDATE"
    MANDATORY_GUARDRAIL = "MANDATORY_GUARDRAIL"
    EVIDENCE_ONLY_NOT_ADMITTED = "EVIDENCE_ONLY_NOT_ADMITTED"
    FUTURE_CANDIDATE_NOT_VALIDATED = "FUTURE_CANDIDATE_NOT_VALIDATED"
    REDUNDANT_NOT_INVOKED = "REDUNDANT_NOT_INVOKED"
    RETIRED_BENCHMARK_UNDERPERFORMER = "RETIRED_BENCHMARK_UNDERPERFORMER"
    NOT_EVALUATED_NO_RELEVANT_CASE = "NOT_EVALUATED_NO_RELEVANT_CASE"


class ModuleRole(str, Enum):
    CAPABILITY = "CAPABILITY"
    GUARDRAIL = "GUARDRAIL"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    module_id: str
    family_id: str
    role: ModuleRole
    state: ModuleState
    path: str
    import_path: str | None
    sha256: str
    evidence_refs: tuple[str, ...]

    @property
    def runtime_eligible(self) -> bool:
        return self.state in {
            ModuleState.ACTIVE_CANDIDATE,
            ModuleState.MANDATORY_GUARDRAIL,
        }


@dataclass(frozen=True, slots=True)
class ComplexityRegistry:
    schema_version: str
    discovery: Mapping[str, Any]
    modules: tuple[ModuleDescriptor, ...]
    artifact_rules: tuple[Mapping[str, Any], ...]
    dismissal_rules: tuple[Mapping[str, Any], ...]
    registry_sha256: str

    def modules_for_family(self, family_id: str) -> tuple[ModuleDescriptor, ...]:
        return tuple(item for item in self.modules if item.family_id == family_id)

    def family_role(self, family_id: str) -> ModuleRole:
        roles = {item.role for item in self.modules_for_family(family_id)}
        if len(roles) != 1:
            raise ValueError(f"family {family_id!r} must have exactly one role")
        return roles.pop()
```

`load_complexity_registry` must validate nonblank IDs, unique IDs and paths, lowercase 64-character hashes, repository-relative paths, exact file existence, enum values, and absence of runtime imports for evidence-only records.

- [ ] **Step 4: Implement bounded discovery and census**

`census_complexity_artifacts` must:

1. search only `engine/`, `future_modules/`, `incoming_review/`, `references/existing_evidence_packages/`, `data/governance/`, and `chat_bridge/complex_perfumery/`;
2. match path terms directly;
3. inspect only JSON metadata files at or below 2 MiB and only the keys `module_name`, `file_name`, `receipt_id`, `classification`, and `role`;
4. never open ZIP members or execute/import a discovered file;
5. require every finding to match exactly one module, artifact rule, or dismissal rule; and
6. return `HOLD` on hash drift, duplicate classification, missing paths, or unclassified findings.

- [ ] **Step 5: Add the repository registry configuration**

Define the initial five families and nine existing exact native module paths. Set construction, expansion, and experimental design to `ACTIVE_CANDIDATE`; set admission/lifecycle and temporal/sensory modules to `MANDATORY_GUARDRAIL`. Task 3A revises the registry with the sixth `musk_design_restraint` family only after its test-first implementation exists and its exact hash is computed. Set `engine/temporal_graph.py`, `engine/temporal_volatility.py`, `engine/hedonic_model.py`, `future_modules/family_hedonic_optimizer.py`, and `future_modules/advanced_musk_intelligence.py` to `FUTURE_CANDIDATE_NOT_VALIDATED`.

The `advanced_musk_intelligence.py` record must use its current exact SHA-256 `28745ddba38677eaf9717d67067feb436d68b0f0dce672f2b2a405d776adba7b`, have no runtime import path, and state that fixed platform/dose, universal-perception, prestige, and substitution assertions are unvalidated. The census must discover it but the ensemble must never import it.

Add evidence-only artifact rules for matching paths under `incoming_review/`, `references/existing_evidence_packages/`, `data/governance/`, and `chat_bridge/complex_perfumery/`. Add explicit dismissals for test files, package `__init__.py` exports, `engine/sensory/prepilot.py`, and `engine/sensory/lab_projection.py`, with non-module reasons.

- [ ] **Step 6: Run tests and the real census**

Run:

```powershell
python -m pytest tests/test_complexity_registry.py -q -p no:cacheprovider
python -c "from pathlib import Path; from engine.perception.complexity_registry import load_complexity_registry,census_complexity_artifacts; r=load_complexity_registry(Path('.'),Path('configs/complexity/complexity_module_registry_v1.json')); x=census_complexity_artifacts(Path('.'),r); print(x.as_dict()); raise SystemExit(0 if x.state=='PASS' else 1)"
```

Expected: tests PASS and real census `state=PASS`, with zero unclassified findings and zero hash drift.

- [ ] **Step 7: Commit the registry**

```powershell
git add engine/perception/complexity_registry.py configs/complexity/complexity_module_registry_v1.json tests/test_complexity_registry.py
git diff --cached --check
git commit -m "feat(complexity): add exact module census"
```

### Task 3: Add the Immutable Case Packet and Ensemble Core

**Files:**
- Create: `engine/perception/complexity_ensemble.py`
- Create: `tests/test_complexity_ensemble.py`
- Create: `tests/complexity_benchmark_fixtures.py`

**Interfaces:**
- Consumes: `ComplexityRegistry`, adapter mapping from Task 4
- Produces: `ComplexityCasePacket.from_mapping`, `ModuleRun`, `ComplexityBundle`, `evaluate_complexity_case`, and `ablate_complexity_case`

- [ ] **Step 1: Write failing case and separation tests**

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.perception.complexity_ensemble import (
    ComplexityCasePacket,
    ablate_complexity_case,
    evaluate_complexity_case,
)
from engine.perception.complexity_registry import load_complexity_registry
from tests.complexity_benchmark_fixtures import valid_case_mapping

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = load_complexity_registry(
    ROOT,
    ROOT / "configs/complexity/complexity_module_registry_v1.json",
)


def test_case_packet_requires_exact_hashes_and_unique_relevance() -> None:
    packet = ComplexityCasePacket.from_mapping(valid_case_mapping())
    assert packet.case_id == "CX-A01"
    with pytest.raises(ValueError, match="relevant family"):
        ComplexityCasePacket.from_mapping({**valid_case_mapping(), "relevant_families": ["construction_profile", "construction_profile"]})


def test_ensemble_keeps_family_outputs_separate_and_has_no_overall_score() -> None:
    bundle = evaluate_complexity_case(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        REGISTRY,
        adapters={"construction_profile": lambda _payload: {"axes": {"formula_structure": {"status": "AVAILABLE"}}}},
    )
    encoded = json.dumps(bundle.as_dict(), sort_keys=True)
    assert bundle.state == "PASS"
    assert set(bundle.family_outputs) == {"construction_profile"}
    assert "overall_score" not in encoded
    assert bundle.formula_authority is False
    assert bundle.release_authority is False


def test_relevant_missing_input_and_omitted_guardrail_fail_closed() -> None:
    packet = ComplexityCasePacket.from_mapping(valid_case_mapping(
        relevant_families=("admission_lifecycle",),
        module_inputs={},
    ))
    result = evaluate_complexity_case(packet, REGISTRY, adapters={})
    assert result.state == "HOLD"
    assert "missing input" in " ".join(result.blockers)
    with pytest.raises(ValueError, match="mandatory guardrail"):
        ablate_complexity_case(packet, REGISTRY, omitted_family="admission_lifecycle", adapters={})
```

Create `tests/complexity_benchmark_fixtures.py` with this initial constructor:

```python
from __future__ import annotations

from typing import Any, Mapping

INVENTORY_WORKBOOK_SHA256 = "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
LOCAL_INVENTORY_SHA256 = "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
USEFUL_COMPLEXITY_DEFINITION = {
    "positive_evidence": [
        "identity-linked facets",
        "coherent perceptual planes, contrasts, and textures",
        "meaningful temporal unfolding",
        "testable hedonic-potential mechanisms",
        "restraint, spacing, dosage control, or negative space",
    ],
    "invalid_proxies": [
        "ingredient count", "module count", "interaction count",
        "descriptor count", "novelty", "response length", "jargon",
        "technical density",
    ],
    "claim_ceiling": "DESIGN_HYPOTHESIS_NOT_TESTED",
    "musk_policy": {
        "selection_rule": "one exact musk or distinct-role layers; never reward musk count",
        "exception_only_materials": ["Tonalide", "Macrolide", "Musk Ketone"],
        "exception_fields": [
            "target_tonal_role", "why_alternatives_fail", "loss_if_omitted",
            "failure_mode", "omission_control", "alternative_control",
        ],
        "current_depleted_exception_state": "HOLD_PROCUREMENT_REQUIRED",
    },
}


def valid_case_mapping(
    *,
    relevant_families: tuple[str, ...] = ("construction_profile",),
    module_inputs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    inputs = module_inputs
    if inputs is None:
        inputs = {"construction_profile": {
            "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}],
            "frames": [{
                "label": "opening",
                "t_seconds": 0.0,
                "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}],
            }],
            "inputs": {},
        }}
    return {
        "case_id": "CX-A01",
        "category": "TARGET_ARCHITECTURE",
        "target_name": "Compact Coherent Iris",
        "target_identity": "recognizable iris construction without row-count padding",
        "brief": "Audit architecture and preserve target identity.",
        "inventory_authority_sha256": INVENTORY_WORKBOOK_SHA256,
        "local_inventory_sha256": LOCAL_INVENTORY_SHA256,
        "inventory_reconciliation_state": "MATCH",
        "evidence_refs": ["fixture:cx-a01"],
        "evidence_sha256s": ["a" * 64],
        "relevant_families": list(relevant_families),
        "module_inputs": dict(inputs),
        "expected_invariants": {
            "complexity_definition": USEFUL_COMPLEXITY_DEFINITION,
            "anti_complication_case": True,
            "required_depth_fields": [
                "identity_linked_facets", "coherent_richness",
                "temporal_unfolding", "restraint_or_subtraction",
                "hedonic_potential_hypotheses", "complication_risks",
            ],
            "forbidden_claims": [
                "row count proves quality",
                "more ingredients means more richness",
                "hedonic success is tested",
            ],
        },
        "permitted_claim_ceiling": "COMPUTATIONAL_DESIGN_ONLY",
        "nonce": "CX-A01-0123456789abcdef",
    }
```

- [ ] **Step 2: Run tests to verify import failure**

Run: `python -m pytest tests/test_complexity_ensemble.py -q -p no:cacheprovider`

Expected: FAIL with missing module import.

- [ ] **Step 3: Implement the immutable packet**

```python
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping

from engine.calibration.hashing import stable_json_hash


def _sha256(value: object) -> str:
    normalized = str(value).strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        raise ValueError("SHA-256 must be 64 lowercase hexadecimal characters")
    return normalized


@dataclass(frozen=True, slots=True)
class ComplexityCasePacket:
    case_id: str
    category: str
    target_name: str
    target_identity: str
    brief: str
    inventory_authority_sha256: str
    local_inventory_sha256: str
    inventory_reconciliation_state: str
    evidence_refs: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    relevant_families: tuple[str, ...]
    module_inputs: Mapping[str, Mapping[str, Any]]
    expected_invariants: Mapping[str, Any]
    permitted_claim_ceiling: str
    nonce: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ComplexityCasePacket":
        required = {
            "case_id", "category", "target_name", "target_identity", "brief",
            "inventory_authority_sha256", "local_inventory_sha256",
            "inventory_reconciliation_state", "evidence_refs",
            "evidence_sha256s", "relevant_families", "module_inputs",
            "expected_invariants", "permitted_claim_ceiling", "nonce",
        }
        if set(value) != required:
            raise ValueError("case packet keys must match the v1 contract exactly")
        relevant = tuple(str(item).strip() for item in value["relevant_families"])
        if not relevant or len(relevant) != len(set(relevant)):
            raise ValueError("relevant family IDs must be nonempty and unique")
        inputs = {str(key): dict(item) for key, item in value["module_inputs"].items()}
        if not set(inputs).issubset(relevant):
            raise ValueError("module input keys must be relevant family IDs")
        packet = cls(
            case_id=str(value["case_id"]).strip(),
            category=str(value["category"]).strip(),
            target_name=str(value["target_name"]).strip(),
            target_identity=str(value["target_identity"]).strip(),
            brief=str(value["brief"]).strip(),
            inventory_authority_sha256=_sha256(value["inventory_authority_sha256"]),
            local_inventory_sha256=_sha256(value["local_inventory_sha256"]),
            inventory_reconciliation_state=str(value["inventory_reconciliation_state"]),
            evidence_refs=tuple(str(item) for item in value["evidence_refs"]),
            evidence_sha256s=tuple(_sha256(item) for item in value["evidence_sha256s"]),
            relevant_families=relevant,
            module_inputs=inputs,
            expected_invariants=dict(value["expected_invariants"]),
            permitted_claim_ceiling=str(value["permitted_claim_ceiling"]).strip(),
            nonce=str(value["nonce"]).strip(),
        )
        packet._validate()
        return packet

    def _validate(self) -> None:
        if self.inventory_reconciliation_state != "MATCH":
            raise ValueError("inventory reconciliation must be MATCH")
        if re.fullmatch(r"CX-[A-D][0-9]{2}-[0-9a-f]{16}", self.nonce) is None:
            raise ValueError("nonce must match the case-bound v1 format")
        if any(not field for field in (self.case_id, self.target_name, self.target_identity, self.brief, self.permitted_claim_ceiling)):
            raise ValueError("case text fields must not be blank")

    @property
    def input_sha256(self) -> str:
        return stable_json_hash(self.as_dict(include_hash=False))

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "case_id": self.case_id,
            "category": self.category,
            "target_name": self.target_name,
            "target_identity": self.target_identity,
            "brief": self.brief,
            "inventory_authority_sha256": self.inventory_authority_sha256,
            "local_inventory_sha256": self.local_inventory_sha256,
            "inventory_reconciliation_state": self.inventory_reconciliation_state,
            "evidence_refs": list(self.evidence_refs),
            "evidence_sha256s": list(self.evidence_sha256s),
            "relevant_families": list(self.relevant_families),
            "module_inputs": {key: dict(value) for key, value in self.module_inputs.items()},
            "expected_invariants": dict(self.expected_invariants),
            "permitted_claim_ceiling": self.permitted_claim_ceiling,
            "nonce": self.nonce,
        }
        if include_hash:
            payload["input_sha256"] = self.input_sha256
        return payload
```

Validate the exact two inventory hashes, `inventory_reconciliation_state == "MATCH"`, unique sorted evidence hashes and relevant families, module input keys as a subset of relevant families, nonblank claim ceiling, and nonce pattern `CX-[A-D][0-9]{2}-[0-9a-f]{16}`.

Validate `expected_invariants.complexity_definition` against the frozen
`USEFUL_COMPLEXITY_DEFINITION`. This semantic contract is common benchmark input,
not a treatment hint: both arms must receive it byte-for-byte. It defines useful
complexity as integrated perceptual depth and explicitly rejects complication
proxies. Do not derive a richness or hedonic score inside the ensemble.

- [ ] **Step 4: Implement separated evaluation and ablation**

```python
Adapter = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ModuleRun:
    family_id: str
    state: str
    input_sha256: str | None
    output_sha256: str | None
    blocker: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComplexityBundle:
    case_id: str
    state: str
    case_input_sha256: str
    registry_sha256: str
    omitted_families: tuple[str, ...]
    family_outputs: Mapping[str, Mapping[str, Any]]
    module_runs: tuple[ModuleRun, ...]
    blockers: tuple[str, ...]
    formula_authority: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "state": self.state,
            "case_input_sha256": self.case_input_sha256,
            "registry_sha256": self.registry_sha256,
            "omitted_families": list(self.omitted_families),
            "family_outputs": {key: dict(value) for key, value in self.family_outputs.items()},
            "module_runs": [item.as_dict() for item in self.module_runs],
            "blockers": list(self.blockers),
            "formula_authority": self.formula_authority,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }


def evaluate_complexity_case(
    case: ComplexityCasePacket,
    registry: ComplexityRegistry,
    *,
    adapters: Mapping[str, Adapter],
    omitted_families: frozenset[str] = frozenset(),
) -> ComplexityBundle:
    outputs: dict[str, Mapping[str, Any]] = {}
    runs: list[ModuleRun] = []
    blockers: list[str] = []
    for family_id in case.relevant_families:
        descriptors = registry.modules_for_family(family_id)
        if not descriptors or not any(item.runtime_eligible for item in descriptors):
            blockers.append(f"{family_id}: no runtime-eligible module")
            continue
        if family_id in omitted_families:
            runs.append(ModuleRun(family_id, "OMITTED", None, None, None))
            continue
        payload = case.module_inputs.get(family_id)
        adapter = adapters.get(family_id)
        if payload is None or adapter is None:
            blockers.append(f"{family_id}: missing input or adapter")
            continue
        input_sha256 = stable_json_hash(payload)
        try:
            output = dict(adapter(payload))
        except (TypeError, ValueError) as exc:
            blockers.append(f"{family_id}: {exc}")
            runs.append(ModuleRun(family_id, "HOLD", input_sha256, None, str(exc)))
            continue
        outputs[family_id] = output
        runs.append(ModuleRun(family_id, "PASS", input_sha256, stable_json_hash(output), None))
    return ComplexityBundle(
        case_id=case.case_id,
        state="HOLD" if blockers else "PASS",
        case_input_sha256=case.input_sha256,
        registry_sha256=registry.registry_sha256,
        omitted_families=tuple(sorted(omitted_families)),
        family_outputs=outputs,
        module_runs=tuple(runs),
        blockers=tuple(blockers),
    )


def ablate_complexity_case(
    case: ComplexityCasePacket,
    registry: ComplexityRegistry,
    *,
    omitted_family: str,
    adapters: Mapping[str, Adapter],
) -> ComplexityBundle:
    if registry.family_role(omitted_family) is ModuleRole.GUARDRAIL:
        raise ValueError("mandatory guardrail cannot be omitted from normal treatment")
    return evaluate_complexity_case(
        case,
        registry,
        adapters=adapters,
        omitted_families=frozenset({omitted_family}),
    )
```

`evaluate_complexity_case` must catch adapter exceptions as module failures and HOLD the bundle; it must not hide exceptions, skip relevant families, aggregate scores, or mutate the packet. `ablate_complexity_case` records exactly one omission and rejects omission of a mandatory guardrail during normal treatment generation.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_complexity_ensemble.py tests/test_complexity_registry.py -q -p no:cacheprovider`

Expected: PASS.

```powershell
git add engine/perception/complexity_ensemble.py tests/test_complexity_ensemble.py tests/complexity_benchmark_fixtures.py
git commit -m "feat(complexity): add separated ensemble contract"
```

### Task 3A: Add the Clean-Room Musk Design Restraint Family

**Files:**
- Create: `engine/perception/musk_design.py`
- Create: `tests/test_musk_design.py`
- Modify: `configs/complexity/complexity_module_registry_v1.json`
- Modify by exact musk-policy hunk only: `AGENTS.md`
- Modify by exact musk-policy hunk only: `.github/copilot-instructions.md`

**Interfaces:**
- Produces: `MuskRole`, `InventoryState`, `MuskExceptionCall`, `MuskCandidate`, `MuskDesignRequest`, `MuskMaterialDecision`, `MuskDesignResult`, `evaluate_musk_design`
- Constant: `EXCEPTION_ONLY_MUSKS = frozenset({"tonalide", "macrolide", "musk ketone"})`
- No external imports, dosage recommendations, aggregate scores, or formula/sensory/safety/release authority

- [ ] **Step 1: Write the failing behavior tests**

Before each test, name the mutation it catches: forcing a chord, accepting
redundant layers, leaking an exception-only musk, or converting an ideal-design
exception into physical stock.

```python
from __future__ import annotations

import pytest

from engine.perception.musk_design import (
    InventoryState,
    MuskCandidate,
    MuskDesignRequest,
    MuskExceptionCall,
    MuskRole,
    evaluate_musk_design,
)


def _exception(material: str) -> MuskExceptionCall:
    return MuskExceptionCall(
        material=material,
        target_tonal_role="specific vintage powder echo",
        why_alternatives_fail="clean musks remove the requested period powder tension",
        loss_if_omitted="the dry powder-to-skin transition disappears",
        failure_mode="talc overload and dated blur",
        omission_control="same architecture with the material omitted",
        alternative_control="same architecture with Exaltolide in the same role",
    )


def test_one_precise_musk_is_valid_without_forcing_a_chord() -> None:
    result = evaluate_musk_design(MuskDesignRequest(
        target_identity="quiet skin aura with negative space",
        candidates=(MuskCandidate(
            material="Zenolide",
            role=MuskRole.DEPTH,
            target_function="one clean skin-depth plane without laundry bloom",
            why_nonredundant="the architecture has no other musk plane",
            inventory_state=InventoryState.OWNED,
            exact_stock_ref="inventory:Zenolide:neat",
        ),),
    ))
    assert result.state == "PASS"
    assert result.architecture_mode == "SPARSE"
    assert [item.material for item in result.selected] == ["Zenolide"]


def test_layered_musks_with_the_same_role_fail_as_redundant() -> None:
    result = evaluate_musk_design(MuskDesignRequest(
        target_identity="transparent skin depth",
        candidates=(
            MuskCandidate("Zenolide", MuskRole.DEPTH, "skin depth", "first depth plane", InventoryState.OWNED, "inventory:Zenolide:neat"),
            MuskCandidate("Exaltolide", MuskRole.DEPTH, "more skin depth", "second depth plane", InventoryState.OWNED, "inventory:Exaltolide:10pct"),
        ),
    ))
    assert result.state == "HOLD"
    assert "REDUNDANT_MUSK_ROLE" in result.issue_codes


@pytest.mark.parametrize("material", ["Tonalide", "Macrolide", "Musk Ketone"])
def test_exception_only_musks_are_omitted_without_a_design_call(material: str) -> None:
    result = evaluate_musk_design(MuskDesignRequest(
        target_identity="clean restrained musk",
        candidates=(MuskCandidate(
            material, MuskRole.CHARACTER_ECHO, "generic musk support",
            "no unique function supplied", InventoryState.DEPLETED, None,
        ),),
    ))
    assert result.state == "HOLD"
    assert result.selected == ()
    assert result.decisions[0].disposition == "OMITTED_EXCEPTION_REQUIRED"
    assert "MUSK_EXCEPTION_REQUIRED" in result.issue_codes


def test_complete_depleted_exception_can_enter_target_but_not_build() -> None:
    result = evaluate_musk_design(MuskDesignRequest(
        target_identity="vintage iris powder with dry skin tension",
        candidates=(MuskCandidate(
            "Musk Ketone", MuskRole.CHARACTER_ECHO,
            "echo the target's period talc register",
            "modern clean musks change the period identity",
            InventoryState.DEPLETED, None, _exception("Musk Ketone"),
        ),),
    ))
    assert result.state == "PASS"
    assert result.target_ideal_state == "DESIGN_AVAILABLE"
    assert result.current_inventory_build_state == "HOLD_PROCUREMENT_REQUIRED"
    assert result.selected[0].material == "Musk Ketone"
    assert result.formula_authority is False
    assert result.physical_execution_authorized is False


def test_incomplete_exception_call_is_rejected() -> None:
    with pytest.raises(ValueError, match="alternative control"):
        MuskExceptionCall(
            material="Tonalide",
            target_tonal_role="warm cosmetic fabric tone",
            why_alternatives_fail="alternatives are too clean",
            loss_if_omitted="warm fabric shadow is lost",
            failure_mode="laundry sweetness and blur",
            omission_control="same formula without Tonalide",
            alternative_control="",
        )
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_musk_design.py -q -p no:cacheprovider`

Expected: FAIL because `engine.perception.musk_design` does not exist. A syntax,
fixture, or import-path error unrelated to the missing production module is not
an accepted RED state.

- [ ] **Step 3: Implement the minimal immutable policy**

Use `str, Enum` values for the six roles `DEPTH`, `PROJECTION`, `TEXTURE`,
`TEMPORAL_BRIDGE`, `CHARACTER_ECHO`, and `FIXATION`; inventory states `OWNED`,
`PLANNED_ACQUISITION`, `DEPLETED`, `MISSING`, and `UNKNOWN`; and frozen slotted
dataclasses. Every human-entered field is stripped and validated nonblank.

`evaluate_musk_design` must:

1. normalize names only for exception matching while preserving display names;
2. reject duplicate candidate materials;
3. require target function and nonredundancy for every selected candidate;
4. allow one valid ordinary candidate as `SPARSE`;
5. call two or more selected candidates `LAYERED` only when roles are unique;
6. omit an exception-only candidate and HOLD with `MUSK_EXCEPTION_REQUIRED`
   unless every exception field is present and bound to the same material;
7. allow a complete exception into target/ideal design while returning
   `HOLD_PROCUREMENT_REQUIRED` for the current-inventory build when stock is not
   `OWNED` with a nonblank `ExactStockRef`;
8. return deterministic tuples sorted by input order, explicit issue codes, and
   all formula, physical, sensory, safety, and release authority flags false;
9. emit no dose, OAV, beauty, complexity, richness, or hedonic scalar score.

- [ ] **Step 4: Verify GREEN and add the sixth registry family**

Run the focused test until all tests pass. Compute the new module's exact SHA-256
and add `musk_design_restraint` as `ACTIVE_CANDIDATE`; add
`future_modules/advanced_musk_intelligence.py` with its exact current hash as
`FUTURE_CANDIDATE_NOT_VALIDATED`, no import path, and no runtime eligibility.
Rerun the registry census and prove the future file is discovered but never
imported.

- [ ] **Step 5: Align human guidance without forcing a musk count**

In `AGENTS.md` and `.github/copilot-instructions.md`, replace only the fixed
two-to-three-musk requirement. State that one precise musk is valid, multiple
musks require distinct nonredundant depth/projection/texture/temporal/character
roles, and Tonalide/Macrolide/Musk Ketone are exception-only under the complete
design-call and inventory-separation contract. Do not change unrelated user
instructions.

- [ ] **Step 6: Run focused regression and commit exact paths**

```powershell
python -m pytest tests/test_musk_design.py tests/test_complexity_registry.py -q -p no:cacheprovider
git add engine/perception/musk_design.py tests/test_musk_design.py configs/complexity/complexity_module_registry_v1.json
git add -p AGENTS.md .github/copilot-instructions.md
git diff --cached --name-status
git commit -m "feat(complexity): add restrained musk design family"
```

### Task 4: Add Native Family Adapters

**Files:**
- Create: `engine/perception/complexity_adapters.py`
- Create: `tests/test_complexity_adapters.py`
- Modify: `tests/complexity_benchmark_fixtures.py`

**Interfaces:**
- Consumes: JSON `module_inputs` from `ComplexityCasePacket`
- Produces: `DEFAULT_COMPLEXITY_ADAPTERS: Mapping[str, Adapter]`
- Each adapter returns canonical JSON-compatible data with `result_sha256`, `claim_ceiling`, `formula_authority=false`, `physical_execution_authorized=false`, `sensory_authority=false`, and `release_authority=false`

- [ ] **Step 1: Write failing adapter tests**

```python
from __future__ import annotations

import json

import pytest

from engine.perception.complexity_adapters import (
    adapt_admission_lifecycle,
    adapt_construction_profile,
    adapt_expansion_frontier,
    adapt_experimental_design,
    adapt_musk_design,
    adapt_temporal_sensory,
)
from tests.complexity_benchmark_fixtures import (
    admission_payload,
    causal_payload,
    expansion_payload,
    musk_payload,
    within_sniff_payload,
)


def test_construction_adapter_calls_native_multi_axis_profile() -> None:
    result = adapt_construction_profile({
        "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}],
        "frames": [{"label": "opening", "t_seconds": 0.0, "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}]}],
        "inputs": {"foreground_materials": ["A"]}
    })
    assert result["schema_version"] == "construction_complexity_profile_v1"
    assert "overall_score" not in json.dumps(result)


def test_expansion_adapter_preserves_no_formula_authority() -> None:
    result = adapt_expansion_frontier(expansion_payload())
    assert result["registry_audit"]["state"] == "PASS"
    assert result["registry_audit"]["formula_authority"] is False


def test_musk_adapter_preserves_sparse_selection_and_exception_holds() -> None:
    sparse = adapt_musk_design(musk_payload())
    assert sparse["architecture_mode"] == "SPARSE"
    assert [item["material"] for item in sparse["selected"]] == ["Zenolide"]
    blocked = adapt_musk_design(musk_payload(material="Tonalide", exception_call=None, inventory_state="DEPLETED"))
    assert blocked["state"] == "HOLD"
    assert "MUSK_EXCEPTION_REQUIRED" in blocked["issue_codes"]


@pytest.mark.parametrize("adapter,payload", [
    (adapt_experimental_design, causal_payload()),
    (adapt_admission_lifecycle, admission_payload()),
    (adapt_temporal_sensory, within_sniff_payload()),
])
def test_guardrail_adapters_emit_no_execution_or_release_authority(adapter, payload) -> None:
    result = adapter(payload)
    encoded = json.dumps(result, sort_keys=True)
    assert '"physical_execution_authorized": true' not in encoded
    assert '"sensory_authority": true' not in encoded
    assert '"release_authority": true' not in encoded
```

Extend `tests/complexity_benchmark_fixtures.py` with five explicit mapping builders:

- `expansion_payload()` contains domains `DX-01`/`DX-02`, directions `ED-001`/`ED-002`, source hash `"a" * 64`, and explicit frontier scores `(0.8, 0.8)` and `(0.6, 0.9)`.
- `causal_payload()` serializes the exact NULL/intermediate/FULL design from `tests/test_complexity_design_contracts.py:144`, including the three invariant hashes and bound stock/active/carrier totals.
- `admission_payload()` serializes a non-formula DESIGN packet with every gate returned by `required_complexity_gates(ComplexityClaimScope.DESIGN)` in PASS state and `repository_canary_pass=false`.
- `within_sniff_payload()` serializes the DESIGN_ONLY pulse-olfactometer sequence from `tests/test_within_sniff.py:37`, including two reversed pulse orders and the screening OAV binding.
- `musk_payload()` defaults to one owned Zenolide depth candidate with a nonblank `ExactStockRef`; keyword overrides can replace material, inventory state, and the complete exception-call mapping without generating dosage or sensory claims.

These builders return JSON mappings only; do not import private helper functions from the existing test modules.

- [ ] **Step 2: Run tests to verify import failure**

Run: `python -m pytest tests/test_complexity_adapters.py -q -p no:cacheprovider`

Expected: FAIL with missing adapter module.

- [ ] **Step 3: Implement construction and expansion adapters**

Use private frozen view classes for construction JSON:

```python
@dataclass(frozen=True, slots=True)
class _MaterialView:
    name: str
    oav: float | None
    intensity: float | None
    is_known: bool = True
    is_opaque_preblend: bool = False
    functional_groups: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _StateView:
    materials: tuple[_MaterialView, ...]


@dataclass(frozen=True, slots=True)
class _FrameView:
    label: str
    t_seconds: float
    state: _StateView
```

`adapt_construction_profile` builds these views, creates `ConstructionComplexityInputs`, invokes `analyze_construction_complexity`, and returns `as_dict()`.

`adapt_expansion_frontier` invokes `audit_expansion_registry`, converts only valid directions with `ExpansionDirection.from_mapping`, runs `pareto_experiment_frontier` from explicit impact/information-gain values, and reports bounded saturation only when discovery rounds are present.

- [ ] **Step 4: Implement scientific and sensory adapters**

Supported `operation` values are exact and closed:

```python
EXPERIMENTAL_OPERATIONS = {
    "causal_isolate": evaluate_causal_isolate,
    "formula_signature": compare_formula_signatures,
    "nary_interaction": evaluate_nary_interaction,
}
ADMISSION_OPERATIONS = {
    "model_admission": evaluate_complexity_model_admission,
    "model_drift": assess_model_drift,
}
SENSORY_OPERATIONS = {
    "within_sniff": evaluate_within_sniff_sequence,
    "temporal_observations": summarize_temporal_observations,
    "order_balance": assess_order_balance,
    "panel_exit": evaluate_c0_exit,
}
```

Each parser must construct the existing frozen native dataclasses, use `Decimal(str(value))` for decimal fields, reject unknown keys or operations, and preserve native `as_dict()` outputs. Do not reinterpret a native HOLD as PASS.

`adapt_musk_design` must construct only the public frozen types from
`engine.perception.musk_design`, reject unknown payload keys, invoke
`evaluate_musk_design`, and preserve the separate target/ideal and
current-inventory build states. It must never consult or import
`future_modules.advanced_musk_intelligence`.

- [ ] **Step 5: Add the default adapter mapping**

```python
DEFAULT_COMPLEXITY_ADAPTERS = {
    "construction_profile": adapt_construction_profile,
    "expansion_frontier": adapt_expansion_frontier,
    "experimental_design": adapt_experimental_design,
    "admission_lifecycle": adapt_admission_lifecycle,
    "temporal_sensory_integrity": adapt_temporal_sensory,
    "musk_design_restraint": adapt_musk_design,
}
```

- [ ] **Step 6: Run focused native and adapter tests**

Run Task 1's native suite plus `tests/test_musk_design.py`, `tests/test_complexity_adapters.py`, and `tests/test_complexity_ensemble.py`.

Expected: all pass; no authority field is promoted.

- [ ] **Step 7: Commit adapters**

```powershell
git add engine/perception/complexity_adapters.py tests/test_complexity_adapters.py tests/complexity_benchmark_fixtures.py
git commit -m "feat(complexity): adapt native module families"
```

### Task 5: Freeze the 16-Case Corpus and Deterministic Rubric

**Files:**
- Create: `tests/fixtures/complexity_xhigh_cases_v1.json`
- Create: `tests/fixtures/complexity_xhigh_cases_v1.sha256`
- Extend: `tests/test_complexity_ensemble.py`

**Interfaces:**
- Produces: exactly 16 `ComplexityCasePacket` mappings, expected structured-response invariants, hard-gate traps, relevance maps, and dimension scoring keys

- [ ] **Step 1: Write the failing corpus contract test**

```python
def test_frozen_corpus_has_four_cases_per_category_and_exact_hash() -> None:
    payload = json.loads(CASES.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "complexity_xhigh_cases_v1"
    assert len(payload["cases"]) == 16
    counts = Counter(case["category"] for case in payload["cases"])
    assert counts == {
        "TARGET_ARCHITECTURE": 4,
        "RECONSTRUCTION_REVISION": 4,
        "MISSING_CHEMICAL_IMPACT": 4,
        "EXPERIMENTAL_EVIDENCE_DESIGN": 4,
    }
    assert sum(bool(case["critical_traps"]) for case in payload["cases"]) >= 4
    assert sum(bool(case["expected_invariants"]["anti_complication_case"]) for case in payload["cases"]) >= 8
    assert hashlib.sha256(canonical_json_bytes(payload)).hexdigest() == SIDECAR.read_text().split()[0]


def test_every_case_binds_current_inventory_and_declares_relevance() -> None:
    for raw in _cases():
        case = ComplexityCasePacket.from_mapping(raw)
        assert case.inventory_authority_sha256 == "e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331"
        assert case.local_inventory_sha256 == "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
        assert case.relevant_families
        definition = case.expected_invariants["complexity_definition"]
        assert definition["claim_ceiling"] == "DESIGN_HYPOTHESIS_NOT_TESTED"
        assert "ingredient count" in definition["invalid_proxies"]


def test_anti_complication_cases_cover_required_failure_modes() -> None:
    cases = [case for case in _cases() if case["expected_invariants"]["anti_complication_case"]]
    covered = {
        mode
        for case in cases
        for mode in case["expected_invariants"]["complication_failure_modes"]
    }
    assert {
        "BLOAT", "REDUNDANCY", "MUD", "SUPERFICIAL_DIVERSITY",
        "FLAT_DEVELOPMENT", "INCOHERENT_NOVELTY", "NEEDED_SUBTRACTION",
    }.issubset(covered)


def test_musk_cases_cover_sparse_layered_and_all_named_exceptions() -> None:
    cases = [case for case in _cases() if "musk_design_restraint" in case["relevant_families"]]
    assert len(cases) >= 4
    modes = {case["expected_invariants"]["musk_case_mode"] for case in cases}
    assert {"SPARSE", "LAYERED", "EXCEPTION_BLOCK", "EXCEPTION_TARGET_ONLY"}.issubset(modes)
    materials = {
        material
        for case in cases
        for material in case["expected_invariants"].get("exception_materials", [])
    }
    assert materials == {"Tonalide", "Macrolide", "Musk Ketone"}
```

- [ ] **Step 2: Run the corpus test to verify missing fixture failure**

Run: `python -m pytest tests/test_complexity_ensemble.py -k frozen_corpus -q -p no:cacheprovider`

Expected: FAIL because the fixture is absent.

- [ ] **Step 3: Create the exact case set**

Use these fixed IDs and purposes:

| ID | Category | Purpose | Relevant families |
|---|---|---|---|
| `CX-A01` | TARGET_ARCHITECTURE | compact formula whose one exact musk, restraint, and negative space create legible depth; reject row-count and musk-count prejudice | construction, musk design |
| `CX-A02` | TARGET_ARCHITECTURE | bloated, redundant formula; diagnose mud and recover identity by subtraction without a beauty score | construction |
| `CX-A03` | TARGET_ARCHITECTURE | modeled temporal transition that adds reveal and return-to-smell potential; preserve modeled-vs-perceived boundary | construction, temporal/sensory |
| `CX-A04` | TARGET_ARCHITECTURE | superficial descriptor diversity with insufficient evidence; reject descriptor count as richness and require abstention | construction |
| `CX-B01` | RECONSTRUCTION_REVISION | stock rebase against immediate parent | experimental design, admission/lifecycle |
| `CX-B02` | RECONSTRUCTION_REVISION | target/ideal versus current-inventory build separation; validate a layered musk chord only when every role is distinct | construction, musk design, admission/lifecycle |
| `CX-B03` | RECONSTRUCTION_REVISION | conflicting same-scope sources; require HOLD | admission/lifecycle |
| `CX-B04` | RECONSTRUCTION_REVISION | natural mixture with monomolecular OAV trap | admission/lifecycle |
| `CX-C01` | MISSING_CHEMICAL_IMPACT | Ambrettolide planned acquisition, not physically owned | expansion, admission/lifecycle |
| `CX-C02` | MISSING_CHEMICAL_IMPACT | genuine missing function whose contrast or temporal role could add identity-linked depth | construction, expansion |
| `CX-C03` | MISSING_CHEMICAL_IMPACT | generic Tonalide padding is blocked as redundant complication without an exception | expansion, musk design |
| `CX-C04` | MISSING_CHEMICAL_IMPACT | depleted Macrolide has a complete target-linked exception; target-only design passes while current build remains procurement HOLD | expansion, musk design, admission/lifecycle |
| `CX-D01` | EXPERIMENTAL_EVIDENCE_DESIGN | exact null/full causal isolate with matched invariants | experimental design |
| `CX-D02` | EXPERIMENTAL_EVIDENCE_DESIGN | dense n-ary interaction hypothesis; distinguish coherent emergence from muddy interaction count without empirical promotion | experimental design, admission/lifecycle |
| `CX-D03` | EXPERIMENTAL_EVIDENCE_DESIGN | flat static blotter mislabeled as within-sniff delivery; test temporal depth rather than change count | temporal/sensory |
| `CX-D04` | EXPERIMENTAL_EVIDENCE_DESIGN | Musk Ketone exception with omission/alternative controls plus an unbound panel and false physical richness/liking trap | musk design, temporal/sensory, admission/lifecycle |

Use full family IDs from `DEFAULT_COMPLEXITY_ADAPTERS`, not the shortened labels in the table. Each case's `expected_invariants` must contain an exact `valid_response` contract for the six rubric dimensions, the frozen `complexity_definition`, `anti_complication_case`, `complication_failure_modes`, `required_depth_fields`, `required_claim_states`, `forbidden_claims`, `required_sections`, and `critical_traps`. Musk-bearing cases also contain `musk_case_mode`, `exception_materials`, role/nonredundancy expectations, and target/build inventory expectations. At least eight cases set `anti_complication_case=true`; the full corpus covers every required failure mode in the tests above.

- [ ] **Step 4: Freeze the canonical fixture hash**

Run:

```powershell
python -c "import hashlib,json,pathlib; from engine.calibration.hashing import canonical_json_bytes; p=pathlib.Path('tests/fixtures/complexity_xhigh_cases_v1.json'); x=json.loads(p.read_text(encoding='utf-8')); h=hashlib.sha256(canonical_json_bytes(x)).hexdigest(); pathlib.Path('tests/fixtures/complexity_xhigh_cases_v1.sha256').write_text(h+'  complexity_xhigh_cases_v1.json\n',encoding='utf-8')"
```

This formatting command is allowed; do not use Python to edit implementation files.

- [ ] **Step 5: Run corpus and ensemble tests**

Expected: PASS with exactly 16 valid packets and zero inventory-hash drift.

- [ ] **Step 6: Commit the frozen corpus**

```powershell
git add tests/fixtures/complexity_xhigh_cases_v1.json tests/fixtures/complexity_xhigh_cases_v1.sha256 tests/test_complexity_ensemble.py
git commit -m "test(complexity): freeze xhigh benchmark corpus"
```

### Task 6: Add Sealed ChatGPT xhigh Request and Receipt Contracts

**Files:**
- Create: `engine/perception/complexity_xhigh.py`
- Create: `tests/test_complexity_xhigh_contract.py`
- Modify: `tests/complexity_benchmark_fixtures.py`

**Interfaces:**
- Produces: `BenchmarkArm`, `XHighRequest`, `XHighExecutionReceipt`, `prepare_xhigh_request`, `validate_xhigh_execution`, `anonymize_response_pair`
- No function in this file sends a network request

- [ ] **Step 1: Write failing xhigh contract tests**

```python
from __future__ import annotations

from dataclasses import replace

from engine.perception.complexity_ensemble import ComplexityCasePacket
from engine.perception.complexity_xhigh import (
    BenchmarkArm,
    prepare_xhigh_request,
    validate_xhigh_execution,
)
from tests.complexity_benchmark_fixtures import (
    valid_bundle,
    valid_case_mapping,
    valid_execution_receipt,
)


def test_control_excludes_module_bundle_and_treatment_includes_only_bundle_delta() -> None:
    case = ComplexityCasePacket.from_mapping(valid_case_mapping())
    bundle = valid_bundle(case)
    control = prepare_xhigh_request(case, BenchmarkArm.CONTROL, bundle=None)
    treatment = prepare_xhigh_request(case, BenchmarkArm.TREATMENT, bundle=bundle)
    assert "module_bundle" not in control.prompt_payload
    assert treatment.prompt_payload["module_bundle"] == bundle.as_dict()
    assert control.common_input_sha256 == treatment.common_input_sha256
    assert control.nonce != treatment.nonce
    assert control.prompt_payload["complexity_definition"] == treatment.prompt_payload["complexity_definition"]
    assert control.prompt_payload["complexity_definition"]["claim_ceiling"] == "DESIGN_HYPOTHESIS_NOT_TESTED"
    assert "ingredient count" in control.prompt_payload["complexity_definition"]["invalid_proxies"]


def test_unverified_model_effort_context_or_duplicate_nonce_blocks() -> None:
    request = prepare_xhigh_request(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        BenchmarkArm.CONTROL,
        bundle=None,
    )
    for field, bad in (("reasoning_effort", "high"), ("context_clean", False), ("completion_state", "AMBIGUOUS")):
        receipt = replace(valid_execution_receipt(request), **{field: bad})
        result = validate_xhigh_execution(request, receipt, seen_nonces=frozenset())
        assert result.state.startswith("BENCHMARK_BLOCKED")
    duplicate = validate_xhigh_execution(request, valid_execution_receipt(request), seen_nonces=frozenset({request.nonce}))
    assert duplicate.state == "BENCHMARK_BLOCKED_DUPLICATE_NONCE"


def test_product_telemetry_is_not_estimated_when_absent() -> None:
    request = prepare_xhigh_request(
        ComplexityCasePacket.from_mapping(valid_case_mapping()),
        BenchmarkArm.CONTROL,
        bundle=None,
    )
    receipt = replace(valid_execution_receipt(request), input_tokens=None, output_tokens=None, price_usd=None)
    assert receipt.telemetry_state == "NOT_EXPOSED"
```

Extend `tests/complexity_benchmark_fixtures.py` with these exact constructors after the Task 6 types exist:

```python
def valid_bundle(case: ComplexityCasePacket) -> ComplexityBundle:
    output = {"axes": {"formula_structure": {"status": "AVAILABLE"}}}
    return ComplexityBundle(
        case_id=case.case_id,
        state="PASS",
        case_input_sha256=case.input_sha256,
        registry_sha256="b" * 64,
        omitted_families=(),
        family_outputs={"construction_profile": output},
        module_runs=(),
        blockers=(),
    )


def valid_execution_receipt(request: XHighRequest) -> XHighExecutionReceipt:
    return XHighExecutionReceipt(
        request_id=request.request_id,
        nonce=request.nonce,
        provider="OpenAI",
        product="ChatGPT",
        model_identity="ChatGPT-current",
        reasoning_effort="xhigh",
        context_clean=True,
        prior_case_transcript_visible=False,
        prompt_sha256=request.prompt_sha256,
        attachment_sha256s=request.attachment_sha256s,
        submitted_at="2026-08-22T10:00:00Z",
        completed_at="2026-08-22T10:01:00Z",
        completion_state="SUCCEEDED",
        conversation_id="chatgpt:test-cx-a01-control",
        response_sha256="c" * 64,
        input_tokens=1000,
        output_tokens=500,
        latency_ms=60000,
        price_usd=Decimal("1.00"),
    )
```

- [ ] **Step 2: Run tests to verify import failure**

Run: `python -m pytest tests/test_complexity_xhigh_contract.py -q -p no:cacheprovider`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement the sealed request contract**

```python
class BenchmarkArm(str, Enum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"
    ABLATION = "ABLATION"


@dataclass(frozen=True, slots=True)
class XHighRequest:
    request_id: str
    case_id: str
    arm: BenchmarkArm
    nonce: str
    model_requirement: str
    reasoning_effort: str
    common_input_sha256: str
    prompt_payload: Mapping[str, Any]
    prompt_sha256: str
    attachment_sha256s: tuple[str, ...]
```

The common output contract requires one JSON object with these keys:

```text
target_identity
functional_architecture
depth_and_richness_analysis
target_ideal_formula
current_inventory_build
missing_chemical_impact
controlled_test_plan
claims
conflicts_and_holds
answer_markdown
```

Reject extra top-level keys. `depth_and_richness_analysis` requires
`identity_linked_facets`, `coherent_richness`, `temporal_unfolding`,
`restraint_or_subtraction`, `hedonic_potential_hypotheses`, and
`complication_risks`. Every hedonic-potential hypothesis must state
`DESIGN_HYPOTHESIS_NOT_TESTED`, identify a target-linked mechanism, and specify a
controlled sensory comparison; raw counts and response length are forbidden as
support. Formula fields may be `null` when the case is not formula-bearing.
Every claim requires `claim`, `state`, `evidence_refs`, and `authority_ceiling`.

- [ ] **Step 4: Implement exact execution receipts and validation**

```python
@dataclass(frozen=True, slots=True)
class XHighExecutionReceipt:
    request_id: str
    nonce: str
    provider: str
    product: str
    model_identity: str
    reasoning_effort: str
    context_clean: bool
    prior_case_transcript_visible: bool
    prompt_sha256: str
    attachment_sha256s: tuple[str, ...]
    submitted_at: str
    completed_at: str
    completion_state: str
    conversation_id: str
    response_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    price_usd: Decimal | None

    @property
    def telemetry_state(self) -> str:
        values = (self.input_tokens, self.output_tokens, self.latency_ms, self.price_usd)
        if all(value is None for value in values):
            return "NOT_EXPOSED"
        if all(value is not None for value in values):
            return "EXPOSED"
        return "PARTIAL"
```

`validate_xhigh_execution` requires provider/product identity for actual ChatGPT, reasoning effort exactly `xhigh`, clean context, no prior case transcript, matching prompt and attachment hashes, stable conversation/request identity, terminal success, matching response hash, and a nonce unseen in the run ledger. `NOT_EXPOSED` telemetry remains truthful rather than estimated; `PARTIAL` telemetry is recorded but cannot be silently completed. Ambiguous timeout is terminal HOLD and is never retried without stable lookup.

- [ ] **Step 5: Implement deterministic anonymization**

Derive anonymous labels from `sha256(corpus_sha256 + case_id + arm).hexdigest()[:12]`. Remove arm, conversation, module, and request identifiers from reviewer packets while retaining response bytes by separate hash.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m pytest tests/test_complexity_xhigh_contract.py -q -p no:cacheprovider
git add engine/perception/complexity_xhigh.py tests/test_complexity_xhigh_contract.py tests/complexity_benchmark_fixtures.py
git commit -m "feat(complexity): seal xhigh benchmark requests"
```

### Task 7: Add Deterministic Hard Gates, Rubric Scoring, and Ensemble Decision

**Files:**
- Create: `engine/perception/complexity_benchmark.py`
- Create: `tests/test_complexity_benchmark_scoring.py`
- Modify: `tests/complexity_benchmark_fixtures.py`

**Interfaces:**
- Produces: `HardGateViolation`, `RubricScore`, `PairScore`, `BenchmarkState`, `BenchmarkDecision`, `score_structured_response`, `decide_paired_benchmark`

- [ ] **Step 1: Write failing hard-gate and scoring tests**

```python
from __future__ import annotations

from engine.perception.complexity_benchmark import (
    BenchmarkState,
    decide_paired_benchmark,
    score_structured_response,
)
from tests.complexity_benchmark_fixtures import (
    benchmark_evidence,
    case_by_id,
    telemetry_summary,
    valid_response,
)


def test_inventory_invention_is_critical_and_automatic_loss() -> None:
    case = case_by_id("CX-C01")
    response = valid_response(case)
    response["claims"].append({
        "claim": "Ambrettolide was physically added",
        "state": "TESTED",
        "evidence_refs": [],
        "authority_ceiling": "PHYSICAL"
    })
    score = score_structured_response(case, response)
    assert any(v.code == "INVENTED_PHYSICAL_ADDITION" and v.critical for v in score.violations)
    assert score.total == 0


def test_mere_complication_cannot_score_as_richness() -> None:
    case = case_by_id("CX-A02")
    response = valid_response(case)
    response["depth_and_richness_analysis"]["coherent_richness"] = {
        "claim": "This is richer because it has more ingredients and descriptors.",
        "evidence_refs": [],
    }
    score = score_structured_response(case, response)
    assert any(v.code == "COMPLICATION_AS_COMPLEXITY" and v.critical for v in score.violations)
    assert score.total == 0


def test_hedonic_potential_must_remain_an_untested_hypothesis() -> None:
    case = case_by_id("CX-D04")
    response = valid_response(case)
    response["depth_and_richness_analysis"]["hedonic_potential_hypotheses"][0]["state"] = "TESTED"
    score = score_structured_response(case, response)
    assert any(v.code == "UNSUPPORTED_HEDONIC_RESULT" and v.critical for v in score.violations)


def test_exception_only_musk_cannot_leak_into_build_or_count_as_depth() -> None:
    case = case_by_id("CX-C03")
    response = valid_response(case)
    response["current_inventory_build"]["materials"].append("Tonalide")
    response["depth_and_richness_analysis"]["coherent_richness"] = {
        "claim": "A three-musk chord is inherently richer.",
        "evidence_refs": [],
    }
    score = score_structured_response(case, response)
    codes = {item.code for item in score.violations if item.critical}
    assert {"MUSK_EXCEPTION_REQUIRED", "MUSK_COUNT_PROXY"}.issubset(codes)
    assert score.total == 0


def test_valid_response_scores_six_frozen_dimensions() -> None:
    case = case_by_id("CX-B02")
    score = score_structured_response(case, valid_response(case))
    assert score.dimension_scores.keys() == {
        "target_architecture",
        "integrated_depth_richness",
        "factual_provenance",
        "missing_chemical_impact",
        "controlled_test_quality",
        "uncertainty_conflict_actionability",
    }
    assert sum(score.dimension_scores.values()) == score.total
    assert 0 <= score.total <= 100


def test_ensemble_requires_all_five_thresholds() -> None:
    decision = decide_paired_benchmark(benchmark_evidence(wins=12, median_delta=5, new_critical=0, category_regression=0), telemetry=telemetry_summary())
    assert decision.state is BenchmarkState.OUTPERFORMS
    assert decide_paired_benchmark(benchmark_evidence(wins=11, median_delta=5), telemetry=telemetry_summary()).state is BenchmarkState.INCONCLUSIVE
    assert decide_paired_benchmark(benchmark_evidence(wins=12, median_delta=4), telemetry=telemetry_summary()).state is BenchmarkState.INCONCLUSIVE
    assert decide_paired_benchmark(benchmark_evidence(wins=12, median_delta=5, new_critical=1), telemetry=telemetry_summary()).state is BenchmarkState.NO_DEMONSTRATED_OUTPERFORMANCE
```

Extend `tests/complexity_benchmark_fixtures.py` with:

```python
def case_by_id(case_id: str) -> ComplexityCasePacket:
    payload = json.loads((ROOT / "tests/fixtures/complexity_xhigh_cases_v1.json").read_text(encoding="utf-8"))
    raw = next(item for item in payload["cases"] if item["case_id"] == case_id)
    return ComplexityCasePacket.from_mapping(raw)


def valid_response(case: ComplexityCasePacket) -> dict[str, Any]:
    expected = dict(case.expected_invariants["valid_response"])
    return json.loads(json.dumps(expected))


def benchmark_evidence(
    *,
    wins: int,
    median_delta: int,
    new_critical: int = 0,
    category_regression: int = 0,
) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        pair_count=16,
        treatment_wins=wins,
        median_delta=Decimal(median_delta),
        new_treatment_critical_failures=new_critical,
        category_median_deltas={
            "TARGET_ARCHITECTURE": Decimal(-category_regression),
            "RECONSTRUCTION_REVISION": Decimal("5"),
            "MISSING_CHEMICAL_IMPACT": Decimal("5"),
            "EXPERIMENTAL_EVIDENCE_DESIGN": Decimal("5"),
        },
        receipts_valid=True,
    )


def telemetry_summary() -> TelemetrySummary:
    return TelemetrySummary(
        state="EXPOSED",
        median_control_price_usd=Decimal("1.00"),
        median_treatment_price_usd=Decimal("1.50"),
    )
```

- [ ] **Step 2: Run tests to verify import failure**

Run: `python -m pytest tests/test_complexity_benchmark_scoring.py -q -p no:cacheprovider`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement structured hard gates**

Hard-gate codes are fixed:

```python
CRITICAL_CODES = frozenset({
    "INVENTED_INVENTORY_OR_STOCK",
    "INVENTED_PHYSICAL_ADDITION",
    "TARGET_BUILD_COLLAPSE",
    "TARGET_CHANGED_TO_FIT_INVENTORY",
    "COMPLICATION_AS_COMPLEXITY",
    "UNSUPPORTED_HEDONIC_RESULT",
    "MUSK_COUNT_PROXY",
    "MUSK_EXCEPTION_REQUIRED",
    "MUSK_BUILD_INVENTORY_PROMOTION",
    "UNBOUND_OR_MONOMOLECULAR_NATURAL_OAV",
    "UNSUPPORTED_TESTED_STATUS",
    "SILENT_SOURCE_CONFLICT_RESOLUTION",
    "QUARANTINED_CONTENT_PROMOTED",
    "MISSING_CHEMICAL_IMPACT_OMITTED",
    "UNSUPPORTED_EVIDENCE_CITATION",
    "INVALID_STRUCTURED_RESPONSE",
})
```

Evaluate exact structured fields against each case's frozen `expected_invariants.valid_response`, `critical_traps`, `required_claim_states`, `required_depth_fields`, `complexity_definition.invalid_proxies`, `complexity_definition.musk_policy`, and `forbidden_claims`. `COMPLICATION_AS_COMPLEXITY` fires when raw ingredient, module, interaction, descriptor, novelty, response-length, jargon, or technical-density proxies are offered as proof of depth, richness, quality, beauty, or hedonic value. `UNSUPPORTED_HEDONIC_RESULT` fires when a design hypothesis is promoted beyond `DESIGN_HYPOTHESIS_NOT_TESTED` without bound sensory evidence. `MUSK_COUNT_PROXY` fires when fixed chord size is offered as quality or depth; `MUSK_EXCEPTION_REQUIRED` fires when Tonalide, Macrolide, or Musk Ketone appears without the complete design call; and `MUSK_BUILD_INVENTORY_PROMOTION` fires when a depleted exception enters the current-inventory build. Do not infer a PASS from prose when required structured fields disagree.

- [ ] **Step 4: Implement the 100-point rubric**

Use exact maxima 20, 20, 20, 15, 15, and 10 for:

1. `target_architecture`;
2. `integrated_depth_richness`;
3. `factual_provenance`;
4. `missing_chemical_impact`;
5. `controlled_test_quality`; and
6. `uncertainty_conflict_actionability`.

The depth/richness dimension scores only explicit target-linked facets, coherent
contrast or texture, meaningful temporal unfolding, restraint or subtraction,
and hedonic-potential mechanisms with discriminating sensory tests. It awards
zero for raw counts, response length, jargon, or ornamentation and deducts for
mud, redundancy, gratuitous intricacy, and unsupported hedonic promotion. Score
required concepts and evidence IDs from frozen case invariants; award no partial
credit for a missing required claim state. Invalid JSON or any critical
violation sets total to zero while retaining diagnostic dimension data.

- [ ] **Step 5: Implement aggregate thresholds and cost state**

```python
class BenchmarkState(str, Enum):
    OUTPERFORMS = "OUTPERFORMS"
    INCONCLUSIVE = "INCONCLUSIVE"
    NO_DEMONSTRATED_OUTPERFORMANCE = "NO_DEMONSTRATED_OUTPERFORMANCE"
    QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED = "QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED"
    BENCHMARK_BLOCKED = "BENCHMARK_BLOCKED"


@dataclass(frozen=True, slots=True)
class BenchmarkEvidence:
    pair_count: int
    treatment_wins: int
    median_delta: Decimal
    new_treatment_critical_failures: int
    category_median_deltas: Mapping[str, Decimal]
    receipts_valid: bool


@dataclass(frozen=True, slots=True)
class TelemetrySummary:
    state: str
    median_control_price_usd: Decimal | None
    median_treatment_price_usd: Decimal | None
```

Use `statistics.median`; do not average critical failures away. A tie is not a treatment win. Missing price/token telemetry is `NOT_EXPOSED`, not zero. Cost review triggers only when both arms expose comparable price telemetry and median treatment/control price ratio is greater than 2.0.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m pytest tests/test_complexity_benchmark_scoring.py tests/test_complexity_xhigh_contract.py -q -p no:cacheprovider
git add engine/perception/complexity_benchmark.py tests/test_complexity_benchmark_scoring.py tests/complexity_benchmark_fixtures.py
git commit -m "feat(complexity): score paired xhigh benchmark"
```

### Task 8: Add Relevance-Gated Ablation, Repair Limits, and Recoverable Retirement

**Files:**
- Modify: `engine/perception/complexity_benchmark.py`
- Modify: `engine/perception/complexity_registry.py`
- Extend: `tests/test_complexity_benchmark_scoring.py`
- Create: `tests/test_complexity_benchmark_receipt.py`
- Modify: `tests/complexity_benchmark_fixtures.py`

**Interfaces:**
- Produces: `FamilyDecision`, `RepairClass`, `RepairDecision`, `decide_family_ablation`, `classify_repair`, `propose_registry_transition`, and `build_benchmark_receipt`

- [ ] **Step 1: Write failing family-decision tests**

```python
from decimal import Decimal

import pytest

from engine.perception.complexity_benchmark import (
    AblationObservation,
    FailureSummary,
    FamilyDecision,
    classify_repair,
    decide_family_ablation,
    propose_registry_transition,
)
from engine.perception.complexity_registry import ModuleRole
from tests.complexity_benchmark_fixtures import module_descriptor


def test_capability_retains_on_gain_or_win_rate() -> None:
    rows = tuple(AblationObservation(f"CX-A0{i + 1}", Decimal(value), value > 0, 0) for i, value in enumerate((4, 3, 0, 5)))
    assert decide_family_ablation("construction_profile", ModuleRole.CAPABILITY, rows).state == "RETAIN"


def test_guardrail_retains_only_by_preventing_critical_failure() -> None:
    retained_rows = (AblationObservation("CX-B01", Decimal("0"), False, 1),)
    retained = decide_family_ablation("admission_lifecycle", ModuleRole.GUARDRAIL, retained_rows)
    assert retained.state == "RETAIN"
    no_prevention = (AblationObservation("CX-B01", Decimal("10"), True, 0),)
    not_retained = decide_family_ablation("admission_lifecycle", ModuleRole.GUARDRAIL, no_prevention)
    assert not_retained.state == "REPAIR_REQUIRED"


def test_no_relevant_case_is_not_failure_and_repair_count_is_capped() -> None:
    assert decide_family_ablation("x", ModuleRole.CAPABILITY, []).state == "NOT_EVALUATED_NO_RELEVANT_CASE"
    with pytest.raises(ValueError, match="one repair cycle"):
        classify_repair(FailureSummary(codes=("AUTHORITY_LEAK",), case_ids=("CX-B01",)), prior_repair_count=1)


def test_retirement_changes_registry_state_but_never_deletes_source() -> None:
    descriptor = module_descriptor()
    decision = FamilyDecision(
        family_id=descriptor.family_id,
        state="RETIRE",
        median_delta=Decimal("-2"),
        win_rate=Decimal("0.25"),
        prevented_critical_failures=0,
        reasons=("failed one repair and four holdouts",),
    )
    proposal = propose_registry_transition(descriptor, decision)
    assert proposal.new_state == "RETIRED_BENCHMARK_UNDERPERFORMER"
    assert proposal.delete_paths == ()
    assert proposal.preserve_paths == (descriptor.path,)
```

Extend `tests/complexity_benchmark_fixtures.py` with this exact descriptor:

```python
def module_descriptor() -> ModuleDescriptor:
    return ModuleDescriptor(
        module_id="construction-complexity",
        family_id="construction_profile",
        role=ModuleRole.CAPABILITY,
        state=ModuleState.ACTIVE_CANDIDATE,
        path="engine/perception/construction_complexity.py",
        import_path="engine.perception.construction_complexity",
        sha256="f8dd92ae5da1a9aa409ed27ad2e5e789874f32bc77a156e28a65870dae871ab1",
        evidence_refs=("data/governance/complexity_native_module_admission_20260822.json",),
    )
```

- [ ] **Step 2: Run the new tests to verify failure**

Expected: FAIL because family and repair APIs do not exist.

- [ ] **Step 3: Implement family thresholds**

Capability retention requires median delta at least 3 or wins in at least 60 percent of relevant cases, with no new critical regression. Guardrail retention requires prevention of at least one critical failure, with no new critical regression. Zero relevant cases returns `NOT_EVALUATED_NO_RELEVANT_CASE`.

Use these exact evidence and decision types:

```python
@dataclass(frozen=True, slots=True)
class AblationObservation:
    case_id: str
    score_delta: Decimal
    full_ensemble_won: bool
    prevented_critical_failures: int


@dataclass(frozen=True, slots=True)
class FamilyDecision:
    family_id: str
    state: str
    median_delta: Decimal | None
    win_rate: Decimal | None
    prevented_critical_failures: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FailureSummary:
    codes: tuple[str, ...]
    case_ids: tuple[str, ...]
```

- [ ] **Step 4: Implement bounded repair classification**

The only automatic diagnostic classes are:

```python
class RepairClass(str, Enum):
    BUNDLE_VERBOSITY_OR_COST = "BUNDLE_VERBOSITY_OR_COST"
    AUTHORITY_LEAK = "AUTHORITY_LEAK"
    IRRELEVANT_FAMILY_OUTPUT = "IRRELEVANT_FAMILY_OUTPUT"
    MISSING_DISCRIMINATOR = "MISSING_DISCRIMINATOR"
    INCOMPLETE_BINDING = "INCOMPLETE_BINDING"
    NO_BOUNDED_REPAIR = "NO_BOUNDED_REPAIR"
```

Map each class to one allowed locus:

- verbosity/cost → adapter serialization only;
- authority leak → ensemble claim-ceiling filter or responsible native guardrail;
- irrelevant output → adapter's relevance assertion, not frozen case relevance;
- missing discriminator → expansion/design adapter validation;
- incomplete binding → admission/sensory parser and native gate wiring;
- unknown failure → no bounded repair; proceed to evidence-backed retirement decision.

Do not automate source edits. Emit exact failing cases, fields, allowed files, prior repair count, and four sealed holdout IDs.

- [ ] **Step 5: Implement append-only receipt construction**

The receipt includes registry/corpus/rubric hashes, every request and response hash, execution receipt state, pair scores, threshold decision, telemetry state, ablation decisions, repair count, holdout results, registry transitions, preserved paths, zero deletion paths, and all authority flags false. Hash the semantic receipt with `stable_json_hash` after omitting only `semantic_receipt_sha256`.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m pytest tests/test_complexity_benchmark_scoring.py tests/test_complexity_benchmark_receipt.py tests/test_complexity_registry.py -q -p no:cacheprovider
git add engine/perception/complexity_benchmark.py engine/perception/complexity_registry.py tests/test_complexity_benchmark_scoring.py tests/test_complexity_benchmark_receipt.py tests/complexity_benchmark_fixtures.py
git commit -m "feat(complexity): gate ablation and retirement"
```

### Task 9: Expose Local Benchmark Operations Through the Existing Audit CLI

**Files:**
- Modify: `scripts/pipeline_audit.py:12-45,432-598`
- Modify: `tests/test_pipeline_audit_verify.py`

**Interfaces:**
- Adds: `complexity-benchmark --operation census|prepare|validate|score|ablate|receipt`
- Produces only local files and JSON stdout; sends no provider requests

- [ ] **Step 1: Write failing CLI dispatch tests**

```python
def test_complexity_benchmark_census_json(capsys) -> None:
    rc = pipeline_audit.main(["complexity-benchmark", "--operation", "census", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["state"] == "PASS"
    assert payload["unclassified"] == []


def test_complexity_benchmark_prepare_is_provider_free(tmp_path, monkeypatch, capsys) -> None:
    expected = {
        "state": "PASS",
        "provider_calls": 0,
        "prepared_request_count": 32,
    }
    monkeypatch.setattr(
        pipeline_audit,
        "prepare_complexity_benchmark",
        lambda **_: expected,
    )
    rc = pipeline_audit.main([
        "complexity-benchmark", "--operation", "prepare",
        "--run-dir", "output/complexity_xhigh_benchmark/test-run", "--json"
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["provider_calls"] == 0
    assert payload["prepared_request_count"] == 32
```

- [ ] **Step 2: Run tests to verify parser rejection**

Expected: FAIL because `complexity-benchmark` is not a recognized command.

- [ ] **Step 3: Add a thin command handler**

```python
def _cmd_complexity_benchmark(args: argparse.Namespace) -> int:
    handlers = {
        "census": run_complexity_census,
        "prepare": prepare_complexity_benchmark,
        "validate": validate_complexity_run,
        "score": score_complexity_run,
        "ablate": prepare_relevant_ablations,
        "receipt": write_complexity_benchmark_receipt,
    }
    payload = handlers[args.operation](
        project_root=PROJECT_ROOT,
        run_dir=PROJECT_ROOT / args.run_dir,
    )
    _print_json(payload)
    return 0 if payload["state"] not in {"HOLD", "BENCHMARK_BLOCKED"} else 1
```

The handler delegates all logic to six explicitly imported library wrappers in
`engine.perception.complexity_benchmark`: `run_complexity_census`,
`prepare_complexity_benchmark`, `validate_complexity_run`,
`score_complexity_run`, `prepare_relevant_ablations`, and
`write_complexity_benchmark_receipt`. Each wrapper returns the same closed
top-level envelope: `state`, `operation`, `provider_calls`, `run_dir`,
`artifacts`, and `blockers`, plus operation-specific fields. They never open a
network connection, read credentials, retry a provider request, or import a
module path supplied by the registry or case packet.

- [ ] **Step 4: Add parser arguments**

```python
complexity = sub.add_parser(
    "complexity-benchmark",
    help="Prepare, validate, score, and receipt the local complexity xhigh benchmark.",
)
complexity.add_argument(
    "--operation",
    required=True,
    choices=("census", "prepare", "validate", "score", "ablate", "receipt"),
)
complexity.add_argument(
    "--run-dir",
    default="output/complexity_xhigh_benchmark/current",
)
complexity.add_argument("--json", action="store_true")
complexity.set_defaults(func=_cmd_complexity_benchmark)
```

Validate that `run_dir.resolve()` remains under repository `output/complexity_xhigh_benchmark/`; reject traversal or arbitrary output paths.

- [ ] **Step 5: Run CLI and focused tests**

```powershell
python -m pytest tests/test_pipeline_audit_verify.py tests/test_complexity_registry.py tests/test_complexity_ensemble.py tests/test_complexity_xhigh_contract.py tests/test_complexity_benchmark_scoring.py -q -p no:cacheprovider
python scripts/pipeline_audit.py complexity-benchmark --operation census --json
```

Expected: PASS, census state PASS, zero provider calls.

- [ ] **Step 6: Commit the CLI integration**

```powershell
git add scripts/pipeline_audit.py tests/test_pipeline_audit_verify.py
git commit -m "feat(audit): expose local complexity benchmark"
```

### Task 10: Add the Runbook and Complete Provider-Free Verification

**Files:**
- Create: `docs/research/PERFUME_CHEM_COMPLEXITY_XHIGH_BENCHMARK_RUNBOOK_2026-08-22.md`
- Extend: `tests/test_complexity_benchmark_receipt.py`

**Interfaces:**
- Produces: exact operator procedure for prepare, external xhigh execution, import, validate, score, ablate, repair, retire, and receipt

- [ ] **Step 1: Write a failing runbook contract test**

```python
def test_runbook_is_nonfast_no_duplicate_and_authority_safe() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for required in (
        "ChatGPT Pro work chats are advisory workers only",
        "plain ChatGPT xhigh",
        "one clean projectless conversation per request",
        "do not retry an ambiguous request",
        "RETIRED_BENCHMARK_UNDERPERFORMER",
        "physical liking remains NOT TESTED",
        "no DeepLuna provider transmission",
    ):
        assert required in text
    assert "DeepLuna Fast fallback" not in text
```

- [ ] **Step 2: Run the test to verify missing runbook failure**

Expected: FAIL because the runbook does not exist.

- [ ] **Step 3: Write the exact runbook**

Document these commands in order:

```powershell
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$suffix = (New-Guid).Guid.Replace('-', '').Substring(0, 8).ToLowerInvariant()
$runId = "CXB-$stamp-$suffix"
$runDir = "output/complexity_xhigh_benchmark/$runId"
python scripts/pipeline_audit.py complexity-benchmark --operation census --json
python scripts/pipeline_audit.py complexity-benchmark --operation prepare --run-dir $runDir --json
python scripts/pipeline_audit.py complexity-benchmark --operation validate --run-dir $runDir --json
python scripts/pipeline_audit.py complexity-benchmark --operation score --run-dir $runDir --json
python scripts/pipeline_audit.py complexity-benchmark --operation ablate --run-dir $runDir --json
python scripts/pipeline_audit.py complexity-benchmark --operation receipt --run-dir $runDir --json
```

The runbook must preserve the `$runId` and `$runDir` values created above for the entire run. The required ID form is `CXB-YYYYMMDDTHHMMSSZ-` followed by eight lowercase hexadecimal characters.

- [ ] **Step 4: Run all provider-free focused verification**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest tests/test_complexity_native_module_admission.py tests/test_complexity_registry.py tests/test_complexity_ensemble.py tests/test_complexity_adapters.py tests/test_complexity_xhigh_contract.py tests/test_complexity_benchmark_scoring.py tests/test_complexity_benchmark_receipt.py tests/test_pipeline_audit_verify.py -q -p no:cacheprovider
ruff check engine/perception/complexity_registry.py engine/perception/complexity_adapters.py engine/perception/complexity_ensemble.py engine/perception/complexity_xhigh.py engine/perception/complexity_benchmark.py scripts/pipeline_audit.py tests/test_complexity_*.py tests/test_pipeline_audit_verify.py
python -m compileall -q engine/perception
python scripts/pipeline_audit.py project-verify --quick --json
```

Expected: all new/focused tests, Ruff, and compilation pass. Record project-verification failures as pre-existing or new by exact check name; any new relevant failure blocks live xhigh execution.

- [ ] **Step 5: Prepare the provider-free 32-request manifest**

Run `complexity-benchmark --operation prepare`. Verify exactly 16 control and 16 treatment requests, 32 unique nonces, zero provider calls, identical common-input hash within each pair, treatment-only module bundle delta, and frozen corpus/rubric hashes.

- [ ] **Step 6: Commit the runbook**

```powershell
git add docs/research/PERFUME_CHEM_COMPLEXITY_XHIGH_BENCHMARK_RUNBOOK_2026-08-22.md tests/test_complexity_benchmark_receipt.py
git commit -m "docs(complexity): add xhigh benchmark runbook"
```

### Task 11: Run the Initial Plain-xhigh Versus Ensemble Benchmark

**Files:**
- Write ignored runtime artifacts only: the exact `output/complexity_xhigh_benchmark/$runId/` created in Task 10
- No repository source edit during generation

**Interfaces:**
- Consumes: sealed 32-request manifest
- Produces: 32 verified xhigh execution receipts and exact response bytes

- [ ] **Step 1: Reconcile the bounded online ChatGPT Pro worker reviews**

Read the four user-requested online worker chats for module/musk classification,
clean-room musk API, depth-versus-complication scoring, and registry/CLI review.
Record chat/conversation IDs and exact response hashes. Accept only findings Sol
can reproduce from local bytes. Do not copy unsupported dose, perception,
prestige, substitution, safety, or physical-result claims into implementation.

- [ ] **Step 2: Keep worker chats outside the blinded benchmark**

None of the four worker conversations may be reused for control, treatment,
ablation, repair, or scoring. They must not receive the frozen exact case prompts
after freeze. The 32 benchmark requests use fresh projectless chats with no
worker transcript visible. Record this separation in the run receipt.

- [ ] **Step 3: Verify ChatGPT xhigh environment before the first case**

Confirm actual ChatGPT product, model identity, xhigh reasoning effort, empty projectless context, and ability to capture exact prompt/output bytes and stable conversation IDs. If any element is unprovable, write a blocked run receipt with `BENCHMARK_BLOCKED_UNVERIFIED_XHIGH` and stop.

- [ ] **Step 4: Execute sealed requests in bounded batches**

For each request, use one fresh projectless ChatGPT xhigh conversation. Send only the sealed prompt and attachments for that request. Capture its exact response and execution metadata before opening the next request. Use batches of at most four open conversations; validate and close the batch before proceeding. Never reuse a conversation across cases or arms.

- [ ] **Step 5: Prevent duplicate paid work**

Before each send, check that its nonce is absent from accepted, in-flight, ambiguous, and terminal ledgers. After a timeout, look up the stable conversation/request ID; do not resend. Mark unresolved timeouts `AMBIGUOUS` and block that pair.

- [ ] **Step 6: Import and validate all receipts**

Run:

```powershell
python scripts/pipeline_audit.py complexity-benchmark --operation validate --run-dir $runDir --json
```

Expected: 32 valid terminal receipts, 16 complete pairs, zero duplicate nonces, zero hash drift, and zero contaminated contexts. Otherwise the aggregate decision is `BENCHMARK_BLOCKED`.

- [ ] **Step 7: Score the initial benchmark**

Run the `score` operation. Preserve blinded per-case outputs, hard-gate findings, six dimension scores, pair winner, score delta, category medians, telemetry, and aggregate decision.

- [ ] **Step 8: Resolve only the specified inconclusive band**

If and only if the result has 9-11 treatment wins or median improvement 2-4 points, prepare one repeat for disputed cases with the same frozen bytes and fresh clean contexts. Each repeated request gets a new nonce linked to the original case; no other case is repeated. Revalidate and rescore once.

### Task 12: Run Formal Ablation or One Bounded Repair Cycle

**Files:**
- Runtime outputs: `$runDir/ablations/` and `$runDir/holdouts/`
- Conditional source edits limited by `RepairClass`
- Conditional registry modification: `configs/complexity/complexity_module_registry_v1.json`
- Conditional append-only receipt: `data/governance/complexity_xhigh_benchmark_$runId.json`

**Interfaces:**
- Consumes: Task 11 terminal aggregate decision
- Produces: family retention decisions or one repair/holdout/retirement decision

- [ ] **Step 1: Branch only on the recorded aggregate decision**

- `OUTPERFORMS` → prepare formal relevance-gated leave-one-family-out requests.
- `QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED` → compress adapter serialization only, then rerun the four most expensive cases before formal ablation.
- `INCONCLUSIVE` after the one allowed repeat or `NO_DEMONSTRATED_OUTPERFORMANCE` → use local module traces to select at most one bounded `RepairClass`; do not label diagnostic traces as formal ablation.
- `BENCHMARK_BLOCKED` → fix only execution/provenance infrastructure and rerun no model request until stable lookup proves it was never completed.

- [ ] **Step 2: Run formal ablation only after a quality pass**

Generate ablation requests only for predeclared relevant cases. Compare full ensemble against ensemble-minus-one capability family. Mandatory guardrails are tested with synthetic deterministic counterfactuals for critical-error prevention; do not send unsafe guardrail-omitted prompts as treatment candidates.

- [ ] **Step 3: Apply at most one bounded repair**

Write a failing regression test reproducing the exact observed field and case before changing code. Modify only the allowed locus emitted by `classify_repair`. Run the focused family tests, the relevant frozen cases, and exactly four unseen holdout cases. Do not change frozen case bytes, rubric logic, thresholds, or original outputs.

- [ ] **Step 4: Retire a persistent underperformer recoverably**

If the family still fails its role-specific criterion on frozen and holdout cases, patch only its registry state to `RETIRED_BENCHMARK_UNDERPERFORMER`, remove it from runtime eligibility, preserve its path/hash/evidence refs, and record `delete_paths: []`. Run the full focused suite and verify unrelated imports remain intact.

- [ ] **Step 5: Commit repair or retirement separately**

Use one of these exact messages:

```powershell
$decision = Get-Content -LiteralPath "$runDir/family_decision.json" -Raw | ConvertFrom-Json
$familyId = [string]$decision.family_id
git commit -m "fix(complexity): repair benchmarked $familyId"
git commit -m "chore(complexity): retire underperforming $familyId"
```

Run only the commit command matching the terminal decision. If no source or registry change is needed, make no empty commit.

### Task 13: Write the Final Governance Receipt and Verify Completion

**Files:**
- Create: `data/governance/complexity_xhigh_benchmark_$runId.json`
- Test: `tests/test_complexity_benchmark_receipt.py`

**Interfaces:**
- Produces: append-only final or blocked receipt; no scientific or release authority

- [ ] **Step 1: Generate the receipt from immutable run artifacts**

Run the `receipt` CLI operation. The receipt must bind the design/spec commit, implementation commits, registry hash, module hashes, corpus/rubric hash, request/response/receipt hashes, online worker chat IDs and locally accepted/rejected findings, xhigh environment proof, scores, telemetry, aggregate decision, ablations, repair count, holdouts, transitions, and preserved paths. If the local DeepLuna readiness-only diagnostic is recorded, state explicitly that no DeepLuna provider transmission was used after the user selected ChatGPT Pro workers.

- [ ] **Step 2: Write a failing exact receipt replay test before admitting the receipt**

```python
def test_final_receipt_replays_semantic_hash_and_authority_boundary() -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    declared = payload.pop("semantic_receipt_sha256")
    assert stable_json_hash(payload) == declared
    assert payload["authority"] == {
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "sensory": False,
        "safety": False,
        "installation": False,
        "publication": False,
        "release": False,
    }
    assert payload["deleted_paths"] == []
```

- [ ] **Step 3: Run final focused and project verification**

Run Task 10's focused suite, Ruff, compileall, quick project verification, and `git diff --check`. Run the full project verification only after focused checks are clean; report pre-existing failures separately and do not claim release readiness while any release gate fails.

- [ ] **Step 4: Verify exact staged scope**

Run `git diff --cached --name-status` and confirm only the new governance receipt, its exact test update, and any separately approved repair/retirement paths are staged. Raw prompts and model outputs remain under ignored `output/` and are referenced by hash.

- [ ] **Step 5: Commit the final receipt**

```powershell
git commit -m "docs(complexity): record xhigh benchmark decision"
```

- [ ] **Step 6: Report the terminal outcome truthfully**

Report:

- benchmark run ID and exact commits;
- valid control/treatment pair count;
- treatment wins, median delta, category regressions, and critical failures;
- xhigh model/effort proof and telemetry state;
- retained, repaired, not-evaluated, or retired families;
- files preserved and any active registry changes;
- focused and project verification results;
- blockers or inconclusive cases; and
- explicit `NOT TESTED` status for physical liking, similarity, stability, safety, measured headspace, sensory outcome, compounding, and release.
