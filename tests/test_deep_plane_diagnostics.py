from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.formulation_intelligence.deep_plane_diagnostics import (
    DEEP_PLANE_IDS,
    DeepPlaneCheckConfig,
    StaleInventoryAuthorityError,
    run_deep_plane_check,
    write_deep_plane_artifacts,
)


def _write_formula(
    path: Path,
    *,
    name: str = "Deep Plane Test",
    immortelle_dilution: str = "10% in DPG",
    include_uncovered_natural: bool = False,
) -> Path:
    extra_row = (
        "| 3 | Frankincense EO | neat | 50 |\n"
        if include_uncovered_natural
        else ""
    )
    path.write_text(
        f"""# {name}

**Target identity:** immortelle light moving from a dry surface into a warm interior.
**Excluded takeovers:** generic amberwood, edible sweetness, and anonymous musk.

## Functional Architecture

- Surface/front glint: dry aromatic lift.
- Interior/living middle: warm floral-hay body.
- Bridge and handoff: the surface recurs as a dry residue.
- Spatial composition: front, middle, rear contour, skin echo, and air.
- Experiment: protected-nucleus constant-total matched-carrier A/B with blinded AB/BA order.

| # | Ingredient | Dilution | Amount (µL) |
|---|---|---|---:|
| 1 | Immortelle Absolute | {immortelle_dilution} | 100 |
| 2 | Hedione | neat | 900 |
{extra_row}""",
        encoding="utf-8",
    )
    return path


def _plane(payload: dict, plane_id: str) -> dict:
    return next(item for item in payload["formulas"][0]["planes"] if item["plane_id"] == plane_id)


def test_deep_plane_run_is_deterministic_and_contains_all_thirteen_planes(
    tmp_path: Path,
) -> None:
    formula = _write_formula(tmp_path / "formula.md")
    config = DeepPlaneCheckConfig(batch_volume_ml=30.0, temperature_k=305.0)

    first = run_deep_plane_check(formula, config=config).as_dict()
    second = run_deep_plane_check(formula, config=config).as_dict()

    assert first == second
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
        second, sort_keys=True, ensure_ascii=False
    )
    assert [item["plane_id"] for item in first["formulas"][0]["planes"]] == list(
        DEEP_PLANE_IDS
    )
    assert len(first["formulas"][0]["planes"]) == 13
    assert all(
        {
            "status",
            "evidence",
            "limitations",
            "falsification_or_test_requirement",
            "authority_ceiling",
        }
        <= set(item)
        for item in first["formulas"][0]["planes"]
    )
    assert first["schema_version"] == "deep_plane_runtime_check_v1"
    assert first["check_state"] == "COMPLETE"
    assert first["status"] == "HOLD"
    assert len(first["content_sha256"]) == 64


def test_parent_and_no_parent_paths_use_the_pre_mix_guard(tmp_path: Path) -> None:
    child = _write_formula(
        tmp_path / "child.md",
        name="Child Revision",
        immortelle_dilution="neat",
    )
    parent = _write_formula(tmp_path / "parent.md", name="Immediate Parent")

    without_parent = run_deep_plane_check(child).as_dict()
    with_parent = run_deep_plane_check(child, parent_formula_path=parent).as_dict()

    no_parent_guard = without_parent["formulas"][0]["pre_mix_guard"]
    parent_guard = with_parent["formulas"][0]["pre_mix_guard"]
    assert no_parent_guard["parent_comparison_available"] is False
    assert parent_guard["parent_comparison_available"] is True
    assert parent_guard["status"] == "FAIL"
    assert any(
        item["code"] == "STOCK_REBASE_ACTIVE_EQUIVALENCE"
        for item in parent_guard["findings"]
    )
    assert with_parent["parent_source_sha256"] is not None


def test_stale_inventory_authority_fails_closed(tmp_path: Path) -> None:
    formula = _write_formula(tmp_path / "formula.md")

    with pytest.raises(StaleInventoryAuthorityError) as error:
        run_deep_plane_check(
            formula,
            expected_inventory_sha256="0" * 64,
        )

    assert error.value.code == "STALE_INVENTORY_AUTHORITY"
    assert error.value.expected_sha256 == "0" * 64
    assert error.value.observed_sha256 != error.value.expected_sha256


def test_naturals_use_composite_authority_or_withhold_oav(tmp_path: Path, monkeypatch) -> None:
    # Freeze the missing-model branch; current registry coverage may expand.
    from engine.pipeline import natural_absolute_decomposition as decomposition

    original = decomposition.get_constituents
    monkeypatch.setattr(
        decomposition, "get_constituents",
        lambda name: None if "frankincense" in name.casefold() else original(name),
    )
    formula = _write_formula(
        tmp_path / "formula.md",
        include_uncovered_natural=True,
    )

    payload = run_deep_plane_check(formula).as_dict()
    rows = {
        row["material"]: row
        for row in payload["formulas"][0]["physicochemical_evidence"]["materials"]
    }

    assert rows["Immortelle Absolute"]["oav_authority"] == "composite_natural"
    assert rows["Immortelle Absolute"]["oav"] is not None
    assert rows["Frankincense EO"]["oav_authority"] == (
        "withheld_missing_composite_natural_model"
    )
    assert rows["Frankincense EO"]["oav"] is None
    assert "Frankincense EO" in _plane(payload, "physicochemical")["evidence"][
        "unresolved_natural_composites"
    ]
    assert _plane(payload, "physicochemical")["status"] == "HOLD"


def test_opaque_preblend_oav_is_withheld_without_constituent_lineage(
    tmp_path: Path,
) -> None:
    formula = tmp_path / "opaque.md"
    formula.write_text(
        """# Opaque Preblend

**Target identity:** dry aromatic contrast.

| # | Ingredient | Dilution | Amount (µL) |
|---|---|---|---:|
| 1 | Cardamom FTEC | neat | 10 |
| 2 | Hedione | neat | 990 |
""",
        encoding="utf-8",
    )

    payload = run_deep_plane_check(formula).as_dict()
    rows = {
        row["material"]: row
        for row in payload["formulas"][0]["physicochemical_evidence"]["materials"]
    }

    assert rows["Cardamom FTEC"]["oav"] is None
    assert rows["Cardamom FTEC"]["oav_authority"] == (
        "withheld_opaque_preblend_constituents"
    )
    assert payload["formulas"][0]["physicochemical_evidence"][
        "opaque_preblends_withheld"
    ] == ["Cardamom FTEC"]


def test_claim_ceilings_never_promote_modeled_output(tmp_path: Path) -> None:
    payload = run_deep_plane_check(_write_formula(tmp_path / "formula.md")).as_dict()

    assert set(payload["authority_flags"].values()) == {False}
    assert payload["authority_ceiling"] == "withheld"
    hedonic = _plane(payload, "hedonic")
    biological = _plane(payload, "biological_sensitivity")
    assert hedonic["status"] == "NOT_TESTED"
    assert biological["status"] == "HOLD"
    combined = " ".join(payload["limitations"]).casefold()
    for forbidden_claim in (
        "smell",
        "liking",
        "similarity",
        "safety",
        "stability",
        "release",
    ):
        assert forbidden_claim in combined


def test_artifact_writes_are_idempotent_and_markdown_is_deterministic(
    tmp_path: Path,
) -> None:
    run = run_deep_plane_check(_write_formula(tmp_path / "formula.md"))
    output_dir = tmp_path / "artifacts"

    first = write_deep_plane_artifacts(run, output_dir)
    first_bytes = {name: path.read_bytes() for name, path in first.items()}
    second = write_deep_plane_artifacts(run, output_dir)

    assert set(first) == {"json", "markdown"}
    assert first == second
    assert {name: path.read_bytes() for name, path in second.items()} == first_bytes
    assert run.to_markdown() == run.to_markdown()
    assert first["markdown"].read_text(encoding="utf-8") == run.to_markdown()


@pytest.fixture
def bound_stock():
    from engine.pipeline.formula_state import build_formula_state
    from engine.pipeline.preflight import (
        build_formula_dose_receipt,
        resolve_inventory_stock_contract,
    )

    formula = {
        "name": "Diagnostic binding regression",
        "ingredients_ul": {"Hedione": 100.0},
        "dilutions": {"Hedione": 1.0},
    }
    contract = resolve_inventory_stock_contract(formula)
    assert contract.status == "PASS"
    receipt = build_formula_dose_receipt(formula, contract)
    assert receipt.status == "BOUND"
    state = build_formula_state(
        formula["ingredients_ul"], formula["dilutions"],
        stock_specs=contract.data["resolved_stock_specs"],
    )
    state = replace(state, dose_receipt_sha256=receipt.receipt_sha256,
                    dose_receipt_status=receipt.status)
    return formula, state, receipt


def _binding(formula, state=None, receipt=None, inventory_path=None):
    from engine.formulation_intelligence import deep_plane_diagnostics as diagnostics

    return diagnostics._inventory_receipt_evidence(
        formula, inventory_path=inventory_path or diagnostics._project_root() / "inventory.txt",
        state=state, dose_receipt=receipt,
    )


def test_exact_live_stock_receipt_replays_without_granting_release(bound_stock):
    from engine.formulation_intelligence.deep_plane_diagnostics import evaluate_deep_plane_gate

    formula, state, receipt = bound_stock
    binding = _binding(formula, state, receipt)
    assert binding["all_formula_materials_executable_from_declared_inventory"] is True
    assert binding["binding_issues"] == []
    result = evaluate_deep_plane_gate(formula, state, (), dose_receipt=receipt)
    assert result["inventory_evidence"] == {**result["inventory_evidence"], **binding}
    assert result["authority_status"] == "HOLD"
    assert set(result["authority_flags"].values()) == {False}
    assert result["calculation_reuse"]["formula_state_reused"] is True


def test_owned_name_and_dilution_without_receipt_is_not_executable(bound_stock):
    from engine.formulation_intelligence.deep_plane_diagnostics import evaluate_deep_plane_gate

    formula, state, _ = bound_stock
    result = evaluate_deep_plane_gate(formula, state, ())
    assert result["inventory_evidence"]["declared_name_and_dilution_match"] is True
    assert result["inventory_evidence"]["all_formula_materials_executable_from_declared_inventory"] is False
    assert result["gate_status"] == "FAIL"
    assert "INVENTORY_DOSE_BINDING_UNVERIFIED" in {row["code"] for row in result["blockers"]}


@pytest.mark.parametrize("change", [
    {"raw_ul": 101.0}, {"active_ul": 99.0}, {"dilution": 0.5},
    {"stock_fraction_basis": "mass_fraction"}, {"stock_carrier": "dpg"},
    {"stock_declared": False},
])
def test_state_dose_and_stock_semantics_cannot_reuse_binding(bound_stock, change):
    formula, state, receipt = bound_stock
    changed = replace(state, materials=(replace(state.materials[0], **change),))
    result = _binding(formula, changed, receipt)
    assert result["all_formula_materials_executable_from_declared_inventory"] is False
    assert result["binding_issues"] == ["dose_receipt_state_replay_failed"]


def test_extra_state_material_cannot_hide_behind_valid_receipt(bound_stock):
    formula, state, receipt = bound_stock
    changed = replace(state, materials=(*state.materials, state.materials[0]))
    assert _binding(formula, changed, receipt)["binding_issues"] == ["state_material_set_mismatch"]


def test_changed_formula_and_stale_stock_receipt_are_rejected(bound_stock):
    formula, state, receipt = bound_stock
    changed = {**formula, "ingredients_ul": {"Hedione": 101.0}}
    assert _binding(changed, state, receipt)["all_formula_materials_executable_from_declared_inventory"] is False
    stale = replace(receipt, inventory_snapshot_sha256="0" * 64)
    stale_state = replace(state, dose_receipt_sha256=stale.receipt_sha256)
    assert _binding(formula, stale_state, stale)["binding_issues"] == [
        "dose_receipt_does_not_match_current_formula_and_stock"
    ]


@pytest.mark.parametrize("name,fraction", [
    ("Turkish Storax Tincture", 0.20), ("Vietnamese Benzoin Tincture", 0.40),
    ("Kenyan Myrrh Ethanol Tincture", 0.20), ("Oman Frankincense Ethanol Tincture", 0.33),
    ("Romandolide", 1.0),
])
def test_non_executable_or_depleted_stock_stays_blocked(name, fraction):
    formula = {"name": "Stock hold regression", "ingredients_ul": {name: 100.0},
               "dilutions": {name: fraction}}
    result = _binding(formula)
    assert result["stock_contract_status"] != "PASS"
    assert result["all_formula_materials_executable_from_declared_inventory"] is False


def test_custom_inventory_cannot_borrow_current_authority(bound_stock, tmp_path):
    formula, state, receipt = bound_stock
    assert _binding(formula, state, receipt, tmp_path / "inventory.txt")["binding_issues"] == [
        "non_authoritative_inventory_path"
    ]


def test_undeclared_fraction_does_not_become_authoritative_neat(bound_stock):
    formula, state, receipt = bound_stock
    undeclared = {key: value for key, value in formula.items() if key != "dilutions"}
    assert _binding(undeclared, state, receipt)["stock_contract_status"] != "PASS"


@pytest.mark.parametrize("status,code", [
    ("FAIL", "PARENT_PRE_MIX_SCREEN_BLOCK"),
    ("SCREEN_BLOCK", "PARENT_PRE_MIX_SCREEN_BLOCK"),
    ("UNRECOGNIZED", "PRE_MIX_STATUS_UNRECOGNIZED"),
    ("PASS", None), ("SCREEN_CLEAR", None),
    ("WARN", "PRE_MIX_SCREEN_REVIEW"), ("SCREEN_REVIEW", "PRE_MIX_SCREEN_REVIEW"),
])
def test_parent_guard_hard_failure_is_not_lost_in_status_translation(status, code):
    from engine.formulation_intelligence import deep_plane_diagnostics as diagnostics

    blockers, warnings = diagnostics._gate_blockers_and_warnings(
        planes=[{"plane_id": name, "status": "DOCUMENTED"}
                for name in diagnostics.STRUCTURAL_PLANE_IDS],
        physical={"unresolved_natural_composites": [], "opaque_preblends_withheld": [],
                  "missing_physics_materials": []},
        inventory={"missing": [], "unavailable": [], "dilution_mismatches": [],
                   "all_formula_materials_executable_from_declared_inventory": True},
        guard={"status": status, "findings": []},
    )
    if code is None:
        assert blockers == [] and warnings == []
    elif code == "PRE_MIX_SCREEN_REVIEW":
        assert blockers == []
        assert code in {item["code"] for item in warnings}
    else:
        assert code in {item["code"] for item in blockers}
