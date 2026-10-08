"""Name check on by default: unrequested checks SKIP, and Hedione/musk dosing warns."""

import pytest

import engine.pipeline.gates as gates_module
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ADVISORY_FAILURE_GATES,
    BLOCKING_STATUSES,
    GateResult,
    ReleaseGateConfig,
    _apply_guideline_policy,
    _status_from_gates,
)


def _state(ingredients: dict[str, float]):
    return build_formula_state(ingredients, {name: 1.0 for name in ingredients})


def _formula(ingredients: dict[str, float], name: str = "Test Formula") -> dict:
    return {
        "name": name,
        "ingredients_ul": dict(ingredients),
        "dilutions": {key: 1.0 for key in ingredients},
    }


# Fragrance-active total is 100 uL, so each Hedione dose is its share in percent.
def _hedione_rows(hedione_ul: float) -> dict[str, float]:
    return {"Hedione": hedione_ul, "Linalool": 100.0 - hedione_ul}


# ── 1. SKIP, not PASS, when a check was not requested ──────────────────


def test_unrequested_checks_skip_instead_of_passing():
    rows = {"Linalool": 50.0, "Iso E Super": 50.0}
    formula = _formula(rows)
    config = ReleaseGateConfig(audit_enabled=False)

    results = [
        gates_module._gate_oav_scaling(formula, config),
        gates_module._gate_family_drift_detector(formula, config),
        gates_module._gate_novelty_vs_reference(formula, config),
        gates_module._gate_oav_intelligence(_state(rows), (), config),
    ]

    assert [(r.gate, r.status, r.detail) for r in results] == [
        ("oav_scaling_guard", "SKIP", "not requested"),
        ("family_drift_detector", "SKIP", "not requested"),
        ("novelty_vs_reference", "SKIP", "not requested"),
        ("oav_intelligence", "SKIP", "not requested"),
    ]


@pytest.mark.parametrize(
    "gate_name",
    ["oav_scaling_guard", "family_drift_detector", "novelty_vs_reference", "oav_intelligence"],
)
def test_skip_survives_guideline_policy_and_never_votes(gate_name):
    skipped = _apply_guideline_policy(GateResult(gate=gate_name, status="SKIP", detail="not requested"))

    assert skipped.status == "SKIP"
    assert skipped.status not in BLOCKING_STATUSES
    assert _status_from_gates([GateResult(gate="other", status="PASS"), skipped]) == "PASS"
    assert _status_from_gates([GateResult(gate="other", status="WARN"), skipped]) == "WARN"


# ── 2. Hedione share ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("hedione_ul", "brief", "name", "status", "cap"),
    [
        (16.0, "generic", "Test Formula", "WARN", "15%"),
        (13.0, "generic", "Moss Chypre", "WARN", "12%"),
        (13.0, "generic", "Test Formula", "PASS", "15%"),
    ],
)
def test_hedione_share_warns_above_family_cap(hedione_ul, brief, name, status, cap):
    rows = _hedione_rows(hedione_ul)
    result = gates_module._gate_hedione_share(
        _formula(rows, name=name), _state(rows), ReleaseGateConfig(brief=brief, audit_enabled=False)
    )

    assert result.status == status
    assert f"{hedione_ul:.1f}%" in result.detail
    assert cap in result.detail
    assert "% of fragrance-active uL" in result.detail


def test_hedione_share_uses_chypre_cap_from_resolved_archetype(monkeypatch):
    monkeypatch.setattr(gates_module, "infer_archetype", lambda brief, archetype: "classic_chypre")
    rows = _hedione_rows(13.0)
    result = gates_module._gate_hedione_share(
        _formula(rows), _state(rows), ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "WARN"
    assert "12%" in result.detail and "chypre" in result.detail


def test_hedione_share_skips_without_hedione():
    rows = {"Linalool": 100.0}
    result = gates_module._gate_hedione_share(
        _formula(rows), _state(rows), ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "SKIP"


# ── 3. Musk count ─────────────────────────────────────────────────────


def test_three_musks_warn_and_name_each():
    rows = {"Galaxolide": 30.0, "Habanolide": 30.0, "Ethylene Brassylate": 30.0, "Linalool": 10.0}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "WARN"
    for musk in ("Galaxolide", "Habanolide", "Ethylene Brassylate"):
        assert musk in result.detail
    assert "omission comparison" in result.detail


def test_two_musks_pass():
    rows = {"Galaxolide": 45.0, "Habanolide": 45.0, "Linalool": 10.0}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "PASS"


def test_tonalide_warns_even_as_the_only_musk():
    rows = {"Tonalide": 20.0, "Linalool": 80.0}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "WARN"
    assert "Tonalide" in result.detail and "exception-only" in result.detail


def test_no_musk_skips():
    rows = {"Linalool": 100.0}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "SKIP"


# ── The new gates are advisory: a failure inside them can never block ──


@pytest.mark.parametrize("gate_name", ["hedione_share", "musk_count"])
def test_new_gates_are_advisory(gate_name):
    assert gate_name in ADVISORY_FAILURE_GATES
    demoted = _apply_guideline_policy(GateResult(gate=gate_name, status="FAIL", detail="x"))
    assert demoted.status == "WARN"


def test_new_gates_run_right_after_perfume_knowledge():
    rows = {"Hedione": 20.0, "Galaxolide": 20.0, "Habanolide": 20.0, "Tonalide": 20.0, "Linalool": 20.0}
    report = gates_module.gate_formula(_formula(rows), ReleaseGateConfig(audit_enabled=False))
    names = [gate.gate for gate in report.gates]
    by_name = {gate.gate: gate for gate in report.gates}

    index = names.index("perfume_knowledge")
    assert names[index + 1 : index + 3] == ["hedione_share", "musk_count"]
    assert by_name["hedione_share"].status == "WARN"
    assert by_name["musk_count"].status == "WARN"


# ── Review fixes: audit ranking, musk identity/trace, accented chypre ──


def test_skipped_gates_do_not_enter_audit_issue_ranking():
    from engine.pipeline.audit_log import suggest_repairs, summarize_events

    events = [
        {
            "event_type": "release_gate",
            "status": "PASS",
            "gates": [
                {"gate": "novelty_vs_reference", "status": "SKIP", "data": {}},
                {"gate": "oav_scaling_guard", "status": "SKIP", "data": {}},
                {"gate": "musk_count", "status": "WARN", "data": {}},
            ],
        }
    ]

    summary = summarize_events(events)

    assert [row["issue"] for row in summary["ranked_issues"]] == ["musk_count"]
    assert summary["gate_status_counts"]["novelty_vs_reference:SKIP"] == 1
    assert all("distinctive signature" not in s["suggestion"] for s in suggest_repairs(events))


def test_one_musk_in_two_dilutions_counts_once():
    ingredients = {
        "Ambrettolide": 20.0,
        "Ambrettolide (10%)": 300.0,
        "Galaxolide": 40.0,
        "Habanolide": 40.0,
    }
    state = build_formula_state(
        ingredients,
        {"Ambrettolide": 1.0, "Ambrettolide (10%)": 0.1, "Galaxolide": 1.0, "Habanolide": 1.0},
    )
    result = gates_module._gate_musk_count(state, ReleaseGateConfig(audit_enabled=False))

    assert result.status == "WARN"
    assert result.detail.startswith("3 musks (")
    assert result.detail.count("Ambrettolide") == 1


def test_trace_musk_is_not_counted_and_is_named_as_trace():
    rows = {"Galaxolide": 49.95, "Habanolide": 49.95, "Ethylene Brassylate": 0.05, "Linalool": 0.05}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "PASS"
    assert result.detail.startswith("2 musk(s)")
    assert "trace" in result.detail and "Ethylene Brassylate" in result.detail


def test_trace_tonalide_still_warns_as_exception_only():
    rows = {"Galaxolide": 99.95, "Tonalide": 0.05}
    result = gates_module._gate_musk_count(_state(rows), ReleaseGateConfig(audit_enabled=False))

    assert result.status == "WARN"
    assert "Tonalide" in result.detail and "exception-only" in result.detail


@pytest.mark.parametrize("name", ["Moss Chypré", "MOSS CHYPRE", "Chypré Noir"])
def test_hedione_share_chypre_name_is_accent_and_case_insensitive(name):
    rows = _hedione_rows(13.0)
    result = gates_module._gate_hedione_share(
        _formula(rows, name=name), _state(rows), ReleaseGateConfig(audit_enabled=False)
    )

    assert result.status == "WARN"
    assert "12%" in result.detail
