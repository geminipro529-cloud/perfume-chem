import re
from pathlib import Path

md_path = Path("formulas/collections/Perfume_Wheel_Full_22x3_Thai_Mass_Pleasing_2026-05-02.md")
md_text = md_path.read_text(encoding="utf-8")

sections = list(re.finditer(r"^##\s+(\d+[A-Z])\.\s+(.+)$", md_text, re.MULTILINE))

inv_path = Path("inventory.txt")
inv_text = inv_path.read_text(encoding="utf-8")
inv_names = set()
for line in inv_text.splitlines():
    m = re.match(r"- (.+?)(?:\s+#.*)?$", line.strip())
    if m:
        inv_names.add(m.group(1).strip().lower())

targets = ["1A", "8A", "10A", "13A", "17A", "20A"]
header = f"{'Formula':>8}  {'Rows':>5}  {'Table Total':>12}  {'Calc Sum':>10}  {'Delta':>8}  {'Delta%':>8}  {'Inventory':>12}"
print(header)
print("-" * len(header))

for i, m in enumerate(sections):
    code = m.group(1)
    if code not in targets:
        continue
    name = m.group(2).strip()
    start = m.end()
    end = sections[i + 1].start() if i + 1 < len(sections) else len(md_text)
    body = md_text[start:end]

    calc, count = 0, 0
    table_total = None
    in_table = False
    missing = []

    for line in body.splitlines():
        s = line.strip()
        if "Layer" in s and "Material" in s:
            in_table = True
            continue
        if not in_table:
            continue
        if "---" in s:
            continue
        if "**Total**" in s:
            mt = re.search(r"\*\*([\d,]+)\*\*", s)
            if mt:
                table_total = int(mt.group(1).replace(",", ""))
            continue
        mv = re.search(r"\|\s*([\d.]+)\s*\|$", s)
        if not mv:
            continue
        calc += float(mv.group(1))
        count += 1
        # Inventory check
        cells = [c.strip() for c in s.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 3:
            mat = cells[-3]
            mat_lower = mat.lower()
            if mat_lower in inv_names:
                continue
            mat_base = re.sub(r"\s*\(.*?\)$", "", mat_lower).strip()
            if mat_base in inv_names:
                continue
            if mat_lower not in [x.lower() for x in missing]:
                missing.append(mat)

    delta = calc - (table_total or 0)
    delta_pct = (delta / table_total * 100) if table_total else 0
    inv_status = f"{len(missing)} missing" if missing else "OK"
    print(f"{code:>8}  {count:>5}  {str(table_total or 'N/A'):>12}  {calc:>10.0f}  {delta:>+8.0f}  {delta_pct:>+7.1f}%  {inv_status:>12}")
    if missing:
        for mat_name in missing:
            print(f"         MISSING: {mat_name}")
