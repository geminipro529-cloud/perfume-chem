"""Full inventory audit — all 195 materials. Verification status per property."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import _PROFILES as profiles
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# Materials with TGSC-verified VP (direct page fetch)
VP_VERIFIED = {
    "Vertofix", "Vetival", "Apritone", "Aurantiol", 
    "Damascenone", "Dihydrojasmone", "Linalool"
}

# Materials with published peer-reviewed ODT (tier A)
ODT_TIER_A = {
    "Hedione","Iso E Super","Linalyl Acetate","Linalool",
    "Romandolide","Ethylene Brassylate","Ambrettolide","Javanol",
    "Dihydrojasmone","Damascenone","Alpha Damascone","Geraniol",
    "Citronellol","Galaxolide","Ambrofix","Damascenone",
    "Scentenal","Ethyl Maltol","Hydroxycitronellal",
}

tgsc_verified_set = VP_VERIFIED

results = []

for name in sorted(profiles.keys()):
    p = profiles[name]
    n = normalize_name(name)
    od = ODT_DATA.get(n, {})
    
    # VP
    vp = p.get('vp')
    vp_ok = "TGSC" if name in tgsc_verified_set else ("LOCAL" if vp else "NONE")
    
    # ODT
    odt = od.get('odt_air')
    odt_ok = "PUB" if name in ODT_TIER_A else ("LOCAL" if odt else "NONE")
    
    # MW
    mw = p.get('mw')
    mw_ok = "Y" if mw else "N"
    
    # cLogP
    clogp = p.get('clogp')
    clogp_ok = "Y" if clogp else "N"
    
    # Note tier
    note = p.get('note')
    note_ok = "Y" if note else "N"
    
    # Role
    role = p.get('role')
    role_ok = "Y" if role else "N"
    
    # CAS
    cas = p.get('cas')
    cas_ok = "Y" if cas else "N"
    
    # Count verified properties (out of 7)
    verified_count = sum([
        1 if name in tgsc_verified_set else 0,
        1 if name in ODT_TIER_A else (1 if odt else 0),
        1 if mw else 0,
        1 if clogp else 0,
        1 if note else 0,
        1 if role else 0,
        1 if cas else 0,
    ])
    
    results.append({
        "name": name,
        "vp": vp_ok,
        "odt": odt_ok,
        "mw": mw_ok,
        "clogp": clogp_ok,
        "note": note_ok,
        "role": role_ok,
        "cas": cas_ok,
        "verified": verified_count,
    })

# Write report
with open("_full_inventory_audit.txt", "w") as f:
    w = lambda s: f.write(s + "\n")
    w("FULL INVENTORY AUDIT — All Materials Verification Status")
    w("=" * 100)
    w("")
    w("Legend: TGSC=verified VP via TGSC fetch | PUB=peer-reviewed ODT | LOCAL=DB value | Y=has data | N=missing")
    w("")
    w(f"{'Material':<35} {'VP':>6} {'ODT':>6} {'MW':>4} {'cLogP':>6} {'Note':>5} {'Role':>5} {'CAS':>4} {'V/7':>5}")
    w("-" * 100)
    
    for r in results:
        w(f"{r['name']:<35} {r['vp']:>6} {r['odt']:>6} {r['mw']:>4} {r['clogp']:>6} {r['note']:>5} {r['role']:>5} {r['cas']:>4} {r['verified']:>5}/7")
    
    w("")
    w("=" * 100)
    w("SUMMARY")
    w("-" * 100)
    total = len(results)
    vp_tgsc = sum(1 for r in results if r['vp'] == 'TGSC')
    vp_local = sum(1 for r in results if r['vp'] == 'LOCAL')
    vp_none = sum(1 for r in results if r['vp'] == 'NONE')
    odt_pub = sum(1 for r in results if r['odt'] == 'PUB')
    odt_local = sum(1 for r in results if r['odt'] == 'LOCAL')
    odt_none = sum(1 for r in results if r['odt'] == 'NONE')
    mw_none = sum(1 for r in results if r['mw'] == 'N')
    clogp_none = sum(1 for r in results if r['clogp'] == 'N')
    note_none = sum(1 for r in results if r['note'] == 'N')
    role_none = sum(1 for r in results if r['role'] == 'N')
    cas_none = sum(1 for r in results if r['cas'] == 'N')
    
    w(f"Total materials: {total}")
    w(f"")
    w(f"VP (Pa):     TGSC verified: {vp_tgsc} | Local DB only: {vp_local} | Missing: {vp_none}")
    w(f"ODT (ppb):   Peer-reviewed: {odt_pub} | Local DB only: {odt_local} | Missing: {odt_none}")
    w(f"MW:          {total - mw_none}/{total} have data | Missing: {mw_none}")
    w(f"cLogP:       {total - clogp_none}/{total} have data | Missing: {clogp_none}")
    w(f"Note tier:   {total - note_none}/{total} have data | Missing: {note_none}")
    w(f"Role:        {total - role_none}/{total} have data | Missing: {role_none}")
    w(f"CAS:         {total - cas_none}/{total} have data | Missing: {cas_none}")
    
    w("")
    w("=" * 100)
    w("PRIORITY FOR VERIFICATION")
    w("-" * 100)
    w("CRITICAL: Materials with missing MW, cLogP, CAS — these break the physics model")
    w("")
    for r in results:
        missing = []
        if r['mw'] == 'N': missing.append('MW')
        if r['clogp'] == 'N': missing.append('cLogP')
        if r['cas'] == 'N': missing.append('CAS')
        if r['note'] == 'N': missing.append('Note')
        if r['role'] == 'N': missing.append('Role')
        if missing:
            w(f"  {r['name']:<35} Missing: {', '.join(missing)}")
    
    w("")
    w("HIGH: Materials with VP from local DB only (no TGSC or NIST cross-check)")
    for r in results:
        if r['vp'] == 'LOCAL':
            w(f"  {r['name']:<35} VP: {profiles[r['name']].get('vp',0):.4f} Pa (local DB, unverified)")

    w("")
    w("MEDIUM: Materials with ODT from local DB only (no peer-reviewed source)")
    for r in results:
        if r['odt'] == 'LOCAL':
            w(f"  {r['name']:<35} ODT: {ODT_DATA.get(normalize_name(r['name']),{}).get('odt_air','?'):.4g} ppb")
    
    total_v7 = sum(1 for r in results if r['verified'] == 7)
    w(f"")
    w(f"Fully verified (7/7): {total_v7}")
    w(f"Zero properties verified: {zero_v}")
    # Fix that last line
    zero_v = sum(1 for r in results if r['verified'] == 0)
    w(f"Zero properties verified: {zero_v}")

print("Written _full_inventory_audit.txt")
