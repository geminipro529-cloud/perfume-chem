from engine.knowledge.perfume_knowledge import resolve_family_key
from engine.knowledge.pyramid_targets import OAV_TARGETS_BY_FAMILY, PYRAMID_RATIOS, get_oav_targets


def test_classical_family_aliases_resolve_to_expected_keys():
    cases = {
        "Eau de Cologne": "citrus_classical",
        "citrus aromatic": "citrus_aromatic",
        "soliflore": "floral_soliflore",
        "floral bouquet": "floral_bouquet",
        "white floral": "floral_white",
        "muguet floral": "floral_muguet",
        "carnation floral": "floral_carnation",
        "powdery floral": "floral_powdery",
        "green floral": "floral_green",
        "classic fougere": "fougere_classical",
        "classic chypre": "chypre_classical",
        "green chypre": "chypre_green",
        "leather chypre": "chypre_leathery",
        "classic amber": "oriental_classical",
        "soft amber": "oriental_soft",
        "floral amber": "oriental_floral",
    }

    for raw, expected in cases.items():
        assert resolve_family_key(raw) == expected


def test_classical_family_keys_have_pyramid_and_oav_targets():
    for key in (
        "citrus_classical",
        "citrus_aromatic",
        "floral_soliflore",
        "floral_bouquet",
        "floral_white",
        "floral_muguet",
        "floral_carnation",
        "floral_powdery",
        "floral_green",
        "floral_aldehydic",
        "fougere_classical",
        "chypre_classical",
        "chypre_floral",
        "chypre_fruity",
        "chypre_green",
        "chypre_leathery",
        "oriental_classical",
        "oriental_soft",
        "oriental_floral",
    ):
        assert key in PYRAMID_RATIOS
        assert key in OAV_TARGETS_BY_FAMILY
        assert get_oav_targets(key)
