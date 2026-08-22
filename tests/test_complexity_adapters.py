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
