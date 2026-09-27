"""Published numeric examples and domain boundaries for measured intensity curves."""
import math
from copy import deepcopy

import pytest

from engine import dose_response


def function(name):
    value = getattr(dose_response, name, None)
    assert callable(value), f"Missing measured-data function: {name}"
    return value


def _exact_limonene_capability():
    loaded = function("load_measured_intensity_capabilities")()
    capability = deepcopy(loaded["curves"]["138-86-3"])
    capability["chemical_identity"].update(
        {
            "canonical_name": "Limonene",
            "canonical_cas": "138-86-3",
            "identity_status": "EXACT",
        }
    )
    capability["applicability"].update(
        {
            "observed_range_ug_l_air": [0.01, 1000.0],
            "exact_material_ids": ["stock-limonene-exact"],
            "matrices": ["source-gas-matrix"],
            "delivery_modes": ["source-delivery"],
            "scenarios": ["source-single-material"],
        }
    )
    return capability


def _exact_context(**changes):
    context = {
        "canonical_name": "Limonene",
        "canonical_cas": "138-86-3",
        "material_id": "stock-limonene-exact",
        "physical_quantity": "GAS_MASS_CONCENTRATION",
        "phase": "AIR",
        "unit": "ug/L_air",
        "gas_ug_l_air": 1.0,
        "matrix": "source-gas-matrix",
        "delivery": "source-delivery",
        "scenario": "source-single-material",
        "commercial_use": False,
    }
    context.update(changes)
    return context


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


def test_corrected_wakayama_threshold_round_trips_at_1_4_lms():
    threshold = function("corrected_wakayama_threshold_ng_l")(
        imax=52.62,
        midpoint_log10_ug_l=1.71,
        slope=0.50,
    )
    # Equation 3 returns ng/L; the forward OISC consumes micrograms/L.
    response = function("measured_intensity_curve")(
        threshold / 1000.0,
        imax=52.62,
        midpoint_log10_ug_l=1.71,
        slope=0.50,
    )
    assert response == pytest.approx(1.4, abs=1e-12)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"imax": 1.4, "midpoint_log10_ug_l": 0.0, "slope": 0.5},
        {"imax": 40.0, "midpoint_log10_ug_l": 0.0, "slope": 0.0},
        {"imax": 40.0, "midpoint_log10_ug_l": math.inf, "slope": 0.5},
        {"imax": 40.0, "midpoint_log10_ug_l": 1000.0, "slope": 0.5},
    ],
)
def test_corrected_wakayama_threshold_rejects_invalid_source_parameters(kwargs):
    with pytest.raises(ValueError):
        function("corrected_wakayama_threshold_ng_l")(**kwargs)


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


def test_capability_requires_source_transcription_hashes_license_and_exact_units():
    loaded = function("load_measured_intensity_capabilities")()

    assert loaded["status"] == "HOLD"
    assert len(loaded["curves"]) == 314
    capability = _exact_limonene_capability()
    admitted = function("validate_measured_intensity_capability")(
        capability, _exact_context()
    )
    assert admitted["usable"] is True
    assert admitted["optimizer_selection_usable"] is False
    assert "SOURCE_FIT_OVERLAP_UNKNOWN" in admitted["caveat_codes"]
    assert "UNCERTAINTY_METHOD_UNAVAILABLE" in admitted["caveat_codes"]

    wrong_hash = deepcopy(capability)
    wrong_hash["source_artifact_sha256"] = "0" * 64
    rejected = function("validate_measured_intensity_capability")(
        wrong_hash, _exact_context()
    )
    assert "SOURCE_ARTIFACT_HASH_MISMATCH" in rejected["reason_codes"]


def test_known_cas_name_conflict_is_withheld_not_auto_mapped():
    capability = function("load_measured_intensity_capabilities")()["curves"][
        "140-88-5"
    ]
    result = function("validate_measured_intensity_capability")(
        capability,
        _exact_context(
            canonical_name="2,6-nonadienal",
            canonical_cas="140-88-5",
            material_id="source-row",
        ),
    )

    assert result["usable"] is False
    assert "SOURCE_IDENTITY_CONFLICT" in result["reason_codes"]
    assert "CAS_NAME_CONFLICT" in result["reason_codes"]


def test_exact_stock_identity_source_range_and_gas_units_are_required():
    capability = _exact_limonene_capability()
    validate = function("validate_measured_intensity_capability")

    assert validate(capability, _exact_context(gas_ug_l_air=2000.0))["status"] == "HOLD"
    direct_liquid = validate(
        capability,
        _exact_context(
            physical_quantity="LIQUID_STOCK_VOLUME",
            phase="LIQUID",
            unit="uL",
        ),
    )
    assert "UNIT_NOT_GAS_UG_L_AIR" in direct_liquid["reason_codes"]
    natural = validate(capability, _exact_context(whole_natural=True))
    assert "WHOLE_NATURAL_CALIBRATION_ABSENT" in natural["reason_codes"]


def test_partial_addition_boundaries_and_training_only_fit():
    partial = function("partial_addition_intensity")
    assert partial([8.0, 3.0, 1.0], lambda_=0.0, upper_bound=10.0) == 8.0
    assert partial([8.0, 3.0, 1.0], lambda_=1.0, upper_bound=10.0) == 10.0

    training = [
        {
            "group_id": "g1",
            "component_intensities": [8.0, 2.0],
            "observed": 8.5,
            "upper_bound": 20.0,
        },
        {
            "group_id": "g2",
            "component_intensities": [6.0, 4.0],
            "observed": 7.0,
            "upper_bound": 20.0,
        },
        {
            "group_id": "g3",
            "component_intensities": [4.0, 1.0],
            "observed": 4.25,
            "upper_bound": 20.0,
        },
    ]
    fit = function("fit_partial_addition_lambda")(training)
    assert fit["lambda"] == pytest.approx(0.25)
    assert fit["empirical_admission"] == "HOLD"
    # Held-out labels are not an input to the fit and therefore cannot alter it.
    held_out = {"observed": -999.0}
    held_out["observed"] = 999.0
    assert function("fit_partial_addition_lambda")(training)["lambda"] == fit["lambda"]


def test_partial_addition_refuses_unidentifiable_training_groups():
    result = function("fit_partial_addition_lambda")(
        [
            {
                "group_id": "g1",
                "component_intensities": [2.0, 1.0],
                "observed": 2.5,
                "upper_bound": 10.0,
            },
            {
                "group_id": "g2",
                "component_intensities": [2.0, 1.0],
                "observed": 2.5,
                "upper_bound": 10.0,
            },
        ]
    )
    assert result["status"] == "HOLD_PARTIAL_ADDITION_IDENTIFIABILITY"
    assert result["lambda"] is None


def test_three_models_remain_separate_and_missing_curve_abstains_whole_mixture():
    curves = {
        key: {"imax": 40.0, "midpoint_log10_ug_l": -1.0, "slope": 0.5}
        for key in ("a", "b")
    }
    compare = function("measured_mixture_intensity_challengers")
    complete = compare(
        {"a": 0.5, "b": 0.25},
        curves,
        partial_addition_lambda=0.25,
        upper_bound=40.0,
    )
    assert complete["models_averaged"] is False
    assert complete["strongest_component"]["intensity"] is not None
    assert complete["partial_addition"]["intensity"] is not None
    assert complete["primacy_transfer"]["status"] == "EXTERNAL_TRANSFER"
    assert complete["predicted_liking"] is None

    withheld = compare(
        {"a": 0.5, "missing": 0.25},
        curves,
        partial_addition_lambda=0.25,
        upper_bound=40.0,
    )
    assert withheld["status"] == "HOLD_MISSING_COMPONENT_CALIBRATION"
    assert withheld["strongest_component"] is None
    assert withheld["partial_addition"] is None
    assert withheld["primacy_transfer"] is None


def test_molecule_connected_groups_never_split_shared_chemical_identity():
    result = function("molecule_connected_mixture_groups")(
        [
            {"mixture_id": "a-ratio-1", "molecule_ids": ["x", "y"]},
            {"mixture_id": "a-ratio-2", "molecule_ids": ["y", "z"]},
            {"mixture_id": "b", "molecule_ids": ["q"]},
            {"mixture_id": "c", "molecule_ids": ["r"]},
        ]
    )
    assert result["status"] == "LEAKAGE_SAFE_GROUPS_AVAILABLE"
    assert result["groups"]["a-ratio-1"] == result["groups"]["a-ratio-2"]
    assert len(set(result["groups"].values())) == 3


def test_grouped_three_model_benchmark_fits_lambda_inside_training_folds_only():
    curve = {"imax": 40.0, "midpoint_log10_ug_l": -1.0, "slope": 0.5}
    curves = {molecule: dict(curve) for molecule in "abcdefgh"}
    rows = [
        {
            "row_id": f"row-{index}",
            "mixture_id": f"mixture-{index}",
            "molecule_ids": [left, right],
            "gas_ug_l_by_cas": {left: gas, right: gas / (index + 1)},
            "observed": 15.0 + index,
        }
        for index, (left, right, gas) in enumerate(
            [
                ("a", "b", 0.1),
                ("c", "d", 0.2),
                ("e", "f", 0.4),
                ("g", "h", 0.8),
            ],
            start=1,
        )
    ]
    result = function("benchmark_grouped_mixture_intensity_challengers")(
        rows,
        curves,
        upper_bound=40.0,
        bootstrap_draws=100,
        bootstrap_seed=17,
    )

    assert result["status"] == "MODEL_COMPARISON_EVALUATED_ADMISSION_HOLD"
    assert result["empirical_admission"] == "HOLD"
    assert result["winner"] is None
    assert result["identical_held_out_rows"] is True
    assert len(result["folds"]) == 4
    for fold in result["folds"]:
        assert fold["held_out_group"] not in fold["training_groups"]
        assert fold["lambda_fit"]["empirical_admission"] == "HOLD"
    assert {
        metrics["valid_prediction_count"]
        for metrics in result["metrics"].values()
    } == {4}
    assert result["partial_addition_lambda_bootstrap"]["draws_requested"] == 100
    assert result["formula_optimization_authority"] is False
    assert result["beauty_authorized"] is False


def test_grouped_benchmark_holds_when_connected_graph_has_too_few_groups():
    curve = {"imax": 40.0, "midpoint_log10_ug_l": -1.0, "slope": 0.5}
    result = function("benchmark_grouped_mixture_intensity_challengers")(
        [
            {
                "mixture_id": "one",
                "molecule_ids": ["a", "b"],
                "gas_ug_l_by_cas": {"a": 0.1, "b": 0.2},
                "observed": 10.0,
            },
            {
                "mixture_id": "two",
                "molecule_ids": ["b", "c"],
                "gas_ug_l_by_cas": {"b": 0.1, "c": 0.2},
                "observed": 11.0,
            },
        ],
        {key: dict(curve) for key in ("a", "b", "c")},
        upper_bound=40.0,
        bootstrap_draws=10,
    )
    assert result["status"] == "HOLD_INSUFFICIENT_LEAKAGE_SAFE_GROUPS"
    assert result["winner"] is None
