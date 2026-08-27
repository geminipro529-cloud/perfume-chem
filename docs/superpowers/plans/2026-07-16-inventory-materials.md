# Inventory Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize four received materials across live inventory, canonical chemistry data, profile/ODT logic, and composite OAV handling, then publish the verified branch to the already-public GitHub repository.

**Architecture:** `inventory.txt` remains the stock authority; `engine.inventory_parser` exposes availability and dilution; A-Z YAML records hold identity and provenance; `engine.ingredient_intelligence` and `engine.odor_thresholds` supply runtime properties; `engine.pipeline.natural_absolute_decomposition` supplies mixture-aware OAV. Regression tests exercise the real loaders and calculators so these paths cannot silently diverge.

**Tech Stack:** Python 3, pytest, PyYAML, repository data-spine dataclasses, Git/GitHub CLI.

---

## File Map

- Create `tests/test_inventory_material_additions.py`: end-to-end contracts for stock, identity, profile, ODT, aliases, and natural-mixture OAV.
- Modify `inventory.txt`: record the user's stock facts and refresh inventory totals.
- Modify `engine/inventory_parser.py`: classify `DEPLETED` as unavailable.
- Modify `data/materials/A.yaml`: align Alpha Irone stock carrier with the live inventory.
- Modify `data/materials/H.yaml`: add hydroxycitronellol and mark depleted hydroxycitronellal unavailable.
- Modify `data/materials/O.yaml`: activate Orris Liquid 30% and viscous olibanum 3 g stock with sourced mixture metadata.
- Modify `engine/name_utils.py`: resolve exact stock labels to canonical names.
- Modify `engine/ingredient_intelligence.py`: add profiles and explicit family/activity-coefficient metadata.
- Modify `engine/odor_thresholds.py`: add derived, clearly labeled fallback ODT records where direct peer ODTs are unavailable.
- Modify `engine/pipeline/natural_absolute_decomposition.py`: add supplier/literature-grounded Orris Liquid and olibanum composite models.
- Update `docs/superpowers/specs/2026-07-16-inventory-materials-design.md`: only if implementation evidence requires a boundary correction.

### Task 1: Lock Stock and Resolution Contracts

**Files:**
- Create: `tests/test_inventory_material_additions.py`

- [ ] **Step 1: Write the failing availability test**

```python
from engine.inventory_parser import parse_inventory


def test_requested_stock_is_available_at_recorded_dilutions():
    available = {
        item.name: item
        for item in parse_inventory(include_unavailable=False)
    }
    assert available["Alpha Irone"].dilution == 0.30
    assert available["Orris Liquid"].dilution == 0.30
    assert available["Hydroxycitronellol"].dilution == 1.0
    assert available["Olibanum Resinoid"].dilution == 1.0
    assert "Hydroxycitronellal" not in available
    assert "Olibanum Resinoid Absolute" not in available
```

- [ ] **Step 2: Write failing data-path tests**

```python
from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.name_utils import names_match
from engine.odor_thresholds import ODT_DATA
from engine.pipeline.natural_absolute_decomposition import composite_oav, get_constituents


def test_requested_materials_have_runtime_data():
    registry = load_registry()
    hydroxy = registry.get("Hydroxycitronellol")
    assert hydroxy is not None
    assert hydroxy.cas == "107-74-4"
    assert hydroxy.vp_25c_pa == 0.0736
    assert registry.get("Orris Liquid").user_stock_dilution.startswith("30%")
    for name in ("Alpha Irone", "Orris Liquid", "Hydroxycitronellol", "Olibanum Resinoid"):
        assert get_profile(name) is not None
    assert not names_match("Hydroxycitronellol", "Hydroxycitronellal")
    assert ODT_DATA["hydroxycitronellol"]["vfy"] == "DERIVED"


def test_natural_mixtures_use_positive_composite_oav():
    for name in ("Orris Liquid", "Olibanum Resinoid", "Olibanum Resinoid (Viscous)"):
        assert get_constituents(name)
        assert composite_oav(name, active_g=0.1, total_moles_in_formula=0.1) > 0
```

- [ ] **Step 3: Run the focused test and verify RED**

Run: `python -m pytest tests/test_inventory_material_additions.py -q`

Expected: failures for missing stock records, missing Hydroxycitronellol/Orris profiles and ODT, and absent composite mappings.

### Task 2: Synchronize Inventory and Single-Material Runtime Data

**Files:**
- Modify: `inventory.txt`
- Modify: `engine/inventory_parser.py`
- Modify: `data/materials/A.yaml`
- Modify: `data/materials/H.yaml`
- Modify: `data/materials/O.yaml`
- Modify: `engine/name_utils.py`
- Modify: `engine/ingredient_intelligence.py`
- Modify: `engine/odor_thresholds.py`
- Test: `tests/test_inventory_material_additions.py`

- [ ] **Step 1: Implement stock truth and depleted parsing**

Add the exact stock labels and recognize depletion without inventing missing solvent or density data:

```python
def _parse_status(raw_name: str) -> str:
    upper = raw_name.upper()
    if "DEPLETED" in upper:
        return "depleted"
    # existing statuses continue unchanged
```

- [ ] **Step 2: Implement canonical physical records**

Use `MW=174.28`, `density=0.928`, `logP=1.5`, and `VP=0.0736 Pa` for Hydroxycitronellol from the RIFM assessment; use supplier-specific effective mixture records for Orris Liquid and viscous olibanum. Keep unknown values null and annotate every effective or proxy value in `notes` and `provenance`.

- [ ] **Step 3: Implement profiles and aliases**

Add exact aliases for `Alpha Irone (30% w/w in IPM)`, `Orris Liquid (30%)`, and `Olibanum Resinoid (viscous, 3 g)`. Add Hydroxycitronellol and Orris Liquid profiles, family overrides, and H-bond-suppressed activity coefficients while preserving Hydroxycitronellal as a distinct key.

- [ ] **Step 4: Implement derived ODT fallbacks**

Add `ODT_DATA` entries with `vfy: DERIVED`, sources that state the absence of a direct peer-reviewed ODT, and positive air/ethanol thresholds. Do not label the estimates as measured or verified.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/test_inventory_material_additions.py -q`

Expected: stock/data/profile tests pass; composite tests still fail until Task 3.

### Task 3: Add Natural-Mixture Composite OAV

**Files:**
- Modify: `engine/pipeline/natural_absolute_decomposition.py`
- Test: `tests/test_inventory_material_additions.py`

- [ ] **Step 1: Add the Orris Liquid composite**

Represent the supplier's 80-85% irone declaration as one 82.5% alpha-irone-equivalent pool. Document that the isomer split is not published and that the remaining 17.5% is intentionally unmodeled.

```python
_ORRIS_LIQUID_CONSTITUENTS = [
    ("irone pool (alpha-equivalent)", 0.825, 206.32, 0.559, 0.9, 1.3),
]
```

- [ ] **Step 2: Add the viscous olibanum composite**

Include supplier-declared benzyl benzoate and a conservative partial Boswellia carteri volatile fraction. Leave the uncharacterized resin matrix unmodeled rather than normalizing the partial list to 100%.

```python
_OLIBANUM_RESINOID_CONSTITUENTS = [
    ("benzyl benzoate", 0.30, 212.24, 0.02, 810.0, 0.7),
    ("alpha pinene", 0.015, 136.24, 400.0, 20.0, 3.0),
    ("limonene", 0.006, 136.24, 200.0, 20.0, 3.0),
    ("myrcene", 0.003, 136.24, 400.0, 10.0, 3.0),
    ("sabinene", 0.002, 136.24, 300.0, 30.0, 3.0),
]
```

- [ ] **Step 3: Register canonical and exact stock aliases**

Map `orris liquid`, `olibanum resinoid`, and `olibanum resinoid (viscous)` to the new constituent lists.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest tests/test_inventory_material_additions.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Refactor comments and provenance without changing behavior**

Ensure comments distinguish supplier declarations, peer literature, and conservative estimates; rerun the focused test unchanged.

### Task 4: Verify, Commit, and Publish

**Files:**
- Verify all modified files from Tasks 1-3.

- [ ] **Step 1: Validate YAML and scientific contracts**

Run: `python -m pytest tests/test_inventory_material_additions.py tests/test_data_spine_loader.py tests/test_scientific_contract.py tests/test_pipeline_formula_state.py -q`

Expected: all selected tests pass without collection or YAML errors.

- [ ] **Step 2: Run the complete engine suite**

Run: `python -m pytest tests -q`

Expected: all tests pass. If runtime exceeds the normal window, record the completed focused suite and the exact broader-suite result.

- [ ] **Step 3: Inspect the diff and stage only intended files**

Run: `git status --short` and `git diff --check`.

Expected: the user's `PERFUME_CHEM_IMPLEMENTATION.txt` and `PERFUME_CHEM_PLAN.txt` remain untracked and unstaged; no whitespace errors appear.

- [ ] **Step 4: Commit the implementation**

Run: `git add <intended paths>` then `git commit -m "feat: sync new perfumery materials"`.

Expected: one intentional feature commit on `codex/add-inventory-materials`.

- [ ] **Step 5: Push and open a draft pull request**

Run: `git push -u origin codex/add-inventory-materials`, then create a draft PR against `master` with the literature/data boundaries and test evidence in the body.

Expected: the branch and PR are visible in the public repository.

- [ ] **Step 6: Re-verify repository visibility**

Run: `gh repo view --json visibility,isPrivate,url`.

Expected: `visibility` is `PUBLIC` and `isPrivate` is `false`.
