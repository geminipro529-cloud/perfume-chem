import pytest

from engine.pipeline.antioxidant import (
    HOUSE_BHT_STOCK,
    house_bht_precharge,
    is_antioxidant_row,
)


def test_house_dose_is_120_ul_per_30_ml():
    row = house_bht_precharge(30.0)
    assert row.material == HOUSE_BHT_STOCK
    assert row.raw_ul == 120.0
    assert row.bht_mg == 6.0
    assert row.operation == "PRECHARGE"


def test_house_dose_scales_with_batch_volume():
    assert house_bht_precharge(50.0).raw_ul == 200.0
    assert house_bht_precharge(10.0).raw_ul == 40.0


def test_non_positive_volume_is_rejected():
    with pytest.raises(ValueError):
        house_bht_precharge(0.0)


@pytest.mark.parametrize(
    "name",
    ["BHT", "BHT 5% w/v in ethanol", "Butylated Hydroxytoluene", "alpha-Tocopherol", "Tocopherol 50%"],
)
def test_antioxidant_rows_are_recognised(name):
    assert is_antioxidant_row(name)


@pytest.mark.parametrize("name", ["Linalool", "Bergamot FCF Oil Sicilian", "Benzyl Benzoate"])
def test_odour_rows_are_not_antioxidants(name):
    assert not is_antioxidant_row(name)
