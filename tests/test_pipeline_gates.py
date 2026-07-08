from engine.pipeline.gates import ReleaseGateConfig, gate_formula


def _formula(ingredients, dilutions=None, name="Test Formula"):
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": name,
        "ingredients_ul": ingredients,
        "dilutions": dilutions or {},
        "ingredients_pct": {k: v / total * 100 for k, v in ingredients.items()},
        "body": name,
    }


def test_gate_blocks_opaque_preblend_by_default():
    formula = _formula(
        {"Hedione": 3000.0, "Iso E Super": 2000.0, "Cardamom FTEC": 1000.0},
        name="Aromatic Fougere",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["opaque_preblends"].status == "FAIL"
    assert report.status == "FAIL"


def test_gate_allows_preblend_with_explicit_waiver():
    formula = _formula(
        {"Hedione": 3000.0, "Iso E Super": 2000.0, "Cardamom FTEC": 1000.0},
        name="Aromatic Fougere",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            allow_preblends=True,
        ),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["opaque_preblends"].status == "WARN"


def test_gate_blocks_neat_trace_below_floor():
    formula = _formula(
        {"Hedione": 5999.0, "Geosmin": 1.0},
        name="Trace Test",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["pipette_floor_neat_traces"].status == "FAIL"


def test_chemistry_stability_fails_aldehyde_amine_contact():
    formula = _formula(
        {"Aldehyde C12 MNA": 2000.0, "Indole": 1000.0, "Hedione": 3000.0},
        name="Reactive Jasmine",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["chemistry_stability"].status == "FAIL"
    assert "Schiff-base risk" in gates["chemistry_stability"].detail


def test_chemistry_stability_warns_for_citrus_heavy_oxidation_risk():
    formula = _formula(
        {"D-Limonene": 1500.0, "Linalool": 300.0, "Hedione": 1200.0, "Iso E Super": 3000.0},
        name="Citrus Stress Test",
    )
    technical = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False),
    )
    commercial = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            commercial_mode=True,
            audit_enabled=False,
        ),
    )

    technical_gates = {g.gate: g for g in technical.gates}
    commercial_gates = {g.gate: g for g in commercial.gates}
    assert technical_gates["chemistry_stability"].status == "WARN"
    assert commercial_gates["chemistry_stability"].status == "FAIL"


def test_chemistry_stability_passes_stable_woody_floral_formula():
    formula = _formula(
        {"Hedione": 2500.0, "Iso E Super": 2500.0, "Habanolide": 1000.0},
        name="Stable Woods Floral",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["chemistry_stability"].status == "PASS"


def test_phase_compatibility_fails_hsp_incompatible_blend():
    formula = _formula(
        {"Vanillin": 1800.0, "D-Limonene": 1800.0, "Galaxolide": 1800.0, "Hedione": 600.0},
        name="Phase Clash",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["phase_compatibility"].status == "FAIL"


def test_phase_compatibility_warns_when_hsp_coverage_is_thin():
    formula = _formula(
        {"Lavender EO": 3000.0, "Habanolide": 2000.0, "Vetiver EO": 1000.0},
        name="Sparse HSP Coverage",
    )
    report = gate_formula(
        formula,
        ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic", audit_enabled=False),
    )

    gates = {g.gate: g for g in report.gates}
    assert gates["phase_compatibility"].status == "WARN"
