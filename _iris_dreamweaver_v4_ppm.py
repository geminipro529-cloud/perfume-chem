"""Iris Dreamweaver v4 — sub-ODT luxury injection layer on top of v3.

v3 hit a luxury ceiling at 64 because synergy was pinned at 95 and any
additive ppm to luxury-signaling materials also tripped a synergy penalty
(the engine read them as "new directions").

User insight: single-direction synergy can be broken with sub-ODT
additions — trace materials at OAV < 1.0 contribute molecular complexity
(luxury / rarity / hedonic) without crossing the single-compound
detection threshold that the synergy axis uses to count "directions."

v4 STRATEGY:
  1. Load v3 final SPEC.
  2. Add 5 sub-ODT luxury-signaling trace materials:
       Isobutyl Quinoline (dirty leather)
       Beta-Damascenone (rose-fruit rarity)
       Indole (dirty floral depth)
       Guaiacol (smoky woodsmoke)
       Ethyl Safranate (saffron)
     Each seeded at ~0.3× ODT_eth (OAV ≈ 0.3).
  3. Coord-descent on luxury axis with a HARD CAP: every trace's OAV
     must stay ≤ 0.9 (strictly sub-threshold). Also require:
       synergy ≥ 94.5   (synergy-preservation contract)
       no new overdoses
       brief-floor rule across all six 1.5-weight axes
"""
import io, os, sys, math, copy, json
if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import check_batch_scaling
from engine.dose_response import score_dose_response
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.odor_thresholds import ODT_DATA

# ── ODT supplement (incl. new trace materials) ──────────────────────
ODT_EXTRA = {
    "heliotropal":           5.0,
    "piperonal":             5.0,
    "anisaldehyde":          5.0,
    "gamma undecalactone":   1.0,
    "gamma decalactone":     1.5,
    "delta decalactone":     10.0,
    "ethyl maltol":          0.3,
    "hedione hc":            3.0,
    "mayol":                 3.0,
    "bourgeonal":            0.03,
    "lilyreal":              1.0,
    "dbca":                  0.5,
    "amyl cinnamic aldehyde":2.0,
    "aca":                   2.0,
    "dihydro beta ionone":   0.3,
    "irotyl":                1.0,
    "ethylene brassylate":   2.0,
    "exaltolide":            1.0,
    "ambrettolide":          0.5,
    "musk ketone":           2.0,
    "romandolide":           1.0,
    "habanolide":            1.5,
    "tonalide":              1.0,
    "ambermax":              0.5,
    "azarbre":               2.0,
    "koavone":               2.0,
    "cedarwood virginia":    3.0,
    "hexyl salicylate":      30.0,
    "myristic acid":         500.0,
    "benzyl alcohol":        60.0,
    "red mandarin":          2.0,
    "bergamot fcf sicilian": 1.5,
    "benzoin resinoid":      30.0,
    "alpha isomethyl ionone":3.0,
    "vanillin":              20.0,
    # ── v4 trace additions (sub-ODT targets) ──
    "isobutyl quinoline":    0.003,   # dirty leather, extreme potency
    "beta damascenone":      0.002,   # rose-fruit rarity marker
    "damascenone":           0.002,
    "indole":                0.3,
    "guaiacol":              3.0,
    "ethyl safranate":       1.0,
}

def lookup_odt(name):
    k = name.lower().strip()
    for nm, d in ODT_DATA.items():
        nk = nm.lower()
        if nk == k or k.startswith(nk) or nk in k:
            return d["odt_eth"]
    for nm, v in ODT_EXTRA.items():
        if nm == k or k.startswith(nm) or nm in k:
            return v
    return None

# ── V3 FINAL SPEC (loaded from v3 json) ──────────────────────────────
V3_PATH = "formulas/collections/Iris_Dreamweaver_v3_ppm.json"
with open(V3_PATH, encoding="utf-8") as f:
    v3_data = json.load(f)
SPEC: dict = copy.deepcopy(v3_data["spec"])

# ── V4: SUB-ODT TRACE LAYER ──────────────────────────────────────────
# Each material seeded at ~0.3 × ODT_eth → OAV ≈ 0.3 (well sub-threshold).
# Dilutions match inventory stock bottles.
TRACE_MATERIALS = {
    "Isobutyl Quinoline": {"seed_oav": 0.3, "dil": 0.10, "role": "trace_lux"},
    "Damascenone":        {"seed_oav": 0.3, "dil": 0.01, "role": "trace_lux"},
    "Indole":             {"seed_oav": 0.3, "dil": 0.10, "role": "trace_lux"},
    "Guaiacol":           {"seed_oav": 0.3, "dil": 0.10, "role": "trace_lux"},
    "Ethyl Safranate":    {"seed_oav": 0.3, "dil": 1.00, "role": "trace_lux"},
}
# Seed using the AUTHORITATIVE ODT returned by lookup_odt (engine-first).
for name, t in TRACE_MATERIALS.items():
    odt_actual = lookup_odt(name)
    ppm = odt_actual * t["seed_oav"]
    t["odt"] = odt_actual
    SPEC[name] = {"ppm": ppm, "dil": t["dil"], "role": t["role"]}
    print(f"  seed {name}: ODT={odt_actual:.4f} → ppm={ppm:.5f} (target OAV {t['seed_oav']})")

# ── AXIS WEIGHTS (unchanged) ─────────────────────────────────────────
AXIS_W = {
    "luxury":           1.5,
    "longevity":        1.5,
    "sillage":          1.5,
    "texture":          1.5,
    "stacking_depth":   1.5,
    "synergy":          1.5,
    "hedonic":          1.0,
    "skin_performance": 1.0,
    "perceptual_clarity": 0.2,
    "photorealism":     0.0,
}
BRIEF_AXES = [a for a, w in AXIS_W.items() if w >= 1.5]

def spec_to_ingredients(spec, batch_ml):
    batch_ul = batch_ml * 1000.0
    ing, dil = {}, {}
    for name, d in spec.items():
        active_ul = batch_ul * d["ppm"] / 1e6
        stock_ul = active_ul / d["dil"]
        ing[name] = stock_ul
        dil[name] = d["dil"]
    return ing, dil

def compute_oav_table(spec):
    rows = []
    for name, d in spec.items():
        odt = lookup_odt(name)
        oav = (d["ppm"] / odt) if odt else None
        rows.append({"name": name, "ppm": d["ppm"], "odt_eth": odt,
                     "oav": oav, "dil": d["dil"], "role": d["role"]})
    return rows

def trace_oav(spec, name):
    d = spec[name]
    odt = lookup_odt(name)
    return (d["ppm"] / odt) if odt else None

def score_spec(spec, batch_ml=10.0):
    ing, dil = spec_to_ingredients(spec, batch_ml)
    conc_total = sum(ing.values())
    scorer = FormulaScorer()
    fi = FormulaInfo(number=0, name="IrisDreamweaverV4", ingredients=ing,
                     dilutions=dil, concentrate_ml=conc_total/1000.0, description="")
    s = scorer.score(formula_to_vector(fi))
    wsum = sum(AXIS_W.values())
    log_sum = sum((w/wsum)*math.log(max(float(s.get(a,5.0)),5.0)) for a,w in AXIS_W.items())
    geo = math.exp(log_sum)
    dr = score_dose_response(ing, dilutions=dil, total_volume_ul=conc_total)
    checks = check_batch_scaling(ing, dil, batch_ml, batch_ml)
    errs = [c for c in checks if c.severity == "error"]
    warns = [c for c in checks if c.severity == "warn"]
    return {
        "geo": geo, "axes": {a: float(s.get(a,0)) for a in AXIS_W},
        "dr_score": dr.score, "overdosed": dr.overdosed, "marginal": dr.marginal,
        "optimal": dr.optimal, "oav_err": len(errs), "oav_warn": len(warns),
        "conc_ul": conc_total, "conc_pct": conc_total/(batch_ml*1000)*100,
        "ingredients": ing, "dilutions": dil,
    }

def print_result(label, res, spec=None):
    print(f"\n── {label} ──")
    print(f"  geo={res['geo']:.3f}  conc={res['conc_pct']:.2f}%  "
          f"dr={res['dr_score']:.1f}/100  od={len(res['overdosed'])}  "
          f"oav_err={res['oav_err']}  oav_warn={res['oav_warn']}")
    ax = res["axes"]
    print(f"  [brief] lux={ax['luxury']:.1f} long={ax['longevity']:.1f} "
          f"sill={ax['sillage']:.1f} tex={ax['texture']:.1f} "
          f"stk={ax['stacking_depth']:.1f} syn={ax['synergy']:.1f}")
    print(f"  [supp]  hed={ax['hedonic']:.1f} skin={ax['skin_performance']:.1f} "
          f"| [info] clar={ax['perceptual_clarity']:.1f} "
          f"photo={ax['photorealism']:.1f}")
    if spec is not None:
        # show trace OAVs
        tr = ", ".join(f"{n}:{trace_oav(spec, n):.2f}" for n in TRACE_MATERIALS if n in spec)
        print(f"  [trace OAVs] {tr}")

# ── SUB-ODT CONSTRAINED COORD-DESCENT ────────────────────────────────
MAX_TRACE_OAV = 0.9          # hard sub-threshold cap per trace (v4 contract)
SYNERGY_FLOOR = 94.5         # must hold

def v4_trace_descent(spec, target_axis="luxury", step=0.25, max_iters=4,
                     geo_tol=0.3, floor_drop=1.0):
    s = copy.deepcopy(spec)
    base = score_spec(s, 10.0)
    baseline_axes = dict(base["axes"])
    print(f"\n── Sub-ODT trace descent: boost {target_axis} ──")
    print(f"  start: {target_axis}={baseline_axes[target_axis]:.2f} "
          f"synergy={baseline_axes['synergy']:.2f} geo={base['geo']:.3f}")
    candidates = list(TRACE_MATERIALS.keys())
    improved = True
    itr = 0
    while improved and itr < max_iters:
        itr += 1
        improved = False
        for mat in candidates:
            if mat not in s:
                continue
            best_delta = 0.0
            best_mult = None
            best_res = None
            for mult in (1.0 + step, 1.0 + step*2, 1.0 - step):
                trial = copy.deepcopy(s)
                trial[mat]["ppm"] = trial[mat]["ppm"] * mult
                # HARD: sub-ODT constraint
                if trace_oav(trial, mat) > MAX_TRACE_OAV:
                    continue
                r = score_spec(trial, 10.0)
                # no new overdoses
                if len(r["overdosed"]) > len(base["overdosed"]):
                    continue
                # synergy floor
                if r["axes"]["synergy"] < SYNERGY_FLOOR:
                    continue
                # geo guard
                if r["geo"] < base["geo"] - geo_tol:
                    continue
                # brief-floor
                ok = True
                for a in BRIEF_AXES:
                    if r["axes"][a] < baseline_axes[a] - floor_drop:
                        ok = False; break
                if not ok:
                    continue
                d = r["axes"][target_axis] - base["axes"][target_axis]
                if d > best_delta + 0.03:
                    best_delta = d
                    best_mult = mult
                    best_res = r
            if best_mult is not None:
                s[mat]["ppm"] = s[mat]["ppm"] * best_mult
                oav = trace_oav(s, mat)
                print(f"    iter{itr}: {mat} ×{best_mult:.2f} "
                      f"(OAV→{oav:.2f}) "
                      f"→ {target_axis} {base['axes'][target_axis]:.2f}→{best_res['axes'][target_axis]:.2f} "
                      f"synergy {base['axes']['synergy']:.2f}→{best_res['axes']['synergy']:.2f} "
                      f"(geo {base['geo']:.3f}→{best_res['geo']:.3f})")
                base = best_res
                improved = True
    print(f"  end:   {target_axis}={base['axes'][target_axis]:.2f} "
          f"synergy={base['axes']['synergy']:.2f} geo={base['geo']:.3f}")
    return s, base

# ── EXECUTE ──────────────────────────────────────────────────────────
print("="*72)
print(" Iris Dreamweaver v4 — sub-ODT luxury layer (synergy-preserving)")
print("="*72)

# v3 anchor
print("\nv3 anchor axes (from v3 json):")
v3_ax = v3_data["axes"]
print(f"  lux={v3_ax['luxury']:.1f} long={v3_ax['longevity']:.1f} "
      f"sill={v3_ax['sillage']:.1f} tex={v3_ax['texture']:.1f} "
      f"stk={v3_ax['stacking_depth']:.1f} syn={v3_ax['synergy']:.1f}")
print(f"  geo(v3)={v3_data['geo']:.3f}")

spec = copy.deepcopy(SPEC)
r0 = score_spec(spec, 10.0)
print_result("v4 baseline (v3 SPEC + 5 trace materials seeded @ OAV 0.3)", r0, spec)

# ── Sub-ODT descent (strict OAV < 0.9 cap) ──
spec_1, r1 = v4_trace_descent(spec, "luxury", step=0.30, max_iters=5)
print_result("v4 after strict sub-ODT descent (OAV cap 0.9)", r1, spec_1)
spec, res = spec_1, r1

# ── Dose-response sweep: map luxury response vs trace OAV 0.3→3.0 ──
# User hypothesis: synergy doesn't flip until much higher. Probe this.
print("\n" + "="*72)
print(" DOSE SWEEP per trace material (others held at OAV 0.3)")
print("="*72)
sweep_results = {}
for tname, t in TRACE_MATERIALS.items():
    odt = t["odt"]
    sweep_results[tname] = []
    for target_oav in [0.1, 0.3, 0.6, 0.9, 1.5, 2.5, 5.0]:
        trial = copy.deepcopy(SPEC)
        # reset all traces to seed OAV 0.3
        for tn, tt in TRACE_MATERIALS.items():
            trial[tn] = {"ppm": tt["odt"] * 0.3, "dil": tt["dil"], "role": tt["role"]}
        # bump just this one
        trial[tname]["ppm"] = odt * target_oav
        r = score_spec(trial, 10.0)
        sweep_results[tname].append((target_oav, r["axes"]["luxury"],
                                     r["axes"]["synergy"], r["geo"],
                                     len(r["overdosed"])))
    print(f"\n  {tname} (ODT {odt:.4f} ppm):")
    print(f"    {'OAV':>6} {'lux':>6} {'syn':>6} {'geo':>7} {'od':>3}")
    for oav, lux, syn, geo, od in sweep_results[tname]:
        print(f"    {oav:>6.2f} {lux:>6.1f} {syn:>6.1f} {geo:>7.3f} {od:>3d}")

# ── Optimistic combination: set each trace at best OAV from its sweep ──
print("\n" + "="*72)
print(" OPTIMISTIC COMBINATION (each trace at its lux-maximizing OAV")
print("                         subject to synergy >= 94.5)")
print("="*72)
best_oavs = {}
for tname, data in sweep_results.items():
    # pick highest-luxury point with synergy >= SYNERGY_FLOOR and od=0
    viable = [(oav, lux, syn, geo, od) for oav, lux, syn, geo, od in data
              if syn >= SYNERGY_FLOOR and od == 0]
    if viable:
        best = max(viable, key=lambda x: x[1])
        best_oavs[tname] = best[0]
        print(f"  {tname}: best OAV={best[0]} → lux={best[1]:.1f} syn={best[2]:.1f}")
    else:
        best_oavs[tname] = 0.3
        print(f"  {tname}: no viable escalation — fallback OAV=0.3")

trial = copy.deepcopy(SPEC)
for tname, tt in TRACE_MATERIALS.items():
    trial[tname] = {"ppm": tt["odt"] * best_oavs[tname], "dil": tt["dil"], "role": tt["role"]}
r_combo = score_spec(trial, 10.0)
print_result("v4 optimistic combination", r_combo, trial)
# accept only if synergy holds and no overdoses
if r_combo["axes"]["synergy"] >= SYNERGY_FLOOR and len(r_combo["overdosed"]) == 0:
    spec, res = trial, r_combo
    print("  → ACCEPTED as v4 final")
else:
    print("  → REJECTED (synergy or overdose violation)")

# ── Final audit: confirm all traces are still sub-ODT ──
print("\n── Sub-ODT audit ──")
all_sub = True
for name in TRACE_MATERIALS:
    if name in spec:
        oav = trace_oav(spec, name)
        flag = "✓" if oav < 1.0 else "✗ ABOVE ODT"
        print(f"  {name:25s} ppm={spec[name]['ppm']:.5f}  OAV={oav:.3f}  {flag}")
        if oav >= 1.0:
            all_sub = False
print(f"  All traces sub-ODT: {all_sub}")

# ── Comparison table ──
print("\n" + "="*72)
print(" v3 vs v4 BRIEF-MARKER COMPARISON")
print("="*72)
print(f"  {'marker':<20} {'v3':>8} {'v4':>8} {'Δ':>7}")
for a in ["luxury","longevity","sillage","texture","stacking_depth","synergy",
          "hedonic","skin_performance","perceptual_clarity"]:
    d = res["axes"][a] - v3_ax[a]
    print(f"  {a:<20} {v3_ax[a]:>8.1f} {res['axes'][a]:>8.1f} {d:>+7.2f}")
dg = res["geo"] - v3_data["geo"]
print(f"  {'GEO':<20} {v3_data['geo']:>8.3f} {res['geo']:>8.3f} {dg:>+7.3f}")

# ── MD REPORT ────────────────────────────────────────────────────────
BATCHES = [5.0, 10.0, 30.0, 100.0]
oav_rows = compute_oav_table(spec)

md = []
md += ["# Iris Dreamweaver v4 — Sub-ODT Luxury Layer", ""]
md += ["**Hypothesis:** Single-direction synergy constraint (pinned at 95 in v3) "
       "counts only materials whose individual OAV ≥ 1 as \"directions.\" Trace "
       "additions at OAV < 1 contribute molecular complexity cues to the "
       "luxury axis without crossing the detection threshold that the synergy "
       "axis polices.", ""]
md += ["**Trace materials added:**", "",
       "| Material | Role | ODT (ppm) | Target OAV | Sub-ODT? |",
       "|---|---|--:|--:|---|"]
for name, t in TRACE_MATERIALS.items():
    if name in spec:
        oav = trace_oav(spec, name)
        md.append(f"| {name} | {t['role']} | {t['odt']:.4f} | {oav:.2f} | "
                  f"{'✓' if oav < 1.0 else '✗'} |")
md += [""]

md += ["## v3 → v4 brief-marker comparison", "",
       "| Marker | v3 | v4 | Δ |", "|---|--:|--:|--:|"]
for a in ["luxury","longevity","sillage","texture","stacking_depth","synergy",
          "hedonic","skin_performance","perceptual_clarity"]:
    d = res["axes"][a] - v3_ax[a]
    md.append(f"| {a} | {v3_ax[a]:.1f} | {res['axes'][a]:.1f} | {d:+.2f} |")
md.append(f"| **geo** | **{v3_data['geo']:.3f}** | **{res['geo']:.3f}** | "
          f"**{res['geo']-v3_data['geo']:+.3f}** |")
md += [""]

md += ["## Final formula (v4) — full ppm / OAV table", "",
       "| Material | Role | ppm juice | Dilution | ODT eth | OAV |",
       "|---|---|--:|---|--:|--:|"]
for row in oav_rows:
    odt_s = f"{row['odt_eth']:.4f}" if row["odt_eth"] else "—"
    oav_s = f"{row['oav']:.3f}" if row["oav"] and row["oav"] < 1 else (f"{row['oav']:.0f}" if row["oav"] else "—")
    dil_s = "neat" if row["dil"] == 1.0 else f"{row['dil']*100:.1f}%"
    ppm_s = f"{row['ppm']:.4f}" if row["ppm"] < 1 else f"{row['ppm']:,.0f}"
    md.append(f"| {row['name']} | {row['role']} | {ppm_s} | {dil_s} | {odt_s} | {oav_s} |")
md += [""]

md += ["## Batch derivations (µL of stock)", "",
       "| Material | Dilution | 5 mL | 10 mL | 30 mL | 100 mL |",
       "|---|---|--:|--:|--:|--:|"]
rows_by_batch = {b: spec_to_ingredients(spec, b)[0] for b in BATCHES}
for name in spec:
    dil = spec[name]["dil"]
    dil_s = "neat" if dil == 1.0 else f"{dil*100:.1f}%"
    cells = " | ".join(f"{rows_by_batch[b][name]:.4f}" if rows_by_batch[b][name] < 1
                      else f"{rows_by_batch[b][name]:.2f}" for b in BATCHES)
    md.append(f"| {name} | {dil_s} | {cells} |")
md.append("| **Concentrate total** | | " + " | ".join(
    f"**{sum(rows_by_batch[b].values()):.1f}**" for b in BATCHES) + " |")
md.append("| **Ethanol 96% (µL)** | | " + " | ".join(
    f"**{b*1000 - sum(rows_by_batch[b].values()):.0f}**" for b in BATCHES) + " |")
md.append("| **Batch (µL)** | | " + " | ".join(f"**{b*1000:.0f}**" for b in BATCHES) + " |")
md += [""]

md += ["## Practical note on sub-ODT dosing", "",
       "Several of these traces (IBQ, Damascenone, Indole) are at ppm so low that "
       "direct pipetting from the stock bottle is impractical at small batches. "
       "The recommended workflow is a two-stage dilution: prepare a 0.1% or 0.01% "
       "working solution of each trace in DPG, then pipette from that. For 10 mL "
       "and under, expect most trace amounts to round to 0.01–0.5 µL of a secondary "
       "dilution. This is standard practice for haute-parfumerie trace dosing.", ""]

out = "formulas/collections/Iris_Dreamweaver_v4_ppm.md"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
with open("formulas/collections/Iris_Dreamweaver_v4_ppm.json", "w", encoding="utf-8") as f:
    json.dump({"spec": spec, "axes": res["axes"], "geo": res["geo"],
               "v3_axes": v3_ax, "v3_geo": v3_data["geo"]}, f, indent=2)
print(f"\n✓ Saved: {out}")
print(f"✓ Saved: formulas/collections/Iris_Dreamweaver_v4_ppm.json")
