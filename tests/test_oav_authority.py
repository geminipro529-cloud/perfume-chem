import json
import re
from collections import Counter
from pathlib import Path

from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.formula_state import build_formula_state


def _request(ingredients, **overrides):
    payload = dict(
        formula_name="Authority Test Formula",
        ingredients_ul=ingredients,
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    payload.update(overrides)
    return OAVAuthorityRequest(**payload)


def test_oav_authority_contract_shape_and_material_rows():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 1200.0,
                "Lavender EO": 700.0,
                "Linalyl Acetate": 600.0,
                "Hedione": 900.0,
                "Coumarin": 300.0,
                "Evernyl": 20.0,
                "Iso E Super": 1500.0,
                "Vetiver EO": 300.0,
                "Habanolide": 480.0,
            },
            family_archetype="aromatic_fougere",
        )
    )

    payload = result.as_dict()

    assert set(payload) == {
        "request_summary",
        "current_batch_assumptions",
        "material_oav_table",
        "family_envelope_table",
        "dominant_oav_leaders_by_window",
        "oav_intelligence",
        "authority_verdict_summary",
        "downstream_integration",
    }
    assert payload["request_summary"]["formula_name"] == "Authority Test Formula"
    assert payload["current_batch_assumptions"]["backend"] == "engine.pipeline.formula_state + engine.pipeline.simulator"
    assert payload["material_oav_table"]
    assert payload["material_oav_table"][0]["oav"] >= payload["material_oav_table"][-1]["oav"]
    assert payload["oav_intelligence"]["intelligence_status"] in {"PASS", "WARN", "FAIL"}
    assert {
        "name",
        "canonical_name",
        "family",
        "note",
        "raw_ul",
        "dilution",
        "active_ul",
        "vapor_ppm",
        "odt_air_ppm",
        "odt_source",
        "oav",
        "intensity",
    } <= set(payload["material_oav_table"][0])
    assert result.primary_status in {"PASS", "WARN", "FAIL"}


def test_oav_authority_family_envelopes_and_time_windows():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 2500.0,
                "Iso E Super": 2500.0,
                "Habanolide": 1000.0,
            }
        )
    )

    labels = [window.label for window in result.time_windows]
    assert labels == ["opening", "top", "heart", "late_heart", "drydown"]
    assert all(window.family_envelope for window in result.time_windows)
    assert all(isinstance(window.dominant_oav, list) for window in result.time_windows)
    assert result.top_family_drift >= 0.0
    # Beragamot ODT corrected from 15 -> 6 ppb (verified against 3+ sources 2026-05-19).
    # Bergamot now dominates all time windows so leaders do not change.
    assert result.dominant_leaders_changed is False


def test_oav_authority_missing_odt_blocks():
    result = analyze_oav_authority(
        _request(
            {
                "Mystery Molecule": 3000.0,
                "Hedione": 1500.0,
                "Iso E Super": 1500.0,
            }
        )
    )

    assert result.primary_status == "FAIL"
    assert "Mystery Molecule" in result.missing_odt_materials
    assert result.odt_coverage["status"] == "FAIL"
    assert result.blocking_reasons


def test_oav_authority_low_legibility_blocks():
    result = analyze_oav_authority(
        _request(
            {
                "Vanillin": 3000.0,
                "Coumarin": 2000.0,
                "Benzyl Salicylate": 1000.0,
            }
        )
    )

    assert result.primary_status == "FAIL"
    assert result.oav_legibility["status"] == "PASS"
    assert result.downstream_integration["perceptible_material_count"] == 3
    assert result.intelligence_blocking_reasons


def test_oav_authority_high_subliminal_mass_warns():
    result = analyze_oav_authority(
        _request(
            {
                "Hedione": 1000.0,
                "Iso E Super": 1000.0,
                "Linalyl Acetate": 1000.0,
                "Benzyl Benzoate": 2500.0,
                "Dipropylene Glycol": 500.0,
            }
        )
    )

    assert result.primary_status == "WARN"
    assert result.oav_legibility["status"] == "WARN"
    assert result.subliminal_mass_ratio > 0.45
    assert result.warning_reasons


def test_oav_authority_scaling_blocker_is_reflected():
    result = analyze_oav_authority(
        _request(
            {
                "Hedione": 5999.0,
                "Geosmin": 1.0,
            },
            batch_scaling_targets_ml=(15.0,),
        )
    )

    assert result.primary_status == "FAIL"
    assert result.scaling_risk["status"] == "FAIL"
    assert result.scaling_risk["data"]["findings"]


def test_oav_authority_json_serialization_is_deterministic():
    result = analyze_oav_authority(
        _request(
            {
                "Bergamot FCF": 1200.0,
                "Lavender EO": 700.0,
                "Linalyl Acetate": 600.0,
                "Hedione": 900.0,
                "Coumarin": 300.0,
                "Evernyl": 20.0,
                "Iso E Super": 1500.0,
                "Vetiver EO": 300.0,
                "Habanolide": 480.0,
            }
        )
    )

    first = json.dumps(result.as_dict(), sort_keys=True)
    second = json.dumps(result.as_dict(), sort_keys=True)

    assert first == second


def test_odt_source_sections_have_no_duplicate_textual_keys():
    text = Path("engine/odor_thresholds.py").read_text(encoding="utf-8")
    odt_data_start = text.index("ODT_DATA: dict[str, dict] = ")
    odt_verification_start = text.index("ODT_VERIFICATION: dict[str, dict] = ")

    def extract_dict_literal(source: str, assignment_start: int) -> str:
        brace_start = source.index("{", assignment_start)
        depth = 0
        for idx in range(brace_start, len(source)):
            char = source[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return source[brace_start : idx + 1]
        raise AssertionError("Unclosed dict literal in odor_thresholds.py")

    odt_data_block = extract_dict_literal(text, odt_data_start)
    odt_verification_block = extract_dict_literal(text, odt_verification_start)

    def duplicate_keys(block: str) -> dict[str, int]:
        keys = re.findall(r'^\s*"([^"]+)"\s*:\s*\{', block, flags=re.M)
        counts = Counter(keys)
        return {key: count for key, count in counts.items() if count > 1}

    assert duplicate_keys(odt_data_block) == {}
    assert duplicate_keys(odt_verification_block) == {}


def test_uncovered_naturals_and_opaque_preblends_never_use_monomolecular_oav():
    state = build_formula_state(
        {
            "Bergamot FCF oil Sicilian": 100.0,
            "Jasmine FO": 100.0,
            "Lavender EO": 100.0,
        },
        batch_volume_ml=10.0,
    )
    rows = {row.name: row for row in state.materials}

    for name in ("Bergamot FCF oil Sicilian", "Jasmine FO"):
        assert rows[name].oav is None
        assert rows[name].intensity is None
        assert rows[name].sources["oav_model"] == (
            "unknown:composite_decomposition_missing"
        )

    assert rows["Lavender EO"].oav is not None
    assert rows["Lavender EO"].sources["oav_model"] == (
        "literature:natural_composite_gc_o"
    )
