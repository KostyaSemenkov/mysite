import logging
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders

from .config import settings
from .routers import auth, boards, ws

app = FastAPI(title='board-app')

app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(boards.router)
app.include_router(ws.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Заголовки безопасности ──
# SPA не содержит inline-скриптов, поэтому CSP здесь строже, чем на сайте:
# только свои источники. До проверки на реальных пользователях политика идёт
# в режиме Report-Only (отчёты принимает сайт на /csp-report/); включить
# принудительный режим — переменная CSP_ENFORCE=1.
SECURITY_HEADERS = (
    ('X-Content-Type-Options', 'nosniff'),
    ('X-Frame-Options', 'DENY'),
    ('Referrer-Policy', 'strict-origin-when-cross-origin'),
    ('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'),
    # same-origin разорвал бы связь с вкладками, которые открывает встроенный контент
    ('Cross-Origin-Opener-Policy', 'same-origin-allow-popups'),
    ('Cross-Origin-Resource-Policy', 'cross-origin'),
)
CSP_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
    "report-uri /csp-report/"
)


class SecurityHeadersMiddleware:
    """Добавляет заголовки безопасности ко всем HTTP-ответам: SPA, API, SSO-страница."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS:
                    headers[name] = value
                csp_header = ('Content-Security-Policy' if settings.csp_enforce
                              else 'Content-Security-Policy-Report-Only')
                headers[csp_header] = CSP_POLICY
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)


class RedactTokenFilter(logging.Filter):
    """Токен в query-строке запроса не должен попадать в лог.

    Токен в адресе больше не принимается, но старая вкладка всё равно
    присылает его в адресе сокета — в логе он заменяется на token=***.
    """

    _pattern = re.compile(r'token=[^&\s"]+')

    def filter(self, record):
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._pattern.sub('token=***', arg) if isinstance(arg, str) else arg
                for arg in record.args)
        elif record.args is None and isinstance(record.msg, str):
            record.msg = self._pattern.sub('token=***', record.msg)
        return True


# HTTP-запросы uvicorn пишет через uvicorn.access, а строки WebSocket
# («WebSocket /ws/… [accepted]») — через uvicorn.error; маскируем в обоих.
for _logger_name in ('uvicorn.access', 'uvicorn.error'):
    logging.getLogger(_logger_name).addFilter(RedactTokenFilter())


@app.get('/api/health')
async def health():
    return {'status': 'ok'}


# Прод-режим: раздаём собранный фронтенд (frontend/dist), если он есть
_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if _dist.is_dir():
    app.mount('/', StaticFiles(directory=str(_dist), html=True), name='spa')
