"""Optimize Iris Rêverie Lactée v7h against the new OAV-space objective.

Strategy:
  • bounds = ±30 % around current dose (perfumer-realistic moves)
  • hard caps on IFRA-restricted materials: Bourgeonal ≤4, Hydroxycitronellal ≤500,
    Isoeugenol ≤10, Beta Ionone ≤60 (anosmia), Carrot Seed EO ≤210 (brief)
  • hard floor on Hedione (≥1700) and salicylate cushion (Hexyl Sal ≥200)
  • Ethanol locked (solvent)
  • Target envelope built from the BRIEF, not from the current snapshot:
      top    : citrus 25, floral  8
      heart  : violet 25, powder 12, muguet  8, floral  6, lactone 3, anisic 3
      base   : wood    6, musk    3, amber   2, balsamic 3, vanilla 2, indolic 0.4
  • Degraded mode (single snapshot reused across windows) — trajectory ODE
    not yet glued in
"""
from __future__ import annotations

from engine.thermo.headspace import headspace_from_wt_pct
from engine.perception.oav import oav_profile
from engine.optimizer.oav_objective import OAVObjective, differential_evolution_oav

# Reuse the analysis script's data tables verbatim
from _analyze_iris_reverie_v7h import (
    ACTIVE_UL, MW, VP25, HSP, ODT_PPM, FAMILY,
)

# ---------------------------------------------------------------------------
# Bounds (µL active in 50 mL).  Will convert to wt% at scoring time.
# ---------------------------------------------------------------------------
HARD_CAPS: dict[str, tuple[float, float]] = {
    # IFRA category-4 / anosmia / brief caps
    "Bourgeonal":          (0,    4),
    "Hydroxycitronellal":  (0,  500),
    "Isoeugenol":          (0,   10),
    "Beta Ionone":         (0,   60),
    "Carrot Seed EO":      (0,  210),
    # Brief floors (lower bound)
    "Hedione":             (1700, 2200),
    "Hexyl Salicylate":    (200,  300),
    # Solvent locked
    "Ethanol":             (35070, 35070),
}

def _bounds_for(name: str, current: float) -> tuple[float, float]:
    if name in HARD_CAPS:
        return HARD_CAPS[name]
    lo = max(0.0, current * 0.7)
    hi = current * 1.3 if current > 0 else 1.0
    # Don't let traces vanish
    if current > 0 and current < 5:
        lo = current * 0.5
        hi = current * 1.5
    return (lo, hi)

MATERIALS = list(ACTIVE_UL.keys())
BOUNDS = [_bounds_for(m, ACTIVE_UL[m]) for m in MATERIALS]

# ---------------------------------------------------------------------------
# Headspace fn: ul-active dict → per-window OAV-profile snapshot
# ---------------------------------------------------------------------------
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
    # Same snapshot for top/heart/base (degraded mode); the family-targeted
    # objective will still differentiate because envelope targets differ.
    return {"top": snap, "heart": snap, "base": snap}

# Brief-aligned envelope (NOT cloned from current state)
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

# Baseline score
baseline_score = 0.0
from engine.optimizer.oav_objective import score_formula_oav
baseline_score = score_formula_oav(ACTIVE_UL, obj)

print("=" * 78)
print("OPTIMIZING Iris Rêverie Lactée v7h against brief envelope")
print("=" * 78)
print(f"  Materials        : {len(MATERIALS)}")
print(f"  Hard-capped      : {sum(1 for m in MATERIALS if m in HARD_CAPS)}")
print(f"  Free-moving      : {sum(1 for m in MATERIALS if m not in HARD_CAPS)}")
print(f"  Baseline score   : {baseline_score:+.3f}")
print()

best_wt, best_score = differential_evolution_oav(
    obj, maxiter=80, popsize=20, seed=42,
)
print(f"  Optimized score  : {best_score:+.3f}")
print(f"  Δ score          : {best_score - baseline_score:+.3f}")
print()

# ---------------------------------------------------------------------------
# Deltas — what did the optimizer want to change?
# ---------------------------------------------------------------------------
print("=" * 78)
print("DOSE DELTAS  (>10 µL change OR >15 % move)")
print("=" * 78)
print(f"{'material':28s} {'now':>8s} {'opt':>8s} {'Δµl':>8s} {'%':>7s}  cap?")
rows = []
for m in MATERIALS:
    now = ACTIVE_UL[m]
    opt = best_wt[m]
    if now == 0 and opt == 0:
        continue
    d = opt - now
    pct = (d / now * 100) if now else 100
    rows.append((abs(d), m, now, opt, d, pct))

rows.sort(reverse=True)
for absd, m, now, opt, d, pct in rows:
    if absd < 10 and abs(pct) < 15:
        continue
    cap = "HARD" if m in HARD_CAPS else ""
    arrow = "↑" if d > 0 else "↓"
    print(f"{m:28s} {now:8.1f} {opt:8.1f} {d:+8.1f} {pct:+6.1f}% {arrow} {cap}")

# ---------------------------------------------------------------------------
# Family axis comparison
# ---------------------------------------------------------------------------
def family_sums(ul_active):
    snap = headspace_fn(ul_active)["top"]
    out = {}
    for mat, m in snap.items():
        fam = FAMILY.get(mat, "default")
        out[fam] = out.get(fam, 0.0) + m["oav"]
    return out

now_sums = family_sums(ACTIVE_UL)
opt_sums = family_sums(best_wt)

print()
print("=" * 78)
print("FAMILY-OAV AXIS  (now → optimized)  [target envelope summed]")
print("=" * 78)
target_sums = {}
for win in TARGET_ENVELOPE.values():
    for fam, t in win.items():
        target_sums[fam] = target_sums.get(fam, 0.0) + t
all_fams = sorted(set(now_sums) | set(opt_sums) | set(target_sums))
print(f"{'family':14s} {'now':>10s} {'opt':>10s} {'target':>10s} {'Δ':>10s}")
for f in all_fams:
    n, o, t = now_sums.get(f, 0.0), opt_sums.get(f, 0.0), target_sums.get(f, 0.0)
    print(f"{f:14s} {n:10.2f} {o:10.2f} {t:10.2f} {o - n:+10.2f}")

# ---------------------------------------------------------------------------
# Brief-fit summary
# ---------------------------------------------------------------------------
def axis(sums, fams):
    return sum(sums.get(f, 0.0) for f in fams)

iris_now  = axis(now_sums, ("violet", "powder"))
iris_opt  = axis(opt_sums, ("violet", "powder"))
rooty_now = now_sums.get("earthy", 0.0)
rooty_opt = opt_sums.get("earthy", 0.0)
musk_now  = now_sums.get("musk", 0.0)
musk_opt  = opt_sums.get("musk", 0.0)
wood_now  = now_sums.get("wood", 0.0)
wood_opt  = opt_sums.get("wood", 0.0)

print()
print("=" * 78)
print("BRIEF-FIT")
print("=" * 78)
print(f"  Iris/powder axis    : {iris_now:6.2f}  →  {iris_opt:6.2f}")
print(f"  Rooty axis          : {rooty_now:6.2f}  →  {rooty_opt:6.2f}")
print(f"  Wood (skin halo)    : {wood_now:6.2f}  →  {wood_opt:6.2f}")
print(f"  Musk (skin halo)    : {musk_now:6.2f}  →  {musk_opt:6.2f}")
print(f"  Iris : Rooty ratio  : {iris_now/(rooty_now+1e-6):5.1f}× → "
      f"{iris_opt/(rooty_opt+1e-6):5.1f}×")
