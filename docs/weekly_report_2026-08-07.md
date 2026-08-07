# Weekly Project Report — Perfume-Chem (Aug 3–7, 2026)

## Reproducibility header

| Field | Value |
|---|---|
| Report generation timestamp (UTC) | `2026-08-06T17:47:35Z` |
| Repository root | `D:\chatbots\perfume-chem` |
| Branch | `codex/add-inventory-materials` |
| Starting commit SHA (oldest in window) | `9f14fe923625a076030e5253b0d35a8b1a108efa` |
| Ending / current HEAD SHA | `783931799ae1558c5e35356c91ffbf3d9ef91042` |
| Commit count (window since 2026-08-01) | **108** |
| Exact git-log command used | `git log --since="2026-08-01 00:00:00" --pretty=format:"%h\|%ad\|%an\|%s" --date=short` (108 lines) |
| Dirty / clean state | **DIRTY** — `git status --short` reports 358 modified/untracked lines |
| `git status --short` snapshot hash (SHA-256 of UTF-8 joined output) | `40a13bb047dd304decf6b043b1b2824a2d603a55e4435490c76ee8a06746979c` |
| Authoring model / runtime identity | `deepseek/deepseek-v4-flash` via OpenCode; OS `win32`; shell PowerShell 5.1 |

> Reproducibility note: the commit window is defined by the exact `git log` command above
> (commits dated on/after `2026-08-01`). Run-time run-directory work under `runs/` is
> **gitignored** and therefore not reflected in any git-based count; it is itemized in
> Section 2 below.

## 1. Committed engineering work — "Scientific Contract / Build C" series
**108 commits this week**, by the Codex agent (Aug 1–3), a locked TDD loop building the
project's scientific claim and evidence authority layer:

| Commit theme | What was built |
|---|---|
| **c3** model-interface gate | model-interface boundary + gate evidence |
| **c4** equilibrium model gate | ideal-equilibrium baseline implementation; **COSMO-RS withholding reconciled** (kept out of gate authority) |
| **c5** calibration program | fail-closed calibration program, frozen contract |
| **c6** dynamic release | conservative dynamic-release model + substrate-release selectors |
| **c7** natural-lot authority | lot-aware natural contracts (unresolved-disclosure guard) |
| **c8** headspace OAV authority | headspace OAV physics authority contracts + sealed evidence |
| **c9** unsupported-science quarantine | fail-closed triage for unsupported science; C9 shelf-life quarantine reconciled |
| **c10** constrained experiment selection | Pareto-observable constrained selection + canonical evidence blobs |
| **c11** Build C evidence tree | aggregate evidence package, final evidence-binding contract, sealed boundary |
| **d0** scientific claim matrix | immutable claim contracts, method-authority registry, first confirmatory claim, claim gate bound into project verification |

Each gate carries the pattern: *define boundary → freeze contract → implement → bind evidence
→ record decision → seal*, with exact-replay decisions recorded for C7/C8.

## 2. Program / run-directory work (Aug 5–7) — audit lanes
These are **uncommitted** (`runs/` is gitignored) but are the week's main deliverables.

### a) CP6-20260805 — Counterbrand Formula Estate Audit (Phase AB + D/E/F)
- Corrective-Plan v6 approval packet + prequalification snapshot, both **hash-verified at
  execution time** (not inherited from the plan).
- **DEF-guard v2** (scoped E2 write + packaging exceptions, 5-way trust-anchor agreement,
  config lock v4).
- **Native path-boundary hardening** (reparse-point policy, traversal classification
  corrected; symlink noted as not empirically exercised).
- Phase D/E/F task graph: 26 nodes = 3 COMPLETE / 5 READY / 18 NOT STARTED (balanced);
  D/E/F run independently; **Phase G NOT authorized**.
- External receipts + checkpoint repair/immutability ledger (reissued hashes).

### b) Prada_LHomme_C1_Program_Merge_20260806 — **PARTIAL PROGRAM MERGE**
- Governing formula PLH-CURRENT-EDT-INV-C1-20260806 (44 rows, 1000 parts, **UNCHANGED**,
  "computational reconstruction candidate / pending physical smell test / not empirically
  verified / not released").
- Fixed core C1 = 952 parts, integrity **PASS across all 7 executable arms** (40 rows;
  excluded Beta Ionone 28 / Alpha Irone 8 / Nympheal 8 / Florol 4).
- Experimental program: eligible arms VF-BASE, IR-C1, FL-1, VIO-1; blocked arms:
  - **FL-2 remains BLOCKED pending resolution of a stock-state conflict.** The Prada merge
    recorded Hydroxycitronellal as DEPLETED, while Inventory Master v3 and the estate-audit
    diagnosis indicate it is available neat/as supplied. Do not resolve this silently.
    Record **INVENTORY CONFLICT / HOLD** until the latest terminal report and the exact
    Inventory Master v3 row are reconciled.
  - VIO-FL-1 (independent parent benefit required).
- Declaration-conflict audit, variant registry, synchronization changeset/diff,
  adjudication + validation reports, sealed merged bundle.

### c) delegation_opt — delegation fast-path optimization
- **Drain-as-complete delegation validated**: 8-job wave, each job processed the moment its
  worker returned (not batch-end); repeat wave **$0.00 (100% cache)**; zero failures/retries.
- Metrics: 3,462 ms cold → 2,988 ms repeat; cost $0.00027 cold → $0.00 repeat.
- Delivered `cheapluna-drain.mjs` (per-job concurrent pollers, run registry, event +
  transmission ledgers, CLI budget/cache enforcement). **Boundary: Cheapluna stays
  advisory-only for canonical content.**

### d) Floral_Coverage FC-1 (Readiness + Reconciliation) — the floral lane
- **FC-1 external validation**: authorized Floral Coverage Foundation v1 package verified by
  SHA (`f3bbb4f3…`, 132,790 B) — 39/39 members, 12 slots, 9 families, 27 branches,
  10/10 tests, CLI PASS. Honest terminal: **FC-1 VALIDATED / ESTATE INPUT HOLD** (5
  counterbrand canonical upstream artifacts absent; no second truth path).
- **FC-1 reconciliation** (three immutable strata: external bundle / local run /
  reconciliation): bundle re-verified (`e106030d…`); **honest divergence finding — the
  earlier "15/15 identical" claim was NOT reproduced; the current reconciliation found 12
  shared files that are all content-divergent** (bundle carries the fuller amendment schema;
  local files are the simpler earlier run), plus 11 bundle-only and 2 local-only members.
  This is exactly why the reconciliation preserves historical, local, and current strata
  separately. Historical graph preserved (12 = 9 COMPLETE + 2 HOLD + 1 BLOCKED); recon graph
  derived (12 = 12 COMPLETE); resume gate **CLOSED** (0/5 artifacts).
- **Cheapluna Chat debugged**: wedged project daemon (pipe `ENOENT`) diagnosed → recycled →
  **READY**; fail-closed schema fixes (`citations_required_for`, `required_output`,
  `definition_of_done`, read range); one **bounded advisory query executed**
  (`deepseek-v4-flash`, 1 call, ~$0.00088) → **BLOCKED/UNRESOLVED** (scope_deviation);
  advisory queue materialized EMPTY, `canonical_claims_added: 0`. Recon bundle sealed
  (`29f9be17…`).

## 3. Working-tree state (uncommitted, broad)
Substantial uncommitted changes across `engine/` (allergen_solver, chemical_life_graph,
pipeline/preflight), `backend/` (config, tracing, AI factories, lab schemas/API),
`data/` (material YAMLs A/B/C/D/J/S/V, material_properties.json, audit_flags),
`docs/` (SCIENCE_PLAN, scientific_contract, model_inventory), plus `AGENTS.md`,
`.opencode/` plugins, and `_generate_material_properties.py`. These belong to the ongoing
audit/program work and are not yet committed.

## 4. Governance / process
- AGENTS.md updated (Rule 0 inventory-first, Rule 1 ppm/ODT/OAV, Rule 2 no new pipeline
  scripts, Rule 3 name-first optimization, Rule 4 composite OAV for naturals).
- Consistent discipline throughout: every gate = define → freeze → implement → evidence →
  seal; external receipts and non-self-referential manifests + external SHA on all program
  bundles; Phases G never authorized; no formula authority, no empirical promotion, physical
  test always required.

## Terminal-boundary

> This weekly report summarizes committed and run-directory work. It does not itself promote
> formula state, empirical state, scientific-release state, engine qualification, physical
> results, safety clearance, or Phase G authorization. Referenced manifests, receipts,
> terminal-state files, and exact source artifacts remain authoritative at their respective
> scopes.
