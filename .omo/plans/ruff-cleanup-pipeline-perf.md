# Ruff Cleanup + Pipeline Performance Fix

## Summary
Fix remaining ruff lint errors, strip `future_modules/__init__.py` to remove 390ms of eager imports, and document delegation constraints.  

**Current state**: Ruff 1,792 → 83 errors (95.4% fixed). Pipeline import reduced ~400ms.

---

## TODOs

- [x] 1. Strip `future_modules/__init__.py` to `_shared_types` only — save ~390ms import time
- [x] 2. Fix remaining ruff N8xx naming violations (20 remaining: 14 N806 + 5 N803 + 1 N815)
- [x] 3. Fix remaining ruff F401 unused imports in engine/ scripts/ tests/ (29 errors)
- [x] 4. Fix remaining ruff E402/E701/E702/E722/E741/I001 in engine/ scripts/ tests/ (34 errors)
- [x] 5. Fix root scratch script ruff errors — validate/verify scripts (144 errors)
- [x] 6. Final verification: ruff clean AND pipeline import time reduced

---

## Acceptance Criteria

### T1: `future_modules/__init__.py` stripped
- File reduced from 1,004 lines to ~85 lines (only `_shared_types` imports + docstring)
- `python -c "from future_modules._shared_types import FragranceFamily; print('OK')"` passes
- `python -c "from future_modules.accord_library import get_accord; print('OK')"` passes (direct submodule import still works)
- Pipeline import time reduced: `future_modules` cumulative time drops from ~389ms to <50ms

### T2: N8xx naming — 0 errors
- `ruff check engine/ --select=N803,N806,N815,N811` = clean
- Standard scientific notation (Re, Sc, Sh in sniff.py): `# noqa` comments acceptable

### T3: F401 unused imports — 0 errors  
- `ruff check engine/ scripts/ tests/ --select=F401` = clean

### T4: Misc ruff errors — 0 errors
- `ruff check engine/ scripts/ tests/ --select=E402,E701,E702,E722,E741,I001` = clean

### T5: Root scratch scripts — 0 errors
- `ruff check validate_*.py verify_*.py` = clean

### T6: Final verification
- `ruff check engine/ scripts/ tests/` = clean (0 errors)
- Pipeline import time <1.7s (from current 2.06s)

---

## Dependency Graph
```
T1 (independent) ─┐
T2 (independent) ─┤
T3 (independent) ─┼──► T6 (all must complete first)
T4 (independent) ─┤
T5 (independent) ─┘
```

All tasks are independent — fire in parallel.

---

## Success Criteria
```bash
# After all fixes:
ruff check engine/ scripts/ tests/
# Expected: All checks passed!

python -X importtime -c "from scripts.formula_release_gate import parse_formula_markdown; print('OK')" 2>&1 | Select-String "future_modules"
# Expected: future_modules cumulative < 50000 (50ms)

python -c "import engine.ingredient_intelligence; print('PROFILES:', len(engine.ingredient_intelligence._PROFILES))"
# Expected: PROFILES: 255 (data integrity)
```

---

## Notepad
- Learnings: `.omo/notepads/ruff-cleanup-pipeline-perf/learnings.md`
- Issues: `.omo/notepads/ruff-cleanup-pipeline-perf/issues.md`
