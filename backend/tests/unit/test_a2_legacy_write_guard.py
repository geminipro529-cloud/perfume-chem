from pathlib import Path

import pytest

from app.verification.legacy_write_guard import (
    assert_no_legacy_write_paths,
    scan_legacy_write_paths,
)


def test_live_backend_has_no_legacy_dual_write_path():
    app_root = Path(__file__).resolve().parents[2] / "app"
    assert scan_legacy_write_paths(app_root) == ()


def test_guard_rejects_legacy_ledger_import_outside_adapter(tmp_path):
    app_root = tmp_path / "app"
    app_root.mkdir()
    (app_root / "bad.py").write_text(
        "from engine.inventory.stock_model import InventoryLedger\n",
        encoding="utf-8",
    )

    violations = scan_legacy_write_paths(app_root)

    assert [(item.code, item.detail) for item in violations] == [
        ("LEGACY_LEDGER_IMPORT", "engine.inventory.stock_model.InventoryLedger")
    ]
    with pytest.raises(RuntimeError, match="LEGACY_LEDGER_IMPORT"):
        assert_no_legacy_write_paths(app_root)


def test_guard_rejects_adapter_mutation_and_transaction_authority(tmp_path):
    app_root = tmp_path / "app"
    adapters = app_root / "adapters"
    adapters.mkdir(parents=True)
    (adapters / "bad.py").write_text(
        "\n".join(
            [
                "from sqlalchemy.ext.asyncio import AsyncSession",
                "def bad(ledger):",
                "    ledger.consume('stock', 1.0)",
                "    ledger.commit()",
            ]
        ),
        encoding="utf-8",
    )

    violations = scan_legacy_write_paths(app_root)

    assert {item.code for item in violations} == {
        "ADAPTER_LEGACY_MUTATION",
        "ADAPTER_TRANSACTION_AUTHORITY",
        "ADAPTER_TRANSACTION_CALL",
    }


def test_guard_rejects_endpoint_owned_transaction_calls(tmp_path):
    app_root = tmp_path / "app"
    endpoints = app_root / "api" / "v1" / "endpoints"
    endpoints.mkdir(parents=True)
    (endpoints / "bad.py").write_text(
        "\n".join(
            [
                "async def bad(session, record):",
                "    session.add(record)",
                "    await session.flush()",
                "    await session.commit()",
                "    await session.refresh(record)",
                "    await session.rollback()",
            ]
        ),
        encoding="utf-8",
    )

    violations = scan_legacy_write_paths(app_root)

    assert [item.code for item in violations] == [
        "ENDPOINT_TRANSACTION_CALL",
        "ENDPOINT_TRANSACTION_CALL",
        "ENDPOINT_TRANSACTION_CALL",
        "ENDPOINT_TRANSACTION_CALL",
        "ENDPOINT_TRANSACTION_CALL",
    ]
    assert [item.detail for item in violations] == [
        "session.add",
        "session.flush",
        "session.commit",
        "session.refresh",
        "session.rollback",
    ]
