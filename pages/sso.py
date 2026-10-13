"""SSO-мост сайт → приложение «Доски» (boardapp).

Сайт подписывает короткоживущий HS256-JWT общим секретом BOARDS_SSO_SECRET;
/boardapp/sso/ в приложении проверяет подпись, находит/создаёт пользователя
по external_id и возвращает страницу, кладущую токен приложения в localStorage.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import time

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _sso_token(secret: str, sub: str, username: str, ttl: int = 120) -> str:
    header = _b64url(json.dumps({'alg': 'HS256', 'typ': 'JWT'},
                                separators=(',', ':')).encode())
    payload = _b64url(json.dumps(
        {'sub': sub, 'username': username, 'iat': int(time.time()),
         'exp': int(time.time()) + ttl},
        separators=(',', ':')).encode())
    signature = _b64url(
        hmac.new(secret.encode(), f'{header}.{payload}'.encode(),
                 hashlib.sha256).digest())
    return f'{header}.{payload}.{signature}'


def _sanitize(username: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', username).strip('_.-')
    return cleaned if 3 <= len(cleaned) <= 32 else ''


@login_required
def boards_sso(request):
    secret = os.environ.get('BOARDS_SSO_SECRET', '')
    if not secret:
        return HttpResponseBadRequest('SSO не настроен: задайте BOARDS_SSO_SECRET')
    user = request.user
    token = _sso_token(secret, str(user.pk),
                       _sanitize(user.get_username()) or f'u{user.pk}')
    return HttpResponseRedirect(
        f'/boards/api/auth/sso?token={token}&next=/boards/')
