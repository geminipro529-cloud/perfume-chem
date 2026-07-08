with open('engine/ingredient_intelligence.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

reclassifications = [
    ("Birch Tar Rectified",      "base",   "top"),
    ("Bergamot FCF oil Sicilian", "top",   "heart"),
    ("Hedione",                  "heart",  "base"),
    ("Alpha Irone",              "heart",  "base"),
    ("Cedarwood EO",             "base",   "top"),
    ("Lavender EO",              "top",    "heart"),
    ("Aurantiol",                "heart",  "base"),
    ("Terpinyl Acetate",         "heart",  "base"),  # borderline, VP 0.40 Pa
]

for mat, old_note, new_note in reclassifications:
    target_key = f'"{mat}":'
    in_target = False
    found = False
    for i, line in enumerate(lines):
        if target_key in line:
            in_target = True
            continue
        if in_target and '"note":' in line:
            # Replace the note value
            old_pattern = f'"note": "{old_note}"'
            new_pattern = f'"note": "{new_note}"'
            if old_pattern in line:
                lines[i] = line.replace(old_pattern, new_pattern)
                print(f'OK: {mat} {old_note} -> {new_note}')
                found = True
            else:
                print(f'SKIP: {mat} note line: {line.strip()}')
            break
    if not found and in_target:
        print(f'FAIL: {mat} — note field not found')

# Cardamom EO — needs "note": "top" but it might not have a note field
# Let me check
for i, line in enumerate(lines):
    if '"Cardamom EO":' in line:
        for j in range(i, min(i+5, len(lines))):
            if '"note":' in lines[j]:
                print(f'Cardamom EO note: {lines[j].strip()}')
                break
        break

with open('engine/ingredient_intelligence.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
