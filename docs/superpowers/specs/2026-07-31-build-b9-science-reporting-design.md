# Build B9 science authority API, UI, and reporting design

## Status

Frozen design for implementation.

Build: B9

Date: 2026-07-31

Authority: the canonical repository, B1-B8 constraints, executable tests, and
the Build B master prompt. This document does not grant scientific or release
authority.

## Problem

B1-B8 store scientific evidence and authority in typed, append-only records,
but the current API and dependency-free laboratory UI expose almost none of
that graph. Build B9 must make the graph inspectable without changing its
meaning.

The required presentation surfaces are:

- source documents and exact locators;
- observations;
- selected assertions;
- conflict sets;
- contextual thresholds and OAV boundaries;
- analytical methods, validation/QC, sequences, runs, peaks, GC-O events, and
  scoped analytical assessments;
- regulatory snapshots and findings;
- claim-authority decisions and their support links; and
- strict and exploratory science views.

The presentation must preserve exactly these evidence classes:

1. `MEASURED`
2. `LITERATURE_DERIVED`
3. `SUPPLIER_PROVIDED`
4. `EMPIRICALLY_CALIBRATED`
5. `MODEL_ESTIMATED`
6. `HEURISTIC`
7. `SPECULATIVE`
8. `UNKNOWN`

No endpoint, UI component, or report may collapse these labels into a single
confidence or coverage percentage.

## Baseline findings

- The production UI is the local, dependency-free static application in
  `backend/app/static`; the `frontend` directory contains no implementation.
- API v1 already uses explicit router modules and a `/lab` namespace.
- B1-B8 records already contain stable IDs, typed status fields, exact source
  references, locators, content hashes, review states, scoped decisions, and
  permitted wording.
- Several canonical records also contain local filesystem paths or source
  wording that should not be serialized by a general-purpose column dump.
- No B9 schema migration is required. B9 is a read-only projection over
  existing append-only authority.

## Chosen architecture

Use a hybrid read-only authority report:

```text
GET /api/v1/lab/science/authority?view=strict|exploratory
GET /api/v1/lab/science/report.md?view=strict|exploratory
```

The JSON endpoint is the canonical B9 representation. The Markdown endpoint
is deterministically rendered from that exact representation. The local UI
loads the JSON endpoint and presents the same sections and labels.

This shape is preferred over many resource endpoints because B9 needs one
cross-domain authority view, one consistent strict/exploratory policy, and one
testable no-flattening contract. It is preferred over a static report because
the API and UI must reflect the current canonical database.

## Modules

Create:

- `backend/app/schemas/lab_reporting.py`
- `backend/app/repositories/lab_reporting.py`
- `backend/app/services/lab_reporting.py`
- `backend/app/api/v1/endpoints/lab_reporting.py`

Modify:

- `backend/app/api/v1/router.py`
- `backend/app/static/index.html`
- `backend/app/static/lab.js`
- `backend/app/static/lab.css`
- `backend/tests/integration/test_lab_ui.py`

Create focused unit and integration tests.

## Response contract

The JSON document has a fixed schema:

```json
{
  "schema_version": "lab-science-authority-report-v1",
  "view": "strict",
  "authority_state": "READ_ONLY_NON_PROMOTING",
  "evidence_classes": [],
  "policy": {},
  "sections": [],
  "totals": {},
  "report_sha256": "..."
}
```

Each section has:

```json
{
  "key": "property_observations",
  "label": "Property observations",
  "included": [],
  "withheld": [],
  "total_count": 0,
  "included_count": 0,
  "withheld_count": 0
}
```

Each record has:

```json
{
  "id": "...",
  "created_at": "...",
  "evidence_class": "MEASURED",
  "strict_eligible": true,
  "strict_reason_codes": [],
  "authority": {},
  "provenance": {},
  "facts": {}
}
```

There is no `confidence`, `confidence_percent`, `coverage_score`,
`overall_score`, or equivalent field.

## Strict and exploratory semantics

Both views retain every record.

- `strict`: records with explicit canonical scoped authority appear in
  `included`; all others appear in `withheld`.
- `exploratory`: every record appears in `included`; `withheld` is empty.

This distinction prevents two opposite failures:

1. exploratory material cannot silently enter strict use; and
2. strict mode cannot erase unknowns, conflicts, rejected records, or missing
   evidence from inspection.

`strict_eligible` is derived only from existing typed canonical fields. It is
not inferred from row presence, source count, age, or a numeric score.

Initial strict predicates:

- source document: `review_state == REVIEWED`;
- source extraction: its source is reviewed and its latest workflow state is
  `ACCEPTED_FOR_SCOPED_USE`;
- property observation:
  `review_state == ACCEPTED_FOR_SCOPED_USE` and evidence class is not
  `HEURISTIC`, `SPECULATIVE`, or `UNKNOWN`;
- selected assertion:
  `authority_state == AUTHORIZED_FOR_SCOPED_PROPERTY`;
- property conflict set: eligible only when
  `state == RESOLVED_FOR_SCOPE`; unresolved conflicts remain withheld and
  visible;
- threshold context: its observation is strict-eligible and matrix context is
  not unknown;
- OAV assessment: `strict_science_mode == true` and `status == COMPUTED`;
- knowledge rule: accepted, active, executable, non-heuristic, and without a
  blocking contradiction;
- analytical method: `status == VALIDATED_FOR_SCOPE`;
- method validation/QC: `result == PASS`;
- analytical sequence: `status == ACQUIRED`;
- analytical run: `disposition` is `ACCEPTED` or `QUALIFIED`;
- analytical peak: identity state is
  `CONFIRMED_AUTHENTIC_STANDARD` or
  `STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM`;
- GC-O event: assessor is `QUALIFIED`;
- analytical claim assessment: `decision == SUPPORTED_FOR_SCOPE`;
- regulatory snapshot: `result_state` is
  `PASS_FOR_DECLARED_SCOPE` or `FAIL`;
- regulatory finding: its parent snapshot is strict-eligible;
- claim-authority version: decision is `ALLOW_EXACT`, `ALLOW_SCOPED`, or
  `BLOCK`; and
- claim support link: its parent claim decision is strict-eligible.

Negative authority (`BLOCK` or `FAIL`) is still strict evidence. Strict means
the scoped decision is authoritative, not that the outcome is favorable.

## Evidence-class policy

Evidence labels are preserved when a model already stores one. For records
without an explicit evidence class, the projection uses conservative,
code-owned mappings:

- local analytical or sensory source: `MEASURED`;
- peer-reviewed paper, standard, regulation, official guidance,
  authoritative database, review, or patent: `LITERATURE_DERIVED`;
- supplier COA/specification/SDS/certificate/declaration:
  `SUPPLIER_PROVIDED`;
- passed method validation: `EMPIRICALLY_CALIBRATED`;
- model-selected assertion: `MODEL_ESTIMATED`;
- expert note, secondary reconstruction, or community observation:
  `HEURISTIC`;
- AI-generated hypothesis: `SPECULATIVE`; and
- no exact mapping: `UNKNOWN`.

Linked records may inherit only an exact upstream evidence class. Ambiguous
or missing linkage becomes `UNKNOWN`; the projection never guesses a stronger
class.

Authority decisions remain separate from evidence classes. An
`ALLOW_SCOPED` decision is not itself relabeled `MEASURED`.

## Sections and safe field allowlists

The repository queries explicit model classes in stable `(created_at, id)`
order. The service projects explicit allowlists; it never serializes every
SQLAlchemy column generically.

Required sections:

- `source_documents`
- `source_extractions`
- `property_observations`
- `selected_assertions`
- `property_conflict_sets`
- `contextual_thresholds`
- `oav_assessments`
- `knowledge_rules`
- `rule_contradictions`
- `analytical_methods`
- `analytical_method_validation`
- `analytical_sequences`
- `analytical_runs`
- `analytical_peaks`
- `gc_o_events`
- `analytical_claim_assessments`
- `regulatory_snapshots`
- `regulatory_findings`
- `claim_authority_decisions`
- `claim_authority_support`

Provenance allowlists include stable source IDs, source version IDs,
extraction IDs, exact locator objects, source artifact digests, content
digests, upstream digests, policy versions, review pseudonyms, and review
times when present.

The API must not expose:

- `preserved_artifact_path`;
- `raw_source_path`;
- filesystem database paths;
- environment or configuration values;
- source credentials or tokens;
- unrestricted ORM internals; or
- original source wording when a locator and normalized value are sufficient.

## Exact locators

The report preserves locator structures, not only source titles:

- source default locator;
- extraction locator;
- property source locator;
- analytical method/validation source locator;
- knowledge-rule source locator and JSON pointer; and
- source references embedded in claim decisions/support.

Missing required locator data does not become an empty authoritative locator.
The record remains visible but strict-withheld with an explicit reason code.

## Markdown report

Markdown is generated from the JSON response after its content hash is
computed. It includes:

- view and non-promoting authority statement;
- the eight-label legend;
- per-section included/withheld counts;
- each record's stable ID, evidence class, authority fields, reason codes,
  exact locator summary, and content/source digests; and
- permitted wording where the canonical model supplies it.

The renderer must be deterministic and must not calculate percentages.

## UI

Add a `Science` navigation view with:

- strict/exploratory toggle;
- complete eight-class visual legend;
- explicit statement that strict-withheld records remain visible;
- per-section included/withheld counts;
- evidence-class badges;
- authority and reason labels;
- expandable provenance/facts JSON for local inspection; and
- JSON and Markdown download links tied to the selected view.

Rendering uses `textContent` or escaped HTML only. Record-provided values must
never be inserted as raw HTML.

## Negative tests

Tests must prove:

- all twenty sections exist even when empty;
- all eight evidence labels are present in API metadata and UI text;
- strict mode separates, but does not erase, unknown/heuristic/speculative
  records;
- exploratory mode includes those same records without changing their
  evidence class or strict eligibility;
- an unresolved conflict and a `BLOCK` decision have different semantics;
- a strict-negative `BLOCK` decision remains included;
- a missing exact locator is strict-withheld;
- model evidence cannot become measured evidence;
- no forbidden aggregate confidence/coverage key occurs recursively;
- local filesystem fields are absent recursively;
- JSON and Markdown are deterministic for the same database state;
- Markdown and UI do not contain a confidence percentage;
- API values are escaped in UI rendering; and
- no endpoint mutates a B1-B8 table.

## Compatibility and gate

Run focused B9 schema/service/API/UI tests, then the complete A2-B9
compatibility set, Ruff, mypy, existing static UI tests, secret/ANSI scans,
protected database hashes, and a fresh bounded DeepLuna Fast final audit.

B10 may begin only after the B9 gate package is committed and every exact B9
path is clean.
