# Recommendation Safety Protocol

**Version:** 1.0  
**Effective Date:** 2026-01-13  
**Purpose:** Prevent recommendations of chemicals without verified data

---

## The Problem

**Incident:** Recommended "Orivone" without verified data:
- CAS number mismatch (33704-61-9 = Cashmeran, not iris molecule)
- No scientific source for odor character
- No verified usage rates
- Trade name with unclear chemical identity

**Impact:** User cannot trust recommendations. App would fail at scale.

**Root Cause:** No systematic validation before recommendation.

---

## The Solution: 5-Layer Safety System

### Layer 1: Pre-Recommendation Validation

**Code:** `engine/chemical_data_validator.py`

**Rule:** Every chemical MUST pass validation before recommendation.

**Validation Checklist:**
- [ ] CAS number verified in TGSC or PubChem
- [ ] Odor description from trusted source
- [ ] Usage rate range (min-max %)
- [ ] Price from verified supplier
- [ ] At least 2 sources confirm data

**Implementation:**
```python
@require_verified_data
def recommend_chemical(name: str):
    # This decorator blocks if data insufficient
    # Only proceeds if validation passes
```

**Result:** If data missing → recommendation BLOCKED.

---

### Layer 2: Trusted Source Registry

**File:** `engine/trusted_sources.yaml`

**Purpose:** Define which sources are authoritative.

**Source Tiers:**
1. **Tier 1 (Scientific):** TGSC, PubChem, ChemSpider - 95-98% reliability
2. **Tier 2 (Suppliers):** PerfumersWorld, Sigma-Aldrich - 90-95% reliability
3. **Tier 3 (User Data):** Inventory, formulations - 80-90% reliability
4. **Tier 4 (Community):** Fragrantica, Basenotes - 60% reliability (verify required)

**Rule:** Recommendations MUST have ≥2 sources, with ≥1 from Tier 1 or 2.

**NO RECOMMENDATIONS from:**
- Chat memory alone
- Single unverified source
- Community sources without corroboration

---

### Layer 3: Knowledge Gap Tracking

**File:** `knowledge/knowledge_gaps.md`

**Purpose:** Document chemicals lacking data.

**Status Levels:**
- 🔴 **BLOCKED** - DO NOT RECOMMEND (Orivone is here)
- 🟡 **PARTIAL** - Recommend with caveats only
- 🟢 **RESOLVED** - Safe to recommend

**Update Protocol:**
- Every unknown chemical → Add to gaps file
- Research and fill gaps within 48 hours
- Move to RESOLVED when verified

**User Visibility:** When chemical flagged, tell user WHY and provide verified alternative.

---

### Layer 4: Alternative Recommendation Engine

**Rule:** If primary chemical lacks data → Suggest verified alternative with similar character.

**Example (Orivone incident):**
```
❌ Orivone: Insufficient data (CAS mismatch, no scientific source)

✅ Verified Alternatives:
1. DIY α-Irone 10% in Isopropyl Myristate
   - Cost: $0 (user owns both)
   - Character: Warm waxy orris
   - Data: α-Irone verified in TGSC, IPM standard carrier

2. α-Irone 10% Myristic Acid (commercial)
   - Cost: $5.13 for 10mL
   - Character: Waxy fatty authentic orris
   - Data: PerfumersWorld confirmed, TGSC α-Irone verified
```

**Result:** User gets recommendation, but with VERIFIED data only.

---

### Layer 5: Automated Data Audits

**Frequency:** Weekly

**Process:**
1. Scan recent conversations for mentioned chemicals
2. Check each against knowledge base
3. Flag any with <70% confidence score
4. Generate gap report
5. Research flagged chemicals
6. Update knowledge_gaps.md

**Tools:**
- `chemical_data_validator.py` (validation engine)
- `knowledge_gaps.md` (gap tracker)
- `trusted_sources.yaml` (source definitions)

---

## Implementation Workflow

### Before Recommending ANY Chemical:

```
1. User asks: "Should I buy X?"

2. Agent MUST:
   a) Query ChemicalKnowledgeBase.validate_for_recommendation(X)
   b) Check confidence score
   c) Verify ≥2 trusted sources
   d) Confirm odor character + usage rate + price exist

3. If validation PASSES (≥70% confidence):
   → Recommend with full data citation

4. If validation FAILS (<70% confidence):
   → DO NOT RECOMMEND
   → Add to knowledge_gaps.md
   → Suggest verified alternative
   → Explain why X cannot be recommended

5. Document:
   → Log decision in conversation
   → Update gaps file if new chemical
   → Flag for research if important
```

### Example Code Flow:

```python
kb = ChemicalKnowledgeBase()

# User asks about Orivone
can_recommend, record, reason = kb.validate_for_recommendation("Orivone")

if can_recommend:
    print(f"✅ Orivone: {record.odor_description}")
    print(f"   Usage: {record.usage_rate_min}-{record.usage_rate_max}%")
    print(f"   Price: ${record.price_per_ml}/mL")
else:
    print(f"❌ Cannot recommend Orivone")
    print(f"   Reason: {reason}")
    print(f"\n✅ Verified alternative: α-Irone 10% IPM (DIY, $0)")
```

---

## User Communication Protocol

### When Chemical Lacks Data:

**DO:**
- ✅ Admit knowledge gap immediately
- ✅ Explain specific missing data (CAS mismatch, no usage rate, etc.)
- ✅ Provide verified alternative with full data
- ✅ Cite sources for alternative
- ✅ Document gap for future resolution

**DON'T:**
- ❌ Recommend anyway "just to be helpful"
- ❌ Guess at usage rates or character
- ❌ Use vague descriptions without source
- ❌ Assume supplier data is accurate without verification

### Example Response Template:

```
❌ [CHEMICAL NAME]: I don't have verified data to recommend this safely.

**Missing Data:**
- [Specific gaps: CAS verification, odor description, usage rate, etc.]

**Why This Matters:**
- [Safety/effectiveness reason]

✅ **Verified Alternative:**
- **[ALTERNATIVE NAME]**
- **Character:** [Odor description] (Source: TGSC)
- **Usage:** [X-Y%] (Source: Formulations + Literature)
- **Cost:** $[Price] (Source: PerfumersWorld)
- **Why It Works:** [Technical reason]

**Next Steps:**
- I've documented this gap and will research [CHEMICAL NAME]
- Once verified data is found, I'll update the knowledge base
- Would you like to proceed with [ALTERNATIVE] or wait for [CHEMICAL] verification?
```

---

## Testing & Validation

### Test Cases (Run Before Deployment):

```python
# Test 1: Block Orivone
assert kb.validate_for_recommendation("Orivone")[0] == False

# Test 2: Allow verified chemical (e.g., Linalool)
assert kb.validate_for_recommendation("Linalool")[0] == True

# Test 3: Require multiple sources
record = kb.lookup_chemical("Alpha-Ionone")
assert len(record.data_sources) >= 2

# Test 4: Flag unknown chemical
kb.validate_for_recommendation("Mystery Chemical")
assert "mystery chemical" in kb.flagged_chemicals
```

---

## Continuous Improvement

### Monthly Review:
1. **Audit Recommendations:** Review all chemicals recommended last 30 days
2. **Verify Sources:** Ensure ≥2 sources for each
3. **Update Gaps:** Research and resolve flagged chemicals
4. **User Feedback:** Check for complaints about bad recommendations
5. **Update Validator:** Add new trust rules as patterns emerge

### Metrics to Track:
- **Recommendation Accuracy:** % of recommended chemicals with verified data (Goal: 100%)
- **Gap Resolution Time:** Hours to research flagged chemical (Goal: <48hr)
- **User Satisfaction:** Complaints about bad recommendations (Goal: 0)
- **Knowledge Base Growth:** Chemicals added to verified database per month

---

## Escalation Protocol

### If User Reports Bad Recommendation:

1. **Immediate:**
   - Apologize
   - Flag chemical in `knowledge_gaps.md`
   - Add to `chemical_data_validator.py` BLOCKED list

2. **Within 24 Hours:**
   - Research chemical from Tier 1 sources
   - Document findings in gaps file
   - If verified → Move to RESOLVED
   - If unverifiable → Keep BLOCKED, document why

3. **Within 48 Hours:**
   - Report back to user with findings
   - Provide verified alternative
   - Update recommendation protocol if systemic issue

4. **Prevent Recurrence:**
   - Add test case to validator
   - Update documentation
   - Review similar chemicals for same issue

---

## Success Criteria

**System is working when:**
1. ✅ Zero recommendations without ≥70% confidence score
2. ✅ All recommendations cite ≥2 trusted sources
3. ✅ Knowledge gaps file updated within 1 hour of discovery
4. ✅ Flagged chemicals resolved within 48 hours
5. ✅ User complaints about bad recommendations = 0

**User trust restored when:**
1. ✅ User says "I trust your recommendations"
2. ✅ User builds formulas from recommended materials without issues
3. ✅ User refers others to the app
4. ✅ No more "you don't have data on X" surprises

---

## Commitment to User

**From this point forward:**

1. **Every recommendation will be verified** against the knowledge base
2. **Every data gap will be documented** immediately when discovered
3. **Every flagged chemical will have a verified alternative** suggested
4. **Every month will include an audit** of recommendation quality
5. **Zero tolerance** for recommendations without verified data

**User safety and trust are the top priority.**

---

**Signed:** Knowledge Curator Agent  
**Date:** 2026-01-13  
**Next Review:** 2026-02-13
