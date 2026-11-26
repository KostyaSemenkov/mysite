import uuid

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from app.main import app
from app.routers import ws as ws_module

from .conftest import auth, ws_connect

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ws_setup(client, session_maker, user):
    """Готовит доску с owner+editor+viewer и подменяет SessionLocal в ws-роутере."""
    owner = await user('owner')
    editor = await user('editor')
    viewer = await user('viewer')

    r = await client.post('/api/boards', json={'title': 'WS доска'},
                          headers=auth(owner['token']))
    bid = r.json()['id']
    for name in ('editor', 'viewer'):
        await client.post(f'/api/boards/{bid}/members',
                          json={'username': name, 'role': name},
                          headers=auth(owner['token']))

    original = ws_module.SessionLocal
    ws_module.SessionLocal = session_maker
    yield {'owner': owner, 'editor': editor, 'viewer': viewer, 'board_id': bid}
    ws_module.SessionLocal = original


async def drain(sock, timeout=0.4):
    import asyncio as aio
    msgs = []
    try:
        while True:
            msgs.append(sock.receive_json())
            if len(msgs) > 50:
                break
    except Exception:
        pass
    return msgs


def test_two_users_realtime(ws_setup):
    owner, editor = ws_setup['owner'], ws_setup['editor']
    bid = ws_setup['board_id']

    with TestClient(app) as tc:
        with ws_connect(tc, owner['token'], bid) as ws1, \
                ws_connect(tc, editor['token'], bid) as ws2:

            init1 = ws1.receive_json()
            assert init1['type'] == 'init'
            assert init1['data']['role'] == 'owner'

            init2 = ws2.receive_json()
            assert init2['type'] == 'init'

            # editor создаёт тикет
            tid = str(uuid.uuid4())
            ws2.send_json({'type': 'ticket:create', 'data': {
                'id': tid, 'x': 10, 'y': 20, 'text': 'привет', 'color': '#CAFFBF'}})

            # оба получают broadcast; actor = editor
            def wait_created(sock):
                while True:
                    m = sock.receive_json()
                    if m['type'] == 'ticket:created':
                        return m

            m1 = wait_created(ws1)
            m2 = wait_created(ws2)
            assert m1['actor'] == editor['user']['id']
            assert m2['data']['id'] == tid
            assert m1['data']['text'] == 'привет'

            # update доходит
            ws2.send_json({'type': 'ticket:update',
                           'data': {'id': tid, 'patch': {'x': 99}}})
            while True:
                m = ws1.receive_json()
                if m['type'] == 'ticket:updated':
                    assert m['data']['patch'] == {'x': 99}
                    break


def test_viewer_cannot_mutate(ws_setup):
    viewer, bid = ws_setup['viewer'], ws_setup['board_id']

    with TestClient(app) as tc:
        with ws_connect(tc, viewer['token'], bid) as ws:
            init = ws.receive_json()
            assert init['data']['role'] == 'viewer'

            ws.send_json({'type': 'ticket:create', 'data': {
                'id': str(uuid.uuid4()), 'x': 0, 'y': 0}})
            while True:
                m = ws.receive_json()
                if m['type'] == 'error':
                    break
            assert 'message' in m['data']


def test_token_in_url_is_not_accepted(ws_setup):
    """Токен в адресе сокета больше не работает — даже действующий: сокет закрывается с 4401."""
    from starlette.websockets import WebSocketDisconnect
    owner, bid = ws_setup['owner'], ws_setup['board_id']
    with TestClient(app) as tc:
        with tc.websocket_connect(f'/ws/boards/{bid}?token={owner["token"]}') as ws:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4401


def test_no_auth_message_closes_socket(ws_setup, monkeypatch):
    """Клиент, который не прислал auth, отключается по таймауту."""
    from starlette.websockets import WebSocketDisconnect
    monkeypatch.setattr(ws_module, 'AUTH_TIMEOUT_SECONDS', 0.2)
    bid = ws_setup['board_id']
    with TestClient(app) as tc:
        with tc.websocket_connect(f'/ws/boards/{bid}') as ws:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4401


def test_batch_is_atomic_and_can_be_retried_after_reconnect(ws_setup):
    owner, bid = ws_setup['owner'], ws_setup['board_id']
    client_id = str(uuid.uuid4())
    first, second, edge = (str(uuid.uuid4()) for _ in range(3))
    duplicate = {
        'type': 'board:batch',
        'operation': {'clientId': client_id, 'sequence': 1},
        'data': {'changes': [
            {'type': 'ticket:create', 'data': {'id': first, 'x': 10}},
            {'type': 'ticket:create', 'data': {'id': second}},
            {'type': 'edge:create', 'data': {'id': edge, 'source': first, 'target': second}},
        ]},
    }

    def receive(sock, kind):
        for _ in range(5):
            message = sock.receive_json()
            if message['type'] == kind:
                return message
        pytest.fail(f'{kind} was not received')

    with TestClient(app) as tc:
        with ws_connect(tc, owner['token'], bid, client_id) as ws:
            receive(ws, 'init')
            ws.send_json(duplicate)
            result = receive(ws, 'board:batch')
            assert result['operation'] == duplicate['operation']
            assert len(result['data']['events']) == 3

        with ws_connect(tc, owner['token'], bid, client_id) as ws:
            init = receive(ws, 'init')['data']
            assert init['lastSequence'] == 1
            assert {t['id'] for t in init['tickets']} == {first, second}
            assert [e['id'] for e in init['edges']] == [edge]
            ws.send_json(duplicate)
            assert receive(ws, 'op:ack')['operation'] == duplicate['operation']

            operation = {'clientId': client_id, 'sequence': 2}
            ws.send_json({
                'type': 'board:batch', 'operation': operation,
                'data': {'changes': [
                    {'type': 'ticket:update', 'data': {'id': first, 'patch': {'x': 500}}},
                    {'type': 'zone:delete', 'data': {'id': str(uuid.uuid4())}},
                ]},
            })
            assert receive(ws, 'error')['operation'] == operation

        with ws_connect(tc, owner['token'], bid, client_id) as ws:
            init = receive(ws, 'init')['data']
            assert init['lastSequence'] == 1
            assert next(t for t in init['tickets'] if t['id'] == first)['x'] == 10


def test_ws_token_in_first_message(ws_setup):
    """Новый клиент присылает токен первым сообщением: адрес сокета без токена."""
    owner = ws_setup['owner']
    bid = ws_setup['board_id']
    with TestClient(app) as tc:
        with tc.websocket_connect(f'/ws/boards/{bid}') as ws:
            ws.send_json({'type': 'auth', 'token': owner['token'],
                          'clientId': str(uuid.uuid4())})
            init = ws.receive_json()
            assert init['type'] == 'init'
            assert init['data']['role'] == 'owner'


def test_ws_rejects_wrong_first_message(ws_setup):
    from starlette.websockets import WebSocketDisconnect
    bid = ws_setup['board_id']
    with TestClient(app) as tc:
        with tc.websocket_connect(f'/ws/boards/{bid}') as ws:
            ws.send_json({'type': 'ticket:create', 'data': {}})
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4400


def test_ws_rejects_bad_token_in_auth_message(ws_setup):
    from starlette.websockets import WebSocketDisconnect
    bid = ws_setup['board_id']
    with TestClient(app) as tc:
        with tc.websocket_connect(f'/ws/boards/{bid}') as ws:
            ws.send_json({'type': 'auth', 'token': 'not-a-jwt', 'clientId': ''})
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4401


def test_ws_origin_check():
    allowed = ws_module._origin_allowed
    assert allowed({'host': 'lemurqa.ru', 'origin': 'https://lemurqa.ru'})
    # алиас сайта: Origin совпадает с Host
    assert allowed({'host': 'www.lemurqa.ru', 'origin': 'https://www.lemurqa.ru'})
    # dev-сервер Vite — из списка CORS
    assert allowed({'host': 'api.local', 'origin': 'http://localhost:5173'})
    # клиент без Origin (не браузер): всё равно потребуется токен
    assert allowed({'host': 'lemurqa.ru'})
    assert not allowed({'host': 'lemurqa.ru', 'origin': 'https://evil.example'})
    # чужой Origin не спасает и поддомен того же имени
    assert not allowed({'host': 'evil.example', 'origin': 'https://app.evil.example'})


def _receive(sock, kind):
    """Читает сообщения до нужного типа (перед ошибкой приходят presence:join и пр.)."""
    for _ in range(20):
        message = sock.receive_json()
        if message.get('type') == kind:
            return message
    pytest.fail(f'{kind} was not received')


def test_ws_batch_is_capped(ws_setup):
    owner = ws_setup['owner']
    bid = ws_setup['board_id']
    with TestClient(app) as tc:
        with ws_connect(tc, owner['token'], bid) as ws:
            _receive(ws, 'init')
            changes = [{'type': 'ticket:create', 'data': {
                'id': str(uuid.uuid4()), 'x': 1, 'y': 2, 'text': '', 'color': '#CAFFBF'}}
                for _ in range(ws_module.MAX_BATCH_CHANGES + 1)]
            ws.send_json({'type': 'board:batch', 'data': {'changes': changes}})
            result = _receive(ws, 'error')
            assert 'не больше' in result['data']['message']
