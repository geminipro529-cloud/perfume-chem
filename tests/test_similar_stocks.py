"""Similar stocks and the shelf map (plan item F6): compared by written profile,
grouped by material, always labelled "similar, not the same"."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from engine.formulation_intelligence.similar_stocks import LABEL, shelf_map, similar_stocks


@dataclass(frozen=True)
class Cap:
    stock_id: str
    identity_name: str
    character: tuple[tuple[str, float], ...]
    descriptor_vocabulary: tuple[str, ...] = ()
    stock_label: str = ""
    note: str = "base"
    profile_source: str = "DECLARED_MATERIAL_PROFILE"
    design_ready: bool = True


WOODS = (
    Cap("s-iso", "Iso E Super", (("woody", 8), ("transparency", 7), ("radiance", 5)), ("woody", "velvet"), "Iso E Super neat"),
    Cap("s-kep", "Kephalis", (("woody", 8), ("transparent", 6), ("warmth", 5)), ("woody", "amber"), "Kephalis neat"),
    Cap("s-ced", "Cedarwood EO", (("woody", 9), ("smoky", 3)), ("woody", "pencil"), "Cedarwood EO neat"),
    Cap("s-ced2", "Cedarwood EO (China; species unspecified)", (("woody", 9), ("smoky", 3)), ("woody",), "Cedarwood EO 10% in DPG",
        design_ready=False),
    Cap("s-hed", "Hedione", (("floral", 7), ("freshness", 6), ("radiance", 6)), ("jasmine", "fresh"), "Hedione neat"),
    Cap("s-hedhc", "Hedione HC", (("floral", 7), ("freshness", 6), ("radiance", 6)), ("jasmine", "fresh"), "Hedione HC neat"),
    Cap("s-van", "Vanillin", (("sweetness", 9), ("creamy", 6), ("warmth", 6)), ("vanilla",), "Vanillin crystals"),
    Cap("s-iso10", "Iso E Super", (("woody", 8), ("transparency", 7), ("radiance", 5)), ("woody", "velvet"), "Iso E Super 10% in DPG"),
    Cap("s-none", "Mystery Base", (), (), "Mystery Base neat", profile_source="HEURISTIC_CATEGORY_PROXY"),
)


def test_closest_owned_materials_come_with_their_stocks_the_stocks_other_bottles_first_and_the_label():
    answer = similar_stocks("s-iso", capabilities=WOODS)

    assert answer["label"] == LABEL == "similar, not the same"
    assert [line["stock_label"] for line in answer["same_material"]] == ["Iso E Super 10% in DPG"]
    names = [item["identity_name"] for item in answer["similar"]]
    assert names[:2] == ["Kephalis", "Cedarwood EO"]
    assert "Hedione" not in names and "Vanillin" not in names  # nothing alike enough
    kephalis = answer["similar"][0]
    # "transparent" in one profile and "transparency" in the other are one facet.
    assert kephalis["shares"] == ["woody", "transparent"]
    assert kephalis["differs"] == ["less radiant", "more warm"]  # biggest gap first, then by facet
    # One material, two stocks: one entry that lists both, the ready stock first.
    cedar = answer["similar"][1]
    assert [line["stock_id"] for line in cedar["stocks"]] == ["s-ced", "s-ced2"]
    assert (answer["inventory_modified"], answer["formula_modified"]) == (False, False)


def test_a_material_name_finds_its_stock_and_a_stock_without_a_profile_says_so():
    by_name = similar_stocks(material="hedione", capabilities=WOODS)
    blank = similar_stocks("s-none", capabilities=WOODS)

    assert by_name["stock"]["stock_id"] == "s-hed"
    assert by_name["similar"][0]["identity_name"] == "Hedione HC"
    assert by_name["similar"][0]["closeness"] == "close"
    assert blank["no_profile"] is True and blank["similar"] == []
    assert blank["stock"]["profile_from_category"] is True
    with pytest.raises(LookupError):
        similar_stocks("s-gone", capabilities=WOODS)
    with pytest.raises(LookupError):
        similar_stocks(material="Unobtainium", capabilities=WOODS)


def test_the_shelf_map_places_one_dot_per_material_and_names_pairs_written_alike_once():
    answer = shelf_map(capabilities=WOODS)

    names = [dot["identity_name"] for dot in answer["stocks"]]
    assert sorted(names) == ["Cedarwood EO", "Hedione", "Hedione HC", "Iso E Super", "Kephalis", "Vanillin"]
    assert all(0 <= dot["x"] <= 1 and 0 <= dot["y"] <= 1 for dot in answer["stocks"])
    iso = next(dot for dot in answer["stocks"] if dot["identity_name"] == "Iso E Super")
    assert [line["stock_id"] for line in iso["stocks"]] == ["s-iso10", "s-iso"]  # by label
    assert (iso["leads_with"], iso["leads_with_word"]) == ("woody", "woody")
    assert answer["unplaced"] == ["Mystery Base"]
    # Each axis runs between two facets, named as words.
    assert set(answer["axes"]) == {"x", "y"}
    assert all(end in {"woody", "transparent", "radiant", "warm", "smoky", "floral", "fresh", "sweet", "creamy"}
               for axis in answer["axes"].values() for end in axis.values())
    assert [(pair["a"], pair["b"]) for pair in answer["written_alike"]] == [("Hedione", "Hedione HC")]
    facets = {facet["facet"]: facet for facet in answer["facets"]}
    assert facets["woody"]["leaders"] == ["Cedarwood EO", "Iso E Super", "Kephalis"]
    assert (facets["sweetness"]["word"], facets["sweetness"]["count"]) == ("sweet", 1)
    assert facets["powdery"]["count"] == 0
    assert answer["label"] == LABEL and answer["inventory_modified"] is False


def test_the_real_shelf_gives_owned_neighbours_and_a_map():
    from engine.formulation_intelligence.similar_stocks import _owned_capabilities

    owned = _owned_capabilities()
    if not owned:
        pytest.skip("no owned stocks in this checkout")
    first = next(capability for capability in owned if capability.character)
    answer = similar_stocks(first.stock_id, capabilities=owned)
    owned_ids = {capability.stock_id for capability in owned}
    assert all(line["stock_id"] in owned_ids for item in answer["similar"] for line in item["stocks"])
    shelf = shelf_map(capabilities=owned)
    assert shelf["stocks"] and len({dot["identity_name"] for dot in shelf["stocks"]}) == len(shelf["stocks"])
    pairs = [frozenset((pair["a"], pair["b"])) for pair in shelf["written_alike"]]
    assert len(pairs) == len(set(pairs))
