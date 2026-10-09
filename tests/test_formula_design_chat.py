from pathlib import Path

import pytest

import engine.inventory_parser as inventory_parser
from engine.inventory_parser import materialize_current_inventory
from engine.research.formula_design import design_inventory_formula


def test_formula_design_is_deterministic_inventory_grounded_and_advisory() -> None:
    request = {
        "idea": "A clear mineral lavender over dry amber, not sweet",
        "formula_name": "Stone Lavender",
        "liquid_concentrate_ul_decimal": "6000",
        "max_materials": 8,
        "must_preserve": ("lavender identity",),
        "must_avoid": ("vanilla",),
    }

    first = design_inventory_formula(**request)
    second = design_inventory_formula(**request)

    assert first == second
    assert first["status"] in {
        "INVENTORY_GROUNDED_DESIGN_READY",
        "INVENTORY_GROUNDED_DESIGN_READY_WITH_HOLDS",
    }
    assert first["formula_action"] == "PROPOSAL_ONLY"
    assert first["inventory_modified"] is False
    assert first["formula_modified"] is False
    assert first["release_authority"] is False
    assert first["safety_authority"] is False
    assert first["compounding_authority"] is False
    assert first["evidence_admission_authorized"] is False
    assert first["pleasantness"] is None
    assert first["beauty_score"] is None
    assert first["prohibited_objectives_used"] == []

    materialized = materialize_current_inventory()
    current_stock_ids = {stock.stock_id for stock in materialized.stocks}
    rows = first["optimized_formula"]["rows"]
    assert 6 <= len(rows) <= 8
    bound_rows = [row for row in rows if not row["stock_id"].startswith("inventory:text")]
    assert {row["stock_id"] for row in bound_rows} <= current_stock_ids
    assert any("Lavender" in row["material"] for row in rows)
    assert all("Vanillin" not in row["material"] for row in rows)
    assert first["optimized_formula"]["separate_totals"]["liquid_total_ul"] == "6000"
    assert float(first["optimization"]["optimized_alignment_decimal"]) >= float(
        first["optimization"]["initial_alignment_decimal"]
    )


def test_formula_design_preserves_crystal_ambrox_as_separate_mass() -> None:
    result = design_inventory_formula(
        idea="A crystal Ambrox and grapefruit mineral perfume, dry and transparent",
        formula_name="Crystal Current",
    )

    rows = result["optimized_formula"]["rows"]
    ambrox = next(row for row in rows if row["identity_name"] == "Ambrox Super")
    assert ambrox["amount_unit"] == "mg"
    assert ambrox["operation"] == "MASS_ADD"
    assert int(result["optimized_formula"]["separate_totals"]["mass_total_mg"]) > 0
    assert result["optimized_formula"]["basis_state"] == "SEPARATE_LIQUID_AND_SOLID_TOTALS"
    assert any(row["identity_name"] == "Grapefruit FCF Oil Sicilian" for row in rows)
    grapefruit = next(row for row in rows if row["identity_name"] == "Grapefruit FCF Oil Sicilian")
    assert grapefruit["profile_source"] == "HEURISTIC_CATEGORY_PROXY"


def test_formula_design_withholds_an_unbound_quantity_in_chat() -> None:
    result = design_inventory_formula(
        idea="Use 15 uL to create something mysterious",
        formula_name="Unbound Measure",
    )

    assert result["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert result["optimized_formula"] is None
    assert result["formula_action"] == "NO_CHANGE"
    assert "QUANTITY_WITHOUT_EXACT_MATERIAL_BINDING" in result["request_interpretation"]["ambiguities"]


def test_formula_design_follow_up_keeps_a_bounded_inventory_seed() -> None:
    initial = design_inventory_formula(
        idea="A transparent green floral with a cool woody trail",
        formula_name="Green Air",
    )
    stock_ids = tuple(row["stock_id"] for row in initial["optimized_formula"]["rows"])

    refined = design_inventory_formula(
        idea="Make the heart more radiant but keep it green and not sweeter",
        formula_name=initial["formula_name"],
        previous_stock_ids=stock_ids,
        conversation_context=("A transparent green floral with a cool woody trail",),
    )

    assert refined["status"] in {
        "INVENTORY_GROUNDED_DESIGN_READY",
        "INVENTORY_GROUNDED_DESIGN_READY_WITH_HOLDS",
    }
    assert refined["constraint_audit"]["liquid_total_conserved"] is True
    refined_ids = {row["stock_id"] for row in refined["optimized_formula"]["rows"]}
    assert refined_ids & set(stock_ids)
    # Concept roles, up to four supporting base layers and two supporting
    # accord materials per requested note.
    assert 6 <= len(refined_ids) <= 20
    assert refined["physical_compounding_performed"] is False


def test_formula_design_treats_sixty_as_a_ceiling_and_adds_no_filler() -> None:
    result = design_inventory_formula(
        idea=(
            "A complex luminous lavender amber perfume with citrus, floral depth, "
            "dry woods and incense, not sweet"
        ),
        formula_name="Lavender Panorama",
        max_materials=60,
    )

    rows = result["optimized_formula"]["rows"]
    assert result["requested_material_limit"] == 60
    assert 6 <= result["selected_material_count"] < 60
    assert len(rows) == result["selected_material_count"]
    assert len({row["stock_id"] for row in rows}) == len(rows)
    assert result["optimized_formula"]["separate_totals"]["liquid_total_ul"] == "6000"
    assert result["optimization"]["objective"] == (
        "REQUEST_CONSTRAINT_AND_NONREDUNDANT_ROLE_FULFILMENT"
    )
    assert result["critic"]["filler_rows_added"] == 0
    assert result["critic"]["stop_reason"] == "ALL_JUSTIFIED_ROLES_COVERED"
    assert result["beauty_score"] is None


def test_formula_design_default_ceiling_is_sixty_materials() -> None:
    # 2026-10-09 08:01 UTC: Kenny raised the default ceiling from 15 to 60 so
    # layers and accents fit. It is a ceiling: the composer stops once its
    # notes, accords and layers are placed.
    result = design_inventory_formula(
        idea="a panoramic, exceptionally detailed modern chypre with rose, patchouli and oakmoss",
        formula_name="Panoramic Chypre",
    )

    rows = result["optimized_formula"]["rows"]
    assert result["requested_material_limit"] == 60
    assert 6 <= result["selected_material_count"] < 60
    assert len(rows) == result["selected_material_count"]
    assert result["optimized_formula"]["separate_totals"]["liquid_total_ul"] == "6000"


def test_formula_design_rejects_more_than_sixty_materials() -> None:
    with pytest.raises(ValueError, match="between 6 and 60"):
        design_inventory_formula(idea="A broad lavender perfume", max_materials=61)


def test_formula_design_uses_semantic_global_solver_for_unseen_concept() -> None:
    result = design_inventory_formula(
        idea=(
            "A cold metallic pear perfume with ink, violet powder and dry cedar, "
            "no vanilla"
        ),
        formula_name="Chrome Orchard",
        max_materials=30,
    )

    assert result["schema_version"] == "inventory-grounded-formula-design-v3"
    assert result["composition_plan"]["method"] == (
        "SEMANTIC_TARGET_PLUS_GLOBAL_CONSTRAINT_SOLVER_V1"
    )
    assert result["runtime"]["global_role_assignment"] is True
    assert result["runtime"]["network_used"] is False
    assert {"violet_powder", "mineral_salt", "fruit", "powder"} <= set(
        result["matched_descriptors"]
    )
    assert result["requested_material_limit"] == 30
    assert 6 <= result["selected_material_count"] < 30
    selected = " ".join(
        row["identity_name"].casefold()
        for row in result["optimized_formula"]["rows"]
    )
    assert "vanill" not in selected
    assert result["pleasantness"] is None
    assert result["beauty_score"] is None


def test_formula_design_deep_compose_returns_diverse_unordered_variants() -> None:
    result = design_inventory_formula(
        idea=(
            "A luminous bitter apricot tea perfume over cool stone, pale iris, "
            "and quiet dry roots"
        ),
        formula_name="Apricot Lithograph",
        max_materials=30,
        design_mode="DEEP_COMPOSE",
    )

    assert result["design_mode"] == "DEEP_COMPOSE"
    variants = result["design_variants"]
    assert len(variants) == 3
    signatures = {
        tuple(row["stock_id"] for row in variant["formula"]["rows"])
        for variant in variants
    }
    assert len(signatures) >= 2
    assert all(
        variant["ordering"] == "UNORDERED_UNTIL_SENSORY_COMPARISON"
        for variant in variants
    )
    assert all(
        variant["solver"]["prohibited_objectives_used"] == []
        for variant in variants
    )


def test_formula_design_deep_mode_does_not_collapse_to_one_curated_capsule() -> None:
    result = design_inventory_formula(
        idea="Create a cool iris and incense cathedral with mineral stone air.",
        formula_name="Iris Cathedral",
        max_materials=18,
        design_mode="DEEP_COMPOSE",
        variant_count=3,
    )

    assert result["design_mode"] == "DEEP_COMPOSE"
    assert 1 < len(result["design_variants"]) <= 3
    signatures = {
        tuple((row["stock_id"], row["amount_decimal"], row["amount_unit"])
              for row in variant["formula"]["rows"])
        for variant in result["design_variants"]
    }
    assert len(signatures) == len(result["design_variants"])
    assert all(
        variant["ordering"] == "UNORDERED_UNTIL_SENSORY_COMPARISON"
        for variant in result["design_variants"]
    )


def test_formula_design_honors_exact_seven_material_request() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a seven-material transparent muguet with watery bells, "
            "green stalk and cold air. No vanilla."
        ),
        formula_name="Seven Bells",
        max_materials=30,
    )

    assert result["status"].startswith("INVENTORY_GROUNDED_DESIGN_READY")
    assert result["selected_material_count"] == 7
    assert result["effective_material_limit"] == 7
    assert not any("__accord_" in row["slot"] for row in result["optimized_formula"]["rows"])
    assert (
        "REQUESTED_MATERIAL_COUNT_CONSTRAINTS_SATISFIED"
        in result["critic"]["passed_checks"]
    )


def test_formula_design_withholds_count_above_configured_ceiling() -> None:
    result = design_inventory_formula(
        idea="Create an exactly twelve-material green perfume.",
        formula_name="Twelve Green",
        max_materials=8,
    )

    assert result["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert result["optimized_formula"] is None
    assert result["formula_action"] == "NO_CHANGE"
    assert (
        "REQUESTED_MATERIAL_COUNT_EXCEEDS_CONFIGURED_CEILING"
        in result["reason_codes"]
    )


def test_formula_design_keeps_nfkc_micro_quantity_exact() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a transparent pear and muguet perfume using exactly 15 μL "
            "of Hedione, with mineral air and no vanilla."
        ),
        formula_name="Pear Glass",
        max_materials=30,
    )

    row = next(
        item
        for item in result["optimized_formula"]["rows"]
        if item["identity_name"] == "Hedione"
    )
    assert row["amount_decimal"] == "15"
    assert row["amount_unit"] == "uL"


def test_formula_design_uses_one_exact_lemonile_stock_and_no_citrus_oil() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a dry citrus cologne without any citrus essential oil, "
            "Bergamot, Grapefruit oil, Mandarin oil, Lime oil, Lemon oil, "
            "Orange oil or Neroli. Include exactly 20 µL of neat Lemonile."
        ),
        formula_name="Citrus Without Citrus Oils",
        max_materials=14,
        must_avoid=(
            "citrus essential oil",
            "Bergamot",
            "Grapefruit oil",
            "Mandarin oil",
            "Lime oil",
            "Lemon oil",
            "Orange oil",
            "Neroli",
        ),
    )

    rows = result["optimized_formula"]["rows"]
    lemonile = [row for row in rows if row["identity_name"] == "Lemonile"]
    assert len(lemonile) == 1
    assert lemonile[0]["stock_label"] == "Lemonile neat/as supplied"
    assert lemonile[0]["amount_decimal"] == "20"
    assert not any(
        "citrus" in row["stock_label"].casefold()
        or any(
            marker in row["identity_name"].casefold()
            for marker in (
                "bergamot",
                "grapefruit",
                "mandarin",
                "lime oil",
                "lemon oil",
                "orange peel",
                "neroli",
                "petitgrain",
                "cedrat",
            )
        )
        for row in rows
    )


def test_formula_design_expanded_brief_gets_more_nonredundant_roles() -> None:
    minimal = design_inventory_formula(
        idea="Create a seven-material lavender, herb, moss and dry-wood fougere.",
        formula_name="Fern Cabinet Minimal",
        max_materials=22,
    )
    expanded = design_inventory_formula(
        idea=(
            "Build an expanded layered fougere with two lavender registers, "
            "minty herbs, geranium, moss, root and dry timber."
        ),
        formula_name="Fern Cabinet Expanded",
        max_materials=22,
    )

    assert minimal["selected_material_count"] == 7
    assert expanded["selected_material_count"] >= 12
    assert expanded["critic"]["filler_rows_added"] == 0
    assert len(
        {row["identity_name"] for row in expanded["optimized_formula"]["rows"]}
    ) == expanded["selected_material_count"]


def test_formula_design_animalic_fur_does_not_collapse_to_clean_skin_capsule() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a six-material restrained animalic perfume suggesting warm "
            "skin, clean fur, dry wood and floral breath. Keep it intimate, not "
            "fecal or urinous."
        ),
        formula_name="Warm Pelt Six",
        max_materials=6,
        must_avoid=("fecal", "urinous", "dirty leather"),
    )

    assert "animalic_fur" in result["matched_descriptors"]
    assert result["selected_material_count"] == 6
    assert any(
        row["slot"] == "facet_animalic_fur"
        for row in result["optimized_formula"]["rows"]
    )
    assert not any(
        row["identity_name"] in {"Birch Tar Rectified", "Skatole"}
        for row in result["optimized_formula"]["rows"]
    )


def test_formula_design_honors_exact_crystal_mass_and_separate_liquid_total() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a dry lavender fougere using exactly 180 mg of neat Ambrox "
            "Super crystals as a separate solid line. Do not use Ambrox solution "
            "or convert the crystal mass to microlitres. Keep the liquid concentrate "
            "exactly 6000 microlitres."
        ),
        max_materials=18,
    )

    assert result["status"] == "INVENTORY_GROUNDED_DESIGN_READY"
    solid = next(row for row in result["optimized_formula"]["rows"] if row["amount_unit"] == "mg")
    assert solid["identity_name"] == "Ambrox Super"
    assert solid["amount_decimal"] == "180"
    assert result["optimized_formula"]["separate_totals"] == {
        "liquid_total_ul": "6000",
        "mass_total_mg": "180",
    }
    assert all("25%" not in row["stock_label"] for row in result["optimized_formula"]["rows"])


def test_formula_design_honors_natural_language_exclusions_before_selection() -> None:
    result = design_inventory_formula(
        idea=(
            "Make a dry lavender, herb, moss and vetiver fougere. Do not use "
            "Hedione, Iso E Super, Dihydromyrcenol, bergamot, Galaxolide, "
            "vanilla or Amber Xtreme."
        ),
        max_materials=16,
    )

    selected = " ".join(
        f"{row['material']} {row['identity_name']}".casefold()
        for row in result["optimized_formula"]["rows"]
    )
    for prohibited in (
        "hedione",
        "iso e super",
        "dihydromyrcenol",
        "bergamot",
        "galaxolide",
        "vanill",
        "amber xtreme",
    ):
        assert prohibited not in selected


def test_formula_design_withholds_impossible_and_unavailable_briefs() -> None:
    contradictory = design_inventory_formula(
        idea=(
            "Create one uniform lavender fougere that is intensely hot and completely "
            "cold at the same time, very sweet and completely unsweetened, and that "
            "must contain Ambrox Super and must contain no Ambrox material."
        ),
        max_materials=12,
    )
    unavailable = design_inventory_formula(
        idea=(
            "Create a current-inventory executable green fig perfume and make "
            "Polysantol mandatory. Do not use unavailable material."
        ),
        max_materials=12,
    )

    assert contradictory["status"] == "WITHHELD_REQUEST_AMBIGUOUS"
    assert contradictory["optimized_formula"] is None
    assert unavailable["status"] == "WITHHELD_MANDATORY_MATERIAL_UNAVAILABLE"
    assert unavailable["optimized_formula"] is None


def test_formula_design_uses_exact_ambrettolide_stock_amount_and_only_one_musk() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a quiet skin scent using exactly 120 microlitres of the owned "
            "Ambrettolide 10% w/w in DPG stock. It must be the only musk. Do not "
            "substitute neat Ambrettolide or add another musk."
        ),
        max_materials=10,
    )

    rows = result["optimized_formula"]["rows"]
    ambrettolide = next(row for row in rows if row["identity_name"] == "Ambrettolide")
    assert ambrettolide["amount_decimal"] == "120"
    assert ambrettolide["amount_unit"] == "uL"
    musk_names = [
        row["identity_name"]
        for row in rows
        if any(token in row["identity_name"].casefold() for token in (
            "musk", "ambrettolide", "habanolide", "zenolide", "romandolide", "exaltolide", "brassylate", "galaxolide"
        ))
    ]
    assert musk_names == ["Ambrettolide"]


def test_formula_design_withholds_same_bottle_delta_without_bottle_state() -> None:
    result = design_inventory_formula(
        idea=(
            "This is not a new formula. Add one small nonnegative delta to my existing "
            "Quiet Human bottle to make it less detergent-like, but I am not providing "
            "the current bottle composition or total volume."
        ),
        max_materials=8,
    )

    assert result["status"] == "WITHHELD_ACTIVE_BOTTLE_STATE_REQUIRED"
    assert result["formula_action"] == "NO_CHANGE"


@pytest.mark.parametrize(
    ("formula_name", "idea", "maximum", "concept_id"),
    [
        (
            "Tea Pith Miniature",
            "Create a six-material bitter grapefruit, dry black-tea and transparent cedar cologne. It must feel tailored and unsweetened, not sporty.",
            6,
            "bitter_grapefruit_tea",
        ),
        (
            "Dry Lavender Hinge",
            "Create a minimal dry lavender fougere with aromatic herbs, a restrained moss-coumarin hinge and vetiver. No shaving foam.",
            7,
            "dry_lavender_fougere",
        ),
        (
            "Rose Suede Line",
            "Create a minimal dark rose, dry patchouli, moss and pale-suede chypre. Tailored, austere and unsweetened.",
            8,
            "rose_suede_chypre",
        ),
        (
            "Fig Cardamom Six",
            "Create a minimal green fig, cardamom and creamy sandalwood perfume with a leafy opening and no coconut-dessert effect.",
            8,
            "green_fig_cardamom",
        ),
        (
            "Tuberose in Six Movements",
            "Create a minimal unmistakable tuberose perfume with green lift and clear air around the flower. No banana, bubblegum or coconut cream.",
            6,
            "green_tuberose",
        ),
        (
            "Iris Chapel Seven",
            "Create a minimal cool iris, pale frankincense, old cedar and distant candle-smoke perfume. No lipstick vanilla.",
            7,
            "iris_incense_cathedral",
        ),
        (
            "Roasted Wood Seven",
            "Create a minimal roasted coffee, dark cocoa and dry wood perfume. It must not smell sugary, edible or like vanilla dessert.",
            7,
            "dry_coffee_cocoa",
        ),
        (
            "Salt Glass Six",
            "Create a minimal cold mineral, bitter-citrus and salt-air perfume without melon, blue shower gel or laundry musk.",
            6,
            "mineral_coast",
        ),
        (
            "Quiet Human Six",
            "Create a six-material intimate human skin scent with soft warmth and close diffusion, not detergent, shampoo or loud clean musk.",
            6,
            "intimate_skin",
        ),
        (
            "Monsoon Market Ten",
            "In ten materials, portray wet pavement, crushed Thai herbs, humid jasmine, tea, warm wood and incense after monsoon rain. Keep the stages readable.",
            10,
            "monsoon_market",
        ),
    ],
)
def test_formula_design_maps_benchmark_concepts_to_specific_architectures(
    formula_name: str,
    idea: str,
    maximum: int,
    concept_id: str,
) -> None:
    result = design_inventory_formula(
        idea=idea,
        formula_name=formula_name,
        max_materials=maximum,
    )

    assert result["concept_family"] == concept_id
    assert result["composition_plan"]["method"] == "CONCEPT_ROLE_COMPILER_V3_CRITIC_REPAIR"
    assert result["critic"]["filler_rows_added"] == 0
    assert 6 <= result["selected_material_count"] <= maximum
    assert result["optimized_formula"]["separate_totals"]["liquid_total_ul"] == "6000"


def test_formula_design_honors_all_required_tuberose_product_forms() -> None:
    result = design_inventory_formula(
        idea=(
            "Use all three owned tuberose forms: Tuberlia Base, Tuberose Absolute "
            "10% in DPG, and Tuberose EO volume grade. Do not add a fourth tuberose "
            "form. Keep them in separate nonredundant roles."
        ),
        formula_name="Three Tuberose Registers",
        max_materials=12,
    )

    rows = result["optimized_formula"]["rows"]
    tuberose = [row for row in rows if "tuber" in row["stock_label"].casefold()]
    assert len(tuberose) == 3
    assert {row["identity_name"] for row in tuberose} == {
        "Tuberlia Base",
        "Tuberose Absolute",
        "Tuberose EO (volume level grade)",
    }


def test_formula_design_keeps_exact_tuberose_base_distinct_from_tuberlia() -> None:
    result = design_inventory_formula(
        idea=(
            "Use all three exact owned forms: Tuberose Base, Tuberose Absolute "
            "10% in DPG, and Tuberose EO volume grade. Give each a separate role."
        ),
        formula_name="Exact Three Tuberoses",
        max_materials=12,
    )

    identities = {
        row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if "tuber" in (row["identity_name"] + row["stock_label"]).casefold()
    }
    assert identities == {
        "Tuberose Base",
        "Tuberose Absolute",
        "Tuberose EO (volume level grade)",
    }


def test_formula_design_expands_temporal_brief_and_marks_timing_unvalidated() -> None:
    result = design_inventory_formula(
        idea=(
            "Create crushed fig leaf in the opening, milky cardamom fig at thirty "
            "minutes, and creamy sandalwood at four hours. Treat the sequence as "
            "a design hypothesis."
        ),
        formula_name="Fig Through Time",
        max_materials=18,
    )

    assert 8 <= result["selected_material_count"] <= 11
    assert result["temporal_hypothesis"]["physical_timing_established"] is False
    assert "TEMPORAL_BEHAVIOR_NOT_PHYSICALLY_VALIDATED" in result["critic"]["limitations"]
    stages = {
        stage["window"]: stage
        for stage in result["temporal_hypothesis"]["sequence"]
    }
    assert any(
        "milky sap" in row["role"].casefold()
        for row in stages["THIRTY_MINUTES"]["intended_roles"]
    )
    assert any(
        "sandalwood" in row["role"].casefold()
        for row in stages["FOUR_HOURS"]["intended_roles"]
    )


def test_formula_design_uses_named_commercial_products_as_documentary_context_only() -> None:
    result = design_inventory_formula(
        idea=(
            "Make a mass-market wearable mineral perfume and compare its intended "
            "architecture with Sauvage EDP and Prada Luna Rossa Carbon without "
            "copying either. Keep sales separate from liking."
        ),
        formula_name="Reference-Safe Mineral",
        max_materials=24,
    )

    context = result["commercial_reference_context"]
    assert context["status"] == "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
    assert {item["product_id"] for item in context["named_products"]} == {
        "dior-sauvage-edp",
        "prada-luna-rossa-carbon-edt",
    }
    assert context["proprietary_composition_state"] == "PROPRIETARY_COMPOSITION_UNKNOWN"
    assert context["population_liking_state"] == "POPULATION_LIKING_NOT_ESTABLISHED"
    assert context["formula_inference_used"] is False
    assert all("selected_architecture_links" in item for item in context["named_products"])


def test_formula_design_withholds_if_exact_requested_iris_stock_is_held(monkeypatch) -> None:
    # The live Orris hold was lifted on 2026-10-08; test against the old record.
    monkeypatch.setattr(
        inventory_parser,
        "USER_COMPOUNDING_HOLDS_PATH",
        Path(__file__).parent / "fixtures" / "orris_liquid_hold_20261005.json",
    )
    result = design_inventory_formula(
        idea=(
            "Use exactly Alpha Irone 10% in DEP, Orris Liquid 9% in DEP, and "
            "Olibanum Resinoid 50% w/w in DPG as separate lines in a cool iris "
            "and incense structure."
        ),
        formula_name="Exact Iris Incense",
        max_materials=10,
    )

    assert result["status"] == "WITHHELD_MANDATORY_MATERIAL_UNAVAILABLE"
    assert result["optimized_formula"] is None
    assert result["formula_action"] == "NO_CHANGE"
    assert any(
        "orris liquid" in reason.casefold()
        for reason in result["constraint_audit"]["reason_codes"]
    )


def test_formula_design_treats_any_musk_as_a_group_level_exclusion() -> None:
    result = design_inventory_formula(
        idea=(
            "Create an intimate warm-skin illusion. Do not use any musk material, "
            "Iso E Super, Hedione, Ambrox, vanilla, lactone or fruity ester."
        ),
        formula_name="Skin Without Musk",
        max_materials=12,
    )

    identities = " ".join(
        row["identity_name"].casefold()
        for row in result["optimized_formula"]["rows"]
    )
    for forbidden in (
        "musk",
        "ambrettolide",
        "brassylate",
        "exaltolide",
        "galaxolide",
        "habanolide",
        "romandolide",
        "zenolide",
    ):
        assert forbidden not in identities


def test_formula_design_uses_a_low_odor_carrier_for_quiet_skin_structure() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a six-material intimate human skin scent with soft warmth and "
            "close diffusion, not detergent, shampoo or loud clean musk."
        ),
        formula_name="Quiet Human Six",
        max_materials=6,
    )

    rows = result["optimized_formula"]["rows"]
    carrier = next(row for row in rows if row["slot"] == "quiet_carrier")
    assert carrier["identity_name"] == "Benzyl Benzoate"
    assert int(carrier["amount_decimal"]) >= 2500
    assert all(
        int(row["amount_decimal"]) <= 1000
        for row in rows
        if row["slot"] != "quiet_carrier"
    )
    slots = {row["slot"] for row in rows}
    assert "clean_paper" not in slots
    assert "book_leather" not in slots
    assert "linen_air" not in slots


def test_formula_design_removes_musk_language_when_every_musk_is_excluded() -> None:
    result = design_inventory_formula(
        idea=(
            "Create an intimate warm-skin illusion. Do not use any musk material, "
            "Iso E Super, Hedione, Ambrox, vanilla, lactone or fruity ester."
        ),
        formula_name="Skin Without Musk",
        max_materials=12,
    )

    assert "no musk material is used" in result["assistant_message"].casefold()
    assert "one deliberate musk" not in result["assistant_message"].casefold()


def test_formula_design_prefers_defined_sandalwood_material_over_opaque_base() -> None:
    result = design_inventory_formula(
        idea=(
            "Create green fig, cardamom and creamy wood. Do not use Gamma "
            "Undecalactone, Allyl Amyl Glycolate, Hedione, Iso E Super, Javanol, "
            "vanilla or Ethyl Maltol."
        ),
        formula_name="Fig Without Shortcuts",
        max_materials=16,
    )

    row = next(
        item
        for item in result["optimized_formula"]["rows"]
        if item["slot"] == "creamy_sandalwood"
    )
    assert row["identity_name"] in {"Sandalore", "Ebanol", "Bacdanol"}
    assert row["identity_name"] != "Sandalwood Base 3X"


def test_formula_design_adds_explicit_wearability_roles_without_liking_claim() -> None:
    result = design_inventory_formula(
        idea=(
            "Make Iris Cathedral easier to wear beside successful prestige perfumes "
            "without erasing its cool iris-incense-stone identity."
        ),
        formula_name="Wearable Iris Cathedral",
        max_materials=22,
    )

    assert result["request_interpretation"]["appeal_mode"] == "GLOBAL_CROWD_PLEASING"
    assert {
        "wearable_entry",
        "soft_cathedral_exit",
    } <= set(result["composition_plan"]["roles_filled"])
    assert result["commercial_reference_context"]["status"] == (
        "DOCUMENTARY_PRESTIGE_DESIGN_CRITERIA_ONLY"
    )
    assert "transition clarity" in result["commercial_reference_context"]["design_criteria"]
    assert result["population_liking"] is None


def test_formula_design_maps_late_echo_to_persistent_signature_role() -> None:
    result = design_inventory_formula(
        idea=(
            "Create bitter grapefruit and black tea with cedar and moss. Explicitly "
            "treat the four-hour echo as a design hypothesis, not established performance."
        ),
        formula_name="Tea Echo",
        max_materials=14,
    )

    stage = next(
        item
        for item in result["temporal_hypothesis"]["sequence"]
        if item["window"] == "FOUR_HOURS"
    )
    assert "echo" in stage["requested_context"].casefold()
    assert any(
        role["role"] == "Persistent citrus-tea echo"
        for role in stage["intended_roles"]
    )
    echo = next(
        row
        for row in result["optimized_formula"]["rows"]
        if row["slot"] == "persistent_signature"
    )
    assert echo["identity_name"] == "Lemonile"


def test_formula_design_records_stock_strength_compensation_as_heuristic() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a minimal dark rose, dry patchouli, moss and pale-suede chypre. "
            "Tailored, austere and unsweetened."
        ),
        formula_name="Rose Suede Line",
        max_materials=8,
    )

    suede = next(
        item
        for item in result["optimized_formula"]["rows"]
        if item["slot"] == "pale_suede"
    )
    assert suede["allocation_basis"] == (
        "STOCK_STRENGTH_COMPENSATED_HEURISTIC_NOT_ACTIVE_MASS"
    )
    assert result["optimized_formula"]["exact_active_mass_established"] is False


def test_formula_design_does_not_claim_molecular_absence_inside_opaque_products() -> None:
    result = design_inventory_formula(
        idea=(
            "Make airy green tuberose. Do not use Hedione, Hedione HC, Benzyl "
            "Salicylate, Hexyl Salicylate, coconut-like lactones, banana-like "
            "materials or Indole."
        ),
        formula_name="Tuberose Without Cushions",
        max_materials=14,
    )

    assert (
        result["composition_uncertainty"]["requested_constituent_absence_state"]
        == "WITHHELD_OPAQUE_PRODUCTS"
    )
    assert any(
        item.endswith(":indole")
        for item in result["composition_uncertainty"]["limitations"]
    )


def test_formula_design_rejects_internally_conflicting_stock_forms() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a minimal dry coffee and bitter cocoa perfume with charred "
            "wood and no dessert sweetness."
        ),
        formula_name="Dry Roast",
        max_materials=7,
    )

    guaiacol = next(
        row
        for row in result["optimized_formula"]["rows"]
        if row["identity_name"] == "Guaiacol"
    )
    assert guaiacol["stock_fraction_decimal"] == "0.1"
    assert "neat" not in guaiacol["stock_label"].casefold()


def test_formula_design_uses_live_inventory_carrier_as_a_conflict_guard() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a monsoon night market perfume with wet pavement, herbs, "
            "jasmine tea, incense and warm wood."
        ),
        formula_name="Rain Market",
        max_materials=12,
    )

    geosmin = next(
        row
        for row in result["optimized_formula"]["rows"]
        if "geosmin" in row["identity_name"].casefold()
    )
    assert geosmin["stock_fraction_decimal"] == "0.001"
    assert geosmin["carrier"] == "tec"
    assert "dpg" not in geosmin["stock_label"].casefold()


def test_formula_design_deduplicates_generic_temporal_windows_and_keeps_tiers() -> None:
    result = design_inventory_formula(
        idea=(
            "Create storm air in the opening, a wet-mineral heart at thirty "
            "minutes and cold driftwood drydown at four hours."
        ),
        formula_name="Storm to Driftwood",
        max_materials=18,
    )

    stages = result["temporal_hypothesis"]["sequence"]
    assert [stage["window"] for stage in stages] == [
        "OPENING",
        "THIRTY_MINUTES",
        "FOUR_HOURS",
    ]
    rows_by_material = {
        row["material"]: row for row in result["optimized_formula"]["rows"]
    }
    for stage in stages:
        for intended in stage["intended_roles"]:
            assert rows_by_material[intended["material"]]["note"] == stage["intended_tier"]


def test_formula_design_does_not_add_third_tuberose_source_by_default() -> None:
    result = design_inventory_formula(
        idea=(
            "Create a high-definition tuberose with green stem, petal air and a "
            "quiet dry trail."
        ),
        formula_name="Tuberose Definition",
        max_materials=20,
    )

    tuberose_rows = [
        row
        for row in result["optimized_formula"]["rows"]
        if "tuber" in (row["identity_name"] + row["stock_label"]).casefold()
    ]
    assert len(tuberose_rows) == 2


def _base_layer_rows(result: dict) -> dict[str, dict]:
    return {
        row["slot"]: row
        for row in result["optimized_formula"]["rows"]
        if row["slot"].startswith("base_") and row["slot"].endswith(("_layer", "_contrast"))
    }


def test_formula_design_builds_a_layered_base_from_several_families() -> None:
    result = design_inventory_formula(
        idea="A warm woody amber for evening",
        formula_name="Evening Amber",
    )

    layers = _base_layer_rows(result)
    # Wood and amber are requested facets; the base adds a second wood, a musk
    # and a balsamic resin around them instead of more of the same amber.
    assert {"base_wood_contrast", "base_musk_layer", "base_resin_layer"} <= set(layers)
    assert "drydown_structure" not in {row["slot"] for row in result["optimized_formula"]["rows"]}
    base_identities = {
        row["identity_name"]
        for row in result["optimized_formula"]["rows"]
        if row["note"] == "base"
    }
    assert len(base_identities) >= 5
    total_ul = sum(int(row["amount_decimal"]) for row in result["optimized_formula"]["rows"])
    for row in layers.values():
        assert int(row["amount_decimal"]) <= total_ul * 0.08


def test_formula_design_base_layers_respect_avoid_and_light_briefs() -> None:
    result = design_inventory_formula(
        idea="A fresh citrus cologne with a soft musky drydown",
        formula_name="Clean Cologne",
        must_avoid=("amber",),
    )

    layers = _base_layer_rows(result)
    assert "skin_musk" in result["matched_descriptors"]
    assert "base_amber_layer" not in layers
    assert "base_resin_layer" not in layers
    assert "base_musk_layer" not in layers  # the requested musk already covers it


def test_formula_design_base_layers_never_reach_an_ifra_limit() -> None:
    from engine.ifra_safety import get_ifra_limit

    for idea in ("A warm woody amber for evening", "A rose perfume for spring"):
        result = design_inventory_formula(idea=idea, formula_name="Layer IFRA")
        supporting = [
            *_base_layer_rows(result).values(),
            *(row for row in result["optimized_formula"]["rows"] if "__accord_" in row["slot"]),
        ]
        assert supporting
        for row in supporting:
            limit = get_ifra_limit(row["identity_name"])
            if limit is None:
                continue
            # 6,000 uL of concentrate in a 30 mL bottle.
            finished_pct = (
                float(row["amount_decimal"]) * float(row["stock_fraction_decimal"]) / 30_000 * 100
            )
            assert finished_pct <= limit, (idea, row["identity_name"], finished_pct, limit)


def test_formula_design_builds_each_requested_note_as_an_accord() -> None:
    # Two supports per note need room beyond the 15-material default.
    result = design_inventory_formula(
        idea="A warm woody amber for evening",
        formula_name="Evening Amber",
        max_materials=30,
    )

    rows = {row["slot"]: row for row in result["optimized_formula"]["rows"]}
    for lead_slot in ("facet_dry_wood", "facet_amber_mineral"):
        lead = rows[lead_slot]
        supports = [rows[slot] for slot in rows if slot.startswith(f"{lead_slot}__accord_")]
        assert len(supports) == 2, lead_slot
        identities = {lead["identity_name"], *(row["identity_name"] for row in supports)}
        assert len(identities) == 3
        for support in supports:
            assert support["note"] == lead["note"]
            # The lead keeps the named character; supports add nuance.
            assert int(support["amount_decimal"]) < int(lead["amount_decimal"])
