"""House review panel: 8 houses rate all 7 Demachy formulas on their signature criteria.
Each house = 5 criteria scored 1-10. Each house ranks formulas 1-7.
"""

import json

formulas = [
    {"id": "I",   "name": "Bergamot + Orange Blossom",   "citrus": "Bergamot FCF Sicilian", "flower": "Orange Blossom (Aurantiol)", "oav": 271020, "fruit_rank": 2, "fruit_pct": 19.4},
    {"id": "II",  "name": "Cedrat + Costus-Suede",       "citrus": "Cedrat FCF Sicilian", "flower": "Costus-Suede Jasmine", "oav": 226597, "fruit_rank": 4, "fruit_pct": 7.4},
    {"id": "III", "name": "Grapefruit + Jasmine",        "citrus": "Grapefruit FCF", "flower": "Jasmine (Dihydrojasmone)", "oav": 276112, "fruit_rank": 2, "fruit_pct": 16.5},
    {"id": "IV",  "name": "Lime + Muguet",               "citrus": "Lime Distilled EO", "flower": "Muguet (Hydroxycitronellal)", "oav": 216838, "fruit_rank": 5, "fruit_pct": 5.8},
    {"id": "V",   "name": "Mandarin + Jasmin-OrBlossom", "citrus": "Red Mandarin EO", "flower": "Jasmine-Orange Blossom", "oav": 234148, "fruit_rank": 5, "fruit_pct": 5.8},
    {"id": "VI",  "name": "Blood Orange + Rose",         "citrus": "Blood Orange Sicilian", "flower": "Rose-Damascone", "oav": 241376, "fruit_rank": 3, "fruit_pct": 12.4},
    {"id": "VII", "name": "Lemon + Muguet-Lily",         "citrus": "Lemon FCF Sicilian", "flower": "Muguet-Lily (Nympheal)", "oav": 232274, "fruit_rank": 3, "fruit_pct": 9.0},
]

houses = {
    "Dior / François Demachy": {
        "criteria": ["Transparency", "Structure", "Elegance", "Wearability", "Citrus Purity"],
        "scores": {
            "I":   [9,9,8,8,10],   # His own creation — perfect match
            "II":  [7,8,7,6,7],    # Too strange for Dior
            "III": [8,8,9,9,9],    # Grapefruit elegance
            "IV":  [8,9,8,8,7],    # Clean, transparent
            "V":   [8,8,8,7,8],    # Mandarin is good but less pure
            "VI":  [7,7,8,6,7],    # Rose makes it too rich for Dior
            "VII": [9,9,9,9,9],    # Lemon = his other favorite
        },
        "quote": "Citrus is the universe. Everything else orbits it."
    },
    "Chanel / Olivier Polge": {
        "criteria": ["Crystalline Precision", "Timelessness", "Refinement", "Abstraction", "Clean Musk"],
        "scores": {
            "I":   [8,9,8,7,8],    # Bergamot is classic but a bit expected
            "II":  [7,6,7,8,6],    # Too weird for Chanel
            "III": [9,8,9,8,9],    # Grapefruit subtraction = Chanel philosophy
            "IV":  [9,9,9,9,8],    # Lime + muguet = crystalline perfection
            "V":   [7,8,8,7,7],    # Mandarin is safe
            "VI":  [7,8,9,7,7],    # Interesting but too Guerlain
            "VII": [10,9,9,9,9],   # Lemon + muguet-lily = Chanel DNA
        },
        "quote": "Luxury is what you don't see. The invisible structure."
    },
    "Hermès / Christine Nagel": {
        "criteria": ["Clarity", "Naturalness", "Green Character", "Subtlety", "Material Quality"],
        "scores": {
            "I":   [8,7,7,7,9],    # Good but not her style
            "II":  [6,8,8,6,7],    # Cedrat is natural, but costus is divisive
            "III": [7,7,6,8,8],    # Clean grapefruit
            "IV":  [10,9,9,10,9],  # Lime + muguet = HER signature
            "V":   [7,8,7,8,8],    # Pleasant
            "VI":  [6,7,7,6,8],    # Rose makes it heavy
            "VII": [9,8,8,9,9],    # Lemon bright = Hermès DNA
        },
        "quote": "I want to smell the material, not the formula."
    },
    "Tom Ford / Rodrigo Flores-Roux": {
        "criteria": ["Boldness", "Sensuality", "Impact", "Sillage", "Sex Appeal"],
        "scores": {
            "I":   [6,7,7,7,7],    # Bergamot is too polite
            "II":  [9,8,8,7,8],    # Cedrat + costus = BOLD and strange
            "III": [9,9,9,9,9],    # Grapefruit + jasmine = sexy and bold
            "IV":  [5,5,6,6,5],    # Lime is too cold, not sensual
            "V":   [8,9,8,8,9],    # Mandarin + jasmine = opulent
            "VI":  [8,9,9,8,10],   # Blood orange + rose = pure sex
            "VII": [7,7,8,8,7],    # Lemon is clean but not bold
        },
        "quote": "If you're not noticed, you don't exist."
    },
    "Guerlain / Thierry Wasser": {
        "criteria": ["Richness", "Oriental Depth", "Complexity", "Gourmand Quality", "Drydown Beauty"],
        "scores": {
            "I":   [6,5,7,5,7],    # Too simple for Guerlain
            "II":  [8,7,9,6,8],    # Complex, strange — respect
            "III": [7,6,7,5,7],    # Clean but lacks depth
            "IV":  [5,4,6,4,6],    # Too cold, not rich enough
            "V":   [8,8,8,7,8],    # Mandarin + jasmine + benzoin = Guerlainable
            "VI":  [10,10,9,9,9],  # Blood orange + rose = Shalimar cousin
            "VII": [7,6,7,5,7],    # Pleasant but simple
        },
        "quote": "A perfume without a base is a story without an ending."
    },
    "Le Labo / Daphné Bugey": {
        "criteria": ["Originality", "Eccentricity", "Artistic Quality", "Narrative", "Anti-Mass Appeal"],
        "scores": {
            "I":   [5,4,7,6,3],    # Too mainstream
            "II":  [10,10,9,10,10],# Cedrat + costus + suede = Le Labo PERFECT
            "III": [6,5,8,7,5],    # Nice but safe
            "IV":  [7,6,8,7,5],    # Clean but safe
            "V":   [6,5,7,6,4],    # Nice but safe
            "VI":  [8,7,9,9,7],    # Rose + blood orange = artistic
            "VII": [5,4,7,6,3],    # Too mainstream
        },
        "quote": "If everyone likes it, I've failed."
    },
    "Frédéric Malle / Dominique Ropion": {
        "criteria": ["Technical Mastery", "Balance", "Innovation", "Overdose Courage", "Signature Mark"],
        "scores": {
            "I":   [8,8,6,7,8],    # Well-made but derivative of DHC
            "II":  [9,8,9,9,9],    # Costus overdose = Ropion courage
            "III": [9,9,8,8,8],    # Subtraction is mastery
            "IV":  [8,8,7,7,7],    # Good balance
            "V":   [9,9,8,8,9],    # Jasmine-OrBlossom accord = technical
            "VI":  [9,8,9,8,9],    # Rose-damascone = beautiful risk
            "VII": [8,9,7,7,7],    # Clean and precise
        },
        "quote": "The difference between a good formula and a masterpiece is the last 5%."
    },
    "YSL / Mathilde Laurent": {
        "criteria": ["Chic", "Daring", "Parisian Edge", "Noir Quality", "Leather-Tobacco Affinity"],
        "scores": {
            "I":   [8,5,6,4,5],    # Too polite, not enough edge
            "II":  [8,9,8,8,9],    # Costus + suede = YSL edge PERFECT
            "III": [9,7,7,6,6],    # Chic grapefruit
            "IV":  [6,5,6,4,4],    # Too cold
            "V":   [7,8,7,7,7],    # Mandarin + jasmine = Parisian
            "VI":  [7,7,8,8,7],    # Rose + blood orange = noir-ish
            "VII": [7,6,7,5,5],    # Bright but safe
        },
        "quote": "A woman in a man's suit. That's the YSL edge."
    },
}

out = []
w = out.append
w("# DHC REDUX — 8-HOUSE REVIEW PANEL")
w("")
w("Each house rates all 7 formulas on their 5 signature criteria (1-10).")
w("Formula IDs: I=Bergamot, II=Cedrat, III=Grapefruit, IV=Lime, V=Mandarin, VI=Blood Orange, VII=Lemon")
w("")

# ── Individual house reviews ──
for house_name, h in houses.items():
    w(f"## {house_name}")
    w(f"> *\"{h['quote']}\"*")
    w(f"")
    w(f"**Criteria:** {', '.join(h['criteria'])}")
    w(f"")
    w(f"| # | Formula | {' | '.join(h['criteria'])} | **Avg** |")
    w(f"|---|---------|{'|'.join(['---:' for _ in h['criteria']])}|-----:|")
    
    totals = {}
    for f in formulas:
        scores = h["scores"][f["id"]]
        avg = sum(scores) / len(scores)
        totals[f["id"]] = avg
        w(f"| {f['id']} | {f['name']:<30} | {' | '.join(str(s) for s in scores)} | **{avg:.1f}** |")
    
    # House ranking
    ranked_houses = sorted(formulas, key=lambda f: totals[f["id"]], reverse=True)
    w(f"")
    ranks = ' > '.join(f'{r["id"]} ({totals[r["id"]]:.1f})' for r in ranked_houses)
    w(f"**House ranking:** {ranks}")
    w("")

# ── Cross-house matrix ──
w("---")
w("")
w("## CROSS-HOUSE MATRIX (Average Score)")
w("")
w(f"| Formula | {' | '.join(h.split('/')[0].strip() for h in houses.keys())} | **Overall** |")
w(f"|---------|{'|'.join(['---:' for _ in houses])}|---------:|")

all_avgs = {}
for f in formulas:
    row = []
    for house_name, h in houses.items():
        avg = sum(h["scores"][f["id"]]) / len(h["scores"][f["id"]])
        row.append(avg)
    overall = sum(row) / len(row)
    all_avgs[f["id"]] = overall
    w(f"| {f['id']} {f['name']:<30} | {' | '.join(f'{r:.1f}' for r in row)} | **{overall:.1f}** |")

# ── Grand ranking ──
w("")
w("## FINAL RANKING (Cross-House Consensus)")
w("")
ranked_all = sorted(formulas, key=lambda f: all_avgs[f["id"]], reverse=True)
for i, f in enumerate(ranked_all):
    w(f"| {i+1} | **{f['id']} {f['name']}** | {all_avgs[f['id']]:.1f} | {f['citrus']} + {f['flower']} |")

# ── House alignment ──
w("")
w("## BEST HOUSE FIT (Each Formula's Natural Home)")
w("")
for f in formulas:
    best_house = max(houses.items(), key=lambda h: sum(h[1]["scores"][f["id"]]) / len(h[1]["scores"][f["id"]]))
    best_score = sum(best_house[1]["scores"][f["id"]]) / len(best_house[1]["scores"][f["id"]])
    w(f"| **{f['id']}** | {f['name']} | **{best_house[0]}** | {best_score:.1f} |")

with open("_demachy_house_review.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written _demachy_house_review.txt")
