"""An opoponax brief leads with the owned Opoponax Resinoid (14 Oct 2026).

Opoponax is a sweet balsamic resin, so it has a note of its own instead of the
smoky incense one. IFRA 51 Category 4 limits it to 0.43% of the finished
product, which kept the 50% stock out of every opoponax role. A stock named for
the identity the brief asks for now stays eligible, and the planner's IFRA cap
holds its dose. These pin the routing and the cap; they make no sensory claim.
"""

from __future__ import annotations

from types import SimpleNamespace

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.research.composition_planner import _ifra_cap_ul

IDEA = "Opoponax on skin with a soft vanilla trail"
LIQUID_TOTAL_UL = 6000


def test_an_opoponax_brief_leads_its_own_note_with_opoponax_resinoid() -> None:
    result = design_formula(idea=IDEA)

    assert "opoponax_balsam" in result["semantic_brief"]["facets"]
    assert "incense_resin" not in result["semantic_brief"]["facets"]
    lead = [row for row in result["initial_formula"]["rows"] if row["slot"] == "facet_opoponax_balsam"]
    assert [row["identity_name"] for row in lead] == ["Opoponax Resinoid"]
    check = result["composition_plan"]["brief_self_check"]["check"]
    assert "opoponax" not in check["uncovered_words"]


def test_the_opoponax_row_stays_inside_its_ifra_cap() -> None:
    result = design_formula(idea=IDEA)

    formula = result.get("optimized_formula") or result["initial_formula"]
    rows = [row for row in formula["rows"] if row["identity_name"] == "Opoponax Resinoid"]
    assert rows
    stock = SimpleNamespace(
        identity_name="Opoponax Resinoid",
        name="Opoponax Resinoid",
        dilution=float(rows[0]["stock_fraction_decimal"]),
    )
    cap = _ifra_cap_ul(SimpleNamespace(stock=stock), LIQUID_TOTAL_UL)
    assert cap is not None
    assert sum(int(row["amount_decimal"]) for row in rows) <= cap
