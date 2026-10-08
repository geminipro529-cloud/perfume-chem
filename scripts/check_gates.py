#!/usr/bin/env python3
"""Check gate status from a pipeline JSON output."""
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python scripts/check_gates.py <pipeline.json> [--details]")
    sys.exit(1)
f = sys.argv[1]
show_detail = "--details" in sys.argv
d = json.load(open(f, encoding="utf-8"))
gates = d["formulas"][0]["gates"]
p = sum(1 for g in gates if g.get("status") == "PASS")
w = sum(1 for g in gates if g.get("status") == "WARN")
h = sum(1 for g in gates if g.get("status") == "HOLD")
fc = sum(1 for g in gates if g.get("status") == "FAIL")
fails = [
    (g.get("status"), g.get("gate", "?"), (g.get("message") or "")[:80])
    for g in gates
    if g.get("status") in ("FAIL", "HOLD")
]
print(f"{p} PASS | {w} WARN | {h} HOLD | {fc} FAIL")
if show_detail:
    for status, name, msg in fails:
        print(f"  {status} {name}: {msg}")
else:
    for status, name, _ in fails:
        print(f"  {status} {name}")
