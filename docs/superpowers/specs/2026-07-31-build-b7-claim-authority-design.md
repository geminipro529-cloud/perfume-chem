# Build B7 Claim-Specific Scientific Authority Design

## Decision

Build B7 adds a new append-only authority layer over the canonical B1-B6
records. It does not widen the legacy A2/A4 boolean gate. A2 claim assessments
remain historical inputs; only a B7 assessment computed from records that the
service resolves from the database can authorize a scientific claim.

The selected design has two additive tables:

1. immutable claim-authority versions; and
2. immutable typed links to canonical B2-B6 support records.

The policy registry is code-owned and content-hashed. Every persisted
assessment snapshots its complete policy and hash. A caller cannot create a
weaker policy, assert that a condition matched, or promote a claim by setting a
boolean in JSON.

This design follows the master prompt, the live repository at
`0c4b7496dcf71e5ad5d8cd60414086e22beade61`, and the bounded DeepLuna Fast
gap audit `DS-f4ac6cf7f5dce29740ee81de03b42135`. DeepLuna was advisory; the
repository schema, service behavior, and executable tests remain authoritative.

## Recovery and preservation gate

Before this design changed the repository, the complete non-runtime dirty and
untracked state plus all existing shared B7 targets was archived at:

`D:\.backups\perfume-chem\build-b7-prewrite-20260731T064410+0700.tar`

The archive contains 405 path-preserving files, is 97,275,904 bytes, and has
SHA-256
`2d487c8b1b681eccc267bb2957d1e6ad03f62621801773a612188165256397dd`.
It was extracted to a separate verification directory and every restored file
was re-hashed successfully. The live `.deepluna-home/` and
`.cheapluna-home/` runtime trees were deliberately excluded; they contain
runtime state and secret-bearing files and are not implementation work.

## Existing authority boundary

The repository already has:

- B1 source-document versions, extraction records, exact locators, artifact
  hashes, review state, and independence groups;
- B2 typed property observations, conflict sets, and selected assertions;
- B3 contextual threshold records and strict-science OAV assessments;
- B4 compiled knowledge rules with provenance and authority state;
- B5 analytical method, validation, run, peak, and claim authority;
- B6 regulatory sources, supplier bindings, composition profiles, snapshots,
  and findings; and
- A2 claim-assessment versions with five decisions and caller-provided
  `authority_json`.

The A2/A4 path is not sufficient for B7 because its critical facts are
caller-provided booleans. It may be retained for compatibility, but no B7
exact or scoped promotion may depend on those booleans.

## Considered approaches

### Expand the generic A4 boolean gate

Rejected. Adding more boolean fields or claim names would preserve the central
defect: the caller could still assert coverage, identity, conditions,
uncertainty, validation, applicability, or safety without proving them from
canonical records.

### Put a B7 result inside A2 `authority_json`

Rejected. JSON-only output would not provide typed upstream links, scoped
version history, append-only database protection, or strong evidence that the
result was derived from B2-B6 records.

### Add a typed B7 overlay

Selected. The new overlay leaves existing tables stable, makes promotion
strictly additive, and lets every result retain exact upstream hashes and
source references.

## Claim types

The code-owned policy registry defines exactly these eleven claim types:

1. `EXACT_CHEMICAL_IDENTITY`
2. `GRADE_IDENTITY`
3. `PROPERTY_VALUE`
4. `THRESHOLD`
5. `ABOVE_THRESHOLD_SCREENING`
6. `ANALYTICAL_IDENTIFICATION`
7. `ANALYTICAL_QUANTITATION`
8. `NATURAL_CONSTITUENT_PROFILE`
9. `KNOWLEDGE_RULE_RECOMMENDATION`
10. `REGULATORY_SCREENING`
11. `FORMULA_OR_MODEL_COMPARISON`

Legacy A2 labels may be normalized only through a closed alias map. An
unrecognized label is withheld, never guessed.

## Policy contract

Every policy declaration contains all of the following:

- required claim-payload fields;
- accepted evidence classes;
- accepted canonical support kinds;
- required identity scope;
- condition-match rule;
- minimum support coverage;
- minimum independent source groups;
- contradiction handling;
- uncertainty limit or an explicit `NOT_APPLICABLE`;
- method-validation requirement;
- model-applicability requirement;
- safety requirement;
- maximum decision;
- permitted wording by decision; and
- forbidden wording.

Policies use the evidence labels already required by the master prompt:
`MEASURED`, `LITERATURE_DERIVED`, `SUPPLIER_PROVIDED`,
`EMPIRICALLY_CALIBRATED`, `MODEL_ESTIMATED`, `HEURISTIC`,
`SPECULATIVE`, and `UNKNOWN`.

The first policy set is deliberately conservative:

| Claim type | Required canonical support | Maximum decision |
| --- | --- | --- |
| Exact chemical identity | exact-scope B2 assertion or supported B5 identity assessment; two independent groups | `ALLOW_EXACT` |
| Grade identity | exact supplier-product or lot B2/B6 record | `ALLOW_EXACT` |
| Property value | exact-scope B2 selected assertion | `ALLOW_EXACT` |
| Threshold | B2 threshold assertion plus B3 context | `ALLOW_EXACT` for the declared context |
| Above-threshold screening | computed strict-science B3 OAV | `ALLOW_SCOPED` |
| Analytical identification | supported B5 identity assessment and validated scope where required | `ALLOW_EXACT` |
| Analytical quantitation | supported calibrated B5 quantity assessment and passing validation | `ALLOW_EXACT` |
| Natural constituent profile | complete lot-specific B6 composition profile | `ALLOW_EXACT`; documented proxies are scoped |
| Knowledge-rule recommendation | approved B4 rule with matching domains | `ALLOW_SCOPED` |
| Regulatory screening | passing current-state B6 snapshot | `ALLOW_SCOPED` |
| Formula or model comparison | matching measured or applicable model support from at least two independent groups | `ALLOW_SCOPED` |

An exact decision means exact only for the persisted identity and condition
scope. It is not a universal claim.

## Canonical support kinds

The typed support-link table accepts only:

- `PROPERTY_ASSERTION` -> `lab_selected_assertions`;
- `OAV_ASSESSMENT` -> `lab_oav_assessments`;
- `KNOWLEDGE_RULE` -> `lab_knowledge_rules`;
- `ANALYTICAL_ASSESSMENT` ->
  `lab_analytical_claim_assessments`;
- `COMPOSITION_PROFILE` ->
  `lab_regulatory_composition_profiles`; or
- `REGULATORY_SNAPSHOT` ->
  `lab_regulatory_snapshot_versions`.

Exactly one typed foreign key is populated on each link. The support role is
`SUPPORTING`, `CONTRADICTING`, or `LIMITATION`. The service resolves the row
and derives the evidence class, identity scope, condition scope, uncertainty,
source references, independence groups, method validation, model
applicability, safety state, and upstream hash. None of those facts are
accepted from the command.

## `lab_claim_authority_versions`

One immutable version records:

- a stable authority ID, positive version number, and optional latest parent;
- the exact A2 claim-assessment version used as historical context;
- the canonical B7 claim type and unchanged A2 subject;
- the claim payload;
- canonical identity and condition scopes plus their SHA-256 digests;
- the complete policy snapshot, policy version, and policy SHA-256;
- one of the five required decisions;
- per-dimension `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` results;
- supporting observations;
- conflicts and missing requirements;
- exact source references and upstream record hashes;
- uncertainty;
- permitted and forbidden language;
- reviewer pseudonym and review timestamp;
- content and parent hashes; and
- a permanently false release-authority flag.

Scalar counts mirror the conflict, missing, critical-unknown, support, and
source-reference arrays so database checks can fail closed without depending
on JSON functions. `ALLOW_EXACT` requires zero conflicts, missing
requirements, and critical unknowns, at least one support and source
reference, and non-empty permitted wording.

The table never conveys release, market, execution, or formula-mutation
authority. Regulatory B7 results are screenings only. Release wording,
certification wording, and claims of universal safety are always forbidden.

## Evaluation algorithm

The service performs one deterministic transaction:

1. Resolve the exact A2 assessment and verify its subject still exists.
2. Normalize the claim type through the closed alias map.
3. Load the code-owned policy and verify its content hash.
4. Canonicalize the claim payload, identity scope, and condition scope.
5. Resolve every typed B2-B6 support row and its full upstream chain.
6. Reject duplicate links and support kinds that the policy does not accept.
7. Derive source documents, locators, artifact hashes, and independence
   groups from B1 records.
8. Evaluate every policy dimension separately. No average, confidence maximum,
   or other aggregate can replace a failed or unknown critical dimension.
9. Apply the decision lattice:
   - unresolved contradiction, explicit upstream rejection, or failed required
     safety -> `BLOCK`;
   - missing required fields, identity mismatch, condition mismatch, missing
     required support, insufficient coverage, unbounded required uncertainty,
     or absent validation/applicability -> `WITHHOLD_UNKNOWN`;
   - only heuristic, speculative, unknown, or otherwise non-promoting support
     -> `ADVISORY_ONLY`;
   - all scoped requirements satisfied -> `ALLOW_SCOPED`;
   - all exact requirements satisfied and the policy permits exactness ->
     `ALLOW_EXACT`.
10. Compute permitted and forbidden wording from the policy and decision.
11. Persist the authority row and typed support links with canonical upstream
    hashes.

An upstream `FAIL`, `REJECTED`, unresolved blocking conflict, or explicitly
contradicting link cannot be softened by stronger evidence elsewhere.

## Scope-preserving upgrades

A revision must use the latest B7 parent and the latest A2 version in the same
A2 claim chain. The B7 claim type, subject, identity-scope hash,
condition-scope hash, and claim-scope hash must remain unchanged.

New evidence may therefore upgrade only that exact scoped claim. A calibrated
analytical concentration cannot upgrade identity, sensory similarity,
regulatory screening, another material, another lot, or another condition
scope. A different scope starts a separate authority chain.

## Compatibility

- The A2/A4 evaluator and its tests remain unchanged for historical
  compatibility.
- Existing B1-B6 records are referenced, not copied or rewritten.
- Protected project databases are not migrated in place during verification.
- The API and UI do not route to B7 until B9.
- B7 does not release formulas, mutate inventory, or certify compliance.

## Verification

The B7 gate requires:

- migration tests for both tables, all checks, indexes, foreign keys, hashes,
  and append-only triggers;
- policy-registry tests proving exactly eleven complete declarations and stable
  policy hashes;
- service tests for all five decisions;
- at least one canonical positive path for every claim type;
- negative tests proving caller A2 booleans are ignored;
- negative tests proving B2 `HEURISTIC`, `SPECULATIVE`, and `UNKNOWN` evidence
  cannot produce `ALLOW_EXACT`;
- negative tests proving identity, lot, matrix, route, endpoint, date,
  jurisdiction, category, and model-domain mismatches cannot promote;
- negative tests for unresolved conflicts, failed QC or validation, unknown
  natural composition, failed/unknown regulatory snapshots, insufficient
  independent sources, and forbidden release wording;
- revision tests proving a support upgrade changes only the same scoped claim;
- reconstruction and content-hash determinism;
- focused unit and integration tests;
- compatibility tests across A2 and B1-B6;
- Ruff and scoped mypy;
- migration-head and read-only protected-database checks; and
- a final bounded DeepLuna Fast audit followed by independent local
  reproduction.

## B7 exit gate

B7 passes only when executable negative tests demonstrate that heuristic or
context-mismatched data cannot become exact, scoped-release, certification, or
release-grade claims, and every persisted decision can be reconstructed from
typed canonical support records.
