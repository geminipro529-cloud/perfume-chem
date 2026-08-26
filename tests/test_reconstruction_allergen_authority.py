from engine.allergen_solver import solve_allergen_ratios
from engine.ifra_constraints import compute_ifra_windows
from engine.reconstruction_pipeline import FragranceSpec, run_reconstruction_pipeline
from engine.reverse_engineer import (
    EvidencePool,
    parse_allergen_list,
    reverse_engineer,
)


def test_allergen_label_does_not_create_standalone_material_hypothesis():
    items = parse_allergen_list("Linalool, Citronellol")
    assert items
    assert all(not item.material_identity_authority for item in items)

    pool = EvidencePool("label-only")
    pool.add_many(items)
    result = reverse_engineer(pool)

    assert len(pool) == 2
    assert result.materials == []


def test_allergen_list_position_cannot_back_calculate_natural_doses():
    first = solve_allergen_ratios(
        "first",
        ["linalool", "citronellol"],
        concentrate_pct=25.0,
        known_ratios={"citronellol:geraniol": 1.94},
    )
    reversed_order = solve_allergen_ratios(
        "reversed",
        ["citronellol", "linalool"],
        concentrate_pct=25.0,
    )

    assert first.authority == "UNSUPPORTED_FROM_LABEL_ORDER"
    assert first.quantitative_authority is False
    assert first.solved_naturals == []
    assert first.deficit_analysis == {}
    assert first.score == 0.0
    assert {row.allergen: row.estimated_pct_range for row in first.equations} == {
        row.allergen: row.estimated_pct_range for row in reversed_order.equations
    }


def test_absent_allergen_bounds_require_explicit_complete_label_regime():
    default = compute_ifra_windows(
        ["linalool"],
        all_26_allergens=["linalool", "citronellol"],
    )
    complete = compute_ifra_windows(
        ["linalool"],
        all_26_allergens=["linalool", "citronellol"],
        label_regime_complete=True,
    )

    assert default.absence_authority is False
    assert default.absent_allergens == []
    assert complete.absence_authority is True
    assert complete.absent_allergens == ["citronellol"]


def test_explicit_unknown_allergen_gets_no_invented_quantitative_limit():
    result = compute_ifra_windows(
        ["newly regulated constituent"],
        all_26_allergens=["linalool", "newly regulated constituent"],
        label_regime_complete=True,
    )

    window = result.windows[0]
    assert window.allergen_name == "newly regulated constituent"
    assert window.ifra_restricted is False
    assert window.max_pct == 100.0
    assert window.confidence == 0.0
    assert result.absent_allergens == ["linalool"]


def test_reconstruction_keeps_label_evidence_out_of_final_materials():
    report = run_reconstruction_pipeline(
        FragranceSpec(
            name="Label-only study",
            declared_allergens=["linalool", "citronellol"],
        )
    )

    assert report.final_materials == {}
    evidence_category = next(
        row for row in report.category_scores if row.category == "ALLERGEN_EVIDENCE"
    )
    chemistry_category = next(
        row for row in report.category_scores if row.category == "ALLERGEN_CHEMISTRY"
    )
    assert evidence_category.score == 0.0
    assert "no reconstruction-confidence credit" in evidence_category.detail
    assert chemistry_category.score == 0.0
    assert "no natural percentages" in chemistry_category.detail
