"""Кнопка «Показать ещё»: номер следующей страницы приходит заголовком."""
from django.test import TestCase

from .models import Post


class LoadMoreTests(TestCase):
    def setUp(self):
        Post.objects.bulk_create(
            Post(title=f'Пост {i}', slug=f'post-{i}', is_published=True) for i in range(7))

    def test_fragment_announces_next_page(self):
        resp = self.client.get('/blog/?page=1', HTTP_X_LOAD_MORE='1')
        self.assertEqual(resp['X-Next-Page'], '2')

    def test_last_page_has_no_next_page_header(self):
        resp = self.client.get('/blog/?page=2', HTTP_X_LOAD_MORE='1')
        self.assertNotIn('X-Next-Page', resp)

    def test_full_page_keeps_button_and_fallback_link(self):
        html = self.client.get('/blog/').content.decode()
        self.assertIn('data-next="2"', html)
        self.assertIn('blog-loadmore.', html)  # имя файла с хэшем WhiteNoise
