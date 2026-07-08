"""Comprehensive cross-system validation of perfume-chem ingredient properties.

Checks consistency of MW, VP, ClogP, ODT, note-classification, hedonic valence,
IFRA limits, and cost data across ALL modules that store them. Reports gaps,
inconsistencies, and missing data.
"""

import sys
import os

sys.path.insert(0, r"D:\chatbots\perfume-chem")

from pathlib import Path

# ── Parse inventory ──────────────────────────────────────────────────
from engine.inventory_parser import parse_inventory, inventory_names

# ── Load all data modules with graceful error handling ────────────────
modules_loaded = {}

try:
    from engine.ingredient_intelligence import _PROFILES, get_profile
    modules_loaded["ingredient_intelligence"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.ingredient_intelligence: {e}")
    modules_loaded["ingredient_intelligence"] = False
    _PROFILES = {}

try:
    from engine.odor_thresholds import ODT_DATA
    modules_loaded["odor_thresholds"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.odor_thresholds: {e}")
    modules_loaded["odor_thresholds"] = False
    ODT_DATA = {}

try:
    from engine.skin_interaction import SKIN_PHYSCHEM
    modules_loaded["skin_interaction"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.skin_interaction: {e}")
    modules_loaded["skin_interaction"] = False
    SKIN_PHYSCHEM = {}

try:
    from engine.diffusion_model import DIFFUSION_DATA
    modules_loaded["diffusion_model"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.diffusion_model: {e}")
    modules_loaded["diffusion_model"] = False
    DIFFUSION_DATA = {}

try:
    from engine.temporal_graph import _ODT_LITERATURE
    modules_loaded["temporal_graph"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.temporal_graph: {e}")
    modules_loaded["temporal_graph"] = False
    _ODT_LITERATURE = {}

try:
    from engine.hedonic_model import HEDONIC_VALENCE
    modules_loaded["hedonic_model"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.hedonic_model: {e}")
    modules_loaded["hedonic_model"] = False
    HEDONIC_VALENCE = {}

try:
    from engine.ifra_safety import IFRA_CAT4_LIMITS
    modules_loaded["ifra_safety"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.ifra_safety: {e}")
    modules_loaded["ifra_safety"] = False
    IFRA_CAT4_LIMITS = {}

try:
    from engine.cost_analysis import MATERIAL_COSTS_PER_KG
    modules_loaded["cost_analysis"] = True
except Exception as e:
    print(f"[WARN] Could not import engine.cost_analysis: {e}")
    modules_loaded["cost_analysis"] = False
    MATERIAL_COSTS_PER_KG = {}

# ── Name normalization ────────────────────────────────────────────────
def normalize(name: str) -> str:
    return name.strip().lower()

# Build lookup dictionaries with normalized keys
profiles_norm = {}
for k, v in _PROFILES.items():
    profiles_norm[normalize(k)] = (k, v)

odt_norm = {}
for k, v in ODT_DATA.items():
    odt_norm[normalize(k)] = (k, v)

skin_norm = {}
for k, v in SKIN_PHYSCHEM.items():
    skin_norm[normalize(k)] = (k, v)

diff_norm = {}
for k, v in DIFFUSION_DATA.items():
    diff_norm[normalize(k)] = (k, v)

temporal_norm = {}
for k, v in _ODT_LITERATURE.items():
    temporal_norm[normalize(k)] = (k, v)

hedonic_norm = {}
for k, v in HEDONIC_VALENCE.items():
    hedonic_norm[normalize(k)] = (k, v)

ifra_norm = {}
for k, v in IFRA_CAT4_LIMITS.items():
    ifra_norm[normalize(k)] = (k, v)

cost_norm = {}
for k, v in MATERIAL_COSTS_PER_KG.items():
    cost_norm[normalize(k)] = (k, v)

# ── Inventory materials (deduplicated, excluding solvents) ──────────
inv_materials = parse_inventory(
    Path(r"D:\chatbots\perfume-chem\inventory.txt"),
    unique=True,
    include_solvents=False,
)
inv_names = [m.name for m in inv_materials]
inv_name_set = set(normalize(n) for n in inv_names)

print("=" * 80)
print("PERFUME-CHEM INGREDIENT VALIDATION REPORT")
print("=" * 80)

# ── 1. Module loading status ──────────────────────────────────────────
print("\n--- MODULE LOADING STATUS ---")
for mod, ok in modules_loaded.items():
    status = "OK" if ok else "FAILED"
    print(f"  {mod}: {status}")

# ── 2. Inventory coverage ─────────────────────────────────────────────
print(f"\n--- INVENTORY COVERAGE ---")
print(f"  Total inventory materials (excl. solvents): {len(inv_names)}")

missing_profiles = []
for mat in inv_names:
    n = normalize(mat)
    if n not in profiles_norm:
        missing_profiles.append(mat)

print(f"  Materials with _PROFILES entry: {len(inv_names) - len(missing_profiles)}/{len(inv_names)}")
if missing_profiles:
    print(f"  Missing from _PROFILES ({len(missing_profiles)}):")
    for m in missing_profiles:
        print(f"    - {m}")

# ── 3. Cross-system consistency ────────────────────────────────────────
print(f"\n--- CROSS-SYSTEM CONSISTENCY ---")
inconsistencies = []

# 3a. MW consistency: ingredient_intelligence vs skin_interaction vs diffusion_model
print("\n  [MW Consistency]")
mw_checked = 0
mw_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    mw_prof = data.get("mw")
    if mw_prof is None:
        continue
    # Check skin_interaction
    if nk in skin_norm:
        _, sdata = skin_norm[nk]
        mw_skin = sdata.get("MW")
        if mw_skin is not None and mw_prof is not None:
            mw_checked += 1
            if abs(mw_prof - mw_skin) > 0.5:
                issue = f"MW mismatch: {orig_name}: Profiles={mw_prof}, Skin={mw_skin} (diff={abs(mw_prof-mw_skin):.1f})"
                inconsistencies.append(("MW", orig_name, issue))
                mw_issues += 1
    # Check diffusion_model
    if nk in diff_norm:
        _, ddata = diff_norm[nk]
        mw_diff = ddata.get("MW")
        if mw_diff is not None and mw_prof is not None:
            mw_checked += 1
            if abs(mw_prof - mw_diff) > 0.5:
                issue = f"MW mismatch: {orig_name}: Profiles={mw_prof}, Diffusion={mw_diff} (diff={abs(mw_prof-mw_diff):.1f})"
                inconsistencies.append(("MW", orig_name, issue))
                mw_issues += 1

print(f"    Checked: {mw_checked}, Issues: {mw_issues}")

# 3b. VP consistency: ingredient_intelligence vs diffusion_model
print("\n  [VP Consistency]")
vp_checked = 0
vp_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    vp_prof = data.get("vp")
    if vp_prof is None:
        continue
    if nk in diff_norm:
        _, ddata = diff_norm[nk]
        vp_diff = ddata.get("VP_25")
        if vp_diff is not None:
            vp_checked += 1
            larger = max(vp_prof, vp_diff)
            smaller = min(vp_prof, vp_diff)
            if smaller > 0 and larger / smaller > 2.0:
                issue = f"VP mismatch: {orig_name}: Profiles={vp_prof}, Diffusion={vp_diff} (ratio={larger/smaller:.1f}x)"
                inconsistencies.append(("VP", orig_name, issue))
                vp_issues += 1
print(f"    Checked: {vp_checked}, Issues: {vp_issues}")

# 3c. ODT consistency: ingredient_intelligence vs odor_thresholds vs temporal_graph
print("\n  [ODT Consistency]")
odt_checked = 0
odt_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    odt_prof = data.get("odt")
    if odt_prof is None:
        continue
    # Check vs odor_thresholds (both store odt_air in ppb)
    if nk in odt_norm:
        _, odata = odt_norm[nk]
        odt_air = odata.get("odt_air")
        if odt_air is not None:
            odt_checked += 1
            if odt_prof > 0 and odt_air > 0:
                ratio = max(odt_prof, odt_air) / min(odt_prof, odt_air)
                if ratio > 3.0:
                    issue = f"ODT mismatch: {orig_name}: Profiles={odt_prof} ppb, ODT_DATA={odt_air} ppb (ratio={ratio:.1f}x)"
                    inconsistencies.append(("ODT", orig_name, issue))
                    odt_issues += 1
    # Check vs temporal_graph
    if nk in temporal_norm:
        _, tdata = temporal_norm[nk]
        odt_tg = tdata if isinstance(tdata, (int, float)) else None
        if odt_tg is not None:
            odt_checked += 1
            if odt_prof > 0 and odt_tg > 0:
                ratio = max(odt_prof, odt_tg) / min(odt_prof, odt_tg)
                if ratio > 3.0:
                    issue = f"ODT mismatch: {orig_name}: Profiles={odt_prof} ppb, Temporal={odt_tg} ppb (ratio={ratio:.1f}x)"
                    inconsistencies.append(("ODT", orig_name, issue))
                    odt_issues += 1
print(f"    Checked: {odt_checked}, Issues: {odt_issues}")

# 3d. Note classification consistency between profiles and temporal_graph
#    (temporal_graph doesn't have a note field, so check ODT_DATA char vs profile note)
#    Actually, temporal_graph gets note from get_profile() — so check _PROFILES note
#    against any note info that might be in ODT_DATA. ODT_DATA has 'char' field.
print("\n  [Note Classification Consistency]")
# No note field in ODT_DATA, so this check is N/A for ODT_DATA vs profiles.
# We check that every profile has a valid note.
note_values = {"top", "heart", "base"}
note_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    note = data.get("note", "heart")
    if note not in note_values:
        issue = f"Invalid note: {orig_name}: note='{note}' (expected top/heart/base)"
        inconsistencies.append(("NOTE", orig_name, issue))
        note_issues += 1
print(f"    Checked: {len(profiles_norm)}, Issues: {note_issues}")

# 3e. LogP / ClogP consistency: ingredient_intelligence vs skin_interaction
print("\n  [LogP/ClogP Consistency]")
logp_checked = 0
logp_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    clogp_prof = data.get("clogp")
    if clogp_prof is None:
        continue
    if nk in skin_norm:
        _, sdata = skin_norm[nk]
        logp_skin = sdata.get("logP")
        if logp_skin is not None:
            logp_checked += 1
            if abs(clogp_prof - logp_skin) > 0.5:
                issue = f"LogP mismatch: {orig_name}: Profiles clogP={clogp_prof}, Skin logP={logp_skin} (diff={abs(clogp_prof-logp_skin):.2f})"
                inconsistencies.append(("LogP", orig_name, issue))
                logp_issues += 1
print(f"    Checked: {logp_checked}, Issues: {logp_issues}")

# ── 4. Data completeness ────────────────────────────────────────────────
print(f"\n--- DATA COMPLETENESS ---")

# 4a. Properties with zero or None values in profiles
print("\n  [Zero/None Values in _PROFILES]")
zero_none_issues = 0
for nk, (orig_name, data) in profiles_norm.items():
    for prop in ("mw", "vp", "clogp", "odt", "odt_ppm", "note", "role"):
        val = data.get(prop)
        if val is None or val == 0:
            issue = f"Missing/zero: {orig_name}.{prop} = {val}"
            inconsistencies.append(("MISSING", orig_name, issue))
            zero_none_issues += 1
print(f"    Issues: {zero_none_issues}")

# ── 5. Gap report ────────────────────────────────────────────────────────
print(f"\n--- GAP REPORT: Materials missing from key property systems ---")

gaps = 0

# 5a. Inventory -> _PROFILES
print(f"\n  [Inventory -> _PROFILES]")
prof_gap = []
for mat in inv_names:
    n = normalize(mat)
    if n not in profiles_norm:
        prof_gap.append(mat)
        gaps += 1
print(f"    Missing: {len(prof_gap)}")
for m in prof_gap[:20]:
    print(f"      - {m}")
if len(prof_gap) > 20:
    print(f"      ... and {len(prof_gap)-20} more")

# 5b. Profiles -> ODT_DATA
print(f"\n  [Profiles -> ODT_DATA (odor_thresholds)]")
odt_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in odt_norm:
        odt_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(odt_gap)}")
for m in odt_gap[:15]:
    print(f"      - {m}")
if len(odt_gap) > 15:
    print(f"      ... and {len(odt_gap)-15} more")

# 5c. Profiles -> SKIN_PHYSCHEM
print(f"\n  [Profiles -> SKIN_PHYSCHEM]")
skin_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in skin_norm:
        skin_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(skin_gap)}")
for m in skin_gap[:15]:
    print(f"      - {m}")
if len(skin_gap) > 15:
    print(f"      ... and {len(skin_gap)-15} more")

# 5d. Profiles -> DIFFUSION_DATA
print(f"\n  [Profiles -> DIFFUSION_DATA]")
diff_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in diff_norm:
        diff_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(diff_gap)}")
for m in diff_gap[:15]:
    print(f"      - {m}")
if len(diff_gap) > 15:
    print(f"      ... and {len(diff_gap)-15} more")

# 5e. Profiles -> _ODT_LITERATURE (temporal_graph)
print(f"\n  [Profiles -> _ODT_LITERATURE (temporal_graph)]")
temporal_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in temporal_norm:
        temporal_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(temporal_gap)}")
for m in temporal_gap[:15]:
    print(f"      - {m}")
if len(temporal_gap) > 15:
    print(f"      ... and {len(temporal_gap)-15} more")

# 5f. Profiles -> HEDONIC_VALENCE
print(f"\n  [Profiles -> HEDONIC_VALENCE]")
hedonic_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in hedonic_norm:
        hedonic_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(hedonic_gap)}")
for m in hedonic_gap[:15]:
    print(f"      - {m}")
if len(hedonic_gap) > 15:
    print(f"      ... and {len(hedonic_gap)-15} more")

# 5g. Profiles -> IFRA_CAT4_LIMITS
print(f"\n  [Profiles -> IFRA_CAT4_LIMITS]")
ifra_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in ifra_norm:
        ifra_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(ifra_gap)}")
for m in ifra_gap[:15]:
    print(f"      - {m}")
if len(ifra_gap) > 15:
    print(f"      ... and {len(ifra_gap)-15} more")

# 5h. Profiles -> MATERIAL_COSTS_PER_KG
print(f"\n  [Profiles -> MATERIAL_COSTS_PER_KG]")
cost_gap = []
for orig_name, data in _PROFILES.items():
    n = normalize(orig_name)
    if n not in cost_norm:
        cost_gap.append(orig_name)
        gaps += 1
print(f"    Missing: {len(cost_gap)}")
for m in cost_gap[:15]:
    print(f"      - {m}")
if len(cost_gap) > 15:
    print(f"      ... and {len(cost_gap)-15} more")

# ── 6. OAV calculation readiness ─────────────────────────────────────────
print(f"\n--- OAV CALCULATION READINESS ---")
oav_ready = 0
oav_not_ready = []
for orig_name, data in _PROFILES.items():
    has_odt_eth = data.get("odt_ppm") is not None
    has_vp = data.get("vp") is not None
    if has_odt_eth:
        oav_ready += 1
    else:
        oav_not_ready.append((orig_name, "no odt_ppm"))
    if not has_vp:
        if orig_name not in [x[0] for x in oav_not_ready]:
            oav_not_ready.append((orig_name, "no vp"))

print(f"  Materials with odt_ppm (OAV-ready): {oav_ready}/{len(_PROFILES)}")
print(f"  Materials missing odt_ppm: {len([x for x in oav_not_ready if 'odt_ppm' in x[1]])}")

# Also check ODT_DATA for entries that have odt_eth
odt_eth_count = sum(1 for v in ODT_DATA.values() if v.get("odt_eth") is not None)
odt_air_count = sum(1 for v in ODT_DATA.values() if v.get("odt_air") is not None)
print(f"  ODT_DATA entries with odt_air: {odt_air_count}")
print(f"  ODT_DATA entries with odt_eth: {odt_eth_count}")

# Cross-reference: materials in profiles with no odt_ppm but have odt_eth in ODT_DATA
fixable = 0
for orig_name, data in _PROFILES.items():
    if data.get("odt_ppm") is None:
        n = normalize(orig_name)
        if n in odt_norm:
            _, odata = odt_norm[n]
            if odata.get("odt_eth") is not None:
                fixable += 1
print(f"  Materials fixable from ODT_DATA (have odt_eth but profile missing odt_ppm): {fixable}")

# ── 7. Specific VP/ODT discrepancies worth flagging ───────────────────────
print(f"\n--- NOTABLE DISCREPANCIES (>3x ratio or >5% MW diff) ---")
notable = []
for kind, name, desc in inconsistencies:
    if kind in ("MW", "VP", "ODT", "LogP"):
        notable.append(desc)

if notable:
    for desc in notable:
        print(f"  * {desc}")
else:
    print("  None found.")

# ── SUMMARY ─────────────────────────────────────────────────────────────
print(f"\n{'=' * 80}")
print(f"SUMMARY")
print(f"{'=' * 80}")
print(f"  Inventory materials checked: {len(inv_names)}")
print(f"  _PROFILES entries: {len(_PROFILES)}")
print(f"  ODT_DATA entries: {len(ODT_DATA)}")
print(f"  SKIN_PHYSCHEM entries: {len(SKIN_PHYSCHEM)}")
print(f"  DIFFUSION_DATA entries: {len(DIFFUSION_DATA)}")
print(f"  _ODT_LITERATURE entries: {len(_ODT_LITERATURE)}")
print(f"  HEDONIC_VALENCE entries: {len(HEDONIC_VALENCE)}")
print(f"  IFRA_CAT4_LIMITS entries: {len(IFRA_CAT4_LIMITS)}")
print(f"  MATERIAL_COSTS_PER_KG entries: {len(MATERIAL_COSTS_PER_KG)}")
print()
inconsistency_count = len(inconsistencies)
print(f"  Total inconsistencies found: {inconsistency_count}")
print(f"  Total gaps found: {gaps}")
print(f"  Missing from _PROFILES (inventory materials): {len(missing_profiles)}")
print(f"  Zero/None property values: {zero_none_issues}")

kind_counts = {}
for kind, _, _ in inconsistencies:
    kind_counts[kind] = kind_counts.get(kind, 0) + 1
print(f"\n  Inconsistencies by type:")
for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
    print(f"    {kind}: {count}")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)