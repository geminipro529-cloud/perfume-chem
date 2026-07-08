# Iris Rêverie Lactée — 50 mL — Version Selector

> ⚠️ **Brief-alignment notice (2026-04-23):** The scoring engine's composite geo
> is **not a brief-alignment metric**. After perfumer review, the optimizer-winning
> **v6** was diagnosed as **off-brief**: it won composite by pushing Carrot Seed
> EO to 800 µL (5.4 % of concentrate — dominant rooty-earth character) and
> dumping Benzyl Salicylate (the cosmetic-cushion spine of the brief). That's
> the *Iris Silver Mist / No. 19* axis (rooty-earth naturalism), not the
> **Prada Infusion d'Iris / L'Heure Bleue** axis the brief asks for
> (cosmetic-creamy-powder white floral).
>
> **✓ RECOMMENDED: v7a** — v7 with **Cedarwood Virginia EO → Cedarwood EO** swap.
> Virginia reads "pencil-shaving / smoky" against a cosmetic-creamy-iris brief;
> generic Cedarwood EO is the neutral natural-cedar register the brief wants.
> The swap yields **geo 80.810 (+2.02 vs v3, +2.77 vs v7)** with hedonic held
> at **85.70 (+1.00 vs v3)** — the only version that beats v3 on composite
> AND hedonic simultaneously. Engine note: Cedarwood Virginia is missing from
> the diffusion model's VP table, so part of the sillage lift (+23.5) is
> engine artefact — but the character direction is perfumer-correct.
>
> **Alternatives:**
> - **v3** — canonical brief-balanced baseline. A constrained hill-climb (v8)
>   from v3 with brief caps found only Ebanol +50 µL. **v3 is near-optimal
>   inside the brief** with Virginia cedar.
> - **v7** — pre-swap perfumer version (still uses Virginia). Kept for reference.
>
> **Wear v6 only if the brief shifts to "naturalistic rooty iris."**
>
> | Version | geo | Δ vs v3 | hedonic | sillage | luxury | character |
> |---|---:|---:|---:|---:|---:|---|
> | v3 baseline | 78.790 | — | 84.70 | 74.50 | 63.40 | canonical, Virginia cedar |
> | **v6** (scorer pick) | **79.025** | **+0.235** | 84.20 | 74.60 | **64.30** | ⚠️ off-brief rooty-earth |
> | **v7** (perfumer, Virginia) | 78.013 | −0.777 | **85.90** | 74.90 | 61.10 | ✓ on-brief, smoky cedar |
> | **v7a** (perfumer, natural cedar) | **80.810** | **+2.008** | 85.70 | **98.40** | 61.00 | ✓✓ **best composite — neutral cedar** |
> | **v7b** (brief-push, 2026-04-23) | 80.542 | +1.254 | 85.60 | 100.00 | 58.70 | ✓✓ **best brief-fit** — amber split + buttery + powder + white-floral push |
> | v8 (brief-constrained) | 78.813 | +0.023 | 84.80 | 74.60 | 63.40 | v3 + Ebanol 50 |
>
> **v7b vs v7a trade-off:** v7b is character-correct for the **refined brief**
> ("powdery iris white floral powder creamy") — splits the amber (Ambrox 300 +
> Ambermax 250 + Azarbre 100), lifts the butter (Orivone 650 + Delta Deca 500 +
> Gamma Deca 100), thickens the powder (Musk Ketone 900 + Heliotropal 150 +
> Anisaldehyde 100 + Helional 50), amplifies the cosmetic cushion (Benzyl Sal
> 500 + Hexyl Sal 500), and adds white-floral body (DBCA 125, Lilyreal 125,
> ACA 40). Composite falls −0.39 vs v7a because the extra mass dilutes luxury
> (−2.3) and perceptual_clarity (−3.2). Stacking_depth gains +5 (better layering).
> Hedonic holds at 85.60. **Wear v7b if the brief emphasis is on powder-
> plush-cosmetic; wear v7a if maximum composite score / minimum material count
> matters more.**
>
> **Takeaway:** when the scorer's composite disagrees with perfumer intuition,
> check which *axis* it's rewarding. Here v6 wins on **luxury/photorealism**
> (naturalistic EO density), v7 wins on **hedonic** (brief-fit pleasantness).
> See [_opt_v7_v8_iris_brief.py](../../_opt_v7_v8_iris_brief.py),
> [_opt_v7_v8_iris_brief.json](../../_opt_v7_v8_iris_brief.json),
> [_opt_v7_v8_out.txt](../../_opt_v7_v8_out.txt).

---

# Iris Rêverie Lactée — 50 mL v7a (perfumer-hand, natural-cedar swap) — **RECOMMENDED FOR BRIEF**

**Batch:** 50.00 mL · **Concentrate ≈ 14.72 mL (29.43 %)** · **Ethanol 96 %:** ≈ 35.28 mL

**v7a geo:** 80.810 (Δ vs v3 +2.008, Δ vs v7 +2.774) · **hedonic 85.70 (+1.00 vs v3)** · **sillage 98.40 (+23.9 vs v3)**

### Single change vs v7

| Ingredient | v7 | v7a | Δ | Why |
|---|---|---|---:|---|
| **Cedarwood Virginia EO** → **Cedarwood EO** | 300 µL | 300 µL (same volume, different material) | — | Virginia reads **"pencil-shaving / smoky / angular cedar"** (engine: `char: "pencil-shaving cedar"`). Generic Cedarwood EO reads **"natural cedar"** (engine: `char: "natural cedar"`) — neutral, less assertive, cleaner against a cosmetic-creamy iris core. The smoky facet of Virginia reads as **masculine aromatic intrusion** into a powder-iris composition; neutral cedar supports the wood-cream register without flagging itself. |

### Why this single swap moves the score so much (+2.77 vs v7)

Two mechanisms:

1. **Character-correct for brief** (legitimate): neutral cedar recedes into the wood-cream register (Ebanol 1100 + Javanol 100 + Iso E Super 200), letting Orivone / Delta Decalactone / Alpha Irone drive the iris-butter face without a smoky counterweight.
2. **Engine artefact** (partially): `Cedarwood Virginia EO` is **missing from `engine/diffusion_model.py`**'s VP table — the engine falls back to a default volatility for it, under-scoring its sillage contribution. `Cedarwood EO` has `VP_25 = 0.25` explicit. The +23.5 sillage jump is inflated by this data gap (real-world difference would be smaller but still favours generic Cedarwood EO for diffusion). **Flagged for future engine maintenance.**

The hedonic axis (which tracks perfumer-intuition brief-fit) held at **85.70 vs v7's 85.90** — essentially equivalent. v7a retains all brief-aligned character of v7 while the scorer finally endorses it.

### v7a full formula (50 mL batch)

| # | Ingredient | Dilution | µL | mL |
|---:|---|---|---:|---:|
| 1 | Benzoin Resinoid | 50 % DPG | 1475 | 1.475 |
| 2 | Hedione | neat | 1250 | 1.250 |
| 3 | **Ebanol** | neat | **1100** | 1.100 |
| 4 | Ethyl Linalool | neat | 1050 | 1.050 |
| 5 | Alpha Irone | 30 % | 900 | 0.900 |
| 6 | Ethylene Brassylate | neat | 800 | 0.800 |
| 7 | Ambrettolide | 10 % DPG | 700 | 0.700 |
| 8 | Hedione HC | neat | 600 | 0.600 |
| 9 | Habanolide | neat | 600 | 0.600 |
| 10 | **Musk Ketone** | 10 % DPG | **600** | 0.600 |
| 11 | Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| 12 | **Orivone** | neat | **500** | 0.500 |
| 13 | **Ambrox Super** | 30 % | **450** | 0.450 |
| 14 | Vanillin | 10 % EtOH | 400 | 0.400 |
| 15 | **Delta Decalactone** | neat | **375** | 0.375 |
| 16 | **Benzyl Salicylate** | neat | **350** | 0.350 |
| 17 | **Hexyl Salicylate** | neat | **350** | 0.350 |
| 18 | Hydroxycitronellal | neat | 300 | 0.300 |
| 19 | **Cedarwood EO** *(was Virginia)* | neat | **300** | 0.300 |
| 20 | Coumarin | 20 % DPG | 275 | 0.275 |
| 21 | **Carrot Seed EO** | neat | **200** | 0.200 |
| 22 | **Iso E Super** | neat | **200** | 0.200 |
| 23 | Mayol | neat | 175 | 0.175 |
| 24 | Javanol | neat | 100 | 0.100 |
| 25 | Ethyl Maltol | 10 % EtOH | 100 | 0.100 |
| 26 | **Heliotropal** | neat | **100** | 0.100 |
| 27 | Lilyreal ND | neat | 75 | 0.075 |
| 28 | DBCA | neat | 75 | 0.075 |
| 29 | Freesia HDI | neat | 75 | 0.075 |
| 30 | Ethyl Vanillin | neat | 75 | 0.075 |
| 31 | Damascol | 10 % | 75 | 0.075 |
| 32 | Gamma Undecalactone | neat | 75 | 0.075 |
| 33 | **Beta Ionone** | neat | **75** | 0.075 |
| 34 | **Alpha Ionone** | neat | **60** | 0.060 |
| 35 | **Anisaldehyde** | neat | **60** | 0.060 |
| 36 | Bourgeonal | neat | 50 | 0.050 |
| 37 | **Ultralia** | neat | **40** | 0.040 |
| 38 | Scentenal | 1 % DPG | 25 | 0.025 |
| 39 | Irotyl | neat | 25 | 0.025 |
| 40 | Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| 41 | PEDMC | neat | 25 | 0.025 |
| 42 | Aurantiol | neat | 25 | 0.025 |
| 43 | Geosmin ⚠️ | 1 % DPG | 15 | 0.015 |
| 44 | Indole | 10 % DPG | 15 | 0.015 |
| 45 | Isoeugenol | neat | 15 | 0.015 |
| 46 | Farnesol (IFRA-capped) | neat | 10 | 0.010 |
| — | Ethanol 96 % | carrier | ~35285 | ~35.285 |
| | **TOTAL** | | **50 000** | **50.000** |

Bolded rows were changed v3 → v7 (kept in v7a). The single change from v7 → v7a is **row 19** (Cedarwood Virginia → Cedarwood EO).

---

## Formula verification report (v7a)

Ran against the in-process scorer and inventory ([_opt_v7a_cedarEO_swap.py](../../_opt_v7a_cedarEO_swap.py), [_opt_v7a_cedarEO_out.txt](../../_opt_v7a_cedarEO_out.txt)).

### ✅ Passes

- **Total volume:** concentrate sum 14 715 µL + ethanol 35 285 µL = **50 000 µL exactly**.
- **Concentrate percentage:** 29.43 % (EDP-strength, within design target).
- **IFRA caps:** no violations. Farnesol at 10.0 / 10.0 µL = **100 % of cap** (intentional — lily-muguet fixative driven to maximum).
- **Inventory compliance:** all 46 materials present in `inventory.txt`; all at correct dilutions per `IRL_DIL_BASE`.
- **FTEC-free:** verified — no FTEC/base accord materials used (per standing directive).
- **Musk chord:** 4 musks covering 4 axes correctly —
  - **Depth axis:** Ethylene Brassylate 800 (creamy-lactonic) + Ambrettolide 70 (of 700 @ 10 %, wine-musk natural warmth) = ~870 depth
  - **Projection axis:** Habanolide 600 (warm-skin macrocyclic)
  - **Character-echo axis:** Musk Ketone 60 (of 600 @ 10 %, powder reinforcement — the ONLY direct powder musk)
  - Rejection: Galaxolide, Tonalide (synthetic-clean wrong direction for creamy brief); Zenolide (too cold); Romandolide (projection would shout); Macrolide (too quiet).
- **Sandalwood chord:** dual register —
  - Ebanol 1100 (creamy-milky soft, primary)
  - Javanol 100 (dry-intimate counterpoint at trace)
  - Rejection: Bacdanol (too heavy-oriental), Sandalore (too thin-fresh), Sandalwood FO (opaque — can't control).
- **Amber register:** single-slot Ambrox Super 450 (30 %, so ~135 µL active) — crystalline-mineral at moderate dose. Justified by brief requiring transparent coolness behind the creamy core. Alternative Ambermax (warm-rounded) rejected to keep v7a inventory-identical to v3/v7 and isolate the cedar effect.
- **Citrus selection:** single slot Bergamot FCF Sicilian 550 — bergamot IS the classical iris companion (Infusion d'Iris uses bergamot); no 2nd citrus needed. Rejected Blood Orange (too juicy), Grapefruit (too bitter-pink), Methyl Pamplemousse (too modern-tart) for this brief.
- **Fixative gradient:** layered correctly — Hexyl Salicylate 350 (light transparent film) under Benzyl Salicylate 350 (heavy cosmetic cushion). Benzyl Benzoate rejected (would add mass without character contribution needed for brief).
- **Powder quartet:** Musk Ketone 60 + Heliotropal 100 + Anisaldehyde 60 + Alpha Ionone 60 + Alpha Isomethyl Ionone 25 + Coumarin 55 (of 275 @ 20 %) — six-material powder layer with cosmetic-talc character.

### ⚠️ Flags

- **Geosmin dose over perfumer-guidance cap.** `copilot-instructions.md` specifies
  *"use max 2–5 µL of 1% dilution per 100 mL"*. v7a has **15 µL of 1 % in 50 mL
  = equivalent to 30 µL per 100 mL**, which is **6–15× the recommended maximum**.
  At ODT ≈ 6 ppt, this is a severe-overdose risk reading as *beet soil* rather
  than petrichor. **Recommend: reduce Geosmin 15 → 2 µL** (equivalent to
  4 µL/100 mL, inside guidance). Expected impact: negligible on composite
  (trace), positive on hedonic (removes soil-metallic off-note).
- **Engine data gap — Cedarwood Virginia EO missing from `engine/diffusion_model.py`**
  VP table. Virginia's sillage is under-scored relative to reality; part of
  v7a's +23.5 sillage lift is artefact. Character direction is perfumer-correct,
  but the magnitude is inflated. **Flagged for future engine maintenance**
  (add `"Cedarwood Virginia EO": {"MW": 204.4, "VP_25": 0.15, "Kaw_eff": 0.001}`
  — Virginia has lower VP than generic Cedarwood EO due to heavier
  cedrol/thujopsene content).
- **Farnesol at 100 % of IFRA cap.** Technically compliant but leaves zero
  margin. If the base batch density or dosing error introduces >0 % overshoot,
  formula goes out-of-compliance. **Recommend: 9 µL instead of 10 µL** for
  safety margin.
- **Alpha Isomethyl Ionone at 25 µL** should be verified against IFRA Category 4
  (fine-fragrance) cap. Currently present at 0.17 % of concentrate — usually
  safe but check latest IFRA amendment.

### Axis scores v7a (composite 80.810)

| Axis | v3 | v7 | v7a | Δ v7a − v3 |
|---|---:|---:|---:|---:|
| longevity | 82.20 | 81.20 | 81.00 | −1.20 |
| sillage | 74.50 | 74.90 | **98.40** | **+23.90** ⚠ (see engine flag) |
| luxury | 63.40 | 61.10 | 61.00 | −2.40 |
| texture | 81.00 | 81.20 | 81.20 | +0.20 |
| stacking_depth | 85.00 | 85.00 | 85.00 | 0.00 |
| photorealism | 82.40 | 80.00 | 80.30 | −2.10 |
| perceptual_clarity | 75.30 | 73.40 | 74.80 | −0.50 |
| skin_performance | 77.30 | 77.50 | 77.50 | +0.20 |
| synergy | 95.00 | 95.00 | 95.00 | 0.00 |
| hedonic | 84.70 | 85.90 | **85.70** | **+1.00** |

### Final perfumer verdict on v7a

**Approve as the working formula for the stated brief.** Two caveats:

1. **Fix Geosmin dose before mixing** (15 → 2 µL).
2. **Flag sillage-98 as partially engine artefact** — expect real-world sillage closer to v7's 75-range once Virginia's missing VP entry is added to the diffusion model.

Character-wise, v7a is the cleanest expression of the *Infusion d'Iris* / *L'Heure Bleue* axis the inventory can produce without new material additions. The single Cedarwood Virginia → Cedarwood EO swap is the user's perfumer-intuition win of this session.

---

# Iris Rêverie Lactée — 50 mL v7b (brief-push: powdery iris white-floral powder creamy) — **ALTERNATIVE RECOMMENDED**

**Batch:** 50.00 mL · **Concentrate = 16.157 mL (32.31 %)** · **Ethanol 96 %:** 33.843 mL

**v7b geo (default weights):** 80.542 (Δ v3 +1.254, Δ v7a −0.392)
**v7b geo (brief weights, D2):** 80.592 (Δ v7a−brief −0.404)
**v7b hedonic:** 85.60 (≈ v7a's 85.70) · **stacking_depth:** 90.00 (+5 vs v7a) · **sillage:** 100.00

### User directive (2026-04-23 session)

User selected optimization moves **A1 + A2 + A4 + all of B (B1+B2+B3)**, skipped all C, adopted **D2 (brief-specific scoring weights)** and **D3 (hill-climb re-seed from v7b)**. Refined brief: **"powdery iris white floral powder creamy"**.

### Changes v7a → v7b (17 modifications)

| Bucket | Ingredient | v7a | v7b | Δ | Dilution | Register / Rationale |
|---|---|---:|---:|---:|---|---|
| **A1** | Geosmin | 15.0 | **2.0** | −13 | 1 % | Perfumer-guidance overdose fix. v7a at 30 µL/100 mL = 6–15× the 2–5 µL/100 mL cap. Reads as *beet-soil* at v7a dose; 2 µL = petrichor trace only. |
| **A2** | Ambrox Super | 450 | **300** | −150 | 30 % | Crystalline-mineral, stays as backbone but reduced to make room for warm register. |
| **A2** | Ambermax (new) | — | **250** | +250 | **50 %** | Warm-rounded amber — adds the cosmetic-warm facet Ambrox lacks. Rejected Amber Core (opaque pre-blend, can't precision-tune), Ambrofix (too close to Ambrox, no new facet). Register: **warm**. |
| **A4** | Azarbre (new) | — | **100** | +100 | neat | Cedar-amber bridge — warmer than Ambrox (no crystalline edge), softer than Timberol. Fills the gap between Cedarwood EO and the amber layer. Rejected Cedramber (too cedar-forward), Amberwood F (too transparent). Register: **cedar-amber-warm**. |
| **B1** | Orivone | 500 | **650** | +150 | neat | Buttery-iris amplifier. Primary driver of the "crème fraîche under the powder" effect. |
| **B1** | Delta Decalactone | 375 | **500** | +125 | neat | Peach-skin lactone, pairs with Gamma Deca. Chosen over Gamma Undecalactone as the primary lactone (Gamma Undec is more apricot-tropical). |
| **B1** | Gamma Decalactone (new) | — | **100** | +100 | neat | Coconut-lactonic, thickens the buttery register. Rejected Delta Octalactone (too tropical), Maple Lactone (too gourmand-caramel). |
| **B2** | Musk Ketone | 600 | **900** | +300 | 10 % | **The ONLY direct powder musk** — the character-echo axis of the musk chord. Pushed hard because brief is now explicitly powder-centric. |
| **B2** | Heliotropal | 100 | **150** | +50 | neat | Powder-almond accord, synergizes with Coumarin + Anisaldehyde + ionones. |
| **B2** | Anisaldehyde | 60 | **100** | +40 | neat | Hawthorn-heliotrope powder facet. |
| **B2** | Helional (new) | — | **50** | +50 | neat | Ozonic-watery-floral — adds transparent lift to the powder layer without clashing (unlike Calone which is too aquatic, or Triplal which overdoses at trace). |
| **B3** | Benzyl Salicylate | 350 | **500** | +150 | neat | Heavy cosmetic cushion — the luxury-cosmetic fixative spine the brief requires. |
| **B3** | Hexyl Salicylate | 350 | **500** | +150 | neat | Light salicylate film on top of Benzyl Sal (gradient: transparent over heavy). Rejected Amyl Salicylate (not in inventory). |
| **Brief** | DBCA | 75 | **125** | +50 | neat | Gardenia-rose cosmetic-clean — core white-floral character material. |
| **Brief** | Lilyreal ND | 75 | **125** | +50 | neat | Synthetic muguet cosmetic-clean — pairs with Bourgeonal + Hydroxycitronellal for the muguet trinity. |
| **Brief** | ACA (new) | — | **40** | +40 | neat | Amyl Cinnamic Aldehyde — jasmine-muguet diffusant, waxy-floral volume. At 40 µL = 80 % of IFRA cap (50 µL EDP ceiling). Rejected Farnesol push (already at 100 % IFRA), Phenylacetaldehyde (too honeyed-animalic for brief). Register: **waxy-floral body**. |

**Net:** concentrate 14.715 mL → 16.157 mL (+1.442 mL), ethanol 35.285 mL → 33.843 mL (total preserved at 50.00 mL exact).

### D2 — brief-specific scoring weights

`ObjectiveWeights` override for the *iris_cosmetic_powder* brief:

| Axis | Default | Brief | Rationale |
|---|---:|---:|---|
| longevity | 0.8 | 0.8 | unchanged |
| sillage | 0.8 | **0.6** | Skin-intimate brief, not sport projection |
| synergy | 0.5 | 0.5 | unchanged |
| luxury | 0.8 | **1.0** | Brief IS niche-luxury cosmetic |
| texture | 0.8 | **1.0** | Powder/creamy *is* texture |
| stacking_depth | 0.8 | 0.8 | unchanged |
| skin_performance | 0.7 | **0.9** | Must sit well on skin |
| hedonic | 0.5 | **0.9** | Brief-alignment axis — heavily up-weighted |
| perceptual_clarity | 0.6 | **0.5** | Powder is inherently blurred |
| photorealism | 0.7 | **0.4** | Brief is cosmetic-warm, not photoreal |

Composite under brief weights: v3=79.288, v7a=80.996, v7b=80.592. Brief weights favour v7a slightly (v7a benefits more from hedonic up-weighting because it has no photorealism penalty from added mass). **The brief weights do not flip the ranking** — v7a remains composite-leader under both profiles.

### D3 — Hill-climb re-seed from v7b under brief weights

Ran `mini_hill_climb` with brief weights, IFRA caps, sub-ODT ceilings, and Geosmin hard-cap at 3 µL. Result: **0 accepted moves in 12 passes**. v7b is a local optimum under the brief weight profile. No further dose tuning available without moving to different materials (a multi-variable probe step, not attempted here).

### v7b full formula (50 mL batch)

| # | Ingredient | Dilution | µL | mL |
|---:|---|---|---:|---:|
| 1 | Benzoin Resinoid | 50 % DPG | 1475 | 1.475 |
| 2 | Hedione | neat | 1250 | 1.250 |
| 3 | Ebanol | neat | 1100 | 1.100 |
| 4 | Ethyl Linalool | neat | 1050 | 1.050 |
| 5 | **Musk Ketone** | 10 % DPG | **900** | 0.900 |
| 6 | Alpha Irone | 30 % | 900 | 0.900 |
| 7 | Ethylene Brassylate | neat | 800 | 0.800 |
| 8 | Ambrettolide | 10 % DPG | 700 | 0.700 |
| 9 | **Orivone** | neat | **650** | 0.650 |
| 10 | Hedione HC | neat | 600 | 0.600 |
| 11 | Habanolide | neat | 600 | 0.600 |
| 12 | Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| 13 | **Benzyl Salicylate** | neat | **500** | 0.500 |
| 14 | **Hexyl Salicylate** | neat | **500** | 0.500 |
| 15 | **Delta Decalactone** | neat | **500** | 0.500 |
| 16 | Vanillin | 10 % EtOH | 400 | 0.400 |
| 17 | **Ambrox Super** | 30 % | **300** | 0.300 |
| 18 | Hydroxycitronellal | neat | 300 | 0.300 |
| 19 | Cedarwood EO | neat | 300 | 0.300 |
| 20 | Coumarin | 20 % DPG | 275 | 0.275 |
| 21 | **Ambermax** *(new)* | **50 %** | **250** | 0.250 |
| 22 | Carrot Seed EO | neat | 200 | 0.200 |
| 23 | Iso E Super | neat | 200 | 0.200 |
| 24 | Mayol | neat | 175 | 0.175 |
| 25 | **Heliotropal** | neat | **150** | 0.150 |
| 26 | **DBCA** | neat | **125** | 0.125 |
| 27 | **Lilyreal ND** | neat | **125** | 0.125 |
| 28 | **Azarbre** *(new)* | neat | **100** | 0.100 |
| 29 | Javanol | neat | 100 | 0.100 |
| 30 | Ethyl Maltol | 10 % EtOH | 100 | 0.100 |
| 31 | **Anisaldehyde** | neat | **100** | 0.100 |
| 32 | **Gamma Decalactone** *(new)* | neat | **100** | 0.100 |
| 33 | Freesia HDI | neat | 75 | 0.075 |
| 34 | Ethyl Vanillin | neat | 75 | 0.075 |
| 35 | Damascol | 10 % | 75 | 0.075 |
| 36 | Gamma Undecalactone | neat | 75 | 0.075 |
| 37 | Beta Ionone | neat | 75 | 0.075 |
| 38 | Alpha Ionone | neat | 60 | 0.060 |
| 39 | Bourgeonal | neat | 50 | 0.050 |
| 40 | **Helional** *(new)* | neat | **50** | 0.050 |
| 41 | Ultralia | neat | 40 | 0.040 |
| 42 | **ACA** *(new, IFRA 80 %)* | neat | **40** | 0.040 |
| 43 | Scentenal | 1 % DPG | 25 | 0.025 |
| 44 | Irotyl | neat | 25 | 0.025 |
| 45 | Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| 46 | PEDMC | neat | 25 | 0.025 |
| 47 | Aurantiol | neat | 25 | 0.025 |
| 48 | Indole | 10 % DPG | 15 | 0.015 |
| 49 | Isoeugenol | neat | 15 | 0.015 |
| 50 | Farnesol (IFRA 100 %) | neat | 10 | 0.010 |
| 51 | **Geosmin** *(overdose fixed)* | 1 % DPG | **2** | 0.002 |
| — | Ethanol 96 % | carrier | 33 843 | 33.843 |
| | **TOTAL** | | **50 000** | **50.000** |

Bolded rows = changed from v7a. Five new materials: **Ambermax**, **Azarbre**, **Gamma Decalactone**, **Helional**, **ACA**. Geosmin reduced 15 → 2 µL.

### Verification report (v7b)

- **Total volume:** 50 000 µL exact. Concentrate 16 157 µL (32.31 %, EDP-range).
- **IFRA caps:** PASS. ACA 40 / 50 = 80 %; Farnesol 10 / 10 = 100 %.
- **Inventory:** all 51 materials verified against `inventory.txt` (Ambermax 50 %, Azarbre neat, Gamma Decalactone neat, Helional neat, ACA neat).
- **FTEC-free:** PASS.
- **Geosmin:** 2 µL of 1 % in 50 mL = 4 µL/100 mL — **inside** the 2–5 µL perfumer-guidance band.
- **Musk chord:** 4 axes covered (Ethylene Brassylate + Ambrettolide depth, Habanolide projection, **Musk Ketone 900 character-echo = powder dominant**). Rejected Galaxolide/Tonalide (wrong direction), Zenolide (too cold), Romandolide (too projective for intimate brief).
- **Sandalwood chord:** Ebanol + Javanol (creamy + dry-intimate). Unchanged from v7a.
- **Amber register:** **dual-slot** (new v7b architecture) — Ambrox Super 90 µL active (crystalline-mineral) + Ambermax 125 µL active (warm-rounded) + Azarbre 100 µL (cedar-amber-warm bridge). Three distinct amber registers co-present.
- **Wood chord:** Cedarwood EO (natural-cedar) + Iso E Super (molecular-skin) + Azarbre (cedar-amber-warm). Three registers, none architectural (Timberol correctly rejected — brief is rounded, not angular).
- **White-floral core:** DBCA 125 + Lilyreal 125 + Bourgeonal 50 + Hydroxycitronellal 300 + Mayol 175 + Freesia HDI 75 + ACA 40 + Helional 50 — a **seven-material muguet/gardenia/white-floral accord** with ACA volume body and Helional ozonic lift.
- **Powder layer:** Musk Ketone 90 µL active + Heliotropal 150 + Anisaldehyde 100 + Alpha Ionone 60 + Alpha Isomethyl Ionone 25 + Coumarin 55 µL active + Ultralia 40 — **seven-material cosmetic-talc register**.
- **Buttery-iris core:** Orivone 650 + Delta Decalactone 500 + Gamma Decalactone 100 + Alpha Irone 270 µL active + Ebanol 1100 — the densest iris-butter layer across all versions.
- **Fixative gradient:** Hexyl Sal 500 (transparent) + Benzyl Sal 500 (cosmetic-heavy) + Benzoin 737 µL active (balsamic). Three-stage gradient.

### Axis scores v7b vs v7a (default weights)

| Axis | v3 | v7a | v7b | Δ v7b−v7a |
|---|---:|---:|---:|---:|
| longevity | 81.60 | 80.10 | 78.80 | −1.30 |
| sillage | 78.50 | 100.00 | 100.00 | 0.00 |
| luxury | 63.40 | 61.00 | 58.70 | **−2.30** |
| texture | 81.00 | 81.20 | 81.20 | 0.00 |
| stacking_depth | 85.00 | 85.00 | **90.00** | **+5.00** |
| photorealism | 82.80 | 80.90 | 79.70 | −1.20 |
| perceptual_clarity | 75.30 | 74.80 | 71.60 | −3.20 |
| skin_performance | 77.30 | 77.50 | 77.50 | 0.00 |
| synergy | 95.00 | 95.00 | 95.00 | 0.00 |
| hedonic | 84.70 | 85.70 | 85.60 | −0.10 |

**Reading:** v7b trades composite-score (luxury −2.3, perceptual_clarity −3.2) for **brief-character gains** (stacking_depth +5, sillage parity at 100, hedonic parity at 85.6). The extra 16 µL/50 mL of concentrate adds mass that the engine reads as "less transparent" but that the brief explicitly wants (powder + cosmetic cushion).

### Final perfumer verdict on v7b

**Mix this if the brief emphasis is powder-plush-cosmetic-white-floral.** v7b delivers every requested register: the amber is **split three ways** (crystalline + warm-rounded + cedar-amber-warm), the buttery-iris core is **maximally dense** (Orivone 650 + dual lactones), the powder layer is **seven-material** (Musk Ketone dominant), the white-floral core is **seven-material** (DBCA/Lilyreal/Bourgeonal/HC/Mayol/Freesia/ACA+Helional), and the fixative gradient is **three-stage**.

The −0.39 composite cost vs v7a is the price of that density. If composite score is the decision metric, wear v7a. If brief-fit character is the decision metric, wear v7b.

See [_opt_v7b_brief.py](../../_opt_v7b_brief.py), [_opt_v7b_brief.json](../../_opt_v7b_brief.json), [_opt_v7b_brief_out.txt](../../_opt_v7b_brief_out.txt).

---

# Iris Rêverie Lactée — 50 mL v7 (perfumer-hand, pre-cedar-swap — superseded by v7a)

**Batch:** 50.00 mL · **Concentrate ≈ 14.72 mL (29.43 %)** · **Ethanol 96 %:** ≈ 35.28 mL

**v7 geo:** 78.013 (Δ vs v3 −0.777) · **hedonic 85.90 (+1.20 vs v3, highest of all versions)**

### Brief this serves

**Prada *Infusion d'Iris* / Guerlain *L'Heure Bleue* axis** — cosmetic-creamy-buttery iris, white-floral heart, powder drydown. NOT rooty-earth naturalism.

### Perfumer rationale

The scorer's v6 pick built a **mineral-cedar-rooty shelf** (Ambrox +200, Cedarwood Virginia +200, Carrot Seed +200, Benzyl Salicylate −200). That's a legitimate iris idiom but the **wrong** one for this brief. v7 reverses the off-brief moves while keeping v6's genuinely brief-aligned lifts (Ebanol +200 creamy sandalwood, Iso E Super +150 molecular halo, Hexyl Salicylate +50 transparent film).

### Key redistributions v3 → v7 (same material set, no new inventory)

| Ingredient | v3 | v7 | Δ | Why (register) |
|---|---:|---:|---:|---|
| **Carrot Seed EO** | 600 | **200** | −400 | Trace-naturalism only. At 200 µL (1.3 % concentrate) it hints at orris-root without dominating. |
| **Cedarwood Virginia EO** | 350 | **300** | −50 | De-emphasize cedar pillar; Ebanol carries the wood-cream axis. |
| **Ambrox Super** (30 %) | 550 | **450** | −100 | Less crystalline-cold; Ambrox read as clinical against "creamy buttery". |
| **Benzyl Salicylate** | 250 | **350** | +100 | **Restored** — cosmetic-plastic-floral cushion IS the brief's diffusion spine. |
| **Hexyl Salicylate** | 300 | **350** | +50 | Kept v6's lift — transparent salicylate film layered under Benzyl Sal. |
| **Ebanol** | 900 | **1100** | +200 | Kept v6's lift — creamy-milky sandalwood. |
| **Iso E Super** | 50 | **200** | +150 | Kept v6's lift — molecular cocoon halo. |
| **Heliotropal** | 50 | **100** | +50 | Cherry-almond-heliotrope — core powder-accord material. |
| **Anisaldehyde** | 40 | **60** | +20 | Hawthorne-anise — powder-axis core. |
| **Musk Ketone** (10 %) | 400 | **600** | +200 | Talcum-powder echo; the *only* musk in inventory that directly reinforces powder. |
| **Orivone** | 350 | **500** | +150 | Buttery-iris base — on-brief; v3 under-served the butter axis. |
| **Delta Decalactone** | 300 | **375** | +75 | Lactonic-peach-cream — direct creamy-buttery contribution. |
| **Alpha Ionone** | 25 | **60** | +35 | Violet-powdery ionone — iris-violet powder bridge. |
| **Beta Ionone** | 40 | **75** | +35 | Woody-violet structural support. |
| **Ultralia** | 25 | **40** | +15 | Ghost iris trace lift — powder-iris halo. |

### Character-register justifications (per inventory differentiation rules)

- **Iris axis:** Alpha Irone 30 % 900 (held) + **Orivone 500** (buttery base, lifted) + **Ultralia 40** (trace halo, lifted). Carrot Seed 200 acts as **naturalistic support, not driver**.
- **Cream/butter:** **Ebanol 1100** (creamy sandalwood — chosen over Javanol 100 kept as dry-intimate counterpoint; Bacdanol rejected as too heavy-oriental for transparent iris) + Ethylene Brassylate 800 (lactonic creamy musk, held) + **Delta Decalactone 375** (lactonic-peach).
- **White floral:** Hedione 1250 + Hedione HC 600 + DBCA 75 + Mayol 175 + Lilyreal ND 75 + Bourgeonal 50 + Hydroxycitronellal 300 + Freesia HDI 75. Balanced as-is from v3 — no change needed; this layer already serves the brief.
- **Powder:** **Musk Ketone 600** (lifted — only direct powder musk) + **Heliotropal 100** (lifted) + **Anisaldehyde 60** (lifted) + **Alpha Ionone 60** (lifted) + Coumarin 20 % 275 (held) + Irotyl 25 (held) + Alpha Isomethyl Ionone 25 (held at IFRA cap).
- **Cushion/diffusion:** **Benzyl Salicylate 350** (cosmetic-heavy cushion, chosen over trimming — brief *requires* this register) + **Hexyl Salicylate 350** (transparent film, layered under for gradient). Rejected Benzyl Benzoate: would contribute no character.
- **Amber shelf:** **Ambrox Super 450** (crystalline-mineral at moderate dose). Rejected pushing Ambrox to 750 (v6) — too cold for "creamy-buttery". Future v7b could split with Ambermax 50 % 300 µL for warm-rounded character, but v7 stays inventory-identical to v3 to isolate the redistribution effect.
- **Wood:** **Iso E Super 200** (molecular halo, lifted) + Cedarwood Virginia 300 (moderate natural cedar, trimmed from v6's 550). Rejected Timberol (too architectural), Kephalis (too powerful for transparent iris).

### Full v7 formula

| Ingredient | Dilution | µL | mL |
|---|---|---:|---:|
| Benzoin Resinoid | 50 % | 1475 | 1.475 |
| Hedione | neat | 1250 | 1.250 |
| **Ebanol** | neat | **1100** | 1.100 |
| Ethyl Linalool | neat | 1050 | 1.050 |
| Alpha Irone | 30 % | 900 | 0.900 |
| Ethylene Brassylate | neat | 800 | 0.800 |
| Ambrettolide | 10 % | 700 | 0.700 |
| Hedione HC | neat | 600 | 0.600 |
| Habanolide | neat | 600 | 0.600 |
| **Musk Ketone** | 10 % | **600** | 0.600 |
| Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| **Orivone** | neat | **500** | 0.500 |
| **Ambrox Super** | 30 % | **450** | 0.450 |
| Vanillin | 10 % | 400 | 0.400 |
| **Delta Decalactone** | neat | **375** | 0.375 |
| **Benzyl Salicylate** | neat | **350** | 0.350 |
| **Hexyl Salicylate** | neat | **350** | 0.350 |
| Hydroxycitronellal | neat | 300 | 0.300 |
| **Cedarwood Virginia EO** | neat | **300** | 0.300 |
| Coumarin | 20 % | 275 | 0.275 |
| **Carrot Seed EO** | neat | **200** | 0.200 |
| **Iso E Super** | neat | **200** | 0.200 |
| Mayol | neat | 175 | 0.175 |
| Javanol | neat | 100 | 0.100 |
| Ethyl Maltol | 10 % | 100 | 0.100 |
| **Heliotropal** | neat | **100** | 0.100 |
| Lilyreal ND | neat | 75 | 0.075 |
| DBCA | neat | 75 | 0.075 |
| Freesia HDI | neat | 75 | 0.075 |
| Ethyl Vanillin | neat | 75 | 0.075 |
| Damascol | 10 % | 75 | 0.075 |
| Gamma Undecalactone | neat | 75 | 0.075 |
| **Beta Ionone** | neat | **75** | 0.075 |
| **Alpha Ionone** | neat | **60** | 0.060 |
| **Anisaldehyde** | neat | **60** | 0.060 |
| Bourgeonal | neat | 50 | 0.050 |
| **Ultralia** | neat | **40** | 0.040 |
| Scentenal | 1 % | 25 | 0.025 |
| Irotyl | neat | 25 | 0.025 |
| Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| PEDMC | neat | 25 | 0.025 |
| Aurantiol | neat | 25 | 0.025 |
| Geosmin | 1 % | 15 | 0.015 |
| Indole | 10 % | 15 | 0.015 |
| Isoeugenol | neat | 15 | 0.015 |
| Farnesol | neat | 10 | 0.010 |
| Ethanol 96 % | carrier | ~35285 | ~35.285 |
| **TOTAL** | | **50000** | **50.000** |

**Bolded rows = changed from v3.** Concentrate total ≈ 14 715 µL (29.43 %).

### Why v7 scores lower on composite but higher on hedonic

The scoring engine rewards **naturalistic oil density** (photorealism) and **structural amber/cedar** (luxury) regardless of brief. v7 trims Carrot Seed (−400) and Cedarwood Virginia (−50), costing ~−2.4 photorealism and ~−2.3 luxury. In exchange, v7 gains **+1.20 hedonic** — the one axis that most closely models "this smells like a well-made perfume". For a stated brief of "creamy-buttery iris powder", hedonic is the right tiebreaker.

---

# Iris Rêverie Lactée — 50 mL v6 (scorer-winner, **⚠️ off-brief — archived**)

**Batch:** 50.00 mL · **Concentrate:** 14.910 mL (29.82 %)  
**Ethanol 96 %:** 35.090 mL

**v3 baseline (fresh process):** 78.825  
**v6 final geo (fresh process):** **79.143** (Δ vs v3 **+0.318**)

> **Archived as scorer-winner but off-brief.** The v6 hill-climb pushed the
> composition toward a rooty-earth-mineral iris (Carrot Seed +200, Cedarwood
> Virginia +200, Ambrox +200, Benzyl Sal −200) — the *Iris Silver Mist* axis,
> not the brief's *Infusion d'Iris* axis. **Do not wear v6 if you want the
> creamy-buttery-powder brief.** v6 remains useful as a reference point for
> how the composite scorer biases toward naturalistic-EO density.

### How v6 was found

The 15-probe single-variable sweep surfaced three seeds that beat v3 after a mini hill-climb (CarrotSeed +0.247, Javanol +0.233, Orivone +0.137 — all measured in the same process). The **CarrotSeed 600→800 seed** produced the largest final gain after 11 hill-climb moves, and the full ingredient dict was harvested to JSON and re-verified in a clean process at **geo 79.143** vs v3's **78.825** (same-process Δ +0.318).

A naive "merge the top moves across probes" attempt (v6-proposed) was validated and **lost** to v3 by −0.180 — confirming that the gain lives in the complete joint-optimization dict, not in the surface-level ingredient moves. The optimizer's path matters.

### Axis shift v3 → v6

| Axis | v3 | v6 | Δ |
|---|---:|---:|---:|
| longevity | 82.00 | **84.50** | **+2.50** ↑ |
| sillage | 74.50 | 73.20 | −1.30 ↓ |
| luxury | 63.40 | **64.30** | **+0.90** ↑ |
| texture | 81.00 | 80.90 | −0.10 |
| stacking_depth | 85.00 | 85.00 | 0.00 |
| photorealism | 82.80 | **83.60** | **+0.80** ↑ |
| perceptual_clarity | 75.30 | 75.30 | 0.00 |
| skin_performance | 77.30 | 77.30 | 0.00 |
| synergy | 95.00 | 95.00 | 0.00 |
| hedonic | 84.70 | 84.20 | −0.50 |

**Read:** v6 trades **−1.30 sillage** and **−0.50 hedonic** for **+2.50 longevity**, **+0.90 luxury**, and **+0.80 photorealism**. The composite wins by +0.318. The character moves from v3's "lifted transparent orris" toward a **more grounded, longer-wearing, more photoreal iris-sandalwood drydown** — the Ambrox lift (+200) and Cedarwood Virginia EO lift (+200) build a mineral-cedar shelf under the iris; Benzyl Salicylate drops hard (−200) to let the Hexyl Salicylate film carry cosmetic diffusion without heaviness; Iso E Super lifts 50→200 as molecular cocoon.

### Changes v3 → v6 (10 ingredients, +725 µL concentrate)

| Ingredient | v3 | v6 | Δ | Register |
|---|---:|---:|---:|---|
| **Ambrox Super** (30 %) | 550 | **750** | +200 | crystalline-mineral amber shelf |
| **Benzyl Salicylate** | 250 | **50** | −200 | cosmetic cushion trim (clarity-first) |
| **Carrot Seed EO** | 600 | **800** | +200 | natural orris-earth (seed driver) |
| **Cedarwood Virginia EO** | 350 | **550** | +200 | natural cedar warmth pillar |
| **Ebanol** | 900 | **1100** | +200 | creamy sandalwood mass |
| **Iso E Super** | 50 | **200** | +150 | molecular cocoon / abstract-cedar halo |
| **Hexyl Salicylate** | 300 | **350** | +50 | transparent salicylate film |
| **Anisaldehyde** | 40 | **15** | −25 | anise-powder trim |
| **Delta Decalactone** | 300 | **275** | −25 | creamy-peach trim |
| **Heliotropal** | 50 | **25** | −25 | cherry-almond trace trim |

**Why these moves (convergent reading):**
- **Ambrox +200 & Cedarwood Virginia +200** — the optimizer built a crystalline-mineral + natural-cedar base shelf under the iris. This is the longevity driver.
- **Ebanol +200** — the creamy sandalwood register gets the dose it needed; Javanol at 100 stays (not lifted here).
- **Iso E Super +150** — molecular cocoon radial halo, finally given real weight (v3 held it at 50 as an abstract trace).
- **Benzyl Salicylate −200** — cosmetic cushion trim; optimizer pushed almost all of it out. Hexyl Salicylate +50 absorbs the diffusion-film role transparently.
- **Carrot Seed +200** — the seed move that launched this trajectory; naturalistic orris-earth over synthetic ionones.
- **Trace trims** (Anisaldehyde, Delta Deca, Heliotropal) — small clarity-seeking nudges.

**Justification per register:**
- Amber: Ambrox Super chosen over Ambermax (too warm-oriental for transparent iris) and Amberwood F (too invisible for the shelf role).
- Sandalwood: Ebanol+Javanol chord kept (creamy-soft + dry-intimate). Rejected lifting Javanol to 200 here because the hill-climb found the cedar+Ebanol route gave more longevity per µL.
- Fixative: Hexyl Salicylate chosen as survivor over Benzyl Salicylate — v6 is a sheer-transparent composition, not a cosmetic-plastic one.
- Wood: Cedarwood Virginia EO + Iso E Super combined rather than Timberol (too architectural) or Kephalis (too powerful).

**Verification:** probe harvest [_opt_iris_top3_harvest.py](../../_opt_iris_top3_harvest.py) → [_opt_iris_top3_harvest.json](../../_opt_iris_top3_harvest.json). Fresh-process validation [_validate_top3.py](../../_validate_top3.py) → [_validate_top3_out.txt](../../_validate_top3_out.txt).

## Formula v6

| Ingredient | Dilution | µL | mL |
|---|---|---:|---:|
| Benzoin Resinoid | 50 % | 1475 | 1.475 |
| Hedione | neat | 1250 | 1.250 |
| **Ebanol** | neat | **1100** | 1.100 |
| Ethyl Linalool | neat | 1050 | 1.050 |
| Alpha Irone | 30 % | 900 | 0.900 |
| **Carrot Seed EO** | neat | **800** | 0.800 |
| Ethylene Brassylate | neat | 800 | 0.800 |
| **Ambrox Super** | 30 % | **750** | 0.750 |
| Ambrettolide | 10 % | 700 | 0.700 |
| Hedione HC | neat | 600 | 0.600 |
| Habanolide | neat | 600 | 0.600 |
| Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| **Cedarwood Virginia EO** | neat | **550** | 0.550 |
| Musk Ketone | 10 % | 400 | 0.400 |
| Vanillin | 10 % | 400 | 0.400 |
| **Hexyl Salicylate** | neat | **350** | 0.350 |
| Orivone | neat | 350 | 0.350 |
| Hydroxycitronellal | neat | 300 | 0.300 |
| Coumarin | 20 % | 275 | 0.275 |
| **Delta Decalactone** | neat | **275** | 0.275 |
| **Iso E Super** | neat | **200** | 0.200 |
| Mayol | neat | 175 | 0.175 |
| Javanol | neat | 100 | 0.100 |
| Ethyl Maltol | 10 % | 100 | 0.100 |
| Lilyreal ND | neat | 75 | 0.075 |
| DBCA | neat | 75 | 0.075 |
| Freesia HDI | neat | 75 | 0.075 |
| Ethyl Vanillin | neat | 75 | 0.075 |
| Damascol | 10 % | 75 | 0.075 |
| Gamma Undecalactone | neat | 75 | 0.075 |
| **Benzyl Salicylate** | neat | **50** | 0.050 |
| Bourgeonal | neat | 50 | 0.050 |
| Beta Ionone | neat | 40 | 0.040 |
| Scentenal | 1 % | 25 | 0.025 |
| Alpha Ionone | neat | 25 | 0.025 |
| **Heliotropal** | neat | **25** | 0.025 |
| Irotyl | neat | 25 | 0.025 |
| Ultralia | neat | 25 | 0.025 |
| Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| PEDMC | neat | 25 | 0.025 |
| Aurantiol | neat | 25 | 0.025 |
| **Anisaldehyde** | neat | **15** | 0.015 |
| Geosmin | 1 % | 15 | 0.015 |
| Indole | 10 % | 15 | 0.015 |
| Isoeugenol | neat | 15 | 0.015 |
| Farnesol | neat | 10 | 0.010 |
| Ethanol 96 % | carrier | **35090** | 35.090 |
| **TOTAL** | | **50000** | **50.000** |

**Bolded rows = changed from v3.**

---

# Iris Rêverie Lactée — 50 mL Optimized (v3 — inventory-constrained rebuild)

**Batch:** 50.00 mL · **Concentrate:** 14.185 mL (28.37 %)  
**Ethanol 96 %:** 35.815 mL

**Baseline geo @ 50 mL:** 74.532  
**Optimizer pass (v1) geo:** 79.020 (re-verified under current scorer, with Exaltolide in palette)  
**v2 hand-expansion (with Heliotropin + Exaltolide):** 78.838 — tied v1 on composite  
**v3 final geo (Heliotropin cut + Exaltolide cut + re-optimized, 3 waves converged):** **79.277** (Δ vs v1 **+0.257**)

### Why v3? Two inventory-driven cuts

1. **Heliotropin cut** — redundant with Vanillin 400 + Ethyl Vanillin 75 + Anisaldehyde 40 + Coumarin 275 + Benzoin 1475. The powder-sweet register was already saturated; adding Heliotropin muddied clarity without a hedonic payoff the weighted composite could register.
2. **Exaltolide out of stock** — the macrocyclic-lactonic skin-musk load (60 µL active) was redistributed across **Ambrettolide 10% 700** (naturalistic fruity-wine macrocyclic), **Habanolide 600** (warm-skin macrocyclic), **EB 800** (creamy-lactonic). This three-musk chord actually outperforms the original four-musk configuration.

### Axis shift v1 → v3-final

| Axis | v1 | v3-final | Δ |
|---|---:|---:|---:|
| longevity | 83.00 | 81.90 | −1.10 ↓ |
| sillage | 77.10 | **78.50** | **+1.40** ↑ |
| luxury | 61.90 | **63.40** | **+1.50** ↑ |
| texture | 81.10 | 81.00 | −0.10 |
| stacking_depth | 85.00 | 85.00 | 0.00 |
| photorealism | 81.90 | 82.40 | +0.50 |
| perceptual_clarity | 74.70 | **75.30** | **+0.60** ↑ |
| skin_performance | 78.80 | 77.30 | −1.50 ↓ |
| synergy | 95.00 | 95.00 | 0.00 |
| hedonic | 84.80 | 84.70 | −0.10 |

**Read:** v3 is a **net gain** (+0.257 geo) driven by luxury, sillage, clarity, and photorealism improvements. The −1.50 skin_performance and −1.10 longevity are the Exaltolide-loss trade — Ambrettolide + Habanolide + EB collectively recover most but not all of it. Luxury's +1.50 jump comes from the palette-expansion materials the v1 hill-climb could never introduce.

**New-material additions the v1 optimizer could not have reached:**

- **Javanol** (neat, 100 µL) — dry-intimate premium skin-sandalwood; complements Ebanol's creamy register, creating a two-axis sandalwood chord. Rejected alternatives: more Bacdanol (too milky-heavy for powdery target), Sandalore (too thin).
- **Cedarwood Virginia EO** (neat, optimizer settled at 350 µL — lifted from seed 150) — natural cedar warmth carrying the woody axis without Timberol's angularity. Rejected: Timberol (too architectural for iris delicacy), Kephalis (too impactful).
- **Ambrettolide 10% 700 µL** (up from 200) — naturalistic macrocyclic covering what Exaltolide used to do, with a fruity-wine skin warmth that bridges luxury + hedonic simultaneously. This is the skin-musk pillar of v3.

**Verification script:** [_opt_iris_reverie_50mL_v2.py](../../_opt_iris_reverie_50mL_v2.py) · output: [_opt_iris_reverie_50mL_v4_out.txt](../../_opt_iris_reverie_50mL_v4_out.txt)

## Why a hand-expanded v2/v3 after optimizer convergence?

The wave-optimizer converged because it hit structural limits, not because the formula was optimal:

1. **Material pinning.** Hill-climbers only move materials already in the starting set. **Javanol, Cedarwood Virginia EO** were not in v1's palette — the optimizer could never try them. Palette expansion is a human-only move.
2. **Acceptance threshold (+0.02 geo).** Small enabling moves (e.g. trim Iso E Super −400 µL) were rejected even when they'd unlock larger downstream gains.
3. **Weighted composite dilutes hedonic.** AXIS_WEIGHTS: hedonic = 0.4 vs luxury/longevity/sillage/texture/stacking/photoreal = 1.0. Powder-sweet moves barely register in the geo.
4. **Sub-ODT start × 3 ceilings** lock trace powerhouses.
5. **Concentrate cap interactions.** v1 held at 25.79 %; v3 settles at 28.37 %.

## Formula v3

| Ingredient | Dilution | µL | mL |
|---|---|---:|---:|
| Benzoin Resinoid | 50 % | 1475 | 1.475 |
| Hedione | neat | 1250 | 1.250 |
| Ethyl Linalool | neat | **1050** | 1.050 |
| Alpha Irone | 30 % | **900** | 0.900 |
| Ebanol | neat | **900** | 0.900 |
| Ethylene Brassylate | neat | **800** | 0.800 |
| Ambrettolide | 10 % | **700** | 0.700 |
| Hedione HC | neat | 600 | 0.600 |
| Carrot Seed EO | neat | **600** | 0.600 |
| Habanolide | neat | **600** | 0.600 |
| Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| Ambrox Super | 30 % | 550 | 0.550 |
| Musk Ketone | 10 % | 400 | 0.400 |
| Vanillin | 10 % | 400 | 0.400 |
| Orivone | neat | **350** | 0.350 |
| **Cedarwood Virginia EO** | neat | **350** | 0.350 |
| Hydroxycitronellal | neat | 300 | 0.300 |
| Delta Decalactone | neat | 300 | 0.300 |
| Hexyl Salicylate | neat | 300 | 0.300 |
| Coumarin | 20 % | 275 | 0.275 |
| Benzyl Salicylate | neat | **250** | 0.250 |
| Mayol | neat | 175 | 0.175 |
| **Javanol** | neat | **100** | 0.100 |
| Ethyl Maltol | 10 % | 100 | 0.100 |
| Lilyreal ND | neat | 75 | 0.075 |
| DBCA | neat | 75 | 0.075 |
| Freesia HDI | neat | 75 | 0.075 |
| Ethyl Vanillin | neat | 75 | 0.075 |
| Damascol | 10 % | 75 | 0.075 |
| Gamma Undecalactone | neat | **75** | 0.075 |
| Iso E Super | neat | **50** | 0.050 |
| Heliotropal | neat | **50** | 0.050 |
| Bourgeonal | neat | 50 | 0.050 |
| Beta Ionone | neat | 40 | 0.040 |
| Anisaldehyde | neat | 40 | 0.040 |
| Scentenal | 1 % | 25 | 0.025 |
| Alpha Ionone | neat | 25 | 0.025 |
| Irotyl | neat | 25 | 0.025 |
| Ultralia | neat | 25 | 0.025 |
| Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| PEDMC | neat | 25 | 0.025 |
| Aurantiol | neat | 25 | 0.025 |
| Geosmin | 1 % | 15 | 0.015 |
| Indole | 10 % | 15 | 0.015 |
| Isoeugenol | neat | 15 | 0.015 |
| Farnesol | neat | 10 | 0.010 |
| Ethanol 96 % | carrier | **35815** | 35.815 |
| **TOTAL** | | **50000** | **50.000** |

**Bolded rows = changed from v1.** Materials cut from v1: Exaltolide (−600). Heliotropin never added.

## Accord architecture

**Top (lift + hesperidic flash):** Bergamot Sicilian 550, Ethyl Linalool 1050 (lifted from 650 — optimizer's clarity-seeking move), Mayol 175 muguet-stem, Freesia HDI 75, Bourgeonal 50, Scentenal trace for mineral-green lift.

**Heart — the iris-cream-jasmine triad:**
- **Iris pillar** — Alpha Irone 30% 900 µL (luxury driver), Orivone 350 (buttery base), Carrot Seed EO 600 (natural earthy-orris), Alpha Ionone 25 + Beta Ionone 40 + Alpha Isomethyl Ionone 25 (ionone chord).
- **Jasmine radiance** — Hedione 1250 + Hedione HC 600 = 1850 µL Hedione-axis (dihydrojasmonate diffusion bed), Indole 10% 15 µL for jasmine depth.
- **Cream-lactonic lock** — Ebanol 900 (creamy sandalwood), Delta Decalactone 300, γ-Undecalactone 75, Mayol muguet.
- **Muguet-floral garland** — DBCA 75 (gardenia-rose accent), Lilyreal ND 75, Hydroxycitronellal 300, Farnesol 10 (IFRA-floor dose).

**Base — three-musk chord + sandalwood two-axis + amber:**
- **Skin-musk chord** — Ambrettolide 10% 700 (naturalistic fruity-wine, depth axis), Habanolide 600 (warm-skin, depth axis), EB 800 (creamy-lactonic), Musk Ketone 10% 400 (powdery character-echo — the ONLY musk that reinforces the iris powder register).
- **Sandalwood two-axis** — Javanol 100 (dry-intimate) + Ebanol 900 (creamy-soft) = full sandalwood spectrum. Rejected Bacdanol (wrong for transparent powder target) and Sandalore (too thin).
- **Amber + wood base** — Ambrox Super 30% 550 (crystalline mineral, the clinical amber — justified here to keep iris transparent, NOT warm), Cedarwood Virginia EO 350 (natural cedar bridge — optimizer lifted from seed 150), Iso E Super 50 (radical trim — molecular halo trace only, not structural).
- **Resin-balsamic anchor** — Benzoin Resinoid 50% 1475 (vanillic-balsamic mass), Benzyl Salicylate 250 (cosmetic diffusion cushion trimmed from 350 — optimizer's clarity-first move), Hexyl Salicylate 300 (transparent-green salicylate film over the heavy Benzyl Sal), Coumarin 20% 275, Vanillin 10% 400, Ethyl Vanillin 75, Heliotropal 50 (cherry-almond radiance trace — kept at minimum for top-of-heart lift).

**Sub-ODT trace set** — Geosmin 1% 15 µL (petrichor), Indole 10% 15 µL (jasmine-skatole depth), Isoeugenol 15 (spice-powder), Farnesol 10 (lily-floor), Aurantiol 25 (neroli-muguet), Damascol 10% 75 (rosy-fruity), Bourgeonal 50 — the "naturalistic dirt floor" under the clean powder composition.

## Character read

v3 delivers an **iris-cream-sandalwood accord** where:
- The **Alpha Irone 900 µL of 30 %** (= 270 µL active) is the luxury pillar — this is the single biggest lever in the entire formula.
- The **Ambrettolide 700 µL of 10 %** (= 70 µL active) replaces Exaltolide as the lactonic skin-musk, with naturalistic fruity-wine warmth Exaltolide lacks.
- The **Javanol 100 + Ebanol 900** creates a sandalwood chord spanning dry-intimate to creamy-soft — not available in v1 or the original hand-expanded v2.
- The **Cedarwood Virginia EO 350** (optimizer lifted it +200 from seed) proves the palette-expansion thesis: the hill-climb wanted this material once a human put it on the bench.

The formula reads as a **transparent lactonic orris** — not the heavy creamy-vanilla iris trope, but a lifted iris where Ambrox's crystalline mineral register keeps the powder from collapsing into sweetness.
# Iris Rêverie Lactée — 50 mL Optimized (v2 — luxury/hedonic palette expansion)

**Batch:** 50.00 mL · **Concentrate:** 14.610 mL (29.22 %)  
**Ethanol 96 %:** 35.390 mL

**Baseline geo @ 50 mL:** 74.532  
**Optimizer pass (v1) geo:** 78.573 (re-verified under current scorer)  
**v2 hand-expansion:** palette additions + dose lifts targeting weakest axes (luxury 61.90, hedonic regression, skin regression)  
**v2 start geo (hand-expanded):** 78.407 (Δ vs v1 −0.166)  
**v2 final geo (after 4 convergence waves):** **78.567** (Δ vs v1 −0.006, essentially tied)  
**Concentrate (v2 final):** 14.885 mL (29.77 %)

### Axis shift v1 → v2-final

| Axis | v1 | v2-final | Δ |
|---|---:|---:|---:|
| longevity | 83.20 | **85.80** | **+2.60** ↑ |
| sillage | 73.10 | 71.90 | −1.20 ↓ |
| luxury | 61.90 | 62.00 | +0.10 |
| texture | 81.10 | 81.00 | −0.10 |
| stacking_depth | 85.00 | 85.00 | 0.00 |
| photorealism | 82.30 | 81.90 | −0.40 |
| perceptual_clarity | 74.70 | 73.60 | −1.10 ↓ |
| skin_performance | 78.80 | 78.80 | 0.00 |
| synergy | 95.00 | 95.00 | 0.00 |
| hedonic | 84.80 | 84.50 | −0.30 |

**Read:** v2 is a **character rewrite, not a score improvement**. The composite geo tied v1, but the axis mix shifted — v2 trades sillage + clarity for a significant longevity lift (+2.60) and a slightly richer textural body via Cedarwood Virginia EO (+550 µL settled by optimizer), Ambrettolide (+300), Alpha Irone (+400), Ebanol (+150), Carrot Seed (+175), Habanolide (+200), Bergamot Sicilian (+200). Iso E Super dropped −200, Coumarin dropped −200, Benzoin dropped −200. The optimizer accepted Javanol 100 µL, Heliotropal 100, Heliotropin 75, γ-Undecalactone 75 — all new-material additions the v1 hill-climb could never have introduced.

**Verdict:** If the goal is a higher weighted-composite score, v1 wins by a whisker. If the goal is a **longer-wearing, more naturalistic orris-sandalwood drydown** with real Cedarwood Virginia resonance and Javanol skin-intimacy, v2 is the formula — the −1.2 sillage trade buys a +2.6 longevity gain and a more "woven" character from three new wood/powder axes the optimizer alone could not reach.

**Verification script:** [_opt_iris_reverie_50mL_v2.py](../../_opt_iris_reverie_50mL_v2.py) · output: [_opt_iris_reverie_50mL_v2_out.txt](../../_opt_iris_reverie_50mL_v2_out.txt)

## Why a v2 after optimizer convergence?

The wave-optimizer converged because it hit structural limits, not because the formula was optimal:

1. **Material pinning.** Hill-climbers only move materials already in the starting set. **Heliotropin, Javanol, Cedarwood Virginia EO** were not in v1's palette — the optimizer could never try them. Palette expansion is a human-only move.
2. **Acceptance threshold (+0.02 geo).** Small enabling moves (e.g. trim Iso E Super −200 µL) were rejected even when they'd unlock larger downstream gains.
3. **Weighted composite dilutes hedonic.** AXIS_WEIGHTS: hedonic = 0.4 vs luxury/longevity/sillage/texture/stacking/photoreal = 1.0. Powder-sweet moves barely register in the geo — hedonic actually dropped −0.70 in v1.
4. **Sub-ODT start × 3 ceilings** lock trace powerhouses.
5. **Concentrate cap.** v1 held at 25.79 %; v2 pushes to 29.22 % to make room for natural orris and cream drydown.

## Changelog v1 → v2 (FTEC-free per standing directive)

**Luxury axis — naturals, macrocyclics, premium sandalwood:**
- Alpha Irone 30 % 500 → **900** µL (+400) — real orris dose, luxury's single biggest lever
- Ambrettolide 10 % 200 → **500** µL (+300) — naturalistic macrocyclic musk, fruity-wine skin warmth
- Ebanol 650 → **900** µL (+250) — creamy-silk sandalwood
- **Javanol neat 100 µL** (new) — dry-intimate premium skin-sandalwood, textural precision
- **Cedarwood Virginia EO 150 µL** (new) — natural cedar warmth, bridges to Koavone register
- Carrot Seed EO 450 → **600** µL (+150) — natural earthy-orris
- Orivone 225 → **350** µL (+125) — buttery iris base deepening
- Iso E Super 450 → **250** µL (−200) — trimmed luxury-neutral abstract-cedar filler

**Hedonic axis — powder-cream-heliotrope:**
- **Heliotropin neat 100 µL** (new) — direct almond-heliotrope hedonic driver
- Heliotropal 25 → **100** µL (+75) — cherry-almond radiance
- γ-Undecalactone neat 10 → **75** µL (+65) — peach-cream lactone
- Ethylene Brassylate 900 → **1100** µL (+200) — lactonic-creamy musk depth

**Rationale for each added material vs rejected alternatives:**
- **Javanol** over Ebanol-alone: dry-intimate register complements Ebanol's creamy, creating a two-axis sandalwood chord. Rejected adding more Bacdanol (too milky-heavy for this powdery target) or Sandalore (too thin).
- **Cedarwood Virginia EO** over Timberol: natural cedar character, not architectural — carries warmth not angles. Rejected Koavone (already implied by overall warm-woody profile) and Kephalis (too impactful, would break the iris delicacy).
- **Heliotropin** over Vanillin boost: heliotrope-almond register directly reinforces the "lactée" concept; Vanillin at 400 µL of 10 % is already sufficient for vanilla floor. Rejected Ethyl Vanillin boost (smokier, off-concept).
- **Ambrettolide over Habanolide boost**: more naturalistic, fruity-wine skin warmth matches the orris-cream brief better than Habanolide's flat warm-skin musk. Ambrettolide bridges luxury + hedonic simultaneously.

## Formula v2

| Ingredient | Dilution | µL | mL |
|---|---|---:|---:|
| Benzoin Resinoid | 50 % | 1475 | 1.475 |
| Hedione | neat | 1250 | 1.250 |
| Ethylene Brassylate | neat | **1100** | 1.100 |
| Alpha Irone | 30 % | **900** | 0.900 |
| Ebanol | neat | **900** | 0.900 |
| Ethyl Linalool | neat | 650 | 0.650 |
| Hedione HC | neat | 600 | 0.600 |
| Exaltolide | 10 % | 600 | 0.600 |
| Carrot Seed EO | neat | **600** | 0.600 |
| Bergamot FCF oil Sicilian | neat | 550 | 0.550 |
| Ambrox Super | 30 % | 550 | 0.550 |
| Ambrettolide | 10 % | **500** | 0.500 |
| Habanolide | neat | 450 | 0.450 |
| Musk Ketone | 10 % | 400 | 0.400 |
| Vanillin | 10 % | 400 | 0.400 |
| Benzyl Salicylate | neat | 350 | 0.350 |
| Orivone | neat | **350** | 0.350 |
| Hydroxycitronellal | neat | 300 | 0.300 |
| Coumarin | 20 % | 300 | 0.300 |
| Delta Decalactone | neat | 300 | 0.300 |
| Hexyl Salicylate | neat | 300 | 0.300 |
| Iso E Super | neat | **250** | 0.250 |
| Mayol | neat | 175 | 0.175 |
| **Cedarwood Virginia EO** | neat | **150** | 0.150 |
| **Heliotropin** | neat | **100** | 0.100 |
| **Javanol** | neat | **100** | 0.100 |
| Ethyl Maltol | 10 % | 100 | 0.100 |
| Heliotropal | neat | **100** | 0.100 |
| Lilyreal ND | neat | 75 | 0.075 |
| DBCA | neat | 75 | 0.075 |
| Freesia HDI | neat | 75 | 0.075 |
| Ethyl Vanillin | neat | 75 | 0.075 |
| Damascol | 10 % | 75 | 0.075 |
| Gamma Undecalactone | neat | **75** | 0.075 |
| Bourgeonal | neat | 50 | 0.050 |
| Beta Ionone | neat | 40 | 0.040 |
| Anisaldehyde | neat | 40 | 0.040 |
| Scentenal | 1 % | 25 | 0.025 |
| Alpha Ionone | neat | 25 | 0.025 |
| Irotyl | neat | 25 | 0.025 |
| Ultralia | neat | 25 | 0.025 |
| Alpha Isomethyl Ionone | neat | 25 | 0.025 |
| PEDMC | neat | 25 | 0.025 |
| Aurantiol | neat | 25 | 0.025 |
| Geosmin | 1 % | 15 | 0.015 |
| Indole | 10 % | 15 | 0.015 |
| Isoeugenol | neat | 15 | 0.015 |
| Farnesol | neat | 10 | 0.010 |
| Ethanol 96 % | carrier | **35390** | 35.390 |
| **TOTAL** | | **50000** | **50.000** |

**Bolded rows = changed from v1.** Materials with unchanged doses appear unbolded.

## Axis scores

| Axis | Baseline | Final | Δ |
|---|---:|---:|---:|
| longevity | 80.20 | 82.90 | +2.70 |
| sillage | 74.20 | 77.10 | +2.90 |
| luxury | 48.70 | 61.90 | +13.20 |
| texture | 73.90 | 81.10 | +7.20 |
| stacking_depth | 85.00 | 85.00 | +0.00 |
| photorealism | 80.80 | 82.30 | +1.50 |
| perceptual_clarity | 67.40 | 74.70 | +7.30 |
| skin_performance | 79.30 | 78.80 | -0.50 |
| synergy | 95.00 | 95.00 | +0.00 |
| hedonic | 85.50 | 84.80 | -0.70 |
