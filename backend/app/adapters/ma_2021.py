"""Fail-closed adapter for the official Ma et al. 2021 V2 dataset.

The adapter preserves each source spreadsheet row as one vector-valued record.
It does not admit source bytes, write database rows, recompute published means,
bind project materials, or grant sensory/model/release authority.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Mapping
from uuid import UUID, uuid5
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile, ZipInfo

from app.services.lab_external_studies import (
    ExternalConditionInput,
    ExternalExperimentalUnitInput,
    ExternalIdentityCrosswalkInput,
    ExternalObservationInput,
    ExternalStimulusComponentInput,
    ExternalStimulusInput,
    ExternalStudyConflictInput,
    ExternalStudyInput,
)
from app.services.lab_sources import (
    ExtractionRecordInput,
    SourceDocumentInput,
    SourceUseConstraintInput,
    SourceUseRequest,
)

MA2021_ADAPTER_NAME = "ma-2021-v2-source-vector-adapter"
MA2021_ADAPTER_VERSION = "1.0.0"
MA2021_DATASET_DOI = "10.15454/51OVY6"
MA2021_FILE_PID = "doi:10.15454/51OVY6/COAY4H"
MA2021_SOURCE_FAMILY = "doi:10.15454/51OVY6"
MA2021_ARTIFACT_SHA256 = (
    "c540f18ba71b778c36756810fff38bdf177c2af9d593567a6dba57a30503c950"
)
MA2021_ARTIFACT_SIZE = 487_926
MA2021_ENDPOINTS = ("IA", "IAmix", "IB", "IBmix", "IAB", "PA", "PB", "PAB")
MA2021_PARTICIPANT_ENDPOINT_KEY = "MA2021_PARTICIPANT_TRIAL_VECTOR"
MA2021_AGGREGATE_ENDPOINT_KEY = "MA2021_SOURCE_AGGREGATE_TRIAL_VECTOR"
MA2021_CHANNEL = "RECHERCHE_DATA_GOUV_OFFICIAL_ORIGINAL"
MA2021_PURPOSE = "MA_2021_EXTERNAL_STUDY_AUTHORITY_FALSE_PROJECTION"

_NAMESPACE = UUID("e7eaeb58-6bb9-5c13-b3c6-54cf9778a1c4")
_OOXML_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_CELL_REF = re.compile(r"^([A-Za-z]+)([1-9][0-9]*)$")
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


class Ma2021AdapterError(ValueError):
    """A stable fail-closed adapter error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class Ma2021WorkbookContract:
    artifact_sha256: str
    artifact_size: int
    odorant_count: int
    trial_count: int
    participant_count: int
    participant_row_count: int
    participants_per_trial: int
    duplicate_group_count: int
    unique_mixture_count: int
    metadata_conflict_trial_count: int = 0
    odorant_name_conflict_count: int = 0

    def __post_init__(self) -> None:
        digest = self.artifact_sha256.casefold()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("artifact_sha256 must be a SHA-256 hexadecimal digest")
        for field in (
            "artifact_size",
            "odorant_count",
            "trial_count",
            "participant_count",
            "participant_row_count",
            "participants_per_trial",
            "unique_mixture_count",
        ):
            if getattr(self, field) < 1:
                raise ValueError(f"{field} must be positive")
        if (
            self.duplicate_group_count < 0
            or self.metadata_conflict_trial_count < 0
            or self.odorant_name_conflict_count < 0
        ):
            raise ValueError("conflict and duplicate counts must be non-negative")


MA2021_V2_CONTRACT = Ma2021WorkbookContract(
    artifact_sha256=MA2021_ARTIFACT_SHA256,
    artifact_size=MA2021_ARTIFACT_SIZE,
    odorant_count=72,
    trial_count=222,
    participant_count=60,
    participant_row_count=6_660,
    participants_per_trial=30,
    duplicate_group_count=24,
    unique_mixture_count=198,
    metadata_conflict_trial_count=4,
    odorant_name_conflict_count=1,
)


@dataclass(frozen=True, slots=True)
class Ma2021Odorant:
    source_row: int
    cas: str
    name: str
    odor: str
    concentration_mg_ml: str
    solvent: str
    purity: str
    trial_numbers: tuple[int, ...]
    source_row_sha256: str


@dataclass(frozen=True, slots=True)
class Ma2021AggregateTrial:
    source_row: int
    trial: int
    reference_trial: int | None
    repeat_index: int | None
    group: str
    odor_a: str
    odor_b: str
    values: Mapping[str, str]
    source_row_sha256: str

    @property
    def mixture_key(self) -> int:
        return self.reference_trial if self.reference_trial is not None else self.trial


@dataclass(frozen=True, slots=True)
class Ma2021ParticipantTrial:
    source_row: int
    subject: int
    trial: int
    reference_trial: int | None
    repeat_index: int | None
    odor_a: str
    odor_b: str
    values: Mapping[str, str]
    source_row_sha256: str


@dataclass(frozen=True, slots=True)
class Ma2021TrialMetadataConflict:
    trial: int
    aggregate_source_row: int
    participant_source_rows: tuple[int, ...]
    aggregate_reference_trial: int | None
    participant_reference_trial: int | None
    aggregate_row_sha256: str
    participant_row_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Ma2021OdorantNameConflict:
    trial_name: str
    odor_information_name: str
    cas: str
    odor_information_source_row: int
    affected_trials: tuple[int, ...]
    odor_information_row_sha256: str
    aggregate_row_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Ma2021Dataset:
    artifact_sha256: str
    artifact_size: int
    odorants: tuple[Ma2021Odorant, ...]
    aggregate_trials: tuple[Ma2021AggregateTrial, ...]
    participant_trials: tuple[Ma2021ParticipantTrial, ...]
    source_sheet_sha256s: Mapping[str, str]
    trial_metadata_conflicts: tuple[Ma2021TrialMetadataConflict, ...] = ()
    odorant_name_conflicts: tuple[Ma2021OdorantNameConflict, ...] = ()

    @property
    def participants(self) -> tuple[int, ...]:
        return tuple(sorted({row.subject for row in self.participant_trials}))

    @property
    def mixture_keys(self) -> tuple[int, ...]:
        return tuple(sorted({row.mixture_key for row in self.aggregate_trials}))


@dataclass(frozen=True, slots=True)
class Ma2021ExtractionSpec:
    """One B1 extraction command blueprint for one native output record."""

    output_record_id: str
    record_kind: str
    locator: Mapping[str, object]
    original_value: Mapping[str, object]
    parsed_value: Mapping[str, object]
    input_sha256: str
    output_sha256: str

    def to_input(
        self,
        *,
        source_version_id: str,
        reviewer_pseudonym: str | None,
    ) -> ExtractionRecordInput:
        return ExtractionRecordInput(
            source_version_id=source_version_id,
            locator=dict(self.locator),
            structure_context={
                "dataset_doi": MA2021_DATASET_DOI,
                "file_pid": MA2021_FILE_PID,
                "record_kind": self.record_kind,
                "source_row_vector_preserved": True,
            },
            original_wording=None,
            original_value=dict(self.original_value),
            parsed_value=dict(self.parsed_value),
            normalization={
                "state": "SOURCE_PRESERVED",
                "numeric_representation": "EXACT_SOURCE_DECIMAL_TEXT",
                "aggregate_recomputed": False,
            },
            parser_or_model_version=f"{MA2021_ADAPTER_NAME}/{MA2021_ADAPTER_VERSION}",
            reviewer_pseudonym=reviewer_pseudonym,
            uncertainty={"state": "SOURCE_REPORTED_OR_NOT_REPORTED"},
            ambiguity=(),
            output_observation_id=self.output_record_id,
            input_sha256=self.input_sha256,
            output_sha256=self.output_sha256,
        )


def _record_id(kind: str, key: str) -> str:
    return str(uuid5(_NAMESPACE, f"ma-2021-v2:{kind}:{key}"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_json_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_digest(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _safe_member_name(info: ZipInfo) -> str:
    raw = info.filename.replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or _URI_SCHEME.match(raw)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise Ma2021AdapterError("OOXML_UNSAFE_MEMBER_PATH", "Unsafe OOXML member path")
    return path.as_posix()


def _relationship_owner(path: str) -> str:
    parts = PurePosixPath(path).parts
    if "_rels" not in parts or not parts[-1].endswith(".rels"):
        raise Ma2021AdapterError("OOXML_RELATIONSHIP_PATH_INVALID", path)
    marker = parts.index("_rels")
    owner_name = parts[-1][: -len(".rels")]
    return PurePosixPath(*parts[:marker], owner_name).as_posix()


def _resolve_internal_target(relationship_path: str, target: str) -> str:
    normalized_target = target.replace("\\", "/")
    if (
        not normalized_target
        or normalized_target.startswith("/")
        or _URI_SCHEME.match(normalized_target)
    ):
        raise Ma2021AdapterError(
            "OOXML_RELATIONSHIP_TARGET_INVALID",
            "Relationship target is not an internal package path",
        )
    owner = _relationship_owner(relationship_path)
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), normalized_target))
    if resolved == ".." or resolved.startswith("../"):
        raise Ma2021AdapterError(
            "OOXML_RELATIONSHIP_ROOT_ESCAPE",
            "Relationship target escapes the OOXML package root",
        )
    return PurePosixPath(resolved).as_posix()


class _StrictXlsxReader:
    MAX_MEMBER_BYTES = 16 * 1024 * 1024
    MAX_TOTAL_BYTES = 64 * 1024 * 1024
    MAX_XML_ELEMENTS = 1_000_000
    MAX_COMPRESSION_RATIO = 200

    def __init__(self, path: Path, contract: Ma2021WorkbookContract) -> None:
        self.path = path
        self.contract = contract
        self._archive: ZipFile | None = None
        self._infos: dict[str, ZipInfo] = {}
        self._xml_cache: dict[str, ElementTree.Element] = {}

    def __enter__(self) -> _StrictXlsxReader:
        with self.path.open("rb") as stream:
            signature = stream.read(8)
        if signature == _CFB_SIGNATURE:
            raise Ma2021AdapterError(
                "ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER",
                "Compound-file Office containers are not parsed",
            )
        try:
            archive = ZipFile(self.path)
        except BadZipFile as exc:
            raise Ma2021AdapterError("OOXML_BAD_ZIP", "Workbook is not a readable ZIP") from exc
        self._archive = archive
        seen: set[str] = set()
        total = 0
        for info in archive.infolist():
            name = _safe_member_name(info)
            identity = name.casefold()
            if identity in seen:
                raise Ma2021AdapterError(
                    "OOXML_DUPLICATE_MEMBER",
                    "Duplicate normalized OOXML member name",
                )
            seen.add(identity)
            if info.flag_bits & 0x1:
                raise Ma2021AdapterError("OOXML_ENCRYPTED_MEMBER", "Encrypted member rejected")
            if info.file_size > self.MAX_MEMBER_BYTES:
                raise Ma2021AdapterError("OOXML_MEMBER_SIZE_LIMIT", "OOXML member too large")
            total += info.file_size
            if total > self.MAX_TOTAL_BYTES:
                raise Ma2021AdapterError("OOXML_TOTAL_SIZE_LIMIT", "OOXML archive too large")
            if info.file_size / max(info.compress_size, 1) > self.MAX_COMPRESSION_RATIO:
                raise Ma2021AdapterError(
                    "OOXML_COMPRESSION_RATIO_LIMIT",
                    "OOXML member compression ratio exceeds the bound",
                )
            suffix = PurePosixPath(name).suffix.casefold()
            if suffix in {".zip", ".xlsx", ".xlsm", ".docx", ".pptx"}:
                raise Ma2021AdapterError(
                    "OOXML_NESTED_ARCHIVE",
                    "Nested archive or Office container rejected",
                )
            self._infos[name] = info
        if archive.testzip() is not None:
            raise Ma2021AdapterError("OOXML_CRC_MISMATCH", "OOXML member CRC failed")
        self._validate_capabilities()
        return self

    def __exit__(self, *_: object) -> None:
        if self._archive is not None:
            self._archive.close()

    def bytes(self, name: str) -> bytes:
        if self._archive is None or name not in self._infos:
            raise Ma2021AdapterError("OOXML_REQUIRED_PART_MISSING", name)
        data = self._archive.read(self._infos[name])
        if len(data) != self._infos[name].file_size:
            raise Ma2021AdapterError("OOXML_PARTIAL_READ", name)
        if data.startswith(_CFB_SIGNATURE):
            raise Ma2021AdapterError(
                "ENCRYPTED_OR_OPAQUE_OFFICE_CONTAINER",
                "Embedded compound-file content rejected",
            )
        return data

    def xml(self, name: str) -> ElementTree.Element:
        if name in self._xml_cache:
            return self._xml_cache[name]
        raw = self.bytes(name)
        upper = raw.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            raise Ma2021AdapterError("OOXML_XML_ENTITY_DECLARATION", name)
        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError as exc:
            raise Ma2021AdapterError("OOXML_XML_PARSE_ERROR", name) from exc
        if sum(1 for _ in root.iter()) > self.MAX_XML_ELEMENTS:
            raise Ma2021AdapterError("OOXML_XML_ELEMENT_LIMIT", name)
        self._xml_cache[name] = root
        return root

    def _validate_capabilities(self) -> None:
        forbidden_prefixes = (
            "xl/externallinks/",
            "xl/embeddings/",
            "xl/macrosheets/",
            "xl/dialogsheets/",
            "xl/ctrlprops/",
        )
        forbidden_names = {
            "xl/vbaproject.bin",
            "xl/connections.xml",
            "encryptedpackage",
            "encryptioninfo",
        }
        for name in self._infos:
            folded = name.casefold()
            if folded in forbidden_names or folded.startswith(forbidden_prefixes):
                raise Ma2021AdapterError(
                    "OOXML_ACTIVE_OR_EXTERNAL_CONTENT",
                    "Active, embedded, or external workbook capability rejected",
                )
            if name.endswith(".rels"):
                root = self.xml(name)
                for relationship in root.findall(f"{{{_REL_NS}}}Relationship"):
                    if str(relationship.attrib.get("TargetMode", "")).casefold() == "external":
                        raise Ma2021AdapterError(
                            "OOXML_EXTERNAL_RELATIONSHIP",
                            "External OOXML relationship rejected",
                        )
                    target = str(relationship.attrib.get("Target", ""))
                    resolved = _resolve_internal_target(name, target)
                    if resolved not in self._infos:
                        raise Ma2021AdapterError(
                            "OOXML_DANGLING_RELATIONSHIP",
                            "OOXML relationship target is missing",
                        )
            if name.casefold().endswith(".xml"):
                root = self.xml(name)
                for element in root.iter():
                    local = _local_name(element.tag).casefold()
                    if local in {
                        "f",
                        "formula",
                        "calculatedcolumnformula",
                        "totalsrowformula",
                    } or (
                        local == "definedname" and (element.text or "").strip()
                    ):
                        raise Ma2021AdapterError(
                            "OOXML_ACTIVE_FORMULA",
                            "Workbook formulas and defined expressions are rejected",
                        )

    def sheet_parts(self) -> dict[str, str]:
        workbook = self.xml("xl/workbook.xml")
        relationships = self.xml("xl/_rels/workbook.xml.rels")
        targets: dict[str, str] = {}
        relationship_path = "xl/_rels/workbook.xml.rels"
        for relationship in relationships.findall(f"{{{_REL_NS}}}Relationship"):
            relationship_id = relationship.attrib.get("Id")
            target = relationship.attrib.get("Target")
            if relationship_id and target:
                targets[relationship_id] = _resolve_internal_target(
                    relationship_path,
                    target,
                )
        sheets: dict[str, str] = {}
        for element in workbook.iter(f"{{{_SHEET_NS}}}sheet"):
            name = str(element.attrib.get("name", "")).strip()
            relationship_id = element.attrib.get(f"{{{_OOXML_REL_NS}}}id")
            if not name or not relationship_id or relationship_id not in targets:
                raise Ma2021AdapterError("OOXML_SHEET_RELATIONSHIP_INVALID", name)
            if name in sheets:
                raise Ma2021AdapterError("OOXML_DUPLICATE_SHEET", name)
            sheets[name] = targets[relationship_id]
        return sheets

    def shared_strings(self) -> tuple[str, ...]:
        if "xl/sharedStrings.xml" not in self._infos:
            return ()
        root = self.xml("xl/sharedStrings.xml")
        values: list[str] = []
        for item in root.findall(f"{{{_SHEET_NS}}}si"):
            values.append("".join(node.text or "" for node in item.iter(f"{{{_SHEET_NS}}}t")))
        return tuple(values)

    def rows(self, sheet_part: str, shared: tuple[str, ...]) -> list[list[str | None]]:
        root = self.xml(sheet_part)
        parsed_rows: list[list[str | None]] = []
        for row in root.iter(f"{{{_SHEET_NS}}}row"):
            cells: dict[int, str | None] = {}
            for cell in row.findall(f"{{{_SHEET_NS}}}c"):
                reference = str(cell.attrib.get("r", ""))
                match = _CELL_REF.fullmatch(reference)
                if match is None:
                    raise Ma2021AdapterError("OOXML_CELL_REFERENCE_INVALID", reference)
                column = _column_number(match.group(1))
                if column in cells:
                    raise Ma2021AdapterError("OOXML_DUPLICATE_CELL", reference)
                kind = cell.attrib.get("t")
                value_node = cell.find(f"{{{_SHEET_NS}}}v")
                if kind == "inlineStr":
                    inline = cell.find(f"{{{_SHEET_NS}}}is")
                    value = (
                        "".join(
                            node.text or ""
                            for node in inline.iter(f"{{{_SHEET_NS}}}t")
                        )
                        if inline is not None
                        else ""
                    )
                elif value_node is None:
                    value = None
                elif kind == "s":
                    try:
                        value = shared[int(value_node.text or "")]
                    except (ValueError, IndexError) as exc:
                        raise Ma2021AdapterError(
                            "OOXML_SHARED_STRING_INDEX_INVALID",
                            reference,
                        ) from exc
                elif kind == "b":
                    value = "TRUE" if value_node.text == "1" else "FALSE"
                else:
                    value = value_node.text
                cells[column] = value
            if cells:
                width = max(cells)
                parsed_rows.append([cells.get(index) for index in range(1, width + 1)])
        return parsed_rows


def _column_number(letters: str) -> int:
    value = 0
    for char in letters.upper():
        value = value * 26 + ord(char) - ord("A") + 1
    return value


def _header(value: str | None) -> str:
    normalized = " ".join(str(value or "").split()).casefold()
    return normalized.rstrip(".")


def _rectangular_rows(
    rows: list[list[str | None]],
    expected_headers: tuple[str, ...],
    sheet_name: str,
) -> list[tuple[int, dict[str, str | None]]]:
    if not rows:
        raise Ma2021AdapterError("MA2021_EMPTY_SHEET", sheet_name)
    actual = tuple(_header(value) for value in rows[0])
    if actual != expected_headers:
        raise Ma2021AdapterError(
            "MA2021_HEADER_MISMATCH",
            f"Unexpected columns in {sheet_name}: {actual!r}",
        )
    output: list[tuple[int, dict[str, str | None]]] = []
    for source_row, raw in enumerate(rows[1:], start=2):
        padded = tuple(raw) + (None,) * (len(expected_headers) - len(raw))
        if len(padded) > len(expected_headers) and any(
            value is not None for value in padded[len(expected_headers) :]
        ):
            raise Ma2021AdapterError("MA2021_EXTRA_COLUMN_DATA", sheet_name)
        values = padded[: len(expected_headers)]
        if all(value is None or not str(value).strip() for value in values):
            continue
        output.append((source_row, dict(zip(expected_headers, values, strict=True))))
    return output


def _required_text(value: str | None, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise Ma2021AdapterError("MA2021_REQUIRED_VALUE_MISSING", field)
    return normalized


def _integer(value: str | None, field: str, *, required: bool = True) -> int | None:
    if value is None or not str(value).strip():
        if required:
            raise Ma2021AdapterError("MA2021_REQUIRED_VALUE_MISSING", field)
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise Ma2021AdapterError("MA2021_INTEGER_INVALID", field) from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise Ma2021AdapterError("MA2021_INTEGER_INVALID", field)
    return int(number)


def _required_integer(value: str | None, field: str) -> int:
    parsed = _integer(value, field)
    if parsed is None:
        raise AssertionError("required integer parser returned None")
    return parsed


def _decimal_text(value: str | None, field: str, *, maximum: Decimal) -> str:
    normalized = _required_text(value, field)
    try:
        number = Decimal(normalized)
    except InvalidOperation as exc:
        raise Ma2021AdapterError("MA2021_DECIMAL_INVALID", field) from exc
    if not number.is_finite() or number < 0 or number > maximum:
        raise Ma2021AdapterError("MA2021_SCALE_OUT_OF_RANGE", field)
    return normalized


def _canonical_plain_decimal(value: str, field: str) -> str:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise Ma2021AdapterError("MA2021_DECIMAL_INVALID", field) from exc
    if not number.is_finite() or number < 0:
        raise Ma2021AdapterError("MA2021_DECIMAL_INVALID", field)
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return canonical or "0"


def _row_hash(
    artifact_sha256: str,
    sheet: str,
    source_row: int,
    values: Mapping[str, object],
) -> str:
    return _stable_json_hash(
        {
            "schema": "ma-2021-source-row-v1",
            "artifact_sha256": artifact_sha256,
            "sheet": sheet,
            "source_row": source_row,
            "values": dict(values),
        }
    )


def _endpoint_values(
    row: Mapping[str, str | None],
    *,
    sheet: str,
    source_row: int,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for endpoint in MA2021_ENDPOINTS:
        maximum = Decimal("11") if endpoint in {"IAmix", "IBmix"} else Decimal("10")
        values[endpoint] = _decimal_text(
            row[endpoint.casefold()],
            f"{sheet}!{endpoint}{source_row}",
            maximum=maximum,
        )
    return values


def _parse_odorants(
    rows: list[list[str | None]],
    *,
    artifact_sha256: str,
) -> tuple[Ma2021Odorant, ...]:
    headers = (
        "cas",
        "odorant",
        "odor",
        "cons.(mg/ml)",
        "solvent",
        "purity",
        "trial number",
    )
    parsed: list[Ma2021Odorant] = []
    for source_row, row in _rectangular_rows(rows, headers, "odor information"):
        trial_numbers = tuple(
            int(value.strip())
            for value in _required_text(row["trial number"], "trial number").split(",")
        )
        cas = _required_text(row["cas"], "CAS")
        name = _required_text(row["odorant"], "odorant")
        odor = _required_text(row["odor"], "odor")
        concentration = _required_text(row["cons.(mg/ml)"], "concentration")
        solvent = _required_text(row["solvent"], "solvent")
        purity = _required_text(row["purity"], "purity")
        payload: dict[str, object] = {
            "cas": cas,
            "name": name,
            "odor": odor,
            "concentration_mg_ml": concentration,
            "solvent": solvent,
            "purity": purity,
            "trial_numbers": trial_numbers,
        }
        parsed.append(
            Ma2021Odorant(
                source_row=source_row,
                cas=cas,
                name=name,
                odor=odor,
                concentration_mg_ml=concentration,
                solvent=solvent,
                purity=purity,
                trial_numbers=trial_numbers,
                source_row_sha256=_row_hash(
                    artifact_sha256,
                    "odor information",
                    source_row,
                    payload,
                ),
            )
        )
    return tuple(parsed)


def _parse_aggregate(
    rows: list[list[str | None]],
    *,
    artifact_sha256: str,
) -> tuple[Ma2021AggregateTrial, ...]:
    headers = (
        "trial",
        "r-trial",
        "repeat",
        "group",
        "odor a",
        "odor b",
        "ia",
        "iamix",
        "ib",
        "ibmix",
        "iab",
        "pa",
        "pb",
        "pab",
    )
    parsed: list[Ma2021AggregateTrial] = []
    sheet = "mean value after deleting sub47"
    for source_row, row in _rectangular_rows(rows, headers, sheet):
        values = _endpoint_values(row, sheet=sheet, source_row=source_row)
        trial = _required_integer(row["trial"], "aggregate trial")
        reference_trial = _integer(
            row["r-trial"],
            "aggregate r-trial",
            required=False,
        )
        repeat_index = _integer(
            row["repeat"],
            "aggregate repeat",
            required=False,
        )
        group = _required_text(row["group"], "aggregate group")
        odor_a = _required_text(row["odor a"], "aggregate odor A")
        odor_b = _required_text(row["odor b"], "aggregate odor B")
        payload: dict[str, object] = {
            "trial": trial,
            "reference_trial": reference_trial,
            "repeat_index": repeat_index,
            "group": group,
            "odor_a": odor_a,
            "odor_b": odor_b,
            "values": values,
        }
        parsed.append(
            Ma2021AggregateTrial(
                source_row=source_row,
                trial=trial,
                reference_trial=reference_trial,
                repeat_index=repeat_index,
                group=group,
                odor_a=odor_a,
                odor_b=odor_b,
                values=values,
                source_row_sha256=_row_hash(
                    artifact_sha256,
                    sheet,
                    source_row,
                    payload,
                ),
            )
        )
    return tuple(parsed)


def _parse_participants(
    rows: list[list[str | None]],
    *,
    artifact_sha256: str,
) -> tuple[Ma2021ParticipantTrial, ...]:
    headers = (
        "sub",
        "trial",
        "r-trial",
        "repeat",
        "odor a",
        "odor b",
        "ia",
        "iamix",
        "ib",
        "ibmix",
        "iab",
        "pa",
        "pb",
        "pab",
    )
    parsed: list[Ma2021ParticipantTrial] = []
    sheet = "individual data"
    for source_row, row in _rectangular_rows(rows, headers, sheet):
        values = _endpoint_values(row, sheet=sheet, source_row=source_row)
        subject = _required_integer(row["sub"], "participant subject")
        trial = _required_integer(row["trial"], "participant trial")
        reference_trial = _integer(
            row["r-trial"],
            "participant r-trial",
            required=False,
        )
        repeat_index = _integer(
            row["repeat"],
            "participant repeat",
            required=False,
        )
        odor_a = _required_text(row["odor a"], "participant odor A")
        odor_b = _required_text(row["odor b"], "participant odor B")
        payload: dict[str, object] = {
            "subject": subject,
            "trial": trial,
            "reference_trial": reference_trial,
            "repeat_index": repeat_index,
            "odor_a": odor_a,
            "odor_b": odor_b,
            "values": values,
        }
        parsed.append(
            Ma2021ParticipantTrial(
                source_row=source_row,
                subject=subject,
                trial=trial,
                reference_trial=reference_trial,
                repeat_index=repeat_index,
                odor_a=odor_a,
                odor_b=odor_b,
                values=values,
                source_row_sha256=_row_hash(
                    artifact_sha256,
                    sheet,
                    source_row,
                    payload,
                ),
            )
        )
    return tuple(parsed)


def _trial_metadata_conflicts(
    aggregate_trials: tuple[Ma2021AggregateTrial, ...],
    participant_trials: tuple[Ma2021ParticipantTrial, ...],
) -> tuple[Ma2021TrialMetadataConflict, ...]:
    aggregate_by_trial = {row.trial: row for row in aggregate_trials}
    participants_by_trial: dict[int, list[Ma2021ParticipantTrial]] = defaultdict(list)
    for row in participant_trials:
        participants_by_trial[row.trial].append(row)
    conflicts: list[Ma2021TrialMetadataConflict] = []
    for trial, rows in sorted(participants_by_trial.items()):
        aggregate = aggregate_by_trial.get(trial)
        if aggregate is None:
            continue
        participant_references = {row.reference_trial for row in rows}
        if len(participant_references) != 1:
            continue
        participant_reference = next(iter(participant_references))
        if participant_reference != aggregate.reference_trial:
            conflicts.append(
                Ma2021TrialMetadataConflict(
                    trial=trial,
                    aggregate_source_row=aggregate.source_row,
                    participant_source_rows=tuple(row.source_row for row in rows),
                    aggregate_reference_trial=aggregate.reference_trial,
                    participant_reference_trial=participant_reference,
                    aggregate_row_sha256=aggregate.source_row_sha256,
                    participant_row_sha256s=tuple(
                        row.source_row_sha256 for row in rows
                    ),
                )
            )
    return tuple(conflicts)


def _odorant_name_conflicts(
    odorants: tuple[Ma2021Odorant, ...],
    aggregate_trials: tuple[Ma2021AggregateTrial, ...],
) -> tuple[Ma2021OdorantNameConflict, ...]:
    exact = {row.name for row in odorants}
    trial_names = {name for row in aggregate_trials for name in (row.odor_a, row.odor_b)}
    conflicts: list[Ma2021OdorantNameConflict] = []
    for trial_name in sorted(trial_names - exact):
        identity = re.sub(r"\s+", "", trial_name).casefold()
        candidates = [
            row
            for row in odorants
            if re.sub(r"\s+", "", row.name).casefold() == identity
        ]
        if len(candidates) != 1:
            continue
        odorant = candidates[0]
        affected = tuple(
            row for row in aggregate_trials if trial_name in {row.odor_a, row.odor_b}
        )
        conflicts.append(
            Ma2021OdorantNameConflict(
                trial_name=trial_name,
                odor_information_name=odorant.name,
                cas=odorant.cas,
                odor_information_source_row=odorant.source_row,
                affected_trials=tuple(row.trial for row in affected),
                odor_information_row_sha256=odorant.source_row_sha256,
                aggregate_row_sha256s=tuple(row.source_row_sha256 for row in affected),
            )
        )
    return tuple(conflicts)


def _validate_dataset(dataset: Ma2021Dataset, contract: Ma2021WorkbookContract) -> None:
    if len(dataset.odorants) != contract.odorant_count:
        raise Ma2021AdapterError("MA2021_ODORANT_COUNT_MISMATCH", "Odorant count mismatch")
    if len(dataset.aggregate_trials) != contract.trial_count:
        raise Ma2021AdapterError("MA2021_TRIAL_COUNT_MISMATCH", "Aggregate trial count mismatch")
    if len(dataset.participant_trials) != contract.participant_row_count:
        raise Ma2021AdapterError(
            "MA2021_PARTICIPANT_ROW_COUNT_MISMATCH",
            "Participant-trial row count mismatch",
        )
    if len(dataset.participants) != contract.participant_count:
        raise Ma2021AdapterError(
            "MA2021_PARTICIPANT_COUNT_MISMATCH",
            "Distinct participant count mismatch",
        )
    cas_values = [row.cas for row in dataset.odorants]
    odorant_names = [row.name for row in dataset.odorants]
    if len(cas_values) != len(set(cas_values)) or len(odorant_names) != len(set(odorant_names)):
        raise Ma2021AdapterError("MA2021_ODORANT_IDENTITY_DUPLICATE", "Odorants must be unique")
    trials = [row.trial for row in dataset.aggregate_trials]
    if trials != list(range(1, contract.trial_count + 1)):
        raise Ma2021AdapterError("MA2021_TRIAL_SEQUENCE_INVALID", "Trials must be 1..N")
    trial_rows: dict[int, list[Ma2021ParticipantTrial]] = defaultdict(list)
    for participant_row in dataset.participant_trials:
        trial_rows[participant_row.trial].append(participant_row)
    if set(trial_rows) != set(trials) or any(
        len(rows) != contract.participants_per_trial for rows in trial_rows.values()
    ):
        raise Ma2021AdapterError(
            "MA2021_TRIAL_ASSIGNMENT_COUNT_MISMATCH",
            "Each trial must preserve the source participant assignment count",
        )
    if len({(row.subject, row.trial) for row in dataset.participant_trials}) != len(
        dataset.participant_trials
    ):
        raise Ma2021AdapterError(
            "MA2021_PARTICIPANT_TRIAL_DUPLICATE",
            "Participant-trial rows must be unique",
        )
    aggregate_by_trial = {
        aggregate_trial.trial: aggregate_trial
        for aggregate_trial in dataset.aggregate_trials
    }
    for trial, rows in trial_rows.items():
        aggregate = aggregate_by_trial.get(trial)
        participant_shapes = {
            (row.reference_trial, row.repeat_index, row.odor_a, row.odor_b)
            for row in rows
        }
        if aggregate is None or len(participant_shapes) != 1:
            raise Ma2021AdapterError(
                "MA2021_TRIAL_METADATA_CONFLICT",
                "Participant rows do not share one trial metadata shape",
            )
        participant_reference, repeat_index, odor_a, odor_b = next(
            iter(participant_shapes)
        )
        if (repeat_index, odor_a, odor_b) != (
            aggregate.repeat_index,
            aggregate.odor_a,
            aggregate.odor_b,
        ):
            raise Ma2021AdapterError(
                "MA2021_TRIAL_METADATA_CONFLICT",
                "Participant and aggregate trial metadata disagree beyond R-Trial",
            )
        if participant_reference != aggregate.reference_trial and trial not in {
            conflict.trial for conflict in dataset.trial_metadata_conflicts
        }:
            raise Ma2021AdapterError(
                "MA2021_TRIAL_METADATA_CONFLICT_UNRECORDED",
                "R-Trial mismatch must be preserved as a typed conflict",
            )
    expected_conflicts = _trial_metadata_conflicts(
        dataset.aggregate_trials,
        dataset.participant_trials,
    )
    if dataset.trial_metadata_conflicts != expected_conflicts or len(
        expected_conflicts
    ) != contract.metadata_conflict_trial_count:
        raise Ma2021AdapterError(
            "MA2021_METADATA_CONFLICT_COUNT_MISMATCH",
            "R-Trial source conflicts do not match the pinned contract",
        )
    repeat_groups: dict[int, list[Ma2021AggregateTrial]] = defaultdict(list)
    for aggregate_trial in dataset.aggregate_trials:
        if (aggregate_trial.reference_trial is None) != (
            aggregate_trial.repeat_index is None
        ):
            raise Ma2021AdapterError(
                "MA2021_REPEAT_SHAPE_INVALID",
                "R-Trial and Repeat must be supplied together",
            )
        if aggregate_trial.reference_trial is not None:
            repeat_groups[aggregate_trial.reference_trial].append(
                aggregate_trial
            )
    if len(repeat_groups) != contract.duplicate_group_count or any(
        {candidate.repeat_index for candidate in rows} != {1, 2}
        or len(rows) != 2
        for rows in repeat_groups.values()
    ):
        raise Ma2021AdapterError(
            "MA2021_REPEAT_GROUP_COUNT_MISMATCH",
            "Duplicate trial groups must preserve paired repeats",
        )
    if len(dataset.mixture_keys) != contract.unique_mixture_count:
        raise Ma2021AdapterError(
            "MA2021_UNIQUE_MIXTURE_COUNT_MISMATCH",
            "Unique binary-mixture count mismatch",
        )
    expected_name_conflicts = _odorant_name_conflicts(
        dataset.odorants,
        dataset.aggregate_trials,
    )
    if dataset.odorant_name_conflicts != expected_name_conflicts or len(
        expected_name_conflicts
    ) != contract.odorant_name_conflict_count:
        raise Ma2021AdapterError(
            "MA2021_ODORANT_NAME_CONFLICT_COUNT_MISMATCH",
            "Odor-information and trial-name conflicts do not match the pinned contract",
        )
    known = set(odorant_names) | {
        conflict.trial_name for conflict in dataset.odorant_name_conflicts
    }
    if any(
        row.odor_a not in known or row.odor_b not in known
        for row in dataset.aggregate_trials
    ):
        raise Ma2021AdapterError(
            "MA2021_ODORANT_CROSS_REFERENCE_MISSING",
            "Trial references an odorant absent from odor information",
        )


def parse_ma2021_workbook(
    path: str | Path,
    *,
    contract: Ma2021WorkbookContract = MA2021_V2_CONTRACT,
) -> Ma2021Dataset:
    """Parse and validate exact source bytes without executing Office content."""

    artifact_path = Path(path)
    size, digest = _artifact_digest(artifact_path)
    if size != contract.artifact_size:
        raise Ma2021AdapterError("MA2021_ARTIFACT_SIZE_MISMATCH", "Workbook size mismatch")
    if digest != contract.artifact_sha256:
        raise Ma2021AdapterError("MA2021_ARTIFACT_SHA256_MISMATCH", "Workbook hash mismatch")
    required = {
        "odor information",
        "mean value after deleting sub47",
        "individual data",
    }
    with _StrictXlsxReader(artifact_path, contract) as reader:
        sheet_parts = reader.sheet_parts()
        if set(sheet_parts) != required:
            raise Ma2021AdapterError(
                "MA2021_SHEET_SET_MISMATCH",
                "Workbook must contain exactly the three pinned source sheets",
            )
        shared = reader.shared_strings()
        source_sheet_sha256s = {
            name: _sha256_bytes(reader.bytes(part)) for name, part in sheet_parts.items()
        }
        odorants = _parse_odorants(
            reader.rows(sheet_parts["odor information"], shared),
            artifact_sha256=digest,
        )
        aggregate = _parse_aggregate(
            reader.rows(sheet_parts["mean value after deleting sub47"], shared),
            artifact_sha256=digest,
        )
        participants = _parse_participants(
            reader.rows(sheet_parts["individual data"], shared),
            artifact_sha256=digest,
        )
    dataset = Ma2021Dataset(
        artifact_sha256=digest,
        artifact_size=size,
        odorants=odorants,
        aggregate_trials=aggregate,
        participant_trials=participants,
        source_sheet_sha256s=source_sheet_sha256s,
        trial_metadata_conflicts=_trial_metadata_conflicts(
            aggregate,
            participants,
        ),
        odorant_name_conflicts=_odorant_name_conflicts(odorants, aggregate),
    )
    _validate_dataset(dataset, contract)
    return dataset


def ma2021_source_document_input(
    *,
    retrieval_date: date,
    preserved_artifact_path: str,
) -> SourceDocumentInput:
    return SourceDocumentInput(
        schema_version="lab-source-document-v2",
        source_type="PRIMARY_RESEARCH_DATASET",
        title=(
            "A dataset on odor intensity and odor pleasantness of 222 binary mixtures "
            "of 72 key food odorants rated by a sensory panel of 30 trained assessors"
        ),
        artifact_sha256=MA2021_ARTIFACT_SHA256,
        language="en",
        review_state="REVIEWED",
        independence_group=MA2021_SOURCE_FAMILY,
        authors=("Ma, Yue", "Tang, Ke", "Xu, Yan", "Thomas Danguin, Thierry"),
        publisher_or_authority="Recherche Data Gouv",
        identifiers={
            "dataset_doi": MA2021_DATASET_DOI,
            "file_pid": MA2021_FILE_PID,
            "dataset_version": "2.0",
        },
        publication_date=date(2021, 2, 16),
        revision_date=date(2021, 5, 5),
        retrieval_date=retrieval_date,
        edition_or_amendment="V2.0 RELEASED",
        default_locator={
            "dataset_url": f"https://doi.org/{MA2021_DATASET_DOI}",
            "file_pid": MA2021_FILE_PID,
            "artifact_sha256": MA2021_ARTIFACT_SHA256,
            "artifact_size": MA2021_ARTIFACT_SIZE,
        },
        rights={
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": (
                "Etalab Open Licence 2.0; attribution and last-update identification required"
            ),
            "license_url": "https://www.data.gouv.fr/pages/legal/licences/etalab-2.0",
            "redistribution_allowed": True,
            "spdx_identifier": "etalab-2.0",
            "notes": "Rights do not promote scientific or release authority.",
        },
        original_terminology="Source spreadsheet row vectors preserved without recomputation",
        preserved_artifact_path=preserved_artifact_path,
    )


def _artifact_locator() -> dict[str, object]:
    return {
        "dataset_doi": MA2021_DATASET_DOI,
        "file_pid": MA2021_FILE_PID,
        "artifact_sha256": MA2021_ARTIFACT_SHA256,
        "artifact_size": MA2021_ARTIFACT_SIZE,
        "source_version": "2.0",
    }


def ma2021_source_use_constraint(
    *,
    subject_source_version_id: str,
    terms_source_version_id: str,
    terms_retrieval_date: date,
    reviewer_pseudonym: str,
) -> SourceUseConstraintInput:
    return SourceUseConstraintInput(
        subject_source_version_id=subject_source_version_id,
        terms_source_version_id=terms_source_version_id,
        artifact_scope="DATASET",
        artifact_locator=_artifact_locator(),
        channel=MA2021_CHANNEL,
        intended_action="INTERNAL_ANALYSIS",
        purpose_context=MA2021_PURPOSE,
        decision="DECLARED_ALLOWED",
        constraints={
            "max_records": 53_280,
            "max_bytes": MA2021_ARTIFACT_SIZE,
            "attribution_required": True,
        },
        terms_retrieval_date=terms_retrieval_date,
        review_state="REVIEWED",
        reviewer_pseudonym=reviewer_pseudonym,
        legal_review_required=False,
    )


def ma2021_source_use_request(
    *,
    source_version_id: str,
    as_of_date: date,
) -> SourceUseRequest:
    return SourceUseRequest(
        subject_source_version_id=source_version_id,
        artifact_scope="DATASET",
        artifact_locator=_artifact_locator(),
        channel=MA2021_CHANNEL,
        intended_action="INTERNAL_ANALYSIS",
        purpose_context=MA2021_PURPOSE,
        as_of_date=as_of_date,
        requested_records=53_280,
        requested_bytes=MA2021_ARTIFACT_SIZE,
        attribution_planned=True,
        share_alike_planned=False,
        commercial_use=False,
        sublicense=False,
        competing_service=False,
    )


def _trial_payload(row: Ma2021AggregateTrial | Ma2021ParticipantTrial) -> dict[str, object]:
    payload: dict[str, object] = {
        "trial": row.trial,
        "reference_trial": row.reference_trial,
        "repeat_index": row.repeat_index,
        "odor_a": row.odor_a,
        "odor_b": row.odor_b,
        "values": dict(row.values),
    }
    if isinstance(row, Ma2021ParticipantTrial):
        payload["subject"] = row.subject
    else:
        payload["group"] = row.group
    return payload


def _odorant_by_name(dataset: Ma2021Dataset) -> dict[str, Ma2021Odorant]:
    lookup = {row.name: row for row in dataset.odorants}
    by_information_name = {row.name: row for row in dataset.odorants}
    for conflict in dataset.odorant_name_conflicts:
        lookup[conflict.trial_name] = by_information_name[
            conflict.odor_information_name
        ]
    return lookup


def _representative_trials(dataset: Ma2021Dataset) -> dict[int, Ma2021AggregateTrial]:
    representatives: dict[int, Ma2021AggregateTrial] = {}
    for row in dataset.aggregate_trials:
        representatives.setdefault(row.mixture_key, row)
    return representatives


def _aggregate_effective_n_by_trial(dataset: Ma2021Dataset) -> dict[int, int]:
    """Derive N for the source sheet that explicitly excludes subject 47."""

    counts: Counter[int] = Counter(
        row.trial for row in dataset.participant_trials if row.subject != 47
    )
    return {trial.trial: counts[trial.trial] for trial in dataset.aggregate_trials}


def _component_source_identity(
    odorant: Ma2021Odorant,
    *,
    source_position: str,
    trial_name: str,
) -> dict[str, object]:
    return {
        "source_trial_odorant_name": trial_name,
        "source_odor_information_name": odorant.name,
        "source_cas": odorant.cas,
        "source_position": source_position,
        "source_name_conflict": trial_name != odorant.name,
        "source_concentration_mg_ml_text": odorant.concentration_mg_ml,
    }


def iter_ma2021_extraction_specs(dataset: Ma2021Dataset) -> Iterator[Ma2021ExtractionSpec]:
    """Yield one exact B1 extraction blueprint per future native record."""

    study_record_id = _record_id("study-version", "v2")
    study_original = {
        "artifact_sha256": dataset.artifact_sha256,
        "odorant_rows": len(dataset.odorants),
        "aggregate_rows": len(dataset.aggregate_trials),
        "participant_rows": len(dataset.participant_trials),
    }
    yield Ma2021ExtractionSpec(
        output_record_id=study_record_id,
        record_kind="STUDY_VERSION",
        locator={"dataset_doi": MA2021_DATASET_DOI, "file_pid": MA2021_FILE_PID},
        original_value=study_original,
        parsed_value={**study_original, "source_row_vectors_preserved": True},
        input_sha256=dataset.artifact_sha256,
        output_sha256=_stable_json_hash(study_original),
    )
    odorants = _odorant_by_name(dataset)
    representatives = _representative_trials(dataset)
    aggregate_by_trial = {row.trial: row for row in dataset.aggregate_trials}
    aggregate_effective_n = _aggregate_effective_n_by_trial(dataset)
    participant_rows: dict[int, list[Ma2021ParticipantTrial]] = defaultdict(list)
    for row in dataset.participant_trials:
        participant_rows[row.subject].append(row)

    for odorant in sorted(dataset.odorants, key=lambda row: (row.cas, row.name)):
        stimulus_id = _record_id("single-stimulus", odorant.cas)
        stimulus_original = {
            "source_odorant_name": odorant.name,
            "source_cas": odorant.cas,
            "source_trials": odorant.trial_numbers,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=stimulus_id,
            record_kind="SINGLE_ODORANT_STIMULUS",
            locator={"sheet": "odor information", "source_row": odorant.source_row},
            original_value=stimulus_original,
            parsed_value={**stimulus_original, "stimulus_kind": "SINGLE"},
            input_sha256=odorant.source_row_sha256,
            output_sha256=_stable_json_hash(
                {**stimulus_original, "stimulus_kind": "SINGLE"}
            ),
        )
        component_id = _record_id("single-component", odorant.cas)
        source_identity = _component_source_identity(
            odorant,
            source_position="SINGLE",
            trial_name=odorant.name,
        )
        component_output = {
            "stimulus_record_id": stimulus_id,
            "position": 1,
            "source_identity": source_identity,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=component_id,
            record_kind="SINGLE_ODORANT_COMPONENT",
            locator={"sheet": "odor information", "source_row": odorant.source_row},
            original_value=source_identity,
            parsed_value=component_output,
            input_sha256=odorant.source_row_sha256,
            output_sha256=_stable_json_hash(component_output),
        )
        crosswalk_id = _record_id("single-crosswalk", odorant.cas)
        crosswalk_output = {
            "component_record_id": component_id,
            "resolution_status": "EXACT_EXTERNAL_IDENTITY_ONLY",
            "source_identity": source_identity,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=crosswalk_id,
            record_kind="SINGLE_ODORANT_IDENTITY_CROSSWALK",
            locator={"sheet": "odor information", "source_row": odorant.source_row},
            original_value=source_identity,
            parsed_value=crosswalk_output,
            input_sha256=odorant.source_row_sha256,
            output_sha256=_stable_json_hash(crosswalk_output),
        )

    for mixture_key, trial in sorted(representatives.items()):
        stimulus_id = _record_id("stimulus", str(mixture_key))
        source_rows = [
            row for row in dataset.aggregate_trials if row.mixture_key == mixture_key
        ]
        original = {
            "mixture_key": mixture_key,
            "source_trials": [row.trial for row in source_rows],
            "odor_a": trial.odor_a,
            "odor_b": trial.odor_b,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=stimulus_id,
            record_kind="BINARY_MIXTURE_STIMULUS",
            locator={
                "sheet": "mean value after deleting sub47",
                "source_rows": [row.source_row for row in source_rows],
            },
            original_value=original,
            parsed_value={**original, "stimulus_kind": "MIXTURE"},
            input_sha256=_stable_json_hash([row.source_row_sha256 for row in source_rows]),
            output_sha256=_stable_json_hash({**original, "stimulus_kind": "MIXTURE"}),
        )
        for position, (source_position, odorant_name) in enumerate(
            (("A", trial.odor_a), ("B", trial.odor_b)),
            start=1,
        ):
            odorant = odorants[odorant_name]
            component_id = _record_id("component", f"{mixture_key}:{source_position}")
            source_identity = _component_source_identity(
                odorant,
                source_position=source_position,
                trial_name=odorant_name,
            )
            component_output = {
                "stimulus_record_id": stimulus_id,
                "position": position,
                "source_identity": source_identity,
            }
            yield Ma2021ExtractionSpec(
                output_record_id=component_id,
                record_kind="STIMULUS_COMPONENT",
                locator={"sheet": "odor information", "source_row": odorant.source_row},
                original_value={
                    **source_identity,
                    "concentration_mg_ml": odorant.concentration_mg_ml,
                    "solvent": odorant.solvent,
                    "purity": odorant.purity,
                },
                parsed_value=component_output,
                input_sha256=odorant.source_row_sha256,
                output_sha256=_stable_json_hash(component_output),
            )
            crosswalk_id = _record_id("crosswalk", f"{mixture_key}:{source_position}")
            crosswalk_output = {
                "component_record_id": component_id,
                "resolution_status": "EXACT_EXTERNAL_IDENTITY_ONLY",
                "source_identity": source_identity,
            }
            yield Ma2021ExtractionSpec(
                output_record_id=crosswalk_id,
                record_kind="EXTERNAL_IDENTITY_CROSSWALK",
                locator={"sheet": "odor information", "source_row": odorant.source_row},
                original_value=source_identity,
                parsed_value=crosswalk_output,
                input_sha256=odorant.source_row_sha256,
                output_sha256=_stable_json_hash(crosswalk_output),
            )

    for trial in dataset.aggregate_trials:
        condition_id = _record_id("condition", str(trial.trial))
        original = _trial_payload(trial)
        yield Ma2021ExtractionSpec(
            output_record_id=condition_id,
            record_kind="TRIAL_PRESENTATION_CONDITION",
            locator={
                "sheet": "mean value after deleting sub47",
                "source_row": trial.source_row,
            },
            original_value=original,
            parsed_value={**original, "mixture_key": trial.mixture_key},
            input_sha256=trial.source_row_sha256,
            output_sha256=_stable_json_hash({**original, "mixture_key": trial.mixture_key}),
        )
        aggregate_unit_id = _record_id("aggregate-unit", str(trial.trial))
        aggregate_unit_output = {
            "trial": trial.trial,
            "reported_n": aggregate_effective_n[trial.trial],
        }
        yield Ma2021ExtractionSpec(
            output_record_id=aggregate_unit_id,
            record_kind="SOURCE_AGGREGATE_UNIT",
            locator={
                "sheet": "mean value after deleting sub47",
                "source_row": trial.source_row,
            },
            original_value={"trial": trial.trial, "source_sheet": "deleting sub47"},
            parsed_value=aggregate_unit_output,
            input_sha256=trial.source_row_sha256,
            output_sha256=_stable_json_hash(aggregate_unit_output),
        )
        aggregate_observation_id = _record_id("aggregate-observation", str(trial.trial))
        aggregate_output = {
            "trial": trial.trial,
            "endpoint_key": MA2021_AGGREGATE_ENDPOINT_KEY,
            "values": dict(trial.values),
        }
        yield Ma2021ExtractionSpec(
            output_record_id=aggregate_observation_id,
            record_kind="SOURCE_AGGREGATE_VECTOR_OBSERVATION",
            locator={
                "sheet": "mean value after deleting sub47",
                "source_row": trial.source_row,
            },
            original_value=original,
            parsed_value=aggregate_output,
            input_sha256=trial.source_row_sha256,
            output_sha256=_stable_json_hash(aggregate_output),
        )

    for subject, rows in sorted(participant_rows.items()):
        unit_id = _record_id("participant-unit", str(subject))
        unit_output = {"source_subject_token": str(subject), "reported_n": 1}
        yield Ma2021ExtractionSpec(
            output_record_id=unit_id,
            record_kind="PARTICIPANT_UNIT",
            locator={
                "sheet": "individual data",
                "source_subject_token": str(subject),
                "source_rows": [row.source_row for row in rows],
            },
            original_value={"source_subject_token": str(subject)},
            parsed_value=unit_output,
            input_sha256=_stable_json_hash([row.source_row_sha256 for row in rows]),
            output_sha256=_stable_json_hash(unit_output),
        )

    for row in dataset.participant_trials:
        observation_id = _record_id(
            "participant-observation",
            f"{row.subject}:{row.trial}",
        )
        original = _trial_payload(row)
        output = {
            "subject": row.subject,
            "trial": row.trial,
            "endpoint_key": MA2021_PARTICIPANT_ENDPOINT_KEY,
            "values": dict(row.values),
        }
        yield Ma2021ExtractionSpec(
            output_record_id=observation_id,
            record_kind="PARTICIPANT_TRIAL_VECTOR_OBSERVATION",
            locator={"sheet": "individual data", "source_row": row.source_row},
            original_value=original,
            parsed_value=output,
            input_sha256=row.source_row_sha256,
            output_sha256=_stable_json_hash(output),
        )

    for metadata_conflict in dataset.trial_metadata_conflicts:
        conflict_id = _record_id(
            "metadata-conflict",
            str(metadata_conflict.trial),
        )
        original = {
            "trial": metadata_conflict.trial,
            "aggregate_reference_trial": metadata_conflict.aggregate_reference_trial,
            "participant_reference_trial": metadata_conflict.participant_reference_trial,
            "aggregate_source_row": metadata_conflict.aggregate_source_row,
            "participant_source_rows": metadata_conflict.participant_source_rows,
        }
        parsed = {
            **original,
            "conflict_type": "R_TRIAL_IDENTIFIER_MISMATCH",
            "conflict_state": "OPEN",
            "source_values_preserved": True,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=conflict_id,
            record_kind="SOURCE_METADATA_CONFLICT",
            locator={
                "aggregate_sheet": "mean value after deleting sub47",
                "aggregate_source_row": metadata_conflict.aggregate_source_row,
                "participant_sheet": "individual data",
                "participant_source_rows": metadata_conflict.participant_source_rows,
            },
            original_value=original,
            parsed_value=parsed,
            input_sha256=_stable_json_hash(
                [
                    metadata_conflict.aggregate_row_sha256,
                    *metadata_conflict.participant_row_sha256s,
                ]
            ),
            output_sha256=_stable_json_hash(parsed),
        )

    for identity_conflict in dataset.odorant_name_conflicts:
        conflict_id = _record_id(
            "odorant-name-conflict",
            identity_conflict.trial_name,
        )
        original = {
            "trial_name": identity_conflict.trial_name,
            "odor_information_name": identity_conflict.odor_information_name,
            "cas": identity_conflict.cas,
            "odor_information_source_row": identity_conflict.odor_information_source_row,
            "affected_trials": identity_conflict.affected_trials,
        }
        parsed = {
            **original,
            "conflict_type": "SOURCE_OWNED_SPELLING_MISMATCH",
            "resolution_scope": "THIS_SOURCE_GRAPH_ONLY",
            "source_values_preserved": True,
        }
        yield Ma2021ExtractionSpec(
            output_record_id=conflict_id,
            record_kind="SOURCE_IDENTITY_CONFLICT",
            locator={
                "odor_information_sheet": "odor information",
                "odor_information_source_row": identity_conflict.odor_information_source_row,
                "aggregate_sheet": "mean value after deleting sub47",
                "affected_trials": identity_conflict.affected_trials,
            },
            original_value=original,
            parsed_value=parsed,
            input_sha256=_stable_json_hash(
                [
                    identity_conflict.odor_information_row_sha256,
                    *identity_conflict.aggregate_row_sha256s,
                ]
            ),
            output_sha256=_stable_json_hash(parsed),
        )

    expected = (
        1
        + 3 * len(dataset.odorants)
        + len(representatives)
        + 4 * len(representatives)
        + 3 * len(aggregate_by_trial)
        + len(participant_rows)
        + len(dataset.participant_trials)
        + len(dataset.trial_metadata_conflicts)
        + len(dataset.odorant_name_conflicts)
    )
    # This assertion is an internal construction invariant, not a source claim.
    if expected < 1:
        raise AssertionError("Ma 2021 extraction graph must not be empty")


def ma2021_dry_run_extraction_ids(dataset: Ma2021Dataset) -> dict[str, str]:
    """Return synthetic IDs that cannot satisfy B1 persistence admission."""

    return {
        spec.output_record_id: _record_id("dry-run-extraction", spec.output_record_id)
        for spec in iter_ma2021_extraction_specs(dataset)
    }


def _extraction_id(extraction_ids: Mapping[str, str], record_id: str) -> str:
    try:
        return extraction_ids[record_id]
    except KeyError as exc:
        raise Ma2021AdapterError(
            "MA2021_EXTRACTION_BINDING_MISSING",
            f"No B1 extraction ID for native record {record_id}",
        ) from exc


def _vector_scale() -> dict[str, object]:
    return {
        "type": "BOUNDED_SOURCE_RATING_VECTOR",
        "endpoint_bounds": {
            endpoint: {
                "minimum": "0",
                "maximum": "11" if endpoint in {"IAmix", "IBmix"} else "10",
            }
            for endpoint in MA2021_ENDPOINTS
        },
        "source_anomaly_preserved": (
            "Source IAmix/IBmix values reach 11 despite the nominal 0-10 scale."
        ),
    }


def _source_presentation(
    trial: Ma2021AggregateTrial,
    *,
    single_stimulus_ids: Mapping[str, str],
    mixture_stimulus_id: str,
) -> tuple[dict[str, object], ...]:
    return (
        {
            "position": 1,
            "stimulus_version_id": single_stimulus_ids[trial.odor_a],
            "role": "REFERENCE",
            "context": {
                "source_role": "ODOR_A_ALONE",
                "source_endpoint_keys": ("IA", "PA"),
            },
        },
        {
            "position": 2,
            "stimulus_version_id": single_stimulus_ids[trial.odor_b],
            "role": "COMPARATOR",
            "context": {
                "source_role": "ODOR_B_ALONE",
                "source_endpoint_keys": ("IB", "PB"),
            },
        },
        {
            "position": 3,
            "stimulus_version_id": mixture_stimulus_id,
            "role": "TARGET",
            "context": {
                "source_role": "BINARY_MIXTURE",
                "source_endpoint_keys": ("IAmix", "IBmix", "IAB", "PAB"),
            },
        },
    )


def build_ma2021_external_study_input(
    dataset: Ma2021Dataset,
    *,
    source_version_id: str,
    extraction_ids: Mapping[str, str],
    as_of_date: date,
) -> ExternalStudyInput:
    """Build the native authority-false graph; this function performs no writes."""

    study_record_id = _record_id("study-version", "v2")
    study_id = _record_id("study", MA2021_DATASET_DOI)
    odorants = _odorant_by_name(dataset)
    representatives = _representative_trials(dataset)
    stimuli: list[ExternalStimulusInput] = []
    components: list[ExternalStimulusComponentInput] = []
    crosswalks: list[ExternalIdentityCrosswalkInput] = []
    single_stimulus_ids: dict[str, str] = {}
    for odorant in sorted(dataset.odorants, key=lambda row: (row.cas, row.name)):
        stimulus_id = _record_id("single-stimulus", odorant.cas)
        single_stimulus_ids[odorant.name] = stimulus_id
        stimuli.append(
            ExternalStimulusInput(
                record_id=stimulus_id,
                stimulus_key=f"ma2021-single-{odorant.cas}",
                source_extraction_id=_extraction_id(extraction_ids, stimulus_id),
                stimulus_kind="SINGLE",
                label=odorant.name,
                matrix={
                    "state": "SOURCE_REPORTED",
                    "source_odorant_name": odorant.name,
                    "source_cas": odorant.cas,
                },
                preparation={
                    "state": "SOURCE_PROTOCOL_BOUND",
                    "concentration_mg_ml_text": odorant.concentration_mg_ml,
                    "solvent": odorant.solvent,
                    "purity": odorant.purity,
                    "no_project_formula_or_stock_binding": True,
                },
                context={
                    "source_odor_information_row": odorant.source_row,
                    "source_trial_presentations": odorant.trial_numbers,
                },
            )
        )
        component_id = _record_id("single-component", odorant.cas)
        source_identity = _component_source_identity(
            odorant,
            source_position="SINGLE",
            trial_name=odorant.name,
        )
        components.append(
            ExternalStimulusComponentInput(
                record_id=component_id,
                stimulus_version_id=stimulus_id,
                position=1,
                component_key=f"source-single-{odorant.cas}",
                source_extraction_id=_extraction_id(extraction_ids, component_id),
                source_identity=source_identity,
                quantity_value_text=None,
                quantity_unit=None,
                quantity_basis=None,
                concentration_value_text=_canonical_plain_decimal(
                    odorant.concentration_mg_ml,
                    f"odor information row {odorant.source_row} concentration",
                ),
                concentration_unit="mg/mL",
                concentration_basis="SOURCE_REPORTED_STOCK_SOLUTION",
                carrier={"state": "SOURCE_REPORTED", "solvent": odorant.solvent},
                purity={"state": "SOURCE_REPORTED", "value": odorant.purity},
                role="SOURCE_SINGLE_ODORANT",
            )
        )
        crosswalk_id = _record_id("single-crosswalk", odorant.cas)
        crosswalks.append(
            ExternalIdentityCrosswalkInput(
                record_id=crosswalk_id,
                component_id=component_id,
                source_extraction_id=_extraction_id(extraction_ids, crosswalk_id),
                resolution_status="EXACT_EXTERNAL_IDENTITY_ONLY",
                material_id=None,
                source_identity=source_identity,
                resolved_identity={
                    "source_odor_information_name": odorant.name,
                    "cas": odorant.cas,
                    "project_material_binding": None,
                },
                evidence={
                    "route": "SOURCE_ODOR_INFORMATION_LITERAL",
                    "source_row_sha256": odorant.source_row_sha256,
                },
            )
        )
    by_information_name = {row.name: row for row in dataset.odorants}
    for name_conflict in dataset.odorant_name_conflicts:
        resolved_odorant = by_information_name[
            name_conflict.odor_information_name
        ]
        single_stimulus_ids[name_conflict.trial_name] = single_stimulus_ids[
            resolved_odorant.name
        ]

    stimulus_ids: dict[int, str] = {}
    for mixture_key, trial in sorted(representatives.items()):
        stimulus_id = _record_id("stimulus", str(mixture_key))
        stimulus_ids[mixture_key] = stimulus_id
        stimuli.append(
            ExternalStimulusInput(
                record_id=stimulus_id,
                stimulus_key=f"ma2021-mixture-{mixture_key:03d}",
                source_extraction_id=_extraction_id(extraction_ids, stimulus_id),
                stimulus_kind="MIXTURE",
                label=f"{trial.odor_a} + {trial.odor_b}",
                matrix={
                    "state": "SOURCE_REPORTED",
                    "components": (trial.odor_a, trial.odor_b),
                },
                preparation={
                    "state": "SOURCE_PROTOCOL_BOUND",
                    "no_project_formula_or_stock_binding": True,
                },
                context={
                    "source_mixture_key": mixture_key,
                    "source_trial_presentations": tuple(
                        row.trial
                        for row in dataset.aggregate_trials
                        if row.mixture_key == mixture_key
                    ),
                },
            )
        )
        for position, (source_position, odorant_name) in enumerate(
            (("A", trial.odor_a), ("B", trial.odor_b)),
            start=1,
        ):
            odorant = odorants[odorant_name]
            component_id = _record_id("component", f"{mixture_key}:{source_position}")
            source_identity = _component_source_identity(
                odorant,
                source_position=source_position,
                trial_name=odorant_name,
            )
            components.append(
                ExternalStimulusComponentInput(
                    record_id=component_id,
                    stimulus_version_id=stimulus_id,
                    position=position,
                    component_key=f"source-{source_position.casefold()}-{odorant.cas}",
                    source_extraction_id=_extraction_id(extraction_ids, component_id),
                    source_identity=source_identity,
                    quantity_value_text=None,
                    quantity_unit=None,
                    quantity_basis=None,
                    concentration_value_text=_canonical_plain_decimal(
                        odorant.concentration_mg_ml,
                        f"odor information row {odorant.source_row} concentration",
                    ),
                    concentration_unit="mg/mL",
                    concentration_basis="SOURCE_REPORTED_STOCK_SOLUTION",
                    carrier={"state": "SOURCE_REPORTED", "solvent": odorant.solvent},
                    purity={"state": "SOURCE_REPORTED", "value": odorant.purity},
                    role=f"SOURCE_COMPONENT_{source_position}",
                )
            )
            crosswalk_id = _record_id("crosswalk", f"{mixture_key}:{source_position}")
            crosswalks.append(
                ExternalIdentityCrosswalkInput(
                    record_id=crosswalk_id,
                    component_id=component_id,
                    source_extraction_id=_extraction_id(extraction_ids, crosswalk_id),
                    resolution_status=(
                        "EXACT_EXTERNAL_IDENTITY_ONLY"
                        if odorant_name == odorant.name
                        else "CONFLICT"
                    ),
                    material_id=None,
                    source_identity=source_identity,
                    resolved_identity={
                        "source_trial_odorant_name": odorant_name,
                        "source_odor_information_name": odorant.name,
                        "cas": odorant.cas,
                        "project_material_binding": None,
                    },
                    evidence={
                        "route": (
                            "SOURCE_LITERAL_CAS_AND_NAME"
                            if odorant_name == odorant.name
                            else "SOURCE_SCOPED_TRIAL_NUMBER_AND_SPACE_ONLY_NAME_LINK"
                        ),
                        "source_row_sha256": odorant.source_row_sha256,
                        "source_values_preserved": True,
                    },
                )
            )

    conditions: list[ExternalConditionInput] = []
    aggregate_units: list[ExternalExperimentalUnitInput] = []
    aggregate_observations: list[ExternalObservationInput] = []
    aggregate_effective_n = _aggregate_effective_n_by_trial(dataset)
    scale = _vector_scale()
    for trial in dataset.aggregate_trials:
        stimulus_id = stimulus_ids[trial.mixture_key]
        condition_id = _record_id("condition", str(trial.trial))
        conditions.append(
            ExternalConditionInput(
                record_id=condition_id,
                condition_key=f"ma2021-trial-{trial.trial:03d}",
                source_extraction_id=_extraction_id(extraction_ids, condition_id),
                condition_role="TEST",
                label=f"Trial {trial.trial}: {trial.odor_a} + {trial.odor_b}",
                primary_stimulus_version_id=stimulus_id,
                factors={
                    "source_group": trial.group,
                    "source_repeat_index": trial.repeat_index,
                    "source_reference_trial": trial.reference_trial,
                },
                context={
                    "source_trial": trial.trial,
                    "source_presentation_roles": ("ODOR_A", "ODOR_B", "BINARY_MIXTURE"),
                    "source_row_sha256": trial.source_row_sha256,
                },
            )
        )
        aggregate_unit_id = _record_id("aggregate-unit", str(trial.trial))
        aggregate_units.append(
            ExternalExperimentalUnitInput(
                record_id=aggregate_unit_id,
                unit_key=f"ma2021-source-aggregate-trial-{trial.trial:03d}",
                source_extraction_id=_extraction_id(extraction_ids, aggregate_unit_id),
                unit_grain="AGGREGATE",
                parent_unit_id=None,
                pseudonymous_token=None,
                reported_n=aggregate_effective_n[trial.trial],
                context={
                    "source_sheet": "mean value after deleting sub47",
                    "source_reported_not_recomputed": True,
                    "effective_n_derived_from_source_exclusion": True,
                },
            )
        )
        aggregate_observation_id = _record_id("aggregate-observation", str(trial.trial))
        aggregate_observations.append(
            ExternalObservationInput(
                record_id=aggregate_observation_id,
                observation_key=f"ma2021-source-aggregate-trial-{trial.trial:03d}-vector",
                source_extraction_id=_extraction_id(
                    extraction_ids,
                    aggregate_observation_id,
                ),
                condition_id=condition_id,
                experimental_unit_id=aggregate_unit_id,
                primary_stimulus_version_id=stimulus_id,
                trial_key=f"trial-{trial.trial:03d}",
                session_key=None,
                repeat_index=trial.repeat_index,
                presentation=_source_presentation(
                    trial,
                    single_stimulus_ids=single_stimulus_ids,
                    mixture_stimulus_id=stimulus_id,
                ),
                endpoint_key=MA2021_AGGREGATE_ENDPOINT_KEY,
                value=dict(trial.values),
                original_unit="SOURCE_SCALE_SCORE",
                scale=scale,
                timepoint={"state": "NOT_REPORTED"},
                replicate_index=None,
                observation_grain="STUDY_AGGREGATE",
                aggregation_statistic="MEAN",
                missingness="OBSERVED",
                uncertainty={
                    "state": "DISPERSION_NOT_REPORTED",
                    "reported_n": aggregate_effective_n[trial.trial],
                },
                limitations=(
                    "SOURCE_SHEET_EXCLUDES_SUBJECT_47",
                    "SOURCE_REPORTED_AGGREGATE_NOT_RECOMPUTED",
                ),
            )
        )

    participant_units: list[ExternalExperimentalUnitInput] = []
    participant_unit_ids: dict[int, str] = {}
    for subject in dataset.participants:
        unit_id = _record_id("participant-unit", str(subject))
        participant_unit_ids[subject] = unit_id
        participant_units.append(
            ExternalExperimentalUnitInput(
                record_id=unit_id,
                unit_key=f"ma2021-participant-{subject:03d}",
                source_extraction_id=_extraction_id(extraction_ids, unit_id),
                unit_grain="PARTICIPANT",
                parent_unit_id=None,
                pseudonymous_token=f"ma2021-source-subject-{subject:03d}",
                reported_n=1,
                context={
                    "source_identifier_is_pseudonymous": True,
                    "trained_assessor": True,
                },
            )
        )
    participant_observations: list[ExternalObservationInput] = []
    aggregate_by_trial = {trial.trial: trial for trial in dataset.aggregate_trials}
    for row in dataset.participant_trials:
        observation_id = _record_id(
            "participant-observation",
            f"{row.subject}:{row.trial}",
        )
        condition_id = _record_id("condition", str(row.trial))
        aggregate_trial = aggregate_by_trial[row.trial]
        stimulus_id = stimulus_ids[aggregate_trial.mixture_key]
        participant_observations.append(
            ExternalObservationInput(
                record_id=observation_id,
                observation_key=(
                    f"ma2021-participant-{row.subject:03d}-trial-{row.trial:03d}-vector"
                ),
                source_extraction_id=_extraction_id(extraction_ids, observation_id),
                condition_id=condition_id,
                experimental_unit_id=participant_unit_ids[row.subject],
                primary_stimulus_version_id=stimulus_id,
                trial_key=f"trial-{row.trial:03d}",
                session_key=None,
                repeat_index=row.repeat_index,
                presentation=_source_presentation(
                    aggregate_trial,
                    single_stimulus_ids=single_stimulus_ids,
                    mixture_stimulus_id=stimulus_id,
                ),
                endpoint_key=MA2021_PARTICIPANT_ENDPOINT_KEY,
                value=dict(row.values),
                original_unit="SOURCE_SCALE_SCORE",
                scale=scale,
                timepoint={"state": "NOT_REPORTED"},
                replicate_index=None,
                observation_grain="INDIVIDUAL",
                aggregation_statistic="RAW",
                missingness="OBSERVED",
                uncertainty={"state": "NOT_REPORTED"},
                limitations=("SOURCE_PARTICIPANT_TOKEN_IS_PSEUDONYMOUS",),
            )
        )

    conflicts: list[ExternalStudyConflictInput] = []
    for metadata_conflict in dataset.trial_metadata_conflicts:
        conflict_id = _record_id(
            "metadata-conflict",
            str(metadata_conflict.trial),
        )
        condition_id = _record_id("condition", str(metadata_conflict.trial))
        conflicts.append(
            ExternalStudyConflictInput(
                record_id=conflict_id,
                conflict_key=(
                    f"ma2021-r-trial-mismatch-{metadata_conflict.trial:03d}"
                ),
                conflict_type="OTHER",
                conflict_state="OPEN",
                source_extraction_id=_extraction_id(extraction_ids, conflict_id),
                related_extraction_id=_extraction_id(extraction_ids, condition_id),
                details={
                    "field": "R-Trial",
                    "trial": metadata_conflict.trial,
                    "aggregate_reference_trial": (
                        metadata_conflict.aggregate_reference_trial
                    ),
                    "participant_reference_trial": (
                        metadata_conflict.participant_reference_trial
                    ),
                    "aggregate_source_row": metadata_conflict.aggregate_source_row,
                    "participant_source_rows": (
                        metadata_conflict.participant_source_rows
                    ),
                    "source_values_preserved": True,
                    "resolution": "UNRESOLVED_SOURCE_TABLE_CONFLICT",
                },
            )
        )

    for identity_conflict in dataset.odorant_name_conflicts:
        conflict_id = _record_id(
            "odorant-name-conflict",
            identity_conflict.trial_name,
        )
        related_trial = identity_conflict.affected_trials[0]
        related_condition_id = _record_id("condition", str(related_trial))
        conflicts.append(
            ExternalStudyConflictInput(
                record_id=conflict_id,
                conflict_key="ma2021-odorant-source-name-spacing-conflict",
                conflict_type="IDENTITY",
                conflict_state="NARROWED",
                source_extraction_id=_extraction_id(extraction_ids, conflict_id),
                related_extraction_id=_extraction_id(
                    extraction_ids,
                    related_condition_id,
                ),
                details={
                    "trial_name": identity_conflict.trial_name,
                    "odor_information_name": identity_conflict.odor_information_name,
                    "cas": identity_conflict.cas,
                    "affected_trials": identity_conflict.affected_trials,
                    "resolution_scope": "THIS_SOURCE_GRAPH_ONLY",
                    "source_values_preserved": True,
                    "project_material_binding": None,
                },
            )
        )

    participants_per_trial = min(
        Counter(row.trial for row in dataset.participant_trials).values()
    )
    duplicate_group_count = len(
        {
            row.reference_trial
            for row in dataset.aggregate_trials
            if row.reference_trial is not None
        }
    )
    return ExternalStudyInput(
        record_id=study_record_id,
        study_id=study_id,
        study_key="ma-2021-v2",
        source_version_id=source_version_id,
        source_extraction_id=_extraction_id(extraction_ids, study_record_id),
        source_family=MA2021_SOURCE_FAMILY,
        title=(
            "Odor intensity and pleasantness of 222 binary mixtures "
            "rated by trained assessors"
        ),
        study_domain="HUMAN_SENSORY",
        design={
            "participant_units": len(dataset.participants),
            "participant_trial_rows": len(dataset.participant_trials),
            "participants_assigned_per_trial": participants_per_trial,
            "trial_presentations": len(dataset.aggregate_trials),
            "unique_single_odorant_stimuli": len(dataset.odorants),
            "unique_binary_mixtures": len(dataset.mixture_keys),
            "total_unique_source_stimuli": (
                len(dataset.odorants) + len(dataset.mixture_keys)
            ),
            "duplicate_trial_groups": duplicate_group_count,
            "source_metadata_conflicts": len(dataset.trial_metadata_conflicts),
            "source_identity_conflicts": len(dataset.odorant_name_conflicts),
            "vector_endpoints": MA2021_ENDPOINTS,
        },
        protocol={
            "source_row_vector_persistence": True,
            "per_endpoint_projection": "DETERMINISTIC_READ_ONLY_ONLY",
            "source_aggregate_sheet": "mean value after deleting sub47",
            "source_aggregate_recomputed": False,
            "source_subject_47_preserved_in_individual_rows": True,
            "source_aggregate_subject_47_exclusion_preserved": True,
            "source_aggregate_effective_n_counts": dict(
                sorted(
                    (str(value), count)
                    for value, count in Counter(
                        aggregate_effective_n.values()
                    ).items()
                )
            ),
            "scientific_authority": False,
        },
        source_use_request=ma2021_source_use_request(
            source_version_id=source_version_id,
            as_of_date=as_of_date,
        ),
        stimuli=tuple(stimuli),
        components=tuple(components),
        conditions=tuple(conditions),
        experimental_units=tuple(participant_units + aggregate_units),
        observations=tuple(participant_observations + aggregate_observations),
        crosswalks=tuple(crosswalks),
        conflicts=tuple(conflicts),
        adapter_name=MA2021_ADAPTER_NAME,
        adapter_version=MA2021_ADAPTER_VERSION,
        adapter_config={
            "artifact_sha256": dataset.artifact_sha256,
            "artifact_size": dataset.artifact_size,
            "dataset_version": "2.0",
            "file_pid": MA2021_FILE_PID,
            "b1_extraction_acceptance_required": True,
            "authority_promoted": False,
        },
    )


def ma2021_native_counts(command: ExternalStudyInput) -> dict[str, int]:
    return {
        "studies": 1,
        "stimuli": len(command.stimuli),
        "components": len(command.components),
        "conditions": len(command.conditions),
        "experimental_units": len(command.experimental_units),
        "observations": len(command.observations),
        "crosswalks": len(command.crosswalks),
        "conflicts": len(command.conflicts),
        "total_records": (
            1
            + len(command.stimuli)
            + len(command.components)
            + len(command.conditions)
            + len(command.experimental_units)
            + len(command.observations)
            + len(command.crosswalks)
            + len(command.conflicts)
        ),
    }


def ma2021_extraction_spec_counts(
    specs: Iterable[Ma2021ExtractionSpec],
) -> dict[str, int]:
    return dict(Counter(spec.record_kind for spec in specs))


__all__ = [
    "MA2021_ADAPTER_NAME",
    "MA2021_ADAPTER_VERSION",
    "MA2021_AGGREGATE_ENDPOINT_KEY",
    "MA2021_ARTIFACT_SHA256",
    "MA2021_ARTIFACT_SIZE",
    "MA2021_DATASET_DOI",
    "MA2021_ENDPOINTS",
    "MA2021_FILE_PID",
    "MA2021_PARTICIPANT_ENDPOINT_KEY",
    "MA2021_SOURCE_FAMILY",
    "MA2021_V2_CONTRACT",
    "Ma2021AdapterError",
    "Ma2021AggregateTrial",
    "Ma2021Dataset",
    "Ma2021ExtractionSpec",
    "Ma2021Odorant",
    "Ma2021ParticipantTrial",
    "Ma2021WorkbookContract",
    "build_ma2021_external_study_input",
    "iter_ma2021_extraction_specs",
    "ma2021_dry_run_extraction_ids",
    "ma2021_extraction_spec_counts",
    "ma2021_native_counts",
    "ma2021_source_document_input",
    "ma2021_source_use_constraint",
    "ma2021_source_use_request",
    "parse_ma2021_workbook",
]
