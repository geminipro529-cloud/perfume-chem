# Root master check report — three force-pushed checks (2026-09-11)

Purpose: record the state of the three checks that were force-pushed past on the
root archive (`D:\chatbots\perfume-chem`, `master` @ `c35289af`), as listed in
the session handoff. Run from the root archive with its own venv; no root files
were modified.

Command:

```powershell
.\.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify `
  --only formula-artifact-validation --only scientific-audit `
  --only material-data-validation --json
```

## Result

| Check | Root master (`c35289af`) | Integration HEAD |
|---|---|---|
| formula-artifact-validation | **FAIL** | PASS |
| scientific-audit | **FAIL** | PASS |
| material-data-validation | **FAIL** | PASS |

All three pass on the integration branch quick gate, so the failures are
archive drift, not a repository-wide regression.

## Evidence per check

### formula-artifact-validation
`artifact-verify` verdict `FAIL`; 514 artifacts:
`NONE 414`, `QUARANTINED 14`, `STALE 35`, `TAMPERED 1`, `UNBOUND_LEGACY 50`.
Blocking policy: `STALE`, `TAMPERED`. Example stale binding:
`formulas\AHS_2004_Reference_First_From_Zero_30mL_EDT_v2_Neat_Neroli.md`
(`inventory`, `scientific_inputs`, `pipeline_source`).

### scientific-audit
`tests/test_oav_authority.py` fails at collection/run with:

```
engine.inventory_parser.InventoryAuthorityError: current inventory alias
crosswalk hash drift: expected 4320f19e1d3dff1cca885ad3d8004c2354cef4c3964e31668a6615028bb914d6,
got 32ee2107e02fdd5f1b923a19852e78cd71f904be17f082f881b56f201ecb76d2
```

Root master's `CURRENT_INVENTORY_ALIAS_CROSSWALK_SHA256` pin does not match the
crosswalk file it ships.

### material-data-validation
`tests/test_inventory_material_additions.py` fails (8 failed, 72 passed in the
check run). Representative: `Black Agarwood Artificial` resolves to dilution
`0.1` where `1.0` is expected — root's inventory authority and runtime material
data paths drifted apart.

## Recommended next action

Do not patch the root archive in place. Re-baseline or promote the integration
branch (which carries the current inventory authority, extraction, and passing
checks), then re-run these three checks on the promoted commit. If the root
archive must stay frozen, record these three as documented holds with this
report as evidence.
