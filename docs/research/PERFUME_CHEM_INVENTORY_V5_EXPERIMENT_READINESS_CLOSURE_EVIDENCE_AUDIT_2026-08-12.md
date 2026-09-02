# Inventory V5 experiment-readiness closure evidence audit

Decision: `OPEN_PARTIAL_EVIDENCE_EXACT_STOCK_AND_PREPARATION_LINEAGE_NOT_CLOSED`.

This audit advances the first two actions in the ranked closure queue without overstating what the repository proves. It does not create an `ExactStockRef`, a preparation receipt, or authority to dose an experiment.

## CLR-001 - 2-Acetyl Pyrazine

The repository presently contains three different kinds of evidence:

- `inventory.txt` asserts a 1% in DPG stock;
- the current V5 snapshot records neat stock plus a 1% working stock while keeping that carrier unstated;
- the PerfumersWorld catalog lists SKU `5EN13769` as 1% in DPG.

Those facts do not close the action. A supplier catalog row does not prove which bottle or lot is owned, and it cannot silently resolve the V5 carrier hold. Closure still requires separate exact identities for neat and 1%, a physical label or lot witness, an explicit fraction basis and carrier, and preparation-or-supplier lineage tied to the owned stock.

## CLR-002 - Lemonile

`inventory.txt` asserts both neat Lemonile and a 1% in DPG dilution. The V5 snapshot records only neat/as-supplied Lemonile. The Demachy extension file contains instructions to make the dilution, but instructions are not evidence that preparation occurred.

Closure still requires a distinct exact identity for each stock and an executed preparation receipt binding the neat parent, DPG, quantities, basis, date, and resulting working stock. Until then the V5-versus-inventory drift remains explicit and prospective dosing must abstain.

## Outcome

- Both actions remain `OPEN_PARTIAL_EVIDENCE`.
- No closure receipt was minted.
- No source file, formula, inventory row, V5 snapshot, physical stock, database, or pipeline was changed.
- All formula, inventory, stock, preparation, physical, sensory, scientific, safety, procurement, collection, installation, and release authorities remain false.

DeepLuna Chat ran two bounded `DIRECT_PRO` read-only audits in parallel. Sol independently reproduced and accepted only their fail-closed provenance conclusions.
