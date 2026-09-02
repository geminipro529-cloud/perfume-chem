# Program v3 Release Gates

**Artifact ID:** `PCV3-C00-F006`  
**Integrator:** `PCV3-INTEGRATOR`  
**Prepared:** `2026-08-07`  
**Current final disposition:** `HOLD — EMPIRICAL RELEASE NOT AUTHORIZED`

## 1. Gate doctrine

Program v3 uses noncompensatory gates. A score, average, commercial opportunity, high complexity class, strong computational result, or attractive design cannot cancel a missing authority, identity failure, physical-chemistry failure, blind compromise, safety failure, or absent observation.

Each gate returns one of:

- `PASS`
- `FAIL`
- `HOLD`
- `NOT_APPLICABLE`
- `NOT_RUN`

`PASS` is permitted only at the gate’s declared evidence level. A computational pass is never promoted into a physical, sensory, analytical, safety, or release pass.

## 2. Claim ladder

| Claim level | Minimum evidence |
|---|---|
| Architecture exists | Versioned design artifact and provenance |
| Computational candidate | Deterministic input, model/engine version, assumptions, result, and scope |
| Physical batch exists | Canonical `PB-` record linked to `BF-` and exact addition/provenance records |
| Physical compatibility | Performed preparation/mixture checks with observations or measurements |
| Sensory observation | Coded sample, assessor, condition, timepoint, replicate, and append-only `OBS-` |
| Measured analytical result | Calibrated `AnalyticalRun`, measurement, QC, and uncertainty |
| Scoped interaction result | Performed exact-material test plus decision and hypothesis revision |
| Similarity result | Matched coded comparison to authenticated exact target version |
| Hedonic result | Coded sensory observations under the declared population and protocol |
| Broad-appeal claim | Defined target population, appropriate panel, preregistered analysis, and result |
| Stability claim | Formula/process/package-specific performed stability protocol |
| Safety/regulatory authorization | Current formula-specific competent review |
| Empirical release | Every applicable release gate passes |

## 3. Gate register

### RG0 — Authority and provenance lock

**Purpose:** Establish the controlling files, versions, hashes, source hierarchy, and unresolved conflicts.

**Pass requires:**

- all release-critical authorities present as exact bytes;
- exact versions and SHA-256 values;
- superseded, duplicate-suffix, unsynced, and historical sources quarantined;
- every authority conflict resolved or explicitly held;
- source-byte ancestry adequate for the claim.

**Current state:** `HOLD`

**Current blockers:**

- inherited 18/18 Phase G source-byte proof and full PRE_DEF ledger remain missing;
- exact byte closure for some upstream authorities and specialist packages remains partial;
- exact SYNCED workbook byte hashes were not independently closed in this runtime.

**Prohibited shortcut:** reconstructing missing bytes or expanding abbreviated hashes.

---

### RG1 — Artifact existence and integrity

**Purpose:** Confirm that required artifacts exist, parse, match immutable IDs, and carry traceable hashes.

**Pass requires:**

- all required files present and non-empty;
- JSON and JSON Schema parse;
- CSVs have stable headers and row widths;
- one immutable ID per required artifact;
- hashes verified on exact bytes;
- package members and manifest agree.

**Current state:** `CONDITIONAL PASS FOR INTEGRATION / HOLD FOR BYTE-COMPLETE REPOSITORY IMPORT`

**Basis:**

- 58/58 required specialist artifacts were located at their declared scope;
- 44 required specialist artifacts have worker-ledger hashes;
- 14 required Chat 1/3 artifacts remain `PARTIAL_HASH_CLOSURE`;
- all final integration artifacts are locally created and hashed.

---

### RG2 — Canonical identity and schema integrity

**Purpose:** Prevent target, build, batch, container, coded sample, observation, and decision identities from collapsing.

**Pass requires:**

- type-prefixed immutable IDs;
- exact foreign-key resolution;
- `PB-` references `BF-`;
- container contents are physical;
- coded sample contains no true origin;
- exact-stock, lot, product basis, dilution, and preparation remain separate;
- raw records append-only;
- blind-decode lifecycle enforced.

**Current state:** `PASS FOR SPECIFICATION / NOT EVALUATED FOR A PARTICULAR FORMULA OR DATASET`

**Residual implementation hold:** canonical schema registry and validators are not yet installed in the target repository.

---

### RG3 — Formula arithmetic and active accounting

**Purpose:** Demonstrate exact totals, active/raw/carrier accounting, dilution feasibility, and operation sequence.

**Pass requires for a formula:**

- exact target and build formula IDs and hashes;
- active versus supplied-stock quantities separated;
- carrier balance nonnegative;
- every dilution physically possible;
- product-basis unknowns retained as unknown;
- no direct sub-device-limit dosing without a valid premix;
- deterministic calculations reproduce.

**Current state:** `NOT_RUN FOR ANY FINAL PROGRAM V3 RELEASE CANDIDATE`

**Prohibited shortcut:** treating spreadsheet arithmetic from an unscoped candidate as physical-batch proof.

---

### RG4 — Actual target-engine qualification

**Purpose:** Demonstrate that the production engine implements the declared gates correctly.

**Pass requires:**

- actual repository path, commit/tree hash, entry point, and dependency lock;
- implemented adapter with zero required-field loss;
- exact expected state, failed gates, and failure codes for all fixtures;
- mandatory mutation score 100%;
- required Monte Carlo runs and independent confirmation;
- two clean-environment reproductions;
- immutable inputs, outputs, environments, seeds, and hashes.

**Current state:** `NOT RUN`

**Authoritative boundary:** the reference checker is not the target engine.

**Release effect:** blocks any claim that the actual engine is qualified.

---

### RG5 — Physical preparation and chemistry

**Purpose:** Establish that stocks, preparations, mixtures, and final candidates are physically executable and compatible.

**Pass requires:**

- exact supplier/lot/strength/solvent/product-basis authority;
- actual preparation records;
- calibrated equipment and uncertainty;
- no unresolved haze, precipitation, crystallization, phase separation, oxidation anomaly, color failure, resin overload, or solvent incompatibility;
- defined maturation and storage;
- formula-specific stability gate when release is intended.

**Current state:** `NOT RUN`

**Release effect:** hard release block.

---

### RG6 — Interaction and exact-stock behavior evidence

**Purpose:** Establish scoped full-mixture or material behavior rather than hypothesis coverage alone.

**Pass requires:**

- performed exact-material tests;
- ratio and total load separated;
- A-alone and B-alone controls;
- matrix, substrate, application, maturation, timepoints, assessor, and replicate locked;
- raw observations and/or measurements;
- decision plus scoped hypothesis revision;
- exact generalization limit.

**Current state:** `NOT RUN / NOT TESTED`

**Basis:** Chat 4 is designed but unexecuted. Chat 5 is a 57-row queue with empirical fields `NOT_TESTED`.

---

### RG7 — Sensory identity and target similarity

**Purpose:** Establish actual perceived identity or reconstruction similarity.

**Pass requires:**

- authenticated exact target/version reference;
- matched concentration, matrix, substrate, application, maturation, and storage scope;
- coded samples and restricted decode;
- qualified assessor(s), repeated timepoints, and replicates;
- preregistered decision rule;
- raw observations locked before decode;
- limitations and population stated.

**Current state:** `NOT RUN`

**Prohibited shortcut:** using note agreement, formula resemblance, modeled headspace, or liking as a similarity pass.

---

### RG8 — Analytical and strict OAV claims

**Purpose:** Support measured headspace, quantitative analysis, GC-O, or strict empirical OAV at the claimed scope.

**Pass requires:**

- fit-for-purpose analytical method;
- raw-file hashes;
- standards, calibration, QC, response factors where quantitative;
- matrix-, surface-, application-, and timepoint-matched measurements;
- measurement uncertainty;
- threshold source and compatibility for OAV;
- unknowns retained rather than forced into convenient identities.

**Current state:** `NOT RUN`

**Explicit nonclaims:** no measured headspace and no strict empirical OAV were created by Program v3 integration.

---

### RG9 — Meaningful complexity, ablation, perturbation, and anti-collapse

**Purpose:** Determine whether the claimed complexity class is functional, coherent, non-padded, and robust.

**Pass requires:**

- v3 complexity vector;
- canonical identity deduplication;
- product bases counted once;
- functional, recognizer, interaction, temporal, textural, and contrast coverage;
- computational ablation and perturbation with provenance;
- post-ablation class integrity;
- sibling anti-collapse checks;
- physical confirmation where the claim is perceptual.

**Current state:** `MODEL AVAILABLE / NO FINAL FORMULA-SPECIFIC EMPIRICAL PASS`

**Compatibility rule:** 50/65 row floors are hard only for explicit v2 compatibility or an authoritative target-specific floor.

---

### RG10 — Hedonic and commercial claims

**Purpose:** Establish beauty, liking trajectory, perceived quality, wearability, artistic interest, annoyance, fatigue, or broad appeal.

**Pass requires:**

- coded physical samples;
- raw assessor-timepoint records;
- distributions and negative tails;
- similarity kept separate;
- defined target population for broad appeal;
- appropriate panel and preregistered analysis;
- no overall compensating score.

**Current state:** `UNPOPULATED / NOT RUN`

**Prohibited shortcut:** inferring beauty or broad appeal from complexity, formula rows, user preference, style inference, or commercial popularity.

---

### RG11 — Manufacturability, cost, supply, and stability

**Purpose:** Support formula-specific production and release positioning.

**Pass requires:**

- current supplier and cost basis date;
- exact formula and lots;
- premix, microdosing, mixing, filtration, maturation, and scale-up records;
- supply-fragility assessment;
- performed physical stability study;
- child formula identity for any formula-changing remediation.

**Current state:** `UNPOPULATED / NOT RUN`

**Boundary:** production practicality cannot silently rewrite the target.

---

### RG12 — Safety and regulatory authorization

**Purpose:** Determine whether the exact formula, concentration, package, use case, and jurisdiction may proceed to skin, consumer, or market use.

**Pass requires:**

- current supplier SDS/IFRA and other applicable documents;
- exact formula and concentration;
- formula-specific competent review;
- allergen and jurisdictional assessment;
- documented authorized use scope.

**Current state:** `NOT AUTHORIZED`

**Release effect:** hard block on skin, consumer, and commercial use.

---

### RG13 — Final release authorization

**Purpose:** Issue a claim-specific release decision only after all applicable gates pass.

**Pass requires:**

- RG0–RG12 applicable gates are `PASS` or documented `NOT_APPLICABLE`;
- no open program hold;
- release class and purpose stated;
- exact formula, batch, package, and lineage frozen;
- final decision linked to all evidence inputs and provenance;
- limitations disclosed.

**Current state:** `HOLD`

## 4. Release-class boundaries

| Release class | Additional evidence required | Not automatically claimed |
|---|---|---|
| `ARTISTIC MASTER` | Coded hedonic evaluation appropriate to artistic claim | broad appeal, similarity, low cost, stability |
| `BROAD_APPEAL EDIT` | Defined population and panel evidence | universal appeal, similarity |
| `COST_CONTROLLED EDIT` | Current cost objective and formula-specific validation | equal beauty, similarity, stability |
| `INVENTORY_FIT PILOT` | Executable build and explicit substitution losses | target identity, production release |
| `STABILITY_OPTIMIZED EDIT` | Performed stability program | stability before results |
| `REFERENCE RECONSTRUCTION` | Exact matched target comparison | exact factory formula, beauty, broad appeal |

A release-class label cannot bypass RG0–RG13.

## 5. Current gate dashboard

```text
RG0  AUTHORITY / PROVENANCE              HOLD
RG1  ARTIFACT INTEGRITY                  CONDITIONAL PASS FOR INTEGRATION
RG2  CANONICAL SCHEMA                    PASS FOR SPECIFICATION
RG3  ARITHMETIC / ACTIVE ACCOUNTING      NOT RUN FOR FINAL CANDIDATE
RG4  TARGET ENGINE QUALIFICATION         NOT RUN
RG5  PHYSICAL CHEMISTRY                  NOT RUN
RG6  INTERACTION / MATERIAL BEHAVIOR     NOT RUN / NOT TESTED
RG7  SENSORY / SIMILARITY                NOT RUN
RG8  ANALYTICAL / STRICT OAV             NOT RUN
RG9  COMPLEXITY / ABLATION               MODEL AVAILABLE; EMPIRICAL PASS ABSENT
RG10 HEDONIC / COMMERCIAL                UNPOPULATED
RG11 MANUFACTURING / STABILITY           UNPOPULATED / NOT RUN
RG12 SAFETY / REGULATORY                 NOT AUTHORIZED
RG13 FINAL RELEASE                       HOLD
```

## 6. Final release statement

```text
PROGRAM V3 INTEGRATION PACKAGE: COMPLETE_WITH_HOLDS
PROGRAM APPROVAL: NOT ISSUED
EMPIRICAL PERFUME RELEASE: NOT AUTHORIZED
SKIN OR CONSUMER USE: NOT AUTHORIZED
PHASE G: LOCKED / NOT AUTHORIZED
```
