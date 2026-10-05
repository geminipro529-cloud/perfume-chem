# Perfume-Chem Inventory V5 Direct-Stock Assertion Reconciliation

Decision: `DATA_AMBER_DPG_ASSERTIONS_RECOVERED_EXACT_STOCK_AND_PREPARATION_RECEIPTS_RED`

## Result

The current inventory text explicitly records two 1% working stocks in DPG:

- `2-Acetyl Pyrazine (1% in DPG)` at `inventory.txt:211`.
- `Lemonile (1% in DPG)` at `inventory.txt:35`, with a stated date of 2026-05-25 and a stated relation to neat stock.

These statements narrow two V5 provenance gaps. V5 records 2-Acetyl Pyrazine's 1% carrier as unstated and represents only neat Lemonile. The new result is additive: it does not edit either parent.

## Positive and negative truth

Positive: both carrier assertions can be preserved as `USER_ASSERTED_DPG`. Lemonile also has user-asserted date and parent-relation text.

Negative: each inventory comment is a user assertion, not a preparation receipt. Neither working stock has a bound ExactStockRef, bottle-label or lot witness, concentration basis, parent stock ID, measured preparation quantities, or complete preparation lineage.

Therefore, **0 of 2 closure actions are complete**. `CLR-001` and `CLR-002` remain `OPEN_PARTIAL_EVIDENCE`.

## Literature boundary

The literature review does not replace local stock evidence. PMID 36571813 directly studied odorants in five solvents including dipropylene glycol and found that liquid concentration need not translate proportionally to vapor concentration because solvent interactions matter. A liquid `1% in DPG` statement therefore does not establish headspace exposure. PMID 30949040 concerns propylene glycol rather than dipropylene glycol and cannot prove DPG neutrality or carrier identity. PMID 18534998 and PMID 34041322 support concentration-aware, repeatable future binary-mixture methods, while ISO 13301:2018 addresses 3-AFC threshold methodology. None validates the user's bottles or preparations.

## Stop gate

Before either working stock enters a physical experiment, bind separate exact stock identifiers, label or lot witnesses, concentration basis, carrier, parent stock identity, and a measured preparation record or exact purchased-dilution lineage.

No physical experiment is authorized. Formula, inventory mutation, preparation, sensory, scientific, safety, procurement, collection, installation, and release authority all remain false.
