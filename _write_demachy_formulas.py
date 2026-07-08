"""Write all 7 Demachy DHC formulas as markdown files from OAV calculations.
Each formula: Massive Citrus → Tree Flower → Woody-Musk Drydown.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

def _ensure(k, odt, eth, char):
    v = {"odt_air": odt, "odt_eth": eth, "char": char}
    if k in ODT_DATA and "odt_air" not in ODT_DATA.get(k, {}):
        ODT_DATA[k].update(v)
    elif k not in ODT_DATA:
        ODT_DATA[k] = v

# Ensure correct ODT values
_ensures = [
    ("blood orange sicilian", 8.0, 2.0, "juicy sweet-tart berry-citrus"),
    ("lemon fcf oil sicilian", 10.0, 2.0, "fresh bright lemon citrus"),
    ("lemon fcf sicilian", 10.0, 2.0, "fresh bright lemon"),
    ("petitgrain eo", 4.0, 1.0, "petitgrain green-citrus"),
    ("cardamom eo", 3.0, 0.5, "cardamom bright-spicy"),
    ("ambrofix", 0.3, 0.005, "ambrox-smooth"),
    ("mayol", 3.0, 0.5, "muguet lily"),
    ("geraniol", 2.22, 0.3, "rose geranium sweet"),
    ("citronellol", 40.0, 5.0, "rose fresh green"),
    ("jessemal", 5.0, 1.0, "jasmine body"),
    ("ethyl linalool", 1.5, 0.3, "clean-linalool ether"),
    ("kephalis", 0.5, 0.1, "woody-amber-tobacco"),
    ("norlimbanol dextro", 0.5, 0.1, "dry-powerful wood"),
    ("vetival", 2.0, 0.5, "vetiver-suede"),
    ("paradisamide", 0.5, 0.1, "guava-passionfruit"),
    ("floralozone", 0.5, 0.1, "ozone airy-floral"),
    ("scentenal", 0.5, 0.05, "metallic-green ozone"),
    ("hydroxycitronellal", 15.0, 3.0, "muguet dewy"),
    ("nympheal", 2.0, 0.4, "muguet creamy-green"),
    ("damascenone", 0.004, 0.0004, "cooked apple tobacco"),
    ("alpha damascone", 0.04, 0.01, "rose plum apple"),
    ("romandolide", 4.9, 0.5, "clean woody-musk"),
    ("ethylene brassylate", 0.97, 1.0, "creamy lactonic musk"),
    ("ambrettolide", 0.136, 0.014, "musky-fruity wine"),
    ("dihydrojasmone", 0.75, 0.15, "jasmine fruity-green"),
    ("aurantiol", 30.0, 5.0, "orange blossom schiff base"),
    ("vertofix", 6.3, 1.0, "woody bridge"),
    ("benzoin resinoid", 3.0, 2.0, "balsamic sweet-resinous"),
    ("jasmine fo", 15.0, 3.0, "jasmine accord"),
    ("alpha irone", 0.9, 0.16, "iris orris butter"),
    ("javanol", 0.0016, 0.0003, "sandalwood dry"),
    ("iso e super", 0.05, 0.01, "cedar abstract wood"),
    ("hedione", 0.05, 0.01, "jasmine radiance"),
    ("hedione hc", 20.0, 3.0, "hedione-HC radiant-jasmine"),
    ("linalyl acetate", 50.0, 8.0, "lavender-bergamot"),
    ("bergamot fcf sicilian", 4.0, 1.0, "rich bergamot"),
    ("cedrat fcf sicilian", 12.0, 2.0, "bitter citron sharp"),
    ("grapefruit fcf", 5.0, 1.0, "bitter-clean pith"),
    ("lime distilled eo", 12.0, 2.0, "tart lime gin-citrus"),
    ("red mandarin eo", 10.0, 2.0, "sweet tangerine"),
    ("linalool", 0.51, 0.1, "floral fresh lavender"),
    ("suederal", 0.5, 0.5, "suede leather warm"),
    ("costus olifac", 10.0, 2.0, "costus root musky-animalic"),
    ("apritone", 3.5, 0.5, "apricot-peach lactonic"),
    ("dihydromyrcenol", 1.0, 0.3, "dihydromyrcenol cool-citrus"),
]
for k, odt, eth, char in _ensures:
    _ensure(k, odt, eth, char)

def vp_odt(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    d = ODT_DATA.get(n, {})
    return vp, d.get('odt_air')

# Dilution helpers: (raw_function, label)
def fmt_dil(active, raw):
    if abs(active - raw) < 0.01:
        return "neat", raw
    pct = active / raw * 100
    return f"{pct:.0f}%", raw

# ══════════════════════════════════════════════════════
# 7 FORMULAS — Demachy Triptych
# ══════════════════════════════════════════════════════

FORMULAS = [
    # I — BERGMOT + ORANGE BLOSSOM
    {
        "file": "DHC_I_Bergamot_OrangeBlossom_Dior_Demachy_50mL_EdP.md",
        "title": "DHC I — Bergamot + Orange Blossom (Dior / Demachy)",
        "brief": "The reference. Calabrian bergamot, its orange blossom flower, clean woody-musk. Demachy's transparent citrus perfection.",
        "house": "Dior / François Demachy",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              600,   600),
            ("LINALYL AC",  "Linalyl Acetate",             200,   200),
            ("RADIANCE",    "Hedione",                    1500,  1500),
            ("HC BOOST",    "Hedione HC",                  180,   180),
            ("CLEAN LIFT",  "Ethyl Linalool",              550,   550),
            ("♥ FLOWER ♥",  "Aurantiol",                    6,    60),
            ("♥ FLOWER ♥",  "Dihydrojasmone",               30,    30),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Bergamot FCF Sicilian",      4200,  4200),
        ],
    },
    # II — CEDRAT + COSTUS-SUEDE
    {
        "file": "DHC_II_Cedrat_CostusSuede_LeLabo_Bugey_50mL_EdP.md",
        "title": "DHC II — Cedrat + Costus-Suede (Le Labo / Bugey)",
        "brief": "Bitter citron with animalic suede-jasmine flower. Rare, strange, unforgettable. The anti-DHC.",
        "house": "Le Labo / Daphné Bugey",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              650,   650),
            ("LINALYL AC",  "Linalyl Acetate",             180,   180),
            ("RADIANCE",    "Hedione",                    1400,  1400),
            ("HC BOOST",    "Hedione HC",                  160,   160),
            ("CLEAN LIFT",  "Ethyl Linalool",              500,   500),
            ("♥ FLOWER ♥",  "Suederal",                      0.15,   1.5),
            ("♥ FLOWER ♥",  "Costus Olifac",                 0.05,   0.5),
            ("♥ FLOWER ♥",  "Dihydrojasmone",               30,    30),
            ("♥ FLOWER ♥",  "Damascenone",                   0.0012, 0.12),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Cedrat FCF Sicilian",        4200,  4200),
        ],
    },
    # III — GRAPEFRUIT + JASMINE
    {
        "file": "DHC_III_Grapefruit_Jasmine_TomFord_FloresRoux_50mL_EdP.md",
        "title": "DHC III — Grapefruit + Jasmine (Tom Ford / Flores-Roux)",
        "brief": "Expensive pink grapefruit via subtraction. White jasmine flower. Bold, clean, sensual.",
        "house": "Tom Ford / Rodrigo Flores-Roux",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              650,   650),
            ("LINALYL AC",  "Linalyl Acetate",             350,   350),
            ("RADIANCE",    "Hedione",                    1600,  1600),
            ("HC BOOST",    "Hedione HC",                  180,   180),
            ("CLEAN LIFT",  "Ethyl Linalool",              600,   600),
            ("♥ FLOWER ♥",  "Dihydrojasmone",               35,    35),
            ("♥ FLOWER ♥",  "Jessemal",                      8,     8),
            ("♥ FLOWER ♥",  "Paradisamide",                  0.6,    6),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Grapefruit FCF",             3800,  3800),
        ],
    },
    # IV — LIME + MUGUET
    {
        "file": "DHC_IV_Lime_Muguet_Hermes_Nagel_50mL_EdP.md",
        "title": "DHC IV — Lime + Muguet (Hermès / Nagel)",
        "brief": "Cold Caribbean lime tree. Delicate white muguet flower. Clarity, transparency, restraint.",
        "house": "Hermès / Christine Nagel",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              700,   700),
            ("LINALYL AC",  "Linalyl Acetate",             160,   160),
            ("RADIANCE",    "Hedione",                    1400,  1400),
            ("HC BOOST",    "Hedione HC",                  150,   150),
            ("CLEAN LIFT",  "Ethyl Linalool",              500,   500),
            ("♥ FLOWER ♥",  "Hydroxycitronellal",            10,    10),
            ("♥ FLOWER ♥",  "Mayol",                         6,     6),
            ("♥ FLOWER ♥",  "Floralozone",                   0.15,   1.5),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Lime Distilled EO",          4200,  4200),
        ],
    },
    # V — MANDARIN + JASMINE-ORANGE BLOSSOM
    {
        "file": "DHC_V_Mandarin_JasmineOrBlossom_Malle_Ropion_50mL_EdP.md",
        "title": "DHC V — Mandarin + Jasmine-Orange Blossom (Malle / Ropion)",
        "brief": "Sicilian tangerine tree. Jasmine and orange blossom flower. Artistic luxury, technical mastery.",
        "house": "Frédéric Malle / Dominique Ropion",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              550,   550),
            ("LINALYL AC",  "Linalyl Acetate",             280,   280),
            ("RADIANCE",    "Hedione",                    1500,  1500),
            ("HC BOOST",    "Hedione HC",                  190,   190),
            ("CLEAN LIFT",  "Ethyl Linalool",              500,   500),
            ("♥ FLOWER ♥",  "Dihydrojasmone",               40,    40),
            ("♥ FLOWER ♥",  "Aurantiol",                    6,    60),
            ("♥ FLOWER ♥",  "Jasmine FO",                  60,    60),
            ("♥ FLOWER ♥",  "Benzoin Resinoid",            12,    12),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Red Mandarin EO",           3800,  3800),
        ],
    },
    # VI — BLOOD ORANGE + ROSE
    {
        "file": "DHC_VI_BloodOrange_Rose_Guerlain_Wasser_50mL_EdP.md",
        "title": "DHC VI — Blood Orange + Rose (Guerlain / Wasser)",
        "brief": "Sicilian blood orange tree. Damascene rose flower. Oriental citrus. Shalimar meets DHC.",
        "house": "Guerlain / Thierry Wasser",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              550,   550),
            ("LINALYL AC",  "Linalyl Acetate",             220,   220),
            ("RADIANCE",    "Hedione",                    1500,  1500),
            ("HC BOOST",    "Hedione HC",                  180,   180),
            ("CLEAN LIFT",  "Ethyl Linalool",              550,   550),
            ("♥ FLOWER ♥",  "Alpha Damascone",               0.08,   0.8),
            ("♥ FLOWER ♥",  "Damascenone",                   0.003,  0.3),
            ("♥ FLOWER ♥",  "Citronellol",                  30,    30),
            ("♥ FLOWER ♥",  "Geraniol",                     15,    15),
            ("♥ FLOWER ♥",  "Aurantiol",                     4,    40),
            ("♥ FLOWER ♥",  "Benzoin Resinoid",             10,    10),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Blood Orange Sicilian",      4000,  4000),
        ],
    },
    # VII — LEMON + MUGUET-LILY
    {
        "file": "DHC_VII_Lemon_MuguetLily_Chanel_Polge_50mL_EdP.md",
        "title": "DHC VII — Lemon + Muguet-Lily (Chanel / Polge)",
        "brief": "Amalfi lemon tree. Crystalline muguet-lily flower. Precision, timelessness, invisible structure.",
        "house": "Chanel / Olivier Polge",
        "layers": [
            ("PETITGRAIN",  "Petitgrain EO",              550,   550),
            ("LINALYL AC",  "Linalyl Acetate",             200,   200),
            ("RADIANCE",    "Hedione",                    1500,  1500),
            ("HC BOOST",    "Hedione HC",                  180,   180),
            ("CLEAN LIFT",  "Ethyl Linalool",              550,   550),
            ("♥ FLOWER ♥",  "Hydroxycitronellal",            12,    12),
            ("♥ FLOWER ♥",  "Nympheal",                      5,     5),
            ("♥ FLOWER ♥",  "Floralozone",                   0.15,   1.5),
            ("♥ FLOWER ♥",  "Scentenal",                     0.06,   6),
            ("STRUCTURE",   "Iso E Super",                 480,   480),
            ("PROJ MUSK",   "Romandolide",                 460,   460),
            ("CREAMY MUSK", "Ethylene Brassylate",          360,   360),
            ("AMBER",       "Ambrofix",                     17,    17),
            ("DRY WOOD",    "Norlimbanol Dextro",           42,    42),
            ("VETIVER",     "Vetival",                      40,    40),
            ("SANDALWOOD",  "Javanol",                      16,    16),
            ("SPARKLE",     "Cardamom EO",                   4,     4),
            ("★ FRUIT ★",   "Lemon FCF oil Sicilian",     4200,  4200),
        ],
    },
]

out_dir = "formulas/demachy_redux"
os.makedirs(out_dir, exist_ok=True)

for f in FORMULAS:
    rows = []
    for role, mat, active, raw in f["layers"]:
        vp_val, odt_val = vp_odt(mat)
        oav_val = vp_val * active * PPM / odt_val if vp_val and odt_val else 0
        dil, r = fmt_dil(active, raw)
        rows.append({"role": role, "mat": mat, "active": active, "raw": r, "dil": dil,
                      "vp": vp_val, "odt": odt_val, "oav": oav_val})

    total_oav = sum(r["oav"] for r in rows)
    total_active = sum(r["active"] for r in rows)
    total_raw = sum(r["raw"] for r in rows)
    ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)

    fruit_share = sum(r["oav"] for r in ranked if "FRUIT" in r["role"]) / total_oav * 100
    flower_share = sum(r["oav"] for r in ranked if "FLOWER" in r["role"]) / total_oav * 100

    md = []
    w = md.append
    w(f"# {f['title']}")
    w("")
    w(f"**House/Perfumer:** {f['house']}")
    w(f"**Architecture:** Demachy Triptych — Massive Citrus → Tree Flower → Woody-Musk")
    w(f"**Brief:** {f['brief']}")
    w("")
    w("## Batch Data")
    w("")
    w(f"- **Volume:** 50 mL EdP")
    w(f"- **Concentrate:** {total_raw:,.0f} µL raw / {total_active:,.0f} µL active")
    w(f"- **Concentration:** ~{total_active/1000/50*100:.0f}%")
    w(f"- **Ethanol fill:** ~{50 - total_raw/1000:.0f} mL")
    w(f"- **Materials:** {len(rows)} | **Citrus mass:** {sum(r['active'] for r in ranked if 'FRUIT' in r['role'])/total_active*100:.0f}% of active")
    w("")
    w("## Formula")
    w("")
    w("*Compound base first, then heart, then top. Swirl gently between layers. Add ethanol to 50 mL line. Invert 50×. Macerate 4 weeks.*")
    w("")
    w("| # | Role | Material | Dilution | Raw µL | Active µL |")
    w("|---:|------|----------|----------|-------:|----------:|")
    for i, r in enumerate(rows):
        w(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['active']:>8.1f} |")

    w("")
    w("## Headspace OAV (32°C, 50mL)")
    w("")
    w("*OAV = VP(Pa) × active_µL × 20 / ODT_air(ppb)*")
    w("")
    w("| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | %Share |")
    w("|---:|----------|----------:|-------:|---------:|----:|-------:|")
    for i, r in enumerate(ranked):
        odt_s = f"{r['odt']:.4g}" if r['odt'] else "—"
        icon = "🍊" if "FRUIT" in r['role'] else "🌸" if "FLOWER" in r['role'] else ""
        w(f"| {i+1:>2} | {r['mat']:<26} | {r['active']:>8.1f} | {r['vp']:>5.4f} | {odt_s:>7} | {r['oav']:>6,.0f} | {r['oav']/total_oav*100:>4.1f}% {icon}|")

    w("")
    w("## Layer Analysis")
    w("")
    w(f"| Layer | OAV | Share |")
    w(f"|-------|----:|------:|")
    w(f"| 🍊 Fruit ({sum(1 for r in ranked if 'FRUIT' in r['role'])} material) | {sum(r['oav'] for r in ranked if 'FRUIT' in r['role']):,.0f} | {fruit_share:.1f}% |")
    w(f"| 🌸 Flower ({sum(1 for r in ranked if 'FLOWER' in r['role'])} materials) | {sum(r['oav'] for r in ranked if 'FLOWER' in r['role']):,.0f} | {flower_share:.1f}% |")
    w(f"| 🪵 Drydown | {sum(r['oav'] for r in ranked if r['role'] not in ('PETITGRAIN','LINALYL AC','RADIANCE','HC BOOST','CLEAN LIFT','♥ FLOWER ♥','★ FRUIT ★')):,.0f} | — |")
    w("")
    w(f"**Total Headspace OAV:** {total_oav:,.0f}")
    w(f"  ")
    w(f"**🍊 Fruit Rank:** #{next(i+1 for i,r in enumerate(ranked) if 'FRUIT' in r['role'])}")
    w(f"  ")
    w(f"**Top 3 Headspace:** {', '.join(r['mat'] for r in ranked[:3])}")
    w(f"  ")
    w(f"**Formula Hash:** (OAV-first, Demachy architecture)")
    w("")

    filepath = os.path.join(out_dir, f["file"])
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(f"  {f['file']}")

print(f"\n7 formulas written to {out_dir}/")
