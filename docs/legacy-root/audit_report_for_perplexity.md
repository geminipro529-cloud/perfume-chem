# Chemical Data Audit Report — Perfume Chemistry Repository

**Date:** 2026-05-10
**Scope:** All chemical data across JSON databases, YAML material catalog, Python embedded data, and inventory file.
**Purpose:** Identify blank, null, suspicious, or inconsistent data that needs correction.

---

## 1. CRITICAL: Vapor Pressure Unit Mismatches in material_properties.json

**File:** `data/knowledge_graph/material_properties.json`

Vapor pressure (`vp`) values are inconsistently sourced — some entries use Pa (Pascals), others use mmHg. This breaks any VP-dependent calculation (sillage modeling, evaporation curves, diffusion fields).

| Material Name | VP in File | Likely Unit | Expected VP (Pa at 25C) | Error Factor |
|---|---|---|---|---|
| Cedarwood EO | 100.0 | mmHg | 0.003–0.1 | ~1000x too high |
| Ethanol 96% | 5900.0 | mmHg | ~7870 | Close to mmHg value |
| Hexyl Acetate | 150.0 | mmHg | ~2000 | Close to mmHg value |
| DPG | 190.0 | mmHg | ~2.5 | ~76x too high |
| Linalool | 22.0 | mmHg | ~0.16 | ~137x too high |
| Rose Oxide | 25.0 | mmHg | ~53 | Roughly correct in Pa |
| Linalyl Acetate | 10.0 | mmHg | ~1.3 | ~8x too high |
| Dihydromyrcenol | 10.0 | mmHg | ~0.3 | ~33x too high |
| Citronellal | 8.0 | mmHg | ~2.8 | ~3x too high |
| Florol | 6.0 | mmHg | ~0.05 | ~120x too high |
| Guaiacol | 14.0 | mmHg | ~0.02 | ~700x too high |
| Lavender EO (Bontaux) | 22.0 | mmHg | ~0.5 | ~44x too high |
| Cardamom EO | 15.0 | mmHg | ~1–3 | ~5–15x too high |

**Contrast with ingredient_intelligence.py**, which appears to use Pa consistently for the same materials:
- Linalool: 0.16 Pa (correct)
- Cedarwood EO: 0.25 Pa (reasonable)
- Galaxolide: 0.0001 Pa (correct)

**Request to Perplexity:** Verify the correct VP at 25°C in Pa for each of the 13 materials listed above. Provide authoritative source citations (PubChem, TGSC, or ChemSpider).

---

## 2. CRITICAL: Molecular Weight Errors

### 2a. Cyclamen Aldehyde MW Mismatch

| Source | MW Value | Correct? |
|---|---|---|
| material_properties.json | 190.28 | Correct (C13H18O = 190.28) |
| compounds.json | 174.24 | **WRONG** (9.2% error) |

CAS: 103-95-7. Molecular formula: C13H18O. Correct MW = 190.28.

**Request:** Confirm MW 190.28 is correct. What is the source of 174.24?

### 2b. Null MW in ingredient_intelligence.py

These inventory materials have `mw: None` in the Python data:

| Material | Notes |
|---|---|
| I-IRIS F-TEC | Proprietary blend — no MW available |
| JASMIN ABS F-TEC | Proprietary blend — no MW available |
| Jasmine Absolute | Natural extract — variable MW |

**Request:** Provide representative MW values for these materials (dominant component MW is acceptable for natural extracts and blends).

---

## 3. HIGH: Missing Boiling Point for Orivone

**File:** `data/knowledge_graph/material_properties.json`, entry "ORIVONE"
**Field:** `bp` (boiling point) is `null`

Orivone (CAS: 36306-53-9 or related) is a ketone used as an iris/orris material. Its boiling point is missing.

**Request:** What is the boiling point of Orivone at 1 atm?

---

## 4. HIGH: Null VP for Orivone in ingredient_intelligence.py

**File:** `engine/ingredient_intelligence.py`, line 577
**Entry:** "Orivone" — `vp: None`

**Request:** What is the vapor pressure of Orivone at 25°C in Pa?

---

## 5. HIGH: Inventory Count Mismatches

**File:** `inventory.txt`

The file states "Raw entries: 195" but actual count is **197**. Category-level mismatches:

| Category | Stated | Actual | Difference |
|---|---|---|---|
| Floral Materials | 48 | 49 | +1 |
| Iris / Violet | 13 | 14 | +1 |
| Woods / Amber / Structure | 27 | 28 | +1 |
| Musks | 11 | 10 | -1 |
| Sweet / Gourmand / Balsamic | 16 | 14 | -2 |
| Spice / Aromatic | 16 | 19 | +3 |
| **Total** | **195** | **197** | **+2** |

**Request:** Identify which entries were added/removed without updating the totals.

---

## 6. HIGH: YAML Material Catalog Has Massive Data Gaps

**File:** `data/materials/*.yaml` (26 files, A–Z, 1210 total entries)

For the 191 entries flagged as `user_in_inventory: true`:

| Field | Missing Count | % Missing |
|---|---|---|
| CAS number | 176 / 191 | 92.1% |
| Molecular weight | 54 / 191 | 28.3% |
| ODT (air, ppb) | 177 / 191 | 92.7% |
| SMILES | ~180 / 191 | ~94% |
| Character dimensions | ~170 / 191 | ~89% |

**Request:** For the following high-priority inventory materials, provide CAS, MW, and ODT (air ppb and ethanol ppm):

1. Aldehyde C10 (Decanal)
2. Aldehyde C11 (Undecanal)
3. Aldehyde C12 MNA (2-Methylundecanal)
4. Alpha Damascone
5. Alpha Ionone
6. Alpha Irone
7. Alpha-Isomethyl Ionone
8. Ambrettolide
9. Ambrox Super
10. Ambrofix
11. Amyl Cinnamic Aldehyde
12. Anisaldehyde
13. Apritone
14. Aurantiol
15. Azarbre
16. Bacdanol
17. Benzoin Resinoid
18. Benzyl Acetate
19. Benzyl Benzoate
20. Benzyl Salicylate
21. Bergamot FCF
22. Beta Ionone
23. Birch Tar Rectified
24. Black Pepper FTEC
25. Blackcurrant FTEC
26. Calone
27. Cardamom FTEC
28. Cardamom EO
29. Carrot Seed EO
30. Cashmeran
31. Cedramber
32. Cedamber
33. Cedarwood EO
34. Cedarwood oil Virginia
35. Cinnamaldehyde
36. Citral
37. Citronellal
38. Citronellol
39. Coumarin
40. Cyclamen Aldehyde

(And approximately 137 more — full list available on request.)

---

## 7. MEDIUM: Duplicate Entry in chemicals_potency.json

**File:** `backend/data/reference/chemicals_potency.json`

"Aldehyde C-12 MNA" and "C-12 MNA" are listed as separate entries with identical data:

```json
"Aldehyde C-12 MNA": {
  "min_percent": 0.1, "max_percent": 0.5, "typical_percent": 0.2,
  "category": "top", "potency": "extreme", "function": "The Shimmer"
},
"C-12 MNA": {
  "min_percent": 0.1, "max_percent": 0.5, "typical_percent": 0.2,
  "category": "top", "potency": "extreme", "function": "The Shimmer"
}
```

**Request:** Confirm these are the same material. If so, which name should be canonical?

---

## 8. MEDIUM: CAS Number Validation Failures

**File:** `data/knowledge_graph/material_properties.json`

These CAS numbers fail the check-digit validation:

| Material | CAS in File | Issue |
|---|---|---|
| Amber Xtreme | 1204333-82-1 (estimated) | Check digit fails |
| Bergamot FCF | 68648-33-3 | Check digit fails |
| Isobutyl Quinoline | 13223-63-3 (mixture) | Check digit fails |
| Kephalis | 58985-01-2 (primary isomer) | Check digit fails |

**Request:** Provide the correct CAS numbers for:
1. Bergamot FCF (furocoumarin-free bergamot oil)
2. Isobutyl Quinoline (6-isobutylquinoline, mixture of isomers)
3. Kephalis (Firmenich woody-amber material)
4. Amber Xtreme (Symrise amber material — may be proprietary with no public CAS)

---

## 9. MEDIUM: Null Jellinek Fields for Several Materials

**File:** `data/knowledge_graph/material_properties.json`

These entries have `null` for `jellinek_axis` and `jellinek_effect`:

| Material | Notes |
|---|---|
| Macrolide | Macrocyclic musk |
| Methyl Pamplemousse | Grapefruit-type modifier |
| Molecule Iris | Iris accord |

**Request:** Assign Jellinek quadrant positions and psychological effect descriptions for these three materials based on their olfactory character.

---

## 10. MEDIUM: VP Cross-Source Inconsistencies

Comparing VP values between `material_properties.json` (MP) and `ingredient_intelligence.py` (II):

| Material | MP VP | II VP | Ratio | Assessment |
|---|---|---|---|---|
| Galaxolide | 0.07 | 0.0001 | 700x | MP likely wrong (should be ~0.0001 Pa) |
| Vanillin | 0.02 | 0.0003 | 67x | MP likely wrong |
| Ambrox Super | 0.004 | 0.05 | 0.08x | II likely closer |
| Cashmeran | 0.05 | 1.2 | 0.04x | II likely closer |
| Cedramber | 0.03 | 0.002 | 15x | Discrepancy |
| Beta Ionone | 0.85 | 7.2 | 0.12x | II likely closer |
| Aldehyde C10 | 2.0 | 19.3 | 0.10x | II likely closer |
| Aldehyde C11 | 0.67 | 50.0 | 0.01x | II likely closer |
| Iso E Super | 0.03 | 0.231 | 0.13x | II likely closer |
| Coumarin | 0.02 | 0.19 | 0.11x | II likely closer |

**Request:** For the 10 materials above, provide the authoritative VP at 25°C in Pa from PubChem or TGSC. Identify which source file (MP or II) has the correct value for each.

---

## 11. LOW: Null Fields in material_properties.json (Functional/Solvent Entries)

These are acceptable nulls for solvent/carrier materials but noted for completeness:

| Material | Null Fields |
|---|---|
| DPG | arctander_tenacity, typical_pct_range, max_safe_pct, jellinek_axis, jellinek_effect |
| Ethanol 96% | arctander_tenacity, typical_pct_range, max_safe_pct, jellinek_axis, jellinek_effect |
| IPM | arctander_tenacity, typical_pct_range, max_safe_pct, jellinek_axis, jellinek_effect |
| DEP | carles_pairing_rule, jellinek_axis, jellinek_effect |
| Amber Core Accord | olfactophore, arctander_character, typical_pct_range, carles_pairing_rule |

No action needed — these are functional materials, not odorants.

---

## 12. LOW: Null Fields for Orivone in material_properties.json

**File:** `data/knowledge_graph/material_properties.json`, entry "ORIVONE"

Missing: `bp` (boiling point), `roudnitska_craft_note`

The entry also has `alt_name: null`.

**Request:** What is Orivone's IUPAC name, boiling point, and CAS number?

---

## Summary of Requests for Perplexity

1. **VP values (Pa at 25C)** for 13 materials with suspected unit mismatches in material_properties.json
2. **Confirm Cyclamen Aldehyde MW** = 190.28 (not 174.24)
3. **Boiling point and VP** for Orivone
4. **CAS, MW, ODT** for ~180 inventory materials missing from YAML catalog (priority list of 40 provided above)
5. **Correct CAS numbers** for Bergamot FCF, Isobutyl Quinoline, Kephalis, Amber Xtreme
6. **Confirm duplicate:** Aldehyde C-12 MNA vs C-12 MNA in chemicals_potency.json
7. **Jellinek assignments** for Macrolide, Methyl Pamplemousse, Molecule Iris
8. **Authoritative VP (Pa)** for 10 materials where material_properties.json and ingredient_intelligence.py disagree
9. **Orivone identity:** IUPAC name, CAS, BP, VP
10. **Inventory count reconciliation:** Which 2 entries explain the 195→197 discrepancy
