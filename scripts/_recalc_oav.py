"""Recalculate OAV for collab formula"""
from collections import defaultdict as dd

materials = [
    ('Iso E Super',800,100,10.0,'Woods'),('Cedarwood EO',500,100,15.0,'Woods'),
    ('Kephalis',50,100,0.5,'Woods'),('Cashmeran',120,100,2.0,'Woods'),
    ('Javanol',40,100,3.0,'Woods'),('Sandalore',120,100,10.0,'Woods'),
    ('Ebanol',180,100,8.0,'Woods'),('Vertofix',80,100,1.0,'Woods'),
    ('Azarbre',60,100,2.0,'Woods'),('Patchouli EO',100,100,10.0,'Woods'),
    ('Olibanum 10%',500,10,15.0,'Incense'),('Siam Benzoin 50%',300,50,50.0,'Incense'),
    ('Labdanum 10%',100,10,10.0,'Incense'),('Romandolide',250,100,1.0,'Musk'),
    ('EB',200,100,2.0,'Musk'),('Musk Ketone 10%',180,10,2.0,'Musk'),
    ('Jasmine Abs 10%',600,10,8.0,'Jasmine'),('Hedione',1200,100,25.0,'Jasmine'),
    ('Hedione HC',600,100,20.0,'Jasmine'),('cis-Jasmone',150,100,0.5,'Jasmine'),
    ('Benzyl Acetate',200,100,20.0,'Jasmine'),('g-Undecalactone',100,100,1.0,'Jasmine'),
    ('Dihydrojasmone',120,100,50.0,'Jasmine'),('Indole 10%',25,10,0.3,'Jasmine'),
    ('Paradisamide 10%',30,10,0.5,'Jasmine'),('Alpha Irone 30%',25,30,0.1,'Orris'),
    ('Myristic Acid 1%',600,1,5000.0,'Orris'),('Dihydro Beta Ionone',150,100,5.0,'Orris'),
    ('Alpha Ionone',100,100,0.4,'Orris'),('Orivone',180,100,3.0,'Orris'),
    ('AIMI',120,100,5.0,'Orris'),('Allyl Ionone',40,100,3.0,'Orris'),
    ('Ultralia',20,100,0.3,'Orris'),('PEA',100,100,200.0,'Rose'),
    ('Geraniol',60,100,40.0,'Rose'),('Rose Oxide 1%',10,1,0.005,'Rose'),
    ('Alpha Damascone 10%',4,10,0.009,'Rose'),('Cardamom EO',80,100,3.0,'Top'),
    ('Bergamot FCF',300,100,15.0,'Top'),('Petitgrain EO',100,100,12.0,'Top'),
    ('D-Limonene',60,100,10.0,'Top'),('Ethyl Safranate',15,100,0.5,'Top'),
    ('Hexyl Salicylate',180,100,3.0,'Struct'),('Benzyl Salicylate',250,100,200.0,'Struct'),
    ('Benzyl Benzoate',400,100,500.0,'Struct'),
]

f = dd(float)
total = 0
conc = 0

for name, dose, dil, odt, fam in materials:
    active = dose * dil / 100
    oav = round((active * 1000) / (30 * odt))
    f[fam] += oav
    total += oav
    conc += dose
    marker = "***" if oav > 3000 else ""
    print(f"  {name:<25} {active:>6.1f} act  ODT {odt:>8}  OAV {oav:>8,}  {marker}")

print()
print("=" * 50)
print("FAMILY BALANCE:")
for fam in sorted(f, key=lambda x: f[x], reverse=True):
    pct = f[fam] / total * 100
    bar = "#" * int(pct)
    print(f"  {fam:<12} {f[fam]:>8,.0f}  ({pct:>5.1f}%)  {bar}")
print(f"  {'TOTAL':<12} {total:>8,.0f}")
print(f"  {'Concentrate':<12} {conc:>8,.0f} uL")
print(f"  {'Ethanol':<12} {30000-conc:>8,.0f} uL")
