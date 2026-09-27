"""Performance caches must remain local, source-bound, and scientifically inert."""

from __future__ import annotations

from pathlib import Path

from engine import inventory_parser
from engine.knowledge import literature_rules
from engine.pipeline import natural_absolute_decomposition as natural_profiles
from engine.pipeline import preflight
from engine.thermo.activity import gamma, mixture_hsp


def test_inventory_materialization_cache_invalidates_on_source_bytes(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "inventory-snapshot.json"
    snapshot.write_bytes(inventory_parser.CURRENT_INVENTORY_SNAPSHOT_PATH.read_bytes())

    first = inventory_parser.materialize_current_inventory(
        snapshot,
        require_pinned_snapshot=False,
        apply_user_overlay=False,
    )
    repeated = inventory_parser.materialize_current_inventory(
        snapshot,
        require_pinned_snapshot=False,
        apply_user_overlay=False,
    )
    assert repeated is first

    snapshot.write_bytes(snapshot.read_bytes() + b"\n")
    changed = inventory_parser.materialize_current_inventory(
        snapshot,
        require_pinned_snapshot=False,
        apply_user_overlay=False,
    )
    assert changed is not first
    assert changed.snapshot_sha256 != first.snapshot_sha256


def test_catalogue_cache_is_reused_only_for_same_source_fingerprint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    rule_file = tmp_path / "rules.json"
    rule_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(
        literature_rules,
        "STRUCTURED_RULE_FILES",
        {"test_rules": rule_file},
    )
    calls: list[int] = []
    sentinel_values = [object(), object()]

    def fake_builder(*, formula_material_names=None):
        assert formula_material_names is None
        calls.append(1)
        return sentinel_values[len(calls) - 1]

    monkeypatch.setattr(
        literature_rules,
        "_build_knowledge_rule_quality_contract_uncached",
        fake_builder,
    )
    literature_rules._cached_catalogue_rule_quality_contract.cache_clear()

    first = literature_rules.build_knowledge_rule_quality_contract()
    repeated = literature_rules.build_knowledge_rule_quality_contract()
    assert repeated is first
    assert len(calls) == 1

    rule_file.write_text("[]\n", encoding="utf-8")
    changed = literature_rules.build_knowledge_rule_quality_contract()
    assert changed is sentinel_values[1]
    assert len(calls) == 2


def test_schema_cache_is_reused_only_for_same_source_fingerprint(
    monkeypatch,
    tmp_path: Path,
) -> None:
    for name in (
        "material_properties.json",
        "pairing_rules.json",
        "synergy_matrix.json",
        "theory_rules.json",
    ):
        (tmp_path / name).write_text("[]", encoding="utf-8")

    calls: list[int] = []

    class FakeReport:
        def summary(self):
            return {"errors": 0, "warnings": 0, "info": 0, "stats": {}}

    class FakeValidator:
        def validate_all(self):
            calls.append(1)
            return FakeReport()

    monkeypatch.setattr(preflight, "KG_DIR", tmp_path)
    monkeypatch.setattr(preflight, "SchemaValidator", FakeValidator)
    preflight._cached_schema_summary.cache_clear()

    assert preflight._schema_check().status == "PASS"
    assert preflight._schema_check().status == "PASS"
    assert len(calls) == 1

    (tmp_path / "theory_rules.json").write_text("[]\n", encoding="utf-8")
    assert preflight._schema_check().status == "PASS"
    assert len(calls) == 2


def test_natural_profile_resolution_cache_changes_no_resolution_semantics() -> None:
    natural_profiles._resolve_profile_key.cache_clear()
    first = natural_profiles._resolve_profile_key("Lavender EO Bontoux")
    second = natural_profiles._resolve_profile_key("Lavender EO Bontoux")
    assert second == first
    info = natural_profiles._resolve_profile_key.cache_info()
    assert info.misses == 1
    assert info.hits == 1


def test_precomputed_mixture_hsp_preserves_gamma_exactly() -> None:
    composition = {
        "Ethanol": 0.85,
        "Water": 0.10,
        "Limonene": 0.05,
        "Zero dose": 0.0,
    }
    hsp_table = {"Limonene": (16.5, 1.1, 4.2)}
    precomputed = mixture_hsp(composition, hsp_table=hsp_table)

    assert precomputed is not None
    assert gamma(
        "Limonene",
        composition,
        hsp_table=hsp_table,
        mixture_hsp_override=precomputed,
    ) == gamma("Limonene", composition, hsp_table=hsp_table)


def test_empty_mixture_hsp_preserves_ideal_fallback() -> None:
    composition = {"Limonene": 0.0}
    assert mixture_hsp(composition) is None
    assert gamma("Limonene", composition) == 1.0


def test_temperature_adjusted_natural_rows_reuse_only_identical_profile_bytes() -> None:
    natural_profiles._temperature_adjusted_constituent_rows.cache_clear()
    first_profile = (("marker", 1.0, 100.0, 1.0, 1000.0, 1.0),)
    changed_profile = (("marker", 1.0, 100.0, 2.0, 1000.0, 1.0),)

    first = natural_profiles._temperature_adjusted_constituent_rows(
        first_profile,
        305.15,
        0.6,
        None,
    )
    repeated = natural_profiles._temperature_adjusted_constituent_rows(
        first_profile,
        305.15,
        0.6,
        None,
    )
    changed = natural_profiles._temperature_adjusted_constituent_rows(
        changed_profile,
        305.15,
        0.6,
        None,
    )

    assert repeated is first
    assert changed is not first
    assert changed[0][0][3] != first[0][0][3]
