import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0
def mat(name):
    n = normalize_name(name)
    p = get_profile(name)
    odt = ODT_DATA.get(n,{}) or ODT_DATA.get(name.lower(),{})
    return p.vp if p and p.vp else 0, odt.get('odt_air')

def oav(a,v,o): return v*a*PPM/o if v and o else 0

formulas = {
    'I Bergamot (Dior+Creed)': [
        ('Bergamot FCF Sicilian',2900),('Linalyl Acetate',200),('Aurantiol',0.8),
        ('Hedione',1450),('Petitgrain EO',620),('Ethyl Linalool',600),('Hedione HC',180),('Paradisamide',3.5),
        ('Romandolide',500),('Iso E Super',480),('Vertofix',80),('Javanol',20),('Ambrofix',17.4),
        ('Ethylene Brassylate',413),('Ambrettolide',1.25),('Norlimbanol Dextro',45),('Vetival',43),('Cardamom EO',5),('Alpha Irone',0.45),
    ],
    'II Cedrat (Prada+Le Labo)': [
        ('Cedrat FCF Sicilian',3000),('Linalyl Acetate',200),
        ('Petitgrain EO',650),('Hedione',1300),('Hedione HC',160),('Paradisamide',3.5),
        ('Romandolide',480),('Iso E Super',380),('Kephalis',12),('Suederal',1.2),('Costus Olifac',0.5),
        ('Ambrofix',19.5),('Ethylene Brassylate',370),('Ambrettolide',1.25),('Norlimbanol Dextro',45),('Vetival',43),('Alpha Irone',0.45),
    ],
    'III Grapefruit (JM+Atelier)': [
        ('Grapefruit FCF',1950),('Linalyl Acetate',450),('Apritone',2),
        ('Hedione',1400),('Petitgrain EO',650),('Ethyl Linalool',550),('Floralozone',1.2),('Hedione HC',170),('Paradisamide',5.5),
        ('Romandolide',550),('Iso E Super',500),('Ambrofix',16.5),
        ('Ethylene Brassylate',380),('Ambrettolide',1.25),('Norlimbanol Dextro',45),('Vetival',43),('Cardamom EO',5),('Alpha Irone',0.45),
    ],
    'IV Lime (Hermes+Byredo)': [
        ('Lime Distilled EO',3100),('Linalyl Acetate',180),('Scentenal',0.1),
        ('Hedione',1300),('Petitgrain EO',680),('Floralozone',0.8),('Hedione HC',150),('Paradisamide',3.5),
        ('Romandolide',420),('Iso E Super',400),('Ambrofix',15.6),
        ('Ethylene Brassylate',330),('Ambrettolide',1.25),('Norlimbanol Dextro',45),('Vetival',80),('Cardamom EO',5),('Alpha Irone',0.45),
    ],
    'V Mandarin (TF+Malle)': [
        ('Red Mandarin EO',2600),('Linalyl Acetate',280),
        ('Hedione',1350),('Petitgrain EO',550),('Ethyl Linalool',480),('Hedione HC',180),('Paradisamide',3.5),('Dihydrojasmone',30),('Jasmine FO',60),
        ('Romandolide',520),('Iso E Super',500),('Benzoin Resinoid',17.5),
        ('Ambrofix',18),('Ethylene Brassylate',350),('Ambrettolide',2),('Norlimbanol Dextro',45),('Vetival',43),('Cardamom EO',5),('Alpha Irone',0.45),
    ],
}

data = {}
for label, mats in formulas.items():
    rows = []
    for name, active in mats:
        vp, odt = mat(name)
        rows.append(oav(active, vp, odt))
    total = sum(rows)
    ranked = sorted(rows, reverse=True)
    dom = sum(1 for o in rows if o >= 50)
    sub = sum(1 for o in rows if o < 1)
    data[label] = {'total':total, 'star':ranked[0], 'dom':dom, 'sub':sub, 'n':len(mats)}

print()
print(f"{'Metric':<28} {'I Bergamot':>13} {'II Cedrat':>13} {'III Grape':>13} {'IV Lime':>13} {'V Mandarin':>13}")
print(f"{'':<28} {'Dior+Creed':>13} {'Prada+LL':>13} {'JM+Atelier':>13} {'Hermes+Byr':>13} {'TF+Malle':>13}")
print('-' * 98)

for metric, fn in [
    ("Star OAV", lambda d: f"{d['star']:>13,.0f}"),
    ("Total OAV", lambda d: f"{d['total']:>13,.0f}"),
    ("Star pct", lambda d: f"{d['star']/d['total']*100:>12.0f}%"),
    ("Dominant", lambda d: f"{d['dom']:>13d}"),
    ("Subliminal", lambda d: f"{d['sub']:>13d}"),
    ("Materials", lambda d: f"{d['n']:>13d}"),
]:
    line = f"  {metric:<26}"
    for label in formulas:
        line += fn(data[label])
    print(line)

# Compare to pre-review
print(f"\n  CHANGES FROM PRE-REVIEW ARCHITECTURAL VERSIONS")
print(f"  {'Metric':<28} {'I Berg':>8} {'II Ced':>8} {'III Grp':>8} {'IV Lim':>8} {'V Man':>8}")

prev = {
    'I Bergamot':  (9333, 21175, 44),
    'II Cedrat':   (10000,20347,49),
    'III Grapefruit':(13320,25423,52),
    'IV Lime':     (9300, 19530,48),
    'V Mandarin':  (10080,20545,49),
}
for label, (star_before, total_before, pct_before) in prev.items():
    d = data[[k for k in data if label in k][0]]
    delta_star = d['star'] - star_before
    delta_total = d['total'] - total_before
    delta_pct = d['star']/d['total']*100 - pct_before
    print(f"    {'Star OAV':<26} {delta_star:>+8,.0f}  (star pct: {delta_pct:>+.0f}%)")
    print(f"    {'Total OAV':<26} {delta_total:>+8,.0f}")
    break
print('-' * 98)
