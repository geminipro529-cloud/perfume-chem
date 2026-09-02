"""Lossless, versioned whole-perfume structural blueprints.

The assembler carries exact typed sources rather than caller-authored summaries.
It maps target, inventory, assessment, synthesis, and candidate-assembly records
onto architectural planes, derives every source hash, and takes the explicit
authority meet.  It never emits a formula, physical instruction, sensory result,
or release claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .candidate_assembler import CandidateAssemblyBlueprint
from .contracts import AuthorityCeiling, PlaneAssessment, PlaneId, ProvenanceRef
from .inventory_projection import (
    IdealProposal,
    InventoryProjection,
    _bool,
    _canonical_json_bytes,
    _CanonicalProjectionRecord,
    _digest,
    _mapping,
    _payload,
    _sequence,
    _text,
)
from .plane_synthesis import PlaneSynthesisResult
from .target_compiler import TargetIntent, TargetResolution


def _target_authority(target: TargetIntent) -> AuthorityCeiling:
    if target.resolution is not TargetResolution.RESOLVED_FOR_DESIGN:
        return AuthorityCeiling.WITHHELD
    return target.to_plane_assessment().authority_ceiling


def _canonical_assessments(
    values: Iterable[PlaneAssessment],
) -> tuple[PlaneAssessment, ...]:
    by_id: dict[str, PlaneAssessment] = {}
    by_hash: dict[str, PlaneAssessment] = {}
    for value in values:
        if not isinstance(value, PlaneAssessment):
            raise TypeError("assessments must contain PlaneAssessment values")
        current = by_id.get(value.assessment_id)
        if current is not None and current != value:
            raise ValueError(
                f"assessment_id {value.assessment_id!r} has conflicting records"
            )
        by_id[value.assessment_id] = value
        by_hash[value.content_sha256] = value
    return tuple(by_hash[key] for key in sorted(by_hash))


def _canonical_syntheses(
    values: Iterable[PlaneSynthesisResult],
) -> tuple[PlaneSynthesisResult, ...]:
    by_hash: dict[str, PlaneSynthesisResult] = {}
    for value in values:
        if not isinstance(value, PlaneSynthesisResult):
            raise TypeError("syntheses must contain PlaneSynthesisResult values")
        by_hash[value.content_sha256] = value
    return tuple(by_hash[key] for key in sorted(by_hash))


def _unique_by_hash(values: Iterable[Any]) -> tuple[Any, ...]:
    by_hash = {value.content_sha256: value for value in values}
    return tuple(by_hash[key] for key in sorted(by_hash))


@dataclass(frozen=True, slots=True)
class PlaneBlueprint(_CanonicalProjectionRecord):
    """One plane with complete typed sources and derived receipts."""

    SCHEMA_VERSION = "whole_perfume_plane_blueprint_v2"

    plane_id: PlaneId
    target_intents: tuple[TargetIntent, ...]
    inventory_projections: tuple[InventoryProjection, ...]
    assessments: tuple[PlaneAssessment, ...]
    syntheses: tuple[PlaneSynthesisResult, ...]
    source_hashes: tuple[str, ...]
    authority_ceiling: AuthorityCeiling

    def __post_init__(self) -> None:
        plane_id = PlaneId(self.plane_id)
        object.__setattr__(self, "plane_id", plane_id)

        targets = _unique_by_hash(self.target_intents)
        if any(not isinstance(item, TargetIntent) for item in targets):
            raise TypeError("target_intents must contain TargetIntent values")
        if targets and plane_id is not PlaneId.IDENTITY:
            raise ValueError("typed target sources belong only to the identity plane")
        inventories = _unique_by_hash(self.inventory_projections)
        if any(not isinstance(item, InventoryProjection) for item in inventories):
            raise TypeError(
                "inventory_projections must contain InventoryProjection values"
            )
        if inventories and plane_id is not PlaneId.INVENTORY_BUILD:
            raise ValueError(
                "typed inventory projections belong only to the inventory-build plane"
            )
        assessments = _canonical_assessments(self.assessments)
        if any(item.plane_id is not plane_id for item in assessments):
            raise ValueError("assessment source is mapped to the wrong plane")
        syntheses = _canonical_syntheses(self.syntheses)
        for synthesis in syntheses:
            represented = {assessment.plane_id for assessment in synthesis.assessments}
            if plane_id not in represented:
                raise ValueError("synthesis source is mapped to a plane it does not contain")

        sources: tuple[Any, ...] = (*targets, *inventories, *assessments, *syntheses)
        if not sources:
            raise ValueError("a plane blueprint requires at least one typed source")
        expected_hashes = tuple(sorted({item.content_sha256 for item in sources}))
        supplied_hashes = tuple(
            sorted({_digest(item, "source_hashes") for item in self.source_hashes})
        )
        if supplied_hashes != expected_hashes:
            raise ValueError("source_hashes must be derived from every complete source record")

        source_authorities = (
            *(_target_authority(item) for item in targets),
            *(item.authority_ceiling for item in inventories),
            *(item.authority_ceiling for item in assessments),
            *(item.authority_ceiling for item in syntheses),
        )
        expected_authority = AuthorityCeiling.minimum(source_authorities)
        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("plane authority must equal the explicit source authority meet")

        object.__setattr__(self, "target_intents", targets)
        object.__setattr__(self, "inventory_projections", inventories)
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "syntheses", syntheses)
        object.__setattr__(self, "source_hashes", expected_hashes)
        object.__setattr__(self, "authority_ceiling", authority)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlaneBlueprint:
        data = _payload(payload, cls)
        return cls(
            plane_id=PlaneId(data["plane_id"]),
            target_intents=tuple(
                TargetIntent.from_dict(_mapping(item, "target_intents item"))
                for item in _sequence(data["target_intents"], "target_intents")
            ),
            inventory_projections=tuple(
                InventoryProjection.from_dict(
                    _mapping(item, "inventory_projections item")
                )
                for item in _sequence(
                    data["inventory_projections"], "inventory_projections"
                )
            ),
            assessments=tuple(
                PlaneAssessment.from_dict(_mapping(item, "assessments item"))
                for item in _sequence(data["assessments"], "assessments")
            ),
            syntheses=tuple(
                PlaneSynthesisResult.from_dict(_mapping(item, "syntheses item"))
                for item in _sequence(data["syntheses"], "syntheses")
            ),
            source_hashes=tuple(
                _sequence(data["source_hashes"], "source_hashes")
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
        )

    @property
    def provenance_refs(self) -> tuple[ProvenanceRef, ...]:
        return _unique_by_hash(
            (
                *(
                    item
                    for target in self.target_intents
                    for item in target.provenance_refs
                ),
                *(
                    item
                    for assessment in self.assessments
                    for item in assessment.provenance_refs
                ),
                *(
                    item
                    for synthesis in self.syntheses
                    for item in synthesis.provenance_refs
                ),
            )
        )

    @property
    def conflicts(self) -> tuple[Any, ...]:
        return _unique_by_hash(
            (
                *(item for source in self.assessments for item in source.conflicts),
                *(item for source in self.syntheses for item in source.conflicts),
            )
        )

    @property
    def unknowns(self) -> tuple[Any, ...]:
        return _unique_by_hash(
            (
                *(item for source in self.assessments for item in source.unknowns),
                *(item for source in self.syntheses for item in source.unknowns),
            )
        )

    @property
    def native_criteria(self) -> tuple[Any, ...]:
        return _unique_by_hash(
            (
                *(item for source in self.assessments for item in source.native_criteria),
                *(item for source in self.syntheses for item in source.native_criteria),
            )
        )

    @property
    def proposed_experiments(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item
                    for assessment in (
                        *self.assessments,
                        *(
                            nested
                            for synthesis in self.syntheses
                            for nested in synthesis.assessments
                        ),
                    )
                    for item in assessment.proposed_experiments
                }
            )
        )


@dataclass(frozen=True, slots=True)
class WholePerfumeBlueprint(_CanonicalProjectionRecord):
    """Immutable whole-plane receipt with no formula or release authority."""

    SCHEMA_VERSION = "versioned_whole_perfume_blueprint_v2"

    blueprint_id: str
    version: int
    predecessor_sha256: str | None
    ideal_proposal: IdealProposal
    inventory_projection: InventoryProjection
    planes: tuple[PlaneBlueprint, ...]
    authority_ceiling: AuthorityCeiling
    physical_execution_authorized: bool = False
    observed_smell: bool = False
    release_authorized: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        predecessor = (
            _digest(self.predecessor_sha256, "predecessor_sha256")
            if self.predecessor_sha256 is not None
            else None
        )
        if self.version == 1 and predecessor is not None:
            raise ValueError("version 1 must not declare a predecessor")
        if self.version > 1 and predecessor is None:
            raise ValueError("version successors require predecessor_sha256")
        object.__setattr__(self, "predecessor_sha256", predecessor)
        if not isinstance(self.ideal_proposal, IdealProposal):
            raise TypeError("ideal_proposal must be an IdealProposal")
        if not isinstance(self.inventory_projection, InventoryProjection):
            raise TypeError("inventory_projection must be an InventoryProjection")
        if self.inventory_projection.ideal_proposal != self.ideal_proposal:
            raise ValueError("inventory projection does not bind the exact ideal proposal")

        by_plane: dict[PlaneId, PlaneBlueprint] = {}
        for plane in self.planes:
            if not isinstance(plane, PlaneBlueprint):
                raise TypeError("planes must contain PlaneBlueprint values")
            if plane.plane_id in by_plane:
                raise ValueError("planes must contain exactly one record per plane_id")
            by_plane[plane.plane_id] = plane
        if not by_plane:
            raise ValueError("planes must not be empty")
        planes = tuple(by_plane[key] for key in sorted(by_plane, key=lambda item: item.value))
        self._validate_source_coverage(planes)
        object.__setattr__(self, "planes", planes)

        expected_authority = AuthorityCeiling.minimum(
            (
                _target_authority(self.ideal_proposal.target_intent),
                self.inventory_projection.authority_ceiling,
                *(plane.authority_ceiling for plane in planes),
            )
        )
        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("whole authority must equal the explicit source authority meet")
        object.__setattr__(self, "authority_ceiling", authority)
        for field_name in (
            "physical_execution_authorized",
            "observed_smell",
            "release_authorized",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value is not False:
                raise ValueError(f"{field_name} cannot be promoted by blueprint assembly")

        expected = _blueprint_id(
            version=self.version,
            predecessor_sha256=predecessor,
            ideal_proposal_sha256=self.ideal_proposal.content_sha256,
            inventory_projection_sha256=self.inventory_projection.content_sha256,
            planes=planes,
            authority_ceiling=authority,
        )
        supplied = _text(self.blueprint_id, "blueprint_id")
        if supplied != expected:
            raise ValueError("blueprint_id does not match complete blueprint content")
        object.__setattr__(self, "blueprint_id", supplied)

    def _validate_source_coverage(self, planes: tuple[PlaneBlueprint, ...]) -> None:
        target = self.ideal_proposal.target_intent
        target_placements = tuple(
            (plane.plane_id, item)
            for plane in planes
            for item in plane.target_intents
        )
        if target_placements != ((PlaneId.IDENTITY, target),):
            raise ValueError("typed target source is missing, duplicated, or misrouted")
        projection_placements = tuple(
            (plane.plane_id, item)
            for plane in planes
            for item in plane.inventory_projections
        )
        if projection_placements != ((PlaneId.INVENTORY_BUILD, self.inventory_projection),):
            raise ValueError(
                "typed inventory projection is missing, duplicated, or misrouted"
            )

        assessment_placements: dict[str, set[PlaneId]] = {}
        synthesis_placements: dict[str, set[PlaneId]] = {}
        assessment_records: dict[str, PlaneAssessment] = {}
        synthesis_records: dict[str, PlaneSynthesisResult] = {}
        for plane in planes:
            for assessment in plane.assessments:
                assessment_placements.setdefault(assessment.content_sha256, set()).add(
                    plane.plane_id
                )
                assessment_records[assessment.content_sha256] = assessment
            for synthesis in plane.syntheses:
                synthesis_placements.setdefault(synthesis.content_sha256, set()).add(
                    plane.plane_id
                )
                synthesis_records[synthesis.content_sha256] = synthesis

        required_assessments = (
            target.to_plane_assessment(),
            self.inventory_projection.to_plane_assessment(),
        )
        for required in required_assessments:
            if assessment_placements.get(required.content_sha256) != {required.plane_id}:
                raise ValueError("required target/inventory plane assessment is omitted")
        for digest, assessment in assessment_records.items():
            if assessment_placements[digest] != {assessment.plane_id}:
                raise ValueError("assessment source is omitted or duplicated across planes")
            if assessment.scope.target_scope != target.ideal_target_id.value:
                raise ValueError("assessment target_scope does not match the typed target")
        for digest, synthesis in synthesis_records.items():
            represented = {item.plane_id for item in synthesis.assessments}
            if synthesis_placements[digest] != represented:
                raise ValueError("synthesis source is not mapped to every represented plane")
            if any(
                item.scope.target_scope != target.ideal_target_id.value
                for item in synthesis.assessments
            ):
                raise ValueError("synthesis target_scope does not match the typed target")
            for assessment in synthesis.assessments:
                if assessment.content_sha256 not in assessment_records:
                    raise ValueError("synthesis assessment source was omitted from blueprint")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> WholePerfumeBlueprint:
        data = _payload(payload, cls)
        return cls(
            blueprint_id=data["blueprint_id"],
            version=data["version"],
            predecessor_sha256=data["predecessor_sha256"],
            ideal_proposal=IdealProposal.from_dict(
                _mapping(data["ideal_proposal"], "ideal_proposal")
            ),
            inventory_projection=InventoryProjection.from_dict(
                _mapping(data["inventory_projection"], "inventory_projection")
            ),
            planes=tuple(
                PlaneBlueprint.from_dict(_mapping(item, "planes item"))
                for item in _sequence(data["planes"], "planes")
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            physical_execution_authorized=_bool(
                data["physical_execution_authorized"],
                "physical_execution_authorized",
            ),
            observed_smell=_bool(data["observed_smell"], "observed_smell"),
            release_authorized=_bool(
                data["release_authorized"], "release_authorized"
            ),
        )

    @property
    def ideal_target_id(self) -> str:
        return self.ideal_proposal.ideal_target_id

    @property
    def ideal_proposal_sha256(self) -> str:
        return self.ideal_proposal.content_sha256

    @property
    def inventory_projection_sha256(self) -> str:
        return self.inventory_projection.content_sha256

    @property
    def cross_plane_conflicts(self) -> tuple[Any, ...]:
        return _unique_by_hash(
            item for plane in self.planes for item in plane.conflicts
        )

    @property
    def alternatives(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    alternative
                    for conflict in self.cross_plane_conflicts
                    for alternative in conflict.alternatives
                }
            )
        )

    @property
    def proposed_experiments(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    experiment
                    for plane in self.planes
                    for experiment in plane.proposed_experiments
                }
            )
        )


_INTEGRATED_AUTHORITY_FLAGS = (
    "formula_generation_authorized",
    "formula_mutation_authorized",
    "inventory_mutation_authorized",
    "physical_execution_authorized",
    "compounding_authorized",
    "purchase_authority",
    "sensory_authority",
    "liking_authority",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "observed_smell",
    "release_authorized",
)


@dataclass(frozen=True, slots=True)
class IntegratedWholePerfumeBlueprint(_CanonicalProjectionRecord):
    """Exact candidate-to-inventory-to-whole integration receipt.

    The wrapper closes the former gap between the all-plane candidate assembly
    and the lossless whole-perfume blueprint.  It preserves both complete source
    records, verifies their target/build identities, and cannot promote any
    formula, physical, sensory, safety, stability, or release authority.
    """

    SCHEMA_VERSION = "integrated_whole_perfume_blueprint_v1"

    integration_id: str
    version: int
    predecessor_sha256: str | None
    candidate_assembly: CandidateAssemblyBlueprint
    whole_blueprint: WholePerfumeBlueprint
    authority_ceiling: AuthorityCeiling
    formula_generation_authorized: bool = False
    formula_mutation_authorized: bool = False
    inventory_mutation_authorized: bool = False
    physical_execution_authorized: bool = False
    compounding_authorized: bool = False
    purchase_authority: bool = False
    sensory_authority: bool = False
    liking_authority: bool = False
    similarity_authority: bool = False
    performance_authority: bool = False
    safety_authority: bool = False
    stability_authority: bool = False
    observed_smell: bool = False
    release_authorized: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise TypeError("version must be an integer")
        if self.version < 1:
            raise ValueError("version must be at least 1")
        predecessor = (
            _digest(self.predecessor_sha256, "predecessor_sha256")
            if self.predecessor_sha256 is not None
            else None
        )
        if self.version == 1 and predecessor is not None:
            raise ValueError("version 1 must not declare a predecessor")
        if self.version > 1 and predecessor is None:
            raise ValueError("version successors require predecessor_sha256")
        object.__setattr__(self, "predecessor_sha256", predecessor)
        if not isinstance(self.candidate_assembly, CandidateAssemblyBlueprint):
            raise TypeError("candidate_assembly must be a CandidateAssemblyBlueprint")
        if not isinstance(self.whole_blueprint, WholePerfumeBlueprint):
            raise TypeError("whole_blueprint must be a WholePerfumeBlueprint")
        if self.whole_blueprint.version != self.version:
            raise ValueError("whole blueprint version must match integration version")
        if self.whole_blueprint.predecessor_sha256 != predecessor:
            raise ValueError("whole blueprint predecessor must match integration predecessor")

        target_id = self.whole_blueprint.ideal_target_id
        if self.candidate_assembly.target_ideal_id != target_id:
            raise ValueError("candidate assembly target does not match the typed whole target")
        build_id = (
            self.whole_blueprint.inventory_projection.build_projection_id.projection_id
        )
        if self.candidate_assembly.current_inventory_build_id != build_id:
            raise ValueError(
                "candidate assembly build does not match the exact inventory projection"
            )
        if {plane.plane_id for plane in self.whole_blueprint.planes} != set(PlaneId):
            raise ValueError("integrated whole blueprint must represent all 13 planes")
        whole_assessment_hashes = {
            assessment.content_sha256
            for plane in self.whole_blueprint.planes
            for assessment in plane.assessments
        }
        candidate_assessment_hashes = {
            assessment.content_sha256
            for assessment in self.candidate_assembly.plane_assessments
        }
        if not candidate_assessment_hashes.issubset(whole_assessment_hashes):
            raise ValueError(
                "whole blueprint omits candidate assembly plane assessments"
            )

        expected_authority = AuthorityCeiling.minimum(
            (
                self.candidate_assembly.authority_ceiling,
                self.whole_blueprint.authority_ceiling,
            )
        )
        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not expected_authority:
            raise ValueError("integration authority must equal the explicit source meet")
        object.__setattr__(self, "authority_ceiling", authority)
        for field_name in _INTEGRATED_AUTHORITY_FLAGS:
            value = getattr(self, field_name)
            if not isinstance(value, bool):
                raise TypeError(f"{field_name} must be bool")
            if value is not False:
                raise ValueError(f"{field_name} cannot be promoted by integration")

        expected_id = _integrated_blueprint_id(
            version=self.version,
            predecessor_sha256=predecessor,
            candidate_assembly_sha256=self.candidate_assembly.content_sha256,
            whole_blueprint_sha256=self.whole_blueprint.content_sha256,
            authority_ceiling=authority,
        )
        supplied = _text(self.integration_id, "integration_id")
        if supplied != expected_id:
            raise ValueError("integration_id does not match complete integrated content")
        object.__setattr__(self, "integration_id", supplied)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> IntegratedWholePerfumeBlueprint:
        data = _payload(payload, cls)
        return cls(
            integration_id=data["integration_id"],
            version=data["version"],
            predecessor_sha256=data["predecessor_sha256"],
            candidate_assembly=CandidateAssemblyBlueprint.from_dict(
                _mapping(data["candidate_assembly"], "candidate_assembly")
            ),
            whole_blueprint=WholePerfumeBlueprint.from_dict(
                _mapping(data["whole_blueprint"], "whole_blueprint")
            ),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            **{
                field_name: _bool(data[field_name], field_name)
                for field_name in _INTEGRATED_AUTHORITY_FLAGS
            },
        )


def _integrated_blueprint_id(
    *,
    version: int,
    predecessor_sha256: str | None,
    candidate_assembly_sha256: str,
    whole_blueprint_sha256: str,
    authority_ceiling: AuthorityCeiling,
) -> str:
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "integrated_whole_perfume_identity_payload_v1",
                "version": version,
                "predecessor_sha256": predecessor_sha256,
                "candidate_assembly_sha256": candidate_assembly_sha256,
                "whole_blueprint_sha256": whole_blueprint_sha256,
                "authority_ceiling": authority_ceiling,
            }
        )
    ).hexdigest()
    return f"integrated-whole-perfume-blueprint/v{version}/{digest}"


def _blueprint_id(
    *,
    version: int,
    predecessor_sha256: str | None,
    ideal_proposal_sha256: str,
    inventory_projection_sha256: str,
    planes: tuple[PlaneBlueprint, ...],
    authority_ceiling: AuthorityCeiling,
) -> str:
    digest = sha256(
        _canonical_json_bytes(
            {
                "schema_version": "whole_perfume_blueprint_identity_payload_v2",
                "version": version,
                "predecessor_sha256": predecessor_sha256,
                "ideal_proposal_sha256": ideal_proposal_sha256,
                "inventory_projection_sha256": inventory_projection_sha256,
                "planes": planes,
                "authority_ceiling": authority_ceiling,
            }
        )
    ).hexdigest()
    return f"whole-perfume-blueprint/v{version}/{digest}"


def assemble_whole_perfume_blueprint(
    ideal: IdealProposal,
    projection: InventoryProjection,
    assessments: Iterable[PlaneAssessment],
    *,
    syntheses: Iterable[PlaneSynthesisResult] = (),
    version: int,
    predecessor_sha256: str | None = None,
) -> WholePerfumeBlueprint:
    """Assemble lossless typed sources into deterministic plane blueprints."""

    if not isinstance(ideal, IdealProposal):
        raise TypeError("ideal must be an IdealProposal")
    if not isinstance(projection, InventoryProjection):
        raise TypeError("projection must be an InventoryProjection")
    if projection.ideal_proposal != ideal:
        raise ValueError("projection does not bind the supplied ideal proposal")

    synthesis_records = _canonical_syntheses(syntheses)
    assessment_records = _canonical_assessments(
        (
            ideal.target_intent.to_plane_assessment(),
            projection.to_plane_assessment(),
            *tuple(assessments),
            *(
                nested
                for synthesis in synthesis_records
                for nested in synthesis.assessments
            ),
        )
    )
    expected_target_scope = ideal.target_intent.ideal_target_id.value
    if any(
        assessment.scope.target_scope != expected_target_scope
        for assessment in assessment_records
    ):
        raise ValueError("all assessments must use the exact typed target_scope")

    plane_ids = {
        PlaneId.IDENTITY,
        PlaneId.INVENTORY_BUILD,
        *(item.plane_id for item in assessment_records),
        *(
            item.plane_id
            for synthesis in synthesis_records
            for item in synthesis.assessments
        ),
    }
    planes: list[PlaneBlueprint] = []
    for plane_id in sorted(plane_ids, key=lambda item: item.value):
        targets = (ideal.target_intent,) if plane_id is PlaneId.IDENTITY else ()
        inventories = (projection,) if plane_id is PlaneId.INVENTORY_BUILD else ()
        plane_assessments = tuple(
            item for item in assessment_records if item.plane_id is plane_id
        )
        plane_syntheses = tuple(
            item
            for item in synthesis_records
            if plane_id in {nested.plane_id for nested in item.assessments}
        )
        sources: tuple[Any, ...] = (
            *targets,
            *inventories,
            *plane_assessments,
            *plane_syntheses,
        )
        source_authorities = (
            *(_target_authority(item) for item in targets),
            *(item.authority_ceiling for item in inventories),
            *(item.authority_ceiling for item in plane_assessments),
            *(item.authority_ceiling for item in plane_syntheses),
        )
        planes.append(
            PlaneBlueprint(
                plane_id=plane_id,
                target_intents=targets,
                inventory_projections=inventories,
                assessments=plane_assessments,
                syntheses=plane_syntheses,
                source_hashes=tuple(item.content_sha256 for item in sources),
                authority_ceiling=AuthorityCeiling.minimum(source_authorities),
            )
        )

    normalized_planes = tuple(planes)
    authority = AuthorityCeiling.minimum(
        (
            _target_authority(ideal.target_intent),
            projection.authority_ceiling,
            *(plane.authority_ceiling for plane in normalized_planes),
        )
    )
    normalized_predecessor = (
        _digest(predecessor_sha256, "predecessor_sha256")
        if predecessor_sha256 is not None
        else None
    )
    blueprint_id = _blueprint_id(
        version=version,
        predecessor_sha256=normalized_predecessor,
        ideal_proposal_sha256=ideal.content_sha256,
        inventory_projection_sha256=projection.content_sha256,
        planes=normalized_planes,
        authority_ceiling=authority,
    )
    return WholePerfumeBlueprint(
        blueprint_id=blueprint_id,
        version=version,
        predecessor_sha256=normalized_predecessor,
        ideal_proposal=ideal,
        inventory_projection=projection,
        planes=normalized_planes,
        authority_ceiling=authority,
    )


def assemble_integrated_whole_perfume_blueprint(
    ideal: IdealProposal,
    projection: InventoryProjection,
    candidate_assembly: CandidateAssemblyBlueprint,
    *,
    syntheses: Iterable[PlaneSynthesisResult] = (),
    version: int,
    predecessor_sha256: str | None = None,
) -> IntegratedWholePerfumeBlueprint:
    """Bind one all-plane candidate assembly to one exact inventory build.

    The candidate decisions and relation packets remain embedded in their
    complete source artifact; every candidate plane assessment is carried into
    the whole blueprint.  No execution or outcome authority is created.
    """

    if not isinstance(candidate_assembly, CandidateAssemblyBlueprint):
        raise TypeError("candidate_assembly must be a CandidateAssemblyBlueprint")
    if candidate_assembly.target_ideal_id != ideal.target_intent.ideal_target_id.value:
        raise ValueError("candidate assembly target does not match the supplied ideal")
    if (
        candidate_assembly.current_inventory_build_id
        != projection.build_projection_id.projection_id
    ):
        raise ValueError("candidate assembly does not bind the supplied inventory build")
    whole = assemble_whole_perfume_blueprint(
        ideal,
        projection,
        candidate_assembly.plane_assessments,
        syntheses=syntheses,
        version=version,
        predecessor_sha256=predecessor_sha256,
    )
    authority = AuthorityCeiling.minimum(
        (candidate_assembly.authority_ceiling, whole.authority_ceiling)
    )
    normalized_predecessor = (
        _digest(predecessor_sha256, "predecessor_sha256")
        if predecessor_sha256 is not None
        else None
    )
    integration_id = _integrated_blueprint_id(
        version=version,
        predecessor_sha256=normalized_predecessor,
        candidate_assembly_sha256=candidate_assembly.content_sha256,
        whole_blueprint_sha256=whole.content_sha256,
        authority_ceiling=authority,
    )
    return IntegratedWholePerfumeBlueprint(
        integration_id=integration_id,
        version=version,
        predecessor_sha256=normalized_predecessor,
        candidate_assembly=candidate_assembly,
        whole_blueprint=whole,
        authority_ceiling=authority,
    )


__all__ = [
    "IntegratedWholePerfumeBlueprint",
    "PlaneBlueprint",
    "WholePerfumeBlueprint",
    "assemble_integrated_whole_perfume_blueprint",
    "assemble_whole_perfume_blueprint",
]
