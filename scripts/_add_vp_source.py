"""
One-shot script: add vp_source: null field to every material entry
across all data/materials/*.yaml files.

Checkbox #73 of Plan v5.
"""

import csv
import glob
import os
import re

YAML_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "materials")
OUTPUT_CSV = os.path.join(
    os.path.dirname(__file__), "..", ".opencode", "cache", "vp_source_audit.csv"
)

NEW_LINE = (
    "  vp_source: null  # NIST, EPI, PubChem_exp, PubChem_pred, ingredient_intelligence, UNKNOWN\n"
)

files = sorted(glob.glob(os.path.join(YAML_DIR, "*.yaml")))
print(f"Found {len(files)} YAML files")

total_materials = 0
total_modified = 0
csv_rows = []

for filepath in files:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    modified = False
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Match vp_25c_pa line at material entry level (2-space indent)
        if re.match(r"^  vp_25c_pa:", line):
            # Check if next line is already vp_source (idempotency)
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("vp_source:"):
                # Already has vp_source - skip insertion
                pass
            else:
                new_lines.append(NEW_LINE)
                modified = True
                total_modified += 1

        i += 1

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"  MODIFIED: {os.path.basename(filepath)}")

    # Count materials in this file (entries starting with "- canonical_name:")
    material_count = sum(1 for line in lines if re.match(r"^- canonical_name:", line))
    total_materials += material_count

    # Build CSV rows
    current_name = None
    current_vp = None
    for line in new_lines:
        m = re.match(r"^- canonical_name: (.+)", line)
        if m:
            current_name = m.group(1)
            current_vp = None
        m = re.match(r"^  vp_25c_pa: (.+)", line)
        if m and current_name:
            vp_val = m.group(1).strip()
            current_vp = vp_val
        m = re.match(r"^  vp_source: (.+)", line)
        if m and current_name:
            csv_rows.append(
                {
                    "canonical_name": current_name,
                    "vp_25c_pa": current_vp or "",
                    "vp_source": "null",
                    "file": os.path.basename(filepath),
                }
            )
            current_name = None
            current_vp = None

# Write CSV report
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["canonical_name", "vp_25c_pa", "vp_source", "file"])
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"\nTotal materials: {total_materials}")
print(f"Materials modified (vp_source added): {total_modified}")
print(f"CSV rows: {len(csv_rows)}")
print(f"CSV written to: {OUTPUT_CSV}")
