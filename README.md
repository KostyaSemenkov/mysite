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

## Деплой (рекомендуемый стек, ~0–5 $/мес)

Проект уже подготовлен: Dockerfile, fly.toml, requirements.txt, WhiteNoise
и настройки через переменные окружения (см. `.env.example`).

1. **Код на GitHub**: `git init && git add . && git commit -m "initial"` → запушить
2. **База**: бесплатный PostgreSQL на https://neon.tech → строка `DATABASE_URL`
3. **Хостинг** (Fly.io):
   ```bash
   fly auth signup
   fly launch --no-deploy          # создаст приложение (fly.toml уже есть)
   fly secrets set DJANGO_SECRET_KEY="<случайная строка>" \
                   DJANGO_DEBUG=0 \
                   DJANGO_ALLOWED_HOSTS="ваш-домен.ru" \
                   DATABASE_URL="postgresql://...из Neon..."
   fly deploy
   fly ssh console -C "python manage.py migrate && python manage.py createsuperuser"
   ```
4. **Домен**: купить у регистратора, DNS через Cloudflare, затем `fly certs add ваш-домен.ru`

Медиа-файлы (фото, обложки) на Fly хранить нельзя (диск несменяемый) —
при первом объёме можно грузить в репозиторий в `media/`, позже перевести
на Cloudflare R2 через `django-storages`.

## Перед продакшеном обязательно

- [x] Смена `SECRET_KEY` и `DEBUG` через переменные окружения — уже настроено
- [x] WhiteNoise для статики — уже настроено (`collectstatic` в Dockerfile)
- [ ] Задать секреты и `DJANGO_ALLOWED_HOSTS` при деплое
- [ ] Сменить пароль админа (`admin12345` — только для локальной разработки)
- [ ] Настроить HTTPS (Fly/Cloudflare делают автоматически)
