"""Primary Formula Studio runtime: semantic target, solver, critic, receipts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from functools import wraps
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Sequence

from engine.formulation_intelligence.architecture_bridge import (
    derive_architecture_briefs,
    role_plan_signature,
)
from engine.formulation_intelligence.composition_checks import attach_composition_checks
from engine.formulation_intelligence.formula_critic import critique_formula
from engine.formulation_intelligence.formula_solver import (
    FormulaSolveResult,
    _has_exact_material_count,
    solve_formula,
)
from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
from engine.formulation_intelligence.material_capability_index import (
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    SemanticBrief,
    compile_semantic_brief,
)
from engine.research.composition_planner import (
    _concept,
    _inventory_text_sha256,
    _reference_context,
    _reference_registry_sha256,
    _temporal_hypothesis,
    compose_inventory_formula,
)
from engine.research.contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash
from engine.research.request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)

DesignMode = Literal["FAST_SKETCH", "DEEP_COMPOSE"]


def _material_count_policy(
    interpretation: dict[str, Any],
    configured_maximum: int,
) -> tuple[int, int | None, tuple[str, ...]]:
    """Resolve prompt count constraints against the caller's hard ceiling."""

    constraints = tuple(interpretation.get("material_count_constraints", ()))
    exact = {
        int(row["count"])
        for row in constraints
        if row.get("kind") == "EXACT"
    }
    minimums = [
        int(row["count"])
        for row in constraints
        if row.get("kind") == "MINIMUM"
    ]
    maximums = [
        int(row["count"])
        for row in constraints
        if row.get("kind") == "MAXIMUM"
    ]
    effective_maximum = min(
        [configured_maximum, *maximums, *(exact if len(exact) == 1 else ())]
    )
    target = next(iter(exact)) if len(exact) == 1 else (max(minimums) if minimums else None)
    issues: list[str] = []
    if effective_maximum < 1:
        issues.append("MATERIAL_COUNT_CEILING_BELOW_ONE")
    if target is not None and target > configured_maximum:
        issues.append("REQUESTED_MATERIAL_COUNT_EXCEEDS_CONFIGURED_CEILING")
    if target is not None and target > effective_maximum:
        issues.append("REQUESTED_MATERIAL_COUNT_EXCEEDS_REQUESTED_MAXIMUM")
    return max(1, effective_maximum), target, tuple(issues)


def _withheld_count_conflict(
    *,
    name: str,
    interpretation: dict[str, Any],
    design_mode: DesignMode,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    report = {
        "schema_version": "inventory-grounded-formula-design-v3",
        "status": "WITHHELD_REQUEST_AMBIGUOUS",
        "formula_name": name,
        "design_mode": design_mode,
        "request_interpretation": interpretation,
        "initial_formula": None,
        "optimized_formula": None,
        "design_variants": [],
        "assistant_message": (
            "The requested material count conflicts with the configured or stated "
            "ceiling, so no formula was invented."
        ),
        "reason_codes": list(reason_codes),
        "formula_action": "NO_CHANGE",
        "inventory_modified": False,
        "formula_modified": False,
        "physical_compounding_performed": False,
        "pleasantness": None,
        "personal_liking": None,
        "population_liking": None,
        "beauty_score": None,
        "prohibited_objectives_used": [],
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "design_sha256": stable_payload_hash(report)}


def _curated_concept_is_applicable(concept_id: str, text: str) -> bool:
    """Require a concept's defining conjunction, not one accidental phrase."""

    normalized = text.casefold()
    checks = {
        "bitter_grapefruit_tea": ("tea", "grapefruit"),
        "dry_lavender_fougere": ("lavender",),
        "rose_suede_chypre": ("rose",),
        "green_fig_cardamom": ("fig",),
        "green_tuberose": ("tuberose",),
        "iris_incense_cathedral": ("iris", "incense"),
        "dry_coffee_cocoa": ("coffee", "cocoa"),
        "mineral_coast": ("mineral",),
        "intimate_skin": ("skin",),
        "monsoon_market": ("rain",),
    }
    required = checks.get(concept_id, ())
    if not all(token in normalized for token in required):
        return False
    if concept_id == "intimate_skin" and re.search(
        r"\b(?:apple|pear|peach|plum|grape|citrus|orange|lemon|fruit)\s+skin\b",
        normalized,
    ):
        return False
    if concept_id == "intimate_skin" and re.search(
        r"\b(?:animalic|fur|civet|castoreum|costus)\b",
        normalized,
    ):
        return False
    if concept_id == "monsoon_market" and not re.search(
        r"\b(?:monsoon|after rain|wet pavement|night[- ]market)\b",
        normalized,
    ):
        return False
    return True


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _derive_name(idea: str) -> str:
    stop = {
        "a", "an", "and", "create", "for", "formula", "fragrance", "make",
        "new", "of", "perfume", "scent", "the", "to", "with",
    }
    words = [
        word
        for word in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+", idea)
        if word.casefold() not in stop
    ][:4]
    return " ".join(word[:1].upper() + word[1:] for word in words) or "Untitled Formula"


def _positive_integer_volume(value: object) -> int:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("liquid_concentrate_ul_decimal must be a finite positive decimal") from exc
    if not parsed.is_finite() or parsed <= 0 or parsed != parsed.to_integral_value():
        raise ValueError("liquid concentrate must be a positive whole number of uL")
    if parsed > 100_000:
        raise ValueError("liquid concentrate must be no greater than 100000 uL")
    return int(parsed)


def _with_runtime_metadata(
    report: dict[str, Any],
    *,
    brief: SemanticBrief | None,
    design_mode: DesignMode,
) -> dict[str, Any]:
    enhanced = dict(report)
    enhanced["schema_version"] = "inventory-grounded-formula-design-v3"
    enhanced["design_mode"] = design_mode
    enhanced["runtime"] = {
        "schema_version": "formula-design-runtime-v1",
        "method": "VERIFIED_NEURO_SYMBOLIC_PERFUME_DESIGN_COMPILER",
        "semantic_target_compiled": brief is not None,
        "inventory_constraints_deterministic": True,
        "dose_arithmetic_deterministic": True,
        "sensory_outcome_claimed": False,
        "network_used": False,
    }
    interpretation = enhanced.get("request_interpretation", {})
    enhanced["formulation_knowledge"] = (
        brief.knowledge_context if brief is not None else retrieve_formulation_knowledge(
            str(interpretation.get("original_request", enhanced.get("formula_name", ""))),
            avoid=tuple(interpretation.get("must_avoid", ())),
        )
    )
    if brief is not None:
        enhanced["semantic_brief"] = brief.as_dict()
        enhanced["target_intent"] = brief.target_intent
    optimized = enhanced.get("optimized_formula")
    if optimized is not None and "design_variants" not in enhanced:
        enhanced["design_variants"] = [
            {
                "variant_id": "curated-architecture-primary",
                "label": "Primary structural hypothesis",
                "ordering": "UNORDERED_WITH_UNTESTED_ALTERNATIVES",
                "formula": optimized,
            }
        ]
    enhanced["design_sha256"] = stable_payload_hash(
        {key: value for key, value in enhanced.items() if key != "design_sha256"}
    )
    return enhanced


def _formula_payload(solve: FormulaSolveResult, role_count: int) -> dict[str, Any]:
    coverage = len(solve.assignments) / max(1, role_count)
    return {
        "rows": list(solve.rows),
        "separate_totals": solve.separate_totals,
        "active_mass_basis_state": "PARTIAL_OR_WITHHELD_PER_ROW",
        "exact_active_mass_established": False,
        "request_alignment_decimal": format(Decimal(str(round(coverage, 6))), "f"),
        "request_alignment_basis": "STRUCTURAL_ROLE_COVERAGE_ONLY_NOT_SENSORY_ACCURACY",
        "basis_state": (
            "SEPARATE_LIQUID_AND_SOLID_TOTALS"
            if int(solve.separate_totals.get("mass_total_mg", "0")) > 0
            else "LIQUID_STOCK_VOLUME_ONLY"
        ),
    }


def _stock_dose_signature(formula: dict[str, Any]) -> str | None:
    """Exact stock-dose equivalence only; not active mass or sensory sameness.

    Independent of role labels and row splitting. Invalid rows cannot suppress
    another candidate. The external diagnostic separately verifies conservation.
    """
    def digest(value: Any) -> str:
        return hashlib.sha256(json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False,
        ).encode()).hexdigest()

    try:
        identities: dict[str, dict[str, Any]] = {}
        amounts: dict[str, Decimal] = {}
        if not formula["rows"]:
            return None
        for row in formula["rows"]:
            amount, fraction = (Decimal(row[k]) if isinstance(row[k], str) else Decimal("NaN")
                                for k in ("amount_decimal", "stock_fraction_decimal"))
            if not amount.is_finite() or amount <= 0 or not fraction.is_finite() or not 0 < fraction <= 1:
                return None
            identity = {k: row[k] for k in (
                "stock_id", "identity_name", "fraction_basis", "carrier", "amount_unit", "operation",
            )}
            if not all(isinstance(identity[k], str) and identity[k] for k in (
                "stock_id", "identity_name", "fraction_basis",
            )) or (identity["amount_unit"], identity["operation"]) not in {
                ("uL", "DIRECT_ADD"), ("uL", "PREPARED_DILUTION_REQUIRED"), ("mg", "MASS_ADD"),
            }:
                return None
            identity["stock_fraction_decimal"] = format(fraction.normalize(), "f")
            key = digest(identity)
            identities[key] = identity
            amounts[key] = amounts.get(key, Decimal(0)) + amount
        return digest(sorted(({
            **identities[key], "amount_decimal": format(amount.normalize(), "f"),
        } for key, amount in amounts.items()), key=digest))
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return None


def _dynamic_report(
    *,
    name: str,
    idea: str,
    mode: DesignMode,
    maximum: int,
    configured_maximum: int,
    liquid_total_ul: int,
    interpretation: dict[str, Any],
    brief: SemanticBrief,
    index: Any,
    solves: Sequence[FormulaSolveResult],
    appeal_mode: str,
    variant_briefs: Sequence[SemanticBrief] | None = None,
    architecture_planning: dict[str, Any] | None = None,
    previous_stock_ids: Sequence[str] = (),
) -> dict[str, Any]:
    paired = list(zip(variant_briefs or [brief] * len(solves), solves, strict=True))
    successful = [(candidate, solve) for candidate, solve in paired if solve.rows]
    attempts = [{
        "variant_id": solve.variant_id, "state": solve.status,
        "role_count": len(candidate.roles),
        "role_plan_sha256": role_plan_signature(candidate.roles),
        "architecture": candidate.architecture_plan or {"kind": "UNCHANGED_CONTROL_OR_STOCK_ALTERNATIVE"},
        "missing_roles": list(solve.missing_roles), "holds": list(solve.holds),
        "assigned_role_ids": [assignment.role.role_id for assignment in solve.assignments],
        "assignment_bindings": [{"role_id": a.role.role_id, "stock_id": a.capability.stock_id}
                                for a in solve.assignments],
        "solver": solve.solver_receipt,
    } for candidate, solve in paired]
    execution_inputs = {
        "schema_version": "architecture-execution-inputs-v1",
        "liquid_total_ul_decimal": str(liquid_total_ul),
        "explicit_quantities": list(interpretation.get("explicit_quantities", ())),
        "previous_stock_ids": list(previous_stock_ids),
        "effective_inventory_sha256": index.effective_inventory_sha256,
    }
    if not successful:
        reason_codes = sorted(
            {
                solve.status
                for solve in solves
            }
            | {
                f"UNFILLED_REQUIRED_ROLE:{role}"
                for solve in solves
                for role in solve.missing_roles
            }
            | {hold for solve in solves for hold in solve.holds}
        )
        report = {
            "schema_version": "inventory-grounded-formula-design-v3",
            "status": "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE",
            "formula_name": name,
            "design_mode": mode,
            "request_interpretation": interpretation,
            "semantic_brief": brief.as_dict(),
            "formulation_knowledge": brief.knowledge_context,
            "target_intent": brief.target_intent,
            "initial_formula": None,
            "optimized_formula": None,
            "design_variants": [],
            "architecture_planning": architecture_planning,
            "architecture_attempts": attempts,
            "architecture_execution_inputs": execution_inputs,
            "assistant_message": "The current inventory cannot cover every required structural role without inventing filler or violating a hard constraint.",
            "reason_codes": reason_codes,
            "formula_action": "NO_CHANGE",
            "inventory_modified": False,
            "formula_modified": False,
            "physical_compounding_performed": False,
            "pleasantness": None,
            "personal_liking": None,
            "population_liking": None,
            "beauty_score": None,
            "prohibited_objectives_used": [],
            **FALSE_ACTION_AUTHORITY,
        }
        return {**report, "design_sha256": stable_payload_hash(report)}

    variants: list[dict[str, Any]] = []
    retained_physical: dict[str, str] = {}
    all_critics: list[dict[str, Any]] = []
    labels = (
        "Intended structural hypothesis",
        "Conservative material alternative",
        "Diverse structural alternative",
    )
    for candidate_brief, solve in successful:
        is_control = candidate_brief is paired[0][0] and solve is paired[0][1]
        critic = critique_formula(
            brief=candidate_brief,
            solve=solve,
            interpretation=interpretation,
            max_materials=maximum,
            liquid_total_ul=liquid_total_ul,
        )
        critic_payload = critic.as_dict()
        all_critics.append(critic_payload)
        variant_formula = _formula_payload(solve, len(candidate_brief.roles))
        physical_signature = _stock_dose_signature(variant_formula)
        if candidate_brief.architecture_plan and physical_signature is not None and physical_signature in retained_physical:
            attempt = next(a for a in attempts if a["variant_id"] == solve.variant_id)
            attempt.update({
                "state": "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION",
                "duplicate_of_variant_id": retained_physical[physical_signature],
                "physical_composition_sha256": physical_signature,
                "suppressed_formula": variant_formula,
                "suppressed_critic": critic_payload,
            })
            continue
        if physical_signature is not None and critic.state != "WITHHELD":
            retained_physical[physical_signature] = solve.variant_id
        variants.append(
            {
                "variant_id": solve.variant_id,
                "label": candidate_brief.architecture_plan.get("label") or (
                    "Unchanged structural control" if architecture_planning and is_control
                    else "Stock alternative · same role plan" if architecture_planning
                    else labels[min(len(variants), len(labels) - 1)]
                ),
                "ordering": "UNORDERED_UNTIL_SENSORY_COMPARISON",
                "formula": variant_formula,
                "formula_action": "NO_CHANGE" if critic.state == "WITHHELD" else "PROPOSAL_ONLY",
                "solver": solve.solver_receipt,
                "critic": critic_payload,
                "temporal_hypothesis": _temporal_hypothesis(
                    variant_formula["rows"], interpretation.get("evaluation_windows", ()),
                    f"{name} {idea}",
                ),
                "commercial_reference_context": _reference_context(
                    f"{name} {idea}", appeal_mode=appeal_mode, concept=None,
                    rows=variant_formula["rows"],
                ),
                "architecture": candidate_brief.architecture_plan or {
                    "kind": "UNCHANGED_CONTROL" if is_control
                    else "STOCK_ALTERNATIVE_SAME_ROLE_PLAN",
                },
                "role_plan_sha256": role_plan_signature(candidate_brief.roles),
                "roles_requested": [role.role_id for role in candidate_brief.roles],
                "role_plan": [
                    asdict(role)
                    for role in candidate_brief.roles
                ],
            }
        )
    primary = variants[0]
    brief = successful[0][0]
    formula = primary["formula"]
    rows = formula["rows"]
    temporal = primary["temporal_hypothesis"]
    reference = primary["commercial_reference_context"]
    primary_critic = primary["critic"]
    issues = primary_critic["issues"]
    hard_withhold = primary_critic["state"] == "WITHHELD"
    status = (
        "WITHHELD_HARD_CONSTRAINT_UNSATISFIED"
        if hard_withhold
        else (
            "INVENTORY_GROUNDED_DESIGN_READY_WITH_HOLDS"
            if issues
            else "INVENTORY_GROUNDED_DESIGN_READY"
        )
    )
    request_payload = {
        "idea": idea,
        "formula_name": name,
        "design_mode": mode,
        "liquid_total_ul": liquid_total_ul,
        "max_materials": maximum,
        "interpretation_sha256": interpretation["interpretation_sha256"],
        "target_intent_receipt_sha256": brief.target_intent["receipt_sha256"],
        "inventory_sha256": index.effective_inventory_sha256,
        "commercial_reference_registry_sha256": _reference_registry_sha256(),
        "knowledge_pack_sha256": brief.knowledge_context.get("pack_sha256"),
        "prior_research_corpus_sha256": brief.knowledge_context.get("prior_corpus_sha256"),
        "source_review_manifest_sha256": brief.knowledge_context.get("source_review_manifest_sha256"),
        "construction_library_sha256": brief.knowledge_context.get("construction_library_sha256"),
        "subtype_research_sha256": brief.knowledge_context.get("subtype_research_sha256"),
        "architecture_plan_sha256": (architecture_planning or {}).get("plan_sha256"),
    }
    report = {
        "schema_version": "inventory-grounded-formula-design-v3",
        "architecture_execution_inputs": execution_inputs,
        "status": status,
        "request_sha256": stable_payload_hash(request_payload),
        "formula_name": name,
        "design_mode": mode,
        "concept_family": (
            brief.family_neighborhoods[0]
            if brief.family_neighborhoods
            else "request_defined_architecture"
        ),
        "matched_descriptors": list(brief.facets),
        "request_interpretation": interpretation,
        "semantic_brief": brief.as_dict(),
        "formulation_knowledge": brief.knowledge_context,
        "target_intent": brief.target_intent,
        "runtime": {
            "schema_version": "formula-design-runtime-v1",
            "method": "VERIFIED_NEURO_SYMBOLIC_PERFUME_DESIGN_COMPILER",
            "semantic_target_compiled": True,
            "inventory_constraints_deterministic": True,
            "global_role_assignment": True,
            "dose_arithmetic_deterministic": True,
            "sensory_outcome_claimed": False,
            "network_used": False,
        },
        "inventory": {
            "snapshot_sha256": index.inventory_snapshot_sha256,
            "overlay_sha256": index.inventory_overlay_sha256,
            "completion_sha256": index.inventory_completion_sha256,
            "effective_inventory_sha256": index.effective_inventory_sha256,
            "inventory_text_sha256": _inventory_text_sha256(),
            "eligible_design_stock_count": len(index.capabilities),
        },
        "composition_plan": {
            "method": "SEMANTIC_TARGET_PLUS_GLOBAL_CONSTRAINT_SOLVER_V1",
            "concept_id": "request_defined_architecture",
            "facets": list(brief.facets),
            "roles_requested": [role.role_id for role in brief.roles],
            "roles_filled": [assignment.role.role_id for assignment in successful[0][1].assignments],
            "stop_rule": "STOP_WHEN_ALL_JUSTIFIED_ROLES_ARE_FILLED",
            "ingredient_count_is_objective": False,
            "character_basis": "COMPONENT_PROFILE_HYPOTHESIS_NOT_SENSORY_MEASUREMENT",
            "commercial_reference_context": reference,
        },
        "initial_formula": formula,
        "optimized_formula": None if hard_withhold else formula,
        "design_variants": variants,
        "architecture_planning": architecture_planning,
        "architecture_attempts": attempts,
        "optimization": {
            "status": "GLOBAL_CONSTRAINT_ASSIGNMENT_COMPLETE",
            "objective": "REQUEST_CONSTRAINT_AND_NONREDUNDANT_ROLE_FULFILMENT",
            "architecture_preserved": not any(item.architecture_plan for item, _ in paired),
            "target_request_preserved": True,
            "iterations": 1,
            "initial_alignment_decimal": formula["request_alignment_decimal"],
            "optimized_alignment_decimal": formula["request_alignment_decimal"],
            "meaning": "The solver assigns exact inventory stocks to prompt-derived roles; it does not optimize a beauty proxy.",
            "not_established": [
                "measured mixture character",
                "pleasantness",
                "personal liking",
                "population liking",
                "beauty",
                "sensory superiority",
            ],
        },
        "design_reasoning": [
            {
                "pass": "SEMANTIC_TARGET_COMPILE",
                "result": f"The request produced {len(brief.facets)} named facets and {len(brief.roles)} bounded functional roles.",
            },
            {
                "pass": "GLOBAL_STOCK_ASSIGNMENT",
                "result": f"The solver evaluated {len(index.capabilities)} current-inventory capabilities jointly instead of filling roles greedily.",
            },
            {
                "pass": "EXACT_ARITHMETIC",
                "result": "Liquid stock volume is conserved exactly; solid mass operations remain separate.",
            },
            {
                "pass": "INDEPENDENT_CRITIC",
                "result": f"The critic retained {len(primary_critic['issues'])} execution hold(s) and {len(primary_critic['limitations'])} evidence limitation(s).",
            },
        ],
        "constraint_audit": {
            "state": "PASS_WITH_HOLDS" if issues else "PASS",
            "explicit_materials": interpretation.get("explicit_materials", []),
            "mandatory_materials": interpretation.get("mandatory_materials", []),
            "prohibited_materials": interpretation.get("prohibited_materials", []),
            "avoid_constraints": interpretation.get("must_avoid", []),
            "liquid_total_conserved": formula["separate_totals"]["liquid_total_ul"] == str(liquid_total_ul),
            "solid_mass_kept_separate": True,
            "material_limit_respected": len(rows) <= maximum,
            "holds": issues,
            "limitations": primary_critic["limitations"],
        },
        "critic": primary_critic,
        "temporal_hypothesis": temporal,
        "commercial_reference_context": reference,
        "scientific_overlays": {
            "release": {"state": "UNAVAILABLE_UNTIL_APPLICABLE_SCENARIO_AND_PARAMETERS"},
            "gas_phase_detection": {"state": "UNAVAILABLE_UNTIL_COMPATIBLE_RELEASE_AND_THRESHOLD"},
            "individual_intensity": {"state": "UNAVAILABLE_UNTIL_EXACT_CURVE_APPLICABILITY"},
            "mixture_intensity": {"state": "UNAVAILABLE_UNTIL_COMPONENT_COVERAGE_AND_ADMITTED_RULE"},
            "character": {"state": "STRUCTURAL_COMPONENT_PROFILE_HYPOTHESIS_ONLY"},
            "pleasantness": {"state": "NOT_ESTABLISHED"},
            "personal_liking": {"state": "NOT_TESTED"},
        },
        "requested_material_limit": configured_maximum,
        "effective_material_limit": maximum,
        "selected_material_count": len(rows),
        "assistant_message": (
            f"I compiled {name} into {len(brief.facets)} request-specific facet(s) and "
            f"{len(brief.roles)} functional role(s), then jointly assigned {len(rows)} exact "
            f"inventory stocks. The {len(variants)} returned design hypothesis/hypotheses are "
            "unordered until you smell them."
        ),
        "formula_action": "NO_CHANGE" if hard_withhold else "PROPOSAL_ONLY",
        "next_step": "Review the concise holds and choose the smallest practical pilot only if you want to compound it.",
        "inventory_modified": False,
        "formula_modified": False,
        "physical_compounding_performed": False,
        "pleasantness": None,
        "personal_liking": None,
        "population_liking": None,
        "beauty_score": None,
        "prohibited_objectives_used": [],
        **FALSE_ACTION_AUTHORITY,
    }
    return {**report, "design_sha256": stable_payload_hash(report)}


def _with_composition_checks(design: Any) -> Any:
    """Attach the gate's advisory crowding/IFRA checks to every composed formula."""

    @wraps(design)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return attach_composition_checks(design(*args, **kwargs))

    return wrapper


@_with_composition_checks
def design_formula(
    *,
    idea: str,
    formula_name: str | None = None,
    liquid_concentrate_ul_decimal: str = "6000",
    max_materials: int = 15,
    must_preserve: Sequence[str] = (),
    must_avoid: Sequence[str] = (),
    previous_stock_ids: Sequence[str] = (),
    conversation_context: Sequence[str] = (),
    execution_strategy: str | None = None,
    appeal_mode: str | None = None,
    comparison_evidence: str = "DOCUMENT_ONLY",
    active_bottle_id: str | None = None,
    design_mode: DesignMode = "FAST_SKETCH",
    variant_count: int | None = None,
) -> dict[str, Any]:
    """Design one read-only inventory formula through the verified compiler."""

    clean_idea = _clean(idea)
    if not clean_idea:
        raise ValueError("idea must be non-empty text")
    if design_mode not in {"FAST_SKETCH", "DEEP_COMPOSE"}:
        raise ValueError("design_mode must be FAST_SKETCH or DEEP_COMPOSE")
    maximum = int(max_materials)
    if not 6 <= maximum <= 60:
        raise ValueError("max_materials must be between 6 and 60")
    liquid_total_ul = _positive_integer_volume(liquid_concentrate_ul_decimal)
    requested_variants = variant_count if variant_count is not None else (
        3 if design_mode == "DEEP_COMPOSE" else 1
    )
    if not 1 <= int(requested_variants) <= 3:
        raise ValueError("variant_count must be from one to three")
    name = _clean(formula_name) or _derive_name(clean_idea)

    initial_index = build_material_capability_index()
    interpretation = interpret_request(
        RequestInterpretationInputV1(
            original_request=clean_idea,
            known_materials=initial_index.known_materials,
            desired_changes=(clean_idea,),
            must_preserve=tuple(must_preserve),
            must_avoid=tuple(must_avoid),
            execution_strategy=execution_strategy,
            appeal_mode=appeal_mode,
            comparison_evidence=comparison_evidence,
            active_bottle_id=active_bottle_id,
        )
    )
    effective_maximum, target_material_count, count_issues = _material_count_policy(
        interpretation,
        maximum,
    )
    if count_issues:
        return _with_runtime_metadata(_withheld_count_conflict(
            name=name,
            interpretation=interpretation,
            design_mode=design_mode,
            reason_codes=count_issues,
        ), brief=None, design_mode=design_mode)
    if interpretation["confirmation_required"] or interpretation["execution_strategy"] == "EVOLVING_BOTTLE":
        legacy = compose_inventory_formula(
            idea=clean_idea,
            formula_name=name,
            liquid_concentrate_ul_decimal=str(liquid_total_ul),
            max_materials=maximum,
            must_preserve=must_preserve,
            must_avoid=must_avoid,
            previous_stock_ids=previous_stock_ids,
            conversation_context=conversation_context,
            execution_strategy=execution_strategy,
            appeal_mode=appeal_mode,
            comparison_evidence=comparison_evidence,
            active_bottle_id=active_bottle_id,
        )
        return _with_runtime_metadata(legacy, brief=None, design_mode=design_mode)

    design_text = " ".join((name, *conversation_context, clean_idea))
    brief = compile_semantic_brief(
        formula_name=name,
        request=" ".join((*conversation_context, clean_idea)),
        interpretation=interpretation,
        max_materials=effective_maximum,
        target_material_count=target_material_count,
    )
    if not brief.knowledge_context.get("subtype_research_sha256"):
        # An unreadable hold-bearing manifest is not an empty hold list. This
        # blocks corrupt governance, not requests lacking empirical calibration.
        withheld = _withheld_count_conflict(
            name=name, interpretation=interpretation, design_mode=design_mode,
            reason_codes=("CAMPAIGN_GOVERNANCE_UNAVAILABLE",),
        )
        withheld.update({
            "status": "WITHHELD_GOVERNANCE_UNAVAILABLE",
            "assistant_message": "Local research and campaign-identity rules could not be verified. Restore the reviewed knowledge files before generating a formula.",
        })
        return _with_runtime_metadata(withheld, brief=brief, design_mode=design_mode)
    campaign_holds = brief.knowledge_context.get("subtype_context", {}).get("campaign_identity_holds", ())
    if campaign_holds:
        withheld = _withheld_count_conflict(
            name=name, interpretation=interpretation, design_mode=design_mode,
            reason_codes=("HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED",),
        )
        recovered_messages = [
            hold["recovered_reference"]["runtime_message"]
            for hold in campaign_holds if hold.get("recovered_reference")
        ]
        withheld.update({
            "status": "WITHHELD_CAMPAIGN_IDENTITY",
            "assistant_message": " ".join(recovered_messages) if recovered_messages else "The accepted campaign brief or formula has not been recovered. Please supply it; adjacent perfume styles are not substitutes.",
            "recovered_campaign_references": [
                hold["recovered_reference"] for hold in campaign_holds if hold.get("recovered_reference")
            ],
        })
        return _with_runtime_metadata(withheld, brief=brief, design_mode=design_mode)

    # Curated capsules remain useful for their exact, reviewed architecture.
    # They are a governed specialization inside the compiler, not the generic
    # fallback.  Unrecognized requests proceed to the semantic global solver.
    curated_concept = _concept(design_text)
    specific_iris_violet = any(
        profile.startswith(("iris_", "violet_"))
        for profile in brief.knowledge_context.get("profile_ids", ())
    )
    if not specific_iris_violet and design_mode == "FAST_SKETCH" and curated_concept is not None and _curated_concept_is_applicable(
        curated_concept.concept_id,
        design_text,
    ):
        curated = compose_inventory_formula(
            idea=clean_idea,
            formula_name=name,
            liquid_concentrate_ul_decimal=str(liquid_total_ul),
            max_materials=maximum,
            must_preserve=must_preserve,
            must_avoid=must_avoid,
            previous_stock_ids=previous_stock_ids,
            conversation_context=conversation_context,
            execution_strategy=execution_strategy,
            appeal_mode=appeal_mode,
            comparison_evidence=comparison_evidence,
            active_bottle_id=active_bottle_id,
        )
        return _with_runtime_metadata(curated, brief=brief, design_mode=design_mode)

    explicit = tuple(interpretation.get("explicit_materials", ()))
    index = initial_index.with_explicit_materials(explicit)
    mandatory = tuple(interpretation.get("mandatory_materials", ()))
    missing = [item for item in mandatory if not index.exact_matches(str(item))]
    if missing:
        legacy = compose_inventory_formula(
            idea=clean_idea,
            formula_name=name,
            liquid_concentrate_ul_decimal=str(liquid_total_ul),
            max_materials=maximum,
            must_preserve=must_preserve,
            must_avoid=must_avoid,
            previous_stock_ids=previous_stock_ids,
            conversation_context=conversation_context,
            execution_strategy=execution_strategy,
            appeal_mode=appeal_mode,
            comparison_evidence=comparison_evidence,
            active_bottle_id=active_bottle_id,
        )
        return _with_runtime_metadata(legacy, brief=brief, design_mode=design_mode)

    avoid = tuple(dict.fromkeys((*must_avoid, *interpretation.get("must_avoid", ()))))
    planning = derive_architecture_briefs(
        control=brief, interpretation=interpretation, max_materials=effective_maximum,
        max_architectures=int(requested_variants) - 1,
    ) if design_mode == "DEEP_COMPOSE" else None
    branch_briefs = list(planning.briefs) if planning is not None else [brief]
    # Unsupported requests retain the existing stock-alternative behavior.
    # When a real source-bound comparison exists, do not pad missing branches
    # with misleading architecture labels or duplicate the accepted plan.
    if len(branch_briefs) == 1:
        branch_briefs = [brief] * int(requested_variants)
    solves: list[FormulaSolveResult] = []
    prior: set[str] = set()
    for variant_index, candidate_brief in enumerate(branch_briefs):
        solve = solve_formula(
            brief=candidate_brief,
            index=index,
            liquid_total_ul=liquid_total_ul,
            explicit_quantities=interpretation.get("explicit_quantities", ()),
            avoid=avoid,
            previous_stock_ids=previous_stock_ids,
            prior_variant_stock_ids=() if candidate_brief.architecture_plan else tuple(prior),
            variant_index=variant_index,
            beam_width=48 if design_mode == "DEEP_COMPOSE" else 12,
            exact_material_count=_has_exact_material_count(interpretation),
        )
        solves.append(solve)
        prior.update(assignment.capability.stock_id for assignment in solve.assignments)
    return _dynamic_report(
        name=name,
        idea=clean_idea,
        mode=design_mode,
        maximum=effective_maximum,
        configured_maximum=maximum,
        liquid_total_ul=liquid_total_ul,
        interpretation=interpretation,
        brief=brief,
        index=index,
        solves=solves,
        appeal_mode=interpretation["appeal_mode"],
        variant_briefs=branch_briefs,
        architecture_planning=planning.receipt if planning is not None else None,
        previous_stock_ids=previous_stock_ids,
    )


__all__ = ["DesignMode", "design_formula"]
