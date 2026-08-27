# DNA-Preserving Structural Chassis Protocol

**Version:** 2.0  
**Purpose:** Derive flanker-capable structural chassis from a complete perfume reconstruction without stripping away the parent perfume’s recognizable identity.  
**Claim limits:** A passing chassis is an internally consistent design hypothesis. It is not proof of the proprietary formula, sensory equivalence, safety compliance, or commercial authorization.

## 1. Core principle

A structural chassis must be derived from the full parent target, not invented by deleting all obvious notes.

Let the complete target formula be:

\[
T = \{T_i\}_{i=1}^{n}
\]

For every material \(i\), partition the target into a fixed core \(C_i\) and the exact parent module \(M_{p,i}\):

\[
T_i = C_i + M_{p,i}
\]

The parent recombination must be exact:

\[
C + M_p = T
\]

An alternative flanker is:

\[
F_j = C + M_j
\]

The alternative module \(M_j\) is valid only if it satisfies the declared socket total, active/carrier constraints, protected-recognizer floors, functional coverage, temporal envelope, family-drift limits, and blind sensory validation.

A neutral solvent slot is not automatically a good chassis. If removing a signature accord makes the core cease to smell recognizably related to the parent, too much DNA was assigned to the module.

## 2. Required upstream artifacts

Do not design a chassis until these files exist:

1. `evidence.csv`
2. `identity_registry.csv`
3. `target_formula.csv`
4. `functional_graph.json`
5. `target_uncertainty.csv`
6. `TARGET_RECON_HASH`
7. a reference-specific sensory lexicon
8. at least one parent target recombination batch

The target must remain independent of inventory. Inventory mapping and physical bottle additions use separate ledgers.

## 3. Five-layer chassis model

### 3.1 Immutable structural core

The immutable core contains materials whose removal damages the parent’s:

- volume;
- spatial profile;
- musk texture;
- woody architecture;
- floral transmission;
- persistent family identity;
- matrix behavior;
- or long drydown.

Structural abundance alone does not make a material immutable. The criterion is whether it carries a role that every plausible family member must retain.

### 3.2 Protected recognizer floor

Headline recognizers are normally split, not deleted.

For protected recognizer \(i\):

\[
C_i \ge f_iT_i
\]

where \(f_i\) is the experimentally determined minimum core fraction.

Examples:

- cardamom in a La Nuit-type family;
- ginger in an L’Homme-type family;
- iris/soap, pepper, patchouli, and neroli in a Prada L’Homme-type family;
- aldehydic-floral transitions in many classic Chanel structures;
- incense/resin continuity in many Amouage structures.

The parent module may restore or intensify the recognizer, but the fixed core retains enough for family recognition.

### 3.3 Interface ring

The interface ring connects a replaceable accord to the fixed structure.

Typical interface materials include:

- linalool and linalyl acetate;
- Hedione and muguet materials;
- ionones;
- transparent woods;
- minor musks;
- citrus esters;
- green materials;
- spice connectors;
- salicylates;
- aldehydic traces;
- and diffusive natural fractions.

Interface materials may be split between core and module. Removing the interface ring creates a pasted-on flanker effect.

### 3.4 Accord socket

The socket is the mobile part of the formula. It has an exact raw total and explicit active/carrier accounting.

A socket may contain:

- a signature spice accord;
- fruit;
- watery-green material;
- a floral direction;
- a resin/incense direction;
- sweetness;
- selected woods;
- or a thematic natural.

The socket is not defined only by volume. Its envelope must constrain active load, volatility, texture, family drift, and protected recognizers.

### 3.5 Compensation vector

Replacing one accord with another changes more than note identity.

A heavy immortelle/tobacco module may need:

- more aromatic lift;
- less coumarinic sweetness;
- a dry-violet bridge;
- lighter carrier behavior;
- and retained cardamom.

A bright citrus module may need:

- enough heart material to avoid a hollow middle;
- restrained aldehydes;
- and a drydown hand-off.

These compensating materials belong inside the module so the fixed core is not repeatedly rewritten.

## 4. Functional graph

Represent each target material as a node. Record edges for:

- reinforcement;
- temporal hand-off;
- masking;
- contrast;
- shared accord;
- texture support;
- diffusion support;
- and module-to-core attachment.

A useful node schema is:

```json
{
  "identity": "Cardamom Oil",
  "roles": ["signature_recognizer", "cool_spice", "top_to_heart_bridge"],
  "time_windows": ["opening", "heart"],
  "blocks": ["spice", "aromatic"],
  "source_confidence": 0.8,
  "quantity_confidence": 0.35,
  "substitution_tolerance": "low",
  "neighbors": ["bergamot", "lavender_system", "cashmeran", "coumarin"]
}
```

Graph analysis should detect:

- isolated signature nodes;
- single points of failure;
- overdependent hubs;
- missing transitions;
- and one-stock-to-many-target compression.

## 5. Anchor scoring

Estimate whether a material belongs in the fixed core using separate dimensions:

\[
A_i =
w_sS_i +
w_gG_i +
w_tT_i +
w_rR_i +
w_oO_i -
w_mM_i
\]

where:

- \(S_i\): signature importance;
- \(G_i\): graph centrality;
- \(T_i\): temporal coverage;
- \(R_i\): reference evidence;
- \(O_i\): omission-test importance;
- \(M_i\): module mobility.

Do not collapse the dimensions permanently. The scalar is only a sorting aid.

Suggested classification:

- high anchor score: `IMMUTABLE_CORE`;
- high signature, moderate mobility: `PROTECTED_ANCHOR`;
- high bridge centrality: `INTERFACE_RING`;
- high thematic mobility: `MODULE_MOBILE`;
- technical or carrier: separate class;
- unresolved but important: `UNKNOWN_PROTECTED`.

## 6. Determine socket size

Do not choose 100 µL, 300 µL, or 10% by habit.

Generate a removal curve:

1. Sort candidate mobile material portions by mobility.
2. Remove 2%, 4%, 6%, 8%, 10%, and 15% of raw concentrate into trial modules.
3. Recombine the exact parent at each size.
4. Evaluate the core alone and the recombined parent.
5. Find the largest socket where:
   - core-alone recognition remains above the project floor;
   - parent recombination remains exact;
   - no interface block is amputated;
   - and alternative modules can still achieve meaningful variation.

For a 4,500 µL concentrate:

- 300 µL is 6.67%;
- 350 µL is 7.78%.

Those sizes are case-study outcomes, not universal standards.

## 7. Derive the parent module

For every row:

```text
parent_module_raw = target_raw - core_raw
parent_module_active = parent_module_raw * active_fraction
```

Hard invariants:

```text
target_raw == core_raw + parent_module_raw
target_active == core_active + parent_module_active
sum(parent_module_raw) == socket_raw
sum(core_raw) == target_total - socket_raw
```

The parent module is not separately optimized. It is the exact remainder after the core partition.

## 8. Module envelope

At minimum record:

```json
{
  "socket_raw_uL": 300,
  "active_range_uL": [180, 300],
  "required_core_floors": {},
  "required_module_roles": [],
  "family_drift_caps": {},
  "opening_share_range": [0.20, 0.65],
  "heart_share_range": [0.20, 0.65],
  "base_share_range": [0.05, 0.40],
  "carrier_range_uL": [0, 120]
}
```

### 8.1 Raw total

The raw total must match the socket exactly.

### 8.2 Active range

Two modules with the same raw volume may have radically different odorant-active load because of diluted stocks. Compare active amount separately.

### 8.3 Carrier composition

DPG, DEP, TEC, ethanol, benzyl salicylate, and other carriers alter release. Carrier is part of the module design.

### 8.4 Protected anchors

Some recognizers may be mandatory in the module as well as the core.

### 8.5 Family caps

A family-compatible flanker may increase a direction without renaming the perfume.

Examples of drift caps:

- gourmand;
- marine;
- leather;
- smoke;
- animalic;
- lactonic fruit;
- medicinal aromatic;
- or resin.

These caps should be measured through a project-specific sensory vector, not a generic odor-family label alone.

## 9. Designing alternative modules

### Step 1: Write the flanker direction

Example:

```text
Parent DNA: cardamom, lavender, violet/coumarin, cedar-vetiver, clean musks
Flanker direction: immortelle and dry tobacco
Forbidden drift: maple dessert, curry, clove oriental, leather dominance
```

### Step 2: Select thematic materials

Choose the smallest set that creates the new accord without replacing the parent’s whole sensory object.

### Step 3: Add interface materials

Select connectors to the protected core.

### Step 4: Add compensation

Correct weight, sweetness, dryness, volatility, and temporal gaps.

### Step 5: Reconcile socket total

Add carrier only after active design is complete.

### Step 6: Validate in an identical matrix

Compare parent and flanker at equal:

- concentrate loading;
- ethanol/water system;
- maturation;
- application amount;
- blotter;
- and timepoints.

## 10. Sensory validation

Minimum blinded set:

1. complete target;
2. fixed core alone;
3. core plus parent module;
4. core plus alternative module;
5. complete target with the thematic accord directly added, as a control;
6. one critical omission from the alternative module.

Evaluate at:

- application;
- 5 minutes;
- 30 minutes;
- 2 hours;
- 4 hours;
- 8 hours;
- and later when the family requires it.

Score separately:

- parent-family recognition;
- flanker distinction;
- signature preservation;
- transition quality;
- projection;
- density;
- sweetness;
- roughness;
- and drydown continuity.

## 11. Acceptance logic

A module is not accepted merely because it smells pleasant.

Example acceptance conditions:

```text
parent-family recognition >= 70/100 at 5 min, 30 min, and 2 h
flanker distinction >= 25/100 versus parent
forbidden drift <= 20/100
no time window with a missing bridge score below 50/100
parent recombination error == 0
```

Thresholds must be set before evaluation.

## 12. Unknown and captive materials

An unresolved but important function remains an explicit node:

```text
UNKNOWN_RADIANT_MUGUET_01
UNKNOWN_DRY_AMBERWOOD_02
UNKNOWN_CLEAN_MUSK_03
```

The target retains the unknown. A build may test a replacement accord, but the mapping must state the expected loss.

Unknown nodes that appear central in the functional graph should usually remain protected in the core.

## 13. Common failure modes

1. Removing every headline note into a neutral slot.
2. Treating equal raw volume as equal sensory power.
3. Ignoring carrier differences.
4. Letting a theme erase the recognizer.
5. Using one material as several independent interface roles.
6. Redesigning the fixed core for every module.
7. Validating only the opening.
8. Comparing unequal concentration or maturation.
9. Calling a pleasant fragrance a successful flanker without blinded family-recognition testing.
10. Altering the target because inventory lacks a material.

## 14. Script order

```bash
python scripts/chassis_tools.py validate-target formulas/TARGET.csv
python scripts/chassis_tools.py validate-partition formulas/PARTITION.csv --socket 300
python scripts/chassis_tools.py validate-module modules/MODULE.csv --socket 300
python scripts/chassis_tools.py diff-parent formulas/PARTITION.csv modules/PARENT.csv
python scripts/validate_suite.py
```

The deterministic scripts verify arithmetic and schema. Sensory identity remains an experimental authority.
