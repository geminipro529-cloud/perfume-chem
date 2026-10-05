# Inventory V5 remaining experiment-readiness evidence audit

Decision: `DATA_AMBER_REMAINING_CLOSURES_CLASSIFIED_NONE_READY_PHYSICAL_AND_REBASE_GATES_PRESERVED`.

This audit covers CLR-003 through CLR-016. It does not create stock identities, preparation receipts, formula revisions, or physical authority.

## Current disposition

- Ready to close: 0.
- Formula rebase required: CLR-005 Javanol and CLR-006 Alpha Irone.
- Formula rebase plus stock-lineage closure required: CLR-007 Beta Ionone.
- Carrier identity, then physical preparation required: CLR-008 Peru Balsam.
- Physical label or preparation evidence required: CLR-003, CLR-004, and CLR-009 through CLR-016.

The distinction matters. Existing material names, historical dilution labels, formula instructions, and inventory comments are not preparation receipts. Likewise, a known replacement stock does not make old formula rows executable until exact active dose and carrier contribution have been deterministically rebound.

## DeepLuna Chat efficiency finding

A 14-node DIRECT_PRO batch admitted seven jobs while seven failed at client transport without job IDs. After the admitted jobs settled and a fresh exact-project check returned `READY`, a separate seven-node client admitted and completed all remaining lanes. This is an observed client-fanout behavior, not proof that the daemon's configured 50-reader capacity is false. No runtime file was changed, no admitted job was retried, and no fallback or Fast route was used.

## Boundary

No physical preparation is authorized by this audit. Every affected formula row remains held until its exact gate passes. Formula, inventory, stock, preparation, physical, sensory, scientific, safety, procurement, collection, installation, and release authorities remain false.
