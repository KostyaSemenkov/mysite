# board-app — упрощённый Miro. Спецификация для агента-разработчика

Этот документ — полное ТЗ и план разработки. Проект создаётся с нуля в текущей папке
(`board-app/`). Никакого кода ещё нет. Читай этот файл целиком перед началом работы.

## 1. Цель проекта

Веб-сервис для командного планирования по образцу Miro, но сильно упрощённый:

- пользователь создаёт **доски**;
- на доске размещает **тикеты** (карточки-стикеры с текстом и цветом);
- соединяет тикеты **стрелками** (направленные связи);
- всё сохраняется в **PostgreSQL**;
- несколько пользователей **одновременно редактируют одну доску в реальном времени**
  (WebSocket): видят изменения и курсоры друг друга;
- есть **авторизация** (регистрация/вход), **шаринг досок** по имени пользователя,
  **Undo/Redo** и **экспорт доски в PNG**.

## 2. Зафиксированные решения (не пересматривать)

| Вопрос | Решение |
|---|---|
| Бэкенд | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, PyJWT, passlib[bcrypt] |
| Фронтенд | React + Vite + TypeScript, `@xyflow/react` (React Flow), Zustand, axios |
| БД | PostgreSQL (docker-compose; допустим локальный Postgres через `.env`) |
| Авторизация | Полноценная: username + пароль, JWT. Регистрация по имени пользователя, без email |
| Реалтайм | WebSocket, сервер — источник истины, last-write-wins на уровне объекта |
| Undo/Redo | Клиентский стек обратных операций, отменяются только свои действия |
| Доступ к доске | Роли: owner / editor / viewer; приглашение по username |

Порт dev-режима: бэкенд `:8000`, фронтенд `:5173` (vite проксирует `/api` и `/ws` на бэкенд).
В проде собранный фронтенд (`dist/`) раздаёт FastAPI через StaticFiles — один процесс.

## 3. Структура репозитория

```
board-app/
├── miro-plan.md            ← этот файл
├── docker-compose.yml       ← сервис db (postgres:16)
├── backend/
│   ├── .env                 ← DATABASE_URL, JWT_SECRET (создать по .env.example)
│   ├── .env.example
│   ├── requirements.txt
│   ├── alembic/             ← миграции
│   └── app/
│       ├── main.py          ← FastAPI app, роутеры, CORS, StaticFiles
│       ├── config.py        ← pydantic-settings
│       ├── database.py      ← async engine, session
│       ├── models.py        ← ORM-модели
│       ├── schemas.py       ← pydantic-схемы
│       ├── security.py      ← JWT, хэширование паролей, get_current_user
│       ├── board_manager.py ← connection manager: presence + broadcast по доске
│       └── routers/
│           ├── auth.py
│           ├── boards.py
│           └── ws.py        ← WebSocket /ws/boards/{id}
└── frontend/
    ├── package.json
    ├── vite.config.ts       ← proxy: /api и /ws → http://localhost:8000 (ws:true)
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx          ← маршруты react-router
        ├── api.ts           ← axios + JWT-интерцептор
        ├── ws.ts            ← WebSocket-клиент: connect, reconnect, dispatch
        ├── store.ts         ← Zustand: доска, тикеты, связи, presence, undo-стек
        ├── pages/
        │   ├── LoginPage.tsx
        │   ├── RegisterPage.tsx
        │   ├── BoardsPage.tsx      ← список «мои» + «доступные мне»
        │   └── BoardEditorPage.tsx ← канва React Flow
        └── components/
            ├── TicketNode.tsx      ← кастомная нода-тикет (React Flow)
            └── Toolbar.tsx         ← добавить тикет, экспорт PNG, undo/redo, статус WS
```

## 4. Модель данных (PostgreSQL)

```
users            id (uuid pk), username (unique), password_hash, created_at
boards           id (uuid pk), owner_id → users.id, title, created_at, updated_at
board_members    board_id → boards.id, user_id → users.id, role ('editor'|'viewer'),
                 pk (board_id, user_id)
tickets          id (uuid pk, ГЕНЕРИРУЕТСЯ КЛИЕНТОМ), board_id → boards.id,
                 x float, y float, width float, height float,
                 text text, color varchar(9), updated_by → users.id, updated_at
edges            id (uuid pk, генерируется клиентом), board_id → boards.id,
                 source_ticket_id → tickets.id, target_ticket_id → tickets.id,
                 updated_by → users.id, updated_at
```

Правила:
- Удаление board — каскадно удаляет tickets, edges, board_members.
- Удаление ticket — каскадно удаляет связанные edges (FK ondelete cascade + логика в WS-хендлере).
- Владелец доски не состоит в board_members (или состоит с ролью owner — выбрать одно, последовательно).
- UUID для tickets/edges генерирует **клиент** — это позволяет оптимистичные обновления без ожидания ответа сервера; сервер принимает их как есть (pk при конфликте — игнорировать/перезаписать).

## 5. REST API

Все ответы — JSON. Ошибки — стандартные FastAPI `{detail: ...}`.
Авторизация: заголовок `Authorization: Bearer <token>` (кроме register/login).

| Метод | Путь | Тело | Ответ | Доступ |
|---|---|---|---|---|
| POST | `/api/auth/register` | `{username, password}` | `{token, user}` | — |
| POST | `/api/auth/login` | `{username, password}` | `{token, user}` | — |
| GET | `/api/auth/me` | — | `{id, username}` | любой вошедший |
| GET | `/api/boards` | — | `{own: [Board], shared: [BoardWithRole]}` | любой |
| POST | `/api/boards` | `{title}` | `Board` | любой |
| GET | `/api/boards/{id}` | — | `{board, tickets, edges, members}` (снимок) | owner/editor/viewer |
| PATCH | `/api/boards/{id}` | `{title}` | `Board` | owner |
| DELETE | `/api/boards/{id}` | — | 204 | owner |
| POST | `/api/boards/{id}/members` | `{username, role}` | `Member` | owner |
| DELETE | `/api/boards/{id}/members/{user_id}` | — | 204 | owner |
| GET | `/api/health` | — | `{"status": "ok"}` | — |

Ограничения: username 3–32 символа, уникальный; пароль ≥ 6 символов; title доски ≤ 200 символов.
Не найдено/нет доступа → 404 (не раскрывать существование чужой доски).

## 6. WebSocket-протокол

`GET /ws/boards/{board_id}?token=<jwt>` — upgrade. Токен обязателен; пользователь должен быть
owner/editor/viewer доски. Viewer может только читать (мутации → сообщение `error`).

### Клиент → Сервер

```jsonc
{"type": "ticket:create", "data": {"id": "<uuid>", "x": 0, "y": 0, "width": 200, "height": 100, "text": "Задача", "color": "#FFF3B1"}}
{"type": "ticket:update", "data": {"id": "<uuid>", "patch": {"x": 120.5, "y": 80}}}     // любые поля тикета
{"type": "ticket:delete", "data": {"id": "<uuid>"}}
{"type": "edge:create",   "data": {"id": "<uuid>", "source": "<ticketId>", "target": "<ticketId>"}}
{"type": "edge:delete",   "data": {"id": "<uuid>"}}
{"type": "cursor:move",   "data": {"x": 300, "y": 240}}                                 // НЕ персистится
```

### Сервер → Клиент

```jsonc
{"type": "init", "data": {"board": {...}, "tickets": [...], "edges": [...], "presence": [{"userId": "...", "username": "...", "color": "#E23E3E"}]}}
{"type": "ticket:created", "data": {...}, "actor": "<userId>"}   // аналогично ...updated / ...deleted, edge:created / edge:deleted
{"type": "presence:join",  "data": {"userId": "...", "username": "...", "color": "#..."}}
{"type": "presence:leave", "data": {"userId": "..."}}
{"type": "cursor", "data": {"userId": "...", "x": 300, "y": 240}}
{"type": "error", "data": {"message": "..."}}
```

Семантика:
- Каждая мутация: применить к БД → разослать всем подписчикам доски, **включая отправителя**.
  Клиент подавляет эхо по полю `actor` (свой actor_id он знает) — единый путь данных, без рассинхрона.
- `ticket:update` — частичный patch; отсутствующие поля не трогаются. `updated_at/updated_by` пишет сервер.
- Позиция при перетаскивании шлётся троттлингом ~50 мс (просто `{x, y}`), текст/цвет — сразу по подтверждению.
- `cursor:move` — только в памяти connection manager'а, рассылается остальным, в БД не пишется.
- Цвет присутствия: выдать каждому подключению цвет из фиксированной палитры по кругу
  (`#E23E3E #F5A623 #3E9BE3 #37B679 #9B51E0 #E23EA8 ...`).
- Отключение → `presence:leave` остальным.
- Клиент при reconnect заново проходит handshake и получает `init` (полный снимок).

## 7. Фронтенд: поведение и детали

**Авторизация**: токен в localStorage; axios-интерцептор добавляет заголовок, при 401 — редирект на /login. Страницы Login и Register, роут-гарды.

**Список досок** (`/`): «Мои доски» и «Доступные мне» (с бейджем роли). Создать (инпут + кнопка), переименовать (owner), удалить (owner, с подтверждением).

**Редактор** (`/board/:id`):
- React Flow: `panOnScroll`, `zoomOnScroll`, `selectionOnDrag`, MiniMap, Controls, тёмный/светлый фон — сетка `#f1f1f1` на белом.
- **Тикет** = кастомная нода `TicketNode`: текст (textarea, inline-редактирование по dblclick или сразу при создании), цветная заливка, скруглённые углы, тень. Палитра из 6 цветов стикеров: `#FFF3B1 #FFD6A5 #CAFFBF #9BF6FF #BDB2FF #FFC6FF`. Размер по умолчанию 200×100.
- Добавление тикета: кнопка «+ Тикет» в тулбаре (в центр вьюпорта) и двойной клик по пустому месту канвы.
- **Связи**: у ноды виден хэндл соединения (справа); протягивание к другой ноде создаёт edge. Тип `default` (безье), `markerEnd: {type: MarkerType.ArrowClosed}`. Клик по связи выделяет, Delete/Backspace удаляет.
- Удаление тикета: выделение + Delete; также кнопка в контекстном меню ноды (опционально).
- **Автосохранение** не нужно как отдельная кнопка — всё через WS мгновенно; в тулбаре показывать статус связи (зелёная точка «онлайн» / «переподключение…»).
- **Presence**: чужие курсоры — абсолютно позиционированные метки с именем и цветом поверх канвы (координаты React Flow); список онлайн-редакторов в тулбаре.
- **Undo/Redo**: Ctrl+Z / Ctrl+Shift+Z (и кнопки в тулбаре). Клиентский стек (до 100 записей) обратных операций:
  - create → обратное delete; delete → обратное create (с полным снимком объекта);
  - update → обратное update со старым patch;
  - перемещение (drag) коалесцировать в одну операцию (запомнить позицию на dragstart, записать на dragstop);
  - отменяются только свои действия; инверсная операция отправляется обычным путём (WS), остальные участники видят её как обычное изменение.
- **Экспорт PNG**: `html-to-image` (`toPng`) по `.react-flow__viewport` c `getNodesBounds(nodes)` и `getViewportForBounds`, padding 100px, скачивание через `<a download>`. Имя файла: `<title доски>.png`.
- Роль viewer: канва в readonly (React Flow `nodesDraggable={false}`, `nodesConnectable={false}`, редактирование текста отключено).
- Интерфейс — на русском языке.

## 8. Порядок разработки (этапы)

Работать строго по этапам; после каждого этапа приложение должно запускаться,
а пройденные возможности — работать. Не забегать вперёд.

1. **Каркас**: docker-compose (postgres:16, порт 5432, том, `POSTGRES_*` env), backend-скелет
   (FastAPI, `/api/health`, CORS для `http://localhost:5173`), alembic init + первая пустая миграция;
   frontend-скелет (Vite react-ts, React Flow «hello world» из 2 нод и 1 связи, proxy). README с командами запуска.
2. **Авторизация**: модели users + миграция, security.py (bcrypt, JWT HS256, срок 7 дней),
   роуты register/login/me; страницы Login/Register, гарды, интерцептор.
3. **Доски**: модели boards/board_members + миграция, REST CRUD + список own/shared; UI списка досок.
4. **Редактор без реалтайма**: модели tickets/edges + миграция, снимок `GET /api/boards/{id}`;
   канва, создание/перемещение/редактирование/удаление тикетов (пока сохранение заглушкой REST
   `PUT /api/boards/{id}/state` — временный эндпоинт, удалится на этапе 6).
5. **Связи**: создание перетаскиванием, стрелки, удаление.
6. **WebSocket**: board_manager (подписки на доску, presence, broadcast), роут ws, применение
   операций к БД; фронт: ws.ts (connect/reconnect/backoff), store переводится на WS,
   optimistic updates с подавлением эха по `actor`; тулбар-статус; курсоры.
7. **Шаринг**: эндпоинты members, UI приглашения (модалка owner'а: username + роль),
   раздел «Доступные мне», viewer-readonly.
8. **Undo/Redo**: стек в store, коалесцирование drag, горячие клавиши, кнопки.
9. **Экспорт PNG**.
10. **Тесты и полировка**: см. раздел 9; финальная проверка сценария двух пользователей.

## 9. Тестирование и приёмка

**Автотесты** (pytest, в `backend/tests/`): регистрация/логин (успех, дубли username, неверный пароль,
невалидный токен); CRUD досок и права доступа (чужая доска → 404, editor не может удалять доску);
WS: два тестовых клиента подключаются к одной доске, операция от первого доходит второму,
viewer не может мутировать, эхо содержит корректного actor. Для тестов допустима SQLite
(aiosqlite) в памяти, если Postgres-специфики нет.

**Ручная приёмка** (обязательна перед сдачей):
1. Регистрация двух пользователей в двух браузерах.
2. Первый создаёт доску, приглашает второго как editor.
3. Оба открывают доску: второй видит появления/перемещения тикетов, стрелки, изменение текста/цвета в реальном времени, курсор первого.
4. Undo у первого отменяет его последнее действие у обоих.
5. Экспорт PNG скачивается и содержит всю доску.
6. Перезагрузка страницы — состояние доски восстанавливается из БД.
7. F12-консоль без ошибок.

## 10. Вне scope (не делать)

- Комментарии на тикетах, чат, вложения, картинки.
- Типы/подписи/стили связей (только стрелка).
- Бесшовное слияние конфликтов (CRDT) — last-write-wins достаточно.
- Восстановление пароля, OAuth, email.
- Экспорт в JSON/PDF, версии и история доски на сервере.
- Мобильное приложение, оффлайн-режим.

## 11. Правила работы агента

- Следуй этому файлу; решения из раздела 2 не меняй без явного запроса пользователя.
- Пиши код на английских идентификаторах, тексты UI — на русском.
- Не добавляй фичи из раздела 10 «на всякий случай».
- После каждого этапа убеждайся, что `backend` и `frontend` стартуют без ошибок.
- Зависимости фиксируй точными версиями в `requirements.txt` / `package.json`.
- Секреты только в `.env` (и `.env.example` с плейсхолдерами); `.env` в `.gitignore`.
- Итог: README с командами запуска (docker compose up -d db → alembic upgrade head →
  uvicorn app.main:app --reload → npm run dev) и кратким описанием проекта.
