import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
for name in ['Damascenone','Alpha Damascone','Vertofix','Romandolide','Linalyl Acetate','Lavender EO High Altitude','Iso E Super','Hedione','Javanol','Geraniol','Cedarwood oil Virginia','Clearwood','Evernyl','Kephalis','Norlimbanol Dextro','Black Pepper EO','Patchouli EO','Vetiver EO (India)','Nagarmortha Oil','Ambrettolide','Juniper Berry EO','Spike Lavender EO','Clary Sage EO','Dihydrojasmone','Rosemary EO']:
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0.0
    mw = p.mw if p and p.mw else 0.0
    print(f"{name:35s} VP={vp:.4f} Pa  MW={mw:.1f}")
