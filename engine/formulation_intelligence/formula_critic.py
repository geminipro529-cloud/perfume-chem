"""Independent deterministic critic for generated perfume design hypotheses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from engine.formulation_intelligence.formula_solver import FormulaSolveResult
from engine.formulation_intelligence.semantic_brief_adapter import SemanticBrief
from engine.name_utils import normalize_name


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _identity_matches(left: object, right: object) -> bool:
    left_key = _key(left)
    right_key = _key(right)
    return (
        normalize_name(str(left or "")) == normalize_name(str(right or ""))
        or left_key in right_key
        or right_key in left_key
    )


@dataclass(frozen=True, slots=True)
class FormulaCriticResult:
    state: str
    issues: tuple[str, ...]
    limitations: tuple[str, ...]
    passed_checks: tuple[str, ...]
    stop_reason: str
    sensory_validation_required: bool
    strongest_clue: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "formula-critic-result-v1",
            "state": self.state,
            "issues": list(self.issues),
            "limitations": list(self.limitations),
            "passed_checks": list(self.passed_checks),
            "stop_reason": self.stop_reason,
            "filler_rows_added": 0,
            "sensory_validation_required": self.sensory_validation_required,
            "strongest_clue": self.strongest_clue,
        }


def critique_formula(
    *,
    brief: SemanticBrief,
    solve: FormulaSolveResult,
    interpretation: Mapping[str, Any],
    max_materials: int,
    liquid_total_ul: int,
) -> FormulaCriticResult:
    issues: list[str] = list(solve.holds)
    limitations = [
        "STRUCTURAL_PROFILE_FIT_IS_NOT_MEASURED_WHOLE_PERFUME_CHARACTER",
        "PLEASANTNESS_NOT_ESTABLISHED",
        "PERSONAL_LIKING_NOT_TESTED",
        "PHYSICAL_RELEASE_AND_TEMPORAL_BEHAVIOR_NOT_VALIDATED",
    ]
    passed: list[str] = []
    rows = list(solve.rows)
    if solve.status != "SOLVED":
        issues.append(solve.status)
    if solve.missing_roles:
        issues.extend(f"UNFILLED_REQUIRED_ROLE:{item}" for item in solve.missing_roles)

    identities = [str(row.get("identity_name", "")) for row in rows]
    stock_ids = [str(row.get("stock_id", "")) for row in rows]
    if len(stock_ids) != len(set(stock_ids)):
        issues.append("DUPLICATE_STOCK_ROW")
    else:
        passed.append("UNIQUE_STOCK_ROWS")
    identity_keys = [_key(value) for value in identities]
    if len(identity_keys) != len(set(identity_keys)):
        issues.append("DUPLICATE_CHEMICAL_OR_PRODUCT_IDENTITY")
    else:
        passed.append("UNIQUE_CHEMICAL_OR_PRODUCT_IDENTITIES")
    if len(rows) > max_materials:
        issues.append("MATERIAL_LIMIT_EXCEEDED")
    else:
        passed.append("MATERIAL_LIMIT_RESPECTED")

    count_constraints = tuple(interpretation.get("material_count_constraints", ()))
    exact_counts = {
        int(row["count"])
        for row in count_constraints
        if row.get("kind") == "EXACT"
    }
    minimums = [
        int(row["count"])
        for row in count_constraints
        if row.get("kind") == "MINIMUM"
    ]
    maximums = [
        int(row["count"])
        for row in count_constraints
        if row.get("kind") == "MAXIMUM"
    ]
    if exact_counts and len(rows) not in exact_counts:
        issues.append("EXACT_MATERIAL_COUNT_NOT_SATISFIED")
    elif minimums and len(rows) < max(minimums):
        issues.append("MINIMUM_MATERIAL_COUNT_NOT_SATISFIED")
    elif maximums and len(rows) > min(maximums):
        issues.append("MAXIMUM_MATERIAL_COUNT_EXCEEDED")
    elif count_constraints:
        passed.append("REQUESTED_MATERIAL_COUNT_CONSTRAINTS_SATISFIED")
    if solve.separate_totals.get("liquid_total_ul") != str(liquid_total_ul):
        issues.append("LIQUID_TOTAL_NOT_CONSERVED")
    elif rows:
        passed.append("LIQUID_TOTAL_CONSERVED")
    if all(row.get("amount_unit") in {"uL", "mg"} for row in rows):
        passed.append("LIQUID_AND_SOLID_UNITS_SEPARATE")
    else:
        issues.append("UNSUPPORTED_OR_MIXED_TRANSFER_UNIT")

    prohibited = tuple(str(item) for item in interpretation.get("prohibited_materials", ()))
    for item in prohibited:
        key = _key(item)
        if key and any(_identity_matches(item, identity) for identity in identities):
            issues.append(f"PROHIBITED_MATERIAL_SELECTED:{item}")
    if not any(item.startswith("PROHIBITED_MATERIAL_SELECTED") for item in issues):
        passed.append("EXACT_MATERIAL_EXCLUSIONS_RESPECTED")

    mandatory = tuple(str(item) for item in interpretation.get("mandatory_materials", ()))
    missing_mandatory = [
        item
        for item in mandatory
        if not any(_identity_matches(item, identity) for identity in identities)
    ]
    issues.extend(f"MANDATORY_MATERIAL_MISSING:{item}" for item in missing_mandatory)
    if not missing_mandatory:
        passed.append("MANDATORY_MATERIALS_PRESENT")

    if any(not row.get("execution_ready", False) for row in rows):
        issues.append("ONE_OR_MORE_ROWS_REQUIRE_STOCK_OR_DILUTION_BINDING")
    if interpretation.get("appeal_mode") == "GLOBAL_CROWD_PLEASING":
        limitations.append("POPULATION_LIKING_NOT_ESTABLISHED")
    limitations.append("SCIENTIFIC_OVERLAYS_REQUIRE_SEPARATE_APPLICABILITY_CHECKS")
    if brief.knowledge_context:
        limitations.append("LITERATURE_ARCHITECTURES_ARE_UNCALIBRATED_DESIGN_HYPOTHESES")
        if brief.knowledge_context.get("state") == "WITHHOLD_UNKNOWN":
            limitations.append("LITERATURE_KNOWLEDGE_UNAVAILABLE")

    unique_issues = tuple(sorted(set(issues)))
    unique_limitations = tuple(sorted(set(limitations)))
    hard_issue_prefixes = (
        "DUPLICATE_STOCK_ROW",
        "DUPLICATE_CHEMICAL_OR_PRODUCT_IDENTITY",
        "MATERIAL_LIMIT_EXCEEDED",
        "EXACT_MATERIAL_COUNT_NOT_SATISFIED",
        "MINIMUM_MATERIAL_COUNT_NOT_SATISFIED",
        "MAXIMUM_MATERIAL_COUNT_EXCEEDED",
        "LIQUID_TOTAL_NOT_CONSERVED",
        "UNSUPPORTED_OR_MIXED_TRANSFER_UNIT",
        "PROHIBITED_MATERIAL_SELECTED:",
        "MANDATORY_MATERIAL_MISSING:",
        "UNFILLED_REQUIRED_ROLE:",
        "WITHHELD_",
    )
    has_hard_issue = any(
        issue.startswith(hard_issue_prefixes)
        for issue in unique_issues
    )
    if has_hard_issue:
        state = "WITHHELD"
    elif unique_issues:
        state = "ACCEPTED_WITH_HOLDS" if rows else "WITHHELD"
    else:
        state = "ACCEPTED_AS_DESIGN_HYPOTHESIS"
    stop_reason = (
        "ALL_JUSTIFIED_ROLES_COVERED"
        if rows and not solve.missing_roles
        else "HARD_OR_STRUCTURAL_CONSTRAINT_UNSATISFIED"
    )
    strongest = (
        f"The request compiled to {len(brief.facets)} named facet(s) and "
        f"{len(brief.roles)} nonredundant functional role(s); "
        f"{len(rows)} exact inventory rows were assigned."
    )
    if brief.knowledge_context.get("strongest_clue"):
        strongest = str(brief.knowledge_context["strongest_clue"])
    return FormulaCriticResult(
        state=state,
        issues=unique_issues,
        limitations=unique_limitations,
        passed_checks=tuple(sorted(set(passed))),
        stop_reason=stop_reason,
        sensory_validation_required=True,
        strongest_clue=strongest,
    )


__all__ = ["FormulaCriticResult", "critique_formula"]
