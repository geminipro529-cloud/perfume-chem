"""Analyze V2 results."""
import json
from pathlib import Path

d = json.loads(Path("perplexity changes/vetiver_v2_results.json").read_text("utf-8"))
s = d["summary"]
st = {x["name"]: x for x in d["stages"]}
oav = st["oav_computation"]["data"]["oav_table"]
mats = sorted(oav, key=lambda m: float(m.get("oav", 0) or 0), reverse=True)

print("REPAIR LOG")
for r in d.get("repair_runs", []):
    print(f"  Pass #{r['pass']}: {r['status']}")
    for f in r["fixes"]:
        print(f"    -> {f}")

print(f"\nStatus: {d['overall_status']}  Family: {d['resolved_family']}")
print(f"Mats: {s['materials']}  Perceptible: {s['perceptible_count']}  Vapor: {s['total_vapor_ppm']} ppm")
nd = s.get("note_distribution", {})
print(f"T/H/B: {nd.get('top',0):.0f}/{nd.get('heart',0):.0f}/{nd.get('base',0):.0f}")
if "oav_contrast_sigma_log" in s:
    print(f"OAV contrast: {s['oav_contrast_sigma_log']}")

print(f"\n{'Material':28s} {'Raw%':>6s} {'Act%':>6s} {'OAV':>10s} {'Note':>6s} {'VP Pa':>7s}")
print("-"*63)
for m in mats:
    pct = m["raw_ul"] / sum(x["raw_ul"] for x in mats) * 100
    apct = m["active_ul"] / sum(x["active_ul"] for x in mats) * 100
    o = m.get("oav", 0) or 0
    print(f"{m['name']:28s} {pct:>5.1f}% {apct:>5.1f}% {o:>10.1f} {m['note']:>6s} {m['vp_pa']:>7.3f}")

print("\n--- KEY MATERIALS ---")
for key in ["ambrox super", "vetiver eo", "vetiver", "geraniol", "tobacco", "hedione"]:
    for m in mats:
        if key in m["name"].lower():
            print(f"  {m['name']:25s} OAV={m.get('oav',0):>8.1f}  active={m['active_ul']:>6.1f}uL")
            break

# Family fit
fam = st.get("family_fit", {})
if fam.get("status") == "FAIL":
    print("\n--- FAMILY FAILURES ---")
    for c in fam["data"].get("checks", []):
        if c["status"] == "FAIL":
            print(f"  {c['name']}: {c['detail']}")

# Gate summary
print("\n--- GATES ---")
for x in d["stages"]:
    ico = "\u2705" if x["status"] == "PASS" else "\u26a0" if x["status"] == "WARN" else "\u2716"
    print(f"  {ico} {x['name']:30s} {x['status']:5s} {x['detail'][:100]}")
