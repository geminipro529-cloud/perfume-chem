# Complexity Ensemble and ChatGPT xhigh Benchmark Design

- **Date:** 2026-08-22
- **Status:** Approved architecture; implementation and paid benchmarking not started
- **Repository:** `D:\chatbots\perfume-chem`
- **ChatGPT control:** Plain ChatGPT xhigh with only the frozen brief, authoritative inventory, and canonical evidence
- **Decision method:** Staged paired benchmark followed by relevance-gated ablation

## 1. Decision Summary

Perfume-Chem will gain one library-level complexity ensemble that classifies and
invokes the repository's admitted native complexity capabilities through a
single deterministic contract. It will not create a second scientific pipeline,
copy quarantined package code, or collapse the existing multi-axis outputs into
one beauty score.

The ensemble will be tested against the user-approved control: plain ChatGPT
xhigh receiving the same frozen task brief, inventory evidence, and canonical
evidence, but no complexity-module output. The comparison will use exact input
hashes, blinded arm labels, deterministic hard gates, a fixed scoring rubric,
and paired cases.

The combined treatment must win at least 12 of 16 cases, improve the median
rubric score by at least five points, and introduce no critical authority,
inventory, safety, physical-result, sensory-result, or provenance regression.
Only then will contributing module families proceed to leave-one-family-out
ablation. A module family that fails its role-specific test receives one bounded
repair cycle and an unseen holdout check. A persistent underperformer is
disabled and recorded as `RETIRED_BENCHMARK_UNDERPERFORMER`; its bytes and
provenance are preserved rather than irreversibly deleted.

No physical liking, similarity, stability, safety, measured headspace, strict
empirical OAV, installation, publication, or release authority is created by
this software benchmark.

## 2. Context

The repository already contains several distinct kinds of complexity work:

1. structural construction analysis;
2. bounded expansion and experiment-frontier generation;
3. causal-isolate, formula-signature, and n-ary interaction contracts;
4. claim-scoped admission, OAV binding, and model lifecycle controls;
5. within-sniff, temporal-observation, order-balance, and sensory-panel
   contracts; and
6. legacy or future temporal and hedonic candidates that do not currently carry
   the same authority as the clean-room native contracts.

These modules do not share one success criterion. Some are capability modules
intended to improve analysis; others are noncompensatory guardrails intended to
prevent false claims. The benchmark must therefore assess both output quality
and critical-error prevention. A safety or provenance gate is not discarded
merely because it does not make prose more attractive.

The V16 external complexity package remains verified, quarantined reference
ancestry with unknown rights. Its code, schemas, registries, formulas, and data
are not installed. Existing native clean-room diagnostics remain controlling
for their declared scope.

## 3. Goals

1. Create one inspectable registry of every discovered complexity-related
   module and assign each an explicit status and role.
2. Provide one deterministic ensemble input and output contract without
   creating a new pipeline script.
3. Determine whether the admitted native ensemble materially outperforms plain
   ChatGPT xhigh on representative Complex Perfumery tasks.
4. Identify which module families add value, prevent critical errors, add no
   value, or cause regressions.
5. Allow one evidence-based repair cycle for underperforming modules.
6. Disable and archive persistent underperformers without destroying provenance
   or unrelated consumers.
7. Preserve target identity, target/build separation, exact stock basis, OAV
   authority, and scientific claim ceilings throughout the experiment.
8. Prevent duplicate paid work and make every external model request and result
   independently auditable.

## 4. Non-Goals

- Installing or copying code from quarantined or unknown-rights packages.
- Creating a parallel pipeline, new pipeline script, schema authority, or truth
  store.
- Optimizing a perfume toward a scalar score instead of its name and target
  architecture.
- Treating model preference as physical hedonic evidence.
- Claiming sensory, safety, stability, similarity, headspace, procurement,
  compounding, publication, or release authority.
- Automatically deleting source files, package bytes, test evidence, receipts,
  or modules used by unrelated repository consumers.
- Using DeepLuna Fast, Luna fallback, Codex subagents, or an alternate provider
  as a substitute for the requested ChatGPT xhigh control.
- Reusing an xhigh response when the exact model setting, prompt bytes, case
  hash, or relevant evidence hash differs.

## 5. Module Census and Classification

### 5.1 Required registry states

Every discovered complexity-related artifact must be represented in the module
registry with one of these states:

| State | Meaning |
|---|---|
| `ACTIVE_CANDIDATE` | Admitted native implementation eligible for the treatment ensemble |
| `MANDATORY_GUARDRAIL` | Native noncompensatory gate evaluated by critical-error prevention |
| `EVIDENCE_ONLY_NOT_ADMITTED` | Quarantined package or design ancestry; never imported at runtime |
| `FUTURE_CANDIDATE_NOT_VALIDATED` | Local candidate lacking the evidence required for active use |
| `REDUNDANT_NOT_INVOKED` | Duplicates a stronger controlling native capability |
| `RETIRED_BENCHMARK_UNDERPERFORMER` | Failed a bounded repair and holdout retest; disabled but preserved |
| `NOT_EVALUATED_NO_RELEVANT_CASE` | No frozen case exercised the module; no performance conclusion allowed |

The census fails closed if a discovered candidate lacks a classification, if a
registry path cannot be resolved, or if current bytes differ from the recorded
hash without a new registry revision.

The discovery scope is fixed to these repository roots:

- `engine/` and `future_modules/` for executable Python surfaces;
- `incoming_review/` and `references/existing_evidence_packages/` for external
  or historical package ancestry;
- `data/governance/` for package and installation receipts; and
- `chat_bridge/complex_perfumery/` for explicit module/package handoff records.

Discovery uses path names, import references, receipt metadata, manifest roles,
and the terms `complexity`, `hedonic`, `temporal`, `interaction`, `ablation`,
`admission`, and `sensory`. Each match is either linked to one registry record
or explicitly dismissed with a recorded non-module reason. This makes “all
modules” a reproducible census rather than an informal filename list.

### 5.2 Initial admitted native families

The implementation plan will start from these current native families and will
recompute their exact hashes before any benchmark:

| Family | Current native surfaces | Primary evaluation role |
|---|---|---|
| Construction profile | `engine/perception/construction_complexity.py` | Multi-axis structural diagnosis without an overall beauty score |
| Expansion frontier | `engine/perception/complexity_expansion.py` | Bounded novelty, collision review, Pareto experiment selection, and declared-scope saturation |
| Experimental design | `engine/scientific_validation/complexity_design_contracts.py` | Causal isolate, formula signature, and n-ary design integrity |
| Admission and lifecycle | `engine/scientific_validation/complexity_model_admission.py`; `engine/physics/model_lifecycle.py` | Claim-scoped gates, exact OAV binding, drift, supersession, and retirement |
| Temporal and sensory integrity | `engine/sensory/within_sniff.py`; `engine/sensory/temporal_observations.py`; `engine/sensory/order_balance.py`; `engine/sensory/panel_contract.py` | Apparatus validity, descriptive temporal summaries, balanced presentation, and claim ceilings |

The admission/lifecycle and temporal/sensory integrity families contain
mandatory guardrails. Their success may be demonstrated by preventing a
critical error even when they do not increase stylistic quality.

### 5.3 Legacy, future, and external candidates

`engine/temporal_graph.py`, `engine/temporal_volatility.py`,
`engine/hedonic_model.py`, and `future_modules/family_hedonic_optimizer.py`
must be inventoried but are not automatically active. Their current dependency
and unsupported-science boundaries must be reviewed before classification.

All complexity-related bytes under `incoming_review/`, historical ChatGPT
packages, V16/V17/V18 collections, and external xhigh packages remain
`EVIDENCE_ONLY_NOT_ADMITTED` unless a separate exact-byte, rights, clean-room,
and native-fit process grants a narrower status. This benchmark cannot grant
that admission.

## 6. Architecture

### 6.1 Library-level ensemble

The combined system will be a focused library module, not a new pipeline script.
It will expose three operations:

1. `census`: discover registered module descriptors, verify paths and hashes,
   and fail on unclassified candidates;
2. `evaluate`: invoke only eligible modules for one immutable case packet and
   return separated structured outputs; and
3. `ablate`: evaluate the same case with one declared family omitted while
   recording the exact omission.

The existing `scripts/pipeline_audit.py` entry point may gain a bounded
subcommand that calls this library. It must not duplicate scientific logic or
become a second source of truth.

### 6.2 Immutable case packet

Each case packet will contain:

- case identifier and category;
- exact target name, identity, and brief;
- target/ideal formula evidence when relevant;
- current-inventory build evidence when relevant;
- authoritative inventory source identity, revision, and SHA-256;
- local `inventory.txt` hash and reconciliation state;
- formula, dose, dilution, and immediate-parent hashes when relevant;
- canonical evidence references and hashes;
- requested output contract;
- permitted claim ceiling;
- module relevance declarations;
- expected deterministic invariants; and
- a nonce that prevents duplicate submission ambiguity.

If the current project inventory workbook and the local inventory representation
conflict at the material, strength, stock, or product-basis level, the affected
case is held. Neither benchmark arm may silently choose the convenient value.

### 6.3 Separated ensemble output

The treatment input to xhigh will contain a normalized module bundle with
separate sections for:

- construction axes;
- expansion directions and Pareto frontier;
- causal/signature/n-ary design checks;
- OAV/admission/lifecycle gates;
- temporal and sensory design checks;
- missing or abstained evidence;
- module failures and claim ceilings; and
- exact source and configuration hashes.

The bundle must not emit one aggregate complexity or beauty score. It must not
convert advisory outputs into formula, stock, sensory, safety, or release
authority.

## 7. Frozen Benchmark Corpus

The benchmark will freeze 16 cases, four in each category:

1. target identity and formula-architecture audit;
2. reconstruction or revision with target/build separation;
3. missing-chemical impact and current-inventory build planning; and
4. experimental, temporal, sensory, admission, or evidence design.

The corpus will include straightforward, adversarial, missing-data, and
conflicting-source cases. At least four cases must contain traps that a
guardrail should catch, such as stock-strength ambiguity, target/build
collapse, unsupported hedonic promotion, formula/OAV mismatch, or a false
physical-result claim.

Cases and expected deterministic invariants are frozen before any xhigh output
is obtained. The case manifest records exact bytes and a SHA-256 for the entire
corpus. Benchmark prompts, rubrics, or invariants may not be edited in response
to seeing treatment or control results.

## 8. ChatGPT xhigh Execution Contract

### 8.1 Clean control

The control is plain ChatGPT xhigh with only:

- the frozen case brief;
- authoritative inventory evidence required by that case;
- canonical evidence required by that case; and
- the common output contract.

It receives no module bundle, module names, treatment hints, prior treatment
output, project complexity instructions, or earlier benchmark-case transcript.

### 8.2 Treatment

The treatment uses the same ChatGPT model identity, xhigh reasoning setting,
case bytes, evidence bytes, output contract, and isolation conditions. Its only
additional input is the deterministic ensemble bundle for that case.

### 8.3 Environment proof

Each run requires an execution receipt proving:

- actual ChatGPT model identity;
- xhigh reasoning setting;
- projectless or otherwise demonstrably uncontaminated context;
- no prior case transcript visible to the model;
- exact prompt and attachment hashes;
- submission and completion timestamps;
- exact output bytes and hash;
- provider request or conversation identifier;
- input and output token counts, latency, and price when exposed by the product;
- accounting state where available; and
- no retry or duplicate submission for the same nonce.

An existing chat with prior perfume context is not a clean control. If the
actual model setting or clean context cannot be proven, the result is
`BENCHMARK_BLOCKED_UNVERIFIED_XHIGH`, not a benchmark observation.

### 8.4 Randomization and blinding

Arm order is deterministically randomized from the frozen corpus hash. During
scoring, outputs are normalized to anonymous labels and stripped of module
names, arm labels, conversation identifiers, and formatting artifacts that
would reveal treatment status.

No arm sees the other arm's response. No score or reviewer feedback is returned
to either generation chat.

## 9. Scoring and Acceptance

### 9.1 Critical hard gates

Any of the following is a critical failure and an automatic loss for that case:

- inventing ownership, stock, dilution, ExactStockRef, or physical addition;
- collapsing target/ideal and current-inventory build formulas;
- changing target identity to fit inventory or a numerical score;
- using an unbound, monomolecular-natural, or otherwise unauthorized OAV claim;
- presenting physical liking, similarity, stability, measured headspace,
  sensory outcome, safety, or release status as tested without evidence;
- silently resolving conflicting sources;
- importing or treating quarantined package content as admitted authority;
- omitting a required missing-chemical impact gate; or
- citing evidence that does not support the claim made.

### 9.2 One-hundred-point rubric

Noncritical responses are scored on a frozen rubric:

| Dimension | Points |
|---|---:|
| Target identity and functional architecture | 25 |
| Factual accuracy, provenance, and authority calibration | 25 |
| Missing-chemical impact and target/build separation | 15 |
| Controlled-test quality and discriminability | 15 |
| Uncertainty, abstention, and conflict handling | 10 |
| Actionability and concise communication | 10 |

The rubric does not contain a beauty, prestige, novelty, price, formula-frequency,
or supplier-description score. Physical pleasantness remains `NOT TESTED` unless
real sensory evidence exists.

### 9.3 Ensemble pass threshold

The treatment is an outperformer only when all conditions hold:

1. it wins at least 12 of the 16 paired cases;
2. its median paired score improvement is at least five points;
3. it introduces zero critical failures not present in the control;
4. no category has a median regression greater than two points; and
5. all exact-input, isolation, blinding, and accounting checks pass.

Provider input/output tokens, elapsed time, and price are reported separately
from quality. If the quality threshold passes but median provider cost exceeds
the control by more than 100 percent, the result is
`QUALITY_OUTPERFORMER_COST_REVIEW_REQUIRED`; the ensemble is not activated until
the module bundle is compressed and rerun on the four most expensive cases.
Missing product-level token or price telemetry is reported as `NOT EXPOSED` and
is never estimated from unrelated process-wide totals.

If the treatment wins 9-11 cases or has a median improvement from two through
four points, the result is `INCONCLUSIVE`. Only the disputed cases are repeated,
once, under fresh clean xhigh contexts using the same frozen bytes. Any other
failure is `NO_DEMONSTRATED_OUTPERFORMANCE`.

## 10. Relevance-Gated Ablation

Ablation begins only after the full ensemble passes. Each native family is
tested only on frozen cases whose predeclared relevance map says the family
should contribute. A module that has no relevant case receives
`NOT_EVALUATED_NO_RELEVANT_CASE`; lack of invocation is not evidence of failure.

For each family, compare the full ensemble against the same ensemble with that
family omitted. Retain the family when at least one role-specific condition is
met without a new critical regression:

- median gain of at least three points across relevant cases;
- paired win in at least 60 percent of relevant cases; or
- prevention of at least one critical hard-gate failure.

Mandatory guardrails may satisfy only the third condition. Capability modules
must satisfy the first or second condition.

## 11. Repair and Retirement

An underperforming family receives one bounded repair cycle:

1. identify the exact failure class from blinded scores and deterministic gate
   output;
2. change only the responsible module or adapter contract;
3. preserve the frozen benchmark corpus and rubric;
4. rerun focused local tests;
5. rerun only the relevant frozen ablation cases; and
6. run four new holdout cases that were not available during repair.

The repair passes only if the module meets its role-specific retention
criterion on both the relevant frozen cases and the unseen holdouts without a
critical regression.

A persistent failure is handled archive-first:

- set registry state to `RETIRED_BENCHMARK_UNDERPERFORMER`;
- remove it from the active ensemble;
- record the exact reason, hashes, cases, scores, repair diff, and holdout result;
- preserve source bytes, tests, provenance, and external-package ancestry;
- verify that unrelated consumers remain intact; and
- delete nothing irreversibly without a separate exact-path authorization.

An external package that was never admitted is not retired as native code; it
remains `EVIDENCE_ONLY_NOT_ADMITTED`.

## 12. Data Flow

```text
module census + exact hashes
            |
            v
frozen case packet ---> native eligibility/relevance selection
            |                         |
            |                         v
            |                 separated module bundle
            |                         |
            +------ control ----------+------ treatment
                     ChatGPT xhigh            ChatGPT xhigh
                           \                  /
                            anonymous outputs
                                   |
                 deterministic gates + blinded rubric
                                   |
                  ensemble decision and relevant ablations
                                   |
                  retain / repair once / retire and archive
                                   |
                     append-only benchmark receipt
```

## 13. Fail-Closed Behavior

The benchmark stops or holds when:

- ChatGPT xhigh identity or reasoning effort cannot be verified;
- clean context isolation cannot be established;
- a prompt, attachment, inventory, evidence, module, rubric, or case hash drifts;
- a model request has an ambiguous timeout or completion state;
- a duplicate nonce or paid submission is detected;
- the authoritative inventory sources conflict;
- a required module fails locally;
- an unclassified complexity candidate is discovered;
- blinded labels are exposed before scoring completes;
- a reviewer cannot distinguish evidence from unsupported inference; or
- current repository changes overlap a planned implementation path.

Ambiguous provider requests are looked up by stable identifier and are never
blindly retried. A readiness result or available capacity is not authorization
to duplicate paid work.

## 14. Planned Implementation Surfaces

The implementation plan may use these focused surfaces:

- `engine/perception/complexity_ensemble.py` for registry validation,
  eligibility, evaluation, and ablation;
- `configs/complexity/complexity_module_registry_v1.json` for explicit module
  descriptors, roles, states, paths, and hashes;
- an added `complexity-benchmark` operation in existing
  `scripts/pipeline_audit.py`, with no new pipeline script;
- `tests/test_complexity_ensemble.py` for census, classification, separation,
  fail-closed behavior, and ablation;
- `tests/test_complexity_xhigh_benchmark_contract.py` for corpus, prompt,
  blinding, scoring, threshold, accounting, and retirement contracts;
- `tests/fixtures/complexity_xhigh_cases_v1.json` and its SHA-256 sidecar for
  the frozen corpus;
- ignored `output/complexity_xhigh_benchmark/` for raw prompts, outputs,
  anonymized scoring packets, and local run reports; and
- one append-only `data/governance/` receipt after a completed benchmark or a
  blocked terminal state.

These are design targets, not authorization to overwrite overlapping user
changes. Before implementation, every path must be rechecked against the live
dirty tree. Any overlap is worked around or brought back for user direction.

## 15. Verification Strategy

### 15.1 Provider-free verification first

Before any external model call:

- registry census and hash validation pass;
- all discovered candidates are classified;
- module outputs remain separate and schema-valid;
- guardrails fail closed on adversarial fixtures;
- case corpus and rubric hashes are frozen;
- randomized arm order and anonymization replay deterministically;
- a mock xhigh runner proves exact request, nonce, output, and ambiguity
  handling without network traffic;
- focused lint, type, compilation, and tests pass; and
- repository quick verification is run with pre-existing failures reported
  separately from benchmark changes.

### 15.2 External execution gate

Before any DeepLuna Chat provider transmission, run a fresh exact-project
health and accounting check for `perfume-chem-cheapluna-isolated` and continue
only when the active `cheapluna-chat / DIRECT_PRO / NO_LUNA` route is `READY`
with settled reservations. Any bounded worker evidence is advisory and must be
verified locally by Sol.

The user-requested ChatGPT xhigh runs are benchmark observations, not a worker
fallback and not implementation or scientific authority. They require the
separate clean-xhigh execution receipt described above.

### 15.3 Completion evidence

Completion requires:

- exact current module and corpus hashes;
- focused tests passing;
- no new relevant lint, type, or compilation failures;
- exact control and treatment request/response receipts;
- blinded per-case scores and critical-gate decisions;
- aggregate threshold computation;
- relevant ablation results;
- any repair and unseen-holdout evidence;
- active registry state after retain/retire decisions;
- an append-only governance receipt; and
- a truthful statement that software/model benchmarking creates no physical,
  sensory, safety, or release authority.

## 16. Rollback and Preservation

Before implementation edits, exact parent bytes for every touched tracked or
untracked path will be archived in a path-preserving rollback bundle and
verified by SHA-256. The approved design document remains immutable except by a
new reviewed revision.

Retiring a module is recoverable: restore its prior registry state and exact
source bytes, then rerun the same admission and benchmark gates. Raw external
packages remain quarantined and are never reconstructed from prose.

## 17. Acceptance Criteria

The project is complete only when:

1. every discovered complexity module or package is classified;
2. the admitted native ensemble is integrated through one library contract;
3. the 16-case corpus is frozen before xhigh execution;
4. plain xhigh and treatment run with verified identical settings and clean
   isolated contexts;
5. the ensemble decision follows the fixed threshold without post-hoc rubric
   changes;
6. relevant native families receive an ablation decision;
7. underperformers receive no more than one repair cycle and four unseen
   holdouts;
8. persistent underperformers are disabled and archived with exact receipts;
9. no unknown-rights package code is installed;
10. no duplicate paid work occurs;
11. all changed paths and benchmark artifacts have exact provenance; and
12. Sol performs final local acceptance while all scientific and release
    authority limits remain explicit.
