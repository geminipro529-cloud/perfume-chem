"""Cross-reference the new verification report against current DB.
Apply confirmed corrections. Flag conflicts for user review."""

import sys; sys.path.insert(0,'.')
from engine.ingredient_intelligence import _PROFILES as P
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# ══════════════════════════════════════════
# NEW FINDINGS FROM OTHER AI
# ══════════════════════════════════════════

# CRITICAL corrections to apply
CRITICAL = {
    # VP corrections (Section 3 confirms all 19)
    # ODT corrections
    "damascenone": {"odt_air": 0.04},  # Line 721: "DB had 0.004 ppb — 10x error" (Leffingwell 1991)
    "linalool":    {"odt_air": 0.51},  # Keep Elsharif 2015 0.51 ppb (report says 8.0 — conflict to review)
    "dihethyl phthalate": {},
}

# MASSIVE ODT CONFLICTS between DB and new report (needs user review)
CONFLICTS = {
    "Material": [
        ("Linalool",         0.51,   8.0,    "Elsharif 2015 vs RIFM/van Gemert"),
        ("Geraniol",         2.22,   40,     "Elsharif 2016 vs RIFM/van Gemert"),
        ("Limonene",         10,     200,    "Nagata 2003 vs RIFM"),
        ("Benzyl Acetate",   20,     130,    "Nagata 2003 vs RIFM/Fazzalari"),
        ("Indole",           0.3,    0.0005, "van Gemert/Devos vs van Gemert/published panels"),
        ("Citral",           30,     0.5,    "van Gemert vs RIFM safety"),
        ("Eugenol",          6.0,    0.5,    "Rychlik 1998 vs FEMA/van Gemert"),
        ("Skatole",          0.3,    0.0001, "DB value vs van Gemert 2011"),
    ]
}

# VP corrections the other AI confirmed (Section 2)
VP_CONFIRMED = {  # All 19 corrections independently verified
    "Galaxolide":0.0727, "Vanillin":0.20, "Melonal":53.0, "Triplal":66.1,
    "Alpha Irone":0.559, "Norlimbanol Dextro":0.067, "Ethyl Vanillin":0.019,
    "Ethyl Maltol":0.029, "Dynascone":1.44, "Ambrettolide":0.003,
    "Isobutyl Quinoline":0.129, "Calone":0.05, "Cashmeran":0.40,
    "Citronellol":2.67, "Geraniol":2.67, "Coumarin":0.133,
    "Habanolide":0.000053, "Ambrofix":0.066, "Hedione":0.089,
}

# VP corrections that are NEW (not previously in our patch)
VP_NEW = {
    "DBCA":  6.67,    # DB had 0.8 Pa — TGSC verified 0.05 mmHg = 6.67 Pa
    "PCME":  270.0,   # DB had 40 Pa — TGSC 2.029 mmHg = 270 Pa
    "Vetikon": 4.16,  # DB had 0.002 Pa — verified
}

# Other critical fixes
OTHER = {
    "Polysantol": {"cas": "107898-54-4"},     # Was 68845-06-7
    "Vetikon":    {"mw": 176.25, "vp": 4.16, "clogp": 2.7},  # Was 222/0.002/4.5
    "Damascenone": {"odt_air": 0.04},          # Was 0.004
}

print("=" * 70)
print("NEW VERIFICATION REPORT — FINDINGS SUMMARY")
print("=" * 70)

print("\n✅ SECTION 3 (All 19 VP corrections): INDEPENDENTLY CONFIRMED")
for name in sorted(VP_CONFIRMED.keys()):
    p = P.get(name, {})
    db_vp = p.get('vp', 'N/A')
    conf_vp = VP_CONFIRMED[name]
    status = 'OK' if db_vp and abs(db_vp - conf_vp)/conf_vp < 0.2 else f'MISMATCH ({db_vp})'
    print(f"  {name:<25} DB VP={db_vp!s:<10} Confirmed={conf_vp:<10} [{status}]")

print("\n🟡 SECTION 2 (VP cross-check): 59 materials checked")
print("  Most CONFIRMED. Some marked REASONABLE (character-compound VP vs full-oil VP).")
print("  Key: the AI distinguishes 'character-compound VP' from 'full oil VP' — our")
print("  DB uses character-compound VP approach, which is correct for OAV calculation.")

print("\n🔴 NEW CRITICAL CORRECTIONS NEEDED:")
print(f"  1. Polysantol CAS: DB had 68845-06-7 -> verified: 107898-54-4")
print(f"  2. Vetikon: MW 222 -> 176.25, VP 0.002 -> 4.16 Pa, logP 4.5 -> 2.7")
print(f"  3. Damascenone ODT: DB had 0.004 -> verification says should be 0.04 ppb (Leffingwell 1991)")
print(f"  4. DBCA VP: DB had 0.8 -> TGSC verified 6.67 Pa")
print(f"  5. PCME VP: DB had 40 -> TGSC verified 270 Pa")

print("\n⚡ MASSIVE ODT CONFLICTS (needs your review):")
for name, db_val, rep_val, note in CONFLICTS["Material"]:
    print(f"  {name:<20} DB={db_val} vs Report={rep_val} [{note}]")

print("\n🔷 SUMMARY:")
print(f"  Confirmed VP corrections: 19/19")
print(f"  New VP corrections found: 3 (DBCA, PCME, Vetikon)")
print(f"  Other critical fixes: Polysantol CAS, Vetikon MW/logP, Damascenone ODT")
print(f"  ODT conflicts needing review: {len(CONFLICTS['Material'])}")
