from itertools import permutations

import pytest

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_REQUIREMENT_TYPES,
)
from app.services.lab_backfill import (
    BACKFILL_PRIORITY_DIMENSIONS,
    BACKFILL_PRIORITY_POLICY,
    BackfillGapProjection,
    BackfillSignalVector,
    ResolvedBackfillMaterial,
    backfill_policy_hash,
    build_backfill_dashboard,
    rank_backfill_materials,
)


def _gap(
    state: str = "MISSING",
    requirement_type: str = "EXACT_IDENTITY",
    evidence_class: str = "UNKNOWN",
) -> BackfillGapProjection:
    return BackfillGapProjection(
        requirement_type=requirement_type,
        state=state,
        evidence_class=evidence_class,
    )


def _material(
    material_id: str,
    *,
    current_inventory: bool | None = False,
    active_or_shipped_formula: bool | None = False,
    high_dose_structure: float | None = 0.0,
    potent_trace: float | None = 0.0,
    regulatory_or_family_driver: int | None = 0,
    analytical_standard: bool | None = False,
    natural_constituent: bool | None = False,
    model_sensitivity: float | None = 0.0,
    gaps: tuple[BackfillGapProjection, ...] = (_gap(),),
    canonical_name: str | None = None,
) -> ResolvedBackfillMaterial:
    return ResolvedBackfillMaterial(
        material_id=material_id,
        canonical_name=canonical_name or material_id,
        chemical_family=None,
        evidence_class="UNKNOWN",
        signal_vector=BackfillSignalVector(
            current_inventory=current_inventory,
            active_or_shipped_formula=active_or_shipped_formula,
            high_dose_structure=high_dose_structure,
            potent_trace=potent_trace,
            regulatory_or_family_driver=regulatory_or_family_driver,
            analytical_standard=analytical_standard,
            natural_constituent=natural_constituent,
            model_sensitivity=model_sensitivity,
        ),
        gaps=gaps,
    )


def test_b8_priority_policy_has_exact_order_and_stable_hash():
    assert BACKFILL_PRIORITY_DIMENSIONS == (
        "CURRENT_INVENTORY",
        "ACTIVE_OR_SHIPPED_FORMULA",
        "HIGH_DOSE_STRUCTURE",
        "POTENT_TRACE",
        "REGULATORY_OR_FAMILY_DRIVER",
        "ANALYTICAL_STANDARD",
        "NATURAL_CONSTITUENT",
        "MODEL_SENSITIVITY",
    )
    assert tuple(BACKFILL_PRIORITY_POLICY["dimensions"]) == (
        BACKFILL_PRIORITY_DIMENSIONS
    )
    assert BACKFILL_PRIORITY_POLICY["requirement_types"] == list(
        BACKFILL_REQUIREMENT_TYPES
    )
    assert len(backfill_policy_hash()) == 64
    assert backfill_policy_hash() == backfill_policy_hash()


def test_b8_ranking_is_strictly_lexicographic():
    fixtures = (
        _material("unknown", current_inventory=None),
        _material("sensitive", model_sensitivity=1.0),
        _material("natural", natural_constituent=True),
        _material("standard", analytical_standard=True),
        _material("regulatory", regulatory_or_family_driver=1),
        _material("potent-trace", potent_trace=1.0),
        _material("high-dose", high_dose_structure=1.0),
        _material("active", active_or_shipped_formula=True),
        _material("owned", current_inventory=True),
    )

    ordered = rank_backfill_materials(fixtures)

    assert [row.material_id for row in ordered] == [
        "owned",
        "active",
        "high-dose",
        "potent-trace",
        "regulatory",
        "standard",
        "natural",
        "sensitive",
        "unknown",
    ]
    assert [row.rank for row in ordered] == list(range(1, 10))


def test_b8_ranking_is_input_order_independent():
    fixtures = (
        _material("owned", current_inventory=True),
        _material("active", active_or_shipped_formula=True),
        _material("sensitive", model_sensitivity=1.0),
    )
    expected = ["owned", "active", "sensitive"]
    for ordering in permutations(fixtures):
        assert [
            row.material_id for row in rank_backfill_materials(ordering)
        ] == expected


def test_b8_ranking_uses_gap_counts_then_name_and_id_for_ties():
    critical = _material(
        "critical",
        gaps=(
            _gap("MISSING", "EXACT_IDENTITY"),
            _gap("MISSING", "DENSITY"),
        ),
    )
    fewer = _material("fewer", gaps=(_gap("MISSING", "DENSITY"),))
    alpha_b = _material(
        "id-b",
        gaps=(_gap("NOT_APPLICABLE", "NATURAL_LOT_COMPOSITION"),),
        canonical_name="alpha",
    )
    alpha_a = _material(
        "id-a",
        gaps=(_gap("NOT_APPLICABLE", "NATURAL_LOT_COMPOSITION"),),
        canonical_name="alpha",
    )

    ordered = rank_backfill_materials((alpha_b, fewer, alpha_a, critical))

    assert [row.material_id for row in ordered] == [
        "critical",
        "fewer",
        "id-a",
        "id-b",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("high_dose_structure", float("nan")),
        ("potent_trace", float("inf")),
        ("model_sensitivity", -0.1),
        ("model_sensitivity", 1.1),
    ),
)
def test_b8_ranking_rejects_nonfinite_or_out_of_range_signals(field, value):
    overrides = {field: value}
    with pytest.raises(ValueError):
        rank_backfill_materials((_material("bad", **overrides),))


def test_b8_dashboard_emits_seven_strata_without_overall_score():
    material = _material(
        "owned",
        current_inventory=True,
        active_or_shipped_formula=None,
        regulatory_or_family_driver=1,
        model_sensitivity=None,
        gaps=(
            _gap("ACCEPTED_EXACT", "EXACT_IDENTITY", "MEASURED"),
            _gap("MISSING", "DENSITY", "UNKNOWN"),
        ),
    )

    cells = build_backfill_dashboard(rank_backfill_materials((material,)))

    assert {cell.dimension for cell in cells} == set(
        BACKFILL_DASHBOARD_DIMENSIONS
    )
    assert all(
        cell.requirements_total
        == cell.accepted_exact_count
        + cell.accepted_scoped_count
        + cell.weak_count
        + cell.conflicted_count
        + cell.unknown_count
        + cell.missing_count
        + cell.not_applicable_count
        for cell in cells
    )
    banned = {
        "OVERALL",
        "TOTAL_CONFIDENCE",
        "COVERAGE_SCORE",
        "CONFIDENCE_PERCENT",
    }
    assert not any(
        cell.dimension in banned or cell.dimension_key in banned
        for cell in cells
    )


def test_b8_dashboard_keeps_evidence_classes_separate():
    material = _material(
        "mixed",
        gaps=(
            _gap("ACCEPTED_EXACT", "EXACT_IDENTITY", "MEASURED"),
            _gap("WEAK", "DENSITY", "HEURISTIC"),
            _gap("UNKNOWN", "VAPOR_PRESSURE", "UNKNOWN"),
        ),
    )

    cells = build_backfill_dashboard(rank_backfill_materials((material,)))
    evidence_keys = {
        cell.dimension_key
        for cell in cells
        if cell.dimension == "EVIDENCE_CLASS"
    }

    assert evidence_keys == {"MEASURED", "HEURISTIC", "UNKNOWN"}
