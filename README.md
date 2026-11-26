# Личный бренд — сайт на Django

Сайт личного IT-бренда: главная, блог, портфолио проектов, «обо мне»,
форма связи и подписка. Весь контент управляется через админку Django.

## Запуск локально

```bash
pip install django pillow
python manage.py migrate
python manage.py runserver
```

- Сайт: http://127.0.0.1:8000
- Админка: http://127.0.0.1:8000/admin (логин `admin`, пароль `admin12345` — смените!)

## Структура

- `config/` — настройки и корневые URL
- `pages/` — главная, «обо мне», модель Profile (данные о вас)
- `blog/` — посты ( slug, теги, черновики, обложки)
- `projects/` — портфолио (стек, ссылки на демо и репозиторий, порядок)
- `contacts/` — заявки и подписчики (падают в админку)
- `templates/` — шаблоны, тёмная тема на Tailwind (CDN)

## Наполнение контентом

1. Админка → «Профиль» — имя, описание, фото, ссылки на соцсети.
2. «Посты» — статьи блога (черновик/опубликовано).
3. «Проекты» — портфолио.
4. Заявки и подписчики видны в админке по мере поступления.

## Деплой: Cloud.ru (VM + Docker, ~1000–1500 ₽/мес)

Стек для сервера: `docker-compose.yml` (web + PostgreSQL + Caddy с авто-HTTPS),
`Caddyfile`, настройки через `.env` (шаблон — `.env.production.example`).

1. **VM у Cloud.ru**: Ubuntu 24.04, 1–2 vCPU / 2 ГБ RAM, открытые порты 80 и 443
2. **DNS**: A-запись `lemurqa.ru` → IP виртуальной машины (и `www`)
3. **На сервере**:
   ```bash
   ssh root@IP_МАШИНЫ
   apt update && apt install -y docker.io docker-compose-v2 git
   git clone https://github.com/KostyaSemenkov/mysite && cd mysite
   cp .env.production.example .env && nano .env   # заполнить секреты и пароль БД
   docker compose up -d --build
   ```
4. **Суперпользователь** (после первого запуска):
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```
5. Обновление сайта после правок: `git pull && docker compose up -d --build`
6. **«Доски», когда образы из GHCR недоступны.** Фронтенд собирается локально и
   уезжает готовым (скрипт делает всё сам):
   ```bash
   scripts/deploy_boards_prebuilt.sh            # хост vm-lemurqa, каталог ~/mysite
   ```
   Что внутри: `npm run build` → передача `boardapp/frontend/dist` на сервер →
   `docker compose -f docker-compose.yml -f docker-compose.prebuilt.yml build boards`
   и `up -d --no-build boards` (стадия `app-prebuilt` в `boardapp/Dockerfile`).
7. **Образы из GitHub Container Registry.** CI (`.github/workflows/ci.yml`) прогоняет
   тесты на каждый push, а с ветки `main` после зелёных тестов публикует образы
   `ghcr.io/<владелец>/mysite-web` и `mysite-boards`. Тогда на сервере ничего не
   собирается:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.images.yml up -d web boards
   sudo docker image prune -f   # убрать образы предыдущих выпусков, иначе диск кончится
   ```
   Пакеты в GHCR открыты для чтения, пока репозиторий публичный: сервер скачивает их
   без входа. Для приватного репозитория один раз выполните на сервере
   `docker login ghcr.io` с токеном, у которого есть `read:packages`.

Защита в браузере включена по умолчанию: строгий CSP (сайт и «Доски»), HSTS на год.
Отчёты о нарушениях CSP сайт пишет в лог (`docker compose logs web | grep CSP`).
Откатить CSP в режим «только отчёты» — `DJANGO_CSP_ENFORCE=0` и
`BOARDS_CSP_ENFORCE=0` в `.env`, затем `docker compose up -d web boards`.
После правки `Caddyfile` нужен `sudo docker compose restart caddy` (около секунды
простоя): контейнер Caddy держит копию файла с момента запуска, и `caddy reload`
внутри него после `git pull` видит прежнюю версию. Адрес с `www` перенаправляется
на основной домен.

Тесты перед деплоем: `python manage.py test` (сайт) и
`python -m pytest -q` в `boardapp/backend` (Доски) — CI запускает те же команды.

Caddy сам выпустит и продлевает сертификаты Let's Encrypt для lemurqa.ru.
База и медиа живут в Docker-томах и переживают пересоздание контейнеров.

## Перед продакшеном обязательно

- [x] Смена `SECRET_KEY` и `DEBUG` через переменные окружения — уже настроено
- [x] WhiteNoise для статики — уже настроено (`collectstatic` в Dockerfile)
- [ ] Задать секреты и `DJANGO_ALLOWED_HOSTS` при деплое
- [ ] Сменить пароль админа (`admin12345` — только для локальной разработки)
- [ ] Настроить HTTPS (Fly/Cloudflare делают автоматически)
