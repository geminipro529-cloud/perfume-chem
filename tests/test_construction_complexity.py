from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from engine.perception.construction_complexity import (
    ConstructionComplexityInputs,
    NegativeSpaceProbe,
    analyze_construction_complexity,
)
from engine.scientific_contract import EvidenceDescriptor, ScientificClass
from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest


@dataclass(frozen=True)
class _Material:
    name: str
    oav: float | None
    intensity: float | None
    is_known: bool = True
    is_opaque_preblend: bool = False
    functional_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class _State:
    materials: tuple[_Material, ...]


@dataclass(frozen=True)
class _Frame:
    label: str
    t_seconds: float
    state: _State


def _frame(label: str, seconds: float, *rows: tuple[str, float, float]) -> _Frame:
    return _Frame(
        label,
        seconds,
        _State(tuple(_Material(name, oav, intensity) for name, oav, intensity in rows)),
    )


def test_profile_separates_axes_and_never_emits_an_overall_score() -> None:
    materials = tuple(
        _Material(
            f"M{index:02d}",
            2.0,
            1.0,
            functional_groups=("terpene_alcohol",),
        )
        for index in range(40)
    )
    state = _State(materials)
    profile = analyze_construction_complexity(
        state,
        (_Frame("opening", 0.0, state),),
    ).as_dict()

    assert "overall_score" not in json.dumps(profile, sort_keys=True)
    assert "olfactory_white_risk" not in json.dumps(profile, sort_keys=True)
    assert profile["decision_contract"] == {
        "complexity_authority": "WITHHELD",
        "candidate_only": True,
        "universal_row_count_gate_authorized": False,
        "aggregate_score_authorized": False,
        "automatic_rebuild_from_row_count_authorized": False,
        "hard_gate_override_authorized": False,
        "candidate_dimensions": [
            "recognizer_preservation",
            "structural_organization",
            "interaction",
            "temporal_shape",
            "texture",
            "contrast",
            "resilience_robustness",
            "post_ablation_effective_complexity",
            "execution_stock_readiness",
            "evidence_uncertainty",
        ],
        "noncompensatory_external_gates": [
            "inventory_identity_and_stock",
            "active_dose_and_basis",
            "strict_oav_evidence",
            "physical_chemistry",
            "safety_and_regulatory",
            "provenance_and_source_use",
            "physical_observation",
        ],
    }
    assert profile["axes"]["formula_structure"]["metrics"]["material_count"] == 40
    assert profile["axes"]["descriptor_gradient"]["status"] == "UNKNOWN"
    assert profile["axes"]["descriptor_gradient"]["evidence"]["classification"] == (
        "UNKNOWN"
    )


def test_temporal_axis_reports_distribution_change_without_perception_claim() -> None:
    opening = _frame("opening", 0.0, ("A", 10.0, 1.0), ("B", 0.0, 0.0))
    drydown = _frame("drydown", 3600.0, ("A", 0.0, 0.0), ("B", 10.0, 1.0))

    profile = analyze_construction_complexity(
        opening.state,
        (opening, drydown),
    ).as_dict()
    temporal = profile["axes"]["modeled_temporal_differentiation"]

    assert temporal["status"] == "AVAILABLE"
    assert temporal["metrics"]["transitions"][0]["jensen_shannon_distance"] == (
        pytest.approx(1.0)
    )
    assert temporal["evidence"]["classification"] == "HEURISTIC"
    assert temporal["metrics"]["perceived_transition_authorized"] is False


def test_explicit_standardized_vectors_enable_gradient_and_negative_space_audit() -> None:
    opening = _frame(
        "opening",
        0.0,
        ("A", 10.0, 1.0),
        ("B", 10.0, 2.0),
        ("C", 10.0, 1.0),
    )
    descriptor_evidence = EvidenceDescriptor(
        classification=ScientificClass.EMPIRICALLY_CALIBRATED,
        basis="standardized ratings from one declared panel and concentration",
        sources=("fixture:panel-v1",),
        limitations=("fixture only",),
    )
    inputs = ConstructionComplexityInputs(
        descriptor_vectors={
            "A": {"floral": 0.0, "woody": 0.0},
            "B": {"floral": 1.0, "woody": 0.0},
            "C": {"floral": 2.0, "woody": 0.0},
        },
        descriptor_vector_evidence=descriptor_evidence,
        descriptor_vectors_standardized=True,
        gradient_material_order=("A", "B", "C"),
        negative_space_probes=(
            NegativeSpaceProbe("middle floral band", "floral", 0.9, 1.1),
        ),
    )

    profile = analyze_construction_complexity(
        opening.state,
        (opening,),
        inputs=inputs,
    ).as_dict()
    gradient = profile["axes"]["descriptor_gradient"]
    negative_space = profile["axes"]["negative_space"]

    assert gradient["status"] == "AVAILABLE"
    assert gradient["metrics"]["path_directness"] == pytest.approx(1.0)
    assert gradient["metrics"]["step_distance_cv"] == pytest.approx(0.0)
    assert gradient["metrics"]["functional_groups_used"] is False
    assert negative_space["status"] == "AVAILABLE"
    assert negative_space["metrics"]["probes"][0]["windows"][0][
        "modeled_descriptor_occupancy_share"
    ] == pytest.approx(0.5)
    assert negative_space["metrics"]["implied_odor_authorized"] is False


def test_semantic_partitions_quantify_coexistence_but_not_independence() -> None:
    opening = _frame(
        "opening",
        0.0,
        ("Amber", 100.0, 4.0),
        ("Rose", 25.0, 2.0),
        ("Air", 9.0, 1.0),
    )
    inputs = ConstructionComplexityInputs(
        foreground_materials=("Rose",),
        background_materials=("Amber", "Air"),
        heavy_materials=("Amber",),
    )

    profile = analyze_construction_complexity(
        opening.state,
        (opening,),
        inputs=inputs,
    ).as_dict()

    foreground = profile["axes"]["foreground_background"]
    heavy = profile["axes"]["heavy_note_coexistence"]
    assert foreground["status"] == "AVAILABLE"
    assert foreground["metrics"]["windows"][0]["foreground_share"] == pytest.approx(
        2 / 7
    )
    assert heavy["metrics"]["windows"][0]["heavy_share"] == pytest.approx(4 / 7)
    assert heavy["metrics"]["independent_perception_authorized"] is False


def test_hedonic_axis_fails_closed_without_panel_calibration() -> None:
    opening = _frame("opening", 0.0, ("A", 10.0, 1.0), ("B", 10.0, 1.0))
    inputs = ConstructionComplexityInputs(
        hedonic_values={"A": 0.2, "B": 0.8},
        hedonic_material_order=("A", "B"),
        hedonic_evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis="hand-entered values",
        ),
    )

    axis = analyze_construction_complexity(
        opening.state,
        (opening,),
        inputs=inputs,
    ).as_dict()["axes"]["hedonic_gradient"]

    assert axis["status"] == "UNKNOWN"
    assert axis["metrics"]["mixture_pleasantness_authorized"] is False


def test_workbench_emits_default_construction_profile() -> None:
    payload = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Construction profile smoke",
            ingredients_ul={"Hedione": 1000.0, "Iso E Super": 1000.0},
            dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
            stock_fraction_bases={
                "Hedione": "volume_fraction",
                "Iso E Super": "volume_fraction",
            },
            batch_volume_ml=10.0,
            windows=(("opening", 0.0), ("heart", 1800.0)),
        )
    ).as_dict()

    profile = payload["construction_complexity"]
    assert profile["schema_version"] == "construction_complexity_profile_v1"
    assert profile["axes"]["modeled_headspace_distribution"]["status"] == (
        "AVAILABLE"
    )
    assert profile["axes"]["hedonic_gradient"]["status"] == "UNKNOWN"


def test_active_orchestrator_uses_withheld_noncompensatory_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    prompt_path = (
        root
        / "prompts"
        / "DeepSeek_V4_Flash_0731_Perfume_Orchestrator_Master_Prompt.md"
    )
    governing_path = root / "docs" / "master_prompt_governing.md"
    opencode = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
    prompt = prompt_path.read_text(encoding="utf-8")
    governing = governing_path.read_text(encoding="utf-8")

    assert opencode["default_agent"] == "perfume-orchestrator"
    assert opencode["agent"]["perfume-orchestrator"]["prompt"] == (
        "{file:./prompts/DeepSeek_V4_Flash_0731_Perfume_Orchestrator_Master_Prompt.md}"
    )
    for active_contract in (prompt, governing):
        assert "complexity_authority=WITHHELD" in active_contract
        assert "No universal material-count minimum" in active_contract
        assert "No aggregate complexity or quality score" in active_contract

    retired_authority_statements = (
        "Accord at least 50 after pruning.",
        "Perfume at least 65 after pruning.",
        "Collision similarity must remain below 0.76.",
        "`92 / 100`",
        "FULL COMPLEX PERFUME: Minimum 65 distinct odor materials.",
        "COMPLEX STANDALONE ACCORD: Minimum 50 distinct odor materials.",
    )
    for retired in retired_authority_statements:
        assert retired not in prompt
        assert retired not in governing
