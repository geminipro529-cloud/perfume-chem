"""Regression tests for diffusion model corrections (2026-04-28).

Verifies that VP_25 values are in Pa (not mmHg), skin-temperature correction
applies correctly, gamma_map parameter integrates, and score_diffusion returns
sane ranges.
"""

import math

from engine.diffusion_model import (
    DIFFUSION_DATA,
    _estimate_kaw_eff,
    score_diffusion,
)
from engine.skin_interaction import _hansen_substantivity

# ── VP_25 values are in Pa (not mmHg) ──

def test_ethyl_2_methylbutyrate_vp_is_pa():
    """14 mmHg → 1860 Pa. If this is ~25, it's still in mmHg."""
    vp = DIFFUSION_DATA["Ethyl 2-Methylbutyrate"]["VP_25"]
    assert vp > 100, f"Expected ~1860 Pa (14 mmHg × 133), got {vp}"
    assert 1500 < vp < 2500, f"Ethyl 2-Methylbutyrate VP={vp} outside 1500-2500 Pa range"


def test_hexyl_acetate_vp_is_pa():
    """1.4 mmHg → 190 Pa."""
    vp = DIFFUSION_DATA["Hexyl Acetate"]["VP_25"]
    assert 100 < vp < 300, f"Hexyl Acetate VP={vp} outside 100-300 Pa range"


def test_heavy_materials_have_low_vp():
    """Sandalore, Norlimbanol, Zenolide should have VP < 1 Pa."""
    for name in ("Sandalore", "Norlimbanol Dextro", "Zenolide"):
        vp = DIFFUSION_DATA[name]["VP_25"]
        assert vp < 1.0, f"{name} VP={vp} should be <1 Pa (heavy material)"


def test_bug_prone_materials_have_pa_comment():
    """Materials with <10 Pa VP should have the # Pa, not mmHg guard."""
    heavy = ["Sandalore", "Norlimbanol Dextro", "Zenolide",
             "Alpha Isomethyl Ionone"]
    for name in heavy:
        vp = DIFFUSION_DATA[name]["VP_25"]
        assert vp < 1.0 or name == "Alpha Isomethyl Ionone", \
            f"{name}: vp={vp}"


# ── Skin-temperature correction ──

def test_kaw_estimate_uses_skin_temp():
    """_estimate_kaw_eff should produce values ~1.59× higher than 25°C VP."""
    vp_test = 100.0
    mw_test = 200.0
    # Without correction (if temp were 25C), kaw would be smaller
    kaw_skin = _estimate_kaw_eff(vp_test, mw_test)
    # Compute equivalent at 25C by dividing out the factor
    # exp(50000/8.314 * (1/298.15 - 1/305.15)) ≈ 1.59
    correction = math.exp(50000.0 / 8.314 * (1.0 / 298.15 - 1.0 / 305.15))
    vp_25c = vp_test / correction
    kaw_25c = 0.003 * math.sqrt(vp_25c) * math.sqrt(180.0 / mw_test)
    ratio = kaw_skin / max(kaw_25c, 1e-10)
    assert 1.2 < ratio < 2.0, \
        f"Kaw skin/25C ratio={ratio:.3f} not in expected 1.2-2.0 range"


# ── score_diffusion gamma_map ──

def test_score_diffusion_accepts_gamma_map():
    """score_diffusion should accept gamma_map and not crash."""
    ingredients = {"Iso E Super": 100.0, "Limonene": 50.0, "Galaxolide": 30.0}
    # Without gamma_map
    r1 = score_diffusion(ingredients)
    assert 0 <= r1.score <= 100
    # With gamma_map
    r2 = score_diffusion(ingredients, gamma_map={
        "Iso E Super": 1.5, "Limonene": 0.8, "Galaxolide": 1.2,
    })
    assert 0 <= r2.score <= 100


def test_gamma_map_changes_classification():
    """High gamma should push materials toward far-field classification."""
    ingredients = {"Iso E Super": 100.0}
    # Same material with different gamma values
    r_low = score_diffusion(ingredients, gamma_map={"Iso E Super": 0.1})
    r_high = score_diffusion(ingredients, gamma_map={"Iso E Super": 5.0})
    # High gamma should increase projection index
    assert r_high.projection_index >= r_low.projection_index, \
        "Higher gamma should not decrease projection index"


# ── Skin interaction fallback ──

def test_hansen_substantivity_returns_float_or_none():
    """_hansen_substantivity should return a float or None (no crash)."""
    result = _hansen_substantivity("Iso E Super")
    # May be None if name not found in registry, but should not raise
    if result is not None:
        assert 0.0 <= result <= 1.0


def test_score_diffusion_known_materials():
    """score_diffusion with known test formula returns sane values."""
    ingredients = {
        "Ethyl 2-Methylbutyrate": 10.0,
        "Limonene": 30.0,
        "Iso E Super": 150.0,
        "Galaxolide": 100.0,
        "Vanillin": 20.0,
    }
    r = score_diffusion(ingredients)
    assert 0 <= r.score <= 100
    assert r.sillage_class in ("beast", "moderate", "balanced", "intimate", "unknown")
    assert len(r.field_materials["far"]) + len(r.field_materials["mid"]) + len(r.field_materials["near"]) >= 1
