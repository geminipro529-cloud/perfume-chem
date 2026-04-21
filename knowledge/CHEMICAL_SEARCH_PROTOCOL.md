# Chemical Search Protocol

## MANDATORY Search Sequence for Unknown Chemicals

**USE THIS EXACT SEQUENCE EVERY TIME YOU ENCOUNTER AN UNKNOWN CHEMICAL**

### Step 1: Multi-Site Parallel Search (ALWAYS DO THIS FIRST)

When you don't have data on a chemical, **IMMEDIATELY** fetch from these sites in parallel:

```python
# REQUIRED URLs to check for ANY unknown chemical:
urls = [
    f"https://olfactorian.com/materials/{chemical_name_lowercase}",
    f"https://www.perfumersworld.com/view.php?pro_id=XXXXX",  # Need catalog ID
    f"https://pubchem.ncbi.nlm.nih.gov/compound/{cas_or_name}",
    f"https://www.thegoodscentscompany.com/data/rw{cas_no_hyphens}.html",
    f"https://www.scentree.co/en/{chemical_name}.html"
]
```

### Step 2: Execute Parallel Fetch

**DO NOT search one at a time. Use fetch_webpage with ALL URLs simultaneously:**

```
fetch_webpage(
    query="[Chemical] CAS FEMA odor description suppliers",
    urls=[
        "https://olfactorian.com/materials/[chemical]",
        "https://pubchem.ncbi.nlm.nih.gov/compound/[CAS]",
        "https://www.perfumersworld.com/view.php?pro_id=[ID]",
        "https://www.thegoodscentscompany.com/data/rw[CAS].html",
        "https://www.scentree.co/en/[Chemical].html"
    ]
)
```

### Step 3: Data Extraction Priority

1. **Olfactorian** - Best for:
   - Odor character descriptions
   - Usage patterns in formulas
   - Functional profiles (blend, build, bridge, etc.)
   - Typical dosage ranges

2. **PubChem** - Best for:
   - Chemical name (IUPAC)
   - CAS number verification
   - Molecular formula
   - Synonyms and trade names
   - Regulatory data

3. **TGSC (The Good Scents Company)** - Best for:
   - Supplier listings
   - Purity grades
   - Alternative trade names

4. **PerfumersWorld** - Best for:
   - Pricing ($X/mL)
   - NEAT vs diluted options
   - Odor Impact ratings
   - Application suitability

5. **Scentree** - Additional verification

### Step 4: URL Pattern Recognition

**TGSC URL Patterns:**
- Format: `https://www.thegoodscentscompany.com/data/[prefix][cas].html`
- Prefix examples:
  - `rw` = Most common (Parmavert: rw1001971)
  - `ir` = Iris/orris materials (attempted but failed)
  - `or` = Orris materials (attempted but failed)
- **DO NOT GUESS** - Try multiple patterns if needed

**PerfumersWorld Product ID:**
- Format: `https://www.perfumersworld.com/view.php?pro_id=XXXXX`
- Examples:
  - Parmavert: 4IG05175
  - Pattern: `[digit][letter]{2}[digits]`

**Olfactorian:**
- Format: `https://olfactorian.com/materials/{lowercase-name}`
- Always use lowercase, hyphenated if multi-word
- Example: `irotyl`, `ultralia`, `orivone`

**PubChem:**
- Format: `https://pubchem.ncbi.nlm.nih.gov/compound/{CAS-or-name}`
- Use CAS without hyphens OR chemical name

## CRITICAL LESSONS FROM PARMAVERT/IROTYL/ULTRALIA/ORIVONE

### WHAT WENT WRONG:
1. ❌ Searched local workspace first (wasted time on zero results)
2. ❌ Tried TGSC search page (returned "no results" - NOT USEFUL)
3. ❌ Tried Google (BLOCKED by JavaScript)
4. ❌ Tried Context7 (WRONG DOMAIN - not for chemistry)
5. ❌ Did NOT try direct URLs until user provided Parmavert link

### WHAT WORKED:
1. ✅ Direct URL fetches (Olfactorian, PubChem, TGSC data pages)
2. ✅ Parallel fetches (all 3 chemicals at once)
3. ✅ Multiple URL patterns (rw prefix for TGSC)

## Examples of Successful Searches

### Irotyl (Ethyl 2-ethylhexanoate)

**URLs that worked:**
- ✅ `https://olfactorian.com/materials/irotyl`
- ✅ `https://pubchem.ncbi.nlm.nih.gov/compound/2983-37-1`

**Data found:**
- CAS: 2983-37-1
- FEMA: 4345
- Odor: Fresh orris fruity herbal cumin
- Suppliers: Confirmed via PubChem (FEMA listed)

### Ultralia (Methylionone)

**URLs that worked:**
- ✅ `https://olfactorian.com/materials/ultralia`
- ✅ `https://pubchem.ncbi.nlm.nih.gov/compound/1335-46-2`

**Data found:**
- CAS: 1335-46-2 (also 127-42-4, 7779-30-8)
- FEMA: 2711
- Odor: Orris violet powdery woody
- Trade names: Iralia (Firmenich), Isoraldeine (Givaudan)
- Usage: 0.5-31.3% in formulas

### Orivone (4-tert-Pentylcyclohexanone)

**URLs that worked:**
- ✅ `https://olfactorian.com/materials/orivone`
- ✅ `https://pubchem.ncbi.nlm.nih.gov/compound/16587-71-6`

**Data found:**
- CAS: 16587-71-6
- Odor: Woody dry orris earthy camphor
- Trade name: Orivone (IFF)
- IFRA restrictions: YES (category limits)
- Usage: 0.4-15.6% in formulas

## NEVER DO THESE AGAIN:

1. **DON'T** search local workspace first for unknown chemicals
   - Reason: Waste of time, local data is incomplete
   
2. **DON'T** try TGSC search.php pages
   - Reason: Returns "Please enter a search" for most chemicals
   
3. **DON'T** try Google searches
   - Reason: BLOCKED by JavaScript challenges
   
4. **DON'T** try Context7 for chemistry
   - Reason: Wrong domain (code libraries, not chemical databases)
   
5. **DON'T** search sequentially
   - Reason: Slow, inefficient - use parallel fetches

## ALWAYS DO THESE:

1. **DO** fetch Olfactorian + PubChem + TGSC simultaneously
2. **DO** use direct data URLs, not search pages
3. **DO** try multiple TGSC URL prefixes (rw, ir, or, etc.)
4. **DO** extract CAS, odor, suppliers, trade names
5. **DO** verify data across multiple sources

## Implementation Checklist

When user asks about an unknown chemical:

- [ ] Extract chemical name from query
- [ ] Construct 5 URLs (Olfactorian, PubChem, TGSC, PerfumersWorld, Scentree)
- [ ] Execute single fetch_webpage with all URLs
- [ ] Parse results for: CAS, chemical name, odor, suppliers, pricing
- [ ] Cross-reference data between sources
- [ ] Report consolidated findings
- [ ] Update local knowledge base if needed

## Response Template

```markdown
## [Chemical Name]

**VERIFIED DATA:**
- **Chemical Name:** [IUPAC name from PubChem]
- **CAS:** [number from PubChem]
- **Trade Names:** [from Olfactorian/TGSC]
- **Odor:** [from Olfactorian + TGSC descriptions]
- **Molecular Formula:** [from PubChem]
- **Suppliers:** [from TGSC/PubChem]
- **Pricing:** [from PerfumersWorld if available]
- **Usage Levels:** [from Olfactorian formula data]
- **Regulatory:** [FEMA/IFRA from PubChem]

**Sources:**
- [Olfactorian](URL)
- [PubChem](URL)
- [TGSC](URL)
- [PerfumersWorld](URL)

**Confidence:** 95%+ (verified across multiple authoritative sources)
```

## FINAL RULE:

**IF YOU DON'T HAVE DATA ON A CHEMICAL → IMMEDIATELY FETCH FROM OLFACTORIAN + PUBCHEM + TGSC IN PARALLEL**

No exceptions. No local searching first. No Google. No Context7. Go straight to the authoritative chemical databases.
