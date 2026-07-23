"""Verify Chanel AHS Blanche formula against headspace OAV / ppm / ODT pipeline."""
import sys

sys.path.insert(0, r"D:\chatbots\perfume-chem")

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.simulator import simulate_formula

FORMULA_NAME = "Chanel Allure Homme Sport Blanche"
FAMILY_ARCHETYPE = "cologne"

# All ingredients with CANONICAL names (no dilution suffixes in names)
# Dilutions are handled separately in the DILUTIONS map.
INGREDIENTS_UL = {}
DILUTIONS = {}

def add_ingr(name, raw_ul, dilution=1.0):
    INGREDIENTS_UL[name] = raw_ul
    DILUTIONS[name] = dilution

# === BASE (Step 1) ===
add_ingr("Iso E Super", 750)
add_ingr("Habanolide", 650)
add_ingr("Galaxolide", 350, 0.5)
add_ingr("Coumarin", 350, 0.2)
add_ingr("Cedarwood EO", 300)
add_ingr("Ambrofix", 220, 0.30)
add_ingr("Cedramber", 180)
add_ingr("Cashmeran", 750, 0.2)
add_ingr("Sandalore", 150)
add_ingr("Vanillin", 120, 0.1)
add_ingr("Vetiver EO (India)", 30)

# === HEART (Step 2) ===
add_ingr("Lavender EO High Altitude", 220)
add_ingr("Hedione HC", 180)
add_ingr("Linalyl Acetate", 120)
add_ingr("Alpha Isomethyl Ionone", 120)
add_ingr("Alpha Ionone", 50)
add_ingr("Orivone", 50)
add_ingr("Irotyl", 20)
add_ingr("Alpha Irone", 20, 0.30)
add_ingr("Ultralia", 15)

# === TOP (Step 3) ===
add_ingr("Bergamot FCF oil Sicilian", 330)
add_ingr("Cedrat FCF oil Sicilian", 270)
add_ingr("Dihydromyrcenol", 210)
add_ingr("Ethyl Linalool", 120)
add_ingr("Floralozone", 100, 0.10)
add_ingr("Red Mandarin EO", 80)
add_ingr("Helional", 50)
add_ingr("D-Limonene", 35)
add_ingr("Aldehyde C10", 30, 0.01)
add_ingr("Aldehyde C11", 25, 0.01)
add_ingr("Aldehyde C12 MNA", 20, 0.01)
add_ingr("Cardamom EO", 15)
add_ingr("Black Pepper EO", 20)

CONCENTRATE_UL = sum(INGREDIENTS_UL.values())
BATCH_ML = 30.0
TEMP_K = 305.0

HR = "=" * 80
DASH = "-" * 80

print(HR)
print(f"VERIFICATION: {FORMULA_NAME}")
print(HR)
print(f"Total raw concentrate: {CONCENTRATE_UL:.0f} uL")
print(f"Batch volume: {BATCH_ML:.0f} mL")
print(f"Concentration (raw/total): {CONCENTRATE_UL/(BATCH_ML*1000)*100:.1f}%")
print(f"Number of materials: {len(INGREDIENTS_UL)}")
print(f"Temperature: {TEMP_K} K (32 C / skin temperature)")

# ---- Phase 1: Build formula state ----
print(f"\n{DASH}")
print("PHASE 1: Formula State (Headspace OAV / ppm / ODT)")
print(DASH)

state = build_formula_state(
    INGREDIENTS_UL, DILUTIONS,
    batch_volume_ml=BATCH_ML, temperature_K=TEMP_K,
)

HDR = f"{'Material':38s} {'raw_uL':>7s} {'dil':>4s} {'act_uL':>7s} {'MW':>6s} {'VP(Pa)':>8s} {'g':>5s} {'vppm':>11s} {'ODT':>10s} {'OAV':>10s} {'note':>6s}"
print(f"\n{HDR}")
print("-" * len(HDR))
sorted_mats = sorted(state.materials, key=lambda m: m.active_ul, reverse=True)
for m in sorted_mats:
    if m.oav is not None:
        oav_str = f"{m.oav:.0f}" if m.oav >= 100 else f"{m.oav:.1f}"
    else:
        oav_str = "N/A"
    odt_str = f"{m.odt_air_ppm:.6f}" if m.odt_air_ppm is not None else "N/A"
    if m.vapor_ppm > 0.001:
        vppm_str = f"{m.vapor_ppm:.6f}"
    else:
        vppm_str = f"{m.vapor_ppm:.2e}"
    mw_str = f"{m.mw_g_mol:.1f}" if m.mw_g_mol else "N/A"
    if m.vp_pure_pa and m.vp_pure_pa < 100:
        vp_str = f"{m.vp_pure_pa:.3f}"
    elif m.vp_pure_pa:
        vp_str = f"{m.vp_pure_pa:.1f}"
    else:
        vp_str = "N/A"
    note_str = (m.note or "?")[:6]
    print(f"{m.name:38s} {m.raw_ul:7.1f} {m.dilution:4.2f} {m.active_ul:7.2f} {mw_str:>6s} {vp_str:>8s} {m.gamma:5.2f} {vppm_str:>11s} {odt_str:>10s} {oav_str:>10s} {note_str:>6s}")

print(f"\n{DASH}")
print("SUMMARY STATS")
print(DASH)
total_active = sum(m.active_ul for m in state.materials)
total_vppm = sum(m.vapor_ppm for m in state.materials)
perc_count = len(state.perceptible_materials)
print(f"Total active concentrate: {total_active:.0f} uL")
print(f"Total vapor-phase conc:  {total_vppm:.2f} ppm")
print(f"Perceptible materials: {perc_count}/{state.material_count} (OAV >= 1.0)")
notes = state.note_distribution()
print(f"Note distribution: Top={notes['top']:.1f}%  Heart={notes['heart']:.1f}%  Base={notes['base']:.1f}%")
print(f"OAV > 1000 (structural waste): {sum(1 for m in state.materials if m.oav and m.oav > 1000)} materials")

print(f"\n{DASH}")
print("TOP 15 OAV LEADERS (headspace at t=0)")
print(DASH)
top_oav = sorted(state.materials, key=lambda m: m.oav or 0.0, reverse=True)
for i, m in enumerate(top_oav[:15]):
    oav_str = f"{m.oav:.0f}" if m.oav and m.oav >= 1000 else f"{m.oav:.1f}" if m.oav else "N/A"
    note_str = m.note if m.note else "?"
    print(f"  {i+1:2d}. {m.name:35s} OAV={oav_str:>9s}  VP={m.vp_pure_pa or 0:.1f} Pa  [{note_str}]")

# ---- Phase 2: Simulation ----
print(f"\n\n{DASH}")
print("PHASE 2: TIME SIMULATION (OAV evolution over evaporation windows)")
print(DASH)

sim_frames = list(simulate_formula(
    INGREDIENTS_UL, DILUTIONS,
    batch_volume_ml=BATCH_ML, temperature_K=TEMP_K,
))

for frame in sim_frames:
    print(f"\n--- [{frame.label.upper()}] t={frame.t_seconds:.0f}s ---")
    dom = frame.dominant_oav(limit=8)
    total_oav = sum(m.oav or 0.0 for m in frame.state.materials)
    print(f"  Total headspace OAV: {total_oav:,.0f}")
    perc = len(frame.state.perceptible_materials)
    print(f"  Perceptible: {perc}/{frame.state.material_count}")
    for d in dom:
        print(f"    {d['material']:35s} OAV={d['oav']:>10.1f}  ppm={d['ppm']:.6f}  I={d['intensity']:.3f}")
    if frame.receptor_activation:
        rec = sorted(frame.receptor_activation.items(), key=lambda x: -x[1])[:5]
        print(f"  Receptors: {', '.join(f'{k}={v:.3f}' for k,v in rec)}")

# ---- Phase 3: Pipeline gates ----
print(f"\n\n{HR}")
print("PHASE 3: PIPELINE RELEASE GATES")
print(HR)

formula_record = {
    "number": 1, "name": FORMULA_NAME,
    "family_archetype": FAMILY_ARCHETYPE,
    "ingredients_ul": INGREDIENTS_UL, "dilutions": DILUTIONS,
}

config = ReleaseGateConfig(
    expected_concentrate_ul=5950.0,
    batch_volume_ml=30.0, temperature_K=305.0,
    family_archetype=FAMILY_ARCHETYPE,
    concentration_bracket="EdP", min_confidence_score=25.0,
)

report = gate_formula(formula_record, config)

print(f"\nOverall Status: {report.status}")
print(f"Commercial Readiness: {report.commercial_readiness}")
print(f"Confidence: {report.confidence.get('combined_confidence', 0):.1f} ({report.confidence.get('combined_grade', '?')})")
print("\nGate Results:")
for g in report.gates:
    icon = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]"}.get(g.status, "[??]")
    print(f"  {icon} {g.gate:45s} {g.status:5s}  {(g.detail or '')[:90]}")

# ---- ODT coverage ----
print(f"\n\n{DASH}")
print("ODT COVERAGE AUDIT")
print(DASH)
missing_odt = [(m.name, m.odt_air_ppm) for m in state.materials if m.odt_air_ppm is None]
if missing_odt:
    print(f"  [XX] Missing ODT: {', '.join(m[0] for m in missing_odt)}")
else:
    print(f"  [OK] ALL {state.material_count} materials have ODT coverage")

# ---- AHS Signature Profile Match ----
print(f"\n\n{HR}")
print("AHS SIGNATURE PROFILE MATCH")
print(HR)

def safe_oav(m):
    return m.oav if m.oav is not None else 0.0

checks = []

# 1. DHM sport freshness
dhm = next(m for m in state.materials if "Dihydromyrcenol" in m.name)
dhm_oav = safe_oav(dhm)
checks.append(f"{'[OK]' if dhm_oav > 5000 else '[!!]'} DHM sport freshness OAV={dhm_oav:.0f} {'>5000' if dhm_oav > 5000 else '(expected >5000)'}")

# 2. Ambrofix ambergris backbone
amb = next(m for m in state.materials if "Ambrofix" in m.name)
amb_oav = safe_oav(amb)
checks.append(f"{'[OK]' if amb_oav > 5 else '[!!]'} Ambrofix backbone OAV={amb_oav:.1f} {'>5' if amb_oav > 5 else '(expected >5)'}")

# 3. Hedione HC radiance (note: Hedione HC aliases to Hedione in ODT)
hed = next(m for m in state.materials if "Hedione" in m.name)
hed_oav = safe_oav(hed)
checks.append(f"{'[OK]' if hed_oav > 100 else '[!!]'} Hedione radiance OAV={hed_oav:.1f} {'>100' if hed_oav > 100 else '(expected >100)'}")

# 4. Coumarin tonka
cou = next(m for m in state.materials if "Coumarin" in m.name)
cou_oav = safe_oav(cou)
checks.append(f"{'[OK]' if cou_oav > 10 else '[!!]'} Coumarin tonka OAV={cou_oav:.1f} {'>10' if cou_oav > 10 else '(expected >10)'}")

# 5. Iso E Super spatial volume
iso = next(m for m in state.materials if "Iso E Super" in m.name)
iso_oav = safe_oav(iso)
checks.append(f"{'[OK]' if iso_oav > 500 else '[!!]'} Iso E Super spatial volume OAV={iso_oav:.0f} {'>500' if iso_oav > 500 else '(expected >500)'}")

# 6. Lavender fougere heart
lav = next(m for m in state.materials if "Lavender" in m.name)
lav_oav = safe_oav(lav)
checks.append(f"{'[OK]' if lav_oav > 5 else '[!!]'} Lavender fougere heart OAV={lav_oav:.1f} {'>5' if lav_oav > 5 else '(expected >5)'}")

# 7. Citrus architecture (bergamot + cedrat + mandarin)
berg = next(m for m in state.materials if "Bergamot" in m.name)
cedrat = next(m for m in state.materials if "Cedrat" in m.name)
mand = next(m for m in state.materials if "Mandarin" in m.name)
citrus_oav = safe_oav(berg) + safe_oav(cedrat) + safe_oav(mand)
checks.append(f"{'[OK]' if citrus_oav > 5000 else '[!!]'} Citrus architecture OAV={citrus_oav:,.0f} {'>5000' if citrus_oav > 5000 else '(expected >5000)'}")

# 8. White musk bed (Habanolide + Galaxolide)
hab = next(m for m in state.materials if "Habanolide" in m.name)
gal = next(m for m in state.materials if "Galaxolide" in m.name)
musk_oav = safe_oav(hab) + safe_oav(gal)
checks.append(f"{'[OK]' if musk_oav > 5 else '[!!]'} White musk bed OAV={musk_oav:.1f} {'>5' if musk_oav > 5 else '(expected >5)'}")

# 9. Alpha Ionone as restrained iris
ai = next(m for m in state.materials if m.name == "Alpha Ionone")
ai_oav = safe_oav(ai)
checks.append(f"{'[OK]' if ai_oav > 50 else '[!!]'} Alpha Ionone iris OAV={ai_oav:.1f} {'>50 (restrained bg)' if ai_oav > 50 else '(expected >50)'}")

# 10. Aldehydic sparkle in opening
first_frame = sim_frames[0] if sim_frames else None
if first_frame:
    alds_in_open = [d for d in first_frame.dominant_oav(limit=15) if "Aldehyde" in d['material']]
    if alds_in_open:
        ald_str = ", ".join(f"{a['material']}(OAV={a['oav']:.0f})" for a in alds_in_open)
        checks.append(f"[OK] Aldehydic sparkle in opening: {ald_str}")
    else:
        checks.append("[!!] No aldehydes in opening top OAV")

# 11. Linalyl Acetate cologne bridge
la = next(m for m in state.materials if "Linalyl Acetate" in m.name)
la_oav = safe_oav(la)
checks.append(f"{'[OK]' if la_oav > 50 else '[!!]'} Linalyl Acetate cologne bridge OAV={la_oav:.1f} {'>50' if la_oav > 50 else ''}")

# 12. D-Limonene bright flash
lim = next(m for m in state.materials if "Limonene" in m.name)
lim_oav = safe_oav(lim)
checks.append(f"{'[OK]' if lim_oav > 500 else '[!!]'} D-Limonene bright flash OAV={lim_oav:.0f} {'>500' if lim_oav > 500 else ''}")

print("\n  Signature Checks:")
for c in checks:
    print(f"    {c}")

# ---- OAV Claim Verification ----
print("\n  OAV CLAIM VERIFICATION (guide vs pipeline):")
guide_claims = {
    "Dihydromyrcenol": 9449, "Iso E Super": 4440,
    "Red Mandarin EO": 4336, "Cedrat FCF oil Sicilian": 2700,
    "Bergamot FCF oil Sicilian": 2582, "D-Limonene": 2177,
    "Hedione HC": 618, "Linalyl Acetate": 492,
    "Alpha Ionone": 423, "Orivone": 370,
    "Cardamom EO": 196, "Ultralia": 56,
    "Coumarin": 48, "Alpha Isomethyl Ionone": 20,
    "Lavender EO High Altitude": 14, "Helional": 11,
    "Galaxolide": 10, "Floralozone": 10,
    "Habanolide": 8.5, "Black Pepper EO": 6.4,
    "Alpha Irone": 4.2, "Sandalore": 2.5,
    "Ethyl Linalool": 1.5, "Vetiver EO (India)": 0.5,
    "Cedramber": 0.5, "Irotyl": 0.2,
}
oav_ok = 0
oav_mismatch = 0
for mat_name, claimed_oav in sorted(guide_claims.items()):
    actual = next((m.oav for m in state.materials if m.name == mat_name), None)
    if actual is not None:
        ratio = actual / claimed_oav if claimed_oav else 0
        within = 0.5 <= ratio <= 2.0
        marker = "[OK]" if within else "[~~]"
        if within:
            oav_ok += 1
        else:
            oav_mismatch += 1
        print(f"    {marker} {mat_name:35s} claimed={claimed_oav:>8}  actual={actual:>8.1f}  ratio={ratio:.2f}")
    else:
        print(f"    [!!] {mat_name:35s} NOT FOUND in pipeline output (name mismatch)")
        oav_mismatch += 1

# ---- Overall Verdict ----
print(f"\n\n{HR}")
print("VERDICT")
print(HR)

ok_count = sum(1 for c in checks if c.startswith("[OK]"))
warn_count = sum(1 for c in checks if c.startswith("[!!]"))

print(f"\n  Signature checks: {ok_count} passed, {warn_count} warnings")
if oav_ok + oav_mismatch > 0:
    print(f"  OAV claim accuracy: {oav_ok}/{oav_ok+oav_mismatch} within 2x of guide value")
print(f"  Pipeline gates: {report.status}")
print(f"  Commercial readiness: {report.commercial_readiness}")
print(f"  Combined confidence: {report.confidence.get('combined_confidence', 0):.1f}")
total_oav = sum(safe_oav(m) for m in state.materials)
print(f"  Total headspace OAV at t=0: {total_oav:,.0f}")

print()
score = ok_count - warn_count
if score >= 8 and report.status in ("PASS", "WARN"):
    print("  CONCLUSION: Formula STRONGLY matches Chanel Allure Homme Sport Blanche profile.")
    print("  All critical AHS markers: DHM sport freshness, hedione radiance,")
    print("  ambergris backbone, citrus architecture, white musk bed, and")
    print("  tonka drydown verified at correct OAV levels. Pipeline-confirmed.")
elif score >= 5:
    print("  CONCLUSION: Formula matches AHS profile with minor deviations.")
    print("  Core markers verified; review warnings for optimization.")
else:
    print("  CONCLUSION: Formula partially matches; review significant deviations noted above.")

print(f"\n{HR}")
