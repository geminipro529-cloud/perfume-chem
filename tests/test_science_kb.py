"""Tests for the science knowledge base population and query API
(:mod:`engine.science_kb`).

Covers all 10 science domains with data-integrity checks and API
round-trips against a fresh temporary SQLite database.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from engine import science_kb as skb

# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_path() -> str:
    """Create a fresh science-KB database for testing."""
    tmp = tempfile.mktemp(suffix=".db", prefix="science_kb_test_")
    result = skb.populate_science_kb(tmp)
    yield result
    try:
        os.remove(result)
    except OSError:
        pass


@pytest.fixture(scope="module")
def conn(db_path: str) -> sqlite3.Connection:
    """Provide a raw connection to the test database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ── Domain 1: OR biophysics ───────────────────────────────────────────


class TestOrBiophysics:
    """``or_biophysics`` table and query."""

    def test_or_biophysics_populated(self, conn: sqlite3.Connection) -> None:
        """Verify >5 entries in or_biophysics table."""
        count = conn.execute("SELECT COUNT(*) FROM or_biophysics").fetchone()[0]
        assert count >= 5, f"Expected >=5 OR biophysics entries, got {count}"

    def test_vibration_theory_exists(self, conn: sqlite3.Connection) -> None:
        """Vibration theory entry must exist."""
        row = conn.execute(
            "SELECT finding FROM or_biophysics WHERE topic = 'vibration_theory'"
        ).fetchone()
        assert row is not None
        assert "electron tunneling" in row[0].lower()

    def test_cryo_em_2023(self, conn: sqlite3.Connection) -> None:
        """Cryo-EM entry must reference Billesbølle et al 2023."""
        row = conn.execute(
            "SELECT citation FROM or_biophysics WHERE topic = 'cryo_em'"
        ).fetchone()
        assert row is not None
        assert "Billesbølle" in row[0]

    def test_query_by_topic(self) -> None:
        """``get_or_biophysics('cryo_em')`` returns the cryo-EM entry."""
        results = skb.get_or_biophysics("cryo_em")
        assert len(results) == 1
        assert results[0]["topic"] == "cryo_em"

    def test_query_all(self) -> None:
        """``get_or_biophysics()`` returns all entries."""
        results = skb.get_or_biophysics()
        assert len(results) >= 5


# ── Specific anosmia ───────────────────────────────────────────────────


class TestMaterialAnosmia:
    """``material_anosmia`` table and query."""

    def test_anosmia_galaxolide(self, conn: sqlite3.Connection) -> None:
        """Galaxolide anosmia rate must be in range 30-35%."""
        rows = conn.execute(
            "SELECT anosmia_pct FROM material_anosmia WHERE material_name LIKE '%Galaxolide%'"
        ).fetchall()
        assert len(rows) > 0
        pct = rows[0][0]
        assert 30 <= pct <= 35, f"Galaxolide anosmia {pct}% outside 30-35%"

    def test_androstenone_receptor(self, conn: sqlite3.Connection) -> None:
        """Androstenone must map to OR7D4."""
        row = conn.execute(
            "SELECT receptor FROM material_anosmia WHERE material_name LIKE '%Androstenone%'"
        ).fetchone()
        assert row is not None
        assert row[0] == "OR7D4"

    def test_query_api(self) -> None:
        """``get_anosmia_rate('Galaxolide')`` returns correct data."""
        result = skb.get_anosmia_rate("Galaxolide")
        assert result is not None
        assert 30 <= result["anosmia_pct"] <= 35
        assert result["receptor"] == "OR5AN1"

    def test_query_unknown(self) -> None:
        """``get_anosmia_rate('Unknown__')`` returns None."""
        assert skb.get_anosmia_rate("__UnknownMaterial__") is None


# ── Domain 2: Evaporation kinetics ─────────────────────────────────────


class TestEvaporationModel:
    """``evaporation_model`` table and query."""

    def test_evaporation_model_fixative(self, conn: sqlite3.Connection) -> None:
        """Fixative effect entry must exist."""
        row = conn.execute(
            "SELECT value FROM evaporation_model WHERE parameter = 'fixative_effect'"
        ).fetchone()
        assert row is not None
        assert "biexponential" in row[0]

    def test_evaporation_has_k1(self, conn: sqlite3.Connection) -> None:
        """k1_evaporation parameter must exist."""
        count = conn.execute(
            "SELECT COUNT(*) FROM evaporation_model WHERE parameter = 'k1_evaporation'"
        ).fetchone()[0]
        assert count == 1

    def test_query_by_parameter(self) -> None:
        """``get_evaporation_model('fixative_effect')`` returns entry."""
        results = skb.get_evaporation_model("fixative_effect")
        assert len(results) == 1
        assert results[0]["parameter"] == "fixative_effect"

    def test_query_all(self) -> None:
        """``get_evaporation_model()`` returns all entries."""
        results = skb.get_evaporation_model()
        assert len(results) >= 5


# ── Domain 3: UNIFAC groups ────────────────────────────────────────────


class TestUnifacGroups:
    """``unifac_groups`` table and query."""

    def test_unifac_groups_populated(self, conn: sqlite3.Connection) -> None:
        """UNIFAC groups must have at least 10 entries."""
        count = conn.execute("SELECT COUNT(*) FROM unifac_groups").fetchone()[0]
        assert count >= 10, f"Expected >=10 UNIFAC groups, got {count}"

    def test_unifac_oh_exists(self, conn: sqlite3.Connection) -> None:
        """OH group must exist with contribution_vp ~3.5."""
        row = conn.execute(
            "SELECT contribution_vp FROM unifac_groups WHERE group_name = 'OH'"
        ).fetchone()
        assert row is not None
        assert row[0] == 3.5

    def test_get_unifac_groups(self) -> None:
        """``get_unifac_groups()`` returns all groups."""
        results = skb.get_unifac_groups()
        assert len(results) >= 10


# ── Domain 4: Skin chemistry ───────────────────────────────────────────


class TestSkinChemistry:
    """``skin_chemistry`` table and query."""

    def test_skin_chemistry_sebum(self, conn: sqlite3.Connection) -> None:
        """Sebum composition entries must exist."""
        count = conn.execute(
            "SELECT COUNT(*) FROM skin_chemistry WHERE topic = 'sebum_composition'"
        ).fetchone()[0]
        assert count >= 4, f"Expected >=4 sebum entries, got {count}"

    def test_skin_ph(self, conn: sqlite3.Connection) -> None:
        """Skin pH entry must exist with range 4.5-6.0."""
        row = conn.execute(
            "SELECT value FROM skin_chemistry WHERE topic = 'skin_ph'"
        ).fetchone()
        assert row is not None
        assert "4.5" in row[0] and "6.0" in row[0]

    def test_microbiome_corynebacterium(self, conn: sqlite3.Connection) -> None:
        """Corynebacterium degrades aldehydes entry must exist."""
        row = conn.execute(
            "SELECT value FROM skin_chemistry WHERE parameter = 'corynebacterium_activity'"
        ).fetchone()
        assert row is not None
        assert "Corynebacterium" in row[0]

    def test_query_by_topic(self) -> None:
        """``get_skin_chemistry('skin_ph')`` returns pH entry."""
        results = skb.get_skin_chemistry("skin_ph")
        assert len(results) >= 1
        assert results[0]["topic"] == "skin_ph"

    def test_query_all(self) -> None:
        """``get_skin_chemistry()`` returns all entries."""
        results = skb.get_skin_chemistry()
        assert len(results) >= 10


# ── Domain 5: Aging reactions ──────────────────────────────────────────


class TestAgingReactions:
    """``aging_reactions`` table and query."""

    def test_aging_schiff_base(self, conn: sqlite3.Connection) -> None:
        """Schiff base entry must exist with k=0.00035."""
        rows = conn.execute(
            "SELECT rate_constant FROM aging_reactions WHERE reaction_type = 'schiff_base'"
        ).fetchall()
        assert len(rows) > 0
        rate = rows[0][0]
        assert rate is not None
        assert "0.00035" in rate

    def test_aging_terpene_oxidation(self, conn: sqlite3.Connection) -> None:
        """Terpene oxidation entries must exist."""
        count = conn.execute(
            "SELECT COUNT(*) FROM aging_reactions WHERE reaction_type = 'terpene_oxidation'"
        ).fetchone()[0]
        assert count >= 2

    def test_query_by_reaction_type(self) -> None:
        """``get_aging_reactions('schiff_base')`` returns all schiff base entries."""
        results = skb.get_aging_reactions("schiff_base")
        assert len(results) >= 1
        assert results[0]["reaction_type"] == "schiff_base"

    def test_query_all(self) -> None:
        """``get_aging_reactions()`` returns all entries."""
        results = skb.get_aging_reactions()
        assert len(results) >= 5


# ── Domain 6: Mixture models ───────────────────────────────────────────


class TestMixtureModels:
    """``mixture_models`` table and query."""

    def test_mixture_component_limit(self, conn: sqlite3.Connection) -> None:
        """Component limit entry must exist."""
        row = conn.execute(
            "SELECT finding FROM mixture_models WHERE topic = 'component_limit'"
        ).fetchone()
        assert row is not None
        assert "4±1" in row[0] or "4" in row[0]

    def test_competitive_antagonism_equation(self, conn: sqlite3.Connection) -> None:
        """Competitive antagonism entry must have equation."""
        row = conn.execute(
            "SELECT equation FROM mixture_models WHERE topic = 'competitive_antagonism'"
        ).fetchone()
        assert row is not None
        assert "F(U,V)" in row[0]

    def test_query_by_topic(self) -> None:
        """``get_mixture_models('component_limit')`` returns the entry."""
        results = skb.get_mixture_models("component_limit")
        assert len(results) >= 1

    def test_query_all(self) -> None:
        """``get_mixture_models()`` returns all entries."""
        results = skb.get_mixture_models()
        assert len(results) >= 4


# ── Domain 7: Climate effects ──────────────────────────────────────────


class TestClimateProfiles:
    """``climate_profiles`` table and query."""

    def test_climate_bangkok(self, conn: sqlite3.Connection) -> None:
        """Bangkok profile must have VP multiplier 2.8."""
        row = conn.execute(
            "SELECT vp_multiplier FROM climate_profiles WHERE profile_name = 'Bangkok'"
        ).fetchone()
        assert row is not None
        assert row[0] == 2.8, f"Bangkok VP multiplier should be 2.8, got {row[0]}"

    def test_climate_paris_longevity(self, conn: sqlite3.Connection) -> None:
        """Paris profile must have longevity_factor 1.0."""
        row = conn.execute(
            "SELECT longevity_factor FROM climate_profiles WHERE profile_name = 'Paris'"
        ).fetchone()
        assert row is not None
        assert row[0] == 1.0

    def test_climate_dubai_notes(self, conn: sqlite3.Connection) -> None:
        """Dubai profile must have extreme heat note."""
        row = conn.execute(
            "SELECT notes FROM climate_profiles WHERE profile_name = 'Dubai'"
        ).fetchone()
        assert row is not None
        assert "extreme" in row[0].lower()

    def test_get_climate_profile(self) -> None:
        """``get_climate_profile('Bangkok')`` returns correct data."""
        profile = skb.get_climate_profile("Bangkok")
        assert profile is not None
        assert profile["vp_multiplier"] == 2.8
        assert profile["longevity_factor"] == 0.5
        assert profile["temperature_c"] == 35.0

    def test_get_climate_profile_unknown(self) -> None:
        """``get_climate_profile('Unknown')`` returns None."""
        assert skb.get_climate_profile("__Unknown__") is None

    def test_get_climate_profiles(self) -> None:
        """``get_climate_profiles()`` returns all 4 profiles."""
        profiles = skb.get_climate_profiles()
        assert len(profiles) == 4
        names = {p["profile_name"] for p in profiles}
        assert names == {"Paris", "Bangkok", "Dubai", "New York"}


# ── Domain 8: Fabric retention ─────────────────────────────────────────


class TestFabricRetention:
    """``fabric_retention`` table and query."""

    def test_fabric_cotton_formula(self, conn: sqlite3.Connection) -> None:
        """Cotton fabric retention entry with log K formula must exist."""
        row = conn.execute(
            "SELECT log_k FROM fabric_retention WHERE fabric_type = 'cotton'"
        ).fetchone()
        assert row is not None
        assert row[0] == 0.36

    def test_query_by_fabric(self) -> None:
        """``get_fabric_retention('cotton')`` returns cotton entries."""
        results = skb.get_fabric_retention("cotton")
        assert len(results) >= 1

    def test_query_all(self) -> None:
        """``get_fabric_retention()`` returns all entries."""
        results = skb.get_fabric_retention()
        assert len(results) >= 3


# ── Domain 9: Masking rules ────────────────────────────────────────────


class TestMaskingRules:
    """``masking_rules`` table and query."""

    def test_masking_patchouli(self, conn: sqlite3.Connection) -> None:
        """Patchouli masking rule must exist."""
        rows = conn.execute(
            "SELECT * FROM masking_rules WHERE masking_material = 'Patchouli'"
        ).fetchall()
        assert len(rows) >= 1
        # masks_what is column index 2 in the table definition
        assert "citrus" in rows[0][2].lower()

    def test_masking_hedione(self, conn: sqlite3.Connection) -> None:
        """Hedione masking rule must exist with mechanism 'non-competitive'."""
        rows = conn.execute(
            "SELECT mechanism FROM masking_rules WHERE masking_material = 'Hedione'"
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == "non-competitive"

    def test_get_masking_rules(self) -> None:
        """``get_masking_rules()`` returns all rules."""
        results = skb.get_masking_rules()
        assert len(results) >= 10

    def test_get_masking_for_material(self) -> None:
        """``get_masking_for_material('Patchouli')`` returns rules."""
        results = skb.get_masking_for_material("Patchouli")
        assert len(results) >= 1

    def test_get_masking_for_material_partial(self) -> None:
        """``get_masking_for_material('Iso')`` matches Iso E Super."""
        results = skb.get_masking_for_material("Iso")
        assert len(results) >= 1
        assert any("Iso" in r["masking_material"] for r in results)


# ── Domain 10: Dose-response cliffs ────────────────────────────────────


class TestDoseResponseCliffs:
    """``dose_response_cliffs`` table and query."""

    def test_dose_response_indole_floral(self, conn: sqlite3.Connection) -> None:
        """Indole at 0.1% must be positive (narcotic creamy floral)."""
        rows = conn.execute(
            "SELECT character, quality FROM dose_response_cliffs WHERE material_name = 'Indole' AND concentration_pct = 0.1"
        ).fetchall()
        assert len(rows) >= 1
        assert any("floral" in r[0].lower() for r in rows)
        assert any(r[1] == "positive" for r in rows)

    def test_dose_response_indole_fecal(self, conn: sqlite3.Connection) -> None:
        """Indole at >1% must be dangerous (fecal repulsive)."""
        rows = conn.execute(
            "SELECT character, quality, notes FROM dose_response_cliffs WHERE material_name = 'Indole' AND quality = 'dangerous'"
        ).fetchall()
        assert len(rows) >= 1
        assert any("fecal" in (r[0] or "").lower() for r in rows)
        assert any(r[1] == "dangerous" for r in rows)
        assert any("sharp cliff" in (r[2] or "") for r in rows)

    def test_dose_response_ambrox_turn(self, conn: sqlite3.Connection) -> None:
        """Ambrox at 5% must be negative (urinous animalic turn)."""
        rows = conn.execute(
            "SELECT character, quality FROM dose_response_cliffs WHERE material_name = 'Ambrox' AND concentration_pct = 5.0"
        ).fetchall()
        assert len(rows) >= 1
        assert any(r[1] == "negative" for r in rows)
        assert any("urinous" in (r[0] or "").lower() for r in rows)

    def test_query_indole(self) -> None:
        """``get_dose_response_cliffs('Indole')`` returns all Indole entries."""
        results = skb.get_dose_response_cliffs("Indole")
        assert len(results) >= 4

    def test_query_galaxolide(self) -> None:
        """``get_dose_response_cliffs('Galaxolide')`` returns entries."""
        results = skb.get_dose_response_cliffs("Galaxolide")
        assert len(results) >= 3


# ── Summary ────────────────────────────────────────────────────────────


class TestGetAllScience:
    """``get_all_science()`` summary."""

    def test_get_all_science(self) -> None:
        """Summary must return all domains with counts > 0."""
        summary = skb.get_all_science()
        expected_tables = [
            "or_biophysics",
            "material_anosmia",
            "evaporation_model",
            "unifac_groups",
            "skin_chemistry",
            "aging_reactions",
            "mixture_models",
            "climate_profiles",
            "fabric_retention",
            "masking_rules",
            "dose_response_cliffs",
        ]
        for tbl in expected_tables:
            assert tbl in summary, f"Table '{tbl}' missing from summary"
            count = summary[tbl]
            assert count > 0, f"Table '{tbl}' has count {count}, expected >0"
