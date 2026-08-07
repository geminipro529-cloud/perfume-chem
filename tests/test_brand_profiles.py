"""Tests for engine.reconstruction.brand_profiles."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reconstruction.brand_profiles import (
    BrandProfile,
    PROFILES,
    apply_brand_priors,
    get_profile,
)

# ── helpers ────────────────────────────────────────────────────────────────────

_REQUIRED_FIELDS = (
    "profile_id",
    "brands",
    "protected_blocks",
    "compression_traps",
    "socket_strategy",
)


def _all_profile_ids() -> list[str]:
    return [p.profile_id for p in PROFILES.values()]


# ── PROFILES count ─────────────────────────────────────────────────────────────


def test_profiles_has_eight_entries():
    assert len(PROFILES) == 8


# ── get_profile: case-insensitive brand lookup ─────────────────────────────────


def test_get_profile_ysl():
    profile = get_profile("ysl")
    assert profile is not None
    assert profile.profile_id == "ysl_modern_masculine"


def test_get_profile_ysl_case_insensitive():
    profile = get_profile("YSL")
    assert profile is not None
    assert profile.profile_id == "ysl_modern_masculine"


def test_get_profile_ysl_full_name():
    profile = get_profile("Yves Saint Laurent")
    assert profile is not None
    assert profile.profile_id == "ysl_modern_masculine"


def test_get_profile_prada():
    profile = get_profile("Prada")
    assert profile is not None
    assert profile.profile_id == "prada_clean_iris"


def test_get_profile_prada_lowercase():
    profile = get_profile("prada")
    assert profile is not None
    assert profile.profile_id == "prada_clean_iris"


def test_get_profile_dior():
    profile = get_profile("Dior")
    assert profile is not None
    assert profile.profile_id == "dior_family_differential"


def test_get_profile_dior_full():
    profile = get_profile("Christian Dior")
    assert profile is not None
    assert profile.profile_id == "dior_family_differential"


def test_get_profile_chanel():
    profile = get_profile("Chanel")
    assert profile is not None
    assert profile.profile_id == "chanel_era_strict"


def test_get_profile_hermes():
    profile = get_profile("Hermes")
    assert profile is not None
    assert profile.profile_id == "hermes_transparent_spacing"


def test_get_profile_hermes_accent():
    profile = get_profile("Hermès")
    assert profile is not None
    assert profile.profile_id == "hermes_transparent_spacing"


def test_get_profile_unknown_returns_none():
    assert get_profile("NonexistentBrand") is None


def test_get_profile_empty_string_returns_none():
    assert get_profile("") is None


# ── apply_brand_priors: natural_complexity_prior > 0.7 ────────────────────────


def test_apply_brand_priors_high_natural_boost():
    """Amouage (natural_complexity_prior=0.95) should boost naturals by 10%."""
    profile = get_profile("Amouage")
    assert profile is not None
    assert profile.natural_complexity_prior > 0.7

    weights = {
        "Bergamot EO": 100.0,
        "Sandalwood EO": 50.0,
        "Iso E Super": 200.0,
        "Hedione": 150.0,
    }
    adjusted = apply_brand_priors(weights, profile)

    # Naturals boosted by 10% (round(..., 4) in source)
    assert adjusted["Bergamot EO"] == round(100.0 * 1.10, 4)
    assert adjusted["Sandalwood EO"] == round(50.0 * 1.10, 4)
    # Non-naturals unchanged
    assert adjusted["Iso E Super"] == 200.0
    assert adjusted["Hedione"] == 150.0


def test_apply_brand_priors_high_natural_keyword_variants():
    """Check that all natural keywords trigger the boost."""
    profile = get_profile("Amouage")
    assert profile is not None

    weights = {
        "Rose absolute": 100.0,
        "Benzoin resinoid": 100.0,
        "Jasmine co2": 100.0,
        "Vanilla extract": 100.0,
        "Cedarwood oil": 100.0,
        "Orris concrete": 100.0,
        "Musk tincture": 100.0,
    }
    adjusted = apply_brand_priors(weights, profile)
    for mat, val in adjusted.items():
        assert val == 110.0, f"{mat} was not boosted"


def test_apply_brand_priors_low_natural_no_change():
    """Prada (natural_complexity_prior=0.30) should make no changes."""
    profile = get_profile("Prada")
    assert profile is not None
    assert profile.natural_complexity_prior <= 0.7

    weights = {
        "Bergamot EO": 100.0,
        "Sandalwood EO": 50.0,
        "Iso E Super": 200.0,
    }
    adjusted = apply_brand_priors(weights, profile)
    assert adjusted == weights


def test_apply_brand_priors_high_captive_reduces_certainty():
    """YSL (unknown_captive_prior=0.40) — not > 0.4, so no reduction.

    Dior (unknown_captive_prior=0.55) — > 0.4, so all weights * 0.95.
    """
    profile = get_profile("Dior")
    assert profile is not None
    assert profile.unknown_captive_prior > 0.4

    weights = {"Bergamot EO": 100.0, "Iso E Super": 200.0}
    adjusted = apply_brand_priors(weights, profile)
    assert adjusted["Bergamot EO"] == 100.0 * 0.95
    assert adjusted["Iso E Super"] == 200.0 * 0.95


def test_apply_brand_priors_low_captive_no_change():
    """Prada (unknown_captive_prior=0.25) — not > 0.4, no change."""
    profile = get_profile("Prada")
    assert profile is not None
    assert profile.unknown_captive_prior <= 0.4

    weights = {"Bergamot EO": 100.0, "Iso E Super": 200.0}
    adjusted = apply_brand_priors(weights, profile)
    assert adjusted == weights


def test_apply_brand_priors_both_priors_active():
    """Amouage: high natural (0.95) AND high captive (0.25 — not > 0.4).

    So only natural boost applies.
    """
    profile = get_profile("Amouage")
    assert profile is not None
    assert profile.natural_complexity_prior > 0.7
    assert profile.unknown_captive_prior <= 0.4

    weights = {"Bergamot EO": 100.0, "Iso E Super": 200.0}
    adjusted = apply_brand_priors(weights, profile)
    assert adjusted["Bergamot EO"] == 110.0
    assert adjusted["Iso E Super"] == 200.0


def test_apply_brand_priors_both_priors_active_captive():
    """Dior: high natural (0.30 — not > 0.7) AND high captive (0.55 > 0.4).

    So only captive reduction applies.
    """
    profile = get_profile("Dior")
    assert profile is not None
    assert profile.natural_complexity_prior <= 0.7
    assert profile.unknown_captive_prior > 0.4

    weights = {"Bergamot EO": 100.0, "Iso E Super": 200.0}
    adjusted = apply_brand_priors(weights, profile)
    assert adjusted["Bergamot EO"] == 95.0
    assert adjusted["Iso E Super"] == 190.0


def test_apply_brand_priors_empty_roster():
    profile = get_profile("Amouage")
    assert profile is not None
    assert apply_brand_priors({}, profile) == {}


# ── BrandProfile from_dict round-trip ──────────────────────────────────────────


def test_brand_profile_from_dict_round_trip():
    original = BrandProfile(
        profile_id="test_profile",
        brands=("TestBrand", "Test Brand Inc"),
        reformulation_risk="medium",
        unknown_captive_prior=0.35,
        natural_complexity_prior=0.60,
        negative_space_importance=0.5,
        default_evaluation_hours=6,
        protected_blocks=("block_a", "block_b"),
        compression_traps=("trap_x",),
        socket_strategy="balanced",
    )
    as_dict = original.as_dict()
    restored = BrandProfile.from_dict(as_dict)

    assert restored.profile_id == original.profile_id
    assert restored.brands == original.brands
    assert restored.reformulation_risk == original.reformulation_risk
    assert restored.unknown_captive_prior == original.unknown_captive_prior
    assert restored.natural_complexity_prior == original.natural_complexity_prior
    assert restored.negative_space_importance == original.negative_space_importance
    assert restored.default_evaluation_hours == original.default_evaluation_hours
    assert restored.protected_blocks == original.protected_blocks
    assert restored.compression_traps == original.compression_traps
    assert restored.socket_strategy == original.socket_strategy


def test_brand_profile_from_dict_empty():
    restored = BrandProfile.from_dict({})
    assert restored.profile_id == ""
    assert restored.brands == ()
    assert restored.reformulation_risk == ""
    assert restored.unknown_captive_prior == 0.0
    assert restored.natural_complexity_prior == 0.0
    assert restored.negative_space_importance == 0.0
    assert restored.default_evaluation_hours == 4
    assert restored.protected_blocks == ()
    assert restored.compression_traps == ()
    assert restored.socket_strategy == ""


# ── All 8 profiles have required fields ────────────────────────────────────────


def test_all_profiles_have_required_fields():
    for profile_id, profile in PROFILES.items():
        for field in _REQUIRED_FIELDS:
            val = getattr(profile, field, None)
            assert val is not None, f"Profile {profile_id!r} is missing required field {field!r}"
        # profile_id must match the dict key
        assert profile.profile_id == profile_id, (
            f"Profile key {profile_id!r} does not match profile_id {profile.profile_id!r}"
        )
        # brands must be non-empty
        assert len(profile.brands) > 0, f"Profile {profile_id!r} has empty brands tuple"
        # protected_blocks must be non-empty
        assert len(profile.protected_blocks) > 0, (
            f"Profile {profile_id!r} has empty protected_blocks"
        )
        # compression_traps must be non-empty
        assert len(profile.compression_traps) > 0, (
            f"Profile {profile_id!r} has empty compression_traps"
        )
        # socket_strategy must be a non-empty string
        assert len(profile.socket_strategy) > 0, f"Profile {profile_id!r} has empty socket_strategy"


def test_all_profiles_have_valid_reformulation_risk():
    valid = {"low", "medium", "high", "very_high", "variable"}
    for profile_id, profile in PROFILES.items():
        assert profile.reformulation_risk in valid, (
            f"Profile {profile_id!r} has invalid reformulation_risk {profile.reformulation_risk!r}"
        )


def test_all_profiles_have_valid_socket_strategy():
    valid = {"tight", "loose", "balanced", "aggressive", "conservative"}
    for profile_id, profile in PROFILES.items():
        assert profile.socket_strategy in valid, (
            f"Profile {profile_id!r} has invalid socket_strategy {profile.socket_strategy!r}"
        )
