from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from pages.notify import tg_notify

from .forms import CommentForm, TopicForm
from .models import TopicReaction
from .models import Topic


def topic_list(request):
    topics = Topic.objects.all()
    return render(request, 'forum/topic_list.html', {'topics': topics})


def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    comments = topic.visible_comments()
    form = None if topic.is_closed else CommentForm(user=request.user)
    return render(request, 'forum/topic_detail.html', {
        'topic': topic,
        'comments': comments,
        'form': form,
        'fire_count': topic.reactions.filter(kind='fire').count(),
        'like_count': topic.reactions.filter(kind='like').count(),
        'my_reactions': set(
            topic.reactions.filter(user=request.user).values_list('kind', flat=True)
        ) if request.user.is_authenticated else set(),
        'can_resolve': request.user.is_authenticated and (
            request.user.is_staff or topic.created_by_id == request.user.id),
    })


@require_POST
def add_comment(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    if topic.is_closed:
        messages.error(request, 'Тема закрыта для комментариев.')
        return redirect(topic.get_absolute_url())

    form = CommentForm(request.POST, user=request.user)
    if form.is_valid():
        if form.honeypot_triggered():
            messages.success(request, 'Комментарий отправлен и появится после проверки модератором.')
            return redirect(topic.get_absolute_url())
        comment = form.save(commit=False)
        comment.topic = topic
        if request.user.is_authenticated:
            comment.author = request.user
            comment.guest_name = ''
            comment.is_approved = True
            comment.save()
            messages.success(request, 'Комментарий добавлен.')
        else:
            comment.is_approved = False
            comment.save()
            tg_notify(f'⏳ Комментарий на премодерации от «{comment.guest_name or "Гость"}»\n'
                      f'Тема: {topic.title}\n'
                      f'{comment.body[:500]}\n'
                      f'https://lemurqa.ru/admin/forum/comment/')
            messages.success(request, 'Комментарий отправлен и появится после проверки модератором.')
    else:
        messages.error(request, 'Проверьте имя и текст комментария.')
    return redirect(topic.get_absolute_url())


@login_required
def new_topic(request):
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            if form.honeypot_triggered():
                # бот: делаем вид, что тема создана, но не сохраняем
                messages.success(request, 'Тема создана.')
                return redirect('forum:topic_list')
            topic = form.save(commit=False)
            topic.created_by = request.user
            topic.save()
            messages.success(request, 'Тема создана.')
            return redirect(topic.get_absolute_url())
    else:
        form = TopicForm()
    return render(request, 'forum/new_topic.html', {'form': form})


def register(request):
    if request.method == 'POST':
        # honeypot: боты заполняют все поля
        if request.POST.get('company_website', ''):
            from django.contrib import messages
            messages.success(request, 'Аккаунт создан. Добро пожаловать!')
            return redirect('forum:topic_list')
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Аккаунт создан. Добро пожаловать!')
            return redirect('forum:topic_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
@require_POST
def toggle_reaction(request, slug):
    from django.http import JsonResponse
    topic = get_object_or_404(Topic, slug=slug)
    kind = request.POST.get('kind', 'fire')
    if kind not in ('fire', 'like'):
        kind = 'fire'
    existing = TopicReaction.objects.filter(topic=topic, user=request.user, kind=kind).first()
    if existing:
        existing.delete()
        added = False
    else:
        TopicReaction.objects.create(topic=topic, user=request.user, kind=kind)
        added = True
    counts = {
        'fire': topic.reactions.filter(kind='fire').count(),
        'like': topic.reactions.filter(kind='like').count(),
    }
    return JsonResponse({'added': added, 'counts': counts})


@login_required
@require_POST
def toggle_resolved(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    if request.user.is_staff or (topic.created_by and topic.created_by_id == request.user.id):
        topic.is_resolved = not topic.is_resolved
        topic.save(update_fields=['is_resolved'])
        from django.contrib import messages
        messages.success(request, 'Отмечено как решённая.' if topic.is_resolved else 'Снята метка «решено».')
    return redirect(topic.get_absolute_url())
