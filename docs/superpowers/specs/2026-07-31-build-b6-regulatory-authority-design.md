# Build B6 Safety and Regulatory Authority Design

## Decision

Build B6 adds an append-only, date-aware regulatory screening authority. It
does not rewrite or backfill A2 regulatory rows, alter protected databases,
claim legal compliance, issue an IFRA certificate, expose a production API, or
route an optimizer or UI consumer. Production routing remains a B9 decision.

The selected design has seven additive tables:

1. official regulatory source versions;
2. regulatory rule versions;
3. exact supplier-document bindings;
4. stock-lot composition profiles;
5. composition-profile entries;
6. immutable regulatory snapshot versions; and
7. per-rule regulatory findings.

Existing A2 regulatory assessments remain historical acquisition records. An
A2 `PASS` is not a B6 result and cannot support B6 wording. B1 source versions
remain the artifact and workflow authority; B6 copies and verifies their exact
digests and scoped acceptance rather than replacing them.

The user delegated design approval to Sol and prohibited permission prompts.
Sol approves this design after reading the authoritative master prompt,
inspecting the repository, verifying current official sources, and reviewing a
bounded DeepLuna Fast gap inventory. DeepLuna was advisory; executable
repository evidence remains authoritative.

## Current official-source state

The source status was rechecked on 2026-07-31.

- IFRA reports that the 52nd Amendment consultation closed on 2026-06-12 and
  that formal notification is expected near the end of November 2026:
  <https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed>.
  B6 therefore records the 52nd Amendment consultation as `CONSULTATION`; it
  cannot displace or be enforced as the latest formally notified amendment.
- Commission Regulation (EU) 2023/1545 establishes individual fragrance
  allergen labelling above 0.001% in leave-on products and 0.01% in rinse-off
  products. The official text permits affected non-compliant products to be
  placed on the Union market until 2026-07-31 and made available until
  2028-07-31:
  <https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng>.

The implementation stores these facts as versioned data. Constants in code
define vocabularies and algorithms, not mutable claims that a particular
amendment or regulation is current.

## Considered approaches

### 1. Expand the A2 regulatory tables in place

This would require ambiguous backfill and would make historical `PASS` rows
appear to satisfy B6 despite missing transition windows, supplier identity,
natural-material composition, and current-state evidence. Rejected.

### 2. Put regulatory detail into existing JSON fields

This minimizes schema work, but direct reads could not distinguish validated
B6 state from legacy payloads, supplier-document scope would remain
unenforceable, and transition semantics would be opaque. Rejected.

### 3. Add a dedicated B6 authority graph

This keeps A2 and B1 compatibility, makes B6 completion explicit and
queryable, permits zero-backfill migration, and provides a fail-closed
screening gate without prematurely changing production consumers. Selected.

## Canonical model

### `lab_regulatory_source_versions`

One immutable row records one official-current-state observation. It contains:

- a stable authority ID, positive revision number, and optional parent;
- authority family: `IFRA_STANDARD`, `JURISDICTIONAL_LEGISLATION`, or
  `OFFICIAL_GUIDANCE`;
- identifier, published version or amendment, jurisdiction, and status;
- notification, effective-from, effective-through, and checked-at dates;
- an optional exact source version that this row supersedes;
- the exact B1 official source version, locator, and copied artifact digest;
- notes that distinguish enforceable content from monitored content; and
- a canonical content hash.

The status vocabulary is exactly:

- `CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED`
- `FUTURE_EFFECTIVE`
- `DRAFT`
- `CONSULTATION`
- `WATCHLIST`
- `SUPERSEDED`

The B1 source must be `REGULATION_OR_OFFICIAL_GUIDANCE` or `STANDARD`, carry
the same 64-character artifact digest, and be accepted for
`regulatory_authority`. `FUTURE_EFFECTIVE` requires a future effective date.
Draft, consultation, and watchlist rows cannot supersede an enforced source.
An enforced source is no longer selectable when a later eligible row names it
as superseded. Every evaluation requires source checks recorded on the same
UTC date as the evaluation.

### `lab_regulatory_rule_versions`

One immutable rule binds to one official source version and records:

- stable rule ID, positive revision, and optional parent;
- rule family: `IFRA_RESTRICTION`, `LEGAL_RESTRICTION`, or
  `ALLERGEN_LABELING`;
- official rule identifier and substance name, optional CAS number, and
  optional canonical material;
- jurisdiction, product category, and use classification;
- concentration basis and rule kind:
  `MAXIMUM_FINISHED_FRACTION` or `DECLARATION_THRESHOLD`;
- a nonnegative maximum or threshold fraction;
- required declaration wording where applicable;
- effective-from and effective-through dates;
- inclusive non-compliant placement and availability transition end dates;
- transition conditions and assumptions; and
- a canonical content hash.

An allergen-labelling rule requires a declaration threshold and wording.
Restrictions require a maximum fraction. Rule jurisdiction and source
jurisdiction must agree. Rules from `DRAFT`, `CONSULTATION`, `WATCHLIST`, or
`SUPERSEDED` sources are recordable but never enforceable.

For an action on the exact inclusive transition end date, the transitional
allowance remains available. Enforcement begins on the following date.
`PLACE_ON_MARKET` uses the placement end date; `MAKE_AVAILABLE` uses the
availability end date. Missing transition context cannot be guessed.

### `lab_supplier_document_bindings`

One immutable row binds one accepted B1 supplier document to one exact stock
solution and captures:

- document scope: `SUPPLIER_PRODUCT` or `SUPPLIER_LOT`;
- supplier, product name, product code, grade, document type, document
  version, and optional lot;
- effective and expiry dates;
- exact B1 source version, locator, and copied artifact digest;
- the normalized supplier-identity hash; and
- a canonical content hash.

Document types are the five B1 supplier types: COA, specification, SDS, IFRA
certificate, and allergen declaration. The service compares the binding with
the stock solution's supplier, lot, and normalized `source_json` product,
code, grade, and origin fields. A lot-scoped document must match the lot.
A product-scoped document is still bound to that exact stock record and cannot
silently transfer across supplier, product, code, or grade. The source must be
accepted for `supplier_regulatory_document`.

### `lab_regulatory_composition_profiles`

One immutable versioned profile binds to one exact stock solution and records:

- origin: `SYNTHETIC`, `NATURAL`, or `TRADE_GRADE`;
- composition basis: `LOT_SPECIFIC`, `DOCUMENTED_PROXY`, or `UNKNOWN`;
- completeness: `COMPLETE`, `PARTIAL`, or `UNKNOWN`;
- an exact supplier-document binding when the composition is known;
- assumptions, limitations, reviewer, review time, and content hash.

Known profiles require a COA, specification, or allergen declaration binding.
`LOT_SPECIFIC` requires a lot-scoped binding. `DOCUMENTED_PROXY` is allowed
only with an explicit product-scoped source, copied assumptions, and an exact
stock identity. `UNKNOWN` has no supplier binding and no entries.

A natural or trade-grade stock requires a current `COMPLETE` profile to
support a pass. `PARTIAL`, `UNKNOWN`, a missing profile, or a stale binding
forces the overall evaluation to `UNKNOWN`.

### `lab_regulatory_composition_entries`

Each immutable entry belongs to one profile and records:

- a positive unique position;
- projection family fixed to `REGULATORY`;
- constituent name, optional CAS number, and optional canonical material;
- nonnegative constituent fraction and fraction basis;
- uncertainty and source locator; and
- a canonical content hash.

The fixed projection family prevents olfactory projection, regulatory
projection, and identity/authenticity evidence from being conflated. B6 never
uses odor contribution, OAV, peak area, tentative analytical identity, or
authenticity state as a regulatory constituent fraction.

### `lab_regulatory_snapshot_versions`

This is the B6 `RegulatorySnapshot`. One immutable version records every
required declaration:

- stable snapshot ID, positive version, and optional parent;
- exact subject type and ID: `FORMULA_VERSION` or `BUILD_PLAN_VERSION`;
- optional non-authoritative A2 assessment reference;
- primary standard or regulation identifier and version;
- copied official source digest;
- jurisdiction, product category, and use classification;
- formula/build version identity;
- finished-product concentration and constituent basis;
- natural-material assumptions;
- effective date, evaluation time, and evaluator software version;
- market action and action date;
- exact ordered current-state, watch-source, rule, supplier-binding, and
  composition-profile IDs plus upstream hashes;
- unresolved items and stable result reasons;
- result state and optional permitted wording;
- reviewer and review time; and
- canonical content and parent hashes.

Result state is exactly:

- `PASS_FOR_DECLARED_SCOPE`
- `FAIL`
- `UNKNOWN`
- `NOT_EVALUATED`

Only `PASS_FOR_DECLARED_SCOPE` can store wording, and the service generates
that wording rather than accepting caller marketing text. The wording says
only that screening passed for the declared jurisdiction, product category,
use classification, action date, formula/build version, and recorded sources.
It contains no certificate or legal-conformity claim. All other states require
null wording.

An A2 assessment reference, including an A2 `PASS`, is copied only as
historical context. It never changes the B6 result and is insufficient without
the complete B6 graph.

### `lab_regulatory_authority_findings`

One immutable finding binds a snapshot to one exact rule and records:

- substance identity, observed finished-product fraction, applicable limit,
  concentration basis, and source status;
- whether the rule was enforced for the declared action and date;
- exact contribution/profile lineage;
- stable reason codes, detail, and result state; and
- a canonical content hash.

An enforced known over-limit restriction is `FAIL`. An enforced known
within-limit rule is `PASS_FOR_DECLARED_SCOPE`. Missing or incomplete
composition, supplier scope, source freshness, or transition context is
`UNKNOWN`. Draft, consultation, watchlist, superseded, and not-yet-applicable
future rules are persisted as non-enforced `NOT_EVALUATED` findings and cannot
raise or lower the enforced result.

## Evaluation algorithm

The evaluation service resolves all identities in one transaction.

1. Resolve the exact formula version or build-plan version and ordered stock
   lines.
2. Verify the finished concentration, mass basis, positive total quantity,
   and exact stock active fractions.
3. Verify same-day current-state source records, reject superseded selections,
   and retain draft/consultation/watchlist sources as non-enforced watch data.
4. Verify each rule's jurisdiction, category, use class, source status,
   effective dates, and action-specific transition window.
5. Verify required supplier bindings for each stock: SDS, IFRA certificate,
   and allergen declaration; natural/trade-grade composition additionally
   requires an applicable COA or specification source.
6. Calculate each stock's active material fraction from immutable formula or
   build-plan quantities.
7. Treat a synthetic material as a direct regulatory constituent. For a
   natural or trade-grade material, multiply by each complete lot-specific or
   documented-proxy profile entry.
8. Aggregate matching constituent keys across all stocks, then multiply by
   finished-product concentration. Never substitute peak area, OAV, odor
   projection, or unreviewed identity.
9. Evaluate every enforceable rule and persist findings.
10. Derive the snapshot result deterministically:
    - any enforced failure -> `FAIL`;
    - otherwise any unresolved authority, composition, supplier document, or
      enforceable rule -> `UNKNOWN`;
    - otherwise all enforceable rules passed -> `PASS_FOR_DECLARED_SCOPE`;
    - an explicit unevaluated draft record -> `NOT_EVALUATED`.

`UNKNOWN` always outranks a would-be pass but never hides a known failure.
Known failure therefore outranks unknown in the final result.

## Supplier-document policy

The required document set is explicit and deterministic:

- every stock: current exact SDS, IFRA certificate, and allergen declaration;
- natural or trade-grade stock: a current exact COA or specification source
  for composition;
- a lot-specific composition profile: a lot-scoped source;
- a documented proxy: a product-scoped source with explicit assumptions.

Expiry is evaluated against the regulatory evaluation date. Missing identity
fields or a mismatched supplier, product, code, grade, version, or lot cannot
be repaired by inference.

## Determinism and append-only behavior

Typed inputs normalize enumerations, reject empty identifiers, non-finite
numbers, naive timestamps, and non-canonical hashes. JSON is canonicalized
before hashing. Ordered IDs and reason codes are stable and sorted.

Every B6 table is append-only. Duplicate content hashes and invalid version
chains fail at the database boundary. The migration creates no B6 rows and
does not reinterpret A2, B1, B2, B3, B4, or B5 data. Downgrade drops only B6
tables in reverse dependency order.

## Compatibility boundary

B6 does not change legacy chemistry validators, ingredient `ifra_max_level`
fields, API endpoints, UI, optimizer inputs, protected databases, or current
export schemas. Those consumers remain non-authoritative until B9 explicitly
routes them through passed canonical gates.

## Verification

The RED/GREEN suite must prove:

- all seven tables, constraints, indexes, FKs, hashes, and append-only guards;
- zero-row upgrade, reverse downgrade, and downgrade/re-upgrade;
- source lifecycle, same-day checks, supersession, and consultation/watchlist
  non-enforcement;
- exact EU leave-on and rinse-off thresholds plus action-specific inclusive
  2026/2028 transition ends;
- exact supplier product, grade, document version, and lot scope;
- lot-specific and documented-proxy natural composition;
- unknown or partial natural composition yields `UNKNOWN`, never pass;
- regulatory projection cannot accept olfactory or identity/authenticity
  values;
- formula-version and build-plan aggregation;
- known over-limit failure outranks unknown, while unknown blocks pass;
- only `PASS_FOR_DECLARED_SCOPE` stores narrowly scoped screening wording;
- an A2 `PASS` alone remains non-authoritative;
- B1-B6 compatibility, Ruff, mypy, current-head, and backup/restore checks;
  and
- unchanged protected database hashes.

## B6 exit gate

B6 passes only when canonical tests reproduce:

`official current-state sources -> exact rules and transitions -> exact
supplier documents -> stock-lot/proxy composition -> formula/build aggregate
-> per-rule findings -> fail-closed regulatory snapshot`

and separately prove that IFRA 52 consultation data is not enforced, the EU
transition boundary is date- and action-aware, unknown natural composition
cannot pass, supplier documents cannot cross identity scope, and no legacy A2
row or consumer path is promoted.
