with open('engine/ingredient_intelligence.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

corrections = [
    ("Azarbre", 0.003, 4.3),
]

for mat, old, new in corrections:
    target_key = f'"{mat}":'
    in_target = False
    for i, line in enumerate(lines):
        if target_key in line:
            in_target = True
            continue
        if in_target and '"vp":' in line:
            parts = line.split('"vp":')
            before = parts[0] + '"vp": '
            after_vp = parts[1]
            import re
            m = re.match(r'([\d.]+)(.*)', after_vp.strip())
            if m:
                current_val = float(m.group(1))
                if abs(current_val - old) < 0.01:
                    lines[i] = before + str(new) + m.group(2) + '\n'
                    print(f'OK: {mat} vp {old} -> {new}')
                else:
                    print(f'SKIP: {mat} vp is {current_val}')
                break

with open('engine/ingredient_intelligence.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
