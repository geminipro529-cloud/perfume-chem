"""Tests for the fragment-based property estimator module.

These tests validate:
  - VP estimation (Stein-Brown style) against known values
  - logP estimation (Wildman-Crippen style)
  - ODT estimation (class-bracketed with MW scaling)
  - Activity coefficient lookup
  - Note tier classification
  - Combined ``estimate_all`` convenience wrapper
  - Input validation (invalid SMILES)
  - Database validation (R² on log₁₀ VP)
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Ensure the repo root is on sys.path ──
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from engine import property_estimator as property_estimator  # noqa: E402
from engine.property_estimator import (  # noqa: E402
    estimate_activity_coef,
    estimate_all,
    estimate_logp,
    estimate_note_tier,
    estimate_odt,
    estimate_vp,
    validate_vp_estimates,
)

# ===================================================================
# 1.  VP estimation — basic smoke tests
# ===================================================================


class TestEstimateVP:
    """Basic VP estimation smoke tests."""

    def test_estimate_vp_returns_float(self) -> None:
        """Any valid SMILES returns a float."""
        result = estimate_vp("CC=O")  # acetaldehyde
        assert isinstance(result, float), f"Expected float, got {type(result)}"

    def test_estimate_vp_benzyl_acetate(self) -> None:
        """Benzyl acetate VP estimate should be within 10× of 15 Pa."""
        # Benzyl acetate: CC(=O)OCc1ccccc1, known VP ≈ 15 Pa
        result = estimate_vp("CC(=O)OCc1ccccc1")
        assert 1.5 <= result <= 150.0, (
            f"Benzyl acetate VP {result:.2f} Pa out of range [1.5, 150]"
        )

    def test_estimate_vp_invalid_smiles(self) -> None:
        """Invalid SMILES raises ValueError, not a silent failure."""
        with pytest.raises(ValueError):
            estimate_vp("")
        with pytest.raises(ValueError):
            estimate_vp("O=O")  # no carbon
        with pytest.raises(ValueError):
            estimate_vp("F")  # single fluorine, no carbon


# ===================================================================
# 2.  logP estimation
# ===================================================================


class TestEstimateLogP:
    """logP estimation smoke tests."""

    def test_estimate_logp_returns_float(self) -> None:
        """Any valid SMILES returns a float."""
        result = estimate_logp("CC=O")
        assert isinstance(result, float), f"Expected float, got {type(result)}"

    def test_estimate_logp_simple(self) -> None:
        """Simple molecule returns a reasonable logP value."""
        # n-octane C8H18 → SMILES: CCCCCCCC
        logp = estimate_logp("CCCCCCCC")
        # Aliphatic: 8 × 0.2 = 1.6, rings: 0 → reasonable hydrophobic
        assert 0.5 <= logp <= 4.0, (
            f"n-Octane logP {logp:.2f} out of expected range [0.5, 4.0]"
        )

    def test_estimate_logp_water_soluble(self) -> None:
        """A polar molecule should have lower (or negative) logP."""
        # Ethanol: CCO → small + OH
        logp_ethanol = estimate_logp("CCO")
        # Octane (non-polar)
        logp_octane = estimate_logp("CCCCCCCC")
        assert logp_ethanol < logp_octane, (
            f"Ethanol logP {logp_ethanol:.2f} should be < octane {logp_octane:.2f}"
        )


# ===================================================================
# 3.  ODT estimation
# ===================================================================


class TestEstimateODT:
    """ODT class-bracketed estimation tests."""

    def test_estimate_odt_esters(self) -> None:
        """Ester class ODT should be within the defined bracket."""
        odt_air, odt_eth = estimate_odt("esters", mw=150.0, logp=2.0)
        # Ester bracket: air [0.001, 0.1] ppb, eth [0.001, 0.01] ppm
        assert 0.0005 <= odt_air <= 0.15, f"ODT air {odt_air} out of ester bracket"
        assert 0.0005 <= odt_eth <= 0.02, f"ODT eth {odt_eth} out of ester bracket"

    def test_estimate_odt_scale_by_mw(self) -> None:
        """Higher MW should give lower (more potent) ODT within bracket."""
        odt_low_mw, _ = estimate_odt("alcohols", mw=60.0, logp=1.0)
        odt_high_mw, _ = estimate_odt("alcohols", mw=300.0, logp=1.0)
        # Higher MW → more potent → lower threshold
        assert odt_high_mw <= odt_low_mw, (
            f"High MW ODT {odt_high_mw} should be <= low MW {odt_low_mw}"
        )

    def test_estimate_odt_unknown_class_falls_back(self) -> None:
        """An unknown chemical class should fall back to a default bracket."""
        odt_air, odt_eth = estimate_odt("unknown_class_xyz", mw=200.0, logp=3.0)
        assert isinstance(odt_air, float)
        assert isinstance(odt_eth, float)
        assert 0.0 < odt_air < 10.0  # sensibly bounded


# ===================================================================
# 4.  Activity coefficient
# ===================================================================


class TestEstimateActivityCoef:
    """Activity coefficient lookup tests."""

    def test_estimate_activity_coef_valid(self) -> None:
        """Each known class returns the correct value."""
        cases: dict[str, float] = {
            "non_polar_hydrocarbons": 3.0,
            "polar_esters": 1.75,
            "mid_polarity_sesquiterpenes_alcohols": 1.5,
            "h_bond_donors_acceptors": 0.6,
            "macrocyclic_musks": 0.5,
        }
        for cls, expected in cases.items():
            gamma = estimate_activity_coef(cls)
            assert gamma == pytest.approx(expected, abs=0.01), (
                f"{cls}: expected {expected}, got {gamma}"
            )

    def test_estimate_activity_coef_invalid_raises(self) -> None:
        """An unknown class raises ValueError."""
        with pytest.raises(ValueError):
            estimate_activity_coef("nonexistent_class")


# ===================================================================
# 5.  Note tier
# ===================================================================


class TestEstimateNoteTier:
    """Note tier classification tests."""

    def test_estimate_note_tier_top(self) -> None:
        """VP > 2 Pa → 'top'."""
        assert estimate_note_tier(10.0) == "top"
        assert estimate_note_tier(2.1) == "top"

    def test_estimate_note_tier_heart(self) -> None:
        """0.1 ≤ VP ≤ 2 Pa → 'heart'."""
        assert estimate_note_tier(1.0) == "heart"
        assert estimate_note_tier(0.1) == "heart"

    def test_estimate_note_tier_base(self) -> None:
        """VP < 0.1 Pa → 'base'."""
        assert estimate_note_tier(0.05) == "base"
        assert estimate_note_tier(0.0001) == "base"


# ===================================================================
# 6.  Combined estimate_all
# ===================================================================


class TestEstimateAll:
    """Combined estimator smoke tests."""

    def test_estimate_all_returns_dict(self) -> None:
        """estimate_all returns a dict with all expected keys."""
        result = estimate_all("CC=O", chemical_class="aldehydes", mw=44.05)
        expected_keys = {
            "vp_pa",
            "logp",
            "odt_air_ppb",
            "odt_eth_ppm",
            "activity_coef",
            "note_tier",
        }
        assert set(result.keys()) == expected_keys, (
            f"Keys mismatch: {set(result.keys()) ^ expected_keys}"
        )

    def test_estimate_all_without_class(self) -> None:
        """estimate_all works even without chemical_class or MW."""
        result = estimate_all("CC=O")
        assert isinstance(result["vp_pa"], float)
        assert isinstance(result["logp"], float)
        assert isinstance(result["note_tier"], str)

    def test_estimate_all_values_are_plausible(self) -> None:
        """Estimate values for a known molecule are in plausible ranges."""
        result = estimate_all("CC(=O)OCc1ccccc1")
        # vp
        assert 0.1 <= result["vp_pa"] <= 500.0
        # logP (aromatic + ester → moderate)
        assert -2.0 <= result["logp"] <= 5.0
        # ODT
        assert 0.0 < result["odt_air_ppb"] < 10.0
        assert 0.0 < result["odt_eth_ppm"] < 5.0
        # note_tier
        assert result["note_tier"] in ("top", "heart", "base")


# ===================================================================
# 7.  Input validation
# ===================================================================


class TestInputValidation:
    """Invalid input handling tests."""

    def test_estimate_vp_invalid_smiles(self) -> None:
        """Invalid SMILES raises ValueError, not a silent failure."""
        with pytest.raises(ValueError):
            estimate_vp("")
        with pytest.raises(ValueError):
            estimate_vp("")  # no carbons
        with pytest.raises(ValueError):
            estimate_vp("O=O")  # no carbon
        with pytest.raises(ValueError):
            estimate_vp("ClCl")  # no carbon


# ===================================================================
# 8.  Database validation
# ===================================================================


class TestDatabaseValidation:
    """Validation against the perfumery knowledge-base materials.

    These are integration-style tests that require the KB database.
    They verify the estimator achieves a minimum R² on log₁₀(VP).
    """

    def test_validation_database_connection_is_read_only(self) -> None:
        """Validation queries must not open the repository KB for writing."""
        connection = property_estimator._get_kb_read_connection()
        try:
            assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        finally:
            connection.close()

    def test_vp_validation_r_squared(self) -> None:
        """VP estimates must achieve R² > 0.2 against DB materials.

        This is a relaxed threshold for a pure-regression estimator.
        """
        result = validate_vp_estimates()
        if result["n"] < 3:
            pytest.skip(f"Only {result['n']} materials with SMILES+VP — insufficient")
        assert result["r_squared"] > 0.2, (
            f"VP validation R² = {result['r_squared']} (need > 0.2, n={result['n']})"
        )

    def test_vp_validation_logp_available(self) -> None:
        """VP validation function should run without errors."""
        result = validate_vp_estimates()
        assert isinstance(result, dict)
        assert "r_squared" in result
        assert isinstance(result.get("n", 0), int)
