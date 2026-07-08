"""F1 Le Barbier de Grasse — 30 mL finished EDP at 20% concentrate in ethanol.

Rescales the validated 30 mL concentrate recipe to a 6 mL concentrate aliquot,
then prints the full 30 mL bottle: 6 mL concentrate (built from 17 materials)
+ 24 mL perfumer's ethanol.
"""
import json, pathlib

src = json.loads(pathlib.Path("_F1_30mL_recipe.json").read_text())
# rows are µL for a 30 mL concentrate batch. Scale to 6 mL concentrate (20% of 30 mL EDP).
SCALE = 6.0 / 30.0   # 0.2
EDP_ML = 30.0
CONC_ML = 6.0
ETHANOL_ML = EDP_ML - CONC_ML

# Mixing-order groups (base / heart / top) per the published recipe.
ORDER = {
    "Coumarin": (1, "Base"),
    "Ethylene Brassylate": (1, "Base"),
    "Galaxolide": (1, "Base"),
    "Vanillin": (1, "Base"),
    "Ambrox Super": (1, "Base"),
    "Cedarwood EO": (1, "Base"),
    "Patchouli EO": (1, "Base"),
    "Vetiver EO": (1, "Base"),
    "Evernyl": (1, "Base"),
    "Hexyl Salicylate": (1, "Base"),
    "Hedione": (2, "Heart"),
    "Iso E Super": (2, "Heart"),
    "Lavender EO": (2, "Heart"),
    "Linalyl Acetate": (2, "Heart"),
    "Geraniol": (2, "Heart"),
    "Eugenol": (2, "Heart"),
    "Bergamot FCF": (3, "Top"),
}

rows = []
for r in src["rows"]:
    mat = r["mat"]
    uL_30 = r["inv_uL_30mL"]
    uL_edp = round(uL_30 * SCALE)
    rows.append({
        "stage": ORDER[mat][0],
        "stage_name": ORDER[mat][1],
        "mat": mat,
        "form": r["form"],
        "uL": uL_edp,
        "mL": round(uL_edp / 1000.0, 3),
    })

# Sort: stage, then descending µL within stage
rows.sort(key=lambda x: (x["stage"], -x["uL"]))

# Adjust rounding so concentrate sums to exactly 6000 µL
total_uL = sum(r["uL"] for r in rows)
diff = 6000 - total_uL
if diff != 0:
    # Apply the diff to the largest concentrate row (Coumarin 20%)
    rows[0]["uL"] += diff
    rows[0]["mL"] = round(rows[0]["uL"] / 1000.0, 3)
    total_uL = sum(r["uL"] for r in rows)

print(f"\n{'='*78}")
print(f" F1 Le Barbier de Grasse — 30 mL FINISHED EDP @ 20% in ethanol")
print(f"{'='*78}")
print(f" Concentrate aliquot : {CONC_ML:.2f} mL  ({int(CONC_ML*1000)} µL)")
print(f" Perfumer's ethanol  : {ETHANOL_ML:.2f} mL  ({int(ETHANOL_ML*1000)} µL)")
print(f" Total bottle        : {EDP_ML:.2f} mL  ({int(EDP_ML*1000)} µL)")
print(f"{'='*78}")

stage_totals = {1: 0, 2: 0, 3: 0}
last_stage = 0
print(f" {'#':>2}  {'Material':<22} {'Form':<14} {'µL':>6}   {'mL':>6}")
print(f" {'-'*2}  {'-'*22} {'-'*14} {'-'*6}   {'-'*6}")
for i, r in enumerate(rows, 1):
    if r["stage"] != last_stage:
        print(f"\n -- Stage {r['stage']}: {r['stage_name']} --")
        last_stage = r["stage"]
    stage_totals[r["stage"]] += r["uL"]
    print(f" {i:>2}  {r['mat']:<22} {r['form']:<14} {r['uL']:>6}   {r['mL']:>6.3f}")

print(f"\n{'-'*78}")
for s, name in [(1, "Base"), (2, "Heart"), (3, "Top")]:
    print(f"  Stage {s} ({name}) subtotal : {stage_totals[s]:>5} µL  ({stage_totals[s]/1000:.3f} mL)")
print(f"{'-'*78}")
print(f"  Concentrate total      : {total_uL:>5} µL  ({total_uL/1000:.3f} mL)  [target 6000]")
print(f"  + Ethanol              : {int(ETHANOL_ML*1000):>5} µL  ({ETHANOL_ML:.3f} mL)")
print(f"  = Finished EDP         : {total_uL + int(ETHANOL_ML*1000):>5} µL  ({(total_uL + int(ETHANOL_ML*1000))/1000:.3f} mL)")

assert total_uL == 6000, f"Concentrate µL ≠ 6000 (got {total_uL})"
assert total_uL + int(ETHANOL_ML*1000) == 30000, "Bottle total ≠ 30000 µL"
print("\nAll volume checks passed ✓")

pathlib.Path("_F1_30mL_EDP_recipe.json").write_text(json.dumps({
    "EDP_mL": EDP_ML, "concentrate_mL": CONC_ML, "ethanol_mL": ETHANOL_ML,
    "concentration_pct": 20, "rows": rows,
}, indent=2))
print("\nWrote _F1_30mL_EDP_recipe.json")
