"""Coverage-matched comparator reports and truthful completion declarations."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash


@dataclass(frozen=True, slots=True)
class ComparatorEvidenceV1:
    comparator_id: str
    formula_sha256: str
    inventory_sha256: str
    scenario_sha256: str
    capability_bundle_sha256: str
    active_accounting: Mapping[str, Any]
    release_coverage_decimal: str
    endpoint_results: Mapping[str, Mapping[str, Any]]
    physically_tested: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.comparator_id, str) or not self.comparator_id.strip():
            raise ValueError("comparator_id must be non-empty text")
        object.__setattr__(self, "comparator_id", self.comparator_id.strip())
        for name in (
            "formula_sha256",
            "inventory_sha256",
            "scenario_sha256",
            "capability_bundle_sha256",
        ):
            value = getattr(self, name)
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} must be lowercase SHA-256")
        try:
            coverage = float(self.release_coverage_decimal)
        except (TypeError, ValueError) as exc:
            raise ValueError("release coverage must be numeric text") from exc
        if not math.isfinite(coverage) or not 0 <= coverage <= 1:
            raise ValueError("release coverage must be from zero to one")
        if not isinstance(self.physically_tested, bool):
            raise TypeError("physically_tested must be boolean")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_design_evidence(
    comparators: Sequence[ComparatorEvidenceV1],
    *,
    ordered_endpoint: str | None = None,
    lower_is_better: bool = True,
) -> dict[str, Any]:
    """Compare immutable designs only when boundaries and coverage match."""

    rows = tuple(comparators)
    if len(rows) < 2:
        raise ValueError("at least two immutable comparators are required")
    if len({row.comparator_id for row in rows}) != len(rows):
        raise ValueError("comparator IDs must be unique")
    boundary_fields = (
        "inventory_sha256",
        "scenario_sha256",
        "capability_bundle_sha256",
    )
    boundary_mismatch = [
        field
        for field in boundary_fields
        if len({getattr(row, field) for row in rows}) != 1
    ]
    coverage_mismatch = len({row.release_coverage_decimal for row in rows}) != 1
    report_rows = [row.as_dict() for row in rows]
    classifications: list[str] = []
    if boundary_mismatch:
        classifications.append("OUT_OF_DOMAIN")
    else:
        payload_hashes = {
            stable_payload_hash(
                {
                    "active_accounting": row.active_accounting,
                    "endpoint_results": row.endpoint_results,
                }
            )
            for row in rows
        }
        if len(payload_hashes) > 1:
            classifications.append("COMPUTATIONALLY_DIFFERENT")
    if not all(row.physically_tested for row in rows):
        classifications.append("NOT_PHYSICALLY_TESTED")

    ranking: list[dict[str, Any]] = []
    reasons: list[str] = []
    if boundary_mismatch:
        reasons.extend(f"BOUNDARY_MISMATCH:{field}" for field in boundary_mismatch)
    if coverage_mismatch:
        reasons.append("MODEL_COVERAGE_DIFFERS")
    if ordered_endpoint is not None and not reasons:
        estimates: list[tuple[ComparatorEvidenceV1, Mapping[str, Any]]] = []
        for row in rows:
            endpoint = row.endpoint_results.get(ordered_endpoint)
            if not isinstance(endpoint, Mapping):
                reasons.append(f"ENDPOINT_MISSING:{row.comparator_id}")
                continue
            if endpoint.get("applicability_state") != "APPLICABLE":
                reasons.append(f"ENDPOINT_NOT_APPLICABLE:{row.comparator_id}")
                continue
            value = endpoint.get("value")
            interval = endpoint.get("uncertainty_interval")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or not isinstance(interval, (list, tuple))
                or len(interval) != 2
                or any(
                    isinstance(bound, bool)
                    or not isinstance(bound, (int, float))
                    or not math.isfinite(float(bound))
                    for bound in interval
                )
            ):
                reasons.append(f"ENDPOINT_UNCERTAINTY_INCOMPLETE:{row.comparator_id}")
                continue
            estimates.append((row, endpoint))
        estimates.sort(
            key=lambda item: (
                float(item[1]["value"]) if lower_is_better else -float(item[1]["value"]),
                item[0].comparator_id,
            )
        )
        if len(estimates) == len(rows):
            separated = all(
                (
                    float(left[1]["uncertainty_interval"][1])
                    < float(right[1]["uncertainty_interval"][0])
                    if lower_is_better
                    else float(left[1]["uncertainty_interval"][0])
                    > float(right[1]["uncertainty_interval"][1])
                )
                for left, right in zip(estimates, estimates[1:])
            )
            if separated:
                ranking = [
                    {
                        "comparator_id": row.comparator_id,
                        "endpoint": ordered_endpoint,
                        "value": endpoint["value"],
                        "uncertainty_interval": endpoint["uncertainty_interval"],
                    }
                    for row, endpoint in estimates
                ]
                classifications.append("SUPPORTED_ENDPOINT_IMPROVEMENT")
            else:
                reasons.append("UNCERTAINTY_NONDISCRIMINATING")
    if reasons or (ordered_endpoint is not None and not ranking):
        classifications.append("NONDISCRIMINATING_EVIDENCE")

    report = {
        "schema_version": "immutable-design-comparison-v1",
        "comparators": report_rows,
        "ordered_endpoint": ordered_endpoint,
        "classifications": sorted(set(classifications)),
        "ranked_comparators": ranking,
        "unordered_comparators": (
            sorted(row.comparator_id for row in rows) if not ranking else []
        ),
        "reason_codes": sorted(set(reasons)),
        "formula_action": "PROPOSE_ONLY" if ranking else "NO_CHANGE",
        "physical_liking_state": (
            "TESTED" if all(row.physically_tested for row in rows) else "NOT_TESTED"
        ),
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "comparison_sha256": stable_payload_hash(report)}


def project_completion_states(
    *,
    generic_platform_contracts_pass: bool,
    computational_comparison_complete: bool,
    personal_selection_complete: bool,
    qualified_commercial_release_receipt_present: bool,
) -> dict[str, Any]:
    """Separate software, computational, personal, and commercial completion."""

    values = (
        generic_platform_contracts_pass,
        computational_comparison_complete,
        personal_selection_complete,
        qualified_commercial_release_receipt_present,
    )
    if any(not isinstance(value, bool) for value in values):
        raise TypeError("completion inputs must be boolean")
    platform = generic_platform_contracts_pass
    computational = platform and computational_comparison_complete
    personal = computational and personal_selection_complete
    # Perfume-Chem can record a qualified external release receipt, but cannot
    # grant commercial readiness itself.
    commercial = personal and qualified_commercial_release_receipt_present
    return {
        "schema_version": "perfume-chem-completion-states-v1",
        "PLATFORM_SOFTWARE_COMPLETE": platform,
        "R6_COMPUTATIONAL_EVIDENCE_COMPLETE": computational,
        "PERSONAL_SELECTION_COMPLETE": personal,
        "COMMERCIAL_RELEASE_READY": commercial,
        "commercial_state_source": (
            "QUALIFIED_EXTERNAL_RECEIPT_RECORDED"
            if commercial
            else "OUTSIDE_AUTOMATIC_PROJECT_BOUNDARY"
        ),
        "automatic_commercial_authority": False,
        **FALSE_ACTION_AUTHORITY,
    }


__all__ = [
    "ComparatorEvidenceV1",
    "compare_design_evidence",
    "project_completion_states",
]
