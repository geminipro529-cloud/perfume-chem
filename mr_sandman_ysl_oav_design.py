"""OAV-first YSL rebuild — back-calculate doses from target OAVs."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

ODT_OVERRIDE = {
    "Cardamom EO":           {"odt_eth": 1.0},
    "Labdanum Absolute":     {"odt_eth": 0.5},
    "Cedarwood EO":          {"odt_eth": 3.0},
    "Vertofix":              {"odt_eth": 2.0},
    "Javanol":               {"odt_eth": 0.5},
    "Sandalore":             {"odt_eth": 1.0},
}

def get_odt(name):
    key = name.lower().replace(" ", "")
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key:
            return v.get("odt_eth")
    if name in ODT_OVERRIDE:
        return ODT_OVERRIDE[name].get("odt_eth")
    p = get_profile(name)
    if p and p.odt_ppm: return p.odt_ppm
    return None

EDP_CONC = 0.22  # 22% w/v

# -- OAV-first design --
# Target OAVs: lock signature, YSL boldness, clean projection
DESIGN = [
    # (name, dilution_pct, note, target_OAV_min, target_OAV_max, ysl_note)
    # TOP — signature locked at original ratios
    ("Bergamot FCF oil Sicilian", 100, "top",  6000,  7000, "Signature locked. Original hesperidic bed."),
    ("Red Mandarin EO",          100, "top",  2000,  3000, "Warm citrus. Preserved."),
    ("Aldehyde C11 undecylenic", 100, "top",  3500,  4000, "LOCKED SIGNATURE. YSL-bold but not Ropion."),
    ("Aldehyde C12 MNA",           1, "top",  1500,  1800, "LOCKED SIGNATURE. Sparkle echo."),
    ("Cardamom EO",              100, "top",  2000,  2500, "YSL spice bite in the opening."),
    # HEART — jingle leads, iris veils, spice warms
    ("Hedione",                  100, "heart", 7000,  8000, "Radiance at the room, not the city."),
    ("Heliotropal",              100, "heart",12000, 14000, "LEAD the jingle. Almond powder."),
    ("Anisaldehyde",             100, "heart", 6000,  7000, "Marshmallow jingle. #2 in powder."),
    ("Coumarin",                  20, "heart",  500,   700, "Hay support. Restrained — not a Tonka perfume."),
    ("Vanillin",                  10, "heart",   80,   120, "Custard warmth. Sub-dominant. Vanillin, not Ethyl."),
    ("Alpha Irone",               30, "heart",25000, 30000, "Iris veil. MEGA but not 400K."),
    ("Eugenol",                  100, "heart",  400,   550, "YSL clove warmth. Opium trace."),
    ("DBCA",                     100, "heart",25000, 30000, "Gardenia-rose body. Carries aldehydes through heart."),
    ("Phenethyl Alcohol",        100, "heart",   40,    55, "Rose petal backbone. BARELY audible."),
    ("Geraniol",                 100, "heart",  180,   230, "Rose brightness. Soft classical rose."),
    ("Damascol",                  10, "heart",35000, 40000, "Rose-plum ghost. Ultra-potent at trace."),
    ("Farnesol",                 100, "heart",   40,    55, "Lily-muguet fixative whisper."),
    # BASE — clean white musk, blanket, structure
    ("Habanolide",               100, "base", 25000, 30000, "YSL clean white musk. THE signature base."),
    ("Romandolide",              100, "base",  7000,  8000, "Projection musk. Heard across the room."),
    ("Ethylene Brassylate",      100, "base",  8000, 10000, "Creamy depth under the clean musk."),
    ("Musk Ketone",               10, "base",   500,   700, "Retro-talc echo. Period correct."),
    ("Ambrettolide",              10, "base",  1200,  1600, "Warm-skin depth."),
    ("Exaltolide",                10, "base",   180,   250, "Skin-fat intimacy. 5-musk chord."),
    ("Cashmeran",                 20, "base",  6000,  8000, "Yellow blanket textile."),
    ("Iso E Super",              100, "base",  3500,  4500, "Skin cocoon. Molecular, not anosmic at dose."),
    ("Azarbre",                  100, "base",  6000,  8000, "Cedar-amber glow under the blanket."),
    ("Polysantol",               100, "base",  1500,  2000, "Sandalwood cream. Luxe hotel blanket."),
    ("Vertofix",                 100, "base", 10000, 12000, "Woody bridge. Structural."),
    ("Hexyl Salicylate",         100, "base",   450,   600, "Transparent fixative. High ODT = high dose."),
    ("Siam Benzoin 50%",          50, "base",    80,   120, "Balsamic trace. Hour 8-12."),
]

print("=" * 120)
print(f"{'MR. SANDMAN — YSL EDITION — OAV-FIRST REBUILD':^120}")
print(f"{'Target OAVs back-calculated to doses. Signature locked. YSL theory: bold aldehydic, clean musk.':^120}")
print("=" * 120)
print()

prev_note = ""
total_mass = 0
section_mass = {"top": 0, "heart": 0, "base": 0}

for section_name, section_label in [("top", "TOP — Aldehydic Signature"), 
                                       ("heart", "HEART — Aldehydes First, Jingle Second"),
                                       ("base", "BASE — Clean White Musk")]:
    print(f"\n{'-'*60}")
    print(f"  {section_label}")
    print(f"{'-'*60}")
    print(f"  {'Material':<28} {'Dil%':>5} {'ODT_eth':>9} {'Tgt OAV':>10} {'Calc_ppm':>10} {'Act%':>7} {'MFr%':>7} {'Notes'}")
    print(f"  {'-'*56}")
    
    for name, dilution, note, oav_min, oav_max, ysl_note in DESIGN:
        if note != section_name:
            continue
        
        odt = get_odt(name)
        if odt is None or odt <= 0:
            print(f"  {name:<26} {'NO ODT':>20}")
            continue
        
        # Target OAV = midpoint
        target_oav = (oav_min + oav_max) / 2
        
        # Back-calculate
        # OAV = C_edp / ODT_eth
        # C_edp = C_conc * EDP_CONC
        # C_conc = active_frac% * 10000  (ppm w/w in concentrate)
        # So: target_oav = (active_frac% * 10000 * EDP_CONC) / ODT_eth
        # active_frac% = target_oav * ODT_eth / (10000 * EDP_CONC)
        
        active_pct = target_oav * odt / (10000 * EDP_CONC)
        mass_frac = active_pct / (dilution / 100.0)
        
        conc_ppm = active_pct * 10000
        edp_ppm = conc_ppm * EDP_CONC
        actual_oav = edp_ppm / odt
        
        total_mass += mass_frac
        section_mass[note] += mass_frac
        
        print(f"  {name:<26} {dilution:>5}% {odt:>9.3f} {target_oav:>10.0f} {edp_ppm:>10.0f} {active_pct:>7.3f} {mass_frac:>7.2f} {ysl_note[:50]}")

print(f"\n{'-'*60}")
print(f"  TOTAL mass_frac: {total_mass:.2f}%")
print(f"  TOP: {section_mass['top']:.1f}%  HEART: {section_mass['heart']:.1f}%  BASE: {section_mass['base']:.1f}%")

print()
print("=" * 120)
print("50 mL EDP WEIGHING SHEET — Mass Fractions")
print("=" * 120)

# For 50 mL: total concentrate mass = 11g approx (adjust based on mass_frac total)
# Concentrate at ~22% = 11g. Scale factor = 11/100 = 0.11g per 1% mass_frac
scale = 11.0 / 100.0  # g per 1% mass_frac

weigh_rows = []
for section_name, section_label in [("top","TOP"), ("heart","HEART"), ("base","BASE")]:
    print(f"\n{section_label}:")
    print(f"  {'#':>3} {'Material':<28} {'MFr%':>7} {'Dil%':>5} {'Weigh(g)':>9}")
    
    idx = 0
    for name, dilution, note, oav_min, oav_max, ysl_note in DESIGN:
        if note != section_name:
            continue
        idx += 1
        odt = get_odt(name)
        target_oav = (oav_min + oav_max) / 2
        active_pct = target_oav * odt / (10000 * EDP_CONC)
        mass_frac = active_pct / (dilution / 100.0)
        weigh = mass_frac * scale
        
        if weigh < 0.01:
            w_str = f"{weigh*1000:.0f} mg"
        else:
            w_str = f"{weigh:.3f}"
        
        weigh_rows.append((idx, name, mass_frac, weigh, section_name))
        print(f"  {idx:3d} {name:<26} {mass_frac:>7.2f} {dilution:>5}% {w_str:>9}")

print()
print("=" * 120)
print("COMPOUNDING ORDER")
print("=" * 120)
print()
print("Stage A — Base: Habanolide → Romandolide → EB → Ambrettolide 10% → Exaltolide 10% →")
print("           Musk Ketone 10% → Cashmeran 20% → Iso E Super → Azarbre →")
print("           Polysantol → Vertofix → Hexyl Salicylate → Siam Benzoin 50%")
print("Stage B — Hedione: add neat.")
print("Stage C — Iris: Alpha Irone 30%")
print("Stage D — Jingle + Spice: Heliotropal → Anisaldehyde → Coumarin 20% → Vanillin 10% → Eugenol")
print("Stage E — Floral: DBCA → PEA → Geraniol → Damascol 10% → Farnesol")
print("Stage F — Top (LAST): Bergamot Sicilian → Red Mandarin → C12 MNA 1% → C11 undecylenic → Cardamom EO")
print("Stage G — Rest 48h. Dilute with ethanol 96% to 50 mL. Macerate 4-6 weeks. Cold-filter.")
