# Perfume Chemistry Application Integration Review and Maximum-Quality Architecture

**Document purpose:** Project implementation specification  
**Scope:** Reconstruction, creative formulation, structural chassis derivation, flanker planning, live batch execution, sensory validation, analytical integration, safety, provenance, and AI behavior  
**Status:** Recommended architecture, suitable for implementation planning  
**Core rule:** Evidence, target formula, inventory, build formula, and physical bottle state must remain separate and independently versioned.

---

# 1. Executive verdict

The current L'Homme structural-chassis document is a strong **formula report and research artifact**, but it should not become the application's canonical data model.

It successfully demonstrates:

- claim and authority labeling;
- raw stock versus active-material accounting;
- an explicit substitution ledger;
- an omission ledger;
- separation of a public identity roster from an authenticated manufacturer formula;
- formula and configuration hashes;
- pipeline warnings;
- a modular-flanker concept;
- and basic maturation and evaluation instructions.

However, it also combines too many different realities in one Markdown file:

1. reference evidence;
2. target interpretation;
3. inventory-constrained substitutions;
4. physical build formula;
5. chassis design;
6. quantitative screening;
7. safety warnings;
8. and a generated narrative report.

The maximum-quality application should treat Markdown as a **generated view**, never as the primary source of truth.

The uploaded chassis should be preserved as a legacy fixture:

```text
artifact_type = legacy_inventory_constrained_chassis
authority = unclaimed
use = regression test, historical comparison, and chassis-design case study
canonical_target = false
```

The application's real source of truth should be structured, immutable, queryable, and event-based.

---

# 2. The most important architectural correction

A content hash does not store memory.

A hash proves that a particular payload has not changed, but it cannot reconstruct the payload, distinguish semantic states, or answer whether a material was merely discussed, owned, recommended, or physically added.

The application needs both:

1. the complete canonical record;
2. a cryptographic hash of that record.

Never use a hash as a replacement for a ledger.

## 2.1 Required independent ledgers

### Evidence ledger

Stores every factual or inferential claim from a source.

Examples:

- official note statement;
- package ingredient declaration;
- public ranked identity;
- supplier description;
- GC-MS peak;
- GC-O odor event;
- patent example;
- historical formula;
- user sensory observation;
- and AI-generated hypothesis.

### Target reconstruction ledger

Stores the current best reference hypothesis, independent of inventory.

Fields include:

- identity;
- grade;
- active amount distribution;
- role;
- time window;
- evidence links;
- uncertainty;
- functional block;
- and unknown/captive status.

### Inventory ledger

Stores what is physically available.

Fields include:

- exact stock label;
- supplier;
- lot;
- concentration;
- concentration basis;
- carrier;
- density;
- remaining amount;
- purchase/opening date;
- and identity confidence.

### Build formula ledger

Stores the selected inventory mapping for one intended build.

It may contain substitutions, but substitutions must never rewrite the target ledger.

### Bottle ledger

Stores only confirmed physical actions.

A material is not in a bottle because:

- it appears in a target;
- it exists in inventory;
- an AI recommended it;
- or the user said they were considering it.

It enters the bottle only through a confirmed batch event.

### Analysis ledger

Stores analytical and model outputs, including the exact inputs, software version, configuration, and uncertainty.

### Sensory ledger

Stores coded sample evaluations, reference comparisons, assessors, time points, and environmental conditions.

### Regulatory ledger

Stores time-stamped and jurisdiction-specific safety and regulatory snapshots.

---

# 3. Required project modes

The application must require an explicit operating mode before generating advice.

```text
RECONSTRUCTION
CREATIVE_FORMULATION
STRUCTURAL_CHASSIS
FLANKER_MODULE
INVENTORY_MAPPING
LIVE_BATCH
BATCH_RESCUE
SENSORY_EXPERIMENT
ANALYTICAL_INTERPRETATION
COMPLIANCE_BUILD
RELEASE_REVIEW
```

Each mode has different permissions.

## 3.1 Reconstruction mode

May:

- gather evidence;
- infer identities and dose distributions;
- preserve unknowns;
- generate ensembles;
- and design validation experiments.

May not:

- silently substitute from inventory;
- claim bottle contents;
- or claim exact proprietary percentages without authority.

## 3.2 Creative formulation mode

May:

- introduce materials not supported by a reference;
- optimize hedonic goals;
- and use inventory or cost constraints.

Every creative addition must be labeled as creative, not reconstructed.

## 3.3 Structural chassis mode

May begin only after a full parent target exists.

It derives a core and a parent module from the complete target.

It may not create an arbitrary empty slot by deleting recognizable materials before the parent has been reconstructed.

## 3.4 Live batch mode

Requires:

- selected build formula;
- current inventory;
- current bottle ledger;
- equipment resolution;
- and explicit user confirmation.

It should provide one irreversible action at a time.

## 3.5 Batch rescue mode

Requires a current bottle snapshot and problem statement.

It should first recommend controlled microtrials rather than modifying the whole bottle.

---

# 4. Core data model

## 4.1 Material identity hierarchy

The system must distinguish these levels:

```text
Chemical entity
    -> stereoisomer or isomeric mixture
        -> trade grade
            -> supplier product
                -> supplier lot
                    -> stock solution
                        -> bottle dose event
```

For naturals:

```text
Botanical species
    -> plant part
        -> chemotype
            -> geographic origin
                -> extraction method
                    -> supplier lot
                        -> analytical profile
                            -> stock solution
```

## 4.2 Material entity

Suggested fields:

```json
{
  "material_id": "mat_uuid",
  "canonical_name": "Methyl Ionone Gamma Coeur",
  "identity_type": "trade_grade",
  "cas_numbers": [],
  "ec_numbers": [],
  "inchi_key": null,
  "smiles": null,
  "supplier": null,
  "grade": "Gamma Coeur",
  "chemical_family": ["ionone"],
  "odor_families": ["violet", "orris", "woody", "tobacco"],
  "verified_synonyms": [],
  "non_equivalent_names": [
    "Alpha Isomethyl Ionone",
    "generic Methyl Ionone"
  ],
  "natural": false,
  "identity_confidence": {
    "family": 0.95,
    "exact_grade": 0.70
  }
}
```

## 4.3 Stock solution

```json
{
  "stock_id": "stock_uuid",
  "material_id": "mat_uuid",
  "supplier_lot_id": "lot_uuid",
  "concentration_value": 10.0,
  "concentration_unit": "% w/w",
  "active_fraction_mass": 0.10,
  "active_fraction_volume": null,
  "carrier_material_id": "dpg_uuid",
  "density_g_ml": 0.98,
  "density_temperature_c": 20.0,
  "remaining_mass_g": 12.45,
  "opened_at": "2026-07-28",
  "stability_status": "unknown"
}
```

Never store a naked value such as `10%` without recording:

- w/w, v/v, or w/v;
- carrier;
- temperature;
- and density authority.

## 4.4 Physical-property observations

Do not place a single global vapor pressure, threshold, or density directly on a material record.

Each property must be an observation:

```json
{
  "property_type": "vapor_pressure",
  "value": 0.45,
  "unit": "Pa",
  "temperature_k": 298.15,
  "method": "measured",
  "source_id": "source_uuid",
  "uncertainty": 0.03,
  "applicability": "pure substance"
}
```

The same applies to:

- odor thresholds;
- boiling point;
- density;
- logP;
- solubility;
- diffusion coefficient;
- and retention index.

This prevents incompatible data from being silently mixed.

## 4.5 Natural-material composition

A natural is a parent identity plus a lot-specific distribution.

```json
{
  "natural_lot_id": "natlot_uuid",
  "material_id": "bergamot_fcf_uuid",
  "origin": "Sicily",
  "extraction": "expressed_then_fcf",
  "supplier": "supplier_name",
  "lot": "lot_code",
  "composition": [
    {
      "constituent_id": "limonene_uuid",
      "fraction": 0.39,
      "method": "supplier_gc",
      "uncertainty": 0.03
    }
  ]
}
```

Never reduce a natural to one molecular weight, one vapor pressure, and one threshold without a prominent low-authority label.

---

# 5. Evidence architecture

## 5.1 Evidence source classes

```text
A  Authenticated formula or manufacturer dossier
B  Calibrated quantitative analytical result
C  Identity confirmed by authentic standard and retention evidence
D  Probable analytical identity
E  Official package ingredient or allergen evidence
F  Official brand note and product description
G  Patent, supplier demo, or perfumer interview
H  Secondary ranked identity roster
I  Community sensory evidence
J  AI inference
```

Do not combine these into one hidden confidence number.

## 5.2 Evidence claim

```json
{
  "claim_id": "claim_uuid",
  "source_id": "source_uuid",
  "reference_product_id": "reference_uuid",
  "claim_type": "identity_presence",
  "subject_material_id": "helional_uuid",
  "reported_value": null,
  "reported_unit": null,
  "rank": 22,
  "source_class": "H",
  "independence_group": "dupehacking_roster_2026",
  "confidence": {
    "identity": 0.65,
    "quantity": 0.05
  },
  "exact_excerpt": "Helional",
  "interpretation": "identity prior only"
}
```

## 5.3 Evidence dependency

Several websites may repeat the same upstream list.

They are not independent corroboration.

Use `independence_group` to prevent duplicated internet claims from artificially increasing confidence.

## 5.4 Contradictions

Contradictions remain visible.

```json
{
  "contradiction_group": "vetiver_origin_01",
  "claims": [
    {
      "identity": "Vetiver Haiti",
      "source": "ranked roster"
    },
    {
      "identity": "Vetiver India",
      "source": "inventory"
    }
  ],
  "resolution": "target retains Haiti; build maps India as substitution",
  "expected_loss": [
    "origin-specific brightness",
    "cleaner acetate-like contour"
  ]
}
```

---

# 6. Reconstruction engine

## 6.1 Reference lock

Every reconstruction must lock:

- exact product;
- concentration;
- market;
- reference year;
- batch code where possible;
- package ingredient-list version;
- storage condition;
- and reformulation era.

A brand name and perfume title are insufficient.

## 6.2 Complete roster first

The engine creates a complete roster before selecting amounts.

Supported identities remain separate unless verified as true duplicates.

The engine must preserve:

- trace identities;
- technical additives;
- carriers;
- unresolved peaks;
- proprietary bases;
- and unknown captive functions.

## 6.3 Unknown nodes

Use explicit unknowns:

```text
UNKNOWN_MUGUET_01
UNKNOWN_DRY_AMBERWOOD_02
UNKNOWN_CLEAN_MUSK_03
UNKNOWN_GREEN_FRUIT_01
```

Unknown fields:

- retention indices;
- spectrum;
- odor description;
- GC-O intensity;
- time window;
- candidate identities;
- presence probability;
- dose distribution;
- and functional roles.

A wrong familiar name is worse than an honest unknown.

## 6.4 Formula amount as a distribution

For each target material:

```text
presence_probability
dose_median
dose_lower
dose_upper
identity_confidence
grade_confidence
quantity_confidence
```

Use an ensemble, not one falsely exact formula.

A useful model is:

\[
\log x_i \sim Normal(\mu_i, \sigma_i^2)
\]

with constraints for:

- total active mass;
- block budgets;
- rank order;
- analytical evidence;
- functional coverage;
- temporal coverage;
- and safety-independent target logic.

## 6.5 Quantity priors

Use several independent priors:

1. ranked-list prior;
2. calibrated analytical prior;
3. functional-role prior;
4. note-architecture prior;
5. historical formula prior;
6. brand, era, and perfumer prior;
7. cost plausibility prior;
8. physical-release prior;
9. supplier-use-level prior where lawful and appropriate.

No one prior may dominate without authority.

## 6.6 Anti-compression gate

Two identities may be merged only when they are verified duplicates or true synonyms.

They must remain separate when they differ in:

- odor character;
- volatility;
- tenacity;
- diffusion;
- texture;
- temporal role;
- supplier grade;
- stereochemistry;
- recognition importance;
- or functional graph position.

A one-stock-to-many-target mapping is allowed only in the build layer and must generate a loss report.

---

# 7. Functional and accord graph

## 7.1 Why a graph is necessary

A note pyramid cannot explain how a perfume works.

The graph should represent:

- structural support;
- accord membership;
- reinforcement;
- masking;
- temporal hand-off;
- contrast;
- diffusion;
- and module attachment.

## 7.2 Node fields

```json
{
  "material_id": "helional_uuid",
  "primary_block": "green_water",
  "roles": [
    "heart_body",
    "muguet_support",
    "leaf_to_floral_bridge",
    "diffusion"
  ],
  "time_window": [
    "opening",
    "heart"
  ],
  "recognizer_importance": 0.40,
  "interface_centrality": 0.86,
  "module_mobility": 0.22
}
```

## 7.3 Edge fields

```json
{
  "from": "bergamot_uuid",
  "to": "linalyl_acetate_uuid",
  "edge_type": "temporal_handoff",
  "strength": 0.80,
  "evidence": [
    "sensory",
    "functional_prior"
  ]
}
```

## 7.4 Accord objects

An accord should be a first-class object.

```json
{
  "accord_id": "accord_green_violet_01",
  "name": "Green violet-water hinge",
  "materials": [
    "verdox_uuid",
    "helional_uuid",
    "bourgeonal_uuid",
    "cis3_hexenyl_salicylate_uuid",
    "ionone_uuid"
  ],
  "roles": [
    "apple_effect",
    "violet_leaf",
    "watery_transition"
  ],
  "parent_formula_version": "formula_v3"
}
```

An accord is not merely a folder. It has:

- internal ratios;
- dose range;
- temporal profile;
- perceptual purpose;
- uncertainty;
- and interface requirements.

---

# 8. DNA-preserving structural chassis engine

## 8.1 The chassis must be derived from a complete parent

The parent relationship is:

\[
T_i = C_i + M_{parent,i}
\]

where:

- \(T_i\) is target amount;
- \(C_i\) is core amount;
- \(M_{parent,i}\) is parent-module amount.

Every target row must recombine exactly.

## 8.2 Do not begin with a fixed 100 µL slot

A fixed slot may be useful for a manual prototype, but it should not be the general algorithm.

The module size should emerge from:

- accord mobility;
- recognizer floors;
- graph centrality;
- temporal placement;
- and expected flanker variation.

Some perfumes need:

- one small top socket;
- one top and heart socket;
- or a coupled spice, resin, and drydown system.

## 8.3 Material classification

Each row receives one chassis class:

```text
IMMUTABLE_CORE
PROTECTED_ANCHOR
INTERFACE_RING
MODULE_MOBILE
UNKNOWN_PROTECTED
UNKNOWN_MODULE_CANDIDATE
TECHNICAL
CARRIER
```

## 8.4 Anchor floor

For protected material \(i\):

\[
C_i \geq f_i T_i
\]

The floor \(f_i\) must be validated by omission testing.

A recognizable material should not be reduced to zero merely because it is part of the theme to be swapped.

## 8.5 Mobility scoring

Suggested components:

```text
theme_specificity
flanker_variance
temporal_locality
graph_peripherality
substitution_tolerance
recognizer_importance
interface_centrality
uncertainty
```

Example:

\[
Mobility_i =
w_1 Theme_i +
w_2 FlankerVariance_i +
w_3 TemporalLocality_i +
w_4 Peripherality_i -
w_5 Recognizer_i -
w_6 InterfaceCentrality_i -
w_7 Uncertainty_i
\]

High-recognition and high-interface materials remain in the core.

## 8.6 Module envelope

Raw volume alone is insufficient.

A module envelope should track:

- active mass;
- carrier mass;
- volatility centroid;
- volatility spread;
- logP distribution;
- top/heart/base emission;
- odor-family vector;
- sweetness;
- dryness;
- freshness;
- floral volume;
- woody pressure;
- musk load;
- polarity;
- color risk;
- solubility;
- and protected-anchor minimums.

## 8.7 Compensation vector

When a module replaces a parent accord with a materially different accord, compensation must occur inside the module.

Example:

```text
Parent: cool cardamom-lavender spice
Replacement: immortelle-tobacco

Required compensation:
- preserve cardamom floor;
- reduce added coumarinic sweetness;
- add aromatic lift;
- cap heavy tobacco;
- maintain top-to-heart volatility;
- preserve violet/wood interface.
```

## 8.8 Multiple sockets

The engine should support:

```text
SIGNATURE_TOP_SOCKET
HEART_THEME_SOCKET
BASE_TONAL_SOCKET
TEXTURE_SOCKET
```

Each perfume can expose zero, one, or several sockets.

A minimalist fresh fragrance may need one.

A resinous or incense-heavy fragrance may need coupled heart and base sockets.

## 8.9 Family drift

Family drift must not run until the family profile is defined.

A valid family profile includes:

- protected recognizers;
- forbidden drift;
- core block ranges;
- temporal signature;
- parent reference vectors;
- and validated legacy examples.

`unknown family archetype` should disable the score or fail the claim, not emit a decorative warning while continuing.

---

# 9. Inventory and build mapping

## 9.1 Status taxonomy

Every target row maps to inventory as:

```text
EXACT_AVAILABLE
PROBABLE_GRADE_MATCH
FUNCTIONAL_SUBSTITUTE
PARTIAL_ACCORD_RECONSTRUCTION
UNAVAILABLE
UNKNOWN_IDENTITY
TECHNICAL_NOT_REQUIRED
```

## 9.2 Substitution report

```json
{
  "target": "Habanolide",
  "build": "Galaxolide",
  "status": "FUNCTIONAL_SUBSTITUTE",
  "preserved_roles": [
    "clean_musk_body",
    "diffusion"
  ],
  "lost_roles": [
    "macrocyclic_radiance",
    "warm_woody_metallic_contour"
  ],
  "confidence": 0.35
}
```

## 9.3 Never hide substitutions inside formula rows

Do not write:

```text
Galaxolide, includes Habanolide amend
```

Instead preserve:

```text
Target row: Habanolide
Build mapping: Galaxolide
Expected loss: documented
```

This is one of the highest-priority corrections to the current chassis file.

## 9.4 Measurability

The build engine must know:

- balance readability and repeatability;
- pipette range and accuracy;
- minimum reliable volume;
- container tare;
- and stock concentration.

A dose below instrument resolution must automatically trigger stock preparation.

---

# 10. Live batch and bottle ledger

## 10.1 Event sourcing

The bottle is reconstructed from immutable events.

```json
{
  "event_id": "event_uuid",
  "batch_id": "batch_uuid",
  "event_type": "DOSE_STOCK",
  "stock_id": "stock_uuid",
  "measured_mass_g": 0.0521,
  "measured_volume_ul": null,
  "timestamp": "2026-07-28T13:10:00Z",
  "operator": "kenny",
  "confirmation": "confirmed",
  "source": "manual_balance"
}
```

## 10.2 Event types

```text
CREATE_BATCH
TARE_CONTAINER
DOSE_STOCK
ADD_SOLVENT
REMOVE_SAMPLE
TRANSFER
CORRECT_ENTRY
DILUTE
MIX
REST_START
REST_END
SAMPLE
EVALUATE
CLOSE_BATCH
```

Never delete an event.

Use a compensating correction event.

## 10.3 Proposed versus committed actions

AI voice or chat suggestions create a proposed action.

Only explicit confirmation or instrument capture commits the event.

```text
PROPOSED
CONFIRMED
MEASURED
COMMITTED
CANCELLED
```

## 10.4 Live-batch money and time gate

Before recommending an irreversible addition, the application must verify:

1. current batch is known;
2. bottle ledger is current;
3. stock and concentration are known;
4. target role is known;
5. addition type is labeled;
6. amount is measurable;
7. expected effect is stated;
8. stop condition is stated;
9. lower-risk microtrial has been considered.

## 10.5 Advice format

During live mixing, the application should answer in this structure:

```text
Action type: target alignment / rescue / stylistic
Material and stock:
Amount:
Why:
Expected effect:
Main risk:
Evaluation time:
Stop condition:
Ledger status after confirmation:
```

Give one action at a time unless the user explicitly requests a full batch plan.

---

# 11. Formula arithmetic engine

## 11.1 Use mass as the canonical basis

Preferred internal formula basis:

```text
active mass parts per 1000 active parts
```

Store volume only as a derived manufacturing view.

## 11.2 Keep these totals separate

```text
raw stock mass
active odorant mass
technical active mass
carrier mass
ethanol mass
water mass
finished product mass
```

DPG should not be counted as odorant-active material.

## 11.3 Stock conversion

For target active mass \(a_i\) and stock fraction \(s_i\):

\[
raw_i = \frac{a_i}{s_i}
\]

\[
carrier_i = raw_i - a_i
\]

## 11.4 Total reconciliation

Every formula must satisfy:

\[
\sum raw_i = target\_concentrate\_mass
\]

\[
\sum active\_odorant_i +
\sum technical_i +
\sum carrier_i
=
target\_concentrate\_mass
\]

## 11.5 Unit engine

Use a units library or a strict internal unit system.

Reject:

- missing concentration basis;
- incompatible units;
- density conversion without temperature;
- and ambiguous percent values.

## 11.6 Rounding optimization

Do not round each row independently.

Solve for measurable increments while minimizing weighted formula error and preserving totals.

---

# 12. Analytical integration

## 12.1 Direct-injection GC-MS or GC-FID/MS

Store:

- method;
- column;
- temperature program;
- injection mode;
- split ratio;
- internal standard;
- retention time;
- retention index;
- peak area;
- response factor;
- qualifier ions;
- and identity confidence.

## 12.2 HS-SPME-GC-MS

Store every experimental condition:

- fiber;
- sample mass;
- vial volume;
- headspace volume;
- temperature;
- incubation;
- extraction time;
- agitation;
- desorption;
- substrate;
- and elapsed application time.

A headspace result is method-specific.

## 12.3 GC-O

Store:

- odor-event start and end;
- descriptor;
- assessor;
- intensity;
- repeatability;
- and aligned retention index.

Small analytical peaks may have high odor importance.

## 12.4 Standards

Critical identities should support:

- authentic standard;
- co-injection;
- retention-index agreement;
- and characteristic-ion agreement.

A spectral-library match alone is insufficient for the highest identity tier.

## 12.5 Instrument quality control

Required controls:

- solvent blank;
- vial blank;
- matrix blank;
- internal standard;
- duplicate or triplicate injection;
- calibration verification;
- retention-index standard;
- drift monitor;
- and control fragrance.

## 12.6 Raw-data preservation

Store vendor raw files and open exports.

Do not preserve only a peak table.

## 12.7 Chemometric layer

Useful analyses:

- PCA;
- PLS;
- clustering;
- peak alignment;
- time-profile comparison;
- reference-versus-candidate distance;
- and batch drift.

Chemometrics should prioritize experiments, not replace sensory validation.

---

# 13. Physical and headspace modeling

## 13.1 Rename weak OAV outputs

Use true `OAV` only when concentration and threshold are comparable in:

- matrix;
- unit;
- temperature;
- and measurement context.

Otherwise use names such as:

```text
HEADSPACE_PRIORITY_INDEX
THEORETICAL_ODOR_SCREEN
VOLATILITY_THRESHOLD_HEURISTIC
```

## 13.2 Do not call the index measured intensity

A modeled index must not directly produce claims such as:

- dominant;
- perceptible;
- sub-threshold;
- fatigue risk;
- or similarity percentage

unless the underlying authority supports them.

## 13.3 Naturals

For a natural, use one of:

1. lot-specific constituent model;
2. empirical headspace curve;
3. composite empirical descriptor with broad uncertainty.

Do not use one pseudo-molecular vapor pressure as if the natural were a pure molecule.

## 13.4 Finite-film modeling

A better model should include:

- initial film thickness;
- substrate;
- solvent evaporation;
- changing liquid composition;
- activity coefficients;
- diffusion;
- skin or blotter absorption;
- and time.

Theoretical modeling remains a screening layer until calibrated against measured emissions.

## 13.5 Uncertainty propagation

Use Monte Carlo propagation for:

- density;
- active fraction;
- vapor pressure;
- threshold;
- natural composition;
- and activity coefficient.

Report distributions, not a single high-precision number.

---

# 14. Sensory validation

## 14.1 Standardized evaluation

Control:

- reference batch;
- application mass;
- blotter type;
- room temperature;
- humidity;
- airflow;
- evaluation distance;
- assessor fragrance abstention;
- and sample code.

## 14.2 Time grid

Recommended minimum:

```text
0 minutes
5 minutes
30 minutes
2 hours
4 hours
8 hours
24 hours where relevant
```

## 14.3 Reference-specific lexicon

Build a lexicon for:

- recognizers;
- transitions;
- texture;
- diffusion;
- sweetness;
- dryness;
- roughness;
- and off-notes.

Avoid relying only on broad families such as woody, floral, and citrus.

## 14.4 Omission tests

For each suspected subsystem, compare:

```text
full formula
minus subsystem
```

Examples:

- no green-water hinge;
- no secondary musk;
- no trace aldehydes;
- no secondary woods;
- no rose-ketone trace;
- no protected spice floor.

## 14.5 Dose-response tests

Use:

```text
zero
low
center
high
```

The best dose may not be linear.

## 14.6 Blind comparison

The evaluator should not know which sample is:

- reference;
- baseline;
- revised candidate;
- or omission.

## 14.7 Sensory vector

Do not collapse similarity to one number.

Store:

```text
opening identity
heart identity
drydown identity
transition quality
texture
diffusion
longevity
off-note severity
overall preference
```

---

# 15. Experiment and optimization engine

## 15.1 Optimize information gain, not addition count

The best next experiment is the one expected to reduce the most uncertainty per cost and risk.

Example objective:

\[
Utility =
\frac{ExpectedInformationGain \times ExpectedSensoryValue}
{Cost \times Irreversibility \times Time}
\]

## 15.2 Microtrial first

When a full bottle is valuable or uncertain:

- withdraw equal aliquots;
- create coded microvariants;
- vary one block;
- compare against control;
- and update the model.

## 15.3 Design of experiments

Use:

- fractional factorial screening;
- mixture designs for accords;
- response surfaces;
- Bayesian optimization;
- and preference learning.

## 15.4 Constrained optimization

The optimizer must obey:

- formula total;
- safety build rules;
- inventory;
- active fraction;
- carrier;
- module envelope;
- recognizer floors;
- and measurement resolution.

## 15.5 Human-in-the-loop

The algorithm proposes candidates.

Bench evidence and sensory comparison decide whether a candidate is better.

---

# 16. Safety and regulatory subsystem

## 16.1 Separate target from compliant build

A historical or forensic target may contain a restricted or unavailable material.

Do not erase it from the target.

Create a separate compliant build with documented substitutions.

## 16.2 Versioned rule sets

Store:

- jurisdiction;
- product category;
- rule-set version;
- effective date;
- source;
- and snapshot hash.

## 16.3 Required source classes

Use current official data and supplier documentation:

- IFRA Standards;
- supplier IFRA certificates;
- supplier SDS and allergen declarations;
- ECHA chemical and classification data;
- European cosmetic nomenclature and legislation;
- and jurisdiction-specific law.

## 16.4 Important distinction

A material appearing in:

- a nomenclature database;
- a transparency list;
- or a supplier catalog

does not by itself prove unrestricted safety or legal use.

## 16.5 Release gate

Release mode should require:

- product category;
- intended use;
- finished concentration;
- current rule snapshot;
- allergen calculation;
- phototoxicity review;
- sensitization review;
- prohibited-material review;
- stability;
- packaging compatibility;
- and appropriate human-safety process.

A research formula may exist while release remains blocked.

---

# 17. AI architecture

## 17.1 Use the LLM as an orchestrator, not the arithmetic engine

LLM responsibilities:

- source extraction;
- hypothesis generation;
- functional explanation;
- contradiction discovery;
- experiment design;
- and natural-language interaction.

Deterministic engine responsibilities:

- units;
- arithmetic;
- formula totals;
- active fractions;
- carrier accounting;
- hashes;
- diffs;
- safety-rule application;
- and state transitions.

Probabilistic engine responsibilities:

- quantity distributions;
- uncertainty;
- candidate ensembles;
- and experiment prioritization.

## 17.2 Schema-constrained AI output

Every AI action should be emitted into a validated schema.

Invalid output does not enter the ledger.

## 17.3 Retrieval

Use retrieval over curated project evidence.

Do not let the model answer from conversational memory when a structured ledger exists.

## 17.4 Tool transparency

The interface should distinguish:

```text
from current ledger
from uploaded source
from official external source
from model inference
from user observation
```

## 17.5 Abstention

When a material amount or bottle state is unknown, the system should say unknown and request confirmation.

It should not infer an exact amount from a vague recollection.

---

# 18. User interface

## 18.1 Main views

### Reference view

- exact product version;
- evidence sources;
- target identity roster;
- authority vector;
- and unknowns.

### Formula view

- active formula;
- raw stock formula;
- carriers;
- accords;
- and functional graph.

### Target versus build versus bottle diff

Columns:

```text
Target
Inventory match
Build amount
Actual bottle amount
Status
Expected substitution loss
```

### Chassis view

- immutable core;
- protected anchors;
- interface ring;
- module materials;
- parent recombination;
- and alternative-module envelope.

### Batch console

- current action;
- instrument;
- measured value;
- confirmation;
- running total;
- and next step.

### Sensory view

- coded samples;
- time points;
- attribute scores;
- and reference distance.

### Safety view

- jurisdiction;
- current snapshot;
- limitations;
- and release blockers.

## 18.2 Voice behavior

During live work:

- read back material, stock, and amount;
- distinguish neat from diluted;
- confirm before commit;
- do not repeat “checking” unless a real tool call occurs;
- use the ledger instead of conversational memory;
- and provide one action at a time.

---

# 19. Provenance and reproducibility

Every run should record:

```text
code commit SHA
container or environment version
dependency lockfile hash
database snapshot
source snapshot hashes
formula version
inventory version
bottle version
config hash
random seed
model version
run timestamp
operator
```

## 19.1 Canonical hashing

Hash canonical JSON, not formatted Markdown.

Canonicalization should define:

- key ordering;
- number formatting;
- unit normalization;
- Unicode normalization;
- and excluded display fields.

## 19.2 Generated reports

Markdown, PDF, spreadsheets, and dashboards are generated from canonical data.

Editing a generated report must not silently change the formula.

## 19.3 Semantic diff

Show:

- row added;
- row removed;
- identity changed;
- grade changed;
- active amount changed;
- stock changed;
- carrier changed;
- evidence changed;
- and authority changed.

---

# 20. Testing strategy

## 20.1 Unit tests

- active-to-stock conversion;
- density conversion;
- carrier calculation;
- total mass balance;
- unit compatibility;
- hash determinism;
- synonym resolution;
- and event replay.

## 20.2 Property-based tests

Generate random valid formulas and verify:

- total conservation;
- nonnegative amounts;
- stock fractions between zero and one;
- parent recombination;
- and stable round trips.

## 20.3 Golden fixtures

Use the YSL L'Homme, La Nuit, and Prada cases as regression fixtures.

Include:

- old compressed chassis;
- expanded target;
- inventory-constrained build;
- chassis partition;
- and module variants.

## 20.4 Gate tests

- unknown family disables family score;
- unresolved concentration basis blocks mass conversion;
- dose below equipment resolution blocks batch action;
- unconfirmed bottle addition remains proposed;
- parent core plus parent module equals target;
- substitution never rewrites target;
- and expired safety snapshot blocks release.

## 20.5 Analytical tests

- blank contamination;
- retention-index drift;
- response-factor availability;
- duplicate precision;
- and peak-alignment stability.

---

# 21. Observability

Track:

- formula-generation failures;
- unresolved identities;
- missing densities;
- missing threshold authority;
- substitution count;
- one-to-many mappings;
- user correction rate;
- unconfirmed bottle events;
- sensory experiment completion;
- and model calibration error.

A useful metric is:

```text
number of user corrections caused by stale or conflated state
```

That metric should trend toward zero.

---

# 22. Data quality and licensing

Store:

- source owner;
- access date;
- usage rights;
- redistribution rights;
- and permitted excerpt.

Do not redistribute proprietary or paywalled content merely because it was used as evidence.

Preserve citations and source hashes.

User-supplied files remain user-scoped.

---

# 23. Specific corrections to the uploaded L'Homme chassis

## 23.1 Reclassify the file

Use:

```text
legacy_inventory_constrained_chassis_v1
```

Do not use it as the canonical reference reconstruction.

## 23.2 Split the file

Create separate files or database records:

```text
reference_contract.json
public_identity_roster.json
target_formula.json
inventory_mapping.json
build_formula.json
chassis_partition.json
pipeline_run.json
generated_report.md
```

## 23.3 Remove hidden target compression

Replace lines such as:

```text
Galaxolide includes Habanolide amend
Exaltolide includes Muscenone Delta amend
Alpha Isomethyl Ionone covers two proprietary ionones
Parmavert covers two green materials
```

with explicit target rows and build mappings.

## 23.4 Correct material identity handling

Do not parenthetically equate Alpha Isomethyl Ionone with Methyl Ionone Pure unless the supplier label and identity registry verify that exact mapping.

## 23.5 Correct active accounting

Separate:

- active odorants;
- technical ingredients;
- and carriers.

Neat DPG is not odorant-active.

## 23.6 Correct concentration profile mismatch

The document calls the study EDT while the semantic configuration uses an EdP bracket.

That inconsistency should be a blocking configuration error.

## 23.7 Disable invalid family logic

The pipeline reports `unknown family archetype: ysl_lhomme`.

Family-drift output must therefore be disabled or marked unavailable.

## 23.8 Replace OAV language

The current model itself states that it is heuristic, matrix-omitted, and not measured.

Do not label materials as objectively dominant, perceptible, or sub-threshold from that screen alone.

## 23.9 Natural-material modeling

Lemon, bergamot, lavender, cedarwood, and vetiver should not be represented as pure pseudo-molecules without explicit uncertainty.

## 23.10 Role taxonomy

The current model places materials such as lemon and Iso E Super into broad top/heart labels that do not adequately describe their real functions.

Use temporal and functional roles independently.

## 23.11 Confidence gate

A combined confidence of 14.1 should block automatic reconstruction claims and high-cost batch recommendations.

## 23.12 Inventory authority

An inventory row can resolve by name while exact grade, concentration basis, density, or lot remains uncertain.

Inventory authority should be multidimensional rather than one PASS.

---

# 24. Recommended project modules

```text
identity_service
evidence_service
reference_service
formula_service
accord_graph_service
reconstruction_engine
chassis_engine
inventory_service
build_mapper
batch_ledger
analytical_service
sensory_service
experiment_planner
safety_service
report_service
agent_orchestrator
```

A modular monolith is a sensible first implementation.

Do not begin with many networked microservices unless scale requires them.

Keep interfaces clean so services can be separated later.

---

# 25. Recommended implementation sequence

## Phase 0: Foundation

1. Canonical material identity registry.
2. Units and concentration engine.
3. Immutable formula versions.
4. Inventory and stock model.
5. Event-sourced bottle ledger.
6. Canonical hashing.
7. Target/build/bottle diff.
8. Generated reports.

## Phase 1: Reconstruction quality

1. Evidence ledger.
2. Reference version lock.
3. Complete roster builder.
4. Unknown-node handling.
5. Functional roles and accord graph.
6. Anti-compression audit.
7. Uncertainty distributions.
8. Candidate ensemble generation.

## Phase 2: Chassis and flanker system

1. Recognizer scoring.
2. Interface centrality.
3. mobility scoring;
4. core/module optimization;
5. parent recombination tests;
6. module envelope;
7. compensation vectors;
8. family-drift validation.

## Phase 3: Bench execution

1. Batch console.
2. instrument-aware measurement;
3. proposed-versus-committed actions;
4. microtrial planner;
5. coded samples;
6. time-series sensory capture;
7. experiment analysis.

## Phase 4: Analytical integration

1. direct GC import;
2. HS-SPME import;
3. retention-index registry;
4. standards and response factors;
5. GC-O events;
6. chromatogram comparison;
7. natural-lot profiles.

## Phase 5: Regulatory and release

1. versioned official rule sources;
2. supplier documents;
3. jurisdiction and category;
4. allergen calculation;
5. compliance build generation;
6. release gate.

## Phase 6: Advanced optimization

1. Bayesian experiment selection;
2. preference learning;
3. family latent models;
4. cross-flanker differential analysis;
5. matrix release calibration;
6. model calibration against measured data.

---

# 26. Minimum acceptance criteria

The project should not call itself maximum-quality until it can demonstrate:

1. Every target row has provenance.
2. Target, inventory, build, and bottle are separate.
3. Every bottle action is replayable.
4. Every formula balances exactly.
5. Concentration basis is explicit.
6. No supplier-grade conflation occurs silently.
7. Unknown captives remain unknown.
8. Parent chassis recombines exactly to target.
9. Protected anchors remain above validated floors.
10. Module validation uses more than raw volume.
11. OAV is not overstated.
12. Naturals are lot-aware or uncertainty-labeled.
13. Sensory data are time-resolved and coded.
14. Safety data are current and versioned.
15. Generated reports reproduce from canonical data.
16. AI cannot commit unconfirmed bottle actions.
17. Expensive recommendations require a state diff and a stop condition.
18. All critical gates have automated tests.

---

# 27. Final design principle

The application should maintain this chain:

```text
Source evidence
    -> evidence claims
        -> identity hypotheses
            -> complete target ensemble
                -> accepted target version
                    -> accord and DNA graph
                        -> chassis derivation
                            -> inventory mapping
                                -> measurable build
                                    -> physical bottle events
                                        -> analytical and sensory results
                                            -> updated posterior
```

Nothing should jump across layers.

The target should never be rewritten because inventory is missing.

The bottle should never be inferred from a recommendation.

The formula should never be inferred from a hash.

A theoretical headspace score should never become a sensory fact.

A flanker slot should never be created by removing the very recognizers that define the perfume.

That separation is the difference between a clever formula generator and a serious perfume-chemistry research platform.
