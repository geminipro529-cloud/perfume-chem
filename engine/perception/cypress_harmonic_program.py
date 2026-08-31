"""Integrated, non-voting design program for the CYP-02 Cypress perfume.

This module composes the current material atlas, Cypress-heart Pareto frontier,
universal family-depth contracts, relational architecture compiler,
zero-or-one Architectural Delta, Temporal Sensory Ledger boundary, and
criterion-scoped preference boundary into one exact-scope harmonic request.

The modules do not cast votes.  They retain separate namespaces and authority
ceilings.  A design module can block an internally contradictory architecture;
an absent empirical module withholds sensory/hedonic claims without preventing
a clearly labelled computational experiment design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.inventory.authority import (
    InventoryAuthorityProjection,
    InventoryAvailabilityState,
)
from engine.material_capability_atlas import (
    InventoryCapabilityState,
    MaterialCapabilityAtlas,
    build_material_capability_atlas,
)
from engine.perception.architectural_delta import ArchitecturalDeltaResult
from engine.perception.architecture_compiler import (
    ArchitectureCompileResult,
    compile_architecture,
)
from engine.perception.architecture_contracts import (
    ArchitectureCompileRequest,
    ArchitectureLayerContract,
    ArchitectureStrategyAssignment,
    ArchitectureStrategyId,
    ArchitectureTransitionContract,
    TargetFunctionContract,
)
from engine.perception.cypress_heart_frontier import (
    CypressHeartFrontierRequestV1,
    CypressHeartFrontierResultV1,
    CypressHeartFrontierState,
    build_default_cypress_heart_frontier_request,
    evaluate_cypress_heart_frontier,
)
from engine.perception.depth_contracts import (
    DepthArchitectureProfileV1,
    DepthEvaluationResultV1,
    PerfumeFamily,
)
from engine.perception.depth_evaluation import evaluate_depth_profile
from engine.perception.depth_family_adapters import (
    build_bounded_reference_depth_profile,
)
from engine.perception.harmonic_synthesis import (
    HarmonicModuleReportV1,
    HarmonicModuleState,
    HarmonicRelationV1,
    HarmonicSynthesisRequestV1,
    HarmonicSynthesisResultV1,
    report_from_architectural_delta,
    report_from_architecture_compiler,
    report_from_cypress_heart_frontier,
    report_from_family_depth,
    report_from_material_atlas,
    report_from_preference,
    report_from_temporal_evidence,
    synthesize_harmonically,
)


class _AtlasCompilerSnapshot:
    """Conservative architecture-compiler view over the same live atlas.

    This adapter supplies source identity and qualitative availability only.
    It deliberately does not fabricate an ExactStockRef, active-equivalence
    authority, or physical execution readiness.  CYP-02's compiler request is
    currently target/ideal-only; current-build readiness is checked separately
    by the harmonic material dispositions against the atlas.
    """

    def __init__(self, atlas: MaterialCapabilityAtlas) -> None:
        self._atlas = atlas
        self.workbook_sha256 = atlas.v5_workbook_sha256
        self.overlay_sha256 = atlas.user_overlay_sha256
        self.workbook_record_count = atlas.v5_stock_count
        self.alias_record_count = max(
            0,
            atlas.current_stock_row_count - atlas.current_identity_count,
        )

    def project(self, material: str) -> InventoryAuthorityProjection:
        record = self._atlas.project(material)
        if record.inventory_state in {
            InventoryCapabilityState.OWNED_EXECUTABLE,
            InventoryCapabilityState.OWNED_HELD,
        }:
            state = InventoryAvailabilityState.OWNED
        elif record.inventory_state is InventoryCapabilityState.UNAVAILABLE:
            state = InventoryAvailabilityState.UNAVAILABLE
        else:
            state = InventoryAvailabilityState.UNLISTED
        note_parts = [*record.blockers]
        if record.current_stocks:
            note_parts.extend(
                f"{stock.raw_name}: {stock.status}"
                for stock in record.current_stocks
            )
        return InventoryAuthorityProjection(
            requested_name=material,
            canonical_name=record.canonical_name,
            state=state,
            stock=None,
            exact_stock_ref=None,
            physical_execution_ready=False,
            active_equivalence_ready=False,
            molecular_mechanism_authority=False,
            formula_rebase_authorized=False,
            general_substitution_authorized=False,
            source_rows=record.v5_source_rows,
            status=record.inventory_state.value,
            note="; ".join(note_parts) or None,
        )


def _function(
    function_id: str,
    description: str,
    target_link: str,
    omission_loss: str,
    success_observable: str,
    failure_observable: str,
    *evidence_refs: str,
) -> TargetFunctionContract:
    return TargetFunctionContract(
        function_id=function_id,
        description=description,
        target_link=target_link,
        omission_loss=omission_loss,
        success_observable=success_observable,
        failure_observable=failure_observable,
        evidence_refs=tuple(evidence_refs),
    )


def _build_architecture_request(
    frontier_result: CypressHeartFrontierResultV1,
) -> ArchitectureCompileRequest:
    selected = frontier_result.selected_candidate
    if (
        frontier_result.state is not CypressHeartFrontierState.THEORY_SELECTED
        or selected is None
    ):
        raise ValueError(
            "a unique theory-selected Cypress heart is required before compilation"
        )
    target = frontier_result.target
    functions = (
        _function(
            "CYPRESS_IDENTITY",
            "continuous Cypress subject and aromatic-green vertical axis",
            "The named brief requires French Cypress EO to remain the sole subject.",
            "The perfume loses its reason for existing and becomes a generic woody floral.",
            "Blinded target-fidelity observations retain Cypress recognition across the declared temporal schedule.",
            "Cypress is masked, reads only in the opening, or becomes cleaner, pencil, sauna, or background twig.",
            "target://cyp-02/brief/v1",
            "doi:10.1186/1472-6882-14-179",
        ),
        _function(
            "MAGNOLIA_RELIEF",
            "Magnolia petal-light relief around the dry Cypress line",
            "The perfume must reveal the niceness of Cypress rather than imitate a tree.",
            "Cypress remains severe, planar, and aromatherapy-like.",
            "Magnolia adds petal light and bodily softness while Cypress remains the named subject.",
            "The heart becomes a clean white floral and Cypress is demoted to decoration.",
            "doi:10.1080/14786419.2012.696256",
            "doi:10.1186/s12864-017-3846-8",
        ),
        _function(
            "ORRIS_SHADOW",
            "cool Orris rhizome-shadow and violet-wood depth",
            "A lower tactile register is required to make the petal light and Cypress axis feel dimensional.",
            "The perfume has radiance and wood but no rooted depth or intimate shadow.",
            "The lower register reads as cool rhizome shadow without becoming the subject.",
            "Lipstick, makeup powder, buttery opacity, or generic iris identity replaces Cypress.",
            "doi:10.1038/s41598-025-08925-z",
        ),
        _function(
            "TEMPORAL_REVEAL",
            "Cypress-to-petal-to-rhizome handoff and return",
            "Depth is defined by linked change through time, not simultaneous ingredient presence.",
            "The composition reads as a static block or as unrelated top, heart, and base perfumes.",
            "Cypress opens the relation, Magnolia expands it, Orris grounds it, and Cypress remains legible in the return.",
            "The floral heart arrives too early, the shadow drops abruptly, or the drydown becomes an unrelated woody wall.",
            "doi:10.1016/j.foodchem.2021.129483",
            "doi:10.1242/jeb.242274",
        ),
    )
    return ArchitectureCompileRequest(
        target_identity=target.target_identity,
        target_reference="CYP-02-CYPRESS-NATIVE-BRIEF-V1",
        family_adapter_id="WOODY_AROMATIC_FLORAL_CYPRESS_SUBJECT",
        target_recognizers=(
            "high-quality French Cypress EO dry-green aromatic wood",
            "Magnolia petal-light relief",
            "Orris rhizome-shadow depth",
        ),
        target_invariants=target.positive_invariants,
        forbidden_drift=target.forbidden_drift,
        ideal_formula_ref=target.ideal_formula_ref,
        current_inventory_build_ref=target.current_inventory_build_ref,
        formula_lineage_sha256=frontier_result.record_sha256,
        primary_strategy=ArchitectureStrategyAssignment(
            strategy_id=ArchitectureStrategyId.CHIAROSCURO_DUAL_STATE,
            owns_function_ids=("MAGNOLIA_RELIEF", "ORRIS_SHADOW"),
            rationale=(
                "Petal light and rhizome shadow define a controlled counterform around "
                "the Cypress subject; neither state is an ingredient-count claim."
            ),
        ),
        secondary_strategies=(
            ArchitectureStrategyAssignment(
                strategy_id=ArchitectureStrategyId.TEMPORAL_METAMORPHOSIS,
                owns_function_ids=("CYPRESS_IDENTITY", "TEMPORAL_REVEAL"),
                rationale=(
                    "The named subject must persist while the relation changes through "
                    "opening, heart, late heart, and drydown."
                ),
            ),
        ),
        functions=functions,
        layers=(
            ArchitectureLayerContract(
                layer_id="CYPRESS_AXIS",
                temporal_position="opening through drydown",
                spatial_position="continuous central vertical axis",
                texture="dry-green aromatic wood with polished grain",
                function_ids=("CYPRESS_IDENTITY",),
            ),
            ArchitectureLayerContract(
                layer_id="PETAL_LIGHT",
                temporal_position="opening-to-heart expansion",
                spatial_position="luminous field around the Cypress axis",
                texture="cream-white petal air with restrained body",
                function_ids=("MAGNOLIA_RELIEF",),
            ),
            ArchitectureLayerContract(
                layer_id="RHIZOME_SHADOW",
                temporal_position="heart-to-drydown lower register",
                spatial_position="near-field shadow beneath the axis",
                texture="cool tactile rhizome, violet wood, and soft mineral suede",
                function_ids=("ORRIS_SHADOW",),
            ),
            ArchitectureLayerContract(
                layer_id="RELATIONAL_HANDOFF",
                temporal_position="entire scheduled trajectory",
                spatial_position="interfaces among axis, light, and shadow",
                texture="legato transition with retained contrast",
                function_ids=("TEMPORAL_REVEAL",),
            ),
        ),
        transitions=(
            ArchitectureTransitionContract(
                transition_id="CYPRESS-TO-PETAL",
                from_layer_id="CYPRESS_AXIS",
                to_layer_id="PETAL_LIGHT",
                relation="tension relief without subject replacement",
                intended_effect="Magnolia makes Cypress feel more bodily, inviting, and luxurious while Cypress remains identifiable.",
                failure_mode="The floral field masks Cypress or produces a generic clean floral.",
                evidence_refs=(
                    "comparison://cyp-02/cypress-magnolia-omission/v1",
                    "doi:10.1093/chemse/bjn026",
                ),
            ),
            ArchitectureTransitionContract(
                transition_id="PETAL-TO-RHIZOME",
                from_layer_id="PETAL_LIGHT",
                to_layer_id="RHIZOME_SHADOW",
                relation="chiaroscuro vertical depth",
                intended_effect="The lower cool register makes the upper petal light feel dimensional rather than merely louder.",
                failure_mode="The registers separate or collapse into cosmetic powder.",
                evidence_refs=(
                    "comparison://cyp-02/magnolia-orris-factorial/v1",
                    "doi:10.1242/jeb.242274",
                ),
            ),
            ArchitectureTransitionContract(
                transition_id="RHIZOME-TO-CYPRESS-RETURN",
                from_layer_id="RHIZOME_SHADOW",
                to_layer_id="RELATIONAL_HANDOFF",
                relation="rooted return to the named woody subject",
                intended_effect="Orris depth resolves into a recognizable Cypress-centered drydown rather than an unrelated iris base.",
                failure_mode="The drydown is generic iris, opaque amberwood, or detached powder.",
                evidence_refs=(
                    "comparison://cyp-02/orris-cypress-return/v1",
                    "doi:10.1016/j.foodchem.2021.129483",
                ),
            ),
        ),
        # Material selection is evaluated by the current-inventory atlas in the
        # same harmonic request.  Keeping compiler hypotheses empty prevents an
        # ExactStockRef from being fabricated at this target/ideal stage.
        material_hypotheses=(),
        delta_candidates=(),
        no_change_reason=(
            "The relational target is structurally closed at architecture level; "
            "material ratios and omissions begin only after a formula line exists."
        ),
        evidence_refs=(
            f"cypress-heart-frontier-sha256:{frontier_result.record_sha256}",
            "target://cyp-02/brief/v1",
            "protocol://cyp-02/constant-total-controls/v1",
        ),
        component_count_used_as_complexity=False,
        predicted_oav_used_as_perception=False,
        composition_score_used_as_hedonic=False,
    )


def _withheld_report(
    module_id: str,
    blocker: str,
    next_action: str,
) -> HarmonicModuleReportV1:
    payload = {
        "module_id": module_id,
        "state": HarmonicModuleState.WITHHELD.value,
        "blocker": blocker,
        "next_action": next_action,
    }
    return HarmonicModuleReportV1(
        module_id=module_id,
        module_sha256=sha256_hex(canonical_json_bytes(payload)),
        state=HarmonicModuleState.WITHHELD,
        assertions=(),
        blockers=(blocker,),
        next_action=next_action,
        authority_flags=(),
    )


def _temporal_report(result: object | None) -> HarmonicModuleReportV1:
    if result is None:
        return _withheld_report(
            "temporal-ledger",
            "NO_BLINDED_TEMPORAL_OBSERVATIONS",
            "collect complete blinded target-fidelity, depth, richness, and transition cells over the frozen schedule",
        )
    return report_from_temporal_evidence(result)


def _preference_report(result: object | None) -> HarmonicModuleReportV1:
    if result is None:
        return _withheld_report(
            "hedonic-preference",
            "NO_SCOPED_BLINDED_PREFERENCE_DATA",
            "fit separate target-fidelity, depth, richness, and liking criteria only after complete order-balanced comparisons",
        )
    return report_from_preference(result)


@dataclass(frozen=True, slots=True)
class CypressHarmonicProgramResultV1:
    """Complete provenance-bearing computational-design receipt."""

    frontier_request: CypressHeartFrontierRequestV1
    frontier_result: CypressHeartFrontierResultV1
    depth_profile: DepthArchitectureProfileV1
    depth_evaluation: DepthEvaluationResultV1
    architecture_request: ArchitectureCompileRequest
    architecture_result: ArchitectureCompileResult
    delta_result: ArchitecturalDeltaResult
    module_reports: tuple[HarmonicModuleReportV1, ...]
    synthesis_request: HarmonicSynthesisRequestV1
    synthesis_result: HarmonicSynthesisResultV1
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    compounding_authorized: bool = field(default=False, init=False)
    purchase_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    hedonic_authority: bool = field(default=False, init=False)
    similarity_authority: bool = field(default=False, init=False)
    performance_authority: bool = field(default=False, init=False)
    safety_authority: bool = field(default=False, init=False)
    stability_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cypress_harmonic_program_result_v1",
            "frontier_request": self.frontier_request.as_dict(),
            "frontier_result": self.frontier_result.as_dict(),
            "depth_profile": self.depth_profile.as_dict(),
            "depth_evaluation": self.depth_evaluation.as_dict(),
            "architecture_request": self.architecture_request.as_dict(),
            "architecture_result": {
                "state": self.architecture_result.state.value,
                "target_lock_sha256": self.architecture_result.target_lock_sha256,
                "compilation_sha256": self.architecture_result.compilation_sha256,
                "primary_strategy": self.architecture_result.primary_strategy.value,
                "secondary_strategies": [
                    item.value for item in self.architecture_result.secondary_strategies
                ],
                "blockers": list(self.architecture_result.blockers),
                "current_build_blockers": list(
                    self.architecture_result.current_build_blockers
                ),
                "claim_ceiling": self.architecture_result.claim_ceiling,
                "authority_flags": dict(self.architecture_result.authority_flags),
            },
            "delta_result": {
                "state": self.delta_result.state.value,
                "formula_lineage_sha256": self.delta_result.formula_lineage_sha256,
                "inventory_workbook_sha256": self.delta_result.inventory_workbook_sha256,
                "inventory_source_row_count": self.delta_result.inventory_source_row_count,
                "blockers": list(self.delta_result.blockers),
                "next_comparison": self.delta_result.next_comparison,
            },
            "module_reports": [item.as_dict() for item in self.module_reports],
            "synthesis_request": self.synthesis_request.as_dict(),
            "synthesis_result": self.synthesis_result.as_dict(),
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "compounding_authorized": self.compounding_authorized,
            "purchase_authority": self.purchase_authority,
            "sensory_authority": self.sensory_authority,
            "hedonic_authority": self.hedonic_authority,
            "similarity_authority": self.similarity_authority,
            "performance_authority": self.performance_authority,
            "safety_authority": self.safety_authority,
            "stability_authority": self.stability_authority,
            "release_authority": self.release_authority,
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


def build_default_cypress_harmonic_program(
    *,
    atlas: MaterialCapabilityAtlas | None = None,
    temporal_evidence: object | None = None,
    preference_result: object | None = None,
) -> CypressHarmonicProgramResultV1:
    """Run the complete CYP-02 computational architecture program."""

    capability_atlas = atlas or build_material_capability_atlas()
    frontier_request = build_default_cypress_heart_frontier_request(capability_atlas)
    frontier_result = evaluate_cypress_heart_frontier(
        frontier_request,
        atlas=capability_atlas,
    )
    selected = frontier_result.selected_candidate
    if (
        frontier_result.state is not CypressHeartFrontierState.THEORY_SELECTED
        or selected is None
    ):
        raise ValueError(
            "default Cypress program requires a unique inventory-eligible heart frontier"
        )

    target = frontier_result.target
    depth_profile = build_bounded_reference_depth_profile(
        profile_id="CYP02_MAGNOLIA_ORRIS_DEPTH_V1",
        target_identity=target.target_identity,
        family=PerfumeFamily.WOODY,
        emotional_tone=(
            "polished aromatic-green tension relieved by petal light and grounded by "
            "cool intimate rhizome shadow"
        ),
        realism_or_abstraction_target=(
            "perfumistic revelation of high-quality French Cypress EO rather than "
            "literal tree, forest, spa, or aromatherapy realism"
        ),
        forbidden_drift=target.forbidden_drift,
        ideal_formula_ref=target.ideal_formula_ref,
        current_inventory_build_ref=target.current_inventory_build_ref,
        construction_row_count=0,
        temporal_windows=("0_min", "5_min", "30_min", "2_hour", "4_hour"),
        source_refs=(
            f"cypress-frontier-sha256:{frontier_result.record_sha256}",
            "design://cyp-02/magnolia-orris-depth/v1",
        ),
        claim_ceiling=target.claim_ceiling,
    )
    depth_evaluation = evaluate_depth_profile(depth_profile)

    architecture_request = _build_architecture_request(frontier_result)
    architecture_result = compile_architecture(
        architecture_request,
        _AtlasCompilerSnapshot(capability_atlas),
    )
    if architecture_result.delta_result is None:
        raise RuntimeError("architecture compiler did not return an Architectural Delta")
    delta_result = architecture_result.delta_result

    selected_material_names = tuple(
        intent.material_name for intent in selected.material_intents
    )
    module_reports = (
        report_from_material_atlas(
            capability_atlas,
            material_names=selected_material_names,
        ),
        report_from_cypress_heart_frontier(frontier_result),
        report_from_family_depth(depth_profile, depth_evaluation),
        report_from_architecture_compiler(architecture_result),
        report_from_architectural_delta(delta_result),
        _temporal_report(temporal_evidence),
        _preference_report(preference_result),
    )

    relation_modules = (
        "cypress-heart-frontier",
        "family-depth",
        "architecture-compiler",
    )
    relations = (
        HarmonicRelationV1(
            relation_id="cyp02_cypress_to_magnolia_relief",
            source_node="role.cypress_subject",
            target_node="role.magnolia_petal_light",
            relation_kind="TENSION_RELIEF",
            target_link=(
                "Magnolia opens petal-light around Cypress while Cypress remains the "
                "sole named subject and continuous identity axis."
            ),
            omission_loss="Cypress remains severe, planar, and aromatherapy-like.",
            failure_mode="Magnolia or floral diffusers become a generic clean-floral subject.",
            temporal_windows=("OPENING", "HEART", "LATE_HEART"),
            probe_ref="comparison://cyp-02/cypress-magnolia-omission/v1",
            module_ids=relation_modules,
        ),
        HarmonicRelationV1(
            relation_id="cyp02_magnolia_to_orris_depth",
            source_node="role.magnolia_petal_light",
            target_node="role.orris_rhizome_shadow",
            relation_kind="CHIAROSCURO_VERTICAL_DEPTH",
            target_link=(
                "Cool rhizome shadow makes the petal-light register feel elevated and "
                "dimensional without turning Orris into the perfume's subject."
            ),
            omission_loss="The heart has floral light but no lower tactile depth.",
            failure_mode="The relation collapses into cosmetic powder or generic woody iris.",
            temporal_windows=("HEART", "LATE_HEART", "DRYDOWN"),
            probe_ref="comparison://cyp-02/magnolia-orris-factorial/v1",
            module_ids=relation_modules,
        ),
        HarmonicRelationV1(
            relation_id="cyp02_orris_to_cypress_return",
            source_node="role.orris_rhizome_shadow",
            target_node="role.cypress_subject",
            relation_kind="ROOTED_RETURN",
            target_link=(
                "The rhizome shadow resolves back into the Cypress-centered drydown so "
                "the perfume remains one architecture rather than an iris base."
            ),
            omission_loss="The late architecture loses its rooted return and becomes detached.",
            failure_mode="Orris, powder, or opaque wood replaces Cypress in the drydown.",
            temporal_windows=("LATE_HEART", "DRYDOWN"),
            probe_ref="comparison://cyp-02/orris-cypress-return/v1",
            module_ids=relation_modules,
        ),
    )
    required_module_ids = tuple(report.module_id for report in module_reports)
    synthesis_request = HarmonicSynthesisRequestV1(
        target=target,
        required_module_ids=required_module_ids,
        design_gate_module_ids=(
            "material-capability-atlas",
            "cypress-heart-frontier",
            "family-depth",
            "architecture-compiler",
            "architectural-delta",
        ),
        module_reports=module_reports,
        relations=relations,
        material_intents=selected.material_intents,
        no_change_reason=(
            "The Cypress-native architecture is closed for formula drafting; no extra "
            "material is rewarded without a target-linked delta and controlled arm."
        ),
    )
    synthesis_result = synthesize_harmonically(
        synthesis_request,
        atlas=capability_atlas,
    )

    return CypressHarmonicProgramResultV1(
        frontier_request=frontier_request,
        frontier_result=frontier_result,
        depth_profile=depth_profile,
        depth_evaluation=depth_evaluation,
        architecture_request=architecture_request,
        architecture_result=architecture_result,
        delta_result=delta_result,
        module_reports=module_reports,
        synthesis_request=synthesis_request,
        synthesis_result=synthesis_result,
    )


__all__ = [
    "CypressHarmonicProgramResultV1",
    "build_default_cypress_harmonic_program",
]
