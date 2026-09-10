"""Published numeric examples and domain boundaries for measured intensity curves."""
import math

import pytest

from engine import dose_response


def function(name):
    value = getattr(dose_response, name, None)
    assert callable(value), f"Missing measured-data function: {name}"
    return value


@pytest.mark.parametrize("log_g,expected", [(-0.99, 0.2), (1.67, 25.2), (2.90, 48.2)])
def test_curve_reproduces_published_limonene_values(log_g, expected):
    actual = function("measured_intensity_curve")(
        10 ** log_g, imax=52.62, midpoint_log10_ug_l=1.71, slope=0.50)
    assert actual == pytest.approx(expected, abs=0.1)


def test_zero_and_midpoint_and_extreme_concentrations():
    curve = function("measured_intensity_curve")
    kwargs = dict(imax=40., midpoint_log10_ug_l=-1., slope=0.5)
    assert curve(0., **kwargs) == 0.
    assert curve(.1, **kwargs) == 20.
    assert curve(1e300, **kwargs) == pytest.approx(40.)
    assert curve(1e-300, **kwargs) == pytest.approx(0.)


@pytest.mark.parametrize("change", [dict(slope=0), dict(slope=-1), dict(imax=math.nan),
                                    dict(gas_ug_l=-1), dict(midpoint_log10_ug_l=math.inf)])
def test_singular_or_invalid_coefficients_are_not_silently_repaired(change):
    kwargs = dict(gas_ug_l=1., imax=40., midpoint_log10_ug_l=0., slope=.5)
    kwargs.update(change)
    with pytest.raises(ValueError):
        function("measured_intensity_curve")(**kwargs)


def test_air_ppm_conversion_uses_molecular_weight_temperature_and_pressure():
    convert = function("air_ppm_to_ug_l")
    assert convert(1., mw_g_mol=100., temperature_k=298.15) == pytest.approx(4.0874, rel=1e-4)
    assert convert(1., mw_g_mol=100., temperature_k=596.30) == pytest.approx(2.0437, rel=1e-4)
    with pytest.raises(ValueError):
        convert(1., mw_g_mol=0.)


def test_primary_parameter_file_loads_without_overwriting_duplicate_cas():
    rows = [{"CAS": "1", "Name": "example", "I_max": "40", "C": "-1", "D": "0.5"}]
    load = function("parse_measured_intensity_parameters")
    result = load(rows)
    assert result["curves"]["1"]["imax"] == 40.
    singular = load([{**rows[0], "D": "0"}])
    assert singular["curves"] == {}
    assert singular["excluded"][0]["reason"] == "NONPOSITIVE_SLOPE"
    with pytest.raises(ValueError, match="Duplicate"):
        load(rows + rows)


def test_mixture_rules_are_not_liking_and_zero_components_do_not_add_signal():
    predict = function("measured_mixture_intensity")
    curves = {"1": dict(imax=40., midpoint_log10_ug_l=-1., slope=.5)}
    strongest = predict({"1": .1}, curves, method="strongest_component")
    assert strongest["intensity"] == 20.
    assert strongest["predicted_liking"] is None
    assert strongest["missing_calibrations"] == []
    assert predict({"1": 0.}, curves, method="primacy")['intensity'] == 0.
    assert predict({"1": .1, "unknown": 0.}, curves, method="primacy") == predict(
        {"1": .1}, curves, method="primacy")
    assert predict({"unknown": .1}, curves, method="primacy")["intensity"] is None


def test_primacy_reproduces_logsumexp_not_normalized_average():
    curves = {key: dict(imax=40., midpoint_log10_ug_l=-1., slope=.5) for key in ["a", "b"]}
    result = function("measured_mixture_intensity")({"a": .5, "b": .5}, curves, method="primacy")
    assert result["intensity"] == pytest.approx(20.69314718056)
    assert result["model_domain_warning"]


def test_benchmark_uses_human_observations_separate_from_published_predictions():
    curves = {"1": dict(imax=40., midpoint_log10_ug_l=0., slope=.5)}
    data = {"single_component_series": [{"cas":"1", "name":"example", "log_g":[0.],
             "observed":[18.], "published_prediction":[20.]}],
            "mixture_series": [{"id":"A", "cas":["1"], "highest_log_g":[0.],
             "log_dilution_offsets":[0.], "observed":[15.], "published_prediction":[20.]}]}
    result = function("benchmark_measured_intensity")(curves, data)
    assert result["single"]["pooled_rmse"] == 2.
    assert result["mixtures"]["strongest_component"]["pooled_rmse"] == 5.
    assert result["single"]["published_prediction_max_abs_difference"] == 0.
    assert result["parameters_fitted"] is False
    assert result["source_training_observation_overlap"] == "NOT_ESTABLISHED"
    assert result["mixtures"]["primacy"]["published_reference_method"] == "strongest_component"


@pytest.mark.parametrize("defect", ["empty", "nonfinite", "duplicate_cas"])
def test_malformed_benchmark_data_is_rejected(defect):
    curves = {"1": dict(imax=40., midpoint_log10_ug_l=0., slope=.5)}
    data = {"single_component_series": [{"cas": "1", "name": "example", "log_g": [0.],
             "observed": [18.], "published_prediction": [20.]}],
            "mixture_series": [{"id": "A", "cas": ["1"], "highest_log_g": [0.],
             "log_dilution_offsets": [0.], "observed": [15.], "published_prediction": [20.]}]}
    if defect == "empty":
        data["single_component_series"] = []
    elif defect == "nonfinite":
        data["single_component_series"][0]["observed"] = [math.nan]
    else:
        data["mixture_series"][0].update(cas=["1", "1"], highest_log_g=[0., 0.])
    with pytest.raises(ValueError):
        function("benchmark_measured_intensity")(curves, data)
