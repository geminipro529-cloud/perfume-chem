"""Simplified photorealistic iris: 8 high-impact materials, 10 mL batch.

Keeps core iris photorealism:
- Alpha Irone (THE iris)
- Myristic Acid (orris-wax realism)
- Carrot Seed EO (natural iris-root bridge)
- Heliotropal (powdery lift)
- Hedione (radiance)
- Iso E Super (skin cocoon)
- Ethylene Brassylate (creamy musk)
- IPM (skin-feel solvent)

Scaled from full 33-material formula — the 8 selected cover ~80% of the
iris photorealism signal. Dropped: top-notes (Bergamot, Dihydromyrcenol,
Ethyl Linalool), accessory ionones, trace florals, multiple musks.
"""
import json

with open("_opt_final_iris.json") as f:
    full = json.load(f)

# Selected 8 materials. Amounts re-optimized for a 10 mL @ 15% mini-batch.
# Ratios preserved from full formula for the kept materials, then rescaled
# to hit 1500 µL concentrate total.
selected = [
    # (name, dilution, full_30mL_µL)
    ("Alpha Irone",         "30%",   730.0),  # iris core
    ("Myristic Acid",       "20%",   750.0),  # orris wax
    ("Carrot Seed EO",      "neat",   30.0),  # natural iris-root
    ("Heliotropal",         "neat",   40.0),  # powder lift
    ("Hedione",             "neat",  355.0),  # radiance
    ("Iso E Super",         "neat",  365.0),  # skin cocoon
    ("Ethylene Brassylate", "neat",  190.0),  # creamy musk
    ("IPM",                 "neat",  250.0),  # skin feel
]

kept_total = sum(v for _, _, v in selected)  # µL in 30 mL
# Scale to 10 mL at same concentration (15.02%) = 1502 µL concentrate
TARGET_10ML = 1502.0
scale = TARGET_10ML / kept_total

print(f"Kept materials total in 30 mL formula: {kept_total:.0f} µL")
print(f"Scale factor to 10 mL @ 15%: {scale:.4f}")
print()

lines = []
lines.append("# Photorealistic Iris — SIMPLIFIED (8 materials, 10 mL)")
lines.append("")
lines.append("**For spill refill or quick mini-batch.** Drops 25 supporting materials from the full formula but keeps the 8 that carry the photorealistic iris signal.")
lines.append("")
lines.append(f"**Batch:** 10 mL · concentrate {TARGET_10ML:.0f} µL (15.02%) · ethanol 96% {10000 - TARGET_10ML:.0f} µL")
lines.append("")
lines.append("| # | Material | Dilution | Amount (µL) | Role |")
lines.append("|--:|---|---|---:|---|")
roles = {
    "Alpha Irone": "Iris core — the signature",
    "Myristic Acid": "Orris-wax realism (natural root fattiness)",
    "Carrot Seed EO": "Natural iris-root bridge (soil-carrot depth)",
    "Heliotropal": "Powdery lift, joins iris to skin",
    "Hedione": "Radiance amplifier, opens up the iris",
    "Iso E Super": "Skin cocoon, molecular halo",
    "Ethylene Brassylate": "Creamy-lactonic musk base",
    "IPM": "Skin-feel solvent, smooths diffusion",
}
scaled = {}
for i, (name, dil, full_v) in enumerate(selected, 1):
    amt = round(full_v * scale, 1)
    scaled[name] = amt
    lines.append(f"| {i} | {name} | {dil} | {amt:.1f} | {roles[name]} |")

total = sum(scaled.values())
lines.append(f"| | **Concentrate total** | | {total:.0f} | |")
lines.append(f"| | **Ethanol 96%** | | {10000 - total:.0f} | |")
lines.append(f"| | **Final volume** | | 10,000 | |")
lines.append("")
lines.append("## Procedure")
lines.append("")
lines.append("1. In a clean 20 mL beaker, add materials in the order listed (macros → traces).")
lines.append("2. Add ethanol 96% to bring to 10 mL.")
lines.append("3. Stir 30 s, cap, rest 24–48 hr (maceration is important for iris — the waxes need time to integrate).")
lines.append("4. Pour into the bottle and swirl.")
lines.append("")
lines.append("## Smaller batches")
lines.append("")
lines.append("For a 5 mL refill, halve all amounts. For 7 mL, multiply by 0.7.")
lines.append("")
lines.append("| Material | Dilution | 5 mL (µL) | 7 mL (µL) | 10 mL (µL) |")
lines.append("|---|---|---:|---:|---:|")
for name, dil, full_v in selected:
    a10 = scaled[name]
    lines.append(f"| {name} | {dil} | {a10*0.5:.1f} | {a10*0.7:.1f} | {a10:.1f} |")
lines.append(f"| **Concentrate** | | {total*0.5:.0f} | {total*0.7:.0f} | {total:.0f} |")
lines.append(f"| **Ethanol 96%** | | {5000 - total*0.5:.0f} | {7000 - total*0.7:.0f} | {10000 - total:.0f} |")
lines.append("")
lines.append("## What you're giving up vs the full 33-material formula")
lines.append("")
lines.append("- **Top notes** (Bergamot, Ethyl Linalool, Dihydromyrcenol): the opening will be quieter, more straight-to-iris. The simplified version skips the brief citrus-airy lift.")
lines.append("- **Accessory ionones** (Alpha, Beta, Dihydro Beta, Orivone): slightly less multidimensional iris — you lose some of the violet-backdrop shimmer around the Alpha Irone.")
lines.append("- **Musk chord** (Habanolide, Exaltolide, Ambrettolide, Musk Ketone): just Ethylene Brassylate carries all musk duty — less layered skin-trail.")
lines.append("- **Trace florals** (Ultralia, Cyclamen Aldehyde, Farnesol, Cis Jasmone): no floral halo around the iris.")
lines.append("")
lines.append("**Net:** ~80–85% of the photorealistic iris effect, ~25% of the work.")

out = "\n".join(lines)
with open("formulas/collections/Photorealistic_Iris_SIMPLIFIED_10mL.md", "w", encoding="utf-8") as f:
    f.write(out)
print(out)
