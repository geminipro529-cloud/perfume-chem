"""Exact-scope evidence gate for observed perfume liking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.preference import (
    PairwisePreference,
    PreferenceFitRequest,
    PreferenceFitResult,
    PreferenceFitStatus,
    PreferenceModelFamily,
    fit_preference_model,
)
from engine.preference_davidson import DavidsonFitReceipt
from engine.preference_validation import (
    ClusterBootstrapConfig,
    ClusterBootstrapReceipt,
    HeldoutValidationConfig,
    HeldoutValidationReceipt,
    NextPairConstraints,
    NextPairReceipt,
    OrderCarryoverConfig,
    OrderCarryoverReceipt,
    TransitivityConfig,
    TransitivityReceipt,
    assess_order_and_carryover,
    assess_transitivity,
    cluster_bootstrap,
    select_next_pair,
    validate_heldout,
)

_HEDONIC_AUTHORITY_FALSE = {
    "formula": False,
    "liking": False,
    "physical_execution": False,
    "publication": False,
    "purchase": False,
    "release": False,
    "runtime": False,
    "safety": False,
    "scientific_claim": False,
    "sensory": False,
}


class HedonicScope(str, Enum):
    """Population to which a liking comparison is allowed to apply."""

    OWNER = "OWNER"
    TRAINED_PANEL = "TRAINED_PANEL"
    CONSUMER_POPULATION = "CONSUMER_POPULATION"


class HedonicEvidenceState(str, Enum):
    """Evidence posture for an exact-scope liking result."""

    NOT_TESTED = "NOT_TESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DIAGNOSTIC = "DIAGNOSTIC"
    VALIDATED_EXACT_SCOPE = "VALIDATED_EXACT_SCOPE"
    FAILED_HELDOUT_BASELINE = "FAILED_HELDOUT_BASELINE"
    INVALID_OR_CONFOUNDED = "INVALID_OR_CONFOUNDED"


class EvaluationSubstrate(str, Enum):
    """Physical presentation domain; results never transfer across domains silently."""

    BLOTTER = "BLOTTER"
    SKIN = "SKIN"
    AIR = "AIR"
    APPARATUS = "APPARATUS"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _sha256(value: object, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return normalized


def _unique_text_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{field_name} must be a sequence of text values")
    normalized = tuple(_required_text(value, field_name) for value in values)  # type: ignore[union-attr]
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def _comparison_payload(comparison: PairwisePreference) -> dict[str, Any]:
    return comparison.as_dict()


@dataclass(frozen=True, slots=True)
class PreferenceItemEvidenceBinding:
    """One immutable item-label to build, sample, and preparation lineage map."""

    item_id: str
    build_sha256: str
    sample_sha256: str
    provenance_manifest_sha256: str
    sampling_or_dose_receipt_sha256: str
    batch_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _required_text(self.item_id, "item_id"))
        object.__setattr__(self, "batch_id", _required_text(self.batch_id, "batch_id"))
        for name in (
            "build_sha256",
            "sample_sha256",
            "provenance_manifest_sha256",
            "sampling_or_dose_receipt_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))

    def as_dict(self) -> dict[str, str]:
        return {
            "item_id": self.item_id,
            "build_sha256": self.build_sha256,
            "sample_sha256": self.sample_sha256,
            "provenance_manifest_sha256": self.provenance_manifest_sha256,
            "sampling_or_dose_receipt_sha256": self.sampling_or_dose_receipt_sha256,
            "batch_id": self.batch_id,
        }


@dataclass(frozen=True, slots=True)
class SensoryEvaluationContext:
    """Hash-bound apparatus, application, environment, wear, and carryover scope."""

    context_id: str
    substrate: EvaluationSubstrate
    application_protocol_sha256: str
    environment_sha256: str
    maturation_state_sha256: str
    carryover_control_sha256: str
    carryover_qualified: bool
    apparatus_sha256: str | None = None
    wearer_id: str | None = None
    body_odor_context_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "context_id", _required_text(self.context_id, "context_id")
        )
        object.__setattr__(self, "substrate", EvaluationSubstrate(self.substrate))
        for name in (
            "application_protocol_sha256",
            "environment_sha256",
            "maturation_state_sha256",
            "carryover_control_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in ("apparatus_sha256", "body_odor_context_sha256"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _sha256(value, name))
        wearer = (
            _required_text(self.wearer_id, "wearer_id")
            if self.wearer_id is not None
            else None
        )
        object.__setattr__(self, "wearer_id", wearer)
        if not isinstance(self.carryover_qualified, bool):
            raise TypeError("carryover_qualified must be boolean")
        if self.substrate is EvaluationSubstrate.SKIN:
            if wearer is None:
                raise ValueError("wearer_id is required for SKIN evaluation")
            if self.body_odor_context_sha256 is None:
                raise ValueError(
                    "body_odor_context_sha256 is required for SKIN evaluation"
                )
        elif wearer is not None or self.body_odor_context_sha256 is not None:
            raise ValueError(
                "wearer and body-odor bindings are valid only for SKIN evaluation"
            )
        if (
            self.substrate is EvaluationSubstrate.APPARATUS
            and self.apparatus_sha256 is None
        ):
            raise ValueError("apparatus_sha256 is required for APPARATUS evaluation")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "sensory_evaluation_context_v1",
            "context_id": self.context_id,
            "substrate": self.substrate.value,
            "application_protocol_sha256": self.application_protocol_sha256,
            "environment_sha256": self.environment_sha256,
            "maturation_state_sha256": self.maturation_state_sha256,
            "carryover_control_sha256": self.carryover_control_sha256,
            "carryover_qualified": self.carryover_qualified,
            "apparatus_sha256": self.apparatus_sha256,
            "wearer_id": self.wearer_id,
            "body_odor_context_sha256": self.body_odor_context_sha256,
            "authority": dict(_HEDONIC_AUTHORITY_FALSE),
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


@dataclass(frozen=True, slots=True)
class PreferenceEvidenceAdequacyContract:
    """Predeclared minimum evidence; passing it is necessary, never sufficient."""

    analysis_plan_sha256: str
    sampling_frame_sha256: str
    minimum_assessors: int
    minimum_directional_training_comparisons: int
    minimum_heldout_groups: int
    minimum_heldout_comparisons: int
    minimum_cluster_bootstrap_replicates: int
    minimum_heldout_bootstrap_replicates: int

    def __post_init__(self) -> None:
        for name in ("analysis_plan_sha256", "sampling_frame_sha256"):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        for name in (
            "minimum_assessors",
            "minimum_directional_training_comparisons",
            "minimum_heldout_groups",
            "minimum_heldout_comparisons",
            "minimum_cluster_bootstrap_replicates",
            "minimum_heldout_bootstrap_replicates",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "preference_evidence_adequacy_v1",
            "analysis_plan_sha256": self.analysis_plan_sha256,
            "sampling_frame_sha256": self.sampling_frame_sha256,
            "minimum_assessors": self.minimum_assessors,
            "minimum_directional_training_comparisons": (
                self.minimum_directional_training_comparisons
            ),
            "minimum_heldout_groups": self.minimum_heldout_groups,
            "minimum_heldout_comparisons": self.minimum_heldout_comparisons,
            "minimum_cluster_bootstrap_replicates": (
                self.minimum_cluster_bootstrap_replicates
            ),
            "minimum_heldout_bootstrap_replicates": (
                self.minimum_heldout_bootstrap_replicates
            ),
        }


def _fit_request_payload(request: PreferenceFitRequest) -> dict[str, Any]:
    return {
        "training": [_comparison_payload(value) for value in request.training],
        "heldout": [_comparison_payload(value) for value in request.heldout],
        "minimum_comparisons": request.minimum_comparisons,
        "minimum_heldout_comparisons": request.minimum_heldout_comparisons,
        "declared_baseline_accuracy": request.declared_baseline_accuracy,
        "regularization": request.regularization,
        "learning_rate": request.learning_rate,
        "maximum_iterations": request.maximum_iterations,
        "criterion_id": request.criterion_id,
        "bootstrap_replicates": request.bootstrap_replicates,
        "bootstrap_seed": request.bootstrap_seed,
        "require_scoped_validation": request.require_scoped_validation,
        "model_family": request.model_family.value,
    }


def _fit_result_payload(result: PreferenceFitResult) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "validated": result.validated,
        "utilities": result.utilities,
        "comparison_count": result.comparison_count,
        "connected": result.connected,
        "regularization": result.regularization,
        "heldout_accuracy": result.heldout_accuracy,
        "baseline_accuracy": result.baseline_accuracy,
        "gate_failures": result.gate_failures,
        "validation_notes": result.validation_notes,
        "criterion_id": result.criterion_id,
        "utility_intervals": result.utility_intervals,
        "tie_rate": result.tie_rate,
        "assessor_heterogeneity": result.assessor_heterogeneity,
        "order_effect": result.order_effect,
        "next_comparison": result.next_comparison,
        "bootstrap_replicates": result.bootstrap_replicates,
        "bootstrap_seed": result.bootstrap_seed,
        "bootstrap_method": result.bootstrap_method,
        "model_family": result.model_family.value,
        "tie_parameter": result.tie_parameter,
        "converged": result.converged,
        "convergence_code": result.convergence_code,
        "pair_probabilities": result.pair_probabilities,
        "evidence": result.evidence.as_dict(),
    }


@dataclass(frozen=True, slots=True)
class PreferenceFitEvidenceReceiptV1:
    """Hash-bound fit, observations, repeat map, and exact sensory scope."""

    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    comparison_repeat_ids: tuple[tuple[str, str], ...]
    time_seconds: float
    schedule_sha256: str
    fit_request: PreferenceFitRequest
    fit_result: PreferenceFitResult
    training_comparisons_sha256: str = field(init=False)
    heldout_comparisons_sha256: str = field(init=False)
    fit_request_sha256: str = field(init=False)
    fit_result_sha256: str = field(init=False)
    model_configuration_sha256: str = field(init=False)
    comparison_repeats_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "criterion_id", _required_text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "scope", HedonicScope(self.scope))
        for name in (
            "formula_build_sha256",
            "protocol_sha256",
            "schedule_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        samples = tuple(_sha256(value, "sample_sha256") for value in self.sample_sha256)
        if not samples or len(samples) != len(set(samples)):
            raise ValueError("sample_sha256 must contain unique sample hashes")
        object.__setattr__(self, "sample_sha256", samples)
        object.__setattr__(
            self,
            "assessor_ids",
            _unique_text_tuple(self.assessor_ids, "assessor_ids"),
        )
        object.__setattr__(
            self, "repeat_ids", _unique_text_tuple(self.repeat_ids, "repeat_ids")
        )
        if isinstance(self.time_seconds, bool) or not isinstance(
            self.time_seconds, (int, float)
        ):
            raise TypeError("time_seconds must be a real number")
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")
        object.__setattr__(self, "time_seconds", time_seconds)

        repeats = tuple(
            sorted(
                (
                    _required_text(comparison_id, "comparison_repeat_ids key"),
                    _required_text(repeat_id, "comparison_repeat_ids value"),
                )
                for comparison_id, repeat_id in self.comparison_repeat_ids
            )
        )
        if len(repeats) != len({comparison_id for comparison_id, _ in repeats}):
            raise ValueError("comparison_repeat_ids must have unique comparison IDs")
        object.__setattr__(self, "comparison_repeat_ids", repeats)

        comparisons = self.fit_request.training + self.fit_request.heldout
        comparison_ids = tuple(comparison.comparison_id for comparison in comparisons)
        if any(value is None for value in comparison_ids) or set(comparison_ids) != {
            comparison_id for comparison_id, _ in repeats
        }:
            raise ValueError(
                "comparison_repeat_ids must cover every fit comparison exactly"
            )
        if any(repeat_id not in self.repeat_ids for _, repeat_id in repeats):
            raise ValueError("comparison_repeat_ids contains an undeclared repeat")
        observed_assessors = {
            comparison.assessor_id
            for comparison in comparisons
            if comparison.assessor_id is not None
        }
        if observed_assessors != set(self.assessor_ids):
            raise ValueError("assessor_ids must exactly match fit comparisons")
        if any(
            comparison.criterion_id != self.criterion_id for comparison in comparisons
        ) or self.fit_request.criterion_id != self.criterion_id:
            raise ValueError("criterion_id must exactly match the fit request")
        if any(
            comparison.time_seconds != self.time_seconds for comparison in comparisons
        ):
            raise ValueError("time_seconds must exactly match fit comparisons")

        expected = fit_preference_model(self.fit_request)
        expected_bytes = canonical_json_bytes(_fit_result_payload(expected))
        result_bytes = canonical_json_bytes(_fit_result_payload(self.fit_result))
        if expected_bytes != result_bytes:
            raise ValueError("fit result does not match the bound fit request")

        request_payload = _fit_request_payload(self.fit_request)
        model_payload = {
            key: value
            for key, value in request_payload.items()
            if key not in {"training", "heldout"}
        }
        derived = {
            "training_comparisons_sha256": sha256_hex(
                canonical_json_bytes(request_payload["training"])
            ),
            "heldout_comparisons_sha256": sha256_hex(
                canonical_json_bytes(request_payload["heldout"])
            ),
            "fit_request_sha256": sha256_hex(canonical_json_bytes(request_payload)),
            "fit_result_sha256": sha256_hex(result_bytes),
            "model_configuration_sha256": sha256_hex(
                canonical_json_bytes(model_payload)
            ),
            "comparison_repeats_sha256": sha256_hex(canonical_json_bytes(repeats)),
        }
        for name, value in derived.items():
            object.__setattr__(self, name, value)

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "preference_fit_evidence_v1",
            "criterion_id": self.criterion_id,
            "scope": self.scope.value,
            "formula_build_sha256": self.formula_build_sha256,
            "sample_sha256": self.sample_sha256,
            "protocol_sha256": self.protocol_sha256,
            "assessor_ids": self.assessor_ids,
            "repeat_ids": self.repeat_ids,
            "comparison_repeat_ids": self.comparison_repeat_ids,
            "time_seconds": self.time_seconds,
            "schedule_sha256": self.schedule_sha256,
            "training_comparisons_sha256": self.training_comparisons_sha256,
            "heldout_comparisons_sha256": self.heldout_comparisons_sha256,
            "fit_request_sha256": self.fit_request_sha256,
            "fit_result_sha256": self.fit_result_sha256,
            "model_configuration_sha256": self.model_configuration_sha256,
            "comparison_repeats_sha256": self.comparison_repeats_sha256,
            "fit_request": _fit_request_payload(self.fit_request),
            "fit_result": _fit_result_payload(self.fit_result),
        }


def bind_preference_fit_evidence(
    fit_request: PreferenceFitRequest,
    fit_result: PreferenceFitResult,
    *,
    scope: HedonicScope,
    formula_build_sha256: str,
    sample_sha256: tuple[str, ...],
    protocol_sha256: str,
    assessor_ids: tuple[str, ...],
    repeat_ids: tuple[str, ...],
    comparison_repeat_ids: Mapping[str, str],
    time_seconds: float,
    schedule_sha256: str,
) -> PreferenceFitEvidenceReceiptV1:
    """Bind a deterministic preference fit to its exact sensory evidence scope."""

    return PreferenceFitEvidenceReceiptV1(
        criterion_id=fit_request.criterion_id or "",
        scope=scope,
        formula_build_sha256=formula_build_sha256,
        sample_sha256=sample_sha256,
        protocol_sha256=protocol_sha256,
        assessor_ids=assessor_ids,
        repeat_ids=repeat_ids,
        comparison_repeat_ids=tuple(comparison_repeat_ids.items()),
        time_seconds=time_seconds,
        schedule_sha256=schedule_sha256,
        fit_request=fit_request,
        fit_result=fit_result,
    )


@dataclass(frozen=True, slots=True)
class PreferenceFitEvidenceReceiptV2:
    """Exact-scope V2 liking evidence with proper validation and diagnostics."""

    parent_v1: PreferenceFitEvidenceReceiptV1
    davidson_fit: DavidsonFitReceipt
    cluster_bootstrap: ClusterBootstrapReceipt
    heldout_validation: HeldoutValidationReceipt
    transitivity: TransitivityReceipt
    next_pair: NextPairReceipt
    construct_registry_sha256: str
    criterion_wording_sha256: str
    source_transfer_sha256: str
    source_transfer_state: str
    metadata_missing_codes: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.parent_v1, PreferenceFitEvidenceReceiptV1):
            raise TypeError("parent_v1 must be a PreferenceFitEvidenceReceiptV1")
        if not isinstance(self.davidson_fit, DavidsonFitReceipt):
            raise TypeError("davidson_fit must be a DavidsonFitReceipt")
        if not isinstance(self.cluster_bootstrap, ClusterBootstrapReceipt):
            raise TypeError("cluster_bootstrap must be a ClusterBootstrapReceipt")
        if not isinstance(self.heldout_validation, HeldoutValidationReceipt):
            raise TypeError("heldout_validation must be a HeldoutValidationReceipt")
        if not isinstance(self.transitivity, TransitivityReceipt):
            raise TypeError("transitivity must be a TransitivityReceipt")
        if not isinstance(self.next_pair, NextPairReceipt):
            raise TypeError("next_pair must be a NextPairReceipt")
        for name in (
            "construct_registry_sha256",
            "criterion_wording_sha256",
            "source_transfer_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        transfer = _required_text(
            self.source_transfer_state, "source_transfer_state"
        ).upper()
        if transfer not in {
            "DIRECT",
            "NARROWER_SCOPE",
            "HYPOTHESIS_ONLY",
            "FAILED",
        }:
            raise ValueError("source_transfer_state is invalid")
        object.__setattr__(self, "source_transfer_state", transfer)
        parent_fit = self.parent_v1.fit_result
        if parent_fit.model_family is not PreferenceModelFamily.DAVIDSON_V1:
            raise ValueError("V2 evidence requires DAVIDSON_V1")
        if set(parent_fit.utilities) != set(self.davidson_fit.utilities) or any(
            abs(parent_fit.utilities[item] - self.davidson_fit.utilities[item]) > 1e-9
            for item in parent_fit.utilities
        ):
            raise ValueError("Davidson receipt does not match the bound fit result")
        if (
            parent_fit.tie_parameter is None
            or abs(parent_fit.tie_parameter - self.davidson_fit.tie_parameter) > 1e-9
        ):
            raise ValueError("Davidson tie parameter does not match the bound fit result")
        if set(self.cluster_bootstrap.utility_intervals) != set(parent_fit.utilities):
            raise ValueError("cluster intervals do not cover the fitted item set")
        missing: set[str] = set()
        comparisons = self.parent_v1.fit_request.training + self.parent_v1.fit_request.heldout
        required = (
            "comparison_id",
            "assessor_id",
            "protocol_id",
            "criterion_id",
            "time_seconds",
            "first_presented_item",
            "session_id",
            "matrix_id",
            "time_window_id",
            "position_in_session",
            "protocol_sha256",
            "sample_sha256",
            "partition",
        )
        for name in required:
            if any(getattr(row, name) is None for row in comparisons):
                missing.add(name.upper())
        if any(
            row.protocol_sha256 is not None
            and row.protocol_sha256 != self.parent_v1.protocol_sha256
            for row in comparisons
        ):
            missing.add("PROTOCOL_SHA256_MISMATCH")
        if any(
            row.sample_sha256 is not None
            and row.sample_sha256 not in self.parent_v1.sample_sha256
            for row in comparisons
        ):
            missing.add("SAMPLE_SHA256_MISMATCH")
        if any(
            row.position_in_session is not None
            and row.position_in_session > 1
            and row.previous_presented_item is None
            for row in comparisons
        ):
            missing.add("PREVIOUS_PRESENTED_ITEM")
        object.__setattr__(self, "metadata_missing_codes", tuple(sorted(missing)))

    @property
    def criterion_id(self) -> str:
        return self.parent_v1.criterion_id

    @property
    def scope(self) -> HedonicScope:
        return self.parent_v1.scope

    @property
    def formula_build_sha256(self) -> str:
        return self.parent_v1.formula_build_sha256

    @property
    def sample_sha256(self) -> tuple[str, ...]:
        return self.parent_v1.sample_sha256

    @property
    def protocol_sha256(self) -> str:
        return self.parent_v1.protocol_sha256

    @property
    def assessor_ids(self) -> tuple[str, ...]:
        return self.parent_v1.assessor_ids

    @property
    def repeat_ids(self) -> tuple[str, ...]:
        return self.parent_v1.repeat_ids

    @property
    def time_seconds(self) -> float:
        return self.parent_v1.time_seconds

    @property
    def schedule_sha256(self) -> str:
        return self.parent_v1.schedule_sha256

    @property
    def fit_request(self) -> PreferenceFitRequest:
        return self.parent_v1.fit_request

    @property
    def fit_result(self) -> PreferenceFitResult:
        return self.parent_v1.fit_result

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_HEDONIC_AUTHORITY_FALSE)

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "preference_fit_evidence_v2",
            "parent_v1_sha256": self.parent_v1.record_sha256,
            "davidson_fit": self.davidson_fit.as_dict(),
            "cluster_bootstrap": self.cluster_bootstrap.as_dict(),
            "heldout_validation": self.heldout_validation.as_dict(),
            "transitivity": self.transitivity.as_dict(),
            "next_pair": self.next_pair.as_dict(),
            "construct_registry_sha256": self.construct_registry_sha256,
            "criterion_wording_sha256": self.criterion_wording_sha256,
            "source_transfer_sha256": self.source_transfer_sha256,
            "source_transfer_state": self.source_transfer_state,
            "metadata_missing_codes": list(self.metadata_missing_codes),
            "authority": self.authority,
        }


def bind_preference_fit_evidence_v2(
    parent_v1: PreferenceFitEvidenceReceiptV1,
    *,
    davidson_fit: DavidsonFitReceipt,
    construct_registry_sha256: str,
    criterion_wording_sha256: str,
    source_transfer_sha256: str,
    source_transfer_state: str,
    bootstrap_config: ClusterBootstrapConfig,
    heldout_config: HeldoutValidationConfig,
    transitivity_config: TransitivityConfig,
    eligible_next_pairs: tuple[tuple[str, str], ...],
    next_pair_constraints: NextPairConstraints,
) -> PreferenceFitEvidenceReceiptV2:
    """Build all V2 receipts from one frozen V1 parent and Davidson fit."""

    training = parent_v1.fit_request.training
    heldout = parent_v1.fit_request.heldout
    bootstrap = cluster_bootstrap(training, config=bootstrap_config)
    validation = validate_heldout(
        fitted=davidson_fit,
        training=training,
        heldout=heldout,
        config=heldout_config,
    )
    transitivity = assess_transitivity(
        training + heldout,
        config=transitivity_config,
    )
    next_pair = select_next_pair(
        fitted=davidson_fit,
        eligible_pairs=eligible_next_pairs,
        constraints=next_pair_constraints,
    )
    return PreferenceFitEvidenceReceiptV2(
        parent_v1=parent_v1,
        davidson_fit=davidson_fit,
        cluster_bootstrap=bootstrap,
        heldout_validation=validation,
        transitivity=transitivity,
        next_pair=next_pair,
        construct_registry_sha256=construct_registry_sha256,
        criterion_wording_sha256=criterion_wording_sha256,
        source_transfer_sha256=source_transfer_sha256,
        source_transfer_state=source_transfer_state,
    )


@dataclass(frozen=True, slots=True)
class PreferenceFitEvidenceReceiptV3:
    """Promotion-capable evidence with exact item, sample, and context lineage."""

    parent_v2: PreferenceFitEvidenceReceiptV2
    focal_item_id: str
    item_bindings: tuple[PreferenceItemEvidenceBinding, ...]
    evaluation_context: SensoryEvaluationContext
    adequacy_contract: PreferenceEvidenceAdequacyContract
    order_carryover: OrderCarryoverReceipt
    item_bindings_sha256: str = field(init=False)
    adequacy_failure_codes: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.parent_v2, PreferenceFitEvidenceReceiptV2):
            raise TypeError("parent_v2 must be a PreferenceFitEvidenceReceiptV2")
        if not isinstance(self.evaluation_context, SensoryEvaluationContext):
            raise TypeError(
                "evaluation_context must be a SensoryEvaluationContext"
            )
        if not isinstance(
            self.adequacy_contract, PreferenceEvidenceAdequacyContract
        ):
            raise TypeError(
                "adequacy_contract must be a PreferenceEvidenceAdequacyContract"
            )
        if not isinstance(self.order_carryover, OrderCarryoverReceipt):
            raise TypeError("order_carryover must be an OrderCarryoverReceipt")
        focal = _required_text(self.focal_item_id, "focal_item_id")
        object.__setattr__(self, "focal_item_id", focal)
        bindings = tuple(sorted(self.item_bindings, key=lambda value: value.item_id))
        if not bindings or any(
            not isinstance(value, PreferenceItemEvidenceBinding) for value in bindings
        ):
            raise TypeError(
                "item_bindings must contain PreferenceItemEvidenceBinding values"
            )
        ids = tuple(value.item_id for value in bindings)
        if len(ids) != len(set(ids)):
            raise ValueError("item_bindings must contain unique item IDs")
        rows = self.fit_request.training + self.fit_request.heldout
        compared_items = {
            item for row in rows for item in (row.left_item, row.right_item)
        }
        if set(ids) != compared_items:
            raise ValueError("item_bindings must exactly cover compared items")
        if focal not in compared_items:
            raise ValueError("focal_item_id must be one of the compared items")
        binding_samples = tuple(value.sample_sha256 for value in bindings)
        if len(binding_samples) != len(set(binding_samples)):
            raise ValueError(
                "item_bindings must map each compared item to a distinct sample"
            )
        if set(binding_samples) != set(self.parent_v2.sample_sha256):
            raise ValueError(
                "item binding samples must exactly match the parent sample set"
            )
        by_item = {value.item_id: value for value in bindings}
        if by_item[focal].build_sha256 != self.parent_v2.formula_build_sha256:
            raise ValueError(
                "focal item build hash must match the parent formula build hash"
            )
        context_sha256 = self.evaluation_context.record_sha256
        for row in rows:
            if row.left_sample_sha256 != by_item[row.left_item].sample_sha256:
                raise ValueError(
                    f"left sample hash does not match item binding: {row.comparison_id}"
                )
            if row.right_sample_sha256 != by_item[row.right_item].sample_sha256:
                raise ValueError(
                    f"right sample hash does not match item binding: {row.comparison_id}"
                )
            if row.sample_sha256 not in {
                row.left_sample_sha256,
                row.right_sample_sha256,
            }:
                raise ValueError(
                    "legacy sample hash must identify the left or right sample: "
                    f"{row.comparison_id}"
                )
            if row.evaluation_context_sha256 != context_sha256:
                raise ValueError(
                    "evaluation context hash does not match every comparison"
                )
            if row.previous_presented_item is not None:
                previous = by_item.get(row.previous_presented_item)
                if previous is None:
                    raise ValueError(
                        "previous presented item is absent from item bindings"
                    )
                if (
                    row.previous_presented_sample_sha256
                    != previous.sample_sha256
                ):
                    raise ValueError(
                        "previous presented sample hash does not match item binding"
                    )
        object.__setattr__(self, "item_bindings", bindings)
        object.__setattr__(
            self,
            "item_bindings_sha256",
            sha256_hex(
                canonical_json_bytes([value.as_dict() for value in bindings])
            ),
        )
        contract = self.adequacy_contract
        validation = self.parent_v2.heldout_validation
        failures: list[str] = []
        if len(self.assessor_ids) < contract.minimum_assessors:
            failures.append("ASSESSOR_COUNT_INSUFFICIENT")
        if (
            self.fit_result.comparison_count
            < contract.minimum_directional_training_comparisons
        ):
            failures.append("DIRECTIONAL_TRAINING_COMPARISONS_INSUFFICIENT")
        if validation.heldout_group_count < contract.minimum_heldout_groups:
            failures.append("HELDOUT_GROUP_COUNT_INSUFFICIENT")
        if validation.heldout_count < contract.minimum_heldout_comparisons:
            failures.append("HELDOUT_COMPARISONS_INSUFFICIENT")
        if (
            self.parent_v2.cluster_bootstrap.completed_replicates
            < contract.minimum_cluster_bootstrap_replicates
        ):
            failures.append("CLUSTER_BOOTSTRAP_REPLICATES_INSUFFICIENT")
        if (
            validation.bootstrap_replicates
            < contract.minimum_heldout_bootstrap_replicates
        ):
            failures.append("HELDOUT_BOOTSTRAP_REPLICATES_INSUFFICIENT")
        object.__setattr__(
            self, "adequacy_failure_codes", tuple(sorted(failures))
        )

    @property
    def criterion_id(self) -> str:
        return self.parent_v2.criterion_id

    @property
    def scope(self) -> HedonicScope:
        return self.parent_v2.scope

    @property
    def formula_build_sha256(self) -> str:
        return self.parent_v2.formula_build_sha256

    @property
    def sample_sha256(self) -> tuple[str, ...]:
        return self.parent_v2.sample_sha256

    @property
    def protocol_sha256(self) -> str:
        return self.parent_v2.protocol_sha256

    @property
    def assessor_ids(self) -> tuple[str, ...]:
        return self.parent_v2.assessor_ids

    @property
    def repeat_ids(self) -> tuple[str, ...]:
        return self.parent_v2.repeat_ids

    @property
    def time_seconds(self) -> float:
        return self.parent_v2.time_seconds

    @property
    def schedule_sha256(self) -> str:
        return self.parent_v2.schedule_sha256

    @property
    def fit_request(self) -> PreferenceFitRequest:
        return self.parent_v2.fit_request

    @property
    def fit_result(self) -> PreferenceFitResult:
        return self.parent_v2.fit_result

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_HEDONIC_AUTHORITY_FALSE)

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "preference_fit_evidence_v3",
            "parent_v2_sha256": self.parent_v2.record_sha256,
            "focal_item_id": self.focal_item_id,
            "item_bindings": [value.as_dict() for value in self.item_bindings],
            "item_bindings_sha256": self.item_bindings_sha256,
            "evaluation_context": self.evaluation_context.as_dict(),
            "evaluation_context_sha256": self.evaluation_context.record_sha256,
            "adequacy_contract": self.adequacy_contract.as_dict(),
            "adequacy_failure_codes": list(self.adequacy_failure_codes),
            "order_carryover": self.order_carryover.as_dict(),
            "authority": self.authority,
        }


def bind_preference_fit_evidence_v3(
    parent_v2: PreferenceFitEvidenceReceiptV2,
    *,
    focal_item_id: str,
    item_bindings: tuple[PreferenceItemEvidenceBinding, ...],
    evaluation_context: SensoryEvaluationContext,
    adequacy_contract: PreferenceEvidenceAdequacyContract,
    order_carryover_config: OrderCarryoverConfig,
) -> PreferenceFitEvidenceReceiptV3:
    """Bind promotion evidence without inferring liking from formulation features."""

    order_carryover = assess_order_and_carryover(
        parent_v2.fit_request.training + parent_v2.fit_request.heldout,
        config=order_carryover_config,
        carryover_qualified=evaluation_context.carryover_qualified,
    )
    return PreferenceFitEvidenceReceiptV3(
        parent_v2=parent_v2,
        focal_item_id=focal_item_id,
        item_bindings=item_bindings,
        evaluation_context=evaluation_context,
        adequacy_contract=adequacy_contract,
        order_carryover=order_carryover,
    )


@dataclass(frozen=True, slots=True)
class HedonicEvidenceRequest:
    """Exact scope against which one liking fit may be evaluated."""

    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    sample_sha256: tuple[str, ...]
    protocol_sha256: str
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    time_seconds: float
    schedule_sha256: str
    fit_receipt: (
        PreferenceFitEvidenceReceiptV1
        | PreferenceFitEvidenceReceiptV2
        | PreferenceFitEvidenceReceiptV3
        | None
    ) = None
    safety_event_ids: tuple[str, ...] = ()
    maximum_absolute_order_effect: float = 0.25
    focal_item_id: str | None = None
    evaluation_context_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "criterion_id", _required_text(self.criterion_id, "criterion_id")
        )
        object.__setattr__(self, "scope", HedonicScope(self.scope))
        for name in (
            "formula_build_sha256",
            "protocol_sha256",
            "schedule_sha256",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        samples = tuple(_sha256(value, "sample_sha256") for value in self.sample_sha256)
        if not samples or len(samples) != len(set(samples)):
            raise ValueError("sample_sha256 must contain unique sample hashes")
        object.__setattr__(self, "sample_sha256", samples)
        object.__setattr__(
            self,
            "assessor_ids",
            _unique_text_tuple(self.assessor_ids, "assessor_ids"),
        )
        object.__setattr__(
            self, "repeat_ids", _unique_text_tuple(self.repeat_ids, "repeat_ids")
        )
        object.__setattr__(
            self,
            "safety_event_ids",
            tuple(
                _required_text(value, "safety_event_ids")
                for value in self.safety_event_ids
            ),
        )
        if self.focal_item_id is not None:
            object.__setattr__(
                self,
                "focal_item_id",
                _required_text(self.focal_item_id, "focal_item_id"),
            )
        if self.evaluation_context_sha256 is not None:
            object.__setattr__(
                self,
                "evaluation_context_sha256",
                _sha256(
                    self.evaluation_context_sha256,
                    "evaluation_context_sha256",
                ),
            )
        if isinstance(self.time_seconds, bool) or not isinstance(
            self.time_seconds, (int, float)
        ):
            raise TypeError("time_seconds must be a real number")
        seconds = float(self.time_seconds)
        if not isfinite(seconds) or seconds < 0:
            raise ValueError("time_seconds must be finite and nonnegative")
        object.__setattr__(self, "time_seconds", seconds)
        limit = self.maximum_absolute_order_effect
        if isinstance(limit, bool) or not isinstance(limit, (int, float)):
            raise TypeError("maximum_absolute_order_effect must be a real number")
        limit = float(limit)
        if not isfinite(limit) or not 0 <= limit <= 0.5:
            raise ValueError(
                "maximum_absolute_order_effect must be between zero and 0.5"
            )
        object.__setattr__(self, "maximum_absolute_order_effect", limit)


@dataclass(frozen=True, slots=True)
class HedonicEvidenceResult:
    state: HedonicEvidenceState
    criterion_id: str
    scope: HedonicScope
    formula_build_sha256: str
    fit_receipt_sha256: str | None
    utility_intervals: dict[str, tuple[float, float]]
    tie_rate: float | None
    directional_comparison_count: int
    assessor_heterogeneity: dict[str, float]
    order_effect: float | None
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_schema_version: str | None = None
    focal_item_id: str | None = None
    evaluation_context_sha256: str | None = None
    item_bindings_sha256: str | None = None
    order_carryover_sha256: str | None = None
    universal_preference_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hedonic_evidence_v3",
            "state": self.state.value,
            "criterion_id": self.criterion_id,
            "scope": self.scope.value,
            "formula_build_sha256": self.formula_build_sha256,
            "fit_receipt_sha256": self.fit_receipt_sha256,
            "utility_intervals": self.utility_intervals,
            "tie_rate": self.tie_rate,
            "directional_comparison_count": self.directional_comparison_count,
            "assessor_heterogeneity": self.assessor_heterogeneity,
            "order_effect": self.order_effect,
            "blockers": self.blockers,
            "limitations": self.limitations,
            "evidence_schema_version": self.evidence_schema_version,
            "focal_item_id": self.focal_item_id,
            "evaluation_context_sha256": self.evaluation_context_sha256,
            "item_bindings_sha256": self.item_bindings_sha256,
            "order_carryover_sha256": self.order_carryover_sha256,
            "universal_preference_authority": self.universal_preference_authority,
            "release_authority": self.release_authority,
        }


def evaluate_hedonic_evidence(
    request: HedonicEvidenceRequest,
) -> HedonicEvidenceResult:
    """Evaluate one fit without converting formulation features into liking."""

    if request.criterion_id != "LIKING":
        return _result(
            request,
            HedonicEvidenceState.INVALID_OR_CONFOUNDED,
            blockers=("criterion_id must be LIKING for hedonic evidence",),
        )
    receipt = request.fit_receipt
    if receipt is None:
        return _result(
            request,
            HedonicEvidenceState.NOT_TESTED,
            limitations=("No blinded exact-scope liking fit was supplied.",),
        )

    blockers: list[str] = []
    exact_fields = (
        "criterion_id",
        "scope",
        "formula_build_sha256",
        "sample_sha256",
        "protocol_sha256",
        "assessor_ids",
        "repeat_ids",
        "time_seconds",
        "schedule_sha256",
    )
    for field_name in exact_fields:
        if getattr(request, field_name) != getattr(receipt, field_name):
            blockers.append(f"{field_name} does not match the fit receipt")
    if isinstance(receipt, PreferenceFitEvidenceReceiptV3):
        if request.focal_item_id != receipt.focal_item_id:
            blockers.append("focal_item_id does not match the V3 fit receipt")
        if (
            request.evaluation_context_sha256
            != receipt.evaluation_context.record_sha256
        ):
            blockers.append(
                "evaluation_context_sha256 does not match the V3 fit receipt"
            )
    if request.safety_event_ids:
        blockers.append("unresolved sensory safety event is present")
    if not receipt.fit_request.require_scoped_validation:
        blockers.append("fit request did not require scoped validation")
    if (
        receipt.fit_result.order_effect is not None
        and abs(receipt.fit_result.order_effect)
        > request.maximum_absolute_order_effect
    ):
        blockers.append(
            "ORDER_EFFECT_EXCEEDS_LIMIT: observed order effect exceeds the declared limit"
        )
    if blockers:
        return _result(
            request,
            HedonicEvidenceState.INVALID_OR_CONFOUNDED,
            receipt=receipt,
            blockers=tuple(blockers),
        )

    fit = receipt.fit_result
    v3 = receipt if isinstance(receipt, PreferenceFitEvidenceReceiptV3) else None
    v2 = (
        receipt
        if isinstance(receipt, PreferenceFitEvidenceReceiptV2)
        else v3.parent_v2
        if v3 is not None
        else None
    )
    if v2 is not None:
        if v2.metadata_missing_codes:
            return _result(
                request,
                HedonicEvidenceState.INVALID_OR_CONFOUNDED,
                receipt=receipt,
                blockers=tuple(
                    f"METADATA_MISSING:{code}"
                    for code in v2.metadata_missing_codes
                ),
            )
        if v2.source_transfer_state not in {"DIRECT", "NARROWER_SCOPE"}:
            return _result(
                request,
                HedonicEvidenceState.INVALID_OR_CONFOUNDED,
                receipt=receipt,
                blockers=("SOURCE_TRANSFER_INVALID",),
            )
        if (
            fit.model_family is not PreferenceModelFamily.DAVIDSON_V1
            or not fit.converged
            or not v2.davidson_fit.converged
        ):
            return _result(
                request,
                HedonicEvidenceState.INSUFFICIENT_EVIDENCE,
                receipt=receipt,
                limitations=("DAVIDSON_FIT_REQUIRED",),
            )
        if v2.heldout_validation.leakage_codes:
            return _result(
                request,
                HedonicEvidenceState.INVALID_OR_CONFOUNDED,
                receipt=receipt,
                blockers=v2.heldout_validation.leakage_codes,
            )
        if not v2.heldout_validation.passed:
            return _result(
                request,
                HedonicEvidenceState.FAILED_HELDOUT_BASELINE,
                receipt=receipt,
                limitations=("PROPER_SCORE_LOWER_BOUND_FAILED",),
            )
        if not v2.cluster_bootstrap.stable:
            return _result(
                request,
                HedonicEvidenceState.INSUFFICIENT_EVIDENCE,
                receipt=receipt,
                limitations=("CLUSTERED_UNCERTAINTY_UNSTABLE",),
            )
        if v2.transitivity.global_winner_withheld:
            return _result(
                request,
                HedonicEvidenceState.DIAGNOSTIC,
                receipt=receipt,
                limitations=(v2.transitivity.state,),
            )
        valid_common = (
            fit.criterion_id == "LIKING"
            and fit.connected
            and v2.davidson_fit.converged
            and v2.heldout_validation.paired_gain_interval[0]
            > v2.heldout_validation.practical_margin
        )
        if not valid_common:
            return _result(
                request,
                HedonicEvidenceState.INVALID_OR_CONFOUNDED,
                receipt=receipt,
                blockers=("PROPER_VALIDATION_CONTRACT_INCONSISTENT",),
            )
        if v3 is None:
            return _result(
                request,
                HedonicEvidenceState.DIAGNOSTIC,
                receipt=receipt,
                limitations=("V3_ITEM_CONTEXT_BINDING_REQUIRED",),
            )
        if v3.adequacy_failure_codes:
            return _result(
                request,
                HedonicEvidenceState.INSUFFICIENT_EVIDENCE,
                receipt=receipt,
                limitations=v3.adequacy_failure_codes,
            )
        if not v3.order_carryover.passed:
            order_blockers = tuple(
                sorted(
                    {
                        *v3.order_carryover.sequence_failure_codes,
                        *(
                            "ORDER_IMBALANCED:"
                            + "|".join(pair)
                            for pair in v3.order_carryover.order_imbalanced_pairs
                        ),
                        *(
                            "ORDER_CONFOUNDED:"
                            + "|".join(pair)
                            for pair in v3.order_carryover.order_confounding_pairs
                        ),
                    }
                )
            )
            return _result(
                request,
                HedonicEvidenceState.INVALID_OR_CONFOUNDED,
                receipt=receipt,
                blockers=order_blockers or ("ORDER_CARRYOVER_CONTRACT_FAILED",),
            )
        return _result(
            request,
            HedonicEvidenceState.VALIDATED_EXACT_SCOPE,
            receipt=receipt,
            limitations=(
                "Validated only for the bound formula, samples, protocol, assessors, "
                "sessions, repeats, matrix, time window, substrate, wearer, order, "
                "carryover controls, and population scope.",
            ),
        )

    if fit.status is PreferenceFitStatus.WITHHELD:
        return _result(
            request,
            HedonicEvidenceState.INSUFFICIENT_EVIDENCE,
            receipt=receipt,
            limitations=fit.gate_failures,
            include_fit=False,
        )
    if any("baseline" in note.lower() for note in fit.validation_notes):
        return _result(
            request,
            HedonicEvidenceState.FAILED_HELDOUT_BASELINE,
            receipt=receipt,
            limitations=fit.validation_notes,
        )
    if fit.status is PreferenceFitStatus.DIAGNOSTIC:
        return _result(
            request,
            HedonicEvidenceState.DIAGNOSTIC,
            receipt=receipt,
            limitations=fit.validation_notes,
        )
    return _result(
        request,
        HedonicEvidenceState.FAILED_HELDOUT_BASELINE,
        receipt=receipt,
        blockers=("PROPER_SCORING_REQUIRED",),
    )


def _result(
    request: HedonicEvidenceRequest,
    state: HedonicEvidenceState,
    *,
    receipt: (
        PreferenceFitEvidenceReceiptV1
        | PreferenceFitEvidenceReceiptV2
        | PreferenceFitEvidenceReceiptV3
        | None
    ) = None,
    blockers: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    include_fit: bool = True,
) -> HedonicEvidenceResult:
    fit = receipt.fit_result if receipt is not None and include_fit else None
    utility_intervals = (
        dict(receipt.cluster_bootstrap.utility_intervals)
        if isinstance(receipt, PreferenceFitEvidenceReceiptV2) and include_fit
        else dict(receipt.parent_v2.cluster_bootstrap.utility_intervals)
        if isinstance(receipt, PreferenceFitEvidenceReceiptV3) and include_fit
        else dict(fit.utility_intervals)
        if fit is not None
        else {}
    )
    return HedonicEvidenceResult(
        state=state,
        criterion_id=request.criterion_id,
        scope=request.scope,
        formula_build_sha256=request.formula_build_sha256,
        fit_receipt_sha256=receipt.record_sha256 if receipt is not None else None,
        utility_intervals=utility_intervals,
        tie_rate=fit.tie_rate if fit is not None else None,
        directional_comparison_count=fit.comparison_count if fit is not None else 0,
        assessor_heterogeneity=(
            dict(fit.assessor_heterogeneity) if fit is not None else {}
        ),
        order_effect=fit.order_effect if fit is not None else None,
        blockers=blockers,
        limitations=limitations,
        evidence_schema_version=(
            "preference_fit_evidence_v3"
            if isinstance(receipt, PreferenceFitEvidenceReceiptV3)
            else "preference_fit_evidence_v2"
            if isinstance(receipt, PreferenceFitEvidenceReceiptV2)
            else "preference_fit_evidence_v1"
            if isinstance(receipt, PreferenceFitEvidenceReceiptV1)
            else None
        ),
        focal_item_id=(
            receipt.focal_item_id
            if isinstance(receipt, PreferenceFitEvidenceReceiptV3)
            else None
        ),
        evaluation_context_sha256=(
            receipt.evaluation_context.record_sha256
            if isinstance(receipt, PreferenceFitEvidenceReceiptV3)
            else None
        ),
        item_bindings_sha256=(
            receipt.item_bindings_sha256
            if isinstance(receipt, PreferenceFitEvidenceReceiptV3)
            else None
        ),
        order_carryover_sha256=(
            receipt.order_carryover.receipt_sha256
            if isinstance(receipt, PreferenceFitEvidenceReceiptV3)
            else None
        ),
    )


__all__ = [
    "EvaluationSubstrate",
    "HedonicEvidenceRequest",
    "HedonicEvidenceResult",
    "HedonicEvidenceState",
    "HedonicScope",
    "PreferenceEvidenceAdequacyContract",
    "PreferenceFitEvidenceReceiptV1",
    "PreferenceFitEvidenceReceiptV2",
    "PreferenceFitEvidenceReceiptV3",
    "PreferenceItemEvidenceBinding",
    "SensoryEvaluationContext",
    "bind_preference_fit_evidence",
    "bind_preference_fit_evidence_v2",
    "bind_preference_fit_evidence_v3",
    "evaluate_hedonic_evidence",
]
