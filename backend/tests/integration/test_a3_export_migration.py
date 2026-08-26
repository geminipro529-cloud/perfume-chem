import json
from pathlib import Path

import pytest

from app.services.lab_export import (
    CURRENT_WRITE_REVISION,
    LabExportService,
    migrate_export_packet,
)


@pytest.mark.asyncio
async def test_every_supported_export_migrates_explicitly_to_current_v4(
    db_session,
):
    exporter = LabExportService(db_session)
    packets = (
        await exporter.export_workspace(format_revision="lab-export-v1"),
        await exporter.export_workspace(format_revision="lab-export-v2"),
        await exporter.export_workspace(format_revision="lab-export-v3"),
        await exporter.export_workspace(format_revision="lab-export-v4"),
    )
    for packet in packets:
        packet["extensions"] = {
            "org.perfumechem.test": {"source": packet["format_revision"]}
        }
        migrated = migrate_export_packet(packet)
        assert migrated["format_revision"] == CURRENT_WRITE_REVISION
        assert migrated["extensions"] == packet["extensions"]
        assert "lab_target_hypothesis_versions" in migrated["tables"]
        assert "lab_analytical_runs" in migrated["tables"]
        assert "lab_bottle_action_proposals" in migrated["tables"]
        assert "lab_bottle_action_commits" in migrated["tables"]


def test_export_migration_rejects_future_version_and_unscoped_fields():
    with pytest.raises(ValueError, match="unknown future laboratory export"):
        migrate_export_packet(
            {
                "format_revision": "lab-export-v99",
                "tables": {},
            }
        )


def test_supported_export_golden_fixtures_migrate_without_extension_loss():
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "fixtures"
        / "lab_export_supported_versions.json"
    )
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert set(fixtures) == {
        "lab-export-v1",
        "lab-export-v2",
        "lab-export-v3",
        "lab-export-v4",
    }
    for revision, packet in fixtures.items():
        assert packet["format_revision"] == revision
        migrated = migrate_export_packet(packet)
        assert migrated["format_revision"] == CURRENT_WRITE_REVISION
        assert migrated["extensions"] == packet["extensions"]
    with pytest.raises(ValueError, match="top-level export field"):
        migrate_export_packet(
            {
                "format_revision": "lab-export-v1",
                "tables": {},
                "surprise": True,
            }
        )
