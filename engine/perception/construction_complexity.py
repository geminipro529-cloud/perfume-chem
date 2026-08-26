"""Evidence-labeled construction-complexity diagnostics for perfume formulas.

The profile intentionally has no overall score.  It keeps arithmetic structure,
modeled OAV/headspace distribution, temporal change, semantic partitions,
descriptor-space hypotheses, and unresolved sensory claims on separate axes.
This prevents component count or functional-group labels from being promoted to
beauty, perceptual complexity, receptor overlap, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import exp, isfinite, log, log10, sqrt
from typing import Any, Mapping, Sequence

from engine.scientific_contract import EvidenceDescriptor, ScientificClass

_WEISS_OLFACTORY_WHITE = (
    "https://www.weizmann.ac.il/brain-sciences/labs/schneidman/sites/"
    "neurobiology.labs.schneidman/files/publications/Weiss%2Bal_2012-PNAS.pdf"
)
_SINGH_COMPETITIVE_BINDING = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6511041/"
_FRANK_ADAPTATION = "https://academic.oup.com/chemse/article/42/7/537/3876319"
_WU_TEMPORAL_ORDER = "https://www.nature.com/articles/s41562-024-01984-8"
_MA_BINARY_HEDONICS = (
    "https://academic.oup.com/chemse/article-pdf/45/4/303/33435595/bjaa020.pdf"
)

_CANDIDATE_DIMENSIONS = (
    "recognizer_preservation",
    "structural_organization",
    "interaction",
    "temporal_shape",
    "texture",
    "contrast",
    "resilience_robustness",
    "post_ablation_effective_complexity",
    "execution_stock_readiness",
    "evidence_uncertainty",
)

_NONCOMPENSATORY_EXTERNAL_GATES = (
    "inventory_identity_and_stock",
    "active_dose_and_basis",
    "strict_oav_evidence",
    "physical_chemistry",
    "safety_and_regulatory",
    "provenance_and_source_use",
    "physical_observation",
)


class AxisStatus(str, Enum):
    """Whether an axis has enough declared inputs to emit bounded metrics."""

    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class NegativeSpaceProbe:
    """A declared interval whose modeled descriptor occupancy can be audited."""

    label: str
    axis: str
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        label = str(self.label).strip()
        axis = str(self.axis).strip()
        minimum = float(self.minimum)
        maximum = float(self.maximum)
        if not label or not axis:
            raise ValueError("negative-space probes require a label and descriptor axis")
        if not isfinite(minimum) or not isfinite(maximum) or minimum > maximum:
            raise ValueError("negative-space probe bounds must be finite and ordered")
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "axis", axis)
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "axis": self.axis,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


@dataclass(frozen=True, slots=True)
class ConstructionComplexityInputs:
    """Optional, explicit hypotheses layered onto canonical formula state.

    Descriptor vectors must be standardized within one declared measurement
    context before ``descriptor_vectors_standardized`` is set.  Functional
    groups are never converted into descriptor or receptor coordinates.
    """

    foreground_materials: tuple[str, ...] = ()
    background_materials: tuple[str, ...] = ()
    heavy_materials: tuple[str, ...] = ()
    descriptor_vectors: Mapping[str, Mapping[str, float]] = field(
        default_factory=dict
    )
    descriptor_vector_evidence: EvidenceDescriptor | None = None
    descriptor_vectors_standardized: bool = False
    gradient_material_order: tuple[str, ...] = ()
    negative_space_probes: tuple[NegativeSpaceProbe, ...] = ()
    hedonic_values: Mapping[str, float] = field(default_factory=dict)
    hedonic_material_order: tuple[str, ...] = ()
    hedonic_evidence: EvidenceDescriptor | None = None

    def __post_init__(self) -> None:
        foreground = _normalized_names(self.foreground_materials, "foreground_materials")
        background = _normalized_names(self.background_materials, "background_materials")
        heavy = _normalized_names(self.heavy_materials, "heavy_materials")
        gradient_order = _normalized_names(
            self.gradient_material_order,
            "gradient_material_order",
        )
        hedonic_order = _normalized_names(
            self.hedonic_material_order,
            "hedonic_material_order",
        )
        overlap = set(foreground).intersection(background)
        if overlap:
            raise ValueError(
                "foreground and background partitions overlap: "
                + ", ".join(sorted(overlap))
            )
        vectors = _normalized_vectors(self.descriptor_vectors)
        hedonic_values = _normalized_scalar_values(
            self.hedonic_values,
            "hedonic_values",
        )
        probes = tuple(self.negative_space_probes)
        if any(not isinstance(probe, NegativeSpaceProbe) for probe in probes):
            raise TypeError("negative_space_probes must contain NegativeSpaceProbe values")
        if self.descriptor_vector_evidence is not None and not isinstance(
            self.descriptor_vector_evidence,
            EvidenceDescriptor,
        ):
            raise TypeError("descriptor_vector_evidence must be an EvidenceDescriptor")
        if self.hedonic_evidence is not None and not isinstance(
            self.hedonic_evidence,
            EvidenceDescriptor,
        ):
            raise TypeError("hedonic_evidence must be an EvidenceDescriptor")
        object.__setattr__(self, "foreground_materials", foreground)
        object.__setattr__(self, "background_materials", background)
        object.__setattr__(self, "heavy_materials", heavy)
        object.__setattr__(self, "descriptor_vectors", vectors)
        object.__setattr__(self, "gradient_material_order", gradient_order)
        object.__setattr__(self, "negative_space_probes", probes)
        object.__setattr__(self, "hedonic_values", hedonic_values)
        object.__setattr__(self, "hedonic_material_order", hedonic_order)
        object.__setattr__(
            self,
            "descriptor_vectors_standardized",
            bool(self.descriptor_vectors_standardized),
        )


@dataclass(frozen=True, slots=True)
class ComplexityAxis:
    """One non-collapsed construction axis and its evidence posture."""

    status: AxisStatus
    metrics: Mapping[str, Any]
    evidence: EvidenceDescriptor
    interpretation: str
    validation_requirements: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "metrics": dict(self.metrics),
            "evidence": self.evidence.as_dict(),
            "interpretation": self.interpretation,
            "validation_requirements": list(self.validation_requirements),
        }


@dataclass(frozen=True, slots=True)
class ConstructionComplexityProfile:
    """A multi-axis diagnostic that deliberately cannot rank perfume quality."""

    axes: Mapping[str, ComplexityAxis]
    limitations: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    schema_version: str = "construction_complexity_profile_v1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_contract": {
                "complexity_authority": "WITHHELD",
                "candidate_only": True,
                "universal_row_count_gate_authorized": False,
                "aggregate_score_authorized": False,
                "automatic_rebuild_from_row_count_authorized": False,
                "hard_gate_override_authorized": False,
                "candidate_dimensions": list(_CANDIDATE_DIMENSIONS),
                "noncompensatory_external_gates": list(
                    _NONCOMPENSATORY_EXTERNAL_GATES
                ),
            },
            "axes": {name: axis.as_dict() for name, axis in self.axes.items()},
            "limitations": list(self.limitations),
            "forbidden_claims": list(self.forbidden_claims),
        }


def analyze_construction_complexity(
    state: Any,
    frames: Sequence[Any],
    *,
    inputs: ConstructionComplexityInputs | None = None,
) -> ConstructionComplexityProfile:
    """Build a deterministic, authority-labeled construction profile.

    ``state`` and each frame state are expected to expose canonical
    ``MaterialState`` fields (name, OAV, modeled intensity, identity flags).
    The loose protocol keeps the calculation independently testable while the
    canonical workbench supplies the production objects.
    """

    frame_tuple = tuple(frames)
    if not frame_tuple:
        raise ValueError("construction complexity requires at least one time frame")
    options = inputs or ConstructionComplexityInputs()
    material_names = tuple(str(material.name) for material in state.materials)
    if len(material_names) != len(set(material_names)):
        raise ValueError("construction complexity requires unique material names")
    axes: dict[str, ComplexityAxis] = {
        "formula_structure": _formula_structure_axis(state),
        "modeled_headspace_distribution": _headspace_axis(frame_tuple),
        "modeled_temporal_differentiation": _temporal_axis(frame_tuple),
        "descriptor_gradient": _descriptor_gradient_axis(
            material_names,
            options,
        ),
        "foreground_background": _foreground_background_axis(
            material_names,
            frame_tuple,
            options,
        ),
        "heavy_note_coexistence": _heavy_note_axis(
            material_names,
            frame_tuple,
            options,
        ),
        "negative_space": _negative_space_axis(
            material_names,
            frame_tuple,
            options,
        ),
        "hedonic_gradient": _hedonic_axis(material_names, options),
        "accord_graph_modularity": _unknown_axis(
            basis="no authority-labeled accord-edge set was supplied",
            requirements=(
                "declare each accord edge and preserve whether it is measured, panel-derived, or heuristic",
                "compute topology separately from the sensory meaning of an edge",
            ),
        ),
        "configural_emergence": _unknown_axis(
            basis="no recombination, omission, or selective-adaptation experiment was supplied",
            requirements=(
                "run blinded complete-mixture, omission, and addition controls",
                "record whether a note emerges, disappears, or is unmasked across participants",
            ),
            sources=(_FRANK_ADAPTATION, _SINGH_COMPETITIVE_BINDING),
        ),
        "individual_variability": _unknown_axis(
            basis="no participant-level response distribution was supplied",
            requirements=(
                "retain participant-level ratings, anosmia screening, expertise, and repeated measures",
                "report distributions and uncertainty rather than one population constant",
            ),
        ),
    }
    limitations = _unique(
        limitation
        for axis in axes.values()
        for limitation in axis.evidence.limitations
    )
    return ConstructionComplexityProfile(
        axes=axes,
        limitations=limitations,
        forbidden_claims=(
            "No axis or combination of axes is an overall beauty, quality, luxury, realism, similarity, or release score.",
            "Raw material count does not establish olfactory white, perceptual richness, clarity, or congestion.",
            "Functional-group membership does not establish receptor overlap or a perceptual gradient.",
            "Modeled OAV-derived intensity shares are not percent perceived contribution and do not prove independent perception.",
            "Low modeled descriptor occupancy does not prove an implied odor or aesthetic negative space.",
            "Component pleasantness does not by itself authorize a finished-mixture pleasantness claim.",
            "Complexity cannot compensate for a failed stock, active-dose, OAV-basis, physical-chemistry, safety, provenance, or physical-observation gate.",
        ),
    )


def _formula_structure_axis(state: Any) -> ComplexityAxis:
    materials = tuple(state.materials)
    metrics = {
        "material_count": len(materials),
        "known_material_count": sum(bool(material.is_known) for material in materials),
        "unknown_material_count": sum(not bool(material.is_known) for material in materials),
        "opaque_preblend_count": sum(
            bool(material.is_opaque_preblend) for material in materials
        ),
    }
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics=metrics,
        evidence=EvidenceDescriptor(
            classification=ScientificClass.EXACT,
            basis="deterministic counts over the supplied formula-state rows",
            sources=("engine.pipeline.formula_state",),
            limitations=(
                "EXACT applies to row accounting only, not sensory complexity or component independence.",
                "An opaque natural, base, or preblend may contain many undeclared constituents.",
            ),
        ),
        interpretation="Declared structural accounting only.",
    )


def _headspace_axis(frames: tuple[Any, ...]) -> ComplexityAxis:
    summaries = [_frame_distribution_summary(frame) for frame in frames]
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            "weighting_basis": "modeled_oav_derived_intensity_for_oav_gte_1",
            "windows": summaries,
            "perceived_component_count_authorized": False,
            "olfactory_white_inference_authorized": False,
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "Shannon effective count, evenness, and dominance calculated from "
                "canonical modeled OAV-derived intensities at OAV >= 1"
            ),
            sources=(
                "engine.pipeline.formula_state",
                _WEISS_OLFACTORY_WHITE,
                _SINGH_COMPETITIVE_BINDING,
            ),
            assumptions=(
                "stored ODT, vapor pressure, activity coefficient, and intensity transforms apply",
            ),
            limitations=(
                "headspace and OAV are modeled rather than measured for the finished perfume",
                "mixture suppression, synergy, learning, and participant variability are not calibrated",
                "effective modeled components are not the number of notes a person can identify",
                "olfactory-white studies used intensity-equated mixtures spanning olfactory space and do not supply a raw formula-count cutoff",
            ),
        ),
        interpretation="Modeled distribution shape, not perceived complexity.",
        validation_requirements=(
            "measure dynamic headspace for the finished matrix",
            "collect blinded participant-level mixture ratings at declared time points",
        ),
    )


def _temporal_axis(frames: tuple[Any, ...]) -> ComplexityAxis:
    distributions = [_perceptible_distribution(frame.state.materials) for frame in frames]
    transitions: list[dict[str, Any]] = []
    distances: list[float] = []
    for earlier, later, first, second in zip(
        frames,
        frames[1:],
        distributions,
        distributions[1:],
    ):
        distance = _jensen_shannon_distance(first, second)
        if distance is not None:
            distances.append(distance)
        first_dominant = _dominant_name(first)
        second_dominant = _dominant_name(second)
        transitions.append(
            {
                "from": str(earlier.label),
                "to": str(later.label),
                "delta_seconds": float(later.t_seconds) - float(earlier.t_seconds),
                "jensen_shannon_distance": distance,
                "dominant_material_before": first_dominant,
                "dominant_material_after": second_dominant,
                "dominant_identity_changed": (
                    None
                    if first_dominant is None or second_dominant is None
                    else first_dominant != second_dominant
                ),
            }
        )
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            "transitions": transitions,
            "mean_jensen_shannon_distance": (
                sum(distances) / len(distances) if distances else None
            ),
            "perceived_transition_authorized": False,
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "Jensen-Shannon distance between consecutive modeled OAV-derived "
                "perceptible-intensity distributions"
            ),
            sources=("engine.pipeline.simulator", _WU_TEMPORAL_ORDER),
            limitations=(
                "the temporal simulator is uncalibrated against skin, blotter, or headspace measurements",
                "distribution change does not establish a consciously perceived note transition",
                "within-sniff temporal order and multi-hour evaporation are different experimental scales",
            ),
        ),
        interpretation="Modeled redistribution through time, not measured narrative evolution.",
        validation_requirements=(
            "pair dynamic headspace sampling with repeated sensory measurements",
        ),
    )


def _descriptor_gradient_axis(
    material_names: tuple[str, ...],
    inputs: ConstructionComplexityInputs,
) -> ComplexityAxis:
    order = inputs.gradient_material_order
    vectors = inputs.descriptor_vectors
    evidence = inputs.descriptor_vector_evidence
    base_metrics = {"functional_groups_used": False}
    if (
        len(order) < 2
        or not vectors
        or evidence is None
        or not inputs.descriptor_vectors_standardized
    ):
        return _unknown_axis(
            basis="no standardized, source-labeled descriptor path was supplied",
            requirements=(
                "supply at least two ordered materials with same-axis standardized descriptor vectors",
                "bind vectors to a panel, concentration, matrix, and source revision",
            ),
            metrics=base_metrics,
        )
    missing_formula = sorted(set(order).difference(material_names))
    missing_vectors = sorted(set(order).difference(vectors))
    if missing_formula or missing_vectors:
        return _unknown_axis(
            basis="the declared descriptor path is incomplete",
            requirements=(
                "resolve missing formula materials or vectors before computing the path",
            ),
            metrics={
                **base_metrics,
                "missing_formula_materials": missing_formula,
                "missing_vectors": missing_vectors,
            },
            sources=evidence.sources,
        )
    axis_sets = [set(vectors[name]) for name in order]
    if not axis_sets or not axis_sets[0] or any(axes != axis_sets[0] for axes in axis_sets):
        return _unknown_axis(
            basis="descriptor vectors do not share one complete axis set",
            requirements=("standardize every ordered vector on identical axes",),
            metrics=base_metrics,
            sources=evidence.sources,
        )
    axes = tuple(sorted(axis_sets[0]))
    points = [tuple(vectors[name][axis] for axis in axes) for name in order]
    steps = [_euclidean(first, second) for first, second in zip(points, points[1:])]
    path_length = sum(steps)
    endpoint_distance = _euclidean(points[0], points[-1])
    monotonic_axes = 0
    for index in range(len(axes)):
        values = [point[index] for point in points]
        deltas = [right - left for left, right in zip(values, values[1:])]
        if all(delta >= 0 for delta in deltas) or all(delta <= 0 for delta in deltas):
            monotonic_axes += 1
    metrics = {
        **base_metrics,
        "material_order": list(order),
        "descriptor_axes": list(axes),
        "step_distances": steps,
        "path_length": path_length,
        "endpoint_distance": endpoint_distance,
        "path_directness": (
            endpoint_distance / path_length if path_length > 0 else None
        ),
        "step_distance_cv": _coefficient_of_variation(steps),
        "monotonic_axis_fraction": monotonic_axes / len(axes),
        "mixture_gradient_authorized": False,
    }
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics=metrics,
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "Euclidean path geometry over supplied standardized component "
                "descriptor vectors; input evidence is "
                f"{evidence.classification.value}"
            ),
            sources=(*evidence.sources, "engine.perception.construction_complexity"),
            assumptions=(*evidence.assumptions, "descriptor axes are commensurate after standardization"),
            limitations=(
                *evidence.limitations,
                "component-space path geometry does not prove that the mixture smells like a continuous gradient",
                "concentration, masking, receptor competition, adaptation, and temporal order remain unresolved",
            ),
        ),
        interpretation="A candidate component-descriptor path for testing, not a receptor or mixture-perception gradient.",
        validation_requirements=(
            "test ordered accords and shuffled-order controls with a blinded panel",
            "recompute vectors for the actual concentration and matrix when available",
        ),
    )


def _foreground_background_axis(
    material_names: tuple[str, ...],
    frames: tuple[Any, ...],
    inputs: ConstructionComplexityInputs,
) -> ComplexityAxis:
    foreground = inputs.foreground_materials
    background = inputs.background_materials
    if not foreground or not background:
        return _unknown_axis(
            basis="foreground and background material partitions were not both declared",
            requirements=(
                "declare non-overlapping foreground and background material sets for the brief",
            ),
        )
    missing = sorted((set(foreground) | set(background)).difference(material_names))
    if missing:
        return _unknown_axis(
            basis="the semantic partition contains materials absent from the formula",
            requirements=("resolve the missing partition members",),
            metrics={"missing_materials": missing},
        )
    windows = []
    for frame in frames:
        weights = _perceptible_weights(frame.state.materials)
        total = sum(weights.values())
        foreground_weight = sum(weights.get(name, 0.0) for name in foreground)
        background_weight = sum(weights.get(name, 0.0) for name in background)
        windows.append(
            {
                "label": str(frame.label),
                "t_seconds": float(frame.t_seconds),
                "foreground_share": foreground_weight / total if total else None,
                "background_share": background_weight / total if total else None,
                "residual_share": (
                    max(0.0, 1.0 - (foreground_weight + background_weight) / total)
                    if total
                    else None
                ),
                "foreground_to_background_ratio": (
                    foreground_weight / background_weight
                    if background_weight > 0
                    else None
                ),
                "modeled_salience_margin_log10": (
                    log10(foreground_weight / background_weight)
                    if foreground_weight > 0 and background_weight > 0
                    else None
                ),
            }
        )
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            "foreground_materials": list(foreground),
            "background_materials": list(background),
            "windows": windows,
            "semantic_figure_ground_authorized": False,
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis="brief-declared partitions summarized with modeled OAV-derived perceptible intensity",
            sources=("engine.pipeline.formula_state", _FRANK_ADAPTATION),
            limitations=(
                "foreground/background labels are brief-relative semantic declarations",
                "modeled salience does not prove figure-ground perception or an implied note",
            ),
        ),
        interpretation="A declared salience partition for experimental design.",
        validation_requirements=(
            "run addition and omission controls against the complete perfume",
        ),
    )


def _heavy_note_axis(
    material_names: tuple[str, ...],
    frames: tuple[Any, ...],
    inputs: ConstructionComplexityInputs,
) -> ComplexityAxis:
    heavy = inputs.heavy_materials
    if not heavy:
        return _unknown_axis(
            basis="no brief-specific heavy-note material set was declared",
            requirements=(
                "declare which materials constitute the heavy note or accord under test",
            ),
        )
    missing = sorted(set(heavy).difference(material_names))
    if missing:
        return _unknown_axis(
            basis="the heavy-note set contains materials absent from the formula",
            requirements=("resolve the missing heavy-note members",),
            metrics={"missing_materials": missing},
        )
    windows = []
    coexistence_windows = 0
    for frame in frames:
        weights = _perceptible_weights(frame.state.materials)
        total = sum(weights.values())
        heavy_weight = sum(weights.get(name, 0.0) for name in heavy)
        nonheavy = {name: value for name, value in weights.items() if name not in heavy}
        nonheavy_weight = sum(nonheavy.values())
        coexistence = heavy_weight > 0 and nonheavy_weight > 0
        coexistence_windows += int(coexistence)
        windows.append(
            {
                "label": str(frame.label),
                "t_seconds": float(frame.t_seconds),
                "heavy_share": heavy_weight / total if total else None,
                "nonheavy_share": nonheavy_weight / total if total else None,
                "nonheavy_effective_component_count": _distribution_shape(nonheavy)[
                    "effective_component_count"
                ],
                "modeled_coexistence": coexistence,
            }
        )
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            "heavy_materials": list(heavy),
            "windows": windows,
            "modeled_coexistence_window_count": coexistence_windows,
            "independent_perception_authorized": False,
            "airiness_claim_authorized": False,
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "brief-declared heavy materials compared with the remaining "
                "modeled OAV-derived perceptible-intensity distribution"
            ),
            sources=("engine.pipeline.formula_state", _SINGH_COMPETITIVE_BINDING),
            limitations=(
                "coexisting modeled signals do not prove parallel or independent perception",
                "matrix partitioning, diffusion, masking, and participant adaptation are not calibrated",
                "airiness remains a sensory hypothesis requiring a defined panel protocol",
            ),
        ),
        interpretation="Modeled coexistence around a declared heavy accord, not sensory independence.",
        validation_requirements=(
            "measure dynamic headspace and run heavy-accord omission/addition controls",
            "define airiness and separability rating anchors before panel testing",
        ),
    )


def _negative_space_axis(
    material_names: tuple[str, ...],
    frames: tuple[Any, ...],
    inputs: ConstructionComplexityInputs,
) -> ComplexityAxis:
    probes = inputs.negative_space_probes
    vectors = inputs.descriptor_vectors
    evidence = inputs.descriptor_vector_evidence
    if (
        not probes
        or not vectors
        or evidence is None
        or not inputs.descriptor_vectors_standardized
    ):
        return _unknown_axis(
            basis="no standardized descriptor vectors and declared empty-space probes were supplied",
            requirements=(
                "declare a descriptor interval and source-labeled standardized component vectors",
                "pre-register an addition/omission test for the purported implied odor",
            ),
            metrics={"implied_odor_authorized": False},
        )
    missing_formula = sorted(set(vectors).difference(material_names))
    available_axes = set.intersection(*(set(vector) for vector in vectors.values()))
    missing_axes = sorted({probe.axis for probe in probes}.difference(available_axes))
    if missing_axes:
        return _unknown_axis(
            basis="one or more negative-space probe axes are absent from the vectors",
            requirements=("supply every declared probe axis for the covered materials",),
            metrics={
                "missing_probe_axes": missing_axes,
                "vectors_outside_formula": missing_formula,
                "implied_odor_authorized": False,
            },
            sources=evidence.sources,
        )
    probe_rows = []
    for probe in probes:
        windows = []
        for frame in frames:
            weights = _perceptible_weights(frame.state.materials)
            total = sum(weights.values())
            covered = {
                name: value
                for name, value in weights.items()
                if name in vectors and probe.axis in vectors[name]
            }
            occupied = sum(
                value
                for name, value in covered.items()
                if probe.minimum <= vectors[name][probe.axis] <= probe.maximum
            )
            covered_weight = sum(covered.values())
            windows.append(
                {
                    "label": str(frame.label),
                    "t_seconds": float(frame.t_seconds),
                    "descriptor_coverage_share": (
                        covered_weight / total if total else None
                    ),
                    "modeled_descriptor_occupancy_share": (
                        occupied / total if total else None
                    ),
                }
            )
        probe_rows.append({**probe.as_dict(), "windows": windows})
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            "probes": probe_rows,
            "vectors_outside_formula": missing_formula,
            "implied_odor_authorized": False,
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.SPECULATIVE,
            basis=(
                "declared descriptor-interval occupancy weighted by modeled "
                "OAV-derived perceptible component intensity"
            ),
            sources=(*evidence.sources, _FRANK_ADAPTATION),
            assumptions=(*evidence.assumptions, "component vectors remain informative in mixture"),
            limitations=(
                *evidence.limitations,
                "low component occupancy is not evidence that listeners perceive an empty region or implied odor",
                "the metric omits configural emergence and suppression unless tested experimentally",
            ),
        ),
        interpretation="An explicit gap hypothesis suitable for omission/addition testing.",
        validation_requirements=(
            "compare complete, gap-filled, and omission variants under blinded repeated measures",
        ),
    )


def _hedonic_axis(
    material_names: tuple[str, ...],
    inputs: ConstructionComplexityInputs,
) -> ComplexityAxis:
    order = inputs.hedonic_material_order
    values = inputs.hedonic_values
    evidence = inputs.hedonic_evidence
    base_metrics = {"mixture_pleasantness_authorized": False}
    if (
        len(order) < 2
        or not values
        or evidence is None
        or evidence.classification is not ScientificClass.EMPIRICALLY_CALIBRATED
    ):
        return _unknown_axis(
            basis="no concentration- and panel-calibrated component hedonic path was supplied",
            requirements=(
                "supply repeated participant-level pleasantness values for the declared matrix and concentration",
                "validate the finished mixture separately from its components",
            ),
            metrics=base_metrics,
            sources=(() if evidence is None else evidence.sources),
        )
    missing = sorted(
        set(order).difference(material_names) | set(order).difference(values)
    )
    if missing:
        return _unknown_axis(
            basis="the calibrated component hedonic path is incomplete",
            requirements=("resolve every missing ordered material value",),
            metrics={**base_metrics, "missing_materials": missing},
            sources=evidence.sources,
        )
    ordered_values = [values[name] for name in order]
    deltas = [right - left for left, right in zip(ordered_values, ordered_values[1:])]
    absolute_steps = [abs(value) for value in deltas]
    return ComplexityAxis(
        status=AxisStatus.AVAILABLE,
        metrics={
            **base_metrics,
            "material_order": list(order),
            "component_values": ordered_values,
            "component_value_range": max(ordered_values) - min(ordered_values),
            "step_distance_cv": _coefficient_of_variation(absolute_steps),
            "monotonic": all(delta >= 0 for delta in deltas)
            or all(delta <= 0 for delta in deltas),
        },
        evidence=EvidenceDescriptor(
            classification=ScientificClass.HEURISTIC,
            basis=(
                "path arithmetic over empirically calibrated component values; "
                "finished-mixture inference remains withheld"
            ),
            sources=(*evidence.sources, _MA_BINARY_HEDONICS),
            assumptions=evidence.assumptions,
            limitations=(
                *evidence.limitations,
                "component pleasantness and intensity do not fully determine higher-order perfume pleasantness",
                "panel, concentration, culture, adaptation, and mixture interactions remain specific to the experiment",
            ),
        ),
        interpretation="A calibrated component-value path, not a perfume beauty score.",
        validation_requirements=(
            "test the complete perfume and controlled variants with the same panel protocol",
        ),
    )


def _unknown_axis(
    *,
    basis: str,
    requirements: tuple[str, ...],
    metrics: Mapping[str, Any] | None = None,
    sources: tuple[str, ...] = (),
) -> ComplexityAxis:
    return ComplexityAxis(
        status=AxisStatus.UNKNOWN,
        metrics=dict(metrics or {}),
        evidence=EvidenceDescriptor(
            classification=ScientificClass.UNKNOWN,
            basis=basis,
            sources=sources,
            limitations=("No sensory or aesthetic claim is authorized for this axis.",),
        ),
        interpretation="Withheld until the declared evidence requirement is met.",
        validation_requirements=requirements,
    )


def _frame_distribution_summary(frame: Any) -> dict[str, Any]:
    materials = tuple(frame.state.materials)
    weights = _perceptible_weights(materials)
    shape = _distribution_shape(weights)
    return {
        "label": str(frame.label),
        "t_seconds": float(frame.t_seconds),
        "material_count": len(materials),
        "oav_available_count": sum(material.oav is not None for material in materials),
        "modeled_perceptible_count": len(weights),
        "missing_oav_count": sum(material.oav is None for material in materials),
        **shape,
    }


def _perceptible_weights(materials: Sequence[Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for material in materials:
        oav = material.oav
        intensity = material.intensity
        if (
            oav is None
            or intensity is None
            or not isfinite(float(oav))
            or not isfinite(float(intensity))
            or float(oav) < 1.0
            or float(intensity) <= 0.0
        ):
            continue
        weights[str(material.name)] = float(intensity)
    return weights


def _perceptible_distribution(materials: Sequence[Any]) -> dict[str, float]:
    weights = _perceptible_weights(materials)
    total = sum(weights.values())
    if total <= 0:
        return {}
    return {name: value / total for name, value in weights.items()}


def _distribution_shape(weights: Mapping[str, float]) -> dict[str, float | None]:
    positive = sorted((float(value) for value in weights.values() if value > 0), reverse=True)
    if not positive:
        return {
            "effective_component_count": 0.0,
            "evenness": None,
            "top1_share": 0.0,
            "top3_share": 0.0,
        }
    total = sum(positive)
    probabilities = [value / total for value in positive]
    entropy = -sum(value * log(value) for value in probabilities)
    effective = exp(entropy)
    return {
        "effective_component_count": effective,
        "evenness": entropy / log(len(probabilities)) if len(probabilities) > 1 else None,
        "top1_share": probabilities[0],
        "top3_share": sum(probabilities[:3]),
    }


def _jensen_shannon_distance(
    first: Mapping[str, float],
    second: Mapping[str, float],
) -> float | None:
    if not first or not second:
        return None
    keys = set(first) | set(second)
    midpoint = {name: (first.get(name, 0.0) + second.get(name, 0.0)) / 2 for name in keys}

    def divergence(source: Mapping[str, float]) -> float:
        return sum(
            value * (log(value / midpoint[name]) / log(2.0))
            for name, value in source.items()
            if value > 0 and midpoint[name] > 0
        )

    return sqrt(max(0.0, (divergence(first) + divergence(second)) / 2))


def _dominant_name(distribution: Mapping[str, float]) -> str | None:
    if not distribution:
        return None
    return min(distribution, key=lambda name: (-distribution[name], name))


def _euclidean(first: Sequence[float], second: Sequence[float]) -> float:
    return sqrt(sum((right - left) ** 2 for left, right in zip(first, second)))


def _coefficient_of_variation(values: Sequence[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return sqrt(variance) / mean


def _normalized_names(values: Sequence[str], label: str) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{label} contains an empty material name")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} contains duplicate material names")
    return normalized


def _normalized_vectors(
    values: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {}
    for raw_name, raw_vector in sorted(values.items(), key=lambda item: str(item[0])):
        name = str(raw_name).strip()
        if not name or name in normalized:
            raise ValueError("descriptor_vectors contains an empty or duplicate material")
        if not isinstance(raw_vector, Mapping) or not raw_vector:
            raise ValueError(f"descriptor vector for {name} must be a non-empty mapping")
        vector: dict[str, float] = {}
        for raw_axis, raw_value in sorted(
            raw_vector.items(),
            key=lambda item: str(item[0]),
        ):
            axis = str(raw_axis).strip()
            value = float(raw_value)
            if not axis or axis in vector or not isfinite(value):
                raise ValueError(f"descriptor vector for {name} is invalid")
            vector[axis] = value
        normalized[name] = vector
    return normalized


def _normalized_scalar_values(
    values: Mapping[str, float],
    label: str,
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for raw_name, raw_value in sorted(values.items(), key=lambda item: str(item[0])):
        name = str(raw_name).strip()
        value = float(raw_value)
        if not name or name in normalized or not isfinite(value):
            raise ValueError(f"{label} contains an invalid material value")
        normalized[name] = value
    return normalized


def _unique(values: Sequence[str] | Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


__all__ = [
    "AxisStatus",
    "ComplexityAxis",
    "ConstructionComplexityInputs",
    "ConstructionComplexityProfile",
    "NegativeSpaceProbe",
    "analyze_construction_complexity",
]
