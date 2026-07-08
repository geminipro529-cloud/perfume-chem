#!/usr/bin/env python3
"""Demachy's red-pen adjustments to each OAV-first DHC formula."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM_FACTOR = 20.0

def mat(name):
    n = normalize_name(name)
    p = get_profile(name)
    odt = ODT_DATA.get(n, {}) or ODT_DATA.get(name.lower(), {})
    return p.vp if p and p.vp else 0, odt.get('odt_air'), odt.get('odt_eth')

def h_oav(active, vp, odt_a):
    return vp * active * PPM_FACTOR / odt_a if vp and odt_a else 0

# Demachy's principles for tuning his own DHCs:
# 1. Citrus star at 40-45% of headspace (not 48-54%). Let the architecture breathe.
# 2. Petitgrain boosted — it IS the structural material. Target 30%+.
# 3. Ambrofix is correct at 185. His signature. Don't touch.
# 4. Hedione reduced — radiance should be felt, not detected. Target OAV 200-240.
# 5. Romandolide reduced — more intimate. Target OAV 900-1000.
# 6. IES reduced — molecular cocoon should whisper. Target OAV 220.
# 7. Add Alpha Irone (30%, 5uL) — orris whisper. Every Demachy formula has one.
# 8. Add Cardamom EO (5uL) at trace — the Grasse perfumer's spice lift.
# 9. Linalyl Acetate reduced — freshness is juvenile. Let the citrus do its own work.
# 10. Reduce Ethyl Linalool — softness is not transparency.

# --- OAV-first (before) vs Demachy's tune (after) ---
# (name, dilution, active_before, active_after, reason_for_change)

adjustments = {
    "I Bergamot": [
        ("Bergamot FCF Sicilian", "neat",  3000.0, 2600.0, "48% too dominant. Refined bergamot should charm, not announce."),
        ("Linalyl Acetate",       "neat",   385.7,  280.0,  "Freshness juvenile. Let bergamot carry the top unaided."),
        ("Hedione",               "neat",  1785.7, 1450.0,  "Radiance should be felt, not smelled."),
        ("Petitgrain EO",         "neat",   580.0,  700.0,  "Petitgrain IS the DHC structural material. More."),
        ("Ethyl Linalool",        "neat",   675.0,  500.0,  "Softness undermines bergamot's classical edge."),
        ("Hedione HC",            "neat",   214.3,  180.0,  "Less is more with high-cis."),
        ("Romandolide",           "neat",   600.0,  500.0,  "Intimacy over projection. This is Dior, not Paco Rabanne."),
        ("Iso E Super",           "neat",   627.7,  480.0,  "Molecular cocoon should whisper, not cocoon."),
        # Ambrofix, EB, Ambrettolide, Norlimbanol, Vetival, Paradisamide unchanged
        ("ADD Alpha Irone",       "30% DEP",  0.0,   1.5,  "Every Demachy formula has an orris whisper. This is mine."),
        ("ADD Cardamom EO",       "neat",    0.0,   5.0,  "The Grasse perfumer's spice lift. Elevates bergamot without changing it."),
    ],
    "II Cedrat": [
        ("Cedrat FCF Sicilian",   "neat",  3240.0, 3000.0, "52% -- even for cedrat, this is showing off."),
        ("Linalyl Acetate",       "neat",   257.1,  200.0,  ""),
        ("Hedione",               "neat",  1547.6, 1300.0,  "Transparency doesn't need amplification."),
        ("Petitgrain EO",         "neat",   580.0,  650.0,  "Cedrat needs more bridge, not less."),
        ("Ethyl Linalool",        "neat",   575.0,  400.0,  "Cedrat is already sharp. Softness is dissonant."),
        ("Hedione HC",            "neat",   214.3,  160.0,  ""),
        ("Romandolide",           "neat",   600.0,  480.0,  "Colder musk for a colder citrus."),
        ("Iso E Super",           "neat",   627.7,  420.0,  "Mineral citrus needs less molecular padding."),
        ("ADD Alpha Irone",       "30% DEP",  0.0,   1.5,  "Orris + mineral = my signature accord."),
        ("ADD Cardamom EO",       "neat",    0.0,   5.0,  "Cold spice for cold citrus."),
    ],
    "III Grapefruit": [
        ("Grapefruit FCF",        "neat",  1944.4, 1800.0, "Grapefruit already punches hardest. Less is more here."),
        ("Linalyl Acetate",       "neat",   571.4,  450.0,  "Grapefruit has its own freshness. Stop helping it."),
        ("Hedione",               "neat",  1666.7, 1400.0,  ""),
        ("Petitgrain EO",         "neat",   580.0,  620.0,  ""),
        ("Ethyl Linalool",        "neat",   775.0,  600.0,  ""),
        ("Hedione HC",            "neat",   214.3,  170.0,  ""),
        ("Romandolide",           "neat",   600.0,  500.0,  "Grapefruit's cheerfulness needs restraint in the base."),
        ("Iso E Super",           "neat",   627.7,  500.0,  ""),
        ("ADD Alpha Irone",       "30% DEP",  0.0,   1.5,  "The unexpected — orris in a grapefruit. This is what makes it Dior."),
        ("ADD Cardamom EO",       "neat",    0.0,   5.0,  ""),
    ],
    "IV Lime": [
        ("Lime Distilled EO",     "neat",  3333.3, 3100.0, "Lime is ethereal -- pushing harder loses the ghost."),
        ("Linalyl Acetate",       "neat",   257.1,  180.0,  "Lime doesn't need a citrus amplifier. It needs quiet."),
        ("Hedione",               "neat",  1547.6, 1300.0,  ""),
        ("Petitgrain EO",         "neat",   580.0,  680.0,  "Lime needs the most structural support of all five."),
        ("Ethyl Linalool",        "neat",   600.0,  400.0,  ""),
        ("Hedione HC",            "neat",   214.3,  150.0,  ""),
        ("Romandolide",           "neat",   600.0,  450.0,  "Lime's ghost deserves the quietest musk."),
        ("Iso E Super",           "neat",   627.7,  380.0,  "Least cocoon for the most transparent citrus."),
        ("ADD Alpha Irone",       "30% DEP",  0.0,   1.5,  "Orris with lime — odd, beautiful, mine."),
        ("ADD Cardamom EO",       "neat",    0.0,   5.0,  ""),
    ],
    "V Mandarin": [
        ("Red Mandarin EO",       "neat",  3055.6, 2800.0, "51% is too much. Mandarin should seduce, not insist."),
        ("Linalyl Acetate",       "neat",   342.9,  280.0,  ""),
        ("Hedione",               "neat",  1547.6, 1350.0,  ""),
        ("Petitgrain EO",         "neat",   580.0,  600.0,  "Mandarin is already warm. Slightly less bridge needed."),
        ("Ethyl Linalool",        "neat",   575.0,  480.0,  ""),
        ("Hedione HC",            "neat",   214.3,  180.0,  ""),
        ("Romandolide",           "neat",   600.0,  520.0,  "Warmest citrus gets the warmest of the reduced musks."),
        ("Iso E Super",           "neat",   627.7,  500.0,  ""),
        ("ADD Alpha Irone",       "30% DEP",  0.0,   1.5,  "Mandarin + orris = the sunset accord. My favorite combination in the five."),
        ("ADD Cardamom EO",       "neat",    0.0,   5.0,  ""),
    ],
}

# Common materials Demachy leaves unchanged
unchanged = {
    "Paradisamide":   ("10%",   35,   3),
    "Ambrofix":       ("30%", 55.5, 185),
    "Ethylene Brassylate": ("neat", 412.5, 33),
    "Ambrettolide":   ("10%", 12.5, 0.5),
    "Norlimbanol Dextro": ("neat", 45, 1.8),
    "Vetival":        ("neat", 42.5, 85),
}

print("=" * 110)
print("DEMACHY'S RED PEN -- TUNING HIS OWN DHC CREATIONS")
print("=" * 110)

for label, adj in adjustments.items():
    print(f"\n{'-'*110}")
    print(f"  DHC {label}")
    print(f"{'-'*110}")
    print(f"  {'Material':<28} {'Before':>8} {'After':>8} {'Delta':>8} {'Effect':<10} {'Reason'}")
    print(f"  {'-'*105}")

    total_before = 0
    total_after = 0

    for name, dil, before, after, reason in adj:
        vp, odt_a, _ = mat(name)
        oav_b = h_oav(before, vp, odt_a) if before > 0 else 0
        oav_a = h_oav(after, vp, odt_a) if after > 0 else 0

        # Determine effect on headspace OAV
        if oav_b == 0 and oav_a > 0:
            eff = "ADDED"
        elif oav_b > oav_a * 1.05:
            eff = "SOFTENED"
        elif oav_a > oav_b * 1.05:
            eff = "BOOSTED"
        else:
            eff = "same"

        display = name.replace("ADD ", "+ ") if "ADD" in name else name
        arrow = f"{'':>3}" if before == 0 else ""
        print(f"  {display:<28} {oav_b:>8,.0f} {oav_a:>8,.0f} {oav_a-oav_b:>+8,.0f} {eff:<10} {reason[:64] if reason else ''}")

        total_before += oav_b
        total_after += oav_a

    # Add unchanged materials
    for uname, (udil, uactive, utarget) in unchanged.items():
        vp, odt_a, _ = mat(uname)
        oav_u = h_oav(uactive, vp, odt_a)
        total_before += oav_u
        total_after += oav_u

    print(f"\n  Total headspace OAV: {total_before:,.0f} --> {total_after:,.0f}  ({total_after/total_before*100-100:+.0f}%)")
    print(f"  Effect: Demachy pulled back the citrus, reduced Hedione/IES/Romandolide,")
    print(f"  boosted Petitgrain, and added two trace materials (orris + cardamom)")
    print(f"  that only a perfumer would notice. The formula is quieter, more intimate,")
    print(f"  and -- critically -- more *French*.")

print(f"\n{'='*110}")
print("  DEMACHY'S TUNING PHILOSOPHY (as applied to each DHC)")
print(f"{'='*110}")
print(f"""
  1. CITRUS RESTRAINT  -- 40-45% of headspace, not 48-54%. The citrus should charm, not announce.
  2. PETITGRAIN BOOST   -- It IS the structural material. Demachy uses it like an architect uses steel.
  3. HEDIONE REDUCTION  -- Radiance should be felt, not detected. Target 200-240 OAV.
  4. ROMANDOLIDE PULLED -- Intimacy over projection. "This is Dior, not Paco Rabanne."
  5. IES PULLED         -- Molecular cocoon should whisper. Target OAV 220.
  6. AMBROFIX UNTOUCHED -- At OAV 185, it IS the Demachy signature. He wouldn't change a decimal.
  7. ORRIS WHISPER      -- Alpha Irone 30% at 5 uL (1.5 active). Every Demachy formula has one.
  8. CARDAMOM LIFT      -- 5 uL neat. The Grasse perfumer's spice. Elevates citrus without changing it.
  9. LINALYL ACETATE -  -- Freshness is juvenile. Let the citrus EO do its own work.
  10. THE FRENCH RULE   -- If you can name every material, the formula is too loud.
""")
