# Perfume-Chem Geraniol Source-Lineage Packet - 2026-08-09

## Outcome in plain language

The highest-value Geraniol B1/B2 lineage gap is now implemented and locally
verified.

- Perfume-Chem can reproducibly compare the exact Keller/Vosshall supporting
  workbook with the pinned DREAM `TrainSet.txt` for Geraniol.
- All 98 Geraniol rows and all 2,058 retained response cells satisfy a fixed,
  executable transform contract; there are zero incompatible cells.
- The validator distinguishes deterministic transformations from 18 cases in
  which the workbook value `1` cannot independently distinguish DREAM `10`
  from `100`.
- Those 18 cells remain explicitly labeled as published-derivative
  disambiguations. They are not presented as independently reconstructed
  values.
- The source relation therefore remains scoped `CITES`, with authority
  `WITHHELD_UNKNOWN`. It is not promoted to `DERIVED_FROM`.
- No canonical source or observation row was written. No inventory, database,
  ODT, OAV, safety, similarity, formula, or release authority changed.

Final staging state: `VERIFIED_STAGED`, `canonical_rows_written=0`,
`promotion_allowed=false`, and `authority_changed=false`.

## Literature and repository-history basis

The 2016 Keller/Vosshall study reports 0-100 slider ratings and 20 semantic
odor descriptors. The 2017 DREAM report describes 49 subjects, 476 molecules,
338 training molecules, and 21 retained response attributes: intensity,
pleasantness, and 19 descriptors.

Primary sources:

- [Keller and Vosshall 2016, BMC Neuroscience](https://pmc.ncbi.nlm.nih.gov/articles/PMC4977894/)
- [DREAM olfaction challenge](https://dream-olfaction.github.io/)
- [Keller et al. 2017, Science](https://doi.org/10.1126/science.aal2014)
- [Official commit that first added the challenge data](https://github.com/dream-olfaction/olfaction-prediction/commit/1cd1343122408bf6fdb36f7628d9d1b1b8c202d9)

The official repository history contains the initial challenge-data addition,
but no transform implementation or correction history that resolves how an
ambiguous workbook value `1` became DREAM `10` in some cells and `100` in
others. This absence is why the implementation records compatibility with the
published derivative without claiming exact independent reconstruction.

The provenance design also follows the [FAIR Guiding
Principles](https://www.nature.com/articles/sdata201618), [W3C
PROV-O](https://www.w3.org/TR/prov-o/), [DataCite Metadata Kernel
4.4](https://schema.datacite.org/meta/kernel-4.4/doc/DataCite-MetadataKernel_v4.4.pdf),
and [RO-Crate 1.3](https://www.researchobject.org/ro-crate/specification/1.3/metadata):
source bytes, contextual citations, derivation claims, and authority are kept
separate and hash-bound.

## Full-corpus research finding

Before implementing the Geraniol tranche, the preserved workbook and DREAM
training set were compared across the entire available corpus.

- All 35,084 DREAM rows mapped uniquely to workbook rows using CID, trimmed and
  case-folded odor label, dilution, and DREAM subject ID.
- Across all 21 retained response fields, every nonblank disagreement was in a
  descriptor field.
- Every such disagreement was either a deterministic `2->20` through `9->90`
  trailing-zero restoration or an ambiguous `1->10` / `1->100` case.
- The executable validator intentionally remains scoped to the first approved
  Geraniol tranche rather than silently generalizing that research result to
  canonical authority for the full corpus.

## Exact Geraniol value-lineage result

| Classification | Cells |
|---|---:|
| Matched rows | 98 |
| Compared retained cells | 2,058 |
| Exact numeric | 407 |
| Source blank to target zero | 1,355 |
| Source blank to target blank | 260 |
| Deterministic `2-9 -> 20-90` restoration | 18 |
| Published derivative `1 -> 10` | 3 |
| Published derivative `1 -> 100` | 15 |
| Incompatible | 0 |

The 36 recoded cells occur across 29 rows. All 18 ambiguous source cells are
numeric `1`, use the workbook's General number format, and share the same
style. No cell-level workbook metadata independently distinguishes `10` from
`100`.

The fixed transform contract is:

1. Join by integer CID, trimmed/case-folded odor label, exact dilution text,
   and integer DREAM subject ID.
2. Treat a missing strength value plus the declared cannot-smell response as
   DREAM intensity zero.
3. Preserve missing valence as missing.
4. Preserve a missing descriptor as missing when source strength is missing.
5. Map a missing descriptor to zero when source strength is present.
6. Accept integral descriptor values `2-9` mapping to `20-90` as deterministic
   trailing-zero restoration.
7. Accept source value `1` mapping to `10` or `100` only as a
   published-derivative disambiguation.
8. Reject every other difference and reject any expected-count drift.

The result is compatible and reproducible, but
`exact_reconstruction_without_published_derivative=false` and
`source_level_derivation_relation_allowed=false`.

## Preserved source packet

| Source | Artifact SHA-256 | Manifest SHA-256 | Staged bundle SHA-256 | Rights state |
|---|---|---|---|---|
| Keller/Vosshall full-text XML | `7e7f309706f52bafc110f2ec36dce7cc8a00b9f177cd678db6e417b1baaabc72` | `259cac4febf15faa7bb696be98f3e77ce82bdd019c2b26ff5edd210611bcb792` | `db5867da0de7f8db386c55dfe19bfddf56c5e173d8f4edfdc8a716dfe0a4f599` | `PERMITTED`, CC BY 4.0 |
| Keller/Vosshall supporting XLSX | `efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62` | `e1d4685caf3d6dfb5341a07a8e9e2b48ccb923c890a6ebb9daf8270ff212f195` | `67eebb5754ec50927d67bcdf930bb1e7114532f9d484662eabdb111e049d8aee` | `PERMITTED`, CC0 1.0 data waiver |
| PubChem CID 637566 properties JSON | `d21151198ff537595597c19f6cf841751df808782768663a2b1b9ba5b22b00c6` | `5dbd21105dab85523fb09dce13f61f1fa09d28197aa0b6c0c8587f8f1f32d3af` | `d3ddfbbc77069f3232539d0ace42d816526dca2a995c1d778b161f589623aa38` | `RESTRICTED`; contributor-level review required |
| PubChem CID 637566 CAS JSON | `629488ac5296b9d35a46bda8ea17494234f3b6f05af7a3c6209d037a9ae3e79a` | `1b0361725dedb437e0907ffa1fee68dc714a36f5bf863f68982db50274d2359e` | `03d4cd2bdbb05b232e20c64742c31db6e6362dd1a952dceb5d2b2e6acce5dc36` | `RESTRICTED`; contributor-level review required |

Article text and supporting-data rights are kept distinct, as stated in the
[peer-reviewed article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4977894/).
PubChem remains conservative because its [download
guidance](https://pubchem.ncbi.nlm.nih.gov/docs/downloads) notes that records
come from multiple contributors with potentially different source rights.

EPA identity remains on HOLD. Earlier official ChemExpo page captures changed
bytes between consecutive requests, and the official CTX chemical-detail API
requires an API key. No credential was requested, stored, or exposed. See the
[EPA CTX API documentation](https://comptox.epa.gov/ctx-api/docs/).

## Implementation

The change stays inside the existing ingestion path; no new pipeline script was
created.

- `engine/ingestion/scientific.py` now contains a bounded, fail-closed stdlib
  OOXML reader and the fixed `keller_vosshall_xlsx_to_dream_v1` adapter.
- The workbook parent must already be an accepted, self-hashed related source.
  Its source candidate, manifest, bundle, artifact ID, artifact SHA-256,
  runtime root containment, and fresh file hash must all match.
- The OOXML reader rejects unsafe or duplicate members, encryption, unsupported
  compression, excessive member/count/ratio limits, unsafe or external sheet
  relationships, malformed row/cell references, formulas, error cells,
  duplicate headers, and missing fixed headers.
- It emits a self-hashed
  `b1_value_lineage_validation_candidate_v1` report and binds the validation ID
  and record hash into both B1 extraction and B2 observation provenance.
- The DREAM manifest now declares the exact parent bindings, key/response maps,
  expected counts, lineage state, and authority limit.
- Six focused tests cover the accepted contract, missing parent, parent hash
  drift, incompatible values, unsafe OOXML paths, and byte-identical replay.

## Emitted evidence

| Evidence | Value |
|---|---|
| Primary manifest SHA-256 | `6d45896975d5e385051bf78d1f857220b1f882cf7fffbe197d29aa8aa156e8fe` |
| Deterministic bundle SHA-256 | `fa7bd7908183f7d90d69f1749fa52662e952adc9e8c935e32179633b5923dc31` |
| Validation ID | `lin-3a23c7e2009f840fab3baf334493e743` |
| Validation record SHA-256 | `43b956ca077a3feb560989f8f6050a8deade51d184e5336f92b05ece1494263d` |
| Transform contract SHA-256 | `e285b0492c3f33c8727dffd693cbb0be8dba14902a1df454074c20ed5e551973` |
| Validation input SHA-256 | `df6827b1fa014d1478a12367b7155345c6c1157dd9aea9c7a6b7225c9f0aa594` |
| Validation output SHA-256 | `d4e55fa7a9701ae955533128ac3ecc5b921e67abddb185d84a00583afc51f745` |

The generated bundle contains one primary source candidate, four scoped
`CITES` candidates, two B1 extraction candidates, two B2 observation
candidates, and one value-lineage validation candidate. The workbook citation
now supports `observation_tranche.value_lineage_validation`; it does not assert
source-level derivation.

## DeepLuna Chat debugging and review

DeepLuna Chat was the only provider route. DeepLuna Fast, alternate providers,
Codex subagents, and fallback routing were not used.

- Fresh exact-project health was `READY` with no active reads, writes, queued
  jobs, reservations, or unknown reservations before transmission.
- Read-audit job `DS-c5c03ad0c818e340996db664f64fb28a` completed all five
  required reads but failed closed with `MAXIMUM_PROVIDER_CALLS_EXHAUSTED`.
  The trace showed a malformed `finish_handoff` argument shape on the second
  provider turn, so no final handoff from that run was accepted.
- A narrowed one-call conceptual review,
  `DS-9833aa8da1cb275705ed13e53bd55101`, correctly returned
  `BLOCKED/UNRESOLVED` because the `1->10/100` scientific distinction cannot be
  recovered from the source workbook alone. It endorsed the smallest safe
  staging-only design: exact parent/hash binding, bounded OOXML parsing,
  self-hashed lineage evidence, provenance binding, retained `CITES`, retained
  `WITHHELD_UNKNOWN`, and zero canonical rows.
- Sol independently implemented and accepted only the locally verified parts
  of that advice. The failed handoff and ambiguity boundary are retained as
  debugging evidence rather than rewritten as a provider success.
- Read-only exact-project postflight remained `READY`: active reads/writes/queue
  `0/0/0`, open and unknown reservations `0/0`, running/queued/validating jobs
  `0/0/0`, and unknown transmissions `0`.

## Backup and verification evidence

Before edits, a path-preserving archive was created and restoration-verified:

- `archive/geraniol-value-lineage-prechange-20260809T202252+0700.zip`
- 33,308 bytes
- SHA-256 `47f603ac38df5e0b152a3d5386fd91ead6f02032013ae9fdc591d2e7ecb47500`
- Five archived paths restored byte-for-byte in the canary directory.

Verification completed:

- Dry-run against the real DREAM data and 9,461,137-byte workbook:
  `VERIFIED_STAGED`, no rejections.
- Actual run: `VERIFIED_STAGED`, no rejections, zero canonical rows.
- Independent replay: all 12 generated report files were byte-identical.
- Scientific ingestion tests: `29 passed`.
- Focused value-lineage tests: `6 passed`.
- Ruff: all checks passed for the changed Python files.
- Python compile check: passed.
- Protected hashes remained unchanged:
  - `inventory.txt`: `dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec`
  - `data/perfumery_kb.db`: `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`
  - DREAM `TrainSet.txt`: `ae43841013a9c5ecb3975953b85e5965663d416d2445178e86ad577d907575a0`
  - Keller/Vosshall workbook: `efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62`

The full project verifier was not run because this slice changes no formula,
release, publication, canonical database, or scientific-authority state.

## Linked-chat notification

The bridge registry already links the work hub conversation
`6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf` to this Codex task
`019fe3a3-3cca-7462-b8e9-e315015e95df`. Direct cross-task messaging was tried,
but both the read and send operations returned `No handler registered`; no
direct delivery is claimed.

A validated durable outbox packet was therefore published at
`chat_bridge/complex_perfumery/outbox/20260809T204452+0700-codex-geraniol-value-lineage-v1.json`.
Its JSON/schema-key contract and six referenced content hashes were verified.
Its acknowledgement remains `accepted=false` and `read_at=null` until the work
hub actually reads it.

## Remaining holds and next best addition

1. Keep the value-lineage result staged and `CITES` unless a versioned primary
   preprocessing artifact resolves the `1->10/100` ambiguity.
2. Generalize the same fixed-contract validator to the full 35,084-row corpus
   only as a separately reviewed staging tranche with expected-count and
   replay gates; do not infer authority from the Geraniol result.
3. Obtain a stable, versioned EPA identity payload through an approved local
   API key or official export without putting credentials in manifests, URLs,
   logs, or reports.
4. Complete supplier/lot/assay/carrier/CoA/SDS/TDS and chain-of-custody evidence
   before connecting chemical-entity evidence to owned Geraniol stock.
5. Review PubChem contributor-level provenance and rights before redistribution
   or canonical identity promotion.

Current authority remains `WITHHELD_UNKNOWN`; B1/B2 canonical loading is not
authorized.
