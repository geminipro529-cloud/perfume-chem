---
name: duplicate-odt-scanner
description: Scan odor_thresholds.py for duplicate material entries where the last entry wins
---

## What I do
- Scan `engine/odor_thresholds.py` for duplicate material keys
- Count occurrences and identify which value "wins" (last entry)
- Flag materials with conflicting ODT values between entries
- Cross-check against `inventory.txt` for in-stock materials only

## When to use me
Use when:
- A material has an unreasonably high OAV (100M+) — common duplicate symptom
- After adding or editing ODT_DATA entries
- Before any pipeline gate run as a quality check
- When investigating data quality issues

## Scanner procedure

1. Parse `engine/odor_thresholds.py` and extract all keys from `ODT_DATA` dict
2. Count occurrences of each key (case-insensitive)
3. For materials with count > 1:
   - Show the ODT values for each occurrence
   - Identify which value "wins" (last entry in file)
   - Flag if values differ between entries (conflict)
4. Filter report to only materials that exist in `inventory.txt`
5. Cross-check against known bug: the Agidol fix where ODT was wrong

## Report format

| Material | Occurrences | Winning ODT | Other values | Stock? |
|----------|-------------|-------------|--------------|--------|

Flag with CRITICAL if:
- Winning ODT differs from earlier entries by more than 10x
- Last entry has suspiciously low value (sub-ppb for non-musk)
- Material is in-stock and the winning value is wrong per known fixes

## Known patterns to flag
- ODT 50.0 → 3.0 (Benzoin Resinoid pattern — last entry correct)
- ODT 20.0 → 0.05 (Hedione pattern — last entry correct)
- Any 0.0 or missing ODT in the winning entry
