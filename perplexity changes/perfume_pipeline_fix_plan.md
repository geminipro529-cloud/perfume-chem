# Perfume Pipeline Fix Plan

## Goal
Make the perfume engine idiot-proof so any AI can run it safely on new formulas.

## Required order
1. Normalize all ingredient names.
2. Resolve the fragrance family.
3. Convert raw percentage to active percentage.
4. Check OAV.
5. Check family fit.
6. Run temporal simulation.
7. Apply repair suggestions if needed.
8. Only then optimize.

## Hard rules
- Never use raw percentages for scoring if a material is diluted.
- Never accept duplicate ODT keys.
- Never let exact string matching decide material identity.
- Never skip family resolution.
- Never evaluate only one timepoint.
- Never let sub-threshold support materials fail silently.

## Material checks
Every material must have:
- Canonical name
- Alias list
- CAS number if available
- MW
- logP
- Vapor pressure
- ODT with source
- Role and family
- Dilution factor

## Gate checks
### 1. Data integrity
- Duplicate detection
- Missing fields
- Invalid units

### 2. Active-dose check
- Convert to active percent
- Reject if dilution is unknown

### 3. OAV check
- Calculate odor contribution
- Flag OAV < 1 as support/echo only

### 4. Family check
- Match formula to intended family template
- Compare top/heart/base pattern

### 5. Time check
- Simulate at 0h, 1h, 4h, 8h, 24h
- Track which notes dominate each window

### 6. Repair check
- Suggest dose reduction
- Suggest material swap
- Suggest family correction
- Suggest base/heart/top rebalance

## Templates to include
- Woody vetiver
- Chypre
- Oriental
- Citrus
- Green
- Floral
- Leather
- Marine
- Gourmand
- Animalic

## Output format
For every formula, produce:
- Valid or invalid
- Reason for failure
- Which gate failed
- Suggested fix
- Time evolution summary
- Family fit summary

## Fail-fast behavior
Stop immediately on:
- Missing family resolver
- Duplicate ODT entry
- Unknown dilution factor
- Missing active percentage
- Broken name normalization

## Safety note
If the formula is not fully validated, do not let it reach optimization.
