"""A facet's search terms follow the words the brief used, not its neighbours."""

from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief


def _roles(text: str, explicit: tuple[str, ...] = ()) -> dict[str, tuple[str, ...]]:
    brief = compile_semantic_brief(
        formula_name="Role match trial",
        request=text,
        interpretation={"must_avoid": (), "must_preserve": (), "explicit_materials": explicit},
        max_materials=18,
    )
    return {role.role_id: role.query_terms for role in brief.roles}


def test_iris_brief_leads_with_iris_and_drops_violet() -> None:
    terms = _roles("warm amber with an iris heart and a smoky shadow")["facet_iris_violet"]
    assert terms[:2] == ("iris", "orris")
    assert "violet" not in terms
    assert {"irone", "ionone"} <= set(terms)


def test_neroli_brief_leads_with_neroli_and_drops_other_white_flowers() -> None:
    terms = _roles("fresh citrus cologne with neroli and a soft musk")["facet_white_floral"]
    assert terms[:2] == ("neroli", "orange blossom")
    # Hedione is a material name; it must not lead a role the brief named neroli.
    assert not {"jasmine", "tuberose", "gardenia", "hedione"} & set(terms)
    assert "indole" in terms


def test_jasmine_and_neroli_brief_keeps_both_named_flowers() -> None:
    terms = _roles("jasmine and neroli white floral")["facet_white_floral"]
    assert terms[:3] == ("jasmine", "neroli", "orange blossom")
    assert not {"tuberose", "gardenia"} & set(terms)


def test_explicit_patchouli_is_not_filled_twice_and_oakmoss_leads_moss() -> None:
    roles = _roles("rose chypre with patchouli and oakmoss depth", explicit=("patchouli eo",))
    assert roles["explicit_anchor_1"] == ("patchouli eo",)
    assert not any(role_id.startswith("facet_patchouli_earth") for role_id in roles)
    assert roles["facet_moss_chypre"][0] == "oakmoss"
    assert "patchouli" in roles["facet_moss_chypre"][1:]


def test_patchouli_facet_stays_without_an_explicit_anchor() -> None:
    roles = _roles("rose chypre with patchouli and oakmoss depth")
    assert roles["facet_patchouli_earth"][0] == "patchouli"


def test_violet_leaf_and_violet_powder_roles_are_unchanged() -> None:
    leaf = _roles("green violet leaf cologne with a soft musk")
    assert leaf["facet_violet_leaf"] == ("violet leaf absolute", "parmavert", "violet leaf", "leaf")
    powder = _roles("violet powder with soft musk")
    assert powder["facet_violet_powder"] == (
        "violet petal recognizer", "beta ionone", "alpha ionone", "violet", "powder",
    )
    assert powder["facet_powder"] == ("powder", "iris", "ionone", "heliotropin", "musk")
