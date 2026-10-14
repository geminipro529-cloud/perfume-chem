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


@pytest.mark.asyncio
async def test_startup_reads_the_material_list_in_the_background(monkeypatch):
    import asyncio
    import threading

    import engine.data_spine.loader as loader

    from app.services import personal_liking

    read = threading.Event()
    threads = []

    def record_read(*_args, **_kwargs):
        threads.append(threading.current_thread().name)
        read.set()

    async def no_refit():
        return None

    monkeypatch.setattr(db_bootstrap, "upgrade_database", lambda _config: None)
    monkeypatch.setattr(personal_liking, "refit_at_startup", no_refit)
    monkeypatch.setattr(loader, "load_registry", record_read)

    async with lifespan(app):
        assert await asyncio.to_thread(read.wait, 10)

    # Off the request thread, so start-up and the first page load don't wait for it.
    assert threads == ["material-registry-warmup"]
