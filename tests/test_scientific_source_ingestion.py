"""Focused tests for manifest-gated scientific source staging."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

from engine.calibration.hashing import stable_json_hash
from engine.ingestion.scientific import (
    SCIENTIFIC_SOURCE_SCHEMA_VERSION,
    UnsafeIngestionPathError,
    stage_scientific_source,
)
from scripts.integrate_external_data import main as importer_main

_COMMIT = "fb47cb343cdfd5cd8b06b33161dfa8b82c0319c6"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_LINEAGE_RESPONSE_FIELD_MAP = {
    "INTENSITY/STRENGTH": "HOW STRONG IS THE SMELL?",
    "VALENCE/PLEASANTNESS": "HOW PLEASANT IS THE SMELL?",
    "BAKERY": "BAKERY",
    "SWEET": "SWEET",
    "FRUIT": "FRUIT",
    "FISH": "FISH",
    "GARLIC": "GARLIC",
    "SPICES": "SPICES",
    "COLD": "COLD",
    "SOUR": "SOUR",
    "BURNT": "BURNT",
    "ACID": "ACID",
    "WARM": "WARM",
    "MUSKY": "MUSKY",
    "SWEATY": "SWEATY",
    "AMMONIA/URINOUS": "AMMONIA/URINOUS",
    "DECAYED": "DECAYED",
    "WOOD": "WOOD",
    "GRASS": "GRASS",
    "FLOWER": "FLOWER",
    "CHEMICAL": "CHEMICAL",
}
_LINEAGE_KEY_FIELD_MAP = {
    "Compound Identifier": "CID",
    "Odor": "Odor",
    "Dilution": "Odor dilution",
    "subject #": "Subject # (DREAM challenge)",
}
_LINEAGE_TARGET_HEADERS = (
    "Compound Identifier",
    "Odor",
    "Replicate",
    "Intensity",
    "Dilution",
    "subject #",
    *_LINEAGE_RESPONSE_FIELD_MAP,
)


def _xlsx_column(index: int) -> str:
    value = index
    result = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xlsx_cell(reference: str, value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}"><v>{value}</v></c>'
    escaped = xml_escape(str(value))
    return (
        f'<c r="{reference}" t="inlineStr"><is><t>{escaped}</t></is></c>'
    )


def _minimal_lineage_xlsx(
    rows: list[dict[str, object | None]],
    *,
    unsafe_member: bool = False,
) -> bytes:
    headers = (
        "CID",
        "Odor",
        "Odor dilution",
        "Subject # (DREAM challenge)",
        "CAN OR CAN'T SMELL",
        *dict.fromkeys(_LINEAGE_RESPONSE_FIELD_MAP.values()),
    )
    xml_rows = [
        '<row r="1"><c r="A1" t="inlineStr"><is><t>fixture</t></is></c></row>',
        '<row r="2"><c r="A2" t="inlineStr"><is><t>context</t></is></c></row>',
    ]
    header_cells = "".join(
        _xlsx_cell(f"{_xlsx_column(index)}3", header)
        for index, header in enumerate(headers, start=1)
    )
    xml_rows.append(f'<row r="3">{header_cells}</row>')
    for row_number, row in enumerate(rows, start=4):
        cells = "".join(
            _xlsx_cell(f"{_xlsx_column(index)}{row_number}", row[header])
            for index, header in enumerate(headers, start=1)
            if row.get(header) is not None
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData>'
        + "".join(xml_rows)
        + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships"><sheets><sheet name="data" sheetId="1" '
        'r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships"><Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types"><Default Extension="xml" '
        'ContentType="application/xml"/></Types>'
    )
    payloads = {
        "[Content_Types].xml": content_types,
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": relationships,
        "xl/worksheets/sheet1.xml": worksheet,
    }
    if unsafe_member:
        payloads["../outside.xml"] = "unsafe"
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name, payload in payloads.items():
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, payload.encode())
    return output.getvalue()


def _lineage_parent_rows() -> list[dict[str, object | None]]:
    blank_descriptors = {
        source: None
        for target, source in _LINEAGE_RESPONSE_FIELD_MAP.items()
        if target not in {"INTENSITY/STRENGTH", "VALENCE/PLEASANTNESS"}
    }

    def row(
        subject: int,
        dilution: str,
        detection: str,
        strength: int | None,
        pleasantness: int | None,
        **descriptors: int,
    ) -> dict[str, object | None]:
        return {
            "CID": 637566,
            "Odor": "geraniol",
            "Odor dilution": dilution,
            "Subject # (DREAM challenge)": subject,
            "CAN OR CAN'T SMELL": detection,
            "HOW STRONG IS THE SMELL?": strength,
            "HOW PLEASANT IS THE SMELL?": pleasantness,
            **blank_descriptors,
            **descriptors,
        }

    return [
        row(1, "1/100,000", "I can't smell anything", None, None),
        row(
            1,
            "1/1,000",
            "I smell something",
            50,
            60,
            SWEET=1,
            FRUIT=2,
            FLOWER=1,
        ),
        row(2, "1/100,000", "I smell something", 20, 30),
        row(2, "1/1,000", "I smell something", 40, 50, CHEMICAL=70),
    ]


def _stage_lineage_parent(
    tmp_path: Path,
    *,
    unsafe_member: bool = False,
    extra_rows: tuple[dict[str, object | None], ...] = (),
):
    source_root = tmp_path / "lineage-parent-raw"
    source_root.mkdir(parents=True)
    xlsx = _minimal_lineage_xlsx(
        [*_lineage_parent_rows(), *extra_rows],
        unsafe_member=unsafe_member,
    )
    (source_root / "study.xlsx").write_bytes(xlsx)
    digest = _sha(xlsx)
    manifest = {
        "schema_version": SCIENTIFIC_SOURCE_SCHEMA_VERSION,
        "source_id": f"keller-fixture-{digest[:12]}",
        "source_type": "PRIMARY_RESEARCH_DATASET",
        "title": "Keller workbook fixture",
        "language": "en",
        "review_state": "UNREVIEWED",
        "independence_group": "keller-fixture",
        "authors": ["Andreas Keller", "Leslie B. Vosshall"],
        "issuing_organization": "fixture",
        "identifiers": {"doi": "10.1186/s12868-016-0287-2"},
        "revision": {"kind": "content_digest", "value": digest},
        "retrieved_at": "2026-08-09T12:00:00+07:00",
        "rights": {
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "redistribution_allowed": True,
        },
        "transformation": {
            "module": "engine.ingestion.scientific",
            "version": "scientific-source-staging-v1",
            "mode": "source-bytes-only",
        },
        "dataset_context": {
            "measurement_kind": "raw psychophysical ratings",
            "authority_limit": "fixture only",
        },
        "artifacts": [
            {
                "artifact_id": "study-data-xlsx",
                "path": "study.xlsx",
                "role": "PRIMARY_DATA",
                "media_type": (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                "byte_size": len(xlsx),
                "sha256": digest,
                "source_url": "https://example.org/study.xlsx",
                "preserved_artifact_path": "data/external/fixture/study.xlsx",
            }
        ],
    }
    return stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "lineage-parent-out",
    )


def _lineage_target_rows() -> list[dict[str, object | None]]:
    descriptors = tuple(
        field
        for field in _LINEAGE_RESPONSE_FIELD_MAP
        if field not in {"INTENSITY/STRENGTH", "VALENCE/PLEASANTNESS"}
    )

    def row(
        subject: int,
        intensity_label: str,
        dilution: str,
        strength: int,
        pleasantness: int | None,
        *,
        blank_descriptors: bool = False,
        **values: int,
    ) -> dict[str, object | None]:
        descriptor_values: dict[str, object | None] = {
            field: None if blank_descriptors else 0 for field in descriptors
        }
        descriptor_values.update(values)
        return {
            "Compound Identifier": 637566,
            "Odor": "geraniol",
            "Replicate": None,
            "Intensity": intensity_label,
            "Dilution": dilution,
            "subject #": subject,
            "INTENSITY/STRENGTH": strength,
            "VALENCE/PLEASANTNESS": pleasantness,
            **descriptor_values,
        }

    return [
        row(1, "low", "1/100,000", 0, None, blank_descriptors=True),
        row(
            1,
            "high",
            "1/1,000",
            50,
            60,
            SWEET=10,
            FRUIT=20,
            FLOWER=100,
        ),
        row(2, "low", "1/100,000", 20, 30),
        row(2, "high", "1/1,000", 40, 50, CHEMICAL=70),
    ]


def _with_value_lineage_validation(
    manifest: dict,
    source_root: Path,
    parent,
    *,
    target_override: tuple[int, str, str, object | None] | None = None,
) -> None:
    _with_dream_observation_tranche(manifest, source_root)
    rows = _lineage_target_rows()
    if target_override is not None:
        subject, dilution, field, value = target_override
        target = next(
            row
            for row in rows
            if row["subject #"] == subject and row["Dilution"] == dilution
        )
        target[field] = value
    text_rows = ["\t".join(_LINEAGE_TARGET_HEADERS)]
    text_rows.extend(
        "\t".join("" if row.get(field) is None else str(row[field]) for field in _LINEAGE_TARGET_HEADERS)
        for row in rows
    )
    data = ("\n".join(text_rows) + "\n").encode()
    (source_root / "data.tsv").write_bytes(data)
    train_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["artifact_id"] == "train-set"
    )
    train_artifact["byte_size"] = len(data)
    train_artifact["sha256"] = _sha(data)
    for condition in manifest["observation_tranche"]["conditions"]:
        condition["expected_replicate_count"] = 2
    parent_candidate = parent.reports["b1_source_candidates.json"][0]
    parent_source_id = parent_candidate["source_id"]
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "support_scope": "PSYCHOPHYSICS_DATASET_CONTEXT",
            "supported_claim_path": (
                "observation_tranche.value_lineage_validation"
            ),
            "rationale": "Exact workbook compatibility fixture.",
        }
    ]
    manifest["observation_tranche"]["value_lineage_validation"] = {
        "adapter": "keller_vosshall_xlsx_to_dream_v1",
        "parent_source_id": parent_source_id,
        "parent_manifest_sha256": parent.manifest_hash,
        "parent_bundle_sha256": parent.bundle_hash,
        "parent_artifact_id": "study-data-xlsx",
        "parent_artifact_sha256": parent_candidate["artifact_sha256"],
        "worksheet_name": "data",
        "header_row": 3,
        "key_field_map": _LINEAGE_KEY_FIELD_MAP,
        "response_field_map": _LINEAGE_RESPONSE_FIELD_MAP,
        "source_detection_field": "CAN OR CAN'T SMELL",
        "cannot_smell_value": "I can't smell anything",
        "expected_counts": {
            "matched_rows": 4,
            "compared_cells": 84,
            "exact_numeric": 7,
            "source_blank_to_target_zero": 54,
            "source_blank_to_target_blank": 20,
            "deterministic_trailing_zero_restoration": 1,
            "published_derivative_one_to_ten": 1,
            "published_derivative_one_to_hundred": 1,
            "incompatible": 0,
        },
        "lineage_state": (
            "PARTIALLY_DETERMINISTIC_PUBLISHED_DERIVATIVE_"
            "DISAMBIGUATION_REQUIRED"
        ),
        "authority_limit": (
            "Compatibility only; source-level derivation and canonical authority "
            "remain withheld."
        ),
    }


def _fixture(tmp_path: Path) -> tuple[dict, Path]:
    source_root = tmp_path / "raw"
    source_root.mkdir(parents=True)
    data = b"cid\tdilution\trating\n1\t-3\t42\n"
    license_bytes = b"fixture license\n"
    (source_root / "data.tsv").write_bytes(data)
    (source_root / "LICENSE").write_bytes(license_bytes)
    manifest = {
        "schema_version": SCIENTIFIC_SOURCE_SCHEMA_VERSION,
        "source_id": "dream-fixture-fb47cb",
        "source_type": "AUTHORITATIVE_DATABASE_RECORD",
        "title": "DREAM fixture",
        "language": "en",
        "review_state": "UNREVIEWED",
        "independence_group": "dream-keller-2017",
        "issuing_organization": "DREAM Olfaction Consortium",
        "identifiers": {
            "doi": "10.1126/science.aal2014",
            "repository": "https://github.com/dream-olfaction/olfaction-prediction",
        },
        "revision": {"kind": "git_commit", "value": _COMMIT},
        "retrieved_at": "2026-08-09T12:00:00+07:00",
        "rights": {
            "reuse_status": "PERMITTED",
            "license_or_reuse_restriction": "MIT",
            "license_url": (
                "https://raw.githubusercontent.com/dream-olfaction/"
                f"olfaction-prediction/{_COMMIT}/LICENSE"
            ),
            "redistribution_allowed": True,
        },
        "transformation": {
            "module": "engine.ingestion.scientific",
            "version": "scientific-source-staging-v1",
            "mode": "source-bytes-only",
        },
        "dataset_context": {
            "measurement_kind": "human psychophysical rating",
            "authority_limit": "benchmark only",
        },
        "artifacts": [
            {
                "artifact_id": "license",
                "path": "LICENSE",
                "role": "LICENSE",
                "media_type": "text/plain",
                "byte_size": len(license_bytes),
                "sha256": _sha(license_bytes),
                "source_url": (
                    "https://raw.githubusercontent.com/dream-olfaction/"
                    f"olfaction-prediction/{_COMMIT}/LICENSE"
                ),
                "preserved_artifact_path": "data/external/fixture/LICENSE",
            },
            {
                "artifact_id": "train-set",
                "path": "data.tsv",
                "role": "PRIMARY_DATA",
                "media_type": "text/tab-separated-values",
                "byte_size": len(data),
                "sha256": _sha(data),
                "source_url": (
                    "https://raw.githubusercontent.com/dream-olfaction/"
                    f"olfaction-prediction/{_COMMIT}/data/TrainSet.txt"
                ),
                "preserved_artifact_path": "data/external/fixture/data.tsv",
            },
        ],
    }
    return manifest, source_root


def _with_dream_observation_tranche(
    manifest: dict,
    source_root: Path,
) -> dict:
    header = (
        "Compound Identifier\tOdor\tReplicate\tIntensity\tDilution\t"
        "subject #\tINTENSITY/STRENGTH"
    )
    rows = [
        "637566\tgeraniol \t\thigh \t1/1,000 \t1\t20",
        "637566\tgeraniol \t\tlow \t1/100,000 \t1\t10",
        "637566\tgeraniol \t\thigh \t1/1,000 \t2\t40",
        "637566\tgeraniol \t\tlow \t1/100,000 \t2\t30",
        "637566\tgeraniol \t\thigh \t1/1,000 \t3\t60",
        "637566\tgeraniol \t\tlow \t1/100,000 \t3\t50",
        "6549\tlinalool \t\thigh \t1/1,000 \t1\t70",
    ]
    data = ("\n".join((header, *rows)) + "\n").encode()
    (source_root / "data.tsv").write_bytes(data)
    train_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["artifact_id"] == "train-set"
    )
    train_artifact["byte_size"] = len(data)
    train_artifact["sha256"] = _sha(data)
    manifest["transformation"]["mode"] = "source-and-observation-candidates"
    manifest["observation_tranche"] = {
        "adapter": "dream_psychophysics_intensity_v1",
        "artifact_id": "train-set",
        "source_compound_identifier": "637566",
        "source_odor_label": "geraniol",
        "identity_scope": "CHEMICAL_ENTITY",
        "subject_identity": {
            "chemical_name": "Geraniol",
            "cas": "106-24-1",
            "pubchem_cid": "637566",
            "comptox_dtxsid": "DTXSID8026727",
            "inchi_key": "GLZPCOQZEFWAFX-JXMROGBWSA-N",
        },
        "identity_evidence": {
            "pubchem_url": "https://pubchem.ncbi.nlm.nih.gov/compound/637566",
            "comptox_url": (
                "https://comptox.epa.gov/chemexpo/chemical/DTXSID8026727/"
            ),
            "verification_state": "IDENTIFIER_CROSSWALK_ONLY",
        },
        "property_type": "HUMAN_ODOR_INTENSITY_RATING",
        "value_kind": "DISTRIBUTION",
        "original_unit": "rating_0_100",
        "canonical_unit": "rating_0_100",
        "method_context": {
            "matrix": "paraffin oil",
            "phase": "liquid stimulus in vial; orthonasal headspace sniff",
            "stimulus_volume_ml": 1.0,
            "method": "self-administered computerized vial-sniff psychophysics",
            "endpoint": "perceived odor intensity/strength",
            "rating_scale": {
                "minimum": 0,
                "maximum": 100,
                "interface": "computerized slider",
            },
            "methods_source": {
                "doi": "10.1186/s12868-016-0287-2",
                "pmcid": "PMC4977894",
                "locator": [
                    "Methods > General psychophysics procedures",
                    "Methods > Stimuli",
                ],
                "lineage_state": "CITATION_METADATA_ONLY_METHOD_BYTES_NOT_PINNED",
            },
        },
        "conditions": [
            {
                "source_intensity_label": "high",
                "source_dilution": "1/1,000",
                "nominal_volume_fraction": 0.001,
                "expected_replicate_count": 3,
            },
            {
                "source_intensity_label": "low",
                "source_dilution": "1/100,000",
                "nominal_volume_fraction": 0.00001,
                "expected_replicate_count": 3,
            },
        ],
        "authority_limit": (
            "Psychophysical ratings only; not ODT, OAV, airborne concentration, "
            "safety, similarity, or formula-release evidence."
        ),
    }
    return manifest


def _codes(result) -> set[str]:
    return {item.code for item in result.rejections}


def test_valid_source_is_verified_staging_only(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is True
    assert result.status == "VERIFIED_STAGED"
    assert len(result.manifest_hash) == 64
    assert len(result.bundle_hash) == 64
    receipt = result.reports["ingestion_receipt.json"]
    assert receipt["authority_changed"] is False
    assert receipt["canonical_rows_written"] == 0
    assert receipt["promotion_allowed"] is False
    assert receipt["review_required"] is True
    candidates = result.reports["b1_source_candidates.json"]
    assert len(candidates) == 1
    assert candidates[0]["artifact_sha256"] == manifest["artifacts"][1]["sha256"]
    assert candidates[0]["review_state"] == "UNREVIEWED"
    assert candidates[0]["rights"] == {
        "reuse_status": "PERMITTED",
        "license_or_reuse_restriction": "MIT",
        "license_url": manifest["rights"]["license_url"],
        "redistribution_allowed": True,
        "spdx_identifier": None,
        "notes": None,
    }
    assert (
        candidates[0]["license_or_reuse_restriction"]
        == candidates[0]["rights"]["license_or_reuse_restriction"]
    )
    tampered = {
        key: value
        for key, value in candidates[0].items()
        if key != "candidate_sha256"
    }
    tampered["rights"] = {
        **tampered["rights"],
        "redistribution_allowed": False,
    }
    assert stable_json_hash(tampered) != candidates[0]["candidate_sha256"]
    assert "b1_extraction_candidates.json" not in result.reports
    assert "b2_observation_candidates.json" not in result.reports


def test_governed_source_rights_census_preserves_source_specific_scopes() -> None:
    manifest_root = Path(__file__).resolve().parents[1] / "data" / "source_manifests"
    manifests = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(manifest_root.glob("*.json"))
    }

    historical_names = {
        "dream_olfaction_fb47cb343cdf.json",
        "keller_vosshall_2016_fulltext_7e7f309706f5.json",
        "keller_vosshall_2016_study_data_efcb1b075584.json",
        "pubchem_geraniol_cas_629488ac5296.json",
        "pubchem_geraniol_properties_d21151198ff5.json",
    }
    assert historical_names <= set(manifests)
    assert set(manifests) - historical_names == {
        "optimizer_sensory_research_20260909.json",
        "perfumersworld_inventory_documents_20260830.json",
    }
    rights = [manifests[name]["rights"] for name in historical_names]
    assert sum(item["reuse_status"] == "PERMITTED" for item in rights) == 3
    assert sum(item["reuse_status"] == "RESTRICTED" for item in rights) == 2
    assert all(isinstance(item["redistribution_allowed"], bool) for item in rights)
    assert all(item["license_url"] for item in rights)
    assert all(item["notes"] for item in rights)
    assert sum(bool(item.get("spdx_identifier")) for item in rights) == 3

    article = manifests[
        "keller_vosshall_2016_fulltext_7e7f309706f5.json"
    ]["rights"]
    study_data = manifests[
        "keller_vosshall_2016_study_data_efcb1b075584.json"
    ]["rights"]
    assert article["spdx_identifier"] == "CC-BY-4.0"
    assert study_data["spdx_identifier"] == "CC0-1.0"
    assert article["license_url"] != study_data["license_url"]

    pubchem = [
        manifest["rights"]
        for name, manifest in manifests.items()
        if name.startswith("pubchem_")
    ]
    assert all(item["reuse_status"] == "RESTRICTED" for item in pubchem)
    assert all(item["redistribution_allowed"] is False for item in pubchem)


def test_source_relation_candidate_binds_separately_staged_sources(
    tmp_path: Path,
) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "method-paper-fixture"
    parent_manifest["source_type"] = "PRIMARY_PEER_REVIEWED_PAPER"
    parent_manifest["title"] = "Method paper fixture"
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_candidate = parent.reports["b1_source_candidates.json"][0]

    child_manifest, child_root = _fixture(tmp_path / "child")
    child_manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_candidate["source_id"],
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "Documents the psychophysics method.",
        }
    ]
    result = stage_scientific_source(
        child_manifest,
        source_root=child_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted is True
    child_candidate = result.reports["b1_source_candidates.json"][0]
    relation = result.reports["b1_source_derivation_candidates.json"][0]
    assert len(parent_candidate["candidate_sha256"]) == 64
    assert len(child_candidate["candidate_sha256"]) == 64
    assert relation["candidate_schema_version"] == (
        "b1_source_derivation_candidate_v1"
    )
    assert relation["child_source_id"] == child_candidate["source_id"]
    assert relation["child_source_candidate_sha256"] == (
        child_candidate["candidate_sha256"]
    )
    assert relation["parent_source_id"] == parent_candidate["source_id"]
    assert relation["parent_source_candidate_sha256"] == (
        parent_candidate["candidate_sha256"]
    )
    assert relation["parent_bundle_sha256"] == parent.bundle_hash
    assert relation["relation"] == "CITES"
    assert relation["support_scope"] == "EXPERIMENTAL_METHOD"
    assert relation["supported_claim_path"] == (
        "observation_tranche.method_context"
    )
    assert relation["review_state"] == "UNREVIEWED"
    assert relation["workflow_state"] == "STAGED"
    assert relation["authority_state"] == "CANDIDATE_ONLY"
    unhashed = dict(relation)
    assert unhashed.pop("record_sha256") == stable_json_hash(unhashed)
    receipt = result.reports["ingestion_receipt.json"]
    assert receipt["source_relation_candidate_count"] == 1
    report_hashes = result.reports["deterministic_hash.json"][
        "candidate_report_sha256s"
    ]
    assert "b1_source_derivation_candidates.json" in report_hashes
    assert receipt["authority_changed"] is False
    assert receipt["canonical_rows_written"] == 0
    assert receipt["promotion_allowed"] is False


def test_source_relation_requires_a_verified_related_source(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": "missing-source:train-set",
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "Missing parent must fail closed.",
        }
    ]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_PARENT_NOT_STAGED" in _codes(result)
    assert "b1_source_derivation_candidates.json" not in result.reports


def test_source_relation_rejects_unproven_derivation_semantics(
    tmp_path: Path,
) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "identity-fixture"
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]
    manifest, source_root = _fixture(tmp_path / "child")
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "DERIVED_FROM",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "A citation must not claim transformation.",
        }
    ]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_SEMANTICS_UNSUPPORTED" in _codes(result)


def test_source_relation_replay_is_deterministic_and_rationale_bound(
    tmp_path: Path,
) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "method-fixture"
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]
    manifest, source_root = _fixture(tmp_path / "child")
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "Method context.",
        }
    ]

    first = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "first",
        related_sources=(parent,),
    )
    second = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "second",
        related_sources=(parent,),
    )
    changed_manifest = json.loads(json.dumps(manifest))
    changed_manifest["source_relations"][0]["rationale"] = "Identity context."
    changed = stage_scientific_source(
        changed_manifest,
        source_root=source_root,
        output_dir=tmp_path / "changed",
        related_sources=(parent,),
    )

    assert first.accepted and second.accepted and changed.accepted
    assert first.bundle_hash == second.bundle_hash
    assert first.reports["b1_source_derivation_candidates.json"] == (
        second.reports["b1_source_derivation_candidates.json"]
    )
    assert changed.bundle_hash != first.bundle_hash
    assert changed.reports["b1_source_derivation_candidates.json"] != (
        first.reports["b1_source_derivation_candidates.json"]
    )


def test_source_relation_requires_explicit_claim_scope(tmp_path: Path) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "scoped-parent-fixture"
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]
    manifest, source_root = _fixture(tmp_path / "child")
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "rationale": "An unscoped citation must fail closed.",
        }
    ]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_SCOPE_REQUIRED" in _codes(result)
    assert "b1_source_derivation_candidates.json" not in result.reports


def test_source_relation_rejects_self_link(tmp_path: Path) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]
    manifest, source_root = _fixture(tmp_path / "child")
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "A source cannot cite itself.",
        }
    ]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_SELF_LINK" in _codes(result)


def test_source_relation_rejects_exact_duplicate(tmp_path: Path) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "duplicate-parent-fixture"
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]
    manifest, source_root = _fixture(tmp_path / "child")
    relation = {
        "child_artifact_id": "train-set",
        "parent_source_id": parent_source_id,
        "relation": "CITES",
        "support_scope": "EXPERIMENTAL_METHOD",
        "supported_claim_path": "observation_tranche.method_context",
        "rationale": "Duplicate fixture.",
    }
    manifest["source_relations"] = [relation, dict(relation)]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_DUPLICATE" in _codes(result)


def test_source_relation_rejects_cycle_from_related_graph(tmp_path: Path) -> None:
    base_manifest, base_root = _fixture(tmp_path / "base")
    base_manifest["source_id"] = "cycle-base-fixture"
    base = stage_scientific_source(
        base_manifest,
        source_root=base_root,
        output_dir=tmp_path / "base-out",
    )
    base_source_id = base.reports["b1_source_candidates.json"][0][
        "source_id"
    ]

    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "cycle-parent-fixture"
    parent_manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": base_source_id,
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "First edge in cycle fixture.",
        }
    ]
    parent = stage_scientific_source(
        parent_manifest,
        source_root=parent_root,
        output_dir=tmp_path / "parent-out",
        related_sources=(base,),
    )
    parent_source_id = parent.reports["b1_source_candidates.json"][0][
        "source_id"
    ]

    child_manifest, child_root = _fixture(tmp_path / "child")
    child_manifest["source_id"] = "cycle-base-fixture"
    child_manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "Closing edge must fail.",
        }
    ]
    result = stage_scientific_source(
        child_manifest,
        source_root=child_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "SOURCE_RELATION_CYCLE" in _codes(result)


def test_dream_tranche_emits_linked_b1_b2_candidates_and_selection_hold(
    tmp_path: Path,
) -> None:
    manifest, source_root = _fixture(tmp_path)
    _with_dream_observation_tranche(manifest, source_root)

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is True
    extractions = result.reports["b1_extraction_candidates.json"]
    observations = result.reports["b2_observation_candidates.json"]
    review = result.reports["b2_conflict_selection_review.json"]
    assert len(extractions) == 2
    assert len(observations) == 2
    assert [item["condition"]["source_dilution"] for item in observations] == [
        "1/1,000",
        "1/100,000",
    ]
    assert [item["distribution"]["summary"]["mean"] for item in observations] == [
        40.0,
        30.0,
    ]
    assert [item["distribution"]["summary"]["sample_standard_deviation"] for item in observations] == [
        20.0,
        20.0,
    ]
    assert all(item["replicate_count"] == 3 for item in observations)
    assert all(item["matrix"] == "paraffin oil" for item in observations)
    assert all(item["value_kind"] == "DISTRIBUTION" for item in observations)
    assert all(
        item["evidence_class"] == "LITERATURE_DERIVED" for item in observations
    )
    assert all(item["review_state"] == "STAGED" for item in observations)
    assert all(item["authority_state"] == "CANDIDATE_ONLY" for item in observations)
    assert all(len(item["subject_identity_sha256"]) == 64 for item in observations)
    assert all(len(item["content_sha256"]) == 64 for item in observations)
    assert all(
        observation["extraction_record_candidate_id"]
        == extraction["extraction_candidate_id"]
        for observation, extraction in zip(observations, extractions, strict=True)
    )
    assert extractions[0]["locator"]["row_numbers"] == [2, 4, 6]
    assert extractions[1]["locator"]["row_numbers"] == [3, 5, 7]
    assert all(len(item["input_sha256"]) == 64 for item in extractions)
    assert all(len(item["output_sha256"]) == 64 for item in extractions)
    assert all(len(item["record_sha256"]) == 64 for item in extractions)
    assert review["conflict_set_candidate"] is None
    assert review["pairwise_assessments"][0]["state"] == (
        "NOT_A_CONFLICT_DIFFERENT_CONDITIONS"
    )
    assertion = review["selected_assertion_candidate"]
    assert assertion["selection_kind"] == "NONE"
    assert assertion["authority_state"] == "WITHHELD_UNKNOWN"
    assert assertion["selected_observation_candidate_id"] is None
    receipt = result.reports["ingestion_receipt.json"]
    assert receipt["extraction_candidate_count"] == 2
    assert receipt["observation_candidate_count"] == 2
    assert receipt["authority_changed"] is False
    assert receipt["canonical_rows_written"] == 0
    assert receipt["promotion_allowed"] is False


def test_dream_tranche_rejects_incomplete_method_context(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    _with_dream_observation_tranche(manifest, source_root)
    del manifest["observation_tranche"]["method_context"]["matrix"]

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert "OBSERVATION_CONTEXT_INCOMPLETE" in _codes(result)
    assert "b1_extraction_candidates.json" not in result.reports
    assert "b2_observation_candidates.json" not in result.reports


def test_dream_tranche_rejects_source_identity_mismatch(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    _with_dream_observation_tranche(manifest, source_root)
    manifest["observation_tranche"]["source_odor_label"] = "not-geraniol"

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert "OBSERVATION_IDENTITY_MISMATCH" in _codes(result)
    assert "b2_observation_candidates.json" not in result.reports


def test_dream_tranche_reports_are_byte_identical_on_replay(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    _with_dream_observation_tranche(manifest, source_root)

    first = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-a",
    )
    second = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-b",
    )
    first_files = first.write()
    second_files = second.write()

    assert first.accepted and second.accepted
    assert first.bundle_hash == second.bundle_hash
    for name in (
        "b1_extraction_candidates.json",
        "b2_observation_candidates.json",
        "b2_conflict_selection_review.json",
    ):
        assert Path(first_files[name]).read_bytes() == Path(second_files[name]).read_bytes()


def test_dream_value_lineage_binds_parent_and_classifies_transforms(
    tmp_path: Path,
) -> None:
    parent = _stage_lineage_parent(tmp_path)
    assert parent.accepted
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted
    candidates = result.reports["b1_value_lineage_validation_candidates.json"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["matched_row_count"] == 4
    assert candidate["compared_cell_count"] == 84
    assert candidate["classification_counts"] == {
        "deterministic_trailing_zero_restoration": 1,
        "exact_numeric": 7,
        "incompatible": 0,
        "published_derivative_one_to_hundred": 1,
        "published_derivative_one_to_ten": 1,
        "source_blank_to_target_blank": 20,
        "source_blank_to_target_zero": 54,
    }
    assert candidate["exact_reconstruction_without_published_derivative"] is False
    assert candidate["authority_state"] == "WITHHELD_UNKNOWN"
    assert candidate["canonical_rows_written"] == 0
    assert candidate["promotion_allowed"] is False
    assert len(candidate["published_derivative_disambiguations"]) == 2
    unhashed = dict(candidate)
    assert unhashed.pop("record_sha256") == stable_json_hash(unhashed)
    binding = {
        "validation_id": candidate["validation_id"],
        "record_sha256": candidate["record_sha256"],
    }
    assert all(
        item["structure_context"]["value_lineage_validation"] == binding
        for item in result.reports["b1_extraction_candidates.json"]
    )
    assert all(
        item["provenance_activity"]["value_lineage_validation"] == binding
        for item in result.reports["b2_observation_candidates.json"]
    )
    assert result.reports["ingestion_receipt.json"][
        "value_lineage_validation_candidate_count"
    ] == 1


def test_dream_value_lineage_requires_verified_related_parent(tmp_path: Path) -> None:
    parent = _stage_lineage_parent(tmp_path)
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
    )

    assert result.accepted is False
    assert "VALUE_LINEAGE_PARENT_UNVERIFIED" in _codes(result)
    assert "b1_value_lineage_validation_candidates.json" not in result.reports


def test_dream_value_lineage_rejects_parent_hash_drift(tmp_path: Path) -> None:
    parent = _stage_lineage_parent(tmp_path)
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)
    manifest["observation_tranche"]["value_lineage_validation"][
        "parent_artifact_sha256"
    ] = "0" * 64

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "VALUE_LINEAGE_PARENT_INTEGRITY_MISMATCH" in _codes(result)


def test_dream_value_lineage_rejects_incompatible_cell(tmp_path: Path) -> None:
    parent = _stage_lineage_parent(tmp_path)
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(
        manifest,
        source_root,
        parent,
        target_override=(1, "1/1,000", "FRUIT", 21),
    )

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "VALUE_LINEAGE_CELL_MISMATCH" in _codes(result)


def test_dream_value_lineage_rejects_unsafe_ooxml_member(tmp_path: Path) -> None:
    parent = _stage_lineage_parent(tmp_path, unsafe_member=True)
    assert parent.accepted
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted is False
    assert "VALUE_LINEAGE_WORKBOOK_INVALID" in _codes(result)


def test_dream_value_lineage_report_is_byte_identical_on_replay(
    tmp_path: Path,
) -> None:
    parent = _stage_lineage_parent(tmp_path)
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)
    first = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-a",
        related_sources=(parent,),
    )
    second = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-b",
        related_sources=(parent,),
    )
    first_files = first.write()
    second_files = second.write()

    assert first.accepted and second.accepted
    name = "b1_value_lineage_validation_candidates.json"
    assert Path(first_files[name]).read_bytes() == Path(second_files[name]).read_bytes()
    assert first.bundle_hash == second.bundle_hash


def test_dream_full_corpus_lineage_accepts_parent_superset_and_bounds_details(
    tmp_path: Path,
) -> None:
    extra_parent = dict(_lineage_parent_rows()[0])
    extra_parent.update(
        {
            "CID": 999999,
            "Odor": "parent-only odor",
            "Subject # (DREAM challenge)": 99,
        }
    )
    parent = _stage_lineage_parent(tmp_path, extra_rows=(extra_parent,))
    manifest, source_root = _fixture(tmp_path / "child")
    _with_value_lineage_validation(manifest, source_root, parent)
    contract = manifest["observation_tranche"]["value_lineage_validation"]
    contract["validation_scope"] = "FULL_CORPUS"
    contract["detail_limit"] = 1
    contract["expected_counts"].update(
        {
            "parent_keyed_rows": 5,
            "parent_rows_outside_child_corpus": 1,
        }
    )

    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "child-out",
        related_sources=(parent,),
    )

    assert result.accepted
    candidate = result.reports["b1_value_lineage_validation_candidates.json"][0]
    assert candidate["scope"]["validation_scope"] == "FULL_CORPUS"
    assert candidate["parent_keyed_row_count"] == 5
    assert candidate["parent_rows_outside_child_corpus"] == 1
    assert candidate["detail_limit"] == 1
    assert len(candidate["deterministic_recodings"]) == 1
    assert len(candidate["published_derivative_disambiguations"]) == 1
    assert candidate["published_derivative_details_truncated"] is True
    assert candidate["canonical_rows_written"] == 0
    assert candidate["promotion_allowed"] is False


def test_replay_writes_byte_identical_reports(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    first = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-a",
    )
    second = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out-b",
    )
    first_files = first.write()
    second_files = second.write()

    assert first.accepted and second.accepted
    assert first.bundle_hash == second.bundle_hash
    assert set(first_files) == set(second_files)
    for name in first_files:
        assert Path(first_files[name]).read_bytes() == Path(second_files[name]).read_bytes()


def test_non_identical_report_is_never_overwritten(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )
    written = result.write()
    Path(written["ingestion_receipt.json"]).write_text("changed", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        result.write()


def test_preexisting_conflict_leaves_no_partial_bundle(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "ingestion_receipt.json").write_text("foreign", encoding="utf-8")
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=output_dir,
    )

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        result.write()
    assert sorted(path.name for path in output_dir.iterdir()) == ["ingestion_receipt.json"]


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest["artifacts"][1]["sha256"] = "0" * 64
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert result.status == "REJECTED"
    assert "ARTIFACT_HASH_MISMATCH" in _codes(result)
    assert "b1_source_candidates.json" not in result.reports


def test_mutable_url_fails_even_with_declared_commit(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest["artifacts"][1]["source_url"] = (
        "https://raw.githubusercontent.com/dream-olfaction/"
        "olfaction-prediction/main/data/TrainSet.txt"
    )
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert "MUTABLE_SOURCE_URL" in _codes(result)


def test_git_revision_must_be_present_in_every_artifact_url(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest["artifacts"][1]["source_url"] = "https://example.org/fixed-data.tsv"
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert "REVISION_URL_MISMATCH" in _codes(result)


def test_unknown_rights_and_path_traversal_fail_closed(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest["rights"]["reuse_status"] = "UNKNOWN"
    manifest["artifacts"][1]["path"] = "../outside.tsv"
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=tmp_path / "out",
    )

    assert result.accepted is False
    assert {"RIGHTS_UNRESOLVED", "ARTIFACT_PATH_ESCAPE"} <= _codes(result)


def test_protected_output_is_refused_before_directory_creation(tmp_path: Path) -> None:
    manifest, source_root = _fixture(tmp_path)
    protected = Path(__file__).resolve().parents[1] / "data" / "materials" / "_ingest_test"
    result = stage_scientific_source(
        manifest,
        source_root=source_root,
        output_dir=protected,
    )

    with pytest.raises(UnsafeIngestionPathError, match="protected"):
        result.write()
    assert not protected.exists()


def test_cli_stages_verified_related_source_before_relation_candidate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parent_manifest, parent_root = _fixture(tmp_path / "parent")
    parent_manifest["source_id"] = "cli-method-source"
    parent_manifest_path = tmp_path / "parent-manifest.json"
    parent_manifest_path.write_text(json.dumps(parent_manifest), encoding="utf-8")
    parent_source_id = f"{parent_manifest['source_id']}:train-set"

    manifest, source_root = _fixture(tmp_path / "child")
    manifest["source_relations"] = [
        {
            "child_artifact_id": "train-set",
            "parent_source_id": parent_source_id,
            "relation": "CITES",
            "support_scope": "EXPERIMENTAL_METHOD",
            "supported_claim_path": "observation_tranche.method_context",
            "rationale": "CLI relation fixture.",
        }
    ]
    manifest_path = tmp_path / "child-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output_dir = tmp_path / "cli-output"

    code = importer_main(
        [
            "--manifest",
            str(manifest_path),
            "--source-root",
            str(source_root),
            "--related-source",
            str(parent_manifest_path),
            str(parent_root),
            "--output-dir",
            str(output_dir),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted"] is True
    relation_path = output_dir / "b1_source_derivation_candidates.json"
    relations = json.loads(relation_path.read_text(encoding="utf-8"))
    assert len(relations) == 1
    assert relations[0]["parent_source_id"] == parent_source_id
    assert relations[0]["relation"] == "CITES"


def test_cli_dry_run_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest, source_root = _fixture(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output_dir = tmp_path / "dry-run-output"

    code = importer_main(
        [
            "--manifest",
            str(manifest_path),
            "--source-root",
            str(source_root),
            "--output-dir",
            str(output_dir),
            "--dry-run",
            "--json",
        ]
    )

    assert code == 0
    assert not output_dir.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted"] is True
    assert payload["written"] == {}


def test_cli_rejection_is_structured_and_writes_nothing(tmp_path, capsys):
    manifest, source_root = _fixture(tmp_path)
    manifest["artifacts"][0]["sha256"] = "0" * 64
    manifest_path = tmp_path / "rejected-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output_dir = tmp_path / "rejected-output"
    code = importer_main([
        "--manifest", str(manifest_path), "--source-root", str(source_root),
        "--output-dir", str(output_dir), "--json",
    ])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted"] is False
    assert payload["rejections"]
    assert all(set(item) == {"code", "detail", "field"} for item in payload["rejections"])
    assert payload["written"] == {}
    assert not output_dir.exists()
    assert all(payload[field] is False for field in (
        "release_authority", "safety_authority", "compounding_authority",
        "evidence_admission_authorized",
    ))
