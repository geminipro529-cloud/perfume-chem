"""Generate spill-refill mini-batches for Photorealistic Iris at 5/7/10 mL."""
import json, math

with open("_opt_final_iris.json") as f:
    data = json.load(f)

ing = data["ingredients"]
dil = data["dilutions"]
BATCH = 30.0  # mL
CONC_TOTAL = sum(ing.values())  # µL
CONC_PCT = CONC_TOTAL / (BATCH * 1000) * 100

volumes = [5.0, 7.0, 10.0]

lines = []
lines.append("# Photorealistic Iris — Spill Refill Mini-Batches")
lines.append("")
lines.append(f"**30 mL formula:** concentrate = {CONC_TOTAL:.0f} µL ({CONC_PCT:.2f}%), ethanol = {BATCH*1000 - CONC_TOTAL:.0f} µL")
lines.append("")
lines.append("Mix the mini-batch, macerate 24–48 hr, pour into the existing bottle, swirl gently.")
lines.append("")

# Table header
header = "| # | Material | Dilution |" + "".join(f" {int(v)} mL spill (µL) |" for v in volumes)
sep    = "|--:|---|---|" + "".join(" ---: |" for _ in volumes)
lines.append(header)
lines.append(sep)

def fmt(x):
    if x < 1.0:
        return f"{x:.2f}"
    if x < 10:
        return f"{x:.1f}"
    return f"{round(x):.0f}"

for i, (name, amt) in enumerate(ing.items(), 1):
    d = dil.get(name, 1.0)
    dstr = "neat" if d == 1.0 else f"{int(d*100)}%"
    cells = [fmt(amt * v / BATCH) for v in volumes]
    lines.append(f"| {i} | {name} | {dstr} | " + " | ".join(cells) + " |")

# Totals row
lines.append("| | **Concentrate total** | | " +
             " | ".join(fmt(CONC_TOTAL * v / BATCH) for v in volumes) + " |")
lines.append("| | **Ethanol 96%** | | " +
             " | ".join(fmt((BATCH*1000 - CONC_TOTAL) * v / BATCH) for v in volumes) + " |")
lines.append("| | **Final volume** | | " +
             " | ".join(f"{int(v)*1000:,} µL" for v in volumes) + " |")

lines.append("")
lines.append("## Notes")
lines.append("- Amounts < 1 µL → use a 10% pre-dilution in DPG or skip (trace contribution only).")
lines.append("- Add in the order listed (macros → traces).")
lines.append("- Materials already at dilution (e.g. Alpha Irone 30%) — these µL values ARE of the dilution, not neat. Use the dilution from your stock.")
lines.append("- Final concentrate % in the mini-batch = 15.02% (matches parent 30 mL formula).")

out = "\n".join(lines)
with open("formulas/collections/Photorealistic_Iris_SPILL_REFILL.md", "w", encoding="utf-8") as f:
    f.write(out)
print(out)
