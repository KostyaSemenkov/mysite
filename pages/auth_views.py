"""Вход и выход: дополнения к стандартным представлениям Django."""
import json
import logging

from django.contrib.auth import views as auth_views
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger('csp')


class LogoutView(auth_views.LogoutView):
    """Выход с сайта заодно стирает локальное хранилище origin.

    В localStorage остаётся токен «Досок» (сроком на неделю): без этого
    заголовка после «выйти» доски продолжали бы открываться от имени пользователя.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response['Clear-Site-Data'] = '"cache", "storage"'
        return response


@csrf_exempt
@require_POST
def csp_report(request):
    """Принимает отчёты браузеров о нарушениях CSP (режим Report-Only).

    Тело — application/csp-report, поэтому CSRF-проверка неприменима.
    Записи идут в лог «csp» — по ним видно, что мешает включить строгий режим.
    """
    try:
        report = json.loads(request.body.decode('utf-8'))['csp-report']
    except (ValueError, KeyError, UnicodeDecodeError):
        return HttpResponseBadRequest('bad report')

    def field(name, limit=200):
        return str(report.get(name) or '')[:limit] or '-'

    logger.warning(
        'CSP %s | blocked: %s | source: %s:%s | page: %s',
        field('effective-directive') if field('effective-directive') != '-' else field('violated-directive'),
        field('blocked-uri'), field('source-file', 160), field('line-number'), field('document-uri', 160),
    )
    return HttpResponse(status=204)
