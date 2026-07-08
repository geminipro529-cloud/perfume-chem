"""DHC Upgraded — 7 citrus formulas, OAV-first, each citrus paired with its signature flower.
Architecture: Star Citrus → Flower Heart → Woody-Musk Drydown = Demachy triptych.
"""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# ── Ensure missing ODTs ──
_ensures = {
    "blood orange sicilian":       {"odt_air": 8.0,  "odt_eth": 2.0, "char": "juicy sweet-tart berry-citrus"},
    "lemon fcf oil sicilian":      {"odt_air": 10.0, "odt_eth": 2.0, "char": "fresh bright lemon citrus, clean tart"},
    "lemon fcf sicilian":          {"odt_air": 10.0, "odt_eth": 2.0, "char": "fresh bright lemon citrus"},
    "petitgrain eo":               {"odt_air": 4.0,  "odt_eth": 1.0, "char": "petitgrain, green-citrus"},
    "cardamom eo":                 {"odt_air": 3.0,  "odt_eth": 0.5, "char": "cardamom, bright-spicy"},
    "ambrofix":                    {"odt_air": 0.3,  "odt_eth": 0.005, "char": "ambrox-smooth amber crystal"},
    "mayol":                       {"odt_air": 3.0,  "odt_eth": 0.5, "char": "muguet lily transparent"},
    "geraniol":                    {"odt_air": 2.22, "odt_eth": 0.3, "char": "rose geranium sweet"},
    "citronellol":                 {"odt_air": 40.0, "odt_eth": 5.0, "char": "rose fresh green"},
    "jessemal":                    {"odt_air": 5.0,  "odt_eth": 1.0, "char": "jasmine body tetrahydropyran acetate"},
}
for k, v in _ensures.items():
    if k not in ODT_DATA or "odt_air" not in ODT_DATA.get(k, {}):
        ODT_DATA[k] = v

PPM = 20.0
RAW = lambda a: a
P30 = lambda a: a / 0.30
P10 = lambda a: a / 0.10
P1  = lambda a: a / 0.01

def vp_odt(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    od = ODT_DATA.get(n, {})
    odt = od.get('odt_air') if od else None
    return vp, odt

def oav(active_ul, vp, odt):
    return vp * active_ul * PPM / odt if vp and odt else 0

# ═══════════════════════════════════════════════════════════════════
# DEMACHY TRIPTYCH: Citrus → Flower → Woody-Musk
# Each formula = Star Citrus + Signature Flower + Universal Drydown
# ═══════════════════════════════════════════════════════════════════

# ── Universal Drydown (shared woody-musk structure) ──
DRYDOWN = [
    ("Cedar structure",    "Iso E Super",            480),
    ("Proj. woody-musk",   "Romandolide",            480),
    ("Creamy musk",        "Ethylene Brassylate",    370),
    ("Amber crystal",      "Ambrofix",                18),
    ("Woody-amber-tobacco","Kephalis",                12),
    ("Dry-powerful wood",  "Norlimbanol Dextro",      42),
    ("Vetiver-suede",      "Vetival",                 40),
    ("Sandalwood whisper", "Javanol",                 16),
    ("Fruity musk",        "Ambrettolide",             0.15),
    ("Iris elegance",      "Alpha Irone",              0.45),
    ("Sparkle",            "Cardamom EO",              4),
]

# ── 7 Citrus-Flower Pairings (Demachy triptych heart) ──
# Each entry: (star_citrus_name, citrus_dose, [flower_heart_materials])
# Flower heart = (role_label, material, active_uL)

FORMULAS = [
    # ═══ I BERGMOT + ORANGE BLOSSOM ═══
    # Classic Calabrian pairing. Aurantiol is the orange blossom Schiff base.
    # Dihydrojasmone adds jasmine-fruity radiance. Alpha Damascone for rose depth.
    {
        "name": "I Bergamot",
        "brief": "Calabrian bergamot with orange blossom heart. Dior structure, Creed whisper.",
        "citrus": ("Bergamot FCF Sicilian", 2700),
        "petitgrain": 550,
        "linalyl_acetate": 180,
        "hedione": 1400,
        "hedione_hc": 170,
        "ethyl_linalool": 500,
        "flower": [
            ("Orange blossom ♥",  "Aurantiol",              5,    P10),
            ("Jasmine radiance",  "Dihydrojasmone",        25,    RAW),
            ("Rose depth",        "Alpha Damascone",        0.04, P10),
        ],
    },
    # ═══ II CEDRAT + JASMINE-COSTUS ═══
    # Bitter citron with animalic-suede jasmine. Le Labo eccentricity.
    {
        "name": "II Cedrat",
        "brief": "Bitter Mediterranean citron with jasmine-costus heart. Prada precision, Le Labo strangeness.",
        "citrus": ("Cedrat FCF Sicilian", 3200),
        "petitgrain": 600,
        "linalyl_acetate": 180,
        "hedione": 1350,
        "hedione_hc": 160,
        "ethyl_linalool": 480,
        "flower": [
            ("Jasmine heart ♥",   "Dihydrojasmone",        28,    RAW),
            ("Suede-leather",     "Suederal",               0.12, P10),
            ("Costus animalic",   "Costus Olifac",          0.04, P10),
            ("Apple depth",       "Damascenone",            0.0012, P1),
        ],
    },
    # ═══ III GRAPEFRUIT + JASMINE ═══
    # Bitter-clean grapefruit with jasmine heart. JM freshness, Atelier purity.
    {
        "name": "III Grapefruit",
        "brief": "Expensive grapefruit with jasmine heart. Subtraction over addition. JM freshness, Atelier purity.",
        "citrus": ("Grapefruit FCF", 2000),
        "petitgrain": 600,
        "linalyl_acetate": 350,
        "hedione": 1450,
        "hedione_hc": 170,
        "ethyl_linalool": 550,
        "flower": [
            ("Jasmine heart ♥",   "Dihydrojasmone",        25,    RAW),
            ("Jasmine body",      "Jessemal",               6,    RAW),
            ("Rose depth",        "Alpha Damascone",        0.03, P10),
            ("Tropical whisper",  "Paradisamide",           0.5,  P10),
            ("Apricot lift",      "Apritone",               2,    RAW),
        ],
    },
    # ═══ IV LIME + MUGUET ═══
    # Cold lime with muguet heart. Hermès clarity, Byredo Scandinavian.
    {
        "name": "IV Lime",
        "brief": "Cold Caribbean lime with muguet-lily heart. Hermès transparency, Byredo restraint.",
        "citrus": ("Lime Distilled EO", 3100),
        "petitgrain": 650,
        "linalyl_acetate": 160,
        "hedione": 1350,
        "hedione_hc": 150,
        "ethyl_linalool": 480,
        "flower": [
            ("Muguet heart ♥",    "Hydroxycitronellal",    8,    RAW),
            ("Muguet-transparent","Mayol",                 5,    RAW),
            ("Ozone green",       "Floralozone",           0.12, P10),
            ("Metallic ozone",    "Scentenal",             0.04, P1),
            ("Tropical whisper",  "Paradisamide",          0.3,  P10),
        ],
    },
    # ═══ V MANDARIN + JASMINE-ORANGE BLOSSOM ═══
    # Sweet tangerine with jasmine-orange blossom. TF opulence, Malle artistry.
    {
        "name": "V Mandarin",
        "brief": "Sicilian tangerine with jasmine-orange blossom heart. TF opulence, Malle artistry.",
        "citrus": ("Red Mandarin EO", 2600),
        "petitgrain": 500,
        "linalyl_acetate": 250,
        "hedione": 1400,
        "hedione_hc": 180,
        "ethyl_linalool": 480,
        "flower": [
            ("Jasmine heart ♥",   "Dihydrojasmone",        30,    RAW),
            ("Orange blossom",    "Aurantiol",              5,    P10),
            ("Jasmine accord",    "Jasmine FO",            50,    RAW),
            ("Apple depth",       "Damascenone",            0.0015, P1),
            ("Tropical whisper",  "Paradisamide",           0.5,  P10),
            ("Sweet balsamic",    "Benzoin Resinoid",      12,    RAW),
        ],
    },
    # ═══ VI BLOOD ORANGE + ROSE ═══
    # Berry-tinged blood orange with rose-damascone heart. Jammy, oriental-citrus.
    {
        "name": "VI Blood Orange",
        "brief": "Berry-tinged blood orange with rose-damascone heart. Shalimar meets DHC.",
        "citrus": ("Blood Orange Sicilian", 2800),
        "petitgrain": 550,
        "linalyl_acetate": 220,
        "hedione": 1400,
        "hedione_hc": 170,
        "ethyl_linalool": 500,
        "flower": [
            ("Rose heart ♥",      "Alpha Damascone",        0.06, P10),
            ("Rose-plum depth",   "Damascenone",            0.0025, P1),
            ("Rose freshness",    "Citronellol",           25,    RAW),
            ("Rose sweet",        "Geraniol",              12,    RAW),
            ("Tropical heart",    "Paradisamide",           0.6,  P10),
            ("Orange blossom",    "Aurantiol",              4,    P10),
            ("Sweet balsamic",    "Benzoin Resinoid",      10,    RAW),
        ],
    },
    # ═══ VII LEMON + MUGUET-LILY ═══
    # Bright lemon with muguet-lily heart. Chanel crystalline, Acqua di Parma solarity.
    {
        "name": "VII Lemon",
        "brief": "Bright Amalfi lemon with muguet-lily heart. Chanel crystalline, Acqua di Parma solarity.",
        "citrus": ("Lemon FCF oil Sicilian", 3100),
        "petitgrain": 550,
        "linalyl_acetate": 200,
        "hedione": 1400,
        "hedione_hc": 170,
        "ethyl_linalool": 500,
        "flower": [
            ("Muguet heart ♥",    "Hydroxycitronellal",    10,    RAW),
            ("Muguet-lily",       "Nympheal",              4,    RAW),
            ("Ozone-green",       "Floralozone",           0.15, P10),
            ("Metallic ozone",    "Scentenal",             0.05, P1),
            ("Orange blossom",    "Aurantiol",              4,    P10),
            ("Apple depth",       "Damascenone",            0.001, P1),
            ("Tropical whisper",  "Paradisamide",           0.3,  P10),
        ],
    },
]

out = []
w = out.append
w("# DHC UPGRADED — 7 Citrus Formulas (Demachy Triptych: Citrus → Flower → Woody-Musk)")
w("")
w("All formulas: **50 mL EdP**, OAV = VP(Pa) × µL × 20 / ODT(ppb) at 32°C")
w("Architecture: Star Citrus + Signature Flower Heart + Universal Woody-Musk Drydown")
w("")

for f in FORMULAS:
    label = f["name"]
    citrus_name, citrus_dose = f["citrus"]
    
    # Build: Petitgrain bridge → Linalyl Acetate → Hedione(s) → Ethyl Linalool → Flower → Drydown → Star Citrus
    rows = []
    
    # Green-citrus bridge
    rows.append(("B Green bridge", "Petitgrain EO", f["petitgrain"], RAW))
    rows.append(("B Bright floral", "Linalyl Acetate", f["linalyl_acetate"], RAW))
    
    # Radiance backbone
    rows.append(("B Radiance", "Hedione", f["hedione"], RAW))
    rows.append(("B Hedione HC", "Hedione HC", f["hedione_hc"], RAW))
    rows.append(("B Clean lift", "Ethyl Linalool", f["ethyl_linalool"], RAW))
    
    # ♥ Flower Heart ♥
    for role, mat, active, fn in f["flower"]:
        rows.append(("♥ " + role, mat, active, fn))
    
    # Woody-Musk Drydown
    for role, mat, active in DRYDOWN:
        rows.append(("D " + role, mat, active, RAW))
    
    # ★ Star Citrus ★ (last = poured on top)
    rows.append(("★ CITRUS ★", citrus_name, citrus_dose, RAW))
    
    # Calculate
    scored = []
    for role, mat, active, raw_fn in rows:
        vp, odt = vp_odt(mat)
        raw_ul = raw_fn(active)
        oav_val = oav(active, vp, odt)
        scored.append({"role": role, "mat": mat, "active": active, "raw": raw_ul,
                        "vp": vp, "odt": odt, "oav": oav_val})
    
    total_oav = sum(s["oav"] for s in scored)
    ranked = sorted(scored, key=lambda s: s["oav"], reverse=True)
    total_raw = sum(s["raw"] for s in scored)
    total_active = sum(s["active"] for s in scored)
    
    cit_oav = sum(s["oav"] for s in ranked if "CITRUS" in s["role"])
    pg_oav = sum(s["oav"] for s in ranked if "bridge" in s["role"].lower() or "petitgrain" in s["mat"].lower())
    flower_oav = sum(s["oav"] for s in ranked if "♥" in s["role"])
    drydown_oav = sum(s["oav"] for s in ranked if s["role"].startswith("D "))
    backbone_oav = sum(s["oav"] for s in ranked if s["role"].startswith("B "))
    
    w(f"---")
    w(f"")
    w(f"## {label} — {citrus_name}")
    w(f"")
    w(f"**Brief:** {f['brief']}")
    w(f"**Flower Heart:** {', '.join(s['mat'] for s in scored if '♥' in s['role'])}")
    w(f"")
    w(f"**Concentrate:** {total_raw:,.0f} µL raw / {total_active:,.0f} µL active | Fill: ~{50 - total_raw/1000:.0f} mL EtOH")
    w(f"")
    w(f"### Formula")
    w(f"")
    w(f"| # | Role | Material | Dilution | Raw µL | Active µL |")
    w(f"|--:|------|----------|----------|-------:|----------:|")
    for i, s in enumerate(scored):
        dil = "neat" if abs(s["raw"] - s["active"]) < 0.01 else f"{s['active']/s['raw']*100:.0f}%"
        w(f"| {i+1:>2} | {s['role']:<20} | {s['mat']:<26} | {dil:<8} | {s['raw']:>7.1f} | {s['active']:>8.1f} |")
    
    w(f"")
    w(f"*Add ethanol to 50 mL. Invert 50×. Macerate 4 weeks.*")
    w(f"")
    w(f"### Headspace OAV Ranked")
    w(f"")
    w(f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | %Share | Role |")
    w(f"|--:|----------|----------:|-------:|---------:|----:|-------:|------|")
    for i, s in enumerate(ranked):
        odt_str = f"{s['odt']:.4g}" if s['odt'] else "—"
        role_icon = "★" if "CITRUS" in s["role"] else "♥" if "♥" in s["role"] else "D" if s["role"].startswith("D ") else "B" if s["role"].startswith("B ") else ""
        w(f"| {i+1:>2} | {s['mat']:<26} | {s['active']:>8.1f} | {s['vp']:>5.4f} | {odt_str:>7} | {s['oav']:>6,.0f} | {s['oav']/total_oav*100:>5.1f}% | {role_icon} |")
    
    w(f"")
    w(f"**Total Headspace OAV:** {total_oav:,.0f}")
    w(f"")
    w(f"| Layer | OAV Share |")
    w(f"|-------|----------|")
    w(f"| ★ Star Citrus | {cit_oav/total_oav*100:.1f}% |")
    w(f"| ♥ Flower Heart | {flower_oav/total_oav*100:.1f}% |")
    w(f"| B Backbone (Hedione/IES/etc.) | {backbone_oav/total_oav*100:.1f}% |")
    w(f"| D Woody-Musk Drydown | {drydown_oav/total_oav*100:.1f}% |")
    w(f"")
    w(f"**Star Citrus Rank:** #{next((i+1 for i, s in enumerate(ranked) if 'CITRUS' in s['role']), 0)}")
    w(f"**Top 5:** {', '.join(s['mat'] for s in ranked[:5])}")
    w("")

with open("_dhc_upgraded_7_v2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written _dhc_upgraded_7_v2.txt")
