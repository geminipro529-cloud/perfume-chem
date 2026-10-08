"""Lavender architecture clues stay distinct, traceable and non-authoritative."""

import socket

import pytest

from engine.formulation_intelligence.literature_knowledge import (
    load_knowledge_pack,
    material_knowledge,
    retrieve_formulation_knowledge,
)


@pytest.mark.parametrize(
    ("prompt", "profile"),
    [
        ("Lavender", "lavender_identity"),
        ("Citrus lavender cologne", "lavender_cologne"),
        ("Classical lavender fougere", "lavender_classic_fougere"),
        ("Green barbershop lavender", "lavender_green_fougere"),
        ("Lavender vanilla resin", "lavender_vanillic_amber"),
        ("Soft musky lavender", "lavender_soft_musk"),
        ("Lavender orange blossom", "lavender_orange_blossom"),
        ("Lavender jasmine sandalwood", "lavender_floral_sandalwood"),
        ("Gourmand vanilla lavender", "lavender_gourmand_vanilla"),
        ("Lavender apple", "lavender_fruity_apple"),
        ("Lavender pineapple", "lavender_fruity_pineapple"),
        ("Lavender iris", "lavender_iris"),
        ("Dry incense lavender", "lavender_incense"),
        ("Lavender dark wood oud", "lavender_oud"),
        ("Lavender coffee milk", "lavender_coffee"),
        ("Lavender licorice", "lavender_licorice"),
        ("Spiced lavender vetiver", "lavender_spiced_wood"),
        ("Lavender mineral Ambroxan", "lavender_mineral_ambergris"),
        ("Ginger citrus lavandin", "lavender_ginger"),
    ],
)
def test_lavender_architecture_retrieval(prompt: str, profile: str) -> None:
    result = retrieve_formulation_knowledge(prompt)
    assert profile in result["profile_ids"]
    assert result["state"] == "ADVISORY_KNOWLEDGE_AVAILABLE"
    assert result["network_used"] is False
    assert result["numeric_calibrations_admitted"] == []
    assert all(value is False for value in result["authority"].values())
    assert result["pleasantness"] is None
    assert result["personal_liking"] is None


@pytest.mark.parametrize(
    "prompt",
    [
        "Non-Ambroxan lavender vanilla",
        "Ambroxan-free lavender vanilla",
        "Ambrox-free lavender vanilla",
        "Non-ambroxide lavender vanilla",
        "Traditional lavender vanilla without Ambroxan",
        "Lavender vanilla, avoid Ambroxan and amberwoods",
    ],
)
def test_no_ambrox_wording_preserves_lavender_without_positive_ambrox_profile(
    prompt: str,
) -> None:
    result = retrieve_formulation_knowledge(prompt)
    assert "lavender_identity" in result["profile_ids"]
    assert "lavender_vanillic_amber" in result["profile_ids"]
    assert "lavender_mineral_ambergris" not in result["profile_ids"]


def test_bare_lavender_does_not_require_one_chassis() -> None:
    result = retrieve_formulation_knowledge("Lavender")
    assert result["profile_ids"] == ["lavender_identity"]
    claims = {row["claim_id"]: row for row in result["claims"]}
    assert "lavender_role_not_chassis" in claims
    assert "does not require" in claims["lavender_role_not_chassis"]["statement"]


def test_bare_amber_does_not_become_ambrox_disclosure() -> None:
    result = retrieve_formulation_knowledge("Lavender amber")
    assert "lavender_mineral_ambergris" not in result["profile_ids"]
    assert "lavender_amber_taxonomy" in {row["claim_id"] for row in result["claims"]}


def test_complex_context_preserves_all_required_claim_and_source_links() -> None:
    result = retrieve_formulation_knowledge(
        "Soft feminine lavender with orange blossom, iris, coffee, apple, "
        "vanilla, sandalwood, musk, incense and mineral ambroxan"
    )
    claims = {row["claim_id"]: row for row in result["claims"]}
    sources = {row["source_id"] for row in result["sources"]}
    assert len(claims) > 12  # The former cut-off orphaned profile links.
    for profile in result["profiles"]:
        assert set(profile["claim_ids"]) <= claims.keys()
    for claim in claims.values():
        assert set(claim["source_ids"]) <= sources


def test_natural_types_and_ambrox_grades_are_not_silent_aliases() -> None:
    fine = material_knowledge("Lavandula angustifolia essential oil")
    lavandin = material_knowledge("Lavandin EO")
    spike = material_knowledge("Spike Lavender EO")
    assert fine and lavandin and spike
    assert len({fine["material_id"], lavandin["material_id"], spike["material_id"]}) == 3
    assert material_knowledge("Lavender 40/42") is None
    assert material_knowledge("Ambrox Super")
    assert material_knowledge("Ambrox Super Neo") is None
    assert material_knowledge("Ambrofix") is None


def test_supplier_description_does_not_mean_owned_or_calibrated() -> None:
    binding = material_knowledge("Sclareolate")
    assert binding
    assert "no claim that it is owned" in binding["scope_limit"]
    assert "stock_id" not in binding
    assert "dose" not in binding


def test_official_architecture_cannot_certify_ambrox_absence() -> None:
    result = retrieve_formulation_knowledge("Traditional lavender")
    claim = next(row for row in result["claims"] if row["claim_id"] == "lavender_absence_not_disclosure")
    assert "cannot certify their absence" in claim["statement"]
    assert claim["numeric_calibration"] is False


def test_new_sources_disclose_abstract_only_review_and_no_empirical_admission() -> None:
    sources = {row["source_id"]: row for row in load_knowledge_pack()["sources"]}
    assert "full article not obtained" in sources["lavender_xiao_2017"]["license_note"]
    assert "rate limited" in sources["lavender_guo_2020"]["license_note"]
    assert all(source["empirical_data_admission"] is False for source in sources.values())


def test_lavender_retrieval_is_offline_and_does_not_change_pack(monkeypatch) -> None:
    import engine.formulation_intelligence.literature_knowledge as knowledge

    def forbid_network(*_args, **_kwargs):
        raise AssertionError("Literature retrieval must not use the network")

    original = knowledge.PACK_PATH.read_bytes()
    monkeypatch.setattr(socket, "create_connection", forbid_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbid_network)
    first = retrieve_formulation_knowledge("Lavender orange blossom")
    assert first == retrieve_formulation_knowledge("Lavender orange blossom")
    assert knowledge.PACK_PATH.read_bytes() == original


def test_runtime_context_remains_finite_and_locally_bounded() -> None:
    pack = load_knowledge_pack()
    result = retrieve_formulation_knowledge("Lavender mineral Ambroxan")
    assert len(result["claims"]) <= len(pack["claims"])
    assert len(result["sources"]) <= len(pack["sources"])
