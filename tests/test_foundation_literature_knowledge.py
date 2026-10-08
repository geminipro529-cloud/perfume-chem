from __future__ import annotations

from engine.formulation_intelligence.literature_knowledge import (
    material_knowledge,
    retrieve_formulation_knowledge,
)


def test_musk_products_keep_distinct_support_roles_without_dose_or_liking():
    helve = material_knowledge("Helvetolide")
    haba = material_knowledge("Habanolide")
    assert helve and haba and helve["material_id"] != haba["material_id"]
    result = retrieve_formulation_knowledge("pear fruity musk with Helvetolide or warm Habanolide")
    assert "musk_fruity_vs_warm_foundation" in result["profile_ids"]
    claim = next(row for row in result["claims"] if row["claim_id"] == "musk_product_role_distinction")
    assert claim["kind"] == "MANUFACTURER_DESCRIPTION"
    assert claim["numeric_calibration"] is False
    assert result["pleasantness"] is None
    assert result["personal_liking"] is None
    assert result["numeric_calibrations_admitted"] == []
    assert material_knowledge("Helvetolide Habanolide replacement") is None


def test_amberwood_is_not_an_ambrox_product_alias_or_a_performance_certificate():
    xtreme = material_knowledge("Amber Xtreme")
    ambrox = material_knowledge("Ambrox Super")
    assert xtreme and ambrox and xtreme["material_id"] != ambrox["material_id"]
    result = retrieve_formulation_knowledge("resinous amber, not a huge woody amber base")
    assert "amber_product_taxonomy_foundation" in result["profile_ids"]
    assert all(flag is False for flag in result["authority"].values())
    assert material_knowledge("Norlimbanol") is None  # not an alias for Amber Xtreme


def test_citrus_grade_clue_does_not_invent_a_curve_or_fcfs_safety_clearance():
    result = retrieve_formulation_knowledge("bergamot FCF and distilled lime citrus")
    assert "citrus_extraction_foundation" in result["profile_ids"]
    claim = next(row for row in result["claims"] if row["claim_id"] == "citrus_process_identity_boundary")
    assert "phototoxicity clearance" in claim["scope_limit"]
    assert claim["numeric_calibration"] is False
    assert result["authority"]["safety_authority"] is False
    assert material_knowledge("Bergamot FCF") is None  # no exact-grade molecular binding


def test_new_primary_sections_are_marked_separately_from_legacy_advisory():
    result = retrieve_formulation_knowledge("citrus fruity musk amber xtreme")
    reviews = {row["source_id"]: row for row in result["source_reviews"]}
    for source in ("helvetolide", "dsm_habanolide_foundation", "iff_amber_xtreme_foundation", "iff_extraction_foundation"):
        assert reviews[source]["review_state"] == "REVIEWED_ADVISORY"
        assert reviews[source]["review_scope"] == "SELECTED_PRIMARY_SECTIONS"
        assert reviews[source]["empirical_data_admission"] is False
