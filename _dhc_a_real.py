"""DHC A — True DHC flankers. Real Dior Homme Cologne architecture.

Citrus → Iris → Clean Musk. Linear. Hollow base. ~10 materials. ~10% concentration.
No woods. No petitgrain. No jasmine/orange blossom heart.
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
    ("galaxolide", 0.05, 0.01, "clean white musk"),
    ("habanolide", 0.5, 0.1, "transparent clean musk"),
    ("molecule iris", 0.2, 0.04, "modern iris veil"),
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
# INVARIANT BACKBONE — Real DHC architecture
# ══════════════════════════════════════════════════════════

BACKBONE = [
    ("RADIANCE",    "Hedione",              400,  400),
    ("HC NUANCE",   "Hedione HC",           80,   80),
    ("CLEAN LIFT",  "Ethyl Linalool",       300,  300),
    ("LINALYL AC",  "Linalyl Acetate",      100,  100),
    ("TRANSPARENT", "Dihydromyrcenol",      40,   40),
    ("IRIS",        "Alpha Irone",          4.5,  15),   # 30% in DEP
    ("MUSK",        "Galaxolide",           125,  250),  # 50% in DEP
    ("MUSK2",       "Habanolide",           40,   40),
    ("AMBER",       "Ambrofix",             24,   80),   # 30% w/v
]

# ══════════════════════════════════════════════════════════
# 7 FLANKERS — Only the star citrus changes
# ══════════════════════════════════════════════════════════

FLANKERS = [
    {
        "key": "I Bergamot",
        "file": "DHC_A_I_Bergamot_Dior.md",
        "tree": "Bergamot (Citrus bergamia)",
        "citrus": ("Bergamot FCF Sicilian", 4000),
        "house": "Dior / Demachy",
        "score": 8.5,
    },
    {
        "key": "II Cedrat",
        "file": "DHC_A_II_Cedrat_LeLabo.md",
        "tree": "Citron (Citrus medica)",
        "citrus": ("Cedrat FCF Sicilian", 4000),
        "house": "Le Labo / Bugey",
        "score": 8.2,
    },
    {
        "key": "III Grapefruit",
        "file": "DHC_A_III_Grapefruit_TomFord.md",
        "tree": "Grapefruit (Citrus paradisi)",
        "citrus": ("Grapefruit FCF", 3800),
        "house": "Tom Ford / Flores-Roux",
        "score": 8.0,
    },
    {
        "key": "IV Lime",
        "file": "DHC_A_IV_Lime_Hermes.md",
        "tree": "Lime (Citrus aurantiifolia)",
        "citrus": ("Lime Distilled EO", 4000),
        "house": "Hermes / Nagel",
        "score": 7.8,
    },
    {
        "key": "V Mandarin",
        "file": "DHC_A_V_Mandarin_Malle.md",
        "tree": "Mandarin (Citrus reticulata)",
        "citrus": ("Red Mandarin EO", 3800),
        "house": "Malle / Ropion",
        "score": 8.1,
    },
    {
        "key": "VI Blood Orange",
        "file": "DHC_A_VI_BloodOrange_Guerlain.md",
        "tree": "Blood Orange (Citrus sinensis)",
        "citrus": ("Blood Orange Sicilian", 3900),
        "house": "Guerlain / Wasser",
        "score": 8.3,
    },
    {
        "key": "VII Lemon",
        "file": "DHC_A_VII_Lemon_Chanel.md",
        "tree": "Lemon (Citrus limon)",
        "citrus": ("Lemon FCF oil Sicilian", 4000),
        "house": "Chanel / Polge",
        "score": 8.0,
    },
]

# ── Build summary table ──
out = []; w = out.append
w("# DHC A — True DHC Flankers. Citrus → Iris → Clean Musk.")
w("")
w("Real Dior Homme Cologne architecture. ~10 materials. ~10% concentration. Linear. Hollow base.")
w("No woods. No petitgrain. Iris heart. White musk drydown.")
w("")
w("| # | Citrus Tree | Citrus µL | OAV | Fruit% | Iris% | Score |")
w("|---:|-------------|----------:|----:|--------|-------|-------|")

for f in FLANKERS:
    cn, cd = f["citrus"]
    layers = list(BACKBONE)
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
    iris_share = sum(r["oav"] for r in ranked if "IRIS" in r["role"]) / total_oav * 100
    fr = next(i+1 for i, r in enumerate(ranked) if "FRUIT" in r["role"])

    w(f"| {f['key'].split()[0]} | {f['tree']} | {cd} | {total_oav:,.0f} | {fruit_share:.1f}% | {iris_share:.2f}% | {f['score']} |")

# Write summary
with open("formulas/demachy_redux/DHC_A_SUMMARY.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("  Written DHC_A_SUMMARY.md")

# Write individual formula files
out_dir = "formulas/demachy_redux"
os.makedirs(out_dir, exist_ok=True)

for f in FLANKERS:
    cn, cd = f["citrus"]
    layers = list(BACKBONE)
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
    iris_share = sum(r["oav"] for r in ranked if "IRIS" in r["role"]) / total_oav * 100
    fr = next(i+1 for i, r in enumerate(ranked) if "FRUIT" in r["role"])

    md = []
    w = md.append
    w(f"# {f['key']} — {f['tree']}")
    w("")
    w(f"**House/Perfumer:** {f['house']}")
    w(f"**Architecture:** DHC A — True DHC Flanker. Citrus → Iris → Clean Musk.")
    w(f"**Concentration:** ~{total_active/1000/50*100:.0f}% | **Materials:** {len(rows)}")
    w(f"**Score:** {f['score']}/10")
    w("")
    w("## Batch Data")
    w("")
    w(f"- **Volume:** 50 mL")
    w(f"- **Concentrate:** {total_raw:,.0f} µL raw / {total_active:,.0f} µL active")
    w(f"- **Ethanol fill:** ~{50 - total_raw/1000:.0f} mL")
    w(f"- **Citrus mass:** {sum(r['active'] for r in ranked if 'FRUIT' in r['role'])/total_active*100:.0f}% of active")
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
        icon = "🍊" if "FRUIT" in r["role"] else "⚜️" if "IRIS" in r["role"] else ""
        w(f"| {i+1:>2} | {r['mat']:<26} | {r['active']:>8.1f} | {r['vp']:>5.4f} | {odt_s:>7} | {r['oav']:>6,.0f} | {r['oav']/total_oav*100:>4.1f}% {icon}|")

    w("")
    w("## Layer Analysis")
    w("")
    w("| Layer | OAV | Share |")
    w("|-------|----:|------:|")
    w(f"| 🍊 Fruit ({sum(1 for r in ranked if 'FRUIT' in r['role'])} material) | {sum(r['oav'] for r in ranked if 'FRUIT' in r['role']):,.0f} | {fruit_share:.1f}% |")
    w(f"| ⚜️ Iris ({sum(1 for r in ranked if 'IRIS' in r['role'])} material) | {sum(r['oav'] for r in ranked if 'IRIS' in r['role']):,.0f} | {iris_share:.2f}% |")
    w(f"| 🫧 Musk/Amber | {sum(r['oav'] for r in ranked if r['role'] in ('MUSK','MUSK2','AMBER')):,.0f} | — |")
    w("")
    w(f"**Total Headspace OAV:** {total_oav:,.0f}")
    w(f"  ")
    w(f"**🍊 Fruit Rank:** #{fr}")
    w(f"  ")
    w(f"**Top 3 Headspace:** {', '.join(r['mat'] for r in ranked[:3])}")
    w(f"  ")
    w(f"**Formula Hash:** (DHC A — true DHC flanker)")
    w("")

    filepath = os.path.join(out_dir, f["file"])
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(f"  Written {f['file']}")

print(f"\n{len(FLANKERS)} DHC A formulas written to {out_dir}/")
