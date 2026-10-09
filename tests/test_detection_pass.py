"""Detection pass: raise silent roles within limits, conserve volume, report honestly."""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.formulation_intelligence import detection_pass as dp

WINDOWS = dp.WINDOWS


def _row(i, name, amount, role, note, slot, unit="uL"):
    return {
        "row_id": f"r{i}", "identity_name": name, "material": name, "amount_decimal": str(amount),
        "amount_unit": unit, "stock_fraction_decimal": "1", "role": role, "note": note, "slot": slot,
        "stock_id": f"s{i}",
    }


def _formula():
    return {"rows": [
        _row(0, "Lead", 500, "character", "heart", "facet_lead"),
        _row(1, "Quiet", 50, "structure", "base", "base_wood_layer"),
        _row(2, "NoOdt", 100, "modifier", "base", "facet_smoke"),
        _row(3, "Filler", 1000, "volume", "heart", "diffusion_texture"),
        _row(4, "Loud", 300, "texture", "top", "top_green_layer"),
        _row(5, "Crystal", 40, "structure", "base", "base_amber", unit="mg"),
    ], "separate_totals": {"liquid_total_ul": "1950", "mass_total_mg": "40"}}


OAV_PER_UL = {"Lead": 0.01, "Quiet": 0.01, "NoOdt": None, "Filler": 0.01, "Loud": 1.0}


def _fake_simulate(rows, amounts):
    out = {}
    for i, amount in amounts.items():
        name = rows[i]["identity_name"]
        per = OAV_PER_UL[name]
        out[name] = {w: (None if per is None else float(amount) * per) for w in WINDOWS}
    return out


@pytest.fixture
def patched(monkeypatch):
    caps = {"Quiet": (Decimal(400), "role cap (8% of the formula)")}
    fails: dict[str, object] = {"rule": lambda formula: set()}
    monkeypatch.setattr(dp, "_simulate", _fake_simulate)
    monkeypatch.setattr(
        dp, "_row_cap",
        lambda row, role, index, total: caps.get(row["identity_name"], (Decimal(5000), "role cap")),
    )
    monkeypatch.setattr(dp, "_blocking_checks", lambda formula, name: fails["rule"](formula))
    return caps, fails


def _run():
    return dp.apply_detection_pass(
        _formula(), role_plan=None, interpretation={}, formula_name="t", index=[object()],
    )


def _status(result, name):
    return next(e for e in result["detection_check"]["roles"] if e["material"] == name)


def _liquid(result):
    return sum(Decimal(r["amount_decimal"]) for r in result["rows"] if r["amount_unit"] == "uL")


def test_silent_role_is_raised_and_volume_is_conserved(patched):
    result = _run()
    quiet = _status(result, "Quiet")
    assert quiet["status"] == "raised"
    assert (quiet["dose_before_ul"], quiet["dose_after_ul"]) == ("50", "100")
    assert quiet["max_screening_oav_in_intended_windows"] >= 1
    assert _liquid(result) == Decimal(1950)
    # The volume/diffusion row gives the added microlitres first.
    filler = next(r for r in result["rows"] if r["identity_name"] == "Filler")
    assert filler["amount_decimal"] == "950"
    assert result["detection_check"]["liquid_total_ul_after"] == "1950"


def test_capped_role_reports_silent_at_cap_with_limit(patched):
    caps, _ = patched
    caps["Quiet"] = (Decimal(60), "normal-use ceiling")
    quiet = _status(_run(), "Quiet")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "normal-use ceiling"
    assert quiet["dose_after_ul"] == "60"


def test_missing_threshold_is_not_silent(patched):
    result = _run()
    entry = _status(result, "NoOdt")
    assert entry["status"] == "no_threshold_data"
    assert entry["dose_after_ul"] == "100"
    assert _status(result, "Crystal")["status"] == "not_checked"


def test_raise_that_creates_ifra_fail_is_rejected(patched):
    _, fails = patched

    def rule(formula):
        dose = next(Decimal(r["amount_decimal"]) for r in formula["rows"] if r["identity_name"] == "Quiet")
        return {"ifra: Quiet exceeds its IFRA Cat 4 limit"} if dose > 80 else set()

    fails["rule"] = rule
    result = _run()
    quiet = _status(result, "Quiet")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "IFRA Cat 4"
    assert Decimal(quiet["dose_after_ul"]) <= 80
    assert rule(result) == set()


def test_unnamed_material_far_above_lead_is_flagged_only(patched):
    result = _run()
    flags = result["detection_check"]["flags"]
    assert [f["material"] for f in flags] == ["Loud"]
    assert flags[0]["windows"] == ["heart", "late_heart"]
    loud = next(r for r in result["rows"] if r["identity_name"] == "Loud")
    assert loud["amount_decimal"] == "300"
    assert "not loudness" in result["detection_check"]["note"]


def test_solver_formula_restores_and_rejects_tampering(patched):
    result = _run()
    restored = dp.solver_formula(result)
    assert [r["amount_decimal"] for r in restored["rows"]] == [r["amount_decimal"] for r in _formula()["rows"]]
    assert "detection_check" not in restored
    result["rows"][1]["amount_decimal"] = "101"
    with pytest.raises(ValueError):
        dp.solver_formula(result)


def test_intended_window_mapping():
    assert dp.intended_windows({"role": "texture", "note": "top"}) == ("opening", "top")
    assert dp.intended_windows({"role": "modifier", "note": "top"}) == ("opening", "top")
    assert dp.intended_windows({"role": "character", "note": "base"}) == ("late_heart", "drydown")
    assert dp.intended_windows({"role": "structure", "note": "base"}) == ("drydown",)
    assert dp.intended_windows({"role": "bridge", "note": "heart"}) == ("top", "heart", "late_heart", "drydown")
