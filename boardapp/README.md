# board-app — упрощённый Miro

Командные доски: тикеты-стикеры, связи-стрелки, одновременное редактирование
в реальном времени (WebSocket), шаринг по имени пользователя с ролями
owner/editor/viewer, Undo/Redo и экспорт доски в PNG.

Полная спецификация — в [miro-plan.md](miro-plan.md).

## Стек

- **Бэкенд**: Python 3.10+, FastAPI, SQLAlchemy 2.0 (async), Alembic, PyJWT, passlib
- **Фронтенд**: React + Vite + TypeScript, @xyflow/react (React Flow), Zustand, axios, html-to-image
- **БД**: PostgreSQL 16 (docker-compose); тесты — SQLite in-memory

## Запуск (dev)

```bash
# 1. база
docker compose up -d db

# 2. бэкенд (порт 8000)
cd backend
pip install -r requirements.txt
cp .env.example .env            # заполнить JWT_SECRET
python -m alembic upgrade head
python -m uvicorn app.main:app --reload

# 3. фронтенд (порт 5173, проксирует /api и /ws на бэкенд)
cd ../frontend
npm install
npm run dev
```

Открыть http://localhost:5173 — зарегистрироваться, создать доску.

## Запуск (прод-режим, один процесс)

```bash
cd frontend && npm run build && cd ../backend
python -m uvicorn app.main:app --port 8000
# FastAPI раздаёт frontend/dist по /
```

## Тесты

```bash
cd backend
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio
```

12 тестов: регистрация/логин/валидация, CRUD досок и права доступа,
WebSocket-сценарий двух пользователей, viewer read-only, отклонение
невалидного токена.

## Как этим пользоваться

1. Зарегистрируйте двух пользователей (в двух браузерах для проверки реалтайма)
2. Первый создаёт доску → «Поделиться» → приглашает второго (editor или viewer)
3. Добавляйте тикеты: кнопка «+ Тикет» или двойной клик по канве
4. Перетаскивайте, меняйте текст и цвет (точки внизу карточки)
5. Соединяйте: потяните от правого края тикета к другому
6. Ctrl+Z / Ctrl+Shift+Z — undo/redo своих действий
7. «Скачать PNG» — экспорт всей доски картинкой
8. Видите курсоры и имена соавторов онлайн
