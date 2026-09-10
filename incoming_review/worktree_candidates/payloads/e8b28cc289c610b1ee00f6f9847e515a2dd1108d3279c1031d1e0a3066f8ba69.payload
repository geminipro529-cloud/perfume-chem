# Perfume-Chem scientific data integration map

Date: 2026-08-09  
Status: first safe ingestion slice implemented and focused-verified; canonical promotion remains disabled

## Decision

Perfume-Chem should use a local-first, manifest-gated evidence pipeline. External
datasets are inputs to the existing B1-B8 scientific authority layers; they do
not become a second authority database and they never overwrite canonical
material, formula, inventory, safety, or generated-artifact state directly.

The first change therefore hardens the existing external-data importer around
four invariants:

1. every artifact is bound to an immutable revision or content snapshot;
2. every local byte sequence must match a declared SHA-256 and byte count;
3. license and reuse state are explicit and archive/file restrictions survive;
4. output is staging-only, deterministic, and incapable of scientific promotion.

This is the smallest change that makes later Pyrfume, DREAM, M2OR, PubChem,
regulatory, and supplier evidence reusable without silently manufacturing
authority.

## Why this method is supported

- The [FAIR principles](https://doi.org/10.1038/sdata.2016.18) require rich
  metadata, persistent identifiers, clear usage licenses, provenance, and
  domain-relevant standards.
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) separates entities, activities,
  and agents. Perfume-Chem already has a compatible provenance shape, so source
  bytes, parsing, review, and selection should remain separate events.
- [DataCite Metadata Schema](https://schema.datacite.org/) supplies useful
  identifier, creator, publisher, date, version, rights, and relation concepts.
  Perfume-Chem should map the needed fields rather than copy the full schema.
- [RO-Crate 1.3](https://www.researchobject.org/ro-crate/specification.html)
  supports packaging datasets with files, rights, and related resources. A
  minimal Perfume-Chem manifest provides the same critical closure without
  making JSON-LD a first-slice dependency.
- Pyrfume's [archive design](https://pyrfume.org/pyrfume/design-scheme.html)
  uses a machine-readable `manifest.toml`, separates stimulus objects from
  subject behavior, and preserves archive-specific files and metadata. The
  2024 [Pyrfume data descriptor](https://www.nature.com/articles/s41597-024-04051-z)
  also emphasizes exact stimuli, conditions, identifiers, raw/processed files,
  and archive-specific citations and credits.
- [Pooch 1.9](https://www.fatiando.org/pooch/latest/hashes.html) verifies local
  and downloaded files against declared hashes and fails on mismatches. It is a
  focused optional fetch dependency; it does not own scientific validation.
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12) is the current
  released JSON Schema dialect. The first slice uses dependency-free Python
  validation to avoid creating a third schema-authority path; a published JSON
  schema can be added only after the repository's schema-registry authority is
  resolved.

## Live integration scope

The inventory-first gate has three deliberately distinct counts for the 235
currently owned entries, including solvents:

| Resolution scope | Resolved | Gaps | Meaning |
|---|---:|---:|---|
| Canonical YAML registry | 221 | 14 | Required before a material is represented in the structured data spine. |
| Runtime known (`registry OR profile`) | 226 | 9 | Legacy profile fallback can model the label, but is not canonical identity. |
| Grade-preserving identity text (`registry OR profile`) | 223 | 12 | Preserves botanical, grade, strength, and product-bearing text instead of stripping it. |

These counts must not be collapsed. A runtime fallback is not evidence that an
exact supplier product, natural, grade, or stock solution has been identified.

## Source priority map

| Priority | Source class | Recommended use | Authority boundary |
|---|---|---|---|
| A1 | Supplier CoA, SDS, specification, IFRA certificate, and lot GC-MS/GC-O | Owned trade products, naturals, purity, lot composition, restrictions | Primary for the exact supplier product or lot only. |
| A2 | [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) | CID, structure, identifiers, computed molecular properties | Exact molecules only; never map a trade blend or natural by fuzzy name. |
| A3 | [EPA CompTox APIs](https://comptox.epa.gov/ctx-api/docs/) | DSSTox identity, physicochemical and hazard records | Chemical identity/property evidence, not odor authority. |
| A4 | [IFRA Standards](https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards/ifra-standards-documentation), [EU 2023/1545](https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng), and [CosIng](https://single-market-economy.ec.europa.eu/sectors/cosmetics/cosmetic-ingredient-database_en) | Versioned regulatory snapshots and ingredient names | Effective date and jurisdiction are mandatory; CosIng presence is not approval. |
| B1 | [Pyrfume](https://github.com/pyrfume/pyrfume-data) | Curated stimulus, behavior, physics, and literature archives | Pin repository/archive revision and preserve each archive's rights. Repository MIT does not erase upstream restrictions. |
| B2 | [DREAM Olfaction](https://github.com/dream-olfaction/olfaction-prediction) | Reproducible human psychophysics benchmark | Ratings are not ODT, OAV, vapor pressure, or perfume similarity authority. |
| B3 | [Principal Odor Map data](https://zenodo.org/records/7992168) | Reproducible embedding benchmark and external validation | Keep model outputs separate from measured observations. |
| B4 | [M2OR](https://pmc.ncbi.nlm.nih.gov/articles/PMC10767820/) | OR-molecule assays, concentrations, cell lines, response and EC50 context | Preserve assay type, species, receptor, concentration, responsive/non-responsive state, and source locator. |
| C1 | [Flavornet](https://flavornet.org/), FlavorDB, EssOilDB, AromaDB, OlfactionBase | Discovery, natural-source context, descriptor cross-reference | Secondary discovery until original measurement, identity, and rights are recovered. |
| Restricted | NIST SRD, proprietary descriptor collections, supplier portals, commercial books/databases | Citation and targeted evidence where licensed | Do not bulk redistribute or infer a permissive license. [NIST SRD policy](https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications) applies. |

## Canonical flow

```mermaid
flowchart LR
    A["Immutable external bytes"] --> B["Source manifest: revision, rights, SHA-256"]
    B --> C["Verified raw archive"]
    C --> D["Parsed candidate records"]
    D --> E["Exact identity, grade, lot, and stock resolution"]
    E --> F["B1 source and extraction records"]
    F --> G["B2 typed observations with units and context"]
    G --> H["B3 contextual thresholds or later scientific layers"]
    H --> I["Conflict sets and human-scoped selection"]
    I --> J["Generated YAML, JSON, SQLite, Parquet, or FAISS projections"]
    J --> K["Formula, safety, optimization, and reporting consumers"]
```

The first implementation stops between B and F. It verifies exact bytes and
emits neutral B1 staging candidates. It writes no backend rows and does not
select a B2 observation.

## Manifest contract

Each source manifest must carry:

- schema version and stable source ID;
- title, source type, issuing organization/authors, language, and independence group;
- DOI/repository/database identifiers;
- immutable revision kind and value;
- timezone-aware retrieval timestamp;
- explicit rights state, license/reuse restriction, license URL, and redistribution flag;
- one or more relative artifact paths, immutable source URLs, roles, media types,
  byte counts, and SHA-256 digests;
- exactly one or more primary-data artifacts for B1 candidate generation;
- a declared transformation module/version and dataset-context limitations.

Mutable selectors such as `main`, `master`, `latest`, or Hugging Face
`resolve/main` are rejected. Relative paths must remain inside the explicitly
supplied source root. Protected canonical paths are never valid output or fetch
destinations.

## Observation contract for the next slice

No B2 observation may be promoted without all applicable fields:

- exact identity scope: molecule, stereoisomer/isomeric mixture, trade grade,
  supplier product, supplier lot, stock solution, physical dose, or natural;
- structure/identifier fields appropriate to that scope;
- property type and typed value (`NUMERIC`, `CATEGORICAL`, `INTERVAL`,
  `DISTRIBUTION`, or `CENSORED`);
- original and canonical units;
- matrix, phase, temperature, pressure, concentration/dose, purity, route,
  endpoint, assay/method, statistic, replicate count, and uncertainty where relevant;
- B1 source version and extraction-record locator;
- measured, literature-derived, supplier-provided, model-estimated, heuristic,
  or unknown evidence class;
- conflict membership and a human-reviewed scoped selection or explicit hold.

Pure molecules, stereoisomers, trade products, naturals, and diluted stocks are
not interchangeable identity scopes. InChI is useful for defined covalent
molecules, but the [InChI technical FAQ](https://www.inchi-trust.org/technical-faq/)
states that mixtures generally cannot be represented; trade blends and naturals
therefore require first-class product/composition identity.

## RED gates

The importer must reject or quarantine when any of these is true:

- missing or mutable revision;
- missing/unknown rights state;
- absolute path, traversal, symlink escape, or protected destination;
- missing artifact, byte-count mismatch, or SHA-256 mismatch;
- duplicate artifact ID/path or no primary data artifact;
- URL points at a mutable branch or latest alias;
- attempt to overwrite a non-identical staging report;
- attempt to write canonical backend/YAML/JSON/SQLite/FAISS state;
- name-only or ambiguous-CAS identity match;
- missing unit, matrix, method, concentration, condition, or uncertainty required
  for the claimed property.

## GREEN gates

The first slice is accepted only when:

- all manifest fields validate;
- every selected local file matches its exact revision's byte count and SHA-256;
- rights are permitted or explicitly restricted (never unknown);
- output is deterministic across replay;
- the receipt says `authority_changed=false`, `canonical_rows_written=0`, and
  `promotion_allowed=false`;
- a dry run performs no filesystem writes;
- protected database, knowledge graph, material properties, and embedding hashes
  remain unchanged;
- focused ingestion tests and Ruff pass.

## Ordered implementation

1. Add a dependency-light `engine.ingestion.scientific` library contract.
2. Replace the existing fixed-path/downloading behavior in
   `scripts/integrate_external_data.py` with manifest, source-root, output-dir,
   dry-run, and optional exact-hash fetch requirements.
3. Add `pooch>=1.9,<2` as the root `data` optional dependency; do not add
   Pyrfume, DuckDB, PyArrow, or cloud storage yet.
4. Add a pinned DREAM canary manifest for the exact local `TrainSet.txt` bytes
   at Git commit `fb47cb343cdfd5cd8b06b33161dfa8b82c0319c6`.
5. Verify the canary in an ignored output path and prove deterministic replay.
6. Next, resolve the 14 canonical-registry gaps with explicit `UNKNOWN` where
   supplier/grade evidence is missing.
7. Build the first B1/B2 tranche from exact PubChem/CompTox identity plus
   supplier evidence for owned, formula-used, high-impact materials.
8. Add pinned Pyrfume and M2OR adapters only after one inventory-first tranche
   passes conflict and review gates.
9. Add Parquet plus DuckDB only when versioned candidate tables are large enough
   that columnar querying has measured value. DuckDB can query Parquet directly
   with schema and file metadata inspection, but it is not needed for the first
   235-item inventory slice: [official Parquet documentation](https://duckdb.org/docs/stable/data/parquet/overview).

## DeepLuna Chat reliability hardening

The bounded DIRECT_PRO review job `DS-8304adacab636b5d9ffddebfafdfd198`
failed closed without changing files. Its first required read requested 867
lines, while the repository tool permits at most 400 lines per call. Because
the project contract permits two provider calls and reserves the second for the
final handoff, the worker had no recovery turn after that invalid read.

Future Chat work is now host-preflighted:

- `.opencode/scripts/cheapluna-contract.mjs` normalizes explicit line ranges,
  resolves bounded `end=null` ranges, merges overlap, splits reads at 400 lines,
  counts selected UTF-8 evidence, and rejects tasks above 15 KiB;
- the same preflight enforces `PRO`/`REASONING`, `DIRECT_PRO`, `NO_LUNA`, one
  attempt, at most two provider calls, a USD 0.08 ceiling, and the runtime's
  3,000-8,192 output-token envelope;
- the direct CLI applies normalization before submission, while the MCP budget
  hook rejects unchunked, over-budget, or misrouted contracts before provider
  transmission;
- eight local Node regression tests cover chunking, range/path/budget failures,
  route and output-token failures, and MCP-hook rejection/acceptance.

A follow-up canary exposed the 3,000-token runtime floor while its contract
still requested 2,500; admission stopped locally before a provider call. The
preflight now catches that class as well. It was not resubmitted, in accordance
with the no-retry rule for deterministic admission failures. DeepLuna therefore
supplied no acceptance verdict for this slice; Sol's local tests, canaries, and
protected-hash checks remain the acceptance evidence.

## Non-goals

- no protected database rebuild;
- no material-properties regeneration;
- no vector-index rebuild;
- no automatic alias insertion;
- no sensory, similarity, safety, measured-headspace, or formula-release claim;
- no cloud database or tunnel dependency;
- no external dataset is treated as canonical merely because it is large or public.
