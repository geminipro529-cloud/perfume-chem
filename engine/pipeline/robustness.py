"""Canonical robustness entrypoint with fail-closed authority semantics.

The prior perturbation implementation is preserved unchanged in
``engine.pipeline.robustness_legacy`` for historical comparison. Canonical
release-gate robustness does not execute that legacy simulator path until an
authorized perturbation adapter is explicitly wired.
"""

from __future__ import annotations

from engine.pipeline.robustness_legacy import *  # noqa: F401,F403
from engine.pipeline.robustness_legacy import (
    audit_formula_robustness as _legacy_audit,
)


def audit_formula_robustness(formula, config) -> RobustnessReport:
    """Return a fail-closed authority hold instead of rebuilding FormulaState.

    This is intentionally conservative. The legacy audit constructs temporal
    states from raw formula/dilution mappings and can therefore bypass the V5
    FormulaDoseReceipt firewall. Until perturbations are derived from an
    authorized base FormulaState/receipt, canonical robustness remains not
    evaluated. Existing commercial gate policy promotes this WARN to FAIL.
    """

    issue = PerturbationResult(
        material="-",
        direction="-",
        delta_ul=0.0,
        status="WARN",
        detail=(
            "Robustness not evaluated: authorized FormulaState / receipt-bound "
            "perturbation adapter required; legacy unbound simulation disabled."
        ),
    )
    return RobustnessReport(
        status="WARN",
        checked=0,
        skipped=0,
        issues=(issue,),
        perturbations=(),
    )
