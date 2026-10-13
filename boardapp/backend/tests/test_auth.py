import pytest

from .conftest import auth

pytestmark = pytest.mark.asyncio


async def test_register_login_me(client, user):
    data = await user('alice')
    assert data['token']
    assert data['user']['username'] == 'alice'

    r = await client.get('/api/auth/me', headers=auth(data['token']))
    assert r.status_code == 200
    assert r.json()['username'] == 'alice'


async def test_register_duplicate_username(client, user):
    await user('bob')
    r = await client.post('/api/auth/register',
                          json={'username': 'bob', 'password': 'secret123'})
    assert r.status_code == 409


async def test_register_validation(client):
    r = await client.post('/api/auth/register',
                          json={'username': 'ab', 'password': 'secret123'})
    assert r.status_code == 422
    r = await client.post('/api/auth/register',
                          json={'username': 'validname', 'password': '12345'})
    assert r.status_code == 422


async def test_login_wrong_password(client, user):
    await user('carol')
    r = await client.post('/api/auth/login',
                          json={'username': 'carol', 'password': 'WRONG'})
    assert r.status_code == 401


async def test_invalid_token(client):
    r = await client.get('/api/auth/me', headers=auth('not-a-jwt'))
    assert r.status_code == 401
    r = await client.get('/api/auth/me')
    assert r.status_code == 401
