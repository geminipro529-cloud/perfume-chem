from __future__ import annotations

import pytest

from engine.formulation_intelligence.literature_knowledge import (
    material_knowledge,
    retrieve_formulation_knowledge,
)


@pytest.mark.parametrize("prompt,profile", [
    ("resinous amber with benzoin and labdanum", "resin_amber_foundation"),
    ("Exaltolide for soft musk", "musk_roundness_foundation"),
    ("bergamot FCF grade", "bergamot_grade_foundation"),
    ("transparent jasmine supported by Hedione", "transparent_floral_foundation"),
    ("warm sandalwood with Sandalore", "sandalwood_foundation"),
    ("fig leaf and cut grass", "green_leaf_foundation"),
    ("fruity chypre", "chypre_foundation"),
    ("soft suede, no smoke", "leather_foundation"),
    ("dry coffee, avoid added sugar", "gourmand_foundation"),
    ("pear apple lychee with freesia", "orchard_reference_foundation"),
])
def test_new_cards_are_advisory_source_bounded_and_not_a_numeric_endpoint(prompt, profile):
    result = retrieve_formulation_knowledge(prompt)
    assert profile in result["profile_ids"]
    assert result["numeric_calibrations_admitted"] == []
    assert result["pleasantness"] is result["personal_liking"] is None
    assert all(value is False for value in result["authority"].values())
    assert all(row["numeric_calibration"] is False for row in result["claims"])


@pytest.mark.parametrize("prompt,forbidden", [
    ("iris, no jasmine", "transparent_floral_foundation"),
    ("dry cedar, avoid creamy sandalwood", "sandalwood_foundation"),
    ("green jasmine", "green_leaf_foundation"),
    ("earthy patchouli soliflore", "chypre_foundation"),
    ("incense, no leather", "leather_foundation"),
    ("rich and smooth", "gourmand_foundation"),
    ("lychee, avoid rose", "lavender_floral_sandalwood"),
])
def test_generic_adjective_or_avoided_identity_does_not_activate_card(prompt, forbidden):
    assert forbidden not in retrieve_formulation_knowledge(prompt)["profile_ids"]


@pytest.mark.parametrize("material", ["Exaltolide", "Hedione", "Sandalore", "Stemone", "Safraleine"])
def test_named_materials_are_not_cross_grade_aliases(material):
    assert material_knowledge(material)
    assert material_knowledge(material + " replacement") is None


def test_new_sources_have_exact_bounded_review_receipts():
    result = retrieve_formulation_knowledge("pear apple lychee freesia sandalwood leather tonka jasmine Stemone Exaltolide bergamot resinous amber")
    rows = {row["source_id"]: row for row in result["source_reviews"]}
    for source in ("dsm_hedione_foundation", "givaudan_sandalore_foundation", "givaudan_stemone_foundation", "givaudan_safraleine_foundation", "iff_tonka_foundation", "guerlain_mitsouko_edp_foundation", "guerlain_pera_granita_edt"):
        # Chypre needs its own recognizer, not an incidental wood/fruit word.
        if source == "guerlain_mitsouko_edp_foundation":
            chypre = retrieve_formulation_knowledge("chypre")
            rows.update({row["source_id"]: row for row in chypre["source_reviews"]})
        assert rows[source]["review_scope"] == "SELECTED_PRIMARY_SECTIONS"
        assert rows[source]["review_state"] == "REVIEWED_ADVISORY"
        assert rows[source]["empirical_data_admission"] is False


def test_ambrettolide_named_grade_does_not_bind_any_generic_owned_bottle():
    assert material_knowledge("IFF Ambrettolide")["material_id"] == "iff_ambrettolide"
    assert material_knowledge("Ambrettolide") is None
    assert material_knowledge("Ambrette Oil") is None
    result = retrieve_formulation_knowledge("soft musk with Exaltolide")
    assert any(row["claim_id"] == "ambrettolide_named_product_boundary" for row in result["claims"])
