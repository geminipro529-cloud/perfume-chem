"""Canonical OAV authority entrypoint with a fail-closed receipt firewall.

The previous implementation is preserved unchanged in
``engine.pipeline.oav_authority_legacy``.  Canonical callers enter here so OAV
cannot reconstruct FormulaState from legacy dilution/inventory assumptions
unless an explicitly labelled exploratory call opts out of authority.
"""

from __future__ import annotations

from dataclasses import replace

from engine.pipeline.oav_authority_legacy import *  # noqa: F401,F403
from engine.pipeline.oav_authority_legacy import (
    analyze_oav_authority as _legacy_analyze,
)


class OAVAuthorityError(ValueError):
    """Raised when OAV analysis is requested without sufficient receipt authority."""


def analyze_oav_authority(
    request: OAVAuthorityRequest,
    *,
    gate_report: GateReport | None = None,
    allow_unbound_exploratory: bool = False,
) -> OAVAuthorityResult:
    """Run OAV only from a BOUND gate receipt, unless explicitly exploratory.

    The exploratory escape hatch is intentionally opt-in and retains the legacy
    implementation's non-authoritative status. Canonical gate-bound analysis
    injects or verifies the exact FormulaDoseReceipt hash before any legacy OAV
    logic can execute.
    """

    if gate_report is None:
        if not allow_unbound_exploratory:
            raise OAVAuthorityError(
                "OAV authority requires a bound gate receipt; "
                "set allow_unbound_exploratory=True only for explicitly "
                "non-authoritative exploratory reconstruction"
            )
        return _legacy_analyze(request, gate_report=None)

    receipt = getattr(gate_report, "dose_receipt", None)
    if receipt is None or getattr(receipt, "status", None) != "BOUND":
        raise OAVAuthorityError(
            "OAV authority requires a BOUND FormulaDoseReceipt"
        )

    expected = str(getattr(receipt, "receipt_sha256", "") or "")
    if not expected:
        raise OAVAuthorityError(
            "OAV authority requires a FormulaDoseReceipt hash"
        )
    supplied = getattr(request, "dose_receipt_sha256", None)
    if supplied is not None and supplied != expected:
        raise OAVAuthorityError(
            "OAV request dose receipt does not match gate report"
        )

    bound_request = (
        request
        if supplied == expected
        else replace(request, dose_receipt_sha256=expected)
    )
    return _legacy_analyze(bound_request, gate_report=gate_report)
