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
    ("cassis base 345b", "dynascone", 0.001, 2.28),
    ("jasmine sambac", "methyl anthranilate", 0.1, 3.61),
    ("jasmine sambac (10% in dpg)", "methyl anthranilate", 0.1, 3.61),
    ("jasmine sambac", "phenethyl alcohol", 0.12, 11.57),
    ("jasmine sambac (10% in dpg)", "phenethyl alcohol", 0.12, 11.57),
    # 2026-10-28: Veloutone's registry VP is ECHA's OECD 104 9.2 Pa at 25 C (was the 2.17 Pa
    # US EPA estimate quoted by RIFM 2017), replacing the table's 0.1.
    ("cassis base 345b", "veloutone", 0.1, 9.2),
    # 2026-10-23 third data pass: registry VPs now sourced, replacing table values.
    # Rose oxide: RIFM measured 0.77 hPa at 25 C (RIFM 2013a).
    ("cassis base 345b", "rose oxide", 15.0, 77.0),
    # Citral: RIFM-quoted EPI Suite 0.0913 mm Hg at 25 C (FMA 0.07 mm Hg at 20 C).
    ("cedrat fcf oil sicilian", "citral", 3.0, 14.1),
    ("cedrat fcf sicilian", "citral", 3.0, 14.1),
    # Evernyl: TGSC estimate 0.00001 mm Hg at 25 C for the solid (mp 143 C).
    ("oakmoss absolute", "evernyl", 0.05, 0.00227),
    ("oakmoss absolute (10% in dpg)", "evernyl", 0.05, 0.00227),
    # p-Cresyl methyl ether: RIFM-quoted US EPA estimate 1.2 mm Hg at 25 C
    # (FMA 1.3 mm Hg at 20 C).
    # 2026-10-30: Kenny's ylang oils take sourced grade profiles that reuse the row.
    ("ylang ylang oil comoros efsa 2022 five-batch profile", "p-cresyl methyl ether", 30.0, 243.0),
    ("ylang ylang oil grade iii benveniste azzo 1992 profile", "p-cresyl methyl ether", 30.0, 243.0),
    ("ylang ylang oil comoros efsa 2022 five-batch profile", "farnesol", 0.05, 0.005253),
    ("ylang ylang eo (extra grade)", "p-cresyl methyl ether", 30.0, 243.0),
    # 2026-10-25 physics batch 1: the frangipani profile reuses the module's citral
    # and citronellol rows, so the cited citral (above) and citronellol (ECHA
    # 2.26 Pa) registry VPs replace their table values.
    ("frangipani absolute perfumersworld 8on00534 declaration profile", "citral", 3.0, 14.1),
    ("frangipani absolute perfumersworld 8on00534 declaration profile", "citronellol", 7.0, 2.26),
    # 2026-10-25 physics batch 2: the terpeneless lemon profile reuses the citral row,
    # so the cited citral registry VP replaces its table value.
    ("lemon oil terpeneless perfumersworld 7cc24027 bp citral midpoint profile", "citral", 3.0, 14.1),
    # 2026-10-25 literature batch: registry VPs re-sourced from primary documents.
    # Citral: RIFM's FMA figure (0.07 mm Hg at 20 C) converted to 25 C; p-cresyl methyl
    # ether: FMA 1.3 mm Hg at 20 C converted; Evernyl: ECHA gas-saturation 0.002 Pa at
    # 24 C; Dynascone: Firmenich's 1.44 Pa at 20 C. Geranyl acetate's ECHA key value
    # (2.06 Pa) is now within 3x of the table's 2.0.
    # Vanillin: Yaws' 0.0157 Pa at 25 C (via HSDB).
    ("benzoin siam resinoid", "vanillin", 0.005, 0.01573),
    ("benzoin sumatra resinoid", "vanillin", 0.005, 0.01573),
    ("hay absolute perfumersworld 8ny00523 allergen declaration profile", "vanillin", 0.005, 0.01573),
    ("styrax tonkinensis resin ethanol tincture generic profile", "vanillin", 0.005, 0.01573),
    ("styrax tonkinensis resin jecfa 2011 mean profile", "vanillin", 0.005, 0.01573),
    ("tonka bean absolute", "vanillin", 0.005, 0.01573),
    ("vanilla absolute", "vanillin", 0.005, 0.01573),
    # Triplal: RIFM's 20 C figure converted; cinnamyl alcohol: Carl Roth SDS 3 Pa at 25 C.
    ("cassis base 345b", "triplal", 0.5, 52.5),
    ("liquidambar orientalis resin ethanol tincture generic profile", "cinnamyl alcohol", 0.03, 3.0),
    # Osmanthus ketones and lactone: alpha-ionone (Takasago, equal to EPI), dihydro-beta-
    # ionone (RIFM measured 3.8 Pa at 25 C), gamma-decalactone (FMA via RIFM, converted).
    ("osmanthus absolute", "alpha ionone", 1.0, 3.62),
    ("osmanthus absolute", "dihydro beta ionone", 0.5, 3.8),
    ("osmanthus absolute", "gamma decalactone", 0.5, 1.7),
    ("osmanthus absolute (volume grade)", "alpha ionone", 1.0, 3.62),
    ("osmanthus absolute (volume grade)", "dihydro beta ionone", 0.5, 3.8),
    ("osmanthus absolute (volume grade)", "gamma decalactone", 0.5, 1.7),
    # 2026-10-25 naturals batch: the sourced lime distilled, cabreuva and rose oil
    # profiles reuse the module's citral and rose oxide rows, so the cited citral
    # (RIFM) and rose oxide (RIFM measured) registry VPs replace their table values.
    # The rose essential oil and rose de mai phenylethyl alcohol rows now carry the
    # cited 11.57 Pa themselves and left this set.
    ("lime distilled eo", "citral", 3.0, 14.1),
    ("myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile", "citral", 3.0, 14.1),
    ("rose essential oil", "rose oxide", 15.0, 77.0),
    # 2026-10-27 MySkinRecipes batch: farnesol's registry VP is now RIFM's EPI Suite v4.11
    # estimate (3.94e-5 mm Hg at 25 C), replacing an unsourced 0.08 Pa; four profiles
    # reuse the module's farnesol row (table 0.05 Pa).
    ("tobacco absolute", "farnesol", 0.05, 0.005253),
    ("rose essential oil", "farnesol", 0.05, 0.005253),
    ("myrocarpus cabreuva oil perfumersworld 7lw00863 ifra declaration profile", "farnesol", 0.05, 0.005253),
    ("abelmoschus moschatus seed oil arokiyaraj 2015 gc-ms profile", "farnesol", 0.05, 0.005253),
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


def test_metadata_marks_rows_whose_vp_now_comes_from_the_data_spine():
    from engine.pipeline import natural_absolute_decomposition as nad

    marked = 0
    for substitution in nad.cited_vp_substitutions():
        metadata = nad.get_composite_metadata(substitution.profile_key)
        row = metadata.input_authority.get(substitution.constituent) if metadata else None
        if isinstance(row, dict):
            assert row["vp_status"] == "CITED_DATA_SPINE_VP"
            assert row["vp_source"] == substitution.source
            marked += 1
    assert marked >= 1
