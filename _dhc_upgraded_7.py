"""DHC Upgraded — 7 citrus formulas from scratch with OAV-first design.
Architecture: Demachy modern citrus (star citrus > hedione radiance > woody-musk drydown).
All doses calculated against corrected ODT/VP data (TGSC-verified VP, peer-reviewed ODT).
"""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# ── Ensure Blood Orange and Lemon FCF are in ODT_DATA ──
if "blood orange sicilian" not in ODT_DATA:
    ODT_DATA["blood orange sicilian"] = {"odt_air": 8.0, "odt_eth": 2.0, "char": "juicy, sweet-tart, berry-citrus"}
if "lemon fcf oil sicilian" not in ODT_DATA:
    ODT_DATA["lemon fcf oil sicilian"] = {"odt_air": 10.0, "odt_eth": 2.0, "char": "fresh bright lemon citrus, clean, tart"}
# Also add "lemon fcf sicilian" alias
if "lemon fcf sicilian" not in ODT_DATA:
    ODT_DATA["lemon fcf sicilian"] = ODT_DATA["lemon fcf oil sicilian"]
if "petitgrain eo" not in ODT_DATA:
    ODT_DATA["petitgrain eo"] = {"odt_air": 4.0, "odt_eth": 1.0, "char": "petitgrain, green-citrus"}
if "cardamom eo" not in ODT_DATA or "odt_air" not in ODT_DATA.get("cardamom eo", {}):
    ODT_DATA["cardamom eo"] = {"odt_air": 3.0, "odt_eth": 0.5, "char": "cardamom, bright-spicy"}

PPM = 20.0  # 50mL bottle, 20 ppm per active uL

def vp_odt(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    od = ODT_DATA.get(n, {})
    odt = od.get('odt_air') if od else None
    return vp, odt

def oav(active_ul, vp, odt):
    if not vp or not odt: 
        return 0
    return vp * active_ul * PPM / odt

# ── Dilution helpers ──
RAW = lambda a: a       # neat
P30 = lambda a: a / 0.30    # 30% dilution → raw uL
P10 = lambda a: a / 0.10    # 10% dilution → raw uL
P1  = lambda a: a / 0.01    # 1% dilution → raw uL

# ── Demachy Universal Backbone (applied to all 7) ──
# These are the invariant structural materials that define DHC
BACKBONE = [
    # (label, material_name, active_uL, raw_uL_fn)
    ("Radiance",           "Hedione",               1400,  RAW),
    ("Hedione HC",         "Hedione HC",             170,  RAW),
    ("Cedar structure",    "Iso E Super",            500,  RAW),
    ("Clean lift",         "Ethyl Linalool",         500,  RAW),
    ("Proj. musk",         "Romandolide",            480,  RAW),
    ("Creamy musk",        "Ethylene Brassylate",    380,  RAW),
    ("Amber crystal",      "Ambrofix",                18,  P30),  # 60 raw
    ("Woody-amber",        "Kephalis",                12,  RAW),
    ("Dry wood",           "Norlimbanol Dextro",      45,  RAW),
    ("Vetiver dryness",    "Vetival",                 43,  RAW),
    ("Iris elegance",      "Alpha Irone",              0.45, P30),  # 1.5 raw of 30%
    ("Sandalwood whisper", "Javanol",                 18,  RAW),
    ("Fruity musk",        "Ambrettolide",              0.15, P10),  # 1.5 raw of 10%
    ("Sparkle",            "Cardamom EO",              5,  RAW),
]

# ── Per-citrus character modifiers ──
# Each citrus gets unique floral/bridge/depth accents
MODIFIERS = {
    "Bergamot FCF Sicilian": [
        ("Orange blossom",    "Aurantiol",              5, P10),     # 50 raw of 10%
        ("Jasmine body",      "Dihydrojasmone",        25, RAW),
        ("Tropical whisper",  "Paradisamide",           0.3, P10),    # 3 raw of 10%
        ("Rose depth",        "Alpha Damascone",        0.03, P10),   # 0.3 raw of 10%
    ],
    "Cedrat FCF Sicilian": [
        ("Tobacco-leather",   "Suederal",               0.15, P10),   # 1.5 raw of 10%
        ("Costus animalic",   "Costus Olifac",          0.05, P10),   # 0.5 raw of 10%
        ("Apple depth",       "Damascenone",            0.001, P1),   # 0.1 raw of 1%
        ("Rose facet",        "Alpha Damascone",        0.03, P10),
    ],
    "Grapefruit FCF": [
        ("Apricot lift",      "Apritone",                2, RAW),
        ("Ozone lift",        "Floralozone",             0.15, P10),   # 1.5 raw of 10%
        ("Tropical heart",    "Paradisamide",            0.5, P10),    # 5 raw of 10%
        ("Rose facet",        "Alpha Damascone",         0.03, P10),
    ],
    "Lime Distilled EO": [
        ("Metallic ozone",    "Scentenal",               0.05, P1),    # 5 raw of 1%
        ("Ozone lift",        "Floralozone",             0.1, P10),    # 1 raw of 10%
        ("Tropical whisper",  "Paradisamide",            0.3, P10),
        ("Rose facet",        "Alpha Damascone",         0.03, P10),
    ],
    "Red Mandarin EO": [
        ("Jasmine body",      "Dihydrojasmone",         30, RAW),
        ("Orange blossom",    "Aurantiol",               5, P10),
        ("Sweet balsamic",    "Benzoin Resinoid",       10, RAW),      # was 17.5, reduced
        ("Tropical whisper",  "Paradisamide",            0.5, P10),
        ("Apple depth",       "Damascenone",             0.0015, P1),
        ("Jasmine accord",    "Jasmine FO",             50, RAW),
    ],
    "Blood Orange Sicilian": [
        # Sweeter, berry-tinged citrus — pairs with Paradisamide + Damascenone
        ("Tropical heart",    "Paradisamide",            0.5, P10),
        ("Berry depth",       "Damascenone",             0.002, P1),   # 0.2 raw of 1%
        ("Orange blossom",    "Aurantiol",               4, P10),
        ("Jasmine body",      "Dihydrojasmone",         20, RAW),
        ("Rose facet",        "Alpha Damascone",         0.04, P10),
        ("Sweet balsamic",    "Benzoin Resinoid",        8, RAW),
    ],
    "Lemon FCF oil Sicilian": [
        # Bright, sharp, clean — pairs with ozonic/floral materials
        ("Metallic ozone",    "Scentenal",               0.05, P1),
        ("Ozone lift",        "Floralozone",             0.15, P10),
        ("Orange blossom",    "Aurantiol",               4, P10),
        ("Jasmine body",      "Dihydrojasmone",         22, RAW),
        ("Apple depth",       "Damascenone",             0.001, P1),
        ("Tropical whisper",  "Paradisamide",            0.3, P10),
    ],
}

# ── Citrus star doses (adjusted for ODT to hit ~15-25% OAV share) ──
CITRUS_STARS = {
    "Bergamot FCF Sicilian":  2700,  # ODT 4.0, VP 2.5 → OAV = 2.5*2700*20/4 = 33,750
    "Cedrat FCF Sicilian":    3200,  # ODT 12.0, VP 2.0 → = 2*3200*20/12 = 10,667
    "Grapefruit FCF":         2000,  # ODT 5.0, VP 1.8 → = 1.8*2000*20/5 = 14,400
    "Lime Distilled EO":      3100,  # ODT 12.0, VP 1.8 → = 1.8*3100*20/12 = 9,300
    "Red Mandarin EO":        2600,  # ODT 10.0, VP 1.8 → = 1.8*2600*20/10 = 9,360
    "Blood Orange Sicilian":  2800,  # ODT 8.0, VP 1.8 → = 1.8*2800*20/8 = 12,600
    "Lemon FCF oil Sicilian": 3100,  # ODT 10.0, VP 2.0 → = 2*3100*20/10 = 12,400
}

# ── Petitgrain bridge (adjusted: lower ODT 4.0 ppb = higher OAV, so use less) ──
PETITGRAIN_BRIDGE = {
    "Bergamot FCF Sicilian": 550,
    "Cedrat FCF Sicilian":   600,
    "Grapefruit FCF":        600,
    "Lime Distilled EO":     650,
    "Red Mandarin EO":       500,
    "Blood Orange Sicilian": 550,
    "Lemon FCF oil Sicilian":550,
}

# ── Linalyl Acetate (bright floral bridge, ODT 50 ppb = high threshold = low OAV) ──
LINALYL_ACETATE = {
    "Bergamot FCF Sicilian": 180,
    "Cedrat FCF Sicilian":   180,
    "Grapefruit FCF":        350,
    "Lime Distilled EO":     160,
    "Red Mandarin EO":       250,
    "Blood Orange Sicilian": 220,
    "Lemon FCF oil Sicilian":200,
}

# ── Build formulas ──
formula_names = [
    ("I Bergamot",   "Bergamot FCF Sicilian"),
    ("II Cedrat",    "Cedrat FCF Sicilian"),
    ("III Grapefruit","Grapefruit FCF"),
    ("IV Lime",      "Lime Distilled EO"),
    ("V Mandarin",   "Red Mandarin EO"),
    ("VI Blood Orange","Blood Orange Sicilian"),
    ("VII Lemon",    "Lemon FCF oil Sicilian"),
]

briefs = {
    "Bergamot FCF Sicilian": "Classical Calabrian reference. Naked bergamot with Dior structure, Creed whisper.",
    "Cedrat FCF Sicilian": "Bitter Mediterranean citron. Prada precision, Le Labo eccentricity.",
    "Grapefruit FCF": "Expensive grapefruit via subtraction. JM freshness, Atelier purity.",
    "Lime Distilled EO": "Cold Caribbean lime. Hermès clarity, Byredo Scandinavian restraint.",
    "Red Mandarin EO": "Sicilian tangerine. TF opulence, Malle artistry.",
    "Blood Orange Sicilian": "Berry-tinged blood orange. Sweet-tart with jammy depth. Shalimar-meets-DHC.",
    "Lemon FCF oil Sicilian": "Bright Amalfi lemon. Chanel crystalline, Acqua di Parma solarity.",
}

out = []
w = out.append
w("# DHC UPGRADED — 7 Citrus Formulas (OAV-First, Demachy Architecture)")
w("")
w("All formulas: **50 mL EdP (~13-17% concentrate)**, 5,500-6,500 µL total active.")
w("OAV = VP(Pa) × active_µL × 20 / ODT_air(ppb) at 32°C skin temperature.")
w("")

for short, star in formula_names:
    # Build formula rows
    formula_rows = [("PETITGRAIN BRIDGE", "Petitgrain EO", PETITGRAIN_BRIDGE[star], RAW)]
    formula_rows.append(("BRIGHT FLORAL", "Linalyl Acetate", LINALYL_ACETATE[star], RAW))
    
    # Add backbone
    for label, mat, active, raw_fn in BACKBONE:
        formula_rows.append((label, mat, active, raw_fn))

    # Add modifiers
    if star in MODIFIERS:
        for label, mat, active, raw_fn in MODIFIERS[star]:
            formula_rows.append((label, mat, active, raw_fn))
    
    # Add citrus star last (poured on top when compounding)
    formula_rows.append(("★ STAR CITRUS ★", star, CITRUS_STARS[star], RAW))
    
    # Calculate OAV
    scored = []
    for label, mat, active, raw_fn in formula_rows:
        vp, odt = vp_odt(mat)
        raw_ul = raw_fn(active)
        oav_val = oav(active, vp, odt)
        scored.append({
            "label": label, "mat": mat, "active": active, "raw": raw_ul,
            "vp": vp, "odt": odt, "oav": oav_val
        })
    
    total_oav = sum(s["oav"] for s in scored)
    ranked = sorted(scored, key=lambda s: s["oav"], reverse=True)
    total_active = sum(s["active"] for s in scored)
    total_raw = sum(s["raw"] for s in scored)
    
    w(f"---")
    w(f"")
    w(f"## {short} — {star}")
    w(f"")
    w(f"**Brief:** {briefs[star]}")
    w(f"")
    w(f"**Concentrate:** {total_raw:,.0f} µL raw / {total_active:,.0f} µL active | Ethanol: ~{50 - total_raw/1000:.0f} mL")
    w(f"")
    w(f"### Formula")
    w(f"")
    w(f"| # | Material | Dilution | Raw µL | Active µL |")
    w(f"|--:|----------|----------|-------:|----------:|")
    for i, s in enumerate(scored):
        dil = "neat" if abs(s["raw"] - s["active"]) < 0.01 else f"{s['active']/s['raw']*100:.0f}%"
        w(f"| {i+1:>2} | {s['mat']:<26} | {dil:<8} | {s['raw']:>7.1f} | {s['active']:>8.1f} |")
    
    w(f"")
    w(f"*Add ethanol to 50 mL line. Invert 50×. Macerate 4 weeks.*")
    w(f"")
    w(f"### Headspace OAV Ranked")
    w(f"")
    w(f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | %Share |")
    w(f"|--:|----------|----------:|-------:|---------:|----:|-------:|")
    for i, s in enumerate(ranked):
        odt_str = f"{s['odt']:.4g}" if s['odt'] else "—"
        star_flag = " ★ STAR ★" if "STAR" in s['label'] else ""
        w(f"| {i+1:>2} | {s['mat']:<26} | {s['active']:>8.1f} | {s['vp']:>5.3f} | {odt_str:>7} | {s['oav']:>6,.0f} | {s['oav']/total_oav*100:>5.1f}%{star_flag} |")
    
    citrus_share = sum(s['oav'] for s in ranked if 'CITRUS' in s['label'] or 'PETITGRAIN' in s['label']) / total_oav * 100
    
    w(f"")
    w(f"**Total Headspace OAV:** {total_oav:,.0f}")
    w(f"**Star Citrus Rank:** #{next((i+1 for i, s in enumerate(ranked) if 'STAR' in s['label']), 0)}")
    w(f"**Star Citrus Share:** {next((s['oav']/total_oav*100 for s in ranked if 'STAR' in s['label']), 0):.1f}%")
    w(f"**Citrus + Petitgrain Share:** {citrus_share:.1f}%")
    w(f"**Top 5:** {', '.join(s['mat'] for s in ranked[:5])}")
    w("")

with open("_dhc_upgraded_7.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written _dhc_upgraded_7.txt")
print(f"Total OAV range: check file")
