# ADR: A0 canonical reconciliation and write authority

Date: 2026-08-01
Status: Accepted for the A0 baseline
Starting SHA: `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435`

## Decision

Laboratory Beta SQL records are the persistence authority. `LabService` owns transactions, `LabRepository` and its mixins own SQLAlchemy persistence/query operations, and engine objects are computations, proposals, or read-only projections unless explicitly imported through a canonical service. Generated Markdown/JSON reports and bound formula artifacts are not independent truth stores.

The legacy `/api/v1/lab` and v2 Laboratory Beta routes may coexist only when both call the same canonical service/table set. New persistence must not target engine in-memory ledgers, legacy top-level formula/ingredient/outcome tables, optimizer-local SQLite, or generated reports.

## Domain reconciliation

| Reconstruction concept | Canonical destination | Disposition | Duplicate risk | Allowed write path |
|---|---|---|---|---|
| Evidence source/document | `LabSourceDocumentVersion`, `LabSourceExtractionRecord`, `LabSourceDerivationLink`, `LabEvidenceWorkflowEvent` | `CANONICAL_EXISTING` | High | `LabSourceServiceMixin.register_source_document`, `record_source_extraction`, `add_source_derivation`, workflow transition -> `LabRepository` |
| Evidence ledger/claim | `LabEvidenceRecord` plus explicit evidence-link tables | `ADAPT_LEGACY_TO_CANONICAL` | High | `LabService.record_evidence` -> `LabRepository.add`; engine `EvidenceLedger` is computation/projection only |
| Target hypothesis | `LabTargetHypothesisVersion`, `LabTargetLine`, `LabTargetEvidenceLink` | `CANONICAL_EXISTING` | Medium | `LabService.create_target_hypothesis` / `revise_target_hypothesis` |
| Accepted target | `LabAcceptedTargetVersion` | `CANONICAL_EXISTING` | Low | `LabService.accept_target`; never mutate the hypothesis row |
| Formula-version DAG | `LabFormula`, `LabFormulaVersion`, `LabFormulaComponent`, `LabFormulaVersionEdge` | `CANONICAL_EXISTING` | High | `LabService.add_formula_version` and `link_formula_version`; engine DAG is a read-only projection |
| Stock lot / inventory ledger | `LabStockSolution`, `LabInventoryMovement`, `LabInventoryReservationEvent` | `MIGRATE_AND_DEPRECATE_LEGACY` | High | `LabService` inventory/bottle/reservation methods; append movements, never decrement an engine ledger |
| Inventory mapping | `LabInventoryMappingVersion`, `LabInventoryMappingEvidenceLink` | `CANONICAL_EXISTING` | Low | `LabService.create_inventory_mapping` / `revise_inventory_mapping` |
| Build formula / plan | `LabBuildPlanVersion`, `LabBuildPlanLine`, `LabBuildPlanEvidenceLink` | `CANONICAL_EXISTING` | Low | `LabService.create_build_plan` and lifecycle transition methods |
| Bottle batch/event | `LabBottle`, `LabBottleEvent`, `LabBottleEventEffect`, `LabBottleMeasurement` | `MIGRATE_AND_DEPRECATE_LEGACY` | High | `LabService` bottle methods; `BottleBatch` may replay but may not persist |
| Bottle console action | `LabBottleActionProposal`, `LabBottleActionConfirmation`, `LabBottleActionCommit`, measurements/events/movements | `CANONICAL_EXISTING` | Low | propose -> confirm -> measure -> `LabService.commit_bottle_action` |
| Analytical ledger | Physical records in `LabAnalyticalMethodVersion`, `LabAnalyticalRun`, `LabAnalyticalPeak`, `LabAnalyticalQCRecord`, `LabAnalyticalAttachment`, `LabGCOEvent`; authority in B5 `LabAnalytical*Authority` tables | `ADAPT_LEGACY_TO_CANONICAL` | High | `LabScienceServiceMixin` for physical records and `LabAnalyticalAuthorityServiceMixin` for reviewed authority |
| Sensory ledger | `LabExperiment`, `LabSample`, `LabApplication`, `LabObservation`, `LabPairwiseComparison`, `LabPrediction`, `LabOutcome` | `ADAPT_LEGACY_TO_CANONICAL` | High | `LabService` experiment/application/observation/prediction/outcome methods; engine `SensoryTrial` is projection only |
| Regulatory snapshot | B6 source/rule/supplier/composition tables plus `LabRegulatorySnapshotVersion` and `LabRegulatoryAuthorityFinding`; A2 assessment rows are precursor records | `CANONICAL_EXISTING` | Medium | `LabRegulatoryAuthorityServiceMixin.evaluate_regulatory_snapshot`; no engine snapshot persistence |
| Authority vector / claim decision | `LabClaimAuthorityVersion`, `LabClaimAuthoritySupportLink`; engine `AuthorityVector` remains derived | `ADAPT_LEGACY_TO_CANONICAL` | High | `LabClaimAuthorityServiceMixin.create_claim_authority_version`; recalculations create new immutable versions |
| Experiment plan/protocol | `LabExperiment`, `LabSample`, `LabPrediction`, linked formula/build-plan versions | `CANONICAL_EXISTING` | Medium | `LabService.create_experiment`, `add_experiment_sample`, `record_prediction` |
| Material identity | `LabMaterial`, `LabMaterialAlias`, `LabConstituent` | `CANONICAL_EXISTING` | High | `LabService.create_material`; alias direct-commit exception must move behind service in A1 |
| Property observation/selection | `LabPropertyObservation`, conflict/member tables, selected assertion/candidate tables | `CANONICAL_EXISTING` | High | `LabPropertyServiceMixin.record_property_observation`, conflict and selected-assertion methods |
| Contextual threshold/OAV | `LabThresholdObservationContext`, `LabOAVAssessment`, quarantined `LabLegacyThresholdRecord` | `CANONICAL_EXISTING` | High | `LabThresholdServiceMixin`; legacy thresholds cannot promote without context |
| Knowledge rules | rule group/member, knowledge rule, contradiction, support evidence, compilation run tables | `CANONICAL_EXISTING` | High | `LabRuleServiceMixin`; compilation output is versioned evidence, not prose truth |
| Backfill campaign/dashboard | B8 campaign, priority, signal-link, gap, dashboard-cell tables | `CANONICAL_EXISTING` | Medium | `LabBackfillServiceMixin.create_backfill_campaign`; dashboard cells are campaign projections |
| Reports | `ScienceReportingService` and release/report scripts project from canonical rows | `EXPERIMENTAL_DO_NOT_PERSIST` | Medium | Generate from a pinned snapshot/version; never edit a report as source data |
| Formula Markdown/artifact binding | SQL formula/target/build-plan versions are persistence authority; embedded manifest is a bound release artifact | `ADAPT_LEGACY_TO_CANONICAL` | High | `FormulaImportService` / `LabService` for import; `formula_release_gate.py` and reviewed `rebind_formula_artifact.py` for artifacts |
| Exact bottle-addition arithmetic | `engine.bottle_addition.AdditionSolver` | `EXPERIMENTAL_DO_NOT_PERSIST` | Low | Compute a proposal; physical commit only through `LabService` |

## Named duplicate or adjacent stores

| Store | Relationship | Risk and decision |
|---|---|---|
| `engine.evidence.ledger.EvidenceLedger` | In-memory evidence ledger | High. Adapter/read projection only; no persistence. |
| `engine.inventory.stock_model.InventoryLedger` | Mutable stock/consumption ledger | High. Writes prohibited; use append-only SQL movements. |
| `engine.bottle.events.BottleBatch` | In-memory bottle stream | High. Replay only; writes prohibited. |
| `engine.sensory.ledger.SensoryTrial` and `engine.analytical.ledger.AnalyticalLedger` | Computation ledgers | High. Import to canonical services or keep experimental. |
| `backend.app.models.perfume.Formula` -> `formulas` | Legacy formula table | High. Migrate/deprecate for Laboratory Beta; do not dual-write with `lab_formula_versions`. |
| `ingredients`, knowledge-graph `materials`, and `lab_materials` | Three material identities with different consumers | High. Laboratory Beta writes only `lab_materials`; reference KB is read-only input until explicit import. |
| `formulation_outcomes` / `pairwise_preferences` and `lab_outcomes` / `lab_pairwise_comparisons` | Legacy feedback versus Laboratory Beta experiment history | High. No dual-write; migrate through versioned import if convergence is required. |
| `engine.optimizer.models.DB_PATH` score-calibration writes | Optimizer-local SQLite path | High. It is not Laboratory Beta authority and must not satisfy a lab release gate. |
| `data/perfumery_kb.db` and root `perfume_chem.db` | Reference knowledge base versus application database | Low when roles remain separated. Never treat KB rows as application transaction history. |
| Markdown formula files and SQL formula versions | Human artifact/input versus immutable application record | High. Binding/import must be explicit and provenance-preserving. |

A2 physical analytical/regulatory records and B5/B6 authority records are complementary layers, not duplicate truth: the former records what was run or assessed, while the latter records reviewed method/scope/claim authority with provenance.

## Allowed-write rule and current exception

The default allowed chain is endpoint -> `LabService`/mixin -> transaction context -> `LabRepository`/mixin -> canonical SQL table. Adapters may construct drafts or projections but may not import `AsyncSession`, `LabRepository`, or `LabService`, commit/rollback, or invoke legacy mutators. The runtime AST scanner reports zero prohibited adapter paths.

Current exception: `backend/app/api/v1/endpoints/lab.py:add_material_alias` directly uses `session.add`, `commit`, and `refresh`. It writes `lab_material_aliases`, so there is still one table authority, but it bypasses transaction/service policy. A1 must either add a `LabService` method and route through it or explicitly reject the route. No additional direct-write exception is accepted for new work.

## Consequences

- Engine arithmetic and scientific models remain reusable without acquiring database authority.
- Every persisted scientific decision is immutable/versioned or append-only and links to evidence.
- Generated reports, dashboards, and formula artifacts cannot promote themselves into truth.
- Legacy stores stay readable only for bounded migration/projection until consumers are proven and retired.
- A1 may harden contracts and close the alias service-boundary exception, but it may not invent a second store.
