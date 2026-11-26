"""Админка очереди ИИ-новостей: предпросмотр и кнопки проверки."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import IncomingNews, NewsSource, Publication
from .news.service import revision

RU = {
    'title_ru': 'Kimi выпустила новую модель',
    'summary_ru': 'Компания Kimi представила модель с большим контекстом.',
    'body_ru': 'Новая модель Kimi поддерживает контекст из миллиона токенов.',
}


def make_news(**overrides):
    fields = {
        'source': NewsSource.objects.get_or_create(company='kimi')[0],
        'source_key': 'kimi-1',
        'source_url': 'https://example.com/kimi-1',
        'original_title': 'Kimi releases a new model',
        'original_text': 'The new model supports a long context.',
        'source_date': timezone.now() - timedelta(hours=1),
        'content_hash': 'a' * 64,
    }
    fields.update(overrides)
    return IncomingNews.objects.create(**fields)


class IncomingNewsAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('editor', 'e@example.com', 'Strong-pass-123')
        self.client.force_login(self.admin)
        self.news = make_news(**RU)

    def url(self, name):
        return reverse(f'admin:ainews_incomingnews_{name}', args=[self.news.pk])

    def refreshed(self):
        return IncomingNews.objects.get(pk=self.news.pk)

    def test_changelist_links_to_preview(self):
        page = self.client.get(reverse('admin:ainews_incomingnews_changelist'))
        self.assertContains(page, 'href="' + self.url('preview') + '"')

    def test_preview_shows_original_and_russian_text(self):
        page = self.client.get(self.url('preview'))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.news.original_title)
        self.assertContains(page, RU['body_ru'])
        self.assertContains(page, f'name="rev" value="{revision(self.news)}"')

    def test_ready_then_publish(self):
        resp = self.client.post(self.url('ready'), {'rev': revision(self.news)}, follow=True)
        self.assertContains(resp, 'отмечен готовым к проверке')
        self.assertEqual(self.refreshed().status, 'review')

        # ревизия берётся у объекта после первого шага: статус уже другой
        resp = self.client.post(self.url('approve'), {'rev': revision(self.refreshed())}, follow=True)
        self.assertContains(resp, 'Новость опубликована.')
        published = self.refreshed()
        self.assertEqual(published.status, 'published')
        self.assertEqual(Publication.objects.get(pk=published.publication_id).title, RU['title_ru'])
        self.assertEqual(published.approved_by, self.admin)

    def test_publish_before_review_is_explained(self):
        resp = self.client.post(self.url('approve'), {'rev': revision(self.news)}, follow=True)
        self.assertContains(resp, 'Сначала проверьте')
        self.assertEqual(self.refreshed().status, 'waiting')
        self.assertFalse(Publication.objects.exists())

    def test_stale_revision_does_not_publish(self):
        self.client.post(self.url('ready'), {'rev': revision(self.news)})
        # новость изменилась после того, как редактор открыл страницу
        IncomingNews.objects.filter(pk=self.news.pk).update(editor_note='проверить цифры')
        resp = self.client.post(self.url('approve'), {'rev': revision(self.refreshed()) + '0'},
                                follow=True)
        self.assertContains(resp, 'Новость изменилась')
        self.assertEqual(self.refreshed().status, 'review')

    def test_publish_uses_free_slug_when_address_is_taken(self):
        """Стартовые публикации занимают адреса вида china-<компания>-<номер>."""
        Publication.objects.create(slug=f'china-kimi-{self.news.pk}', title='Старая публикация')
        Publication.objects.create(slug=f'china-kimi-{self.news.pk}-2', title='Тоже занято')
        self.client.post(self.url('ready'), {'rev': revision(self.news)})
        resp = self.client.post(self.url('approve'), {'rev': revision(self.refreshed())}, follow=True)
        self.assertContains(resp, 'Новость опубликована.')
        published = self.refreshed()
        self.assertEqual(published.status, 'published')
        self.assertEqual(Publication.objects.get(pk=published.publication_id).slug,
                         f'china-kimi-{self.news.pk}-3')

    def test_reject(self):
        self.client.post(self.url('reject'), {'rev': revision(self.news)})
        self.assertEqual(self.refreshed().status, 'rejected')

    def test_missing_news_is_not_found(self):
        self.assertEqual(self.client.get(reverse('admin:ainews_incomingnews_preview',
                                                  args=[999999])).status_code, 404)

    def test_actions_require_staff(self):
        self.client.force_login(get_user_model().objects.create_user('reader', password='Strong-pass-123'))
        self.assertEqual(self.client.get(self.url('preview')).status_code, 302)
