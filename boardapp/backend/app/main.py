from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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


@app.get('/api/health')
async def health():
    return {'status': 'ok'}


# Прод-режим: раздаём собранный фронтенд (frontend/dist), если он есть
_dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if _dist.is_dir():
    app.mount('/', StaticFiles(directory=str(_dist), html=True), name='spa')
