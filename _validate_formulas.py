"""Validate formulas 8A, 10A, 20A from Perfume Wheel collection."""
import re
from pathlib import Path

# --- Load inventory ---
inv_path = Path("inventory.txt")
inv_text = inv_path.read_text(encoding="utf-8")
inventory_names = set()
inventory_names_lower = {}

for line in inv_text.splitlines():
    match = re.match(r"- (.+?)(?:\s+#.*)?$", line.strip())
    if not match:
        continue
    name = match.group(1).strip()
    inventory_names.add(name)
    # Case-insensitive index
    name_lower = name.lower()
    if name_lower not in inventory_names_lower:
        inventory_names_lower[name_lower] = name
    # Add without dilution suffix
    name_no_dil = re.sub(r"\s*\(\d+%\s*(?:in\s+\w+)?\)\s*$", "", name)
    name_no_dil = re.sub(r"\s*\(\d+%\s*w/v.*?\)\s*$", "", name_no_dil)
    name_no_dil = re.sub(r"\s*\(\d+%\s*in\s+[\w\s]+\)\s*$", "", name_no_dil)
    if name_no_dil != name:
        inventory_names.add(name_no_dil)
        nl = name_no_dil.lower()
        if nl not in inventory_names_lower:
            inventory_names_lower[nl] = name_no_dil

def find_in_inventory(mat_name):
    """Check if material exists in inventory (case-insensitive, handles dilutions)."""
    if mat_name in inventory_names:
        return True
    # Try lowercase exact
    mat_lower = mat_name.lower()
    if mat_lower in inventory_names_lower:
        return True
    # Try without trailing parenthetical
    mat_base = re.sub(r"\s*\(.*?\)\s*$", "", mat_name).strip()
    if mat_base in inventory_names:
        return True
    if mat_base.lower() in inventory_names_lower:
        return True
    # Try removing (neat), (pure powder) suffix
    mat_simple = mat_name.replace(" (neat)", "").replace(" (pure powder)", "").strip()
    if mat_simple in inventory_names:
        return True
    if mat_simple.lower() in inventory_names_lower:
        return True
    # Try with parentheses removed from base
    mat_clean = re.sub(r"\s*\(.*?\)", "", mat_name).strip()
    if mat_clean in inventory_names:
        return True
    if mat_clean.lower() in inventory_names_lower:
        return True
    return False


# --- Parse markdown ---
md_path = Path("formulas/collections/Perfume_Wheel_Full_22x3_Thai_Mass_Pleasing_2026-05-02.md")
md_text = md_path.read_text(encoding="utf-8")

sections = list(re.finditer(r"^##\s+(\d+[A-Z])\.\s+(.+)$", md_text, re.MULTILINE))

targets = {"8A", "10A", "20A"}
formula_data = {}

for i, m in enumerate(sections):
    code = m.group(1)
    if code not in targets:
        continue
    name = m.group(2).strip()
    start = m.end()
    end = sections[i + 1].start() if i + 1 < len(sections) else len(md_text)
    body = md_text[start:end]

    # Stated concentrate
    conc_match = re.search(r"\*\*Concentrate:\*\*\s*(\d+)\s*%\s*\w+,\s*([\d,]+)\s*µL", body)
    stated_conc_pct = int(conc_match.group(1)) if conc_match else None
    stated_total_ul = int(conc_match.group(2).replace(",", "")) if conc_match else None

    # Parse table with simple column-count approach
    materials = []
    total_from_table = None
    in_table = False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "Layer" in stripped and "Material" in stripped:
            in_table = True
            continue
        if not in_table:
            continue
        if "---" in stripped:
            continue
        if "**Total**" in stripped:
            # | **Total** | | | | **6,290** |
            m_total = re.search(r"\*\*([\d,]+)\*\*", stripped)
            if m_total:
                total_from_table = int(m_total.group(1).replace(",", ""))
            continue
        # Extract last | number | from row
        m_val = re.search(r"\|\s*([\d.]+)\s*\|$", stripped)
        if not m_val:
            continue
        ul_val = float(m_val.group(1))

        # Extract columns
        cells = [c.strip() for c in stripped.split("|")]
        cells = [c for c in cells if c]  # remove empty strings from edges
        # Expected: [Layer, #, Material, Dilution, µL] or [#, Material, Dilution, µL]
        if len(cells) >= 4:
            num_str = cells[-4]  # The # column
            mat = cells[-3]      # Material
            dil = cells[-2]      # Dilution
            try:
                num = int(num_str)
            except ValueError:
                # Layer was in first column, shift
                if len(cells) >= 5:
                    num = int(cells[-4])
                    mat = cells[-3]
                    dil = cells[-2]
                else:
                    continue
            materials.append((num, mat, dil, ul_val))

    formula_data[code] = {
        "name": name,
        "stated_total": stated_total_ul,
        "stated_conc_pct": stated_conc_pct,
        "total_from_table": total_from_table,
        "materials": materials,
    }

# --- Validate and print ---
print("PERFUME WHEEL FORMULA VALIDATION REPORT")
print("=" * 80)
print(f"File: Perfume_Wheel_Full_22x3_Thai_Mass_Pleasing_2026-05-02.md")
print(f"Inventory: {len([n for n in inventory_names if ' in ' not in n.lower() and ') ' not in n.lower()])} unique materials")
print()

all_issues = []

for code in ["8A", "10A", "20A"]:
    f = formula_data[code]
    print(f"## Formula {code}: {f['name']}")
    print(f"   Concentrate: {f['stated_conc_pct']}%, Stated total: {f['stated_total']} uL")
    print(f"   Table row count: {len(f['materials'])} materials")
    print()

    # MATH CHECK
    calc_total = sum(m[3] for m in f["materials"])
    print(f"   Stated concentrate: {f['stated_total']:>6} uL")
    print(f"   Table Total row:    {f['total_from_table'] or 'N/A':>6} uL")
    print(f"   Actual sum:         {calc_total:>6.0f} uL")

    math_issues = []
    if f["stated_total"] is not None and abs(calc_total - f["stated_total"]) > 1:
        diff = calc_total - f["stated_total"]
        math_issues.append(f"Stated total ({f['stated_total']}) != calculated ({calc_total:.0f}), delta {diff:+.0f}")
        all_issues.append(f"{code}: MATH ERROR - stated {f['stated_total']} uL vs actual {calc_total:.0f} uL (diff {diff:+.0f})")
    if f["total_from_table"] is not None and abs(calc_total - f["total_from_table"]) > 1:
        diff = calc_total - f["total_from_table"]
        math_issues.append(f"Table total ({f['total_from_table']}) != calculated ({calc_total:.0f}), delta {diff:+.0f}")

    if math_issues:
        for issue in math_issues:
            print(f"   ** {issue}")
    else:
        print(f"   Math: PASS")

    # INVENTORY CHECK
    not_in_inv = []
    for num, mat, dil, ul in f["materials"]:
        if not find_in_inventory(mat):
            not_in_inv.append((num, mat))

    if not_in_inv:
        print(f"\n   NOT IN INVENTORY ({len(not_in_inv)}):")
        for num, mat in not_in_inv:
            print(f"      #{num}: {mat}")
            all_issues.append(f"{code}: NOT IN INVENTORY - #{num} {mat}")
    else:
        print(f"\n   Inventory check: PASS ({len(f['materials'])}/187 inventory items)")

    # DILUTION CHECK
    dil_issues = []
    for num, mat, dil, ul in f["materials"]:
        mat_lower = mat.lower()

        # Check Calone neat
        if "calone" in mat_lower and dil.lower() in ("neat", "", "pure"):
            dil_issues.append(f"#{num} {mat}: neat ({ul:.0f} uL) — typical use is 1%")
        # Check Scentenal neat
        if "scentenal" in mat_lower and dil.lower() in ("neat", "", "pure"):
            dil_issues.append(f"#{num} {mat}: neat ({ul:.0f} uL) — typical use is 1%")
        # Check Geosmin
        if "geosmin" in mat_lower and dil.lower() in ("neat", "", "pure"):
            dil_issues.append(f"#{num} {mat}: neat ({ul:.0f} uL) — should be 1% or lower")

    if dil_issues:
        print(f"\n   DILUTION CONCERNS ({len(dil_issues)}):")
        for c in dil_issues:
            print(f"      {c}")
            all_issues.append(f"{code}: DILUTION - {c}")
    else:
        print(f"\n   Dilution check: PASS")

    # IFRA CHECK
    ifra_issues = []
    for num, mat, dil, ul in f["materials"]:
        mat_lower = mat.lower()
        dil_lower = dil.lower()
        product_ml = 30.0

        # ACA: IFRA <=0.1% in Cat 4 (30 uL neat per 30mL)
        if "amyl cinnamic" in mat_lower:
            if dil_lower in ("neat", "", "pure") and ul > 30:
                pct = ul / (product_ml * 1000) * 100
                ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL neat = {pct:.3f}% in product (IFRA limit 0.1%)")

        # Cinnamaldehyde: IFRA <=0.05%
        if "cinnamaldehy" in mat_lower:
            if dil_lower in ("neat", "", "pure") and ul > 15:
                pct = ul / (product_ml * 1000) * 100
                ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL neat = {pct:.3f}% in product (IFRA limit 0.05%)")

        # Eugenol (not isoeugenol): IFRA <=0.5% Cat 4
        if "eugenol" in mat_lower and "isoeugenol" not in mat_lower:
            if dil_lower in ("neat", "", "pure") and ul > 150:
                pct = ul / (product_ml * 1000) * 100
                ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL neat = {pct:.3f}% in product (IFRA limit 0.5%)")

        # Birch Tar: IFRA <=0.002%
        if "birch tar" in mat_lower:
            if dil_lower in ("neat", "", "pure"):
                pct = ul / (product_ml * 1000) * 100
                if pct > 0.002:
                    ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL neat = {pct:.4f}% in product (IFRA limit 0.002%)")
            elif "1%" in dil_lower:
                pct = ul * 0.01 / (product_ml * 1000) * 100
                if pct > 0.002:
                    ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL at 1% = {pct:.4f}% active (IFRA limit 0.002%)")

        # Farnesol: IFRA restricted
        if "farnesol" in mat_lower and dil_lower in ("neat", "", "pure") and ul > 30:
            ifra_issues.append(f"#{num} {mat}: {ul:.0f} uL neat — Farnesol IFRA-restricted, low dose only")

        # Lilial: IFRA-banned
        if "lilial" in mat_lower:
            ifra_issues.append(f"#{num} {mat}: Lilial is IFRA-BANNED (49th Amendment)")

    if ifra_issues:
        print(f"\n   IFRA CONCERNS ({len(ifra_issues)}):")
        for c in ifra_issues:
            print(f"      {c}")
            all_issues.append(f"{code}: IFRA - {c}")
    else:
        print(f"\n   IFRA check: PASS")

    print()

# Summary
print("=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)

if not all_issues:
    print("No issues found across all 3 formulas.")
else:
    errors = [i for i in all_issues if "MATH ERROR" in i]
    warnings = [i for i in all_issues if "MATH ERROR" not in i]
    print(f"Total issues found: {len(all_issues)}")
    print(f"  Critical (math errors): {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print()
    for issue in all_issues:
        marker = "[CRITICAL]" if "MATH ERROR" in issue else "[WARNING]"
        print(f"  {marker} {issue}")

print()
print("Note: Math errors imply the stated concentrate total doesn't match the sum")
print("of individual materials. The likely cause is that the Total row was")
print("auto-generated and not recalculated after material adjustments.")
