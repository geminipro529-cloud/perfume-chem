import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import db_session


@pytest.mark.asyncio
async def test_get_session_is_an_async_context_manager(monkeypatch, test_engine):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "async_session_maker", factory)

    async with db_session.get_session() as session:
        assert session.bind is test_engine
