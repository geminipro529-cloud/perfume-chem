from __future__ import annotations

import hashlib

import pytest

from engine.perception.complexity_decision_cards import (
    DecisionCard,
    DecisionCardState,
    build_decision_card,
)


def valid_card(**overrides: object) -> DecisionCard:
    values: dict[str, object] = {
        "module_id": "construction_profile",
        "decision_kind": "TARGET_DEFINING_RELATION",
        "state": DecisionCardState.DECIDE,
        "decision_question": "Which relation creates the target's depth?",
        "decisive_evidence": ("foreground ownership changes at drydown",),
        "preserve": "recognizable iris",
        "reject": "ingredient-count reasoning",
        "controlled_comparison": "full design versus relation omission",
        "claim_ceiling": "COMPUTATIONAL_DESIGN_ONLY",
        "source_result_sha256": "a" * 64,
    }
    values.update(overrides)
    return DecisionCard(**values)  # type: ignore[arg-type]


def test_decision_card_is_hash_bound_closed_and_bounded() -> None:
    card = valid_card()

    assert card.as_dict()["schema_version"] == "complexity_decision_card_v1"
    assert len(card.to_json_bytes()) <= 1600
    assert card.card_sha256 == hashlib.sha256(card.to_json_bytes()).hexdigest()
    assert set(card.as_dict()) == {
        "schema_version",
        "module_id",
        "decision_kind",
        "state",
        "decision_question",
        "decisive_evidence",
        "preserve",
        "reject",
        "controlled_comparison",
        "claim_ceiling",
        "source_result_sha256",
    }


def test_decision_card_rejects_more_than_three_evidence_facts() -> None:
    with pytest.raises(ValueError, match="at most three"):
        valid_card(decisive_evidence=("a", "b", "c", "d"))


@pytest.mark.parametrize(
    "field_name",
    (
        "module_id",
        "decision_kind",
        "decision_question",
        "preserve",
        "reject",
        "controlled_comparison",
        "claim_ceiling",
    ),
)
def test_decision_card_rejects_blank_contract_text(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        valid_card(**{field_name: "  "})


def test_decision_card_rejects_invalid_source_hash() -> None:
    with pytest.raises(ValueError, match="source_result_sha256"):
        valid_card(source_result_sha256="not-a-hash")


def test_decision_card_rejects_empty_or_blank_evidence() -> None:
    with pytest.raises(ValueError, match="one to three"):
        valid_card(decisive_evidence=())
    with pytest.raises(ValueError, match="decisive_evidence"):
        valid_card(decisive_evidence=("valid", " "))


def test_decision_card_rejects_payload_over_byte_limit() -> None:
    card = valid_card(reject="x" * 1600)

    with pytest.raises(ValueError, match="exceeds 1600"):
        card.to_json_bytes()


def test_decision_card_requires_enum_state() -> None:
    with pytest.raises(TypeError, match="DecisionCardState"):
        valid_card(state="DECIDE")


def native_result(module_id: str) -> dict[str, object]:
    shared: dict[str, object] = {
        "result_sha256": "b" * 64,
        "claim_ceiling": "COMPUTATIONAL_DESIGN_ONLY",
    }
    results: dict[str, dict[str, object]] = {
        "construction_profile": {
            "axes": {
                "formula_structure": {
                    "status": "AVAILABLE",
                    "interpretation": "Declared row accounting only.",
                    "metrics": {"material_count": 99},
                },
                "foreground_background": {
                    "status": "AVAILABLE",
                    "interpretation": "Iris owns the opening while skin musk owns the residue.",
                    "metrics": {},
                },
            }
        },
        "complexity_expansion": {
            "pareto_frontier": [
                {
                    "title": "Dry tea shadow",
                    "origin": "NEW_V2_FRONTIER",
                    "mechanism_contract": "Add one bitter aromatic shadow behind iris.",
                    "first_discriminator": "Iris stays recognizable while the residue gains depth.",
                    "failure_mode": "Tea shadow becomes a competing theme.",
                }
            ]
        },
        "musk_design_restraint": {
            "state": "PASS",
            "architecture_mode": "SPARSE",
            "selected": [
                {
                    "material": "Zenolide",
                    "role": "DEPTH",
                    "target_function": "cool skin-depth plane without laundry bloom",
                    "why_nonredundant": "no other musk plane is present",
                }
            ],
            "issue_codes": [],
        },
        "model_admission": {
            "state": "DESIGN_REGISTRY_ADMITTED",
            "claim_scope": "DESIGN",
            "required_gates": ["M0", "M1", "M5", "M16"],
            "gate_failures": [],
            "packet_failures": [],
        },
        "model_lifecycle": {
            "state": "DRIFT_ALERT",
            "release_sha256": "c" * 64,
            "calibration_scope": "blotter-2h-v1",
            "observation_count": 12,
            "tolerance": "0.10",
            "mae": "0.17",
            "blockers": ["quarantine pending scope-matched recalibration"],
        },
        "within_sniff": {
            "state": "PASS_FOR_DESIGN",
            "pulse_count": 2,
            "onset_span_ms": "80",
            "failures": [],
            "boundary": "A passing design is not an observed perfume effect.",
        },
        "temporal_observations": {
            "state": "DESCRIPTIVE_ONLY",
            "dimension": "target_fidelity",
            "observed_cells": [
                {"timepoint": "5m", "value": "7", "dominant_system": "iris"},
                {"timepoint": "2h", "value": "5", "dominant_system": "woods"},
            ],
            "missing_cells": ["30m"],
            "disagreement": "replicate 2 reverses the apparent handoff",
            "blockers": [],
        },
        "order_balance": {
            "state": "REBUILD",
            "first_position_counts": {"A": 3, "B": 1},
            "adjacent_pair_counts": {"A->B": 3, "B->A": 1},
            "failures": ["first-position frequencies are not balanced"],
        },
        "panel_contract": {
            "decision": "hold",
            "passed_gates": ["discrimination"],
            "failed_gates": [],
            "inconclusive_gates": ["agreement"],
            "blockers": ["repeatability gate has no result"],
            "estimand": "identity-linked depth independent of pleasantness",
        },
    }
    return {**shared, **results[module_id]}


@pytest.mark.parametrize(
    ("module_id", "expected_kind"),
    [
        ("construction_profile", "TARGET_DEFINING_RELATION"),
        ("complexity_expansion", "MINIMUM_NONREDUNDANT_MOVE"),
        ("musk_design_restraint", "STRONGEST_SINGLE_MUSK"),
        ("model_admission", "EXACT_SCOPE_ADMISSION"),
        ("model_lifecycle", "RELEASE_LIFECYCLE_ACTION"),
        ("within_sniff", "APPARATUS_INTERPRETABILITY"),
        ("temporal_observations", "OBSERVED_TIME_CELLS"),
        ("order_balance", "POSITION_CARRYOVER_BALANCE"),
        ("panel_contract", "ESTIMAND_AND_CLAIM_CEILING"),
    ],
)
def test_native_projection_resolves_one_module_specific_decision(
    module_id: str, expected_kind: str
) -> None:
    card = build_decision_card(module_id, native_result(module_id), "recognizable iris")

    assert card.decision_kind == expected_kind
    assert len(card.decisive_evidence) <= 3
    assert len(card.to_json_bytes()) <= 1600
    assert card.source_result_sha256 == "b" * 64


def test_construction_projection_ignores_row_count_as_depth_evidence() -> None:
    native = native_result("construction_profile")
    native["axes"] = {
        "formula_structure": {
            "status": "AVAILABLE",
            "interpretation": "Declared row accounting only.",
            "metrics": {"material_count": 99},
        }
    }

    card = build_decision_card("construction_profile", native, "recognizable iris")

    assert card.state is DecisionCardState.HOLD
    assert "99" not in card.to_json_bytes().decode("utf-8")
    assert "count" in card.reject


def test_expansion_projection_returns_none_for_redundant_frontier() -> None:
    native = native_result("complexity_expansion")
    native["pareto_frontier"] = [
        {
            "title": "Existing iris support",
            "origin": "INHERITED_V1",
            "mechanism_contract": None,
            "first_discriminator": None,
            "failure_mode": None,
        }
    ]

    card = build_decision_card("complexity_expansion", native, "recognizable iris")

    assert card.state is DecisionCardState.NONE
    assert "minimum" in card.decision_question.casefold()


def test_musk_projection_holds_incomplete_exception_material() -> None:
    native = native_result("musk_design_restraint")
    native.update(
        state="HOLD",
        selected=[],
        issue_codes=["MUSK_EXCEPTION_REQUIRED", "HOLD_PROCUREMENT_REQUIRED"],
    )

    card = build_decision_card("musk_design_restraint", native, "quiet skin aura")

    assert card.state is DecisionCardState.HOLD
    assert "Tonalide" in card.reject
    assert "strongest-single" in card.controlled_comparison


def test_admission_projection_names_decisive_failed_gate() -> None:
    native = native_result("model_admission")
    native.update(state="HOLD", gate_failures=["M5"], packet_failures=[])

    card = build_decision_card("model_admission", native, "model scope")

    assert card.state is DecisionCardState.HOLD
    assert any("M5" in fact for fact in card.decisive_evidence)
    assert "release" in card.reject.casefold()


def test_lifecycle_projection_binds_release_and_scope() -> None:
    card = build_decision_card(
        "model_lifecycle", native_result("model_lifecycle"), "model scope"
    )

    joined = " ".join(card.decisive_evidence)
    assert "cccccccccccc" in joined
    assert "blotter-2h-v1" in joined
    assert card.state is DecisionCardState.HOLD


def test_within_sniff_projection_does_not_promote_design_to_observation() -> None:
    card = build_decision_card("within_sniff", native_result("within_sniff"), "pulse order")

    assert "not an observed perfume effect" in card.reject
    assert "apparatus" in card.controlled_comparison.casefold()


def test_temporal_projection_reports_cells_and_missingness_without_interpolation() -> None:
    card = build_decision_card(
        "temporal_observations",
        native_result("temporal_observations"),
        "iris-to-woods handoff",
    )

    encoded = card.to_json_bytes().decode("utf-8")
    assert "5m=7" in encoded
    assert "2h=5" in encoded
    assert "missing: 30m" in encoded
    assert "smooth narrative" in card.reject


def test_order_projection_names_exact_balance_alias() -> None:
    card = build_decision_card("order_balance", native_result("order_balance"), "panel")

    assert card.state is DecisionCardState.HOLD
    assert any("first-position" in fact for fact in card.decisive_evidence)
    assert "predecessor" in card.decision_question


def test_panel_projection_keeps_liking_separate_from_depth_estimand() -> None:
    card = build_decision_card("panel_contract", native_result("panel_contract"), "panel")

    assert card.state is DecisionCardState.HOLD
    assert "pleasantness" in " ".join(card.decisive_evidence)
    assert "cannot compensate" in card.reject


def test_projection_rejects_unknown_module_and_unbound_result_hash() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        build_decision_card("unknown", native_result("model_admission"), "target")
    with pytest.raises(ValueError, match="result_sha256"):
        build_decision_card("model_admission", {"state": "HOLD"}, "target")
