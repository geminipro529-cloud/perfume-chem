"""Analyze vetiver full pipeline results and print formatted analysis."""
import json
from pathlib import Path

data = json.loads(Path("perplexity changes/vetiver_full_pipeline.json").read_text("utf-8"))
stages = {st["name"]: st for st in data["stages"]}
s = data["summary"]

print("=" * 80)
print("  VETIVER CLASSIQUE — FULL PIPELINE ANALYSIS")
print("=" * 80)

# Repair log
print("\n--- REPAIR LOG ---")
for run in data.get("repair_runs", []):
    icon = "\u2705" if run["status"] == "PASS" else "\u26a0" if run["status"] == "WARN" else "\u2716"
    print(f"  Pass #{run['pass']}: {icon} {run['status']}")
    for fix in run["fixes"]:
        print(f"    -> {fix}")

# Final status
print(f"\n  Final status: {data['overall_status']}  |  Readiness: {data['commercial_readiness']}")
print(f"  Family: {data['resolved_family']}  |  Archetype: {data['archetype_key']}")
print(f"  Materials: {s['materials']}  |  Perceptible: {s['perceptible_count']}")
print(f"  Total vapor: {s['total_vapor_ppm']} ppm")
nd = s.get("note_distribution", {})
print(f"  T/H/B: {nd.get('top',0):.0f}/{nd.get('heart',0):.0f}/{nd.get('base',0):.0f}")
if "oav_contrast_sigma_log" in s:
    print(f"  OAV contrast: {s['oav_contrast_sigma_log']} (sigma-log)")
if "oav_max" in s:
    print(f"  OAV range: {s.get('oav_min',0):.2f} to {s.get('oav_max',0):.0f}")

# OAV headspace table
oav_stage = stages.get("oav_computation", {})
oav_table = oav_stage.get("data", {}).get("oav_table", [])
if oav_table:
    print("\n" + "=" * 80)
    print("  OAV HEADSPACE TABLE (sorted by OAV descending)")
    print("=" * 80)
    header = f"{'Material':24s} {'Dil':>5s} {'Raw uL':>8s} {'Act uL':>8s} {'MW':>6s} {'MF%':>6s} {'VP Pa':>7s} {'\u03b3':>5s} {'Vap ppm':>9s} {'ODT ppm':>9s} {'OAV':>10s} {'Note':>6s}"
    print(header)
    print("-" * 102)
    mats = sorted(oav_table, key=lambda m: float(m.get("oav", 0) or 0), reverse=True)
    total_ppm = 0
    for m in mats:
        oav = m.get("oav", 0) or 0
        odt = m.get("odt_air_ppm", 0) or 0
        mf = m.get("mole_fraction", 0) * 100
        mw = m.get("mw_g_mol", m.get("mole_fraction", 0) and 200 or 200) or 200
        print(f"  {m['name']:22s} {m['dilution']:>5.2f} {m['raw_ul']:>8.1f} {m['active_ul']:>8.2f} {mw:>6.0f} {mf:>5.2f} {m['vp_pa']:>7.3f} {m.get('gamma',1):>5.2f} {m['vapor_ppm']:>9.4f} {odt:>9.6f} {oav:>10.1f} {m['note']:>6s}")
        total_ppm += m["vapor_ppm"]
    print("-" * 102)
    print(f"  {'TOTAL':22s} {'':>5s} {sum(m['raw_ul'] for m in mats):>8.1f} {'':>14s} {'':>6s} {'':>7s} {'':>5s} {total_ppm:>9.4f} {'':>9s} {'':>10s}")

# Note distribution
print("\n" + "=" * 80)
print("  NOTE DISTRIBUTION (OAV-weighted)")
print("=" * 80)
tiers = {"top": [], "heart": [], "base": []}
for m in mats:
    n = m.get("note", "heart")
    if n in tiers:
        tiers[n].append(m)
for tier in ("top", "heart", "base"):
    mt = tiers[tier]
    total_oav = sum(float(m.get("oav", 0) or 0) for m in mt) or 1
    total_act = sum(m["active_ul"] for m in mt)
    print(f"  {tier.upper()}: {len(mt)} mats, {total_act:.0f} uL active, {total_oav:.0f} total OAV")
    for m in mt[:5]:
        o = m.get("oav", 0) or 0
        pct = o / total_oav * 100
        bar = "#" * max(1, int(pct / 5))
        print(f"    {m['name']:25s} OAV={o:>8.1f} ({pct:4.0f}%) {bar}")

# Sub-threshold
sub = oav_stage.get("data", {}).get("sub_threshold_materials", [])
if sub:
    print("\n--- SUB-THRESHOLD (OAV < 1) ---")
    for m in sub:
        print(f"  {m['name']:25s} OAV={m['oav']:.2f}  role={m['role']}  active={m['active_ul']:.1f} uL")

# Temporal evolution
temporal_stage = stages.get("temporal_simulation", {})
windows = temporal_stage.get("data", {}).get("windows", [])
if windows:
    print("\n" + "=" * 80)
    print("  TEMPORAL EVOLUTION (5 windows)")
    print("=" * 80)
    wh = f"{'Window':15s} {'Time':>8s} {'Vap ppm':>9s} {'Raw uL':>8s} {'T/H/B':>15s}  Leaders"
    print(wh)
    print("-" * 100)
    for w in windows:
        nd = w.get("note_distribution", {})
        doms = w.get("dominant_oav", [])
        ldrs = ", ".join(f"{d['material'][:15]}({d['oav']:.0f})" for d in doms[:3])
        print(f"  {w['label']:15s} {w['t_seconds']:>8.0f}s {w['total_vapor_ppm']:>9.2f} {w['total_active_ul']:>8.0f} {nd.get('top',0):>4.0f}/{nd.get('heart',0):>4.0f}/{nd.get('base',0):>4.0f}  {ldrs}")

    # Receptor
    print("\n--- RECEPTOR ACTIVATION (opening) ---")
    ra = windows[0].get("receptor_activation", {})
    for rec, val in sorted(ra.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {rec}: {val:.1%}")

# Performance projection
oav_intel = stages.get("oav_intelligence", {})
perf_proj = oav_intel.get("data", {}).get("performance_projection", {})
if perf_proj:
    warns = perf_proj.get("warnings", [])
    if warns:
        print("\n--- CLIMATE WARNINGS (Bangkok 35C) ---")
        for w_ in warns:
            print(f"  {w_}")
    print("\n--- HALF-LIFE PROJECTIONS ---")
    for m in perf_proj.get("materials", []):
        bs = m.get("bangkok_shift", {})
        print(f"  {m['material']:25s} Paris {m['paris_half_life_min']:>5.0f}min  Bangkok {bs.get('bangkok_half_life_min_est',0):>5.0f}min  VP {bs.get('vp_ratio',0):.1f}x")

# Gate results
print("\n" + "=" * 80)
print("  GATE RESULTS")
print("=" * 80)
for st in data["stages"]:
    icon = "\u2705" if st["status"] == "PASS" else "\u26a0" if st["status"] == "WARN" else "\u2716"
    print(f"  {icon} {st['name']:30s} {st['status']:5s}  {st['detail'][:120]}")

# Repair suggestions
rep = stages.get("repair_suggestions", {})
sugs = rep.get("data", {}).get("suggestions", [])
if sugs:
    print("\n--- SUGGESTIONS ---")
    for s_ in sugs:
        print(f"  -> {s_}")
