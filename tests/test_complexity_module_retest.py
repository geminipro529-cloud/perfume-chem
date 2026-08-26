from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from engine.perception.complexity_decision_cards import build_decision_card
from engine.perception.complexity_module_retest import (
    EXPECTED_MODULE_IDS,
    ModulePairScore,
    ModuleRetestArm,
    ModuleRetestRole,
    build_module_retest_receipt,
    decide_module_retention,
    group_cases,
    load_module_retest_cases,
    prepare_module_retest_request,
)
from engine.perception.complexity_replacement_benchmark import (
    REPLACEMENT_MODULE_IDS,
    load_replacement_benchmark_cases,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/complexity_module_retest_cases_v1.json"
FIXTURE_V2 = ROOT / "tests/fixtures/complexity_module_retest_cases_v2.json"
REPLACEMENT_V4 = (
    ROOT / "tests/fixtures/complexity_replacement_benchmark_cases_v4.json"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_corpus_has_six_role_complete_cases_per_module() -> None:
    cases = load_module_retest_cases(FIXTURE)
    by_module = group_cases(cases)

    assert set(by_module) == set(EXPECTED_MODULE_IDS)
    assert all(len(items) == 6 for items in by_module.values())
    assert all(
        [item.phase for item in items].count("SCREEN") == 3
        and [item.phase for item in items].count("CONFIRM") == 3
        for items in by_module.values()
    )
    assert all(
        {item.role for item in items}
        == {
            ModuleRetestRole.POSITIVE,
            ModuleRetestRole.SAFE_COUNTERCASE,
            ModuleRetestRole.CRITICAL_TRAP,
            ModuleRetestRole.INVENTORY_MISMATCH,
            ModuleRetestRole.CONTROL,
            ModuleRetestRole.UNSEEN_VARIANT,
        }
        for items in by_module.values()
    )


def test_corpus_sidecar_locks_exact_bytes() -> None:
    expected = FIXTURE.with_suffix(".sha256").read_text(encoding="ascii").strip()

    assert expected == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def test_v4_replacement_corpus_is_separate_from_retired_module_corpus() -> None:
    expected = REPLACEMENT_V4.with_suffix(".sha256").read_text(
        encoding="ascii"
    ).split()[0]
    assert expected == hashlib.sha256(REPLACEMENT_V4.read_bytes()).hexdigest()

    cases = load_replacement_benchmark_cases(REPLACEMENT_V4)
    assert {case.module_id for case in cases} == set(REPLACEMENT_MODULE_IDS)
    assert not {case.module_id for case in cases}.intersection(EXPECTED_MODULE_IDS)


def test_v2_corpus_inherits_complete_matrix_and_binds_new_inventory_materials() -> None:
    cases = load_module_retest_cases(FIXTURE_V2)
    by_module = group_cases(cases)

    assert set(by_module) == set(EXPECTED_MODULE_IDS)
    assert all(len(items) == 6 for items in by_module.values())
    named = {
        material: state
        for case in cases
        for material, state in case.inventory_state.items()
        if material
        in {
            "Neroli EO 10% in DPG",
            "Ambrettolide 10% in DPG",
            "Romandolide",
            "Habanolide",
            "Ethylene Brassylate",
        }
    }
    assert named == {
        "Neroli EO 10% in DPG": "OWNED_10_PERCENT_DPG_ONLY_SUPPORT_ONLY",
        "Ambrettolide 10% in DPG": (
            "PLANNED_ACQUISITION_DESIGN_AVAILABLE_PROCUREMENT_PENDING"
        ),
        "Romandolide": "OWNED_NEAT_AS_SUPPLIED",
        "Habanolide": "OWNED_NEAT_AS_SUPPLIED",
        "Ethylene Brassylate": "MISSING_HIGH_VALUE_EXPANSION",
    }

    neroli_case = next(item for item in cases if item.case_id == "CM-CIT-01")
    neroli_card = build_decision_card(
        neroli_case.module_id,
        neroli_case.native_result,
        neroli_case.target_identity,
    )
    assert "support stock" in " ".join(neroli_card.decisive_evidence)


def test_v2_corpus_sidecar_locks_exact_bytes() -> None:
    expected = FIXTURE_V2.with_suffix(".sha256").read_text(
        encoding="ascii"
    ).strip()

    assert expected == hashlib.sha256(FIXTURE_V2.read_bytes()).hexdigest()


def test_treatment_diff_is_only_one_card_and_placebo_is_length_matched() -> None:
    case = load_module_retest_cases(FIXTURE)[0]
    card = build_decision_card(case.module_id, case.native_result, case.target_identity)
    control = prepare_module_retest_request(case, ModuleRetestArm.CONTROL, card=None)
    treatment = prepare_module_retest_request(
        case, ModuleRetestArm.TREATMENT, card=card
    )
    placebo = prepare_module_retest_request(case, ModuleRetestArm.PLACEBO, card=card)

    assert "decision_card" not in control.prompt_payload
    assert treatment.prompt_payload["decision_card"] == card.as_dict()
    assert abs(placebo.card_byte_count - treatment.card_byte_count) <= 16
    assert placebo.prompt_payload["decision_card"] != card.as_dict()
    assert case.module_id not in json.dumps(
        placebo.prompt_payload["decision_card"], sort_keys=True
    )
    assert control.common_input_sha256 == treatment.common_input_sha256
    assert control.common_input_sha256 == placebo.common_input_sha256
    assert len({control.nonce, treatment.nonce, placebo.nonce}) == 3


def test_request_hashes_bind_exact_prompt_and_card_bytes() -> None:
    case = load_module_retest_cases(FIXTURE)[0]
    card = build_decision_card(case.module_id, case.native_result, case.target_identity)
    request = prepare_module_retest_request(case, ModuleRetestArm.TREATMENT, card=card)

    assert request.prompt_sha256 == hashlib.sha256(
        canonical_bytes(request.prompt_payload)
    ).hexdigest()
    assert request.card_sha256 == card.card_sha256
    assert request.card_byte_count == len(card.to_json_bytes())
    assert request.reasoning_effort == "Extra High"
    assert request.model_requirement == "ChatGPT 5.6 Sol Extra High"
    assert request.context_requirement == "FRESH_PROJECTLESS_CONVERSATION"


def test_request_rejects_missing_or_wrong_module_card() -> None:
    cases = load_module_retest_cases(FIXTURE)
    case = cases[0]
    other = next(item for item in cases if item.module_id != case.module_id)
    wrong_card = build_decision_card(
        other.module_id, other.native_result, other.target_identity
    )

    with pytest.raises(ValueError, match="requires a decision card"):
        prepare_module_retest_request(case, ModuleRetestArm.TREATMENT, card=None)
    with pytest.raises(ValueError, match="does not match"):
        prepare_module_retest_request(
            case, ModuleRetestArm.TREATMENT, card=wrong_card
        )
    with pytest.raises(ValueError, match="must not receive"):
        prepare_module_retest_request(case, ModuleRetestArm.CONTROL, card=wrong_card)


def pair_scores(
    deltas: tuple[int, ...] = (8, 6, 5, 5, 0, -1),
    *,
    critical_regression: bool = False,
    safe_countercase_pass: bool = True,
    critical_trap_pass: bool = True,
    specialist_checks_pass: bool = True,
) -> tuple[ModulePairScore, ...]:
    roles = tuple(ModuleRetestRole)
    return tuple(
        ModulePairScore(
            module_id="construction_profile",
            case_id=f"CM-CON-{index + 1:02d}",
            role=roles[index],
            treatment_score=Decimal(80 + delta),
            control_score=Decimal(80),
            critical_regression=critical_regression and index == 0,
            safe_countercase_pass=(
                safe_countercase_pass
                if roles[index] is ModuleRetestRole.SAFE_COUNTERCASE
                else True
            ),
            critical_trap_pass=(
                critical_trap_pass
                if roles[index] is ModuleRetestRole.CRITICAL_TRAP
                else True
            ),
            specialist_checks_pass=specialist_checks_pass,
        )
        for index, delta in enumerate(deltas)
    )


def test_four_wins_median_five_no_critical_and_placebo_gain_passes() -> None:
    decision = decide_module_retention(pair_scores(), placebo_delta=Decimal("3"))

    assert decision.state == "REACTIVATE"
    assert decision.treatment_wins == 4
    assert decision.median_paired_delta == Decimal("5")


@pytest.mark.parametrize(
    ("scores", "placebo_delta", "reason"),
    [
        (pair_scores((8, 6, 5, 0, 0, -1)), Decimal("3"), "FOUR_WINS_REQUIRED"),
        (pair_scores((8, 6, 4, 4, 1, -1)), Decimal("3"), "MEDIAN_GAIN_BELOW_FIVE"),
        (
            pair_scores(critical_regression=True),
            Decimal("3"),
            "CRITICAL_REGRESSION",
        ),
        (
            pair_scores(safe_countercase_pass=False),
            Decimal("3"),
            "SAFE_COUNTERCASE_FAILED",
        ),
        (
            pair_scores(critical_trap_pass=False),
            Decimal("3"),
            "CRITICAL_TRAP_NOT_PREVENTED",
        ),
        (
            pair_scores(specialist_checks_pass=False),
            Decimal("3"),
            "SPECIALIST_CHECK_FAILED",
        ),
        (pair_scores(), Decimal("0"), "PLACEBO_NOT_BEATEN"),
    ],
)
def test_each_noncompensatory_failure_retires(
    scores: tuple[ModulePairScore, ...], placebo_delta: Decimal, reason: str
) -> None:
    decision = decide_module_retention(scores, placebo_delta=placebo_delta)

    assert decision.state == "RETIRED_BENCHMARK_UNDERPERFORMER"
    assert reason in decision.reasons


def test_retention_rejects_incomplete_or_mixed_module_evidence() -> None:
    with pytest.raises(ValueError, match="exactly six"):
        decide_module_retention(pair_scores()[:5], placebo_delta=Decimal("3"))
    mixed = list(pair_scores())
    mixed[0] = ModulePairScore(
        module_id="model_admission",
        case_id=mixed[0].case_id,
        role=mixed[0].role,
        treatment_score=mixed[0].treatment_score,
        control_score=mixed[0].control_score,
        critical_regression=False,
        safe_countercase_pass=True,
        critical_trap_pass=True,
        specialist_checks_pass=True,
    )
    with pytest.raises(ValueError, match="one module"):
        decide_module_retention(tuple(mixed), placebo_delta=Decimal("3"))


def test_retest_receipt_is_hash_bound_and_grants_no_authority() -> None:
    decision = decide_module_retention(pair_scores(), placebo_delta=Decimal("3"))
    receipt = build_module_retest_receipt(
        run_id="CMR-20260822-decision-cards-v1",
        corpus_sha256="a" * 64,
        registry_sha256="b" * 64,
        decisions=(decision,),
        execution_artifacts=(
            {
                "path": "output/complexity_module_retest/run/response.json",
                "sha256": "c" * 64,
            },
        ),
        telemetry_state="NOT_EXPOSED",
    )

    assert receipt["schema_version"] == "complexity_module_retest_receipt_v1"
    assert receipt["authority"] == {
        "formula": False,
        "inventory": False,
        "physical_execution": False,
        "sensory": False,
        "safety": False,
        "publication": False,
        "release": False,
    }
    semantic_hash = receipt.pop("semantic_receipt_sha256")
    assert semantic_hash == hashlib.sha256(canonical_bytes(receipt)).hexdigest()
