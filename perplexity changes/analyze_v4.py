"""Analyze V4 results."""
import json
from pathlib import Path

d = json.loads(Path("perplexity changes/vetiver_v4_results.json").read_text("utf-8"))
s = d["summary"]
st = {x["name"]: x for x in d["stages"]}
oav = st["oav_computation"]["data"]["oav_table"]
mats = sorted(oav, key=lambda m: float(m.get("oav", 0) or 0), reverse=True)

print("REPAIR LOG")
for r in d.get("repair_runs", []):
    icon = "\u2705" if r["status"]=="PASS" else "\u26a0" if r["status"]=="WARN" else "\u2716"
    print(f"  Pass #{r['pass']}: {icon} {r['status']}")
    for f in r["fixes"]:
        print(f"    -> {f}")

print(f"\nFINAL STATUS: {d['overall_status']}  |  {d['commercial_readiness']}")
print(f"Family: {d['resolved_family']}  |  Archetype: {d['archetype_key']}")
print(f"Materials: {s['materials']}  |  Perceptible: {s['perceptible_count']}")
print(f"Vapor: {s['total_vapor_ppm']} ppm")
nd = s.get("note_distribution", {})
print(f"T/H/B: {nd.get('top',0):.0f}/{nd.get('heart',0):.0f}/{nd.get('base',0):.0f}")
if "oav_contrast_sigma_log" in s:
    print(f"OAV contrast: {s['oav_contrast_sigma_log']}  |  Range: {s.get('oav_min',0):.2f} to {s.get('oav_max',0):.0f}")

print(f"\n{'Material':28s} {'Raw%':>6s} {'Act%':>6s} {'OAV':>10s} {'Note':>6s} {'VP Pa':>7s} {'ODT ppb':>9s}")
print("-"*73)
total_raw = sum(x["raw_ul"] for x in mats)
total_act = sum(x["active_ul"] for x in mats) or 1
for m in mats:
    pct = m["raw_ul"] / total_raw * 100
    apct = m["active_ul"] / total_act * 100
    o = m.get("oav", 0) or 0
    odt = m.get("odt_air_ppm", 0) or 0
    print(f"{m['name']:28s} {pct:>5.1f}% {apct:>5.1f}% {o:>10.1f} {m['note']:>6s} {m['vp_pa']:>7.3f} {odt*1000:>8.2f}")

# Sub-threshold
sub = st["oav_computation"]["data"].get("sub_threshold_materials", [])
if sub:
    print("\n--- SUB-THRESHOLD ---")
    for m in sub:
        print(f"  {m['name']:25s} OAV={m['oav']:.2f}  role={m['role']}  active={m['active_ul']:.1f}uL")

# Gate results
print("\n--- GATES ---")
for x in d["stages"]:
    icon = "\u2705" if x["status"] == "PASS" else "\u26a0" if x["status"] == "WARN" else "\u2716"
    print(f"  {icon} {x['name']:30s} {x['status']:5s}  {x['detail'][:120]}")

# Temporal
ts = st.get("temporal_simulation", {})
windows = ts.get("data", {}).get("windows", [])
if windows:
    print("\n--- TEMPORAL ---")
    for w in windows:
        n = w["note_distribution"]
        dom = w.get("dominant_oav", [])
        ldrs = ", ".join(f"{d['material'][:14]}({d['oav']:.0f})" for d in dom[:3])
        print(f"  {w['label']:15s} {w['t_seconds']:>6.0f}s  T/H/B: {n.get('top',0):>4.0f}/{n.get('heart',0):>4.0f}/{n.get('base',0):>4.0f}  {ldrs}")

# Key materials
print("\n--- KEY MATERIALS ---")
for key in ["ambrox super", "vetiver eo", "geraniol", "tobacco", "coumarin", "iso e super"]:
    for m in mats:
        if key in m["name"].lower():
            print(f"  {m['name']:25s} OAV={m.get('oav',0):>8.1f}  active={m['active_ul']:>6.1f}uL")
            break

# Family fit detail
fam = st.get("family_fit", {})
if fam.get("status") in ("FAIL", "WARN"):
    print("\n--- FAMILY FAILURES ---")
    for c in fam["data"].get("checks", []):
        if c["status"] != "PASS":
            print(f"  {c['name']:30s} {c['detail']}")

# IFRA detail
ifra = st.get("ifra_safety", {})
if ifra.get("status") in ("FAIL", "WARN"):
    print("\n--- IFRA ---")
    for v in ifra["data"].get("violation_details", []):
        print(f"  {v['material']:25s} at {v['active_pct_finished']:.3f}% (limit {v['effective_limit']:.3f}%)")
