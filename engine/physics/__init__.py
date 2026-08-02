"""C1 evidence contracts and selection.

This package represents condition-aware thermophysical evidence. It does not evaluate
thermodynamic equations and does not authorize scientific release.
"""

from engine.physics.properties import (
    CanonicalScope,
    ClaimGrade,
    PropertyConditions,
    PropertyDatum,
    PropertyIdentity,
    PropertyValueKind,
    SelectionStatus,
    SourceReference,
    ThermophysicalContractError,
    ThermophysicalProperty,
    UncertaintyDescriptor,
    UncertaintyKind,
)
from engine.physics.selection import (
    AuthorityState,
    InterpolationState,
    MissingDataReason,
    PropertyRequest,
    PropertySelectionResult,
    PropertySelectionService,
    SelectedPropertyAssertion,
    SelectionKind,
    selected_assertion_from_b2_reconstruction,
)
from engine.physics.vapor_pressure import (
    ExtrapolationPolicy,
    TemperatureRange,
    VaporPressureCoefficient,
    VaporPressureEquationType,
    VaporPressurePoint,
    VaporPressureRepresentation,
)

__all__ = [
    "AuthorityState",
    "CanonicalScope",
    "ClaimGrade",
    "ExtrapolationPolicy",
    "InterpolationState",
    "MissingDataReason",
    "PropertyConditions",
    "PropertyDatum",
    "PropertyIdentity",
    "PropertyRequest",
    "PropertySelectionResult",
    "PropertySelectionService",
    "PropertyValueKind",
    "SelectedPropertyAssertion",
    "SelectionKind",
    "SelectionStatus",
    "SourceReference",
    "TemperatureRange",
    "ThermophysicalContractError",
    "ThermophysicalProperty",
    "UncertaintyDescriptor",
    "UncertaintyKind",
    "VaporPressureCoefficient",
    "VaporPressureEquationType",
    "VaporPressurePoint",
    "VaporPressureRepresentation",
    "selected_assertion_from_b2_reconstruction",
]
