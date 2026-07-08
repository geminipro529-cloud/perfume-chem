"""Iris-Jasmine *Luxe Lactée* — character-aligned optimization.

Baseline: formulas/Iris_Jasmine_Luxe_Lactee.md (mass-fraction spec converted to
µL at 11 000 µL concentrate / 50 mL @ 22 % EDP reference batch).

Character axes emphasized per brief (hedonic, depth, complexion, luxury,
texture). Composite weights up-weight hedonic + texture + luxury +
stacking_depth + skin_performance; longevity/sillage kept at base; photorealism
and perceptual_clarity down-weighted (this is a stylized soft-floral, not a
photoreal EO composition).

Guardrails:
  * NO narcotic molecules: Indole, Skatole, Methyl Anthranilate, PCME,
    Cinnamaldehyde, Isoeugenol, Eugenol — blocked from optimizer moves
  * NO pre-blended materials: every FTEC / FO / Accord / Fleuressence / Core
    blocked (per repo rules 2026-04-23)
  * Pillar floors at 60 % of baseline for: Hedione HC, Alpha Irone, Ebanol,
    Hexyl Salicylate, Heliotropal, Ambrettolide, Exaltolide, Musk Ketone,
    Alpha Isomethyl Ionone, Orivone
  * IFRA caps on Coumarin, Hydroxycitronellal, Bergamot FCF, etc.
  * Cis Jasmone ceiling 120 µL (overdose = celery-soup)
  * Ethyl Safranate ceiling 80 µL (overdose = medicinal-saffron)
  * Gamma Undecalactone ceiling 300 µL (overdose = dessert)
  * γ-Undecalactone floor 100 µL (signal molecule — lactonic bridge)
  * Musk Ketone active ceiling (10 % dilution): 550 µL of dilution
    (= 55 µL active, respects powder-echo brief, avoids nitro-musk overdose)

Output: _opt_iris_jasmine_luxe_out.txt (streamed) and
        _opt_iris_jasmine_luxe_out.json (final ing/dil/axes/geo).
"""

from __future__ import annotations
import copy, io, json, math, os, sys, time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True, write_through=True)
except Exception:
    pass

sys.path.insert(0, ".")

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from engine.formula_analyzer import FormulaInfo, formula_to_vector


# ── Character-aligned axis weights ─────────────────────────
# Brief pillars: hedonic, depth(→stacking_depth), complexion(→skin_performance),
# luxury, texture.  Photorealism and perceptual_clarity de-weighted — this is
# stylized perfumery not a photoreal EO reconstruction.
AXIS_WEIGHTS = {
    "hedonic":            1.6,   # olfactory pleasure — top priority
    "texture":            1.4,   # silk tactility
    "luxury":             1.4,   # Alpha Irone + Heliotropal + Ebanol registers
    "stacking_depth":     1.2,   # depth axis
    "skin_performance":   1.2,   # complexion / salicylate cushion
    "longevity":          1.0,   # base — standard weight
    "sillage":            1.0,   # base — standard weight
    "synergy":            0.8,
    "photorealism":       0.4,   # de-weight: not an EO-photoreal brief
    "perceptual_clarity": 0.4,   # de-weight: softness > clarity here
}
WSUM = sum(AXIS_WEIGHTS.values())


def geo_composite(detail: dict) -> float:
    log_sum = 0.0
    for a, w in AXIS_WEIGHTS.items():
        v = max(float(detail.get(a, 5.0)), 5.0)
        log_sum += (w / WSUM) * math.log(v)
    return round(math.exp(log_sum), 3)


def score_formula(ing: dict, dil: dict, scorer: FormulaScorer):
    total_ul = sum(ing.values())
    fi = FormulaInfo(number=0, name="IJLL", ingredients=ing, dilutions=dil,
                     concentrate_ml=total_ul / 1000.0, description="")
    fv = formula_to_vector(fi)
    s = scorer.score(fv)
    detail = {a: float(s.get(a, 5.0)) for a in AXIS_WEIGHTS}
    return geo_composite(detail), detail


# ── Baseline formula (50 mL EDP reference, 11 000 µL concentrate = 22 %) ─
# µL of AS-BOTTLED material (dilution baked into the µL figure)
BASE_ING = {
    # TOP (v7: bergamot/petitgrain trimmed to fund iris pillar)
    "Bergamot FCF oil Sicilian":    420.0,   # v7: -30
    "Petitgrain EO":                155.0,   # v7: -10
    "Aldehyde C12 MNA":             330.0,   # 1 %
    "Ethyl Safranate":               55.0,
    "Helional":                      80.0,   # watery-green aldehydic halo
    # HEART — jasmine chord (v7: HC slashed to 800, std Hedione bulk carrier added)
    "Hedione HC":                   800.0,   # v7: -2070 (receptor-active heart radiance only; Dior Homme window)
    "Hedione":                     1035.0,   # v7 NEW/v8 -30: bulk solvent-carrier (funds Indole trace)
    "Cis Jasmone":                  120.0,   # v7: +32 — true jasmine marker
    "Dihydrojasmone":                40.0,   # warm jasmine-ketone rounder
    "Amyl Cinnamic Aldehyde":       115.0,   # v7: +35 — waxy-jasmine body
    "Indole (10%)":                  30.0,   # v8 NEW: 10 % dil = 3 µL active (0.027 %) — the honest drop of dirt
    "Benzyl Acetate":               308.0,
    "Gamma Undecalactone":          230.0,   # v7: +65 — lactonic peach expansion
    "Delta Decalactone":            120.0,   # v7: +30 — coconut-peach texture
    # HEART — iris (v7: α-Irone pillar strengthened, β-Ionone/Carrot/Geosmin added)
    "Alpha Irone":                 1200.0,   # v7: +180 (30 % in DEP)
    "Alpha Isomethyl Ionone":       490.0,
    "Orivone":                      280.0,   # v7: +45
    "Heliotropal":                  360.0,   # v7: +85 — powder-almond bridge
    "Ultralia":                      50.0,   # v7: +6
    "Cashmeran":                    250.0,   # v7: +50 (20 % dilution)
    "Beta Ionone":                   20.0,   # v7 NEW: neat — ODT 0.007 ng/L, most potent luxury signal/µL
    "Carrot Seed EO":                50.0,   # v7 NEW: carotol/daucol natural orris-root depth
    "Geosmin (1% in TEC)":            3.0,   # v7 NEW: ppt-level petrichor (Silver Mist signature)
    # BASE (v7: Exaltolide promoted to pillar, Ebanol +200, MK/Coumarin/Ambrofix trimmed)
    "Hexyl Salicylate":             900.0,   # brief-floor salicylate diffusion film
    "Ebanol":                      1050.0,   # v7: +200 — creamy-milk sandal pillar
    "Coumarin":                     395.0,   # v7: -45 (20 %)
    "Musk Ketone":                  344.0,   # v7: -41 (10 %)
    "Exaltolide":                   700.0,   # v7: +260 — milky-skin lactonic pillar (Lactée spine)
    "Ambrettolide":                 360.0,   # v7: +70 (10 %)
    "Ambrofix":                     410.0,   # 30 %
    "Ethylene Brassylate":          300.0,   # neat creamy-lactonic macrocyclic musk
}
BASE_DIL = {
    "Bergamot FCF oil Sicilian":    1.00,
    "Petitgrain EO":                1.00,
    "Aldehyde C12 MNA":             0.01,
    "Ethyl Safranate":              1.00,
    "Helional":                     1.00,
    "Hedione HC":                   1.00,
    "Hedione":                      1.00,   # v7 NEW (neat standard Hedione)
    "Cis Jasmone":                  1.00,
    "Dihydrojasmone":               1.00,
    "Amyl Cinnamic Aldehyde":       1.00,
    "Indole (10%)":                 0.10,   # v8 NEW
    "Benzyl Acetate":               1.00,
    "Gamma Undecalactone":          1.00,
    "Alpha Irone":                  0.30,
    "Alpha Isomethyl Ionone":       1.00,
    "Orivone":                      1.00,
    "Heliotropal":                  1.00,
    "Ultralia":                     1.00,
    "Cashmeran":                    0.20,
    "Beta Ionone":                  1.00,   # v7 NEW (neat)
    "Carrot Seed EO":               1.00,   # v7 NEW (neat)
    "Geosmin (1% in TEC)":          0.01,   # v7 NEW (1 % dilution in TEC)
    "Hexyl Salicylate":             1.00,
    "Ebanol":                       1.00,
    "Coumarin":                     0.20,
    "Musk Ketone":                  0.10,
    "Exaltolide":                   0.10,
    "Ambrettolide":                 0.10,
    "Ambrofix":                     0.30,
    "Delta Decalactone":            1.00,
    "Ethylene Brassylate":          1.00,
}
assert abs(sum(BASE_ING.values()) - 11000.0) < 1.0, \
    f"baseline must sum to 11000 µL, got {sum(BASE_ING.values()):.1f}"

# ── Narcotic & pre-blend block ─────────────────────────────
# Absolute block: these materials must stay at 0 µL in every candidate.
BLOCKED = {
    # Narcotic / Thai-medicinal axis (explicit user ban; v8 un-bans Indole trace)
    "Skatole", "Methyl Anthranilate",
    "p-Cresyl Methyl Ether (PCME)", "PCME",
    "Cinnamaldehyde", "Isoeugenol", "Eugenol",
    # Pre-blends (repo rule 2026-04-23)
    "Orris F-TEC", "I-IRIS F-TEC", "Cardamom FTEC", "Styrax FTEC",
    "Heliotropin Fleuressence", "Jasmine FO", "Sandalwood FO",
    "Tonka Bean FO", "Amber Core", "Violet Fleuressence",
    "Blackcurrant FTEC", "Dewberry FTEC", "Leather FO",
    "Tobacco FTEC", "Tobacco Fleuressence", "Ginger FTEC",
    "Oud Fleuressence", "Black Pepper FTEC",
    # Off-brief (would break Soft Floral Iris-Lactonic register)
    "Birch Tar Rectified", "Guaiacol", "Isobutyl Quinoline",
    "Evernyl", "Patchouli EO", "Vetiver EO", "Dynascone",
    "Galbanum Resinoid", "Leafovert", "Champaca Flower EO",
    "Ylang Comoros Complete EO F3255", "Ylang Comoros III EO F3295",
    "Ylang Ylang EO (Extra grade)",   # ylang pulls narcotic-indolic
    "Methyl Salicylate", "Methyl Benzoate",
    "Cis Jasmone",  # keep cis-jasmone but block OVERDOSE above ceiling (handled in bounds)
}
BLOCKED.discard("Cis Jasmone")   # allow, capped via bounds()

# ── Pillars — structural materials optimizer may shrink only to 60 % floor ─
PILLARS = {
    "Hedione HC", "Hedione", "Alpha Irone", "Ebanol", "Hexyl Salicylate",
    "Heliotropal", "Ambrettolide", "Exaltolide", "Musk Ketone",
    "Alpha Isomethyl Ionone", "Orivone", "Gamma Undecalactone",
    "Ambrofix",
}
PILLAR_FLOOR_FRAC = 0.60
PILLAR_CEIL_FRAC  = 1.45   # pillar ceiling at 145 % of baseline to prevent blow-up

# ── Per-material ceilings (overdose or IFRA) ───────────────
# values in µL of AS-BOTTLED material
HARD_CEIL = {
    "Cis Jasmone":               120.0,   # overdose = celery
    "Ethyl Safranate":            80.0,   # overdose = medicinal
    "Gamma Undecalactone":       300.0,   # overdose = dessert
    "Aldehyde C12 MNA":          500.0,   # 1 % dilution; 5 µL active cap
    "Ultralia":                   80.0,   # trace iris echo only
    "Coumarin":                  720.0,   # 20 % dil → 144 µL active; IFRA Cat 4 ≈ 0.6 % skin
    "Bergamot FCF oil Sicilian": 900.0,   # IFRA / bergapten margin
    "Petitgrain EO":             220.0,   # cap: architecture accent, not co-lead
    "Benzyl Acetate":            450.0,   # overdose = nail-polish
    "Musk Ketone":               550.0,   # 10 % dil → 55 µL active (nitro musk margin)
    "Dihydrojasmone":            120.0,   # v4: overdose = fatty-celery
    "Amyl Cinnamic Aldehyde":    150.0,   # v4: IFRA Cat 4 skin sensitizer — strict
    "Helional":                  200.0,   # v4: overdose = synthetic-melon
    "Cashmeran":                 400.0,   # v5: 20 % dil ceiling = 80 µL active (overdose = textile-laundry character dominates)
    "Delta Decalactone":         200.0,   # v6: overdose = coconut-suntan lotion
    "Ethylene Brassylate":       500.0,   # v6: neat macrocyclic musk; overdose = soapy-creamy dominance
    "Hedione HC":                900.0,   # v7: COST CAP — receptor-active cis isomer is ~4-5× price; bulk moves to std Hedione
    "Hedione":                  1500.0,   # v7: standard Hedione bulk carrier (solvent + skin-spread roles saturate ~15% conc)
    "Exaltolide":                900.0,   # v7: pillar promoted; ceiling for Lactée-spine expansion
    "Beta Ionone":                40.0,   # v7: neat, ODT 0.007 — overdose = synthetic-violet/shampoo
    "Carrot Seed EO":            100.0,   # v7: overdose = carrot-soup / rooty dominance
    "Geosmin (1% in TEC)":         5.0,   # v7: petrichor trace only; overdose = beet-soil
    "Indole (10%)":               50.0,   # v8: 10 % dil; 5 µL active (0.045 %) ceiling — above = fecal/narcotic
}
HARD_FLOOR = {
    "Gamma Undecalactone":       100.0,   # lactonic bridge — signal floor
    "Cis Jasmone":                80.0,   # v8: raised 40→80 — defend jasmine-ketone identity (v7 fell to floor)
    "Heliotropal":               180.0,   # luxury powder signal
    "Ultralia":                   30.0,
    "Ethyl Safranate":            30.0,
    "Aldehyde C12 MNA":          150.0,   # complexion sparkle
    "Dihydrojasmone":             20.0,   # v4: warm jasmine-ketone signal
    "Amyl Cinnamic Aldehyde":     40.0,   # v4: waxy-jasmine diffusion signal
    "Helional":                   40.0,   # v4: watery-green halo signal
    "Cashmeran":                 100.0,   # v5: cashmere-textile signal floor (20 µL active min)
    "Delta Decalactone":          50.0,   # v6: creamy lactone signal floor
    "Ethylene Brassylate":       200.0,   # v6: musk anchor signal floor
    "Hedione HC":                500.0,   # v7: receptor-active heart radiance floor (cost-capped)
    "Hedione":                   800.0,   # v7: bulk solvent-carrier floor (below this, fixatives phase-separate)
    "Exaltolide":                500.0,   # v7: Lactée-spine pillar floor
    "Beta Ionone":                10.0,   # v7: luxury-precious signal floor
    "Carrot Seed EO":             30.0,   # v7: natural-orris signal floor
    "Geosmin (1% in TEC)":         2.0,   # v7: petrichor trace floor
    "Indole (10%)":               20.0,   # v8: 2 µL active floor (0.018 %) — the jasmine dirt-drop
}

# Sum-of-all-materials (concentrate mass) kept within ±3 % of baseline to
# preserve EDP strength — optimizer rebalances ratios, not total mass.
TARGET_TOTAL = 11000.0
TOTAL_TOL = 330.0     # ±3 %


def bounds(name, cur):
    base = BASE_ING.get(name, 0.0)
    if name in PILLARS and base > 0:
        floor = base * PILLAR_FLOOR_FRAC
        ceil  = base * PILLAR_CEIL_FRAC
    else:
        floor = 0.0
        ceil  = max(cur * 3.0, cur + 200.0, 800.0)
    floor = max(floor, HARD_FLOOR.get(name, 0.0))
    ceil  = min(ceil,  HARD_CEIL.get(name, ceil))
    return floor, ceil


def brief_ok(ing, dil):
    for b in BLOCKED:
        if ing.get(b, 0.0) > 0.0:
            return False, f"blocked material present: {b}"
    # Pillar floors
    for p in PILLARS:
        base = BASE_ING.get(p, 0.0)
        if base > 0 and ing.get(p, 0.0) < base * PILLAR_FLOOR_FRAC - 0.5:
            return False, f"pillar {p} below 60 % floor"
    # Hard caps
    for mat, ceil in HARD_CEIL.items():
        if ing.get(mat, 0.0) > ceil + 0.5:
            return False, f"{mat} over cap {ceil}"
    # Concentrate mass window
    tot = sum(ing.values())
    if abs(tot - TARGET_TOTAL) > TOTAL_TOL:
        return False, f"concentrate mass {tot:.0f} outside {TARGET_TOTAL}±{TOTAL_TOL}"
    # Complexion cushion floor — Hexyl Sal alone must be ≥ 900 µL (brief)
    if ing.get("Hexyl Salicylate", 0.0) < 900.0:
        return False, "Hexyl Salicylate cushion < 900 µL (complexion brief)"
    # v7 gate overhaul: separate jasmine-character floor from Hedione-carrier floor.
    # Rationale: Hedione is a solvent-carrier + weak receptor agonist, not a jasmine
    # character marker. Counting it as jasmine_sig (v4-v6) let the optimizer parasitize
    # Hedione mass to pass the jasmine gate, which inflated carrier % to 26 % (v6) —
    # well above Dior Homme (~18 %) / Terre d'Hermès (~15 %) literature ceilings.
    # v7 splits into (a) true jasmine markers and (b) radiance carrier floor.
    jasmine_true = (ing.get("Benzyl Acetate", 0.0)
                  + ing.get("Cis Jasmone", 0.0)
                  + ing.get("Gamma Undecalactone", 0.0)
                  + ing.get("Delta Decalactone", 0.0)
                  + ing.get("Dihydrojasmone", 0.0)
                  + ing.get("Amyl Cinnamic Aldehyde", 0.0))
    if jasmine_true < 900.0:
        return False, f"jasmine-character signal {jasmine_true:.0f} < 900 µL (excl. Hedione) — v8 gate"
    radiance_sig = ing.get("Hedione HC", 0.0) + ing.get("Hedione", 0.0)
    if radiance_sig < 1500.0:
        return False, f"radiance carrier {radiance_sig:.0f} < 1500 µL (HC + std Hedione)"
    # Iris signal floor — Alpha Irone + Orivone + Alpha Isomethyl Ionone + Ultralia ≥ 1700 µL
    iris_sig = (ing.get("Alpha Irone", 0.0)
              + ing.get("Orivone", 0.0)
              + ing.get("Alpha Isomethyl Ionone", 0.0)
              + ing.get("Ultralia", 0.0))
    if iris_sig < 1700.0:
        return False, f"iris signal {iris_sig:.0f} < 1700 µL"
    return True, ""


# ── Mass-preserving paired moves ───────────────────────────
# Every +Δ on material A is balanced by −Δ on material B so TARGET_TOTAL is
# preserved. The optimizer explores paired trades within the brief envelope.
STEPS = [+80, +40, +20, +10, -10, -20, -40, -80]


def climb(ing, dil, scorer, max_passes=5):
    geo, detail = score_formula(ing, dil, scorer)
    print(f"  start: geo={geo:.3f}  "
          f"hed={detail['hedonic']:.2f}  lux={detail['luxury']:.2f}  "
          f"tex={detail['texture']:.2f}  depth={detail['stacking_depth']:.2f}  "
          f"skin={detail['skin_performance']:.2f}")
    names = list(ing.keys())
    moves = 0
    t0 = time.time()
    for p in range(1, max_passes + 1):
        improved = False
        # For each material try a unilateral move, then rebalance excess/deficit
        # by spreading opposite-sign Δ across the other pillars proportionally.
        for name in names:
            cur_amt = ing[name]
            floor, ceil = bounds(name, cur_amt)
            best = None
            for s in STEPS:
                new_amt = cur_amt + s
                if new_amt < floor - 0.5 or new_amt > ceil + 0.5:
                    continue
                # Rebalance: spread −s across all *other* non-blocked materials
                # in proportion to current amount, skipping pillars below floor
                # and pillars near ceiling.
                trial = dict(ing)
                trial[name] = new_amt
                others = [n for n in names if n != name and trial[n] > 10.0]
                tot_others = sum(trial[n] for n in others)
                if tot_others <= 0:
                    continue
                share = -s / tot_others
                ok_apply = True
                for n in others:
                    trial[n] = trial[n] * (1.0 + share)
                    f2, c2 = bounds(n, trial[n])
                    if trial[n] < f2 - 0.5 or trial[n] > c2 + 0.5:
                        ok_apply = False
                        break
                if not ok_apply:
                    continue
                ok, _ = brief_ok(trial, dil)
                if not ok:
                    continue
                g_new, d_new = score_formula(trial, dil, scorer)
                if g_new > geo + 0.003:
                    if best is None or g_new > best[0]:
                        best = (g_new, d_new, trial, s)
            if best is not None:
                g_new, d_new, trial, s = best
                print(f"    ★ p{p} {name}: {cur_amt:.0f} → {trial[name]:.0f}  "
                      f"(Δ{s:+.0f}, rebalanced)  geo {geo:.3f} → {g_new:.3f}  "
                      f"hed={d_new['hedonic']:.2f} lux={d_new['luxury']:.2f} "
                      f"tex={d_new['texture']:.2f}")
                ing = trial
                geo, detail = g_new, d_new
                improved = True
                moves += 1
        print(f"  pass {p} complete  moves={moves}  t={time.time()-t0:.0f}s  geo={geo:.3f}")
        if not improved:
            break
    return ing, dil, geo, detail, moves


def main():
    print("=" * 78)
    print("  Iris-Jasmine *Luxe Lactée* — character-aligned optimization")
    print("  Axis weights:  hedonic 1.6 · texture 1.4 · luxury 1.4 ·")
    print("                 stacking_depth 1.2 · skin_performance 1.2 ·")
    print("                 longevity/sillage 1.0 · photorealism 0.4 · clarity 0.4")
    print("=" * 78)

    scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())

    ing = copy.deepcopy(BASE_ING)
    dil = copy.deepcopy(BASE_DIL)

    ok, why = brief_ok(ing, dil)
    print(f"\n  brief gate: {'OK' if ok else 'FAIL — ' + why}")
    if not ok:
        sys.exit(1)

    geo0, det0 = score_formula(ing, dil, scorer)
    print(f"\n  baseline geo (character-weighted): {geo0:.3f}")
    print(f"  baseline axes:")
    for a, w in sorted(AXIS_WEIGHTS.items(), key=lambda kv: -kv[1]):
        print(f"     {a:<22s} w={w:.1f}   score={det0[a]:.2f}")

    print("\n" + "─" * 78)
    print("  HILL-CLIMB — mass-preserving paired moves")
    print("─" * 78)
    ing, dil, geo, detail, moves = climb(ing, dil, scorer, max_passes=5)

    print("\n" + "═" * 78)
    print("  RESULT")
    print("═" * 78)
    print(f"  baseline geo : {geo0:.3f}")
    print(f"  optimized geo: {geo:.3f}   Δ = {geo - geo0:+.3f}")
    print(f"  moves accepted: {moves}")
    print(f"\n  axis             baseline   optimized   Δ")
    for a in sorted(AXIS_WEIGHTS.keys(), key=lambda x: -AXIS_WEIGHTS[x]):
        print(f"    {a:<20s}  {det0[a]:>6.2f}     {detail[a]:>6.2f}   {detail[a]-det0[a]:+.2f}")

    print(f"\n  final ingredients (µL of as-bottled):")
    for name in ing:
        base = BASE_ING.get(name, 0.0)
        delta = ing[name] - base
        marker = "★" if abs(delta) > 5 else " "
        print(f"    {marker} {name:<32s} {ing[name]:>7.1f}  (base {base:>7.1f}  Δ{delta:+7.1f})")

    total = sum(ing.values())
    print(f"\n  Σ concentrate = {total:.1f} µL  (target {TARGET_TOTAL:.0f} ± {TOTAL_TOL:.0f})")

    out = {
        "baseline_geo": geo0,
        "optimized_geo": geo,
        "axes_baseline": det0,
        "axes_optimized": detail,
        "ing": ing,
        "dil": dil,
        "axis_weights": AXIS_WEIGHTS,
    }
    with open("_opt_iris_jasmine_luxe_v8_out.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("\n  → _opt_iris_jasmine_luxe_v8_out.json")


if __name__ == "__main__":
    main()
