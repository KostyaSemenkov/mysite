from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Post


def post_list(request):
    posts = Post.objects.published()
    paginator = Paginator(posts, 6)
    page = paginator.get_page(request.GET.get('page'))
    if request.headers.get('X-Load-More'):
        # фрагмент для кнопки «Показать ещё»
        return render(request, 'blog/includes/posts_page.html', {'page_obj': page})
    return render(request, 'blog/post_list.html', {'page_obj': page})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, 'blog/post_detail.html', {'post': post})
