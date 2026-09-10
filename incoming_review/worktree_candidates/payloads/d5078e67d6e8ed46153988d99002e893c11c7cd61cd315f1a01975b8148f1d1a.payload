from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from engine.evidence.augmentation import EvidenceAugmentationState
from engine.solforge.adapters import (
    compile_architectural_delta,
    compile_architectural_delta_v2,
)
from engine.solforge.architectural_adapter import (
    compile_architectural_delta as compile_runtime_architectural_delta,
)
from engine.solforge.contracts import (
    CompilationState,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
)

H = "a" * 64


@pytest.fixture
def inventory_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, int]:
    records = (
        ("Habanolide", "HAVE — NEAT", "Habanolide neat/as supplied"),
        ("Romandolide", "HAVE — NEAT", "Romandolide neat/as supplied"),
        ("Neroli EO 10%", "HAVE — DILUTION", "Neroli EO 10% in DPG"),
        ("Tonalide", "HAVE — DILUTION", "Tonalide 10% in DPG"),
        ("Ambrettolide 10%", "PLANNED ACQUISITION", None),
        ("Ethylene Brassylate", "MISSING", None),
    )
    workbook_path = tmp_path / "inventory-v5.xlsx"
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Current Inventory Master")
    for row in (["title"], ["authority"], [], []):
        sheet.append(row)
    sheet.append(
        [
            "Canonical material", "Status", "Actual stock(s)", "Can prepare",
            "Family", "Alias / non-equivalent", "Formula-use policy", "User note",
        ]
    )
    for material, status, stock in records:
        sheet.append([material, status, stock, None, "test", None, "test only", None])
    workbook.save(workbook_path)
    workbook.close()
    workbook_sha256 = hashlib.sha256(workbook_path.read_bytes()).hexdigest()

    root = Path(__file__).resolve().parents[1]
    source = root / "data/governance/complexity_inventory_catalog_v1.json"
    catalog = json.loads(source.read_text(encoding="utf-8"))
    catalog["authority"]["workbook_sha256"] = workbook_sha256
    catalog["authority"]["current_record_count"] = len(records)
    catalog["current_records"] = [
        {
            "source_row": index + 6,
            "canonical_material": material,
            "status": status,
            "actual_stocks": stock,
            "can_prepare": None,
            "family": "test",
            "alias_or_non_equivalent": None,
            "formula_use_policy": "test only",
            "user_note": None,
        }
        for index, (material, status, stock) in enumerate(records)
    ]
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    from engine.perception import complexity_inventory

    monkeypatch.setattr(complexity_inventory, "_EXPECTED_WORKBOOK_SHA256", workbook_sha256)
    monkeypatch.setattr(complexity_inventory, "_CATALOG_PATH", catalog_path)
    return workbook_path, workbook_sha256, len(records)


def _case(authority: tuple[Path, str, int], *, target: str = "quiet mineral skin") -> SolForgeCaseV1:
    path, digest, _ = authority
    return SolForgeCaseV1(
        case_id="MUSK-1",
        state=SolForgeCaseState.READY,
        target_identity=target,
        ideal_architecture={"base": ["radiant dry musk", "soft skin texture"]},
        current_inventory_build={"materials": {"Iso E Super": 0.9, "carrier": 0.1}},
        inventory_path=str(path),
        inventory_sha256=digest,
        formula_sha256="b" * 64,
        dose_receipt_sha256="c" * 64,
        constraints=("constant total",),
        criterion="DEPTH",
        forbidden_claims=("liking", "release"),
    )


def _hypothesis(**changes) -> SolHypothesisV1:
    values = {
        "hypothesis_id": "H1", "rank": 1,
        "claim": "Test one precise musk function.",
        "target_function": "radiant dryness",
        "material_names": ("Habanolide",), "intervention_kind": "ADDITION",
        "expected_behavior": "test a dry spatial transition",
        "rationale": "target-functional isolate",
        "uncertainty": 0.5, "evidence_refs": ("d" * 64,), "nary_factors": (),
    }
    values.update(changes)
    return SolHypothesisV1(**values)


def _set(case: SolForgeCaseV1, *hypotheses: SolHypothesisV1) -> SolHypothesisSetV1:
    return SolHypothesisSetV1(
        case_sha256=case.record_sha256, model_identity="Sol 5.6 xhigh",
        reasoning_setting="xhigh", prompt_sha256=H, input_sha256="b" * 64,
        output_sha256="c" * 64, hypotheses=hypotheses,
        uncertainty="physical response is untested",
    )


def test_empty_hypotheses_return_inventory_bound_no_change(inventory_authority) -> None:
    case = _case(inventory_authority, target="austere iris without citrus or musk")
    result = compile_architectural_delta(case, _set(case))
    assert result.state is CompilationState.NO_CHANGE
    assert result.inventory_refresh_sha256 == inventory_authority[1]
    assert result.inventory_source_row_count == inventory_authority[2]
    assert result.arms == ()


def test_more_than_one_independent_intervention_is_held(inventory_authority) -> None:
    case = _case(inventory_authority)
    second = _hypothesis(hypothesis_id="H2", rank=2, material_names=("Romandolide",))
    result = compile_architectural_delta(case, _set(case, _hypothesis(), second))
    assert result.state is CompilationState.HOLD
    assert "MULTIPLE_INDEPENDENT_INTERVENTIONS" in result.blockers


def test_inventory_cannot_rewrite_the_case_ideal_architecture(inventory_authority) -> None:
    case = _case(inventory_authority)
    ideal_before = case.as_dict()["ideal_architecture"]
    result = compile_architectural_delta(case, _set(case, _hypothesis()))
    assert result.state is CompilationState.COMPILED
    assert case.as_dict()["ideal_architecture"] == ideal_before
    assert result.inventory_statuses == (("Habanolide", "OWNED"),)


def test_neroli_primary_is_held_unless_orange_blossom_is_central(inventory_authority) -> None:
    case = _case(inventory_authority, target="lemon peel over dry woods")
    hypothesis = _hypothesis(
        material_names=("Neroli EO 10%",), target_function="primary citrus",
        claim="Test Neroli as the primary citrus.",
    )
    result = compile_architectural_delta(case, _set(case, hypothesis))
    assert result.state is CompilationState.HOLD
    assert any("support-only" in blocker for blocker in result.blockers)


def test_exception_musk_needs_target_role_and_justification(inventory_authority) -> None:
    case = _case(inventory_authority, target="quiet mineral skin")
    held = compile_architectural_delta(
        case, _set(case, _hypothesis(material_names=("Tonalide",)))
    )
    explicit_case = _case(inventory_authority, target="Tonalide powder shadow study")
    accepted = compile_architectural_delta(
        explicit_case,
        _set(
            explicit_case,
            _hypothesis(
                material_names=("Tonalide",),
                rationale="explicit exception: powdery polycyclic shadow required by target",
            ),
        ),
    )
    assert held.state is CompilationState.HOLD
    assert accepted.state is CompilationState.COMPILED


def test_generic_musk_layering_is_held(inventory_authority) -> None:
    case = _case(inventory_authority)
    hypothesis = _hypothesis(
        intervention_kind="NARY_DESIGN",
        material_names=("Habanolide", "Romandolide"),
        nary_factors=("Habanolide", "Romandolide"),
        target_function="generic musk layering",
    )
    result = compile_architectural_delta(case, _set(case, hypothesis))
    assert result.state is CompilationState.HOLD
    assert any("distinct roles" in blocker for blocker in result.blockers)


def test_two_factor_musk_design_has_complete_constant_total_arms(inventory_authority) -> None:
    case = _case(inventory_authority)
    hypothesis = _hypothesis(
        intervention_kind="NARY_DESIGN",
        material_names=("Habanolide", "Romandolide"),
        nary_factors=("Habanolide", "Romandolide"),
        target_function="radiance|texture",
        rationale="Habanolide supplies radiance; Romandolide supplies texture",
    )
    result = compile_architectural_delta(case, _set(case, hypothesis))
    assert result.state is CompilationState.COMPILED
    assert tuple(arm.arm_id for arm in result.arms) == (
        "CONTROL", "HABANOLIDE", "ROMANDOLIDE", "HABANOLIDE_X_ROMANDOLIDE"
    )
    assert len({arm.total_active_mass_g for arm in result.arms}) == 1
    assert result.delta_kind == "NARY_DESIGN"
    assert result.inventory_statuses == (
        ("Habanolide", "OWNED"), ("Romandolide", "OWNED")
    )


def test_case_inventory_hash_mismatch_fails_closed(inventory_authority) -> None:
    case = _case(inventory_authority)
    case = SolForgeCaseV1.from_dict(
        {**case.as_dict(), "inventory_sha256": "f" * 64}
    )
    result = compile_architectural_delta(case, _set(case, _hypothesis()))
    assert result.state is CompilationState.HOLD
    assert "INVENTORY_HASH_MISMATCH" in result.blockers


def test_runtime_adapter_matches_the_historical_shadow_compiler(
    inventory_authority,
) -> None:
    case = _case(inventory_authority)
    for hypotheses in (
        _set(case),
        _set(case, _hypothesis()),
        _set(
            case,
            _hypothesis(),
            _hypothesis(
                hypothesis_id="H2",
                rank=2,
                material_names=("Romandolide",),
            ),
        ),
    ):
        historical = compile_architectural_delta(case, hypotheses)
        admitted = compile_runtime_architectural_delta(case, hypotheses)
        assert admitted.canonical_bytes() == historical.canonical_bytes()


def test_v2_adapter_emits_only_one_closed_evidence_delta(inventory_authority) -> None:
    case = _case(inventory_authority)
    result = compile_architectural_delta_v2(case, _set(case, _hypothesis()))

    assert result.receipt.state is EvidenceAugmentationState.AUGMENT
    assert result.receipt.delta is not None
    assert result.comparison_closure is not None
    assert result.receipt.next_action == "COMPARE:CONTROL:H1"


def test_v2_adapter_abstains_when_no_hypothesis_remains(inventory_authority) -> None:
    case = _case(inventory_authority, target="austere iris without citrus or musk")
    result = compile_architectural_delta_v2(case, _set(case))

    assert result.receipt.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert result.receipt.delta is None
    assert result.receipt.next_action is None


def test_v2_adapter_missing_inventory_path_holds(inventory_authority, tmp_path) -> None:
    case = _case(inventory_authority)
    missing = SolForgeCaseV1.from_dict(
        {**case.as_dict(), "inventory_path": str(tmp_path / "missing-v5.xlsx")}
    )
    result = compile_architectural_delta_v2(
        missing, _set(missing, _hypothesis())
    )

    assert result.receipt.state is EvidenceAugmentationState.HOLD
    assert "INVENTORY_PATH_MISSING" in result.receipt.blockers
