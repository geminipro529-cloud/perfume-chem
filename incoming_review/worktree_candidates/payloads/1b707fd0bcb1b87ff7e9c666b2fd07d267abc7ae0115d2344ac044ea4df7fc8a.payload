# Perfume-Chem ChatGPT project reconciliation and execution map

Date: 2026-08-10 (Asia/Bangkok)  
Workspace: `D:\chatbots\perfume-chem`  
Status: **38 project chats plus late linked continuations reconciled; exact V5 stock/dose receipt identity, typed strict-OAV abstention, legacy OAV quarantine, exact-decimal planned-lineage, profile-schema, B1 rights/scope, operation-scoped source-use, native external-study admission, and atomic workspace-import cutovers implemented and subsystem-verified; scientific and release authority remain withheld**

## Outcome in easy words

The ChatGPT project contains useful research packets, package descriptions,
formula ideas, and implementation proposals. It does not contain one clean,
current source of truth. Several chats describe older repository-neutral work,
some repeat or supersede one another, and several report generated packages
whose exact bytes or licenses were never admitted to the local scientific
ledger.

The local repository is therefore the authority boundary. The correct workflow
is:

1. use chats as a discovery and coordination layer;
2. preserve exact source/package bytes and hashes locally;
3. retain source rights, claim scope, units, nulls, parser/configuration, and
   parent lineage through staging;
4. promote nothing until local schema, tests, review, and scientific gates pass;
5. generate formula-facing projections only from accepted local records.

The most valuable live code defects found by reconciling the chats with the
repository were not missing perfume formulas. They were three authority leaks:

- decision-bearing formula state could recompute active dose from an omitted
  dilution as though the stock were neat, even when an upstream immutable stock
  receipt already carried the resolved fraction;
- the upstream inventory parser treated bare `inventory.txt` labels as neat and
  could collapse multiple stocks by highest concentration, although Inventory
  V5 explicitly separates requirement rows from physical `Current Inventory
  Master` stock;
- legacy OAV family sums, cliffs, balance ranges, and generic synergy factors
  could lower an otherwise strict OAV authority status or rank.

All three execution paths are now cut over locally. One immutable formula-dose
receipt binds the exact V5 snapshot and workbook, physical stock ID, source-row
and authority lineage, concentration fraction/basis/carrier, raw and
active-equivalent quantity, formula-input identity, and a deterministic receipt
SHA. Gate, formula state, simulation, scaling, robustness, OAV, scoring, and
reporting consume that receipt instead of silently rebuilding stock strength.
Contradictory duplicate data fail closed. Preparation/gap states remain
explicit. Legacy OAV intelligence remains visible as advisory output but is
excluded from primary status and rank.

A fourth execution defect is also cut over: planned active-equivalence inputs
now retain canonical exact-decimal text through API, persistence, hashing, and
`lab-export-v5`. Legacy SQL floats remain compatibility projections. Migration
does not manufacture decimal authority from old floats, so old rows require an
explicit immutable rebind before they can issue a planned-equivalence PASS.
This closes the numeric-persistence gap but does not create physical metrology,
uncertainty, traceability, or release authority.

A fifth metadata defect is also cut over: complete six-field source rights and
claim-scoped source-relation metadata now survive B1 candidate hashing,
persistence, reconstruction, and read-only reporting. Legacy rows without a
verified manifest become explicit `UNKNOWN`/nonredistributable records; free
text is not converted into permission. The stale natural-composite census and
15 prose-valued material profiles were reconciled without inventing numeric
character scores. The frozen C5 v1 program remains immutable, while an exact
V5 rebase assessment now binds its program hash to the current 280-row snapshot
and governing workbook. The assessment is `HOLD_REDESIGN_REQUIRED`: seven
material lines match exactly, one needs a canonical-identity rebind, six retain
unresolved basis/carrier authority, two changed stock form, two are absent from
V5, and planned Ambrettolide lacks a physical receipt; the bulk matrix-carrier
authority is also incomplete. No C5 v2 program or empirical authority was
created. Stale formula artifacts, physical validation, and release remain
explicit holds, so this is not a full green release.

A sixth metadata/policy defect is cut over without creating legal authority:
append-only B1 source-use assertions now bind the exact source version, terms
version, artifact locator, channel, action, and purpose. Local caching,
source-byte archival, internal analysis, external transmission, training,
publication, redistribution, and commercial runtime no longer inherit a
nearby API or license statement. Missing, conflicting, unreviewed, legally
held, or unsatisfied dimensions return `HOLD`; an exact allowed result remains
`SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION`.

A seventh execution seam is also closed: release-mode OAV cannot reuse a gate
by matching only raw material names and quantities. It requires exact
formula-dose receipt identity. Strict OAV delegates to the native C8
headspace/threshold evidence contract and returns an answerless typed
`ABSTAINED` result when candidate-air, threshold, analyte, unit, matrix,
temperature, uncertainty, or context evidence is absent or incompatible.
Modeled legacy OAV remains above-threshold screening only, with primary status
`WITHHELD` and authority rank zero. Unknown candidate-air is no longer coerced
to zero or allowed to raise a numeric-field exception.

## Authority ladder

| Level | What belongs here | Permitted use |
|---|---|---|
| Canonical local record | Reviewed Laboratory Beta/scientific records with immutable lineage | Decision-bearing use within the record's exact scope |
| Lossless staging record | Hash-bound source bytes plus complete rights, relation scope, parser/config, units, and schema census | Candidate review and deterministic replay |
| Verified local package | Exact bytes and internal hashes verified, but not admitted or scientifically validated | Archive and admission planning only |
| Chat report | A chat's account of a result, package, formula, or literature finding | Discovery, cross-checking, and task generation |
| Structured hypothesis | Mechanistic, perfumery, or model-generated proposal without direct validation | Experiment design only |

No chat claim, receptor association, pair rule, OAV heuristic, reconstructed
formula, or schema package becomes formula, inventory, safety, physical,
perceptual, or release authority merely because a worker reported that its own
checks passed.

## Chat estate reviewed

The reviewed estate is the 38-chat registry for the ChatGPT project
`g-p-6a74ab83668081919f5cbd0dfe80eb09` (Complex Perfumery). The linked work hub
is `6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf`. Each disposition below is a local
integration decision, not an endorsement of the chat's claims. All 38 registry
entries were reread through their latest completed turn on 2026-08-10; late
package and implementation claims remain secondary until exact bytes and local
tests establish otherwise.

| # | Chat ID | Title | Reconciled disposition |
|---:|---|---|---|
| 1 | `6a770c24-a64c-83ec-9448-9c7972751357` | Aromachemical Recipe Breakdown | Physics/OAV v3 remains a recovery target. The six-recipe, Violet Leaf, and Tobacco/Amber packages are externally hash-verified in Downloads but unadmitted, rights-UNKNOWN source designs on stock/safety/physical HOLD. |
| 2 | `6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf` | Data Integration for Perfume-Chem | Coordination hub; point it to this local ledger and verified code status. |
| 3 | `6a7768a3-5794-83ec-9670-c8a0aa3fc831` | Parse Chat Logic | Workflow/history packet; its proposed Physical Decision Rule Calibration Kernel is planning input only. Receptor, matrix-specific headspace, sensor-optimization, and Atlas-confidence evidence cannot validate human perfume decisions, and no parallel decision kernel is admitted. |
| 4 | `6a753afc-c714-83ec-a854-e6fbb3022048` | Human Mixture Datasets | The original human-mixture deliverable was never produced and remains unrecovered. A later Atlas v2/V5-rebase continuation in the same chat is now exact-byte recovered and quarantined separately; it is not a substitute. Ma, Snitz, Bushdid, and Weiss still require separate rights-governed source families at their original trial/aggregate grain. |
| 5 | `6a74bb71-33fc-83ec-9aad-d9f26b14726a` | Chat 0 Integration Complete | Current Universal Accord and PCV3 v3 bytes remain unrecovered. The same-name 8a9c... and claimed superseding 8dd0... receipts are unresolved lineage pointers; transcript counts are candidate design census only. Active complexity authority is WITHHELD with no universal row minimum, collision cutoff, aggregate score, or row-count REBUILD. |
| 6 | `6a753bd1-2584-83ec-b504-fe5ceec183bf` | Chat K Waiting for Workers | Superseded status/reporting chat. |
| 7 | `6a762632-0808-83ec-99a5-349be9053eaa` | Chat K Complete Review | Deployment review rejected unbounded integration and missing host/CI qualification; quantity/stock controls take priority. |
| 8 | `6a7569a9-f8d8-83ec-a9ab-0aee395337e6` | Repair Sequence Validation | Historical repair proposal; compare against current immutable receipt path and tests. |
| 9 | `6a71d172-8dd0-83ec-87d4-f8ceaf80551a` | Perfume Data Progress | Historical status only; current repository and manifests supersede it. |
| 10 | `6a74ba21-0d30-83ec-b211-e80baca66948` | PCV3 Complexity Lane Complete | Candidate complexity taxonomy; no universal complexity/beauty score or formula authority. |
| 11 | `6a750484-a76c-83ec-87cb-2d2f88fda0c0` | Chat OA Tasks | Task decomposition only; deduplicate against current roadmap. |
| 12 | `6a76fbe0-4c80-83ec-ac8e-fba7321b1ba3` | Project status update | Historical status; current local verification wins. |
| 13 | `6a6edb63-b570-83ec-989e-90720adace20` | Perfume Verification Process | Useful gate concepts; must be mapped to current release contracts, not run as a parallel authority. |
| 14 | `6a75276a-be08-83ec-86d5-47bf97c807cb` | Prada Precision Reconstruction | Reference/formula hypothesis on HOLD; Citronellol stock incident is governance evidence, not sensory validation. |
| 15 | `6a753b7a-5b04-83ec-8e4c-61fcebc1aa50` | Chat H Evidence Upgrade | 253-pair atlas package is locally present and internally hash-coherent; candidate-only admission is still required. |
| 16 | `6a753b22-3490-83ec-bc7b-a0e46c4655c0` | Molecular Perception Execution | Exact 8,463,278-byte/22-file v1.1 worker ZIP recovered; all 21 declared payload checksums verify. Its Keller workbook duplicates the governed local source exactly, M2OR remains dynamic, OlfactionBase currently says 875 pairs but exports only 874 data rows, and DoOR is species-specific Drosophila evidence. No receptor-to-quality or receptor-to-liking truth follows. |
| 17 | `6a753b26-53b4-83ec-92ec-02cdc8d63629` | Chat C Summary | Exact 1,319,192-byte/27-file worker ZIP recovered; all 26 declared payload checksums verify. Its 105 patent plus 25 Deite rows remain quarantined source grammar, not executable formulas. A primary-source diff found that two US8168163B2 em-dash absences were collapsed to numeric zero, so the package is not a lossless B1 extraction. Olfactorian requires approved OAuth and operation-specific reuse review; no scraping. |
| 18 | `6a753b14-8180-83ec-84f9-38e1e13e01ec` | B Lane Validation Complete | Exact 50,235-byte package recovered and hash-verified, but not admitted. Official source wording resolves Le Berre as 4 x 4 x 4 = 64 experimental mixtures plus a separate target reference; the package's 125-row reconstruction is quarantined. Source rights and numeric extraction still require governance. |
| 19 | `6a753b55-a92c-83ec-b6b4-8768db966f5c` | Experiment Intelligence Design | Seven experiment designs and the later v1.3 freeze claim are protocols/package claims, not completed experiments or measured results; host deployment remains open. |
| 20 | `6a753b49-e6dc-83ec-9224-48e24f28e73d` | G Complete Schema Validation | Exact 62,670-byte/31-file package recovered and hash-verified, but not installed. Its 34-table `ee_*` proposal is internally checksum-coherent while its own two integration holds remain open: exact parent SQL/SQLite bytes were not mounted and exact A-F parser bindings were not completed. The smallest B1-backed external-study slice remains implemented under Laboratory Beta; the parallel store remains rejected. |
| 21 | `6a753b43-9644-83ec-92ad-7d66d62e7ebe` | Chat F Completion | Exact 68,531-byte package recovered and hash-verified, but not admitted. Its 80 source rows are secondary governance assertions: every row says the rights artifact is absent, 65 were not live-verified in the F lane, and the baseline parent bytes are not included. Native append-only operation-scoped declarations remain authoritative for project handling; no source right or legal conclusion was inferred. |
| 22 | `6a74bc5c-b538-83ec-8d9b-2ebf8a827b80` | Chat 3 Completion | Claimed leaf/infusion V1/V2 package remains unrecovered. Black-tea recombination, omission, brewing, and interaction studies may enter only as source-native external-study records with their panel/aggregate/conflict grain; no beverage-to-perfume formula transfer or Black Tea Base ownership inference. |
| 23 | `6a753b36-a0b8-83ec-a7cc-bc79f1d37b47` | Chat E Completion Summary | Exact 33,356-byte v1 and 86,646-byte post-freeze hardening attachments are recovered and internally checksum-complete. A distinct five-message XHIGH conversation later supplied the exact 120,861-byte v1.2 domain-adjudication package over byte-identical v1.1 ancestry. The v1.2 source-specific codebook is useful migration evidence, but native C3/C8/B5 remain controlling and host adoption, numeric source tables, private reference data, execution, empirical truth and release stay held. |
| 24 | `6a77eaa8-edf4-83ec-8fdd-275cbecfd8ab` | Parse and Continue Chat | Repository-neutral FormulaDoseReceipt/PreparedFormulaRun design was reconciled into the native exact V5 receipt path. Local receipt-identity and abstention tests, not the chat claim, are the acceptance evidence. |
| 25 | `6a77e596-8e0c-83ec-9883-690ed5a9732d` | Task Scheduling and Reporting | Coordination history plus a PR-1 V5 authority-firewall candidate; no direct code or scientific authority until exact package admission and native replay. |
| 26 | `6a74bef7-24d8-83ec-ac0f-dc5cbcd2b242` | Chat 4 Completion | The claimed 2-acetylpyrazine parent-matrix package is unrecovered. Preserve its neutral/coffee/cocoa factorial only as a future study design; current 1% stock carrier and ODT authority are unresolved, and existing Atlas/profile rows are priors rather than observations. |
| 27 | `6a74f9c7-7edc-83ec-9964-6ede1e22a069` | Chat 0 Request | Ancestor prompt plus a later empirical-activation bridge proposal; retain as bounded experiment architecture, not observed evidence. |
| 28 | `6a74bcf2-895c-83ec-97d3-f5d098e9ba91` | Chat 7 complete | The PR-2B package remains unrecovered. Native receipt and Laboratory-Beta execution records overlap with its lineage concept, but a lossless mixed-dimension actual-run projection remains an adapter gap; no parallel store, fallback density, or FormulaState/OAV authority is accepted. |
| 29 | `6a74ba3d-4110-83ec-a421-ddc02fcd224f` | Chat 2 Completion | Historical program lane; retain only source-traceable, nonduplicative candidates. |
| 30 | `6a753ba8-a404-83ec-a4bd-0589023c256b` | Chat J Completion | Repository-neutral read-only adapter reportedly passed its own checks; current local repository integration remains the authority. |
| 31 | `6a74bcb4-ecc0-83ec-85f8-0001f5e4892b` | Chat 6 Floral Expansion | Earlier floral architecture is already represented. The distinct later ATMOSPHERE/TEXTURE package is unrecovered and transcript-only; 2-acetyl-1-pyrroline is not owned 2-acetylpyrazine, Scentanal identity is unresolved, Romandolide is V5 HAVE-neat, and generic Seaweed material identity is absent. No empirical or formula authority. |
| 32 | `6a74bf01-0734-83ec-8336-8b2c9af00f6a` | Chat 5 Completion | Claimed V5-rebased ZIP remains unrecovered. Primary melon, blackcurrant, cherry, and peach sensomics can enter only as native-grain external studies after rights review; fruit, absolute, base, accord, and molecule identities remain separate. Gamma Decalactone is legacy-only/unqualified against current V5, and Nonanal is absent. |
| 33 | `6a73d938-4908-83ec-976f-69d1d1721eb3` | No content provided | No evidence to integrate. |
| 34 | `6a74a5bb-1ec0-83ec-b093-b39abde51799` | File Retrieval Request | File/ancestry pointer only; retrieve and hash exact bytes before use. |
| 35 | `6a73d7be-f608-83ec-a270-ddab5e86dd99` | No content shared | No evidence to integrate. |
| 36 | `6a74c127-2374-83ec-b94f-580dec46927f` | Complex Perfumery Program | Program architecture and hypotheses; not an executed physical-validation program. |
| 37 | `6a74c82b-834c-83ec-8600-43c39d9329e9` | Chat 8 Completion | Claimed Active-Equivalence Metrology Oracle ZIP is unrecovered; its fixture/test claims are unverified. Native v3 planned-lineage receipts now use exact-decimal persistence, while physical metrology remains withheld. |
| 38 | `6a73da1e-1950-83ec-82fe-8eca61c3fb75` | No Content Provided | No evidence to integrate. |
| 39 | `6a762995-0d8c-83ec-aee3-66c90e56811e` | Complex Perfumery Continuation | Exact-byte recovery already exists locally for all 21 members declared by the repaired-floral integrity receipt, including the separately reread 5,510-byte test member. The reconstructed 116,771-byte outer ZIP remains SHA-wrong (`f876...` observed versus `d9abe...` expected), so member identities are quarantine evidence only and the cloud outer package remains unadmitted. No duplicate recovery or installation. |

### Late-linked global chat-estate governance package

The out-of-registry chat `6a762c12-5af0-83ec-8050-798c78c53d75`
(`Chat reconstruction and continuation`) supplied a Google Drive receipt for
`PERFUME_CHEM_GLOBAL_CHAT_ESTATE_INTEGRATION_v1.zip`:

- Drive file ID: `1c013i5LUu9iLAt3UnBrNZfAUokRmizKd`;
- 28,929 bytes;
- SHA-256: `491461de453f1a9d213381a48f408b5a6d3ebc8144c9c98cac5a824de6da308e`;
- 18/18 members decompressed and matched the reported CRC32/size checks in the
  authenticated read-only audit.

Disposition:
**EXTERNAL_GOOGLE_DRIVE_HASH_AND_CRC_VERIFIED_GOVERNANCE_PACKAGE_RECOVERED_UNADMITTED**.
The bundle is architecture/methods evidence with
`HOLD_SOURCE_ESTATE_INCOMPLETE`; it does not contain exact chat exports,
completed all-message lineage, formulas, observations, inventory, safety,
physical results, or release evidence. It must not install a second schema or
source store. Native B1/B2/B7 and external-study records remain controlling.

Its 28-row gap register requires a current native rebase before use. The
38-chat count denominator and many subsystem cutovers now exist, while exact
message/attachment denominators and source-estate bytes remain unresolved.
Future interchange should bind current RO-Crate 1.3 where applicable and call
the custom mapping predicates SSSOM-inspired rather than SSSOM-conformant. The
16 complexity axes remain a non-scalar audit checklist; they confer no formula
or release authority.

### Continuation repaired-floral exact-member recovery

Conversation `6a762995-0d8c-83ec-aee3-66c90e56811e` was used as a bounded
transport surface for one claimed 116,771-byte repaired-floral ZIP with expected
SHA-256
`d9abe68882edc86dfff47ab2cb4890e11c5bbe3e1e9c37dbd0c22930e628e54e`.
The reconstructed outer candidate has the right declared length but the wrong
SHA-256,
`f8766945a3c02500e7774c1b0ecfa1343a9acaf437c644916ca3f447dd7ec473`,
and is not admitted as the original ZIP.

The narrower member-level recovery is locally complete and does not need to be
repeated. The exact `INTEGRITY_RECEIPT.json` at
`incoming_review/chatgpt/20260818T044149+0700-floral-members-6a762995/exact_members/`
is 3,899 bytes with SHA-256
`5abff128fcfce28eb891176c93cfed080e3e7bfc22fbb068ef41d52129f88b65`.
Fresh local recomputation confirms all **21/21** declared members match their
exact byte lengths and SHA-256 values. This includes the independently reread
`tests/test_stock_basis_repair_and_admission.py`: 5,510 bytes, SHA-256
`6abd59ee9daab27893646a15a45911f9e6241dd7e4af37f368867d200d55dad2`.
The local `VALIDATION_RESULT.json` consequently remains
`PASS_ALL_MEMBER_IDENTITIES_EXACT_QUARANTINE_ONLY`.

These facts establish member identity, not a valid original outer container,
code installation, test truth, formula correctness, stock authority, physical
execution, sensory evidence, or release readiness. Preserve the 21 exact
members and receipt as one quarantine lineage; do not rerun the base64 recovery,
reconstruct a new ZIP and label it original, or copy candidate code into native
runtime. If a future operation requires the outer package itself, recover the
exact cloud attachment bytes and match the expected outer SHA first.
Disposition:
**REPAIRED_FLORAL_OUTER_ZIP_UNADMITTED_MEMBER_SET_EXACT_QUARANTINED_NO_DUPLICATE_RECOVERY**.

### Parse-Chat physical-decision-kernel refinement

The later Parse-Chat proposal is useful only as a methods checklist. Its cited
receptor work establishes receptor-level competition or antagonism, not a
simple receptor-to-human-perception map
([PNAS 2019](https://doi.org/10.1073/pnas.1813230116),
[Oka et al. 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC1271670/)); the
[OR5AN1 study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9874024/) does not
directly test Habanolide; and alpha-ionone is not a universal-sensitivity
control merely because beta-ionone has a known OR5A1 genotype effect. The cited
[DPG Henry-law study](https://doi.org/10.1021/acs.iecr.5b03852) and skin/hair
release evidence remain matrix-, apparatus-, and substrate-scoped. The
[automated-blending paper](https://doi.org/10.1039/D3DD00215B)'s Bayesian
objective is a 12-channel sensor response for a ternary solvent mixture, not
human liking, perfume quality, or beauty.

No new physical-decision engine is needed. Native exact-stock/preparation
lineage, C5 calibration, C8 headspace/OAV/interaction evidence, Laboratory Beta
execution records, strict C0 sensory qualification, B5 analytical evidence,
and B7 claim authority already separate the required stages. In particular,
native C8 `InteractionEvidence` binds exact identities and concentrations,
context, sensory method, assessor population/count, source, uncertainty,
applicable ranges, calibration state, and any bounded numerical effect. A
numerical adjustment remains withheld unless the recorded model is
context-calibrated and the request matches its exact identities, concentration
ranges, context, and target.

The recovered Interaction Atlas therefore remains a secondary candidate grid:
253 pairs, 68 evidence-enriched rows, 185 structured hypotheses, and zero
measured-headspace, strict-OAV, physical-pair-pass, or completed-style-study
closure. Any first physical program must be a separately authorized C0/A2
prepilot with exact V5 stock identity, carrier and active-dose controls,
blinding/randomization, repeated-day experimental units, and separate
analytical/headspace versus sensory endpoints. A/B/3:1/1:1/1:3 is one candidate
geometry, not a universal rule. Active learning may select experiments only
after a governed endpoint and held-out validation exist; it is never beauty or
formula truth.

## Cross-chat data map

| Lane | Reported content | Current local decision |
|---|---|---|
| A: human mixtures | Ma, Snitz, Bushdid, and Weiss source families plus an unrecovered Chat-A package | Preserve source rows, experimental units, and endpoint observations as separate grains. Ma participant/trial nesting, Snitz aggregate pairs, Bushdid triangle responses/erratum, and shared Weiss/Snitz lineage must not be flattened into one N. |
| B: exact ratios | Exact package recovered with 253 generated arms and 23 claimed checks | Preserve the package only as quarantined secondary reconstruction. Le Berre's official design is 4 levels on each of 3 axes = 64 experimental mixtures; the target is a separate paired-comparison reference, so the package's 125-row grid is not source geometry. |
| C: corpora/patents | Exact Chat-C package with four patent publications/five arms/105 rows plus two Deite blocks/25 rows; two source em-dash absences are incorrectly represented as numeric zero | Preserve the attachment as a quarantined secondary reconstruction. Rebuild ordered B1 source rows from primary bytes with raw lines, original units, totals, typed absences, trade-product dilution, locators, and rights intact. Derived projections are separate and nonexecuting; no normalization by convenience. |
| D: receptor data | Exact quarantined Chat-D v1.1 package; governed duplicate Keller data plus dynamic M2OR, internally inconsistent live OlfactionBase, and stable DoOR candidates | Preserve raw positive/negative assay rows, species, receptor sequence, concentration, assay context, identity provenance, source version, and derived-consensus lineage. Deduplicate Keller; keep discovery associations and Drosophila normalization separate. No receptor-to-perceptual-quality shortcut. |
| E: physical chemistry | Strict guards and headspace/OAV contracts | Direction is sound; matrix-specific measured calibration and explicit abstention remain required. |
| F: rights | Exact Chat-F 20-file/80-row rights package plus a separate local 80-row scored registry; live FragDB/Fragella/ScentRev/Fragrantica and infrastructure channels | Preserve the recovered package as a quarantined secondary inventory only. It contains zero exact rights artifacts and omits its baseline parents. Six-field rights round-trip and exact operation-scoped declarations are implemented; missing dimensions, conflicting channels, unmodeled obligations, and required legal review stay HOLD. |
| G: external schema | Exact Chat-G 34-table package; distinct local 22-entity planning bundle; distinct XHIGH read-only adapter/receipt package whose frozen archive and database bytes are absent | Preserve all three as separate historical/planning artifacts. The recovered package still omits its exact parent database and final A-F bindings. Laboratory Beta remains the sole persistence authority; the smallest B1-backed external-study records and deterministic source-only projection are implemented without a second database. |
| H: interaction atlas | 253 unique group pairs; 68 evidence-enriched, 185 structured hypotheses | Exact local ZIP verified. Archive/admit as secondary reconstruction; all pair claims remain candidate-only. |
| Atmosphere/texture | Distinct Chat-6 claim of 11 families, 33 branches, 26 combinations, 28 techniques, 32 interfaces, and 11 confusion sets | Package bytes are unrecovered; counts are transcript-only architecture. Keep separate from the governed floral registry and require exact compound/product/stock identity plus blinded matched-strength tests before any negative-space or atmosphere claim. |
| 2AP parent matrix | Chat-4 neutral, coffee, and cocoa parent-by-dose proposal | Package bytes are unrecovered. Keep the Atlas/profile material associations as general priors only; resolve the exact 2-acetylpyrazine stock receipt and run a separately authorized coded factorial before any parent-specific interaction claim. |
| Leaf/infusion | Unrecovered Chat-3 V1/V2 package plus source-native black-tea AEDA, recombination, omission, brewing, and binary-interaction studies | Preserve tea origin, preparation, panel/group, aggregate, omission arm, table/prose conflict, and source units. Beverage, molecule, opaque base, and perfume accord remain non-equivalent; no source concentration becomes a perfume dose. |
| I: experiments | Seven experiment designs | Run only after stock identity, randomization, blinding, sample, outcome, and analysis contracts are frozen. |
| J: adapter | Default-off, read-only repository-neutral adapter | Reconcile with native ingestion and test locally; do not install a competing authority path. |
| K: deployment | Review rejected unbounded deployment | Preserve that rejection; host/CI and scope gates must be explicit. |
| Formula/reconstruction | Prada and other formula drafts | Keep on HOLD until live inventory, exact stock dose, strict OAV context, IFRA, and blinded physical testing pass. |

## Chat 0 Universal Accord and Meaningful Complexity correction

The exact current Universal Accord and PCV3 v3 bytes remain unrecovered. The
exact recovery kit
`incoming_review/Perfume_Chem_Full_Recovery_Capture_Kit_20260808.zip` is 36,358
bytes with SHA-256
`ae3b36afe359f50871f742280341986bfd0b494c75a6e7da4b762932c5bdf570`.
It identifies the unmounted PCV3 Chat-1 package as
`10acff0eb8f9e40dc0bd0e8152e04eb3c6440393c39dc950ccc3e96dccc1f6e1`,
the unmounted PCV3 Chat-2 package as
`db638ab82c7e1a798297a9f4376014b9f51965511ae1d65132e57b4d12c9c9eb`,
and a stale same-name Universal Accord receipt beginning `8a9cbdfb...`. A later
Chat-0 receipt claims a superseding same-name SHA beginning `8dd04ea6...`, but
those bytes and the supersession relation are not mounted or independently
verified. Neither receipt may silently replace the other.

The claimed 94 families, 228 combinations, 202 techniques, 227 interfaces, 191
anti-collapse records, 638 temporal records, 167 gaps, 161 physical-screen
designs, and 28 checks remain transcript-level design counts. They establish no
physical winner, formula mutation, liking, beauty, complexity, safety, or
release result.

The former live OpenCode default prompt granted Meaningful Complexity v2 fixed
row minima, preferred ranges, a generic collision cutoff, and an aggregate
quality threshold. That conflicts with primary mixture evidence and with the
native noncollapsed construction profile. The active contract now states
`complexity_authority=WITHHELD`: no universal material-count minimum, no
aggregate complexity or quality score, no universal collision threshold, and
no automatic REBUILD solely from row count. Candidate dimensions remain
separate, and none can rescue stock/dose, strict-OAV, physical-chemistry,
safety, provenance, or physical-observation failure.

The 2023 semantic mixture-discriminability paper is *Chemical Senses*
(PMID 37262433, DOI 10.1093/chemse/bjad018), not a 2026 PNAS paper. The distinct
2026 PhysSim paper is a physics-inspired latent model (PMID 42469179, DOI
10.1021/acs.jcim.6c01297), not semantic or receptor truth. The 2026 linear
mixture work remains a bioRxiv preprint (PMID 42465471, DOI
10.64898/2026.07.03.736426) and is retained only as a source-scoped baseline.

## Chat 6 atmosphere and texture correction

The earlier Chat-6 floral expansion is already represented by the Program-v3
specification and is not duplicated. The later distinct
`ACCORD-INTEL-ATMOSPHERE` execution claims 11 families, 33 branches, 26
combination candidates, 28 techniques, 32 interfaces, and 11 confusion sets.
Its claimed ZIP SHA-256
`21a94e02107becdf5411f17eee2b75801d04d47badc58e1164daa4564e10e268`
was not recovered in the bounded Downloads census. Package structure, tests,
rights, and content therefore remain unverified transcript claims.

Material corrections are fail-closed:

- 2-acetyl-1-pyrroline (PubChem CID 522834, C6H9NO, MW 111.14) and
  2-acetylpyrazine (CID 30914, C6H6N2O, MW 122.12) are non-equivalent. V5 owns
  only 2-Acetyl Pyrazine; the fragrant-rice marker remains a missing specialist,
  never an alias, substitute, or authorized dose.
- `Scentanal 1%` has no resolved compound/product identity. Pure
  SCENTENAL(R) is reported as CAS 86803-90-9 / PubChem CID 163529, but local MW
  and vapor-pressure values conflict with that identity and supplier documents
  conflict between pure-substance and proprietary-mixture descriptions.
  Neither spelling/product is current V5 stock. Preserve separate molecule,
  supplier-product, and physical-stock identities under
  `SOURCE_DOCUMENT_AND_LOT_IDENTITY_CONFLICT`.
- Romandolide is current V5 `HAVE—NEAT`.
- Seaweed Absolute/Base is absent from V5. Published Palmaria and mixed-seaweed
  studies demonstrate species-, processing-, and storage-dependent profiles;
  a future stock requires exact producer, species/material basis, extraction,
  carrier/fraction, lot, safety, and source receipts before use.

Any future atmosphere or negative-space record remains an architecture and
controlled-test proposal. It requires exact package recovery, B1 rights/source
admission, current-V5 child requalification, matched-strength coded sensory
comparisons, ablation/add-back, independent-session replication, and
preregistered endpoints. A pass requires improved prespecified
airiness/transparency or separation while overall intensity remains inside a
frozen equivalence margin and target identity is preserved; simple dilution,
weaker intensity, fewer detectable notes, or liking alone cannot pass. No transcript count,
material name, lower dose, or row count creates empirical, formula, stock,
procurement, safety, release, or publication authority.

## Chat 4 2-acetylpyrazine parent-matrix correction

Chat 4 proposes a neutral, Coffee Absolute, and Cocoa Absolute parent-by-dose
matrix under the key `CHAT4-BA-EXP-001`. Its earlier claimed package SHA-256 is
`3332429852bfdfdea809b7b33fa2e3ad8f53502543af2404eb43c8623165532c`,
but no matching package or named member was recovered in the reported bounded
Downloads and `incoming_review` census. The experiment and its result must not
be reconstructed from transcript prose.

Current local evidence narrows the design:

- V5 owns 2-Acetyl Pyrazine neat/as supplied plus a 1% working stock whose
  carrier is unstated. That 1% stock is not execution-qualified until its
  carrier and concentration basis are bound, or a fresh exact preparation
  receipt is produced from the neat material.
- Coffee Absolute Grasse 10% in DPG is owned; Coffee CO2 is a distinct gap.
  Cocoa Absolute is owned, Cocoa Absolute 10% requires a recorded preparation,
  and Cocoa CO2 Extract 7.7% is a distinct stock that cannot be pooled or
  substituted.
- `engine/odor_thresholds.py` marks the 2-acetylpyrazine threshold
  `UNVERIFIED` and describes its numbers as a conservative trace-use estimate.
  They cannot set a sensory dose, detectability result, interaction result, or
  safety decision.
- The Interaction Atlas and `ingredient_intelligence` coffee/cocoa/nutty
  relations remain architecture and mechanism priors. They are not empirical
  parent-specific observations.

The cited food-analysis and sensomics papers (PMIDs 33470094, 32045517,
39258874, and 31955778) support identity, measurement, roasted-mixture context,
and formal interaction design, not transfer of food-matrix OAVs or proof of the
proposed perfume interaction. Later source reconciliation strengthens that
boundary: one trained-panel ethanol study reports an acetylpyrazine threshold
of 1.8 micrograms/L (PMID 40503524), while a 23% ethanol hydroalcoholic model
reports 12 micrograms/L (DOI 10.1002/ffj.3729). A fixed-ratio
furaneol/acetylpyrazine study found additivity rather than synergy and explicitly
limited transfer beyond its simplified solvent and ratio (PMID 42006658).
These values are context evidence, not local dose settings or independent proof
of a perfume interaction.

A future study therefore requires separate neutral, Coffee-Absolute, and
Cocoa-Absolute conditions; carrier-matched parent-only, 2AP-only, and carrier
controls; a blinded local dose-range stage in the exact application matrix;
exact active mass; coded repeated observations with assessor/session as the
top-level units; and a prespecified parent-by-continuous-dose estimand. It
remains a future physical-study plan, not an activated experiment or authority
record.

## Chat 5 fruit and fermentation sensomics correction

Chat 5 reports a V5-rebased package with claimed ZIP SHA-256
`941f6d48eaf9c6ef687c4d054a30ee4050a7d5a46da87d9ab4b4d8234f0e7f70`.
The reported exact census across Downloads and the workspace found no matching
archive, and no current project source record contains the four newly supplied
primary-source identifiers. The package and its transcript counts remain
`UNRECOVERED`; they must not be reconstructed from prose.

The nonduplicative source-level conclusions are:

- oriental-melon recombination and omission work used 22 selected odorants and
  found both significant and nonsignificant omissions. `Melonal` was not one
  of the source-identified key odorants, so owned Melonal is a comparator or
  null arm, not a melon-identity pass (PMID 40491709);
- fresh-blackcurrant headspace changes materially with freezing, disruption,
  cultivar, site, and ripeness. Fresh fruit, owned Blackcurrant Absolute 10%
  DPG, and opaque Cassis Base 345B are non-equivalent source objects
  (PMID 28992408);
- sweet-cherry GC-O identifies green, almond, floral, and citrus axes in
  addition to benzaldehyde. `cherry = benzaldehyde` is therefore an
  oversimplification, not a source reconstruction (DOI 10.1002/ffj.1994);
- peach evidence supports multiple lactone, floral, ionone, green, and ester
  axes rather than one-lactone sufficiency (PMIDs 34298395 and 42169315).
  Current V5 qualifies linalool, beta-ionone, and some hexyl-acetate stocks,
  but has no Nonanal. Gamma Decalactone appears only in legacy
  `inventory.txt` and is absent from the authoritative V5 snapshot, so its
  executable state is `LEGACY_ONLY_UNQUALIFIED`.

Future source admission must preserve cultivar/biological source, ripeness,
processing, extraction, matrix, recombination or omission stimulus, exact
chemical identity, source-native quantity, participant-group or aggregate
grain, repeated-rating structure, correct-count/significance, data
availability, and rights. No pseudo-participants or cross-paper pooled sample
size may be created. A separate project crosswalk must distinguish
`EXACT_V5_STOCK_MATCH`, `STOCK_STRENGTH_CONFLICT`,
`LEGACY_ONLY_UNQUALIFIED`, `ABSENT`, and
`OPAQUE_PRODUCT_NONDECOMPOSABLE`.

The highest-value later experiment is a source-informed, non-equivalence peach
ablation/add-back design, but it is not operationally ready. Gamma Decalactone
requires current V5 authority, Nonanal remains held or absent, and every arm
requires exact stock IDs, active mass, carrier controls, coded/blinded samples,
and assessor/session replication. No source concentration, fruit equivalence,
formula mutation, liking, similarity, safety, or release conclusion is
authorized.

## Chat 3 leaf-and-infusion and black-tea correction

Chat 3's later ACCORD-INTEL-INFUSION lane claims a recovered V1, a V2 package,
51 checks, and hundreds of subtype, combination, technique, interface,
confusion-control, gap, screen, source, and delta records. Its claimed V1 ZIP
SHA-256 is
`db780b8f45b001315ce31ba96c7fb921dae5fbdd61d4f3e47454e892f2ffb70b`.
The reported exact census of 296 local ZIPs found no matching archive or member
names. The existing Program-v3 Chat-1/3 recovery pack belongs to a different
engine-qualification lane. The accord/infusion package, checks, record counts,
recipes, screens, and source graph are therefore `UNRECOVERED` transcript
claims and must not be reconstructed.

The independently identified black-tea studies are useful only at their native
grain:

- Darjeeling AEDA/recombination identified 24 odor-active compounds and used 18
  OAV-greater-than-one compounds at beverage concentrations; leaf and infusion
  concentrations differ ([PMID 16448203](https://pubmed.ncbi.nlm.nih.gov/16448203/));
- Dimbula work identifies potent cis/trans epoxy-decenal sweet/juicy odorants
  ([PMID 16787030](https://pubmed.ncbi.nlm.nih.gov/16787030/));
- brewing conditions materially alter volatiles, with water/tea ratio the
  strongest reported factor in one study
  ([PMID 33756321](https://pubmed.ncbi.nlm.nih.gov/33756321/)); and
- a sweet-floral black-tea abstract reports 21 binary comparisons classified as
  five partial-addition, nine compromising, and seven masking cases, but does
  not expose pair-level mappings. Those counts must remain aggregate-only
  ([PMID 41534222](https://pubmed.ncbi.nlm.nih.gov/41534222/)).

The 2026 Wuyi study's full text adds a particularly valuable conflict-aware
source fixture ([PMID 42232488](https://pubmed.ncbi.nlm.nih.gov/42232488/)). It
screened 47 samples, selected six, used a 12-person QDA panel, three trained
GC-O evaluators, and a mean-concentration recombination assessed by 12
panelists. Table 3 is the controlling omission evidence: 14 significant and
five nonsignificant omissions. The strongest five significant omissions were
beta-damascenone, phenylacetaldehyde, alpha-ionone, beta-cyclocitral, and
2-amylfuran. The five nonsignificant omissions were 1-octen-3-ol, safranal,
2-phenyl-2-butenal, decanal, and (E)-beta-ocimene. Preserve three source
conflicts instead of resolving them by convenience:

1. methods describe triplicate 3-AFC comparisons while Table 3 reports a
   denominator of 12;
2. one ethics statement reports approval 2023-138 and written consent, while a
   later statement says approval was not required and consent was verbal; and
3. prose says 15 significant omissions and inconsistently names decanal and
   (E)-beta-ocimene, while the observed table reports 14 and marks both
   nonsignificant.

Current V5 has exact or high-confidence linalool, beta-damascenone 1%,
alpha-ionone, nerol, methyl salicylate, and d-limonene stocks. Nerolidol needs
stereochemical bottle/source confirmation. Aldehyde C10 needs B4/CAS evidence
before it can be identified as decanal. Phenylacetaldehyde is absent, and owned
Phenylacetaldehyde Dimethyl Acetal is a different molecule. Beta-cyclocitral,
1-octen-3-ol, 2-amylfuran, safranal, nonanal, linalool oxide I, dimethyl
trisulfide, 2-phenyl-2-butenal, longifolene, and (E)-beta-ocimene are absent.
Black Tea Base is absent from authoritative V5; a legacy catalog mention or an
opaque commercial base would not establish ownership or source equivalence.

Admission belongs in the shared native external-study layer after B1 rights and
operation assessment. It must preserve study/source version, tea origin and
preparation, brewing matrix, participant groups rather than fabricated people,
47-screened/6-selected source aggregates, GC-O evaluator grain, recombinant
stimuli, omission arms, exact chemical identities and source quantities,
aggregate observations, binary-count-only records, and explicit
table/prose/method/ethics conflicts. Published beverage rows must not enter
`LabExperiment`, `accord_library`, natural decomposition, inventory, or formula
tables. A future local source-informed presence/absence screen would be a new
separately authorized experiment, not a tea recreation or automatic formula
mutation.

## Late 2026-08-10 Aromachemical Recipe Breakdown delta

The exact ChatGPT thread was reread after the original 38-chat census. Its
latest completed turn reports a `Physics/OAV/Physical-Decision Model v3`
package with ZIP SHA-256
`08abcf6456b39d509d7ffe585a0fffa5a9d7f3e7d8a53a775fede4b4b15f5eff`.
No matching top-level local byte object or text reference was found in the
current workspace scan, and the broader source-recovery scan likewise reports
no exact local bytes. Do not confuse it with the local OAV-HSG v1.3 package,
whose SHA-256 begins `4327c39a`.

The prose direction is useful: keep active dose, analytical calibration,
thermodynamics, finite-dose transport, measured headspace, threshold
distributions, temporal OAV, coded sensory decisions, and formula-revision
authority as separate objects. Its default action bands—within 1.5x, 1.5x to
below 3x, 3x or greater, and 9.5x-10.5x—are declared project defaults, not
validated universal thresholds. They cannot displace the current native guard
without source, calibration, and repository-native comparison.

The same thread reports two teaching/formula packages:

- six-recipe ZIP SHA-256
  `77ad64fbe0ad0d4c7e85bde252f52fa245fffc223c7abc6ef352005703804996`;
- tobacco/amber-school ZIP SHA-256
  `ece9bb598e9b640a9ea8bac0e08058220bc8ceaed55ddb6688d55c23ad45a47f`.

All three formula/teaching ZIPs have now been found in Downloads and verified
without extraction or content promotion: the six-recipe pack, Tobacco/Amber
School, and Violet Leaf portfolio. None has been admitted as source content.
Their rights remain `UNKNOWN`, their formula designs and modeled/proxy OAV
remain computational teaching candidates, and physical liking, similarity,
stability, safety, measured headspace, and release remain untested.

Disposition:
**PHYSICS_RECOVERY_TARGET_SIX_RECIPE_TOBACCO_AND_VIOLET_EXTERNAL_BYTES_VERIFIED_UNADMITTED**.

### Recovered six-recipe source package

The exact six-recipe source package is now present externally at
`C:\Users\ASUS\Downloads\Latest_Integrated_Commercial_Reconstruction_Recipe_Pack_Aug2026.zip`:
361,505 bytes, SHA-256
`77ad64fbe0ad0d4c7e85bde252f52fa245fffc223c7abc6ef352005703804996`.
The archive has 54 entries, of which 47 are files: 45 manifest-declared payload
files plus `MANIFEST.json` and `MANIFEST.sha256`. All 45 declared payload
byte-count/hash pairs verify. Its 152,424-byte workbook has SHA-256
`459b9b8f5e6e4546d05248b93248519645eb002dfcf38e8bc2f2f8ae30e876e9`,
and the declared 199,635-byte V5 inventory parent has the controlling workbook
SHA-256 `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`.

The support handoff transcribed the manifest digest as
`5fcd69c0f0316a1bca727335af00b2af8e124020674ee2dfcf38e0f30fbcb42`.
Direct recomputation and the archive's own `MANIFEST.sha256` agree instead on
`5fcd69c0f0316a1bca727335af00b2af8e124020674ee2df0d818a0e30fbcb42`.
This is preserved as
`HANDOFF_TRANSCRIPTION_ERROR_ARCHIVE_BYTES_CONTROL`; the discrepancy is not
silently erased. Conversation-level lineage is known, while exact source turn
and message IDs remain unresolved.

The source workbook preserves six separate target/build branches:

| Formula ID | Target rows | V5-build rows |
|---|---:|---:|
| `PR-E01` | 49 | 52 |
| `H07` | 66 | 65 |
| `AM-E01` | 97 | 96 |
| `S06` | 44 | 43 |
| `C03` | 58 | 57 |
| `PR-E07` | 47 | 49 |
| **Total** | **361** | **362** |

All 361 target molecular doses are inferred. The package records 313
exact/active-equivalent mappings and 48 nonexact/constructed controlled-test
mappings; those 48 must never be flattened into exact source lineage. Current
V5 requalification classifies the 362 build rows as 191 exact-ready, 116
exact-but-metadata-incomplete, 32 opaque product-basis, 11 preparation-required,
8 package physical blocks, 2 without executable current stock, and 2 carrier
references. All 800 modeled OAV-time rows are warnings and retain
`MODELED_SCREENING_ONLY` authority. The 361-row dose firewall is an internal
portfolio envelope only (287 pass, 74 review), not toxicology or IFRA clearance.

Disposition:
**DATA_AMBER_SIX_RECONSTRUCTION_SOURCE_PACKAGE_RECOVERED_TARGET_DOSES_INFERRED_NONEXACT_SUBSTITUTIONS_V5_STOCK_METADATA_AND_PHYSICAL_VALIDATION_RED**.
All six remain `HOLD_SOURCE_DESIGN_AND_COMPUTATIONAL_COMPARISON_ONLY`; no source,
formula, strict-OAV, headspace, sensory, safety, procurement, compounding, or
release authority changed.

## Verified local package correction: Interaction Atlas

The following was checked directly without extracting or promoting data:

- package: `incoming_review/Perfumery_Interaction_Layering_Atlas_v1_Package.zip`;
- size: 679,235 bytes;
- SHA-256: `d9d3b55cb37f6dbcb0f2f9317162afdebe9ce2ff8092647d2fbdfd5042b11e6f`;
- 23 ZIP members, including manifest, checksum list, seven core artifacts, 12
  worker packets, README, and template;
- all seven checksum-declared core members recomputed from ZIP streams: 7/7
  match;
- manifest census: 23 groups, 253 pairs, 55 priority pairs, 27 evidence
  sources, 68 evidence-enriched rows, 185 structured hypotheses, 12 worker
  packets;
- declared empirical boundary: measured headspace 0, strict OAV 0, physical
  pair passes 0, completed perfumer-style case studies 0.

The exact inventory parent is also present:

- `runs/CP6-20260805/ingest/inputs/Kenny_Current_Perfumery_Inventory_Master_Aug2026_v3 (1)(1).xlsx`;
- size: 148,042 bytes;
- SHA-256: `90049fd0445a1c69eea52ea1fb88909f51a49810ea77503e6aee690f4a00b21f`.

Disposition: **LOCAL_BYTES_PRESENT_NOT_GOVERNED**. Admit one package-level
secondary-reconstruction record with the inventory parent, then stage the 27
underlying sources separately and connect them only with claim-scoped citations.
“Evidence-enriched” must not be translated into pairwise causal proof.

### Implemented authority-false external-package receipt boundary

`engine/ingestion/package_receipts.py` now supplies a read-only quarantine
contract for exact ZIP identity before source admission. It validates a
self-hashed receipt, structured rights, explicit blockers, parent pointers, and
ten authority flags that must all remain false. ZIP verification checks the
outer byte count/hash, entry/file counts, package root, duplicate or unsafe
paths, symlinks, encryption, compression limits, and embedded
manifest/checksum bytes without extracting members. A verified result is
`VERIFIED_QUARANTINED`; it cannot emit B1 candidates or authorize promotion.

Two immutable governance receipts now use that boundary:

- `data/governance/interaction_atlas_package_receipt_20260810.json`, receipt
  SHA-256 `70941bf51b5ec2d438bc7a815399aa3e2f4c4156f9652a89c91919623ff763c7`;
- `data/governance/six_recipe_package_receipt_20260810.json`, receipt SHA-256
  `e9a1103e8ff4dc09913adf7439d3a4a9bd6d89894b2e9c07fdee7ab827ea96b7`.

Both exact ZIPs pass this native verifier locally, but both retain
`reuse_status=UNKNOWN`, `redistribution_allowed=false`, all admission booleans
false, and every scientific/formula/safety/release authority false. The Atlas
receipt preserves its 27 source IDs only as candidate pointers; each underlying
artifact still needs separate exact bytes, source scope, and rights before B1
staging.

### Chat A later Atlas v2 continuation: exact recovery and non-substitution

Conversation `6a753afc-c714-83ec-a854-e6fbb3022048` did not produce the
requested Chat-A human-mixture package. A later continuation in that same chat
did produce a distinct V5-rebase successor, recovered through the authenticated
attachment surface on 2026-08-19:

- package:
  `incoming_review/chatgpt/20260819T123618Z-chat-a-atlas-v2-6a753afc/PERFUMERY_INTERACTION_ATLAS_V2_V5_REBASE_20260809.zip`;
- exact size: 419,611 bytes;
- exact SHA-256:
  `e9c4477ea736a5f9f380658ed4dd9e2ab294e01a0e69e565a2a19bb994f50e3e`;
- 14 files under one package root; all 13 checksum-declared payload members
  independently recomputed exact;
- receipt:
  `data/governance/chat_a_interaction_atlas_v2_v5_rebase_package_receipt_20260819.json`;
- capture manifest:
  `incoming_review/chatgpt/20260819T123618Z-chat-a-atlas-v2-6a753afc/source_manifest.json`.

The package binds the exact Atlas v1 JSON hash and the same canonical Inventory
V5 workbook hash already used by the project. A direct local diff proves all 253
v1 interaction rows and every original field are unchanged; v2 adds scope,
governance, evidence-posture, and inventory-rebase fields. Its V5 census is 125
inventory-example occurrences: 120 physically ready as named, four requiring a
controlled 10% working-stock preparation (Allyl Ionone, Carrot Seed EO,
Citronellol, and Heliotropal), and one procurement hold (Ambrettolide 10% in
DPG). No ExactStockRef was issued and no package row was installed.

The four added primary sources support only scoped guardrails:

- [PMID 42241975](https://pubmed.ncbi.nlm.nih.gov/42241975/) shows
  receptor-dependent ethanol antagonism in heterologous OR1A1/OR2W1 assays, not
  a universal perfume-level suppression factor;
- [PMID 40524649 / DOI 10.1111/ics.13085](https://pubmed.ncbi.nlm.nih.gov/40524649/)
  reports molecule- and skin-dependent release in ten volunteers, not a
  universal longevity ranking;
- [PMID 42391911](https://pubmed.ncbi.nlm.nih.gov/42391911/) and
  [PMID 41605011](https://pubmed.ncbi.nlm.nih.gov/41605011/) report bounded
  Magnolia and Rosa natural-matrix interactions, not transferable
  fine-fragrance pair constants.

The native archive scanner keeps the package `GRAPH_COMPLETE_QUARANTINED`
because the embedded XLSX is a nested archive without its own child receipt and
large JSON/PNG members receive partial-member scans. Rights remain UNKNOWN, all
ten authority flags are false, and source/runtime row admission is zero.
Classification:
**CHAT_A_ORIGINAL_HUMAN_MIXTURE_DELIVERABLE_ABSENT_LATER_ATLAS_V2_EXACT_RECOVERED_V1_INTERACTIONS_PRESERVED_V5_REBASE_ADVISORY_ONLY_NO_IMPORT**.

## Verified nearby 80-source data-science registry

A data-science planning bundle that overlaps the Chat F/G subject matter is
present and was checked directly. Matching row counts or themes do not prove it
is the exact attachment described by either chat:

- package: `incoming_review/Perfume_Data_Science_Extreme_Research_Bundle_v1.zip`;
- size: 132,728 bytes;
- SHA-256: `69bbdc04fcb8f113b615525bcb13d40c51ee25e78657739b35efef482ed77f5c`;
- 11 ZIP members: one manifest plus ten declared outputs;
- all ten declared outputs are present and match both declared byte size and
  SHA-256: 10/10;
- source registry shape: 80 rows by 25 columns;
- integration plan: 22 proposed external entities, 14 model use cases, and nine
  phases P0-P8;
- `raw_external_data_included=false`.

The registry columns `exact_formula_ratios`,
`exact_component_concentrations`, and `openness_license` contain ordinal
scores from 0 to 10. They are not booleans, source-table receipts, or legal
license determinations. A score of 10 therefore cannot be reinterpreted as
exact formula evidence, an exact measured concentration, or permission to
reuse or redistribute a source.

Input closure was recomputed against the manifest. Seven of eight declared
project inputs are source-resolvable locally by exact size and SHA-256:

- the inventory v5 hash matches the local alias without the manifest's `(1)`;
- `PROTOCOL.md`, `Meaningful_Complexity_Audit_v2.md`, and the literature ledger
  match;
- the Interaction Atlas JSON and XLSX match;
- `Top_Complexity_Program_Spec_v2.json` matches exactly inside
  `Top_Complexity_Microevent_Bundle_v2.zip`.

`Citrus_Top_Volatile_Program_Spec_v1.json` was not found as a matching loose
file or in the scanned top-level incoming ZIPs. Its expected closure remains
RED: 232,118 bytes and SHA-256
`f3c8111aac417d437d61e79a2540d8fb738eb8abd3ce6e53111418f4cba370fd`.

Disposition:
**LOCAL_SECONDARY_REGISTRY_PRESENT_ONE_PARENT_MISSING_RAW_SOURCES_NOT_INCLUDED**.
Admit the bundle itself only as a secondary reconstruction and retain all 80
rows and the 22-entity proposal as candidate planning metadata. Acquire and
hash-bind each study table, database snapshot, patent, and license artifact
separately. The bundle does not clear FragDB, Fragella, or Olfactorian rights
and does not supply the Atanasova, Le Berre, or Kurtz ratio tables, M2OR source
snapshots, or source licenses.

## Exact Chat B/F attachment census

The Chat B and Chat F transcripts describe reconstructed worker outputs. The
historical targeted direct-member and one-level nested-ZIP scan covered 110
top-level ZIPs and 80 nested ZIPs below 100 MB and initially found:

- zero `Citrus_Top_Volatile_Program_Spec_v1.json` members;
- zero member names matching the targeted `PDS_XHIGH`, `Exact_Ratio`,
  `license_permission`, `integration_permission`, or `source_governance`
  attachment patterns.

That negative local census is preserved as historical evidence, but the Chat B
and Chat F original attachments were recovered from their authenticated
conversations on 2026-08-19. Recovery establishes exact package bytes, not the
truth or authority of their contents. Do not infer that cited primary ratio
tables, source-rights artifacts, permission records, or licenses were attached,
and do not silently regenerate a missing parent merely to make package closure
turn green.

### Chat B exact-ratio recovery and Le Berre geometry correction

Chat B conversation `6a753b14-8180-83ec-84f9-38e1e13e01ec` supplied
`CHAT_B_EXACT_RATIO_CAUSAL_XHIGH_v1.zip`. The authenticated attachment is now
captured at 50,235 bytes with SHA-256
`15ef920283d457ec06e39af6009ae6153e5d835f39d26539d3463806d7c53cd6`.
All 13 members declared by its embedded checksum ledger recompute exactly, and
the archive scanner reports `CLEAR_FOR_RECEIPT_REVIEW`. The governed disposition
is nevertheless **EXTERNAL_BYTES_VERIFIED_NOT_ADMITTED**: the package has unknown
reuse rights, contains generated secondary rows, and confers no source, formula,
inventory, sensory, safety, compounding, or release authority.

The recovery receipt is bound to user turn
`8e2420a7-363c-4fb1-b6b3-ec7edb461c14` and agent message
`fde01494-9d5f-42e7-a1d0-6c7c574f9b90`; those identifiers establish chat
lineage only. Exact package identity is established separately by the captured
bytes, archive member census, and recomputed hashes.

The independently identifiable source is Le Berre et al., *Chemical Senses*
33(4):389-395 (2008), PMID 18304991, DOI
[10.1093/chemse/bjn006](https://academic.oup.com/chemse/article-abstract/33/4/389/267601).
The official abstract describes a ternary target, **four concentration levels
for each component**, every combination, 15 participants, paired comparison to
the target, and intensity, typicality, and pleasantness endpoints. Therefore the
experimental factorial is 4 x 4 x 4 = **64 mixtures**. The target is a separate
paired-comparison reference, not a fifth factorial level. Chat B's 125 symbolic
Le Berre rows (`JND--`, `JND-`, `TARGET`, `JND+`, `JND++` on every axis) are a
derivation error and are quarantined as
`LE_BERRE_FACTORIAL_GEOMETRY_MISINTERPRETED_125_VS_64`.

No Table 1 numeric values are admitted. Earlier values came through a
third-party mirror whose source-use and archive rights are not established.
After legitimate acquisition, retain one rights-qualified source document and
source-scoped extraction records; do not reconstruct or publish the table from
the Chat B package. Do not merge the package's 253 generated ratio arms with the
Interaction Atlas's 253 material-group pairs; the equal counts describe
different ontologies.

### Chat A human-mixture source-admission correction

Chat A conversation `6a753afc-c714-83ec-a854-e6fbb3022048` describes a
human-mixture package, but the exact package filename, bytes, and receipt remain
unrecovered after the same 223-ZIP / 272,268,006-byte census. Do not fabricate
an `external_package_receipt_v1` or treat the chat's combined row counts as one
observation table.

The independently recoverable source families have incompatible grains:

- [Ma et al. 2021](https://www.sciencedirect.com/science/article/pii/S2352340921004273)
  records 222 binary-mixture trials from 72 odorants with eight endpoints and
  duplicated presentations. Its original workbook and the pinned Pyrfume copy
  at commit `8054ea98ed675005ec10e67359902f500e4911b0` were reported byte-identical
  at 487,926 bytes, SHA-256
  `c540f18ba71b778c36756810fff38bdf177c2af9d593567a6dba57a30503c950`.
  Preserve participant, trial, repeat, stimulus, and endpoint nesting; the
  study used up to 30 selected participants per trial, not 30 people total.
- [Snitz et al. 2013](https://pubmed.ncbi.nlm.nih.gov/24068899/) provides
  aggregate pair scores across three experiments. Aggregate rows must never be
  expanded into pseudo-participant observations.
- [Bushdid et al. 2014](https://pubmed.ncbi.nlm.nih.gov/24653035/) provides
  exact triangle-test responses, but its trillion-scale extrapolation is
  excluded from target or model authority in light of the formal erratum and
  published [statistical](https://elifesciences.org/articles/08127) and
  [dimensionality](https://elifesciences.org/articles/07865) critiques.
- Weiss 2012 and Snitz Dataset 1 share the same 191-comparison experimental
  lineage. Represent that derivation explicitly and do not count it twice.

The native B1 source-document/version/extraction spine is suitable provenance,
but local `LabExperiment`, `LabObservation`, identity-scoped property records,
and the heuristic `engine/psychophysics.py` are not suitable published-study
stores. A future additive external-study schema must keep immutable source
rows, experimental units, and endpoint observations separate, retain aggregate
grain explicitly, and split later models by source family rather than random
rows. Disposition:
**CHAT_A_PACKAGE_UNRECOVERED_PRIMARY_SOURCE_FAMILIES_REPRODUCIBLE_EXTERNAL_STUDY_ADMISSION_NOT_IMPLEMENTED**.

### Chat D receptor-source admission correction

Chat D conversation `6a753b22-3490-83ec-bc7b-a0e46c4655c0` claims package
versions with SHA-256 values `e3f0e7841a54fa5117288ccada36a04d7f24fd9f47db5a85d989f0b6e886d48d`
and `8f283781742e6ed51950b4397b486a2b4ec9745835cc20bd278a013f2a3a5743`.
The v1.1 successor is now an exact authenticated attachment capture at
`incoming_review/chatgpt/20260819T125952Z-chat-d-molecular-receptor-6a753b22/CHAT_D_XHIGH_MOLECULAR_RECEPTOR_v1_1.zip`:
8,463,278 bytes with the second SHA-256 above. The predecessor v1 remains
unrecovered. The archive has 22 files under one root; all 21 members declared
by its internal checksum ledger verify. Native archive quarantine reports
`GRAPH_COMPLETE_QUARANTINED` across the outer ZIP and nested XLSX, with no
promotion authority. The package's 36 claimed checks are package-internal
evidence only; its claimed baseline bundle remains unmounted, and bundled
Python plus compiled bytecode were not executed. Disposition:
**EXACT_CHAT_D_V1_1_PACKAGE_RECOVERED_NOT_ADMITTED**.

The bundled 9,461,137-byte Keller/Vosshall workbook has SHA-256
`efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62`,
which is byte-identical to the already governed local source. It is therefore
one source lineage, not an independent replication and not a second B1 row.
The package crosswalk contains 480 identities: 478 source-native PubChem/CAS
rows, one independently reverified CAS rescue (`3796-70-1` to PubChem CID
1549778), and one retained hold. The hold is material: the source calls the
compound isobutyl acetate but records `109-19-0`; current PubChem resolves
isobutyl acetate and CAS `110-19-0` to CID 8038 while `109-19-0` does not
resolve. Do not repair that row by name alone.

Current official-source review establishes three different admission classes:

- [M2OR v1.2.0](https://m2or.chemsensim.fr/) currently reports 771 molecules,
  1,402 receptor sequences, 16 species, 45 references, 77,611 experiments, and
  53,444 pairs. Its [publication](https://academic.oup.com/nar/article/52/D1/D1370/7327067)
  reports an earlier census, so the live export is dynamic rather than an
  immutable publication release. The site is All Rights Reserved and the
  recovered Chat-D ZIP contains no package-level license; retain retrieval metadata/hash
  on `RIGHTS_HOLD`, not redistributed payload or receptor truth.
- [OlfactionBase](https://olfactionbase.com/or-odorant-pairs) currently says
  875 associations in prose (409 human plus 466 mouse), but its official
  81,764-byte XLSX export observed on 2026-08-19 has 875 worksheet rows
  including the header and therefore only 874 data rows (SHA-256
  `451571afffbf102a5cdd18b4e2d16b856b3ccae62f351b275dbfc55bbe81cc0d`).
  The homepage had advanced to "Last Updated on 19th August, 2026" while the
  package retained an August 6 snapshot. The export lacks assay and
  evidence-locator grain. Treat it only as a discovery association on
  `RIGHTS_AND_INTERNAL_CONSISTENCY_HOLD`; do not force either 874 or 875 into
  canonical row truth without a versioned source correction.
- [DoOR v2](https://zenodo.org/records/46554) is a stable Drosophila normalized
  response package with an exact Zenodo file identity. It remains
  species-specific evidence; admission requires an explicit license/attribution
  receipt and must not be presented as human or whole-perfume perception.

Native `ReceptorAssayEvidence` already requires a complete, source-verified
dose-response contract. Most screening records do not satisfy it. `ORTarget`
is too lossy and carries Hill/efficacy defaults that could invent precision,
while `scripts/populate_receptor_data.py` writes broad legacy claims without
assay grain and must not be run or promoted. Future native entities should
preserve raw receptor experiments (including negative rows), derived pair
consensus plus algorithm/version, discovery associations, and species-specific
normalized responses separately. Reuse the existing Keller source manifest
rather than copying its workbook again. A future adapter should bind immutable
release bytes and rights first, then retain source family, species, receptor and
variant, molecule identity state, assay system, concentration/unit, response
mode/value, negative rows, biological/technical unit, reference position, and
derivation algorithm. Live-count snapshots and model outputs must remain
separate from row-level observations. No receptor occupancy, psychophysics,
liking, anosmia, adaptation, formula, OAV, safety, or release authority follows.
Disposition:
**CHAT_D_V1_1_EXACT_QUARANTINED_KELLER_DUPLICATE_DYNAMIC_M2OR_RIGHTS_HOLD_OLFACTIONBASE_PAGE_EXPORT_CONFLICT_DOOR_SPECIES_SCOPED_ADMISSION_NOT_IMPLEMENTED**.

### Chat E physical/analytical package recovery and native-contract diff

Chat E conversation `6a753b36-a0b8-83ec-a7cc-bc79f1d37b47` supplied two exact,
separate attachments. They are captured together under
`incoming_review/chatgpt/20260819T131508Z-chat-e-physical-analytical-6a753b36/`:

- `CHAT_E_XHIGH_PHYSICAL_ANALYTICAL_LANE_v1.zip` is 33,356 bytes with SHA-256
  `685098081c631a0c39e3113d1d3ef3ba08662537bcee3dbcee722b321aa338cf`.
  It has 25 files and all 24 members declared in `SHA256SUMS.json` verify.
  Archive quarantine reports `CLEAR_FOR_RECEIPT_REVIEW`, terminal and
  nonpromoting.
- `CHAT_E_XHIGH_POSTFREEZE_HARDENING_v1.zip` is 86,646 bytes with SHA-256
  `0d989b72a2678359b797c5e936c4aebc818e8fca700dcc2f557ae86321a71212`.
  It has 52 files under one root and all 51 declared payload members verify.
  Its nested v1 ZIP is byte-identical to the separately recovered attachment.
  Archive quarantine reports `GRAPH_COMPLETE_QUARANTINED` across the outer and
  nested ZIPs, terminal and nonpromoting.

The v1 package is a secondary planning registry, not a physical-data release.
It lists 12 source records (PubChem, NIST WebBook, NIST26 EI/RI, MassBank,
MoNA, GNPS and six papers) and six release-model records (DPG Henry,
diffusion-tube, radial diffusion, COSMO-RS, UNIFAC and chromatographic-spectrum
recognition). Its declared holds are the controlling boundary: baseline bytes,
source bytes, numeric tables and matrix transfer are absent. The package's
23/23 result is a package claim; bundled code was not executed. The package has
no blanket license, and the registry spans open, licensed and paper-specific
sources, so rights must be resolved per exact source and operation before any
row-level admission.

The post-freeze addendum contributes one useful bounded artifact: a six-item
defect ledger. It reproduces that v1 (1) forbids in schema the caller flag its
guard needs, (2) lets caller attestation bypass matrix/apparatus checks, (3)
makes its `STRICT_OAV` branch schema-unreachable, (4) omits exact
identity/endpoint/numeric/condition compatibility from strict OAV, (5)
underconstrains authentic-standard and calibrated-quantitation evidence, and
(6) does not separate public claims from host-verified bindings. Its 88/88
result and proposed v1.1 code remain package-internal evidence; no package code
was imported or executed, no source bytes were added, and machine-domain code
adjudication plus host adoption remain explicit holds.

The current native implementation supersedes those proposed runtime changes:

- C3 emits a typed `VersionedModelResult`; C8 `PredictedGasModelBinding`
  requires that exact computed, applicability-eligible result and verifies
  operation, output quantity, release, request, domain and environment hashes.
  Legacy caller `within_model_domain` authority is rejected. Matrix,
  temperature, pressure, relative humidity and application-environment
  mismatches fail closed, while measured gas remains a separate evidence path.
- C8 strict OAV is answerless unless measured gas and threshold evidence have
  compatible identity, endpoint, matrix, conditions, units and uncertainty.
  Unsupported perceptual claims remain withheld.
- Laboratory Beta B5 separately enforces authentic-standard/co-injection
  evidence for confirmed identity, calibrated concentration with working
  range, uncertainty, QC and exact matrix/analyte/method calibration scope, and
  forbids GC-O evidence from claiming exact chemical identity.

Fresh local verification passed **90/90 C8 tests** and **84/84 B5 analytical
service/schema tests** in the backend's governed Poetry/Python 3.11
environment. An initial root Python 3.14 attempt produced 44 setup errors from
an unavailable `greenlet._greenlet` binary and 40 passing non-database tests;
that environment mismatch is not counted as a B5 logic failure or success.

The recovered receipts are
`data/governance/chat_e_physical_analytical_lane_v1_package_receipt_20260819.json`
and
`data/governance/chat_e_postfreeze_hardening_v1_package_receipt_20260819.json`.
Disposition:
**CHAT_E_EXACT_V1_AND_POSTFREEZE_PACKAGES_QUARANTINED_DEFECT_LEDGER_PRESERVED_NATIVE_C3_C8_B5_CONTROLLING_SOURCE_BYTES_RIGHTS_MATRIX_TRANSFER_AND_RELEASE_HELD**.
The distinct later transcript-owned v1.2 ZIP claim with SHA-256
`8170ac4e7f558698b97a746ac30cd39110b371325b92c542a1ca3b90d2397898`
was unresolved at this checkpoint. The later exact recovery below supersedes
only that missing-byte statement; it does not alter the v1/v1.1 admission or
native-runtime decisions.

### Chat E v1.2 machine-domain adjudication recovery and literature diff

The separate XHIGH conversation `6a754c18-a948-83ec-a456-1923b470d0cc`
contains five rendered messages (three assistant, two user) and supplies the
exact `CHAT_E_XHIGH_DOMAIN_ADJUDICATION_v1_2.zip`. It is captured under
`incoming_review/chatgpt/20260819T170000Z-xhigh-chat-e-v1-2-6a754c18/`:

- 120,861 bytes, SHA-256
  `8170ac4e7f558698b97a746ac30cd39110b371325b92c542a1ca3b90d2397898`;
- 39 archive members, with all 38 non-ledger members matching the embedded
  checksum ledger;
- three terminal archive-graph nodes: v1.2, its exact embedded v1.1 parent and
  the v1 package nested within v1.1;
- embedded v1.1 is byte-identical to the separately recovered 86,646-byte
  package with SHA-256 `0d989b72a2678359b797c5e936c4aebc818e8fca700dcc2f557ae86321a71212`.

The useful delta is narrow. The package records six source-specific model
domains for Costa DPG/Henry, Teixeira axial diffusion, Almeida radial
diffusion, Dupeux COSMO-RS property priors, Cetti ionic-liquid VLE and Truan
chromatographic-spectrum candidate retrieval. Independent publisher-page
checks confirmed the six article identities and high-level study domains:
`10.1021/acs.iecr.5b03852`, `10.1002/aic.14106`, `10.1002/aic.17351`,
`10.1002/ffj.3690`, `10.1021/acs.jced.7b00116` and `10.1002/ffj.3564`.
The Costa 2015 DPG paper is distinct from the group's 2017 mineral-oil study;
the two must not be conflated. JRC107493 is the official QMRF author/editor
guidance and JRC107494 is the corresponding reviewer guideline/protocol; both
describe QMRF reporting around OECD model-validation principles.

Those checks do not unlock the missing full numeric tables, licensed COSMO-RS
inputs, complete source method settings or Truan's private 4,106-ingredient
commercial reference database. The package's 108 passing tests and 35-case
adversarial replay are package claims and were not executed locally. The
package itself keeps `HOLD_HOST_ADOPTION`, `HOLD_FULL_NUMERIC_SOURCE_TABLES`,
`HOLD_RUNTIME_PUBLICATION_AND_CI`, `HOLD_PHYSICAL_OR_EMPIRICAL_RESULTS` and
`HOLD_STRICT_OAV_CALCULATION`.

Native-code diff found no justified runtime replacement. C3 already hashes
identity, matrix, ranges, environment, calibration domain and known failure
modes; C8 rejects cross-matrix and condition mismatches and binds exact C3
results; B5 separately binds analytical method, matrix, calibration, identity,
uncertainty and QC. The v1.2 codebook is therefore retained only as
nonexecuted source-specific migration input. Its exact receipt is
`data/governance/chat_e_domain_adjudication_v1_2_package_receipt_20260819.json`.
Disposition:
**CHAT_E_V1_2_EXACT_DOMAIN_ADJUDICATION_QUARANTINED_MACHINE_CODE_GAP_CAPTURED_NATIVE_C3_C8_B5_CONTROLLING_HOST_ADOPTION_SOURCE_TABLES_PRIVATE_REFERENCE_DATA_EMPIRICAL_TRUTH_AND_RELEASE_HELD**.

### Chat C patent, historical-formula, and Olfactorian correction

Chat C conversation `6a753b26-53b4-83ec-92ec-02cdc8d63629` now has an exact
authenticated attachment capture at
`incoming_review/chatgpt/20260819T124503Z-chat-c-formula-corpora-6a753b26/CHAT_C_FORMULA_CORPORA_PATENT_MINING_XHIGH_v1.zip`:
1,319,192 bytes, SHA-256
`ce6e95f40cd53bdc3c94f169ccb9761638500ae085be23df7b7abc2db94bb42d`.
The archive has 27 files under one root; all 26 members declared by its internal
checksum ledger verify exactly. Native archive quarantine reports
`GRAPH_COMPLETE_QUARANTINED` with five large-PDF/TXT partial member scans and no
promotion authority. The package's claimed 21 validation checks and mutation
census are package-internal evidence only; its baseline bundle remains
unmounted. Disposition: **EXACT_CHAT_C_PACKAGE_RECOVERED_NOT_ADMITTED**.

The independently identifiable primary sources support a source-formula
grammar census, not executable perfume formulas:

| Source block | Preserved source geometry |
|---|---|
| [US20120058073A1 Example 6](https://patents.google.com/patent/US20120058073A1/en) | 22 ordered rows; declared total 1,000 parts |
| [US8168163B2 Example III](https://patents.google.com/patent/US8168163B2/en) | Two dependent comparison arms; 13 row positions each; explicit em-dash absences retained; each arm totals 990 |
| [US6495186B1 Example 1](https://patents.google.com/patent/US6495186B1/en) | 25 ordered rows with neat and explicitly diluted product-basis entries |
| [EP3042891A1 Example 6](https://patents.google.com/patent/EP3042891A1/en) | 32 ordered rows; declared total 1,000 parts; trade products and explicit dilutions retained; qualitative four-person panel context |

The exact patent census is 105 rows across five arms. Primary-source comparison
also exposed a package defect: the test-material absence in the minus arm and
the DPG absence in the plus arm are em dashes in US8168163B2, but both become
numeric `0` in the package registry and grammar CSV. This contradicts the
package's own `original_rows_preserved` claim. Patent examples remain
source-owned class-G evidence, not commercial formulas, independent
replication, current claim/FTO analysis, safety evidence, or production
authority. An em dash or blank is not numerical zero, and a 990-part source arm
must not be silently normalized to 1,000. The two absence rows must be rebuilt
from the primary source as typed absences before any B1 admission.

[Deite's 1892 treatise](https://www.gutenberg.org/files/50139/50139-h/50139-h.htm)
adds two historical source blocks: *Extrait Jockey Club No. 1* has 16 ordered
drachm rows with a declared 520-drachm total, while *Cologne Water, Quality I*
has nine rows in mixed gallons, ounces, and quarts plus process timing. A
separate proportional Jockey Club projection may be mathematically admissible;
the Cologne block remains conversion-HOLD until units, density, and temperature
are governed. The 105 patent rows plus 25 Deite rows define a 130-row source
grammar target. The recovered package contains 130 rows, but the absence
collapse means it is not itself a lossless governed extraction.

Native B1 source versions and extraction records can preserve locator,
structure context, original wording/value, parsed value, units, uncertainty,
ambiguity, rights, and hashes. They are the correct source spine. Executable
`LabFormulaVersion` components are stock-bound physical records and must not be
populated with patent, book, or API source formulas. The legacy patent helpers
accept only material-to-float percentage maps and therefore lose order,
duplicates, raw units/totals, product basis, comparison-arm dependence,
explicit absence, rights, and transformation lineage. Only a separately
reviewed derived projection may feed those helpers.

The current [Olfactorian API](https://olfactorian.com/developers) is read-only,
published-data-only, admin-approved OAuth2/PKCE with per-user consent and
`formulas.read` / `materials.read` scopes. Its API reports omitted dilution as
100% neat; that must be recorded as a source default/omission, never as measured
stock identity. The current [Olfactorian terms](https://olfactorian.com/terms)
prohibit scraper/robot access, default service use to personal noncommercial
use, preserve user ownership, and provide unpublish/delete behavior. A future
adapter must therefore be default-off, OAuth-only, secret-safe,
tombstone-aware, and blocked from persistence, training, or redistribution
until exact operation rights are established. `knowledge/CHEMICAL_SEARCH_PROTOCOL.md`
currently mandates direct Olfactorian URL fetching and must be quarantined or
revised before any adapter work. Classification:
**CHAT_C_PACKAGE_EXACTLY_RECOVERED_QUARANTINED_SOURCE_ABSENCE_COLLAPSE_AND_RAW_FORMULA_PERSISTENCE_OLFACTORIAN_REUSE_RIGHTS_NOT_IMPLEMENTED**.

### Chat F channel- and operation-scoped rights correction

Chat F conversation `6a753b43-9644-83ec-92ad-7d66d62e7ebe` claims a 20-member
rights package with SHA-256
`ca290ec0819bc2381beec4a3a53d504517996ac092d050d0bd5d11bf5556b6b0`.
The authenticated attachment was recovered on 2026-08-19 as
`incoming_review/chatgpt/20260819T121134Z-chat-f-rights-6a753b43/Perfume_Chem_External_Evidence_F_Lane_v1.zip`:

- exact size: 68,531 bytes;
- exact SHA-256:
  `ca290ec0819bc2381beec4a3a53d504517996ac092d050d0bd5d11bf5556b6b0`;
- 20 files, with all 19 entries in the embedded `SHA256SUMS.json` independently
  recomputed exact;
- archive scan `CLEAR_FOR_RECEIPT_REVIEW`, with promotion false;
- receipt:
  `data/governance/chat_f_external_evidence_f_lane_v1_package_receipt_20260819.json`.

Transport integrity does not establish rights authority. All 80 rows in
`LICENSE_AND_PERMISSION_LEDGER.csv` say
`rights_artifact_present_in_worker_package=NO`; 65 rows have no
`verified_at_utc` and remain
`BASELINE_CLASSIFICATION_NOT_LIVE_VERIFIED_IN_F_LANE`. The package omits the
referenced `PDS_XHIGH_MODULE_MANIFEST_v1.json` and
`perfume_data_science_source_registry_v1.csv` parents, and it contains a compiled
Python cache. No package code was executed or installed. The local 132,728-byte
`Perfume_Data_Science_Extreme_Research_Bundle_v1.zip` remains a distinct
secondary planning registry whose 80 rows contain ordinal scores, whose raw
external data are absent, and whose declared lineage is incomplete. Equal row
counts do not establish package identity or permission.

Current official terms show why one blanket `integration_allowed` value would
be unsafe. This is a descriptive engineering classification, not legal advice:

- [FragDB's paid-channel terms](https://fragdb.net/legal) permit several own-use
  and internal/model activities while restricting redistribution, competing
  services, credential sharing, and repeated automated downloads. Its
  [GitHub sample](https://github.com/FragDB/fragrance-database) and
  [Kaggle sample](https://www.kaggle.com/datasets/eriklindqvist/fragdb-fragrance-database)
  expose different license channels; each artifact and upstream UGC scope must
  remain separate.
- [Fragella's API terms](https://api.fragella.com/terms-of-use.html) grant a
  revocable API-use license but prohibit standalone redistribution and large
  caching that circumvents fresh API access unless a plan permits it.
- [ScentRev's current terms](https://mcp.scentrev.com/terms) prohibit bulk
  underlying-dataset extraction, raw-access resale, rate-limit circumvention,
  and directly competing datasets; the page also labels itself a general
  template pending counsel. Production/bulk use remains HOLD.
- [Fragrantica's terms](https://www.fragrantica.com/Terms-of-Service.phtml)
  explicitly prohibit unauthorized automated extraction, dataset/vector
  creation, and AI/ML use without written consent. The
  [PerfumAPI repository](https://github.com/seccaz/PerfumAPI) says it scrapes
  Fragrantica for testing/education; its code visibility cannot confer upstream
  content rights.
- Infrastructure metadata is field- and artifact-scoped:
  [OpenAlex data are CC0](https://developers.openalex.org/),
  [Crossref bibliographic metadata are generally open but abstracts retain
  publisher/author copyright](https://www.crossref.org/documentation/retrieve-metadata/),
  and [Zenodo metadata are CC0 while files follow each deposit's license](https://about.zenodo.org/policies/).
  [Public GitHub visibility without a license retains default copyright](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

B1 now round-trips the six-field structured rights object and claim-scoped
source relations without loss. The additive operation-scoped layer is also
implemented natively as immutable `LabSourceUseConstraintVersion` records.
Every assertion binds the exact subject source version, terms source version,
artifact scope and locator, channel, action, purpose, plan/volume/retention and
other structured obligations, effective/retrieval dates, review state,
legal-review flag, supersession, and record hash. The action vocabulary
separates discovery metadata, API fetch, local cache, source-byte archive,
internal analysis, external transmission, ML training/evaluation, derivative
publication, raw redistribution, and commercial runtime. Decisions are
source-declared `DECLARED_ALLOWED`, `DECLARED_PROHIBITED`, `UNRESOLVED`, or
`CONFLICT`—not Sol legal conclusions.

Assessment uses only the latest version of each assertion chain and requires an
exact scope match. Missing assertions, unreviewed source or terms versions,
unresolved/conflicting decisions, unmodeled obligations, legal-review holds,
or missing request dimensions remain `HOLD`. The B9 report exposes the records
read-only with authority state
`SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION`; there is no blanket
`integration_allowed` field. Classification:
**CHAT_F_EXACT_PACKAGE_RECOVERED_TRANSPORT_GREEN_RIGHTS_ARTIFACTS_AND_BASELINE_PARENTS_ABSENT_OPERATION_SCOPED_NATIVE_MODEL_CONTROLS_NO_ROW_IMPORT**.

### Chat G schema-package recovery and native persistence disposition

Chat G conversation `6a753b49-e6dc-83ec-9224-48e24f28e73d` claims a
34-table `ee_*` completion ZIP with SHA-256
`feb747fa9589dfeb621e9c6312bfce291f1aa9fe306ad988aa841cf90eb6c278`.
The authenticated attachment was recovered on 2026-08-19 as
`incoming_review/chatgpt/20260819T122123Z-chat-g-external-schema-6a753b49/Perfume_Chem_External_Evidence_CHAT_G_XHIGH_v1.zip`:

- exact size: 62,670 bytes;
- exact SHA-256:
  `feb747fa9589dfeb621e9c6312bfce291f1aa9fe306ad988aa841cf90eb6c278`;
- 31 files, with all 30 entries in the embedded `SHA256SUMS.json` independently
  recomputed exact;
- proposed schema census: 34 `ee_*` tables, 10 indexes, 2 views, and 64
  append-only triggers;
- archive scan `CLEAR_FOR_RECEIPT_REVIEW`, with promotion false;
- receipt:
  `data/governance/chat_g_external_evidence_xhigh_v1_package_receipt_20260819.json`.

Transport integrity does not clear integration. The package's own baseline
reference says the exact parent SQL and SQLite bytes were not mounted; no
SQLite database is a package member. Its worker manifest keeps
`HOLD_BASELINE_BYTES` and `HOLD_PARALLEL_A_F_PACKAGE_BINDING` open and says the
byte-for-byte parent migration and final A-F parser binding were not run. No
package code or schema was executed, installed, or merged.

Two earlier local artifacts overlap the subject but remain distinct from the
recovered Chat G package:

- `Perfume_Data_Science_Extreme_Research_Bundle_v1.zip` is 132,728 bytes,
  SHA-256
  `69bbdc04fcb8f113b615525bcb13d40c51ee25e78657739b35efef482ed77f5c`.
  Its 22-entity integration proposal is secondary planning metadata and says
  raw external data are absent.
- `Perfume_Chem_XHIGH_Host_Remediation_RC2_LOCAL_READY.zip` is 117,597 bytes,
  SHA-256
  `fc502585c355efc8890afa699a7931cb0f845b0ee102ddd1b6358cd1dc4626ba`.
  It contains a historical default-off read-only adapter and receipts that
  refer to frozen archive SHA-256 `14996a27...` and database SHA-256
  `6ed06ff8...`; those frozen objects are not members of the local package and
  are not mounted as exact local bytes. Its 34-table claims do not prove
  identity with either the recovered package or its missing parent database.

The accepted A0 ADR makes Laboratory Beta SQL the sole persistence authority
and forbids new writes to a second store. B1 already owns immutable source
versions, extraction rows, structured rights, scoped derivations, locators,
and hashes. Conversely, native `LabExperiment` is a local physical-lab model:
every `LabSample` requires a `lab_bottles.id`. It cannot represent published
participants, groups, or aggregate-only observations without a category
error. `external_candidate_v1.json` is likewise a formula-reconstruction
candidate contract, not a general published-study schema.

The smallest native slice is now implemented under Laboratory Beta and reuses
B1 provenance:

1. source-bound external study version;
2. stimulus version and ordered stimulus components;
3. condition/arm, including ratio, omission, and addition without a separate
   ratio-truth system;
4. experimental unit with explicit `PARTICIPANT`, `GROUP`, `AGGREGATE`, or
   `SAMPLE` grain;
5. endpoint observation with original unit, timepoint, replicate/aggregation
   grain, source row/locator, and record hash;
6. evidence-backed external identity crosswalk; and
7. explicit source conflicts without compressing contradictory wording,
   extraction ambiguity, or source-integrity holds.

Migration `20260810_0016` installs eight append-only native tables for those
roles. Admission requires an exact operation-scoped B1 `INTERNAL_ANALYSIS`
decision of `DECLARED_ALLOWED`, an accepted source record, and an accepted B1
extraction for every staged record under scope `EXTERNAL_STUDY_ADMISSION`.
The source-family key must equal the B1 independence group; every child stays
inside one study graph, aggregate rows cannot become participant observations,
and identity crosswalks cannot silently replace the source identity. A
deterministic read-only projection replays the source, extraction, study, and
child hashes and explicitly withholds formula, inventory, physical-observation,
sensory-truth, model-training, and release authority. No `ee_*` store, generic
query API, or alternate persistence authority was added.

Patent/historical formulas remain B1 source extractions plus nonexecuting
staging. Receptor assays, market proxies, model output, physical measurements,
and human sensory endpoints remain separate evidence classes. Published
aggregate rows are never expanded into pseudo-participants, and no adapter may
write canonical tables or promote matrix, model, patent, receptor, or market
evidence into another authority class. PROV-O, RO-Crate, Frictionless Table
Schema, ISA, and SPDX expressions may be interchange/validation profiles only,
not persistence authorities. Classification:
**DATA_AMBER_CHAT_G_EXACT_PACKAGE_RECOVERED_PARENT_DATABASE_AND_A_F_BINDINGS_ABSENT_PARALLEL_STORE_REJECTED_NATIVE_EXTERNAL_STUDY_ADMISSION_CONTROLS**.

### Chat 8 metrology-oracle recovery correction and native boundary

Chat 8 conversation `6a74c82b-834c-83ec-8600-43c39d9329e9` claims a
qualification-only Active-Equivalence Metrology Oracle ZIP with SHA-256
`50613e4873b99a5d2fe32f985810d593119eb43f279668fe7bcf0fa5ac39680f`.
Exact hashing found no matching archive in either the Downloads or local
`incoming_review` ZIP estates. The claimed fixtures, tests, Decimal precision,
uncertainty propagation, schemas, and PASS/HOLD/FAIL rules are therefore
unverified chat assertions. No package code or fixture was imported.

The recovery pointer is bound to user turn
`dcc3218b-d27f-4823-acd8-4aad836980f8` and agent message
`ce40d2cf-e731-4f88-8b0b-a44138afbdcd`; neither identifier substitutes for an
exact package receipt.

The native review found two different scopes. Backend stock lineage is the
planned mass-basis transition authority; the engine pre-mix guard is a nominal
volume/OAV safety screen. The native cutover now makes that distinction
machine-readable:

- backend `formula-stock-lineage-v3` computes planned active mass from
  canonical `requested_mass_g_decimal_text` and
  `active_fraction_decimal_text`, accepts only mass-fraction authority, binds a
  versioned tolerance rule and all comparison rows into
  `comparison_sha256`, and reports `PASS_PLAN_ACTIVE_EQUIVALENT`;
- its receipt says `PLANNED_FORMULA_LINEAGE_ONLY`, while physical measurement,
  uncertainty, cross-basis conversion, formula release, and scientific release
  authority remain false;
- migration `20260810_0014` deliberately leaves legacy exact-decimal fields
  NULL rather than manufacturing precision from SQL floats; exact text is
  authority, the sibling float is a compatibility projection, and missing,
  noncanonical, or disagreeing values fail closed;
- `lab-export-v5` preserves the exact fields. V1-v4 remain supported
  compatibility formats but cannot create exact-decimal authority;
- persisted v3 receipts must equal native recomputation before a revision can
  drive physical execution; old or mismatched receipts fail closed; and
- the engine guard reports `SCREEN_CLEAR`, `SCREEN_REVIEW`, or `SCREEN_BLOCK`
  and explicitly directs planned equivalence to backend stock lineage. Its
  generic G15 gate status is only a screening disposition.

This is not the final metrology layer. Exact planned values now survive
persistence, but density context, standard uncertainty, significant
correlations, calibration/traceability, and a validated physical conformity
rule remain absent. Those records are required before physical PASS authority
can exist. The boundary follows
[IUPAC mass fraction](https://goldbook.iupac.org/terms/view/M03722),
[IUPAC volume fraction](https://goldbook.iupac.org/terms/view/V06643),
[JCGM 100](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e),
[JCGM 106](https://www.bipm.org/en/doi/10.59161/jcgm106-2012), and
[NIST metrological traceability](https://www.nist.gov/metrology/metrological-traceability).
The project hash profile is deterministic but is not claimed as RFC 8785
conformance.

## Pointer-only Chat 1-3 source recovery pack

`incoming_review/PROGRAM_V3_CHAT1_3_SOURCE_RECOVERY_PACK_20260807.zip` is
present:

- size: 513,132 bytes;
- SHA-256: `5eb12ae7b4ece04a90df4bbc1e89caf2beb8f53d678b106120b5df6c1e26a2c1`;
- 50 ZIP members, including its own package manifest;
- expected specialist artifact records: 28;
- specialist exact bytes included: 0;
- File Library pointer records: 28;
- supporting local exact files included: 11;
- byte closure: `PARTIAL / FILE_LIBRARY_ONLY SPECIALIST BYTES NOT EXPORTABLE
  FROM THIS RUNTIME`.

The pack explicitly states that no File-Library-only source was reconstructed
from snippets, summaries, schemas, or worker manifests, and its instructions
say that every `.pointer.json` is a retrieval instruction rather than source
content. The 11 included byte-bearing files are governance, Interaction Atlas,
and engine-v1 ancestry; they are not the Chat 1-3 specialist deliverables.

Disposition: **POINTER_RECOVERY_INVENTORY_ONLY**. Preserve known names and
hashes as retrieval targets. Do not count the 28 specialist records as locally
admitted and do not regenerate substitutes.

## Mechanically coherent but incomplete “Canonical” upload kit

`incoming_review/Complex_Perfumery_Canonical_Source_Upload_Kit_v1.zip` is a
coherent transport bundle, not canonical authority:

- size: 7,487,981 bytes;
- SHA-256: `decfc7b65878410360e4862014324a9dd5e863ea29ac0e8384d8f7ab38494639`;
- manifest-declared included files: 29;
- recomputed member size and SHA-256 matches: 29/29, drift 0;
- absent/File-Library-only entries: 10.

The live manifest marks **7** of the 10 absent entries required:

1. `SOL_5_6_PRO_Strict_Perfume_Reverification_V2.md`;
2. `CrossBrand_120_Master_Audit_GPT56_Pro_PR_E01_C1_SYNCED.xlsx`;
3. `CrossBrand_120_Testable_Formula_Book_GPT56_Pro_PR_E01_C1_SYNCED.xlsx`;
4. `FINAL_VERIFICATION_REPORT.md`;
5. `PHASE_C_F_TERMINAL_CHECKPOINT.md`;
6. `FINAL_ADDENDUM_VERIFICATION_REPORT.md`;
7. `SOURCE_GAP_CERTIFICATE_v2.md`.

The included CrossBrand workbooks label themselves local available copies and
explicitly state that they cannot substitute for the exact synced authorities.
The package filename, internal use of “canonical,” and successful member hashes
do not grant formula, inventory, empirical, safety, or release authority.

Disposition: **HASH_BOUND_SECONDARY_TRANSPORT_PACKAGE_INCOMPLETE_AUTHORITY_CLOSURE**.
Keep per-member identities and all ten missing records explicit.

## Deduplicated unintegrated-intake receipt

Two loose files named
`PERFUME_CHEM_UNINTEGRATED_INTEGRATION_INTAKE_20260807.zip` and
`PERFUME_CHEM_UNINTEGRATED_INTEGRATION_INTAKE_20260807 (1).zip` are exact
duplicates, not independent sources:

- each is 16,597,813 bytes;
- each has SHA-256
  `7d2e9769ab805c2f5d9575da7432d925ba34471c4f71aeaf4b451a842dc13aa3`;
- ZIP entries: 175;
- `SHA256SUMS.txt` rows recomputed successfully: 174/174.

The package's own intake summary is plan-only:

- local files discovered: 181;
- exact local files included: 162;
- local files excluded: 19;
- remote File Library rows: 98;
- archive-category records: 29, stored under
  `04_ARCHIVE_PACKAGES_DO_NOT_IMPORT_DIRECTLY`;
- truth rule: `NO RETURNED_AND_APPROVED_PLAN => NOT INTEGRATED`;
- execution authorized: false;
- physical results created: false;
- formula mutation: false.

The intake does contain the exact-named `PR_E01_C1_SYNCED` CrossBrand
workbooks under its authority-context folder, and their members pass the intake
checksum ledger. That improves current byte recovery relative to the older
upload kit and Program-v3 runtime, but it does not itself admit the workbooks or
resolve their scientific/formula authority.

Disposition: **ONE_DEDUPLICATED_PLAN_ONLY_INTAKE_RECEIPT**. Preserve one package
identity and assign a per-artifact disposition. Never bulk import the 162 files,
never import the 29 archive-category records directly, and never count the `(1)`
copy as independent provenance.

## Program-v3 final package boundary

`incoming_review/PROGRAM_V3_FINAL_INTEGRATION_PACKAGE.zip` is present:

- size: 61,935 bytes;
- SHA-256: `919d08c69b21db887decaf029945b9c9b1c24ed58b919812dee79d0b598c467e`;
- 12 final integration/report/register files only;
- required specialist artifacts reported located: 58/58;
- worker-declared hashes surfaced: 44/58;
- partial upstream hash closure: 14/58, all from Chat 1 and Chat 3;
- target engine: `NOT_RUN`;
- program approval: `NOT_ISSUED`;
- empirical release: `NOT_AUTHORIZED`;
- Phase G: `LOCKED_NOT_AUTHORIZED`;
- validation final state: `PASS_WITH_PROGRAM_AND_LANE_HOLDS`.

The manifest explicitly says that the package does not reconstruct or repack
File-Library-only upstream bytes. “Located” records discovery and worker
evidence, not local mounting and independent rehashing. Exact synced-workbook
closure was absent in that package's original runtime; the later intake receipt
above is a separate, still-unintegrated recovery source.

Disposition: **TERMINAL_SECONDARY_ARCHITECTURE_AND_REGISTER_SNAPSHOT**. The name
`FINAL_INTEGRATION` does not prove upstream source admission, target-engine
execution, physical validation, program approval, or release.

## File-Library recovery identities only

`incoming_review/Perfume_Chem_Full_Recovery_Capture_Kit_20260808.zip` is a
36,358-byte recovery utility/register package with SHA-256
`ae3b36afe359f50871f742280341986bfd0b494c75a6e7da4b762932c5bdf570`.
Its queue records these exact Program-v3 retrieval identities:

- `PCV3_CHAT1_MEANINGFUL_COMPLEXITY_MODEL_V3_COMPLETE.zip` — SHA-256
  `10acff0eb8f9e40dc0bd0e8152e04eb3c6440393c39dc950ccc3e96dccc1f6e1`;
- `PCV3_CHAT2_EXPERIMENTAL_DATA_MODEL_v1.zip` — SHA-256
  `db638ab82c7e1a798297a9f4376014b9f51965511ae1d65132e57b4d12c9c9eb`.

Both are labeled
`VERIFIED_IN_FILE_LIBRARY_RECEIPT__NOT_CONFIRMED_MOUNTED`. The same queue lists
11 accord-intelligence package targets whose exact bytes remain required before
installation. These are recovery identities, not local bytes, admission, or
authority.

## OAV-HSG candidate package versus native engine

`incoming_review/Perfume_Chem_OAV_HSG_v1_3_Package.zip` is internally coherent:

- size: 1,154,539 bytes;
- SHA-256: `4327c39aa28772fe74310b1d36d42fd7eeac7d654b244965264b24b4f5d3d552`;
- ZIP entries: 56;
- manifest payloads recomputed successfully: 55/55;
- package claim: 48 standalone tests;
- contents include ten generated formula fixtures, 62 registry materials, 28
  evidence records, a v5 stock map, code, and large modeled outputs.

Its own contract withholds strict OAV unless context-compatible calibrated
measured-air concentration and threshold evidence exist. Temporal anomalies are
review-only and automatic formula editing is false. The derived trajectories
are not empirical headspace.

The useful adversarial cases were compared with the native implementation.
Native tests already cover missing ODT blocking, `14 x 0.10 = 1.4` active-dose
receipt consumption, Citronellol and Lemonile 10x stock/dose failures, a generic
same-stock 10x revision jump, and advisory-only modeled OAV dominance. Tuberose,
Immortelle, and Geranium names do not require a second guard because the native
quantity invariant is material-agnostic; natural-mixture OAV remains a separate
composite calculation.

Disposition: **COHERENT_SECONDARY_CANDIDATE_DUPLICATES_NATIVE_ENGINE**. Do not
import its code, registry, formulas, modeled trajectories, or outputs wholesale.
Retain only nonduplicative context-contract or adversarial-test ideas after
native review.

## Linked-continuation OAV identity and abstention correction

The linked Complex Perfumery continuation reports a newer OAV identity-gate
package with claimed ZIP SHA-256
`da6f5961aae3d7ba15054f5925dedc76b6feb973eaddb56c3e8fc4d786ce7cbc`.
No matching archive or literal hash was recovered in the reported bounded local
census, so its package files and 32/32 validation claim remain unaccepted.

The reported defect was independently reproduced against the live repository:
a gate built from 20 microliters of Citronellol at 10% could be reused by an OAV
request that independently declared the same raw quantity as neat. The old
check compared windows and positive raw quantities but not stock identity,
inventory snapshot, fraction/basis/carrier, active dose, source lineage, or a
stock/dose receipt SHA. The request was accepted while carrying a live 10x
contradiction. Separately, a legitimate unknown `vapor_ppm=None` raised
`TypeError` instead of preserving abstention. The existing twelve-test OAV
suite passed before these adversarial cases were added, proving a coverage gap
rather than safety of the old path.

The native correction does not import the missing package or add another OAV
engine:

1. `FormulaDoseReceipt` is the exact stock/dose identity and binds V5 snapshot
   and workbook identity, stock IDs, source-row/authority lineage,
   fraction/basis/carrier, raw and active quantities, formula-input identity,
   and receipt SHA;
2. `GateReport`, `FormulaState`, simulation, scaling, robustness, OAV, scoring,
   audit, and report surfaces retain and verify that receipt identity;
3. a gate-bound OAV request must agree with receipt formula, stock, quantity,
   matrix/context, temperature, and windows. A stale snapshot, different stock
   ID, fraction mismatch, or unbound standalone request cannot issue primary
   authority;
4. strict OAV reuses `engine.physics.headspace_oav` and returns typed,
   answerless `ABSTAINED` results for missing or incompatible measured-air and
   threshold evidence. Unknown candidate-air remains unknown rather than zero,
   NaN, a fallback ppm, or an exception; and
5. legacy modeled OAV remains `LEGACY_HEURISTIC_ADVISORY_ONLY`, primary status
   `WITHHELD`, authority rank zero, and barred from release scoring, optimizer
   reruns, safety, presentation, or formula mutation.

The scientific boundary remains unchanged. Matrix-specific threshold evidence
([Perry and Hayes 2017](https://pubmed.ncbi.nlm.nih.gov/28231131/)),
application-matrix/skin headspace work
([Vuilleumier et al.](https://doi.org/10.1111/j.1467-2494.1995.tb00110.x)),
and concentration-dependent mixture interactions
([Tian et al. 2020](https://pubmed.ncbi.nlm.nih.gov/32448580/)) all oppose
transferring raw formula dose into universal candidate-air or perceptual
authority. Even an exact receipt-bound modeled OAV is above-threshold screening
only; strict empirical OAV still requires compatible measured candidate-air
and threshold evidence.

## Linked-continuation PR-3 gate-identity correction

The out-of-project continuation's broad claim that 47 skeleton callbacks were
undefined is false for the current runtime. A fresh census resolved all 47/47
`_SKELETONS` products and all 143/143 dispatch targets as callable, with zero
runtime-missing targets; the existing applicability suite also executes the
generated families. Runtime completeness does not establish their scientific
validity, but no 47-function fabrication or replacement is warranted.

One narrower release-governance defect was real and reproduced. Duplicate
canonical materials were dispatched as `duplicates` while `_gate_duplicates`
returned `duplicate_canonical_materials`. Because advisory policy used the
returned ID, a genuine duplicate FAIL was demoted to WARN and aggregate status
became WARN. The native repair preserves `duplicate_canonical_materials` as the
established report identity and now uses it as the sole dispatch and
hard-blocking identity; the dead `duplicates` and `duplicate_materials` aliases
were removed. The same adversarial replay now remains FAIL through policy and
aggregate status.

This closes only the naming drift. It does not grant formula, stock, safety,
scientific, sensory, physical, publication, or release authority, and it does
not claim that every dynamically generated skeleton rule is validated.

## Stock-basis hardening patch package

`incoming_review/Perfume_Chem_Stock_Basis_Hardening_v1.zip` is also coherent but
historical:

- size: 59,012 bytes;
- SHA-256: `a07e189c88c121be5da0242a9f4a36f5da30e7c5d0d4bfd640d9dd2240e75477`;
- manifest payloads recomputed successfully: 24/24;
- status: `PATCH_READY_NOT_REPOSITORY_INTEGRATED`;
- observed historical head:
  `2e46e4ce5795014e92924102c38c1358d7a9fdca`;
- standalone tests: 16 passed; repository-native tests were not run;
- it packages `.pytest_cache`, further confirming it is a handoff artifact, not
  a clean current source tree.

The live hard-gate JSON contains eight gates, SG0-SG7. Reusable candidate
evidence includes the v5 workbook hash
`e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`,
source-derived stock snapshot/recalculation data, and the reported impact census:
261 formula-row uses, 16 stock-strength-recalculation rows, and 104 unique target
IDs. Those counts must be replayed against the current inventory and code before
use.

The package itself correctly states that the Prada Citronellol 10x arithmetic
proves a lineage hazard, not the sensory-correct dose. Disposition:
**HISTORICAL_PATCH_AND_CANDIDATE_RECEIPTS_ONLY**. Do not copy its patches or
modules wholesale.

## Inventory V5 authority split and exact snapshot

The controlling workbook is
`incoming_review/Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx`:

- size: 199,635 bytes;
- SHA-256:
  `e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`;
- `Ingredient Master` is portfolio/requirement scope, not physical ownership;
- `Current Inventory Master` is the physical-stock authority;
- `INVENTORY READ ME` explicitly prohibits inferring a prepared dilution from
  an owned neat stock.

The stock-hardening package contains a lossless JSON projection of `Current
Inventory Master!A5:N285`. Direct workbook comparison found 280/280 row objects
and every header/cell equal, with zero mismatches. The admitted projection is
`data/governance/inventory_v5_current_stock_snapshot.json`, 226,125 bytes,
SHA-256
`f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99`.

The direct semantic checks establish:

- Alpha Irone 10% is a GAP; the owned stock is 30% w/w in IPM;
- Beta Ionone neat and a separate 0.1% working dilution exist; the old 1% row is
  a preparation requirement, not an owned 1% stock;
- Carrot Seed EO 1%/10%, Heliotropal 10%, Citronellol 10%, and Dihydro Beta
  Ionone 10% require fresh documented preparation from owned neat stock;
- Javanol neat is not confirmed; the executable stock is 20% in DPG;
- Neroli EO is owned as 10% in DPG only.

The repository now materializes physical stocks and requirement states
separately. The legacy text parser remains available to non-execution consumers;
it is not silently presented as the V5 physical authority.

## Deduplicated Execution RC2 handoff

The two loose `PERFUME_CHEM_EXECUTION_RC2_20260808*.zip` files are exact
duplicates:

- each is 245,334 bytes;
- each has SHA-256
  `664df6d9142cc9e3eca17bef2665b64e4f5c9e3d6919412ed3d3b6aa951931cf`;
- reviewed historical base:
  `a7bacff3539bf5e60c94d1fbe48df3d0f1f90da3`;
- local selector tests: 12/12; bounded backend tests: 20/20;
- Ruff: not run;
- repository-native CI, writable publication, host qualification, and fresh
  independent review remained open;
- deployment and all formula/inventory/physical/release mutation authority:
  false.

The packaged `repo_delta` and `apply_xhigh_rc2.py` must not be applied to the
current dirty tree. Its own future-input receipt warns that multiplying stock
volume by a fraction is insufficient for mass-fraction w/w stock without
density and basis conversion. Accord final-module, Chat 8, and Program-v3
package hashes are File-Library receipts only; exact bytes were not vendored.

Disposition: **ONE_DEDUPLICATED_HISTORICAL_PATCH_RECEIPT**. Preserve adversarial
test and trust-boundary ideas, not old-head code.

## 156-target “truth-resolved” package boundary

`incoming_review/PERFUME_156_TRUTH_RESOLVED_WORKING_PACKAGE_v3_1.zip` is 465,274
bytes, SHA-256
`aa590491333ff0bdf82720188eae195df3e6f94f9b89ba674d3e3944a74c75d1`, and has
11 members. It has no package manifest, member-hash ledger, generator,
environment receipt, or source-byte binding.

Independent in-memory recomputation found:

- 9,732 ancestry rows, 156 targets, and 154 formula-bearing targets;
- all 154 formula-bearing raw totals equal exactly 1,000;
- five explicit active-equivalent repairs, all arithmetically consistent;
- 330 `PRODUCT_BASIS_RAW_ACTIVE_UNKNOWN`, six `QUANTITY_BASIS_HOLD`, and no
  presentation-authorized target;
- all 9,732 threshold rows await G15 resolution;
- all 9,732 strict OAV rows are `NOT CALCULABLE • NO COMPATIBLE MEASURED AIR`;
- measured-air values and strict empirical OAV values: zero.

Its five repairs distinguish freshly prepared 10% Citronellol/Dihydro Beta
Ionone from the already-owned Neroli 10% stock. That distinction agrees with V5
and must survive future preparation receipts. Disposition:
**LOCAL_SECONDARY_QUANTITY_RECONSTRUCTION_INTERNALLY_CONSISTENT_PROVENANCE_UNBOUND_NONEXECUTABLE**.

## Corrective screening handoff boundary

`incoming_review/Perfume_Program_Corrective_Reconciliation_Handoff_v6.zip` is
7,838,452 bytes, SHA-256
`7358186577e77044cc43d12788d6465ce5286eebe611114c9135ea61887b62f8`, and has 27
members. Its JSON checksum ledger covers the other 26 members; all 26 size/hash
pairs recomputed exactly, with no missing, drifted, or unlisted member.

The five included pilot packages prove 215 screen designs and 2,580 coded
evaluation rows, but zero physical results and zero final screen-derived
formulas. Pilot 06, the six-pilot master, and the physical-chemistry dossier are
explicitly absent. The package embeds Inventory V3, not controlling V5; every
“inventory available” hard check must be replayed through the V5 materializer.
Disposition:
**LOCAL_HASH_VERIFIED_SCREEN_DESIGN_ANCESTRY_215_DESIGNS_NO_PHYSICAL_RESULTS_V3_INVENTORY_SUPERSEDED**.

## Woody/amber/musk V2 design package boundary

`incoming_review/Woody_Amber_Musk_Extreme_Research_Bundle_V2.zip` is 450,094
bytes, SHA-256
`8e2c29d615081cbaea116fd08a2bea8cfb637f017139c1d39897bdf9d6e8d6ba`, and has
eight members. The V2 manifest binds five unique V1/V2 atlas, screen, and report
artifacts; all five hashes recomputed successfully.

The V2 literature atlas has 22 sheets and 72 source records spanning peer-
reviewed original/review/method evidence, supplier primary/comparator records,
patents, and one preprint. Every row states a limitation and URL; one lacks a
DOI/identifier. Source coverage does not convert the proposed interactions into
observed mixture effects.

The V2 screening workbook deliberately retains stale V1 sheets before its V2
sheets. `START HERE` still describes the V1 three-ratio/Inventory V3 program,
whereas `V2 START`, `Binary DOE V2`, and `Ternary Simplex V2` define 400 binary
and 280 ternary recipes. Direct inspection found result cells blank and statuses
`PENDING CALIBRATION`; strict OAV is not calculable and skin/release are not
authorized. Any importer must select the explicit V2 sheets, preserve V1 as
ancestry, and replay V3 stock assertions through V5. Disposition:
**LOCAL_HASH_BOUND_MIXED_V1_V2_RESEARCH_DESIGN_PHYSICAL_DATA_EMPTY_INVENTORY_V3_SUPERSEDED**.

## Batch-05 source-formula and accord-hierarchy handoff

The late Batch-05/V5 handoff was retained as read-only design/source evidence.
Its three controlling local identities were recomputed and match the handoff:

- workbook:
  `incoming_review/Fragrance_80_Completion_Batch_05_Mixed_Designer_Niche_Sol_Pass.xlsx`,
  127,439 bytes, SHA-256
  `d272ca3615acb6194c8f2c9a082333615f5f87992b99d5237e53a956de8278c3`;
- recovery receipt:
  `incoming_review/COMPLEX_PERFUMERY_BATCH05_SOURCE_BYTE_RECOVERY_RECEIPT_20260809.json`,
  2,557 bytes, SHA-256
  `fe558214012cb0f8064d592c99c13093333bf3575f80a83695e220073adaced5`;
- controlling V5 stock snapshot:
  `data/governance/inventory_v5_current_stock_snapshot.json`, 226,125 bytes,
  SHA-256
  `f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99`.

The workbook preserves 48 Black Opium parent rows and 41 Millesime Imperial
parent rows. Forty-two exact material rows plus two exact DPG carrier rows are
individually executable against V5, but neither whole formula is executable.
Remaining rows include identity-crosswalk, carrier/fraction, preparation,
inventory-gap, product-basis, ambiguous-stock, unresolved-material, and accord
expansion holds. Ten parent labels must not be fuzzily mapped; `Orris Liquid
30%`, for example, cannot override V5's proprietary/as-supplied product basis.

Six named parent accords are exact source-defined 100-part subformulas rather
than proprietary commercial black boxes: Coffee-Liqueur, Orange Blossom
Functional, Pear-Cassis Lift, Iris Pallida Functional, Marine-Salt, and
Patchouli Heart. Their 47 component rows must remain linked to immutable accord
nodes with source coordinates. No accord is currently fully V5-executable, and
flattening them before identity, stock, and mass/volume conversion are resolved
would lose both hierarchy and provenance.

Disposition:
**DATA_AMBER_SOURCE_FORMULA_AND_ACCORD_HIERARCHY_RECOVERED_V5_EXECUTION_REQUALIFICATION_RED**.
The package is a future source-receipt and requalification candidate only. No
formula, stock, OAV, headspace, sensory, safety, procurement, compounding, or
release authority changed in this work.

## Violet Leaf mass-market source-portfolio handoff

The late Violet Leaf portfolio was retained as external read-only evidence and
was not copied into the repository. Its exact transport identity was verified
directly at
`C:\Users\ASUS\Downloads\Violet_Leaf_Mass_Market_Portfolio_Aug2026.zip`:
257,361 bytes, SHA-256
`01705218a21436811484d1079dc9bb4e75bb5c1ae2c252097f136030af911678`.
The ZIP contains one manifest plus eight declared payload members; all 8/8
member byte counts and SHA-256 values recomputed from ZIP streams exactly.
Package rights remain `UNKNOWN` until separately established.

The package preserves four 30 mL, 20% EdP source designs. Their own firewall
records the following Violet Leaf doses and explicitly labels the OAV values as
legacy transferred proxies rather than measured headspace or strict OAV:

| Source design | Odor rows | Violet Leaf 10% raw | Active equivalent | Finished-volume basis | Source gate |
|---|---:|---:|---:|---:|---|
| `VPH-01` Violet Pear Halo | 69 | 120 uL | 12 uL | 400 ppm | `CONDITIONAL PILOT` |
| `RMV-02` Rainmetal Violet | 65 | 150 uL | 15 uL | 500 ppm | `CONDITIONAL PILOT` |
| `VSS-03` Violet Suede Skin | 65 | 90 uL | 9 uL | 300 ppm | `CONDITIONAL PILOT` |
| `VNT-04` Violet Noir Tonka | 72 | 180 uL | 18 uL | 600 ppm | `CONDITIONAL PILOT` |

Each source formula totals 6,000 uL raw concentrate and 1,000 normalized
active-equivalent or named-product-basis parts. Those arithmetic facts do not
make the formulas executable. In particular, the source Markdown calls the
Violet Leaf 10% row `OWNED`, while controlling V5 row 247 says only `10% working
stock` and does not identify carrier, supplier, lot, acquisition, or preparation
receipt. Catalog availability cannot identify the user's bottle. The handoff's
deterministic V5 child census also retains unresolved carrier/basis metadata,
opaque named products, two Heliotropal preparation requirements, and no physical
results. All four designs are therefore tightened to `HOLD_SOURCE_DESIGN_ONLY`.

The correct future admission shape is one immutable external-package receipt,
four formula hierarchies with source cell/row locators, the OAV proxy screen,
dose ladders and corruption controls as experimental-design records, and a
separate V5 requalification child. Violet Leaf activation requires an exact
owned SKU or preparation receipt, fraction and basis, carrier, supplier and lot,
CoA/SDS, and the relevant constituent-contribution information. A literature
profile remains `LITERATURE_PARTIAL_PROFILE`; no single supplier CoA may be
promoted to a universal composition.

Disposition:
**DATA_AMBER_SOURCE_FORMULA_PORTFOLIO_AND_DOSE_LADDERS_RECOVERED_VIOLET_LEAF_STOCK_BASIS_OAV_PROXY_AND_PHYSICAL_VALIDATION_RED**.
No formula, strict-OAV, physical-pilot, safety, compounding, or release authority
changed.

## Complex Tobacco and Amber School handoff

The teaching portfolio at
`C:\Users\ASUS\Downloads\Complex_Tobacco_and_Amber_School_Aug2026.zip`
was retained as external read-only evidence and was not copied into the
repository. Its exact identity is 907,940 bytes, SHA-256
`ece9bb598e9b640a9ea8bac0e08058220bc8ceaed55ddb6688d55c23ad45a47f`.
The ZIP contains one manifest plus 20 declared payload members; all 20/20 byte
counts and SHA-256 values recomputed exactly. Rights remain `UNKNOWN`. The
manifest-declared inventory digest
`e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331`
also independently matches the 199,635-byte local V5 workbook under its
checksum-equivalent filename.

The source package contains five tobacco and six amber 30 mL teaching designs,
each with a 6,000 uL concentrate master. Its summary proves 828 odor-material
rows; with one DPG carrier row per formula, the portfolio has 839 source uses.
The package itself says physical liking, stability, safety, measured headspace,
strict OAV, and release are not tested. Its `CONDITIONAL PILOT` labels and
natural-mixture OAV proxies therefore cannot be imported as authority.

The support packet's deterministic current-V5 child census classifies the 839
uses as 571 `EXACT_READY`, 211 `EXACT_METADATA_INCOMPLETE`, 33
`PRODUCT_BASIS_OPAQUE`, 13 `PREPARATION_REQUIRED`, and 11
`CARRIER_REF_NOT_EXACT`, with no invalid references or true fraction mismatch.
Recurring opaque products include Nympheal, Jessemal, and Castoreum Synthetic;
DPG prose is not an exact stock object. Every design remains
`HOLD_SOURCE_DESIGN_AND_TEACHING_ONLY` until exact stock/basis, natural-lot,
safety, and physical-protocol gates close. Peru Balsam additionally fails
closed until its exact crude/extract/distillate form and carrier are identified.

One locally reproducible lineage collision requires an explicit RED delta:

- source-package `TBC-02`: 28,444 bytes, SHA-256
  `c8feda1143e9115ee52fe09e54184bdbe038ba2915ecc6ab425a4794a96f41e3`;
- untracked repository adaptation
  `formulas/TBC02_Velvet_Vanilla_Tobacco_30mL_20pct_EdP.md`: 7,280 bytes,
  SHA-256
  `7b06574114440c4e2f7e85c1512ecf9b139e60b7d00b2582dc37b46ae6761b14`.

Direct comparison confirms that the adaptation omits source rows for
Immortelle Absolute 10% (18 uL), Polysantol (120 uL), and Cashmeran 20% (220
uL), while DPG rises from 849 to 1,207 uL, exactly compensating the 358 uL.
Its change note incorrectly describes Ambrettolide as removed even though the
source says it was planned but never physically present, and it does not
disclose the Cashmeran omission. Current V5 lists Immortelle, Polysantol, and
Cashmeran 20% as `HAVE`. Neither source nor adaptation was overwritten or chosen
as correct. Preserve
`SOURCE_PORTFOLIO_FORMULA -> DOWNSTREAM_INVENTORY_ADAPTATION` with both hashes,
the explicit omission delta, and
`DATA_RED_ADAPTATION_CHANGE_LOG_MISSTATES_AMBRETTOLIDE_AND_OMITS_CASHMERAN`.

Disposition:
**DATA_AMBER_TOBACCO_AMBER_TEACHING_PORTFOLIO_RECOVERED_PARTIAL_TBC02_COLLISION_V5_STOCK_METADATA_AND_SAFETY_VALIDATION_RED**.
Future admission is package receipt plus separate course, formula, stock-hold,
resin-study, source-ledger, and V5-requalification artifacts. No formula,
natural-profile, proxy-OAV, safety, bench, compounding, or release authority
changed.

## Implemented B1 rights and relation-scope persistence boundary

The prior B1 candidate and database boundary flattened the manifest's structured
rights object to one free-text restriction and dropped relation
`support_scope`, `supported_claim_path`, and `rationale`. That was classified
`DATA_RED_STRUCTURED_SOURCE_RIGHTS_NOT_MATERIALIZED_AT_B1_PERSISTENCE_BOUNDARY`:
an actionable metadata/persistence defect, not a legal conclusion.

The native boundary now preserves:

1. all six normalized rights fields in every B1 source candidate and its
   candidate hash;
2. immutable non-null `rights_json` in `LabSourceDocumentVersion`, its v2 record
   hash, observation-derivation reconstruction, and read-only science reports;
3. the legacy free-text field as a compatibility projection that must agree
   exactly with structured rights;
4. `support_scope`, `supported_claim_path`, and `rationale` as a normalized,
   hash-bound `relation_scopes_json` array on every new derivation link;
5. a deterministic candidate-to-registration adapter that verifies candidate
   hashes and preserves the external staged source ID and candidate digest;
6. `PRIMARY_RESEARCH_DATASET` as a distinct source type rather than mislabeling
   primary study data as article text.

Rows predating a verified manifest are migrated to explicit `UNKNOWN`,
`redistribution_allowed=false`, with a rebind-required note. Legacy derivation
links receive an empty scope array and are treated as incomplete. No permission
is inferred from free text. A populated-database migration regression verifies
backfill, source-type expansion, append-only triggers, foreign-key integrity,
downgrade, and re-upgrade.

The current governed census is five manifests: three `PERMITTED` and two
`RESTRICTED`; all five carry a redistribution boolean, license URL, and caution
notes, and three carry SPDX identifiers. CC-BY article XML remains distinct
from CC0 study data. Both PubChem records remain `RESTRICTED` and
nonredistributable in candidate, database, hash, and report tests.

This closes the lossless schema prerequisite but does not admit Chat B/D/F/G
packages. Package-level independence groups, separate underlying source records,
rights review, exact claim-scoped relations, and non-authority defaults remain
mandatory before promotion.

[PROV-O](https://www.w3.org/TR/prov-o/),
[RO-Crate](https://www.researchobject.org/ro-crate/quick-reference),
[Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/),
and [SPDX 3.0.1 license expressions](https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/)
are useful interchange profiles. They should map into the native authority
system, not become a second truth database.

## Implemented B1 operation-scoped source-use boundary

The prior six-field rights cutover preserved source declarations losslessly but
could not evaluate an exact proposed operation. A paid API plan, article
license, repository software license, metadata grant, dataset license, and UGC
terms could still be mistaken for one blanket integration decision. The native
additive slice now provides:

1. append-only `LabSourceUseConstraintVersion` records linked by exact subject
   and terms source-version foreign keys;
2. exact artifact scope/locator, channel, intended action, and purpose identity;
3. structured plan, jurisdiction, valid-date, volume, byte, retention,
   freshness, attribution, share-alike, noncommercial, sublicensing,
   competing-service, deletion/tombstone, rate-limit, and unmodeled-obligation
   fields;
4. reviewed source-declared decisions
   (`DECLARED_ALLOWED`, `DECLARED_PROHIBITED`, `UNRESOLVED`, or `CONFLICT`), a
   legal-review flag, and immutable version/record hashes;
5. deterministic latest-version assessment that returns `HOLD` for every
   missing, mismatched, conflicting, unreviewed, legally held, unmodeled, or
   unsatisfied dimension; and
6. a read-only B9 projection that exposes exact facts/provenance while labeling
   authority `SOURCE_DECLARATION_ONLY_NOT_LEGAL_CONCLUSION`.

Migration `20260810_0015` creates the table, exact checks/foreign keys/indexes,
and SQLite append-only update/delete guards. Revision scope cannot silently
change: a new subject, artifact locator, channel, action, or purpose requires a
new assertion identity. Source bytes, API credentials, external-study rows, and
operation-assessment results are not stored by this slice. There is no blanket
`integration_allowed` flag and no package, training, formula, publication,
commercial, or release authority.

The information-model direction follows
[W3C ODRL 2.2](https://www.w3.org/TR/odrl-model/) for distinct assets, actions,
permissions, prohibitions, duties, constraints, and conflict posture.
[SPDX licensing](https://spdx.github.io/spdx-spec/v3.0.1/model/Licensing/Licensing/)
remains license-expression metadata, and
[PROV-O](https://www.w3.org/TR/prov-o/) remains provenance vocabulary; neither
becomes a second decision database.

## Workspace-import invariant replay delta

The linked workspace-import audit is stale in one important respect:
`LabExportService.import_workspace()` now invokes
`validate_workspace_invariants()` before an importer-owned transaction commits.
That replay covers formula stock lineage, the exact current-V5 build-plan
snapshot, build-line fraction/basis/active arithmetic, target active quantity,
reservation/line/stock caps, cumulative line consumption, and bound-bottle
freeform-addition restrictions. The focused planning/export regression remains
green.

It is not yet a complete candidate-graph admission boundary. Four read-only
probes against the current code still accepted or leaked states that must fail:

- a stock with `active_fraction=9.0` and unknown basis `dash` was accepted;
- a synthetic imported `CLOSED` plan with no reservations or commits was
  accepted;
- an `APPROVED` plan retained stale mapping v1 after mapping v2 existed; and
- an invariant failure inside a caller-owned ambient transaction left inserted
  rows pending, which the caller could subsequently commit.

The remaining P0 is therefore
`DATA_AMBER_CURRENT_LOCAL_WORKSPACE_IMPORT_REPLAY_PRESENT_BUT_STOCK_DOMAIN_CURRENT_VERSION_EXECUTION_STATE_AND_AMBIENT_TRANSACTION_ATOMICITY_INCOMPLETE`.
The smallest native fix is isolated staging or an importer-owned SAVEPOINT;
closed validation for every stock row; latest target/acceptance/mapping replay;
event-derived reservation/execution/closure state; complete
proposal-confirmation-measurement-movement-commit quantity conservation; exact
batch/bottle binding; and zero-row rollback assertions for every rejected graph.
Imported denormalized lifecycle labels must never create execution authority.
No workspace-import edit is included in the current OAV transaction.

## Literature-to-implementation decisions

| Question | Best supported boundary | Repository decision |
|---|---|---|
| Can omitted stock concentration be assumed neat? | A measurement result depends on an explicit model and the quality/context of its input quantities; hidden input defaults are not acceptable decision evidence. [BIPM JCGM GUM-6](https://www.bipm.org/documents/20126/2071204/JCGM_GUM_6_2020.pdf) | Consume the upstream stock receipt fraction; reject contradictions; undeclared concentration cannot carry quantitative authority. |
| Does matching material name and raw quantity prove that a gate and OAV request describe the same dose? | Raw delivered quantity does not identify active quantity without the exact stock fraction/basis, and candidate-air concentration additionally depends on matrix, application, temperature, time, and analytical context. [PMID 28231131](https://pubmed.ncbi.nlm.nih.gov/28231131/), [Vuilleumier et al.](https://doi.org/10.1111/j.1467-2494.1995.tb00110.x) | Require exact formula-dose receipt SHA equality across gate, state, physics, OAV, scaling, robustness, scoring, and reports. Missing or incompatible gas/threshold evidence returns answerless `ABSTAINED`; no standalone raw request can issue primary status. |
| Can rights be represented by one license string? | SPDX license expressions preserve operators and exceptions, while the SPDX licensing model distinguishes declared from concluded licensing; CC BY also carries attribution, license-link, and change-indication obligations. [SPDX expressions](https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/), [SPDX licensing](https://spdx.github.io/spdx-spec/v3.0.1/model/Licensing/Licensing/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Preserve the source-declared structured rights object and exact scope. Do not convert metadata into a legal conclusion or let an article license leak to data/database artifacts. |
| Does permission for one channel or action authorize every use? | ODRL models assets, actions, permissions, prohibitions, duties, and constraints separately, and defines explicit conflict strategies rather than a blanket allow flag. [W3C ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/), [ODRL Vocabulary 2.2](https://www.w3.org/TR/odrl-vocab/) | Match the exact source version, artifact locator, channel, action, purpose, and obligations. Missing or conflicting dimensions stay HOLD; a source-declared allow is not a legal conclusion. |
| Can a threshold measured in one solvent be reused in another matrix? | Comparative psychophysical evidence shows strong carrier/matrix dependence, including large threshold shifts between water and ethanol contexts. [PMID 31284982](https://pubmed.ncbi.nlm.nih.gov/31284982/), [PMID 40005243](https://pubmed.ncbi.nlm.nih.gov/40005243/) | Require matrix, solvent, concentration basis, method, temperature, panel, and source match; otherwise withhold strict OAV. |
| Can one composition profile represent every natural lot? | Primary studies document material composition changing with provenance, chemotype, harvest, or processing context. [PMID 26669121](https://pubmed.ncbi.nlm.nih.gov/26669121/), [PMID 38542978](https://pubmed.ncbi.nlm.nih.gov/38542978/), [PMID 37746842](https://pubmed.ncbi.nlm.nih.gov/37746842/) | Preserve lot and analytical context. A literature decomposition is a bounded candidate model, not permanent measured composition for every owned natural. |
| Can fruit sensomics validate an owned perfume material or a one-material fruit accord? | Recombination/omission studies are bound to cultivar, ripeness, processing, extraction, matrix, and tested component set. Melon, blackcurrant, cherry, and peach studies show multiple important axes and both significant and redundant components. [PMID 40491709](https://pubmed.ncbi.nlm.nih.gov/40491709/), [PMID 28992408](https://pubmed.ncbi.nlm.nih.gov/28992408/), [PMID 34298395](https://pubmed.ncbi.nlm.nih.gov/34298395/) | Keep fruit, extract/absolute, opaque base, accord, and molecule identities separate. Admit source-native observations only after rights review; use project materials in preregistered comparison designs, never as automatic fruit-equivalence or formula authority. |
| Can one Violet Leaf Absolute profile identify the user's bottle? | GC-MS/GC-O work found origin-associated volatile and odor-active markers in French and Egyptian *Viola odorata* absolutes, while nontargeted metabolomics distinguished geographic fingerprints and statistically validated adulteration cases. [PMID 24934671](https://pubmed.ncbi.nlm.nih.gov/24934671/), [PMID 27135901](https://pubmed.ncbi.nlm.nih.gov/27135901/) | Bind the literature to a partial, source-scoped Violet profile. Require the actual bottle's supplier, lot, CoA/SDS, and preferably lot-specific analysis before a batch override; never substitute a convenient supplier CoA. |
| Can a transferred OAV proxy establish a Violet Leaf contribution in the finished perfume? | Detection thresholds change with matrix, and a background-odor experiment showed both masking and enhancement of key odorants in a complex aroma buffer. [PMID 28231131](https://pubmed.ncbi.nlm.nih.gov/28231131/), [PMID 35460965](https://pubmed.ncbi.nlm.nih.gov/35460965/) | Preserve the package values as `DERIVED_NATURAL_PROXY` only. Upgrade requires lot-specific analytical/headspace evidence plus matched-matrix threshold and coded sensory work. |
| Does an IFRA listing identify or fully qualify an owned natural stock? | IFRA notes that natural complex substances can have materially different compositions and that relevant constituent information may need to pass between supplier and user; final compliance responsibility remains with the finished-product manufacturer. [IFRA NCS nomenclature](https://ifrafragrance.org/transparency-list/about-the-ifra-transparency-list/nomenclature-for-natural-complex-substances-on-the-ifra-transparency-list), [Understanding the Standards](https://ifrafragrance.org/understanding-standards) | Treat IFRA data as safety evidence, not bottle identity. Require an exact stock/preparation receipt and supplier documentation; do not infer the carrier or lot from a catalog alias. |
| Can tobacco or resin literature define the composition of the user's extract? | Studies differentiate volatile profiles across tobacco varieties/cigars and botanical olibanum samples, demonstrating source and processing variability rather than a universal extract profile. [PMID 40454082](https://pubmed.ncbi.nlm.nih.gov/40454082/), [PMID 39153428](https://pubmed.ncbi.nlm.nih.gov/39153428/), [PMID 15922374](https://pubmed.ncbi.nlm.nih.gov/15922374/) | Bind papers by role as composition/context evidence only. Supplier, lot, extraction form, carrier, CoA/SDS, and batch-specific analysis remain required before an empirical natural-profile override. |
| Can the Tobacco/Amber package's `CONDITIONAL PILOT` label clear safety? | The 51st Amendment was formally notified in 2023. The 52nd consultation closed on 12 June 2026, but formal notification is expected only toward the end of November 2026. The current Peru Balsam standard prohibits crude material and separately restricts extracts/distillates. [51st notification](https://ifrafragrance.org/latest-updates/press-releases/notification-of-the-51st-amendment-to-the-ifra-standards), [52nd consultation status](https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed), [Peru Balsam standard](https://ifrafragrance.org/standards/IFRA_STD_071.pdf) | Use the notified baseline for current checks and retain the 52nd as watchlist/draft context. Identify the exact Peru Balsam form and stock receipt before any safety calculation; package prose never grants release authority. |
| Can one generic partition model predict finished perfume headspace? | In mineral-oil fragrance systems, experimentally fitted Henry constants outperformed UNIFAC at low concentration. That result is matrix-specific and does not validate transfer to ethanol, air, blotter, or skin. [Costa et al. 2017](https://doi.org/10.1021/acs.iecr.7b01802) | Prefer measured matrix-specific headspace/Henry evidence, disclose model domain, and abstain outside it. Do not claim UNIFAC implementation by name. |
| Do high OAV values identify odor character or contribution? | OAV is a useful above-threshold screen but can mis-rank importance and does not encode mixture suppression, interaction, or perceptual quality. [Grosch 2001](https://doi.org/10.1021/bk-2001-0782.ch014) | Keep strict OAV calculation for screening; exclude family sums/cliffs and heuristic synergy from release authority and rank. |
| Can generic synergy multipliers be assigned to pairs? | Vapor-calibrated perithreshold synergy was shown for a narrow maple-lactone/acid context, not as a universal pair law. [Miyazawa et al. 2008](https://doi.org/10.1093/chemse/bjn004) | Store bounded interaction observations with material, concentration, matrix, task, panel, and source context. No universal multiplier. |
| Can receptor data determine perfume quality or liking? | Receptor mixtures can show competitive, suppressive, and antagonistic nonlinear responses. Receptor response is not perceptual identity, beauty, or liking. [Singh et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6511041/), [Xu et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC5915184/), [Oka et al. 2004](https://pmc.ncbi.nlm.nih.gov/articles/PMC1271670/) | Keep assay and receptor records source-scoped; compare candidate models on held-out data; never promote receptor-to-aesthetic rules. |
| Is skin evaporation a universal material property? | A 2025 study with ten volunteers associated hydration, roughness, and transepidermal water loss with fragrance evaporation and explicitly requires broader validation. [Hadjiefstathiou et al. 2025](https://doi.org/10.1111/ics.13085) | Preserve substrate, subject/panel, environment, application, and time context; do not transfer a small skin study into a universal release constant. |

## Correct ChatGPT/Codex/Git workflow

A tunnel is transport, not synchronization or scientific provenance. Git is
versioned local evidence history, not a live chat bus. The reliable workflow is
an append-only bridge:

```mermaid
flowchart LR
    A["ChatGPT project chats"] --> B["Bounded export or evidence packet"]
    B --> C["Local hash and rights manifest"]
    C --> D["Lossless staging and scoped relations"]
    D --> E["Sol local review and tests"]
    E --> F["Canonical acceptance or explicit HOLD"]
    F --> G["Derived project reports and Git history"]
    G --> H["Verified status packet to work chat"]
```

ChatGPT projects can share uploaded files, project instructions, and connected
sources, while each chat retains its own transcript. A ChatGPT project does not
directly mount a local repository. Local Codex projects attach local folders;
remote MCP/plugin connections can expose bounded tools, but the ChatGPT web app
does not read the desktop Codex MCP configuration automatically. See the
official [Projects](https://learn.chatgpt.com/docs/projects),
[MCP](https://learn.chatgpt.com/docs/extend/mcp), and
[Plugins](https://learn.chatgpt.com/docs/plugins) documentation.

Recommended responsibilities:

| Surface | Responsibility | Must not do |
|---|---|---|
| ChatGPT project | Research discussion, human decisions, attached source discovery | Pretend all chat transcripts form one canonical database |
| DeepLuna Chat | Bounded, non-sensitive mechanical research/inspection when exact-project admission is READY | Make architecture/science decisions or bypass failed readiness/budget gates |
| Perfume Chem Tunnel / remote MCP | Expose explicit, authenticated, narrow tools and health checks | Be treated as transcript synchronization or proof of remote attachment from local health alone |
| Local Codex workspace | Exact bytes, code, tests, manifests, scientific gates, final acceptance | Import chat claims directly into authority tables |
| Git | Reviewable version and provenance history after local acceptance | Store credentials, restricted raw data, or substitute commits for scientific validation |

## Executed highest-value local increment

### A. Exact stock/dose receipt cutover

`engine/pipeline/preflight.py` now emits one immutable
`FormulaDoseReceipt`. Its digest binds the exact Inventory V5 snapshot and
workbook/sheet authority, physical stock ID, source rows, stock authority,
concentration fraction/basis/carrier, delivered raw quantity,
active-equivalent quantity, formula-input identity, and legacy formula-shape
hash for every line. A formula receipt is `BOUND` only when its stock contract
passes and every line is individually bound; a held formula cannot hide a
missing or ambiguous stock behind resolved neighboring lines.

`GateReport` and `FormulaState` retain the receipt SHA/status. Simulation,
scaling, robustness, OAV, release scoring, optimizer, audit, CLI, and report
surfaces consume the same receipt-bound state rather than independently
re-deriving ingredients and dilutions. Exact receipt replay is deterministic;
changing the inventory snapshot, stock ID, fraction, basis, carrier, raw dose,
active dose, source row, authority, or formula input changes identity and fails
reuse. This closes the live Prada Citronellol-style 10%-to-neat bypass.

When neither a declared V5 stock receipt nor explicit valid concentration
exists, the compatibility representation remains non-authoritative:
`stock_declared=false`, receipt status is not `BOUND`, and quantitative/release
authority is unavailable. A standalone exploratory path may still render
compatibility output, but it is labeled unbound and cannot feed release
scoring or automatic optimizer reruns.

### B. V5 physical-stock authority cutover

`engine/inventory_parser.py` now validates the exact snapshot and controlling
workbook hashes, materializes stable physical stock IDs, preserves multiple
stocks, and keeps `OWNED`, `PREPARATION_REQUIRED`, `GAP`, and `UNRESOLVED`
states distinct. Conservative parsing produced 216 explicit physical-stock
records; 143 currently have sufficient concentration/carrier semantics for the
execution resolver. Missing carrier, product-basis, identity, lot, or physical-
form detail remains non-executable.

`engine/pipeline/preflight.py` now consumes this V5 projection instead of
`inventory.txt`, binds the exact stock ID into the immutable receipt, reports
preparation/gap states explicitly, and preserves the existing
`formula_row+inventory_snapshot` composite authority marker while retaining the
underlying V5 authority separately. This keeps G15 compatible without hiding
which inventory authority supplied the stock.

`scripts/verify_formula_workflow.py` and `parse_stock_specification()` now leave
blank, dash, and unknown stock text undeclared. Only explicit neat/pure/
undiluted, an explicit percentage, or an explicit numeric fraction can declare
a concentration.

### C. Legacy OAV intelligence quarantine

`engine/pipeline/oav_authority.py` no longer lets family target ranges, cliffs,
top/heart/base OAV sums, shift zones, or generic synergy factors reduce primary
strict status or rank. The outputs remain visible under
`LEGACY_HEURISTIC_ADVISORY_ONLY` with explicit no-release-authority and
excluded-from-status/rank markers. Primary OAV status is always `WITHHELD` and
authority rank is zero unless a future separately governed authority contract
is introduced; a legacy modeled screen cannot supply one.

Gate reuse now verifies the exact formula-dose receipt rather than raw names
and quantities alone. Strict rows adapt receipt-bound candidate-air and
threshold evidence into `engine.physics.headspace_oav.calculate_headspace_oav`.
Missing or incompatible analyte identity, unit, matrix/context, temperature,
uncertainty, measured-air evidence, or threshold evidence returns a typed,
answerless `ABSTAINED` assessment with reasons and hashes. Unknown
`vapor_ppm` remains `None`; it is never silently zero and no longer raises a
numeric conversion exception.

The two legacy collection scripts now reject blank/dash/unknown dilution rather
than assuming neat. `scripts/reconstruct.py` requires an explicit normalized
stock fraction before a dose can be projected, preserves active/raw ratio in
chassis and module construction, labels design partitions as non-authoritative,
and does not describe missing stock basis as neat. These are compatibility-path
closures, not promotion of reconstructed formulas.

### D. Natural census and profile-schema reconciliation

The live inventory audit now freezes the exact unresolved natural-composite set
at 20 materials and separately classifies the three opaque preblends `Leather
FO`, `Sandalwood Base 3X`, and `Tuberlia Base`. This updates a stale test; it does
not fabricate GC-O constituent evidence or convert any natural into strict OAV
authority.

Fifteen intake profiles stored prose in the numeric `character` vector field.
Their prose is now preserved as `character_description`, while `character`
remains an explicitly empty numeric mapping. No dimension scores were inferred.
A regression requires every live `_PROFILES.character` value to retain the
mapping contract.

### E. B1 structured-rights and scoped-relation cutover

`engine/ingestion/scientific.py` now includes the complete normalized rights
object in each B1 candidate and candidate digest. The backend adds immutable
`rights_json`, hash-bound `relation_scopes_json`, candidate adapters, v2 source
record hashing, reporting, reconstruction, a distinct primary-dataset source
type, and a populated-row migration. Article, study-data, and PubChem rights are
tested as separate records and scopes. This is metadata preservation only; it
does not decide legal permission or promote source authority.

### F. B1 operation-scoped source-use cutover

The backend adds append-only, hash-chained source-use assertions plus exact
assessment and a B9 read-only projection. The request cannot inherit rights
across source versions, article/data/software/UGC artifacts, API channels,
actions, or purposes. Unknown, conflict, unreviewed evidence, unmodeled terms,
required legal review, and unmet obligations all fail closed. The assessment
authority is source declaration only, and no API credential or source payload
is stored.

### G. Exact-decimal planned-lineage persistence cutover

`LabStockSolution.active_fraction_decimal_text` and
`LabFormulaComponent.requested_mass_g_decimal_text` now preserve canonical
finite decimal input, while the existing SQL floats remain API/database
compatibility projections. Planned active-equivalence reads only the exact
text, validates projection agreement, and emits `formula-stock-lineage-v3`.
Missing exact text yields `ACTIVE_EQUIVALENT_DECIMAL_REBIND_REQUIRED`; a
disagreement yields `ACTIVE_EQUIVALENT_DECIMAL_PROJECTION_MISMATCH`.

Migration `20260810_0014` intentionally does not backfill old float rows.
`lab-export-v5` is the current writer and includes the exact fields; v1-v4
remain supported compatibility inputs/outputs but cannot confer exact-decimal
authority. API responses expose both representations so consumers can migrate
without mistaking the float projection for authority. This is a planned
formula-lineage software boundary only, not physical metrology.

### H. Recovery and verification

Before the edit, a path-preserving five-file recovery archive was created and
each extracted member hash was checked:

- `archive/pre_change_stock_receipt_cutover_20260810T024723.zip`;
- SHA-256: `32f888f7145dadbbe67b2c12226554653467e9db0f9fff60b9cde47f7cee996b`;
- 5/5 archived member hashes matched after extraction.

Before the V5 cutover, a second path-preserving six-file recovery archive was
created and restoration-verified:

- `archive/pre_change_20260810T_v5_authority_cutover.zip`;
- SHA-256: `9a499f8118608db3fe456a50da841c39813cefecded0e984bff75a98cefa5b01`;
- 6/6 restored file hashes matched; the verification copy remains under
  `archive/verify_pre_change_20260810T_v5_authority_cutover`.

Before the profile and B1 rights/scope cutover, a third path-preserving archive
was created and restoration-verified:

- `archive/pre_change_20260810T_rights_profiles_cutover.zip`;
- 123,060 bytes;
- SHA-256: `cede85f96c252f892eadc9ae6b3cb952e54e11663a43b3bf6739f9bb947a0762`;
- 12/12 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_20260810T_rights_profiles_cutover`.

Before the active-equivalence authority cutover, a fourth path-preserving
archive was created and restoration-verified:

- `archive/pre_change_active_equivalence_authority_20260810T054901434.zip`;
- 101,231 bytes;
- SHA-256: `d3a7d3ab571b348eb09aa4edf75716dac45f69890bb9d9fc1464e5eb897dae40`;
- 7/7 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_active_equivalence_authority_20260810T054901434`.

Before the exact-decimal persistence cutover, a fifth path-preserving archive
was created and restoration-verified:

- `archive/pre_change_exact_decimal_persistence_20260810T061127557.zip`;
- 80,182 bytes;
- SHA-256: `c4e0216ab73be5baa9657e58ebea9ccca00bf5670c35bfa32a743f1c3ca4b6c1`;
- 13/13 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_exact_decimal_persistence_20260810T061127557`.

Before appending compatibility notes to the two historical A2/A3 verification
documents, a sixth path-preserving archive was created and
restoration-verified:

- `archive/pre_change_decimal_verification_docs_20260810T062549963.zip`;
- 6,210 bytes;
- SHA-256: `e20e165e6d0eadb49251603a3eb423925573f3cb54ec2d1f12dc2b99dcbe3802`;
- 2/2 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_decimal_verification_docs_20260810T062549963`.

Before replacing stale hard-coded migration-head expectations with the
repository-derived single head, a seventh path-preserving archive was created
and restoration-verified:

- `archive/pre_change_decimal_migration_head_tests_20260810T063233030.zip`;
- 5,334 bytes;
- SHA-256: `182aa86780977decea3e5e11099d6ae1153e509fc6eb4b5ebe5e2705aa63942e`;
- 2/2 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_decimal_migration_head_tests_20260810T063233030`.

Before the operation-scoped source-use cutover, an eighth path-preserving
archive was created and restoration-verified:

- `archive/pre_change_b1_operation_scoped_rights_pathsafe_20260810T065635404.zip`;
- 99,315 bytes;
- SHA-256: `b8876df4c99dd98ed8c7d8db257ad0cac0448125677ee85afc0c98d4dd088725`;
- 13/13 restored member hashes matched; the verification copy remains under
  `archive/verify_pre_change_b1_operation_scoped_rights_pathsafe_20260810T065635404`.

Before the Meaningful Complexity authority cutover, a ninth path-preserving
archive was created and restoration-verified:

- `archive/meaningful-complexity-authority-prechange-20260810T084000693.zip`;
- 81,070 bytes;
- SHA-256: `b27386b961a411fb0b5fe4835f782364c27516bdd30428cdc9a6e736946640ea`;
- 6/6 restored member hashes matched. The path-preserving staging and
  verification copies remain under `archive/_stage-meaningful-complexity-20260810T084000693`
  and `archive/_verify-meaningful-complexity-20260810T084000693`.

Before the receipt-bound OAV identity and abstention cutover, a tenth
path-preserving archive was created and restoration-verified:

- `archive/oav-receipt-identity-prechange-20260810T091647725.zip`;
- 187,395 bytes;
- SHA-256: `367b82391173dcee795c3c91a85c06f7f7350fbe7b2f4eafdb0b9a9639fd7293`;
- 19/19 restored member hashes matched. The verification copy remains under
  `C:\Users\ASUS\AppData\Local\Temp\perfume-oav-receipt-restore-20260810T091647725`.

Before closing the named legacy collection/reconstruction neat fallbacks, an
eleventh path-preserving archive was created and restoration-verified:

- `archive/stock-dose-legacy-bypass-prechange-20260810T093919040.zip`;
- 20,178 bytes;
- SHA-256: `e3142b378c1773138b3c986165495b6abfae946b54a188c434b04fea2d1a656c`;
- 3/3 restored member hashes matched. The verification copy remains under
  `C:\Users\ASUS\AppData\Local\Temp\perfume-stock-dose-restore-20260810T093919040`.

Before changing the two golden unknown-candidate-air expectations from numeric
zero to typed unknown, a twelfth path-preserving archive was created and
restoration-verified:

- `archive/golden-unknown-air-prechange-20260810T095443892.zip`;
- 4,117 bytes;
- SHA-256: `f4ba3a17fdea1e3aaef7893daabac24e4c6b38045323bc58f4ab81c967429455`;
- 3/3 restored member hashes matched. The verification copy remains under
  `C:\Users\ASUS\AppData\Local\Temp\perfume-golden-unknown-air-restore-20260810T095443892`.

Before adding the native external-study admission slice, a path-preserving
pre-change archive was created and read-verified:

- `archive/external_study_admission_prechange_20260810_001.zip`;
- SHA-256:
  `acd5dd2cc94e8e9b56f9764fd5da570215155a24d0624639ffee5e1ebef0e321`;
- all four repository-relative members streamed without error.

Before the C3-to-C8 exact-domain binding cutover, a path-preserving pre-change
archive was created and read-verified:

- `archive/c3_c8_domain_binding_prechange_20260810_105138.zip`;
- 47,472 bytes;
- SHA-256: `413da6bf6796f9268df2ac5b2605871db7e1a5dc48df49cb1c4efe13aa866327`;
- all five repository-relative members streamed without error.

Before the PR-3 gate-identity correction, a path-preserving pre-change archive
was created and read-verified:

- `archive/pr3_gate_identity_prechange_20260810_121437.zip`;
- 56,228 bytes;
- SHA-256: `ded95db678dd6b31ce508005a1fa4a780e6af87181d97288f5153af7e328a890`;
- all three repository-relative members matched their source SHA-256 values.

Before adding runtime build-plan current-authority replay, a path-preserving
pre-change archive was created and read-verified:

- `archive/a2_lifecycle_revalidation_prechange_20260810_133100.zip`;
- 95,963 bytes;
- SHA-256: `dd7b81a8df88a83466d67b635ab2662afda8d53ff5ec4fa2e6ea5af50fe9f439`;
- all eight repository-relative members decompressed and matched their source
  SHA-256 values.

An earlier flat-path `Compress-Archive` attempt was invalid because it did not
preserve repository-relative paths. It was renamed with an `.invalid` suffix
and is not counted as a backup or recovery receipt.
An earlier Meaningful Complexity archive attempt produced a zero-byte ignored
object at
`archive/meaningful-complexity-authority-prechange-20260810T083941280.zip`;
it is likewise not counted as a backup or recovery receipt.

Current verification completed:

- Ruff on all touched root/backend code, tests, and migration: passed;
- exact authority, parser, stock receipt, run-evidence, and formula-state suites:
  **67 passed**;
- targeted Prada/V5, confidence-policy, and stale-commercial-trial regressions:
  passed;
- refreshed root scientific-ingestion/profile slice: **52 passed**;
- external-package receipt quarantine slice: **8 passed**;
- wider root stock/formula/OAV/run-evidence/scientific slice: **171 passed**;
- backend B1 schema/service/reporting plus populated migration and full-head
  migration-smoke slice: **42 passed**;
- operation-scoped B1 source-use schema/service/reporting/migration/API slice:
  **45 passed**; the broader B1/migration/backup compatibility slice added
  **23 passed**;
- native external-study schema/service/migration slice: **11 passed**; adjacent
  B1, Laboratory-Beta migration, and backup/restore compatibility: **57
  passed**;
- targeted mypy for the external-study model/repository/service: **no issues in
  3 source files**; focused Ruff passed;
- C3-to-C8 predicted-gas binding: **195 focused tests passed**; the adjacent
  C1-C4/C6-C9 physics and unsupported-science ladder passed **541 tests**.
  Exact matrix, temperature, pressure, relative humidity, and full C2
  application-environment binding mismatches now fail closed; scoped Ruff,
  format, and mypy checks passed.
  The independent C0 stale inventory/fixture checks and frozen C5 runtime
  parent remain explicit holds rather than being counted as C3/C8 failures.
  The separate C5-to-V5 assessment is hash-bound and **3 focused tests passed**,
  but correctly returns `HOLD_REDESIGN_REQUIRED` and creates no v2 program.
  Combined replay with the frozen v1 suite produced **40 passed / 1 expected
  stale-parent failure**: live `inventory.txt` no longer equals the immutable
  2026-08-03 parent hash, which is the hold rather than a reason to rewrite v1;
- PR-3 duplicate-gate identity: **73 focused tests passed**, including hard/advisory
  exception behavior, all dynamic family-applicability checks, and G15 wiring;
  scoped Ruff passed. The wider direct gate-consumer slice passed **235/237**;
  its two failures were independent current preflight/G15/inventory-stock
  fixture expectations and did not involve the duplicate gate;
- runtime A2 current-authority replay: six adversarial approval, reservation,
  execution-transition, proposal, and commit tests first failed on the
  unchanged services and then passed after the shared validator was wired; a
  seventh passing regression covers corrupted reservation-stock identity.
  The critical planning/execution/import slice passed **42 tests**. The wider
  A2 slice passed **61/62**; its sole failure occurs earlier in the API fixture
  because `DERIVED_FROM` is outside the current formula-transition vocabulary,
  not in the build-plan replay path. Scoped Ruff excluding the archive-proven
  pre-existing import-order finding, compileall, and `git diff --check` passed.
  Full scoped format and mypy remain held by pre-existing dirty-file findings
  reproduced from the archive rather than attributed to this cutover;
- sequential backend B5 analytical, B6 regulatory, and B7 claim-authority
  schema/service slices: **135 passed** (84 + 23 + 28);
- targeted mypy for `lab_sources` model/service and science reporting:
  **no issues in 3 source files**.
- Meaningful Complexity authority-contract slice: **7 passed**; Ruff and
  compileall passed for the touched native module and regression test;
- wider construction-complexity, workbench, and golden-formula direct
  consumers: **34 passed**;
- receipt-bound stock/dose, OAV, strict-abstention, CLI, simulator, optimizer,
  and legacy-consumer focused slice: **135 passed**;
- optimizer, scenario-matrix, and thermodynamic-unification consumers after the
  unbound-rerun fence: **51 passed**;
- golden formula regression after changing Leather FO and missing-physical-data
  candidate-air from `0.0` to `None`: **13 passed**; the canonical JSON fixture
  lock was deliberately updated to
  `9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`;
- final consolidated receipt/preflight/formula-state/OAV/scoring/intervention/
  optimizer/scenario/golden replay: **115 passed**;
- Ruff on the receipt/OAV/CLI/optimizer/test cutover files and
  `git diff --check`: passed. `scripts/reconstruct.py` passes the scoped Ruff
  policy while retaining 13 pre-existing unused-import/plain-f-string findings
  outside this transaction;
- active-equivalence focused slices: **15 root + 4 backend passed**;
- wider direct consumers: **140 root + 38 backend passed**;
- exact-decimal lineage/migration/API/export focused backend slice:
  **14 passed**;
- wider exact-decimal migration, export/import, lifecycle, planning,
  transaction, and backup/restore backend slice: **46 passed**;
- Alembic reports one head, `20260810_0016`; source and migration compileall
  passed;
- targeted mypy for the six operation-scoped source-use model/repository/
  service/reporting files: **no issues**;
- targeted backend mypy for `stock_lineage.py`: **no issues**;
- the broader changed-source mypy command reported no error in a changed file;
  it surfaced one pre-existing unrelated return-type error at
  `stock_strength_quarantine.py:55`;
- canonical quick verifier: **8 PASS / 2 known fail-closed checks**; the three existing
  type errors remain confined to `engine/inventory/stock_model.py` and
  `engine/target/formula.py`, formula artifacts remain explicitly stale and
  quarantined, and the golden digest remains unchanged at
  `9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`.

The fresh 2026-08-10 canonical quick project verifier passed eight checks and
retained two known fail-closed checks; its golden-output digest remained unchanged at
`9cf31e92d3c8e814f3bc2654ffba6f3fbd766de8c705630ae78fb5c24a1dfc61`:

- PASS: engine compile/lint, scientific audit (22 tests), material-data
  validation (80 tests), knowledge-rule validation (77 tests), golden formula
  regression (13 tests), golden API regression, and fixture lock;
- FAIL: engine typecheck has three existing errors in untouched
  `engine/inventory/stock_model.py` and `engine/target/formula.py`;
- FAIL: formula artifacts are stale/quarantined after inventory, scientific
  input, formula-definition, or pipeline-source changes. They were not silently
  rebound because no formula rerun or release was authorized.

The fixture change is intentional and narrow: unknown candidate-air is no
longer represented as a measured/modelled zero. A wider
`test_project_verification.py` run passed 29 tests and exposed one independent
stale shard-census failure because seven newer test files are not yet assigned
to the project-wide shard registry. That registry debt was not altered in this
OAV transaction.

The natural-composite and prose-profile failures are now resolved by explicit
census/schema tests. The C5 program still pins an older `inventory.txt` hash and
must be version-rebased deliberately rather than silently rebound. A full
backend unit sweep exceeded the bounded 244-second verification window without
returning a final result; it is not counted as pass or failure. Full backend
Ruff still reports one existing import-order error in unrelated dirty-tree
`lab_planning.py`. Full backend mypy still reports five existing errors in
unrelated dirty-tree modules
`stock_strength_quarantine.py` and `workspace_invariants.py`; the touched B1
modules pass targeted mypy.

An attempted parallel B5/B6/B7 run was invalid because all three pytest
processes shared the fixed `backend/test_perfume_chem.db` fixture while each
dropped and recreated its schema. The resulting `table already exists` and
`no such table` setup/teardown errors were test-process collisions, not product
failures. The three lanes were rerun sequentially and passed in full as counted
above; no product code was changed to mask the fixture limitation.

DeepLuna Chat was checked on the exact project and was READY with settled
reservations. Repository audit job
`DS-df337cec72708f28a67ff83e29c52b6b` exhausted its repository-tool budget
before reading evidence and failed closed. Contract-only job
`DS-dd2cc55ddd48739aa685af52a075d7d4` returned a mechanical rights/scope test
matrix with no repository claims; Sol independently implemented and ran the
tests. The older V5 job `DS-9c5672b5ed77ed732df7694bc2b63374`
likewise returned no usable repository evidence. The later report-consistency
job `DS-60cb23dc18f3b063b0bf757bbea82a48` also failed closed before its required
read because the repository-tool budget was exhausted. It was not retried and
no alternate route was used. A fresh exact-project check for the metrology slice
was READY with settled reservations, but bounded DIRECT_PRO read job
`DS-47c6171f9cef245e8beaf6831252dcfe` stopped with
`MAXIMUM_PROVIDER_CALLS_EXHAUSTED` before returning evidence. It too was not
retried or rerouted. Sol retained architecture, science, migration, and final
acceptance. Fresh Chat-A and Chat-D source-admission reads were attempted only
after READY checks with settled reservations; jobs
`DS-d3a8c99741974e2e6dfd1e6b76f21c02` and
`DS-c6b253dab135fe8ff5b06421a963a17c` each exhausted the bounded
repository-tool allowance before reading evidence. Neither was retried or
rerouted. Chat-C read job `DS-98bfa773af47f163d92730bde9d616af`
failed in the same way before inspecting any allowed path. A subsequent
Chat-F check was READY with settled reservations, but no further paid job was
sent because the orchestration stop rule forbids an automatic provider loop
after repeated primary failures. Sol reconciled the primary sources and local
contracts directly, with no Fast or alternate-provider fallback. The fresh
Chat-G exact-project check was also READY with zero open or unknown
reservations, but it did not reset that failure stop: no provider job was sent,
and Sol verified the ZIP identities, canonical ADR, B1 source spine,
physical-experiment model, and formula-specific external-candidate schema
locally.

The later Meaningful Complexity exact-project checks were READY with settled
reservations, but bounded DIRECT_PRO read job
`DS-bef444a090999e708aa289a140fe` exhausted its repository-tool allowance
before collecting the required file receipts and returned no usable evidence.
It was not retried or rerouted. Sol performed the live prompt/runtime audit,
literature reconciliation, cutover, and final verification locally.
The subsequent Chat-4 handoff also received a fresh READY exact-project check
with zero open or unknown reservations. The repeated-failure stop remained in
force, so no additional paid job was sent and no alternate route was used.
The receipt-bound OAV transaction received the same fresh exact-project READY
result with settled reservations. The repeated-primary-failure stop still
applied, so no paid transmission, Fast route, Codex subagent, or alternate
provider was used; Sol reproduced both defects, implemented the cutover, and
performed local acceptance.

For the operation-scoped rights slice, the first bounded DIRECT_PRO packet
(`DS-687074c420ca0f09713ed6bf880abca8`) was rejected before execution because
its 60,376-token input exceeded the 18,000-token contract. The reduced
model-only audit (`DS-384e2156167dd1fb42755b8af250fc00`) then exhausted its
repository-read allowance before opening the required file and returned no
governed evidence. Neither result was accepted, retried, or rerouted. Fresh
exact-project checks remained READY with settled reservations; Sol performed
the model, migration, service, report, test, and final review locally, with no
Fast or alternate-provider fallback.

For the C3-to-C8 acceptance audit, the fresh exact-project check was READY with
the correct project identity and settled reservations. Bounded DIRECT_PRO read
job `DS-6b95b3d016bb4cc924cd2c441e65b861` exhausted its repository-tool budget
before reading a file and returned no governed evidence. It was not retried or
rerouted; Sol reproduced the cross-condition seam, implemented the narrow
native fix, and verified it locally.

### I. Meaningful Complexity authority cutover

The active OpenCode orchestrator and governing prompt no longer treat
Meaningful Complexity v2 row-count minima, preferred row ranges, the generic
`0.76` collision cutoff, or a compensatory `92/100` score as authority. The v2
pack remains immutable historical ancestry; no missing PCV3 v3 or Universal
Accord package was reconstructed from transcript counts.

`engine/perception/construction_complexity.py` now exposes an explicit
machine-readable decision contract with `complexity_authority=WITHHELD`,
candidate-only dimensions, and noncompensatory external gates. It authorizes
neither a universal row-count gate, an aggregate score, an automatic rebuild
from row count, nor override of stock, active-dose, strict-OAV,
physical-chemistry, safety, provenance/source-use, or physical-observation
failure. The active prompt and governing document carry the same boundary.

Chat-6 atmosphere/texture counts and proposed negative-space techniques were
added only to the reconciliation layer. No package, family registry, material
alias, formula, inventory row, experimental result, or release decision was
imported. Exact package recovery, identity and V5 child qualification, and
matched-strength blinded observations remain prerequisites for later work.

### J. Atomic workspace-import authority replay

The P0 workspace-import seam is now fail-closed for the reproduced bypasses.
`LabExportService.import_workspace()` places the entire candidate graph inside
an owned `AsyncSession.begin_nested()` SAVEPOINT before the invariant replay.
An invalid import therefore rolls back its candidate rows even when the caller
owns the outer transaction, while preserving unrelated pre-existing outer work.
This follows SQLAlchemy's documented SAVEPOINT boundary for
[`begin_nested()`](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#using-savepoint).

The whole-graph replay now verifies:

- exact-decimal V5 stock fractions, a closed fraction-basis vocabulary,
  physical stock balances, movement arithmetic, and cumulative active
  reservations against the canonical balance;
- current accepted target and latest executable mapping identity, build-line
  stock/fraction/basis/active arithmetic, and executable-state quarantine;
- contiguous reservation history and exact proposal, confirmation,
  measurement, bottle-event, movement, and commit bindings;
- proposal/reservation/line quantity caps and evidence-backed
  `RESERVED`/`EXECUTING`/`CLOSED` states rather than trusted imported labels.

The regression matrix rejects an active fraction of `9.0` with basis `dash`, a
stale target or stock mapping, a synthetic `CLOSED` plan, reservations above
physical stock, a measurement above its confirmed proposal, and ambient-
transaction row leakage. Valid idempotent round-trips remain accepted. Final
focused acceptance is **35 passed**, plus **6 stock-lineage tests passed**;
Ruff, targeted mypy, and `git diff --check` are clean. This closes the observed
import-authority defects only. It does not create formula, inventory-truth,
physical-metrology, safety, sensory, or release authority, and it does not
claim a redesign of all future partial-fulfillment policy.

### K. Runtime build-plan current-authority replay

The import replay closed stale graphs at the workspace boundary, but one live
lifecycle gap remained. Build-plan creation already checked the exact selected
stock fraction/basis and immutable active quantity; later approval,
reservation, execution transition, action proposal, and commit did not all
replay the same current target, mapping, and stock authority. Six no-write
regressions confirmed that a superseded target or mapping and a changed stock
fraction could still cross those later seams; a seventh regression covers a
corrupted reservation whose stock no longer matches its immutable line.

The native cutover adds no table or second arithmetic path. One reusable
existing-plan validator reconstructs the immutable `BuildPlanInput`, then
replays the creation validator. That validator now also requires the latest
target-hypothesis version and latest version of every referenced inventory
mapping. It is invoked before transitions into `APPROVED`, `RESERVED`,
`EXECUTING`, or `CLOSED`, before inventory reservation, and before both physical
action proposal and transaction commit. The execution seam also requires the
reservation stock to equal the immutable build-line stock. Review,
cancellation, and supersession remain available so stale candidates can be
retired without gaining physical authority.

Workspace whole-graph replay remains an independent defense. The new runtime
guard does not infer physical measurement, metrological equivalence, formula
correctness, safety, sensory success, or release authority; it only prevents a
previously valid plan from exercising authority after its target, mapping, or
selected stock contract changes.

### L. Chat-7 mixed-dimension projection boundary

Chat 7's claimed PR-2B package, manifest, schema, and test log remain
unrecovered. Native `FormulaDoseReceipt` is a planned-volume screening receipt,
while Laboratory Beta retains exact planned mass lineage and confirmed,
measured, committed execution events. No native `PreparedFormulaRun` aggregate
or lossless mixed-dimension engine projection is currently admitted.

A current dirty-tree candidate in `backend/app/adapters/lab_legacy.py` now
demonstrates the intended typed lineage envelope and answerless conversion
abstention; its focused adapter file passes **13 tests**. It is not yet an
admitted cutover. Only tests construct its `LabProjectionLineInput` values, and
the public function still accepts caller-supplied identifiers, hashes,
composition/density evidence, and `source_run_state` (including
`CONFIRMED_MEASURED_COMMITTED`) rather than assembling and proving them from the
canonical formula/build/stock/bottle-action/measurement/movement graph. It can
therefore preserve a supplied envelope but cannot yet prove that the envelope
is Laboratory Beta execution truth.

The future fit is one pure, read-only Laboratory-Beta-to-engine adapter, not a
second persistence system. It must always emit a typed lineage projection that
preserves exact quantity kind, unit, basis, Decimal text, IDs, hashes,
conditions, uncertainty, opaque remainder, and blockers. A legacy
`FormulaState` may be emitted only when every required conversion is supported
by stock/lot- and condition-specific density/composition evidence; otherwise
the projection is answerless `ABSTAINED`. Planned receipts cannot masquerade as
prepared or measured runs, and requesting `FORMULA_STATE` cannot grant
headspace or OAV authority.

### Perfume Making Consultant 11-formula portfolio exact-byte resolution

Conversation `6a79b172-0264-83ec-b77a-306a37ecb832` supplied the standalone
`Complex_Perfumery_11_Formula_Portfolio.json`. The primary object had previously
been visible only as a cloud pointer after tunnel transport returned
`EXACT_BYTES_OR_CONNECTOR_UNAVAILABLE`. Authenticated browser retrieval now
resolves the exact original object:

- 2,617,388 bytes;
- SHA-256 `869757d6de9cca844475c9437b2e0de7d87596ba69cb2a0f1c568d205612e9f6`;
- strict UTF-8 and JSON parse;
- source object `file_00000000ce08820bb478271dae96a32f`;
- source response `2467d5f7-8168-439b-a330-3ebb12c536b2` and exact re-exposure
  response `742a0bf5-112a-4e2c-89ed-e8c73f0a48f4`.

The separately recovered 7,672-byte `VALIDATION_REPORT.json` remains its
standalone companion rather than an embedded member. The portfolio contains 11
computational candidates, 771 current-build rows, 788 target rows, 19 missing
concept rows, 55 test definitions, 187 G0-G16 gate records, and all 55 pairwise
formula diagnostics. All 11 formulas state
`COMPUTATIONAL RECONSTRUCTION CANDIDATE / PHYSICAL HOLD`. The source's 69/69
PASS result is internal arithmetic/schema consistency only: the same source
calls the formulas evidence-weighted reconstructions, not manufacturer formulas
or empirical similarity claims, and explicitly withholds aggregate authority.

The source is not interchangeable with the later exact-decimal successor. Nine
formula IDs overlap (`DHI12`, `DHP25`, `AHS`, `EB`, `EE`, `ELIXIR`, `LHOMME`,
`LANUIT`, `BDCP`), but none of the nine current hashes matches either the later
parent or successor hash, and no exact material-plus-parts row matches. `PR_E07`
and `PR_E01` are present only in this recovered portfolio. The correct
disposition is therefore a distinct candidate ancestry branch: retain all 11
formulas and the two unique IDs without merging, replacing, installing, or
normalizing either lineage.

The source has no primary citations and cannot upgrade its own physical or OAV
claims. Independent literature supports the existing native abstention gates:

- Teixeira et al. model perfume mixtures as nonideal liquids whose headspace
  depends on activity coefficients and ethanol composition
  ([DOI 10.1021/ie048760w](https://pubs.acs.org/doi/10.1021/ie048760w));
- direct fragrance-evaporation work uses HS-SPME/GC and shows surface-dependent
  release rather than a supplied-stock concentration proxy
  ([DOI 10.1016/j.talanta.2024.126851](https://www.sciencedirect.com/science/article/pii/S003991402401230X));
- odor-detection thresholds vary substantially with measurement method and
  require analytically controlled delivery
  ([PMID 37393967](https://pubmed.ncbi.nlm.nih.gov/37393967/),
  [PMID 19965900](https://pubmed.ncbi.nlm.nih.gov/19965900/));
- 222 tested binary mixtures showed masking far more often than synergy, so a
  vector/cosine diagnostic cannot establish mixture odor or liking
  ([PMID 33740506](https://pubmed.ncbi.nlm.nih.gov/33740506/));
- natural oils require constituent-resolved analytical and olfactometric work,
  not a single generic stock identity
  ([PMID 17339042](https://pubmed.ncbi.nlm.nih.gov/17339042/),
  [PMID 32163841](https://pubmed.ncbi.nlm.nih.gov/32163841/));
- diffusion models likewise use nonideal vapor-liquid equilibrium and ethanol
  matrix terms
  ([DOI 10.1016/j.ces.2009.01.064](https://www.sciencedirect.com/science/article/pii/S0009250909000700)).

Native C4 already forbids treating modeled output as measured headspace or a
validated nonideal prediction; C5 requires empirical calibration; C8 requires
context-matched threshold and candidate-air evidence and abstains when those
preconditions are absent. The recovered portfolio therefore justifies no
physics/OAV code replacement. Its `strict_oav=NOT CALCULABLE`, G15 HOLD, and
physical/sensory/safety/release holds agree with the native boundary.

The exact capture is bound by
`incoming_review/chatgpt/20260819T134159Z-formula-portfolio-6a79b172/capture_manifest.json`
and the authority-false receipt
`data/governance/complex_perfumery_11_formula_portfolio_package_receipt_20260819.json`.
No formula, inventory, bottle, physical, sensory, analytical, safety,
publication, installation, or release authority changed.

### Perfume Chemicals List orris-butter reference claim correction

Conversation `6a8050ce-526c-83ec-889f-36fe923bc7b8` asked whether one gram
of “orris butter 10% IPM” is worthwhile when Orris Liquid is already owned.
The three governing source messages are bound by rendered-text SHA-256 rather
than paraphrase: assistant composition/reconstruction message
`253526be76c6f2d3c2201547d5b01ae4bdcf0c2893a7a105c751e004a0d2636f`,
user purchase question
`592a06eecc69e85a3a78752a23b298987c16c4149226543a846502b4bf17da7b`,
and assistant purchase/trial response
`a6065fd58c420e663bd5ab4d10b846fc0d6b1f7ee6298a68a2968bd5de2bd07a`.
The useful source conclusion survives: Orris Liquid and natural orris butter
are not identity-equivalent, a single gram may be a cost-contained reference,
and no predicted improvement has been tested. The proposed IPM execution does
not survive source verification.

Current official product identity is carrier-specific. PerfumersWorld lists
SKU `5IA07847` as Orris Concrete/Orris Butter 10% in DPG, in stock at
US$2.20/g; its COA describes a proprietary perfume compound plus DPG and does
not quantify irones. SKU `5IA18424` is a separate 10% TEC product, currently
out of stock at US$2.05/g. The bounded official check found no current IPM SKU;
that nonretrieval is not proof that an IPM product cannot exist. Any future
comparison must bind the purchased label, SKU, carrier, concentration basis,
lot, and documents, then match the *actual* carrier. It must never default to
IPM. ([PW DPG product](https://www.perfumersworld.com/view.php?pro_id=5IA07847),
[PW TEC product](https://www.perfumersworld.com/view.php?pro_id=5IA18424),
[PW DPG COA](https://www.perfumersworld.com/ifra/COA/5IA07847.pdf))

The literature requires three scope corrections:

- the reported 56% myristic acid, 15.42% lauric acid, 14.50% capric acid, and
  2.85% alpha-irone belong to one steam-distilled *Iris pallida* rhizome-oil
  sample from Ukraine, not to the PerfumersWorld stock or to all orris butter
  ([PMCID PMC7227901](https://pmc.ncbi.nlm.nih.gov/articles/PMC7227901/));
- the published 4.16/34.46/0.16/61.26 values for trans-alpha/cis-alpha/beta/
  cis-gamma irone sum to about 100% because they are a normalized irone-isomer
  distribution, not whole-butter mass percentages; the distribution changes
  with botanical species
  ([DOI 10.1016/S1631-0748(03)00087-0](https://comptes-rendus.academie-sciences.fr/chimie/articles/10.1016/S1631-0748%2803%2900087-0/));
- Givaudan's 8%-irones *Iris pallida* butter is a separately standardized
  supplier product and cannot be used as the undisclosed composition of a PW
  lot
  ([Givaudan product](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/natural-ingredients/orris-pallida-butter-8-irones-france)).

ISO 18054:2004 supplies a GC method for measuring irone content in orris-
rhizome oil; it supplies no result for this supplier lot
([ISO 18054:2004](https://www.iso.org/standard/29826.html)). Therefore even
“1 g of 10% stock = 0.1 g nominal butter” is only conditional arithmetic until
the concentration basis is verified, and it never means 0.1 g irones.

The four-arm 0/25/75/150 mg stock comparison is retained only as a
nonexecuting design. It must be recomputed from the exact stock receipt and
carrier before use; no nominal active-mass, carrier-balance, blind trial, cart,
purchase, or formula action is authorized. Native V5 product-basis identity,
stock-lineage, pre-mix, and sensory-authority gates already enforce the needed
boundary, so no runtime, headspace, OAV, inventory, or formula code changed.
The source manifest is
`incoming_review/chatgpt/20260819T140438Z-orris-butter-6a8050ce/source_manifest.json`;
the authority-false local disposition is
`data/governance/orris_butter_reference_claim_receipt_20260819.json`.

### Immortelle Absolute to Helichrysum EO substitution correction

Conversation `6a818995-0090-83ec-9b8e-22ad37dd42f7` asked for the
Helichrysum EO volume equivalent of 49 uL Immortelle Absolute 10%. The user
message is bound by rendered-text SHA-256
`2ea5b33e6c788283e7da06444a43cef75e1572683898d3cd40452bf309bbc21a`;
the answer is bound by
`0a8fd8155c12317ea367097db24c7a1a611078376872047a8c249e7d482428d8`.
The answer's `49 x 0.10 = 4.9 uL` calculation is valid only if the nominal
10% is volume per volume. The chat did not state that fraction basis, use a
density, or establish that Immortelle Absolute and Helichrysum EO are identity
or sensory equivalents. Its approximate 5 uL substitution therefore does not
survive local admission.

The live inventory keeps the materials separate: Immortelle Absolute is a 10%
DPG working stock, while Helichrysum EO is neat/as supplied with botanical,
origin, lot, density, and composition details still open. The current
PerfumersWorld catalog page for SKU `5NY23688` identifies Immortelle Absolute
10% in DPG, lists US$0.59/g and a coarse specific gravity of 0.9010. Those
catalog values do not establish the concentration basis or density of the
user's actual lot, and they provide no Helichrysum-EO substitution factor.
The older local US$0.52/g value is retained only as observed price drift; no
cart or purchase state changed.
([PW product](https://www.perfumersworld.com/view.php?pro_id=5NY23688))

The literature reinforces the identity boundary rather than supplying a
generic conversion:

- *Helichrysum italicum* essential oil is dominated by volatile terpenes,
  whereas polar and semipolar constituents occur in different extract
  fractions; a wide range of extract types and compositions is reported
  ([PMCID PMC8399527](https://pmc.ncbi.nlm.nih.gov/articles/PMC8399527/));
- essential-oil chemotypes vary with geography and genetics, so one generic
  EO composition cannot identify this bottle
  ([PMCID PMC11836004](https://pmc.ncbi.nlm.nih.gov/articles/PMC11836004/));
- botanical authentication, region, development, genotype/subspecies, and
  extraction or distillation method materially affect composition
  ([PMCID PMC9957194](https://pmc.ncbi.nlm.nih.gov/articles/PMC9957194/),
  [DOI 10.3390/chromatography9100280](https://doi.org/10.3390/chromatography9100280));
- a direct comparison reports striking compositional differences between
  supercritical-fluid extracts and essential oil, which rules out a
  literature-only extract-to-EO volume factor
  ([DOI 10.1080/01496395.2016.1237967](https://doi.org/10.1080/01496395.2016.1237967)).

The substitution is therefore `ABSTAINED_NOT_CALCULABLE`. Unlock requires the
Immortelle stock's fraction basis and density; the Helichrysum stock's exact
botanical identity, origin, lot, and density; analytical profiles for both;
and a defined odor attribute and matrix followed by blinded dose-response or
matching calibration. Native quantities, intervention-trial, and legacy
Laboratory-Beta adapters already reject or abstain from unsupported
mass-volume conversion, so no new runtime conversion logic is needed. The
source manifest is
`incoming_review/chatgpt/20260819T141521Z-immortelle-helichrysum-6a818995/source_manifest.json`;
the authority-false disposition is
`data/governance/immortelle_absolute_helichrysum_substitution_claim_receipt_20260819.json`.

### Thailand 1965 floral portfolio and “most hedonic” claim correction

Conversation `6a7c5b07-7000-83ec-8489-53f859a90abe` supplied the exact
`THAILAND-MASS-MARKET-FLORAL-1965-TARGET-V1` archive, asked which formula was
most hedonic, and then generated an 18% Crystal Peony Rose mixing-order card.
The four source messages and both attachments are now bound by exact bytes and
SHA-256. The outer ZIP is 156,622 bytes with SHA-256
`4ec759409e005394ed303f6d6c103c8c98e66da6782a4e060ef924b5e46a9182`;
all eight members and four embedded checksum records verify. The recipe is
11,640 bytes with SHA-256
`dc8ff680b0ffed6dfaf67f52f39a8aac65eec9e2da73152af0e0137806a6f052`.

The package is useful design ancestry and internally preserves its own limit:
zero physical batches, zero liking results, zero broad-appeal results, no
strict OAV or measured headspace, safety not cleared, and release withheld.
Its complete geometry is retained without flattening it to the chat's winner:

- TH65-F01 Crystal Peony Rose: 74-row ideal design and 71-row current build;
- TH65-F02 White Tea Magnolia: 74-row ideal design and 70-row current build;
- TH65-F03 Lilac Wisteria Memory: 77-row ideal design and 73-row current build;
- 45 gate rows, seven missing-chemical-impact rows, eight preparation or
  verification rows, and eight controlled tests, all not run.

The source's ranking of Crystal Peony Rose as the most hedonic and most
commercially promising remains `SOURCE_CLAIM_ONLY_NOT_TESTED`. Literature does
not turn a paper architecture into a target-market winner. A large
cross-cultural monomolecular study found substantial shared ordering but also
large individual variation
([PMID 35381183](https://pubmed.ncbi.nlm.nih.gov/35381183/)); a later
five-population study found ecological and cultural availability still affects
preferences
([PMID 38863390](https://pubmed.ncbi.nlm.nih.gov/38863390/)). Neither study
tests these complex perfumes, this target demographic, or purchase intent.
Concentration changes hedonic ratings relative to individual thresholds and
odor identity, so 18% cannot be selected as an optimum from composition alone
([PMID 36323760](https://pubmed.ncbi.nlm.nih.gov/36323760/)). Even binary-
mixture prediction required empirical constituent pleasantness and perceived
intensity
([PMCID PMC2533422](https://pmc.ncbi.nlm.nih.gov/articles/PMC2533422/));
current mixture work likewise relies on measured component and replicate human
ratings rather than formula text
([PMCID PMC13371102](https://pmc.ncbi.nlm.nih.gov/articles/PMC13371102/)).

The 18% card is preserved exactly but is not executable. It contains 71
aromatic additions plus ethanol, two `PREPARE` rows, three `VERIFY FIRST`
rows, one label-verification row, and one opaque product-basis row. More
importantly, its row title says `Cedramber 10%` while the exact-stock field and
dose use neat/as supplied Cedramber. The 30 mL column remains reference-only.
Unlock requires all eight package preparation/verification rows to be bound,
the Cedramber stock-basis conflict to be resolved, formula-specific safety and
skin-use review, coded 16%/18%/20% microbatches at fixed application dose, and
the package's reference-free target panel repeated on a second day. No formula,
inventory, cart, purchase, compounding, runtime, or release state changed.

The exact capture is
`incoming_review/chatgpt/20260819T143426Z-hedonic-comparison-6a7c5b07/`;
the authority-false disposition is
`data/governance/th65_hedonic_comparison_portfolio_claim_receipt_20260819.json`.

### Working Stock Preparation DEP: preserve the design table, withhold Helvetolide identity and possession

Conversation `6a830dfe-c4c8-83ec-bb1e-f859fa6375f9` supplied 23
working-stock recommendations and later asserted `I have 1 g helvetolide`.
All seven rendered messages are now bound by exact message IDs, bytes, and
SHA-256. The 23-row table is preserved losslessly as planning ancestry; it was
not installed as stock, inventory, formula, compounding, or release authority.

The Helvetolide assertion does not match either `inventory.txt` or the
authoritative V5 current-stock snapshot. A local PerfumersWorld catalog row
does name Helvetolide at SKU `3XD17215`, but catalog availability is not
physical possession. More importantly, the supplier's current documents call
that SKU a proprietary perfume compound and complex mixture. The separate
DSM-Firmenich `HELVETOLIDE 947650` reference sheet identifies CAS
`141773-73-1` and molecular weight 284, but does not identify the user's bottle.
The RIFM safety assessment for that CAS is ingredient-level context only; it
does not establish the bottle, lot, purity, dilution basis, or final-formula
safety.

Accordingly, `1.00 g supplied product + 1.00 g DEP = 2.00 g at 50% w/w` is
valid only on a supplied-product basis. It is not evidence of 50% pure
molecular Helvetolide. The corresponding 20% and 10% arithmetic remains
planning-only as well. Unlock requires the bottle label, supplier/SKU, lot,
exact concentration or product basis, physical mass, DEP lot, and balance
calibration, followed by the existing native parent-child stock-preparation
receipt. `backend/app/services/stock_lineage.py` already supplies that guard;
no runtime change is needed.

The exact capture is
`incoming_review/chatgpt/20260819T150500Z-working-stock-dep-6a830dfe/source_manifest.json`
(3,417 bytes, SHA-256
`4fadae024ca62d7045899594dc450d485937b246d5f14a7b5c9210b349a04cd5`).
The authority-false disposition is
`data/governance/working_stock_dep_claim_receipt_20260819.json` (10,081
bytes, SHA-256
`180c4c24fcae9246c34e1fbea48f16696b755d4dcc10d9e6a2c8ceeb6f09f798`;
semantic receipt SHA-256
`a376b9183922d00994b04c1be9ac4bff12f2968d85b1d9ba151c34088504b462`).

### Data Integration work hub: recover the historical controls without replaying stale state

Conversation `6a77b1b5-fabc-83ec-896b-9b7c5c5a2ebf` is a coordination and
historical-integration hub, not a single scientific result. All 63 rendered
messages are now bound by exact message ID, role, UTF-8 byte count, and
SHA-256: 45 user messages and 18 assistant messages. Four inline control
artifacts were also recovered by exact bytes:

- the 28,047-byte lossless-integration control report, SHA-256
  `157115c3a71c259808c48715705b7a2d68f68320f1019cfd0e38e4979501afe7`;
- the 10,698-byte all-chat read-only request, SHA-256
  `f9b563eb58457452fe3703373ed62f50e7858837a6c1cb3580b88afe0c314875`;
- the 33,671-byte report schema, SHA-256
  `151f42f085e7301fad1309104eac74391f96acbd384003fd2be71ac44a39495e`;
- the 16,589-byte provisional destination ledger, SHA-256
  `4e5e125f2a014607f6b6c479b10951e23c36d37008a7905b5f64c3d24e69c7a6`.

These files correctly self-classify as pre-dispatch controls: zero requests
had been sent, and the 75 rows were provisional functional destinations, not
75 proven conversations. They therefore cannot replace the later 38-chat
point-in-time local registry, current bridge status, current Git state, or
current automation state. Historical status statements in the conversation
are preserved as source claims only.

The chat's recommended Ma-2021 binary-mixture lane is already implemented in
`backend/app/adapters/ma_2021.py` and
`backend/app/services/ma_2021_baselines.py`. The later exact benchmark binds
the 487,926-byte workbook at SHA-256
`c540f18ba71b778c36756810fff38bdf177c2af9d593567a6dba57a30503c950`,
6,660 participant trial rows, 222 source aggregate rows, and 198 unique
mixture groups. Its decision remains source-internal calibration only;
nonlinear escalation and same-source novelty are not authorized. The C0 and
external-study recommendations likewise have later native local successors.
Sixteen task-output citations were not reconstructed or declared absent;
their exact bytes remain unresolved, while the corresponding P0, C0,
evidence-admission, and Ma lanes are historical or successor-covered rather
than runtime inputs.

The exact capture is
`incoming_review/chatgpt/20260819T160000Z-data-integration-6a77b1b5/`;
its source manifest is 17,033 bytes with SHA-256
`d39170cd058faa951ccc01c425e4015c059d44c571e16c016f4a7a2e5c7eaa2c`.
The preservation-only disposition is
`data/governance/data_integration_chat_historical_control_receipt_20260819.json`
(6,620 bytes, SHA-256
`d8fe065b2596b5c69b9dd94c31c009b3e1743286ecf632b33fd06ad27a0a6a1f`;
semantic receipt SHA-256
`81dba021e40a89211047c91b16656b48d8d559db8379e9bcb94633d8c88f1b6b`).
No formula, inventory, stock, model, runtime, bridge, automation, or release
state changed.

### Perfume Chem Task Update: bind the G15 handoff without replaying old hashes

Conversation `6a7765a9-a50c-83ec-a73e-0dce89b28c55` is a three-message
status handoff with no attachment. Its named local report,
`runs/HOURLY_STATUS_AND_G15_COMPLETION_20260809.md`, is exact at 14,102 bytes,
SHA-256
`1104cd55352ad8f49a843905d9b284da7afb10abd0917cef75daff0a1c14eae6`.
The report's six code/test hashes are retained as a historical point-in-time
snapshot, not silently rebound to later dirty-tree bytes.

Current local verification separately establishes that G15 remains wired as a
hard gate, same-stock active-dose jumps at or above threefold fail without
explicit authority, stock-rebase active equivalence remains hard-blocking,
parent baseline and UID checks fail closed, the release CLI and optimizer carry
parent/authority state, and run evidence includes G15. The focused regression
is currently 15/15 passing. No G15 implementation file was recreated,
reformatted, or otherwise mutated during this intake.

Primary literature on human threshold variability and odorant-receptor
antagonistic, suppressive, and additive mixture behavior supports the existing
conservative boundary: modeled OAV is anomaly screening only, not a linear
perceived-contribution model, measured-headspace claim, or standalone perfume
verdict. The exact conversation capture is
`incoming_review/chatgpt/20260819T173000Z-perfume-chem-task-update-6a7765a9/source_manifest.json`
(2,109 bytes, SHA-256
`99cbd2c3d120cf919de5cb890bf4f70685001da81c789d240755c4637b2e2608`;
semantic receipt SHA-256
`234586c1c2f061ce83085541d688e25f3bc14246dd2b580c079600b3531a7d8b`).
The authority-false implementation-provenance receipt is
`data/governance/perfume_chem_task_update_g15_provenance_receipt_20260819.json`
(5,831 bytes, SHA-256
`bd2be95752cc201a01ecb843f2c84acf0af1fca40d0a5930ea5b7023feb18af8`;
semantic receipt SHA-256
`4127fb567ea6f7343b981155e73552ccbefb52c49afce407feaa03bdd1f4fd0e`).
All formula, inventory, OAV, headspace, physical, sensory, safety, compounding,
and release authorities remain false.

## Dependency-ordered job map

| Priority | Job | Why now | Completion evidence |
|---:|---|---|---|
| P0 | Immutable stock/dose receipt consumed by gate, formula state, simulation, scaling, robustness, OAV, scoring, audit, optimizer, and reports | Prevents silent 10%-to-neat quantity errors and stale gate reuse | Implemented: exact V5/stock/source/fraction/raw/active/formula receipt SHA; tamper/stale/mismatch tests pass |
| P0 | Bind executable inventory to V5 Current Inventory Master and preserve exact stock IDs | A correct downstream receipt cannot repair a false upstream neat/ownership assumption | Implemented for release preflight; 280-row snapshot equality and semantic regressions pass |
| P0 | Separate planned active-equivalence authority from engine screening and physical metrology | Prevents two numeric paths from independently claiming equivalence PASS | Implemented: exact-decimal planned receipt v3, migration/API/export persistence, and hash replay in backend; engine emits screen-only states; physical authority remains withheld |
| P0 | Bind strict OAV to exact receipt identity and native C8 typed abstention; remove legacy intelligence from primary status/rank | Prevents raw-request reconstruction, unknown-air crashes, and unsupported heuristics from becoming authority | Implemented: strict missing/incompatible evidence is answerless `ABSTAINED`; modeled screening is advisory, primary `WITHHELD`, rank zero; 135 focused + 51 consumer tests pass |
| P0 | Make workspace import an atomic whole-graph invariant replay | Invalid stock domains, synthetic terminal state, stale mapping, and ambient-transaction row leakage previously bypassed import authority | Implemented: owned SAVEPOINT, closed V5 stock domain, latest target/mapping and event-chain replay, proposal-to-commit conservation, physical-balance cap, and zero-row rejection regressions; 35 focused + 6 lineage tests pass |
| P0 | Replay current target, mapping, and selected-stock authority across the live build lifecycle | A plan valid at creation could otherwise approve, reserve, enter execution, propose, or commit after its governing target/mapping/stock contract changed | Implemented through one reusable existing-plan validator at authority-bearing transitions, reservation, proposal, and commit; six RED-to-GREEN plus one stock-drift regression, 42 critical tests passed, and independent workspace replay retained |
| P0 | Bind C8 predicted gas evidence to the exact validated C3 model-domain result | A caller-supplied `within_model_domain=true` could self-authorize a cross-matrix or cross-condition predicted-gas computation | Implemented: predicted gas embeds and verifies the exact C3 release/request/domain/applicability/output result, operation, `COMPUTED` state, and `may_feed_oav_screening`; exact matrix, temperature, pressure, relative humidity, and full C2 application-environment hash must agree with the bound request; legacy predicted/boolean paths reject, measured evidence remains independent; 195 focused and 541 adjacent tests pass with unrelated C0 and frozen-C5 holds kept explicit |
| P0 | Canonicalize hard-gate dispatch and result identity for duplicate materials | The duplicate gate emitted an ID absent from the hard set, so policy could demote a real FAIL to WARN | Implemented narrowly: `duplicate_canonical_materials` is the sole emitter, dispatch, and hard-blocking ID; two dead aliases were removed; focused replay stays FAIL through policy and aggregate status, with 73 focused tests passing |
| P1 | Reconcile natural-composite census and malformed live-profile fields | Restores honest dependent-suite signal without hiding evidence gaps or inventing numeric character scores | Implemented; 20-natural/3-opaque census and all-profile mapping contract pass |
| P1 | Rebase the C5 frozen-design inventory parent deliberately | C5 pins an older `inventory.txt` hash and must not be rebound by convenience | Implemented as an authority-false V5 rebase assessment: exact v1 program, 280-row snapshot, and workbook hashes; complete 19-line/8-matrix semantic diff; decision `HOLD_REDESIGN_REQUIRED`; 3 focused tests pass; no v2 program created |
| P1 | Preserve full rights plus claim-scoped source relations through B1 persistence | Required before Chat B/D/F/G packages can be admitted losslessly | Implemented; candidate-to-DB-to-report equality, tamper hashes, populated migration, and scope tests pass |
| P1 | Add operation-scoped B1 source-use constraints | Channel terms can permit API discovery while prohibiting archival, training, publication, redistribution, or commercial runtime | Implemented: append-only exact source/terms/artifact/channel/action/purpose assertions, structured obligations, latest-version assessment, B9 projection, and migration; missing/conflicting dimensions HOLD; no legal conclusion |
| P1 | Retire unvalidated Meaningful Complexity v2 runtime thresholds | Row count, a generic collision cutoff, and a compensatory score can overrule stronger stock, evidence, and physical-observation gates | Implemented: active prompt, governing document, and native decision contract now use WITHHELD candidate-only noncompensatory authority; v2 ancestry is preserved and missing v3 bytes remain unadmitted |
| P1 | Admit Chat-C patent/Deite formula blocks as ordered B1 source extractions | Legacy percentage-map helpers lose raw units, totals, order, explicit absences, product basis, rights, and arm dependence | Exact authority-false package receipt implemented; zero rows admitted. Rebuild the two collapsed US8168163B2 absence rows from primary bytes, then produce an immutable 130-row B1 source grammar plus separately hash-bound nonexecuting projections; no `LabFormula` population |
| P1 | Bind the Working Stock Preparation DEP design table and resolve the Helvetolide bottle before any stock preparation | A chat possession claim and a catalog name cannot establish current stock or pure-molecule concentration | Implemented as an authority-false 23-row receipt. Helvetolide remains `CHAT_REPORTED_POSSESSION_UNVERIFIED`; the 50%/20%/10% calculations are supplied-product-basis arithmetic only until label/SKU/lot/mass/carrier evidence closes the native parent-child receipt |
| P1 | Preserve the Data Integration hub's exact historical controls and separate them from later local successors | The chat contains useful pre-dispatch controls, but its 75 destinations, bridge/GitHub state, Ma recommendation, and task-output claims are historical and cannot overwrite current registry or runtime state | Implemented as a 63-message, four-attachment authority-false receipt. Ma and C0 have stronger local successors; 16 unrecovered task-output citations remain unresolved without inferred absence or duplicate implementation |
| P1 | Register the Interaction Atlas package and inventory parent as secondary reconstruction | Exact bytes exist and are internally coherent, but rights and underlying source artifacts remain unresolved | Authority-false receipt implemented; 27 source IDs remain blocked candidate pointers, not B1 records |
| P1 | Register the exact Chat-F package and the nearby 80-source data-science bundle as distinct secondary planning inventories | Chat F exact bytes now exist, but all 80 rows lack included rights artifacts, 65 were not live-verified in-lane, and baseline parents are absent; the nearby scored registry remains a distinct artifact with missing raw sources/lineage | Exact authority-false Chat-F receipt implemented; zero source rows imported. Keep the separate registry's RED parent closure and route any future source use through native operation-scoped review |
| P1 | Register the exact Chat-G package as historical schema evidence without installing its parallel store | Exact package bytes and internal checks are coherent, but exact parent SQL/SQLite bytes and final A-F bindings are absent; the package itself keeps both integration holds open | Exact authority-false Chat-G receipt implemented; zero schema/code/source rows imported. Laboratory Beta remains the sole persistence authority |
| P1 | Register the Chat 1-3 recovery pack as pointer inventory only | It contains zero of 28 specialist bytes and forbids reconstruction | Retrieval records only; no source admission |
| P1 | Register the "Canonical" upload kit as an incomplete transport package | 29 included members verify, but six required authority files are absent | Per-member hashes plus explicit missing set; no authority promotion |
| P1 | Deduplicate and register the 16.6 MB unintegrated-intake receipt | Two copies are byte-identical; its own rule says plan-only and 29 archive records are do-not-import | One package identity plus 162 individual dispositions; no bulk import |
| P1 | Register the Program-v3 final package and recovery kit as terminal/pointer snapshots | Final architecture passes its own checks while engine, bytes, physical work, approval, and release remain held | Preserve explicit hold state and retrieval hashes; no execution authority |
| P1 | Register OAV-HSG, stock-hardening, and Execution RC2 as historical/candidate packages | All are mechanically coherent but duplicate or predate native code and lack current repository qualification | Deduplicated receipts and nonduplicative regression inventory; no wholesale patching |
| P1 | Register the 156-target, corrective-screen, and woody/amber/musk packages as secondary design/quantity ancestry | Exact local packages add useful censuses but have no physical results and contain provenance or V3-version holds | Per-package hashes and explicit non-execution/V5-replay dispositions |
| P1 | Admit Batch-05 formulas and six accord nodes as source hierarchy only | Exact bytes and source arithmetic exist, but neither formula nor any accord is fully V5-executable | Immutable source coordinates/hashes, accord links, and per-row V5 requalification children; execution false |
| P1 | Admit the Violet Leaf portfolio as an external source/design hierarchy | Eight payload hashes verify, but rights, exact stock carrier/lot, strict OAV, and physical results are unresolved | Package receipt, four formula hierarchies, proxy-OAV and ladder records, V5 child; all formulas held |
| P1 | Admit the Tobacco/Amber teaching portfolio and preserve the TBC-02 collision | Twenty payload hashes verify and 839 uses are censused, but safety/stock metadata are incomplete and the repo adaptation is lossy | Separate source/adaptation nodes, machine-readable omission delta, course/design roles, V5 child; no overwrite or activation |
| P1 | Register the six-recipe reconstruction pack without importing formulas | Forty-five declared payload hashes verify, but all doses are inferred, 48 mappings are nonexact, rights are unknown, and physical/safety gates are open | Authority-false receipt implemented; six source/build branches remain external and held |
| P1 | Resolve Chat B source geometry without fabricating its missing package | The 64-versus-125 conflict blocked a faithful experimental-design representation | Primary study identifies a 3-axis x 5-level design; retain 125 derived mixtures, 15 singleton stimuli, and one air control only after rights-governed source acquisition; quarantine 64-arm legacy grid |
| P1 | Implement the native external-study admission slice shared by Chat A/G, Chat-3 tea, and Chat-5 fruit sources | Published participant/trial data, pair aggregates, omission/recombination results, GC-O panels, controls, condition arms, and source-only formulas have incompatible grains and cannot enter the physical `LabExperiment` model | Implemented under Laboratory Beta with eight append-only B1-bound tables, exact participant/group/aggregate/sample grain, operation-scoped rights and extraction gates, source-family and identity nonleakage, deterministic tamper-evident projection, and all formula/model/physical/sensory/release authorities false |
| P1 | Design a one-way mixed-dimension Laboratory-Beta-to-engine projection for the unrecovered Chat-7 PR-2B concept | Native planned and actual lineage exists, but FormulaState cannot losslessly represent mixed mass/volume dimensions or prove an executed run | Dirty-tree candidate preserves typed lines and abstains on incompatible conversion; 13 focused tests pass. Still HOLD: no production canonical-record assembler/caller, and run state, hashes, and evidence remain caller-supplied; no parallel store or capability promotion |
| P1 | Register Chat D v1.1 as an authority-false receipt, then design native receptor-source admission | Exact package bytes are recovered, but Keller is a governed duplicate, M2OR is dynamic and rights-held, OlfactionBase has a live 875-page/874-export conflict, and DoOR is Drosophila-specific | Deduplicate Keller; separately model release snapshots, raw assay rows, derived consensus, discovery associations, species-normalized responses, and model outputs; require source rights and immutable bytes; no ORTarget defaults or perceptual promotion |
| P1 | Register Chat E v1 and its separate post-freeze hardening addendum without importing either runtime | Exact bytes preserve 12 source pointers, six model scopes, and six useful v1 defects, but source bytes, rights, numeric tables and matrix transfer are absent | Authority-false dual receipts implemented; native C3/C8 and B5 remain controlling after 90 + 84 focused tests; package code and rows stay unexecuted/uninstalled, and physical/release authority remains held |
| P1 | Register the exact Chat E v1.2 domain-adjudication addendum without adopting its host code | Exact bytes close the previously missing package-level six-model codebook and bind exact v1.1 ancestry, but numeric tables, licensed model inputs, private reference data, local execution and host bindings remain absent | Authority-false receipt implemented after independent publisher/JRC identity checks and native C3/C8/B5 diff; retain the source-specific codebook as migration evidence only, with all empirical, runtime, OAV and release authority held |
| P1 | Bind the Perfume Chem Task Update G15 handoff without replaying historical file hashes | The status report is exact and the current behavior is testable, but its embedded hashes describe an earlier point in time | Implemented as a three-message authority-false provenance receipt; current G15 behavior passes 15 focused tests, no duplicate implementation or reformat was performed, and modeled OAV remains anomaly screening only |
| P1 | Register the exact 11-formula Perfume Making Consultant portfolio as a distinct candidate branch | The recovered JSON preserves two portfolio-only IDs and complete G0-G16 structure, but nine overlapping names are not hash- or row-equivalent to the later exact-decimal successor | Exact authority-false artifact receipt implemented; all 11 formulas remain quarantined physical-HOLD ancestry, pairwise metrics remain diagnostic only, and native C4/C5/C8 remain controlling |
| P1 | Bind the Perfume Chemicals List orris-butter purchase claim and correct its carrier/composition scope | The chat preserves a useful one-gram reference idea, but current official products are DPG and TEC rather than verified IPM, literature compositions are source-specific, and the exact lot/basis are unknown | Authority-false source receipt implemented; future comparison must bind and match the exact purchased carrier; no purchase, cart, formula, stock, trial, or runtime authority |
| P1 | Bind the Immortelle Absolute-to-Helichrysum EO claim and remove its implicit v/v and identity assumptions | `49 x 10% = 4.9` is conditional arithmetic, while the two complex naturals are distinct extraction products and the user-lot basis, density, composition, and sensory match are unresolved | Authority-false source receipt implemented; substitution is `ABSTAINED_NOT_CALCULABLE`; existing density guards remain controlling and no formula, inventory, purchase, or runtime state changed |
| P1 | Register the Thailand 1965 three-formula portfolio and demote its paper-only hedonic crown | The exact package preserves useful formula branches, preparation queues, and tests, but it reports zero physical batches or liking results; the 18% card also contains an unresolved Cedramber 10%-title versus neat-dose conflict | Exact authority-false ZIP, member, message, and recipe receipt implemented; all three ideal/current branches and eight tests are preserved; no formula installation, compounding, purchase, or hedonic promotion |
| P2 | Recover/hash-bind remaining exact Chat A-G worker packages where bytes actually exist | Converts chat reports into reproducible local evidence candidates without fabricating missing attachments | Recovery pointers for absent packages; byte/schema/row/null/unit/parser/config manifests only for recovered bytes |
| P2 | Build native external-only adapters, not a parallel 34-table truth database | Avoids authority duplication and schema drift | Read-only deterministic projections and failure-closed tests |
| P2 | Resolve current inventory identity/property gaps and stale V5 stock claims | Quantity and identity precede model/data expansion | Physical receipt per stock, exact grade/carrier/strength, conflict records |
| P3 | Add matrix/substrate-specific physical-calibration manifests | Headspace and skin behavior are context-specific | Measured standards, uncertainty, domain, method, instrument, environment |
| P3 | Design the 2-acetylpyrazine parent-by-dose study only after exact stock qualification | The current Atlas/profile links are priors, the 1% carrier is unstated, the ODT is provisional, and parent extracts are non-interchangeable | Separate neutral/Coffee Absolute/Cocoa Absolute conditions, carrier-matched controls, exact active mass, repeated coded observations, and a prespecified parent-by-dose interaction estimand; no automatic Atlas update |
| P3 | Design a source-informed multi-axis peach ablation/add-back study only after V5 identity closure | Fruit sensomics supports multiple axes but not source-equivalent perfume doses; Gamma Decalactone is legacy-only/unqualified and Nonanal is absent | Resolve exact stocks first, then preregister qualified lactone/linalool/beta-ionone/hexyl-acetate arms with carrier controls and assessor/session replication; no fruit-equivalence or formula authority |
| P3 | Run blinded physical experiments | Converts hypotheses into evidence | Lemonile 0x/0.5x/1x; pair omissions/additions; panel and headspace protocols |
| P4 | Compare perceptual models on held-out data | Tests strongest-component, linear-average, and competitive models honestly | Registered split, metrics, uncertainty, abstention and failure cases |
| P4 | Regenerate downstream JSON/SQLite/Parquet/FAISS projections | Only safe after source and selection records are accepted | Input/config/software hashes and deterministic reproduction |

## Current stock and formula holds carried forward

- Lemonile exists both neat and at 1% in DPG. A prior precautionary dose
  reduction is not a calibrated potency law; keep it on physical-evidence HOLD
  pending a blinded 0x/0.5x/1x comparison.
- Javanol resolves only to 20% in DPG; neat is a GAP. Alpha Irone resolves to
  30% w/w in IPM; 10% is a GAP.
- Beta Ionone neat and 0.1% are separate physical stocks; the old 1% row is not
  owned. Carrot Seed EO 1%/10%, Heliotropal 10%, Citronellol 10%, and Dihydro
  Beta Ionone 10% require fresh preparation receipts from neat stock.
- Neroli EO resolves to the owned 10% DPG stock only.
- Immortelle Absolute 10% in DPG and Helichrysum EO neat/as supplied are
  separate identities. Neither stock has the complete lot-specific basis,
  density, composition, and blinded sensory calibration needed for direct
  uL-for-uL substitution; the chat's approximate 5 uL conversion is held.
- The Working Stock Preparation chat's `1 g Helvetolide` statement is absent
  from both `inventory.txt` and the authoritative V5 stock snapshot. The local
  PerfumersWorld SKU is a catalog-only proprietary-mixture record, while the
  DSM-Firmenich CAS sheet is a separate reference molecule. Retain all
  Helvetolide dilution arithmetic on supplied-product-basis HOLD until the
  physical bottle identity, lot, concentration basis, and mass are receipted.
- TH65-F01 Crystal Peony Rose remains a computational formula candidate, not
  an executable stock plan or established hedonic winner. Its Cedramber row
  must resolve the `10%` title versus neat/as-supplied dosing conflict, and all
  remaining prepare/verify, safety, concentration, and target-panel gates must
  close before compounding or preference claims.
- 2-Acetyl Pyrazine is owned neat/as supplied plus a 1% working stock with
  carrier unstated. The diluted stock remains non-executable until its carrier
  and concentration basis are receipted; its provisional ODT cannot set dose.
- Oakmoss Absolute 10%, Safraleine 10% and neat, and Raspberry Ketone 20% and
  neat are present in the current inventory snapshot. `Scentanal` is unresolved,
  while `Scentenal` is not present in the current V5 physical-stock snapshot;
  the legacy `inventory.txt` entry cannot create ownership.
- Benzaldehyde is present neat and at 1%, not at the older claimed 10%; a 10%
  stock requires a fresh preparation receipt.
- Globanone 50% and Amber Xtreme 0.1% were not present in the reconciled
  inventory snapshot. Romandolide is present as neat/as supplied in V5 and
  must not inherit the older absence claim.
- Gamma Decalactone appears in legacy `inventory.txt` but is absent from the
  authoritative V5 current-stock snapshot; it is
  `LEGACY_ONLY_UNQUALIFIED`, not executable stock. Nonanal is absent. Melonal,
  Blackcurrant Absolute, Cassis Base, whole fruit, and published fruit odorants
  remain non-equivalent identities.
- Black Tea Base is absent from authoritative V5. Phenylacetaldehyde Dimethyl
  Acetal is not phenylacetaldehyde; Aldehyde C10 requires exact CAS/B4 evidence
  before decanal identity; and neat Nerolidol requires stereochemical
  confirmation before binding an `(E)` source row.
- Le Berre's complete experimental factorial is 64 mixtures (3 axes x 4
  levels). The target is a separate paired-comparison reference. The exact Chat
  B package is recovered and hash-verified, but its 125-row reconstruction is
  quarantined; governed source-table bytes and reuse rights remain missing.

## Acceptance boundary

This reconciliation records and verifies the local exact receipt-bound
stock/dose and typed strict-OAV abstention path, V5 inventory, exact-decimal
planned active-equivalence/screening boundary, OAV-ranking, profile-schema, and
B1 metadata-persistence, operation-scoped source-use, native source-only
external-study admission, and atomic workspace-import changes described above.
It does
**not** authorize a formula,
physical result, sensory claim, similarity claim, universal complexity law,
generic synergy multiplier, external-data promotion, canonical-database load,
purchase, compounding run, or fragrance release.
