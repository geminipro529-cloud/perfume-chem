from __future__ import annotations

import math
import random
from pathlib import Path

import pytest

from engine.name_utils import normalize_name
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    ReleaseGateConfig,
    _gate_guerlain_rose_jasmine_balance,
    _gate_oriental_skeleton,
)
from engine.pipeline.preflight import (
    _natural_composite_coverage_check,
    resolve_inventory_stock_contract,
)
from engine.reference_contracts import (
    PRADA_LHOMME_OFFICIAL_NOTES_V1,
    evaluate_reference_contract,
)
from engine.science_audit import build_inventory_oav_coverage_audit
from scripts.format_pipeline_analysis import (
    build_authority_dimensions,
    build_oav_headspace_table,
    build_subthreshold,
)
from scripts.formula_release_gate import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
PRADA_CASES = (
    (
        ROOT / "formulas" / "Prada_LHomme_Architecture_Control_30mL_EdT.md",
        {
            ("Aldehyde C11", "inventory_stock_metadata_incomplete"),
            ("Ambrofix", "inventory_gap"),
            ("Bourgeonal", "stock_fraction_mismatch"),
            ("Neroli EO", "stock_carrier_mismatch"),
        },
    ),
    (
        ROOT / "formulas" / "Prada_LHomme_Luxury_Orris_30mL_EdT.md",
        {
            ("Aldehyde C11", "inventory_stock_metadata_incomplete"),
            ("Alpha Irone", "inventory_gap"),
            ("Ambrofix", "inventory_gap"),
            ("Neroli EO", "stock_carrier_mismatch"),
            ("Orris Liquid", "stock_fraction_mismatch"),
            ("Bourgeonal", "stock_fraction_mismatch"),
        },
    ),
)
PRADA_FILES = tuple(path for path, _expected_issues in PRADA_CASES)


def _formula(path: Path) -> dict:
    return parse_formula_markdown(path)[0]


def _state(formula: dict):
    return build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        stock_specs=formula.get("stock_specs"),
    )


@pytest.mark.parametrize(
    ("path", "expected_stock_issues"),
    PRADA_CASES,
    ids=lambda case: case.stem if isinstance(case, Path) else None,
)
def test_prada_controls_preserve_architecture_but_fail_closed_on_current_stock(
    path: Path,
    expected_stock_issues: set[tuple[str, str]],
) -> None:
    formula = _formula(path)
    state = _state(formula)
    stock_contract = resolve_inventory_stock_contract(formula)

    assert sum(formula["ingredients_ul"].values()) == pytest.approx(5000.0)
    assert stock_contract.status == "FAIL"
    assert {
        (str(issue["material"]), str(issue["reason"]))
        for issue in stock_contract.data["issues"]
    } == expected_stock_issues
    assert _natural_composite_coverage_check(state).status == "PASS"
    assert evaluate_reference_contract(formula, state)["status"] == "PASS"
    assert all(material.oav is not None for material in state.materials)


@pytest.mark.parametrize(
    "group",
    PRADA_LHOMME_OFFICIAL_NOTES_V1.marker_groups,
    ids=lambda group: group.name,
)
def test_prada_contract_fails_when_any_official_anchor_group_is_deleted(group) -> None:
    formula = _formula(PRADA_FILES[0])
    kept = {
        name: amount
        for name, amount in formula["ingredients_ul"].items()
        if not any(
            alternative in normalize_name(name)
            for alternative in group.alternatives
        )
    }
    dilutions = {name: formula["dilutions"][name] for name in kept}
    stock_specs = {
        name: formula["stock_specs"][name]
        for name in kept
        if name in formula.get("stock_specs", {})
    }

    result = evaluate_reference_contract(
        formula,
        build_formula_state(kept, dilutions, stock_specs=stock_specs),
    )

    assert len(kept) < len(formula["ingredients_ul"])
    assert result["status"] == "FAIL"
    assert group.name in result["detail"]


def test_luxury_orris_variant_substitutes_inside_the_iris_module() -> None:
    control = _formula(PRADA_FILES[0])["ingredients_ul"]
    luxury = _formula(PRADA_FILES[1])["ingredients_ul"]
    synthetic_iris = {
        "Alpha Isomethyl Ionone (Methyl Ionone Pure)",
        "Alpha Ionone",
        "Beta Ionone",
        "Dihydro Beta Ionone",
        "Orivone",
    }

    control_synthetic = sum(control.get(name, 0.0) for name in synthetic_iris)
    luxury_synthetic = sum(luxury.get(name, 0.0) for name in synthetic_iris)

    assert sum(control.values()) == pytest.approx(sum(luxury.values()))
    assert luxury_synthetic < control_synthetic * 0.60
    assert luxury["Orris Liquid"] == pytest.approx(600.0)
    assert luxury["Alpha Irone"] == pytest.approx(250.0)
    assert "Orris Liquid" not in control
    assert "Alpha Irone" not in control


def test_headspace_is_scale_order_and_matrix_consistent() -> None:
    formula = {
        "Red Mandarin EO": 40.0,
        "Hedione": 200.0,
        "Iso E Super": 300.0,
    }
    dilutions = {name: 1.0 for name in formula}
    base = build_formula_state(formula, dilutions)
    reordered = build_formula_state(dict(reversed(tuple(formula.items()))), dilutions)
    scaled = build_formula_state(
        {name: amount * 7.0 for name, amount in formula.items()},
        dilutions,
    )
    finished = build_formula_state(
        formula,
        dilutions,
        matrix_moles={"ethanol": 0.4, "water": 0.05},
        matrix_mass_g=20.0,
        matrix_source="declared_test_matrix",
    )

    assert reordered is base  # canonical input freezing reaches the exact cache
    for original, multiplied, diluted in zip(
        base.materials,
        scaled.materials,
        finished.materials,
        strict=True,
    ):
        assert multiplied.name == original.name
        assert multiplied.vapor_ppm == pytest.approx(original.vapor_ppm)
        assert multiplied.oav == pytest.approx(original.oav)
        assert diluted.oav is not None
        assert original.oav is not None
        assert diluted.oav < original.oav


def test_randomized_formula_states_preserve_physical_invariants() -> None:
    rng = random.Random(20260719)
    material_pool = (
        "Hedione",
        "Iso E Super",
        "Linalool",
        "Linalyl Acetate",
        "Beta Ionone",
        "Ethylene Brassylate",
        "Red Mandarin EO",
        "Clary Sage EO",
        "Eucalyptus Essential Oil",
    )

    for _case in range(12):
        chosen = rng.sample(material_pool, rng.randint(3, 7))
        formula = {name: rng.uniform(0.1, 900.0) for name in chosen}
        state = build_formula_state(formula)

        assert sum(material.mole_fraction for material in state.materials) == pytest.approx(
            1.0
        )
        assert state.total_vapor_ppm > 0.0
        for material in state.materials:
            assert material.raw_ul > 0.0
            assert material.active_ul > 0.0
            assert material.vapor_ppm >= 0.0
            assert material.oav is not None
            assert material.oav >= 0.0
            assert math.isfinite(material.oav)


def test_unresolved_natural_matrix_is_explicit_and_opaque_blends_are_separate() -> None:
    audit = build_inventory_oav_coverage_audit()

    assert set(audit["categories"]["naturals_missing_composite_evidence"]) == {
        "Anise EO",
        "Basil EO",
        "Cabreuva EO",
        "Cade Oil Rectified",
        "Caraway Seed Oil",
        "Champaca Flower EO",
        "Cypress EO",
        "Elemi EO",
        "Grapefruit FCF oil Sicilian",
        "Hay Absolute",
        "Helichrysum EO",
        "Himalayan Cedarwood EO",
        "Magnolia EO",
        "Myrrh EO",
        "Nutmeg EO",
        "Opoponax Resinoid",
        "Peppermint EO",
        "Peppermint Essential Oil",
        "Peru Balsam Resinoid",
        "Pine EO",
        "Pink Pepper EO",
        "Sandalwood EO",
        "Spike Lavender EO",
        "Tagetes EO",
    }
    assert set(
        audit["categories"]["opaque_preblends_without_disclosed_composition"]
    ) == {
        "Leather FO",
        "Lilyreal ND",
        "Sandalwood Base 3X",
        "Tuberlia Base",
    }
    assert audit["status"] == "FAIL_CLOSED_GAPS"
    assert audit["release_authority"] is False


def test_material_state_preserves_profile_role_and_texture_for_reporting() -> None:
    material = build_formula_state({"Hedione": 100.0}).materials[0]
    row = material.as_dict()

    assert material.role
    assert row["role"] == material.role
    assert row["texture"] == material.texture
    assert row["role"] != row["profile_name"]


def test_required_headspace_table_has_exact_physics_columns() -> None:
    material = build_formula_state({"Hedione": 100.0}).materials[0].as_dict()
    table = build_oav_headspace_table([material])

    assert table[2] == (
        "| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | "
        "Vapor ppm | ODT ppm | OAV | Note |"
    )
    assert "| Role |" not in table[2]
    assert "| Percept |" not in table[2]


def test_subthreshold_flags_follow_function_not_profile_alias() -> None:
    common = {
        "oav": 0.5,
        "vp_pure_pa": 0.01,
        "active_ul": 25.0,
        "family": "musk",
        "profile_name": "Alias Must Not Be Role",
    }
    lines = build_subthreshold(
        [
            {
                **common,
                "name": "Projection Musk",
                "role": "modifier",
                "texture": "diffusion",
            },
            {
                **common,
                "name": "Structural Musk",
                "role": "fixative",
                "texture": "",
            },
        ]
    )
    rendered = "\n".join(lines)

    assert "Projection Musk" in rendered
    assert "FUNCTIONAL_UNDERPERFORMANCE" in rendered
    assert "Structural Musk" in rendered
    assert "STRUCTURAL_OR_FIXATIVE" in rendered
    assert "Alias Must Not Be Role" not in rendered


def test_authority_dimensions_never_imply_sensory_similarity() -> None:
    formula = {
        "gates": [
            {
                "gate": "inventory_stock_contract",
                "status": "PASS",
                "detail": "Live stock resolved.",
            },
            {
                "gate": "reference_claim_contract",
                "status": "PASS",
                "detail": "Architecture only.",
                "data": {"scope": "architecture"},
            },
        ],
        "formula_state": {
            "headspace_basis": "MODELED_FINISHED_PRODUCT_MATRIX_PROXY",
            "quantitative_authority": {
                "active_concentrate_ppm_w_w": "UNAVAILABLE",
                "headspace_oav": "MODELED_FINISHED_PRODUCT_MATRIX_PROXY",
                "headspace_model_class": "HEURISTIC_NOT_MEASURED",
            },
        },
        "confidence": {"combined_confidence": 0.0},
    }
    rendered = "\n".join(build_authority_dimensions(formula))

    assert "NOT_AUTHORIZED_NOT_MEASURED" in rendered
    assert "PASS (architecture)" in rendered
    assert "UNAVAILABLE" in rendered
    assert "0.0/100" in rendered


@pytest.mark.parametrize("path", PRADA_FILES, ids=lambda path: path.stem)
def test_prada_controls_skip_unrelated_floral_and_oriental_skeletons(
    path: Path,
) -> None:
    state = _state(_formula(path))
    config = ReleaseGateConfig(
        family_archetype="iris_amber_woody.prada_lhomme_reference"
    )

    assert _gate_guerlain_rose_jasmine_balance(state, config).detail == "not applicable"
    assert _gate_oriental_skeleton(state, config).detail == "not applicable"


def test_family_specific_skeletons_still_execute_for_matching_concepts() -> None:
    floral = build_formula_state({"Geraniol": 1000.0, "Hedione": 1000.0})
    oriental = build_formula_state({"Hedione": 1000.0})

    floral_result = _gate_guerlain_rose_jasmine_balance(
        floral,
        ReleaseGateConfig(family_archetype="floral_classical.test"),
    )
    oriental_result = _gate_oriental_skeleton(
        oriental,
        ReleaseGateConfig(family_archetype="oriental_classical.test"),
    )

    assert floral_result.detail != "not applicable"
    assert oriental_result.detail != "not applicable"
    assert "Oriental skeleton missing" in oriental_result.detail
