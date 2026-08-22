from __future__ import annotations

import json

import pytest

from engine.perception.complexity_adapters import (
    adapt_admission_lifecycle,
    adapt_construction_profile,
    adapt_expansion_frontier,
    adapt_experimental_design,
    adapt_musk_design,
    adapt_temporal_sensory,
)
from tests.complexity_benchmark_fixtures import (
    admission_payload,
    causal_payload,
    expansion_payload,
    musk_payload,
    within_sniff_payload,
)


def test_construction_adapter_calls_native_multi_axis_profile() -> None:
    result = adapt_construction_profile(
        {
            "materials": [{"name": "A", "oav": 10.0, "intensity": 2.0}],
            "frames": [
                {
                    "label": "opening",
                    "t_seconds": 0.0,
                    "materials": [
                        {"name": "A", "oav": 10.0, "intensity": 2.0}
                    ],
                }
            ],
            "inputs": {"foreground_materials": ["A"]},
        }
    )
    assert result["schema_version"] == "construction_complexity_profile_v1"
    assert len(result["result_sha256"]) == 64
    assert "overall_score" not in json.dumps(result)


def test_expansion_adapter_preserves_no_formula_authority() -> None:
    result = adapt_expansion_frontier(expansion_payload())
    assert result["registry_audit"]["state"] == "PASS"
    assert result["registry_audit"]["formula_authority"] is False


def test_musk_adapter_preserves_sparse_selection_and_exception_holds() -> None:
    sparse = adapt_musk_design(musk_payload())
    assert sparse["architecture_mode"] == "SPARSE"
    assert [item["material"] for item in sparse["selected"]] == ["Zenolide"]
    blocked = adapt_musk_design(
        musk_payload(
            material="Tonalide",
            exception_call=None,
            inventory_state="DEPLETED",
        )
    )
    assert blocked["state"] == "HOLD"
    assert "MUSK_EXCEPTION_REQUIRED" in blocked["issue_codes"]


def test_sealed_adapter_exposes_target_build_and_gap_discriminators() -> None:
    result = adapt_admission_lifecycle(admission_payload())

    discriminators = result["response_discriminators"]
    assert discriminators["target_build_separation"] == {
        "target_ideal_inventory_independent": True,
        "current_build_requires_case_bound_stock_evidence": True,
        "identical_target_and_build_material_lists_forbidden": True,
        "when_stock_evidence_is_absent": (
            "use an empty current_inventory_build.materials list"
        ),
    }
    assert discriminators["missing_chemical_impact"] == {
        "module_inventory_authority": False,
        "default_gap_class": "EVIDENCE_GAP_NOT_INVENTORY_GAP",
        "inventory_gap_requires_case_bound_evidence": True,
        "controlled_comparison_required": True,
    }


def test_musk_adapter_projects_complete_exception_call_as_material_keyed_object() -> None:
    exception = {
        "material": "Macrolide",
        "target_tonal_role": "barely-there disappearing residue",
        "why_alternatives_fail": "alternatives leave a more projected clean trail",
        "loss_if_omitted": "the warmth-to-skin transition becomes abrupt",
        "failure_mode": "overdose creates anonymous soft blur",
        "omission_control": "carrier-matched omission",
        "alternative_control": "matched strongest clean macrocyclic alternative",
    }

    result = adapt_musk_design(
        musk_payload(
            material="Macrolide",
            exception_call=exception,
            inventory_state="DEPLETED",
        )
    )

    projection = result["formula_projection"]
    assert projection["target_ideal_materials"] == ["Macrolide"]
    assert projection["current_inventory_build_materials"] == []
    assert projection["current_inventory_build_state"] == (
        "HOLD_PROCUREMENT_REQUIRED"
    )
    assert projection["target_ideal_exception_calls"] == {
        "Macrolide": {
            key: value for key, value in exception.items() if key != "material"
        }
    }
    assert projection["current_inventory_build_exception_calls"] == {}


@pytest.mark.parametrize(
    ("adapter", "payload"),
    [
        (adapt_experimental_design, causal_payload()),
        (adapt_admission_lifecycle, admission_payload()),
        (adapt_temporal_sensory, within_sniff_payload()),
    ],
)
def test_guardrail_adapters_emit_no_execution_or_release_authority(
    adapter, payload
) -> None:
    result = adapter(payload)
    encoded = json.dumps(result, sort_keys=True)
    assert '"physical_execution_authorized": true' not in encoded
    assert '"sensory_authority": true' not in encoded
    assert '"release_authority": true' not in encoded


def test_adapters_reject_unknown_keys_and_operations() -> None:
    with pytest.raises(ValueError, match="unknown keys"):
        adapt_musk_design({**musk_payload(), "dose": "forbidden"})
    with pytest.raises(ValueError, match="unsupported operation"):
        adapt_experimental_design({"operation": "invent_claims"})
