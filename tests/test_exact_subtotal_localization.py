"""exact_subtotal names the row behind a mismatch instead of reporting only totals."""

from engine.pipeline.gates import ReleaseGateConfig, _gate_exact_subtotal


def _formula(rows: dict[str, float]) -> dict:
    return {"name": "t", "ingredients_ul": rows}


def _config(expected_ul: float) -> ReleaseGateConfig:
    return ReleaseGateConfig(expected_concentrate_ul=expected_ul, audit_enabled=False)


def test_a_decimal_slip_names_the_row_and_its_corrected_amount():
    # Fougere Herbier's pattern: Geraniol typed as 8200 uL where 820 closes the total.
    rows = {"Bergamot FCF": 2000.0, "Geraniol": 8200.0, "Coumarin": 1500.0, "Vetiver EO (India)": 1680.0}

    result = _gate_exact_subtotal(_formula(rows), _config(6000.0))

    assert result.status == "FAIL"
    assert "13380.0 uL parsed; expected 6000.0 uL (7380.0 uL over)" in result.detail
    assert "Geraniol 8200 uL (at 820 uL the total would be 6000 uL)" in result.detail
    assert "Larger than the whole expected concentrate: Geraniol 8200 uL" in result.detail
    suspect = result.data["decimal_shift_suspects"][0]
    assert suspect["material"] == "Geraniol"
    assert suspect["factor"] == "/10"
    assert suspect["total_if_corrected_ul"] == 6000.0
    assert result.data["rows_over_expected"] == [{"material": "Geraniol", "ul": 8200.0}]


def test_a_row_ten_times_too_small_is_found_when_the_total_is_short():
    rows = {"Iso E Super": 3000.0, "Hedione": 2100.0, "Ambroxan": 18.0}

    result = _gate_exact_subtotal(_formula(rows), _config(5280.0))

    assert result.status == "FAIL"
    assert "short" in result.detail
    suspect = result.data["decimal_shift_suspects"][0]
    assert (suspect["material"], suspect["factor"], suspect["corrected_ul"]) == ("Ambroxan", "x10", 180.0)


def test_without_a_single_row_explanation_the_largest_rows_are_listed():
    rows = {"Iso E Super": 3000.0, "Hedione": 2000.0, "Ambroxan": 300.0}

    result = _gate_exact_subtotal(_formula(rows), _config(6000.0))

    assert result.status == "FAIL"
    assert result.data["decimal_shift_suspects"] == []
    assert result.data["rows_over_expected"] == []
    assert "Largest rows: Iso E Super 3000 uL (57%), Hedione 2000 uL (38%), Ambroxan 300 uL (6%)" in result.detail


def test_a_matching_total_still_passes():
    result = _gate_exact_subtotal(_formula({"Hedione": 3000.0, "Iso E Super": 3000.2}), _config(6000.0))

    assert result.status == "PASS"
    assert result.detail == "6000.2 uL"
