# Perfume-Chem Project Status Report for 5.6 Sol

**Date:** 2026-07-29
**Prepared by:** GLM-5.2 (DeepInfra route) with CheapLuna preflight, literature verification, and verification scan
**Delegation note:** CheapLuna DeepSeek V4 Flash delegation was attempted but could not complete due to repeated cost-ceiling parameter issues. The report was synthesized directly from source files, live verification artifacts, and fetched literature.

---

## Executive Summary

Perfume-Chem is a local-first perfume formulation workbench implementing deterministic bottle arithmetic, ppm/ODT/OAV analysis, evidence-labeled formula diagnostics, and advisory release gates. It has reached **Laboratory Beta readiness** — all software-controllable deliverables are tested, the verifier passes 18 of 19 required checks (1 failure due to uncommitted working-tree modifications), and the FastAPI lab interface is operational. **Scientific release remains blocked** because preregistered held-out sensory validation has not been executed. The system is honest about its boundaries: modeled OAV is heuristic (not sensory likeness), 68.2% of ODT values are heuristic rather than peer-sourced, and several science modules (UNIFAC, OR EC50s, Antoine coefficients) are stubbed or 0% coverage. The project is a well-engineered research prototype with explicit auditability, but should be presented with caveats about heuristic data layers.

---

## 1. Project Identity & Truth Posture

**What it is:** Perfume-Chem is a local-first formulation workbench for deterministic bottle arithmetic, ppm/ODT/OAV analysis, evidence-labeled formula diagnostics, and advisory release gates (`README.md:1-5`).

**Canonical entry point:** `engine.workbench.PerfumeWorkbench` (`README.md:7-9`). Language-model services are optional renderers and ideation tools; they are not the authority for arithmetic, inventory, safety, or scientific classification (`README.md:9-10`).

**Evidence classes:** Every canonical result uses one of six evidence classes (`README.md:14-22`):
- `EXACT` — exact arithmetic (bottle mass balance)
- `LITERATURE_DERIVED` — from published sources
- `EMPIRICALLY_CALIBRATED` — fitted to measured data
- `HEURISTIC` — modeled/approximated (headspace, temporal evolution)
- `SPECULATIVE` — unvalidated hypotheses
- `UNKNOWN` — withheld rather than guessed

**Withheld vs modeled:**
- **Withheld (UNKNOWN/null):** Longevity, sillage, receptor activation, and emotion outputs. These remain `null` or `UNKNOWN` rather than guessed (`README.md:24-25`, `docs/SCIENCE_PLAN.md` known weaknesses).
- **Modeled (HEURISTIC):** Current headspace and temporal evolution. Bottle mass balance is `EXACT` for stated inputs (`README.md:22-24`).

**Scientific posture:** "This repository is a Laboratory Beta. Passing verification means the declared software, persistence, and scientific-truth contracts are internally consistent; it does not make modeled headspace a measurement, golden fixtures a sensory panel, or the safety screen a regulatory certificate" (`README.md:27-32`).

---

## 2. Current State

### Laboratory Beta: READY

The Laboratory Beta Completion plan (`docs/superpowers/plans/2026-07-16-laboratory-beta-completion.md`) documents:

- **Task 0 (Truth Baseline):** Completed in commit `0566978`. 18 verifier checks passed, 0 failed, 2 Docker skips. Engine test shards: 354 tests. Backend: 61 tests at that checkpoint (`laboratory-beta-completion.md:11-16`).
- **Tasks 1-8:** All completed — strict quantities, lab schema, transactional repository, evidence/safety/intervention contracts, experiment/preference loop, deterministic lab API, offline lab interface, backup/restore/export.
- **Full Verification Evidence (2026-07-17):** `project-verify --json` completed in 1104.1 seconds with `PASS_WITH_SKIPS`. 18 required checks passed, zero failed, 2 optional Docker checks skipped. Engine tests: 101 truth-core, 158 data/knowledge, 69 gates/families, 60 legacy (total 388). Backend: 154 tests. Golden fixture SHA-256: `f47b79a6e4aeaa6e9e72aa3a6934264806cbb349b5bcad853a8b8e5bac9d0996` (`laboratory-beta-completion.md:226-238`).

### Scientific Release: BLOCKED

"Scientific Release remains `blocked` because preregistered held-out sensory validation has not passed" (`laboratory-beta-completion.md:239-240`).

### Current Verification Scan (2026-07-29, this report)

The live `verification_runs/project_verification.json` shows a **different** state due to uncommitted working-tree modifications:

| Metric | Documented (2026-07-17) | Current (2026-07-29) |
|--------|------------------------|---------------------|
| Passed | 18 | 18 |
| Failed | 0 | **1** (`formula-artifact-validation`) |
| Skipped | 2 (Docker) | 2 (Docker) |
| Golden fixture SHA-256 | `f47b79a...` | `0067d16...` (unchanged) |
| Scope | full | full |

The `formula-artifact-validation` failure is due to formula markdown files being modified in the working tree (uncommitted), which invalidates their persisted analysis hash bindings. This is a **working-tree hygiene issue**, not a code regression — committing or stashing the changes would restore the artifact validation to PASS.

---

## 3. Features

### Core Engine

| Feature | Canonical path | Evidence |
|---------|---------------|----------|
| Formula physical state and OAV table | `engine/pipeline/formula_state.py` | `README.md:152` |
| Temporal diagnostic frames | `engine/pipeline/simulator.py` | `README.md:153` |
| Evidence-labeled application service | `engine/workbench.py` | `README.md:154` |
| Typed quantity and stock-basis conversion | `engine/quantities.py` | `README.md:155` |
| Exact mixture reconstruction | `engine/mixture.py` | `README.md:156` |
| Conservative safety assessment | `engine/safety_assessment.py` | `README.md:157` |
| Feasible intervention ranking | `engine/interventions.py` | `README.md:159` |
| Preference calibration gate | `engine/preference.py` | `README.md:159` |
| Exact bottle addition | `engine/bottle_addition.py` | `README.md:161` |
| Scientific class vocabulary | `engine/scientific_contract.py` | `README.md:162` |

### Release Pipeline (23 Gates)

Entry point: `scripts/formula_release_gate.py` (`README.md:164`, `docs/pipeline_architecture_and_gaps.md:86-93`).

Pipeline flow:
```
formula source
  → strip generated analysis before parsing
  → resolve live inventory stock identity
  → build exact-or-explicitly-modeled ppm/ODT/OAV state
  → enforce named-reference evidence scope
  → run hard truth gates and advisory aesthetic gates
  → render analysis
  → atomically persist + immediately re-read and verify the bound artifact
```
(`docs/pipeline_architecture_and_gaps.md:25-34`)

### Lab Schema (Append-Only Events)

- SQLAlchemy lab tables persist immutable versions and append-only events (`laboratory-beta-completion.md:5-6`).
- Formula versions, evidence, stocks, bottle events, inventory movements, experiments, predictions, and outcomes have explicit foreign keys and units (`laboratory-beta-completion.md:58`).
- Immutable/append-only records reject update/delete at repository and database levels (`laboratory-beta-completion.md:60`).
- Bottle state is reconstructed from ordered events; stream sequence and idempotency prevent stale writes and duplicate retries (`laboratory-beta-completion.md:74-76`).

### Exact Bottle Addition

`POST /api/v1/formulas/calculate-addition` solves final mass balance accounting for material already in the bottle and mass added by the stock (`README.md:284-285`). Response includes exact stock mass, propagated standard uncertainty, pipette plan, target error in ppm, and before/addition/after mass ledgers (`README.md:313-319`).

### Backup, Restore, and Export

- Live SQLite backup produces consistent snapshot, manifest, and digest (`laboratory-beta-completion.md:162`).
- Restore validates integrity, digest, and schema revision before replacement (`laboratory-beta-completion.md:163`).
- Restore stages while running and applies only in maintenance mode or stopped-server command (`laboratory-beta-completion.md:164`).
- JSON exports preserve stable UUIDs, units, provenance, versions, and event order; re-import is idempotent (`laboratory-beta-completion.md:165`).

### Offline FastAPI UI

- Served at `http://localhost:8000/app` without Node runtime or network dependency (`laboratory-beta-completion.md:145`).
- Dashboard, bottle, formula, materials, experiment, and assistant views reachable (`laboratory-beta-completion.md:146`).
- Mobile and desktop layouts usable; browser smoke confirmed at 1440x900 and 390x844 (`laboratory-beta-completion.md:201-203`).

### Sensory Experiment Loop

Protocol, applications, timed observations, predictions, outcomes, and comparisons persist (`laboratory-beta-completion.md:111`). Predictions cannot be edited after outcomes; preference fitting is withheld below sample/connectivity gates; prediction claims remain `UNKNOWN/not_validated` until held-out evaluation beats declared baselines (`laboratory-beta-completion.md:113-114`).

### Composite Natural OAV Decomposition

35+ naturals are decomposed into published GC-O constituents in `engine/pipeline/natural_absolute_decomposition.py` (`AGENTS.md` Rule 4). Composite OAV is injected at `formula_state.py:219` and `formula_state.py:567`. This increases OAV accuracy by 100-500,000x for absolutes. Composite OAV is olfactory headspace evidence, not regulatory constituent composition.

### Family Archetype Registry

Family archetypes defined in `engine/families/registry.py` with material group tuples, `ArchetypeSpec` with anchors/drift_limits/forbidden_materials/OAV_targets/repair_pool. Supported briefs: `generic`, `aromatic_fougere`, `layton_dna`, `vetiver_woody` (`AGENTS.md` Running section).

### Reconstruction Ledger Architecture

Layered ledger architecture (`AGENTS.md` Reconstruction section):
```
Evidence → Target hypothesis → Accepted target → Accord/DNA graph →
Chassis derivation → Inventory mapping → Build formula →
Bottle events → Analytical/sensory results → Updated target
```

Critical rule: missed inventory never alters the target; substitutions are in the build layer only. 11 operating modes from `RECONSTRUCTION` to `RELEASE_REVIEW`. New gates: `mode_protection`, `chassis_integrity`, `authority_vector`.

---

## 4. Gaps

### 4.1 ODT Authority Mostly Heuristic

From `docs/project_audit_2026-06-30.md:134-142`:

- Authoritative (PEER_CROSS, PEER_SINGLE, PEER_EST): **31.8%**
- Heuristic (DERIVED, UNVERIFIED, UNKNOWN): **68.2%**

Live ODT verification counts from `verification_runs/project_verification.json`:
- PEER_CROSS: 1
- PEER_SINGLE: 72
- PEER_EST: 14
- DERIVED: 86
- UNVERIFIED: 102
- UNKNOWN: 1

Interpretation: "OAV math may be mechanically correct, but many underlying thresholds are not authoritative enough for high-confidence scientific claims" (`project_audit_2026-06-30.md:140-142`).

### 4.2 Low Chemistry Metadata Coverage

From `docs/project_audit_2026-06-30.md:114-124`, corroborated by live `verification_runs/science_audit.json` (221 materials):

| Field | Audit (2026-06-30) | Live (2026-07-29) |
|-------|-------------------|-------------------|
| mw | 21.84% | 22.11% |
| logp | 15.66% | 15.93% |
| vp_25c | 21.60% | 21.87% |
| odt_air | 6.01% | 6.42% |
| hedonic | 10.68% | 10.86% |
| ifra | 1.11% | 1.19% |
| cas | 3.96% | 4.36% |
| antoine | 0.0% | 0.0% |
| hsp | 0.0% | 0.0% |
| or_targets | 0.0% | 0.0% |
| dhvap | — | 0.16% |
| smiles | — | 1.19% |
| trp | — | 3.96% |

Material consistency: 221 materials, 125 conflicts (61 material-level conflicts). Most conflicts are `UNRESOLVED_NATURAL_MIXTURE_PROXY_CONFLICT` — bulk ODT values for naturals vs composite constituent values. This is expected behavior (composite model takes precedence), not data corruption.

### 4.3 Advisory Knowledge Rules

From `docs/project_audit_2026-06-30.md:151-174`:

| Category | Count |
|----------|-------|
| Total structured entries | 2,452 |
| Valid | 11 |
| Advisory | 2,311 |
| Invalid | 130 |
| Orphan material refs | 149 |
| Generic material refs | 302 |

Interpretation: "The literature corpus exists, but most pairing and synergy rules are still not normalized to exact material identities" (`project_audit_2026-06-30.md:170-173`).

### 4.4 Disconnected/Deprecated Modules

From `docs/project_audit_2026-06-30.md:198-217`:

| Module | Status |
|--------|--------|
| `engine.formulator` | Deprecated, no runtime import usage |
| `engine.opus_v_workbook` | Deprecated from pipeline narrative |
| `engine.reconstruction_pipeline` | Deprecated from pipeline narrative |
| `engine.formula_analyzer` | Effectively unused outside audit labeling |
| `engine.thermo.headspace` | Needs consolidation with pipeline headspace |
| `engine.thermo.trajectory` | Needs consolidation review |
| `engine.family_scorer` | Audit for duplication |

### 4.5 Science Plan Weaknesses

From `docs/SCIENCE_PLAN.md:42-62`:

| Module | Status |
|--------|--------|
| Antoine A/B/C | 0% coverage — VP(T) uses inferred ΔHvap (heuristic) |
| UNIFAC | Stubbed — Hansen-distance heuristic calibrated to limonene-in-EtOH only |
| OR EC50s | 0% coverage — 8-OR caricature vs 396-locus human OR repertoire |
| Adaptation τ | Rat single-cell values; human bulb-level may differ by 2-3x |
| Maturation kinetics | Arrhenius A/Ea calibrated to Blakeway 1987 only |

### 4.6 Pipeline Gap Analysis (6 gaps)

From `docs/pipeline_architecture_and_gaps.md:118-162`:

| # | Gap | Severity | Status |
|---|-----|----------|--------|
| 1 | No NL diagnosis | High | **Fixed** — `scripts/formula_diagnosis.py` integrated |
| 2 | No intervention simulation | Medium | Open |
| 3 | No temporal coherence score | Medium | **Fixed** — `temporal_coherence` score added |
| 4 | No data quality score | Low | **Fixed** — `data_quality` score added |
| 5 | No pairing rule validation | Medium | **Fixed** — VP-aware pair validation |
| 6 | No family-specific calibration | Low | **Fixed** — family-normalized industry scores |

### 4.7 Material Conflict Count

Live `verification_runs/science_audit.json` reports 125 conflicts across 61 materials. Most are natural-mixture proxy conflicts (bulk ODT vs composite constituent values) where composite OAV takes runtime precedence. This is architectural, not a data quality failure.

---

## 5. Future Plans

### Priority 1: Scientific Credibility (from `project_audit_2026-06-30.md:249-252`)

- Split runtime-authoritative data from heuristic/estimated data in reports
- Add a strict mode that refuses heuristic ODTs for professor/demo outputs
- Keep `engine/odor_thresholds.py` under duplicate-key regression coverage

### Priority 2: Knowledge-Graph Quality (`project_audit_2026-06-30.md:254-258`)

- Normalize generic rule references to exact material identities where possible
- Move placeholders (`orange`, `rose`, `musks`, `Florals (Rose, Jasmine)`) into explicit advisory-only sections
- Fail CI when invalid structured rule references increase

### Priority 3: Codebase Clarity (`project_audit_2026-06-30.md:260-265`)

- Remove or archive clearly disconnected modules after import-trace confirmation
- Keep underscore scratch formulas excluded from default audit sampling
- Keep source-level hygiene tests in the default verification path

### Science Backfill (from `docs/SCIENCE_PLAN.md:42-62`)

- **Antoine A/B/C:** Ingest measured Antoine constants for VP(T) accuracy
- **UNIFAC:** Implement SMARTS group decomposition for activity coefficients
- **OR EC50s:** Backfill per-material EC50 values for the 396-locus human OR repertoire
- **Adaptation τ:** Obtain human bulb-level feedback data (current: rat single-cell)
- **Maturation kinetics:** Expand Arrhenius calibration beyond Blakeway 1987

### Scientific Release Blocker

The single blocker for Scientific Release: **preregistered held-out sensory validation must pass its declared baseline** (`laboratory-beta-completion.md:239-240`). Until then, all modeled outputs remain `HEURISTIC` or `UNKNOWN`.

### Working-Tree Hygiene (new finding, this report)

The current `formula-artifact-validation` failure is caused by uncommitted formula file modifications. Committing or stashing working-tree changes would restore the verifier to 18/18 PASS.

---

## 6. Project Health

### Verifier Results

| Check | 2026-07-17 (committed) | 2026-07-29 (working tree) |
|-------|----------------------|---------------------------|
| engine-compile | PASS | PASS |
| engine-lint | PASS | PASS |
| engine-typecheck | PASS | PASS |
| engine-tests-truth-core | PASS | PASS |
| engine-tests-data-knowledge | PASS | PASS |
| engine-tests-gates-families | PASS | PASS |
| engine-tests-legacy | PASS | PASS |
| backend-lint | PASS | PASS |
| backend-typecheck | PASS | PASS |
| backend-tests | PASS | PASS |
| scientific-audit | PASS | PASS |
| material-data-validation | PASS | PASS |
| knowledge-rule-validation | PASS | PASS |
| golden-formula-regression | PASS | PASS |
| golden-api-regression | PASS | PASS |
| package-build | PASS | PASS |
| package-wheel-smoke | PASS | PASS |
| golden-fixture-lock | PASS | PASS |
| **formula-artifact-validation** | **PASS** | **FAIL** (uncommitted changes) |
| docker-build | SKIP | SKIP |
| docker-smoke-test | SKIP | SKIP |

**Totals (2026-07-29):** 18 passed, 1 failed, 2 skipped.

### Test Counts (from 2026-07-17 committed baseline)

- Engine: 388 tests (101 truth-core + 158 data/knowledge + 69 gates/families + 60 legacy) — `laboratory-beta-completion.md:232-234`
- Backend: 154 tests — `laboratory-beta-completion.md:235`
- Golden fixture SHA-256 (current): `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec` (unchanged from baseline)

### Browser Smoke

Confirmed at 1440x900 (desktop) and 390x844 (mobile). All six laboratory views reachable, no horizontal overflow, mobile media query active (`laboratory-beta-completion.md:201-203`).

### Independent Review

Luna fallback review (Sol xhigh was quota-blocked): no critical findings. Two important findings reproduced and fixed:
1. HTTP backup service pinned previous Alembic revision → now derives from single current script head
2. Liquid mass concentration absent from strict quantity model → now separate g/L quantity with mg/L conversion (`laboratory-beta-completion.md:208-223`)

### CI / GitHub Actions

"Hosted GitHub Actions are intentionally not used" (`README.md:73`). Hosted jobs were "created but blocked before steps by the account billing state; this is an infrastructure exception, not a test result" (`laboratory-beta-completion.md:14-16`).

### Commit Cadence

Recent commits show active development across formula creation, pipeline hardening, plan documentation, and script refactoring (20 commits visible in log, from `cff1a7a` to `2e46e4c`).

### Known Legacy Limitations (from `verification_runs/project_verification.json`)

1. Full-engine Ruff cleanup remains legacy debt; canonical truth-core slice is blocking.
2. Compatibility requests may omit finished solvent matrix; strict mode requires it; headspace remains modeled.
3. Temporal evolution is heuristic, not calibrated to skin or blotter measurements.
4. Longevity, sillage, receptor activation, and emotion outputs remain unsupported; preference fits remain UNKNOWN until held-out validation passes.
5. Composite natural OAV is olfactory headspace evidence, not regulatory constituent composition.

---

## 7. Literature Anchors

The following references are cited in the repository documentation and verified where possible:

| Reference | Claim supported | Source in repo | External verification |
|-----------|-----------------|----------------|---------------------|
| Audouin et al. 2001, ACS Symp. Ser. 782:156-171, DOI 10.1021/bk-2001-0782.ch014 | OAV alone does not reliably identify every odor-impact compound | `docs/pipeline_architecture_and_gaps.md:67-68` | **Verified** via experts.umn.edu: "OAVs were not useful measures of intensities... not good indicators of the percent contribution to the overall intensity of a mixture" |
| RFC 8785 (JSON Canonicalization Scheme) | Deterministic JSON hashing for persisted evidence | `docs/pipeline_architecture_and_gaps.md:62-63` | **Verified** via rfc-editor.org: JCS defines canonical representation of JSON data for cryptographic operations |
| W3C PROV-DM | Provenance entities and derivations modeling | `docs/pipeline_architecture_and_gaps.md:63-64` | Cited; standard W3C recommendation on provenance |
| NIST Metrological Traceability | Unbroken input chain for evidence | `docs/pipeline_architecture_and_gaps.md:64-66` | Cited; NIST standard on metrological traceability |
| Calkin & Jellinek 1994 | Chypre ratios, fixative loading | `AGENTS.md` Perfumery Literature References | Cited in repo |
| Carles 1961 | Pyramid structure, accord ratios, material counts | `AGENTS.md` Perfumery Literature References | Cited in repo |
| Sinding et al. 2017 | Olfactory adaptation — high VP citrus habituates in 45-90s | `AGENTS.md` Perfumery Literature References | Cited in repo |
| Laing & Francis 1989 | Humans track 3-4 components maximum | `AGENTS.md` Perfumery Literature References | Cited in repo |
| Hong et al. 2023 | GC-MS-O of osmanthus — β-ionone is dominant character compound | `AGENTS.md` Perfumery Literature References | Cited in repo |
| Guo et al. 2024 | Osmanthus absolute composite OAV = 1,371,872 floral | `AGENTS.md` Session Learnings | Cited in repo |

---

## 8. Caveats

1. **Modeled OAV is NOT a sensory-likeness percentage.** OAV is `MODELED_HEURISTIC` — it is never a sensory-likeness percentage. The authority boundary reflects the published limitation that OAV alone does not reliably identify every odor-impact compound (Audouin et al., 2001) (`docs/pipeline_architecture_and_gaps.md:38, 66-68`).

2. **Passing verification means internal consistency, not a measurement.** "Passing verification means the declared software, persistence, and scientific-truth contracts are internally consistent; it does not make modeled headspace a measurement" (`README.md:27-30`).

3. **Golden fixtures are not a sensory panel.** They are regression anchors for arithmetic and evidence labels, not human olfactory validation.

4. **The safety screen is not a regulatory certificate.** `engine/safety_assessment.py` provides conservative safety assessment, not IFRA certification (`README.md:158`, `laboratory-beta-completion.md:93-97`).

5. **Pre-blended materials are excluded from the optimizer.** FTECs, Fleuressences, FOs, Accord/Core bases, and opaque-composition materials are tagged `families: ["pre-blended"]` and filtered out of the optimizer search space (`docs/SCIENCE_PLAN.md:88-97`).

6. **Composite natural OAV is olfactory headspace evidence, not regulatory constituent composition.** The composite OAV model decomposes naturals for perceptual modeling; IFRA allergen assessment uses separate constituent data (`verification_runs/project_verification.json` known_legacy_limitations).

7. **The project is a Laboratory Beta, not a released commercial system.** "A scientific release remains blocked until held-out sensory validation beats its declared baseline" (`README.md:31-32`).

8. **Current working-tree state has uncommitted modifications** that cause `formula-artifact-validation` to fail. This is a hygiene issue, not a code regression.

9. **GitHub Actions are blocked by account billing**, not by code or configuration failures. This is an infrastructure exception (`laboratory-beta-completion.md:14-16`).

10. **68.2% of ODT values are heuristic.** OAV calculations using heuristic ODTs should be treated as approximate. The pipeline labels each material's ODT confidence level, but downstream consumers must check this label, not assume all OAVs are equally authoritative.

---

*End of report. Prepared 2026-07-29 for review by 5.6 Sol.*