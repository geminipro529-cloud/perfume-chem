"""Startup migration behavior tests."""

import pytest

import app.db_bootstrap as db_bootstrap
from app.main import app, lifespan


@pytest.mark.asyncio
async def test_startup_migration_failure_stops_application(monkeypatch):
    def fail_upgrade(_config):
        raise RuntimeError("migration failed")

    monkeypatch.setattr(db_bootstrap, "upgrade_database", fail_upgrade)

    with pytest.raises(RuntimeError, match="migration failed"):
        async with lifespan(app):
            pass
