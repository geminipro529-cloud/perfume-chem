import json, sys

raw = open(sys.argv[1], "rb").read()
text = (
    raw[2:].decode("utf-16-le", errors="replace")
    if raw[:2] == b"\xff\xfe"
    else raw.decode("utf-8", errors="replace")
)
idx = text.find('{"formulas"')
if idx < 0:
    print("No formulas")
    sys.exit(1)
brace = text.rfind("{", 0, idx)
d = json.loads(text[brace:])
fm = d["formulas"][0]
print("Formula:", fm["name"])
print("Overall:", fm["status"])
gs = [(g["gate"], g["status"]) for g in fm["gates"]]
p = sum(1 for _, s in gs if s == "PASS")
w = sum(1 for _, s in gs if s == "WARN")
f = sum(1 for _, s in gs if s == "FAIL")
print(f"Gates: {p}P/{w}W/{f}F ({len(gs)} total)")
for g in fm["gates"]:
    if g["status"] == "FAIL":
        print(f"  FAIL: {g['gate']} - {g['detail'][:120]}")
nd = fm.get("formula_state", {}).get("note_distribution", {})
print(
    f"Note dist: T:{nd.get('top', 0):.1f}% H:{nd.get('heart', 0):.1f}% B:{nd.get('base', 0):.1f}%"
)
