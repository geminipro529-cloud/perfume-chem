"""Naturals use cited data-spine VPs (diagnosis V3).

A molecule inside a natural evaporates with the same 25 C vapour pressure as
the same molecule dosed on its own when the data spine cites that VP. Uncited
data-spine VPs leave the profile's own table VP in place.
"""

from __future__ import annotations

from engine.data_spine.loader import load_registry
from engine.pipeline.natural_absolute_decomposition import (
    _ABSOLUTE_CONSTITUENTS,
    get_constituents,
)


def _row(material: str, constituent: str) -> tuple:
    return next(row for row in get_constituents(material) if row[0] == constituent)


def test_clove_eo_eugenol_uses_the_registry_vp():
    eugenol = load_registry().get("eugenol")
    assert eugenol is not None and eugenol.vp_25c_pa is not None
    assert eugenol.provenance.get("vp_25c_pa")

    assert _row("Clove EO", "eugenol")[3] == float(eugenol.vp_25c_pa)


def test_uncited_registry_vp_keeps_the_table_vp():
    # Beta pinene's data-spine VP is a manual optimizer override, not a citation.
    pinene = load_registry().get("beta pinene")
    assert pinene is not None and pinene.vp_25c_pa is not None
    assert pinene.provenance.get("vp_25c_pa", "").startswith("manual:")
    table_row = next(
        row for row in _ABSOLUTE_CONSTITUENTS["frankincense eo"] if row[0] == "beta pinene"
    )
    assert table_row[3] != float(pinene.vp_25c_pa)

    assert _row("Frankincense EO", "beta pinene")[3] == table_row[3]


def test_only_the_vp_column_is_substituted():
    table = _ABSOLUTE_CONSTITUENTS["clove eo"]
    effective = get_constituents("Clove EO")
    assert len(effective) == len(table)
    for table_row, row in zip(table, effective):
        assert row[:3] == table_row[:3]
        assert row[4:] == table_row[4:]
    assert sum(row[1] for row in effective) == sum(row[1] for row in table)


# Every substitution where table and registry VP differ by more than 3x,
# as (natural profile, constituent, table VP, registry VP).
_EXPECTED_LARGE_SUBSTITUTIONS = {
    ("cassis base 345b", "citronellol", 7.0, 2.26),
    ("cassis base 345b", "dynascone", 0.001, 1.33322),
    ("ginger eo", "geranyl acetate", 2.0, 6.17),
    ("clary sage eo", "geranyl acetate", 2.0, 6.17),
    ("jasmine sambac", "methyl anthranilate", 0.1, 3.61),
    ("jasmine sambac (10% in dpg)", "methyl anthranilate", 0.1, 3.61),
    ("jasmine sambac", "phenethyl alcohol", 0.12, 11.57),
    ("jasmine sambac (10% in dpg)", "phenethyl alcohol", 0.12, 11.57),
    ("rose essential oil", "phenethyl alcohol", 2.0, 11.57),
    ("rose de mai absolute", "phenylethyl alcohol", 0.12, 11.57),
}


def test_substitutions_beyond_3x_are_the_reviewed_set():
    from engine.pipeline.natural_absolute_decomposition import cited_vp_substitutions

    large = {
        (s.profile_key, s.constituent, s.table_vp_25c_pa, s.registry_vp_25c_pa)
        for s in cited_vp_substitutions()
        if max(s.table_vp_25c_pa, s.registry_vp_25c_pa)
        > 3 * min(s.table_vp_25c_pa, s.registry_vp_25c_pa)
    }
    assert large == _EXPECTED_LARGE_SUBSTITUTIONS
    assert all(s.source for s in cited_vp_substitutions())
