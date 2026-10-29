from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from blog.models import Post
from forum.models import Comment, Topic
from projects.models import Project
from talks.models import Talk

from .models import (FaqItem, Favorite, PathItem, PathStep, Profile, QuizAttempt,
                     QuizQuestion, Testimonial, UsefulFile, UserPathProgress)


def home(request):
    if request.method == 'POST' and request.POST.get('next'):
        # форма листа ожидания с возвратом на исходную страницу
        from contacts.models import Subscriber
        from django.contrib import messages
        email = request.POST.get('email', '').strip().lower()
        if email:
            Subscriber.objects.get_or_create(email=email)
            messages.success(request, 'Вы в списке ожидания — напишем, как только стартуем!')
            return redirect(request.POST['next'])

    stats = {
        'posts': Post.objects.published().count(),
        'projects': Project.objects.published().count(),
        'talks': Talk.objects.published().count(),
        'topics': Topic.objects.count(),
        'members': _member_count(),
    }
    context = {
        'stats': stats,
        'stats_list': [
            (stats['posts'], 'статей в блоге'),
            (stats['talks'], 'выступлений'),
            (stats['projects'], 'проектов'),
            (stats['topics'], 'тем на форуме'),
            (stats['members'], 'участников'),
        ],
        'latest_posts': Post.objects.published()[:3],
        'featured_projects': Project.objects.published()[:3],
        'upcoming_talks': Talk.objects.upcoming()[:2],
        'testimonials': Testimonial.objects.filter(is_published=True),
        'faq_items': FaqItem.objects.filter(is_published=True),
    }
    return render(request, 'pages/home.html', context)


def _member_count():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.count()


def about(request):
    return render(request, 'pages/about.html')


def privacy(request):
    return render(request, 'pages/privacy.html')


def offer(request):
    return render(request, 'pages/offer.html')


def waiting_list(request):
    return render(request, 'pages/waiting.html')


@login_required
@require_POST
def favorite_toggle(request):
    from django.contrib.contenttypes.models import ContentType
    ct_id = request.POST.get('ct')
    object_id = request.POST.get('oid')
    try:
        ct = ContentType.objects.get_for_id(int(ct_id))
        model = ct.model_class()
        if model not in (Post, Project, Talk):
            raise LookupError
        if not model.objects.filter(pk=object_id).exists():
            raise LookupError
    except (TypeError, ValueError, LookupError, ContentType.DoesNotExist):
        return redirect('/')

    fav, created = Favorite.objects.get_or_create(
        user=request.user, content_type=ct, object_id=str(object_id))
    if not created:
        fav.delete()
    return redirect(request.META.get('HTTP_REFERER') or '/')



class _SectionResult:
    """Раздел сайта как результат поиска."""

    def __init__(self, title, url):
        self.title = title
        self.url = url

    def get_absolute_url(self):
        return self.url

    def __str__(self):
        return self.title


SITE_SECTIONS = [
    ('Главная', '/', 'домой home старт'),
    ('Блог', '/blog/', 'статьи посты записи'),
    ('Проекты', '/projects/', 'портфолио работы кейсы пет'),
    ('Выступления', '/talks/', 'доклады вебинары конференции записи видео'),
    ('Календарь выступлений', '/talks/calendar/', 'календарь расписание даты события митап ical'),
    ('Доски', '/boardapp/sso/', 'доска miro миро стикеры стикер канбан канван групп совместные'),
    ('Форум', '/forum/', 'обсуждения темы сообщество комментарии'),
    ('Полезности', '/useful/', 'чеклист чек-лист скачать шаблоны файлы репорт баг'),
    ('Тренажёр', '/quiz/', 'квиз тест вопросы проверка знаний обучение'),
    ('Услуги', '/services/', 'консультации аудит менторство ревью автотестов цена заказать'),
    ('Обо мне', '/about/', 'автор биография манифест таймлайн кто'),
    ('Контакты', '/contacts/', 'связаться написать email письмо заявка'),
    ('Курс по автотестам', '/waiting/', 'курс обучение автотесты ожидание pytest'),
]

def search(request):
    q = request.GET.get('q', '').strip()
    section = request.GET.get('section', '').strip()
    results = []
    if q:
        ql = q.lower()
        for title, url, keywords in SITE_SECTIONS:
            if ql in title.lower() or any(k in ql or ql in k for k in keywords.split()):
                results.append(('Раздел', _SectionResult(title, url)))
        lookups = {
            'blog': ('Посты', Post.objects.published().filter(
                Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(content__icontains=q))),
            'projects': ('Проекты', Project.objects.published().filter(
                Q(title__icontains=q) | Q(description__icontains=q)
                | Q(tech_stack__icontains=q))),
            'talks': ('Выступления', Talk.objects.published().filter(
                Q(title__icontains=q) | Q(description__icontains=q)
                | Q(event__icontains=q))),
            'forum': ('Темы форума', Topic.objects.filter(
                Q(title__icontains=q) | Q(body__icontains=q))),
        }
        if section == 'sections':
            lookups = {}
        for key, (label, qs) in lookups.items():
            if section and key != section:
                continue
            for obj in qs[:20]:
                results.append((label, obj))
    return render(request, 'pages/search.html',
                  {'q': q, 'results': results, 'section': section})


@login_required
def profile(request):
    from django.contrib.contenttypes.models import ContentType
    favs = request.user.favorites.select_related('content_type').order_by('-created_at')
    favorites = []
    for fav in favs[:50]:
        obj = fav.content_object
        if obj is not None:
            favorites.append({
                'label': fav.content_type.name.capitalize(),
                'title': str(obj),
                'url': getattr(obj, 'get_absolute_url', lambda: '/')(),
            })
    from .models import PathItem
    total_items = PathItem.objects.count()
    done_items = UserPathProgress.objects.filter(user=request.user).count()
    percent = round(done_items * 100 / total_items) if total_items else 0
    stage = lemur_stage(percent)
    return render(request, 'pages/profile.html', {
        'lemur_percent': percent, 'lemur_stage': stage,
        'quiz_attempts': (request.user.quiz_attempts.all()[:8]
                          if hasattr(request.user, 'quiz_attempts') else []),
        'my_topics': Topic.objects.filter(created_by=request.user)[:10],
        'my_comments': Comment.objects.filter(author=request.user,
                                              is_approved=True).select_related('topic')[:15],
        'favorites': favorites,
        'fav_count': favs.count(),
    })


def useful_downloads(request):
    files = UsefulFile.objects.filter(is_published=True)
    return render(request, 'pages/useful.html', {'files': files})


def download_file(request, pk):
    from django.http import FileResponse
    from django.shortcuts import get_object_or_404 as _g
    uf = _g(UsefulFile, pk=pk, is_published=True)
    uf.downloads += 1
    uf.save(update_fields=['downloads'])
    return FileResponse(uf.file.open('rb'), as_attachment=True, filename=uf.file.name.split('/')[-1])


def services(request):
    return render(request, 'pages/services.html')


def quiz(request):
    mode = 'interview' if request.GET.get('mode') == 'interview' else 'base'
    questions = list(QuizQuestion.objects.filter(mode=mode))
    score = None
    answers = {}
    explanations = []
    if request.method == 'POST' and questions:
        for question in questions:
            answers[question.id] = request.POST.get(f'q{question.id}', '')
        correct_count = sum(1 for question in questions
                            if answers.get(question.id) == question.correct)
        score = round(correct_count * 100 / max(1, len(questions)))
        explanations = [
            {'question': question, 'picked': answers.get(question.id, ''),
             'is_right': answers.get(question.id) == question.correct}
            for question in questions
        ]
        QuizAttempt.objects.create(user=request.user if request.user.is_authenticated else None,
                                   mode=mode, score=score, total=len(questions))
        # подписка «получить разбор на почту» — тем же механизмом
        email = request.POST.get('email', '').strip().lower()
        if email and score is not None:
            from contacts.models import Subscriber
            from django.contrib import messages
            Subscriber.objects.get_or_create(email=email)
            messages.success(request, 'Разбор отправлен в ближайший дайджест — вы в списке!')
    return render(request, 'pages/quiz.html', {
        'questions': questions, 'score': score, 'answers': answers,
        'explanations': explanations, 'mode': mode,
    })


LEMUR_STAGES = [
    (0, 'Голодный джун', '🐓'),
    (25, 'Начинающий лемур', '🐒'),
    (50, 'Упитанный мидл', '🐵'),
    (75, 'Плотный сеньор', '🦍'),
    (100, 'Дородный гуру QA', '🦧'),
]


def lemur_stage(percent):
    current = LEMUR_STAGES[0]
    for stage in LEMUR_STAGES:
        if percent >= stage[0]:
            current = stage
    return current


def path_page(request):
    steps = PathStep.objects.prefetch_related('items').all()
    done_ids = set()
    if request.user.is_authenticated:
        done_ids = set(UserPathProgress.objects.filter(
            user=request.user).values_list('item_id', flat=True))
    total = sum(st.items.count() for st in steps)
    percent = round(len(done_ids) * 100 / total) if total else 0
    return render(request, 'pages/path.html', {
        'steps': steps, 'done_ids': done_ids,
        'total': total, 'done': len(done_ids), 'percent': percent,
    })


@login_required
@require_POST
def path_toggle(request, item_id):
    from django.http import JsonResponse
    item = PathItem.objects.filter(pk=item_id).first()
    if item is None:
        return JsonResponse({'ok': False}, status=404)
    progress = UserPathProgress.objects.filter(user=request.user, item=item).first()
    if progress:
        progress.delete()
        done = False
    else:
        UserPathProgress.objects.create(user=request.user, item=item)
        done = True
    total = PathItem.objects.count()
    done_count = UserPathProgress.objects.filter(user=request.user).count()
    return JsonResponse({'ok': True, 'done': done,
                         'percent': round(done_count * 100 / total) if total else 0})
