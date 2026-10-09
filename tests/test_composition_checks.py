"""Composed formulas carry the release gate's crowding and IFRA findings."""

from engine.formulation_intelligence.composition_checks import composition_checks
from engine.research.formula_design import design_inventory_formula

CHYPRE = {
    "idea": "a panoramic, exceptionally detailed modern chypre with rose, patchouli and oakmoss",
    "formula_name": "Panoramic Chypre",
}
# The composer keeps IFRA-binding stock out of the roles it adds on its own,
# so the damascone FAIL path needs a brief that names the material.
NAMED_DAMASCONE_CHYPRE = {
    "idea": (
        "a panoramic, exceptionally detailed modern chypre with rose, patchouli, "
        "oakmoss and alpha damascone"
    ),
    "formula_name": "Panoramic Chypre",
}


def _flagged(checks: dict) -> list[dict]:
    return [c for c in checks["checks"] if c["status"] in {"WARN", "FAIL"}]


def test_composed_chypre_carries_the_gate_ifra_fail_for_alpha_damascone() -> None:
    unnamed = design_inventory_formula(**CHYPRE)
    assert not any(
        "damascone" in row["material"].casefold() for row in unnamed["optimized_formula"]["rows"]
    )
    report = design_inventory_formula(**NAMED_DAMASCONE_CHYPRE)

    checks = report["composition_checks"]
    assert "30 mL" in checks["basis"]
    assert {c["check"] for c in checks["checks"]} >= {"hedione_share", "musk_count", "ifra"}
    fails = [c["message"] for c in checks["checks"] if c["check"] == "ifra" and c["status"] == "FAIL"]
    assert any(m.startswith("Alpha Damascone at ") and "IFRA Category 4 limit" in m for m in fails)
    # Advisory only: the design decision is untouched.
    assert report["status"].startswith("INVENTORY_GROUNDED_DESIGN_READY")
    assert report["design_variants"][0]["composition_checks"] == checks


def test_every_deep_compose_variant_carries_its_own_checks() -> None:
    report = design_inventory_formula(**CHYPRE, design_mode="DEEP_COMPOSE", variant_count=3)

    assert report["design_variants"]
    for variant in report["design_variants"]:
        assert variant["composition_checks"]["checks"]


def test_a_brief_within_limits_gets_pass_entries() -> None:
    report = design_inventory_formula(idea="a lavender fougere")

    checks = report["composition_checks"]
    assert _flagged(checks) == []
    ifra = [c for c in checks["checks"] if c["check"] == "ifra"]
    assert [c["status"] for c in ifra] == ["PASS"]


def test_a_gate_error_becomes_an_error_check_not_a_failed_design(monkeypatch) -> None:
    import engine.pipeline.gates as gates

    def boom(*_args, **_kwargs):
        raise RuntimeError("state unavailable")

    monkeypatch.setattr(gates, "run_composition_gates", boom)
    report = design_inventory_formula(**CHYPRE)

    assert report["composition_checks"]["checks"] == [
        {
            "check": "gate",
            "status": "ERROR",
            "message": "checks could not run: RuntimeError: state unavailable",
        }
    ]


def _row(material: str, amount: str, fraction: str, unit: str = "uL") -> dict:
    return {"material": material, "amount_decimal": amount, "amount_unit": unit,
            "stock_fraction_decimal": fraction, "fraction_basis": "mass_fraction", "carrier": "DPG"}


def test_a_second_strength_of_the_same_material_counts_toward_its_ifra_total() -> None:
    # 12 uL neat is just under the 0.043% limit in 30 mL; the 10% row's 120 uL
    # adds another 12 uL of active and takes it over.
    rows = [_row("Alpha Damascone", "12", "1"), _row("Alpha Damascone", "120", "0.1"),
            _row("Hedione", "5868", "1")]
    checks = composition_checks({"rows": rows}, formula_name="Rose test")

    fails = [c["message"] for c in checks["checks"] if c["check"] == "ifra" and c["status"] == "FAIL"]
    assert any(m.startswith("Alpha Damascone at ") for m in fails), checks["checks"]
    assert checks["unchecked_rows"] == []


def test_a_weighed_solid_is_named_as_not_checked() -> None:
    rows = [_row("Hedione", "6000", "1"), _row("Coumarin", "500", "1", unit="mg")]
    checks = composition_checks({"rows": rows}, formula_name="Solid test")

    assert checks["unchecked_rows"] == [{"material": "Coumarin", "reason": "weighed solid (mg)"}]
