# Chypre and citrus-wood architecture v4: implementation and acceptance

Date: 2026-10-07. Status: active source configuration after staged acceptance and
post-activation focused verification. This is a software/construction contract,
not sensory validation, empirical model admission, or a live-server deployment receipt.

## Outcome

The closed Deep Compose bridge now contains **47 mappings and 93 options**,
preserving the exact ordered 44-mapping v3 prefix. The three additions are:

| Subtype | Planned comparisons | Current-inventory result |
|---|---|---|
| Floral chypre | Rose-associated versus jasmine-associated bridge | Both distinct comparisons executable |
| Green chypre | Bitter-resin-green versus watery-leaf contour | Watery leaf executable; bitter-resin-green withheld with verified empty eligible pool |
| Woody cologne | Citrus-leaf-floral bridge versus unchanged control | Bridge withheld with verified empty eligible pool |

The unchanged control remains first. At most two source-bound comparisons are
returned, unordered. An option registered in the library is not automatically an
executable formula or a successful sensory intervention. No new stock, formula,
physical transfer, purchase, calibration, or empirical capability was admitted.

## Research and own-odor correction

The implementation followed the preceding
[reviewed plan](CHYPRE_COLOGNE_V4_IMPLEMENTATION_PLAN_20261007.md), the
[primary-source architecture review](CHYPRE_COLOGNE_AND_TEXTURE_NEXT_WAVE_20261007.md),
and the [descriptor prerequisite](ARCHITECTURE_V4_ELIGIBILITY_REVIEW_20261007.md).
Fresh supplier checks were qualitative and identity-specific:

- [PW Fructone B, 3FG00196](https://www.perfumersworld.com/view.php?pro_id=3FG00196):
  separated its own fruity/floral/fermented-fruit description from suggested
  jasmine and tuberose applications. The runtime own-odor field no longer lets
  those application words qualify it for a required jasmine intervention.
  This does not establish that every jasmine-like nuance is absent.
- [PW BerryFlor, 3FG19149](https://www.perfumersworld.com/view.php?pro_id=3FG19149):
  retained its explicitly described jasmine-associated aspect. A generic cut
  at the word `Use:` would remove legitimate odor prose and was not implemented.
- [Standard Hedione](https://studio.dsm-firmenich.com/product/hedioner-pe-964898):
  retained the manufacturer's jasmine-associated description without claiming
  an exact HC-grade or measured intensity equivalence.
- [Owned-supplier Petitgrain Paraguay listing](https://aromaandmore.com/en/essential-oil-100-pure-/97-petitgrain-essential-oil-paraguay-fresh-floral-woody-and-slightly-citrus-.html):
  its leaves/twigs botanical origin does not itself establish leafy odor. The
  described floral/woody/citrus facets do not satisfy the full leaf conjunction.
  No different-origin petitgrain was silently aliased into the owned stock.

Supplier applications, botanical organs, stock names, categories and synergy
partners are not substitutes for the material's own odor evidence. Raw supplier
caches and the 53-line receipt were preserved. Supplier descriptions are not
human preference data, quantitative gas/intensity curves or safety clearance.

## Reproduced defects and repairs

The new own-odor regression initially produced **1 failure and 2 passes**:
Fructone B incorrectly qualified for jasmine. The correction preserved BerryFlor
and Hedione's independent qualifying annotations. The descriptor suite then
passed all 74 cases.

The first staged v4 execution produced **39 passes and 1 failure**. Watery leaf
had an eligible stock, but broad earlier roles consumed the scarce identity in
every surviving beam state. The exhaustive option audit correctly refused to
call this an empty-stock-pool hold. An isolated beam-width-one regression was
also red before the repair.

Following the algorithmic principle in
[UC Berkeley CS188 forward checking](https://inst.eecs.berkeley.edu/~cs188/textbook/csp/filtering.html),
the existing beam now prefers assignments leaving candidates for future required
descriptor-constrained roles. It reuses existing bounded unary pools and the
existing admission rules, then applies the prior ordering. No state is discarded
solely by this look-ahead rule; no stock, trace, identity or exclusion gate is
weakened. It is a bounded search heuristic, not a complete feasibility proof.

The execution receipt names `BOUNDED_REQUIRED_DESCRIPTOR_FORWARD_CHECK_V1`.
After repair, all 41 then-present staged tests passed. Later corpus mutation,
artifact, paraphrase and activation tests expanded that coverage.

## Frozen staged diagnostic

Artifact: [full result](chypre_cologne_v4_staged_20261007.json).

| Measure | Observed result |
|---|---|
| Status | PASS |
| Frozen cases / design calls | 68 / 272 |
| Forward versus reverse replay | Identical |
| Per-case contract and control preservation | 68/68 |
| Inventory consistency | Identical |
| Watched files / changed paths | 1,028 / 0 |
| Cases returning source-bound alternatives | 51 |
| Returned / viable source-bound alternatives | 99 / 99 |
| Cases with changed physical compositions | 51 |

The fixture is an immutable 56-case v3 prefix plus 12 predeclared v4 cases. It
was frozen before the first v4 solver run and was not relaxed after the failure.
The new negative cases cover omitted facets, explicit exclusions, unqualified
requests, and the unavailable exact CHIMIE L'HOMME campaign.

Every planned option is replayed and accounted for. An unavailable option must
have an exhaustively empty admissible pool under the exact required predicate.
A consumed stock, failed solve, duplicate formula or critic rejection cannot
stand in for that proof. The bitter-resin and citrus-leaf holds are visible;
they are not counted among the 99 viable alternatives.

The result binds adapter SHA-256
`44776decd27ba01d88dbdbc30b37393b1700c9b9403634be1162044ef01638a3`
and corpus SHA-256
`4e3e24bd12fa968d60e35576f06c1729f72f528794fff7f4ed31ed44db20b79f`.
Its own SHA-256 is
`2b384f516a4453b86e4891e0693bf0644ce7ddcb5583b5e4f79d7e0da0c3d976`.
Opening and closing snapshot digests both equal
`c8606ab1959127ef323a6b1fb37e3601a16242e82df9862dba732db8d15ab067`.

This was a **staged v4** run, with the adapter explicitly selected in the harness.
After it passed, the production default changed from v3 to v4, AGENTS and
successor assertions were updated, and focused activation checks ran. The full
272-call corpus was not rerun against those later activation/documentation
bytes. Its historical source snapshot must not be relabeled as that later state.

## Verification receipts

- Pre-activation wider focused engine run: **361 passed in 774.57 seconds**.
  This covers v4, descriptor eligibility, v3 repairs, bridge/successor/receipt
  contracts, fruit recognition and current PW inventory tests.
- Eight subsequently added paraphrase checks: **8 passed in 4.52 seconds**.
- Five exact Formula Studio guard nodes: **5 passed in 29.18 seconds** before
  activation; these were also included in the final activation run.
- Post-activation run: **179 passed in 194.79 seconds**, including v4, all
  predecessor replay/withholding checks, v3, descriptor eligibility and the five
  Studio guards (exclusions, exact crystal mass, held Orris, micro-unit parsing,
  and unordered diverse variants). These overlap prior runs; do not sum them
  as a unique-test census.
- Backend source-review/job fingerprint tests: **8 passed in 27.36 seconds**;
  v4 is included in the durable reference fingerprint.
- Scoped root Ruff and mypy: PASS; mypy covered three modules with explicit
  namespace-package handling and skipped imported-module analysis.
- Scoped backend Ruff then mypy then targeted tests: PASS. The engine and
  backend used their separate interpreters; no cross-environment package mix.
- `git diff --check`: PASS, with existing line-ending warnings only.

The quick project report had an environment failure: Poetry selected an
incomplete sandbox Python 3.14 environment without `pytest_asyncio`. Other
selected engine, source, material, knowledge and golden-formula checks passed.
The exact golden API test then stalled inside sandboxed Windows asyncio
self-pipe creation. A bounded approved rerun in the real backend Python 3.11
environment, outside that restriction, passed **1 test, 18 deselected, 9.86s**.
It used disposable test state, not the live database. No production gate was
weakened. The [environment receipt](chypre_cologne_v4_quick_verification_20261007.json)
preserves the original failed quick report separately from the successful
targeted retest. The original report is not reclassified PASS.

No full release verifier, merge-readiness claim, live UI deployment, or physical
validation was performed for this increment. Two native read-only reviews
informed the work; the parent verified edits and tests locally. The required
exact DeepSeek bridge was not exposed, so no external LLM route was substituted.

## Performance: remaining work, not a passing claim

| Forward diagnostic p95 | Control only | Architecture comparisons |
|---|---:|---:|
| Design | 7.5126 s | 10.8174 s |
| Audit | 0.1659 s | 0.5148 s |
| Combined | 7.6038 s | 11.0921 s |

These are this diagnostic corpus/workstation's observations, not isolated
whole-system or cold/warm performance acceptance. The design p95 does not meet
the five-second objective. No 1/2/4/8-worker corpus claim is made.

Next, profile fresh and warm representative control/comparison requests, with
exact source/inventory hashes and file-read counts. Code review identified
repeated knowledge-byte reads per stock, repeated immutable predecessor parsing
and shared source-record scans as candidates, not measured bottlenecks. Any
request-scoped snapshot or byte-keyed cache must preserve missing/duplicate
source detection, per-request source freshness, cancellation and exact output
equivalence. Do not cache by name, path or modification time alone.

After the performance checkpoint, research the deferred powder-musk,
lavender-iris and tea-musk role bindings. Non-smoky suede/resin roles and real
omission operations need separate representation work; generic smoke-weighted
templates and appended roles are not adequate substitutes.

## Preserved boundary and remaining coverage

The library still has 49 construction dossiers, 179 partial subtype cards and
13 floral packages with at least one mapping. **132 subtype cards remain without
an executable mapping.** These counts are not exhaustive botanical review or
sensory coverage. No source record or numeric calibration was added this wave.

Inventory SHA-256 remains
`116c39815c81d148f0a259332b8acf734b9f3eced484b5e390dc4bc7df38cc58`;
the effective inventory is
`e8094e07505fbfbb7121d94693069e624531c4726d853e27b7a24f6c5d0fb280`.
No formula or inventory was changed by this increment. Unrelated dirty work
was preserved; no cleanup, commit or push was performed. Orris Liquid remains
excluded from new compounding. The exact CHIMIE L'HOMME brief/formula remains
unavailable and is not inferred from adjacent commercial references.

All release, safety, compounding and evidence-admission authority flags remain
false. Architecture differences, source traceability and passing software tests
do not establish scent realism, consumer liking, longevity or superiority.
