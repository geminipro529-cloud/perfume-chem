from __future__ import annotations

import inspect

import pytest

from engine.fuckups.pre_mix_guard import PreMixGuardError, evaluate_pre_mix_guard
from engine.name_utils import normalize_name
from engine.odor_thresholds import lookup_odt_entry
from engine.pipeline.gates import HARD_BLOCKING_GATES, gate_formula
from engine.pipeline.natural_absolute_decomposition import get_constituents


def frame(label: str, rows: list[tuple[str, float]]) -> dict:
    return {
        "label": label,
        "state": {"materials": [{"name": name, "oav": oav} for name, oav in rows]},
    }


def test_regression_prada_citronellol_10pct_to_neat_same_raw_hard_fails() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Citronellol": 63.0},
        parent_dilutions={"Citronellol": 0.10},
        child_ingredients_ul={"Citronellol": 63.0},
        child_dilutions={"Citronellol": 1.0},
    )
    assert result.status == "FAIL"
    f = next(x for x in result.findings if x.code == "STOCK_REBASE_ACTIVE_EQUIVALENCE")
    assert f.parent_active_ul == pytest.approx(6.3)
    assert f.child_active_ul == pytest.approx(63.0)
    assert f.active_fold_change == pytest.approx(10.0)
    assert "6.3" in f.detail


def test_regression_lemonile_10pct_to_neat_same_raw_hard_fails() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Lemonile": 20.0, "Hedione": 100.0},
        parent_dilutions={"Lemonile": 0.10, "Hedione": 1.0},
        child_ingredients_ul={"Lemonile": 20.0, "Hedione": 100.0},
        child_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        parent_time_series=[
            frame("opening", [("Lemonile", 12.0), ("Hedione", 10.0)]),
            frame("top", [("Lemonile", 8.0), ("Hedione", 7.0)]),
        ],
        child_time_series=[
            frame("opening", [("Lemonile", 120.0), ("Hedione", 10.0)]),
            frame("top", [("Lemonile", 80.0), ("Hedione", 7.0)]),
        ],
    )
    assert result.status == "FAIL"
    f = next(x for x in result.findings if x.code == "STOCK_REBASE_ACTIVE_EQUIVALENCE")
    assert f.active_fold_change == pytest.approx(10.0)
    assert f.max_temporal_oav_fold_change == pytest.approx(10.0)


def test_correct_active_equivalent_rebase_passes() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Citronellol": 63.0},
        parent_dilutions={"Citronellol": 0.10},
        child_ingredients_ul={"Citronellol": 6.3},
        child_dilutions={"Citronellol": 1.0},
    )
    assert result.status == "PASS"


def test_moderate_rebase_drift_warns() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Geraniol": 100.0},
        parent_dilutions={"Geraniol": 0.10},
        child_ingredients_ul={"Geraniol": 18.0},
        child_dilutions={"Geraniol": 1.0},
    )
    assert result.status == "WARN"
    assert result.findings[0].code == "STOCK_REBASE_ACTIVE_DRIFT"


def test_same_stock_10x_dose_hard_fails_without_intent_authority() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Lemonile": 2.0, "Hedione": 100.0},
        parent_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        child_ingredients_ul={"Lemonile": 20.0, "Hedione": 100.0},
        child_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        parent_time_series=[
            frame("opening", [("Lemonile", 10.0), ("Hedione", 8.0)]),
            frame("top", [("Lemonile", 6.0), ("Hedione", 5.0)]),
        ],
        child_time_series=[
            frame("opening", [("Lemonile", 100.0), ("Hedione", 8.0)]),
            frame("top", [("Lemonile", 60.0), ("Hedione", 5.0)]),
        ],
    )
    codes = {x.code for x in result.findings}
    assert result.status == "FAIL"
    assert "ACTIVE_DOSE_REVISION_JUMP" in codes
    assert "STOCK_REBASE_ACTIVE_EQUIVALENCE" not in codes


def test_same_stock_10x_dose_can_only_be_overridden_by_explicit_intent_authority() -> None:
    result = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Lemonile": 2.0, "Hedione": 100.0},
        parent_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        child_ingredients_ul={"Lemonile": 20.0, "Hedione": 100.0},
        child_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        authorized_active_dose_changes={
            "Lemonile": "REV-017 perfumer-approved deliberate 10x active-dose experiment"
        },
    )
    assert result.status == "WARN"
    finding = next(x for x in result.findings if x.code == "AUTHORIZED_ACTIVE_DOSE_CHANGE")
    assert finding.active_fold_change == pytest.approx(10.0)
    assert "REV-017" in finding.detail


def test_persistent_oav_dominance_warns_only() -> None:
    result = evaluate_pre_mix_guard(
        child_ingredients_ul={"Lemonile": 20.0, "Hedione": 100.0},
        child_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        child_time_series=[
            frame("opening", [("Lemonile", 1000.0), ("Hedione", 20.0)]),
            frame("top", [("Lemonile", 600.0), ("Hedione", 20.0)]),
            frame("heart", [("Lemonile", 50.0), ("Hedione", 10.0)]),
        ],
    )
    assert result.status == "WARN"
    assert any(x.code == "PERSISTENT_MODELED_OAV_DOMINANCE" for x in result.findings)


def test_percent_number_instead_of_fraction_is_rejected() -> None:
    with pytest.raises(PreMixGuardError, match="fraction"):
        evaluate_pre_mix_guard(
            child_ingredients_ul={"Lemonile": 1.0},
            child_dilutions={"Lemonile": 10.0},
        )


def test_oav_authority_boundary_is_explicit() -> None:
    report = evaluate_pre_mix_guard(
        child_ingredients_ul={"Lemonile": 1.0},
        child_dilutions={"Lemonile": 1.0},
    ).as_dict()
    limitations = " ".join(report["limitations"]).casefold()
    assert "screening" in limitations
    assert "not percent perceived contribution" in limitations
    assert "target-similarity" in limitations


def test_g15_is_hard_blocking_and_wired_into_gate_formula() -> None:
    assert "g15_oav_firewall" in HARD_BLOCKING_GATES
    source = inspect.getsource(gate_formula)
    assert "_gate_g15_oav_firewall" in source
    assert "parent_formula=parent_formula" in source
    assert "authorized_active_dose_changes=authorized_active_dose_changes" in source


def test_sambac_and_grandiflorum_remain_distinct_across_premix_and_natural_profiles() -> None:
    assert normalize_name("Jasmine Sambac Absolute") == "jasmine sambac absolute"
    assert normalize_name("Jasmine Absolute") == "jasmine absolute"
    assert normalize_name("Jasmine Sambac Absolute") != normalize_name("Jasmine Absolute")
    assert get_constituents("Jasmine Sambac Absolute") != get_constituents("Jasmine Absolute")
    assert lookup_odt_entry("Jasmine Sambac Absolute") == lookup_odt_entry("Jasmine Absolute")

    report = evaluate_pre_mix_guard(
        child_ingredients_ul={
            "Jasmine Sambac Absolute": 100.0,
            "Jasmine Absolute": 100.0,
        },
        child_dilutions={
            "Jasmine Sambac Absolute": 0.10,
            "Jasmine Absolute": 0.10,
        },
    )
    assert report.status == "PASS"
