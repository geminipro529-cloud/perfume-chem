"""Diagnostic sillage/tenacity curve for Mr. Sandman formula.

Uses engine.diffusion_model.score_diffusion for the near/mid/far field
architecture, plus a VP-weighted temporal headspace model for tenacity.

No hill-climb, no scorer composite — pure diagnostic.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.diffusion_model import score_diffusion, DIFFUSION_DATA


# Mr. Sandman formula — mass_frac (% of concentrate), dilution factor (active/bottle)
# Name keys must match diffusion_model.DIFFUSION_DATA aliases.
FORMULA = [
    # (name, mass_frac %, dilution, vp_pa_from_formula, odt_ppb)
    # TOP
    ("Bergamot FCF",          5.00, 1.00,    1.3e2, 30),
    ("Red Mandarin EO",       3.00, 1.00,    1.5e2, 40),
    ("Aldehyde C11",          0.30, 1.00,    5.0e0, 0.5),   # C11 undecylenic → closest DIFFUSION_DATA key
    ("Aldehyde C12 MNA",      2.50, 0.01,    5.0e0, 0.7),
    # HEART
    ("Hedione",              15.00, 1.00,    8.0e-2, 1000),
    ("Heliotropin Fleuressence", 6.00, 1.00, 2.0e-1, 0.5),  # Heliotropal / piperonal aliased
    ("Anisaldehyde",          3.00, 1.00,    4.0e-1, 0.3),  # not in DIFFUSION_DATA — score_diffusion will skip, handled separately
    ("Alpha Irone",           8.00, 0.30,    4.0e-3, 0.002),
    ("Ultralia",              0.20, 1.00,    5.0e-2, 0.1),
    ("Mayol",                 1.50, 1.00,    1.0e-1, 5),
    ("Hydroxycitronellal",    1.00, 1.00,    2.0e0, 10),
    ("Damascol",              2.00, 0.10,    1.0e-1, 0.5),
    ("Ethyl Maltol",          2.50, 0.10,    3.0e-2, 20),   # not in DIFFUSION_DATA
    ("Vanillin",              4.00, 0.10,    7.0e-4, 20),
    ("Orivone",               0.60, 1.00,    1.8e-2, 3),
    ("Farnesol",              0.25, 1.00,    2.0e-3, 20),
    # BASE
    ("Hexyl Salicylate",      8.00, 1.00,    3.5e-2, 35),
    ("Coumarin",              1.50, 1.00,    1.3e-2, 7),
    ("Cashmeran",            10.00, 0.20,    5.0e-3, 0.2),
    ("Ethylene Brassylate",   9.00, 1.00,    3.0e-4, 0.8),
    ("Musk Ketone",           4.00, 0.10,    5.0e-4, 1),
    ("Ambrettolide",          3.50, 0.10,    3.0e-4, 0.5),
    ("Romandolide",           3.00, 1.00,    5.0e-4, 3),    # not in DIFFUSION_DATA — handled separately
    ("Iso E Super",           4.00, 1.00,    2.0e-3, 0.5),
    ("Azarbre",               2.00, 1.00,    1.0e-3, 0.2),  # not in DIFFUSION_DATA — handled separately
    ("Benzoin Resinoid",      1.00, 0.50,    1.0e-4, 10),
]


# ───────────────────────── Diffusion (field architecture) ─────────────────────────

# score_diffusion expects {name: amount}, dilutions {name: factor}
ingredients = {row[0]: row[1] for row in FORMULA}
dilutions   = {row[0]: row[2] for row in FORMULA}

report = score_diffusion(ingredients, dilutions)

print("=" * 78)
print("MR. SANDMAN — DIFFUSION ARCHITECTURE (near/mid/far field)")
print("=" * 78)
print(f"Score:                    {report.score}/100")
print(f"Sillage class:            {report.sillage_class}")
print(f"Far-field %:              {report.far_field_pct}")
print(f"Mid-field %:              {report.mid_field_pct}")
print(f"Near-field %:             {report.near_field_pct}")
print(f"Projection index (Kaw):   {report.projection_index}")
print(f"MW spread:                {report.molecular_weight_spread} Da")
print()
for d in report.diagnostics:
    print(f"  {d}")

# Materials NOT found in DIFFUSION_DATA (worth flagging)
missing = [n for n in ingredients if n not in DIFFUSION_DATA]
if missing:
    print()
    print("Materials without DIFFUSION_DATA entry (skipped in diffusion scoring):")
    for m in missing:
        mf = ingredients[m] * dilutions[m]
        print(f"  - {m:30s}  active_frac = {mf:.3f}%")


# ───────────────────────── Tenacity (temporal headspace curve) ─────────────────────────

# Simple per-material depletion model:
#   fraction_remaining(t) = exp(-k * VP * t)
# where k is calibrated so a VP=1 Pa material drops to ~37% after 60 min.
#   k ≈ 1 / 60 min⁻¹ / Pa
#
# Perceived intensity contribution at t:
#   I_i(t) = active_frac × VP × fraction_remaining(t) / (ODT/1000)
#
# This is the same Intensity Index used in the formula spec, decayed over time.

K_DECAY = 1.0 / 60.0  # per minute per Pa

TIME_POINTS_MIN = [0, 20, 60, 180, 360, 720]   # 0, 20min, 1h, 3h, 6h, 12h
TIME_LABELS     = ["t=0", "20 min", "1 h", "3 h", "6 h", "12 h"]


def intensity(active_frac_pct: float, vp_pa: float, odt_ppb: float, t_min: float) -> float:
    """Decayed Intensity Index at time t."""
    remaining = math.exp(-K_DECAY * vp_pa * t_min)
    active = active_frac_pct * remaining
    odt_frac = odt_ppb / 1000.0
    return active * vp_pa / max(odt_frac, 1e-9)


print()
print("=" * 78)
print("TENACITY — temporal Intensity Index by section")
print("=" * 78)

# Bucket by section (hard-coded from formula order)
SECTION_CUTOFF_TOP = 4
SECTION_CUTOFF_HEART = 16  # first 4 top + next 12 heart
section_of = []
for i in range(len(FORMULA)):
    if i < SECTION_CUTOFF_TOP:
        section_of.append("TOP")
    elif i < SECTION_CUTOFF_HEART:
        section_of.append("HEART")
    else:
        section_of.append("BASE")

section_curves = {"TOP": [], "HEART": [], "BASE": []}

for t_min in TIME_POINTS_MIN:
    per_section = {"TOP": 0.0, "HEART": 0.0, "BASE": 0.0}
    for (name, mass_frac, dil, vp, odt), sec in zip(FORMULA, section_of):
        active = mass_frac * dil
        per_section[sec] += intensity(active, vp, odt, t_min)
    for sec in per_section:
        section_curves[sec].append(per_section[sec])

# Print table
hdr = f"{'Section':<8}" + "".join(f"{lbl:>14}" for lbl in TIME_LABELS)
print(hdr)
print("-" * len(hdr))
for sec in ("TOP", "HEART", "BASE"):
    row = f"{sec:<8}" + "".join(f"{v:>14,.0f}" for v in section_curves[sec])
    print(row)

# Section dominance at each time point
print()
print("Dominant section at each time point:")
for i, lbl in enumerate(TIME_LABELS):
    vals = {sec: section_curves[sec][i] for sec in ("TOP", "HEART", "BASE")}
    total = sum(vals.values()) or 1e-9
    dom = max(vals, key=vals.get)
    pct = {sec: 100.0 * v / total for sec, v in vals.items()}
    print(f"  {lbl:<8}  TOP={pct['TOP']:5.1f}%  HEART={pct['HEART']:5.1f}%  BASE={pct['BASE']:5.1f}%   → {dom}")

# Top contributors at key points (t=0, 1h, 6h, 12h)
print()
print("Top 5 Intensity Contributors per time point:")
for t_min, lbl in zip(TIME_POINTS_MIN, TIME_LABELS):
    contribs = []
    for (name, mass_frac, dil, vp, odt) in FORMULA:
        active = mass_frac * dil
        contribs.append((name, intensity(active, vp, odt, t_min)))
    contribs.sort(key=lambda x: -x[1])
    top5 = contribs[:5]
    print(f"\n  {lbl}:")
    for name, i_val in top5:
        print(f"    {name:<30s}  I = {i_val:>12,.1f}")


# ───────────────────────── Brief fit diagnostic ─────────────────────────

print()
print("=" * 78)
print("BRIEF-FIT INTERPRETATION — Mr. Sandman (lullaby-drift)")
print("=" * 78)

notes = []

# Check drift shape: heart should dominate 20min-3h, base should dominate 6h+
def section_share(t_idx, sec):
    total = sum(section_curves[s][t_idx] for s in ("TOP", "HEART", "BASE")) or 1e-9
    return 100.0 * section_curves[sec][t_idx] / total

# Brief expectations
heart_at_1h = section_share(2, "HEART")
base_at_6h  = section_share(4, "BASE")
base_at_12h = section_share(5, "BASE")
top_at_0    = section_share(0, "TOP")

if top_at_0 >= 40:
    notes.append(f"✓ Top present at t=0 ({top_at_0:.1f}% of Σ Intensity) — retro-glamour lift registering")
elif top_at_0 >= 20:
    notes.append(f"◦ Top moderate at t=0 ({top_at_0:.1f}%) — subtle entry (acceptable for lullaby)")
else:
    notes.append(f"⚠ Top weak at t=0 ({top_at_0:.1f}%) — opening may feel flat")

if heart_at_1h >= 45:
    notes.append(f"✓ Heart dominates at 1h ({heart_at_1h:.1f}%) — jingle chord registering on schedule")
else:
    notes.append(f"⚠ Heart weak at 1h ({heart_at_1h:.1f}%) — lullaby signal may not register strongly")

if base_at_6h >= 50:
    notes.append(f"✓ Base dominates at 6h ({base_at_6h:.1f}%) — blanket-drift engaged")
else:
    notes.append(f"⚠ Base weak at 6h ({base_at_6h:.1f}%) — drift-to-sleep shape may not hold")

if base_at_12h >= 70:
    notes.append(f"✓ Base holds at 12h ({base_at_12h:.1f}%) — tenacity confirmed for overnight trail")
else:
    notes.append(f"⚠ Base thin at 12h ({base_at_12h:.1f}%) — overnight persistence questionable")

# Diffusion field match to brief: lullaby wants near-dominant (intimate), mid-supported, minimal far
if report.near_field_pct >= 50:
    notes.append(f"✓ Near-field dominant ({report.near_field_pct:.0f}%) — intimate skin-scent matches drift-to-sleep brief")
elif report.far_field_pct >= 40:
    notes.append(f"⚠ Far-field high ({report.far_field_pct:.0f}%) — projects too hard for a lullaby; may feel 'daytime'")
else:
    notes.append(f"◦ Diffusion mix (near={report.near_field_pct:.0f}% mid={report.mid_field_pct:.0f}% far={report.far_field_pct:.0f}%)")

for n in notes:
    print(f"  {n}")

print()
print("=" * 78)
