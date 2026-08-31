from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from engine.perception.floral_depth import (
    FloralArchitectureContractV1,
    FloralCouplingContractV1,
    FloralDepthStrategy,
    FloralDesignRequestV1,
    FloralDesignState,
    FloralDosePreparationV1,
    FloralFacetClass,
    FloralFacetV1,
    FloralIdentityContractV1,
    FloralInterfaceEdgeV1,
    FloralMaterialClass,
    FloralMaterialDoseV1,
    FloralMaterialRoleV1,
    FloralScope,
    FloralSourceClass,
    FloralSubjectAnatomyV1,
    FloralSubjectRole,
    FloralSubjectV1,
    FloralTemporalBand,
    FloralTemporalContourV1,
    FloralTemporalWindowV1,
    FloralTrainingTrialV1,
    InventoryBindingState,
    MissingChemicalImpactV1,
    NaturalOAVState,
    TrainingDomain,
    WoodTextureContractV1,
    evaluate_floral_design,
)
from scripts.verify_formula_workflow import parse_formula_markdown

SOURCE_HASH = "a" * 64
WINDOWS = ("OPENING", "5_MIN", "30_MIN", "2_HOUR", "4_HOUR", "8_HOUR")
ROOT = Path(__file__).resolve().parents[1]
WHITE_FIRE_FIXTURE = (
    ROOT / "tests/fixtures/floral_depth/white_fire_reliquary_v1.json"
)
WHITE_FIRE_CURRENT = ROOT / "formulas/White_Fire_Reliquary_30mL_Parfum.md"


def _subject(subject_id: str, role: FloralSubjectRole) -> FloralSubjectV1:
    return FloralSubjectV1(subject_id, subject_id.replace("_", " ").title(), role)


def _dose(
    material_id: str,
    material: str,
    *,
    source_class: FloralSourceClass = FloralSourceClass.KNOWN_CHEMICAL,
    owner: str = "white_champi",
    raw: str = "100",
    fraction: str = "1",
    active: str = "100",
    ppm: str = "100000",
    exact_stock_ref: str | None = "inventory.txt#owned",
    preparation_id: str | None = None,
    natural_oav_state: NaturalOAVState = NaturalOAVState.NOT_APPLICABLE,
    is_musk: bool = False,
) -> FloralMaterialDoseV1:
    return FloralMaterialDoseV1(
        material_id=material_id,
        material=material,
        source_class=source_class,
        subject_owner=owner,
        target_function=f"{material_id} target function",
        raw_stock_ul=Decimal(raw),
        stock_fraction=Decimal(fraction),
        active_ul=Decimal(active),
        active_ppm=Decimal(ppm),
        inventory_state=InventoryBindingState.OWNED,
        exact_stock_ref=exact_stock_ref,
        preparation_id=preparation_id,
        natural_oav_state=natural_oav_state,
        is_musk=is_musk,
    )


def _architecture(request: FloralDesignRequestV1) -> FloralArchitectureContractV1:
    subject_ids = {item.subject_id for item in request.identity.floral_subjects}
    subjects = tuple(
        FloralSubjectAnatomyV1(
            subject_id=subject.subject_id,
            required_facet_classes=(
                FloralFacetClass.PETAL,
                FloralFacetClass.FLESH,
                FloralFacetClass.DIFFUSION,
                FloralFacetClass.SHADOW,
            ),
            required_material_ids=(
                next(
                    material.material_id
                    for material in request.current_build_materials
                    if material.subject_owner == subject.subject_id
                ),
            ),
            omission_trial_ids=("trial_floral_coupling",),
        )
        for subject in request.identity.floral_subjects
    )
    roles = tuple(
        FloralMaterialRoleV1(
            material_id=material.material_id,
            module_id=(
                material.subject_owner
                if material.subject_owner in subject_ids
                else "wood_reliquary"
            ),
            primary_role_id=f"role_{material.material_id}",
            material_class=(
                FloralMaterialClass.WOOD
                if material.subject_owner == "WOOD"
                else FloralMaterialClass.MUSK
                if material.is_musk
                else FloralMaterialClass.FLORAL
            ),
            temporal_band=(
                FloralTemporalBand.DRYDOWN
                if material.subject_owner == "WOOD"
                else FloralTemporalBand.HEART
            ),
            texture_axis=(
                "dry mineral grain"
                if material.material_id == "javanol"
                else "creamy yielding grain"
                if material.material_id == "ebanol"
                else "petal flesh continuity"
            ),
            interface_ids=(
                (f"edge_{material.subject_owner}_wood",)
                if material.subject_owner in subject_ids
                else ()
            ),
            ablation_trial_id=(
                "trial_wood_texture"
                if material.subject_owner == "WOOD"
                else "trial_floral_coupling"
            ),
        )
        for material in request.current_build_materials
    )
    interfaces = tuple(
        FloralInterfaceEdgeV1(
            interface_id=f"edge_{subject.subject_id}_wood",
            source_module_id=subject.subject_id,
            target_module_id="wood_reliquary",
            bridge_material_ids=(
                next(
                    material.material_id
                    for material in request.current_build_materials
                    if material.subject_owner == subject.subject_id
                ),
            ),
            failure_mode="Flower and reliquary split into unrelated planes.",
            controlled_trial_id="trial_floral_coupling",
        )
        for subject in request.identity.floral_subjects
    )
    return FloralArchitectureContractV1(
        contract_id="white_fire_target_linked_resolution",
        benchmark_reference="DHP_DEPTH_TOPOLOGY_TRANSLATED_TO_FLOWERS_NOT_SENSORY_PARITY",
        benchmark_scope="Explicit target-linked role resolution; no count or liking authority.",
        subject_anatomies=subjects,
        material_roles=roles,
        interface_edges=interfaces,
        required_module_ids=tuple(
            item.subject_id for item in request.identity.floral_subjects
        )
        + ("wood_reliquary",),
        required_wood_role_ids=("role_javanol", "role_ebanol"),
        required_floral_temporal_bands=(FloralTemporalBand.HEART,),
        required_wood_temporal_bands=(FloralTemporalBand.DRYDOWN,),
        required_wood_texture_axes=("dry mineral grain", "creamy yielding grain"),
        ablation_trial_ids=("trial_floral_coupling", "trial_wood_texture"),
        perturbation_trial_ids=("trial_wood_texture",),
        anti_collapse_trial_ids=("trial_floral_coupling",),
        rationale="Resolve named flower anatomy, wood texture, interfaces, and survival tests independently.",
    )


def _request() -> FloralDesignRequestV1:
    identity = FloralIdentityContractV1(
        target_identity="White Fire Reliquary",
        emotional_tone="Lucid ceremonial calm opening into narcotic intimacy.",
        floral_subjects=(
            _subject("white_champi", FloralSubjectRole.LEAD),
            _subject("jasmine", FloralSubjectRole.CO_LEAD),
            _subject("tuberose", FloralSubjectRole.CO_LEAD),
            _subject("orange_blossom", FloralSubjectRole.CO_LEAD),
        ),
        floral_scope=FloralScope.BOUQUET,
        realism_target="Four legible flowers behaving as one spatial organism.",
        ideal_formula_ref="formula:white-fire:ideal:v1",
        current_inventory_build_ref="formula:white-fire:current:v1",
        allowed_source_classes=(
            FloralSourceClass.ESSENTIAL_OIL,
            FloralSourceClass.ABSOLUTE,
            FloralSourceClass.KNOWN_CHEMICAL,
        ),
        forbidden_drift=("generic amber", "detergent musk", "opaque floral base"),
        evidence_refs=(SOURCE_HASH,),
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )
    facet_specs = tuple(
        (subject_id, facet_class)
        for subject_id in (
            "white_champi",
            "jasmine",
            "tuberose",
            "orange_blossom",
        )
        for facet_class in (
            FloralFacetClass.PETAL,
            FloralFacetClass.FLESH,
            FloralFacetClass.DIFFUSION,
            FloralFacetClass.SHADOW,
        )
    )
    facets = tuple(
        FloralFacetV1(
            facet_id=f"{subject_id}_{facet_class.value.casefold()}",
            facet_class=facet_class,
            target_function=f"{subject_id} {facet_class.value.casefold()} recognizer.",
            subject_owner=subject_id,
            omission_loss=f"The {subject_id} subject loses its {facet_class.value.casefold()} anatomy.",
            failure_mode=f"The {subject_id} subject collapses toward generic white floral.",
            required_temporal_windows=("OPENING", "30_MIN", "2_HOUR"),
            evidence_refs=(SOURCE_HASH,),
            ideal_materials=(subject_id,),
            current_build_bindings=(subject_id,),
            controlled_comparison_ref="trial_floral_coupling",
        )
        for subject_id, facet_class in facet_specs
    )
    coupling = FloralCouplingContractV1(
        coupling_id="white_fire_reciprocal_coupling",
        facet_ids=("white_champi_petal", "jasmine_flesh"),
        shared_recognizers=("linalool", "benzyl acetate", "methyl benzoate"),
        relationship_edges=("cool_shell CONTRASTS warm_flesh", "warm_flesh RECURS_IN drydown"),
        bridge="Hedione/benzoate/jasmonate/salicylate continuity binds both poles.",
        collision_risks=("jasmine takeover", "tuberose wax overload", "neroli cologne drift"),
        controlled_arms=("CARRIER_MATCHED_BRIDGE_ABLATION", "FULL_FLORAL_COUPLING"),
        identity_retention_endpoints=("WHITE_CHAMPI_PRESENT", "FOUR_FLOWER_HIERARCHY"),
    )
    contour = FloralTemporalContourV1(
        tuple(
            FloralTemporalWindowV1(
                window_id,
                ("WHITE_CHAMPI_PRESENT", "FOUR_FLOWER_HIERARCHY"),
                f"Target state hypothesis at {window_id}.",
            )
            for window_id in WINDOWS
        )
    )
    magnolia = _dose(
        "magnolia",
        "Magnolia EO",
        source_class=FloralSourceClass.ESSENTIAL_OIL,
        raw="900",
        fraction="0.1",
        active="90",
        ppm="12500",
        exact_stock_ref=None,
        preparation_id="prep_magnolia_10",
        natural_oav_state=NaturalOAVState.HOLD_LOT_OR_MODEL,
    )
    jasmine = _dose(
        "jasmine",
        "Jasmine Absolute",
        source_class=FloralSourceClass.ABSOLUTE,
        owner="jasmine",
        raw="100",
        fraction="0.1",
        active="10",
        ppm="1388.888889",
        natural_oav_state=NaturalOAVState.COMPOSITE_COVERED,
    )
    tuberose = _dose(
        "tuberose",
        "Tuberose Absolute",
        source_class=FloralSourceClass.ABSOLUTE,
        owner="tuberose",
        raw="100",
        fraction="0.1",
        active="10",
        ppm="1388.888889",
        natural_oav_state=NaturalOAVState.COMPOSITE_COVERED,
    )
    neroli = _dose(
        "neroli",
        "Neroli EO",
        source_class=FloralSourceClass.ESSENTIAL_OIL,
        owner="orange_blossom",
        raw="100",
        fraction="0.1",
        active="10",
        ppm="1388.888889",
        natural_oav_state=NaturalOAVState.COMPOSITE_COVERED,
    )
    javanol = _dose("javanol", "Javanol", owner="WOOD", raw="120", active="120", ppm="16666.6667")
    ebanol = _dose("ebanol", "Ebanol", owner="WOOD", raw="180", active="180", ppm="25000")
    ambrettolide = _dose(
        "ambrettolide",
        "Ambrettolide",
        owner="SHARED_FLORAL_SKIN",
        raw="360",
        fraction="0.1",
        active="36",
        ppm="5000",
        is_musk=True,
    )
    current = (magnolia, jasmine, tuberose, neroli, javanol, ebanol, ambrettolide)
    preparation = FloralDosePreparationV1(
        preparation_id="prep_magnolia_10",
        source_material="Magnolia EO",
        source_stock_fraction=Decimal("1"),
        concentration_basis="v/v",
        carrier="DPG",
        source_ul=Decimal("200"),
        carrier_ul=Decimal("1800"),
        prepared_total_ul=Decimal("2000"),
        final_stock_fraction=Decimal("0.1"),
        delivered_ul=Decimal("900"),
        delivered_active_ul=Decimal("90"),
        instruction="Combine 200 uL Magnolia EO with 1800 uL DPG and mix uniformly.",
    )
    floral_trial = FloralTrainingTrialV1(
        trial_id="trial_floral_coupling",
        domain=TrainingDomain.FLORAL,
        stage_order=1,
        changed_factor="WHITE_FIRE_FLORAL_COUPLING_BRIDGE",
        intervention_material_ids=(
            "magnolia",
            "jasmine",
            "tuberose",
            "neroli",
            "ambrettolide",
        ),
        controlled_arms=("CARRIER_MATCHED_BRIDGE_ABLATION", "FULL_FLORAL_COUPLING"),
        primary_endpoints=("TARGET_IDENTITY", "FLORAL_DEPTH", "LIKING"),
        failure_endpoints=("FLOWER_BLUR", "GENERIC_WHITE_FLORAL_DRIFT"),
        constant_constraints=("CONSTANT_TOTAL_RAW_VOLUME", "CONSTANT_TOTAL_ACTIVE_MASS"),
        prerequisite_trial_ids=(),
        accept_rule="Accept only for repeatable floral depth and liking gain with identity retained.",
        reject_rule="Reject for no gain, flower blur, or target drift.",
        blinding_rule="Assign opaque codes after formula hashes are frozen.",
        order_rule="Balance first presentation and record predecessor.",
        time_windows=WINDOWS,
        evidence_refs=(SOURCE_HASH,),
    )
    wood_trial = FloralTrainingTrialV1(
        trial_id="trial_wood_texture",
        domain=TrainingDomain.WOOD,
        stage_order=2,
        changed_factor="JAVANOL_X_EBANOL_TEXTURE_INTERACTION",
        intervention_material_ids=("javanol", "ebanol"),
        controlled_arms=("W00", "WJ", "WE", "WJE"),
        primary_endpoints=("WOOD_TEXTURE", "FRONT_CENTER_REAR_SEPARATION", "LIKING"),
        failure_endpoints=("WOOD_TAKEOVER", "FLORAL_IDENTITY_LOSS"),
        constant_constraints=("CONSTANT_TOTAL_RAW_VOLUME", "ISO_E_SUPER_FIXED"),
        prerequisite_trial_ids=("trial_floral_coupling",),
        accept_rule="Accept one wood state only if texture and spatial depth improve without takeover.",
        reject_rule="Reject for no interaction, wood takeover, or floral loss.",
        blinding_rule="Assign opaque codes after formula hashes are frozen.",
        order_rule="Use a balanced four-arm order across repeats.",
        time_windows=("30_MIN", "2_HOUR", "4_HOUR", "8_HOUR"),
        evidence_refs=(SOURCE_HASH,),
    )
    wood = WoodTextureContractV1(
        contract_id="white_fire_wood_dyad",
        material_ids=("javanol", "ebanol"),
        texture_axis="dry mineral precision versus creamy yielding sandalwood",
        floral_echo="Javanol echoes the cool shell; Ebanol echoes warm floral flesh.",
        omission_loss="The rear plane loses its controlled tactile counterpoint.",
        failure_mode="Sandalwood becomes a separate perfume or obscures the flowers.",
        fixed_constraints=("ISO_E_SUPER_FIXED", "FLORAL_CORE_FIXED"),
        controlled_arms=("W00", "WJ", "WE", "WJE"),
        prerequisite_trial_ids=("trial_floral_coupling",),
    )
    request = FloralDesignRequestV1(
        identity=identity,
        strategy=FloralDepthStrategy.AUTOGENOUS_POLARITY,
        facets=facets,
        coupling=coupling,
        temporal_contour=contour,
        ideal_materials=current,
        current_build_materials=current,
        preparations=(preparation,),
        missing_chemical_impacts=(
            MissingChemicalImpactV1(
                material="White Champi lot COA/GC and safety documents",
                target_function="Quantitative natural identity and safety authority.",
                impact="Critical for OAV, safety, and release; not for paper design.",
                current_handling="Keep whole natural identity and hold quantitative OAV.",
                decision="Obtain documentation before physical skin work.",
            ),
        ),
        wood_texture_contracts=(wood,),
        training_trials=(floral_trial, wood_trial),
        passed_trial_ids=(),
        no_change_reason="No change only if no target-linked deficiency remains.",
    )
    return replace(request, architecture_contract=_architecture(request))


def test_valid_design_selects_exactly_one_flower_first_trial() -> None:
    result = evaluate_floral_design(_request())
    assert result.state is FloralDesignState.READY
    assert result.selected_trial is not None
    assert result.selected_trial.trial_id == "trial_floral_coupling"
    assert result.deferred_trial_ids == ("trial_wood_texture",)
    assert result.quantitative_oav_holds == ("Magnolia EO",)
    assert len(result.request_sha256) == 64
    assert result.record_sha256 == result.record_sha256
    assert not any(
        (
            result.empirical_authority,
            result.formula_mutation_authorized,
            result.physical_execution_authorized,
            result.purchase_authority,
            result.sensory_authority,
            result.safety_authority,
            result.release_authority,
        )
    )


def test_non_simple_floral_requires_architecture_contract() -> None:
    result = evaluate_floral_design(replace(_request(), architecture_contract=None))
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_ARCHITECTURE_CONTRACT_MISSING" in result.reason_codes


def test_each_named_flower_requires_complete_declared_anatomy() -> None:
    request = _request()
    facets = tuple(
        facet
        for facet in request.facets
        if not (
            facet.subject_owner == "tuberose"
            and facet.facet_class is FloralFacetClass.SHADOW
        )
    )
    result = evaluate_floral_design(replace(request, facets=facets))
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_SUBJECT_ANATOMY" in result.reason_codes


def test_benchmark_wood_roles_cannot_be_compressed_to_two_planes() -> None:
    request = _request()
    contract = request.architecture_contract
    assert contract is not None
    declared_wood_roles = contract.required_wood_role_ids + tuple(
        f"white_fire_wood_role_{index:02d}" for index in range(3, 31)
    )
    result = evaluate_floral_design(
        replace(
            request,
            architecture_contract=replace(
                contract,
                required_wood_role_ids=declared_wood_roles,
            ),
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_ROLE_COVERAGE" in result.reason_codes


def test_material_count_cannot_be_padded_with_duplicate_primary_roles() -> None:
    request = _request()
    contract = request.architecture_contract
    assert contract is not None
    roles = list(contract.material_roles)
    roles[1] = replace(roles[1], primary_role_id=roles[0].primary_role_id)
    result = evaluate_floral_design(
        replace(
            request,
            architecture_contract=replace(contract, material_roles=tuple(roles)),
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_ROLE_COVERAGE" in result.reason_codes


def test_flower_wood_interfaces_must_be_material_and_trial_bound() -> None:
    request = _request()
    contract = request.architecture_contract
    assert contract is not None
    result = evaluate_floral_design(
        replace(
            request,
            architecture_contract=replace(
                contract,
                interface_edges=contract.interface_edges[:-1],
            ),
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_INTERFACE_CLOSURE" in result.reason_codes


def test_wood_temporal_and_texture_commitments_are_not_rhetorical() -> None:
    request = _request()
    contract = request.architecture_contract
    assert contract is not None
    result = evaluate_floral_design(
        replace(
            request,
            architecture_contract=replace(
                contract,
                required_wood_temporal_bands=(
                    FloralTemporalBand.DRYDOWN,
                    FloralTemporalBand.PERSISTENT,
                ),
                required_wood_texture_axes=contract.required_wood_texture_axes
                + ("polished resin shadow",),
            ),
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_TEMPORAL_RESOLUTION" in result.reason_codes
    assert "HOLD_TEXTURE_RESOLUTION" in result.reason_codes


def test_support_only_florals_are_not_applicable() -> None:
    request = _request()
    identity = replace(
        request.identity,
        floral_subjects=tuple(
            replace(subject, role=FloralSubjectRole.SUPPORT)
            for subject in request.identity.floral_subjects
        ),
    )
    result = evaluate_floral_design(replace(request, identity=identity))
    assert result.state is FloralDesignState.NOT_APPLICABLE
    assert result.reason_codes == ("FLORAL_NOT_PRIMARY",)


def test_target_and_build_references_cannot_collapse() -> None:
    request = _request()
    identity = replace(
        request.identity,
        current_inventory_build_ref=request.identity.ideal_formula_ref,
    )
    result = evaluate_floral_design(replace(request, identity=identity))
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_TARGET_BUILD_COLLAPSE" in result.reason_codes


def test_source_policy_rejects_opaque_or_fragrance_oil_materials() -> None:
    request = _request()
    opaque = replace(
        request.current_build_materials[0],
        source_class=FloralSourceClass.OPAQUE_BASE,
        material="Tuberlia Base",
    )
    result = evaluate_floral_design(
        replace(request, current_build_materials=(opaque, *request.current_build_materials[1:]))
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_SOURCE_CLASS" in result.reason_codes


def test_autogenous_polarity_requires_explicit_reciprocal_coupling() -> None:
    result = evaluate_floral_design(replace(_request(), coupling=None))
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_STRATEGY_UNSUPPORTED" in result.reason_codes


def test_woods_cannot_be_presented_as_the_flower_depth_mechanism() -> None:
    request = _request()
    result = evaluate_floral_design(
        replace(
            request,
            strategy=FloralDepthStrategy.ATMOSPHERIC_RELIEF,
            coupling=None,
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_EXTERNALIZED_DEPTH" in result.reason_codes


def test_decorative_facet_without_omission_loss_or_control_is_held() -> None:
    request = _request()
    decorative = replace(
        request.facets[0],
        omission_loss="",
        controlled_comparison_ref="",
    )
    result = evaluate_floral_design(replace(request, facets=(decorative, request.facets[1])))
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_DECORATIVE_FACET" in result.reason_codes


def test_natural_oav_hold_preserves_whole_material_identity() -> None:
    result = evaluate_floral_design(_request())
    assert result.state is FloralDesignState.READY
    assert result.quantitative_oav_holds == ("Magnolia EO",)
    assert any(item.material == "Magnolia EO" for item in result.current_build_materials)


def test_sub_ten_microlitre_raw_delivery_is_held() -> None:
    request = _request()
    tiny = replace(
        request.current_build_materials[1],
        raw_stock_ul=Decimal("5"),
        active_ul=Decimal("5"),
        active_ppm=Decimal("694.4444"),
    )
    result = evaluate_floral_design(
        replace(request, current_build_materials=(request.current_build_materials[0], tiny, *request.current_build_materials[2:]))
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_SUB_10_UL" in result.reason_codes


def test_complete_serial_preparation_is_measurable_and_accepted() -> None:
    request = _request()
    serial = FloralDosePreparationV1(
        preparation_id="prep_trace_01",
        source_material="Methyl Anthranilate 1% stock",
        source_stock_fraction=Decimal("0.01"),
        concentration_basis="v/v",
        carrier="DPG",
        source_ul=Decimal("100"),
        carrier_ul=Decimal("900"),
        prepared_total_ul=Decimal("1000"),
        final_stock_fraction=Decimal("0.001"),
        delivered_ul=Decimal("50"),
        delivered_active_ul=Decimal("0.05"),
        instruction="Combine 100 uL of 1% stock with 900 uL DPG and mix uniformly.",
    )
    trace = _dose(
        "methyl_anthranilate",
        "Methyl Anthranilate",
        raw="50",
        fraction="0.001",
        active="0.05",
        ppm="6.9444",
        exact_stock_ref=None,
        preparation_id="prep_trace_01",
    )
    contract = request.architecture_contract
    assert contract is not None
    trace_role = FloralMaterialRoleV1(
        material_id="methyl_anthranilate",
        module_id="white_champi",
        primary_role_id="role_methyl_anthranilate",
        material_class=FloralMaterialClass.BRIDGE,
        temporal_band=FloralTemporalBand.HEART,
        texture_axis="orange-flower nectar trace",
        interface_ids=("edge_white_champi_wood",),
        ablation_trial_id="trial_floral_coupling",
    )
    floral_trial = replace(
        request.training_trials[0],
        intervention_material_ids=request.training_trials[0].intervention_material_ids
        + ("methyl_anthranilate",),
    )
    result = evaluate_floral_design(
        replace(
            request,
            current_build_materials=(*request.current_build_materials, trace),
            ideal_materials=(*request.ideal_materials, trace),
            preparations=(*request.preparations, serial),
            training_trials=(floral_trial, *request.training_trials[1:]),
            architecture_contract=replace(
                contract,
                material_roles=(*contract.material_roles, trace_role),
            ),
        )
    )
    assert result.state is FloralDesignState.READY
    assert "HOLD_SUB_10_UL" not in result.reason_codes


def test_multiple_musks_require_an_isolated_pairwise_trial() -> None:
    request = _request()
    second = _dose(
        "ethylene_brassylate",
        "Ethylene Brassylate",
        owner="SHARED_FLORAL_SKIN",
        raw="100",
        active="100",
        ppm="13888.8889",
        is_musk=True,
    )
    result = evaluate_floral_design(
        replace(
            request,
            ideal_materials=(*request.ideal_materials, second),
            current_build_materials=(*request.current_build_materials, second),
        )
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_MUSK_REDUNDANCY" in result.reason_codes


def test_exception_only_musks_are_rejected_without_exception_contract() -> None:
    request = _request()
    exception = replace(
        request.current_build_materials[-1],
        material="Musk Ketone",
        material_id="musk_ketone",
    )
    result = evaluate_floral_design(
        replace(request, current_build_materials=(*request.current_build_materials[:-1], exception))
    )
    assert result.state is FloralDesignState.HOLD
    assert "HOLD_MUSK_EXCEPTION" in result.reason_codes


def test_precise_simplicity_is_a_first_class_no_change_result() -> None:
    request = _request()
    result = evaluate_floral_design(
        replace(
            request,
            strategy=FloralDepthStrategy.PRECISE_SIMPLICITY,
            coupling=None,
            wood_texture_contracts=(),
            training_trials=(),
        )
    )
    assert result.state is FloralDesignState.NO_CHANGE
    assert result.reason_codes == ("NO_TARGET_DEFICIENCY",)


def test_frozen_white_fire_parent_is_an_explicit_negative_regression_fixture() -> None:
    payload = json.loads(WHITE_FIRE_FIXTURE.read_text(encoding="utf-8"))
    formula = payload["formula"]
    materials = formula["materials"]

    assert payload["schema_version"] == "white_fire_reliquary_rejected_parent_v1"
    assert payload["architecture_state"] == "REJECTED_UNDERRESOLVED_PARENT"
    assert payload["superseded_by"] == "formulas/White_Fire_Reliquary_30mL_Parfum.md"
    assert len(payload["rejection_reasons"]) == 3
    assert payload["claim_ceiling"] == "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY"
    assert len(payload["floral_subjects"]) == 4
    assert {item["role"] for item in payload["floral_subjects"]} == {
        "LEAD",
        "CO_LEAD",
    }
    assert formula["ideal_and_current_composition_identical"] is True
    assert formula["target_and_build_authority_references_distinct"] is True
    assert payload["ideal_formula_ref"] != payload["current_inventory_build_ref"]
    assert len(materials) == 26
    assert sum(item["subject_owner"] == "WOOD" for item in materials) == 3
    assert sum(item["raw_ul"] for item in materials) == 7200.0
    assert all(item["raw_ul"] >= 10.0 for item in materials)
    assert sum(item["is_musk"] is True for item in materials if "is_musk" in item) == 1
    assert {item["source_class"] for item in materials} <= {
        "ESSENTIAL_OIL",
        "ABSOLUTE",
        "KNOWN_CHEMICAL",
    }
    for item in materials:
        assert item["active_ul"] == pytest.approx(
            item["raw_ul"] * item["stock_fraction"]
        )
        assert item["active_ppm"] == pytest.approx(
            item["active_ul"] / 7200.0 * 1_000_000.0,
            rel=1e-6,
            abs=1e-4,
        )

    preparations = {item["preparation_id"]: item for item in payload["preparations"]}
    for item in preparations.values():
        assert item["source_ul"] >= 10.0
        assert item["carrier_ul"] >= 10.0
        assert item["delivered_ul"] >= 10.0
        assert item["source_ul"] + item["carrier_ul"] == pytest.approx(
            item["prepared_total_ul"]
        )
        assert (
            item["source_stock_fraction"]
            * item["source_ul"]
            / item["prepared_total_ul"]
        ) == pytest.approx(item["final_stock_fraction"])
        assert item["final_stock_fraction"] * item["delivered_ul"] == pytest.approx(
            item["delivered_active_ul"]
        )

    trials = payload["training_trials"]
    assert trials[0]["domain"] == "FLORAL"
    assert trials[0]["arms"] == [
        "CARRIER_MATCHED_BRIDGE_ABLATION",
        "FULL_FLORAL_COUPLING",
    ]
    assert trials[1]["domain"] == "WOOD"
    assert trials[1]["arms"] == ["W00", "WJ", "WE", "WJE"]
    assert trials[1]["prerequisites"] == ["trial_floral_coupling:PASS"]
    assert payload["wood_texture_contract"]["fixed_spatial_scaffold"] == "Iso E Super"
    assert all(value is False for value in payload["authority"].values())

    for binding in payload["evidence_bindings"]:
        path = ROOT / binding["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]


def test_white_fire_current_case_closes_target_linked_geometry_and_dosing() -> None:
    text = WHITE_FIRE_CURRENT.read_text(encoding="utf-8")
    formulas = parse_formula_markdown(WHITE_FIRE_CURRENT)

    assert len(formulas) == 1
    formula = formulas[0]
    ingredients = formula["ingredients_ul"]
    dilutions = formula["dilutions"]
    assert len(ingredients) == 78
    assert sum(ingredients.values()) == pytest.approx(7200.0)
    assert all(raw_ul >= 10.0 for raw_ul in ingredients.values())
    assert ingredients["Ambrettolide"] == 330.0
    assert dilutions["Ambrettolide"] == pytest.approx(0.1)
    assert "Methyl Anthranilate" not in ingredients
    assert "Lemon FCF oil Sicilian" not in ingredients
    assert "Cedarwood Virginia" not in ingredients

    current_section = text.split(
        "## 4. CURRENT-INVENTORY BUILD — parser-visible formula", 1
    )[1].split("## 5. Missing-chemical and authority impact gate", 1)[0]
    numbered_roles = re.findall(
        r"^\|\s*(\d+)\s*\|.*?\|\s*(R\d{2})\b.*?\|\s*$",
        current_section,
        flags=re.MULTILINE,
    )
    assert [int(row) for row, _ in numbered_roles] == list(range(1, 79))
    # The parser-visible table is ordered by the user's physical storage
    # baskets, while role IDs retain the target-first architecture order.
    # Require a complete, unique role census without forcing those two
    # independent orderings to coincide.
    assert sorted(int(role[1:]) for _, role in numbered_roles) == list(range(1, 79))

    expected_modules = {
        "White Champi": (1, 8),
        "Jasmine": (9, 17),
        "Tuberose": (18, 25),
        "Orange blossom": (26, 32),
        "Shared living tissue": (33, 48),
        "Wood air / cream": (49, 54),
        "Wood pressure / warmth": (55, 63),
        "Natural wood grain / root": (64, 73),
        "Wood finish / skin": (74, 78),
    }
    architecture_section = text.split(
        "## 7. Architecture-resolution and anti-padding gate", 1
    )[1].split("## 8. OAV, stock-rebase, and temporal diagnostic policy", 1)[0]
    module_rows = re.findall(
        r"^\|\s*([^|]+?)\s*\|\s*R(\d{2})[–-]R(\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
        architecture_section,
        flags=re.MULTILINE,
    )
    observed_modules = {
        name.strip(): (int(start), int(end)) for name, start, end, *_ in module_rows
    }
    assert observed_modules == expected_modules
    covered_roles = [
        role
        for start, end in observed_modules.values()
        for role in range(start, end + 1)
    ]
    assert covered_roles == list(range(1, 79))
    wood_roles = [
        role
        for name, (start, end) in observed_modules.items()
        if name.startswith("Wood") or name == "Natural wood grain / root"
        for role in range(start, end + 1)
    ]
    assert wood_roles == list(range(49, 79))
    assert all(temporal.strip() for *_, temporal, _texture, _loss in module_rows)
    assert all(texture.strip() for *_, texture, _loss in module_rows)
    assert all("A" in loss for *_, loss in module_rows)
    assert "A high row count does not pass this gate" in architecture_section

    preparations = formula["stock_preparations"]
    assert set(preparations) == {
        "Magnolia EO",
        "Indole",
        "Methyl Salicylate",
        "Amyl Cinnamic Aldehyde (ACA)",
        "Aurantiol",
        "Damascenone",
        "Javanol",
        "Timberol",
        "Amberwood F",
        "Ambermax",
        "Norlimbanol Dextro",
        "Benzaldehyde",
        "Geraniol",
    }
    for material, preparation in preparations.items():
        assert preparation["source_ul"] >= 10.0, material
        assert preparation["carrier_ul"] >= 10.0, material
        assert preparation["formula_delivery_ul"] >= 10.0, material
        assert preparation["source_ul"] + preparation["carrier_ul"] == pytest.approx(
            preparation["prepared_total_ul"]
        )
        assert (
            preparation["source_fraction"]
            * preparation["source_ul"]
            / preparation["prepared_total_ul"]
        ) == pytest.approx(preparation["final_fraction"])

    preparation_ids = {}
    for material, stock_spec in formula["stock_specs"].items():
        match = re.search(r"prepare\s+(P\d+)", stock_spec["raw"], flags=re.I)
        if match:
            preparation_ids[match.group(1).upper()] = material
    assert set(preparation_ids) == {f"P{index}" for index in range(1, 14)}

    visible_preparations = {}
    preparation_section = text.split(
        "## 6. Required stock preparations; every source transfer ≥10 µL", 1
    )[1].split("## 7. Architecture-resolution and anti-padding gate", 1)[0]
    for line in preparation_section.splitlines():
        if not re.match(r"^\|\s*P\d+\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        delivered_match = re.fullmatch(r"([\d,]+(?:\.\d+)?)\s*µL", cells[3])
        active_match = re.fullmatch(r"([\d,]+(?:\.\d+)?)\s*µL", cells[4])
        assert delivered_match is not None, line
        assert active_match is not None, line
        visible_preparations[cells[0].upper()] = (
            float(delivered_match.group(1).replace(",", "")),
            float(active_match.group(1).replace(",", "")),
        )

    assert set(visible_preparations) == set(preparation_ids)
    for preparation_id, material in preparation_ids.items():
        preparation = preparations[material]
        visible_delivery, visible_active = visible_preparations[preparation_id]
        assert visible_delivery == pytest.approx(
            preparation["formula_delivery_ul"]
        ), material
        assert visible_active == pytest.approx(
            preparation["formula_delivery_ul"] * preparation["final_fraction"]
        ), material

    assert "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY" in text
    assert "NOT TESTED" in text
    assert re.search(r"constant[- ]total", text, flags=re.IGNORECASE)
