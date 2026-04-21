# Knowledge Gaps - Chemicals Lacking Verified Data

**Purpose:** Track chemicals mentioned in conversations or inventory that lack sufficient verified data for safe recommendations.

**Last Updated:** 2026-01-13

**CRITICAL RULE:** Do NOT recommend any chemical on this list until gaps are filled from trusted sources.

---

## Status Levels

- 🔴 **BLOCKED** - Critical gaps, DO NOT RECOMMEND under any circumstances
- 🟡 **PARTIAL** - Some data available, recommend with caveats only
- 🟢 **RESOLVED** - Gaps filled, safe to recommend

---

## 🔴 BLOCKED - Critical Data Gaps

### Orivone

**Status:** 🔴 BLOCKED

**Problem:**
- **CAS Number Mismatch:** Listed as 33704-61-9 (which is Cashmeran, NOT an iris molecule)
- **No Chemical Structure:** Unknown molecular formula
- **No Verified Odor Data:** Described as "orris-woody" but no TGSC/scientific confirmation
- **Trade Name Only:** Not an IUPAC chemical name
- **Single Source:** Only in PerfumersWorld, no corroboration

**Data Needed:**
- [ ] Correct CAS number from scientific source (TGSC, PubChem)
- [ ] Molecular structure/formula
- [ ] Odor threshold (ppm or %)
- [ ] Verified usage rate from formulations
- [ ] Supplier verification (is this a blend or pure molecule?)

**Alternative to Recommend:**
- ✅ **DIY α-Irone 10% in Isopropyl Myristate** (user owns both, $0 cost, authentic warm orris)
- ✅ **α-Irone 10% Myristic Acid** (commercial version, $5.13, verified)

**Action Taken:**
- Flagged in `chemical_data_validator.py`
- Blocked from recommendations
- User warned on 2026-01-13

**Resolution Path:**
1. Contact PerfumersWorld for detailed product information
2. Request GCMS analysis or supplier spec sheet
3. Cross-reference with TGSC database
4. If blend: identify components and ratios
5. If pure molecule: verify CAS and odor profile

---

## 🟡 PARTIAL - Incomplete Data (Use With Caution)

### [Placeholder for future entries]

**Status:** 🟡 PARTIAL

**Available Data:**
- 

**Missing Data:**
- 

**Recommendation Status:**
- Can mention with disclaimer
- Must cite data gaps
- Provide verified alternatives

---

## 🟢 RESOLVED - Previously Flagged, Now Verified

### [Placeholder for resolved items]

**Date Resolved:**

**How Resolved:**

**Sources:**

---

## Data Verification Checklist

Before recommending ANY chemical for purchase, verify:

### Tier 1: Identity (CRITICAL)
- [ ] CAS number confirmed in TGSC or PubChem
- [ ] Molecular formula known
- [ ] IUPAC name or verified trade name
- [ ] Supplier sells verified product (not mystery blend)

### Tier 2: Olfactory (ESSENTIAL for perfumery)
- [ ] Odor description from scientific source (TGSC preferred)
- [ ] Usage rate range documented (min-max %)
- [ ] Odor threshold if available (ppm or %)
- [ ] Blending notes from formulations or literature

### Tier 3: Physical/Chemical (IMPORTANT)
- [ ] logP value (for blending predictions)
- [ ] Vapor pressure (for longevity predictions)
- [ ] Solubility data (for stability)
- [ ] IFRA status (for safety compliance)

### Tier 4: Commercial (PRACTICAL)
- [ ] Price per mL from verified supplier
- [ ] Current availability (in stock)
- [ ] Minimum order quantity
- [ ] Shelf life / storage requirements

### Tier 5: Safety (MANDATORY)
- [ ] IFRA Category limits checked
- [ ] Known allergens/sensitizers flagged
- [ ] LD50 or toxicity data reviewed
- [ ] Storage hazards (flammable, oxidizer, etc.)

---

## How to Fill Gaps

### Step 1: Check TGSC
- Search http://www.thegoodscentscompany.com
- Download ingredient page
- Extract: CAS, odor, uses, regulatory

### Step 2: Verify with PubChem
- Search https://pubchem.ncbi.nlm.nih.gov
- Confirm: CAS, formula, molecular weight
- Download SDF file for structure

### Step 3: Check User Inventory
- `knowledge/chemical_inventory.md`
- Look for usage notes, quantities

### Step 4: Search Formulations
- `formulations/` directory
- Find usage rates in tested formulas
- Extract practical blending notes

### Step 5: Supplier Verification
- `perfumersworld_ABC_families/` for pricing
- Cross-check product name vs CAS

### Step 6: Document Sources
- Record ALL sources used
- Note discrepancies
- Calculate confidence score

---

## Gap Report Generation

Run `chemical_data_validator.py` to generate automated report:

```bash
python engine/chemical_data_validator.py
```

Output: List of flagged chemicals with reasons.

---

## Emergency Protocol: Unknown Chemical in Conversation

If a chemical is mentioned that's not in verified database:

1. **STOP** - Do not recommend purchase
2. **ACKNOWLEDGE** - Tell user: "I don't have verified data on [chemical]"
3. **SEARCH** - Check TGSC, PubChem, inventory immediately
4. **REPORT** - If gaps found, add to this file
5. **ALTERNATIVE** - Suggest verified alternative with similar character
6. **FLAG** - Add to `chemical_data_validator.py` flagged list

**Example Response:**
```
❌ I don't have verified data on Orivone (CAS mismatch, no scientific source confirmation).

✅ Instead, I recommend:
- DIY α-Irone 10% in Isopropyl Myristate ($0, you own both)
- Commercial α-Irone 10% Myristic Acid ($5.13, verified)

These provide authentic warm orris character with verified chemistry.
```

---

## User Feedback Loop

When user says "you don't have data on X":

1. **Apologize** - Acknowledge the gap
2. **Document** - Add X to this file immediately
3. **Fix** - Research and fill gaps within 24 hours
4. **Verify** - Update validator with findings
5. **Report** - Notify user when resolved

---

## Metrics (Track Progress)

- **Total Chemicals in Database:** [TODO: Count from inventory + TGSC]
- **Flagged Chemicals:** 1 (Orivone)
- **Resolved This Month:** 0
- **Average Resolution Time:** N/A

**Goal:** <5% of mentioned chemicals flagged, <48hr resolution time

---

## Notes

- This file is a living document
- Update EVERY time a data gap is discovered
- Review monthly for resolution progress
- User safety depends on this rigor
