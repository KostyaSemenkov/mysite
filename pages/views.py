from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from blog.models import Post
from forum.models import Comment, Topic
from projects.models import Project
from talks.models import Talk

from .models import FaqItem, Favorite, Profile, Testimonial


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

    context = {
        'latest_posts': Post.objects.published()[:3],
        'featured_projects': Project.objects.published()[:3],
        'upcoming_talks': Talk.objects.upcoming()[:2],
        'testimonials': Testimonial.objects.filter(is_published=True),
        'faq_items': FaqItem.objects.filter(is_published=True),
        'stats': {
            'posts': Post.objects.published().count(),
            'projects': Project.objects.published().count(),
            'talks': Talk.objects.published().count(),
            'topics': Topic.objects.count(),
            'members': _member_count(),
        },
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


def search(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        lookups = {
            'Посты': Post.objects.published().filter(
                Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(content__icontains=q)),
            'Проекты': Project.objects.published().filter(
                Q(title__icontains=q) | Q(description__icontains=q)
                | Q(tech_stack__icontains=q)),
            'Выступления': Talk.objects.published().filter(
                Q(title__icontains=q) | Q(description__icontains=q)
                | Q(event__icontains=q)),
            'Темы форума': Topic.objects.filter(
                Q(title__icontains=q) | Q(body__icontains=q)),
        }
        for label, qs in lookups.items():
            for obj in qs[:20]:
                results.append((label, obj))
    return render(request, 'pages/search.html', {'q': q, 'results': results})


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
    return render(request, 'pages/profile.html', {
        'my_topics': Topic.objects.filter(created_by=request.user)[:10],
        'my_comments': Comment.objects.filter(author=request.user,
                                              is_approved=True).select_related('topic')[:15],
        'favorites': favorites,
        'fav_count': favs.count(),
    })
