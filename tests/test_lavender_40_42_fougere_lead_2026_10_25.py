"""Fougère and barbershop briefs lead with Lavender 40/42 (Kenny, 25 Oct 2026, stock thread).

Asked "Make the composer pick Lavender 40/42 for fougère and barbershop briefs?", he chose
"Yes, fougère only": those briefs lead with the 40/42 grade (lavandin camphor and cineole),
while soft or floral lavender briefs, and a brief that names the BONTAUX oil, keep BONTAUX.
These pin which lavender stock leads; they make no sensory claim.
"""
from __future__ import annotations

import pytest

from engine.formulation_intelligence import note_accord_specs
from engine.formulation_intelligence.formula_design_runtime import design_formula

GRADE = "Lavender 40/42, Aroma&More"
BONTAUX = "Lavender EO (BONTAUX SAS)"


def _lavender_rows(idea: str) -> list[str]:
    rows = design_formula(idea=idea)["initial_formula"]["rows"]
    return [row["identity_name"] for row in rows if "lavend" in row["identity_name"].casefold()]


def test_the_fougere_rule_names_one_of_the_lavender_lead_stocks():
    spec = note_accord_specs.accord_spec_for("aromatic_lavender")
    assert spec.lead_stocks[0].name == BONTAUX
    names = {stock.name for stock in spec.lead_stocks}
    for words, name in spec.lead_first_when:
        assert name in names
        assert {"fougere", "barbershop"} <= set(words)


@pytest.mark.parametrize(
    "idea",
    ["a barbershop lavender with tonka", "an aromatic fougere"],
)
def test_fougere_and_barbershop_briefs_lead_with_the_40_42_grade(idea):
    assert _lavender_rows(idea) == [GRADE]


@pytest.mark.parametrize(
    "idea",
    ["a fine soft floral lavender for women", "a fougere with Bontaux lavender"],
)
def test_soft_lavender_and_a_named_bontaux_keep_bontaux(idea):
    assert _lavender_rows(idea) == [BONTAUX]
