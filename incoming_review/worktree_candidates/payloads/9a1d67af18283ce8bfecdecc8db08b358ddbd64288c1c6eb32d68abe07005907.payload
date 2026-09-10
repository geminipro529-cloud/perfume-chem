"""Adversarial tests for bounded external-archive quarantine scans."""

from __future__ import annotations

import hashlib
import io
import json
import struct
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from engine.ingestion import archive_quarantine as quarantine_module
from engine.ingestion.archive_quarantine import (
    scan_archive_graph_quarantine,
    scan_archive_quarantine,
)


def _write_zip(path: Path, members: dict[str, bytes | str]) -> Path:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    return path


def _nested_zip_bytes() -> bytes:
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("child.txt", "child")
    return payload.getvalue()


def _zip_bytes(members: dict[str, bytes | str]) -> bytes:
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        for name, member_payload in members.items():
            archive.writestr(name, member_payload)
    return payload.getvalue()


def _ooxml_members(
    *,
    extra_relationships: str = "",
    extras: dict[str, bytes | str] | None = None,
) -> dict[str, bytes | str]:
    members: dict[str, bytes | str] = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet.main+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="/xl/workbook.xml"/>'
            f"{extra_relationships}"
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'
        ),
    }
    members.update(extras or {})
    return members


def test_clean_zip_is_clear_for_receipt_review_but_never_promoted(
    tmp_path: Path,
) -> None:
    path = _write_zip(
        tmp_path / "clean.zip",
        {"manifest.json": "{}", "payload.csv": "id,value\n1,test\n"},
    )

    result = scan_archive_quarantine(path)

    assert result.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert result.promotion_allowed is False
    assert result.entry_count == 2
    assert result.sampled_bytes > 0
    assert result.nested_archive_members == ()
    assert result.credential_signature_findings == 0
    assert result.findings == ()


def test_nested_zip_requires_independent_child_receipt(tmp_path: Path) -> None:
    path = _write_zip(
        tmp_path / "nested.zip",
        {"manifest.json": "{}", "packages/child.zip": _nested_zip_bytes()},
    )

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert result.promotion_allowed is False
    assert result.nested_archive_members == ("packages/child.zip",)
    assert {finding.code for finding in result.findings} == {
        "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT"
    }


def test_credential_signature_is_redacted(tmp_path: Path) -> None:
    secret = "sk-exampletokenvalue1234567890"
    path = _write_zip(
        tmp_path / "credential.zip",
        {"manifest.json": "{}", ".env": f'API_KEY="{secret}"\n'},
    )

    result = scan_archive_quarantine(path)
    rendered = json.dumps(result.as_dict(), sort_keys=True)

    assert result.status == "QUARANTINE_HOLD"
    assert result.promotion_allowed is False
    assert result.credential_signature_findings >= 1
    assert secret not in rendered
    assert "value redacted" in rendered
    assert "RISKY_CREDENTIAL_FILENAME" in rendered


def test_unsafe_and_normalized_duplicate_members_are_held(tmp_path: Path) -> None:
    path = _write_zip(
        tmp_path / "unsafe.zip",
        {
            "manifest.json": "{}",
            "../escape.txt": "blocked",
            "PAYLOAD.csv": "first",
            "payload.csv": "second",
        },
    )

    result = scan_archive_quarantine(path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "QUARANTINE_HOLD"
    assert result.promotion_allowed is False
    assert "UNSAFE_MEMBER_PATH" in codes
    assert "DUPLICATE_NORMALIZED_MEMBER" in codes


def test_total_sample_budget_exhaustion_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_zip(
        tmp_path / "budget.zip",
        {"one.txt": "1234", "two.txt": "5678"},
    )
    monkeypatch.setattr(quarantine_module, "_MAX_TOTAL_SAMPLE_BYTES", 4)

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert result.promotion_allowed is False
    assert result.sampled_bytes == 4
    assert "TOTAL_SAMPLE_LIMIT_EXCEEDED" in {finding.code for finding in result.findings}


@pytest.mark.parametrize("fixture", ["missing", "bad_zip"])
def test_unreadable_archives_are_fail_closed(tmp_path: Path, fixture: str) -> None:
    path = tmp_path / "unreadable.zip"
    if fixture == "bad_zip":
        path.write_bytes(b"not-a-zip")

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert result.promotion_allowed is False
    assert result.findings[0].code in {"ARCHIVE_MISSING", "ARCHIVE_READ_ERROR"}


def test_unread_member_tail_is_explicitly_held(tmp_path: Path) -> None:
    payload = b"A" * (300 * 1024) + b'API_KEY="tail-secret-value"'
    path = _write_zip(tmp_path / "unread-tail.zip", {"large.txt": payload})

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert "PARTIAL_MEMBER_SCAN" in {finding.code for finding in result.findings}


def test_corrupt_unread_tail_cannot_clear_without_crc_proof(tmp_path: Path) -> None:
    path = tmp_path / "corrupt-tail.zip"
    with ZipFile(path, "w", compression=ZIP_STORED) as archive:
        archive.writestr("large.bin", b"A" * (300 * 1024))
        info = archive.getinfo("large.bin")
        header_offset = info.header_offset
    raw = bytearray(path.read_bytes())
    filename_length, extra_length = struct.unpack_from("<HH", raw, header_offset + 26)
    data_offset = header_offset + 30 + filename_length + extra_length
    raw[data_offset + (280 * 1024)] ^= 0xFF
    path.write_bytes(raw)

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert "PARTIAL_MEMBER_SCAN" in {finding.code for finding in result.findings}


def test_clean_ooxml_is_statically_clear_but_never_promoted(tmp_path: Path) -> None:
    path = _write_zip(tmp_path / "clean.xlsx", _ooxml_members())

    result = scan_archive_quarantine(path)

    assert result.status == "CLEAR_FOR_RECEIPT_REVIEW"
    assert result.promotion_allowed is False
    assert result.ooxml_profile.detected is True
    assert result.ooxml_profile.package_kind == "spreadsheet"
    assert result.ooxml_profile.relationship_parts_scanned == 1
    assert result.ooxml_profile.relationships_scanned == 1
    assert result.ooxml_profile.finding_codes == ()


@pytest.mark.parametrize(
    ("target", "expected_scheme"),
    [
        ("file://server/share/book.xlsx", "file"),
        (r"\\server\share\book.xlsx", "network_path"),
        ("https://example.invalid/private-book.xlsx", "https"),
        ("%66%69%6c%65%3A%2F%2Fserver%2Fshare%2Fbook.xlsx", "file"),
    ],
)
def test_ooxml_external_targets_are_canonicalized_and_redacted(
    tmp_path: Path,
    target: str,
    expected_scheme: str,
) -> None:
    relationship = (
        '<Relationship Id="rIdExternal" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/externalLink" '
        f'Target="{target}" TargetMode="External"/>'
    )
    path = _write_zip(
        tmp_path / "external.xlsx",
        _ooxml_members(extra_relationships=relationship),
    )

    result = scan_archive_quarantine(path)
    rendered = json.dumps(result.as_dict(), sort_keys=True)

    assert result.status == "QUARANTINE_HOLD"
    assert result.ooxml_profile.external_relationships[0].target_scheme == (expected_scheme)
    assert "OOXML_EXTERNAL_RELATIONSHIP" in result.ooxml_profile.finding_codes
    assert target not in rendered
    assert "server/share/book.xlsx" not in rendered


def test_ooxml_internal_root_escape_is_held_and_redacted(tmp_path: Path) -> None:
    members = _ooxml_members()
    members["_rels/.rels"] = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="..%2Fescape.xml"/>'
        "</Relationships>"
    )
    path = _write_zip(tmp_path / "escape.xlsx", members)

    result = scan_archive_quarantine(path)
    rendered = json.dumps(result.as_dict(), sort_keys=True)

    assert result.status == "QUARANTINE_HOLD"
    assert "OOXML_UNSAFE_INTERNAL_RELATIONSHIP" in {finding.code for finding in result.findings}
    assert "escape.xml" not in rendered


@pytest.mark.parametrize(
    "formula",
    [
        'DDE("cmd","/c calc","A1")',
        "[1]Sheet1!A1",
        'WEBSERVICE("https://example.invalid/value")',
    ],
)
def test_ooxml_active_external_formulas_are_held_and_redacted(
    tmp_path: Path,
    formula: str,
) -> None:
    worksheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData><row><c>'
        f"<f>{formula}</f>"
        "</c></row></sheetData></worksheet>"
    )
    path = _write_zip(
        tmp_path / "formula.xlsx",
        _ooxml_members(extras={"xl/worksheets/sheet1.xml": worksheet}),
    )

    result = scan_archive_quarantine(path)
    rendered = json.dumps(result.as_dict(), sort_keys=True)

    assert result.status == "QUARANTINE_HOLD"
    assert result.ooxml_profile.active_formula_parts == ("xl/worksheets/sheet1.xml",)
    assert "OOXML_ACTIVE_EXTERNAL_FORMULA" in result.ooxml_profile.finding_codes
    assert formula not in rendered


@pytest.mark.parametrize(
    ("member", "xml"),
    [
        (
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><definedNames><definedName name="active">'
            'WEBSERVICE("https://example.invalid/workbook")'
            "</definedName></definedNames></workbook>",
        ),
        (
            "xl/charts/chart1.xml",
            '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/'
            'drawingml/2006/chart"><c:chart><c:f>'
            'WEBSERVICE("https://example.invalid/chart")'
            "</c:f></c:chart></c:chartSpace>",
        ),
        (
            "xl/tables/table1.xml",
            '<table xmlns="http://schemas.openxmlformats.org/'
            'spreadsheetml/2006/main"><tableColumns><tableColumn id="1" name="x">'
            '<calculatedColumnFormula>WEBSERVICE("https://example.invalid/table")'
            "</calculatedColumnFormula></tableColumn></tableColumns></table>",
        ),
    ],
)
def test_ooxml_active_formulas_in_nonworksheet_parts_are_held(
    tmp_path: Path,
    member: str,
    xml: str,
) -> None:
    path = _write_zip(
        tmp_path / "formula-surface.xlsx",
        _ooxml_members(extras={member: xml}),
    )

    result = scan_archive_quarantine(path)
    rendered = json.dumps(result.as_dict(), sort_keys=True)

    assert result.status == "QUARANTINE_HOLD"
    assert result.ooxml_profile.active_formula_parts == (member,)
    assert "OOXML_ACTIVE_EXTERNAL_FORMULA" in result.ooxml_profile.finding_codes
    assert "example.invalid" not in rendered


@pytest.mark.parametrize(
    ("member", "expected_code"),
    [
        ("xl/vbaProject.bin", "OOXML_MACRO_CONTENT"),
        ("xl/embeddings/oleObject1.bin", "OOXML_EMBEDDED_OBJECT"),
        ("xl/activeX/activeX1.bin", "OOXML_EMBEDDED_OBJECT"),
        ("xl/connections.xml", "OOXML_EXTERNAL_DATA_PART"),
        ("xl/queryTables/queryTable1.xml", "OOXML_EXTERNAL_DATA_PART"),
        ("_xmlsignatures/sig1.xml", "OOXML_DIGITAL_SIGNATURE"),
        ("EncryptionInfo", "OOXML_ENCRYPTED_PACKAGE"),
    ],
)
def test_ooxml_active_parts_are_held(
    tmp_path: Path,
    member: str,
    expected_code: str,
) -> None:
    path = _write_zip(
        tmp_path / "active.xlsx",
        _ooxml_members(extras={member: b"bounded fixture"}),
    )

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert expected_code in {finding.code for finding in result.findings}


@pytest.mark.parametrize(
    ("relationship_xml", "expected_code"),
    [
        ("<Relationships", "OOXML_RELATIONSHIP_PARSE_ERROR"),
        (
            '<!DOCTYPE x [<!ENTITY y "z">]><Relationships '
            'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
            "OOXML_UNSAFE_XML_DECLARATION",
        ),
        (
            '<Relationships xmlns="urn:untrusted"><Relationship Id="rId1"/></Relationships>',
            "OOXML_UNKNOWN_CONTROL_NAMESPACE",
        ),
        (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="urn:unknown" Target="xl/workbook.xml"/>'
            "</Relationships>",
            "OOXML_UNKNOWN_RELATIONSHIP_TYPE",
        ),
    ],
)
def test_ooxml_control_xml_failures_are_held(
    tmp_path: Path,
    relationship_xml: str,
    expected_code: str,
) -> None:
    members = _ooxml_members()
    members["_rels/.rels"] = relationship_xml
    path = _write_zip(tmp_path / "control.xlsx", members)

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert expected_code in {finding.code for finding in result.findings}


def test_ooxml_control_part_and_depth_limits_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_zip(tmp_path / "bounded.xlsx", _ooxml_members())
    monkeypatch.setattr(quarantine_module, "_MAX_OOXML_PART_BYTES", 64)

    result = scan_archive_quarantine(path)

    assert result.status == "QUARANTINE_HOLD"
    assert "OOXML_PART_SCAN_LIMIT_EXCEEDED" in {finding.code for finding in result.findings}

    monkeypatch.setattr(quarantine_module, "_MAX_OOXML_PART_BYTES", 2 * 1024 * 1024)
    monkeypatch.setattr(quarantine_module, "_MAX_OOXML_XML_DEPTH", 1)
    depth_result = scan_archive_quarantine(path)
    assert "OOXML_XML_RESOURCE_LIMIT_EXCEEDED" in {
        finding.code for finding in depth_result.findings
    }


def test_identical_nested_bytes_are_one_node_with_all_edges(tmp_path: Path) -> None:
    child = _nested_zip_bytes()
    parent_one = _zip_bytes({"first/child.zip": child, "second/child-copy.zip": child})
    parent_two = _zip_bytes({"third/child.zip": child})
    root = _write_zip(
        tmp_path / "root.zip",
        {"parents/one.zip": parent_one, "parents/two.zip": parent_two},
    )

    graph = scan_archive_graph_quarantine(root)

    assert graph.status == "GRAPH_COMPLETE_QUARANTINED"
    assert graph.all_nodes_terminal is True
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 5
    assert graph.resource_usage.unique_containers == 4
    assert graph.resource_usage.edge_candidates_seen == 5
    child_hash = hashlib.sha256(child).hexdigest()
    assert sum(edge.child_sha256 == child_hash for edge in graph.edges) == 3
    assert sum(node.archive_sha256 == child_hash for node in graph.nodes) == 1


@pytest.mark.parametrize(
    ("limit_name", "limit_value", "expected_code"),
    [
        ("_MAX_GRAPH_EDGES", 1, "GRAPH_EDGE_LIMIT_EXCEEDED"),
        ("_MAX_GRAPH_CONTAINERS", 2, "GRAPH_CONTAINER_LIMIT_EXCEEDED"),
        (
            "_MAX_GRAPH_TOTAL_COMPRESSED_BYTES",
            1,
            "GRAPH_COMPRESSED_BYTE_LIMIT_EXCEEDED",
        ),
        (
            "_MAX_GRAPH_TOTAL_DECLARED_BYTES",
            1,
            "GRAPH_DECLARED_BYTE_LIMIT_EXCEEDED",
        ),
        (
            "_MAX_GRAPH_TOTAL_CHILD_BYTES",
            1,
            "GRAPH_CHILD_BYTE_BUDGET_EXCEEDED",
        ),
    ],
)
def test_graph_wide_limits_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    limit_name: str,
    limit_value: int,
    expected_code: str,
) -> None:
    root = _write_zip(
        tmp_path / f"{limit_name}.zip",
        {"one.zip": _nested_zip_bytes(), "two.zip": _zip_bytes({"two.txt": "2"})},
    )
    monkeypatch.setattr(quarantine_module, limit_name, limit_value)

    graph = scan_archive_graph_quarantine(root)

    assert graph.status == "INTEGRITY_HOLD"
    assert graph.all_nodes_terminal is False
    assert expected_code in {finding.code for finding in graph.findings}


def test_graph_depth_limit_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grandchild = _nested_zip_bytes()
    child = _zip_bytes({"grandchild.zip": grandchild})
    root = _write_zip(tmp_path / "depth.zip", {"child.zip": child})
    monkeypatch.setattr(quarantine_module, "_MAX_GRAPH_DEPTH", 1)

    graph = scan_archive_graph_quarantine(root)

    assert graph.status == "INTEGRITY_HOLD"
    assert graph.all_nodes_terminal is False
    assert "GRAPH_DEPTH_LIMIT_EXCEEDED" in {finding.code for finding in graph.findings}


def test_graph_depth_limit_applies_before_duplicate_hash_short_circuit(
    tmp_path: Path,
) -> None:
    shared_child = _nested_zip_bytes()
    deep_parent = _zip_bytes({"duplicate.zip": shared_child})
    for level in range(7, 0, -1):
        deep_parent = _zip_bytes({f"level-{level + 1}.zip": deep_parent})
    root = _write_zip(
        tmp_path / "duplicate-depth.zip",
        {
            "a-direct.zip": shared_child,
            "b-level-1.zip": deep_parent,
        },
    )

    graph = scan_archive_graph_quarantine(root)

    assert graph.status == "INTEGRITY_HOLD"
    assert graph.all_nodes_terminal is False
    assert graph.resource_usage.max_depth == 9
    assert len(graph.nodes) == 10
    assert len(graph.edges) == 10
    assert "GRAPH_DEPTH_LIMIT_EXCEEDED" in {finding.code for finding in graph.findings}


def test_compound_file_office_wrapper_is_named_and_held(tmp_path: Path) -> None:
    path = tmp_path / "opaque.xlsx"
    path.write_bytes(quarantine_module._CFB_MAGIC + (b"\0" * 512))

    result = scan_archive_quarantine(path)
    codes = {finding.code for finding in result.findings}

    assert result.status == "QUARANTINE_HOLD"
    assert "ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER" in codes
    assert "ARCHIVE_READ_ERROR" not in codes
    assert result.ooxml_profile.encryption_parts == ("<compound-file-wrapper>",)
