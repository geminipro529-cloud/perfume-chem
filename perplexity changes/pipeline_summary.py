"""Print a human-readable summary of pipeline_results.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / "pipeline_results.json"
data = json.loads(path.read_text(encoding="utf-8"))

print("=" * 80)
print("  PERFUME PIPELINE ORCHESTRATOR — RESULTS SUMMARY")
print("=" * 80)

for key, v in data.items():
    s = v["summary"]
    stages = v["stages"]
    fails = [st for st in stages if st["status"] == "FAIL"]
    warns = [st for st in stages if st["status"] == "WARN"]
    passes = [st for st in stages if st["status"] == "PASS"]

    print(f"\n{'=' * 70}")
    print(f"  {key}")
    print(f"  {v['formula_name']}")
    print(f"{'=' * 70}")
    print(f"  Status:          {v['overall_status']}")
    print(f"  Readiness:       {v['commercial_readiness']}")
    print(f"  Family:          {v['resolved_family']}")
    print(f"  Archetype:       {v['archetype_key']}")
    print(f"  Materials:       {s['materials']}")
    print(f"  Perceptible:     {s['perceptible_count']}")
    print(f"  Total vapor:     {s['total_vapor_ppm']} ppm")
    nd = s.get("note_distribution", {})
    print(f"  T/H/B:           {nd.get('top','?')}/{nd.get('heart','?')}/{nd.get('base','?')}")

    if "oav_contrast_sigma_log" in s:
        print(f"  OAV contrast:    {s['oav_contrast_sigma_log']} (sigma-log)")
    if "oav_max" in s:
        print(f"  OAV range:       {s.get('oav_min',0):.2f} to {s.get('oav_max',0):.0f}")
    if "evaporation_pct" in s:
        print(f"  Evaporation:     {s['evaporation_pct']}% over 4h")
    if "vapor_decay" in s:
        print(f"  Vapor decay:     {s['vapor_decay']}% over 4h")

    print(f"\n  Stages: {len(passes)} PASS, {len(warns)} WARN, {len(fails)} FAIL")

    for f in fails:
        print(f"    \u2716 FAIL [{f['name']}]: {f['detail'][:130]}")
    for w in warns:
        print(f"    \u26a0 WARN [{w['name']}]: {w['detail'][:130]}")

    print()
