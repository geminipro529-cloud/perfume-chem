# Perfume-Chem data integration audit

Date: 2026-08-09 (Asia/Bangkok)

Status: **integration design ready; scientific data convergence not complete**

This report answers four questions:

1. What is already finished?
2. What data or evidence is still missing?
3. What can sensibly be installed or connected?
4. What is the safest way to integrate and regenerate the project data?

It is a read-only audit and design decision. No external value is promoted to
canonical authority by this report, and no protected database is replaced.

## Plain-language result

Perfume-Chem has already built the difficult *software control system* for
scientific data: immutable provenance, typed observations, conflict handling,
claim gates, regulatory snapshots, analytical-method records, and a single SQL
write authority. That part is unusually strong.

The actual scientific content has not caught up with that architecture. The
current repository still has several overlapping representations of the same
materials, sparse primary-source provenance, exact-identity gaps, stale derived
artifacts, and broad disagreement among YAML, Python profiles, ODT dictionaries,
generated JSON, and the protected SQLite knowledge base. The software can say
"unknown" honestly, but most of the legacy values have not yet been imported
through the new authority path.

The correct next move is therefore **not a bulk download and not a bulk
regeneration**. Integrate a small, source-pinned, inventory-first tranche into
the existing B1-B3 canonical tables; accept conflicts rather than averaging
them; then regenerate only derived projections from an exact manifest.

## Scope and evidence

The audit covered:

- repository architecture, dependency files, current inventory, and current
  working-tree boundaries;
- the YAML material spine, inventory registry, ingredient profiles, ODT data,
  generated material properties, knowledge rules, embeddings, and both SQLite
  databases;
- Build A, Build B, Build C11, and D0 verification evidence;
- disposable, isolated knowledge-base reconstruction and logical comparison;
- the existing Pyrfume, DREAM, and Hugging Face integration script;
- current app/plugin availability for Data Analytics, Context7, SciSpace,
  Consensus, Scholar Gateway, GitHub, HAPI MCP Registry, and MotherDuck;
- current primary literature and official documentation for Pyrfume, DREAM,
  the Principal Odor Map, PubChem, NIST, IFRA, EU allergen labeling, Pooch,
  and DuckDB.

The current working tree already contains unrelated user changes under
`tools/`, `chat_bridge/`, `incoming_review/`, and a formula card. They were not
modified by this audit.

## What is finished

| Area | Current result | Meaning |
|---|---|---|
| Canonical write authority | Finished | Laboratory Beta SQL records, `LabService`, and repository mixins are the sole persisted authority. Engine objects and reports are projections. |
| Build A convergence | `PASS_WITH_SKIPS` at its recorded commit | Recovery, serialization, quantity conservation, canonical hashing, operating modes, bottle/inventory operations, and artifact binding were implemented. |
| Build B authority framework | `PASS`; scientific release not granted | B1-B8 define 40 append-only table definitions for sources, observations, thresholds, rules, analytical evidence, regulation, claims, and backfill planning. |
| Scientific claim boundaries | Finished | Exact/scoped/advisory/withhold/block outcomes prevent missing or heuristic evidence from becoming an affirmative claim. |
| Build C model governance | Finished for software scope | Unsupported physical and biological models are explicitly withheld; ideal Raoult behavior remains a theoretical baseline, not validation. |
| D0 claim matrix | `PASS` for D0 software only | Claim contracts and method-authority policy exist. D1 experimental work has not started. |
| Protected-state controls | Finished | Protected SQLite paths have immutable checks, recovery archives, and isolated-test contracts. |
| Formula release protections | Active | Ppm/ODT/OAV, composite natural OAV, stock-rebase equivalence, OAV-per-time screening, inventory, and claim gates are present. |

Important qualification: the Build B migrations and backfills populated **zero
real canonical scientific rows** at the recorded completion point. The
framework is complete; the evidence migration is not.

## Current local data state

These counts are a 2026-08-09 working-tree snapshot, not the older sealed B0
baseline.

| Surface | Current observation | Decision |
|---|---|---|
| YAML material spine | 1,270 rows; 1,237 unique under the current exact-normalized audit; 30 duplicate identity groups | Keep as source/projection input, but deduplicate through identity records rather than deleting rows blindly. |
| Live inventory | 235 owned entries when solvents are included | This is the first integration scope. Do not backfill all supplier-catalog rows first. |
| Inventory resolution | 221/235 resolve to the runtime material registry; 14 remain unresolved | Resolve exact stock identity, grade, carrier, and strength before property promotion. |
| Runtime inventory flags | Raw YAML and generated flags drift from the live inventory | Recompute only after alias and stock identity reconciliation. |
| `ingredient_intelligence._PROFILES` | 282 entries | Legacy runtime projection; not an independent authority. |
| `ODT_DATA` | 339 entries; current audit flags 16 zero/extreme values | Adapt each useful threshold through contextual B1-B3 evidence before authority. |
| `material_properties.json` | 293 entries | Generated projection with stale inventory flags and cross-surface conflicts. |
| Knowledge rules | 2,408 current schema-validator records; 137 orphan material references | Keep advisory until exact identities and evidence bindings pass. |
| Protected `perfumery_kb.db` | SQLite `quick_check=ok`; protected SHA-256 unchanged | Do not replace. |
| Embedding index | `chunk_map.json` and `knowledge_index.faiss` both dated 2026-05-25 | Treat as stale until rebuilt from a manifest and tied to input hashes/model version. |
| Latest project verifier artifact | Dated 2026-08-02 | Historical evidence only; it predates the current Aug 7-9 data and code changes. |

### Data coverage

The current data-spine audit reports:

| Field | Non-null coverage |
|---|---:|
| CAS | 68 / 1,270 (5%) |
| SMILES | 15 / 1,270 (1%) |
| Molecular weight | 296 / 1,270 (23%) |
| logP | 218 / 1,270 (17%) |
| Vapor pressure | 293 / 1,270 (23%) |
| Antoine coefficients | 0 / 1,270 |
| Enthalpy of vaporization | 2 / 1,270 |
| Hansen parameters | 0 / 1,270 |
| Air ODT | 99 / 1,270 (8%) |
| Ethanol ODT | 81 / 1,270 (6%) |
| Olfactory-receptor targets | 0 / 1,270 |
| TRP targets | 50 / 1,270 (4%) |
| Hedonic data | 137 / 1,270 (11%) |
| IFRA values | 15 / 1,270 (1%) |
| Supplier information | 990 / 1,270 (78%) |

The high supplier coverage reflects a broad vendor catalog, not broad
scientific coverage. The YAML set includes at least 28 obvious workshops,
services, or other non-material catalog records and hundreds of supplier-only
rows. Those should be typed as catalog offerings or services, not forced into a
chemical-material schema.

### Cross-surface conflicts

For exact-normalized identities shared by the surfaces, the current audit found:

| Comparison | Conflicting values |
|---|---:|
| YAML vs Python profile vapor pressure | 14 |
| YAML vs Python profile logP | 75 |
| YAML vs generated JSON molecular weight | 21 |
| YAML vs generated JSON vapor pressure | 24 |
| YAML vs generated JSON logP | 76 |

Examples include materially different vapor pressures for Cedramber and Benzyl
Benzoate and implausible molecular-weight divergence for Dipropylene Glycol.
These are identity/provenance review cases, not candidates for automatic
averaging. Trade blends, naturals, solvents, stereoisomers, and pure compounds
must remain distinct scopes.

Only 17 YAML rows currently carry a non-null `vp_source`. Core provenance is
also sparse: the audit found source citations on only 21 CAS, 181 MW, 154 VP,
140 logP, 229 air-ODT, 218 ethanol-ODT, 18 density, 10 IFRA, and 9 structure
fields. A value being populated is therefore not the same as a value being
authoritative.

## Current generated-artifact decision

Two new disposable SQLite candidates were built in isolated temporary paths.
They were byte-identical to each other, which proves deterministic execution for
those inputs. They were **not** logically equivalent to the protected database:

- candidate material count: 1,294;
- protected material count: 1,285;
- 78 material rows added, removed, or changed in the current comparison;
- several existing science/population tables would fall to zero, including
  aging, climate, dose-response, evaporation, retention, masking, anosmia,
  mixture, OR-biophysics, skin-chemistry, and UNIFAC-related tables.

Therefore the protected database must not be regenerated in place. Determinism
is necessary but does not prove semantic equivalence or scientific correctness.

The JSONL knowledge-library builder also has a blocking implementation defect in
its family-archetype phase: it constructs `fam_entry` but writes `entry` for
`repair_pool`/`oav_targets` and emits `entry`. Do not run it against its fixed
output until that existing script is repaired and covered by a focused test.

The material-property generator is also unsafe for authoritative regeneration:
it executes at module import, performs live PubChem requests, and automatically
overrides MW/logP when values diverge. PubChem is valuable for compound identity
and computed properties, but an automatic compound-CID overwrite is not valid
for trade mixtures, naturals, grades, or ambiguous CAS/name mappings.

## External data already present

| Dataset | Local state | Scientific use |
|---|---|---|
| DREAM Olfaction Challenge | Repository/data bundle present; 35,084 response rows and 4,870 descriptor columns observed locally | Useful benchmark for single-molecule psychophysics. Keep concentration, subject, split, and source revision explicit. |
| Hugging Face molecular odor dataset | `train.csv` and labels present; validation/test files absent | Incomplete and unpinned. Quarantine from model acceptance and canonical data. |
| Pyrfume | Package not installed in the supported root environment | Strong optional archive adapter, but imports must be source-revision and manifest pinned. |
| Principal Odor Map | Not integrated as a canonical dataset | Useful external benchmark/embedding candidate. It does not replace measured VP, ODT, mixture, safety, or sensory evidence. |

The existing `scripts/integrate_external_data.py` is not release-safe. It writes
CSV files directly to fixed paths, uses unpinned Pyrfume archive state, downloads
Hugging Face files from `resolve/main`, and records no license, revision,
retrieval time, schema, or cryptographic digest. It should be strengthened in
place; Rule 2 forbids creating a new pipeline script.

## Current research findings

### Pyrfume and psychophysics

The 2024 Pyrfume data paper describes a unified archive spanning olfactory
psychophysics and biology. Its key design choice is to keep odor objects,
stimuli/conditions, subjects, and behavior separate, with molecules commonly
linked by PubChem CID. The project documentation requires each archive to have a
machine-readable `manifest.toml` listing sources, raw/parsed/processed files,
and processing code.

This is a good model for Perfume-Chem external archives, but CID alone is not
enough for stock identity. Perfume-Chem must add grade, stereochemistry, purity,
supplier, lot, carrier, dilution, matrix, concentration, method, temperature,
and endpoint where relevant.

Sources:

- [Pyrfume data paper](https://pubmed.ncbi.nlm.nih.gov/39532906/)
- [Pyrfume archive design](https://pyrfume.org/pyrfume/design-scheme.html)
- [Pyrfume public data repository](https://github.com/pyrfume/pyrfume-data)

The DREAM dataset remains a sound legacy benchmark for concentration-aware
single-molecule ratings, but it is not a headspace, mixture, threshold, or
regulatory dataset. The newer Principal Odor Map shows strong prospective
single-molecule odor-description performance, while its paper also documents
important data/code availability limits. Both should remain benchmark inputs,
not promoted material truth.

Sources:

- [DREAM Olfaction paper](https://pubmed.ncbi.nlm.nih.gov/28219971/)
- [DREAM challenge data and code](https://dream-olfaction.github.io/)
- [Principal Odor Map paper and data statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC11898014/)
- [Principal Odor Map reproducibility archive](https://doi.org/10.5281/zenodo.7992168)

A 2026 preprint, AROMMA, proposes joint embeddings for molecules and binary
mixtures. It is useful to monitor but is not a validated production dependency
or a replacement for concentration-resolved mixture measurements.

### Chemical identity and physical properties

Use PubChem PUG REST for standardized structures, CIDs, InChIKeys, formulas,
computed properties, and cross-references. Record the exact request, returned
CID/SID, retrieval date, response digest, and selection decision. PubChem asks
clients to remain below five requests per second and recommends bulk routes for
large retrievals.

Use NIST Chemistry WebBook first for measured vapor-pressure/Antoine and phase
change data where available, preserving temperature range, equation form,
units, original literature citation, and whether the value is measured or
estimated. Its current data release is marked 2025.

Sources:

- [PubChem PUG REST specification](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest)
- [PubChem PUG-View annotations](https://pubchem.ncbi.nlm.nih.gov/docs/pug-view)
- [NIST Chemistry WebBook SRD 69](https://webbook.nist.gov/chemistry/)
- [NIST WebBook data guide](https://webbook.nist.gov/chemistry/guide/)

### Regulatory data

As of this audit, IFRA Amendment 51 is the last formally notified complete
standard set. The Amendment 52 consultation closed on 12 June 2026; IFRA says
formal notification is expected toward the end of November 2026. Amendment 52
must therefore be modeled as a pending snapshot, not silently treated as
operative final limits.

EU Regulation 2023/1545 expands individual fragrance-allergen labeling and
retains the 0.001% leave-on and 0.01% rinse-off declaration thresholds, with
transition periods described in the regulation. Regulatory records need
jurisdiction, product category, amendment/regulation version, evaluation date,
effective date, supersession state, and source digest.

Sources:

- [IFRA Amendment 51 complete standards](https://ifrafragrance.org/publications/guidanceReferenceDocument/51st-amendment-document)
- [IFRA Amendment 52 consultation status](https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed)
- [EU Regulation 2023/1545](https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng)

### Analytics and reproducible downloads

DuckDB can query Parquet directly, inspect schemas and metadata, and push
filters/projections into the files. That makes it a good **derived analytics
layer** over immutable versioned exports. It should not become a second
canonical transactional store and MotherDuck should not be required for local
operation.

Pooch supports URL plus known-hash retrieval and local caching. It is a compact
fit for external dataset fetches, provided the project still writes its own
source manifest and refuses `known_hash=None` in accepted ingestion.

Sources:

- [DuckDB Parquet documentation](https://duckdb.org/docs/stable/data/parquet/overview)
- [Pooch retrieve documentation](https://www.fatiando.org/pooch/v1.8.0/retrieve.html)
- [Pooch 1.9 changelog](https://www.fatiando.org/pooch/latest/changes.html)

## App and connector decision

These are Codex/ChatGPT services, not Python dependencies inside the repository.

| Service | Current state observed | Recommendation |
|---|---|---|
| Data Analytics | Plugin installed/enabled; several optional app dependencies present | Keep app-level. Do not add it to repo requirements. Use only for bounded analysis of exported artifacts. |
| Context7 | Available and working | Keep app-level for current official library docs. DuckDB documentation resolved successfully. |
| SciSpace | Available and working | Use for discovery; verify claims against the paper/DOI before promotion. |
| Consensus | Available connector, but calls returned `INVALID_ARGUMENT` in this session | Do not depend on it for this integration. Re-test later; no scientific claim here relies on it. |
| Scholar Gateway | Available in the catalog but not installed | Do not install now. SciSpace, PubMed, and direct DOI sources cover the present need. |
| GitHub | Available; current installation search did not expose Pyrfume via the scoped connector | Use public upstream URLs/commits and record exact revision; connector installation is not repository provenance. |
| HAPI MCP Registry | Search returned no PubChem/chemistry server | Do not install an unreviewed chemistry MCP. Direct official APIs are safer and easier to pin. |
| MotherDuck | Connector requires reauthentication | No action needed. Local DuckDB is sufficient for the recommended first phase. |

## Package install decision

Nothing should be installed merely because it is available. The smallest
quality-preserving dependency set is:

| Package | Decision | Reason |
|---|---|---|
| `pooch` | **Recommended, after importer hardening** | Hash-verified, cached external downloads with a small dependency footprint. Pin in an optional data-ingestion extra/lock. |
| `pyrfume` | **Conditional** | Useful archive adapter. Pin package and archive revision; import selected archives into B1/B2 observations, never directly into runtime truth. |
| `duckdb` | **Recommended for phase 2 analytics** | Query immutable Parquet exports locally without another service. Derived/read-only only. |
| `pyarrow` | **Conditional with Parquet export** | Stable typed Parquet interchange from pandas; pin alongside DuckDB. |
| `pandera` | **Defer** | The project already has typed schemas and authority validation. Add only if a concrete dataframe contract cannot be expressed cleanly in existing validators. |
| `rdkit` | **Defer** | Valuable for structure normalization and modeling, but heavy and unnecessary for the first provenance tranche. Exact source identifiers come first. |
| `pubchempy` | **Do not add now** | Existing direct PUG REST access is sufficient and more transparent to manifest. |
| `polars`, `datasets`, `frictionless`, DVC | **Do not add now** | They duplicate current capabilities or add operational weight before a concrete need exists. |
| MotherDuck cloud | **Do not require** | It weakens the local-first boundary and is unnecessary for the present data volume. |

The root dependency declarations are currently inconsistent: `requirements.txt`
contains the broad runtime/model stack while root `pyproject.toml` declares only
PyYAML. Any package addition should first choose and document one supported root
lock/install path; backend Poetry remains a separate environment.

## Recommended integration architecture

Use the existing canonical services and tables. Do not add another canonical
database and do not create a new pipeline script.

```text
immutable external bytes
  -> source manifest + license + SHA-256 + retrieval/revision metadata
  -> raw archive (never edited in place)
  -> parsed candidate records
  -> exact identity/grade/lot resolution
  -> typed B2 observation with units, context, method, and uncertainty
  -> explicit conflict set and candidate selection
  -> scoped selected assertion
  -> generated YAML/JSON/SQLite/Parquet/FAISS projections
  -> formula and reporting consumers
```

Every accepted source manifest should include at least:

- source URL, DOI, repository and exact commit/tag/release;
- license and redistribution constraints;
- retrieval timestamp and SHA-256 of every raw file;
- parser/generator version and configuration hash;
- row count, schema version, units, null policy, and identity namespace;
- derivation links from raw to parsed to selected records;
- source independence group and evidence class;
- supersession and withdrawal state.

Every property observation should additionally bind:

- exact compound/material, stereochemistry, grade, purity, supplier, and lot;
- matrix, medium, concentration, route, endpoint, temperature, pressure, and
  method where applicable;
- value, unit, uncertainty/range, measured-vs-estimated state, and citation;
- whether it applies to a pure molecule, trade blend, natural composition, or
  diluted stock.

Generated artifacts must carry an input-manifest hash, generator commit/version,
configuration hash, deterministic seed where applicable, software versions,
creation time, and logical-diff summary. A matching byte hash is cache evidence;
it is not scientific acceptance by itself.

## Integration priority

### Phase 0 - make ingestion safe

1. Repair and test the existing JSONL builder's `fam_entry` defect.
2. Add dry-run/output-path/manifest requirements to the existing external-data
   importer and material-property generator; remove import-time execution and
   automatic authority-changing overwrites.
3. Define one root dependency/lock path and an optional `data` extra.
4. Resolve the 14 current live-inventory identity gaps.
5. Split vendor catalog services and opaque trade blends from pure material
   records. Preserve trade products as trade products; do not assign invented
   monomolecular physics.

### Phase 1 - inventory-first scientific backfill

Work in this order:

1. currently owned and available materials;
2. materials used in active formulas and release gates;
3. high-OAV/high-dose or IFRA-edge materials;
4. naturals requiring lot/composition evidence;
5. remaining supplier catalog only after the above converges.

For each tranche, import sources through B1, observations through B2, and
contextual thresholds through B3. Preserve all conflicting candidates. Require
human review for selected assertions that affect formula release or safety.

Suggested source precedence is property-specific:

- structure/identity: supplier identity plus PubChem standardized identifiers;
- measured VP/Antoine/delta-Hvap: NIST/original literature before estimates;
- stock density/composition: lot-specific supplier SDS/CoA before generic data;
- ODT: primary psychophysical literature with exact medium/method/endpoint;
- natural composition: lot GC-MS/GC-O before generic literature composition;
- IFRA/EU: dated official snapshots only;
- perceptual benchmarks: Pyrfume/DREAM/POM with subjects, concentrations, and
  train/test boundaries intact.

### Phase 2 - deterministic projections and analytics

1. Generate projections only to disposable paths.
2. Compare logical tables/rows, not only file hashes.
3. Require protected-path hash invariants during tests.
4. Accept and atomically promote only the intended diff.
5. Export canonical read-only snapshots to versioned Parquet.
6. Use local DuckDB views for joins, coverage, conflicts, and model datasets.
7. Rebuild FAISS only from an accepted manifest and record embedding model,
   revision, chunking policy, and source hashes.

### Phase 3 - scientific calibration

Do not promote headspace, OAV-per-time, longevity, sillage, mixture, receptor,
or hedonic models merely because more rows exist. Promotion requires
preregistered held-out observations, defined endpoints, representative matrices,
baseline comparison, uncertainty, and claim-specific acceptance gates.

## Regeneration matrix

| Artifact/action | Status now | Required gate |
|---|---|---|
| Data-spine audit and schema report | Safe | Read-only current-source run. |
| Disposable SQLite candidate build | Safe | Exact temporary path, protected hashes before/after, logical diff. |
| Protected `data/perfumery_kb.db` replacement | **Blocked** | Intended logical diff, no table loss, accepted source manifest, recovery archive, human acceptance. |
| `material_properties.json` regeneration | **Blocked** | Remove live auto-override/import side effects; source-bound candidate selection; temp output and diff. |
| `.opencode` JSONL knowledge library | **Blocked** | Repair `fam_entry`, focused test, manifest, disposable output. |
| FAISS/chunk map | Conditional | Accepted source snapshot plus embedding/chunk/model manifest. |
| Pyrfume archive import | Conditional | Pin archive commit/release and manifest; raw digest; B1/B2 adapter. |
| DREAM data use | Safe as quarantined benchmark | Record local source commit/hash, concentration/split semantics, license. |
| Hugging Face odor data use | **Blocked** | Complete train/val/test bundle, exact revision, license, checksums, schema audit. |
| IFRA refresh | Conditional and high priority | Keep Amendment 51 operative; store Amendment 52 as pending until formal notification. |

## Acceptance criteria for the next implementation slice

The first implementation slice should stop when all of these are true:

- no protected path changed unexpectedly;
- the 14 inventory gaps have explicit resolved or `UNKNOWN` outcomes;
- at least one small property tranche has complete B1/B2 lineage and conflict
  handling;
- every raw source has license/revision/retrieval/hash metadata;
- no generator performs an authority-changing overwrite from a name-only or
  ambiguous-CAS match;
- candidate outputs are deterministic and their logical diff is reviewed;
- root focused tests and the quick project verifier pass from the supported
  Python 3.11 environment;
- no scientific-release, safety-certified, measured-headspace, or sensory-match
  claim is made.

## Final decision

Perfume-Chem should install **nothing immediately** as part of this audit. The
next code change should harden the existing ingestion/regeneration surfaces and
then add `pooch` as the first optional dependency. Add `pyrfume` only for a
pinned archive tranche; add `duckdb` and `pyarrow` only when versioned Parquet
exports exist.

Do not rebuild the protected knowledge database, material-properties JSON,
JSONL knowledge library, or vector index from the current unconverged inputs.
The safest high-value work is the current 235-item owned inventory, beginning
with the 14 unresolved identities and the formula-used/high-impact materials.

## Verification and DeepLuna review

The supported Python 3.11 quick verifier was run after the report draft with a
separate ignored output path:

```text
.venv_py311_a0\Scripts\python.exe scripts\pipeline_audit.py \
  project-verify --quick \
  --output output/data_integration_audit_quick_verify.json --json
```

Result: **10 selected checks passed; 0 failed; 0 skipped**.

- engine compile, canonical-slice Ruff, and MyPy: PASS;
- formula artifact validation: PASS;
- scientific audit: 22 tests passed;
- material-data validation: 80 tests passed;
- knowledge-rule validation: 77 tests passed;
- golden formula regression: 13 tests passed;
- golden API regression: 1 selected test passed;
- golden fixture hash: unchanged.

This was intentionally a partial quick scope. The completion gate was
`NOT_EVALUATED`; backend-full, full engine shards, package builds, migrations,
backup/restore, Docker, and held-out sensory validation were not established by
this run. Laboratory Beta and scientific-release readiness therefore remain
blocked in this evidence packet.

The requested final DeepLuna Chat review could not be transmitted. A fresh
exact-project launch/preflight was attempted after the draft, but the protected
launcher reported:

```text
DeepLuna bootstrap failed: stale or incompatible daemon owns the project pipe
(PID 24224). Refusing duplicate start.
```

Readiness was consequently not `READY`. In accordance with the Fast-only,
fail-closed policy, no provider content was sent, no paid DeepLuna call or
delegation occurred, no fallback provider or Codex subagent was used, and the
existing process was not terminated. The report's final acceptance is Sol's
local evidence-backed acceptance only. A future DeepLuna Chat review requires
the project-pipe owner to be repaired or deliberately restarted under separate
authorization, followed by a new exact-project `deepseek_check`.

## Superseding Perfume Complexity intake and implementation addendum

This addendum records the later 2026-08-09 intake requested from the ChatGPT Pro
**Complex Perfumery** project and the targeted implementation accepted from it.
It supersedes only the earlier DeepLuna availability note above; the broader
scientific and release holds remain in force.

### Chat and report intake boundary

The local bridge registry enumerates 38 chats in ChatGPT project
`g-p-6a74ab83668081919f5cbd0dfe80eb09`. The work hub is **Data Integration for
Perfume-Chem**, conversation `6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf`.
The focused reports were taken from these project chats:

- Parse Chat Logic: `6a7768a3-5794-83ec-9670-c8a0aa3fc831`;
- Parse and Continue Chat: `6a77eaa8-edf4-83ec-8fdd-275cbecfd8ab`;
- Human Mixture Datasets: `6a753afc-c714-83ec-a854-e6fbb3022048`;
- Chat K Complete Review: `6a762632-0808-83ec-99a5-349be9053eaa`;
- PCV3 Complexity Lane Complete: `6a74ba21-0d30-83ec-b211-e80baca66948`;
- Prada Precision Reconstruction: `6a75276a-be08-83ec-86d5-47bf97c807cb`.

Chat statements are untrusted evidence-inbox records, not repository or
scientific authority. Three local report bytes used for reconciliation are:

| Local report | SHA-256 |
|---|---|
| `COMPLEX_PERFUMERY_CURRENT_STATE_SUPERSESSION_V2_20260809.json` | `f52f60299c8c36e43e2c738ca1bdcf191a2439460d111448b46ebec8bd841476` |
| `PREMIX_GUARD_LOCAL_DEPLOYMENT_AUDIT_20260809.json` | `9cf054d917409702ecc98e3badff4678e307d2faa21d4da7c8691841778339b3` |
| `PROGRAM_V3_FINAL_INTEGRATION_REPORT(1).md` | `743755e4d5079b622539fbb221f0a8f62be46996131c52642af3a906b2969ddf` |

The recovered master inventory and Batch 05 workbooks were retained as source
bytes only. No workbook row was promoted into inventory, formula, physical, or
scientific authority during this change.

### Reconciled dispositions

| Report claim | Local disposition |
|---|---|
| G15 can default an absent stock fraction to neat `1.0` | **Accepted after direct code inspection and an independent DeepLuna Chat review. Implemented below.** |
| Child G15 should consume the stock contract already resolved by `gate_formula` | **Accepted and implemented.** |
| Parent G15 should pass through the same resolver before comparison | **Accepted and implemented fail-closed.** A historical parent that no longer resolves against live stock now requires explicit authority repair rather than silent arithmetic. |
| Tunnel plus local validation plus Git for accepted artifacts | **Accepted architecture.** The tunnel is transport, local validation is the promotion boundary, and Git is review/history rather than a data bus. |
| The earlier tunnel HTTP 401 is stale | **Unresolved conflict.** One incoming report says tunnel list/read/write is usable; `chat_bridge/complex_perfumery/shared_state.json` still records the remote ChatGPT canary as `BLOCKED_ACTIVE_ORGANIZATION_CONTEXT_401`. Local bridge health does not prove the remote ChatGPT connector canary. |
| Universal-accord, mixture-dataset, or 156-formula reconstruction packages are ready for release | **Held.** They remain staged reports without canonical identity, stock, source, physical-test, and release authority. |
| Rebuild the protected database or generated property corpus now | **Rejected for this slice.** The earlier deterministic candidate was not logically equivalent and would remove populated scientific tables. |

### Literature-to-decision map

The implementation follows a narrow measurement-model rule: an output cannot
be more authoritative than the input quantities used to compute it. BIPM
JCGM GUM-6 warns that omitted or inadequate input contributions can make a
measurement result wrong; therefore an absent stock fraction cannot be invented
as neat `1.0` merely to keep the model running. See
[JCGM GUM-6](https://www.bipm.org/documents/20126/2071204/JCGM_GUM_6_2020.pdf)
and the Monte Carlo propagation supplement
[JCGM 101](https://www.bipm.org/en/doi/10.59161/jcgm101-2008).

OAV remains a screening calculation. Audouin et al. document that OAV does not
directly quantify a component's sensory contribution in a mixture, while
headspace studies show that matrix composition and ethanol/water conditions
change volatile release. These findings support the existing separation:
stock-rebase active-dose arithmetic is the hard invariant; OAV-per-time is a
review alarm, not percent perceived contribution or a final aesthetic gate.
See [Audouin et al.](https://doi.org/10.1021/bk-2001-0782.ch014),
[Robinson et al.](https://doi.org/10.1021/jf902586n), and
[Tsachaki et al.](https://pubmed.ncbi.nlm.nih.gov/18529063/).

For ChatGPT integration, official OpenAI guidance supports remote MCP/connectors
as explicitly approved tool calls and secure tunnels as outbound-only private
connectivity. It also requires treating tool output as untrusted and preserving
workspace controls. That supports the bridge's append-only inbox and local Sol
acceptance boundary; it does not support hidden transcript sharing or automatic
scientific promotion. See the official
[connectors and remote MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)
and [secure MCP tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

### Implementation map and result

1. **Completed now - G15 authority handoff.** `gate_formula` passes its resolved
   child contract and stock specs into G15. G15 accepts only declared,
   inventory-resolved fractions and never falls back to neat.
2. **Completed now - parent continuity.** A supplied parent is resolved through
   the same inventory contract. Invalid child and parent authority produce
   explicit `G15_CHILD_STOCK_AUTHORITY_INVALID` and
   `G15_PARENT_STOCK_AUTHORITY_INVALID` failures.
3. **Completed now - evidence binding.** Persisted formula-analysis validation
   now includes `g15_parent_formula_definitions` when recomputing its input hash.
4. **Next - source-byte intake.** Continue append-only browser/chat intake with
   immutable bytes, manifest, license, conversation/report identifier, SHA-256,
   and parser version. Do not write chat claims directly to canonical tables.
5. **Next - inventory-first B1/B2 tranche.** Resolve the 14 live identity gaps,
   then adapt a small high-impact property tranche as source and observation
   candidates with conflicts preserved.
6. **Later - disposable projections.** Regenerate JSON, SQLite, Parquet, and
   embeddings only from an accepted manifest, compare logical diffs, and promote
   atomically after human acceptance.

No formula, inventory row, workbook row, protected database, physical result,
sensory result, safety status, or scientific release authority was changed by
this implementation.

### DeepLuna Chat review and performance finding

A fresh exact-project check returned `READY` for
`perfume-chem-cheapluna-isolated`, server `0.9.9`, with settled accounting and no
unknown reservations. DeepLuna Fast and all fallback routes remained disabled.

The first bounded `DIRECT_PRO` job (`DS-855978d1441720eb380ce69e3d66359d`)
failed closed before review because its packed input estimate was 34,231 tokens,
above the caller's 24,000-token cap. The evidence selection itself was only
11,530 UTF-8 bytes. The retry kept the same evidence and route but corrected the
envelope; job `DS-db6878115afb32cc1edfbf3ac42ca9dd` reproduced the G15 defect.
Its final summary was truncated, so only the independently line-verified finding
was accepted.

Operational lesson: future Chat packets must budget for fixed orchestration and
tool-schema overhead in addition to selected file bytes. The 15 KiB evidence cap
remains useful; a job should fail during host preflight when its total packed
estimate exceeds the explicit route envelope, and Sol must still verify the
returned evidence locally.

### Focused verification

- `python -m ruff check` passed for the changed Python surfaces;
- `python -m compileall -q` passed for the changed Python surfaces;
- `pytest -q tests/test_pre_mix_guard.py tests/test_run_evidence_contract.py tests/test_pipeline_gates.py` passed: **62 tests**;
- `git diff --check` passed, apart from informational Windows line-ending warnings.

The full release verifier was intentionally not run because this was a targeted
integration hardening slice, not a merge or publication release. The repository
also remains broadly dirty with pre-existing user work that was not altered or
claimed by this addendum.
