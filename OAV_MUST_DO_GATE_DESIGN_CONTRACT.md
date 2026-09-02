# Perfume-Chem OAV MUST-DO Gate Design Contract v1.1

**Date:** 2026-08-17  
**State:** `CLEAN_ROOM_DESIGN_CONTRACT_REFERENCE__NOT_INSTALLED`  
**Current-build boundary:** V19/V20 candidate state  
**Repository/app status:** `BRIDGE_BLOCKED`  
**Authority:** design and implementation handoff only

No source admission, package installation, formula mutation, stock mutation, physical measurement, sensory result, strict empirical OAV, safety decision, procurement decision, publication, or release authority is created by this package.

## 1. Hard invariant

No formula may enter the bench-recipe presentation path until **every odor-active row** has a terminal OAV/potency disposition.

`STRICT_EMPIRICAL_OAV_UNAVAILABLE` never means `SKIP`.

The required terminal states are:

| State | Meaning | Downstream consequence |
|---|---|---|
| `PASS_SCREENED` | The OAV pre-presentation screen is complete at the stated authority and context. | The formula may proceed to the next independent gate. It is not released or bench-authorized by this state alone. |
| `REVIEW_REQUIRED` | A bounded computational estimate exists, but authority is screening-level, temporal coverage is absent, or uncertainty/model disagreement requires review. | Computational candidate only. No bench recipe export. |
| `HOLD` | Critical stock, identity, matrix, natural-profile, property, threshold, model, or measured-air evidence is missing or incompatible. | Block presentation and specify the exact evidence or controlled test needed. |
| `FAIL` | A hard contradiction, arithmetic error, impossible value, or known physical negative is reached. | Stop and rebuild/rebase before reevaluation. |

There is no aggregate quality score. Formula status is the worst blocking row state, with each dimension retained separately.

## 2. Non-duplication rule

This design does not create a second physics, sensory, temporal, stock, or analytical owner. It is a **mandatory adapter and claim firewall**:

```text
exact source/formula identity
  -> Inventory V5 exact stock binding
  -> exact active-equivalent arithmetic
  -> accepted physical-property / headspace StageResult adapters
  -> OAV MUST-DO disposition
  -> formula-presentation dispatcher
```

Existing stock, analytical, physical-release, temporal, interaction, sensory, safety, and release owners remain authoritative. The OAV gate consumes their typed outputs only when their `may_feed` contract permits that use.

## 3. Gate topology

### G15.00 — Source, formula, and context lock

Required:

- exact formula artifact/hash;
- exact target/version;
- exact finished-product matrix;
- temperature, pressure, substrate, dose geometry, and timepoint scope;
- operation-scoped source-use authorization.

A stale formula, mixed versions, or unresolved source conflict returns `HOLD`.

### G15.01 — Odor-active row coverage

Every row must be either:

- `odor_active=true`, and processed through all applicable stages; or
- `odor_active=false`, with a scoped exemption reason.

A missing row, blanket exemption, or unnamed proprietary contribution returns `HOLD`.

### G15.02 — Exact stock and active-equivalent firewall

For every odor-active row:

```text
active_mass = raw_stock_mass × active_fraction
embedded_carrier = raw_stock_mass - active_mass
active_finished_ppm_w_w = active_mass / finished_product_mass × 1,000,000
```

Requirements:

- `ExactStockRef`;
- stock fraction and basis;
- carrier identity;
- density and conversion authority whenever converting a volume basis to mass;
- parent-to-child active-equivalent continuity;
- exact-decimal arithmetic.

Unknown stock strength does not default to neat. A 10% to neat stock change with an unchanged raw dose fails. A carrier change must be reconciled separately.

### G15.03 — Material-class and molecular-identity gate

Supported paths:

- `PURE`: molecular properties and threshold apply only to the confirmed identity/isomer/grade scope;
- `NATURAL_COMPLEX`: constituent-resolved natural profile path;
- `COMPLEX_PRODUCT_PROFILED`: constituent-resolved product-basis path with explicit profile authority;
- `PROPRIETARY_PRODUCT`: no guessed molecular active fraction, molecular weight, vapor pressure, or whole-product OAV.

An opaque base stays `HOLD` unless a valid constituent-resolved or measured-headspace path exists.

### G15.04 — Matrix and measurement-context gate

Mandatory context fields include:

- matrix composition and basis;
- liquid volume or a justified alternative when a Henry route requires concentration;
- substrate/apparatus;
- temperature and pressure;
- sampling mode and timepoint;
- measurement or model domain.

Headspace behavior from DPG, ethanol-water, oil, blotter, chamber, membrane, fabric, or skin cannot be transferred silently.

### G15.05 — Natural/essential-oil decomposition gate

A whole essential oil, absolute, tincture, balsam, resin, or natural extract receives **no single molecular OAV**.

Authority ladder:

1. constituent-resolved measured candidate headspace in the matching matrix/context;
2. lot-specific calibrated constituent composition plus matching-matrix measured Henry constants;
3. lot-specific calibrated constituent composition plus validated nonideal VLE;
4. GC relative-area profile with bounded response factors and explicit concentration uncertainty;
5. species/plant-part/process/chemotype/origin-matched literature composition ranges;
6. marker-only lower bound with unresolved remainder;
7. unprofiled whole natural, which returns `HOLD`.

Supported profile modes:

- `CALIBRATED_MASS_FRACTION`;
- `RELATIVE_AREA_RESPONSE_BOUNDED`;
- `LITERATURE_MASS_FRACTION_RANGE`;
- `MARKER_LOWER_BOUND`.

Relative GC area is stored separately from calibrated concentration and never silently treated as mass fraction.

### G15.06 — Property and threshold authority gate

For each pure molecule or characterized natural constituent, require:

- molecular weight;
- identity-matched vapor-pressure or partition data at a stated temperature;
- activity-coefficient authority where used;
- compatible air threshold with units, method, and population/panel provenance;
- uncertainty or range where appropriate.

No arbitrary numeric defaults are permitted. A water threshold cannot be divided into an air concentration for strict OAV.

### G15.07 — Equilibrium partial-pressure model ladder

Multiple models may run in parallel, but they remain separately labelled.

#### A. Direct measured equilibrium partial pressure

```text
p_i = measured matching-matrix constituent partial pressure
```

Requires calibrated method and context match.

#### B. Matching-matrix Henry route

Supported explicit conventions:

```text
H_PC_PA_M3_PER_MOL: p_i = H_pc × C_liquid,i
K_AW_DIMENSIONLESS: C_air,i = K_aw × C_liquid,i; p_i = C_air,i × R × T
H_CP_MOL_M3_PER_PA: p_i = C_liquid,i / H_cp
```

A Henry constant without a convention, matrix match, temperature basis, and calibration is unusable.

#### C. Modified Raoult route

```text
p_i = x_i × gamma_i × P_sat,i(T)
```

Nonideal authority order:

1. measured matching-matrix activity/partition evidence;
2. validated, versioned perfume-domain UNIFAC with complete subgroup coverage;
3. validated COSMO-RS/COSMO-SAC adapter with exact parameterization and benchmark error;
4. external nonideal model, review only.

#### D. Ideal Raoult sensitivity

```text
p_i = x_i × P_sat,i(T)
```

This is a loose sensitivity model. It is never measured headspace and does not acquire higher authority through presentation labels.

### G15.08 — Essential-oil partial-pressure diagnostics

For every characterized natural constituent and every executable model, report:

- constituent liquid mole fraction in the finished matrix;
- constituent liquid mole fraction within the characterized natural;
- constituent partial-pressure distribution;
- equilibrium air-concentration distribution;
- constituent OAV distribution, if threshold-compatible;
- `P(OAV>1)`, `P(OAV>3)`, `P(OAV>10)`, and `P(OAV>100)`;
- model authority and limitations.

For the characterized natural subset, compute scenario by scenario:

```text
P_known,natural = sum_i p_i
y_i = p_i / sum_j p_j
E_i = y_i / z_i
```

where `y_i` is estimated vapor fraction and `z_i` is liquid mole fraction within the characterized natural. `E_i` is a headspace-enrichment diagnostic.

The summed partial pressure is labelled:

```text
CHARACTERIZED_CONSTITUENTS_ONLY__NOT_WHOLE_NATURAL_OAV
```

The unresolved mass/profile remainder remains explicit. It is never assigned an invented vapor pressure or threshold.

### G15.09 — Dynamic release and finite-deposit gate

Equilibrium tendency and transport are separate.

The OAV gate does not multiply `gamma` into an arbitrary evaporation-rate constant. A dynamic stage must come from an accepted external owner and declare:

- stage/model version;
- exact input hashes;
- applicability;
- identifiability state;
- finite-mass conservation;
- substrate uptake/back-release/loss assumptions;
- ventilation and geometry;
- timepoints;
- permitted downstream uses.

Still-air diffusion cannot be called human sillage. Skin is a new context and requires separate safety and substrate assumptions.

If no dynamic stage exists, equilibrium screening can be reported, but temporal-performance claims remain unavailable and the row is `REVIEW_REQUIRED` for bench presentation.

### G15.10 — OAV computation and psychometric separation

Strict empirical OAV:

```text
OAV_i(t) = measured C_air,i(t) / compatible T_air,i
```

It requires calibrated, context-matched measured candidate air and a compatible threshold. Raw detector area is not air concentration.

Modeled OAV uses modeled air concentration and stays labelled modeled. Outputs are distributions, not a single magic number.

Direct forced-choice psychometric detection probability is a separate, higher-value perceptual layer when trial-level analytically verified vapor data exist. It does not turn OAV into liking, similarity, or note identity.

### G15.11 — Model disagreement and conservative danger gate

For each component, compare model medians and uncertainty ranges. Default diagnostic bands:

- ratio below 10×: no disagreement escalation;
- 10× to below 100×: `REVIEW_REQUIRED`;
- 100× or greater: `HOLD`.

These are workflow thresholds, not universal scientific constants, and must be calibrated later.

A dangerous result in any plausible, in-domain scenario may block. Dangerous scenarios are not averaged away. A target-specific danger rule requires explicit provenance and cannot be invented from a high OAV alone.

### G15.12 — Negative evidence and target-conflict gate

Known physical negatives override desk scores. The permanent stock regression remains:

```text
14 parts at 10% = 1.4 active
1.4 parts neat = 1.4 active
14 parts neat = 14 active = 10× historical reference -> FAIL
```

High modeled potency in a target-conflicting material triggers a controlled comparison, not automatic deletion or formula mutation.

Recommended carrier-balanced ladder:

```text
0× / 0.5× / 1.0× / 1.5×
```

For extreme traces, use logarithmic or finer levels. Omission/addition and recombination decide structural relevance.

### G15.13 — Claim-language firewall

Forbidden outputs:

- OAV as percent sensory contribution;
- sum of OAVs as mixture intensity;
- highest OAV as the dominant note;
- OAV below one as a deletion rule;
- a single OAV for an EO, absolute, tincture, resin, or opaque base;
- modeled headspace described as measured;
- equilibrium partial pressure described as longevity, projection, or sillage;
- computational PASS described as physical, sensory, safety, or release PASS.

## 4. Output contract

Each row returns:

- exact stock/active arithmetic;
- row state and reason codes;
- natural-profile authority where applicable;
- component-resolved partial-pressure models;
- modeled OAV distributions and exceedance probabilities;
- strict empirical OAV only where valid;
- model-disagreement state;
- dynamic-adapter state;
- controlled comparison required;
- `automatic_formula_mutation=false`.

Formula output returns the worst row state and separate authority flags. A `PASS_SCREENED` OAV result only allows consideration by the next gate.

## 5. Required regressions

Minimum tests:

1. 10% to neat active-equivalence pass;
2. unchanged raw dose after 10% to neat change fails;
3. missing stock fraction holds;
4. w/w versus v/v without density holds;
5. missing air threshold holds;
6. water/air threshold mismatch holds;
7. unprofiled natural holds;
8. whole-natural OAV remains null;
9. relative-area natural remains review-only;
10. constituent partial pressures aggregate scenario by scenario;
11. Henry convention mismatch holds;
12. measured-air method mismatch blocks strict OAV;
13. high model disagreement holds;
14. OAV below one does not delete or mutate a row;
15. known physical negative overrides computational outputs;
16. formula presentation bypass is impossible.

## 6. Current implementation state

The accompanying `oav_gate_reference.py` implements the clean-room input/output contract, exact stock arithmetic, constituent-resolved natural partial-pressure estimates, multiple equilibrium routes, modeled OAV distributions, measured-air strict OAV guards, model disagreement, external dynamic-stage validation, and fail-closed states.

It does **not** install into Perfume-Chem, solve the production dynamic model, calibrate the local perfume domain, measure headspace, validate sensory effects, or authorize compounding.
