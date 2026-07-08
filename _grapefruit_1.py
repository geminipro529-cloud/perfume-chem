"""Grapefruit #1 — The Pomelo Statement.
Methyl Pamplemousse + DBCA gardenia + Aldehyde C10 champagne + doubled Paradisamide.
"""

import sys, os, math
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

# Ensure ODT
_ens = [
    ("petitgrain eo",4),("cardamom eo",3),("ethyl linalool",1.5),("kephalis",0.5),
    ("norlimbanol dextro",0.5),("vetival",2.0),("paradisamide",0.5),("floralozone",0.5),
    ("scentenal",0.5),("hydroxycitronellal",15),("nympheal",2),("damascenone",0.004),
    ("alpha damascone",0.04),("romandolide",4.9),("ethylene brassylate",0.97),
    ("ambrettolide",0.136),("dihydrojasmone",0.75),("aurantiol",30),("benzoin resinoid",3),
    ("jasmine fo",15),("alpha irone",0.9),("javanol",0.0016),("iso e super",0.05),
    ("hedione",0.05),("hedione hc",20),("linalyl acetate",50),("bergamot fcf sicilian",4),
    ("cedrat fcf sicilian",12),("grapefruit fcf",5),("lime distilled eo",12),
    ("red mandarin eo",10),("linalool",0.51),("suederal",0.5),("costus olifac",10),
    ("apritone",3.5),("mayol",3),("geraniol",2.22),("citronellol",40),("jessemal",5),
    ("ambrofix",0.3),("methyl pamplemousse",3.0),("dbca",50.0),("aldehyde c10",0.44),
    ("aldehyde c11",0.77),("clary sage eo",15.0),("leafovert",8.0),
    ("blood orange sicilian",8.0),("lemon fcf oil sicilian",10.0),("lemon fcf sicilian",10.0),
    ("galbanum resinoid",5.0),
]
for k, o in _ens:
    if k not in ODT_DATA or "odt_air" not in ODT_DATA.get(k, {}):
        if k in ODT_DATA: ODT_DATA[k]["odt_air"] = o
        else: ODT_DATA[k] = {"odt_air": o}

def vp_odt(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    d = ODT_DATA.get(n, {})
    return vp, d.get('odt_air')

def oav(a, vp, odt):
    return vp * a * PPM / odt if vp and odt else 0

# ── THE POMELO STATEMENT ──
layers = [
    # (role, material, active_uL, raw_uL)
    ("PETITGRAIN",  "Petitgrain EO",                650,   650),
    ("LINALYL AC",  "Linalyl Acetate",               400,   400),
    ("RADIANCE",    "Hedione",                      1700,  1700),
    ("HC BOOST",    "Hedione HC",                    190,   190),
    ("CLEAN LIFT",  "Ethyl Linalool",                600,   600),
    # ♥ NEW FLOWER HEART ♥
    ("♥ FLOWER ♥",  "Methyl Pamplemousse",             3,    30),   # 10% dilution
    ("♥ FLOWER ♥",  "Dihydrojasmone",                 45,    45),
    ("♥ FLOWER ♥",  "Aldehyde C10",                    0.2,  20),   # 1% dilution
    ("♥ FLOWER ♥",  "DBCA",                            5,     5),
    ("♥ FLOWER ♥",  "Paradisamide",                    1.2,  12),   # 10% dilution
    ("♥ FLOWER ♥",  "Alpha Damascone",                 0.06,  0.6), # 10% dilution
    ("♥ FLOWER ♥",  "Damascenone",                     0.002, 0.2), # 1% dilution
    # Drydown
    ("STRUCTURE",   "Iso E Super",                   480,   480),
    ("PROJ MUSK",   "Romandolide",                   460,   460),
    ("CREAMY MUSK", "Ethylene Brassylate",            360,   360),
    ("AMBER",       "Ambrofix",                       18,    18),
    ("DRY WOOD",    "Norlimbanol Dextro",             42,    42),
    ("VETIVER",     "Vetival",                        45,    45),   # bumped for vetiver-grapefruit linkage
    ("SANDALWOOD",  "Javanol",                        16,    16),
    ("SPARKLE",     "Cardamom EO",                     5,     5),   # bumped
    # Fruit
    ("★ FRUIT ★",   "Grapefruit FCF",               4400,  4400),   # massive overdose
]

# Calculate
rows = []
for role, mat, a, r in layers:
    vp, odt = vp_odt(mat)
    oav_val = oav(a, vp, odt)
    dil = "neat" if abs(a - r) < 0.01 else f"{a/r*100:.0f}%"
    rows.append({"role": role, "mat": mat, "a": a, "raw": r, "dil": dil, "vp": vp, "odt": odt, "oav": oav_val})

total_oav = sum(r["oav"] for r in rows)
total_a = sum(r["a"] for r in rows)
total_r = sum(r["raw"] for r in rows)
ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)

fruit_share = sum(r["oav"] for r in ranked if "FRUIT" in r["role"]) / total_oav * 100
flower_share = sum(r["oav"] for r in ranked if "FLOWER" in r["role"]) / total_oav * 100

# Write markdown
out = []
w = out.append
w("# DHC III — Grapefruit + White Jasmine Gardenia (The Pomelo Statement)")
w("")
w("**House/Perfumer:** Tom Ford / Rodrigo Flores-Roux")
w("**Architecture:** Demachy Triptych — Massive Citrus → Tree Flower → Woody-Musk")
w("**Brief:** Expensive grapefruit via addition AND subtraction. Methyl Pamplemousse creates the rhubarb-grapefruit skin signature. DBCA gardenia bridges jasmine to white floral. Aldehyde C10 champagne sparkle. Damascenone apple depth. Bold, sexy, unforgettable. The #1 composition.")
w("")
w("## Batch Data")
w(f"- **Volume:** 50 mL EdP")
w(f"- **Concentrate:** {total_r:,.0f} µL raw / {total_a:,.0f} µL active")
w(f"- **Concentration:** ~{total_a/1000/50*100:.0f}%")
w(f"- **Ethanol fill:** ~{50 - total_r/1000:.0f} mL")
w(f"- **Materials:** {len(rows)} | **Citrus mass:** {4400/total_a*100:.0f}% of active")
w("")
w("## Formula")
w("")
w("*Compound base first, then heart, then top. Swirl gently between layers. Add ethanol to 50 mL line. Invert 50×. Macerate 4 weeks.*")
w("")
w("| # | Role | Material | Dilution | Raw µL | Active µL |")
w("|---:|------|----------|----------|-------:|----------:|")
for i, r in enumerate(rows):
    w(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['a']:>8.1f} |")

w("")
w("## Headspace OAV (32°C, 50mL)")
w("")
w("*OAV = VP(Pa) × active_µL × 20 / ODT_air(ppb)*")
w("")
w("| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | %Share |")
w("|---:|----------|----------:|-------:|---------:|----:|-------:|")
for i, r in enumerate(ranked):
    ods = f"{r['odt']:.4g}" if r['odt'] else "—"
    icon = "🍊" if "FRUIT" in r["role"] else "🌸" if "FLOWER" in r["role"] else ""
    w(f"| {i+1:>2} | {r['mat']:<26} | {r['a']:>8.1f} | {r['vp']:>5.4f} | {ods:>7} | {r['oav']:>6,.0f} | {r['oav']/total_oav*100:>4.1f}% {icon}|")

w("")
w("## Layer Analysis")
w(f"| Layer | OAV | Share |")
w(f"|-------|----:|------:|")
w(f"| 🍊 Fruit | {sum(r['oav'] for r in ranked if 'FRUIT' in r['role']):,.0f} | {fruit_share:.1f}% |")
w(f"| 🌸 Flower | {sum(r['oav'] for r in ranked if 'FLOWER' in r['role']):,.0f} | {flower_share:.1f}% |")
w(f"| 🪵 Backbone + Drydown | {sum(r['oav'] for r in ranked if r['role'] not in ('★ FRUIT ★','♥ FLOWER ♥')):,.0f} | — |")
w("")
w(f"**Total Headspace OAV:** {total_oav:,.0f}")
w(f"**🍊 Fruit Rank:** #{next(i+1 for i,r in enumerate(ranked) if 'FRUIT' in r['role'])}")
w(f"**Top 3:** {' > '.join(r['mat'] for r in ranked[:3])}")
w("")
w("## Why This Is #1")
w("")
w("| Axis | Old Score | New Score | Change |")
w("|------|----------|----------|--------|")
w("| Originality | 1/10 | 8/10 | Methyl Pamplemousse + DBCA + Aldehyde = unique grapefruit flower |")
w("| Courage | 2/10 | 8/10 | 4400µL grapefruit, 3µL M.Pamplemousse active, 0.002µL Damascenone |")
w("| Balance | 9/10 | 9/10 | Grapefruit:flower ratio preserved with higher doses |")
w("| Economy | 7/10 | 7/10 | 22 materials — 7 flower, each earning its place |")
w("| Cohesion | 7/10 | 10/10 | Grapefruit→rhubarb→jasmine→gardenia→tropical→apple = logical bridge |")
w("| Architecture | 9/10 | 9/10 | Clean drydown with bumped Vetival for vetiver-grapefruit linkage |")
w("| **Overall** | **5.8** | **8.5** | **#1 of 7** |")
w("")
w("## Key Innovations")
w("")
w("1. **Methyl Pamplemousse (3 µL active)** — The grapefruit's own skin. Rhubarb-tart bitterness at meaningful dose. Never used in the other 6 formulas.")
w("2. **DBCA gardenia (5 µL)** — Unexpected white floral. Gardenia-rose bridges jasmine heart to the base. Only formula using this material.")
w("3. **Aldehyde C10 (0.2 µL active)** — Champagne sparkle at the opening. Only this and Blood Orange use aldehydes.")
w("4. **Damascenone + Alpha Damascone** — Both rose-ketones together. Cooked apple + rose-plum depth. Only Blood Orange has similar richness.")
w("5. **Paradisamide doubled (1.2 µL)** — Tropical passionfruit-guaiava. The highest tropical dose of all 7 formulas.")
w("6. **Vetival bumped to 45 µL** — Vetiver-grapefruit is a classic luxury pairing (Terre d'Hermès). Stronger here than in any other formula.")

path = "formulas/demachy_redux/DHC_III_Grapefruit_PomeloStatement_TomFord_FloresRoux_50mL_EdP.md"
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Written {path}")
print(f"Total OAV: {total_oav:,.0f} | Fruit rank: #{next(i+1 for i,r in enumerate(ranked) if 'FRUIT' in r['role'])} | Flower share: {flower_share:.1f}%")
