# HED-FLORAL-01 — Rose de Mai Unadorned — FINAL — 30 mL / nominal 20% stock concentrate — v2

**Date:** 2026-09-02  
**Claim mode:** unclaimed  
**Reference contract:** none  
**Reference scope:** architecture  
**Family archetype:** `floral_soliflore.rose_reference`  
**Immediate parent:** `formulas/HED-FLORAL-01_Rose_de_Mai_Unadorned_30mL_20pct_EdP_v1.md`  
**Parent formula-definition SHA-256:** `9e3865931347d6cf855ca0363da78ec02fa7576a8497374de5af51d92bec0529`  
**Concentration:** 6,000 uL stock concentrate + 24,000 uL ethanol; 30,000 uL finished total; nominal 20% v/v stock concentrate  
**Status:** FINAL DESIGN FORMULA — SENSORY / SAFETY / PHYSICAL PERFORMANCE NOT TESTED — RELEASE HOLD  
**Essential-oil use:** NONE

## Target / Ideal

Rose de Mai Absolute is the subject, not a decoration inside a generic floral perfume. The intended character is warm living petals, soft honey, damp-green natural shadow, and a quiet persistent floral skin. The formula is deliberately not padded for ingredient count.

Only rose-compatible supports are used. Phenethyl Alcohol supplies petal volume; Citronellol and Nerol extend rose-alcohol facets already represented in the absolute; Hexyl Salicylate supplies a low-odor transparent film. The absolute remains the largest individual nominal odor-active dose. Added Geraniol is omitted because the absolute's composite model already contains a substantial geraniol fraction and the repository flags the standalone Geraniol ODT as likely wrong by 1000x.

Benzyl Salicylate, Phenyl Ethyl Acetate, Hedione, musks, woods, ionones, Rose Oxide, added damascones/damascenone, muguet materials, aldehydes, gourmand materials, and all essential oils are excluded because each can impose a recognizable non-Rose-de-Mai signature. Phenyl Ethyl Acetate was evaluated at 20 uL and rejected after it formed a separate strong modeled OAV channel rather than remaining a trace. The absolute's own very low vapor pressure also supplies persistence, so no woody or musky ballast is added.

## Current-Inventory Authority

Every formula row was checked against the live `inventory.txt` on 2026-09-02. The subject stock is the user-confirmed `Rose de Mai Absolute (10% in DPG)`, the only owned Rose de Mai stock. No sub-10-uL raw dose is required.

The Rose de Mai stock's 10% fraction basis is not recorded as w/w, w/v, or v/v, and its density and batch-specific constituent assay are unresolved. Raw-volume arithmetic is exact. Nominal active-volume proxies are supplied for compounding transparency, but exact active mass and exact concentrate ppm w/w remain `UNAVAILABLE / HOLD`; they are not fabricated.

Rose de Mai Absolute is a natural mixture. Its OAV must use the repository's constituent-composite model rather than a monomolecular parent ODT. The composite is a partial literature proxy rather than a batch-specific GC-O assay, so OAV is a screening diagnostic, never a measured smell-share or liking result.

## Final Formula

| # | Ingredient | Stock | Raw amount (uL) | Nominal active (uL) | Nominal active-volume ppm in 6,000 uL concentrate* | Role |
|---:|---|---|---:|---:|---:|---|
| 1 | Rose de Mai Absolute | 10% in DPG | 5000 | 500 | 83,333 | Named subject; majority of the odor-active proxy |
| 2 | Phenethyl Alcohol | neat | 250 | 250 | 41,667 | Quiet petal volume; deliberately cut to one quarter of v1 |
| 3 | Citronellol | neat | 60 | 60 | 10,000 | Soft fresh rose-alcohol contour |
| 4 | Nerol | neat | 20 | 20 | 3,333 | Small fresh-petal lift; held below a citrusy-rose takeover |
| 5 | Hexyl Salicylate | neat | 100 | 100 | 16,667 | Transparent structural floral film, not a creamy salicylate cushion |
| 6 | Dipropylene Glycol | neat | 570 | 0 | 0 | Constant-total carrier |
|  | **Concentrate total** |  | **6000** | **930** | **155,000** |  |

\*Active-volume ppm is a nominal v/v proxy, not ppm w/w and not an OAV input. Exact ppm w/w is withheld until the stock fraction bases and density chain are authoritative.

Nominal DPG carrier proxy in the concentrate is 5,070 uL: 4,500 uL from the Rose stock and 570 uL direct DPG. Nominal non-carrier active-volume proxy is 930 uL. Rose de Mai Absolute contributes 500/930 = **53.8%** of that total and 500/830 = **60.2%** of the rose-core active proxy when the structural Hexyl Salicylate is excluded. The subject is therefore a true majority, not merely the largest single row.

Add 24,000 uL ethanol only after stock identity, quantity, basis, safety, and physical-compounding authority are confirmed. The resulting 30,000 uL batch is nominally 20% v/v stock concentrate; because the stocks contain DPG, it is not 20% neat aromatic material.

## v1 to v2 Intentional Dose Decisions

| Material | v1 nominal active (uL) | v2 nominal active (uL) | Decision |
|---|---:|---:|---|
| Rose de Mai Absolute | 180 | 500 | Increase the named subject by 2.78x so it becomes a true active-proxy majority rather than a decoration |
| Phenethyl Alcohol | 1000 | 250 | Intentional 4x reduction; remove generic rosewater bulk |
| Citronellol | 450 | 60 | Intentional 7.5x reduction; retain contour without detergent/geranium drift |
| Geraniol | 10 | 0 | Intentional omission; the absolute already carries modeled native Geraniol and the standalone ODT is under data-quality dispute |
| Nerol | 100 | 20 | Intentional 5x reduction; retain freshness without citrusy takeover |
| Hexyl Salicylate | 240 | 100 | Reduce structural film; keep it subordinate and non-cosmetic |

## Finality and Claim Ceiling

This is the single final design formula for the 30 mL Rose de Mai perfume. No additional material should be added merely to increase complexity, price signaling, score, or material count. A later change is justified only by a defined defect observed in a controlled physical smelling trial.

"Final design" does not mean empirically proven best-smelling, safe, stable, or release-ready. Rose identity retention, hedonic preference, sillage, longevity, stability, skin behavior, and safety remain `NOT TESTED`; physical compounding and release remain `HOLD` until the missing stock-basis and safety authority are resolved.

<!-- PIPELINE_ANALYSIS_START -->
## Pipeline Analysis

<!-- pipeline-analysis-manifest: {"analysis_input_sha256":"b5239346dc1dfb0a9d3d50298677ac3d0f748bd8e5b61eabd4169d0aaadf6a09","analysis_sha256":"bf842793df0af4f1425172256b0e12c70a52269b820611f20bdfd6aa8102db0b","artifact_sha256":"11b5a49010b44162be8eb050790e741a2a51530fdcbd9351f557a9fb49481884","authorities":{"claim":["PASS"],"headspace_oav":["MODELED_ACTIVE_CONCENTRATE_SCREEN"],"quantitative":["WARN"],"stock":["FAIL"]},"binding_schema":"formula-artifact-binding-v2","canonical_records":[{"canonical_content_sha256":"24812743829a25c9d22030fd74fb4ea86b2414a9ed4b626037131c7b38eab6e5","record_id":"formula:1:hed-floral-01-rose-de-mai-unadorned-final-30-ml-nominal-20-stock-concentrate-v2","record_version":1}],"config_sha256":"75d42e21858b20f00367f6afd3dab5369a1d367843eac367d52fa796055dadcb","formula_definitions":[{"name":"HED-FLORAL-01 — Rose de Mai Unadorned — FINAL — 30 mL / nominal 20% stock concentrate — v2","number":1,"sha256":"24812743829a25c9d22030fd74fb4ea86b2414a9ed4b626037131c7b38eab6e5"}],"g15_parent_formula_definitions":[{"name":"HED-FLORAL-01 — Rose de Mai Unadorned — 30 mL / 20% EdP — v1","number":1,"sha256":"9e3865931347d6cf855ca0363da78ec02fa7576a8497374de5af51d92bec0529"}],"generated_at_utc":"2026-09-02T06:21:40.574062+00:00","inventory_sha256":"fc0249eb1329b15cf7c3b43d8c06114860090a5222ca3fc3341e64d6e3059e2a","inventory_v5_alias_crosswalk_sha256":"4320f19e1d3dff1cca885ad3d8004c2354cef4c3964e31668a6615028bb914d6","inventory_v5_snapshot_sha256":"f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99","inventory_v5_source_workbook_sha256":"e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331","legacy_formula_hashes_v1":[{"name":"HED-FLORAL-01 — Rose de Mai Unadorned — FINAL — 30 mL / nominal 20% stock concentrate — v2","number":1,"sha256":"127ef9653b4b52655742f5e02f5d871358e6f9cc03824b0a1458d00ee0fdfdd2"}],"overall":"FAIL","pipeline_source_sha256":"69da44d8dca828b154daab7bf73caab2fef75c91b985f85af7a7c0867d6eadd5","provenance":{"activity":"formula_release_gate","agent":"perfume-chem pipeline","derivation":"analysis_artifact wasDerivedFrom all input entities","entities":["formula_definition","release_config","legacy_inventory_compatibility_text","inventory_v5_snapshot","inventory_v5_source_workbook","inventory_v5_alias_crosswalk","scientific_inputs","pipeline_source","analysis_artifact"]},"renderer_version":"formula-release-gate-v2","repository_commit":"d99ecdca8b0a4bf741bd4dda7bd564649cf05982","schema":"perfume_pipeline_run_evidence_v2","scientific_inputs_sha256":"8a8994b92cc098aeacc167e80f829ee69cc99d51f062ca277390916a47da4a71","semantic_config":{"formula_family_archetypes":["floral_soliflore.rose_reference"],"g15_authorized_active_dose_changes":{"Citronellol":"Intentional 7.5x reduction to prevent detergent or geranium drift","Geraniol":"Intentional omission because Rose de Mai already carries modeled native geraniol and the standalone ODT has a 1000x data-quality dispute","Nerol":"Intentional 5x reduction to prevent citrusy rose takeover","Phenethyl Alcohol":"Intentional 4x reduction so Rose de Mai replaces generic rosewater bulk as the named subject"},"requested":{"allow_preblends":false,"batch_scaling_targets_ml":[],"batch_volume_ml":30,"brief":"generic","commercial_confidence_policy":"block","commercial_mode":false,"concentration_bracket":"EdP","effective_ifra_headroom":1,"expected_concentrate_ul":6000,"expected_retail_price_thb":1500,"family_archetype":"floral_soliflore.rose_reference","ifra_headroom":1,"matrix_components_moles":[],"matrix_mass_g":0,"matrix_source":"omitted","max_perceptible_channels":30,"min_confidence_score":25,"min_neat_trace_ul":5,"min_perceptible_materials":3,"price_tier":"auto","quantitative_claim":false,"temperature_K":305}}} -->

```text
# Run Evidence Contract

Formula definition SHA-256: #1 24812743829a25c9d22030fd74fb4ea86b2414a9ed4b626037131c7b38eab6e5
Config SHA-256: 75d42e21858b20f00367f6afd3dab5369a1d367843eac367d52fa796055dadcb
Legacy inventory.txt compatibility SHA-256: fc0249eb1329b15cf7c3b43d8c06114860090a5222ca3fc3341e64d6e3059e2a
Inventory V5 snapshot SHA-256: f81c7b277bb1b56d4b2045c98355754449be11fc9d6f121ce4e8de4539e35d99
Inventory V5 source workbook SHA-256: e36287aca26f34354b3244f07618cb4c12750dfb85db5584dca39d5130025331
Inventory V5 alias crosswalk SHA-256: 4320f19e1d3dff1cca885ad3d8004c2354cef4c3964e31668a6615028bb914d6
Scientific inputs SHA-256: 8a8994b92cc098aeacc167e80f829ee69cc99d51f062ca277390916a47da4a71
Pipeline source SHA-256: 69da44d8dca828b154daab7bf73caab2fef75c91b985f85af7a7c0867d6eadd5
Exact concentrate ppm w/w: UNAVAILABLE
Headspace/OAV basis: MODELED_ACTIVE_CONCENTRATE_SCREEN
Headspace/OAV class: HEURISTIC_NOT_MEASURED (never a sensory-similarity percentage)
Inventory stock authority: FAIL
Quantitative gate authority: WARN
Named-reference authority: PASS
Sensory-equivalence authority: NOT_AUTHORIZED_NOT_MEASURED
# HED-FLORAL-01 — Rose de Mai Unadorned — FINAL — 30 mL / nominal 20% stock concentrate — v2

## Gate Summary

**104 PASS** / **40 WARN** / **3 FAIL**

  FAIL pipeline_preflight: 13 checks; 7 warnings
  FAIL g15_oav_firewall: G15 requires every child row to have a uniquely resolved live inventory stock.
  FAIL inventory_stock_contract: 1 material stock contract failure(s): Dipropylene Glycol
  WARN quantitative_authority: Exact active concentrate ppm w/w is unavailable; OAV is an estimated diagnostic only.
  WARN headspace_scope: Headspace/OAV is an active-concentrate screening model; the finished ethanol-water-solvent matrix is omitted.
  WARN architecture_concentration: Top-1/3/5 active share = 38.0%/88.0%/98.7% (estimated_active_volume_fraction); HHI=0.290
  WARN odt_coverage: 3 material(s) rely on derived/unverified ODTs (83% OAV share)
  WARN phase_compatibility: HSP coverage too thin for trusted phase audit: 0.0% active mass across 0 materials
  WARN odt_sanity: 1 materials with suspect ODT values: Dipropylene Glycol=100ppm (possible sentinel)
  WARN vp_cross_source: 6 materials use inferred enthalpy for VP at 305.00 K; 1 unresolved cross-source VP conflicts
  WARN safety_ifra_allergen: 3 materials lack explicit IFRA Cat4 limits; 2 EU allergen declarations
  WARN eu_allergen_declaration: EU allergens requiring label: citronellol
  WARN oav_physics_gamma: 6/6 materials use predictive, heuristic, fallback, or unknown gamma authority; largest gamma=1 comparison leverage Citronellol=1.8x
  WARN solvent_matrix: stock-carrier authority NAMED_CARRIER_VOLUME_PROXY; known named carriers {'DPG': 4500.0}; unresolved carrier proxy 0.0 uL; 1 named carrier row(s) lack a v/v basis
  WARN perfumer_logic: floral_soliflore.rose_reference; rerun optimizer: rose_core: 5.500% active below 16.000; rose_diffusion_support: 1.667% active below 3.000 [advisory guideline; not release-blocking]
  WARN family_drift_detector: floral_soliflore.rose_reference; rose_core: 5.500% active below 16.000; rose_diffusion_support: 1.667% active below 3.000 [advisory guideline; not release-blocking]
  WARN novelty_vs_reference: reference/control archetype; familiar by design, not the new exploration target
  WARN perfume_knowledge: Pyramid off-target: Expected T:10% H:60% B:30%, Actual T:2.2% H:87.1% B:10.8%; top OAV off-target for family floral_soliflore; heart OAV needs improvement for family floral_soliflore
  WARN carles_pyramid: Carles pyramid: empty windows = 3h_top_heart (need >2% active in each of 5 windows)
  WARN carles_material_count: 6 materials — too few for a finished perfume [advisory guideline; not release-blocking]
  WARN carles_accord_ratio: Exact active-mass ppm is unavailable; pairwise dose ratios were not evaluated.
  WARN beaux_registres: Beaux registers missing: soprano
  WARN ellena_legibility: Top 3 materials = 100% of OAV — too simple, no depth
  WARN literature_compliance: Literature compliance: 2/5 principles passed (40%) [advisory guideline; not release-blocking]
  WARN edge_cases: Musk coverage: 0%, gaps: 3, formula VP factor x1.79-2.21 (median x1.94, T=305.00K vs 298.15K, n=6)
  WARN family_hedonic: Family 'floral_soliflore.rose_reference' has 0 legacy pitfalls and 0 tips quarantined pending validation
  WARN somatosensory: 0 candidate chemesthetic materials detected; formula-level effects require exposure and human validation
  WARN stevens_power_law: rose de mai absolute dominates perceived intensity at 63%
  WARN stevens_n_efficiency: Exact active-mass ppm is unavailable; dose-efficiency comparison not evaluated.
  WARN jellinek_psychology: Jellinek categories weak: erogenic, narcotic, stimulating, anti_erogenic
  WARN coty_single_material_limit: Exact active-mass ppm is unavailable; single-material limit not evaluated.
  WARN roudnitska_hedione_pct: Exact active-mass ppm is unavailable; Hedione percentage heuristic not evaluated.
  WARN adaptation_timing: fast tier < 5% (no immediate impact); slow tier < 10% (poor longevity)
  WARN adaptation_overlap: Top 5 materials all in same adaptation tier (medium: 100%) — collapse risk
  WARN oav_intelligence: diffusion_layers: Missing intimate layer — fragrance will feel hollow up close; material_class_distribution: Class distribution: florals:21%; volatility_balance: T:16% H:84% B:0% (target 30:35:35 for EdP)
  WARN evaporation_rate_balance: Pyramid imbalance: top = 1%, heart = 92%
  WARN tenacity_projection: VP<0.001Pa = 0% (<3%, may lack depth)
  WARN master_perfumer_gate: opening likely underbuilt; drydown likely underbuilt
  WARN mass_market_tier_check: Only 6 materials for a 1500 THB formula. Consumers expect complexity at this price. Consider adding structural materials.
  WARN authority_vector: Safety authority insufficient (0.00) — unknown IFRA limits for too many materials; Identity (0.00) AND Quantity (0.00) authority both insufficient — insufficient evidence; Identity authority insufficient (0.00). DIMENSIONS NEVER AVERAGED. [advisory guideline; not release-blocking]
  WARN concentration_basis: 7 material(s) with unspecified concentration basis: Citronellol: concentration basis not specified (use w/w, v/v, or w/v); Dipropylene Glycol: concentration basis not specified (use w/w, v/v, or w/v); Hexyl Salicylate: concentration basis not specified (use w/w, v/v, or w/v); Nerol: concentration basis not specified (use w/w, v/v, or w/v); Phenethyl Alcohol: concentration basis not specified (use w/w, v/v, or w/v)... [advisory guideline; not release-blocking]
  WARN robustness_perturbation: 12 fragile perturbation(s) across 12 checks; Citronellol up: brief grammar failure under perturbation; Citronellol down: brief grammar failure under perturbation; Dipropylene Glycol up: brief grammar failure under perturbation
  WARN confidence_minimum: combined confidence 11.2 below 25.0 after preflight evidence penalty 9.0; reference-control study remains diagnostic only


## Authority Dimensions

| Dimension | Status | Authority |
|---|---|---|
| Inventory stock | FAIL | 1 material stock contract failure(s): Dipropylene Glycol |
| Quantitative ppm w/w | UNAVAILABLE | Exact only when the full declared mass and density chain is available. |
| Headspace/OAV | MODELED_ACTIVE_CONCENTRATE_SCREEN | HEURISTIC_NOT_MEASURED; diagnostic model, not measured odor intensity. |
| Named reference | PASS () | Reference comparison explicitly disclaimed. |
| Sensory similarity | NOT_AUTHORIZED_NOT_MEASURED | Requires blinded bench comparison; no model score supplies this authority. |
| Combined confidence | 11.2/100 | Aggregate diagnostic only; it cannot override any authority dimension above. |


## Headspace OAV — Opening (0s)

| Material | Dil | Raw µL | Act µL | MW | MF% | VP Pa | γ | Vapor ppm | ODT ppm | OAV | Note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Rose de Mai Absolute | 10.0% | 5000.00 | 500.00 | 220.000 | 23.749 | 0.002395 | 0.550 | 19.962775 | 0.005000000 | 8963.8 | heart |
| Nerol | 100.0% | 20.00 | 20.00 | 154.250 | 1.355 | 3.681605 | 1.800 | 0.886138 | 0.000500000 | 1772.3 | top |
| Citronellol | 100.0% | 60.00 | 60.00 | 156.300 | 4.011 | 4.142654 | 1.800 | 2.952096 | 0.040000000 | 73.8 | heart |
| Phenethyl Alcohol | 100.0% | 250.00 | 250.00 | 122.170 | 21.790 | 0.235647 | 1.000 | 0.506755 | 0.026000000 | 19.5 | heart |
| Hexyl Salicylate | 100.0% | 100.00 | 100.00 | 222.300 | 4.701 | 0.158655 | 0.750 | 0.055203 | 0.035000000 | 1.6 | base |
| Dipropylene Glycol | 100.0% | 570.00 | 570.00 | 134.170 | 44.394 | 0.022113 | 1.000 | 0.096883 | 100.000000000 | 0.0 | carrier |

**Materials:** 6 total (1 top, 3 heart, 1 base)
**Total vapor:** 24.46 ppm

### Note Distribution

**TOP:** 1 mats, 1.3% active, 16.4% OAV
  - Nerol                        OAV=  1772.3 (very strong) VP=3.682Pa
**HEART:** 3 mats, 54.0% active, 83.6% OAV
  - Rose de Mai Absolute         OAV=  8963.8 (very strong) VP=0.002Pa
  - Citronellol                  OAV=    73.8 (moderate-strong) VP=4.143Pa
  - Phenethyl Alcohol            OAV=    19.5 (moderate) VP=0.236Pa
**BASE:** 1 mats, 6.7% active, 0.0% OAV
  - Hexyl Salicylate             OAV=     1.6 (at threshold) VP=0.159Pa

### Sub-threshold Materials (OAV < 1)
1/6 materials below perceptible threshold
  - Dipropylene Glycol: OAV=0.00 VP=0.022Pa act=570uL role=solvent [STRUCTURAL_OR_FIXATIVE]
### High-OAV Flags (>5000)
  - Rose de Mai Absolute OAV=8964 dominates headspace — may mask subtler notes

### OAV by Odor Family

             rose  83.6% =========================================  (3 mats)
           floral  16.4% ========  (1 mats)
       salicylate   0.0% =  (1 mats)
         fixative   0.0% =  (1 mats)

## Temporal Evolution (5 Windows)

| Window | Time | T/H/B | Vapor | Remain idx | Leaders |
|------------|------------|------------|------------|------------|------------|
| opening      |      0s |  1.3/92.0/ 6.7 |   24.46ppm |  100.0% | Rose de Mai (8964), Nerol(1772), Citronellol(74)
| top          |    300s |  1.3/92.0/ 6.7 |   24.41ppm |   99.7% | Rose de Mai (8944), Nerol(1768), Citronellol(74)
| heart        |   1800s |  1.3/92.0/ 6.7 |   24.15ppm |   98.3% | Rose de Mai (8847), Nerol(1749), Citronellol(73)
| late_heart   |   7200s |  1.3/91.8/ 6.9 |   23.22ppm |   93.2% | Rose de Mai (8499), Nerol(1682), Citronellol(69)
| drydown      |  14400s |  1.2/91.7/ 7.1 |   22.01ppm |   87.0% | Rose de Mai (8044), Nerol(1594), Citronellol(65)

Temporal authority: HEURISTIC_UNCALIBRATED; model=dynamic_headspace_exponential_loss_v2; remaining index is not measured evaporation.

### Per-Window Detail

**OPENING** (0.0s) — Uncalibrated loss index:0%
  T:1.3% H:92.0% B:6.7%  Vapor:24.46ppm
  Leaders: Rose de Mai Absolute OAV 8964 | Nerol OAV 1772 | Citronellol OAV 74 | Phenethyl Alcohol OAV 19 | Hexyl Salicylate OAV 2

**TOP** (300.0s) — Uncalibrated loss index:0%
  T:1.3% H:92.0% B:6.7%  Vapor:24.41ppm
  Leaders: Rose de Mai Absolute OAV 8944 | Nerol OAV 1768 | Citronellol OAV 74 | Phenethyl Alcohol OAV 20 | Hexyl Salicylate OAV 2

**HEART** (1800.0s) — Uncalibrated loss index:2%
  T:1.3% H:92.0% B:6.7%  Vapor:24.15ppm
  Leaders: Rose de Mai Absolute OAV 8847 | Nerol OAV 1749 | Citronellol OAV 73 | Phenethyl Alcohol OAV 20 | Hexyl Salicylate OAV 2

**LATE_HEART** (7200.0s) — Uncalibrated loss index:7%
  T:1.3% H:91.8% B:6.9%  Vapor:23.22ppm
  Leaders: Rose de Mai Absolute OAV 8499 | Nerol OAV 1682 | Citronellol OAV 69 | Phenethyl Alcohol OAV 20 | Hexyl Salicylate OAV 2

**DRYDOWN** (14400.0s) — Uncalibrated loss index:13%
  T:1.2% H:91.7% B:7.1%  Vapor:22.01ppm
  Leaders: Rose de Mai Absolute OAV 8044 | Nerol OAV 1594 | Citronellol OAV 65 | Phenethyl Alcohol OAV 20 | Hexyl Salicylate OAV 2

## Perfumer's Assessment

### 1. Character
  Top: Nerol(very strong)
  Heart: Rose de Mai Absolute(very strong) + Citronellol(moderate-strong)
  Base: Hexyl Salicylate(at threshold)

### 2. Opening (0-5min)
  Nerol leads the reported top at OAV 1772 (very strong).
  - Nerol OAV=1772 VP=3.7Pa (floral)
  Total vapor: 24.5 ppm

### 3. Heart (30min-2hr)
  Rose de Mai Absolute OAV=8847 (very strong)
  Nerol OAV=1749 (very strong)
  Citronellol OAV=73 (moderate-strong)
  Phenethyl Alcohol OAV=20 (moderate)
  T:1.3% H:92.0% B:6.7%
  Vapor: 24.1 ppm

### 4. Drydown (2hr-4hr+)
  Base share of active note distribution: 7%
  - Rose de Mai Absolute OAV=8044
  - Nerol OAV=1594
  - Citronellol OAV=65
  - Phenethyl Alcohol OAV=20
  - Hexyl Salicylate OAV=2
  Vapor: 22.0 ppm

### 5. Sillage & Diffusion
  Primary carriers: Rose de Mai Absolute(8964) + Nerol(1772)
  OAV by family: rose84% floral16% salicylate0% fixative0%

### 6. Longevity
  Uncalibrated loss index: 13% over modeled window
  Vapor: 24.5 > 22.0 ppm
  Base @ drydown: 7%
  Absolute skin life: unavailable; calibrated finite-film, vehicle, skin-absorption, and sensory data are required

### 7. Balance
  Pyramid: T:1.3% H:92.0% B:6.7%
  OAV range: 0.00 to 8964 (sigma-log=2.49)
  Wide OAV contrast: Rose de Mai Absolute leads at OAV 8964; lower-OAV materials may be masked.
    sub-threshold: 1

### 8. Flags
  SUB: Dipropylene Glycol OAV=0.00 role=solvent class=STRUCTURAL_OR_FIXATIVE


## Structural OAV Analysis

**Vapor:** 24 ppm  |  **Active:** 5.0%  |  **Perceptible:** 5/6  |  **Unknown:** 0

### OAV Tiers
  **massive** (2): Nerol(1772), Rose de Mai Absolute(8964)
  **strong** (1): Citronellol(74)
  **moderate** (1): Phenethyl Alcohol(19)
  **threshold** (1): Hexyl Salicylate(2)
  **sub** (1): Dipropylene Glycol(0)

### Block Balance
  **Citrus**        0 (0%)
  **Floral**     9057 (100%)
  **Base**          2 (0%)
  **Ratio:** 5742:1 between strongest/weakest block

### Issues
  ! 1 sub-threshold material(s): Dipropylene Glycol
  ! Missing 'very strong' tier (OAV 100-1000)
```
<!-- PIPELINE_ANALYSIS_END -->
