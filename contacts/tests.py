"""Подписка и форма связи принимают только корректный email."""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import ContactRequest, Subscriber


class SubscribeTests(TestCase):
    def test_invalid_email_is_not_stored(self):
        resp = self.client.post(reverse('subscribe'), {'email': 'не-email'}, follow=True)
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertContains(resp, 'некорректно')


class ContactFormTests(TestCase):
    def test_invalid_email_is_declined(self):
        resp = self.client.post(reverse('contacts:contact_submit'),
                                {'name': 'Иван', 'email': 'иван@', 'message': 'Привет'}, follow=True)
        self.assertEqual(ContactRequest.objects.count(), 0)
        self.assertContains(resp, 'некорректно')

    @patch('contacts.views.tg_notify')
    def test_valid_request_is_stored(self, notify):
        resp = self.client.post(reverse('contacts:contact_submit'),
                                {'name': 'Иван', 'email': ' Ivan@Example.com ', 'message': 'Привет'})
        self.assertRedirects(resp, reverse('contacts:contact'))
        self.assertEqual(ContactRequest.objects.get().email, 'ivan@example.com')
        notify.assert_called_once()
