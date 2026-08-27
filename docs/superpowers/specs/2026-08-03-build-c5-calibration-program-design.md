# Build C5 calibration-program design

Status: accepted by Sol on 2026-08-03
Phase parent: `085512ec620fd5a8f192fc6298a6fa1acce2d7b0`
Authoritative requirement: `D:\.prompts\perfume chem\SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md`, C5.1-C5.7 and the C5 exit gate

## Decision

C5 adds a pure, immutable, fail-closed experimental-calibration contract under
`engine.physics`. It does not modify the legacy feedback calibration pipeline,
the standalone analytical ledger, the Build B5 database authority, production
callers, databases, migrations, generated artifacts, optimizers, or UI routes.

Repository and protected-database inspection found no actual GC-MS,
HS-SPME-GC-MS, chromatographic, calibration, or held-out measurement dataset.
The file named `output_cuir_obscur_gcms.json` is a failed formula release-gate
output, not instrument data. C5 therefore implements the protocol, schema,
strict importer, split lock, model/held-out lock, metric harness, and explicitly
simulation-only smoke tests. The empirical phase remains
`BLOCKED_PENDING_DATA`; no synthetic value is labeled calibration evidence.

Build B5 remains the only analytical authority. A real C5 observation must bind
one supported B5 method-validation-run-peak-claim chain, matching matrix,
analyte, and method calibration scope, preserved vendor raw data and open
export, blocking-QC clearance, measurement uncertainty, and exact digests.
Legacy `engine/calibration.py`, `engine/calibration/store.py`, and
`engine/analytical/ledger.py` are neither imported nor promoted.

## Representative material panel

The panel is pinned to the current `inventory.txt` SHA-256
`9d778721db1f5a0a10d1f278eeef9b7fab0bc73ce7f0d58b26c501be70fe0eb8`.
Every entry is an owned, parser-normalized inventory identity. Selection is by
domain coverage and decision value, not a target count.

| Inventory identity | Primary class | Coverage role | Stock constraint |
| --- | --- | --- | --- |
| D-Limonene | hydrocarbon/terpene | high volatility, low polarity, bulk top | neat |
| Linalool | alcohol | donor/acceptor, higher volatility | neat |
| Phenethyl Alcohol | alcohol | donor/acceptor, polar, lower volatility | neat |
| Citral | aldehyde | acceptor, volatile | neat |
| Aldehyde C10 | aldehyde | trace-potent stock | 1%, undeclared basis/carrier |
| Alpha Ionone | ketone/ionone | lower volatility, acceptor | neat |
| Raspberry Ketone | ketone | donor/acceptor, low volatility | neat |
| Linalyl Acetate | ester | acceptor, bulk top/heart | neat |
| Ethyl 2-Methylbutyrate | ester | very volatile trace-potent stock | 0.1%, undeclared basis/carrier |
| Gamma Decalactone | lactone | lower volatility, acceptor | neat |
| Eugenol | phenol | donor/acceptor, polar | neat |
| Myristic Acid Powder | acid | low-volatility feasibility/abstention control | neat solid; analytical feasibility unresolved |
| Galaxolide | musk | low volatility, bulk structural | 50% in DEP, undeclared fraction basis |
| Ambrettolide | musk/lactone | low volatility, macrocyclic | 10% in DPG, undeclared fraction basis |
| Iso E Super | woody amber | low polarity, bulk structural | neat |
| Ambermax | woody amber | low volatility, high-impact | 50%, undeclared basis/carrier |
| Hedione | ester/bulk structural | high-use heart material | neat |
| Damascenone | ketone | trace-potent | 1%, undeclared basis/carrier |
| Geosmin | alcohol | trace-potent, polar | 1% in TEC, undeclared fraction basis |

Unknown stock basis, carrier, or analytical feasibility remains a preparation
blocker. Panel membership never converts an undeclared stock into a neat or
quantitative source.

## Matrix panel

C5 freezes eight mass-fraction recipe templates. They are experimental design
targets, not evidence that a physical sample exists:

1. current declared stock, 100% of the inventory stock as held;
2. 10% finished-strength target: 10% concentrate, 82% ethanol 96%, 8% water;
3. 20% finished-strength target: 20% concentrate, 72% ethanol 96%, 8% water;
4. high-ethanol stock: 1% test material, 99% ethanol 96%;
5. DPG-heavy: 1% test material, 90% DPG, 9% ethanol 96%;
6. TEC-heavy: 1% test material, 90% TEC, 9% ethanol 96%;
7. DEP-heavy: 1% test material, 90% DEP, 9% ethanol 96%; and
8. IPM/oil: 1% test material, 90% IPM, 9% ethanol 96%.

Ethanol 96%, DPG, TEC, and IPM are normalized owned inventory records. DEP is
used in owned stocks but no standalone owned DEP row was found, so DEP-heavy is
`REQUIRES_DECLARED_SOURCE`. Water also requires a declared lot/source before
sample preparation. Exact sample preparation must additionally resolve every
stock fraction basis.

## Protocol and B5 binding

An executable protocol is immutable and records:

- sample mass and sample volume, with explicit units;
- vial and headspace volume;
- exact matrix recipe and batch identity;
- temperature and equilibration duration;
- extraction/sampling mode;
- SPME fiber identity, conditioning, and age/use count;
- agitation and desorption conditions;
- internal standard and calibration plan;
- blank design, carryover control, and QC plan;
- replicate count and identities;
- deterministic randomization algorithm and seed; and
- instrument-drift controls.

It binds exact B5 method-authority and validation IDs/hashes and the applicable
matrix-scope digest. Empty placeholders, non-finite numbers, implicit units,
and unbound validated-method claims are rejected. The schema can represent a
draft protocol, but only a fully B5-bound protocol can import real outcomes.

## Real-data import boundary

The strict JSONL importer accepts exact-schema records only. Every real record
must include:

- a unique observation ID and canonical protocol hash;
- material, matrix, condition, formula, supplier-lot, matrix-batch, and
  measurement-session identity;
- chemical-identity and close-analog leakage groups;
- a supported B5 claim receipt with method, validation, run, peak, claim,
  matrix-calibration, analyte-calibration, and method-calibration identifiers;
- distinct vendor-raw and open-export SHA-256 digests;
- measured value, prediction, baseline prediction, unit, uncertainty, and
  prediction interval, or an explicit model abstention; and
- `REAL_INSTRUMENT` origin.

`SIMULATED_SMOKE` is rejected by the real importer. Simulation is accepted only
by a separate smoke-evaluation function whose report authority is
`SIMULATION_ONLY` and whose empirical decision is always ineligible.

## Leakage-resistant split and held-out lock

The split manifest is immutable, hash-bound, and must contain nonempty
`CALIBRATION`, `VALIDATION`, and `HELD_OUT_TEST` partitions. It rejects overlap
between partitions for every one of:

- chemical identity;
- close analog group;
- formula;
- supplier lot;
- matrix batch; and
- measurement session.

Split assignment uses descriptors without outcomes. The evaluation plan and
acceptance criteria are locked before model selection. A model-lock receipt
binds the model digest, split digest, evaluation-plan digest, and validation
dataset digest. Held-out outcomes can be released to the evaluation API only
after that receipt, with a later timestamp and matching digests. The API never
offers an ambient `latest` selection.

## Prespecified metrics and decisions

The plan requires, overall and by material class, matrix, and condition:

- bias;
- MAE;
- RMSE;
- median absolute fold error;
- rank agreement;
- calibration slope and intercept;
- prediction-interval coverage;
- catastrophic-outlier count/rate;
- missing-domain and abstention count/rate; and
- performance against the declared baseline.

Metrics are computed on the plan's declared linear or log10 scale. Fold error
always uses positive original-scale values. R-squared is not an acceptance
metric. Undefined metrics fail closed. Acceptance criteria are immutable,
explicit comparators and thresholds bound into the plan hash before held-out
release. A failed criterion produces `FAIL`; it cannot promote the model.

## Empirical status and C5 exit

C5 software/protocol acceptance and empirical-model acceptance are separate.
With no actual records, the canonical empirical assessment is exactly:

- status: `BLOCKED_PENDING_DATA`;
- metrics: absent;
- model promotion: false; and
- reasons: no validated B5-bound protocol, no real instrument observations,
  no locked leak-resistant split, and no pre-held-out model lock.

C5 passes only when the harness is reproducible, simulated smoke tests are
truthfully segregated, leakage controls and metric formulas are executable,
and the empirical block cannot be bypassed. C6 may open from the C5 software
gate, but no measured domain is declared calibrated and Build C cannot claim
empirical completion without real data.

## Verification

Acceptance requires focused tests for canonical hashes, inventory/matrix
coverage, exact schemas, B5 binding, real/simulated separation, each leakage
dimension, split/model/held-out ordering, metric formulas, grouped metrics,
baseline comparison, acceptance failure, and the no-data block. It also
requires C0-C4 regressions, root tests, dependency consistency, Ruff,
basedpyright, mypy, archive verification, protected-database verification,
three bounded mutation catches, an exact-commit replay, and a bounded
DeepLuna Fast final audit independently reproduced by Sol.
