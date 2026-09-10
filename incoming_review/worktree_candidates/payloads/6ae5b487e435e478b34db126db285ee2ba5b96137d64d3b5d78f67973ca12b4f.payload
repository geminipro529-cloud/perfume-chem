# Universal Non-Compressed Perfume Reconstruction Protocol

## A reproducible, brand-agnostic workflow for detailed fragrance reconstruction

**Version:** 1.0  
**Purpose:** Research, comparison, education, formula hypothesis generation, and controlled bench validation.  
**Not a claim of:** access to a proprietary manufacturer formula, authenticated commercial percentages, sensory equivalence, regulatory clearance, or skin-use authorization.

---

## 1. The central idea

A perfume is not adequately represented by:

- a note pyramid;
- a list of allergens;
- a ranked ingredient list;
- a handful of “main” materials;
- an odor-activity-value table;
- or a generic base plus a detachable signature module.

A perfume is a **time-dependent network of independent odor functions**. Some materials provide body. Others provide lift, diffusion, persistence, texture, contrast, transitions, shadows, or tiny recognition cues. Two materials can share the word “musk,” “wood,” “rose,” or “muguet” while performing different jobs. A reconstruction becomes over-compressed when those jobs are silently merged.

The goal of non-compressed reconstruction is therefore not “use as many ingredients as possible.” The goal is:

> Preserve every evidence-backed identity or function that changes the odor’s quality, timing, texture, diffusion, or recognizability, unless evidence shows it is a duplicate, degradation product, contaminant, or technical non-odor component.

A truly minimalist commercial fragrance can have a non-compressed reconstruction with relatively few materials. A complex designer fragrance may require dozens. Ingredient count is an outcome, not a target.

---

## 2. What the improved L’Homme reconstruction actually did

The expanded reconstruction was produced from several layers of evidence and inference. It was not recovered from a hidden exact formula.

### 2.1 Inputs

The working inputs were:

1. An official brand description of the perceptual architecture.
2. A public roster of 70 identities in descending order, with percentages withheld.
3. A 24-row compressed chassis derived from that roster.
4. Explicit substitution and omission ledgers.
5. A heuristic OAV/headspace report with its own warnings and authority limits.
6. Supplier-style knowledge about how distinct materials differ functionally.

The compressed chassis had deliberately removed the ginger, pepper, cardamom, basil, and watery signature into a DPG slot. It also collapsed Habanolide into Galaxolide, Muscenone Delta into Exaltolide, two ionone functions into one material, and two separate green materials into Parmavert. It omitted a long list of trace connectors. Those choices made the formula buildable from a constrained inventory, but they also erased part of the reference’s internal articulation.

### 2.2 Step 1: separate the target from the inventory

The first major correction was conceptual:

- The **target formula** must describe what the evidence suggests is present.
- The **inventory formula** describes what can be built with available stock.
- The **bottle ledger** describes what was physically added.

The compressed version had allowed inventory shortages to reshape the target itself. The expanded version restored target identities first and postponed substitutions.

### 2.3 Step 2: restore the full identity roster

Every one of the 70 public identities was retained as its own target row unless it was clearly a name normalization or technical material. This reversed the sparsity pressure that had reduced the formula to 24 lines.

The restoration was not based on the assumption that all 70 were equally important. It was based on the principle that identity and amount are different questions:

- An identity may be highly certain while its dose is uncertain.
- A trace may be low in concentration but high in recognition value.
- A high-ranked material may be structural rather than characterful.

### 2.4 Step 3: generate a soft rank prior

Because the source disclosed order but not percentages, the rank list was converted into a **soft initial concentration prior** rather than treated as a formula.

For rank `r`, number of materials `N`, and active budget `B`, the initial prior used was:

```text
q_r = B * r^(-p) / sum(k^(-p) for k = 1..N)
```

For the L’Homme exercise:

- `N = 70`
- `B = 4500` raw-volume proxy units during the initial exploration
- `p = 0.70`

This gives approximately:

- rank 1: 490.69 units;
- rank 10: 97.91 units;
- rank 70: 25.07 units.

The exponent was deliberately softer than a Zipf-like `p = 1` curve. A steeper curve would have concentrated too much material into the first few ranks and starved the trace tail. A flatter curve would have made the list nearly uniform.

This prior was never treated as the final dose. It was only a monotonic skeleton.

### 2.5 Step 4: override rank with functional and potency evidence

The rank prior was then corrected material by material.

Examples from the reconstruction illustrate the logic:

- Hedione’s rank prior was about 159 units, but it was raised to 300 because it served as a transmission and diffusion medium across the heart.
- Habanolide’s prior was about 186 and was raised to 220 to preserve a separate radiant musk function instead of hiding it inside Galaxolide.
- Black pepper’s prior was about 34.7, but it was reduced to 8 because its sensory potency and role were trace-like.
- Cardamom’s prior was about 34.2, but it was reduced to 5 for the same reason.
- Damascenone’s prior was about 31.7 raw units, but the final operational dose became 5 units of a 1% stock, or 0.05 active units.
- Aldehyde C-12 MNA and Calone were also moved into 1% trace stocks rather than dosed near their rank-prior values.

This is the critical rule:

> Rank can suggest order. It cannot determine dose without potency, stock form, functional role, analytical response, and sensory context.

### 2.6 Step 5: build functional blocks instead of a note pyramid

The 70 identities were organized into independent systems:

1. Radiant musk architecture.
2. Multi-speed woody, amber, cedar, sandalwood, and vetiver scaffold.
3. Apple-green-water transition system.
4. Split violet, orris, leafy-ionone system.
5. Integrated ginger, pepper, cardamom, nutmeg, coriander, elemi, and basil signature.
6. Muguet and floral transmission system.
7. Tonka, powder, moss, and sweet shadow system.
8. Citrus, ester, aldehyde, mint, and watery micro-connectors.
9. Carrier and stability components.

This block model explained why materials that looked redundant by a crude odor-family classifier were not necessarily redundant. Habanolide and Galaxolide are both musks, but not the same kind of space. Sandalore and Bacdanol are both sandalwood materials, but not the same diffusion or profile. Helional, Bourgeonal, Florol, cis-3-hexenol, and cis-3-hexenyl salicylate all touch “green/floral,” but operate at different times and textures.

### 2.7 Step 6: reintegrate the signature

The spice and watery materials were no longer treated as a removable module. They were integrated into the formula so that:

- ginger linked to citrus and green esters;
- black pepper linked to caryophyllene acetate and woods;
- coriander and elemi linked spice to the citrus opening;
- cardamom cooled the aromatic heart;
- nutmeg and cinnamon extended warm spice;
- basil supplied the anisic green kink;
- Calone and watery materials remained trace accents, not a marine theme.

This repaired the conceptual problem in which the fragrance’s recognizer had been separated from the structure it was supposed to shape.

### 2.8 Step 7: plan operational stock forms

High-impact materials were assigned 10%, 1%, or lower stocks so they could be measured reproducibly. The operational stock was selected after the active target, not before it.

For a target active amount `a` and stock fraction `s`:

```text
raw_stock_amount = a / s
embedded_carrier = raw_stock_amount - a
```

This prevents a common error in which 5 units of a 1% stock is mistaken for 5 units of neat material.

### 2.9 Step 8: reconcile the total and verify arithmetic

The rows were reconciled to exactly 4,500 raw units. Raw stock amount, active amount, embedded carrier, and finished-product dilution were kept separate.

The formula was canonicalized and hashed. The target hash represented only the target formula, not the inventory or live bottle.

### 2.10 Step 9: design omission experiments

The reconstruction was accompanied by controlled omission pairs:

- full formula versus no watery-muguet system;
- full formula versus no apple-green ester system;
- full formula versus no radiant musks;
- full formula versus no secondary wood ladder.

These tests are more informative than asking whether a single material is “detectable.” A material can be individually invisible yet change the blend’s continuity, texture, or identity.

### 2.11 What remains uncertain

The expanded formula remains an evidence-weighted hypothesis. It was not validated by:

- calibrated quantitative GC-FID or GC-MS;
- authentic standards for every peak;
- GC-olfactometry;
- GC×GC resolution of coelutions;
- blinded sensory comparison;
- recombination and omission results;
- or a manufacturer formula.

Therefore, the method produced a more detailed and less destructive reconstruction, but not proof of exact commercial percentages.

---

## 3. Accuracy tiers

Every project should declare its authority tier before formula work begins.

| Tier | Name | What it supports |
|---:|---|---|
| 0 | Concept study | A fragrance inspired by public notes or style. No identity claim. |
| 1 | Note-architecture reconstruction | Major sensory blocks and recognizable notes are represented. |
| 2 | Identity-complete hypothesis | Public, analytical, or documentary identities are preserved, but quantities are inferred. |
| 3 | Semi-quantitative analytical reconstruction | Peak areas, response corrections, and partial standards constrain quantities. |
| 4 | Quantitative analytical reconstruction | Calibrated measurements, retention indices, standards, and mass balance constrain most formula amounts. |
| 5 | Sensory-validated reconstitution | Recombination and omission tests show close similarity under controlled conditions. |
| 6 | Authenticated formula | Authorized formula or equivalent primary documentation is available. |

Do not collapse these tiers into one confidence number. A project can have high identity confidence but low dosage confidence, or high analytical confidence but low sensory confidence.

Recommended authority dimensions are:

1. Reference-version certainty.
2. Material-identity certainty.
3. Quantitative certainty.
4. Matrix and release certainty.
5. Sensory-similarity certainty.
6. Natural-material lot certainty.
7. Safety and regulatory authority.
8. Manufacturability authority.

---

## 4. The universal project state machine

Use a strict state machine so an AI or script cannot jump ahead.

```text
INIT
  -> REFERENCE_LOCKED
  -> EVIDENCE_CAPTURED
  -> IDENTITIES_NORMALIZED
  -> ANALYTICAL_PROFILE_BUILT
  -> FUNCTION_GRAPH_BUILT
  -> QUANTITY_PRIORS_BUILT
  -> TARGET_CANDIDATES_GENERATED
  -> TARGET_ACCEPTED
  -> INVENTORY_MAPPED
  -> BUILD_RECIPE_GENERATED
  -> BATCH_MIXED
  -> SENSORY_EVALUATED
  -> ANALYTICALLY_RECHECKED
  -> REVISED_OR_CLOSED
```

Hard transitions:

- Inventory may not alter the target before `TARGET_ACCEPTED`.
- A bottle diff may not run before the bottle ledger is confirmed.
- A substitution may not be accepted without a loss statement.
- A similarity claim may not be made before controlled sensory evaluation.
- An OAV may not be labeled exact unless concentration and threshold use compatible units and matrix.
- A material may not be deleted merely because a heuristic OAV is below one.

---

# Part I: Evidence and reference control

## 5. Step 0: write the reconstruction contract

Before collecting ingredients, define:

```yaml
project_id: unique_machine_readable_id
brand: brand_name
target_product: exact_product_name
concentration: EDT_or_EDP_or_extrait_or_oil
region: market_region
batch_code: exact_batch_if_available
manufacture_period: estimated_date
reference_scope: fresh_current_or_vintage_or_aged_bottle
reference_samples: list_of_physical_samples
claim_mode: unclaimed_or_similarity_study
output_basis: mass_parts_preferred
finished_vehicle: ethanol_water_or_oil_or_other
accuracy_tier_target: 2_to_5
```

### Why this matters

Brands reformulate. Product names persist while formulas change. A current website, a vintage bottle, and a regional package may describe different materials. An aged bottle also contains oxidation and degradation products that may not belong to the intended fresh formula.

A reconstruction target must therefore be a specific object, not merely a perfume name.

## 6. Step 1: acquire and archive the reference

For each physical reference:

1. Record seller and authenticity evidence.
2. Photograph bottle, box, batch code, and ingredient label.
3. Record purchase date, region, fill level, and storage history.
4. Record apparent age and whether the bottle was previously opened.
5. Create duplicate aliquots where practical.
6. Assign an immutable sample identifier.
7. Hash photographs, chromatograms, and extracted data files.

Suggested files:

```text
references/
  REF_A/
    metadata.json
    bottle_front.jpg
    bottle_back.jpg
    box_label.jpg
    batch_code.jpg
    direct_injection_01.mzML
    headspace_0min_01.mzML
    headspace_120min_01.mzML
```

### Fresh versus aged target

Decide explicitly whether the target is:

- the intended fresh product;
- the current smell of an aged bottle;
- or a historical/vintage reconstruction.

Do not automatically add oxidation products to a fresh target formula.

## 7. Step 2: collect evidence by source class

Create an evidence ledger. Every claim should be one row.

### 7.1 Evidence classes

| Class | Examples | Permitted inference |
|---|---|---|
| Primary formula evidence | Authorized formula, manufacturer production sheet | Identity and amount, subject to version scope |
| Quantitative analytical evidence | Calibrated GC-FID/MS, internal standards, SIDA, qNMR | Amount with stated uncertainty |
| Qualitative analytical evidence | GC-MS, GC×GC, RI, exact mass, GC-O | Identity candidate and odor activity |
| Regulatory/label evidence | Package allergens, INCI, technical additives | Presence or legal-label constraint, not hidden perfume percentage |
| Official sensory evidence | Brand notes and description | Perceptual architecture, not molecular identity by itself |
| Supplier evidence | TDS, SDS, demo formulas, odor description | Grade identity, function, use-level prior |
| Patent/literature evidence | Patents, scientific papers | Candidate identity, mechanism, historical context |
| Secondary reconstruction | Public ranked lists, formula databases | Hypothesis and ordering prior only |
| Community evidence | Reviews, note votes | Sensory vocabulary and reformulation clues only |

### 7.2 Evidence weighting

Use weights as defaults, not truth:

```text
authorized_formula               1.00
calibrated_quantitative_analysis 0.95
semi_quantitative_GC_FID         0.80
qualitative_GC_MS_plus_RI        0.70
GC_O_odor_event                  0.70
supplier_primary_document        0.60
official_brand_description       0.40
package_allergen_presence        0.35
public_ranked_identity_roster     0.30
review_or_note_database           0.10
```

The weight controls uncertainty, not dose. Low-confidence evidence should widen a range or preserve an unknown slot, not automatically reduce the amount.

### 7.3 Evidence ledger schema

```text
evidence_id
source_type
source_authority
source_date
retrieval_date
target_version
claim_type
canonical_identity
raw_source_name
CAS
rank
reported_amount
reported_unit
analytical_method
matrix
confidence
quotation_or_summary
source_hash
```

## 8. Step 3: preserve provenance

Every formula number must be tagged with its derivation:

```text
MEASURED_CALIBRATED
MEASURED_SEMIQUANT
INFERRED_FROM_RANK
INFERRED_FROM_ROLE_PRIOR
INFERRED_FROM_SUPPLIER_RANGE
MANUAL_FUNCTIONAL_ADJUSTMENT
BENCH_SENSORY_UPDATE
SUBSTITUTION
ROUNDING_CORRECTION
```

A formula row without a derivation tag is not reproducible.

---

# Part II: Identity recovery and normalization

## 9. Step 4: normalize names without inventing equivalence

Create a canonical material table with:

```text
material_id
canonical_name
CAS
EC_number
supplier
trade_name
grade
isomer_or_enantiomer
purity
stock_fraction
stock_solvent
density
molecular_weight
natural_or_synthetic
natural_origin
plant_part
extraction_method
chemotype
lot
```

### 9.1 Safe normalization

Safe normalization includes:

- word-order differences;
- punctuation differences;
- recognized spelling variants;
- unambiguous CAS-matched synonyms;
- stock form versus neat identity.

### 9.2 Unsafe normalization

Do not silently equate:

- a generic chemical family with a supplier grade;
- two trade names with different isomer distributions;
- alpha-isomethyl ionone with every methyl-ionone grade;
- one macrocyclic musk with another;
- one vetiver origin with another;
- lavender with lavandin;
- a proprietary replacer with one muguet molecule;
- an essential oil with a single dominant constituent.

When uncertain, preserve both names and mark the equivalence unresolved.

## 10. Step 5: analyze identity evidence instrumentally

### 10.1 Direct-injection GC-FID/MS

Use direct injection of a controlled dilution of the perfume or concentrate to estimate bulk composition.

Best use:

- major and medium-volatility materials;
- mass-balance work;
- quantitative calibration;
- comparison across batches.

Limitations:

- coelution;
- detector response differences;
- thermally labile compounds;
- very volatile compounds;
- nonvolatile components;
- library failure for captives or proprietary blends.

### 10.2 Headspace SPME-GC-MS

Use HS-SPME to characterize what is emitted rather than merely what is present.

Run multiple conditions or optimize them using designed experiments because:

- fiber chemistry changes extraction bias;
- incubation temperature changes partitioning;
- extraction time changes competitive adsorption;
- the substrate changes release;
- ethanol, water, DPG, DEP, TEC, oils, creams, and skin all alter headspace.

Recommended reference contexts:

1. Sealed vial headspace.
2. Freshly dosed blotter.
3. Blotter at multiple timepoints.
4. Skin or a validated skin-mimicking substrate when appropriate.
5. Fabric when the product is designed for clothing or home care.

### 10.3 GC-olfactometry

GC-MS answers “what chemical signal is present?” GC-O helps answer “which eluting region is odor-active?”

Use GC-O to:

- detect potent trace odorants hidden under large peaks;
- distinguish odor-active from odor-inactive components;
- record odor descriptors at retention times;
- prioritize unknowns for identification;
- identify coelutions that matter sensorially.

GC-O is not a substitute for quantitation. It is an orthogonal sensory detector.

### 10.4 GC×GC-TOFMS or equivalent multidimensional GC

Use GC×GC when one-dimensional GC cannot resolve the mixture.

It is especially useful for:

- perfumes with many naturals;
- isomer-rich citrus, herbs, woods, and florals;
- musk and amberwood coelutions;
- trace compounds next to large solvent or terpene peaks;
- non-target fingerprinting;
- counterfeit or batch differentiation.

### 10.5 Retention indices and standards

A mass spectral library match is a candidate, not confirmation.

For stronger identification:

1. Match EI spectrum.
2. Match retention index on the same stationary-phase class.
3. Where possible, match a second column of different polarity.
4. Inject an authentic standard.
5. Use exact mass or characteristic ions where available.
6. Use odor at the GC-O port for odor-active peaks.

NIST EI and retention-index data are appropriate reference tools for this stage.

### 10.6 Chiral GC

Use chiral separation when:

- natural authenticity matters;
- enantiomers have materially different odor;
- a synthetic racemate is being distinguished from a natural source;
- citrus, lavender, mint, rose, woody, or terpene-rich materials are central.

### 10.7 Nonvolatile and difficult materials

GC may underrepresent:

- heavy fixatives;
- dyes and UV filters;
- polymers;
- some antioxidants;
- salts;
- very high-boiling materials;
- certain proprietary blends.

Use LC-MS, HPLC-UV, qNMR, FTIR, density, refractive index, or targeted assays as needed.

## 11. Step 6: perform mass balance

For each sample, track:

```text
known_quantified_mass
known_semiquantified_mass
unidentified_peak_area
nonvolatile_residue
solvent_mass
water_mass
unresolved_mass
```

Useful metrics:

```text
identity_completeness = identified_peaks / total_relevant_peaks
mass_completeness = quantified_fragrance_mass / estimated_total_fragrance_mass
odor_event_completeness = identified_GC_O_events / total_GC_O_events
function_completeness = covered_required_roles / total_required_roles
```

Do not reassign unidentified mass to known materials merely to make the formula total reach 100%.

## 12. Step 7: preserve unknowns as unknowns

When a peak cannot be identified, create a latent slot:

```text
UNKNOWN_017
RI_nonpolar: 1432
RI_polar: 1880
exact_mass: candidate_range
GC_O_descriptor: green_muguet_metallic
headspace_window: 30_to_120_minutes
estimated_amount_range: 0.02_to_0.2_percent
identity_confidence: unresolved
```

This is better than forcing the unknown into “Florol,” “Iso E Super,” or another convenient stock.

---

# Part III: Convert evidence into a structural model

## 13. Step 8: translate official notes into constraints, not ingredients

Marketing notes are perceptual labels. Some are literal materials, some are accords, and some are metaphors.

Examples:

- “Violet leaf” may involve green alcohols, salicylates, watery materials, ionones, and aldehydes.
- “Apple” may involve Verdox-like materials, pear esters, green aldehydes, fruity esters, and musks.
- “Sea air” may involve Calone-like materials, Helional-like materials, ozonic aldehydes, salicylates, and clean musks.
- “Leather” may be an accord of quinolines, smoky materials, saffron-like molecules, woods, ionones, and musks.
- “Oud” may be a natural, a reconstitution, or a woody-animalic accord.

For each official note, define:

1. Literal markers.
2. Body materials.
3. Top or diffusion materials.
4. Bridge materials.
5. Persistence materials.
6. Shadow or realism traces.

The note is considered structurally supported only when the graph contains a plausible path through time.

## 14. Step 9: assign functional roles

Use a multi-label ontology. A material may have several roles.

Recommended roles:

```text
SIGNATURE_MARKER
CORE_BODY
VOLUME
DIFFUSION
TOP_LIFT
HEART_TRANSMISSION
BASE_PERSISTENCE
TEXTURE
ROUNDING
DRYING
COOLING
WARMING
BRIDGE
CONTRAST
REALISM_TRACE
NATURAL_COMPLEXITY
MASKING_OR_SUPPRESSION_RISK
TECHNICAL_SOLVENT
ANTIOXIDANT
COLOR_OR_UV_COMPONENT
```

Time windows should be separate metadata:

```text
opening_0_to_5m
heart_5_to_60m
late_heart_1_to_3h
drydown_3_to_12h
residual_12h_plus
```

## 15. Step 10: build a functional graph

Construct a graph with four node types:

- `MATERIAL`
- `FUNCTION`
- `PERCEPTUAL_NOTE`
- `TIME_WINDOW`

Edges carry contribution weights and evidence sources.

Example:

```text
Fresh Ginger Oil -> SIGNATURE_MARKER
Fresh Ginger Oil -> opening_0_to_5m
SIGNATURE_MARKER -> ginger_note
Coriander Seed Oil -> BRIDGE
BRIDGE -> ginger_note
BRIDGE -> citrus_note
Hedione -> HEART_TRANSMISSION
HEART_TRANSMISSION -> violet_leaf_note
```

Use the graph to find:

- unsupported official notes;
- orphan materials with no defined role;
- abrupt transitions between blocks;
- one material being asked to cover too many independent roles;
- missing persistence or diffusion support;
- excessive role duplication with no functional diversity.

## 16. Step 11: apply the anti-compression gate

Before merging two target identities, test whether they are independently necessary.

### 16.1 Independence criteria

For materials `i` and `j`, mark whether they differ in:

1. Chemical scaffold or isomer profile.
2. Supplier grade or proprietary composition.
3. Volatility or time window.
4. Odor quality.
5. Diffusion behavior.
6. Texture.
7. Substantivity.
8. Matrix partitioning.
9. GC peak or RI evidence.
10. GC-O odor event.
11. Official-note support.
12. Source roster identity.

If several criteria differ, preserve both.

### 16.2 Permitted merges

Merging is usually safe only for:

- exact synonyms with the same CAS and grade;
- word-order changes;
- the same material expressed as neat versus a declared dilution;
- duplicate source entries proven to be the same physical stock;
- analytical artifacts proven to arise from the same material.

### 16.3 Substitution is not merging

If the target material is unavailable, create a substitution map:

```text
target_identity
build_identity
substitution_type
shared_functions
lost_functions
expected_odor_shift
compensating_materials
confidence
```

Never delete the target row. Keep it in the target ledger and create a separate build ledger.

### 16.4 Multi-target substitution warning

If one available material is mapped to multiple target identities, trigger a warning. This was a major source of over-compression in the earlier chassis.

---

# Part IV: Infer quantities without pretending rank is percentage

## 17. Step 12: choose the formula basis

For accurate work, use **mass**, not volume.

Preferred units:

- active mass parts per 1,000 concentrate parts;
- grams for the actual batch;
- wt% in concentrate;
- wt% in finished product.

If volume is used:

```text
mass_i = volume_i * density_i
active_mass_i = mass_i * stock_fraction_i
```

A volume-only formula without density is a screening proxy.

## 18. Step 13: define quantity priors

Every material needs an amount distribution or interval, not merely one guessed number.

Sources of priors:

1. Calibrated analytical amount.
2. Semi-quantitative peak area corrected by response factor.
3. Public rank.
4. Supplier use-level guidance.
5. Public demo formulas and patents.
6. Family-specific formula corpus.
7. Functional block requirement.
8. Sensory dose-response tests.
9. Natural-material composition data.

### 18.1 Rank prior

Use a softened power law when only order is available:

```text
q_r = B * (r + b)^(-p) / sum((k + b)^(-p))
```

Where:

- `B` is the active budget for the ranked materials;
- `b` is an optional offset;
- `p` controls steepness.

For 70 materials and 4,500 parts:

| p | Rank 1 | Rank 10 | Rank 70 | Top-10 share |
|---:|---:|---:|---:|---:|
| 0.50 | 293.49 | 92.81 | 35.08 | 32.7% |
| 0.70 | 490.69 | 97.91 | 25.07 | 43.3% |
| 0.90 | 766.04 | 96.44 | 16.74 | 54.8% |
| 1.10 | 1110.99 | 88.25 | 10.38 | 66.2% |

Do not pick `p` because the resulting formula looks tidy. Fit it using anchors if available. Otherwise generate an ensemble such as `p = 0.55, 0.70, 0.85`.

### 18.2 Role priors

Use broad log-scale priors by role, learned from a curated formula corpus or supplier information.

Conceptually:

```text
log(amount_i) ~ Normal(mu_role_i, sigma_role_i)
```

Structural materials may have broad high-dose priors. High-impact traces may have low-dose priors. Do not derive these solely from odor threshold.

### 18.3 Analytical priors

For a calibrated amount `m_i` with standard error `s_i`:

```text
amount_i ~ LogNormal(log(m_i), sigma_from_measurement)
```

For semi-quantitative GC area:

```text
estimated_mass_i = area_i * response_correction_i * calibration_scale
```

Report uncertainty. Peak-area percent is not automatically formula wt%.

### 18.4 Label and allergen priors

Use labels primarily as presence constraints:

```text
amount_i > trace_lower_bound
```

Do not infer the perfume formula percentage directly from a finished-product allergen declaration unless the legal threshold, natural contribution, finished concentration, and regional rules are explicitly modeled.

## 19. Step 14: assign block budgets

Create active-mass budgets for functional blocks. These are not top/heart/base percentages alone.

Example block schema:

```text
spatial_scaffold
musk_architecture
main_floral_or_aromatic_body
signature_accord
green_fruity_transition
wood_ladder
sweet_or_resinous_shadow
realism_traces
technical_carriers
```

For each block define:

- minimum active mass;
- maximum active mass;
- required identities;
- required role coverage;
- required time-window coverage;
- dominance risk;
- sensory target descriptors.

A block budget prevents rank logic from producing a mathematically orderly but sensorially incoherent formula.

## 20. Step 15: solve a constrained optimization problem

Let `x_i` be active mass of material `i`.

A general objective is:

```text
minimize
    lambda_anchor * analytical_anchor_loss
  + lambda_rank   * rank_order_loss
  + lambda_block  * block_budget_loss
  + lambda_role   * role_coverage_loss
  + lambda_time   * temporal_profile_loss
  + lambda_note   * official_note_loss
  + lambda_round  * manufacturability_loss
  + lambda_safe   * safety_constraint_loss
```

Subject to:

```text
sum(x_i) = active_budget
lower_i <= x_i <= upper_i
required_identity_i => x_i > 0
block_min_b <= sum(M_ib * x_i) <= block_max_b
```

### 20.1 Rank-order loss

Use a soft pairwise constraint:

```text
L_rank = sum(log(1 + exp(-(log(x_i) - log(x_j)) / tau)))
```

for pairs where source rank says `i` precedes `j`.

This allows potency-based exceptions without discarding the source order entirely.

### 20.2 Analytical anchor loss

```text
L_anchor = sum(w_i * (log(x_i) - log(measured_i))^2)
```

### 20.3 Block loss

```text
L_block = sum_b w_b * (sum_i M_ib*x_i - target_b)^2
```

### 20.4 Functional coverage loss

Penalize missing roles, not just missing mass:

```text
L_role = sum_required_roles max(0, role_floor_r - contribution_r)^2
```

### 20.5 Avoid sparsity penalties

Do not use generic L1 regularization, top-k pruning, or “remove all low-impact materials” logic for a non-compressed target. Those methods are designed to create sparse solutions and will systematically erase trace connectors.

If regularization is needed, use:

- smoothness across rank;
- block-budget regularization;
- uncertainty penalties;
- or group-aware minimum coverage.

## 21. Step 16: model uncertainty with an ensemble

Never produce only one candidate when amount evidence is weak.

Generate candidate families:

```text
CANDIDATE_FLAT_RANK
CANDIDATE_MEDIUM_RANK
CANDIDATE_STEEP_RANK
CANDIDATE_GREEN_HIGH
CANDIDATE_MUSK_HIGH
CANDIDATE_SIGNATURE_HIGH
```

Keep all other variables controlled. Bench testing should discriminate among hypotheses.

A Bayesian formulation is even better:

```text
P(x | evidence) proportional to
    P(rank | x)
  * P(analytical_data | x)
  * P(official_notes | x)
  * P(sensory_data | x)
  * P(x | role_and_material_priors)
```

The output should be posterior ranges, not only point estimates.

---

# Part V: Convert the target into a measurable formula

## 22. Step 17: choose stock dilutions after active targets

For each material, choose the strongest stock that produces a measurable raw amount.

Example algorithm:

```python
for fraction in [1.0, 0.5, 0.2, 0.1, 0.05, 0.01, 0.001]:
    raw = target_active / fraction
    if minimum_measurable <= raw <= maximum_convenient:
        choose fraction
        break
```

Selection criteria:

- pipette or balance resolution;
- material viscosity;
- solvent compatibility;
- solubility;
- oxidation risk;
- carrier load;
- expected storage stability;
- cross-contamination risk.

## 23. Step 18: track three layers

### 23.1 Active target

Neat-equivalent mass of each intended odorant.

### 23.2 Weighable stock recipe

Actual stock amount and embedded carrier.

### 23.3 Finished product

Concentrate, ethanol, water, oil, UV filters, colors, and other matrix components.

Do not mix these layers in one “amount” column.

## 24. Step 19: reconcile carrier load

Calculate:

```text
raw_stock_i = active_i / stock_fraction_i
embedded_carrier_i = raw_stock_i - active_i
```

Then:

```text
total_raw_stock = sum(raw_stock_i)
neutral_carrier_available = concentrate_total - total_raw_stock - deliberate_technical_materials
```

If neutral carrier becomes negative:

- strengthen some trace stocks;
- reduce the active budget;
- increase total concentrate mass;
- or redesign the stock plan.

Do not silently scale only part of the formula.

## 25. Step 20: rounding and integer feasibility

Optimize in continuous active mass first. Round only after stock planning.

After rounding:

1. Recalculate active amounts.
2. Recalculate block totals.
3. Recalculate carrier load.
4. Recalculate the total.
5. Assign the rounding correction to a deliberate carrier or robust structural material, not a potent trace.
6. Re-hash the formula.

For very small batches, use serial dilutions or gravimetric microstocks rather than rounding a trace to zero.

---

# Part VI: Target, inventory, and bottle ledgers

## 26. The four-ledger rule

Maintain these separately:

### 26.1 `EVIDENCE_HASH`

All source claims and analytical files.

### 26.2 `TARGET_RECON_HASH`

The accepted evidence-faithful target formula.

### 26.3 `INVENTORY_HASH`

Owned stocks, suppliers, grades, lots, dilutions, carriers, densities, and availability.

### 26.4 `BOTTLE_HASH`

Every physically added amount, with timestamp and operator confirmation.

Optional additional hashes:

```text
CONFIG_HASH
SUBSTITUTION_HASH
SENSORY_HASH
ANALYTICAL_RUN_HASH
BUILD_RECIPE_HASH
```

## 27. Target-to-inventory mapping

Only after the target is accepted:

1. Exact match.
2. Same identity, different stock fraction.
3. Same identity, different supplier grade.
4. Same natural, different origin or chemotype.
5. Close functional substitute.
6. Partial substitute requiring a small accord.
7. Unresolved or unavailable.

Each non-exact map needs a loss statement.

## 28. Bottle ledger requirements

Every addition should record:

```text
timestamp
material_identity
supplier_and_grade
lot
stock_fraction
stock_solvent
mass_or_volume_added
active_amount
operator
measurement_device
confirmation_status
reason_for_addition
sample_or_bottle_id
```

An AI should never infer that “owned” means “added.”

## 29. Diff logic

The correct diff is:

```text
TARGET minus BOTTLE
```

Inventory is used only to explain whether missing target rows are buildable.

Diff categories:

```text
TARGET_PRESENT_BOTTLE_MATCHED
TARGET_PRESENT_BOTTLE_AMOUNT_MISMATCH
TARGET_PRESENT_BOTTLE_UNCONFIRMED
TARGET_MISSING_FROM_BOTTLE_AVAILABLE_IN_INVENTORY
TARGET_MISSING_FROM_BOTTLE_UNAVAILABLE
BOTTLE_EXTRA_STYLISTIC
BOTTLE_EXTRA_RESCUE
BOTTLE_UNKNOWN_AMOUNT
NONEXACT_SUBSTITUTION
```

---

# Part VII: Mixing and bench validation

## 30. Step 21: build small controlled candidates

Do not commit the entire batch when uncertainty is high.

Recommended sequence:

1. Prepare the active stocks.
2. Build 1–5 mL concentrate candidates by mass.
3. Dilute all candidates to the same finished concentration.
4. Use the same ethanol/water or oil matrix as the reference category.
5. Mature under identical conditions.
6. Blind-code the samples.

## 31. Step 22: standardize presentation

Control:

- dose on blotter;
- blotter type;
- application geometry;
- room temperature and airflow;
- reference dose;
- evaluation order;
- timepoints;
- assessor rest;
- sample randomization.

Do not compare one fragrance from the bottle neck and another from a blotter.

## 32. Step 23: build a sensory lexicon

Create descriptors from:

- official brand language;
- expert evaluation of the reference;
- GC-O descriptors;
- supplier descriptions;
- observed differences between candidate and reference.

Descriptors should be specific enough to guide changes:

Bad:

```text
nice
strong
complex
masculine
```

Better:

```text
pepper sparkle
watery green hinge
violet-leaf metallic dryness
muguet volume
ginger bite
clean macrocyclic trail
cedar splinter
powdered tonka shadow
```

## 33. Step 24: evaluate across time

A general fine-fragrance schedule:

```text
0 minutes
5 minutes
15 or 30 minutes
1 hour
2 hours
4 hours
8 hours
24 hours if relevant
```

Adjust for product type. Colognes need dense early sampling. Extraits, attars, oud, and heavy ambers need longer observation.

## 34. Step 25: use trained or at least calibrated assessors

Use a consistent panel when possible. Train descriptors and reference anchors. ISO sensory-profile and assessor-training standards are useful frameworks.

Record:

- attribute intensity;
- global similarity;
- difference direction;
- diffusion;
- texture;
- recognizable signature;
- off-notes;
- confidence.

## 35. Step 26: use omission and addition experiments

### 35.1 Omission test

Remove one material or functional block while keeping total mass constant with neutral carrier.

Question:

> Does the omission create a reproducible difference from the full model, and which descriptor changes?

### 35.2 Addition test

Add the suspected trace to a controlled base.

Question:

> Does the addition restore a missing reference quality without creating a new obvious note?

### 35.3 Dose-response test

Use at least three levels:

```text
0.5x
1.0x
1.5x
```

For potent traces use logarithmic or finer steps.

## 36. Step 27: control interactions

Odor mixtures are not always additive. Materials can suppress, enhance, mask, or create a configural percept. Therefore:

- do not delete a material solely because it is below a published threshold;
- do not assume two OAVs add linearly;
- do not assume a high-OAV material will smell strongest in the blend;
- test important binary or small-block interactions;
- measure thresholds in a relevant matrix when possible.

## 37. Step 28: optimize with designed experiments

Use different designs at different stages.

### Screening stage

Fractional factorial or Plackett-Burman style designs can identify influential blocks.

### Accord-ratio stage

Mixture designs or simplex-lattice designs are appropriate when the total of an accord is fixed and internal ratios vary.

### Local refinement

Response-surface methods or Bayesian optimization can search a small neighborhood.

### Hard limit

An optimizer may only vary:

- approved target materials;
- approved dose ranges;
- approved substitution candidates.

It may not invent materials or delete required identities without a gate review.

---

# Part VIII: Analytical and sensory model integration

## 38. OAV: correct use and misuse

For a pure material in a defined matrix:

```text
OAV_i = concentration_i / odor_threshold_i
```

This is meaningful only when:

- units match;
- concentration is known;
- threshold matrix is relevant;
- threshold method is known;
- material identity and purity are known;
- enantiomer and isomer effects are considered where important.

### OAV should be used for

- screening potentially important traces;
- prioritizing GC-O or omission work;
- comparing candidates under the same assumptions;
- identifying gross anomalies.

### OAV should not be used for

- declaring sensory similarity;
- deleting all rows with OAV below one;
- treating natural oils as single molecules;
- predicting exact dominance in a mixture;
- predicting skin longevity from a concentrate-only model;
- replacing bench evaluation.

## 39. Headspace modeling

A simple relative headspace model may use:

```text
H_i(t) proportional to x_i * gamma_i * P_sat_i * K_release_i(matrix) * exp(-k_i*t)
```

But every term can be uncertain. Treat it as a diagnostic model until calibrated.

Improve it by fitting to measured headspace data at multiple timepoints and matrices.

## 40. Matrix effects

The same concentrate can smell different in:

- ethanol-water;
- DPG;
- DEP;
- TEC;
- oil;
- silicone;
- cream;
- detergent;
- fabric;
- skin.

Therefore, formula matching and performance matching are separate tasks.

## 41. Skin and inter-person variation

Skin headspace varies by person. A fragrance may diffuse differently because of skin chemistry, temperature, application, and endogenous volatiles.

Use blotter as the main controlled substrate and skin as a later validation substrate. Do not infer universal skin life from one person.

---

# Part IX: Natural materials and proprietary materials

## 42. Natural-material handling

Every natural complex substance should have:

```text
botanical_name
plant_part
origin
extraction_method
chemotype
supplier
lot
GC_profile
major_constituents
allergen_profile
oxidation_status
```

Do not assume that two lots of the same oil are interchangeable. Chemotype and origin can produce large compositional differences.

## 43. Parent natural versus constituent peaks

Avoid double counting.

If the formula uses a whole natural oil, the analytical chromatogram will show its constituents. The reconstruction may represent it as:

- a whole-oil row;
- a reconstitution of constituents;
- or a hybrid.

Whichever model is chosen, document it. Do not add the whole oil and then independently add every detected constituent unless evidence supports both.

## 44. Captives and proprietary blends

When a proprietary material is suspected:

1. Keep an unresolved target slot.
2. Record RI, mass spectrum, exact mass, GC-O odor, and time window.
3. Search patents and supplier literature.
4. Test multiple purchasable candidates.
5. Use a small accord if one material cannot cover all functions.
6. Keep the substitution separate from the target.

The correct target may remain partially unbuildable. That is preferable to false certainty.

---

# Part X: Adapt the method to perfume family

## 45. Citrus cologne and fresh aromatic

Priorities:

- exact citrus species and processing;
- terpene and aldehyde balance;
- oxidation state;
- herbal bridges;
- lightweight musks and woods;
- very early headspace sampling.

Common compression failure:

> Replacing the whole citrus architecture with limonene plus bergamot.

## 46. Fougère and aromatic lavender

Priorities:

- lavender versus lavandin versus synthetic linalool/linalyl acetate;
- coumarin and moss axis;
- camphoraceous lift;
- herb and spice traces;
- woody and musk modernization.

Common compression failure:

> Calling linalool, lavender oil, lavandin, and ethyl linalool one “lavender” line.

## 47. Chypre

Priorities:

- bergamot quality;
- patchouli fractions;
- oakmoss or moss replacer system;
- labdanum/resin balance;
- floral or fruity heart;
- dry woody structure.

Common compression failure:

> Replacing the chypre axis with patchouli plus Evernyl without preserving citrus, floral, resinous, and textural transitions.

## 48. Rose and floral bouquets

Priorities:

- body alcohols;
- citronellol/geraniol/nerol balance;
- oxides and aldehydes;
- damascones and damascenone;
- green and spicy realism;
- floral fixatives and musks.

Common compression failure:

> Replacing a multidimensional rose with phenethyl alcohol and geraniol.

## 49. White florals

Priorities:

- indolic and animalic traces;
- methyl anthranilate and orange-flower facets;
- salicylates;
- lactones;
- benzyl esters;
- green top;
- dense floral body and diffusion.

Common compression failure:

> Removing traces because they appear “dirty” in isolation, leaving a clean but hollow floral.

## 50. Gourmand and amber

Priorities:

- separate vanilla, caramel, almond, powder, balsam, resin, spice, and wood functions;
- balance sweetness against diffusion and dryness;
- preserve trace burnt, toasted, smoky, or animalic realism.

Common compression failure:

> Using vanillin, ethyl maltol, and Ambrox as a complete amber-gourmand.

## 51. Woody amber and modern designer woods

Priorities:

- multiple wood speeds and textures;
- dry versus creamy woods;
- ambergris materials;
- radiant musks;
- floral-air transmission;
- trace spice and green lift.

Common compression failure:

> Treating Iso E Super, Ambrox, Cashmeran, Cedramber, Norlimbanol, Bacdanol, and sandalwood materials as interchangeable “woody amber.”

## 52. Leather, smoke, incense, and oud

Priorities:

- phenolic, smoky, tarry, saffron, quinoline, animalic, resinous, and woody subfacets;
- very potent traces;
- natural variability;
- long-time evaluation;
- GC-O for odor-active traces.

Common compression failure:

> One leather base or one oud base replacing the complete accord.

## 53. Aquatic and ozonic

Priorities:

- watery, melon, mineral, seaweed, green, ozonic, aldehydic, floral, and musk facets;
- trace-dose precision;
- configural effects;
- suppression and harshness risk.

Common compression failure:

> Treating Calone as the whole aquatic accord.

## 54. Musk-centered and minimalist perfumes

Priorities:

- musk anosmia variation;
- separate metallic, laundry, skin, powdery, fruity, woody, and animalic musk profiles;
- texture and diffusion;
- subtle floral and woody carriers.

Common compression failure:

> Replacing several musks with whichever musk is available.

## 55. Naturals-heavy artisanal perfumes

Priorities:

- lot-specific analysis;
- nonvolatile resin and absolute components;
- oxidation and aging;
- chiral and chemotype information;
- broader uncertainty ranges.

Common compression failure:

> Treating a natural name as a fixed composition.

## 56. Captive-heavy modern perfumes

Priorities:

- unresolved analytical slots;
- exact mass and RI;
- patents and supplier documents;
- functional substitute ensembles;
- avoiding false identity claims.

Common compression failure:

> Forcing every unknown peak into the nearest catalog material.

## 57. Oil perfumes and attars

Priorities:

- matrix-specific release;
- very long time windows;
- heavy naturals and fixatives;
- skin interaction;
- headspace measured in oil, not borrowed from ethanol data.

Common compression failure:

> Applying an ethanol fragrance’s volatility assumptions to an oil matrix.

---

# Part XI: AI orchestration and scripting

## 58. AI role boundaries

AI is useful for:

- source discovery;
- extracting structured claims;
- name normalization suggestions;
- classifying functions;
- proposing candidate blocks;
- generating uncertainty-aware hypotheses;
- explaining substitutions;
- planning experiments;
- summarizing results.

AI should not be trusted alone for:

- arithmetic;
- chemical identity confirmation;
- exact percentages from hidden data;
- safety clearance;
- stock reconciliation;
- live bottle state;
- sensory equivalence.

Use deterministic scripts for numbers, hashes, totals, and diffs.

## 59. Recommended agent architecture

### 59.1 Research agent

Output: evidence JSON only.

### 59.2 Identity agent

Output: canonical names, CAS candidates, unresolved conflicts.

### 59.3 Analytical agent

Output: peak table with spectrum match, RI match, quantitation status, and GC-O status.

### 59.4 Functional agent

Output: material-to-role graph.

### 59.5 Formula inference agent

Output: priors, bounds, and rationale. No final arithmetic.

### 59.6 Deterministic optimizer

Output: candidate formulas satisfying constraints.

### 59.7 Validation agent

Checks:

- total;
- stock fractions;
- carrier load;
- missing identities;
- multi-target substitutions;
- unsupported claims;
- hash consistency.

### 59.8 Sensory experiment agent

Output: blind trial plan and score sheet.

## 60. Prompt contract for an AI

```text
You are constructing a target reconstruction, not an inventory-constrained build.

Hard rules:
1. Preserve target identities separately until an equivalence gate passes.
2. Do not use inventory to alter the target formula.
3. Every identity and amount requires a provenance tag.
4. A ranked list supplies order evidence, not percentages.
5. Official notes constrain perceptual blocks, not exact molecules.
6. Do not delete trace materials from heuristic OAV alone.
7. Keep unresolved peaks as unresolved slots.
8. Output active amount, stock fraction, raw stock amount, and carrier separately.
9. Do not claim sensory similarity without blind bench evidence.
10. Arithmetic and hashes must be produced by deterministic scripts.
```

## 61. Recommended repository layout

```text
project/
  project.json
  references/
  evidence/
    evidence.csv
    sources/
  analytical/
    raw/
    processed/
    peak_table.csv
    gc_o_events.csv
  materials/
    canonical_materials.csv
    aliases.csv
  target/
    ranked_roster.csv
    function_graph.json
    priors.csv
    target_formula.csv
    target_manifest.json
  inventory/
    inventory.csv
  build/
    substitution_mapping.csv
    build_formula.csv
  bottle/
    bottle_ledger.csv
  sensory/
    lexicon.csv
    trial_plan.csv
    observations.csv
  scripts/
  reports/
```

## 62. Script order

```text
01_lock_reference.py
02_ingest_evidence.py
03_normalize_identities.py
04_parse_analytical_data.py
05_build_function_graph.py
06_generate_quantity_priors.py
07_optimize_target_candidates.py
08_plan_stock_dilutions.py
09_validate_and_hash_target.py
10_map_inventory.py
11_generate_build_recipe.py
12_diff_bottle.py
13_generate_sensory_trials.py
14_ingest_sensory_results.py
15_update_candidate_posterior.py
16_close_release_report.py
```

## 63. Minimal pseudocode

```python
project = lock_reference(project_config)
evidence = ingest_and_hash_sources(project)
identities = normalize_without_merging(evidence)
analytical = parse_gc_and_gc_o(project, identities)
roles = build_function_graph(identities, analytical, official_notes)

rank_candidates = [0.55, 0.70, 0.85]
formula_candidates = []
for exponent in rank_candidates:
    prior = build_rank_prior(identities, exponent)
    prior = update_with_measurements(prior, analytical)
    prior = apply_functional_bounds(prior, roles)
    target = constrained_optimize(prior, project.constraints)
    assert anti_compression_gate(target)
    stock_plan = choose_measurable_stocks(target)
    validated = reconcile_carriers_and_rounding(stock_plan)
    formula_candidates.append(hash_target(validated))

trials = design_blind_recombination_and_omission_tests(formula_candidates)
results = run_and_record_trials(trials)
posterior = update_formula_ranges(formula_candidates, results)

accepted_target = select_candidate(posterior)
inventory_map = map_inventory_after_target_lock(accepted_target)
build = generate_build_recipe(inventory_map)
```

---

# Part XII: Failure modes and hard gates

## 64. Failure: inventory-first design

Symptom:

> The formula contains only materials currently owned.

Consequence:

The target changes before it is understood.

Gate:

> Target formula must be accepted before inventory mapping.

## 65. Failure: rank equals percentage

Symptom:

> Rank 1 receives 20%, rank 2 receives 10%, and so on.

Consequence:

Detector response, potency, stock dilution, and trace roles are ignored.

Gate:

> Rank creates a soft prior only.

## 66. Failure: one material covers several identities

Symptom:

> Galaxolide includes Habanolide; Exaltolide includes Muscenone; one ionone covers two proprietary grades.

Consequence:

Texture, diffusion, and timing collapse.

Gate:

> Multi-target substitutions require explicit approval and a loss statement.

## 67. Failure: note pyramid as formula

Symptom:

> Ginger, violet leaf, cedar, and tonka are selected as four materials.

Consequence:

Bridges, diffusion, musks, and hidden accords disappear.

Gate:

> Every note must be expanded into marker, body, bridge, persistence, and realism roles.

## 68. Failure: OAV tyranny

Symptom:

> Anything below OAV 1 is deleted; the highest OAV is called the dominant note.

Consequence:

Mixture interactions, texture, matrix effects, and trace identity are ignored.

Gate:

> OAV is diagnostic only. Omission tests decide structural relevance.

## 69. Failure: natural oil treated as one molecule

Symptom:

> One molecular weight, vapor pressure, and threshold represent an essential oil.

Consequence:

Composite behavior and lot variation are hidden.

Gate:

> Natural materials carry batch fingerprints and composite uncertainty.

## 70. Failure: mass and volume mixed

Symptom:

> Microlitres, active microlitres, ppm w/w, and finished-product percentage are used interchangeably.

Consequence:

The formula cannot be reproduced.

Gate:

> Preferred basis is mass. Every conversion records density and stock fraction.

## 71. Failure: unlogged live additions

Symptom:

> The operator remembers adding “some cardamom.”

Consequence:

The bottle cannot be diffed or repaired reliably.

Gate:

> No addition without an immediate bottle-ledger entry.

## 72. Failure: premature cost or safety reformulation

Symptom:

> Expensive, unavailable, or restricted materials disappear from the target.

Consequence:

The target ceases to describe the reference.

Gate:

> Historical/evidence target, compliant target, and production build are separate versions.

## 73. Failure: one scalar confidence score

Symptom:

> “The formula is 82% confident.”

Consequence:

High inventory certainty can hide low quantitative or sensory certainty.

Gate:

> Report a vector of authority dimensions.

---

# Part XIII: Acceptance checklist

## 74. Reference gate

- Exact product, concentration, region, and batch recorded.
- Fresh versus aged target declared.
- Physical samples archived.
- Source files hashed.

## 75. Evidence gate

- Every claim has source and authority.
- Official notes are marked semantic only.
- Labels are not treated as hidden percentages.
- Secondary rosters are marked unquantified unless proven otherwise.

## 76. Identity gate

- Names canonicalized.
- CAS and grade conflicts preserved.
- Naturals include origin, lot, and chemotype.
- Unknown peaks remain explicit.
- No unapproved multi-target merge.

## 77. Quantity gate

- Active mass basis declared.
- Rank exponent and prior disclosed.
- Priors, bounds, and manual multipliers recorded.
- Analytical response corrections recorded.
- Trace stocks selected after active targets.
- Carrier load reconciled.

## 78. Structural gate

- Every official note has a functional path.
- Every required function is covered.
- Multiple materials within a family have distinct roles.
- Transitions between blocks are represented.
- Signature materials are integrated where the reference requires them.

## 79. Formula gate

- Total equals the declared concentrate mass.
- Raw, active, and carrier amounts are separate.
- Formula is canonically hashed.
- Target, inventory, build, and bottle remain separate.

## 80. Validation gate

- Reference and candidates are matched in concentration and matrix.
- Blind codes are used.
- Timepoints are standardized.
- Omission tests cover major uncertainties.
- Sensory observations are recorded, not remembered.
- Similarity claims match the evidence tier.

## 81. Safety gate

- Current IFRA standards checked for the intended product category.
- Local cosmetic regulations checked.
- Supplier SDS and specifications reviewed.
- Allergen and restricted-natural contributions aggregated.
- Skin use is withheld until safety review is complete.

---

# Part XIV: Tool stack

## 82. Low-budget, instrument-free workflow

Tools:

- official brand pages and archived packaging;
- public identity rosters;
- supplier TDS/SDS and demo formulas;
- NIST and public chemical references;
- Python or another deterministic scripting language;
- precision scale and serial dilutions;
- blind-coded blotter testing.

Expected authority:

- Tier 1 to Tier 2, occasionally early Tier 3 with strong documentary evidence.

## 83. Outsourced analytical workflow

Add:

- direct-injection GC-MS and GC-FID;
- HS-SPME-GC-MS at several timepoints;
- authentic standards for key materials;
- nonvolatile residue and density measurements.

Expected authority:

- Tier 3 to Tier 4 for identified/quantified portions.

## 84. High-end analytical workflow

Add:

- GC×GC-TOFMS or high-resolution GC-MS;
- GC-O/AEDA;
- stable-isotope or internal-standard quantitation;
- chiral GC;
- LC-MS or qNMR;
- trained sensory panel;
- recombination and omission testing.

Expected authority:

- Tier 4 to Tier 5.

---

# Part XV: Recommended scientific and standards basis

The workflow is consistent with the following general bodies of evidence:

1. NIST EI mass spectral and gas-chromatographic retention-index databases for compound identification support.
2. HS-SPME-GC-MS studies showing that extraction conditions, substrate, cosmetic base, and skin affect observed fragrance profiles.
3. GC-O studies showing that odor-active trace compounds can be distinguished from chemically abundant but less odor-relevant compounds.
4. GC×GC method-development work showing the value of higher peak capacity and dual-detection quantitation for complex fragrances.
5. Sensomics workflows using identification, quantitation, OAV, recombination, and omission as a sequence rather than treating OAV as a final answer.
6. ISO 13299 sensory-profile guidance and ISO 8586 assessor-training guidance.
7. ASTM E679-style forced-choice threshold methodology when threshold work is required.
8. IFRA standards, CosIng, ECHA, and applicable local regulations for the safety/compliance layer.

Selected references:

- Gherghel S. et al. Development of a HS-SPME/GC-MS method for VOC analysis from fabrics and commercial perfumes. *Forensic Science International* 290 (2018), 207–218. DOI: 10.1016/j.forsciint.2018.07.015.
- Duffy E., Albero G., Morrin A. Headspace SPME-GC-MS analysis of scent profiles from human skin. *Cosmetics* 5 (2018), 62. DOI: 10.3390/cosmetics5040062.
- Di Nicolantonio L. et al. Interactions between fragrances and cosmetic bases measured by SPME-GC/MS and expert evaluation. *Cosmetics* 9 (2022), 70. DOI: 10.3390/cosmetics9040070.
- Bartsch J., Uhde E., Salthammer T. Analysis of odor compounds from scented consumer products by GC-MS and GC-O. *Analytica Chimica Acta* 904 (2016), 98–106. DOI: 10.1016/j.aca.2015.11.031.
- Belhassen E. et al. Quantification of fragrance allergens using comprehensive two-dimensional GC-QMS/FID. *Flavour and Fragrance Journal* 33 (2018), 63–74. DOI: 10.1002/ffj.3416.
- NIST GC Retention Index Database and NIST/EPA/NIH EI Mass Spectral Library.
- ISO 13299:2016, sensory profiling.
- ISO 8586:2023, selection and training of sensory assessors.
- ASTM E679-19, forced-choice ascending concentration threshold method.

---

## Final operating rule

A detailed reconstruction should be produced by the following chain:

```text
reference lock
-> evidence ledger
-> identity normalization
-> analytical identification
-> independent functional graph
-> anti-compression gate
-> uncertainty-aware quantity priors
-> constrained target optimization
-> stock and carrier reconciliation
-> target hash
-> inventory mapping
-> controlled build
-> blind time-course comparison
-> omission and recombination
-> iterative correction
```

The most important design decision is not the rank exponent, OAV equation, or optimizer. It is the refusal to let convenience erase independent odor functions before they have been tested.


---

# DNA-Preserving Structural Chassis Protocol

## Version 2.0

**Purpose:** derive modular, flanker-capable structural chassis from a complete non-compressed reconstruction without amputating the parent perfume's recognizers.

**Not a claim of:** access to a proprietary formula, exact commercial percentages, sensory equivalence, safety clearance, or authorization to market a derivative under a brand name.

---

## 1. Core principle

A structural chassis must be derived *from* a complete parent reconstruction. It must not be created by deleting every ingredient that looks thematic and filling the hole with DPG.

Let the complete target formula be \(T\). Split it into:

\[
T = C + M_p
\]

where:

- \(C\) is the fixed DNA-preserving core;
- \(M_p\) is the parent module;
- row-by-row recombination of \(C + M_p\) must reproduce \(T\) exactly.

An alternative flanker is:

\[
F_j = C + M_j
\]

where \(M_j\) has the same raw socket size as \(M_p\), but may contain a different accord. The alternative module must pass anchor, interface, carrier, temporal, family-drift, and sensory gates.

A chassis is therefore **not** a generic base. It is the parent perfume with enough of each recognizer left in the core that the identity remains perceptible before the module is inserted.

---

## 2. Why naive modularization fails

The naive method usually performs these steps:

1. Identify the marketed top or signature notes.
2. remove all of them;
3. replace their volume with neutral carrier;
4. call the remainder the DNA;
5. insert a different note at the same raw volume.

This fails because equal raw volume is not equal to:

- active mass;
- vapor output;
- odor intensity;
- time behavior;
- polarity;
- carrier load;
- sweetness;
- dryness;
- diffusion;
- or receptor interaction.

It also fails because marketed notes often belong to a larger interface network. Removing cardamom may also remove the reason the lavender, citrus, coumarin, and woods read as one object. Removing ginger may expose a generic clean wood base. Removing iris may erase the polished soap identity even when every musk remains.

---

## 3. Required inputs

No chassis partition should begin without:

1. a locked reference version;
2. a complete target reconstruction;
3. target rows with active and stock amounts;
4. functional roles;
5. temporal roles;
6. recognizer importance;
7. functional graph edges;
8. source confidence;
9. uncertainty ranges;
10. a declared module size objective.

The target, inventory, and bottle remain separate ledgers.

---

## 4. Five-layer chassis architecture

### 4.1 Immutable structural core

Materials that mainly establish persistent volume, space, texture, and family structure.

Typical examples:

- structural musks;
- transparent woods;
- base woods;
- broad floral transmitters;
- non-thematic fixatives;
- technical materials.

These usually remain 80-100% in the core.

### 4.2 Protected recognizer floor

Recognizers cannot all be moved into the socket. A minimum remains in the core.

For target amount \(T_i\), core amount \(C_i\), and recognizer floor \(f_i\):

\[
C_i \ge f_iT_i
\]

Example starting hypotheses:

- principal signature recognizer: retain 30-60%;
- important secondary recognizer: retain 50-80%;
- persistent family anchor: retain 75-100%;
- stylistic accent: retain 10-40%.

These are priors, not universal rules. Determine them by omission testing.

### 4.3 Interface ring

Materials that connect the mobile accord to the fixed core. They commonly include:

- esters;
- muguet materials;
- ionones;
- salicylates;
- aromatic alcohols;
- minor citrus;
- green materials;
- floral transmitters;
- diffusive woods;
- light musks.

Interface materials can be split between core and module. A module that lacks interfaces will smell pasted on.

### 4.4 Accord socket

The socket is the mobile part of the target. It must have:

- exact raw total;
- declared active total;
- carrier budget;
- role coverage;
- protected-anchor requirements;
- family caps;
- and temporal limits.

It is not necessarily 100 or 300 µL. Size should be inferred from the amount of movable target material and the scale at which alternative accords can be integrated without destabilizing the core.

### 4.5 Compensation vector

A replacement accord may differ from the parent in volatility, sweetness, density, or tenacity. The module must include its own compensation.

Examples:

- heavy immortelle may require aromatic lift and sweetness reduction;
- bright citrus may require persistence and heart attachment;
- dense oud may require air, dry woods, and a smaller active load;
- marine material may require green-floral interfaces and strict melon caps.

Do not repeatedly rewrite the fixed core to rescue every module. Put compensation inside the socket.

---

## 5. Node classification

Every target row receives one class:

- `IMMUTABLE_CORE`
- `PROTECTED_ANCHOR`
- `INTERFACE_RING`
- `MODULE_MOBILE`
- `TECHNICAL`
- `CARRIER`
- `UNKNOWN_PROTECTED`
- `UNKNOWN_MODULE_CANDIDATE`

Suggested feature vector:

```json
{
  "identity": "",
  "target_raw": 0,
  "target_active": 0,
  "recognizer_score": 0.0,
  "structural_score": 0.0,
  "interface_score": 0.0,
  "mobility_score": 0.0,
  "temporal_windows": [],
  "functional_roles": [],
  "evidence_confidence": 0.0,
  "quantity_confidence": 0.0
}
```

A material may have high recognizer and high interface scores. Such a material is normally split, not moved wholesale.

---

## 6. Partition algorithm

### Step 1: preserve technical and carrier accounting

Technical additives remain fixed unless the alternative module changes oxidation or solubility requirements. Carrier may be split only as an explicit balancing component.

### Step 2: retain structural floors

For structural material \(i\):

\[
C_i \ge s_iT_i
\]

Typical initial \(s_i\): 0.80 to 1.00.

### Step 3: retain recognizer floors

For recognizer \(i\):

\[
C_i \ge f_iT_i
\]

### Step 4: allocate interface material

Move only enough interface material to allow the parent module and alternative modules to bind to the core.

### Step 5: allocate mobile theme

Move the portion of the parent accord that can plausibly vary across flankers.

### Step 6: balance socket

If the moved parent material is below the desired socket size, use a controlled amount of existing carrier from the target. Do not create unexplained carrier. If the moved material exceeds the socket, increase the socket or reclassify nodes. Do not compress the parent module merely to meet a preselected round number.

### Step 7: verify exact recombination

For every row:

\[
T_i = C_i + M_{p,i}
\]

and:

\[
\sum_i T_i = \sum_i C_i + \sum_i M_{p,i}
\]

Any row mismatch is a blocking error.

---

## 7. Module envelope

A machine-readable envelope should include:

```json
{
  "socket_raw_total": 300,
  "active_range": [150, 300],
  "carrier_range": [0, 150],
  "anchor_minimums": {},
  "required_roles": [],
  "family_caps": {},
  "temporal_ranges": {},
  "forbidden_materials": [],
  "maximum_unknown_nodes": 2
}
```

### 7.1 Active range

Equal raw module sizes can contain very different active loads due to dilution. Set an acceptable active range based on the parent module and matrix.

### 7.2 Anchor minimums

Some recognizers must occur in the alternative module even when a floor remains in the core.

### 7.3 Required roles

A module should cover jobs, not merely note names.

Example:

```text
cool spice recognizer
citrus-to-heart bridge
dry wood hand-off
sweetness compensation
```

### 7.4 Family caps

Prevent genre collapse, such as:

- too much gourmand in a dry aromatic;
- too much leather in a clean iris perfume;
- too much marine melon in a green floral;
- too much clove in a cardamom perfume.

### 7.5 Temporal range

Compare the module with the parent at opening, heart, and drydown. A replacement that has no opening but massive drydown cannot be accepted merely because its total active amount matches.

---

## 8. Unknown and captive handling

Unknown materials remain explicit nodes.

Example:

```text
UNKNOWN_RADIANT_MUGUET_01
UNKNOWN_DRY_AMBERWOOD_02
```

When partitioning:

- protect an unknown if it appears central across time or flankers;
- allow it into the socket only if evidence suggests the corresponding function varies;
- do not replace the target unknown with a familiar inventory material in the target ledger.

A build can test a functional substitute, but the mapping must state the expected loss.

---

## 9. Alternative module design

### Step 1: write the flanker brief

Specify:

- desired thematic accord;
- retained parent recognizers;
- acceptable family drift;
- forbidden directions;
- time behavior;
- and expected intensity.

### Step 2: choose a thematic center

Use one or a small accord, not a random list.

### Step 3: provide interface materials

Connect the thematic center to at least two protected systems.

### Step 4: compensate physics and perception

Balance:

- volatility;
- active load;
- sweetness;
- dryness;
- polarity;
- diffusion;
- and tenacity.

### Step 5: fill the socket exactly

Carrier is permitted only as declared carrier, not as invisible arithmetic.

### Step 6: validate against the envelope

Reject any module that fails hard gates before bench testing.

---

## 10. Distance model

A module can be screened using a weighted feature vector:

\[
d(M_j,M_p)=
\sqrt{\sum_k w_k(z_{jk}-z_{pk})^2}
\]

Possible features:

- top-active share;
- heart-active share;
- base-active share;
- citrus;
- aromatic;
- green;
- floral;
- spice;
- sweet;
- wood;
- musk;
- amber;
- polarity proxy;
- carrier fraction;
- vapor-pressure bins.

This is a screening distance, not a sensory similarity percentage.

---

## 11. Sensory validation

Run coded samples:

1. complete parent target;
2. fixed core alone;
3. core plus parent module;
4. core plus alternative module;
5. alternative module in a neutral base where useful.

Evaluate at:

- 0 minutes;
- 5 minutes;
- 30 minutes;
- 2 hours;
- 4 hours;
- 8 hours;
- and later for dense systems.

Questions:

- Is the parent recognizable from the core alone?
- Does the parent module restore the complete target?
- Does the alternative read as a flanker rather than a different perfume?
- Which recognizer disappears first?
- Does the module sit on top or integrate?
- Does the drydown retain the family?

---

## 12. Omission experiments

Test:

- core without each protected recognizer;
- core without the interface ring;
- parent module without each major interface;
- alternative module with low, center, and high thematic dose.

Do not delete a trace material because its isolated OAV is below one. Mixture interactions can make subthreshold components alter quality.

---

## 13. Script contract

Minimum files:

```text
target_formula.csv
chassis_partition.csv
parent_module.csv
module_envelope.json
alternative_modules/
validation_report.json
```

Partition CSV must include:

```text
ingredient,target_raw,core_raw,parent_module_raw,
target_active,core_active,parent_module_active,
classification,block,role
```

### Pseudocode

```python
target = load_target()
features = load_features()
classes = classify_nodes(target, features)

core = target.copy()
module = zero_formula(target)

for row in target:
    floor = compute_floor(row, classes[row.id])
    movable = row.raw - floor
    allocated = choose_parent_module_share(row, movable)
    core[row.id] -= allocated
    module[row.id] += allocated

balance_socket_with_declared_carrier(core, module)
assert_rowwise_recombination(target, core, module)
validate_anchor_floors(core)
write_hashes()
```

---

## 14. Hard gates

Fail when:

- the target is incomplete;
- inventory limitations altered the target;
- recognizers are entirely removed without evidence;
- a single stock impersonates multiple target identities;
- the module has no interface materials;
- raw total matches but active/carrier load is unresolved;
- parent recombination is not exact;
- alternative modules violate anchor floors;
- the core no longer smells recognizable;
- or a successful arithmetic check is described as sensory proof.

---

## 15. Acceptance definition

A successful DNA chassis has three properties:

1. **Parent exactness:** core plus parent module exactly restores the target formula.
2. **Core recognizability:** the core retains a subdued but identifiable parent DNA.
3. **Flanker continuity:** alternative modules change theme while preserving recognition through time.

Ingredient count should remain whatever the evidence and function require. The chassis should be modular without becoming skeletal.


---

# From-Scratch Reconstruction Addendum

## When no ranked identity roster or formula hypothesis exists

This addendum extends the Universal Non-Compressed Perfume Reconstruction Protocol to perfumes for which only official notes, labels, public descriptions, family context, and physical reference samples are available.

The authority ceiling is lower than a reconstruction supported by a detailed identity roster or calibrated analytical data. The method must therefore produce an **ensemble of explicit hypotheses**, not one falsely exact formula.

---

## 1. Lock the exact reference

Record:

- brand and exact product;
- concentration;
- bottle and label version;
- market;
- batch code;
- approximate production date;
- storage and opening history;
- and known reformulation boundaries.

Do not combine EDT, EDP, Parfum, Intense, Absolu, and later reformulations as one target.

---

## 2. Build a documentary evidence matrix

Collect only attributable claims.

### Official product data

Extract:

- fragrance family;
- named notes;
- composition narrative;
- ingredient list;
- allergens;
- launch and reformulation data;
- perfumer attribution where officially documented;
- sibling-flanker descriptions.

### Independent but secondary data

Record separately:

- retailer note lists;
- interviews;
- patents;
- supplier demo formulas;
- historical reviews;
- and public databases.

### Evidence status

Every claim receives:

- source class;
- date;
- reference version;
- presence confidence;
- and whether it constrains identity, function, or only perception.

---

## 3. Translate note language into functional constraints

A note is not automatically an ingredient.

For each note, define:

```json
{
  "note": "iris",
  "required_facets": [
    "powder",
    "violet",
    "root",
    "cosmetic",
    "dry wood"
  ],
  "time_windows": ["heart","drydown"],
  "candidate_functions": [
    "ionone body",
    "orris diffusion",
    "powder bridge",
    "woody handoff"
  ],
  "forbidden_drift": [
    "lipstick dominant",
    "sweet violet candy"
  ]
}
```

This creates a search space without pretending the note reveals the commercial raw materials.

---

## 4. Use label evidence carefully

Declared allergens may support the presence of:

- free aroma chemicals;
- natural-material constituents;
- reaction or oxidation products;
- or components of a premade base.

Do not automatically add every allergen as an independent neat material.

Use the label to constrain candidate families and lower bounds only under the applicable labeling rules and product version.

---

## 5. Build the family graph

Construct a graph of official note functions and likely transitions.

Example for a clean iris fougere:

```text
citrus / neroli
      |
aromatic ester lift
      |
soap / muguet air
      |
iris / violet body
      |
pepper / geranium / patchouli
      |
cedar / amber / clean musks
```

The graph exposes missing hand-offs that a simple note list hides.

---

## 6. Use sibling flankers as differential evidence

Sibling products can act as a natural experiment.

For products \(P_1...P_n\):

\[
G_{shared} = \bigcap_j G(P_j)
\]

where \(G(P_j)\) is the functional graph of flanker \(j\).

Repeated functions across siblings are evidence for family DNA, not proof of identical materials or percentages.

Differences identify candidate module regions.

Avoid circular reasoning: marketing copy may repeat house language even where the formula changed.

---

## 7. Generate candidate material families

For every required role, create a candidate set.

Example:

```json
{
  "role": "powdery iris body",
  "candidates": [
    "Methyl Ionone Gamma Coeur",
    "Isoraldeine 95",
    "Alpha Isomethyl Ionone",
    "Dihydro Alpha Ionone",
    "Dihydro Beta Ionone",
    "orris natural or base",
    "UNKNOWN_IRIS_CAPTIVE_01"
  ]
}
```

Do not choose one material immediately. Preserve alternatives and unknown nodes.

---

## 8. Add analytical evidence when possible

### Direct injection GC-MS/FID

Useful for:

- major volatile and semivolatile composition;
- solvent and carrier;
- abundant musks;
- woods;
- naturals;
- and approximate mass balance.

### HS-SPME-GC-MS

Use multiple timepoints and extraction conditions. Headspace is condition-dependent and does not directly equal formula percentage.

### GC-olfactometry

Prioritize peaks that actually carry odor identity, including small or coeluted peaks.

### GCxGC, chiral GC, LC-MS, NMR

Use where coelution, stereochemistry, high-boiling material, naturals, or proprietary mixtures justify it.

Unknown peaks remain unknown nodes.

---

## 9. Build quantity priors

Without a roster, combine:

- analytical peak estimates;
- functional role priors;
- family-era priors;
- official-note constraints;
- allergen evidence;
- cost/manufacturing plausibility;
- and sensory recombination.

Represent each amount as a distribution:

\[
\log q_i \sim \mathcal{N}(\mu_i,\sigma_i^2)
\]

Do not collapse broad uncertainty into a precise microlitre amount without labeling it as a bench center.

---

## 10. Generate an ensemble

Create multiple complete candidate formulas.

Vary:

- material identity alternatives;
- block budgets;
- accord ratios;
- response factors;
- natural composition;
- and trace intensity.

Each ensemble member must remain complete. Do not create sparse candidates merely because optimization prefers fewer variables.

Report:

- median amount;
- credible interval;
- inclusion probability;
- and source confidence.

---

## 11. Recombination testing

Build:

1. central candidate;
2. iris system low/high;
3. soap-muguet system low/high;
4. pepper-geranium-patchouli system low/high;
5. musk architecture alternatives;
6. wood/amber alternatives;
7. candidate unknown replacements.

Evaluate blind against the exact retail reference through time.

Use omission tests to determine whether detail rows earn their place.

---

## 12. Chassis derivation from a from-scratch target

Do not design the chassis until one target ensemble member has become the accepted working center.

For uncertain target rows:

- protect central unknown functions if they appear essential;
- avoid moving low-confidence unknowns into the socket unless flanker evidence suggests mobility;
- give the chassis a wider uncertainty envelope;
- and require a stronger sensory gate.

The chassis report must state that parent recombination is exact relative to the **working hypothesis**, not relative to a proprietary commercial formula.

---

## 13. Authority label

Suggested labels:

- `TIER_0_NOTE_INSPIRED`
- `TIER_1_DOCUMENTARY_FUNCTIONAL_HYPOTHESIS`
- `TIER_2_SENSORY_RECOMBINATION_HYPOTHESIS`
- `TIER_3_ANALYTICALLY_CONSTRAINED`
- `TIER_4_QUANTITATIVELY_CALIBRATED`
- `TIER_5_BLIND_SENSORY_VALIDATED`
- `TIER_6_AUTHENTICATED_FORMULA`

The Prada L'Homme case study in this suite is Tier 1-2. Its 54 rows are a structured, testable center hypothesis, not a recovered commercial formula.

---

## 14. Additional hard gates

Fail when:

- official notes are treated as literal ingredient disclosures;
- review-site consensus replaces evidence;
- sibling flankers are copied into the parent;
- allergens become independent ingredients without provenance;
- every unknown is forced into a catalog material;
- one formula is generated without an alternative ensemble;
- or the final precision exceeds the evidence authority.

The purpose of from-scratch reconstruction is not to sound certain. It is to make uncertainty testable.


---

# Brand, Era, and Product-Family Adaptation

## Universal workflow, non-universal priors

The reconstruction state machine is brand-agnostic. Its priors are not.

Every project must load a brand-era-family profile that changes:

- evidence weighting;
- expected structural blocks;
- likely captive uncertainty;
- natural-material emphasis;
- reformulation risk;
- temporal evaluation window;
- and chassis socket design.

The profiles below are starting configurations, not claims that every fragrance from a house follows one template.

---

## 1. Dior

### Reconstruction emphasis

- lock exact concentration, edition, and reformulation;
- use official parent and flanker descriptions as differential evidence;
- compare repeated structural functions across the line;
- separate modern woody-amber architecture from marketed notes;
- preserve trace floral and spice transitions.

### Typical compression traps

- reducing a Sauvage-type formula to ambroxide plus pepper and citrus;
- treating Dior Homme iris as one ionone;
- treating Fahrenheit leather/violet/gasoline as one leather base;
- confusing a repeated marketing note with an invariant literal ingredient.

### Chassis direction

Dior families often support a protected common core plus a moderate mobile accord. Use line siblings to estimate which functions are fixed and which vary, but verify on the parent.

Potential sockets:

- citrus/spice;
- floral/iris;
- woody-amber;
- or gourmand/resin, depending on line.

---

## 2. Chanel

### Reconstruction emphasis

- strict vintage and concentration control;
- aldehydic series rather than one aldehyde;
- floral layering;
- ionone and orris differentiation;
- sandalwood and musk architecture;
- moss, patchouli, labdanum, and reformulation-sensitive materials;
- high importance of transition quality and negative space.

### Typical compression traps

- collapsing all aldehydes into C-12 MNA;
- reducing jasmine/rose/muguet transmission to Hedione;
- replacing several ionones with Alpha Isomethyl Ionone;
- treating sandalwood as Sandalore alone;
- ignoring vintage restrictions and reformulation.

### Chassis direction

Protect:

- aldehydic-floral interface;
- house floral body;
- ionone/orris geometry;
- and base texture.

A mobile socket may alter citrus, spice, fruit, or tonal woods, but should not amputate the aldehydic and floral handwriting.

---

## 3. Amouage

### Reconstruction emphasis

- high-boiling naturals;
- resins, incense, balsams, smoke, spices, oud-like woods, animalic notes;
- lot-specific natural composition;
- long drydown and fabric evaluation;
- nonvolatile analysis where possible.

### Analytical changes

Prefer:

- direct-injection GC-FID/MS;
- extended headspace intervals;
- GCxGC for resins and naturals;
- LC-MS/HPLC for nonvolatile fractions;
- residue and solvent analysis;
- 24-72 hour sensory windows.

### Typical compression traps

- treating incense as frankincense oil alone;
- treating oud as one amberwood;
- using a short top-note socket for a formula whose identity evolves in the base;
- ignoring resin and natural batch variation.

### Chassis direction

Use multiple coupled sockets where needed:

1. volatile spice/citrus socket;
2. floral-resin heart socket;
3. smoke/wood/balsam drydown socket.

Each socket must preserve cross-links. A single 300 µL module may be inadequate.

---

## 4. Guerlain

### Reconstruction emphasis

- historical formula families;
- branded bases and house accords;
- bergamot, lavender, ionones, heliotropin, vanilla, balsams, moss, patchouli;
- era-specific musks and restrictions;
- powder and sweetness decomposition.

### Typical compression traps

- reducing a Guerlinade-like effect to vanilla plus tonka;
- merging all powder into heliotropin;
- ignoring natural and base provenance.

### Chassis direction

Protect the powder-balsam-floral base. Mobile sockets can change citrus, aromatic, fruit, spice, or leather themes while retaining the family accord.

---

## 5. Hermès

### Reconstruction emphasis

- material spacing;
- transparency and negative space;
- high specificity of citrus, vegetal, mineral, and woody transitions;
- restraint;
- perfumer-era and line context.

### Typical compression traps

- adding too much structural mass because the formula appears sparse;
- mistaking transparency for simplicity;
- replacing several specific citrus or green materials with one broad substitute.

### Chassis direction

Use smaller sockets and tighter family-distance limits. A large module can overwhelm the carefully spaced core.

---

## 6. Prada

### Reconstruction emphasis

- iris/amber opposition;
- clean musk and soap architecture;
- muguet transmission;
- neroli, geranium, pepper, patchouli, cedar;
- powder and texture;
- family comparison with Amber, L'Homme, L'Eau, and Intense only as differential evidence.

### Typical compression traps

- one iris material;
- one musk;
- one soapy material;
- patchouli omitted because it is not obvious;
- clean character treated as high Hedione alone.

### Chassis direction

Protect the iris-soap-musk object and keep some pepper, geranium, patchouli, and neroli in the core. Mobile sockets can redirect brightness, green tea, ginger, amber, or tonka.

---

## 7. YSL

### Reconstruction emphasis

- identify the family recognizer rather than relying on the broad woody designer base;
- distinguish L'Homme's ginger-violet-green-water structure from La Nuit's cardamom-lavender-coumarin structure;
- preserve citrus and muguet interfaces;
- separate wood and musk grades.

### Typical compression traps

- removing the entire spice signature into a neutral slot;
- collapsing ionones;
- replacing green-water systems with Parmavert alone;
- treating all amberwoods as equivalent.

### Chassis direction

Use protected recognizer floors. The core must already suggest the parent before the module is added.

---

## 8. Tom Ford and Estee Lauder portfolio brands

### Reconstruction emphasis

- product-era and concentration lock;
- naturals versus constructed note effects;
- dense woods, amber, leather, florals, and musks;
- possible shared corporate bases;
- edition and discontinuation history.

### Chassis direction

Dense formulas may need larger or multiple sockets, but sweetness and woody pressure must be capped to prevent every flanker becoming the same amber base.

---

## 9. Jean-Claude Ellena-style and minimalist work

This is a perfumer/era profile more than a brand profile.

### Emphasis

- negative space;
- few but highly specific materials;
- trace contrast;
- temporal transparency;
- precise naturals;
- and low material redundancy.

### Compression trap

Assuming a short formula needs no non-compressed analysis. In a minimalist perfume, each row can carry several delicate functions. Substitution tolerance may be lower.

### Chassis direction

Use very small sockets and require strict sensory continuity.

---

## 10. Modern captive-heavy designer fragrances

### Emphasis

- explicit unknown nodes;
- high-resolution chromatography where possible;
- functional reconstitution of unresolved captives;
- family and supplier-era priors;
- no forced catalog naming.

### Chassis direction

Protect unknown nodes that appear central across time. Alternative modules can vary known mobile accord regions while the unknown functional core remains fixed.

---

## 11. Middle Eastern oils, attars, and mukhallats

### Reconstruction emphasis

- oil vehicle;
- natural oud, rose, sandalwood, saffron, resins, musk materials;
- slow release;
- skin and fabric deposition;
- high-boiling fractions;
- adulteration and natural-lot authenticity.

### Analytical changes

- direct injection;
- long headspace windows;
- nonvolatile residue;
- chiral and natural fingerprinting;
- matrix-specific evaluation.

### Chassis direction

Design around active mass and slow time behavior, not ethanol-style top-heart-base assumptions. Coupled heart/base sockets are often more useful.

---

## 12. Vintage perfume

### Reconstruction emphasis

- bottle age and degradation;
- archival formulas and labels;
- historical material availability;
- old naturals and animalics;
- comparison with multiple bottles;
- restoration versus as-smelled reconstruction.

### Two targets may be needed

1. `AS_CURRENTLY_SMELLED`
2. `ESTIMATED_FRESH_ORIGINAL`

Do not mix them.

### Chassis direction

Derive only after the intended target is selected.

---

## 13. Machine-readable profile fields

```json
{
  "profile_id": "",
  "brand": "",
  "era": "",
  "family": "",
  "reformulation_risk": "low|medium|high",
  "unknown_captive_prior": 0.0,
  "natural_complexity_prior": 0.0,
  "negative_space_importance": 0.0,
  "default_evaluation_hours": [],
  "protected_blocks": [],
  "common_compression_traps": [],
  "socket_strategy": "single|coupled|multi_stage"
}
```

The profile supplies priors. It does not override direct evidence.
