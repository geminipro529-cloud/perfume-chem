#!/usr/bin/env python3
"""Check gate status from a pipeline JSON output."""
import json, sys
if len(sys.argv) < 2:
    print("Usage: python scripts/check_gates.py <pipeline.json> [--details]")
    sys.exit(1)
f = sys.argv[1]
show_detail = "--details" in sys.argv
d = json.load(open(f, encoding="utf-8"))
gates = d["formulas"][0]["gates"]
p = sum(1 for g in gates if g.get("status") == "PASS")
w = sum(1 for g in gates if g.get("status") == "WARN")
fc = sum(1 for g in gates if g.get("status") == "FAIL")
fails = [(g.get("gate","?"), (g.get("message") or "")[:80]) for g in gates if g.get("status") == "FAIL"]
print(f"{p} PASS | {w} WARN | {fc} FAIL")
if show_detail:
    for name, msg in fails:
        print(f"  FAIL {name}: {msg}")
else:
    for name, _ in fails:
        print(f"  FAIL {name}")
