from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from engine.formulation_intelligence.accord_graph import (
    MANDATORY_GRAPH_EXCLUSIONS,
    AccordRelationGraph,
    EdgeOrientation,
    EpistemicState,
    GraphEdge,
    GraphNode,
    GraphScope,
    GraphUnknown,
    NodeKind,
    RelationAlternativeSet,
    RelationKind,
    accord_graph_to_plane_assessment,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimCardinality,
    ClaimKind,
    EvidenceClass,
    PlaneId,
    ProvenanceRef,
)


def _source(
    provenance_id: str = "source:brief",
    *,
    evidence_class: EvidenceClass = EvidenceClass.PRIMARY_SOURCE,
) -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id=provenance_id,
        source_ref="Caller-supplied target architecture record",
        evidence_class=evidence_class,
        independence_key=provenance_id,
        source_sha256="a" * 64,
    )


def _scope(*, temporal_scope: str = "heart:30m") -> GraphScope:
    return GraphScope(
        target_scope="Iris Cathedral / v1",
        condition_scope="20 C; ethanol matrix; design condition",
        temporal_scope=temporal_scope,
        matrix_scope="target-ideal; no inventory projection",
    )


def _node(
    node_id: str,
    kind: NodeKind,
    plane_ids: tuple[PlaneId, ...],
    *,
    label: str | None = None,
    scope: GraphScope | None = None,
    state: EpistemicState = EpistemicState.DECLARED,
    authority: AuthorityCeiling = AuthorityCeiling.STRUCTURAL_ONLY,
    unknown_reason: str | None = None,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_kind=kind,
        label=label or node_id,
        scope=scope or _scope(),
        plane_ids=plane_ids,
        epistemic_state=state,
        authority_ceiling=authority,
        provenance_refs=(_source(),),
        unknown_reason=unknown_reason,
    )


def _edge(
    edge_id: str,
    source_id: str,
    target_id: str,
    relation: RelationKind,
    orientation: EdgeOrientation,
    plane_ids: tuple[PlaneId, ...],
    *,
    scope: GraphScope | None = None,
    state: EpistemicState = EpistemicState.DECLARED,
    authority: AuthorityCeiling = AuthorityCeiling.STRUCTURAL_ONLY,
    unknown_reason: str | None = None,
    alternative_group_id: str | None = None,
) -> GraphEdge:
    return GraphEdge(
        edge_id=edge_id,
        source_node_id=source_id,
        target_node_id=target_id,
        relation_kind=relation,
        orientation=orientation,
        scope=scope or _scope(),
        plane_ids=plane_ids,
        epistemic_state=state,
        authority_ceiling=authority,
        provenance_refs=(_source(),),
        rationale=f"Structural candidate relation: {relation.value}",
        unknown_reason=unknown_reason,
        alternative_group_id=alternative_group_id,
    )


def _graph() -> AccordRelationGraph:
    target = _node("node:target", NodeKind.TARGET, (PlaneId.IDENTITY,))
    iris = _node(
        "node:iris",
        NodeKind.MATERIAL_CANDIDATE,
        (PlaneId.IDENTITY, PlaneId.MORPHOLOGY),
    )
    incense = _node(
        "node:incense",
        NodeKind.ACCORD,
        (PlaneId.FUNCTION, PlaneId.MORPHOLOGY),
    )
    smoke = _node("node:smoke", NodeKind.FACET, (PlaneId.MORPHOLOGY,))
    support = _edge(
        "edge:iris-supports-target",
        iris.node_id,
        target.node_id,
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY, PlaneId.MORPHOLOGY),
    )
    bridge = _edge(
        "edge:incense-bridges-iris",
        incense.node_id,
        iris.node_id,
        RelationKind.BRIDGES,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY, PlaneId.MORPHOLOGY, PlaneId.FUNCTION),
    )
    contrast = _edge(
        "edge:smoke-contrasts-iris",
        smoke.node_id,
        iris.node_id,
        RelationKind.CONTRASTS,
        EdgeOrientation.UNDIRECTED,
        (PlaneId.IDENTITY, PlaneId.MORPHOLOGY),
    )
    return AccordRelationGraph(
        graph_id="graph:iris-cathedral:v1",
        scope=_scope(),
        nodes=(target, iris, incense, smoke),
        edges=(support, bridge, contrast),
        alternative_sets=(),
        unknowns=(),
        provenance_refs=(_source(),),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        authority_exclusions=MANDATORY_GRAPH_EXCLUSIONS,
    )


def test_graph_scope_is_exact_normalized_and_immutable() -> None:
    scope = GraphScope(
        target_scope="  Iris  Cathedral / V1 ",
        condition_scope=" 20 C   ethanol ",
        temporal_scope=" Heart 30M ",
        matrix_scope=" TARGET IDEAL ",
    )

    assert scope.key == (
        "iris cathedral / v1",
        "20 c ethanol",
        "heart 30m",
        "target ideal",
    )
    with pytest.raises(FrozenInstanceError):
        scope.target_scope = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("relation", "orientation"),
    (
        (RelationKind.SUPPORTS, EdgeOrientation.UNDIRECTED),
        (RelationKind.BRIDGES, EdgeOrientation.UNDIRECTED),
        (RelationKind.MASKS, EdgeOrientation.UNDIRECTED),
        (RelationKind.SUCCESSION, EdgeOrientation.UNDIRECTED),
        (RelationKind.PERSISTENCE, EdgeOrientation.UNDIRECTED),
        (RelationKind.CONTRASTS, EdgeOrientation.DIRECTED),
        (RelationKind.CONFLICTS, EdgeOrientation.DIRECTED),
        (RelationKind.SHARED_ROLE, EdgeOrientation.DIRECTED),
        (RelationKind.HYPOTHESIS_SYNERGY, EdgeOrientation.DIRECTED),
    ),
)
def test_relation_kinds_enforce_direction_semantics(
    relation: RelationKind,
    orientation: EdgeOrientation,
) -> None:
    with pytest.raises(ValueError, match="orientation"):
        _edge(
            "edge:bad-direction",
            "node:a",
            "node:b",
            relation,
            orientation,
            (PlaneId.RELATION,),
        )


def test_undirected_edges_have_canonical_endpoint_order() -> None:
    edge = _edge(
        "edge:contrast",
        "node:z",
        "node:a",
        RelationKind.CONTRASTS,
        EdgeOrientation.UNDIRECTED,
        (PlaneId.RELATION,),
    )

    assert (edge.source_node_id, edge.target_node_id) == ("node:a", "node:z")


def test_graph_rejects_scope_mismatch_missing_endpoint_and_plane_loss() -> None:
    first = _node("node:first", NodeKind.ACCORD, (PlaneId.FUNCTION,))
    second = _node("node:second", NodeKind.FACET, (PlaneId.MORPHOLOGY,))
    wrong_scope = _node(
        "node:late",
        NodeKind.FACET,
        (PlaneId.MORPHOLOGY,),
        scope=_scope(temporal_scope="drydown:4h"),
    )
    valid = _edge(
        "edge:valid",
        first.node_id,
        second.node_id,
        RelationKind.BRIDGES,
        EdgeOrientation.DIRECTED,
        (PlaneId.FUNCTION, PlaneId.MORPHOLOGY),
    )

    with pytest.raises(ValueError, match="exact graph scope"):
        AccordRelationGraph(
            "graph:scope",
            _scope(),
            (first, second, wrong_scope),
            (valid,),
            (),
            (),
            (_source(),),
            AuthorityCeiling.STRUCTURAL_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )

    missing = _edge(
        "edge:missing",
        first.node_id,
        "node:absent",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.FUNCTION,),
    )
    with pytest.raises(ValueError, match="unknown endpoint"):
        AccordRelationGraph(
            "graph:missing",
            _scope(),
            (first, second),
            (missing,),
            (),
            (),
            (_source(),),
            AuthorityCeiling.STRUCTURAL_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )

    loses_plane = _edge(
        "edge:plane-loss",
        first.node_id,
        second.node_id,
        RelationKind.BRIDGES,
        EdgeOrientation.DIRECTED,
        (PlaneId.FUNCTION,),
    )
    with pytest.raises(ValueError, match="preserve endpoint planes"):
        AccordRelationGraph(
            "graph:plane-loss",
            _scope(),
            (first, second),
            (loses_plane,),
            (),
            (),
            (_source(),),
            AuthorityCeiling.STRUCTURAL_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )


def test_duplicate_ids_and_self_edges_fail_closed() -> None:
    node = _node("node:a", NodeKind.ACCORD, (PlaneId.RELATION,))
    with pytest.raises(ValueError, match="unique node_id"):
        AccordRelationGraph(
            "graph:duplicate",
            _scope(),
            (node, node),
            (),
            (),
            (),
            (_source(),),
            AuthorityCeiling.STRUCTURAL_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )
    with pytest.raises(ValueError, match="distinct endpoints"):
        _edge(
            "edge:self",
            node.node_id,
            node.node_id,
            RelationKind.PERSISTENCE,
            EdgeOrientation.DIRECTED,
            (PlaneId.TEMPORAL,),
        )


def test_unknown_state_is_not_zero_or_silent_certainty() -> None:
    with pytest.raises(ValueError, match="unknown_reason"):
        _node(
            "node:unknown",
            NodeKind.UNKNOWN,
            (PlaneId.RELATION,),
            state=EpistemicState.UNKNOWN,
            authority=AuthorityCeiling.WITHHELD,
        )
    with pytest.raises(ValueError, match="WITHHELD"):
        _node(
            "node:unknown",
            NodeKind.UNKNOWN,
            (PlaneId.RELATION,),
            state=EpistemicState.UNKNOWN,
            authority=AuthorityCeiling.STRUCTURAL_ONLY,
            unknown_reason="Identity is unresolved",
        )

    unknown = GraphUnknown(
        unknown_id="unknown:bridge-identity",
        field_key="bridge.identity",
        scope=_scope(),
        reason="The bridge candidate is not identified",
        needed_evidence="Caller-supplied identity evidence",
        provenance_refs=(_source(),),
    )
    assert "value" not in unknown.as_dict()


def test_hypothesis_synergy_cannot_be_promoted_or_declared_empirical() -> None:
    with pytest.raises(ValueError, match="hypothesis"):
        _edge(
            "edge:synergy",
            "node:a",
            "node:b",
            RelationKind.HYPOTHESIS_SYNERGY,
            EdgeOrientation.UNDIRECTED,
            (PlaneId.RELATION,),
            state=EpistemicState.DECLARED,
            authority=AuthorityCeiling.STRUCTURAL_ONLY,
        )
    with pytest.raises(ValueError, match="HYPOTHESIS_ONLY"):
        _edge(
            "edge:synergy",
            "node:a",
            "node:b",
            RelationKind.HYPOTHESIS_SYNERGY,
            EdgeOrientation.UNDIRECTED,
            (PlaneId.RELATION,),
            state=EpistemicState.HYPOTHESIS,
            authority=AuthorityCeiling.DESIGN_ONLY,
        )


def test_alternatives_are_explicit_and_queryable() -> None:
    nodes = (
        _node("node:target", NodeKind.TARGET, (PlaneId.IDENTITY,)),
        _node("node:a", NodeKind.ACCORD, (PlaneId.IDENTITY,)),
        _node("node:b", NodeKind.ACCORD, (PlaneId.IDENTITY,)),
    )
    edge_a = _edge(
        "edge:a",
        "node:a",
        "node:target",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY,),
        alternative_group_id="alternatives:target-support",
    )
    edge_b = _edge(
        "edge:b",
        "node:b",
        "node:target",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY,),
        alternative_group_id="alternatives:target-support",
    )
    alternatives = RelationAlternativeSet(
        alternative_set_id="alternatives:target-support",
        scope=_scope(),
        edge_ids=(edge_a.edge_id, edge_b.edge_id),
        reason="Two non-collapsed structural candidates",
        provenance_refs=(_source(),),
    )
    graph = AccordRelationGraph(
        "graph:alternatives",
        _scope(),
        nodes,
        (edge_a, edge_b),
        (alternatives,),
        (),
        (_source(),),
        AuthorityCeiling.STRUCTURAL_ONLY,
        MANDATORY_GRAPH_EXCLUSIONS,
    )

    assert graph.alternatives_for_edge("edge:a") == alternatives
    assert graph.alternatives_for_edge("edge:b") == alternatives

    unbound = _edge(
        "edge:unbound",
        "node:a",
        "node:target",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY,),
        alternative_group_id="alternatives:missing",
    )
    with pytest.raises(ValueError, match="alternative group"):
        AccordRelationGraph(
            "graph:bad-alternatives",
            _scope(),
            nodes,
            (unbound,),
            (),
            (),
            (_source(),),
            AuthorityCeiling.STRUCTURAL_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )


def test_queries_preserve_relations_directions_planes_and_conflicts() -> None:
    graph = _graph()

    assert tuple(item.node_id for item in graph.nodes_by_kind(NodeKind.ACCORD)) == (
        "node:incense",
    )
    assert {item.node_id for item in graph.nodes_in_plane(PlaneId.MORPHOLOGY)} == {
        "node:incense",
        "node:iris",
        "node:smoke",
    }
    assert tuple(
        item.edge_id for item in graph.outgoing_edges("node:incense")
    ) == ("edge:incense-bridges-iris",)
    assert tuple(item.edge_id for item in graph.incoming_edges("node:iris")) == (
        "edge:incense-bridges-iris",
        "edge:smoke-contrasts-iris",
    )
    assert {item.node_id for item in graph.neighbors("node:iris")} == {
        "node:incense",
        "node:smoke",
        "node:target",
    }
    assert graph.conflicts_for_node("node:iris") == ()

    conflict = _edge(
        "edge:explicit-conflict",
        "node:iris",
        "node:smoke",
        RelationKind.CONFLICTS,
        EdgeOrientation.UNDIRECTED,
        (PlaneId.IDENTITY, PlaneId.MORPHOLOGY),
    )
    conflicted = AccordRelationGraph(
        "graph:conflict",
        graph.scope,
        graph.nodes,
        (*graph.edges, conflict),
        (),
        (),
        graph.provenance_refs,
        AuthorityCeiling.STRUCTURAL_ONLY,
        MANDATORY_GRAPH_EXCLUSIONS,
    )
    assert conflicted.conflicts_for_node("node:iris") == (conflict,)


def test_reachable_query_respects_directed_edges() -> None:
    graph = _graph()

    assert tuple(item.node_id for item in graph.reachable_from("node:incense")) == (
        "node:iris",
        "node:smoke",
        "node:target",
    )
    assert tuple(item.node_id for item in graph.reachable_from("node:target")) == ()


def test_graph_round_trip_is_strict_versioned_and_hash_stable() -> None:
    graph = _graph()
    payload = graph.as_dict()
    restored = AccordRelationGraph.from_dict(payload)

    assert restored == graph
    assert restored.content_sha256 == graph.content_sha256
    assert payload["schema_version"] == "formulation_accord_relation_graph_v1"
    assert "score" not in payload
    assert "weight" not in payload

    extra = dict(payload)
    extra["aggregate_score"] = 1.0
    with pytest.raises(ValueError, match="closed schema"):
        AccordRelationGraph.from_dict(extra)
    stale = dict(payload)
    stale["schema_version"] = "formulation_accord_relation_graph_v0"
    with pytest.raises(ValueError, match="schema_version"):
        AccordRelationGraph.from_dict(stale)


def test_caller_records_adapter_never_imports_or_reads_legacy_graph() -> None:
    graph = _graph()
    restored = AccordRelationGraph.from_caller_records(
        graph_id=graph.graph_id,
        scope_record=graph.scope.as_dict(),
        node_records=tuple(item.as_dict() for item in graph.nodes),
        edge_records=tuple(item.as_dict() for item in graph.edges),
        alternative_records=(),
        unknown_records=(),
        provenance_records=tuple(item.as_dict() for item in graph.provenance_refs),
        authority_ceiling=graph.authority_ceiling.value,
        authority_exclusions=graph.authority_exclusions,
    )

    assert restored == graph


def test_authority_exclusions_and_ceiling_fail_closed() -> None:
    graph = _graph()
    assert set(MANDATORY_GRAPH_EXCLUSIONS).issubset(graph.authority_exclusions)
    weakened_exclusions = tuple(
        item for item in MANDATORY_GRAPH_EXCLUSIONS if item != "smell inference"
    )
    with pytest.raises(ValueError, match="mandatory authority exclusions"):
        AccordRelationGraph(
            graph.graph_id,
            graph.scope,
            graph.nodes,
            graph.edges,
            graph.alternative_sets,
            graph.unknowns,
            graph.provenance_refs,
            graph.authority_ceiling,
            weakened_exclusions,
        )
    with pytest.raises(ValueError, match="authority ceiling"):
        AccordRelationGraph(
            graph.graph_id,
            graph.scope,
            graph.nodes,
            graph.edges,
            graph.alternative_sets,
            graph.unknowns,
            graph.provenance_refs,
            AuthorityCeiling.DESIGN_ONLY,
            MANDATORY_GRAPH_EXCLUSIONS,
        )


def test_relation_plane_adapter_preserves_exact_semantic_scope_and_records() -> None:
    graph = _graph()

    assessment = accord_graph_to_plane_assessment(graph)

    assert assessment == graph.to_plane_assessment()
    assert assessment.plane_id is PlaneId.RELATION
    assert assessment.scope.target_scope == graph.scope.target_scope
    assert assessment.scope.temporal_scope == graph.scope.temporal_scope
    assert assessment.scope.matrix_scope == graph.scope.matrix_scope
    assert assessment.module_id == "accord-relation-graph-v1"
    assert assessment.support_intervals == ()
    assert assessment.native_criteria == ()
    assert assessment.proposed_experiments == ()
    assert set(assessment.provenance_refs) == set(graph.provenance_refs)
    assert graph.content_sha256 in assessment.freshness_hashes

    graph_claims = [
        claim for claim in assessment.claims if claim.claim_key == "relation.graph"
    ]
    node_claims = [
        claim for claim in assessment.claims if claim.claim_key == "relation.node"
    ]
    edge_claims = [
        claim for claim in assessment.claims if claim.claim_key.startswith("relation.edge.")
    ]
    exclusion_claims = [
        claim
        for claim in assessment.claims
        if claim.claim_key == "relation.authority_exclusion"
    ]
    assert len(graph_claims) == 1
    assert len(node_claims) == len(graph.nodes)
    assert len(edge_claims) == len(graph.edges)
    assert len(exclusion_claims) == len(graph.authority_exclusions)
    assert all(
        claim.cardinality is ClaimCardinality.SET_MEMBER
        for claim in (*node_claims, *edge_claims, *exclusion_claims)
    )
    assert {json.loads(claim.claim_value)["node_id"] for claim in node_claims} == {
        node.node_id for node in graph.nodes
    }
    assert {json.loads(claim.claim_value)["relation_kind"] for claim in edge_claims} == {
        edge.relation_kind.value for edge in graph.edges
    }
    graph_payload = json.loads(graph_claims[0].claim_value)
    assert graph_payload["scope"]["condition_scope"] == graph.scope.condition_scope


def test_relation_plane_adapter_preserves_alternatives_conflicts_and_unknowns() -> None:
    source = _source()
    nodes = (
        _node("node:target", NodeKind.TARGET, (PlaneId.IDENTITY,)),
        _node("node:a", NodeKind.ACCORD, (PlaneId.RELATION,)),
        _node("node:b", NodeKind.ACCORD, (PlaneId.RELATION,)),
        _node(
            "node:unknown",
            NodeKind.UNKNOWN,
            (PlaneId.RELATION,),
            state=EpistemicState.UNKNOWN,
            authority=AuthorityCeiling.WITHHELD,
            unknown_reason="Candidate identity is unresolved",
        ),
    )
    edge_a = _edge(
        "edge:a",
        "node:a",
        "node:target",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY, PlaneId.RELATION),
        alternative_group_id="alternatives:support",
    )
    edge_b = _edge(
        "edge:b",
        "node:b",
        "node:target",
        RelationKind.SUPPORTS,
        EdgeOrientation.DIRECTED,
        (PlaneId.IDENTITY, PlaneId.RELATION),
        alternative_group_id="alternatives:support",
    )
    conflict = _edge(
        "edge:conflict",
        "node:a",
        "node:b",
        RelationKind.CONFLICTS,
        EdgeOrientation.UNDIRECTED,
        (PlaneId.RELATION,),
    )
    alternatives = RelationAlternativeSet(
        alternative_set_id="alternatives:support",
        scope=_scope(),
        edge_ids=(edge_a.edge_id, edge_b.edge_id),
        reason="Keep both support hypotheses",
        provenance_refs=(source,),
    )
    graph_unknown = GraphUnknown(
        unknown_id="unknown:relation-resolution",
        field_key="relation.resolution",
        scope=_scope(),
        reason="The competing relation has not been resolved",
        needed_evidence="Exact-scope controlled comparison",
        provenance_refs=(source,),
    )
    graph = AccordRelationGraph(
        "graph:rich",
        _scope(),
        nodes,
        (edge_a, edge_b, conflict),
        (alternatives,),
        (graph_unknown,),
        (source,),
        AuthorityCeiling.STRUCTURAL_ONLY,
        MANDATORY_GRAPH_EXCLUSIONS,
    )

    assessment = graph.to_plane_assessment()

    alternative_claims = tuple(
        claim
        for claim in assessment.claims
        if claim.claim_key == "relation.alternative_set"
    )
    assert len(alternative_claims) == 1
    assert json.loads(alternative_claims[0].claim_value)["edge_ids"] == [
        "edge:a",
        "edge:b",
    ]
    assert len(assessment.conflicts) == 1
    assert assessment.conflicts[0].claim_key == "relation.edge.conflicts"
    assert assessment.conflicts[0].alternatives == ("node:a", "node:b")
    assert set(assessment.conflicts[0].claim_ids) == {
        "relation-edge-edge-conflict",
        "relation-node-node-a",
        "relation-node-node-b",
    }
    unknown_by_field = {item.field_key: item for item in assessment.unknowns}
    assert "relation.resolution" in unknown_by_field
    assert "relation.node.node:unknown" in unknown_by_field
    assert unknown_by_field["relation.resolution"].needed_evidence == (
        "Exact-scope controlled comparison"
    )


def test_relation_plane_adapter_keeps_synergy_hypothetical() -> None:
    nodes = (
        _node("node:a", NodeKind.ACCORD, (PlaneId.RELATION,)),
        _node("node:b", NodeKind.ACCORD, (PlaneId.RELATION,)),
    )
    synergy = _edge(
        "edge:synergy",
        "node:a",
        "node:b",
        RelationKind.HYPOTHESIS_SYNERGY,
        EdgeOrientation.UNDIRECTED,
        (PlaneId.RELATION,),
        state=EpistemicState.HYPOTHESIS,
        authority=AuthorityCeiling.STRUCTURAL_ONLY,
    )
    graph = AccordRelationGraph(
        "graph:synergy",
        _scope(),
        nodes,
        (synergy,),
        (),
        (),
        (_source(),),
        AuthorityCeiling.STRUCTURAL_ONLY,
        MANDATORY_GRAPH_EXCLUSIONS,
    )

    claim = next(
        item
        for item in graph.to_plane_assessment().claims
        if item.claim_key == "relation.edge.hypothesis_synergy"
    )
    assert claim.claim_kind is ClaimKind.HYPOTHESIS
    assert claim.authority_ceiling.is_no_stronger_than(
        AuthorityCeiling.HYPOTHESIS_ONLY
    )


def test_relation_plane_adapter_fails_closed_on_missing_evidence() -> None:
    unknown_source = ProvenanceRef(
        provenance_id="source:unbound",
        source_ref="Caller declaration with no bound artifact",
        evidence_class=EvidenceClass.UNKNOWN,
        independence_key="source:unbound",
        source_sha256=None,
    )
    scope = _scope()
    nodes = (
        GraphNode(
            node_id="node:a",
            node_kind=NodeKind.ACCORD,
            label="Unbound accord candidate",
            scope=scope,
            plane_ids=(PlaneId.RELATION,),
            epistemic_state=EpistemicState.HYPOTHESIS,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(unknown_source,),
        ),
        GraphNode(
            node_id="node:b",
            node_kind=NodeKind.ACCORD,
            label="Second unbound accord candidate",
            scope=scope,
            plane_ids=(PlaneId.RELATION,),
            epistemic_state=EpistemicState.HYPOTHESIS,
            authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
            provenance_refs=(unknown_source,),
        ),
    )
    edge = GraphEdge(
        edge_id="edge:unbound",
        source_node_id="node:a",
        target_node_id="node:b",
        relation_kind=RelationKind.BRIDGES,
        orientation=EdgeOrientation.DIRECTED,
        scope=scope,
        plane_ids=(PlaneId.RELATION,),
        epistemic_state=EpistemicState.HYPOTHESIS,
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        provenance_refs=(unknown_source,),
        rationale="Unbound bridge hypothesis",
    )
    graph = AccordRelationGraph(
        "graph:unbound",
        scope,
        nodes,
        (edge,),
        (),
        (),
        (unknown_source,),
        AuthorityCeiling.STRUCTURAL_ONLY,
        MANDATORY_GRAPH_EXCLUSIONS,
    )

    assessment = graph.to_plane_assessment()

    assert assessment.authority_ceiling is AuthorityCeiling.WITHHELD
    assert all(
        claim.authority_ceiling is AuthorityCeiling.WITHHELD
        for claim in assessment.claims
    )
    assert any(item.startswith("HOLD:") for item in assessment.failure_modes)
    assert any(item.field_key == "relation.evidence" for item in assessment.unknowns)
    assert assessment.support_intervals == ()
    assert assessment.native_criteria == ()


def test_relation_plane_adapter_is_deterministic() -> None:
    graph = _graph()

    first = graph.to_plane_assessment()
    second = AccordRelationGraph.from_dict(graph.as_dict()).to_plane_assessment()

    assert first == second
    assert first.content_sha256 == second.content_sha256
