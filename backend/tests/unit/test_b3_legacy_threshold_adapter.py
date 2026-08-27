from app.adapters.legacy_thresholds import legacy_threshold_inputs


def test_legacy_adapter_emits_air_and_solution_records_without_status_upgrade():
    records = legacy_threshold_inputs(
        odt_data={
            "linalool": {
                "odt_air": 0.51,
                "odt_eth": 0.1,
                "sources": ["legacy source"],
            },
            "unknown material": {"odt_air": 5.0},
        },
        odt_verification={
            "linalool": {
                "vfy": "DERIVED",
                "sources": ["verification source"],
                "note": "estimated from constituents",
            }
        },
        id_prefix="legacy-test",
    )

    assert [(record.material_key, record.medium) for record in records] == [
        ("linalool", "AIR"),
        ("linalool", "ETHANOL_SOLUTION"),
        ("unknown material", "AIR"),
    ]
    assert [record.verification_status for record in records] == [
        "DERIVED",
        "DERIVED",
        "UNKNOWN",
    ]
    assert all(record.authority_state == "LEGACY_CONTEXT_INCOMPLETE" for record in records)


def test_legacy_adapter_preserves_low_authority_tokens_verbatim():
    records = legacy_threshold_inputs(
        odt_data={
            "a": {"odt_air": 1.0},
            "b": {"odt_air": 2.0},
            "c": {"odt_air": 3.0},
        },
        odt_verification={
            "a": {"vfy": "UNVERIFIED"},
            "b": {"vfy": "HEURISTIC"},
            "c": {"vfy": "UNKNOWN"},
        },
        id_prefix="legacy-status",
    )

    assert [record.verification_status for record in records] == [
        "UNVERIFIED",
        "HEURISTIC",
        "UNKNOWN",
    ]
