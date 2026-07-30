# Build B2 Observation-First Property Authority Design

**Status:** Approved for implementation by the controlling master prompt and
the user's standing authorization.

**Scope:** B2 only. This does not implement threshold/OAV policy (B3), rule
compilation (B4), analytical/regulatory expansion (B5–B6), or claim sufficiency
policy (B7).

## Decision

Add a focused `lab_properties` authority module to the canonical laboratory
database. Reuse B1 source versions, extraction records, workflow acceptance,
and derivation reconstruction. Do not extend the legacy scalar property row
into an observation and do not create an engine-side truth store.

Alternatives rejected:

1. Extending `LabMaterialProperty` cannot represent exact grade/lot identity,
   typed/censored values, condition context, conflicts, or selection policy.
2. One JSON “current property” document would permit last-write-wins and weak
   database constraints.
3. Engine-only property registries would create parallel scientific truth.

## Identity contract

Every observation stores:

- `identity_scope` from `CHEMICAL_ENTITY`,
  `STEREOISOMER_OR_ISOMERIC_MIXTURE`, `TRADE_GRADE`,
  `SUPPLIER_PRODUCT`, `SUPPLIER_LOT`, `STOCK_SOLUTION`,
  `PHYSICAL_DOSE`, or `NATURAL_MATERIAL`;
- complete `subject_identity_json`;
- deterministic `subject_identity_sha256`.

Service validation requires scope-specific keys. A natural identity requires
botanical species, plant part, chemotype, geographic origin,
harvest/production period, extraction/processing, supplier product, supplier
lot, analytical profile, and stock solution. Values may state an explicit
unknown, but dimensions may not disappear. CAS equality never collapses grade,
lot, natural, dilution, dose, or sensory scope.

## Canonical tables

### `lab_property_observations`

One immutable observation contains:

- schema version, identity scope/JSON/hash, property type;
- one exact `value_kind`: `NUMERIC`, `CATEGORICAL`, `INTERVAL`,
  `DISTRIBUTION`, or `CENSORED`;
- mutually constrained typed value columns;
- censored qualifiers `LT_LOD`, `LT_LOQ`, `GT_UPPER_RANGE`,
  `NOT_DETECTED`, or `TRACE`;
- original and canonical units;
- temperature, pressure, humidity, matrix, phase, purity, and method;
- B1 source version, extraction record, and exact locator;
- replicate count, statistic, standard uncertainty, uncertainty interval;
- evidence class, review state, quality flags, applicability domain,
  provenance activity, supersession link, and content SHA-256.

`NOT_DETECTED` has no numeric value and is never normalized to zero. Interval
and distribution records remain typed; incompatible observations are not
averaged.

### `lab_property_conflict_sets`

An immutable conflict set declares requested subject/property/conditions,
materiality, unresolved or scoped-resolution state, differing dimensions,
explanation, and content digest.

### `lab_property_conflict_members`

Each member links one observation and records its exact differences from the
request/anchor. At least two members are required by the service. Identity,
method, matrix, temperature, unit, endpoint, and source independence remain
visible.

### `lab_selected_assertions`

An immutable selected assertion stores requested property/conditions,
selection-policy version, optional conflict set, selected observation/model or
explicit none, interpolation/extrapolation state, propagated uncertainty,
applicability, authority state, permitted wording, and content digest.

Consumers retrieve assertions by explicit ID. No repository method returns
“latest selected value.”

### `lab_selected_assertion_candidates`

Every candidate observation receives `INCLUDE` or `EXCLUDE` plus a nonblank
rationale. Candidate membership is relational and foreign-key constrained.

## Legacy boundary

Add nonnullable `authority_state` and `authority_reason` columns to
`lab_material_properties`. Existing and new rows default to
`LEGACY_HEURISTIC`, are frozen by append-only triggers, and are never copied
into `lab_property_observations`. The migration must prove that representative
legacy rows gain the label while B2 canonical tables remain empty.

## Service rules

`LabPropertyServiceMixin` owns validated commands to:

- create a property observation only when its B1 extraction exists, points to
  the same source version, reserves the same observation ID, and is accepted
  for the requested scope;
- create a conflict set from two or more existing observations while computing
  visible difference dimensions;
- create a selected assertion only when every candidate has one explicit
  decision and the selection is internally consistent;
- withhold authority for unresolved material conflicts;
- reconstruct assertion → candidates/conflict → observations → B1 derivation.

Stable errors identify identity, value-shape, source, workflow, duplicate,
conflict, selection, and authority failures without exposing environment data.

## Migration

Alembic revision `20260730_0006`, down-revision `20260730_0005`:

- adds the two explicit legacy authority columns;
- creates the five B2 tables, constraints, indexes, and foreign keys;
- installs SQLite update/delete guards on B2 tables and legacy properties;
- performs no canonical observation backfill;
- preserves all B1 and earlier schema/data;
- supports downgrade/re-upgrade on temporary databases.

## Verification

TDD must prove:

- exact identity hashes distinguish equal-CAS grades/lots and each natural
  dimension;
- all value kinds round-trip and invalid mixed shapes fail at service/database
  boundaries;
- `NOT_DETECTED` never becomes zero;
- observation creation requires accepted exact-scope B1 extraction linkage;
- conflicts remain visible and incompatible values are not averaged;
- selected assertions enumerate all candidates and use explicit policies;
- unresolved material conflicts withhold authority;
- no last-write-wins API exists;
- legacy values are labeled/frozen but not promoted;
- migration preserves representative B1 rows and canonical tables remain
  empty after legacy labeling;
- export/backup/current-head compatibility remains green.

The B2 gate passes only with fresh preserved logs and a machine-readable
verification report.
