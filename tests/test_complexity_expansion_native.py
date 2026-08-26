from __future__ import annotations

from engine.perception.complexity_expansion import (
    ExpansionAuditState,
    ExpansionDirection,
    ExpansionDiscoveryRound,
    ExpansionOrigin,
    ExpansionPriority,
    ExpansionSaturationState,
    assess_bounded_saturation,
    audit_expansion_registry,
    pareto_experiment_frontier,
)

PACKAGE_SHA = "a" * 64


def _registry() -> dict:
    return {
        "domains": [{"domain_id": "DX-01"}, {"domain_id": "DX-02"}],
        "directions": [
            {
                "direction_id": "ED-001",
                "domain_id": "DX-01",
                "title": "Functional diversity",
                "origin": "INHERITED_V1",
                "current_state": "FORMAL MODEL / REGISTRY",
                "priority": "P0",
                "evidence_ceiling": "DESIGN",
                "formula_mutation_authorized": False,
            },
            {
                "direction_id": "ED-002",
                "domain_id": "DX-02",
                "title": "Within sniff pulse order",
                "origin": "NEW_V2_FRONTIER",
                "current_state": "MISSING_OR_UNDERFORMALIZED",
                "priority": "P1",
                "evidence_ceiling": "DESIGN_ONLY",
                "mechanism_contract": "Compare matched pulse order.",
                "first_discriminator": "Counterbalanced order effect.",
                "failure_mode": "Apparatus artifact.",
                "formula_mutation_authorized": False,
            },
        ],
    }


def test_registry_audit_passes_without_promoting_authority() -> None:
    audit = audit_expansion_registry(_registry(), source_package_sha256=PACKAGE_SHA)
    assert audit.state is ExpansionAuditState.PASS
    assert audit.direction_count == 2
    assert audit.source_admission is False
    assert audit.formula_authority is False
    assert audit.release_authority is False
    assert len(audit.as_dict()["result_sha256"]) == 64


def test_registry_rejects_formula_mutation_and_orphans() -> None:
    registry = _registry()
    registry["directions"][0]["formula_mutation_authorized"] = True
    registry["directions"][1]["domain_id"] = "DX-09"
    audit = audit_expansion_registry(registry, source_package_sha256=PACKAGE_SHA)
    assert audit.state is ExpansionAuditState.HOLD
    assert "ED-001" in audit.invalid_records
    assert audit.orphan_domain_ids == ("DX-09",)


def test_pareto_frontier_is_not_a_scalar_beauty_rank() -> None:
    first = ExpansionDirection.from_mapping(_registry()["directions"][0])
    second = ExpansionDirection.from_mapping(_registry()["directions"][1])
    dominated = ExpansionDirection(
        direction_id="ED-003",
        domain_id="DX-02",
        title="Dominated experiment",
        origin=ExpansionOrigin.FRONTIER,
        current_state="DESIGN",
        priority=ExpansionPriority.P2,
        evidence_ceiling="DESIGN_ONLY",
        mechanism_contract="A bounded mechanism.",
        first_discriminator="A discriminator.",
        failure_mode="A failure.",
    )
    frontier = pareto_experiment_frontier(
        ((first, 0.8, 0.8), (second, 0.6, 0.9), (dominated, 0.3, 0.2))
    )
    assert tuple(item.direction_id for item in frontier) == ("ED-001", "ED-002")


def test_saturation_is_bounded_to_declared_scope_and_reopenable() -> None:
    rounds = (
        ExpansionDiscoveryRound(
            "ROUND-1",
            0,
            ("PROJECT", "PRIMARY"),
            "b" * 64,
        ),
        ExpansionDiscoveryRound(
            "ROUND-2",
            0,
            ("OFFICIAL_STANDARD_OR_GUIDANCE",),
            "c" * 64,
        ),
    )
    result = assess_bounded_saturation(rounds, declared_scope="V2 registry review")
    assert result.state is ExpansionSaturationState.SATURATED_FOR_DECLARED_SCOPE
    assert result.global_exhaustiveness_claim is False
    assert result.release_authority is False
    assert result.as_dict()["reopen_triggers"]


def test_saturation_stays_open_without_source_diversity() -> None:
    rounds = tuple(
        ExpansionDiscoveryRound(f"ROUND-{index}", 0, ("PROJECT",), f"{index}" * 64)
        for index in (1, 2)
    )
    result = assess_bounded_saturation(rounds, declared_scope="local only")
    assert result.state is ExpansionSaturationState.ACTIVE_FRONTIER_REMAINS
    assert result.missing_source_classes == (
        "OFFICIAL_STANDARD_OR_GUIDANCE",
        "PRIMARY",
    )
