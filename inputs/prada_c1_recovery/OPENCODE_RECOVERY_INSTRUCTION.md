# OpenCode Input-Recovery Instruction

Your discovery plan reported an INPUT HARD STOP because the exact governing C1 workbook and final verdict were absent from the current OpenCode workspace. The attached pack supplies the exact authoritative artifacts from the accepted C1 governing bundle.

## Required action

1. Copy or extract this pack into a new isolated `inputs/prada_c1_recovery/` directory.
2. Hash every file independently and compare against `RECOVERY_MANIFEST.json`.
3. Verify the governing workbook contains:
   - UID `PLH-CURRENT-EDT-INV-C1-20260806-BA4366B26231`;
   - 44 rows;
   - 1,000.000 supplied-stock parts;
   - governing row hash `ba4366b2623130478b56b34d97087611ada095787a17a285aeae44f1b31f3c3f`.
4. Verify the final verdict identifies the same UID/hash and `PILOT AUTHORIZED` desk state.
5. Reclassify the two prior GLOBAL HARD STOP entries as `RECOVERED AUTHORITATIVE INPUT / HASH-VERIFIED` only after those checks pass.
6. Reclassify the two CrossBrand files as `RECOVERED SYNCED SYSTEMS OF RECORD / HASH-VERIFIED` only after independent inspection.
7. Resume the replacement contract at governing formula integrity verification, fixed-core extraction, and reviewer lanes.
8. Do not treat differently named bundle contents as replacements when the exact files in this pack are available.
9. Do not change the formula, invent physical evidence, or authorize Phase G.

If any hash, UID, row count, total, or workbook identity fails, retain `FORMULA INTEGRITY HOLD` and report the exact mismatch.
