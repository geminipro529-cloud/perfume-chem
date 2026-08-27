import pytest

from engine.bottle_addition import (
    AdditionCalculationError,
    AdditionRequest,
    AdditionSolver,
    BottleSnapshot,
    PipetteProfile,
    StockSolution,
)


def test_reach_target_accounts_for_existing_active_mass_and_added_stock_mass():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=30.0, active_material_mass_g=0.03),
            stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
            target_active_mass_fraction=0.002,
            pipette=PipetteProfile(
                minimum_ul=10.0,
                increment_ul=5.0,
                maximum_single_step_ul=200.0,
            ),
        )
    )

    assert result.exact_stock_mass_g == pytest.approx(0.30612244898)
    assert result.exact_stock_volume_ul == pytest.approx(306.12244898)
    assert result.rounded_stock_volume_ul == 305.0
    assert result.staged_additions_ul == (155.0, 150.0)
    assert sum(result.staged_additions_ul) == result.rounded_stock_volume_ul
    assert result.pipette_feasible is True

    exact_ledger = result.mass_ledger["calculated"]
    assert exact_ledger["after"]["total_mass_g"] == pytest.approx(
        exact_ledger["before"]["total_mass_g"]
        + exact_ledger["addition"]["stock_mass_g"]
    )
    assert exact_ledger["after"]["active_material_mass_g"] == pytest.approx(
        exact_ledger["before"]["active_material_mass_g"]
        + exact_ledger["addition"]["active_material_mass_g"]
    )
    assert exact_ledger["after"]["active_mass_fraction"] == pytest.approx(0.002)

    rounded_ledger = result.mass_ledger["pipette_rounded"]
    assert rounded_ledger is not None
    expected_error_ppm = (
        rounded_ledger["after"]["active_mass_fraction"] - 0.002
    ) * 1_000_000
    assert result.target_error_ppm == pytest.approx(expected_error_ppm)


def test_missing_density_preserves_mass_result_but_withholds_volume_plan():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=0.2),
            target_active_mass_fraction=0.01,
        )
    )

    assert result.exact_stock_mass_g == pytest.approx(10.0 / 19.0)
    assert result.exact_stock_volume_ul is None
    assert result.rounded_stock_volume_ul is None
    assert result.pipette_feasible is False
    assert "density" in " ".join(result.warnings).lower()


def test_target_below_current_fraction_is_not_an_additive_operation():
    with pytest.raises(AdditionCalculationError, match="below current"):
        AdditionSolver().reach_target_active_fraction(
            AdditionRequest(
                bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.2),
                stock=StockSolution(active_mass_fraction=0.1, density_g_ml=1.0),
                target_active_mass_fraction=0.01,
            )
        )


def test_target_must_be_lower_than_stock_fraction():
    with pytest.raises(AdditionCalculationError, match="stock"):
        AdditionSolver().reach_target_active_fraction(
            AdditionRequest(
                bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
                stock=StockSolution(active_mass_fraction=0.1, density_g_ml=1.0),
                target_active_mass_fraction=0.1,
            )
        )


def test_invalid_bottle_cannot_contain_more_active_mass_than_total_mass():
    with pytest.raises(AdditionCalculationError, match="cannot exceed"):
        BottleSnapshot(total_mass_g=1.0, active_material_mass_g=1.01)


def test_subminimum_addition_is_reported_as_infeasible_without_rounding_up():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=1.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=1.0, density_g_ml=1.0),
            target_active_mass_fraction=0.000001,
            pipette=PipetteProfile(minimum_ul=10.0, increment_ul=1.0),
        )
    )

    assert result.exact_stock_volume_ul == pytest.approx(0.001000001)
    assert result.pipette_feasible is False
    assert result.rounded_stock_volume_ul is None
    assert result.staged_additions_ul == ()
    assert result.mass_ledger["pipette_rounded"] is None


def test_solver_is_scale_invariant():
    solver = AdditionSolver()
    small = solver.reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.01),
            stock=StockSolution(active_mass_fraction=0.1),
            target_active_mass_fraction=0.002,
        )
    )
    large = solver.reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=100.0, active_material_mass_g=0.1),
            stock=StockSolution(active_mass_fraction=0.1),
            target_active_mass_fraction=0.002,
        )
    )

    assert large.exact_stock_mass_g == pytest.approx(10 * small.exact_stock_mass_g)


def test_already_reached_target_returns_a_zero_addition():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.02),
            stock=StockSolution(active_mass_fraction=0.1, density_g_ml=0.95),
            target_active_mass_fraction=0.002,
            pipette=PipetteProfile(minimum_ul=10.0, increment_ul=1.0),
        )
    )

    assert result.exact_stock_mass_g == 0.0
    assert result.exact_stock_volume_ul == 0.0
    assert result.rounded_stock_volume_ul == 0.0
    assert result.resulting_active_mass_fraction == pytest.approx(0.002)
    assert result.target_error_ppm == pytest.approx(0.0)
    assert result.pipette_feasible is True
    assert result.staged_additions_ul == ()


def test_standard_uncertainty_is_propagated_from_declared_inputs():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(
                total_mass_g=30.0,
                active_material_mass_g=0.03,
                total_mass_standard_uncertainty_g=0.01,
                active_mass_standard_uncertainty_g=0.001,
            ),
            stock=StockSolution(
                active_mass_fraction=0.10,
                density_g_ml=0.95,
                active_fraction_standard_uncertainty=0.001,
                density_standard_uncertainty_g_ml=0.005,
            ),
            target_active_mass_fraction=0.002,
        )
    )

    assert result.exact_stock_mass_standard_uncertainty_g > 0
    assert result.exact_stock_volume_standard_uncertainty_ul is not None
    assert result.exact_stock_volume_standard_uncertainty_ul > 0
    assert result.evidence["stock_mass_arithmetic"].classification.value == "EXACT"
    assert result.evidence["uncertainty_propagation"].classification.value == (
        "LITERATURE_DERIVED"
    )
    assert (
        result.as_dict()["evidence"]["uncertainty_propagation"]["classification"]
        == "LITERATURE_DERIVED"
    )


def test_multistep_pipette_uncertainty_combines_random_and_systematic_components():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(
                total_mass_g=30.0,
                active_material_mass_g=0.03,
                total_mass_standard_uncertainty_g=0.01,
                active_mass_standard_uncertainty_g=0.001,
            ),
            stock=StockSolution(
                active_mass_fraction=0.10,
                density_g_ml=1.0,
                active_fraction_standard_uncertainty=0.001,
                density_standard_uncertainty_g_ml=0.002,
            ),
            target_active_mass_fraction=0.002,
            pipette=PipetteProfile(
                minimum_ul=10.0,
                increment_ul=5.0,
                maximum_single_step_ul=200.0,
                standard_uncertainty_ul=1.0,
                systematic_standard_uncertainty_ul=0.5,
            ),
        )
    )

    assert len(result.staged_additions_ul) == 2
    assert result.pipette_standard_uncertainty_ul == pytest.approx(3**0.5)
    assert result.resulting_active_mass_fraction_standard_uncertainty is not None
    assert result.resulting_active_mass_fraction_standard_uncertainty > 0
    assert result.evidence["pipette_delivery_uncertainty"].classification.value == (
        "LITERATURE_DERIVED"
    )


def test_zero_addition_has_zero_plan_uncertainty():
    result = AdditionSolver().reach_target_active_fraction(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.02),
            stock=StockSolution(active_mass_fraction=0.1, density_g_ml=1.0),
            target_active_mass_fraction=0.002,
            pipette=PipetteProfile(
                minimum_ul=10.0,
                increment_ul=1.0,
                standard_uncertainty_ul=1.0,
                systematic_standard_uncertainty_ul=0.5,
            ),
        )
    )

    assert result.pipette_standard_uncertainty_ul == 0.0
    assert result.resulting_active_mass_fraction_standard_uncertainty == 0.0


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: BottleSnapshot(0.0, 0.0), "total_mass_g"),
        (lambda: BottleSnapshot(1.0, -0.1), "active_material_mass_g"),
        (lambda: StockSolution(0.0), "active_mass_fraction"),
        (lambda: StockSolution(0.1, density_g_ml=0.0), "density_g_ml"),
        (lambda: PipetteProfile(0.0, 1.0), "minimum_ul"),
        (lambda: PipetteProfile(10.0, 0.0), "increment_ul"),
        (lambda: PipetteProfile(10.0, 1.0, maximum_single_step_ul=5.0), "maximum"),
    ],
)
def test_input_quantities_are_validated(factory, message):
    with pytest.raises(AdditionCalculationError, match=message):
        factory()
