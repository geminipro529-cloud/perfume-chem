"""VP Data Gap Report — tell another AI what to find."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

materials = sorted([
    "Hedione", "Iso E Super", "Linalyl Acetate", "Linalool", "Romandolide",
    "Ethylene Brassylate", "Ambrettolide", "Javanol", "Dihydrojasmone",
    "Damascenone", "Alpha Damascone", "Geraniol", "Citronellol",
    "Galaxolide", "Habanolide", "Bergamot FCF Sicilian", "Cedrat FCF Sicilian",
    "Grapefruit FCF", "Lime Distilled EO", "Red Mandarin EO",
    "Blood Orange Sicilian", "Lemon FCF oil Sicilian", "Petitgrain EO",
    "Ethyl Linalool", "Aurantiol", "Kephalis", "Paradisamide",
    "Scentenal", "Floralozone", "Norlimbanol Dextro", "Vetival",
    "Vertofix", "Methyl Pamplemousse", "Ambrofix", "Apritone",
    "Mayol", "Hydroxycitronellal", "Nympheal", "Ethyl Maltol",
    "Isobutyl Quinoline", "Suederal", "Costus Olifac", "Benzoin Resinoid",
    "Jasmine FO", "Alpha Irone", "Cardamom EO", "Cashmeran",
    "Amberwood F", "Azarbre", "Timberol", "Polysantol",
    "Triplal", "Calone", "Melonal", "Dynascone",
    "Galbanum Resinoid", "Carrot Seed EO", "Vetiver EO", "Cedarwood EO",
    "Patchouli EO", "Lavender EO", "Clary Sage EO", "Rosemary EO",
    "Coumarin", "Vanillin", "Ethyl Vanillin", "Benzyl Benzoate",
])

# Materials that have TGSC-verified VP values
tgsc_verified = {
    "Vertofix": "0.000084 mmHg @ 25C = 0.0112 Pa",
    "Vetival": "0.049 mmHg @ 25C = 6.53 Pa",
    "Apritone": "0.001 mmHg @ 25C = 0.133 Pa",
    "Aurantiol": "0.004 mmHg @ 20C = 0.533 Pa",
    "Damascenone": "0.020 mmHg @ 20C = 2.67 Pa",
    "Dihydrojasmone": "0.010 mmHg @ 20C = 1.333 Pa",
    "Linalool": "0.091 mmHg @ 25C (est) = 12.13 Pa (laevo form)",
}

with open("_VP_GAP_REPORT.txt", "w") as f:
    w = f.write
    w("VP DATA GAP REPORT — Materials Needing TGSC Verification\n")
    w("=" * 70 + "\n\n")
    
    # Part 1: Materials with known VP (local DB)
    w("1. MATERIALS WITH LOCAL DB VP (NEED TGSC CROSS-CHECK)\n")
    w("-" * 50 + "\n\n")
    
    for m in materials:
        p = get_profile(m)
        if not p or not p.vp:
            continue
        local_vp = p.vp
        status = "TGSC VERIFIED" if m in tgsc_verified else "NEEDS TGSC"
        tgsc_note = f" | TGSC: {tgsc_verified[m]}" if m in tgsc_verified else ""
        w(f"  [{status:15}] {m:<30} DB VP: {local_vp:.4f} Pa{tgsc_note}\n")
    
    w("\n\n")
    
    # Part 2: Materials with NO VP data
    w("2. MATERIALS WITH NO VP DATA (CRITICAL GAP)\n")
    w("-" * 50 + "\n\n")
    no_vp = [m for m in materials if not get_profile(m) or not get_profile(m).vp]
    if no_vp:
        for m in no_vp:
            w(f"  [NO VP] {m}\n")
    else:
        w("  (none — all materials have VP data)\n")
    
    w("\n\n")
    
    # Part 3: Missing ODT data
    w("3. MATERIALS WITH MISSING/DUBIOUS ODT\n")
    w("-" * 50 + "\n\n")
    for m in materials:
        n = normalize_name(m)
        od = ODT_DATA.get(n, {})
        odt = od.get('odt_air')
        if odt is None:
            w(f"  [NO ODT] {m}\n")
    
    w("\n\n")
    
    # Part 4: TGSC URL guide for another AI
    w("4. HOW ANOTHER AI CAN FIND TGSC DATA\n")
    w("-" * 50 + "\n")
    w("""
The Good Scents Company (thegoodscentscompany.com) has VP data for most
materials in the Physical Properties section labeled "Vapor Pressure."
Values are in mmHg at a specified temperature.

To collect TGSC VP data:
1. Search TGSC: https://www.thegoodscentscompany.com/search.html
2. Enter CAS number or material name in the "Name, CAS, EINECS, FEMA, FLAVIS" field
3. Click Search (uses POST)
4. Find "Vapor Pressure:" in the Physical Properties section
5. Convert: 1 mmHg = 133.322 Pa
6. If no mmHg value, look for "logP (o/w)" or "Boiling Point" for estimation

ALTERNATIVE: Try direct URL patterns:
  https://www.thegoodscentscompany.com/data/rwXXXXXX.html
  where XXXXXX is a sequential numeric ID (try searching to find the ID)

KEY CAS NUMBERS FOR THE 30 MOST IMPORTANT MATERIALS:
""")
    
    cas_list = {
        "Hedione": "24851-98-7",
        "Iso E Super": "54464-57-2",
        "Linalyl Acetate": "115-95-7",
        "Linalool": "78-70-6",
        "Romandolide": "236391-76-7",
        "Ethylene Brassylate": "105-95-3",
        "Ambrettolide": "28645-51-4",
        "Javanol": "198404-98-7",
        "Damascenone": "23696-85-7",
        "Alpha Damascone": "43052-87-5",
        "Geraniol": "106-24-1",
        "Citronellol": "106-22-9",
        "Galaxolide": "1222-05-5",
        "Bergamot FCF Sicilian": "8007-75-8",
        "Cedrat FCF Sicilian": "8008-56-8",
        "Grapefruit FCF": "8016-20-4",
        "Lime Distilled EO": "8008-26-2",
        "Red Mandarin EO": "8008-31-9",
        "Blood Orange Sicilian": "8028-48-6",
        "Lemon FCF oil Sicilian": "8008-56-8",
        "Petitgrain EO": "8014-17-3",
        "Ethyl Linalool": "10339-55-6",
        "Kephalis": "36306-87-3",
        "Norlimbanol Dextro": "70788-30-6",
        "Ambrofix": "6790-58-5",
        "Calone": "28940-11-6",
        "Triplal": "68039-49-6",
        "Coumarin": "91-64-5",
        "Vanillin": "121-33-5",
        "Ethyl Vanillin": "121-32-4",
    }
    for name, cas in sorted(cas_list.items(), key=lambda x: x[0]):
        status = "VERIFIED" if name in tgsc_verified else "NEEDS"
        w(f"  [{status}] {name:<30} CAS: {cas}\n")

    w("\n\n")
    w("5. SUMMARY\n")
    w("-" * 50 + "\n")
    total = len(materials)
    verified = sum(1 for m in materials if m in tgsc_verified)
    needs = total - verified
    w(f"  Total materials tracked: {total}\n")
    w(f"  TGSC-verified VP:        {verified}\n")
    w(f"  Needs another AI:        {needs}\n")

print("Written _VP_GAP_REPORT.txt")
