"""Современные практики сайта: тема, CSP, подписка, меню и защита от открытого редиректа."""
import json
import re

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from contacts.models import Subscriber
from forum.models import Topic
from pages.templatetags.site_extras import highlight


class HighlightTests(SimpleTestCase):
    """Фильтр подсветки работает с пользовательским текстом — только экранированным."""

    def test_escapes_user_text(self):
        self.assertEqual(
            highlight('<script>x</script>', 's'),
            '&lt;<mark>s</mark>cript&gt;x&lt;/<mark>s</mark>cript&gt;')

    def test_without_query_returns_plain_text(self):
        self.assertEqual(highlight('<b>жирный</b>', ''), '<b>жирный</b>')


class BaseTemplateTests(TestCase):
    def test_theme_meta_skip_link_and_external_scripts(self):
        html = self.client.get(reverse('services')).content.decode()
        self.assertIn('<meta name="color-scheme" content="light dark">', html)
        self.assertIn('<a class="skip-link" href="#content">', html)
        self.assertIn('<main id="content"', html)
        self.assertIn('data-theme-toggle', html)
        self.assertIn('data-menu-toggle', html)
        # обработчики и скрипты — не inline, а nonce-файлами
        self.assertNotRegex(html, r'\son(click|load|change|submit)=')
        self.assertRegex(html, r'<script defer src="[^"]*/js/site\.[^"]*" nonce="[^"]{10,}">')
        # многострочные пояснения — комментарии шаблона, в HTML им не место
        self.assertNotIn('{#', html)
        self.assertNotIn('{%', html)

    def test_nav_marks_current_section(self):
        Topic.objects.create(title='Тема', slug='tema')
        html = self.client.get(reverse('forum:topic_list')).content.decode()
        self.assertRegex(html, r'<a href="/forum/" class="[^"]*" aria-current="page">Форум</a>')

    def test_desktop_nav_lists_all_sections_without_hiding(self):
        """В шапке сайта нет скрытых на узких экранах разделов («Выступления» терялось)."""
        html = self.client.get(reverse('home')).content.decode()
        start = html.index('aria-label="Основное меню"')
        desktop = html[start:html.index('</nav>', start)]
        links = re.findall(r'<a href="([^"]+)"([^>]*)>([^<]*)</a>', desktop)
        by_label = {text.strip(): (href, attrs) for href, attrs, text in links}
        for label in ('Проекты', 'Выступления', 'Путь', 'ИИ-новости', 'Доски'):
            self.assertIn(label, by_label)
            self.assertNotRegex(by_label[label][1], r'\bhidden\b', label)
        self.assertEqual(by_label['Выступления'][0], reverse('talks:talk_list'))

    def test_mobile_menu_lists_all_sections(self):
        html = self.client.get(reverse('home')).content.decode()
        start = html.index('id="mobile-nav"')
        mobile = html[start:html.index('</nav>', start)]
        for label in ('ИИ-новости', 'Полезности', 'Тренажёр', 'Путь'):
            self.assertIn(label, mobile)

    def test_removed_about_section_and_contact_button(self):
        """Раздел «Обо мне» и кнопка «Связаться» убраны из шапки и меню по просьбе владельца."""
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn('Обо мне', html)
        self.assertNotIn('Связаться', html)
        self.assertNotIn('/about/', html)
        # старые ссылки на раздел ведут на главную, а не на 404
        self.assertRedirects(self.client.get('/about/'), '/', status_code=301)
        self.assertNotIn('/about/', self.client.get('/sitemap.xml').content.decode())


class SubscribeAndRedirectTests(TestCase):
    def test_valid_email_subscribes_and_returns_back(self):
        resp = self.client.post('/', {'email': ' Me@Example.com ', 'next': '/waiting/'})
        self.assertRedirects(resp, '/waiting/')
        self.assertTrue(Subscriber.objects.filter(email='me@example.com').exists())

    def test_invalid_email_is_rejected(self):
        resp = self.client.post('/', {'email': 'не-email', 'next': '/'}, follow=True)
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertContains(resp, 'некорректно')

    def test_next_cannot_point_to_another_site(self):
        for url in ('https://evil.example/', '//evil.example/'):
            with self.subTest(url=url):
                resp = self.client.post('/', {'email': 'me@example.com', 'next': url})
                self.assertRedirects(resp, '/')


class LogoutTests(TestCase):
    def test_logout_clears_local_storage_of_origin(self):
        get_user_model().objects.create_user('u', password='Strong-pass-123')
        self.client.login(username='u', password='Strong-pass-123')
        resp = self.client.post(reverse('logout'))
        self.assertEqual(resp['Clear-Site-Data'], '"cache", "storage"')


class CspTests(TestCase):
    def test_report_only_header_carries_nonce(self):
        resp = self.client.get('/robots.txt')
        policy = resp['Content-Security-Policy-Report-Only']
        self.assertIn("script-src 'nonce-", policy)
        self.assertIn("'strict-dynamic'", policy)
        self.assertNotIn('Content-Security-Policy', resp)

    @override_settings(CSP_ENFORCE=True)
    def test_enforce_mode_replaces_report_only(self):
        resp = self.client.get('/robots.txt')
        self.assertIn("script-src 'nonce-", resp['Content-Security-Policy'])
        self.assertNotIn('Content-Security-Policy-Report-Only', resp)

    def test_admin_gets_no_csp_header_in_any_mode(self):
        for enforce in (False, True):
            with self.subTest(enforce=enforce), override_settings(CSP_ENFORCE=enforce):
                resp = self.client.get('/admin/login/')
                self.assertNotIn('Content-Security-Policy', resp)
                self.assertNotIn('Content-Security-Policy-Report-Only', resp)

    def test_report_endpoint_logs_violation(self):
        report = {'csp-report': {
            'effective-directive': 'script-src', 'blocked-uri': 'inline',
            'document-uri': 'https://lemurqa.ru/', 'source-file': 'https://lemurqa.ru/x', 'line-number': 3}}
        with self.assertLogs('csp', 'WARNING') as logs:
            resp = self.client.post('/csp-report/', data=json.dumps(report),
                                    content_type='application/csp-report')
        self.assertEqual(resp.status_code, 204)
        self.assertIn('script-src', logs.output[0])
        self.assertIn('inline', logs.output[0])

    def test_report_endpoint_rejects_garbage(self):
        resp = self.client.post('/csp-report/', data='not json', content_type='application/csp-report')
        self.assertEqual(resp.status_code, 400)
