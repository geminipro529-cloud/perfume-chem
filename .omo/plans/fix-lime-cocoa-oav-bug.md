# Fix: Lime & Cocoa OAV=0 Bug — Unmodeled Natural Fallback

**Status:** PLANNED  
**Date:** 2026-07-18  
**Session:** ULTRAWORK — cost-benefit pipeline fix  

---

## Diagnosis

### Root Cause
`engine/pipeline/formula_state.py` lines 256-257 and 661-662: when a natural mixture (Lime Distilled EO, Cocoa Absolute, Cocoa CO2 Absolute) is NOT in the composite decomposition model, the pipeline sets OAV to `None` (displayed as 0.0) instead of falling back to monomolecular Raoult-law OAV.

```
composite = composite_oav(name, ...)
requires_composite = is_opaque_preblend or _is_natural_mixture(name)
if composite is not None:
    oav_value = composite
elif requires_composite:
    oav_value = None   ← BUG: unmodeled naturals get OAV=0
```

### Impact
| Material | VP Pa | Vapor ppm | ODT ppb | Should-be OAV | Pipeline says |
|----------|-------|-----------|---------|---------------|----------------|
| Lime Distilled EO | 200 | 453 | 8 | ~56,625 | **0.0** |
| Cocoa Absolute | 0.01 | 0.0014 | 5 | ~0.28 | **0.0** |
| Cocoa CO2 Absolute | 0.01 | 0.0003 | 3 | ~0.10 | **0.0** |

### Why This Matters
- Lime is the ONLY top note — OAV=0 means the opening appears to have nothing. Actual perception: massive lime burst.
- Cocoa at VP 0.01 Pa genuinely IS sub-threshold (~OAV 0.3) but the pipeline can't even tell perfumers it's close — it shows 0.
- Future formulas with any unmodeled natural will silently zero out those materials.

---

## Fix Plan

### Task 1: Fix formula_state.py — two locations (2 lines each, identical pattern)

**File:** `engine/pipeline/formula_state.py`

**Location 1 — line 252-257** (primary material loop):
```python
# BEFORE:
            composite = composite_oav(m.canonical_name, active_g, total_moles)
            requires_composite = m.is_opaque_preblend or _is_natural_mixture(m.name)
            if composite is not None:
                oav_value = composite
            elif requires_composite:
                oav_value = None

# AFTER:
            composite = composite_oav(m.canonical_name, active_g, total_moles)
            requires_composite = m.is_opaque_preblend or _is_natural_mixture(m.name)
            if composite is not None:
                oav_value = composite  # use accurate multi-constituent model
            # Fall through: unmodeled naturals keep their monomolecular OAV.
            # Composite decomposition is a better model, but monomolecular
            # (Raoult-law) is a better estimate than zero.
```

**Location 2 — line 656-662** (secondary material loop):
```python
# BEFORE:
        composite = composite_oav(canonical, active_g, total_moles)
        is_opaque_preblend = _is_opaque_preblend(name, profile)
        requires_composite = is_opaque_preblend or _is_natural_mixture(name)
        if composite is not None:
            oav_value = composite
        elif requires_composite:
            oav_value = None

# AFTER:
        composite = composite_oav(canonical, active_g, total_moles)
        is_opaque_preblend = _is_opaque_preblend(name, profile)
        requires_composite = is_opaque_preblend or _is_natural_mixture(name)
        if composite is not None:
            oav_value = composite  # use accurate multi-constituent model
        # Fall through: unmodeled naturals keep their monomolecular OAV.
```

**No other changes needed.** `_oav_model_source()` at line 401 already correctly labels the source as `"heuristic:monomolecular_headspace"` for unmodeled naturals.

### Task 2: Verify — re-gate formula

```powershell
python scripts/formula_release_gate.py \
    --formula-file formulas/Osmanthus_Dark_Crystal_30mL_EdP.md \
    --expected-concentrate-ul 4220 \
    --brief generic \
    --json > output/osmanthus_dark_crystal_gate.json

python scripts/format_pipeline_analysis.py --input output/osmanthus_dark_crystal_gate.json
```

**Expected after fix:**
- Lime Distilled EO: OAV ~56,000 (massive top note — correct)
- Cocoa CO2 Absolute: OAV ~0.1 (genuinely sub-threshold — correct, VP wall)
- Clearwood: OAV unchanged (~0.2)

### Task 3: Fix format_pipeline_analysis.py crash

**File:** `scripts/format_pipeline_analysis.py` line 37

`oav_label()` accepts `None` OAV which causes `TypeError: '>=' not supported between instances of 'NoneType' and 'int'`.

Fix: guard against None at the top of `oav_label()`:
```python
def oav_label(oav: float | None) -> str:
    if oav is None:
        return "?"
    if oav >= 1000:
        return "massive"
    # ... rest unchanged
```

Also at line 278, handle `m.get('oav')` returning None:
```python
tdesc = " + ".join(f"{m['name']}({oav_label(m.get('oav') or 0)})" for m in top_m[:3])
```

### Task 4: Optional — address Cocoa formulation reality

Even after the fix, Cocoa CO2 at VP 0.01 Pa gives OAV ~0.1. The VP wall is absolute (Registry F3). Options for the user to consider:
1. Accept cocoa as skin-only texture (no headspace contribution)
2. Find higher-VP chocolate material (none in current inventory — Paradisamide VP 0.002 Pa is worse)
3. Boost cocoa dose massively (won't help — VP wall means diminishing returns)

### Task 5: Optional — Hedione reduction

Hedione at 15.4% of concentrate (>12% ceiling, Registry F2). OAV 8924 dominates Osmanthus 1202 by 7.4x.

Recommendation: reduce Hedione from 650 µL → 450 µL. This:
- Drops to ~10.7% of concentrate (within ceiling)
- OAV drops to ~6200
- Osmanthus:Hedione ratio improves to ~1:5x
- Add 200 µL of something else to maintain concentration (e.g., more Osmanthus or a bridging material)

---

## Execution Order
1. Fix formula_state.py (2 edits)
2. Fix format_pipeline_analysis.py (2 edits)
3. Re-run pipeline gate
4. Present corrected OAV table
5. Discuss formulation fixes (Hedione, cocoa, opening)

## Verification
- `pytest tests/test_pipeline_gates.py -k test_gate_blocks` must pass
- Lime OAV must be > 10,000 (non-zero)
- Cocoa OAV must be non-zero (even if < 1)
- format_pipeline_analysis.py must not crash
