"""Historical green replay never certifies a changed current inventory."""
import pytest

from engine.experiments.checkpoint3_readiness import evaluate_r5_checkpoint3_readiness
from engine.experiments.checkpoint4_readiness import evaluate_r6_aimi_checkpoint4_readiness
from engine.experiments.checkpoint5_readiness import (
    Checkpoint5ContractError,
    evaluate_r6_checkpoint5_readiness,
)


def test_current_cp3_and_cp4_do_not_inherit_september_verification():
    for evaluate in (evaluate_r5_checkpoint3_readiness, evaluate_r6_aimi_checkpoint4_readiness):
        assert evaluate()["input_integrity_state"] != "VERIFIED"


def test_current_cp5_rejects_frozen_inventory_pin():
    with pytest.raises(Checkpoint5ContractError, match="inventory text hash drift"):
        evaluate_r6_checkpoint5_readiness()


def test_superseded_gin_plan_does_not_bind_to_current_inventory():
    from scripts.verify_formula_workflow import run_design_portfolio
    from tests.historical_snapshots import ROOT

    with pytest.raises(ValueError, match="Design plan source drift"):
        run_design_portfolio(
            ROOT / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json",
            ROOT / "data/design_briefs/gin_vetiver_edp_evidence_v1.json",
        )
