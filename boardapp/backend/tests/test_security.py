"""Заголовки безопасности и чистота access-лога «Досок»."""
import logging

import pytest

from app.main import SECURITY_HEADERS, RedactTokenFilter

pytestmark = pytest.mark.asyncio


async def test_security_headers_on_api(client):
    r = await client.get('/api/health')
    for name, value in SECURITY_HEADERS:
        assert r.headers[name] == value
    policy = r.headers['content-security-policy-report-only']
    assert "script-src 'self'" in policy
    assert 'content-security-policy' not in r.headers


def test_access_log_hides_token():
    record = logging.LogRecord(
        'uvicorn.access', logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
        ('127.0.0.1:1', 'GET', '/ws/boards/42?token=secret.value&clientId=abc', '1.1', 101), None)
    assert RedactTokenFilter().filter(record)
    message = record.getMessage()
    assert 'secret.value' not in message
    assert 'token=***' in message
    assert 'clientId=abc' in message


def test_uvicorn_loggers_mask_token_in_real_lines(caplog):
    """HTTP-строки uvicorn пишет через uvicorn.access, строки WebSocket — через uvicorn.error."""
    client = ('172.18.0.4', 41910)
    path = '/ws/boards/42?token=secret.value&clientId=abc'
    with caplog.at_level(logging.INFO, logger='uvicorn.access'), \
            caplog.at_level(logging.INFO, logger='uvicorn.error'):
        logging.getLogger('uvicorn.access').info('%s - "%s %s HTTP/%s" %d',
                                                 '172.18.0.4:1', 'GET', path, '1.1', 200)
        logging.getLogger('uvicorn.error').info('%s - "WebSocket %s" [accepted]', client, path)
    assert len(caplog.messages) == 2
    assert all('secret.value' not in line for line in caplog.messages)
    assert all('token=***&clientId=abc' in line for line in caplog.messages)
