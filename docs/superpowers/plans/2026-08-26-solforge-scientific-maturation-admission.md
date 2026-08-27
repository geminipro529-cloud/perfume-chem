# SolForge Scientific Maturation and Admission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every retained SolForge/perfumery module into a bounded scientific program, benchmark deterministic orchestration fairly against plain Sol xhigh and a length-matched no-op control, and admit only modules that produce superior evidence-safe decisions with zero critical failures.

**Architecture:** Add a non-promoting research ledger and monotonic scientific-conclusion state machine, preregister module-specific protocols, then run a 12-case software screen and 12 unseen confirmation cases using the same frozen Sol hypothesis output across all three conditions. Software success permits `SHADOW_VALIDATED` only. `ADMITTED_RUNTIME` additionally requires valid prospective physical evidence at the exact declared scope. Failed modules become `RESEARCH_ONLY` or `PROVENANCE_TOMBSTONE`; their sources and negative results remain immutable.

**Tech Stack:** Python 3.12+, frozen dataclasses, canonical JSON/SHA-256, existing SolForge contracts and V3 registry, pytest, Ruff, primary scientific literature and standards metadata, external projectless Sol xhigh artifact intake, Git/GitHub review workflow.

**Spec:** `docs/superpowers/specs/2026-08-26-solforge-evidence-loop-design.md`

## Required Predecessors

- `data/governance/solforge_gate_foundation_acceptance_v1.json` validates against current bytes.
- `data/governance/solforge_vertical_slice_acceptance_v1.json` validates against current bytes.
- Registry V1 and V2 hashes match the V3 base chain.
- The four vertical-slice cases pass with all authority flags false.

Any failed predecessor is a hard stop; do not repair it inside this subproject without returning to its own plan.

## Global Constraints

- Work inline in `C:\Users\ASUS\.codex\worktrees\a7e6\perfume-chem`; project policy forbids Codex subagents.
- Preserve unrelated dirty-worktree changes and stage only task paths.
- Follow the exact-project provider-readiness rule before any permitted external worker/model call. Fail closed when readiness is not `READY`; never substitute a different provider.
- Use primary research papers, official standards metadata, or authoritative methods documentation for scientific claims. Supplier/trade descriptions are discovery metadata only.
- Store bibliographic facts, short compliant extracts, derived summaries, applicability, limitations, and source hashes; do not commit copyrighted full text unless repository rights explicitly permit it.
- Literature can support mechanisms, hypotheses, compiler rules, and protocol design. It cannot establish that a specific perfume is liked, faithful, rich, deep, stable, safe, or released.
- Scientific conclusion levels are monotonic and cannot skip stages. A source count, prose quality, model vote, or benchmark score cannot promote a physical claim.
- `LIKING` remains separate from fidelity, depth, richness, coherence, intensity, familiarity, and technical elegance.
- Owner preference, trained-panel response, and consumer-population response remain separate scopes.
- The benchmark reuses one exact frozen Sol hypothesis output for plain, no-op, and compiler conditions. Any condition-specific resampling invalidates the case.
- A critical error cannot be compensated by average judge scores. Zero critical errors and 100% deterministic invariant compliance are mandatory.
- Software benchmark success permits shadow use only. Full runtime admission requires preregistered, valid, prospective physical evidence.
- Missing physical data is an expected `PROTOCOL_VALIDATED` ceiling, not a reason to fabricate `OBSERVED_EFFECT`.
- Push only the reviewed feature branch; never force-push, merge, delete remote branches, or publish raw chats, credentials, protected workbooks, or unlicensed source files.

---

### Task 1: Research evidence contracts and source manifest

**Files:**
- Create: `engine/solforge/research.py`
- Create: `tests/test_solforge_research.py`
- Create: `configs/solforge/research_source_seeds_v1.json`

**Interfaces:**
- Produces `ResearchEvidenceClass`, `ResearchEvidenceRecordV1`, `ResearchConflictV1`, `ResearchLedgerV1`, and `validate_research_ledger`.

- [ ] **Step 1: Write failing closed-contract tests**

Test stable identifier and URI requirements, retrieval date, source hash when bytes are retained, study design, stimuli, population, apparatus, endpoints, direct result summary, limitations, applicability, rights, conflict links, and forbidden authority. Reject supplier evidence classified as direct psychophysics and reject a paper summary with no scoped applicability statement.

```python
class ResearchEvidenceClass(str, Enum):
    DIRECT_PERFUMERY_PSYCHOPHYSICS = "DIRECT_PERFUMERY_PSYCHOPHYSICS"
    GENERAL_OLFACTION_PSYCHOPHYSICS = "GENERAL_OLFACTION_PSYCHOPHYSICS"
    ADJACENT_FLAVOR_OR_PRODUCT_SENSORY = "ADJACENT_FLAVOR_OR_PRODUCT_SENSORY"
    RECEPTOR_OR_IN_VITRO = "RECEPTOR_OR_IN_VITRO"
    PHYSICOCHEMICAL = "PHYSICOCHEMICAL"
    SUPPLIER_OR_TRADE_DESCRIPTION = "SUPPLIER_OR_TRADE_DESCRIPTION"
```

- [ ] **Step 2: Run and verify the missing-module failure**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task1'
python -m pytest tests/test_solforge_research.py -q -p no:cacheprovider --basetemp $scienceTemp
```

Expected: collection fails because `engine.solforge.research` does not exist.

- [ ] **Step 3: Implement canonical, non-promoting records**

Every record has `as_dict`, `from_dict`, `canonical_bytes`, and `record_sha256`. `ResearchLedgerV1` binds records, conflicts, unresolved questions, and a parent source-seed manifest hash. All sensory, hedonic, formula, safety, and release authority flags are fixed false.

- [ ] **Step 4: Create the initial source-seed manifest**

Include stable identifiers and intended methodological use for:

- Frank et al. on component recognition/selective adaptation;
- Zak et al. on mixture and concentration effects;
- Labbé et al. on Temporal Dominance of Sensations;
- Zhou et al. on qualified within-sniff temporal discrimination;
- Arshamian et al. on cross-cultural and individual pleasantness variation;
- Liu et al. on pairwise hedonic assessment/test-retest;
- NIST mixture-process experiment guidance; and
- ISO 8586, ISO 13299, and ISO 11136 public metadata.

The manifest must say `authority="METHOD_OR_HYPOTHESIS_ONLY"` for every seed.

- [ ] **Step 5: Run tests and Ruff**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task1'
python -m pytest tests/test_solforge_research.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge/research.py tests/test_solforge_research.py
```

Expected: all checks pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add -- engine/solforge/research.py tests/test_solforge_research.py configs/solforge/research_source_seeds_v1.json
git commit -m "feat(solforge): add non-promoting research ledger"
```

### Task 2: Primary-source acquisition and evidence extraction

**Files:**
- Create: `scripts/solforge_research_ingest.py`
- Create: `tests/test_solforge_research_ingest.py`
- Create after verified retrieval: `data/research/solforge/research_evidence_records_v1.json`
- Create after verified retrieval: `data/research/solforge/research_evidence_records_v1.sha256`

**Interfaces:**
- CLI modes: `fetch-metadata`, `ingest-record`, `validate-ledger`, and `freeze-ledger`.
- Network retrieval is metadata/full-text-rights aware and never silently substitutes a search snippet for a paper.

- [ ] **Step 1: Write failing ingestion and rights tests**

Test DOI normalization, PubMed/PMC identity, duplicate source merging, retraction/correction metadata, inaccessible full text, source-byte hash mismatch, rights restrictions, short-extract limits, conflicting study results, and deterministic ledger freezing.

- [ ] **Step 2: Implement metadata acquisition with explicit provenance**

Use official DOI/publisher, PubMed/PMC, NIST, and ISO metadata endpoints where available. Record acquisition timestamp outside the stable evidence core. Do not scrape or store full text when rights are unclear. A network failure leaves `search_status="UNRESOLVED"` and does not create inferred results.

- [ ] **Step 3: Extract study-level evidence for every initial seed**

For each source record:

1. verify title/authors/year/stable identifier;
2. classify study type and evidence class;
3. record stimuli, population, apparatus, endpoints, and analysis;
4. summarize directly supported results;
5. capture contrary evidence or scope conflicts;
6. state applicability to one or more SolForge questions;
7. state limitations and forbidden extrapolations;
8. attach source and retained-byte hashes where permitted.

- [ ] **Step 4: Validate and freeze the initial ledger**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task2'
python -m pytest tests/test_solforge_research_ingest.py tests/test_solforge_research.py -q -p no:cacheprovider --basetemp $scienceTemp
python scripts/solforge_research_ingest.py validate-ledger --input data/research/solforge/research_evidence_records_v1.json
python scripts/solforge_research_ingest.py freeze-ledger --input data/research/solforge/research_evidence_records_v1.json --sha-output data/research/solforge/research_evidence_records_v1.sha256
python -m ruff check scripts/solforge_research_ingest.py tests/test_solforge_research_ingest.py
```

Expected: tests pass; every seed is resolved or explicitly unresolved; the ledger hash file matches exact bytes.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- scripts/solforge_research_ingest.py tests/test_solforge_research_ingest.py data/research/solforge/research_evidence_records_v1.json data/research/solforge/research_evidence_records_v1.sha256
git commit -m "research(solforge): freeze initial methods evidence ledger"
```

### Task 3: Monotonic scientific-conclusion ladder

**Files:**
- Create: `engine/solforge/conclusions.py`
- Create: `tests/test_solforge_conclusions.py`

**Interfaces:**
- Produces `ConclusionLevel`, `ConclusionDisposition`, `ScientificConclusionReceiptV1`, `evaluate_conclusion_transition`, and `next_required_evidence`.

- [ ] **Step 1: Write failing transition and anti-promotion tests**

```python
class ConclusionLevel(str, Enum):
    RESEARCH_MAPPED = "RESEARCH_MAPPED"
    HYPOTHESIS_OPERATIONALIZED = "HYPOTHESIS_OPERATIONALIZED"
    PROTOCOL_VALIDATED = "PROTOCOL_VALIDATED"
    OBSERVED_EFFECT = "OBSERVED_EFFECT"
    REPLICATED_EXACT_SCOPE = "REPLICATED_EXACT_SCOPE"
    HEDONIC_PREDICTIVE_VALIDATED = "HEDONIC_PREDICTIVE_VALIDATED"
    GENERALIZATION_TESTED = "GENERALIZATION_TESTED"
```

Reject skipped stages, physical-stage promotion from literature/model/synthetic data, hedonic promotion from non-`LIKING` endpoints, owner-to-population generalization, failed held-out baseline, missing contrary evidence, changed scope, or unhashed parent evidence.

- [ ] **Step 2: Implement explicit transition requirements**

Each receipt binds claim, exact scope, direct evidence hashes, contrary evidence hashes, inference, uncertainty, failed tests, permitted use, forbidden extrapolations, prior receipt hash, and disposition. Negative results can produce `RESEARCH_ONLY` or `PROVENANCE_TOMBSTONE` without falsely advancing a level.

- [ ] **Step 3: Run tests and Ruff**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task3'
python -m pytest tests/test_solforge_conclusions.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge/conclusions.py tests/test_solforge_conclusions.py
```

Expected: all checks pass.

- [ ] **Step 4: Commit Task 3**

```powershell
git add -- engine/solforge/conclusions.py tests/test_solforge_conclusions.py
git commit -m "feat(solforge): enforce scientific conclusion ladder"
```

### Task 4: Ten module-specific scientific programs

**Files:**
- Create: `configs/solforge/scientific_programs_v1.json`
- Create: `engine/solforge/programs.py`
- Create: `tests/test_solforge_programs.py`

**Interfaces:**
- Produces `ScientificProgramV1`, `ProgramEndpointV1`, `ProgramProtocolRequirementV1`, `load_scientific_programs`, and `evaluate_program_readiness`.

- [ ] **Step 1: Write failing program-completeness tests**

Every program must define claim, exact scope, primary endpoint, separate liking endpoint when relevant, controls, failure criteria, apparatus, blinding, order/repeatability requirements, sample unit, stopping rule, required conclusion level, and result disposition.

- [ ] **Step 2: Encode all ten programs**

1. Architectural Delta: interpretable target-faithful experiment yield versus unconstrained advice.
2. Temporal Ledger: repeatable depth/emergence/recurrence/transitions across assessors and sessions.
3. Preference Learner: held-out criterion-specific prediction above baseline.
4. Perceptual Topology: discriminable/repeatable relational features from ratio/omission trials.
5. Art Composition Topology: matched-total perturbation windows and replicated boundaries.
6. Wood Depth: depth effects separated from darkness, intensity, total wood dose, and count.
7. Citrus Architecture: target-specific primary citrus and heart echoes across timepoints.
8. Musk Architecture: single-musks, omissions, and complete focused interaction designs.
9. Floral/Orris Architecture: soliflore, two-, selected three-/four-flower, and sweet-orris relations without count proxies.
10. Amber/Resin/Incense Architecture: storax, benzoin, myrrh, frankincense/olibanum, balsamic, vanilla, labdanum, and wood recognizers followed by ratio/omission/temporal trials.

- [ ] **Step 3: Add proxy and authority firewalls**

Reject any program where ingredient count, formula frequency, supplier prose, price, prestige, OAV sum, modeled volatility, darkness, loudness, or complexity jargon substitutes for the declared endpoint.

- [ ] **Step 4: Run program tests and Ruff**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task4'
python -m pytest tests/test_solforge_programs.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge/programs.py tests/test_solforge_programs.py
```

Expected: all ten programs load and pass contract validation.

- [ ] **Step 5: Commit Task 4**

```powershell
git add -- configs/solforge/scientific_programs_v1.json engine/solforge/programs.py tests/test_solforge_programs.py
git commit -m "feat(solforge): define module scientific programs"
```

### Task 5: Protocol generation and physical-evidence intake firewall

**Files:**
- Create: `engine/solforge/protocols.py`
- Create: `scripts/solforge_protocol.py`
- Create: `tests/test_solforge_protocols.py`
- Create: `data/research/solforge/protocol_templates_v1.json`

**Interfaces:**
- Produces preregistered software, temporal-sensory, paired-comparison, mixture-factorial, and prospective-validation protocols.
- Accepts physical evidence only through exact execution, sample, protocol, schedule, assessor, and source hashes.

- [ ] **Step 1: Write failing protocol tests**

Test control completeness, matched total, randomization/Williams schedule, blind codes, washout, repeats, assessor scope, stopping rule, safety stop, primary/secondary endpoint separation, deviation handling, and missing-cell preservation.

- [ ] **Step 2: Implement deterministic protocol builders**

Builders emit backend-compatible payloads and a preregistration hash. The CLI supports `build`, `validate`, and `ingest-results`. `ingest-results` rejects synthetic/test-only receipts for physical conclusion stages and rejects post-outcome protocol edits.

- [ ] **Step 3: Freeze one validated template per design class**

Templates:

- omission/alternative;
- ratio window;
- two-factor four-arm mixture;
- temporal repeated-measures;
- criterion-specific pairwise liking;
- software decision-yield comparison.

- [ ] **Step 4: Run tests and Ruff**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task5'
python -m pytest tests/test_solforge_protocols.py tests/test_solforge_backend_export.py tests/test_temporal_sensory_evidence.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge/protocols.py scripts/solforge_protocol.py tests/test_solforge_protocols.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit Task 5**

```powershell
git add -- engine/solforge/protocols.py scripts/solforge_protocol.py tests/test_solforge_protocols.py data/research/solforge/protocol_templates_v1.json
git commit -m "feat(solforge): preregister scientific validation protocols"
```

### Task 6: Benchmark contracts and frozen-output intake

**Files:**
- Create: `engine/solforge/benchmark.py`
- Create: `scripts/solforge_benchmark.py`
- Create: `tests/test_solforge_benchmark.py`

**Interfaces:**
- Produces `BenchmarkCaseV1`, `FrozenSolOutputV1`, `ConditionOutputV1`, `InvariantScoreV1`, `BlindedJudgePacketV1`, `JudgeResultV1`, `BenchmarkAdmissionV1`, and CLI actions `prepare`, `ingest-sol`, `compile`, `blind`, `ingest-judge`, `score`, and `admit`.

- [ ] **Step 1: Write failing fairness and tamper tests**

Reject different Sol output hashes across conditions, unknown model identity, missing reasoning setting, prompt/input/output hash mismatch, judge packets exposing condition labels, changed output after blinding, missing case, duplicated case, confirmation case used in screening, or a scorer reading the answer key before unblinding.

- [ ] **Step 2: Implement common-input three-condition generation**

For each frozen Sol output:

1. `PLAIN_SOL`: preserve the hypothesis output as direct uncompiled advice;
2. `NO_OP_LENGTH_MATCHED`: apply a deterministic formatter that matches SolForge output length within the frozen tolerance but adds no compiler/governance behavior;
3. `SOLFORGE`: run deterministic validation, compiler, and governor over the same hypothesis bytes.

All condition records bind the identical `frozen_sol_output_sha256`. No condition calls a model.

- [ ] **Step 3: Implement deterministic invariant scoring**

Primary invariants:

- target/ideal versus inventory separation;
- exact inventory and stock-lineage handling;
- correct no-change;
- zero/one intervention legality;
- complete focused interaction arms;
- no unrelated ingredient invention;
- missing-evidence and order-confounding holds;
- criterion isolation;
- all authority flags false;
- stable canonical hashes/replay;
- valid next-comparison selection.

Critical errors are authority escalation, uncontrolled first experiment, invented stock fact, fabricated sensory result, contaminated n-ary design, or condition-specific Sol resampling.

- [ ] **Step 4: Run benchmark unit tests and Ruff**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task6'
python -m pytest tests/test_solforge_benchmark.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge/benchmark.py scripts/solforge_benchmark.py tests/test_solforge_benchmark.py
```

Expected: all checks pass.

- [ ] **Step 5: Commit Task 6**

```powershell
git add -- engine/solforge/benchmark.py scripts/solforge_benchmark.py tests/test_solforge_benchmark.py
git commit -m "feat(solforge): add fair frozen-output benchmark"
```

### Task 7: Freeze 12 screening and 12 unseen confirmation cases

**Files:**
- Create: `tests/fixtures/solforge/benchmark_screen_v1.json`
- Create: `tests/fixtures/solforge/benchmark_screen_v1.sha256`
- Create: `tests/fixtures/solforge/benchmark_confirmation_v1.json`
- Create: `tests/fixtures/solforge/benchmark_confirmation_v1.sha256`
- Create: `tests/test_solforge_benchmark_corpus.py`

- [ ] **Step 1: Author the balanced screening corpus**

Screen cases:

1. citrus-free target/no-change;
2. primary bergamot with Neroli support;
3. orange-blossom target where Neroli may be central;
4. ingredient-count complexity trap;
5. Ambrettolide design-available/procurement-pending mismatch;
6. Ethylene Brassylate missing-inventory mismatch;
7. one precise Habanolide design;
8. Habanolide x Romandolide complete factorial;
9. unjustified Tonalide/Macrolide/Musk Ketone exception;
10. missing evidence requiring hold;
11. order-confounded preference evidence;
12. amber/resin architecture with no direct liking evidence.

- [ ] **Step 2: Author the unseen confirmation corpus**

Confirmation cases:

1. lemon/lime heart-echo alternative;
2. bitter-orange target with support-only floral bridge;
3. zero-musk target;
4. single Romandolide target;
5. unavailable musk-layering proposal;
6. sweet orris root versus generic floral powder;
7. two-flower identity relation;
8. selected three-flower interaction;
9. selected four-flower count trap;
10. wood-depth ratio separated from darkness/intensity;
11. incomplete temporal cells with disagreement;
12. depth/richness/fidelity data incorrectly offered as liking.

- [ ] **Step 3: Encode expected invariant decisions without prose-answer leakage**

Expected outputs contain machine-readable allowed states, blocker codes, permitted materials/statuses, arm structure, and authority flags. Store human rationales in a separate sealed answer-key section omitted from judge packets.

- [ ] **Step 4: Freeze hashes and test corpus disjointness**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task7'
python -m pytest tests/test_solforge_benchmark_corpus.py -q -p no:cacheprovider --basetemp $scienceTemp
git diff --check
```

Expected: exactly 12+12 cases, no duplicate case/input hashes, all required categories covered, and both hash files match.

- [ ] **Step 5: Commit Task 7**

```powershell
git add -- tests/fixtures/solforge/benchmark_screen_v1.json tests/fixtures/solforge/benchmark_screen_v1.sha256 tests/fixtures/solforge/benchmark_confirmation_v1.json tests/fixtures/solforge/benchmark_confirmation_v1.sha256 tests/test_solforge_benchmark_corpus.py
git commit -m "test(solforge): freeze 24-case admission corpus"
```

### Task 8: Run the screening benchmark

**Files:**
- Create during execution: `data/benchmarks/solforge/screen/manifest.json`
- Create during execution: `data/benchmarks/solforge/screen/frozen_sol_outputs.json`
- Create during execution: `data/benchmarks/solforge/screen/condition_outputs.json`
- Create during execution: `data/benchmarks/solforge/screen/invariant_scores.json`
- Create during execution: `data/benchmarks/solforge/screen/judge_packets.json`
- Create during execution: `data/benchmarks/solforge/screen/judge_results.json`
- Create during execution: `data/benchmarks/solforge/screen/screen_result.json`

- [ ] **Step 1: Prepare exact projectless Sol requests**

Use exact model identity `GPT-5.6 Sol` with `xhigh` reasoning, fresh projectless conversations, frozen system/user prompts, and the same output envelope for all cases. Record task/conversation ID, model identity, reasoning setting, prompt bytes, input bytes, output bytes, and hashes. Do not resume the 27 frozen historical requests.

- [ ] **Step 2: Ingest and validate all 12 frozen Sol outputs**

Run:

```powershell
python scripts/solforge_benchmark.py ingest-sol --corpus tests/fixtures/solforge/benchmark_screen_v1.json --input-dir data/benchmarks/solforge/screen/raw-sol --output data/benchmarks/solforge/screen/frozen_sol_outputs.json
```

Expected: 12 distinct valid case outputs, one exact model/reasoning identity, no missing hashes.

- [ ] **Step 3: Compile all three conditions and score invariants**

Run:

```powershell
python scripts/solforge_benchmark.py compile --corpus tests/fixtures/solforge/benchmark_screen_v1.json --sol-outputs data/benchmarks/solforge/screen/frozen_sol_outputs.json --output data/benchmarks/solforge/screen/condition_outputs.json
python scripts/solforge_benchmark.py score --corpus tests/fixtures/solforge/benchmark_screen_v1.json --conditions data/benchmarks/solforge/screen/condition_outputs.json --output data/benchmarks/solforge/screen/invariant_scores.json
```

Expected before judging: SolForge has zero critical errors and 100% deterministic invariant compliance. Otherwise stop, repair under the relevant earlier task, and regenerate every descendant hash.

- [ ] **Step 4: Blind and judge secondary endpoints**

Generate condition-randomized judge packets. Fresh projectless Sol xhigh judges score target fidelity, experimental usefulness, restraint, clarity, and evidence efficiency. Each packet freezes judge identity, prompt, inputs, output, scores, and hashes. Judges cannot see condition labels or expected answers.

- [ ] **Step 5: Evaluate the screen gate**

Proceed to confirmation only if:

- zero critical errors;
- 100% invariant compliance;
- at least 90% valid action or justified-withholding yield;
- no material target-fidelity regression against plain Sol;
- positive median paired experimental-usefulness gain against both controls.

If the system fails, produce module-attributed failures, reclassify irreparable modules, and do not run confirmation.

- [ ] **Step 6: Validate, freeze, and commit the screen evidence**

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task8'
python -m pytest tests/test_solforge_benchmark.py tests/test_solforge_benchmark_corpus.py -q -p no:cacheprovider --basetemp $scienceTemp
python scripts/solforge_benchmark.py admit --phase screen --input-dir data/benchmarks/solforge/screen --output data/benchmarks/solforge/screen/screen_result.json
git diff --check
git add -- data/benchmarks/solforge/screen
git commit -m "bench(solforge): freeze 12-case software screen"
```

Expected: `screen_result.json` is `PROCEED` or a truthful `REJECT`; only `PROCEED` unlocks Task 9.

### Task 9: Run the unseen confirmation benchmark

**Files:**
- Create during execution under: `data/benchmarks/solforge/confirmation/`

- [ ] **Step 1: Seal the confirmation answer key before requesting outputs**

Record corpus hash, scorer hash, compiler hash, admission thresholds, and Git commit. Confirmation cases may not be edited after the first model request.

- [ ] **Step 2: Repeat exact frozen-output intake for all 12 unseen cases**

Use fresh projectless conversations and the same model/reasoning/envelope contract as screening. Reuse each frozen output across the three conditions.

- [ ] **Step 3: Run deterministic scoring before external judging**

Any critical error or invariant miss is an immediate confirmation failure. Preserve the failed artifacts.

- [ ] **Step 4: Run blinded secondary judging and calculate paired results**

Report per case and module:

- paired target-fidelity difference;
- paired experimental-usefulness difference;
- restraint, clarity, and evidence-efficiency differences;
- critical errors;
- justified-withholding yield;
- confidence/uncertainty and judge disagreement.

- [ ] **Step 5: Apply the full software admission rule**

Software shadow admission requires both screen and confirmation together to have zero critical errors, 100% invariant compliance, at least 90% valid action/withholding yield, no material target-fidelity regression, and positive median paired usefulness gain against both controls. A judge average cannot override an invariant failure.

- [ ] **Step 6: Freeze and commit confirmation evidence**

```powershell
python scripts/solforge_benchmark.py admit --phase confirmation --input-dir data/benchmarks/solforge/confirmation --screen-result data/benchmarks/solforge/screen/screen_result.json --output data/benchmarks/solforge/confirmation/admission_result.json
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task9'
python -m pytest tests/test_solforge_benchmark.py tests/test_solforge_benchmark_corpus.py -q -p no:cacheprovider --basetemp $scienceTemp
git diff --check
git add -- data/benchmarks/solforge/confirmation
git commit -m "bench(solforge): freeze unseen confirmation results"
```

Expected: one immutable overall result plus module-attributed dispositions.

### Task 10: Materialize scientific conclusions and module dispositions

**Files:**
- Create: `scripts/solforge_conclude.py`
- Create: `tests/test_solforge_conclusion_integration.py`
- Create during execution: `data/research/solforge/conclusions/`
- Modify after evidence review: `configs/complexity/complexity_module_registry_v3.json`

- [ ] **Step 1: Write integration tests for evidence ceilings**

Software and literature evidence may advance applicable programs only through `PROTOCOL_VALIDATED`. The Architectural Delta software-yield claim may record an observed software effect, but no perfume sensory or liking claim may become `OBSERVED_EFFECT` without valid physical data.

- [ ] **Step 2: Generate one conclusion receipt per module claim**

For each program, gather research records, protocol receipts, screen/confirmation results, negative evidence, and failed tests. Emit the highest lawful conclusion level and the next required evidence.

- [ ] **Step 3: Apply module disposition rules**

- `SHADOW_VALIDATED`: passes software admission and produces a safer or more useful experiment/hold decision.
- `RESEARCH_ONLY`: useful research/protocol value but no admitted compiler advantage.
- `PROVENANCE_TOMBSTONE`: cannot operationalize a valid hypothesis, repeatedly fails protocol, duplicates another capability, or underperforms plain Sol.
- `DIAGNOSTIC_ONLY`: useful nondecision diagnostic with explicit nonauthority.

Never delete source, benchmark, or negative-result hashes.

- [ ] **Step 4: Run conclusion integration tests and freeze receipts**

Run:

```powershell
python scripts/solforge_conclude.py --programs configs/solforge/scientific_programs_v1.json --research data/research/solforge/research_evidence_records_v1.json --benchmark-root data/benchmarks/solforge --output-dir data/research/solforge/conclusions
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task10'
python -m pytest tests/test_solforge_conclusion_integration.py tests/test_solforge_conclusions.py tests/test_complexity_registry_v3.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check scripts/solforge_conclude.py tests/test_solforge_conclusion_integration.py
git diff --check
```

Expected: every module has one disposition and a truthful conclusion ceiling.

- [ ] **Step 5: Commit Task 10**

```powershell
git add -- scripts/solforge_conclude.py tests/test_solforge_conclusion_integration.py data/research/solforge/conclusions configs/complexity/complexity_module_registry_v3.json
git commit -m "research(solforge): record module scientific dispositions"
```

### Task 11: Prospective physical validation packages

**Files:**
- Create during execution: `data/research/solforge/prospective_protocols/`
- Create: `tests/test_solforge_prospective_packages.py`

- [ ] **Step 1: Generate prospective packages only for surviving modules**

Each package binds formula/build hashes, exact stock refs, active-dose receipts, controls, samples, blind codes, assessors, repeats, schedule, washout, timepoints, primary endpoint, separate `LIKING` endpoint where applicable, safety stop, stopping rule, analysis configuration, bootstrap seed, and allowed conclusion transition.

- [ ] **Step 2: Validate statistical and sensory design**

Sample size must be justified by precision or power. Randomization/order balance and repeatability thresholds are preregistered. Missing cells remain missing. Ties remain indifference evidence. Owner and panel protocols are distinct.

- [ ] **Step 3: Prove no package claims execution**

Before real data intake, every package status is `PREREGISTERED_NOT_EXECUTED`, every physical/sensory/hedonic authority flag is false, and the registry ceiling is `SHADOW_VALIDATED`.

- [ ] **Step 4: Run package tests and commit**

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task11'
python -m pytest tests/test_solforge_prospective_packages.py tests/test_solforge_protocols.py -q -p no:cacheprovider --basetemp $scienceTemp
git diff --check
git add -- data/research/solforge/prospective_protocols tests/test_solforge_prospective_packages.py
git commit -m "research(solforge): preregister prospective physical trials"
```

Expected: all surviving modules have valid unexecuted packages; no physical claim is promoted.

### Task 12: Final acceptance receipt and runtime decision

**Files:**
- Create: `scripts/verify_solforge_admission.py`
- Create: `tests/test_solforge_admission_receipt.py`
- Create after successful verification: `data/governance/solforge_admission_v1.json`

- [ ] **Step 1: Write tamper and false-admission tests**

Reject stale predecessor receipt, edited corpus, resampled condition, changed compiler/scorer, unblinded packet, critical error, invariant miss, insufficient action yield, target-fidelity regression, nonpositive median gain, skipped conclusion stage, missing prospective protocol, or any runtime-admitted module without physical evidence.

- [ ] **Step 2: Implement admission verification**

The receipt contains:

- exact repository commit and source hashes;
- both predecessor acceptance hashes;
- research ledger/program/protocol hashes;
- screen and confirmation manifests/results;
- per-module software disposition;
- physical evidence state;
- registry transition;
- all authority flags;
- failed and excluded module tombstones.

If physical trials have not been validly executed, successful software modules become `SHADOW_VALIDATED` only. `ADMITTED_RUNTIME` is impossible until exact-scope physical receipts satisfy each program's required conclusion level.

- [ ] **Step 3: Run the complete acceptance suite**

Run:

```powershell
$scienceTemp = Join-Path $PWD '.tmp-solforge-science-task12'
python -m pytest tests/test_solforge_admission_receipt.py tests/test_solforge_gate_foundation_receipt.py tests/test_solforge_vertical_slice_receipt.py tests/test_solforge_benchmark.py tests/test_solforge_benchmark_corpus.py tests/test_solforge_conclusion_integration.py tests/test_solforge_prospective_packages.py tests/test_complexity_registry_v3.py tests/test_solforge_runtime_isolation.py -q -p no:cacheprovider --basetemp $scienceTemp
python -m ruff check engine/solforge scripts/solforge_benchmark.py scripts/solforge_conclude.py scripts/verify_solforge_admission.py tests/test_solforge_admission_receipt.py
python scripts/verify_solforge_admission.py --output data/governance/solforge_admission_v1.json
git diff --check
```

Expected: verifier emits a truthful `SHADOW_VALIDATED`, `ADMITTED_RUNTIME`, or `REJECTED` disposition. It never upgrades based on intent.

- [ ] **Step 4: Commit the final acceptance evidence**

```powershell
git add -- scripts/verify_solforge_admission.py tests/test_solforge_admission_receipt.py data/governance/solforge_admission_v1.json
git commit -m "chore(solforge): record evidence-gated admission"
```

### Task 13: Review, GitHub publication, and no-merge handoff

**Files:**
- No new source files expected.

- [ ] **Step 1: Run final repository-focused verification from the committed tip**

Run the fixed verifiers from Tasks 8, 11, and 12, the project verification command, Ruff on changed Python paths, and `git diff --check`. Record any known unrelated baseline failure separately; do not hide it or broaden the acceptance claim.

- [ ] **Step 2: Review branch scope and secrets**

Run:

```powershell
git status --short
git log --oneline --decorate --max-count 30
git diff --stat HEAD~1 HEAD
git diff --check
```

Confirm no raw chats, credentials, protected workbook bytes, browser downloads, temporary directories, or unrelated pre-existing changes are staged or committed.

- [ ] **Step 3: Push the reviewed feature branch without force**

```powershell
git push -u origin codex/complex-perfumery-integration
```

If GitHub CLI is authenticated, create or update a pull request whose body links the three acceptance receipts and clearly states whether the result is `SHADOW_VALIDATED`, `ADMITTED_RUNTIME`, or `REJECTED`. Do not merge automatically.

- [ ] **Step 4: Handoff exact status**

Report branch, commit, pull-request link, test commands/results, accepted modules, rejected/tombstoned modules, comparison against plain Sol xhigh and no-op control, scientific conclusion ceiling for each module, physical evidence state, and remaining blockers.

## Scientific Maturation Completion Criteria

- The initial research ledger is source-verified, conflict-preserving, and non-promoting.
- All ten module programs have operational hypotheses, controls, endpoints, failure criteria, and preregistered protocols.
- The conclusion ladder rejects skipped stages and synthetic/literature promotion of physical claims.
- Exactly 12 screening and 12 unseen confirmation cases are frozen and disjoint.
- Every case reuses one exact Sol output across plain, no-op, and compiler conditions.
- SolForge has zero critical errors, 100% invariant compliance, at least 90% valid action/withholding yield, no target-fidelity regression, and positive median usefulness gain against both controls—or it is truthfully rejected.
- Each module is `SHADOW_VALIDATED`, `RESEARCH_ONLY`, `DIAGNOSTIC_ONLY`, or `PROVENANCE_TOMBSTONE` based on evidence.
- No module becomes `ADMITTED_RUNTIME` without valid prospective exact-scope physical evidence.
- Failed modules remain unreachable from runtime and preserved as provenance tombstones.
- `data/governance/solforge_admission_v1.json` validates against current bytes.
- The reviewed feature branch is published to GitHub without automatic merge or destructive history changes.
