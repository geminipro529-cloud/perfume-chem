import re
from pathlib import Path

import pytest

from engine.pipeline.natural_absolute_decomposition import (
    get_composite_metadata,
    get_constituents,
)
from engine.reference_contracts import (
    ARCHITECTURE,
    CREED_AVENTUS_OFFICIAL_NOTES_V1,
    CREED_AVENTUS_OFFICIAL_NOTES_V2,
    REFERENCE_CONTRACTS,
    _evaluate_contract_groups,
)
from future_modules.advanced_musk_intelligence import HELVETOLIDE
from future_modules.iconic_formulas import (
    AVENTUS_ARCHITECTURE,
    AVENTUS_SKELETON,
    get_aventus_architecture_module,
)
from future_modules.niche_construction import DIFFUSION_PLATFORMS
from scripts.verify_formula_workflow import (
    parse_formula_markdown,
    split_generated_pipeline_analysis,
)


def test_aventus_target_is_architecture_first_and_fruit_secondary() -> None:
    module = get_aventus_architecture_module()
    layers = {layer.layer: layer for layer in module.target_ideal}

    assert module is AVENTUS_ARCHITECTURE
    assert module.head_priority == (
        "Bergamot FCF oil Sicilian",
        "Blackcurrant Absolute (10% in DPG)",
    )
    assert module.secondary_fruit == ("Allyl Amyl Glycolate (10%)",)
    assert layers["head"].prominence == "primary"
    assert layers["heart"].prominence == "secondary"
    assert layers["base"].prominence == "primary"
    assert "Pineapple Accord" in layers["heart"].markers
    assert "pineapple" in module.primary_rule.lower()
    assert "secondary" in module.primary_rule.lower()


def test_aventus_current_build_uses_live_stock_and_keeps_gaps_explicit() -> None:
    inventory = Path("inventory.txt").read_text(encoding="utf-8")
    mappings = {item.target_function: item for item in AVENTUS_ARCHITECTURE.current_inventory_build}

    for mapping in mappings.values():
        for material in mapping.stock_materials:
            assert material in inventory

    pepper = mappings["pink_pepper_bridge"]
    assert pepper.stock_materials == ("Pink Pepper EO (Schinus molle; neat / as supplied)",)
    assert pepper.status == "OWNED_CURRENT_INVENTORY_EXECUTION_READY_RAW_VOLUME_ONLY"
    assert "Pink Pepper EO / CO2 requirement as a separate GAP" in pepper.note
    assert "Black Pepper EO is not equivalent" in pepper.note
    assert pepper.stock_materials[0] in inventory
    assert "COMPOSITE_OAV_REQUIRED" in mappings["blackcurrant_head"].status
    assert "Birch Tar" in mappings["smoky_birch_effect"].note
    assert "prohibited" in mappings["smoky_birch_effect"].note
    assert all(not mapping.equivalence for mapping in mappings.values())


def test_aventus_relations_are_falsifiable_and_authority_stays_withheld() -> None:
    module = AVENTUS_ARCHITECTURE

    assert len(module.relations) == 3
    assert all(relation.omission_loss for relation in module.relations)
    assert all(relation.failure_mode for relation in module.relations)
    assert all(relation.temporal_windows for relation in module.relations)
    assert all("constant" in relation.controlled_comparison.lower() for relation in module.relations)
    assert "architecture-first versus pineapple-forward" in module.next_comparison.lower()
    assert module.component_count_used_as_complexity is False
    assert module.predicted_oav_used_as_perception is False
    assert module.composition_score_used_as_hedonic is False
    assert module.quantitative_authority == "UNKNOWN"
    assert module.sensory_authority == "NOT_TESTED"
    assert module.formula_authority is False
    assert module.physical_authority is False
    assert module.safety_authority is False
    assert module.release_authority is False


def test_aventus_skeleton_does_not_invent_commercial_percentages() -> None:
    roles = {name: role for name, _percentage, role in AVENTUS_SKELETON.materials}

    assert all(percentage is None for _name, percentage, _role in AVENTUS_SKELETON.materials)
    assert AVENTUS_SKELETON.three_pillar_platform is None
    assert "architecture-first" in AVENTUS_SKELETON.construction_method
    assert "Secondary" in roles["Pineapple accord"]
    assert "QUANTITATIVE_FORMULA_UNKNOWN" in AVENTUS_SKELETON.data_confidence


def test_current_aventus_reference_contract_has_layered_role_hierarchy() -> None:
    contract = CREED_AVENTUS_OFFICIAL_NOTES_V2
    groups = {group.name: group for group in contract.marker_groups}

    assert REFERENCE_CONTRACTS[contract.contract_id] is contract
    assert contract.target_aliases == ("creed aventus", "aventus")
    assert CREED_AVENTUS_OFFICIAL_NOTES_V1.target_aliases == ()
    assert groups["bergamot"].layer == "head"
    assert groups["bergamot"].prominence == "primary"
    assert groups["blackcurrant"].layer == "head"
    assert groups["blackcurrant"].prominence == "primary"
    assert groups["pineapple"].layer == "heart"
    assert groups["pineapple"].prominence == "secondary"
    assert not {"blackcurrant", "cassis"}.intersection(groups["pineapple"].alternatives)
    assert "schinus molle" in groups["pink_pepper"].alternatives
    assert groups["smoky_birch"].layer == "base"
    assert groups["smoky_birch"].prominence == "primary"


def test_blackcurrant_no_longer_satisfies_the_pineapple_marker() -> None:
    result = _evaluate_contract_groups(
        CREED_AVENTUS_OFFICIAL_NOTES_V2,
        {"bergamot fcf oil sicilian", "blackcurrant absolute"},
        ARCHITECTURE,
    )

    assert "bergamot" in result["matched_groups"]
    assert "blackcurrant" in result["matched_groups"]
    assert "pineapple" in result["missing_groups"]
    assert result["group_metadata"]["pineapple"] == {
        "layer": "heart",
        "prominence": "secondary",
    }


def test_adjacent_aventus_platform_record_no_longer_claims_exact_percentages() -> None:
    platform = next(item for item in DIFFUSION_PLATFORMS if item.name == "Aventus Platform")

    assert platform.total_formula_pct is None
    assert "hypothesis" in platform.character.lower()
    assert "exact commercial ratios" in platform.construction_note.lower()


def test_helvetolide_profile_keeps_aventus_dose_unknown() -> None:
    assert HELVETOLIDE.aventus_scale_dose_pct is None
    assert "exact commercial dose" in HELVETOLIDE.key_insight.lower()
    assert "cannot be inferred" in HELVETOLIDE.tropical_notes.lower()


def test_schinus_composite_is_literature_partial_and_not_batch_specific() -> None:
    constituents = get_constituents("Pink Pepper EO (Schinus molle)")
    metadata = get_composite_metadata("Pink Pepper EO (Schinus molle)")

    assert constituents is not None
    assert len(constituents) == 8
    assert sum(row[1] for row in constituents) == pytest.approx(0.897)
    assert metadata is not None
    assert metadata.composition_authority == "LITERATURE_PARTIAL_PROFILE"
    assert metadata.batch_specific is False
    assert metadata.sources == ("https://doi.org/10.1080/0972060X.2004.10643396",)
    assert any("GC-O" in limitation for limitation in metadata.limitations)


def test_architecture_first_recipe_parses_to_6000_ul_with_secondary_pineapple() -> None:
    formula_path = Path("formulas/Aventus_Architecture_First_Current_Inventory_30mL_EDP.md")
    formulas = parse_formula_markdown(formula_path)

    assert len(formulas) == 1
    formula = formulas[0]
    ingredients = formula["ingredients_ul"]
    assert len(ingredients) == 23
    assert sum(ingredients.values()) == pytest.approx(6000.0)
    assert ingredients["Bergamot FCF oil Sicilian"] == pytest.approx(500.0)
    assert ingredients["Blackcurrant Absolute"] == pytest.approx(250.0)
    assert ingredients["Allyl Amyl Glycolate"] == pytest.approx(60.0)
    assert ingredients["Pink Pepper EO (Schinus molle)"] == pytest.approx(10.0)
    assert ingredients["Romandolide"] == pytest.approx(400.0)
    assert ingredients["Dihydrojasmone"] == pytest.approx(150.0)
    assert ingredients["Benzyl Salicylate"] == pytest.approx(200.0)
    assert ingredients["Hexyl Salicylate"] == pytest.approx(150.0)
    assert ingredients["Petitgrain EO Paraguay"] == pytest.approx(100.0)
    assert ingredients["Coriander Essential Oil"] == pytest.approx(40.0)
    assert all("musk" not in name.casefold() for name in ingredients)


def test_layered_recipe_uses_all_17_baskets_and_descends_within_each() -> None:
    formula_path = Path("formulas/Aventus_Architecture_First_Current_Inventory_30mL_EDP.md")
    source, _artifact = split_generated_pipeline_analysis(
        formula_path.read_text(encoding="utf-8")
    )
    headings = list(
        re.finditer(r"^### Basket (\d+) — (.+)$", source, flags=re.MULTILINE)
    )

    assert [int(match.group(1)) for match in headings] == list(range(1, 18))
    expected_occupied = {1, 3, 4, 6, 7, 8, 13, 15, 17}
    occupied: set[int] = set()
    for index, heading in enumerate(headings):
        basket = int(heading.group(1))
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = source[heading.end() : end]
        doses = [
            float(value)
            for value in re.findall(
                r"^\|\s*\d+\s*\|[^|]+\|[^|]+\|\s*([0-9.]+)\s*\|",
                section,
                flags=re.MULTILINE,
            )
        ]
        if doses:
            occupied.add(basket)
            assert doses == sorted(doses, reverse=True), (basket, doses)
        else:
            assert "No materials in this formula" in section

    assert occupied == expected_occupied
    assert source.index("| 1 | Ambrox Super") < source.index("| 2 | Iso E Super")
    assert source.index("| 10 | Kephalis") < source.index("| 11 | Vertofix")
    assert "The baskets are a pull/addition order, not separate premixes" in source


def test_astra_v3_preserves_parent_stocks_and_exact_raw_total() -> None:
    parent_path = Path("formulas/Aventus_Architecture_First_Current_Inventory_30mL_EDP.md")
    child_path = Path(
        "formulas/Aventus_Architecture_First_Current_Inventory_30mL_EDP_V3_Astra.md"
    )
    parent = parse_formula_markdown(parent_path)[0]
    children = parse_formula_markdown(child_path)
    assert len(children) == 1
    child = children[0]
    expected = {
        "Iso E Super": 1250.0,
        "Ambrox Super": 1100.0,
        "Hedione": 700.0,
        "Patchouli EO": 350.0,
        "Hexyl Salicylate": 180.0,
        "Cedarwood oil Virginia": 350.0,
        "Cashmeran": 50.0,
        "Suederal": 150.0,
        "Kephalis": 120.0,
        "Cade Oil Rectified": 40.0,
        "Romandolide": 500.0,
        "Dihydrojasmone": 60.0,
        "Pink Pepper EO (Schinus molle)": 10.0,
        "Bergamot FCF oil Sicilian": 550.0,
        "Blackcurrant Absolute": 300.0,
        "Lemon FCF oil Sicilian": 100.0,
        "Allyl Amyl Glycolate": 60.0,
        "Petitgrain EO Paraguay": 50.0,
        "Evernyl": 80.0,
    }
    # This freezes the authored transfer recipe, not a minimum complexity count.
    assert child["ingredients_ul"] == expected
    assert sum(expected.values()) == pytest.approx(6000.0)
    assert min(expected.values()) >= 10.0
    assert all(child["dilutions"][name] == parent["dilutions"][name] for name in expected)
    assert set(parent["ingredients_ul"]) - set(expected) == {
        "Benzyl Salicylate", "Coriander Essential Oil", "Linalyl Acetate", "Vertofix"
    }


def test_astra_v3_basket_order_and_unproven_authority_are_explicit() -> None:
    path = Path("formulas/Aventus_Architecture_First_Current_Inventory_30mL_EDP_V3_Astra.md")
    source, _artifact = split_generated_pipeline_analysis(path.read_text(encoding="utf-8"))
    headings = list(re.finditer(r"^### Basket (\d+) — (.+)$", source, flags=re.MULTILINE))
    assert [int(match.group(1)) for match in headings] == list(range(1, 18))
    occupied = set()
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = source[heading.end():end]
        rows = [line.split("|") for line in section.splitlines() if re.match(r"^\|\s*\d+\s*\|", line)]
        if not rows:
            assert "No materials in this formula" in section
            continue
        occupied.add(int(heading.group(1)))
        doses = [float(row[4].strip()) for row in rows]
        assert doses == sorted(doses, reverse=True)
        assert all(float(row[5].strip()) == pytest.approx(float(row[4].strip()) / 1000) for row in rows)
        assert all(row[6].strip() == "UNKNOWN" for row in rows)
    assert occupied == {1, 3, 4, 6, 8, 13, 15, 17}
    assert "not separate accords or staged-day premixes" in source
    assert "Controlled six-case/three-condition Cypress benchmark: NOT RUN" in source
    assert "RELEASE HOLD" in source
    assert "not an isolated experiment proving improvement over V2" in source
    assert "supplier/model conflict for Romandolide" in source
