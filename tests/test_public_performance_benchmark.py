"""Public performance benchmark: Parfumo votes and TGSC substantivity vs the gate's numbers."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.calibration import public_performance as pp

REPO = Path(__file__).resolve().parents[1]


def _run(oav_by_hour, ul=1000.0, rows=10, path="x.md", no_oav=()):
    hours = tuple(float(h) for h in oav_by_hour)
    frames = tuple(dict(v) for v in oav_by_hour.values())
    names = set().union(*frames)
    return pp.BuildRun(
        path=path,
        hours=hours,
        batch_ml=30.0,
        rows=rows,
        oav=frames,
        active_ul=tuple({n: ul / len(names) for n in names} for _ in frames),
        no_oav_rows=tuple(no_oav),
    )


def test_benchmark_file_is_complete_and_records_the_failed_verdict():
    bm = pp.load_benchmark()
    assert bm["schema"] == "public_performance_benchmark_v1"
    assert bm["status"] == pp.PUBLIC_BENCHMARK_STATUS == "FAILED_PUBLIC_BENCHMARK"
    assert len(bm["labels"]) == 20
    for key, lab in bm["labels"].items():
        assert 0 < lab["longevity"] <= 10 and 0 < lab["sillage"] <= 10, key
        assert lab["n_longevity"] >= 250 and lab["url"].startswith("https://www.parfumo.com/"), key
        assert bm["builds"][key], key
    assert set(bm["builds"]) == set(bm["labels"])
    for entries in bm["builds"].values():
        for entry in entries:
            if not entry.startswith("project:"):
                assert (REPO / entry).exists(), entry
    assert len(bm["tgsc_substantivity"]) >= 80
    assert all(0 < r["hours"] <= 400 for r in bm["tgsc_substantivity"])
    result = bm["result_20261106"]
    assert result["clock_x1"]["any_read_out_passes"] is False
    assert result["clock_x100"]["any_read_out_passes"] is False
    assert result["clock_x1"]["concentrate_fraction_vs_longevity"] > 0.7


def test_spearman_uses_average_ranks_and_rejects_constant_input():
    assert pp.average_ranks([3, 1, 1, 2]) == [4.0, 1.5, 1.5, 3.0]
    assert pp.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert pp.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert pp.spearman([1, 2, 3], [5, 5, 5]) is None


def test_fit_read_out_picks_the_dilution_that_ranks_and_holds_out_each_item():
    labels = [1.0, 2.0, 3.0, 4.0, 5.0]
    table = {1.0: [5, 4, 3, 2, 1], 1e-2: [1, 2, 3, 4, 5], 1e-4: [0, 0, 0, 0, 0]}
    res = pp.fit_read_out(labels, table)
    assert res["dilution"] == 1e-2
    assert res["spearman"] == pytest.approx(1.0)
    assert res["leave_one_out_spearman"] == pytest.approx(1.0)


def test_hours_until_faint_and_strength_follow_the_diluted_oav():
    run = _run({0: {"a": 1e6, "b": 1e3}, 1: {"a": 1e5, "b": 10}, 2: {"a": 1e3, "b": 1}, 4: {"a": 10, "b": 0}})
    assert pp.hours_until_faint(run, 1.0) == 4.0  # never below 1 within the horizon: censored
    assert 1.0 < pp.hours_until_faint(run, 1e-4) < 2.0
    assert pp.hours_until_faint(run, 1e-7) == 0.0
    assert pp.strength_at(run, 1e-2, 1.0) == pytest.approx(1e3 ** 0.5)
    assert pp.strength_at(run, 1.0, 1.0, exponent=1.0) == pytest.approx(1e5 + 10)


def test_build_drop_reasons_are_parse_validity_only():
    ok = _run({0: {"a": 1.0, "b": 2.0}}, ul=4000.0)
    assert pp.build_drop_reason(ok) is None
    assert "rows" in pp.build_drop_reason(_run({0: {"a": 1.0}}, ul=4000.0, rows=4))
    assert "concentrate" in pp.build_drop_reason(_run({0: {"a": 1.0}}, ul=500.0))
    assert "OAV" in pp.build_drop_reason(_run({0: {"a": 1.0, "b": 2.0}}, ul=4000.0, no_oav=("a",)))
    assert "10 mL" in pp.build_drop_reason(_run({0: {"a": 1.0}}, ul=4000.0, path="Thing_10mL_EdP.md"))


def test_strip_clock_check_ranks_against_tgsc_with_injected_life():
    recs = [{"material": m, "hours": h} for m, h in (("a", 4), ("b", 24), ("c", 168), ("d", 400))]
    life = {"a": 2.0, "b": 30.0, "c": 150.0, "d": 4000.0}
    res = pp.strip_clock_check(recs, life=life.__getitem__)
    assert res.n == 4 and res.spearman == pytest.approx(1.0)
    assert res.median_ratio_tgsc_over_model == pytest.approx(1.0, rel=0.3)


def test_gate_strip_clock_empties_limonene_in_hours():
    hours = pp.strip_life_hours("D-Limonene", hours=(0, 0.25, 0.5, 1, 2, 4, 8))
    assert 0.25 < hours < 4.0  # TGSC prints 4 h


def test_simulate_build_runs_a_repo_reconstruction_through_the_gate():
    run = pp.simulate_build(REPO / "formulas/L_Homme_Realistic_Reconstruction_30mL_EDT.md", hours=(0, 1, 6))
    assert pp.build_drop_reason(run) is None
    assert run.concentrate_fraction == pytest.approx(0.122, abs=0.01)
    assert pp.strength_at(run, 1.0, 1.0) > pp.strength_at(run, 1e-4, 1.0) >= 0.0


def _volume_run(ul_by_hour, batch_ml=30.0):
    hours = tuple(float(h) for h in ul_by_hour)
    frames = tuple(dict(v) for v in ul_by_hour.values())
    return pp.BuildRun(
        path="x.md", hours=hours, batch_ml=batch_ml, rows=10,
        oav=tuple({n: 1.0 for n in f} for f in frames), active_ul=frames, no_oav_rows=(),
    )


def test_round_two_read_outs_use_only_volumes():
    run = _volume_run({
        0: {"top": 600.0, "heart": 300.0, "base": 300.0},
        0.5: {"top": 300.0, "heart": 300.0, "base": 300.0},
        1.5: {"top": 0.0, "heart": 270.0, "base": 300.0},
        6: {"top": 0.0, "heart": 150.0, "base": 300.0},
    })
    assert pp.oil_left_ul_per_ml(run) == pytest.approx(450.0 / 30.0)
    assert pp.oil_flux_ul_per_ml_h(run) == pytest.approx(330.0 / 30.0)
    vp = {"top": 50.0, "heart": 0.2, "base": 0.01}
    assert pp.long_lasting_ul_per_ml(run, vp.get) == pytest.approx(300.0 / 30.0)


def test_long_lasting_line_matches_the_composer():
    from engine.research import composition_planner

    assert pp.LONG_LASTING_VP_25C_PA == float(composition_planner.LONG_LASTING_VP_25C_PA)


def test_judged_bottles_need_both_weak_bottles_below_the_six_hour_bottle():
    assert pp.judged_bottles_pass({"six_hour_bottle": 160.0, "cedrat_r32": 150.0, "lhomme_luxe_edt": 90.0})
    assert not pp.judged_bottles_pass({"six_hour_bottle": 160.0, "cedrat_r32": 170.0, "lhomme_luxe_edt": 90.0})


def test_round_two_was_declared_before_its_result_and_no_read_out_passes():
    bm = pp.load_benchmark()
    declared = bm["declared_round2"]
    result = bm["result_20261107_round2"]
    assert set(declared["read_outs"]) == set(pp.PHYSICS_READ_OUTS) == set(result["read_outs"])
    assert result["any_read_out_passes"] is False
    oil = result["read_outs"]["oil_left_6h_ul_per_ml"]
    assert oil["labels_pass"] is True and oil["judged_bottles_pass"] is False
    assert oil["spearman"] > oil["concentrate_fraction_spearman"]
    assert oil["judged_bottles"] == pp.OIL_LEFT_RECORD["judged_bottles_ul_per_ml"]
    assert pp.OIL_LEFT_RECORD["public_longevity_spearman"] == round(oil["spearman"], 2)
    for bottle in bm["judged_bottles"].values():
        assert bottle["model"].startswith("project:")


def test_oil_left_contract_runs_on_a_gate_state_and_never_raises():
    from engine.pipeline.gates import ReleaseGateConfig, _gate_formula_state, _resolve_gate_config

    path = REPO / "formulas" / "L_Homme_Realistic_Reconstruction_30mL_EDT.md"
    run = pp.simulate_build(path, hours=(0.0, 6.0))
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    from verify_formula_workflow import parse_formula_markdown

    formula = max(parse_formula_markdown(path), key=lambda f: len(f.get("ingredients_ul") or {}))
    state, _, _ = _gate_formula_state(formula, _resolve_gate_config(formula, ReleaseGateConfig()))
    contract = pp.oil_left_contract(state)
    assert contract["ul_per_ml"] == pytest.approx(round(pp.oil_left_ul_per_ml(run), 1))
    assert contract["status"] == pp.OIL_LEFT_STATUS
    broken = pp.oil_left_contract(object())
    assert broken["ul_per_ml"] is None and broken["unavailable_reason"]
