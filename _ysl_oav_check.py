import sys; sys.path.insert(0, r'D:\chatbots\perfume-chem')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

ODT_OV = {'Cardamom EO':{'odt_eth':1.0},'Vertofix':{'odt_eth':2.0}}
def get_odt(name):
    key=name.lower().replace(' ','')
    for k,v in ODT_DATA.items():
        if k.replace(' ','')==key: return v.get('odt_eth')
    if name in ODT_OV: return ODT_OV[name].get('odt_eth')
    p=get_profile(name)
    if p and p.odt_ppm: return p.odt_ppm
    return None

F = [
    ('Ethylene Brassylate',900,100,'base'),('Cashmeran',875,20,'base'),('Hexyl Salicylate',787,100,'base'),
    ('Musk Ketone',600,10,'base'),('Iso E Super',400,100,'base'),('Romandolide',375,100,'base'),
    ('Ambrettolide',350,10,'base'),('Habanolide',275,100,'base'),('Azarbre',175,100,'base'),
    ('Vertofix',165,100,'base'),('Siam Benzoin 50%',110,50,'base'),('Exaltolide',107,10,'base'),
    ('Polysantol',44,100,'base'),('Hedione',1500,100,'heart'),('Hedione HC',375,100,'heart'),
    ('Alpha Irone',733,30,'heart'),('Coumarin',750,20,'heart'),('Heliotropal',650,100,'heart'),
    ('Vanillin',500,10,'heart'),('Anisaldehyde',325,100,'heart'),('DBCA',138,100,'heart'),
    ('Phenethyl Alcohol',95,100,'heart'),('Damascol',94,10,'heart'),('Geraniol',51,100,'heart'),
    ('Eugenol',24,100,'heart'),('Farnesol',24,100,'heart'),
    ('Bergamot FCF oil Sicilian',487,100,'top'),('Aldehyde C12 MNA',412,1,'top'),
    ('Red Mandarin EO',250,100,'top'),('Aldehyde C11 undecylenic',75,100,'top'),
    ('Cardamom EO',56,100,'top')]
TC=11702; EC=0.234
results=[]
for name,ul,dil,note in F:
    act=ul*dil/100; ppm=act/TC*1e6; edp=ppm*EC; odt=get_odt(name)
    oav=edp/odt if odt and odt>0 else 0
    results.append((name,ul,act,odt,oav,note))
results.sort(key=lambda x:-x[4])
print('OAV LEADERBOARD - Final YSL Formula (50 mL, 23.4% EDP)')
print('-'*75)
for i,(name,ul,act,odt,oav,note) in enumerate(results):
    odt_s=f'{odt:.3f}' if odt else 'N/A'
    if oav>5000: p='MEGA'
    elif oav>500: p='EXTREME'
    elif oav>50: p='DOM'
    elif oav>5: p='clear'
    else: p='weak'
    print(f'{i+1:2d}. {name:<28} {ul:>5}uL act={act:>6.1f} ODT={odt_s:>8} OAV={oav:>10,.0f} {p:>5} ({note})')

sec={'top':0,'heart':0,'base':0}
for r in results:
    sec[r[5]]+=r[4]
total = sum(r[4] for r in results)
print(f'\nTotal OAV: {total:,.0f}')
print(f'Top: {sec["top"]:,.0f} ({sec["top"]/total*100:.0f}%)  Heart: {sec["heart"]:,.0f} ({sec["heart"]/total*100:.0f}%)  Base: {sec["base"]:,.0f} ({sec["base"]/total*100:.0f}%)')
below=[r for r in results if r[4]>0 and r[4]<5]
print(f'Below threshold (OAV<5): {len(below)}' if below else 'All materials above OAV=5')
