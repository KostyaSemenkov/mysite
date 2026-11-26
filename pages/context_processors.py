from django.urls import reverse

from .models import Profile

# фавикон раздела по префиксу пути (static/img/favicon/<имя>.svg)
FAVICON_BY_PREFIX = (
    ('/blog', 'blog'),
    ('/projects', 'projects'),
    ('/talks', 'talks'),
    ('/forum', 'forum'),
    ('/contacts', 'contacts'),
    ('/search', 'search'),
    ('/profile', 'profile'),
    ('/waiting', 'waiting'),
    ('/ai', 'ainews'),
    ('/boardapp', 'boards'),
)

# пункты меню: (адрес или имя URL, подпись, раздел)
_NAV = (
    ('home', 'Главная', 'home'),
    ('blog:post_list', 'Блог', 'blog'),
    ('projects:project_list', 'Проекты', 'projects'),
    ('talks:talk_list', 'Выступления', 'talks'),
    ('/ai/', 'ИИ-новости', 'ai'),
    ('/boardapp/sso/', 'Доски', 'boards'),
    ('forum:topic_list', 'Форум', 'forum'),
    ('useful', 'Полезности', 'useful'),
    ('quiz', 'Тренажёр', 'quiz'),
    ('path', 'Путь', 'path'),
)

# текущий раздел — по пространству имён URL, иначе по имени маршрута
_SECTION_BY_NS = {'blog': 'blog', 'projects': 'projects', 'talks': 'talks', 'forum': 'forum',
                  'contacts': 'contacts', 'ai': 'ai', 'ainews': 'ai'}
_SECTION_BY_NAME = {'home': 'home', 'search': 'search', 'useful': 'useful',
                    'quiz': 'quiz', 'path': 'path', 'profile': 'profile', 'boards_sso': 'boards'}

_nav_items = None


def _menu():
    global _nav_items
    if _nav_items is None:
        _nav_items = [{
            'url': url if url.startswith('/') else reverse(url),
            'label': label,
            'section': section,
        } for url, label, section in _NAV]
    return _nav_items


def profile(request):
    """Профиль, фавикон раздела, меню и текущий раздел доступны во всех шаблонах."""
    path = request.path
    favicon = 'home'
    for prefix, name in FAVICON_BY_PREFIX:
        if path.startswith(prefix):
            favicon = name
            break

    match = getattr(request, 'resolver_match', None)
    namespace = (match.namespace or '').split(':')[-1] if match else ''
    url_name = match.url_name if match else ''
    section = _SECTION_BY_NS.get(namespace) or _SECTION_BY_NAME.get(url_name, '')

    return {
        'profile': Profile.objects.first(),
        'favicon_svg': f'img/favicon/{favicon}.svg',
        'nav_items': _menu(),
        'nav_section': section,
    }
