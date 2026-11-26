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
    owner = await user('owner')
    viewer = await user('viewer2')
    r = await client.post('/api/boards', json={'title': 'Z'},
                          headers=auth(owner['token']))
    bid = r.json()['id']
    await client.post(f'/api/boards/{bid}/members',
                      json={'username': 'viewer2', 'role': 'viewer'},
                      headers=auth(owner['token']))
    original = ws_module.SessionLocal
    ws_module.SessionLocal = session_maker
    yield {'owner': owner, 'viewer': viewer, 'board_id': bid}
    ws_module.SessionLocal = original


def _recv_until(sock, wanted, limit=50):
    for _ in range(limit):
        m = sock.receive_json()
        if m['type'] == wanted:
            return m
    raise RuntimeError(f'{wanted} not received')


def test_zone_crud_and_init(ws_setup):
    owner, bid = ws_setup['owner'], ws_setup['board_id']
    with TestClient(app) as tc:
        with ws_connect(tc, owner["token"], bid) as ws:
            init = ws.receive_json()
            assert init['type'] == 'init'
            assert init['data']['zones'] == []

            zid = str(uuid.uuid4())
            ws.send_json({'type': 'zone:create', 'data': {
                'id': zid, 'title': 'Спринт 1', 'x': 10, 'y': 20,
                'width': 420, 'height': 280}})
            m = _recv_until(ws, 'zone:created')
            assert m['data']['title'] == 'Спринт 1'

            ws.send_json({'type': 'zone:update', 'data': {
                'id': zid, 'patch': {'title': 'Бэклог', 'width': 600}}})
            m = _recv_until(ws, 'zone:updated')
            assert m['data']['patch']['title'] == 'Бэклог'

        # новый снимок init содержит зону
        with ws_connect(tc, owner["token"], bid) as ws2:
            init2 = ws2.receive_json()
            zones = init2['data']['zones']
            assert len(zones) == 1
            assert zones[0]['title'] == 'Бэклог'
            assert zones[0]['width'] == 600

        with ws_connect(tc, owner["token"], bid) as ws:
            ws.receive_json()
            ws.send_json({'type': 'zone:delete', 'data': {'id': zid}})
            _recv_until(ws, 'zone:deleted')


def test_viewer_cannot_create_zone(ws_setup):
    viewer, bid = ws_setup['viewer'], ws_setup['board_id']
    with TestClient(app) as tc:
        with ws_connect(tc, viewer["token"], bid) as ws:
            ws.receive_json()
            ws.send_json({'type': 'zone:create', 'data': {
                'id': str(uuid.uuid4()), 'x': 0, 'y': 0}})
            m = ws.receive_json()
            while m['type'] != 'error':
                m = ws.receive_json()
            assert 'прав' in m['data']['message']


def test_ticket_text_autogrows_height(ws_setup):
    owner, bid = ws_setup['owner'], ws_setup['board_id']
    with TestClient(app) as tc:
        with ws_connect(tc, owner["token"], bid) as ws:
            ws.receive_json()
            tid = str(uuid.uuid4())
            ws.send_json({'type': 'ticket:create', 'data': {
                'id': tid, 'x': 0, 'y': 0, 'text': 'коротко'}})
            m = _recv_until(ws, 'ticket:created')
            short_height = m['data']['height']

            long_text = 'очень длинный текст ' * 12  # ~220 символов
            ws.send_json({'type': 'ticket:update', 'data': {
                'id': tid, 'patch': {'text': long_text}}})
            m = _recv_until(ws, 'ticket:updated')
            # текст обрезается лимитом тикета (100), высота растёт под него
            assert m['data']['patch']['height'] > short_height
            assert m['data']['patch']['height'] >= 300  # ~8 строк по 32px под крупный шрифт


def test_zone_membership_and_arrow_label_survive_reconnect(ws_setup):
    owner, bid = ws_setup['owner'], ws_setup['board_id']
    headers = auth(owner['token'])
    zone, foreign_zone, first, second, edge = (str(uuid.uuid4()) for _ in range(5))
    with TestClient(app) as tc:
        other = tc.post('/api/boards', json={'title': 'Other board'}, headers=headers).json()['id']
        with ws_connect(tc, owner["token"], other) as other_ws:
            _recv_until(other_ws, 'init')
            other_ws.send_json({'type': 'zone:create', 'data': {'id': foreign_zone}})
            _recv_until(other_ws, 'zone:created')
        with ws_connect(tc, owner['token'], bid) as ws:
            _recv_until(ws, 'init')
            ws.send_json({'type': 'board:batch', 'data': {'changes': [
                {'type': 'zone:create', 'data': {'id': zone, 'title': 'В работе'}},
                {'type': 'ticket:create', 'data': {'id': first, 'zoneId': zone}},
                {'type': 'ticket:create', 'data': {'id': second}},
                {'type': 'edge:create', 'data': {'id': edge, 'source': first, 'target': second}},
            ]}})
            _recv_until(ws, 'board:batch')
            ws.send_json({'type': 'ticket:update', 'data': {'id': second, 'patch': {'zoneId': foreign_zone}}})
            assert 'на этой доске' in _recv_until(ws, 'error')['data']['message']
            ws.send_json({'type': 'edge:update', 'data': {'id': edge, 'label': ' блокирует '}})
            assert _recv_until(ws, 'edge:updated')['data']['label'] == 'блокирует'

        with ws_connect(tc, owner['token'], bid) as ws:
            init = _recv_until(ws, 'init')['data']
            assert {t['id']: t['zoneId'] for t in init['tickets']} == {first: zone, second: None}
            assert init['edges'][0]['label'] == 'блокирует'
            ws.send_json({'type': 'zone:delete', 'data': {'id': zone}})
            _recv_until(ws, 'zone:deleted')

        snapshot = tc.get(f'/api/boards/{bid}', headers=headers).json()
        assert snapshot['zones'] == []
        assert {t['id']: t['zoneId'] for t in snapshot['tickets']} == {first: None, second: None}
        assert snapshot['edges'][0]['label'] == 'блокирует'
