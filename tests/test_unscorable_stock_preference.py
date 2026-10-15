"""The composer prefers a stock the checks can score when two fit a role.

Kenny's frankincense tincture is dosable (15 Oct 2026) but has no odor threshold
of its own, so the checks cannot score it; he chose Olibanum Resinoid winning
the close call instead.
"""

from engine.research.formula_design import design_inventory_formula


def test_incense_brief_takes_olibanum_resinoid_over_the_unscored_tincture() -> None:
    report = design_inventory_formula(idea="an incense and resin", formula_name="Incense", max_materials=60)
    materials = [row["material"] for row in report["optimized_formula"]["rows"]]

    assert "Olibanum Resinoid" in materials
    assert "Oman Frankincense Ethanol Tincture" not in materials


def test_a_named_tincture_is_still_used_when_the_brief_asks_for_it() -> None:
    report = design_inventory_formula(
        idea="an incense and resin with Oman Frankincense Ethanol Tincture",
        formula_name="Incense",
        max_materials=60,
    )
    materials = [row["material"] for row in report["optimized_formula"]["rows"]]

    assert "Oman Frankincense Ethanol Tincture" in materials
