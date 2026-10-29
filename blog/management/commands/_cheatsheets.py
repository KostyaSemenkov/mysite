# Шпаргалки волны R3: SQL, Postman/API, DevTools, Git

CHEATSHEETS = [
    ('Чек-лист регресса перед релизом',
     'Дым + зоны риска + фоновые проверки + прод-проверки: один лист, который можно защитить перед менеджером.',
     'checklist-regress.md',
     None),
    ('Шаблон баг-репорта',
     '7 обязательных элементов с примерами заполнения — копируйте в трекер.',
     'template-bug-report.md',
     None),
    ('Чек-лист ревью пул-реквестов тестировщика',
     'Что смотреть в чужом коде без умения программировать: ветвления, границы, дефолты.',
     'checklist-pr-review.md',
     None),
    ('План первых 90 дней в QA',
     'Понедельная карта входа в профессию с контрольными точками.',
     'plan-90-days.md',
     None),
    ('SQL-шпаргалка для тестировщика',
     'JOIN, GROUP BY, NULL-ловушки, осиротевшие записи — готовые запросы для проверки данных.',
     'cheatsheet-sql.md',
     '''# SQL для тестировщика

## Быстрые проверки данных
```sql
-- дубли по ключу
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;

-- осиротевшие записи (заказ без предметов)
SELECT o.* FROM orders o
LEFT JOIN order_items i ON i.order_id = o.id
WHERE i.id IS NULL;

-- NULL в обязательных полях
SELECT COUNT(*) FROM products WHERE price IS NULL OR price <= 0;
```

## JOIN-шпаргалка
| Тип | Что вернёт |
|---|---|
| INNER | только совпадения в обеих таблицах |
| LEFT | все из левой + совпадения из правой (NULL если нет) |
| RIGHT | зеркально LEFT |
| FULL | всё из обеих |

## NULL-ловушки
- `WHERE x != 'value'` НЕ вернёт строки где x IS NULL
- `COUNT(*)` считает все, `COUNT(x)` — только не-NULL
- `ORDER BY x` ставит NULL последними (ASC) или первыми (DESC)

## Группировка и агрегаты
```sql
-- сумма заказов по статусам за неделю
SELECT status, COUNT(*), SUM(total)
FROM orders
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY status
ORDER BY count DESC;
```
'''),
    ('Postman / API-шпаргалка',
     'Тестирование REST: статусы, headers, коллекции, environments, скрипты.',
     'cheatsheet-api.md',
     '''# Postman / API для тестировщика

## HTTP-статусы: на что смотреть
| Код | Значение | Когда ок |
|---|---|---|
| 200 | OK | GET, PATCH, DELETE |
| 201 | Created | POST (создание) |
| 204 | No Content | DELETE, иногда PUT |
| 400 | Bad Request | негативная валидация |
| 401 | Unauthorized | нет/просрочен токен |
| 403 | Forbidden | есть токен, нет прав |
| 404 | Not Found | несуществующий ресурс |
| 409 | Conflict | дубликат |
| 422 | Unprocessable | семантическая ошибка |
| 500 | Server Error | НИКОГДА не ок |

## Чек-лист тестирования API
- [ ] Позитив: валидные данные → 2xx + корректное тело ответа
- [ ] Негатив: пустые/граничные/невалидные данные → 4xx (не 500!)
- [ ] Обязательные поля: каждое отсутствует по отдельности
- [ ] Дубликаты → 409, не создание второй записи
- [ ] Права: чужой ресурс → 403/404
- [ ] Токен отсутствует/просрочен → 401
- [ ] Схема ответа: все поля присутствуют, типы совпадают
- [ ] Заголовки: Content-Type, CORS, идемпотентность DELETE/PUT

## Postman environments
`{{base_url}}`, `{{token}}` — переключение стендов без правки запросов.
Tests-вкладка: `pm.response.to.have.status(200)` — авто-проверки.

## cURL из DevTools
Правой кнопкой на запрос в Network → Copy as cURL — и вопрос «что уходит на сервер» закрыт.
'''),
    ('DevTools-шпаргалка',
     'Network, Console, Application, Throttling — 80% вопросов без Charles.',
     'cheatsheet-devtools.md',
     '''# Chrome DevTools для тестировщика

## Network (главная вкладка)
| Что | Как |
|---|---|
| Только API-запросы | фильтр Fetch/XHR |
| Медленный запрос | колонка Time, сортировка |
| Что ушло на сервер | клик → Headers → Request Payload |
| cURL запроса | ПКМ → Copy → Copy as cURL |
| Ответ сервера | вкладка Response / Preview |
| Статусы с ошибкой | фильтр статус ≥400 красным |

## Console
- `fetch('/api/...')` — быстрый тест ручки из консоли
- Ошибки JS — красным, жёлтое — предупреждения
- `localStorage`, `document.cookie` — состояние клиента

## Application
- Cookies: домен, срок, HttpOnly флаг
- LocalStorage / SessionStorage: ключ-значение, можно редактировать
- Service Workers: Offline режим, Cache Storage

## Тестирование производительности
- Network → Throttling → Slow 3G: как ведёт себя при плохом интернете
- Performance → Recording: что тормозит на странице
- Lighthouse: общий аудит (SEO, доступность, перф)

## Мобильный вид
Ctrl+Shift+M → Device Toolbar → iPhone/Android: вёрстка, тач-таргеты, viewport
'''),
    ('Git для тестировщика',
     'Минимум для выживания: clone, pull, diff, лог, ветки — и как смотреть код фичи.',
     'cheatsheet-git.md',
     '''# Git для тестировщика

## Ежедневный минимум
```bash
git pull                     # забрать свежий код
git log --oneline -20        # что меняли недавно
git show <hash>              # конкретный коммит (что и где поменяли)
git diff main..feature-xyz   # что изменит фича до мержа
git branch -a                # какие ветки есть
```

## Как понять, что залетит на прод
```bash
git fetch origin
git diff origin/main..origin/feature/LEMR-123 --stat   # файлы, которые тронули
git diff origin/main..origin/feature/LEMR-123 -- path/ # только нужный модуль
```

## Смотреть код без IDE
- GitHub/GitLab → Pull Requests → Files changed: то же самое с интерфейсом
- `git blame file.py` — кто и когда написал строку (когда нужна история)

## Типичные ситуации
| Ситуация | Команда |
|---|---|
| «Что нового на стейдже?» | `git log origin/stage..origin/main` |
| «В каком коммите добавили поле X?» | `git log -S "field_name"` |
| «Откатить локальные правки» | `git checkout -- file.py` |
| «Скачать конкретную ветку» | `git fetch && git checkout feature/xyz` |
'''),
]
