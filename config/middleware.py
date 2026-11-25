"""Content Security Policy с одноразовым nonce для каждого запроса."""
import secrets
from urllib.parse import urlparse

from django.conf import settings

# сервисы, чьи плееры встраиваются в страницы (<iframe>)
FRAME_SOURCES = (
    'https://www.youtube-nocookie.com',
    'https://www.youtube.com',
    'https://vk.com',
)


def build_policy(nonce):
    """Политика CSP для страницы сайта.

    Скрипты — только с nonce текущего ответа (inline-скрипт темы и наши файлы);
    'strict-dynamic' разрешает скриптам подгружать свои зависимости.
    Стили оставлены 'unsafe-inline': в шаблонах много style-атрибутов с токенами.
    """
    connect = ["'self'"]
    if settings.UMAMI_SRC:
        parsed = urlparse(settings.UMAMI_SRC)
        if parsed.scheme and parsed.netloc:
            connect.append(f'{parsed.scheme}://{parsed.netloc}')

    directives = [
        "default-src 'self'",
        f"script-src 'nonce-{nonce}' 'strict-dynamic'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        'connect-src ' + ' '.join(connect),
        'frame-src ' + ' '.join(FRAME_SOURCES),
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        'report-uri ' + settings.CSP_REPORT_URI,
    ]
    return '; '.join(directives)


class CspNonceMiddleware:
    """Выдаёт nonce в request.csp_nonce и добавляет заголовок CSP.

    По умолчанию режим Report-Only: браузер лишь сообщает о нарушениях
    на CSP_REPORT_URI и ничего не блокирует. Когда отчёты чистые,
    включите принудительный режим переменной DJANGO_CSP_ENFORCE=1.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)

        # в админке Django собственные inline-скрипты: её не трогаем ни в одном режиме
        if request.path.startswith('/admin/'):
            return response
        if settings.CSP_ENFORCE:
            header = 'Content-Security-Policy'
        else:
            header = 'Content-Security-Policy-Report-Only'
        response[header] = build_policy(request.csp_nonce)
        return response


def csp_nonce(request):
    """Контекст-процессор: nonce для <script nonce="…"> в шаблонах."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
