import json

cats = {}
with open(".omo/evidence/truths.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('{"_meta"'):
            continue
        try:
            obj = json.loads(line)
            cat = obj.get("category", "?")
            cats[cat] = cats.get(cat, 0) + 1
        except:
            pass
for c, n in sorted(cats.items()):
    print(f"{c}: {n}")
print(f"TOTAL: {sum(cats.values())}")
