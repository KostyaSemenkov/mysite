from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, TopicForm
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
    })


@require_POST
def add_comment(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    if topic.is_closed:
        messages.error(request, 'Тема закрыта для комментариев.')
        return redirect(topic.get_absolute_url())

    form = CommentForm(request.POST, user=request.user)
    if form.is_valid():
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
            messages.success(request, 'Комментарий отправлен и появится после проверки модератором.')
    else:
        messages.error(request, 'Проверьте имя и текст комментария.')
    return redirect(topic.get_absolute_url())


@login_required
def new_topic(request):
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
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
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Аккаунт создан. Добро пожаловать!')
            return redirect('forum:topic_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
