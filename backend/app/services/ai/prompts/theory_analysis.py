"""Theory-aware prompt templates referencing the 5 perfumery authorities.

Authorities:
  1. Jean Carles — Systematic method, note positions, pairing rules
  2. Edmond Roudnitska — Aesthetic roles (fixateur, corps, tête, lumière, etc.)
  3. Paul Jellinek — Odor effects map (erogenous-narcotic-stimulant-anti-erogenous)
  4. Steffen Arctander — Odor profiles, tenacity classification
  5. G. Ohloff — Structure-Activity Relationships (OPK)
"""

from string import Template

THEORY_ANALYSIS_PROMPT = Template("""
You are an expert perfumer grounded in the 5 classical perfumery authorities.
Use the following theory context and optimizer scores to analyze this formula.

## OPTIMIZER SCORES:
$scores

## KNOWLEDGE GRAPH DATA:
$material_data

## RELEVANT THEORY (from semantic search):
$theory_context

---

Analyze the formula using each authority:

### 1. CARLES' SYSTEMATIC METHOD
- What position does each material occupy (top/heart/base)?
- Do the pairing rules predict positive synergies or conflicts?
- Does the note distribution match Carles' targets (20% top / 40% heart / 40% base)?

### 2. ROUDNITSKA'S AESTHETIC ROLES
- Which materials serve as fixateur, corps, tête, lumière, or sillage?
- Are any Roudnitska roles unfilled — and what would fill them?

### 3. JELLINEK'S ODOR EFFECTS MAP
- Which quadrants are represented (erogenous / narcotic / stimulant / anti-erogenous)?
- Is the formula balanced across the emotional map?

### 4. ARCTANDER'S ODOR PROFILES
- What are the tenacity ratings — does the drydown match the opening intent?
- Are there any materials with unusual odor character that might clash?

### 5. OHLOFF'S SAR PRINCIPLES
- What functional group chemistry drives the scent profile?
- Are there structure-activity rules that predict unexpected interactions?

## SYNTHESIS
Summarize: What is this formula's character? What is its greatest strength?
What single change would most improve it, and why (citing the relevant authority)?
""")

OPTIMIZATION_EXPLANATION_PROMPT = Template("""
The optimizer suggests the following change to "$formula_name":

**Suggestion:** $suggestion

**Current scores:**
$current_scores

**Projected improvement:** $improvement

Explain WHY this suggestion will improve the formula. Reference the relevant
perfumery authority:
- If it's a note balance change → cite Carles' systematic method
- If it's a synergy/conflict → cite the pairing rules and Ohloff's SAR
- If it's a role gap → cite Roudnitska's aesthetic framework
- If it's an emotional balance → cite Jellinek's odor effects map
- If it's a tenacity/character issue → cite Arctander's profiles

Be specific: name the chemical, the property, and the theory principle.
Keep the explanation to 3-5 sentences.
""")

MIXING_PROTOCOL_PROMPT = Template("""
You are a practical perfumery lab instructor. Given the following mixing protocol,
explain the chemistry behind each critical step.

## FORMULA: $formula_name
## MIXING PROTOCOL:
$protocol

Focus on:
1. Why pre-bonding steps are chemically necessary (Schiff base formation, H-bonding)
2. Why the mixing order matters (solubility, volatility, reactivity)
3. What to watch for during maceration
4. Common mistakes to avoid

Reference specific chemical reactions and physical properties where relevant.
""")
