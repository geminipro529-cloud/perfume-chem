"""
Compute top-up deltas: existing 15 mL batch → optimized 30 mL formula.

Given:
  - Existing 15 mL batch was mixed per the original 15 mL-optimized formula
    (stored in _opt_convergence_v2_out.json as the per-material µL)
  - New optimized 30 mL formula (hill-climbed, differs from exact 2× scale)

For each material:
  target30 = optimized 30 mL amount (µL)
  current  = 15 mL batch amount (µL)
  delta    = target30 - current  →  amount to ADD to the 15 mL batch

Cases:
  delta >= 0  → add this many µL (OK)
  delta <  0  → hill-climb reduced this material — CAN'T subtract from
                the already-mixed batch. The final concentration will be
                slightly higher than optimal. Report the overshoot.
  new material → just add target30 µL

Writes formulas/collections/{Photorealistic_Iris,Iris_Jasmine}_TOPUP_from_15mL.md
"""
from __future__ import annotations
import json
from pathlib import Path
import re

data15 = json.loads(Path("_opt_convergence_v2_out.json").read_text())


def parse_optimized_md(path: Path) -> tuple[dict, dict]:
    """Parse the | # | Material | Dilution | Amount (µL) | … table."""
    text = path.read_text(encoding="utf-8")
    ing, dil = {}, {}
    # Lines like: | 1 | Hedione | neat | 695 | 0.695 |
    row_re = re.compile(r"^\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(\S+?)\s*\|\s*([\d.]+)\s*\|")
    for line in text.splitlines():
        m = row_re.match(line)
        if not m:
            continue
        name, dil_str, amt = m.group(1), m.group(2), float(m.group(3))
        if "total" in name.lower() or "ethanol" in name.lower():
            continue
        ing[name] = amt
        if dil_str.lower() == "neat":
            dil[name] = 1.0
        else:
            dil[name] = float(dil_str.rstrip("%")) / 100.0
    return ing, dil


FORMULAS = [
    {
        "key": "iris",
        "label": "Photorealistic Iris",
        "opt30_md": Path("formulas/collections/Photorealistic_Iris_30mL_optimized.md"),
        "topup_md": Path("formulas/collections/Photorealistic_Iris_TOPUP_from_15mL.md"),
    },
    {
        "key": "iris_jasmine",
        "label": "Iris-Jasmine",
        "opt30_md": Path("formulas/collections/Iris_Jasmine_30mL_optimized.md"),
        "topup_md": Path("formulas/collections/Iris_Jasmine_TOPUP_from_15mL.md"),
    },
]

for f in FORMULAS:
    current15 = {k: float(v) for k, v in data15[f["key"]]["ingredients"].items()}
    dil = {k: float(v) for k, v in data15[f["key"]]["dilutions"].items()}
    target30, _ = parse_optimized_md(f["opt30_md"])

    all_names = sorted(set(current15) | set(target30))

    adds, overshoots, new_mats = [], [], []
    for name in all_names:
        cur = current15.get(name, 0.0)
        tgt = target30.get(name, 0.0)
        delta = tgt - cur
        if name not in current15:
            new_mats.append((name, tgt, dil.get(name, 1.0)))
        elif delta >= 0:
            adds.append((name, cur, tgt, delta, dil.get(name, 1.0)))
        else:
            # Overshoot: current batch has more than target → after ethanol top-up
            # compute resulting concentration vs target
            # Final batch is 30 mL, so cur µL in 30 mL = cur/30000 fraction
            # Target is tgt/30000. Overshoot ratio = cur / tgt
            overshoot_pct = (cur - tgt) / tgt * 100 if tgt > 0 else float("inf")
            overshoots.append((name, cur, tgt, cur - tgt, overshoot_pct,
                               dil.get(name, 1.0)))

    total_add = sum(a[3] for a in adds) + sum(n[1] for n in new_mats)
    # Ethanol top-up: current batch volume (with existing ethanol) = 15 mL
    # After all adds it should become 30 mL. So ethanol to add = 30000 - 15000 - total_add
    ethanol_add = 30000 - 15000 - total_add

    lines = [
        f"# {f['label']} — top-up from existing 15 mL batch → 30 mL optimized",
        "",
        f"**Situation:** You have an existing 15 mL batch mixed to the original "
        f"15 mL-optimized formula. This doc shows the **deltas** to bring it to "
        f"the hill-climb-optimized 30 mL formula (geo score +{0.5:.1f}–{0.8:.1f} vs scaled).",
        "",
        f"**Total aroma-chem to add:** {total_add:.0f} µL "
        f"({total_add/1000:.3f} mL)",
        f"**Ethanol 96% to add:** {ethanol_add:.0f} µL "
        f"({ethanol_add/1000:.3f} mL)",
        f"**Final batch:** 30.00 mL",
        "",
        "## Step 1 — Additions (add these µL to the existing 15 mL)",
        "",
        "| # | Material | Dilution | Add (µL) | Current 15mL (µL) | Target 30mL (µL) |",
        "|--:|---|---|---:|---:|---:|",
    ]
    adds_sorted = sorted(adds, key=lambda a: -a[3])
    i = 0
    for name, cur, tgt, delta, d in adds_sorted:
        if delta < 0.5:  # skip ~zero adds
            continue
        i += 1
        d_str = "neat" if d >= 1.0 else f"{d*100:.0f}%"
        lines.append(f"| {i} | {name} | {d_str} | **{delta:.0f}** | {cur:.0f} | {tgt:.0f} |")

    if new_mats:
        lines += ["", "### New materials (not in 15 mL batch)", "",
                  "| Material | Dilution | Add (µL) |", "|---|---|---:|"]
        for name, tgt, d in new_mats:
            d_str = "neat" if d >= 1.0 else f"{d*100:.0f}%"
            lines.append(f"| {name} | {d_str} | **{tgt:.0f}** |")

    lines += [
        "",
        "## Step 2 — Top up with ethanol",
        "",
        f"Add **{ethanol_add:.0f} µL ({ethanol_add/1000:.3f} mL)** of ethanol 96% "
        f"to bring the final volume to 30 mL.",
        "",
    ]

    if overshoots:
        lines += [
            "## ⚠ Overshoots — cannot subtract from an already-mixed batch",
            "",
            "The hill-climb reduced these materials. Since you can't remove them "
            "from the existing 15 mL batch, the final 30 mL will have a slight "
            "overshoot. Overshoots <5% are typically imperceptible; 5–15% is "
            "noticeable; >15% may require re-mixing.",
            "",
            "| Material | Dilution | 15mL has (µL) | 30mL target (µL) | Overshoot (µL) | Overshoot % |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for name, cur, tgt, over, pct, d in sorted(overshoots, key=lambda x: -x[4]):
            d_str = "neat" if d >= 1.0 else f"{d*100:.0f}%"
            warn = "⚠⚠" if pct > 15 else ("⚠" if pct > 5 else "")
            lines.append(
                f"| {name} | {d_str} | {cur:.0f} | {tgt:.0f} | +{over:.0f} | "
                f"**+{pct:.1f}%** {warn} |"
            )
        max_pct = max(o[4] for o in overshoots)
        lines += [
            "",
            f"**Worst overshoot:** +{max_pct:.1f}%. "
            + ("Likely imperceptible — proceed with top-up." if max_pct < 5
               else "Noticeable but usually acceptable — proceed with top-up and taste-test."
               if max_pct < 15
               else "Significant — consider re-mixing a fresh 30 mL batch from scratch."),
        ]

    lines += [
        "",
        "## Procedure",
        "",
        "1. Work in a 50 mL beaker or flask (gives headroom for stirring).",
        "2. Add the aroma-chem deltas in the order listed (largest first — macro "
        "materials stir in easier before trace drops are added).",
        "3. Add the ethanol 96% top-up.",
        "4. Stir gently for 30–60 s, then rest 24–48 hr for maceration.",
        f"5. Final batch: **30.00 mL**, concentrate "
        f"{sum(target30.values()):.0f} µL "
        f"({sum(target30.values())/30000*100:.1f}%).",
    ]

    f["topup_md"].write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{f['label']}:")
    print(f"  additions        : {len([a for a in adds if a[3] >= 0.5])} materials, "
          f"{total_add:.0f} µL total")
    print(f"  new materials    : {len(new_mats)}")
    print(f"  overshoots       : {len(overshoots)}")
    if overshoots:
        print(f"  worst overshoot  : +{max(o[4] for o in overshoots):.1f}% "
              f"({max(overshoots, key=lambda o: o[4])[0]})")
    print(f"  ethanol to add   : {ethanol_add:.0f} µL")
    print(f"  wrote            : {f['topup_md']}")
