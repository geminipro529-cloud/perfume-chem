# White Fire Reliquary Floral/Wood Depth Training Implementation Plan

> **Execution owner:** Sol, inline in the isolated `codex/all-floral-depth-candidate` worktree. Codex subagents are forbidden by project authority. DeepLuna Chat may be used only after a fresh exact-project READY check; the current check is `BLOCKED/budget-unsafe`, so this plan has no provider transmission step.

**Goal:** Implement the first nonruntime all-floral depth case, `White Fire Reliquary`, as a target-first four-flower and two-texture wood experiment whose current build is fully supported by the user's dated physical authority. Preserve five genuinely different inventory-buildable training directions, but formulate and diagnose only the first one now.

**Claim ceiling:** Computational experiment design only. No physical compounding, procurement, liking, realism, DHP/Opus-V equivalence, safety, stability, performance, release, or runtime-admission authority.

**Architecture:** Add a pure floral-domain contract/evaluator over the admitted Architectural Delta comparison engine. The floral compiler owns target identity, flower-specific facets/couplings, temporal hypotheses, source policy, current-build mapping, measurable-dose preparation, wood-texture controls, and claim ceilings. The adapter emits at most one currently actionable constant-total comparison. A V9 registry overlay records the candidate and keeps it runtime-unreachable.

**Technology:** Python 3 dataclasses/enums, existing `engine.evidence_contracts` canonical hashing, existing inventory parser and Architectural Delta contracts, pytest, Ruff, JSON fixtures, and the existing formula release/analysis commands. No new pipeline script.

---

## Task 1: Reconcile dated physical authority and freeze all-five buildability

**Files:**

- Modify: `inventory.txt`
- Modify: `data/materials/M.yaml`
- Create: `tests/fixtures/floral_depth/training_directions_v1.json`
- Create: `tests/test_floral_training_inventory.py`

**Test first:** Add a test which parses `inventory.txt` with `include_unavailable=False`, loads the fixture, and requires:

```python
assert len(directions) == 5
assert all(len(item["floral_subjects"]) >= 3 for item in directions)
assert missing_owned_materials == {}
assert all(item["allowed_source_classes"] == [
    "ESSENTIAL_OIL", "ABSOLUTE", "KNOWN_CHEMICAL"
] for item in directions)
```

The fixture will freeze these distinct directions and exact inventory anchors:

1. `white-fire-reliquary`: White Champi/Magnolia + jasmine + tuberose + orange blossom; translucent/carnal floral polarity over a dry/creamy sandalwood dyad.
2. `rain-before-pollen`: mimosa + muguet + freesia + cyclamen; damp-air relief against powdery pollen.
3. `velvet-thorn`: rose + jasmine + violet + carnation; satin petal mass against green thorn and clove-like floral spice.
4. `apricot-eclipse`: osmanthus + immortelle + jasmine + violet; apricot-leather light against hayed floral shadow.
5. `sunlit-wax-garden`: ylang + orange blossom + gardenia + peony; solar wax and cream against cool rosy petal lift.

No opaque FO, FTEC, captive base, supplier accord, Cedarwood Virginia, Lemon FCF, or tincture may appear in the fixture.

**Authority patch:**

- mark Lemon FCF and Cedarwood Virginia depleted on 2026-08-27;
- mark the two listed ethanol tinctures lost/depleted;
- add owned neat Ethylene Brassylate;
- restore owned Ambrettolide 10% in DPG;
- annotate Magnolia EO as the user's separately sourced, as-sold 100%-labelled White Champi/White Champaca (`Michelia alba`) flower EO while retaining composition/safety/lot holds;
- update inventory counts using `engine.inventory_parser.inventory_counts()` rather than hand guessing;
- update `data/materials/M.yaml` aliases and stock metadata only; leave VP/ODT/composite values null.

Run the new inventory test and existing focused inventory tests before proceeding.

## Task 2: Implement pure target-first floral/wood contracts

**Files:**

- Create: `engine/perception/floral_depth.py`
- Create: `tests/test_floral_depth.py`

**Test first:** Cover closed enums and these exact outcomes:

- complete White Fire request -> `READY` with exactly one active trial;
- all-support floral subjects -> `NOT_APPLICABLE`;
- identical ideal/current references -> `HOLD_TARGET_BUILD_COLLAPSE`;
- unsupported source class -> `HOLD_SOURCE_CLASS`;
- autogenous polarity without an explicit reciprocal coupling -> `HOLD_STRATEGY_UNSUPPORTED`;
- woods presented as the sole source of flower depth -> `HOLD_EXTERNALIZED_DEPTH`;
- facet without omission loss/control -> `HOLD_DECORATIVE_FACET`;
- natural without lot/composite authority -> quantitative OAV hold while whole-natural identity remains present;
- unprepared raw delivery below 10 uL -> `HOLD_SUB_10_UL`;
- complete serial preparation with every measured source/delivery at least 10 uL -> accepted;
- more than one musk without pairwise controls -> `HOLD_MUSK_REDUNDANCY`;
- Tonalide/Macrolide/Musk Ketone -> rejected without an exception contract;
- precise simplicity -> `NO_CHANGE`;
- every empirical/formula/physical/purchase/sensory/safety/release authority flag -> false.

**Public interface:**

```python
class FloralDesignState(str, Enum):
    READY = "READY"
    NO_CHANGE = "NO_CHANGE"
    HOLD = "HOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass(frozen=True, slots=True)
class FloralSubjectV1:
    subject_id: str
    name: str
    role: FloralSubjectRole

@dataclass(frozen=True, slots=True)
class FloralIdentityContractV1:
    target_identity: str
    emotional_tone: str
    floral_subjects: tuple[FloralSubjectV1, ...]
    floral_scope: FloralScope
    realism_target: str
    ideal_formula_ref: str
    current_inventory_build_ref: str
    allowed_source_classes: tuple[FloralSourceClass, ...]
    forbidden_drift: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_ceiling: str

@dataclass(frozen=True, slots=True)
class FloralFacetV1:
    facet_id: str
    facet_class: FloralFacetClass
    target_function: str
    subject_owner: str
    omission_loss: str
    failure_mode: str
    required_temporal_windows: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    ideal_materials: tuple[str, ...]
    current_build_bindings: tuple[str, ...]
    controlled_comparison_ref: str

@dataclass(frozen=True, slots=True)
class FloralCouplingContractV1:
    coupling_id: str
    facet_ids: tuple[str, ...]
    shared_recognizers: tuple[str, ...]
    relationship_edges: tuple[str, ...]
    bridge: str
    collision_risks: tuple[str, ...]
    controlled_arms: tuple[str, str]
    identity_retention_endpoints: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class FloralTemporalWindowV1:
    window_id: str
    required_recognizers: tuple[str, ...]
    state_hypothesis: str

@dataclass(frozen=True, slots=True)
class FloralTemporalContourV1:
    windows: tuple[FloralTemporalWindowV1, ...]

@dataclass(frozen=True, slots=True)
class FloralDosePreparationV1:
    preparation_id: str
    source_material: str
    source_stock_fraction: Decimal
    concentration_basis: str
    carrier: str
    source_ul: Decimal
    carrier_ul: Decimal
    prepared_total_ul: Decimal
    final_stock_fraction: Decimal
    delivered_ul: Decimal
    delivered_active_ul: Decimal
    instruction: str

@dataclass(frozen=True, slots=True)
class FloralMaterialDoseV1:
    material_id: str
    material: str
    source_class: FloralSourceClass
    subject_owner: str
    target_function: str
    raw_stock_ul: Decimal
    stock_fraction: Decimal
    active_ul: Decimal
    active_ppm: Decimal
    inventory_state: InventoryBindingState
    exact_stock_ref: str | None
    preparation_id: str | None
    natural_oav_state: NaturalOAVState
    is_musk: bool = False

@dataclass(frozen=True, slots=True)
class WoodTextureContractV1:
    contract_id: str
    material_ids: tuple[str, ...]
    texture_axis: str
    floral_echo: str
    omission_loss: str
    failure_mode: str
    fixed_constraints: tuple[str, ...]
    controlled_arms: tuple[str, ...]
    prerequisite_trial_ids: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class FloralTrainingTrialV1:
    trial_id: str
    domain: TrainingDomain
    stage_order: int
    changed_factor: str
    intervention_material_ids: tuple[str, ...]
    controlled_arms: tuple[str, ...]
    primary_endpoints: tuple[str, ...]
    failure_endpoints: tuple[str, ...]
    constant_constraints: tuple[str, ...]
    prerequisite_trial_ids: tuple[str, ...]
    accept_rule: str
    reject_rule: str
    blinding_rule: str
    order_rule: str
    time_windows: tuple[str, ...]
    evidence_refs: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class MissingChemicalImpactV1:
    material: str
    target_function: str
    impact: str
    current_handling: str
    decision: str

@dataclass(frozen=True, slots=True)
class FloralDesignRequestV1:
    identity: FloralIdentityContractV1
    strategy: FloralDepthStrategy
    facets: tuple[FloralFacetV1, ...]
    coupling: FloralCouplingContractV1 | None
    temporal_contour: FloralTemporalContourV1
    ideal_materials: tuple[FloralMaterialDoseV1, ...]
    current_build_materials: tuple[FloralMaterialDoseV1, ...]
    preparations: tuple[FloralDosePreparationV1, ...]
    missing_chemical_impacts: tuple[MissingChemicalImpactV1, ...]
    wood_texture_contracts: tuple[WoodTextureContractV1, ...]
    training_trials: tuple[FloralTrainingTrialV1, ...]
    passed_trial_ids: tuple[str, ...]
    no_change_reason: str

@dataclass(frozen=True, slots=True)
class FloralDesignResultV1:
    state: FloralDesignState
    reason_codes: tuple[str, ...]
    request_sha256: str
    selected_trial: FloralTrainingTrialV1 | None
    deferred_trial_ids: tuple[str, ...]
    quantitative_oav_holds: tuple[str, ...]
    blockers: tuple[str, ...]
    identity: FloralIdentityContractV1
    strategy: FloralDepthStrategy
    ideal_materials: tuple[FloralMaterialDoseV1, ...]
    current_build_materials: tuple[FloralMaterialDoseV1, ...]
    missing_chemical_impacts: tuple[MissingChemicalImpactV1, ...]
    empirical_authority: bool = field(default=False, init=False)
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

def evaluate_floral_design(
    request: FloralDesignRequestV1,
) -> FloralDesignResultV1:
    """Return one target-scoped experiment, NO_CHANGE, NOT_APPLICABLE, or HOLD."""
```

All records expose deterministic `as_dict()` output and `record_sha256`. OAV state is diagnostic metadata, never a score. Trial selection is ordered and emits zero or one active trial; later wood stages stay explicitly prerequisite-blocked until floral coupling passes physically.

## Task 3: Compile one floral comparison through Architectural Delta

**Files:**

- Create: `engine/solforge/floral_adapter.py`
- Create: `tests/test_solforge_floral_adapter.py`

**Test first:** Build a valid White Fire result and verify:

```python
compiled = compile_floral_design(result, inventory_workbook_path=path)
assert compiled.receipt.state.value == "AUGMENT"
assert compiled.architectural_result.controlled_arms == (
    "CARRIER_MATCHED_BRIDGE_ABLATION", "FULL_FLORAL_COUPLING"
)
assert "CONSTANT_TOTAL" in " ".join(compiled.comparison_closure.constant_constraints)
```

Also test `NO_CHANGE`, held designs, multiple active trials, absent workbook, and source-hash omission. The adapter will translate only the first actionable `FloralTrainingTrialV1` into one `ArchitecturalDeltaCandidate(kind=RATIO)`, bind exact constituent names and source hashes in evidence, and call `evaluate_architectural_evidence_delta`. It will not mutate a formula or authorize physical execution.

## Task 4: Freeze the White Fire training case

**Files:**

- Create: `tests/fixtures/floral_depth/white_fire_reliquary_v1.json`
- Extend: `tests/test_floral_depth.py`

Freeze:

- the four floral voices and hierarchy;
- White Champi cool distilled-flower shell versus jasmine/tuberose warm flesh, coupled by shared linalool/benzenoid/jasmonate/salicylate relations;
- orange blossom as a named co-lead, not generic neroli support;
- flower facets, temporal contour, source classes, missing-chemical impact, and White Champi composite-OAV hold;
- one musk only: Ambrettolide 10%, for floral-skin character echo;
- fixed Iso E Super spatial scaffold;
- Javanol dry/mineral and Ebanol creamy/yielding wood-texture contracts;
- stage 1 carrier-matched floral-coupling ablation;
- stage 2 prerequisite-blocked `2 x 2` Javanol/Ebanol factorial (`W00`, `WJ`, `WE`, `WJE`) with Iso E fixed;
- optional later Ambrettolide-versus-equal-active-EB comparison, not active now.

Endpoints remain separate: target identity, each floral voice/hierarchy, cool-warm floral simultaneity, dry-creamy wood texture, front/center/rear separation, transition continuity, wood takeover, depth, liking, and fixed-distance detection. DHP 2025 and Opus V may be blinded geometry/texture/performance anchors only.

## Task 5: Add an immutable nonruntime V9 registry overlay

**Files:**

- Modify: `engine/perception/complexity_registry.py`
- Create: `configs/complexity/complexity_module_registry_v9.json`
- Create: `tests/test_complexity_registry_v9.py`
- Modify: `tests/test_complexity_registry_v8.py`
- Modify: `tests/test_complexity_registry_v6.py`
- Modify: `engine/project_verification.py`

The V9 loader will preserve direct V8 validation and add a narrowly scoped, hash-bound runtime rebinding for `complexity_registry.py` itself. It will append exactly one descriptor:

```json
{
  "module_id": "all-floral-depth-compiler",
  "family_id": "floral-depth",
  "role": "CAPABILITY",
  "state": "FUTURE_CANDIDATE_NOT_VALIDATED",
  "path": "engine/perception/floral_depth.py",
  "import_path": null
}
```

The overlay binds source, adapter, tests, both fixtures, approved spec, and implementation-plan bytes. The formula is deliberately excluded from this registry binding because the mandatory pipeline-analysis append changes formula bytes under its own manifest after the candidate registry is frozen. Runtime-eligible modules must remain exactly `{architectural-delta-engine}` and every authority flag remains false. Add the three new focused tests to the `complexity-solforge` project-verification shard.

## Task 6: Write the first inventory-buildable formula and protocol

**Files:**

- Create: `formulas/White_Fire_Reliquary_30mL_Parfum.md`

Before writing, reread `AGENTS.md`, `inventory.txt`, `.github/copilot-instructions.md`, the floral/woods family sections, and the approved all-floral spec.

The document will contain, in order:

1. named identity, emotional tone, floral subject, realism target, and functional architecture;
2. DHP/Opus-V concept transfer with no similarity claim;
3. separate TARGET/IDEAL and CURRENT-INVENTORY formulas;
4. material-choice/rejection ledger;
5. missing-chemical and natural-authority impact gate;
6. every dilution/preparation needed to avoid a raw-stock delivery below 10 uL;
7. ppm, ODT, composite-natural OAV, stock-rebase, and temporal diagnostics with exact holds;
8. controlled blinded floral and wood training stages;
9. preparation/purchase recommendations, explicitly not authorized;
10. claim ceiling and local acceptance.

Current formula target: 7,200 uL raw concentrate plus 22.8 mL ethanol, nominal 30 mL at 24% v/v. It uses only owned EO/absolute/known-chemical stocks and exactly one musk. White Champi is used as a prepared 10% stock; methyl anthranilate uses a serial 0.1% stock; indole uses a 1% stock prepared from the owned 10% stock. Every measured preparation and formula delivery is at least 10 uL.

Use one flat parser-visible CURRENT-INVENTORY table. Place the TARGET/IDEAL table under an `Accord architecture` heading so the existing parser does not double-count it.

## Task 7: Run diagnostics and append the required analysis

**Commands:**

```powershell
python scripts/formula_release_gate.py --formula-file formulas/White_Fire_Reliquary_30mL_Parfum.md --expected-concentrate-ul 7200 --batch-volume-ml 30 --brief woody_floral_musk --json --append-analysis > output/white_fire_reliquary_v1.json
python scripts/format_pipeline_analysis.py --input output/white_fire_reliquary_v1.json
python scripts/verify_formula_workflow.py --formula-file formulas/White_Fire_Reliquary_30mL_Parfum.md
```

If the release gate holds or fails because White Champi lacks composite/lot data, preserve the result; do not replace it with a monomolecular OAV or delete the named natural. Append the formatter's verbatim output under the generated Pipeline Analysis section and retain the full text for user presentation.

## Task 8: Local verification and acceptance

**Commands:**

```powershell
python -m pytest tests/test_floral_training_inventory.py tests/test_floral_depth.py tests/test_solforge_floral_adapter.py tests/test_complexity_registry_v9.py tests/test_complexity_registry_v8.py tests/test_complexity_registry_v6.py -q
python -m ruff check engine/perception/floral_depth.py engine/solforge/floral_adapter.py tests/test_floral_training_inventory.py tests/test_floral_depth.py tests/test_solforge_floral_adapter.py tests/test_complexity_registry_v9.py
python -m compileall -q engine/perception/floral_depth.py engine/solforge/floral_adapter.py
python scripts/pipeline_audit.py project-verify --quick --json
git diff --check
git status --short
```

Acceptance requires focused tests, Ruff, compile checks, quick verification, formula subtotal/stock checks, and registry census to pass. Any unsupported sensory result remains `NOT_TESTED`. Do not merge, hand off, or alter program-integration/publish branches.
