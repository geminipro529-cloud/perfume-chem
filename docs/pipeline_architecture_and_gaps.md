# Pipeline Architecture Analysis & Gap Assessment
**Generated:** 2026-05-21  
**Scope:** Full pipeline audit from `scripts/formula_release_gate.py` through `engine/` modules

---

> **⚠️ RULE: Optimize for the name, not just the numbers.**  
> When optimizing through this pipeline, the target is always the **name / concept / original brief** of the perfume, not the numerical scores. Gates and optimizers are tools — the formula name is the north star.

## 2026-07-19 Run Evidence Contract

The release path now separates four independent authorities. A result may be
useful as a creative diagnostic while still being forbidden from authorizing a
dose, safety decision, named-reference ratio, or current persisted analysis.

| Authority | Required evidence | Failure policy |
|---|---|---|
| Stock | One owned inventory identity per row; matching fraction, physical basis, and carrier | Hard FAIL |
| Quantitative | Complete mass chain for exact concentrate ppm w/w; finished-product mass chain for commercial release | Hard FAIL when a quantitative or commercial claim requests it; otherwise explicit modeled WARN |
| Claim | Explicit claim mode, versioned reference contract, and supported scope | Hard FAIL |
| Artifact | Formula-definition, config, inventory, scientific-input, pipeline-source, and analysis hashes | STALE/TAMPERED hard failure; legacy reports are unbound and never current |

The executable flow is:

```text
formula source
  -> strip generated analysis before parsing
  -> resolve live inventory stock identity
  -> build exact-or-explicitly-modeled ppm/ODT/OAV state
  -> enforce named-reference evidence scope
  -> run hard truth gates and advisory aesthetic gates
  -> render analysis
  -> atomically persist + immediately re-read and verify the bound artifact
```

Key invariants:

1. OAV remains `MODELED_HEURISTIC`; it is never a sensory-likeness percentage.
2. Pairwise Carles diagnostics use active mass ppm, never OAV ratios.
3. Single-material share uses active mass, never raw diluted-stock volume.
4. A generic brief cannot be inferred as chypre, fougere, or another named family from layer dominance.
5. Generated analysis can never become formula input. Legacy headings and the new sentinel block are removed before table parsing and formula hashing.
6. Optimizer candidates inherit live inventory dilutions before gating; missing or ambiguous stocks remain blocked.
7. Natural mixtures without composite GC-O decomposition remain hard failures.

Named-reference metadata is explicit:

```markdown
**Claim mode:** named_reference
**Reference contract:** montblanc_explorer_official_notes_v1
**Reference scope:** architecture
```

The current Explorer and Aventus contracts are based on official note
architectures ([Montblanc](https://www.montblanc.com/en-ph/fragrances/collection/explorer),
[Creed](https://creedboutique.com/products/aventus)). They authorize architecture
checks only. They do not contain formula ratios, GC-MS composition, or sensory
equivalence evidence, so `quantitative_similarity` and `sensory_similarity`
remain blocked.

Persisted evidence uses deterministic JSON hashing aligned with the repository
subset of [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), provenance
entities and derivations modeled after [W3C PROV-DM](https://www.w3.org/TR/prov-dm/),
and an explicit unbroken input chain consistent with
[NIST metrological traceability](https://www.nist.gov/metrology/metrological-traceability).
The authority boundary also reflects the published limitation that OAV alone
does not reliably identify every odor-impact compound
([Audouin et al., 2001](https://experts.umn.edu/en/publications/limitations-in-the-use-of-odor-activity-values-to-determine-impor/)).

Verification commands:

```powershell
python scripts/pipeline_audit.py artifact-verify --json
python scripts/pipeline_audit.py project-verify --quick --json
python scripts/pipeline_audit.py project-verify --json
```

This contract prevents the documented data/provenance failure classes. It does
not promise that a mathematically valid perfume will smell good; sensory quality
and likeness still require blinded smelling, reference comparison, and wear data.

## 1. CURRENT ARCHITECTURE

### Entry Point
```
scripts/formula_release_gate.py
  ├── parse_formula_markdown()       → flexible table/percent/uL parser
  ├── analyze_oav_authority()        → OAV surface (14/19 perceptible, vapor ppm, time windows)
  ├── FormulaScorer.score()          → 10 proprietary axes + per-axis synergy boosts
  │   └── synergy pre-multiplier     → 5 axes boosted (sillage/depth/texture/complexity)
  ├── gate_formula()                 → 23 release gates
  └── industry_10                    → 7 axes + industry_total
```

### Scoring Output (per formula)

| Group | Axes | Source |
|-------|------|--------|
| **Industry 10** | impact, tenacity, diffusion, bloom, lift, character, balance | OAV authority + time windows |
| **Proprietary** | longevity, sillage, texture, stacking_depth, skin_perf, hedonic, clarity, photorealism, luxury | FormulaScorer |
| **Synergy boosts** | sillage +20%, texture +20%, stacking +20%, photorealism +20% | Pairing rules × axis matching |
| **Gates** | 23 gates (PASS/WARN/FAIL) | gate_formula() |

### Data Sources Used
- `inventory.txt` → material availability
- `engine/odor_thresholds.py` → 270+ ODT values (41 corrected from master table)
- `engine/ingredient_intelligence.py` → 200+ profiles (note, role, MW, VP, logP, character)
- `data/materials/*.yaml` → 26 files, 200+ entries (physical properties)
- `data/knowledge_graph/pairing_rules.json` → 2,388 rules with axis + magnitude
- `data/knowledge_graph/synergy_matrix.json` → 58 documented synergy rules
- `engine/knowledge/pyramid_targets.py` → family OAV targets per tier

---

## 2. GAP ANALYSIS

### Gap 1: No Natural Language Diagnosis
**Severity: High** — The pipeline scores but doesn't tell the perfumer what to fix.

A perfumer reading the output sees `tenacity=9.8` but has to manually figure out:
- "Which material should I swap?"
- "How much should I change?"
- "What's the root cause vs symptom?"

**Fix:** Formula Diagnosis Engine — reads scores + gates + OAV table, produces prioritized intervention list with specific dose/material recommendations.

### Gap 2: No Intervention Simulation
**Severity: Medium** — The pipeline scores the current formula but can't answer "what if I change X?"

A perfumer wants to know: "If I reduce Grapefruit by 40% and boost Kephalis to 12%, does tenacity go from 9.8 to 40?"

**Fix:** What-if simulator — takes a delta formula and re-runs OAV/scoring, returns predicted scores.

### Gap 3: No Temporal Coherence Score
**Severity: Medium** — The `bloom` score (40.0) measures unique leaders but not smoothness of evolution.

A formula that jumps from top to base with no heart transition has the same bloom score as one that smoothly transitions. The rate of note_distribution change across windows is not scored.

**Fix:** Temporal coherence module — measures smoothness of OAV envelope transition across 5 windows.

### Gap 4: No Data Quality Score
**Severity: Low** — The `confidence_minimum` gate PASS/FAIL but no continuous 0-100 data quality score.

Materials with LOW confidence ODT values (DBCA=3.0 UNVERIFIED, orris ftec=0.2 UNVERIFIED) contribute to scores as if their data is certain. The pipeline should discount scores based on data confidence.

**Fix:** Data quality modifier — each material's contribution to every score is multiplied by its ODT confidence factor (HIGH=1.0, MEDIUM=0.8, LOW=0.5, UNVERIFIED=0.3).

### Gap 5: No Pairing Rule Quality Validation
**Severity: Medium** — The 5 agents found 1,696 pairs, but there's no validation that they're real.

A pair like `Clearwood + Azarbre` (both VP < 0.01 Pa) is chemically impossible to be synergistic — neither can volatilize enough to interact in headspace. Yet it's scored as a valid pair.

**Fix:** VP-aware pair validation — reject pairs where both materials have VP < 0.1 Pa (can't co-volatilize).

### Gap 6: No Family-Specific Calibration
**Severity: Low** — The industry_10 scores use the same scale for all families.

Impact=56.9 means different things for a citrus cologne vs an amber oriental. A citrus SHOULD have high impact and low tenacity. The industry scores should be calibrated per-family.

**Fix:** Family normalization — each industry score is normalized relative to the family's expected range (from pyramid_targets.py).

---

## 3. IMPLEMENTATION STATUS

### Phase 1: Formula Diagnosis Engine ✅
`scripts/formula_diagnosis.py` — integrated into `formula_release_gate.py`

Produces prioritized interventions across 6 modules:
- `diagnose_industry()` — checks all 8 industry scores for structural issues
- `diagnose_oav_table()` — flags dormant character/radiance materials
- `diagnose_vp_pairs()` — flags low-VP materials that can't interact
- `diagnose_data_quality()` — flags missing ODT data
- `diagnose_gates()` — surfaces FAIL/WARN gates
- `diagnose_synergy()` — flags unmatched synergy axes

### Phase 2: VP-Aware Pair Validation ✅
Diagnosis module `diagnose_vp_pairs()` — flags pairs where both materials have VP < 0.1 Pa and OAV < 1.0. Prevents chemically impossible pairs from being considered synergistic.

### Phase 3: Temporal Coherence ✅
New industry score `temporal_coherence` (Vetiver Moderne = 91.4) — measures smoothness of OAV envelope transition across 5 time windows. Low coefficient of variation = smooth evolution.

### Phase 4: Data Quality Modifier ✅
New industry score `data_quality` (Vetiver Moderne = 100.0) — penalizes formulas using UNVERIFIED ODT materials. Each UNVERIFIED material deducts 8%.

### Phase 5: Family Normalization ✅
Industry scores are now normalized per family (7 axes × 3 families = 21 normalized variants). Normalized scores tell the perfumer how the formula performs relative to family expectations.

## Final Diagnosis: Vetiver Moderne

### CRITICAL (must fix)
| # | Issue | Fix |
|---|-------|-----|
| 1 | Tenacity=9.8 — no perceptible base | Swap Romandolide (OAV=0.06) for Habanolide or boost to 15% |
| 2 | Lift=93.5 — top notes dominate 94% | Reduce Grapefruit by 40%, redistribute to heart |

### HIGH (should fix)
| # | Issue | Fix |
|---|-------|-----|
| 3 | OAV targets off for family woody | Reduce Iso E Super (OAV=3039, target 40-150) |
| 4 | Family archetype constraints | Adjust vetiver_star_axis and moss_structure |

### MEDIUM (consider)
| # | Issue | Fix |
|---|-------|-----|
| 5 | Bloom=40 — only 2 leaders | Add mid-volatility bridge material |
| 6 | 5 dormant materials (VP<0.1) | Swap one for higher-VP analogue |

### LOW (note)
| # | Issue | Fix |
|---|-------|-----|
| 7-13 | HSP coverage, IFRA limits, synergies | Data improvements, not formula changes |

---

## 4. MODULE INVENTORY

### Phase 1: Formula Diagnosis Engine (Priority: HIGH)
```python
class FormulaDiagnosis:
    """Reads pipeline output, produces prioritized interventions."""
    
    def diagnose(industry_scores, gates, oav_table, synergy_info):
        issues = []
        # Check each low industry score
        if scores.tenacity < 30:
            # Find dormant base materials
            dormant = [m for m in oav_table if m.note == 'base' and m.oav < 1]
            issues.append({
                'severity': 'HIGH',
                'axis': 'tenacity',
                'message': f'Base perceptibility critically low ({scores.tenacity})',
                'cause': f'{len(dormant)} dormant base materials',
                'suggestion': f'Swap {dormant[0].name} (OAV={dormant[0].oav}) for higher-VP alternative'
            })
        if scores.lift > 80:
            top = [m for m in oav_table if m.note == 'top' and m.oav > 1000]
            issues.append({
                'severity': 'HIGH',
                'axis': 'lift',
                'message': f'Top notes dominate ({scores.lift}%)',
                'cause': f'{len(top)} ultra-potent top materials',
                'suggestion': f'Reduce highest-OAV top note by 30-50%'
            })
        # Sort by severity
        return sorted(issues, key=lambda x: -severity_rank(x.severity))
```

### Phase 2: VP-Aware Pair Validation (Priority: MEDIUM)
```python
def validate_pair_chemistry(rule):
    """Reject pairs that are chemically impossible."""
    vp_a = get_profile(rule.material_a).vp
    vp_b = get_profile(rule.material_b).vp
    if vp_a and vp_b and vp_a < 0.1 and vp_b < 0.1:
        return False  # Neither can volatilize
    return True
```

### Phase 3: Temporal Coherence (Priority: MEDIUM)
```python
def score_temporal_coherence(time_windows):
    """Measure smoothness of OAV envelope transition."""
    rates = []
    for i in range(len(time_windows) - 1):
        w1 = time_windows[i].family_envelope
        w2 = time_windows[i+1].family_envelope
        # Rate of change between windows
        delta = sum(abs(w2.get(k,0) - w1.get(k,0)) for k in set(w1) | set(w2))
        rates.append(delta)
    # Coefficient of variation of rates = coherence
    mean = sum(rates) / len(rates)
    std = (sum((r - mean)**2 for r in rates) / len(rates))**0.5
    coherence = 100 - min(100, std / max(mean, 0.01) * 20)
    return coherence
```

### Phase 4: Family-Normalized Industry Scores (Priority: LOW)
```python
def normalize_industry_scores(raw_scores, family):
    """Normalize scores relative to family expectations."""
    range_map = {
        'citrus_woody': {'impact': (40, 90), 'tenacity': (20, 60)},
        'amber_oriental': {'impact': (20, 60), 'tenacity': (50, 95)},
    }
    returns = family in range_map
    if not returns:
        return raw_scores
    ranges = range_map[family]
    for axis in raw_scores:
        lo, hi = ranges.get(axis, (0, 100))
        raw_scores[axis] = (raw_scores[axis] - lo) / (hi - lo) * 100
    return raw_scores
```

---

## 4. PIPELINE FLOW (AFTER PHASE 1)

```
scripts/formula_release_gate.py
  ├── parse_formula_markdown()
  ├── analyze_oav_authority()         → OAV table, time windows, vapor ppm
  ├── FormulaScorer.score()           → 10 proprietary axes + synergy boosts
  ├── gate_formula()                  → 23 gates
  ├── industry_10()                   → 7 axes + industry_total (NEW: family-normalized)
  ├── temporal_coherence()            → NEW: smoothness score
  ├── vp_validate_pairs()            → NEW: reject impossible pairs
  └── FormulaDiagnosis.diagnose()     → NEW: prioritized interventions
      Output: [
        {"severity":"HIGH", "axis":"tenacity", "message":"...", "suggestion":"..."},
        {"severity":"MEDIUM", "axis":"lift", "message":"...", "suggestion":"..."},
      ]
```

---

## 5. DATA QUALITY GAPS

| Material | ODT Confidence | Impact if Wrong |
|----------|---------------|-----------------|
| DBCA | UNVERIFIED (3.0 ppb) | All formulas using DBCA have wrong OAV |
| PEDMC | UNVERIFIED (3.0 ppb) | Same |
| Orris F-TEC | UNVERIFIED (0.2 ppb) | Iris formulas OAV inflated |
| I-IRIS F-TEC | UNVERIFIED (0.2 ppb) | Same |
| Blood Orange Sicilian | LOW (8.0 ppb) | Citrus formulas slightly off |
| Cedrat FCF Sicilian | LOW (8.0 ppb) | Same |
| Rhodinol ex Citronella | PEER_EST (0.3 ppb) | Rose formulas |
| ~40 newly added materials | UNVERIFIED/LOW | Varies |

**Fix:** Add `confidence` factor to each score contribution. LOW = 50% weight, UNVERIFIED = 30%.

---

## 6. MODULE INVENTORY

| Module | Lines | Functions | Status |
|--------|-------|-----------|--------|
| `scripts/formula_release_gate.py` | 295 | 3 | ✅ Unified entry point |
| `engine/pipeline/gates.py` | 1026 | 36 | ✅ 23 gates |
| `engine/pipeline/oav_authority.py` | 523 | 24 | ✅ OAV surface |
| `engine/pipeline/formula_state.py` | 449 | 16 | ✅ Modified Raoult |
| `engine/optimizer/scoring.py` | 2389 | 28 | ⚠️ Too large, needs split |
| `engine/odor_thresholds.py` | 1182 | 6 | ⚠️ 270+ entries, 41 corrected |
| `data/knowledge_graph/pairing_rules.json` | 2388 | — | ✅ Axis + magnitude tagged |
| `engine/ingredient_intelligence.py` | 2246 | — | ⚠️ 200+ profiles, needs refactor |
| `scripts/mcp_call.py` | 120 | — | ✅ CLI for all MCP servers |
| `scripts/sequential_thinking.py` | 42 | — | ✅ Problem decomposition CLI |
