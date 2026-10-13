import pytest

from .conftest import auth

pytestmark = pytest.mark.asyncio


async def _board(client, token, title='Доска'):
    r = await client.post('/api/boards', json={'title': title},
                          headers=auth(token))
    assert r.status_code == 201
    return r.json()['id']


async def test_create_list_boards(client, user):
    u = await user('alice')
    bid = await _board(client, u['token'], 'Первая')
    await _board(client, u['token'], 'Вторая')

    r = await client.get('/api/boards', headers=auth(u['token']))
    data = r.json()
    assert len(data['own']) == 2
    assert data['shared'] == []

    r = await client.get(f'/api/boards/{bid}', headers=auth(u['token']))
    assert r.status_code == 200
    assert r.json()['board']['role'] == 'owner'
    assert r.json()['tickets'] == []


async def test_foreign_board_404(client, user):
    alice = await user('alice')
    mallory = await user('mallory')
    bid = await _board(client, alice['token'])

    r = await client.get(f'/api/boards/{bid}', headers=auth(mallory['token']))
    assert r.status_code == 404
    r = await client.delete(f'/api/boards/{bid}', headers=auth(mallory['token']))
    assert r.status_code == 404


async def test_editor_cannot_delete_or_rename(client, user):
    owner = await user('owner')
    editor = await user('editor')
    bid = await _board(client, owner['token'])

    r = await client.post(f'/api/boards/{bid}/members',
                          json={'username': 'editor', 'role': 'editor'},
                          headers=auth(owner['token']))
    assert r.status_code == 201

    r = await client.delete(f'/api/boards/{bid}', headers=auth(editor['token']))
    assert r.status_code == 403
    r = await client.patch(f'/api/boards/{bid}', json={'title': 'X'},
                           headers=auth(editor['token']))
    assert r.status_code == 403
    # но снапшот доступен
    r = await client.get(f'/api/boards/{bid}', headers=auth(editor['token']))
    assert r.status_code == 200
    assert r.json()['board']['role'] == 'editor'


async def test_members_flow(client, user):
    owner = await user('owner')
    other = await user('guest')
    bid = await _board(client, owner['token'])

    # приглашение несуществующего
    r = await client.post(f'/api/boards/{bid}/members',
                          json={'username': 'ghost', 'role': 'viewer'},
                          headers=auth(owner['token']))
    assert r.status_code == 404

    r = await client.post(f'/api/boards/{bid}/members',
                          json={'username': 'guest', 'role': 'viewer'},
                          headers=auth(owner['token']))
    assert r.status_code == 201

    # guest видит доску в shared
    r = await client.get('/api/boards', headers=auth(other['token']))
    shared = r.json()['shared']
    assert len(shared) == 1 and shared[0]['role'] == 'viewer'

    # удалить участника
    uid = other['user']['id']
    r = await client.delete(f'/api/boards/{bid}/members/{uid}',
                            headers=auth(owner['token']))
    assert r.status_code == 204
    r = await client.get('/api/boards', headers=auth(other['token']))
    assert r.json()['shared'] == []
