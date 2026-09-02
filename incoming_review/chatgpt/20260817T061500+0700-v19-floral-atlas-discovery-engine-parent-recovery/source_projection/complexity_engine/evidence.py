from __future__ import annotations

from typing import Iterable

from consultant_core import sha256_json

OBSERVED_KINDS = {"PHYSICAL_OBSERVATION", "TRAINED_SENSORY_OBSERVATION", "CODED_SENSORY_OBSERVATION"}
MEASURED_KINDS = {"ANALYTICAL_MEASUREMENT", "INSTRUMENTAL_MEASUREMENT"}


def _has_prefix(links: Iterable[str], prefix: str) -> bool:
    return any(str(x).upper().startswith(prefix) for x in links)


def validate_evidence_transition(
    *,
    from_state: str,
    to_state: str,
    source_kind: str,
    evidence_links: list[str] | None,
) -> dict[str, object]:
    """Fail closed when plans, sources, or estimates are promoted to observations."""
    old = str(from_state).upper()
    new = str(to_state).upper()
    kind = str(source_kind).upper()
    links = [str(x) for x in (evidence_links or [])]
    failures: list[str] = []

    if new == "OBSERVED":
        if kind not in OBSERVED_KINDS:
            failures.append("Only an atomic physical or coded sensory observation may create OBSERVED state.")
        for prefix in ("OBS-", "EXP-", "CS-"):
            if not _has_prefix(links, prefix):
                failures.append(f"OBSERVED state requires a {prefix} evidence link.")
    elif new == "MEASURED":
        if kind not in MEASURED_KINDS:
            failures.append("Only an analytical or instrumental measurement may create MEASURED state.")
        for prefix in ("AM-", "EXP-"):
            if not _has_prefix(links, prefix):
                failures.append(f"MEASURED state requires a {prefix} evidence link.")
    elif new == "INFERRED_FROM_LOCKED_DATA":
        if kind not in {"LOCKED_ANALYSIS", "MODEL_RUN", "DERIVATION"}:
            failures.append("Inference requires a locked analysis or versioned model-run source.")
        if not (_has_prefix(links, "MR-") or _has_prefix(links, "DEC-") or _has_prefix(links, "PROV-")):
            failures.append("Inference requires a ModelRun, Decision, or Provenance link.")
    elif new in {"PROPOSED", "DESIGNED", "SOURCE_SUPPORTED_HYPOTHESIS", "NOT_RUN", "NOT_TESTED"}:
        pass
    elif new == "INVALIDATED":
        if not (_has_prefix(links, "DEC-") or _has_prefix(links, "PROV-")):
            failures.append("Invalidation requires an append-only Decision or Provenance link.")
    else:
        failures.append(f"Unsupported target evidence state: {new}.")

    if old in {"OBSERVED", "MEASURED"} and new in {"PROPOSED", "DESIGNED", "NOT_RUN", "NOT_TESTED"}:
        failures.append("Empirical records are append-only; supersede them instead of downgrading state in place.")

    state = "PASS" if not failures else "REJECTED"
    result: dict[str, object] = {
        "state": state,
        "from_state": old,
        "to_state": new,
        "source_kind": kind,
        "evidence_links": links,
        "failures": failures,
        "authority_upgrade": state == "PASS" and new in {"OBSERVED", "MEASURED"},
        "boundary": "A protocol, source statement, supplier description, or model estimate is never an observation.",
    }
    result["result_hash"] = sha256_json(result)
    return result
