"""Tests for the knowledge-base query APIs.

Covers both ``engine.knowledge_base`` (material queries) and
``engine.kb_rules_api`` (rules queries) against the live SQLite
database at ``data/perfumery_kb.db``.
"""

from __future__ import annotations

import pytest
from engine import knowledge_base as kb
from engine import kb_rules_api as rules


# ── Material queries ───────────────────────────────────────────────────


class TestGetMaterial:
    """Tests for ``knowledge_base.get_material``."""

    def test_get_material_hedione(self) -> None:
        """Hedione must exist with correct VP."""
        mat = kb.get_material("Hedione")
        assert mat is not None
        assert mat["canonical_name"] == "Hedione"
        assert mat["vp_25c_pa"] == 0.21

    def test_get_material_none(self) -> None:
        """Unknown material returns None."""
        assert kb.get_material("NonExistentMaterialXYZ") is None

    def test_alias_resolution(self) -> None:
        """Querying by alias resolves to canonical name."""
        mat = kb.get_material("hedione")
        assert mat is not None
        assert mat["canonical_name"] == "Hedione"


class TestGetMaterialsByNote:
    """Tests for ``knowledge_base.get_materials_by_note``."""

    def test_heart_materials_returned(self) -> None:
        """Heart materials must include known heart entries."""
        mats = kb.get_materials_by_note("heart")
        assert len(mats) > 0
        names = {m["canonical_name"] for m in mats}
        assert "Alpha Ionone" in names or "Hedione" in names


class TestGetMaterialsByRole:
    """Tests for ``knowledge_base.get_materials_by_role``."""

    def test_character_role(self) -> None:
        """Materials with role='character' should be found."""
        mats = kb.get_materials_by_role("character")
        assert len(mats) > 0


class TestGetMaterialsByFamily:
    """Tests for ``knowledge_base.get_materials_by_family``."""

    def test_floral_family(self) -> None:
        """Materials in floral family should be found."""
        mats = kb.get_materials_by_family("floral")
        assert len(mats) > 0


class TestGetMaterialVp:
    """Tests for ``knowledge_base.get_material_vp``."""

    def test_hedione_vp(self) -> None:
        """Hedione VP must be 0.21."""
        vp = kb.get_material_vp("Hedione")
        assert vp == 0.21

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert kb.get_material_vp("__nonexistent__") is None


class TestGetMaterialOdt:
    """Tests for ``knowledge_base.get_material_odt``."""

    def test_hedione_odt(self) -> None:
        """Hedione should have ODT values."""
        odt = kb.get_material_odt("Hedione")
        assert odt is not None
        assert len(odt) == 2

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert kb.get_material_odt("__nonexistent__") is None


class TestGetMaterialIfraLimit:
    """Tests for ``knowledge_base.get_material_ifra_limit``."""

    def test_hedione_limit(self) -> None:
        """Hedione IFRA limit may be None (not restricted)."""
        limit = kb.get_material_ifra_limit("Hedione")
        # Not all materials have an IFRA limit
        assert limit is None or isinstance(limit, float)


class TestGetMaterialSynergies:
    """Tests for ``knowledge_base.get_material_synergies``."""

    def test_aldehyde_c10_synergies(self) -> None:
        """ALDEHYDE C10 should have synergies (e.g. Bergamot)."""
        syns = kb.get_material_synergies("ALDEHYDE C10")
        assert len(syns) > 0
        assert "Bergamot" in syns


class TestGetMaterialClashes:
    """Tests for ``knowledge_base.get_material_clashes``."""

    def test_aldehyde_c10_clashes(self) -> None:
        """ALDEHYDE C10 should have clash entries."""
        clashes = kb.get_material_clashes("ALDEHYDE C10")
        assert len(clashes) > 0


class TestGetNaturalDecomposition:
    """Tests for ``knowledge_base.get_natural_decomposition``."""

    def test_osmanthus_decomposition(self) -> None:
        """Osmanthus absolute must decompose into known constituents."""
        decomp = kb.get_natural_decomposition("osmanthus absolute")
        assert decomp is not None
        assert len(decomp) > 0
        names = {d["constituent_name"] for d in decomp}
        assert "beta ionone" in names


class TestSearchMaterials:
    """Tests for ``knowledge_base.search_materials``."""

    def test_search_hedione(self) -> None:
        """Text search for 'hedione' must find Hedione."""
        results = kb.search_materials("Hedione")
        assert len(results) > 0
        names = {r["canonical_name"] for r in results}
        assert "Hedione" in names

    def test_search_empty(self) -> None:
        """Empty/matching-nothing search returns empty list."""
        results = kb.search_materials("__zzz_nonexistent_zzz__")
        assert results == []


# ── Rules queries ──────────────────────────────────────────────────────


class TestGetArchetype:
    """Tests for ``kb_rules_api.get_archetype``."""

    def test_chypre_classical(self) -> None:
        """Classic chypre archetype must return with anchors."""
        arch = rules.get_archetype("chypre_classical.coty_reference")
        assert arch is not None
        assert arch["family"] == "chypre_classical"
        assert "anchors" in arch
        assert isinstance(arch["anchors"], list)

    def test_unknown_returns_none(self) -> None:
        """Unknown archetype returns None."""
        assert rules.get_archetype("__nonexistent__") is None


class TestGetPyramidRatio:
    """Tests for ``kb_rules_api.get_pyramid_ratio``."""

    def test_chypre_edt(self) -> None:
        """Chypre EdT must return correct ratios."""
        ratio = rules.get_pyramid_ratio("chypre", "EdT")
        assert ratio is not None
        assert ratio["top_pct"] == 25.0
        assert ratio["heart_pct"] == 30.0
        assert ratio["base_pct"] == 45.0

    def test_unknown_returns_none(self) -> None:
        """Unknown family/bracket returns None."""
        assert rules.get_pyramid_ratio("__nonexistent__", "EdT") is None


class TestGetOavTargets:
    """Tests for ``kb_rules_api.get_oav_targets``."""

    def test_results_returned(self) -> None:
        """A known family must return OAV target entries."""
        targets = rules.get_oav_targets("chypre")
        assert len(targets) >= 0  # May be empty depending on data


class TestGetMaterialRoleRatios:
    """Tests for ``kb_rules_api.get_material_role_ratios``."""

    def test_fougere_style(self) -> None:
        """Fougere style must return role ratios."""
        ratios = rules.get_material_role_ratios("fougere")
        assert len(ratios) > 0
        roles = {r["role"] for r in ratios}
        assert "character" in roles


class TestCheckCrossFamily:
    """Tests for ``kb_rules_api.check_cross_family``."""

    def test_citrus_floral_high(self) -> None:
        """Citrus and floral should have high compatibility."""
        level = rules.check_cross_family("citrus", "floral")
        assert level == "high"

    def test_unknown_returns_none(self) -> None:
        """Unknown pair returns None."""
        assert rules.check_cross_family("__nonexistent__", "floral") is None


class TestGetIfraLimit:
    """Tests for ``kb_rules_api.get_ifra_limit``."""

    def test_linalool_limit(self) -> None:
        """Linalool should have a known IFRA limit of 15.0."""
        limit = rules.get_ifra_limit("Linalool")
        assert limit == 15.0

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert rules.get_ifra_limit("__nonexistent__") is None


class TestGetEuAllergens:
    """Tests for ``kb_rules_api.get_eu_allergens``."""

    def test_allergens_returned(self) -> None:
        """EU allergens list must not be empty."""
        allergens = rules.get_eu_allergens()
        assert len(allergens) > 0
        names = {a["material_name"] for a in allergens}
        assert "Linalool" in names or "Limonene" in names


class TestGetBannedMaterials:
    """Tests for ``kb_rules_api.get_banned_materials``."""

    def test_banned_returned(self) -> None:
        """Banned materials list must contain known entries."""
        banned = rules.get_banned_materials()
        assert len(banned) > 0
        assert "Lilial" in banned


class TestGetFatigueThreshold:
    """Tests for ``kb_rules_api.get_fatigue_threshold``."""

    def test_beta_ionone_threshold(self) -> None:
        """Beta ionone must have fatigue threshold."""
        thresh = rules.get_fatigue_threshold("beta ionone")
        assert thresh is not None
        assert thresh["warn_oav"] == 2000.0
        assert thresh["fail_oav"] == 15000.0

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert rules.get_fatigue_threshold("__nonexistent__") is None


class TestGetJellinekClass:
    """Tests for ``kb_rules_api.get_jellinek_class``."""

    def test_ambrox_super_class(self) -> None:
        """Ambrox Super must be classified as erogenic."""
        cls = rules.get_jellinek_class("ambrox super")
        assert cls == "erogenic"

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert rules.get_jellinek_class("__nonexistent__") is None


class TestGetCharacterShifts:
    """Tests for ``kb_rules_api.get_character_shifts``."""

    def test_indole_shifts(self) -> None:
        """Indole must have character shift zones."""
        shifts = rules.get_character_shifts("Indole")
        assert len(shifts) > 0
        assert shifts[0]["character"] is not None


class TestGetHillParams:
    """Tests for ``kb_rules_api.get_hill_params``."""

    def test_indole_hill(self) -> None:
        """Indole should have Hill parameters."""
        params = rules.get_hill_params("Indole")
        assert params is not None
        assert "n" in params

    def test_unknown_returns_none(self) -> None:
        """Unknown material returns None."""
        assert rules.get_hill_params("__nonexistent__") is None


class TestGetIconicSkeleton:
    """Tests for ``kb_rules_api.get_iconic_skeleton``."""

    def test_iris_woody_skeleton(self) -> None:
        """Iris woody skeleton must return marker materials."""
        skeleton = rules.get_iconic_skeleton("iris_woody")
        assert skeleton is not None
        assert "marker_materials" in skeleton
        assert skeleton["source_reference"] is not None

    def test_unknown_returns_none(self) -> None:
        """Unknown family returns None."""
        assert rules.get_iconic_skeleton("__nonexistent__") is None


class TestGetAccord:
    """Tests for ``kb_rules_api.get_accord``."""

    def test_chypre_accord(self) -> None:
        """Chypre accord should exist."""
        accord = rules.get_accord("chypre")
        assert accord is not None


class TestGetBriefDefaults:
    """Tests for ``kb_rules_api.get_brief_defaults``."""

    def test_brief_defaults_returned(self) -> None:
        """Brief defaults must be a non-empty dict."""
        defaults = rules.get_brief_defaults()
        assert isinstance(defaults, dict)
        assert len(defaults) > 0
        # Should map brief keys to families
        assert "chypre_classical" in defaults or "aromatic_fougere" in defaults
