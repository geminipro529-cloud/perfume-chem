import json

raw = open("ws_stdout4.txt", "rb").read()
text = raw[2:].decode("utf-16-le", errors="replace")
idx = text.index('"formulas":')
brace = text.rfind("{", 0, idx)
d = json.loads(text[brace:])
f = d["formulas"][0]
print("Overall:", f["status"])
gs = [(g["gate"], g["status"]) for g in f["gates"]]
p = sum(1 for _, s in gs if s == "PASS")
w = sum(1 for _, s in gs if s == "WARN")
fail = sum(1 for _, s in gs if s == "FAIL")
print(f"Gates: {p}P/{w}W/{fail}F")
for g in f["gates"]:
    if g["status"] == "FAIL":
        print(f"  FAIL: {g['gate']} - {g.get('detail', '')[:140]}")
nd = f.get("formula_state", {}).get("note_distribution", {})
print(
    f"Notes: T:{nd.get('top', 0):.0f}% H:{nd.get('heart', 0):.0f}% B:{nd.get('base', 0):.0f}%"
)
conf = f.get("confidence", {})
print(
    f"Confidence: {conf.get('combined_grade', '?')} ({conf.get('combined_confidence', 0):.0f})"
)
