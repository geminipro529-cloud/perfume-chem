"""Top/heart layers and small accents the composer adds around requested notes."""

from functools import lru_cache

from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.formula_design import design_inventory_formula

WARM_AMBER = "A warm woody amber for evening"
FRESH_COLOGNE = "A fresh citrus cologne with a soft musky drydown"
SPRING_ROSE = "A rose perfume for spring"


@lru_cache(maxsize=None)
def _design(
    idea: str,
    formula_name: str,
    must_avoid: tuple[str, ...] = (),
    max_materials: int | None = None,
) -> dict:
    kwargs: dict = {"idea": idea, "formula_name": formula_name}
    if must_avoid:
        kwargs["must_avoid"] = must_avoid
    if max_materials is not None:
        kwargs["max_materials"] = max_materials
    return design_inventory_formula(**kwargs)


def _rows(result: dict) -> list[dict]:
    return result["optimized_formula"]["rows"]


def _slots(result: dict) -> set[str]:
    return {row["slot"] for row in _rows(result)}


def _supporting_rows(result: dict) -> list[dict]:
    return [row for row in _rows(result) if row["slot"].endswith(("_layer", "_accent"))]


def test_warm_brief_layers_every_register_and_adds_small_accents() -> None:
    result = _design(WARM_AMBER, "Evening Amber")

    slots = _slots(result)
    assert {
        "top_citrus_layer",
        "top_green_layer",
        "heart_floral_layer",
        "heart_powder_layer",
        "heart_spice_accent",
        "base_shadow_accent",
    } <= slots, sorted(slots)
    total_ul = sum(int(row["amount_decimal"]) for row in _rows(result))
    for row in _rows(result):
        amount = int(row["amount_decimal"])
        if row["slot"].endswith("_accent"):
            assert 10 <= amount <= total_ul * 0.025, (row["slot"], amount, total_ul)
        elif row["slot"].endswith("_layer"):
            assert amount <= total_ul * 0.08, (row["slot"], amount, total_ul)


def test_light_brief_drops_covered_and_warm_only_layers() -> None:
    result = _design(FRESH_COLOGNE, "Clean Cologne")

    slots = _slots(result)
    # The requested citrus already covers the top citrus layer; a light brief
    # takes no powder or spice, and the shadow accent is for warm briefs only.
    for slot in ("top_citrus_layer", "heart_powder_layer", "heart_spice_accent", "base_shadow_accent"):
        assert slot not in slots, (slot, sorted(slots))
    assert "top_green_layer" in slots, sorted(slots)


def test_floral_brief_skips_floral_layer_and_light_brief_skips_resin() -> None:
    slots = _slots(_design(SPRING_ROSE, "Spring Rose"))

    assert "heart_floral_layer" not in slots, sorted(slots)
    assert "base_resin_layer" not in slots, sorted(slots)


def test_must_avoid_removes_matching_layer_and_accent() -> None:
    slots = _slots(_design(WARM_AMBER, "Evening Amber", must_avoid=("floral", "spice")))

    assert "heart_floral_layer" not in slots, sorted(slots)
    assert "heart_spice_accent" not in slots, sorted(slots)
    # Only the avoided families go: the other layers and accents remain.
    assert {"top_green_layer", "base_shadow_accent"} <= slots, sorted(slots)


def test_tight_material_limit_keeps_room_for_each_requested_accord() -> None:
    result = _design(WARM_AMBER, "Evening Amber", max_materials=15)

    slots = _slots(result)
    for lead in ("facet_dry_wood", "facet_amber_mineral"):
        assert lead in slots, (lead, sorted(slots))
        assert any(slot.startswith(f"{lead}__accord_") for slot in slots), (lead, sorted(slots))
    # Layers still fill the remaining places, in the top and heart too.
    assert any(slot.startswith(("top_", "heart_")) and slot.endswith("_layer") for slot in slots)
    # Two places stay free for Deep Compose.
    assert len(_rows(result)) <= 13, sorted(slots)


def _compiled_role_ids(target_material_count: int | None) -> set[str]:
    brief = compile_semantic_brief(
        formula_name="Evening Amber",
        request=WARM_AMBER,
        interpretation={
            "explicit_materials": [],
            "must_avoid": [],
            "must_preserve": [],
            "material_count_constraints": [],
        },
        max_materials=20,
        target_material_count=target_material_count,
    )
    return {role.role_id for role in brief.roles}


def test_exact_material_count_compiles_no_layers_or_accents() -> None:
    exact = _compiled_role_ids(target_material_count=10)
    open_count = _compiled_role_ids(target_material_count=None)

    assert not {role for role in exact if role.endswith(("_layer", "_accent"))}, sorted(exact)
    assert any(role.endswith("_layer") for role in open_count), sorted(open_count)
    assert any(role.endswith("_accent") for role in open_count), sorted(open_count)


def test_layers_and_accents_never_reach_an_ifra_limit() -> None:
    from engine.ifra_safety import get_ifra_limit

    for idea, name in ((WARM_AMBER, "Evening Amber"), (SPRING_ROSE, "Spring Rose")):
        supporting = _supporting_rows(_design(idea, name))
        assert any(row["slot"].endswith("_accent") for row in supporting), idea
        for row in supporting:
            limit = get_ifra_limit(row["identity_name"])
            if limit is None:
                continue
            # 6,000 uL of concentrate in a 30 mL bottle.
            finished_pct = (
                float(row["amount_decimal"]) * float(row["stock_fraction_decimal"]) / 30_000 * 100
            )
            assert finished_pct <= limit, (idea, row["identity_name"], finished_pct, limit)


def test_accord_supports_leave_deep_compose_refinements_available() -> None:
    from engine.formulation_intelligence import architecture_bridge as bridge

    interpretation: dict = {"must_avoid": []}
    control = compile_semantic_brief(
        formula_name="Neutral diagnostic",
        request="Green tea and musk",
        interpretation=interpretation,
        max_materials=30,
    )
    # The musk note is built as an accord, and its lead role stays the exact
    # canonical role a v5 refinement strengthens.
    assert any(role.role_id.startswith("facet_skin_musk__accord_") for role in control.roles)
    plan = bridge.derive_architecture_briefs(
        control=control, interpretation=interpretation, max_materials=30,
    )
    assert [b.architecture_plan["option_id"] for b in plan.briefs[1:]] == ["powder_musk", "pear_musk"]
