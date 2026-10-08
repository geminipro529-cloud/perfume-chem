from pathlib import Path

import pytest

from tests import conftest as backend_fixtures


@pytest.mark.asyncio
async def test_closing_one_test_database_cannot_drop_another_tests_tables(tmp_path):
    first_path, second_path = tmp_path / "first", tmp_path / "second"
    first_path.mkdir()
    second_path.mkdir()
    factory = backend_fixtures.test_engine.__wrapped__
    first, second = factory(first_path), factory(second_path)
    first_engine = await anext(first)
    second_engine = await anext(second)

    async def finish_fixture(generator):
        # Drive the post-yield teardown as pytest does. aclose alone would skip
        # the fixture's normal schema cleanup and pool disposal.
        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    try:
        assert first_engine.url.database != second_engine.url.database
        assert Path(first_engine.url.database).resolve().parent == first_path.resolve()
        assert Path(second_engine.url.database).resolve().parent == second_path.resolve()
        await finish_fixture(first)
        async with second_engine.connect() as connection:
            table = await connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='lab_engine_jobs'"
            )
            assert table.scalar_one() == "lab_engine_jobs"
    finally:
        await finish_fixture(first)
        await finish_fixture(second)
