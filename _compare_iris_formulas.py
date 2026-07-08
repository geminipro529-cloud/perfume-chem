"""Compare all Photorealistic Iris formula MD files — extract ingredients, dilutions, amounts."""
import re, os, glob, json

FILES = sorted(glob.glob("formulas/collections/Photorealistic_Iris*.md"))

def parse_md(path):
    """Pull | material | dil | amount | rows."""
    rows = []
    meta = {"conc_ul": None, "ethanol_ul": None, "batch_ml": None, "geo": None, "pct": None}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # Quick meta sniff
    m = re.search(r"[Cc]oncentrate[^|\n]*?(\d[\d,\.]*)\s*µL", text)
    if m: meta["conc_ul"] = float(m.group(1).replace(",", ""))
    m = re.search(r"[Ee]thanol[^|\n]*?(\d[\d,\.]*)\s*µL", text)
    if m: meta["ethanol_ul"] = float(m.group(1).replace(",", ""))
    m = re.search(r"(?:[Gg]eo|composite)[^\d]*(\d{2,3}\.\d+)", text)
    if m: meta["geo"] = float(m.group(1))
    m = re.search(r"(\d{1,2}\.\d{1,2})\s*%", text)
    if m: meta["pct"] = float(m.group(1))
    # Table rows: | # | Material | Dil | Amount (µL) | ...
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        # skip header/separator
        if set(cells[0]) <= set("-:"): continue
        if cells[0].lower() in ("#", "") and "material" in " ".join(c.lower() for c in cells):
            continue
        # try to find amount cell — first number after a material name
        # pattern: idx, material, dilution, amount...  OR material, dilution, amount
        try:
            num = int(cells[0])
            material = cells[1]
            rest = cells[2:]
        except (ValueError, IndexError):
            material = cells[0]
            rest = cells[1:]
        # find dilution + amount
        dil = None; amt = None
        for c in rest:
            if c.lower() in ("neat",) or re.match(r"^\d{1,3}\s*%$", c):
                dil = c.lower().replace(" ", "")
                break
        for c in rest:
            mm = re.match(r"^([\d,\.]+)\s*(µL|uL|mL|ml)?\s*$", c)
            if mm:
                v = float(mm.group(1).replace(",", ""))
                unit = (mm.group(2) or "µL").lower()
                if unit in ("ml",): v *= 1000
                amt = v
                break
        if material and amt is not None and len(material) > 2 and not material.lower().startswith(("concentrate", "ethanol", "final", "total", "batch")):
            rows.append((material, dil, amt))
    return meta, rows

formulas = {}
for p in FILES:
    name = os.path.basename(p).replace("Photorealistic_Iris_", "").replace(".md", "")
    meta, rows = parse_md(p)
    formulas[name] = {"meta": meta, "rows": rows, "path": p}

# All materials across all formulas
all_materials = set()
for f in formulas.values():
    for mat, _, _ in f["rows"]:
        all_materials.add(mat)

print(f"Found {len(formulas)} Photorealistic Iris formulas\n")
print(f"{'File':40s} {'Conc µL':>9s} {'EtOH µL':>9s} {'%':>5s} {'Geo':>7s} {'#mat':>5s}")
print("─" * 90)
for name, f in formulas.items():
    m = f["meta"]
    print(f"{name:40s} {str(m['conc_ul'] or ''):>9s} {str(m['ethanol_ul'] or ''):>9s} "
          f"{str(m['pct'] or ''):>5s} {str(m['geo'] or ''):>7s} {len(f['rows']):>5d}")

# Material-level comparison table: for each material, amount in each formula (normalized to 30 mL for comparability)
print("\n" + "═" * 110)
print("  PER-MATERIAL COMPARISON — amounts NORMALIZED to 30 mL equivalent (µL of dilution)")
print("═" * 110)

# Normalization factor for each formula (to 30 mL)
norms = {}
for name, f in formulas.items():
    # infer batch from filename if possible
    n = name.lower()
    if "7mL" in name or "7ml" in n: batch = 7.0
    elif "15mL" in name or "15ml" in n: batch = 15.0
    elif "30mL" in name or "30ml" in n: batch = 30.0
    elif "10mL" in name or "10ml" in n: batch = 10.0
    elif "spill" in n or "topup" in n or "top" in n:
        # multi-batch doc — skip normalization
        batch = None
    else:
        batch = None
    if batch:
        norms[name] = 30.0 / batch
    else:
        norms[name] = None

# Build material × formula matrix
name_order = list(formulas.keys())
header = "Material" + " " * 22
for n in name_order:
    short = n[:12]
    header += f"{short:>13s}"
print(header)
print("─" * len(header))

sorted_mats = sorted(all_materials)
for mat in sorted_mats:
    row = f"{mat[:28]:<30s}"
    for n in name_order:
        amts = [a for m, d, a in formulas[n]["rows"] if m == mat]
        if not amts:
            row += f"{'—':>13s}"
        else:
            amt = amts[0]
            norm = norms[n]
            if norm:
                amt_30 = amt * norm
                row += f"{amt_30:>13.1f}"
            else:
                row += f"{amt:>11.1f}* "
    print(row)

print("\n  * = raw µL (batch size not detected in filename — not normalized)")
print("  All other values = µL normalized to 30 mL equivalent for direct comparison.")

# Diff summary — are they the same formula?
print("\n" + "═" * 70)
print("  STRUCTURAL DIFF")
print("═" * 70)
# Pick the 30mL_optimized as canonical reference
ref_name = None
for n in name_order:
    if "30mL" in n:
        ref_name = n; break
if ref_name is None:
    ref_name = name_order[0]
print(f"  Reference: {ref_name}")
ref_mats = {m for m, _, _ in formulas[ref_name]["rows"]}

for n in name_order:
    if n == ref_name: continue
    mats = {m for m, _, _ in formulas[n]["rows"]}
    only_in_ref = ref_mats - mats
    only_in_this = mats - ref_mats
    common = ref_mats & mats
    tag = ""
    if not only_in_ref and not only_in_this:
        tag = "SAME SET"
    print(f"\n  {n}:")
    print(f"    common: {len(common)} · only in {ref_name}: {len(only_in_ref)} · only here: {len(only_in_this)} {tag}")
    if only_in_ref: print(f"    missing vs ref: {sorted(only_in_ref)}")
    if only_in_this: print(f"    added vs ref:   {sorted(only_in_this)}")
