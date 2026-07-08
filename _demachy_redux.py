"""Demachy DHC Redux — 7 formulas. Architecture: Massive Citrus → Tree Flower → Clean Woody-Musk.
Each citrus is paired with the flower of its tree (or closest analog).
OAV = VP(Pa) * active_uL * 20 / ODT_air(ppb).
"""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

def _ensure(k, odt, eth, char):
    if k not in ODT_DATA or "odt_air" not in ODT_DATA.get(k, {}):
        v = {"odt_air": odt, "odt_eth": eth, "char": char}
        if k in ODT_DATA:
            ODT_DATA[k].update(v)
        else:
            ODT_DATA[k] = v

_ensure("blood orange sicilian", 8.0, 2.0, "juicy sweet-tart berry-citrus")
_ensure("lemon fcf oil sicilian", 10.0, 2.0, "fresh bright lemon citrus")
_ensure("lemon fcf sicilian", 10.0, 2.0, "fresh bright lemon citrus")
_ensure("petitgrain eo", 4.0, 1.0, "petitgrain green-citrus")
_ensure("cardamom eo", 3.0, 0.5, "cardamom bright-spicy")
_ensure("ambrofix", 0.3, 0.005, "ambrox-smooth")
_ensure("mayol", 3.0, 0.5, "muguet lily transparent")
_ensure("geraniol", 2.22, 0.3, "rose geranium sweet")
_ensure("citronellol", 40.0, 5.0, "rose fresh green")
_ensure("jessemal", 5.0, 1.0, "jasmine body")
_ensure("ethyl linalool", 1.5, 0.3, "clean-linalool ether")
_ensure("kephalis", 0.5, 0.1, "woody-amber-tobacco")
_ensure("norlimbanol dextro", 0.5, 0.1, "dry-powerful wood")
_ensure("vetival", 2.0, 0.5, "vetiver-suede")
_ensure("paradisamide", 0.5, 0.1, "guava-passionfruit")
_ensure("floralozone", 0.5, 0.1, "ozone airy-floral")
_ensure("scentenal", 0.5, 0.05, "metallic-green ozone")
_ensure("hydroxycitronellal", 15.0, 3.0, "muguet dewy fresh")
_ensure("nympheal", 2.0, 0.4, "muguet creamy-green")
_ensure("damascenone", 0.004, 0.0004, "cooked apple tobacco")
_ensure("alpha damascone", 0.04, 0.01, "rose plum apple")
_ensure("romandolide", 4.9, 0.5, "clean woody-musk")
_ensure("ethylene brassylate", 0.97, 2.0, "creamy lactonic musk")
_ensure("ambrettolide", 0.136, 0.014, "musky-fruity wine")
_ensure("dihydrojasmone", 0.75, 0.15, "jasmine fruity-green")
_ensure("aurantiol", 30.0, 5.0, "orange blossom schiff base")
_ensure("vertofix", 6.3, 1.0, "woody bridge")
_ensure("benzoin resinoid", 3.0, 2.0, "balsamic sweet-resinous")
_ensure("jasmine fo", 15.0, 3.0, "jasmine accord")
_ensure("alpha irone", 0.9, 0.16, "iris orris butter")
_ensure("javanol", 0.0016, 0.0003, "sandalwood dry")
_ensure("iso e super", 0.05, 0.01, "cedar abstract wood")
_ensure("hedione", 0.05, 0.01, "jasmine radiance")
_ensure("hedione hc", 20.0, 3.0, "hedione-HC radiant-jasmine")
_ensure("linalyl acetate", 50.0, 8.0, "lavender-bergamot")
_ensure("bergamot fcf sicilian", 4.0, 1.0, "rich bergamot")
_ensure("cedrat fcf sicilian", 12.0, 2.0, "bitter citron sharp")
_ensure("grapefruit fcf", 5.0, 1.0, "bitter-clean pith")
_ensure("lime distilled eo", 12.0, 2.0, "tart lime gin-citrus")
_ensure("red mandarin eo", 10.0, 2.0, "sweet tangerine")
_ensure("linalool", 0.51, 0.1, "floral fresh lavender")

def vp(name):
    p = get_profile(name)
    return p.vp if p and p.vp else 0

def odt(name):
    d = ODT_DATA.get(normalize_name(name), {})
    return d.get('odt_air')

def o(active, vp_val, odt_val):
    return vp_val * active * PPM / odt_val if vp_val and odt_val else 0

# dilutions
N = lambda a: a       # neat
D3 = lambda a: a / 0.30  # 30%
D1 = lambda a: a / 0.10  # 10%
D01 = lambda a: a / 0.01 # 1%

# ═══════════════════════════════════════════════════════════
# DEMACHY ARCHITECTURE (each formula ≈16-18 materials)
# 
# Layer A: MASSIVE CITRUS (3500–4500 µL, dominates opening)
# Layer B: PETITGRAIN BRIDGE (green of the tree, 500-700 µL)
# Layer C: LINALYL ACETATE (bright floral sparkle, 150-300 µL)
# Layer D: HEDIONE RADIANCE (jasmine heart, 1200-1800 µL)
# Layer E: FLOWER OF THE TREE (signature citrus flower)
# Layer F: WOODY-MUSK DRYDOWN (clean, transparent, modern)
# ═══════════════════════════════════════════════════════════

# ── Shared Drydown ──
DRY = [
    ("D Woody structure",  "Iso E Super",             480),
    ("D Projective musk",  "Romandolide",             460),
    ("D Creamy cushion",   "Ethylene Brassylate",     360),
    ("D Amber crystal",    "Ambrofix",                 17),
    ("D Dry wood",         "Norlimbanol Dextro",       42),
    ("D Vetiver dryness",  "Vetival",                  40),
    ("D Sandalwood",       "Javanol",                  16),
    ("D Sparkle",          "Cardamom EO",               4),
]

FORMULAS = [
    # ═══ I — BERGAMOT + ORANGE BLOSSOM ═══
    # Bergamot tree → flower is orange blossom (both Calabrian)
    {
        "tag": "I Bergamot",
        "brief": "Calabrian bergamot tree: fruit + orange blossom flower. Dior structure, Creed whisper.",
        "fruit": ("Bergamot FCF Sicilian", 4200),
        "petitgrain": 600,
        "linalyl_acetate": 200,
        "hedione": 1500,
        "hedione_hc": 180,
        "ethyl_linalool": 550,
        "flower": [
            ("♥ Orange blossom tree", "Aurantiol", 6, D1),       # 60 raw
            ("♥ Jasmine radiance",    "Dihydrojasmone", 30, N),
        ],
    },
    # ═══ II — CEDRAT + SUEDE-JASMINE ═══
    # Citron tree → rare, precious, its flower is equally unusual
    {
        "tag": "II Cedrat",
        "brief": "Bitter Mediterranean citron tree: rare fruit, strange suede-jasmine flower. Prada, Le Labo.",
        "fruit": ("Cedrat FCF Sicilian", 4200),
        "petitgrain": 650,
        "linalyl_acetate": 180,
        "hedione": 1400,
        "hedione_hc": 160,
        "ethyl_linalool": 500,
        "flower": [
            ("♥ Costus-suede flower",  "Suederal", 0.15, D1),
            ("♥ Animalic depth",        "Costus Olifac", 0.05, D1),
            ("♥ Jasmine radiance",      "Dihydrojasmone", 30, N),
            ("♥ Apple depth",           "Damascenone", 0.0012, D01),
        ],
    },
    # ═══ III — GRAPEFRUIT + JASMINE ═══
    # Grapefruit tree → flower is white and intensely fragrant, like jasmine
    {
        "tag": "III Grapefruit",
        "brief": "Pink grapefruit tree: bitter-clean fruit, white jasmine flower. Subtraction, not addition.",
        "fruit": ("Grapefruit FCF", 3800),
        "petitgrain": 650,
        "linalyl_acetate": 350,
        "hedione": 1600,
        "hedione_hc": 180,
        "ethyl_linalool": 600,
        "flower": [
            ("♥ White grapefruit flower","Dihydrojasmone", 35, N),
            ("♥ Jasmine body",           "Jessemal", 8, N),
            ("♥ Tropical fruit",         "Paradisamide", 0.6, D1),
        ],
    },
    # ═══ IV — LIME + MUGUET ═══
    # Lime tree → flower is delicate white, like muguet
    {
        "tag": "IV Lime",
        "brief": "Caribbean lime tree: cold tart fruit, delicate white muguet flower. Hermès, Byredo.",
        "fruit": ("Lime Distilled EO", 4200),
        "petitgrain": 700,
        "linalyl_acetate": 160,
        "hedione": 1400,
        "hedione_hc": 150,
        "ethyl_linalool": 500,
        "flower": [
            ("♥ Muguet flower",        "Hydroxycitronellal", 10, N),
            ("♥ Transparent lily",     "Mayol", 6, N),
            ("♥ Ozone-green air",      "Floralozone", 0.15, D1),
        ],
    },
    # ═══ V — MANDARIN + JASMINE-ORANGE BLOSSOM ═══
    # Mandarin tree → flower is orange blossom, Sicily's classic pairing
    {
        "tag": "V Mandarin",
        "brief": "Sicilian mandarin tree: sweet fruit, jasmine-orange blossom flower. TF, Malle.",
        "fruit": ("Red Mandarin EO", 3800),
        "petitgrain": 550,
        "linalyl_acetate": 280,
        "hedione": 1500,
        "hedione_hc": 190,
        "ethyl_linalool": 500,
        "flower": [
            ("♥ Jasmine flower",       "Dihydrojasmone", 40, N),
            ("♥ Orange blossom",       "Aurantiol", 6, D1),
            ("♥ Jasmine accord",       "Jasmine FO", 60, N),
            ("♥ Sweet balsamic",       "Benzoin Resinoid", 12, N),
        ],
    },
    # ═══ VI — BLOOD ORANGE + ROSE ═══
    # Blood orange tree → Sicilian, its flower pairs with rose in oriental tradition
    {
        "tag": "VI Blood Orange",
        "brief": "Sicilian blood orange tree: berry-sweet fruit, damascene rose flower. Shalimar meets DHC.",
        "fruit": ("Blood Orange Sicilian", 4000),
        "petitgrain": 550,
        "linalyl_acetate": 220,
        "hedione": 1500,
        "hedione_hc": 180,
        "ethyl_linalool": 550,
        "flower": [
            ("♥ Rose flower heart",    "Alpha Damascone", 0.08, D1),    # 0.8 raw
            ("♥ Rose-plum depth",      "Damascenone", 0.003, D01),      # 0.3 raw
            ("♥ Rose freshness",       "Citronellol", 30, N),
            ("♥ Rose sweet",           "Geraniol", 15, N),
            ("♥ Orange blossom",       "Aurantiol", 4, D1),
            ("♥ Sweet balsamic",       "Benzoin Resinoid", 10, N),
        ],
    },
    # ═══ VII — LEMON + MUGUET-LILY ═══
    # Lemon tree → flower is white lemon blossom, like crystalline lily
    {
        "tag": "VII Lemon",
        "brief": "Amalfi lemon tree: bright fruit, crystalline muguet-lily flower. Chanel, Acqua di Parma.",
        "fruit": ("Lemon FCF oil Sicilian", 4200),
        "petitgrain": 550,
        "linalyl_acetate": 200,
        "hedione": 1500,
        "hedione_hc": 180,
        "ethyl_linalool": 550,
        "flower": [
            ("♥ Muguet flower heart",  "Hydroxycitronellal", 12, N),
            ("♥ Crystalline lily",     "Nympheal", 5, N),
            ("♥ Ozone-green air",      "Floralozone", 0.15, D1),
            ("♥ Metallic sparkle",     "Scentenal", 0.06, D01),
        ],
    },
]

# ── Build & Calculate ──
out = []
w = out.append
w("# DEMACHY DHC REDUX — 7 Formulas")
w("")
w("Architecture: **Massive Citrus (tree fruit) → Tree Flower → Woody-Musk**")
w("OAV = VP(Pa) × active_µL × 20 / ODT_air(ppb) at 32°C. All formulas ~50mL EdP.")
w("")

for f in FORMULAS:
    fruit_name, fruit_dose = f["fruit"]
    rows = []
    rows.append(("PETITGRAIN",  "Petitgrain EO",         f["petitgrain"], N))
    rows.append(("LINALYL AC",  "Linalyl Acetate",       f["linalyl_acetate"], N))
    rows.append(("RADIANCE",    "Hedione",               f["hedione"], N))
    rows.append(("HC BOOST",    "Hedione HC",            f["hedione_hc"], N))
    rows.append(("CLEAN LIFT",  "Ethyl Linalool",        f["ethyl_linalool"], N))
    for role, mat, a, fn in f["flower"]:
        rows.append(("FLOWER", mat, a, fn))
    for role, mat, a in DRY:
        rows.append((role.replace("D ",""), mat, a, N))
    rows.append(("★ FRUIT ★",  fruit_name,              fruit_dose, N))

    scored = []
    for role, mat, a, fn in rows:
        v = vp(mat); d = odt(mat); oav = o(a, v, d)
        scored.append({"role": role, "mat": mat, "a": a, "raw": round(fn(a), 1),
                        "vp": v, "odt": d, "oav": oav})

    total = sum(s["oav"] for s in scored)
    ranked = sorted(scored, key=lambda s: s["oav"], reverse=True)
    ra = sum(s["raw"] for s in scored)
    aa = sum(s["a"] for s in scored)
    fruit_share = sum(s["oav"] for s in ranked if "FRUIT" in s["role"]) / total * 100
    flower_share = sum(s["oav"] for s in ranked if "FLOWER" in s["role"]) / total * 100
    dry_share = sum(s["oav"] for s in ranked if s["role"] not in ("FRUIT","FLOWER","PETITGRAIN","LINALYL AC","RADIANCE","HC BOOST","CLEAN LIFT")) / total * 100

    w(f"---")
    w(f"")
    w(f"## {f['tag']} — {fruit_name}")
    w(f"**{f['brief']}**")
    w(f"")
    w(f"**Concentrate:** {ra:,.0f} µL raw / {aa:,.0f} µL active | ~{50 - ra/1000:.0f} mL EtOH | {aa/1000/50*100:.0f}% EdP")
    w(f"**Materials:** {len(rows)} total | Citrus: {fruit_dose/aa*100:.0f}% of active mass")
    w(f"")
    w(f"### Headspace OAV")
    w(f"")
    w(f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | % |")
    w(f"|--:|----------|----------:|-------:|---------:|----:|---:|")
    for i, s in enumerate(ranked):
        od = f"{s['odt']:.4g}" if s['odt'] and s['odt'] != 9999 else ("—" if not s['odt'] else "—")
        icon = "🍊" if "FRUIT" in s["role"] else "🌸" if "FLOWER" in s["role"] else ""
        w(f"| {i+1:>2} | {s['mat']:<26} | {s['a']:>8.1f} | {s['vp']:>5.4f} | {od:>7} | {s['oav']:>6,.0f} | {s['oav']/total*100:>4.1f}% {icon} |")

    w(f"")
    w(f"| Layer | Share |")
    w(f"|---|------:|")
    w(f"| 🍊 Fruit | {fruit_share:.1f}% |")
    w(f"| 🌸 Flower | {flower_share:.1f}% |")
    w(f"| 🪵 Drydown | {dry_share:.1f}% |")
    w(f"")
    w(f"**Total OAV:** {total:,.0f} | **Fruit Rank:** #{next(i+1 for i,s in enumerate(ranked) if 'FRUIT' in s['role'])} | **Top 3:** {', '.join(s['mat'] for s in ranked[:3])}")
    w("")

with open("_demachy_redux.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"_demachy_redux.txt — {len(FORMULAS)} formulas written")
