import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='session')
async def engine():
    # SQLite in-memory: Postgres-специфики нет
    eng = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_maker(engine):
    # каждая тестовая функция получает чистую копию схемы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(session_maker):
    async def override():
        async with session_maker() as s:
            yield s

    app.dependency_overrides[get_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(client):
    async def make(username: str, password: str = 'secret123'):
        r = await client.post('/api/auth/register',
                              json={'username': username, 'password': password})
        return r.json()

    return make


def auth(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}
