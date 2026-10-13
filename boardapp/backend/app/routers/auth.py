from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from ..config import settings
from ..database import get_session
from ..models import User
from ..schemas import AuthOut, LoginIn, RegisterIn, UserOut
from ..security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix='/api/auth', tags=['auth'])


@router.post('/register', response_model=AuthOut)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    existing = await session.scalar(
        select(User).where(User.username == body.username)
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Имя пользователя уже занято')
    user = User(username=body.username, password_hash=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return AuthOut(token=create_token(user.id), user=UserOut.of(user))


@router.post('/login', response_model=AuthOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Неверное имя или пароль')
    return AuthOut(token=create_token(user.id), user=UserOut.of(user))


@router.get('/me', response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.of(user)


def _sanitize_username(raw: str, fallback: str) -> str:
    cleaned = ''.join(ch for ch in raw if ch.isalnum() and ch.isascii() or ch in '_.-')
    cleaned = cleaned.strip('_.-')
    if not (3 <= len(cleaned) <= 32):
        cleaned = f'u{fallback}'[:32]
    return cleaned


_SSO_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Вход…</title></head>
<body style="background:#1e222c;color:#dde3ee;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<p>Входим в «Доски»…</p>
<script>
localStorage.setItem('boardapp_token', {token_json});
localStorage.setItem('boardapp_user', {user_json});
location.replace({next_json});
</script>
</body></html>"""


@router.get('/sso', response_class=HTMLResponse)
async def sso(token: str = Query(''), next: str = Query('/boards/'),
              session: AsyncSession = Depends(get_session)):
    """Вход по короткоживущему JWT, выпущенному сайтом Django (общий SSO_SECRET).

    Находит (или создаёт) пользователя по external_id = id аккаунта сайта,
    обновляет имя, выдаёт свой JWT и отдаёт HTML-шим, кладущий токен
    в localStorage и возвращающий пользователя в приложение.
    """
    try:
        payload = jwt.decode(token, settings.sso_secret, algorithms=['HS256'])
        external_id = str(payload['sub'])
        raw_username = str(payload.get('username', ''))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Недействительный SSO-токен')

    user = await session.scalar(select(User).where(User.external_id == external_id))
    if user is None:
        base = _sanitize_username(raw_username, external_id)
        username, n = base, 0
        while True:
            clash = await session.scalar(select(User).where(User.username == username))
            if clash is None:
                break
            n += 1
            username = f'{base[:28]}{n}'
        user = User(username=username,
                    password_hash=hash_password(f'sso:{external_id}:{settings.jwt_secret}'),
                    external_id=external_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        wanted = _sanitize_username(raw_username, external_id)
        if wanted != user.username:
            clash = await session.scalar(select(User).where(User.username == wanted))
            if clash is None:
                user.username = wanted
                await session.commit()

    import json
    next_url = next if next.startswith('/boards') else '/boards/'
    return HTMLResponse(_SSO_PAGE.format(
        token_json=json.dumps(create_token(user.id)),
        user_json=json.dumps({'id': user.id, 'username': user.username}),
        next_json=json.dumps(next_url),
    ))
