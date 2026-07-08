# Bleu Luxe Mineral Jasmine - OAV Analysis Summary
**Date:** 2026-05-09  
**Formula:** Bleu_Luxe_Mineral_Jasmine_vF_30mL_EDP.md  
**Analyst:** OpenCode Agent

---

## What Was Done

### 1. VP Data Corrections (48 materials updated)
Applied measured VP values from `VP_ODT_fragrance_data.xlsx` to `engine/ingredient_intelligence.py`:

**Critical Fixes:**
- β-Ionone: 1.2 → 7.20 Pa (BASF SDS)
- Hedione: 0.003 → 0.210 Pa (ChemicalBook)
- Iso E Super: 0.003 → 0.231 Pa (IFF SDS)
- cis-Jasmone: 0.02 → 0.91 Pa (ChemicalBook)
- α-Isomethyl Ionone: 0.008 → 0.400 Pa (Perflavory)
- Rose Oxide: 0.5 → 53 Pa (ScenTree)
- See full list: `docs/vp_corrections_log_2026-05-09.txt`

### 2. Formula Adjustments
- β-Ionone: 60 µL → 15 µL (75% reduction to balance jasmine)
- α-Isomethyl Ionone: 270 µL → 100 µL (removed expensive dead weight)

### 3. Name Normalization Fixes
Added aliases in `engine/name_utils.py`:
- `"b-ionone"` → `"beta ionone"` (Greek β normalization)
- `"a-ionone"` → `"alpha ionone"` (Greek α normalization)

---

## OAV Analysis Results

### Formula Statistics
- **Total OAV:** 85,220
- **Perceptible materials:** 53 of 60
- **Concentration:** 15.4% EdP
- **Batch volume:** 31.075 mL

### Register Balance (by OAV)
| Register | OAV | % | Status |
|----------|-----|---|--------|
| **Musk** | 44,924 | 52.7% | ⚠️ DOMINANT |
| **Rose** | 22,298 | 26.2% | ⚠️ HIGH |
| **Woods** | 12,733 | 14.9% | OK |
| **Jasmine** | 2,126 | 2.5% | ⚠️ LOW |
| **Citrus** | 1,853 | 2.2% | OK |
| **Ionone/Orris** | 1,287 | 1.5% | OK |

### Critical Issues
1. **Ambrofix flooding** - 33,306 combined OAV (39% of formula)
2. **Rose Oxide too high** - 16,090 OAV at just 2.5 µL active
3. **α-Damascone too high** - 5,363 OAV at 1.5 µL active
4. **Jasmine weak** - Only 2.5% of total signal
5. **β-Ionone ODT missing** - Cannot calculate OAV

### Top 10 Materials by OAV
1. Ambrofix (base add) - 19,308 (21.9%)
2. Rose Oxide - 16,090 (18.3%)
3. Ambrofix (heart) - 13,998 (15.9%)
4. Romandolide - 8,045 (9.1%)
5. α-Damascone - 5,363 (6.1%)
6. Ethylene Brassylate - 2,414 (2.7%)
7. Iso E Super - 2,253 (2.6%)
8. Kephalis - 1,931 (2.2%)
9. Cashmeran - 1,609 (1.8%)
10. Vertofix - 1,609 (1.8%)

---

## Jasmine Register Detail
| Material | Active µL | ppm | OAV |
|----------|-----------|-----|-----|
| cis-Jasmone | 20 | 644 | 1,287 |
| Hedione | 400 | 12,872 | 515 |
| Hedione HC | 200 | 6,436 | 257 |
| Jasmine Sambac Absolute | 10 | 322 | 40 |
| Dihydrojasmone | 40 | 1,287 | 26 |
| **Total** | **670** | | **2,126** |

**Target:** Jasmine should be 10-15% of total OAV (currently 2.5%)

---

## Recommended Fixes (Priority Order)

### 🔴 CRITICAL (Do First)
1. **Reduce Ambrofix** 1,085 µL → 400 µL (-685 µL)
   - Move to base only, remove from Step 1 adds
   - Reduces musk from 53% to ~25%

2. **Reduce Rose Oxide** 25 µL → 8 µL (-17 µL)
   - Still perceptible (OAV ~5,000) but not flooding

3. **Add β-Ionone ODT** to `engine/odor_thresholds.py`
   - Typical value: ~0.007 ppb
   - Enables proper OAV calculation

### 🟡 HIGH (Next Pass)
4. **Reduce α-Damascone** 15 µL → 5 µL (-10 µL)
   - Balance rose character

5. **Increase Jasmine Sambac** 150 µL → 400 µL (+250 µL)
   - Brings jasmine to ~8-10% of signal

6. **Add missing ODTs** for:
   - Polysantol
   - PEA (Phenethyl Alcohol)
   - α-Irone
   - β-Ionone

### 🟢 MEDIUM (Fine Tuning)
7. Consider reducing α-Isomethyl Ionone further (100 → 50 µL)
8. Add more Hedione HC if jasmine needs more radiance

---

## Data Sources
- **VP data:** `C:\Users\Kenny\Downloads\VP_ODT_fragrance_data.xlsx`
  - Givaudan SDS, IFF, BASF, ChemicalBook, ScenTree, NIST
- **ODT data:** `engine/odor_thresholds.py`
  - Leffingwell, ScenTree, literature
- **Profiles:** `engine/ingredient_intelligence.py`

---

## Files Modified
1. `engine/ingredient_intelligence.py` - 42 VP corrections
2. `engine/name_utils.py` - Greek letter aliases
3. `formulas/Bleu_Luxe_Mineral_Jasmine_vF_30mL_EDP.md` - Dose adjustments

---

## Full Report
See: `docs/oav_analysis_Bleu_Luxe_vF_2026-05-09.txt`
