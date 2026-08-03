# Build D0 Scientific Claim Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task in the
> authoritative checkout. Codex subagents are forbidden; DeepLuna Fast may be
> used only for bounded mechanical review.

**Goal:** Implement the complete D0 claim-family registry and one immutable,
planning-only Prada control-versus-luxury-orris confirmatory claim, prove the
D0 exit fields, and stop before D1.

**Architecture:** Add a pure `engine/scientific_validation` package with frozen
contracts, a 17-family method-alignment registry, and a factory that accepts
explicit formula/software bindings. Reuse the repository canonical hashing
utility; keep all live file/Git reads in a read-only verifier script. Do not
alter B7, C9, legacy sensory/planner/release modules, formulas, databases, or
migrations.

**Tech Stack:** Python 3.11, frozen dataclasses, `Enum`, `Decimal`, existing
`engine.calibration.hashing`, pytest, Ruff, mypy, PowerShell, Git, and bounded
DeepLuna Fast mechanical audits.

---

## Execution boundary

- Repository: `D:\chatbots\perfume-chem`.
- Start HEAD: `23f71cef875fc74991de9f5c49764109ba2466d1`.
- Branch: `codex/add-inventory-materials`.
- Authoritative pre-D dirty-state digest:
  `4487309377de170c3dc1edf71022f16133806be81f142c305fa894e14efdf532`
  over 1,782 status entries.
- Recovery archive:
  `D:\.backups\perfume-chem\build-d0-prewrite-20260803T115425+0700.tar`,
  SHA-256
  `a94928628805538cf34138de92bb0dda4886f3d1216b934057e9ed4138ee76b2`.
- Root Python:
  `D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe`.
- Run without a PTY, set `NO_COLOR=1` and `TERM=dumb`, use `--color=no`,
  capture stdout/stderr separately for gate runs, and enforce the timeout stated
  in each task.
- Use `git -c safe.directory=D:/chatbots/perfume-chem` for every Git command.
- Stage and commit only the exact paths named by the current task.
- Do not read `.project-secret`, environment values, credentials, runtime
  homes, or hidden provider logs.
- D1 and all later phases remain closed until the D0 evidence commit passes.

## File map

**Create:**

- `engine/scientific_validation/contracts.py` — immutable D0 values, claims,
  validation, canonical payload/hash.
- `engine/scientific_validation/claim_registry.py` — 17-family policy table and
  method-alignment checks.
- `engine/scientific_validation/first_claim.py` — pure Prada first-claim
  factory.
- `engine/scientific_validation/__init__.py` — supported public API only.
- `scripts/verify_d0_claim_matrix.py` — live read-only formula/Git receipt and
  JSON gate output.
- `tests/test_d0_claim_matrix.py` — contract, registry, first-claim, and
  verifier tests.
- `docs/verification/d0/claim_matrix_gate.json` — machine-readable D0 gate.
- `docs/verification/d0/claim_matrix_gate.md` — human-readable D0 handoff.

**Must remain byte-identical:**

- `backend/app/models/lab_claims.py` and all B7 services/migrations;
- `engine/evidence/unsupported_science.py`;
- `engine/sensory/ledger.py`;
- `engine/experiments/planner.py`;
- `engine/release_readiness.py`;
- both Prada formula documents;
- all databases and migration files.

## Task 1: Define immutable contracts with RED tests

**Files:**

- Create: `tests/test_d0_claim_matrix.py`
- Create: `engine/scientific_validation/contracts.py`
- Create: `engine/scientific_validation/__init__.py`

- [ ] **Step 1: Write the failing enum, binding, and immutability tests**

Start `tests/test_d0_claim_matrix.py` with imports and tests equivalent to:

```python
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from engine.scientific_validation.contracts import (
    AssessorType,
    BindingAuthorityState,
    BindingState,
    ClaimAuthorityState,
    ClaimDefinition,
    ClaimFamily,
    ClaimScope,
    ComparatorDefinition,
    CriterionKind,
    DecisionCriterion,
    EndpointDefinition,
    EndpointRole,
    EvidenceRequirement,
    MarginAuthority,
    ScopeValue,
    ValidationMethodFamily,
    VersionBinding,
)


def formula_binding(identifier: str, digest: str = "a" * 64) -> VersionBinding:
    return VersionBinding(
        kind="formula",
        identifier=identifier,
        version="overlay-sha256",
        sha256=digest,
        authority_state=BindingAuthorityState.QUARANTINED,
    )


def software_binding(digest: str = "b" * 64) -> VersionBinding:
    return VersionBinding(
        kind="software",
        identifier="perfume-chem",
        version="23f71cef875fc74991de9f5c49764109ba2466d1",
        sha256=digest,
        authority_state=BindingAuthorityState.REFERENCE_ONLY,
    )


def test_scope_value_requires_exactly_one_bound_value_or_unbound_reason() -> None:
    assert ScopeValue.bound("standardized blotter").state is BindingState.BOUND
    assert ScopeValue.required_unbound("lot not created").value is None
    with pytest.raises(ValueError, match="bound scope value"):
        ScopeValue(state=BindingState.BOUND, value=None, reason=None)
    with pytest.raises(ValueError, match="unbound scope value"):
        ScopeValue(
            state=BindingState.REQUIRED_UNBOUND,
            value="fabricated",
            reason="not allowed",
        )


def test_version_binding_rejects_malformed_hash_and_empty_identity() -> None:
    with pytest.raises(ValueError, match="identifier"):
        formula_binding("")
    with pytest.raises(ValueError, match="sha256"):
        formula_binding("control", "not-a-hash")


def test_contracts_are_frozen() -> None:
    binding = formula_binding("control")
    with pytest.raises(FrozenInstanceError):
        binding.identifier = "changed"  # type: ignore[misc]


def minimum_effect() -> DecisionCriterion:
    return DecisionCriterion(
        criterion_id="minimum-effect",
        kind=CriterionKind.MINIMUM_EFFECT,
        lower_margin=Decimal("0.50"),
        upper_margin=None,
        unit="scale points",
        margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
        success_rule="lower confidence bound meets the margin",
        failure_rule="upper confidence bound is nonpositive",
        inconclusive_rule="all other interval positions are inconclusive",
    )


def primary_endpoint() -> EndpointDefinition:
    return EndpointDefinition(
        endpoint_id="primary-iris",
        claim_family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        role=EndpointRole.PRIMARY,
        attribute="iris/orris intensity",
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes",
        scale="anchored 0-to-10",
        estimand="paired mean difference",
        criterion=minimum_effect(),
    )


def valid_claim() -> ClaimDefinition:
    control = formula_binding("control", "1" * 64)
    intervention = formula_binding("intervention", "2" * 64)
    return ClaimDefinition(
        claim_id="D0-TEST-001",
        version=1,
        title="test planning claim",
        family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        claimant_versions=(intervention, software_binding()),
        assessor_type=AssessorType.TRAINED_DESCRIPTIVE_PANEL,
        scope=ClaimScope(
            population=ScopeValue.bound("trained panel"),
            product=ScopeValue.bound("research product"),
            formula=ScopeValue.required_unbound("formula must be locked"),
            lot=ScopeValue.required_unbound("lot must be created"),
            matrix=ScopeValue.required_unbound("matrix must be locked"),
            substrate=ScopeValue.bound("blotter"),
            condition=ScopeValue.required_unbound("condition must be locked"),
        ),
        primary_endpoint=primary_endpoint(),
        secondary_endpoints=(),
        comparator=ComparatorDefinition(
            comparator_id="control",
            description="locked control",
            binding=control,
        ),
        required_evidence=(EvidenceRequirement("evidence", "real evidence"),),
        authority_state=ClaimAuthorityState.PLANNING_ONLY,
        expiration_triggers=("formula hash changes",),
    )


def test_decision_criterion_rejects_invalid_margin_geometry() -> None:
    with pytest.raises(ValueError, match="minimum-effect"):
        replace(minimum_effect(), upper_margin=Decimal("0.75"))
    with pytest.raises(ValueError, match="equivalence"):
        DecisionCriterion(
            criterion_id="bad-equivalence",
            kind=CriterionKind.EQUIVALENCE,
            lower_margin=Decimal("0"),
            upper_margin=Decimal("0.75"),
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule="inside",
            failure_rule="outside",
            inconclusive_rule="overlap",
        )


def test_claim_rejects_invalid_version_duplicate_evidence_and_primary_shape() -> None:
    claim = valid_claim()
    with pytest.raises(ValueError, match="version"):
        replace(claim, version=0)
    with pytest.raises(ValueError, match="evidence"):
        replace(claim, required_evidence=claim.required_evidence * 2)
    with pytest.raises(ValueError, match="primary endpoint"):
        replace(
            claim,
            primary_endpoint=replace(
                claim.primary_endpoint,
                role=EndpointRole.SECONDARY_SUPPORTIVE,
            ),
        )


def test_claim_hash_is_stable_and_fixed_authority_fields_are_false() -> None:
    first = valid_claim()
    second = valid_claim()
    assert first.content_sha256 == second.content_sha256
    assert len(first.content_sha256) == 64
    assert first.study_authorized is False
    assert first.release_authority is False
    assert first.observed_outcome == "unmeasured"
```

- [ ] **Step 2: Run the RED tests**

Run with a 120-second timeout:

```powershell
$env:NO_COLOR='1'
$env:TERM='dumb'
& 'D:\chatbots\perfume-chem\.venv_py311_a0\Scripts\python.exe' `
  -B -m pytest -q -p no:cacheprovider --color=no `
  tests/test_d0_claim_matrix.py
```

Expected: collection fails because `engine.scientific_validation` does not yet
exist. Record the exact error; do not weaken the import.

- [ ] **Step 3: Implement the contract enums and validators**

Create `contracts.py` with frozen, slotted dataclasses. The exact enum values
are:

```python
class ClaimFamily(str, Enum):
    EXACT_BOTTLE_ARITHMETIC = "exact_bottle_arithmetic"
    EVENT_REPLAY = "event_replay"
    ANALYTICAL_IDENTITY = "analytical_identity"
    ANALYTICAL_QUANTITY = "analytical_quantity"
    EQUILIBRIUM_HEADSPACE_PREDICTION = "equilibrium_headspace_prediction"
    PHYSICAL_RELEASE_TRAJECTORY = "physical_release_trajectory"
    ABOVE_THRESHOLD_SCREENING = "above_threshold_screening"
    PERCEPTIBLE_DIFFERENCE = "perceptible_difference"
    SENSORY_SIMILARITY_EQUIVALENCE = "sensory_similarity_equivalence"
    DESCRIPTIVE_PROFILE_ACCURACY = "descriptive_profile_accuracy"
    TEMPORAL_PROFILE_ACCURACY = "temporal_profile_accuracy"
    RECONSTRUCTION_SIMILARITY = "reconstruction_similarity"
    INTERVENTION_EFFECTIVENESS = "intervention_effectiveness"
    PROTECTED_ATTRIBUTE_PRESERVATION = "protected_attribute_preservation"
    PREFERENCE_LIKING_PREDICTION = "preference_liking_prediction"
    LONGEVITY_PROJECTION_PROXY = "longevity_projection_proxy"
    REGULATORY_SCREENING = "regulatory_screening"


class ValidationMethodFamily(str, Enum):
    DETERMINISTIC_ARITHMETIC = "deterministic_arithmetic"
    EVENT_STREAM_REPLAY = "event_stream_replay"
    ANALYTICAL_IDENTITY = "analytical_identity"
    ANALYTICAL_QUANTITATION = "analytical_quantitation"
    HELD_OUT_HEADSPACE_BENCHMARK = "held_out_headspace_benchmark"
    HELD_OUT_PHYSICAL_RELEASE_BENCHMARK = "held_out_physical_release_benchmark"
    CONTEXTUAL_THRESHOLD_SCREENING = "contextual_threshold_screening"
    SENSORY_DISCRIMINATION = "sensory_discrimination"
    DIRECTIONAL_PAIRED_COMPARISON = "directional_paired_comparison"
    TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE = (
        "trained_quantitative_descriptive_profile"
    )
    REPEATED_TEMPORAL_INTENSITY_PROFILE = "repeated_temporal_intensity_profile"
    SENSOMICS_RECOMBINATION = "sensomics_recombination"
    CONTROLLED_CONSUMER_HEDONIC = "controlled_consumer_hedonic"
    REGULATORY_EVIDENCE_REVIEW = "regulatory_evidence_review"


class ClaimAuthorityState(str, Enum):
    PLANNING_ONLY = "planning_only"
    PREREGISTERED = "preregistered"
    DATA_LOCKED = "data_locked"
    SUPPORTED_EXACT_SCOPE = "supported_exact_scope"
    FAILED_EXACT_SCOPE = "failed_exact_scope"
    INCONCLUSIVE_EXACT_SCOPE = "inconclusive_exact_scope"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class AssessorType(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    TRAINED_DESCRIPTIVE_PANEL = "trained_descriptive_panel"
    DISCRIMINATION_ASSESSOR = "discrimination_assessor"
    CONSUMER = "consumer"
    GC_OLFACTOMETRY_ASSESSOR = "gc_olfactometry_assessor"


class BindingState(str, Enum):
    BOUND = "bound"
    REQUIRED_UNBOUND = "required_unbound"


class BindingAuthorityState(str, Enum):
    QUARANTINED = "quarantined"
    REFERENCE_ONLY = "reference_only"
    LOCK_CANDIDATE = "lock_candidate"
    VALIDATED_EXACT_SCOPE = "validated_exact_scope"


class MarginAuthority(str, Enum):
    PROVISIONAL_PREPILOT = "provisional_prepilot"
    PREREGISTERED_LOCKED = "preregistered_locked"


class EndpointRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY_PROTECTED = "secondary_protected"
    SECONDARY_SUPPORTIVE = "secondary_supportive"


class CriterionKind(str, Enum):
    MINIMUM_EFFECT = "minimum_effect"
    EQUIVALENCE = "equivalence"
```

Implement these exact immutable records:

Import `asdict`, `dataclass`, and `field` from `dataclasses`, and `cast` from
`typing`; `ClaimDefinition.as_dict()` uses those imports exactly as shown.

```python
@dataclass(frozen=True, slots=True)
class VersionBinding:
    kind: str
    identifier: str
    version: str
    sha256: str
    authority_state: BindingAuthorityState


@dataclass(frozen=True, slots=True)
class ScopeValue:
    state: BindingState
    value: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if self.state is BindingState.BOUND:
            if not isinstance(self.value, str) or not self.value.strip():
                raise ValueError("bound scope value must be non-empty")
            if self.reason is not None:
                raise ValueError("bound scope value cannot carry an unbound reason")
            return
        if self.value is not None:
            raise ValueError("unbound scope value cannot carry a value")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("unbound scope value requires a reason")

    @classmethod
    def bound(cls, value: str) -> "ScopeValue":
        return cls(state=BindingState.BOUND, value=value, reason=None)

    @classmethod
    def required_unbound(cls, reason: str) -> "ScopeValue":
        return cls(
            state=BindingState.REQUIRED_UNBOUND,
            value=None,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class ClaimScope:
    population: ScopeValue
    product: ScopeValue
    formula: ScopeValue
    lot: ScopeValue
    matrix: ScopeValue
    substrate: ScopeValue
    condition: ScopeValue


@dataclass(frozen=True, slots=True)
class DecisionCriterion:
    criterion_id: str
    kind: CriterionKind
    lower_margin: Decimal
    upper_margin: Decimal | None
    unit: str
    margin_authority: MarginAuthority
    success_rule: str
    failure_rule: str
    inconclusive_rule: str


@dataclass(frozen=True, slots=True)
class EndpointDefinition:
    endpoint_id: str
    claim_family: ClaimFamily
    role: EndpointRole
    attribute: str
    method_family: ValidationMethodFamily
    timepoint: str
    scale: str
    estimand: str
    criterion: DecisionCriterion


@dataclass(frozen=True, slots=True)
class ComparatorDefinition:
    comparator_id: str
    description: str
    binding: VersionBinding


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    evidence_id: str
    description: str


@dataclass(frozen=True, slots=True)
class ClaimDefinition:
    claim_id: str
    version: int
    title: str
    family: ClaimFamily
    claimant_versions: tuple[VersionBinding, ...]
    assessor_type: AssessorType
    scope: ClaimScope
    primary_endpoint: EndpointDefinition
    secondary_endpoints: tuple[EndpointDefinition, ...]
    comparator: ComparatorDefinition
    required_evidence: tuple[EvidenceRequirement, ...]
    authority_state: ClaimAuthorityState
    expiration_triggers: tuple[str, ...]
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    observed_outcome: str = field(default="unmeasured", init=False)

    def as_dict(self) -> dict[str, object]:
        return cast(dict[str, object], asdict(self))

    @property
    def content_sha256(self) -> str:
        return stable_json_hash(self.as_dict())
```

Use `engine.calibration.hashing.stable_json_hash`; do not implement another
JSON normalizer. Validate IDs/text/hashes, positive claim version, unique
claimant/endpoint/evidence/trigger IDs, primary role/family agreement, and
criterion geometry. A minimum-effect criterion requires a positive lower
margin and no upper margin. An equivalence criterion requires
`lower_margin < 0 < upper_margin`.

- [ ] **Step 4: Export the supported contract API**

Create `__init__.py` with explicit imports and `__all__`; do not wildcard-import
or expose legacy modules.

- [ ] **Step 5: Run the contract tests GREEN**

Run the Task 1 command. Expected: the initial contract tests pass; registry and
first-claim tests do not exist yet.

- [ ] **Step 6: Run static checks and commit**

Run with 120-second timeouts:

```powershell
& $python -B -m ruff check --no-cache --output-format concise `
  engine/scientific_validation/contracts.py `
  engine/scientific_validation/__init__.py tests/test_d0_claim_matrix.py
& $python -B -m mypy --follow-imports=skip `
  engine/scientific_validation/contracts.py
git -c safe.directory=D:/chatbots/perfume-chem diff --check -- `
  engine/scientific_validation tests/test_d0_claim_matrix.py
```

Stage only the three Task 1 paths and commit:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem commit `
  -m 'feat(d0): add immutable scientific claim contracts'
```

## Task 2: Implement the 17-family method registry

**Files:**

- Modify: `tests/test_d0_claim_matrix.py`
- Create: `engine/scientific_validation/claim_registry.py`
- Modify: `engine/scientific_validation/__init__.py`

- [ ] **Step 1: Add RED registry and category-error tests**

Add the exact expected family tuple and tests:

```python
EXPECTED_CLAIM_FAMILIES = (
    "exact_bottle_arithmetic",
    "event_replay",
    "analytical_identity",
    "analytical_quantity",
    "equilibrium_headspace_prediction",
    "physical_release_trajectory",
    "above_threshold_screening",
    "perceptible_difference",
    "sensory_similarity_equivalence",
    "descriptive_profile_accuracy",
    "temporal_profile_accuracy",
    "reconstruction_similarity",
    "intervention_effectiveness",
    "protected_attribute_preservation",
    "preference_liking_prediction",
    "longevity_projection_proxy",
    "regulatory_screening",
)

EXPECTED_AUTHORITY_METHODS = {
    ClaimFamily.EXACT_BOTTLE_ARITHMETIC: (
        ValidationMethodFamily.DETERMINISTIC_ARITHMETIC,
    ),
    ClaimFamily.EVENT_REPLAY: (ValidationMethodFamily.EVENT_STREAM_REPLAY,),
    ClaimFamily.ANALYTICAL_IDENTITY: (
        ValidationMethodFamily.ANALYTICAL_IDENTITY,
    ),
    ClaimFamily.ANALYTICAL_QUANTITY: (
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.EQUILIBRIUM_HEADSPACE_PREDICTION: (
        ValidationMethodFamily.HELD_OUT_HEADSPACE_BENCHMARK,
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.PHYSICAL_RELEASE_TRAJECTORY: (
        ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
        ValidationMethodFamily.ANALYTICAL_QUANTITATION,
    ),
    ClaimFamily.ABOVE_THRESHOLD_SCREENING: (
        ValidationMethodFamily.CONTEXTUAL_THRESHOLD_SCREENING,
    ),
    ClaimFamily.PERCEPTIBLE_DIFFERENCE: (
        ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ValidationMethodFamily.DIRECTIONAL_PAIRED_COMPARISON,
    ),
    ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.DESCRIPTIVE_PROFILE_ACCURACY: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.TEMPORAL_PROFILE_ACCURACY: (
        ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
    ),
    ClaimFamily.RECONSTRUCTION_SIMILARITY: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ValidationMethodFamily.SENSOMICS_RECOMBINATION,
    ),
    ClaimFamily.INTERVENTION_EFFECTIVENESS: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION: (
        ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
    ),
    ClaimFamily.PREFERENCE_LIKING_PREDICTION: (
        ValidationMethodFamily.CONTROLLED_CONSUMER_HEDONIC,
    ),
    ClaimFamily.LONGEVITY_PROJECTION_PROXY: (
        ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
        ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
    ),
    ClaimFamily.REGULATORY_SCREENING: (
        ValidationMethodFamily.REGULATORY_EVIDENCE_REVIEW,
    ),
}


def test_registry_contains_exactly_17_unique_master_claim_families() -> None:
    assert tuple(family.value for family in ClaimFamily) == EXPECTED_CLAIM_FAMILIES
    assert tuple(policy.family for policy in CLAIM_FAMILY_POLICIES) == tuple(
        ClaimFamily
    )
    assert len({policy.family for policy in CLAIM_FAMILY_POLICIES}) == 17
    assert all(policy.authoritative_methods for policy in CLAIM_FAMILY_POLICIES)
    assert {
        policy.family: policy.authoritative_methods
        for policy in CLAIM_FAMILY_POLICIES
    } == EXPECTED_AUTHORITY_METHODS


@pytest.mark.parametrize(
    ("family", "method"),
    [
        (
            ClaimFamily.EXACT_BOTTLE_ARITHMETIC,
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ),
        (
            ClaimFamily.PREFERENCE_LIKING_PREDICTION,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        (
            ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE,
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
        ),
    ],
)
def test_master_category_errors_fail_closed(
    family: ClaimFamily,
    method: ValidationMethodFamily,
) -> None:
    assert is_authoritative_method(family, method) is False
```

- [ ] **Step 2: Run RED**

Run the focused test command. Expected: import/name failures for the registry
API.

- [ ] **Step 3: Implement the immutable policy table**

Create:

```python
@dataclass(frozen=True, slots=True)
class ClaimFamilyPolicy:
    family: ClaimFamily
    authoritative_methods: tuple[ValidationMethodFamily, ...]
    insufficient_shortcuts: tuple[str, ...]


CLAIM_FAMILY_POLICIES: tuple[ClaimFamilyPolicy, ...] = (
    ClaimFamilyPolicy(
        ClaimFamily.EXACT_BOTTLE_ARITHMETIC,
        (ValidationMethodFamily.DETERMINISTIC_ARITHMETIC,),
        ("sensory testing cannot revalidate exact arithmetic",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.EVENT_REPLAY,
        (ValidationMethodFamily.EVENT_STREAM_REPLAY,),
        ("assessor recollection is not event-stream authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ANALYTICAL_IDENTITY,
        (ValidationMethodFamily.ANALYTICAL_IDENTITY,),
        ("odour description alone does not establish identity",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ANALYTICAL_QUANTITY,
        (ValidationMethodFamily.ANALYTICAL_QUANTITATION,),
        ("liking or intensity ratings do not establish quantity",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.EQUILIBRIUM_HEADSPACE_PREDICTION,
        (
            ValidationMethodFamily.HELD_OUT_HEADSPACE_BENCHMARK,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        ("in-sample model fit is not held-out prediction authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PHYSICAL_RELEASE_TRAJECTORY,
        (
            ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
            ValidationMethodFamily.ANALYTICAL_QUANTITATION,
        ),
        ("equilibrium-only output does not establish release trajectory",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.ABOVE_THRESHOLD_SCREENING,
        (ValidationMethodFamily.CONTEXTUAL_THRESHOLD_SCREENING,),
        ("raw concentration alone is not contextual threshold authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PERCEPTIBLE_DIFFERENCE,
        (
            ValidationMethodFamily.SENSORY_DISCRIMINATION,
            ValidationMethodFamily.DIRECTIONAL_PAIRED_COMPARISON,
        ),
        ("a model score alone does not establish perceptibility",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.SENSORY_SIMILARITY_EQUIVALENCE,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("discrimination non-significance does not establish equivalence",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.DESCRIPTIVE_PROFILE_ACCURACY,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("consumer liking is not descriptive-profile authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.TEMPORAL_PROFILE_ACCURACY,
        (ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,),
        ("one static endpoint does not establish a temporal profile",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.RECONSTRUCTION_SIMILARITY,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
            ValidationMethodFamily.SENSOMICS_RECOMBINATION,
        ),
        ("formula arithmetic does not establish sensory reconstruction",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.INTERVENTION_EFFECTIVENESS,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("an unblinded anecdote does not establish intervention effect",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION,
        (
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE,
        ),
        ("no significant difference does not establish equivalence",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.PREFERENCE_LIKING_PREDICTION,
        (ValidationMethodFamily.CONTROLLED_CONSUMER_HEDONIC,),
        ("analytical quantity or trained-panel intensity cannot prove liking",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.LONGEVITY_PROJECTION_PROXY,
        (
            ValidationMethodFamily.REPEATED_TEMPORAL_INTENSITY_PROFILE,
            ValidationMethodFamily.HELD_OUT_PHYSICAL_RELEASE_BENCHMARK,
        ),
        ("equilibrium headspace alone is not longevity/projection authority",),
    ),
    ClaimFamilyPolicy(
        ClaimFamily.REGULATORY_SCREENING,
        (ValidationMethodFamily.REGULATORY_EVIDENCE_REVIEW,),
        ("sensory or model prediction is not regulatory authority",),
    ),
)


def get_claim_family_policy(family: ClaimFamily) -> ClaimFamilyPolicy:
    for policy in CLAIM_FAMILY_POLICIES:
        if policy.family is family:
            return policy
    raise ValueError(f"unregistered claim family: {family.value}")


def is_authoritative_method(
    family: ClaimFamily,
    method: ValidationMethodFamily,
) -> bool:
    return method in get_claim_family_policy(family).authoritative_methods


def validate_claim_method_alignment(claim: ClaimDefinition) -> None:
    endpoints = (claim.primary_endpoint, *claim.secondary_endpoints)
    for endpoint in endpoints:
        if not is_authoritative_method(endpoint.claim_family, endpoint.method_family):
            raise ValueError(
                f"method {endpoint.method_family.value} cannot authorize "
                f"claim family {endpoint.claim_family.value}"
            )
```

Populate the policies exactly as the design matrix specifies. In particular,
do not include sensory discrimination for descriptive equivalence, analytical
quantitation for liking, or any sensory method for arithmetic.

- [ ] **Step 4: Run GREEN, static checks, and commit**

Run focused pytest, Ruff, mypy over the package, and `git diff --check`.
Expected: all pass. Stage only the Task 2 paths and commit:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem commit `
  -m 'feat(d0): register scientific claim method authority'
```

## Task 3: Build the first planning-only claim

**Files:**

- Modify: `tests/test_d0_claim_matrix.py`
- Create: `engine/scientific_validation/first_claim.py`
- Modify: `engine/scientific_validation/__init__.py`

- [ ] **Step 1: Add RED first-claim tests**

Build synthetic exact bindings and assert:

```python
def test_first_claim_defines_the_complete_d0_exit_gate() -> None:
    claim = build_prada_orris_first_claim(
        control_binding=formula_binding("prada-control", "1" * 64),
        intervention_binding=formula_binding("prada-luxury-orris", "2" * 64),
        software_binding=VersionBinding(
            kind="software",
            identifier="perfume-chem",
            version="23f71cef875fc74991de9f5c49764109ba2466d1",
            sha256="3" * 64,
            authority_state=BindingAuthorityState.REFERENCE_ONLY,
        ),
    )

    assert claim.claim_id == "D0-PRADA-ORRIS-INTERVENTION-001"
    assert claim.version == 1
    assert claim.family is ClaimFamily.INTERVENTION_EFFECTIVENESS
    assert claim.assessor_type is AssessorType.TRAINED_DESCRIPTIVE_PANEL
    assert claim.primary_endpoint.attribute == "iris/orris intensity"
    assert claim.primary_endpoint.timepoint == "30 minutes post-application"
    assert claim.primary_endpoint.criterion.lower_margin == Decimal("0.50")
    assert len(claim.secondary_endpoints) == 3
    assert {
        endpoint.criterion.upper_margin for endpoint in claim.secondary_endpoints
    } == {Decimal("0.75")}
    assert len(claim.required_evidence) == 12
    assert claim.authority_state is ClaimAuthorityState.PLANNING_ONLY
    assert claim.study_authorized is False
    assert claim.release_authority is False
    assert claim.observed_outcome == "unmeasured"
    assert claim.scope.lot.state is BindingState.REQUIRED_UNBOUND
    assert claim.scope.matrix.state is BindingState.REQUIRED_UNBOUND
    validate_claim_method_alignment(claim)


def test_first_claim_rejects_nonquarantined_formula_bindings() -> None:
    control = replace(
        formula_binding("control"),
        authority_state=BindingAuthorityState.VALIDATED_EXACT_SCOPE,
    )
    with pytest.raises(ValueError, match="quarantined planning bindings"):
        build_prada_orris_first_claim(
            control_binding=control,
            intervention_binding=formula_binding("intervention"),
            software_binding=software_binding(),
        )
```

Also assert exact protected attributes, success/failure/inconclusive strings,
evidence IDs, revalidation triggers, unique endpoint IDs, deterministic
`content_sha256`, and frozen mutation failure.

- [ ] **Step 2: Run RED**

Expected: import/name failure for `build_prada_orris_first_claim`.

- [ ] **Step 3: Implement the pure factory**

Create the factory and its closed constants as follows (formatting may be
adjusted by Ruff, but values and wording are contractual):

```python
from decimal import Decimal

from engine.scientific_validation.claim_registry import (
    validate_claim_method_alignment,
)
from engine.scientific_validation.contracts import (
    AssessorType,
    BindingAuthorityState,
    ClaimAuthorityState,
    ClaimDefinition,
    ClaimFamily,
    ClaimScope,
    ComparatorDefinition,
    CriterionKind,
    DecisionCriterion,
    EndpointDefinition,
    EndpointRole,
    EvidenceRequirement,
    MarginAuthority,
    ScopeValue,
    ValidationMethodFamily,
    VersionBinding,
)

FIRST_CLAIM_ID = "D0-PRADA-ORRIS-INTERVENTION-001"

REQUIRED_EVIDENCE = (
    EvidenceRequirement(
        "regenerated-formulas",
        "regenerated and revalidated formula artifacts bound to exact hashes",
    ),
    EvidenceRequirement(
        "stock-identity",
        "exact ingredient and stock-lot identity, basis, carrier, density, and concentration records",
    ),
    EvidenceRequirement(
        "study-safety",
        "actual-dose safety and regulatory screening appropriate to the study",
    ),
    EvidenceRequirement(
        "sample-conditions",
        "locked common matrix, concentration, substrate, dose, maturation, storage, and environment",
    ),
    EvidenceRequirement(
        "panel-authority",
        "consent, ethics, privacy, qualification, and trained-panel performance receipt",
    ),
    EvidenceRequirement(
        "separate-pilot",
        "pilot observations kept separate from confirmatory observations",
    ),
    EvidenceRequirement(
        "margin-power-lock",
        "prespecified margin and power rationale ratified before outcome access",
    ),
    EvidenceRequirement(
        "immutable-study-lock",
        "immutable protocol, sample, prediction, randomization, and analysis locks",
    ),
    EvidenceRequirement(
        "confirmatory-observations",
        "blinded randomized replicated append-only confirmatory observations",
    ),
    EvidenceRequirement(
        "locked-analysis",
        "locked analysis with effect sizes, intervals, deviations, and pass/fail/inconclusive output",
    ),
    EvidenceRequirement(
        "claim-specific-analytical-safety",
        "analytical or safety evidence required by final scoped wording",
    ),
    EvidenceRequirement(
        "human-release-review",
        "authorized human review and scoped release decision",
    ),
)

EXPIRATION_TRIGGERS = (
    "claimant formula, software, model, or canonical serialization hash changes",
    "target, comparator, build, ingredient lot, bottle, matrix, substrate, dose, maturation, storage, or condition changes",
    "assessor population, screening, training, lexicon, performance standard, or panel composition changes",
    "endpoint, attribute, scale, timepoint, margin, decision rule, sample-size rationale, exclusion rule, or analysis changes",
    "randomization, blinding, carryover, or data-lock procedure changes",
    "analytical, safety, regulatory, or adverse-event evidence changes",
    "a major or critical protocol deviation occurs",
    "a contradictory study or evidence-expiration event is recorded",
)


def _protected_endpoint(endpoint_id: str, attribute: str) -> EndpointDefinition:
    return EndpointDefinition(
        endpoint_id=endpoint_id,
        claim_family=ClaimFamily.PROTECTED_ATTRIBUTE_PRESERVATION,
        role=EndpointRole.SECONDARY_PROTECTED,
        attribute=attribute,
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes post-application",
        scale="locked anchored 0-to-10 intensity scale",
        estimand="model-adjusted paired mean difference Luxury Orris - Control",
        criterion=DecisionCriterion(
            criterion_id=f"{endpoint_id}-equivalence",
            kind=CriterionKind.EQUIVALENCE,
            lower_margin=Decimal("-0.75"),
            upper_margin=Decimal("0.75"),
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule=(
                "multiplicity-controlled two-one-sided equivalence interval "
                "lies wholly within [-0.75,+0.75]"
            ),
            failure_rule=(
                "interval lies wholly below -0.75 or wholly above +0.75"
            ),
            inconclusive_rule="all other interval positions are inconclusive",
        ),
    )


def build_prada_orris_first_claim(
    *,
    control_binding: VersionBinding,
    intervention_binding: VersionBinding,
    software_binding: VersionBinding,
) -> ClaimDefinition:
    formula_bindings = (control_binding, intervention_binding)
    if any(binding.kind != "formula" for binding in formula_bindings):
        raise ValueError("first claim requires formula bindings")
    if any(
        binding.authority_state is not BindingAuthorityState.QUARANTINED
        for binding in formula_bindings
    ):
        raise ValueError("first claim requires quarantined planning bindings")
    if control_binding.identifier == intervention_binding.identifier:
        raise ValueError("control and intervention must be distinct")
    if control_binding.sha256 == intervention_binding.sha256:
        raise ValueError("control and intervention hashes must be distinct")
    if software_binding.kind != "software":
        raise ValueError("first claim requires a software binding")

    primary = EndpointDefinition(
        endpoint_id="iris-orris-intensity-30m",
        claim_family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        role=EndpointRole.PRIMARY,
        attribute="iris/orris intensity",
        method_family=(
            ValidationMethodFamily.TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE
        ),
        timepoint="30 minutes post-application",
        scale="locked anchored 0-to-10 intensity scale",
        estimand="model-adjusted paired mean difference Luxury Orris - Control",
        criterion=DecisionCriterion(
            criterion_id="iris-orris-minimum-effect",
            kind=CriterionKind.MINIMUM_EFFECT,
            lower_margin=Decimal("0.50"),
            upper_margin=None,
            unit="scale points",
            margin_authority=MarginAuthority.PROVISIONAL_PREPILOT,
            success_rule="two-sided 95% CI lower bound is at least +0.50",
            failure_rule="two-sided 95% CI upper bound is at most 0.00",
            inconclusive_rule="all other interval positions are inconclusive",
        ),
    )
    claim = ClaimDefinition(
        claim_id=FIRST_CLAIM_ID,
        version=1,
        title="Prada Luxury Orris intervention with protected attributes",
        family=ClaimFamily.INTERVENTION_EFFECTIVENESS,
        claimant_versions=(intervention_binding, software_binding),
        assessor_type=AssessorType.TRAINED_DESCRIPTIVE_PANEL,
        scope=ClaimScope(
            population=ScopeValue.bound(
                "trained quantitative descriptive panel meeting D3 qualification"
            ),
            product=ScopeValue.bound(
                "Prada L'Homme architecture research study"
            ),
            formula=ScopeValue.required_unbound(
                "regenerated exact control and intervention builds must be locked"
            ),
            lot=ScopeValue.required_unbound(
                "exact control, intervention, ingredient, and stock lots do not yet exist"
            ),
            matrix=ScopeValue.required_unbound(
                "one common final concentration and hydroalcoholic matrix must be locked"
            ),
            substrate=ScopeValue.bound("standardized fragrance blotter"),
            condition=ScopeValue.required_unbound(
                "D1 must lock dose, environment, session, and 30-minute presentation condition"
            ),
        ),
        primary_endpoint=primary,
        secondary_endpoints=(
            _protected_endpoint(
                "clean-pressed-shirt-soapy",
                "clean pressed-shirt/soapy character",
            ),
            _protected_endpoint(
                "wood-amber-structure",
                "wood-amber structure",
            ),
            _protected_endpoint("dryness-balance", "dryness/balance"),
        ),
        comparator=ComparatorDefinition(
            comparator_id="prada-architecture-control",
            description="Prada L'Homme Architecture Control planning binding",
            binding=control_binding,
        ),
        required_evidence=REQUIRED_EVIDENCE,
        authority_state=ClaimAuthorityState.PLANNING_ONLY,
        expiration_triggers=EXPIRATION_TRIGGERS,
    )
    validate_claim_method_alignment(claim)
    return claim
```

Require the two formula bindings to be `QUARANTINED`, distinct, and kind
`formula`; require the software binding kind `software`. Construct:

- primary iris/orris endpoint at 30 minutes, method
  `TRAINED_QUANTITATIVE_DESCRIPTIVE_PROFILE`, minimum-effect margin
  `Decimal("0.50")`;
- protected clean pressed-shirt/soapy, wood-amber structure, and
  dryness/balance endpoints, each using equivalence
  `Decimal("-0.75")` to `Decimal("0.75")`;
- the exact 12 evidence requirements from the design;
- bound product/population/substrate and explicit required-unbound formula,
  lot, matrix, and controlled-condition scope;
- all design revalidation triggers;
- planning-only authority and no study/release authority.

Do not read formula files, Git, environment, time, or random state.

- [ ] **Step 4: Run GREEN, static checks, and commit**

Run focused pytest, Ruff, mypy, and `git diff --check`. Stage only Task 3 paths
and commit:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem commit `
  -m 'feat(d0): define first confirmatory claim'
```

## Task 4: Add the authoritative-overlay verifier

**Files:**

- Modify: `tests/test_d0_claim_matrix.py`
- Create: `scripts/verify_d0_claim_matrix.py`

- [ ] **Step 1: Add RED verifier tests**

Import `Path`, define
`REPOSITORY_ROOT = Path(__file__).resolve().parents[1]`, and import
`build_gate_payload` from `scripts.verify_d0_claim_matrix`. Test that pure
`build_gate_payload(repository_root: Path) -> dict[str, object]` function with
the live repository and test the CLI in a subprocess. Assert:

```python
def test_live_d0_gate_binds_quarantined_formula_bytes() -> None:
    payload = build_gate_payload(REPOSITORY_ROOT)
    assert payload["schema"] == "d0-claim-matrix-gate-v1"
    assert payload["status"] == "PASS"
    assert payload["claim_family_count"] == 17
    assert payload["d0_exit_fields_complete"] is True
    assert payload["study_authorized"] is False
    assert payload["release_authority"] is False
    assert payload["scientific_outcome"] == "unmeasured"
    assert payload["formula_bindings"][0]["sha256"] == (
        "151de70b2983a7902a67daf8ddd43e0692bfea4ee5f8c92e553c3174827e1d00"
    )
    assert payload["formula_bindings"][1]["sha256"] == (
        "c05661384d53c27aa7a50b50e14e62cf245ee5aa8d3974e0829a56f873d5eb4d"
    )
    assert all(item["status"] == "QUARANTINED" for item in payload["formula_bindings"])
```

The subprocess test requires return code zero, UTF-8 JSON stdout, and empty
stderr. Do not print formula contents.

- [ ] **Step 2: Run RED**

Expected: the verifier module/file is missing.

- [ ] **Step 3: Implement the read-only verifier**

The script must:

1. resolve and validate the repository root;
2. hash only the two named formula files;
3. inspect only enough text to require the exact `**Status:** QUARANTINED`
   marker, without echoing file content;
4. obtain `git rev-parse HEAD` with a 30-second noninteractive subprocess;
5. derive a SHA-256 software content digest from
   `f"git-commit:{head}".encode("ascii")`;
6. build and method-validate the first claim;
7. emit `json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"`;
8. return nonzero with a redacted error category if a hash, status, registry,
   or claim invariant fails.

The payload records the exact formula paths/hashes, Git commit, claim hash,
17-family count, all six D0 exit-field booleans, current blockers,
`study_authorized=false`, `release_authority=false`, and
`scientific_outcome="unmeasured"`.

- [ ] **Step 4: Run GREEN and verifier CLI**

Run with 120-second timeouts:

```powershell
& $python -B -m pytest -q -p no:cacheprovider --color=no `
  tests/test_d0_claim_matrix.py
& $python -B scripts/verify_d0_claim_matrix.py
```

Expected: tests pass; verifier exits 0 with one JSON object on stdout and empty
stderr.

- [ ] **Step 5: Static-check and commit**

Run Ruff, mypy with `--follow-imports=skip`, and `git diff --check` over D0
paths. Stage only the test and verifier, then commit:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem commit `
  -m 'test(d0): verify authoritative claim bindings'
```

## Task 5: Run the D0 software verification matrix

**Files:**

- Generated outside repository:
  `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\d0-gate-*`

- [ ] **Step 1: Capture focused D0 tests**

Run with a 300-second timeout, external `--basetemp`, and separate UTF-8
stdout/stderr files. Require exit 0 and empty stderr.

- [ ] **Step 2: Re-run the complete C0-C10 focused matrix plus D0**

Run these paths with a 1,200-second timeout:

```text
tests/test_c0_physical_model_inventory.py
tests/test_c1_thermophysical_contracts.py
tests/test_c2_matrix_environment.py
tests/test_c3_model_interface.py
tests/test_c4_equilibrium_models.py
tests/test_c5_calibration_program.py
tests/test_c6_dynamic_release.py
tests/test_c7_natural_lots.py
tests/test_c8_headspace_oav.py
tests/test_c9_unsupported_science.py
tests/test_c10_mixture_design.py
tests/test_c10_selection.py
tests/test_c10_historical.py
tests/test_d0_claim_matrix.py
```

Require zero failures. Compare the C0-C10 portion with the prior 655-pass
overlay boundary; do not hide count changes caused by D0 tests.

- [ ] **Step 3: Run the full root suite diagnostically**

Run `pytest tests` with a 1,200-second timeout and external `--basetemp`.
The prior clean baseline had three inherited C0/C5 failures while the
authoritative overlay passed the focused matrix. Record the exact current
outcome; do not relabel inherited or new failures.

- [ ] **Step 4: Run static, verifier, and preservation gates**

Run:

- Ruff on all D0 Python/test/script files;
- mypy on `engine/scientific_validation` and the verifier with
  `--follow-imports=skip`;
- `scripts/verify_d0_claim_matrix.py` twice and require byte-identical stdout;
- `git diff --check` on all D0 paths;
- a redacted sensitive-pattern scan over D0-authored files;
- exact status digest excluding D0-owned paths, requiring the original 1,782
  preserved entries and digest;
- a protected-path hash comparison for all “must remain byte-identical” paths;
- zero staged paths.

If any new failure appears, invoke `superpowers:systematic-debugging`, identify
the root cause, add a failing test, and fix only the D0-owned cause.

## Task 6: Create the D0 evidence reports

**Files:**

- Create: `docs/verification/d0/claim_matrix_gate.json`
- Create: `docs/verification/d0/claim_matrix_gate.md`

- [ ] **Step 1: Write the machine-readable report from observed evidence**

The JSON schema is `d0-claim-matrix-evidence-v1` and must contain:

- design and plan commit hashes;
- implementation commit hashes;
- master-prompt hash;
- archive path, byte length, hash, and extraction result;
- branch, HEAD, prewrite status count/digest, and postwrite preservation result;
- DeepLuna prewrite/design/final job IDs and exact verdicts;
- exact command, exit code, test count, duration, stdout hash, stderr hash, and
  timeout for each verification run;
- Ruff/mypy/verifier/determinism results;
- claim ID/version/hash, comparator and intervention hashes;
- all six D0 exit-field completeness booleans;
- `claim_family_count=17`;
- provisional margin authority;
- `study_authorized=false`, `release_authority=false`,
  `scientific_outcome="unmeasured"`;
- formula quarantine and unresolved-scope blockers;
- `d1_started=false` and an explicit D0 decision.

Never include environment values, credentials, hidden logs, or secret paths.

- [ ] **Step 2: Write the Markdown report with the same facts**

The Markdown report must state in easy words first that D0 software is either
PASS, FAIL, or INCONCLUSIVE and that no perfume study/result/release was
created. Include a requirement crosswalk, exact evidence table, limitations,
revalidation triggers, and the mandatory stop-before-D1 statement.

- [ ] **Step 3: Validate report parity and commit reports only**

Parse the JSON, compare all duplicated facts in Markdown, run a sensitive
pattern scan and `git diff --check`, then stage only the two reports. Commit:

```powershell
git -c safe.directory=D:/chatbots/perfume-chem commit `
  -m 'docs(d0): record scientific claim matrix gate'
```

## Task 7: Independent DeepLuna Fast audit and Sol acceptance

**Files:**

- Read-only D0 implementation, tests, verifier, and reports.
- Modify reports only if an evidence-grounded correction is required.

- [ ] **Step 1: Run a fresh exact-project CheckDL**

Require `READY`, provider calls enabled, zero unknown reservations, and exact
project `workspace-712a446e211c45e1b9d1`. If not READY, fail closed and perform
only local diagnostics.

- [ ] **Step 2: Submit one bounded Fast-only mechanical audit**

Allow only D0-authored paths plus the B7/C9/C10 boundary slices and the two
formula status/hash receipts. Require one provider call, `FLASH`, `NO_LUNA`,
no writes, complete read citations, and output limited to requirement
crosswalk, test-log consistency, forbidden-surface imports, and report parity.
Forbid architecture, scientific interpretation, margin judgment, study
authorization, ISO compliance, and release decisions.

- [ ] **Step 3: Verify the worker locally**

Recheck every reported finding against exact files and logs. Preserve a
negative, mixed, blocked, or truncated verdict exactly; never substitute a
model or retry a deterministic failure.

- [ ] **Step 4: Run final local postflight**

Run focused D0 tests, the verifier twice, Ruff, mypy, report parity,
protected-path hashes, status preservation, `git diff --check`, and a fresh
CheckDL showing settled accounting and no active/queued D0 job.

- [ ] **Step 5: Correct and seal evidence if needed**

If final evidence facts changed, archive the prior two reports, patch only the
reports, rerun parity/static checks, and commit the report correction by exact
path. Do not amend implementation history to conceal failures.

## Task 8: D0 exit gate and mandatory stop

**Files:**

- No new implementation files.

- [ ] **Step 1: Audit every D0 requirement against authoritative evidence**

Require proof for all 17 families, every claim field, method alignment, first
claim/comparator/endpoint/margins/population/evidence, formula receipts,
authority/revalidation, tests, reports, archive, and preserved overlay.

- [ ] **Step 2: Prove D1 did not start**

Search staged/committed D0 changes and require no protocol lock, migration,
assessor record, sample record, randomization schedule, observation, analysis
result, C9 passing receipt, or release upgrade.

- [ ] **Step 3: Verify final Git boundary**

Require:

- zero staged files;
- only intended D0 paths in D0 commits;
- all pre-existing dirty/untracked paths preserved;
- no secret-bearing files in commits/reports;
- final evidence blobs match their recorded hashes.

- [ ] **Step 4: Stop before D1 and report**

Report the exact D0 software decision, commits, test counts, archive, DeepLuna
verdict, preserved-work result, formula/scientific blockers, and the explicit
fact that D1 has not begun. Do not create D1 artifacts in the same boundary
turn.

## D0 completion rule

D0 is complete only when the executable registry contains exactly 17 claim
families; the first planning claim has every master-prompt exit field; method
category errors fail closed; live formula bindings are exact and quarantined;
focused and cumulative software gates pass without a new regression; reports
are parity-checked; DeepLuna's bounded audit is locally verified; and the final
Git/status boundary preserves all prior work. Scientific improvement,
equivalence, safety, preference, and release remain unmeasured and cannot be
claimed by D0 completion.
