"""Уведомления администратору сайта.

Telegram: задайте TG_BOT_TOKEN (от @BotFather) и TG_ADMIN_CHAT_ID
(свой id — узнаётся первым сообщением боту через getUpdates) в .env —
и уведомления о заявках, комментариях на премодерации и гостевых постах
придут в Telegram. Без переменных вызовы тихо игнорируются.
"""
import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)


def tg_notify(text: str) -> bool:
    token = os.environ.get('TG_BOT_TOKEN', '')
    chat_id = os.environ.get('TG_ADMIN_CHAT_ID', '')
    if not token or not chat_id:
        return False
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = json.dumps({'chat_id': chat_id, 'text': text[:4000]}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        logger.warning('TG-уведомление не отправлено', exc_info=True)
        return False
