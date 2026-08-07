# Build B5 Analytical Authority Design

## Decision

Build B5 adds an append-only analytical-authority specialization over the
existing A2 acquisition records. It does not rebuild or reinterpret the A2
tables, backfill authority, alter protected databases, expose a production
API, or route any optimizer or UI consumer.

The selected design is additive because A2 already provides useful immutable
method, run, peak, QC, attachment, and GC-O identities, but its broad JSON
fields and three-state identity model cannot enforce B5 claim authority.
Only records that pass the new B5 service and claim gate can support an
analytical claim.

The user delegated design approval to Sol and prohibited further permission
questions. Sol approves this design after local repository inspection,
master-prompt reconciliation, and a bounded DeepLuna Fast gap inventory.
DeepLuna's findings are advisory; the repository, tests, constraints, and
reproduced evidence remain authoritative.

## Current-state evidence

The current A2 analytical graph is append-only and content-addressed, but:

- `LabAnalyticalMethodVersion` stores most method detail in unstructured
  `method_json` and exposes only `DRAFT`, `VALIDATED`, and `RETIRED`;
- `LabAnalyticalRun` permits one or several simultaneous contextual subjects,
  has no stock-lot or bottle-stream-sequence field, and stores sequence,
  instrument-state, and processing detail in broad JSON;
- `LabAnalyticalPeak` exposes only `UNASSIGNED`, `TENTATIVE`, and `CONFIRMED`;
- quantitative fields do not distinguish calibrated concentration from peak
  area percentage;
- QC criteria and observations are free-form and the current exact-claim
  check accepts any nonempty all-PASS QC set;
- attachments have strong digests but do not establish that both vendor raw
  data and an open export were preserved;
- GC-O events lack assessor training, event windows, detection frequency, and
  an explicit prohibition on chemical-identity promotion; and
- no method-validation record or analytical missing-requirement assessment
  exists.

Therefore existing A2 rows remain acquisition history. They gain no B5
authority through migration or inference.

## Considered approaches

### 1. Rewrite the A2 analytical tables

This could make every required field a first-class column, but it would mutate
an established append-only baseline, force ambiguous backfill, disrupt the
v3/v4 export contract, and make old rows appear more authoritative than their
evidence supports. Rejected.

### 2. Validate the existing A2 JSON fields in service code

This minimizes schema work, but old and new rows remain indistinguishable,
direct reads cannot tell whether B5 validation occurred, and the legacy exact
claim path remains fail-open. Rejected.

### 3. Add one-to-one B5 authority records over A2

This preserves acquisition compatibility while making B5 completion explicit,
queryable, append-only, and zero-backfill. It also permits a focused claim
gate without prematurely changing API, export, optimizer, or UI consumers.
Selected.

## Canonical model

Build B5 adds eight tables.

### `lab_analytical_method_authorities`

One row specializes one immutable A2 method version. It records:

- B5 schema version and status: `EXPLORATORY`, `VERIFIED`,
  `VALIDATED_FOR_SCOPE`, or `RETIRED`;
- nonempty analyte scope;
- structured instrument, detector, software, separation, acquisition,
  sample-preparation, standards, calibration, response-factor,
  identity-criteria, integration/deconvolution, QC-plan, and raw-data-policy
  payloads;
- complete HS-SPME conditions when the A2 technique is `HS_SPME_GCMS`;
- an exact B1 source-document version, locator, and copied artifact digest;
  and
- a unique canonical content hash.

The service requires named keys for every method component. It rejects
non-finite JSON numbers, unknown keys in authority-critical policy objects,
and empty placeholder values. `VERIFIED` and `VALIDATED_FOR_SCOPE` require a
B1 source accepted for the exact `ANALYTICAL_METHOD_AUTHORITY` scope.
Accreditation is not represented or implied.

The existing A2 method version remains the owner of technique, intended use,
version chain, and identity. B5 status must be compatible with the A2 status:
exploratory with `DRAFT`, verified/validated-for-scope with `VALIDATED`, and
retired with `RETIRED`.

### `lab_method_validation_records`

Each immutable record binds a method authority to one intended claim and one
matrix/scope digest. It records all required fitness-for-purpose
characteristics:

- selectivity/specificity;
- calibration function, working range, residual behavior, and weighting;
- LOD and LOQ;
- trueness/recovery;
- repeatability and intermediate precision;
- robustness/ruggedness;
- matrix effect, carryover, sample stability, and blank behavior;
- sampling/preparation uncertainty and measurement uncertainty;
- explicit acceptance criteria;
- `PASS`, `FAIL`, or `INCOMPLETE`;
- limitations, reviewer, review time, and exact B1 source provenance.

A method status label never substitutes for this record. Supported quantity
claims require a matching `PASS` record. The service stores no accreditation
claim.

### `lab_analytical_sequences`

A sequence header and all entries are created in one transaction. The header
binds an exact method authority, sequence key, instrument identifier, status,
entry count, and hash of the complete ordered entry payload.

### `lab_analytical_sequence_entries`

Each positive, unique injection order has one role from:

`SAMPLE`, `SOLVENT_BLANK`, `METHOD_BLANK`, `CALIBRATION_STANDARD`,
`INTERNAL_STANDARD`, `SPIKE`, `DUPLICATE`, `REPLICATE`, `QC_SAMPLE`,
`RI_STANDARD`, or `CONTROL`.

The entry preserves its sample/standard reference and declared level or
preparation payload. The service requires at least one sample, every QC role
named by the method policy, and a calibration standard when the method
declares quantitative use.

### `lab_analytical_run_authorities`

One row specializes one A2 run and binds:

- exactly one B5 primary subject: `SAMPLE`, `STOCK_LOT`, `NATURAL_LOT`,
  `FORMULA_VERSION`, `BUILD_PLAN_VERSION`, or `BOTTLE_STREAM`;
- one canonical subject ID and, for a bottle stream, one exact positive stream
  sequence;
- one acquired sequence and the exact sample entry used for the subject;
- matrix and applicability scope;
- instrument state, processing detail, and deviation assessment;
- reviewer and review time;
- disposition: `PENDING`, `ACCEPTED`, `QUALIFIED`, or `REJECTED`;
- one A2 `RAW_VENDOR_DATA` attachment and one distinct A2 `OPEN_EXPORT`
  attachment, each belonging to the same run and carrying a valid digest; and
- a canonical content hash.

The service resolves samples, formulas, build plans, and bottles through their
canonical tables. `STOCK_LOT` and `NATURAL_LOT` resolve to one canonical
`LabStockSolution` with a nonempty supplier lot; a natural lot additionally
requires an explicit natural-material marker in the stock source payload.
`BOTTLE_STREAM` resolves the bottle and exact event-stream sequence. A matching
A2 subject link is required when A2 has a column for that primary type. Other
A2 populated subject columns remain acquisition context and cannot broaden the
B5 claim scope. A peak table alone can never satisfy this record.

### `lab_analytical_peak_authorities`

One row specializes one A2 peak. Identity state is exactly one of:

`CONFIRMED_AUTHENTIC_STANDARD`,
`STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM`, `PROBABLE`,
`TENTATIVE_LIBRARY_MATCH`, `UNRESOLVED`, or `REJECTED`.

The row preserves stationary phase, spectrum evidence, deconvolution,
library candidates and scores, exact-mass evidence, authentic-standard and
co-injection states, quantifier ions, coelution assessment, manual review,
identity decision, applicability, and reviewer.

`CONFIRMED_AUTHENTIC_STANDARD` requires a matched authentic standard or
co-injection, an A2 material identity, manual review, spectrum evidence, and
retention evidence. A library score alone can reach only
`TENTATIVE_LIBRARY_MATCH`. `STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM` requires both
retention-index and spectrum support.

Quantitation state is `NONE`, `AREA_PERCENT_ONLY`, or
`CALIBRATED_CONCENTRATION`. Calibrated concentration requires an exact
calibration reference, standard, response factor, working range, dilution
factor, blank correction, applicable QC, quantity unit and basis, and
measurement uncertainty. Area percentage is explicitly non-authoritative for
formula weight percentage.

For `HS_SPME_GCMS`, calibrated concentration additionally requires declared
matrix, analyte, and method calibration identifiers matching the claim scope.
Otherwise the response remains method- and matrix-dependent advisory data.

### `lab_gco_event_authorities`

One row specializes one A2 GC-O event. It records assessor training status,
an RT or RI start/end window, detection/intensity method, replicate index and
count, detection frequency, repeatability, same-run aligned peak candidates,
and unknown-event status.

The schema fixes `exact_identity_claim` to false. GC-O can support an
odor-active-region statement but cannot confer exact chemical identity.

### `lab_analytical_claim_assessments`

The claim gate writes one immutable assessment for an identity or quantity
request. It records:

- the exact A2 analytical run ID plus exact run and peak authority IDs;
- claim type and evaluation-policy version;
- `SUPPORTED_FOR_SCOPE`, `ADVISORY_ONLY`, or `WITHHELD`;
- requested scope, stable sorted missing-requirement codes,
  qualifications, upstream content hashes, reviewer, and evidence record;
- a result payload only when the decision permits it; and
- a unique canonical content hash.

`WITHHELD` rows must have a null result. A failed blocking QC check, rejected
run, missing raw file, unvalidated quantity method, unsupported identity tier,
missing uncertainty, scope mismatch, or absent review prevents support.

## QC propagation

The method QC plan has two closed objects:

- `required_checks`: an ordered set drawn from `BLANK`,
  `DRIFT_CHECK`, `CALIBRATION_VERIFICATION`, `INTERNAL_STANDARD`,
  `RI_STANDARD`, `DUPLICATE`, and `CONTROL_SAMPLE`;
- `failure_policy`: exactly one `BLOCK` or `QUALIFY` value for each required
  check.

The claim gate groups A2 QC records by `qc_type`.

- A missing required type yields `QC_REQUIRED_CHECK_MISSING`.
- `UNKNOWN` or `NOT_APPLICABLE` on a required check yields
  `QC_REQUIRED_CHECK_UNRESOLVED`.
- A `FAIL` with `BLOCK` yields `QC_FAILED_BLOCKING` and withholds the result.
- A `FAIL` with `QUALIFY` yields `QC_FAILED_QUALIFYING` and caps the decision
  at advisory.
- Passing all required checks satisfies only the QC dimension; it does not
  substitute for method, raw-data, calibration, identity, uncertainty,
  applicability, or review requirements.

Missing codes are stable and sorted; details identify affected QC types
without encoding dynamic values into the code vocabulary.

## Claim flow and legacy bypass closure

The supported end-to-end flow is:

1. create an A2 method version and its B5 method authority;
2. record a matching method-validation result;
3. create the complete ordered sequence;
4. create the A2 run, preserve vendor raw data and open export, then bind B5
   run authority to exactly one primary subject and sequence entry;
5. record A2 QC and peak data;
6. add B5 peak identity/quantity authority;
7. evaluate and persist the B5 analytical claim assessment; and
8. if a caller also requests an A2 `ALLOW_EXACT` analytical-run claim, require
   the exact matching supported B5 assessment ID in its authority payload.

An all-PASS legacy QC set without a B5 assessment is rejected. This closes the
existing bypass while preserving non-analytical A2 claim behavior.

## Error handling and determinism

Typed command inputs normalize enum values, reject empty identifiers, validate
timezone-aware review times, and canonicalize JSON before hashing. Service
conflicts use stable codes. Repository reads use explicit IDs; there is no
ambient `latest` selection in the B5 claim path.

Every B5 table is append-only. Duplicate content hashes or one-to-one
authority bindings fail at the database boundary. The migration creates no
records. Downgrade drops only B5 tables in reverse dependency order.

## Compatibility boundary

B5 does not change A2 table columns, legacy adapters, protected databases,
`lab-export-v3`/`lab-export-v4`, production endpoints, optimizer inputs, or UI
behavior. B9 will decide explicit production routing and any new export
revision. Until then, B5 is reachable only through the canonical service.

## Verification

The RED/GREEN suite must prove:

- all eight tables, named constraints, FKs, indexes, and append-only guards;
- zero-row upgrade, reverse downgrade, and downgrade/re-upgrade;
- required method fields and complete HS-SPME conditions;
- source-scope and status compatibility;
- full validation characteristics and no accreditation field;
- atomic sequence creation and deterministic order/hash;
- exact primary-subject run binding for sample, stock lot, natural lot,
  formula, build plan, and bottle stream, plus two distinct preserved raw-file
  forms;
- all six identity states and authentic-standard/library-match ceilings;
- calibrated quantity requirements, area-percent non-equivalence, and
  HS-SPME matrix/analyte/method calibration;
- GC-O window/training/replicate/frequency data and no identity promotion;
- blocking and qualifying QC propagation with exact missing codes;
- supported, advisory, and withheld claim records, including no numerical
  result when withheld;
- the full method-to-evidence-claim chain and failed-QC blocking;
- the legacy exact analytical claim bypass is closed;
- B1-B5 compatibility, Ruff, mypy, current-head, and backup/restore checks;
  and
- unchanged protected database hashes.

## Evidence boundary

The design follows the fitness-for-purpose and uncertainty principles exposed
by the official ISO/IEC 17025, Eurachem method-validation, and BIPM GUM
sources. Passing B5 does not claim laboratory accreditation, universal method
validity, or truth beyond the recorded matrix, analyte, method, and review
scope.

## B5 exit gate

B5 passes only when canonical tests reproduce:

`method -> validation -> sequence -> run -> vendor raw + open export -> QC ->
peak -> identity/quantity -> analytical claim`

and separately prove that blocking failed QC withholds the result, qualifying
failed QC cannot exceed advisory, legacy all-PASS QC cannot bypass B5, and no
pre-B5 row was promoted or rewritten.
