from __future__ import annotations

import hashlib
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.adapters.ma_2021 import (
    MA2021_AGGREGATE_ENDPOINT_KEY,
    MA2021_ARTIFACT_SHA256,
    MA2021_ARTIFACT_SIZE,
    MA2021_PARTICIPANT_ENDPOINT_KEY,
    Ma2021AdapterError,
    Ma2021WorkbookContract,
    build_ma2021_external_study_input,
    iter_ma2021_extraction_specs,
    ma2021_dry_run_extraction_ids,
    ma2021_native_counts,
    ma2021_source_document_input,
    ma2021_source_use_constraint,
    ma2021_source_use_request,
    parse_ma2021_workbook,
)
from app.services.lab_external_studies import LabExternalStudyServiceMixin

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
SOURCE_VERSION_ID = "11111111-1111-4111-8111-111111111111"
TERMS_VERSION_ID = "22222222-2222-4222-8222-222222222222"


def _column_name(index: int) -> str:
    value = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        value = chr(ord("A") + remainder) + value
    return value


def _sheet_xml(
    rows: list[list[object | None]],
    *,
    empty_shared_formula: bool = False,
) -> bytes:
    root = ElementTree.Element(f"{{{SHEET_NS}}}worksheet")
    data = ElementTree.SubElement(root, f"{{{SHEET_NS}}}sheetData")
    for row_index, values in enumerate(rows, start=1):
        row = ElementTree.SubElement(data, f"{{{SHEET_NS}}}row", {"r": str(row_index)})
        for column_index, value in enumerate(values, start=1):
            if value is None:
                continue
            reference = f"{_column_name(column_index)}{row_index}"
            if isinstance(value, str):
                cell = ElementTree.SubElement(
                    row,
                    f"{{{SHEET_NS}}}c",
                    {"r": reference, "t": "inlineStr"},
                )
                inline = ElementTree.SubElement(cell, f"{{{SHEET_NS}}}is")
                ElementTree.SubElement(inline, f"{{{SHEET_NS}}}t").text = value
            else:
                cell = ElementTree.SubElement(row, f"{{{SHEET_NS}}}c", {"r": reference})
                ElementTree.SubElement(cell, f"{{{SHEET_NS}}}v").text = str(value)
            if empty_shared_formula and row_index == 2 and column_index == 1:
                ElementTree.SubElement(
                    cell,
                    f"{{{SHEET_NS}}}f",
                    {"t": "shared", "si": "0"},
                )
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _fixture_rows(*, out_of_range: bool = False) -> dict[str, list[list[object | None]]]:
    endpoint_headers = ["IA  ", "IAmix", "IB ", "IBmix", "IAB  ", "PA", "PB", "PAB"]
    values: list[object] = [12 if out_of_range else 5, 5, 6, 6, 7, 4, 5, 5]
    return {
        "odor information": [
            ["CAS.", "Odorant", "Odor", "Cons.(mg/mL)", "Solvent", "Purity", "Trial number"],
            ["111-11-1", "odorant A", "alpha", 1.25, "mineral oil", "99%", "1"],
            ["222-22-2", "odorant B", "beta", 0.5, "mineral oil", "98%", "1"],
        ],
        "mean value after deleting sub47": [
            ["Trial", "R-Trial", "Repeat", "Group", "odor A", "odor B", *endpoint_headers],
            [1, None, None, "E", "odorant A", "odorant B", *values],
        ],
        "individual data": [
            ["Sub.", "Trial", "R-Trial", "Repeat", "odor A", "odor B", *endpoint_headers],
            [1, 1, None, None, "odorant A", "odorant B", *values],
            [2, 1, None, None, "odorant A", "odorant B", *values],
        ],
    }


def _write_workbook(
    path: Path,
    *,
    empty_shared_formula: bool = False,
    late_entity_declaration: bool = False,
    external_relationship: bool = False,
    out_of_range: bool = False,
) -> Ma2021WorkbookContract:
    rows = _fixture_rows(out_of_range=out_of_range)
    sheets = tuple(rows)
    content_types = ElementTree.Element(f"{{{CONTENT_NS}}}Types")
    ElementTree.SubElement(
        content_types,
        f"{{{CONTENT_NS}}}Default",
        {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"},
    )
    ElementTree.SubElement(
        content_types,
        f"{{{CONTENT_NS}}}Default",
        {"Extension": "xml", "ContentType": "application/xml"},
    )
    root_relationships = ElementTree.Element(f"{{{REL_NS}}}Relationships")
    ElementTree.SubElement(
        root_relationships,
        f"{{{REL_NS}}}Relationship",
        {
            "Id": "rId1",
            "Type": f"{DOC_REL_NS}/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    workbook = ElementTree.Element(f"{{{SHEET_NS}}}workbook")
    sheet_container = ElementTree.SubElement(workbook, f"{{{SHEET_NS}}}sheets")
    workbook_relationships = ElementTree.Element(f"{{{REL_NS}}}Relationships")
    for index, name in enumerate(sheets, start=1):
        ElementTree.SubElement(
            sheet_container,
            f"{{{SHEET_NS}}}sheet",
            {
                "name": name,
                "sheetId": str(index),
                f"{{{DOC_REL_NS}}}id": f"rId{index}",
            },
        )
        ElementTree.SubElement(
            workbook_relationships,
            f"{{{REL_NS}}}Relationship",
            {
                "Id": f"rId{index}",
                "Type": f"{DOC_REL_NS}/worksheet",
                "Target": f"worksheets/sheet{index}.xml",
            },
        )
    if external_relationship:
        ElementTree.SubElement(
            workbook_relationships,
            f"{{{REL_NS}}}Relationship",
            {
                "Id": "rIdExternal",
                "Type": f"{DOC_REL_NS}/externalLink",
                "Target": "https://example.invalid/data.xlsx",
                "TargetMode": "External",
            },
        )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            ElementTree.tostring(content_types, encoding="utf-8", xml_declaration=True),
        )
        archive.writestr(
            "_rels/.rels",
            ElementTree.tostring(root_relationships, encoding="utf-8", xml_declaration=True),
        )
        archive.writestr(
            "xl/workbook.xml",
            ElementTree.tostring(workbook, encoding="utf-8", xml_declaration=True),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            ElementTree.tostring(
                workbook_relationships,
                encoding="utf-8",
                xml_declaration=True,
            ),
        )
        for index, name in enumerate(sheets, start=1):
            payload = _sheet_xml(
                rows[name],
                empty_shared_formula=empty_shared_formula and index == 2,
            )
            if late_entity_declaration and index == 2:
                root = payload.split(b"?>", 1)[1]
                payload = (
                    b'<?xml version="1.0" encoding="utf-8"?>'
                    + b"<!--"
                    + b"a" * 5000
                    + b"-->"
                    + b'<!DOCTYPE worksheet [<!ENTITY late "blocked">]>'
                    + root
                )
            archive.writestr(f"xl/worksheets/sheet{index}.xml", payload)
    raw = path.read_bytes()
    return Ma2021WorkbookContract(
        artifact_sha256=hashlib.sha256(raw).hexdigest(),
        artifact_size=len(raw),
        odorant_count=2,
        trial_count=1,
        participant_count=2,
        participant_row_count=2,
        participants_per_trial=2,
        duplicate_group_count=0,
        unique_mixture_count=1,
    )


def test_tiny_source_vectors_map_to_existing_native_graph(tmp_path: Path) -> None:
    workbook = tmp_path / "ma-tiny.xlsx"
    contract = _write_workbook(workbook)
    dataset = parse_ma2021_workbook(workbook, contract=contract)
    extraction_ids = ma2021_dry_run_extraction_ids(dataset)
    command = build_ma2021_external_study_input(
        dataset,
        source_version_id=SOURCE_VERSION_ID,
        extraction_ids=extraction_ids,
        as_of_date=date(2026, 8, 11),
    )
    LabExternalStudyServiceMixin._validate_external_graph(command)

    assert ma2021_native_counts(command) == {
        "studies": 1,
        "stimuli": 3,
        "components": 4,
        "conditions": 1,
        "experimental_units": 3,
        "observations": 3,
        "crosswalks": 4,
        "conflicts": 0,
        "total_records": 19,
    }
    assert {row.endpoint_key for row in command.observations} == {
        MA2021_PARTICIPANT_ENDPOINT_KEY,
        MA2021_AGGREGATE_ENDPOINT_KEY,
    }
    aggregate = next(
        row for row in command.experimental_units if row.unit_grain == "AGGREGATE"
    )
    assert aggregate.reported_n == 2
    assert tuple(
        (row["position"], row["role"])
        for row in command.observations[0].presentation
    ) == ((1, "REFERENCE"), (2, "COMPARATOR"), (3, "TARGET"))
    assert command.adapter_config["authority_promoted"] is False


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    (
        ({"empty_shared_formula": True}, "OOXML_ACTIVE_FORMULA"),
        ({"late_entity_declaration": True}, "OOXML_XML_ENTITY_DECLARATION"),
        ({"external_relationship": True}, "OOXML_EXTERNAL_RELATIONSHIP"),
        ({"out_of_range": True}, "MA2021_SCALE_OUT_OF_RANGE"),
    ),
)
def test_strict_parser_rejects_active_or_invalid_source_bytes(
    tmp_path: Path,
    mutation: dict[str, bool],
    expected_code: str,
) -> None:
    workbook = tmp_path / f"mutated-{expected_code}.xlsx"
    contract = _write_workbook(workbook, **mutation)
    with pytest.raises(Ma2021AdapterError) as error:
        parse_ma2021_workbook(workbook, contract=contract)
    assert error.value.code == expected_code


def test_strict_parser_requires_exact_artifact_hash(tmp_path: Path) -> None:
    workbook = tmp_path / "wrong-hash.xlsx"
    contract = _write_workbook(workbook)
    wrong = Ma2021WorkbookContract(
        artifact_sha256="0" * 64,
        artifact_size=contract.artifact_size,
        odorant_count=contract.odorant_count,
        trial_count=contract.trial_count,
        participant_count=contract.participant_count,
        participant_row_count=contract.participant_row_count,
        participants_per_trial=contract.participants_per_trial,
        duplicate_group_count=contract.duplicate_group_count,
        unique_mixture_count=contract.unique_mixture_count,
    )
    with pytest.raises(Ma2021AdapterError) as error:
        parse_ma2021_workbook(workbook, contract=wrong)
    assert error.value.code == "MA2021_ARTIFACT_SHA256_MISMATCH"


def test_b1_source_and_operation_rights_are_exact_and_internal_only() -> None:
    source = ma2021_source_document_input(
        retrieval_date=date(2026, 8, 11),
        preserved_artifact_path=(
            "archive/source_quarantine/ma_2021_v2/data_in_brief_v2_original.xlsx"
        ),
    )
    constraint = ma2021_source_use_constraint(
        subject_source_version_id=SOURCE_VERSION_ID,
        terms_source_version_id=TERMS_VERSION_ID,
        terms_retrieval_date=date(2026, 8, 11),
        reviewer_pseudonym="source-rights-reviewer",
    )
    request = ma2021_source_use_request(
        source_version_id=SOURCE_VERSION_ID,
        as_of_date=date(2026, 8, 11),
    )

    assert source.artifact_sha256 == MA2021_ARTIFACT_SHA256
    assert source.rights["reuse_status"] == "PERMITTED"
    assert source.rights["spdx_identifier"] == "etalab-2.0"
    assert constraint.intended_action == request.intended_action == "INTERNAL_ANALYSIS"
    assert constraint.artifact_locator == request.artifact_locator
    assert constraint.constraints["attribution_required"] is True
    assert request.requested_records == 53_280
    assert request.requested_bytes == MA2021_ARTIFACT_SIZE


def test_exact_quarantined_v2_replays_when_available() -> None:
    project_root = Path(__file__).resolve().parents[3]
    workbook = (
        project_root
        / "archive"
        / "source_quarantine"
        / "ma_2021_v2"
        / "data_in_brief_v2_original.xlsx"
    )
    if not workbook.exists():
        pytest.skip("exact official V2 quarantine bytes are not present")

    dataset = parse_ma2021_workbook(workbook)
    assert workbook.stat().st_size == MA2021_ARTIFACT_SIZE
    assert hashlib.sha256(workbook.read_bytes()).hexdigest() == MA2021_ARTIFACT_SHA256
    assert (
        len(dataset.odorants),
        len(dataset.aggregate_trials),
        len(dataset.participant_trials),
        len(dataset.participants),
        len(dataset.mixture_keys),
    ) == (72, 222, 6_660, 60, 198)
    assert len(dataset.trial_metadata_conflicts) == 4
    assert len(dataset.odorant_name_conflicts) == 1
    above_nominal = [
        Decimal(value)
        for row in dataset.participant_trials
        for endpoint, value in row.values.items()
        if endpoint in {"IAmix", "IBmix"} and Decimal(value) > 10
    ]
    assert len(above_nominal) == 327
    assert max(above_nominal) == Decimal("11")

    extraction_specs = tuple(iter_ma2021_extraction_specs(dataset))
    assert len(extraction_specs) == len({row.output_record_id for row in extraction_specs})
    assert len(extraction_specs) == 8_598
    command = build_ma2021_external_study_input(
        dataset,
        source_version_id=SOURCE_VERSION_ID,
        extraction_ids=ma2021_dry_run_extraction_ids(dataset),
        as_of_date=date(2026, 8, 11),
    )
    LabExternalStudyServiceMixin._validate_external_graph(command)
    counts = ma2021_native_counts(command)
    assert (counts["stimuli"], counts["components"], counts["crosswalks"]) == (
        270,
        468,
        468,
    )
    aggregate_n = Counter(
        row.reported_n
        for row in command.experimental_units
        if row.unit_grain == "AGGREGATE"
    )
    assert aggregate_n == {29: 129, 30: 93}
    first_aggregate = next(
        row
        for row in command.observations
        if row.observation_key == "ma2021-source-aggregate-trial-001-vector"
    )
    assert first_aggregate.value["IA"] == "4.9586206896551728"
    assert first_aggregate.limitations == (
        "SOURCE_SHEET_EXCLUDES_SUBJECT_47",
        "SOURCE_REPORTED_AGGREGATE_NOT_RECOMPUTED",
    )
    assert counts["total_records"] == 8_598
