import json

from scripts.b8_backfill_dashboard import (
    build_workspace_backfill_projection,
    main,
)


def _write_inventory(path):
    path.write_text(
        "\n".join(
            (
                "--- Aromachemicals ---",
                "- Iso-E-Super",
                "- Iso-E-Super (50% in DPG)",
                "- Missing Material",
                "- Gone Material [OUT OF STOCK]",
                "--- Solvents / Carriers ---",
                "- DPG",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _write_scientific_inventory(path):
    payload = {
        "schema_version": "scientific-truth-inventory-v1",
        "summary": {
            "material_count": 3,
            "material_property_observation_count": 5,
        },
        "material_property_observations": [
            {
                "subject_id": "Iso E Super",
                "property_type": "density",
                "current_value": 0.96,
                "evidence_class": "HEURISTIC",
                "authority_label": "UNATTRIBUTED_LEGACY",
                "review_state": "LEGACY_UNREVIEWED",
                "conflict_set": None,
                "affects_blocking_gate": True,
                "claim_impacts": ["property_value"],
                "content_sha256": "a" * 64,
            },
            {
                "subject_id": "Iso E Super",
                "property_type": "vapor_pressure",
                "current_value": None,
                "evidence_class": "UNKNOWN",
                "authority_label": "UNKNOWN",
                "review_state": "LEGACY_UNREVIEWED",
                "conflict_set": None,
                "affects_blocking_gate": True,
                "claim_impacts": ["property_value"],
                "content_sha256": "b" * 64,
            },
            {
                "subject_id": "Gone Material",
                "property_type": "density",
                "current_value": 1.02,
                "evidence_class": "SUPPLIER_PROVIDED",
                "authority_label": "UNATTRIBUTED_LEGACY",
                "review_state": "LEGACY_UNREVIEWED",
                "conflict_set": None,
                "affects_blocking_gate": False,
                "claim_impacts": ["property_value"],
                "content_sha256": "c" * 64,
            },
            {
                "subject_id": "iso e super",
                "property_type": "boiling_point",
                "current_value": None,
                "evidence_class": "UNKNOWN",
                "authority_label": "UNKNOWN",
                "review_state": "LEGACY_UNREVIEWED",
                "conflict_set": None,
                "affects_blocking_gate": False,
                "claim_impacts": ["property_value"],
                "content_sha256": "e" * 64,
            },
            {
                "subject_id": "Not In Inventory",
                "property_type": "density",
                "current_value": 0.88,
                "evidence_class": "MEASURED",
                "authority_label": "MEASURED",
                "review_state": "REVIEWED",
                "conflict_set": None,
                "affects_blocking_gate": False,
                "claim_impacts": ["property_value"],
                "content_sha256": "d" * 64,
            },
        ],
    }
    path.write_text(
        json.dumps(payload, sort_keys=True),
        encoding="utf-8",
    )


def test_b8_projection_is_alias_aware_fail_closed_and_stratified(tmp_path):
    inventory_path = tmp_path / "inventory.txt"
    scientific_path = tmp_path / "scientific.json"
    _write_inventory(inventory_path)
    _write_scientific_inventory(scientific_path)

    projection = build_workspace_backfill_projection(
        inventory_path=inventory_path,
        scientific_inventory_path=scientific_path,
    )

    counts = projection["inventory_counts"]
    assert counts["raw_entries"] == 5
    assert counts["unique_normalized"] == 4
    assert counts["unique_fragrance"] == 3
    assert counts["duplicate_canonical_entries"] == 1
    assert counts["owned_unique_fragrance"] == 2
    assert counts["unavailable_unique_fragrance"] == 1
    assert counts["matched_owned_materials"] == 1
    assert counts["unmatched_owned_materials"] == 1
    assert counts["matched_unavailable_materials"] == 1
    assert projection["unmatched_owned_materials"] == ["Missing Material"]
    assert projection["matched_owned_materials"][0][
        "scientific_subject_id"
    ] == "Iso E Super"

    property_rows = {
        row["property_type"]: row for row in projection["property_gaps"]
    }
    assert property_rows["density"]["requirements_total"] == 1
    assert property_rows["density"]["weak_count"] == 1
    assert property_rows["vapor_pressure"]["missing_count"] == 1
    assert projection["legacy_promotion_count"] == 0

    dashboard = projection["dashboard_cells"]
    assert {cell["dimension"] for cell in dashboard} == {
        "EVIDENCE_CLASS",
        "PROPERTY",
        "CURRENT_INVENTORY",
        "ACTIVE_FORMULA",
        "CHEMICAL_FAMILY",
        "REGULATORY_IMPACT",
        "MODEL_SENSITIVITY",
    }
    assert all(
        cell["requirements_total"]
        == cell["accepted_exact_count"]
        + cell["accepted_scoped_count"]
        + cell["weak_count"]
        + cell["conflicted_count"]
        + cell["unknown_count"]
        + cell["missing_count"]
        + cell["not_applicable_count"]
        for cell in dashboard
    )
    assert {
        cell["dimension_key"]
        for cell in dashboard
        if cell["dimension"] == "CURRENT_INVENTORY"
    } == {"OWNED_MATCHED", "OWNED_UNMATCHED", "UNAVAILABLE"}
    assert {
        cell["dimension_key"]
        for cell in dashboard
        if cell["dimension"]
        in {"ACTIVE_FORMULA", "CHEMICAL_FAMILY", "MODEL_SENSITIVITY"}
    } == {"UNKNOWN"}
    serialized = json.dumps(projection, sort_keys=True).casefold()
    assert "coverage_score" not in serialized
    assert "confidence_percent" not in serialized


def test_b8_projection_and_cli_bytes_are_deterministic(tmp_path):
    inventory_path = tmp_path / "inventory.txt"
    scientific_path = tmp_path / "scientific.json"
    first_output = tmp_path / "first.json"
    second_output = tmp_path / "second.json"
    _write_inventory(inventory_path)
    _write_scientific_inventory(scientific_path)

    first = build_workspace_backfill_projection(
        inventory_path=inventory_path,
        scientific_inventory_path=scientific_path,
    )
    second = build_workspace_backfill_projection(
        inventory_path=inventory_path,
        scientific_inventory_path=scientific_path,
    )
    assert first == second

    assert (
        main(
            [
                "--inventory",
                str(inventory_path),
                "--scientific-inventory",
                str(scientific_path),
                "--output",
                str(first_output),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "--inventory",
                str(inventory_path),
                "--scientific-inventory",
                str(scientific_path),
                "--output",
                str(second_output),
            ]
        )
        == 0
    )
    assert first_output.read_bytes() == second_output.read_bytes()
    assert json.loads(first_output.read_text(encoding="utf-8")) == first
