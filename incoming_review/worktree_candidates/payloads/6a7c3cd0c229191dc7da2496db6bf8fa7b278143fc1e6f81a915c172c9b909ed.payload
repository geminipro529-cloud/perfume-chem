from __future__ import annotations

from typing import Any

from consultant_core import sha256_json
from complexity_engine.admission import evaluate_model_admission
from complexity_engine.causal import validate_causal_experiment
from complexity_engine.hypergraph import validate_nary_interaction
from complexity_engine.ontology import validate_model_definition
from complexity_engine.signature import build_formula_signature, portfolio_report
from meaningful_complexity_v3 import evaluate_complexity_v3


def run_model_development_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Run a complete design-stage model packet without creating empirical truth."""
    model = packet.get("model") or {}
    causal = packet.get("causal_experiment") or {}
    formulas = list(packet.get("formulas") or [])
    nary = list(packet.get("nary_interactions") or [])

    ontology = validate_model_definition(model)
    causal_result = validate_causal_experiment(causal) if causal else {"state":"NOT_RUN"}
    signatures = [build_formula_signature(f) for f in formulas]
    portfolio = portfolio_report(signatures)
    complexity = [evaluate_complexity_v3(f) for f in formulas]
    nary_results = [validate_nary_interaction(x) for x in nary]
    admission_payload = dict(packet.get("admission") or {})
    admission_payload.setdefault("model", model)
    admission_payload.setdefault("causal_experiment", causal_result)
    admission = evaluate_model_admission(admission_payload)

    if ontology["state"] != "PASS" or causal_result.get("state") == "REBUILD":
        state = "REBUILD"
    elif admission["state"] == "DESIGN_REGISTRY_ADMITTED":
        state = "DESIGN_PACKET_PASS"
    else:
        state = "HOLD"
    result = {
        "state":state,"ontology":ontology,"causal":causal_result,"formula_signatures":signatures,
        "portfolio":portfolio,"meaningful_complexity_v3":complexity,"nary_interactions":nary_results,
        "admission":admission,"formula_mutations":0,"physical_results_created":0,"canonical_promotion_authorized":False,
        "boundary":"A complete design packet still requires physical execution, coded observations, decisions, robustness, and Sol review."
    }
    result["packet_hash"]=sha256_json(result)
    return result
