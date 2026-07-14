"""Show drift limit values for V4 family fit."""
import json
from pathlib import Path

d = json.loads(Path("perplexity changes/vetiver_v4_results.json").read_text("utf-8"))
st = {x["name"]: x for x in d["stages"]}
fam = st["family_fit"]
print("ANCHOR CHECKS:")
for c in fam["data"].get("checks", []):
    print(f"  {c['status']:5s}  {c['name']:30s}  {c['detail']}")
