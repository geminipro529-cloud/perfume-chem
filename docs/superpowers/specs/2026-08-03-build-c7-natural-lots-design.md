# Build C7 Lot-Aware Natural Materials Design

## Decision

Build C7 will add an immutable, deterministic natural-lot authority layer at
`engine/physics/natural_lots.py`. It will not alter the disconnected
`engine/reconstruction/natural_lots.py` stub, the generic literature profile
runtime, production callers, databases, or migrations.

The new layer is a contract and selection boundary. It records exact-lot data,
preserves analytical meaning, selects a declared composition source by a fixed
precedence, emits separate projection artifacts, and abstains when an intended
claim lacks authority. It does not calculate headspace OAV, approve regulatory
use, infer adulteration, or convert relative chromatography into concentration.

## Evidence and existing boundaries

The canonical C0 inventory establishes two facts that C7 must preserve:

- generic natural-composite headspace/OAV is a literature-derived,
  non-batch-specific compatibility proxy and is not regulatory composition;
- the in-memory reconstruction lot registry is a disconnected, untested stub
  with no authoritative lot data or consumer.

Build B5 provides useful exact-subject analytical patterns and Build B6
provides useful regulatory-profile separation, but C7 will reference their
immutable IDs and hashes instead of importing backend services. A bounded
DeepLuna Fast read audit independently reproduced these boundaries and found no
reason to change them. Sol owns this architecture and acceptance decision.

## Scope

C7 may change only:

- this design;
- `docs/superpowers/plans/2026-08-03-build-c7-natural-lots.md`;
- `engine/physics/natural_lots.py`;
- `engine/physics/__init__.py`;
- `engine/project_verification.py`;
- `tests/test_c7_natural_lots.py`;
- the C7 export assertion in `tests/test_c3_model_interface.py`;
- C7 verification evidence after implementation.

C7 will not change:

- production API, service, UI, or orchestration callers;
- database models, database contents, migrations, WAL, or SHM state;
- inventory, formula, scientific-data, or generated product artifacts;
- the legacy reconstruction lot stub;
- generic natural profile coefficients or current compatibility behavior;
- C8 OAV, mixture-interaction, or sensory logic.

## Public contract

### Closed vocabularies

`ConstituentBasis` is exactly:

- `CALIBRATED_MASS_FRACTION`;
- `CALIBRATED_MOLAR_FRACTION`;
- `ESTIMATED_MASS_FRACTION`;
- `RESPONSE_CORRECTED_RELATIVE_FRACTION`;
- `NORMALIZED_AREA_PERCENT`;
- `RELATIVE_RESPONSE`;
- `PRESENCE_ONLY`;
- `LITERATURE_RANGE`;
- `UNKNOWN`.

Additional closed vocabularies describe source-document kind, identity
confidence, observation origin, calibration state, censoring, review state,
composition authority, composition completeness, unresolved-fraction kind and
disclosure state, selection status, projection family/status, and authenticity
decision. Parsers reject unknown enum values and unknown mapping fields.

### Exact lot identity

`NaturalMaterialLot` records:

- stable material and lot IDs;
- material name, botanical species, variety or chemotype, plant part, and
  geographic origin;
- harvest or production date;
- extraction method plus processing/fractionation/rectification/FCF/aging
  declarations;
- supplier, supplier product, and supplier lot;
- receipt and opening state/dates;
- storage conditions and oxidation/stability observations;
- exact-lot COA/SDS/specification/analytical source references;
- exact-lot analytical-run authority references;
- authenticity/quality state;
- explicit identity fields whose value is unknown.

Unknown identity metadata remains explicit. An exact supplier lot is still
required; C7 never manufactures one from a material name. Opening chronology,
source binding, analytical subject binding, duplicate IDs, and all content
hashes fail closed.

### Constituent observations

`ConstituentObservation` records one named identity and its confidence, origin,
value or range, exact basis, method, calibration/response-model state,
uncertainty, LOD/LOQ and censoring, source hash, exact lot, analytical run, and
review state.

Basis-specific rules are structural:

- calibrated mass/molar fractions require calibrated response authority and a
  validated response-model reference;
- response-corrected relative fractions require a response-corrected model;
- normalized area percent remains in the range 0-100 and must retain that
  basis; it cannot be emitted as a mass or molar fraction;
- fraction-valued bases remain in the range 0-1;
- relative response is finite and nonnegative;
- `PRESENCE_ONLY` and `UNKNOWN` carry no numeric value;
- `LITERATURE_RANGE` carries ordered lower/upper bounds, not a fabricated point
  estimate;
- censored observations carry the applicable LOD/LOQ and no detected value;
- exact-lot measured observations require an exact-lot analytical run.

### Unresolved composition

`UnresolvedFractionObservation` preserves these categories independently:

- unknown peak;
- coelution;
- unresolved group;
- unidentified GC-O event;
- below quantitation;
- unassigned mass;
- unassigned area.

Every `NaturalCompositionProfile` includes an
`UnresolvedFractionDisclosure`, even when the source did not report unresolved
composition. The disclosure states `PRESENT`, `NOT_REPORTED`, or
`REVIEWED_NONE_OBSERVED`; omission is impossible. Named constituent totals are
reported by their original bases but are never normalized or forced to close
to one or 100 percent.

### Composition authority and precedence

`CompositionAuthority` follows this exact order:

1. `EXACT_LOT_QUANTIFIED`;
2. `EXACT_LOT_RELATIVE_PROFILE`;
3. `SUPPLIER_BATCH_SPECIFIC`;
4. `SPECIFIC_LITERATURE_PROXY`;
5. `GENERIC_MATERIAL_PROXY`;
6. `UNKNOWN`.

`select_natural_composition` accepts an exact requested lot and a set of
versioned profiles. It matches lot, supplier batch, and proxy scope exactly,
then selects the single highest-authority candidate. Equal-rank disagreement
returns `AMBIGUOUS`; no admissible profile returns `ABSTAINED`. Any fallback
records its precedence rank, fallback steps, authority loss, and widened
uncertainty category. C7 uses no arbitrary numerical widening multiplier.

Authority/profile invariants prevent an exact-lot label on a generic profile,
require exact-lot observation binding for levels 1-2, require exact supplier
batch binding for level 3, require declared botanical/extraction proxy scope for
level 4, and prohibit observations on an `UNKNOWN` profile.

### Separate projections

`build_natural_projection` emits a versioned artifact for exactly one family:

- `OLFACTORY_HEADSPACE`;
- `REGULATORY_ALLERGEN`;
- `IDENTITY_AUTHENTICITY`.

Projection entries retain the observation value, range, basis, lot ID, source
hash, and profile hash byte-for-byte. Projection building never performs basis
conversion.

Olfactory/headspace and identity/authenticity projections may expose explicit
relative or proxy data with limitations. A regulatory/allergen projection is
available only from a complete exact-lot quantified or supplier-batch profile
whose entries are calibrated mass fractions and whose unresolved review is
complete. Otherwise it is `WITHHELD`, with no answer-bearing entries. No family
artifact can be relabeled as another family.

### Authenticity and quality

`AuthenticityReferenceRange` retains the reference basis and source hash.
`assess_authenticity_profile` compares only basis-compatible values. It records
expected ranges, deviations, explicit chemotype mismatch, caller-supplied
possible-adulteration indicators, unresolved-composition disclosure, decision,
and limitations. It does not infer absolute concentration or adulteration from
area percent alone.

### Aging observations

`LotAgingObservation` versions the measured state of one immutable lot. A
validated series requires:

- one unchanged lot ID;
- contiguous positive sequence numbers;
- strictly increasing timezone-aware observation times;
- an exact previous-snapshot hash chain;
- explicit storage, oxidation/stability, source, and analytical-run references.

The series cannot mutate or replace `NaturalMaterialLot` identity.

## Determinism and serialization

All public records are frozen, slotted dataclasses. Unordered inputs are
canonicalized and duplicate semantic IDs are rejected. Major artifacts expose
deterministic mappings and SHA-256 content identities using the repository's
stable canonical JSON hashing. Parsers use exact field sets and verify nested
and top-level hashes.

No registry, cache, current-time lookup, random UUID, environment value,
database, network call, or mutable global state participates in a C7 result.

## Verification

Focused tests will prove:

- all closed vocabularies and public exports;
- every lot identity field and source/run binding changes the hash;
- unknown lot fields are explicit and supplier-lot identity is mandatory;
- all nine basis rules, calibration/censoring combinations, and parser
  tamper-rejection behavior;
- incomplete named totals remain incomplete and every unresolved category is
  preserved;
- all six precedence levels, exact matching, fallback disclosure, ambiguity,
  and abstention;
- generic or relative profiles cannot emit regulatory concentration;
- three projection families retain source values/bases and never cross-label;
- authenticity comparison is basis-compatible only;
- aging observations preserve lot identity and form a chronological hash chain;
- the module imports no legacy natural runtime, backend, persistence, database,
  C8 OAV, or sensory code.

Mutation evidence will deliberately remove:

1. normalized-area anti-conversion enforcement;
2. exact-lot matching in precedence selection;
3. unresolved-disclosure enforcement;
4. regulatory projection basis/authority withholding;

Each mutation must be killed and the original bytes restored exactly.

## Exit gate

C7 passes only when the focused, C6-C0 compatibility, complete-root,
dependency, static, mutation, archive, protected-state, log-hygiene, DeepLuna
Fast, Sol-reconciliation, evidence-commit, and exact-commit replay gates pass.
Passing C7 opens C8 software work only. It does not claim that any actual lot
data exist, validate a natural material, authorize a regulatory calculation, or
promote generic profiles.
