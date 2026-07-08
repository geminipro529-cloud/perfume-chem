"""Rate Bottle B as an aromatic fougere."""
import sys, math
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20

bottle_b = {
    'Lemon FCF oil Sicilian': 3150.0, 'Hedione': 710.5, 'Hedione HC': 270.0,
    'Ethyl Linalool': 247.5, 'Linalyl Acetate': 90.0, 'Petitgrain EO': 112.5,
    'Ambrofix': 8.1, 'Ethyl Maltol': 1.35, 'Dihydrojasmone': 22.5, 'Aurantiol': 6.75,
    'Mayol': 6.3, 'Nympheal': 2.7, 'Scentenal': 0.009, 'Floralozone': 0.045,
    'Iso E Super': 225.0, 'Romandolide': 216.0, 'Ethylene Brassylate': 171.0,
    'Norlimbanol Dextro': 18.9, 'Vetival': 18.0, 'Javanol': 7.2, 'Cardamom EO': 2.25,
    'Alpha Irone': 318.3, 'Lime Distilled EO': 314.8, 'Bergamot FCF oil Sicilian': 279.8,
    'Galaxolide': 174.9, 'Cedrat FCF oil Sicilian': 139.9, 'Lavender EO HA': 122.4,
    'Terpinyl Acetate': 104.9, 'Galbanum Resinoid': 87.4, 'Coumarin': 70.0,
    'Rhodinol ex Citronella': 28.0, 'Cyclamen Aldehyde': 26.2,
    'Parmavert': 14.0, 'Ambrox Super': 14.0, 'Evernyl': 10,     'Damascenone': 8.7,
    'D-Limonene': 7.0, 'Beta-Pinene': 3.5,
    # Mass-appeal additions
    'Vanillin': 15, 'Cashmeran': 15, 'Coumarin_extra': 70,
}

# Merge extras
bottle_b['Coumarin'] += bottle_b.pop('Coumarin_extra', 0)

def get_vp(n):
    p = get_profile(n)
    return p.vp if p and p.vp else 0
def get_odt(n):
    return ODT_DATA.get(normalize_name(n), {}).get('odt_air') or 0

rows = []
for n, a in bottle_b.items():
    vp, odt = get_vp(n), get_odt(n)
    if vp and odt:
        rows.append((n, a, a * vp * PPM / odt))
rows.sort(key=lambda x: x[2], reverse=True)
total_oav = sum(r[2] for r in rows)

fougere_good = set(bottle_b.keys())
bad_mats = {'Scentenal', 'Floralozone', 'Ethyl Maltol', 'Aurantiol'}
good_oav = sum(r[2] for r in rows if r[0] not in bad_mats)

# Character groups
fresh_pool = {'Lemon FCF','Cedrat FCF','Lime Distilled EO','Bergamot FCF','D-Limonene',
              'Hedione','Hedione HC','Lavender EO HA','Petitgrain EO'}
herbal_pool = {'Lavender EO HA','Terpinyl Acetate','Galbanum Resinoid','Petitgrain EO',
               'Cyclamen Aldehyde','Parmavert','Rosemary EO','Evernyl'}
warm_pool = {'Coumarin','Rhodinol','Damascenone','Cardamom EO','Javanol','Romandolide',
             'Ethyl Maltol','Vanillin','Cashmeran'}
woody_pool = {'Iso E Super','Norlimbanol','Vetival','Ethylene Brassylate','Ambrox Super',
              'Ambrofix','Vetiver EO India'}
floral_pool = {'Dihydrojasmone','Mayol','Nympheal','Bergamot FCF','Alpha Irone',
               'Rhodinol','Aurantiol','Damascenone'}

fresh = sum(r[2] for r in rows if r[0] in fresh_pool) / total_oav * 100
herbal = sum(r[2] for r in rows if r[0] in herbal_pool) / total_oav * 100
warm = sum(r[2] for r in rows if r[0] in warm_pool) / total_oav * 100
woody = sum(r[2] for r in rows if r[0] in woody_pool) / total_oav * 100
floral = sum(r[2] for r in rows if r[0] in floral_pool) / total_oav * 100

# Fougere pillars
pillars = {'Bergamot':'Bergamot FCF oil Sicilian','Lavender':'Lavender EO HA',
           'Geranium/Rose':'Rhodinol ex Citronella','Coumarin':'Coumarin',
           'Oakmoss sub':'Galbanum Resinoid'}
present = [n for n in pillars.values() if n in bottle_b]
fougere_pct = len(present) / 5 * 100

total_active = sum(bottle_b.values())
hedonism = good_oav / total_oav * 100

print("=" * 70)
print("  BOTTLE B — AROMATIC FOUGERE RATING")
print("=" * 70)
print(f"  Materials: {len(bottle_b)}  |  Active: {total_active:.0f} uL  |  OAV: {total_oav:,.0f}")
print(f"  Concentration: 14%  |  Hedonism: {hedonism:.1f}/100")
print()

print(f"  TOP 10 OAV:")
for i, (n, a, o) in enumerate(rows[:10], 1):
    p = o / total_oav * 100
    tag = ""
    if n in bad_mats: tag = " XX"
    print(f"  {i:>2}. {n:<30} {o:>8,.0f} ({p:>5.1f}%){tag}")
print(f"  ... ({len(rows)} materials with ODT data)")

print(f"\n  CHARACTER RADAR:")
print(f"  Fresh/Citrus: {'#'*int(fresh/5)}{'-'*(20-int(fresh/5))} {fresh:>5.1f}%")
print(f"  Herbal/Green: {'#'*int(herbal/5)}{'-'*(20-int(herbal/5))} {herbal:>5.1f}%")
print(f"  Floral:       {'#'*int(floral/5)}{'-'*(20-int(floral/5))} {floral:>5.1f}%")
print(f"  Warm:         {'#'*int(warm/5)}{'-'*(20-int(warm/5))} {warm:>5.1f}%")
print(f"  Woody:        {'#'*int(woody/5)}{'-'*(20-int(woody/5))} {woody:>5.1f}%")

print(f"\n  FOUGERE PILLARS: {fougere_pct:.0f}/100")
for role, mat in pillars.items():
    ok = "V" if mat in present else "X"
    print(f"    [{ok}] {role:<14} -> {mat}")

# Star ratings
f = fresh / 100
s = {
    'Wearability': min(10, 5 + f * 5),
    'Versatility': min(10, 3 + f * 3 + (warm/100) * 3),
    'Originality': min(10, 4 + (1 - len(bad_mats)/len(bottle_b)) * 4 + floral/100 * 2),
    'Sophistication': min(10, 3 + fougere_pct/100 * 4 + herbal/100 * 3),
    'Signature': min(10, 4 + (fougere_pct/100) * 3 + warm/100 * 3),
    'Mass Appeal': min(10, 4 + f * 4 + warm/100 * 2),
    'Gender Versatility': min(10, 5 + f * 3 - woody/100 * 1),
    'Age Range': min(10, 6 + f * 2 + warm/100 * 2),
    'Formula Elegance': min(10, 3 + fougere_pct/100 * 3 + hedonism/100 * 4),
    'Value': min(10, 4 + fougere_pct/100 * 3),
}
avg = sum(s.values()) / len(s)

print(f"\n  10-STAR RATINGS:")
for k, v in sorted(s.items(), key=lambda x: x[1], reverse=True):
    bar = "#" * int(v) + "-" * (10 - int(v))
    print(f"    {k:<22} {v:>4.1f}/10  {bar}")
print(f"    {'OVERALL':<22} {avg:>4.1f}/10")
