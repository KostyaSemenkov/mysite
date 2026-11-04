from django.contrib.syndication.views import Feed
from django.utils import timezone

from .models import Publication


class AIRSSFeed(Feed):
    title = 'ИИ-новости — Лемурзильня тестировщика'
    link = '/ai/'
    description = ('Новости китайских нейросетей: Kimi, Z.ai, Qwen, DeepSeek — '
                   'официальные релизы, функции, API.')

    def items(self):
        return (Publication.objects
                .filter(published=True, published_at__lte=timezone.now())
                .order_by('-published_at')[:20])

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary or item.body[:300]

    def item_pubdate(self, item):
        return item.published_at

    def item_link(self, item):
        return item.get_absolute_url()
