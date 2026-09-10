# Evidence-Gated Perfume Design and Reconstruction Method

**Abbreviation:** EG-PDRM  
**Purpose:** A standalone specification for generating, reconstructing, optimizing, building, and validating high-quality perfume formulas without confusing numerical models with olfactory truth.

---

## 1. Core proposition

A high-quality perfume formula is not obtained by maximizing one score.

It is obtained by preserving a clear concept while iteratively aligning:

- chemical identity;
- olfactory architecture;
- temporal architecture;
- mixture interactions;
- matrix behavior;
- physical measurability;
- inventory reality;
- safety scope;
- sensory evidence.

The method is a loop:

```text
Concept lock
→ evidence
→ ideal target
→ architecture and graph
→ chassis/module partition
→ quantitative ensemble
→ inventory-mapped build
→ transactional batch
→ blinded sensory/analytical experiment
→ posterior update
→ new version
```

---

## 2. Required independent records

Maintain separate hashes for:

- `evidence_hash`
- `target_hash`
- `inventory_snapshot_hash`
- `build_plan_hash`
- `bottle_stream_hash`
- `analytical_snapshot_hash`
- `sensory_protocol_hash`
- `sensory_outcome_hash`
- `regulatory_snapshot_hash`
- `release_decision_hash`

No recommendation may use an unstated or stale state.

---

## 3. Concept lock schema

```yaml
name:
mode:
reference:
family:
brand_era:
one_sentence_promise:
signature_contrast:
mandatory_recognizers:
protected_negative_space:
forbidden_drift:
concentration:
matrix:
batch_size:
temporal_targets:
evaluation_substrate:
evaluation_timepoints:
safety_scope:
```

The name and concept outrank aesthetic score inflation.

---

## 4. Evidence ledger

Every claim records:

- source;
- source class;
- exact location;
- identity claim;
- quantity claim;
- independence group;
- contradiction group;
- confidence;
- uncertainty;
- matrix;
- lot;
- date;
- transformation.

Evidence classes:

```text
EXACT
MEASURED_VALIDATED
MEASURED_DEVELOPMENTAL
LITERATURE_DIRECT
LITERATURE_PROXY
CALIBRATED_MODEL
HEURISTIC
SPECULATIVE
UNKNOWN
```

---

## 5. Ideal target construction

Create the target independently of current inventory.

For reconstruction:

1. collect official notes, GC evidence, source formulas, supplier products, and sensory descriptions;
2. resolve identities without collapsing grades or lots;
3. build a complete roster, preserving unknown nodes;
4. construct amount priors with intervals;
5. generate several target candidates;
6. accept a target version only through explicit review.

For creative formulation:

1. define the concept lock;
2. construct functional blocks;
3. choose recognizers and contrasts;
4. create negative space;
5. preserve family boundaries;
6. create a target before inventory substitutions.

---

## 6. Architecture views

### 6.1 Note and time view

Use at least:

- opening;
- transition;
- heart;
- early drydown;
- deep drydown.

### 6.2 Functional view

Each material can carry multiple roles:

```text
recognizer
signature
bridge
volume
lift
diffusion
texture
fixation
shadow
contrast
sweetening
drying
masking risk
family control
technical
```

### 6.3 Chemical view

Record chemical family, scaffold, stereochemistry, polarity, vapor behavior, and natural occurrence.

### 6.4 Graph view

Allowed edge types:

```text
IDENTITY
SCAFFOLD
FUNCTIONAL_GROUP
ODOR_QUALITY
VOLATILITY_OVERLAP
MATRIX_PARTITION
NATURAL_COOCCURRENCE
TEMPORAL_HANDOFF
FUNCTIONAL_SUPPORT
MEASURED_INTERACTION
LITERATURE_INTERACTION
SUBSTITUTION
```

Every edge stores direction, context, evidence, and uncertainty.

Use one to three explicit connection paths for major note transitions.

---

## 7. Chassis and module method

Partition:

```text
target = chassis + parent module
flanker = locked chassis + new module
```

Chassis selection score may consider:

```text
A_i =
w_structure × structural_role
+ w_graph × graph_centrality
+ w_time × temporal_persistence
+ w_recognizer × recognizer_score
+ w_omission × omission_impact
- w_mobility × flanker_mobility
```

Do not trust the score until validated by removal curves and sensory omission.

Support sockets:

- signature;
- heart;
- base;
- texture;
- top contrast;
- atmospheric effect.

A module includes volume/active budget, anchor floors, forbidden drift, and compensation options.

---

## 8. Anti-compression

Before substituting or simplifying, compare:

1. chemical scaffold/stereoisomer;
2. grade;
3. volatility/time;
4. quality;
5. diffusion;
6. texture;
7. substantivity;
8. partition;
9. GC/RI;
10. GC-O;
11. official-source support;
12. target-roster identity.

Output:

```text
EXACT_EQUIVALENT
SAME_CHEMICAL_DIFFERENT_STOCK
GRADE_VARIANT
FUNCTIONAL_OVERLAP
PARTIAL_SUBSTITUTE
NON_EQUIVALENT
UNKNOWN
```

Never convert `UNKNOWN` to exact.

---

## 9. Quantitative model

### 9.1 Rank prior

```text
q_r = B × (r + b)^(-p) / Σ(k + b)^(-p)
```

Generate multiple `p`, `b`, and uncertainty settings.

### 9.2 Active accounting

For compatible basis:

```text
q_active = q_raw × f_active
```

Partition inactive quantity according to declared diluent.

### 9.3 Mass-volume

```text
m = ρV
```

with uncertainty and conditions.

### 9.4 Concentration

Store raw and active concentration, with w/w, v/v, w/v, or mass/volume basis explicit.

### 9.5 OAV

```text
OAV = contextual concentration / contextual detection threshold
```

Never use OAV as percent contribution.

### 9.6 Headspace

Candidate equilibrium model:

```text
p_i = x_i γ_i P_i^sat
```

with explicit model and domain.

---

## 10. Candidate ensemble

Generate a Pareto set:

- reference-faithful;
- conservative;
- median;
- signature-forward;
- texture-forward;
- diffusion-forward;
- measurable-low-risk;
- uncertainty-stress.

Hard constraints:

- total quantity;
- exact accounting;
- target identity;
- family;
- chassis anchors;
- module envelope;
- safety scope;
- inventory for build candidates;
- minimum measurable increment.

Soft objectives:

- concept fidelity;
- recognizer profile;
- temporal continuity;
- texture;
- diffusion;
- contrast;
- elegance;
- cost;
- waste.

Do not reduce all soft objectives to one unexplained score.

---

## 11. Experimental optimization

### 11.1 Developmental design

Use constrained mixture DOE or Bayesian optimization only after defining measurable responses.

Possible response variables:

- trained-panel attribute intensities;
- profile distance to reference;
- discrimination rate;
- temporal coherence;
- analytical headspace ratios;
- user preference;
- physical stability.

### 11.2 Omission/addition

Test suspected key materials and key associations.

### 11.3 Dose-range

Use logarithmic or otherwise justified dose spacing around the current estimate.

### 11.4 Held-out validation

Keep confirmatory samples and outcomes outside model fitting.

---

## 12. Build mapping

Each build line stores:

- target line;
- exact selected lot;
- raw amount;
- active amount;
- basis;
- density;
- uncertainty;
- measurability;
- substitution state;
- preserved functions;
- lost functions;
- rationale.

User-facing output defaults to µL. Canonical quantities remain unit-safe.

---

## 13. Manufacturing SOP

Each build version has an SOP.

Potential ordering logic:

1. viscous resins and pre-dilutions;
2. low-volatility musks/fixatives;
3. amber woods and structural base;
4. earth/vetiver/wood modifiers;
5. diffusive scaffold;
6. floral/ionone bridges;
7. aromatic/signature module;
8. citrus and volatile top;
9. designated carrier/solvent balance;
10. homogenization and maturation.

The exact order is recipe-specific.

For the reusable night chassis, retain the known successful pattern:

```text
woods/musks/coumarinic base first
→ heart
→ signature slot
→ DPG balance last
→ mature ~14 days
→ evaluate 0/5/30 min/2 h/4 h
```

---

## 14. Transactional execution

```text
proposal
→ human confirmation
→ measurement
→ atomic bottle event + inventory movement
→ replay
→ state diff
```

Corrections append. Transfers are atomic. Idempotency keys prevent duplicate retries.

---

## 15. Sensory validation

Choose methods by claim.

### Descriptive profile

Use trained assessors, lexicon, references, repeats, and assessor monitoring.

### Directional attribute

Use paired comparison or 2-AFC where appropriate.

### Overall difference

Triangle or tetrad only when carryover and fatigue permit.

### Similarity/equivalence

Preregister an equivalence margin and profile-distance rule. Nonsignificance is not equivalence.

### Temporal behavior

Use fixed-time ratings, time-intensity, TDS, or TCATA according to the claim.

### Preference

Use target consumers, not only trained assessors.

---

## 16. Update and release

After each experiment:

- preserve raw data;
- record deviations;
- run locked analysis;
- append evidence;
- update posterior;
- create a new version.

Release is scoped:

```text
ARITHMETIC_VERIFIED
BUILD_VERIFIED
ANALYTICAL_VALIDATED_FOR_SCOPE
SENSORY_PROFILE_VALIDATED
SIMILARITY_VALIDATED
PREFERENCE_VALIDATED
COMPLIANCE_SCREENED_FOR_SNAPSHOT
SCIENTIFIC_RELEASE_FOR_SCOPE
```

---

## 17. Software modes mapped to the method

| Mode | Method steps |
|---|---|
| RECONSTRUCTION | F1–F10 |
| CREATIVE_FORMULATION | F1–F3, F5–F12 |
| STRUCTURAL_CHASSIS | F3–F5 |
| FLANKER_MODULE | F1, F3–F5, F10 |
| INVENTORY_MAPPING | F2, F7, F10–F12 |
| LIVE_BATCH | F12–F13 |
| BATCH_RESCUE | state diff, candidate correction, F13 |
| SENSORY_EXPERIMENT | F14–F16 |
| ANALYTICAL_INTERPRETATION | F7–F9, F16 |
| COMPLIANCE_BUILD | F7, regulatory snapshot |
| RELEASE_REVIEW | F16–F17 |

---

## 18. Minimum verification suite

- property-based conservation;
- unit and basis conversion;
- inventory mapping identity cases;
- anti-compression cases;
- empty input;
- candidate reproducibility;
- canonical hashing;
- build-plan versioning;
- event replay and corrections;
- atomic transaction rollback;
- formula/chassis/module invariants;
- OAV authority labels;
- model abstention;
- sensory protocol locking;
- release-scope blocking.
