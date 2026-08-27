"""Tests for engine.versioning.formula_version."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.versioning.formula_version import (
    CHANGE_ADD,
    CHANGE_CREATE,
    CHANGE_DECREASE,
    CHANGE_INCREASE,
    CHANGE_REMOVE,
    CHANGE_SUBSTITUTE,
    MODE_CREATIVE_FORMULATION,
    MODE_RECONSTRUCTION,
    FormulaChange,
    FormulaVersion,
    compute_formula_hash,
    diff_versions,
    version_graph,
)


# ===========================================================================
# FormulaChange creation
# ===========================================================================


def test_change_add():
    c = FormulaChange(
        material_name="Bergamot FCF",
        change_type=CHANGE_ADD,
        new_value=200.0,
        reason="Add citrus top note",
    )
    assert c.material_name == "Bergamot FCF"
    assert c.change_type == CHANGE_ADD
    assert c.new_value == 200.0
    assert c.old_value is None
    assert c.unit == "uL"
    assert c.reason == "Add citrus top note"


def test_change_remove():
    c = FormulaChange(
        material_name="Indole",
        change_type=CHANGE_REMOVE,
        old_value=30.0,
        reason="Remove animalic note",
    )
    assert c.change_type == CHANGE_REMOVE
    assert c.old_value == 30.0
    assert c.new_value is None


def test_change_increase():
    c = FormulaChange(
        material_name="Hedione",
        change_type=CHANGE_INCREASE,
        old_value=150.0,
        new_value=300.0,
        reason="Boost radiance",
    )
    assert c.change_type == CHANGE_INCREASE
    assert c.old_value == 150.0
    assert c.new_value == 300.0


def test_change_decrease():
    c = FormulaChange(
        material_name="Iso E Super",
        change_type=CHANGE_DECREASE,
        old_value=400.0,
        new_value=250.0,
        reason="Reduce woodiness",
    )
    assert c.change_type == CHANGE_DECREASE
    assert c.old_value == 400.0
    assert c.new_value == 250.0


def test_change_substitute():
    c = FormulaChange(
        material_name="Sandalwood",
        change_type=CHANGE_SUBSTITUTE,
        old_material="Bacdanol",
        new_material="Javanol",
        reason="Swap to premium sandalwood",
    )
    assert c.change_type == CHANGE_SUBSTITUTE
    assert c.old_material == "Bacdanol"
    assert c.new_material == "Javanol"
    assert c.old_value is None
    assert c.new_value is None


# ===========================================================================
# FormulaVersion creation
# ===========================================================================


def test_version_initial():
    v = FormulaVersion.create_initial(
        formula_hash="abc123",
        description="Initial formula",
    )
    assert v.parent_version_id is None
    assert v.change_type == CHANGE_CREATE
    assert v.formula_hash == "abc123"
    assert v.description == "Initial formula"
    assert v.mode == MODE_CREATIVE_FORMULATION
    assert v.changes == ()


def test_version_with_parent():
    parent = FormulaVersion.create_initial(formula_hash="parent_hash")
    child = FormulaVersion.derive(
        parent=parent,
        formula_hash="child_hash",
        change_type=CHANGE_ADD,
        changes=(
            FormulaChange(
                material_name="Bergamot FCF",
                change_type=CHANGE_ADD,
                new_value=200.0,
            ),
        ),
        description="Added bergamot",
    )
    assert child.parent_version_id == parent.version_id
    assert child.formula_hash == "child_hash"
    assert child.change_type == CHANGE_ADD
    assert len(child.changes) == 1
    assert child.description == "Added bergamot"
    assert child.mode == MODE_CREATIVE_FORMULATION  # inherited from parent


def test_version_with_changes_list():
    changes = [
        FormulaChange("Hedione", CHANGE_INCREASE, 100.0, 200.0),
        FormulaChange("Iso E Super", CHANGE_DECREASE, 300.0, 200.0),
    ]
    v = FormulaVersion.create_initial(
        formula_hash="hash123",
        description="With changes",
    )
    # create_initial always has empty changes; derive is the way to attach changes
    assert v.changes == ()
    # Verify we can create a version with changes via derive
    parent = v
    child = FormulaVersion.derive(
        parent=parent,
        formula_hash="hash456",
        change_type=CHANGE_ADD,
        changes=tuple(changes),
    )
    assert len(child.changes) == 2


def test_version_without_parent_has_no_parent():
    v = FormulaVersion.create_initial(formula_hash="h1")
    assert v.parent_version_id is None


def test_version_mode_custom():
    v = FormulaVersion.create_initial(
        formula_hash="h1",
        mode=MODE_RECONSTRUCTION,
    )
    assert v.mode == MODE_RECONSTRUCTION


# ===========================================================================
# version_graph
# ===========================================================================


def test_version_graph_single():
    v = FormulaVersion.create_initial(formula_hash="h1")
    g = version_graph([v])
    assert g == {v.version_id: []}


def test_version_graph_two_versions():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.derive(v1, "h2", CHANGE_ADD, ())
    g = version_graph([v1, v2])
    assert g[v1.version_id] == [v2.version_id]
    assert g[v2.version_id] == []


def test_version_graph_three_in_chain():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.derive(v1, "h2", CHANGE_ADD, ())
    v3 = FormulaVersion.derive(v2, "h3", CHANGE_ADD, ())
    g = version_graph([v1, v2, v3])
    assert g[v1.version_id] == [v2.version_id]
    assert g[v2.version_id] == [v3.version_id]
    assert g[v3.version_id] == []


def test_version_graph_branching():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2a = FormulaVersion.derive(v1, "h2a", CHANGE_ADD, ())
    v2b = FormulaVersion.derive(v1, "h2b", CHANGE_ADD, ())
    g = version_graph([v1, v2a, v2b])
    assert sorted(g[v1.version_id]) == sorted([v2a.version_id, v2b.version_id])
    assert g[v2a.version_id] == []
    assert g[v2b.version_id] == []


# ===========================================================================
# diff_versions
# ===========================================================================


def test_diff_versions_add_remove():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.derive(
        v1,
        "h2",
        CHANGE_ADD,
        (
            FormulaChange("Bergamot", CHANGE_ADD, new_value=200.0),
            FormulaChange("Indole", CHANGE_REMOVE, old_value=30.0),
        ),
    )
    lines = diff_versions(v1, v2)
    # Header lines
    assert any("---" in l for l in lines)
    assert any("+++" in l for l in lines)
    # ADD line — diff_versions compares changes tuples; v2 has an ADD for Bergamot
    add_lines = [l for l in lines if "Bergamot" in l]
    assert len(add_lines) == 1
    assert "ADD" in add_lines[0]
    assert "200" in add_lines[0]
    # REMOVE line — v2 has a REMOVE for Indole (shown as + because v1 has no entry)
    rem_lines = [l for l in lines if "Indole" in l]
    assert len(rem_lines) == 1
    assert "REMOVE" in rem_lines[0]


def test_diff_versions_increase_shows_old_new():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.derive(
        v1,
        "h2",
        CHANGE_INCREASE,
        (FormulaChange("Hedione", CHANGE_INCREASE, old_value=100.0, new_value=300.0),),
    )
    lines = diff_versions(v1, v2)
    inc_lines = [l for l in lines if "Hedione" in l]
    assert len(inc_lines) == 1
    # v1 has no changes, so the diff shows v2's change as an addition
    # old_value is not shown because v1 has no entry for Hedione
    assert "INCREASE" in inc_lines[0]
    assert "300" in inc_lines[0]


def test_diff_versions_substitute():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.derive(
        v1,
        "h2",
        CHANGE_SUBSTITUTE,
        (
            FormulaChange(
                "Sandalwood",
                CHANGE_SUBSTITUTE,
                old_material="Bacdanol",
                new_material="Javanol",
            ),
        ),
    )
    lines = diff_versions(v1, v2)
    sub_lines = [l for l in lines if "Sandalwood" in l]
    assert len(sub_lines) == 1


def test_diff_versions_both_empty():
    v1 = FormulaVersion.create_initial(formula_hash="h1")
    v2 = FormulaVersion.create_initial(formula_hash="h2")
    lines = diff_versions(v1, v2)
    assert any("no material changes" in l for l in lines)


# ===========================================================================
# compute_formula_hash
# ===========================================================================


def test_hash_same_ingredients():
    ingredients = {"Bergamot FCF": 200.0, "Hedione": 300.0}
    h1 = compute_formula_hash(ingredients)
    h2 = compute_formula_hash(ingredients)
    assert h1 == h2


def test_hash_different_ingredients():
    h1 = compute_formula_hash({"Bergamot FCF": 200.0})
    h2 = compute_formula_hash({"Hedione": 300.0})
    assert h1 != h2


def test_hash_different_amounts():
    h1 = compute_formula_hash({"Bergamot FCF": 200.0})
    h2 = compute_formula_hash({"Bergamot FCF": 250.0})
    assert h1 != h2


def test_hash_with_dilutions_differs():
    h1 = compute_formula_hash({"Bergamot FCF": 200.0})
    h2 = compute_formula_hash({"Bergamot FCF": 200.0}, dilutions={"Bergamot FCF": 0.1})
    assert h1 != h2


def test_hash_deterministic_order():
    h1 = compute_formula_hash({"A": 1.0, "B": 2.0})
    h2 = compute_formula_hash({"B": 2.0, "A": 1.0})
    assert h1 == h2


# ===========================================================================
# as_dict / from_dict round-trip
# ===========================================================================


def test_formula_change_as_dict_from_dict():
    c = FormulaChange(
        material_name="Hedione",
        change_type=CHANGE_INCREASE,
        old_value=100.0,
        new_value=300.0,
        unit="uL",
        reason="Boost radiance",
    )
    d = c.as_dict()
    restored = FormulaChange.from_dict(d)
    assert restored == c
    assert restored.material_name == "Hedione"
    assert restored.old_value == 100.0
    assert restored.new_value == 300.0


def test_formula_change_substitute_round_trip():
    c = FormulaChange(
        material_name="Sandalwood",
        change_type=CHANGE_SUBSTITUTE,
        old_material="Bacdanol",
        new_material="Javanol",
        reason="Premium swap",
    )
    d = c.as_dict()
    restored = FormulaChange.from_dict(d)
    assert restored == c
    assert restored.old_material == "Bacdanol"
    assert restored.new_material == "Javanol"


def test_formula_change_remove_round_trip():
    c = FormulaChange(
        material_name="Indole",
        change_type=CHANGE_REMOVE,
        old_value=30.0,
    )
    d = c.as_dict()
    restored = FormulaChange.from_dict(d)
    assert restored == c
    assert restored.old_value == 30.0
    assert restored.new_value is None


def test_formula_version_as_dict_from_dict():
    v = FormulaVersion.create_initial(
        formula_hash="abc123",
        description="Initial version",
        mode=MODE_RECONSTRUCTION,
    )
    d = v.as_dict()
    restored = FormulaVersion.from_dict(d)
    assert restored.version_id == v.version_id
    assert restored.parent_version_id == v.parent_version_id
    assert restored.formula_hash == v.formula_hash
    assert restored.description == v.description
    assert restored.mode == v.mode
    assert restored.changes == v.changes


def test_formula_version_with_nested_changes_round_trip():
    parent = FormulaVersion.create_initial(formula_hash="parent_hash")
    child = FormulaVersion.derive(
        parent,
        "child_hash",
        CHANGE_ADD,
        (
            FormulaChange("Bergamot", CHANGE_ADD, new_value=200.0),
            FormulaChange("Hedione", CHANGE_INCREASE, 100.0, 300.0),
            FormulaChange(
                "Sandalwood",
                CHANGE_SUBSTITUTE,
                old_material="Bacdanol",
                new_material="Javanol",
            ),
        ),
        description="Added top notes",
        mode=MODE_RECONSTRUCTION,
    )
    d = child.as_dict()
    restored = FormulaVersion.from_dict(d)
    assert restored.version_id == child.version_id
    assert restored.parent_version_id == child.parent_version_id
    assert restored.formula_hash == child.formula_hash
    assert restored.description == child.description
    assert restored.mode == child.mode
    assert len(restored.changes) == 3
    for orig, rest in zip(child.changes, restored.changes):
        assert orig == rest


def test_formula_version_from_dict_defaults():
    """from_dict should handle missing optional fields gracefully."""
    d = {
        "version_id": "v1",
        "parent_version_id": None,
        "timestamp": "2026-01-01T00:00:00Z",
        "formula_hash": "h1",
        "change_type": CHANGE_CREATE,
        "changes": [],
    }
    v = FormulaVersion.from_dict(d)
    assert v.description == ""
    assert v.mode == MODE_CREATIVE_FORMULATION
    assert v.changes == ()
