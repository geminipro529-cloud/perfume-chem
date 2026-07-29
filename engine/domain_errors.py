"""Stable domain errors shared by fail-closed engine entry points."""

from __future__ import annotations


class PerfumeChemDomainError(ValueError):
    """Base class for deterministic, user-correctable domain failures."""

    code = "PERFUME_CHEM_DOMAIN_ERROR"


class ReconstructionInputError(PerfumeChemDomainError):
    """Invalid reconstruction input detected before calculation."""

    code = "INVALID_RECONSTRUCTION_INPUT"


class EventStreamError(PerfumeChemDomainError):
    """Invalid or non-deterministic bottle event stream."""

    code = "INVALID_EVENT_STREAM"


class LegacyWriteProhibitedError(PerfumeChemDomainError):
    """A duplicate legacy ledger was asked to mutate canonical state."""

    code = "LEGACY_WRITE_PROHIBITED"


__all__ = [
    "EventStreamError",
    "LegacyWriteProhibitedError",
    "PerfumeChemDomainError",
    "ReconstructionInputError",
]
