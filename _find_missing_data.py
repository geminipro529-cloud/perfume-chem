import sys; sys.path.insert(0,'.')
from engine.ingredient_intelligence import _PROFILES as P
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

needs = []
for n in sorted(P.keys()):
    p = P[n]; r = normalize_name(n); od = ODT_DATA.get(r, {})
    vp = p.get('vp', None); odt = od.get('odt_air', None); mw = p.get('mw', None)
    if not vp or not odt or not mw:
        needs.append((n, vp, odt, mw))
        print(f"MISSING: {n} | VP={vp} | ODT={odt} | MW={mw}")
print(f"\nTotal: {len(needs)} materials with gaps")
print("\nNO VP:", [n for n,v,o,m in needs if not v])
print("\nNO ODT:", [n for n,v,o,m in needs if not o])
print("\nNO MW:", [n for n,v,o,m in needs if not m])
