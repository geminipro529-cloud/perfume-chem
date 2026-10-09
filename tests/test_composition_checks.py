"""Composed formulas carry the release gate's crowding and IFRA findings."""

from engine.research.formula_design import design_inventory_formula

CHYPRE = {
    "idea": "a panoramic, exceptionally detailed modern chypre with rose, patchouli and oakmoss",
    "formula_name": "Panoramic Chypre",
}


def _flagged(checks: dict) -> list[dict]:
    return [c for c in checks["checks"] if c["status"] in {"WARN", "FAIL"}]


def test_composed_chypre_carries_the_gate_ifra_fail_for_alpha_damascone() -> None:
    report = design_inventory_formula(**CHYPRE)

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


def test_a_gate_error_becomes_a_skip_not_a_failed_design(monkeypatch) -> None:
    import engine.pipeline.gates as gates

    def boom(*_args, **_kwargs):
        raise RuntimeError("state unavailable")

    monkeypatch.setattr(gates, "run_composition_gates", boom)
    report = design_inventory_formula(**CHYPRE)

    assert report["composition_checks"]["checks"] == [
        {
            "check": "gate",
            "status": "SKIP",
            "message": "checks could not run: RuntimeError: state unavailable",
        }
    ]
