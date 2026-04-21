"""Dump synergy rules, pairing rules, and material properties relevant to inventory."""
import sys, json, sqlite3

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DB = str(Path(ROOT) / "perfume_chem.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1. All pairing rules
pairs = conn.execute("SELECT material_a_name, material_b_name, effect, rule_type, source FROM pairing_rules").fetchall()
print(f"\n=== PAIRING RULES ({len(pairs)} total) ===")
for r in pairs:
    print(f"  {r['material_a_name']:25s} + {r['material_b_name']:25s}  | {r['rule_type']:10s} | {r['effect']}")

# 2. All synergy rules (non-corrupted)
syns = conn.execute("SELECT material_a_name, material_b_name, effect, ratio, rule_type, source FROM synergy_rules WHERE is_corrupted=0").fetchall()
print(f"\n=== SYNERGY RULES ({len(syns)} total) ===")
for r in syns:
    print(f"  {r['material_a_name']:25s} + {r['material_b_name']:25s}  | ratio={r['ratio'] or 'N/A':6s} | {r['rule_type']:10s} | {r['effect']}")

# 3. Material properties (just the key fields for formula design)
mats = conn.execute("""SELECT name, odor_family, carles_position, 
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


    roudnitska_function, jellinek_quadrant, sar_class,
    mw, bp, vp, clp, odt, best_with
    FROM materials ORDER BY name""").fetchall()
print(f"\n=== MATERIAL PROPERTIES ({len(mats)} materials) ===")
for m in mats:
    bw = m['best_with'] or ''
    if bw and bw.startswith('['):
        try:
            bw = ', '.join(json.loads(bw)[:5])
        except:
            pass
    print(f"  {m['name']:30s} | family={str(m['odor_family'] or '?'):15s} "
          f"| carles={str(m['carles_position'] or '?'):15s} "
          f"| roudnitska={str(m['roudnitska_function'] or '?'):15s} "
          f"| jellinek={str(m['jellinek_quadrant'] or '?'):20s} "
          f"| MW={m['mw'] or '?'} BP={m['bp'] or '?'} VP={m['vp'] or '?'} "
          f"| best_with=[{bw[:80]}]")

# 4. Theory frameworks
theories = conn.execute("SELECT name, rules_json FROM theory_frameworks").fetchall()
print(f"\n=== THEORY FRAMEWORKS ({len(theories)} total) ===")
for t in theories:
    rules = t['rules_json']
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except:
            pass
    print(f"\n  {t['name']}:")
    if isinstance(rules, dict):
        for k, v in list(rules.items())[:10]:
            print(f"    {k}: {v}")

conn.close()
