"""Add-only optimizer for Iris Rêverie Lactée v7h.

Physical constraint: batch is already mixed.  You can ADD material, never
remove.  Two materials currently unavailable (lock at current dose):
  • Hedione HC      → arriving later, locked at 800 µL
  • Alpha Irone     → arriving later, locked at 375 µL

For everything else: lo = current dose, hi = current * 1.30 (or *1.50 for
traces < 5 µL).  Hard upper caps (IFRA / anosmia / brief) still binding.

After optimization, materials are ranked by SCORE-IMPROVEMENT-PER-µL added,
so the user knows which top-ups matter most when materials arrive in waves.
"""
from __future__ import annotations

from engine.thermo.headspace import headspace_from_wt_pct
from engine.perception.oav import oav_profile
from engine.optimizer.oav_objective import (
    OAVObjective, differential_evolution_oav, score_formula_oav,
)
from _analyze_iris_reverie_v7h import (
    ACTIVE_UL, MW, VP25, HSP, ODT_PPM, FAMILY,
)

# Currently unavailable — lock at current dose
UNAVAILABLE = {"Hedione HC", "Alpha Irone"}

# Hard upper caps (IFRA / anosmia / brief)
HARD_UPPER = {
    "Bourgeonal":          4.0,
    "Hydroxycitronellal":  500.0,
    "Isoeugenol":          10.0,
    "Beta Ionone":         60.0,
    "Carrot Seed EO":      210.0,
    "Hexyl Salicylate":    300.0,
    "Hedione":             2200.0,
}

ETHANOL_LOCKED = 35070.0  # solvent stays put for now

def _bounds_for(name: str, current: float) -> tuple[float, float]:
    # Unavailable materials: locked at current dose
    if name in UNAVAILABLE:
        return (current, current)
    if name == "Ethanol":
        return (ETHANOL_LOCKED, ETHANOL_LOCKED)
    # Add-only: lo = current, hi = current * 1.30 (or 1.50 for traces)
    lo = current
    if current > 0 and current < 5:
        hi = current * 1.50
    else:
        hi = current * 1.30 if current > 0 else 1.0
    # Apply hard upper cap if any
    if name in HARD_UPPER:
        hi = min(hi, HARD_UPPER[name])
        lo = min(lo, hi)  # if current already at/over cap, lo=hi (locked)
    return (lo, hi)

MATERIALS = list(ACTIVE_UL.keys())
BOUNDS = [_bounds_for(m, ACTIVE_UL[m]) for m in MATERIALS]

# Headspace fn (same as base optimizer)
def headspace_fn(ul_active: dict) -> dict:
    total_mass = sum(ul_active.values())
    wt = {n: 100.0 * v / total_mass for n, v in ul_active.items()}
    hs = headspace_from_wt_pct(
        wt, T_K=305.0, mw_table=MW, vp_table=VP25, hsp_table=HSP,
    )
    conc_ppm = {c.name: c.vapor_ppm for c in hs.values() if c.name in ODT_PPM}
    odt = {n: ODT_PPM[n] for n in conc_ppm}
    snap = oav_profile(conc_ppm, odt, FAMILY,
                       use_mixture_shift=True, beta=0.3)
    return {"top": snap, "heart": snap, "base": snap}

TARGET_ENVELOPE = {
    "top":   {"citrus": 25.0, "floral":  8.0},
    "heart": {"violet": 25.0, "powder": 12.0, "muguet":  8.0,
              "floral":  6.0, "lactone": 3.0, "anisic":  3.0},
    "base":  {"wood":    6.0, "musk":    3.0, "amber":   2.0,
              "balsamic": 3.0, "vanilla": 2.0, "indolic": 0.4},
}

obj = OAVObjective(
    materials=MATERIALS,
    bounds=BOUNDS,
    target_envelope=TARGET_ENVELOPE,
    headspace_fn=headspace_fn,
    families=FAMILY,
)

baseline_score = score_formula_oav(ACTIVE_UL, obj)

print("=" * 78)
print("ADD-ONLY OPTIMIZER  (Hedione HC + Alpha Irone LOCKED — not yet in stock)")
print("=" * 78)
locked = sum(1 for m in MATERIALS
             if BOUNDS[MATERIALS.index(m)][0] == BOUNDS[MATERIALS.index(m)][1])
print(f"  Materials             : {len(MATERIALS)}")
print(f"  Locked (no room)      : {locked}")
print(f"  Free to add           : {len(MATERIALS) - locked}")
print(f"  Baseline score        : {baseline_score:+.3f}")
print()

best_wt, best_score = differential_evolution_oav(
    obj, maxiter=80, popsize=20, seed=42,
)
print(f"  Optimized score       : {best_score:+.3f}")
print(f"  Δ score               : {best_score - baseline_score:+.3f}")
print()

# ---------------------------------------------------------------------------
# Per-material marginal impact: how much score does each top-up buy?
# Computed by reverting ONE material at a time to its baseline and
# re-scoring → impact = best_score - score_with_that_material_reverted.
# ---------------------------------------------------------------------------
print("=" * 78)
print("PRIORITY RANKING  —  add these first when materials arrive")
print("=" * 78)
print(f"{'rank':>4s} {'material':28s} {'now':>8s} {'add':>8s} "
      f"{'→':>8s} {'Δscore':>10s} {'Δs/µL':>8s}")

rows = []
for m in MATERIALS:
    now = ACTIVE_UL[m]
    opt = best_wt[m]
    add = opt - now
    if add < 0.5:  # locked or no meaningful add
        continue
    # Marginal: revert this single material, rescore
    test = dict(best_wt)
    test[m] = now
    s_without = score_formula_oav(test, obj)
    impact = best_score - s_without  # positive = adding it helped
    per_ul = impact / add if add > 0 else 0.0
    rows.append((per_ul, impact, m, now, add, opt))

# Sort by per-µL impact (best score gain per µL of material consumed)
rows.sort(reverse=True)
for rank, (per_ul, impact, m, now, add, opt) in enumerate(rows, 1):
    cap = " HARD" if m in HARD_UPPER else ""
    print(f"{rank:>4d} {m:28s} {now:8.1f} {add:+8.1f} {opt:8.1f} "
          f"{impact:+10.1f} {per_ul:+8.3f}{cap}")

# ---------------------------------------------------------------------------
# Total volume added
# ---------------------------------------------------------------------------
total_add = sum(r[4] for r in rows)
print()
print(f"  Total material added  : {total_add:.1f} µL")
print(f"  Batch grows from      : 50.00 mL → {(50000 + total_add)/1000:.2f} mL")

# ---------------------------------------------------------------------------
# Family axis
# ---------------------------------------------------------------------------
def family_sums(ul_active):
    snap = headspace_fn(ul_active)["top"]
    out = {}
    for mat, mm in snap.items():
        fam = FAMILY.get(mat, "default")
        out[fam] = out.get(fam, 0.0) + mm["oav"]
    return out

now_sums = family_sums(ACTIVE_UL)
opt_sums = family_sums(best_wt)
target_sums = {}
for win in TARGET_ENVELOPE.values():
    for fam, t in win.items():
        target_sums[fam] = target_sums.get(fam, 0.0) + t

print()
print("=" * 78)
print("FAMILY AXIS  (now → add-only opt → target)")
print("=" * 78)
print(f"{'family':14s} {'now':>10s} {'opt':>10s} {'target':>10s} {'Δ to tgt':>10s}")
for fam in sorted(set(now_sums) | set(opt_sums) | set(target_sums)):
    n = now_sums.get(fam, 0.0)
    o = opt_sums.get(fam, 0.0)
    t = target_sums.get(fam, 0.0)
    if t == 0 and max(n, o) < 0.5:
        continue
    print(f"{fam:14s} {n:10.2f} {o:10.2f} {t:10.2f} {o-t:+10.2f}")
