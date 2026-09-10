from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from engine.formulation_intelligence.contracts import AuthorityCeiling, PlaneId
from engine.formulation_intelligence.deep_plane_runtime import (
    DeepPlaneRuntimeReceipt,
    DeepPlaneRuntimeRequest,
)
from engine.perception.dhi_2011_architecture import DHI2011EvidenceTier
from engine.perception.dhi_2011_deep_plane import (
    BASKET_LABELS,
    PARENT_FORMULA_REF,
    DHI2011ClaimStatus,
    DHI2011CompounderCommandV1,
    DHI2011DeepPlaneProgramV1,
    build_default_dhi_2011_deep_plane_program,
)
from scripts.verify_formula_workflow import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / "formulas" / "DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md"

RESOLUTION_IDS = (
    "deep:target-silhouette",
    "deep:perceptual-layer-graph",
    "deep:material-role-geometry",
    "deep:compounder-and-experiment-control",
)
ARTISTIC_LAYER_IDS = (
    "layer:lavender-veil",
    "layer:ambrette-pear-talc-membrane",
    "layer:orris-body",
    "layer:amber-vanillic-shadow",
    "layer:cedar-vetiver-counterform",
    "layer:musky-skin-echo",
)

EXPECTED_ROWS = (
    (1, 1, "Hedione", 140.0, 140.0),
    (2, 1, "Iso E Super", 140.0, 140.0),
    (3, 1, "Benzyl Salicylate", 60.0, 60.0),
    (4, 1, "Benzyl Benzoate", 40.0, 40.0),
    (5, 2, "Vetiver EO (India)", 140.0, 140.0),
    (6, 3, "Cedarwood oil Virginia", 250.0, 250.0),
    (7, 3, "Cashmeran", 60.0, 60.0),
    (8, 3, "Sandalore", 60.0, 60.0),
    (9, 5, "Vetival", 80.0, 80.0),
    (10, 6, "Ambrettolide", 1600.0, 160.0),
    (11, 6, "Ethylene Brassylate", 870.0, 870.0),
    (12, 6, "Romandolide", 210.0, 210.0),
    (13, 7, "Lavender EO High Altitude", 110.0, 110.0),
    (14, 7, "Linalyl Acetate", 70.0, 70.0),
    (15, 7, "Linalool", 20.0, 20.0),
    (16, 9, "Mimosa Absolute", 80.0, 8.0),
    (17, 9, "Osmanthus Absolute", 20.0, 2.0),
    (18, 11, "Alpha Isomethyl Ionone (Methyl Ionone Pure)", 420.0, 420.0),
    (19, 11, "Alpha Ionone", 180.0, 180.0),
    (20, 11, "Alpha Irone", 180.0, 18.0),
    (21, 11, "Dihydro Beta Ionone", 100.0, 100.0),
    (22, 11, "Irotyl", 80.0, 80.0),
    (23, 11, "Ultralia", 60.0, 60.0),
    (24, 11, "Orivone", 20.0, 20.0),
    (25, 11, "Carrot Seed EO", 10.0, 10.0),
    (26, 12, "Tonkarome", 310.0, 62.0),
    (27, 12, "Isobutavan", 140.0, 140.0),
    (28, 15, "Verdox", 280.0, 280.0),
    (29, 15, "Benzyl Acetate", 220.0, 220.0),
    (30, 15, "Ethyl 2-Methylbutyrate", 50.0, 0.05),
)

EXPECTED_BASKET_CHECKPOINTS = (
    (1, "COMPOUND", (1, 2, 3, 4), 380.0, 380.0),
    (2, "COMPOUND", (5,), 140.0, 520.0),
    (3, "COMPOUND", (6, 7, 8), 370.0, 890.0),
    (4, "SKIP", (), 0.0, 890.0),
    (5, "COMPOUND", (9,), 80.0, 970.0),
    (6, "COMPOUND", (10, 11, 12), 2680.0, 3650.0),
    (7, "COMPOUND", (13, 14, 15), 200.0, 3850.0),
    (8, "SKIP", (), 0.0, 3850.0),
    (9, "COMPOUND", (16, 17), 100.0, 3950.0),
    (10, "SKIP", (), 0.0, 3950.0),
    (11, "COMPOUND", (18, 19, 20, 21, 22, 23, 24, 25), 1050.0, 5000.0),
    (12, "COMPOUND", (26, 27), 450.0, 5450.0),
    (13, "SKIP", (), 0.0, 5450.0),
    (14, "SKIP", (), 0.0, 5450.0),
    (15, "COMPOUND", (28, 29, 30), 550.0, 6000.0),
    (16, "SKIP", (), 0.0, 6000.0),
    (17, "SKIP", (), 0.0, 6000.0),
)


@pytest.fixture(scope="module")
def program() -> DHI2011DeepPlaneProgramV1:
    return build_default_dhi_2011_deep_plane_program()


def test_deep_plane_recurses_by_resolution_across_every_plane(program):
    layers = program.deep_plane_request.layers
    assert tuple(item.layer_id for item in layers) == RESOLUTION_IDS
    assert tuple(item.depth for item in layers) == (0, 1, 2, 3)
    assert tuple(item.parent_layer_id for item in layers) == (
        None,
        RESOLUTION_IDS[0],
        RESOLUTION_IDS[1],
        RESOLUTION_IDS[2],
    )
    for layer in layers:
        assert {item.plane_id for item in layer.assessments} == set(PlaneId)
        assert len(layer.assessments) == 13


def test_all_six_artistic_layers_air_seam_and_smoothness_probe_are_explicit(program):
    command = program.compounder_command
    assert command.artistic_layer_order == ARTISTIC_LAYER_IDS
    assert tuple(item.field_id for item in command.structural_fields) == ("field:iris-air-seam",)
    probe_ids = {item.probe_id for item in program.architecture_request.controlled_probes}
    assert {
        "probe:dhi2011:pear-continuum",
        "probe:dhi2011:talc-cushion",
        "probe:dhi2011:musk-axes",
        "probe:dhi2011:seam-smoothness",
    }.issubset(probe_ids)
    for layer in command.layer_commands:
        assert layer.incoming_transition_ids or layer.outgoing_transition_ids


def test_compounder_packet_is_exact_basket_first_and_formula_bound(program):
    command = program.compounder_command
    observed = tuple(
        (row.step, row.basket, row.engine_material, row.raw_ul, row.nominal_active_ul)
        for row in command.rows
    )
    assert observed == EXPECTED_ROWS
    assert len(command.rows) == 30
    assert sum(row.raw_ul for row in command.rows) == pytest.approx(6000.0)
    assert sum(row.nominal_active_ul for row in command.rows) == pytest.approx(4010.05)
    assert min(row.raw_ul for row in command.rows) == 10.0
    for basket in sorted({row.basket for row in command.rows}):
        amounts = [row.raw_ul for row in command.rows if row.basket == basket]
        assert amounts == sorted(amounts, reverse=True)
    parsed = parse_formula_markdown(FORMULA_PATH)[0]
    assert parsed["ingredients_ul"] == {
        row.engine_material: row.raw_ul for row in command.rows
    }
    assert parsed["dilutions"] == {
        row.engine_material: row.nominal_active_ul / row.raw_ul
        for row in command.rows
    }


def test_every_target_layer_has_material_depth_and_transition_bridges(program):
    command = program.compounder_command
    by_node = {
        node: [row.engine_material for row in command.rows if node in row.architecture_node_ids]
        for node in (*ARTISTIC_LAYER_IDS, "field:iris-air-seam")
    }
    assert all(len(materials) >= 3 for materials in by_node.values())
    assert len(by_node["layer:ambrette-pear-talc-membrane"]) >= 8
    assert len(by_node["layer:orris-body"]) >= 10
    assert len(by_node["layer:musky-skin-echo"]) >= 8
    transition_bridges = {
        "transition:aromatic-fold": {"Linalyl Acetate", "Linalool", "Ethyl 2-Methylbutyrate"},
        "transition:membrane-wrap": {"Ambrettolide", "Mimosa Absolute", "Alpha Ionone"},
        "transition:warmth-underlay": {"Orivone", "Tonkarome", "Isobutavan"},
        "transition:dry-wood-reveal": {"Dihydro Beta Ionone", "Vetival", "Sandalore"},
        "transition:talc-musk-recurrence": {"Ambrettolide", "Ethylene Brassylate", "Ultralia"},
        "transition:wood-fibre-settling": {"Cashmeran", "Iso E Super", "Romandolide"},
    }
    assert {item.transition_id for item in program.architecture_request.transitions} == set(transition_bridges)
    row_names = {row.engine_material for row in command.rows}
    assert all(bridges.issubset(row_names) for bridges in transition_bridges.values())


def test_all_seventeen_basket_checkpoints_are_arithmetically_bound(program):
    command = program.compounder_command
    observed = tuple(
        (
            checkpoint.basket,
            checkpoint.action,
            checkpoint.row_steps,
            checkpoint.subtotal_ul,
            checkpoint.running_total_ul,
        )
        for checkpoint in command.basket_checkpoints
    )
    assert observed == EXPECTED_BASKET_CHECKPOINTS
    assert tuple(checkpoint.basket for checkpoint in command.basket_checkpoints) == tuple(BASKET_LABELS)
    assert command.basket_checkpoints[-1].running_total_ul == 6000.0


def test_packet_binds_rejected_parent_and_exact_positive_addition(program):
    command = program.compounder_command
    assert command.mode == "EXPLORATORY_RAW_VOLUME_BUILD"
    assert command.immediate_parent_ref == PARENT_FORMULA_REF
    assert "successor to the rejected 14-row control" in command.parent_semantics
    assert command.raw_concentrate_ul == 6000.0
    assert command.ethanol_96_addition_ul == 24000.0
    assert command.nominal_finished_ul == 30000.0
    assert "not a q.s.-to-volume instruction" in command.finish_convention
    assert command.raw_volume_recipe_complete is True
    assert command.agent_handoff_ready is True
    assert command.basket_compounding_card_ready is True
    assert command.component_count_used_as_complexity is False
    assert any("never silently substitute" in item for item in command.model_instructions)
    assert any("smoothness and endpoint legibility separately" in item for item in command.model_instructions)


def test_three_musks_have_nonredundant_bound_functions(program):
    rows = {row.engine_material: row for row in program.compounder_command.rows}
    assert rows["Ambrettolide"].function_ids == ("fn:ambrette-mediator", "fn:skin-closure")
    assert rows["Ethylene Brassylate"].function_ids == ("fn:talc-cushion", "fn:musk-velvet")
    assert rows["Romandolide"].function_ids == ("fn:musk-diffusion",)


def test_unresolved_stock_math_and_natural_composites_are_exposed(program):
    statuses = {row.engine_material: row.analytical_status for row in program.compounder_command.rows}
    assert "W_W_STOCK" in statuses["Ambrettolide"]
    assert "STOCK_SOLUTION_DENSITY_UNMEASURED" in statuses["Ambrettolide"]
    assert "DENSITY_UNMEASURED" in statuses["Alpha Irone"]
    assert "DENSITY_UNMEASURED" in statuses["Tonkarome"]
    for natural in ("Vetiver EO (India)", "Cedarwood oil Virginia", "Lavender EO High Altitude", "Carrot Seed EO"):
        assert "COMPOSITE_OAV_SCREEN_ONLY" in statuses[natural]
    assert any("complete embedded DPG, DEP, and TEC" in item for item in program.compounder_command.unresolved_facts)


def test_historical_fact_and_perfumer_mechanism_remain_separate(program):
    commands = {item.layer_id: item for item in program.compounder_command.layer_commands}
    wood = commands["layer:cedar-vetiver-counterform"]
    assert DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT in wood.evidence_tiers
    assert DHI2011EvidenceTier.PERFUMER_INFERENCE in wood.evidence_tiers
    assert DHI2011ClaimStatus.TEMPORAL_BEHAVIOR_PREDICTED_NOT_OBSERVED in wood.claim_statuses


def test_deep_plane_round_trips_and_hashes_are_deterministic(program):
    second = build_default_dhi_2011_deep_plane_program()
    assert second.record_sha256 == program.record_sha256
    assert second.deep_plane_request.content_sha256 == program.deep_plane_request.content_sha256
    assert second.deep_plane_receipt.content_sha256 == program.deep_plane_receipt.content_sha256
    assert second.compounder_command.record_sha256 == program.compounder_command.record_sha256
    assert DeepPlaneRuntimeRequest.from_dict(program.deep_plane_request.as_dict()) == program.deep_plane_request
    assert DeepPlaneRuntimeReceipt.from_dict(program.deep_plane_receipt.as_dict()) == program.deep_plane_receipt


def test_row_parent_and_checkpoint_tampering_fail_closed(program):
    command = program.compounder_command
    with pytest.raises(ValueError, match="formula_rows_sha256"):
        replace(command, formula_rows_sha256="0" * 64)
    with pytest.raises(ValueError, match="rejected 14-row parent"):
        replace(command, immediate_parent_ref=None)
    first = command.basket_checkpoints[0]
    with pytest.raises(ValueError, match="subtotal"):
        replace(
            command,
            basket_checkpoints=(
                replace(first, subtotal_ul=first.subtotal_ul + 1.0, running_total_ul=first.running_total_ul + 1.0),
                *command.basket_checkpoints[1:],
            ),
        )


def test_every_downstream_authority_remains_false(program):
    command = program.compounder_command
    receipt = program.deep_plane_receipt
    assert receipt.candidate_state == "future_candidate_not_validated"
    assert receipt.authority_ceiling is AuthorityCeiling.WITHHELD
    for item in fields(receipt):
        if item.name.endswith("authority") or item.name.endswith("authorized"):
            assert getattr(receipt, item.name) is False
    for item in fields(DHI2011CompounderCommandV1):
        if item.name.endswith("authority") or item.name.endswith("authorized"):
            assert getattr(command, item.name) is False
    for item in fields(DHI2011DeepPlaneProgramV1):
        if item.name.endswith("authority") or item.name.endswith("authorized"):
            assert getattr(program, item.name) is False
