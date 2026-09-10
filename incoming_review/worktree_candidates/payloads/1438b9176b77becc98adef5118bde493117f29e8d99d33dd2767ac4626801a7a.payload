from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.families.registry import evaluate_family_archetype
from engine.odor_thresholds import lookup_odt_entry, lookup_odt_raw_name, odt_collision_names
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.natural_absolute_decomposition import get_composite_metadata
from engine.pipeline.preflight import _dilution_consistency_check
from engine.reference_contracts import evaluate_reference_contract
from scripts.verify_formula_workflow import parse_formula_markdown

ROOT = Path(__file__).resolve().parents[1]
FORMULA_PATH = ROOT / "formulas" / "DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md"
PARENT_PATH = ROOT / "formulas" / "DHI-11_Velours_d_Iris_05443A_30mL_20pct.md"

EXPECTED_INGREDIENTS = {
    "Hedione": 140.0,
    "Iso E Super": 140.0,
    "Benzyl Salicylate": 60.0,
    "Benzyl Benzoate": 40.0,
    "Vetiver EO (India)": 140.0,
    "Cedarwood oil Virginia": 250.0,
    "Cashmeran": 60.0,
    "Sandalore": 60.0,
    "Vetival": 80.0,
    "Ambrettolide": 1600.0,
    "Ethylene Brassylate": 870.0,
    "Romandolide": 210.0,
    "Lavender EO High Altitude": 110.0,
    "Linalyl Acetate": 70.0,
    "Linalool": 20.0,
    "Mimosa Absolute": 80.0,
    "Osmanthus Absolute": 20.0,
    "Alpha Isomethyl Ionone (Methyl Ionone Pure)": 420.0,
    "Alpha Ionone": 180.0,
    "Alpha Irone": 180.0,
    "Dihydro Beta Ionone": 100.0,
    "Irotyl": 80.0,
    "Ultralia": 60.0,
    "Orivone": 20.0,
    "Carrot Seed EO": 10.0,
    "Tonkarome": 310.0,
    "Isobutavan": 140.0,
    "Verdox": 280.0,
    "Benzyl Acetate": 220.0,
    "Ethyl 2-Methylbutyrate": 50.0,
}


@pytest.fixture(scope="module")
def formula():
    parsed = parse_formula_markdown(FORMULA_PATH)
    assert len(parsed) == 1
    return parsed[0]


@pytest.fixture(scope="module")
def formula_state(formula):
    return build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        stock_specs=formula["stock_specs"],
        batch_volume_ml=30.0,
        temperature_K=305.0,
        matrix_moles=formula["matrix_moles"],
        matrix_mass_g=formula["matrix_mass_g"],
        matrix_source=formula["matrix_source"],
    )


def test_formula_is_one_exact_6000_ul_thirty_row_build(formula):
    assert formula["ingredients_ul"] == EXPECTED_INGREDIENTS
    assert sum(formula["ingredients_ul"].values()) == pytest.approx(6000.0)
    assert len(formula["ingredients_ul"]) == 30
    assert all(amount >= 10.0 for amount in formula["ingredients_ul"].values())
    assert formula["family_archetype"] == "iris_coumarin_amber.dhi2011"


def test_dilutions_and_nominal_active_ppm_are_arithmetically_closed(formula):
    expected_dilutions = {name: 1.0 for name in EXPECTED_INGREDIENTS}
    expected_dilutions.update(
        {
            "Ambrettolide": 0.10,
            "Alpha Irone": 0.10,
            "Tonkarome": 0.20,
            "Mimosa Absolute": 0.10,
            "Osmanthus Absolute": 0.10,
            "Ethyl 2-Methylbutyrate": 0.001,
        }
    )
    assert formula["dilutions"] == expected_dilutions
    active_ul = sum(
        amount * expected_dilutions[name]
        for name, amount in formula["ingredients_ul"].items()
    )
    assert active_ul == pytest.approx(4010.05)
    assert active_ul / 6000.0 * 1_000_000.0 == pytest.approx(668341.6666667)


def test_every_formula_row_resolves_to_one_executable_current_stock(formula):
    result = _dilution_consistency_check(formula)
    assert result.status == "PASS"
    assert result.data["issues"] == []
    assert len(result.data["matched_stocks"]) == 30


def test_formula_has_explicit_fruit_talc_depth_warmth_and_three_musk_axes(formula):
    materials = set(formula["ingredients_ul"])
    assert {
        "Ethyl 2-Methylbutyrate",
        "Verdox",
        "Benzyl Acetate",
        "Osmanthus Absolute",
    }.issubset(materials)
    assert {"Benzyl Salicylate", "Mimosa Absolute", "Ethylene Brassylate"}.issubset(materials)
    assert {
        "Dihydro Beta Ionone",
        "Irotyl",
        "Ultralia",
        "Carrot Seed EO",
    }.issubset(materials)
    assert {"Tonkarome", "Isobutavan", "Orivone"}.issubset(materials)
    assert {"Ambrettolide", "Ethylene Brassylate", "Romandolide"}.issubset(materials)
    assert {
        "Orris Liquid",
        "Cocoa Absolute",
        "Damascone Beta",
        "Vanillin",
        "Coumarin",
        "Ambrofix",
        "Musk Ketone",
        "Tonalide",
        "Macrolide",
    }.isdisjoint(materials)


def test_naturals_have_constituent_composite_oav_profiles(formula):
    naturals = {
        "Lavender EO High Altitude",
        "Vetiver EO (India)",
        "Cedarwood oil Virginia",
        "Mimosa Absolute",
        "Osmanthus Absolute",
        "Carrot Seed EO",
    }
    assert naturals.issubset(formula["ingredients_ul"])
    for material in naturals:
        metadata = get_composite_metadata(material)
        assert metadata is not None, material
        assert metadata.characterized_fraction > 0.0
        assert metadata.batch_specific is False


def test_required_recognizers_clear_oav_one_while_support_hypotheses_are_flagged(formula_state):
    rows = {material.name: material for material in formula_state.materials}
    structural_only = {
        "Benzyl Benzoate",
        "Benzyl Salicylate",
        "Carrot Seed EO",
        "Dihydro Beta Ionone",
        "Irotyl",
        "Sandalore",
        "Ultralia",
    }
    required_recognizers = set(EXPECTED_INGREDIENTS).difference(structural_only)
    assert all((rows[name].oav or 0.0) >= 1.0 for name in required_recognizers)
    assert all((rows[name].oav or 0.0) < 1.0 for name in structural_only)
    assert (rows["Ethyl 2-Methylbutyrate"].oav or 0.0) >= 1.0
    assert (rows["Verdox"].oav or 0.0) >= 1.0


def test_each_selected_material_has_unique_odt_and_complete_physics(formula, formula_state):
    for name in formula["ingredients_ul"]:
        assert lookup_odt_raw_name(name) is not None, name
        assert lookup_odt_entry(name) is not None, name
        assert odt_collision_names(name) == (), name
    for material in formula_state.materials:
        assert material.is_known is True, material.name
        assert material.mw_g_mol is not None and material.mw_g_mol > 0, material.name
        assert material.vp_pure_pa is not None and material.vp_pure_pa > 0, material.name
        assert material.odt_air_ppm is not None and material.odt_air_ppm > 0, material.name
        assert material.oav is not None, material.name


def test_target_current_separation_parent_and_authority_ceiling_are_explicit():
    text = FORMULA_PATH.read_text(encoding="utf-8")
    assert "## Target identity and evidence ceiling" in text
    assert "## CURRENT-INVENTORY RAW-VOLUME BUILD — parser-visible formula" in text
    assert "build_default_dhi_2011_deep_plane_program" in text
    assert f"`formulas/{PARENT_PATH.name}`" in text
    assert "**Physical state:** `NOT COMPOUNDED`" in text
    assert "**Sensory / liking / depth / similarity / smoothness / performance / stability:** `NOT TESTED`" in text
    assert "**Safety / IFRA / skin-use / release:** `HOLD`" in text
    assert "**Bench compounding card:** `READY_TO_COMPOUND_BY_RAW_VOLUME`" in text
    assert "PINNED_CURRENT_INVENTORY_AUTHORITY_20260904 + LIVE_INVENTORY_TEXT" in text
    assert "not Dior's formula, a clone claim, or" in text


def test_formula_uses_all_17_baskets_and_descends_inside_each_occupied_basket():
    text = FORMULA_PATH.read_text(encoding="utf-8")
    current = text.split("## CURRENT-INVENTORY RAW-VOLUME BUILD — parser-visible formula", 1)[1].split("**CARRIER / TECHNICAL**", 1)[0]
    headings = re.findall(r"^\*\*BASKET (\d+) —", current, flags=re.MULTILINE)
    assert headings == [str(number) for number in range(1, 18)]
    for basket in range(1, 18):
        start = current.index(f"**BASKET {basket} —")
        if basket < 17:
            end = current.index(f"**BASKET {basket + 1} —", start)
        else:
            end = len(current)
        section = current[start:end]
        values = [
            float(value.replace(",", ""))
            for value in re.findall(
                r"^\|\s*\d+\s*\|[^\n]*?\|\s*([\d,]+(?:\.\d+)?)\s*\|",
                section,
                flags=re.MULTILINE,
            )
        ]
        assert values == sorted(values, reverse=True)


def test_each_parser_visible_formula_row_has_all_eight_cells():
    text = FORMULA_PATH.read_text(encoding="utf-8")
    current = text.split("## CURRENT-INVENTORY RAW-VOLUME BUILD — parser-visible formula", 1)[1].split("**CARRIER / TECHNICAL**", 1)[0]
    dose_rows = re.findall(r"^\|\s*\d+\s*\|.*$", current, flags=re.MULTILINE)
    assert len(dose_rows) == 30
    assert all(len(row.strip().strip("|").split("|")) == 8 for row in dose_rows)


def test_formula_bound_pour_protocol_and_transfer_card_close_exactly():
    text = FORMULA_PATH.read_text(encoding="utf-8")
    rendered = text.split("<!-- FORMULA_MIXING_PROTOCOL_START -->", 1)[1].split("<!-- FORMULA_MIXING_PROTOCOL_END -->", 1)[0]
    assert "1. **Always used:** Hedione 140; Iso E Super 140" in rendered
    assert "Ambrettolide (10% w/w in DPG) 1600" in rendered
    assert "11. **Iris and orris:** Alpha Isomethyl Ionone 420" in rendered
    assert "15. **Fruits:** Verdox 280; Benzyl Acetate 220; Ethyl 2-Methylbutyrate (0.1%) 50" in rendered
    card = rendered.split("#### Exact transfer card", 1)[1].split("#### Seventeen-basket checkpoints", 1)[0]
    transfers = []
    running = []
    for line in card.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|\s*\d+\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        transfers.append(float(cells[4].replace("µL", "").replace(",", "")))
        running.append(float(cells[5].replace("µL", "").replace(",", "")))
    assert len(transfers) == 30
    assert sum(transfers) == pytest.approx(6000.0)
    cumulative = []
    total = 0.0
    for transfer in transfers:
        total += transfer
        cumulative.append(total)
    assert running == cumulative
    checkpoints = rendered.split("#### Seventeen-basket checkpoints", 1)[1]
    rows = [line for line in checkpoints.splitlines() if re.match(r"^\|\s*\d+\s*\|\s*(?:COMPOUND|SKIP)\s*\|", line)]
    assert len(rows) == 17
    assert "| 15 | COMPOUND | 28–30 | 550 µL | 6,000 µL |" in checkpoints
    assert "add exactly **24,000 µL Ethanol 96%**" in text
    assert "Do not q.s. to 30 mL" in text


def test_live_physical_labels_are_present_and_not_depleted():
    inventory_lines = (ROOT / "inventory.txt").read_text(encoding="utf-8").splitlines()
    labels = (
        "Ethanol 96%",
        "Benzyl Salicylate",
        "Indian Vetiver EO (volume grade)",
        "Cedarwood oil Virginia",
        "Cashmeran (neat)",
        "Sandalore",
        "Vetival",
        "Ambrettolide (10% w/w in DPG)",
        "Ethylene Brassylate",
        "Romandolide",
        "Lavender EO High Altitude (angustifolia, France)",
        "Mimosa Absolute (10% in DPG)",
        "Osmanthus Absolute (10% in DPG)",
        "Alpha Irone (10% w/w in DEP)",
        "Tonkarome (20% w/w in TEC)",
        "Ethyl 2-Methylbutyrate (0.1%)",
    )
    for label in labels:
        matches = [line for line in inventory_lines if line.startswith(f"- {label}")]
        assert len(matches) == 1, label
        assert "DEPLETED" not in matches[0].upper(), label


def test_richer_child_passes_strengthened_reference_and_family_while_parent_does_not(formula, formula_state):
    reference = evaluate_reference_contract(formula, formula_state)
    family = evaluate_family_archetype(formula, "iris_coumarin_amber.dhi2011")
    assert reference["status"] == "PASS"
    assert family.status == "PASS"
    group_names = set(reference["data"]["evaluations"][0]["group_metadata"])
    assert {
        "ambrette_musk_mediator",
        "pear_liqueur_facet",
        "talc_textile_cushion",
        "coumarinic_tonka_shadow",
        "vanillic_amber_shadow",
    }.issubset(group_names)

    parent = parse_formula_markdown(PARENT_PATH)[0]
    parent_state = build_formula_state(
        parent["ingredients_ul"],
        parent["dilutions"],
        stock_specs=parent["stock_specs"],
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    parent_reference = evaluate_reference_contract(parent, parent_state)
    assert parent_reference["status"] == "FAIL"
    assert {
        "pear_liqueur_facet",
        "talc_textile_cushion",
        "vanillic_amber_shadow",
    }.issubset(parent_reference["data"]["evaluations"][0]["missing_groups"])
    assert evaluate_family_archetype(parent, "iris_coumarin_amber.dhi2011").status == "FAIL"


def test_smoothness_is_noncompensatory_and_all_controlled_omissions_are_declared():
    text = FORMULA_PATH.read_text(encoding="utf-8")
    assert "Smoothness is a separate endpoint from liking" in text
    assert "continuity **and** legibility of both endpoints" in text
    assert "**Pear continuum:**" in text
    assert "**Talc cushion:**" in text
    assert "**Iris anatomy:**" in text
    assert "**Warm seam:**" in text
    assert "**Musk axes:**" in text
    assert "hidden repeated control" in text
    assert "No average score may compensate" in " ".join(text.split())
