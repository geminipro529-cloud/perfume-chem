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
