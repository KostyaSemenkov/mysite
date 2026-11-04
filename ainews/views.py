from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Course, Publication


def _live():
    return Publication.objects.filter(published=True, published_at__lte=timezone.now())


def ai_index(request):
    qs = _live()
    company = request.GET.get('company', '').strip()
    if company in ('kimi', 'zai', 'qwen', 'deepseek'):
        qs = qs.filter(company=company)
    query = request.GET.get('q', '').strip()
    if query:
        qs = [p for p in qs if query.lower() in p.title.lower()
              or query.lower() in (p.summary or '').lower()
              or query.lower() in p.body.lower()]

    paginator = Paginator(qs, 9)
    page = paginator.get_page(request.GET.get('page'))

    hero = _live().filter(featured=True).first() or (_live().first() if _live().exists() else None)
    return render(request, 'ai/index.html', {
        'page_obj': page,
        'hero': hero,
        'company': company,
        'query': query,
        'companies': [('kimi', 'Kimi'), ('zai', 'Z.ai'), ('qwen', 'Qwen'),
                      ('deepseek', 'DeepSeek')],
        'total': _live().count(),
    })


def publication(request, slug):
    pub = get_object_or_404(Publication, slug=slug, published=True)
    related = _live().filter(company=pub.company).exclude(pk=pub.pk)[:3]
    return render(request, 'ai/publication.html', {
        'pub': pub,
        'related': related,
    })


def courses(request):
    qs = Course.objects.filter(published=True)
    level = request.GET.get('level', '').strip()
    if level in ('beginner', 'intermediate'):
        qs = qs.filter(level=level)
    direction = request.GET.get('direction', '').strip()
    if direction:
        qs = qs.filter(direction=direction)
    price = request.GET.get('price', '').strip()
    if price == 'free':
        qs = qs.filter(price=0)
    elif price == 'paid':
        qs = qs.filter(price__gt=0)
    query = request.GET.get('q', '').strip()
    if query:
        qs = [c for c in qs if query.lower() in c.title.lower()
              or query.lower() in c.summary.lower()
              or query.lower() in c.provider.lower()]
    return render(request, 'ai/courses.html', {
        'courses': qs,
        'level': level, 'direction': direction, 'price': price, 'query': query,
        'topics': Publication.TOPICS,
    })


def course_detail(request, slug):
    c = get_object_or_404(Course, slug=slug, published=True)
    return render(request, 'ai/course.html', {'course': c})
