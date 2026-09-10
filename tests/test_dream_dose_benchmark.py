"""DREAM diagnostics must preserve doses and prevent molecule leakage."""

import json

import pandas as pd
import pytest

from scripts import train_odor_predictor as cli


def observations():
    return pd.DataFrame([
        {"Compound Identifier": cid, "Dilution": dilution,
         "INTENSITY/STRENGTH": value, "VALENCE/PLEASANTNESS": None}
        for cid in range(1, 7)
        for dilution, value in [("1/10", 80.0), ("1/1,000 ", 40.0)]
    ])


def test_dose_model_recovers_signal_without_molecule_leakage():
    assert hasattr(cli, "benchmark_dream_dose")
    result = cli.benchmark_dream_dose(observations(), folds=3, seed=42)
    endpoint = result["endpoints"]["INTENSITY/STRENGTH"]
    assert endpoint["models"]["linear"]["rmse"] < 1e-9
    assert endpoint["models"]["intercept"]["rmse"] == pytest.approx(20)
    assert endpoint["models"]["linear"]["dose_ordering"]["correct"] == 6
    for fold in result["folds"]:
        assert not set(fold["train_cids"]) & set(fold["test_cids"])
    assert result["molecule_dose_rows"] == 12
    assert endpoint["fitted_models"]["linear"]["coefficients"] == pytest.approx([100, 20])
    assert result["endpoints"]["VALENCE/PLEASANTNESS"]["status"] == "NO_OBSERVATIONS"
    json.dumps(result, allow_nan=False)


def test_missing_endpoint_rows_are_not_zero_labels():
    assert hasattr(cli, "benchmark_dream_dose")
    frame = observations()
    frame.loc[0, "INTENSITY/STRENGTH"] = None
    result = cli.benchmark_dream_dose(frame, folds=3, seed=42)
    endpoint = result["endpoints"]["INTENSITY/STRENGTH"]
    assert endpoint["n_observations"] == 11
    assert endpoint["models"]["linear"]["rmse"] < 1e-9
    assert endpoint["models"]["linear"]["dose_ordering"]["n_pairs"] == 5


def test_duplicate_observations_do_not_create_extra_dose_groups():
    assert hasattr(cli, "benchmark_dream_dose")
    frame = observations()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    result = cli.benchmark_dream_dose(frame, folds=3, seed=42)
    assert result["molecule_dose_rows"] == 12
    assert result["endpoints"]["INTENSITY/STRENGTH"]["n_observations"] == 12


@pytest.mark.parametrize("dilution", ["0/10", "1/0", "unknown", "1/-10"])
def test_invalid_dilution_refused(dilution):
    assert hasattr(cli, "benchmark_dream_dose")
    frame = observations()
    frame.loc[0, "Dilution"] = dilution
    with pytest.raises(ValueError):
        cli.benchmark_dream_dose(frame, folds=3)
