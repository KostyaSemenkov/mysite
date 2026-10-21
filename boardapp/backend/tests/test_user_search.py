import pytest

from .conftest import auth

pytestmark = pytest.mark.asyncio


async def test_user_search_by_prefix(client, user):
    anna = await user('anna_qa')
    await user('anton_dev')
    await user('kirill')

    r = await client.get('/api/users/search', params={'q': 'an'},
                         headers=auth(anna['token']))
    assert r.status_code == 200
    names = [u['username'] for u in r.json()['items']]
    assert names == ['anna_qa', 'anton_dev']  # по префиксу, без kirill

    r = await client.get('/api/users/search', params={'q': 'kir'}, headers=auth(anna['token']))
    assert [u['username'] for u in r.json()['items']] == ['kirill']


async def test_user_search_requires_auth_and_min_length(client, user):
    u = await user('someone')
    r = await client.get('/api/users/search', params={'q': 'an'})
    assert r.status_code == 401
    r = await client.get('/api/users/search', params={'q': 'a'}, headers=auth(u['token']))
    assert r.status_code == 422
