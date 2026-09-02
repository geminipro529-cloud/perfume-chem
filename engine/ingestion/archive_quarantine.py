"""Bounded, read-only quarantine inspection for untrusted ZIP containers.

``scan_archive_quarantine`` inspects one container without extraction or
recursion. ``scan_archive_graph_quarantine`` additionally walks bounded nested
ZIP/OOXML bytes in memory, deduplicates containers by SHA-256, and still never
imports records or grants authority.
"""

from __future__ import annotations

import hashlib
import io
import re
import stat
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile, ZipInfo

from engine.calibration.hashing import stable_file_hash
from engine.ingestion.package_receipts import (
    ExternalPackageReceiptError,
    _archive_collision_key,
    _safe_archive_member,
)

_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_CANDIDATE_MEMBER_BYTES = 16 * 1024 * 1024
_MAX_MEMBER_SAMPLE_BYTES = 256 * 1024
_MAX_TOTAL_SAMPLE_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 1_000

_MAX_OOXML_PART_BYTES = 2 * 1024 * 1024
_MAX_OOXML_RELATIONSHIP_PARTS = 1_000
_MAX_OOXML_RELATIONSHIPS = 10_000
_MAX_OOXML_XML_ELEMENTS = 50_000
_MAX_OOXML_XML_DEPTH = 128

_MAX_GRAPH_DEPTH = 8
_MAX_GRAPH_CONTAINERS = 256
_MAX_GRAPH_EDGES = 4_096
_MAX_GRAPH_TOTAL_COMPRESSED_BYTES = 64 * 1024 * 1024
_MAX_GRAPH_TOTAL_DECLARED_BYTES = 128 * 1024 * 1024
_MAX_GRAPH_TOTAL_CHILD_BYTES = 128 * 1024 * 1024

_NESTED_ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tar.zst",
    ".7z",
    ".rar",
)
_OOXML_SUFFIXES = (
    ".xlsx",
    ".xlsm",
    ".xltx",
    ".xltm",
    ".docx",
    ".docm",
    ".dotx",
    ".dotm",
    ".pptx",
    ".pptm",
    ".potx",
    ".potm",
    ".ppsx",
    ".ppsm",
)
_OOXML_MACRO_SUFFIXES = (
    ".xlsm",
    ".xltm",
    ".docm",
    ".dotm",
    ".pptm",
    ".potm",
    ".ppsm",
)
_ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_CFB_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_OOXML_RELATIONSHIP_NAMESPACES = {
    "http://schemas.openxmlformats.org/package/2006/relationships",
    "http://purl.oclc.org/ooxml/package/relationships",
}
_OOXML_CONTENT_TYPE_NAMESPACES = {
    "http://schemas.openxmlformats.org/package/2006/content-types",
    "http://purl.oclc.org/ooxml/package/content-types",
}
_SAFE_RELATIONSHIP_TYPE_TAILS = {
    "calcchain",
    "chart",
    "chartsheet",
    "comments",
    "core-properties",
    "custom-properties",
    "customxml",
    "customxmlprops",
    "dialogsheet",
    "drawing",
    "extended-properties",
    "featurepropertybag",
    "font",
    "glossarydocument",
    "image",
    "notesmaster",
    "notesslide",
    "numbering",
    "officedocument",
    "person",
    "pivotcachedefinition",
    "pivotcacherecords",
    "pivottable",
    "presprops",
    "printersettings",
    "sharedstrings",
    "sheetmetadata",
    "slide",
    "slidelayout",
    "slidemaster",
    "styles",
    "table",
    "tabledefinition",
    "theme",
    "themeoverride",
    "thumbnail",
    "viewprops",
    "websettings",
    "worksheet",
}
_ACTIVE_FORMULA_FUNCTION = re.compile(
    r"(?:^|[^A-Z0-9_.])"
    r"(?:DDE|RTD|WEBSERVICE|FILTERXML|HYPERLINK|CALL|REGISTER\.ID)\s*\(",
    re.IGNORECASE,
)
_EXTERNAL_WORKBOOK_FORMULA = re.compile(
    r"(?:'[^']*')?\[(?:\d+|[^\]\r\n]+\.(?:xlsx?|xlsm|xlsb|ods|csv))\][^!\r\n]*!",
    re.IGNORECASE,
)
_COMMAND_DDE_FORMULA = re.compile(
    r"(?:^|[=+\-@])\s*(?:CMD|POWERSHELL|WSCRIPT|CSCRIPT)\s*\|",
    re.IGNORECASE,
)
_RISKY_FILENAMES = re.compile(
    rb"(?:^\.env(?:[._-].*)?$|(?:^|[._-])"
    rb"(?:credentials?|secrets?|private[_-]?key|id_rsa)(?:[._-]|$))",
    re.IGNORECASE,
)
_CREDENTIAL_SIGNATURES: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "CREDENTIAL_SIGNATURE_PRIVATE_KEY",
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "CREDENTIAL_SIGNATURE_BEARER",
        re.compile(
            rb"authorization\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._~-]{12,}",
            re.IGNORECASE,
        ),
    ),
    (
        "CREDENTIAL_SIGNATURE_ASSIGNMENT",
        re.compile(
            rb"(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)"
            rb"\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']",
            re.IGNORECASE,
        ),
    ),
    (
        "CREDENTIAL_SIGNATURE_TOKEN_PREFIX",
        re.compile(rb"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    ),
)


@dataclass(frozen=True, slots=True)
class ArchiveQuarantineFinding:
    """One value-redacted reason to retain quarantine."""

    code: str
    member: str | None
    detail: str

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "member": self.member, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class OOXMLExternalRelationship:
    """A redacted external OOXML relationship descriptor."""

    relationship_part: str
    relationship_type: str
    target_scheme: str

    def as_dict(self) -> dict[str, str]:
        return {
            "relationship_part": self.relationship_part,
            "relationship_type": self.relationship_type,
            "target_scheme": self.target_scheme,
        }


@dataclass(frozen=True, slots=True)
class OOXMLQuarantineProfile:
    """Static OOXML risk profile; authority is false by construction."""

    detected: bool
    package_kind: str | None
    macro_enabled_format: bool
    relationship_parts_scanned: int
    relationships_scanned: int
    external_relationships: tuple[OOXMLExternalRelationship, ...]
    macro_parts: tuple[str, ...]
    embedded_object_parts: tuple[str, ...]
    external_data_parts: tuple[str, ...]
    active_formula_parts: tuple[str, ...]
    signature_parts: tuple[str, ...]
    encryption_parts: tuple[str, ...]
    finding_codes: tuple[str, ...]
    promotion_allowed: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "package_kind": self.package_kind,
            "macro_enabled_format": self.macro_enabled_format,
            "relationship_parts_scanned": self.relationship_parts_scanned,
            "relationships_scanned": self.relationships_scanned,
            "external_relationships": [
                relationship.as_dict() for relationship in self.external_relationships
            ],
            "macro_parts": list(self.macro_parts),
            "embedded_object_parts": list(self.embedded_object_parts),
            "external_data_parts": list(self.external_data_parts),
            "active_formula_parts": list(self.active_formula_parts),
            "signature_parts": list(self.signature_parts),
            "encryption_parts": list(self.encryption_parts),
            "finding_codes": list(self.finding_codes),
            "promotion_allowed": self.promotion_allowed,
        }


@dataclass(frozen=True, slots=True)
class ArchiveQuarantineScan:
    """Immutable single-container evidence; promotion is always false."""

    status: str
    archive_sha256: str
    entry_count: int
    sampled_bytes: int
    package_root: str | None
    nested_archive_members: tuple[str, ...]
    credential_signature_findings: int
    ooxml_profile: OOXMLQuarantineProfile
    findings: tuple[ArchiveQuarantineFinding, ...]
    promotion_allowed: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "archive_sha256": self.archive_sha256,
            "entry_count": self.entry_count,
            "sampled_bytes": self.sampled_bytes,
            "package_root": self.package_root,
            "nested_archive_members": list(self.nested_archive_members),
            "credential_signature_findings": self.credential_signature_findings,
            "ooxml_profile": self.ooxml_profile.as_dict(),
            "findings": [finding.as_dict() for finding in self.findings],
            "promotion_allowed": self.promotion_allowed,
        }


@dataclass(frozen=True, slots=True)
class ArchiveContainerEdge:
    """One bounded parent/member/child relationship in a container graph."""

    parent_sha256: str
    member: str
    child_sha256: str
    byte_size: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "parent_sha256": self.parent_sha256,
            "member": self.member,
            "child_sha256": self.child_sha256,
            "byte_size": self.byte_size,
        }


@dataclass(frozen=True, slots=True)
class ArchiveContainerNode:
    """One unique SHA-addressed container and its terminal static scan."""

    archive_sha256: str
    display_name: str
    byte_size: int
    media_type: str
    depth: int
    terminal: bool
    scan: ArchiveQuarantineScan

    def as_dict(self) -> dict[str, Any]:
        return {
            "archive_sha256": self.archive_sha256,
            "display_name": self.display_name,
            "byte_size": self.byte_size,
            "media_type": self.media_type,
            "depth": self.depth,
            "terminal": self.terminal,
            "scan": self.scan.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class ArchiveGraphResourceLimits:
    """The exact finite bounds used for one graph scan."""

    max_depth: int
    max_unique_containers: int
    max_edges: int
    max_compressed_bytes: int
    max_declared_bytes: int
    max_child_bytes_read: int

    def as_dict(self) -> dict[str, int]:
        return {
            "max_depth": self.max_depth,
            "max_unique_containers": self.max_unique_containers,
            "max_edges": self.max_edges,
            "max_compressed_bytes": self.max_compressed_bytes,
            "max_declared_bytes": self.max_declared_bytes,
            "max_child_bytes_read": self.max_child_bytes_read,
        }


@dataclass(frozen=True, slots=True)
class ArchiveGraphResourceUsage:
    """Observed graph traversal costs, including duplicate provenance edges."""

    max_depth: int
    unique_containers: int
    edge_candidates_seen: int
    compressed_bytes_seen: int
    declared_bytes_seen: int
    child_bytes_read: int

    def as_dict(self) -> dict[str, int]:
        return {
            "max_depth": self.max_depth,
            "unique_containers": self.unique_containers,
            "edge_candidates_seen": self.edge_candidates_seen,
            "compressed_bytes_seen": self.compressed_bytes_seen,
            "declared_bytes_seen": self.declared_bytes_seen,
            "child_bytes_read": self.child_bytes_read,
        }


@dataclass(frozen=True, slots=True)
class ArchiveQuarantineGraph:
    """Deduplicated, bounded graph evidence; promotion is always false."""

    status: str
    root_archive_sha256: str
    nodes: tuple[ArchiveContainerNode, ...]
    edges: tuple[ArchiveContainerEdge, ...]
    all_nodes_terminal: bool
    resource_limits: ArchiveGraphResourceLimits
    resource_usage: ArchiveGraphResourceUsage
    findings: tuple[ArchiveQuarantineFinding, ...]
    promotion_allowed: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "root_archive_sha256": self.root_archive_sha256,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "all_nodes_terminal": self.all_nodes_terminal,
            "resource_limits": self.resource_limits.as_dict(),
            "resource_usage": self.resource_usage.as_dict(),
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "findings": [finding.as_dict() for finding in self.findings],
            "promotion_allowed": self.promotion_allowed,
        }


@dataclass(frozen=True, slots=True)
class _NestedCandidate:
    member: str
    declared_size: int
    compressed_size: int
    payload: bytes | None
    unresolved_code: str | None = None


@dataclass(frozen=True, slots=True)
class _ContainerWork:
    scan: ArchiveQuarantineScan
    nested_candidates: tuple[_NestedCandidate, ...]


@dataclass(frozen=True, slots=True)
class _QueuedContainer:
    payload: bytes | None
    path: Path | None
    archive_sha256: str
    display_name: str
    byte_size: int
    depth: int


def _finding(
    findings: list[ArchiveQuarantineFinding],
    code: str,
    member: str | None,
    detail: str,
) -> None:
    findings.append(ArchiveQuarantineFinding(code=code, member=member, detail=detail))


def _finding_once(
    findings: list[ArchiveQuarantineFinding],
    code: str,
    member: str | None,
    detail: str,
) -> None:
    if any(finding.code == code and finding.member == member for finding in findings):
        return
    _finding(findings, code, member, detail)


def _empty_ooxml_profile() -> OOXMLQuarantineProfile:
    return OOXMLQuarantineProfile(
        detected=False,
        package_kind=None,
        macro_enabled_format=False,
        relationship_parts_scanned=0,
        relationships_scanned=0,
        external_relationships=(),
        macro_parts=(),
        embedded_object_parts=(),
        external_data_parts=(),
        active_formula_parts=(),
        signature_parts=(),
        encryption_parts=(),
        finding_codes=(),
    )


def _result(
    *,
    archive_sha256: str,
    entry_count: int,
    sampled_bytes: int,
    package_root: str | None,
    nested_archive_members: list[str],
    ooxml_profile: OOXMLQuarantineProfile,
    findings: list[ArchiveQuarantineFinding],
) -> ArchiveQuarantineScan:
    return ArchiveQuarantineScan(
        status="QUARANTINE_HOLD" if findings else "CLEAR_FOR_RECEIPT_REVIEW",
        archive_sha256=archive_sha256,
        entry_count=entry_count,
        sampled_bytes=sampled_bytes,
        package_root=package_root,
        nested_archive_members=tuple(nested_archive_members),
        credential_signature_findings=sum(
            finding.code.startswith("CREDENTIAL_SIGNATURE_") for finding in findings
        ),
        ooxml_profile=ooxml_profile,
        findings=tuple(findings),
    )


def _package_root(members: list[str]) -> str | None:
    roots = {
        PurePosixPath(member).parts[0] for member in members if len(PurePosixPath(member).parts) > 1
    }
    if len(roots) != 1:
        return None
    root = next(iter(roots))
    if any(
        len(PurePosixPath(member).parts) < 2 or PurePosixPath(member).parts[0] != root
        for member in members
    ):
        return None
    return root


def _ooxml_package_kind(
    display_name: str,
    content_types: tuple[str, ...] = (),
) -> str:
    lower_name = display_name.casefold()
    lower_types = " ".join(content_types).casefold()
    if lower_name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")) or (
        "spreadsheetml" in lower_types
    ):
        return "spreadsheet"
    if lower_name.endswith((".docx", ".docm", ".dotx", ".dotm")) or (
        "wordprocessingml" in lower_types
    ):
        return "wordprocessing"
    if (
        lower_name.endswith((".pptx", ".pptm", ".potx", ".potm", ".ppsx", ".ppsm"))
        or "presentationml" in lower_types
    ):
        return "presentation"
    return "generic_opc"


def _relationship_type_category(relationship_type: str) -> str:
    lower = relationship_type.casefold()
    tail = lower.rstrip("/").rsplit("/", 1)[-1]
    if "vbaproject" in lower or "macro" in lower:
        return "macro"
    if "oleobject" in lower:
        return "ole_object"
    if "activex" in lower:
        return "activex"
    if lower.endswith("/package"):
        return "embedded_package"
    if "digital-signature" in lower:
        return "digital_signature"
    if "externallink" in lower or "connection" in lower or "querytable" in lower:
        return "external_data"
    if lower.endswith("/hyperlink"):
        return "hyperlink"
    if tail in _SAFE_RELATIONSHIP_TYPE_TAILS:
        return "safe_internal"
    return "other"


def _target_scheme(target: str) -> str:
    canonical_target = unquote(target)
    parsed = urlsplit(canonical_target)
    scheme = parsed.scheme.casefold()
    if re.fullmatch(r"[a-z][a-z0-9+.-]{0,15}", scheme):
        return scheme
    if parsed.netloc or canonical_target.startswith(("//", "\\\\")):
        return "network_path"
    return "relative" if not scheme else "unknown"


def _xml_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _parse_ooxml_xml(
    payload: bytes,
    *,
    member: str,
    parse_error_code: str,
    expected_namespaces: set[str],
    findings: list[ArchiveQuarantineFinding],
) -> ElementTree.Element | None:
    upper_payload = payload.upper()
    if b"<!DOCTYPE" in upper_payload or b"<!ENTITY" in upper_payload:
        _finding_once(
            findings,
            "OOXML_UNSAFE_XML_DECLARATION",
            member,
            "OOXML control XML contains a prohibited declaration.",
        )
        return None
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        _finding_once(
            findings,
            parse_error_code,
            member,
            "OOXML control XML could not be parsed safely.",
        )
        return None

    namespace = _xml_namespace(root.tag)
    if expected_namespaces and namespace not in expected_namespaces:
        _finding_once(
            findings,
            "OOXML_UNKNOWN_CONTROL_NAMESPACE",
            member,
            "OOXML control XML uses an unrecognized namespace.",
        )
        return None

    element_count = 0
    stack: list[tuple[ElementTree.Element, int]] = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        element_count += 1
        if element_count > _MAX_OOXML_XML_ELEMENTS or depth > _MAX_OOXML_XML_DEPTH:
            _finding_once(
                findings,
                "OOXML_XML_RESOURCE_LIMIT_EXCEEDED",
                member,
                "OOXML control XML exceeds the element or depth bound.",
            )
            return None
        stack.extend((child, depth + 1) for child in element)
    return root


def _relationship_source_base(relationship_part: str) -> PurePosixPath | None:
    part = PurePosixPath(relationship_part)
    if relationship_part.casefold() == "_rels/.rels":
        return PurePosixPath()
    if part.parent.name.casefold() != "_rels" or not part.name.endswith(".rels"):
        return None
    source_name = part.name[: -len(".rels")]
    return (part.parent.parent / source_name).parent


def _resolve_internal_relationship_target(
    relationship_part: str,
    target: str,
) -> str | None:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or "\\" in target:
        return None
    decoded_path = unquote(parsed.path)
    if not decoded_path and parsed.fragment:
        return ""
    if not decoded_path or decoded_path.startswith("//"):
        return None
    base: PurePosixPath | None
    if decoded_path.startswith("/"):
        base = PurePosixPath()
        decoded_path = decoded_path.lstrip("/")
    else:
        base = _relationship_source_base(relationship_part)
        if base is None:
            return None
    parts = list(base.parts)
    for part in PurePosixPath(decoded_path).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        if part in ("/", "\\") or ":" in part:
            return None
        parts.append(part)
    return PurePosixPath(*parts).as_posix() if parts else ""


def _categorize_ooxml_part(
    member: str,
    *,
    macro_parts: set[str],
    embedded_parts: set[str],
    external_data_parts: set[str],
    signature_parts: set[str],
    encryption_parts: set[str],
    findings: list[ArchiveQuarantineFinding],
) -> None:
    lower = f"/{member.casefold().lstrip('/')}"
    if (
        lower.endswith("/vbaproject.bin")
        or "/macrosheets/" in lower
        or "/intlmacrosheets/" in lower
        or lower.endswith("/vbadata.xml")
    ):
        macro_parts.add(member)
        _finding_once(
            findings,
            "OOXML_MACRO_CONTENT",
            member,
            "OOXML macro-capable content requires quarantine review.",
        )
    if "/embeddings/" in lower or "/activex/" in lower:
        embedded_parts.add(member)
        _finding_once(
            findings,
            "OOXML_EMBEDDED_OBJECT",
            member,
            "OOXML embedded or ActiveX content requires quarantine review.",
        )
    if "/externallinks/" in lower or lower.endswith("/connections.xml") or "/querytables/" in lower:
        external_data_parts.add(member)
        _finding_once(
            findings,
            "OOXML_EXTERNAL_DATA_PART",
            member,
            "OOXML external-data content requires quarantine review.",
        )
    if "/_xmlsignatures/" in lower:
        signature_parts.add(member)
        _finding_once(
            findings,
            "OOXML_DIGITAL_SIGNATURE",
            member,
            "OOXML signature content requires explicit trust review.",
        )
    if (
        lower.endswith("/encryptedpackage")
        or lower.endswith("/encryptioninfo")
        or "/dataspaces/" in lower
    ):
        encryption_parts.add(member)
        _finding_once(
            findings,
            "OOXML_ENCRYPTED_PACKAGE",
            member,
            "Encrypted OOXML content cannot be inspected statically.",
        )


def _inspect_ooxml(
    archive: ZipFile,
    infos_by_member: dict[str, ZipInfo],
    inspected_sizes: dict[str, int],
    display_name: str,
    sampled_bytes: int,
    findings: list[ArchiveQuarantineFinding],
) -> tuple[OOXMLQuarantineProfile, int]:
    lower_to_member = {member.casefold(): member for member in infos_by_member}
    content_types_member = lower_to_member.get("[content_types].xml")
    root_relationship_member = lower_to_member.get("_rels/.rels")
    suffix_claims_ooxml = display_name.casefold().endswith(_OOXML_SUFFIXES)
    detected = bool(content_types_member and root_relationship_member) or (suffix_claims_ooxml)
    if not detected:
        return _empty_ooxml_profile(), sampled_bytes

    ooxml_finding_start = len(findings)
    macro_parts: set[str] = set()
    embedded_parts: set[str] = set()
    external_data_parts: set[str] = set()
    active_formula_parts: set[str] = set()
    signature_parts: set[str] = set()
    encryption_parts: set[str] = set()
    external_relationships: list[OOXMLExternalRelationship] = []
    content_types: list[str] = []
    relationship_parts_scanned = 0
    relationships_scanned = 0

    if not content_types_member or not root_relationship_member:
        _finding_once(
            findings,
            "OOXML_PACKAGE_STRUCTURE_MISSING",
            None,
            "OOXML extension is present but required OPC roots are missing.",
        )

    for member in infos_by_member:
        _categorize_ooxml_part(
            member,
            macro_parts=macro_parts,
            embedded_parts=embedded_parts,
            external_data_parts=external_data_parts,
            signature_parts=signature_parts,
            encryption_parts=encryption_parts,
            findings=findings,
        )

    macro_enabled_format = display_name.casefold().endswith(_OOXML_MACRO_SUFFIXES)
    if macro_enabled_format:
        _finding_once(
            findings,
            "OOXML_MACRO_ENABLED_FORMAT",
            None,
            "Macro-enabled OOXML format requires quarantine review.",
        )

    def read_part(member: str) -> bytes | None:
        nonlocal sampled_bytes
        info = infos_by_member[member]
        if info.file_size > _MAX_OOXML_PART_BYTES:
            _finding_once(
                findings,
                "OOXML_PART_SCAN_LIMIT_EXCEEDED",
                member,
                "OOXML control part exceeds the bounded static-scan size.",
            )
            return None
        prior = inspected_sizes.get(member, 0)
        additional = max(0, info.file_size - prior)
        if sampled_bytes + additional > _MAX_TOTAL_SAMPLE_BYTES:
            _finding_once(
                findings,
                "TOTAL_SAMPLE_LIMIT_EXCEEDED",
                member,
                "Archive scan exhausted its total byte budget.",
            )
            return None
        payload = archive.read(info)
        if len(payload) != info.file_size:
            _finding_once(
                findings,
                "OOXML_PART_SIZE_MISMATCH",
                member,
                "OOXML control part size did not match archive metadata.",
            )
            return None
        inspected_sizes[member] = len(payload)
        sampled_bytes += additional
        return payload

    if content_types_member:
        content_payload = read_part(content_types_member)
        if content_payload is not None:
            root = _parse_ooxml_xml(
                content_payload,
                member=content_types_member,
                parse_error_code="OOXML_CONTENT_TYPES_PARSE_ERROR",
                expected_namespaces=_OOXML_CONTENT_TYPE_NAMESPACES,
                findings=findings,
            )
            if root is not None:
                for element in root.iter():
                    content_type = element.attrib.get("ContentType")
                    if not content_type:
                        continue
                    content_types.append(content_type)
                    lower_type = content_type.casefold()
                    part_name = element.attrib.get("PartName", "")
                    raw_member = part_name.lstrip("/")
                    try:
                        member = (
                            _safe_archive_member(raw_member, "ooxml.content_type")
                            if raw_member
                            else content_types_member
                        )
                    except ExternalPackageReceiptError:
                        member = content_types_member
                        _finding_once(
                            findings,
                            "OOXML_UNSAFE_PART_NAME",
                            content_types_member,
                            "OOXML content type declares an unsafe part name.",
                        )
                    if "macroenabled" in lower_type or "vbaproject" in lower_type:
                        macro_parts.add(member)
                        _finding_once(
                            findings,
                            "OOXML_MACRO_CONTENT",
                            member,
                            "OOXML macro-capable content requires quarantine review.",
                        )
                    if "oleobject" in lower_type or "activex" in lower_type:
                        embedded_parts.add(member)
                        _finding_once(
                            findings,
                            "OOXML_EMBEDDED_OBJECT",
                            member,
                            "OOXML embedded or ActiveX content requires quarantine review.",
                        )
                    if (
                        "externallink" in lower_type
                        or "connection" in lower_type
                        or "querytable" in lower_type
                    ):
                        external_data_parts.add(member)
                        _finding_once(
                            findings,
                            "OOXML_EXTERNAL_DATA_PART",
                            member,
                            "OOXML external-data content requires quarantine review.",
                        )
                    if "digital-signature" in lower_type:
                        signature_parts.add(member)
                        _finding_once(
                            findings,
                            "OOXML_DIGITAL_SIGNATURE",
                            member,
                            "OOXML signature content requires explicit trust review.",
                        )

    relationship_members = sorted(
        member
        for member in infos_by_member
        if member.casefold().endswith(".rels")
        and (member.casefold() == "_rels/.rels" or "/_rels/" in f"/{member.casefold()}")
    )
    if len(relationship_members) > _MAX_OOXML_RELATIONSHIP_PARTS:
        _finding_once(
            findings,
            "OOXML_RELATIONSHIP_PART_LIMIT_EXCEEDED",
            None,
            "OOXML relationship-part count exceeds the static-scan bound.",
        )
        relationship_members = relationship_members[:_MAX_OOXML_RELATIONSHIP_PARTS]

    all_member_keys = set(lower_to_member)
    relationship_limit_hit = False
    for relationship_member in relationship_members:
        payload = read_part(relationship_member)
        if payload is None:
            continue
        relationship_parts_scanned += 1
        root = _parse_ooxml_xml(
            payload,
            member=relationship_member,
            parse_error_code="OOXML_RELATIONSHIP_PARSE_ERROR",
            expected_namespaces=_OOXML_RELATIONSHIP_NAMESPACES,
            findings=findings,
        )
        if root is None:
            continue

        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] != "Relationship":
                continue
            relationships_scanned += 1
            if relationships_scanned > _MAX_OOXML_RELATIONSHIPS:
                _finding_once(
                    findings,
                    "OOXML_RELATIONSHIP_LIMIT_EXCEEDED",
                    relationship_member,
                    "OOXML relationship count exceeds the static-scan bound.",
                )
                relationship_limit_hit = True
                break
            target = element.attrib.get("Target", "")
            relationship_type = element.attrib.get("Type", "")
            category = _relationship_type_category(relationship_type)
            target_mode = element.attrib.get("TargetMode", "").strip().casefold()
            if target_mode == "external":
                external_relationships.append(
                    OOXMLExternalRelationship(
                        relationship_part=relationship_member,
                        relationship_type=category,
                        target_scheme=_target_scheme(target),
                    )
                )
                _finding_once(
                    findings,
                    "OOXML_EXTERNAL_RELATIONSHIP",
                    relationship_member,
                    "External OOXML relationship target detected; value redacted.",
                )
                continue

            if category == "other":
                _finding_once(
                    findings,
                    "OOXML_UNKNOWN_RELATIONSHIP_TYPE",
                    relationship_member,
                    "OOXML relationship type is not in the static allowlist.",
                )

            resolved = _resolve_internal_relationship_target(
                relationship_member,
                target,
            )
            if resolved is None:
                _finding_once(
                    findings,
                    "OOXML_UNSAFE_INTERNAL_RELATIONSHIP",
                    relationship_member,
                    "Internal OOXML relationship target is unsafe; value redacted.",
                )
            elif resolved and resolved.casefold() not in all_member_keys:
                _finding_once(
                    findings,
                    "OOXML_MISSING_INTERNAL_TARGET",
                    relationship_member,
                    "Internal OOXML relationship target is absent; value redacted.",
                )

            if category == "macro":
                macro_parts.add(resolved or relationship_member)
                _finding_once(
                    findings,
                    "OOXML_MACRO_CONTENT",
                    relationship_member,
                    "OOXML macro relationship requires quarantine review.",
                )
            elif category in {"ole_object", "activex", "embedded_package"}:
                embedded_parts.add(resolved or relationship_member)
                _finding_once(
                    findings,
                    "OOXML_EMBEDDED_OBJECT",
                    relationship_member,
                    "OOXML embedded-object relationship requires quarantine review.",
                )
            elif category == "external_data":
                external_data_parts.add(resolved or relationship_member)
                _finding_once(
                    findings,
                    "OOXML_EXTERNAL_DATA_PART",
                    relationship_member,
                    "OOXML external-data relationship requires quarantine review.",
                )
            elif category == "digital_signature":
                signature_parts.add(resolved or relationship_member)
                _finding_once(
                    findings,
                    "OOXML_DIGITAL_SIGNATURE",
                    relationship_member,
                    "OOXML signature relationship requires explicit trust review.",
                )
        if relationship_limit_hit:
            break

    formula_members = sorted(
        member
        for member in infos_by_member
        if member.casefold().endswith(".xml")
        and (
            member.casefold() == "xl/workbook.xml"
            or member.casefold().startswith(
                (
                    "xl/worksheets/",
                    "xl/chartsheets/",
                    "xl/dialogsheets/",
                    "xl/charts/",
                    "xl/tables/",
                )
            )
        )
    )
    formula_element_names = {
        "f",
        "definedName",
        "calculatedColumnFormula",
        "totalsRowFormula",
    }
    for formula_member in formula_members:
        payload = read_part(formula_member)
        if payload is None:
            continue
        root = _parse_ooxml_xml(
            payload,
            member=formula_member,
            parse_error_code="OOXML_FORMULA_XML_PARSE_ERROR",
            expected_namespaces=set(),
            findings=findings,
        )
        if root is None:
            continue
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] not in formula_element_names:
                continue
            formula = "".join(element.itertext())
            if (
                _ACTIVE_FORMULA_FUNCTION.search(formula)
                or _EXTERNAL_WORKBOOK_FORMULA.search(formula)
                or _COMMAND_DDE_FORMULA.search(formula)
            ):
                active_formula_parts.add(formula_member)
                _finding_once(
                    findings,
                    "OOXML_ACTIVE_EXTERNAL_FORMULA",
                    formula_member,
                    "OOXML formula can invoke external behavior; formula redacted.",
                )
                break

    ooxml_codes = sorted(
        {
            finding.code
            for finding in findings[ooxml_finding_start:]
            if finding.code.startswith("OOXML_")
        }
    )
    return (
        OOXMLQuarantineProfile(
            detected=True,
            package_kind=_ooxml_package_kind(display_name, tuple(content_types)),
            macro_enabled_format=macro_enabled_format,
            relationship_parts_scanned=relationship_parts_scanned,
            relationships_scanned=relationships_scanned,
            external_relationships=tuple(external_relationships),
            macro_parts=tuple(sorted(macro_parts)),
            embedded_object_parts=tuple(sorted(embedded_parts)),
            external_data_parts=tuple(sorted(external_data_parts)),
            active_formula_parts=tuple(sorted(active_formula_parts)),
            signature_parts=tuple(sorted(signature_parts)),
            encryption_parts=tuple(sorted(encryption_parts)),
            finding_codes=tuple(ooxml_codes),
        ),
        sampled_bytes,
    )


def _source_prefix(source: Path | io.BytesIO, length: int) -> bytes:
    if isinstance(source, Path):
        with source.open("rb") as handle:
            return handle.read(length)
    position = source.tell()
    source.seek(0)
    prefix = source.read(length)
    source.seek(position)
    return prefix


def _scan_zip_source(
    source: Path | io.BytesIO,
    *,
    archive_sha256: str,
    display_name: str,
    collect_nested: bool,
    nested_edge_budget: int,
    nested_compressed_budget: int,
    nested_declared_budget: int,
    nested_byte_budget: int,
) -> _ContainerWork:
    findings: list[ArchiveQuarantineFinding] = []
    nested_archive_members: list[str] = []
    nested_candidates: list[_NestedCandidate] = []
    sampled_bytes = 0
    entry_count = 0
    package_root: str | None = None
    ooxml_profile = _empty_ooxml_profile()

    if _source_prefix(source, len(_CFB_MAGIC)) == _CFB_MAGIC:
        _finding(
            findings,
            "ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER",
            None,
            "Compound-file Office bytes are opaque to the ZIP/OOXML static scanner.",
        )
        if display_name.casefold().endswith(_OOXML_SUFFIXES):
            ooxml_profile = OOXMLQuarantineProfile(
                detected=True,
                package_kind=_ooxml_package_kind(display_name),
                macro_enabled_format=display_name.casefold().endswith(_OOXML_MACRO_SUFFIXES),
                relationship_parts_scanned=0,
                relationships_scanned=0,
                external_relationships=(),
                macro_parts=(),
                embedded_object_parts=(),
                external_data_parts=(),
                active_formula_parts=(),
                signature_parts=(),
                encryption_parts=("<compound-file-wrapper>",),
                finding_codes=("ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER",),
            )
        return _ContainerWork(
            scan=_result(
                archive_sha256=archive_sha256,
                entry_count=0,
                sampled_bytes=0,
                package_root=None,
                nested_archive_members=[],
                ooxml_profile=ooxml_profile,
                findings=findings,
            ),
            nested_candidates=(),
        )

    try:
        with ZipFile(source) as archive:
            infos = archive.infolist()
            entry_count = len(infos)
            if not infos or entry_count > _MAX_ARCHIVE_ENTRIES:
                _finding(
                    findings,
                    "ARCHIVE_ENTRY_LIMIT",
                    None,
                    "Archive entry count is outside the scan bound.",
                )
                return _ContainerWork(
                    scan=_result(
                        archive_sha256=archive_sha256,
                        entry_count=entry_count,
                        sampled_bytes=0,
                        package_root=None,
                        nested_archive_members=nested_archive_members,
                        ooxml_profile=ooxml_profile,
                        findings=findings,
                    ),
                    nested_candidates=(),
                )

            seen: dict[str, str] = {}
            infos_by_member: dict[str, ZipInfo] = {}
            inspected_sizes: dict[str, int] = {}
            regular_members: list[str] = []
            nested_info_by_member: dict[str, ZipInfo] = {}
            total_uncompressed = 0
            sample_budget_exhausted = False

            for index, info in enumerate(infos):
                try:
                    member = _safe_archive_member(
                        info.filename,
                        f"archive.entries[{index}]",
                    )
                    collision_key = _archive_collision_key(member)
                except ExternalPackageReceiptError:
                    _finding(
                        findings,
                        "UNSAFE_MEMBER_PATH",
                        info.filename,
                        "Member path is unsafe or ambiguous on the local platform.",
                    )
                    continue

                prior = seen.get(collision_key)
                if prior is not None:
                    _finding(
                        findings,
                        "DUPLICATE_NORMALIZED_MEMBER",
                        member,
                        f"Member aliases an earlier archive path: {prior}",
                    )
                    continue
                seen[collision_key] = member

                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    _finding(
                        findings,
                        "SYMLINK_MEMBER",
                        member,
                        "Archive symlinks are not scanned or admitted.",
                    )
                    continue
                if info.flag_bits & 0x1:
                    _finding(
                        findings,
                        "ENCRYPTED_MEMBER",
                        member,
                        "Encrypted members cannot be inspected safely.",
                    )
                    continue
                if info.is_dir():
                    continue

                infos_by_member[member] = info
                regular_members.append(member)
                total_uncompressed += info.file_size
                if total_uncompressed > _MAX_TOTAL_UNCOMPRESSED_BYTES:
                    _finding(
                        findings,
                        "TOTAL_UNCOMPRESSED_LIMIT_EXCEEDED",
                        member,
                        "Archive metadata exceeds the total uncompressed bound.",
                    )
                    break

                suffix_nested = member.casefold().endswith(
                    _NESTED_ARCHIVE_SUFFIXES + _OOXML_SUFFIXES
                )
                if suffix_nested:
                    nested_info_by_member[member] = info

                if info.file_size > _MAX_CANDIDATE_MEMBER_BYTES:
                    _finding(
                        findings,
                        "MEMBER_SCAN_LIMIT_EXCEEDED",
                        member,
                        "Member exceeds the bounded content-scan size.",
                    )
                    continue
                if info.file_size and (
                    info.compress_size == 0
                    or info.file_size / info.compress_size > _MAX_COMPRESSION_RATIO
                ):
                    _finding(
                        findings,
                        "COMPRESSION_RATIO_LIMIT_EXCEEDED",
                        member,
                        "Member metadata exceeds the compression-ratio bound.",
                    )
                    continue

                remaining = _MAX_TOTAL_SAMPLE_BYTES - sampled_bytes
                if remaining <= 0:
                    if not sample_budget_exhausted:
                        _finding(
                            findings,
                            "TOTAL_SAMPLE_LIMIT_EXCEEDED",
                            member,
                            "Archive scan exhausted its total byte budget.",
                        )
                        sample_budget_exhausted = True
                    continue
                requested = min(info.file_size, _MAX_MEMBER_SAMPLE_BYTES, remaining)
                with archive.open(info) as handle:
                    sample = handle.read(requested)
                sampled_bytes += len(sample)
                inspected_sizes[member] = len(sample)

                if any(sample.startswith(magic) for magic in _ZIP_MAGIC):
                    nested_info_by_member[member] = info

                basename = PurePosixPath(member).name.encode("utf-8", "ignore")
                if _RISKY_FILENAMES.search(basename):
                    _finding(
                        findings,
                        "RISKY_CREDENTIAL_FILENAME",
                        member,
                        "Member name is credential-shaped and requires review.",
                    )
                for code, pattern in _CREDENTIAL_SIGNATURES:
                    if pattern.search(sample):
                        _finding(
                            findings,
                            code,
                            member,
                            "Credential-shaped content signature detected; value redacted.",
                        )

            package_root = _package_root(regular_members)
            nested_archive_members.extend(nested_info_by_member)
            for member in nested_archive_members:
                _finding(
                    findings,
                    "NESTED_ARCHIVE_REQUIRES_CHILD_RECEIPT",
                    member,
                    "Nested container bytes require an independent child receipt.",
                )

            ooxml_profile, sampled_bytes = _inspect_ooxml(
                archive,
                infos_by_member,
                inspected_sizes,
                display_name,
                sampled_bytes,
                findings,
            )

            if collect_nested:
                remaining_edge_budget = max(0, nested_edge_budget)
                remaining_compressed_budget = max(0, nested_compressed_budget)
                remaining_declared_budget = max(0, nested_declared_budget)
                remaining_nested_budget = max(0, nested_byte_budget)
                for member, info in nested_info_by_member.items():
                    edge_allowed = remaining_edge_budget > 0
                    remaining_edge_budget = max(0, remaining_edge_budget - 1)
                    compressed_allowed = info.compress_size <= remaining_compressed_budget
                    remaining_compressed_budget = max(
                        0,
                        remaining_compressed_budget - info.compress_size,
                    )
                    declared_allowed = info.file_size <= remaining_declared_budget
                    remaining_declared_budget = max(
                        0,
                        remaining_declared_budget - info.file_size,
                    )
                    if not edge_allowed:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code="GRAPH_EDGE_LIMIT_EXCEEDED",
                            )
                        )
                        continue
                    if not compressed_allowed:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code=("GRAPH_COMPRESSED_BYTE_LIMIT_EXCEEDED"),
                            )
                        )
                        continue
                    if not declared_allowed:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code=("GRAPH_DECLARED_BYTE_LIMIT_EXCEEDED"),
                            )
                        )
                        continue
                    if info.file_size > _MAX_CANDIDATE_MEMBER_BYTES:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code="GRAPH_CHILD_MEMBER_LIMIT_EXCEEDED",
                            )
                        )
                        continue
                    if info.file_size > remaining_nested_budget:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code="GRAPH_CHILD_BYTE_BUDGET_EXCEEDED",
                            )
                        )
                        continue
                    payload = archive.read(info)
                    if len(payload) != info.file_size:
                        nested_candidates.append(
                            _NestedCandidate(
                                member=member,
                                declared_size=info.file_size,
                                compressed_size=info.compress_size,
                                payload=None,
                                unresolved_code="GRAPH_CHILD_SIZE_MISMATCH",
                            )
                        )
                        continue
                    remaining_nested_budget -= len(payload)
                    inspected_sizes[member] = len(payload)
                    nested_candidates.append(
                        _NestedCandidate(
                            member=member,
                            declared_size=info.file_size,
                            compressed_size=info.compress_size,
                            payload=payload,
                        )
                    )

            for member, info in infos_by_member.items():
                if inspected_sizes.get(member, 0) < info.file_size:
                    _finding_once(
                        findings,
                        "PARTIAL_MEMBER_SCAN",
                        member,
                        "Member tail and CRC were not fully inspected; quarantine retained.",
                    )
    except (BadZipFile, NotImplementedError, OSError, RuntimeError) as exc:
        _finding(
            findings,
            "ARCHIVE_READ_ERROR",
            None,
            f"Archive could not be scanned safely: {type(exc).__name__}.",
        )

    return _ContainerWork(
        scan=_result(
            archive_sha256=archive_sha256,
            entry_count=entry_count,
            sampled_bytes=sampled_bytes,
            package_root=package_root,
            nested_archive_members=nested_archive_members,
            ooxml_profile=ooxml_profile,
            findings=findings,
        ),
        nested_candidates=tuple(nested_candidates),
    )


def scan_archive_quarantine(path: str | Path) -> ArchiveQuarantineScan:
    """Inspect one bounded ZIP/OOXML container without extraction or recursion."""

    archive_path = Path(path)
    if not archive_path.is_file():
        findings: list[ArchiveQuarantineFinding] = []
        _finding(findings, "ARCHIVE_MISSING", None, "Archive bytes are unavailable.")
        return _result(
            archive_sha256="",
            entry_count=0,
            sampled_bytes=0,
            package_root=None,
            nested_archive_members=[],
            ooxml_profile=_empty_ooxml_profile(),
            findings=findings,
        )

    return _scan_zip_source(
        archive_path,
        archive_sha256=stable_file_hash(archive_path),
        display_name=archive_path.name,
        collect_nested=False,
        nested_edge_budget=0,
        nested_compressed_budget=0,
        nested_declared_budget=0,
        nested_byte_budget=0,
    ).scan


def _media_type(display_name: str, profile: OOXMLQuarantineProfile) -> str:
    lower_name = display_name.casefold()
    if profile.detected:
        if profile.package_kind == "spreadsheet":
            if lower_name.endswith((".xlsm", ".xltm")):
                return "application/vnd.ms-excel.sheet.macroenabled.12"
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if profile.package_kind == "wordprocessing":
            if lower_name.endswith((".docm", ".dotm")):
                return "application/vnd.ms-word.document.macroenabled.12"
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if profile.package_kind == "presentation":
            if lower_name.endswith((".pptm", ".potm", ".ppsm")):
                return "application/vnd.ms-powerpoint.presentation.macroenabled.12"
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        return "application/vnd.openxmlformats-package"
    if lower_name.endswith(".zip"):
        return "application/zip"
    return "application/octet-stream"


def _graph_resource_limits() -> ArchiveGraphResourceLimits:
    return ArchiveGraphResourceLimits(
        max_depth=_MAX_GRAPH_DEPTH,
        max_unique_containers=_MAX_GRAPH_CONTAINERS,
        max_edges=_MAX_GRAPH_EDGES,
        max_compressed_bytes=_MAX_GRAPH_TOTAL_COMPRESSED_BYTES,
        max_declared_bytes=_MAX_GRAPH_TOTAL_DECLARED_BYTES,
        max_child_bytes_read=_MAX_GRAPH_TOTAL_CHILD_BYTES,
    )


def scan_archive_graph_quarantine(path: str | Path) -> ArchiveQuarantineGraph:
    """Walk bounded nested ZIP/OOXML bytes in memory and dedupe by SHA-256."""

    archive_path = Path(path)
    if not archive_path.is_file():
        finding = ArchiveQuarantineFinding(
            code="ARCHIVE_MISSING",
            member=None,
            detail="Archive bytes are unavailable.",
        )
        return ArchiveQuarantineGraph(
            status="INTEGRITY_HOLD",
            root_archive_sha256="",
            nodes=(),
            edges=(),
            all_nodes_terminal=False,
            resource_limits=_graph_resource_limits(),
            resource_usage=ArchiveGraphResourceUsage(
                max_depth=0,
                unique_containers=0,
                edge_candidates_seen=0,
                compressed_bytes_seen=0,
                declared_bytes_seen=0,
                child_bytes_read=0,
            ),
            findings=(finding,),
        )

    root_sha256 = stable_file_hash(archive_path)
    queue: deque[_QueuedContainer] = deque(
        [
            _QueuedContainer(
                payload=None,
                path=archive_path,
                archive_sha256=root_sha256,
                display_name=archive_path.name,
                byte_size=archive_path.stat().st_size,
                depth=0,
            )
        ]
    )
    scheduled = {root_sha256}
    nodes: dict[str, ArchiveContainerNode] = {}
    edges: list[ArchiveContainerEdge] = []
    graph_findings: list[ArchiveQuarantineFinding] = []
    total_edges_seen = 0
    total_compressed_bytes = 0
    total_declared_bytes = 0
    total_child_bytes = 0
    max_edge_depth_seen = 0

    while queue:
        queued = queue.popleft()
        source: Path | io.BytesIO
        if queued.path is not None:
            source = queued.path
        else:
            source = io.BytesIO(queued.payload or b"")
        remaining_edges = _MAX_GRAPH_EDGES - total_edges_seen
        remaining_compressed_bytes = _MAX_GRAPH_TOTAL_COMPRESSED_BYTES - total_compressed_bytes
        remaining_declared_bytes = _MAX_GRAPH_TOTAL_DECLARED_BYTES - total_declared_bytes
        remaining_graph_bytes = _MAX_GRAPH_TOTAL_CHILD_BYTES - total_child_bytes
        work = _scan_zip_source(
            source,
            archive_sha256=queued.archive_sha256,
            display_name=queued.display_name,
            collect_nested=True,
            nested_edge_budget=remaining_edges,
            nested_compressed_budget=remaining_compressed_bytes,
            nested_declared_budget=remaining_declared_bytes,
            nested_byte_budget=remaining_graph_bytes,
        )
        fatal_codes = {
            "ARCHIVE_READ_ERROR",
            "ARCHIVE_ENTRY_LIMIT",
            "ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER",
            "TOTAL_UNCOMPRESSED_LIMIT_EXCEEDED",
        }
        terminal = not any(finding.code in fatal_codes for finding in work.scan.findings)
        nodes[queued.archive_sha256] = ArchiveContainerNode(
            archive_sha256=queued.archive_sha256,
            display_name=PurePosixPath(queued.display_name).name,
            byte_size=queued.byte_size,
            media_type=_media_type(queued.display_name, work.scan.ooxml_profile),
            depth=queued.depth,
            terminal=terminal,
            scan=work.scan,
        )

        for candidate in work.nested_candidates:
            total_edges_seen += 1
            total_compressed_bytes += candidate.compressed_size
            total_declared_bytes += candidate.declared_size
            if candidate.payload is None:
                _finding(
                    graph_findings,
                    candidate.unresolved_code or "GRAPH_CHILD_UNAVAILABLE",
                    candidate.member,
                    "Nested container could not be inspected within graph bounds.",
                )
                continue
            total_child_bytes += len(candidate.payload)
            child_sha256 = hashlib.sha256(candidate.payload).hexdigest()
            edges.append(
                ArchiveContainerEdge(
                    parent_sha256=queued.archive_sha256,
                    member=candidate.member,
                    child_sha256=child_sha256,
                    byte_size=len(candidate.payload),
                )
            )
            child_depth = queued.depth + 1
            max_edge_depth_seen = max(max_edge_depth_seen, child_depth)
            if child_depth > _MAX_GRAPH_DEPTH:
                _finding(
                    graph_findings,
                    "GRAPH_DEPTH_LIMIT_EXCEEDED",
                    candidate.member,
                    "Nested container exceeds the graph depth bound.",
                )
                continue
            if child_sha256 in scheduled:
                continue
            if len(scheduled) >= _MAX_GRAPH_CONTAINERS:
                _finding(
                    graph_findings,
                    "GRAPH_CONTAINER_LIMIT_EXCEEDED",
                    candidate.member,
                    "Nested container count exceeds the graph bound.",
                )
                continue
            scheduled.add(child_sha256)
            queue.append(
                _QueuedContainer(
                    payload=candidate.payload,
                    path=None,
                    archive_sha256=child_sha256,
                    display_name=candidate.member,
                    byte_size=len(candidate.payload),
                    depth=child_depth,
                )
            )

    edges.sort(key=lambda edge: (edge.parent_sha256, edge.member, edge.child_sha256))
    ordered_nodes = tuple(nodes[sha256] for sha256 in sorted(nodes))
    all_nodes_terminal = (
        not graph_findings
        and len(nodes) == len(scheduled)
        and all(node.terminal for node in ordered_nodes)
        and all(edge.child_sha256 in nodes for edge in edges)
    )
    if not all_nodes_terminal:
        status = "INTEGRITY_HOLD"
    elif any(node.scan.status == "QUARANTINE_HOLD" for node in ordered_nodes):
        status = "GRAPH_COMPLETE_QUARANTINED"
    else:
        status = "CLEAR_FOR_RECEIPT_REVIEW"

    return ArchiveQuarantineGraph(
        status=status,
        root_archive_sha256=root_sha256,
        nodes=ordered_nodes,
        edges=tuple(edges),
        all_nodes_terminal=all_nodes_terminal,
        resource_limits=_graph_resource_limits(),
        resource_usage=ArchiveGraphResourceUsage(
            max_depth=max(
                max((node.depth for node in ordered_nodes), default=0),
                max_edge_depth_seen,
            ),
            unique_containers=len(ordered_nodes),
            edge_candidates_seen=total_edges_seen,
            compressed_bytes_seen=total_compressed_bytes,
            declared_bytes_seen=total_declared_bytes,
            child_bytes_read=total_child_bytes,
        ),
        findings=tuple(graph_findings),
    )


__all__ = [
    "ArchiveContainerEdge",
    "ArchiveContainerNode",
    "ArchiveGraphResourceLimits",
    "ArchiveGraphResourceUsage",
    "ArchiveQuarantineFinding",
    "ArchiveQuarantineGraph",
    "ArchiveQuarantineScan",
    "OOXMLExternalRelationship",
    "OOXMLQuarantineProfile",
    "scan_archive_graph_quarantine",
    "scan_archive_quarantine",
]
