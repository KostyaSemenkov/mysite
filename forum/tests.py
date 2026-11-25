"""Регистрация, вход и лимиты форума (гиды autofill-sign-up-form, autofill-sign-in-form)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import RATE_LIMITS
from .models import Comment, Topic

PASSWORD = 'Strong pass 123'


class RegisterTests(TestCase):
    def register(self, **overrides):
        data = {'username': 'ivan_petrov', 'password1': PASSWORD, 'password2': PASSWORD}
        data.update(overrides)
        return self.client.post(reverse('register'), data)

    def test_password_keeps_spaces(self):
        """Пробелы в пароле значимы: регистрация и вход должны понимать пароль одинаково."""
        resp = self.register()
        self.assertRedirects(resp, reverse('forum:topic_list'))
        self.assertTrue(self.client.login(username='ivan_petrov', password=PASSWORD))

    def test_fields_are_ready_for_password_manager(self):
        html = self.client.get(reverse('register')).content.decode()
        self.assertIn('autocomplete="username"', html)
        self.assertEqual(html.count('autocomplete="new-password"'), 2)
        self.assertIn('data-password-toggle="id_password1 id_password2"', html)

    def test_errors_are_linked_to_the_field(self):
        html = self.register(password2='Другой пароль 42').content.decode()
        self.assertIn('id="id_password2_error"', html)
        self.assertIn('id="id_password2_helptext"', html)
        self.assertRegex(
            html, r'<input[^>]*aria-describedby="id_password2_helptext id_password2_error"[^>]*>')

    def test_mismatch_is_explained_in_russian(self):
        resp = self.register(password2='Другой пароль 42')
        self.assertContains(resp, 'Пароли не совпадают')


class LoginTests(TestCase):
    def test_form_attributes_and_return_url(self):
        get_user_model().objects.create_user('anna', password='Qwerty-uiop-42')
        html = self.client.get(reverse('login') + '?next=/path/').content.decode()
        self.assertIn('autocomplete="username"', html)
        self.assertIn('autocomplete="current-password"', html)
        self.assertIn('class="input"', html)
        self.assertIn('<input type="hidden" name="next" value="/path/">', html)
        resp = self.client.post(reverse('login') + '?next=/path/',
                                {'username': 'anna', 'password': 'Qwerty-uiop-42', 'next': '/path/'})
        self.assertRedirects(resp, '/path/')


class CommentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('author', password=PASSWORD)
        self.topic = Topic.objects.create(title='Тема', slug='tema')
        self.client.login(username='author', password=PASSWORD)
        self.url = reverse('forum:add_comment', args=['tema'])

    def _hit_comment_limit(self):
        limit, _ = RATE_LIMITS['comment']
        Comment.objects.bulk_create(
            Comment(topic=self.topic, author=self.user, body=f'Комментарий {i}', is_approved=True)
            for i in range(limit))

    def test_rejected_comment_keeps_typed_text(self):
        self._hit_comment_limit()
        resp = self.client.post(self.url, {'guest_name': '', 'body': 'Мой длинный текст'})
        # контракт ответа прежний — перенаправление на тему
        # (fetch_redirect_response=False: иначе assertRedirects сам заберёт черновик и сообщение)
        self.assertRedirects(resp, self.topic.get_absolute_url(), fetch_redirect_response=False)
        page = self.client.get(self.topic.get_absolute_url())
        self.assertContains(page, 'Проверьте имя и текст комментария.')
        self.assertContains(page, 'Слишком много комментариев за час')
        self.assertContains(page, 'Мой длинный текст')
        # черновик показывается один раз, дальше форма снова пустая
        again = self.client.get(self.topic.get_absolute_url())
        self.assertNotContains(again, 'Слишком много комментариев за час')
        self.assertNotContains(again, 'Мой длинный текст')

    def test_empty_comment_is_declined_with_message(self):
        resp = self.client.post(self.url, {'guest_name': '', 'body': ''})
        self.assertRedirects(resp, self.topic.get_absolute_url(), fetch_redirect_response=False)
        page = self.client.get(self.topic.get_absolute_url())
        self.assertContains(page, 'Проверьте имя и текст комментария.')
        self.assertEqual(Comment.objects.count(), 0)
