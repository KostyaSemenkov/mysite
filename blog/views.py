from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from pages.notify import tg_notify

from .forms import GuestPostForm
from .models import Post


def post_list(request):
    posts = Post.objects.published()
    paginator = Paginator(posts, 6)
    page = paginator.get_page(request.GET.get('page'))
    if request.headers.get('X-Load-More'):
        # фрагмент для кнопки «Показать ещё»
        return render(request, 'blog/includes/posts_page.html', {'page_obj': page})
    return render(request, 'blog/post_list.html', {'page_obj': page})


def posts_by_tag(request, tag):
    tag = tag.strip()
    posts = Post.objects.published().filter(tags__icontains=tag)
    paginator = Paginator(posts, 6)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'blog/tag.html', {'tag': tag, 'page_obj': page})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, 'blog/post_detail.html', {'post': post})


@login_required
def guest_post(request):
    if request.method == 'POST':
        form = GuestPostForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.author = request.user
            submission.save()
            tg_notify(f'📝 Новый гостевой пост на премодерации:\n'
                      f'{submission.title}\n'
                      f'Автор: {request.user.username}\n'
                      f'https://lemurqa.ru/admin/blog/guestpostsubmission/')
            messages.success(request,
                             'Пост отправлен! Появится в блоге после проверки модератором.')
            return redirect('blog:guest_post')
    else:
        form = GuestPostForm()
    from .models import GuestPostSubmission
    my_posts = GuestPostSubmission.objects.filter(author=request.user)[:10]
    return render(request, 'blog/guest_post.html', {'form': form, 'my_posts': my_posts})
