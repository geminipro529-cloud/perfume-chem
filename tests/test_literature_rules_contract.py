import json
from pathlib import Path

from engine.knowledge.literature_rules import (
    _is_generic_reference,
    build_literature_rule_contract,
)
from engine.material_resolver import resolve_material


def test_literature_rule_contract_exposes_runtime_coverage():
    contract = build_literature_rule_contract().as_dict()
    assert contract["english_sources"] > 0
    assert contract["french_manifest_entries"] > 0
    assert contract["deterministic_rule_entries"] > 0
    assert "structured_rule_files" in contract["details"]
    assert "knowledge_index" in contract["details"]


def test_synergy_matrix_has_no_extracted_table_junk_rows():
    rows = json.loads(
        Path("data/knowledge_graph/synergy_matrix.json").read_text(encoding="utf-8")
    )

    bad = []
    for row in rows:
        material_a = str(row.get("material_a", "")).strip()
        material_b = str(row.get("material_b", "")).strip()
        effect = str(row.get("effect", "")).strip()

        if material_a in {"Goal", "1:4"}:
            bad.append(row)
            continue
        if not effect:
            bad.append(row)
            continue
        if material_b in {"Amplifier", "2-3x sillage"}:
            bad.append(row)

    assert bad == []


def test_grouped_rule_labels_are_treated_as_generic_references():
    assert _is_generic_reference("Musks (Galaxolide, Habanolide)") is True
    assert _is_generic_reference("Florals (Rose, Jasmine)") is True
    assert _is_generic_reference("Marine notes (Calone)") is True
    assert _is_generic_reference("Heavy Musks") is True
    assert _is_generic_reference("Everything — universal enhancer") is True


def test_defensible_rule_aliases_resolve_but_generic_shortcuts_do_not():
    for raw_name in ("Ambrox", "ambrox", "DHM", "DEP"):
        resolved = resolve_material(raw_name)
        assert resolved.is_known is True

    for raw_name in ("patchouli", "olibanum", "pink pepper", "lavender"):
        resolved = resolve_material(raw_name)
        assert resolved.is_known is False
