Интеграция портала «НЕЙРО» в lemurqa.ru как полноценного раздела «ИИ-новости» на /ai/.

═══ ПЛАН ИНТЕГРАЦИИ ═══

ШАГ 1: Извлечение и перенос моделей (app `ainews`)
- Извлечь ai_portal из архива в рабочую папку
- Создать Django-app `ainews` в проекте lemurqa.ru
- Перенести модели: Publication (kind=news/article, company=kimi/zai/qwen/deepseek, slug, summary, body, source_url, featured, published_at), Course (provider, program, level, price), NewsSource, IncomingNews (очередь с ревизиями), ImportRun
- Адаптировать под PostgreSQL (убрать SQLite-специфику,fk на User для approved_by)
- Миграции + сид данных из SQLite-дампа (31 публикация, 6 курсов, 18 входящих)

ШАГ 2: Перенос сборщика новостей
- Скопировать portal/news/ (fetch.py, adapters.py, service.py) в ainews/news/
- Заменить Windows file-lock (msvcrt) на Linux (fcntl) — уже поддерживается
- Перенести management command import_china_news
- Добавить cron на VM: `0 * * * * docker compose exec web python manage.py import_china_news`

ШАГ 3: Вьюхи и URLы
- /ai/ — главная раздела (hero-новость + лента, фильтр по компании, поиск, пагинация)
- /ai/read/<slug>/ — страница публикации
- /ai/courses/ — каталог курсов (фильтры: уровень, направление, цена)
- /ai/courses/<slug>/ — страница курса
- Регистрация в config/urls.py + sitemap

ШАГ 4: Шаблоны в дизайне lemurqa.ru
- base.html с навигацией (добавить «ИИ-новости» в меню)
- ai/index.html — hero + сетка карточек (card-warm), фильтры по компании (чипы)
- ai/publication.html — статья с prose-warm, OG-теги, schema.org Article
- ai/courses.html — сетка курсов с фильтрами
- ai/course.html — детальная страница курса
- Дуал-тема, Manrope/Unbounded, иконки Lucide, reveal-анимации

ШАГ 5: Админка
- Регистрация Publication, Course в админке
- Перенести news_admin.py: IncomingNews с preview, кнопками «Одобрить» / «Отклонить», readonly-полями, групповыми действиями
- Настраиваемые list_filter, search_fields

ШАГ 6: Интеграция с существующим сайтом
- Добавить «ИИ-новости» в навигацию (шапка + бургер + футер)
- Подключить к поиску по сайту (раздел «ИИ-новости»)
- Добавить в sitemap.xml
- RSS-лента /ai/rss/
- Фавикон 🤖 для раздела

ШАГ 7: Тесты и деплой
- Перенести 23 теста (адаптировать под новые модели)
- Прогнать все тесты, check
- Пересобрать tw.css (новые классы)
- Деплой на Cloud.ru: git push → docker compose up -d --build web
- Настроить cron для сборщика на VM
- Проверить прод: страницы, сборщик, админ-очередь

═══ ЧТО НЕ ПЕРЕНОСИМ ═══
- Windows Task Scheduler (заменяем на Linux cron)
- SQLite (используем PostgreSQL)
- Собственные CSS/style.css (используем дизайн-систему lemurqa.ru)
- Шаблоны НЕЙРО (переписываем на base.html lemurqa.ru)