import sys; sys.path.insert(0,'.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name
PPM=20.0
for k,o in {'petitgrain eo':4,'cardamom eo':3,'ethyl linalool':15,'norlimbanol dextro':0.8,'vetival':7.0,'romandolide':4.9,'ethylene brassylate':0.97,'dihydrojasmone':0.75,'aurantiol':30,'javanol':0.0016,'iso e super':0.05,'hedione':0.05,'hedione hc':20,'linalyl acetate':2.7,'lemon fcf oil sicilian':10,'ambrofix':0.3,'hydroxycitronellal':15,'nympheal':2,'floralozone':1.0,'scentenal':0.02,'ethyl maltol':0.3}.items():
    if k in ODT_DATA: ODT_DATA[k]['odt_air']=o
    else: ODT_DATA[k]={'odt_air':o}
def v(name):
    p=get_profile(name); k='hedione hc' if name.lower()=='hedione hc' else normalize_name(name)
    return (p.vp if p and p.vp else 0), ODT_DATA.get(k,{}).get('odt_air')

mats=[('Lemon FCF oil Sicilian',6500),('Petitgrain EO',250),('Linalyl Acetate',160),('Hedione',1300),('Hedione HC',550),('Ethyl Linalool',550),('Ethyl Maltol',2),('Dihydrojasmone',35),('Aurantiol',15),('Mayol',14),('Nympheal',6),('Scentenal',0.02),('Floralozone',0.15),('Iso E Super',500),('Romandolide',480),('Ethylene Brassylate',380),('Ambrofix',18),('Norlimbanol Dextro',42),('Vetival',40),('Javanol',16),('Cardamom EO',5)]
with open("_oav_air_audit.txt","w") as f:
    f.write(f"{'Material':<25} {'Active':>8} {'VP(Pa)':>8} {'ODT':>8} {'OAV':>10} {'In Air?':>10}\n")
    f.write('-'*75 + '\n')
    for m,a in mats:
        vp,odt=v(m); ov=round(vp*a*PPM/odt,1) if vp and odt else 0
        if ov>=10: status='LOUD'
        elif ov>=2: status='detectable'
        elif ov>=0.5: status='trace'
        elif ov>=0.1: status='skin only'
        else: status='INVISIBLE'
        f.write(f'{m:<25} {a:>8.1f} {vp:>8.4f} {str(odt):>8} {ov:>10,.1f} {status:>10}\n')
    idx=0; loud=0; det=0; trc=0; skin=0; inv=0
    for m,a in mats:
        vp,odt=v(m); ov=round(vp*a*PPM/odt,1) if vp and odt else 0
        if ov>=10: loud+=1
        elif ov>=2: det+=1
        elif ov>=0.5: trc+=1
        elif ov>=0.1: skin+=1
        else: inv+=1
    f.write(f'\nLOUD: {loud} | detectable: {det} | trace: {trc} | skin-only: {skin} | INVISIBLE: {inv}\n')
print("Written _oav_air_audit.txt")
