from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.architectural_delta import _load_execution_inventory_catalog
from engine.sensory.ledger import ObservationCellKey, TemporalObservationCell
from engine.sensory.order_balance import generate_williams_schedule
from engine.solforge.contracts import (
    AUTHORITY_FLAGS_FALSE,
    DecisionState,
    ExecutionReceiptV1,
    SolForgeCaseState,
    SolForgeCaseV1,
    SolHypothesisSetV1,
    SolHypothesisV1,
)
from engine.solforge.orchestrator import SolForgeStage, run_solforge_shadow

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/solforge/vertical_slice_cases_v1.json"
FIXTURE_HASH = ROOT / "tests/fixtures/solforge/vertical_slice_cases_v1.sha256"


def _fixture() -> dict:
    expected = FIXTURE_HASH.read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == expected
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def inventory_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, str, int]:
    rows = _fixture()["inventory_rows"]
    workbook_path = tmp_path / "inventory-v5.xlsx"
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Current Inventory Master")
    for row in (["title"], ["authority"], [], []):
        sheet.append(row)
    sheet.append(
        [
            "Canonical material",
            "Status",
            "Actual stock(s)",
            "Can prepare",
            "Family",
            "Alias / non-equivalent",
            "Formula-use policy",
            "User note",
        ]
    )
    for material, status, stock in rows:
        sheet.append([material, status, stock, None, "test", None, "test only", None])
    workbook.save(workbook_path)
    workbook.close()
    workbook_sha256 = hashlib.sha256(workbook_path.read_bytes()).hexdigest()

    source = ROOT / "data/governance/complexity_inventory_catalog_v1.json"
    catalog = json.loads(source.read_text(encoding="utf-8"))
    catalog["authority"]["workbook_sha256"] = workbook_sha256
    catalog["authority"]["current_record_count"] = len(rows)
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
        for index, (material, status, stock) in enumerate(rows)
    ]
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    from engine.perception import complexity_inventory

    monkeypatch.setattr(
        complexity_inventory, "_EXPECTED_WORKBOOK_SHA256", workbook_sha256
    )
    monkeypatch.setattr(complexity_inventory, "_CATALOG_PATH", catalog_path)
    return workbook_path, workbook_sha256, len(rows)


def _case(case_data: dict, authority: tuple[Path, str, int]) -> SolForgeCaseV1:
    path, digest, _ = authority
    return SolForgeCaseV1(
        state=SolForgeCaseState.READY,
        case_id=case_data["case_id"],
        target_identity=case_data["target_identity"],
        ideal_architecture=case_data["ideal_architecture"],
        current_inventory_build=case_data["current_inventory_build"],
        inventory_path=str(path),
        inventory_sha256=digest,
        formula_sha256=sha256_hex(
            canonical_json_bytes(case_data["current_inventory_build"])
        ),
        dose_receipt_sha256=sha256_hex(
            canonical_json_bytes(
                {"case_id": case_data["case_id"], "test_only": True}
            )
        ),
        constraints=("constant total", "shadow only"),
        criterion=case_data["criterion"],
        forbidden_claims=("liking", "safety", "release"),
    )


def _hypotheses(case: SolForgeCaseV1, case_data: dict) -> SolHypothesisSetV1:
    value = case_data["hypothesis"]
    hypotheses: tuple[SolHypothesisV1, ...] = ()
    if value is not None:
        hypotheses = (
            SolHypothesisV1(
                hypothesis_id=value["hypothesis_id"],
                rank=1,
                claim=value["claim"],
                target_function=value["target_function"],
                material_names=tuple(value["material_names"]),
                intervention_kind=value["intervention_kind"],
                expected_behavior=value["expected_behavior"],
                rationale=value["rationale"],
                uncertainty=0.5,
                evidence_refs=("d" * 64,),
                nary_factors=tuple(value["nary_factors"]),
            ),
        )
    return SolHypothesisSetV1(
        case_sha256=case.record_sha256,
        model_identity="FROZEN_TEST_HYPOTHESIS",
        reasoning_setting="deterministic-fixture",
        prompt_sha256="a" * 64,
        input_sha256="b" * 64,
        output_sha256="c" * 64,
        hypotheses=hypotheses,
        uncertainty="Synthetic observations do not establish physical performance.",
    )


def _execution(compiled, *, criterion: str) -> ExecutionReceiptV1:
    arm_ids = tuple(arm.arm_id for arm in compiled.arms)
    schedule = generate_williams_schedule(arm_ids)
    assessors = ("A1", "A2")
    scores = {arm_id: float(index + 1) for index, arm_id in enumerate(arm_ids)}
    observations = [
        TemporalObservationCell(
            key=ObservationCellKey(
                protocol_id="SOLFORGE-VERTICAL-SLICE-V1",
                sample_id=arm_id,
                assessor_id=assessor,
                repeat_id="R1",
                time_seconds=0,
                endpoint_id=criterion,
            ),
            observation_id=f"OBS-{arm_id}-{assessor}",
            value=scores[arm_id] + (0.1 if assessor == "A2" else 0),
            presentation_sequence_id=f"SEQ-{assessor}",
            presentation_position=index + 1,
        ).as_dict()
        for assessor in assessors
        for index, arm_id in enumerate(arm_ids)
    ]
    comparisons: list[dict[str, object]] = []
    comparison_index = 0
    for left, right in itertools.combinations(arm_ids, 2):
        winner = right if scores[right] > scores[left] else left
        for assessor, first in (("A1", left), ("A2", right)):
            comparison_index += 1
            comparisons.append(
                {
                    "left_item": left,
                    "right_item": right,
                    "preferred_item": winner,
                    "comparison_id": f"TRAIN-{comparison_index:03d}",
                    "assessor_id": assessor,
                    "protocol_id": "SOLFORGE-VERTICAL-SLICE-V1",
                    "criterion_id": criterion,
                    "time_seconds": 0,
                    "first_presented_item": first,
                    "repeat_id": "R1",
                    "partition": "training",
                }
            )
        comparison_index += 1
        comparisons.append(
            {
                "left_item": left,
                "right_item": right,
                "preferred_item": winner,
                "comparison_id": f"HELDOUT-{comparison_index:03d}",
                "assessor_id": "A1",
                "protocol_id": "SOLFORGE-VERTICAL-SLICE-V1",
                "criterion_id": criterion,
                "time_seconds": 0,
                "first_presented_item": right,
                "repeat_id": "R1",
                "partition": "heldout",
            }
        )
    context = {
        "synthetic": True,
        "protocol_scope": {
            "protocol_id": "SOLFORGE-VERTICAL-SLICE-V1",
            "sample_ids": list(arm_ids),
            "assessor_ids": list(assessors),
            "repeat_ids": ["R1"],
            "timepoints_seconds": [0.0],
            "endpoint_ids": [criterion],
            "schedule_sha256": schedule.schedule_sha256,
            "within_sniff": False,
            "within_sniff_apparatus_qualified": False,
            "within_sniff_timing_protocol_qualified": False,
            "require_repeatability": False,
            "maximum_within_assessor_repeat_spread": None,
        },
        "schedule": schedule.as_dict(),
        "observations": observations,
        "safety_events": [],
        "comparisons": comparisons,
        "preference_fit": {
            "minimum_comparisons": 2,
            "minimum_heldout_comparisons": 1,
            "declared_baseline_accuracy": 0.0,
            "bootstrap_replicates": 16,
            "bootstrap_seed": 20260826,
            "require_scoped_validation": True,
        },
        "formula_build_sha256": compiled.case_sha256,
        "hedonic_scope": "OWNER",
    }
    return ExecutionReceiptV1(
        compiled_experiment_sha256=compiled.record_sha256,
        executor="SYNTHETIC_VERTICAL_SLICE_FIXTURE",
        execution_context=context,
        sample_sha256=tuple(
            (arm.arm_id, arm.sample_sha256) for arm in compiled.arms
        ),
        deviations=(),
        test_only=True,
    )


@pytest.mark.parametrize("case_data", _fixture()["cases"], ids=lambda row: row["case_id"])
def test_four_case_vertical_slice_is_deterministic_and_fail_closed(
    case_data: dict, inventory_authority: tuple[Path, str, int]
) -> None:
    case = _case(case_data, inventory_authority)
    hypotheses = _hypotheses(case, case_data)
    first = run_solforge_shadow(case, hypotheses)

    if case_data["expected_decision"] == "NO_CHANGE":
        final = first
    else:
        assert first.stage is SolForgeStage.EXPORTED
        assert first.compiled_experiment is not None
        execution = _execution(first.compiled_experiment, criterion=case.criterion)
        final = run_solforge_shadow(case, hypotheses, execution=execution)
        replay = run_solforge_shadow(case, hypotheses, execution=execution)
        assert final.decision_receipt.canonical_bytes() == replay.decision_receipt.canonical_bytes()

    assert final.stage.value == case_data["expected_stage"]
    assert final.decision_receipt.decision is DecisionState(case_data["expected_decision"])
    assert final.compiled_experiment is not None
    assert final.compiled_experiment.case_sha256 == case.record_sha256
    assert final.compiled_experiment.hypothesis_set_sha256 == hypotheses.record_sha256
    assert final.compiled_experiment.inventory_refresh_sha256 == inventory_authority[1]
    assert final.compiled_experiment.inventory_source_row_count == inventory_authority[2]
    assert [arm.arm_id for arm in final.compiled_experiment.arms] == case_data[
        "expected_arm_ids"
    ]
    assert len(
        {arm.total_active_mass_g for arm in final.compiled_experiment.arms}
    ) <= 1
    assert final.decision_receipt.as_dict()["authority_flags"] == AUTHORITY_FLAGS_FALSE
    if final.backend_export is not None:
        assert final.backend_export["schema_version"] == "solforge_backend_lab_export_v1"
        assert final.backend_export["database_write_authorized"] is False
        assert final.backend_export["physical_execution_authorized"] is False
        assert final.backend_export["publication_authorized"] is False


def test_vertical_slice_reparses_every_inventory_row_and_preserves_statuses(
    inventory_authority: tuple[Path, str, int]
) -> None:
    path, _, row_count = inventory_authority
    catalog = _load_execution_inventory_catalog(None, str(path))
    expected = {
        "Neroli EO 10%": "OWNED",
        "Habanolide": "OWNED",
        "Romandolide": "OWNED",
        "Ambrettolide 10%": "PLANNED_ACQUISITION",
        "Ethylene Brassylate": "MISSING",
    }
    assert catalog.current_record_count == row_count == len(_fixture()["inventory_rows"])
    assert {
        material: catalog.project(material).availability.value for material in expected
    } == expected


def test_vertical_slice_fixture_authority_is_exactly_all_false() -> None:
    assert _fixture()["authority_flags"] == AUTHORITY_FLAGS_FALSE
