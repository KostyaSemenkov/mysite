import base64
import hashlib
import hmac
import json
import time

import pytest

from .conftest import auth

pytestmark = pytest.mark.asyncio


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def make_sso_token(secret: str, sub: str, username: str, ttl: int = 120) -> str:
    """То же подписание, что делает вьюха сайта Django."""
    header = _b64url(json.dumps({'alg': 'HS256', 'typ': 'JWT'},
                                separators=(',', ':')).encode())
    payload = _b64url(json.dumps({'sub': sub, 'username': username,
                                  'iat': int(time.time()),
                                  'exp': int(time.time()) + ttl},
                                 separators=(',', ':')).encode())
    sig = _b64url(hmac.new(secret.encode(), f'{header}.{payload}'.encode(),
                           hashlib.sha256).digest())
    return f'{header}.{payload}.{sig}'


@pytest.fixture
def sso_secret(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'sso_secret', 'test-sso-secret')
    return 'test-sso-secret'


async def test_sso_creates_user_and_returns_shim(client, sso_secret):
    token = make_sso_token(sso_secret, 'django-user-42', 'kotik')
    r = await client.get(f'/api/auth/sso?token={token}&next=/boards/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert 'boardapp_token' in r.text
    assert '/boards/' in r.text

    # пользователь создан и валиден для обычного API
    import re
    m = re.search(r"localStorage\.setItem\('boardapp_token', \"(.*?)\"\)", r.text)
    app_token = m.group(1)
    me = await client.get('/api/auth/me', headers=auth(app_token))
    assert me.status_code == 200
    assert me.json()['username'] == 'kotik'


async def test_sso_second_login_updates_username(client, sso_secret):
    t1 = make_sso_token(sso_secret, 'django-user-42', 'kotik')
    await client.get(f'/api/auth/sso?token={t1}')
    t2 = make_sso_token(sso_secret, 'django-user-42', 'zhorik')
    r = await client.get(f'/api/auth/sso?token={t2}')
    assert r.status_code == 200
    import re
    m = re.search(r"localStorage\.setItem\('boardapp_token', \"(.*?)\"\)", r.text)
    me = await client.get('/api/auth/me', headers=auth(m.group(1)))
    assert me.json()['username'] == 'zhorik'


async def test_sso_sanitizes_bad_username(client, sso_secret):
    token = make_sso_token(sso_secret, 'django-7', 'Лемур!')  # кириллица и символы
    r = await client.get(f'/api/auth/sso?token={token}')
    import re
    m = re.search(r"localStorage\.setItem\('boardapp_token', \"(.*?)\"\)", r.text)
    me = await client.get('/api/auth/me', headers=auth(m.group(1)))
    assert me.json()['username'] == 'udjango-7'


async def test_sso_rejects_bad_signature(client, sso_secret):
    token = make_sso_token('wrong-secret', 'x' * 8, 'someone')
    r = await client.get(f'/api/auth/sso?token={token}')
    assert r.status_code == 401

    r = await client.get('/api/auth/sso')
    assert r.status_code == 401
