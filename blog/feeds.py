from django.contrib.syndication.views import Feed
from django.urls import reverse

from .models import Post


class LatestPostsFeed(Feed):
    title = 'Блог Лемурзильни тестировщика'
    link = '/blog/'
    description = 'Статьи о тестировании: ручное QA, автотесты, инструменты, процессы.'

    def items(self):
        return Post.objects.published()[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.content[:300]

    def item_pubdate(self, item):
        return item.created_at

    def item_link(self, item):
        return reverse('blog:post_detail', args=[item.slug])
