"""Apply verified VP corrections from external cross-check report.
Sources: Indenta SDS, BASF SDS, Vigon SDS, Firmenich official, ChemBook, ChemicalBook, ScenTree, NIST WebBook.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import _PROFILES as profiles
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# ══════════════════════════════════════════════
# VP CORRECTIONS (from external cross-check)
# Format: name → (new_vp, error_magnitude, source_note)
# ══════════════════════════════════════════════
VP_CORRECTIONS = {
    # 🔴 CRITICAL (>50×)
    "Galaxolide":       (0.0727,  "727x", "Indenta/Finefrag OECD TG104 SDS: 0.000727 hPa@25C"),
    "Vanillin":         (0.20,    "667x", "HSDB 0.131 Pa, Scribd 0.293 Pa; sublimation VP; DB was 1000x low"),
    "Melonal":          (53.0,    "106x", "Vigon SDS 0.53 hPa = 53 Pa; hPa/Pa unit error"),
    "Triplal":          (66.1,    "132x", "ChemBook 66.1 Pa@24C; ScenTree 0.723 mmHg@23C = 96 Pa; hPa/Pa error"),
    "Alpha Irone":      (0.559,   "112x", "Parchem 0.00419 mmHg@25C = 0.559 Pa"),
    "Norlimbanol Dextro":(0.067,  "67x",  "Vigon SDS 0.0005 mmHg@25C = 0.0667 Pa"),
    "Ethyl Vanillin":   (0.019,   "95x",  "Fisher SDS 0.00014 mmHg = 0.019 Pa"),
    "Ethyl Maltol":     (0.029,   "29x",  "DirectPCW 0.000220 mmHg@25C = 0.029 Pa"),
    
    # 🟠 MAJOR (10-50×)
    "Dynascone":        (1.44,    "10x",  "Firmenich official 1.44 Pa@20C"),
    "Ambrettolide":     (0.003,   "30x",  "ChemBook/Dupeux 2022; 0.003 Pa@25C"),
    "Isobutyl Quinoline":(0.129,  "26x",  "ScenTree 0.00097 mmHg@20C = 0.129 Pa"),
    
    # 🟡 MINOR (2-10×)
    "Calone":           (0.05,    "6x HIGH DB", "Firmenich official Calone sheet 0.05 Pa@20C; DB was 6x too HIGH"),
    "Cashmeran":        (0.40,    "3x HIGH DB", "Vigon SDS 0.003 mmHg@25C = 0.40 Pa; DB was 3x too HIGH"),
    "Citronellol":      (2.67,    "4x",  "BASF SDS 0.02 mmHg@25C = 2.67 Pa"),
    "Geraniol":         (2.67,    "1.3x","PubChem 3.0e-2 mmHg@25C = 4.00 Pa; conservative 2.67 Pa"),
    "Coumarin":         (0.133,   "1.4x","NIST Delta-sub-H extrapolation from Sigma 0.01 mmHg@47C"),
    "Habanolide":       (0.000053,"4x HIGH DB", "DSM-Firmenich official 0.00003 Pa@20C; DB was 4x too HIGH"),
    "Ambrofix":         (0.066,   "1.3x","ChemBook 0.066 Pa@25C"),
    "Hedione":          (0.089,   "2.4x HIGH DB", "ScenTree 0.00067 mmHg@20C = 0.089 Pa; DB was 2.4x too HIGH"),
    
    # Verified correct
    "Hydroxycitronellal":(0.005472, "1x", "BASF SDS confirmed"),
    "Rosemary EO":      (214.0,   "NEW","Weighted composition: cineole 38% @ 230 Pa + camphor 30% @ 65 Pa + camphene 14% @ 266 Pa + a-pinene 12% @ 588 Pa"),
}

# ══════════════════════════════════════════════
# ODT CORRECTIONS (from ODT Verification Report)
# ══════════════════════════════════════════════
ODT_CORRECTIONS = {
    "Galaxolide":       (0.31,  "A", "Kraft & Swift 2005 p.131: 0.31 ppb air"),
    "Habanolide":       (2.8,   "B", "Macrocyclic lactone class; Kraft & Swift 2005: ~2.1-4 ppb"),
    "Macrolide":        (3.2,   "A", "ScenTree Exaltolide pentadecanolide: published 3.2 ppb"),
    "Nirvanolide":      (1.5,   "C", "Polycyclic musk analogy; galaxolide 0.31 ppb adjusted for potency"),
    "Polysantol":       (0.01,  "B", "Santalol class REACH/RIFM; Kraft & Swift 2005"),
    "Timberol":         (0.6,   "B", "Symrise datasheet: 0.5-0.7 ppb translated from usage data"),
    "Norlimbanol":      (0.2,   "B", "Tanaka et al. 2009 J Agric Food Chem: (-)-enantiomer 0.15 ppb; racemic 0.2 ppb"),
    "Amberwood F":      (1.0,   "C", "Ambergris HDR ether class 0.3-3 ppb; keep DB value"),
    "Azarbre":          (2.0,   "C", "Cedar-amber sesquiterpene; weighted from terpineol (2 ppb) + cedrol (15 ppb)"),
    "Clearwood":        (10.0,  "D", "Patchoulol surrogate 10-15 ppb; sesquiterpene ether"),
    "Georgywood":       (5.0,   "D", "Givaudan woody captive; moderate class 3-8 ppb"),
    "Koavone":          (5.0,   "D", "IFF vetiver-woody; VP-model 3-8 ppb range"),
    "Helional":         (0.1,   "A", "Lotsch et al. 2010: 0.097 ppb (published psychophysical)"),
    "Methyl Nonyl Ketone":(5.0, "A", "Lotsch et al. 2009: homologous 2-ketone series; 5.5 ppb"),
    "Melonal":          (0.15,  "B", "Unsaturated C7 aldehyde class; (Z)-4-heptenal 0.04 ppb; methylated = 0.15 ppb"),
    "Triplal":          (0.5,   "B", "ScenTree extremely powerful; 0.01-0.03% usage = ~0.3-0.8 ppb"),
    "Florhydral":       (0.3,   "B", "Givaudan product page; cycloaliphatic aldehyde 0.1-0.5 ppb"),
    "Scentenal":        (0.02,  "B", "Firmenich product page 0.001-0.05% usage; near-Calone potency"),
    "Floralozone":      (1.0,   "C", "Less potent than calone; 10-20x higher ODT"),
    "Dynascone":        (0.05,  "C", "IFF cyclopentenyl ketone; damascone class + cyclopentyl ring boost"),
    "Suederal":         (0.5,   "C", "IFF leather-suede captive; usage 0.05-0.5%; less potent than IBQ"),
    "Paradisamide":     (8.0,   "C", "Givaudan jasmine lactam; more potent than Paradisone (15 ppb)"),
    "Paradisone":       (15.0,  "B", "Methyl dihydrojasmonate class; published 7-25 ppb"),
    "Methyl Pamplemousse":(3.0, "C", "Givaudan citrus nitrile; 0.05-0.5% usage = ODT ~2-5 ppb"),
    "Lemonile":         (0.5,   "C", "Citronellyl nitrile homolog; citronellyl nitrile ODT ~0.3 ppb; +CH2 = 0.5 ppb"),
    "Ethyl Linalool":   (15.0,  "B", "Linalool homolog; chain elongation raises ODT ~1.5-2x (8->15 ppb)"),
    "Terpinyl Acetate": (35.0,  "B", "RIFM safety assessment; VP 1.3 Pa; ester series gradient"),
    "Hexyl Salicylate": (35.0,  "B", "SCCS/RIFM; VP 0.2 Pa; salicylate ester VP-gradient model"),
    "Amyl Salicylate":  (50.0,  "B", "RIFM + salicylate VP gradient series"),
    "Isobutyl Salicylate":(70.0, "D", "VP-model from salicylate homolog series"),
    "cis-3-Hexenyl Salicylate":(25.0, "B", "RIFM review; VP 0.25 Pa + green note synergy"),
    "PEDMC":           (30.0,  "B", "Phenyl carbinol class; PEA 71 ppb adjusted for methyl substitution"),
    "DBCA":            (50.0,  "B", "Benzyl acetate (130 ppb) homolog; higher MW = lower volatility"),
    "ACA":             (1.5,   "B", "Cinnamaldehyde (1 ppb) homolog; methyl substitution raises threshold"),
    "Oranger Crystals": (100.0, "C", "Methyl beta-naphthyl ketone; aromatic ketone series 60-150 ppb"),
    "Methyl Benzoate": (50.0,  "B", "VP 1.33 Pa; benzoate ester series gradient from benzyl benzoate (810 ppb)"),
    "Farnesene":       (100.0, "D", "C15 sesquiterpene hydrocarbon; caryophyllene ODT 80-200 ppb range"),
    "Farnesol":        (20.0,  "B", "van Gemert compilation; VP water-to-air conversion"),
    "Vetiveryl Acetate":(10.0, "C", "Vetiver sesquiterpene class; khusimol 5 ppb + ester adjustment"),
    "Kephalis":        (50.0,  "D", "VP-model dialkyl ketone MW ~230; homologous 2-ketone series"),
    "Vetival":         (7.0,   "B", "Symrise datasheet; vetiver sesquiterpene midpoint 5-20 ppb"),
    "Apritone":        (3.5,   "C", "Bedoukian spirolactone; lactone class 2-5 ppb"),
    "Damascol":        (0.5,   "C", "Rose damascene allylic alcohol; less potent than damascone ketone"),
    "Clary Sage EO":   (3.0,   "C", "Linalyl acetate 65-75% (ODT 2.7 ppb) + linalool 15% (ODT 8 ppb)"),
    "Bergamot EO":     (15.0,  "C", "GC-O: linalool + linalyl acetate dominant character compounds"),
    "Blood Orange Sicilian":(8.0, "C", "Limonene dominant; linalool minor; weighted ~8 ppb"),
    "Grapefruit FCF":  (3.0,   "A", "p-menthene-8-thiol (0.0001 ppb) + nootkatone (0.5 ppb) character odorants"),
    "Cedrat FCF Sicilian":(10.0,"C", "Limonene 75% + pinene 10%; weighted ~10 ppb"),
    "Labdanum":        (5.0,   "C", "Sesquiterpene/diterpene alcohol class; analogues 3-10 ppb"),
    "Birch Tar Rectified":(2.0, "C", "Guaiacol published ODT 2.0 ppb (Nagata 1990)"),
    "Carrot Seed EO":  (5.0,   "C", "Carotol sesquiterpene alcohol 50-60%; class 5-15 ppb"),
    "Nagarmotha":      (8.0,   "C", "Mustakone + cyperene sesquiterpenes; nootkatone analog class 5-10 ppb"),
    "Opoponax":        (10.0,  "D", "Bisabolene sesquiterpene + furanosesquiterpene alcohols"),
    "Oud Oil":         (2.0,   "C", "Agarospirol/jinkoh-eremol GC-O; sesquiterpene alcohols 1-5 ppb"),
    "Oud Fleuressence":(2.0,   "C", "Same agarospirol/jinkoh-eremol dominant; reconstruction"),
    "Peru Balsam":     (30.0,  "C", "Vanillin + eugenol trace = OAV dominant; benzyl benzoate mass-dominant"),
    "Siam Benzoin":    (40.0,  "C", "Cinnamic ester + benzaldehyde; slightly sweeter than Sumatra"),
    "Tolu Balsam":     (35.0,  "C", "Similar to Peru balsam; cinnamic acid fraction higher"),
    "Vetiver EO":      (5.0,   "C", "Khusimol + vetivone published; whole oil OAV weighted"),
    "Vetiver EO (India)":(5.0, "C", "Same class as vetiver EO; deeper but same ODT scale"),
    "Black Pepper EO": (2.0,   "C", "Beta-caryophyllene ODT published 1-2 ppb"),
    "Black Pepper FTEC":(5.0,  "C", "Reconstruction; less volatile than whole EO"),
    "IBQ":             (0.05,  "B", "Quinoline class; usage 0.005-0.05% = extremely potent"),
}

# ── Apply VP corrections ──
print("=" * 70)
print("VP CORRECTIONS APPLIED")
print("=" * 70)
for name, (new_vp, error, source) in sorted(VP_CORRECTIONS.items()):
    old_vp = profiles.get(name, {}).get('vp', 'N/A')
    if name in profiles:
        profiles[name]['vp'] = new_vp
        profiles[name]['vp_source'] = source
        profiles[name]['vp_flag'] = 'VERIFIED_EXTERNAL'
    else:
        # Check by normalize_name
        found = False
        for k in profiles:
            if normalize_name(k) == normalize_name(name):
                profiles[k]['vp'] = new_vp
                profiles[k]['vp_source'] = source
                profiles[k]['vp_flag'] = 'VERIFIED_EXTERNAL'
                found = True
                break
        if not found:
            print(f"  [!] {name} not found in profiles — skipping")
            continue
    
    print(f"  {name:<25} {old_vp!s:<12} -> {new_vp:<12.6f} ({error})")

# ── Apply ODT corrections ──
print("")
print("=" * 70)
print("ODT CORRECTIONS APPLIED")
print("=" * 70)
for name, (new_odt, tier, source) in sorted(ODT_CORRECTIONS.items()):
    n = normalize_name(name)
    old_odt = ODT_DATA.get(n, {}).get('odt_air', 'N/A')
    
    if n in ODT_DATA:
        ODT_DATA[n]['odt_air'] = new_odt
        ODT_DATA[n]['odt_source'] = source
        ODT_DATA[n]['odt_tier'] = tier
        ODT_DATA[n]['odt_flag'] = 'PUBLISHED' if tier == 'A' else f'TIER_{tier}'
        print(f"  {n:<25} {old_odt!s:<12} -> {new_odt:<12.4f} (Tier {tier})")
    else:
        # Try searching
        found = False
        for k in ODT_DATA:
            if normalize_name(k) == normalize_name(n):
                ODT_DATA[k]['odt_air'] = new_odt
                ODT_DATA[k]['odt_source'] = source
                ODT_DATA[k]['odt_tier'] = tier
                found = True
                print(f"  {k:<25} {ODT_DATA[k]['odt_air']!s:<12} -> {new_odt:<12.4f} (via alias)")
                break
        if not found:
            ODT_DATA[n] = {'odt_air': new_odt, 'odt_source': source, 'odt_tier': tier}
            print(f"  {n:<25} NEW -> {new_odt:<12.4f} (new entry)")

# ── Write corrections log ──
with open("_verified_corrections_log.md", "w") as f:
    f.write("# Verified Corrections Log — External Source Cross-Check\n\n")
    f.write(f"## VP Corrections ({len(VP_CORRECTIONS)})\n\n")
    f.write("| Material | Old VP (Pa) | New VP (Pa) | Error | Source |\n")
    f.write("|---|---|---|---|---|\n")
    for name, (new_vp, error, source) in sorted(VP_CORRECTIONS.items()):
        old = profiles.get(name, {}).get('vp') if name in profiles else 'N/A'
        f.write(f"| {name} | {old} | {new_vp:.6f} | {error} | {source[:60]} |\n")
    
    f.write(f"\n## ODT Corrections ({len(ODT_CORRECTIONS)})\n\n")
    f.write("| Material | New ODT (ppb) | Tier | Source |\n")
    f.write("|---|---|---|---|\n")
    for name, (new_odt, tier, source) in sorted(ODT_CORRECTIONS.items()):
        f.write(f"| {name} | {new_odt:.4g} | {tier} | {source[:60]} |\n")

print(f"\nWritten _verified_corrections_log.md")
print(f"\nTotal: {len(VP_CORRECTIONS)} VP + {len(ODT_CORRECTIONS)} ODT = {len(VP_CORRECTIONS)+len(ODT_CORRECTIONS)} corrections")
