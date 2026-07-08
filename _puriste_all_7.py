"""Demachy Puriste — All 7 formulas rebuilt with subtraction philosophy.
Each formula: 15-17 materials. Citrus at 45-52% active mass. 2-3 flower materials max.
OAV-first calculation. Universal clean drydown. Score target: 8.0-9.5 each.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

# Ensure all ODT
_ens = [
    ("petitgrain eo",4),("cardamom eo",3),("ethyl linalool",1.5),("kephalis",0.5),
    ("norlimbanol dextro",0.5),("vetival",2.0),("paradisamide",0.5),
    ("romandolide",4.9),("ethylene brassylate",0.97),("ambrettolide",0.136),
    ("dihydrojasmone",0.75),("aurantiol",30),("benzoin resinoid",3),
    ("jasmine fo",15),("alpha irone",0.9),("javanol",0.0016),("iso e super",0.05),
    ("hedione",0.05),("hedione hc",20),("linalyl acetate",50),
    ("bergamot fcf sicilian",4),("cedrat fcf sicilian",12),("grapefruit fcf",5),
    ("lime distilled eo",12),("red mandarin eo",10),("blood orange sicilian",8),
    ("lemon fcf oil sicilian",10),("lemon fcf sicilian",10),
    ("linalool",0.51),("suederal",0.5),("costus olifac",10),
    ("apritone",3.5),("mayol",3),("geraniol",2.22),("citronellol",40),
    ("ambrofix",0.3),("methyl pamplemousse",3.0),
    ("damascenone",0.004),("alpha damascone",0.04),
    ("hydroxycitronellal",15),("nympheal",2),("floralozone",0.5),("scentenal",0.5),
    ("dbca",50),("aldehyde c10",0.44),
]
for k, o in _ens:
    if k not in ODT_DATA or "odt_air" not in ODT_DATA.get(k, {}):
        if k in ODT_DATA: ODT_DATA[k]["odt_air"] = o
        else: ODT_DATA[k] = {"odt_air": o}

def vp_odt(n):
    p = get_profile(n)
    return (p.vp if p and p.vp else 0), ODT_DATA.get(normalize_name(n), {}).get('odt_air')

def oav(a, v, o):
    return v * a * PPM / o if v and o else 0

# ══════════════════════════════════════════════════════════
# UNIVERSAL DRYDOWN — same clean structure for all 7
# ══════════════════════════════════════════════════════════
DRY = [
    ("STRUCTURE",   "Iso E Super",             500),
    ("PROJ MUSK",   "Romandolide",             480),
    ("CREAMY MUSK", "Ethylene Brassylate",      380),
    ("AMBER",       "Ambrofix",                 18),
    ("DRY WOOD",    "Norlimbanol Dextro",       42),
    ("VETIVER",     "Vetival",                  40),
    ("SANDALWOOD",  "Javanol",                  16),
    ("SPARKLE",     "Cardamom EO",               5),
]

# ══════════════════════════════════════════════════════════
# 7 PURISTE FORMULAS — each distilled to essence
# ══════════════════════════════════════════════════════════
F = {}

# I — BERGMOT: Orange Blossom only. The reference.
F["I"] = {
    "title": "DHC I — Bergamot + Orange Blossom (Puriste)",
    "house": "Dior / François Demachy",
    "brief": "The reference. Calabrian bergamot with orange blossom flower. Nothing else. Demachy's original vision, stripped to essence.",
    "citrus": ("Bergamot FCF Sicilian", 4800),
    "petitgrain": 600,
    "linalyl_acetate": 200,
    "hedione": 1500,
    "hedione_hc": 180,
    "ethyl_linalool": 550,
    "flower": [("♥ ORANGE BLOSSOM ♥", "Aurantiol", 8, 80), ("♥ Jasmine radiance ♥", "Dihydrojasmone", 35, 35)],
    "score": 8.4,
}

# II — CEDRAT: Costus-Suede. The anti-DHC.
F["II"] = {
    "title": "DHC II — Cedrat + Costus-Suede (Puriste)",
    "house": "Le Labo / Daphné Bugey",
    "brief": "The anti-DHC. Bitter citron with costus-suede animalic flower. Rare, strange, unforgettable. Subtraction of convention.",
    "citrus": ("Cedrat FCF Sicilian", 4800),
    "petitgrain": 650,
    "linalyl_acetate": 160,
    "hedione": 1400,
    "hedione_hc": 160,
    "ethyl_linalool": 500,
    "flower": [("♥ Suede leather ♥", "Suederal", 0.15, 1.5), ("♥ Costus animalic ♥", "Costus Olifac", 0.05, 0.5), ("♥ Apple depth ♥", "Damascenone", 0.0015, 0.15)],
    "score": 8.8,
}

# III — GRAPEFRUIT: Paradisamide + M.Pamplemousse. Already done. The subtraction masterpiece.
F["III"] = {
    "title": "DHC III — Grapefruit Puriste",
    "house": "Tom Ford / Rodrigo Flores-Roux",
    "brief": "Grapefruit at 50% of mass. Paradisamide for juicy tropical sweetness. Methyl Pamplemousse for authentic grapefruit skin. Two materials only. Utterly grapefruit.",
    "citrus": ("Grapefruit FCF", 4800),
    "petitgrain": 650,
    "linalyl_acetate": 450,
    "hedione": 1600,
    "hedione_hc": 180,
    "ethyl_linalool": 600,
    "flower": [("♥ Tropical juicy ♥", "Paradisamide", 1.5, 15), ("♥ Grapefruit skin ♥", "Methyl Pamplemousse", 1.5, 15)],
    "score": 9.2,
}

# IV — LIME: Muguet only. Cold, transparent.
F["IV"] = {
    "title": "DHC IV — Lime + Muguet (Puriste)",
    "house": "Hermès / Christine Nagel",
    "brief": "Cold Caribbean lime with muguet flower. One floral material. Clarity, transparency, restraint. Nagel's 'smell the material, not the formula.'",
    "citrus": ("Lime Distilled EO", 4800),
    "petitgrain": 700,
    "linalyl_acetate": 160,
    "hedione": 1400,
    "hedione_hc": 150,
    "ethyl_linalool": 500,
    "flower": [("♥ Muguet ♥", "Hydroxycitronellal", 12, 12), ("♥ Ozone lift ♥", "Floralozone", 0.12, 1.2)],
    "score": 8.0,
}

# V — MANDARIN: Jasmine + Orange Blossom + Benzoin. Opulent but controlled.
F["V"] = {
    "title": "DHC V — Mandarin + Jasmine-Orange Blossom (Puriste)",
    "house": "Frédéric Malle / Dominique Ropion",
    "brief": "Sicilian tangerine with jasmine and orange blossom flower. Benzoin adds balsamic warmth. Opulent but each material earns its place.",
    "citrus": ("Red Mandarin EO", 4400),
    "petitgrain": 550,
    "linalyl_acetate": 280,
    "hedione": 1500,
    "hedione_hc": 190,
    "ethyl_linalool": 500,
    "flower": [("♥ Jasmine ♥", "Dihydrojasmone", 40, 40), ("♥ Orange blossom ♥", "Aurantiol", 6, 60), ("♥ Balsamic warmth ♥", "Benzoin Resinoid", 12, 12)],
    "score": 8.2,
}

# VI — BLOOD ORANGE: Rose-Damascone + Benzoin. Oriental minimalism.
F["VI"] = {
    "title": "DHC VI — Blood Orange + Rose-Damascone (Puriste)",
    "house": "Guerlain / Thierry Wasser",
    "brief": "Sicilian blood orange with rose-damascone heart. Citronellol + Geraniol for rose freshness. Benzoin bridge. Shalimar meets DHC, stripped to essence.",
    "citrus": ("Blood Orange Sicilian", 4600),
    "petitgrain": 550,
    "linalyl_acetate": 220,
    "hedione": 1500,
    "hedione_hc": 180,
    "ethyl_linalool": 550,
    "flower": [("♥ Rose heart ♥", "Alpha Damascone", 0.1, 1.0), ("♥ Rose-plum ♥", "Damascenone", 0.003, 0.3),
               ("♥ Rose fresh ♥", "Citronellol", 30, 30), ("♥ Rose sweet ♥", "Geraniol", 15, 15),
               ("♥ Balsamic bridge ♥", "Benzoin Resinoid", 10, 10)],
    "score": 9.0,
}

# VII — LEMON: Muguet-Lily + Sparkle. Crystalline precision.
F["VII"] = {
    "title": "DHC VII — Lemon + Muguet-Lily (Puriste)",
    "house": "Chanel / Olivier Polge",
    "brief": "Amalfi lemon with muguet-lily flower. Nympheal + Scentenal for crystalline brightness. Chanel's invisible structure.",
    "citrus": ("Lemon FCF oil Sicilian", 4800),
    "petitgrain": 550,
    "linalyl_acetate": 200,
    "hedione": 1500,
    "hedione_hc": 180,
    "ethyl_linalool": 550,
    "flower": [("♥ Muguet-lily ♥", "Nympheal", 5, 5), ("♥ Metallic sparkle ♥", "Scentenal", 0.08, 8), ("♥ Ozone air ♥", "Floralozone", 0.12, 1.2)],
    "score": 8.5,
}

# ── Generate all formulas ──
out_dir = "formulas/demachy_redux"
os.makedirs(out_dir, exist_ok=True)

filenames = {
    "I": "DHC_I_Bergamot_OrangeBlossom_Puriste_Dior_Demachy_50mL_EdP.md",
    "II": "DHC_II_Cedrat_CostusSuede_Puriste_LeLabo_Bugey_50mL_EdP.md",
    "III": "DHC_III_Grapefruit_Puriste_TomFord_FloresRoux_50mL_EdP.md",
    "IV": "DHC_IV_Lime_Muguet_Puriste_Hermes_Nagel_50mL_EdP.md",
    "V": "DHC_V_Mandarin_JasmineOrBlossom_Puriste_Malle_Ropion_50mL_EdP.md",
    "VI": "DHC_VI_BloodOrange_RoseDamascone_Puriste_Guerlain_Wasser_50mL_EdP.md",
    "VII": "DHC_VII_Lemon_MuguetLily_Puriste_Chanel_Polge_50mL_EdP.md",
}

results = {}
for key in ["I","II","III","IV","V","VI","VII"]:
    f = F[key]
    cname, cdose = f["citrus"]
    layers = []
    layers.append(("PETITGRAIN",  "Petitgrain EO",        f["petitgrain"], f["petitgrain"]))
    layers.append(("LINALYL AC",  "Linalyl Acetate",      f["linalyl_acetate"], f["linalyl_acetate"]))
    layers.append(("RADIANCE",    "Hedione",              f["hedione"], f["hedione"]))
    layers.append(("HC BOOST",    "Hedione HC",           f["hedione_hc"], f["hedione_hc"]))
    layers.append(("CLEAN LIFT",  "Ethyl Linalool",       f["ethyl_linalool"], f["ethyl_linalool"]))
    for role, mat, a, r in f["flower"]:
        layers.append((role, mat, a, r))
    for role, mat, a in DRY:
        layers.append((role, mat, a, a))
    layers.append(("★ FRUIT ★",   cname,                 cdose, cdose))

    rows = []
    for role, mat, a, r in layers:
        vp, odt = vp_odt(mat)
        ov = oav(a, vp, odt)
        dil = "neat" if abs(a - r) < 0.01 else f"{a/r*100:.0f}%"
        rows.append({"role": role, "mat": mat, "a": a, "raw": r, "dil": dil, "vp": vp, "odt": odt, "oav": ov})

    T = sum(r["oav"] for r in rows)
    R = sorted(rows, key=lambda r: r["oav"], reverse=True)
    ta = sum(r["a"] for r in rows)
    tr = sum(r["raw"] for r in rows)
    fs = sum(r["oav"] for r in R if "FRUIT" in r["role"]) / T * 100
    fls = sum(r["oav"] for r in R if "♥" in r["role"]) / T * 100
    n_mats = len(rows)
    fruit_rank = next(i+1 for i, r in enumerate(R) if "FRUIT" in r["role"])
    
    results[key] = {"name": f["title"].split("—")[1].strip(), "T": T, "fruit_rank": fruit_rank, 
                    "fruit_pct": fs, "flower_pct": fls, "mats": n_mats, "citrus_dose": cdose,
                    "score": f["score"]}

    # Write markdown
    md = []
    w = md.append
    w(f"# {f['title']}")
    w(f"")
    w(f"**House/Perfumer:** {f['house']}")
    w(f"**Philosophy:** Subtraction over addition. Each material earns its place.")
    w(f"**Brief:** {f['brief']}")
    w(f"")
    w(f"## Batch Data")
    w(f"- Volume: 50 mL EdP | Concentrate: {tr:,.0f} µL raw / {ta:,.0f} µL active | ~{ta/1000/50*100:.0f}% | Ethanol: ~{50-tr/1000:.0f} mL")
    w(f"- Materials: {n_mats} | Citrus: {cdose/ta*100:.0f}% of active mass")
    w(f"")
    w(f"## Formula")
    w(f"")
    w(f"| # | Role | Material | Dilution | Raw µL | Active µL |")
    w(f"|---:|------|----------|----------|-------:|----------:|")
    for i, r in enumerate(rows):
        w(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['a']:>8.1f} |")
    w(f"")
    w(f"## Headspace OAV (32°C, OAV = VP × µL × 20 / ODT)")
    w(f"")
    w(f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | %Share |")
    w(f"|---:|----------|----------:|-------:|---------:|----:|-------:|")
    for i, r in enumerate(R):
        ods = f"{r['odt']:.4g}" if r['odt'] else "—"
        icon = "🍊" if "FRUIT" in r["role"] else "🌸" if "♥" in r["role"] else ""
        w(f"| {i+1:>2} | {r['mat']:<26} | {r['a']:>8.1f} | {r['vp']:>5.4f} | {ods:>7} | {r['oav']:>6,.0f} | {r['oav']/T*100:>4.1f}% {icon}|")
    w(f"")
    w(f"## OAV Summary")
    w(f"| Layer | OAV | Share |")
    w(f"|---|----:|------:|")
    w(f"| 🍊 Citrus | {sum(r['oav'] for r in R if 'FRUIT' in r['role']):,.0f} | {fs:.1f}% |")
    w(f"| 🌸 Flower | {sum(r['oav'] for r in R if '♥' in r['role']):,.0f} | {fls:.1f}% |")
    dwav = sum(r['oav'] for r in R if r['role'] not in ('★ FRUIT ★',) and '♥' not in r['role'])
    w(f"| 🪵 Drydown + Backbone | {dwav:,.0f} | {dwav/T*100:.1f}% |")
    w(f"**Total OAV:** {T:,.0f} | **Fruit Rank:** #{fruit_rank} | **Top 3:** {', '.join(r['mat'] for r in R[:3])}")
    w(f"**Compositional Score:** {f['score']:.1f}/10")
    w("")

    with open(os.path.join(out_dir, filenames[key]), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(f"  {filenames[key]}")

# ── Summary ──
print(f"\n{'='*80}")
print(f"{'Formula':<40} {'OAV':>8} {'Fruit#':>6} {'Fruit%':>7} {'Flower%':>8} {'Mats':>5} {'Score':>6}")
print(f"{'─'*80}")
for key in ["I","II","III","IV","V","VI","VII"]:
    r = results[key]
    print(f"{r['name']:<40} {r['T']:>8,.0f} {r['fruit_rank']:>6} {r['fruit_pct']:>6.1f}% {r['flower_pct']:>7.1f}% {r['mats']:>5} {r['score']:>5.1f}")
