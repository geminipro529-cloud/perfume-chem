"""Reviewed subtype guidance -> explicitly heuristic comparison role plans.

No prose-to-dose conversion, stock alias, external call or evidence promotion.
The unchanged semantic brief is always retained as the experimental control.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine.formulation_intelligence import architecture_rules_v5 as rules_v5
from engine.formulation_intelligence import literature_knowledge
from engine.formulation_intelligence.literature_knowledge import _positive_text, _present
from engine.formulation_intelligence.semantic_brief_adapter import (
    _FACETS,
    _LITERATURE_FACETS,
    SemanticBrief,
    SemanticRole,
    _key,
)
from engine.formulation_intelligence.source_review import assess_review_bundle, source_record_hash
from engine.formulation_intelligence.subtype_coverage import coverage_for_context
from engine.research.contracts import FALSE_ACTION_AUTHORITY

V1_PATH = (
    Path(__file__).resolve().parents[2] / "data/formulation_knowledge/architecture_adapters_v1.json"
)
V2_PATH = V1_PATH.with_name("architecture_adapters_v2.json")
V3_PATH = V1_PATH.with_name("architecture_adapters_v3.json")
V4_PATH = V1_PATH.with_name("architecture_adapters_v4.json")
V5_PATH = V1_PATH.with_name("architecture_adapters_v5.json")
ADAPTER_PATH = V5_PATH
ADAPTER_SCHEMA = "source-bound-architecture-adapters-v5"
_V1_SHA256 = "2a18a458d26fa891dc665ce4e75f8b8964873d46bbd36a780cd72bcd0a77e3bd"
_V2_SHA256 = "3f2fc6bb721b9902d1d08c4f3b900f7d685008818364dc66bff747adb59b3972"
_V3_SHA256 = "70ec8bd60abefa7d5e09556fece34067caecacba539e6db1fcdea5d7d2f0111c"
_V4_SHA256 = "44776decd27ba01d88dbdbc30b37393b1700c9b9403634be1162044ef01638a3"
_V5_SHA256 = "a88ebdd25e440da5ed23c532e632de2bd05a98ee7abc70ea05590d3a16a67c12"
_V5_SCHEMA = "source-bound-architecture-adapters-v5"
_V5_POLICY = "ISOLATED_ARCHITECTURE_OPERATIONS_V5"
_V4_REQUIREMENTS = {
    ("chypre_floral_axes", "rose_petals"): "rose",
    ("chypre_floral_axes", "jasmine_bridge"): "jasmine",
    ("chypre_green_axes", "bitter_resin"): "bitter_resin_green",
    ("chypre_green_axes", "watery_leaf"): "watery_leaf",
    ("cologne_wood_leaf_bridge", "leaf_bridge"): "citrus_leaf_floral",
}
_TEMPLATES = {item.facet_id: item for item in _FACETS}
# These allocations are local structural hypotheses, never source-derived doses.
# They are deliberately absent from ordinary control compilation and v1-v4 hashes.
_V5_TEMPLATES = {
    **_TEMPLATES,
    "iris_woody": _LITERATURE_FACETS["iris_woody"],
    "iris_cosmetic": _LITERATURE_FACETS["iris_cosmetic"],
}
for _name, _parent, _weights, _share, _cap in (
    ("v5_resin", "incense_resin", (("warmth", .4), ("woody", .2)), .03, .08),
    ("v5_leather", "leather_suede", (("woody", .25), ("spicy", .2)), .03, .07),
    ("v5_cream", "fig", (("creamy", .7),), .03, .08),
    ("v5_toast", "coffee_cocoa", (("warmth", .3),), .02, .05),
    ("v5_hay", "tobacco_hay", (("warmth", .2), ("powdery", .2)), .03, .07),
    ("v5_flower", "floral_bouquet", (("floral", .5),), .03, .08),
    ("v5_terpenic", "aromatic_herbs", (("green", .15), ("floral", .2)), .025, .06),
    ("v5_smoke", "smoke_char", (("smoky", .5), ("woody", .2)), .02, .04),
):
    _V5_TEMPLATES[_name] = replace(
        _TEMPLATES[_parent], facet_id=_name, function="modifier",
        character_weights=_weights, default_share=_share, max_raw_share=_cap,
    )
_POLICY = "EXISTING_SEMANTIC_FACET_TEMPLATES_V1"
_SCOPE = "LOCAL_HEURISTIC_ROLE_MAPPING_NOT_EMPIRICAL_FORMULA"
_CORE = {"opening_articulation", "heart_continuity", "drydown_structure"}
_OPTIONAL_PROVENANCE = {"FUNCTIONAL_COVERAGE", "MINIMUM_FUNCTIONAL_ARCHITECTURE"}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def role_plan_signature(roles: Sequence[SemanticRole]) -> str:
    """Executable differences, not label wording, IDs, or role ordering."""
    plans = [
        {
            "note": role.note,
            "function": role.function,
            "query_terms": sorted({_key(term) for term in role.query_terms}),
            "character_weights": sorted(role.character_weights),
            "share": role.share,
            "required": role.required,
            "exact_material": role.exact_material,
            "max_raw_share": role.max_raw_share,
            "knowledge_role_slot": role.knowledge_role_slot,
            "descriptor_requirement": role.descriptor_requirement,
            # Provenance affects trace-material eligibility in the solver.
            "provenance": role.provenance,
        }
        for role in roles
    ]
    return _digest(sorted(plans, key=_digest))


def _keys(value: Any, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("unknown or incomplete architecture adapter fields")


def _text(value: Any, *, identifier: bool = False) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 600:
        raise ValueError("invalid architecture text")
    if identifier and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
        raise ValueError("invalid architecture identifier")


def _hash(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("unbound architecture source")


def validate_adapter_manifest(value: Any, *, expected_schema: str | None = None) -> None:
    if not isinstance(value, dict):
        raise ValueError("invalid architecture adapter object")
    schema = value.get("schema_version")
    if schema != (expected_schema if expected_schema is not None else ADAPTER_SCHEMA):
        raise ValueError("unexpected architecture adapter schema")
    fields = {"schema_version", "version", "scope", "allocation_policy", "authority", "adapters"}
    if schema in {
        "source-bound-architecture-adapters-v2", "source-bound-architecture-adapters-v3",
        "source-bound-architecture-adapters-v4",
        _V5_SCHEMA,
    }:
        fields.add("predecessor_sha256")
    elif schema != "source-bound-architecture-adapters-v1":
        raise ValueError("unsupported architecture adapter contract")
    _keys(
        value, fields
    )
    if value["scope"] != _SCOPE:
        raise ValueError("unsupported architecture adapter contract")
    if value["allocation_policy"] != (_V5_POLICY if schema == _V5_SCHEMA else _POLICY):
        raise ValueError("unregistered allocation policy")
    _text(value["version"])
    _keys(value["authority"], set(FALSE_ACTION_AUTHORITY))
    if any(flag is not False for flag in value["authority"].values()):
        raise ValueError("architecture adapters have no action authority")
    if not isinstance(value["adapters"], list) or not 1 <= len(value["adapters"]) <= (179 if schema == _V5_SCHEMA else 64):
        raise ValueError("invalid architecture collection")
    seen: set[str] = set()
    subtypes: set[str] = set()
    for adapter in value["adapters"]:
        _keys(
            adapter,
            {
                "adapter_id",
                "subtype_id",
                "subtype_card_sha256",
                "source_bindings",
                "title",
                "options",
            },
        )
        for field in ("adapter_id", "subtype_id"):
            _text(adapter[field], identifier=True)
        _text(adapter["title"])
        _hash(adapter["subtype_card_sha256"])
        if adapter["adapter_id"] in seen or adapter["subtype_id"] in subtypes:
            raise ValueError("duplicate architecture or subtype mapping")
        seen.add(adapter["adapter_id"])
        subtypes.add(adapter["subtype_id"])
        bindings = adapter["source_bindings"]
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("architecture needs source bindings")
        sources: set[str] = set()
        for binding in bindings:
            _keys(binding, {"source_id", "source_record_sha256"})
            _text(binding["source_id"], identifier=True)
            _hash(binding["source_record_sha256"])
            if binding["source_id"] in sources:
                raise ValueError("duplicate architecture source")
            sources.add(binding["source_id"])
        options = adapter["options"]
        if not isinstance(options, list) or not 1 <= len(options) <= 3:
            raise ValueError("invalid comparison options")
        option_ids: set[str] = set()
        for option in options:
            v5_rule = rules_v5.OPTIONS.get(
                (adapter["adapter_id"], str(option.get("option_id"))),
            ) if schema == _V5_SCHEMA and isinstance(option, dict) else None
            requirement = _V4_REQUIREMENTS.get(
                (adapter["adapter_id"], str(option.get("option_id"))),
            ) if isinstance(option, dict) else None
            option_fields = {
                "option_id", "label", "template_id", "query_terms", "conflict_terms",
                "comparison_question", "status",
            }
            if schema in {"source-bound-architecture-adapters-v4", _V5_SCHEMA} and requirement:
                option_fields.add("descriptor_requirement")
            if v5_rule:
                option_fields.update({"descriptor_requirement", "operation", "target_role_id"})
            _keys(
                option, option_fields,
            )
            if v5_rule and (
                tuple(option[k] for k in ("template_id", "descriptor_requirement", "operation", "target_role_id")) != v5_rule
                or v5_rule[1] not in rules_v5.REQUIREMENTS
            ):
                raise ValueError("unregistered v5 architecture operation")
            if not v5_rule and "descriptor_requirement" in option and option["descriptor_requirement"] != requirement:
                raise ValueError("unregistered architecture descriptor requirement")
            _text(option["option_id"], identifier=True)
            if option["option_id"] in option_ids:
                raise ValueError("duplicate architecture option")
            option_ids.add(option["option_id"])
            for field in ("label", "comparison_question"):
                _text(option[field])
            if option["status"] != "UNTESTED_FORMULATION_HYPOTHESIS":
                raise ValueError("architecture is not empirically validated")
            _text(option["template_id"], identifier=True)
            if option["template_id"] not in (_V5_TEMPLATES if v5_rule else _TEMPLATES):
                raise ValueError("unknown role allocation template")
            for field in ("query_terms", "conflict_terms"):
                terms = option[field]
                if not isinstance(terms, list) or not 1 <= len(terms) <= 12:
                    raise ValueError("invalid bounded role vocabulary")
                for term in terms:
                    _text(term)
                if len({_key(term) for term in terms}) != len(terms):
                    raise ValueError("duplicate role vocabulary")
    if schema != "source-bound-architecture-adapters-v1":
        previous_path, previous_hash, previous_schema = {
            "source-bound-architecture-adapters-v2": (V1_PATH, _V1_SHA256, "source-bound-architecture-adapters-v1"),
            "source-bound-architecture-adapters-v3": (V2_PATH, _V2_SHA256, "source-bound-architecture-adapters-v2"),
            "source-bound-architecture-adapters-v4": (V3_PATH, _V3_SHA256, "source-bound-architecture-adapters-v3"),
            _V5_SCHEMA: (V4_PATH, _V4_SHA256, "source-bound-architecture-adapters-v4"),
        }[schema]
        if value["predecessor_sha256"] != previous_hash:
            raise ValueError("unregistered architecture predecessor")
        payload = previous_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != previous_hash:
            raise ValueError("architecture predecessor bytes drifted")
        predecessor = json.loads(payload)
        validate_adapter_manifest(predecessor, expected_schema=previous_schema)
        inherited = predecessor["adapters"]
        if value["adapters"][:len(inherited)] != inherited:
            raise ValueError("architecture predecessor mappings changed")
        if schema == "source-bound-architecture-adapters-v4":
            added = {(a["adapter_id"], o["option_id"])
                     for a in value["adapters"][len(inherited):] for o in a["options"]}
            if added != set(_V4_REQUIREMENTS):
                raise ValueError("unregistered v4 architecture options")
        if schema == _V5_SCHEMA:
            added = {(a["adapter_id"], o["option_id"])
                     for a in value["adapters"][len(inherited):] for o in a["options"]}
            if added != set(rules_v5.OPTIONS):
                raise ValueError("unregistered v5 architecture options")


@dataclass(frozen=True)
class ArchitecturePlanningResult:
    briefs: tuple[SemanticBrief, ...]
    receipt: dict[str, Any]


def _phrase(left: str, right: str) -> bool:
    return bool(_key(right) and f" {_key(right)} " in f" {_key(left)} ")


def _conflicts(option: Mapping[str, Any], avoid: Sequence[str]) -> bool:
    return any(
        _phrase(term, rejected) or _phrase(rejected, term)
        for term in (*option["query_terms"], *option["conflict_terms"])
        for rejected in avoid
        if _key(rejected)
    )


def _support_error(
    adapter: Mapping[str, Any], card: Mapping[str, Any], context: Mapping[str, Any]
) -> str | None:
    # Retrieval may attach a separately reviewed addendum. This adapter binds
    # only the original card and cannot silently consume the addendum's claims.
    base = copy.deepcopy(dict(card))
    addenda = base.pop("review_addenda", [])
    expected = adapter["source_bindings"]
    supplemental = []
    for addendum in addenda:
        if (
            addendum.get("subtype_id") != adapter["subtype_id"]
            or addendum.get("target_card_sha256") != adapter["subtype_card_sha256"]
        ):
            return "ADDENDUM_BINDING_MISMATCH"
        for binding in addendum.get("source_bindings", ()):
            if binding not in expected and binding not in supplemental:
                supplemental.append(binding)
    if base.get("source_bindings") != [*expected, *supplemental]:
        return "SOURCE_BINDING_MISMATCH"
    base["source_bindings"] = copy.deepcopy(expected)
    if _digest(base) != adapter["subtype_card_sha256"]:
        return "SUBTYPE_CARD_DRIFT"
    for binding in expected:
        identity = binding["source_id"]
        sources = [row for row in context.get("sources", ()) if row.get("source_id") == identity]
        reviews = [row for row in context.get("source_reviews", ()) if row.get("source_id") == identity]
        if len(sources) > 1 or len(reviews) > 1:
            return "AMBIGUOUS_SOURCE_OR_REVIEW_IDENTITY"
        if len(sources) != 1 or len(reviews) != 1 or reviews[0].get("allowed") is not True:
            return "SOURCE_REVIEW_UNAVAILABLE"
        if source_record_hash(sources[0]) != binding["source_record_sha256"]:
            return "SOURCE_RECORD_DRIFT"
        try:
            reviewed = assess_review_bundle(sources, literature_knowledge.SOURCE_REVIEWS_PATH.read_bytes())
            if (reviewed["manifest_sha256"] != context.get("source_review_manifest_sha256")
                    or reviewed["assessments"] != reviews):
                return "SOURCE_REVIEW_RECEIPT_DRIFT"
        except (OSError, ValueError, TypeError, KeyError):
            return "SOURCE_REVIEW_UNAVAILABLE"
    return None


def protected_role_set(
    roles: Sequence[SemanticRole], preserve: Sequence[str], recognizers: Sequence[str],
) -> tuple[SemanticRole, ...]:
    """Pure executable protection rule, shared with the independent receipt audit."""
    terms = tuple(dict.fromkeys((*preserve, *recognizers)))
    return tuple(role for role in roles if (
        role.exact_material is not None or role.role_id in _CORE
        or role.provenance not in _OPTIONAL_PROVENANCE
        or any(_phrase(role.role_id, term) or _phrase(role.label, term)
               or any(_phrase(q, term) for q in role.query_terms) for term in terms)
    ))


def mapped_roles(
    *, control_roles: Sequence[SemanticRole], protected: Sequence[SemanticRole],
    adapter: Mapping[str, Any], option: Mapping[str, Any], max_materials: int,
    exact_count: bool,
) -> tuple[tuple[SemanticRole, ...], str | None] | None:
    """Apply one registered comparison; never infer a source dose or replace an anchor."""
    roles = list(control_roles)
    if option.get("operation") == "REFINE_ROLE":
        targets = [i for i, r in enumerate(roles) if r.role_id == option["target_role_id"]]
        if len(targets) != 1:
            return None
        target = targets[0]
        if roles[target] != _canonical_refinement_role(option["template_id"]):
            return None
        roles[target] = replace(roles[target], descriptor_requirement=option["descriptor_requirement"])
        return tuple(roles), None
    donor = next((i for i, r in reversed(list(enumerate(roles))) if r not in protected), None)
    if donor is None and (len(roles) >= max_materials or exact_count):
        return None
    template = (_V5_TEMPLATES if "operation" in option else _TEMPLATES)[option["template_id"]]
    role = SemanticRole(
        role_id=f"research_{adapter['adapter_id']}_{option['option_id']}",
        label=option["label"], note=template.note, function=template.function,
        query_terms=tuple(option["query_terms"]), character_weights=template.character_weights,
        share=template.default_share, max_raw_share=template.max_raw_share,
        provenance="SOURCE_BOUND_ARCHITECTURE_HEURISTIC",
        descriptor_requirement=option.get(
            "descriptor_requirement", "fruit" if template.facet_id == "fruit" else None,
        ),
    )
    replaced_id = roles[donor].role_id if donor is not None else None
    if donor is None:
        roles.append(role)
    else:
        roles[donor] = role
    return tuple(roles), replaced_id


def _canonical_refinement_role(template_id: str) -> SemanticRole:
    template = _V5_TEMPLATES[template_id]
    return SemanticRole(
        role_id=f"facet_{template.facet_id}",
        label=f"{template.facet_id.replace('_', ' ').title()} expression",
        note=template.note, function=template.function, query_terms=template.query_terms,
        character_weights=template.character_weights, share=template.default_share,
        max_raw_share=template.max_raw_share, knowledge_role_slot=template.knowledge_role_slot,
    )


def protected_roles_preserved(
    control_roles: Sequence[SemanticRole], roles: Sequence[SemanticRole],
    protected: Sequence[SemanticRole], binding: Mapping[str, Any],
) -> bool:
    """Exact legacy equality, or one proved v5 canonical predicate strengthening."""
    if binding.get("operation") != "REFINE_ROLE":
        return all(role in roles for role in protected)
    adapter_id, option_id = binding.get("adapter_id"), binding.get("option_id")
    if not isinstance(adapter_id, str) or not isinstance(option_id, str):
        return False
    rule = rules_v5.OPTIONS.get((adapter_id, option_id))
    if not rule or rule[2] != "REFINE_ROLE" or binding.get("adapter_schema_version") != _V5_SCHEMA:
        return False
    template, requirement, _, target = rule
    original = _canonical_refinement_role(template)
    refined = replace(original, descriptor_requirement=requirement)
    return bool(
        len(roles) == len(control_roles)
        and sum(r.role_id == target for r in control_roles) == 1
        and all((a == original and b == refined) if a.role_id == target else a == b
                for a, b in zip(control_roles, roles))
        and binding.get("target_role_id") == target
        and binding.get("operation_before_sha256") == _digest(asdict(original))
        and binding.get("operation_after_sha256") == _digest(asdict(refined))
    )


def option_binding(
    *, manifest: Mapping[str, Any], manifest_hash: str, adapter: Mapping[str, Any],
    option: Mapping[str, Any], roles: Sequence[SemanticRole],
    control_roles: Sequence[SemanticRole], protected: Sequence[SemanticRole],
    replaced_id: str | None,
) -> dict[str, Any]:
    """Exact option/template/policy/lineage receipt, reconstructable without a solver."""
    templates = _V5_TEMPLATES if manifest["schema_version"] == _V5_SCHEMA else _TEMPLATES
    binding = {
        "kind": "SOURCE_BOUND_ARCHITECTURE_COMPARISON",
        "adapter_id": adapter["adapter_id"], "subtype_id": adapter["subtype_id"],
        "option_id": option["option_id"], "label": option["label"],
        "comparison_question": option["comparison_question"], "status": option["status"],
        "source_bindings": copy.deepcopy(adapter["source_bindings"]),
        "subtype_card_sha256": adapter["subtype_card_sha256"],
        "adapter_manifest_sha256": manifest_hash,
        "allocation_policy_sha256": _digest({k: asdict(v) for k, v in templates.items()}),
        "template_id": option["template_id"],
        "template_sha256": _digest(asdict(templates[option["template_id"]])),
        "role_id": f"research_{adapter['adapter_id']}_{option['option_id']}",
        "replaced_optional_role_id": replaced_id,
        "role_plan_sha256": role_plan_signature(roles),
        "control_role_plan_sha256": role_plan_signature(control_roles),
        "protected_and_prompt_roles_unchanged": all(r in roles for r in protected),
        "stock_aliases_inferred": False, "dose_evidence_class": "LOCAL_HEURISTIC",
        "sensory_preservation_measured": False, "authority": dict(FALSE_ACTION_AUTHORITY),
    }
    if "predecessor_sha256" in manifest:
        binding.update({
            "adapter_schema_version": manifest["schema_version"],
            "adapter_version": manifest["version"],
            "predecessor_sha256": manifest["predecessor_sha256"],
        })
    if "descriptor_requirement" in option:
        binding["descriptor_requirement"] = option["descriptor_requirement"]
    if "operation" in option:
        binding.update({
            "operation": option["operation"], "target_role_id": option["target_role_id"],
            "comparison_scope": "ARCHITECTURE_HYPOTHESIS_NOT_CONTROLLED_PHYSICAL_OMISSION",
            "background_stock_doses_fixed": False,
            "descriptor_absence_certified": False,
        })
        if option["operation"] == "REFINE_ROLE":
            binding["role_id"] = option["target_role_id"]
            before = next(r for r in control_roles if r.role_id == binding["role_id"])
            after = next(r for r in roles if r.role_id == binding["role_id"])
            binding["operation_before_sha256"] = _digest(asdict(before))
            binding["operation_after_sha256"] = _digest(asdict(after))
        binding["protected_constraints_preserved"] = protected_roles_preserved(control_roles, roles, protected, binding)
    return binding


def derive_architecture_briefs(
    *,
    control: SemanticBrief,
    interpretation: Mapping[str, Any],
    max_materials: int,
    max_architectures: int = 2,
) -> ArchitecturePlanningResult:
    """Retain control; add at most two reviewed, independent comparison branches."""
    if type(max_architectures) is not int or not 0 <= max_architectures <= 2:
        raise ValueError("architecture comparison budget must be zero through two")
    if type(max_materials) is not int or not 1 <= max_materials <= 60:
        raise ValueError("invalid architecture material ceiling")
    context = control.knowledge_context
    subtypes = context.get("subtype_context", {})
    registry = _V5_TEMPLATES if ADAPTER_SCHEMA == _V5_SCHEMA else _TEMPLATES
    templates = {key: asdict(value) for key, value in registry.items()}
    receipt: dict[str, Any] = {
        "schema_version": "source-bound-architecture-plan-v1",
        "state": "NO_APPLICABLE_ADAPTER",
        "scope": _SCOPE,
        "adapter_manifest_sha256": None,
        "allocation_policy": _V5_POLICY if ADAPTER_SCHEMA == _V5_SCHEMA else _POLICY,
        "allocation_policy_sha256": _digest(templates),
        "allocation_evidence_class": "HEURISTIC_NOT_SOURCE_CALIBRATION",
        "control_role_plan_sha256": role_plan_signature(control.roles),
        "comparison_budget": max_architectures,
        "max_materials": max_materials,
        "request_sha256": control.request_sha256,
        "interpretation_sha256": interpretation.get("interpretation_sha256"),
        "knowledge_pack_sha256": context.get("pack_sha256"),
        "source_review_manifest_sha256": context.get("source_review_manifest_sha256"),
        "subtype_research_sha256": context.get("subtype_research_sha256"),
        "preserve_constraints": list(interpretation.get("must_preserve", ())),
        "avoid_constraints": list(interpretation.get("must_avoid", ())),
        "campaign_identity_holds": copy.deepcopy(subtypes.get("campaign_identity_holds", [])),
        "candidates": [],
        "withheld_options": [],
        "deferred_options": [],
        "unsupported_subtype_ids": [],
        "numeric_calibrations_admitted": [],
        "formula_action": "NO_CHANGE",
        "network_used": False,
        "authority": dict(FALSE_ACTION_AUTHORITY),
    }

    def result(briefs: Sequence[SemanticBrief] = (control,)) -> ArchitecturePlanningResult:
        receipt["plan_sha256"] = _digest(receipt)
        return ArchitecturePlanningResult(tuple(briefs), copy.deepcopy(receipt))

    if receipt["campaign_identity_holds"]:
        receipt["state"] = "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED"
        return result()
    if "SUBTYPE_MANIFEST_UNAVAILABLE_OR_DRIFTED" in subtypes.get(
        "reason_codes", ()
    ) or not context.get("pack_sha256"):
        receipt["state"] = "WITHHOLD_UNKNOWN"
        return result()
    try:
        payload = ADAPTER_PATH.read_bytes()
        if ADAPTER_SCHEMA == _V5_SCHEMA and hashlib.sha256(payload).hexdigest() != _V5_SHA256:
            raise ValueError("v5 adapter bytes drifted")
        manifest = json.loads(payload)
        if not isinstance(manifest, dict) or manifest.get("schema_version") != ADAPTER_SCHEMA:
            raise ValueError("active architecture schema downgraded or changed")
        validate_adapter_manifest(manifest, expected_schema=ADAPTER_SCHEMA)
    except (OSError, ValueError, TypeError, KeyError):
        receipt["state"] = "WITHHOLD_UNKNOWN"
        receipt["reason_codes"] = ["ARCHITECTURE_ADAPTER_UNAVAILABLE_OR_INVALID"]
        return result()
    receipt["adapter_manifest_sha256"] = hashlib.sha256(payload).hexdigest()
    if manifest["schema_version"] == _V5_SCHEMA:
        receipt["implementation_coverage"] = coverage_for_context(context)
        if receipt["implementation_coverage"]["state"] == "WITHHOLD_UNKNOWN":
            receipt["state"] = "WITHHOLD_UNKNOWN"
            receipt["reason_codes"] = ["SUBTYPE_DISPOSITION_UNAVAILABLE_OR_DRIFTED"]
            return result()
    if "predecessor_sha256" in manifest:
        receipt.update({
            "adapter_schema_version": manifest["schema_version"],
            "adapter_version": manifest["version"],
            "predecessor_sha256": manifest["predecessor_sha256"],
        })
    card_map = {card["subtype_id"]: card for card in subtypes.get("cards", ())}
    supported_ids = {adapter["subtype_id"] for adapter in manifest["adapters"]}
    receipt["unsupported_subtype_ids"] = sorted(set(card_map) - supported_ids)
    avoid = tuple(str(item) for item in interpretation.get("must_avoid", ()))
    preserve = tuple(str(item) for item in interpretation.get("must_preserve", ()))
    receipt["protected_recognizers"] = list(control.protected_recognizers)
    exact_count = any(
        row.get("kind") == "EXACT" for row in interpretation.get("material_count_constraints", ())
    )
    protected_roles = protected_role_set(control.roles, preserve, control.protected_recognizers)
    briefs: list[SemanticBrief] = [control]
    signatures = {receipt["control_role_plan_sha256"]}
    adapters = manifest["adapters"]
    if manifest["schema_version"] in {
        "source-bound-architecture-adapters-v3", "source-bound-architecture-adapters-v4",
        _V5_SCHEMA,
    }:
        # A direct request outranks incidental title tokens (e.g. the diagnostic
        # name 'muguet_cyclamen'). Preserve names for retrieval, not priority over
        # explicitly requested facets. Then prefer conjunctive specificity.
        # Stable ties retain manifest order; none of these keys ranks scent.
        direct = _positive_text(control.normalized_request, avoid)

        def specificity(adapter: Mapping[str, Any]) -> tuple[bool, int]:
            groups = card_map.get(adapter["subtype_id"], {}).get("match_groups", ())
            direct_match = bool(groups) and all(
                any(_present(direct, phrase) for phrase in group) for group in groups
            )
            return not direct_match, -len(groups)

        adapters = sorted(adapters, key=specificity)
    for adapter in adapters:
        card = card_map.get(adapter["subtype_id"])
        if card is None:
            if adapter["subtype_id"] in subtypes.get("withheld_subtype_ids", ()):
                receipt["withheld_options"].append(
                    {"adapter_id": adapter["adapter_id"], "reason": "SUBTYPE_SOURCE_WITHHELD"}
                )
            continue
        error = _support_error(adapter, card, context)
        if error:
            receipt["withheld_options"].append(
                {"adapter_id": adapter["adapter_id"], "reason": error}
            )
            continue
        for option in adapter["options"]:
            identity = f"{adapter['adapter_id']}:{option['option_id']}"
            if _conflicts(option, avoid):
                receipt["withheld_options"].append(
                    {"option": identity, "reason": "EXPLICIT_AVOID_CONFLICT"}
                )
                continue
            mapped = mapped_roles(
                control_roles=control.roles, protected=protected_roles, adapter=adapter,
                option=option, max_materials=max_materials, exact_count=exact_count,
            )
            if mapped is None:
                receipt["withheld_options"].append(
                    {"option": identity, "reason": (
                        "CANONICAL_REFINEMENT_TARGET_UNAVAILABLE" if option.get("operation") == "REFINE_ROLE"
                        else "NO_UNPROTECTED_ROLE_CAPACITY"
                    )}
                )
                continue
            roles, replaced_id = mapped
            signature = role_plan_signature(roles)
            if signature in signatures:
                receipt["withheld_options"].append(
                    {"option": identity, "reason": "DUPLICATE_EXECUTABLE_ARCHITECTURE"}
                )
                continue
            if len(briefs) - 1 >= max_architectures:
                receipt["deferred_options"].append(
                    {"option": identity, "reason": "COMPARISON_BUDGET"}
                )
                continue
            binding = option_binding(
                manifest=manifest, manifest_hash=receipt["adapter_manifest_sha256"],
                adapter=adapter, option=option, roles=roles, control_roles=control.roles,
                protected=protected_roles, replaced_id=replaced_id,
            )
            briefs.append(
                replace(control, roles=tuple(roles), architecture_plan=copy.deepcopy(binding))
            )
            signatures.add(signature)
            receipt["candidates"].append(binding)
    if len(briefs) > 1:
        receipt["state"] = "SOURCE_BOUND_COMPARISON_READY"
    elif receipt["withheld_options"]:
        receipt["state"] = "WITHHELD_NO_ELIGIBLE_ARCHITECTURE"
    return result(briefs)


__all__ = [
    "ADAPTER_PATH",
    "ArchitecturePlanningResult",
    "derive_architecture_briefs",
    "role_plan_signature",
    "validate_adapter_manifest",
]
