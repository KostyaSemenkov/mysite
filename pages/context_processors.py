from .models import Profile

# фавикон раздела по префиксу пути (static/img/favicon/<имя>.svg)
FAVICON_BY_PREFIX = (
    ('/blog', 'blog'),
    ('/projects', 'projects'),
    ('/talks', 'talks'),
    ('/forum', 'forum'),
    ('/contacts', 'contacts'),
    ('/about', 'about'),
    ('/search', 'search'),
    ('/profile', 'profile'),
    ('/waiting', 'waiting'),
    ('/boardapp', 'boards'),
)


def profile(request):
    """Профиль и фавикон раздела доступны во всех шаблонах."""
    path = request.path
    favicon = 'home'
    for prefix, name in FAVICON_BY_PREFIX:
        if path.startswith(prefix):
            favicon = name
            break
    return {
        'profile': Profile.objects.first(),
        'favicon_svg': f'img/favicon/{favicon}.svg',
    }
