
from engine.optimizer.gate_aware import max_raw_ul_for_ifra, optimize_until_release_ready
from engine.pipeline.audit_log import append_event, load_events, suggest_repairs, summarize_events
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.formula_release_gate import main as release_gate_main


def _fougere_formula(evernyl_ul=150.0):
    ingredients = {
        "Cedrat FCF oil Sicilian": 1200.0,
        "Lavender EO (BONTAUX SAS)": 700.0,
        "Linalyl Acetate": 600.0,
        "Hedione": 900.0,
        "Coumarin": 300.0,
        "Evernyl": evernyl_ul,
        "Iso E Super": 1500.0,
        "Cedarwood oil Virginia": 300.0,
        "Zenolide": 500.0 - evernyl_ul,
    }
    total = sum(ingredients.values())
    return {
        "number": 1,
        "name": "Commercial Fougere Edge",
        "body": "aromatic fougere",
        "ingredients_ul": ingredients,
        "dilutions": {
            name: (
                0.3
                if name == "Coumarin"
                else 0.2
                if name == "Evernyl"
                else 1.0
            )
            for name in ingredients
        },
        "ingredients_pct": {name: amount / total * 100 for name, amount in ingredients.items()},
    }


def _raw_pct_from_formula(formula):
    return dict(formula["ingredients_pct"])


def test_ifra_headroom_math_for_evernyl():
    assert max_raw_ul_for_ifra(0.1, 30.0, 1.0, headroom=1.0) == 30.0
    assert round(max_raw_ul_for_ifra(0.1, 30.0, 1.0, headroom=0.8), 6) == 24.0


def test_commercial_mode_blocks_technical_edge_evernyl():
    formula = _fougere_formula(evernyl_ul=150.0)

    technical = gate_formula(
        formula,
        ReleaseGateConfig(
            brief="aromatic_fougere",
            min_confidence_score=0.0,
            audit_enabled=False,
        ),
    )
    commercial = gate_formula(
        formula,
        ReleaseGateConfig(
            brief="aromatic_fougere",
            min_confidence_score=0.0,
            commercial_mode=True,
            audit_enabled=False,
        ),
    )

    technical_gates = {gate.gate: gate for gate in technical.gates}
    commercial_gates = {gate.gate: gate for gate in commercial.gates}
    assert technical_gates["safety_ifra_allergen"].status != "FAIL"
    assert commercial_gates["safety_ifra_allergen"].status == "FAIL"
    assert commercial_gates["safety_ifra_allergen"].data["effective_headroom"] == 0.8


def test_commercial_optimizer_repairs_evernyl_robustness_margin():
    formula = _fougere_formula(evernyl_ul=150.0)
    result = optimize_until_release_ready(
        "Commercial Fougere Repair",
        _raw_pct_from_formula(formula),
        stock_dilutions=formula["dilutions"],
        config=ReleaseGateConfig(
            brief="aromatic_fougere",
            commercial_mode=True,
            min_confidence_score=0.0,
            audit_enabled=False,
        ),
        repair_pool={"Iso E Super": 2.0, "Cedarwood oil Virginia": 1.0},
        max_passes=4,
    )

    evernyl_ul = result.raw_concentrate_pct["Evernyl"] / 100.0 * 6000.0
    assert evernyl_ul * 0.2 < 25.0
    assert any(
        action.gate == "robustness_perturbation"
        and action.action == "cap_robustness_safety_margin"
        and action.material == "Evernyl"
        for action in result.repair_actions
    )
    # Arithmetic repair is not proof of stock binding or release authority.
    assert result.status == "FAIL"
    assert any(
        gate.status == "FAIL" and gate.gate in {"inventory_stock_contract", "authority_vector"}
        for gate in result.gate_report.gates
    )


def test_gate_formula_writes_compact_audit_event(tmp_path, monkeypatch):
    audit_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("PERFUME_PIPELINE_AUDIT_PATH", str(audit_path))

    report = gate_formula(
        _fougere_formula(evernyl_ul=20.0),
        ReleaseGateConfig(
            brief="aromatic_fougere",
            audit_source="unit-test",
        ),
    )
    events = load_events(audit_path)

    assert report.audit_event_id
    assert len(events) == 1
    assert events[0]["event_id"] == report.audit_event_id
    assert events[0]["formula_hash"] == report.formula_hash
    assert events[0]["source"] == "unit-test"


def test_audit_disabled_writes_nothing(tmp_path, monkeypatch):
    audit_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("PERFUME_PIPELINE_AUDIT_PATH", str(audit_path))

    gate_formula(
        _fougere_formula(evernyl_ul=20.0),
        ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False),
    )

    assert not audit_path.exists()


def test_audit_summary_and_suggestions_rank_recurring_material(tmp_path):
    audit_path = tmp_path / "events.jsonl"
    for _ in range(2):
        append_event(
            {
                "event_type": "gate_formula",
                "status": "WARN",
                "gates": [
                    {
                        "gate": "robustness_perturbation",
                        "status": "WARN",
                        "data": {
                            "issues": [
                                {
                                    "material": "Evernyl",
                                    "direction": "up",
                                    "safety_failed": True,
                                    "family_envelope_drift": 0.0,
                                }
                            ]
                        },
                    }
                ],
            },
            audit_path,
        )

    events = load_events(audit_path)
    summary = summarize_events(events)
    suggestions = suggest_repairs(events, material="Evernyl")

    assert summary["ranked_issues"][0]["issue"] == "robustness_perturbation:Evernyl:safety_margin"
    assert summary["ranked_issues"][0]["count"] == 2
    assert "Reduce Evernyl" in suggestions[0]["suggestion"]


def test_formula_release_gate_cli_commercial_mode(tmp_path, monkeypatch, capsys):
    audit_path = tmp_path / "events.jsonl"
    formula_path = tmp_path / "edge.md"
    monkeypatch.setenv("PERFUME_PIPELINE_AUDIT_PATH", str(audit_path))
    formula_path.write_text(
        """# Edge Formula

| # | Ingredient | Dilution | uL | % |
|---|---|---:|---:|---:|
| 1 | Cedrat FCF oil Sicilian | neat | 1200 | 20 |
| 2 | Lavender EO (BONTAUX SAS) | neat | 700 | 11.67 |
| 3 | Linalyl Acetate | neat | 600 | 10 |
| 4 | Hedione | neat | 900 | 15 |
| 5 | Coumarin | 30% | 300 | 5 |
| 6 | Evernyl | 20% | 150 | 2.5 |
| 7 | Iso E Super | neat | 1500 | 25 |
| 8 | Cedarwood oil Virginia | neat | 300 | 5 |
| 9 | Zenolide | neat | 350 | 5.83 |
""",
        encoding="utf-8",
    )

    status = release_gate_main([
        "--formula-file",
        str(formula_path),
        "--brief",
        "aromatic_fougere",
        "--commercial-ready",
    ])
    captured = capsys.readouterr()

    assert status == 1
    assert "Overall: FAIL" in captured.out
    assert load_events(audit_path)
