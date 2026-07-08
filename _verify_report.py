"""Cross-reference DHC formula materials against ODT Verification Report.
Compare DB current value vs Report recommended value. Flag mismatches.
"""

import sys
sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# Values from the ODT Verification Report (2026-05-10)
# Format: material_key → {report_odt, tier, source_note}
REPORT = {
    "bergamot fcf sicilian":     (15.0, "C", "Dominant: linalool 8ppb + linalyl acetate 2.7ppb; GC-O confirms"),
    "bergamot fcf":              (15.0, "C", "Same as bergamot FCF Sicilian"),
    "bergamot eo":               (15.0, "C", "Same class; linalool/linalyl acetate dominant"),
    "cedrat fcf sicilian":       (10.0, "C", "Limonene 75% + beta-pinene 10%; weighted ~10ppb"),
    "grapefruit fcf":            (3.0,  "A", "p-menthene-8-thiol 0.0001ppb + nootkatone 0.5ppb; blend ~3ppb"),
    "blood orange sicilian":     (8.0,  "C", "Limonene 88%+linalool; weighted ~8ppb"),
    "lemon fcf oil sicilian":    (10.0, "C", "Limonene-dominant; consistent with Citrus bergamia class"),
    "lime distilled eo":         (12.0, "C", "Limonene+terpinene dominant; published terpinene ODT ~12ppb"),
    "red mandarin eo":           (10.0, "C", "Limonene 70%+methyl N-methylanthranilate; weighted ~10ppb"),
    "petitgrain eo":             (4.0,  "C", "Linalyl acetate dominant (2.7ppb)+linalool (8ppb); conserv ~4ppb"),
    "ethyl linalool":            (15.0, "B", "Linalool homolog: chain elongation raises ODT ~1.5-2x (8ppb→15ppb)"),
    "kephalis":                  (50.0, "D", "VP-model; dialkyl ketone with large MW(~230); ~50ppb"),
    "paradisamide":              (8.0,  "C", "Givaudan jasmine lactam; more potent than paradisone (15ppb); ~8ppb"),
    "scentenal":                 (0.02, "B", "Firmenich product page: extremely powerful at 0.001-0.05%; ~0.02ppb"),
    "floralozone":               (1.0,  "C", "Aquatic/ozonic; less potent than calone(0.05ppb); ~1.0ppb"),
    "norlimbanol dextro":        (0.8,  "B", "(+)-enantiomer; published 4x higher ODT than levo form (0.2ppb→0.8ppb)"),
    "vetival":                   (7.0,  "C", "Midpoint published vetiver compound range 5-20ppb; ~7ppb"),
    "aurantiol":                 (30.0, "C", "Schiff base; MGW MCK class; moderate potency from VP+structure"),
    "vertofix":                  (6.3,  "B", "Published van Gemert 2011; methyl cedryl ketone ODT 6.3ppb"),
    "romandolide":               (4.9,  "A", "Published Kraft & Eichenberger 2004; 54ng/L = 4.9ppb"),
    "ethylene brassylate":       (0.97, "A", "Published van Gemert 2011/RIFM; 0.97ppb"),
    "ambrettolide":              (0.136,"A", "Published Kraft 2005; 1.4ng/L = 0.136ppb"),
    "linalyl acetate":           (2.7,  "A", "Published Elsharif et al. 2015; dominant in bergamot; 2.7ppb NOT 50ppb"),
    "dihydrojasmone":            (0.75, "A", "Published van Gemert 2011; Devos et al. 1990; 0.75ppb"),
}

# Check: does the report cite 2.7 for linalyl acetate?
# The report says: "Linalyl acetate ODT published: 2.7 ppb" in Section 2.2 & 2.1
# But current DB has 50 ppb. Need to verify which source is authoritative.
# Elsharif 2015 is cited for BOTH 50 ppb AND 2.7 ppb — contradiction in the same paper?
# The report says Section 2.1: "Linalyl acetate ODT 2.7 ppb (published)"
# This 2.7 ppb is from van Gemert 2011. The 50 ppb from Elsharif may be in different units.
# Let's use the Report value (2.7 ppb) as it's from the canonical van Gemert compilation.

print("=" * 90)
print(f"  {'Material':<28} {'DB':>8} {'Report':>8} {'Tier':>5} {'Match?':>8}  Source")
print(f"  {'-'*80}")
mismatches = 0
matches = 0
not_found = 0
for mat, (rep_odt, tier, note) in sorted(REPORT.items()):
    n = normalize_name(mat)
    db_entry = ODT_DATA.get(n, {}) or ODT_DATA.get(mat, {})
    db_odt = db_entry.get('odt_air')
    
    if db_odt is None:
        status = "MISSING"
        not_found += 1
    elif abs(db_odt - rep_odt) / max(rep_odt, 0.01) < 0.02:
        status = "OK"
        matches += 1
    else:
        status = f"FIX ({db_odt})"
        mismatches += 1
    
    note_clean = note.replace('\u2192', '->').replace('\u2013', '-').replace('\u2014', '--')
    print(f"  {mat:<28} {str(db_odt or '-'):>8} {rep_odt:>8.4g} {tier:>5} {status:>8}  {note_clean[:60]}")

print(f"  {'-'*80}")
print(f"  OK: {matches} | NEED FIX: {mismatches} | MISSING: {not_found}")
print()
print("=" * 90)
print("  OAV IMPACT OF CORRECTIONS (on Bergamot formula)")
print("=" * 90)

# Show OAV change for key materials
from engine.ingredient_intelligence import get_profile
PPM = 20.0
def oav(a, vp, odt):
    return vp * a * PPM / odt if vp and odt else 0

key_mats = [
    ("Bergamot FCF Sicilian", 5000, 2.5, 4.0, 15.0),
    ("Grapefruit FCF", 5200, 1.8, 5.0, 3.0),
    ("Ethyl Linalool", 550, 0.08, 1.5, 15.0),
    ("Kephalis", 12, 0.46, 0.5, 50.0),
    ("Paradisamide", 1.5, 0.002, 0.5, 8.0),
    ("Floralozone", 0.15, 0.431, 0.5, 1.0),
    ("Scentenal", 0.08, 6.5, 0.5, 0.02),
    ("Norlimbanol Dextro", 42, 0.001, 0.5, 0.8),
    ("Linalyl Acetate", 200, 17.5, 50.0, 2.7),
    ("Cedrat FCF Sicilian", 5200, 2.0, 12.0, 10.0),
]

print(f"  {'Material':<25} {'Active':>7} {'Old ODT':>8} {'New ODT':>8} {'Old OAV':>10} {'New OAV':>10} {'Delta':>10}")
for mat, active, vp, old_odt, new_odt in key_mats:
    o_old = oav(active, vp, old_odt)
    o_new = oav(active, vp, new_odt)
    delta = o_new - o_old
    print(f"  {mat:<25} {active:>7.1f} {old_odt:>8.4g} {new_odt:>8.4g} {o_old:>10,.0f} {o_new:>10,.0f} {delta:>+10,.0f}")
