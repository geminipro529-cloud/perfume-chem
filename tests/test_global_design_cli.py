"""Global search integration must not fabricate a formula evaluator."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts.verify_formula_workflow import run_design_portfolio
from tests.historical_snapshots import bind_gin_design_test_plan

ROOT = Path(__file__).resolve().parents[1]
FORMULA = ROOT / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json"
OLD_PLAN = ROOT / "data/design_briefs/gin_vetiver_edp_evidence_v1.json"


def _local_mixture_assets_available():
    """Optional downloaded integration data are not part of the source checkout."""
    plan = json.loads((ROOT / "data/design_briefs/gin_vetiver_edp_partial_mixture_v1.json").read_text())
    spec = plan["numerical_model"]
    model_path = ROOT / spec["path"]
    if not model_path.is_file():
        return False
    receipt = json.loads(model_path.read_text())
    paths = [*receipt["fitted_model"]["source_hashes"],
             *(row["path"] for row in spec["structures"].values())]
    return all((ROOT / path).is_file() for path in paths)


LOCAL_MIXTURE_DATA = _local_mixture_assets_available()


def global_plan(tmp_path):
    plan = bind_gin_design_test_plan(json.loads(OLD_PLAN.read_text()))
    plan.update(schema="global_design_portfolio_v1", budget=16, seed=31,
                evaluator_version="fixture-numeric-v1")
    path = tmp_path / "global.json"
    path.write_text(json.dumps(plan))
    return path


def test_global_without_model_fails_instead_of_selecting_baseline(tmp_path):
    before = hashlib.sha256(FORMULA.read_bytes()).hexdigest()
    result = run_design_portfolio(FORMULA, global_plan(tmp_path))
    assert result["status"] == "FAIL_NUMERICAL_EVALUATOR_UNAVAILABLE"
    assert result["evaluated_candidates"] == 0
    assert result["experimental_recommendation"] is None
    assert result["hedonic_optimization_achieved"] is False
    assert result["requires_premix_trial"] is False
    assert result["stock_checks_passed"] == 18
    assert result["formula_modified"] is False
    assert hashlib.sha256(FORMULA.read_bytes()).hexdigest() == before


def test_matching_version_cannot_admit_an_unbound_measured_callback(tmp_path):
    with pytest.raises(ValueError, match="Unbound numerical callbacks"):
        run_design_portfolio(
            FORMULA, global_plan(tmp_path), numerical_evaluator=lambda f: {
                "losses": {"invented": 0.}, "basis": "measured_model_prediction"},
            numerical_evaluator_version="fixture-numeric-v1")


def test_global_callback_version_must_match_plan(tmp_path):
    with pytest.raises(ValueError, match="Unbound numerical callbacks"):
        run_design_portfolio(FORMULA, global_plan(tmp_path),
                             numerical_evaluator=lambda f: {},
                             numerical_evaluator_version="wrong-version")


def test_numeric_callback_is_not_silently_ignored_by_legacy_mode():
    with pytest.raises(ValueError, match="global"):
        run_design_portfolio(FORMULA, OLD_PLAN, numerical_evaluator=lambda f: {})


@pytest.mark.skipif(not LOCAL_MIXTURE_DATA, reason="Optional local DREAM/PubChem evidence bundle not downloaded")
def test_hash_bound_partial_model_runs_without_full_perfume_promotion(tmp_path):
    plan = bind_gin_design_test_plan(json.loads((ROOT / "data/design_briefs/gin_vetiver_edp_partial_mixture_v1.json").read_text()))
    plan["budget"] = 8
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(plan))
    result = run_design_portfolio(FORMULA, path)
    assert result["evaluation_counts"] == {"baseline": 1, "optimizer": 8, "random": 8, "total": 17}
    assert result["numerical_model_binding"]["full_formula_prediction"] is False
    assert len(result["numerical_model_binding"]["unmodeled_frozen_materials"]) == 13
    assert result["formula_modified"] is False
    assert result["predicted_liking"] is None
    assert result["experimental_recommendation"] is None
    assert result["status"] == "DIAGNOSTIC_ONLY_NO_CHANGE"
    assert result["evaluator_authority_admitted"] is False
    assert result["evaluator_authority_reasons"]
    assert result["partial_model_best_observed"] is None
    assert result["diagnostic_frontier"]
    assert result["full_perfume_gate"] == "FAIL_TARGET_AND_MIXTURE_COVERAGE"


@pytest.mark.parametrize("mutation", ["model_hash", "structure", "unfrozen"])
@pytest.mark.skipif(not LOCAL_MIXTURE_DATA, reason="Optional local DREAM/PubChem evidence bundle not downloaded")
def test_partial_model_drift_and_silent_unknown_changes_fail(tmp_path, mutation):
    plan = bind_gin_design_test_plan(json.loads((ROOT / "data/design_briefs/gin_vetiver_edp_partial_mixture_v1.json").read_text()))
    if mutation == "model_hash":
        plan["numerical_model"]["sha256"] = "0" * 64
    elif mutation == "structure":
        plan["numerical_model"]["structures"]["Hedione"]["smiles"] = "CCO"
    else:
        plan["bounds"]["Juniper Berry EO"] = [10, 2000]
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError):
        run_design_portfolio(FORMULA, path)


def test_partial_numerical_completion_cannot_signal_full_perfume_success(monkeypatch, tmp_path):
    import sys

    from scripts import verify_formula_workflow as workflow
    monkeypatch.setattr(sys, "argv", ["verify_formula_workflow", "--formula-file", str(FORMULA),
                                    "--design-plan", str(global_plan(tmp_path))])
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(workflow, "run_design_portfolio", lambda *a, **k: {
        "status": "FINITE_BUDGET_COMPLETE", "evaluated_candidates": 8,
        "stock_checks_passed": 18, "formula_modified": False, "predicted_liking": None,
        "proposal_counts": {}, "pending_proposals": 0,
        "design_plan": {"schema": "global_design_portfolio_v1"},
        "search_complete": True, "full_perfume_gate": "FAIL_TARGET_AND_MIXTURE_COVERAGE"})
    assert workflow.main() == 2


def test_envelopes_classify_allocation_not_baseline_similarity():
    from scripts.verify_formula_workflow import _natural_design_envelopes
    base = {r['material']: r['raw_ul'] for r in json.loads(FORMULA.read_text())['ingredients']}
    # Vetiver-dominant allocation with a substantial gin axis, independent of
    # the original recipe's exact ratios.
    base.update({'Vetiver EO (India)': 1200, 'Vetikon': 450,
                 'Iso E Super': 900, 'Cedarwood Virginia': 100,
                 'Juniper Berry EO': 800, 'Grapefruit FCF oil Sicilian': 250})
    assert 'vetiver_bodied' in _natural_design_envelopes(base)
    base['Cypress EO'] = 300
    assert _natural_design_envelopes(base) == []


def test_natural_adapter_rejects_unbound_profile_before_prediction(tmp_path):
    from scripts.verify_formula_workflow import _bound_natural_mixture_evaluator
    plan = json.loads((ROOT / 'data/design_briefs/gin_vetiver_edp_partial_mixture_v1.json').read_text())
    plan['numerical_model']['kind'] = 'dream2025_natural_scenarios_v1'
    plan['numerical_model']['natural_manifest'] = {'path': 'does-not-exist.json', 'sha256': '0'*64}
    with pytest.raises(ValueError, match='source'):
        _bound_natural_mixture_evaluator(json.loads(FORMULA.read_text()), plan)


@pytest.mark.skipif(not LOCAL_MIXTURE_DATA or not (ROOT / 'output/optimizer_research_20260909/natural_structures/manifest_stereo_v2.json').is_file(),
                    reason='Optional natural/PubChem evidence bundle not downloaded')
def test_natural_scenarios_require_exact_source_before_any_prediction(tmp_path, monkeypatch):
    plan = bind_gin_design_test_plan(json.loads((ROOT / 'data/design_briefs/gin_vetiver_edp_natural_selected_v2.json').read_text()))
    plan['budget'] = 4
    path = tmp_path / 'natural.json'
    path.write_text(json.dumps(plan))
    manifest = json.loads((ROOT / plan['numerical_model']['natural_manifest']['path']).read_bytes())
    source = manifest['source_hashes']['natural_profile_source']
    if hashlib.sha256((ROOT / source['path']).read_bytes()).hexdigest() != source['sha256']:
        # Preserve real current-source drift rather than rebind the old model.
        from scripts import train_odor_predictor

        def forbidden_prediction(*args, **kwargs):
            pytest.fail('Source-drifted natural model reached prediction')

        monkeypatch.setattr(train_odor_predictor, 'predict_dream_mixture', forbidden_prediction)
        with pytest.raises(ValueError, match='Natural model source hash drift'):
            run_design_portfolio(FORMULA, path)
        assert hashlib.sha256(FORMULA.read_bytes()).hexdigest() == plan['formula_sha256']
        return
    result = run_design_portfolio(FORMULA, path)
    assert result['evaluation_counts']['total'] == 9
    assert result['search_complete'] is True
    assert len(result['numerical_model_binding']['mapped_materials']) == 12
    assert len(result['numerical_model_binding']['unmodeled_frozen_materials']) == 6
    assert result['experimental_recommendation'] is None
    assert result['formula_modified'] is False
    assert result['requires_premix_trial'] is False
    assert result['engineering_candidate']['formula']['Juniper Berry EO'] == 930
    assert result['engineering_candidate']['mix_ready'] is False
    assert len(result['design_envelope_fronts']) == 3
    for row in result['archive']:
        scenarios = row['evaluation']['scenario_predictions']
        assert len(scenarios) == 3
        for scenario in scenarios.values():
            coverage = scenario['coverage']
            assert coverage['unresolved_raw_equivalent_ul'] > 1180
            assert coverage['modeled_raw_equivalent_ul'] + coverage['unresolved_raw_equivalent_ul'] == pytest.approx(5400)
            assert coverage['unresolved_residual_renormalized'] is False
            # Actual source binding must keep named geraniol/nerol E/Z separate.
            assert len(coverage['components']) == 32
        assert row['formula']['Ambrox Super'] == 400
        assert row['formula']['Ambrettolide'] == 250


def test_engineering_candidate_cannot_change_total_or_frozen_stock():
    from scripts.verify_formula_workflow import _validate_engineering_candidate
    base = {'neat': 80., 'diluted': 20.}
    bounds = {'neat': [10, 100], 'diluted': [20, 20]}
    assert _validate_engineering_candidate(base, base, bounds) == base
    for candidate in ({'neat': 90., 'diluted': 20.}, {'neat': 90., 'diluted': 10.},
                      {'neat': 80.}, {'neat': float('nan'), 'diluted': 20.}):
        with pytest.raises(ValueError):
            _validate_engineering_candidate(candidate, base, bounds)


def test_engineering_lineage_binds_receipt_hash_and_rounded_point(monkeypatch, tmp_path):
    from scripts import verify_formula_workflow as workflow
    monkeypatch.setattr(workflow, 'PROJECT_ROOT', tmp_path)
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps({'design_envelope_fronts': {'gin': {'pareto': [
        {'source': 'random', 'formula': {'a': 23., 'b': 37.}}]}}}))
    proposal = {'formula': {'a': 20, 'b': 40}, 'lineage': {'path': 'receipt.json',
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'envelope': 'gin', 'source': 'random'}}
    assert workflow._verify_engineering_lineage(proposal)['verified'] is True
    for field in ('source', 'envelope'):
        original = proposal['lineage'][field]
        proposal['lineage'][field] = 'wrong'
        with pytest.raises(ValueError):
            workflow._verify_engineering_lineage(proposal)
        proposal['lineage'][field] = original
    proposal['formula']['a'] = 30
    with pytest.raises(ValueError):
        workflow._verify_engineering_lineage(proposal)
    proposal['formula']['a'] = 20
    path.write_text('{}')
    with pytest.raises(ValueError, match='hash'):
        workflow._verify_engineering_lineage(proposal)
    path.unlink()
    with pytest.raises(ValueError):
        workflow._verify_engineering_lineage(proposal)
