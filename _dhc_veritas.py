"""DHC Veritas — True flankers of the original DHC. Each citrus wears its OWN tree flower.

Backbone and drydown are invariant across all 7 formulas.
Only the star citrus and the tree-flower accord change.
This makes them recognizable as coming from the same collection.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

def _ensure(k, odt, eth, char):
    """Force-override ODT values — DHC-corrected values win over engine defaults."""
    if k not in ODT_DATA:
        ODT_DATA[k] = {}
    ODT_DATA[k].update({"odt_air": odt, "odt_eth": eth, "char": char})

_ensures = [
    ("blood orange sicilian", 8.0, 2.0, "juicy sweet-tart berry-citrus"),
    ("lemon fcf oil sicilian", 10.0, 2.0, "fresh bright lemon citrus"),
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

def fmt_dil(active, raw):
    if abs(active - raw) < 0.01:
        return "neat", raw
    pct = active / raw * 100
    return f"{pct:.0f}%", raw

# ══════════════════════════════════════════════════════════
# INVARIANT BACKBONE + DRYDOWN — shared across all flankers
# ══════════════════════════════════════════════════════════

BACKBONE = [
    ("PETITGRAIN",  "Petitgrain EO"),
    ("LINALYL AC",  "Linalyl Acetate"),
    ("RADIANCE",    "Hedione"),
    ("HC BOOST",    "Hedione HC"),
    ("CLEAN LIFT",  "Ethyl Linalool"),
]

DRYDOWN = [
    ("STRUCTURE",   "Iso E Super",         480,   480),
    ("PROJ MUSK",   "Romandolide",         460,   460),
    ("CREAMY MUSK", "Ethylene Brassylate",  360,   360),
    ("AMBER",       "Ambrofix",             17,    17),
    ("DRY WOOD",    "Norlimbanol Dextro",   42,    42),
    ("VETIVER",     "Vetival",              40,    40),
    ("SANDALWOOD",  "Javanol",              16,    16),
    ("SPARKLE",     "Cardamom EO",           4,     4),
]

# ══════════════════════════════════════════════════════════
# TREE FLOWERS — each citrus wears its own blossom
# Backbone proportions vary slightly per formula (as in original DHC)
# ══════════════════════════════════════════════════════════

FLANKERS = [
    {
        "key": "I Bergamot",
        "file": "DHC_I_Bergamot_Veritas_Dior.md",
        "tree": "Bergamot (Citrus bergamia)",
        "blossom": "Orange blossom — white, honeyed, Neroli",
        "citrus": ("Bergamot FCF Sicilian", 4200),
        "backbone": [(350, 350), (200, 200), (1500, 1500), (180, 180), (550, 550)],
        "flower": [
            ("♥ FLOWER ♥", "Aurantiol",            6,   60),
            ("♥ FLOWER ♥", "Dihydrojasmone",       30,   30),
        ],
        "house": "Dior / Demachy",
        "score": 8.8,
    },
    {
        "key": "II Cedrat",
        "file": "DHC_II_Cedrat_Veritas_LeLabo.md",
        "tree": "Citron (Citrus medica)",
        "blossom": "Citron blossom — white, fresh, lemony-green, delicate",
        "citrus": ("Cedrat FCF Sicilian", 4200),
        "backbone": [(350, 350), (180, 180), (1400, 1400), (160, 160), (500, 500)],
        "flower": [
            ("♥ FLOWER ♥", "Suederal",             0.15, 1.5),
            ("♥ FLOWER ♥", "Costus Olifac",        0.05, 0.5),
            ("♥ FLOWER ♥", "Dihydrojasmone",       30,   30),
            ("♥ FLOWER ♥", "Damascenone",          0.0012, 0.12),
        ],
        "house": "Le Labo / Bugey",
        "score": 9.0,
    },
    {
        "key": "III Grapefruit",
        "file": "DHC_III_Grapefruit_Veritas_TomFord.md",
        "tree": "Grapefruit (Citrus paradisi)",
        "blossom": "Grapefruit blossom — white, intensely jasmine-like, tropical",
        "citrus": ("Grapefruit FCF", 3800),
        "backbone": [(350, 350), (350, 350), (1600, 1600), (180, 180), (600, 600)],
        "flower": [
            ("♥ FLOWER ♥", "Dihydrojasmone",       35,   35),
            ("♥ FLOWER ♥", "Jessemal",             8,     8),
            ("♥ FLOWER ♥", "Paradisamide",         0.6,   6),
        ],
        "house": "Tom Ford / Flores-Roux",
        "score": 9.5,
    },
    {
        "key": "IV Lime",
        "file": "DHC_IV_Lime_Veritas_Hermes.md",
        "tree": "Lime (Citrus aurantiifolia)",
        "blossom": "Lime blossom — small white flower, delicate, green-fresh",
        "citrus": ("Lime Distilled EO", 4200),
        "backbone": [(350, 350), (160, 160), (1400, 1400), (150, 150), (500, 500)],
        "flower": [
            ("♥ FLOWER ♥", "Hydroxycitronellal",   10,   10),
            ("♥ FLOWER ♥", "Mayol",                6,     6),
            ("♥ FLOWER ♥", "Floralozone",          0.15, 1.5),
        ],
        "house": "Hermes / Nagel",
        "score": 8.5,
    },
    {
        "key": "V Mandarin",
        "file": "DHC_V_Mandarin_Veritas_Malle.md",
        "tree": "Mandarin (Citrus reticulata)",
        "blossom": "Mandarin blossom — orange blossom family, sweet, warm",
        "citrus": ("Red Mandarin EO", 3800),
        "backbone": [(350, 350), (280, 280), (1500, 1500), (190, 190), (500, 500)],
        "flower": [
            ("♥ FLOWER ♥", "Dihydrojasmone",       40,   40),
            ("♥ FLOWER ♥", "Aurantiol",            6,    60),
            ("♥ FLOWER ♥", "Jasmine FO",           60,   60),
            ("♥ FLOWER ♥", "Benzoin Resinoid",     12,   12),
        ],
        "house": "Malle / Ropion",
        "score": 8.7,
    },
    {
        "key": "VI Blood Orange",
        "file": "DHC_VI_BloodOrange_Veritas_Guerlain.md",
        "tree": "Blood Orange (Citrus sinensis)",
        "blossom": "Orange blossom — white, honeyed, slightly berry-fruited",
        "citrus": ("Blood Orange Sicilian", 4000),
        "backbone": [(350, 350), (220, 220), (1500, 1500), (180, 180), (550, 550)],
        "flower": [
            ("♥ FLOWER ♥", "Alpha Damascone",      0.08,  0.8),
            ("♥ FLOWER ♥", "Damascenone",          0.003, 0.3),
            ("♥ FLOWER ♥", "Citronellol",          30,    30),
            ("♥ FLOWER ♥", "Geraniol",             15,    15),
            ("♥ FLOWER ♥", "Aurantiol",            4,     40),
            ("♥ FLOWER ♥", "Benzoin Resinoid",     10,    10),
        ],
        "house": "Guerlain / Wasser",
        "score": 9.3,
    },
    {
        "key": "VII Lemon",
        "file": "DHC_VII_Lemon_Veritas_Chanel.md",
        "tree": "Lemon (Citrus limon)",
        "blossom": "Lemon blossom — white, intensely citrusy-floral, bright, crystalline",
        "citrus": ("Lemon FCF oil Sicilian", 4200),
        "backbone": [(350, 350), (200, 200), (1500, 1500), (180, 180), (550, 550)],
        "flower": [
            ("♥ FLOWER ♥", "Hydroxycitronellal",   12,   12),
            ("♥ FLOWER ♥", "Nympheal",             5,     5),
            ("♥ FLOWER ♥", "Floralozone",          0.15, 1.5),
            ("♥ FLOWER ♥", "Scentenal",            0.06,  6),
        ],
        "house": "Chanel / Polge",
        "score": 9.0,
    },
]

# ── Build summary table ──
out = []; w = out.append
w("# DHC VERITAS — True Flankers. Each Citrus Wears Its Own Tree Flower.")
w("")
w("Verified ODT architecture. Invariant backbone + drydown. Only citrus and flower change.")
w("")
w("| # | Citrus Tree | Blossom | Flower Materials | Citrus µL | OAV | Fruit% | Flower% | Score |")
w("|---:|-------------|---------|------------------|----------:|----:|--------|---------|-------|")

for f in FLANKERS:
    cn, cd = f["citrus"]
    layers = []
    for (role, mat), (act, raw) in zip(BACKBONE, f["backbone"]):
        layers.append((role, mat, act, raw))
    for role, mat, act, raw in f["flower"]:
        layers.append((role, mat, act, raw))
    for role, mat, act, raw in DRYDOWN:
        layers.append((role, mat, act, raw))
    layers.append(("★ FRUIT ★", cn, cd, cd))

    rows = []
    for role, mat, act, raw in layers:
        vp_val, odt_val = vp_odt(mat)
        oav_val = vp_val * act * PPM / odt_val if vp_val and odt_val else 0
        rows.append({"role": role, "mat": mat, "active": act, "raw": raw,
                     "vp": vp_val, "odt": odt_val, "oav": oav_val})

    total_oav = sum(r["oav"] for r in rows)
    ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)
    fruit_share = sum(r["oav"] for r in ranked if "FRUIT" in r["role"]) / total_oav * 100
    flower_share = sum(r["oav"] for r in ranked if "FLOWER" in r["role"]) / total_oav * 100
    fr = next(i+1 for i, r in enumerate(ranked) if "FRUIT" in r["role"])

    blossom_mats = ", ".join(mat for _, mat, _, _ in f["flower"])
    w(f"| {f['key'].split()[0]} | {f['tree'].split('(')[1].replace(')','')} | {f['blossom'][:20]} | {blossom_mats[:40]} | {cd} | {total_oav:,.0f} | {fruit_share:.1f}% | {flower_share:.1f}% | {f['score']} |")

# Write summary
with open("formulas/demachy_redux/DHC_VERITAS.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("  Written DHC_VERITAS.md")

# Write individual formula files
out_dir = "formulas/demachy_redux"
os.makedirs(out_dir, exist_ok=True)

for f in FLANKERS:
    cn, cd = f["citrus"]
    layers = []
    for (role, mat), (act, raw) in zip(BACKBONE, f["backbone"]):
        layers.append((role, mat, act, raw))
    for role, mat, act, raw in f["flower"]:
        layers.append((role, mat, act, raw))
    for role, mat, act, raw in DRYDOWN:
        layers.append((role, mat, act, raw))
    layers.append(("★ FRUIT ★", cn, cd, cd))

    rows = []
    for role, mat, act, raw in layers:
        vp_val, odt_val = vp_odt(mat)
        oav_val = vp_val * act * PPM / odt_val if vp_val and odt_val else 0
        dil, r = fmt_dil(act, raw)
        rows.append({"role": role, "mat": mat, "active": act, "raw": r, "dil": dil,
                     "vp": vp_val, "odt": odt_val, "oav": oav_val})

    total_oav = sum(r["oav"] for r in rows)
    total_active = sum(r["active"] for r in rows)
    total_raw = sum(r["raw"] for r in rows)
    ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)

    fruit_share = sum(r["oav"] for r in ranked if "FRUIT" in r["role"]) / total_oav * 100
    flower_share = sum(r["oav"] for r in ranked if "FLOWER" in r["role"]) / total_oav * 100
    fr = next(i+1 for i, r in enumerate(ranked) if "FRUIT" in r["role"])

    md = []
    w = md.append
    w(f"# {f['key']} — {f['tree']} + {f['blossom']}")
    w("")
    w(f"**House/Perfumer:** {f['house']}")
    w(f"**Tree:** {f['tree']} | **Blossom:** {f['blossom']}")
    w(f"**Architecture:** DHC Flanker — Invariant Backbone + Drydown. Only citrus and flower change.")
    w(f"**Hedione:** {f['backbone'][2][0]}µL H + {f['backbone'][3][0]}µL HC ({f['backbone'][3][0]/(f['backbone'][2][0]+f['backbone'][3][0])*100:.0f}% high-cis) | **Score:** {f['score']}/10")
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
        icon = "🍊" if "FRUIT" in r["role"] else "🌸" if "FLOWER" in r["role"] else ""
        w(f"| {i+1:>2} | {r['mat']:<26} | {r['active']:>8.1f} | {r['vp']:>5.4f} | {odt_s:>7} | {r['oav']:>6,.0f} | {r['oav']/total_oav*100:>4.1f}% {icon}|")

    w("")
    w("## Layer Analysis")
    w("")
    w("| Layer | OAV | Share |")
    w("|-------|----:|------:|")
    w(f"| 🍊 Fruit ({sum(1 for r in ranked if 'FRUIT' in r['role'])} material) | {sum(r['oav'] for r in ranked if 'FRUIT' in r['role']):,.0f} | {fruit_share:.1f}% |")
    w(f"| 🌸 Flower ({sum(1 for r in ranked if 'FLOWER' in r['role'])} materials) | {sum(r['oav'] for r in ranked if 'FLOWER' in r['role']):,.0f} | {flower_share:.1f}% |")
    w(f"| 🪵 Drydown | {sum(r['oav'] for r in ranked if r['role'] not in ('PETITGRAIN','LINALYL AC','RADIANCE','HC BOOST','CLEAN LIFT','♥ FLOWER ♥','★ FRUIT ★')):,.0f} | — |")
    w("")
    w(f"**Total Headspace OAV:** {total_oav:,.0f}")
    w(f"  ")
    w(f"**🍊 Fruit Rank:** #{fr}")
    w(f"  ")
    w(f"**Top 3 Headspace:** {', '.join(r['mat'] for r in ranked[:3])}")
    w(f"  ")
    w(f"**Formula Hash:** (DHC Veritas — true flanker of original DHC)")
    w("")

    filepath = os.path.join(out_dir, f["file"])
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(f"  Written {f['file']}")

print(f"\n{len(FLANKERS)} Veritas flanker formulas written to {out_dir}/")
