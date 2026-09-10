import pytest

from engine import hedonic_model as model

TARGET = {"required": ["juniper", "vetiver"],
          "minimum_ul": {"vetiver": 400.},
          "maximum_ratios": [{"numerator": "cypress", "denominator": "juniper", "maximum": .1}]}
BASE = {"juniper": 750., "vetiver": 700., "cypress": 50., "support": 500.}


def evaluate(formula=BASE, **kwargs):
    assert hasattr(model, "evaluate_targeted_hedonics")
    return model.evaluate_targeted_hedonics(formula, target=TARGET, **kwargs)


def test_baseline_has_separate_identity_liking_and_confidence():
    result = evaluate()
    assert result["target_identity"]["status"] == "PASS_DESIGN_CONSTRAINTS"
    assert result["target_identity"]["perceptual_fit"] == "NOT_ESTABLISHED"
    assert result["predicted_liking"]["score"] is None
    assert result["confidence"]["matched_material_fraction"] == 0.
    assert result["requires_premix_trial"] is False


@pytest.mark.parametrize("change", [{"juniper": 0.}, {"vetiver": 0.}, {"cypress": 500.}])
def test_identity_breaks_are_not_hidden_by_pleasant_support(change):
    result = evaluate({**BASE, **change})
    assert result["target_identity"]["status"] == "FAIL_DESIGN_CONSTRAINTS"
    assert result["target_identity"]["violations"]
    assert result["optimization_eligible"] is False


def evidence(intensity, pleasantness, ppm=100.):
    return {"intensity": intensity, "pleasantness": pleasantness,
            "concentration_ppm": ppm, "context": "air:25C:opening:cohort-A",
            "source": "fixture:hand-checked-human-observation"}


def binary(**overrides):
    assert hasattr(model, "evaluate_targeted_hedonics")
    kwargs = dict(target={"required": ["A", "B"]},
                  evidence={"A": evidence(1., 20.), "B": evidence(3., 80.)},
                  concentrations_ppm={"A": 100., "B": 100.},
                  context="air:25C:opening:cohort-A")
    kwargs.update(overrides)
    return model.evaluate_targeted_hedonics({"A": 10., "B": 10.}, **kwargs)


def test_binary_prediction_is_intensity_weighted_not_volume_weighted():
    result = binary()
    assert result["predicted_liking"]["score"] == 65.
    assert result["predicted_liking"]["status"] == "EXPERIMENTAL_ESTIMATE"
    assert result["confidence"]["matched_material_fraction"] == 1.
    assert result["optimization_eligible"] is False


def test_unknown_rows_cannot_disappear_from_denominator():
    result = binary(evidence={"A": evidence(1., 20.)})
    assert result["predicted_liking"]["score"] is None
    assert result["confidence"]["matched_material_fraction"] == .5
    assert result["confidence"]["unmatched"] == {"B": "missing_evidence"}


@pytest.mark.parametrize("override,reason", [
    ({"context": "skin:35C:drydown:cohort-B"}, "context_mismatch"),
    ({"concentrations_ppm": {"A": 200., "B": 100.}}, "concentration_mismatch"),
    ({"concentrations_ppm": None}, "missing_concentration"),
])
def test_mismatched_evidence_cannot_predict_a_new_condition(override, reason):
    result = binary(**override)
    assert result["predicted_liking"]["score"] is None
    assert result["confidence"]["unmatched"]["A"] == reason


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1., 101.])
def test_invalid_pleasantness_is_not_a_good_score(invalid):
    result = binary(evidence={"A": evidence(1., invalid), "B": evidence(3., 80.)})
    assert result["predicted_liking"]["score"] is None


def test_evidence_without_provenance_is_unavailable():
    row = evidence(1., 20.)
    row["source"] = ""
    assert binary(evidence={"A": row, "B": evidence(3., 80.)})["predicted_liking"]["score"] is None


def test_larger_mixture_is_not_automatically_a_validated_binary_model():
    result = evaluate(evidence={k: evidence(1., 80.) for k in BASE},
                      concentrations_ppm={k: 100. for k in BASE},
                      context="air:25C:opening:cohort-A")
    assert result["predicted_liking"]["score"] is None
    assert result["predicted_liking"]["status"] == "OUT_OF_MODEL_SCOPE"


def test_search_adapter_does_not_promote_experimental_or_missing_data():
    assert hasattr(model, "targeted_hedonic_losses")
    with pytest.raises(ValueError, match="not admitted"):
        model.targeted_hedonic_losses(binary())


def test_malformed_formula_is_rejected():
    with pytest.raises(ValueError):
        evaluate({**BASE, "support": -1.})


def test_explicit_experimental_search_uses_unrounded_liking_loss():
    assert hasattr(model, "targeted_hedonic_losses")
    assert model.targeted_hedonic_losses(binary(), allow_experimental=True) == {"identity": 0., "liking": 35.}


def test_experimental_permission_cannot_fill_missing_evidence():
    assert hasattr(model, "targeted_hedonic_losses")
    with pytest.raises(ValueError, match="not admitted"):
        model.targeted_hedonic_losses(evaluate(), allow_experimental=True)
