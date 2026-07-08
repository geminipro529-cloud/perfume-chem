"""Full gap analysis — every material checked against ALL system-required fields.
Per system instructions: cas, mw, formula, vp_pa, logp, odt_ppb, ifra_category, 
ifra_limit_pct, note_tier, sar_class, functional_role, _source fields."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import _PROFILES as profiles
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

REQUIRED = [
    ("cas", "CAS number"),
    ("mw", "Molecular weight"),
    ("formula", "Chemical formula"),
    ("vp", "VP at 25C (Pa)"),
    ("clogp", "cLogP"),
    ("odt_air", "ODT in air (ppb)"),
    ("odt_source", "ODT source citation"),
    ("note", "Note tier"),
    ("role", "Functional role"),
    ("character", "Character tags"),
    ("texture", "Texture"),
    ("synergies", "Pairing/synergy materials"),
]

# Common names for lookup
ODT_NAMES = set(ODT_DATA.keys())

gaps = {}
profile_names = set()

for name, profile in profiles.items():
    profile_names.add(name)
    n = normalize_name(name)
    row_gaps = []
    
    for field, desc in REQUIRED:
        val = profile.get(field)
        if val is None or val == '' or val == 0:
            # Special case: odt is in ODT_DATA dict, not profile
            if field == 'odt_air':
                odt_entry = ODT_DATA.get(n, {}) or ODT_DATA.get(name, {})
                if odt_entry.get('odt_air'):
                    continue
            if field == 'odt_source':
                odt_entry = ODT_DATA.get(n, {}) or ODT_DATA.get(name, {})
                if odt_entry.get('odt_source') or odt_entry.get('vfy'):
                    continue
            row_gaps.append(field)
        elif field == 'vp' and profile.get('vp_flag') is None and profile.get('vp') is not None:
            # VP needs a source flag
            row_gaps.append('vp_source')
    
    # Check IFRA fields
    if profile.get('ifra_category') is None:
        row_gaps.append('ifra_category')
    if profile.get('ifra_limit') is None and profile.get('ifra_limit_pct') is None:
        row_gaps.append('ifra_limit')
    
    # Check note tier consistency
    vp = profile.get('vp')
    note = profile.get('note')
    if vp is not None and note is not None:
        expected_note = 'top' if vp > 50 else 'heart' if vp >= 0.5 else 'base'
        if note != expected_note:
            row_gaps.append(f'note_tier_mismatch({note}->{expected_note})')
    elif vp is not None and note is None:
        row_gaps.append('note_tier_unset')
    
    if row_gaps:
        gaps[name] = row_gaps

# Check ODT_DATA entries without matching profiles
for odt_name in ODT_NAMES:
    if odt_name not in profiles and odt_name not in profile_names:
        # Check if it maps to a profile via normalize
        matched = False
        for pn in profiles:
            if normalize_name(pn) == odt_name:
                matched = True
                break
        if not matched:
            gap_file = f"odt_only_no_profile_{odt_name}"

with open("_ALL_GAPS.txt", "w") as f:
    w = f.write
    
    w("COMPLETE GAP ANALYSIS — All Materials × All Required Fields\n")
    w("=" * 90 + "\n")
    w("Per system instructions Section 3 & Section 4 requirements\n\n")
    w(f"{'Material':<35} {'Missing Fields'}\n")
    w("-" * 90 + "\n")
    
    # Group by severity
    critical = []   # missing MW, VP, ODT
    major = []      # missing cLogP, CAS, formula
    minor = []      # missing role, texture, synergies, source flags
    
    for name in sorted(gaps.keys(), key=lambda n: len(gaps[n]), reverse=True):
        fields = gaps[name]
        has_critical = any(f in ('vp','odt_air','mw','formula') for f in fields)
        has_major = any(f in ('clogp','cas','ifra_category') for f in fields)
        missing_str = ", ".join(fields)
        
        if has_critical:
            critical.append((name, missing_str))
        elif has_major:
            major.append((name, missing_str))
        else:
            minor.append((name, missing_str))
    
CRITICAL = "[CRIT]"
MAJOR = "[MAJ]"
MINOR = "[MIN]"

for name, missing in critical:
    w(f"{CRITICAL} {name:<33} {missing}\n")
for name, missing in major:
    w(f"{MAJOR}   {name:<33} {missing}\n")
for name, missing in minor:
    w(f"        {name:<33} {missing}\n")
    
    w("\n" + "=" * 90 + "\n")
    w("SUMMARY\n")
    w("-" * 90 + "\n")
    w(f"Total materials checked: {len(profiles)}\n")
    w(f"Materials with gaps:     {len(gaps)}\n")
    w(f"  🔴 Critical (MW/VP/ODT): {len(critical)}\n")
    w(f"  🟡 Major (logP/CAS/IFRA): {len(major)}\n")
    w(f"  Minor (role/texture):     {len(minor)}\n")
    
    w("\nField-by-field coverage:\n")
    for field, desc in REQUIRED:
        ok = 0
        for name in profiles:
            n = normalize_name(name)
            if field == 'odt_air':
                odt = ODT_DATA.get(n, {})
                if odt.get('odt_air'): ok += 1
            else:
                if profiles[name].get(field) and profiles[name].get(field) != 0 and profiles[name].get(field) != '':
                    ok += 1
        pct = ok / len(profiles) * 100
        w(f"  {desc:<25} {ok:>3}/{len(profiles)} ({pct:>5.1f}%)\n")
    
    w("\n\nMOST CRITICAL — Materials needing VP + ODT:\n")
    for name, missing in critical:
        prof = profiles.get(name, {})
        vp = prof.get('vp', 'MISSING')
        odt_entry = ODT_DATA.get(normalize_name(name), {})
        odt = odt_entry.get('odt_air', 'MISSING')
        cas = prof.get('cas', 'MISSING')
        mw = prof.get('mw', 'MISSING')
        w(f"  {name:<30} VP={vp!s:<12} ODT={odt!s:<12} CAS={cas!s:<12} MW={mw!s:<12}\n")

print(f"Written _ALL_GAPS.txt")
print(f"Total: {len(profiles)} profiles | {len(gaps)} with gaps | {len(critical)} critical")
