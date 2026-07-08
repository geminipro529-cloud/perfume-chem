from engine.data_spine.loader import load_materials
from engine.science_audit import _gather_data_coverage


def test_science_audit_uses_loader_backed_completeness():
    coverage = _gather_data_coverage()
    materials = load_materials()

    assert coverage
    assert coverage["mw"] > 0.0
    assert materials

    supplier_covered = sum(1 for material in materials if material.completeness()["supplier"])
    supplier_pct = 100.0 * supplier_covered / len(materials)
    assert supplier_pct > 75.0
