"""Quick score comparison for Cedre Azure variants."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from _opt_cedre_azure_mass_market import ORIGINAL_UL, MASS_MARKET_UL, score_ul

print("Scoring ORIGINAL Cedre Azure...")
orig = score_ul(ORIGINAL_UL)
print(f"  hedonic={orig['hedonic']:.1f}  sillage={orig['sillage']:.1f}  longevity={orig['longevity']:.1f}  total={orig['total']:.1f}")
print(f"  perceptual_clarity={orig['perceptual_clarity']:.1f}  skin_performance={orig['skin_performance']:.1f}")

print("\nScoring MASS-MARKET variant...")
mm = score_ul(MASS_MARKET_UL)
print(f"  hedonic={mm['hedonic']:.1f}  sillage={mm['sillage']:.1f}  longevity={mm['longevity']:.1f}  total={mm['total']:.1f}")
print(f"  perceptual_clarity={mm['perceptual_clarity']:.1f}  skin_performance={mm['skin_performance']:.1f}")

print("\nDelta (Mass-Mkt - Original):")
for axis in ["hedonic", "sillage", "longevity", "perceptual_clarity", "skin_performance", "total"]:
    d = mm[axis] - orig[axis]
    print(f"  {axis}: {d:+.1f}")

print(f"\nMaterials: {len(ORIGINAL_UL)} -> {len(MASS_MARKET_UL)}")
print(f"Concentrate: {sum(ORIGINAL_UL.values()):.0f} -> {sum(MASS_MARKET_UL.values()):.0f} uL")
