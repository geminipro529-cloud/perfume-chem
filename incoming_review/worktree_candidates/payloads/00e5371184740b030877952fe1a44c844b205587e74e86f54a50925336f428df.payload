from __future__ import annotations

import hashlib
import json
from pathlib import Path

import engine.ingestion.archive_quarantine as quarantine
from engine.calibration.hashing import stable_file_hash

ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT / "data" / "governance" / "complex_perfumery_v11_embedded_package_census_20260816.json"
)
CAPTURE = (
    ROOT
    / "incoming_review"
    / "chatgpt"
    / "20260815T233019+0700-post-v9-six-package-recovery-6a7992db-n417f58e1"
)
COMPILATION = CAPTURE / "Perfume_Chem_Latest_State_Compilation_2026-08-12_v1.zip"
BRIDGE = (
    CAPTURE / "Perfume_Chem_Cloud_Work_Chat_Latest_State_"
    "PC-LATEST-STATE-SYNC-20260812T103344Z-6153a337.zip"
)


def _load() -> dict[str, object]:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _stable_json_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _graph_sets(graph: quarantine.ArchiveQuarantineGraph) -> tuple[list[dict], list[dict]]:
    nodes = [
        {
            "sha256": node.archive_sha256,
            "display_name": node.display_name,
            "byte_size": node.byte_size,
            "depth": node.depth,
            "terminal": node.terminal,
            "scan_status": node.scan.status,
        }
        for node in graph.nodes
    ]
    edges = [
        {
            "parent_sha256": edge.parent_sha256,
            "member": edge.member,
            "child_sha256": edge.child_sha256,
            "byte_size": edge.byte_size,
        }
        for edge in graph.edges
    ]
    return nodes, edges


def test_v11_report_self_hash_parents_and_authority_are_exact() -> None:
    report = _load()
    unhashed = dict(report)
    declared = unhashed.pop("semantic_self_sha256")
    assert declared == _stable_json_hash(unhashed)

    parents = report["parents"]
    assert parents["compilation"]["sha256"] == stable_file_hash(COMPILATION)
    assert parents["bridge"]["sha256"] == stable_file_hash(BRIDGE)
    assert all(value is False for value in report["authority"].values())
    assert report["admission"]["promotion_allowed"] is False
    assert report["admission"]["source_admission_complete"] is False


def test_v11_preserves_authoritative_default_scanner_holds() -> None:
    report = _load()
    assert quarantine._MAX_CANDIDATE_MEMBER_BYTES == 16 * 1024 * 1024
    assert quarantine._MAX_GRAPH_TOTAL_COMPRESSED_BYTES == 64 * 1024 * 1024
    assert quarantine._MAX_GRAPH_TOTAL_CHILD_BYTES == 128 * 1024 * 1024

    compilation = quarantine.scan_archive_graph_quarantine(COMPILATION)
    bridge = quarantine.scan_archive_graph_quarantine(BRIDGE)
    assert compilation.status == "INTEGRITY_HOLD"
    assert bridge.status == "INTEGRITY_HOLD"
    assert {finding.code for finding in compilation.findings} == {
        "GRAPH_COMPRESSED_BYTE_LIMIT_EXCEEDED"
    }
    assert {finding.code for finding in bridge.findings} == {"GRAPH_CHILD_MEMBER_LIMIT_EXCEEDED"}
    assert report["policy_boundary"]["authoritative_native_states_unchanged"] is True


def test_v11_high_budget_diagnostic_replays_exact_graph_sets() -> None:
    report = _load()
    names = (
        "_MAX_CANDIDATE_MEMBER_BYTES",
        "_MAX_GRAPH_DEPTH",
        "_MAX_GRAPH_CONTAINERS",
        "_MAX_GRAPH_EDGES",
        "_MAX_GRAPH_TOTAL_COMPRESSED_BYTES",
        "_MAX_GRAPH_TOTAL_DECLARED_BYTES",
        "_MAX_GRAPH_TOTAL_CHILD_BYTES",
    )
    original = {name: getattr(quarantine, name) for name in names}
    try:
        quarantine._MAX_CANDIDATE_MEMBER_BYTES = 512 * 1024 * 1024
        quarantine._MAX_GRAPH_DEPTH = 16
        quarantine._MAX_GRAPH_CONTAINERS = 2_048
        quarantine._MAX_GRAPH_EDGES = 50_000
        quarantine._MAX_GRAPH_TOTAL_COMPRESSED_BYTES = 4 * 1024 * 1024 * 1024
        quarantine._MAX_GRAPH_TOTAL_DECLARED_BYTES = 8 * 1024 * 1024 * 1024
        quarantine._MAX_GRAPH_TOTAL_CHILD_BYTES = 8 * 1024 * 1024 * 1024
        graphs = {
            "compilation": quarantine.scan_archive_graph_quarantine(COMPILATION),
            "bridge": quarantine.scan_archive_graph_quarantine(BRIDGE),
        }
    finally:
        for name, value in original.items():
            setattr(quarantine, name, value)

    for key, graph in graphs.items():
        expected = report["diagnostic_results"][key]
        nodes, edges = _graph_sets(graph)
        assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
        assert graph.all_nodes_terminal is True
        assert graph.findings == ()
        assert len(nodes) == expected["node_count"]
        assert len(edges) == expected["edge_count"]
        assert graph.resource_usage.max_depth == expected["max_depth"]
        assert _stable_json_hash(nodes) == expected["node_set_sha256"]
        assert _stable_json_hash(edges) == expected["edge_set_sha256"]

    assert any(
        node.archive_sha256 == "417f58e1e471b62dc7d04b7dc817a64b8b4b1d1fb343bb243f02e95fb7ae3418"
        for node in graphs["bridge"].nodes
    )


def test_v11_unique_container_census_is_hash_bound_and_nonpromoting() -> None:
    report = _load()
    census = report["unique_container_census"]
    assert len(census) == 21
    assert len({row["sha256"] for row in census}) == 21
    assert _stable_json_hash(census) == report["unique_container_census_sha256"]
    assert report["collection_complete"] is False
    assert report["implementation_complete"] is False
    assert report["installation_authorized"] is False
    assert report["residual_holds"] == [
        "UNIVERSAL_ACCORD_EXACT_ORIGINAL_BYTES_UNAVAILABLE_NO_RECONSTRUCTION_OR_SUBSTITUTION",
        "P6_EXACT_ZIP_AND_WHEEL_UNAVAILABLE_NO_SUBSTITUTION",
        "DEFAULT_NATIVE_SCANNER_INTEGRITY_HOLDS_RETAINED",
        "NESTED_CONTAINERS_QUARANTINED_NOT_ADMITTED",
        "SOURCE_RIGHTS_UNKNOWN",
    ]
