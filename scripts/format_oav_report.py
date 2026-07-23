"""Clean OAV report from any pipeline output."""

import json
import sys

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = r"D:\chatbots\perfume-chem\output\chypre_time.json"

d = json.load(open(path, encoding="utf-8"))
f = d["formulas"][0]
ms = f["formula_state"]["materials"]
ts = f["time_series"]

BOLD = "\033[1m"
RESET = "\033[0m"

# ── Scores ──
scores = f.get("scores", {})
if scores:
    print(f"\n{BOLD}{'SCORES':─^50}{RESET}")
    print(
        f"  Total: {scores.get('total', '?'):.1f}  |  Hedonic: {scores.get('hedonic', '?'):.1f}  |  Luxury: {scores.get('luxury', '?'):.1f}"
    )
    print(
        f"  Sillage: {scores.get('sillage', '?'):.1f}  |  Longevity: {scores.get('longevity', '?'):.1f}"
    )
    print()

# ── Pyramid ──
nd = f["formula_state"]["note_distribution"]
print(f"{BOLD}{'PYRAMID':─^50}{RESET}")
print(f"  TOP ▄▄ {nd['top']:.0f}%    HEART ▄▄ {nd['heart']:.0f}%    BASE ▄▄ {nd['base']:.0f}%")
print(f"  Materials: {len(ms)} total")
print()

# ── OAV Rank ──
print(f"{BOLD}{'OAV RANKING':─^50}{RESET}")
print(f"  {'#':>2s} {'Material':<30s} {'OAV':>8s} {'Percept':>16s}")
print(f"  {'─' * 2} {'─' * 30} {'─' * 8} {'─' * 16}")
ranked = sorted(ms, key=lambda m: m["oav"] or 0, reverse=True)
for i, m in enumerate(ranked, 1):
    oav = m["oav"] or 0
    if oav < 1:
        break
    name = m["name"][:29]
    if m.get("role") == "anosmia-prone":
        percept = "(abstract)"
    elif oav > 1000:
        percept = "MASSIVE"
    elif oav > 100:
        percept = "very strong"
    elif oav > 50:
        percept = "strong"
    elif oav > 10:
        percept = "moderate"
    elif oav > 5:
        percept = "perceptible"
    else:
        percept = "at threshold"
    print(f"  {i:2d} {name:<30s} {oav:8.0f} {percept:>16s}")

# ── Time ──
print(f"\n{BOLD}{'TIME RELEASE':─^50}{RESET}")
for w in ts:
    label = w["label"]
    secs = w["t_seconds"]
    leaders = w["dominant_oav"][:3]
    mins = secs // 60 if secs >= 60 else f"{secs}s"
    if secs >= 3600:
        mins = f"{secs // 3600}h"
    elif secs >= 60:
        mins = f"{secs // 60}min"
    else:
        mins = f"{secs}s"
    names = " > ".join(f"{leader['name'][:16]}" for leader in leaders)
    print(f"  {label:12s} ({mins:>4s})  {names}")

# ── Sub-threshold ──
sub = [m for m in ms if (m["oav"] or 0) < 1]
if sub:
    print(f"\n{BOLD}{'SUB-THRESHOLD':─^50}{RESET}")
    for m in sub:
        role = m.get("role", "")
        status = "(structural — OK)" if role in ("fixative", "modifier") else "(check dosing)"
        print(f"  {m['name'][:30]:30s} OAV={m['oav']:.1f}  {status}")

# ── Gates FAIL/WARN ──
fail = [g for g in f["gates"] if g["status"] == "FAIL"]
warn = [g for g in f["gates"] if g["status"] == "WARN"]
if fail:
    print(f"\n{BOLD}{'GATES — FAIL':─^50}{RESET}")
    for g in fail:
        print(f"  {g['gate']:35s} {g.get('detail', '')[:80]}")
if warn:
    print(f"\n{BOLD}{'GATES — WARN':─^50}{RESET}")
    for g in warn[:10]:
        print(f"  {g['gate']:35s} {g.get('detail', '')[:80]}")
